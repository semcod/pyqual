from __future__ import annotations

import re

from pyqual.bulk.models import ProjectRunState, RunStatus

_STAGE_DONE_RE = re.compile(r"^\s*(✅|❌|⏭)\s+(\S+)")
_GATE_PASS_RE = re.compile(r"^\s*✅\s+\S+:.*[≥≤]")


def _parse_stage_start(state: ProjectRunState, line: str) -> bool:
    if line.startswith("▶ ") or line.startswith("► "):
        state.current_stage = line[2:].strip()
        return True
    return False


def _parse_iteration_header(state: ProjectRunState, line: str) -> None:
    if "Iteration " not in line:
        return
    try:
        num_str = line.split("Iteration ")[1].split()[0].strip("─ ")
        state.iteration = int(num_str)
        state.stages_done = 0
        state.gates_passed = 0
    except (ValueError, IndexError):
        pass


def _parse_output_line(state: ProjectRunState, line: str) -> None:
    stripped = line.strip()
    if not stripped:
        return

    state.last_line = stripped

    if "Iteration " in line:
        _parse_iteration_header(state, line)
        return

    m = _STAGE_DONE_RE.match(line)
    if m:
        state.stages_done += 1
        state.current_stage = m.group(2).rstrip("(").strip()
        if _GATE_PASS_RE.match(line):
            state.gates_passed += 1
        return

    if "All gates passed" in line:
        state.status = RunStatus.PASSED
        return

    if "Gates not met" in line:
        state.status = RunStatus.FAILED
        return