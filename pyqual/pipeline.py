"""Pipeline runner — executes stages in loop until quality gates pass."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nfo import Logger as NfoLogger
from nfo.models import LogEntry
from nfo.sinks import SQLiteSink

from pyqual.config import PyqualConfig, StageConfig
from pyqual.gates import GateSet, GateResult
from pyqual.tools import get_preset

log = logging.getLogger("pyqual.pipeline")

PIPELINE_DB = ".pyqual/pipeline.db"
PIPELINE_TABLE = "pipeline_logs"

TIMEOUT_EXIT_CODE = 124


@dataclass
class StageResult:
    """Result of running a single stage."""
    name: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    skipped: bool = False
    original_returncode: int = 0
    command: str = ""
    tool: str = ""

    @property
    def passed(self) -> bool:
        return self.returncode == 0 or self.skipped


@dataclass
class IterationResult:
    """Result of one full pipeline iteration."""
    iteration: int
    stages: list[StageResult] = field(default_factory=list)
    gates: list[GateResult] = field(default_factory=list)
    all_gates_passed: bool = False
    duration: float = 0.0


@dataclass
class PipelineResult:
    """Result of the complete pipeline run (all iterations)."""
    iterations: list[IterationResult] = field(default_factory=list)
    final_passed: bool = False
    total_duration: float = 0.0

    @property
    def iteration_count(self) -> int:
        return len(self.iterations)


class Pipeline:
    """Execute pipeline stages in a loop until quality gates pass."""

    def __init__(self, config: PyqualConfig, workdir: str | Path = ".",
                 on_stage_start: Any = None, on_iteration_start: Any = None,
                 on_stage_error: Any = None):
        self.config = config
        self.workdir = Path(workdir).resolve()
        self.gate_set = GateSet(config.gates)
        self.on_stage_start = on_stage_start
        self.on_iteration_start = on_iteration_start
        self.on_stage_error = on_stage_error
        self._ensure_pyqual_dir()
        self._nfo = self._init_nfo()

    def run(self, dry_run: bool = False) -> PipelineResult:
        """Run the full pipeline loop."""
        result = PipelineResult()
        start = time.monotonic()

        self._log_event("pipeline_start",
                        stages=len(self.config.stages),
                        gates=len(self.config.gates),
                        max_iterations=self.config.loop.max_iterations,
                        dry_run=dry_run)
        log.info("pipeline=%s stages=%d gates=%d max_iter=%d dry_run=%s",
                 self.config.name, len(self.config.stages),
                 len(self.config.gates), self.config.loop.max_iterations, dry_run)

        for i in range(1, self.config.loop.max_iterations + 1):
            iteration = self._run_iteration(i, dry_run)
            result.iterations.append(iteration)

            if iteration.all_gates_passed:
                result.final_passed = True
                break

        result.total_duration = time.monotonic() - start
        self._log_event("pipeline_end",
                        final_ok=result.final_passed,
                        iterations=result.iteration_count,
                        total_duration_s=round(result.total_duration, 3))
        log.info("pipeline=%s result=%s iterations=%d duration=%.1fs",
                 self.config.name,
                 "PASS" if result.final_passed else "FAIL",
                 result.iteration_count, result.total_duration)
        return result

    def check_gates(self) -> list[GateResult]:
        """Check quality gates without running stages."""
        return self.gate_set.check_all(self.workdir)

    def _run_iteration(self, num: int, dry_run: bool) -> IterationResult:
        """Run one iteration of all stages + gate check."""
        if self.on_iteration_start:
            self.on_iteration_start(num)
        start = time.monotonic()
        iteration = IterationResult(iteration=num)
        gates_status = self.gate_set.all_passed(self.workdir)

        for stage_cfg in self.config.stages:
            should_run = self._should_run_stage(stage_cfg, gates_status)
            if not should_run:
                iteration.stages.append(StageResult(
                    name=stage_cfg.name, returncode=0,
                    stdout="", stderr="", duration=0.0, skipped=True,
                ))
                continue

            stage_result = self._execute_stage(stage_cfg, dry_run)
            iteration.stages.append(stage_result)

        iteration.gates = self.gate_set.check_all(self.workdir)
        iteration.all_gates_passed = all(g.passed for g in iteration.gates)
        iteration.duration = time.monotonic() - start
        self._log_gates(num, iteration.gates)
        return iteration

    def _should_run_stage(self, stage: StageConfig, gates_pass: bool) -> bool:
        """Determine if a stage should run based on its 'when' condition."""
        if stage.when == "always":
            return True
        if stage.when == "metrics_fail":
            return not gates_pass
        if stage.when == "metrics_pass":
            return gates_pass
        return True

    def _resolve_tool_stage(self, stage: StageConfig) -> tuple[str, bool]:
        """Resolve a tool-based stage to (command, allow_failure).

        Returns the shell command string and whether non-zero exit codes
        should be tolerated (True for linters/scanners, False for tests).
        If the tool is missing and ``stage.optional`` is set, returns
        empty command to signal the stage should be skipped.
        Raises RuntimeError for missing non-optional tools.
        """
        preset = get_preset(stage.tool)
        if preset is None:
            raise RuntimeError(
                f"Unknown tool preset '{stage.tool}' in stage '{stage.name}'. "
                f"This should have been caught during config validation."
            )

        if not preset.is_available():
            if stage.optional:
                log.info("stage=%s tool=%s status=skipped reason=not_installed", stage.name, stage.tool)
                return "", True
            raise RuntimeError(
                f"Stage '{stage.name}': tool '{stage.tool}' ({preset.binary}) "
                f"not found on PATH. Install it or set 'optional: true'."
            )

        return preset.shell_command("."), preset.allow_failure

    def _execute_stage(self, stage: StageConfig, dry_run: bool) -> StageResult:
        """Execute a single stage command."""
        command = stage.run
        allow_failure = False

        if stage.tool:
            resolved = self._resolve_tool_stage(stage)
            command, allow_failure = resolved
            if not command:
                result = StageResult(
                    name=stage.name, returncode=0,
                    stdout=f"[skipped] Tool '{stage.tool}' not found (optional)",
                    stderr="", duration=0.0, skipped=True,
                    tool=stage.tool,
                )
                self._log_stage(stage, result)
                return result

        if dry_run:
            label = f"tool:{stage.tool}" if stage.tool else stage.run
            result = StageResult(
                name=stage.name, returncode=0,
                stdout=f"[dry-run] Would execute: {label}",
                stderr="", duration=0.0,
                command=command, tool=stage.tool,
            )
            self._log_stage(stage, result)
            return result

        log.info("stage=%s tool=%s command=%r status=started", stage.name, stage.tool or "-", command)
        if self.on_stage_start:
            self.on_stage_start(stage.name)

        is_fix_stage = bool(stage.run and any(
            kw in stage.run for kw in ("llx", "aider", "fix", "repair")
        ))

        env = {**os.environ, **self.config.env}
        start = time.monotonic()

        try:
            effective_timeout = stage.timeout if stage.timeout > 0 else None
            proc = subprocess.run(
                command, shell=True, cwd=self.workdir,
                capture_output=stage.capture_output, text=True,
                timeout=effective_timeout, env=env,
            )
            raw_rc = proc.returncode
            rc = 0 if (allow_failure and raw_rc != 0) else raw_rc
            result = StageResult(
                name=stage.name, returncode=rc,
                stdout=proc.stdout or "", stderr=proc.stderr or "",
                duration=time.monotonic() - start,
                original_returncode=raw_rc,
                command=command, tool=stage.tool,
            )
        except subprocess.TimeoutExpired:
            result = StageResult(
                name=stage.name, returncode=TIMEOUT_EXIT_CODE,
                stdout="", stderr=f"Timeout after {stage.timeout}s",
                duration=time.monotonic() - start,
                original_returncode=TIMEOUT_EXIT_CODE,
                command=command, tool=stage.tool,
            )
        except Exception as e:
            result = StageResult(
                name=stage.name, returncode=1,
                stdout="", stderr=str(e),
                duration=time.monotonic() - start,
                original_returncode=1,
                command=command, tool=stage.tool,
            )

        self._log_stage(stage, result)

        if not result.passed and not result.skipped and self.on_stage_error:
            from pyqual.validation import StageFailure
            failure = StageFailure(
                stage_name=stage.name,
                returncode=result.returncode,
                stderr=result.stderr,
                stdout=result.stdout,
                duration=result.duration,
                is_fix_stage=is_fix_stage,
                timed_out=(result.returncode == TIMEOUT_EXIT_CODE),
            )
            self.on_stage_error(failure)

        return result

    # ------------------------------------------------------------------
    # nfo structured logging
    # ------------------------------------------------------------------

    def _init_nfo(self) -> NfoLogger:
        """Initialize nfo Logger with SQLiteSink writing to .pyqual/pipeline.db."""
        db_path = self.workdir / PIPELINE_DB
        sink = SQLiteSink(db_path=str(db_path), table=PIPELINE_TABLE)
        nfo = NfoLogger(name="pyqual.pipeline", sinks=[sink], propagate_stdlib=False)
        return nfo

    def _nfo_emit(self, event: str, level: str, kwargs: dict[str, Any],
                  duration_ms: float | None = None) -> None:
        """Emit a structured log entry via nfo."""
        entry = LogEntry(
            timestamp=LogEntry.now(),
            level=level,
            function_name=event,
            module="pyqual.pipeline",
            args=(),
            kwargs=kwargs,
            arg_types=[],
            kwarg_types={},
            duration_ms=duration_ms,
            version=self.config.name,
            extra=kwargs,
        )
        try:
            self._nfo.emit(entry)
        except Exception:
            pass

    def _log_stage(self, stage: StageConfig, result: StageResult) -> None:
        """Write structured nfo log entry for a stage execution."""
        preset = get_preset(stage.tool) if stage.tool else None
        kwargs: dict[str, Any] = {
            "event": "stage_done",
            "pipeline": self.config.name,
            "stage": stage.name,
            "tool": stage.tool or None,
            "command": result.command or stage.run,
            "returncode": result.returncode,
            "original_returncode": result.original_returncode,
            "ok": result.passed,
            "skipped": result.skipped,
            "duration_s": round(result.duration, 3),
            "optional": stage.optional,
            "allow_failure": bool(preset and preset.allow_failure),
        }
        if result.stderr:
            kwargs["stderr_tail"] = result.stderr[-500:]

        level_str = "INFO" if result.passed else "WARNING"
        log.log(logging.INFO if result.passed else logging.WARNING,
                "stage=%s rc=%d original_rc=%d passed=%s duration=%.1fs",
                stage.name, result.returncode, result.original_returncode,
                result.passed, result.duration)

        self._nfo_emit("stage_done", level_str, kwargs,
                       duration_ms=round(result.duration * 1000, 1))

    def _log_gates(self, iteration: int, gates: list[GateResult]) -> None:
        """Write structured nfo log entries for gate check results."""
        for g in gates:
            kwargs: dict[str, Any] = {
                "event": "gate_check",
                "pipeline": self.config.name,
                "iteration": iteration,
                "metric": g.metric,
                "value": g.value,
                "threshold": g.threshold,
                "operator": g.operator,
                "ok": g.passed,
            }
            level_str = "INFO" if g.passed else "WARNING"
            self._nfo_emit("gate_check", level_str, kwargs)
        passed = sum(1 for g in gates if g.passed)
        log.info("gates: %d/%d passed (iteration %d)", passed, len(gates), iteration)

    def _log_event(self, event: str, **extra: Any) -> None:
        """Write a generic pipeline event to the nfo structured log."""
        kwargs: dict[str, Any] = {
            "event": event,
            "pipeline": self.config.name,
            **extra,
        }
        self._nfo_emit(event, "INFO", kwargs)

    def _ensure_pyqual_dir(self) -> None:
        """Create .pyqual/ working directory."""
        (self.workdir / ".pyqual").mkdir(exist_ok=True)
