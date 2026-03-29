# Python Linters Example

Quality gates for Python code linting using ruff, pylint, flake8, mypy, and interrogate.

## Quick Start

```bash
# Install linters
pip install ruff pylint flake8 mypy interrogate

# Run with pyqual
pyqual run
```

## Tools

| Tool | Purpose | Output File |
|------|---------|-------------|
| ruff | Modern Python linter | `.pyqual/ruff.json` |
| pylint | Comprehensive static analysis | `.pyqual/pylint.json` |
| flake8 | Style guide enforcement | `.pyqual/flake8.json` |
| mypy | Type checking | `.pyqual/mypy.json` |
| interrogate | Docstring coverage | `.pyqual/interrogate.json` |

## Metrics

| Metric | Description | Gate |
|--------|-------------|------|
| `ruff_errors` | Total ruff violations | ≤ 10 |
| `ruff_fatal` | Fatal errors (E,F codes) | ≤ 0 |
| `pylint_score` | Pylint rating (0-10) | ≥ 8.0 |
| `flake8_violations` | Total flake8 issues | ≤ 20 |
| `mypy_errors` | Type errors count | ≤ 5 |
| `docstring_coverage` | Docstring coverage % | ≥ 90% |

## Generating Reports

```bash
# ruff JSON output
ruff check . --output-format=json > .pyqual/ruff.json

# pylint JSON output
pylint --output-format=json . > .pyqual/pylint.json 2>/dev/null || true

# flake8 with JSON formatter
flake8 --format=json . > .pyqual/flake8.json 2>/dev/null || true

# mypy JSON
mypy --output=json . > .pyqual/mypy.json 2>/dev/null || true

# interrogate JSON
interrogate --generate-badge=never --format=json . > .pyqual/interrogate.json
```

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for complete configuration with all linters.
