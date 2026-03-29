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
