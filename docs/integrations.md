# Ecosystem Integrations

pyqual is intentionally small (~800 lines). It orchestrates, not implements. It reads metrics from tools you already use.

## planfile → Ticket Management

pyqual integrates with **planfile** to manage tickets from `TODO.md` and GitHub Issues.

### Commands

```bash
pyqual tickets todo      # sync TODO.md through planfile
pyqual tickets github    # sync GitHub issues through planfile
pyqual tickets all       # sync both TODO.md and GitHub
```

### Configuration

Enable automatic ticket sync on gate failure:

```yaml
loop:
  on_fail: create_ticket  # triggers planfile TODO sync
```

### How it works

- **TODO.md**: pyqual uses planfile's markdown backend to parse and sync checklist items
- **GitHub Issues**: pyqual uses planfile's GitHub backend to sync issues with your repository
- **Automatic sync**: When `on_fail: create_ticket` is set, failed quality gates trigger TODO.md synchronization

### Requirements

planfile is included as a dependency. Ensure you have `.planfile/` directory initialized in your project root.

## code2llm → Complexity Metrics

```yaml
stages:
  - name: analyze
    run: code2llm ./ -f toon,evolution
```

pyqual reads from `analysis_toon.yaml` or `analysis.toon`:

```yaml
SUMMARY:
  CC̄=2.5          # average cyclomatic complexity
  critical=0       # critical issues count
```

**Metrics extracted:** `cc`, `critical`

## vallm → Validation Pass Rate

```yaml
stages:
  - name: validate
    run: vallm batch ./ --recursive --errors-json > .pyqual/errors.json
```

pyqual reads from `validation_toon.yaml` or reads `.pyqual/errors.json`:

```yaml
SUMMARY:
  scanned: 100
  passed: 95 (95.0%)    # vallm_pass metric
  warnings: 5
```

**Metrics extracted:** `vallm_pass`, `error_count`

## pytest → Coverage

```yaml
stages:
  - name: test
    run: pytest --cov --cov-report=json:.pyqual/coverage.json
```

pyqual reads from `.pyqual/coverage.json` (pytest-cov output):

```json
{
  "totals": {
    "percent_covered": 92.5
  }
}
```

**Metrics extracted:** `coverage`

## pylint → Code Quality Score

```yaml
stages:
  - name: pylint
    run: pylint --output-format=json . > .pyqual/pylint.json 2>/dev/null || true
```

pyqual reads `.pyqual/pylint.json` (list of messages or dict with score):

**Metrics extracted:** `pylint_score`, `pylint_errors`, `pylint_fatal`, `pylint_error`, `pylint_warnings`

## ruff → Modern Linting

```yaml
stages:
  - name: ruff
    run: ruff check . --output-format=json > .pyqual/ruff.json 2>/dev/null || true
```

**Metrics extracted:** `ruff_errors`, `ruff_fatal`, `ruff_warnings`

## flake8 → Style Guide

```yaml
stages:
  - name: flake8
    run: flake8 --format=json . > .pyqual/flake8.json 2>/dev/null || true
```

**Metrics extracted:** `flake8_violations`, `flake8_errors`, `flake8_warnings`

## bandit → Security Issues

```yaml
stages:
  - name: bandit
    run: bandit -r . -f json -o .pyqual/bandit.json 2>/dev/null || true
```

**Metrics extracted:** `bandit_high`, `bandit_medium`, `bandit_low`, `bandit_total`

## radon → Maintainability Index

```yaml
stages:
  - name: radon
    run: radon mi . -j > .pyqual/radon.json 2>/dev/null || true
```

**Metrics extracted:** `maintainability_index`, `radon_cc`

## interrogate → Docstring Coverage

```yaml
stages:
  - name: interrogate
    run: interrogate --generate-badge=never --format=json . > .pyqual/interrogate.json
```

**Metrics extracted:** `docstring_coverage`, `docstring_missing`

## pip-audit / safety → Vulnerability Scanning

