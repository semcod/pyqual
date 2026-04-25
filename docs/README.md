<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-2003-green)
> **2003** functions | **125** classes | **295** files | CC̄ = 4.8

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




## Architecture

```
pyqual/
├── TODO_mocked
├── SUMR
├── REQUEST_FOR_FILES
├── SUGGESTED_COMMANDS
├── goal
            ├── history
├── planfile
├── run_analysis
├── REQUEST_EDIT_FILES
├── Makefile
├── REQUEST_ADD_FILES
├── SUMD
├── pyqual/
├── renovate
├── tree
    ├── planfile
├── TODO
├── prefact
├── CHANGELOG
├── Taskfile
├── README
        ├── node
    ├── tsconfig
        ├── config
        ├── config
        ├── config
        ├── config
    ├── package
    ├── README
    ├── constants
        ├── main
        ├── App
            ├── MetricsTrendChart
            ├── StagesChart
            ├── Settings
            ├── Overview
            ├── RepositoryDetail
            ├── MetricsChart
        ├── types/
        ├── api/
            ├── example
        ├── requirements
        ├── main
    ├── ai-fix-tools
    ├── integrations
    ├── quickstart
    ├── ci-dashboard-integration
    ├── configuration
    ├── api
    ├── runtime-errors
    ├── README
    ├── integration_example
    ├── README
        ├── both-backends
        ├── all-backends
        ├── README
        ├── github-only
        ├── markdown-only
        ├── metric_history
        ├── composite_gates
        ├── pyqual
        ├── dynamic_thresholds
        ├── composite_simple
        ├── README
        ├── README
        ├── pyqual
        ├── README
        ├── README
        ├── README
        ├── README
        ├── performance_collector
        ├── pyqual
        ├── code_health_collector
        ├── README
        ├── README
        ├── pyqual
        ├── README
        ├── sync_if_fail
        ├── minimal
        ├── check_gates
        ├── run_pipeline
        ├── pyqual
        ├── README
        ├── demo
        ├── pyqual-llx
        ├── README
        ├── pyqual
        ├── README
        ├── docker-compose
        ├── pyqual
        ├── Dockerfile
        ├── README
        ├── run_pipeline
        ├── pyqual
        ├── TODO
        ├── CHANGELOG
        ├── README
        ├── pyqual
        ├── sync_tickets
        ├── README
        ├── analysis_summary
            ├── toon
            ├── toon
            ├── toon
        ├── REQUEST_ADD_FILES
    ├── custom_fix
    ├── config
    ├── llm
    ├── report_generator
    ├── command
    ├── tools
    ├── auto_closer
    ├── pipeline_protocols
    ├── github_tasks
    ├── analysis
    ├── bulk_init_classify
    ├── gates
    ├── parallel
    ├── bulk_run
    ├── pipeline_results
    ├── stage_names
    ├── tickets
    ├── __main__
    ├── cli_bulk_cmds
    ├── api
    ├── github_actions
    ├── validation/
    ├── run_parallel_fix
    ├── _gate_collectors
    ├── yaml_fixer
    ├── release_check
    ├── setup_deps
    ├── bulk_init
    ├── bulk_init_fingerprint
    ├── pipeline
    ├── cli_observe
    ├── cli_run_helpers
    ├── profiles
    ├── cli_log_helpers
    ├── report
    ├── constants
    ├── default_tools
        ├── legacy
    ├── gate_collectors/
        ├── utils
        ├── base
    ├── fix_tools/
        ├── aider
        ├── claude
        ├── llx
        ├── cmd_git
        ├── cmd_info
        ├── cmd_init
    ├── cli/
        ├── cmd_mcp
        ├── cmd_run
        ├── cmd_tune
        ├── cmd_tickets
        ├── main
        ├── cmd_config
        ├── cmd_plugin
    ├── plugins/
        ├── cli_helpers
        ├── _base
        ├── builtin
        ├── docs/
            ├── test
            ├── main
            ├── README
        ├── security/
            ├── test
            ├── main
            ├── README
        ├── code_health/
            ├── main
        ├── attack/
            ├── __main__
            ├── test
            ├── main
            ├── README
        ├── docker/
            ├── test
            ├── main
            ├── README
        ├── deps/
            ├── test
            ├── main
            ├── README
        ├── lint/
            ├── main
            ├── status
        ├── git/
            ├── git_command
            ├── test
            ├── main
            ├── README
        ├── coverage/
            ├── main
        ├── example_plugin/
            ├── test
            ├── main
            ├── README
        ├── documentation/
            ├── test
            ├── main
            ├── README
        ├── schema
        ├── errors
        ├── release
        ├── config_check
        ├── runner
        ├── parser
        ├── orchestrator
        ├── models
        ├── llx_mcp_service
    ├── integrations/
        ├── llx_mcp
    ├── run_docker_matrix
    ├── run_matrix
    ├── Dockerfile
├── project
├── pyproject
        ├── toon
                ├── toon
    ├── logs-and-data
                ├── toon
            ├── context
            ├── prompt
                ├── toon
        ├── toon
    ├── context
                ├── toon
                ├── toon
                ├── toon
                ├── toon
                ├── toon
            ├── README
            ├── context
                ├── toon
                ├── toon
            ├── prompt
                ├── toon
            ├── README
                ├── toon
                ├── toon
            ├── context
                ├── toon
            ├── README
                ├── toon
            ├── context
                ├── toon
                ├── toon
                ├── toon
            ├── context
        ├── pyqual
            ├── README
                ├── toon
            ├── prompt
                ├── toon
            ├── README
                ├── toon
            ├── prompt
                ├── toon
                ├── toon
    ├── README
    ├── prompt
        ├── toon
            ├── README
    ├── planfile
                ├── toon
        ├── toon
        ├── toon
        ├── toon
                ├── toon
            ├── toon
    ├── README
    ├── context
            ├── toon
            ├── toon
            ├── prompt
            ├── toon
        ├── context
        ├── toon
        ├── toon
        ├── context
            ├── toon
    ├── calls
        ├── toon
    ├── output
        ├── project
```

## API Overview

### Classes

