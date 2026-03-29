# LLM Fix Example

Example of using pyqual's LLM integration for automatic code fixing.

## Setup

Create `.env` file:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=openrouter/qwen/qwen3-coder-next
```

## Files

- `fix_code.py` - Use LLM to fix code issues
- `fix_in_pipeline.py` - Integrate LLM fix into pipeline
- `simple_prompt.py` - Simple LLM prompt example

## fix_code.py

```python
#!/usr/bin/env python3
"""Fix code issues using LLM."""

from pyqual import get_llm

# Get LLM instance (reads .env automatically)
llm = get_llm()

# Code with issue
broken_code = '''
def calculate(x, y):
    return x + y

result = calculate(5)  # Missing argument
'''

# Get fix from LLM
response = llm.fix_code(
    code=broken_code,
    error="TypeError: calculate() missing 1 required positional argument: 'y'"
)

print(f"Fixed code:\n{response.content}")
print(f"Model: {response.model}")
if response.cost:
    print(f"Cost: ${response.cost:.4f}")
```

## fix_in_pipeline.py

```python
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
```

## simple_prompt.py

```python
#!/usr/bin/env python3
"""Simple LLM prompt example."""

from pyqual import get_llm

llm = get_llm()

# Direct completion
response = llm.complete(
    prompt="Write a Python function to reverse a string",
    system="You are a Python expert. Provide only code, no explanation.",
    temperature=0.3
)

print(response.content)
print(f"\nTokens used: {response.usage}")
```

## Usage

```bash
cd llm_fix
python simple_prompt.py       # Basic LLM prompt
python fix_code.py             # Fix specific code issue
python fix_in_pipeline.py      # Auto-fix in pipeline
```

## Integration with pyqual.yaml

```yaml
pipeline:
  name: auto-fix-pipeline

  stages:
    - name: test
      run: pytest tests/ -v
      when: always

    - name: llm_fix
      run: python fix_in_pipeline.py
      when: metrics_fail

  loop:
    max_iterations: 3  # Allow 3 auto-fix attempts
    on_fail: report
```
