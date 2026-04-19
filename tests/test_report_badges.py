from __future__ import annotations

from pyqual.report import build_badges


def test_build_badges_pass() -> None:
    metrics = {"cc": 3.6, "coverage": 85.0, "vallm_pass": 92.0}
    line = build_badges(metrics, gates_passed=True, gates_passed_count=3, gates_total=3)
    assert "pyqual-pass-brightgreen" in line
    assert "CC" in line
    assert "coverage" in line
    assert "vallm" in line


def test_build_badges_fail() -> None:
    metrics = {"cc": 25.0, "coverage": 30.0}
    line = build_badges(metrics, gates_passed=False, gates_passed_count=0, gates_total=2)
    assert "pyqual-fail-red" in line


def test_build_badges_empty_metrics_no_project_meta() -> None:
    line = build_badges({}, gates_passed=True)
    assert "pyqual-pass" in line
    assert line.count("![") == 1


def test_build_badges_with_project_meta() -> None:
    metrics = {"cc": 5.0, "coverage": 80.0}
    meta = {
        "version": "1.2.3",
        "python": ">=3.9",
        "license": "MIT",
        "ai_cost": 3.50,
        "ai_commits": 42,
        "human_hours": 10.5,
        "model": "openrouter/qwen/qwen3-coder-next",
    }
    block = build_badges(metrics, gates_passed=True, project_meta=meta,
                         gates_passed_count=2, gates_total=2)
    lines = block.split("\n")
    assert len(lines) == 2
    assert "version" in lines[0].lower() or "Version" in lines[0]
    assert "AI Cost" in lines[0] or "AI%20Cost" in lines[0]
    assert "Human Time" in lines[0] or "Human%20Time" in lines[0]
    assert "Model" in lines[0]
    assert "license" in lines[0].lower() or "License" in lines[0]
    assert "pyqual-pass" in lines[1]
    assert "gates" in lines[1]
    assert "CC" in lines[1]


def test_build_badges_gates_ratio() -> None:
    metrics = {"cc": 5.0}
    block = build_badges(metrics, gates_passed=False,
                         gates_passed_count=1, gates_total=3)
    assert "1%2F3" in block or "1/3" in block