- **`Pipeline`** — —
- **`BulkInitResult`** — —
- **`Pipeline`** — —
- **`BulkInitResult`** — —
- **`MetricsTrendChartProps`** — —
- **`StagesChartProps`** — —
- **`OverviewProps`** — —
- **`RepositoryDetailProps`** — —
- **`MetricsChartProps`** — —
- **`PyqualMetric`** — —
- **`PyqualStage`** — —
- **`PyqualSummary`** — —
- **`Repository`** — —
- **`DashboardConfig`** — —
- **`MetricHistory`** — —
- **`MetricTrend`** — —
- **`MyGateSet`** — —
- **`MyToolCollector`** — —
- **`PerformanceCollector`** — Collect latency and throughput metrics from load test results.
- **`CodeHealthCollector`** — Weighted composite health score from multiple code quality signals.
- **`MyCollector`** — —
- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`StageResult`** — —
- **`PipelineRun`** — —
- **`ToolPreset`** — Definition of a built-in tool invocation preset.
- **`OnStageStart`** — —
- **`OnIterationStart`** — —
- **`OnStageError`** — —
- **`OnStageDone`** — Called after each stage completes. Receives the full StageResult.
- **`OnStageOutput`** — Called with each line of streaming output from a stage.
- **`OnIterationDone`** — Called after each iteration completes. Receives the full IterationResult.
- **`ProjectConfig`** — Parsed LLM response — project-specific config decisions.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.
- **`CompositeGateSet`** — Weighted composite quality scoring from multiple gates.
- **`FixTool`** — Configuration for a single fix tool.
- **`TaskResult`** — Result of processing a single task.
- **`ParallelRunResult`** — Result of parallel execution.
- **`ParallelExecutor`** — Executes tasks across multiple fix tools in parallel.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`ShellHelper`** — Shell helper utilities for external tool integration.
- **`GitHubTask`** — Represents a task from GitHub (issue or PR).
- **`GitHubActionsReporter`** — Reports pyqual results to GitHub Actions and PRs.
- **`YamlErrorType`** — Types of YAML syntax errors we can detect and fix.
- **`YamlSyntaxIssue`** — A single YAML syntax issue with location and fix information.
- **`YamlFixResult`** — Result of parsing/fixing YAML.
- **`DepResult`** — Result of a single dependency check.
- **`BulkInitResult`** — Summary of a bulk-init run.
- **`ProjectFingerprint`** — Lightweight summary of a project directory sent to LLM for classification.
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.
- **`PipelineProfile`** — A reusable pipeline template with default stages and metrics.
- **`ToolResult`** — Result from running a fix tool.
- **`FixTool`** — Abstract base class for fix tools.
- **`AiderTool`** — Aider tool via Docker (paulgauthier/aider).
- **`ClaudeTool`** — Claude Code CLI tool.
- **`LlxTool`** — LLX fix tool.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`LlxMcpFixCollector`** — Dockerized llx MCP fix/refactor workflow results.
- **`TestDocsCollector`** — Test DocsCollector metric collection.
- **`TestCheckReadme`** — Test README checking.
- **`TestInterrogate`** — Test interrogate integration.
- **`TestCheckLinks`** — Test link checking.
- **`TestDocsQualitySummary`** — Test comprehensive docs summary.
- **`DocsCollector`** — Documentation quality metrics collector.
- **`TestSecurityCollector`** — Test SecurityCollector metric collection.
- **`TestBanditCheck`** — Test bandit check functionality.
- **`TestPipAudit`** — Test pip-audit functionality.
- **`TestDetectSecrets`** — Test detect-secrets functionality.
- **`TestSecuritySummary`** — Test security summary aggregation.
- **`SecurityCollector`** — Security metrics collector — aggregates findings from security scanners.
- **`CodeHealthCollector`** — Code health metrics collector — maintainability, dead code, packaging quality.
- **`TestAttackCollector`** — Test AttackCollector class.
- **`TestAttackCheck`** — Test attack_check function.
- **`TestAttackMerge`** — Test attack_merge function.
- **`TestAutoMergePR`** — Test auto_merge_pr function.
- **`TestMergeStrategies`** — Test merge strategy constants.
- **`AttackCollector`** — Attack merge collector — automerge with aggressive conflict resolution.
- **`TestDockerCollector`** — Test DockerCollector metric collection.
- **`TestHadolint`** — Test hadolint integration.
- **`TestTrivyScan`** — Test trivy integration.
- **`TestDockerSecurityCheck`** — Test comprehensive security check.
- **`DockerCollector`** — Docker security and quality metrics collector.
- **`TestDepsCollector`** — Test DepsCollector metric collection.
- **`TestGetOutdatedPackages`** — Test outdated packages functionality.
- **`TestGetDependencyTree`** — Test dependency tree functionality.
- **`TestCheckRequirements`** — Test requirements file checking.
- **`TestDepsHealthCheck`** — Test comprehensive health check.
- **`DepsCollector`** — Dependency management metrics collector.
- **`LintCollector`** — Lint metrics collector — aggregates findings from linters.
- **`TestGitCollector`** — Tests for the GitCollector class.
- **`TestGitStatus`** — Tests for git_status function.
- **`TestGitCommit`** — Tests for git_commit function.
- **`TestSecretScanning`** — Tests for secret scanning functionality.
- **`TestPreFlightCheck`** — Tests for preflight_push_check function.
- **`TestSecretPatterns`** — Tests for SECRET_PATTERNS regex patterns.
- **`GitCollector`** — Git repository operations collector — status, commit, push with protection handling.
- **`CoverageCollector`** — Coverage metrics collector — extracts test coverage data.
- **`TestExampleCollector`** — Tests for the ExampleCollector class.
- **`TestHelperFunctions`** — Tests for helper functions.
- **`ExampleCollector`** — Example collector showing plugin structure.
- **`TestDocumentationCollector`** — Test DocumentationCollector metric collection.
- **`DocumentationCollector`** — Documentation completeness and quality metrics.
- **`ValidationIssue`** — Single validation finding.
- **`ValidationResult`** — Aggregated result of validating one pyqual.yaml.
- **`ErrorDomain`** — —
- **`EC`** — Namespace for standardised error-code string constants.
- **`Severity`** — —
- **`StageFailure`** — Runtime failure description from a completed stage.
- **`BulkRunResult`** — —
- **`RunStatus`** — —
- **`ProjectRunState`** — —

### Functions

