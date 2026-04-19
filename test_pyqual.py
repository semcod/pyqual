"""Tests for pyqual — config, gates, pipeline."""

import json
import tempfile
from pathlib import Path

import yaml

from pyqual.config import PyqualConfig, GateConfig
from pyqual.gates import Gate, GateSet
from pyqual.pipeline import Pipeline

CONSTANT_3 = 3
CONSTANT_3 = 3.6
CONSTANT_4 = 4.0
CONSTANT_5 = 5
CONSTANT_15 = 15.0
CONSTANT_20 = 20
CONSTANT_80 = 80.0
CONSTANT_85 = 85.0
CONSTANT_90 = 90.0
CONSTANT_92 = 92.5



def test_default_yaml_parses() -> None:
    """Default pyqual.yaml should parse without errors."""
    raw = yaml.safe_load(PyqualConfig.default_yaml())
    config = PyqualConfig._parse(raw)
    assert config.name == "quality-loop"
    assert len(config.stages) == CONSTANT_5
    assert len(config.gates) == CONSTANT_3
    assert config.loop.max_iterations == CONSTANT_3


def test_gate_config_from_dict() -> None:
    """Gate config parses suffixes correctly."""
    g1 = GateConfig.from_dict("cc_max", "15")
    assert g1.metric == "cc"
    assert g1.operator == "le"
    assert g1.threshold == CONSTANT_15

    g2 = GateConfig.from_dict("coverage_min", "80")
    assert g2.metric == "coverage"
    assert g2.operator == "ge"
    assert g2.threshold == CONSTANT_80


def test_gate_check_pass() -> None:
    """Gate passes when metric meets threshold."""
    g = Gate(GateConfig(metric="cc", operator="le", threshold=CONSTANT_15))
    result = g.check({"cc": CONSTANT_3})
    assert result.passed is True


def test_gate_check_fail():
    """Gate fails when metric exceeds threshold."""
    g = Gate(GateConfig(metric="cc", operator="le", threshold=CONSTANT_3))
    result = g.check({"cc": CONSTANT_3})
    assert result.passed is False


def test_gate_check_missing_metric():
    """Gate fails when metric is not found."""
    g = Gate(GateConfig(metric="coverage", operator="ge", threshold=CONSTANT_80))
    result = g.check({})
    assert result.passed is False
    assert result.value is None


def test_gate_set_from_toon():
    """GateSet reads CC from analysis_toon.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "analysis_toon.yaml").write_text(
            "# code2llm | CC̄=3.6 | critical:9\nHEALTH:\n  test"
        )
        gs = GateSet([GateConfig(metric="cc", operator="le", threshold=CONSTANT_4)])
        results = gs.check_all(p)
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].value == CONSTANT_3


def test_gate_set_from_vallm():
    """GateSet reads vallm pass rate from validation_toon.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 85 (85.0%)  warnings: 5"
        )
        gs = GateSet([GateConfig(metric="vallm_pass", operator="ge", threshold=CONSTANT_80)])
        results = gs.check_all(p)
        assert results[0].passed is True
        assert results[0].value == CONSTANT_85


def test_gate_set_from_coverage():
    """GateSet reads coverage from .pyqual/coverage.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        pyqual_dir = p / ".pyqual"
        pyqual_dir.mkdir()
        (pyqual_dir / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": CONSTANT_92}})
        )
        gs = GateSet([GateConfig(metric="coverage", operator="ge", threshold=CONSTANT_80)])
        results = gs.check_all(p)
        assert results[0].passed is True
        assert results[0].value == CONSTANT_92


def test_pipeline_dry_run() -> None:
    """Pipeline dry run executes without errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        config_path = p / "pyqual.yaml"
        config_path.write_text(PyqualConfig.default_yaml())
        (p / ".pyqual").mkdir()

        config = PyqualConfig.load(config_path)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run(dry_run=True)

        assert result.iteration_count >= 1
        for iteration in result.iterations:
            for stage in iteration.stages:
                assert "[dry-run]" in stage.stdout or stage.skipped


def test_pipeline_with_passing_gates():
    """Pipeline stops after first iteration when gates pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()
        # Write metrics that pass all gates
        (p / "analysis_toon.yaml").write_text("CC̄=2.0 critical=0")
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 95 (95.0%)"
        )
        (p / ".pyqual" / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": CONSTANT_90}})
        )

        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""\
pipeline:
  name: test
  metrics:
    cc_max: 3.0
    vallm_pass_min: 90
    coverage_min: 80
  stages:
    - name: noop
      run: echo ok
  loop:
    max_iterations: 3
""")
        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()

        assert result.final_passed is True
        assert result.iteration_count == 1


