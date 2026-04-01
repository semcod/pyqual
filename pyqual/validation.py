"""Pre-flight validation and runtime error categorization for pyqual.

Validates config files before running the pipeline, detecting:
- YAML parse errors
- Unknown tool presets
- Tool binaries missing from PATH
- Gate metric names that no collector can produce
- Stage configuration mistakes

Standardized error codes
------------------------
All codes use the format  ``E_PYQUAL_<DOMAIN>_<SPECIFIC>``:

  E_PYQUAL_CONFIG_*   — pyqual.yaml is wrong (bad YAML, unknown preset, …)
  E_PYQUAL_ENV_*      — environment problem (binary missing, API key absent, …)
  E_PYQUAL_PROJECT_*  — project code issue (test failure, lint error, …)
  E_PYQUAL_PIPELINE_* — pipeline execution problem (timeout, I/O error, …)
  E_PYQUAL_LLM_*      — LLM / fix-stage problem (API key, network, model, …)

The domain is the first component after ``E_PYQUAL_``.  Use it to decide
whether to auto-fix the config (CONFIG/ENV) or let the fix-stage handle it
(PROJECT) or surface it to the user (PIPELINE/LLM).
"""

import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pyqual.constants import CONFIG_READ_MAX_CHARS


# ---------------------------------------------------------------------------
# Standardised error taxonomy
# ---------------------------------------------------------------------------

class ErrorDomain(str, Enum):
    CONFIG   = "CONFIG"    # pyqual.yaml is wrong
    ENV      = "ENV"       # missing binary / API key / network
    PROJECT  = "PROJECT"   # project code issue (test / lint / gate failure)
    PIPELINE = "PIPELINE"  # subprocess timeout / I/O crash
    LLM      = "LLM"       # LLM / fix-stage problem


# Full error codes  (domain_name : specific_name)
class EC:
    """Namespace for standardised error-code string constants."""
    # CONFIG
    CONFIG_NOT_FOUND        = "E_PYQUAL_CONFIG_NOT_FOUND"
    CONFIG_YAML_PARSE       = "E_PYQUAL_CONFIG_YAML_PARSE"
    CONFIG_YAML_EMPTY       = "E_PYQUAL_CONFIG_YAML_EMPTY"
    CONFIG_STAGE_NO_CMD     = "E_PYQUAL_CONFIG_STAGE_NO_CMD"
    CONFIG_STAGE_BOTH_CMDS  = "E_PYQUAL_CONFIG_STAGE_BOTH_CMDS"
    CONFIG_UNKNOWN_PRESET   = "E_PYQUAL_CONFIG_UNKNOWN_PRESET"
    CONFIG_BAD_ITERATIONS   = "E_PYQUAL_CONFIG_BAD_ITERATIONS"
    CONFIG_BAD_THRESHOLD    = "E_PYQUAL_CONFIG_BAD_THRESHOLD"
    CONFIG_UNKNOWN_ON_FAIL  = "E_PYQUAL_CONFIG_UNKNOWN_ON_FAIL"
    CONFIG_REGISTRY_ERROR   = "E_PYQUAL_CONFIG_REGISTRY_ERROR"
    # ENV
    ENV_TOOL_MISSING        = "E_PYQUAL_ENV_TOOL_MISSING"
    ENV_TOOL_MISSING_OPT    = "E_PYQUAL_ENV_TOOL_MISSING_OPT"
    ENV_API_KEY_MISSING     = "E_PYQUAL_ENV_API_KEY_MISSING"
    ENV_UNKNOWN_METRIC      = "E_PYQUAL_ENV_UNKNOWN_METRIC"
    ENV_NO_STAGES           = "E_PYQUAL_ENV_NO_STAGES"
    ENV_NO_GATES            = "E_PYQUAL_ENV_NO_GATES"
    # PROJECT
    PROJECT_TEST_FAILURE    = "E_PYQUAL_PROJECT_TEST_FAILURE"
    PROJECT_LINT_FAILURE    = "E_PYQUAL_PROJECT_LINT_FAILURE"
    PROJECT_GATE_FAILURE    = "E_PYQUAL_PROJECT_GATE_FAILURE"
    PROJECT_BUILD_FAILURE   = "E_PYQUAL_PROJECT_BUILD_FAILURE"
    PROJECT_GENERIC         = "E_PYQUAL_PROJECT_GENERIC"
    # PIPELINE
    PIPELINE_TIMEOUT        = "E_PYQUAL_PIPELINE_TIMEOUT"
    PIPELINE_IO_ERROR       = "E_PYQUAL_PIPELINE_IO_ERROR"
    PIPELINE_CMD_NOT_FOUND  = "E_PYQUAL_PIPELINE_CMD_NOT_FOUND"
    PIPELINE_GENERIC        = "E_PYQUAL_PIPELINE_GENERIC"
    # LLM
    LLM_API_KEY_MISSING     = "E_PYQUAL_LLM_API_KEY_MISSING"
    LLM_NETWORK_ERROR       = "E_PYQUAL_LLM_NETWORK_ERROR"
    LLM_FIX_FAILED          = "E_PYQUAL_LLM_FIX_FAILED"
    LLM_GENERIC             = "E_PYQUAL_LLM_GENERIC"


