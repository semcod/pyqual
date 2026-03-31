"""Pipeline runner — executes stages in loop until quality gates pass."""

from __future__ import annotations

import json as _json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from nfo import Logger as NfoLogger
from nfo.models import LogEntry
from nfo.sinks import SQLiteSink

from pyqual.config import PyqualConfig, StageConfig
from pyqual.constants import (
    LLX_HISTORY_FILE,
    LLX_MCP_REPORT,
    PIPELINE_DB,
    PIPELINE_TABLE,
    STDERR_TAIL_CHARS,
    STDOUT_TAIL_CHARS,
    TIMEOUT_EXIT_CODE,
)
from pyqual.gates import GateSet, GateResult
from pyqual.tools import get_preset

log = logging.getLogger("pyqual.pipeline")


# ---------------------------------------------------------------------------
# Callback protocols — used by Pipeline.__init__ for type safety
# ---------------------------------------------------------------------------

@runtime_checkable
class OnStageStart(Protocol):
    def __call__(self, name: str) -> None: ...

@runtime_checkable
class OnIterationStart(Protocol):
    def __call__(self, iteration: int) -> None: ...

@runtime_checkable
class OnStageError(Protocol):
    def __call__(self, failure: Any) -> None: ...

@runtime_checkable
class OnStageDone(Protocol):
    """Called after each stage completes. Receives the full StageResult."""
    def __call__(self, result: "StageResult") -> None: ...

@runtime_checkable
class OnStageOutput(Protocol):
    """Called with each line of streaming output from a stage."""
    def __call__(self, stage_name: str, stream: str, line: str) -> None: ...

