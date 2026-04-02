"""Base classes for the pyqual plugin system.

Extracted from ``plugins.py`` to reduce its maintainability index score.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Type


@dataclass
class PluginMetadata:
    """Metadata for a pyqual plugin."""
    name: str
    description: str
    version: str
    author: str = ""
    tags: list[str] = None
    config_example: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MetricCollector(ABC):
    """Base class for metric collector plugins."""

    name: ClassVar[str] = ""
    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="",
        description="",
        version="0.1.0"
    )

    @abstractmethod
    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect metrics from workdir/.pyqual/ artifacts."""
        ...

    def get_config_example(self) -> str:
        """Return example YAML configuration for this plugin."""
        return f"""\
# {self.metadata.name} plugin configuration
pipeline:
  metrics:
    {self.name}_min: 0.8
  stages:
    - name: {self.name}_check
      run: echo "Run your tool here > .pyqual/output.json"
"""


class PluginRegistry:
    """Registry for metric collector plugins."""

    _plugins: dict[str, Type[MetricCollector]] = {}

    @classmethod
    def register(cls, plugin_class: Type[MetricCollector]) -> Type[MetricCollector]:
        """Register a plugin class. Can be used as a decorator."""
        cls._plugins[plugin_class.name] = plugin_class
        return plugin_class

    @classmethod
    def get(cls, name: str) -> Type[MetricCollector] | None:
        """Get a plugin class by name."""
        return cls._plugins.get(name)

    @classmethod
    def list_plugins(cls, tag: str | None = None) -> list[Type[MetricCollector]]:
        """List all registered plugins, optionally filtered by tag."""
        plugins = list(cls._plugins.values())
        if tag:
            plugins = [p for p in plugins if tag in (p.metadata.tags or [])]
        return plugins

    @classmethod
    def create_instance(cls, name: str) -> MetricCollector | None:
        """Create an instance of a registered plugin."""
        plugin_class = cls._plugins.get(name)
        if plugin_class:
            return plugin_class()
        return None
