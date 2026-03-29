"""CLI for devloop — declarative quality gate loops."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from devloop.config import DevloopConfig
from devloop.gates import GateSet
from devloop.pipeline import Pipeline

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Project directory")):
    """Create devloop.yaml with sensible defaults."""
    target = path / "devloop.yaml"
    if target.exists():
        overwrite = typer.confirm(f"{target} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    target.write_text(DevloopConfig.default_yaml())
    (path / ".devloop").mkdir(exist_ok=True)
    console.print(f"[green]Created {target}[/green]")
    console.print("Edit metrics thresholds and stages, then run: [bold]devloop run[/bold]")


@app.command()
def run(
    config: Path = typer.Option("devloop.yaml", "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
    """Execute pipeline loop until quality gates pass."""
    cfg = DevloopConfig.load(config)
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
    config: Path = typer.Option("devloop.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
    """Check quality gates without running stages."""
    cfg = DevloopConfig.load(config)
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
    config: Path = typer.Option("devloop.yaml", "--config", "-c"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
):
    """Show current metrics and pipeline config."""
    cfg = DevloopConfig.load(config)
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
        console.print("[yellow]No metrics found. Run 'devloop run' first.[/yellow]")


if __name__ == "__main__":
    app()
