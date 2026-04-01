#!/usr/bin/env python3
"""Generate markdown report after pyqual run.

Creates a comprehensive report with:
- Mermaid diagram of pipeline flow
- ASCII diagram of pipeline flow  
- Execution results for each stage
- Current metrics and gates status
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import ast


def parse_kwargs(kwargs_str: str) -> dict[str, Any]:
    """Parse kwargs string that might have single quotes."""
    try:
        return json.loads(kwargs_str)
    except json.JSONDecodeError:
        # Try with single quotes (Python dict format)
        try:
            return ast.literal_eval(kwargs_str)
        except (ValueError, SyntaxError):
            return {}


@dataclass
class StageResult:
    name: str
    status: str
    duration: float
    returncode: int | None = None
    details: dict[str, Any] | None = None


@dataclass
class PipelineRun:
    timestamp: str
    total_time: float
    all_gates_passed: bool
    stages: list[StageResult]
    gates: list[dict[str, Any]]
    metrics: dict[str, Any]


def get_last_run(db_path: Path) -> PipelineRun | None:
    """Get the last pipeline run from database."""
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get the most recent stage_done entries to find the last run
    # Group by time window (runs within 5 minutes of each other)
    cursor.execute("""
        SELECT timestamp, function_name, kwargs FROM pipeline_logs 
        WHERE function_name = 'stage_done'
        ORDER BY id DESC LIMIT 50
    """)
    
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return None
    
    # Get the most recent run (first row timestamp)
    latest_timestamp = rows[0]['timestamp']
    
    # Parse stages from recent entries (within last 10 minutes of latest)
    stages = []
    total_duration = 0.0
    gates = []
    metrics = {}
    
    for row in rows[:20]:  # Last 20 stages max
        kwargs = parse_kwargs(row['kwargs'])
        stage_name = kwargs.get('stage', '')
        
        # Skip entries without proper stage name (filter out 'unknown')
        if not stage_name or stage_name == 'unknown':
            continue
        
        # Skip duplicate stages (keep most recent)
        if any(s.name == stage_name for s in stages):
            continue
            
        is_ok = kwargs.get('ok', False)
        is_skipped = kwargs.get('skipped', False)
        
        if is_skipped:
            status = 'skipped'
        elif is_ok:
            status = 'passed'
        else:
            status = 'failed'
        
        stages.append(StageResult(
            name=stage_name,
            status=status,
            duration=kwargs.get('duration_s', 0.0),
            returncode=kwargs.get('returncode'),
            details=kwargs
        ))
        total_duration += kwargs.get('duration_s', 0.0)
        
        # Extract metrics from certain stages
        if 'vallm_pass_pct' in kwargs:
            metrics['vallm_pass_pct'] = kwargs['vallm_pass_pct']
        if 'cc' in kwargs:
            metrics['cc'] = kwargs['cc']
        if 'files' in kwargs:
            metrics['files'] = kwargs['files']
        if 'passed' in kwargs and isinstance(kwargs['passed'], int):
            metrics['tests_passed'] = kwargs['passed']
        # Extract coverage from coverage.json if available
        if 'coverage' in kwargs:
            metrics['coverage'] = kwargs['coverage']
        elif 'coverage_percent' in kwargs:
            metrics['coverage'] = kwargs['coverage_percent']
    
    # Build gates from metrics with proper thresholds from config
    if 'cc' in metrics:
        gates.append({'metric': 'cc', 'value': metrics['cc'], 'threshold': 15.0, 'operator': '<=', 'passed': metrics['cc'] <= 15.0})
    if 'vallm_pass_pct' in metrics:
        gates.append({'metric': 'vallm_pass', 'value': metrics['vallm_pass_pct'], 'threshold': 90.0, 'operator': '>=', 'passed': metrics['vallm_pass_pct'] >= 90.0})
    if 'coverage' in metrics:
        gates.append({'metric': 'coverage', 'value': metrics['coverage'], 'threshold': 55.0, 'operator': '>=', 'passed': metrics['coverage'] >= 55.0})
    
    # Calculate all_gates_passed based on actual gates, not stages
    all_gates_passed = all(gate.get('passed', False) for gate in gates) if gates else True
    
    conn.close()
    
    # Reverse stages to show in execution order
    stages.reverse()
    
    # Read coverage from file if available and not already extracted
    if 'coverage' not in metrics:
        coverage_file = db_path.parent / "coverage.json"
        if coverage_file.exists():
            try:
                cov_data = json.loads(coverage_file.read_text())
                if 'totals' in cov_data and 'percent_covered' in cov_data['totals']:
                    metrics['coverage'] = cov_data['totals']['percent_covered']
                elif 'percent_covered' in cov_data:
                    metrics['coverage'] = cov_data['percent_covered']
            except (json.JSONDecodeError, KeyError):
                pass
    
    # Rebuild gates with coverage if now available
    if 'coverage' in metrics and not any(g.get('metric') == 'coverage' for g in gates):
        gates.append({'metric': 'coverage', 'value': metrics['coverage'], 'threshold': 55.0, 'operator': '>=', 'passed': metrics['coverage'] >= 55.0})
        # Recalculate all_gates_passed
        all_gates_passed = all(gate.get('passed', False) for gate in gates) if gates else True
    
    return PipelineRun(
        timestamp=latest_timestamp,
        total_time=total_duration,
        all_gates_passed=all_gates_passed,
        stages=stages,
        gates=gates,
        metrics=metrics
    )


def generate_mermaid_diagram(run: PipelineRun) -> str:
    """Generate Mermaid flowchart of pipeline execution."""
    lines = ["```mermaid", "flowchart LR"]
    
    # Add stages
    prev_stage = None
    for i, stage in enumerate(run.stages):
        node_id = f"S{i}"
        # Color based on status
        if stage.status == 'passed':
            color = 'fill:#90EE90'
        elif stage.status == 'failed':
            color = 'fill:#FFB6C1'
        else:  # skipped
            color = 'fill:#D3D3D3'
        
        lines.append(f'    {node_id}["{stage.name}<br/>{stage.duration:.1f}s"]')
        lines.append(f'    style {node_id} {color}')
        
        if prev_stage:
            lines.append(f'    {prev_stage} --> {node_id}')
        prev_stage = node_id
    
    # Add gates result
    if run.all_gates_passed:
        lines.append('    G["✓ All Gates Passed"]')
        lines.append('    style G fill:#90EE90,stroke:#228B22,stroke-width:3px')
    else:
        lines.append('    G["✗ Gates Failed"]')
        lines.append('    style G fill:#FFB6C1,stroke:#DC143C,stroke-width:3px')
    
    if prev_stage:
        lines.append(f'    {prev_stage} --> G')
    
    lines.append("```")
    return '\n'.join(lines)


def generate_ascii_diagram(run: PipelineRun) -> str:
    """Generate ASCII art diagram of pipeline execution."""
    lines = []
    lines.append("┌─────────────────────────────────────────────────────────────────┐")
    lines.append("│                    PYQUAL PIPELINE FLOW                         │")
    lines.append("├─────────────────────────────────────────────────────────────────┤")
    
    for stage in run.stages:
        status_icon = "✓" if stage.status == 'passed' else "✗" if stage.status == 'failed' else "○"
        status_color = "🟢" if stage.status == 'passed' else "🔴" if stage.status == 'failed' else "⚪"
        lines.append(f"│  {status_icon} {stage.name:<25} {stage.duration:>6.1f}s {status_color}        │")
    
    lines.append("├─────────────────────────────────────────────────────────────────┤")
    
    if run.all_gates_passed:
        lines.append("│  🎉 ALL GATES PASSED ✓                                           │")
    else:
        lines.append("│  ❌ SOME GATES FAILED                                            │")
    
    lines.append(f"│  ⏱️  Total time: {run.total_time:.1f}s                                          │")
    lines.append("└─────────────────────────────────────────────────────────────────┘")
    
    return '\n'.join(lines)


def generate_metrics_table(run: PipelineRun) -> str:
    """Generate metrics table."""
    lines = ["### 📊 Quality Gates"]
    lines.append("")
    lines.append("| Metric | Value | Threshold | Status |")
    lines.append("|--------|-------|-----------|--------|")
    
    # Format values with proper units
    for gate in run.gates:
        metric = gate.get('metric', 'unknown')
        value = gate.get('value', 0)
        threshold = gate.get('threshold', 0)
        operator = gate.get('operator', '>=')
        passed = gate.get('passed', False)
        status = "✅ PASS" if passed else "❌ FAIL"
        
        # Format value based on metric type
        if metric == 'cc':
            value_str = f"{value:.1f}"
            threshold_str = f"{operator} {threshold:.1f}"
        elif metric in ('vallm_pass', 'coverage'):
            value_str = f"{value:.1f}%"
            threshold_str = f"{operator} {threshold:.1f}%"
        else:
            value_str = str(value)
            threshold_str = f"{operator} {threshold}"
        
        lines.append(f"| {metric} | {value_str} | {threshold_str} | {status} |")
    
    return '\n'.join(lines)


def generate_stage_details(run: PipelineRun) -> str:
    """Generate detailed stage results."""
    lines = ["### 🔧 Stage Execution Details"]
    lines.append("")
    
    for stage in run.stages:
        status_emoji = "✅" if stage.status == 'passed' else "❌" if stage.status == 'failed' else "⏭️"
        lines.append(f"#### {status_emoji} {stage.name}")
        lines.append(f"- **Status:** {stage.status}")
        lines.append(f"- **Duration:** {stage.duration:.1f}s")
        if stage.returncode is not None:
            lines.append(f"- **Return code:** {stage.returncode}")
        
        # Add any additional details from the stage
        if stage.details:
            details = stage.details
            if 'tickets' in details:
                lines.append(f"- **Tickets created:** {details.get('tickets', 0)}")
            if 'files' in details:
                lines.append(f"- **Files analyzed:** {details.get('files', 0)}")
            if 'passed' in details and isinstance(details['passed'], int):
                lines.append(f"- **Tests passed:** {details.get('passed', 0)}")
            if 'vallm_pass_pct' in details:
                lines.append(f"- **vallm pass %:** {details.get('vallm_pass_pct', 0):.1f}%")
        
        lines.append("")
    
    return '\n'.join(lines)


def generate_report(workdir: Path | None = None) -> str:
    """Generate full markdown report."""
    if workdir is None:
        workdir = Path.cwd()
    
    db_path = workdir / ".pyqual" / "pipeline.db"
    run = get_last_run(db_path)
    
    if not run:
        return "# No pipeline run found\n\nRun `pyqual run` first to generate a report."
    
    lines = [
        "# Pyqual Pipeline Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Pipeline run:** {run.timestamp}",
        "",
        "---",
        "",
        "## 🔄 Pipeline Flow Diagram",
        "",
        generate_mermaid_diagram(run),
        "",
        "## 📈 ASCII Visualization",
        "",
        "```",
        generate_ascii_diagram(run),
        "```",
        "",
        generate_metrics_table(run),
        "",
        generate_stage_details(run),
        "",
        "---",
        "",
        "## 📝 Summary",
        "",
    ]
    
    if run.all_gates_passed:
        lines.append(f"✅ **All quality gates passed!** Pipeline completed successfully in {run.total_time:.1f}s.")
    else:
        lines.append("❌ **Some quality gates failed.** Review the stage details above.")
    
    lines.append("")
    
    return '\n'.join(lines)


def main() -> int:
    """Generate and print report."""
    report = generate_report()
    print(report)
    
    # Also save to file
    report_path = Path(".pyqual/report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"\n📄 Report saved to: {report_path}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
