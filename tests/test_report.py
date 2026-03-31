"""Tests for pyqual.report — metrics YAML report + README badge generation."""

import json
import tempfile
from pathlib import Path

import yaml

from pyqual.report import (
    BADGE_END,
    BADGE_START,
    build_badges,
    collect_all_metrics,
    generate_report,
    update_readme_badges,
)
from pyqual.config import PyqualConfig


def _make_project(tmpdir: Path, *, cc: float = 3.6, critical: int = 2,
                  vallm_pass: float = 85.0, coverage: float = 72.0) -> Path:
    """Create a minimal project tree with .pyqual/ and toon artifacts."""
    (tmpdir / ".pyqual").mkdir(exist_ok=True)
    (tmpdir / "project").mkdir(exist_ok=True)

    # analysis.toon.yaml
    (tmpdir / "project" / "analysis.toon.yaml").write_text(
        f"# code2llm | CC̄={cc} | critical:{critical}\nHEALTH:\n  ok"
    )
    # validation.toon.yaml
    (tmpdir / "project" / "validation.toon.yaml").write_text(
        f"SUMMARY:\n  scanned: 100  passed: 85 ({vallm_pass}%)  warnings: 5"
    )
    # coverage.json
    (tmpdir / ".pyqual" / "coverage.json").write_text(
        json.dumps({"totals": {"percent_covered": coverage}})
    )
    return tmpdir


def _write_config(tmpdir: Path) -> Path:
    """Write a minimal pyqual.yaml and return its path."""
    cfg_path = tmpdir / "pyqual.yaml"
    cfg_path.write_text(yaml.dump({
        "pipeline": {
            "name": "test-report",
            "metrics": {"cc_max": 15, "coverage_min": 60, "vallm_pass_min": 80},
            "stages": [
                {"name": "test", "run": "echo ok"},
            ],
        }
    }))
    return cfg_path


# ---------------------------------------------------------------------------
# collect_all_metrics
# ---------------------------------------------------------------------------

def test_collect_all_metrics_reads_toon_and_coverage() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _make_project(Path(td))
        metrics = collect_all_metrics(p)
        assert "cc" in metrics
        assert "coverage" in metrics
        assert metrics["cc"] == 3.6
        assert metrics["coverage"] == 72.0


def test_collect_all_metrics_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        metrics = collect_all_metrics(Path(td))
        assert isinstance(metrics, dict)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

def test_generate_report_creates_yaml() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _make_project(Path(td))
        cfg_path = _write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert "pyqual_report" in report
        assert report["pyqual_report"]["status"] in ("pass", "fail")
        assert report["pyqual_report"]["gates"]["total"] == 3

        # File should be written
        report_file = p / ".pyqual" / "metrics_report.yaml"
        assert report_file.exists()
        loaded = yaml.safe_load(report_file.read_text())
        assert loaded["pyqual_report"]["pipeline"] == "test-report"


def test_generate_report_gates_pass() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _make_project(Path(td), cc=3.0, coverage=90.0, vallm_pass=95.0)
        cfg_path = _write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert report["pyqual_report"]["status"] == "pass"
        assert report["pyqual_report"]["gates"]["failed"] == 0


def test_generate_report_gates_fail() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = _make_project(Path(td), cc=20.0, coverage=30.0, vallm_pass=40.0)
        cfg_path = _write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert report["pyqual_report"]["status"] == "fail"
        assert report["pyqual_report"]["gates"]["failed"] > 0


# ---------------------------------------------------------------------------
# build_badges
# ---------------------------------------------------------------------------

def test_build_badges_pass() -> None:
    metrics = {"cc": 3.6, "coverage": 85.0, "vallm_pass": 92.0}
    line = build_badges(metrics, gates_passed=True)
    assert "pyqual-pass-brightgreen" in line
    assert "CC" in line
    assert "coverage" in line
    assert "vallm" in line


def test_build_badges_fail() -> None:
    metrics = {"cc": 25.0, "coverage": 30.0}
    line = build_badges(metrics, gates_passed=False)
    assert "pyqual-fail-red" in line


def test_build_badges_empty_metrics() -> None:
    line = build_badges({}, gates_passed=True)
    assert "pyqual-pass" in line
    # No metric badges, just overall status
    assert line.count("![") == 1


# ---------------------------------------------------------------------------
# update_readme_badges
# ---------------------------------------------------------------------------

def test_update_readme_inserts_markers_after_existing_badges() -> None:
    with tempfile.TemporaryDirectory() as td:
        readme = Path(td) / "README.md"
        readme.write_text(
            "![Logo](logo.png)\n"
            "![Version](https://img.shields.io/badge/version-1.0-blue)\n"
            "\n"
            "# My Project\n"
            "\nSome description.\n"
        )
        changed = update_readme_badges(readme, {"cc": 5.0, "coverage": 80.0}, True)
        assert changed is True

        text = readme.read_text()
        assert BADGE_START in text
        assert BADGE_END in text
        # Markers should be after badge lines but before the heading
        start_idx = text.index(BADGE_START)
        heading_idx = text.index("# My Project")
        assert start_idx < heading_idx


def test_update_readme_replaces_existing_markers() -> None:
    with tempfile.TemporaryDirectory() as td:
        readme = Path(td) / "README.md"
        readme.write_text(
            "# Project\n"
            f"{BADGE_START}\n"
            "![old](https://old-badge)\n"
            f"{BADGE_END}\n"
            "\nContent.\n"
        )
        changed = update_readme_badges(readme, {"cc": 3.0}, True)
        assert changed is True

        text = readme.read_text()
        assert "old-badge" not in text
        assert "pyqual-pass" in text
        # Should still have exactly one start/end pair
        assert text.count(BADGE_START) == 1
        assert text.count(BADGE_END) == 1


def test_update_readme_no_change_when_identical() -> None:
    with tempfile.TemporaryDirectory() as td:
        readme = Path(td) / "README.md"
        # First write
        readme.write_text("# Project\n")
        update_readme_badges(readme, {"cc": 3.0}, True)

        # Second write with same data — should detect no change
        text_before = readme.read_text()
        changed = update_readme_badges(readme, {"cc": 3.0}, True)
        assert changed is False
        assert readme.read_text() == text_before


def test_update_readme_no_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        readme = Path(td) / "README.md"
        changed = update_readme_badges(readme, {"cc": 3.0}, True)
        assert changed is False


def test_update_readme_inserts_at_top_when_no_badges() -> None:
    with tempfile.TemporaryDirectory() as td:
        readme = Path(td) / "README.md"
        readme.write_text("# Project\n\nDescription.\n")
        changed = update_readme_badges(readme, {"cc": 3.0}, True)
        assert changed is True

        text = readme.read_text()
        # Markers should be at the top (before heading)
        assert text.startswith(BADGE_START)


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------

def test_run_integration() -> None:
    from pyqual.report import run

    with tempfile.TemporaryDirectory() as td:
        p = _make_project(Path(td), cc=3.0, coverage=90.0, vallm_pass=95.0)
        cfg_path = _write_config(p)
        readme = p / "README.md"
        readme.write_text("# Test\n\nHello.\n")

        rc = run(workdir=p, config_path=cfg_path, readme_path=readme)
        assert rc == 0

        # Report YAML exists
        assert (p / ".pyqual" / "metrics_report.yaml").exists()

        # Badges in README
        text = readme.read_text()
        assert BADGE_START in text
        assert "pyqual-pass" in text
