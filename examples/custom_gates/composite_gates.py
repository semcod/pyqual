#!/usr/bin/env python3
"""Composite quality gates — combine multiple metrics into pass/fail decisions.

Demonstrates:
- Weighted composite score from multiple gate results
- Conditional gate logic (skip gates when data is missing)
- Custom gate evaluation with programmatic thresholds
- Rich console output with detailed breakdown

Usage:
    python composite_gates.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from pyqual.config import GateConfig
from pyqual.gates import Gate, GateSet

# ---------------------------------------------------------------------------
# Named thresholds for composite scoring
# ---------------------------------------------------------------------------
WEIGHT_COVERAGE = 0.35
WEIGHT_COMPLEXITY = 0.25
WEIGHT_LINT = 0.20
WEIGHT_SECURITY = 0.20

COVERAGE_TARGET = 90.0
CC_TARGET = 10.0
LINT_TARGET = 0.0
SECURITY_TARGET = 0.0


def compute_composite_score(metrics: dict[str, float]) -> float:
    """Compute a weighted quality score (0–100) from available metrics.

    Missing metrics are excluded from weighting (weights re-normalized).
    """
    components: list[tuple[float, float]] = []

    if "coverage" in metrics:
        # Coverage: 0–100 maps directly
        score = min(100.0, max(0.0, metrics["coverage"]))
        components.append((WEIGHT_COVERAGE, score))

    if "cc" in metrics:
        # CC: lower is better. CC=1 → 100, CC≥CC_TARGET → 0
        cc = metrics["cc"]
        score = max(0.0, 100.0 - ((cc - 1.0) / (CC_TARGET - 1.0)) * 100.0)
        components.append((WEIGHT_COMPLEXITY, score))

    if "ruff_errors" in metrics:
        # Lint errors: 0 → 100, ≥20 → 0
        errors = metrics["ruff_errors"]
        score = max(0.0, 100.0 - errors * 5.0)
        components.append((WEIGHT_LINT, score))

    if "bandit_high" in metrics:
        # Security: 0 high issues → 100, any → penalty
        high = metrics["bandit_high"]
        score = 100.0 if high == 0 else max(0.0, 100.0 - high * 25.0)
        components.append((WEIGHT_SECURITY, score))

    if not components:
        return 0.0

    total_weight = sum(w for w, _ in components)
    weighted_sum = sum(w * s for w, s in components)
    return round(weighted_sum / total_weight, 2)


def run_composite_check(workdir: Path) -> None:
    """Run individual gates + composite score on a workdir."""
    # Define individual gates
    gate_configs = [
        GateConfig(metric="coverage", operator="ge", threshold=80.0),
        GateConfig(metric="cc", operator="le", threshold=15.0),
        GateConfig(metric="ruff_errors", operator="le", threshold=10.0),
        GateConfig(metric="bandit_high", operator="le", threshold=0.0),
    ]

    gate_set = GateSet(gate_configs)
    results = gate_set.check_all(workdir)

    # Collect metrics for composite
    metrics = gate_set._collect_metrics(workdir)
    composite = compute_composite_score(metrics)

    print("=" * 60)
    print("COMPOSITE QUALITY GATE REPORT")
    print("=" * 60)

    for r in results:
        icon = "✅" if r.passed else "❌"
        val = f"{r.value:.1f}" if r.value is not None else "N/A"
        print(f"  {icon} {r.metric}: {val} (threshold: {r.threshold})")

    print("-" * 60)
    composite_passed = composite >= 75.0
    icon = "✅" if composite_passed else "❌"
    print(f"  {icon} composite_score: {composite} (threshold: 75.0)")
    print("=" * 60)

    all_individual = all(r.passed for r in results)
    final = all_individual and composite_passed
    print(f"\nFinal verdict: {'PASS ✅' if final else 'FAIL ❌'}")

    return final


# ---------------------------------------------------------------------------
# Self-test with synthetic data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        pyqual_dir = p / ".pyqual"
        pyqual_dir.mkdir()

        # Simulate coverage output
        (pyqual_dir / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": 88.5}})
        )

        # Simulate ruff output (list of violations)
        ruff_violations = [{"code": "E501", "message": "line too long"}] * 3
        (pyqual_dir / "ruff.json").write_text(json.dumps(ruff_violations))

        # Simulate bandit output
        (pyqual_dir / "bandit.json").write_text(
            json.dumps({"results": [], "metrics": {"_totals": {"SEVERITY.HIGH": 0}}})
        )

        # Simulate toon analysis for CC
        project_dir = p / "project"
        project_dir.mkdir()
        (project_dir / "analysis.toon.yaml").write_text(
            "SUMMARY:\n  CC̄=3.2\n  critical=0\n"
        )

        print("Running composite gates with synthetic data...\n")
        passed = run_composite_check(p)
        sys.exit(0 if passed else 1)
