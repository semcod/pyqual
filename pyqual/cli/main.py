"""Shared CLI setup — app, console, logging configuration.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

from pyqual.constants import TIMESTAMP_COL_WIDTH, PIPELINE_DB

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"
_TIMESTAMP_COL_WIDTH = TIMESTAMP_COL_WIDTH  # "YYYY-MM-DD HH:MM:SS"

app = typer.Typer(help="Declarative quality gate loops for AI-assisted development.")
console = Console()
stderr_console = Console(stderr=True)


@app.command("tune")
def tune_thresholds_cmd(
    aggressive: bool = typer.Option(False, "--aggressive", "-a", help="More ambitious thresholds"),
    conservative: bool = typer.Option(False, "--conservative", "-c", help="Safer thresholds with margin"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying"),
    config_path: Path = typer.Option(Path("pyqual.yaml"), "--config", "-f", help="Config file path"),
) -> None:
    """
    Auto-tune quality gate thresholds based on current metrics.
    
    Analyzes collected metrics and suggests optimal thresholds.
    """
    console.print("[bold blue]🔧 pyqual tune - Auto-tuning quality gates[/bold blue]\n")
    
    from pyqual.config import PyqualConfig
    
    try:
        config_obj = PyqualConfig.load(config_path)
        current_metrics = {g.metric: g.threshold for g in config_obj.gates}
    except FileNotFoundError:
        console.print(f"[yellow]⚠️  Config not found: {config_path}. Run 'pyqual init'.[/yellow]")
        raise typer.Exit(1)
    
    # Load latest metrics from database
    latest_metrics = _load_latest_metrics_for_tune()
    
    if not latest_metrics:
        console.print("[yellow]⚠️  No metrics found. Run 'pyqual run' first.[/yellow]")
        raise typer.Exit(1)
    
    # Calculate suggested thresholds
    suggested = _calculate_thresholds_for_tune(
        latest_metrics, 
        aggressive=aggressive, 
        conservative=conservative
    )
    
    # Display comparison table
    _display_comparison_for_tune(current_metrics, suggested, latest_metrics)
    
    # Show diff or apply
    if dry_run:
        console.print("\n[dim]Dry run - no changes made. Remove --dry-run to apply.[/dim]")
    elif aggressive or conservative:
        if typer.confirm("\nApply these thresholds to pyqual.yaml?"):
            _apply_thresholds_for_tune(config_path, suggested)
            console.print("\n[bold green]✅ Thresholds updated in pyqual.yaml[/bold green]")
            console.print("[dim]Run 'pyqual run' to verify all gates pass[/dim]")
    else:
        console.print("\n[dim]Use --aggressive or --conservative to apply changes[/dim]")
        console.print("[dim]Use --dry-run to preview without applying[/dim]")


def _load_latest_metrics_for_tune() -> dict[str, float]:
    """Load the most recent metrics from pipeline database."""
    db_path = Path(PIPELINE_DB)
    if not db_path.exists():
        return {}
    
    try:
        import sqlite3
        import json
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get latest pipeline_end event with gate_check data
        cursor.execute(
            """SELECT kwargs FROM pipeline_logs 
               WHERE function_name = 'gate_check' 
               ORDER BY timestamp DESC"""
        )
        
        metrics = {}
        for row in cursor.fetchall():
            try:
                data = json.loads(row[0].replace("'", '"'))
                metric_name = data.get('metric')
                metric_value = data.get('value')
                if metric_name and metric_value is not None:
                    metrics[metric_name] = float(metric_value)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        
        conn.close()
        return metrics
    except Exception as e:
        console.print(f"[dim]Debug: Could not load from DB: {e}[/dim]")
        return {}


def _calculate_thresholds_for_tune(
    metrics: dict[str, float],
    aggressive: bool = False,
    conservative: bool = False,
) -> dict[str, Any]:
    """Calculate optimal thresholds based on current metrics."""
    
    # Safety margins based on strategy
    if aggressive:
        upper_margin = 0.90
        lower_margin = 1.10
    elif conservative:
        upper_margin = 1.20
        lower_margin = 0.85
    else:
        upper_margin = 1.15
        lower_margin = 0.90
    
    suggested: dict[str, Any] = {}
    
    if "cc" in metrics:
        suggested["cc_max"] = max(10, int(metrics["cc"] * upper_margin))
    if "critical" in metrics:
        suggested["critical_max"] = max(15, int(metrics["critical"] * upper_margin))
    if "vallm_pass" in metrics:
        suggested["vallm_pass_min"] = int(metrics["vallm_pass"] * lower_margin)
    if "coverage" in metrics:
        suggested["coverage_min"] = max(1, int(metrics["coverage"] * lower_margin))
    
    suggested["secrets_found_max"] = 0
    
    return suggested


def _display_comparison_for_tune(
    current: dict[str, Any],
    suggested: dict[str, Any],
    actual: dict[str, float]
) -> None:
    """Display comparison table of current vs suggested thresholds."""
    
    table = Table(title="Quality Gate Thresholds")
    table.add_column("Metric", style="cyan")
    table.add_column("Current", style="dim")
    table.add_column("Suggested", style="green")
    table.add_column("Actual Value", style="blue")
    table.add_column("Status", style="bold")
    
    for metric, suggested_val in suggested.items():
        current_val = current.get(metric, "—")
        
        base_name = metric.replace("_min", "").replace("_max", "").replace("_exists", "")
        actual_val = actual.get(base_name, actual.get(metric, "—"))
        
        if isinstance(actual_val, (int, float)) and isinstance(suggested_val, (int, float)):
            if "_max" in metric:
                passes = actual_val <= suggested_val
            else:
                passes = actual_val >= suggested_val
            status = "[green]✓ PASS[/green]" if passes else "[red]✗ FAIL[/red]"
        else:
            status = "[dim]—[/dim]"
        
        table.add_row(
            metric,
            str(current_val),
            str(suggested_val),
            f"{actual_val:.1f}" if isinstance(actual_val, float) else str(actual_val),
            status
        )
    
    console.print(table)


def _apply_thresholds_for_tune(config_path: Path, thresholds: dict) -> None:
    """Write updated thresholds to config file."""
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    
    if "pipeline" not in raw:
        raw["pipeline"] = {}
    if "metrics" not in raw["pipeline"]:
        raw["pipeline"]["metrics"] = {}
    
    raw["pipeline"]["metrics"].update(thresholds)
    
    with open(config_path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, sort_keys=False)


# Sub-apps
git_app = typer.Typer(help="Git repository operations: status, commit, push with protection handling.")
app.add_typer(git_app, name="git")

tickets_app = typer.Typer(help="Control planfile-backed tickets from TODO.md and GitHub.")
app.add_typer(tickets_app, name="tickets")


def setup_logging(verbose: bool, workdir: Path = Path(".")) -> None:
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
