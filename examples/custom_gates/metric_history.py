#!/usr/bin/env python3
"""Track quality metrics over time and detect regressions.

Demonstrates:
- Storing metric snapshots in a JSON history file
- Detecting regressions vs. previous run
- Trend analysis (improving / degrading / stable)
- Gate that fails on metric regression beyond a tolerance

Usage:
    python metric_history.py
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = ".pyqual/metric_history.json"
REGRESSION_TOLERANCE = 2.0  # allow up to 2% regression without failing
EXPECTED_HISTORY_LENGTH = 2

RUN_1_METRICS = {
    "coverage": 85.0,
    "cc": 4.2,
    "ruff_errors": 8.0,
    "pylint_score": 8.5,
}

RUN_2_METRICS = {
    "coverage": 82.0,  # regression (-3%)
    "cc": 3.8,  # improved
    "ruff_errors": 12.0,  # regression (+4)
    "pylint_score": 8.7,  # improved
}


def load_history(workdir: Path) -> list[dict]:
    """Load metric history from JSON file."""
    path = workdir / HISTORY_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_snapshot(workdir: Path, metrics: dict[str, float]) -> list[dict]:
    """Append current metrics as a timestamped snapshot and return full history."""
    history = load_history(workdir)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    history.append(snapshot)

    path = workdir / HISTORY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2))
    return history


def detect_regressions(
    history: list[dict],
    tolerance: float = REGRESSION_TOLERANCE,
) -> dict[str, dict]:
    """Compare latest snapshot to previous and detect regressions.

    Returns dict of metric_name -> {prev, curr, delta, regressed, trend}.
    'trend' is one of: improving, degrading, stable.
    """
    if len(history) < 2:
        return {}

    prev_metrics = history[-2].get("metrics", {})
    curr_metrics = history[-1].get("metrics", {})
    analysis: dict[str, dict] = {}

    # Metrics where higher is better
    higher_better = {"coverage", "vallm_pass", "health_score", "pylint_score",
                     "perf_rps", "docstring_coverage", "maintainability_index"}

    all_keys = set(prev_metrics.keys()) | set(curr_metrics.keys())
    for key in sorted(all_keys):
        if key not in prev_metrics or key not in curr_metrics:
            continue

        prev = prev_metrics[key]
        curr = curr_metrics[key]
        delta = curr - prev

        if key in higher_better:
            regressed = delta < -tolerance
            trend = "improving" if delta > tolerance else ("degrading" if delta < -tolerance else "stable")
        else:
            regressed = delta > tolerance
            trend = "improving" if delta < -tolerance else ("degrading" if delta > tolerance else "stable")

        analysis[key] = {
            "prev": prev,
            "curr": curr,
            "delta": round(delta, 2),
            "regressed": regressed,
            "trend": trend,
        }

    return analysis


def print_trend_report(analysis: dict[str, dict]) -> bool:
    """Print trend analysis and return True if no regressions found."""
    if not analysis:
        print("  (no previous data to compare)")
        return True

    any_regression = False
    for metric, info in analysis.items():
        delta_str = f"+{info['delta']}" if info['delta'] >= 0 else str(info['delta'])

        if info["trend"] == "improving":
            icon = "📈"
        elif info["trend"] == "degrading":
            icon = "📉"
        else:
            icon = "➡️"

        regr = " ⚠️  REGRESSION" if info["regressed"] else ""
        print(f"  {icon} {metric}: {info['prev']:.1f} → {info['curr']:.1f} ({delta_str}){regr}")

        if info["regressed"]:
            any_regression = True

    return not any_regression


def main() -> int:
    """Run the metric history self-test with synthetic history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        pyqual_dir = p / ".pyqual"
        pyqual_dir.mkdir()

        print("=" * 60)
        print("METRIC HISTORY & REGRESSION DETECTION")
        print("=" * 60)

        print("\nRun 1 (baseline):")
        for k, v in sorted(RUN_1_METRICS.items()):
            print(f"  {k}: {v}")
        save_snapshot(p, RUN_1_METRICS)

        print("\nRun 2 (current):")
        for k, v in sorted(RUN_2_METRICS.items()):
            print(f"  {k}: {v}")
        history = save_snapshot(p, RUN_2_METRICS)

        print(f"\nTrend analysis (tolerance: ±{REGRESSION_TOLERANCE}):")
        analysis = detect_regressions(history)
        no_regressions = print_trend_report(analysis)

        print("-" * 60)
        if no_regressions:
            print("✅ No regressions detected")
        else:
            regressed = [k for k, v in analysis.items() if v["regressed"]]
            print(f"❌ Regressions in: {', '.join(regressed)}")

        saved = json.loads((pyqual_dir / "metric_history.json").read_text())
        assert len(saved) == EXPECTED_HISTORY_LENGTH
        assert saved[1]["metrics"]["coverage"] == RUN_2_METRICS["coverage"]
        print(f"\n✅ History file has {len(saved)} snapshots")

        return 0 if no_regressions else 1


if __name__ == "__main__":
    raise SystemExit(main())
