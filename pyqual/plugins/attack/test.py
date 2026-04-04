"""Tests for attack plugin."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyqual.plugins.attack import (
    AttackCollector,
    MERGE_STRATEGIES,
    attack_check,
    attack_merge,
    auto_merge_pr,
)
from pyqual.plugins import PluginRegistry


class TestAttackCollector:
    """Test AttackCollector class."""

    def test_collector_registration(self):
        """Test that collector is registered."""
        collector_class = PluginRegistry.get("attack")
        assert collector_class is not None
        assert collector_class.name == "attack"

    def test_collect_empty_directory(self, tmp_path: Path):
        """Test collecting metrics with no artifacts."""
        collector = AttackCollector()
        result = collector.collect(tmp_path)
        assert result == {}

    def test_collect_check_metrics(self, tmp_path: Path):
        """Test collecting check metrics from artifact."""
        collector = AttackCollector()

        # Create mock artifact
        artifact = tmp_path / ".pyqual" / "attack_check.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({
            "conflicts_detected": 2,
            "branches_behind": 5,
            "can_fast_forward": False,
            "success": True,
        }))

        result = collector.collect(tmp_path)

        assert result["attack_conflicts_detected"] == 2.0
        assert result["attack_branches_behind"] == 5.0
        assert result["attack_can_fast_forward"] == 0.0
        assert result["attack_check_success"] == 1.0

    def test_collect_merge_metrics(self, tmp_path: Path):
        """Test collecting merge metrics from artifact."""
        collector = AttackCollector()

        # Create mock artifact
        artifact = tmp_path / ".pyqual" / "attack_merge.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps({
            "success": True,
            "conflicts_resolved": 3,
            "strategy": "theirs",
            "files_changed": 10,
        }))

        result = collector.collect(tmp_path)

        assert result["attack_merge_success"] == 1.0
        assert result["attack_merge_conflicts_resolved"] == 3.0
        assert result["attack_merge_strategy_used"] == 2.0  # theirs = 2
        assert result["attack_merge_files_changed"] == 10.0


class TestAttackCheck:
    """Test attack_check function."""

    def test_not_git_repo(self, tmp_path: Path):
        """Test check in non-git directory."""
        result = attack_check(tmp_path)
        assert result["success"] is False
        assert "Not a git repository" in result["error"]

    @patch("pyqual.plugins.attack.main.run_git_command")
    def test_successful_check(self, mock_run, tmp_path: Path):
        """Test successful attack check."""
        # Mock git responses
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=".git"),  # rev-parse --git-dir
            MagicMock(returncode=0, stdout="feature-branch"),  # current branch
            MagicMock(returncode=0, stdout="3"),  # behind count
            MagicMock(returncode=0, stdout=""),  # merge-tree (no conflicts)
        ]

        result = attack_check(tmp_path)

        assert result["success"] is True
        assert result["branches_behind"] == 3
        assert result["can_fast_forward"] is True


class TestAttackMerge:
    """Test attack_merge function."""

    def test_not_git_repo(self, tmp_path: Path):
        """Test merge in non-git directory."""
        result = attack_merge(strategy="theirs", cwd=tmp_path)
        assert result["success"] is False
        assert "Not a git repository" in result["error"]

    @patch("pyqual.plugins.attack.main.run_git_command")
    def test_dry_run_merge(self, mock_run, tmp_path: Path):
        """Test dry-run merge."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=".git"),  # rev-parse
            MagicMock(returncode=0, stdout="feature"),  # current branch
            MagicMock(returncode=0, stdout="fetch done"),  # fetch
            MagicMock(returncode=0, stdout="changed: file.txt\nchanged: other.py"),  # merge-tree
        ]

        result = attack_merge(strategy="theirs", cwd=tmp_path, dry_run=True)

        assert result["success"] is True
        assert result["files_changed"] == 2


class TestAutoMergePR:
    """Test auto_merge_pr function."""

    @patch("subprocess.run")
    def test_pr_merge_with_gh_cli(self, mock_run, tmp_path: Path):
        """Test PR merge using GitHub CLI."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Merged #42")

        result = auto_merge_pr(pr_number=42, cwd=tmp_path)

        assert result["success"] is True
        assert result["method"] == "squash"

    @patch("subprocess.run")
    def test_pr_merge_failure(self, mock_run, tmp_path: Path):
        """Test PR merge failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Pull request not found"
        )

        result = auto_merge_pr(pr_number=999, cwd=tmp_path)

        assert result["success"] is False
        assert "not found" in result["error"].lower() or result["error"]

    def test_no_pr_or_branch(self, tmp_path: Path):
        """Test merge without specifying PR or branch."""
        result = auto_merge_pr(cwd=tmp_path)
        assert result["success"] is False
        assert "No PR number or branch" in result["error"]


class TestMergeStrategies:
    """Test merge strategy constants."""

    def test_strategies_defined(self):
        """Test that all strategies are defined."""
        assert "ours" in MERGE_STRATEGIES
        assert "theirs" in MERGE_STRATEGIES
        assert "union" in MERGE_STRATEGIES

    def test_collector_strategy_conversion(self):
        """Test strategy to int conversion."""
        collector = AttackCollector()
        assert collector._strategy_to_int("none") == 0
        assert collector._strategy_to_int("ours") == 1
        assert collector._strategy_to_int("theirs") == 2
        assert collector._strategy_to_int("union") == 3
        assert collector._strategy_to_int("UNKNOWN") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
