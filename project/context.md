# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/pyqual
- **Primary Language**: python
- **Languages**: python: 52, typescript: 11, shell: 4, javascript: 2
- **Analysis Mode**: static
- **Total Functions**: 369
- **Total Classes**: 70
- **Modules**: 69
- **Entry Points**: 244

## Architecture by Module

### pyqual.pipeline
- **Functions**: 26
- **Classes**: 10
- **File**: `pipeline.py`

### dashboard.src.api
- **Functions**: 23
- **File**: `index.ts`

### pyqual._gate_collectors
- **Functions**: 22
- **File**: `_gate_collectors.py`

### pyqual.cli
- **Functions**: 21
- **File**: `cli.py`

### pyqual.github_actions
- **Functions**: 16
- **Classes**: 2
- **File**: `github_actions.py`

### pyqual.report
- **Functions**: 16
- **File**: `report.py`

### pyqual.tools
- **Functions**: 15
- **Classes**: 1
- **File**: `tools.py`

### pyqual.builtin_collectors
- **Functions**: 15
- **Classes**: 8
- **File**: `builtin_collectors.py`

### pyqual.bulk_init
- **Functions**: 15
- **Classes**: 3
- **File**: `bulk_init.py`

### pyqual.cli_run_helpers
- **Functions**: 15
- **File**: `cli_run_helpers.py`

### dashboard.api.main
- **Functions**: 13
- **File**: `main.py`

### pyqual.documentation
- **Functions**: 11
- **Classes**: 1
- **File**: `documentation.py`

### dashboard.src.App
- **Functions**: 9
- **File**: `App.tsx`

### pyqual.report_generator
- **Functions**: 8
- **Classes**: 2
- **File**: `report_generator.py`

### pyqual.gates
- **Functions**: 8
- **Classes**: 3
- **File**: `gates.py`

### integration.run_matrix
- **Functions**: 8
- **File**: `run_matrix.sh`

### dashboard.src.components.MetricsChart
- **Functions**: 7
- **Classes**: 1
- **File**: `MetricsChart.tsx`

### pyqual.config
- **Functions**: 7
- **Classes**: 4
- **File**: `config.py`

### pyqual.parallel
- **Functions**: 7
- **Classes**: 4
- **File**: `parallel.py`

### pyqual._plugin_base
- **Functions**: 7
- **Classes**: 3
- **File**: `_plugin_base.py`

## Key Entry Points

Main execution flows into the system:

### pyqual.cli_observe.register_observe_commands
> Register logs, watch, and history commands onto *app*.
- **Calls**: app.command, app.command, app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.cli.run
> Execute pipeline loop until quality gates pass.

Output is streamed as YAML to stdout as each stage completes.
Diagnostic messages go to stderr.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, pyqual.cli._setup_logging

### pyqual.cli_bulk_cmds.register_bulk_commands
> Register bulk-init and bulk-run commands onto *app*.
- **Calls**: app.command, app.command, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.run_parallel_fix.main
> Run parallel fix on TODO.md items - configurable batch size with git push.
- **Calls**: pyqual.run_parallel_fix.parse_args, Path.cwd, pyqual.run_parallel_fix.get_todo_batch, print, enumerate, batch_file.parent.mkdir, batch_file.write_text, print

### pyqual.cli_run_helpers.enrich_from_artifacts
> Enrich stage dicts with metrics read from artifact files on disk.
- **Calls**: analysis.exists, validation.exists, todo.exists, None.join, re.search, re.search, re.search, None.join

### pyqual.cli.fix_config
> Use LLM to auto-repair pyqual.yaml based on project structure.

Scans the project (language, available tools, test framework) and asks the
LLM to prod
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, None.resolve, pyqual.validation.validate_config, pyqual.validation.detect_project_facts

### pyqual.auto_closer.main
- **Calls**: Path.cwd, gates_info.get, gates_info.get, print, PlanfileStore, store.list_tickets, print, pyqual.auto_closer.get_changed_files

### pyqual.cli_log_helpers.format_log_entry_row
> Return (ts, event_name, name, status, details) for one log entry.
- **Calls**: entry.get, entry.get, None.replace, entry.get, entry.get, None.join, entry.get, entry.get

