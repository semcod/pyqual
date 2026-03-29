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
