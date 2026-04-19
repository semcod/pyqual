from __future__ import annotations

from pyqual.report import _build_quality_badges


def test_quality_badges_with_extra_metrics() -> None:
    metrics = {
        "cc": 5.0,
        "coverage": 85.0,
        "maintainability_index": 72.0,
        "ruff_errors": 0.0,
        "mypy_errors": 3.0,
        "docstring_coverage": 90.0,
    }
    line = _build_quality_badges(metrics, gates_passed=True, gates_passed_count=3, gates_total=3)
    assert "CC" in line
    assert "coverage" in line
    assert "maintainability" in line.lower() or "Maintainability" in line
    assert "ruff" in line.lower()
    assert "mypy" in line.lower()
    assert "docstring" in line.lower()


def test_quality_badges_no_metrics() -> None:
    line = _build_quality_badges({}, gates_passed=False, gates_passed_count=0, gates_total=0)
    assert "pyqual-fail" in line or "pyqual" in line
