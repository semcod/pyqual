<!-- code2docs:start --># pyqual

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-78-green)
> **78** functions | **23** classes | **12** files | CC̄ = 6.3

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
    ├── cli    ├── config├── pyqual/    ├── llm        ├── dynamic_thresholds        ├── minimal        ├── check_gates        ├── run_pipeline├── project    ├── plugins    ├── pipeline    ├── gates```

## API Overview

### Classes

- **`StageConfig`** — Single pipeline stage.
- **`GateConfig`** — Single quality gate threshold.
- **`LoopConfig`** — Loop iteration settings.
- **`PyqualConfig`** — Full pyqual.yaml configuration.
- **`LLMResponse`** — Response from LLM call.
- **`LLM`** — LiteLLM wrapper with .env configuration.
- **`PluginMetadata`** — Metadata for a pyqual plugin.
- **`MetricCollector`** — Base class for metric collector plugins.
- **`PluginRegistry`** — Registry for metric collector plugins.
- **`LLMBenchCollector`** — LLM code generation quality metrics from human-eval and CodeBLEU.
- **`HallucinationCollector`** — Hallucination detection and prompt quality metrics.
- **`SBOMCollector`** — SBOM compliance and supply chain security metrics.
- **`I18nCollector`** — Internationalization coverage metrics.
- **`A11yCollector`** — Accessibility (a11y) compliance metrics.
- **`RepoMetricsCollector`** — Advanced repository health metrics (bus factor, diversity).
- **`SecurityCollector`** — Security scanning metrics from trufflehog, gitleaks, safety.
- **`StageResult`** — Result of running a single stage.
- **`IterationResult`** — Result of one full pipeline iteration.
- **`PipelineResult`** — Result of the complete pipeline run (all iterations).
- **`Pipeline`** — Execute pipeline stages in a loop until quality gates pass.
- **`GateResult`** — Result of a single gate check.
- **`Gate`** — Single quality gate with metric extraction.
- **`GateSet`** — Collection of quality gates with metric collection.

### Functions

- `init(path)` — Create pyqual.yaml with sensible defaults.
- `run(config, dry_run, workdir)` — Execute pipeline loop until quality gates pass.
- `gates(config, workdir)` — Check quality gates without running stages.
- `status(config, workdir)` — Show current metrics and pipeline config.
- `plugin(action, name, workdir)` — Manage pyqual plugins - add new metric collectors.
- `doctor()` — Check availability of external tools used by pyqual collectors.
- `get_llm_model()` — Get LLM model from environment or default.
- `get_api_key()` — Get OpenRouter API key from environment.
- `get_llm(model)` — Get configured LLM instance.
- `get_available_plugins()` — Get metadata for all available built-in plugins.
- `install_plugin_config(name, workdir)` — Generate configuration snippet for a plugin.


## Project Structure

📄 `examples.basic.check_gates`
📄 `examples.basic.minimal`
📄 `examples.basic.run_pipeline`
📄 `examples.custom_gates.dynamic_thresholds`
📄 `project`
📦 `pyqual`
📄 `pyqual.cli` (6 functions)
📄 `pyqual.config` (5 functions, 4 classes)
📄 `pyqual.gates` (37 functions, 3 classes)
📄 `pyqual.llm` (7 functions, 2 classes)
📄 `pyqual.pipeline` (7 functions, 4 classes)
📄 `pyqual.plugins` (16 functions, 10 classes)

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0- litellm >=1.0- python-dotenv >=1.0

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