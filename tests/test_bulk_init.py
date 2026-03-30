"""Tests for pyqual.bulk_init — bulk project initialization."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from pyqual.bulk_init import (
    PROJECT_CONFIG_SCHEMA,
    BulkInitResult,
    ProjectConfig,
    ProjectFingerprint,
    _classify_heuristic,
    _safe_name,
    bulk_init,
    classify_with_llm,
    collect_fingerprint,
    generate_pyqual_yaml,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a fake workspace with several project types."""
    # Python project with tests
    py = tmp_path / "mylib"
    py.mkdir()
    (py / "pyproject.toml").write_text("[project]\nname = 'mylib'\n")
    (py / "tests").mkdir()
    (py / "tests" / "test_main.py").write_text("def test_ok(): pass\n")
    (py / "src").mkdir()
    (py / "src" / "main.py").write_text("print('hello')\n")

    # Node project with test script
    node = tmp_path / "webapp"
    node.mkdir()
    (node / "package.json").write_text(json.dumps({
        "name": "webapp",
        "scripts": {"test": "jest", "lint": "eslint .", "build": "tsc"},
    }))
    (node / "src").mkdir()
    (node / "src" / "index.ts").write_text("console.log('hi');\n")

    # PHP project
    php = tmp_path / "api-server"
    php.mkdir()
    (php / "composer.json").write_text(json.dumps({
        "name": "vendor/api-server",
        "scripts": {"test": "phpunit"},
    }))
    (php / "index.php").write_text("<?php echo 'ok'; ?>\n")

    # Makefile-only project
    mk = tmp_path / "infra"
    mk.mkdir()
    (mk / "Makefile").write_text("test:\n\techo ok\nlint:\n\techo lint\n")
    (mk / "deploy.sh").write_text("#!/bin/bash\n")

    # Existing pyqual project (should be skipped)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "pyqual.yaml").write_text("pipeline:\n  name: existing\n  stages: []\n")
    (existing / "pyproject.toml").write_text("[project]\nname = 'existing'\n")

    # Non-project (data directory)
    data = tmp_path / "recordings"
    data.mkdir()
    (data / "file.wav").write_text("")

    # Hidden dir (should be ignored)
    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "stuff").write_text("")

    return tmp_path


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Heuristic classification tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# YAML generation tests
# ---------------------------------------------------------------------------

class TestGenerateYaml:
    def test_python_yaml_is_valid(self) -> None:
        cfg = ProjectConfig(
            project_type="python",
            has_tests=True,
            test_command="python3 -m pytest -q",
            lint_tool_preset="ruff",
        )
        content = generate_pyqual_yaml("mylib", cfg)
        data = yaml.safe_load(content)
        assert data["pipeline"]["name"] == "mylib-quality"
        assert data["pipeline"]["metrics"]["cc_max"] == 15
        stages = data["pipeline"]["stages"]
        stage_names = [s["name"] for s in stages]
        assert "analyze" in stage_names
        assert "validate" in stage_names
        assert "lint" in stage_names
        assert "fix" in stage_names
        assert "test" in stage_names

    def test_node_yaml_has_npm_test(self) -> None:
        cfg = ProjectConfig(
            project_type="node",
            has_tests=True,
            test_command="npm test",
            lint_command="npm run lint",
            build_command="npm run build",
        )
        content = generate_pyqual_yaml("webapp", cfg)
        data = yaml.safe_load(content)
        stages = data["pipeline"]["stages"]
        test_stage = next(s for s in stages if s["name"] == "test")
        assert test_stage["run"] == "npm test"
        lint_stage = next(s for s in stages if s["name"] == "lint")
        assert lint_stage["run"] == "npm run lint"
        build_stage = next(s for s in stages if s["name"] == "build")
        assert build_stage["run"] == "npm run build"

    def test_custom_tools_use_safe_name(self) -> None:
        cfg = ProjectConfig(project_type="python", test_command="pytest")
        content = generate_pyqual_yaml("my-cool-lib", cfg)
        data = yaml.safe_load(content)
        tool_names = [t["name"] for t in data["pipeline"]["custom_tools"]]
        assert "code2llm_my_cool_lib" in tool_names
        assert "vallm_my_cool_lib" in tool_names

    def test_extra_excludes_included(self) -> None:
        cfg = ProjectConfig(
            project_type="python",
            test_command="pytest",
            extra_excludes=["webops", "src-tauri"],
        )
        content = generate_pyqual_yaml("bigapp", cfg)
        assert "webops" in content
        assert "src-tauri" in content

    def test_extra_stages(self) -> None:
        cfg = ProjectConfig(
            project_type="python",
            test_command="pytest",
            extra_stages=[
                {"name": "security", "run": "bandit -r src/", "when": "always", "optional": True},
            ],
        )
        content = generate_pyqual_yaml("secure", cfg)
        data = yaml.safe_load(content)
        stage_names = [s["name"] for s in data["pipeline"]["stages"]]
        assert "security" in stage_names
        sec = next(s for s in data["pipeline"]["stages"] if s["name"] == "security")
        assert sec["run"] == "bandit -r src/"
        assert sec["optional"] is True

    def test_workdir_placeholder_single_brace(self) -> None:
        cfg = ProjectConfig(project_type="python", test_command="pytest")
        content = generate_pyqual_yaml("test", cfg)
        assert "{workdir}" in content
        assert "{{workdir}}" not in content


# ---------------------------------------------------------------------------
# Safe name tests
# ---------------------------------------------------------------------------

