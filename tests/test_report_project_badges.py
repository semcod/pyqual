from __future__ import annotations

from pyqual.report import _build_project_badges


def test_project_badges_all_fields() -> None:
    meta = {
        "version": "0.1.0",
        "python": ">=3.10",
        "license": "Apache-2.0",
        "ai_cost": 7.50,
        "ai_commits": 61,
        "human_hours": 20.3,
        "model": "openrouter/qwen/qwen3-coder-next",
    }
    line = _build_project_badges(meta)
    assert "0.1.0" in line
    assert "3.10" in line
    assert "Apache" in line
    assert "$7.50" in line or "%247.50" in line
    assert "20.3h" in line
    assert "Model" in line


def test_project_badges_empty_meta() -> None:
    line = _build_project_badges({})
    assert line == ""


def test_project_badges_ai_cost_colors() -> None:
    line = _build_project_badges({"ai_cost": 0.50})
    assert "brightgreen" in line
    line = _build_project_badges({"ai_cost": 3.0})
    assert "green" in line
    line = _build_project_badges({"ai_cost": 8.0})
    assert "orange" in line
    line = _build_project_badges({"ai_cost": 15.0})
    assert "red" in line
