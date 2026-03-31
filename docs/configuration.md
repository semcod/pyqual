# Configuration Reference

Everything pyqual does is defined in `pyqual.yaml`.

## Quick Start with Profiles

The easiest way to get started — use a built-in profile:

```yaml
pipeline:
  profile: python        # analyze → validate → test → fix → verify
  metrics:
    coverage_min: 55     # override only what you need
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
```

Generate with: `pyqual init --profile python`

Available profiles:

| Profile | Stages | Description |
|---------|--------|-------------|
| `python` | analyze, validate, test, prefact, fix, verify | Standard Python quality loop |
| `python-full` | + push, publish | Full pipeline with goal push & publish |
| `ci` | analyze, validate, test | Report-only, no fix, single iteration |
| `lint-only` | lint, typecheck, test | Ruff + mypy, no LLM |
| `security` | analyze, audit, bandit, test | Security-focused scans |

Run `pyqual profiles` to see details. Profiles provide default stages, metrics, and loop settings — all overridable in your YAML.

## Full Example (without profile)

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

    - name: prefact
      tool: prefact
      when: metrics_fail   # run when quality gates fail
      optional: true

    - name: fix
      tool: llx-fix         # reads TODO.md from prefact
      when: metrics_fail
      optional: true

    - name: verify
      tool: pytest
      when: after_fix       # run after fix stage completes

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
| `prefact` | prefact | `TODO.md` | yes |
| `llx-fix` | llx | (applies fixes) | yes |
| `aider` | aider | (applies fixes) | yes |
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

| Condition | Triggers when | Typical stages |
|-----------|--------------|----------------|
| `always` | every iteration (default) | validate, test, benchmark |
| `first_iteration` | only iteration 1 | analyze, baseline, code2llm |
| `metrics_fail` | quality gates failed | prefact, fix, fix_regression |
| `metrics_pass` | all quality gates pass | push, publish, deploy |
| `after_fix` | any stage with "fix" in name ran (not skipped) | verify, verify_fix |
| `after_verify_fix` | any stage with "verify" in name ran (not skipped) | regression_report |
| `any_stage_fail` | a prior stage in this iteration failed | prefact, fix |

### Smart Defaults

pyqual **auto-infers** the `when:` condition from the stage name, so you often don't need to set it:

```yaml
stages:
  # These two are equivalent:
  - name: fix_regression
    run: llx fix . --apply
    when: metrics_fail        # explicit

  - name: fix_regression
    run: llx fix . --apply
    # when: is auto-set to metrics_fail because name contains "fix"
```

| Stage name pattern | Auto `when:` |
|---|---|
| `analyze`, `baseline`, `code2llm` | `first_iteration` |
| `fix`, `fix_regression`, `auto_fix`, `repair`, `prefact` | `metrics_fail` |
| `verify`, `verify_fix` | `after_fix` |
| `regression_report` | `after_verify_fix` |
| `push`, `publish`, `deploy` | `metrics_pass` |
| `test`, `lint`, `validate` | `always` |
| anything else | `always` |

You can always override with an explicit `when:` in your YAML.

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

## Goal Integration (Push & Publish)

pyqual can automatically push changes and publish packages when all quality gates pass using the **goal** tool:

```yaml
stages:
  # ... existing stages ...

  # Run only when all gates pass
  - name: push
    run: goal push --bump patch --no-publish --todo --model ${LLM_MODEL}
    when: metrics_pass
    optional: true
    timeout: 120

  - name: publish
    run: goal publish
    when: metrics_pass
    optional: true
    timeout: 300
```

### Goal options

- `--bump patch` — automatically bump version (patch/minor/major)
- `--no-publish` — skip publishing during push (handled by separate publish stage)
- `--todo` — create TODO.md with detected issues
- `--model ${LLM_MODEL}` — use same LLM model for commit message generation
- `optional: true` — skip gracefully if goal isn't installed

### What goal does

1. **push stage**:
   - Runs tests (if configured)
   - Generates a conventional commit message with AI
   - Updates CHANGELOG.md
   - Syncs version across files
   - Creates git tag
   - Pushes to remote

2. **publish stage**:
   - Publishes to package registry (PyPI, npm, etc.)
   - Can use Makefile publish target if available

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
│ 2026-03-30T07:19:01+00  │ INFO     │ pipeline_start  │ pyqual…  │ {stages: 4, gates: 3, ...}    │
│ 2026-03-30T07:19:02+00  │ INFO     │ stage_done      │ pyqual…  │ {stage: ruff, rc: 0, ...}     │
│ 2026-03-30T07:19:03+00  │ WARNING  │ gate_check      │ pyqual…  │ {metric: coverage, ok: false} │
│ 2026-03-30T07:19:03+00  │ INFO     │ pipeline_end    │ pyqual…  │ {final_ok: true, iter: 1}     │
└─────────────────────────┴──────────┴─────────────────┴──────────┴───────────────────────────────┘
```

### Key fields in kwargs

| Field | Description |
|-------|-------------|
| `event` | `pipeline_start`, `stage_done`, `gate_check`, `pipeline_end` |
| `returncode` | Normalized (0 for allow_failure linters) |
| `original_returncode` | Raw tool exit code (preserved for diagnosis) |
| `stdout_tail` | Last 500 chars of stdout (2000 for fix stages) |
| `stderr_tail` | Last 500 chars of stderr |
| `tool` | Preset name if used, null for `run:` commands |
| `ok` | Whether stage/gate passed |

### Viewing logs

```bash
pyqual logs                        # table view of all entries
pyqual logs --failed               # only failures (level=WARNING)
pyqual logs --stage fix --output   # fix stage with captured stdout/stderr
pyqual logs --json --failed        # JSON for llx/litellm auto-diagnosis
pyqual logs --tail 10              # last 10 entries
pyqual run --verbose               # live log output to stderr
pyqual run --stream                # real-time stdout/stderr streaming per stage
```

### Viewing LLX fix history

```bash
pyqual history                     # summary table of all LLX fix runs
pyqual history --prompts           # include full LLX prompts sent to the model
pyqual history --verbose           # include aider/llx stdout
pyqual history --json              # raw JSONL for LLM consumption
```

### Live log tailing (`pyqual watch`)

Monitor pipeline execution in real-time from a second terminal while `pyqual run` is active:

```bash
pyqual watch                       # live tail of pipeline.db events
pyqual watch --output              # include captured stage stdout/stderr
pyqual watch --prompts             # show LLX fix prompts as they appear
pyqual watch --interval 0.5        # faster polling (default: 1s)
```

> **📖 For comprehensive documentation on the database schema, all event types, SQL queries, and Python API — see [Logs & Data Access](logs-and-data.md).**

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

## AI Fix Tools

pyqual works with **any AI coding agent** that has a CLI: Claude Code, Codex CLI, Gemini CLI, aider, llx, Cursor, Windsurf, Cline, and more.

**→ See [AI Fix Tools](ai-fix-tools.md) for complete `pyqual.yaml` examples for each tool.**

## Examples

See the [examples/](../examples/) directory for complete configurations:

- [Basic pipeline](../examples/basic/pyqual.yaml)
- [Linters (ruff, pylint, flake8, mypy)](../examples/linters/pyqual.yaml)
- [Security scanning](../examples/security/pyqual.yaml)
- [LLM fix with llx MCP](../examples/llm_fix/pyqual.yaml)
- [Custom gates](../examples/custom_gates/pyqual.yaml)
- [Multi-gate pipeline](../examples/multi_gate_pipeline/pyqual.yaml)
- [Ticket workflow](../examples/ticket_workflow/pyqual.yaml)