def test_pipeline_runs_fix_chain_when_gates_fail() -> None:
    """metrics_fail should trigger prefact/fix and after_fix should trigger verify."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()
        (p / "analysis_toon.yaml").write_text("CC̄=2.0 critical=0")
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 95 (95.0%)"
        )
        (p / ".pyqual" / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": CONSTANT_90}})
        )

        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""\
pipeline:
  name: metrics-fail-flow
  metrics:
    cc_max: 1
    vallm_pass_min: 90
    coverage_min: 80
  stages:
    - name: analyze
      run: python3 -c "print('analyze')"
    - name: validate
      run: python3 -c "print('validate')"
    - name: test
      run: python3 -c "print('test')"
    - name: prefact
      run: python3 -c "print('prefact')"
      when: metrics_fail
    - name: fix
      run: python3 -c "print('fix')"
      when: metrics_fail
    - name: verify
      run: python3 -c "print('verify')"
      when: after_fix
  loop:
    max_iterations: 1
""")

        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()

        assert result.iteration_count == 1
        assert result.final_passed is False

        stages = {stage.name: stage for stage in result.iterations[0].stages}
        assert stages["prefact"].stdout.strip() == "prefact"
        assert stages["fix"].stdout.strip() == "fix"
        assert stages["verify"].stdout.strip() == "verify"
        assert stages["prefact"].skipped is False
        assert stages["fix"].skipped is False
        assert stages["verify"].skipped is False


def test_timeout_zero_means_no_timeout() -> None:
    """timeout: 0 should be treated as no timeout, not an immediate timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()

        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""\
pipeline:
  name: timeout-zero
  stages:
    - name: slow-but-safe
      run: python3 -c \"import time; time.sleep(0.2); print('done')\"
      timeout: 0
  loop:
    max_iterations: 1
""")

        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()

        assert result.iteration_count == 1
        stage = result.iterations[0].stages[0]
        assert stage.passed is True
        assert stage.returncode == 0
        assert stage.original_returncode == 0
        assert "done" in stage.stdout


def test_tool_preset_stage_config() -> None:
    """StageConfig with tool: field parses correctly."""
    raw = yaml.safe_load("""\
pipeline:
  name: tool-test
  metrics:
    coverage_min: 80
  stages:
    - name: lint
      tool: ruff
    - name: secrets
      tool: trufflehog
      optional: true
    - name: custom
      run: echo ok
  loop:
    max_iterations: 1
""")
    config = PyqualConfig._parse(raw)
    assert len(config.stages) == CONSTANT_3
    assert config.stages[0].tool == "ruff"
    assert config.stages[0].run == ""
    assert config.stages[0].optional is False
    assert config.stages[1].tool == "trufflehog"
    assert config.stages[1].optional is True
    assert config.stages[2].run == "echo ok"
    assert config.stages[2].tool == ""


def test_tool_preset_dry_run() -> None:
    """Pipeline dry run with tool: stages shows tool label."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()
        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""\
pipeline:
  name: tool-dry
  stages:
    - name: lint
      tool: ruff
    - name: secrets
      tool: trufflehog
      optional: true
  loop:
    max_iterations: 1
""")
        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run(dry_run=True)

        assert result.iteration_count == 1
        stages = result.iterations[0].stages
        # ruff stage should show dry-run or be skipped (if not installed)
        lint_stage = stages[0]
        assert "tool:ruff" in lint_stage.stdout or lint_stage.skipped
        # trufflehog is optional — skipped if not installed
        secrets_stage = stages[1]
        assert secrets_stage.skipped or "tool:trufflehog" in secrets_stage.stdout


def test_tool_preset_resolution() -> None:
    """Tool presets resolve to correct commands."""
    from pyqual.tools import get_preset, list_presets

    assert "ruff" in list_presets()
    assert "pytest" in list_presets()

    ruff = get_preset("ruff")
    assert ruff is not None
    assert ruff.binary == "ruff"
    assert ".pyqual/ruff.json" in ruff.shell_command(".")
    assert ruff.allow_failure is True

    pytest_preset = get_preset("pytest")
    assert pytest_preset is not None
    assert pytest_preset.allow_failure is False

    assert get_preset("nonexistent-tool") is None


