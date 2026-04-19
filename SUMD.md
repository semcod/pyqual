# pyqual

Declarative quality gate loops for AI-assisted development

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Interfaces](#interfaces)
- [Workflows](#workflows)
- [Quality Pipeline (`pyqual.yaml`)](#quality-pipeline-pyqualyaml)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Release Management (`goal.yaml`)](#release-management-goalyaml)
- [Makefile Targets](#makefile-targets)
- [Code Analysis](#code-analysis)
- [Source Map](#source-map)
- [Call Graph](#call-graph)
- [Intent](#intent)

## Metadata

- **name**: `pyqual`
- **version**: `0.1.140`
- **python_requires**: `>=3.9`
- **license**: Apache-2.0
- **ai_model**: `openrouter/x-ai/grok-code-fast-1`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, app.doql.css, pyqual.yaml, goal.yaml, .env.example, src(36 mod), project/(2 analysis files)

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

## Interfaces

### CLI Entry Points

- `pyqual`

## Workflows

### Taskfile Tasks (`Taskfile.yml`)

```yaml markpact:taskfile path=Taskfile.yml
version: '1'
name: pyqual
description: Minimal Taskfile
variables:
  APP_NAME: pyqual
environments:
  local:
    container_runtime: docker
    compose_command: docker compose
pipeline:
  python_version: "3.12"
  runner_image: ubuntu-latest
  branches: [main]
  cache: [~/.cache/pip]
  artifacts: [dist/]

  stages:
    - name: lint
      tasks: [lint]

    - name: test
      tasks: [test]

    - name: build
      tasks: [build]
      when: "branch:main"

tasks:
  install:
    desc: Install Python dependencies (editable)
    cmds:
    - pip install -e .[dev]
  test:
    desc: Run pytest suite
    cmds:
    - pytest -q
  lint:
    desc: Run ruff lint check
    cmds:
    - ruff check .
  fmt:
    desc: Auto-format with ruff
    cmds:
    - ruff format .
  build:
    desc: Build wheel + sdist
    cmds:
    - python -m build
  clean:
    desc: Remove build artefacts
    cmds:
    - rm -rf build/ dist/ *.egg-info
  help:
    desc: '[imported from Makefile] help'
    cmds:
    - echo "Available targets:"
    - echo "  install      Install the package"
    - echo "  install-dev  Install the package with dev dependencies"
    - echo "  test         Run tests"
    - echo "  lint         Run linting"
    - echo "  format       Format code"
    - echo "  clean        Clean build artifacts"
    - echo "  build        Build the package"
    - echo "  bump-patch   Bump patch version (0.1.2 -> 0.1.3)"
    - echo "  bump-minor   Bump minor version (0.1.2 -> 0.2.0)"
    - echo "  publish      Bump version, build and publish to PyPI"
    - echo "  upload       Upload to PyPI (alias for publish)"
  install-dev:
    desc: '[imported from Makefile] install-dev'
    cmds:
    - pip3 install -e ".[dev]"
  format:
    desc: '[imported from Makefile] format'
    cmds:
    - ruff format .
  bump-patch:
    desc: '[imported from Makefile] bump-patch'
    cmds:
    - echo "Bumping patch version..."
    - CURRENT=$$(cat VERSION); \
    - MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
    - MINOR=$$(echo $$CURRENT | cut -d. -f2); \
    - PATCH=$$(echo $$CURRENT | cut -d. -f3); \
    - NEW_PATCH=$$((PATCH + 1)); \
    - NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
    - echo "$$NEW_VERSION" > VERSION; \
    - sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml;
      \
    - 'echo "Version bumped: $$CURRENT -> $$NEW_VERSION"'
  bump-minor:
    desc: '[imported from Makefile] bump-minor'
    cmds:
    - echo "Bumping minor version..."
    - CURRENT=$$(cat VERSION); \
    - MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
    - MINOR=$$(echo $$CURRENT | cut -d. -f2); \
    - NEW_MINOR=$$((MINOR + 1)); \
    - NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
    - echo "$$NEW_VERSION" > VERSION; \
    - sed -i "s/version = \"$$CURRENT\"/version = \"$$NEW_VERSION\"/" pyproject.toml;
      \
    - 'echo "Version bumped: $$CURRENT -> $$NEW_VERSION"'
  publish:
    desc: '[imported from Makefile] publish'
    cmds:
    - python3 -m twine upload dist/* --skip-existing
    deps:
    - bump-patch
    - build
  upload:
    desc: '[imported from Makefile] upload'
    deps:
    - publish
  health:
    desc: '[from doql] workflow: health'
    cmds:
    - docker compose ps
    - docker compose exec app echo "Health check passed"
  import-makefile-hint:
    desc: '[from doql] workflow: import-makefile-hint'
    cmds:
    - 'echo ''Run: taskfile import Makefile to import existing targets.'''
  all:
    desc: Run install, lint, test
    cmds:
    - taskfile run install
    - taskfile run lint
    - taskfile run test
```

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

## Configuration

```yaml
project:
  name: pyqual
  version: 0.1.140
  env: local
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

## Deployment

```bash markpact:run
pip install pyqual

# development install
pip install -e .[dev]
```

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `*(not set)*` | Required: OpenRouter API key (https://openrouter.ai/keys) |
| `PFIX_MODEL` | `openrouter/qwen/qwen3-coder-next` | Model (default: openrouter/qwen/qwen3-coder-next) |
| `PFIX_AUTO_APPLY` | `true` | true = apply fixes without asking |
| `PFIX_AUTO_INSTALL_DEPS` | `true` | true = auto pip/uv install |
| `PFIX_AUTO_RESTART` | `false` | true = os.execv restart after fix |
| `PFIX_MAX_RETRIES` | `3` |  |
| `PFIX_DRY_RUN` | `false` |  |
| `PFIX_ENABLED` | `true` |  |
| `PFIX_GIT_COMMIT` | `false` | true = auto-commit fixes |
| `PFIX_GIT_PREFIX` | `pfix:` | commit message prefix |
| `PFIX_CREATE_BACKUPS` | `false` | false = disable .pfix_backups/ directory |

## Release Management (`goal.yaml`)

- **versioning**: `semver`
- **commits**: `conventional` scope=`pyqual`
- **changelog**: `keep-a-changelog`
- **build strategies**: `python`, `nodejs`, `rust`
- **version files**: `VERSION`, `pyproject.toml:version`, `pyqual/__init__.py:__version__`

## Makefile Targets

- `help` — Default target
- `install` — Install the package
- `install-dev` — Install with dev dependencies
- `test` — Run tests
- `lint` — Run linting
- `format` — Format code
- `clean` — Clean build artifacts
- `build` — Build the package
- `bump-patch` — Bump patch version (0.1.2 -> 0.1.3)
- `bump-minor` — Bump minor version (0.1.2 -> 0.2.0)
- `publish` — Build and publish to PyPI (auto-bumps patch version, skips if version exists)
- `upload` — Upload to PyPI (alias)

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# pyqual | 118f 19682L | shell:4,javascript:2,typescript:11,python:101 | 2026-04-19
# stats: 625 func | 0 cls | 118 mod | CC̄=5.1 | critical:16 | cycles:0
# alerts[5]: fan-out get_last_run=26; fan-out run=26; fan-out fix_config=23; fan-out main=21; CC validate_release_state=22
# hotspots[5]: get_last_run fan=26; run fan=26; fix_config fan=23; main fan=21; run_project fan=19
# evolution: CC̄ 5.1→5.1 (flat 0.0)
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[118]:
  SUGGESTED_COMMANDS.sh,4
  dashboard/api/main.py,340
  dashboard/constants.py,57
  dashboard/postcss.config.js,6
  dashboard/src/App.tsx,201
  dashboard/src/api/index.ts,205
  dashboard/src/components/MetricsChart.tsx,82
  dashboard/src/components/MetricsTrendChart.tsx,60
  dashboard/src/components/Overview.tsx,175
  dashboard/src/components/RepositoryDetail.tsx,198
  dashboard/src/components/Settings.tsx,129
  dashboard/src/components/StagesChart.tsx,54
  dashboard/src/main.tsx,10
  dashboard/src/types/index.ts,62
  dashboard/tailwind.config.js,11
  dashboard/vite.config.ts,20
  integration/run_docker_matrix.sh,5
  integration/run_matrix.sh,211
  project.sh,35
  pyqual/__init__.py,154
  pyqual/__main__.py,6
  pyqual/_gate_collectors.py,705
  pyqual/analysis.py,5
  pyqual/api.py,523
  pyqual/auto_closer.py,217
  pyqual/bulk/models.py,56
  pyqual/bulk/orchestrator.py,141
  pyqual/bulk/parser.py,55
  pyqual/bulk/runner.py,32
  pyqual/bulk_init.py,567
  pyqual/bulk_init_classify.py,61
  pyqual/bulk_init_fingerprint.py,168
  pyqual/bulk_run.py,26
  pyqual/cli/__init__.py,43
  pyqual/cli/cmd_config.py,266
  pyqual/cli/cmd_git.py,309
  pyqual/cli/cmd_info.py,91
  pyqual/cli/cmd_init.py,90
  pyqual/cli/cmd_mcp.py,176
  pyqual/cli/cmd_plugin.py,44
  pyqual/cli/cmd_run.py,337
  pyqual/cli/cmd_tickets.py,169
  pyqual/cli/cmd_tune.py,240
  pyqual/cli/main.py,231
  pyqual/cli_bulk_cmds.py,285
  pyqual/cli_log_helpers.py,117
  pyqual/cli_observe.py,381
  pyqual/cli_run_helpers.py,418
  pyqual/command.py,5
  pyqual/config.py,273
  pyqual/constants.py,107
  pyqual/custom_fix.py,218
  pyqual/fix_tools/__init__.py,47
  pyqual/fix_tools/aider.py,49
  pyqual/fix_tools/base.py,53
  pyqual/fix_tools/claude.py,33
  pyqual/fix_tools/llx.py,36
  pyqual/gate_collectors/__init__.py,4
  pyqual/gate_collectors/legacy.py,81
  pyqual/gate_collectors/utils.py,12
  pyqual/gates.py,197
  pyqual/github_actions.py,357
  pyqual/github_tasks.py,64
  pyqual/integrations/__init__.py,1
  pyqual/integrations/llx_mcp.py,101
  pyqual/integrations/llx_mcp_service.py,68
  pyqual/llm.py,126
  pyqual/output.py,5
  pyqual/parallel.py,328
  pyqual/pipeline.py,700
  pyqual/pipeline_protocols.py,44
  pyqual/pipeline_results.py,52
  pyqual/plugins/__init__.py,84
  pyqual/plugins/_base.py,87
  pyqual/plugins/attack/__init__.py,22
  pyqual/plugins/attack/__main__.py,92
  pyqual/plugins/attack/main.py,354
  pyqual/plugins/builtin.py,399
  pyqual/plugins/cli_helpers.py,193
  pyqual/plugins/code_health/__init__.py,7
  pyqual/plugins/code_health/main.py,157
  pyqual/plugins/coverage/__init__.py,7
  pyqual/plugins/coverage/main.py,77
  pyqual/plugins/deps/__init__.py,22
  pyqual/plugins/deps/main.py,464
  pyqual/plugins/docker/__init__.py,22
  pyqual/plugins/docker/main.py,427
  pyqual/plugins/docs/__init__.py,22
  pyqual/plugins/docs/main.py,485
  pyqual/plugins/documentation/__init__.py,10
  pyqual/plugins/documentation/main.py,388
  pyqual/plugins/example_plugin/__init__.py,13
  pyqual/plugins/example_plugin/main.py,62
  pyqual/plugins/git/__init__.py,28
  pyqual/plugins/git/git_command.py,11
  pyqual/plugins/git/main.py,967
  pyqual/plugins/git/status.py,91
  pyqual/plugins/lint/__init__.py,7
  pyqual/plugins/lint/main.py,164
  pyqual/plugins/security/__init__.py,22
  pyqual/plugins/security/main.py,410
  pyqual/profiles.py,207
  pyqual/release_check.py,101
  pyqual/report.py,571
  pyqual/report_generator.py,423
  pyqual/run_parallel_fix.py,401
  pyqual/setup_deps.py,136
  pyqual/stage_names.py,61
  pyqual/tickets.py,123
  pyqual/tools.py,323
  pyqual/validation/__init__.py,86
  pyqual/validation/config_check.py,259
  pyqual/validation/errors.py,210
  pyqual/validation/project.py,60
  pyqual/validation/release.py,291
  pyqual/validation/schema.py,91
  pyqual/yaml_fixer.py,419
  run_analysis.py,87
D:
  pyqual/validation/release.py:
    e: _read_pyproject,_parse_pyproject_fallback,_read_version_file,_read_package_init_version,_read_project_metadata,_bump_patch_version,_resolve_release_version,_check_pypi_version,validate_release_state
    _read_pyproject(workdir)
    _parse_pyproject_fallback(path)
    _read_version_file(workdir)
    _read_package_init_version(workdir;package_name)
    _read_project_metadata(workdir)
    _bump_patch_version(version)
    _resolve_release_version(base_version;bump_patch)
    _check_pypi_version(package_name;version)
    validate_release_state(workdir;registry;bump_patch)
  pyqual/cli/cmd_config.py:
    e: gates,validate,fix_config,status,report
    gates(config;workdir)
    validate(config;workdir;strict;fix)
    fix_config(config;workdir;dry_run;model)
    status(config;workdir)
    report(config;workdir;readme)
  pyqual/plugins/git/status.py:
    e: git_status
    git_status(cwd)
  pyqual/plugins/git/main.py:
    e: GitCollector,_count_by_severity,run_git_command,git_status,git_commit,git_push,git_add,scan_for_secrets,_scan_with_trufflehog,_scan_with_gitleaks,_scan_with_patterns,_is_likely_false_positive,_get_provider_for_pattern,_get_severity_for_pattern,preflight_push_check
    GitCollector(MetricCollector): collect(1),_collect_scan_metrics(2),_collect_preflight_metrics(2),_collect_status_metrics(2),_collect_push_metrics(2),_collect_commit_metrics(2),get_config_example(0)  # Git repository operations collector — status, commit, push w...
    _count_by_severity(secrets)
    run_git_command(args;cwd;check;capture_output)
    git_status(cwd)
    git_commit(message;cwd;add_all;only_if_changed)
    git_push(cwd;remote;branch;force;force_with_lease)
    git_add(paths;cwd)
    scan_for_secrets(paths;cwd;use_trufflehog;use_gitleaks;use_patterns)
    _scan_with_trufflehog(paths;cwd)
    _scan_with_gitleaks(paths;cwd)
    _scan_with_patterns(paths;cwd)
    _is_likely_false_positive(match;pattern_name;line)
    _get_provider_for_pattern(pattern_name)
    _get_severity_for_pattern(pattern_name)
    preflight_push_check(cwd;remote;branch;scan_secrets;dry_run)
  pyqual/cli/cmd_run.py:
    e: _emit,_emit_yaml_items,_build_stage_dict,_build_gate_dict,_handle_config_env_error,_handle_llm_error,_handle_pipeline_error,_run_auto_fix_config,_on_stage_error_impl,_create_tickets_if_needed,run
    _emit(text)
    _emit_yaml_items(items;indent)
    _build_stage_dict(result;workdir)
    _build_gate_dict(gate;op_sym)
    _handle_config_env_error(failure;config_path;console;auto_fix)
    _handle_llm_error(failure;console)
    _handle_pipeline_error(failure;console)
    _run_auto_fix_config(cfg_path;console;diag)
    _on_stage_error_impl(failure;config_path;console;auto_fix_config)
    _create_tickets_if_needed(result_final_passed;cfg;workdir;console)
    run(config;dry_run;workdir;verbose;stream;auto_fix_config)
  pyqual/pipeline.py:
    e: Pipeline
    Pipeline: __init__(9),run(1),check_gates(0),_run_iteration(2),_iteration_stagnated(0),_should_run_stage(4),_resolve_tool_stage(1),_resolve_env(0),_check_optional_binary(0),_make_skipped_result(2),_make_dry_run_result(2),_execute_stage(2),_notify_stage_error(3),_execute_captured(5),_execute_streaming(5),_init_nfo(0),_nfo_emit(4),_is_fix_stage(1),_log_stage(2),_archive_llx_report(2),_log_gates(2),_log_event(1),_ensure_pyqual_dir(0),_capture_runtime_error(2),_classify_error(1),_extract_error_message(1)  # Execute pipeline stages in a loop until quality gates pass...
  pyqual/report_generator.py:
    e: StageResult,PipelineRun,parse_kwargs,_should_skip_stage,_get_stage_status,_extract_metrics_from_kwargs,_read_coverage_from_file,_build_gate,_build_gates_from_metrics,get_last_run,generate_mermaid_diagram,generate_ascii_diagram,generate_metrics_table,generate_stage_details,generate_report,main
    StageResult:
    PipelineRun:
    parse_kwargs(kwargs_str)
    _should_skip_stage(stage_name)
    _get_stage_status(kwargs)
    _extract_metrics_from_kwargs(kwargs)
    _read_coverage_from_file(db_path)
    _build_gate(metric;value;threshold;operator)
    _build_gates_from_metrics(metrics)
    get_last_run(db_path)
    generate_mermaid_diagram(run)
    generate_ascii_diagram(run)
    generate_metrics_table(run)
    generate_stage_details(run)
    generate_report(workdir)
    main()
  pyqual/parallel.py:
    e: FixTool,TaskResult,ParallelRunResult,ParallelExecutor,parse_todo_items,group_similar_issues,run_parallel_fix
    FixTool:  # Configuration for a single fix tool...
    TaskResult:  # Result of processing a single task...
    ParallelRunResult:  # Result of parallel execution...
    ParallelExecutor: __init__(4),_run_tool_task(3),_tool_worker(1),run(2)  # Executes tasks across multiple fix tools in parallel...
    parse_todo_items(todo_path)
    group_similar_issues(issues;max_group_size)
    run_parallel_fix(workdir;tools;todo_path;issues;env;group_similar;on_task_done)
  pyqual/_gate_collectors.py:
    e: _read_artifact_text,_from_toon,_from_vallm,_from_coverage,_from_bandit,_from_secrets,_count_by_severity,_from_vulnerabilities,_from_security,_from_sbom,_from_vulture,_from_pyroma,_from_code_health,_from_git_health,_from_llm_quality,_from_ai_cost,_from_benchmark,_from_memory_profile,_from_radon,_from_mypy,_from_lint,_from_ruff,_count_pylint_by_type,_from_pylint,_from_flake8,_from_runtime_errors,_from_interrogate
    _read_artifact_text(workdir;filenames)
    _from_toon(workdir)
    _from_vallm(workdir)
    _from_coverage(workdir)
    _from_bandit(workdir)
    _from_secrets(workdir)
    _count_by_severity(items;severity)
    _from_vulnerabilities(workdir)
    _from_security(workdir)
    _from_sbom(workdir)
    _from_vulture(workdir)
    _from_pyroma(workdir)
    _from_code_health(workdir)
    _from_git_health(workdir)
    _from_llm_quality(workdir)
    _from_ai_cost(workdir)
    _from_benchmark(workdir)
    _from_memory_profile(workdir)
    _from_radon(workdir)
    _from_mypy(workdir)
    _from_lint(workdir)
    _from_ruff(workdir)
    _count_pylint_by_type(messages;type_name;symbol_prefix)
    _from_pylint(workdir)
    _from_flake8(workdir)
    _from_runtime_errors(workdir)
    _from_interrogate(workdir)
  pyqual/plugins/attack/main.py:
    e: AttackCollector,run_git_command,attack_check,attack_merge,auto_merge_pr
    AttackCollector(MetricCollector): collect(1),_collect_check_metrics(2),_collect_merge_metrics(2),_strategy_to_int(0),get_config_example(0)  # Attack merge collector — automerge with aggressive conflict ...
    run_git_command(args;cwd;check)
    attack_check(cwd)
    attack_merge(strategy;cwd;dry_run)
    auto_merge_pr(pr_number;branch;cwd)
  pyqual/plugins/deps/main.py:
    e: DepsCollector,get_outdated_packages,get_dependency_tree,check_requirements,deps_health_check
    DepsCollector(MetricCollector): collect(1),_collect_outdated(2),_collect_deptree(2),_collect_requirements(2),_collect_licenses(2),get_config_example(0)  # Dependency management metrics collector...
    get_outdated_packages(cwd)
    get_dependency_tree(cwd)
    check_requirements(req_file;cwd)
    deps_health_check(cwd)
  pyqual/plugins/documentation/main.py:
    e: DocumentationCollector
    DocumentationCollector(MetricCollector): _find_file(2),_check_file_exists(2),_read_pyproject(1),_parse_pyproject_fallback(1),_check_pyproject_metadata(1),_analyze_readme(1),_check_docs_folder(1),_check_required_files(1),_get_docstring_coverage(1),_check_license_type(1),collect(1)  # Documentation completeness and quality metrics.

Measures:
-...
  pyqual/bulk/orchestrator.py:
    e: BulkRunResult,discover_projects,build_dashboard_table,bulk_run
    BulkRunResult:
    discover_projects(root)
    build_dashboard_table(states;show_last_line)
    bulk_run(root;parallel;pyqual_cmd;filter_names;dry_run;timeout;log_dir;live_callback)
  pyqual/cli_bulk_cmds.py:
    e: _bulk_init_impl,_discover_and_validate,_output_bulk_result,_bulk_run_impl,_run_with_live_dashboard,register_bulk_commands
    _bulk_init_impl(path;dry_run;no_llm;model;overwrite;show_schema;json_output)
    _discover_and_validate(path)
    _output_bulk_result(result;json_output)
    _bulk_run_impl(path;parallel;dry_run;timeout;filter_name;no_live;verbose;json_output;log_dir;analyze)
    _run_with_live_dashboard(path;parallel;dry_run;timeout;filter_name;log_dir;analyze;verbose;all_states)
    register_bulk_commands(app)
  pyqual/release_check.py:
    e: _print_result,main
    _print_result(result;verbose)
    main(args)
  pyqual/bulk_init.py:
    e: BulkInitResult,_build_llm_prompt,classify_with_llm,_classify_python,_classify_node,_classify_php,_classify_rust,_classify_go,_classify_makefile,_classify_heuristic,_safe_name,generate_pyqual_yaml,_validate_yaml_content,_write_pyqual_yaml,_classify_project,bulk_init
    BulkInitResult:  # Summary of a bulk-init run...
    _build_llm_prompt(fp)
    classify_with_llm(fp;model)
    _classify_python(fp)
    _classify_node(fp)
    _classify_php(fp)
    _classify_rust(fp)
    _classify_go(fp)
    _classify_makefile(fp)
    _classify_heuristic(fp)
    _safe_name(name)
    generate_pyqual_yaml(project_name;cfg)
    _validate_yaml_content(yaml_content;project_name)
    _write_pyqual_yaml(project_dir;yaml_content)
    _classify_project(fp;use_llm;model;project_name)
    bulk_init(root)
  pyqual/cli_log_helpers.py:
    e: query_nfo_db,row_to_event_dict,format_log_entry_row
    query_nfo_db(db_path;event;failed;tail;sql;stage)
    row_to_event_dict(row)
    format_log_entry_row(entry)
  pyqual/plugins/code_health/main.py:
    e: CodeHealthCollector,code_health_summary
    CodeHealthCollector(MetricCollector): collect(1),_collect_radon(2),_collect_vulture(2),_collect_pyroma(2),_collect_interrogate(2)  # Code health metrics collector — maintainability, dead code, ...
    code_health_summary(workdir)
  pyqual/plugins/docker/main.py:
    e: DockerCollector,run_hadolint,run_trivy_scan,get_image_info,docker_security_check
    DockerCollector(MetricCollector): collect(1),_collect_trivy(2),_count_trivy_vulns(2),_set_zero_trivy(1),_collect_hadolint(2),_collect_grype(2),_get_grype_severity(1),_collect_image_info(2),get_config_example(0)  # Docker security and quality metrics collector...
    run_hadolint(dockerfile;cwd)
    run_trivy_scan(image;output_format;cwd)
    get_image_info(image;cwd)
    docker_security_check(image;dockerfile;cwd)
  pyqual/custom_fix.py:
    e: apply_patch,add_docstring,parse_and_apply_suggestions
    apply_patch(file_path;old_text;new_text)
    add_docstring(file_path;docstring)
    parse_and_apply_suggestions(suggestions)
  pyqual/config.py:
    e: StageConfig,GateConfig,LoopConfig,PyqualConfig,_load_env_file,_normalize_env_values
    StageConfig: __post_init__(0)  # Single pipeline stage...
    GateConfig: from_dict(2)  # Single quality gate threshold...
    LoopConfig:  # Loop iteration settings...
    PyqualConfig: load(1),_parse(1),_validate_stages(0),default_yaml(-1)  # Full pyqual.yaml configuration...
    _load_env_file()
    _normalize_env_values(env)
  pyqual/run_parallel_fix.py:
    e: get_todo_batch,mark_completed_todos,run_tool,git_commit_and_push,parse_args,_check_git_changes,_determine_tool_status,_print_yaml_results,_print_cycle_completion,_setup_batch,_run_tools_parallel,main
    get_todo_batch(todo_path;max_items)
    mark_completed_todos(todo_path;changed_files)
    run_tool(name;command;workdir;timeout)
    git_commit_and_push(workdir;completed_count)
    parse_args()
    _check_git_changes(workdir)
    _determine_tool_status(result)
    _print_yaml_results(results;changed_files;total_pending;completed_count;max_items;batch_size;duration;pushed)
    _print_cycle_completion(remaining;max_items)
    _setup_batch(workdir;batch_items)
    _run_tools_parallel(tool_configs;workdir)
    main()
  pyqual/plugins/builtin.py:
    e: LLMBenchCollector,HallucinationCollector,SBOMCollector,I18nCollector,A11yCollector,RepoMetricsCollector,LlxMcpFixCollector
    LLMBenchCollector(MetricCollector): collect(1)  # LLM code generation quality metrics from human-eval and Code...
    HallucinationCollector(MetricCollector): collect(1)  # Hallucination detection and prompt quality metrics...
    SBOMCollector(MetricCollector): collect(1)  # SBOM compliance and supply chain security metrics...
    I18nCollector(MetricCollector): collect(1)  # Internationalization coverage metrics...
    A11yCollector(MetricCollector): collect(1)  # Accessibility (a11y) compliance metrics...
    RepoMetricsCollector(MetricCollector): collect(1)  # Advanced repository health metrics (bus factor, diversity)...
    LlxMcpFixCollector(MetricCollector): _tier_rank(0),_load_report(0),_assign_float(2),_count_lines(0),_collect_analysis_metrics(2),_collect_aider_metrics(2),get_config_example(0),collect(1)  # Dockerized llx MCP fix/refactor workflow results...
  pyqual/plugins/lint/main.py:
    e: LintCollector,lint_summary
    LintCollector(MetricCollector): collect(1),_collect_ruff(2),_collect_mypy(2),_collect_pylint(2),_collect_flake8(2)  # Lint metrics collector — aggregates findings from linters...
    lint_summary(workdir)
  dashboard/src/components/Overview.tsx:
    i: ../types,./MetricsChart,react
    e: OverviewProps,Overview,totalRepos,passingRepos,failingRepos,avgCoverage
    OverviewProps:
    Overview()
    totalRepos()
    passingRepos()
    failingRepos()
    avgCoverage()
  pyqual/report.py:
    e: _read_pyproject,_parse_pyproject_fallback,_read_version,_read_git_commit_count,_read_costs_json,_read_costs_package,_read_costs_data,collect_project_metadata,collect_all_metrics,evaluate_gates,generate_report,_badge_url,_build_project_badges,_build_quality_badges,build_badges,update_readme_badges,run,main
    _read_pyproject(workdir)
    _parse_pyproject_fallback(path)
    _read_version(workdir;pyproject)
    _read_git_commit_count(workdir)
    _read_costs_json(workdir)
    _read_costs_package(workdir)
    _read_costs_data(workdir)
    collect_project_metadata(workdir;config)
    collect_all_metrics(workdir)
    evaluate_gates(config;workdir)
    generate_report(config;workdir;output)
    _badge_url(label;value;color)
    _build_project_badges(meta)
    _build_quality_badges(metrics;gates_passed;gates_passed_count;gates_total)
    build_badges(metrics;gates_passed;project_meta;gates_passed_count;gates_total)
    update_readme_badges(readme_path;metrics;gates_passed;project_meta;gates_passed_count;gates_total)
    run(workdir;config_path;readme_path)
    main()
  pyqual/cli/cmd_mcp.py:
    e: _run_mcp_workflow,mcp_fix,mcp_refactor,mcp_service
    _run_mcp_workflow()
    mcp_fix(workdir;project_path;issues;output;endpoint;model;file;use_docker;docker_arg;task;json_output)
    mcp_refactor(workdir;project_path;issues;output;endpoint;model;file;use_docker;docker_arg;json_output)
    mcp_service(host;port)
  pyqual/cli/cmd_tune.py:
    e: tune_thresholds,_load_latest_metrics,_calculate_thresholds,_display_comparison,_confirm_apply,_apply_thresholds,tune_show
    tune_thresholds(aggressive;conservative;dry_run;config_path)
    _load_latest_metrics()
    _calculate_thresholds(metrics;aggressive;conservative)
    _display_comparison(current;suggested;actual)
    _confirm_apply()
    _apply_thresholds(config_path;thresholds)
    tune_show()
  dashboard/src/App.tsx:
    i: ./api,./components/Overview,./components/RepositoryDetail,./components/Settings,./types,react,react-router-dom
    e: App,loadRepositories,repos,handleRepositorySelect,runs,RepositoryCard,lastRun,statusColor,statusIcon
    App()
    loadRepositories()
    repos()
    handleRepositorySelect()
    runs()
    RepositoryCard()
    lastRun()
    statusColor()
    statusIcon()
  dashboard/src/api/index.ts:
    i: ../types
    e: API_BASE_URL,GITHUB_TOKEN,loadConfig,response,fetchRepositories,config,repositories,lastRun,fetchLatestRun,response,releases,latestRelease,summaryAsset,summaryResponse,response,fetchRepositoryRuns,response,fetchMetricsHistory,response,getRepoPath,match,fetchRepositoriesWithFallback,repos
    API_BASE_URL()
    GITHUB_TOKEN()
    loadConfig()
    response()
    fetchRepositories()
    config()
    repositories()
    lastRun()
    fetchLatestRun()
    response()
    releases()
    latestRelease()
    summaryAsset()
    summaryResponse()
    response()
    fetchRepositoryRuns()
    response()
    fetchMetricsHistory()
    response()
    getRepoPath()
    match()
    fetchRepositoriesWithFallback()
    repos()
  run_analysis.py:
    e: run_project,main
    run_project(project_path)
    main()
  pyqual/auto_closer.py:
    e: get_changed_files,get_diff_content,evaluate_with_llm,_should_close_ticket,_close_github_issue,_process_ticket,main
    get_changed_files()
    get_diff_content()
    evaluate_with_llm(title;description;diff)
    _should_close_ticket(ticket;changed_files)
    _close_github_issue(reporter;issue_num)
    _process_ticket(ticket;store;reporter;diff_content;completion_rate)
    main()
  pyqual/cli_observe.py:
    e: _output_sql_query,_output_json_entries,_output_human_logs,_print_stage_output,_logs_impl,_watch_impl,_poll_pipeline_db,_poll_history_file,_history_impl,_load_history_entries,_print_history_table,_print_history_prompts,_print_history_stdout,_print_history_summary,register_observe_commands
    _output_sql_query(rows;json_output)
    _output_json_entries(entries)
    _output_human_logs(entries;show_output)
    _print_stage_output(console;entry)
    _logs_impl(workdir;tail;level;stage;failed;show_output;json_output;sql)
    _watch_impl(workdir;interval;show_output;show_prompts)
    _poll_pipeline_db(db_path;last_count;show_output;console)
    _poll_history_file(history_path;last_lines;console)
    _history_impl(workdir;tail;prompts;json_output;verbose)
    _load_history_entries(history_path)
    _print_history_table(entries)
    _print_history_prompts(entries)
    _print_history_stdout(entries)
    _print_history_summary(entries;history_path)
    register_observe_commands(app)
  pyqual/cli_run_helpers.py:
    e: count_todo_items,extract_pytest_stage_summary,extract_lint_stage_summary,extract_prefact_stage_summary,extract_code2llm_stage_summary,extract_validation_stage_summary,extract_fix_stage_summary,extract_mypy_stage_summary,extract_bandit_stage_summary,extract_stage_summary,_enrich_analysis,_enrich_validation,_enrich_todo,enrich_from_artifacts,infer_fix_result,_extract_todo_summary,_extract_fix_summary,_extract_delivery_summary,build_run_summary,_format_ticket_summary,_format_fix_summary,_format_delivery_summary,format_run_summary,get_last_error_line
    count_todo_items(todo_path)
    extract_pytest_stage_summary(name;text)
    extract_lint_stage_summary(text)
    extract_prefact_stage_summary(name;text)
    extract_code2llm_stage_summary(name;text)
    extract_validation_stage_summary(name;text)
    extract_fix_stage_summary(name;text)
    extract_mypy_stage_summary(name;text)
    extract_bandit_stage_summary(text)
    extract_stage_summary(name;stdout;stderr)
    _enrich_analysis(workdir;stages)
    _enrich_validation(workdir;stages)
    _enrich_todo(workdir;stages)
    enrich_from_artifacts(workdir;stages)
    infer_fix_result(stage)
    _extract_todo_summary(stages)
    _extract_fix_summary(stages)
    _extract_delivery_summary(stages)
    build_run_summary(report)
    _format_ticket_summary(summary)
    _format_fix_summary(summary)
    _format_delivery_summary(summary)
    format_run_summary(summary)
    get_last_error_line(text)
  pyqual/cli/cmd_git.py:
    e: _print_file_list,git_status_cmd,git_add_cmd,git_scan_cmd,git_commit_cmd,git_push_cmd,_run_preflight_checks,_handle_push_result
    _print_file_list(files;label;color;prefix)
    git_status_cmd(workdir;json_output)
    git_add_cmd(paths;workdir)
    git_scan_cmd(paths;workdir;use_trufflehog;use_gitleaks;use_patterns;json_output;fail_on_findings)
    git_commit_cmd(message;workdir;add_all;if_changed;json_output)
    git_push_cmd(workdir;remote;branch;force;force_with_lease;detect_protection;dry_run;scan_secrets;json_output)
    _run_preflight_checks(workdir;remote;branch;scan_secrets;dry_run;json_output)
    _handle_push_result(result;workdir;remote;json_output;detect_protection)
  pyqual/plugins/cli_helpers.py:
    e: plugin_list,plugin_search,plugin_info,plugin_add,plugin_remove,plugin_validate,plugin_unknown_action
    plugin_list(plugins;tag)
    plugin_search(plugins;query)
    plugin_info(name;workdir)
    plugin_add(name;workdir)
    plugin_remove(name;workdir)
    plugin_validate(plugins;workdir)
    plugin_unknown_action(action)
  pyqual/plugins/security/main.py:
    e: SecurityCollector,run_bandit_check,run_pip_audit,run_detect_secrets,security_summary
    SecurityCollector(MetricCollector): collect(1),_collect_bandit(2),_collect_audit(2),_get_severity(1),_collect_secrets(2),_collect_safety(2),get_config_example(0)  # Security metrics collector — aggregates findings from securi...
    run_bandit_check(paths;severity;cwd)
    run_pip_audit(output_format;cwd)
    run_detect_secrets(baseline_file;all_files;cwd)
    security_summary(workdir)
  pyqual/plugins/docs/main.py:
    e: DocsCollector,check_readme,run_interrogate,check_links,docs_quality_summary,_generate_recommendations
    DocsCollector(MetricCollector): collect(1),_collect_readme_metrics(2),_set_zero_readme(1),_collect_docstring_metrics(2),_collect_link_metrics(2),_collect_changelog_metrics(2),get_config_example(0)  # Documentation quality metrics collector...
    check_readme(readme_path;cwd)
    run_interrogate(paths;cwd)
    check_links(files;cwd)
    docs_quality_summary(cwd)
    _generate_recommendations(readme;metrics)
  pyqual/bulk/runner.py:
    e: _run_single_project
    _run_single_project(state;dry_run;timeout;pyqual_cmd;log_dir;analyze)
  pyqual/validation/errors.py:
    e: ErrorDomain,EC,Severity,StageFailure,error_domain,_match_env_subtype,_match_fix_env_subtype,_classify_failure
    ErrorDomain(str,Enum):
    EC:  # Namespace for standardised error-code string constants...
    Severity(str,Enum):
    StageFailure:  # Runtime failure description from a completed stage...
    error_domain(code)
    _match_env_subtype(combined)
    _match_fix_env_subtype(combined)
    _classify_failure(f)
  pyqual/api.py:
    e: ShellHelper,load_config,validate_config,create_default_config,run,run_pipeline,check_gates,dry_run,run_stage,get_tool_command,format_result_summary,export_results_json,shell_check
    ShellHelper: run(5),check(3),output(3)  # Shell helper utilities for external tool integration...
    load_config(path;workdir)
    validate_config(config)
    create_default_config(path;profile;workdir)
    run(config;workdir;dry_run;on_stage_start;on_stage_done;on_iteration_start;on_iteration_done;stream_output)
    run_pipeline(config_path;workdir;dry_run)
    check_gates(config;workdir)
    dry_run(config_path;workdir)
    run_stage(stage_name;command;tool;workdir;timeout;env)
    get_tool_command(tool_name;workdir)
    format_result_summary(result)
    export_results_json(result;output_path)
    shell_check(command)
  pyqual/setup_deps.py:
    e: DepResult,_check_pip,_check_cli,_install_pip,check_all,main
    DepResult:  # Result of a single dependency check...
    _check_pip(package)
    _check_cli(tool)
    _install_pip(package)
    check_all(install_missing)
    main()
  pyqual/bulk_init_fingerprint.py:
    e: ProjectFingerprint,_collect_top_level_entries,_collect_manifests,_collect_file_extensions,_load_json_object,_collect_json_scripts,_collect_makefile_targets,_collect_pyproject_metadata,_collect_readme_excerpt,collect_fingerprint
    ProjectFingerprint:  # Lightweight summary of a project directory sent to LLM for c...
    _collect_top_level_entries(project_dir;fp)
    _collect_manifests(project_dir;fp)
    _collect_file_extensions(project_dir)
    _load_json_object(path)
    _collect_json_scripts(project_dir;filename)
    _collect_makefile_targets(project_dir)
    _collect_pyproject_metadata(project_dir;fp)
    _collect_readme_excerpt(project_dir)
    collect_fingerprint(project_dir)
  pyqual/yaml_fixer.py:
    e: YamlErrorType,YamlSyntaxIssue,YamlFixResult,_detect_indentation_issues,_detect_quote_issues,_is_multiline_quote,_detect_bracket_issues,_detect_colon_issues,_detect_trailing_spaces,_detect_bom,_get_context,analyze_yaml_syntax,_try_parse_yaml,_parse_pyyaml_error,fix_yaml_file
    YamlErrorType(str,Enum):  # Types of YAML syntax errors we can detect and fix...
    YamlSyntaxIssue:  # A single YAML syntax issue with location and fix information...
    YamlFixResult:  # Result of parsing/fixing YAML...
    _detect_indentation_issues(lines)
    _detect_quote_issues(lines)
    _is_multiline_quote(lines;start_line;quote_char)
    _detect_bracket_issues(lines)
    _detect_colon_issues(lines)
    _detect_trailing_spaces(lines)
    _detect_bom(content)
    _get_context(lines;line_num;context_size)
    analyze_yaml_syntax(content)
    _try_parse_yaml(content)
    _parse_pyyaml_error(error_str;lines)
    fix_yaml_file(config_path;dry_run)
  pyqual/gate_collectors/legacy.py:
    e: _from_toon,_from_vallm,_from_coverage,_from_bandit,_from_secrets,_from_vulnerabilities
    _from_toon(workdir)
    _from_vallm(workdir)
    _from_coverage(workdir)
    _from_bandit(workdir)
    _from_secrets(workdir)
    _from_vulnerabilities(workdir)
  pyqual/validation/config_check.py:
    e: _get_issue_severity,_load_yaml_config,_load_tool_registry,_validate_stage,_validate_gate,_validate_loop_config,validate_config
    _get_issue_severity(issue;try_fix)
    _load_yaml_config(config_path;result;try_fix)
    _load_tool_registry(pipeline;result)
    _validate_stage(s;result;get_preset;list_presets)
    _validate_gate(gate_key;threshold;result)
    _validate_loop_config(loop_raw;result)
    validate_config(config_path;try_fix)
  dashboard/src/components/RepositoryDetail.tsx:
    i: ../types,./MetricsTrendChart,./StagesChart,@heroicons/react/24/outline,react,react-router-dom
    e: RepositoryDetailProps,StatusBadge,isPassed,bgClass,Icon,Icon,iconColor,RunDetails,MetricsSection,gate,RepositoryDetail,navigate,repo,latestRun
    RepositoryDetailProps:
    StatusBadge()
    isPassed()
    bgClass()
    Icon()
    Icon()
    iconColor()
    RunDetails()
    MetricsSection()
    gate()
    RepositoryDetail()
    navigate()
    repo()
    latestRun()
  pyqual/gates.py:
    e: GateResult,Gate,GateSet,CompositeGateSet
    GateResult: __str__(0)  # Result of a single gate check...
    Gate: check(1)  # Single quality gate with metric extraction...
    GateSet: __init__(1),_completion_rate(1),check_all(1),all_passed(1),completion_percentage(1),_collect_metrics(1)  # Collection of quality gates with metric collection...
    CompositeGateSet(GateSet): __init__(3),compute_score(1),check_composite(1)  # Weighted composite quality scoring from multiple gates.

Exa...
  pyqual/tickets.py:
    e: _load_sync_integration,_normalize_sources,sync_planfile_tickets,sync_todo_tickets,sync_github_tickets,sync_all_tickets,sync_from_gates
    _load_sync_integration()
    _normalize_sources(source)
    sync_planfile_tickets(source;workdir;dry_run;direction)
    sync_todo_tickets(workdir;dry_run;direction)
    sync_github_tickets(workdir;dry_run;direction)
    sync_all_tickets(workdir;dry_run;direction)
    sync_from_gates(workdir;dry_run;backends)
  pyqual/github_actions.py:
    e: GitHubTask,GitHubActionsReporter
    GitHubTask: to_todo_item(0),__str__(0)  # Represents a task from GitHub (issue or PR)...
    GitHubActionsReporter: __init__(2),create_issue(3),ensure_issue_exists(3),is_running_in_github_actions(0),get_pr_number(0),fetch_issues(2),fetch_pull_requests(1),post_pr_comment(2),post_issue_comment(2),close_issue(2),close_pull_request(2),generate_failure_report(4),set_output(2),set_failed(1)  # Reports pyqual results to GitHub Actions and PRs...
  pyqual/tools.py:
    e: ToolPreset,_preset_from_dict,_load_json_presets,_load_default_presets,get_preset,list_presets,is_builtin,register_preset,load_user_tools,preset_to_dict,dump_presets_json,register_custom_tools_from_yaml,load_entry_point_presets,resolve_stage_command
    ToolPreset: is_available(0),shell_command(1)  # Definition of a built-in tool invocation preset...
    _preset_from_dict(d)
    _load_json_presets(path)
    _load_default_presets()
    get_preset(name)
    list_presets()
    is_builtin(name)
    register_preset(name;preset)
    load_user_tools(workdir)
    preset_to_dict(preset)
    dump_presets_json(names)
    register_custom_tools_from_yaml(custom_tools)
    load_entry_point_presets()
    resolve_stage_command(tool_name;workdir)
  pyqual/bulk_init_classify.py:
    e: ProjectConfig,check_skip_conditions
    ProjectConfig:  # Parsed LLM response — project-specific config decisions...
    check_skip_conditions(fp)
  pyqual/cli/cmd_plugin.py:
    e: plugin
    plugin(action;name;workdir;tag)
  pyqual/cli/main.py:
    e: tune_thresholds_cmd,_load_latest_metrics_for_tune,_calculate_thresholds_for_tune,_display_comparison_for_tune,_apply_thresholds_for_tune,setup_logging
    tune_thresholds_cmd(aggressive;conservative;dry_run;config_path)
    _load_latest_metrics_for_tune()
    _calculate_thresholds_for_tune(metrics;aggressive;conservative)
    _display_comparison_for_tune(current;suggested;actual)
    _apply_thresholds_for_tune(config_path;thresholds)
    setup_logging(verbose;workdir)
  pyqual/plugins/coverage/main.py:
    e: CoverageCollector,coverage_summary
    CoverageCollector(MetricCollector): collect(1)  # Coverage metrics collector — extracts test coverage data...
    coverage_summary(workdir)
  pyqual/validation/project.py:
    e: _detect_language,detect_project_facts
    _detect_language(file_names)
    detect_project_facts(workdir)
  pyqual/stage_names.py:
    e: normalize_stage_name,is_fix_stage_name,is_verify_stage_name,is_delivery_stage_name,get_stage_when_default
    normalize_stage_name(name)
    is_fix_stage_name(name)
    is_verify_stage_name(name)
    is_delivery_stage_name(name)
    get_stage_when_default(name)
  pyqual/cli/cmd_init.py:
    e: init,profiles
    init(path;profile)
    profiles()
  pyqual/cli/cmd_tickets.py:
    e: tickets_sync,tickets_todo,tickets_github,tickets_all,tickets_fetch,tickets_comment
    tickets_sync(workdir;from_gates;backends;dry_run)
    tickets_todo(workdir;dry_run;direction)
    tickets_github(workdir;dry_run;direction)
    tickets_all(workdir;dry_run;direction)
    tickets_fetch(label;state;output;todo_output;append)
    tickets_comment(issue_number;message;is_pr)
  pyqual/bulk/parser.py:
    e: _parse_stage_start,_parse_iteration_header,_parse_output_line
    _parse_stage_start(state;line)
    _parse_iteration_header(state;line)
    _parse_output_line(state;line)
  dashboard/src/components/MetricsTrendChart.tsx:
    i: ../types,react,recharts
    e: MetricsTrendChartProps,MetricsTrendChart,data
    MetricsTrendChartProps:
    MetricsTrendChart()
    data()
  dashboard/src/components/MetricsChart.tsx:
    i: ../types,react,recharts
    e: MetricsChartProps,MetricsChart,data,days,today,date,baseCoverage,variation
    MetricsChartProps:
    MetricsChart()
    data()
    days()
    today()
    date()
    baseCoverage()
    variation()
  dashboard/api/main.py:
    e: get_db_path,read_summary_json,query_pipeline_db,safe_parse,get_projects,get_latest_run,get_project_runs,get_metric_history,get_stage_performance,get_gate_status,get_project_summary,ingest_results,health_check
    get_db_path(project_id)
    read_summary_json(project_id)
    query_pipeline_db(db_path;query;params)
    safe_parse(data)
    get_projects()
    get_latest_run(project_id)
    get_project_runs(project_id;limit)
    get_metric_history(project_id;metric;days)
    get_stage_performance(project_id;days)
    get_gate_status(project_id;days)
    get_project_summary(project_id)
    ingest_results(project_id;data;credentials)
    health_check()
  pyqual/github_tasks.py:
    e: fetch_github_tasks,save_tasks_to_todo,save_tasks_to_json
    fetch_github_tasks(label;state;include_issues;include_prs)
    save_tasks_to_todo(tasks;todo_path;append)
    save_tasks_to_json(tasks;json_path)
  pyqual/integrations/llx_mcp.py:
    e: build_parser,main
    build_parser()
    main(argv)
  pyqual/gate_collectors/utils.py:
    e: _read_artifact_text
    _read_artifact_text(workdir;filenames)
  pyqual/fix_tools/__init__.py:
    e: get_available_tools
    get_available_tools(batch_file;batch_count;llm_model;skip_claude)
  pyqual/cli/cmd_info.py:
    e: doctor,tools
    doctor()
    tools()
  pyqual/plugins/__init__.py:
    e: _discover_plugins,get_available_plugins,install_plugin_config
    _discover_plugins()
    get_available_plugins()
    install_plugin_config(name;workdir)
  pyqual/plugins/_base.py:
    e: PluginMetadata,MetricCollector,PluginRegistry
    PluginMetadata: __post_init__(0)  # Metadata for a pyqual plugin...
    MetricCollector(ABC): collect(1),get_config_example(0)  # Base class for metric collector plugins...
    PluginRegistry: register(1),get(1),list_plugins(1),create_instance(1)  # Registry for metric collector plugins...
  pyqual/plugins/attack/__main__.py:
    e: _ensure_dir,cmd_check,cmd_merge,main
    _ensure_dir()
    cmd_check()
    cmd_merge()
    main()
  dashboard/src/components/StagesChart.tsx:
    i: ../types,react,recharts
    e: StagesChartProps,StagesChart,data
    StagesChartProps:
    StagesChart()
    data()
  pyqual/plugins/example_plugin/main.py:
    e: ExampleCollector,example_helper_function
    ExampleCollector(MetricCollector): collect(1),get_config_example(0)  # Example collector showing plugin structure.

This demonstrat...
    example_helper_function()
  pyqual/validation/schema.py:
    e: ValidationIssue,ValidationResult,_resolve_gate_metric
    ValidationIssue:  # Single validation finding...
    ValidationResult: add(5)  # Aggregated result of validating one pyqual.yaml...
    _resolve_gate_metric(gate_key)
  dashboard/src/components/Settings.tsx:
    i: @heroicons/react/24/outline,react
    e: Settings
    Settings()
  pyqual/fix_tools/base.py:
    e: ToolResult,FixTool
    ToolResult:  # Result from running a fix tool...
    FixTool(ABC): __init__(3),is_available(0),get_command(0),get_timeout(0),to_config(0)  # Abstract base class for fix tools...
  pyqual/fix_tools/aider.py:
    e: AiderTool
    AiderTool(FixTool): is_available(0),get_command(0),get_timeout(0)  # Aider tool via Docker (paulgauthier/aider)...
  pyqual/fix_tools/llx.py:
    e: LlxTool
    LlxTool(FixTool): __init__(3),is_available(0),get_command(0),get_timeout(0)  # LLX fix tool...
  pyqual/output.py:
    e: _parse_output_line
    _parse_output_line(state;line)
  pyqual/command.py:
    e: _run_command
    _run_command(cmd;log_dir)
  pyqual/analysis.py:
    e: _analyze_project
    _analyze_project(state;log_dir)
  pyqual/profiles.py:
    e: PipelineProfile,get_profile,list_profiles
    PipelineProfile:  # A reusable pipeline template with default stages and metrics...
    get_profile(name)
    list_profiles()
  pyqual/fix_tools/claude.py:
    e: ClaudeTool
    ClaudeTool(FixTool): is_available(0),get_command(0),get_timeout(0)  # Claude Code CLI tool...
  pyqual/pipeline_protocols.py:
    e: OnStageStart,OnIterationStart,OnStageError,OnStageDone,OnStageOutput,OnIterationDone
    OnStageStart(Protocol): __call__(1)
    OnIterationStart(Protocol): __call__(1)
    OnStageError(Protocol): __call__(1)
    OnStageDone(Protocol): __call__(1)  # Called after each stage completes. Receives the full StageRe...
    OnStageOutput(Protocol): __call__(3)  # Called with each line of streaming output from a stage...
    OnIterationDone(Protocol): __call__(1)  # Called after each iteration completes. Receives the full Ite...
  pyqual/plugins/git/git_command.py:
    e: run_git_command
    run_git_command(args;cwd)
  pyqual/integrations/llx_mcp_service.py:
    e: create_app,run_server,build_parser,main
    create_app(state;llx_server)
    run_server(host;port;state)
    build_parser()
    main(argv)
  SUGGESTED_COMMANDS.sh:
  project.sh:
  dashboard/tailwind.config.js:
  dashboard/vite.config.ts:
    i: @vitejs/plugin-react,vite
  dashboard/postcss.config.js:
  dashboard/src/main.tsx:
    i: ./App,react,react-dom/client
  dashboard/src/types/index.ts:
    e: PyqualMetric,PyqualStage,PyqualSummary,Repository,DashboardConfig,MetricHistory,MetricTrend
    PyqualMetric:
    PyqualStage:
    PyqualSummary:
    Repository:
    DashboardConfig:
    MetricHistory:
    MetricTrend:
  dashboard/constants.py:
  pyqual/llm.py:
  pyqual/bulk_run.py:
  pyqual/__init__.py:
  pyqual/__main__.py:
  pyqual/pipeline_results.py:
    e: StageResult,IterationResult,PipelineResult
    StageResult:  # Result of running a single stage...
    IterationResult:  # Result of one full pipeline iteration...
    PipelineResult:  # Result of the complete pipeline run (all iterations)...
  pyqual/validation/__init__.py:
  pyqual/constants.py:
  pyqual/gate_collectors/__init__.py:
  pyqual/cli/__init__.py:
  pyqual/plugins/docs/__init__.py:
  pyqual/plugins/security/__init__.py:
  pyqual/plugins/code_health/__init__.py:
  pyqual/plugins/attack/__init__.py:
  pyqual/plugins/docker/__init__.py:
  pyqual/plugins/deps/__init__.py:
  pyqual/plugins/lint/__init__.py:
  pyqual/plugins/git/__init__.py:
  pyqual/plugins/coverage/__init__.py:
  pyqual/plugins/example_plugin/__init__.py:
  pyqual/plugins/documentation/__init__.py:
  pyqual/integrations/__init__.py:
  integration/run_docker_matrix.sh:
  integration/run_matrix.sh:
    e: run_case,hello,hello,add,hello,hello,hello,hello
    run_case()
    hello()
    hello()
    add()
    hello()
    hello()
    hello()
    hello()
  pyqual/bulk/models.py:
    e: RunStatus,ProjectRunState
    RunStatus(Enum):
    ProjectRunState:
```

## Source Map

*Top 5 modules by symbol density — signatures for LLM orientation.*

### `pyqual._gate_collectors` (`pyqual/_gate_collectors.py`)

```python
def _read_artifact_text(workdir, filenames)  # CC=5, fan=2
def _from_toon(workdir)  # CC=4, fan=4
def _from_vallm(workdir)  # CC=6, fan=9
def _from_coverage(workdir)  # CC=9, fan=6
def _from_bandit(workdir)  # CC=10, fan=7 ⚠
def _from_secrets(workdir)  # CC=9, fan=11
def _count_by_severity(items, severity)  # CC=3, fan=3
def _from_vulnerabilities(workdir)  # CC=6, fan=9
def _from_security(workdir)  # CC=2, fan=6
def _from_sbom(workdir)  # CC=11, fan=10 ⚠
def _from_vulture(workdir)  # CC=5, fan=8
def _from_pyroma(workdir)  # CC=8, fan=9
def _from_code_health(workdir)  # CC=2, fan=6
def _from_git_health(workdir)  # CC=5, fan=5
def _from_llm_quality(workdir)  # CC=12, fan=5 ⚠
def _from_ai_cost(workdir)  # CC=5, fan=5
def _from_benchmark(workdir)  # CC=14, fan=8 ⚠
def _from_memory_profile(workdir)  # CC=7, fan=5
def _from_radon(workdir)  # CC=15, fan=11 ⚠
def _from_mypy(workdir)  # CC=6, fan=8
def _from_lint(workdir)  # CC=2, fan=6
def _from_ruff(workdir)  # CC=12, fan=11 ⚠
def _count_pylint_by_type(messages, type_name, symbol_prefix)  # CC=4, fan=5
def _from_pylint(workdir)  # CC=8, fan=9
def _from_flake8(workdir)  # CC=12, fan=11 ⚠
def _from_runtime_errors(workdir)  # CC=8, fan=13
def _from_interrogate(workdir)  # CC=10, fan=6 ⚠
```

### `pyqual.pipeline` (`pyqual/pipeline.py`)

```python
class Pipeline:  # Execute pipeline stages in a loop until quality gates pass.
    def __init__(config, workdir, on_stage_start, on_iteration_start, on_stage_error, on_stage_done, on_stage_output, stream, on_iteration_done)  # CC=1
    def run(dry_run)  # CC=6
    def check_gates()  # CC=1
    def _run_iteration(num, dry_run)  # CC=8
    def _iteration_stagnated(iteration)  # CC=8
    def _should_run_stage(stage, gates_pass, stages_so_far, iteration)  # CC=4
    def _resolve_tool_stage(stage)  # CC=5
    def _resolve_env()  # CC=6
    def _check_optional_binary(command)  # CC=8
    def _make_skipped_result(stage, reason)  # CC=1
    def _make_dry_run_result(stage, command)  # CC=2
    def _execute_stage(stage, dry_run)  # CC=16 ⚠
    def _notify_stage_error(stage, result, is_fix_stage)  # CC=1
    def _execute_captured(stage, command, allow_failure, env, start)  # CC=8
    def _execute_streaming(stage, command, allow_failure, env, start)  # CC=13 ⚠
    def _init_nfo()  # CC=1
    def _nfo_emit(event, level, kwargs, duration_ms)  # CC=2
    def _is_fix_stage(stage)  # CC=6
    def _log_stage(stage, result)  # CC=12 ⚠
    def _archive_llx_report(stage, result)  # CC=6
    def _log_gates(iteration, gates)  # CC=5
    def _log_event(event)  # CC=1
    def _ensure_pyqual_dir()  # CC=1
    def _capture_runtime_error(stage, result)  # CC=9
    def _classify_error(result)  # CC=6
    def _extract_error_message(result)  # CC=12 ⚠
```

### `pyqual.cli_run_helpers` (`pyqual/cli_run_helpers.py`)

```python
def count_todo_items(todo_path)  # CC=2, fan=3
def extract_pytest_stage_summary(name, text)  # CC=6, fan=5
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
def infer_fix_result(stage)  # CC=8, fan=7
def _extract_todo_summary(stages)  # CC=9, fan=4
def _extract_fix_summary(stages)  # CC=8, fan=7
def _extract_delivery_summary(stages)  # CC=7, fan=9
def build_run_summary(report)  # CC=5, fan=6
def _format_ticket_summary(summary)  # CC=6, fan=3
def _format_fix_summary(summary)  # CC=7, fan=3
def _format_delivery_summary(summary)  # CC=5, fan=3
def format_run_summary(summary)  # CC=6, fan=5
def get_last_error_line(text)  # CC=11, fan=5 ⚠
```

### `pyqual.report` (`pyqual/report.py`)

```python
def _read_pyproject(workdir)  # CC=5, fan=4
def _parse_pyproject_fallback(path)  # CC=4, fan=3
def _read_version(workdir, pyproject)  # CC=3, fan=4
def _read_git_commit_count(workdir)  # CC=3, fan=4
def _read_costs_json(workdir)  # CC=6, fan=5
def _read_costs_package(workdir)  # CC=12, fan=12 ⚠
def _read_costs_data(workdir)  # CC=4, fan=4
def collect_project_metadata(workdir, config)  # CC=10, fan=11 ⚠
def collect_all_metrics(workdir)  # CC=5, fan=5
def evaluate_gates(config, workdir)  # CC=3, fan=3
def generate_report(config, workdir, output)  # CC=9, fan=14
def _badge_url(label, value, color)  # CC=1, fan=1
def _build_project_badges(meta)  # CC=11, fan=4 ⚠
def _build_quality_badges(metrics, gates_passed, gates_passed_count, gates_total)  # CC=8, fan=6
def build_badges(metrics, gates_passed, project_meta, gates_passed_count, gates_total)  # CC=4, fan=4
def _replace_badges_in_text(text, badge_line)  # CC=5, fan=10
def update_readme_badges(readme_path, metrics, gates_passed, project_meta, gates_passed_count, gates_total)  # CC=7, fan=14
def run(workdir, config_path, readme_path)  # CC=9, fan=12
def main()  # CC=1, fan=6
```

### `pyqual.bulk_init` (`pyqual/bulk_init.py`)

```python
def _build_llm_prompt(fp)  # CC=3, fan=4
def classify_with_llm(fp, model)  # CC=9, fan=14
def _classify_python(fp)  # CC=2, fan=1
def _classify_node(fp)  # CC=6, fan=1
def _classify_php(fp)  # CC=2, fan=1
def _classify_rust(fp)  # CC=1, fan=1
def _classify_go(fp)  # CC=1, fan=1
def _classify_makefile(fp)  # CC=3, fan=1
def _classify_heuristic(fp)  # CC=6, fan=5
def _safe_name(name)  # CC=1, fan=3
def generate_pyqual_yaml(project_name, cfg)  # CC=7, fan=6
def _validate_yaml_content(yaml_content, project_name)  # CC=4, fan=2
def _write_pyqual_yaml(project_dir, yaml_content)  # CC=1, fan=2
def _classify_project(fp, use_llm, model, project_name)  # CC=3, fan=3
def bulk_init(root)  # CC=14, fan=12 ⚠
class BulkInitResult:  # Summary of a bulk-init run.
    def total()  # CC=1
```

## Call Graph

*335 nodes · 314 edges · 67 modules · CC̄=5.1*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `generate_pyqual_yaml` *(in pyqual.bulk_init)* | 7 | 1 | 77 | **78** |
| `run` *(in pyqual.cli.cmd_run)* | 17 ⚠ | 0 | 53 | **53** |
| `fix_config` *(in pyqual.cli.cmd_config)* | 13 ⚠ | 0 | 46 | **46** |
| `git_scan_cmd` *(in pyqual.cli.cmd_git)* | 11 ⚠ | 0 | 42 | **42** |
| `run_project` *(in run_analysis)* | 11 ⚠ | 1 | 38 | **39** |
| `main` *(in pyqual.run_parallel_fix)* | 13 ⚠ | 0 | 37 | **37** |
| `validate_release_state` *(in pyqual.validation.release)* | 22 ⚠ | 1 | 33 | **34** |
| `get_last_run` *(in pyqual.report_generator)* | 15 ⚠ | 1 | 32 | **33** |

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

## Intent

Declarative quality gate loops for AI-assisted development
