"""Bulk pipeline runner with real-time dashboard.

Runs ``pyqual run`` in parallel across all projects in a directory and displays
a live-updating Rich table showing status, current stage, iteration, duration,
and gate results for every project.

Usage (CLI):
    pyqual bulk-run /path/to/workspace
    pyqual bulk-run /path/to/workspace --parallel 4
    pyqual bulk-run /path/to/workspace --dry-run
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Project run status model
# ---------------------------------------------------------------------------

class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


STATUS_STYLE = {
    RunStatus.QUEUED: "dim",
    RunStatus.RUNNING: "bold cyan",
    RunStatus.PASSED: "bold green",
    RunStatus.FAILED: "bold red",
    RunStatus.ERROR: "bold red",
    RunStatus.SKIPPED: "dim",
    RunStatus.TIMEOUT: "bold yellow",
}

STATUS_ICON = {
    RunStatus.QUEUED: "⏳",
    RunStatus.RUNNING: "🔄",
    RunStatus.PASSED: "✅",
    RunStatus.FAILED: "❌",
    RunStatus.ERROR: "💥",
    RunStatus.SKIPPED: "⏭",
    RunStatus.TIMEOUT: "⏰",
}


@dataclass
class ProjectRunState:
    """Mutable state for a single project's pyqual run."""

    name: str
    path: Path
    status: RunStatus = RunStatus.QUEUED
    current_stage: str = ""
    iteration: int = 0
    max_iterations: int = 0
    stages_total: int = 0
    stages_done: int = 0
    gates_passed: int = 0
    gates_total: int = 0
    duration: float = 0.0
    error_msg: str = ""
    start_time: float = 0.0
    last_line: str = ""

    @property
    def progress_pct(self) -> int:
        if self.stages_total == 0 or self.max_iterations == 0:
            return 0
        total_work = self.stages_total * self.max_iterations
        done_work = (self.iteration - 1) * self.stages_total + self.stages_done
        return min(100, int(done_work / total_work * 100))

    @property
    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0.0
        if self.status in (RunStatus.PASSED, RunStatus.FAILED, RunStatus.ERROR, RunStatus.TIMEOUT):
            return self.duration
        return time.monotonic() - self.start_time

    @property
    def gates_label(self) -> str:
        if self.gates_total == 0:
            return ""
        return f"{self.gates_passed}/{self.gates_total}"


# ---------------------------------------------------------------------------
# Output line parser (parses pyqual run --verbose stderr/stdout)
# ---------------------------------------------------------------------------

def _parse_output_line(state: ProjectRunState, line: str) -> None:
    """Parse a line of pyqual run output and update state."""
    line = line.strip()
    if not line:
        return

    state.last_line = line[:120]

    # Rich markup removal for parsing
    clean = line

    # Detect iteration header: "─── Iteration 2 ───" or similar
    if "Iteration " in clean:
        try:
            parts = clean.split("Iteration ")
            if len(parts) > 1:
                num_str = parts[1].split()[0].strip("─ ")
                state.iteration = int(num_str)
                state.stages_done = 0
        except (ValueError, IndexError):
            pass

    # Detect stage completion: "  ✅ lint (1.2s)" or "  ❌ test (3.4s)" or "  ⏭ fix (skipped)"
    for icon in ("✅", "❌", "⏭", "⏭"):
        if icon in clean:
            state.stages_done += 1
            try:
                after_icon = clean.split(icon, 1)[1].strip()
                stage_name = after_icon.split("(")[0].strip()
                state.current_stage = stage_name
            except (IndexError, ValueError):
                pass
            break

    # Detect gate results: "  cc: 4.9 ≤ 15 ✅" or "  coverage: 28.9 ≥ 80 ❌"
    if "≤" in clean or "≥" in clean or ">" in clean or "<" in clean or "=" in clean:
        if "✅" in clean:
            state.gates_passed += 1

    # Detect "All gates passed!"
    if "All gates passed" in clean:
        state.status = RunStatus.PASSED

    # Detect "Gates not met after"
    if "Gates not met after" in clean:
        state.status = RunStatus.FAILED


# ---------------------------------------------------------------------------
# Single project runner (runs in a thread)
# ---------------------------------------------------------------------------