def error_domain(code: str) -> ErrorDomain | None:
    """Return the domain of a standardised error code string."""
    for domain in ErrorDomain:
        if code.startswith(f"E_PYQUAL_{domain.value}_"):
            return domain
    return None


@dataclass
class StageFailure:
    """Runtime failure description from a completed stage."""
    stage_name: str
    returncode: int
    stderr: str
    stdout: str
    duration: float
    is_fix_stage: bool = False   # True when this IS the LLM fix stage
    timed_out: bool = False

    @property
    def error_code(self) -> str:
        """Classify failure into a standardised error code."""
        return _classify_failure(self)

    @property
    def domain(self) -> ErrorDomain | None:
        return error_domain(self.error_code)


# ---------------------------------------------------------------------------
# Runtime failure classifier
# ---------------------------------------------------------------------------

# Patterns that indicate environment / config problems (tool not installed, etc.)
_ENV_PATTERNS: list[re.Pattern] = [
    re.compile(r"command not found", re.I),
    re.compile(r"No such file or directory", re.I),
    re.compile(r"not found on PATH", re.I),
    re.compile(r"ModuleNotFoundError", re.I),
    re.compile(r"ImportError", re.I),
    re.compile(r"Permission denied", re.I),
    re.compile(r"OPENROUTER_API_KEY", re.I),
    re.compile(r"API key", re.I),
    re.compile(r"AuthenticationError", re.I),
]

_LLM_PATTERNS: list[re.Pattern] = [
    re.compile(r"openrouter", re.I),
    re.compile(r"litellm", re.I),
    re.compile(r"anthropic|openai|gemini", re.I),
    re.compile(r"rate.limit", re.I),
    re.compile(r"context.length", re.I),
    re.compile(r"llx.*error|error.*llx", re.I),
]

_TEST_PATTERNS: list[re.Pattern] = [
    re.compile(r"FAILED\s+tests/", re.I),
    re.compile(r"pytest.*failed", re.I),
    re.compile(r"\d+ failed", re.I),
    re.compile(r"AssertionError", re.I),
    re.compile(r"ERRORS?\s+collecting", re.I),
]

_LINT_PATTERNS: list[re.Pattern] = [
    re.compile(r"ruff.*error|error.*ruff", re.I),
    re.compile(r"pylint.*error|flake8.*error", re.I),
    re.compile(r"E\d{3,4}|W\d{3,4}|F\d{3,4}", re.I),
]


