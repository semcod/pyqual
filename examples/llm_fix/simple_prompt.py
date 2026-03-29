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
