"""CLI for pyqual — declarative quality gate loops."""

import asyncio
import json
import logging
import shutil

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from pyqual.cli_log_helpers import (
    format_log_entry_row as _format_log_entry_row,
    query_nfo_db as _query_nfo_db,
    row_to_event_dict as _row_to_event_dict,
)
from pyqual.cli_run_helpers import (
    build_run_summary as _build_run_summary,
    enrich_from_artifacts as _enrich_from_artifacts,
    extract_stage_summary as _extract_stage_summary,
    format_run_summary as _format_run_summary,
    get_last_error_line as _get_last_error_line,
    infer_fix_result as _infer_fix_result,
)
from pyqual.config import PyqualConfig
from pyqual.constants import (
    BULK_LINE_TRUNCATE,
    DEFAULT_MCP_PORT,
    STATUS_COLUMN_WIDTH,
)
from pyqual.gates import GateSet
try:
    from pyqual.integrations.llx_mcp import run_llx_fix_workflow
    from pyqual.integrations.llx_mcp import run_llx_refactor_workflow
except Exception:  # pragma: no cover - llx MCP modules are optional
    run_llx_fix_workflow = None  # type: ignore[assignment]
    run_llx_refactor_workflow = None  # type: ignore[assignment]

try:
    from pyqual.integrations.llx_mcp_service import run_server as run_llx_mcp_service
except Exception:  # pragma: no cover
    run_llx_mcp_service = None  # type: ignore[assignment]
from pyqual.pipeline import Pipeline
from pyqual.plugins import get_available_plugins
from pyqual.tickets import sync_all_tickets
from pyqual.tickets import sync_github_tickets
from pyqual.tickets import sync_todo_tickets
from pyqual.validation import EC, ErrorDomain, Severity, detect_project_facts, validate_config

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"
_TIMESTAMP_COL_WIDTH = 19  # "YYYY-MM-DD HH:MM:SS"
_BULK_PASS_PREVIEW = 20    # max passed-gate names to show inline

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()
stderr_console = Console(stderr=True)
tickets_app = typer.Typer(help="Control planfile-backed tickets from TODO.md and GitHub.")
app.add_typer(tickets_app, name="tickets")


