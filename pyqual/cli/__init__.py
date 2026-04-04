"""CLI for pyqual — declarative quality gate loops.

This package contains modular command implementations.
All command implementations have been extracted to separate modules for
better maintainability and reduced complexity.
"""

from __future__ import annotations

# Import main app and shared objects first
from pyqual.cli.main import app, console, stderr_console, setup_logging

# Import all command modules to trigger @app.command() decorators
# The modules self-register their commands with the app
from pyqual.cli import (
    cmd_init,
    cmd_run,
    cmd_config,
    cmd_mcp,
    cmd_info,
    cmd_plugin,
    cmd_tickets,
    cmd_git,
)

# Backward-compatible re-exports for tests and external code
from pyqual.cli.cmd_mcp import run_llx_fix_workflow, run_llx_refactor_workflow, run_llx_mcp_service
from pyqual.cli.cmd_tickets import sync_todo_tickets, sync_github_tickets, sync_all_tickets
from pyqual.pipeline import Pipeline

__all__ = [
    "app",
    "console", 
    "stderr_console",
    "setup_logging",
    # Re-exports for backward compatibility
    "run_llx_fix_workflow",
    "run_llx_refactor_workflow",
    "run_llx_mcp_service",
    "sync_todo_tickets",
    "sync_github_tickets",
    "sync_all_tickets",
]
