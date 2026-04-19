# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/pyqual
- **Primary Language**: python
- **Languages**: python: 122, typescript: 12, shell: 5, javascript: 2
- **Analysis Mode**: static
- **Total Functions**: 755
- **Total Classes**: 118
- **Modules**: 141
- **Entry Points**: 466

## Architecture by Module

### pyqual._gate_collectors
- **Functions**: 27
- **File**: `_gate_collectors.py`

### pyqual.pipeline
- **Functions**: 26
- **Classes**: 1
- **File**: `pipeline.py`

### pyqual.cli_run_helpers
- **Functions**: 24
- **File**: `cli_run_helpers.py`

### pyqual.plugins.git.test
- **Functions**: 24
- **Classes**: 6
- **File**: `test.py`

### dashboard.src.api
- **Functions**: 23
- **File**: `index.ts`

### pyqual.plugins.git.main
- **Functions**: 21
- **Classes**: 1
- **File**: `main.py`

### pyqual.report
- **Functions**: 19
- **File**: `report.py`

### pyqual.github_actions
- **Functions**: 16
- **Classes**: 2
- **File**: `github_actions.py`

### pyqual.tools
- **Functions**: 15
- **Classes**: 1
- **File**: `tools.py`

### pyqual.api
- **Functions**: 15
- **Classes**: 1
- **File**: `api.py`

### pyqual.bulk_init
- **Functions**: 15
- **Classes**: 1
- **File**: `bulk_init.py`

### pyqual.cli_observe
- **Functions**: 15
- **File**: `cli_observe.py`

### pyqual.report_generator
- **Functions**: 14
- **Classes**: 2
- **File**: `report_generator.py`

### pyqual.plugins.builtin
- **Functions**: 14
- **Classes**: 7
- **File**: `builtin.py`

### pyqual.plugins.deps.test
- **Functions**: 14
- **Classes**: 5
- **File**: `test.py`

### dashboard.src.components.RepositoryDetail
- **Functions**: 13
- **Classes**: 1
- **File**: `RepositoryDetail.tsx`

### dashboard.api.main
- **Functions**: 13
- **File**: `main.py`

### pyqual.plugins.security.test
- **Functions**: 13
- **Classes**: 5
- **File**: `test.py`

### pyqual.plugins.docker.main
- **Functions**: 13
- **Classes**: 1
- **File**: `main.py`

### pyqual.plugins.attack.test
- **Functions**: 13
- **Classes**: 5
- **File**: `test.py`

## Key Entry Points

Main execution flows into the system:

### pyqual.cli.cmd_run.run
> Execute pipeline loop until quality gates pass.

Output is streamed as YAML to stdout as each stage completes.
Diagnostic messages go to stderr.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, pyqual.cli.main.setup_logging

### pyqual.cli.cmd_config.fix_config
> Use LLM to auto-repair pyqual.yaml based on project structure.

Scans the project (language, available tools, test framework) and asks the
LLM to prod
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, None.resolve, pyqual.api.validate_config, pyqual.validation.project.detect_project_facts

### pyqual.cli.cmd_git.git_scan_cmd
> Scan files for secrets before push.

Runs multiple scanners in order:
1. trufflehog (if available) - most comprehensive
2. gitleaks (if available) - f
- **Calls**: git_app.command, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.cli_log_helpers.format_log_entry_row
> Return (ts, event_name, name, status, details) for one log entry.
- **Calls**: entry.get, entry.get, None.replace, entry.get, entry.get, None.join, entry.get, entry.get

### pyqual.run_parallel_fix.main
> Run parallel fix on TODO.md items - configurable batch size with git push.
- **Calls**: pyqual.run_parallel_fix.parse_args, Path.cwd, pyqual.run_parallel_fix.get_todo_batch, print, enumerate, pyqual.run_parallel_fix._setup_batch, print, os.environ.get

### examples.multi_gate_pipeline.run_pipeline.main
- **Calls**: Path, PyqualConfig.load, Pipeline, print, print, print, print, print