def _run_single_project(
    state: ProjectRunState,
    dry_run: bool = False,
    timeout: int = 0,
    pyqual_cmd: str = "pyqual",
) -> None:
    """Run pyqual in a single project directory. Updates state in-place."""
    state.status = RunStatus.RUNNING
    state.start_time = time.monotonic()
    state.iteration = 1

    config_path = state.path / "pyqual.yaml"
    if not config_path.exists():
        state.status = RunStatus.SKIPPED
        state.error_msg = "no pyqual.yaml"
        state.duration = 0.0
        return

    # Parse config to get stage/iteration counts
    try:
        import yaml
        data = yaml.safe_load(config_path.read_text())
        pipe = data.get("pipeline", data)
        state.stages_total = len(pipe.get("stages", []))
        state.max_iterations = pipe.get("loop", {}).get("max_iterations", 3)
        state.gates_total = len(pipe.get("metrics", {}))
    except Exception:
        state.stages_total = 0
        state.max_iterations = 3

    cmd = [pyqual_cmd, "run", "--config", str(config_path), "--workdir", str(state.path)]
    if dry_run:
        cmd.append("--dry-run")

    effective_timeout = timeout if timeout > 0 else None

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(state.path),
            bufsize=1,
        )

        # Read output line by line
        assert proc.stdout is not None
        for line in proc.stdout:
            _parse_output_line(state, line)

        proc.wait(timeout=effective_timeout)

        state.duration = time.monotonic() - state.start_time

        if state.status == RunStatus.RUNNING:
            # Finished but status not yet set by parser
            if proc.returncode == 0:
                state.status = RunStatus.PASSED
            else:
                state.status = RunStatus.FAILED

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        state.duration = time.monotonic() - state.start_time
        state.status = RunStatus.TIMEOUT
        state.error_msg = f"timeout after {timeout}s"
    except FileNotFoundError:
        state.duration = time.monotonic() - state.start_time
        state.status = RunStatus.ERROR
        state.error_msg = f"'{pyqual_cmd}' not found on PATH"
    except Exception as exc:
        state.duration = time.monotonic() - state.start_time
        state.status = RunStatus.ERROR
        state.error_msg = str(exc)[:200]


# ---------------------------------------------------------------------------
# Dashboard table builder
# ---------------------------------------------------------------------------

def build_dashboard_table(
    states: list[ProjectRunState],
    *,
    show_last_line: bool = False,
) -> Table:
    """Build a Rich Table showing the current status of all projects."""
    running = sum(1 for s in states if s.status == RunStatus.RUNNING)
    passed = sum(1 for s in states if s.status == RunStatus.PASSED)
    failed = sum(1 for s in states if s.status == RunStatus.FAILED)
    errors = sum(1 for s in states if s.status in (RunStatus.ERROR, RunStatus.TIMEOUT))
    queued = sum(1 for s in states if s.status == RunStatus.QUEUED)

    title = (
        f"pyqual bulk-run  "
        f"[cyan]running:{running}[/]  "
        f"[green]pass:{passed}[/]  "
        f"[red]fail:{failed}[/]  "
        f"[yellow]err:{errors}[/]  "
        f"[dim]queue:{queued}[/]  "
        f"total:{len(states)}"
    )

    table = Table(title=title, expand=True, show_lines=False, pad_edge=False)
    table.add_column("Project", style="bold", min_width=20, max_width=28)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Iter", width=7, justify="center")
    table.add_column("Stage", min_width=12, max_width=20)
    table.add_column("Progress", width=10, justify="center")
    table.add_column("Gates", width=8, justify="center")
    table.add_column("Time", width=8, justify="right")
    if show_last_line:
        table.add_column("Last Output", max_width=50, style="dim")

    for s in states:
        icon = STATUS_ICON.get(s.status, "?")
        style = STATUS_STYLE.get(s.status, "")
        status_text = Text(f"{icon} {s.status.value}", style=style)

        # Iteration
        if s.max_iterations > 0 and s.status not in (RunStatus.QUEUED, RunStatus.SKIPPED):
            iter_text = f"{s.iteration}/{s.max_iterations}"
        else:
            iter_text = ""

        # Stage
        stage_text = s.current_stage if s.status == RunStatus.RUNNING else s.current_stage

        # Progress bar (text-based)
        pct = s.progress_pct
        if s.status == RunStatus.PASSED:
            progress = "[green]100%[/]"
        elif s.status in (RunStatus.QUEUED, RunStatus.SKIPPED):
            progress = ""
        elif s.status in (RunStatus.FAILED, RunStatus.ERROR, RunStatus.TIMEOUT):
            progress = f"[red]{pct}%[/]"
        else:
            filled = pct // 10
            bar = "█" * filled + "░" * (10 - filled)
            progress = f"[cyan]{bar}[/]"

        # Gates
        if s.gates_total > 0:
            if s.gates_passed == s.gates_total:
                gates_text = f"[green]{s.gates_label}[/]"
            elif s.gates_passed > 0:
                gates_text = f"[yellow]{s.gates_label}[/]"
            else:
                gates_text = f"[red]{s.gates_label}[/]"
        else:
            gates_text = ""

        # Time
        elapsed = s.elapsed
        if elapsed > 60:
            time_text = f"{elapsed / 60:.1f}m"
        elif elapsed > 0:
            time_text = f"{elapsed:.1f}s"
        else:
            time_text = ""

        # Error display
        if s.error_msg and s.status in (RunStatus.ERROR, RunStatus.TIMEOUT):
            stage_text = f"[red]{s.error_msg[:30]}[/]"

        row = [s.name, status_text, iter_text, stage_text, progress, gates_text, time_text]
        if show_last_line:
            row.append(s.last_line[:50] if s.last_line else "")
        table.add_row(*row)

    return table


