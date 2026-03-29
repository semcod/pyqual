# pyqual Documentation

**Declarative quality gate loops for AI-assisted development.**

One YAML file. One command. Pipeline iterates until your code meets quality thresholds.

```bash
pip install pyqual
pyqual init
pyqual run
```

## Overview

You use Copilot, Claude, GPT. They generate code. But nobody checks if that code meets your quality standards before it hits code review. And nobody automatically iterates if it doesn't.

pyqual closes that gap: define metrics → run tools → check gates → if fail, LLM fixes → re-check → repeat until pass.

## How it works

```
pyqual.yaml defines everything:
    ┌─────────────────────────────────────────┐
    │  metrics:                               │
    │    cc_max: 15        ← quality gates    │
    │    vallm_pass_min: 90                   │
    │    coverage_min: 80                     │
    │                                         │
    │  stages:                                │
    │    - analyze  (code2llm)                │
    │    - validate (vallm)                   │
    │    - fix      (llx/aider, when: fail)   │
    │    - test     (pytest)                  │
    │                                         │
    │  loop:                                  │
    │    max_iterations: 3                    │
    │    on_fail: report                      │
    └─────────────────────────────────────────┘

pyqual run:
    Iteration 1 → analyze → validate → fix → test → check gates
                                                         │
                                              ┌── PASS ──┴── FAIL ──┐
                                              │                     │
                                           Done ✅          Iteration 2...
```

## Table of Contents

- [Quick Start](quickstart.md) - Get up and running in 5 minutes
- [Configuration](configuration.md) - pyqual.yaml reference
- [Integrations](integrations.md) - Connect with code2llm, vallm, planfile, pytest
- [Python API](api.md) - Use pyqual programmatically
- [Examples](../examples/) - Real-world usage patterns:
  - [Python Package (src-layout)](../examples/python-package/)
  - [Python Flat Layout](../examples/python-flat/)
  - [GitHub Actions](../examples/github-actions/)
  - [GitLab CI](../examples/gitlab-ci/)
  - [Monorepo](../examples/monorepo/)

## Why pyqual?

| Metric | pyqual | Typical LLM workflow |
|--------|--------|---------------------|
| Lines of code | ~800 | 29,000+ (algitex) |
| Cyclomatic complexity | < 2.5 | 3.6+ |
| Test pass rate | 100% | ~43% |
| Focus | One thing well | Everything poorly |

pyqual practices what it preaches — maintaining its own quality standards.

---

*PyPI: `pip install pyqual` | GitHub: [github.com/semcod/pyqual](https://github.com/semcod/pyqual) | License: Apache 2.0*