### examples.custom_gates.metric_history.main
> Run the metric history self-test with synthetic history.
- **Calls**: tempfile.TemporaryDirectory, Path, pyqual_dir.mkdir, print, print, print, print, sorted

### pyqual.config.PyqualConfig._parse
- **Calls**: raw.get, pyqual.tools.load_entry_point_presets, pyqual.tools.load_user_tools, pipeline.get, pipeline.get, pipeline.get, cls._validate_stages, cls

### pyqual.auto_closer.main
- **Calls**: Path.cwd, gates_info.get, gates_info.get, print, PlanfileStore, store.list_tickets, print, pyqual.auto_closer.get_changed_files

### pyqual.plugins.docs.main.DocsCollector._collect_readme_metrics
> Extract README quality metrics.
- **Calls**: readme_json_path.exists, readme_path.exists, self._set_zero_readme, json.loads, float, float, float, readme_path.read_text

### pyqual.cli_observe.register_observe_commands
> Register logs, watch, and history commands onto *app*.
- **Calls**: app.command, app.command, app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.cli.cmd_git.git_commit_cmd
> Create a git commit.
- **Calls**: git_app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, pyqual.plugins.git.main.git_commit, result.get

### pyqual.cli.cmd_config.validate
> Validate pyqual.yaml without running the pipeline.

Checks for:
- YAML parse errors (with line/column positions)
- Unknown or missing tool binaries
- 
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, pyqual.api.validate_config, console.print, console.print

### pyqual.plugins.lint.main.LintCollector._collect_pylint
> Extract pylint score and error counts.
- **Calls**: isinstance, p.exists, json.loads, float, float, float, isinstance, p.read_text

### pyqual.cli.cmd_tickets.tickets_sync
> Sync tickets from gate failures or explicitly.

Examples:
    pyqual tickets sync --from-gates              # Check gates, sync if fail
    pyqual tic
- **Calls**: tickets_app.command, typer.Option, typer.Option, typer.Option, typer.Option, Path, console.print, console.print

### pyqual.pipeline.Pipeline._execute_streaming
> Execute stage with real-time output streaming via Popen.
- **Calls**: subprocess.Popen, proc.wait, StageResult, StageResult, select.select, fd.readline, None.append, None.join

### pyqual.cli.cmd_git.git_status_cmd
> Show git repository status.
- **Calls**: git_app.command, typer.Option, typer.Option, pyqual.plugins.git.status.git_status, pyqual.cli.cmd_git._print_file_list, pyqual.cli.cmd_git._print_file_list, pyqual.cli.cmd_git._print_file_list, console.print

### pyqual.cli.cmd_config.status
> Show current metrics and pipeline config.
- **Calls**: app.command, typer.Option, typer.Option, PyqualConfig.load, GateSet, gate_set._collect_metrics, console.print, console.print

### pyqual.plugins.lint.main.LintCollector._collect_ruff
> Extract ruff linter metrics.
- **Calls**: p.exists, json.loads, isinstance, p.read_text, len, sum, sum, float

### pyqual.cli.cmd_init.init
> Create pyqual.yaml with sensible defaults.

Use --profile for a minimal config based on a built-in profile:

    pyqual init --profile python         
- **Calls**: app.command, typer.Argument, typer.Option, target.exists, None.mkdir, console.print, console.print, Path

### pyqual.cli.main.tune_thresholds_cmd
> Auto-tune quality gate thresholds based on current metrics.

Analyzes collected metrics and suggests optimal thresholds.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, console.print, pyqual.cli.main._load_latest_metrics_for_tune, pyqual.cli.main._calculate_thresholds_for_tune

### pyqual.custom_fix.parse_and_apply_suggestions
> Parse LLM suggestions and apply patches.
- **Calls**: re.findall, Path, print, re.search, file_path.exists, print, file_path.read_text, re.search

### pyqual.cli_bulk_cmds.register_bulk_commands
> Register bulk-init and bulk-run commands onto *app*.
- **Calls**: app.command, app.command, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.plugins.lint.main.LintCollector._collect_flake8
> Extract flake8 violation count.
- **Calls**: p.exists, json.loads, isinstance, p.read_text, len, sum, sum, float

