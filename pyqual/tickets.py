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
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync tickets via planfile backends."""
    sync_integration = _load_sync_integration()
    for index, integration_name in enumerate(_normalize_sources(source)):
        sync_integration(
            integration_name,
            str(workdir),
            dry_run,
            direction,
            show_header=index == 0,
        )


def sync_todo_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md tickets through planfile's markdown backend."""
    sync_planfile_tickets("todo", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_github_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync GitHub issues through planfile's GitHub backend."""
    sync_planfile_tickets("github", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_all_tickets(
    workdir: Path = Path("."),
    dry_run: bool = False,
    direction: str = "both",
) -> None:
    """Sync TODO.md and GitHub tickets through planfile."""
    sync_planfile_tickets("all", workdir=workdir, dry_run=dry_run, direction=direction)


def sync_from_gates(
    workdir: Path = Path("."),
    dry_run: bool = False,
    backends: list[str] | None = None,
) -> dict:
    """Check gates and sync tickets only if gates fail.

    This is what pyqual does internally when `on_fail: create_ticket` is set.
    Use this for programmatic gate-based ticket creation.

    Args:
        workdir: Project directory containing pyqual.yaml
        dry_run: Preview without making changes
        backends: List of backends to sync (default: ["markdown"])

    Returns:
        dict with {synced: bool, failures: list[str], backends: list[str]}
    """
    from pyqual.config import PyqualConfig
    from pyqual.gates import GateSet

    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"pyqual.yaml not found in {workdir}")

    config = PyqualConfig.load(config_path)
    gate_set = GateSet(config.gates)
    results = gate_set.check_all(workdir)

    failures = [r for r in results if not r.passed]

    if not failures:
        return {"synced": False, "failures": [], "backends": [], "all_passed": True}

    backends = backends or ["markdown"]

    if "all" in backends:
        sync_all_tickets(workdir=workdir, dry_run=dry_run, direction="from")
    else:
        for backend in backends:
            sync_planfile_tickets(backend, workdir=workdir, dry_run=dry_run, direction="from")

    return {
        "synced": True,
        "failures": [f.metric for f in failures],
        "backends": backends,
        "all_passed": False,
    }