### pyqual.config.PyqualConfig._parse
- **Calls**: raw.get, pyqual.tools.load_entry_point_presets, pyqual.tools.load_user_tools, pipeline.get, pipeline.get, pipeline.get, cls, pyqual.tools.register_custom_tools_from_yaml

### pyqual._gate_collectors._from_vulnerabilities
> Extract vulnerability metrics from vulns.json.
- **Calls**: vuln_path.exists, json.loads, isinstance, vuln_path.read_text, sum, sum, sum, float

### examples.multi_gate_pipeline.run_pipeline.main
- **Calls**: Path, PyqualConfig.load, Pipeline, print, print, print, print, print

### pyqual.cli_run_helpers.build_run_summary
- **Calls**: next, next, prefact_stage.get, prefact_stage.get, isinstance, isinstance, fix_stage.get, isinstance

### examples.custom_gates.metric_history.main
> Run the metric history self-test with synthetic history.
- **Calls**: tempfile.TemporaryDirectory, Path, pyqual_dir.mkdir, print, print, print, print, sorted

### pyqual._gate_collectors._from_flake8
> Extract flake8 violation count from JSON output.
- **Calls**: p.exists, json.loads, isinstance, p.read_text, len, sum, sum, sum

### pyqual.parallel.ParallelExecutor.run
> Run all issues across tools in parallel.

Args:
    issues: List of issue strings to process
    group_similar: If True, group similar issues for batc
- **Calls**: time.monotonic, enumerate, len, log.info, sum, sum, sum, log.info

### pyqual.builtin_collectors.SecurityCollector.collect
- **Calls**: path.exists, path.exists, json.loads, isinstance, json.loads, sum, float, float

### pyqual._gate_collectors._from_ruff
> Extract ruff linter error counts from JSON output.
- **Calls**: p.exists, json.loads, isinstance, p.read_text, len, sum, sum, float

### pyqual.pipeline.Pipeline._execute_streaming
> Execute stage with real-time output streaming via Popen.
- **Calls**: subprocess.Popen, proc.wait, StageResult, StageResult, select.select, fd.readline, None.append, None.join

### pyqual.cli.init
> Create pyqual.yaml with sensible defaults.

Use --profile for a minimal config based on a built-in profile:

    pyqual init --profile python         
- **Calls**: app.command, typer.Argument, typer.Option, target.exists, None.mkdir, console.print, console.print, Path

### pyqual.custom_fix.parse_and_apply_suggestions
> Parse LLM suggestions and apply patches.
- **Calls**: re.findall, Path, print, re.search, file_path.exists, print, file_path.read_text, re.search

### pyqual.cli.validate
> Validate pyqual.yaml without running the pipeline.

Checks for:
- YAML parse errors
- Unknown or missing tool binaries
- Gate metric names that no col
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, pyqual.validation.validate_config, console.print, console.print, len

### pyqual.cli.status
> Show current metrics and pipeline config.
- **Calls**: app.command, typer.Option, typer.Option, PyqualConfig.load, GateSet, gate_set._collect_metrics, console.print, console.print

### pyqual.cli.gates
> Check quality gates without running stages.
- **Calls**: app.command, typer.Option, typer.Option, PyqualConfig.load, GateSet, gate_set.check_all, Table, table.add_column

### pyqual.documentation.DocumentationCollector._check_docs_folder
> Check docs/ folder presence and content.
- **Calls**: any, next, float, any, list, len, any, p.exists

### pyqual.cli.tools
> List built-in tool presets for pipeline stages.
- **Calls**: app.command, Table, table.add_column, table.add_column, table.add_column, table.add_column, table.add_column, sorted

### pyqual.documentation.DocumentationCollector.collect
> Collect all documentation metrics.
- **Calls**: result.update, result.update, result.update, result.update, result.update, result.update, sum, self._check_required_files

### pyqual.pipeline.Pipeline._execute_stage
> Execute a single stage command.
- **Calls**: log.info, bool, time.monotonic, self._log_stage, self._resolve_tool_stage, StageResult, self._log_stage, self.on_stage_start

### pyqual.cli.mcp_fix
> Run the llx-backed MCP fix workflow.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### pyqual.documentation.DocumentationCollector._get_docstring_coverage
> Get docstring coverage from interrogate output or estimate.
- **Calls**: interrogate_path.exists, pydocstyle_path.exists, json.loads, json.loads, isinstance, interrogate_path.read_text, data.get, data.get

