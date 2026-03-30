#!/usr/bin/env python3
"""Dynamic thresholds based on file changes."""

import subprocess

from pyqual import GateConfig, GateSet

DEFAULT_COVERAGE_THRESHOLD = 80.0
LARGE_CHANGE_COVERAGE_THRESHOLD = 60.0
LARGE_CHANGE_FILE_THRESHOLD = 10
EXAMPLE_COVERAGE_VALUE = 75.0
GIT_DIFF_BASE_REF = "HEAD~1"
PYTHON_FILE_SUFFIX = ".py"

def main() -> int:
    """Run the dynamic-threshold gate example."""
    # Detect changed files
    result = subprocess.run(
        ["git", "diff", "--name-only", GIT_DIFF_BASE_REF],
        capture_output=True,
        text=True,
        check=False,
    )
    changed_files = [line for line in result.stdout.splitlines() if line.strip()]

    # Adjust thresholds based on change size
    num_changed = sum(1 for filename in changed_files if filename.endswith(PYTHON_FILE_SUFFIX))
    coverage_threshold = (
        # Lower threshold for large changes
        LARGE_CHANGE_COVERAGE_THRESHOLD
        if num_changed > LARGE_CHANGE_FILE_THRESHOLD
        # Higher threshold for small changes
        else DEFAULT_COVERAGE_THRESHOLD
    )

    gates = [
        GateConfig(metric="coverage", operator="ge", threshold=coverage_threshold),
    ]

    print(f"Checking with coverage threshold: {coverage_threshold}%")
    gate_set = GateSet(gates)

    # Example metrics (in real use, collect from actual sources)
    metrics = {"coverage": EXAMPLE_COVERAGE_VALUE}
    results = [g.check(metrics) for g in gate_set.gates]

    for r in results:
        print(f"{'✅' if r.passed else '❌'} {r.metric}: {r.value}% (threshold: {r.threshold}%)")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
