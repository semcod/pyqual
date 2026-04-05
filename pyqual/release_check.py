"""CLI wrapper for release-state validation.

Usage (via tool preset):
    python3 -m pyqual.release_check [--workdir PATH] [--registry pypi] [--bump-patch]

Exit codes:
    0 - release check passed (clean git, unique version, etc.)
    1 - release check found blocking issues
    2 - unexpected error during validation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn


def _print_result(result: "ValidationResult", verbose: bool = False) -> None:
    """Print human-readable validation results."""
    from pyqual.validation import EC, Severity

    errors = [i for i in result.issues if i.severity == Severity.ERROR]
    warnings = [i for i in result.issues if i.severity == Severity.WARNING]
    infos = [i for i in result.issues if i.severity == Severity.INFO]

    if not result.issues:
        print("✅ Release check passed")
        return

    for e in errors:
        print(f"❌ [{e.code}] {e.message}")
        if e.suggestion:
            print(f"   💡 {e.suggestion}")

    for w in warnings:
        print(f"⚠️  [{w.code}] {w.message}")
        if w.suggestion:
            print(f"   💡 {w.suggestion}")

    for i in infos:
        print(f"ℹ️  [{i.code}] {i.message}")

    if verbose:
        print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s)")


def main(args: list[str] | None = None) -> NoReturn:
    """Run release check from CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="python3 -m pyqual.release_check",
        description="Validate release state before publishing (git clean, version unique on PyPI).",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("."),
        help="Project directory to inspect (default: current directory)",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default="pypi",
        help="Registry name to check against (default: pypi)",
    )
    parser.add_argument(
        "--no-bump-patch",
        dest="bump_patch",
        action="store_false",
        default=True,
        help="Validate current version instead of the post-bump version",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose output",
    )
    parsed = parser.parse_args(args)

    try:
        from pyqual.validation import validate_release_state, ValidationResult

        result = validate_release_state(
            workdir=Path(parsed.workdir).resolve(),
            registry=parsed.registry,
            bump_patch=parsed.bump_patch,
        )

        _print_result(result, verbose=parsed.verbose)

        has_errors = any(i.severity.value == "error" for i in result.issues)
        sys.exit(1 if has_errors else 0)

    except Exception as exc:
        print(f"💥 Release check crashed: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
