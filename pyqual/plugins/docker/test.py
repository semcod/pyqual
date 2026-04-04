"""Tests for the Docker plugin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyqual.plugins.docker import (
    DockerCollector,
    docker_security_check,
    get_image_info,
    run_hadolint,
    run_trivy_scan,
)


class TestDockerCollector:
    """Test DockerCollector metric collection."""

    def test_collector_name(self):
        assert DockerCollector.name == "docker"

    def test_collector_metadata(self):
        collector = DockerCollector()
        assert collector.metadata.name == "docker"
        assert "docker" in collector.metadata.tags
        assert "security" in collector.metadata.tags

    def test_collect_empty_workdir(self, tmp_path: Path):
        """Test collecting from empty workdir returns zeros."""
        collector = DockerCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docker_vuln_critical"] == 0.0
        assert metrics["docker_hadolint_errors"] == 0.0
        assert metrics["docker_image_size_mb"] == 0.0

    def test_collect_trivy_results(self, tmp_path: Path):
        """Test parsing trivy JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        trivy_data = {
            "Results": [
                {
                    "Target": "myimage",
                    "Type": "image",
                    "Vulnerabilities": [
                        {"VulnerabilityID": "CVE-1", "Severity": "CRITICAL"},
                        {"VulnerabilityID": "CVE-2", "Severity": "HIGH"},
                        {"VulnerabilityID": "CVE-3", "Severity": "HIGH"},
                        {"VulnerabilityID": "CVE-4", "Severity": "MEDIUM"},
                    ]
                }
            ]
        }
        
        (pyqual_dir / "trivy.json").write_text(json.dumps(trivy_data))
        
        collector = DockerCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docker_vuln_critical"] == 1.0
        assert metrics["docker_vuln_high"] == 2.0
        assert metrics["docker_vuln_medium"] == 1.0

    def test_collect_hadolint_results(self, tmp_path: Path):
        """Test parsing hadolint JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        hadolint_data = [
            {"line": 1, "code": "DL3006", "level": "warning", "message": "Always tag"},
            {"line": 5, "code": "DL3018", "level": "error", "message": "Pin versions"},
        ]
        
        (pyqual_dir / "hadolint.json").write_text(json.dumps(hadolint_data))
        
        collector = DockerCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docker_hadolint_errors"] == 1.0
        assert metrics["docker_hadolint_warnings"] == 1.0

    def test_collect_grype_results(self, tmp_path: Path):
        """Test parsing grype JSON output."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        grype_data = {
            "matches": [
                {"vulnerability": {"id": "CVE-1", "severity": "Critical"}},
                {"vulnerability": {"id": "CVE-2", "severity": "High"}},
            ]
        }
        
        (pyqual_dir / "grype.json").write_text(json.dumps(grype_data))
        
        collector = DockerCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docker_grype_critical"] == 1.0
        assert metrics["docker_grype_high"] == 1.0

    def test_get_config_example(self):
        """Test config example contains expected keys."""
        collector = DockerCollector()
        example = collector.get_config_example()
        
        assert "docker_vuln_critical_max" in example
        assert "trivy" in example.lower() or "hadolint" in example.lower()


class TestHadolint:
    """Test hadolint integration."""

    def test_hadolint_not_found(self, tmp_path: Path):
        """Test graceful handling when hadolint is not installed."""
        result = run_hadolint(dockerfile="Dockerfile", cwd=tmp_path)
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "hadolint" in result.get("error", "").lower()


class TestTrivyScan:
    """Test trivy integration."""

    def test_trivy_not_found(self):
        """Test graceful handling when trivy is not installed."""
        result = run_trivy_scan("myimage:latest")
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "trivy" in result.get("error", "").lower()


class TestDockerSecurityCheck:
    """Test comprehensive security check."""

    def test_security_check_without_image(self, tmp_path: Path):
        """Test security check with just Dockerfile linting."""
        # Create a dummy Dockerfile
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        
        result = docker_security_check(dockerfile="Dockerfile", cwd=tmp_path)
        
        assert "lint" in result or "error" in result
        assert "image_scan" in result
        assert "is_secure" in result

    def test_security_check_structure(self):
        """Test result structure."""
        result = docker_security_check()
        
        assert "success" in result
        assert "is_secure" in result
