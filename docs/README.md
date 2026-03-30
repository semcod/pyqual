<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-145-green)
> **145** functions | **29** classes | **23** files | CC̄ = 4.7

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

# List available tool presets
pyqual tools

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

## Tool Presets

Use `tool:` instead of complex shell commands — pyqual handles invocation, output capture, and error handling:

```yaml
stages:
  - name: lint
    tool: ruff           # built-in preset

  - name: secrets
    tool: trufflehog
    optional: true       # skip if not installed

  - name: custom
    run: my-tool --flag  # custom command still works
```

**15 built-in presets:** ruff, pylint, flake8, mypy, interrogate, radon, bandit, pip-audit, trufflehog, gitleaks, safety, pytest, code2llm, vallm, cyclonedx

List all: `pyqual tools`

## Architecture

```
pyqual/
├── cli.py                  # CLI commands (typer)
├── config.py               # YAML configuration loader
├── gates.py                # Quality gate checking + metric collection
├── pipeline.py             # Pipeline loop executor
├── plugins.py              # Plugin system (MetricCollector base)
├── tools.py                # Built-in tool presets (15 tools)
├── llm.py                  # LiteLLM wrapper
├── tickets.py              # Planfile ticket sync
└── integrations/
    ├── llx_mcp.py          # llx MCP client helpers
    └── llx_mcp_service.py  # MCP SSE service (ASGI)
```

## API Overview

### Classes

- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`LLMResponse`** — Response from LLM call.
- **`LLM`** — LiteLLM wrapper with .env configuration.
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
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
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
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `build_fix_prompt(project_path, issues, analysis, prompt_limit)` — Build a concise prompt for llx/aider from gate failures.
- `run_llx_fix_workflow(workdir, project_path, issues_path, output_path)` — Run the analysis + fix workflow and save a JSON report.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `check_tool()` — —
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
- `create_app(state, llx_server)` — Create an ASGI app that exposes the llx MCP server over SSE.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.


## Project Structure

📄 `examples.basic.check_gates`
📄 `examples.basic.minimal`
📄 `examples.basic.run_pipeline`
📄 `examples.custom_gates.composite_gates` (2 functions)
📄 `examples.custom_gates.dynamic_thresholds`
📄 `examples.custom_gates.metric_history` (4 functions)
📄 `examples.custom_plugins.code_health_collector` (2 functions, 1 classes)
📄 `examples.custom_plugins.performance_collector` (2 functions, 1 classes)
📄 `examples.llx.demo` (1 functions)
📄 `examples.multi_gate_pipeline.run_pipeline` (2 functions)
📄 `examples.ticket_workflow.sync_tickets` (3 functions)
📄 `project`
📦 `pyqual`
📄 `pyqual.cli` (18 functions)
📄 `pyqual.config` (6 functions, 4 classes)
📄 `pyqual.gates` (32 functions, 3 classes)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (15 functions, 2 classes)
📄 `pyqual.integrations.llx_mcp_service` (15 functions, 1 classes)
📄 `pyqual.llm` (7 functions, 2 classes)
📄 `pyqual.pipeline` (7 functions, 4 classes)
📄 `pyqual.plugins` (24 functions, 11 classes)
📄 `pyqual.tickets` (6 functions)

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0- litellm >=1.0- python-dotenv >=1.0- mcp >=1.0- prefact- planfile

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

- 📖 [Full Documentation](https://github.com/semcod/pyqual/tree/main/docs) — API reference, module docs, architecture
- 🚀 [Getting Started](https://github.com/semcod/pyqual/blob/main/docs/getting-started.md) — Quick start guide
- 📚 [API Reference](https://github.com/semcod/pyqual/blob/main/docs/api.md) — Complete API documentation
- 🔧 [Configuration](https://github.com/semcod/pyqual/blob/main/docs/configuration.md) — Configuration options
- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `docs/api.md` | Consolidated API reference | [View](./docs/api.md) |
| `docs/modules.md` | Module reference with metrics | [View](./docs/modules.md) |
| `docs/architecture.md` | Architecture with diagrams | [View](./docs/architecture.md) |
| `docs/dependency-graph.md` | Dependency graphs | [View](./docs/dependency-graph.md) |
| `docs/coverage.md` | Docstring coverage report | [View](./docs/coverage.md) |
| `docs/getting-started.md` | Getting started guide | [View](./docs/getting-started.md) |
| `docs/configuration.md` | Configuration reference | [View](./docs/configuration.md) |
| `docs/api-changelog.md` | API change tracking | [View](./docs/api-changelog.md) |
| `CONTRIBUTING.md` | Contribution guidelines | [View](./CONTRIBUTING.md) |
| `examples/` | Usage examples | [Browse](./examples) |
| `mkdocs.yml` | MkDocs configuration | — |

<!-- code2docs:end -->