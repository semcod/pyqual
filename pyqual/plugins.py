"""Plugin system for pyqual - extensible metric collectors."""

from pathlib import Path

from pyqual._plugin_base import MetricCollector, PluginMetadata, PluginRegistry

# Import built-in collectors to trigger registration side-effects.
# This import must come after PluginRegistry/MetricCollector/PluginMetadata are defined.
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
