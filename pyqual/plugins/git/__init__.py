"""Git plugin for pyqual.

This package provides git repository operations with secret scanning.
"""

from __future__ import annotations

from pyqual.plugins.git.main import (
    GitCollector,
    SECRET_PATTERNS,
    git_add,
    git_commit,
    git_push,
    git_status,
    preflight_push_check,
    scan_for_secrets,
)

__all__ = [
    "GitCollector",
    "SECRET_PATTERNS",
    "git_status",
    "git_add",
    "git_commit",
    "git_push",
    "scan_for_secrets",
    "preflight_push_check",
]
