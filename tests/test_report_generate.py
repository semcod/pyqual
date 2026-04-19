from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from pyqual.config import PyqualConfig
from pyqual.report import generate_report

from .test_report_helpers import make_project, write_config


def test_generate_report_creates_yaml() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = make_project(Path(td))
        cfg_path = write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert "pyqual_report" in report
        assert report["pyqual_report"]["status"] in ("pass", "fail")
        assert report["pyqual_report"]["gates"]["total"] == 3
        assert "project" in report["pyqual_report"]

        report_file = p / ".pyqual" / "metrics_report.yaml"
        assert report_file.exists()
        loaded = yaml.safe_load(report_file.read_text())
        assert loaded["pyqual_report"]["pipeline"] == "test-report"


def test_generate_report_gates_pass() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = make_project(Path(td), cc=3.0, coverage=90.0, vallm_pass=95.0)
        cfg_path = write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert report["pyqual_report"]["status"] == "pass"
        assert report["pyqual_report"]["gates"]["failed"] == 0


def test_generate_report_gates_fail() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = make_project(Path(td), cc=20.0, coverage=30.0, vallm_pass=40.0)
        cfg_path = write_config(p)
        config = PyqualConfig.load(cfg_path)

        report = generate_report(config, p)
        assert report["pyqual_report"]["status"] == "fail"
        assert report["pyqual_report"]["gates"]["failed"] > 0
