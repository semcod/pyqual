"""Observe commands for pyqual CLI — logs, watch, history.

Extracted from ``cli.py`` to reduce its maintainability index score.
Register all three commands by calling ``register_observe_commands(app)``.
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from pyqual.cli_log_helpers import (
    format_log_entry_row as _format_log_entry_row,
    query_nfo_db as _query_nfo_db,
    row_to_event_dict as _row_to_event_dict,
)
from pyqual.constants import (
    BULK_LINE_TRUNCATE,
    LLX_HISTORY_FILE,
    PIPELINE_DB,
    TIMESTAMP_COL_WIDTH,
)

_console = Console()
_TIMESTAMP_COL_WIDTH = TIMESTAMP_COL_WIDTH


def register_observe_commands(app: typer.Typer) -> None:
    """Register logs, watch, and history commands onto *app*."""

    @app.command()
    def logs(
        workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
        tail: int = typer.Option(0, "--tail", "-n", help="Show last N entries (0 = all)."),
        level: str = typer.Option("", "--level", "-l", help="Filter by event type (stage_done, gate_check, pipeline_start, pipeline_end)."),
        stage: str = typer.Option("", "--stage", help="Filter by stage name (e.g. fix, validate)."),
        failed: bool = typer.Option(False, "--failed", "-f", help="Show only failed stages/gates."),
        show_output: bool = typer.Option(False, "--output", "-o", help="Show captured stdout/stderr for each stage."),
        json_output: bool = typer.Option(False, "--json", "-j", help="Raw JSON lines (for LLM/llx consumption)."),
        sql: str = typer.Option("", "--sql", help="Run raw SQL query against pipeline.db (advanced)."),
    ) -> None:
        """View structured pipeline logs from .pyqual/pipeline.db (nfo SQLite).

        Logs are written via nfo to SQLite during every pipeline run.
        Use --output to see captured stdout/stderr (llx prompts, vallm results, etc).
        Use --json for machine-readable output (ideal for llx auto-diagnosis).
        Use --sql for arbitrary SQL queries against the log database.

        Examples:
            pyqual logs                    # show all entries
            pyqual logs --tail 20          # last 20 entries
            pyqual logs --failed           # only failures
            pyqual logs --stage fix --output  # fix stage with full output
            pyqual logs --json --failed    # JSON failures for LLM consumption
            pyqual logs --level gate_check # only gate results
            pyqual logs --sql "SELECT * FROM pipeline_logs WHERE function_name='stage_done' AND level='WARNING'"
        """
        db_path = Path(workdir) / PIPELINE_DB
        if not db_path.exists():
            _console.print("[yellow]No pipeline log found. Run 'pyqual run' first.[/yellow]")
            raise typer.Exit(1)

        if sql:
            rows = _query_nfo_db(db_path, sql=sql)
            if json_output:
                for row in rows:
                    _console.print(json.dumps(row, default=str))
            else:
                if not rows:
                    _console.print("[dim]No results.[/dim]")
                    return
                table = Table(title=f"SQL Query ({len(rows)} rows)")
                for col in rows[0].keys():
                    table.add_column(col)
                for row in rows:
                    table.add_row(*[str(v)[:80] for v in row.values()])
                _console.print(table)
            return

        rows = _query_nfo_db(db_path, event=level, failed=failed, tail=tail,
                             stage=stage)
        entries = [_row_to_event_dict(r) for r in rows]

        if not entries:
            _console.print("[dim]No matching log entries.[/dim]")
            return

        if json_output:
            for entry in entries:
                clean = {k: v for k, v in entry.items() if not k.startswith("_")}
                _console.print(json.dumps(clean, default=str))
            return

        # Human-readable output (works in both TTY and non-TTY)
        _lc = Console(force_terminal=True, width=BULK_LINE_TRUNCATE)
        _lc.print(f"[bold]Pipeline Log[/bold] ({len(entries)} entries)\n")

        for entry in entries:
            ts, event_name, name, status_col, details = _format_log_entry_row(entry)
            _lc.print(f"  {ts}  {event_name:<14} {name:<20} {status_col:<8} {details}")

            if show_output and entry.get("_function_name") == "stage_done":
                stdout = entry.get("stdout_tail", "")
                stderr = entry.get("stderr_tail", "")
                if stdout:
                    for line in str(stdout).splitlines()[-15:]:
                        _lc.print(f"    [dim][out][/dim] {line}")
                if stderr:
                    for line in str(stderr).splitlines()[-10:]:
                        _lc.print(f"    [red][err][/red] {line}")

        _lc.print(f"\n[dim]Log DB: {db_path}[/dim]")
        _lc.print("[dim]Tip: pyqual logs --stage fix --output   # see llx prompts/output[/dim]")
        _lc.print("[dim]Tip: pyqual history --prompts            # see full LLX fix prompts[/dim]")

    @app.command()
    def watch(
        workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
        interval: float = typer.Option(1.0, "--interval", "-i", help="Poll interval in seconds."),
        show_output: bool = typer.Option(False, "--output", "-o", help="Show captured stdout/stderr."),
        show_prompts: bool = typer.Option(False, "--prompts", "-p", help="Show LLX fix prompts as they appear."),
    ) -> None:
        """Live-tail pipeline logs while 'pyqual run' executes in another terminal.

        Watches .pyqual/pipeline.db and .pyqual/llx_history.jsonl for new entries.

        Examples:
            pyqual watch                    # live tail in another terminal
            pyqual watch --output           # include stage stdout/stderr
            pyqual watch --prompts          # show llx prompts as they appear
            pyqual watch --interval 0.5     # faster polling
        """
        import time as _time

        _wc = Console(stderr=True, force_terminal=True)
        _wd = Path(workdir).resolve()
        db_path = _wd / ".pyqual" / "pipeline.db"
        history_path = _wd / ".pyqual" / "llx_history.jsonl"

        _wc.print(f"[bold]pyqual watch[/bold]  workdir={_wd}")
        _wc.print(f"[dim]Watching: {db_path}[/dim]")
        _wc.print("[dim]Press Ctrl+C to stop.[/dim]\n")

        last_db_count = 0
        last_history_lines = 0

        if db_path.exists():
            try:
                entries = _query_nfo_db(db_path)
                last_db_count = len(entries)
                _wc.print(f"[dim]({last_db_count} existing log entries)[/dim]")
            except Exception:
                pass

        if history_path.exists():
            last_history_lines = len(history_path.read_text().splitlines())

        try:
            while True:
                _time.sleep(interval)

                # Poll pipeline.db for new entries
                if db_path.exists():
                    try:
                        entries = _query_nfo_db(db_path)
                        if len(entries) > last_db_count:
                            new_entries = entries[last_db_count:]
                            last_db_count = len(entries)
                            for entry in new_entries:
                                ts, event_name, name, status_col, details = _format_log_entry_row(entry)
                                _wc.print(f"  {ts}  [bold]{event_name:<14}[/bold] {name:<20} {status_col:<8} {details}")

                                if show_output and entry.get("_function_name") == "stage_done":
                                    stdout = entry.get("stdout_tail", "")
                                    stderr = entry.get("stderr_tail", "")
                                    if stdout:
                                        for line in str(stdout).splitlines()[-10:]:
                                            _wc.print(f"    [dim][out][/dim] {line}")
                                    if stderr:
                                        for line in str(stderr).splitlines()[-5:]:
                                            _wc.print(f"    [red][err][/red] {line}")
                    except Exception:
                        pass

                # Poll llx_history.jsonl for new fix runs
                if show_prompts and history_path.exists():
                    try:
                        lines = history_path.read_text().splitlines()
                        if len(lines) > last_history_lines:
                            new_lines = lines[last_history_lines:]
                            last_history_lines = len(lines)
                            for line in new_lines:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    entry = json.loads(line)
                                    ts = entry.get("timestamp", "")[:19].replace("T", " ")
                                    model = entry.get("model", "?")
                                    issues = entry.get("issues_count", "?")
                                    _wc.print(f"\n  [bold cyan]── LLX Fix ({ts}) ──[/bold cyan]")
                                    _wc.print(f"  model={model}  issues={issues}")
                                    prompt = entry.get("prompt", "")
                                    if prompt:
                                        for pline in prompt.splitlines()[:20]:
                                            _wc.print(f"    [dim]{pline}[/dim]")
                                        if len(prompt.splitlines()) > 20:
                                            _wc.print(f"    [dim]... ({len(prompt.splitlines())} lines total)[/dim]")
                                except json.JSONDecodeError:
                                    continue
                    except Exception:
                        pass

        except KeyboardInterrupt:
            _wc.print("\n[dim]watch stopped.[/dim]")

    @app.command()
    def history(
        workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
        tail: int = typer.Option(0, "--tail", "-n", help="Show last N fix runs (0 = all)."),
        prompts: bool = typer.Option(False, "--prompts", "-p", help="Show full LLX prompts."),
        json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON lines."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show stdout/aider output."),
    ) -> None:
        """View history of LLX/LLM fix runs from .pyqual/llx_history.jsonl.

        Each time a fix stage runs during 'pyqual run', the LLX prompt, model,
        issues, result, and aider output are archived to llx_history.jsonl.

        Examples:
            pyqual history                  # summary table of all fix runs
            pyqual history --tail 5         # last 5 runs
            pyqual history --prompts        # include full LLX prompts
            pyqual history --json           # raw JSONL for LLM consumption
            pyqual history --verbose        # include aider stdout
        """
        history_path = Path(workdir) / LLX_HISTORY_FILE
        if not history_path.exists():
            _console.print("[yellow]No fix history found.[/yellow]")
            _console.print("[dim]Run 'pyqual run' with a fix stage to start recording history.[/dim]")
            raise typer.Exit(1)

        entries: list[dict] = []
        for line in history_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not entries:
            _console.print("[dim]History file is empty.[/dim]")
            raise typer.Exit(1)

        if tail > 0:
            entries = entries[-tail:]

        if json_output:
            for entry in entries:
                _console.print(json.dumps(entry, default=str, ensure_ascii=False))
            return

        # Human-readable table
        table = Table(title=f"LLX Fix History ({len(entries)} runs)")
        table.add_column("Time", style="dim", width=_TIMESTAMP_COL_WIDTH)
        table.add_column("Stage", width=10)
        table.add_column("Model", width=28)
        table.add_column("Issues", justify="right", width=6)
        table.add_column("Result", width=10)
        table.add_column("Duration", justify="right", width=8)

        for entry in entries:
            ts = entry.get("timestamp", "")[:TIMESTAMP_COL_WIDTH].replace("T", " ")
            stage = entry.get("stage", "")
            model = entry.get("model", "")
            issues = str(entry.get("issues_count", "?"))
            ok = entry.get("ok") if entry.get("ok") is not None else entry.get("success")
            if ok is True:
                result = "[green]✅ pass[/green]"
            elif ok is False:
                result = "[red]❌ fail[/red]"
            else:
                result = "[dim]?[/dim]"
            dur = entry.get("duration_s")
            dur_s = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "?"
            table.add_row(ts, stage, model, issues, result, dur_s)

        _console.print(table)

        if prompts:
            _console.print()
            for i, entry in enumerate(entries):
                prompt = entry.get("prompt", "")
                if prompt:
                    ts = entry.get("timestamp", "")[:19].replace("T", " ")
                    _console.print(f"\n[bold]── Run {i+1} ({ts}) ──[/bold]")
                    _console.print(Syntax(prompt, "text", theme="monokai", background_color="default",
                                         word_wrap=True))

        if verbose:
            _console.print()
            for i, entry in enumerate(entries):
                stdout = entry.get("stdout_tail", "")
                if stdout:
                    ts = entry.get("timestamp", "")[:19].replace("T", " ")
                    _console.print(f"\n[bold]── Stdout {i+1} ({ts}) ──[/bold]")
                    _console.print(Syntax(stdout, "text", theme="monokai", background_color="default",
                                         word_wrap=True))

        # Summary line
        total = len(entries)
        passed = sum(1 for e in entries if e.get("ok") is True or e.get("success") is True)
        failed = sum(1 for e in entries if e.get("ok") is False or e.get("success") is False)
        models = set(e.get("model", "") for e in entries if e.get("model"))
        _console.print(f"\n[bold]Summary:[/bold] {total} runs, {passed} passed, {failed} failed"
                       f" | Models: {', '.join(sorted(models)) or '?'}")
        _console.print(f"[dim]History: {history_path}[/dim]")
