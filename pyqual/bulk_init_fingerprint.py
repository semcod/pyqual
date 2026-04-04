"""Project fingerprinting helpers for bulk initialization.

This module provides functions for collecting project fingerprints
used by the LLM-based project classification system.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyqual.constants import README_EXCERPT_MAX_CHARS, TOP_LEVEL_FILES_MAX

logger = logging.getLogger("pyqual.bulk_init.fingerprint")


@dataclass
class ProjectFingerprint:
    """Lightweight summary of a project directory sent to LLM for classification."""

    name: str
    path: str
    manifests: list[str] = field(default_factory=list)
    has_tests_dir: bool = False
    has_src_dir: bool = False
    file_extensions: list[str] = field(default_factory=list)
    top_level_files: list[str] = field(default_factory=list)
    node_scripts: dict[str, str] = field(default_factory=dict)
    makefile_targets: list[str] = field(default_factory=list)
    composer_scripts: dict[str, str] = field(default_factory=dict)
    pyproject_build_system: str | None = None
    pyproject_test_deps: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_pyqual_yaml: bool = False
    readme_excerpt: str = ""


def _collect_top_level_entries(project_dir: Path, fp: ProjectFingerprint) -> None:
    """Collect top-level files and directories."""
    for child in sorted(project_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_file():
            fp.top_level_files.append(child.name)
        elif child.is_dir():
            if child.name in ("tests", "test"):
                fp.has_tests_dir = True
            if child.name == "src":
                fp.has_src_dir = True


def _collect_manifests(project_dir: Path, fp: ProjectFingerprint) -> None:
    """Collect project manifest files."""
    manifest_names = [
        "pyproject.toml", "setup.py", "setup.cfg",
        "package.json", "composer.json",
        "Cargo.toml", "go.mod",
        "Makefile", "Taskfile.yml",
    ]
    for manifest_name in manifest_names:
        if (project_dir / manifest_name).exists():
            fp.manifests.append(manifest_name)


def _collect_file_extensions(project_dir: Path) -> list[str]:
    """Collect file extensions from project directory."""
    exts: set[str] = set()
    for f in project_dir.glob("*.*"):
        if f.is_file() and not f.name.startswith("."):
            exts.add(f.suffix)
    for f in project_dir.glob("*/*.*"):
        if f.is_file() and not f.name.startswith("."):
            exts.add(f.suffix)
    return sorted(exts)


def _load_json_object(path: Path) -> dict[str, Any] | None:
    """Load a JSON object from a file."""
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _collect_json_scripts(project_dir: Path, filename: str) -> dict[str, str]:
    """Collect scripts from a JSON manifest file."""
    path = project_dir / filename
    if not path.exists():
        return {}
    data = _load_json_object(path)
    if data is None:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def _collect_makefile_targets(project_dir: Path) -> list[str]:
    """Collect Makefile targets."""
    makefile = project_dir / "Makefile"
    if not makefile.exists():
        return []
    try:
        targets: list[str] = []
        for line in makefile.read_text(errors="ignore").splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):", line)
            if m and not m.group(1).startswith("."):
                targets.append(m.group(1))
        return targets[:TOP_LEVEL_FILES_MAX]
    except OSError:
        return []


def _collect_pyproject_metadata(project_dir: Path, fp: ProjectFingerprint) -> None:
    """Collect metadata from pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return
    try:
        import tomllib
    except ImportError:
        try:
            import importlib as _il
            tomllib = _il.import_module("tomli")  # type: ignore[assignment]
        except ImportError:
            tomllib = None  # type: ignore[assignment]
    if tomllib is None:
        return
    try:
        data = tomllib.loads(pyproject.read_text(errors="ignore"))
        bs = data.get("build-system", {}).get("requires", [])
        fp.pyproject_build_system = bs[0] if bs else None
        dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        fp.pyproject_test_deps = [d for d in dev_deps if "pytest" in d.lower() or "test" in d.lower()]
    except Exception:
        pass


def _collect_readme_excerpt(project_dir: Path) -> str:
    """Collect README excerpt."""
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = project_dir / readme_name
        if readme.exists():
            try:
                return readme.read_text(errors="ignore")[:README_EXCERPT_MAX_CHARS]
            except OSError:
                return ""
    return ""


def collect_fingerprint(project_dir: Path) -> ProjectFingerprint:
    """Collect a lightweight fingerprint from a project directory."""
    fp = ProjectFingerprint(name=project_dir.name, path=str(project_dir))
    _collect_top_level_entries(project_dir, fp)
    _collect_manifests(project_dir, fp)
    fp.has_pyqual_yaml = (project_dir / "pyqual.yaml").exists()
    fp.has_dockerfile = (project_dir / "Dockerfile").exists() or (project_dir / "docker-compose.yml").exists()
    fp.file_extensions = _collect_file_extensions(project_dir)
    fp.node_scripts = _collect_json_scripts(project_dir, "package.json")
    fp.composer_scripts = _collect_json_scripts(project_dir, "composer.json")
    fp.makefile_targets = _collect_makefile_targets(project_dir)
    _collect_pyproject_metadata(project_dir, fp)
    fp.readme_excerpt = _collect_readme_excerpt(project_dir)
    return fp
