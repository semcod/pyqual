"""Init and profiles commands.
"""

from __future__ import annotations

from pathlib import Path

import typer

from pyqual.cli.main import app, console
from pyqual.config import PyqualConfig
from rich.table import Table


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory"),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Use a built-in profile (e.g. python, python-full, ci, lint-only, security). See 'pyqual profiles'."),
) -> None:
    """Create pyqual.yaml with sensible defaults.

    Use --profile for a minimal config based on a built-in profile:

        pyqual init --profile python          # 6-line YAML
        pyqual init --profile python-full     # includes push & publish
        pyqual init --profile ci              # report-only, no fix
    """
    target = path / "pyqual.yaml"
    if target.exists():
        overwrite = typer.confirm(f"{target} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    if profile:
        from pyqual.profiles import get_profile, list_profiles
        prof = get_profile(profile)
        if prof is None:
            console.print(f"[red]Unknown profile '{profile}'.[/red]")
            console.print(f"Available: {', '.join(list_profiles())}")
            raise typer.Exit(1)
        yaml_content = f"""\
pipeline:
  profile: {profile}

  # Override metrics (profile defaults: {', '.join(f'{k}={v}' for k, v in prof.metrics.items())}):
  # metrics:
  #   coverage_min: 55

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
"""
        target.write_text(yaml_content)
    else:
        target.write_text(PyqualConfig.default_yaml())

    (path / ".pyqual").mkdir(exist_ok=True)
    console.print(f"[green]Created {target}[/green]")
    if profile:
        console.print(f"Using profile [bold]{profile}[/bold]: {prof.description}")
    console.print("Run: [bold]pyqual run[/bold]")


@app.command()
def profiles() -> None:
    """List available pipeline profiles for pyqual.yaml.

    Profiles provide pre-configured stage lists and metrics so you can write
    a minimal pyqual.yaml:

        pipeline:
          profile: python
          metrics:
            coverage_min: 55    # override only what you need
    """
    from pyqual.profiles import PROFILES

    table = Table(title="Available Profiles", show_lines=True)
    table.add_column("Profile", style="bold cyan")
    table.add_column("Description")
    table.add_column("Stages", style="dim")
    table.add_column("Gates", style="dim")

    for name, prof in sorted(PROFILES.items()):
        stage_names = ", ".join(s["name"] for s in prof.stages)
        gate_names = ", ".join(prof.metrics.keys()) if prof.metrics else "—"
        table.add_row(name, prof.description, stage_names, gate_names)

    console.print(table)
    console.print("\n[dim]Usage: set 'profile: <name>' in pyqual.yaml under pipeline:[/dim]")
