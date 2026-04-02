"""Tests for Pipeline._should_run_stage, _is_fix_stage, _archive_llx_report, and history CLI."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyqual.config import StageConfig
from pyqual.constants import LLX_HISTORY_FILE, LLX_MCP_REPORT
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

    def test_fail_flow_runs_delivery_stages_after_fix(self, pipeline: Pipeline):
        """When gates fail: fix/rerun stages run and delivery stages follow after fix."""
        stages_config = [
            StageConfig(name="validate", when="always"),
            StageConfig(name="fix", when="metrics_fail"),
            StageConfig(name="verify", when="after_fix"),
            StageConfig(name="push", when="after_fix"),
            StageConfig(name="publish", when="after_fix"),
            StageConfig(name="close_tasks", when="after_fix"),
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
        assert "fix" in ran
        assert "verify" in ran
        assert "push" in ran
        assert "publish" in ran
        assert "close_tasks" in ran
        assert not skipped


class TestIsFixStage:
    """_is_fix_stage detects fix/repair stages by tool or command keywords."""

    def test_llx_fix_tool(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", tool="llx-fix")
        assert pipeline._is_fix_stage(sc) is True

    def test_aider_tool(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", tool="aider")
        assert pipeline._is_fix_stage(sc) is True

    def test_llx_in_run_command(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", run="llx fix . --apply")
        assert pipeline._is_fix_stage(sc) is True

    def test_repair_in_run_command(self, pipeline: Pipeline):
        sc = StageConfig(name="auto_repair", run="python repair.py")
        assert pipeline._is_fix_stage(sc) is True

    def test_non_fix_stage(self, pipeline: Pipeline):
        sc = StageConfig(name="validate", tool="ruff")
        assert pipeline._is_fix_stage(sc) is False

    def test_non_fix_run_command(self, pipeline: Pipeline):
        sc = StageConfig(name="test", run="pytest -q")
        assert pipeline._is_fix_stage(sc) is False


class TestArchiveLlxReport:
    """_archive_llx_report appends to llx_history.jsonl."""

    def test_archives_without_report_file(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", run="llx fix .")
        result = _stage("fix", passed=True)
        result.command = "llx fix ."
        result.stdout = "Applied 2 changes"
        pipeline._archive_llx_report(sc, result)

        history_path = pipeline.workdir / LLX_HISTORY_FILE
        assert history_path.exists()
        entries = [json.loads(l) for l in history_path.read_text().splitlines() if l.strip()]
        assert len(entries) == 1
        assert entries[0]["stage"] == "fix"
        assert entries[0]["ok"] is True
        assert "stdout_tail" in entries[0]

    def test_archives_with_report_file(self, pipeline: Pipeline):
        report_path = pipeline.workdir / LLX_MCP_REPORT
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "success": True,
            "prompt": "Fix the code",
            "model": "test-model",
            "issues": [{"file": "a.py", "message": "bug"}],
        }
        report_path.write_text(json.dumps(report))

        sc = StageConfig(name="fix", run="llx fix .")
        result = _stage("fix", passed=True)
        result.command = "llx fix ."
        pipeline._archive_llx_report(sc, result)

        history_path = pipeline.workdir / LLX_HISTORY_FILE
        entries = [json.loads(l) for l in history_path.read_text().splitlines() if l.strip()]
        assert len(entries) == 1
        assert entries[0]["prompt"] == "Fix the code"
        assert entries[0]["model"] == "test-model"
        assert entries[0]["issues_count"] == 1
        assert entries[0]["success"] is True

    def test_multiple_archives_append(self, pipeline: Pipeline):
        sc = StageConfig(name="fix", run="llx fix .")
        for i in range(3):
            result = _stage("fix", passed=(i % 2 == 0))
            result.command = "llx fix ."
            pipeline._archive_llx_report(sc, result)

        history_path = pipeline.workdir / LLX_HISTORY_FILE
        entries = [json.loads(l) for l in history_path.read_text().splitlines() if l.strip()]
        assert len(entries) == 3
        assert entries[0]["ok"] is True
        assert entries[1]["ok"] is False
        assert entries[2]["ok"] is True


class TestStreamingExecution:
    """_execute_streaming sends lines to on_stage_output in real time."""

    def _make_pipeline(self, tmp_path: Path, stream: bool = True,
                       on_output=None) -> Pipeline:
        cfg_file = tmp_path / "pyqual.yaml"
        cfg_file.write_text(
            "pipeline:\n  name: test\n  stages: []\n  metrics: {}\n"
        )
        from pyqual.config import PyqualConfig
        cfg = PyqualConfig.load(str(cfg_file))
        return Pipeline(cfg, workdir=tmp_path, stream=stream,
                        on_stage_output=on_output)

    def test_captures_stdout_lines(self, tmp_path: Path):
        collected: list[tuple[str, str, bool]] = []

        def on_output(name, line, is_stderr):
            collected.append((name, line, is_stderr))

        pipe = self._make_pipeline(tmp_path, stream=True, on_output=on_output)
        sc = StageConfig(name="echo_test", run="echo hello && echo world")
        result = pipe._execute_streaming(
            sc, "echo hello && echo world", False,
            dict(os.environ), time.monotonic(),
        )
        assert result.passed
        assert "hello" in result.stdout
        assert "world" in result.stdout
        stdout_lines = [(n, l) for n, l, s in collected if not s]
        assert any("hello" in l for _, l in stdout_lines)
        assert any("world" in l for _, l in stdout_lines)

    def test_captures_stderr_lines(self, tmp_path: Path):
        collected: list[tuple[str, str, bool]] = []

        def on_output(name, line, is_stderr):
            collected.append((name, line, is_stderr))

        pipe = self._make_pipeline(tmp_path, stream=True, on_output=on_output)
        sc = StageConfig(name="err_test", run="echo oops >&2")
        result = pipe._execute_streaming(
            sc, "echo oops >&2", False,
            dict(os.environ), time.monotonic(),
        )
        assert "oops" in result.stderr
        stderr_lines = [(n, l) for n, l, s in collected if s]
        assert any("oops" in l for _, l in stderr_lines)

    def test_streaming_still_returns_full_output(self, tmp_path: Path):
        """Streaming mode must still collect full stdout/stderr for the report."""
        pipe = self._make_pipeline(tmp_path, stream=True)
        sc = StageConfig(name="multi", run="echo line1 && echo line2 && echo err1 >&2")
        result = pipe._execute_streaming(
            sc, sc.run, False, dict(os.environ), time.monotonic(),
        )
        assert "line1" in result.stdout
        assert "line2" in result.stdout
        assert "err1" in result.stderr

    def test_non_streaming_does_not_call_output(self, tmp_path: Path):
        """When stream=False, on_stage_output is never called."""
        called = []

        def on_output(name, line, is_stderr):
            called.append(1)

        pipe = self._make_pipeline(tmp_path, stream=False, on_output=on_output)
        sc = StageConfig(name="test", run="echo quiet")
        result = pipe._execute_captured(
            sc, "echo quiet", False, dict(os.environ), time.monotonic(),
        )
        assert result.passed
        assert len(called) == 0

    def test_execute_stage_dispatches_to_streaming(self, tmp_path: Path):
        """_execute_stage uses streaming when self.stream is True."""
        collected: list[tuple[str, str, bool]] = []

        def on_output(name, line, is_stderr):
            collected.append((name, line, is_stderr))

        pipe = self._make_pipeline(tmp_path, stream=True, on_output=on_output)
        sc = StageConfig(name="fix", run="echo 'llx fix applied'")
        result = pipe._execute_stage(sc, dry_run=False)
        assert result.passed
        assert "llx fix applied" in result.stdout
        assert len(collected) > 0


class TestSmartStageDefaults:
    """Tests for _STAGE_WHEN_DEFAULTS auto-inference in StageConfig."""

    def test_fix_stage_defaults_to_metrics_fail(self):
        s = StageConfig(name="fix", run="llx fix .")
        assert s.when == "metrics_fail"

    def test_fix_regression_defaults_to_metrics_fail(self):
        s = StageConfig(name="fix_regression", run="llx fix .")
        assert s.when == "metrics_fail"

    def test_prefact_defaults_to_metrics_fail(self):
        s = StageConfig(name="prefact", tool="prefact")
        assert s.when == "metrics_fail"

    def test_verify_defaults_to_after_fix(self):
        s = StageConfig(name="verify", run="echo ok")
        assert s.when == "after_fix"

    def test_verify_fix_defaults_to_after_fix(self):
        s = StageConfig(name="verify_fix", run="echo ok")
        assert s.when == "after_fix"

    def test_analyze_defaults_to_first_iteration(self):
        s = StageConfig(name="analyze", tool="code2llm")
        assert s.when == "first_iteration"

    def test_push_defaults_to_metrics_pass(self):
        s = StageConfig(name="push", run="goal push")
        assert s.when == "metrics_pass"

    def test_publish_defaults_to_metrics_pass(self):
        s = StageConfig(name="publish", run="goal publish")
        assert s.when == "metrics_pass"

    def test_deploy_defaults_to_metrics_pass(self):
        s = StageConfig(name="deploy", run="deploy.sh")
        assert s.when == "metrics_pass"

    def test_regression_report_defaults_to_after_verify_fix(self):
        s = StageConfig(name="regression_report", run="regix report")
        assert s.when == "after_verify_fix"

    def test_unknown_stage_defaults_to_always(self):
        s = StageConfig(name="custom_step", run="echo hello")
        assert s.when == "always"

    def test_test_stage_defaults_to_always(self):
        s = StageConfig(name="test", tool="pytest")
        assert s.when == "always"

    def test_explicit_when_overrides_default(self):
        s = StageConfig(name="fix", run="llx fix .", when="always")
        assert s.when == "always"

    def test_explicit_when_on_push_overrides_default(self):
        s = StageConfig(name="push", run="git push", when="after_fix")
        assert s.when == "after_fix"