# ---------------------------------------------------------------------------
# Bulk run orchestrator
# ---------------------------------------------------------------------------

@dataclass
class BulkRunResult:
    """Summary of a bulk-run session."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    total_duration: float = 0.0


def discover_projects(root: Path) -> list[ProjectRunState]:
    """Find all subdirectories with pyqual.yaml and create run states."""
    states: list[ProjectRunState] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "pyqual.yaml").exists():
            states.append(ProjectRunState(name=d.name, path=d))
    return states


def bulk_run(
    root: Path,
    *,
    parallel: int = 4,
    dry_run: bool = False,
    timeout: int = 0,
    pyqual_cmd: str = "pyqual",
    filter_names: list[str] | None = None,
    live_callback: Any = None,
) -> BulkRunResult:
    """Run pyqual across all projects with parallel execution.

    Parameters
    ----------
    root:
        Parent directory containing project subdirectories.
    parallel:
        Max number of concurrent pyqual processes.
    dry_run:
        Pass --dry-run to each pyqual run.
    timeout:
        Per-project timeout in seconds (0 = no limit).
    pyqual_cmd:
        Command to invoke pyqual (default: "pyqual").
    filter_names:
        If set, only run these project names.
    live_callback:
        Callable invoked after each state change (for dashboard refresh).
    """
    import concurrent.futures

    all_states = discover_projects(root)

    if filter_names:
        name_set = set(filter_names)
        for s in all_states:
            if s.name not in name_set:
                s.status = RunStatus.SKIPPED

    active_states = [s for s in all_states if s.status == RunStatus.QUEUED]
    start = time.monotonic()

    semaphore = threading.Semaphore(parallel)

    def _run_with_semaphore(state: ProjectRunState) -> None:
        semaphore.acquire()
        try:
            _run_single_project(state, dry_run=dry_run, timeout=timeout, pyqual_cmd=pyqual_cmd)
        finally:
            semaphore.release()

    threads: list[threading.Thread] = []
    for state in active_states:
        t = threading.Thread(target=_run_with_semaphore, args=(state,), daemon=True)
        threads.append(t)
        t.start()

    # Wait for all threads, periodically calling live_callback
    while any(t.is_alive() for t in threads):
        if live_callback:
            live_callback(all_states)
        time.sleep(0.5)

    # Final callback
    if live_callback:
        live_callback(all_states)

    # Wait for threads to fully finish
    for t in threads:
        t.join(timeout=1)

    total_duration = time.monotonic() - start

    result = BulkRunResult(total_duration=total_duration)
    for s in all_states:
        if s.status == RunStatus.PASSED:
            result.passed.append(s.name)
        elif s.status == RunStatus.FAILED:
            result.failed.append(s.name)
        elif s.status in (RunStatus.ERROR, RunStatus.TIMEOUT):
            result.errors.append((s.name, s.error_msg))
        elif s.status == RunStatus.SKIPPED:
            result.skipped.append(s.name)

    return result
