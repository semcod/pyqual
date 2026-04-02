"""CLI for pyqual — declarative quality gate loops."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
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
)
from pyqual.config import PyqualConfig
from pyqual.constants import (
    BULK_PASS_PREVIEW,
    DEFAULT_MCP_PORT,
    STATUS_COLUMN_WIDTH,
    TIMESTAMP_COL_WIDTH,
    LLM_FIX_MAX_TOKENS,
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
_TIMESTAMP_COL_WIDTH = TIMESTAMP_COL_WIDTH  # "YYYY-MM-DD HH:MM:SS"
_BULK_PASS_PREVIEW = BULK_PASS_PREVIEW    # max passed-gate names to show inline

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
            resp = llm.complete(prompt, temperature=0.1, max_tokens=LLM_FIX_MAX_TOKENS)
            new_yaml = resp.content.strip()
            if new_yaml.startswith("```"):
                new_yaml = "\n".join(line for line in new_yaml.splitlines()
                                     if not line.startswith("```")).strip()
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
            line for line in lines
            if not line.startswith("```")
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


@tickets_app.command("fetch")
def tickets_fetch(
    label: str | None = typer.Option(None, "--label", "-l", help="Filter by label (e.g. 'pyqual-fix')"),
    state: str = typer.Option("open", "--state", "-s", help="Issue state: open, closed, all"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON file"),
    todo_output: Path = typer.Option(None, "--todo-output", "-t", help="Append to TODO.md"),
    append: bool = typer.Option(False, "--append", "-a", help="Append to TODO.md instead of overwrite"),
) -> None:
    """Fetch GitHub issues/PRs as tasks.
    
    Examples:
        pyqual tickets fetch --label pyqual-fix
        pyqual tickets fetch --label bug --output tasks.json
        pyqual tickets fetch --todo-output TODO.md --append
    """
    from pyqual.github_tasks import fetch_github_tasks, save_tasks_to_json, save_tasks_to_todo
    
    tasks = fetch_github_tasks(
        label=label,
        state=state,
        include_prs=True,
        include_issues=True,
    )
    
    if not tasks:
        console.print("[yellow]No tasks found matching criteria[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[bold]Found {len(tasks)} tasks[/bold]")
    for t in tasks:
        console.print(f"  - #{t.number}: {t.title[:50]}{'...' if len(t.title) > 50 else ''}")
    
    if output:
        save_tasks_to_json(tasks, output)
    
    if todo_output:
        save_tasks_to_todo(tasks, todo_output, append=append)


@tickets_app.command("comment")
def tickets_comment(
    issue_number: int = typer.Argument(..., help="Issue or PR number"),
    message: str = typer.Argument(..., help="Comment text"),
    is_pr: bool = typer.Option(False, "--pr", help="Comment on PR instead of issue"),
) -> None:
    """Post a comment on a GitHub issue or PR.
    
    Examples:
        pyqual tickets comment 123 "Fix applied successfully"
        pyqual tickets comment 456 "Failed due to timeout" --pr
    """
    from pyqual.github_actions import GitHubActionsReporter
    
    reporter = GitHubActionsReporter()
    
    if is_pr:
        success = reporter.post_pr_comment(message, issue_number)
    else:
        success = reporter.post_issue_comment(message, issue_number)
    
    if success:
        console.print(f"[green]✅ Comment posted to #{issue_number}[/green]")
    else:
        console.print(f"[red]❌ Failed to post comment[/red]")
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


if __name__ == "__main__":
    app()
