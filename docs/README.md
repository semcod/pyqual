<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-161-green)
> **161** functions | **37** classes | **30** files | CC̄ = 6.4

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
pip install pyqual[llx]    # llx features
pip install pyqual[mcp]    # mcp features
pip install pyqual[all]    # all optional features
```

## Quick Start

### CLI Usage

```bash
# Generate full documentation for your project
pyqual ./my-project

# Only regenerate README
pyqual ./my-project --readme-only

# Preview what would be generated (no file writes)
pyqual ./my-project --dry-run

# Check documentation health
pyqual check ./my-project

# Sync — regenerate only changed modules
pyqual sync ./my-project
```

### Python API

```python
from pyqual import generate_readme, generate_docs, Code2DocsConfig

# Quick: generate README
generate_readme("./my-project")

# Full: generate all documentation
config = Code2DocsConfig(project_name="mylib", verbose=True)
docs = generate_docs("./my-project", config=config)
```

## Generated Output

When you run `pyqual`, the following files are produced:

```
<project>/
├── README.md                 # Main project README (auto-generated sections)
├── docs/
│   ├── api.md               # Consolidated API reference
│   ├── modules.md           # Module documentation with metrics
│   ├── architecture.md      # Architecture overview with diagrams
│   ├── dependency-graph.md  # Module dependency graphs
│   ├── coverage.md          # Docstring coverage report
│   ├── getting-started.md   # Getting started guide
│   ├── configuration.md    # Configuration reference
│   └── api-changelog.md    # API change tracking
├── examples/
│   ├── quickstart.py       # Basic usage examples
│   └── advanced_usage.py   # Advanced usage examples
├── CONTRIBUTING.md         # Contribution guidelines
└── mkdocs.yml             # MkDocs site configuration
```

## Configuration

Create `pyqual.yaml` in your project root (or run `pyqual init`):

```yaml
project:
  name: my-project
  source: ./
  output: ./docs/

readme:
  sections:
    - overview
    - install
    - quickstart
    - api
    - structure
  badges:
    - version
    - python
    - coverage
  sync_markers: true

docs:
  api_reference: true
  module_docs: true
  architecture: true
  changelog: true

examples:
  auto_generate: true
  from_entry_points: true

sync:
  strategy: markers    # markers | full | git-diff
  watch: false
  ignore:
    - "tests/"
    - "__pycache__"
