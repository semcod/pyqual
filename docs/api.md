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
