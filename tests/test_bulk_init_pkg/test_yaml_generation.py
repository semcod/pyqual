from __future__ import annotations

import yaml

from pyqual.bulk_init import ProjectConfig, generate_pyqual_yaml


class TestGenerateYaml:
    def test_python_yaml_is_valid(self) -> None:
        cfg = ProjectConfig(project_type="python", has_tests=True, test_command="python3 -m pytest -q", lint_tool_preset="ruff")
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
        cfg = ProjectConfig(project_type="node", has_tests=True, test_command="npm test", lint_command="npm run lint", build_command="npm run build")
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
