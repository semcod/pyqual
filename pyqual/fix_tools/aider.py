"""Aider tool for parallel TODO fix.

Runs aider via Docker to fix TODO items.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import FixTool


class AiderTool(FixTool):
    """Aider tool via Docker (paulgauthier/aider)."""
    
    def is_available(self) -> bool:
        """Check if Docker and aider image are available."""
        if not shutil.which("docker"):
            return False
        
        # Check if aider image exists
        docker_check = subprocess.run(
            ["docker", "images", "-q", "paulgauthier/aider"],
            capture_output=True, text=True
        )
        return bool(docker_check.stdout.strip())
    
    def get_command(self) -> str:
        """Get aider Docker command for batch processing."""
        workdir = Path.cwd()
        return (
            'docker run --rm '
            f'-v "{workdir}:/app" '
            '-w /app '
            '-e OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" '
            '-e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" '
            '-e OPENAI_API_KEY="${OPENAI_API_KEY}" '
            'paulgauthier/aider '
            f'--model {self.llm_model} '
            '--yes --no-git '
            f'--read {self.batch_file} '
            f'--message "Fix these {self.batch_count} code issues. Focus on: unused imports, magic numbers, duplicate imports. Do NOT modify TODO.md itself."'
        )
    
    def get_timeout(self) -> int:
        """Aider timeout: 15 minutes per batch."""
        return 900
