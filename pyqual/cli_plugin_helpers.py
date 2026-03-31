"""Plugin command helper functions for pyqual CLI."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from pyqual.constants import MAX_DESCRIPTION_LENGTH
from pyqual.plugins import get_available_plugins, install_plugin_config

console = Console()


def plugin_list(plugins: dict[str, object], tag: str | None) -> None:
    """List available plugins, optionally filtered by tag."""
    if tag:
        plugins = {k: v for k, v in plugins.items() if tag in getattr(v, "tags", [])}

    if not plugins:
        console.print(
            "[yellow]No plugins available.[/yellow]"
            if not tag
            else f"[yellow]No plugins with tag '{tag}' found.[/yellow]"
        )
        return

    title = f"Available Plugins ({len(plugins)} total)" if not tag else f"Plugins with tag '{tag}' ({len(plugins)})"
    table = Table(title=title)
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    table.add_column("Tags")

    for plugin_name, meta in sorted(plugins.items()):
        tags = ", ".join(getattr(meta, "tags", [])[:3]) if getattr(meta, "tags", None) else ""
        table.add_row(plugin_name, getattr(meta, "description", "")[:MAX_DESCRIPTION_LENGTH], getattr(meta, "version", ""), tags)

    console.print(table)


def plugin_search(plugins: dict[str, object], query: str) -> None:
    """Search plugins by name, description, or tags."""
    if not query:
        console.print("[red]Search query required. Usage: pyqual plugin search <query>[/red]")
        raise typer.Exit(1)

    results = {}
    normalized_query = query.lower()
    for plugin_name, meta in plugins.items():
        description = getattr(meta, "description", "")
        tags = getattr(meta, "tags", []) or []
        if (
            normalized_query in plugin_name.lower()
            or normalized_query in description.lower()
            or any(normalized_query in str(tag).lower() for tag in tags)
        ):
            results[plugin_name] = meta

    if not results:
        console.print(f"[yellow]No plugins found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search results for '{query}' ({len(results)} found)")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Tags")

    for plugin_name, meta in sorted(results.items()):
        tags = ", ".join(getattr(meta, "tags", [])[:3]) if getattr(meta, "tags", None) else ""
        table.add_row(plugin_name, getattr(meta, "description", "")[:MAX_DESCRIPTION_LENGTH], tags)

    console.print(table)


def plugin_info(name: str | None, workdir: Path) -> None:
    """Show detailed info and configuration example for a plugin."""
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin info <name>[/red]")
        raise typer.Exit(1)

    meta = get_available_plugins().get(name)
    if not meta:
        console.print(f"[red]Unknown plugin: {name}[/red]")
        console.print("Run 'pyqual plugin list' to see available plugins.")
        raise typer.Exit(1)

    console.print(f"[bold]{meta.name}[/bold] v{meta.version}")
    console.print(f"Description: {meta.description}")
    if meta.author:
        console.print(f"Author: {meta.author}")
    if meta.tags:
        console.print(f"Tags: {', '.join(meta.tags)}")
    console.print()
    console.print("[bold]Configuration example:[/bold]")
    console.print(install_plugin_config(name, workdir))


def plugin_add(name: str | None, workdir: Path) -> None:
    """Add a plugin's configuration snippet to pyqual.yaml."""
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin add <name>[/red]")
        raise typer.Exit(1)

    meta = get_available_plugins().get(name)
    if not meta:
        console.print(f"[red]Unknown plugin: {name}[/red]")
        console.print("Run 'pyqual plugin list' to see available plugins.")
        raise typer.Exit(1)

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        console.print("Run 'pyqual init' first.")
        raise typer.Exit(1)

    plugin_config = install_plugin_config(name, workdir)
    existing = config_path.read_text()
    if f"# {name} plugin" in existing:
        console.print(f"[yellow]Plugin {name} already appears in pyqual.yaml[/yellow]")
        return

    with open(config_path, "a") as f:
        f.write(f"\n# {name} plugin configuration\n")
        f.write(plugin_config)

    console.print(f"[green]Added {name} plugin configuration to pyqual.yaml[/green]")
    console.print("Review and customize the added metrics and stages.")


def plugin_remove(name: str | None, workdir: Path) -> None:
    """Remove a plugin's configuration block from pyqual.yaml."""
    if not name:
        console.print("[red]Plugin name required. Usage: pyqual plugin remove <name>[/red]")
        raise typer.Exit(1)

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        raise typer.Exit(1)

    existing = config_path.read_text()
    marker = f"# {name} plugin configuration"
    if marker not in existing:
        console.print(f"[yellow]Plugin {name} not found in pyqual.yaml[/yellow]")
        raise typer.Exit(1)

    lines = existing.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        if marker in line:
            skip = True
            continue
        if skip and line.startswith("# ") and "plugin" in line:
            skip = False
        if not skip:
            new_lines.append(line)

    config_path.write_text("\n".join(new_lines))
    console.print(f"[green]Removed {name} plugin configuration from pyqual.yaml[/green]")


def plugin_validate(plugins: dict[str, object], workdir: Path) -> None:
    """Validate that configured plugins in pyqual.yaml are available."""
    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        console.print(f"[red]pyqual.yaml not found in {workdir}[/red]")
        raise typer.Exit(1)

    existing = config_path.read_text()
    found_plugins = [plugin_name for plugin_name in plugins if f"# {plugin_name} plugin" in existing]

    console.print("[bold]Validation Results[/bold]")
    console.print(f"Found {len(found_plugins)} configured plugins: {', '.join(found_plugins)}")

    available = set(plugins.keys())
    configured = set(found_plugins)
    missing = available - configured

    if missing:
        console.print(f"\n[yellow]Available but not configured:[/yellow] {', '.join(sorted(missing))}")

    console.print("\n[green]✓ Configuration is valid[/green]")


def plugin_unknown_action(action: str) -> None:
    """Print an error for an unrecognized plugin sub-command."""
    console.print(f"[red]Unknown action: {action}[/red]")
    console.print("Supported actions: list, add, remove, info, search, validate")
    raise typer.Exit(1)
