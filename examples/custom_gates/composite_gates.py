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

import json
import sys
import tempfile
from pathlib import Path

from pyqual.config import GateConfig
from pyqual.gates import GateSet

# ---------------------------------------------------------------------------
# Named thresholds for composite scoring
# ---------------------------------------------------------------------------
MAX_SCORE = 100.0
MIN_SCORE = 0.0
WEIGHT_COVERAGE = 0.35
WEIGHT_COMPLEXITY = 0.25
WEIGHT_LINT = 0.20
WEIGHT_SECURITY = 0.20

CC_TARGET = 10.0
COMPOSITE_PASS_THRESHOLD = 75.0

COVERAGE_GATE_THRESHOLD = 80.0
CC_GATE_THRESHOLD = 15.0
LINT_GATE_THRESHOLD = 10.0
SECURITY_GATE_THRESHOLD = 0.0

CC_BASELINE = 1.0
LINT_ERROR_PENALTY = 5.0
SECURITY_HIGH_PENALTY = 25.0


def compute_composite_score(metrics: dict[str, float]) -> float:
    """Compute a weighted quality score (0–100) from available metrics.

    Missing metrics are excluded from weighting (weights re-normalized).
    """
    components: list[tuple[float, float]] = []

    if "coverage" in metrics:
        # Coverage: 0–100 maps directly
        score = min(MAX_SCORE, max(MIN_SCORE, metrics["coverage"]))
        components.append((WEIGHT_COVERAGE, score))

    if "cc" in metrics:
        # CC: lower is better. CC=1 → 100, CC≥CC_TARGET → 0
        cc = metrics["cc"]
        score = max(MIN_SCORE, MAX_SCORE - ((cc - CC_BASELINE) / (CC_TARGET - CC_BASELINE)) * MAX_SCORE)
        components.append((WEIGHT_COMPLEXITY, score))

    if "ruff_errors" in metrics:
        # Lint errors: 0 → 100, ≥20 → 0
        errors = metrics["ruff_errors"]
        score = max(MIN_SCORE, MAX_SCORE - errors * LINT_ERROR_PENALTY)
        components.append((WEIGHT_LINT, score))

    if "bandit_high" in metrics:
        # Security: 0 high issues → 100, any → penalty
        high = metrics["bandit_high"]
        score = MAX_SCORE if high == 0 else max(MIN_SCORE, MAX_SCORE - high * SECURITY_HIGH_PENALTY)
        components.append((WEIGHT_SECURITY, score))

    if not components:
        return 0.0

    total_weight = sum(w for w, _ in components)
    weighted_sum = sum(w * s for w, s in components)
    return round(weighted_sum / total_weight, 2)


def run_composite_check(workdir: Path) -> bool:
    """Run individual gates + composite score on a workdir."""
    # Define individual gates
    gate_configs = [
        GateConfig(metric="coverage", operator="ge", threshold=COVERAGE_GATE_THRESHOLD),
        GateConfig(metric="cc", operator="le", threshold=CC_GATE_THRESHOLD),
        GateConfig(metric="ruff_errors", operator="le", threshold=LINT_GATE_THRESHOLD),
        GateConfig(metric="bandit_high", operator="le", threshold=SECURITY_GATE_THRESHOLD),
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
    composite_passed = composite >= COMPOSITE_PASS_THRESHOLD
    icon = "✅" if composite_passed else "❌"
    print(f"  {icon} composite_score: {composite} (threshold: {COMPOSITE_PASS_THRESHOLD})")
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