class TestSafeName:
    def test_simple(self) -> None:
        assert _safe_name("mylib") == "mylib"

    def test_dashes(self) -> None:
        assert _safe_name("my-cool-lib") == "my_cool_lib"

    def test_dots(self) -> None:
        assert _safe_name("blog.pactown.com") == "blog_pactown_com"

    def test_uppercase(self) -> None:
        assert _safe_name("FixOS") == "fixos"


# ---------------------------------------------------------------------------
# LLM classification tests (mocked)
# ---------------------------------------------------------------------------

class TestClassifyWithLlm:
    def test_valid_json_response(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "mylib")
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "project_type": "python",
            "skip": False,
            "skip_reason": None,
            "has_tests": True,
            "test_command": "python3 -m pytest -q",
            "lint_tool_preset": "ruff",
            "cc_max": 10,
        })

        with patch("pyqual.llm.LLM") as MockLLM:
            MockLLM.return_value.complete.return_value = mock_response
            cfg = classify_with_llm(fp, model="test-model")

        assert cfg.project_type == "python"
        assert cfg.has_tests is True
        assert cfg.test_command == "python3 -m pytest -q"
        assert cfg.cc_max == 10

    def test_markdown_fenced_json(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "mylib")
        mock_response = MagicMock()
        mock_response.content = '```json\n{"project_type": "python", "skip": false, "has_tests": true}\n```'

        with patch("pyqual.llm.LLM") as MockLLM:
            MockLLM.return_value.complete.return_value = mock_response
            cfg = classify_with_llm(fp)

        assert cfg.project_type == "python"

    def test_invalid_json_falls_back_to_heuristic(self, workspace: Path) -> None:
        fp = collect_fingerprint(workspace / "mylib")
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON at all"

        with patch("pyqual.llm.LLM") as MockLLM:
            MockLLM.return_value.complete.return_value = mock_response
            cfg = classify_with_llm(fp)

        # Should fall back to heuristic and detect Python
        assert cfg.project_type == "python"


# ---------------------------------------------------------------------------
# Bulk init orchestrator tests
# ---------------------------------------------------------------------------

class TestBulkInit:
    def test_dry_run_creates_nothing(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=True)
        assert len(result.created) > 0
        # Verify no files were actually written
        for name in result.created:
            assert not (workspace / name / "pyqual.yaml").exists() or name == "existing"

    def test_heuristic_creates_configs(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=False)
        assert "mylib" in result.created
        assert "webapp" in result.created
        assert "api-server" in result.created
        assert "infra" in result.created
        assert "existing" in result.skipped_existing
        # Verify files exist
        for name in result.created:
            target = workspace / name / "pyqual.yaml"
            assert target.exists()
            data = yaml.safe_load(target.read_text())
            assert "pipeline" in data

    def test_skips_existing(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=False)
        assert "existing" in result.skipped_existing

    def test_existing_file_content_preserved(self, workspace: Path) -> None:
        original = (workspace / "existing" / "pyqual.yaml").read_text()
        bulk_init(workspace, use_llm=False, dry_run=False)
        after = (workspace / "existing" / "pyqual.yaml").read_text()
        assert after == original

    def test_existing_not_in_created(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=False)
        assert "existing" not in result.created
        assert "existing" in result.skipped_existing

    def test_second_run_skips_already_generated(self, workspace: Path) -> None:
        """Running bulk_init twice should skip projects that got a pyqual.yaml in the first run."""
        r1 = bulk_init(workspace, use_llm=False, dry_run=False)
        assert "mylib" in r1.created
        r2 = bulk_init(workspace, use_llm=False, dry_run=False)
        assert "mylib" not in r2.created
        assert "mylib" in r2.skipped_existing

    def test_overwrite_regenerates(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=False, overwrite=True)
        assert "existing" in result.created

    def test_overwrite_replaces_content(self, workspace: Path) -> None:
        original = (workspace / "existing" / "pyqual.yaml").read_text()
        bulk_init(workspace, use_llm=False, dry_run=False, overwrite=True)
        after = (workspace / "existing" / "pyqual.yaml").read_text()
        assert after != original
        data = yaml.safe_load(after)
        assert data["pipeline"]["name"] == "existing-quality"

    def test_hidden_dirs_ignored(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=True)
        all_names = result.created + result.skipped_existing + [n for n, _ in result.skipped_nonproject]
        assert ".cache" not in all_names

    def test_total_count(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=True)
        expected = len([d for d in workspace.iterdir() if d.is_dir() and not d.name.startswith(".")])
        assert result.total == expected

    def test_generated_yaml_is_valid(self, workspace: Path) -> None:
        result = bulk_init(workspace, use_llm=False, dry_run=False)
        for name in result.created:
            content = (workspace / name / "pyqual.yaml").read_text()
            data = yaml.safe_load(content)
            pipe = data["pipeline"]
            assert "name" in pipe
            assert "stages" in pipe
            for stage in pipe["stages"]:
                assert "name" in stage
                assert "tool" in stage or "run" in stage

    def test_pyqual_dir_created(self, workspace: Path) -> None:
        bulk_init(workspace, use_llm=False, dry_run=False)
        assert (workspace / "mylib" / ".pyqual").is_dir()
        assert (workspace / "webapp" / ".pyqual").is_dir()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchema:
    def test_schema_is_valid_json_schema(self) -> None:
        assert PROJECT_CONFIG_SCHEMA["type"] == "object"
        assert "project_type" in PROJECT_CONFIG_SCHEMA["properties"]
        assert "required" in PROJECT_CONFIG_SCHEMA

    def test_schema_has_all_project_types(self) -> None:
        types = PROJECT_CONFIG_SCHEMA["properties"]["project_type"]["enum"]
        assert "python" in types
        assert "node" in types
        assert "php" in types
        assert "rust" in types
        assert "go" in types