- `print()` — —
- `run()` — —
- `check_gates()` — —
- `count_todo_items()` — —
- `extract_pytest_stage_summary()` — —
- `extract_lint_stage_summary()` — —
- `extract_prefact_stage_summary()` — —
- `extract_code2llm_stage_summary()` — —
- `extract_validation_stage_summary()` — —
- `extract_fix_stage_summary()` — —
- `extract_mypy_stage_summary()` — —
- `extract_bandit_stage_summary()` — —
- `extract_stage_summary()` — —
- `enrich_from_artifacts()` — —
- `infer_fix_result()` — —
- `build_run_summary()` — —
- `format_run_summary()` — —
- `get_last_error_line()` — —
- `collect_project_metadata()` — —
- `collect_all_metrics()` — —
- `evaluate_gates()` — —
- `generate_report()` — —
- `build_badges()` — —
- `update_readme_badges()` — —
- `main()` — —
- `classify_with_llm()` — —
- `generate_pyqual_yaml()` — —
- `bulk_init()` — —
- `total()` — —
- `Questions()` — —
- `run_project(project_path)` — —
- `main()` — —
- `print()` — —
- `get_db_path()` — —
- `read_summary_json()` — —
- `query_pipeline_db()` — —
- `safe_parse()` — —
- `get_projects()` — —
- `get_latest_run()` — —
- `get_project_runs()` — —
- `get_metric_history()` — —
- `get_stage_performance()` — —
- `get_gate_status()` — —
- `get_project_summary()` — —
- `ingest_results()` — —
- `health_check()` — —
- `compute_composite_score()` — —
- `run_composite_check()` — —
- `main()` — —
- `load_history()` — —
- `save_snapshot()` — —
- `detect_regressions()` — —
- `print_trend_report()` — —
- `run_quality_check()` — —
- `run_with_callbacks()` — —
- `check_prerequisites()` — —
- `run_shell_command_example()` — —
- `run_single_stage()` — —
- `preview_pipeline()` — —
- `quick_gate_check()` — —
- `build_report()` — —
- `sync_from_cli()` — —
- `tickets_from_gate_failures()` — —
- `load_config()` — —
- `validate_config()` — —
- `create_default_config()` — —
- `run()` — —
- `run_pipeline()` — —
- `check_gates()` — —
- `dry_run()` — —
- `run_stage()` — —
- `get_tool_command()` — —
- `format_result_summary()` — —
- `export_results_json()` — —
- `shell_check()` — —
- `get_changed_files()` — —
- `get_diff_content()` — —
- `evaluate_with_llm()` — —
- `discover_projects()` — —
- `build_dashboard_table()` — —
- `bulk_run()` — —
- `classify_with_llm()` — —
- `generate_pyqual_yaml()` — —
- `bulk_init()` — —
- `check_skip_conditions()` — —
- `collect_fingerprint()` — —
- `gates()` — —
- `validate()` — —
- `fix_config()` — —
- `status()` — —
- `report()` — —
- `git_status_cmd()` — —
- `git_add_cmd()` — —
- `git_scan_cmd()` — —
- `git_commit_cmd()` — —
- `git_push_cmd()` — —
- `doctor()` — —
- `tools()` — —
- `init()` — —
- `profiles()` — —
- `mcp_fix()` — —
- `mcp_refactor()` — —
- `mcp_service()` — —
- `plugin()` — —
- `tickets_sync()` — —
- `tickets_todo()` — —
- `tickets_github()` — —
- `tickets_all()` — —
- `tickets_fetch()` — —
- `tickets_comment()` — —
- `tune_thresholds()` — —
- `tune_show()` — —
- `tune_thresholds_cmd()` — —
- `setup_logging()` — —
- `register_bulk_commands()` — —
- `query_nfo_db()` — —
- `row_to_event_dict()` — —
- `format_log_entry_row()` — —
- `register_observe_commands()` — —
- `count_todo_items()` — —
- `extract_pytest_stage_summary()` — —
- `extract_lint_stage_summary()` — —
- `extract_prefact_stage_summary()` — —
- `extract_code2llm_stage_summary()` — —
- `extract_validation_stage_summary()` — —
- `extract_fix_stage_summary()` — —
- `extract_mypy_stage_summary()` — —
- `extract_bandit_stage_summary()` — —
- `extract_stage_summary()` — —
- `enrich_from_artifacts()` — —
- `infer_fix_result()` — —
- `build_run_summary()` — —
- `format_run_summary()` — —
- `get_last_error_line()` — —
- `apply_patch()` — —
- `add_docstring()` — —
- `parse_and_apply_suggestions()` — —
- `get_available_tools()` — —
- `fetch_github_tasks()` — —
- `save_tasks_to_todo()` — —
- `save_tasks_to_json()` — —
- `build_parser()` — —
- `create_app()` — —
- `run_server()` — —
- `parse_todo_items()` — —
- `group_similar_issues()` — —
- `run_parallel_fix()` — —
- `get_available_plugins()` — —
- `install_plugin_config()` — —
- `cmd_check()` — —
- `cmd_merge()` — —
- `run_git_command()` — —
- `attack_check()` — —
- `attack_merge()` — —
- `auto_merge_pr()` — —
- `plugin_list()` — —
- `plugin_search()` — —
- `plugin_info()` — —
- `plugin_add()` — —
- `plugin_remove()` — —
- `plugin_validate()` — —
- `plugin_unknown_action()` — —
- `code_health_summary()` — —
- `coverage_summary()` — —
- `get_outdated_packages()` — —
- `get_dependency_tree()` — —
- `check_requirements()` — —
- `deps_health_check()` — —
- `run_hadolint()` — —
- `run_trivy_scan()` — —
- `get_image_info()` — —
- `docker_security_check()` — —
- `check_readme()` — —
- `run_interrogate()` — —
- `check_links()` — —
- `docs_quality_summary()` — —
- `example_helper_function()` — —
- `git_status()` — —
- `git_commit()` — —
- `git_push()` — —
- `git_add()` — —
- `scan_for_secrets()` — —
- `preflight_push_check()` — —
- `lint_summary()` — —
- `run_bandit_check()` — —
- `run_pip_audit()` — —
- `run_detect_secrets()` — —
- `security_summary()` — —
- `get_profile()` — —
- `list_profiles()` — —
- `collect_project_metadata()` — —
- `collect_all_metrics()` — —
- `evaluate_gates()` — —
- `generate_report()` — —
- `build_badges()` — —
- `update_readme_badges()` — —
- `parse_kwargs()` — —
- `get_last_run()` — —
- `generate_mermaid_diagram()` — —
- `generate_ascii_diagram()` — —
- `generate_metrics_table()` — —
- `generate_stage_details()` — —
- `get_todo_batch()` — —
- `mark_completed_todos()` — —
- `run_tool()` — —
- `git_commit_and_push()` — —
- `parse_args()` — —
- `check_all()` — —
- `normalize_stage_name()` — —
- `is_fix_stage_name()` — —
- `is_verify_stage_name()` — —
- `is_delivery_stage_name()` — —
- `get_stage_when_default()` — —
- `sync_planfile_tickets()` — —
- `sync_todo_tickets()` — —
- `sync_github_tickets()` — —
- `sync_all_tickets()` — —
- `sync_from_gates()` — —
- `get_preset()` — —
- `list_presets()` — —
- `is_builtin()` — —
- `register_preset()` — —
- `load_user_tools()` — —
- `preset_to_dict()` — —
- `dump_presets_json()` — —
- `register_custom_tools_from_yaml()` — —
- `load_entry_point_presets()` — —
- `resolve_stage_command()` — —
- `error_domain()` — —
- `detect_project_facts()` — —
- `validate_release_state()` — —
- `analyze_yaml_syntax()` — —
- `fix_yaml_file()` — —
- `run_project()` — —
- `test_github_connection()` — —
- `test_todo_creation()` — —
- `test_default_yaml_parses()` — —
- `test_gate_config_from_dict()` — —
- `test_gate_check_pass()` — —
- `test_gate_check_fail()` — —
- `test_gate_check_missing_metric()` — —
- `test_gate_set_from_toon()` — —
- `test_gate_set_from_vallm()` — —
- `test_gate_set_from_coverage()` — —
- `test_pipeline_dry_run()` — —
- `test_pipeline_with_passing_gates()` — —
- `test_pipeline_runs_fix_chain_when_gates_fail()` — —
- `test_timeout_zero_means_no_timeout()` — —
- `test_tool_preset_stage_config()` — —
- `test_tool_preset_dry_run()` — —
- `test_tool_preset_resolution()` — —
- `test_stage_requires_run_or_tool()` — —
- `test_stage_rejects_both_run_and_tool()` — —
- `test_stage_rejects_unknown_tool()` — —
- `test_pipeline_writes_nfo_sqlite_log()` — —
- `test_stage_result_preserves_original_returncode()` — —
- `test_default_tools_json_loads_all_presets()` — —
- `test_preset_from_dict()` — —
- `test_load_user_tools_from_json()` — —
- `test_load_user_tools_no_file()` — —
- `test_dump_presets_json()` — —
- `test_register_custom_preset()` — —
- `test_custom_tools_from_yaml()` — —
- `make_project()` — —
- `write_config()` — —
- `workspace()` — —
- `anyio_backend()` — —
- `test_llx_mcp_plugin_collects_metrics()` — —
- `test_load_issue_source_parses_todo_md()` — —
- `test_llx_mcp_plugin_config_example_contains_stage()` — —
- `test_run_llx_fix_workflow_uses_todo_md_fallback()` — —
- `test_run_llx_refactor_workflow_uses_refactor_prompt()` — —
- `test_mcp_fix_cli_invokes_workflow()` — —
- `test_mcp_refactor_cli_invokes_workflow()` — —
- `test_mcp_service_cli_shows_friendly_error()` — —
- `test_persistent_mcp_service_exposes_health_and_metrics()` — —
- `test_build_fix_prompt_uses_issue_summary()` — —
- `pipeline()` — —
- `test_placeholder()` — —
- `test_import()` — —
- `test_llm_exports_use_llx_when_available()` — —
- `test_gate_set_reads_project_toon_artifacts()` — —
- `test_gate_set_derives_completion_rate()` — —
- `test_collect_all_metrics_reads_toon_and_coverage()` — —
- `test_collect_all_metrics_empty_dir()` — —
- `test_generate_report_creates_yaml()` — —
- `test_generate_report_gates_pass()` — —
- `test_generate_report_gates_fail()` — —
- `test_build_badges_pass()` — —
- `test_build_badges_fail()` — —
- `test_build_badges_empty_metrics_no_project_meta()` — —
- `test_build_badges_with_project_meta()` — —
- `test_build_badges_gates_ratio()` — —
- `test_project_badges_all_fields()` — —
- `test_project_badges_empty_meta()` — —
- `test_project_badges_ai_cost_colors()` — —
- `test_quality_badges_with_extra_metrics()` — —
- `test_read_costs_from_json()` — —
- `test_read_costs_empty_dir()` — —
- `test_update_readme_inserts_markers_after_existing_badges()` — —
- `test_update_readme_replaces_existing_markers()` — —
- `test_update_readme_no_change_when_identical()` — —
- `test_update_readme_no_file()` — —
- `test_update_readme_inserts_at_top_when_no_badges()` — —
- `test_run_integration()` — —
- `test_run_integration_with_costs()` — —
- `test_quality_badges_no_metrics()` — —
- `test_read_costs_data_missing_file()` — —
- `test_update_readme_badges_noop_markers()` — —
- `test_sync_todo_tickets_uses_planfile_markdown_backend()` — —
- `test_sync_github_tickets_uses_planfile_github_backend()` — —
- `test_sync_all_tickets_calls_both_backends()` — —
- `test_tickets_todo_cli_invokes_sync_helper()` — —
- `test_run_on_fail_create_ticket_syncs_todo_tickets()` — —
- `test_run_report_includes_todo_and_fix_summary()` — —
- `test_temp_dir_creation()` — —
- `total()` — —
- `print()` — —
- `print()` — —
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
- `Overview()` — —
- `totalRepos()` — —
- `passingRepos()` — —
- `failingRepos()` — —
- `avgCoverage()` — —
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
- `print()` — —
- `collect()` — —
- `generate_readme()` — —
- `run_quality_check(config_path, workdir)` — Run pyqual quality pipeline and return True if all gates pass.
- `run_with_callbacks(workdir)` — Run pipeline with progress callbacks.
- `check_prerequisites()` — Check if required tools are available.
- `run_shell_command_example()` — Run a shell command through pyqual's shell helper.
- `run_single_stage(stage_name, tool, workdir)` — Run a single stage without full pipeline.
- `preview_pipeline(config_path)` — Preview pipeline execution without running anything.
- `quick_gate_check(workdir)` — Check if current code passes quality gates.
- `load_history(workdir)` — Load metric history from JSON file.
- `save_snapshot(workdir, metrics)` — Append current metrics as a timestamped snapshot and return full history.
- `detect_regressions(history, tolerance)` — Compare latest snapshot to previous and detect regressions.
- `print_trend_report(analysis)` — Print trend analysis and return True if no regressions found.
- `main()` — Run the metric history self-test with synthetic history.
- `compute_composite_score(metrics)` — Compute a weighted quality score (0–100) from available metrics.
- `run_composite_check(workdir)` — Run individual gates + composite score on a workdir.
- `main()` — Run the composite gate self-test with synthetic data.
- `main()` — Run the dynamic-threshold gate example.
- `collect()` — —
- `print()` — —
- `exit()` — —
- `check_tool()` — —
- `build_report(result, gate_results)` — Build a structured JSON report from pipeline + gate results.
- `main()` — —
- `sync_from_cli(args)` — Parse CLI args and run the appropriate sync.
- `tickets_from_gate_failures(workdir, dry_run)` — Check gates and create tickets for any failures.
- `main()` — —
- `apply_patch(file_path, old_text, new_text)` — Apply a simple text replacement patch.
- `add_docstring(file_path, docstring)` — Add module docstring at the top of a file.
- `parse_and_apply_suggestions(suggestions)` — Parse LLM suggestions and apply patches.
- `parse_kwargs(kwargs_str)` — Parse kwargs string that might have single quotes.
- `get_last_run(db_path)` — Get the last pipeline run from database.
- `generate_mermaid_diagram(run)` — Generate Mermaid flowchart of pipeline execution.
- `generate_ascii_diagram(run)` — Generate ASCII art diagram of pipeline execution.
- `generate_metrics_table(run)` — Generate metrics table.
- `generate_stage_details(run)` — Generate detailed stage results.
- `generate_report(workdir)` — Generate full markdown report.
- `main()` — Generate and print report.
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
- `get_changed_files()` — Get files changed in the last commit or current working tree.
- `get_diff_content()` — Get the unified diff of recent changes.
- `evaluate_with_llm(title, description, diff)` — Use LLM to evaluate the implementation quality.
- `main()` — —
- `fetch_github_tasks(label, state, include_issues, include_prs)` — Fetch tasks from GitHub issues and PRs.
- `save_tasks_to_todo(tasks, todo_path, append)` — Save tasks to TODO.md file.
- `save_tasks_to_json(tasks, json_path)` — Save tasks to JSON file.
- `check_skip_conditions(fp)` — Check if directory should be skipped. Returns ProjectConfig if skip, None otherwise.
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
- `analyze_yaml_syntax(content)` — Analyze YAML content for syntax errors without external parsers.
- `fix_yaml_file(config_path, dry_run)` — Analyze and optionally fix a YAML file.
- `main(args)` — Run release check from CLI arguments.
- `check_all(install_missing)` — Check all dependencies and optionally install missing pip packages.
- `main()` — Check and report dependency status.
- `classify_with_llm(fp, model)` — Send fingerprint to LLM, parse structured response.
- `generate_pyqual_yaml(project_name, cfg)` — Generate pyqual.yaml content from a ProjectConfig.
- `bulk_init(root)` — Scan subdirectories of *root* and generate pyqual.yaml for each project.
- `collect_fingerprint(project_dir)` — Collect a lightweight fingerprint from a project directory.
- `register_observe_commands(app)` — Register logs, watch, and history commands onto *app*.
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
- `get_profile(name)` — Return a profile by name, or None if not found.
- `list_profiles()` — Return sorted list of available profile names.
- `query_nfo_db(db_path, event, failed, tail)` — Query the nfo SQLite pipeline log and return structured dicts.
- `row_to_event_dict(row)` — Parse an nfo SQLite row into a structured event dict.
- `format_log_entry_row(entry)` — Return (ts, event_name, name, status, details) for one log entry.
- `collect_project_metadata(workdir, config)` — Collect project-level metadata for badges and report.
- `collect_all_metrics(workdir)` — Collect all available metrics from .pyqual/ and project/ artifacts.
- `evaluate_gates(config, workdir)` — Evaluate all configured gates and return structured results.
- `generate_report(config, workdir, output)` — Generate a metrics report and write it to YAML.
- `build_badges(metrics, gates_passed, project_meta, gates_passed_count)` — Build full badge block: project info line + quality metrics line.
- `update_readme_badges(readme_path, metrics, gates_passed, project_meta)` — Insert or replace pyqual badges in README.md.
- `run(workdir, config_path, readme_path)` — Run report generation + badge update. Returns 0 on success.
- `main()` — —
- `get_available_tools(batch_file, batch_count, llm_model, skip_claude)` — Get list of available tools configured for current batch.
- `git_status_cmd(workdir, json_output)` — Show git repository status.
- `git_add_cmd(paths, workdir)` — Stage files for commit.
- `git_scan_cmd(paths, workdir, use_trufflehog, use_gitleaks)` — Scan files for secrets before push.
- `git_commit_cmd(message, workdir, add_all, if_changed)` — Create a git commit.
- `git_push_cmd(workdir, remote, branch, force)` — Push commits to remote with push protection detection.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `tools()` — List built-in tool presets for pipeline stages.
- `init(path, profile)` — Create pyqual.yaml with sensible defaults.
- `profiles()` — List available pipeline profiles for pyqual.yaml.
- `mcp_fix(workdir, project_path, issues, output)` — Run the llx-backed MCP fix workflow.
- `mcp_refactor(workdir, project_path, issues, output)` — Run the llx-backed MCP refactor workflow.
- `mcp_service(host, port)` — Run the persistent llx MCP service with health and metrics endpoints.
- `run(config, dry_run, workdir, verbose)` — Execute pipeline loop until quality gates pass.
- `tune_thresholds(aggressive, conservative, dry_run, config_path)` — Automatically tune quality gate thresholds to match current metrics.
- `tune_show()` — Display all currently collected metrics.
- `tickets_sync(workdir, from_gates, backends, dry_run)` — Sync tickets from gate failures or explicitly.
- `tickets_todo(workdir, dry_run, direction)` — Sync TODO.md tickets using planfile's markdown backend.
- `tickets_github(workdir, dry_run, direction)` — Sync GitHub Issues using planfile's GitHub backend.
- `tickets_all(workdir, dry_run, direction)` — Sync TODO.md and GitHub tickets using planfile.
- `tickets_fetch(label, state, output, todo_output)` — Fetch GitHub issues/PRs as tasks.
- `tickets_comment(issue_number, message, is_pr)` — Post a comment on a GitHub issue or PR.
- `tune_thresholds_cmd(aggressive, conservative, dry_run, config_path)` — Auto-tune quality gate thresholds based on current metrics.
- `setup_logging(verbose, workdir)` — Configure Python logging for pyqual.pipeline.
- `gates(config, workdir)` — Check quality gates without running stages.
- `validate(config, workdir, strict, fix)` — Validate pyqual.yaml without running the pipeline.
- `fix_config(config, workdir, dry_run, model)` — Use LLM to auto-repair pyqual.yaml based on project structure.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `report(config, workdir, readme)` — Generate metrics report (YAML) and update README.md badges.
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
- `check_readme(readme_path, cwd)` — Analyze README.md for quality metrics.
- `run_interrogate(paths, cwd)` — Run interrogate for docstring coverage.
- `check_links(files, cwd)` — Check for broken links in documentation.
- `docs_quality_summary(cwd)` — Generate comprehensive documentation quality summary.
- `print()` — —
- `run_bandit_check(paths, severity, cwd)` — Run bandit security check on Python code.
- `run_pip_audit(output_format, cwd)` — Run pip-audit to check for known vulnerabilities.
- `run_detect_secrets(baseline_file, all_files, cwd)` — Run detect-secrets to find potential secrets.
- `security_summary(workdir)` — Generate comprehensive security summary.
- `print()` — —
- `code_health_summary(workdir)` — Generate comprehensive code health summary.
- `cmd_check()` — Run attack check and write result to .pyqual/attack_check.json.
- `cmd_merge()` — Run attack check + merge and write results to .pyqual/attack_*.json.
- `main()` — Dispatch subcommands: check | merge (default).
- `run_git_command(args, cwd, check)` — Run a git command with proper error handling.
- `attack_check(cwd)` — Check if attack merge is possible.
- `attack_merge(strategy, cwd, dry_run)` — Perform attack merge with specified strategy.
- `auto_merge_pr(pr_number, branch, cwd)` — Auto-merge a PR or branch when safe to do so.
- `run_hadolint(dockerfile, cwd)` — Run hadolint on a Dockerfile.
- `run_trivy_scan(image, output_format, cwd)` — Run trivy vulnerability scan on a Docker image.
- `get_image_info(image, cwd)` — Get Docker image information.
- `docker_security_check(image, dockerfile, cwd)` — Run comprehensive Docker security check.
- `print()` — —
- `get_outdated_packages(cwd)` — Get list of outdated packages.
- `get_dependency_tree(cwd)` — Get dependency tree using pipdeptree.
- `check_requirements(req_file, cwd)` — Check requirements file for issues.
- `deps_health_check(cwd)` — Run comprehensive dependency health check.
- `print()` — —
- `lint_summary(workdir)` — Generate comprehensive lint summary.
- `git_status(cwd)` — Get git repository status.
- `run_git_command(args, cwd)` — Run a git command and return the completed process.
- `run_git_command(args, cwd, check, capture_output)` — Run a git command with proper error handling.
- `git_status(cwd)` — Get git repository status.
- `git_commit(message, cwd, add_all, only_if_changed)` — Create a git commit.
- `git_push(cwd, remote, branch, force)` — Push commits to remote.
- `git_add(paths, cwd)` — Stage files for commit.
- `scan_for_secrets(paths, cwd, use_trufflehog, use_gitleaks)` — Scan for secrets in files before push.
- `preflight_push_check(cwd, remote, branch, scan_secrets)` — Pre-flight check before push - scan for secrets and validate.
- `print()` — —
- `coverage_summary(workdir)` — Generate coverage summary.
- `example_helper_function()` — Helper function demonstrating utility functions in plugins.
- `print()` — —
- `error_domain(code)` — Return the domain of a standardised error code string.
- `validate_release_state(workdir, registry, bump_patch)` — Validate whether the current package state is safe to publish.
- `validate_config(config_path, try_fix)` — Validate a pyqual.yaml file and return structured issues.
- `discover_projects(root)` — —
- `build_dashboard_table(states, show_last_line)` — —
- `bulk_run(root, parallel, pyqual_cmd, filter_names)` — —
- `create_app(state, llx_server)` — Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``.
- `run_server(host, port, state)` — Run the persistent MCP service with uvicorn.
- `build_parser()` — Build the CLI parser for the MCP service.
- `main(argv)` — CLI entry point for the llx MCP service.
- `build_parser()` — Build the CLI parser for the llx MCP helper.
- `main(argv)` — CLI entry point used by pyqual pipeline stages.
- `run_case()` — —
- `hello()` — —
- `add()` — —
- `print()` — —
- `generate_readme()` — —
- `parse_todo_items()` — —
- `group_similar_issues()` — —
- `run_parallel_fix()` — —
- `register_bulk_commands()` — —
- `main()` — —
- `classify_with_llm()` — —
- `generate_pyqual_yaml()` — —
- `bulk_init()` — —
- `query_nfo_db()` — —
- `row_to_event_dict()` — —
- `format_log_entry_row()` — —
- `code_health_summary()` — —
- `run_hadolint()` — —
- `run_trivy_scan()` — —
- `get_image_info()` — —
- `docker_security_check()` — —
- `build_report()` — —
- `apply_patch()` — —
- `add_docstring()` — —
- `parse_and_apply_suggestions()` — —
- `get_todo_batch()` — —
- `mark_completed_todos()` — —
- `run_tool()` — —
- `git_commit_and_push()` — —
- `parse_args()` — —
- `gates()` — —
- `validate()` — —
- `fix_config()` — —
- `status()` — —
- `report()` — —
- `get_outdated_packages()` — —
- `get_dependency_tree()` — —
- `check_requirements()` — —
- `deps_health_check()` — —
- `lint_summary()` — —
- `Overview()` — —
- `totalRepos()` — —
- `passingRepos()` — —
- `failingRepos()` — —
- `avgCoverage()` — —
- `collect_project_metadata()` — —
- `collect_all_metrics()` — —
- `evaluate_gates()` — —
- `generate_report()` — —
- `build_badges()` — —
- `update_readme_badges()` — —
- `run()` — —
- `mcp_fix()` — —
- `mcp_refactor()` — —
- `mcp_service()` — —
- `tune_thresholds()` — —
- `tune_show()` — —
- `run_git_command()` — —
- `git_status()` — —
- `git_commit()` — —
- `git_push()` — —
- `git_add()` — —
- `scan_for_secrets()` — —
- `preflight_push_check()` — —
- `run_project()` — —
- `App()` — —
- `loadRepositories()` — —
- `repos()` — —
- `handleRepositorySelect()` — —
- `runs()` — —
- `RepositoryCard()` — —
- `lastRun()` — —
- `statusColor()` — —
- `statusIcon()` — —
- `API_BASE_URL()` — —
- `GITHUB_TOKEN()` — —
- `loadConfig()` — —
- `response()` — —
- `fetchRepositories()` — —
- `config()` — —
- `repositories()` — —
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
- `parse_kwargs()` — —
- `get_last_run()` — —
- `generate_mermaid_diagram()` — —
- `generate_ascii_diagram()` — —
- `generate_metrics_table()` — —
- `generate_stage_details()` — —
- `get_changed_files()` — —
- `get_diff_content()` — —
- `evaluate_with_llm()` — —
- `register_observe_commands()` — —
- `count_todo_items()` — —
- `extract_pytest_stage_summary()` — —
- `extract_lint_stage_summary()` — —
- `extract_prefact_stage_summary()` — —
- `extract_code2llm_stage_summary()` — —
- `extract_validation_stage_summary()` — —
- `extract_fix_stage_summary()` — —
- `extract_mypy_stage_summary()` — —
- `extract_bandit_stage_summary()` — —
- `extract_stage_summary()` — —
- `enrich_from_artifacts()` — —
- `infer_fix_result()` — —
- `build_run_summary()` — —
- `format_run_summary()` — —
- `get_last_error_line()` — —
- `git_status_cmd()` — —
- `git_add_cmd()` — —
- `git_scan_cmd()` — —
- `git_commit_cmd()` — —
- `git_push_cmd()` — —
- `plugin_list()` — —
- `plugin_search()` — —
- `plugin_info()` — —
- `plugin_add()` — —
- `plugin_remove()` — —
- `plugin_validate()` — —
- `plugin_unknown_action()` — —
- `check_readme()` — —
- `run_interrogate()` — —
- `check_links()` — —
- `docs_quality_summary()` — —
- `run_bandit_check()` — —
- `run_pip_audit()` — —
- `run_detect_secrets()` — —
- `security_summary()` — —
- `error_domain()` — —
- `discover_projects()` — —
- `build_dashboard_table()` — —
- `bulk_run()` — —
- `load_history()` — —
- `save_snapshot()` — —
- `detect_regressions()` — —
- `print_trend_report()` — —
- `load_config()` — —
- `validate_config()` — —
- `create_default_config()` — —
- `run_pipeline()` — —
- `check_gates()` — —
- `dry_run()` — —
- `run_stage()` — —
- `get_tool_command()` — —
- `format_result_summary()` — —
- `export_results_json()` — —
- `shell_check()` — —
- `analyze_yaml_syntax()` — —
- `fix_yaml_file()` — —
- `check_all()` — —
- `collect_fingerprint()` — —
- `validate_release_state()` — —
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
- `compute_composite_score()` — —
- `run_composite_check()` — —
- `sync_planfile_tickets()` — —
- `sync_todo_tickets()` — —
- `sync_github_tickets()` — —
- `sync_all_tickets()` — —
- `sync_from_gates()` — —
- `attack_check()` — —
- `attack_merge()` — —
- `auto_merge_pr()` — —
- `get_preset()` — —
- `list_presets()` — —
- `is_builtin()` — —
- `register_preset()` — —
- `load_user_tools()` — —
- `preset_to_dict()` — —
- `dump_presets_json()` — —
- `register_custom_tools_from_yaml()` — —
- `load_entry_point_presets()` — —
- `resolve_stage_command()` — —
- `check_skip_conditions()` — —
- `tune_thresholds_cmd()` — —
- `setup_logging()` — —
- `plugin()` — —
- `coverage_summary()` — —
- `sync_from_cli()` — —
- `tickets_from_gate_failures()` — —
- `normalize_stage_name()` — —
- `is_fix_stage_name()` — —
- `is_verify_stage_name()` — —
- `is_delivery_stage_name()` — —
- `get_stage_when_default()` — —
- `init()` — —
- `profiles()` — —
- `tickets_sync()` — —
- `tickets_todo()` — —
- `tickets_github()` — —
- `tickets_all()` — —
- `tickets_fetch()` — —
- `tickets_comment()` — —
- `MetricsTrendChart()` — —
- `data()` — —
- `MetricsChart()` — —
- `days()` — —
- `today()` — —
- `date()` — —
- `baseCoverage()` — —
- `variation()` — —
- `get_db_path()` — —
- `read_summary_json()` — —
- `query_pipeline_db()` — —
- `safe_parse()` — —
- `get_projects()` — —
- `get_latest_run()` — —
- `get_project_runs()` — —
- `get_metric_history()` — —
- `get_stage_performance()` — —
- `get_gate_status()` — —
- `get_project_summary()` — —
- `ingest_results()` — —
- `health_check()` — —
- `fetch_github_tasks()` — —
- `save_tasks_to_todo()` — —
- `save_tasks_to_json()` — —
- `build_parser()` — —
- `get_available_tools()` — —
- `doctor()` — —
- `tools()` — —
- `get_available_plugins()` — —
- `install_plugin_config()` — —
- `cmd_check()` — —
- `cmd_merge()` — —
- `StagesChart()` — —
- `run_quality_check()` — —
- `run_with_callbacks()` — —
- `check_prerequisites()` — —
- `run_shell_command_example()` — —
- `run_single_stage()` — —
- `preview_pipeline()` — —
- `quick_gate_check()` — —
- `example_helper_function()` — —
- `Settings()` — —
- `get_profile()` — —
- `list_profiles()` — —
- `create_app()` — —
- `run_server()` — —
- `print()` — —
- `check_tool()` — —
- `run_case()` — —
- `hello()` — —
- `add()` — —
- `collect()` — —
- `Questions()` — —
- `exit()` — —
- `generate_readme()` — —
- `total()` — —
- `detect_project_facts()` — —
- `test_github_connection()` — —
- `test_todo_creation()` — —
- `test_default_yaml_parses()` — —
- `test_gate_config_from_dict()` — —
- `test_gate_check_pass()` — —
- `test_gate_check_fail()` — —
- `test_gate_check_missing_metric()` — —
- `test_gate_set_from_toon()` — —
- `test_gate_set_from_vallm()` — —
- `test_gate_set_from_coverage()` — —
- `test_pipeline_dry_run()` — —
- `test_pipeline_with_passing_gates()` — —
- `test_pipeline_runs_fix_chain_when_gates_fail()` — —
- `test_timeout_zero_means_no_timeout()` — —
- `test_tool_preset_stage_config()` — —
- `test_tool_preset_dry_run()` — —
- `test_tool_preset_resolution()` — —
- `test_stage_requires_run_or_tool()` — —
- `test_stage_rejects_both_run_and_tool()` — —
- `test_stage_rejects_unknown_tool()` — —
- `test_pipeline_writes_nfo_sqlite_log()` — —
- `test_stage_result_preserves_original_returncode()` — —
- `test_default_tools_json_loads_all_presets()` — —
- `test_preset_from_dict()` — —
- `test_load_user_tools_from_json()` — —
- `test_load_user_tools_no_file()` — —
- `test_dump_presets_json()` — —
- `test_register_custom_preset()` — —
- `test_custom_tools_from_yaml()` — —
- `make_project()` — —
- `write_config()` — —
- `workspace()` — —
- `anyio_backend()` — —
- `test_llx_mcp_plugin_collects_metrics()` — —
- `test_load_issue_source_parses_todo_md()` — —
- `test_llx_mcp_plugin_config_example_contains_stage()` — —
- `test_run_llx_fix_workflow_uses_todo_md_fallback()` — —
- `test_run_llx_refactor_workflow_uses_refactor_prompt()` — —
- `test_mcp_fix_cli_invokes_workflow()` — —
- `test_mcp_refactor_cli_invokes_workflow()` — —
- `test_mcp_service_cli_shows_friendly_error()` — —
- `test_persistent_mcp_service_exposes_health_and_metrics()` — —
- `test_build_fix_prompt_uses_issue_summary()` — —
- `pipeline()` — —
- `test_placeholder()` — —
- `test_import()` — —
- `test_llm_exports_use_llx_when_available()` — —
- `test_gate_set_reads_project_toon_artifacts()` — —
- `test_gate_set_derives_completion_rate()` — —
- `test_collect_all_metrics_reads_toon_and_coverage()` — —
- `test_collect_all_metrics_empty_dir()` — —
- `test_generate_report_creates_yaml()` — —
- `test_generate_report_gates_pass()` — —
- `test_generate_report_gates_fail()` — —
- `test_build_badges_pass()` — —
- `test_build_badges_fail()` — —
- `test_build_badges_empty_metrics_no_project_meta()` — —
- `test_build_badges_with_project_meta()` — —
- `test_build_badges_gates_ratio()` — —
- `test_project_badges_all_fields()` — —
- `test_project_badges_empty_meta()` — —
- `test_project_badges_ai_cost_colors()` — —
- `test_quality_badges_with_extra_metrics()` — —
- `test_read_costs_from_json()` — —
- `test_read_costs_empty_dir()` — —
- `test_update_readme_inserts_markers_after_existing_badges()` — —
- `test_update_readme_replaces_existing_markers()` — —
- `test_update_readme_no_change_when_identical()` — —
- `test_update_readme_no_file()` — —
- `test_update_readme_inserts_at_top_when_no_badges()` — —
- `test_run_integration()` — —
- `test_run_integration_with_costs()` — —
- `test_quality_badges_no_metrics()` — —
- `test_read_costs_data_missing_file()` — —
- `test_update_readme_badges_noop_markers()` — —
- `test_sync_todo_tickets_uses_planfile_markdown_backend()` — —
- `test_sync_github_tickets_uses_planfile_github_backend()` — —
- `test_sync_all_tickets_calls_both_backends()` — —
- `test_tickets_todo_cli_invokes_sync_helper()` — —
- `test_run_on_fail_create_ticket_syncs_todo_tickets()` — —
- `test_run_report_includes_todo_and_fix_summary()` — —
- `test_temp_dir_creation()` — —
- `detect_project_facts(workdir)` — Scan project directory and return facts for LLM-based config repair.


