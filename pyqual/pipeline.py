"""Pipeline runner — executes stages in loop until quality gates pass."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from pyqual.config import PyqualConfig, StageConfig
from pyqual.gates import GateSet, GateResult

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

    def __init__(self, config: PyqualConfig, workdir: str | Path = "."):
        self.config = config
        self.workdir = Path(workdir).resolve()
        self.gate_set = GateSet(config.gates)
        self._ensure_pyqual_dir()

    def run(self, dry_run: bool = False) -> PipelineResult:
        """Run the full pipeline loop."""
        result = PipelineResult()
        start = time.monotonic()

        for i in range(1, self.config.loop.max_iterations + 1):
            iteration = self._run_iteration(i, dry_run)
            result.iterations.append(iteration)

            if iteration.all_gates_passed:
                result.final_passed = True
                break

        result.total_duration = time.monotonic() - start
        return result

    def check_gates(self) -> list[GateResult]:
        """Check quality gates without running stages."""
        return self.gate_set.check_all(self.workdir)

    def _run_iteration(self, num: int, dry_run: bool) -> IterationResult:
        """Run one iteration of all stages + gate check."""
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

    def _execute_stage(self, stage: StageConfig, dry_run: bool) -> StageResult:
        """Execute a single stage command."""
        if dry_run:
            return StageResult(
                name=stage.name, returncode=0,
                stdout=f"[dry-run] Would execute: {stage.run}",
                stderr="", duration=0.0,
            )

        env = {**os.environ, **self.config.env}
        start = time.monotonic()

        try:
            proc = subprocess.run(
                stage.run, shell=True, cwd=self.workdir,
                capture_output=stage.capture_output, text=True,
                timeout=stage.timeout, env=env,
            )
            return StageResult(
                name=stage.name, returncode=proc.returncode,
                stdout=proc.stdout or "", stderr=proc.stderr or "",
                duration=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired:
            return StageResult(
                name=stage.name, returncode=TIMEOUT_EXIT_CODE,
                stdout="", stderr=f"Timeout after {stage.timeout}s",
                duration=time.monotonic() - start,
            )
        except Exception as e:
            return StageResult(
                name=stage.name, returncode=1,
                stdout="", stderr=str(e),
                duration=time.monotonic() - start,
            )

    def _ensure_pyqual_dir(self) -> None:
        """Create .pyqual/ working directory."""
        (self.workdir / ".pyqual").mkdir(exist_ok=True)
