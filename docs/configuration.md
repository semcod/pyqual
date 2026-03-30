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
      run: code2llm ./ -f toon,evolution
    
    - name: validate
      run: vallm batch ./ --recursive --errors-json > .pyqual/errors.json
    
    - name: fix
      run: echo "LLM fix placeholder — connect llx or aider here"
      when: metrics_fail    # only runs if gates fail
    
    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json
      when: always

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

## Stage Conditions

- `when: always` — run every iteration
- `when: metrics_fail` — only run if gates failed
- `when: metrics_pass` — only run if gates passed (rarely used)

## Stage Options

```yaml
stages:
  - name: analyze
    run: code2llm ./
    timeout: 600          # seconds (default: 300)
    when: always
    env:                  # stage-specific env vars
      DEBUG: "1"
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
| `DEFAULT_MAX_TOKENS` | `pyqual.llm` | 2000 | LLM max response tokens |
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

## Examples

See the [examples/](../examples/) directory for complete configurations:

- [Basic pipeline](../examples/basic/pyqual.yaml)
- [Linters (ruff, pylint, flake8, mypy)](../examples/linters/pyqual.yaml)
- [Security scanning](../examples/security/pyqual.yaml)
- [LLM fix with llx MCP](../examples/llm_fix/pyqual.yaml)
- [Custom gates](../examples/custom_gates/pyqual.yaml)
- [Multi-gate pipeline](../examples/multi_gate_pipeline/pyqual.yaml)
- [Ticket workflow](../examples/ticket_workflow/pyqual.yaml)
