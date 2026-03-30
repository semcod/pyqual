"""CLI for pyqual — declarative quality gate loops."""

from __future__ import annotations

import asyncio
import re
import json
import logging
import shutil
import sys

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pyqual.config import PyqualConfig
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
from pyqual.plugins import (
    get_available_plugins,
    install_plugin_config,
)
from pyqual.tickets import sync_all_tickets
from pyqual.tickets import sync_github_tickets
from pyqual.tickets import sync_todo_tickets

DEFAULT_MCP_PORT = 8000
STATUS_COLUMN_WIDTH = 12
MAX_DESCRIPTION_LENGTH = 50

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"

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
def init(path: Path = typer.Argument(Path("."), help="Project directory")) -> None:
    """Create pyqual.yaml with sensible defaults."""
    target = path / "pyqual.yaml"
    if target.exists():
        overwrite = typer.confirm(f"{target} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    target.write_text(PyqualConfig.default_yaml())
    (path / ".pyqual").mkdir(exist_ok=True)
    console.print(f"[green]Created {target}[/green]")
    console.print("Edit metrics thresholds and stages, then run: [bold]pyqual run[/bold]")


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
        console.print(f"[green]✅ Passed ({len(result.passed)}):[/green] {', '.join(result.passed[:20])}"
                      + (f" +{len(result.passed)-20} more" if len(result.passed) > 20 else ""))
    if result.failed:
        console.print(f"[red]❌ Failed ({len(result.failed)}):[/red] {', '.join(result.failed)}")
    if result.errors:
        console.print(f"[red]💥 Errors ({len(result.errors)}):[/red]")
        for name, err in result.errors:
            console.print(f"  {name}: {err}")
    if result.skipped:
        console.print(f"[dim]⏭ Skipped ({len(result.skipped)}): {', '.join(result.skipped[:10])}"
                      + (f" +{len(result.skipped)-10} more" if len(result.skipped) > 10 else "") + "[/dim]")

    console.print(f"\n[bold]Total time: {result.total_duration:.1f}s[/bold]")

    if result.failed or result.errors:
        raise typer.Exit(1)


def _extract_stage_summary(name: str, stdout: str, stderr: str) -> dict[str, str]:
    """Extract key metrics from stage output as YAML-ready key: value pairs."""
    text = (stdout or "") + "\n" + (stderr or "")
    metrics: dict[str, str] = {}
    metrics.update(_extract_pytest_stage_summary(text))
    metrics.update(_extract_lint_stage_summary(text))
    metrics.update(_extract_prefact_stage_summary(name, text))
    metrics.update(_extract_code2llm_stage_summary(name, text))
    metrics.update(_extract_validation_stage_summary(name, text))
    metrics.update(_extract_fix_stage_summary(name, text))
    metrics.update(_extract_mypy_stage_summary(name, text))
    metrics.update(_extract_bandit_stage_summary(text))
    return metrics


def _get_last_error_line(text: str) -> str:
    """Return the last meaningful error line, filtering out informational noise."""
    if not text:
        return ""
    noise_prefixes = (
        "Using .gitignore", "Excluded ", "✓ ", "Results saved",
        "Processing ", "Scanning ", "Checking ", "Loading ", "Collecting ",
    )
    error_kws = ("error", "fail", "assert", "exception", "traceback",
                 "critical", "syntax", "invalid", "cannot", "no module")
    clean = [l.strip() for l in text.splitlines()
             if l.strip() and not any(l.strip().startswith(p) for p in noise_prefixes)]
    err_lines = [l for l in clean if any(kw in l.lower() for kw in error_kws)]
    if err_lines:
        return err_lines[-1][:200]
    return clean[-1][:200] if clean else ""


@app.command()
def run(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show live pipeline log output."),
    auto_fix_config: bool = typer.Option(False, "--auto-fix-config",
                                         help="Auto-repair pyqual.yaml when ENV/CONFIG errors are detected."),
) -> None:
    """Execute pipeline loop until quality gates pass."""
    _setup_logging(verbose, workdir)
    cfg = PyqualConfig.load(config)

    _workdir = Path(workdir).resolve()
    _config_path = (_workdir / config) if not Path(config).is_absolute() else Path(config)

    _sc = stderr_console  # live progress → stderr (keeps stdout clean YAML)

    def _on_iter_start(num: int) -> None:
        _sc.print(f"[dim]─── Iteration {num} ───[/dim]")

    def _on_stage_start(name: str) -> None:
        _sc.print(f"[dim]▶ {name}[/dim]")

    def _on_stage_error(failure: Any) -> None:  # failure: StageFailure
        from pyqual.validation import EC, ErrorDomain, validate_config
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
            _sc.print(f"  [dim][{failure.stage_name}] {code}  → fix stage will handle this.[/dim]")

    def _run_auto_fix_config(cfg_path: Path, wd: Path, diag: Any) -> None:
        from pyqual.validation import detect_project_facts
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

    import pyqual as _pq
    import yaml as _yaml
    _ver = getattr(_pq, "__version__", "?")

    pipeline = Pipeline(cfg, workdir,
                        on_stage_start=_on_stage_start,
                        on_iteration_start=_on_iter_start,
                        on_stage_error=_on_stage_error)
    result = pipeline.run(dry_run=dry_run)

    # ── Build structured report and emit as YAML to stdout ──
    op_sym = {"le": "<=", "ge": ">=", "lt": "<", "gt": ">", "eq": "=="}
    report: dict[str, Any] = {
        "pyqual": _ver,
        "config": str(config),
        "workdir": str(_workdir),
        "iterations": [],
    }

    for iteration in result.iterations:
        iter_data: dict[str, Any] = {
            "iteration": iteration.iteration,
            "stages": [],
            "gates": [],
            "all_gates_passed": iteration.all_gates_passed,
        }
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
            iter_data["stages"].append(sd)

        for gate in iteration.gates:
            gd: dict[str, Any] = {
                "metric": gate.metric,
                "value": round(gate.value, 1) if gate.value is not None else None,
                "threshold": gate.threshold,
                "operator": op_sym.get(gate.operator, gate.operator),
                "passed": gate.passed,
            }
            iter_data["gates"].append(gd)

        report["iterations"].append(iter_data)
        if iteration.all_gates_passed:
            break

    report["result"] = "all_gates_passed" if result.final_passed else "gates_not_met"
    report["total_time"] = round(result.total_duration, 1)

    print(_yaml.safe_dump(report, default_flow_style=False, sort_keys=False,
                          allow_unicode=True), end="")

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
    from pyqual.validation import Severity, validate_config

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
        console.print(f"[bold red]{nerr} error(s)[/bold red]"
                      + (f", {nwarn} warning(s)" if nwarn else "")
                      + " — pipeline cannot start.")
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
    from pyqual.validation import Severity, detect_project_facts, validate_config
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
):
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


