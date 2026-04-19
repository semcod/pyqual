"""Tests for pyqual/validation.py — pre-flight config validation and error taxonomy."""

from __future__ import annotations

from pathlib import Path


from pyqual.validation import (
    EC,
    ErrorDomain,
    Severity,
    StageFailure,
    ValidationResult,
    detect_project_facts,
    error_domain,
    validate_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "pyqual.yaml"
    p.write_text(content)
    return p


MINIMAL_VALID = """\
pipeline:
  name: test
  stages:
    - name: lint
      run: echo ok
  metrics:
    coverage_min: 80
"""

VALID_NO_METRICS = """\
pipeline:
  name: test
  stages:
    - name: lint
      run: echo ok
"""


# ---------------------------------------------------------------------------
# EC namespace
# ---------------------------------------------------------------------------

class TestEC:
    def test_all_config_codes_start_with_prefix(self) -> None:
        config_codes = [v for k, v in vars(EC).items()
                        if not k.startswith("_") and k.startswith("CONFIG")]
        assert all(c.startswith("E_PYQUAL_CONFIG_") for c in config_codes)

    def test_all_env_codes_start_with_prefix(self) -> None:
        env_codes = [v for k, v in vars(EC).items()
                     if not k.startswith("_") and k.startswith("ENV")]
        assert all(c.startswith("E_PYQUAL_ENV_") for c in env_codes)

    def test_all_project_codes_start_with_prefix(self) -> None:
        proj_codes = [v for k, v in vars(EC).items()
                      if not k.startswith("_") and k.startswith("PROJECT")]
        assert all(c.startswith("E_PYQUAL_PROJECT_") for c in proj_codes)

    def test_all_lllm_codes_start_with_prefix(self) -> None:
        llm_codes = [v for k, v in vars(EC).items()
                     if not k.startswith("_") and k.startswith("LLM")]
        assert all(c.startswith("E_PYQUAL_LLM_") for c in llm_codes)


# ---------------------------------------------------------------------------
# error_domain()
# ---------------------------------------------------------------------------

class TestErrorDomain:
    def test_config_domain(self) -> None:
        assert error_domain(EC.CONFIG_NOT_FOUND) == ErrorDomain.CONFIG

    def test_env_domain(self) -> None:
        assert error_domain(EC.ENV_TOOL_MISSING) == ErrorDomain.ENV

    def test_project_domain(self) -> None:
        assert error_domain(EC.PROJECT_TEST_FAILURE) == ErrorDomain.PROJECT

    def test_pipeline_domain(self) -> None:
        assert error_domain(EC.PIPELINE_TIMEOUT) == ErrorDomain.PIPELINE

    def test_llm_domain(self) -> None:
        assert error_domain(EC.LLM_API_KEY_MISSING) == ErrorDomain.LLM

    def test_unknown_code_returns_none(self) -> None:
        assert error_domain("E_PYQUAL_GARBAGE_CODE") is None

    def test_non_pyqual_code_returns_none(self) -> None:
        assert error_domain("SOME_OTHER_ERROR") is None


# ---------------------------------------------------------------------------
# StageFailure classifier
# ---------------------------------------------------------------------------

class TestStageFailure:
    def _f(self, stderr="", stdout="", rc=1, is_fix=False, timed_out=False):
        return StageFailure(
            stage_name="test",
            returncode=rc,
            stderr=stderr,
            stdout=stdout,
            duration=1.0,
            is_fix_stage=is_fix,
            timed_out=timed_out,
        )

    def test_timeout_classified(self) -> None:
        f = self._f(timed_out=True)
        assert f.error_code == EC.PIPELINE_TIMEOUT
        assert f.domain == ErrorDomain.PIPELINE

    def test_command_not_found(self) -> None:
        f = self._f(stderr="sh: ruff: command not found")
        assert f.domain == ErrorDomain.ENV

    def test_no_such_file(self) -> None:
        f = self._f(stderr="/usr/bin/xyz: No such file or directory")
        assert f.domain == ErrorDomain.ENV

    def test_api_key_missing(self) -> None:
        f = self._f(stderr="Missing OPENROUTER_API_KEY environment variable")
        assert f.error_code == EC.ENV_API_KEY_MISSING

    def test_module_not_found(self) -> None:
        f = self._f(stderr="ModuleNotFoundError: No module named 'vallm'")
        assert f.domain == ErrorDomain.ENV

    def test_pytest_failures(self) -> None:
        f = self._f(stderr="FAILED tests/test_foo.py::test_bar - AssertionError")
        assert f.error_code == EC.PROJECT_TEST_FAILURE

    def test_assertion_error(self) -> None:
        f = self._f(stdout="AssertionError: expected 1 got 2")
        assert f.domain == ErrorDomain.PROJECT

    def test_n_failed_pattern(self) -> None:
        f = self._f(stdout="3 failed, 12 passed in 1.4s")
        assert f.error_code == EC.PROJECT_TEST_FAILURE

    def test_ruff_lint_failure(self) -> None:
        f = self._f(stderr="ruff check: found 5 errors")
        assert f.domain == ErrorDomain.PROJECT

    def test_empty_output_unknown_tool(self) -> None:
        f = self._f(stderr="", stdout="", rc=127)
        assert f.error_code == EC.ENV_TOOL_MISSING

    def test_generic_project_error(self) -> None:
        f = self._f(stderr="SyntaxError: invalid syntax at line 42", rc=1)
        assert f.domain == ErrorDomain.PROJECT

    def test_fix_stage_api_key(self) -> None:
        f = self._f(stderr="Missing API key for openai", is_fix=True)
        assert f.error_code == EC.LLM_API_KEY_MISSING

    def test_fix_stage_generic(self) -> None:
        f = self._f(stderr="something went wrong in the fix", is_fix=True)
        assert f.error_code == EC.LLM_FIX_FAILED
        assert f.domain == ErrorDomain.LLM

    def test_domain_property_matches_code(self) -> None:
        f = self._f(stderr="pytest: 2 failed")
        assert f.domain == error_domain(f.error_code)


# ---------------------------------------------------------------------------
# validate_config()
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_missing_file(self, tmp_path: Path) -> None:
        result = validate_config(tmp_path / "pyqual.yaml")
        assert not result.ok
        assert any(i.code == EC.CONFIG_NOT_FOUND for i in result.errors)

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "pyqual.yaml"
        p.write_text("{ broken yaml: [")
        result = validate_config(p)
        assert not result.ok
        assert any(i.code == EC.CONFIG_YAML_PARSE for i in result.errors)

    def test_empty_yaml(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, "null\n")
        result = validate_config(p)
        assert not result.ok
        assert any(i.code == EC.CONFIG_YAML_EMPTY for i in result.errors)

    def test_valid_minimal_passes(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, MINIMAL_VALID)
        result = validate_config(p)
        assert result.ok, [i.message for i in result.errors]

    def test_stages_counted(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, MINIMAL_VALID)
        result = validate_config(p)
        assert result.stages_checked == 1

    def test_gates_counted(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, MINIMAL_VALID)
        result = validate_config(p)
        assert result.gates_checked == 1

    def test_stage_no_command(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages:
    - name: broken
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_STAGE_NO_CMD for i in result.errors)

    def test_stage_both_commands(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages:
    - name: oops
      run: echo hi
      tool: pytest
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_STAGE_BOTH_CMDS for i in result.errors)

    def test_unknown_tool_preset(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages:
    - name: s
      tool: this_tool_does_not_exist_xyz
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_UNKNOWN_PRESET for i in result.errors)

    def test_unknown_metric_is_warning(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
  metrics:
    totally_made_up_metric_min: 50
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert result.ok  # warnings don't fail
        assert any(i.code == EC.ENV_UNKNOWN_METRIC for i in result.warnings)

    def test_bad_threshold_type(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
  metrics:
    coverage_min: "not_a_number"
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_BAD_THRESHOLD for i in result.errors)

    def test_bad_max_iterations(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
  loop:
    max_iterations: -1
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_BAD_ITERATIONS for i in result.errors)

    def test_unknown_on_fail_is_warning(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
  loop:
    on_fail: explode
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.CONFIG_UNKNOWN_ON_FAIL for i in result.warnings)

    def test_no_stages_is_warning(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        assert any(i.code == EC.ENV_NO_STAGES for i in result.warnings)

    def test_no_metrics_is_info(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, VALID_NO_METRICS)
        result = validate_config(p)
        assert result.ok
        assert any(i.code == EC.ENV_NO_GATES for i in result.issues
                   if i.severity == Severity.INFO)

    def test_known_metrics_pass(self, tmp_path: Path) -> None:
        yaml = """\
pipeline:
  name: t
  stages: []
  metrics:
    coverage_min: 80
    cc_max: 15
    mypy_errors_max: 0
    ruff_errors_max: 0
    secrets_found_max: 0
    secrets_severity_max: 0
"""
        p = _make_config(tmp_path, yaml)
        result = validate_config(p)
        # Only INFO-level (no_gates gone since we have metrics) — no warnings
        warnings = [i for i in result.warnings if i.code == EC.ENV_UNKNOWN_METRIC]
        assert warnings == []

    def test_suggestion_present_on_error(self, tmp_path: Path) -> None:
        p = _make_config(tmp_path, "null\n")
        result = validate_config(p)
        for issue in result.errors:
            assert issue.suggestion  # every error should have a suggestion


# ---------------------------------------------------------------------------
# ValidationResult helpers
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_ok_with_no_issues(self) -> None:
        r = ValidationResult()
        assert r.ok

    def test_not_ok_with_error(self) -> None:
        r = ValidationResult()
        r.add(Severity.ERROR, EC.CONFIG_NOT_FOUND, "missing")
        assert not r.ok

    def test_ok_with_only_warning(self) -> None:
        r = ValidationResult()
        r.add(Severity.WARNING, EC.ENV_NO_STAGES, "no stages")
        assert r.ok

    def test_errors_and_warnings_separated(self) -> None:
        r = ValidationResult()
        r.add(Severity.ERROR, EC.CONFIG_NOT_FOUND, "e")
        r.add(Severity.WARNING, EC.ENV_NO_STAGES, "w")
        assert len(r.errors) == 1
        assert len(r.warnings) == 1


# ---------------------------------------------------------------------------
# detect_project_facts()
# ---------------------------------------------------------------------------

class TestDetectProjectFacts:
    def test_returns_dict_with_workdir(self, tmp_path: Path) -> None:
        facts = detect_project_facts(tmp_path)
        assert "workdir" in facts
        assert facts["workdir"] == str(tmp_path)

    def test_python_project_detected(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[build-system]\n")
        facts = detect_project_facts(tmp_path)
        assert facts.get("lang") == "python"

    def test_nodejs_project_detected(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        facts = detect_project_facts(tmp_path)
        assert facts.get("lang") == "nodejs"

    def test_unknown_lang_default(self, tmp_path: Path) -> None:
        facts = detect_project_facts(tmp_path)
        assert facts.get("lang") == "unknown"

    def test_available_tools_is_list(self, tmp_path: Path) -> None:
        facts = detect_project_facts(tmp_path)
        assert isinstance(facts["available_tools"], list)

    def test_current_config_included_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "pyqual.yaml").write_text("pipeline:\n  name: t\n")
        facts = detect_project_facts(tmp_path)
        assert "current_config" in facts
        assert "pipeline" in facts["current_config"]

    def test_has_tests_detected(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        facts = detect_project_facts(tmp_path)
        assert facts.get("has_tests") is True

    def test_nonexistent_dir_returns_facts(self) -> None:
        facts = detect_project_facts(Path("/tmp/pyqual_nonexistent_xyz"))
        assert "workdir" in facts
        assert isinstance(facts["available_tools"], list)  # PATH-based, not dir-based
        assert facts.get("lang") == "unknown"  # no files to detect
