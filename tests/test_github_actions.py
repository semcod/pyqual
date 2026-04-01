"""Tests for GitHub Actions integration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyqual.github_actions import GitHubActionsReporter, GitHubTask


class TestGitHubTask:
    """Test GitHubTask dataclass."""

    def test_to_todo_item(self):
        """Test converting task to TODO.md format."""
        task = GitHubTask(
            number=42,
            title="Fix magic numbers",
            body="Issue body",
            state="open",
            html_url="https://github.com/owner/repo/issues/42",
            labels=["bug", "pyqual-fix"],
            assignees=["user1"],
            source="issue"
        )
        todo = task.to_todo_item()
        assert "#42: Fix magic numbers" in todo
        assert "[bug, pyqual-fix]" in todo
        assert "(issue)" in todo

    def test_to_todo_item_no_labels(self):
        """Test converting task without labels."""
        task = GitHubTask(
            number=1,
            title="Test",
            body="",
            state="open",
            html_url="url",
            labels=[],
            assignees=[],
            source="pull_request"
        )
        todo = task.to_todo_item()
        assert "#1: Test" in todo
        assert "[]" not in todo  # No empty labels


class TestGitHubActionsReporter:
    """Test GitHubActionsReporter."""

    def test_init_without_env(self):
        """Test initialization without environment variables."""
        reporter = GitHubActionsReporter()
        assert reporter.token is None
        assert reporter.repo is None

    def test_init_with_env(self, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        reporter = GitHubActionsReporter()
        assert reporter.token == "test-token"
        assert reporter.repo == "owner/repo"

    def test_is_running_in_github_actions(self, monkeypatch):
        """Test detection of GitHub Actions environment."""
        reporter = GitHubActionsReporter()
        
        # Not in GitHub Actions
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        assert not reporter.is_running_in_github_actions()
        
        # In GitHub Actions
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert reporter.is_running_in_github_actions()

    @patch("subprocess.run")
    def test_create_issue_success(self, mock_run, monkeypatch):
        """Test creating issue successfully."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"number": 123, "title": "Test Issue"}),
            stderr=""
        )
        
        reporter = GitHubActionsReporter()
        issue_num = reporter.create_issue("Test Title", "Test Body", ["bug"])
        
        assert issue_num == 123
        mock_run.assert_called_once()
        
        # Verify command contains correct arguments
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "repos/owner/repo/issues" in call_args

    @patch("subprocess.run")
    def test_create_issue_failure(self, mock_run, monkeypatch):
        """Test creating issue when API fails."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="API Error"
        )
        
        reporter = GitHubActionsReporter()
        issue_num = reporter.create_issue("Test", "Body")
        
        assert issue_num is None

    def test_create_issue_no_token(self):
        """Test creating issue without token."""
        reporter = GitHubActionsReporter(token=None, repo=None)
        issue_num = reporter.create_issue("Test", "Body")
        assert issue_num is None

    @patch("subprocess.run")
    def test_ensure_issue_exists_creates_new(self, mock_run, monkeypatch):
        """Test ensure_issue_exists when no matching issue exists."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        # First call: search returns empty
        # Second call: create returns new issue
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="[]", stderr=""),  # Search
            MagicMock(returncode=0, stdout=json.dumps({"number": 456}), stderr="")  # Create
        ]
        
        reporter = GitHubActionsReporter()
        issue_num = reporter.ensure_issue_exists("New Issue", "Body")
        
        assert issue_num == 456
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_ensure_issue_exists_finds_existing(self, mock_run, monkeypatch):
        """Test ensure_issue_exists when matching issue exists."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        existing_issues = [
            {"number": 789, "title": "[CI Fail] Stage 'test' failed in PR #42"}
        ]
        
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if "search" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(existing_issues),
                    stderr=""
                )
            else:
                return MagicMock(returncode=0, stdout="{}", stderr="")
        
        mock_run.side_effect = side_effect
        
        reporter = GitHubActionsReporter()
        # Title should be found in existing issues
        issue_num = reporter.ensure_issue_exists(
            "[CI Fail] Stage 'test' failed",
            "Body"
        )
        
        assert issue_num == 789
        assert mock_run.call_count == 1  # Only search, no create

    @patch("subprocess.run")
    def test_fetch_issues(self, mock_run, monkeypatch):
        """Test fetching issues from GitHub."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        mock_issues = [
            {
                "number": 1,
                "title": "Issue 1",
                "body": "Body",
                "state": "open",
                "url": "url",
                "labels": [{"name": "bug"}],
                "assignees": [{"login": "user"}]
            }
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_issues),
            stderr=""
        )
        
        reporter = GitHubActionsReporter()
        issues = reporter.fetch_issues(state="open", labels="pyqual-fix")
        
        assert len(issues) == 1
        assert issues[0].number == 1
        assert issues[0].title == "Issue 1"

    @patch("subprocess.run")
    def test_post_pr_comment(self, mock_run, monkeypatch):
        """Test posting comment on PR."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        reporter = GitHubActionsReporter()
        success = reporter.post_pr_comment("Test comment", pr_number=42)
        
        assert success is True
        mock_run.assert_called_once()
        
        call_args = mock_run.call_args[0][0]
        assert "pr" in call_args
        assert "comment" in call_args
        assert "42" in call_args

    @patch("subprocess.run")
    def test_post_issue_comment(self, mock_run, monkeypatch):
        """Test posting comment on issue."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        reporter = GitHubActionsReporter()
        success = reporter.post_issue_comment("Test comment", issue_number=42)
        
        assert success is True
        mock_run.assert_called_once()
        
        call_args = mock_run.call_args[0][0]
        assert "issue" in call_args
        assert "comment" in call_args

    def test_generate_failure_report(self):
        """Test generating failure report."""
        reporter = GitHubActionsReporter(
            token="test",
            repo="owner/repo"
        )
        reporter.sha = "abc123"
        reporter.ref = "main"
        reporter.event_name = "pull_request"
        
        report = reporter.generate_failure_report(
            stage_name="test",
            error="Tests failed",
            logs="Error log",
            suggestions=["Fix test 1", "Fix test 2"]
        )
        
        assert "Pipeline Failure" in report
        assert "test" in report
        assert "Tests failed" in report
        assert "Error log" in report
        assert "Fix test 1" in report
