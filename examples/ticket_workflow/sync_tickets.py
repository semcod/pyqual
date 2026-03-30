#!/usr/bin/env python3
"""Programmatic ticket sync with planfile — TODO.md and GitHub Issues.

Demonstrates:
- Syncing TODO.md tickets via planfile's markdown backend
- Syncing GitHub Issues via planfile's GitHub backend
- Combining both sync directions
- Checking gate results and auto-creating tickets for failures
- Dry-run mode for previewing changes

Usage:
    python sync_tickets.py                # sync TODO.md
    python sync_tickets.py --github       # sync GitHub issues
    python sync_tickets.py --all          # sync both
    python sync_tickets.py --dry-run      # preview only
    python sync_tickets.py --from-gates   # create tickets from gate failures
"""

from __future__ import annotations

import sys
from pathlib import Path

from pyqual.config import PyqualConfig, GateConfig
from pyqual.gates import GateSet
from pyqual.tickets import sync_todo_tickets, sync_github_tickets, sync_all_tickets


def sync_from_cli(args: list[str]) -> int:
    """Parse CLI args and run the appropriate sync."""
    dry_run = "--dry-run" in args
    direction = "both"

    if "--github" in args:
        print(f"Syncing GitHub Issues (dry_run={dry_run}, direction={direction})...")
        sync_github_tickets(directory=Path("."), dry_run=dry_run, direction=direction)
    elif "--all" in args:
        print(f"Syncing TODO.md + GitHub (dry_run={dry_run}, direction={direction})...")
        sync_all_tickets(directory=Path("."), dry_run=dry_run, direction=direction)
    else:
        print(f"Syncing TODO.md (dry_run={dry_run}, direction={direction})...")
        sync_todo_tickets(directory=Path("."), dry_run=dry_run, direction=direction)

    print("Done.")
    return 0


def tickets_from_gate_failures(workdir: Path, dry_run: bool = False) -> int:
    """Check gates and create tickets for any failures.

    This is what pyqual does internally when `on_fail: create_ticket` is set.
    This example shows how to do it programmatically.
    """
    config_path = workdir / "pyqual.yaml"
    if not config_path.exists():
        print("Error: pyqual.yaml not found.")
        return 1

    config = PyqualConfig.load(config_path)
    gate_set = GateSet(config.gates)
    results = gate_set.check_all(workdir)

    failures = [r for r in results if not r.passed]

    if not failures:
        print("✅ All gates pass — no tickets needed.")
        return 0

    print(f"❌ {len(failures)} gate(s) failed:")
    for f in failures:
        val = f"{f.value:.1f}" if f.value is not None else "N/A"
        print(f"  - {f.metric}: {val} (threshold: {f.threshold})")

    print(f"\nSyncing TODO.md tickets (dry_run={dry_run})...")
    sync_todo_tickets(directory=workdir, dry_run=dry_run, direction="both")
    print("Tickets synced.")
    return 1


def main() -> int:
    args = sys.argv[1:]

    if "--from-gates" in args:
        dry_run = "--dry-run" in args
        return tickets_from_gate_failures(Path("."), dry_run=dry_run)

    return sync_from_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