def test_stage_requires_run_or_tool() -> None:
    """StageConfig must have either 'run' or 'tool'."""
    raw = yaml.safe_load("""\
pipeline:
  name: bad-config
  stages:
    - name: empty-stage
  loop:
    max_iterations: 1
""")
    try:
        PyqualConfig._parse(raw)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty-stage" in str(e)


def test_stage_rejects_both_run_and_tool() -> None:
    """StageConfig rejects having both 'run' and 'tool' set."""
    raw = yaml.safe_load("""\
pipeline:
  name: ambiguous
  stages:
    - name: conflict
      run: echo hello
      tool: ruff
  loop:
    max_iterations: 1
""")
    try:
        PyqualConfig._parse(raw)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "conflict" in str(e)
        assert "not both" in str(e)


def test_stage_rejects_unknown_tool() -> None:
    """StageConfig rejects unknown tool preset names at parse time."""
    import yaml
    raw = yaml.safe_load("""\
pipeline:
  name: bad-tool
  stages:
    - name: typo
      tool: ruf
  loop:
    max_iterations: 1
""")
    try:
        PyqualConfig._parse(raw)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "ruf" in str(e)
        assert "unknown" in str(e).lower()


def test_pipeline_writes_nfo_sqlite_log() -> None:
    """Pipeline run writes structured log to .pyqual/pipeline.db via nfo."""
    import json as json_mod
    import sqlite3
    import ast
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()
        (p / "analysis_toon.yaml").write_text("CC̄=2.0 critical=0")
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 95 (95.0%)"
        )
        (p / ".pyqual" / "coverage.json").write_text(
            json_mod.dumps({"totals": {"percent_covered": CONSTANT_90}})
        )

        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""\
pipeline:
  name: log-test
  metrics:
    cc_max: 3.0
    coverage_min: 80
  stages:
    - name: noop
      run: echo ok
  loop:
    max_iterations: 1
