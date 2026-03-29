# pyqual Examples

Real-world usage patterns for different project types and CI/CD setups.

## Available Examples

### Project Structures

| Example | Description | Best For |
|---------|-------------|----------|
| [python-package](python-package/) | Python package with src-layout | New libraries, PyPI packages |
| [python-flat](python-flat/) | Flat Python structure (no src/) | Simple scripts, small projects |
| [monorepo](monorepo/) | Multiple packages in one repo | Large projects, microservices |

### CI/CD Integrations

| Example | Platform | Features |
|---------|----------|----------|
| [github-actions](github-actions/) | GitHub Actions | PR checks, artifacts, coverage |
| [gitlab-ci](gitlab-ci/) | GitLab CI | Coverage reports, caching |

### Specialized Workflows

| Example | Focus | Tools |
|---------|-------|-------|
| [linters](linters/) | Code quality gates | ruff, pylint, flake8, mypy, interrogate |
| [security](security/) | Security scanning | bandit, pip-audit, trufflehog, sbom |
| [llm_fix](llm_fix/) | AI auto-fixing | Docker-backed llx MCP integration |
| [llx](llx/) | Intelligent LLM routing | LLX model selection, preLLM |
| [custom_gates](custom_gates/) | Custom metrics | Composite gates, custom collectors |

## Quick Reference

### Minimal Config

```yaml
pipeline:
  name: minimal
  metrics:
    coverage_min: 80
  stages:
    - name: test
      run: pytest --cov
  loop:
    max_iterations: 1
```

### With Linting

```yaml
pipeline:
  name: with-lint
  metrics:
    coverage_min: 80
  stages:
    - name: lint
      run: ruff check .
    - name: test
      run: pytest --cov
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
      run: code2llm ./ -f toon,evolution
    - name: validate
      run: vallm batch ./ --errors-json > .pyqual/errors.json
    - name: fix
      run: llx fix . --errors .pyqual/errors.json --verbose
      when: metrics_fail
    - name: test
      run: pytest --cov
  loop:
    max_iterations: 3
```

## Copy & Paste

Copy any example to your project:

```bash
# From pyqual repo root
cp examples/python-package/pyqual.yaml /path/to/your/project/
cd /path/to/your/project
pyqual run
```
