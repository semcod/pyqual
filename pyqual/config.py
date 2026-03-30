"""Configuration loader for pyqual.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from pyqual.tools import (
    get_preset,
    list_presets,
    load_entry_point_presets,
    register_custom_tools_from_yaml,
)

DEFAULT_STAGE_TIMEOUT = 300


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


@dataclass
class StageConfig:
    """Single pipeline stage."""
    name: str
    run: str = ""
    tool: str = ""            # built-in tool preset (e.g. "ruff", "pytest")
    optional: bool = False    # skip silently when tool binary is missing
    when: str = "always"      # always | metrics_fail | metrics_pass
    timeout: int = DEFAULT_STAGE_TIMEOUT
    capture_output: bool = True


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
        return self.env.get("LLM_MODEL") or os.getenv("LLM_MODEL") or os.getenv("PFIX_MODEL", "openrouter/qwen/qwen3-coder-next")

    @classmethod
    def _parse(cls, raw: dict[str, Any]) -> "PyqualConfig":
        pipeline = raw.get("pipeline", raw)

        # Register external tool presets before validating stages
        load_entry_point_presets()
        custom_tools = pipeline.get("custom_tools", [])
        if custom_tools:
            register_custom_tools_from_yaml(custom_tools)

        stages = []
        for s in pipeline.get("stages", []):
            stage = StageConfig(**s)
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
        gates = [
            GateConfig.from_dict(k, v)
            for k, v in (pipeline.get("metrics") or {}).items()
        ]
        loop_raw = pipeline.get("loop", {})
        loop = LoopConfig(**loop_raw) if loop_raw else LoopConfig()
        return cls(
            name=pipeline.get("name", "default"),
            stages=stages,
            gates=gates,
            loop=loop,
            env=_normalize_env_values(pipeline.get("env", {})),
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
  stages:
    - name: analyze
      tool: code2llm

    - name: validate
      tool: vallm

    - name: fix
      run: echo "LLM fix placeholder — connect llx or aider here"
      when: metrics_fail

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
