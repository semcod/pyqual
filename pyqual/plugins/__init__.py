"""Plugin system for pyqual - extensible metric collectors.

Plugin Structure:
Each plugin should be in its own subdirectory under pyqual/plugins/:
    plugins/
    ├── __init__.py          # This file - auto-discovery
    ├── git/                 # Git plugin example
    │   ├── __init__.py      # Package exports
    │   ├── main.py          # Main plugin code with collector class
    │   ├── test.py          # Test suite
    │   └── README.md        # Documentation
    └── [other_plugins]/
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from pyqual._plugin_base import MetricCollector, PluginMetadata, PluginRegistry

# Auto-discover and import all plugins from subdirectories
def _discover_plugins() -> None:
    """Automatically discover and import all plugins from subdirectories."""
    package_dir = Path(__file__).parent
    
    for _, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
        if ispkg and not name.startswith("_"):
            try:
                # Import the plugin package (triggers @PluginRegistry.register)
                importlib.import_module(f"pyqual.plugins.{name}")
            except Exception as e:
                # Log but don't crash if a plugin fails to load
                import warnings
                warnings.warn(f"Failed to load plugin '{name}': {e}", RuntimeWarning)

# Import built-in collectors first
from pyqual.builtin_collectors import (  # noqa: E402
    A11yCollector,
    HallucinationCollector,
    I18nCollector,
    LLMBenchCollector,
    LlxMcpFixCollector,
    RepoMetricsCollector,
    SBOMCollector,
    SecurityCollector,
)

# Auto-discover plugins from plugins/ directory
_discover_plugins()

__all__ = [
    "PluginMetadata",
    "MetricCollector",
    "PluginRegistry",
    "LLMBenchCollector",
    "HallucinationCollector",
    "SBOMCollector",
    "I18nCollector",
    "A11yCollector",
    "RepoMetricsCollector",
    "SecurityCollector",
    "LlxMcpFixCollector",
    "get_available_plugins",
    "install_plugin_config",
    "_discover_plugins",
]


def get_available_plugins() -> dict[str, PluginMetadata]:
    """Get metadata for all available built-in plugins."""
    return {
        name: plugin.metadata
        for name, plugin in PluginRegistry._plugins.items()
    }


def install_plugin_config(name: str, workdir: Path = Path(".")) -> str:
    """Generate YAML configuration snippet for a named plugin."""
    plugin_class = PluginRegistry.get(name)
    if not plugin_class:
        raise ValueError(f"Unknown plugin: {name}")

    instance = plugin_class()
    return instance.get_config_example()
