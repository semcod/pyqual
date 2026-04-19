from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RunStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ProjectRunState:
    name: str
    path: Path
    status: RunStatus = RunStatus.QUEUED
    iteration: int = 0
    current_stage: str = ""
    stages_done: int = 0
    stages_total: int = 0
    gates_passed: int = 0
    gates_total: int = 0
    max_iterations: int = 0
    duration: float = 0.0
    error_msg: str = ""
    analysis: str = ""
    start_time: float = 0.0
    last_line: str = ""

    @property
    def elapsed(self) -> float:
        if self.status not in (RunStatus.RUNNING,):
            return self.duration
        if self.start_time == 0.0:
            return 0.0
        return time.monotonic() - self.start_time

    @property
    def progress_pct(self) -> int:
        total = self.stages_total * max(self.max_iterations, 1)
        if total == 0:
            return 0
        return int(self.stages_done / total * 100)

    @property
    def gates_label(self) -> str:
        if self.gates_total == 0:
            return ""
        return f"{self.gates_passed}/{self.gates_total}"