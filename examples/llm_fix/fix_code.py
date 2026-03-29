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
