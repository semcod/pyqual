"""Release-state validation for package publishing.

This validator checks whether the current project state is safe to publish:
- the git worktree is clean
- the local version metadata is synchronized
- the release version does not already exist on PyPI

It is intentionally lightweight so it can run as a pre-publish stage.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from pyqual.plugins.git import git_status
from pyqual.validation.errors import EC, Severity
from pyqual.validation.schema import ValidationResult

CONSTANT_200 = 200
CONSTANT_404 = 404


__all__ = ["validate_release_state"]


def _read_pyproject(workdir: Path) -> dict[str, Any]:
    """Read ``pyproject.toml`` and return the parsed data.

    Falls back to a tiny regex parser when ``tomllib`` is unavailable.
    """
    pyproject = workdir / "pyproject.toml"
    if not pyproject.exists():
        return {}

    try:
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                return _parse_pyproject_fallback(pyproject)

        return tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return _parse_pyproject_fallback(pyproject)


def _parse_pyproject_fallback(path: Path) -> dict[str, Any]:
    """Extract key metadata from ``pyproject.toml`` with regexes."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    result: dict[str, Any] = {"project": {}}

    for key in ("name", "version"):
        match = re.search(rf'^\s*{key}\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            result["project"][key] = match.group(1)

    poetry_match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if poetry_match and not result["project"].get("name"):
        result["project"]["name"] = poetry_match.group(1)

    poetry_version = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if poetry_version and not result["project"].get("version"):
        result["project"]["version"] = poetry_version.group(1)

    return result


def _read_version_file(workdir: Path) -> Optional[str]:
    version_file = workdir / "VERSION"
    if not version_file.exists():
        return None
    version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
    return version or None


def _read_package_init_version(workdir: Path, package_name: str) -> Optional[str]:
    package_dir = workdir / package_name.replace("-", "_") / "__init__.py"
    if not package_dir.exists():
        return None

    content = package_dir.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def _read_project_metadata(workdir: Path) -> dict[str, Optional[str]]:
    pyproject = _read_pyproject(workdir)
    project = pyproject.get("project") or {}

    package_name = project.get("name")
    pyproject_version = project.get("version")
    version_file = _read_version_file(workdir)

    if not package_name and not pyproject_version and not version_file:
        return {
            "package_name": None,
            "pyproject_version": None,
            "version_file": None,
            "module_version": None,
        }

    package_name_str = str(package_name) if package_name else None
    module_version = _read_package_init_version(workdir, package_name_str) if package_name_str else None

    return {
        "package_name": package_name_str,
        "pyproject_version": str(pyproject_version) if pyproject_version else None,
        "version_file": version_file,
        "module_version": module_version,
    }


def _bump_patch_version(version: str) -> Optional[str]:
    """Return ``version`` with the patch component incremented by one."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version.strip())
    if not match:
        return None
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


def _resolve_release_version(base_version: str, bump_patch: bool) -> Optional[str]:
    if bump_patch:
        return _bump_patch_version(base_version)
    return base_version.strip() or None


def _check_pypi_version(package_name: str, version: str) -> tuple[bool, Optional[str]]:
    """Return ``(exists, error_message)`` for a PyPI package version."""
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    try:
        response = urlopen(url, timeout=10)
        status = getattr(response, "status", CONSTANT_200)
        return status == CONSTANT_200, None
    except HTTPError as exc:
        if exc.code == CONSTANT_404:
            return False, None
        return False, f"HTTP {exc.code}"
    except URLError as exc:
        return False, str(exc.reason or exc)
    except Exception as exc:
        return False, str(exc)


def validate_release_state(
    workdir: Path,
    registry: str = "pypi",
    bump_patch: bool = True,
) -> ValidationResult:
    """Validate whether the current package state is safe to publish.

    Args:
        workdir: Project root to inspect.
        registry: Package registry name. Currently only ``pypi`` is supported.
        bump_patch: When True, validate the version that will be produced by
            the current ``make publish`` workflow (patch bump first).
    """
    workdir = Path(workdir).resolve()
    result = ValidationResult(config_name=workdir.name)

    git = git_status(cwd=workdir)
    if not git.get("success", False):
        result.add(
            Severity.ERROR,
            EC.RELEASE_GIT_NOT_REPO,
            f"{git.get('error') or 'Git status check failed'}",
            stage="release-check",
            suggestion="Run the release check from inside a git repository.",
        )
    else:
        if not git.get("is_clean", False):
            dirty_parts: list[str] = []
            for key, label in (
                ("staged_files", "staged"),
                ("unstaged_files", "unstaged"),
                ("untracked_files", "untracked"),
            ):
                files = git.get(key, [])
                if isinstance(files, list) and files:
                    dirty_parts.append(f"{len(files)} {label}")

            detail = ", ".join(dirty_parts) if dirty_parts else "working tree contains changes"
            result.add(
                Severity.ERROR,
                EC.RELEASE_GIT_DIRTY,
                f"Working tree is not clean ({detail}).",
                stage="release-check",
                suggestion="Commit or stash changes before publishing.",
            )

        behind = int(git.get("behind", 0) or 0)
        if behind > 0:
            result.add(
                Severity.WARNING,
                EC.RELEASE_GIT_BEHIND,
                f"Branch is behind remote by {behind} commit(s).",
                stage="release-check",
                suggestion="Pull or rebase before publishing to avoid releasing stale code.",
            )

    metadata = _read_project_metadata(workdir)
    package_name = metadata.get("package_name")
    pyproject_version = metadata.get("pyproject_version")
    version_file = metadata.get("version_file")
    module_version = metadata.get("module_version")

    if not package_name:
        result.add(
            Severity.ERROR,
            EC.RELEASE_METADATA_MISSING,
            "Could not determine the package name from pyproject.toml.",
            stage="release-check",
            suggestion="Add [project].name to pyproject.toml.",
        )
        return result

    base_version = version_file or pyproject_version
    if not base_version:
        result.add(
            Severity.ERROR,
            EC.RELEASE_METADATA_MISSING,
            f"Could not determine the release version for {package_name}.",
            stage="release-check",
            suggestion="Add a VERSION file or set [project].version in pyproject.toml.",
        )
        return result

    if version_file and pyproject_version and version_file != pyproject_version:
        result.add(
            Severity.ERROR,
            EC.RELEASE_VERSION_MISMATCH,
            f"VERSION file ({version_file}) and pyproject.toml ({pyproject_version}) differ.",
            stage="release-check",
            suggestion="Synchronize VERSION and pyproject.toml before publishing.",
        )

    if module_version and module_version != base_version:
        result.add(
            Severity.WARNING,
            EC.RELEASE_MODULE_VERSION_MISMATCH,
            f"pyqual.__version__ ({module_version}) does not match release metadata ({base_version}).",
            stage="release-check",
            suggestion="Update pyqual/__init__.py so __version__ matches VERSION and pyproject.toml.",
        )

    release_version = _resolve_release_version(base_version, bump_patch=bump_patch)
    if not release_version:
        result.add(
            Severity.ERROR,
            EC.RELEASE_INVALID_VERSION,
            f"Version '{base_version}' is not a supported semantic version.",
            stage="release-check",
            suggestion="Use MAJOR.MINOR.PATCH versioning so the release validator can check PyPI.",
        )
        return result

    if registry.lower() != "pypi":
        result.add(
            Severity.WARNING,
            EC.RELEASE_REGISTRY_UNSUPPORTED,
            f"Registry '{registry}' is not supported by this validator.",
            stage="release-check",
            suggestion="Use registry='pypi' or extend the validator for another registry.",
        )
        return result

    exists, registry_error = _check_pypi_version(package_name, release_version)
    if registry_error:
        result.add(
            Severity.WARNING,
            EC.RELEASE_REGISTRY_UNAVAILABLE,
            f"Could not verify PyPI version for {package_name} {release_version}: {registry_error}",
            stage="release-check",
            suggestion="Retry the check before publishing, or confirm network access to PyPI.",
        )
    elif exists:
        result.add(
            Severity.ERROR,
            EC.RELEASE_VERSION_EXISTS,
            f"{package_name} {release_version} already exists on PyPI.",
            stage="release-check",
            suggestion="Bump the version before publishing or publish a different release.",
        )

    return result
