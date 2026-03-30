<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.29-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-129-green)
> **129** functions | **27** classes | **17** files | CC̄ = 4.7

> Auto-generated project documentation from source code analysis.

**Author:** Tom Sapletta  
**License:** Apache-2.0[(LICENSE)](./LICENSE)  
**Repository:** [https://github.com/semcod/pyqual](https://github.com/semcod/pyqual)

## Installation

### From PyPI

```bash
pip install pyqual
```

### From Source

```bash
git clone https://github.com/semcod/pyqual
cd pyqual
pip install -e .
```

### Optional Extras

```bash
pip install pyqual[analysis]    # analysis features
pip install pyqual[costs]    # costs features
pip install pyqual[dev]    # development tools
pip install pyqual[mcp]    # mcp features
pip install pyqual[all]    # all optional features
```

## Quick Start

### CLI Usage

```bash
# Initialize project with default pyqual.yaml
pyqual init

# Run the quality pipeline loop
pyqual run

# Check quality gates without running stages
pyqual gates

# Show current metrics
pyqual status

# Preview without executing
pyqual run --dry-run

# Manage tickets
pyqual tickets todo
pyqual tickets github

# Check tool availability
pyqual doctor
```

### Python API

```python
from pyqual import Pipeline, PyqualConfig, GateSet

# Run full pipeline
config = PyqualConfig.load("pyqual.yaml")
result = Pipeline(config).run()

# Check gates only
gate_set = GateSet(config.gates)
results = gate_set.check_all()
```

## How It Works

pyqual runs a loop: execute stages → collect metrics → check gates → if fail, fix → repeat.

```
pyqual run:
    Iteration 1 → analyze → validate → fix → test → check gates
                                                         │
                                              ┌── PASS ──┴── FAIL ──┐
                                              │                     │
                                           Done ✅          Iteration 2...
```

## Configuration

Create `pyqual.yaml` in your project root (or run `pyqual init`):

```yaml
pipeline:
  name: quality-loop
  metrics:
    cc_max: 15           # cyclomatic complexity ≤ 15
    coverage_min: 80     # test coverage ≥ 80%
    vallm_pass_min: 90   # validation pass rate ≥ 90%
  stages:
    - name: analyze
      run: code2llm ./ -f toon,evolution
    - name: validate
      run: vallm batch ./ --recursive --errors-json > .pyqual/errors.json
    - name: fix
      run: llx fix . --errors .pyqual/errors.json --verbose
      when: metrics_fail
    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json
  loop:
    max_iterations: 3
    on_fail: report
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
```

## Architecture

```
pyqual/
├── cli.py                  # CLI commands (typer)
├── config.py               # YAML configuration loader
├── gates.py                # Quality gate checking + metric collection
├── pipeline.py             # Pipeline loop executor
├── plugins.py              # Plugin system (MetricCollector base)
├── llm.py                  # LiteLLM wrapper
├── tickets.py              # Planfile ticket sync
└── integrations/
    ├── llx_mcp.py          # llx MCP client helpers
    └── llx_mcp_service.py  # MCP SSE service (ASGI)
```

## API Overview

### Classes

- **`LLMResponse`** — Response from LLM call.
- **`LLM`** — LiteLLM wrapper with .env configuration.
- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`SecurityCollector`** — Security scanning metrics from trufflehog, gitleaks, safety.
- **`LlxMcpFixCollector`** — Dockerized llx MCP fixer workflow results.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.
- **`LlxMcpRunResult`** — Result of an llx MCP fix workflow.
- **`LlxMcpClient`** — Thin MCP client for the llx SSE service.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`McpServiceState`** — Runtime state exposed via health and metrics endpoints.

### Functions

- `init(path)` — Create pyqual.yaml with sensible defaults.
- `run(config, dry_run, workdir)` — Execute pipeline loop until quality gates pass.
- `gates(config, workdir)` — Check quality gates without running stages.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `plugin(action, name, workdir, tag)` — Manage pyqual plugins - add, remove, search metric collectors.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `get_llm_model()` — Get LLM model from environment or default.
- `get_api_key()` — Get OpenRouter API key from environment.
- `get_llm(model)` — Get configured LLM instance.
- `sync_planfile_tickets(source, directory, dry_run, direction)` — Sync tickets via planfile backends.
- `sync_todo_tickets(directory, dry_run, direction)` — Sync TODO.md tickets through planfile's markdown backend.
- `sync_github_tickets(directory, dry_run, direction)` — Sync GitHub issues through planfile's GitHub backend.
- `sync_all_tickets(directory, dry_run, direction)` — Sync TODO.md and GitHub tickets through planfile.
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate YAML configuration snippet for a named plugin.
- `check_tool()` — —
- `build_fix_prompt(project_path, issues, analysis, prompt_limit)` — Build a concise prompt for llx/aider from gate failures.
- `run_llx_fix_workflow(workdir, project_path, issues_path, output_path)` — Run the analysis + fix workflow and save a JSON report.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `create_app(state, llx_server)` — Create an ASGI app that exposes the llx MCP server over SSE.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.


## Project Structure

📄 `examples.basic.check_gates`
📄 `examples.basic.minimal`
📄 `examples.basic.run_pipeline`
📄 `examples.custom_gates.dynamic_thresholds`
📄 `examples.llx.demo` (1 functions)
📄 `project`
📦 `pyqual`
📄 `pyqual.cli` (18 functions)
📄 `pyqual.config` (6 functions, 4 classes)
📄 `pyqual.gates` (31 functions, 3 classes)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (15 functions, 2 classes)
📄 `pyqual.integrations.llx_mcp_service` (15 functions, 1 classes)
📄 `pyqual.llm` (7 functions, 2 classes)
📄 `pyqual.pipeline` (7 functions, 4 classes)
📄 `pyqual.plugins` (24 functions, 11 classes)
📄 `pyqual.tickets` (6 functions)

## Requirements

- Python >= 3.9
- pyyaml >=6.0
- typer >=0.12
- rich >=13.0
- litellm >=1.0
- python-dotenv >=1.0
- mcp >=1.0
- prefact
- planfile

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Tom Sapletta <tom-sapletta-com@users.noreply.github.com>

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/semcod/pyqual
cd pyqual

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- [Quick Start](./docs/quickstart.md) — get up and running in 5 minutes
- [Configuration](./docs/configuration.md) — pyqual.yaml reference
- [Integrations](./docs/integrations.md) — pylint, ruff, bandit, pytest, llx, planfile…
- [Python API](./docs/api.md) — Pipeline, GateSet, Plugin system, LLM wrapper
- [Examples](./examples/) — real-world usage patterns

### Documentation Files

| File | Description |
|------|-------------|
| `docs/quickstart.md` | Quick start guide |
| `docs/configuration.md` | Configuration reference |
| `docs/integrations.md` | Tool integrations (13+ tools) |
| `docs/api.md` | Python API reference |
| `docs/index.md` | Documentation index |

<!-- code2docs:end -->