```yaml
stages:
  - name: pip-audit
    run: pip-audit --format=json --output=.pyqual/vulns.json 2>/dev/null || true
```

**Metrics extracted:** `vuln_critical`, `vuln_high`, `vuln_medium`, `vuln_total`

## llx MCP → AI-Powered Fixes

Use the built-in `llx-fix` preset for automatic code repair:

```yaml
stages:
  - name: prefact
    tool: prefact           # analyze issues → TODO.md
    when: any_stage_fail
    optional: true

  - name: fix
    tool: llx-fix           # apply fixes from TODO.md
    when: any_stage_fail
    optional: true
    timeout: 1800
```

Or use `aider` for AI pair-programming:

```yaml
stages:
  - name: aider-fix
    tool: aider
    when: any_stage_fail
    optional: true
```

The MCP workflow:
1. Analyzes the project via `llx_analyze`
2. Builds a fix/refactor prompt from gate failures or `TODO.md` issues
3. Calls `aider` through the MCP service
4. Saves results to `.pyqual/llx_mcp.json`

Use `pyqual mcp-refactor` when you want the same flow framed as a refactor task rather than a bugfix.

See [examples/llm_fix/](../examples/llm_fix/) and [examples/llx/](../examples/llx/) for Docker-based and standalone setups.

## Custom Integrations

Extend `GateSet._collect_metrics()` or build a plugin:

```python
from pyqual.gates import GateSet
from pathlib import Path

class MyGateSet(GateSet):
    def _collect_metrics(self, workdir: Path) -> dict[str, float]:
        metrics = super()._collect_metrics(workdir)
        metrics.update(self._from_my_tool(workdir))
        return metrics

    def _from_my_tool(self, workdir: Path) -> dict[str, float]:
        return {"my_metric": 42.0}
```

Or use the plugin system (see [Plugin API](api.md#plugin-api) and [examples/custom_plugins/](../examples/custom_plugins/)).

## Integration Summary

| Tool | Output File | Metrics | Optional? |
|------|-------------|---------|-----------|
| code2llm | `analysis_toon.yaml` | `cc`, `critical` | Yes |
| vallm | `validation_toon.yaml` | `vallm_pass`, `error_count` | Yes |
| pytest | `.pyqual/coverage.json` | `coverage` | Yes |
| pylint | `.pyqual/pylint.json` | `pylint_score`, `pylint_errors`, `pylint_fatal`, `pylint_warnings` | Yes |
| ruff | `.pyqual/ruff.json` | `ruff_errors`, `ruff_fatal`, `ruff_warnings` | Yes |
| flake8 | `.pyqual/flake8.json` | `flake8_violations`, `flake8_errors`, `flake8_warnings` | Yes |
| bandit | `.pyqual/bandit.json` | `bandit_high`, `bandit_medium`, `bandit_low` | Yes |
| radon | `.pyqual/radon.json` | `maintainability_index`, `radon_cc` | Yes |
| interrogate | `.pyqual/interrogate.json` | `docstring_coverage`, `docstring_missing` | Yes |
| pip-audit | `.pyqual/vulns.json` | `vuln_critical`, `vuln_high`, `vuln_total` | Yes |
| planfile | `.planfile/` | Ticket management (TODO.md, GitHub) | Yes |
| llx MCP | `.pyqual/llx_mcp.json` | AI fix/refactor results | Yes |
| llx fix | (code changes) | Applies fixes from TODO.md | Yes |
| prefact | `TODO.md` | Issue detection for llx fix | Yes |
| custom | any | any | — |

**All integrations are optional.** Stages can be any shell commands.

## Examples

- [Linters pipeline](../examples/linters/) — ruff, pylint, flake8, mypy, interrogate
- [Security scanning](../examples/security/) — bandit, pip-audit, trufflehog, SBOM
- [LLM fix/refactor (Docker)](../examples/llm_fix/) — Dockerized llx MCP workflow
- [LLX integration](../examples/llx/) — standalone llx pipeline
- [Multi-gate pipeline](../examples/multi_gate_pipeline/) — combining all tools
