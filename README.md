# pyqual

## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.13-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$1.05-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-5.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $1.0500 (7 commits)
- 👤 **Human dev:** ~$500 (5.0h @ $100/h, 30min dedup)

Generated on 2026-03-29 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---



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

pyqual can be configured via `pyqual.yaml` or `[tool.pyqual]` in `pyproject.toml`:

### Option 1: pyqual.yaml (recommended)

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

### Option 2: pyproject.toml

If `pyqual.yaml` doesn't exist, pyqual will automatically check `pyproject.toml`:

```toml
[tool.pyqual]
name = "quality-loop"

[tool.pyqual.metrics]
cc_max = 15
vallm_pass_min = 90
coverage_min = 80

[[tool.pyqual.stages]]
name = "analyze"
run = "code2llm ./ -f toon,evolution"

[[tool.pyqual.stages]]
name = "test"
run = "pytest --cov --cov-report=json:.pyqual/coverage.json"
when = "always"

[tool.pyqual.loop]
max_iterations = 3
on_fail = "report"
```

## CLI

```bash
pyqual init              # create pyqual.yaml
pyqual run               # execute full loop
pyqual run --dry-run     # preview without executing
pyqual gates             # check gates without running stages
pyqual status            # show current metrics
pyqual doctor            # check tool availability
pyqual plugin list       # list available plugins
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

## LLM Integration

pyqual includes built-in LLM support via [liteLLM](https://litellm.ai/). Configure via `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=openrouter/qwen/qwen3-coder-next
```

Use in your code:

```python
from pyqual import get_llm

llm = get_llm()  # Auto-loads config from .env

# Simple completion
response = llm.complete("Explain Python decorators")
print(response.content)

# Fix code issues
response = llm.fix_code(
    code="def foo(x): return x + 1",  # missing type hints
    error="Function lacks type annotations"
)
print(response.content)

# Access cost info
print(f"Cost: ${response.cost:.4f}")
```

See [`examples/llm_fix/`](examples/llm_fix/) for complete examples.

## Metric sources

pyqual automatically collects metrics from:

| Source | Metrics | How |
|--------|---------|-----|
| `analysis_toon.yaml` | `cc` (CC̄), `critical` | Regex parse from code2llm output |
| `validation_toon.yaml` | `vallm_pass` | Pass rate from vallm batch |
| `.pyqual/errors.json` | `error_count` | Count of vallm errors |
| `.pyqual/coverage.json` | `coverage` | pytest-cov JSON report |

**Security & Dependencies:**

| Source | Metrics | File | Command |
|--------|---------|------|---------|
| pip-audit | `vuln_critical`, `vuln_high`, `vuln_medium`, `vuln_low`, `vuln_total` | `.pyqual/pip_audit.json` | `pip-audit --format=json` |
| bandit | `bandit_high`, `bandit_medium`, `bandit_low` | `.pyqual/bandit.json` | `bandit -r . -f json` |
| trufflehog/gitleaks | `secrets_found`, `secrets_severity` | `.pyqual/trufflehog.json` | `trufflehog filesystem . --json` |
| pip | `outdated_deps` | `.pyqual/outdated.json` | `pip list --outdated --format=json` |

**Code Quality:**

| Source | Metrics | File | Command |
|--------|---------|------|---------|
| mypy | `mypy_errors` | `.pyqual/mypy.json` | `mypy . --show-error-codes` |
| ruff | `ruff_errors`, `ruff_fatal`, `ruff_warnings` | `.pyqual/ruff.json` | `ruff check . --output-format=json` |
| pylint | `pylint_errors`, `pylint_score`, `pylint_fatal`, `pylint_warning` | `.pyqual/pylint.json` | `pylint . --output-format=json` |
| flake8 | `flake8_violations`, `flake8_errors`, `flake8_warnings`, `flake8_conventions` | `.pyqual/flake8.json` | `flake8 . --format=json` |
| radon | `mi_avg`, `mi_min`, `cc_rank_avg` | `.pyqual/radon_mi.json` | `radon mi . -j` |
| interrogate | `docstring_coverage`, `docstring_total`, `docstring_missing` | `.pyqual/interrogate.json` | `interrogate . -v --json` |
| pydocstyle | `pydocstyle_violations`, `pydocstyle_D<xxx>` | `.pyqual/pydocstyle.json` | `pydocstyle . --format=json` |
| pytest | `test_time`, `slow_tests` | `.pyqual/pytest_durations.json` | pytest with durations |

**Code Formatting:**

| Source | Metrics | File | Command |
|--------|---------|------|---------|
| black | `black_unformatted`, `black_files_changed` | `.pyqual/black.json` | `black --check --diff .` |
| isort | `isort_unsorted`, `isort_import_changes` | `.pyqual/isort.json` | `isort --check-only --diff .` |

**Import Structure:**

| Source | Metrics | File | Command |
|--------|---------|------|---------|
| import-linter | `import_violations`, `broken_import_contracts` | `.pyqual/import_linter.json` | `lint-imports` |

**SARIF Security:**

| Source | Metrics | File | Tools |
|--------|---------|------|-------|
| SARIF | `sarif_total`, `sarif_critical`, `sarif_high`, `sarif_medium`, `sarif_low`, `sarif_<rule_id>` | `.pyqual/*.sarif` | bandit, codeql, semgrep, etc. |

**Advanced Metrics:**

| Category | Available Metrics |
|----------|-------------------|
| Performance | `bench_time`, `bench_regression`, `mem_usage`, `cpu_time` |
| SBOM/Licensing | `sbom_compliance`, `sbom_coverage`, `vuln_supply_chain`, `license_blacklist` |
| Code Health | `unused_count`, `pyroma_score` |
| Git/Repo | `git_branch_age`, `todo_count`, `bus_factor`, `commit_frequency`, `contributor_diversity` |
| LLM Quality | `llm_pass_rate`, `code_bleu`, `ai_generated_pct`, `hallucination_rate`, `faithfulness_score` |
| AI Cost | `ai_cost` |
| i18n | `i18n_coverage`, `i18n_missing`, `i18n_total` |
| Accessibility | `a11y_issues`, `a11y_critical`, `a11y_score` |

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

## Examples

See [`examples/`](examples/) directory for real-world configurations:

**Project setups:**
- [`python-package`](examples/python-package/) — Standard Python package (src-layout)
- [`python-flat`](examples/python-flat/) — Simple project without src/
- [`monorepo`](examples/monorepo/) — Multiple packages in one repository

**Specialized configurations:**
- [`security/`](examples/security/) — Security-first scanning (bandit, pip-audit, secrets)
- [`linters/`](examples/linters/) — Comprehensive linting (ruff, pylint, flake8, mypy)

**CI/CD:**
- [`github-actions`](examples/github-actions/) — CI/CD with GitHub Actions
- [`gitlab-ci`](examples/gitlab-ci/) — CI/CD with GitLab CI

**Python API usage:**
- [`basic`](examples/basic/) — Using Pipeline and GateSet from Python
- [`llm_fix`](examples/llm_fix/) — LLM integration for auto-fixing code
- [`custom_gates`](examples/custom_gates/) — Custom quality gates and metrics

## Why not add this to algitex?

algitex has 29,448 lines, CC̄=3.6, 64 critical issues, vallm pass 42.8%. Adding more features makes it worse. pyqual does one thing well: declarative quality gate loops. algitex imports pyqual. Both improve.

## License

Licensed under Apache-2.0.
