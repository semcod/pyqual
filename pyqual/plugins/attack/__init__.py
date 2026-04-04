"""Attack plugin for pyqual.

This package provides aggressive merge automation and conflict resolution.
"""

from __future__ import annotations

from pyqual.plugins.attack.main import (
    AttackCollector,
    MERGE_STRATEGIES,
    attack_check,
    attack_merge,
    auto_merge_pr,
)

__all__ = [
    "AttackCollector",
    "MERGE_STRATEGIES",
    "attack_check",
    "attack_merge",
    "auto_merge_pr",
]
