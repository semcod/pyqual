"""Project detection: scan project directory for LLM-based config repair."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from pyqual.constants import CONFIG_READ_MAX_CHARS


# ---------------------------------------------------------------------------
# Project-type heuristics (for fix-config / LLM context)
# ---------------------------------------------------------------------------

_LANG_MARKERS: dict[str, tuple[str, ...]] = {
    "python": ("pyproject.toml", "setup.py", "setup.cfg"),
    "nodejs": ("package.json",),
    "rust": ("Cargo.toml",),
    "go": ("go.mod",),
    "java": ("pom.xml", "build.gradle"),
}


def _detect_language(file_names: set[str]) -> str:
    """Detect project language from marker files."""
    for lang, markers in _LANG_MARKERS.items():
        if any(m in file_names for m in markers):
            return lang
    return "unknown"


def detect_project_facts(workdir: Path) -> dict[str, Any]:
    """Scan project directory and return facts for LLM-based config repair."""
    facts: dict[str, Any] = {"workdir": str(workdir)}

    files = list(workdir.iterdir()) if workdir.exists() else []
    file_names = {f.name for f in files}

    facts["lang"] = _detect_language(file_names)

    # Available tools on PATH
    available_tools = []
    for tool in ["pytest", "ruff", "mypy", "code2llm", "vallm", "prefact",
                 "bandit", "pip-audit", "trufflehog", "coverage"]:
        if shutil.which(tool):
            available_tools.append(tool)
    facts["available_tools"] = available_tools

    # Test framework hints
    has_tests = any(f.name.startswith("test_") or f.name == "tests"
                    for f in files)
    facts["has_tests"] = has_tests

    # Existing pyqual.yaml
    config_path = workdir / "pyqual.yaml"
    if config_path.exists():
        facts["current_config"] = config_path.read_text()[:CONFIG_READ_MAX_CHARS]

    return facts
