"""pyqual — declarative quality gate loops for AI-assisted development."""

from pyqual.config import PyqualConfig, GateConfig, StageConfig, LoopConfig
from pyqual.gates import Gate, GateSet, GateResult
from pyqual.pipeline import Pipeline, PipelineResult, StageResult, IterationResult
from pyqual.plugins import (
    MetricCollector,
    PluginRegistry,
    PluginMetadata,
    get_available_plugins,
    install_plugin_config,
)
from pyqual.tools import (
    ToolPreset,
    get_preset,
    list_presets,
    is_builtin,
    register_preset,
    register_custom_tools_from_yaml,
    load_entry_point_presets,
    TOOL_PRESETS,
)

try:
    from llx.llm import DEFAULT_MAX_TOKENS, LLM, LLMResponse, get_api_key, get_llm, get_llm_model
except Exception:  # pragma: no cover - llx is optional in some environments
    from pyqual.llm import DEFAULT_MAX_TOKENS, LLM, LLMResponse, get_api_key, get_llm, get_llm_model

try:
    from pyqual.integrations.llx_mcp import (
        LlxMcpClient,
        LlxMcpRunResult,
        build_fix_prompt,
        run_llx_fix_workflow,
        run_llx_refactor_workflow,
    )
except Exception:  # pragma: no cover - llx MCP modules are optional
    LlxMcpClient = None  # type: ignore[assignment,misc]
    LlxMcpRunResult = None  # type: ignore[assignment,misc]
    build_fix_prompt = None  # type: ignore[assignment]
    run_llx_fix_workflow = None  # type: ignore[assignment]
    run_llx_refactor_workflow = None  # type: ignore[assignment]

__version__ = "0.1.45"

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
    "DEFAULT_MAX_TOKENS",
    "LLM",
    "LLMResponse",
    "get_api_key",
    "get_llm",
    "get_llm_model",
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
    "run_llx_refactor_workflow",
    # Tool presets
    "ToolPreset",
    "get_preset",
    "list_presets",
    "is_builtin",
    "register_preset",
    "register_custom_tools_from_yaml",
    "load_entry_point_presets",
    "TOOL_PRESETS",
    "__version__",
]
