#!/usr/bin/env python3
"""Composite code health collector — combines multiple signals into a single score.

Reads .pyqual/code_health.json (produced by your own tooling or a wrapper script)
and computes a weighted health score from tech debt, TODO count, dead code, and
test-to-code ratio.

Usage:
    # As a gate in pyqual.yaml:
    #   health_score_min: 70
    #   health_tech_debt_hours_max: 40

    # Self-test:
    python code_health_collector.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import ClassVar

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry

DEFAULT_WEIGHT_TECH_DEBT = 0.30
DEFAULT_WEIGHT_TODO = 0.15
DEFAULT_WEIGHT_DEAD_CODE = 0.25
DEFAULT_WEIGHT_TEST_RATIO = 0.30

MAX_ACCEPTABLE_DEBT_HOURS = 160.0
MAX_ACCEPTABLE_TODOS = 50.0
MAX_ACCEPTABLE_DEAD_CODE_PCT = 20.0


class CodeHealthCollector(MetricCollector):
    """Weighted composite health score from multiple code quality signals."""

    name: ClassVar[str] = "code-health"
    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="code-health",
        description="Composite code health score from tech debt, TODOs, dead code, test ratio",
        version="1.0.0",
        tags=["quality", "health", "composite"],
    )

    ARTIFACT = ".pyqual/code_health.json"

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        path = workdir / self.ARTIFACT
        if not path.exists():
            return result

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return result

        tech_debt = float(data.get("tech_debt_hours", 0))
        todo_count = float(data.get("todo_count", 0))
        dead_code_pct = float(data.get("dead_code_pct", 0))
        test_ratio = float(data.get("test_to_code_ratio", 0))

        result["health_tech_debt_hours"] = tech_debt
        result["health_todo_count"] = todo_count
        result["health_dead_code_pct"] = dead_code_pct
        result["health_test_ratio"] = test_ratio

        # Compute weighted score (0–100)
        debt_score = max(0.0, 100.0 - (tech_debt / MAX_ACCEPTABLE_DEBT_HOURS) * 100.0)
        todo_score = max(0.0, 100.0 - (todo_count / MAX_ACCEPTABLE_TODOS) * 100.0)
        dead_score = max(0.0, 100.0 - (dead_code_pct / MAX_ACCEPTABLE_DEAD_CODE_PCT) * 100.0)
        test_score = min(100.0, test_ratio * 100.0)  # 1.0 ratio = 100%

        health = (
            DEFAULT_WEIGHT_TECH_DEBT * debt_score
            + DEFAULT_WEIGHT_TODO * todo_score
            + DEFAULT_WEIGHT_DEAD_CODE * dead_score
            + DEFAULT_WEIGHT_TEST_RATIO * test_score
        )
        result["health_score"] = round(health, 2)

        return result

    def get_config_example(self) -> str:
        return """\
# code-health plugin — composite quality gates
pipeline:
  metrics:
    health_score_min: 70              # composite score ≥ 70
    health_tech_debt_hours_max: 40    # tech debt ≤ 40 hours
    health_dead_code_pct_max: 10      # dead code ≤ 10%
  stages:
    - name: health-scan
      run: |
        python -c "
        import json, subprocess, pathlib
        # Combine outputs from vulture (dead code) and custom scripts
        result = {'tech_debt_hours': 20, 'todo_count': 8, 'dead_code_pct': 5.2, 'test_to_code_ratio': 0.85}
        pathlib.Path('.pyqual/code_health.json').write_text(json.dumps(result))
        "
"""


PluginRegistry.register(CodeHealthCollector)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        pyqual_dir = p / ".pyqual"
        pyqual_dir.mkdir()

        sample = {
            "tech_debt_hours": 24,
            "todo_count": 12,
            "dead_code_pct": 4.5,
            "test_to_code_ratio": 0.75,
        }
        (pyqual_dir / "code_health.json").write_text(json.dumps(sample))

        collector = CodeHealthCollector()
        metrics = collector.collect(p)

        print("CodeHealthCollector self-test:")
        for k, v in sorted(metrics.items()):
            print(f"  {k}: {v}")

        assert metrics["health_tech_debt_hours"] == 24.0
        assert metrics["health_todo_count"] == 12.0
        assert metrics["health_dead_code_pct"] == 4.5
        assert 60.0 < metrics["health_score"] < 95.0
        print(f"✅ health_score = {metrics['health_score']} (expected 60–95)")
        sys.exit(0)
