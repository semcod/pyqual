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
from pyqual.integrations.llx_mcp import (
    LlxMcpClient,
    LlxMcpRunResult,
    build_fix_prompt,
    run_llx_fix_workflow,
)

__version__ = "0.1.23"

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
    "LlxMcpClient",
    "LlxMcpRunResult",
    "build_fix_prompt",
    "run_llx_fix_workflow",
    "__version__",
]
