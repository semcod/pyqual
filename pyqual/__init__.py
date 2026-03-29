"""pyqual — declarative quality gate loops for AI-assisted development."""

from pyqual.config import PyqualConfig, GateConfig, StageConfig, LoopConfig
from pyqual.gates import Gate, GateSet, GateResult
from pyqual.llm import LLM, LLMResponse, get_llm
from pyqual.pipeline import Pipeline, PipelineResult, StageResult, IterationResult
from pyqual.plugins import (
    MetricCollector,
    PluginRegistry,
    PluginMetadata,
    get_available_plugins,
    install_plugin_config,
)

__version__ = "0.1.16"

__all__ = [
    "PyqualConfig",
    "GateConfig",
    "StageConfig",
    "LoopConfig",
    "Gate",
    "GateSet",
    "GateResult",
    "Pipeline",
    "PipelineResult",
    "StageResult",
    "IterationResult",
    "LLM",
    "LLMResponse",
    "get_llm",
    # Plugin system
    "MetricCollector",
    "PluginRegistry",
    "PluginMetadata",
    "get_available_plugins",
    "install_plugin_config",
    "__version__",
]
