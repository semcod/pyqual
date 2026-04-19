# pyqual

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Dependencies](#dependencies)
- [Source Map](#source-map)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `pyqual`
- **version**: `0.1.142`
- **python_requires**: `>=3.9`
- **license**: Apache-2.0
- **ai_model**: `openrouter/x-ai/grok-code-fast-1`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, app.doql.css, pyqual.yaml, goal.yaml, .env.example, src(36 mod), project/(6 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.css`)

```css markpact:doql path=app.doql.css
app {
  name: "pyqual";
  version: "0.1.139";
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="pyqual"] {

}

workflow[name="install"] {
  trigger: "manual";
  step-1: run cmd=pip3 install -e .;
}

workflow[name="install-dev"] {
  trigger: "manual";
  step-1: run cmd=pip3 install -e ".[dev]";
}

workflow[name="test"] {
  trigger: "manual";
  step-1: run cmd=python3 -m pytest;
}

workflow[name="lint"] {
  trigger: "manual";
  step-1: run cmd=ruff check .;
  step-2: run cmd=mypy pyqual;
}

workflow[name="format"] {
  trigger: "manual";
  step-1: run cmd=ruff format .;
}

workflow[name="clean"] {
  trigger: "manual";
  step-1: run cmd=rm -rf build/;
  step-2: run cmd=rm -rf dist/;
  step-3: run cmd=rm -rf *.egg-info/;
  step-4: run cmd=find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true;
  step-5: run cmd=find . -type f -name "*.pyc" -not -path "./.venv/*" -delete;
}

workflow[name="build"] {
  trigger: "manual";
  step-1: run cmd=python3 -m build;
}

workflow[name="bump-patch"] {
  trigger: "manual";
  step-1: run cmd=echo "Bumping patch version...";
  step-2: run cmd=CURRENT=$$(cat VERSION); \;
  step-3: run cmd=MAJOR=$$(echo $$CURRENT | cut -d. -f1); \;
  step-4: run cmd=MINOR=$$(echo $$CURRENT | cut -d. -f2); \;
  step-5: run cmd=PATCH=$$(echo $$CURRENT | cut -d. -f3); \;
  step-6: run cmd=NEW_PATCH=$$((PATCH + 1)); \;
  step-7: run cmd=NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \;
  step-8: run cmd=echo "$$NEW_VERSION" > VERSION; \;
  step-9: run cmd=sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \;
  step-10: run cmd=echo "Version bumped: $$CURRENT -> $$NEW_VERSION";
}

workflow[name="bump-minor"] {
  trigger: "manual";
  step-1: run cmd=echo "Bumping minor version...";
  step-2: run cmd=CURRENT=$$(cat VERSION); \;
  step-3: run cmd=MAJOR=$$(echo $$CURRENT | cut -d. -f1); \;
  step-4: run cmd=MINOR=$$(echo $$CURRENT | cut -d. -f2); \;
  step-5: run cmd=NEW_MINOR=$$((MINOR + 1)); \;
  step-6: run cmd=NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \;
  step-7: run cmd=echo "$$NEW_VERSION" > VERSION; \;
  step-8: run cmd=sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \;
  step-9: run cmd=echo "Version bumped: $$CURRENT -> $$NEW_VERSION";
}

workflow[name="publish"] {
  trigger: "manual";
  step-1: run cmd=python3 -m twine upload dist/* --skip-existing;
}

workflow[name="upload"] {
  trigger: "manual";
  step-1: depend target=publish;
}

workflow[name="fmt"] {
  trigger: "manual";
  step-1: run cmd=ruff format .;
}

workflow[name="health"] {
  trigger: "manual";
  step-1: run cmd=docker compose ps;
  step-2: run cmd=docker compose exec app echo "Health check passed";
}

workflow[name="import-makefile-hint"] {
  trigger: "manual";
  step-1: run cmd=echo 'Run: taskfile import Makefile to import existing targets.';
}

workflow[name="help"] {
  trigger: "manual";
  step-1: run cmd=echo "Available targets:";
  step-2: run cmd=echo "  install      Install the package";
  step-3: run cmd=echo "  install-dev  Install the package with dev dependencies";
  step-4: run cmd=echo "  test         Run tests";
  step-5: run cmd=echo "  lint         Run linting";
  step-6: run cmd=echo "  format       Format code";
  step-7: run cmd=echo "  clean        Clean build artifacts";
  step-8: run cmd=echo "  build        Build the package";
  step-9: run cmd=echo "  bump-patch   Bump patch version (0.1.2 -> 0.1.3)";
  step-10: run cmd=echo "  bump-minor   Bump minor version (0.1.2 -> 0.2.0)";
  step-11: run cmd=echo "  publish      Bump version, build and publish to PyPI";
  step-12: run cmd=echo "  upload       Upload to PyPI (alias for publish)";
}

deploy {
  target: docker;
}

environment[name="local"] {
  runtime: docker;
  env_file: ".env";
}

workflow[name="all"] {
  trigger: "manual";
  step-1: run cmd=taskfile run install;
  step-2: run cmd=taskfile run lint;
  step-3: run cmd=taskfile run test;
}
```

### Source Modules

- `pyqual._gate_collectors`
- `pyqual.analysis`
- `pyqual.api`
- `pyqual.auto_closer`
- `pyqual.bulk_init`
- `pyqual.bulk_init_classify`
- `pyqual.bulk_init_fingerprint`
- `pyqual.bulk_run`
- `pyqual.cli_bulk_cmds`
- `pyqual.cli_log_helpers`
- `pyqual.cli_observe`
- `pyqual.cli_run_helpers`
- `pyqual.command`
- `pyqual.config`
- `pyqual.constants`
- `pyqual.custom_fix`
- `pyqual.gates`
- `pyqual.github_actions`
- `pyqual.github_tasks`
- `pyqual.llm`
- `pyqual.output`
- `pyqual.parallel`
- `pyqual.pipeline`
- `pyqual.pipeline_protocols`
- `pyqual.pipeline_results`
- `pyqual.profiles`
- `pyqual.release_check`
- `pyqual.report`
- `pyqual.report_generator`
- `pyqual.run_parallel_fix`
- `pyqual.setup_deps`
- `pyqual.stage_names`
- `pyqual.tickets`
- `pyqual.tools`
- `pyqual.validation`
- `pyqual.yaml_fixer`

## Quality Pipeline (`pyqual.yaml`)

```yaml markpact:pyqual path=pyqual.yaml
pipeline:
  name: quality-loop-with-llx

  # Quality gates — pipeline iterates until ALL pass
  metrics:
    cc_max: 15           # cyclomatic complexity per function
    critical_max: 30     # functions above complexity threshold
    vallm_pass_min: 50   # vallm validation pass rate (%)
    coverage_min: 20     # line coverage (%) — minimum threshold
    coverage_branch_min: 15  # branch coverage (%) — minimum threshold
    completion_rate_min: 75  # percentage of passed gates required for closure — realistic threshold
    # Security gates (enabled):
    vuln_high_max: 0         # pip-audit high severity CVEs
    vuln_critical_max: 0     # pip-audit critical severity CVEs
    ruff_errors_max: 150     # ruff lint errors (realistic threshold)
    secrets_found_max: 0     # detect-secrets findings
    mypy_errors_max: 100      # mypy type errors (realistic for gradual typing)

  # Pipeline stages using new built-in tools
  stages:
    - name: setup
      tool: setup-deps
      when: first_iteration
      timeout: 300

    - name: setup_tasks
      run: |
        planfile sync github
        planfile sync markdown
      when: first_iteration
      optional: true

    - name: pip-audit
      tool: pip-audit
      when: always
      optional: true

    - name: ruff-lint
      tool: ruff
      when: always
      optional: true

    - name: detect-secrets
      tool: detect-secrets
      when: always
      optional: true

    - name: mypy-types
      tool: mypy
      when: always
      optional: true

    - name: prefact
      tool: prefact
      optional: true
      when: metrics_fail
      timeout: 900

    # Custom fix - uses explicit LLM_MODEL
    - name: fix
      run: |
        export PATH="$HOME/.local/bin:$PATH"
        python3 pyqual/custom_fix.py 2>&1 | tee .pyqual/fix_output.log || echo "Fix stage skipped"
      when: metrics_fail
      optional: true
      timeout: 1800

    - name: verify
      tool: vallm-verify
      optional: true
      when: after_fix

    - name: report
      tool: report
      when: always
      optional: true

    - name: todo_fix
      tool: todo-fix
      when: metrics_pass
      optional: true
      timeout: 1800

    - name: close_tasks
      tool: close-tasks
      when: always
      optional: true

    - name: push
      tool: git-push
      when: always
      optional: true

    - name: release-check
      tool: release-check
      when: metrics_pass
      timeout: 60

    - name: publish
      tool: make-publish
      when: metrics_pass
      optional: true

    - name: automerge
      tool: attack-merge
      when: always
      optional: true

    - name: markdown_report
      tool: markdown-report
      when: always
      optional: true

  loop:
    max_iterations: 3
    on_fail: report

  env:
    LLM_MODEL: openrouter/openai/gpt-5-mini
    LLX_DEFAULT_TIER: balanced
    LLX_VERBOSE: true
```

## Dependencies

### Runtime

```text markpact:deps python
pyyaml>=6.0
typer>=0.12
rich>=13.0
litellm>=1.0
python-dotenv>=1.0
nfo>=0.2.13
```

### Development

```text markpact:deps python scope=dev
pytest>=8.0
pytest-cov>=5.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
tox>=4.0.0
```

## Source Map

*Top 5 modules by symbol density — signatures for LLM orientation.*

### `pyqual._gate_collectors` (`pyqual/_gate_collectors.py`)

```python
def _read_artifact_text(workdir, filenames)  # CC=5, fan=2
def _from_toon(workdir)  # CC=4, fan=4
def _from_vallm(workdir)  # CC=6, fan=9
def _from_coverage(workdir)  # CC=9, fan=6
def _from_bandit(workdir)  # CC=4, fan=7
def _from_secrets(workdir)  # CC=7, fan=11
def _count_by_severity(items, severity)  # CC=1, fan=3
def _from_vulnerabilities(workdir)  # CC=6, fan=9
def _from_security(workdir)  # CC=2, fan=6
def _from_sbom(workdir)  # CC=5, fan=10
def _from_vulture(workdir)  # CC=5, fan=8
def _from_pyroma(workdir)  # CC=8, fan=9
def _from_code_health(workdir)  # CC=2, fan=6
def _from_git_health(workdir)  # CC=5, fan=5
def _from_llm_quality(workdir)  # CC=12, fan=5 ⚠
def _from_ai_cost(workdir)  # CC=5, fan=5
def _from_benchmark(workdir)  # CC=12, fan=8 ⚠
def _from_memory_profile(workdir)  # CC=7, fan=5
def _parse_radon_json(data)  # CC=4, fan=6
def _from_radon(workdir)  # CC=6, fan=7
def _from_mypy(workdir)  # CC=6, fan=8
def _from_lint(workdir)  # CC=2, fan=6
def _from_ruff(workdir)  # CC=8, fan=11
def _count_pylint_by_type(messages, type_name, symbol_prefix)  # CC=2, fan=5
def _from_pylint(workdir)  # CC=8, fan=9
def _from_flake8(workdir)  # CC=6, fan=11
def _from_runtime_errors(workdir)  # CC=6, fan=13
def _from_interrogate(workdir)  # CC=10, fan=6 ⚠
```

### `pyqual.pipeline` (`pyqual/pipeline.py`)

```python
class Pipeline:  # Execute pipeline stages in a loop until quality gates pass.
    def __init__(config, workdir, on_stage_start, on_iteration_start, on_stage_error, on_stage_done, on_stage_output, stream, on_iteration_done)  # CC=1
    def run(dry_run)  # CC=5
    def check_gates()  # CC=1
    def _run_iteration(num, dry_run)  # CC=7
    def _iteration_stagnated(iteration)  # CC=8
    def _should_run_stage(stage, gates_pass, stages_so_far, iteration)  # CC=5
    def _resolve_tool_stage(stage)  # CC=5
    def _resolve_env()  # CC=6
    def _check_optional_binary(command)  # CC=7
    def _make_skipped_result(stage, reason)  # CC=1
    def _make_dry_run_result(stage, command)  # CC=1
    def _execute_stage(stage, dry_run)  # CC=16 ⚠
    def _notify_stage_error(stage, result, is_fix_stage)  # CC=1
    def _execute_captured(stage, command, allow_failure, env, start)  # CC=6
    def _execute_streaming(stage, command, allow_failure, env, start)  # CC=10 ⚠
    def _init_nfo()  # CC=1
    def _nfo_emit(event, level, kwargs, duration_ms)  # CC=2
    def _is_fix_stage(stage)  # CC=5
    def _log_stage(stage, result)  # CC=9
    def _archive_llx_report(stage, result)  # CC=7
    def _log_gates(iteration, gates)  # CC=2
    def _log_event(event)  # CC=1
    def _ensure_pyqual_dir()  # CC=1
    def _capture_runtime_error(stage, result)  # CC=7
    def _classify_error(result)  # CC=6
    def _extract_error_message(result)  # CC=11 ⚠
```

### `pyqual.cli_run_helpers` (`pyqual/cli_run_helpers.py`)

```python
def count_todo_items(todo_path)  # CC=2, fan=3
def extract_pytest_stage_summary(name, text)  # CC=5, fan=5
def extract_lint_stage_summary(text)  # CC=3, fan=3
def extract_prefact_stage_summary(name, text)  # CC=4, fan=5
def extract_code2llm_stage_summary(name, text)  # CC=5, fan=5
def extract_validation_stage_summary(name, text)  # CC=6, fan=5
def extract_fix_stage_summary(name, text)  # CC=9, fan=10
def extract_mypy_stage_summary(name, text)  # CC=2, fan=3
def extract_bandit_stage_summary(text)  # CC=2, fan=3
def extract_stage_summary(name, stdout, stderr)  # CC=3, fan=9
def _enrich_analysis(workdir, stages)  # CC=8, fan=10
def _enrich_validation(workdir, stages)  # CC=7, fan=10
def _enrich_todo(workdir, stages)  # CC=7, fan=7
def enrich_from_artifacts(workdir, stages)  # CC=1, fan=3
def infer_fix_result(stage)  # CC=6, fan=7
def _extract_todo_summary(stages)  # CC=7, fan=4
def _extract_fix_summary(stages)  # CC=6, fan=7
def _extract_delivery_summary(stages)  # CC=7, fan=9
def build_run_summary(report)  # CC=1, fan=6
def _format_ticket_summary(summary)  # CC=6, fan=3
def _format_fix_summary(summary)  # CC=7, fan=3
def _format_delivery_summary(summary)  # CC=4, fan=3
def format_run_summary(summary)  # CC=5, fan=5
def get_last_error_line(text)  # CC=4, fan=5
```

### `pyqual.report` (`pyqual/report.py`)

```python
def _read_pyproject(workdir)  # CC=5, fan=4
def _parse_pyproject_fallback(path)  # CC=4, fan=3
def _read_version(workdir, pyproject)  # CC=3, fan=4
def _read_git_commit_count(workdir)  # CC=3, fan=4
def _read_costs_json(workdir)  # CC=6, fan=5
def _read_costs_package(workdir)  # CC=6, fan=12
def _read_costs_data(workdir)  # CC=4, fan=4
def collect_project_metadata(workdir, config)  # CC=10, fan=11 ⚠
def collect_all_metrics(workdir)  # CC=5, fan=5
def evaluate_gates(config, workdir)  # CC=1, fan=3
def generate_report(config, workdir, output)  # CC=2, fan=14
def _badge_url(label, value, color)  # CC=1, fan=1
def _build_project_badges(meta)  # CC=7, fan=4
def _build_quality_badges(metrics, gates_passed, gates_passed_count, gates_total)  # CC=5, fan=6
def build_badges(metrics, gates_passed, project_meta, gates_passed_count, gates_total)  # CC=4, fan=4
def _replace_badges_in_text(text, badge_line)  # CC=5, fan=10
def update_readme_badges(readme_path, metrics, gates_passed, project_meta, gates_passed_count, gates_total)  # CC=7, fan=14
def run(workdir, config_path, readme_path)  # CC=6, fan=12
def main()  # CC=1, fan=6
```

### `pyqual.bulk_init` (`pyqual/bulk_init.py`)

```python
def _build_llm_prompt(fp)  # CC=3, fan=4
def classify_with_llm(fp, model)  # CC=9, fan=14
def _classify_python(fp)  # CC=1, fan=1
def _classify_node(fp)  # CC=2, fan=1
def _classify_php(fp)  # CC=1, fan=1
def _classify_rust(fp)  # CC=1, fan=1
def _classify_go(fp)  # CC=1, fan=1
def _classify_makefile(fp)  # CC=1, fan=1
def _classify_heuristic(fp)  # CC=6, fan=5
def _safe_name(name)  # CC=1, fan=3
def generate_pyqual_yaml(project_name, cfg)  # CC=7, fan=6
def _validate_yaml_content(yaml_content, project_name)  # CC=4, fan=2
def _write_pyqual_yaml(project_dir, yaml_content)  # CC=1, fan=2
def _classify_project(fp, use_llm, model, project_name)  # CC=3, fan=3
def bulk_init(root)  # CC=12, fan=12 ⚠
class BulkInitResult:  # Summary of a bulk-init run.
    def total()  # CC=1
```

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/pyqual
# nodes: 335 | edges: 314 | modules: 67
# CC̄=5.1

HUBS[20]:
  pyqual.bulk_init.generate_pyqual_yaml
    CC=7  in:1  out:77  total:78
  pyqual.cli.cmd_run.run
    CC=17  in:0  out:53  total:53
  pyqual.cli.cmd_config.fix_config
    CC=13  in:0  out:46  total:46
  pyqual.cli.cmd_git.git_scan_cmd
    CC=11  in:0  out:42  total:42
  run_analysis.run_project
    CC=11  in:1  out:38  total:39
  pyqual.run_parallel_fix.main
    CC=13  in:0  out:37  total:37
  pyqual.validation.release.validate_release_state
    CC=22  in:1  out:33  total:34
  pyqual.report_generator.get_last_run
    CC=15  in:1  out:32  total:33
  pyqual._gate_collectors._from_flake8
    CC=12  in:1  out:30  total:31
  examples.multi_gate_pipeline.run_pipeline.main
    CC=13  in:0  out:30  total:30
  examples.custom_gates.metric_history.main
    CC=9  in:0  out:29  total:29
  pyqual.config.PyqualConfig._parse
    CC=13  in:0  out:28  total:28
  pyqual.cli_bulk_cmds._bulk_init_impl
    CC=14  in:1  out:27  total:28
  pyqual._gate_collectors._from_ruff
    CC=12  in:1  out:27  total:28
  pyqual.auto_closer.main
    CC=11  in:0  out:27  total:27
  pyqual._gate_collectors._from_vulnerabilities
    CC=6  in:1  out:26  total:27
  pyqual.bulk_init.classify_with_llm
    CC=9  in:1  out:26  total:27
  pyqual.yaml_fixer.analyze_yaml_syntax
    CC=10  in:2  out:24  total:26
  pyqual.plugins.attack.main.attack_merge
    CC=15  in:2  out:24  total:26
  pyqual.parallel.ParallelExecutor.run
    CC=15  in:1  out:25  total:26

MODULES:
  dashboard.api.main  [11 funcs]
    get_db_path  CC=1  out:1
    get_gate_status  CC=2  out:12
    get_latest_run  CC=2  out:3
    get_metric_history  CC=3  out:10
    get_project_runs  CC=3  out:8
    get_project_summary  CC=6  out:12
    get_projects  CC=5  out:10
    get_stage_performance  CC=3  out:12
    query_pipeline_db  CC=4  out:7
    read_summary_json  CC=3  out:5
  dashboard.src.App  [2 funcs]
    App  CC=8  out:11
    loadRepositories  CC=3  out:5
  dashboard.src.api  [8 funcs]
    config  CC=3  out:3
    fetchLatestRun  CC=11  out:6
    fetchRepositories  CC=4  out:5
    fetchRepositoriesWithFallback  CC=3  out:3
    getRepoPath  CC=2  out:1
    loadConfig  CC=7  out:5
    match  CC=1  out:0
    repositories  CC=3  out:3
  dashboard.src.components.RepositoryDetail  [2 funcs]
    RepositoryDetail  CC=9  out:9
    navigate  CC=3  out:6
  examples.custom_gates.composite_gates  [3 funcs]
    compute_composite_score  CC=9  out:12
    main  CC=2  out:13
    run_composite_check  CC=8  out:17
  examples.custom_gates.metric_history  [3 funcs]
    load_history  CC=4  out:4
    main  CC=9  out:29
    save_snapshot  CC=1  out:7
  examples.integration_example  [7 funcs]
    check_prerequisites  CC=1  out:3
    preview_pipeline  CC=4  out:5
    quick_gate_check  CC=4  out:3
    run_quality_check  CC=1  out:1
    run_shell_command_example  CC=3  out:8
    run_single_stage  CC=2  out:5
    run_with_callbacks  CC=1  out:5
  examples.multi_gate_pipeline.run_pipeline  [1 funcs]
    main  CC=13  out:30
  examples.ticket_workflow.sync_tickets  [3 funcs]
    main  CC=2  out:3
    sync_from_cli  CC=3  out:10
    tickets_from_gate_failures  CC=7  out:12
  pyqual._gate_collectors  [19 funcs]
    _count_by_severity  CC=3  out:3
    _count_pylint_by_type  CC=4  out:6
    _from_bandit  CC=10  out:17
    _from_code_health  CC=2  out:9
    _from_flake8  CC=12  out:30
    _from_interrogate  CC=10  out:16
    _from_lint  CC=2  out:9
    _from_mypy  CC=6  out:12
    _from_pylint  CC=8  out:21
    _from_pyroma  CC=8  out:15
  pyqual.api  [15 funcs]
    check  CC=2  out:1
    output  CC=3  out:1
    run  CC=2  out:2
    check_gates  CC=1  out:3
    create_default_config  CC=3  out:6
    dry_run  CC=1  out:1
    export_results_json  CC=4  out:5
    format_result_summary  CC=9  out:7
    get_tool_command  CC=2  out:4
    load_config  CC=2  out:7
  pyqual.auto_closer  [6 funcs]
    _close_github_issue  CC=4  out:6
    _process_ticket  CC=3  out:10
    evaluate_with_llm  CC=2  out:2
    get_changed_files  CC=4  out:9
    get_diff_content  CC=2  out:2
    main  CC=11  out:27
  pyqual.bulk.orchestrator  [3 funcs]
    build_dashboard_table  CC=15  out:16
    bulk_run  CC=11  out:16
    discover_projects  CC=5  out:7
  pyqual.bulk.parser  [2 funcs]
    _parse_iteration_header  CC=3  out:4
    _parse_output_line  CC=7  out:7
  pyqual.bulk.runner  [1 funcs]
    _run_single_project  CC=11  out:14
  pyqual.bulk_init  [9 funcs]
    _build_llm_prompt  CC=3  out:7
    _classify_heuristic  CC=6  out:7
    _classify_project  CC=3  out:4
    _safe_name  CC=1  out:3
    _validate_yaml_content  CC=4  out:3
    _write_pyqual_yaml  CC=1  out:2
    bulk_init  CC=14  out:18
    classify_with_llm  CC=9  out:26
    generate_pyqual_yaml  CC=7  out:77
  pyqual.bulk_init_classify  [1 funcs]
    check_skip_conditions  CC=8  out:6
  pyqual.bulk_init_fingerprint  [9 funcs]
    _collect_file_extensions  CC=7  out:10
    _collect_json_scripts  CC=4  out:4
    _collect_makefile_targets  CC=6  out:8
    _collect_manifests  CC=3  out:2
    _collect_pyproject_metadata  CC=10  out:11
    _collect_readme_excerpt  CC=4  out:2
    _collect_top_level_entries  CC=7  out:6
    _load_json_object  CC=3  out:3
    collect_fingerprint  CC=2  out:13
  pyqual.cli.cmd_config  [4 funcs]
    fix_config  CC=13  out:46
    gates  CC=6  out:20
    status  CC=5  out:23
    validate  CC=19  out:25
  pyqual.cli.cmd_git  [6 funcs]
    _print_file_list  CC=4  out:6
    _run_preflight_checks  CC=9  out:17
    git_add_cmd  CC=2  out:10
    git_commit_cmd  CC=5  out:25
    git_scan_cmd  CC=11  out:42
    git_status_cmd  CC=6  out:23
  pyqual.cli.cmd_init  [1 funcs]
    init  CC=7  out:22
  pyqual.cli.cmd_plugin  [1 funcs]
    plugin  CC=8  out:14
  pyqual.cli.cmd_run  [9 funcs]
    _create_tickets_if_needed  CC=7  out:6
    _emit  CC=1  out:2
    _emit_yaml_items  CC=2  out:4
    _handle_config_env_error  CC=8  out:10
    _handle_llm_error  CC=5  out:7
    _handle_pipeline_error  CC=2  out:4
    _on_stage_error_impl  CC=6  out:3
    _run_auto_fix_config  CC=7  out:21
    run  CC=17  out:53
  pyqual.cli.cmd_tickets  [4 funcs]
    tickets_all  CC=2  out:8
    tickets_fetch  CC=6  out:15
    tickets_github  CC=2  out:8
    tickets_todo  CC=2  out:8
  pyqual.cli.cmd_tune  [5 funcs]
    _calculate_thresholds  CC=12  out:15
    _display_comparison  CC=7  out:21
    _load_latest_metrics  CC=5  out:11
    tune_show  CC=4  out:13
    tune_thresholds  CC=7  out:19
  pyqual.cli.main  [5 funcs]
    _calculate_thresholds_for_tune  CC=7  out:7
    _display_comparison_for_tune  CC=7  out:21
    _load_latest_metrics_for_tune  CC=7  out:13
    setup_logging  CC=2  out:11
    tune_thresholds_cmd  CC=8  out:22
  pyqual.cli_bulk_cmds  [6 funcs]
    _bulk_init_impl  CC=14  out:27
    _bulk_run_impl  CC=8  out:11
    _discover_and_validate  CC=3  out:6
    _output_bulk_result  CC=9  out:21
    _run_with_live_dashboard  CC=2  out:10
    register_bulk_commands  CC=1  out:21
  pyqual.cli_observe  [9 funcs]
    _history_impl  CC=8  out:14
    _load_history_entries  CC=4  out:5
    _logs_impl  CC=6  out:11
    _output_human_logs  CC=4  out:10
    _output_json_entries  CC=4  out:4
    _output_sql_query  CC=7  out:11
    _print_history_summary  CC=10  out:14
    _print_history_table  CC=6  out:21
    _print_stage_output  CC=5  out:8
  pyqual.cli_run_helpers  [17 funcs]
    _enrich_analysis  CC=8  out:20
    _enrich_todo  CC=7  out:11
    _enrich_validation  CC=7  out:19
    _extract_delivery_summary  CC=7  out:15
    _extract_fix_summary  CC=8  out:15
    _extract_todo_summary  CC=9  out:13
    _format_delivery_summary  CC=5  out:3
    _format_fix_summary  CC=7  out:8
    _format_ticket_summary  CC=6  out:9
    build_run_summary  CC=5  out:10
  pyqual.config  [5 funcs]
    _parse  CC=13  out:28
    _validate_stages  CC=11  out:10
    load  CC=2  out:7
    __post_init__  CC=2  out:1
    _load_env_file  CC=2  out:3
  pyqual.custom_fix  [2 funcs]
    add_docstring  CC=6  out:11
    parse_and_apply_suggestions  CC=13  out:21
  pyqual.fix_tools  [1 funcs]
    get_available_tools  CC=5  out:9
  pyqual.gate_collectors.legacy  [2 funcs]
    _from_toon  CC=4  out:7
    _from_vallm  CC=6  out:10
  pyqual.gates  [1 funcs]
    _collect_metrics  CC=5  out:6
  pyqual.github_tasks  [1 funcs]
    fetch_github_tasks  CC=3  out:5
  pyqual.integrations.llx_mcp  [2 funcs]
    build_parser  CC=1  out:16
    main  CC=6  out:18
  pyqual.integrations.llx_mcp_service  [3 funcs]
    build_parser  CC=1  out:7
    main  CC=1  out:3
    run_server  CC=1  out:1
  pyqual.output  [1 funcs]
    _parse_output_line  CC=1  out:0
  pyqual.parallel  [3 funcs]
    run  CC=15  out:25
    parse_todo_items  CC=4  out:7
    run_parallel_fix  CC=7  out:16
  pyqual.pipeline  [4 funcs]
    _is_fix_stage  CC=6  out:2
    _iteration_stagnated  CC=8  out:1
    _log_stage  CC=12  out:8
    _resolve_tool_stage  CC=5  out:8
  pyqual.plugins  [2 funcs]
    get_available_plugins  CC=2  out:1
    install_plugin_config  CC=2  out:5
  pyqual.plugins._base  [2 funcs]
    get  CC=1  out:1
    list_plugins  CC=5  out:2
  pyqual.plugins.attack.__main__  [4 funcs]
    _ensure_dir  CC=1  out:1
    cmd_check  CC=2  out:10
    cmd_merge  CC=5  out:19
    main  CC=4  out:4
  pyqual.plugins.attack.main  [4 funcs]
    attack_check  CC=7  out:9
    attack_merge  CC=15  out:24
    auto_merge_pr  CC=6  out:7
    run_git_command  CC=5  out:3
  pyqual.plugins.cli_helpers  [4 funcs]
    plugin_add  CC=5  out:19
    plugin_info  CC=5  out:16
    plugin_list  CC=9  out:19
    plugin_search  CC=11  out:25
  pyqual.plugins.deps.main  [4 funcs]
    check_requirements  CC=15  out:16
    deps_health_check  CC=8  out:21
    get_dependency_tree  CC=10  out:7
    get_outdated_packages  CC=9  out:15
  pyqual.plugins.docker.main  [4 funcs]
    docker_security_check  CC=8  out:7
    get_image_info  CC=6  out:10
    run_hadolint  CC=9  out:6
    run_trivy_scan  CC=14  out:13
  pyqual.plugins.docs.main  [4 funcs]
    check_links  CC=8  out:7
    check_readme  CC=9  out:15
    docs_quality_summary  CC=5  out:12
    run_interrogate  CC=5  out:5
  pyqual.plugins.git.git_command  [1 funcs]
    run_git_command  CC=1  out:1
  pyqual.plugins.git.main  [14 funcs]
    _collect_scan_metrics  CC=4  out:16
    _get_provider_for_pattern  CC=1  out:1
    _get_severity_for_pattern  CC=1  out:1
    _is_likely_false_positive  CC=9  out:6
    _scan_with_gitleaks  CC=7  out:9
    _scan_with_patterns  CC=9  out:11
    _scan_with_trufflehog  CC=10  out:18
    git_add  CC=4  out:6
    git_commit  CC=12  out:9
    git_push  CC=17  out:22
  pyqual.plugins.git.status  [1 funcs]
    git_status  CC=18  out:20
  pyqual.profiles  [1 funcs]
    get_profile  CC=1  out:1
  pyqual.release_check  [2 funcs]
    _print_result  CC=14  out:10
    main  CC=4  out:15
  pyqual.report  [18 funcs]
    _badge_url  CC=1  out:2
    _build_project_badges  CC=11  out:20
    _build_quality_badges  CC=8  out:10
    _parse_pyproject_fallback  CC=4  out:5
    _read_costs_data  CC=3  out:4
    _read_costs_json  CC=6  out:5
    _read_costs_package  CC=12  out:17
    _read_git_commit_count  CC=3  out:4
    _read_pyproject  CC=5  out:4
    _read_version  CC=3  out:5
  pyqual.report_generator  [9 funcs]
    _build_gate  CC=1  out:1
    _build_gates_from_metrics  CC=3  out:2
    generate_ascii_diagram  CC=7  out:10
    generate_mermaid_diagram  CC=7  out:11
    generate_metrics_table  CC=5  out:11
    generate_report  CC=4  out:12
    generate_stage_details  CC=11  out:16
    get_last_run  CC=15  out:32
    main  CC=1  out:6
  pyqual.run_parallel_fix  [4 funcs]
    _setup_batch  CC=2  out:2
    get_todo_batch  CC=5  out:8
    main  CC=13  out:37
    parse_args  CC=1  out:7
  pyqual.setup_deps  [5 funcs]
    _check_cli  CC=1  out:2
    _check_pip  CC=5  out:7
    _install_pip  CC=2  out:1
    check_all  CC=5  out:5
    main  CC=10  out:8
  pyqual.stage_names  [5 funcs]
    get_stage_when_default  CC=1  out:2
    is_delivery_stage_name  CC=1  out:1
    is_fix_stage_name  CC=7  out:6
    is_verify_stage_name  CC=1  out:1
    normalize_stage_name  CC=1  out:2
  pyqual.tickets  [7 funcs]
    _load_sync_integration  CC=2  out:1
    _normalize_sources  CC=4  out:2
    sync_all_tickets  CC=1  out:2
    sync_from_gates  CC=9  out:8
    sync_github_tickets  CC=1  out:2
    sync_planfile_tickets  CC=2  out:6
    sync_todo_tickets  CC=1  out:2
  pyqual.tools  [12 funcs]
    _load_default_presets  CC=2  out:2
    _load_json_presets  CC=6  out:10
    _preset_from_dict  CC=1  out:3
    dump_presets_json  CC=5  out:5
    get_preset  CC=1  out:2
    list_presets  CC=1  out:2
    load_entry_point_presets  CC=8  out:15
    load_user_tools  CC=6  out:6
    preset_to_dict  CC=2  out:0
    register_custom_tools_from_yaml  CC=5  out:10
  pyqual.validation.config_check  [6 funcs]
    _get_issue_severity  CC=9  out:0
    _load_tool_registry  CC=3  out:4
    _load_yaml_config  CC=7  out:13
    _validate_gate  CC=3  out:6
    _validate_stage  CC=10  out:12
    validate_config  CC=9  out:14
  pyqual.validation.errors  [3 funcs]
    _classify_failure  CC=11  out:5
    _match_env_subtype  CC=3  out:1
    _match_fix_env_subtype  CC=5  out:2
  pyqual.validation.project  [2 funcs]
    _detect_language  CC=4  out:2
    detect_project_facts  CC=8  out:11
  pyqual.validation.release  [9 funcs]
    _bump_patch_version  CC=2  out:4
    _check_pypi_version  CC=6  out:4
    _parse_pyproject_fallback  CC=7  out:9
    _read_package_init_version  CC=3  out:5
    _read_project_metadata  CC=8  out:8
    _read_pyproject  CC=5  out:5
    _read_version_file  CC=3  out:3
    _resolve_release_version  CC=3  out:2
    validate_release_state  CC=22  out:33
  pyqual.validation.schema  [1 funcs]
    _resolve_gate_metric  CC=3  out:2
  pyqual.yaml_fixer  [8 funcs]
    _detect_bracket_issues  CC=9  out:14
    _detect_quote_issues  CC=8  out:18
    _get_context  CC=3  out:6
    _is_multiline_quote  CC=8  out:10
    _parse_pyyaml_error  CC=8  out:13
    _try_parse_yaml  CC=2  out:2
    analyze_yaml_syntax  CC=10  out:24
    fix_yaml_file  CC=3  out:5
  run_analysis  [2 funcs]
    main  CC=4  out:9
    run_project  CC=11  out:38

EDGES:
  dashboard.src.App.App → dashboard.src.App.loadRepositories
  dashboard.src.components.RepositoryDetail.RepositoryDetail → dashboard.src.components.RepositoryDetail.navigate
  dashboard.src.api.fetchRepositories → dashboard.src.api.loadConfig
  dashboard.src.api.fetchRepositories → dashboard.src.api.fetchLatestRun
  dashboard.src.api.config → dashboard.src.api.fetchLatestRun
  dashboard.src.api.repositories → dashboard.src.api.fetchLatestRun
  dashboard.src.api.fetchLatestRun → dashboard.src.api.getRepoPath
  dashboard.src.api.getRepoPath → dashboard.src.api.match
  dashboard.src.api.fetchRepositoriesWithFallback → dashboard.src.api.fetchRepositories
  run_analysis.run_project → pyqual.config.PyqualConfig.load
  run_analysis.main → run_analysis.run_project
  examples.integration_example.run_quality_check → pyqual.api.run_pipeline
  examples.integration_example.run_with_callbacks → pyqual.api.load_config
  examples.integration_example.run_with_callbacks → pyqual.api.run
  examples.integration_example.run_with_callbacks → pyqual.api.export_results_json
  examples.integration_example.check_prerequisites → pyqual.api.shell_check
  examples.integration_example.run_shell_command_example → pyqual.api.shell_check
  examples.integration_example.run_single_stage → pyqual.api.run_stage
  examples.integration_example.preview_pipeline → pyqual.api.dry_run
  examples.integration_example.preview_pipeline → pyqual.api.format_result_summary
  examples.integration_example.quick_gate_check → pyqual.api.load_config
  examples.integration_example.quick_gate_check → pyqual.api.check_gates
  examples.custom_gates.metric_history.save_snapshot → examples.custom_gates.metric_history.load_history
  examples.custom_gates.metric_history.main → examples.custom_gates.metric_history.save_snapshot
  examples.custom_gates.composite_gates.run_composite_check → examples.custom_gates.composite_gates.compute_composite_score
  examples.custom_gates.composite_gates.main → examples.custom_gates.composite_gates.run_composite_check
  dashboard.api.main.get_projects → dashboard.api.main.read_summary_json
  dashboard.api.main.get_latest_run → dashboard.api.main.read_summary_json
  dashboard.api.main.get_project_runs → dashboard.api.main.get_db_path
  dashboard.api.main.get_project_runs → dashboard.api.main.query_pipeline_db
  dashboard.api.main.get_project_runs → dashboard.api.main.safe_parse
  dashboard.api.main.get_metric_history → dashboard.api.main.get_db_path
  dashboard.api.main.get_metric_history → dashboard.api.main.query_pipeline_db
  dashboard.api.main.get_metric_history → dashboard.api.main.safe_parse
  dashboard.api.main.get_stage_performance → dashboard.api.main.get_db_path
  dashboard.api.main.get_stage_performance → dashboard.api.main.query_pipeline_db
  dashboard.api.main.get_stage_performance → dashboard.api.main.safe_parse
  dashboard.api.main.get_gate_status → dashboard.api.main.get_db_path
  dashboard.api.main.get_gate_status → dashboard.api.main.query_pipeline_db
  dashboard.api.main.get_gate_status → dashboard.api.main.safe_parse
  dashboard.api.main.get_project_summary → dashboard.api.main.get_db_path
  dashboard.api.main.get_project_summary → dashboard.api.main.query_pipeline_db
  dashboard.api.main.get_project_summary → dashboard.api.main.safe_parse
  examples.ticket_workflow.sync_tickets.sync_from_cli → pyqual.tickets.sync_github_tickets
  examples.ticket_workflow.sync_tickets.sync_from_cli → pyqual.tickets.sync_all_tickets
  examples.ticket_workflow.sync_tickets.sync_from_cli → pyqual.tickets.sync_todo_tickets
  examples.ticket_workflow.sync_tickets.tickets_from_gate_failures → pyqual.config.PyqualConfig.load
  examples.ticket_workflow.sync_tickets.tickets_from_gate_failures → pyqual.tickets.sync_todo_tickets
  examples.ticket_workflow.sync_tickets.main → examples.ticket_workflow.sync_tickets.sync_from_cli
  examples.ticket_workflow.sync_tickets.main → examples.ticket_workflow.sync_tickets.tickets_from_gate_failures
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 127f 21304L | python:111,typescript:12,shell:6,javascript:2 | 2026-04-19
# CC̄=4.9 | critical:16/755 | dups:0 | cycles:0

HEALTH[16]:
  🟡 CC    validate_release_state CC=22 (limit:15)
  🟡 CC    validate CC=19 (limit:15)
  🟡 CC    git_status CC=18 (limit:15)
  🟡 CC    git_status CC=18 (limit:15)
  🟡 CC    run CC=17 (limit:15)
  🟡 CC    git_push CC=17 (limit:15)
  🟡 CC    scan_for_secrets CC=17 (limit:15)
  🟡 CC    _execute_stage CC=16 (limit:15)
  🟡 CC    get_last_run CC=15 (limit:15)
  🟡 CC    run CC=15 (limit:15)
  🟡 CC    _from_radon CC=15 (limit:15)
  🟡 CC    attack_merge CC=15 (limit:15)
  🟡 CC    check_requirements CC=15 (limit:15)
  🟡 CC    _check_docs_folder CC=15 (limit:15)
  🟡 CC    preflight_push_check CC=15 (limit:15)
  🟡 CC    build_dashboard_table CC=15 (limit:15)

REFACTOR[1]:
  1. split 16 high-CC methods  (CC>15)

PIPELINES[401]:
  [1] Src [MetricsTrendChart]: MetricsTrendChart
      PURITY: 100% pure
  [2] Src [data]: data
      PURITY: 100% pure
  [3] Src [StagesChart]: StagesChart
      PURITY: 100% pure
  [4] Src [data]: data
      PURITY: 100% pure
  [5] Src [App]: App → loadRepositories
      PURITY: 100% pure

LAYERS:
  ./                              CC̄=7.5    ←in:0  →out:0
  │ run_analysis                87L  0C    2m  CC=11     ←0
  │ project.sh                  35L  0C    0m  CC=0.0    ←0
  │ SUGGESTED_COMMANDS.sh        4L  0C    0m  CC=0.0    ←0
  │
  pyqual/                         CC̄=5.1    ←in:37  →out:10  !! split
  │ !! main                       967L  1C   21m  CC=18     ←2
  │ !! _gate_collectors           705L  0C   27m  CC=15     ←2
  │ !! pipeline                   700L  1C   26m  CC=16     ←0
  │ !! report                     592L  0C   19m  CC=12     ←0
  │ !! bulk_init                  567L  1C   15m  CC=14     ←1
  │ !! api                        523L  1C   15m  CC=10     ←3
  │ main                       485L  1C   12m  CC=11     ←1
  │ !! main                       464L  1C   10m  CC=15     ←1
  │ main                       427L  1C   13m  CC=14     ←1
  │ !! report_generator           423L  2C   14m  CC=15     ←0
  │ yaml_fixer                 419L  3C   12m  CC=10     ←1
  │ cli_run_helpers            418L  0C   24m  CC=11     ←0
  │ main                       410L  1C   11m  CC=11     ←1
  │ test                       408L  6C   24m  CC=6      ←0
  │ run_parallel_fix           401L  0C   12m  CC=13     ←0
  │ builtin                    399L  7C   14m  CC=13     ←0
  │ !! main                       388L  1C   11m  CC=15     ←0
  │ cli_observe                381L  0C   15m  CC=11     ←0
  │ github_actions             357L  2C   16m  CC=9      ←0
  │ !! main                       354L  1C    9m  CC=15     ←3
  │ !! cmd_run                    337L  0C   11m  CC=17     ←0
  │ !! parallel                   328L  4C    7m  CC=15     ←1
  │ tools                      323L  1C   15m  CC=8      ←4
  │ cmd_git                    309L  0C    8m  CC=11     ←0
  │ !! release                    291L  0C    9m  CC=22     ←1
  │ cli_bulk_cmds              285L  0C    6m  CC=14     ←0
  │ config                     273L  4C    8m  CC=13     ←11
  │ !! cmd_config                 266L  0C    5m  CC=19     ←0
  │ config_check               259L  0C    7m  CC=10     ←0
  │ cmd_tune                   240L  0C    7m  CC=12     ←0
  │ main                       231L  0C    6m  CC=8      ←1
  │ custom_fix                 218L  0C    3m  CC=13     ←0
  │ auto_closer                217L  0C    7m  CC=11     ←0
  │ errors                     210L  4C    4m  CC=11     ←0
  │ profiles                   207L  1C    2m  CC=1      ←3
  │ test                       204L  5C   13m  CC=5      ←0
  │ gates                      197L  4C   11m  CC=9      ←0
  │ test                       197L  5C   14m  CC=6      ←0
  │ cli_helpers                193L  0C    7m  CC=11     ←1
  │ test                       185L  5C   13m  CC=6      ←0
  │ test                       180L  5C   12m  CC=7      ←0
  │ cmd_mcp                    176L  0C    4m  CC=12     ←0
  │ cmd_tickets                169L  0C    6m  CC=7      ←0
  │ bulk_init_fingerprint      168L  1C    9m  CC=10     ←1
  │ main                       164L  1C    6m  CC=13     ←0
  │ test                       159L  4C   11m  CC=4      ←0
  │ main                       157L  1C    6m  CC=14     ←0
  │ __init__                   154L  0C    0m  CC=0.0    ←0
  │ !! orchestrator               141L  1C    3m  CC=15     ←1
  │ test                       139L  1C    9m  CC=8      ←0
  │ setup_deps                 136L  1C    5m  CC=10     ←0
  │ llm                        126L  0C    0m  CC=0.0    ←0
  │ tickets                    123L  0C    7m  CC=9      ←3
  │ cli_log_helpers            117L  0C    3m  CC=14     ←0
  │ constants                  107L  0C    0m  CC=0.0    ←0
  │ test                       102L  2C    7m  CC=4      ←0
  │ release_check              101L  0C    2m  CC=14     ←0
  │ llx_mcp                    101L  0C    2m  CC=6      ←0
  │ __main__                    92L  0C    4m  CC=5      ←0
  │ cmd_info                    91L  0C    2m  CC=5      ←0
  │ !! status                      91L  0C    1m  CC=18     ←3
  │ schema                      91L  2C    2m  CC=3      ←1
  │ cmd_init                    90L  0C    2m  CC=7      ←0
  │ _base                       87L  3C    7m  CC=5      ←6
  │ __init__                    86L  0C    0m  CC=0.0    ←0
  │ __init__                    84L  0C    3m  CC=5      ←2
  │ legacy                      81L  0C    6m  CC=10     ←0
  │ main                        77L  1C    2m  CC=8      ←0
  │ llx_mcp_service             68L  0C    4m  CC=1      ←0
  │ github_tasks                64L  0C    3m  CC=6      ←1
  │ main                        62L  1C    3m  CC=4      ←1
  │ bulk_init_classify          61L  1C    1m  CC=8      ←1
  │ stage_names                 61L  0C    5m  CC=7      ←3
  │ project                     60L  0C    2m  CC=8      ←2
  │ models                      56L  2C    0m  CC=0.0    ←0
  │ parser                      55L  0C    3m  CC=7      ←0
  │ base                        53L  2C    5m  CC=2      ←0
  │ pipeline_results            52L  3C    0m  CC=0.0    ←0
  │ aider                       49L  1C    3m  CC=2      ←0
  │ __init__                    47L  0C    1m  CC=5      ←1
  │ pipeline_protocols          44L  6C    6m  CC=1      ←0
  │ cmd_plugin                  44L  0C    1m  CC=8      ←0
  │ __init__                    43L  0C    0m  CC=0.0    ←0
  │ llx                         36L  1C    4m  CC=2      ←0
  │ claude                      33L  1C    3m  CC=1      ←0
  │ runner                      32L  0C    1m  CC=11     ←1
  │ __init__                    28L  0C    0m  CC=0.0    ←0
  │ bulk_run                    26L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    13L  0C    0m  CC=0.0    ←0
  │ utils                       12L  0C    1m  CC=5      ←0
  │ git_command                 11L  0C    1m  CC=1      ←0
  │ __init__                    10L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __main__                     6L  0C    0m  CC=0.0    ←0
  │ output                       5L  0C    1m  CC=1      ←1
  │ command                      5L  0C    1m  CC=1      ←0
  │ analysis                     5L  0C    1m  CC=1      ←0
  │ __init__                     4L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │
  dashboard/                      CC̄=3.3    ←in:0  →out:0
  │ main                       340L  0C   13m  CC=6      ←0
  │ index.ts                   205L  0C   19m  CC=11     ←0
  │ App.tsx                    201L  0C    9m  CC=11     ←0
  │ RepositoryDetail.tsx       198L  1C   12m  CC=9      ←0
  │ Overview.tsx               175L  1C    5m  CC=12     ←0
  │ Settings.tsx               129L  0C    1m  CC=2      ←0
  │ MetricsChart.tsx            82L  1C    7m  CC=6      ←0
  │ index.ts                    62L  7C    0m  CC=0.0    ←0
  │ MetricsTrendChart.tsx       60L  1C    2m  CC=6      ←0
  │ constants                   57L  0C    0m  CC=0.0    ←0
  │ StagesChart.tsx             54L  1C    2m  CC=4      ←0
  │ vitest.config.ts            27L  0C    0m  CC=0.0    ←0
  │ vite.config.ts              20L  0C    0m  CC=0.0    ←0
  │ tailwind.config.js          11L  0C    0m  CC=0.0    ←0
  │ main.tsx                    10L  0C    0m  CC=0.0    ←0
  │ postcss.config.js            6L  0C    0m  CC=0.0    ←0
  │
  integration/                    CC̄=0.0    ←in:0  →out:0
  │ run_matrix.sh              211L  0C    3m  CC=0.0    ←0
  │ run_docker_matrix.sh         5L  0C    0m  CC=0.0    ←0
  │

COUPLING:
                                          pyqual              pyqual.cli          pyqual.plugins       pyqual.validation             pyqual.bulk  pyqual.gate_collectors            run_analysis
                  pyqual                      ──                     ←22                       3                       1                       6                      ←2                      ←1  hub
              pyqual.cli                      22                      ──                      13                       2                                                                          !! fan-out
          pyqual.plugins                       6                     ←13                      ──                      ←1                                                                          hub
       pyqual.validation                       5                      ←2                       1                      ──                                                                        
             pyqual.bulk                       1                                                                                              ──                                                  hub
  pyqual.gate_collectors                       2                                                                                                                      ──                        
            run_analysis                       1                                                                                                                                              ──
  CYCLES: none
  HUB: pyqual/ (fan-in=37)
  HUB: pyqual.bulk/ (fan-in=6)
  HUB: pyqual.plugins/ (fan-in=17)
  SMELL: pyqual.cli/ fan-out=37 → split needed
  SMELL: pyqual/ fan-out=10 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 10 groups | 114f 19182L | 2026-04-15

SUMMARY:
  files_scanned: 114
  total_lines:   19182
  dup_groups:    10
  dup_fragments: 29
  saved_lines:   155
  scan_ms:       13681

DUPLICATES[10] (ranked by impact):
  [969039c4ca2a3049] ! STRU  _display_comparison  L=40 N=2 saved=40 sim=1.00
      pyqual/cli/cmd_tune.py:158-197  (_display_comparison)
      pyqual/cli/main.py:151-188  (_display_comparison_for_tune)
  [0838ff986b9c2e82]   STRU  tickets_todo  L=11 N=3 saved=22 sim=1.00
      pyqual/cli/cmd_tickets.py:64-74  (tickets_todo)
      pyqual/cli/cmd_tickets.py:78-88  (tickets_github)
      pyqual/cli/cmd_tickets.py:92-102  (tickets_all)
  [96bfc15f5794cd81]   EXAC  get_config_example  L=3 N=8 saved=21 sim=1.00
      pyqual/plugins/attack/main.py:91-93  (get_config_example)
      pyqual/plugins/builtin.py:381-383  (get_config_example)
      pyqual/plugins/deps/main.py:214-216  (get_config_example)
      pyqual/plugins/docker/main.py:187-189  (get_config_example)
      pyqual/plugins/docs/main.py:216-218  (get_config_example)
      pyqual/plugins/example_plugin/main.py:55-57  (get_config_example)
      pyqual/plugins/git/main.py:200-202  (get_config_example)
      pyqual/plugins/security/main.py:177-179  (get_config_example)
  [67981de8f7d62bf4]   STRU  _apply_thresholds  L=17 N=2 saved=17 sim=1.00
      pyqual/cli/cmd_tune.py:205-221  (_apply_thresholds)
      pyqual/cli/main.py:191-204  (_apply_thresholds_for_tune)
  [adc53a6895c3c8e5]   STRU  sync_todo_tickets  L=7 N=3 saved=14 sim=1.00
      pyqual/tickets.py:49-55  (sync_todo_tickets)
      pyqual/tickets.py:58-64  (sync_github_tickets)
      pyqual/tickets.py:67-73  (sync_all_tickets)
  [e20172f0036c9a8e]   EXAC  _read_artifact_text  L=11 N=2 saved=11 sim=1.00
      pyqual/_gate_collectors.py:51-61  (_read_artifact_text)
      pyqual/gate_collectors/utils.py:3-12  (_read_artifact_text)
  [83d4e43f6248a283]   STRU  _from_code_health  L=11 N=2 saved=11 sim=1.00
      pyqual/_gate_collectors.py:310-320  (_from_code_health)
      pyqual/_gate_collectors.py:495-505  (_from_lint)
  [5a6d760035a8c5b8]   STRU  _print_history_prompts  L=10 N=2 saved=10 sim=1.00
      pyqual/cli_observe.py:299-308  (_print_history_prompts)
      pyqual/cli_observe.py:311-320  (_print_history_stdout)
  [a02d766eee4a1879]   STRU  get_timeout  L=3 N=3 saved=6 sim=1.00
      pyqual/fix_tools/aider.py:47-49  (get_timeout)
      pyqual/fix_tools/claude.py:31-33  (get_timeout)
      pyqual/fix_tools/llx.py:34-36  (get_timeout)
  [f8d1d8d43a0875d6]   STRU  list_profiles  L=3 N=2 saved=3 sim=1.00
      pyqual/profiles.py:205-207  (list_profiles)
      pyqual/tools.py:144-146  (list_presets)

REFACTOR[10] (ranked by priority):
  [1] ◐ extract_function   → pyqual/cli/utils/_display_comparison.py
      WHY: 2 occurrences of 40-line block across 2 files — saves 40 lines
      FILES: pyqual/cli/cmd_tune.py, pyqual/cli/main.py
  [2] ○ extract_function   → pyqual/cli/utils/tickets_todo.py
      WHY: 3 occurrences of 11-line block across 1 files — saves 22 lines
      FILES: pyqual/cli/cmd_tickets.py
  [3] ○ extract_function   → pyqual/plugins/utils/get_config_example.py
      WHY: 8 occurrences of 3-line block across 8 files — saves 21 lines
      FILES: pyqual/plugins/attack/main.py, pyqual/plugins/builtin.py, pyqual/plugins/deps/main.py, pyqual/plugins/docker/main.py, pyqual/plugins/docs/main.py +3 more
  [4] ○ extract_function   → pyqual/cli/utils/_apply_thresholds.py
      WHY: 2 occurrences of 17-line block across 2 files — saves 17 lines
      FILES: pyqual/cli/cmd_tune.py, pyqual/cli/main.py
  [5] ○ extract_function   → pyqual/utils/sync_todo_tickets.py
      WHY: 3 occurrences of 7-line block across 1 files — saves 14 lines
      FILES: pyqual/tickets.py
  [6] ○ extract_function   → pyqual/utils/_read_artifact_text.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: pyqual/_gate_collectors.py, pyqual/gate_collectors/utils.py
  [7] ○ extract_function   → pyqual/utils/_from_code_health.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: pyqual/_gate_collectors.py
  [8] ○ extract_function   → pyqual/utils/_print_history_prompts.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: pyqual/cli_observe.py
  [9] ○ extract_function   → pyqual/fix_tools/utils/get_timeout.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: pyqual/fix_tools/aider.py, pyqual/fix_tools/claude.py, pyqual/fix_tools/llx.py
  [10] ○ extract_function   → pyqual/utils/list_profiles.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: pyqual/profiles.py, pyqual/tools.py

METRICS-TARGET:
  dup_groups:  10 → 0
  saved_lines: 155 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 729 func | 95f | 2026-04-19

NEXT[10] (ranked by impact):
  [1] !! SPLIT           pyqual/plugins/git/main.py
      WHY: 967L, 1 classes, max CC=18
      EFFORT: ~4h  IMPACT: 17406

  [2] !! SPLIT           pyqual/pipeline.py
      WHY: 700L, 1 classes, max CC=16
      EFFORT: ~4h  IMPACT: 11200

  [3] !! SPLIT           pyqual/_gate_collectors.py
      WHY: 705L, 0 classes, max CC=15
      EFFORT: ~4h  IMPACT: 10575

  [4] !  SPLIT-FUNC      run  CC=17  fan=26
      WHY: CC=17 exceeds 15
      EFFORT: ~1h  IMPACT: 442

  [5] !  SPLIT-FUNC      get_last_run  CC=15  fan=26
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 390

  [6] !  SPLIT-FUNC      validate_release_state  CC=22  fan=16
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 352

  [7] !  SPLIT-FUNC      git_status  CC=18  fan=16
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 288

  [8] !  SPLIT-FUNC      git_status  CC=18  fan=16
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 288

  [9] !  SPLIT-FUNC      ParallelExecutor.run  CC=15  fan=17
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 255

  [10] !  SPLIT-FUNC      Pipeline._execute_stage  CC=16  fan=14
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 224


RISKS[3]:
  ⚠ Splitting pyqual/plugins/git/main.py may break 21 import paths
  ⚠ Splitting pyqual/_gate_collectors.py may break 27 import paths
  ⚠ Splitting pyqual/pipeline.py may break 26 import paths

METRICS-TARGET:
  CC̄:          4.9 → ≤3.4
  max-CC:      22 → ≤11
  god-modules: 7 → 0
  high-CC(≥15): 16 → ≤8
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=5.1 → now CC̄=4.9
```

### Validation (`project/validation.toon.yaml`)

```toon markpact:analysis path=project/validation.toon.yaml
# vallm batch | 375f | 216✓ 17⚠ 29✗ | 2026-04-15

SUMMARY:
  scanned: 375  passed: 216 (57.6%)  warnings: 17  errors: 29  unsupported: 130

WARNINGS[17]{path,score}:
  dashboard/vite.config.ts,0.83
    issues[1]{rule,severity,message,line}:
      js.import.resolvable,warning,Module 'vite' not found,1
  dashboard/vitest.config.ts,0.89
    issues[1]{rule,severity,message,line}:
      js.import.resolvable,warning,Module 'vitest/config' not found,1
  pyqual/plugins/git/main.py,0.90
    issues[7]{rule,severity,message,line}:
      complexity.cyclomatic,warning,git_status has cyclomatic complexity 18 (max: 15),238
      complexity.cyclomatic,warning,git_push has cyclomatic complexity 17 (max: 15),415
      complexity.cyclomatic,warning,scan_for_secrets has cyclomatic complexity 17 (max: 15),614
      complexity.maintainability,warning,Low maintainability index: 17.5 (threshold: 20),
      complexity.lizard_cc,warning,git_status: CC=18 exceeds limit 15,238
      complexity.lizard_cc,warning,git_push: CC=17 exceeds limit 15,415
      complexity.lizard_cc,warning,scan_for_secrets: CC=17 exceeds limit 15,614
  dashboard/src/components/Overview.tsx,0.93
    issues[2]{rule,severity,message,line}:
      complexity.lizard_cc,warning,Overview: CC=23 exceeds limit 15,16
      complexity.lizard_length,warning,Overview: 132 lines exceeds limit 100,16
  pyqual/validation/release.py,0.93
    issues[3]{rule,severity,message,line}:
      complexity.cyclomatic,warning,validate_release_state has cyclomatic complexity 22 (max: 15),151
      complexity.lizard_cc,warning,validate_release_state: CC=21 exceeds limit 15,151
      complexity.lizard_length,warning,validate_release_state: 121 lines exceeds limit 100,151
  pyqual/pipeline.py,0.96
    issues[3]{rule,severity,message,line}:
      complexity.cyclomatic,warning,_execute_stage has cyclomatic complexity 16 (max: 15),292
      complexity.maintainability,warning,Low maintainability index: 10.3 (threshold: 20),
      complexity.lizard_cc,warning,_execute_stage: CC=16 exceeds limit 15,292
  test_pyqual.py,0.96
    issues[2]{rule,severity,message,line}:
      complexity.cyclomatic,warning,test_pipeline_writes_nfo_sqlite_log has cyclomatic complexity 17 (max: 15),392
      complexity.maintainability,warning,Low maintainability index: 14.1 (threshold: 20),
  dashboard/src/App.tsx,0.97
    issues[1]{rule,severity,message,line}:
      complexity.lizard_length,warning,App: 114 lines exceeds limit 100,16
  dashboard/src/components/Settings.tsx,0.97
    issues[1]{rule,severity,message,line}:
      complexity.lizard_length,warning,Settings: 110 lines exceeds limit 100,4
  integration/run_matrix.sh,0.97
    issues[1]{rule,severity,message,line}:
      complexity.lizard_length,warning,run_case: 170 lines exceeds limit 100,11
  pyqual/cli/cmd_config.py,0.97
    issues[2]{rule,severity,message,line}:
      complexity.cyclomatic,warning,validate has cyclomatic complexity 19 (max: 15),54
      complexity.lizard_cc,warning,validate: CC=19 exceeds limit 15,54
  pyqual/plugins/git/status.py,0.97
    issues[2]{rule,severity,message,line}:
      complexity.cyclomatic,warning,git_status has cyclomatic complexity 18 (max: 15),10
      complexity.lizard_cc,warning,git_status: CC=18 exceeds limit 15,10
  pyqual/_gate_collectors.py,0.98
    issues[1]{rule,severity,message,line}:
      complexity.maintainability,warning,Low maintainability index: 4.2 (threshold: 20),
  pyqual/cli/cmd_run.py,0.98
    issues[1]{rule,severity,message,line}:
      complexity.cyclomatic,warning,run has cyclomatic complexity 17 (max: 15),224
  pyqual/cli_run_helpers.py,0.98
    issues[1]{rule,severity,message,line}:
      complexity.maintainability,warning,Low maintainability index: 19.7 (threshold: 20),
  tests/pipeline_test.py,0.98
    issues[1]{rule,severity,message,line}:
      complexity.cyclomatic,warning,test_pipeline_writes_nfo_sqlite_log has cyclomatic complexity 17 (max: 15),6
  tests/test_pipeline.py,0.98
    issues[1]{rule,severity,message,line}:
      complexity.cyclomatic,warning,test_pipeline_writes_nfo_sqlite_log has cyclomatic complexity 17 (max: 15),9

ERRORS[29]{path,score}:
  .pyqual/attack_merge.json,0.00
    issues[1]{rule,severity,message,line}:
      syntax.tree_sitter,error,tree-sitter found 6 parse error(s) in json,
  dashboard/api/main.py,0.85
    issues[5]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'fastapi' not found,1
      python.import.resolvable,error,Module 'fastapi.middleware.cors' not found,2
      python.import.resolvable,error,Module 'fastapi.staticfiles' not found,3
      python.import.resolvable,error,Module 'fastapi.security' not found,4
      python.import.resolvable,error,Module 'dashboard.constants' not found,14
  pyqual/integrations/llx_mcp.py,0.86
    issues[3]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'llx.mcp.client' not found,15
      python.import.resolvable,error,Module 'llx.mcp.workflows' not found,16
      python.import.resolvable,error,Module 'llx.utils.issues' not found,23
  tests/test_profiles_module.py,0.86
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,5
  pyqual/integrations/llx_mcp_service.py,0.89
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'llx.mcp.service' not found,13
  tests/test_bulk_init_pkg/test_fixtures.py,0.89
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,6
  tests/test_cli_run_helpers.py,0.89
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,7
  tests/test_secrets_collector.py,0.89
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,6
  pyqual/plugins/deps/test.py,0.91
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
  pyqual/plugins/docker/test.py,0.91
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
  pyqual/plugins/docs/test.py,0.91
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
  pyqual/plugins/documentation/test.py,0.91
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
  tests/test_profiles.py,0.91
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,6
  pyqual/auto_closer.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'planfile.core.models' not found,157
  pyqual/llm.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'llx.llm' not found,12
  pyqual/plugins/example_plugin/test.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,12
  pyqual/plugins/security/test.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,9
  tests/test_bulk_init.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,9
  tests/test_github_actions.py,0.94
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,10
  pyqual/plugins/attack/test.py,0.95
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,10
  pyqual/plugins/git/test.py,0.95
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,14
  tests/test_bulk_run.py,0.95
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
  tests/test_llx_mcp.py,0.95
    issues[2]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,8
      python.import.resolvable,error,Module 'llx.mcp.workflows' not found,13
  tests/test_pyqual.py,0.95
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,7
  pyqual/__init__.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'llx.llm' not found,54
  tests/test_pipeline_stages.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,10
  tests/test_release_validation.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,12
  tests/test_runtime_errors.py,0.96
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,10
  tests/test_tickets.py,0.97
    issues[1]{rule,severity,message,line}:
      python.import.resolvable,error,Module 'pytest' not found,7

UNSUPPORTED[5]{bucket,count}:
  *.md,63
  Dockerfile*,2
  *.txt,13
  *.yml,3
  other,49
```

## Intent

Declarative quality gate loops for AI-assisted development
