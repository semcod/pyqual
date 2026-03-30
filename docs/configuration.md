# Configuration Reference

Everything pyqual does is defined in `pyqual.yaml`.

## Full Example

```yaml
pipeline:
  name: quality-loop

  # Quality gates — pipeline iterates until ALL pass
  metrics:
    cc_max: 15           # cyclomatic complexity per function
    vallm_pass_min: 90   # vallm validation pass rate (%)
    coverage_min: 80     # test coverage (%)

  stages:
    - name: analyze
      tool: code2llm           # built-in preset

    - name: validate
      tool: vallm

    - name: fix
      run: llx fix . --errors .pyqual/errors.json --verbose
      when: metrics_fail       # only runs if gates fail

    - name: test
      tool: pytest

  # Loop behavior
  loop:
    max_iterations: 3
    on_fail: report      # report | create_ticket | block

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
```

## Gate Operators

| Suffix | Operator | Example |
|--------|----------|---------|
| `_max` | ≤ | `cc_max: 15` → cc ≤ 15 |
| `_min` | ≥ | `coverage_min: 80` → coverage ≥ 80 |
| `_lt` | < | `critical_lt: 1` → critical < 1 |
| `_gt` | > | `lines_gt: 100` → lines > 100 |
| `_eq` | = | `version_eq: 1.0` → version = 1.0 |

## Tool Presets

Instead of writing complex shell commands with output redirection, use built-in `tool:` presets:

```yaml
stages:
  # Before (verbose, error-prone):
  - name: ruff
    run: ruff check . --output-format=json > .pyqual/ruff.json 2>/dev/null || true

  # After (pyqual handles invocation, output, and errors):
  - name: ruff
    tool: ruff
```

pyqual automatically:
- Runs the correct command with JSON output flags
- Captures output to `.pyqual/<tool>.json`
- Handles non-zero exit codes gracefully (for linters/scanners)
- Skips optional tools that aren't installed

### Available presets

| Preset | Binary | Output | Fail-safe |
|--------|--------|--------|-----------|
| `ruff` | ruff | `.pyqual/ruff.json` | yes |
| `pylint` | pylint | `.pyqual/pylint.json` | yes |
| `flake8` | flake8 | `.pyqual/flake8.json` | yes |
| `mypy` | mypy | `.pyqual/mypy.json` | yes |
| `interrogate` | interrogate | `.pyqual/interrogate.json` | yes |
| `radon` | radon | `.pyqual/radon.json` | yes |
| `bandit` | bandit | `.pyqual/bandit.json` | yes |
| `pip-audit` | pip-audit | `.pyqual/vulns.json` | yes |
| `trufflehog` | trufflehog | `.pyqual/secrets.json` | yes |
| `gitleaks` | gitleaks | `.pyqual/secrets.json` | yes |
| `safety` | safety | `.pyqual/safety.json` | yes |
| `pytest` | pytest | `.pyqual/coverage.json` | **no** |
| `code2llm` | code2llm | (toon files) | **no** |
| `vallm` | vallm | `.pyqual/errors.json` | **no** |
| `cyclonedx` | cyclonedx-py | `.pyqual/sbom.json` | yes |

List presets: `pyqual tools`

### Custom presets (external packages)

Register your own tool presets without modifying pyqual — three methods:

**1. `custom_tools:` in pyqual.yaml** (simplest):

```yaml
pipeline:
  custom_tools:
    - name: my-linter
      binary: my-linter
      command: "my-linter check {workdir} --json"
      output: .pyqual/my-linter.json
      allow_failure: true

  stages:
    - name: lint
      tool: my-linter
```

**2. Python API** (`register_preset`):

```python
from pyqual.tools import ToolPreset, register_preset

register_preset("my-linter", ToolPreset(
    binary="my-linter",
    command="my-linter check {workdir} --json",
    output=".pyqual/my-linter.json",
))
```

**3. Entry points** (for distributable packages):

```toml
# In your package's pyproject.toml:
[project.entry-points."pyqual.tools"]
my-linter = "my_package:MY_PRESET"   # MY_PRESET is a ToolPreset instance
```

pyqual auto-discovers entry points at config load time.

### Optional tools

Skip stages silently when a tool isn't installed:

```yaml
stages:
  - name: secrets
    tool: trufflehog
    optional: true       # skipped if trufflehog not on PATH
```

## Stage Conditions

- `when: always` — run every iteration
- `when: metrics_fail` — only run if gates failed
- `when: metrics_pass` — only run if gates passed (rarely used)

## Stage Options

Use `tool:` for built-in presets or `run:` for custom commands:

```yaml
stages:
  # Built-in preset:
  - name: lint
    tool: ruff
    optional: true
    when: always

  # Custom command:
  - name: custom-step
    run: my-tool --flag
    timeout: 600          # seconds (default: 300)
    when: always
```

## Loop Behavior

```yaml
loop:
  max_iterations: 3       # stop after N iterations
  on_fail: report         # report | create_ticket | block
```

- `report` — print results, exit with error code
- `create_ticket` — sync TODO.md tickets via planfile when gates fail
- `block` — exit immediately on first failure

## Ticket Management Commands

pyqual integrates with **planfile** to manage tickets from `TODO.md` and GitHub Issues:

```bash
pyqual tickets todo      # sync TODO.md through planfile
pyqual tickets github    # sync GitHub issues through planfile
pyqual tickets all       # sync both TODO.md and GitHub
```

To enable automatic ticket sync on gate failure:

```yaml
loop:
  on_fail: create_ticket  # triggers planfile TODO sync
```

## Environment Variables

Set global environment for all stages:

```yaml
env:
  LLM_MODEL: openrouter/qwen/qwen3-coder-next
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Or use shell variable syntax in stage commands.

## Named Constants

pyqual uses named constants for all default values. Override them in `pyqual.yaml` or programmatically:

| Constant | Module | Default | Description |
|----------|--------|---------|-------------|
| `DEFAULT_STAGE_TIMEOUT` | `pyqual.config` | 300 | Stage timeout in seconds |
| `DEFAULT_MCP_PORT` | `pyqual.cli` | 8000 | MCP service port |
| `DEFAULT_MAX_TOKENS` | `llx.llm` (re-exported by `pyqual.llm`) | 2000 | LLM max response tokens |
| `TIMEOUT_EXIT_CODE` | `pyqual.pipeline` | 124 | Exit code for timed-out stages |

## Plugin Configuration

Add plugin metrics to your pipeline:

```yaml
pipeline:
  metrics:
    # Built-in plugin metrics
    pass_at_1_min: 0.8        # LLM benchmark (llm-bench plugin)
    hallucination_rate_max: 5  # Hallucination rate (hallucination plugin)
    sbom_compliance_min: 95    # SBOM compliance (sbom plugin)
    a11y_score_min: 90         # Accessibility score (a11y plugin)
    bus_factor_min: 2          # Bus factor (repo-metrics plugin)
```

Generate a plugin config snippet:

```bash
pyqual plugin info llm-bench
pyqual plugin add llm-bench
```

## Pipeline Logging (nfo SQLite)

Every `pyqual run` writes structured logs to `.pyqual/pipeline.db` via [nfo](https://pypi.org/project/nfo/) (SQLite-backed):

```
pipeline_logs table:
┌─────────────────────────┬──────────┬─────────────────┬──────────┬───────────────────────────────┐
│ timestamp               │ level    │ function_name   │ module   │ kwargs (structured data)      │
├─────────────────────────┼──────────┼─────────────────┼──────────┼───────────────────────────────┤
│ 2026-03-30T07:19:01+00  │ INFO     │ pipeline_start  │ pyqual…  │ {stages: 4, gates: 3, ...}   │
│ 2026-03-30T07:19:02+00  │ INFO     │ stage_done      │ pyqual…  │ {stage: ruff, rc: 0, ...}    │
│ 2026-03-30T07:19:03+00  │ WARNING  │ gate_check      │ pyqual…  │ {metric: coverage, ok: false} │
│ 2026-03-30T07:19:03+00  │ INFO     │ pipeline_end    │ pyqual…  │ {final_ok: true, iter: 1}    │
└─────────────────────────┴──────────┴─────────────────┴──────────┴───────────────────────────────┘
```

### Key fields in kwargs

| Field | Description |
|-------|-------------|
| `event` | `pipeline_start`, `stage_done`, `gate_check`, `pipeline_end` |
| `returncode` | Normalized (0 for allow_failure linters) |
| `original_returncode` | Raw tool exit code (preserved for diagnosis) |
| `stderr_tail` | Last 500 chars of stderr (only on failure) |
| `tool` | Preset name if used, null for `run:` commands |
| `ok` | Whether stage/gate passed |

### Viewing logs

```bash
pyqual logs                    # table view
pyqual logs --failed           # only failures (level=WARNING)
pyqual logs --json --failed    # JSON for llx/litellm auto-diagnosis
pyqual logs --tail 10          # last 10 entries
pyqual run --verbose           # live log output to stderr
```

### SQL access

Query the nfo SQLite DB directly for advanced analysis:

```bash
pyqual logs --sql "SELECT function_name, kwargs FROM pipeline_logs WHERE level='WARNING'"
pyqual logs --sql "SELECT COUNT(*) as runs FROM pipeline_logs WHERE function_name='pipeline_end'"
```

Or from Python / LLM tools:

```python
import sqlite3
conn = sqlite3.connect(".pyqual/pipeline.db")
rows = conn.execute("SELECT * FROM pipeline_logs WHERE level='WARNING'").fetchall()
```

### LLM auto-diagnosis workflow

```bash
# 1. Run pipeline
pyqual run

# 2. Extract failures as JSON for LLM
pyqual logs --json --failed > .pyqual/failures.json

# 3. Feed to llx for auto-fix
llx fix . --errors .pyqual/failures.json --verbose
```

## Examples

See the [examples/](../examples/) directory for complete configurations:

- [Basic pipeline](../examples/basic/pyqual.yaml)
- [Linters (ruff, pylint, flake8, mypy)](../examples/linters/pyqual.yaml)
- [Security scanning](../examples/security/pyqual.yaml)
- [LLM fix with llx MCP](../examples/llm_fix/pyqual.yaml)
- [Custom gates](../examples/custom_gates/pyqual.yaml)
- [Multi-gate pipeline](../examples/multi_gate_pipeline/pyqual.yaml)
- [Ticket workflow](../examples/ticket_workflow/pyqual.yaml)