### pyqual.cli.cmd_config.gates
> Check quality gates without running stages.
- **Calls**: app.command, typer.Option, typer.Option, PyqualConfig.load, GateSet, gate_set.check_all, Table, table.add_column

### pyqual.plugins.documentation.main.DocumentationCollector._check_docs_folder
> Check docs/ folder presence and content.
- **Calls**: any, next, float, any, list, len, any, p.exists

### pyqual.plugins.git.main.GitCollector.collect
> Collect git metrics from .pyqual/git_*.json artifacts.
- **Calls**: status_path.exists, push_path.exists, commit_path.exists, scan_path.exists, preflight_path.exists, json.loads, self._collect_status_metrics, json.loads

### pyqual.cli.cmd_info.tools
> List built-in tool presets for pipeline stages.
- **Calls**: app.command, Table, table.add_column, table.add_column, table.add_column, table.add_column, table.add_column, sorted

### pyqual.cli.cmd_tune.tune_thresholds
> Automatically tune quality gate thresholds to match current metrics.

Analyzes collected metrics and suggests optimal thresholds that will
result in a
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, console.print, PyqualConfig.load, pyqual.cli.cmd_tune._load_latest_metrics

### pyqual.plugins.documentation.main.DocumentationCollector.collect
> Collect all documentation metrics.
- **Calls**: result.update, result.update, result.update, result.update, result.update, result.update, sum, self._check_required_files

## Process Flows

Key execution flows identified:

### Flow 1: run
```
run [pyqual.cli.cmd_run]
```

### Flow 2: fix_config
```
fix_config [pyqual.cli.cmd_config]
```

### Flow 3: git_scan_cmd
```
git_scan_cmd [pyqual.cli.cmd_git]
```

### Flow 4: format_log_entry_row
```
format_log_entry_row [pyqual.cli_log_helpers]
```

### Flow 5: main
```
main [pyqual.run_parallel_fix]
  └─> parse_args
  └─> get_todo_batch
```

### Flow 6: _parse
```
_parse [pyqual.config.PyqualConfig]
  └─ →> load_entry_point_presets
  └─ →> load_user_tools
      └─> _load_json_presets
```

### Flow 7: _collect_readme_metrics
```
_collect_readme_metrics [pyqual.plugins.docs.main.DocsCollector]
```

### Flow 8: register_observe_commands
```
register_observe_commands [pyqual.cli_observe]
```

### Flow 9: git_commit_cmd
```
git_commit_cmd [pyqual.cli.cmd_git]
```

### Flow 10: validate
```
validate [pyqual.cli.cmd_config]
```

## Key Classes

### pyqual.pipeline.Pipeline
> Execute pipeline stages in a loop until quality gates pass.
- **Methods**: 26
- **Key Methods**: pyqual.pipeline.Pipeline.__init__, pyqual.pipeline.Pipeline.run, pyqual.pipeline.Pipeline.check_gates, pyqual.pipeline.Pipeline._run_iteration, pyqual.pipeline.Pipeline._iteration_stagnated, pyqual.pipeline.Pipeline._should_run_stage, pyqual.pipeline.Pipeline._resolve_tool_stage, pyqual.pipeline.Pipeline._resolve_env, pyqual.pipeline.Pipeline._check_optional_binary, pyqual.pipeline.Pipeline._make_skipped_result

### pyqual.github_actions.GitHubActionsReporter
> Reports pyqual results to GitHub Actions and PRs.
- **Methods**: 14
- **Key Methods**: pyqual.github_actions.GitHubActionsReporter.__init__, pyqual.github_actions.GitHubActionsReporter.create_issue, pyqual.github_actions.GitHubActionsReporter.ensure_issue_exists, pyqual.github_actions.GitHubActionsReporter.is_running_in_github_actions, pyqual.github_actions.GitHubActionsReporter.get_pr_number, pyqual.github_actions.GitHubActionsReporter.fetch_issues, pyqual.github_actions.GitHubActionsReporter.fetch_pull_requests, pyqual.github_actions.GitHubActionsReporter.post_pr_comment, pyqual.github_actions.GitHubActionsReporter.post_issue_comment, pyqual.github_actions.GitHubActionsReporter.close_issue

