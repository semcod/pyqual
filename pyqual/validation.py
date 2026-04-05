"""Backward-compatibility shim for pyqual.validation.

The validation module has been split into a package:
- validation.errors: Error taxonomy and failure classification
- validation.schema: Validation data structures and known metrics
- validation.config_check: Config validation logic
- validation.project: Project detection

This shim re-exports all public symbols for backward compatibility.
"""

from __future__ import annotations

# Re-export everything from sub-modules for backward compatibility
from pyqual.validation.errors import (
    EC,
    ErrorDomain,
    Severity,
    StageFailure,
    error_domain,
    _classify_failure,
)
from pyqual.validation.schema import (
    KNOWN_METRICS,
    ValidationIssue,
    ValidationResult,
    _resolve_gate_metric,
)
from pyqual.validation.config_check import validate_config
from pyqual.validation.project import detect_project_facts

__all__ = [
    "EC",
    "ErrorDomain",
    "KNOWN_METRICS",
    "Severity",
    "StageFailure",
    "ValidationIssue",
    "ValidationResult",
    "_resolve_gate_metric",
    "_classify_failure",
    "detect_project_facts",
    "error_domain",
    "validate_config",
]
