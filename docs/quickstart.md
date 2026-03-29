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

## Next steps

- [Configure your quality gates](configuration.md)
- [Set up integrations](integrations.md)
- [Use the Python API](api.md)
- Browse [Examples](../examples/) for your use case:
  - [Python Package (src-layout)](../examples/python-package/) - Standard Python package structure
  - [Python Flat Layout](../examples/python-flat/) - Simple project without src/
  - [GitHub Actions](../examples/github-actions/) - CI/CD with GitHub
  - [GitLab CI](../examples/gitlab-ci/) - CI/CD with GitLab
  - [Monorepo](../examples/monorepo/) - Multiple packages in one repo
