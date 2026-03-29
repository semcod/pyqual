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
    timeout: 300          # seconds (default: 60)
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
- `create_ticket` — create planfile tickets for failures
- `block` — exit immediately on first failure

## Environment Variables

Set global environment for all stages:

```yaml
env:
  LLM_MODEL: openrouter/qwen/qwen3-coder-next
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Or use shell variable syntax in stage commands.