def _plugin_list(plugins: dict[str, object], tag: str | None) -> None:
    if tag:
        plugins = {k: v for k, v in plugins.items() if tag in getattr(v, "tags", [])}

    if not plugins:
        console.print(
            "[yellow]No plugins available.[/yellow]"
            if not tag
            else f"[yellow]No plugins with tag '{tag}' found.[/yellow]"
        )
        return

    table = Table(
        title=f"Available Plugins ({len(plugins)} total)" if not tag else f"Plugins with tag '{tag}' ({len(plugins)})"
    )
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    table.add_column("Tags")

    for plugin_name, meta in sorted(plugins.items()):
        tags = ", ".join(getattr(meta, "tags", [])[:3]) if getattr(meta, "tags", None) else ""
        table.add_row(plugin_name, getattr(meta, "description", "")[:MAX_DESCRIPTION_LENGTH], getattr(meta, "version", ""), tags)

    console.print(table)


def _plugin_search(plugins: dict[str, object], query: str) -> None:
    if not query:
        console.print("[red]Search query required. Usage: pyqual plugin search <query>[/red]")
        raise typer.Exit(1)

    results = {}
    normalized_query = query.lower()
    for plugin_name, meta in plugins.items():
        description = getattr(meta, "description", "")
        tags = getattr(meta, "tags", []) or []
        if (
            normalized_query in plugin_name.lower()
            or normalized_query in description.lower()
            or any(normalized_query in str(tag).lower() for tag in tags)
        ):
            results[plugin_name] = meta

    if not results:
        console.print(f"[yellow]No plugins found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search results for '{query}' ({len(results)} found)")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Tags")

    for plugin_name, meta in sorted(results.items()):
        tags = ", ".join(getattr(meta, "tags", [])[:3]) if getattr(meta, "tags", None) else ""
        table.add_row(plugin_name, getattr(meta, "description", "")[:MAX_DESCRIPTION_LENGTH], tags)

    console.print(table)


