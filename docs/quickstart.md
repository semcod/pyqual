# Quick Start

Get up and running with pyqual in 5 minutes.

## Installation

```bash
pip install pyqual
```

Optional dependencies for full ecosystem integration:

```bash
pip install pyqual[all]  # includes code2llm, vallm, costs
```

## Initialize your project

```bash
cd your-project
pyqual init
```

This creates `pyqual.yaml` with sensible defaults and `.pyqual/` working directory.

## Run the pipeline

```bash
pyqual run
```

The pipeline will:
1. Run all stages in order
2. Collect metrics from outputs
3. Check quality gates
4. Iterate up to `max_iterations` times
5. Report results

## Ticket Management

Sync tickets from TODO.md and GitHub:

```bash
pyqual tickets todo      # sync TODO.md
pyqual tickets github    # sync GitHub issues
pyqual tickets all       # sync both
```

Enable automatic sync on gate failures in `pyqual.yaml`:

```yaml
loop:
  on_fail: create_ticket
```

## Check status without running

```bash
pyqual status   # Show current metrics
pyqual gates    # Check gates only
```

## Dry run mode

Preview what would happen without executing:

```bash
pyqual run --dry-run
```

## Verbose mode, Streaming & Logs

See live pipeline logging during execution:

```bash
pyqual run --verbose       # live progress to stderr
pyqual run --stream        # real-time stdout/stderr per stage (see llx prompts)
```

View structured logs after a run:

```bash
pyqual logs                    # all entries (table view)
pyqual logs --tail 20          # last 20 entries
pyqual logs --failed           # only failures
pyqual logs --stage fix --output   # fix stage with captured stdout/stderr
pyqual logs --json --failed    # JSON for LLM/llx consumption
pyqual logs --level gate_check # only gate results
```

View LLX fix history (prompts, models, results):

```bash
pyqual history               # summary table of all LLX fix runs
pyqual history --prompts     # include full LLX prompts
pyqual history --verbose     # include aider/llx stdout
pyqual history --json        # raw JSONL for LLM consumption
```

Live-tail pipeline execution in another terminal:

```bash
pyqual watch                 # live tail of pipeline.db events
pyqual watch --output        # include stage stdout/stderr
pyqual watch --prompts       # show LLX fix prompts as they appear
pyqual watch --interval 0.5  # faster polling
```

Logs are written to `.pyqual/pipeline.db` (SQLite) and `.pyqual/llx_history.jsonl` for LLX runs.

## Next steps

- [Configure your quality gates](configuration.md)
- [Set up integrations](integrations.md)
- [Use the Python API](api.md)
- Browse [Examples](../examples/) for your use case:
  - [Basic API usage](../examples/basic/) — Pipeline, GateSet, minimal one-liner
  - [Python Package (src-layout)](../examples/python-package/) — standard Python package
  - [Python Flat Layout](../examples/python-flat/) — simple project without src/
  - [Linters](../examples/linters/) — ruff, pylint, flake8, mypy, interrogate
  - [Security scanning](../examples/security/) — bandit, pip-audit, trufflehog, SBOM
  - [Custom gates](../examples/custom_gates/) — dynamic thresholds, composite gates, metric history
  - [Custom plugins](../examples/custom_plugins/) — build your own MetricCollector
  - [LLM fix (Docker)](../examples/llm_fix/) — Dockerized llx MCP workflow
  - [Multi-gate pipeline](../examples/multi_gate_pipeline/) — combining linters + security + LLM
  - [Ticket workflow](../examples/ticket_workflow/) — planfile-backed ticket sync
  - [GitHub Actions](../examples/github-actions/) — CI/CD with GitHub
  - [GitLab CI](../examples/gitlab-ci/) — CI/CD with GitLab
  - [Monorepo](../examples/monorepo/) — multiple packages in one repo
