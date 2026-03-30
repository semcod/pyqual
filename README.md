# pyqual

## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.41-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
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
pyqual bulk-init .       # auto-generate pyqual.yaml for all subprojects
pyqual bulk-run .        # run all projects with live dashboard
pyqual run               # execute full loop
pyqual run --dry-run     # preview without executing
pyqual gates             # check gates without running stages
pyqual status            # show current metrics
pyqual doctor            # check tool availability
pyqual mcp-fix           # run the llx-backed MCP fix workflow
pyqual mcp-refactor      # run the llx-backed MCP refactor workflow
pyqual mcp-service       # start the persistent llx MCP service
pyqual tickets todo      # sync TODO.md through planfile
pyqual tickets github    # sync GitHub issues through planfile
pyqual tickets all       # sync TODO.md and GitHub tickets

# Plugin management
pyqual plugin list                   # list all plugins
pyqual plugin list --tag security     # filter by tag
pyqual plugin search <query>          # search plugins
pyqual plugin info <name>             # show plugin details
pyqual plugin add <name>              # add plugin to config
pyqual plugin remove <name>           # remove plugin from config
pyqual plugin validate                # validate configuration
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

The convenience wrapper now lives upstream in `llx.llm`; `pyqual` re-exports it so existing imports keep working.

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

## Docker-backed MCP fixer/refactor

If you want pyqual to delegate automatic fixes or refactors to a Dockerized `llx` MCP service:

The MCP client, service, workflow orchestration (`LlxMcpRunResult`, `run_llx_fix_workflow`,
`run_llx_refactor_workflow`), issue parsing and prompt building all live in the upstream
`llx` package (≥ 0.1.47). pyqual re-exports them for backward compatibility.
Install `pyqual[llx]` or `pyqual[mcp]` so those shared helpers are available.

```bash
docker compose -f examples/llm_fix/docker-compose.yml up --build -d
pyqual plugin add llx-mcp-fixer
pyqual run
```

The plugin writes results to `.pyqual/llx_mcp.json`, which is also collected by `pyqual status` and can be gated with `llx_fix_*` metrics.

If you only want to run the workflows directly, use:

```bash
pyqual mcp-fix --workdir . --project-path /workspace/project
pyqual mcp-refactor --workdir . --project-path /workspace/project
```

If you want to run the service standalone in development, use:

```bash
pyqual mcp-service --host 0.0.0.0 --port 8000
```

See [`examples/llm_fix/`](examples/llm_fix/) for complete examples.

## Metric sources

pyqual automatically collects metrics from:

| Source | File | Metrics |
|--------|------|---------|
| **Analysis** | `analysis_toon.yaml` | `cc` (CC̄), `critical` |
| **Validation** | `validation_toon.yaml` | `vallm_pass` |
| | `.pyqual/errors.json` | `error_count` |
| **Coverage** | `.pyqual/coverage.json` | `coverage` |
| **Performance** | `.pyqual/asv.json` | `bench_regression`, `bench_time` |
| | `.pyqual/mem.json` | `mem_usage`, `cpu_time` |
| **Security** | `.pyqual/secrets.json` | `secrets_severity`, `secrets_count` |
| | `.pyqual/vulns.json` | `vuln_critical`, `vuln_count` |
| | `.pyqual/sbom.json` | `sbom_compliance`, `license_blacklist` |
| **Project Health** | `.pyqual/vulture.json` | `unused_count` |
| | `.pyqual/pyroma.json` | `pyroma_score` |
| | `.pyqual/git_metrics.json` | `git_branch_age`, `todo_count` |
| **LLM/AI** | `.pyqual/humaneval.json` | `llm_pass_rate` |
| | `.pyqual/llm_analysis.json` | `llm_cc`, `hallucination_rate`, `prompt_bias_score`, `agent_efficiency` |
| | `.pyqual/llx_mcp.json` | `llx_fix_success`, `llx_fix_returncode`, `llx_tool_calls`, `llx_fix_tier_rank` |
| | `.pyqual/costs.json` | `ai_cost` |
| **Linting** | `.pyqual/ruff.json` | `ruff_errors`, `ruff_fatal`, `ruff_warnings` |
| | `.pyqual/pylint.json` | `pylint_errors`, `pylint_fatal`, `pylint_error`, `pylint_warnings`, `pylint_score` |
| | `.pyqual/flake8.json` | `flake8_violations`, `flake8_errors`, `flake8_warnings`, `flake8_conventions` |
| **Documentation** | `.pyqual/interrogate.json` | `docstring_coverage`, `docstring_total`, `docstring_missing` |

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
- **llx** does LLM routing, MCP workflows, issue parsing → pyqual calls it as a stage (requires Python ≥ 3.10)
- **planfile** manages tickets → pyqual syncs TODO.md and GitHub tickets through planfile
- **costs** tracks spending → pyqual can gate on budget
- **algitex** can import pyqual as a dependency for its `go` command

## Examples

See [`examples/`](examples/) directory for real-world configurations:

**Project setups:**
- [`python-package`](examples/python-package/) — Standard Python package (src-layout)
- [`python-flat`](examples/python-flat/) — Simple project without src/
- [`monorepo`](examples/monorepo/) — Multiple packages in one repository

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