### pyqual.plugins.documentation.main.DocumentationCollector
> Documentation completeness and quality metrics.

Measures:
- Required files presence (readme, licens
- **Methods**: 11
- **Key Methods**: pyqual.plugins.documentation.main.DocumentationCollector._find_file, pyqual.plugins.documentation.main.DocumentationCollector._check_file_exists, pyqual.plugins.documentation.main.DocumentationCollector._read_pyproject, pyqual.plugins.documentation.main.DocumentationCollector._parse_pyproject_fallback, pyqual.plugins.documentation.main.DocumentationCollector._check_pyproject_metadata, pyqual.plugins.documentation.main.DocumentationCollector._analyze_readme, pyqual.plugins.documentation.main.DocumentationCollector._check_docs_folder, pyqual.plugins.documentation.main.DocumentationCollector._check_required_files, pyqual.plugins.documentation.main.DocumentationCollector._get_docstring_coverage, pyqual.plugins.documentation.main.DocumentationCollector._check_license_type
- **Inherits**: MetricCollector

### pyqual.plugins.docker.main.DockerCollector
> Docker security and quality metrics collector.
- **Methods**: 9
- **Key Methods**: pyqual.plugins.docker.main.DockerCollector.collect, pyqual.plugins.docker.main.DockerCollector._collect_trivy, pyqual.plugins.docker.main.DockerCollector._count_trivy_vulns, pyqual.plugins.docker.main.DockerCollector._set_zero_trivy, pyqual.plugins.docker.main.DockerCollector._collect_hadolint, pyqual.plugins.docker.main.DockerCollector._collect_grype, pyqual.plugins.docker.main.DockerCollector._get_grype_severity, pyqual.plugins.docker.main.DockerCollector._collect_image_info, pyqual.plugins.docker.main.DockerCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.plugins.documentation.test.TestDocumentationCollector
> Test DocumentationCollector metric collection.
- **Methods**: 9
- **Key Methods**: pyqual.plugins.documentation.test.TestDocumentationCollector.test_collector_name, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collector_metadata, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collect_empty_workdir, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collect_with_readme, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collect_with_license, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collect_with_docs_folder, pyqual.plugins.documentation.test.TestDocumentationCollector.test_collect_with_pyproject, pyqual.plugins.documentation.test.TestDocumentationCollector.test_get_config_example, pyqual.plugins.documentation.test.TestDocumentationCollector.test_documentation_score_calculation

### pyqual.plugins.builtin.LlxMcpFixCollector
> Dockerized llx MCP fix/refactor workflow results.
- **Methods**: 8
- **Key Methods**: pyqual.plugins.builtin.LlxMcpFixCollector._tier_rank, pyqual.plugins.builtin.LlxMcpFixCollector._load_report, pyqual.plugins.builtin.LlxMcpFixCollector._assign_float, pyqual.plugins.builtin.LlxMcpFixCollector._count_lines, pyqual.plugins.builtin.LlxMcpFixCollector._collect_analysis_metrics, pyqual.plugins.builtin.LlxMcpFixCollector._collect_aider_metrics, pyqual.plugins.builtin.LlxMcpFixCollector.get_config_example, pyqual.plugins.builtin.LlxMcpFixCollector.collect
- **Inherits**: MetricCollector

### pyqual.plugins.security.test.TestSecurityCollector
> Test SecurityCollector metric collection.
- **Methods**: 8
- **Key Methods**: pyqual.plugins.security.test.TestSecurityCollector.test_collector_name, pyqual.plugins.security.test.TestSecurityCollector.test_collector_metadata, pyqual.plugins.security.test.TestSecurityCollector.test_collect_empty_workdir, pyqual.plugins.security.test.TestSecurityCollector.test_collect_bandit_results, pyqual.plugins.security.test.TestSecurityCollector.test_collect_audit_results, pyqual.plugins.security.test.TestSecurityCollector.test_collect_secrets_results, pyqual.plugins.security.test.TestSecurityCollector.test_collect_safety_results, pyqual.plugins.security.test.TestSecurityCollector.test_get_config_example

### pyqual.plugins.deps.test.TestDepsCollector
> Test DepsCollector metric collection.
- **Methods**: 8
- **Key Methods**: pyqual.plugins.deps.test.TestDepsCollector.test_collector_name, pyqual.plugins.deps.test.TestDepsCollector.test_collector_metadata, pyqual.plugins.deps.test.TestDepsCollector.test_collect_empty_workdir, pyqual.plugins.deps.test.TestDepsCollector.test_collect_outdated_results, pyqual.plugins.deps.test.TestDepsCollector.test_collect_deptree_results, pyqual.plugins.deps.test.TestDepsCollector.test_collect_requirements, pyqual.plugins.deps.test.TestDepsCollector.test_collect_licenses, pyqual.plugins.deps.test.TestDepsCollector.test_get_config_example

### pyqual.plugins.docs.test.TestDocsCollector
> Test DocsCollector metric collection.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.docs.test.TestDocsCollector.test_collector_name, pyqual.plugins.docs.test.TestDocsCollector.test_collector_metadata, pyqual.plugins.docs.test.TestDocsCollector.test_collect_empty_workdir, pyqual.plugins.docs.test.TestDocsCollector.test_collect_with_readme, pyqual.plugins.docs.test.TestDocsCollector.test_collect_docstring_coverage, pyqual.plugins.docs.test.TestDocsCollector.test_collect_link_results, pyqual.plugins.docs.test.TestDocsCollector.test_get_config_example

### pyqual.plugins.docs.main.DocsCollector
> Documentation quality metrics collector.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.docs.main.DocsCollector.collect, pyqual.plugins.docs.main.DocsCollector._collect_readme_metrics, pyqual.plugins.docs.main.DocsCollector._set_zero_readme, pyqual.plugins.docs.main.DocsCollector._collect_docstring_metrics, pyqual.plugins.docs.main.DocsCollector._collect_link_metrics, pyqual.plugins.docs.main.DocsCollector._collect_changelog_metrics, pyqual.plugins.docs.main.DocsCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.plugins.security.main.SecurityCollector
> Security metrics collector — aggregates findings from security scanners.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.security.main.SecurityCollector.collect, pyqual.plugins.security.main.SecurityCollector._collect_bandit, pyqual.plugins.security.main.SecurityCollector._collect_audit, pyqual.plugins.security.main.SecurityCollector._get_severity, pyqual.plugins.security.main.SecurityCollector._collect_secrets, pyqual.plugins.security.main.SecurityCollector._collect_safety, pyqual.plugins.security.main.SecurityCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.plugins.docker.test.TestDockerCollector
> Test DockerCollector metric collection.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.docker.test.TestDockerCollector.test_collector_name, pyqual.plugins.docker.test.TestDockerCollector.test_collector_metadata, pyqual.plugins.docker.test.TestDockerCollector.test_collect_empty_workdir, pyqual.plugins.docker.test.TestDockerCollector.test_collect_trivy_results, pyqual.plugins.docker.test.TestDockerCollector.test_collect_hadolint_results, pyqual.plugins.docker.test.TestDockerCollector.test_collect_grype_results, pyqual.plugins.docker.test.TestDockerCollector.test_get_config_example

### pyqual.plugins.git.test.TestSecretScanning
> Tests for secret scanning functionality.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.git.test.TestSecretScanning.temp_repo_with_secrets, pyqual.plugins.git.test.TestSecretScanning.test_scan_finds_github_token, pyqual.plugins.git.test.TestSecretScanning.test_scan_finds_aws_key, pyqual.plugins.git.test.TestSecretScanning.test_scan_skips_placeholders, pyqual.plugins.git.test.TestSecretScanning.test_false_positive_detection, pyqual.plugins.git.test.TestSecretScanning.test_provider_mapping, pyqual.plugins.git.test.TestSecretScanning.test_severity_mapping

### pyqual.plugins.git.main.GitCollector
> Git repository operations collector — status, commit, push with protection handling.
- **Methods**: 7
- **Key Methods**: pyqual.plugins.git.main.GitCollector.collect, pyqual.plugins.git.main.GitCollector._collect_scan_metrics, pyqual.plugins.git.main.GitCollector._collect_preflight_metrics, pyqual.plugins.git.main.GitCollector._collect_status_metrics, pyqual.plugins.git.main.GitCollector._collect_push_metrics, pyqual.plugins.git.main.GitCollector._collect_commit_metrics, pyqual.plugins.git.main.GitCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.gates.GateSet
> Collection of quality gates with metric collection.
- **Methods**: 6
- **Key Methods**: pyqual.gates.GateSet.__init__, pyqual.gates.GateSet._completion_rate, pyqual.gates.GateSet.check_all, pyqual.gates.GateSet.all_passed, pyqual.gates.GateSet.completion_percentage, pyqual.gates.GateSet._collect_metrics

### pyqual.plugins.deps.main.DepsCollector
> Dependency management metrics collector.
- **Methods**: 6
- **Key Methods**: pyqual.plugins.deps.main.DepsCollector.collect, pyqual.plugins.deps.main.DepsCollector._collect_outdated, pyqual.plugins.deps.main.DepsCollector._collect_deptree, pyqual.plugins.deps.main.DepsCollector._collect_requirements, pyqual.plugins.deps.main.DepsCollector._collect_licenses, pyqual.plugins.deps.main.DepsCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.plugins.example_plugin.test.TestExampleCollector
> Tests for the ExampleCollector class.
- **Methods**: 6
- **Key Methods**: pyqual.plugins.example_plugin.test.TestExampleCollector.test_collector_registration, pyqual.plugins.example_plugin.test.TestExampleCollector.test_metadata, pyqual.plugins.example_plugin.test.TestExampleCollector.test_config_example, pyqual.plugins.example_plugin.test.TestExampleCollector.test_collect_with_valid_artifact, pyqual.plugins.example_plugin.test.TestExampleCollector.test_collect_without_artifact, pyqual.plugins.example_plugin.test.TestExampleCollector.test_collect_with_invalid_json

### pyqual.config.PyqualConfig
> Full pyqual.yaml configuration.
- **Methods**: 5
- **Key Methods**: pyqual.config.PyqualConfig.load, pyqual.config.PyqualConfig.llm_model, pyqual.config.PyqualConfig._parse, pyqual.config.PyqualConfig._validate_stages, pyqual.config.PyqualConfig.default_yaml

### pyqual.fix_tools.base.FixTool
> Abstract base class for fix tools.
- **Methods**: 5
- **Key Methods**: pyqual.fix_tools.base.FixTool.__init__, pyqual.fix_tools.base.FixTool.is_available, pyqual.fix_tools.base.FixTool.get_command, pyqual.fix_tools.base.FixTool.get_timeout, pyqual.fix_tools.base.FixTool.to_config
- **Inherits**: ABC

### pyqual.plugins.code_health.main.CodeHealthCollector
> Code health metrics collector — maintainability, dead code, packaging quality.
- **Methods**: 5
- **Key Methods**: pyqual.plugins.code_health.main.CodeHealthCollector.collect, pyqual.plugins.code_health.main.CodeHealthCollector._collect_radon, pyqual.plugins.code_health.main.CodeHealthCollector._collect_vulture, pyqual.plugins.code_health.main.CodeHealthCollector._collect_pyroma, pyqual.plugins.code_health.main.CodeHealthCollector._collect_interrogate
- **Inherits**: MetricCollector

## Data Transformation Functions

Key functions that process and transform data:

### dashboard.api.main.safe_parse
> Parse kwargs from SQLite, handling both JSON and Python repr formats.
- **Output to**: json.loads, ast.literal_eval

### pyqual.custom_fix.parse_and_apply_suggestions
> Parse LLM suggestions and apply patches.
- **Output to**: re.findall, Path, print, re.search, file_path.exists

### pyqual.output._parse_output_line

### pyqual.config.PyqualConfig._parse
- **Output to**: raw.get, pyqual.tools.load_entry_point_presets, pyqual.tools.load_user_tools, pipeline.get, pipeline.get

### pyqual.config.PyqualConfig._validate_stages
> Validate and construct StageConfig list from raw dicts.
- **Output to**: StageConfig, stages.append, StageConfig.__dataclass_fields__.values, ValueError, ValueError

### pyqual.auto_closer._process_ticket
> Process a single ticket for closure. Returns True if closed.
- **Output to**: print, pyqual.auto_closer.evaluate_with_llm, ticket.sync.get, store.update_ticket, external_id.isdigit

### pyqual.report_generator.parse_kwargs
> Parse kwargs string that might have single quotes.
- **Output to**: json.loads, ast.literal_eval

### pyqual.parallel.parse_todo_items
> Parse unchecked items from TODO.md.
- **Output to**: todo_path.read_text, content.splitlines, todo_path.exists, line.strip, line.startswith

### pyqual.cli_bulk_cmds._discover_and_validate
> Discover projects and validate path. Returns states or raises Exit.
- **Output to**: pyqual.bulk.orchestrator.discover_projects, path.is_dir, _console.print, typer.Exit, _console.print

### pyqual.api.validate_config
> Validate configuration and return list of errors (empty if valid).
- **Output to**: _validate, str

### pyqual.api.format_result_summary
> Format pipeline result as human-readable summary.

Args:
    result: Pipeline result object
    
Ret
- **Output to**: enumerate, None.join, lines.append, lines.append, lines.append

### pyqual.run_parallel_fix.parse_args
> Parse command line arguments.
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args

### pyqual.bulk_init._validate_yaml_content
> Validate that YAML content is parseable and has required structure.
- **Output to**: yaml.safe_load, ValueError, ValueError

### pyqual.yaml_fixer._try_parse_yaml
> Try to parse YAML and return success status and error message.
- **Output to**: yaml.safe_load, str

### pyqual.yaml_fixer._parse_pyyaml_error
> Parse PyYAML error message to extract line/column info.
- **Output to**: YamlSyntaxIssue, re.search, error_str.lower, pyqual.yaml_fixer._get_context, error_str.lower

### pyqual.cli_log_helpers.format_log_entry_row
> Return (ts, event_name, name, status, details) for one log entry.
- **Output to**: entry.get, entry.get, None.replace, entry.get, entry.get

### pyqual.cli_run_helpers._format_ticket_summary
> Format ticket/TODO progress section.
- **Output to**: summary.get, summary.get, summary.get, parts.append, None.join

### pyqual.cli_run_helpers._format_fix_summary
> Format fix stage outcomes section.
- **Output to**: summary.get, summary.get, summary.get, summary.get, fix_parts.append

### pyqual.cli_run_helpers._format_delivery_summary
> Format delivery/push outcomes section.
- **Output to**: isinstance, None.join, str

### pyqual.cli_run_helpers.format_run_summary
> Format run summary dict into human-readable string with ticket outcomes.
- **Output to**: pyqual.cli_run_helpers._format_ticket_summary, pyqual.cli_run_helpers._format_fix_summary, pyqual.cli_run_helpers._format_delivery_summary, parts.append, parts.append

### pyqual.report._parse_pyproject_fallback
> Minimal regex parser for pyproject.toml when tomllib is unavailable.
- **Output to**: path.read_text, re.search, re.search, m.group, m.group

### pyqual.cli.cmd_config.validate
> Validate pyqual.yaml without running the pipeline.

Checks for:
- YAML parse errors (with line/colum
- **Output to**: app.command, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.plugins.cli_helpers.plugin_validate
> Validate that configured plugins in pyqual.yaml are available.
- **Output to**: config_path.read_text, console.print, console.print, set, set

### pyqual.plugins.documentation.main.DocumentationCollector._parse_pyproject_fallback
> Minimal regex parser for pyproject.toml.
- **Output to**: path.read_text, re.search, m.group

### pyqual.validation.release._parse_pyproject_fallback
> Extract key metadata from ``pyproject.toml`` with regexes.
- **Output to**: path.read_text, re.search, re.search, re.search, poetry_match.group

## Behavioral Patterns

### state_machine_ProjectRunState
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: pyqual.bulk.models.ProjectRunState.elapsed, pyqual.bulk.models.ProjectRunState.progress_pct, pyqual.bulk.models.ProjectRunState.gates_label

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `pyqual.bulk_init.generate_pyqual_yaml` - 77 calls
- `pyqual.cli.cmd_run.run` - 53 calls
- `pyqual.cli.cmd_config.fix_config` - 46 calls
- `pyqual.cli.cmd_git.git_scan_cmd` - 42 calls
- `run_analysis.run_project` - 38 calls
- `pyqual.cli_log_helpers.format_log_entry_row` - 38 calls
- `pyqual.run_parallel_fix.main` - 37 calls
- `pyqual.validation.release.validate_release_state` - 33 calls
- `pyqual.report_generator.get_last_run` - 32 calls
- `examples.multi_gate_pipeline.run_pipeline.main` - 30 calls
- `examples.custom_gates.metric_history.main` - 29 calls
- `pyqual.auto_closer.main` - 27 calls
- `pyqual.bulk_init.classify_with_llm` - 26 calls
- `pyqual.cli_observe.register_observe_commands` - 26 calls
- `pyqual.parallel.ParallelExecutor.run` - 25 calls
- `pyqual.cli.cmd_git.git_commit_cmd` - 25 calls
- `pyqual.cli.cmd_config.validate` - 25 calls
- `pyqual.plugins.cli_helpers.plugin_search` - 25 calls
- `pyqual.yaml_fixer.analyze_yaml_syntax` - 24 calls
- `pyqual.cli.cmd_tickets.tickets_sync` - 24 calls
- `pyqual.plugins.attack.main.attack_merge` - 24 calls
- `pyqual.cli.cmd_git.git_status_cmd` - 23 calls
- `pyqual.cli.cmd_config.status` - 23 calls
- `pyqual.plugins.git.main.scan_for_secrets` - 23 calls
- `pyqual.cli.cmd_init.init` - 22 calls
- `pyqual.cli.main.tune_thresholds_cmd` - 22 calls
- `pyqual.plugins.git.main.git_push` - 22 calls
- `pyqual.custom_fix.parse_and_apply_suggestions` - 21 calls
- `pyqual.cli_bulk_cmds.register_bulk_commands` - 21 calls
- `pyqual.plugins.deps.main.deps_health_check` - 21 calls
- `pyqual.plugins.git.main.preflight_push_check` - 21 calls
- `pyqual.cli_run_helpers.extract_fix_stage_summary` - 20 calls
- `pyqual.cli.cmd_config.gates` - 20 calls
- `pyqual.plugins.git.status.git_status` - 20 calls
- `pyqual.plugins.git.main.GitCollector.collect` - 20 calls
- `pyqual.plugins.git.main.git_status` - 20 calls
- `pyqual.run_parallel_fix.mark_completed_todos` - 19 calls
- `pyqual.cli.cmd_info.tools` - 19 calls
- `pyqual.cli.cmd_tune.tune_thresholds` - 19 calls
- `pyqual.plugins.cli_helpers.plugin_list` - 19 calls

## System Interactions

How components interact:

```mermaid
graph TD
    run --> command
    run --> Option
    fix_config --> command
    fix_config --> Option
    git_scan_cmd --> command
    git_scan_cmd --> Argument
    git_scan_cmd --> Option
    format_log_entry_row --> get
    format_log_entry_row --> replace
    main --> parse_args
    main --> cwd
    main --> get_todo_batch
    main --> print
    main --> enumerate
    main --> Path
    main --> load
    main --> Pipeline
    main --> TemporaryDirectory
    main --> mkdir
    _parse --> get
    _parse --> load_entry_point_pre
    _parse --> load_user_tools
    main --> get
    main --> PlanfileStore
    _collect_readme_metr --> exists
    _collect_readme_metr --> _set_zero_readme
    _collect_readme_metr --> loads
    _collect_readme_metr --> float
    register_observe_com --> command
    register_observe_com --> Option
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.