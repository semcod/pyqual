"""Validation schema: data structures and known metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from pyqual.validation.errors import Severity


# ---------------------------------------------------------------------------
# Known metric names produced by built-in collectors
# ---------------------------------------------------------------------------

KNOWN_METRICS: Final[frozenset[str]] = frozenset({
    "cc", "critical",
    "vallm_pass", "error_count",
    "coverage",
    "completion_rate",
    "bandit_high", "bandit_medium", "bandit_low",
    "secrets_severity", "secrets_count", "secrets_found",
    "vuln_critical", "vuln_count",
    "sbom_compliance", "license_blacklist",
    "unused_count",
    "pyroma_score",
    "git_branch_age", "todo_count",
    "llm_pass_rate", "llm_cc", "hallucination_rate", "prompt_bias_score", "agent_efficiency",
    "ai_cost",
    "bench_regression", "bench_time",
    "mem_usage", "cpu_time",
    "mypy_errors",
    "ruff_errors", "ruff_fatal", "ruff_warnings",
    "pylint_errors", "pylint_fatal", "pylint_error", "pylint_warnings", "pylint_score",
    "flake8_violations", "flake8_errors", "flake8_warnings", "flake8_conventions",
    "docstring_coverage", "docstring_total", "docstring_missing",
})

# Metric suffix → operator mapping (from GateConfig.from_dict)
_GATE_SUFFIX_OPS: Final[dict[str, str]] = {
    "max": "le", "min": "ge", "eq": "eq", "lt": "lt", "gt": "gt"
}


def _resolve_gate_metric(gate_key: str) -> str:
    """Strip _max/_min/_eq suffix to get the base metric name."""
    for suffix in _GATE_SUFFIX_OPS:
        if gate_key.endswith(f"_{suffix}"):
            return gate_key[: -len(suffix) - 1]
    return gate_key


# ---------------------------------------------------------------------------
# Validation data structures
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """Single validation finding."""
    severity: Severity
    code: str            # e.g. "TOOL_MISSING", "UNKNOWN_METRIC"
    message: str
    stage: str = ""      # which stage (if applicable)
    suggestion: str = "" # how to fix it


@dataclass
class ValidationResult:
    """Aggregated result of validating one pyqual.yaml."""
    issues: list[ValidationIssue] = field(default_factory=list)
    config_name: str = ""
    stages_checked: int = 0
    gates_checked: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add(self, severity: Severity, code: str, message: str,
            stage: str = "", suggestion: str = "") -> None:
        self.issues.append(ValidationIssue(
            severity=severity, code=code, message=message,
            stage=stage, suggestion=suggestion,
        ))
