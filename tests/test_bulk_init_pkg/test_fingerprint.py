from __future__ import annotations

from pathlib import Path

from pyqual.bulk_init import collect_fingerprint


class TestCollectFingerprint:
    def test_python_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "mylib")
        assert fp.name == "mylib"
        assert "pyproject.toml" in fp.manifests
        assert fp.has_tests_dir is True
        assert fp.has_src_dir is True
        assert fp.has_pyqual_yaml is False

    def test_node_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "webapp")
        assert fp.name == "webapp"
        assert "package.json" in fp.manifests
        assert "test" in fp.node_scripts
        assert "lint" in fp.node_scripts
        assert ".ts" in fp.file_extensions

    def test_php_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "api-server")
        assert "composer.json" in fp.manifests
        assert "test" in fp.composer_scripts

    def test_makefile_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "infra")
        assert "Makefile" in fp.manifests
        assert "test" in fp.makefile_targets
        assert "lint" in fp.makefile_targets

    def test_existing_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "existing")
        assert fp.has_pyqual_yaml is True