```

## Sync Markers

pyqual can update only specific sections of an existing README using HTML comment markers:

```markdown
<!-- pyqual:start -->
# Project Title
... auto-generated content ...
<!-- pyqual:end -->
```

Content outside the markers is preserved when regenerating. Enable this with `sync_markers: true` in your configuration.

## Architecture

```
pyqual/
    ├── config├── run_analysis    ├── plugins    ├── llm    ├── gates├── pyqual/    ├── tickets    ├── tools    ├── builtin_collectors    ├── cli    ├── _gate_collectors    ├── pipeline        ├── llx_mcp_service    ├── integrations/        ├── llx_mcp    ├── validation        ├── metric_history        ├── dynamic_thresholds        ├── composite_gates    ├── bulk_init        ├── performance_collector        ├── minimal        ├── check_gates        ├── run_pipeline        ├── sync_tickets├── project        ├── demo        ├── run_pipeline        ├── code_health_collector    ├── bulk_run```

## API Overview

### Classes

- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`ToolPreset`** — Definition of a built-in tool invocation preset.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`SecurityCollector`** — Security scanning metrics from trufflehog, gitleaks, safety.
- **`LlxMcpFixCollector`** — Dockerized llx MCP fix/refactor workflow results.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.
- **`ErrorDomain`** — —
- **`EC`** — Namespace for standardised error-code string constants.
- **`StageFailure`** — Runtime failure description from a completed stage.
- **`Severity`** — —
- **`ValidationIssue`** — Single validation finding.
- **`ValidationResult`** — Aggregated result of validating one pyqual.yaml.
- **`ProjectFingerprint`** — Lightweight summary of a project directory sent to LLM for classification.
- **`ProjectConfig`** — Parsed LLM response — project-specific config decisions.
- **`BulkInitResult`** — Summary of a bulk-init run.
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
- **`RunStatus`** — —
- **`ProjectRunState`** — Mutable state for a single project's pyqual run.
- **`BulkRunResult`** — Summary of a bulk-run session.

### Functions

- `run_project(project_path)` — —
- `main()` — —
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate YAML configuration snippet for a named plugin.
- `sync_planfile_tickets(source, workdir, dry_run, direction)` — Sync tickets via planfile backends.
- `sync_todo_tickets(workdir, dry_run, direction)` — Sync TODO.md tickets through planfile's markdown backend.
- `sync_github_tickets(workdir, dry_run, direction)` — Sync GitHub issues through planfile's GitHub backend.
- `sync_all_tickets(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets through planfile.
- `get_preset(name)` — Look up a tool preset by name (case-insensitive).
- `list_presets()` — Return sorted list of available preset names.
- `is_builtin(name)` — Return True if *name* is a built-in (not externally registered) preset.
- `register_preset(name, preset)` — Register a custom tool preset at runtime.
- `register_custom_tools_from_yaml(custom_tools)` — Register tool presets from the ``custom_tools:`` YAML section.
- `load_entry_point_presets()` — Discover and load tool presets from ``pyqual.tools`` entry point group.
- `resolve_stage_command(tool_name, workdir)` — Resolve a tool name to (shell_command, allow_failure).
- `init(path)` — Create pyqual.yaml with sensible defaults.
- `bulk_init_cmd(path, dry_run, no_llm, model)` — Bulk-generate pyqual.yaml for every project in a directory.
- `bulk_run_cmd(path, parallel, dry_run, timeout)` — Run pyqual across all projects with a real-time dashboard.
- `run(config, dry_run, workdir, verbose)` — Execute pipeline loop until quality gates pass.
- `gates(config, workdir)` — Check quality gates without running stages.
- `validate(config, workdir, strict)` — Validate pyqual.yaml without running the pipeline.
- `fix_config(config, workdir, dry_run, model)` — Use LLM to auto-repair pyqual.yaml based on project structure.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_refactor(workdir, project_path, issues, output)` — Run the llx-backed MCP refactor workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `plugin(action, name, workdir, tag)` — Manage pyqual plugins - add, remove, search metric collectors.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `tools()` — List built-in tool presets for pipeline stages.
- `logs(workdir, tail, level, failed)` — View structured pipeline logs from .pyqual/pipeline.db (nfo SQLite).
- `create_app(state, llx_server)` — Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `error_domain(code)` — Return the domain of a standardised error code string.
- `validate_config(config_path)` — Validate a pyqual.yaml file and return structured issues.
- `detect_project_facts(workdir)` — Scan project directory and return facts for LLM-based config repair.
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `main()` — Run the metric history self-test with synthetic history.
- `main()` — Run the dynamic-threshold gate example.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `collect_fingerprint(project_dir)` — Collect a lightweight fingerprint from a project directory.
- `classify_with_llm(fp, model)` — Send fingerprint to LLM, parse structured response.
- `generate_pyqual_yaml(project_name, cfg)` — Generate pyqual.yaml content from a ProjectConfig.
- `bulk_init(root)` — Scan subdirectories of *root* and generate pyqual.yaml for each project.
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
- `check_tool()` — —
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `build_dashboard_table(states)` — Build a Rich Table showing the current status of all projects.
- `discover_projects(root)` — Find all subdirectories with pyqual.yaml and create run states.
- `bulk_run(root)` — Run pyqual across all projects with parallel execution.


## Project Structure

📄 `examples.basic.check_gates`
📄 `examples.basic.minimal`
📄 `examples.basic.run_pipeline`
📄 `examples.custom_gates.composite_gates` (2 functions)
📄 `examples.custom_gates.dynamic_thresholds` (1 functions)
📄 `examples.custom_gates.metric_history` (5 functions)
📄 `examples.custom_plugins.code_health_collector` (2 functions, 1 classes)
📄 `examples.custom_plugins.performance_collector` (2 functions, 1 classes)
📄 `examples.llx.demo` (1 functions)
📄 `examples.multi_gate_pipeline.run_pipeline` (2 functions)
📄 `examples.ticket_workflow.sync_tickets` (3 functions)
📄 `project`
📦 `pyqual`
📄 `pyqual._gate_collectors` (21 functions)
📄 `pyqual.builtin_collectors` (15 functions, 8 classes)
📄 `pyqual.bulk_init` (7 functions, 3 classes)
📄 `pyqual.bulk_run` (7 functions, 3 classes)
📄 `pyqual.cli` (30 functions)
📄 `pyqual.config` (6 functions, 4 classes)
📄 `pyqual.gates` (6 functions, 3 classes)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (2 functions)
📄 `pyqual.integrations.llx_mcp_service` (4 functions)
📄 `pyqual.llm`
📄 `pyqual.pipeline` (13 functions, 4 classes)
📄 `pyqual.plugins` (9 functions, 3 classes)
📄 `pyqual.tickets` (6 functions)
📄 `pyqual.tools` (9 functions, 1 classes)
📄 `pyqual.validation` (6 functions, 6 classes)
📄 `run_analysis` (2 functions)

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0- litellm >=1.0- python-dotenv >=1.0- mcp >=1.0- nfo >=0.2.13- prefact- planfile

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