"""CLI for pyqual — declarative quality gate loops."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet
from pyqual.pipeline import Pipeline
from pyqual.plugins import (
    PluginRegistry,
    get_available_plugins,
    install_plugin_config,
)

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()


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
            console.print("[yellow]Creating planfile tickets for failures...[/yellow]")
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


@app.command()
def plugin(
    action: str = typer.Argument(..., help="Action: list, add, info"),
    name: str | None = typer.Argument(None, help="Plugin name (for add/info)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
    """Manage pyqual plugins - add new metric collectors."""
    if action == "list":
        plugins = get_available_plugins()
        if not plugins:
            console.print("[yellow]No plugins available.[/yellow]")
            return
        
        table = Table(title="Available Plugins")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Version")
        table.add_column("Tags")
        
        for name, meta in sorted(plugins.items()):
            tags = ", ".join(meta.tags) if meta.tags else ""
            table.add_row(name, meta.description, meta.version, tags)
        
        console.print(table)
    
    elif action == "info":
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
    
    elif action == "add":
        if not name:
            console.print("[red]Plugin name required. Usage: pyqual plugin add <name>[/red]")
            raise typer.Exit(1)
        
        meta = get_available_plugins().get(name)
        if not meta:
            console.print(f"[red]Unknown plugin: {name}[/red]")
            console.print("Run 'pyqual plugin list' to see available plugins.")
            raise typer.Exit(1)
        
        # Append config to pyqual.yaml
        config_path = workdir / "pyqual.yaml"
        if not config_path.exists():
            console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
            console.print("Run 'pyqual init' first.")
            raise typer.Exit(1)
        
        plugin_config = install_plugin_config(name, workdir)
        
        # Read existing content
        existing = config_path.read_text()
        
        # Check if already added
        if f"# {name} plugin" in existing:
            console.print(f"[yellow]Plugin {name} already appears in pyqual.yaml[/yellow]")
            return
        
        # Append plugin config as comment + YAML
        with open(config_path, "a") as f:
            f.write(f"\n# {name} plugin configuration\n")
            f.write(plugin_config)
        
        console.print(f"[green]Added {name} plugin configuration to pyqual.yaml[/green]")
        console.print(f"Review and customize the added metrics and stages.")
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Supported actions: list, add, info")
        raise typer.Exit(1)


@app.command()
def doctor():
    """Check availability of external tools used by pyqual collectors."""
    tools = [
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
