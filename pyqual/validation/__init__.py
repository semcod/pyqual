"""Pre-flight validation and runtime error categorization for pyqual.

Validates config files before running the pipeline, detecting:
- YAML parse errors
- Unknown tool presets
- Tool binaries missing from PATH
- Gate metric names that no collector can produce
- Stage configuration mistakes

Standardized error codes
------------------------
All codes use the format  ``E_PYQUAL_<DOMAIN>_<SPECIFIC>``:

  E_PYQUAL_CONFIG_*   — pyqual.yaml is wrong (bad YAML, unknown preset, …)
  E_PYQUAL_ENV_*      — environment problem (binary missing, API key absent, …)
  E_PYQUAL_PROJECT_*  — project code issue (test failure, lint error, …)
  E_PYQUAL_PIPELINE_* — pipeline execution problem (timeout, I/O error, …)
  E_PYQUAL_LLM_*      — LLM / fix-stage problem (API key, network, model, …)

The domain is the first component after ``E_PYQUAL_``.  Use it to decide
whether to auto-fix the config (CONFIG/ENV) or let the fix-stage handle it
(PROJECT) or surface it to the user (PIPELINE/LLM).
"""

from __future__ import annotations

# Error taxonomy and failure classification
from pyqual.validation.errors import (
    EC,
    ErrorDomain,
    Severity,
    StageFailure,
    error_domain,
    _classify_failure,
)

# Validation schema
from pyqual.validation.schema import (
    KNOWN_METRICS,
    ValidationIssue,
    ValidationResult,
    _resolve_gate_metric,
)

# Config validation
from pyqual.validation.config_check import (
    validate_config,
)

# Project detection
from pyqual.validation.project import (
    detect_project_facts,
)

__all__ = [
    # Error taxonomy
    "EC",
    "ErrorDomain",
    "Severity",
    "StageFailure",
    "error_domain",
    "_classify_failure",
    # Validation schema
    "KNOWN_METRICS",
    "ValidationIssue",
    "ValidationResult",
    "_resolve_gate_metric",
    # Config validation
    "validate_config",
    # Project detection
    "detect_project_facts",
]
