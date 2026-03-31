"""Tests for the pipeline profile system."""

from __future__ import annotations

import yaml
import pytest

from pyqual.config import PyqualConfig
from pyqual.profiles import PROFILES, get_profile, list_profiles


class TestProfileRegistry:
    def test_list_profiles_returns_sorted(self) -> None:
        names = list_profiles()
        assert names == sorted(names)
        assert len(names) >= 4

    def test_get_profile_known(self) -> None:
        prof = get_profile("python")
        assert prof is not None
        assert prof.description
        assert len(prof.stages) >= 4
        assert "cc_max" in prof.metrics

    def test_get_profile_unknown(self) -> None:
        assert get_profile("nonexistent") is None

    def test_all_profiles_have_required_fields(self) -> None:
        for name, prof in PROFILES.items():
            assert prof.description, f"Profile {name} missing description"
            assert prof.stages, f"Profile {name} has no stages"
            for stage in prof.stages:
                assert "name" in stage, f"Profile {name}: stage missing name"
                assert "tool" in stage or "run" in stage, \
                    f"Profile {name}: stage {stage['name']} has neither tool nor run"


class TestProfileConfig:
    def test_profile_python_loads(self) -> None:
        raw = yaml.safe_load("pipeline:\n  profile: python")
        cfg = PyqualConfig._parse(raw)
        assert cfg.name == "python"
        stage_names = [s.name for s in cfg.stages]
        assert "analyze" in stage_names
        assert "test" in stage_names
        assert len(cfg.gates) >= 2

    def test_profile_metrics_override(self) -> None:
        raw = yaml.safe_load("""
pipeline:
  profile: python
  metrics:
    coverage_min: 42
""")
        cfg = PyqualConfig._parse(raw)
        coverage_gate = next(g for g in cfg.gates if g.metric == "coverage")
        assert coverage_gate.threshold == 42.0
        # Other profile gates should still be present
        cc_gate = next(g for g in cfg.gates if g.metric == "cc")
        assert cc_gate.threshold == 15.0

    def test_profile_env_merge(self) -> None:
        raw = yaml.safe_load("""
pipeline:
  profile: python
  env:
    MY_VAR: hello
""")
        cfg = PyqualConfig._parse(raw)
        assert cfg.env["MY_VAR"] == "hello"

    def test_profile_loop_override(self) -> None:
        raw = yaml.safe_load("""
pipeline:
  profile: python
  loop:
    max_iterations: 5
    on_fail: block
""")
        cfg = PyqualConfig._parse(raw)
        assert cfg.loop.max_iterations == 5
        assert cfg.loop.on_fail == "block"

    def test_profile_stages_override(self) -> None:
        """Explicit stages: in YAML should completely replace profile stages."""
        raw = yaml.safe_load("""
pipeline:
  profile: python
  stages:
    - name: test
      tool: pytest
""")
        cfg = PyqualConfig._parse(raw)
        assert len(cfg.stages) == 1
        assert cfg.stages[0].name == "test"

    def test_unknown_profile_raises(self) -> None:
        raw = yaml.safe_load("pipeline:\n  profile: nonexistent")
        with pytest.raises(ValueError, match="Unknown profile"):
            PyqualConfig._parse(raw)

    def test_ci_profile_single_iteration(self) -> None:
        raw = yaml.safe_load("pipeline:\n  profile: ci")
        cfg = PyqualConfig._parse(raw)
        assert cfg.loop.max_iterations == 1
        assert cfg.loop.on_fail == "report"

    def test_profile_name_defaults(self) -> None:
        """Without explicit name:, config name should be the profile name."""
        raw = yaml.safe_load("pipeline:\n  profile: lint-only")
        cfg = PyqualConfig._parse(raw)
        assert cfg.name == "lint-only"

    def test_explicit_name_overrides_profile(self) -> None:
        raw = yaml.safe_load("""
pipeline:
  name: my-pipeline
  profile: python
""")
        cfg = PyqualConfig._parse(raw)
        assert cfg.name == "my-pipeline"

    def test_no_profile_still_works(self) -> None:
        """Config without profile: should work as before."""
        raw = yaml.safe_load("""
pipeline:
  stages:
    - name: test
      tool: pytest
  metrics:
    coverage_min: 80
""")
        cfg = PyqualConfig._parse(raw)
        assert len(cfg.stages) == 1
        assert cfg.stages[0].name == "test"
