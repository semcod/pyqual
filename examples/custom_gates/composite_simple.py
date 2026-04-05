#!/usr/bin/env python3
"""Composite gates example using pyqual.CompositeGateSet.

Uses pyqual.gates.CompositeGateSet - new in pyqual 0.1.x
"""
import json
import tempfile
from pathlib import Path

from pyqual.config import GateConfig
from pyqual.gates import CompositeGateSet

# Gate thresholds
COVERAGE_THRESHOLD: float = 80.0
CC_THRESHOLD: float = 15.0
RUFF_ERRORS_THRESHOLD: float = 10.0

# Weights for composite scoring
WEIGHT_COVERAGE = 0.4
WEIGHT_CC = 0.3
WEIGHT_RUFF_ERRORS = 0.3

# Composite pass threshold
PASS_THRESHOLD = 75.0

# Define gates with weights
gates = [
    GateConfig(metric="coverage", operator="ge", threshold=COVERAGE_THRESHOLD),
    GateConfig(metric="cc", operator="le", threshold=CC_THRESHOLD),
    GateConfig(metric="ruff_errors", operator="le", threshold=RUFF_ERRORS_THRESHOLD),
]
weights = {"coverage": WEIGHT_COVERAGE, "cc": WEIGHT_CC, "ruff_errors": WEIGHT_RUFF_ERRORS}

# Create composite gate set with pass threshold
composite = CompositeGateSet(gates, weights, pass_threshold=PASS_THRESHOLD)

# Test with synthetic data
with tempfile.TemporaryDirectory() as tmpdir:
    p = Path(tmpdir)
    pyqual_dir = p / ".pyqual"
    pyqual_dir.mkdir()
    
    # Simulate metrics
    (pyqual_dir / "coverage.json").write_text(
        json.dumps({"totals": {"percent_covered": 88.5}})
    )
    (pyqual_dir / "ruff.json").write_text(json.dumps([{"code": "E501"}] * 3))
    
    project_dir = p / "project"
    project_dir.mkdir()
    (project_dir / "analysis.toon.yaml").write_text("SUMMARY:\n  CC̄=3.2\n")
    
    # Run composite check
    result = composite.check_composite(p)
    
    print(f"Composite Score: {result.score:.1f}/100")
    print(f"Pass Threshold: {result.pass_threshold:.1f}")
    print(f"Result: {'✅ PASS' if result.passed else '❌ FAIL'}")
    print("\nIndividual Gates:")
    for g in result.individual:
        print(f"  {g}")
