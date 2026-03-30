from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import pyqual.cli as cli_module
from pyqual.cli import app
from pyqual import tickets as tickets_module
from pyqual import pipeline as pipeline_module


def test_sync_todo_tickets_uses_planfile_markdown_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool, str, bool]] = []

    def fake_sync_integration(
        integration_name: str,
        directory: str,
        dry_run: bool,
        direction: str,
        show_header: bool = True,
    ) -> None:
        calls.append((integration_name, directory, dry_run, direction, show_header))

    monkeypatch.setattr(tickets_module, "_load_sync_integration", lambda: fake_sync_integration)

    tickets_module.sync_todo_tickets(workdir=tmp_path, dry_run=True, direction="from")

    assert calls == [("markdown", str(tmp_path), True, "from", True)]


def test_sync_github_tickets_uses_planfile_github_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool, str, bool]] = []

    def fake_sync_integration(
        integration_name: str,
        directory: str,
        dry_run: bool,
        direction: str,
        show_header: bool = True,
    ) -> None:
        calls.append((integration_name, directory, dry_run, direction, show_header))

    monkeypatch.setattr(tickets_module, "_load_sync_integration", lambda: fake_sync_integration)

    tickets_module.sync_github_tickets(workdir=tmp_path, dry_run=False, direction="both")

    assert calls == [("github", str(tmp_path), False, "both", True)]


def test_sync_all_tickets_calls_both_backends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool, str, bool]] = []

    def fake_sync_integration(
        integration_name: str,
        directory: str,
        dry_run: bool,
        direction: str,
        show_header: bool = True,
    ) -> None:
        calls.append((integration_name, directory, dry_run, direction, show_header))

    monkeypatch.setattr(tickets_module, "_load_sync_integration", lambda: fake_sync_integration)

    tickets_module.sync_all_tickets(workdir=tmp_path, dry_run=False, direction="to")

    assert calls == [
        ("markdown", str(tmp_path), False, "to", True),
        ("github", str(tmp_path), False, "to", False),
    ]


def test_tickets_todo_cli_invokes_sync_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_sync_todo_tickets(*, workdir: Path, dry_run: bool, direction: str) -> None:
        captured.update({"workdir": workdir, "dry_run": dry_run, "direction": direction})

    monkeypatch.setattr(cli_module, "sync_todo_tickets", fake_sync_todo_tickets)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "tickets",
            "todo",
            "--workdir",
            str(tmp_path),
            "--dry-run",
            "--direction",
            "from",
        ],
    )

    assert result.exit_code == 0
    assert captured == {"workdir": tmp_path, "dry_run": True, "direction": "from"}


def test_run_on_fail_create_ticket_syncs_todo_tickets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "pyqual.yaml"
    config_path.write_text(
        """pipeline:
  name: test-loop
  metrics: {}
  stages: []
  loop:
    max_iterations: 1
    on_fail: create_ticket
"""
    )

    captured: dict[str, object] = {}

    class FakePipeline:
        def __init__(self, config: object, workdir: Path, on_stage_start=None,
                     on_iteration_start=None, on_stage_error=None,
                     on_stage_done=None):
            self.config = config
            self.workdir = workdir

        def run(self, dry_run: bool = False) -> SimpleNamespace:
            return SimpleNamespace(
                iterations=[],
                final_passed=False,
                iteration_count=1,
                total_duration=0.0,
            )

    def fake_sync_todo_tickets(*, workdir: Path, dry_run: bool, direction: str) -> None:
        captured.update({"workdir": workdir, "dry_run": dry_run, "direction": direction})

    # Patch in cli_module where Pipeline and sync_todo_tickets are used
    # (cli.py does: from pyqual.pipeline import Pipeline)
    # (cli.py does: from pyqual.tickets import sync_todo_tickets)
    import pyqual.cli as cli_mod
    monkeypatch.setattr(cli_mod, "Pipeline", FakePipeline)
    monkeypatch.setattr(cli_mod, "sync_todo_tickets", fake_sync_todo_tickets)

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.app,
        [
            "run",
            "--config",
            str(config_path),
            "--workdir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert captured == {"workdir": tmp_path, "dry_run": False, "direction": "from"}


def test_run_report_includes_todo_and_fix_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "pyqual.yaml"
    config_path.write_text(
        """pipeline:
  name: test-loop
  metrics: {}
  stages: []
  loop:
    max_iterations: 1
    on_fail: report
"""
    )

    (tmp_path / "TODO.md").write_text(
        """# TODO

**Generated by:** prefact v0.1.30
**Generated on:** 2026-03-30T20:12:39.741132
**Total issues:** 4 active, 1 completed
"""
    )

    class FakePipeline:
        def __init__(self, config: object, workdir: Path, on_stage_start=None,
                     on_iteration_start=None, on_stage_error=None,
                     on_stage_done=None):
            self.config = config
            self.workdir = workdir

        def run(self, dry_run: bool = False) -> SimpleNamespace:
            prefact_stage = SimpleNamespace(
                name="prefact",
                returncode=0,
                stdout="Total issues: 4 active",
                stderr="",
                duration=1.0,
                skipped=False,
                passed=True,
            )
            fix_stage = SimpleNamespace(
                name="fix",
                returncode=0,
                stdout="3 files changed, 42 insertions(+)",
                stderr="",
                duration=2.0,
                skipped=False,
                passed=True,
            )
            iteration = SimpleNamespace(
                iteration=1,
                stages=[prefact_stage, fix_stage],
                gates=[],
                all_gates_passed=True,
                duration=3.0,
            )
            return SimpleNamespace(
                iterations=[iteration],
                final_passed=True,
                iteration_count=1,
                total_duration=3.0,
            )

    monkeypatch.setattr(cli_module, "Pipeline", FakePipeline)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--workdir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "summary:" in result.output
    assert "todo_active: 4" in result.output
    assert "todo_completed: 1" in result.output
    assert "todo_total: 5" in result.output
    assert "fix_files_changed: 3" in result.output
    assert "fix_result: changed" in result.output