def _plugin_info(name: str | None, workdir: Path) -> None:
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin info <name>[/red]")
        raise typer.Exit(1)

    meta = get_available_plugins().get(name)
    if not meta:
        console.print(f"[red]Unknown plugin: {name}[/red]")
        console.print("Run 'pyqual plugin list' to see available plugins.")
        raise typer.Exit(1)

    console.print(f"[bold]{meta.name}[/bold] v{meta.version}")
    console.print(f"Description: {meta.description}")
    if meta.author:
        console.print(f"Author: {meta.author}")
    if meta.tags:
        console.print(f"Tags: {', '.join(meta.tags)}")
    console.print()
    console.print("[bold]Configuration example:[/bold]")
    console.print(install_plugin_config(name, workdir))


def _plugin_add(name: str | None, workdir: Path) -> None:
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin add <name>[/red]")
        raise typer.Exit(1)

    meta = get_available_plugins().get(name)
    if not meta:
        console.print(f"[red]Unknown plugin: {name}[/red]")
        console.print("Run 'pyqual plugin list' to see available plugins.")
        raise typer.Exit(1)

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        console.print("Run 'pyqual init' first.")
        raise typer.Exit(1)

    plugin_config = install_plugin_config(name, workdir)
    existing = config_path.read_text()
    if f"# {name} plugin" in existing:
        console.print(f"[yellow]Plugin {name} already appears in pyqual.yaml[/yellow]")
        return

    with open(config_path, "a") as f:
        f.write(f"\n# {name} plugin configuration\n")
        f.write(plugin_config)

    console.print(f"[green]Added {name} plugin configuration to pyqual.yaml[/green]")
    console.print("Review and customize the added metrics and stages.")


def _plugin_remove(name: str | None, workdir: Path) -> None:
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin remove <name>[/red]")
        raise typer.Exit(1)

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        raise typer.Exit(1)

    existing = config_path.read_text()
    marker = f"# {name} plugin configuration"
    if marker not in existing:
        console.print(f"[yellow]Plugin {name} not found in pyqual.yaml[/yellow]")
        raise typer.Exit(1)

    lines = existing.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        if marker in line:
            skip = True
            continue
        if skip and line.startswith("# ") and "plugin" in line:
            skip = False
        if not skip:
            new_lines.append(line)

    config_path.write_text("\n".join(new_lines))
    console.print(f"[green]Removed {name} plugin configuration from pyqual.yaml[/green]")


def _plugin_validate(plugins: dict[str, object], workdir: Path) -> None:
    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        raise typer.Exit(1)

    existing = config_path.read_text()
    found_plugins = [plugin_name for plugin_name in plugins if f"# {plugin_name} plugin" in existing]

    console.print("[bold]Validation Results[/bold]")
    console.print(f"Found {len(found_plugins)} configured plugins: {', '.join(found_plugins)}")

    available = set(plugins.keys())
    configured = set(found_plugins)
    missing = available - configured

    if missing:
        console.print(f"\n[yellow]Available but not configured:[/yellow] {', '.join(sorted(missing))}")

    console.print("\n[green]✓ Configuration is valid[/green]")


def _plugin_unknown_action(action: str) -> None:
    console.print(f"[red]Unknown action: {action}[/red]")
    console.print("Supported actions: list, add, remove, info, search, validate")
    raise typer.Exit(1)


@app.command()
def plugin(
    action: str = typer.Argument(..., help="Action: list, add, remove, info, search, validate"),
    name: str | None = typer.Argument(None, help="Plugin name (for add/remove/info)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag (for list/search)"),
):
    """Manage pyqual plugins - add, remove, search metric collectors."""
    plugins = get_available_plugins()
    if action == "list":
        _plugin_list(plugins, tag)
    elif action == "search":
        _plugin_search(plugins, name or "")
    elif action == "info":
        _plugin_info(name, workdir)
    elif action == "add":
        _plugin_add(name, workdir)
    elif action == "remove":
        _plugin_remove(name, workdir)
    elif action == "validate":
        _plugin_validate(plugins, workdir)
    else:
        _plugin_unknown_action(action)


@app.command()
def doctor():
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


def _extract_pytest_stage_summary(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"(\d+) passed", text)
    if m:
        out["passed"] = int(m.group(1))
    m = re.search(r"(\d+) failed", text)
    if m:
        out["failed"] = int(m.group(1))
    m = re.search(r"(\d+) error", text)
    if m:
        out["errors"] = int(m.group(1))
    return out


def _extract_lint_stage_summary(text: str) -> dict[str, Any]:
    m = re.search(r"Found (\d+) error", text)
    if m:
        return {"lint_errors": int(m.group(1))}
    if "All checks passed" in text:
        return {"lint_errors": 0}
    return {}


