#!/usr/bin/env python3
"""Check quality gates without running stages."""

from pyqual import PyqualConfig, GateSet

# Load config
config = PyqualConfig.load("pyqual.yaml")

# Check gates only
gate_set = GateSet(config.gates)
results = gate_set.check_all()

for result in results:
    status = "✅" if result.passed else "❌"
    print(f"{status} {result}")

if all(r.passed for r in results):
    print("\nAll gates pass!")
else:
    print("\nSome gates failed.")
    exit(1)
