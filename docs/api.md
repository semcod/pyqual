# Python API

Use pyqual programmatically in your Python scripts.

## Basic Usage

```python
from pyqual import Pipeline, PyqualConfig

# Load configuration
config = PyqualConfig.load("pyqual.yaml")

# Create pipeline
pipeline = Pipeline(config, workdir="./my-project")

# Run pipeline
result = pipeline.run()

# Check results
if result.final_passed:
    print(f"All gates passed in {result.iteration_count} iterations")
else:
    print("Gates not met — check result.iterations for details")
    for iteration in result.iterations:
        for stage in iteration.stages:
            if not stage.passed:
                print(f"  Failed: {stage.name}")
                print(f"  Error: {stage.stderr}")
```

## Configuration API

### Create config programmatically

```python
from pyqual import PyqualConfig, GateConfig, StageConfig, LoopConfig

config = PyqualConfig(
    name="my-pipeline",
    stages=[
        StageConfig(name="test", run="pytest"),
        StageConfig(name="lint", run="ruff check ."),
    ],
    gates=[
        GateConfig.from_dict("coverage_min", 80),
        GateConfig.from_dict("cc_max", 15),
    ],
    loop=LoopConfig(max_iterations=3, on_fail="report"),
)
```

### Get default YAML

```python
yaml_content = PyqualConfig.default_yaml()
print(yaml_content)
```

## Gate Checking API

Check gates without running the full pipeline:

```python
from pyqual import GateSet, GateConfig
from pathlib import Path

# Create gate set
gates = [
    GateConfig.from_dict("cc_max", 15),
    GateConfig.from_dict("coverage_min", 80),
]
gate_set = GateSet(gates)

# Check all gates
results = gate_set.check_all(Path("."))

for result in results:
    status = "✓" if result.passed else "✗"
    print(f"{status} {result.metric}: {result.value} (threshold: {result.threshold})")

# Quick check
if gate_set.all_passed(Path(".")):
    print("All gates pass!")
```

## Pipeline Results

```python
from pyqual import PipelineResult, IterationResult, StageResult

result: PipelineResult = pipeline.run()

# Properties
print(f"Iterations: {result.iteration_count}")
print(f"Total time: {result.total_duration:.1f}s")
print(f"Final result: {'PASS' if result.final_passed else 'FAIL'}")

# Detailed iteration data
for iteration in result.iterations:
    print(f"\nIteration {iteration.iteration}")
    for stage in iteration.stages:
        print(f"  {stage.name}: {stage.duration:.1f}s")
        if stage.stderr:
            print(f"    Error: {stage.stderr}")
```

## Dry Run Mode

```python
# Preview without executing
result = pipeline.run(dry_run=True)

for iteration in result.iterations:
    for stage in iteration.stages:
        # In dry-run, stdout contains preview
        print(stage.stdout)
```

## Ticket Sync API

Use the ticket sync API to programmatically sync TODO.md and GitHub tickets:

```python
from pyqual.tickets import sync_todo_tickets, sync_github_tickets, sync_all_tickets
from pathlib import Path

# Sync TODO.md through planfile
sync_todo_tickets(
    directory=Path("."),
    dry_run=False,
    direction="both"  # "from", "to", or "both"
)

# Sync GitHub issues through planfile
sync_github_tickets(
    directory=Path("."),
    dry_run=False,
    direction="both"
)

# Sync both TODO.md and GitHub
sync_all_tickets(
    directory=Path("."),
    dry_run=False,
    direction="both"
)
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `PyqualConfig` | Full pipeline configuration |
| `GateConfig` | Single quality gate definition |
| `StageConfig` | Pipeline stage definition |
| `LoopConfig` | Iteration settings |
| `Pipeline` | Pipeline executor |
| `GateSet` | Quality gate checker |
| `GateResult` | Single gate check result |
| `PipelineResult` | Complete pipeline result |
| `IterationResult` | Single iteration result |
| `StageResult` | Single stage result |

### Ticket Functions

| Function | Description |
|----------|-------------|
| `sync_todo_tickets()` | Sync TODO.md through planfile markdown backend |
| `sync_github_tickets()` | Sync GitHub issues through planfile GitHub backend |
| `sync_all_tickets()` | Sync both TODO.md and GitHub tickets |

## Plugin API

Build custom metric collectors by extending `MetricCollector`:

```python
from pyqual.plugins import MetricCollector, PluginRegistry, PluginMetadata
from pathlib import Path
import json

