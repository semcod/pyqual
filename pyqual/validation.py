"""Pre-flight validation for pyqual.yaml configurations.

Validates config files before running the pipeline, detecting:
- YAML parse errors
- Unknown tool presets
- Tool binaries missing from PATH
- Gate metric names that no collector can produce
- Stage configuration mistakes

Use ``validate_config()`` to get structured issues, or ``check_and_report()``
for a human-readable console output.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    ERROR = "error"      # pipeline cannot start
    WARNING = "warning"  # pipeline may behave unexpectedly
    INFO = "info"        # suggestion


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


# ---------------------------------------------------------------------------
# Known metric names produced by built-in collectors
# ---------------------------------------------------------------------------

KNOWN_METRICS: frozenset[str] = frozenset({
    "cc", "critical",
    "vallm_pass", "error_count",
    "coverage",
    "bandit_high", "bandit_medium", "bandit_low",
    "secrets_severity", "secrets_count",
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
_GATE_SUFFIX_OPS = {"max": "le", "min": "ge", "eq": "eq", "lt": "lt", "gt": "gt"}


def _resolve_gate_metric(gate_key: str) -> str:
    """Strip _max/_min/_eq suffix to get the base metric name."""
    for suffix in _GATE_SUFFIX_OPS:
        if gate_key.endswith(f"_{suffix}"):
            return gate_key[: -len(suffix) - 1]
    return gate_key


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------

def validate_config(config_path: Path) -> ValidationResult:
    """Validate a pyqual.yaml file and return structured issues.

    Does NOT run any stages — this is a static pre-flight check.
    """
    result = ValidationResult()

    if not config_path.exists():
        result.add(Severity.ERROR, "CONFIG_NOT_FOUND",
                   f"pyqual.yaml not found: {config_path}",
                   suggestion="Run 'pyqual init' to create one.")
        return result

    # --- YAML parse ---
    try:
        import yaml
        raw = yaml.safe_load(config_path.read_text())
    except Exception as exc:
        result.add(Severity.ERROR, "YAML_PARSE_ERROR",
                   f"YAML parse error: {exc}",
                   suggestion="Fix the YAML syntax in pyqual.yaml.")
        return result

    if not isinstance(raw, dict):
        result.add(Severity.ERROR, "YAML_EMPTY",
                   "pyqual.yaml is empty or not a mapping.",
                   suggestion="Run 'pyqual init' to regenerate a valid config.")
        return result

    pipeline = raw.get("pipeline", raw)
    result.config_name = pipeline.get("name", "default")

    # --- Register tools so presets are available ---
    try:
        from pyqual.tools import (
            get_preset, list_presets,
            load_entry_point_presets, register_custom_tools_from_yaml,
        )
        load_entry_point_presets()
        custom_tools = pipeline.get("custom_tools", [])
        if custom_tools:
            register_custom_tools_from_yaml(custom_tools)
    except Exception as exc:
        result.add(Severity.ERROR, "TOOL_REGISTRY_ERROR",
                   f"Failed to load tool registry: {exc}")
        return result

    # --- Stages ---
    stages_raw = pipeline.get("stages", [])
    if not stages_raw:
        result.add(Severity.WARNING, "NO_STAGES",
                   "No stages defined — pipeline will only check gates.",
                   suggestion="Add at least one stage with 'tool:' or 'run:'.")

    for s in stages_raw:
        result.stages_checked += 1
        name = s.get("name", f"stage#{result.stages_checked}")
        tool = s.get("tool", "")
        run = s.get("run", "")
        optional = s.get("optional", False)

        if not run and not tool:
            result.add(Severity.ERROR, "STAGE_NO_COMMAND",
                       f"Stage '{name}' has neither 'run' nor 'tool'.",
                       stage=name,
                       suggestion=f"Add 'run: <command>' or 'tool: <preset>' to stage '{name}'.")
            continue

        if run and tool:
            result.add(Severity.ERROR, "STAGE_BOTH_COMMANDS",
                       f"Stage '{name}' has both 'run' and 'tool' — use one only.",
                       stage=name,
                       suggestion=f"Remove either 'run' or 'tool' from stage '{name}'.")
            continue

        if tool:
            preset = get_preset(tool)
            if preset is None:
                available = ", ".join(list_presets()[:8]) + "…"
                result.add(Severity.ERROR, "UNKNOWN_TOOL_PRESET",
                           f"Stage '{name}': unknown tool preset '{tool}'.",
                           stage=name,
                           suggestion=f"Available presets: {available}. Use 'run:' for custom commands.")
            elif not preset.is_available():
                sev = Severity.WARNING if optional else Severity.ERROR
                code = "TOOL_MISSING_OPTIONAL" if optional else "TOOL_MISSING"
                install_hint = f"Install '{preset.binary}' or add 'optional: true' to skip silently."
                result.add(sev, code,
                           f"Stage '{name}': tool '{tool}' binary '{preset.binary}' not found on PATH.",
                           stage=name,
                           suggestion=install_hint)

    # --- Metrics / gates ---
    metrics_raw = pipeline.get("metrics") or {}
    if not metrics_raw:
        result.add(Severity.INFO, "NO_GATES",
                   "No quality gates defined — pipeline will always pass after one iteration.",
                   suggestion="Add 'metrics:' with thresholds like 'coverage_min: 80'.")

    for gate_key, threshold in metrics_raw.items():
        result.gates_checked += 1
        base_metric = _resolve_gate_metric(gate_key)
        if base_metric not in KNOWN_METRICS:
            result.add(Severity.WARNING, "UNKNOWN_METRIC",
                       f"Gate '{gate_key}': metric '{base_metric}' is not produced by any built-in collector.",
                       suggestion=(
                           f"Known metrics: {', '.join(sorted(KNOWN_METRICS)[:10])}… "
                           "Custom metrics require a plugin or custom stage writing to .pyqual/."
                       ))
        try:
            float(threshold)
        except (TypeError, ValueError):
            result.add(Severity.ERROR, "GATE_BAD_THRESHOLD",
                       f"Gate '{gate_key}': threshold '{threshold}' is not a number.",
                       suggestion=f"Fix '{gate_key}:' to a numeric value, e.g. '{gate_key}: 80'.")

    # --- Loop config ---
    loop_raw = pipeline.get("loop", {})
    if loop_raw:
        max_iter = loop_raw.get("max_iterations", 3)
        on_fail = loop_raw.get("on_fail", "report")
        if not isinstance(max_iter, int) or max_iter < 1:
            result.add(Severity.ERROR, "BAD_MAX_ITERATIONS",
                       f"loop.max_iterations must be a positive integer, got: {max_iter!r}.",
                       suggestion="Set 'max_iterations: 3' (or any positive integer).")
        valid_on_fail = {"report", "create_ticket", "block"}
        if on_fail not in valid_on_fail:
            result.add(Severity.WARNING, "UNKNOWN_ON_FAIL",
                       f"loop.on_fail '{on_fail}' is not a known value.",
                       suggestion=f"Use one of: {', '.join(sorted(valid_on_fail))}.")

    return result


# ---------------------------------------------------------------------------
# Project-type heuristics (for fix-config / LLM context)
# ---------------------------------------------------------------------------

def detect_project_facts(workdir: Path) -> dict[str, Any]:
    """Scan project directory and return facts for LLM-based config repair."""
    facts: dict[str, Any] = {"workdir": str(workdir)}

    files = list(workdir.iterdir()) if workdir.exists() else []
    file_names = {f.name for f in files}

    # Language / framework
    if "pyproject.toml" in file_names or "setup.py" in file_names or "setup.cfg" in file_names:
        facts["lang"] = "python"
    elif "package.json" in file_names:
        facts["lang"] = "nodejs"
    elif "Cargo.toml" in file_names:
        facts["lang"] = "rust"
    elif "go.mod" in file_names:
        facts["lang"] = "go"
    elif "pom.xml" in file_names or "build.gradle" in file_names:
        facts["lang"] = "java"
    else:
        facts["lang"] = "unknown"

    # Available tools on PATH
    available_tools = []
    for tool in ["pytest", "ruff", "mypy", "code2llm", "vallm", "prefact",
                 "bandit", "pip-audit", "trufflehog", "coverage"]:
        if shutil.which(tool):
            available_tools.append(tool)
    facts["available_tools"] = available_tools

    # Test framework hints
    has_tests = any(f.name.startswith("test_") or f.name == "tests"
                    for f in files)
    facts["has_tests"] = has_tests

    # Existing pyqual.yaml
    config_path = workdir / "pyqual.yaml"
    if config_path.exists():
        facts["current_config"] = config_path.read_text()[:2000]

    return facts