def _classify_failure(f: StageFailure) -> str:
    if f.timed_out:
        return EC.PIPELINE_TIMEOUT

    combined = f"{f.stderr}\n{f.stdout}".strip()

    # LLM fix stage failures are their own domain
    if f.is_fix_stage:
        for pat in _ENV_PATTERNS:
            if pat.search(combined):
                if "API" in combined.upper() or "KEY" in combined.upper():
                    return EC.LLM_API_KEY_MISSING
                if "network" in combined.lower() or "connect" in combined.lower():
                    return EC.LLM_NETWORK_ERROR
        return EC.LLM_FIX_FAILED

    # No output at all — binary likely missing
    if not combined and f.returncode != 0:
        return EC.ENV_TOOL_MISSING

    for pat in _ENV_PATTERNS:
        if pat.search(combined):
            if "API" in combined.upper() or "KEY" in combined.upper():
                return EC.ENV_API_KEY_MISSING
            return EC.ENV_TOOL_MISSING

    for pat in _LLM_PATTERNS:
        if pat.search(combined):
            return EC.LLM_GENERIC

    for pat in _TEST_PATTERNS:
        if pat.search(combined):
            return EC.PROJECT_TEST_FAILURE

    for pat in _LINT_PATTERNS:
        if pat.search(combined):
            return EC.PROJECT_LINT_FAILURE

    return EC.PROJECT_GENERIC


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
        result.add(Severity.ERROR, EC.CONFIG_NOT_FOUND,
                   f"pyqual.yaml not found: {config_path}",
                   suggestion="Run 'pyqual init' to create one.")
        return result

    # --- YAML parse ---
    try:
        import yaml
        raw = yaml.safe_load(config_path.read_text())
    except Exception as exc:
        result.add(Severity.ERROR, EC.CONFIG_YAML_PARSE,
                   f"YAML parse error: {exc}",
                   suggestion="Fix the YAML syntax in pyqual.yaml.")
        return result

    if not isinstance(raw, dict):
        result.add(Severity.ERROR, EC.CONFIG_YAML_EMPTY,
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
        result.add(Severity.ERROR, EC.CONFIG_REGISTRY_ERROR,
                   f"Failed to load tool registry: {exc}")
        return result

    # --- Stages ---
    stages_raw = pipeline.get("stages", [])
    if not stages_raw:
        result.add(Severity.WARNING, EC.ENV_NO_STAGES,
                   "No stages defined — pipeline will only check gates.",
                   suggestion="Add at least one stage with 'tool:' or 'run:'.")

    for s in stages_raw:
        result.stages_checked += 1
        name = s.get("name", f"stage#{result.stages_checked}")
        tool = s.get("tool", "")
        run = s.get("run", "")
        optional = s.get("optional", False)

        if not run and not tool:
            result.add(Severity.ERROR, EC.CONFIG_STAGE_NO_CMD,
                       f"Stage '{name}' has neither 'run' nor 'tool'.",
                       stage=name,
                       suggestion=f"Add 'run: <command>' or 'tool: <preset>' to stage '{name}'.")
            continue

        if run and tool:
            result.add(Severity.ERROR, EC.CONFIG_STAGE_BOTH_CMDS,
                       f"Stage '{name}' has both 'run' and 'tool' — use one only.",
                       stage=name,
                       suggestion=f"Remove either 'run' or 'tool' from stage '{name}'.")
            continue

        if tool:
            preset = get_preset(tool)
            if preset is None:
                top = ", ".join(list_presets()[:8])
                available = f"{top}…"
                result.add(Severity.ERROR, EC.CONFIG_UNKNOWN_PRESET,
                           f"Stage '{name}': unknown tool preset '{tool}'.",
                           stage=name,
                           suggestion=f"Available presets: {available}. Use 'run:' for custom commands.")
            elif not preset.is_available():
                sev = Severity.WARNING if optional else Severity.ERROR
                code = EC.ENV_TOOL_MISSING_OPT if optional else EC.ENV_TOOL_MISSING
                install_hint = f"Install '{preset.binary}' or add 'optional: true' to skip silently."
                result.add(sev, code,
                           f"Stage '{name}': tool '{tool}' binary '{preset.binary}' not found on PATH.",
                           stage=name,
                           suggestion=install_hint)

    # --- Metrics / gates ---
    metrics_raw = pipeline.get("metrics") or {}
    if not metrics_raw:
        result.add(Severity.INFO, EC.ENV_NO_GATES,
                   "No quality gates defined — pipeline will always pass after one iteration.",
                   suggestion="Add 'metrics:' with thresholds like 'coverage_min: 80'.")

    for gate_key, threshold in metrics_raw.items():
        result.gates_checked += 1
        base_metric = _resolve_gate_metric(gate_key)
        if base_metric not in KNOWN_METRICS:
            result.add(Severity.WARNING, EC.ENV_UNKNOWN_METRIC,
                       f"Gate '{gate_key}': metric '{base_metric}' is not produced by any built-in collector.",
                       suggestion=(
                           f"Known metrics: {', '.join(sorted(KNOWN_METRICS)[:10])}… "
                           "Custom metrics require a plugin or custom stage writing to .pyqual/."
                       ))
        try:
            float(threshold)
        except (TypeError, ValueError):
            result.add(Severity.ERROR, EC.CONFIG_BAD_THRESHOLD,
                       f"Gate '{gate_key}': threshold '{threshold}' is not a number.",
                       suggestion=f"Fix '{gate_key}:' to a numeric value, e.g. '{gate_key}: 80'.")

    # --- Loop config ---
    loop_raw = pipeline.get("loop", {})
    if loop_raw:
        max_iter = loop_raw.get("max_iterations", 3)
        on_fail = loop_raw.get("on_fail", "report")
        if not isinstance(max_iter, int) or max_iter < 1:
            result.add(Severity.ERROR, EC.CONFIG_BAD_ITERATIONS,
                       f"loop.max_iterations must be a positive integer, got: {max_iter!r}.",
                       suggestion="Set 'max_iterations: 3' (or any positive integer).")
        valid_on_fail = {"report", "create_ticket", "block"}
        if on_fail not in valid_on_fail:
            result.add(Severity.WARNING, EC.CONFIG_UNKNOWN_ON_FAIL,
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
        facts["current_config"] = config_path.read_text()[:CONFIG_READ_MAX_CHARS]

    return facts
