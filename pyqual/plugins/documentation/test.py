"""Tests for the documentation plugin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyqual.plugins.documentation import DocumentationCollector


class TestDocumentationCollector:
    """Test DocumentationCollector metric collection."""

    def test_collector_name(self):
        assert DocumentationCollector.name == "documentation"

    def test_collector_metadata(self):
        collector = DocumentationCollector()
        assert collector.metadata.name == "documentation"
        assert "documentation" in collector.metadata.tags

    def test_collect_empty_workdir(self, tmp_path: Path):
        """Test collecting from empty workdir."""
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["readme_exists"] == 0.0
        assert metrics["license_exists"] == 0.0
        assert metrics["docs_folder_exists"] == 0.0

    def test_collect_with_readme(self, tmp_path: Path):
        """Test collecting with README present."""
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

![Build Status](https://img.shields.io/badge/build-passing)
""")
        
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["readme_exists"] == 1.0
        assert metrics["readme_has_installation"] == 1.0
        assert metrics["readme_has_usage"] == 1.0
        assert metrics["readme_has_license"] == 1.0
        assert metrics["readme_has_badges"] == 1.0
        assert metrics["readme_has_code_examples"] == 1.0
        assert metrics["readme_has_install"] == 1.0

    def test_collect_with_license(self, tmp_path: Path):
        """Test license detection."""
        license_file = tmp_path / "LICENSE"
        license_file.write_text("""MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
""")
        
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["license_exists"] == 1.0
        assert metrics["license_type_mit"] == 1.0
        assert metrics["license_spdx_score"] >= 80.0

    def test_collect_with_docs_folder(self, tmp_path: Path):
        """Test docs folder detection."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("# Documentation")
        (docs_dir / "api.md").write_text("# API Reference")
        
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["docs_folder_exists"] == 1.0
        assert metrics["docs_files_count"] == 2.0
        assert metrics["docs_has_index"] == 1.0
        assert metrics["docs_has_api"] == 1.0

    def test_collect_with_pyproject(self, tmp_path: Path):
        """Test pyproject.toml analysis."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""[project]
name = "myproject"
version = "1.0.0"
description = "A test project"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [{name = "Test", email = "test@example.com"}]
keywords = ["test", "python"]
classifiers = ["Development Status :: 4 - Beta"]

[project.urls]
Repository = "https://github.com/test/myproject"
""")
        
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert metrics["pyproject_fields"] == 6.0  # All required fields
        assert metrics["pyproject_completeness"] == 100.0
        assert metrics["pyproject_optional_fields"] >= 2.0  # authors, keywords, classifiers
        assert metrics["pyproject_has_repo_url"] == 1.0

    def test_get_config_example(self):
        """Test config example."""
        collector = DocumentationCollector()
        example = collector.get_config_example()
        
        # The config example comes from metadata and should contain documentation-related keys
        assert "documentation" in example.lower() or "metrics:" in example

    def test_documentation_score_calculation(self, tmp_path: Path):
        """Test that documentation score is calculated."""
        # Create minimal documentation
        (tmp_path / "README.md").write_text("# Test\n\n## Install\n\n## Usage\n\n## License\n")
        (tmp_path / "LICENSE").write_text("MIT License")
        
        collector = DocumentationCollector()
        metrics = collector.collect(tmp_path)
        
        assert "documentation_score" in metrics
        assert metrics["documentation_score"] > 0
