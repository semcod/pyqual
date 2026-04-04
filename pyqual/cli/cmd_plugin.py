"""Plugin management command.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from pyqual.cli.main import app, console
from pyqual.plugins import get_available_plugins

if TYPE_CHECKING:
    pass


@app.command()
def plugin(
    action: str = typer.Argument(..., help="Action: list, add, remove, info, search, validate"),
    name: str | None = typer.Argument(None, help="Plugin name (for add/remove/info)"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag (for list/search)"),
) -> None:
    """Manage pyqual plugins - add, remove, search metric collectors."""
    from pyqual.cli_plugin_helpers import (
        plugin_add, plugin_info, plugin_list, plugin_remove,
        plugin_search, plugin_unknown_action, plugin_validate,
    )
    plugins = get_available_plugins()
    if action == "list":
        plugin_list(plugins, tag)
    elif action == "search":
        plugin_search(plugins, name or "")
    elif action == "info":
        plugin_info(name, workdir)
    elif action == "add":
        plugin_add(name, workdir)
    elif action == "remove":
        plugin_remove(name, workdir)
    elif action == "validate":
        plugin_validate(plugins, workdir)
    else:
        plugin_unknown_action(action)
