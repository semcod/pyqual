#!/usr/bin/env python3
"""Dynamic thresholds based on file changes."""

import subprocess
from pyqual import GateConfig, GateSet

# Detect changed files
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD~1"],
    capture_output=True, text=True
)
changed_files = result.stdout.strip().split("\n")

# Adjust thresholds based on change size
num_changed = len([f for f in changed_files if f.endswith(".py")])

if num_changed > 10:
    # Lower threshold for large changes
    coverage_threshold = 60.0
else:
    # Higher threshold for small changes
    coverage_threshold = 80.0

gates = [
    GateConfig(metric="coverage", operator="ge", threshold=coverage_threshold),
]

print(f"Checking with coverage threshold: {coverage_threshold}%")
gate_set = GateSet(gates)

# Example metrics (in real use, collect from actual sources)
metrics = {"coverage": 75.0}  # Example: 75% coverage
results = [g.check(metrics) for g in gate_set.gates]

for r in results:
    print(f"{'✅' if r.passed else '❌'} {r.metric}: {r.value}% (threshold: {r.threshold}%)")
