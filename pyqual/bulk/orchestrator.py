from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from pyqual.bulk.models import ProjectRunState, RunStatus
from pyqual.bulk.runner import _run_single_project

STATUS_ICON: dict[RunStatus, str] = {
    RunStatus.QUEUED: "⏳",
    RunStatus.RUNNING: "🔄",
    RunStatus.PASSED: "✅",
    RunStatus.FAILED: "❌",
    RunStatus.SKIPPED: "⏭",
    RunStatus.TIMEOUT: "⏰",
    RunStatus.ERROR: "💥",
}

STATUS_STYLE: dict[RunStatus, str] = {
    RunStatus.QUEUED: "dim",
    RunStatus.RUNNING: "bold cyan",
    RunStatus.PASSED: "bold green",
    RunStatus.FAILED: "bold red",
    RunStatus.SKIPPED: "dim yellow",
    RunStatus.TIMEOUT: "bold yellow",
    RunStatus.ERROR: "bold magenta",
}


@dataclass
class BulkRunResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def discover_projects(root: Path) -> list[ProjectRunState]:
    states: list[ProjectRunState] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / "pyqual.yaml").exists():
            states.append(ProjectRunState(name=child.name, path=child))
    return states


def build_dashboard_table(
    states: list[ProjectRunState],
    show_last_line: bool = False,
) -> "rich.table.Table":  # type: ignore[name-defined]
    try:
        from rich.table import Table
    except ImportError:  # pragma: no cover
        raise ImportError("rich is required for build_dashboard_table")

    n_pass = sum(1 for s in states if s.status == RunStatus.PASSED)
    n_fail = sum(1 for s in states if s.status == RunStatus.FAILED)
    n_run = sum(1 for s in states if s.status == RunStatus.RUNNING)
    title = f"pass:{n_pass}  fail:{n_fail}  running:{n_run}"

    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Project")
    table.add_column("Status")
    table.add_column("Iter")
    table.add_column("Gates")
    table.add_column("Time")
    if show_last_line:
        table.add_column("Last Output")

    for s in states:
        icon = STATUS_ICON.get(s.status, "?")
        style = STATUS_STYLE.get(s.status, "")
        elapsed = f"{s.elapsed:.1f}s" if s.elapsed else "-"
        row = [
            s.name,
            f"{icon} {s.status.value}",
            str(s.iteration) if s.iteration else "-",
            s.gates_label or "-",
            elapsed,
        ]
        if show_last_line:
            row.append(s.last_line or "")
        table.add_row(*row, style=style)

    return table


def bulk_run(
    root: Path,
    parallel: int = 4,
    pyqual_cmd: str = "pyqual",
    filter_names: Optional[list[str]] = None,
    dry_run: bool = False,
    timeout: int = 0,
    log_dir: Optional[Path] = None,
    live_callback: Optional[Callable[[list[ProjectRunState]], None]] = None,
) -> BulkRunResult:
    all_states = discover_projects(root)
    result = BulkRunResult()

    to_run: list[ProjectRunState] = []
    for s in all_states:
        if filter_names and s.name not in filter_names:
            s.status = RunStatus.SKIPPED
            result.skipped.append(s.name)
        else:
            to_run.append(s)

    def _run(state: ProjectRunState) -> None:
        _run_single_project(
            state,
            dry_run=dry_run,
            timeout=timeout,
            pyqual_cmd=pyqual_cmd,
            log_dir=log_dir,
        )
        if live_callback:
            live_callback(all_states)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        futures = {pool.submit(_run, s): s for s in to_run}
        for fut in concurrent.futures.as_completed(futures):
            s = futures[fut]
            exc = fut.exception()
            if exc:
                s.status = RunStatus.ERROR
                s.error_msg = str(exc)
            if s.status == RunStatus.PASSED:
                result.passed.append(s.name)
            elif s.status == RunStatus.FAILED:
                result.failed.append(s.name)
            elif s.status == RunStatus.SKIPPED:
                if s.name not in result.skipped:
                    result.skipped.append(s.name)
            else:
                result.errors.append((s.name, s.error_msg))

    return result
