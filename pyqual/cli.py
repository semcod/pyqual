"""CLI for pyqual — declarative quality gate loops."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet
from pyqual.integrations.llx_mcp import run_llx_fix_workflow
from pyqual.integrations.llx_mcp_service import run_server as run_llx_mcp_service
from pyqual.pipeline import Pipeline
from pyqual.plugins import (
    get_available_plugins,
    install_plugin_config,
)
from pyqual.tickets import sync_all_tickets
from pyqual.tickets import sync_github_tickets
from pyqual.tickets import sync_todo_tickets

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()
tickets_app = typer.Typer(help="Control planfile-backed tickets from TODO.md and GitHub.")
app.add_typer(tickets_app, name="tickets")


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Project directory")):
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


@app.command()
def run(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
    """Execute pipeline loop until quality gates pass."""
    cfg = PyqualConfig.load(config)
    pipeline = Pipeline(cfg, workdir)
    result = pipeline.run(dry_run=dry_run)

    for iteration in result.iterations:
        console.rule(f"[bold]Iteration {iteration.iteration}[/bold]")
        for stage in iteration.stages:
            icon = "⏭" if stage.skipped else ("✅" if stage.passed else "❌")
            label = "skipped" if stage.skipped else f"{stage.duration:.1f}s"
            console.print(f"  {icon} {stage.name} ({label})")
            if not stage.passed and stage.stderr:
                console.print(f"     [red]{stage.stderr[:200]}[/red]")

        console.print()
        for gate in iteration.gates:
            console.print(f"  {gate}")

        if iteration.all_gates_passed:
            console.print("\n[bold green]All gates passed![/bold green]")
            break

    if not result.final_passed:
        console.print(f"\n[bold red]Gates not met after {result.iteration_count} iterations.[/bold red]")
        if cfg.loop.on_fail == "create_ticket":
            console.print("[yellow]Creating planfile tickets from TODO.md...[/yellow]")
            try:
                sync_todo_tickets(workdir=workdir, dry_run=False, direction="from")
            except RuntimeError as exc:
                console.print(f"[red]{exc}[/red]")
                raise typer.Exit(1)
        raise typer.Exit(1)

    console.print(f"\nTotal time: {result.total_duration:.1f}s")


@app.command()
def gates(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
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
    resolved_project_path = project_path or str(workdir)
    resolved_issues = issues if issues.is_absolute() else (workdir / issues).resolve()
    resolved_output = output if output.is_absolute() else (workdir / output).resolve()

    try:
        result = asyncio.run(
            run_llx_fix_workflow(
                workdir=workdir,
                project_path=resolved_project_path,
                issues_path=resolved_issues,
                output_path=resolved_output,
                endpoint_url=endpoint,
                model=model,
                files=file,
                use_docker=use_docker,
                docker_args=docker_arg,
                task=task,
            )
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        table = Table(title="llx MCP fix")
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


@app.command("mcp-service")
def mcp_service(
    host: str = typer.Option("0.0.0.0", "--host", help="Host interface to bind to."),
    port: int = typer.Option(8000, "--port", help="Port to listen on."),
) -> None:
    """Run the persistent llx MCP service with health and metrics endpoints."""
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
        table.add_row(plugin_name, getattr(meta, "description", "")[:50], getattr(meta, "version", ""), tags)

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
        table.add_row(plugin_name, getattr(meta, "description", "")[:50], tags)

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
    table.add_column("Status", width=12)
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


if __name__ == "__main__":
    app()
