"""Quality gates — check metrics against thresholds."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyqual.config import GateConfig


@dataclass
class GateResult:
    """Result of a single gate check."""
    metric: str
    value: float | None
    threshold: float
    operator: str
    passed: bool
    source: str = ""

    def __str__(self) -> str:
        symbol = "✅" if self.passed else "❌"
        op_str = {"le": "≤", "ge": "≥", "lt": "<", "gt": ">", "eq": "="}
        op = op_str.get(self.operator, self.operator)
        val = f"{self.value:.1f}" if self.value is not None else "N/A"
        return f"{symbol} {self.metric}: {val} {op} {self.threshold}"


@dataclass
class Gate:
    """Single quality gate with metric extraction."""
    config: GateConfig

    def check(self, metrics: dict[str, float]) -> GateResult:
        """Check this gate against collected metrics."""
        value = metrics.get(self.config.metric)
        if value is None:
            return GateResult(
                metric=self.config.metric, value=None,
                threshold=self.config.threshold, operator=self.config.operator,
                passed=False, source="metric not found",
            )
        ops = {
            "le": lambda v, t: v <= t,
            "ge": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "gt": lambda v, t: v > t,
            "eq": lambda v, t: v == t,
        }
        check_fn = ops.get(self.config.operator, ops["le"])
        return GateResult(
            metric=self.config.metric, value=value,
            threshold=self.config.threshold, operator=self.config.operator,
            passed=check_fn(value, self.config.threshold),
        )


class GateSet:
    """Collection of quality gates with metric collection."""

    def __init__(self, configs: list[GateConfig]):
        self.gates = [Gate(c) for c in configs]

    def check_all(self, workdir: Path = Path(".")) -> list[GateResult]:
        """Collect metrics from known sources and check all gates."""
        metrics = self._collect_metrics(workdir)
        return [g.check(metrics) for g in self.gates]

    def all_passed(self, workdir: Path = Path(".")) -> bool:
        """Return True if all gates pass."""
        return all(r.passed for r in self.check_all(workdir))

    def _collect_metrics(self, workdir: Path) -> dict[str, float]:
        """Collect metrics from .pyqual/ artifacts and .toon files."""
        metrics: dict[str, float] = {}
        metrics.update(self._from_toon(workdir))
        metrics.update(self._from_vallm(workdir))
        metrics.update(self._from_coverage(workdir))
        return metrics

    def _from_toon(self, workdir: Path) -> dict[str, float]:
        """Extract CC̄ and critical count from analysis_toon.yaml or analysis.toon."""
        result: dict[str, float] = {}
        for name in ["analysis_toon.yaml", "analysis.toon", "project_toon.yaml"]:
            p = workdir / name
            if not p.exists():
                continue
            text = p.read_text()
            cc_match = re.search(r"CC̄[=:]?\s*([\d.]+)", text)
            if cc_match:
                result["cc"] = float(cc_match.group(1))
            crit_match = re.search(r"critical[=:]?\s*(\d+)", text)
            if crit_match:
                result["critical"] = float(crit_match.group(1))
            break
        return result

    def _from_vallm(self, workdir: Path) -> dict[str, float]:
        """Extract vallm pass rate from validation_toon.yaml or errors.json."""
        result: dict[str, float] = {}
        for name in ["validation_toon.yaml", "validation.toon"]:
            p = workdir / name
            if not p.exists():
                continue
            text = p.read_text()
            pass_match = re.search(r"passed:\s*(\d+)\s*\(([\d.]+)%\)", text)
            if pass_match:
                result["vallm_pass"] = float(pass_match.group(2))
            break
        errors_path = workdir / ".pyqual" / "errors.json"
        if errors_path.exists():
            try:
                errors = json.loads(errors_path.read_text())
                if isinstance(errors, list):
                    result["error_count"] = float(len(errors))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_coverage(self, workdir: Path) -> dict[str, float]:
        """Extract test coverage from coverage.json."""
        result: dict[str, float] = {}
        cov_path = workdir / ".pyqual" / "coverage.json"
        if not cov_path.exists():
            cov_path = workdir / "coverage.json"
        if cov_path.exists():
            try:
                data = json.loads(cov_path.read_text())
                total = data.get("totals", {}).get("percent_covered")
                if total is not None:
                    result["coverage"] = float(total)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return result
