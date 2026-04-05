"""Tests for cli_run_helpers.py — stage summary extraction and report building."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyqual.cli_run_helpers import (
    build_run_summary,
    count_todo_items,
    enrich_from_artifacts,
    extract_bandit_stage_summary,
    extract_code2llm_stage_summary,
    extract_fix_stage_summary,
    extract_lint_stage_summary,
    extract_mypy_stage_summary,
    extract_prefact_stage_summary,
    extract_pytest_stage_summary,
    extract_stage_summary,
    extract_validation_stage_summary,
    format_run_summary,
    get_last_error_line,
    infer_fix_result,
)


class TestExtractPytestStageSummary:
    """Tests for pytest output extraction."""

    def test_extracts_passed(self) -> None:
        text = "5 passed in 0.12s"
        result = extract_pytest_stage_summary("test", text)
        assert result == {"passed": 5}

    def test_extracts_failed(self) -> None:
        text = "3 failed, 1 passed"
        result = extract_pytest_stage_summary("test", text)
        assert result == {"passed": 1, "failed": 3}

    def test_extracts_errors(self) -> None:
        text = "2 error, 1 passed"
        result = extract_pytest_stage_summary("test", text)
        assert result == {"passed": 1, "errors": 2}

    def test_skips_non_test_stages(self) -> None:
        text = "5 passed"
        result = extract_pytest_stage_summary("lint", text)
        assert result == {}


class TestExtractLintStageSummary:
    """Tests for lint output extraction."""

    def test_extracts_errors(self) -> None:
        text = "Found 42 errors"
        result = extract_lint_stage_summary(text)
        assert result == {"lint_errors": 42}

    def test_extracts_all_passed(self) -> None:
        text = "All checks passed"
        result = extract_lint_stage_summary(text)
        assert result == {"lint_errors": 0}


class TestExtractPrefactStageSummary:
    """Tests for prefact output extraction."""

    def test_extracts_total_issues(self) -> None:
        text = "**Total issues:** 15 active"
        result = extract_prefact_stage_summary("prefact", text)
        assert result == {"tickets": 15}

    def test_counts_unchecked_items(self) -> None:
        text = "- [ ] item 1\n- [ ] item 2\n- [x] done"
        result = extract_prefact_stage_summary("prefact", text)
        assert result == {"tickets": 2}


class TestExtractFixStageSummary:
    """Tests for fix stage output extraction."""

    def test_extracts_model(self) -> None:
        text = "Selected: gpt-4 → claude-3-opus-20240229 (via openrouter)"
        result = extract_fix_stage_summary("fix", text)
        assert result.get("model") == "claude-3-opus-20240229"

    def test_extracts_issues_loaded(self) -> None:
        text = "Loaded 5 errors from TODO.md"
        result = extract_fix_stage_summary("fix", text)
        assert result.get("issues_loaded") == 5

    def test_extracts_files_changed(self) -> None:
        text = "3 files changed, 12 insertions(+)"
        result = extract_fix_stage_summary("fix", text)
        assert result.get("files_changed") == 3

    def test_extracts_from_applied_changes(self) -> None:
        text = "Applied 7 changes"
        result = extract_fix_stage_summary("fix", text)
        assert result.get("files_changed") == 7

    def test_extracts_repair_stage(self) -> None:
        text = "Applied 2 changes"
        result = extract_fix_stage_summary("repair", text)
        assert result.get("files_changed") == 2


class TestExtractMypyStageSummary:
    """Tests for mypy output extraction."""

    def test_extracts_errors_and_files(self) -> None:
        text = "Found 5 errors in 3 files"
        result = extract_mypy_stage_summary("typecheck", text)
        assert result == {"mypy_errors": 5, "mypy_files": 3}


class TestExtractBanditStageSummary:
    """Tests for bandit output extraction."""

    def test_extracts_severity_counts(self) -> None:
        text = "High: 2 Medium: 5 Low: 10"
        result = extract_bandit_stage_summary(text)
        assert result == {"bandit_high": 2, "bandit_medium": 5, "bandit_low": 10}


class TestExtractValidationStageSummary:
    """Tests for validation (vallm) output extraction."""

    def test_extracts_cc_and_critical(self) -> None:
        text = "CC̄=12.5 critical:3"
        result = extract_validation_stage_summary("validate", text)
        assert result.get("cc") == 12.5
        assert result.get("critical") == 3

    def test_lowercase_cc(self) -> None:
        text = "cc: 8.2"
        result = extract_validation_stage_summary("validate", text)
        assert result.get("cc") == 8.2


class TestInferFixResult:
    """Tests for fix result inference."""

    def test_changed_when_files_changed(self) -> None:
        stage = {"files_changed": 3}
        assert infer_fix_result(stage) == "changed"

    def test_no_changes_when_zero_files(self) -> None:
        stage = {"files_changed": 0}
        assert infer_fix_result(stage) == "no_changes"

    def test_changed_from_status(self) -> None:
        stage = {"fix_status": "Applied 5 changes"}
        assert infer_fix_result(stage) == "changed"

    def test_no_changes_from_status(self) -> None:
        stage = {"fix_status": "No changes made"}
        assert infer_fix_result(stage) == "no_changes"


class TestGetLastErrorLine:
    """Tests for error line extraction."""

    def test_filters_noise(self) -> None:
        text = "Using .gitignore\nExcluded venv/\nError: something failed"
        result = get_last_error_line(text)
        assert "Error" in result
        assert "Using" not in result

    def test_returns_empty_for_clean_output(self) -> None:
        text = "All good\nSuccess!"
        result = get_last_error_line(text)
        assert result == "Success!"


class TestCountTodoItems:
    """Tests for TODO counting."""

    def test_counts_unchecked_items(self, tmp_path: Path) -> None:
        todo_file = tmp_path / "TODO.md"
        todo_file.write_text("- [ ] item 1\n- [ ] item 2\n- [x] done\n")
        assert count_todo_items(todo_file) == 2

    def test_returns_zero_for_no_todo(self, tmp_path: Path) -> None:
        todo_file = tmp_path / "TODO.md"
        assert count_todo_items(todo_file) == 0


class TestBuildRunSummary:
    """Tests for run summary building."""

    def test_extracts_prefact_tickets(self) -> None:
        report = {
            "iterations": [
                {
                    "stages": [
                        {"name": "prefact", "status": "passed", "tickets": 5, "tickets_completed": 3}
                    ]
                }
            ]
        }
        summary = build_run_summary(report)
        assert summary["todo_active"] == 5
        assert summary["todo_completed"] == 3
        assert summary["todo_total"] == 8

    def test_extracts_fix_results(self) -> None:
        report = {
            "iterations": [
                {
                    "stages": [
                        {"name": "fix", "status": "passed", "files_changed": 2, "failed": 0}
                    ]
                }
            ]
        }
        summary = build_run_summary(report)
        assert summary["fix_files_changed"] == 2
        assert summary["fix_result"] == "changed"

    def test_extracts_repair_fix_results(self) -> None:
        report = {
            "iterations": [
                {
                    "stages": [
                        {"name": "repair", "status": "passed", "files_changed": 4, "failed": 0}
                    ]
                }
            ]
        }
        summary = build_run_summary(report)
        assert summary["fix_files_changed"] == 4
        assert summary["fix_result"] == "changed"

    def test_extracts_delivery_failures(self) -> None:
        report = {
            "iterations": [
                {
                    "stages": [
                        {"name": "publish", "status": "failed", "rc": 2, "stderr": "make: *** [Makefile:129: publish] Error 1"},
                        {"name": "push", "status": "passed"},
                    ]
                }
            ]
        }
        summary = build_run_summary(report)
        assert summary["delivery_failures"] == [
            "publish failed (rc=2): make: *** [Makefile:129: publish] Error 1"
        ]

    def test_extracts_deploy_failures(self) -> None:
        report = {
            "iterations": [
                {
                    "stages": [
                        {"name": "deploy", "status": "failed", "rc": 1, "stderr": "deployment failed"},
                    ]
                }
            ]
        }
        summary = build_run_summary(report)
        assert summary["delivery_failures"] == ["deploy failed (rc=1): deployment failed"]


class TestFormatRunSummary:
    """Tests for summary formatting."""

    def test_includes_todo_info(self) -> None:
        summary = {"todo_active": 5, "todo_completed": 3, "todo_total": 8}
        text = format_run_summary(summary)
        assert "Tickets" in text

    def test_includes_fix_info(self) -> None:
        summary = {"fix_result": "changed", "fix_files_changed": 2}
        text = format_run_summary(summary)
        assert "Fix" in text

    def test_includes_delivery_failures(self) -> None:
        summary = {"delivery_failures": ["publish failed (rc=2): make: *** Error 1", "deploy failed (rc=1): deployment failed"]}
        text = format_run_summary(summary)
        assert "Delivery" in text
        assert "publish failed" in text
        assert "deploy failed" in text

    def test_returns_empty_for_empty_summary(self) -> None:
        assert format_run_summary({}) == ""
