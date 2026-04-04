"""Info commands: doctor, tools.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from rich.table import Table

from pyqual.cli.main import app, console
from pyqual.constants import STATUS_COLUMN_WIDTH

if TYPE_CHECKING:
    pass


@app.command()
def doctor() -> None:
    """Check availability of external tools used by pyqual collectors."""
    tools = [
        ("docker", "Container runtime for the llx MCP service", "Install Docker Engine"),
        ("bandit", "Security scanner", "pip install bandit"),
        ("pip-audit", "Dependency vulnerability scanner", "pip install pip-audit"),
        ("trufflehog", "Secret scanner", "brew install trufflehog"),
        ("gitleaks", "Alternative secret scanner", "brew install gitleaks"),
        ("mypy", "Type checker", "pip install mypy"),
        ("ruff", "Modern Python linter", "pip install ruff"),
        ("pylint", "Comprehensive linter", "pip install pylint"),
        ("flake8", "Style guide checker", "pip install flake8"),
        ("radon", "Complexity analyzer", "pip install radon"),
        ("interrogate", "Docstring coverage", "pip install interrogate"),
        ("vulture", "Dead code finder", "pip install vulture"),
        ("pytest", "Test runner", "pip install pytest"),
        ("code2llm", "Code analysis", "pip install code2llm"),
        ("vallm", "LLM validation", "pip install vallm"),
        ("uvicorn", "ASGI server for the llx MCP service", "pip install pyqual[mcp]"),
    ]

    table = Table(title="Tool Availability Check")
    table.add_column("Tool")
    table.add_column("Status", width=STATUS_COLUMN_WIDTH)
    table.add_column("Purpose")
    table.add_column("Install Command")

    available = 0
    for tool, purpose, install in tools:
        path = shutil.which(tool)
        if path:
            table.add_row(tool, "[green]✓ Available[/green]", purpose, "")
            available += 1
        else:
            table.add_row(tool, "[red]✗ Missing[/red]", purpose, install)

    console.print(table)
    console.print()
    console.print(f"[bold]{available}/{len(tools)} tools available[/bold]")

    if available < len(tools):
        console.print("\n[yellow]Install missing tools to enable all metrics:[/yellow]")
        console.print("  pip install bandit pip-audit mypy ruff pylint flake8 radon interrogate vulture")
        console.print("  # For secret scanning, install trufflehog or gitleaks separately")


@app.command()
def tools() -> None:
    """List built-in tool presets for pipeline stages."""
    from pyqual.tools import TOOL_PRESETS

    table = Table(title="Built-in Tool Presets")
    table.add_column("Tool")
    table.add_column("Binary")
    table.add_column("Output")
    table.add_column("Allow Failure")
    table.add_column("Available")

    for name in sorted(TOOL_PRESETS):
        preset = TOOL_PRESETS[name]
        avail = "[green]✓[/green]" if preset.is_available() else "[red]✗[/red]"
        af = "yes" if preset.allow_failure else "no"
        table.add_row(name, preset.binary, preset.output or "(inline)", af, avail)

    console.print(table)
    console.print()
    console.print("[dim]Use in pyqual.yaml:[/dim]")
    console.print("  stages:")
    console.print("    - name: lint")
    console.print("      tool: ruff")
    console.print("    - name: secrets")
    console.print("      tool: trufflehog")
    console.print("      optional: true")
