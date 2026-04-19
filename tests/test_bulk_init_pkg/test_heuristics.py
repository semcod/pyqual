from __future__ import annotations

from pathlib import Path

from pyqual.bulk_init import ProjectFingerprint, _classify_heuristic, collect_fingerprint


class TestClassifyHeuristic:
    def test_python_with_tests(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "mylib")
        cfg = _classify_heuristic(fp)
        assert cfg.project_type == "python"
        assert cfg.has_tests is True
        assert cfg.test_command == "python3 -m pytest -q"
        assert cfg.lint_tool_preset == "ruff"
        assert cfg.skip is False

    def test_node_with_scripts(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "webapp")
        cfg = _classify_heuristic(fp)
        assert cfg.project_type in ("node", "typescript")
        assert cfg.test_command == "npm test"
        assert cfg.lint_command == "npm run lint"
        assert cfg.build_command == "npm run build"

    def test_php_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "api-server")
        cfg = _classify_heuristic(fp)
        assert cfg.project_type == "php"
        assert cfg.test_command == "composer test"

    def test_makefile_project(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "infra")
        cfg = _classify_heuristic(fp)
        assert cfg.has_tests is True
        assert cfg.test_command == "make test"
        assert cfg.lint_command == "make lint"

    def test_skip_venv(self) -> None:
        fp = ProjectFingerprint(name="venv", path="/tmp/venv")
        cfg = _classify_heuristic(fp)
        assert cfg.skip is True

    def test_skip_empty(self) -> None:
        fp = ProjectFingerprint(name="empty", path="/tmp/empty")
        cfg = _classify_heuristic(fp)
        assert cfg.skip is True
