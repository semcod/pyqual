"""Config validation: YAML parsing and stage/gate validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyqual.constants import CONFIG_READ_MAX_CHARS
from pyqual.validation.errors import EC, Severity
from pyqual.validation.schema import (
    KNOWN_METRICS,
    ValidationResult,
    _resolve_gate_metric,
)
from pyqual.yaml_fixer import (
    YamlErrorType,
    analyze_yaml_syntax,
)


# Severity lookup for YAML error types
_ERROR_SEVERITY_MAP = {
    YamlErrorType.UNCLOSED_QUOTE: Severity.ERROR,
    YamlErrorType.UNCLOSED_BRACKET: Severity.ERROR,
    YamlErrorType.TAB_CHARACTER: Severity.INFO,
    YamlErrorType.TRAILING_SPACE: Severity.INFO,
    YamlErrorType.INDENTATION: Severity.INFO,
}


def _get_issue_severity(issue: Any, try_fix: bool) -> tuple[Severity, str]:
    """Determine severity and suggestion for a YAML issue."""
    # Check explicit mapping first
    if issue.error_type in _ERROR_SEVERITY_MAP:
        sev = _ERROR_SEVERITY_MAP[issue.error_type]
        if issue.can_fix and try_fix:
            return Severity.WARNING, f"Auto-fixed: {issue.error_type.value}"
        if sev == Severity.ERROR:
            return sev, issue.fixed if issue.can_fix else f"Fix at line {issue.line}, col {issue.column}"
        return sev, f"Style: {issue.error_type.value} at line {issue.line}"

    # Default handling
    if issue.can_fix and try_fix:
        return Severity.WARNING, f"Auto-fixed: {issue.error_type.value}"
    if issue.can_fix:
        return Severity.INFO, f"Style: {issue.error_type.value} at line {issue.line}"
    return Severity.ERROR, f"Fix at line {issue.line}, col {issue.column}"


def _load_yaml_config(
    config_path: Path,
    result: ValidationResult,
    try_fix: bool = False,
) -> dict[str, Any] | None:
    """Load and parse YAML config file. Returns None on error (already added to result).

    Args:
        config_path: Path to YAML file
        result: ValidationResult to populate with issues
        try_fix: If True, attempt to auto-fix syntax errors
    """
    if not config_path.exists():
        result.add(Severity.ERROR, EC.CONFIG_NOT_FOUND,
                   f"pyqual.yaml not found: {config_path}",
                   suggestion="Run 'pyqual init' to create one.")
        return None

    content = config_path.read_text()

    # Run detailed syntax analysis
    syntax_result = analyze_yaml_syntax(content)

    # Report syntax issues
    for issue in syntax_result.issues:
        severity, suggestion = _get_issue_severity(issue, try_fix)
        result.add(severity, EC.CONFIG_YAML_PARSE, issue.message, suggestion=suggestion)

    # If trying to fix, use fixed content
    if try_fix and syntax_result.was_fixed:
        content = syntax_result.fixed_content
        backup = config_path.with_suffix(".yaml.bak")
        config_path.rename(backup)
        config_path.write_text(content)

    # Try to parse with PyYAML
    try:
        import yaml
        raw = yaml.safe_load(content)
    except Exception as exc:
        result.add(Severity.ERROR, EC.CONFIG_YAML_PARSE,
                   f"YAML parse error: {exc}",
                   suggestion="Fix the YAML syntax in pyqual.yaml or run 'pyqual validate --fix' to auto-repair.")
        return None

    if not isinstance(raw, dict):
        result.add(Severity.ERROR, EC.CONFIG_YAML_EMPTY,
                   "pyqual.yaml is empty or not a mapping.",
                   suggestion="Run 'pyqual init' to regenerate a valid config.")
        return None

    return raw


def _load_tool_registry(pipeline: dict[str, Any], result: ValidationResult) -> tuple[bool, Any, Any]:
    """Load tool registry and return (success, get_preset, list_presets)."""
    try:
        from pyqual.tools import (
            get_preset, list_presets,
            load_entry_point_presets, register_custom_tools_from_yaml,
        )
        load_entry_point_presets()
        custom_tools = pipeline.get("custom_tools", [])
        if custom_tools:
            register_custom_tools_from_yaml(custom_tools)
        return True, get_preset, list_presets
    except Exception as exc:
        result.add(Severity.ERROR, EC.CONFIG_REGISTRY_ERROR,
                   f"Failed to load tool registry: {exc}")
        return False, None, None


def _validate_stage(
    s: dict[str, Any],
    result: ValidationResult,
    get_preset: Any,
    list_presets: Any,
) -> None:
    """Validate a single stage configuration."""
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
        return

    if run and tool:
        result.add(Severity.ERROR, EC.CONFIG_STAGE_BOTH_CMDS,
                   f"Stage '{name}' has both 'run' and 'tool' — use one only.",
                   stage=name,
                   suggestion=f"Remove either 'run' or 'tool' from stage '{name}'.")
        return

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


def _validate_gate(
    gate_key: str,
    threshold: Any,
    result: ValidationResult,
) -> None:
    """Validate a single gate/metric configuration."""
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


def _validate_loop_config(loop_raw: dict[str, Any], result: ValidationResult) -> None:
    """Validate loop configuration."""
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


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------

def validate_config(config_path: Path, try_fix: bool = False) -> ValidationResult:
    """Validate a pyqual.yaml file and return structured issues.

    Does NOT run any stages — this is a static pre-flight check.

    Args:
        config_path: Path to the config file
        try_fix: If True, attempt to auto-fix syntax errors
    """
    result = ValidationResult()

    # --- YAML parse ---
    raw = _load_yaml_config(config_path, result, try_fix=try_fix)
    if raw is None:
        return result

    pipeline = raw.get("pipeline", raw)
    result.config_name = pipeline.get("name", "default")

    # --- Register tools so presets are available ---
    success, get_preset, list_presets = _load_tool_registry(pipeline, result)
    if not success:
        return result

    # --- Stages ---
    stages_raw = pipeline.get("stages", [])
    if not stages_raw:
        result.add(Severity.WARNING, EC.ENV_NO_STAGES,
                   "No stages defined — pipeline will only check gates.",
                   suggestion="Add at least one stage with 'tool:' or 'run:'.")

    for s in stages_raw:
        _validate_stage(s, result, get_preset, list_presets)

    # --- Metrics / gates ---
    metrics_raw = pipeline.get("metrics") or {}
    if not metrics_raw:
        result.add(Severity.INFO, EC.ENV_NO_GATES,
                   "No quality gates defined — pipeline will always pass after one iteration.",
                   suggestion="Add 'metrics:' with thresholds like 'coverage_min: 80'.")

    for gate_key, threshold in metrics_raw.items():
        _validate_gate(gate_key, threshold, result)

    # --- Loop config ---
    loop_raw = pipeline.get("loop", {})
    if loop_raw:
        _validate_loop_config(loop_raw, result)

    return result
