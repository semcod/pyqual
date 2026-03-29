# Basic API Usage

Example of using pyqual programmatically via Python API.

## Files

- `run_pipeline.py` - Execute pipeline from Python
- `check_gates.py` - Check quality gates only
- `minimal.py` - Minimal one-liner

## Project Structure

```
basic/
├── run_pipeline.py
├── check_gates.py
├── minimal.py
└── README.md
```

## run_pipeline.py

```python
#!/usr/bin/env python3
"""Run quality pipeline from Python."""

from pyqual import PyqualConfig, Pipeline

# Load config from YAML
config = PyqualConfig.load("pyqual.yaml")

# Create and run pipeline
pipeline = Pipeline(config)
result = pipeline.run()

# Check results
if result.final_passed:
    print(f"✅ All gates passed in {result.iteration_count} iterations")
else:
    print(f"❌ Gates failed after {result.iteration_count} iterations")
    for it in result.iterations:
        for gate in it.gates:
            print(f"  {gate}")
```

## check_gates.py

```python
#!/usr/bin/env python3
"""Check quality gates without running stages."""

from pyqual import PyqualConfig, GateSet

# Load config
config = PyqualConfig.load("pyqual.yaml")

# Check gates only
gate_set = GateSet(config.gates)
results = gate_set.check_all()

for result in results:
    status = "✅" if result.passed else "❌"
    print(f"{status} {result}")

if all(r.passed for r in results):
    print("\nAll gates pass!")
else:
    print("\nSome gates failed.")
    exit(1)
```

## minimal.py

```python
#!/usr/bin/env python3
"""Minimal pyqual usage."""
from pyqual import Pipeline, PyqualConfig

Pipeline(PyqualConfig.load("pyqual.yaml")).run()
```

## Usage

```bash
cd basic
python run_pipeline.py
python check_gates.py
python minimal.py
```

## Key Points

- `PyqualConfig.load()` loads YAML configuration
- `Pipeline()` creates executable pipeline
- `GateSet()` for checking gates without stages
- All results are dataclasses with typed fields
