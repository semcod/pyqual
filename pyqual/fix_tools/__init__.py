"""Fix tools for parallel TODO processing.

This package provides modular tool implementations for processing
TODO.md items in parallel with configurable batch sizes.
"""

from __future__ import annotations

from .base import FixTool, ToolResult
from .claude import ClaudeTool
from .llx import LlxTool
from .aider import AiderTool

__all__ = ["FixTool", "ToolResult", "ClaudeTool", "LlxTool", "AiderTool", "get_available_tools"]


def get_available_tools(batch_file: str, batch_count: int, llm_model: str | None = None, skip_claude: bool = False) -> list[FixTool]:
    """Get list of available tools configured for current batch.
    
    Args:
        batch_file: Path to batch TODO file
        batch_count: Number of items in this batch
        llm_model: Optional LLM model override
        skip_claude: If True, skip Claude Code tool (useful when rate-limited)
        
    Returns:
        List of initialized tools that are available in this environment
    """
    tools: list[FixTool] = []
    
    # Try Claude Code (unless skipped)
    if not skip_claude:
        claude = ClaudeTool(batch_file, batch_count, llm_model)
        if claude.is_available():
            tools.append(claude)
    
    # Try llx
    llx = LlxTool(batch_file, batch_count, llm_model)
    if llx.is_available():
        tools.append(llx)
    
    # Try aider (Docker)
    aider = AiderTool(batch_file, batch_count, llm_model)
    if aider.is_available():
        tools.append(aider)
    
    return tools
