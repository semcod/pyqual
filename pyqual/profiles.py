"""Built-in pipeline profiles for pyqual.yaml simplification.

Instead of manually listing every stage, gate, and timeout, users can write:

    pipeline:
      profile: python
      metrics:
        coverage_min: 55    # override only what you need

Profiles provide sensible stage lists with smart ``when:`` defaults already
assigned by stage name in ``config._STAGE_WHEN_DEFAULTS``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyqual.constants import DEFAULT_CC_MAX, DEFAULT_COVERAGE_MIN, DEFAULT_VALLM_PASS_MIN


@dataclass(frozen=True)
class PipelineProfile:
    """A reusable pipeline template with default stages and metrics."""
    description: str
    stages: list[dict[str, Any]]
    metrics: dict[str, float] = field(default_factory=dict)
    loop: dict[str, Any] = field(default_factory=dict)
    env: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

PROFILES: dict[str, PipelineProfile] = {
    "python": PipelineProfile(
        description="Standard Python quality loop: analyze → validate → test → fix → verify",
        stages=[
            {"name": "analyze", "tool": "code2llm"},
            {"name": "validate", "tool": "vallm"},
            {"name": "test", "tool": "pytest", "optional": True},
            {"name": "prefact", "tool": "prefact", "optional": True, "timeout": 900},
            {"name": "fix", "tool": "llx-fix", "optional": True, "timeout": 1800},
            {"name": "verify", "tool": "vallm", "optional": True},
        ],
        metrics={
            "cc_max": DEFAULT_CC_MAX,
            "vallm_pass_min": DEFAULT_VALLM_PASS_MIN,
            "coverage_min": DEFAULT_COVERAGE_MIN,
        },
    ),

    "python-full": PipelineProfile(
        description="Full Python pipeline: analyze → validate → test → fix → verify → push → publish",
        stages=[
            {"name": "analyze", "tool": "code2llm"},
            {"name": "validate", "tool": "vallm"},
            {"name": "test", "tool": "pytest", "optional": True},
            {"name": "prefact", "tool": "prefact", "optional": True, "timeout": 900},
            {"name": "fix", "tool": "llx-fix", "optional": True, "timeout": 1800},
            {"name": "verify", "tool": "vallm", "optional": True},
            {"name": "push", "run": "goal push --bump patch --no-publish --todo --model ${LLM_MODEL}", "optional": True, "timeout": 120},
            {"name": "publish", "run": "goal publish", "optional": True, "timeout": 300},
        ],
        metrics={
            "cc_max": DEFAULT_CC_MAX,
            "vallm_pass_min": DEFAULT_VALLM_PASS_MIN,
            "coverage_min": DEFAULT_COVERAGE_MIN,
        },
    ),

    "lint-only": PipelineProfile(
        description="Lint-only pipeline: ruff → mypy (no LLM, no fix)",
        stages=[
            {"name": "lint", "tool": "ruff", "optional": True},
            {"name": "typecheck", "tool": "mypy", "optional": True},
            {"name": "test", "tool": "pytest", "optional": True},
        ],
        metrics={
            "cc_max": DEFAULT_CC_MAX,
            "coverage_min": DEFAULT_COVERAGE_MIN,
        },
        loop={"max_iterations": 1},
    ),

    "ci": PipelineProfile(
        description="CI pipeline: analyze → validate → test (no fix, report-only)",
        stages=[
            {"name": "analyze", "tool": "code2llm"},
            {"name": "validate", "tool": "vallm"},
            {"name": "test", "tool": "pytest", "optional": True},
        ],
        metrics={
            "cc_max": DEFAULT_CC_MAX,
            "vallm_pass_min": DEFAULT_VALLM_PASS_MIN,
            "coverage_min": DEFAULT_COVERAGE_MIN,
        },
        loop={"max_iterations": 1, "on_fail": "report"},
    ),

    "security": PipelineProfile(
        description="Security-focused: analyze → audit → bandit → test",
        stages=[
            {"name": "analyze", "tool": "code2llm"},
            {"name": "audit", "tool": "pip-audit", "optional": True},
            {"name": "bandit", "tool": "bandit", "optional": True},
            {"name": "test", "tool": "pytest", "optional": True},
        ],
        metrics={
            "cc_max": DEFAULT_CC_MAX,
            "coverage_min": DEFAULT_COVERAGE_MIN,
        },
        loop={"max_iterations": 1},
    ),
}


def get_profile(name: str) -> PipelineProfile | None:
    """Return a profile by name, or None if not found."""
    return PROFILES.get(name)


def list_profiles() -> list[str]:
    """Return sorted list of available profile names."""
    return sorted(PROFILES.keys())
