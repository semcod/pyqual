# Security Plugin

Comprehensive security scanning for pyqual pipelines.

## Overview

The security plugin aggregates findings from multiple security scanners:

- **bandit** — Python security linter (finds common security issues in Python code)
- **pip-audit** — PyPI vulnerability scanner (checks for known CVEs in dependencies)
- **detect-secrets** — Credential scanning (finds potential secrets in code)
- **safety** — Dependency security checker

## Installation

```bash
pip install bandit pip-audit detect-secrets safety
```

## Metrics Collected

| Metric | Description | Default Max |
|--------|-------------|-------------|
| `security_bandit_high` | Bandit HIGH severity issues | 0 |
| `security_bandit_medium` | Bandit MEDIUM severity issues | 5 |
| `security_bandit_low` | Bandit LOW severity issues | ∞ |
| `security_vuln_critical` | pip-audit CRITICAL CVEs | 0 |
| `security_vuln_high` | pip-audit HIGH CVEs | 0 |
| `security_vuln_moderate` | pip-audit MODERATE CVEs | ∞ |
| `security_secrets_found` | detect-secrets findings | 0 |
| `security_safety_issues` | safety package vulnerabilities | 0 |

## Configuration Example

```yaml
pipeline:
  name: security-focused

  metrics:
    security_bandit_high_max: 0
    security_vuln_critical_max: 0
    security_secrets_found_max: 0

  stages:
    - name: bandit_scan
      run: bandit -r pyqual -f json -o .pyqual/bandit.json || true
      when: always
      optional: true

    - name: pip_audit
      run: pip-audit --format=json --output=.pyqual/audit.json || echo '[]' > .pyqual/audit.json
      when: always
      optional: true

    - name: detect_secrets
      run: detect-secrets scan --all-files > .pyqual/secrets.json || echo '{"results":{}}' > .pyqual/secrets.json
      when: always
      optional: true

  loop:
    max_iterations: 1
    on_fail: report
```

## Programmatic API

```python
from pyqual.plugins.security import (
    SecurityCollector,
    run_bandit_check,
    run_pip_audit,
    run_detect_secrets,
    security_summary,
)

# Run individual checks
bandit_result = run_bandit_check(paths=["myapp"], severity="high")
print(f"Found {len(bandit_result['issues'])} issues")

# Get comprehensive summary
summary = security_summary(Path("."))
print(f"Secure: {summary['is_secure']}")
print(f"Total issues: {summary['total_issues']}")

# Use collector for metrics
collector = SecurityCollector()
metrics = collector.collect(Path("."))
print(f"Critical vulns: {metrics['security_vuln_critical']}")
```

## Tags

- `security`
- `vulnerability`
- `bandit`
- `audit`
- `secrets`
- `safety`

## Version

1.0.0
