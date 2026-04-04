"""Tests for the security plugin."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pyqual.plugins.security import (
    SecurityCollector,
    run_bandit_check,
    run_pip_audit,
    run_detect_secrets,
    security_summary,
)
from pyqual.plugins.security.main import (
    run_bandit_check,
    run_pip_audit,
    run_detect_secrets,
    security_summary,
)


class TestSecurityCollector:
    """Test SecurityCollector metric collection."""

    def test_collector_name(self):
        assert SecurityCollector.name == "security"

    def test_collector_metadata(self):
        collector = SecurityCollector()
        assert collector.metadata.name == "security"
        assert "bandit" in collector.metadata.description.lower()
        assert "security" in collector.metadata.tags

    def test_collect_empty_workdir(self, tmp_path: Path):
        """Test collecting from empty workdir returns zeros."""
        collector = SecurityCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["security_bandit_high"] == 0.0
        assert metrics["security_vuln_critical"] == 0.0
        assert metrics["security_secrets_found"] == 0.0

    def test_collect_bandit_results(self, tmp_path: Path):
        """Test parsing bandit JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        bandit_data = {
            "results": [
                {"issue_severity": "HIGH", "issue_confidence": "HIGH"},
                {"issue_severity": "HIGH", "issue_confidence": "MEDIUM"},
                {"issue_severity": "MEDIUM", "issue_confidence": "HIGH"},
                {"issue_severity": "LOW", "issue_confidence": "LOW"},
            ],
            "metrics": {}
        }
        
        (pyqual_dir / "bandit.json").write_text(json.dumps(bandit_data))
        
        collector = SecurityCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["security_bandit_high"] == 2.0
        assert metrics["security_bandit_medium"] == 1.0
        assert metrics["security_bandit_low"] == 1.0
        assert metrics["security_bandit_confidence_high"] == 2.0

    def test_collect_audit_results(self, tmp_path: Path):
        """Test parsing pip-audit JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        audit_data = [
            {"name": "package1", "severity": "CRITICAL"},
            {"name": "package2", "severity": "HIGH"},
            {"name": "package3", "severity": "MODERATE"},
        ]
        
        (pyqual_dir / "audit.json").write_text(json.dumps(audit_data))
        
        collector = SecurityCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["security_vuln_critical"] == 1.0
        assert metrics["security_vuln_high"] == 1.0
        assert metrics["security_vuln_moderate"] == 1.0

    def test_collect_secrets_results(self, tmp_path: Path):
        """Test parsing detect-secrets JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        secrets_data = {
            "results": {
                "file1.py": [{}, {}, {}],
                "file2.py": [{}],
            },
            "version": "1.0"
        }
        
        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))
        
        collector = SecurityCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["security_secrets_found"] == 4.0

    def test_collect_safety_results(self, tmp_path: Path):
        """Test parsing safety JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        safety_data = [
            {"package_name": "pkg1", "vulnerability_id": "CVE-1"},
            {"package_name": "pkg2", "vulnerability_id": "CVE-2"},
        ]
        
        (pyqual_dir / "safety.json").write_text(json.dumps(safety_data))
        
        collector = SecurityCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["security_safety_issues"] == 2.0

    def test_get_config_example(self):
        """Test config example contains expected keys."""
        collector = SecurityCollector()
        example = collector.get_config_example()
        
        assert "security_bandit_high_max" in example
        assert "bandit" in example.lower()
        assert "pip-audit" in example.lower()


class TestBanditCheck:
    """Test bandit check functionality."""

    def test_bandit_not_found(self, tmp_path: Path):
        """Test graceful handling when bandit is not installed."""
        result = run_bandit_check(paths=[str(tmp_path)])
        
        # Should fail gracefully, not crash
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "bandit" in result.get("error", "").lower()


class TestPipAudit:
    """Test pip-audit functionality."""

    def test_pip_audit_not_found(self):
        """Test graceful handling when pip-audit is not installed."""
        result = run_pip_audit()
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "pip-audit" in result.get("error", "").lower()


class TestDetectSecrets:
    """Test detect-secrets functionality."""

    def test_detect_secrets_not_found(self):
        """Test graceful handling when detect-secrets is not installed."""
        result = run_detect_secrets()
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "detect-secrets" in result.get("error", "").lower()


class TestSecuritySummary:
    """Test security summary aggregation."""

    def test_security_summary_empty(self, tmp_path: Path):
        """Test summary with no security issues."""
        summary = security_summary(tmp_path)
        
        assert summary["success"] is True
        assert summary["is_secure"] is True
        assert summary["total_issues"] == 0
        assert "bandit" in summary["tools_checked"]

    def test_security_summary_with_issues(self, tmp_path: Path):
        """Test summary with security issues detected."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        # Create bandit results with HIGH issues
        bandit_data = {
            "results": [{"issue_severity": "HIGH"}],
            "metrics": {}
        }
        (pyqual_dir / "bandit.json").write_text(json.dumps(bandit_data))
        
        summary = security_summary(tmp_path)
        
        assert summary["success"] is True
        assert summary["is_secure"] is False
        assert summary["total_issues"] > 0