def _setup_logging(verbose: bool, workdir: Path = Path(".")) -> None:
    """Configure Python logging for pyqual.pipeline.

    Always writes structured JSON lines to .pyqual/pipeline.log (handled by Pipeline).
    With --verbose, also prints human-readable lines to stderr.
    """
    logger = logging.getLogger("pyqual")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    if verbose:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory"),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Use a built-in profile (e.g. python, python-full, ci, lint-only, security). See 'pyqual profiles'."),
) -> None:
    """Create pyqual.yaml with sensible defaults.

    Use --profile for a minimal config based on a built-in profile:

        pyqual init --profile python          # 6-line YAML
        pyqual init --profile python-full     # includes push & publish
        pyqual init --profile ci              # report-only, no fix
    """
    target = path / "pyqual.yaml"
    if target.exists():
        overwrite = typer.confirm(f"{target} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    if profile:
        from pyqual.profiles import get_profile, list_profiles
        prof = get_profile(profile)
        if prof is None:
            console.print(f"[red]Unknown profile '{profile}'.[/red]")
            console.print(f"Available: {', '.join(list_profiles())}")
            raise typer.Exit(1)
        yaml_content = f"""\
pipeline:
  profile: {profile}

  # Override metrics (profile defaults: {', '.join(f'{k}={v}' for k, v in prof.metrics.items())}):
  # metrics:
  #   coverage_min: 55

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
"""
        target.write_text(yaml_content)
    else:
        target.write_text(PyqualConfig.default_yaml())

    (path / ".pyqual").mkdir(exist_ok=True)
    console.print(f"[green]Created {target}[/green]")
    if profile:
        console.print(f"Using profile [bold]{profile}[/bold]: {prof.description}")
    console.print("Run: [bold]pyqual run[/bold]")


@app.command()
def profiles() -> None:
    """List available pipeline profiles for pyqual.yaml.

    Profiles provide pre-configured stage lists and metrics so you can write
    a minimal pyqual.yaml:

        pipeline:
          profile: python
          metrics:
            coverage_min: 55    # override only what you need
    """
    from pyqual.profiles import PROFILES

    table = Table(title="Available Profiles", show_lines=True)
    table.add_column("Profile", style="bold cyan")
    table.add_column("Description")
    table.add_column("Stages", style="dim")
    table.add_column("Gates", style="dim")

    for name, prof in sorted(PROFILES.items()):
        stage_names = ", ".join(s["name"] for s in prof.stages)
        gate_names = ", ".join(prof.metrics.keys()) if prof.metrics else "—"
        table.add_row(name, prof.description, stage_names, gate_names)

    console.print(table)
    console.print("\n[dim]Usage: set 'profile: <name>' in pyqual.yaml under pipeline:[/dim]")


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
    """Bulk-generate pyqual.yaml for every project in a directory.

    Scans each subdirectory of PATH, detects the project type (via LLM or
    heuristics), and generates a tailored pyqual.yaml with appropriate stages,
    tools, and metrics.

    Examples:
        pyqual bulk-init /path/to/workspace
        pyqual bulk-init /path/to/workspace --dry-run
        pyqual bulk-init /path/to/workspace --no-llm
        pyqual bulk-init /path/to/workspace --show-schema
    """
    from pyqual.bulk_init import (
        PROJECT_CONFIG_SCHEMA,
        BulkInitResult,
        bulk_init,
    )

    if show_schema:
        console.print(json.dumps(PROJECT_CONFIG_SCHEMA, indent=2))
        return

    if not path.is_dir():
        console.print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    mode = "heuristic" if no_llm else "LLM"
    console.print(f"[bold]Bulk init[/bold]: scanning [cyan]{path}[/cyan] ({mode} classification)")
    if dry_run:
        console.print("[yellow]DRY RUN — no files will be written[/yellow]")
    console.print()

    result = bulk_init(
        root=path,
        use_llm=not no_llm,
        model=model,
        dry_run=dry_run,
        overwrite=overwrite,
    )

    if json_output:
        console.print(json.dumps({
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
        console.print(table)

    # Skipped (existing)
    if result.skipped_existing:
        console.print(f"\n[dim]Skipped (existing pyqual.yaml): {', '.join(result.skipped_existing)}[/dim]")

    # Skipped (non-project)
    if result.skipped_nonproject:
        console.print(f"\n[dim]Skipped (non-project):[/dim]")
        for name, reason in result.skipped_nonproject:
            console.print(f"  [dim]{name}: {reason}[/dim]")

    # Errors
    if result.errors:
        console.print()
        for name, err in result.errors:
            console.print(f"  [red]✗ {name}: {err}[/red]")

    console.print(f"\n[bold]Total: {result.total}[/bold] "
                  f"(created: {len(result.created)}, "
                  f"existing: {len(result.skipped_existing)}, "
                  f"skipped: {len(result.skipped_nonproject)}, "
                  f"errors: {len(result.errors)})")


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
    """Run pyqual across all projects with a real-time dashboard.

    Discovers all subdirectories of PATH that contain pyqual.yaml and runs
    ``pyqual run`` in each one, up to --parallel at a time.  A live-updating
    table shows status, iteration, current stage, gates, and elapsed time.

    Examples:
        pyqual bulk-run /path/to/workspace
        pyqual bulk-run /path/to/workspace --parallel 8
        pyqual bulk-run /path/to/workspace --dry-run
        pyqual bulk-run /path/to/workspace --filter mylib --filter webapp
        pyqual bulk-run /path/to/workspace --timeout 600
        pyqual bulk-run /path/to/workspace --log-dir /tmp/bulk-logs
        pyqual bulk-run /path/to/workspace --analyze
        pyqual bulk-run /path/to/workspace --analyze --log-dir /tmp/logs
    """
    from rich.live import Live

    from pyqual.bulk_run import (
        BulkRunResult,
        RunStatus,
        build_dashboard_table,
        bulk_run,
        discover_projects,
    )

    if not path.is_dir():
        console.print(f"[red]Not a directory: {path}[/red]")
        raise typer.Exit(1)

    # Discover projects
    all_states = discover_projects(path)
    if not all_states:
        console.print(f"[yellow]No projects with pyqual.yaml found in {path}[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Bulk run[/bold]: {len(all_states)} projects in [cyan]{path}[/cyan]"
                  f" (parallel={parallel})")
    if dry_run:
        console.print("[yellow]DRY RUN mode[/yellow]")
    console.print()

    if log_dir:
        console.print(f"[dim]Logs → {log_dir}/[/dim]")
    if analyze:
        console.print("[dim]LLX analysis enabled for failed projects.[/dim]")

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
                  console=console, refresh_per_second=2) as live:
            result = _run_with_live(live, states_ref)
            # Final update
            if states_ref:
                live.update(build_dashboard_table(states_ref, show_last_line=verbose,
                                                  show_analysis=analyze))

    if json_output:
        console.print(json.dumps({
            "passed": result.passed,
            "failed": result.failed,
            "errors": result.errors,
            "skipped": result.skipped,
            "total_duration": round(result.total_duration, 1),
        }, indent=2, ensure_ascii=False))
        return

    # Final summary
    console.print()
    if result.passed:
        more = f" +{len(result.passed)-_BULK_PASS_PREVIEW} more" if len(result.passed) > _BULK_PASS_PREVIEW else ""
        console.print(f"[green]✅ Passed ({len(result.passed)}):[/green] {', '.join(result.passed[:_BULK_PASS_PREVIEW])}{more}")
    if result.failed:
        console.print(f"[red]❌ Failed ({len(result.failed)}):[/red] {', '.join(result.failed)}")
    if result.errors:
        console.print(f"[red]💥 Errors ({len(result.errors)}):[/red]")
        for name, err in result.errors:
            console.print(f"  {name}: {err}")
    if result.skipped:
        more_s = f" +{len(result.skipped)-10} more" if len(result.skipped) > 10 else ""
        console.print(f"[dim]⏭ Skipped ({len(result.skipped)}): {', '.join(result.skipped[:10])}{more_s}[/dim]")

    console.print(f"\n[bold]Total time: {result.total_duration:.1f}s[/bold]")

    if result.failed or result.errors:
        raise typer.Exit(1)


@app.command()
def run(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show live pipeline log output."),
    stream: bool = typer.Option(False, "--stream", "-s",
                                help="Stream stage stdout/stderr in real-time (shows llx prompts, vallm output, etc)."),
    auto_fix_config: bool = typer.Option(False, "--auto-fix-config",
                                         help="Auto-repair pyqual.yaml when ENV/CONFIG errors are detected."),
) -> None:
    """Execute pipeline loop until quality gates pass.

    Output is streamed as YAML to stdout as each stage completes.
    Diagnostic messages go to stderr.
    """
    import sys
    _setup_logging(verbose, workdir)
    cfg = PyqualConfig.load(config)

    _workdir = Path(workdir).resolve()
    _config_path = (_workdir / config) if not Path(config).is_absolute() else Path(config)

    _sc = stderr_console
    import pyqual as _pq
    import yaml as _yaml
    _ver = getattr(_pq, "__version__", "?")
    op_sym = {"le": "<=", "ge": ">=", "lt": "<", "gt": ">", "eq": "=="}

    # ── Streaming state ──
    _iter_stages: list[dict[str, Any]] = []
    _all_iterations: list[dict[str, Any]] = []

    def _emit(text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def _emit_yaml_items(items: list[dict], indent: int = 0) -> None:
        fragment = _yaml.safe_dump(items, default_flow_style=False,
                                    sort_keys=False, allow_unicode=True)
        prefix = " " * indent
        for line in fragment.rstrip().splitlines():
            _emit(f"{prefix}{line}\n")

    # ── Emit YAML preamble ──
    _emit(f"pyqual: {_ver}\n")
    _emit(f"config: {config}\n")
    _emit(f"workdir: {_workdir}\n")
    _emit("iterations:\n")

    def _on_iter_start(num: int) -> None:
        _iter_stages.clear()
        _emit(f"- iteration: {num}\n")
        _emit("  stages:\n")

    def _on_stage_start(name: str) -> None:
        pass  # YAML streaming is the progress indicator; use `pyqual watch` for live logs

    def _on_stage_done(result: Any) -> None:
        sd: dict[str, Any] = {"name": result.name}
        if result.skipped:
            sd["status"] = "skipped"
        else:
            sd["status"] = "passed" if result.passed else "failed"
            sd["duration"] = round(result.duration, 1)
            metrics = _extract_stage_summary(result.name, result.stdout, result.stderr)
            sd.update(metrics)
            if not result.passed:
                sd["rc"] = result.returncode
                err = _get_last_error_line(result.stderr or result.stdout or "")
                if err:
                    sd["stderr"] = err
        _enrich_from_artifacts(_workdir, [sd])
        _iter_stages.append(sd)
        _emit_yaml_items([sd], indent=2)

    def _on_iteration_done(iteration: Any) -> None:
        gate_dicts: list[dict[str, Any]] = []
        for gate in iteration.gates:
            gate_dicts.append({
                "metric": gate.metric,
                "value": round(gate.value, 1) if gate.value is not None else None,
                "threshold": gate.threshold,
                "operator": op_sym.get(gate.operator, gate.operator),
                "passed": gate.passed,
            })
        _emit("  gates:\n")
        _emit_yaml_items(gate_dicts, indent=2)
        _emit(f"  all_gates_passed: {'true' if iteration.all_gates_passed else 'false'}\n")
        _all_iterations.append({
            "iteration": iteration.iteration,
            "stages": list(_iter_stages),
            "gates": gate_dicts,
            "all_gates_passed": iteration.all_gates_passed,
        })

    def _on_stage_error(failure: Any) -> None:  # failure: StageFailure
        code = failure.error_code
        domain = failure.domain

        if domain == ErrorDomain.CONFIG or domain == ErrorDomain.ENV:
            _sc.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                      f"  rc={failure.returncode}")
            _sc.print("  [yellow]→ Detected CONFIG/ENV problem — running pre-flight diagnostics…[/yellow]")
            diag = validate_config(_config_path)
            if diag.issues:
                for issue in diag.issues:
                    badge = "[red]ERR [/]" if issue.severity.value == "error" else "[yellow]WARN[/]"
                    _sc.print(f"    {badge}  {issue.code}  {issue.message}")
                    if issue.suggestion:
                        _sc.print(f"         [dim]→ {issue.suggestion}[/dim]")
                if auto_fix_config and diag.errors:
                    _sc.print("\n  [yellow]--auto-fix-config: attempting LLM repair of pyqual.yaml…[/yellow]")
                    _run_auto_fix_config(_config_path, _workdir, diag)
            else:
                _sc.print("  [dim]Pre-flight: config looks valid — problem is runtime environment.[/dim]")
                if failure.stderr:
                    _sc.print(f"  [dim]stderr: {failure.stderr[:200]}[/dim]")
            _sc.print()

        elif domain == ErrorDomain.LLM:
            _sc.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                      f"  rc={failure.returncode}")
            _sc.print("  [yellow]→ LLM/fix-stage problem.[/yellow]")
            if code == EC.LLM_API_KEY_MISSING:
                _sc.print("  [red]API key missing.[/red] Set OPENROUTER_API_KEY in .env or environment.")
            elif code == EC.LLM_NETWORK_ERROR:
                _sc.print("  [red]Network error.[/red] Check connectivity to the LLM endpoint.")
            elif code == EC.LLM_FIX_FAILED:
                _sc.print("  [dim]Fix stage failed — project code may be too complex for one pass.[/dim]")
            if failure.stderr:
                _sc.print(f"  [dim]{failure.stderr[:200]}[/dim]")
            _sc.print()

        elif domain == ErrorDomain.PIPELINE:
            _sc.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                      f"  rc={failure.returncode}")
            if code == EC.PIPELINE_TIMEOUT:
                _sc.print(f"  [red]Stage timed out[/red] after {failure.duration:.0f}s."
                          " Increase 'timeout:' in the stage config.")
            else:
                _sc.print(f"  [red]Pipeline execution error.[/red]  {failure.stderr[:200]}")
            _sc.print()

        elif domain == ErrorDomain.PROJECT:
            pass  # expected — fix stage handles project issues; visible in YAML as status: failed

    def _run_auto_fix_config(cfg_path: Path, wd: Path, diag: Any) -> None:
        from pyqual.llm import LLM
        facts = detect_project_facts(wd)
        issues_text = "\n".join(
            f"  [{i.severity.value.upper()}] {i.code}: {i.message}"
            + (f" → {i.suggestion}" if i.suggestion else "")
            for i in diag.issues
        )
        prompt = (
            f"Fix this pyqual.yaml to resolve all validation errors.\n\n"
            f"Available tools on PATH: {', '.join(facts.get('available_tools', []))}\n"
            f"Language: {facts.get('lang', 'unknown')}\n\n"
            f"Current config:\n{facts.get('current_config', '')}\n\n"
            f"Issues:\n{issues_text}\n\n"
            "Output ONLY corrected YAML, no fences, no explanation."
        )
        try:
            llm = LLM()
            resp = llm.complete(prompt, temperature=0.1, max_tokens=1200)
            new_yaml = resp.content.strip()
            if new_yaml.startswith("```"):
                new_yaml = "\n".join(l for l in new_yaml.splitlines()
                                     if not l.startswith("```")).strip()
            backup = cfg_path.with_suffix(".yaml.bak")
            cfg_path.rename(backup)
            cfg_path.write_text(new_yaml)
            _sc.print(f"  [green]pyqual.yaml rewritten[/green] (backup: {backup.name})")
            _sc.print("  [dim]Re-run 'pyqual run' to continue with the fixed config.[/dim]")
        except Exception as exc:
            _sc.print(f"  [red]Auto-fix failed: {exc}[/red]")

    def _on_stage_output(name: str, line: str, is_stderr: bool) -> None:
        tag = "err" if is_stderr else "out"
        _sc.print(f"  [dim][{name}:{tag}][/dim] {line}")

    pipeline = Pipeline(cfg, workdir,
                        on_stage_start=_on_stage_start,
                        on_iteration_start=_on_iter_start,
                        on_stage_error=_on_stage_error,
                        on_stage_done=_on_stage_done,
                        on_stage_output=_on_stage_output if (stream or verbose) else None,
                        stream=stream or verbose,
                        on_iteration_done=_on_iteration_done)
    result = pipeline.run(dry_run=dry_run)

    # ── Emit final YAML fields ──
    # If callbacks weren't fired (e.g. no iterations), rebuild from result
    if not _all_iterations and result.iterations:
        for iteration in result.iterations:
            iter_stages = []
            for stage in iteration.stages:
                sd: dict[str, Any] = {"name": stage.name}
                if stage.skipped:
                    sd["status"] = "skipped"
                else:
                    sd["status"] = "passed" if stage.passed else "failed"
                    sd["duration"] = round(stage.duration, 1)
                    metrics = _extract_stage_summary(stage.name, stage.stdout, stage.stderr)
                    sd.update(metrics)
                    if not stage.passed:
                        sd["rc"] = stage.returncode
                        err = _get_last_error_line(stage.stderr or stage.stdout or "")
                        if err:
                            sd["stderr"] = err
                _enrich_from_artifacts(_workdir, [sd])
                iter_stages.append(sd)
                _emit_yaml_items([sd], indent=2)
            gate_dicts = [{
                "metric": g.metric,
                "value": round(g.value, 1) if g.value is not None else None,
                "threshold": g.threshold,
                "operator": op_sym.get(g.operator, g.operator),
                "passed": g.passed,
            } for g in iteration.gates]
            if gate_dicts:
                _emit("  gates:\n")
                _emit_yaml_items(gate_dicts, indent=2)
            _emit(f"  all_gates_passed: {'true' if iteration.all_gates_passed else 'false'}\n")
            _all_iterations.append({
                "iteration": iteration.iteration,
                "stages": iter_stages,
                "gates": gate_dicts,
                "all_gates_passed": iteration.all_gates_passed,
            })

    _emit(f"result: {'all_gates_passed' if result.final_passed else 'gates_not_met'}\n")
    _emit(f"total_time: {round(result.total_duration, 1)}\n")

    report = {"iterations": _all_iterations}
    summary = _build_run_summary(report)
    if summary:
        _emit(_yaml.safe_dump({"summary": summary}, default_flow_style=False,
                               sort_keys=False, allow_unicode=True))

    summary_text = _format_run_summary(summary)
    if summary_text:
        _sc.print(f"\n{summary_text}")

    if not result.final_passed:
        if cfg.loop.on_fail == "create_ticket":
            _sc.print("[yellow]Creating planfile tickets from TODO.md...[/yellow]")
            try:
                sync_todo_tickets(workdir=workdir, dry_run=False, direction="from")
            except RuntimeError as exc:
                _sc.print(f"[red]{exc}[/red]")
                raise typer.Exit(1)
        raise typer.Exit(1)


@app.command()
def gates(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
) -> None:
    """Check quality gates without running stages."""
    cfg = PyqualConfig.load(config)
    gate_set = GateSet(cfg.gates)
    results = gate_set.check_all(Path(workdir))

    table = Table(title="Quality gates")
    table.add_column("Status", width=4)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Threshold", justify="right")

    for r in results:
        icon = "✅" if r.passed else "❌"
        val = f"{r.value:.1f}" if r.value is not None else "N/A"
        op = {"le": "≤", "ge": "≥", "lt": "<", "gt": ">", "eq": "="}.get(r.operator, "?")
        table.add_row(icon, r.metric, val, f"{op} {r.threshold}")

    console.print(table)

    passed = all(r.passed for r in results)
    if passed:
        console.print("[bold green]All gates pass.[/bold green]")
    else:
        console.print("[bold red]Some gates fail.[/bold red]")
        raise typer.Exit(1)


@app.command()
def validate(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    strict: bool = typer.Option(False, "--strict", "-s", help="Exit 1 on warnings too."),
) -> None:
    """Validate pyqual.yaml without running the pipeline.

    Checks for:
    - YAML parse errors
    - Unknown or missing tool binaries
    - Gate metric names that no collector produces
    - Stage configuration mistakes

    Examples:
        pyqual validate
        pyqual validate --config path/to/pyqual.yaml
        pyqual validate --strict
    """
    cfg_path = Path(workdir) / config if not Path(config).is_absolute() else Path(config)
    result = validate_config(cfg_path)

    SEV_STYLE = {
        Severity.ERROR:   ("[bold red]ERROR  [/]", "red"),
        Severity.WARNING: ("[yellow]WARNING[/]", "yellow"),
        Severity.INFO:    ("[dim]INFO   [/]", "dim"),
    }

    if not result.issues:
        console.print(f"[bold green]✅ {cfg_path.name} is valid.[/bold green]"
                      f" ({result.stages_checked} stages, {result.gates_checked} gates)")
        return

    console.print(f"[bold]Validating {cfg_path.name}[/bold]"
                  f" — {result.stages_checked} stages, {result.gates_checked} gates\n")

    for issue in result.issues:
        badge, style = SEV_STYLE[issue.severity]
        location = f" [dim][{issue.stage}][/dim]" if issue.stage else ""
        console.print(f"  {badge}{location}  [{style}]{issue.message}[/{style}]")
        if issue.suggestion:
            console.print(f"          [dim]→ {issue.suggestion}[/dim]")

    console.print()
    nerr = len(result.errors)
    nwarn = len(result.warnings)
    if nerr:
        suffix = f", {nwarn} warning(s)" if nwarn else ""
        console.print(f"[bold red]{nerr} error(s)[/bold red]{suffix} — pipeline cannot start.")
        raise typer.Exit(1)
    if nwarn:
        console.print(f"[yellow]{nwarn} warning(s)[/yellow] — pipeline may behave unexpectedly.")
        if strict:
            raise typer.Exit(1)


@app.command("fix-config")
def fix_config(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Print proposed config, do not write."),
    model: str | None = typer.Option(None, "--model", "-m", help="Override LLM model."),
) -> None:
    """Use LLM to auto-repair pyqual.yaml based on project structure.

    Scans the project (language, available tools, test framework) and asks the
    LLM to produce a corrected pyqual.yaml that matches the actual project.
    Validation issues are included in the prompt so the LLM knows what to fix.

    Examples:
        pyqual fix-config
        pyqual fix-config --dry-run
        pyqual fix-config --workdir /path/to/project
    """
    from pyqual.llm import LLM

    workdir_path = Path(workdir).resolve()
    cfg_path = workdir_path / config if not Path(config).is_absolute() else Path(config)

    validation = validate_config(cfg_path)
    facts = detect_project_facts(workdir_path)

    if validation.ok and not validation.warnings:
        console.print("[bold green]✅ Config is already valid — nothing to fix.[/bold green]")
        return

    issues_text = "\n".join(
        f"  [{i.severity.value.upper()}] {i.message}"
        + (f" → {i.suggestion}" if i.suggestion else "")
        for i in validation.issues
    )

    available_tools = ", ".join(facts.get("available_tools", [])) or "none detected"
    current_config = facts.get("current_config", "(file missing)")

    prompt = f"""You are a pyqual configuration expert.

Project facts:
  Language: {facts.get("lang", "unknown")}
  Has tests: {facts.get("has_tests", False)}
  Tools available on PATH: {available_tools}

Current pyqual.yaml:
{current_config}

Validation issues found:
{issues_text}

Fix the pyqual.yaml to resolve all issues above.
Rules:
- Only use tool presets that are available on PATH (listed above).
- Use 'run:' for any command not in the tool preset list.
- Keep stages that work correctly; only fix broken ones.
- Output ONLY the corrected YAML content, no explanation, no markdown fences.
"""

    console.print(f"[bold]Asking LLM to fix {cfg_path.name}…[/bold]")
    console.print(f"[dim]Issues: {len(validation.issues)} | Lang: {facts.get('lang')} | Tools: {available_tools}[/dim]\n")

    try:
        llm = LLM(model=model)
        response = llm.complete(prompt, temperature=0.1, max_tokens=1500)
    except Exception as exc:
        console.print(f"[red]LLM error: {exc}[/red]")
        raise typer.Exit(1)

    new_yaml = response.content.strip()
    if new_yaml.startswith("```"):
        lines = new_yaml.splitlines()
        new_yaml = "\n".join(
            l for l in lines
            if not l.startswith("```")
        ).strip()

    console.print(new_yaml)
    console.print()

    if dry_run:
        console.print("[yellow]--dry-run: not writing.[/yellow]")
        return

    backup = cfg_path.with_suffix(".yaml.bak")
    cfg_path.rename(backup)
    cfg_path.write_text(new_yaml)
    console.print(f"[green]Written to {cfg_path}[/green] (backup: {backup.name})")

    re_check = validate_config(cfg_path)
    if re_check.ok:
        console.print("[bold green]✅ Re-validation passed.[/bold green]")
    else:
        console.print(f"[yellow]{len(re_check.errors)} issue(s) remain — review manually.[/yellow]")


@app.command()
def status(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
) -> None:
    """Show current metrics and pipeline config."""
    cfg = PyqualConfig.load(config)
    gate_set = GateSet(cfg.gates)
    metrics = gate_set._collect_metrics(Path(workdir))

    console.print(f"[bold]{cfg.name}[/bold]")
    console.print(f"Stages: {len(cfg.stages)}")
    console.print(f"Gates:  {len(cfg.gates)}")
    console.print(f"Max iterations: {cfg.loop.max_iterations}")
    console.print(f"On fail: {cfg.loop.on_fail}")
    console.print()

    if metrics:
        console.print("[bold]Collected metrics:[/bold]")
        for k, v in sorted(metrics.items()):
            console.print(f"  {k}: {v:.1f}")
    else:
        console.print("[yellow]No metrics found. Run 'pyqual run' first.[/yellow]")


@app.command()
def report(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    readme: Path = typer.Option(None, "--readme", "-r", help="README file to update badges in."),
) -> None:
    """Generate metrics report (YAML) and update README.md badges."""
    from pyqual.report import run as run_report

    rc = run_report(
        workdir=Path(workdir),
        config_path=config,
        readme_path=readme,
    )
    if rc != 0:
        raise typer.Exit(rc)
    console.print("[bold green]✅ Report generated.[/bold green]")


def _run_mcp_workflow(
    *,
    title: str,
    runner,
    workdir: Path,
    project_path: str | None,
    issues: Path,
    output: Path,
    endpoint: str | None,
    model: str | None,
    file: list[str],
    use_docker: bool,
    docker_arg: list[str],
    json_output: bool,
    task: str | None = None,
) -> None:
    resolved_project_path = project_path or str(workdir)
    resolved_issues = issues if issues.is_absolute() else (workdir / issues).resolve()
    resolved_output = output if output.is_absolute() else (workdir / output).resolve()

    try:
        workflow_kwargs = {
            "workdir": workdir,
            "project_path": resolved_project_path,
            "issues_path": resolved_issues,
            "output_path": resolved_output,
            "endpoint_url": endpoint,
            "model": model,
            "files": file,
            "use_docker": use_docker,
            "docker_args": docker_arg,
        }
        if task is not None:
            workflow_kwargs["task"] = task

        result = asyncio.run(runner(**workflow_kwargs))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        table = Table(title=title)
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("success", "yes" if result.success else "no")
        table.add_row("endpoint", result.endpoint)
        table.add_row("project path", result.project_path)
        table.add_row("report", str(resolved_output))
        table.add_row("tool calls", str(result.tool_calls))
        table.add_row("model", result.model or "auto")
        if result.error:
            table.add_row("error", result.error)
        console.print(table)

    if result.error:
        raise typer.Exit(1)
    if not result.success:
        raise typer.Exit(1)


@app.command("mcp-fix")
def mcp_fix(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Project directory on the host."),
    project_path: str | None = typer.Option(None, "--project-path", help="Project path as seen by the MCP service container."),
    issues: Path = typer.Option(Path(".pyqual/errors.json"), "--issues", help="Gate-failure JSON file to summarize."),
    output: Path = typer.Option(Path(".pyqual/llx_mcp.json"), "--output", help="Where to write the MCP run report."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="MCP SSE endpoint URL."),
    model: str | None = typer.Option(None, "--model", help="Override the model selected by llx."),
    file: list[str] = typer.Option([], "--file", help="Specific file to focus on (repeatable)."),
    use_docker: bool = typer.Option(False, "--use-docker", help="Let llx's aider tool run inside Docker."),
    docker_arg: list[str] = typer.Option([], "--docker-arg", help="Extra Docker arguments forwarded to llx's aider tool."),
    task: str = typer.Option("quick_fix", "--task", help="Analysis task hint for llx."),
    json_output: bool = typer.Option(False, "--json", help="Print the full JSON result."),
) -> None:
    """Run the llx-backed MCP fix workflow."""
    if run_llx_fix_workflow is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    _run_mcp_workflow(
        title="llx MCP fix",
        runner=run_llx_fix_workflow,
        workdir=workdir,
        project_path=project_path,
        issues=issues,
        output=output,
        endpoint=endpoint,
        model=model,
        file=file,
        use_docker=use_docker,
        docker_arg=docker_arg,
        json_output=json_output,
        task=task,
    )


@app.command("mcp-refactor")
def mcp_refactor(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Project directory on the host."),
    project_path: str | None = typer.Option(None, "--project-path", help="Project path as seen by the MCP service container."),
    issues: Path = typer.Option(Path(".pyqual/errors.json"), "--issues", help="Gate-failure JSON file to summarize."),
    output: Path = typer.Option(Path(".pyqual/llx_mcp.json"), "--output", help="Where to write the MCP run report."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="MCP SSE endpoint URL."),
    model: str | None = typer.Option(None, "--model", help="Override the model selected by llx."),
    file: list[str] = typer.Option([], "--file", help="Specific file to focus on (repeatable)."),
    use_docker: bool = typer.Option(False, "--use-docker", help="Let llx's aider tool run inside Docker."),
    docker_arg: list[str] = typer.Option([], "--docker-arg", help="Extra Docker arguments forwarded to llx's aider tool."),
    json_output: bool = typer.Option(False, "--json", help="Print the full JSON result."),
) -> None:
    """Run the llx-backed MCP refactor workflow."""
    if run_llx_refactor_workflow is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    _run_mcp_workflow(
        title="llx MCP refactor",
        runner=run_llx_refactor_workflow,
        workdir=workdir,
        project_path=project_path,
        issues=issues,
        output=output,
        endpoint=endpoint,
        model=model,
        file=file,
        use_docker=use_docker,
        docker_arg=docker_arg,
        json_output=json_output,
    )


@app.command("mcp-service")
def mcp_service(
    host: str = typer.Option("0.0.0.0", "--host", help="Host interface to bind to."),
    port: int = typer.Option(DEFAULT_MCP_PORT, "--port", help="Port to listen on."),
) -> None:
    """Run the persistent llx MCP service with health and metrics endpoints."""
    if run_llx_mcp_service is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    try:
        run_llx_mcp_service(host=host, port=port)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("todo")
def tickets_todo(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing TODO.md and .planfile/.") ,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync TODO.md tickets using planfile's markdown backend."""
    try:
        sync_todo_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("github")
def tickets_github(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing .planfile/ and GitHub sync config."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync GitHub Issues using planfile's GitHub backend."""
    try:
        sync_github_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@tickets_app.command("all")
def tickets_all(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Repository root containing TODO.md and .planfile/."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without changing files."),
    direction: str = typer.Option("both", "--direction", help="Sync direction: from, to, or both."),
) -> None:
    """Sync TODO.md and GitHub tickets using planfile."""
    try:
        sync_all_tickets(workdir=workdir, dry_run=dry_run, direction=direction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@app.command()
def plugin(
    action: str = typer.Argument(..., help="Action: list, add, remove, info, search, validate"),
    name: str | None = typer.Argument(None, help="Plugin name (for add/remove/info)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag (for list/search)"),
) -> None:
    """Manage pyqual plugins - add, remove, search metric collectors."""
    from pyqual.cli_plugin_helpers import (
        plugin_add, plugin_info, plugin_list, plugin_remove,
        plugin_search, plugin_unknown_action, plugin_validate,
    )
    plugins = get_available_plugins()
    if action == "list":
        plugin_list(plugins, tag)
    elif action == "search":
        plugin_search(plugins, name or "")
    elif action == "info":
        plugin_info(name, workdir)
    elif action == "add":
        plugin_add(name, workdir)
    elif action == "remove":
        plugin_remove(name, workdir)
    elif action == "validate":
        plugin_validate(plugins, workdir)
    else:
        plugin_unknown_action(action)


@app.command()
def doctor() -> None:
    """Check availability of external tools used by pyqual collectors."""
    tools = [
        ("docker", "Container runtime for the llx MCP service", "Install Docker Engine"),
        ("bandit", "Security scanner", "pip install bandit"),
        ("pip-audit", "Dependency vulnerability scanner", "pip install pip-audit"),
        ("trufflehog", "Secret scanner", "brew install trufflehog"),
        ("gitleaks", "Alternative secret scanner", "brew install gitleaks"),
        ("mypy", "Type checker", "pip install mypy"),
        ("ruff", "Modern Python linter", "pip install ruff"),
        ("pylint", "Comprehensive linter", "pip install pylint"),
        ("flake8", "Style guide checker", "pip install flake8"),
        ("radon", "Complexity analyzer", "pip install radon"),
        ("interrogate", "Docstring coverage", "pip install interrogate"),
        ("vulture", "Dead code finder", "pip install vulture"),
        ("pytest", "Test runner", "pip install pytest"),
        ("code2llm", "Code analysis", "pip install code2llm"),
        ("vallm", "LLM validation", "pip install vallm"),
        ("uvicorn", "ASGI server for the llx MCP service", "pip install pyqual[mcp]"),
    ]

    table = Table(title="Tool Availability Check")
    table.add_column("Tool")
    table.add_column("Status", width=STATUS_COLUMN_WIDTH)
    table.add_column("Purpose")
    table.add_column("Install Command")

    available = 0
    for tool, purpose, install in tools:
        path = shutil.which(tool)
        if path:
            table.add_row(tool, "[green]✓ Available[/green]", purpose, "")
            available += 1
        else:
            table.add_row(tool, "[red]✗ Missing[/red]", purpose, install)

    console.print(table)
    console.print()
    console.print(f"[bold]{available}/{len(tools)} tools available[/bold]")

    if available < len(tools):
        console.print("\n[yellow]Install missing tools to enable all metrics:[/yellow]")
        console.print("  pip install bandit pip-audit mypy ruff pylint flake8 radon interrogate vulture")
        console.print("  # For secret scanning, install trufflehog or gitleaks separately")


@app.command()
def tools() -> None:
    """List built-in tool presets for pipeline stages."""
    from pyqual.tools import TOOL_PRESETS

    table = Table(title="Built-in Tool Presets")
    table.add_column("Tool")
    table.add_column("Binary")
    table.add_column("Output")
    table.add_column("Allow Failure")
    table.add_column("Available")

    for name in sorted(TOOL_PRESETS):
        preset = TOOL_PRESETS[name]
        avail = "[green]✓[/green]" if preset.is_available() else "[red]✗[/red]"
        af = "yes" if preset.allow_failure else "no"
        table.add_row(name, preset.binary, preset.output or "(inline)", af, avail)

    console.print(table)
    console.print()
    console.print("[dim]Use in pyqual.yaml:[/dim]")
    console.print("  stages:")
    console.print("    - name: lint")
    console.print("      tool: ruff")
    console.print("    - name: secrets")
    console.print("      tool: trufflehog")
    console.print("      optional: true")


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
    from pyqual.constants import PIPELINE_DB

    db_path = Path(workdir) / PIPELINE_DB
    if not db_path.exists():
        console.print("[yellow]No pipeline log found. Run 'pyqual run' first.[/yellow]")
        raise typer.Exit(1)

    if sql:
        rows = _query_nfo_db(db_path, sql=sql)
        if json_output:
            for row in rows:
                console.print(json.dumps(row, default=str))
        else:
            if not rows:
                console.print("[dim]No results.[/dim]")
                return
            table = Table(title=f"SQL Query ({len(rows)} rows)")
            for col in rows[0].keys():
                table.add_column(col)
            for row in rows:
                table.add_row(*[str(v)[:80] for v in row.values()])
            console.print(table)
        return

    rows = _query_nfo_db(db_path, event=level, failed=failed, tail=tail,
                          stage=stage)
    entries = [_row_to_event_dict(r) for r in rows]

    if not entries:
        console.print("[dim]No matching log entries.[/dim]")
        return

    if json_output:
        for entry in entries:
            clean = {k: v for k, v in entry.items() if not k.startswith("_")}
            console.print(json.dumps(clean, default=str))
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
    from rich.console import Console as _WatchConsole

    _wc = _WatchConsole(stderr=True, force_terminal=True)
    _wd = Path(workdir).resolve()
    db_path = _wd / ".pyqual" / "pipeline.db"
    history_path = _wd / ".pyqual" / "llx_history.jsonl"

    _wc.print(f"[bold]pyqual watch[/bold]  workdir={_wd}")
    _wc.print(f"[dim]Watching: {db_path}[/dim]")
    _wc.print(f"[dim]Press Ctrl+C to stop.[/dim]\n")

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
                            icon = "✅" if "PASS" in status_col or status_col.strip() == "" else "❌"
                            if "SKIP" in status_col:
                                icon = "⏭"
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
    from pyqual.constants import LLX_HISTORY_FILE

    history_path = Path(workdir) / LLX_HISTORY_FILE
    if not history_path.exists():
        console.print("[yellow]No fix history found.[/yellow]")
        console.print("[dim]Run 'pyqual run' with a fix stage to start recording history.[/dim]")
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
        console.print("[dim]History file is empty.[/dim]")
        raise typer.Exit(1)

    if tail > 0:
        entries = entries[-tail:]

    if json_output:
        for entry in entries:
            console.print(json.dumps(entry, default=str, ensure_ascii=False))
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
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
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

    console.print(table)

    if prompts:
        console.print()
        for i, entry in enumerate(entries):
            prompt = entry.get("prompt", "")
            if prompt:
                ts = entry.get("timestamp", "")[:19].replace("T", " ")
                console.print(f"\n[bold]── Run {i+1} ({ts}) ──[/bold]")
                console.print(Syntax(prompt, "text", theme="monokai", background_color="default",
                                     word_wrap=True))

    if verbose:
        console.print()
        for i, entry in enumerate(entries):
            stdout = entry.get("stdout_tail", "")
            if stdout:
                ts = entry.get("timestamp", "")[:19].replace("T", " ")
                console.print(f"\n[bold]── Stdout {i+1} ({ts}) ──[/bold]")
                console.print(Syntax(stdout, "text", theme="monokai", background_color="default",
                                     word_wrap=True))

    # Summary line
    total = len(entries)
    passed = sum(1 for e in entries if e.get("ok") is True or e.get("success") is True)
    failed = sum(1 for e in entries if e.get("ok") is False or e.get("success") is False)
    models = set(e.get("model", "") for e in entries if e.get("model"))
    console.print(f"\n[bold]Summary:[/bold] {total} runs, {passed} passed, {failed} failed"
                  f" | Models: {', '.join(sorted(models)) or '?'}")
    console.print(f"[dim]History: {history_path}[/dim]")


if __name__ == "__main__":
    app()
