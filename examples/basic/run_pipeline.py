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
