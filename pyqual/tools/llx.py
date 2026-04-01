"""LLX tool for parallel TODO fix.

Uses llx fix command with LLM-driven fixes.
"""

from __future__ import annotations

import os

from .base import FixTool


class LlxTool(FixTool):
    """LLX fix tool."""
    
    def __init__(self, batch_file: str, batch_count: int, llm_model: str | None = None):
        super().__init__(batch_file, batch_count, llm_model)
        # Use env model if not specified
        if llm_model is None:
            self.llm_model = os.environ.get("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    
    def is_available(self) -> bool:
        """Check if llx is installed."""
        try:
            import llx  # noqa: F401
            return True
        except ImportError:
            return False
    
    def get_command(self) -> str:
        """Get llx fix command for batch processing."""
        return f"LLM_MODEL={self.llm_model} llx fix . --apply --errors {self.batch_file} --verbose"
    
    def get_timeout(self) -> int:
        """LLX timeout: 10 minutes per batch."""
        return 600
