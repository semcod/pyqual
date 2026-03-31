"""Configuration loader for pyqual.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from pyqual.constants import DEFAULT_STAGE_TIMEOUT
from pyqual.tools import (
    get_preset,
    list_presets,
    load_entry_point_presets,
    register_custom_tools_from_yaml,
)


def _load_env_file() -> None:
    """Load .env file if exists."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)


def _normalize_env_values(env: dict[str, Any] | None) -> dict[str, str]:
    """Convert YAML env values to strings suitable for subprocess environments."""
    normalized: dict[str, str] = {}
    for key, value in (env or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            normalized[str(key)] = "true" if value else "false"
        else:
            normalized[str(key)] = str(value)
    return normalized


_STAGE_WHEN_DEFAULTS: dict[str, str] = {
    "analyze": "first_iteration",
    "baseline": "first_iteration",
    "code2llm": "first_iteration",
    "prefact": "metrics_fail",
    "fix": "metrics_fail",
    "fix_regression": "metrics_fail",
    "auto_fix": "metrics_fail",
    "repair": "metrics_fail",
    "verify": "after_fix",
    "verify_fix": "after_fix",
    "regression_report": "after_verify_fix",
    "push": "metrics_pass",
    "publish": "metrics_pass",
    "deploy": "metrics_pass",
}
"""Smart defaults for ``when:`` based on stage name.

Users can still override with explicit ``when:`` in their YAML.
If the stage name is not in this dict, the default is ``"always"``.
"""


@dataclass
class StageConfig:
    """Single pipeline stage."""
    name: str
    run: str = ""
    tool: str = ""            # built-in tool preset (e.g. "ruff", "pytest")
    optional: bool = False    # skip silently when tool binary is missing
    when: str = ""            # auto-inferred from name if empty; see _STAGE_WHEN_DEFAULTS
    timeout: int = DEFAULT_STAGE_TIMEOUT
    capture_output: bool = True

    def __post_init__(self) -> None:
        if not self.when:
            self.when = _STAGE_WHEN_DEFAULTS.get(self.name, "always")


@dataclass
class GateConfig:
    """Single quality gate threshold."""
    metric: str
    operator: str  # le, ge, lt, gt, eq
    threshold: float

    @classmethod
    def from_dict(cls, metric: str, spec: str) -> "GateConfig":
        """Parse 'cc_max: 15' or 'coverage_min: 80' into GateConfig."""
        ops = {"max": "le", "min": "ge", "eq": "eq", "lt": "lt", "gt": "gt"}
        for suffix, op in ops.items():
            if metric.endswith(f"_{suffix}"):
                base = metric[: -len(suffix) - 1]
                return cls(metric=base, operator=op, threshold=float(spec))
        return cls(metric=metric, operator="le", threshold=float(spec))


@dataclass
class LoopConfig:
    """Loop iteration settings."""
    max_iterations: int = 3
    on_fail: str = "report"  # report | create_ticket | block


@dataclass
class PyqualConfig:
    """Full pyqual.yaml configuration."""
    name: str = "default"
    stages: list[StageConfig] = field(default_factory=list)
    gates: list[GateConfig] = field(default_factory=list)
    loop: LoopConfig = field(default_factory=LoopConfig)
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path = "pyqual.yaml") -> "PyqualConfig":
        """Load configuration from YAML file."""
        _load_env_file()
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config not found: {p}. Run 'pyqual init'.")
        raw = yaml.safe_load(p.read_text())
        return cls._parse(raw)

    @property
    def llm_model(self) -> str:
        """Get LLM model from env or config."""
        return self.env.get("LLM_MODEL") or os.getenv("LLM_MODEL", "openrouter/qwen/qwen3-coder-next")

    @classmethod
    def _parse(cls, raw: dict[str, Any]) -> "PyqualConfig":
        pipeline = raw.get("pipeline", raw)

        # Register external tool presets before validating stages
        load_entry_point_presets()
        custom_tools = pipeline.get("custom_tools", [])
        if custom_tools:
            register_custom_tools_from_yaml(custom_tools)

        # --- Profile support ---
        # If profile: is set, use it as the base and merge user overrides.
        profile_name = pipeline.get("profile")
        profile_stages: list[dict[str, Any]] = []
        profile_metrics: dict[str, Any] = {}
        profile_loop: dict[str, Any] = {}
        profile_env: dict[str, Any] = {}
        if profile_name:
            from pyqual.profiles import get_profile, list_profiles
            profile = get_profile(profile_name)
            if profile is None:
                raise ValueError(
                    f"Unknown profile '{profile_name}'. "
                    f"Available: {', '.join(list_profiles())}. "
                    f"Use 'pyqual profiles' to see details."
                )
            profile_stages = list(profile.stages)
            profile_metrics = dict(profile.metrics)
            profile_loop = dict(profile.loop)
            profile_env = dict(profile.env)

        # Stages: explicit stages override profile, otherwise use profile stages
        raw_stages = pipeline.get("stages", profile_stages)
        _stage_fields = {f.name for f in StageConfig.__dataclass_fields__.values()}
        stages = []
        for s in raw_stages:
            filtered = {k: v for k, v in s.items() if k in _stage_fields}
            stage = StageConfig(**filtered)
            if not stage.run and not stage.tool:
                raise ValueError(
                    f"Stage '{stage.name}': must have either 'run' or 'tool' (got neither)."
                )
            if stage.run and stage.tool:
                raise ValueError(
                    f"Stage '{stage.name}': set 'run' or 'tool', not both. "
                    f"Use 'run' for custom commands, 'tool' for built-in presets."
                )
            if stage.tool and get_preset(stage.tool) is None:
                raise ValueError(
                    f"Stage '{stage.name}': unknown tool preset '{stage.tool}'. "
                    f"Available: {', '.join(list_presets())}. "
                    f"Use 'run:' for custom commands."
                )
            stages.append(stage)

        # Metrics: profile defaults merged with user overrides
        merged_metrics = {**profile_metrics, **(pipeline.get("metrics") or {})}
        gates = [
            GateConfig.from_dict(k, v)
            for k, v in merged_metrics.items()
        ]

        # Loop: profile defaults merged with user overrides
        merged_loop = {**profile_loop, **(pipeline.get("loop") or {})}
        if merged_loop:
            _loop_fields = {f.name for f in LoopConfig.__dataclass_fields__.values()}
            loop = LoopConfig(**{k: v for k, v in merged_loop.items() if k in _loop_fields})
        else:
            loop = LoopConfig()

        # Env: profile defaults merged with user overrides
        merged_env = {**profile_env, **(pipeline.get("env") or {})}

        return cls(
            name=pipeline.get("name", profile_name or "default"),
            stages=stages,
            gates=gates,
            loop=loop,
            env=_normalize_env_values(merged_env),
        )

    @staticmethod
    def default_yaml() -> str:
        """Return default pyqual.yaml content."""
        return """\
pipeline:
  name: quality-loop

  # Quality gates — pipeline iterates until ALL pass
  metrics:
    cc_max: 15           # cyclomatic complexity per function
    vallm_pass_min: 90   # vallm validation pass rate (%)
    coverage_min: 80     # test coverage (%)

  # Pipeline stages — use 'tool:' for built-in presets or 'run:' for custom commands
  # See all presets: pyqual tools
  # when: any_stage_fail    — run only when a prior stage in this iteration failed
  # when: metrics_fail      — run only when quality gates are not yet passing
  # when: first_iteration   — run only on iteration 1 (skip re-runs after fix)
  # when: after_fix         — run only after the fix stage ran in this iteration
  stages:
    - name: analyze
      tool: code2llm

    - name: validate
      tool: vallm

    - name: prefact
      tool: prefact
      optional: true
      when: any_stage_fail
      timeout: 900

    - name: fix
      tool: llx-fix
      optional: true
      when: any_stage_fail
      timeout: 1800

    - name: test
      tool: pytest

  # Loop behavior
  loop:
    max_iterations: 3
    on_fail: report      # report | create_ticket | block

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
"""
