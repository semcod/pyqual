"""Quality gates — check metrics against thresholds."""

from __future__ import annotations

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

    def _completion_rate(self, metrics: dict[str, float]) -> float:
        """Compute completion rate from all non-completion-rate gates."""
        relevant_gates = [g for g in self.gates if g.config.metric != "completion_rate"]
        if not relevant_gates:
            return 100.0
        passed_count = sum(1 for g in relevant_gates if g.check(metrics).passed)
        return (passed_count / len(relevant_gates)) * 100

    def check_all(self, workdir: Path = Path(".")) -> list[GateResult]:
        """Collect metrics from known sources and check all gates."""
        metrics = self._collect_metrics(workdir)
        metrics["completion_rate"] = self._completion_rate(metrics)
        return [g.check(metrics) for g in self.gates]

    def all_passed(self, workdir: Path = Path(".")) -> bool:
        """Return True if all gates pass."""
        return all(r.passed for r in self.check_all(workdir))

    def completion_percentage(self, workdir: Path = Path(".")) -> float:
        """Calculate ticket completion percentage based on passed gates.
        
        Returns percentage (0-100) indicating how complete the ticket is.
        Each gate contributes equally to the total score.
        """
        metrics = self._collect_metrics(workdir)
        return self._completion_rate(metrics)

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


class CompositeGateSet(GateSet):
    """Weighted composite quality scoring from multiple gates.
    
    Example:
        gates = [
            GateConfig(metric="coverage", operator="ge", threshold=80),
            GateConfig(metric="cc", operator="le", threshold=15),
        ]
        weights = {"coverage": 0.6, "cc": 0.4}
        composite = CompositeGateSet(gates, weights, pass_threshold=75.0)
        
        result = composite.check_composite(Path("."))
        print(f"Score: {result.score:.1f} - {'PASS' if result.passed else 'FAIL'}")
    """
    
    def __init__(
        self, 
        configs: list[GateConfig], 
        weights: dict[str, float] | None = None,
        pass_threshold: float = 75.0,
    ):
        super().__init__(configs)
        self.weights = weights or {}
        self.pass_threshold = pass_threshold
    
    def compute_score(self, metrics: dict[str, float]) -> float:
        """Compute weighted quality score (0-100) from available metrics.
        
        Missing metrics are excluded from weighting (weights re-normalized).
        """
        components: list[tuple[float, float]] = []
        
        for gate in self.gates:
            metric_name = gate.config.metric
            if metric_name not in metrics:
                continue
                
            value = metrics[metric_name]
            weight = self.weights.get(metric_name, 1.0)
            
            # Convert to 0-100 score based on gate operator
            if gate.config.operator in ("le", "lt"):  # Lower is better
                threshold = gate.config.threshold
                if value <= threshold:
                    score = 100.0
                else:
                    # Linear decay: at 2x threshold, score = 0
                    score = max(0.0, 100.0 - (value - threshold) / threshold * 100.0)
            else:  # ge, gt, eq - higher is better
                threshold = gate.config.threshold
                if value >= threshold:
                    score = 100.0
                else:
                    # Linear: at 0, score = 0
                    score = max(0.0, value / threshold * 100.0)
            
            components.append((weight, score))
        
        if not components:
            return 0.0
        
        total_weight = sum(w for w, _ in components)
        weighted_sum = sum(w * s for w, s in components)
        return round(weighted_sum / total_weight, 2)
    
    def check_composite(self, workdir: Path = Path(".")) -> "CompositeResult":
        """Check all individual gates + compute composite score."""
        from dataclasses import dataclass
        
        @dataclass
        class CompositeResult:
            score: float
            passed: bool
            individual: list[GateResult]
            pass_threshold: float
        
        metrics = self._collect_metrics(workdir)
        individual = self.check_all(workdir)
        score = self.compute_score(metrics)
        
        return CompositeResult(
            score=score,
            passed=score >= self.pass_threshold,
            individual=individual,
            pass_threshold=self.pass_threshold,
        )
