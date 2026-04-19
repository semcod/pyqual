"""pyqual — declarative quality gate loops for AI-assisted development."""

# Re-export the public API module for easy access
from pyqual import api

from pyqual.api import (
    load_config,
    validate_config,
    create_default_config,
    run_pipeline,
    run,
    check_gates,
    dry_run,
    run_stage,
    get_tool_command,
    format_result_summary,
    export_results_json,
    shell,
    shell_check,
)

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
from pyqual.plugins.git import (
    GitCollector,
    SECRET_PATTERNS,
    git_status,
    git_add,
    git_commit,
    git_push,
    scan_for_secrets,
    preflight_push_check,
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

from pyqual.yaml_fixer import (
    YamlErrorType,
    YamlFixResult,
    YamlSyntaxIssue,
    analyze_yaml_syntax,
    fix_yaml_file,
)

__version__ = "0.1.143"

__all__ = [
    # Public API module
    "api",
    # High-level API functions
    "load_config",
    "validate_config",
    "create_default_config",
    "run_pipeline",
    "run",
    "check_gates",
    "dry_run",
    "run_stage",
    "get_tool_command",
    "format_result_summary",
    "export_results_json",
    "shell",
    "shell_check",
    # Core classes
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
    # Git plugin
    "GitCollector",
    "SECRET_PATTERNS",
    "git_status",
    "git_add",
    "git_commit",
    "git_push",
    "scan_for_secrets",
    "preflight_push_check",
    # Tool presets
    "ToolPreset",
    "get_preset",
    "list_presets",
    "is_builtin",
    "register_preset",
    "register_custom_tools_from_yaml",
    "load_entry_point_presets",
    "TOOL_PRESETS",
    # YAML fixer
    "YamlErrorType",
    "YamlFixResult",
    "YamlSyntaxIssue",
    "analyze_yaml_syntax",
    "fix_yaml_file",
    "__version__",
]
