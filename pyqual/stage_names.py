"""Shared helpers for classifying pyqual stage names."""

from __future__ import annotations

from typing import Final


STAGE_WHEN_DEFAULTS: Final[dict[str, str]] = {
    "analyze": "first_iteration",
    "baseline": "first_iteration",
    "code2llm": "first_iteration",
    "prefact": "metrics_fail",
    "fix": "metrics_fail",
    "fix_regression": "metrics_fail",
    "auto_fix": "metrics_fail",
    "repair": "metrics_fail",
    "verify": "after_fix",
    "verify_fix": "after_fix",
    "regression_report": "after_verify_fix",
    "report": "metrics_pass",
    "push": "metrics_pass",
    "publish": "metrics_pass",
    "deploy": "metrics_pass",
}

DELIVERY_STAGE_NAMES: Final[frozenset[str]] = frozenset({"push", "publish", "deploy"})


def normalize_stage_name(name: str) -> str:
    """Return a lower-cased, trimmed stage name."""
    return name.lower().strip()


def is_fix_stage_name(name: str) -> bool:
    """Return True for fix-like stage names, excluding verification stages."""
    lower = normalize_stage_name(name)
    if lower.startswith("verify"):
        return False
    return (
        lower == "fix"
        or lower.startswith("fix_")
        or lower.startswith("fix-")
        or lower.startswith("auto_fix")
        or lower.startswith("repair")
        or "_repair" in lower
    )


def is_verify_stage_name(name: str) -> bool:
    """Return True for stage names that belong to verification steps."""
    return "verify" in normalize_stage_name(name)


def is_delivery_stage_name(name: str) -> bool:
    """Return True for delivery-style stage names."""
    return normalize_stage_name(name) in DELIVERY_STAGE_NAMES


def get_stage_when_default(name: str) -> str:
    """Return the default when: value inferred from a stage name."""
    return STAGE_WHEN_DEFAULTS.get(normalize_stage_name(name), "always")
