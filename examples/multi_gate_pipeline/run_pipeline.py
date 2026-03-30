#!/usr/bin/env python3
"""Run the multi-gate pipeline programmatically with detailed reporting.

Demonstrates:
- Loading config and running pipeline from Python
- Iterating over results with per-stage timing
- Gate result inspection with pass/fail breakdown
- Generating a summary report as JSON artifact

Usage:
    python run_pipeline.py
    python run_pipeline.py --dry-run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet
from pyqual.pipeline import Pipeline

REPORT_PATH = ".pyqual/pipeline_report.json"


def build_report(result, gate_results) -> dict:
    """Build a structured JSON report from pipeline + gate results."""
    report = {
        "final_passed": result.final_passed,
        "iterations": result.iteration_count,
        "total_duration_s": round(result.total_duration, 2),
        "stages": [],
        "gates": [],
    }

    for iteration in result.iterations:
        for stage in iteration.stages:
            report["stages"].append({
                "name": stage.name,
                "iteration": iteration.iteration,
                "passed": stage.passed,
                "skipped": stage.skipped,
                "duration_s": round(stage.duration, 2),
                "returncode": stage.returncode,
            })

    for gr in gate_results:
        report["gates"].append({
            "metric": gr.metric,
            "value": gr.value,
            "threshold": gr.threshold,
            "passed": gr.passed,
        })

    return report


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    config_path = Path("pyqual.yaml")
    if not config_path.exists():
        print("Error: pyqual.yaml not found. Copy from this example directory.")
        return 1

    config = PyqualConfig.load(config_path)
    pipeline = Pipeline(config)

    print(f"Running {'DRY RUN' if dry_run else 'PIPELINE'}: {config.name}")
    print(f"  Stages: {len(config.stages)}")
    print(f"  Gates: {len(config.gates)}")
    print(f"  Max iterations: {config.loop.max_iterations}")
    print()

    result = pipeline.run(dry_run=dry_run)

    # Print per-iteration results
    for iteration in result.iterations:
        print(f"--- Iteration {iteration.iteration} ---")
        for stage in iteration.stages:
            if stage.skipped:
                icon = "⏭"
                label = "skipped"
            elif stage.passed:
                icon = "✅"
                label = f"{stage.duration:.1f}s"
            else:
                icon = "❌"
                label = f"{stage.duration:.1f}s rc={stage.returncode}"
            print(f"  {icon} {stage.name}: {label}")

    # Check gates
    gate_set = GateSet(config.gates)
    gate_results = gate_set.check_all(Path("."))

    print("\n--- Quality Gates ---")
    passed_count = 0
    for gr in gate_results:
        icon = "✅" if gr.passed else "❌"
        val = f"{gr.value:.1f}" if gr.value is not None else "N/A"
        print(f"  {icon} {gr.metric}: {val} (threshold: {gr.threshold})")
        if gr.passed:
            passed_count += 1

    print(f"\n{passed_count}/{len(gate_results)} gates passed")
    print(f"Total time: {result.total_duration:.1f}s")
    print(f"Final: {'PASS ✅' if result.final_passed else 'FAIL ❌'}")

    # Save report
    report = build_report(result, gate_results)
    report_path = Path(REPORT_PATH)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {REPORT_PATH}")

    return 0 if result.final_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
