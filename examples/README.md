# pyqual Examples

Real-world usage patterns for different project types and CI/CD setups.

## Available Examples

### Basics & API

| Example | Description | Files |
|---------|-------------|-------|
| [basic](basic/) | Python API usage — Pipeline, GateSet, minimal | 3 scripts + yaml |
| [python-package](python-package/) | Python package with src-layout | yaml |
| [python-flat](python-flat/) | Flat Python structure (no src/) | yaml |
| [monorepo](monorepo/) | Multiple packages in one repo | yaml |

### Quality & Linting

| Example | Description | Tools |
|---------|-------------|-------|
| [linters](linters/) | Code quality gates | ruff, pylint, flake8, mypy, interrogate |
| [security](security/) | Security scanning (full config) | bandit, pip-audit, gitleaks, sbom |
| [security-profile](security-profile/) | Security scanning (built-in profile) | profile: security |
| [custom_gates](custom_gates/) | Dynamic thresholds, composite scoring, metric history | pyqual API |
| [custom_plugins](custom_plugins/) | Build your own MetricCollector plugins | pyqual plugin system |

### AI & LLM

| Example | Description | Tools |
|---------|-------------|-------|
| [llm_fix](llm_fix/) | Docker-backed llx MCP fix workflow | llx, aider, Docker |
| [llx](llx/) | Standalone llx integration pipeline | llx, code2llm, vallm |

> **📖 pyqual supports any AI coding agent with a CLI as a fix stage — Claude Code, Codex CLI, Gemini CLI, aider, llx, Cursor, Windsurf, Cline.
> See [AI Fix Tools](../docs/ai-fix-tools.md) for complete `pyqual.yaml` examples for each tool.**

### CI/CD

| Example | Platform | Features |
|---------|----------|----------|
| [github-actions](github-actions/) | GitHub Actions | PR checks, artifacts, coverage |
| [gitlab-ci](gitlab-ci/) | GitLab CI | Coverage reports, caching |

### Advanced

| Example | Description | Key Feature |
|---------|-------------|-------------|
| [multi_gate_pipeline](multi_gate_pipeline/) | 21-gate production pipeline | Linters + security + AI + testing combined |
| [ticket_workflow](ticket_workflow/) | Planfile ticket sync on gate failures | Auto TODO.md + GitHub Issues |
| [ticket_backends](ticket_backends/) | Multi-backend ticket configuration | markdown, github, all backends |

## Quick Reference

### Minimal Config

```yaml
pipeline:
  name: minimal
  metrics:
    coverage_min: 80
  stages:
    - name: test
      tool: pytest
  loop:
    max_iterations: 1
```

### With Linting

```yaml
pipeline:
  name: with-lint
  metrics:
    coverage_min: 80
    ruff_errors_max: 5
  stages:
    - name: lint
      tool: ruff
    - name: test
      tool: pytest
  loop:
    max_iterations: 1
```

### Multi-Iteration (Auto-Fix with LLX)

```yaml
pipeline:
  name: auto-fix-llx
  metrics:
    coverage_min: 90
    cc_max: 15
    vallm_pass_min: 90
  stages:
    - name: analyze
      tool: code2llm
    - name: validate
      tool: vallm
    - name: fix
      run: llx fix . --errors .pyqual/errors.json --verbose
      when: metrics_fail
    - name: test
      tool: pytest
  loop:
    max_iterations: 3
    on_fail: create_ticket
```

### With Custom Plugins

```yaml
pipeline:
  name: with-plugins
  metrics:
    perf_p99_ms_max: 200
    health_score_min: 70
    coverage_min: 80
  stages:
    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json
    - name: loadtest
      run: locust --headless -u 50 --json > .pyqual/performance.json
  loop:
    max_iterations: 1
```

## Copy & Paste

Copy any example to your project:

```bash
# From pyqual repo root
cp examples/multi_gate_pipeline/pyqual.yaml /path/to/your/project/
cd /path/to/your/project
pyqual run
```

## Documentation

- [Quick Start](../docs/quickstart.md) — get up and running in 5 minutes
- [Configuration Reference](../docs/configuration.md) — all pyqual.yaml options
- [Integrations](../docs/integrations.md) — 13+ supported tools
- [Python API](../docs/api.md) — Pipeline, GateSet, Plugin system, LLM wrapper
