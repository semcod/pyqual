"""Tests for the deps plugin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyqual.plugins.deps import (
    DepsCollector,
    check_requirements,
    deps_health_check,
    get_dependency_tree,
    get_outdated_packages,
)


class TestDepsCollector:
    """Test DepsCollector metric collection."""

    def test_collector_name(self):
        assert DepsCollector.name == "deps"

    def test_collector_metadata(self):
        collector = DepsCollector()
        assert collector.metadata.name == "deps"
        assert "dependencies" in collector.metadata.tags

    def test_collect_empty_workdir(self, tmp_path: Path):
        """Test collecting from empty workdir."""
        collector = DepsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["deps_outdated_count"] == 0.0
        assert metrics["deps_direct_count"] == 0.0

    def test_collect_outdated_results(self, tmp_path: Path):
        """Test parsing outdated packages JSON."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        outdated_data = [
            {"name": "requests", "version": "2.28.0", "latest_version": "2.31.0"},
            {"name": "numpy", "version": "1.23.0", "latest_version": "2.0.0"},  # Major update
            {"name": "click", "version": "8.0.0", "latest_version": "8.1.0"},
        ]
        
        (pyqual_dir / "outdated.json").write_text(json.dumps(outdated_data))
        
        collector = DepsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["deps_outdated_count"] == 3.0
        assert metrics["deps_outdated_major"] == 1.0  # Only numpy is major

    def test_collect_deptree_results(self, tmp_path: Path):
        """Test parsing dependency tree JSON."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        deptree_data = [
            {"package_name": "requests", "installed_version": "2.31.0", "required_by": []},
            {"package_name": "urllib3", "installed_version": "2.0.0", "required_by": ["requests"]},
            {"package_name": "certifi", "installed_version": "2023.0", "required_by": ["requests"]},
        ]
        
        (pyqual_dir / "deptree.json").write_text(json.dumps(deptree_data))
        
        collector = DepsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["deps_direct_count"] == 1.0  # requests
        assert metrics["deps_transitive_count"] == 2.0  # urllib3, certifi
        assert metrics["deps_total_count"] == 3.0

    def test_collect_requirements(self, tmp_path: Path):
        """Test parsing requirements.txt."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("""requests==2.31.0
flask>=2.0.0
numpy
# comment
pytest~=7.0.0
""")
        
        collector = DepsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["deps_requirements_entries"] == 4.0
        assert metrics["deps_pins_incomplete"] == 1.0  # numpy is unpinned

    def test_collect_licenses(self, tmp_path: Path):
        """Test parsing license data."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        licenses_data = [
            {"name": "requests", "license": "Apache-2.0"},
            {"name": "numpy", "license": "BSD"},
            {"name": "unknown-pkg", "license": "UNKNOWN"},
            {"name": "proprietary-lib", "license": "GPL-3.0"},
        ]
        
        (pyqual_dir / "licenses.json").write_text(json.dumps(licenses_data))
        
        collector = DepsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["deps_licenses_unknown"] == 1.0
        assert metrics["deps_licenses_restrictive"] == 1.0  # GPL

    def test_get_config_example(self):
        """Test config example."""
        collector = DepsCollector()
        example = collector.get_config_example()
        
        assert "deps_outdated_max" in example
        assert "pip list" in example.lower()


class TestGetOutdatedPackages:
    """Test outdated packages functionality."""

    def test_pip_not_available(self):
        """Test graceful handling."""
        # This test just ensures no crash
        result = get_outdated_packages()
        
        assert "success" in result


class TestGetDependencyTree:
    """Test dependency tree functionality."""

    def test_pipdeptree_not_available(self):
        """Test graceful handling when pipdeptree is not installed."""
        result = get_dependency_tree()
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "pipdeptree" in result.get("error", "").lower()


class TestCheckRequirements:
    """Test requirements file checking."""

    def test_requirements_not_found(self, tmp_path: Path):
        """Test handling missing file."""
        result = check_requirements(cwd=tmp_path)
        
        assert result["success"] is False
        assert result["exists"] is False

    def test_requirements_parsing(self, tmp_path: Path):
        """Test parsing valid requirements."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("""requests==2.31.0
flask>=2.0.0
numpy
pytest~=7.0.0
# comment
""")
        
        result = check_requirements(cwd=tmp_path)
        
        assert result["success"] is True
        assert result["exists"] is True
        assert result["entries"] == 4
        assert result["unpinned_packages"] == 1  # numpy
        assert result["is_fully_pinned"] is False

    def test_fully_pinned_requirements(self, tmp_path: Path):
        """Test with all packages pinned."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("""requests==2.31.0
flask==2.3.0
numpy==1.24.0
""")
        
        result = check_requirements(cwd=tmp_path)
        
        assert result["is_fully_pinned"] is True
        assert result["unpinned_packages"] == 0


class TestDepsHealthCheck:
    """Test comprehensive health check."""

    def test_health_check_structure(self, tmp_path: Path):
        """Test result structure."""
        result = deps_health_check(cwd=tmp_path)
        
        assert "success" in result
        assert "metrics" in result
        assert "recommendations" in result
        assert "is_healthy" in result
