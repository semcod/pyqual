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

With `tool:` presets, pyqual handles all output capture automatically:

```yaml
stages:
  - name: ruff
    tool: ruff         # → .pyqual/ruff.json
  - name: pylint
    tool: pylint       # → .pyqual/pylint.json
  - name: flake8
    tool: flake8       # → .pyqual/flake8.json
  - name: mypy
    tool: mypy         # → .pyqual/mypy.json
  - name: interrogate
    tool: interrogate  # → .pyqual/interrogate.json
```

No shell redirections or error handling needed — pyqual manages it all.

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for complete configuration with all linters.
