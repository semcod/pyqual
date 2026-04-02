# Security Profile Example

Minimal configuration using the built-in `security` profile.

## Overview

This example demonstrates using the built-in `security` pipeline profile which includes:

- **analyze** (code2llm) - code analysis
- **audit** (pip-audit) - dependency vulnerability scan
- **bandit** - Python security issues
- **secrets** (gitleaks) - API token and secret detection ← NEW!
- **test** (pytest) - test execution

## Quick Start

```bash
# Install security tools
pip install bandit pip-audit
# Install gitleaks: https://github.com/gitleaks/gitleaks/releases

# Run with security profile
pyqual run
```

## What This Demonstrates

The `profile: security` line activates the built-in security profile with all security stages pre-configured. This is the simplest way to enable secret detection in your pipeline.

## See Also

- [Full Security Example](../security/) - complete manual configuration
- [Multi-gate Pipeline](../multi_gate_pipeline/) - combining security with other checks
