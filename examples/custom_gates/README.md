# Custom Quality Gates

Example of creating and using custom quality gates programmatically.

## Files

- `custom_metric.py` - Define custom metrics and gates
- `dynamic_thresholds.py` - Adjust thresholds based on context
- `composite_gates.py` - Combine multiple gates

## custom_metric.py

```python
#!/usr/bin/env python3
"""Define and check custom quality gates."""

from pyqual import GateConfig, GateSet, Gate

# Define custom gates
gates = [
    GateConfig(metric="doc_coverage", operator="ge", threshold=80.0),
    GateConfig(metric="type_coverage", operator="ge", threshold=70.0),
    GateConfig(metric="todo_count", operator="le", threshold=5.0),
]

# Custom metric collection
def collect_custom_metrics(workdir):
    """Collect custom metrics from codebase."""
    import re
    from pathlib import Path
    
    metrics = {}
    
    # Count TODOs
    todos = 0
    for pyfile in Path(workdir).rglob("*.py"):
        content = pyfile.read_text()
        todos += len(re.findall(r'#\s*TODO', content, re.IGNORECASE))
    
    metrics["todo_count"] = float(todos)
    
    # Estimate doc coverage (functions with docstrings / total functions)
    total_funcs = 0
    doc_funcs = 0
    for pyfile in Path(workdir).rglob("*.py"):
        content = pyfile.read_text()
        funcs = re.findall(r'def\s+\w+', content)
        total_funcs += len(funcs)
        docstrings = re.findall(r'def\s+\w+.*?"""', content, re.DOTALL)
        doc_funcs += len(docstrings)
    
    metrics["doc_coverage"] = (doc_funcs / total_funcs * 100) if total_funcs else 0
    
    return metrics

# Check gates with custom metrics
gate_set = GateSet(gates)
metrics = collect_custom_metrics(".")
results = [g.check(metrics) for g in gate_set.gates]

for r in results:
    print(f"{'✅' if r.passed else '❌'} {r}")
```

## dynamic_thresholds.py

```python
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
results = gate_set.check_all()

for r in results:
    print(f"{'✅' if r.passed else '❌'} {r.metric}: {r.value}% (threshold: {r.threshold}%)")
```

## composite_gates.py

```python
#!/usr/bin/env python3
"""Composite gates - all must pass."""

from pyqual import GateConfig, GateSet, GateResult

# Define related gates that must pass together
security_gates = [
    GateConfig(metric="secrets_found", operator="le", threshold=0.0),
    GateConfig(metric="vuln_deps", operator="le", threshold=0.0),
]

quality_gates = [
    GateConfig(metric="cc", operator="le", threshold=15.0),
    GateConfig(metric="coverage", operator="ge", threshold=80.0),
]

# Check composite groups
def check_composite(name, gates, metrics):
    gate_set = GateSet(gates)
    results = [g.check(metrics) for g in gate_set.gates]
    passed = all(r.passed for r in results)
    
    print(f"\n{name} Gates:")
    for r in results:
        print(f"  {'✅' if r.passed else '❌'} {r}")
    print(f"  Overall: {'✅ PASS' if passed else '❌ FAIL'}")
    
    return passed

# Example metrics
metrics = {
    "secrets_found": 0,
    "vuln_deps": 1,
    "cc": 12,
    "coverage": 85,
}

security_pass = check_composite("Security", security_gates, metrics)
quality_pass = check_composite("Quality", quality_gates, metrics)

print(f"\nFinal: {'✅ All composite gates pass' if security_pass and quality_pass else '❌ Some composite gates fail'}")
```

## Usage

```bash
cd custom_gates
python custom_metric.py
python dynamic_thresholds.py
python composite_gates.py
```

## Key Points

- `GateConfig(metric, operator, threshold)` defines a gate
- `GateSet()` collects and checks gates
- `gate.check(metrics)` checks single gate against metrics
- Metrics are just `dict[str, float]`
- Combine gates for complex quality policies
