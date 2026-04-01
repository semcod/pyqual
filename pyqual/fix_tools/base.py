"""Base class for fix tools.

Provides common interface for all TODO fix tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result from running a fix tool."""
    name: str
    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration: float


class FixTool(ABC):
    """Abstract base class for fix tools."""
    
    def __init__(self, batch_file: str, batch_count: int, llm_model: str | None = None):
        self.batch_file = batch_file
        self.batch_count = batch_count
        self.llm_model = llm_model or "openrouter/qwen/qwen3-coder-next"
        self.name = self.__class__.__name__.replace("Tool", "").lower()
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this tool is available in the current environment."""
        pass
    
    @abstractmethod
    def get_command(self) -> str:
        """Get the shell command to run this tool."""
        pass
    
    @abstractmethod
    def get_timeout(self) -> int:
        """Get timeout in seconds for this tool."""
        pass
    
    def to_config(self) -> dict:
        """Convert to tool configuration dict."""
        return {
            "name": self.name,
            "command": self.get_command(),
            "timeout": self.get_timeout(),
        }
