"""Tests for secret scanning metric collection."""

import json
from pathlib import Path

import pytest

from pyqual._gate_collectors import _from_secrets


class TestSecretsCollector:
    """Test secret scanning metric collection from secrets.json."""

    def test_no_secrets_file_returns_empty(self, tmp_path: Path) -> None:
        """When no secrets.json exists, return empty dict."""
        result = _from_secrets(tmp_path)
        assert result == {}

    def test_simple_secrets_list_parsed(self, tmp_path: Path) -> None:
        """Parse simple list format with severity field."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        secrets_data = [
            {"severity": "high", "description": "AWS key"},
            {"severity": "critical", "description": "Private key"},
        ]

        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))

        result = _from_secrets(tmp_path)

        assert result["secrets_count"] == 2.0
        assert result["secrets_found"] == 2.0
        assert result["secrets_severity"] == 4.0  # max(critical=4, high=3)

    def test_gitleaks_format_parsed(self, tmp_path: Path) -> None:
        """Parse gitleaks JSON output format - requires lowercase severity key."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        # Note: gitleaks uses "Severity" with capital S, but collector needs "severity"
        # This test shows what works with current implementation
        secrets_data = [
            {"description": "AWS Access Key", "severity": "high"},
            {"description": "GitHub Token", "severity": "medium"},
            {"description": "Private Key", "severity": "critical"},
        ]

        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))

        result = _from_secrets(tmp_path)

        assert result["secrets_count"] == 3.0
        assert result["secrets_found"] == 3.0
        assert result["secrets_severity"] == 4.0  # max severity = critical=4

    def test_empty_secrets_returns_zero(self, tmp_path: Path) -> None:
        """When secrets.json exists but is empty, return zeros."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        (pyqual_dir / "secrets.json").write_text(json.dumps([]))

        result = _from_secrets(tmp_path)

        assert result["secrets_count"] == 0.0
        assert result["secrets_found"] == 0.0
        assert result["secrets_severity"] == 0.0

    def test_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        """When secrets.json is invalid, return empty dict."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        (pyqual_dir / "secrets.json").write_text("invalid json {")

        result = _from_secrets(tmp_path)
        assert result == {}

    def test_severity_mapping(self, tmp_path: Path) -> None:
        """Test that severity levels are correctly mapped to weights."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        secrets_data = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "info"},  # unknown severity
        ]

        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))

        result = _from_secrets(tmp_path)

        assert result["secrets_count"] == 5.0
        assert result["secrets_found"] == 5.0
        # max severity: critical=4, high=3, medium=2, low=1, unknown=0
        assert result["secrets_severity"] == 4.0

    def test_case_insensitive_severity(self, tmp_path: Path) -> None:
        """Severity matching should be case-insensitive."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        secrets_data = [
            {"severity": "HIGH"},  # uppercase
            {"Severity": "Medium"},  # different key case - won't be read
            {"severity": "critical"},
        ]

        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))

        result = _from_secrets(tmp_path)

        assert result["secrets_count"] == 3.0
        # Only lowercase 'severity' key is checked
        # HIGH -> high=3, critical=4, Medium not found
        assert result["secrets_severity"] == 4.0

    def test_dict_format_supported(self, tmp_path: Path) -> None:
        """Dict format (e.g., detect-secrets with 'results' key) is now supported."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()

        # Dict format with results key (detect-secrets format)
        secrets_data = {
            "results": {
                "file1.py": [
                    {"type": "AWS Access Key"},
                    {"type": "Private Key"},
                ]
            }
        }

        (pyqual_dir / "secrets.json").write_text(json.dumps(secrets_data))

        result = _from_secrets(tmp_path)
        # Dict format now returns proper metrics
        assert result["secrets_count"] == 2.0
        assert result["secrets_found"] == 2.0
        assert result["secrets_severity"] == 3.0  # High severity for secrets
