"""Tests for Pipeline._should_run_stage — verify after_fix, after_verify_fix, metrics_pass logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyqual.config import StageConfig
from pyqual.pipeline import Pipeline, StageResult


def _stage(name: str, skipped: bool = False, passed: bool = True) -> StageResult:
    return StageResult(
        name=name, returncode=0 if passed else 1,
        stdout="", stderr="", duration=0.1, skipped=skipped,
    )


@pytest.fixture
def pipeline(tmp_path: Path) -> Pipeline:
    """Create a Pipeline with minimal config for testing _should_run_stage."""
    cfg_file = tmp_path / "pyqual.yaml"
    cfg_file.write_text(
        "pipeline:\n  name: test\n  stages: []\n  metrics: {}\n"
    )
    from pyqual.config import PyqualConfig
    cfg = PyqualConfig.load(str(cfg_file))
    return Pipeline(cfg, workdir=tmp_path)


class TestAfterFix:
    """after_fix should trigger when ANY stage with 'fix' in its name ran."""

    def test_exact_name_fix(self, pipeline: Pipeline):
        sc = StageConfig(name="verify", when="after_fix")
        stages = [_stage("fix")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is True

    def test_fix_regression_name(self, pipeline: Pipeline):
        """The bug fix: 'fix_regression' should match after_fix."""
        sc = StageConfig(name="verify", when="after_fix")
        stages = [_stage("fix_regression")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is True

    def test_auto_fix_name(self, pipeline: Pipeline):
        sc = StageConfig(name="verify", when="after_fix")
        stages = [_stage("auto_fix")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is True

    def test_no_fix_ran(self, pipeline: Pipeline):
        sc = StageConfig(name="verify", when="after_fix")
        stages = [_stage("validate"), _stage("test")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is False

    def test_fix_skipped(self, pipeline: Pipeline):
        sc = StageConfig(name="verify", when="after_fix")
        stages = [_stage("fix", skipped=True)]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is False

    def test_empty_stages(self, pipeline: Pipeline):
        sc = StageConfig(name="verify", when="after_fix")
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=[]) is False
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=None) is False


class TestAfterVerifyFix:
    """after_verify_fix should trigger when ANY stage with 'verify' in its name ran."""

    def test_verify_ran(self, pipeline: Pipeline):
        sc = StageConfig(name="report", when="after_verify_fix")
        stages = [_stage("fix"), _stage("verify_fix")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is True

    def test_verify_not_ran(self, pipeline: Pipeline):
        sc = StageConfig(name="report", when="after_verify_fix")
        stages = [_stage("fix"), _stage("test")]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is False

    def test_verify_skipped(self, pipeline: Pipeline):
        sc = StageConfig(name="report", when="after_verify_fix")
        stages = [_stage("verify_fix", skipped=True)]
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=stages) is False

    def test_empty_stages(self, pipeline: Pipeline):
        sc = StageConfig(name="report", when="after_verify_fix")
        assert pipeline._should_run_stage(sc, gates_pass=False, stages_so_far=None) is False


class TestMetricsPass:
    """metrics_pass should trigger push/publish when all gates pass."""

    def test_gates_pass(self, pipeline: Pipeline):
        sc = StageConfig(name="push", when="metrics_pass")
        assert pipeline._should_run_stage(sc, gates_pass=True) is True

    def test_gates_fail(self, pipeline: Pipeline):
        sc = StageConfig(name="push", when="metrics_pass")
        assert pipeline._should_run_stage(sc, gates_pass=False) is False


class TestMetricsFail:
    """metrics_fail should trigger fix stages when gates fail."""

    def test_gates_fail(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", when="metrics_fail")
        assert pipeline._should_run_stage(sc, gates_pass=False) is True

    def test_gates_pass(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", when="metrics_fail")
        assert pipeline._should_run_stage(sc, gates_pass=True) is False


class TestAlwaysAndFirstIteration:
    def test_always(self, pipeline: Pipeline):
        sc = StageConfig(name="validate", when="always")
        assert pipeline._should_run_stage(sc, gates_pass=True) is True
        assert pipeline._should_run_stage(sc, gates_pass=False) is True

    def test_first_iteration_on_first(self, pipeline: Pipeline):
        sc = StageConfig(name="baseline", when="first_iteration")
        assert pipeline._should_run_stage(sc, gates_pass=False, iteration=1) is True

    def test_first_iteration_on_second(self, pipeline: Pipeline):
        sc = StageConfig(name="baseline", when="first_iteration")
        assert pipeline._should_run_stage(sc, gates_pass=False, iteration=2) is False


class TestFullPipelineFlow:
    """Simulate full pipeline flow to verify stage ordering with push/publish."""

    def test_pass_flow_runs_push_skips_fix(self, pipeline: Pipeline):
        """When gates pass: fix=skipped, push=runs, verify=skipped."""
        stages_config = [
            StageConfig(name="validate", when="always"),
            StageConfig(name="fix", when="metrics_fail"),
            StageConfig(name="verify", when="after_fix"),
            StageConfig(name="push", when="metrics_pass"),
            StageConfig(name="publish", when="metrics_pass"),
        ]
        ran = []
        skipped = []
        stages_so_far: list[StageResult] = []
        for sc in stages_config:
            should = pipeline._should_run_stage(
                sc, gates_pass=True, stages_so_far=stages_so_far, iteration=1,
            )
            sr = _stage(sc.name, skipped=not should)
            stages_so_far.append(sr)
            (ran if should else skipped).append(sc.name)

        assert "validate" in ran
        assert "push" in ran
        assert "publish" in ran
        assert "fix" in skipped
        assert "verify" in skipped

    def test_fail_flow_runs_fix_skips_push(self, pipeline: Pipeline):
        """When gates fail: fix=runs, verify=runs, push=skipped."""
        stages_config = [
            StageConfig(name="validate", when="always"),
            StageConfig(name="fix_regression", when="metrics_fail"),
            StageConfig(name="verify_fix", when="after_fix"),
            StageConfig(name="push", when="metrics_pass"),
            StageConfig(name="regression_report", when="after_verify_fix"),
        ]
        ran = []
        skipped = []
        stages_so_far: list[StageResult] = []
        for sc in stages_config:
            should = pipeline._should_run_stage(
                sc, gates_pass=False, stages_so_far=stages_so_far, iteration=1,
            )
            sr = _stage(sc.name, skipped=not should)
            stages_so_far.append(sr)
            (ran if should else skipped).append(sc.name)

        assert "validate" in ran
        assert "fix_regression" in ran
        assert "verify_fix" in ran
        assert "regression_report" in ran
        assert "push" in skipped
