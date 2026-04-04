<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-442-green)
> **442** functions | **74** classes | **79** files | CC̄ = 5.4

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
├── SUGGESTED_COMMANDS├── project        ├── config        ├── config        ├── config        ├── main            ├── MetricsTrendChart            ├── StagesChart        ├── App            ├── Settings            ├── Overview            ├── RepositoryDetail        ├── types/            ├── MetricsChart        ├── api/    ├── constants        ├── metric_history├── run_analysis        ├── dynamic_thresholds    ├── integration_example        ├── composite_gates        ├── composite_simple        ├── sync_if_fail        ├── minimal        ├── check_gates        ├── run_pipeline        ├── demo        ├── main        ├── run_pipeline        ├── sync_tickets    ├── custom_fix        ├── performance_collector        ├── code_health_collector    ├── llm    ├── config    ├── tools    ├── github_tasks    ├── auto_closer    ├── report_generator    ├── gates    ├── parallel├── pyqual/    ├── cli    ├── _plugin_base    ├── __main__    ├── tickets    ├── documentation    ├── cli_bulk_cmds    ├── api    ├── github_actions    ├── run_parallel_fix    ├── builtin_collectors    ├── _gate_collectors    ├── cli_plugin_helpers    ├── validation    ├── cli_observe    ├── bulk_run    ├── profiles    ├── cli_log_helpers    ├── bulk_init    ├── constants        ├── base    ├── cli_run_helpers    ├── fix_tools/        ├── aider        ├── claude        ├── llx        ├── git/    ├── plugins/        ├── example_plugin/            ├── main        ├── llx_mcp_service    ├── integrations/    ├── report    ├── run_docker_matrix    ├── run_matrix        ├── llx_mcp            ├── main    ├── pipeline```

## API Overview

### Classes

- **`MetricsTrendChartProps`** — —
- **`StagesChartProps`** — —
- **`OverviewProps`** — —
- **`RepositoryDetailProps`** — —
- **`PyqualMetric`** — —
- **`PyqualStage`** — —
- **`PyqualSummary`** — —
- **`Repository`** — —
- **`DashboardConfig`** — —
- **`MetricHistory`** — —
- **`MetricTrend`** — —
- **`MetricsChartProps`** — —
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`ToolPreset`** — Definition of a built-in tool invocation preset.
- **`StageResult`** — —
- **`PipelineRun`** — —
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`CompositeGateSet`** — Weighted composite quality scoring from multiple gates.
- **`FixTool`** — Configuration for a single fix tool.
- **`TaskResult`** — Result of processing a single task.
- **`ParallelRunResult`** — Result of parallel execution.
- **`ParallelExecutor`** — Executes tasks across multiple fix tools in parallel.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`DocumentationCollector`** — Documentation completeness and quality metrics.
- **`ShellHelper`** — Shell helper utilities for external tool integration.
- **`GitHubTask`** — Represents a task from GitHub (issue or PR).
- **`GitHubActionsReporter`** — Reports pyqual results to GitHub Actions and PRs.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`SecurityCollector`** — Security metrics collector - pip-audit CVEs and ruff lint errors.
- **`LlxMcpFixCollector`** — Dockerized llx MCP fix/refactor workflow results.
- **`ErrorDomain`** — —
- **`EC`** — Namespace for standardised error-code string constants.
- **`StageFailure`** — Runtime failure description from a completed stage.
- **`Severity`** — —
- **`ValidationIssue`** — Single validation finding.
- **`ValidationResult`** — Aggregated result of validating one pyqual.yaml.
- **`RunStatus`** — —
- **`ProjectRunState`** — Mutable state for a single project's pyqual run.
- **`BulkRunResult`** — Summary of a bulk-run session.
- **`PipelineProfile`** — A reusable pipeline template with default stages and metrics.
- **`ProjectFingerprint`** — Lightweight summary of a project directory sent to LLM for classification.
- **`ProjectConfig`** — Parsed LLM response — project-specific config decisions.
- **`BulkInitResult`** — Summary of a bulk-init run.
- **`ToolResult`** — Result from running a fix tool.
- **`FixTool`** — Abstract base class for fix tools.
- **`AiderTool`** — Aider tool via Docker (paulgauthier/aider).
- **`ClaudeTool`** — Claude Code CLI tool.
- **`LlxTool`** — LLX fix tool.
- **`ExampleCollector`** — Example collector showing plugin structure.
- **`GitCollector`** — Git repository operations collector — status, commit, push with protection handling.
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

- `MetricsTrendChart()` — —
- `data()` — —
- `StagesChart()` — —
- `data()` — —
- `App()` — —
- `loadRepositories()` — —
- `repos()` — —
- `handleRepositorySelect()` — —
- `runs()` — —
- `RepositoryCard()` — —
- `lastRun()` — —
- `statusColor()` — —
- `statusIcon()` — —
- `Settings()` — —
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
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `main()` — Run the metric history self-test with synthetic history.
- `run_project(project_path)` — —
- `main()` — —
- `main()` — Run the dynamic-threshold gate example.
- `run_quality_check(config_path, workdir)` — Run pyqual quality pipeline and return True if all gates pass.
- `run_with_callbacks(workdir)` — Run pipeline with progress callbacks.
- `check_prerequisites()` — Check if required tools are available.
- `run_shell_command_example()` — Run a shell command through pyqual's shell helper.
- `run_single_stage(stage_name, tool, workdir)` — Run a single stage without full pipeline.
- `preview_pipeline(config_path)` — Preview pipeline execution without running anything.
- `quick_gate_check(workdir)` — Check if current code passes quality gates.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `main()` — Run the composite gate self-test with synthetic data.
- `check_tool()` — —
- `get_db_path(project_id)` — Get the path to a project's pipeline database.
- `read_summary_json(project_id)` — Read the summary.json file for a project.
- `query_pipeline_db(db_path, query, params)` — Execute a query on the pipeline database.
- `safe_parse(data)` — Parse kwargs from SQLite, handling both JSON and Python repr formats.
- `get_projects()` — List all configured projects.
- `get_latest_run(project_id)` — Get the latest run for a project.
- `get_project_runs(project_id, limit)` — Get recent runs for a project.
- `get_metric_history(project_id, metric, days)` — Get historical values for a specific metric.
- `get_stage_performance(project_id, days)` — Get stage performance over time.
- `get_gate_status(project_id, days)` — Get recent gate check results.
- `get_project_summary(project_id)` — Get a comprehensive summary of project metrics.
- `ingest_results(project_id, data, credentials)` — Ingest results from CI/CD pipeline.
- `health_check()` — Health check endpoint.
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
- `apply_patch(file_path, old_text, new_text)` — Apply a simple text replacement patch.
- `add_docstring(file_path, docstring)` — Add module docstring at the top of a file.
- `parse_and_apply_suggestions(suggestions)` — Parse LLM suggestions and apply patches.
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
- `fetch_github_tasks(label, state, include_issues, include_prs)` — Fetch tasks from GitHub issues and PRs.
- `save_tasks_to_todo(tasks, todo_path, append)` — Save tasks to TODO.md file.
- `save_tasks_to_json(tasks, json_path)` — Save tasks to JSON file.
- `get_changed_files()` — Get files changed in the last commit or current working tree.
- `get_diff_content()` — Get the unified diff of recent changes.
- `evaluate_with_llm(title, description, diff)` — Use LLM to evaluate the implementation quality.
- `main()` — —
- `parse_kwargs(kwargs_str)` — Parse kwargs string that might have single quotes.
- `get_last_run(db_path)` — Get the last pipeline run from database.
- `generate_mermaid_diagram(run)` — Generate Mermaid flowchart of pipeline execution.
- `generate_ascii_diagram(run)` — Generate ASCII art diagram of pipeline execution.
- `generate_metrics_table(run)` — Generate metrics table.
- `generate_stage_details(run)` — Generate detailed stage results.
- `generate_report(workdir)` — Generate full markdown report.
- `main()` — Generate and print report.
- `parse_todo_items(todo_path)` — Parse unchecked items from TODO.md.
- `group_similar_issues(issues, max_group_size)` — Group similar issues together for batch processing.
- `run_parallel_fix(workdir, tools, todo_path, issues)` — Convenience function to run parallel fix with multiple tools.
- `init(path, profile)` — Create pyqual.yaml with sensible defaults.
- `profiles()` — List available pipeline profiles for pyqual.yaml.
- `run(config, dry_run, workdir, verbose)` — Execute pipeline loop until quality gates pass.
- `gates(config, workdir)` — Check quality gates without running stages.
- `validate(config, workdir, strict)` — Validate pyqual.yaml without running the pipeline.
- `fix_config(config, workdir, dry_run, model)` — Use LLM to auto-repair pyqual.yaml based on project structure.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `report(config, workdir, readme)` — Generate metrics report (YAML) and update README.md badges.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_refactor(workdir, project_path, issues, output)` — Run the llx-backed MCP refactor workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `tickets_sync(workdir, from_gates, backends, dry_run)` — Sync tickets from gate failures or explicitly.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `tickets_fetch(label, state, output, todo_output)` — Fetch GitHub issues/PRs as tasks.
- `tickets_comment(issue_number, message, is_pr)` — Post a comment on a GitHub issue or PR.
- `plugin(action, name, workdir, tag)` — Manage pyqual plugins - add, remove, search metric collectors.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `tools()` — List built-in tool presets for pipeline stages.
- `git_status_cmd(workdir, json_output)` — Show git repository status.
- `git_add_cmd(paths, workdir)` — Stage files for commit.
- `git_scan_cmd(paths, workdir, use_trufflehog, use_gitleaks)` — Scan files for secrets before push.
- `git_commit_cmd(message, workdir, add_all, if_changed)` — Create a git commit.
- `git_push_cmd(workdir, remote, branch, force)` — Push commits to remote with push protection detection.
- `sync_planfile_tickets(source, workdir, dry_run, direction)` — Sync tickets via planfile backends.
- `sync_todo_tickets(workdir, dry_run, direction)` — Sync TODO.md tickets through planfile's markdown backend.
- `sync_github_tickets(workdir, dry_run, direction)` — Sync GitHub issues through planfile's GitHub backend.
- `sync_all_tickets(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets through planfile.
- `sync_from_gates(workdir, dry_run, backends)` — Check gates and sync tickets only if gates fail.
- `register_bulk_commands(app)` — Register bulk-init and bulk-run commands onto *app*.
- `load_config(path, workdir)` — Load pyqual configuration from YAML file.
- `validate_config(config)` — Validate configuration and return list of errors (empty if valid).
- `create_default_config(path, profile, workdir)` — Create a default pyqual.yaml config file.
- `run(config, workdir, dry_run, on_stage_start)` — Run a quality pipeline with the given configuration.
- `run_pipeline(config_path, workdir, dry_run)` — Run pipeline from config file path (convenience function).
- `check_gates(config, workdir)` — Check quality gates without running pipeline.
- `dry_run(config_path, workdir)` — Simulate pipeline execution without running commands.
- `run_stage(stage_name, command, tool, workdir)` — Run a single stage/command directly.
- `get_tool_command(tool_name, workdir)` — Get the shell command for a built-in tool preset.
- `format_result_summary(result)` — Format pipeline result as human-readable summary.
- `export_results_json(result, output_path)` — Export pipeline results to JSON file.
- `shell_check(command)` — Check if a shell command succeeds.
- `get_todo_batch(todo_path, max_items)` — Get up to max_items unchecked TODO items and total pending count.
- `mark_completed_todos(todo_path, changed_files)` — Mark TODO items as completed if their file was modified.
- `run_tool(name, command, workdir, timeout)` — Run a single fix tool and return results.
- `git_commit_and_push(workdir, completed_count)` — Commit changes and push to origin. Returns True if pushed.
- `parse_args()` — Parse command line arguments.
- `main()` — Run parallel fix on TODO.md items - configurable batch size with git push.
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
- `register_observe_commands(app)` — Register logs, watch, and history commands onto *app*.
- `build_dashboard_table(states)` — Build a Rich Table showing the current status of all projects.
- `discover_projects(root)` — Find all subdirectories with pyqual.yaml and create run states.
- `bulk_run(root)` — Run pyqual across all projects with parallel execution.
- `get_profile(name)` — Return a profile by name, or None if not found.
- `list_profiles()` — Return sorted list of available profile names.
- `query_nfo_db(db_path, event, failed, tail)` — Query the nfo SQLite pipeline log and return structured dicts.
- `row_to_event_dict(row)` — Parse an nfo SQLite row into a structured event dict.
- `format_log_entry_row(entry)` — Return (ts, event_name, name, status, details) for one log entry.
- `collect_fingerprint(project_dir)` — Collect a lightweight fingerprint from a project directory.
- `classify_with_llm(fp, model)` — Send fingerprint to LLM, parse structured response.
- `generate_pyqual_yaml(project_name, cfg)` — Generate pyqual.yaml content from a ProjectConfig.
- `bulk_init(root)` — Scan subdirectories of *root* and generate pyqual.yaml for each project.
- `count_todo_items(todo_path)` — Count pending TODO items in TODO.md.
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
- `get_available_tools(batch_file, batch_count, llm_model, skip_claude)` — Get list of available tools configured for current batch.
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate YAML configuration snippet for a named plugin.
- `example_helper_function()` — Helper function demonstrating utility functions in plugins.
- `create_app(state, llx_server)` — Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.
- `collect_project_metadata(workdir, config)` — Collect project-level metadata for badges and report.
- `collect_all_metrics(workdir)` — Collect all available metrics from .pyqual/ and project/ artifacts.
- `evaluate_gates(config, workdir)` — Evaluate all configured gates and return structured results.
- `generate_report(config, workdir, output)` — Generate a metrics report and write it to YAML.
- `build_badges(metrics, gates_passed, project_meta, gates_passed_count)` — Build full badge block: project info line + quality metrics line.
- `update_readme_badges(readme_path, metrics, gates_passed, project_meta)` — Insert or replace pyqual badges in README.md.
- `run(workdir, config_path, readme_path)` — Run report generation + badge update. Returns 0 on success.
- `main()` — —
- `run_case()` — —
- `hello()` — —
- `add()` — —
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `run_git_command(args, cwd, check, capture_output)` — Run a git command with proper error handling.
- `git_status(cwd)` — Get git repository status.
- `git_commit(message, cwd, add_all, only_if_changed)` — Create a git commit.
- `git_push(cwd, remote, branch, force)` — Push commits to remote.
- `git_add(paths, cwd)` — Stage files for commit.
- `scan_for_secrets(paths, cwd, use_trufflehog, use_gitleaks)` — Scan for secrets in files before push.
- `preflight_push_check(cwd, remote, branch, scan_secrets)` — Pre-flight check before push - scan for secrets and validate.


## Project Structure

📄 `SUGGESTED_COMMANDS`
📄 `dashboard.api.main` (13 functions)
📄 `dashboard.constants`
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
📄 `examples.basic.sync_if_fail`
📄 `examples.custom_gates.composite_gates` (3 functions)
📄 `examples.custom_gates.composite_simple`
📄 `examples.custom_gates.dynamic_thresholds` (1 functions)
📄 `examples.custom_gates.metric_history` (5 functions)
📄 `examples.custom_plugins.code_health_collector` (2 functions, 1 classes)
📄 `examples.custom_plugins.performance_collector` (2 functions, 1 classes)
📄 `examples.integration_example` (7 functions)
📄 `examples.llx.demo` (1 functions)
📄 `examples.multi_gate_pipeline.run_pipeline` (2 functions)
📄 `examples.ticket_workflow.sync_tickets` (3 functions)
📄 `integration.run_docker_matrix`
📄 `integration.run_matrix` (8 functions)
📄 `project`
📦 `pyqual`
📄 `pyqual.__main__`
📄 `pyqual._gate_collectors` (22 functions)
📄 `pyqual._plugin_base` (7 functions, 3 classes)
📄 `pyqual.api` (15 functions, 1 classes)
📄 `pyqual.auto_closer` (4 functions)
📄 `pyqual.builtin_collectors` (21 functions, 9 classes)
📄 `pyqual.bulk_init` (15 functions, 3 classes)
📄 `pyqual.bulk_run` (7 functions, 3 classes)
📄 `pyqual.cli` (27 functions)
📄 `pyqual.cli_bulk_cmds` (1 functions)
📄 `pyqual.cli_log_helpers` (3 functions)
📄 `pyqual.cli_observe` (1 functions)
📄 `pyqual.cli_plugin_helpers` (7 functions)
📄 `pyqual.cli_run_helpers` (20 functions)
📄 `pyqual.config` (8 functions, 4 classes)
📄 `pyqual.constants`
📄 `pyqual.custom_fix` (3 functions)
📄 `pyqual.documentation` (11 functions, 1 classes)
📦 `pyqual.fix_tools` (1 functions)
📄 `pyqual.fix_tools.aider` (3 functions, 1 classes)
📄 `pyqual.fix_tools.base` (5 functions, 2 classes)
📄 `pyqual.fix_tools.claude` (3 functions, 1 classes)
📄 `pyqual.fix_tools.llx` (4 functions, 1 classes)
📄 `pyqual.gates` (11 functions, 4 classes)
📄 `pyqual.github_actions` (16 functions, 2 classes)
📄 `pyqual.github_tasks` (3 functions)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (2 functions)
📄 `pyqual.integrations.llx_mcp_service` (4 functions)
📄 `pyqual.llm`
📄 `pyqual.parallel` (7 functions, 4 classes)
📄 `pyqual.pipeline` (26 functions, 10 classes)
📦 `pyqual.plugins` (3 functions)
📦 `pyqual.plugins.example_plugin`
📄 `pyqual.plugins.example_plugin.main` (3 functions, 1 classes)
📦 `pyqual.plugins.git`
📄 `pyqual.plugins.git.main` (20 functions, 1 classes)
📄 `pyqual.profiles` (2 functions, 1 classes)
📄 `pyqual.report` (18 functions)
📄 `pyqual.report_generator` (8 functions, 2 classes)
📄 `pyqual.run_parallel_fix` (6 functions)
📄 `pyqual.tickets` (7 functions)
📄 `pyqual.tools` (15 functions, 1 classes)
📄 `pyqual.validation` (9 functions, 6 classes)
📄 `run_analysis` (2 functions)

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0- litellm >=1.0- python-dotenv >=1.0- nfo >=0.2.13

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Pyqual Bot <pyqual-bot@semcod.github.io>
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