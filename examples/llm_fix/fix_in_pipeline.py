#!/usr/bin/env python3
"""Use LLM in quality pipeline for auto-fixing."""

import subprocess
from pathlib import Path

from pyqual import PyqualConfig, Pipeline, get_llm

# Check if tests pass
result = subprocess.run(["python", "-m", "pytest"], capture_output=True, text=True)

if result.returncode != 0:
    print("Tests failed, attempting LLM fix...")
    
    llm = get_llm()
    
    # Read failing test file
    test_file = Path("test_example.py")
    code = test_file.read_text()
    
    # Get fix from LLM
    response = llm.fix_code(
        code=code,
        error=result.stderr,
        context="pytest test failure"
    )
    
    # Write fixed code back
    test_file.write_text(response.content)
    print(f"Applied fix (cost: ${response.cost or 0:.4f})")
    
    # Re-run pipeline
    config = PyqualConfig.load("pyqual.yaml")
    pipeline = Pipeline(config)
    pipeline.run()
