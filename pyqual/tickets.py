"""Planfile-backed ticket sync helpers for TODO.md and GitHub."""

from pathlib import Path

PLANFILE_MARKDOWN_SOURCE = "markdown"
PLANFILE_GITHUB_SOURCE = "github"
PLANFILE_TODO_SOURCE = "todo"


def _load_sync_integration():
    try:
        from planfile.cli.cmd.cmd_sync import sync_integration
    except ImportError as exc:  # pragma: no cover - dependency error
        raise RuntimeError(
            "planfile is required for ticket sync. Install it with: pip install pyqual[planfile]"
        ) from exc
    return sync_integration


def _normalize_sources(source: str) -> list[str]:
    normalized = source.lower()
    if normalized == PLANFILE_TODO_SOURCE:
        return [PLANFILE_MARKDOWN_SOURCE]
    if normalized in {PLANFILE_MARKDOWN_SOURCE, PLANFILE_GITHUB_SOURCE}:
        return [normalized]
    if normalized == "all":
        return [PLANFILE_MARKDOWN_SOURCE, PLANFILE_GITHUB_SOURCE]
    raise ValueError(f"Unknown ticket source: {source}")


def sync_planfile_tickets(
    source: str,
    directory: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync tickets via planfile backends."""
    sync_integration = _load_sync_integration()
    for index, integration_name in enumerate(_normalize_sources(source)):
        sync_integration(
            integration_name,
            str(directory),
            dry_run,
            direction,
            show_header=index == 0,
        )


def sync_todo_tickets(
    directory: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md tickets through planfile's markdown backend."""
    sync_planfile_tickets("todo", directory=directory, dry_run=dry_run, direction=direction)


def sync_github_tickets(
    directory: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync GitHub issues through planfile's GitHub backend."""
    sync_planfile_tickets("github", directory=directory, dry_run=dry_run, direction=direction)


def sync_all_tickets(
    directory: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md and GitHub tickets through planfile."""
    sync_planfile_tickets("all", directory=directory, dry_run=dry_run, direction=direction)
