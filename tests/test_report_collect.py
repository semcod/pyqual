from __future__ import annotations

import tempfile
from pathlib import Path

from pyqual.report import collect_all_metrics

from .test_report_helpers import make_project


def test_collect_all_metrics_reads_toon_and_coverage() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = make_project(Path(td))
        metrics = collect_all_metrics(p)
        assert "cc" in metrics
        assert "coverage" in metrics
        assert metrics["cc"] == 3.6
        assert metrics["coverage"] == 72.0


def test_collect_all_metrics_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        metrics = collect_all_metrics(Path(td))
        assert isinstance(metrics, dict)
