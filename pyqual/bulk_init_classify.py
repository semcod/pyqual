"""LLM-based project classification helpers for bulk initialization."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pyqual.bulk_init_fingerprint import ProjectFingerprint
from pyqual.constants import DEFAULT_CC_MAX

logger = logging.getLogger("pyqual.bulk_init.classify")


@dataclass
class ProjectConfig:
    """Parsed LLM response — project-specific config decisions."""

    project_type: str = "unknown"
    skip: bool = False
    skip_reason: str | None = None
    has_tests: bool = False
    test_command: str | None = None
    lint_command: str | None = None
    lint_tool_preset: str | None = None
    build_command: str | None = None
    extra_excludes: list[str] = field(default_factory=list)
    cc_max: int = DEFAULT_CC_MAX
    extra_stages: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Skip condition checker (shared between LLM and heuristic classification)
# ---------------------------------------------------------------------------

_DATA_EXTENSIONS = {
    ".md", ".rst", ".txt", ".csv", ".json", ".yaml", ".yml", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".wav", ".mp3", ".mp4", ".pdf", ".toon", ".log", ".bak",
    ".iml", ".ini", ".cfg", ".conf", ".lock", ".toml",
    ".html", ".css",
}

_SKIP_NAMES = {"venv", ".venv", "node_modules", "__pycache__", "dist", "build"}


def check_skip_conditions(fp: ProjectFingerprint) -> ProjectConfig | None:
    """Check if directory should be skipped. Returns ProjectConfig if skip, None otherwise."""
    if fp.name in _SKIP_NAMES:
        return ProjectConfig(skip=True, skip_reason="common artifact directory")
    if not fp.manifests and not fp.file_extensions:
        return ProjectConfig(skip=True, skip_reason="empty or data-only directory")

    if not fp.manifests and set(fp.file_extensions) <= _DATA_EXTENSIONS:
        return ProjectConfig(skip=True, skip_reason="data/documentation-only directory")

    if fp.name.isdigit() and not fp.manifests:
        return ProjectConfig(skip=True, skip_reason="archive directory")

    return None
