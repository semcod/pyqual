# Deps Plugin

Dependency management and freshness analysis for pyqual.

## Overview

The deps plugin helps maintain healthy dependencies:

- **Outdated packages** — Detect packages needing updates (via `pip list --outdated`)
- **Dependency tree** — Analyze direct vs transitive dependencies (via `pipdeptree`)
- **Requirements validation** — Check for unpinned packages
- **License analysis** — Identify unknown or restrictive licenses

## Installation

```bash
pip install pipdeptree

# Optional tools for enhanced functionality
pip install pip-licenses  # For license analysis
```

## Metrics Collected

| Metric | Description | Target |
|--------|-------------|--------|
| `deps_outdated_count` | Total outdated packages | ≤ 10 |
| `deps_outdated_major` | Major version outdated | 0 |
| `deps_direct_count` | Direct dependencies | ≤ 20 |
| `deps_transitive_count` | Transitive dependencies | ≤ 50 |
| `deps_total_count` | Total packages | ≤ 70 |
| `deps_pins_incomplete` | Unpinned in requirements | 0 |
| `deps_requirements_entries` | Requirements.txt entries | varies |
| `deps_licenses_unknown` | Packages with unknown license | ≤ 5 |
| `deps_licenses_restrictive` | GPL/AGPL/etc. packages | review |

## Configuration Example

```yaml
pipeline:
  name: dependency-health

  metrics:
    deps_outdated_max: 10
    deps_outdated_major_max: 0
    deps_vulnerable_max: 0
    deps_pins_incomplete_max: 0

  stages:
    - name: deps_check
      run: |
        pip list --outdated --format=json > .pyqual/outdated.json 2>&1 || echo '[]' > .pyqual/outdated.json
        pipdeptree --json > .pyqual/deptree.json 2>&1 || echo '{}' > .pyqual/deptree.json
        python3 -c "
          from pyqual.plugins.deps import check_requirements, deps_health_check
          import json
          json.dump(check_requirements(), open('.pyqual/requirements_check.json', 'w'))
          json.dump(deps_health_check(), open('.pyqual/deps_health.json', 'w'))
        "
      when: first_iteration
      optional: true
      timeout: 120

  loop:
    max_iterations: 1
```

## Programmatic API

```python
from pyqual.plugins.deps import (
    DepsCollector,
    get_outdated_packages,
    get_dependency_tree,
    check_requirements,
    deps_health_check,
)

# Check for outdated packages
outdated = get_outdated_packages()
print(f"Outdated: {outdated['total']}")
print(f"Major updates: {outdated['major_outdated']}")
for pkg in outdated['packages'][:5]:
    print(f"  {pkg['name']}: {pkg['version']} → {pkg['latest_version']}")

# Analyze dependency tree
tree = get_dependency_tree()
print(f"Direct: {tree['direct_count']}, Transitive: {tree['transitive_count']}")

# Validate requirements.txt
reqs = check_requirements()
print(f"Entries: {reqs['entries']}")
print(f"Unpinned: {reqs['unpinned_packages']}")
if reqs['unpinned_list']:
    print(f"Missing pins: {', '.join(reqs['unpinned_list'])}")

# Full health check
health = deps_health_check()
print(f"Healthy: {health['is_healthy']}")
print(f"Recommendations: {health['recommendations']}")
```

## Dependency Best Practices

### Pin Your Dependencies

Always pin versions in `requirements.txt`:

```
# Good
requests==2.31.0
flask>=2.0.0,<3.0.0

# Bad (unpinned)
requests
flask
```

### Update Strategy

1. **Security updates** — Apply immediately
2. **Major versions** — Review changelog, test thoroughly
3. **Minor/patch** — Apply in regular maintenance

### Monitor Transitive Dependencies

Large transitive dependency trees:
- Increase security surface area
- Slow down installs
- Cause version conflicts

Keep `deps_transitive_count < 50`.

## CI/CD Integration

### GitHub Actions

```yaml
- name: Check Dependencies
  run: |
    pip install pipdeptree
    pyqual run --stage deps_check
```

### Pre-commit Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: check-deps
        name: Check outdated dependencies
        entry: python -c "from pyqual.plugins.deps import get_outdated_packages; import sys; sys.exit(1 if get_outdated_packages().get('has_major_outdated') else 0)"
        language: system
```

## Tags

- `dependencies`
- `outdated`
- `packages`
- `pip`
- `requirements`
- `licenses`

## Version

1.0.0
