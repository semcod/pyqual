"""Auto-tune command for pyqual - automatically adjusts metric thresholds."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.table import Table

from pyqual.cli.main import app, console
from pyqual.config import PyqualConfig
from pyqual.constants import PIPELINE_DB


@app.command("tune-thresholds")
def tune_thresholds(
    aggressive: bool = typer.Option(False, "--aggressive", "-a", help="More ambitious thresholds"),
    conservative: bool = typer.Option(False, "--conservative", "-c", help="Safer thresholds with margin"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show changes without applying"),
    config_path: Path = typer.Option(Path("pyqual.yaml"), "--config", "-f", help="Config file path"),
) -> None:
    """
    Automatically tune quality gate thresholds to match current metrics.
    
    Analyzes collected metrics and suggests optimal thresholds that will
    result in all-green status while maintaining quality standards.
    
    Examples:
        pyqual tune                    # Show suggested thresholds
        pyqual tune --dry-run          # Same as above (explicit)
        pyqual tune --aggressive       # Tighter thresholds
        pyqual tune --conservative     # Looser thresholds with safety margin
    """
    console.print("[bold blue]🔧 pyqual tune - Auto-tuning quality gates[/bold blue]\n")
    
    # Load current config
    config_obj = PyqualConfig.load(config_path)
    current_metrics = {g.metric: g.threshold for g in config_obj.gates}
    
    # Load latest metrics from database
    latest_metrics = _load_latest_metrics()
    
    if not latest_metrics:
        console.print("[yellow]⚠️  No metrics found. Run 'pyqual run' first.[/yellow]")
        raise typer.Exit(1)
    
    # Calculate suggested thresholds
    suggested = _calculate_thresholds(
        latest_metrics, 
        aggressive=aggressive, 
        conservative=conservative
    )
    
    # Display comparison table
    _display_comparison(current_metrics, suggested, latest_metrics)
    
    # Show diff or apply
    if dry_run or (not aggressive and not conservative):
        console.print("\n[dim]Use --aggressive or --conservative to see different strategies[/dim]")
        console.print("[dim]To apply changes, the tune command will update pyqual.yaml[/dim]")
    else:
        if _confirm_apply():
            _apply_thresholds(config_path, suggested)
            console.print("\n[bold green]✅ Thresholds updated in pyqual.yaml[/bold green]")
            console.print("[dim]Run 'pyqual run' to verify all gates pass[/dim]")


def _load_latest_metrics() -> dict[str, float]:
    """Load the most recent metrics from pipeline database."""
    db_path = Path(PIPELINE_DB)
    if not db_path.exists():
        return {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get latest run_id
        cursor.execute("SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return {}
        
        run_id = row[0]
        
        # Get metrics for that run
        cursor.execute(
            "SELECT metric_name, metric_value FROM pipeline_metrics WHERE run_id = ?",
            (run_id,)
        )
        metrics = {name: float(value) for name, value in cursor.fetchall()}
        conn.close()
        return metrics
    except Exception as e:
        console.print(f"[dim]Debug: Could not load from DB: {e}[/dim]")
        return {}


def _calculate_thresholds(
    metrics: dict[str, float],
    aggressive: bool = False,
    conservative: bool = False,
) -> dict[str, Any]:
    """Calculate optimal thresholds based on current metrics."""
    
    # Safety margins based on strategy
    if aggressive:
        upper_margin = 0.90  # 10% tighter for upper limits
        lower_margin = 1.10  # 10% higher for lower limits
    elif conservative:
        upper_margin = 1.20  # 20% looser for upper limits  
        lower_margin = 0.85  # 15% lower for lower limits
    else:
        upper_margin = 1.15  # 15% looser for upper limits
        lower_margin = 0.90  # 10% lower for lower limits
    
    suggested: dict[str, Any] = {}
    
    # Complexity (lower is better)
    if "cc" in metrics:
        suggested["cc_max"] = max(10, int(metrics["cc"] * upper_margin))
    
    # Issues (lower is better)
    if "critical" in metrics:
        suggested["critical_max"] = max(15, int(metrics["critical"] * upper_margin))
    if "ruff_fatal" in metrics:
        suggested["ruff_fatal_max"] = max(10, int(metrics["ruff_fatal"] * upper_margin))
    if "ruff_errors" in metrics:
        suggested["ruff_errors_max"] = max(500, int(metrics["ruff_errors"] * upper_margin))
    
    # Pass rates (higher is better)
    if "vallm_pass" in metrics:
        suggested["vallm_pass_min"] = int(metrics["vallm_pass"] * lower_margin)
    if "coverage" in metrics:
        suggested["coverage_min"] = max(1, int(metrics["coverage"] * lower_margin))
    
    # Documentation scores (higher is better)
    if "documentation_score" in metrics:
        suggested["documentation_score_min"] = int(metrics["documentation_score"] * lower_margin)
    if "readme_completeness" in metrics:
        suggested["readme_completeness_min"] = int(metrics["readme_completeness"] * lower_margin)
    
    # Security (strict - zero tolerance)
    suggested["secrets_found_max"] = 0
    suggested["security_vuln_critical_max"] = 0
    suggested["security_vuln_high_max"] = 0
    
    # Project hygiene
    suggested["license_exists_min"] = 1
    if "pyproject_completeness" in metrics:
        suggested["pyproject_completeness_min"] = min(90, int(metrics["pyproject_completeness"] * lower_margin))
    
    return suggested


def _display_comparison(
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
        
        # Get actual value (remove _min/_max suffix to find metric name)
        base_name = metric.replace("_min", "").replace("_max", "").replace("_exists", "")
        actual_val = actual.get(base_name, actual.get(metric, "—"))
        
        # Determine if threshold would pass
        if isinstance(actual_val, (int, float)) and isinstance(suggested_val, (int, float)):
            if "_max" in metric:  # Upper limit
                passes = actual_val <= suggested_val
            else:  # Lower limit
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


def _confirm_apply() -> bool:
    """Ask user to confirm applying changes."""
    return typer.confirm("\nApply these thresholds to pyqual.yaml?")


def _apply_thresholds(config_path: Path, thresholds: dict) -> None:
    """Write updated thresholds to config file."""
    # Read raw YAML to preserve structure
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    
    # Update metrics section
    if "pipeline" not in raw:
        raw["pipeline"] = {}
    if "metrics" not in raw["pipeline"]:
        raw["pipeline"]["metrics"] = {}
    
    raw["pipeline"]["metrics"].update(thresholds)
    
    # Write back
    with open(config_path, "w") as f:
        yaml.dump(raw, f, default_flow_style=False, sort_keys=False)


@app.command("tune-show")
def tune_show() -> None:
    """Display all currently collected metrics."""
    metrics = _load_latest_metrics()
    
    if not metrics:
        console.print("[yellow]No metrics found. Run 'pyqual run' first.[/yellow]")
        raise typer.Exit(1)
    
    table = Table(title="Collected Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    for name, value in sorted(metrics.items()):
        table.add_row(name, f"{value:.2f}" if isinstance(value, float) else str(value))
    
    console.print(table)
