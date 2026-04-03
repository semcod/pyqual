"""Example plugin for pyqual - Template for new plugins.

This is a template showing how to create a new pyqual plugin.
Copy this directory and modify for your own plugin.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class ExampleCollector(MetricCollector):
    """Example collector showing plugin structure.
    
    This demonstrates how to create a custom metric collector.
    """

    name = "example"
    metadata = PluginMetadata(
        name="example",
        description="Example plugin demonstrating the pyqual plugin structure",
        version="1.0.0",
        tags=["example", "template"],
        config_example="""
metrics:
  example_metric_min: 0.8

stages:
  - name: example_stage
    run: echo '{"metric": 0.9}' > .pyqual/example.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect metrics from .pyqual/example.json artifact."""
        result: dict[str, float] = {}
        
        example_path = workdir / ".pyqual" / "example.json"
        if example_path.exists():
            try:
                data = json.loads(example_path.read_text())
                metric = data.get("metric")
                if metric is not None:
                    result["example_metric"] = float(metric)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return result

    def get_config_example(self) -> str:
        """Return example configuration."""
        return self.metadata.config_example


def example_helper_function() -> dict[str, Any]:
    """Helper function demonstrating utility functions in plugins."""
    return {"success": True, "message": "Example helper"}
