from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any


def run_git_command(args: list[str], cwd: Path | None = None) -> CompletedProcess[str]:
    """Run a git command and return the completed process."""
    return run(["git", *args], cwd=cwd, capture_output=True, text=True)

