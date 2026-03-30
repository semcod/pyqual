# Multi-Gate Pipeline Example

A comprehensive pipeline combining **linters**, **security scanning**, **AI validation**, and **testing** with auto-fix and ticket creation.

## Overview

This example demonstrates a production-grade pyqual pipeline that:
1. Analyzes code complexity with `code2llm`
2. Runs 5 linters in sequence (ruff, pylint, flake8, mypy, interrogate)
3. Scans for security issues (bandit, pip-audit, trufflehog)
4. Validates with AI (`vallm`)
5. Auto-fixes on failure (`llx`)
6. Runs tests with coverage
7. Checks maintainability index (`radon`)
8. Creates TODO.md tickets for remaining failures

## Quality Gates (21 gates)

### Complexity
| Metric | Gate | Tool |
|--------|------|------|
| `cc` | ≤ 15 | code2llm |
| `maintainability_index` | ≥ 65 | radon |

### Coverage
| Metric | Gate | Tool |
|--------|------|------|
| `coverage` | ≥ 85% | pytest-cov |

### Linters
| Metric | Gate | Tool |
|--------|------|------|
| `ruff_errors` | ≤ 5 | ruff |
| `ruff_fatal` | ≤ 0 | ruff |
| `pylint_score` | ≥ 8.0 | pylint |
| `flake8_violations` | ≤ 10 | flake8 |
| `mypy_errors` | ≤ 0 | mypy |
| `docstring_coverage` | ≥ 85% | interrogate |

### Security
| Metric | Gate | Tool |
|--------|------|------|
| `bandit_high` | ≤ 0 | bandit |
| `bandit_medium` | ≤ 3 | bandit |
| `vuln_critical` | ≤ 0 | pip-audit |
| `vuln_high` | ≤ 0 | pip-audit |
| `secrets_found` | ≤ 0 | trufflehog/gitleaks |

### AI Validation
| Metric | Gate | Tool |
|--------|------|------|
| `vallm_pass` | ≥ 90% | vallm |

## Quick Start

```bash
# Install all tools
pip install pyqual[all] ruff pylint flake8 mypy interrogate bandit radon

# Copy config
cp pyqual.yaml /path/to/your/project/
cd /path/to/your/project

# Run the full pipeline
pyqual run

# Or check gates only
pyqual gates
```

## Pipeline Flow

```
Iteration 1:
  analyze → ruff → pylint → flake8 → mypy → interrogate →
  bandit → pip-audit → secrets → validate → [fix] → test → radon
  → CHECK GATES
      ├── ALL PASS → Done ✅
      └── FAIL → create ticket → Iteration 2...
```

## Customization

- Remove stages you don't need (e.g., drop `mypy` if you don't use type hints)
- Adjust thresholds to match your project's maturity
- Change `on_fail: create_ticket` to `report` for CI/CD (no file writes)
- Add `timeout` per stage for slow tools

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for the complete 21-gate configuration.
