# pyqual

**Declarative quality gate loops for AI-assisted development.**

One YAML file. One command. Pipeline iterates until your code meets quality thresholds.

```bash
pip install pyqual
pyqual init
pyqual run
```

## The problem

You use Copilot, Claude, GPT. They generate code. But nobody checks if that code meets your quality standards before it hits code review. And nobody automatically iterates if it doesn't.

pyqual closes that gap: define metrics → run tools → check gates → if fail, LLM fixes → re-check → repeat until pass.

## How it works

```
pyqual.yaml defines everything:
    ┌─────────────────────────────────────────┐
    │  metrics:                               │
    │    cc_max: 15        ← quality gates    │
    │    vallm_pass_min: 90                   │
    │    coverage_min: 80                     │
    │                                         │
    │  stages:                                │
    │    - analyze  (code2llm)                │
    │    - validate (vallm)                   │
    │    - fix      (llx/aider, when: fail)   │
    │    - test     (pytest)                  │
    │                                         │
    │  loop:                                  │
    │    max_iterations: 3                    │
    │    on_fail: report                      │
    └─────────────────────────────────────────┘

pyqual run:
    Iteration 1 → analyze → validate → fix → test → check gates
                                                         │
                                              ┌── PASS ──┴── FAIL ──┐
                                              │                     │
                                           Done ✅          Iteration 2...
```

## pyqual.yaml

```yaml
pipeline:
  name: quality-loop

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
      run: echo "Connect your LLM fixer here"
      when: metrics_fail    # only runs if gates fail

    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json

  loop:
    max_iterations: 3
    on_fail: report         # report | create_ticket | block
```

## CLI

```bash
pyqual init              # create pyqual.yaml
pyqual run               # execute full loop
pyqual run --dry-run     # preview without executing
pyqual gates             # check gates without running stages
pyqual status            # show current metrics
```

## Python API

```python
from pyqual import Pipeline, PyqualConfig

config = PyqualConfig.load("pyqual.yaml")
pipeline = Pipeline(config, workdir="./my-project")
result = pipeline.run()

if result.final_passed:
    print(f"All gates passed in {result.iteration_count} iterations")
else:
    print("Gates not met — check result.iterations for details")
```

## Metric sources

pyqual automatically collects metrics from:

| Source | Metrics | How |
|--------|---------|-----|
| `analysis_toon.yaml` | `cc` (CC̄), `critical` | Regex parse from code2llm output |
| `validation_toon.yaml` | `vallm_pass` | Pass rate from vallm batch |
| `.pyqual/errors.json` | `error_count` | Count of vallm errors |
| `.pyqual/coverage.json` | `coverage` | pytest-cov JSON report |

Custom metrics: extend `GateSet._collect_metrics()` or add your own collector.

## Gate operators

```yaml
metrics:
  cc_max: 15           # cc ≤ 15
  coverage_min: 80     # coverage ≥ 80
  critical_max: 0      # critical ≤ 0
  error_count_max: 5   # error_count ≤ 5
  vallm_pass_min: 90   # vallm_pass ≥ 90
```

Suffixes: `_max` → ≤, `_min` → ≥, `_lt` → <, `_gt` → >, `_eq` → =

## Integration with ecosystem

pyqual is intentionally small (~800 lines). It orchestrates, not implements:

- **code2llm** does analysis → pyqual reads the `.toon` output
- **vallm** does validation → pyqual reads pass rates
- **llx** does LLM routing → pyqual calls it as a stage
- **planfile** manages tickets → pyqual creates tickets on gate failure
- **costs** tracks spending → pyqual can gate on budget
- **algitex** can import pyqual as a dependency for its `go` command

## Why not add this to algitex?

algitex has 29,448 lines, CC̄=3.6, 64 critical issues, vallm pass 42.8%. Adding more features makes it worse. pyqual does one thing well: declarative quality gate loops. algitex imports pyqual. Both improve.

## License

Licensed under Apache-2.0.


Licensed under Apache-2.0.


Licensed under Apache-2.0.


Licensed under Apache-2.0.


Licensed under Apache-2.0.


Apache 2.0
