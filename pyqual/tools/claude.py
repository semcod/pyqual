"""Claude Code tool for parallel TODO fix.

Runs Claude Code CLI in non-interactive mode to fix TODO items.
"""

from __future__ import annotations

import shutil

from .base import FixTool


class ClaudeTool(FixTool):
    """Claude Code CLI tool."""
    
    def is_available(self) -> bool:
        """Check if claude CLI is installed."""
        return shutil.which("claude") is not None
    
    def get_command(self) -> str:
        """Get Claude Code command for batch processing."""
        return (
            f'claude -p "Fix these {self.batch_count} TODO items in this Python project. '
            'Apply minimal, safe changes. Focus on: unused imports, magic numbers, duplicate imports. '
            'Skip dependency updates." '
            '--model sonnet '
            '--allowedTools "Edit,Read,Write,Bash(git diff),Bash(python)" '
            '--output-format text'
        )
    
    def get_timeout(self) -> int:
        """Claude timeout: 15 minutes per batch."""
        return 900
