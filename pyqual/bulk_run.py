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
    analysis: str = ""

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
    clean = line

    # Detect stage START: "▶ lint" (emitted before stage executes)
    if clean.startswith("▶ ") or clean.startswith("► "):
        state.current_stage = clean[2:].strip()
        return

    # Detect iteration header: "─── Iteration 2 ───"
    if "Iteration " in clean:
        try:
            num_str = clean.split("Iteration ")[1].split()[0].strip("─ ")
            state.iteration = int(num_str)
            state.stages_done = 0
            state.gates_passed = 0   # reset per-iteration gate counter
        except (ValueError, IndexError):
            pass

    # Gate lines: "  ✅ critical: 0.0 ≤ 0.0" — handle before stage detection
    if "≤" in clean or "≥" in clean:
        if "✅" in clean:
            state.gates_passed += 1
        return

    # Stage completion: "  ✅ lint (1.2s)" or "  ❌ test (3.4s)" or "  ⏭ fix (skipped)"
    # Stage lines always have "(Xs)" or "(skipped)" after the name
    for icon in ("✅", "❌", "⏭"):
        if icon in clean:
            after_icon = clean.split(icon, 1)[1].strip()
            if "(" in after_icon:
                state.stages_done += 1
                state.current_stage = after_icon.split("(")[0].strip()
            break

    if "All gates passed" in clean:
        state.status = RunStatus.PASSED
    if "Gates not met after" in clean:
        state.status = RunStatus.FAILED


# ---------------------------------------------------------------------------
# LLM log analysis (optional, triggered for failed/error projects)
# ---------------------------------------------------------------------------

def _analyze_project(state: ProjectRunState, log_dir: Path | None = None) -> None:
    """Call LLM to produce a 1-line failure diagnosis. Updates state.analysis."""
    try:
        from pyqual.llm import LLM  # type: ignore[import]
        import yaml

        model: str | None = None
        config_path = state.path / "pyqual.yaml"
        if config_path.exists():
            try:
                data = yaml.safe_load(config_path.read_text())
                pipe = data.get("pipeline", data)
                model = pipe.get("env", {}).get("LLM_MODEL")
            except Exception:
                pass

        context_lines: list[str] = []
        if log_dir is not None:
            log_file = log_dir / f"{state.name}.log"
            if log_file.exists():
                try:
                    lines = log_file.read_text().splitlines()
                    context_lines = lines[-80:]
                except Exception:
                    pass

        if not context_lines:
            lines = [state.last_line] if state.last_line else []
            if state.error_msg:
                lines.append(state.error_msg)
            context_lines = lines

        if not context_lines:
            state.analysis = "no log data"
            return

        log_excerpt = "\n".join(context_lines)
        prompt = (
            f"Project: {state.name}\n"
            f"Pipeline log (last lines):\n{log_excerpt}\n\n"
            "Diagnose the main failure in ONE sentence, max 80 characters. "
            "No code, no suggestions, just diagnosis."
        )

        llm = LLM(model=model)
        response = llm.complete(
            prompt,
            system="You are a concise code quality analyst. Reply with exactly one sentence.",
            temperature=0.1,
            max_tokens=100,
        )
        analysis = response.content.strip().replace("\n", " ")
        state.analysis = analysis[:80]
    except Exception as exc:
        state.analysis = f"[llm error: {str(exc)[:40]}]"


# ---------------------------------------------------------------------------
# Single project runner (runs in a thread)
# ---------------------------------------------------------------------------

def _run_single_project(
    state: ProjectRunState,
    dry_run: bool = False,
    timeout: int = 0,
    pyqual_cmd: str = "pyqual",
    log_dir: Path | None = None,
    analyze: bool = False,
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

    # --- Pre-flight validation (fast, local, no subprocess) ---
    try:
        from pyqual.validation import Severity, validate_config
        preflight = validate_config(config_path)
        if not preflight.ok:
            state.status = RunStatus.ERROR
            first_err = preflight.errors[0]
            state.error_msg = f"[config] {first_err.code}: {first_err.message[:120]}"
            state.duration = time.monotonic() - state.start_time
            return
    except Exception:
        pass  # validation module import failed — let subprocess report the error

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

    log_fh = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / f"{state.name}.log", "w")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(state.path),
            bufsize=1,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            if log_fh is not None:
                log_fh.write(line)
                log_fh.flush()
            _parse_output_line(state, line)

        proc.wait(timeout=effective_timeout)

        state.duration = time.monotonic() - state.start_time

        if state.status == RunStatus.RUNNING:
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
    finally:
        if log_fh is not None:
            log_fh.close()

    if analyze and state.status in (RunStatus.FAILED, RunStatus.ERROR, RunStatus.TIMEOUT):
        state.analysis = "🤔 analyzing…"
        _analyze_project(state, log_dir=log_dir)


# ---------------------------------------------------------------------------
# Dashboard table builder
# ---------------------------------------------------------------------------

def _build_project_row(s: ProjectRunState, show_last_line: bool,
                        show_analysis: bool = False) -> list:
    """Build a single dashboard table row for one project state."""
    icon = STATUS_ICON.get(s.status, "?")
    style = STATUS_STYLE.get(s.status, "")
    status_text = Text(f"{icon} {s.status.value}", style=style)

    if s.max_iterations > 0 and s.status not in (RunStatus.QUEUED, RunStatus.SKIPPED):
        iter_text = f"{s.iteration}/{s.max_iterations}"
    else:
        iter_text = ""

    stage_text = s.current_stage

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

    if s.gates_total > 0:
        if s.gates_passed == s.gates_total:
            gates_text = f"[green]{s.gates_label}[/]"
        elif s.gates_passed > 0:
            gates_text = f"[yellow]{s.gates_label}[/]"
        else:
            gates_text = f"[red]{s.gates_label}[/]"
    else:
        gates_text = ""

    elapsed = s.elapsed
    if elapsed > 60:
        time_text = f"{elapsed / 60:.1f}m"
    elif elapsed > 0:
        time_text = f"{elapsed:.1f}s"
    else:
        time_text = ""

    if s.error_msg and s.status in (RunStatus.ERROR, RunStatus.TIMEOUT):
        stage_text = f"[red]{s.error_msg[:30]}[/]"

    row: list = [s.name, status_text, iter_text, stage_text, progress, gates_text, time_text]
    if show_last_line:
        row.append(s.last_line[:50] if s.last_line else "")
    if show_analysis:
        if s.analysis.startswith("🤔"):
            row.append(f"[dim]{s.analysis}[/]")
        elif s.analysis:
            color = "yellow" if s.status in (RunStatus.FAILED, RunStatus.ERROR, RunStatus.TIMEOUT) else "dim"
            row.append(f"[{color}]{s.analysis[:60]}[/]")
        else:
            row.append("")
    return row


def build_dashboard_table(
    states: list[ProjectRunState],
    *,
    show_last_line: bool = False,
    show_analysis: bool = False,
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
    if show_analysis:
        table.add_column("LLX Analysis", max_width=60, style="dim")

    for s in states:
        table.add_row(*_build_project_row(s, show_last_line, show_analysis))

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
    log_dir: Path | None = None,
    analyze: bool = False,
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
    log_dir:
        If set, save each project's output to ``log_dir/<name>.log``.
    analyze:
        If True, call LLM to diagnose each failed/error project after it finishes.
    """
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
            _run_single_project(state, dry_run=dry_run, timeout=timeout,
                                 pyqual_cmd=pyqual_cmd, log_dir=log_dir,
                                 analyze=analyze)
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
