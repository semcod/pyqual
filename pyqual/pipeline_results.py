"""Pipeline result dataclasses for pyqual."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyqual.gates import GateResult


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
