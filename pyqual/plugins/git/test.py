"""Tests for the git plugin.

Run with: pytest pyqual/plugins/git/test.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Import plugin under test
from pyqual.plugins.git.main import (
    GitCollector,
    SECRET_PATTERNS,
    _is_likely_false_positive,
    _get_provider_for_pattern,
    _get_severity_for_pattern,
    git_add,
    git_commit,
    git_push,
    git_status,
    preflight_push_check,
    scan_for_secrets,
)


class TestGitCollector:
    """Tests for the GitCollector class."""

    def test_collector_registration(self):
        """Test that GitCollector is properly registered."""
        from pyqual.plugins import PluginRegistry
        
        collector_class = PluginRegistry.get("git")
        assert collector_class is not None
        assert collector_class.name == "git"

    def test_metadata(self):
        """Test collector metadata."""
        collector = GitCollector()
        
        assert collector.metadata.name == "git"
        assert "secret" in collector.metadata.tags
        assert "security" in collector.metadata.tags
        assert collector.metadata.version == "1.1.0"

    def test_config_example(self):
        """Test that config example is provided."""
        collector = GitCollector()
        config = collector.get_config_example()
        
        assert "git scan" in config
        assert "git_status" in config
        assert "metrics:" in config


class TestGitStatus:
    """Tests for git_status function."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            
            # Configure git user
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            
            yield repo_path

    def test_status_in_empty_repo(self, temp_git_repo):
        """Test git status in empty repo."""
        result = git_status(cwd=temp_git_repo)
        
        assert result["success"] is True
        assert result["is_clean"] is True
        assert result["staged_files"] == []
        assert result["unstaged_files"] == []
        assert result["untracked_files"] == []

    def test_status_with_untracked_file(self, temp_git_repo):
        """Test git status with untracked file."""
        # Create an untracked file
        (temp_git_repo / "untracked.txt").write_text("test content")
        
        result = git_status(cwd=temp_git_repo)
        
        assert result["success"] is True
        assert result["is_clean"] is False
        assert "untracked.txt" in result["untracked_files"]

    def test_status_not_a_git_repo(self):
        """Test git status in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = git_status(cwd=Path(tmpdir))
            
            assert result["success"] is False
            assert "Not a git repository" in result["error"]


class TestGitCommit:
    """Tests for git_commit function."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository with initial commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_path, capture_output=True, check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path, capture_output=True, check=True,
            )
            
            # Create initial commit
            (repo_path / "initial.txt").write_text("initial")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path, capture_output=True, check=True,
            )
            
            yield repo_path

    def test_commit_with_changes(self, temp_git_repo):
        """Test committing changes."""
        # Create and stage a file
        (temp_git_repo / "test.txt").write_text("test content")
        
        result = git_commit(
            message="Test commit",
            cwd=temp_git_repo,
            add_all=True,
        )
        
        assert result["success"] is True
        assert result["commit_hash"] is not None
        assert len(result["commit_hash"]) == 40  # SHA-1 hash

    def test_commit_only_if_changed_no_changes(self, temp_git_repo):
        """Test commit with only_if_changed when no changes."""
        result = git_commit(
            message="No changes",
            cwd=temp_git_repo,
            only_if_changed=True,
        )
        
        assert result["skipped"] is True
        assert result["success"] is True


