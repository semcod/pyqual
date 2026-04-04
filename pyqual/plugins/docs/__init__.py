"""Docs plugin for pyqual.

This package provides documentation quality analysis.
"""

from __future__ import annotations

from pyqual.plugins.docs.main import (
    DocsCollector,
    check_links,
    check_readme,
    docs_quality_summary,
    run_interrogate,
)

__all__ = [
    "DocsCollector",
    "check_readme",
    "run_interrogate",
    "check_links",
    "docs_quality_summary",
]