## Project Structure

📄 `.aider.chat.history` (1 functions)
📄 `.assistant.REQUEST_ADD_FILES`
📄 `.planfile_analysis.analysis_summary`
📄 `CHANGELOG`
📄 `Makefile`
📄 `README` (6 functions)
📄 `REQUEST_ADD_FILES`
📄 `REQUEST_EDIT_FILES`
📄 `REQUEST_FOR_FILES`
📄 `SUGGESTED_COMMANDS`
📄 `SUMD` (664 functions, 2 classes)
📄 `SUMR` (120 functions, 2 classes)
📄 `TODO`
📄 `TODO_mocked`
📄 `Taskfile` (2 functions)
📄 `code2llm_output.README`
📄 `code2llm_output.analysis.toon`
📄 `code2llm_output.context`
📄 `code2llm_output.evolution.toon`
📄 `dashboard.README`
📄 `dashboard.api.main` (13 functions)
📄 `dashboard.api.requirements`
📄 `dashboard.config.repos.example`
📄 `dashboard.constants`
📄 `dashboard.package`
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
📄 `dashboard.tsconfig`
📄 `dashboard.tsconfig.node`
📄 `dashboard.vite.config`
📄 `dashboard.vitest.config`
📄 `docs.README` (1 functions)
📄 `docs.ai-fix-tools`
📄 `docs.api` (16 functions, 1 classes)
📄 `docs.ci-dashboard-integration`
📄 `docs.configuration`
📄 `docs.integrations` (2 functions, 1 classes)
📄 `docs.logs-and-data` (2 functions)
📄 `docs.quickstart`
📄 `docs.runtime-errors`
📄 `examples.README`
📄 `examples.basic.README` (7 functions)
📄 `examples.basic.check_gates`
📄 `examples.basic.minimal`
📄 `examples.basic.pyqual`
📄 `examples.basic.run_pipeline`
📄 `examples.basic.sync_if_fail`
📄 `examples.custom_gates.README`
📄 `examples.custom_gates.composite_gates` (3 functions)
📄 `examples.custom_gates.composite_simple`
📄 `examples.custom_gates.dynamic_thresholds` (1 functions)
📄 `examples.custom_gates.metric_history` (5 functions)
📄 `examples.custom_gates.pyqual`
📄 `examples.custom_plugins.README` (1 functions, 1 classes)
📄 `examples.custom_plugins.code_health_collector` (2 functions, 1 classes)
📄 `examples.custom_plugins.performance_collector` (2 functions, 1 classes)
📄 `examples.custom_plugins.pyqual`
📄 `examples.github-actions.README`
📄 `examples.gitlab-ci.README`
📄 `examples.integration_example` (7 functions)
📄 `examples.linters.README`
📄 `examples.linters.pyqual`
📄 `examples.llm_fix.Dockerfile`
📄 `examples.llm_fix.README`
📄 `examples.llm_fix.docker-compose`
📄 `examples.llm_fix.project.README`
📄 `examples.llm_fix.project.analysis.toon`
📄 `examples.llm_fix.project.context`
📄 `examples.llm_fix.project.evolution.toon`
📄 `examples.llm_fix.project.map.toon`
📄 `examples.llm_fix.project.project.toon`
📄 `examples.llm_fix.project.prompt`
📄 `examples.llm_fix.project.validation.toon`
📄 `examples.llm_fix.pyqual`
📄 `examples.llx.README`
📄 `examples.llx.demo` (1 functions)
📄 `examples.llx.project.README`
📄 `examples.llx.project.analysis.toon`
📄 `examples.llx.project.context`
📄 `examples.llx.project.evolution.toon`
📄 `examples.llx.project.map.toon`
📄 `examples.llx.project.project.toon`
📄 `examples.llx.project.prompt`
📄 `examples.llx.project.validation.toon`
📄 `examples.llx.pyqual-llx`
📄 `examples.monorepo.README`
📄 `examples.multi_gate_pipeline.CHANGELOG`
📄 `examples.multi_gate_pipeline.README`
📄 `examples.multi_gate_pipeline.TODO`
📄 `examples.multi_gate_pipeline.project.README`
📄 `examples.multi_gate_pipeline.project.analysis.toon`
📄 `examples.multi_gate_pipeline.project.context`
📄 `examples.multi_gate_pipeline.project.evolution.toon`
📄 `examples.multi_gate_pipeline.project.map.toon`
📄 `examples.multi_gate_pipeline.project.project.toon`
📄 `examples.multi_gate_pipeline.project.prompt`
📄 `examples.multi_gate_pipeline.project.validation.toon`
📄 `examples.multi_gate_pipeline.pyqual`
📄 `examples.multi_gate_pipeline.run_pipeline` (2 functions)
📄 `examples.project_analysis.docs.README` (1 functions)
📄 `examples.project_analysis.project.README`
📄 `examples.project_analysis.project.analysis.toon`
📄 `examples.project_analysis.project.context`
📄 `examples.project_analysis.project.duplication.toon`
📄 `examples.project_analysis.project.evolution.toon`
📄 `examples.project_analysis.project.map.toon`
📄 `examples.project_analysis.project.project.toon`
📄 `examples.project_analysis.project.prompt`
📄 `examples.project_analysis.project.validation.toon`
📄 `examples.project_analysis.pyqual`
📄 `examples.python-flat.README`
📄 `examples.python-package.README`
📄 `examples.security-profile.README`
📄 `examples.security-profile.pyqual`
📄 `examples.security.README`
📄 `examples.security.pyqual`
📄 `examples.ticket_backends.README`
📄 `examples.ticket_backends.all-backends`
📄 `examples.ticket_backends.both-backends`
📄 `examples.ticket_backends.github-only`
📄 `examples.ticket_backends.markdown-only`
📄 `examples.ticket_workflow.README`
📄 `examples.ticket_workflow.project.README`
📄 `examples.ticket_workflow.project.analysis.toon`
📄 `examples.ticket_workflow.project.context`
📄 `examples.ticket_workflow.project.evolution.toon`
📄 `examples.ticket_workflow.project.map.toon`
📄 `examples.ticket_workflow.project.project.toon`
📄 `examples.ticket_workflow.project.prompt`
📄 `examples.ticket_workflow.pyqual`
📄 `examples.ticket_workflow.sync_tickets` (3 functions)
📄 `goal`
📄 `integration.Dockerfile`
📄 `integration.run_docker_matrix`
📄 `integration.run_matrix` (8 functions)
📄 `integrations.planfile`
📄 `planfile`
📄 `prefact`
📄 `project`
📄 `project.README`
📄 `project.analysis.toon`
📄 `project.calls`
📄 `project.calls.toon`
📄 `project.context`
📄 `project.dashboard_pyqual_examples.analysis.toon`
📄 `project.dashboard_pyqual_examples.context`
📄 `project.dashboard_pyqual_examples.evolution.toon`
📄 `project.duplication.toon`
📄 `project.evolution.toon`
📄 `project.map.toon` (1347 functions)
📄 `project.planfile`
📄 `project.project.toon`
📄 `project.prompt`
📄 `project.root.analysis.toon`
📄 `project.root.context`
📄 `project.root.evolution.toon`
📄 `project.validation.toon`
📄 `project.verify.validation.toon`
📄 `pyproject`
📦 `pyqual`
📄 `pyqual.__main__`
📄 `pyqual._gate_collectors` (28 functions)
📄 `pyqual.analysis` (1 functions)
📄 `pyqual.api` (15 functions, 1 classes)
📄 `pyqual.auto_closer` (7 functions)
📄 `pyqual.bulk.models` (2 classes)
📄 `pyqual.bulk.orchestrator` (5 functions, 1 classes)
📄 `pyqual.bulk.parser` (3 functions)
📄 `pyqual.bulk.runner` (1 functions)
📄 `pyqual.bulk_init` (15 functions, 1 classes)
📄 `pyqual.bulk_init_classify` (1 functions, 1 classes)
📄 `pyqual.bulk_init_fingerprint` (9 functions, 1 classes)
📄 `pyqual.bulk_run`
📦 `pyqual.cli`
📄 `pyqual.cli.cmd_config` (7 functions)
📄 `pyqual.cli.cmd_git` (8 functions)
📄 `pyqual.cli.cmd_info` (2 functions)
📄 `pyqual.cli.cmd_init` (2 functions)
📄 `pyqual.cli.cmd_mcp` (4 functions)
📄 `pyqual.cli.cmd_plugin` (1 functions)
📄 `pyqual.cli.cmd_run` (12 functions)
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
📄 `pyqual.default_tools`
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
📄 `pyqual.pipeline` (31 functions, 1 classes)
📄 `pyqual.pipeline_protocols` (6 functions, 6 classes)
📄 `pyqual.pipeline_results` (3 classes)
📦 `pyqual.plugins` (3 functions)
📄 `pyqual.plugins._base` (7 functions, 3 classes)
📦 `pyqual.plugins.attack`
📄 `pyqual.plugins.attack.README`
📄 `pyqual.plugins.attack.__main__` (4 functions)
📄 `pyqual.plugins.attack.main` (10 functions, 1 classes)
📄 `pyqual.plugins.attack.test` (13 functions, 5 classes)
📄 `pyqual.plugins.builtin` (14 functions, 7 classes)
📄 `pyqual.plugins.cli_helpers` (7 functions)
📦 `pyqual.plugins.code_health`
📄 `pyqual.plugins.code_health.main` (6 functions, 1 classes)
📦 `pyqual.plugins.coverage`
📄 `pyqual.plugins.coverage.main` (2 functions, 1 classes)
📦 `pyqual.plugins.deps`
📄 `pyqual.plugins.deps.README` (8 functions)
📄 `pyqual.plugins.deps.main` (11 functions, 1 classes)
📄 `pyqual.plugins.deps.test` (14 functions, 5 classes)
📦 `pyqual.plugins.docker`
📄 `pyqual.plugins.docker.README` (4 functions)
📄 `pyqual.plugins.docker.main` (13 functions, 1 classes)
📄 `pyqual.plugins.docker.test` (11 functions, 4 classes)
📦 `pyqual.plugins.docs`
📄 `pyqual.plugins.docs.README` (8 functions)
📄 `pyqual.plugins.docs.main` (12 functions, 1 classes)
📄 `pyqual.plugins.docs.test` (12 functions, 5 classes)
📦 `pyqual.plugins.documentation`
📄 `pyqual.plugins.documentation.README` (2 functions)
📄 `pyqual.plugins.documentation.main` (12 functions, 1 classes)
📄 `pyqual.plugins.documentation.test` (9 functions, 1 classes)
📦 `pyqual.plugins.example_plugin`
📄 `pyqual.plugins.example_plugin.README`
📄 `pyqual.plugins.example_plugin.main` (3 functions, 1 classes)
📄 `pyqual.plugins.example_plugin.test` (7 functions, 2 classes)
📦 `pyqual.plugins.git`
📄 `pyqual.plugins.git.README` (3 functions)
📄 `pyqual.plugins.git.git_command` (1 functions)
📄 `pyqual.plugins.git.main` (27 functions, 1 classes)
📄 `pyqual.plugins.git.status` (3 functions)
📄 `pyqual.plugins.git.test` (24 functions, 6 classes)
📦 `pyqual.plugins.lint`
📄 `pyqual.plugins.lint.main` (6 functions, 1 classes)
📦 `pyqual.plugins.security`
📄 `pyqual.plugins.security.README` (3 functions)
📄 `pyqual.plugins.security.main` (11 functions, 1 classes)
📄 `pyqual.plugins.security.test` (13 functions, 5 classes)
📄 `pyqual.profiles` (2 functions, 1 classes)
📄 `pyqual.release_check` (2 functions)
📄 `pyqual.report` (19 functions)
📄 `pyqual.report_generator` (15 functions, 2 classes)
📄 `pyqual.run_parallel_fix` (12 functions)
📄 `pyqual.setup_deps` (5 functions, 1 classes)
📄 `pyqual.stage_names` (5 functions)
📄 `pyqual.tickets` (7 functions)
📄 `pyqual.tools` (15 functions, 1 classes)
📦 `pyqual.validation`
📄 `pyqual.validation.config_check` (7 functions)
📄 `pyqual.validation.errors` (4 functions, 4 classes)
📄 `pyqual.validation.project` (2 functions)
📄 `pyqual.validation.release` (12 functions)
📄 `pyqual.validation.schema` (2 functions, 2 classes)
📄 `pyqual.yaml_fixer` (12 functions, 3 classes)
📄 `renovate`
📄 `run_analysis` (2 functions)
📄 `testql-scenarios.generated-api-smoke.testql.toon`
📄 `testql-scenarios.generated-cli-tests.testql.toon`
📄 `testql-scenarios.generated-from-pytests.testql.toon`
📄 `tree`

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0- litellm >=1.0- python-dotenv >=1.0- nfo >=0.2.13

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Pyqual Bot <pyqual-bot@semcod.github.io>
- Tom Sapletta <tom-sapletta-com@users.noreply.github.com>

We welcome contributions! Open an issue or pull request to get started.
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

- 📚 [API Reference](./docs/api.md) — Complete API documentation
- 🔧 [Configuration](./docs/configuration.md) — Configuration reference
- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `docs/api.md` | Complete API documentation | [View](./docs/api.md) |
| `docs/configuration.md` | Configuration reference | [View](./docs/configuration.md) |
| `examples` | Usage examples and code samples | [View](./examples) |

<!-- code2docs:end -->