class TestSecretScanning:
    """Tests for secret scanning functionality."""

    @pytest.fixture
    def temp_repo_with_secrets(self):
        """Create a temp repo with files containing secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Create file with fake GitHub token
            (repo_path / "config.py").write_text(
                'GITHUB_TOKEN = "ghp_1234567890abcdef1234567890abcdef123456"\n'
            )
            
            # Create file with fake AWS key
            (repo_path / "aws_config.py").write_text(
                'AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
            )
            
            # Create file with placeholder (should not match)
            (repo_path / "safe.py").write_text(
                'API_KEY = "your_key_here"\n'
            )
            
            yield repo_path

    def test_scan_finds_github_token(self, temp_repo_with_secrets):
        """Test that GitHub token is detected."""
        result = scan_for_secrets(
            paths=["config.py"],
            cwd=temp_repo_with_secrets,
            use_trufflehog=False,
            use_gitleaks=False,
            use_patterns=True,
        )
        
        assert result["success"] is False  # Secrets found
        assert len(result["secrets_found"]) > 0
        
        # Check for GitHub token
        github_secrets = [
            s for s in result["secrets_found"]
            if "github" in s["type"].lower()
        ]
        assert len(github_secrets) > 0

    def test_scan_finds_aws_key(self, temp_repo_with_secrets):
        """Test that AWS key is detected."""
        result = scan_for_secrets(
            paths=["aws_config.py"],
            cwd=temp_repo_with_secrets,
            use_trufflehog=False,
            use_gitleaks=False,
            use_patterns=True,
        )
        
        assert result["success"] is False
        
        aws_secrets = [
            s for s in result["secrets_found"]
            if "aws" in s["type"].lower()
        ]
        assert len(aws_secrets) > 0

    def test_scan_skips_placeholders(self, temp_repo_with_secrets):
        """Test that placeholder values are skipped."""
        result = scan_for_secrets(
            paths=["safe.py"],
            cwd=temp_repo_with_secrets,
            use_trufflehog=False,
            use_gitleaks=False,
            use_patterns=True,
        )
        
        # Should pass (no secrets) because "your_key_here" is filtered
        assert result["success"] is True
        assert len(result["secrets_found"]) == 0

    def test_false_positive_detection(self):
        """Test false positive filtering."""
        # Hex color code should be filtered for aws_secret_key
        assert _is_likely_false_positive(
            "1234567890abcdef1234567890abcdef12345678",
            "aws_secret_key",
            "background-color: #1234567890abcdef1234567890abcdef12345678;"
        ) is True
        
        # Placeholder should be filtered
        assert _is_likely_false_positive(
            "your_key_here_12345",
            "api_key_generic",
            "API_KEY = your_key_here_12345"
        ) is True

    def test_provider_mapping(self):
        """Test provider name mapping."""
        assert _get_provider_for_pattern("github_token") == "GitHub"
        assert _get_provider_for_pattern("aws_access_key") == "AWS"
        assert _get_provider_for_pattern("stripe_key") == "Stripe"
        assert _get_provider_for_pattern("unknown_pattern") == "Unknown"

    def test_severity_mapping(self):
        """Test severity level mapping."""
        assert _get_severity_for_pattern("github_token") == "CRITICAL"
        assert _get_severity_for_pattern("aws_access_key") == "CRITICAL"
        assert _get_severity_for_pattern("api_key_generic") == "HIGH"
        assert _get_severity_for_pattern("postgres_url") == "MEDIUM"
        assert _get_severity_for_pattern("high_entropy") == "LOW"


class TestPreFlightCheck:
    """Tests for preflight_push_check function."""

    @pytest.fixture
    def temp_git_repo_with_commits(self):
        """Create a temp repo with commits ahead of remote."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Initialize and configure
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_path, capture_output=True, check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path, capture_output=True, check=True,
            )
            
            # Create initial commit
            (repo_path / "file.txt").write_text("content")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=repo_path, capture_output=True, check=True,
            )
            
            # Create additional commit
            (repo_path / "file.txt").write_text("modified")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Second commit"],
                cwd=repo_path, capture_output=True, check=True,
            )
            
            yield repo_path

    def test_preflight_with_secrets_blocks_push(self, temp_git_repo_with_commits):
        """Test that secrets block push in preflight."""
        # Create file with secret
        (temp_git_repo_with_commits / "secret.py").write_text(
            'TOKEN = "ghp_1234567890abcdef1234567890abcdef123456"\n'
        )
        
        result = preflight_push_check(
            cwd=temp_git_repo_with_commits,
            scan_secrets=True,
        )
        
        assert result["can_push"] is False
        assert any("CRITICAL" in b for b in result["blockers"])

    def test_preflight_clean_repo(self, temp_git_repo_with_commits):
        """Test preflight with clean repo."""
        result = preflight_push_check(
            cwd=temp_git_repo_with_commits,
            scan_secrets=True,
        )
        
        # Should have commits to push and no secrets
        assert result["can_push"] is True
        assert result["secrets_scan"]["success"] is True


class TestSecretPatterns:
    """Tests for SECRET_PATTERNS regex patterns."""

    def test_github_token_pattern(self):
        """Test GitHub token regex."""
        pattern = SECRET_PATTERNS["github_token"]
        
        # Should match
        assert pattern.search("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert pattern.search("gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert pattern.search("github_pat_xxxxxxxxxxxxxxxxxxxxxx")
        
        # Should not match
        assert not pattern.search("ghp_123")  # Too short
        assert not pattern.search("invalid_token")

    def test_aws_access_key_pattern(self):
        """Test AWS access key regex."""
        pattern = SECRET_PATTERNS["aws_access_key"]
        
        # Should match
        assert pattern.search("AKIAIOSFODNN7EXAMPLE")
        
        # Should not match
        assert not pattern.search("AKIA123")  # Too short
        assert not pattern.search("AKIAIOSFODNN7")  # Too short

    def test_private_key_pattern(self):
        """Test private key regex."""
        pattern = SECRET_PATTERNS["private_key"]
        
        # Should match
        assert pattern.search("-----BEGIN RSA PRIVATE KEY-----")
        assert pattern.search("-----BEGIN PRIVATE KEY-----")
        assert pattern.search("-----BEGIN OPENSSH PRIVATE KEY-----")
        
        # Should not match
        assert not pattern.search("-----BEGIN PUBLIC KEY-----")

    def test_jwt_token_pattern(self):
        """Test JWT token regex."""
        pattern = SECRET_PATTERNS["jwt_token"]
        
        # Should match valid JWT format
        assert pattern.search("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THg")
        
        # Should not match
        assert not pattern.search("not.a.jwt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
