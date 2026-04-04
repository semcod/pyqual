#!/usr/bin/env python3
"""Composite gates example using pyqual.CompositeGateSet.

Uses pyqual.gates.CompositeGateSet - new in pyqual 0.1.x
"""
import json
import tempfile
from pathlib import Path

from pyqual.config import GateConfig
from pyqual.gates import CompositeGateSet

# Define gates with weights
gates = [
    GateConfig(metric="coverage", operator="ge", threshold=80),
    GateConfig(metric="cc", operator="le", threshold=15),
    GateConfig(metric="ruff_errors", operator="le", threshold=10),
]
weights = {"coverage": 0.4, "cc": 0.3, "ruff_errors": 0.3}

# Create composite gate set with 75% pass threshold
composite = CompositeGateSet(gates, weights, pass_threshold=75.0)

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
