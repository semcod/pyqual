"""Configuration loader for pyqual.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


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
    run: str
    when: str = "always"  # always | metrics_fail | metrics_pass
    timeout: int = 300
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
        stages = [
            StageConfig(**s) for s in pipeline.get("stages", [])
        ]
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

  # Pipeline stages — executed in order
  stages:
    - name: analyze
      run: code2llm ./ -f toon,evolution
    
    - name: validate
      run: vallm batch ./ --recursive --errors-json > .pyqual/errors.json
    
    - name: fix
      run: echo "LLM fix placeholder — connect llx or aider here"
      when: metrics_fail
    
    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json
      when: always

  # Loop behavior
  loop:
    max_iterations: 3
    on_fail: report      # report | create_ticket | block

  # Environment (optional)
  env:
    LLM_MODEL: openrouter/qwen/qwen3-coder-next
"""
