"""Tests for devloop — config, gates, pipeline."""

import json
import tempfile
from pathlib import Path

from devloop.config import DevloopConfig, GateConfig
from devloop.gates import Gate, GateSet
from devloop.pipeline import Pipeline


def test_default_yaml_parses():
    """Default devloop.yaml should parse without errors."""
    import yaml
    raw = yaml.safe_load(DevloopConfig.default_yaml())
    config = DevloopConfig._parse(raw)
    assert config.name == "quality-loop"
    assert len(config.stages) == 4
    assert len(config.gates) == 3
    assert config.loop.max_iterations == 3


def test_gate_config_from_dict():
    """Gate config parses suffixes correctly."""
    g1 = GateConfig.from_dict("cc_max", "15")
    assert g1.metric == "cc"
    assert g1.operator == "le"
    assert g1.threshold == 15.0

    g2 = GateConfig.from_dict("coverage_min", "80")
    assert g2.metric == "coverage"
    assert g2.operator == "ge"
    assert g2.threshold == 80.0


def test_gate_check_pass():
    """Gate passes when metric meets threshold."""
    g = Gate(GateConfig(metric="cc", operator="le", threshold=15.0))
    result = g.check({"cc": 3.6})
    assert result.passed is True


def test_gate_check_fail():
    """Gate fails when metric exceeds threshold."""
    g = Gate(GateConfig(metric="cc", operator="le", threshold=3.0))
    result = g.check({"cc": 3.6})
    assert result.passed is False


def test_gate_check_missing_metric():
    """Gate fails when metric is not found."""
    g = Gate(GateConfig(metric="coverage", operator="ge", threshold=80.0))
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
        gs = GateSet([GateConfig(metric="cc", operator="le", threshold=4.0)])
        results = gs.check_all(p)
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].value == 3.6


def test_gate_set_from_vallm():
    """GateSet reads vallm pass rate from validation_toon.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 85 (85.0%)  warnings: 5"
        )
        gs = GateSet([GateConfig(metric="vallm_pass", operator="ge", threshold=80.0)])
        results = gs.check_all(p)
        assert results[0].passed is True
        assert results[0].value == 85.0


def test_gate_set_from_coverage():
    """GateSet reads coverage from .devloop/coverage.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        devloop_dir = p / ".devloop"
        devloop_dir.mkdir()
        (devloop_dir / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": 92.5}})
        )
        gs = GateSet([GateConfig(metric="coverage", operator="ge", threshold=80.0)])
        results = gs.check_all(p)
        assert results[0].passed is True
        assert results[0].value == 92.5


def test_pipeline_dry_run():
    """Pipeline dry run executes without errors."""
    import yaml
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        config_path = p / "devloop.yaml"
        config_path.write_text(DevloopConfig.default_yaml())
        (p / ".devloop").mkdir()

        config = DevloopConfig.load(config_path)
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
        (p / ".devloop").mkdir()
        # Write metrics that pass all gates
        (p / "analysis_toon.yaml").write_text("CC̄=2.0 critical=0")
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 95 (95.0%)"
        )
        (p / ".devloop" / "coverage.json").write_text(
            json.dumps({"totals": {"percent_covered": 90.0}})
        )

        config_yaml = p / "devloop.yaml"
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
        config = DevloopConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()

        assert result.final_passed is True
        assert result.iteration_count == 1
