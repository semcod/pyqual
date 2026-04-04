"""Tests for the docs plugin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyqual.plugins.docs import (
    DocsCollector,
    check_links,
    check_readme,
    docs_quality_summary,
    run_interrogate,
)


class TestDocsCollector:
    """Test DocsCollector metric collection."""

    def test_collector_name(self):
        assert DocsCollector.name == "docs"

    def test_collector_metadata(self):
        collector = DocsCollector()
        assert collector.metadata.name == "docs"
        assert "documentation" in collector.metadata.tags

    def test_collect_empty_workdir(self, tmp_path: Path):
        """Test collecting from empty workdir."""
        collector = DocsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docs_readme_sections"] == 0.0
        assert metrics["docs_changelog_exists"] == 0.0

    def test_collect_with_readme(self, tmp_path: Path):
        """Test collecting with README present."""
        # Create README
        readme = tmp_path / "README.md"
        readme.write_text("""# My Project

## Installation
```bash
pip install myproject
```

## Usage
Example usage here.

## License
MIT
""")
        
        collector = DocsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docs_readme_sections"] >= 3.0
        assert metrics["docs_readme_has_install"] == 1.0
        assert metrics["docs_readme_has_usage"] == 1.0
        assert metrics["docs_readme_has_license"] == 1.0
        assert metrics["docs_readme_code_blocks"] >= 1.0

    def test_collect_docstring_coverage(self, tmp_path: Path):
        """Test parsing docstring coverage JSON."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        coverage_data = {
            "coverage": 75.5,
            "missing": 10,
        }
        
        (pyqual_dir / "docstring_coverage.json").write_text(json.dumps(coverage_data))
        
        collector = DocsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docs_docstring_coverage"] == 75.5
        assert metrics["docs_missing_docstrings"] == 10.0

    def test_collect_link_results(self, tmp_path: Path):
        """Test parsing link check JSON."""
        pyqual_dir = tmp_path / ".pyqual"
        pyqual_dir.mkdir()
        
        links_data = [
            {"url": "https://example.com", "status": "ok"},
            {"url": "https://broken.com", "status": "error"},
        ]
        
        (pyqual_dir / "links.json").write_text(json.dumps(links_data))
        
        collector = DocsCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docs_total_links"] == 2.0
        assert metrics["docs_broken_links"] == 1.0

    def test_get_config_example(self):
        """Test config example."""
        collector = DocsCollector()
        example = collector.get_config_example()
        
        assert "docs_docstring_coverage_min" in example


class TestCheckReadme:
    """Test README checking."""

    def test_readme_not_found(self, tmp_path: Path):
        """Test handling missing README."""
        result = check_readme(cwd=tmp_path)
        
        assert result["success"] is False
        assert result["exists"] is False

    def test_readme_quality_check(self, tmp_path: Path):
        """Test README quality analysis."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Test Project

## Installation
Install via pip.

## Usage
Use it like this.

## License
MIT
""")
        
        result = check_readme(cwd=tmp_path)
        
        assert result["success"] is True
        assert result["exists"] is True
        assert result["has_install"] is True
        assert result["has_usage"] is True
        assert result["has_license"] is True
        assert result["is_quality"] is True


class TestInterrogate:
    """Test interrogate integration."""

    def test_interrogate_not_found(self, tmp_path: Path):
        """Test graceful handling when interrogate is not installed."""
        result = run_interrogate(paths=[str(tmp_path)])
        
        assert "success" in result
        if not result["success"]:
            assert "not found" in result.get("error", "").lower() or "interrogate" in result.get("error", "").lower()


class TestCheckLinks:
    """Test link checking."""

    def test_lychee_not_found(self, tmp_path: Path):
        """Test graceful handling when lychee is not installed."""
        result = check_links(files=["README.md"], cwd=tmp_path)
        
        # Should not fail, just report tool not found
        assert "success" in result


class TestDocsQualitySummary:
    """Test comprehensive docs summary."""

    def test_summary_structure(self, tmp_path: Path):
        """Test summary contains expected keys."""
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n\n## Install\n\n## Usage\n")
        
        summary = docs_quality_summary(cwd=tmp_path)
        
        assert "success" in summary
        assert "metrics" in summary
        assert "readme" in summary
        assert "recommendations" in summary
