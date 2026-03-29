from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import pyqual.cli as cli_module
from pyqual.cli import app
from pyqual import tickets as tickets_module


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

    tickets_module.sync_todo_tickets(tmp_path, dry_run=True, direction="from")

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

    tickets_module.sync_github_tickets(tmp_path, dry_run=False, direction="both")

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

    tickets_module.sync_all_tickets(tmp_path, dry_run=False, direction="to")

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
        def __init__(self, config: object, workdir: Path):
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

    monkeypatch.setattr(cli_module, "Pipeline", FakePipeline)
    monkeypatch.setattr(cli_module, "sync_todo_tickets", fake_sync_todo_tickets)

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

    assert result.exit_code == 1
    assert captured == {"workdir": tmp_path, "dry_run": False, "direction": "from"}
