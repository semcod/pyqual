"""Deps plugin for pyqual.

This package provides dependency management and freshness analysis.
"""

from __future__ import annotations

from pyqual.plugins.deps.main import (
    DepsCollector,
    check_requirements,
    deps_health_check,
    get_dependency_tree,
    get_outdated_packages,
)

__all__ = [
    "DepsCollector",
    "get_outdated_packages",
    "get_dependency_tree",
    "check_requirements",
    "deps_health_check",
]
