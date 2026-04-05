"""Entry point for ``python3 -m pyqual.plugins.attack``.

Allows invoking attack operations as a built-in pyqual tool:

    tool: attack-merge

Which runs:

    python3 -m pyqual.plugins.attack [check|merge]

Usage:
    python3 -m pyqual.plugins.attack          # default: merge
    python3 -m pyqual.plugins.attack check    # check only, write .pyqual/attack_check.json
    python3 -m pyqual.plugins.attack merge    # check + merge if needed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PYQUAL_DIR = Path(".pyqual")


def _ensure_dir() -> None:
    PYQUAL_DIR.mkdir(exist_ok=True)


def cmd_check() -> int:
    """Run attack check and write result to .pyqual/attack_check.json."""
    from pyqual.plugins.attack.main import attack_check

    _ensure_dir()
    result = attack_check()
    out = PYQUAL_DIR / "attack_check.json"
    out.write_text(json.dumps(result, indent=2))

    if not result.get("success"):
        print(f"Attack check failed: {result.get('error')}", file=sys.stderr)
        return 1

    conflicts = result.get("conflicts_detected", 0)
    behind = result.get("branches_behind", 0)
    print(f"Attack check OK — conflicts={conflicts}, behind={behind}")
    return 0


def cmd_merge() -> int:
    """Run attack check + merge and write results to .pyqual/attack_*.json."""
    from pyqual.plugins.attack.main import attack_check, attack_merge

    _ensure_dir()

    check = attack_check()
    (PYQUAL_DIR / "attack_check.json").write_text(json.dumps(check, indent=2))

    if not check.get("success"):
        print(f"Attack check failed: {check.get('error')}", file=sys.stderr)
        return 0  # non-fatal — pipeline continues

    conflicts = check.get("conflicts_detected", 0)
    behind = check.get("branches_behind", 0)
    print(f"Conflicts: {conflicts}, Behind: {behind}")

    if behind > 0 or conflicts > 0:
        merge = attack_merge(strategy="theirs", dry_run=False)
        (PYQUAL_DIR / "attack_merge.json").write_text(json.dumps(merge, indent=2))
        if merge.get("success"):
            resolved = merge.get("conflicts_resolved", 0)
            print(f"Merge OK — resolved {resolved} conflicts")
        else:
            print(f"Merge failed: {merge.get('error')}", file=sys.stderr)
    else:
        print("Already up to date — no merge needed")

    return 0


def main() -> int:
    """Dispatch subcommands: check | merge (default)."""
    subcmd = sys.argv[1] if len(sys.argv) > 1 else "merge"
    if subcmd == "check":
        return cmd_check()
    if subcmd == "merge":
        return cmd_merge()
    print(f"Unknown subcommand: {subcmd!r}. Use 'check' or 'merge'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
