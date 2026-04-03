"""Tests for the example plugin.

Run with: pytest pyqual/plugins/example_plugin/test.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pyqual.plugins.example_plugin.main import (
    ExampleCollector,
    example_helper_function,
)


class TestExampleCollector:
    """Tests for the ExampleCollector class."""

    def test_collector_registration(self):
        """Test that ExampleCollector is properly registered."""
        from pyqual.plugins import PluginRegistry
        
        collector_class = PluginRegistry.get("example")
        assert collector_class is not None
        assert collector_class.name == "example"

    def test_metadata(self):
        """Test collector metadata."""
        collector = ExampleCollector()
        
        assert collector.metadata.name == "example"
        assert "example" in collector.metadata.tags
        assert collector.metadata.version == "1.0.0"

    def test_config_example(self):
        """Test that config example is provided."""
        collector = ExampleCollector()
        config = collector.get_config_example()
        
        assert "example_metric" in config
        assert "stages:" in config

    def test_collect_with_valid_artifact(self):
        """Test collecting metrics from valid artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()
            
            # Create example.json artifact
            artifact = pyqual_dir / "example.json"
            artifact.write_text(json.dumps({"metric": 0.95}))
            
            collector = ExampleCollector()
            result = collector.collect(workdir)
            
            assert result["example_metric"] == 0.95

    def test_collect_without_artifact(self):
        """Test collecting when artifact doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            collector = ExampleCollector()
            result = collector.collect(workdir)
            
            assert result == {}

    def test_collect_with_invalid_json(self):
        """Test collecting with invalid JSON artifact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            pyqual_dir = workdir / ".pyqual"
            pyqual_dir.mkdir()
            
            # Create invalid artifact
            artifact = pyqual_dir / "example.json"
            artifact.write_text("not valid json")
            
            collector = ExampleCollector()
            result = collector.collect(workdir)
            
            assert result == {}


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_example_helper_function(self):
        """Test the example helper function."""
        result = example_helper_function()
        
        assert result["success"] is True
        assert "message" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
