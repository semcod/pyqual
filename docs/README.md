<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-298-green)
> **298** functions | **60** classes | **52** files | CC̄ = 6.0

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
├── project        ├── config        ├── config        ├── main        ├── config            ├── StagesChart            ├── MetricsTrendChart            ├── Settings        ├── App            ├── Overview        ├── types/            ├── RepositoryDetail            ├── MetricsChart        ├── api/├── run_analysis        ├── dynamic_thresholds        ├── composite_gates        ├── metric_history        ├── minimal        ├── check_gates        ├── run_pipeline        ├── demo        ├── run_pipeline        ├── main        ├── sync_tickets        ├── performance_collector        ├── code_health_collector    ├── llm    ├── plugins    ├── config    ├── tools    ├── gates├── pyqual/    ├── tickets    ├── parallel    ├── cli    ├── builtin_collectors    ├── run_parallel_fix    ├── cli_plugin_helpers    ├── _gate_collectors    ├── validation    ├── cli_run_helpers    ├── profiles    ├── cli_log_helpers    ├── bulk_init    ├── constants        ├── llx_mcp_service    ├── integrations/        ├── llx_mcp    ├── bulk_run    ├── report    ├── pipeline```

## API Overview

### Classes

- **`StagesChartProps`** — —
- **`MetricsTrendChartProps`** — —
- **`OverviewProps`** — —
- **`PyqualMetric`** — —
- **`PyqualStage`** — —
- **`PyqualSummary`** — —
- **`Repository`** — —
- **`DashboardConfig`** — —
- **`MetricHistory`** — —
- **`MetricTrend`** — —
- **`RepositoryDetailProps`** — —
- **`MetricsChartProps`** — —
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`ToolPreset`** — Definition of a built-in tool invocation preset.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`FixTool`** — Configuration for a single fix tool.
- **`TaskResult`** — Result of processing a single task.
- **`ParallelRunResult`** — Result of parallel execution.
- **`ParallelExecutor`** — Executes tasks across multiple fix tools in parallel.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`SecurityCollector`** — Security scanning metrics from trufflehog, gitleaks, safety.
- **`LlxMcpFixCollector`** — Dockerized llx MCP fix/refactor workflow results.
- **`ErrorDomain`** — —
- **`EC`** — Namespace for standardised error-code string constants.
- **`StageFailure`** — Runtime failure description from a completed stage.
- **`Severity`** — —
- **`ValidationIssue`** — Single validation finding.
- **`ValidationResult`** — Aggregated result of validating one pyqual.yaml.
- **`PipelineProfile`** — A reusable pipeline template with default stages and metrics.
- **`ProjectFingerprint`** — Lightweight summary of a project directory sent to LLM for classification.
- **`ProjectConfig`** — Parsed LLM response — project-specific config decisions.
- **`BulkInitResult`** — Summary of a bulk-init run.
- **`RunStatus`** — —
- **`ProjectRunState`** — Mutable state for a single project's pyqual run.
- **`BulkRunResult`** — Summary of a bulk-run session.
- **`OnStageStart`** — —
- **`OnIterationStart`** — —
- **`OnStageError`** — —
- **`OnStageDone`** — Called after each stage completes. Receives the full StageResult.
- **`OnStageOutput`** — Called with each line of streaming output from a stage.
- **`OnIterationDone`** — Called after each iteration completes. Receives the full IterationResult.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.

### Functions

- `StagesChart()` — —
- `data()` — —
- `MetricsTrendChart()` — —
- `data()` — —
- `Settings()` — —
- `App()` — —
- `loadRepositories()` — —
- `repos()` — —
- `handleRepositorySelect()` — —
- `runs()` — —
- `RepositoryCard()` — —
- `lastRun()` — —
- `statusColor()` — —
- `statusIcon()` — —
- `Overview()` — —
- `totalRepos()` — —
- `passingRepos()` — —
- `failingRepos()` — —
- `avgCoverage()` — —
- `RepositoryDetail()` — —
- `navigate()` — —
- `repo()` — —
- `latestRun()` — —
- `gate()` — —
- `passed()` — —
- `MetricsChart()` — —
- `data()` — —
- `days()` — —
- `today()` — —
- `date()` — —
- `baseCoverage()` — —
- `variation()` — —
- `API_BASE_URL()` — —
- `GITHUB_TOKEN()` — —
- `loadConfig()` — —
- `response()` — —
- `fetchRepositories()` — —
- `config()` — —
- `repositories()` — —
- `lastRun()` — —
- `fetchLatestRun()` — —
- `releases()` — —
- `latestRelease()` — —
- `summaryAsset()` — —
- `summaryResponse()` — —
- `fetchRepositoryRuns()` — —
- `fetchMetricsHistory()` — —
- `getRepoPath()` — —
- `match()` — —
- `fetchRepositoriesWithFallback()` — —
- `repos()` — —
- `run_project(project_path)` — —
- `main()` — —
- `main()` — Run the dynamic-threshold gate example.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `main()` — Run the metric history self-test with synthetic history.
- `check_tool()` — —
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `get_db_path(project_id)` — Get the path to a project's pipeline database.
- `read_summary_json(project_id)` — Read the summary.json file for a project.
- `query_pipeline_db(db_path, query, params)` — Execute a query on the pipeline database.
- `get_projects()` — List all configured projects.
- `get_latest_run(project_id)` — Get the latest run for a project.
- `get_project_runs(project_id, limit)` — Get recent runs for a project.
- `get_metric_history(project_id, metric, days)` — Get historical values for a specific metric.
- `get_stage_performance(project_id, days)` — Get stage performance over time.
- `get_gate_status(project_id, days)` — Get recent gate check results.
- `get_project_summary(project_id)` — Get a comprehensive summary of project metrics.
- `ingest_results(project_id, data, credentials)` — Ingest results from CI/CD pipeline.
- `health_check()` — Health check endpoint.
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate YAML configuration snippet for a named plugin.
- `get_preset(name)` — Look up a tool preset by name (case-insensitive).
- `list_presets()` — Return sorted list of available preset names.
- `is_builtin(name)` — Return True if *name* is a built-in (not externally registered) preset.
- `register_preset(name, preset)` — Register a custom tool preset at runtime.
- `load_user_tools(workdir)` — Load user tool overrides from ``pyqual.tools.json`` in *workdir*.
- `preset_to_dict(preset)` — Serialize a ToolPreset to a JSON-compatible dict.
- `dump_presets_json(names)` — Serialize current presets (or a subset) to JSON string.
- `register_custom_tools_from_yaml(custom_tools)` — Register tool presets from the ``custom_tools:`` YAML section.
- `load_entry_point_presets()` — Discover and load tool presets from ``pyqual.tools`` entry point group.
- `resolve_stage_command(tool_name, workdir)` — Resolve a tool name to (shell_command, allow_failure).
- `sync_planfile_tickets(source, workdir, dry_run, direction)` — Sync tickets via planfile backends.
- `sync_todo_tickets(workdir, dry_run, direction)` — Sync TODO.md tickets through planfile's markdown backend.
- `sync_github_tickets(workdir, dry_run, direction)` — Sync GitHub issues through planfile's GitHub backend.
- `sync_all_tickets(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets through planfile.
- `parse_todo_items(todo_path)` — Parse unchecked items from TODO.md.
- `group_similar_issues(issues, max_group_size)` — Group similar issues together for batch processing.
- `run_parallel_fix(workdir, tools, todo_path, issues)` — Convenience function to run parallel fix with multiple tools.
- `init(path, profile)` — Create pyqual.yaml with sensible defaults.
- `profiles()` — List available pipeline profiles for pyqual.yaml.
- `bulk_init_cmd(path, dry_run, no_llm, model)` — Bulk-generate pyqual.yaml for every project in a directory.
- `bulk_run_cmd(path, parallel, dry_run, timeout)` — Run pyqual across all projects with a real-time dashboard.
- `run(config, dry_run, workdir, verbose)` — Execute pipeline loop until quality gates pass.
- `gates(config, workdir)` — Check quality gates without running stages.
- `validate(config, workdir, strict)` — Validate pyqual.yaml without running the pipeline.
- `fix_config(config, workdir, dry_run, model)` — Use LLM to auto-repair pyqual.yaml based on project structure.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `report(config, workdir, readme)` — Generate metrics report (YAML) and update README.md badges.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_refactor(workdir, project_path, issues, output)` — Run the llx-backed MCP refactor workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `plugin(action, name, workdir, tag)` — Manage pyqual plugins - add, remove, search metric collectors.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `tools()` — List built-in tool presets for pipeline stages.
- `logs(workdir, tail, level, stage)` — View structured pipeline logs from .pyqual/pipeline.db (nfo SQLite).
- `watch(workdir, interval, show_output, show_prompts)` — Live-tail pipeline logs while 'pyqual run' executes in another terminal.
- `history(workdir, tail, prompts, json_output)` — View history of LLX/LLM fix runs from .pyqual/llx_history.jsonl.
- `count_todo_items(todo_path)` — Count unchecked items in TODO.md.
- `mark_completed_todos(todo_path, changed_files)` — Mark TODO items as completed if their file was modified.
- `run_tool(name, command, workdir, timeout)` — Run a single fix tool and return results.
- `main()` — Run parallel fix on TODO.md items using multiple tools.
- `plugin_list(plugins, tag)` — List available plugins, optionally filtered by tag.
- `plugin_search(plugins, query)` — Search plugins by name, description, or tags.
- `plugin_info(name, workdir)` — Show detailed info and configuration example for a plugin.
- `plugin_add(name, workdir)` — Add a plugin's configuration snippet to pyqual.yaml.
- `plugin_remove(name, workdir)` — Remove a plugin's configuration block from pyqual.yaml.
- `plugin_validate(plugins, workdir)` — Validate that configured plugins in pyqual.yaml are available.
- `plugin_unknown_action(action)` — Print an error for an unrecognized plugin sub-command.
- `error_domain(code)` — Return the domain of a standardised error code string.
- `validate_config(config_path)` — Validate a pyqual.yaml file and return structured issues.
- `detect_project_facts(workdir)` — Scan project directory and return facts for LLM-based config repair.
- `extract_pytest_stage_summary(name, text)` — —
- `extract_lint_stage_summary(text)` — —
- `extract_prefact_stage_summary(name, text)` — —
- `extract_code2llm_stage_summary(name, text)` — —
- `extract_validation_stage_summary(name, text)` — —
- `extract_fix_stage_summary(name, text)` — —
- `extract_mypy_stage_summary(name, text)` — —
- `extract_bandit_stage_summary(text)` — —
- `extract_stage_summary(name, stdout, stderr)` — Extract key metrics from stage output as YAML-ready key: value pairs.
- `enrich_from_artifacts(workdir, stages)` — Enrich stage dicts with metrics read from artifact files on disk.
- `infer_fix_result(stage)` — —
- `build_run_summary(report)` — —
- `format_run_summary(summary)` — —
- `get_last_error_line(text)` — Return the last meaningful error line, filtering out informational noise.
- `get_profile(name)` — Return a profile by name, or None if not found.
- `list_profiles()` — Return sorted list of available profile names.
- `query_nfo_db(db_path, event, failed, tail)` — Query the nfo SQLite pipeline log and return structured dicts.
- `row_to_event_dict(row)` — Parse an nfo SQLite row into a structured event dict.
- `format_log_entry_row(entry)` — Return (ts, event_name, name, status, details) for one log entry.
- `collect_fingerprint(project_dir)` — Collect a lightweight fingerprint from a project directory.
- `classify_with_llm(fp, model)` — Send fingerprint to LLM, parse structured response.
- `generate_pyqual_yaml(project_name, cfg)` — Generate pyqual.yaml content from a ProjectConfig.
- `bulk_init(root)` — Scan subdirectories of *root* and generate pyqual.yaml for each project.
- `create_app(state, llx_server)` — Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `build_dashboard_table(states)` — Build a Rich Table showing the current status of all projects.
- `discover_projects(root)` — Find all subdirectories with pyqual.yaml and create run states.
- `bulk_run(root)` — Run pyqual across all projects with parallel execution.
- `collect_project_metadata(workdir, config)` — Collect project-level metadata for badges and report.
- `collect_all_metrics(workdir)` — Collect all available metrics from .pyqual/ and project/ artifacts.
- `evaluate_gates(config, workdir)` — Evaluate all configured gates and return structured results.
- `generate_report(config, workdir, output)` — Generate a metrics report and write it to YAML.
- `build_badges(metrics, gates_passed, project_meta, gates_passed_count)` — Build full badge block: project info line + quality metrics line.
- `update_readme_badges(readme_path, metrics, gates_passed, project_meta)` — Insert or replace pyqual badges in README.md.
- `run(workdir, config_path, readme_path)` — Run report generation + badge update. Returns 0 on success.
- `main()` — —


## Project Structure

📄 `dashboard.api.main` (12 functions)
📄 `dashboard.postcss.config`
📄 `dashboard.src.App` (9 functions)
📦 `dashboard.src.api` (23 functions)
📄 `dashboard.src.components.MetricsChart` (7 functions, 1 classes)
📄 `dashboard.src.components.MetricsTrendChart` (2 functions, 1 classes)
📄 `dashboard.src.components.Overview` (5 functions, 1 classes)
📄 `dashboard.src.components.RepositoryDetail` (6 functions, 1 classes)
📄 `dashboard.src.components.Settings` (1 functions)
📄 `dashboard.src.components.StagesChart` (2 functions, 1 classes)
📄 `dashboard.src.main`
📦 `dashboard.src.types` (7 classes)
📄 `dashboard.tailwind.config`
📄 `dashboard.vite.config`
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
📄 `pyqual._gate_collectors` (22 functions)
📄 `pyqual.builtin_collectors` (15 functions, 8 classes)
📄 `pyqual.bulk_init` (15 functions, 3 classes)
📄 `pyqual.bulk_run` (7 functions, 3 classes)
📄 `pyqual.cli` (24 functions)
📄 `pyqual.cli_log_helpers` (3 functions)
📄 `pyqual.cli_plugin_helpers` (7 functions)
📄 `pyqual.cli_run_helpers` (14 functions)
📄 `pyqual.config` (7 functions, 4 classes)
📄 `pyqual.constants`
📄 `pyqual.gates` (6 functions, 3 classes)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (2 functions)
📄 `pyqual.integrations.llx_mcp_service` (4 functions)
📄 `pyqual.llm`
📄 `pyqual.parallel` (7 functions, 4 classes)
📄 `pyqual.pipeline` (24 functions, 10 classes)
📄 `pyqual.plugins` (9 functions, 3 classes)
📄 `pyqual.profiles` (2 functions, 1 classes)
📄 `pyqual.report` (16 functions)
📄 `pyqual.run_parallel_fix` (4 functions)
📄 `pyqual.tickets` (6 functions)
📄 `pyqual.tools` (15 functions, 1 classes)
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