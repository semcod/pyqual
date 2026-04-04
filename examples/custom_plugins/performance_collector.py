#!/usr/bin/env python3
"""Custom MetricCollector for performance/benchmark metrics.

Reads .pyqual/performance.json produced by any load-testing tool
(e.g. locust, k6, wrk, ab) and exposes latency/throughput gates.

Usage:
    # As a gate in pyqual.yaml:
    #   perf_p99_ms_max: 200
    #   perf_error_rate_max: 1.0

    # Self-test:
    python performance_collector.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import ClassVar

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


# Sample data constants (for self-test)
SAMPLE_P50_MS = 12.5
SAMPLE_P95_MS = 45.0
SAMPLE_P99_MS = 120.3
SAMPLE_AVG_MS = 18.7
SAMPLE_RPS = 850.0
SAMPLE_ERRORS = 3
SAMPLE_TOTAL_REQUESTS = 5000

# Expected values for assertions
EXPECTED_P99_MS = 120.3
EXPECTED_RPS = 850.0
EXPECTED_ERROR_RATE = 0.06
ERROR_TOLERANCE = 0.01


class PerformanceCollector(MetricCollector):
    """Collect latency and throughput metrics from load test results."""

    name: ClassVar[str] = "performance"
    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="performance",
        description="Latency, throughput, and error rate from load tests",
        version="1.0.0",
        tags=["performance", "benchmark", "latency"],
    )

    ARTIFACT = ".pyqual/performance.json"

    def collect(self, workdir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        path = workdir / self.ARTIFACT
        if not path.exists():
            return result

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return result

        # Latency percentiles (milliseconds)
        for key, metric in [
            ("p50_ms", "perf_p50_ms"),
            ("p95_ms", "perf_p95_ms"),
            ("p99_ms", "perf_p99_ms"),
            ("avg_ms", "perf_avg_ms"),
        ]:
            if key in data:
                result[metric] = float(data[key])

        # Throughput
        if "requests_per_second" in data:
            result["perf_rps"] = float(data["requests_per_second"])

        # Error rate (percentage)
        if "error_rate" in data:
            result["perf_error_rate"] = float(data["error_rate"])
        elif "errors" in data and "total_requests" in data:
            total = float(data["total_requests"])
            if total > 0:
                result["perf_error_rate"] = float(data["errors"]) / total * 100.0

        return result

    def get_config_example(self) -> str:
        return """\
# performance plugin — load test quality gates
pipeline:
  metrics:
    perf_p99_ms_max: 200       # 99th percentile latency ≤ 200ms
    perf_error_rate_max: 1.0   # error rate ≤ 1%
    perf_rps_min: 100          # throughput ≥ 100 rps
  stages:
    - name: loadtest
      run: locust --headless -u 50 -r 10 --run-time 60s --json > .pyqual/performance.json
      timeout: 120
"""


# Register on import
PluginRegistry.register(PerformanceCollector)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        pyqual_dir = p / ".pyqual"
        pyqual_dir.mkdir()

        # Write sample performance data
        sample = {
            "p50_ms": SAMPLE_P50_MS,
            "p95_ms": SAMPLE_P95_MS,
            "p99_ms": SAMPLE_P99_MS,
            "avg_ms": SAMPLE_AVG_MS,
            "requests_per_second": SAMPLE_RPS,
            "errors": SAMPLE_ERRORS,
            "total_requests": SAMPLE_TOTAL_REQUESTS,
        }
        (pyqual_dir / "performance.json").write_text(json.dumps(sample))

        collector = PerformanceCollector()
        metrics = collector.collect(p)

        print("PerformanceCollector self-test:")
        for k, v in sorted(metrics.items()):
            print(f"  {k}: {v}")

        assert metrics["perf_p99_ms"] == EXPECTED_P99_MS
        assert metrics["perf_rps"] == EXPECTED_RPS
        assert abs(metrics["perf_error_rate"] - EXPECTED_ERROR_RATE) < ERROR_TOLERANCE
        print("✅ All assertions passed")
        sys.exit(0)
