"""Quality gates — check metrics against thresholds."""

from dataclasses import dataclass
from pathlib import Path

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
        from pyqual._gate_collectors import _COLLECTORS

        metrics: dict[str, float] = {}
        for fn in _COLLECTORS:
            metrics.update(fn(workdir))

        try:
            from pyqual.plugins import PluginRegistry

            for plugin_class in PluginRegistry.list_plugins():
                try:
                    metrics.update(plugin_class().collect(workdir))
                except Exception:
                    pass
        except Exception:
            pass
        return metrics