""")
        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()

        db_path = p / ".pyqual" / "pipeline.db"
        assert db_path.exists(), "pipeline.db should be written by nfo"

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM pipeline_logs ORDER BY rowid").fetchall()
        conn.close()

        assert len(rows) >= CONSTANT_3, f"Expected ≥CONSTANT_3 log entries, got {len(rows)}"

        events = [r["function_name"] for r in rows]
        assert "pipeline_start" in events
        assert "stage_done" in events
        assert "gate_check" in events
        assert "pipeline_end" in events

        # Verify stage_done row has structured kwargs
        stage_row = next(r for r in rows if r["function_name"] == "stage_done")
        kwargs = ast.literal_eval(stage_row["kwargs"])
        assert kwargs["stage"] == "noop"
        assert "returncode" in kwargs
        assert "duration_s" in kwargs
        assert "ok" in kwargs  # 'ok' not 'passed' — avoids nfo PASS redaction

        # Verify pipeline_end entry
        end_row = next(r for r in rows if r["function_name"] == "pipeline_end")
        end_kw = ast.literal_eval(end_row["kwargs"])
        assert end_kw["final_ok"] is True  # 'final_ok' not 'final_passed'


def test_stage_result_preserves_original_returncode() -> None:
    """StageResult.original_returncode preserves the raw exit code."""
    from pyqual.pipeline import StageResult
    result = StageResult(
        name="lint", returncode=0, stdout="", stderr="",
        duration=1.0, original_returncode=1, command="ruff check .",
        tool="ruff",
    )
    assert result.passed is True  # normalized rc=0
    assert result.original_returncode == 1  # raw rc preserved


def test_default_tools_json_loads_all_presets() -> None:
    """Built-in default_tools.json loads and populates TOOL_PRESETS."""
    from pyqual.tools import TOOL_PRESETS, _BUILTIN_NAMES
    assert len(TOOL_PRESETS) >= CONSTANT_20, f"Expected >=CONSTANT_20 presets, got {len(TOOL_PRESETS)}"
    assert "ruff" in TOOL_PRESETS
    assert "pytest" in TOOL_PRESETS
    assert "report" in TOOL_PRESETS
    assert _BUILTIN_NAMES == frozenset(TOOL_PRESETS.keys()) or len(_BUILTIN_NAMES) > 0


def test_preset_from_dict() -> None:
    """_preset_from_dict creates ToolPreset from JSON dict."""
    from pyqual.tools import _preset_from_dict
    d = {"binary": "echo", "command": "echo {workdir}", "output": ".pyqual/out.json"}
    p = _preset_from_dict(d)
    assert p.binary == "echo"
    assert p.allow_failure is True  # default

    d2 = {"binary": "pytest", "command": "pytest -q", "output": "", "allow_failure": False}
    p2 = _preset_from_dict(d2)
    assert p2.allow_failure is False


def test_load_user_tools_from_json() -> None:
    """load_user_tools() loads pyqual.tools.json and overrides/adds presets."""
    import json
    from pyqual.tools import TOOL_PRESETS, load_user_tools, get_preset

    with tempfile.TemporaryDirectory() as td:
        user_file = Path(td) / "pyqual.tools.json"
        user_file.write_text(json.dumps({
            "_test_user_tool": {
                "binary": "echo",
                "command": "echo user {workdir}",
                "output": ".pyqual/user.json"
            },
            "ruff": {
                "binary": "ruff",
                "command": "ruff check {workdir} --fix --output-format=json",
                "output": ".pyqual/ruff.json"
            }
        }))
        # Save original ruff preset
        original_ruff = TOOL_PRESETS.get("ruff")
        try:
            count = load_user_tools(td)
            assert count == 2
            assert get_preset("_test_user_tool") is not None
            assert get_preset("_test_user_tool").binary == "echo"
            # ruff should be overridden
            assert "--fix" in get_preset("ruff").command
        finally:
            TOOL_PRESETS.pop("_test_user_tool", None)
            if original_ruff:
                TOOL_PRESETS["ruff"] = original_ruff


def test_load_user_tools_no_file() -> None:
    """load_user_tools() returns 0 when no pyqual.tools.json exists."""
    from pyqual.tools import load_user_tools

    with tempfile.TemporaryDirectory() as td:
        assert load_user_tools(td) == 0


def test_dump_presets_json() -> None:
    """dump_presets_json() produces valid JSON with all presets."""
    import json as json_mod
    from pyqual.tools import dump_presets_json
    output = dump_presets_json()
    data = json_mod.loads(output)
    assert isinstance(data, dict)
    assert "ruff" in data
    assert "binary" in data["ruff"]
    assert "command" in data["ruff"]

    # Subset dump
    subset = dump_presets_json(["ruff", "pytest"])
    subset_data = json_mod.loads(subset)
    assert set(subset_data.keys()) == {"ruff", "pytest"}


def test_register_custom_preset() -> None:
    """register_preset() adds a new tool preset at runtime."""
    from pyqual.tools import ToolPreset, register_preset, get_preset, TOOL_PRESETS

    name = "_test_custom_tool"
    try:
        preset = ToolPreset(
            binary="echo",
            command="echo check {workdir}",
            output=".pyqual/custom.json",
            allow_failure=True,
        )
        register_preset(name, preset)
        assert get_preset(name) is preset
        assert get_preset(name).binary == "echo"

        # Reject duplicate without override
        try:
            register_preset(name, preset)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already registered" in str(e)

        # Allow override
        preset2 = ToolPreset(binary="cat", command="cat {workdir}", output="", allow_failure=False)
        register_preset(name, preset2, override=True)
        assert get_preset(name).binary == "cat"
    finally:
        TOOL_PRESETS.pop(name, None)


def test_custom_tools_from_yaml() -> None:
    """custom_tools: section in YAML registers presets that stages can use."""
    import yaml
    from pyqual.tools import TOOL_PRESETS, get_preset

    raw = yaml.safe_load("""\
pipeline:
  name: custom-preset-test
  custom_tools:
    - name: _yaml_custom
      binary: echo
      command: "echo lint {workdir}"
      output: .pyqual/custom.json
      allow_failure: true
  stages:
    - name: custom-lint
      tool: _yaml_custom
  loop:
    max_iterations: 1
""")
    try:
        config = PyqualConfig._parse(raw)
        assert len(config.stages) == 1
        assert config.stages[0].tool == "_yaml_custom"
        assert get_preset("_yaml_custom") is not None
        assert get_preset("_yaml_custom").binary == "echo"
    finally:
        TOOL_PRESETS.pop("_yaml_custom", None)
