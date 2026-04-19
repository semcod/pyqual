<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-647-green)
> **647** functions | **84** classes | **132** files | CC̄ = 5.1

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
├── SUGGESTED_COMMANDS├── project        ├── config        ├── config        ├── main        ├── config        ├── App            ├── MetricsTrendChart            ├── StagesChart            ├── Settings            ├── RepositoryDetail            ├── Overview        ├── types/            ├── MetricsChart        ├── api/├── run_analysis        ├── metric_history    ├── constants        ├── dynamic_thresholds        ├── composite_gates        ├── composite_simple        ├── main        ├── sync_if_fail        ├── minimal        ├── check_gates        ├── run_pipeline        ├── demo    ├── integration_example        ├── run_pipeline    ├── custom_fix        ├── sync_tickets        ├── code_health_collector    ├── output        ├── performance_collector    ├── command    ├── tools    ├── report_generator    ├── llm    ├── config    ├── analysis    ├── auto_closer    ├── bulk_init_classify    ├── github_tasks    ├── bulk_run├── pyqual/    ├── parallel    ├── stage_names    ├── gates    ├── tickets    ├── __main__    ├── cli_bulk_cmds    ├── pipeline_results    ├── validation/    ├── api    ├── github_actions    ├── run_parallel_fix    ├── release_check    ├── setup_deps    ├── _gate_collectors    ├── bulk_init_fingerprint    ├── bulk_init    ├── yaml_fixer    ├── pipeline    ├── cli_run_helpers    ├── cli_observe    ├── profiles    ├── cli_log_helpers    ├── constants    ├── gate_collectors/        ├── utils    ├── pipeline_protocols        ├── legacy    ├── fix_tools/        ├── aider        ├── base        ├── claude        ├── llx        ├── cmd_init    ├── cli/        ├── cmd_info        ├── cmd_mcp    ├── report        ├── cmd_tune        ├── cmd_git        ├── cmd_tickets        ├── cmd_plugin    ├── plugins/        ├── cli_helpers        ├── cmd_run        ├── main        ├── docs/        ├── builtin        ├── security/            ├── main        ├── code_health/        ├── _base            ├── main            ├── __main__        ├── attack/        ├── cmd_config        ├── docker/            ├── main            ├── main        ├── deps/        ├── lint/            ├── status        ├── git/            ├── git_command            ├── main        ├── coverage/            ├── main        ├── example_plugin/            ├── main            ├── main        ├── documentation/            ├── main        ├── schema        ├── project            ├── main            ├── main        ├── release        ├── runner        ├── parser        ├── llx_mcp_service    ├── integrations/        ├── llx_mcp    ├── run_docker_matrix    ├── run_matrix        ├── errors        ├── config_check        ├── models```

## API Overview

### Classes

- **`MetricsTrendChartProps`** — —
- **`StagesChartProps`** — —
- **`RepositoryDetailProps`** — —
- **`OverviewProps`** — —
- **`PyqualMetric`** — —
- **`PyqualStage`** — —
- **`PyqualSummary`** — —
- **`Repository`** — —
- **`DashboardConfig`** — —
- **`MetricHistory`** — —
- **`MetricTrend`** — —
- **`MetricsChartProps`** — —
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`ToolPreset`** — Definition of a built-in tool invocation preset.
- **`StageResult`** — —
- **`PipelineRun`** — —
- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`ProjectConfig`** — Parsed LLM response — project-specific config decisions.
- **`FixTool`** — Configuration for a single fix tool.
- **`TaskResult`** — Result of processing a single task.
- **`ParallelRunResult`** — Result of parallel execution.
- **`ParallelExecutor`** — Executes tasks across multiple fix tools in parallel.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`CompositeGateSet`** — Weighted composite quality scoring from multiple gates.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`ShellHelper`** — Shell helper utilities for external tool integration.
- **`GitHubTask`** — Represents a task from GitHub (issue or PR).
- **`GitHubActionsReporter`** — Reports pyqual results to GitHub Actions and PRs.
- **`DepResult`** — Result of a single dependency check.
- **`ProjectFingerprint`** — Lightweight summary of a project directory sent to LLM for classification.
- **`BulkInitResult`** — Summary of a bulk-init run.
- **`YamlErrorType`** — Types of YAML syntax errors we can detect and fix.
- **`YamlSyntaxIssue`** — A single YAML syntax issue with location and fix information.
- **`YamlFixResult`** — Result of parsing/fixing YAML.
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.
- **`PipelineProfile`** — A reusable pipeline template with default stages and metrics.
- **`OnStageStart`** — —
- **`OnIterationStart`** — —
- **`OnStageError`** — —
- **`OnStageDone`** — Called after each stage completes. Receives the full StageResult.
- **`OnStageOutput`** — Called with each line of streaming output from a stage.
- **`OnIterationDone`** — Called after each iteration completes. Receives the full IterationResult.
- **`AiderTool`** — Aider tool via Docker (paulgauthier/aider).
- **`ToolResult`** — Result from running a fix tool.
- **`FixTool`** — Abstract base class for fix tools.
- **`ClaudeTool`** — Claude Code CLI tool.
- **`LlxTool`** — LLX fix tool.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`LlxMcpFixCollector`** — Dockerized llx MCP fix/refactor workflow results.
- **`SecurityCollector`** — Security metrics collector — aggregates findings from security scanners.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`CodeHealthCollector`** — Code health metrics collector — maintainability, dead code, packaging quality.
- **`AttackCollector`** — Attack merge collector — automerge with aggressive conflict resolution.
- **`DocsCollector`** — Documentation quality metrics collector.
- **`DockerCollector`** — Docker security and quality metrics collector.
- **`CoverageCollector`** — Coverage metrics collector — extracts test coverage data.
- **`DepsCollector`** — Dependency management metrics collector.
- **`ExampleCollector`** — Example collector showing plugin structure.
- **`GitCollector`** — Git repository operations collector — status, commit, push with protection handling.
- **`ValidationIssue`** — Single validation finding.
- **`ValidationResult`** — Aggregated result of validating one pyqual.yaml.
- **`LintCollector`** — Lint metrics collector — aggregates findings from linters.
- **`DocumentationCollector`** — Documentation completeness and quality metrics.
- **`ErrorDomain`** — —
- **`EC`** — Namespace for standardised error-code string constants.
- **`Severity`** — —
- **`StageFailure`** — Runtime failure description from a completed stage.
- **`RunStatus`** — —
- **`ProjectRunState`** — —

### Functions

- `App()` — —
- `loadRepositories()` — —
- `repos()` — —
- `handleRepositorySelect()` — —
- `runs()` — —
- `RepositoryCard()` — —
- `lastRun()` — —
- `statusColor()` — —
- `statusIcon()` — —
- `MetricsTrendChart()` — —
- `data()` — —
- `StagesChart()` — —
- `data()` — —
- `Settings()` — —
- `StatusBadge()` — —
- `isPassed()` — —
- `bgClass()` — —
- `Icon()` — —
- `iconColor()` — —
- `RunDetails()` — —
- `MetricsSection()` — —
- `gate()` — —
- `RepositoryDetail()` — —
- `navigate()` — —
- `repo()` — —
- `latestRun()` — —
- `Overview()` — —
- `totalRepos()` — —
- `passingRepos()` — —
- `failingRepos()` — —
- `avgCoverage()` — —
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
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `main()` — Run the metric history self-test with synthetic history.
- `main()` — Run the dynamic-threshold gate example.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `main()` — Run the composite gate self-test with synthetic data.
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
- `check_tool()` — —
- `run_quality_check(config_path, workdir)` — Run pyqual quality pipeline and return True if all gates pass.
- `run_with_callbacks(workdir)` — Run pipeline with progress callbacks.
- `check_prerequisites()` — Check if required tools are available.
- `run_shell_command_example()` — Run a shell command through pyqual's shell helper.
- `run_single_stage(stage_name, tool, workdir)` — Run a single stage without full pipeline.
- `preview_pipeline(config_path)` — Preview pipeline execution without running anything.
- `quick_gate_check(workdir)` — Check if current code passes quality gates.
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `apply_patch(file_path, old_text, new_text)` — Apply a simple text replacement patch.
- `add_docstring(file_path, docstring)` — Add module docstring at the top of a file.
- `parse_and_apply_suggestions(suggestions)` — Parse LLM suggestions and apply patches.
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
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
- `parse_kwargs(kwargs_str)` — Parse kwargs string that might have single quotes.
- `get_last_run(db_path)` — Get the last pipeline run from database.
- `generate_mermaid_diagram(run)` — Generate Mermaid flowchart of pipeline execution.
- `generate_ascii_diagram(run)` — Generate ASCII art diagram of pipeline execution.
- `generate_metrics_table(run)` — Generate metrics table.
- `generate_stage_details(run)` — Generate detailed stage results.
- `generate_report(workdir)` — Generate full markdown report.
- `main()` — Generate and print report.
- `get_changed_files()` — Get files changed in the last commit or current working tree.
- `get_diff_content()` — Get the unified diff of recent changes.
- `evaluate_with_llm(title, description, diff)` — Use LLM to evaluate the implementation quality.
- `main()` — —
- `check_skip_conditions(fp)` — Check if directory should be skipped. Returns ProjectConfig if skip, None otherwise.
- `fetch_github_tasks(label, state, include_issues, include_prs)` — Fetch tasks from GitHub issues and PRs.
- `save_tasks_to_todo(tasks, todo_path, append)` — Save tasks to TODO.md file.
- `save_tasks_to_json(tasks, json_path)` — Save tasks to JSON file.
- `parse_todo_items(todo_path)` — Parse unchecked items from TODO.md.
- `group_similar_issues(issues, max_group_size)` — Group similar issues together for batch processing.
- `run_parallel_fix(workdir, tools, todo_path, issues)` — Convenience function to run parallel fix with multiple tools.
- `normalize_stage_name(name)` — Return a lower-cased, trimmed stage name.
- `is_fix_stage_name(name)` — Return True for fix-like stage names, excluding verification stages.
- `is_verify_stage_name(name)` — Return True for stage names that belong to verification steps.
- `is_delivery_stage_name(name)` — Return True for delivery-style stage names.
- `get_stage_when_default(name)` — Return the default when: value inferred from a stage name.
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
- `main(args)` — Run release check from CLI arguments.
- `check_all(install_missing)` — Check all dependencies and optionally install missing pip packages.
- `main()` — Check and report dependency status.
- `collect_fingerprint(project_dir)` — Collect a lightweight fingerprint from a project directory.
- `classify_with_llm(fp, model)` — Send fingerprint to LLM, parse structured response.
- `generate_pyqual_yaml(project_name, cfg)` — Generate pyqual.yaml content from a ProjectConfig.
- `bulk_init(root)` — Scan subdirectories of *root* and generate pyqual.yaml for each project.
- `analyze_yaml_syntax(content)` — Analyze YAML content for syntax errors without external parsers.
- `fix_yaml_file(config_path, dry_run)` — Analyze and optionally fix a YAML file.
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
- `format_run_summary(summary)` — Format run summary dict into human-readable string with ticket outcomes.
- `get_last_error_line(text)` — Return the last meaningful error line, filtering out informational noise.
- `register_observe_commands(app)` — Register logs, watch, and history commands onto *app*.
- `get_profile(name)` — Return a profile by name, or None if not found.
- `list_profiles()` — Return sorted list of available profile names.
- `query_nfo_db(db_path, event, failed, tail)` — Query the nfo SQLite pipeline log and return structured dicts.
- `row_to_event_dict(row)` — Parse an nfo SQLite row into a structured event dict.
- `format_log_entry_row(entry)` — Return (ts, event_name, name, status, details) for one log entry.
- `get_available_tools(batch_file, batch_count, llm_model, skip_claude)` — Get list of available tools configured for current batch.
- `init(path, profile)` — Create pyqual.yaml with sensible defaults.
- `profiles()` — List available pipeline profiles for pyqual.yaml.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `tools()` — List built-in tool presets for pipeline stages.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_refactor(workdir, project_path, issues, output)` — Run the llx-backed MCP refactor workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `collect_project_metadata(workdir, config)` — Collect project-level metadata for badges and report.
- `collect_all_metrics(workdir)` — Collect all available metrics from .pyqual/ and project/ artifacts.
- `evaluate_gates(config, workdir)` — Evaluate all configured gates and return structured results.
- `generate_report(config, workdir, output)` — Generate a metrics report and write it to YAML.
- `build_badges(metrics, gates_passed, project_meta, gates_passed_count)` — Build full badge block: project info line + quality metrics line.
- `update_readme_badges(readme_path, metrics, gates_passed, project_meta)` — Insert or replace pyqual badges in README.md.
- `run(workdir, config_path, readme_path)` — Run report generation + badge update. Returns 0 on success.
- `main()` — —
- `tune_thresholds(aggressive, conservative, dry_run, config_path)` — Automatically tune quality gate thresholds to match current metrics.
- `tune_show()` — Display all currently collected metrics.
- `git_status_cmd(workdir, json_output)` — Show git repository status.
- `git_add_cmd(paths, workdir)` — Stage files for commit.
- `git_scan_cmd(paths, workdir, use_trufflehog, use_gitleaks)` — Scan files for secrets before push.
- `git_commit_cmd(message, workdir, add_all, if_changed)` — Create a git commit.
- `git_push_cmd(workdir, remote, branch, force)` — Push commits to remote with push protection detection.
- `tickets_sync(workdir, from_gates, backends, dry_run)` — Sync tickets from gate failures or explicitly.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `tickets_fetch(label, state, output, todo_output)` — Fetch GitHub issues/PRs as tasks.
- `tickets_comment(issue_number, message, is_pr)` — Post a comment on a GitHub issue or PR.
- `plugin(action, name, workdir, tag)` — Manage pyqual plugins - add, remove, search metric collectors.
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate YAML configuration snippet for a named plugin.
- `plugin_list(plugins, tag)` — List available plugins, optionally filtered by tag.
- `plugin_search(plugins, query)` — Search plugins by name, description, or tags.
- `plugin_info(name, workdir)` — Show detailed info and configuration example for a plugin.
- `plugin_add(name, workdir)` — Add a plugin's configuration snippet to pyqual.yaml.
- `plugin_remove(name, workdir)` — Remove a plugin's configuration block from pyqual.yaml.
- `plugin_validate(plugins, workdir)` — Validate that configured plugins in pyqual.yaml are available.
- `plugin_unknown_action(action)` — Print an error for an unrecognized plugin sub-command.
- `run(config, dry_run, workdir, verbose)` — Execute pipeline loop until quality gates pass.
- `tune_thresholds_cmd(aggressive, conservative, dry_run, config_path)` — Auto-tune quality gate thresholds based on current metrics.
- `setup_logging(verbose, workdir)` — Configure Python logging for pyqual.pipeline.
- `run_bandit_check(paths, severity, cwd)` — Run bandit security check on Python code.
- `run_pip_audit(output_format, cwd)` — Run pip-audit to check for known vulnerabilities.
- `run_detect_secrets(baseline_file, all_files, cwd)` — Run detect-secrets to find potential secrets.
- `security_summary(workdir)` — Generate comprehensive security summary.
- `code_health_summary(workdir)` — Generate comprehensive code health summary.
- `cmd_check()` — Run attack check and write result to .pyqual/attack_check.json.
- `cmd_merge()` — Run attack check + merge and write results to .pyqual/attack_*.json.
- `main()` — Dispatch subcommands: check | merge (default).
- `gates(config, workdir)` — Check quality gates without running stages.
- `validate(config, workdir, strict, fix)` — Validate pyqual.yaml without running the pipeline.
- `fix_config(config, workdir, dry_run, model)` — Use LLM to auto-repair pyqual.yaml based on project structure.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `report(config, workdir, readme)` — Generate metrics report (YAML) and update README.md badges.
- `run_git_command(args, cwd, check)` — Run a git command with proper error handling.
- `attack_check(cwd)` — Check if attack merge is possible.
- `attack_merge(strategy, cwd, dry_run)` — Perform attack merge with specified strategy.
- `auto_merge_pr(pr_number, branch, cwd)` — Auto-merge a PR or branch when safe to do so.
- `check_readme(readme_path, cwd)` — Analyze README.md for quality metrics.
- `run_interrogate(paths, cwd)` — Run interrogate for docstring coverage.
- `check_links(files, cwd)` — Check for broken links in documentation.
- `docs_quality_summary(cwd)` — Generate comprehensive documentation quality summary.
- `git_status(cwd)` — Get git repository status.
- `run_git_command(args, cwd)` — Run a git command and return the completed process.
- `run_hadolint(dockerfile, cwd)` — Run hadolint on a Dockerfile.
- `run_trivy_scan(image, output_format, cwd)` — Run trivy vulnerability scan on a Docker image.
- `get_image_info(image, cwd)` — Get Docker image information.
- `docker_security_check(image, dockerfile, cwd)` — Run comprehensive Docker security check.
- `coverage_summary(workdir)` — Generate coverage summary.
- `get_outdated_packages(cwd)` — Get list of outdated packages.
- `get_dependency_tree(cwd)` — Get dependency tree using pipdeptree.
- `check_requirements(req_file, cwd)` — Check requirements file for issues.
- `deps_health_check(cwd)` — Run comprehensive dependency health check.
- `example_helper_function()` — Helper function demonstrating utility functions in plugins.
- `run_git_command(args, cwd, check, capture_output)` — Run a git command with proper error handling.
- `git_status(cwd)` — Get git repository status.
- `git_commit(message, cwd, add_all, only_if_changed)` — Create a git commit.
- `git_push(cwd, remote, branch, force)` — Push commits to remote.
- `git_add(paths, cwd)` — Stage files for commit.
- `scan_for_secrets(paths, cwd, use_trufflehog, use_gitleaks)` — Scan for secrets in files before push.
- `preflight_push_check(cwd, remote, branch, scan_secrets)` — Pre-flight check before push - scan for secrets and validate.
- `detect_project_facts(workdir)` — Scan project directory and return facts for LLM-based config repair.
- `lint_summary(workdir)` — Generate comprehensive lint summary.
- `validate_release_state(workdir, registry, bump_patch)` — Validate whether the current package state is safe to publish.
- `create_app(state, llx_server)` — Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `run_case()` — —
- `hello()` — —
- `add()` — —
- `error_domain(code)` — Return the domain of a standardised error code string.
- `validate_config(config_path, try_fix)` — Validate a pyqual.yaml file and return structured issues.


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
📄 `dashboard.src.components.RepositoryDetail` (13 functions, 1 classes)
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
📄 `pyqual._gate_collectors` (27 functions)
📄 `pyqual.analysis` (1 functions)
📄 `pyqual.api` (15 functions, 1 classes)
📄 `pyqual.auto_closer` (7 functions)
📄 `pyqual.bulk.models` (2 classes)
📄 `pyqual.bulk.parser` (2 functions)
📄 `pyqual.bulk.runner` (1 functions)
📄 `pyqual.bulk_init` (15 functions, 1 classes)
📄 `pyqual.bulk_init_classify` (1 functions, 1 classes)
📄 `pyqual.bulk_init_fingerprint` (9 functions, 1 classes)
📄 `pyqual.bulk_run`
📦 `pyqual.cli`
📄 `pyqual.cli.cmd_config` (5 functions)
📄 `pyqual.cli.cmd_git` (8 functions)
📄 `pyqual.cli.cmd_info` (2 functions)
📄 `pyqual.cli.cmd_init` (2 functions)
📄 `pyqual.cli.cmd_mcp` (4 functions)
📄 `pyqual.cli.cmd_plugin` (1 functions)
📄 `pyqual.cli.cmd_run` (11 functions)
📄 `pyqual.cli.cmd_tickets` (6 functions)
📄 `pyqual.cli.cmd_tune` (7 functions)
📄 `pyqual.cli.main` (6 functions)
📄 `pyqual.cli_bulk_cmds` (6 functions)
📄 `pyqual.cli_log_helpers` (3 functions)
📄 `pyqual.cli_observe` (15 functions)
📄 `pyqual.cli_run_helpers` (24 functions)
📄 `pyqual.command` (1 functions)
📄 `pyqual.config` (8 functions, 4 classes)
📄 `pyqual.constants`
📄 `pyqual.custom_fix` (3 functions)
📦 `pyqual.fix_tools` (1 functions)
📄 `pyqual.fix_tools.aider` (3 functions, 1 classes)
📄 `pyqual.fix_tools.base` (5 functions, 2 classes)
📄 `pyqual.fix_tools.claude` (3 functions, 1 classes)
📄 `pyqual.fix_tools.llx` (4 functions, 1 classes)
📦 `pyqual.gate_collectors`
📄 `pyqual.gate_collectors.legacy` (6 functions)
📄 `pyqual.gate_collectors.utils` (1 functions)
📄 `pyqual.gates` (11 functions, 4 classes)
📄 `pyqual.github_actions` (16 functions, 2 classes)
📄 `pyqual.github_tasks` (3 functions)
📦 `pyqual.integrations`
📄 `pyqual.integrations.llx_mcp` (2 functions)
📄 `pyqual.integrations.llx_mcp_service` (4 functions)
📄 `pyqual.llm`
📄 `pyqual.output` (1 functions)
📄 `pyqual.parallel` (7 functions, 4 classes)
📄 `pyqual.pipeline` (26 functions, 1 classes)
📄 `pyqual.pipeline_protocols` (6 functions, 6 classes)
📄 `pyqual.pipeline_results` (3 classes)
📦 `pyqual.plugins` (3 functions)
📄 `pyqual.plugins._base` (7 functions, 3 classes)
📦 `pyqual.plugins.attack`
📄 `pyqual.plugins.attack.__main__` (4 functions)
📄 `pyqual.plugins.attack.main` (9 functions, 1 classes)
📄 `pyqual.plugins.builtin` (14 functions, 7 classes)
📄 `pyqual.plugins.cli_helpers` (7 functions)
📦 `pyqual.plugins.code_health`
📄 `pyqual.plugins.code_health.main` (6 functions, 1 classes)
📦 `pyqual.plugins.coverage`
📄 `pyqual.plugins.coverage.main` (2 functions, 1 classes)
📦 `pyqual.plugins.deps`
📄 `pyqual.plugins.deps.main` (10 functions, 1 classes)
📦 `pyqual.plugins.docker`
📄 `pyqual.plugins.docker.main` (13 functions, 1 classes)
📦 `pyqual.plugins.docs`
📄 `pyqual.plugins.docs.main` (12 functions, 1 classes)
📦 `pyqual.plugins.documentation`
📄 `pyqual.plugins.documentation.main` (11 functions, 1 classes)
📦 `pyqual.plugins.example_plugin`
📄 `pyqual.plugins.example_plugin.main` (3 functions, 1 classes)
📦 `pyqual.plugins.git`
📄 `pyqual.plugins.git.git_command` (1 functions)
📄 `pyqual.plugins.git.main` (21 functions, 1 classes)
📄 `pyqual.plugins.git.status` (1 functions)
📦 `pyqual.plugins.lint`
📄 `pyqual.plugins.lint.main` (6 functions, 1 classes)
📦 `pyqual.plugins.security`
📄 `pyqual.plugins.security.main` (11 functions, 1 classes)
📄 `pyqual.profiles` (2 functions, 1 classes)
📄 `pyqual.release_check` (2 functions)
📄 `pyqual.report` (18 functions)
📄 `pyqual.report_generator` (14 functions, 2 classes)
📄 `pyqual.run_parallel_fix` (12 functions)
📄 `pyqual.setup_deps` (5 functions, 1 classes)
📄 `pyqual.stage_names` (5 functions)
📄 `pyqual.tickets` (7 functions)
📄 `pyqual.tools` (15 functions, 1 classes)
📦 `pyqual.validation`
📄 `pyqual.validation.config_check` (7 functions)
📄 `pyqual.validation.errors` (4 functions, 4 classes)
📄 `pyqual.validation.project` (2 functions)
📄 `pyqual.validation.release` (9 functions)
📄 `pyqual.validation.schema` (2 functions, 2 classes)
📄 `pyqual.yaml_fixer` (12 functions, 3 classes)
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