def _extract_prefact_stage_summary(name: str, text: str) -> dict[str, Any]:
    m = re.search(r"Total issues:\s*(\d+)\s*active", text)
    if m:
        return {"tickets": int(m.group(1))}
    if "prefact" in name.lower():
        open_tickets = text.count("- [ ]")
        if open_tickets:
            return {"tickets": open_tickets}
    return {}


def _extract_code2llm_stage_summary(name: str, text: str) -> dict[str, Any]:
    m = re.search(r"(\d+)\s+file", text)
    if m and ("analyze" in name.lower() or "code2llm" in name.lower()):
        out: dict[str, Any] = {"files": int(m.group(1))}
        m2 = re.search(r"([\d,]+)\s+line", text)
        if m2:
            out["lines"] = int(m2.group(1).replace(",", ""))
        return out
    return {}


def _extract_validation_stage_summary(name: str, text: str) -> dict[str, Any]:
    lower_name = name.lower()
    if "valid" not in lower_name and "vallm" not in lower_name:
        return {}
    out: dict[str, Any] = {}
    m_cc = re.search(r"CC\u0304?[:\s=]+([0-9.]+)", text)
    if not m_cc:
        m_cc = re.search(r"\bcc[:\s=]+([0-9.]+)", text, re.IGNORECASE)
    if m_cc:
        out["cc"] = float(m_cc.group(1))
    m_crit = re.search(r"critical[:\s=]+([0-9]+)", text, re.IGNORECASE)
    if m_crit:
        out["critical"] = int(m_crit.group(1))
    return out


def _extract_fix_stage_summary(name: str, text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"Selected:\s*\S+\s*\u2192\s*(.+)", text)
    if m:
        out["model"] = m.group(1).strip().split()[0]
    m2 = re.search(r"(\d+)\s+file[s]?\s+changed", text)
    if m2:
        out["files_changed"] = int(m2.group(1))
    elif "fix" in name.lower():
        m3 = re.search(r"(Applied|No changes)[^\n]*", text)
        if m3:
            out["fix_status"] = m3.group(0)[:80]
    return out


def _extract_mypy_stage_summary(name: str, text: str) -> dict[str, Any]:  # noqa: ARG001
    m = re.search(r"Found (\d+) error[s]? in (\d+) file", text)
    if m:
        return {"mypy_errors": int(m.group(1)), "mypy_files": int(m.group(2))}
    return {}


def _extract_bandit_stage_summary(text: str) -> dict[str, Any]:
    m = re.search(r"High: (\d+)\s+Medium: (\d+)\s+Low: (\d+)", text)
    if not m:
        return {}
    return {
        "bandit_high": int(m.group(1)),
        "bandit_medium": int(m.group(2)),
        "bandit_low": int(m.group(3)),
    }


def _format_log_entry_row(entry: dict) -> tuple:
    """Return (ts, event_name, name, status, details) for one log entry."""
    ts = entry.get("_timestamp", "")[:19].replace("T", " ")[11:]
    event_name = entry.get("event", entry.get("_function_name", ""))
    ok = entry.get("ok")
    status = "[green]PASS[/green]" if ok else ("[red]FAIL[/red]" if ok is False else "[dim]—[/dim]")
    name = ""
    details = ""

    if event_name == "stage_done":
        name = entry.get("stage", "")
        tool_info = f"tool:{entry['tool']}" if entry.get("tool") else ""
        rc_info = f"rc={entry.get('original_returncode', '?')}"
        dur = f"{entry.get('duration_s', 0):.1f}s"
        details = " ".join(filter(None, [tool_info, rc_info, dur]))
        if entry.get("skipped"):
            status = "[dim]SKIP[/dim]"
        if entry.get("stderr_tail"):
            details += f" err: {entry['stderr_tail'][:80]}"
    elif event_name == "gate_check":
        name = entry.get("metric", "")
        val = entry.get("value")
        thr = entry.get("threshold")
        op = {"le": "≤", "ge": "≥", "lt": "<", "gt": ">", "eq": "="}.get(str(entry.get("operator", "")), "?")
        val_s = f"{val:.1f}" if val is not None else "N/A"
        details = f"{val_s} {op} {thr}"
    elif event_name in ("pipeline_start", "pipeline_end"):
        name = entry.get("pipeline", "")
        parts: list[str] = []
        if event_name == "pipeline_start":
            parts.append(f"stages={entry.get('stages')}")
            parts.append(f"gates={entry.get('gates')}")
            parts.append(f"max_iter={entry.get('max_iterations')}")
            if entry.get("dry_run"):
                parts.append("DRY-RUN")
        else:
            parts.append("PASS" if entry.get("final_ok") else "FAIL")
            parts.append(f"iter={entry.get('iterations')}")
            dur_s = entry.get("total_duration_s", 0)
            parts.append(f"{dur_s:.1f}s" if isinstance(dur_s, (int, float)) else str(dur_s))
        details = " ".join(parts)
    else:
        details = str(entry)[:80]

    return ts, event_name, name, status, details