class MyToolCollector(MetricCollector):
    """Collect metrics from my custom tool."""
    name = "my-tool"
    metadata = PluginMetadata(
        name="my-tool",
        description="Custom tool metrics",
        version="1.0.0",
        tags=["custom", "quality"],
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        result = {}
        path = workdir / ".pyqual" / "my_tool.json"
        if path.exists():
            data = json.loads(path.read_text())
            if "score" in data:
                result["my_tool_score"] = float(data["score"])
            if "errors" in data:
                result["my_tool_errors"] = float(data["errors"])
        return result

# Register the plugin
PluginRegistry.register(MyToolCollector)
```

Manage plugins via CLI:

```bash
pyqual plugin list              # list all plugins
pyqual plugin search security   # search by keyword
pyqual plugin info llm-bench    # show plugin details
pyqual plugin add llm-bench     # add plugin config to pyqual.yaml
pyqual plugin validate          # check plugin config consistency
pyqual doctor                   # check tool availability
```

See [examples/custom_plugins/](../examples/custom_plugins/) for a complete working example.

## LLM API

The LLM convenience wrapper now lives upstream in `llx.llm`.
`pyqual.llm` re-exports it for backward compatibility (with a local fallback
on Python 3.9 or when `llx` is not installed).

```python
# Preferred — use llx directly (Python >= 3.10)
from llx.llm import LLM, get_llm_model, DEFAULT_MAX_TOKENS

# Also works — pyqual re-export
from pyqual.llm import LLM, get_llm_model, DEFAULT_MAX_TOKENS

# Create LLM instance (reads .env for model/key)
llm = LLM()

# Complete a prompt
response = llm.complete(
    prompt="Explain this function:\ndef foo(): return 42",
    system="You are a code reviewer.",
    max_tokens=DEFAULT_MAX_TOKENS,
)
print(response.content)

# Fix code with LLM
fixed = llm.fix_code(
    code="def add(a, b):\n    return a - b",
    issue="Function should add, not subtract",
)
print(fixed.content)
```

## Named Constants

All constants are centralized in `pyqual.constants` for consistency:

### Importing Constants

```python
from pyqual.constants import (
    # Default thresholds
    DEFAULT_CC_MAX,           # 15
    DEFAULT_VALLM_PASS_MIN,   # 90
    DEFAULT_COVERAGE_MIN,     # 80
    
    # Timeouts
    PREFACT_TIMEOUT,          # 900 (15 min)
    FIX_TIMEOUT,              # 1800 (30 min)
    DEFAULT_STAGE_TIMEOUT,    # 300 (5 min)
    
    # Badge thresholds
    BADGE_THRESHOLD_CC_LOW,   # 10
    BADGE_THRESHOLD_CC_MED,   # 15
    BADGE_THRESHOLD_CC_HIGH,  # 25
    BADGE_THRESHOLD_EXCELLENT, # 80
    
    # CLI formatting
    TIMESTAMP_COL_WIDTH,      # 19
    BULK_PASS_PREVIEW,        # 20
)
```

### Constants Reference Table

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_CC_MAX` | 15 | Cyclomatic complexity limit |
| `DEFAULT_VALLM_PASS_MIN` | 90 | vallm pass rate (%) |
| `DEFAULT_COVERAGE_MIN` | 80 | Test coverage (%) |
| `PREFACT_TIMEOUT` | 900 | Prefact stage timeout (15 min) |
| `FIX_TIMEOUT` | 1800 | LLM fix stage timeout (30 min) |
| `DEFAULT_STAGE_TIMEOUT` | 300 | Default stage timeout (5 min) |
| `BADGE_THRESHOLD_CC_LOW` | 10 | Excellent CC for badges |
| `BADGE_THRESHOLD_CC_MED` | 15 | Good CC for badges |
| `BADGE_THRESHOLD_CC_HIGH` | 25 | Acceptable CC for badges |
| `DEFAULT_MAX_TOKENS` | 2000 | LLM max response tokens |

## Examples

For complete working examples, see:

- [Basic API usage](../examples/basic/) — `Pipeline`, `GateSet`, minimal one-liner
- [Custom gates](../examples/custom_gates/) — dynamic thresholds, composite gates, metric history
- [Custom plugins](../examples/custom_plugins/) — building your own `MetricCollector`
- [Multi-gate pipeline](../examples/multi_gate_pipeline/) — combining linters, security, LLM gates
- [Ticket workflow](../examples/ticket_workflow/) — planfile-backed ticket sync
