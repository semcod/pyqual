"""Bulk commands for pyqual CLI — bulk-init and bulk-run.

Extracted from ``cli.py`` to reduce its maintainability index score.
Register both commands by calling ``register_bulk_commands(app)``.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from pyqual.constants import BULK_PASS_PREVIEW

_console = Console()
_BULK_PASS_PREVIEW = BULK_PASS_PREVIEW


def _bulk_init_impl(
    path: Path,
    dry_run: bool,
    no_llm: bool,
    model: str | None,
    overwrite: bool,
    show_schema: bool,
    json_output: bool,
) -> None:
    """Implementation of bulk-init command."""
    from pyqual.bulk_init import (
        PROJECT_CONFIG_SCHEMA,
        bulk_init,
    )
    from rich.table import Table

    if show_schema:
        _console.print(json.dumps(PROJECT_CONFIG_SCHEMA, indent=2))
        return

    if not path.is_dir():
        _console.print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    mode = "heuristic" if no_llm else "LLM"
    _console.print(f"[bold]Bulk init[/bold]: scanning [cyan]{path}[/cyan] ({mode} classification)")
    if dry_run:
        _console.print("[yellow]DRY RUN — no files will be written[/yellow]")
    _console.print()

    result = bulk_init(
        root=path,
        use_llm=not no_llm,
        model=model,
        dry_run=dry_run,
        overwrite=overwrite,
    )

    if json_output:
        _console.print(json.dumps({
            "created": result.created,
            "skipped_existing": result.skipped_existing,
            "skipped_nonproject": result.skipped_nonproject,
            "errors": result.errors,
        }, indent=2, ensure_ascii=False))
        return

    # Created
    if result.created:
        table = Table(title=f"{'Would create' if dry_run else 'Created'} ({len(result.created)})")
        table.add_column("Project")
        for name in result.created:
            table.add_row(name)
        _console.print(table)

    # Skipped (existing)
    if result.skipped_existing:
        _console.print(f"\n[dim]Skipped (existing pyqual.yaml): {', '.join(result.skipped_existing)}[/dim]")

    # Skipped (non-project)
    if result.skipped_nonproject:
        _console.print("\n[dim]Skipped (non-project):[/dim]")
        for name, reason in result.skipped_nonproject:
            _console.print(f"  [dim]{name}: {reason}[/dim]")

    # Errors
    if result.errors:
        _console.print()
        for name, err in result.errors:
            _console.print(f"  [red]✗ {name}: {err}[/red]")

    _console.print(f"\n[bold]Total: {result.total}[/bold] "
                   f"(created: {len(result.created)}, "
                   f"existing: {len(result.skipped_existing)}, "
                   f"skipped: {len(result.skipped_nonproject)}, "
                   f"errors: {len(result.errors)})")


def _bulk_run_impl(
    path: Path,
    parallel: int,
    dry_run: bool,
    timeout: int,
    filter_name: list[str],
    no_live: bool,
    verbose: bool,
    json_output: bool,
    log_dir: Path | None,
    analyze: bool,
) -> None:
    """Implementation of bulk-run command."""
    from rich.live import Live

    from pyqual.bulk_run import (
        BulkRunResult,
        build_dashboard_table,
        bulk_run,
        discover_projects,
    )

    if not path.is_dir():
        _console.print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    # Discover projects
    all_states = discover_projects(path)
    if not all_states:
        _console.print(f"[yellow]No projects with pyqual.yaml found in {path}[/yellow]")
        raise typer.Exit(1)

    _console.print(f"[bold]Bulk run[/bold]: {len(all_states)} projects in [cyan]{path}[/cyan]"
                   f" (parallel={parallel})")
    if dry_run:
        _console.print("[yellow]DRY RUN mode[/yellow]")
    _console.print()

    if log_dir:
        _console.print(f"[dim]Logs → {log_dir}/[/dim]")
    if analyze:
        _console.print("[dim]LLX analysis enabled for failed projects.[/dim]")

    if no_live:
        # No live dashboard — just run and print summary
        result = bulk_run(
            root=path,
            parallel=parallel,
            dry_run=dry_run,
            timeout=timeout,
            filter_names=filter_name or None,
            log_dir=log_dir,
            analyze=analyze,
        )
    else:
        # Live dashboard
        _live_result: list[BulkRunResult] = []

        def _run_with_live(live: Live, states_ref: list) -> BulkRunResult:
            def _refresh(states):
                states_ref.clear()
                states_ref.extend(states)
                live.update(build_dashboard_table(states, show_last_line=verbose,
                                                  show_analysis=analyze))

            return bulk_run(
                root=path,
                parallel=parallel,
                dry_run=dry_run,
                timeout=timeout,
                filter_names=filter_name or None,
                live_callback=_refresh,
                log_dir=log_dir,
                analyze=analyze,
            )

        states_ref: list = []
        with Live(build_dashboard_table(all_states, show_last_line=verbose,
                                        show_analysis=analyze),
                  console=_console, refresh_per_second=2) as live:
            result = _run_with_live(live, states_ref)
            # Final update
            if states_ref:
                live.update(build_dashboard_table(states_ref, show_last_line=verbose,
                                                  show_analysis=analyze))

    if json_output:
        _console.print(json.dumps({
            "passed": result.passed,
            "failed": result.failed,
            "errors": result.errors,
            "skipped": result.skipped,
            "total_duration": round(result.total_duration, 1),
        }, indent=2, ensure_ascii=False))
        return

    # Final summary
    _console.print()
    if result.passed:
        more = f" +{len(result.passed)-_BULK_PASS_PREVIEW} more" if len(result.passed) > _BULK_PASS_PREVIEW else ""
        _console.print(f"[green]✅ Passed ({len(result.passed)}):[/green] {', '.join(result.passed[:_BULK_PASS_PREVIEW])}{more}")
    if result.failed:
        _console.print(f"[red]❌ Failed ({len(result.failed)}):[/red] {', '.join(result.failed)}")
    if result.errors:
        _console.print(f"[red]💥 Errors ({len(result.errors)}):[/red]")
        for name, err in result.errors:
            _console.print(f"  {name}: {err}")
    if result.skipped:
        more_s = f" +{len(result.skipped)-10} more" if len(result.skipped) > 10 else ""
        _console.print(f"[dim]⏭ Skipped ({len(result.skipped)}): {', '.join(result.skipped[:10])}{more_s}[/dim]")

    _console.print(f"\n[bold]Total time: {result.total_duration:.1f}s[/bold]")

    if result.failed or result.errors:
        raise typer.Exit(1)


def register_bulk_commands(app: typer.Typer) -> None:
    """Register bulk-init and bulk-run commands onto *app*."""

    @app.command("bulk-init")
    def bulk_init_cmd(
        path: Path = typer.Argument(..., help="Parent directory whose subdirectories are projects."),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be generated without writing files."),
        no_llm: bool = typer.Option(False, "--no-llm", help="Use heuristic classification only (no LLM calls)."),
        model: str | None = typer.Option(None, "--model", "-m", help="Override LLM model for classification."),
        overwrite: bool = typer.Option(False, "--overwrite", help="Regenerate pyqual.yaml even if one already exists."),
        show_schema: bool = typer.Option(False, "--show-schema", help="Print the JSON schema used for LLM classification and exit."),
        json_output: bool = typer.Option(False, "--json", "-j", help="Output results as JSON."),
    ) -> None:
        """Bulk-generate pyqual.yaml for every project in a directory."""
        _bulk_init_impl(path, dry_run, no_llm, model, overwrite, show_schema, json_output)

    @app.command("bulk-run")
    def bulk_run_cmd(
        path: Path = typer.Argument(..., help="Parent directory whose subdirectories are projects."),
        parallel: int = typer.Option(4, "--parallel", "-p", help="Max concurrent pyqual processes."),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Pass --dry-run to each pyqual run."),
        timeout: int = typer.Option(0, "--timeout", "-t", help="Per-project timeout in seconds (0 = no limit)."),
        filter_name: list[str] = typer.Option([], "--filter", "-f", help="Only run these project names (repeatable)."),
        no_live: bool = typer.Option(False, "--no-live", help="Disable live dashboard, print final summary only."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show last output line per project in dashboard."),
        json_output: bool = typer.Option(False, "--json", "-j", help="Output final results as JSON."),
        log_dir: Path | None = typer.Option(None, "--log-dir", "-l", help="Save per-project output to LOG_DIR/<name>.log."),
        analyze: bool = typer.Option(False, "--analyze", "-a", help="Call LLX/LLM to diagnose each failed project (adds LLX Analysis column)."),
    ) -> None:
        """Run pyqual across all projects with a real-time dashboard."""
        _bulk_run_impl(path, parallel, dry_run, timeout, filter_name, no_live, verbose, json_output, log_dir, analyze)
