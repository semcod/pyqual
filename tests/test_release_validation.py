"""Tests for release-state validation.

These tests mock external dependencies (git status, PyPI API) to validate
the release-check logic without requiring network access or a real git repo.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyqual.validation import validate_release_state
from pyqual.validation.errors import EC, Severity


def _make_clean_git_status(**overrides):
    """Return a clean git status dict with optional overrides."""
    return {
        "success": True,
        "is_clean": True,
        "staged_files": [],
        "unstaged_files": [],
        "untracked_files": [],
        "ahead": 0,
        "behind": 0,
        "branch": "main",
        **overrides,
    }


class TestReleaseValidationHappyPath:
    """Tests for successful release validation scenarios."""

    @pytest.fixture
    def fake_project(self, tmp_path: Path) -> Path:
        """Create a minimal Python project structure for testing."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.0\n")
        pkg = tmp_path / "testpkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "0.1.0"\n')
        return tmp_path

    def test_clean_git_unique_version_passes(
        self, fake_project: Path
    ) -> None:
        """When git is clean and version doesn't exist on PyPI, validation passes."""
        from urllib.error import HTTPError

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            with patch(
                "pyqual.validation.release.urlopen",
                side_effect=HTTPError(
                    url="https://pypi.org/pypi/testpkg/0.1.1/json",
                    code=404,
                    msg="Not Found",
                    hdrs={},
                    fp=None,
                ),
            ):
                result = validate_release_state(fake_project, bump_patch=True)

        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_no_bump_validates_current_version(
        self, fake_project: Path
    ) -> None:
        """With bump_patch=False, validates current version (0.1.0) not 0.1.1."""
        from urllib.error import HTTPError

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            with patch(
                "pyqual.validation.release.urlopen",
                side_effect=HTTPError(
                    url="https://pypi.org/pypi/testpkg/0.1.0/json",
                    code=404,
                    msg="Not Found",
                    hdrs={},
                    fp=None,
                ),
            ):
                result = validate_release_state(fake_project, bump_patch=False)

        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        assert len(errors) == 0


class TestReleaseValidationGitIssues:
    """Tests for git-related validation failures."""

    def test_dirty_git_fails(self, tmp_path: Path) -> None:
        """Uncommitted changes block release."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.0\n")

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(
                is_clean=False,
                staged_files=["file.py"],
            ),
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_GIT_DIRTY]
        assert len(errors) == 1
        assert errors[0].severity == Severity.ERROR

    def test_not_git_repo_fails(self, tmp_path: Path) -> None:
        """Non-git directory blocks release."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )

        with patch(
            "pyqual.validation.release.git_status",
            return_value={"success": False, "error": "Not a git repository"},
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_GIT_NOT_REPO]
        assert len(errors) == 1

    def test_behind_remote_warns(self, tmp_path: Path) -> None:
        """Being behind remote is a warning, not an error."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(behind=3),
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        behind_warnings = [w for w in warnings if w.code == EC.RELEASE_GIT_BEHIND]
        assert len(behind_warnings) == 1


class TestReleaseValidationVersionIssues:
    """Tests for version metadata validation."""

    def test_version_mismatch_error(self, tmp_path: Path) -> None:
        """Mismatch between VERSION file and pyproject.toml is an error."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.1\n")  # Different!

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_VERSION_MISMATCH]
        assert len(errors) == 1

    def test_module_version_mismatch_warning(
        self, tmp_path: Path
    ) -> None:
        """Mismatch in __init__.py is a warning, not blocking."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.0\n")
        pkg = tmp_path / "testpkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "0.0.99"\n')  # Mismatch

        from urllib.error import HTTPError

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            with patch(
                "pyqual.validation.release.urlopen",
                side_effect=HTTPError(
                    url="https://pypi.org/pypi/testpkg/0.1.0/json",
                    code=404,
                    msg="Not Found",
                    hdrs={},
                    fp=None,
                ),
            ):
                result = validate_release_state(tmp_path, bump_patch=False)

        warnings = [i for i in result.issues if i.code == EC.RELEASE_MODULE_VERSION_MISMATCH]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING


class TestReleaseValidationRegistry:
    """Tests for PyPI registry checks."""

    def test_existing_version_fails(
        self, tmp_path: Path
    ) -> None:
        """Version already on PyPI blocks release."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.0\n")

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            # Mock successful response (no exception) = version exists
            with patch(
                "pyqual.validation.release.urlopen",
                return_value=MagicMock(status=200),
            ):
                result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_VERSION_EXISTS]
        assert len(errors) == 1
        assert "already exists on PyPI" in errors[0].message

    def test_network_error_warns(self, tmp_path: Path) -> None:
        """Network problems are warnings, not blocking."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )

        from urllib.error import URLError

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            with patch(
                "pyqual.validation.release.urlopen",
                side_effect=URLError("Network unreachable"),
            ):
                result = validate_release_state(tmp_path, bump_patch=False)

        warnings = [i for i in result.issues if i.code == EC.RELEASE_REGISTRY_UNAVAILABLE]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING

    def test_unsupported_registry_warns(
        self, tmp_path: Path
    ) -> None:
        """Non-PyPI registries emit a warning."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            result = validate_release_state(tmp_path, registry="npm", bump_patch=False)

        warnings = [i for i in result.issues if i.code == EC.RELEASE_REGISTRY_UNSUPPORTED]
        assert len(warnings) == 1


class TestReleaseValidationMetadata:
    """Tests for metadata edge cases."""

    def test_missing_package_name(self, tmp_path: Path) -> None:
        """No package name in pyproject.toml is an error."""
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_METADATA_MISSING]
        assert len(errors) == 1
        assert "package name" in errors[0].message.lower()

    def test_missing_version(self, tmp_path: Path) -> None:
        """No version info blocks release."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "testpkg"\n')

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            result = validate_release_state(tmp_path, bump_patch=False)

        errors = [i for i in result.issues if i.code == EC.RELEASE_METADATA_MISSING]
        # Should have error about missing version (since no VERSION file either)
        version_errors = [e for e in errors if "version" in e.message.lower()]
        assert len(version_errors) >= 1


class TestBumpPatchLogic:
    """Tests for version bumping logic."""

    def test_bump_patch_computes_next_version(self, tmp_path: Path) -> None:
        """bump_patch=True validates 0.1.1 when VERSION is 0.1.0."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\nversion = "0.1.0"\n'
        )
        (tmp_path / "VERSION").write_text("0.1.0\n")

        # Version 0.1.1 should be checked (not 0.1.0)
        from urllib.error import HTTPError

        checked_urls: list[str] = []

        def capture_urlopen(url: str, **kwargs):
            checked_urls.append(url)
            raise HTTPError(url, 404, "Not Found", {}, None)

        with patch(
            "pyqual.validation.release.git_status",
            return_value=_make_clean_git_status(),
        ):
            with patch(
                "pyqual.validation.release.urlopen",
                side_effect=capture_urlopen,
            ):
                validate_release_state(tmp_path, bump_patch=True)

        assert any("0.1.1" in url for url in checked_urls)
