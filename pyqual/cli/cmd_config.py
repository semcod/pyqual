"""Config-related commands: gates, validate, fix-config, status, report.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.table import Table

from pyqual.cli.main import app, console
from pyqual.config import PyqualConfig
from pyqual.gates import GateSet
from pyqual.validation import Severity, detect_project_facts, validate_config

if TYPE_CHECKING:
    pass


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


_SEV_STYLE = {
    Severity.ERROR:   ("[bold red]ERROR  [/]", "red"),
    Severity.WARNING: ("[yellow]WARNING[/]", "yellow"),
    Severity.INFO:    ("[dim]INFO   [/]", "dim"),
}


def _print_issues(result: Any, cfg_path: Path, fix: bool) -> None:
    """Print all validation issues to the console."""
    for issue in result.issues:
        badge, style = _SEV_STYLE[issue.severity]
        location = f" [dim][{issue.stage}][/dim]" if issue.stage else ""
        fixed_indicator = ""
        if fix and issue.suggestion and "Auto-fixed:" in issue.suggestion:
            fixed_indicator = " [green][fixed][/green]"
        console.print(f"  {badge}{location}{fixed_indicator}  [{style}]{issue.message}[/{style}]")
        if issue.suggestion and not issue.suggestion.startswith("Auto-fixed:"):
            console.print(f"          [dim]→ {issue.suggestion}[/dim]")


def _print_fix_summary(result: Any, cfg_path: Path) -> None:
    """Print count of auto-fixed issues when --fix is active."""
    fixed_count = sum(1 for i in result.issues if "Auto-fixed:" in (i.suggestion or ""))
    if fixed_count:
        console.print(f"\n[green]✓ Auto-fixed {fixed_count} syntax issue(s)[/green] (backup: {cfg_path.name}.bak)")


@app.command()
def validate(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    strict: bool = typer.Option(False, "--strict", "-s", help="Exit 1 on warnings too."),
    fix: bool = typer.Option(False, "--fix", "-f", help="Auto-fix YAML syntax errors (creates .bak backup)."),
) -> None:
    """Validate pyqual.yaml without running the pipeline.

    Checks for:
    - YAML parse errors (with line/column positions)
    - Unknown or missing tool binaries
    - Gate metric names that no collector produces
    - Stage configuration mistakes

    Use --fix to auto-repair common syntax errors (tabs, unclosed quotes, etc.)

    Examples:
        pyqual validate
        pyqual validate --config path/to/pyqual.yaml
        pyqual validate --strict
        pyqual validate --fix
    """
    cfg_path = Path(workdir) / config if not Path(config).is_absolute() else Path(config)
    result = validate_config(cfg_path, try_fix=fix)

    if not result.issues:
        console.print(f"[bold green]✅ {cfg_path.name} is valid.[/bold green]"
                      f" ({result.stages_checked} stages, {result.gates_checked} gates)")
        return

    console.print(f"[bold]Validating {cfg_path.name}[/bold]"
                  f" — {result.stages_checked} stages, {result.gates_checked} gates\n")

    _print_issues(result, cfg_path, fix)

    if fix:
        _print_fix_summary(result, cfg_path)

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
    if cfg.loop.on_fail == "create_ticket":
        backends = cfg.loop.ticket_backends or ["markdown"]
        console.print(f"Ticket backends: {', '.join(backends)}")
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
