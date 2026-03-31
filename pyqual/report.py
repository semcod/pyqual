"""Generate metrics report (YAML) and update README.md badges after a successful pyqual run.

Usage as a stage in pyqual.yaml:

    - name: report
      tool: report
      when: metrics_pass
      optional: true

Or directly:

    python -m pyqual.report [--workdir .] [--config pyqual.yaml] [--readme README.md]
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPORT_FILE = ".pyqual/metrics_report.yaml"
BADGE_START = "<!-- pyqual:badges:start -->"
BADGE_END = "<!-- pyqual:badges:end -->"

# Metric → badge config: (label, color_fn_or_static, format_fn)
# color_fn takes the value and returns a shields.io color string.
_BADGE_DEFS: list[tuple[str, str, Any, Any]] = [
    # (metric_key, label, color_fn, format_fn)
    ("cc", "CC̄", lambda v: "brightgreen" if v <= 10 else "green" if v <= 15 else "orange" if v <= 25 else "red", lambda v: f"{v:.1f}"),
    ("coverage", "coverage", lambda v: "brightgreen" if v >= 80 else "green" if v >= 60 else "orange" if v >= 40 else "red", lambda v: f"{v:.0f}%25"),
    ("vallm_pass", "vallm", lambda v: "brightgreen" if v >= 90 else "green" if v >= 70 else "orange" if v >= 50 else "red", lambda v: f"{v:.0f}%25"),
    ("critical", "critical", lambda v: "brightgreen" if v == 0 else "red", lambda v: f"{v:.0f}"),
    ("error_count", "errors", lambda v: "brightgreen" if v == 0 else "orange" if v <= 5 else "red", lambda v: f"{v:.0f}"),
]


# ---------------------------------------------------------------------------
# Metric collection (reuse GateSet internals)
# ---------------------------------------------------------------------------

def collect_all_metrics(workdir: Path) -> dict[str, float]:
    """Collect all available metrics from .pyqual/ and project/ artifacts."""
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


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------

def evaluate_gates(config: PyqualConfig, workdir: Path) -> list[dict[str, Any]]:
    """Evaluate all configured gates and return structured results."""
    gate_set = GateSet(config.gates)
    results = gate_set.check_all(workdir)
    return [
        {
            "metric": r.metric,
            "value": round(r.value, 2) if r.value is not None else None,
            "threshold": r.threshold,
            "operator": r.operator,
            "passed": r.passed,
        }
        for r in results
    ]


# ---------------------------------------------------------------------------
# YAML report generation
# ---------------------------------------------------------------------------

def generate_report(
    config: PyqualConfig,
    workdir: Path,
    output: Path | None = None,
) -> dict[str, Any]:
    """Generate a metrics report and write it to YAML.

    Returns the report dict.
    """
    metrics = collect_all_metrics(workdir)
    gates = evaluate_gates(config, workdir)
    all_passed = all(g["passed"] for g in gates)

    report: dict[str, Any] = {
        "pyqual_report": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline": config.name,
            "status": "pass" if all_passed else "fail",
            "gates": {
                "total": len(gates),
                "passed": sum(1 for g in gates if g["passed"]),
                "failed": sum(1 for g in gates if not g["passed"]),
                "details": gates,
            },
            "metrics": {k: round(v, 2) for k, v in sorted(metrics.items())},
        }
    }

    out_path = output or (workdir / REPORT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.dump(report, default_flow_style=False, allow_unicode=True, sort_keys=False))
    return report


# ---------------------------------------------------------------------------
# Badge generation
# ---------------------------------------------------------------------------

def _badge_url(label: str, value: str, color: str) -> str:
    """Build a shields.io static badge URL."""
    label_enc = quote(label, safe="")
    value_enc = quote(value, safe="%")
    return f"https://img.shields.io/badge/{label_enc}-{value_enc}-{color}"


def build_badges(metrics: dict[str, float], gates_passed: bool) -> str:
    """Build a markdown line of shields.io badges from collected metrics."""
    badges: list[str] = []

    # Overall status badge
    if gates_passed:
        badges.append(f"![pyqual](https://img.shields.io/badge/pyqual-pass-brightgreen)")
    else:
        badges.append(f"![pyqual](https://img.shields.io/badge/pyqual-fail-red)")

    # Per-metric badges
    for key, label, color_fn, fmt_fn in _BADGE_DEFS:
        value = metrics.get(key)
        if value is not None:
            color = color_fn(value)
            formatted = fmt_fn(value)
            url = _badge_url(label, formatted, color)
            badges.append(f"![{label}]({url})")

    return " ".join(badges)


# ---------------------------------------------------------------------------
# README badge update
# ---------------------------------------------------------------------------

def update_readme_badges(
    readme_path: Path,
    metrics: dict[str, float],
    gates_passed: bool,
) -> bool:
    """Insert or replace pyqual badges in README.md.

    Badges are placed between <!-- pyqual:badges:start --> and
    <!-- pyqual:badges:end --> markers.  If the markers don't exist,
    they are appended after the last existing badge line (any line
    starting with ``![``), or at the very top of the file.

    Returns True if the file was modified.
    """
    if not readme_path.exists():
        return False

    text = readme_path.read_text()
    badge_line = build_badges(metrics, gates_passed)
    block = f"{BADGE_START}\n{badge_line}\n{BADGE_END}"

    # Case 1: markers already present — replace the block
    pattern = re.compile(
        re.escape(BADGE_START) + r".*?" + re.escape(BADGE_END),
        re.DOTALL,
    )
    if pattern.search(text):
        new_text = pattern.sub(block, text)
        if new_text != text:
            readme_path.write_text(new_text)
            return True
        return False

    # Case 2: no markers — find last badge line and insert after it
    lines = text.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("![") or stripped.startswith("[!["):
            insert_idx = i + 1

    # If we found badge lines, insert after the last one
    # Otherwise insert at the top (line 0)
    lines.insert(insert_idx, block)
    readme_path.write_text("\n".join(lines))
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(
    workdir: Path = Path("."),
    config_path: Path | None = None,
    readme_path: Path | None = None,
) -> int:
    """Run report generation + badge update. Returns 0 on success."""
    cfg_file = config_path or (workdir / "pyqual.yaml")
    readme = readme_path or (workdir / "README.md")

    try:
        config = PyqualConfig.load(cfg_file)
    except FileNotFoundError:
        print(f"pyqual report: config not found: {cfg_file}", file=sys.stderr)
        return 1

    metrics = collect_all_metrics(workdir)
    gates = evaluate_gates(config, workdir)
    all_passed = all(g["passed"] for g in gates)

    # 1. Generate YAML report
    report = generate_report(config, workdir)
    report_path = workdir / REPORT_FILE
    passed = report["pyqual_report"]["gates"]["passed"]
    total = report["pyqual_report"]["gates"]["total"]
    print(f"pyqual report: {report_path} ({passed}/{total} gates, {len(metrics)} metrics)")

    # 2. Update README badges
    if readme.exists():
        changed = update_readme_badges(readme, metrics, all_passed)
        if changed:
            print(f"pyqual report: updated badges in {readme}")
        else:
            print(f"pyqual report: badges unchanged in {readme}")
    else:
        print(f"pyqual report: {readme} not found, skipping badges")

    return 0


# ---------------------------------------------------------------------------
# CLI entry (python -m pyqual.report)
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate pyqual metrics report and update README badges")
    parser.add_argument("-w", "--workdir", type=Path, default=Path("."), help="Working directory")
    parser.add_argument("-c", "--config", type=Path, default=None, help="Config file path")
    parser.add_argument("-r", "--readme", type=Path, default=None, help="README file path")
    args = parser.parse_args()

    sys.exit(run(workdir=args.workdir, config_path=args.config, readme_path=args.readme))


if __name__ == "__main__":
    main()
