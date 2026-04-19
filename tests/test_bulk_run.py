"""Tests for pyqual.bulk_run — bulk pipeline runner with dashboard."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from pyqual.bulk_run import (
    ProjectRunState,
    RunStatus,
    _parse_output_line,
    build_dashboard_table,
    bulk_run,
    discover_projects,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a workspace with projects that have pyqual.yaml."""
    # Project with valid pyqual.yaml
    p1 = tmp_path / "alpha"
    p1.mkdir()
    (p1 / "pyqual.yaml").write_text(yaml.dump({
        "pipeline": {
            "name": "alpha-quality",
            "metrics": {"cc_max": 15},
            "stages": [
                {"name": "lint", "run": "echo lint ok"},
                {"name": "test", "run": "echo test ok"},
            ],
            "loop": {"max_iterations": 2, "on_fail": "report"},
        }
    }))

    # Another project
    p2 = tmp_path / "beta"
    p2.mkdir()
    (p2 / "pyqual.yaml").write_text(yaml.dump({
        "pipeline": {
            "name": "beta-quality",
            "metrics": {"cc_max": 10},
            "stages": [
                {"name": "check", "run": "echo check ok"},
            ],
            "loop": {"max_iterations": 3, "on_fail": "report"},
        }
    }))

    # Directory without pyqual.yaml (should be ignored)
    p3 = tmp_path / "no-config"
    p3.mkdir()
    (p3 / "README.md").write_text("hello")

    # Hidden dir
    h = tmp_path / ".hidden"
    h.mkdir()
    (h / "pyqual.yaml").write_text("pipeline:\n  name: x\n  stages: []\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Discover tests
# ---------------------------------------------------------------------------

class TestDiscoverProjects:
    def test_finds_projects_with_pyqual_yaml(self, workspace: Path) -> None:
        states = discover_projects(workspace)
        names = [s.name for s in states]
        assert "alpha" in names
        assert "beta" in names

    def test_ignores_dirs_without_config(self, workspace: Path) -> None:
        states = discover_projects(workspace)
        names = [s.name for s in states]
        assert "no-config" not in names

    def test_ignores_hidden_dirs(self, workspace: Path) -> None:
        states = discover_projects(workspace)
        names = [s.name for s in states]
        assert ".hidden" not in names

    def test_all_start_as_queued(self, workspace: Path) -> None:
        states = discover_projects(workspace)
        for s in states:
            assert s.status == RunStatus.QUEUED

    def test_paths_are_correct(self, workspace: Path) -> None:
        states = discover_projects(workspace)
        for s in states:
            assert s.path == workspace / s.name


# ---------------------------------------------------------------------------
# Output parser tests
# ---------------------------------------------------------------------------

class TestParseOutputLine:
    def test_parse_iteration(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "─── Iteration 2 ───")
        assert s.iteration == 2

    def test_parse_stage_pass(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "  ✅ lint (1.2s)")
        assert s.stages_done == 1
        assert s.current_stage == "lint"

    def test_parse_stage_fail(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "  ❌ test (3.4s)")
        assert s.stages_done == 1
        assert s.current_stage == "test"

    def test_parse_stage_skip(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "  ⏭ fix (skipped)")
        assert s.stages_done == 1

    def test_parse_all_gates_passed(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        s.status = RunStatus.RUNNING
        _parse_output_line(s, "All gates passed!")
        assert s.status == RunStatus.PASSED

    def test_parse_gates_not_met(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        s.status = RunStatus.RUNNING
        _parse_output_line(s, "Gates not met after 3 iterations.")
        assert s.status == RunStatus.FAILED

    def test_empty_line_no_crash(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "")
        _parse_output_line(s, "   ")

    def test_last_line_captured(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"))
        _parse_output_line(s, "some random output here")
        assert s.last_line == "some random output here"

    def test_gate_line_increments_passed(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"), gates_total=2)
        _parse_output_line(s, "  ✅ coverage: 85.0 ≥ 80.0")
        assert s.gates_passed == 1

    def test_gate_line_failed_does_not_increment(self) -> None:
        s = ProjectRunState(name="test", path=Path("/tmp/test"), gates_total=2)
        _parse_output_line(s, "  ❌ coverage: 42.0 ≥ 80.0")
        assert s.gates_passed == 0

    def test_gates_reset_on_new_iteration(self) -> None:
        """gates_passed must NOT accumulate across iterations (regression: showed 3/2)."""
        s = ProjectRunState(name="test", path=Path("/tmp/test"), gates_total=2)
        # iteration 1: 1 gate passes
        _parse_output_line(s, "─── Iteration 1 ───")
        _parse_output_line(s, "  ✅ coverage: 85.0 ≥ 80.0")
        assert s.gates_passed == 1
        # iteration 2: 1 gate passes — counter must reset, not reach 2
        _parse_output_line(s, "─── Iteration 2 ───")
        assert s.gates_passed == 0
        _parse_output_line(s, "  ✅ coverage: 90.0 ≥ 80.0")
        assert s.gates_passed == 1
        # iteration 3: both gates pass
        _parse_output_line(s, "─── Iteration 3 ───")
        _parse_output_line(s, "  ✅ coverage: 92.0 ≥ 80.0")
        _parse_output_line(s, "  ✅ cc: 8.0 ≤ 15.0")
        assert s.gates_passed == 2
        assert s.gates_passed <= s.gates_total  # never exceeds total


# ---------------------------------------------------------------------------
# ProjectRunState tests
# ---------------------------------------------------------------------------

class TestProjectRunState:
    def test_progress_pct_zero_when_queued(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"))
        assert s.progress_pct == 0

    def test_progress_pct_mid_run(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"),
                            stages_total=4, max_iterations=2,
                            iteration=1, stages_done=2)
        assert s.progress_pct == 25  # 2 of 8 total

    def test_elapsed_zero_when_not_started(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"))
        assert s.elapsed == 0.0

    def test_elapsed_fixed_when_finished(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"),
                            status=RunStatus.PASSED, duration=5.5,
                            start_time=time.monotonic() - 10)
        assert s.elapsed == 5.5

    def test_gates_label(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"),
                            gates_passed=2, gates_total=3)
        assert s.gates_label == "2/3"

    def test_gates_label_empty_when_no_gates(self) -> None:
        s = ProjectRunState(name="t", path=Path("/tmp"))
        assert s.gates_label == ""


# ---------------------------------------------------------------------------
# Dashboard table tests
# ---------------------------------------------------------------------------

class TestBuildDashboardTable:
    def test_builds_table_with_correct_columns(self) -> None:
        states = [
            ProjectRunState(name="a", path=Path("/a"), status=RunStatus.PASSED, duration=1.0),
            ProjectRunState(name="b", path=Path("/b"), status=RunStatus.RUNNING,
                            start_time=time.monotonic(), iteration=1,
                            current_stage="test", max_iterations=3),
            ProjectRunState(name="c", path=Path("/c"), status=RunStatus.QUEUED),
        ]
        table = build_dashboard_table(states)
        assert table.row_count == 3
        col_names = [c.header for c in table.columns]
        assert "Project" in col_names
        assert "Status" in col_names
        assert "Iter" in col_names
        assert "Gates" in col_names
        assert "Time" in col_names

    def test_verbose_adds_last_output_column(self) -> None:
        states = [ProjectRunState(name="a", path=Path("/a"), last_line="hello")]
        table = build_dashboard_table(states, show_last_line=True)
        col_names = [c.header for c in table.columns]
        assert "Last Output" in col_names

    def test_title_has_counts(self) -> None:
        states = [
            ProjectRunState(name="a", path=Path("/a"), status=RunStatus.PASSED),
            ProjectRunState(name="b", path=Path("/b"), status=RunStatus.FAILED),
            ProjectRunState(name="c", path=Path("/c"), status=RunStatus.RUNNING,
                            start_time=time.monotonic()),
        ]
        table = build_dashboard_table(states)
        assert "pass:1" in table.title
        assert "fail:1" in table.title
        assert "running:1" in table.title


# ---------------------------------------------------------------------------
# Bulk run integration (with mock subprocess)
# ---------------------------------------------------------------------------

class TestBulkRun:
    def test_skips_missing_pyqual_cmd(self, workspace: Path) -> None:
        result = bulk_run(
            workspace,
            parallel=2,
            pyqual_cmd="nonexistent_pyqual_binary_xyz",
        )
        # All should error because the binary doesn't exist
        assert len(result.errors) >= 2

    def test_filter_only_runs_selected(self, workspace: Path) -> None:
        callbacks: list = []
        result = bulk_run(
            workspace,
            parallel=1,
            filter_names=["alpha"],
            pyqual_cmd="nonexistent_pyqual_binary_xyz",
        )
        assert "beta" in result.skipped
        # alpha tried to run (and errored because binary missing)
        assert any(name == "alpha" for name, _ in result.errors)

    def test_result_totals(self, workspace: Path) -> None:
        result = bulk_run(
            workspace,
            parallel=2,
            pyqual_cmd="nonexistent_pyqual_binary_xyz",
        )
        total = len(result.passed) + len(result.failed) + len(result.errors) + len(result.skipped)
        assert total == 2  # alpha + beta (no-config has no pyqual.yaml)

    def test_live_callback_called(self, workspace: Path) -> None:
        calls: list = []

        def cb(states):
            calls.append(len(states))

        bulk_run(
            workspace,
            parallel=1,
            pyqual_cmd="nonexistent_pyqual_binary_xyz",
            live_callback=cb,
        )
        assert len(calls) > 0


# ---------------------------------------------------------------------------
# RunStatus tests
# ---------------------------------------------------------------------------

class TestRunStatus:
    def test_all_statuses_have_icon(self) -> None:
        from pyqual.bulk_run import STATUS_ICON
        for status in RunStatus:
            assert status in STATUS_ICON

    def test_all_statuses_have_style(self) -> None:
        from pyqual.bulk_run import STATUS_STYLE
        for status in RunStatus:
            assert status in STATUS_STYLE