def _query_nfo_db(db_path: Path, event: str = "", failed: bool = False,
                  tail: int = 0, sql: str = "") -> list[dict]:
    """Query the nfo SQLite pipeline log and return structured dicts."""
    import sqlite3
    from pyqual.pipeline import PIPELINE_TABLE

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    if sql:
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Build query from filters
    where_clauses: list[str] = []
    params: list[str] = []

    if event:
        where_clauses.append("function_name = ?")
        params.append(event)

    if failed:
        where_clauses.append("level = 'WARNING'")

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit = f"LIMIT {tail}" if tail > 0 else ""
    order = "ORDER BY rowid DESC" if tail > 0 else "ORDER BY rowid ASC"

    query = f"SELECT * FROM {PIPELINE_TABLE} {where} {order} {limit}"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    entries = [dict(r) for r in rows]
    if tail > 0:
        entries.reverse()
    return entries


def _row_to_event_dict(row: dict) -> dict:
    """Parse an nfo SQLite row into a structured event dict.

    nfo stores kwargs as repr string in the 'kwargs' column.
    We parse it back to extract structured fields.
    """
    import ast
    kwargs_raw = row.get("kwargs", "{}")
    try:
        data = ast.literal_eval(kwargs_raw) if isinstance(kwargs_raw, str) else kwargs_raw
    except (ValueError, SyntaxError):
        data = {}
    data["_timestamp"] = row.get("timestamp", "")
    data["_level"] = row.get("level", "")
    data["_function_name"] = row.get("function_name", "")
    data["_duration_ms"] = row.get("duration_ms")
    return data


@app.command()
def logs(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    tail: int = typer.Option(0, "--tail", "-n", help="Show last N entries (0 = all)."),
    level: str = typer.Option("", "--level", "-l", help="Filter by event type (stage_done, gate_check, pipeline_start, pipeline_end)."),
    failed: bool = typer.Option(False, "--failed", "-f", help="Show only failed stages/gates."),
    json_output: bool = typer.Option(False, "--json", "-j", help="Raw JSON lines (for LLM/llx consumption)."),
    sql: str = typer.Option("", "--sql", help="Run raw SQL query against pipeline.db (advanced)."),
) -> None:
    """View structured pipeline logs from .pyqual/pipeline.db (nfo SQLite).

    Logs are written via nfo to SQLite during every pipeline run.
    Use --json for machine-readable output (ideal for llx auto-diagnosis).
    Use --sql for arbitrary SQL queries against the log database.

    Examples:
        pyqual logs                    # show all entries
        pyqual logs --tail 20          # last 20 entries
        pyqual logs --failed           # only failures
        pyqual logs --json --failed    # JSON failures for LLM consumption
        pyqual logs --level gate_check # only gate results
        pyqual logs --sql "SELECT * FROM pipeline_logs WHERE function_name='stage_done' AND level='WARNING'"
    """
    from pyqual.pipeline import PIPELINE_DB

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

    rows = _query_nfo_db(db_path, event=level, failed=failed, tail=tail)
    entries = [_row_to_event_dict(r) for r in rows]

    if not entries:
        console.print("[dim]No matching log entries.[/dim]")
        return

    if json_output:
        for entry in entries:
            clean = {k: v for k, v in entry.items() if not k.startswith("_")}
            console.print(json.dumps(clean, default=str))
        return

    # Human-readable table output
    table = Table(title=f"Pipeline Log ({len(entries)} entries)")
    table.add_column("Time", style="dim", width=12)
    table.add_column("Event", width=14)
    table.add_column("Stage/Metric")
    table.add_column("Status", width=8)
    table.add_column("Details")

    for entry in entries:
        ts, event_name, name, status, details = _format_log_entry_row(entry)
        table.add_row(ts, event_name, name, status, details)

    console.print(table)
    console.print(f"\n[dim]Log DB: {db_path}[/dim]")
    console.print("[dim]For LLM consumption: pyqual logs --json --failed[/dim]")
    console.print("[dim]SQL access: pyqual logs --sql \"SELECT * FROM pipeline_logs WHERE level='WARNING'\"[/dim]")


if __name__ == "__main__":
    app()