@runtime_checkable
class OnIterationDone(Protocol):
    """Called after each iteration completes. Receives the full IterationResult."""
    def __call__(self, result: "IterationResult") -> None: ...


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
                 on_stage_start: OnStageStart | None = None,
                 on_iteration_start: OnIterationStart | None = None,
                 on_stage_error: OnStageError | None = None,
                 on_stage_done: OnStageDone | None = None,
                 on_stage_output: OnStageOutput | None = None,
                 stream: bool = False,
                 on_iteration_done: OnIterationDone | None = None):
        self.config = config
        self.workdir = Path(workdir).resolve()
        self.gate_set = GateSet(config.gates)
        self.on_stage_start = on_stage_start
        self.on_iteration_start = on_iteration_start
        self.on_stage_error = on_stage_error
        self.on_stage_done = on_stage_done
        self.on_stage_output = on_stage_output
        self.stream = stream
        self.on_iteration_done = on_iteration_done
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

            if i > 1 and self._iteration_stagnated(iteration):
                log.info("pipeline=%s status=stagnated iteration=%d reason=fix_no_changes",
                         self.config.name, i)
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
            should_run = self._should_run_stage(stage_cfg, gates_status, iteration.stages, num)
            if not should_run:
                skipped_result = StageResult(
                    name=stage_cfg.name, returncode=0,
                    stdout="", stderr="", duration=0.0, skipped=True,
                )
                iteration.stages.append(skipped_result)
                if self.on_stage_done:
                    self.on_stage_done(skipped_result)
                continue

            stage_result = self._execute_stage(stage_cfg, dry_run)
            iteration.stages.append(stage_result)
            if self.on_stage_done:
                self.on_stage_done(stage_result)

        iteration.gates = self.gate_set.check_all(self.workdir)
        iteration.all_gates_passed = all(g.passed for g in iteration.gates)
        iteration.duration = time.monotonic() - start
        self._log_gates(num, iteration.gates)
        if self.on_iteration_done:
            self.on_iteration_done(iteration)
        return iteration

    @staticmethod
    def _iteration_stagnated(iteration: IterationResult) -> bool:
        """Return True if a fix stage ran but produced no changes (no diff output)."""
        for stage in iteration.stages:
            if "fix" in stage.name.lower() and not stage.skipped:
                combined = (stage.stdout or "") + (stage.stderr or "")
                if combined and "+++ b/" not in combined:
                    return True
        return False

    def _should_run_stage(
        self,
        stage: StageConfig,
        gates_pass: bool,
        stages_so_far: list[StageResult] | None = None,
        iteration: int = 1,
    ) -> bool:
        """Determine if a stage should run based on its 'when' condition."""
        if stage.when == "always":
            return True
        if stage.when == "first_iteration":
            return iteration == 1
        if stage.when == "metrics_fail":
            return not gates_pass
        if stage.when == "metrics_pass":
            return gates_pass
        if stage.when == "any_stage_fail":
            if not stages_so_far:
                return False
            return any(
                not s.passed and not s.skipped for s in stages_so_far
            )
        if stage.when == "after_fix":
            if not stages_so_far:
                return False
            return any("fix" in s.name.lower() and not s.skipped for s in stages_so_far)
        if stage.when == "after_verify_fix":
            if not stages_so_far:
                return False
            return any("verify" in s.name.lower() and not s.skipped for s in stages_so_far)
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
        elif stage.optional and command:
            # Extract the main binary, handling pipes (e.g. "yes | goal push ...")
            # and env-var prefixes. Check the last pipe segment's first word.
            # Skip check for multi-line scripts (shell scripts don't need binary check).
            cmd_stripped = command.strip()
            is_multiline = "\n" in cmd_stripped
            if not is_multiline:
                if "|" in cmd_stripped:
                    cmd_stripped = cmd_stripped.rsplit("|", 1)[-1].strip()
                binary = cmd_stripped.split()[0] if cmd_stripped else ""
                # Skip shell builtins and assignment-like tokens
                shell_builtins = {"set", "export", "cd", "source", ".", "exec", "eval", "true", "false", "test", "[", "[["}
                if binary and binary not in shell_builtins and "=" not in binary and not shutil.which(binary):
                    result = StageResult(
                        name=stage.name, returncode=0,
                        stdout=f"[skipped] '{binary}' not found on PATH (optional)",
                        stderr="", duration=0.0, skipped=True,
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

        is_fix_stage = bool(
            (stage.run and any(kw in stage.run for kw in ("llx", "aider", "fix", "repair")))
            or (stage.tool and stage.tool in ("llx-fix", "aider"))
        )

        # Resolve ${VAR} references in config env values against os.environ.
        # Drop entries whose value is an unresolvable ${VAR} so they don't
        # overwrite real env vars (e.g. OAuth session tokens).
        resolved_env: dict[str, str] = {}
        for k, v in self.config.env.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                ref = v[2:-1]
                real = os.environ.get(ref)
                if real:
                    resolved_env[k] = real
                # else: drop — don't overwrite os.environ with literal "${…}"
            else:
                resolved_env[k] = str(v)
        env = {**os.environ, **resolved_env}
        start = time.monotonic()

        if self.stream:
            result = self._execute_streaming(stage, command, allow_failure, env, start)
        else:
            result = self._execute_captured(stage, command, allow_failure, env, start)

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

    def _execute_captured(self, stage: StageConfig, command: str,
                          allow_failure: bool, env: dict, start: float) -> StageResult:
        """Execute stage with captured output (default mode)."""
        try:
            effective_timeout = stage.timeout if stage.timeout > 0 else None
            proc = subprocess.run(
                command, shell=True, cwd=self.workdir,
                capture_output=stage.capture_output, text=True,
                timeout=effective_timeout, env=env,
                stdin=subprocess.DEVNULL,
            )
            raw_rc = proc.returncode
            rc = 0 if (allow_failure and raw_rc != 0) else raw_rc
            return StageResult(
                name=stage.name, returncode=rc,
                stdout=proc.stdout or "", stderr=proc.stderr or "",
                duration=time.monotonic() - start,
                original_returncode=raw_rc,
                command=command, tool=stage.tool,
            )
        except subprocess.TimeoutExpired:
            return StageResult(
                name=stage.name, returncode=TIMEOUT_EXIT_CODE,
                stdout="", stderr=f"Timeout after {stage.timeout}s",
                duration=time.monotonic() - start,
                original_returncode=TIMEOUT_EXIT_CODE,
                command=command, tool=stage.tool,
            )
        except Exception as e:
            return StageResult(
                name=stage.name, returncode=1,
                stdout="", stderr=str(e),
                duration=time.monotonic() - start,
                original_returncode=1,
                command=command, tool=stage.tool,
            )

    def _execute_streaming(self, stage: StageConfig, command: str,
                           allow_failure: bool, env: dict, start: float) -> StageResult:
        """Execute stage with real-time output streaming via Popen."""
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        effective_timeout = stage.timeout if stage.timeout > 0 else None
        try:
            proc = subprocess.Popen(
                command, shell=True, cwd=self.workdir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, bufsize=1,
                stdin=subprocess.DEVNULL,
            )
            import select
            readable = [proc.stdout, proc.stderr]
            while readable:
                if effective_timeout:
                    elapsed = time.monotonic() - start
                    remaining = effective_timeout - elapsed
                    if remaining <= 0:
                        proc.kill()
                        proc.wait()
                        return StageResult(
                            name=stage.name, returncode=TIMEOUT_EXIT_CODE,
                            stdout="".join(stdout_lines),
                            stderr=f"Timeout after {stage.timeout}s",
                            duration=time.monotonic() - start,
                            original_returncode=TIMEOUT_EXIT_CODE,
                            command=command, tool=stage.tool,
                        )
                else:
                    remaining = 1.0
                try:
                    ready, _, _ = select.select(readable, [], [], min(remaining, 1.0))
                except (ValueError, OSError):
                    break
                for fd in ready:
                    line = fd.readline()
                    if not line:
                        readable.remove(fd)
                        continue
                    is_stderr = fd is proc.stderr
                    (stderr_lines if is_stderr else stdout_lines).append(line)
                    if self.on_stage_output:
                        self.on_stage_output(stage.name, line.rstrip(), is_stderr)

            proc.wait()
            raw_rc = proc.returncode
            rc = 0 if (allow_failure and raw_rc != 0) else raw_rc
            return StageResult(
                name=stage.name, returncode=rc,
                stdout="".join(stdout_lines), stderr="".join(stderr_lines),
                duration=time.monotonic() - start,
                original_returncode=raw_rc,
                command=command, tool=stage.tool,
            )
        except Exception as e:
            return StageResult(
                name=stage.name, returncode=1,
                stdout="".join(stdout_lines), stderr=str(e),
                duration=time.monotonic() - start,
                original_returncode=1,
                command=command, tool=stage.tool,
            )

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

    def _is_fix_stage(self, stage: StageConfig) -> bool:
        """Return True if *stage* is a fix/repair stage (llx, aider, etc.)."""
        if stage.tool and stage.tool in ("llx-fix", "aider"):
            return True
        run_cmd = stage.run or ""
        return any(kw in run_cmd for kw in ("llx", "aider", "fix", "repair", "claude"))

    def _log_stage(self, stage: StageConfig, result: StageResult) -> None:
        """Write structured nfo log entry for a stage execution."""
        preset = get_preset(stage.tool) if stage.tool else None
        is_fix = self._is_fix_stage(stage)
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
            kwargs["stderr_tail"] = result.stderr[-STDERR_TAIL_CHARS:]
        if is_fix and result.stdout:
            kwargs["stdout_tail"] = result.stdout[-STDOUT_TAIL_CHARS:]

        level_str = "INFO" if result.passed else "WARNING"
        log.log(logging.INFO if result.passed else logging.WARNING,
                "stage=%s rc=%d original_rc=%d passed=%s duration=%.1fs",
                stage.name, result.returncode, result.original_returncode,
                result.passed, result.duration)

        self._nfo_emit("stage_done", level_str, kwargs,
                       duration_ms=round(result.duration * 1000, 1))

        if is_fix and not result.skipped:
            self._archive_llx_report(stage, result)

    def _archive_llx_report(self, stage: StageConfig, result: StageResult) -> None:
        """Append the current llx_mcp.json report to llx_history.jsonl.

        Each line is a JSON object with a timestamp, stage name, duration,
        return code, and the full llx_mcp.json content (if present).
        """
        history_path = self.workdir / LLX_HISTORY_FILE
        report_path = self.workdir / LLX_MCP_REPORT

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage.name,
            "command": result.command or stage.run,
            "returncode": result.returncode,
            "duration_s": round(result.duration, 3),
            "ok": result.passed,
        }

        if report_path.exists():
            try:
                report = _json.loads(report_path.read_text())
                entry["llx_report"] = report
                entry["prompt"] = report.get("prompt", "")
                entry["model"] = report.get("model", "")
                entry["issues_count"] = len(report.get("issues", []))
                entry["success"] = report.get("success")
            except Exception:
                pass

        if result.stdout:
            entry["stdout_tail"] = result.stdout[-STDOUT_TAIL_CHARS:]

        try:
            with open(history_path, "a") as f:
                f.write(_json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            log.info("llx_history: archived fix run to %s", history_path)
        except Exception as exc:
            log.warning("llx_history: failed to archive: %s", exc)

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
