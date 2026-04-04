"""Security plugin for pyqual.

This package provides comprehensive security scanning capabilities.
"""

from __future__ import annotations

from pyqual.plugins.security.main import (
    SecurityCollector,
    run_bandit_check,
    run_detect_secrets,
    run_pip_audit,
    security_summary,
)

__all__ = [
    "SecurityCollector",
    "run_bandit_check",
    "run_pip_audit",
    "run_detect_secrets",
    "security_summary",
]