### pyqual.builtin_collectors.LLMBenchCollector.collect
- **Calls**: humaneval_path.exists, codebleu_path.exists, json.loads, json.loads, humaneval_path.read_text, data.get, data.get, float

## Process Flows

Key execution flows identified:

### Flow 1: register_observe_commands
```
register_observe_commands [pyqual.cli_observe]
```

### Flow 2: run
```
run [pyqual.cli]
```

### Flow 3: register_bulk_commands
```
register_bulk_commands [pyqual.cli_bulk_cmds]
```

### Flow 4: main
```
main [pyqual.run_parallel_fix]
  └─> parse_args
  └─> get_todo_batch
```

### Flow 5: enrich_from_artifacts
```
enrich_from_artifacts [pyqual.cli_run_helpers]
```

### Flow 6: fix_config
```
fix_config [pyqual.cli]
```

### Flow 7: format_log_entry_row
```
format_log_entry_row [pyqual.cli_log_helpers]
```

### Flow 8: _parse
```
_parse [pyqual.config.PyqualConfig]
  └─ →> load_entry_point_presets
  └─ →> load_user_tools
      └─> _load_json_presets
```

### Flow 9: _from_vulnerabilities
```
_from_vulnerabilities [pyqual._gate_collectors]
```

### Flow 10: build_run_summary
```
build_run_summary [pyqual.cli_run_helpers]
```

## Key Classes

### pyqual.pipeline.Pipeline
> Execute pipeline stages in a loop until quality gates pass.
- **Methods**: 20
- **Key Methods**: pyqual.pipeline.Pipeline.__init__, pyqual.pipeline.Pipeline.run, pyqual.pipeline.Pipeline.check_gates, pyqual.pipeline.Pipeline._run_iteration, pyqual.pipeline.Pipeline._iteration_stagnated, pyqual.pipeline.Pipeline._should_run_stage, pyqual.pipeline.Pipeline._resolve_tool_stage, pyqual.pipeline.Pipeline._resolve_env, pyqual.pipeline.Pipeline._check_optional_binary, pyqual.pipeline.Pipeline._execute_stage

### pyqual.github_actions.GitHubActionsReporter
> Reports pyqual results to GitHub Actions and PRs.
- **Methods**: 14
- **Key Methods**: pyqual.github_actions.GitHubActionsReporter.__init__, pyqual.github_actions.GitHubActionsReporter.create_issue, pyqual.github_actions.GitHubActionsReporter.ensure_issue_exists, pyqual.github_actions.GitHubActionsReporter.is_running_in_github_actions, pyqual.github_actions.GitHubActionsReporter.get_pr_number, pyqual.github_actions.GitHubActionsReporter.fetch_issues, pyqual.github_actions.GitHubActionsReporter.fetch_pull_requests, pyqual.github_actions.GitHubActionsReporter.post_pr_comment, pyqual.github_actions.GitHubActionsReporter.post_issue_comment, pyqual.github_actions.GitHubActionsReporter.close_issue

### pyqual.documentation.DocumentationCollector
> Documentation completeness and quality metrics.

Measures:
- Required files presence (readme, licens
- **Methods**: 11
- **Key Methods**: pyqual.documentation.DocumentationCollector._find_file, pyqual.documentation.DocumentationCollector._check_file_exists, pyqual.documentation.DocumentationCollector._read_pyproject, pyqual.documentation.DocumentationCollector._parse_pyproject_fallback, pyqual.documentation.DocumentationCollector._check_pyproject_metadata, pyqual.documentation.DocumentationCollector._analyze_readme, pyqual.documentation.DocumentationCollector._check_docs_folder, pyqual.documentation.DocumentationCollector._check_required_files, pyqual.documentation.DocumentationCollector._get_docstring_coverage, pyqual.documentation.DocumentationCollector._check_license_type
- **Inherits**: MetricCollector

### pyqual.builtin_collectors.LlxMcpFixCollector
> Dockerized llx MCP fix/refactor workflow results.
- **Methods**: 8
- **Key Methods**: pyqual.builtin_collectors.LlxMcpFixCollector._tier_rank, pyqual.builtin_collectors.LlxMcpFixCollector._load_report, pyqual.builtin_collectors.LlxMcpFixCollector._assign_float, pyqual.builtin_collectors.LlxMcpFixCollector._count_lines, pyqual.builtin_collectors.LlxMcpFixCollector._collect_analysis_metrics, pyqual.builtin_collectors.LlxMcpFixCollector._collect_aider_metrics, pyqual.builtin_collectors.LlxMcpFixCollector.get_config_example, pyqual.builtin_collectors.LlxMcpFixCollector.collect
- **Inherits**: MetricCollector

### pyqual.gates.GateSet
> Collection of quality gates with metric collection.
- **Methods**: 6
- **Key Methods**: pyqual.gates.GateSet.__init__, pyqual.gates.GateSet._completion_rate, pyqual.gates.GateSet.check_all, pyqual.gates.GateSet.all_passed, pyqual.gates.GateSet.completion_percentage, pyqual.gates.GateSet._collect_metrics

### pyqual.fix_tools.base.FixTool
> Abstract base class for fix tools.
- **Methods**: 5
- **Key Methods**: pyqual.fix_tools.base.FixTool.__init__, pyqual.fix_tools.base.FixTool.is_available, pyqual.fix_tools.base.FixTool.get_command, pyqual.fix_tools.base.FixTool.get_timeout, pyqual.fix_tools.base.FixTool.to_config
- **Inherits**: ABC

### pyqual.config.PyqualConfig
> Full pyqual.yaml configuration.
- **Methods**: 4
- **Key Methods**: pyqual.config.PyqualConfig.load, pyqual.config.PyqualConfig.llm_model, pyqual.config.PyqualConfig._parse, pyqual.config.PyqualConfig.default_yaml

### pyqual.parallel.ParallelExecutor
> Executes tasks across multiple fix tools in parallel.
- **Methods**: 4
- **Key Methods**: pyqual.parallel.ParallelExecutor.__init__, pyqual.parallel.ParallelExecutor._run_tool_task, pyqual.parallel.ParallelExecutor._tool_worker, pyqual.parallel.ParallelExecutor.run

### pyqual._plugin_base.PluginRegistry
> Registry for metric collector plugins.
- **Methods**: 4
- **Key Methods**: pyqual._plugin_base.PluginRegistry.register, pyqual._plugin_base.PluginRegistry.get, pyqual._plugin_base.PluginRegistry.list_plugins, pyqual._plugin_base.PluginRegistry.create_instance

### pyqual.validation.ValidationResult
> Aggregated result of validating one pyqual.yaml.
- **Methods**: 4
- **Key Methods**: pyqual.validation.ValidationResult.errors, pyqual.validation.ValidationResult.warnings, pyqual.validation.ValidationResult.ok, pyqual.validation.ValidationResult.add

### pyqual.fix_tools.llx.LlxTool
> LLX fix tool.
- **Methods**: 4
- **Key Methods**: pyqual.fix_tools.llx.LlxTool.__init__, pyqual.fix_tools.llx.LlxTool.is_available, pyqual.fix_tools.llx.LlxTool.get_command, pyqual.fix_tools.llx.LlxTool.get_timeout
- **Inherits**: FixTool

### pyqual.bulk_run.ProjectRunState
> Mutable state for a single project's pyqual run.
- **Methods**: 3
- **Key Methods**: pyqual.bulk_run.ProjectRunState.progress_pct, pyqual.bulk_run.ProjectRunState.elapsed, pyqual.bulk_run.ProjectRunState.gates_label

### pyqual.fix_tools.aider.AiderTool
> Aider tool via Docker (paulgauthier/aider).
- **Methods**: 3
- **Key Methods**: pyqual.fix_tools.aider.AiderTool.is_available, pyqual.fix_tools.aider.AiderTool.get_command, pyqual.fix_tools.aider.AiderTool.get_timeout
- **Inherits**: FixTool

### pyqual.fix_tools.claude.ClaudeTool
> Claude Code CLI tool.
- **Methods**: 3
- **Key Methods**: pyqual.fix_tools.claude.ClaudeTool.is_available, pyqual.fix_tools.claude.ClaudeTool.get_command, pyqual.fix_tools.claude.ClaudeTool.get_timeout
- **Inherits**: FixTool

### examples.custom_plugins.performance_collector.PerformanceCollector
> Collect latency and throughput metrics from load test results.
- **Methods**: 2
- **Key Methods**: examples.custom_plugins.performance_collector.PerformanceCollector.collect, examples.custom_plugins.performance_collector.PerformanceCollector.get_config_example
- **Inherits**: MetricCollector

### examples.custom_plugins.code_health_collector.CodeHealthCollector
> Weighted composite health score from multiple code quality signals.
- **Methods**: 2
- **Key Methods**: examples.custom_plugins.code_health_collector.CodeHealthCollector.collect, examples.custom_plugins.code_health_collector.CodeHealthCollector.get_config_example
- **Inherits**: MetricCollector

### pyqual.tools.ToolPreset
> Definition of a built-in tool invocation preset.
- **Methods**: 2
- **Key Methods**: pyqual.tools.ToolPreset.is_available, pyqual.tools.ToolPreset.shell_command

### pyqual._plugin_base.MetricCollector
> Base class for metric collector plugins.
- **Methods**: 2
- **Key Methods**: pyqual._plugin_base.MetricCollector.collect, pyqual._plugin_base.MetricCollector.get_config_example
- **Inherits**: ABC

### pyqual.github_actions.GitHubTask
> Represents a task from GitHub (issue or PR).
- **Methods**: 2
- **Key Methods**: pyqual.github_actions.GitHubTask.to_todo_item, pyqual.github_actions.GitHubTask.__str__

### pyqual.validation.StageFailure
> Runtime failure description from a completed stage.
- **Methods**: 2
- **Key Methods**: pyqual.validation.StageFailure.error_code, pyqual.validation.StageFailure.domain

## Data Transformation Functions

Key functions that process and transform data:

### dashboard.api.main.safe_parse
> Parse kwargs from SQLite, handling both JSON and Python repr formats.
- **Output to**: json.loads, ast.literal_eval

### pyqual.custom_fix.parse_and_apply_suggestions
> Parse LLM suggestions and apply patches.
- **Output to**: re.findall, Path, print, re.search, file_path.exists

### pyqual.config.PyqualConfig._parse
- **Output to**: raw.get, pyqual.tools.load_entry_point_presets, pyqual.tools.load_user_tools, pipeline.get, pipeline.get

### pyqual.report_generator.parse_kwargs
> Parse kwargs string that might have single quotes.
- **Output to**: json.loads, ast.literal_eval

### pyqual.parallel.parse_todo_items
> Parse unchecked items from TODO.md.
- **Output to**: todo_path.read_text, content.splitlines, todo_path.exists, line.strip, line.startswith

### pyqual.cli.validate
> Validate pyqual.yaml without running the pipeline.

Checks for:
- YAML parse errors
- Unknown or mis
- **Output to**: app.command, typer.Option, typer.Option, typer.Option, pyqual.validation.validate_config

### pyqual.documentation.DocumentationCollector._parse_pyproject_fallback
> Minimal regex parser for pyproject.toml.
- **Output to**: path.read_text, re.search, m.group

### pyqual.run_parallel_fix.parse_args
> Parse command line arguments.
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args

### pyqual.cli_plugin_helpers.plugin_validate
> Validate that configured plugins in pyqual.yaml are available.
- **Output to**: config_path.read_text, console.print, console.print, set, set

### pyqual.validation.validate_config
> Validate a pyqual.yaml file and return structured issues.

Does NOT run any stages — this is a stati
- **Output to**: ValidationResult, raw.get, pipeline.get, pipeline.get, metrics_raw.items

### pyqual.cli_run_helpers.format_run_summary
- **Output to**: todo_bits.append, todo_bits.append, todo_bits.append, parts.append, fix_bits.append

### pyqual.cli_log_helpers.format_log_entry_row
> Return (ts, event_name, name, status, details) for one log entry.
- **Output to**: entry.get, entry.get, None.replace, entry.get, entry.get

### pyqual.bulk_run._parse_output_line
> Parse a line of pyqual run output and update state.
- **Output to**: line.strip, clean.startswith, clean.startswith, None.strip, None.strip

### pyqual.integrations.llx_mcp_service.build_parser
> Build the CLI parser for the MCP service.
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, os.getenv, int

### pyqual.integrations.llx_mcp.build_parser
> Build the CLI parser for the llx MCP helper.
- **Output to**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument

### pyqual.report._parse_pyproject_fallback
> Minimal regex parser for pyproject.toml when tomllib is unavailable.
- **Output to**: path.read_text, re.search, re.search, m.group, m.group

## Behavioral Patterns

### state_machine_ProjectRunState
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: pyqual.bulk_run.ProjectRunState.progress_pct, pyqual.bulk_run.ProjectRunState.elapsed, pyqual.bulk_run.ProjectRunState.gates_label

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `pyqual.cli_observe.register_observe_commands` - 180 calls
- `pyqual.cli.run` - 115 calls
- `pyqual.cli_bulk_cmds.register_bulk_commands` - 91 calls
- `pyqual.run_parallel_fix.main` - 86 calls
- `pyqual.bulk_init.generate_pyqual_yaml` - 77 calls
- `pyqual.cli_run_helpers.enrich_from_artifacts` - 50 calls
- `pyqual.cli.fix_config` - 46 calls
- `pyqual.auto_closer.main` - 45 calls
- `pyqual.validation.validate_config` - 45 calls
- `run_analysis.run_project` - 38 calls
- `pyqual.cli_log_helpers.format_log_entry_row` - 38 calls
- `pyqual.report_generator.get_last_run` - 33 calls
- `examples.multi_gate_pipeline.run_pipeline.main` - 30 calls
- `pyqual.cli_run_helpers.build_run_summary` - 30 calls
- `examples.custom_gates.metric_history.main` - 29 calls
- `pyqual.bulk_init.classify_with_llm` - 26 calls
- `pyqual.parallel.ParallelExecutor.run` - 25 calls
- `pyqual.cli_plugin_helpers.plugin_search` - 25 calls
- `pyqual.builtin_collectors.SecurityCollector.collect` - 23 calls
- `pyqual.cli.init` - 22 calls
- `pyqual.bulk_init.bulk_init` - 22 calls
- `pyqual.bulk_run.bulk_run` - 22 calls
- `pyqual.custom_fix.parse_and_apply_suggestions` - 21 calls
- `pyqual.cli.validate` - 21 calls
- `pyqual.cli.status` - 21 calls
- `pyqual.cli.gates` - 20 calls
- `pyqual.cli_run_helpers.extract_fix_stage_summary` - 20 calls
- `pyqual.cli.tools` - 19 calls
- `pyqual.documentation.DocumentationCollector.collect` - 19 calls
- `pyqual.run_parallel_fix.mark_completed_todos` - 19 calls
- `pyqual.cli_plugin_helpers.plugin_list` - 19 calls
- `pyqual.cli_plugin_helpers.plugin_add` - 19 calls
- `pyqual.cli.mcp_fix` - 18 calls
- `pyqual.builtin_collectors.LLMBenchCollector.collect` - 18 calls
- `pyqual.bulk_run.build_dashboard_table` - 18 calls
- `pyqual.integrations.llx_mcp.main` - 18 calls
- `dashboard.src.components.RepositoryDetail.RepositoryDetail` - 17 calls
- `examples.custom_gates.composite_gates.run_composite_check` - 17 calls
- `pyqual.cli.mcp_refactor` - 17 calls
- `pyqual.cli.doctor` - 17 calls

## System Interactions

How components interact:

```mermaid
graph TD
    register_observe_com --> command
    register_observe_com --> Option
    run --> command
    run --> Option
    register_bulk_comman --> command
    register_bulk_comman --> Argument
    register_bulk_comman --> Option
    main --> parse_args
    main --> cwd
    main --> get_todo_batch
    main --> print
    main --> enumerate
    enrich_from_artifact --> exists
    enrich_from_artifact --> join
    enrich_from_artifact --> search
    fix_config --> command
    fix_config --> Option
    main --> get
    main --> PlanfileStore
    format_log_entry_row --> get
    format_log_entry_row --> replace
    _parse --> get
    _parse --> load_entry_point_pre
    _parse --> load_user_tools
    _from_vulnerabilitie --> exists
    _from_vulnerabilitie --> loads
    _from_vulnerabilitie --> isinstance
    _from_vulnerabilitie --> read_text
    _from_vulnerabilitie --> sum
    main --> Path
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.