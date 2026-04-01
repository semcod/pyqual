"""Generate metrics report (YAML) and update README.md badges after a successful pyqual run.

Usage as a stage in pyqual.yaml:

    - name: report
      tool: report
      when: metrics_pass
      optional: true

Or directly:

    python -m pyqual.report [--workdir .] [--config pyqual.yaml] [--readme README.md]
"""

import json
import os
import re
import subprocess
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

# Quality metric badges: (metric_key, label, color_fn, format_fn)
_QUALITY_BADGE_DEFS: list[tuple[str, str, Any, Any]] = [
    ("cc", "CC̄", lambda v: "brightgreen" if v <= 10 else "green" if v <= 15 else "orange" if v <= 25 else "red", lambda v: f"{v:.1f}"),
    ("coverage", "coverage", lambda v: "brightgreen" if v >= 80 else "green" if v >= 60 else "orange" if v >= 40 else "red", lambda v: f"{v:.0f}%25"),
    ("vallm_pass", "vallm", lambda v: "brightgreen" if v >= 90 else "green" if v >= 70 else "orange" if v >= 50 else "red", lambda v: f"{v:.0f}%25"),
    ("critical", "critical", lambda v: "brightgreen" if v == 0 else "red", lambda v: f"{v:.0f}"),
    ("error_count", "errors", lambda v: "brightgreen" if v == 0 else "orange" if v <= 5 else "red", lambda v: f"{v:.0f}"),
    ("maintainability_index", "MI", lambda v: "brightgreen" if v >= 80 else "green" if v >= 60 else "orange" if v >= 40 else "red", lambda v: f"{v:.0f}"),
    ("ruff_errors", "ruff", lambda v: "brightgreen" if v == 0 else "orange" if v <= 10 else "red", lambda v: f"{v:.0f}"),
    ("mypy_errors", "mypy", lambda v: "brightgreen" if v == 0 else "orange" if v <= 5 else "red", lambda v: f"{v:.0f}"),
    ("bandit_high", "bandit", lambda v: "brightgreen" if v == 0 else "red", lambda v: f"{v:.0f}%20high"),
    ("docstring_coverage", "docstrings", lambda v: "brightgreen" if v >= 80 else "green" if v >= 60 else "orange" if v >= 40 else "red", lambda v: f"{v:.0f}%25"),
]


# ---------------------------------------------------------------------------
# Project metadata collection
# ---------------------------------------------------------------------------

def _read_pyproject(workdir: Path) -> dict[str, Any]:
    """Read pyproject.toml and return the parsed dict (or empty)."""
    for name in ("pyproject.toml",):
        p = workdir / name
        if p.exists():
            try:
                import tomllib  # Python 3.11+
            except ModuleNotFoundError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ModuleNotFoundError:
                    # Fallback: parse with regex for key fields
                    return _parse_pyproject_fallback(p)
            return tomllib.loads(p.read_text())
    return {}


def _parse_pyproject_fallback(path: Path) -> dict[str, Any]:
    """Minimal regex parser for pyproject.toml when tomllib is unavailable."""
    text = path.read_text()
    result: dict[str, Any] = {"project": {}}
    for key in ("name", "version", "license", "description"):
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            result["project"][key] = m.group(1)
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
    if m:
        result["project"]["requires-python"] = m.group(1)
    return result


def _read_version(workdir: Path, pyproject: dict[str, Any]) -> str | None:
    """Read project version from VERSION file or pyproject.toml."""
    version_file = workdir / "VERSION"
    if version_file.exists():
        v = version_file.read_text().strip()
        if v:
            return v
    return pyproject.get("project", {}).get("version")


def _read_git_commit_count(workdir: Path) -> int | None:
    """Get total git commit count."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, cwd=str(workdir),
            timeout=10,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def _read_costs_data(workdir: Path) -> dict[str, Any]:
    """Read AI cost data from .pyqual/costs.json or the costs package."""
    result: dict[str, Any] = {}

    # 1. Try .pyqual/costs.json
    costs_path = workdir / ".pyqual" / "costs.json"
    if costs_path.exists():
        try:
            data = json.loads(costs_path.read_text())
            cost = data.get("total_cost") or data.get("cost_usd")
            if cost is not None:
                result["ai_cost"] = float(cost)
            commits = data.get("total_commits") or data.get("ai_commits")
            if commits is not None:
                result["ai_commits"] = int(commits)
            human = data.get("human_time") or data.get("human_hours")
            if human is not None:
                result["human_hours"] = float(human)
            human_cost = data.get("human_cost")
            if human_cost is not None:
                result["human_cost"] = float(human_cost)
            model = data.get("model")
            if model:
                result["model"] = str(model)
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. Try costs package (if installed and no data yet)
    if "ai_cost" not in result:
        try:
            from costs.git_parser import parse_commits  # type: ignore[import-untyped]

            all_commits = parse_commits(str(workdir), max_count=500, ai_only=False, full_history=True)
            ai_indicators = ["🤖", "ai:", "[ai]", "(ai)", "automat", "cascade", "claude", "gpt", "llm"]
            ai_commits = [
                c for c in all_commits
                if any(ind in c[1].lower() for ind in ai_indicators)
            ]
            total_cost = max(len(ai_commits) * 0.15, 0.01) if ai_commits else 0.0
            result.setdefault("ai_cost", total_cost)
            result.setdefault("ai_commits", len(ai_commits) or len(all_commits))

            # Human time estimate
            from collections import defaultdict
            daily: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
            for c in all_commits:
                try:
                    date = c[0].committed_datetime.strftime("%Y-%m-%d")
                    author = c[0].author.name
                    daily[date][author].append(c)
                except Exception:
                    pass
            human_hours = sum(
                min(len(commits) * 0.5, 8.0)
                for authors in daily.values()
                for commits in authors.values()
            )
            result.setdefault("human_hours", human_hours)
            result.setdefault("human_cost", human_hours * 100)
        except Exception:
            pass

    return result


def collect_project_metadata(workdir: Path, config: PyqualConfig) -> dict[str, Any]:
    """Collect project-level metadata for badges and report."""
    pyproject = _read_pyproject(workdir)
    proj = pyproject.get("project", {})
    meta: dict[str, Any] = {}

    # Version
    version = _read_version(workdir, pyproject)
    if version:
        meta["version"] = version

    # Python version requirement
    py_req = proj.get("requires-python")
    if py_req:
        meta["python"] = py_req

    # License
    license_val = proj.get("license")
    if isinstance(license_val, dict):
        license_val = license_val.get("text") or license_val.get("file", "")
    if license_val:
        meta["license"] = str(license_val)

    # Package name
    name = proj.get("name")
    if name:
        meta["name"] = name

    # LLM Model (from config env or OS env)
    model = config.env.get("LLM_MODEL") or os.getenv("LLM_MODEL", "")
    if model:
        meta["model"] = model

    # Git commit count
    commits = _read_git_commit_count(workdir)
    if commits is not None:
        meta["commits"] = commits

    # AI cost data (from costs.json or costs package)
    costs = _read_costs_data(workdir)
    meta.update(costs)

    # Timestamp
    meta["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return meta


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
    project_meta = collect_project_metadata(workdir, config)

    report: dict[str, Any] = {
        "pyqual_report": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline": config.name,
            "status": "pass" if all_passed else "fail",
            "project": project_meta,
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


def _build_project_badges(meta: dict[str, Any]) -> str:
    """Build project-info badge line (version, python, license, AI cost, human time, model)."""
    badges: list[str] = []

    # Version
    version = meta.get("version")
    if version:
        url = _badge_url("version", version, "blue")
        badges.append(f"![Version]({url})")

    # Python
    python = meta.get("python")
    if python:
        url = _badge_url("python", python, "blue")
        badges.append(f"![Python]({url})")

    # License
    license_val = meta.get("license")
    if license_val:
        url = _badge_url("license", license_val, "green")
        badges.append(f"![License]({url})")

    # AI Cost
    ai_cost = meta.get("ai_cost")
    ai_commits = meta.get("ai_commits")
    if ai_cost is not None:
        cost_color = "brightgreen" if ai_cost < 1 else "green" if ai_cost < 5 else "orange" if ai_cost < 10 else "red"
        label = "AI Cost"
        value = f"${ai_cost:.2f}" + (f" ({ai_commits} commits)" if ai_commits else "")
        url = _badge_url(label, value, cost_color)
        badges.append(f"![{label}]({url})")

    # Human Time
    human_hours = meta.get("human_hours")
    if human_hours is not None:
        time_color = "blue"
        url = _badge_url("Human Time", f"{human_hours:.1f}h", time_color)
        badges.append(f"![Human Time]({url})")

    # Model
    model = meta.get("model")
    if model:
        url = _badge_url("Model", model, "lightgrey")
        badges.append(f"![Model]({url})")

    return " ".join(badges)


def _build_quality_badges(metrics: dict[str, float], gates_passed: bool,
                          gates_passed_count: int = 0, gates_total: int = 0) -> str:
    """Build quality-metric badge line (pyqual status, gates, CC, coverage, etc.)."""
    badges: list[str] = []

    # Overall pyqual status badge
    if gates_passed:
        badges.append("![pyqual](https://img.shields.io/badge/pyqual-pass-brightgreen)")
    else:
        badges.append("![pyqual](https://img.shields.io/badge/pyqual-fail-red)")

    # Gates ratio badge
    if gates_total > 0:
        ratio = gates_passed_count / gates_total
        color = "brightgreen" if ratio == 1.0 else "green" if ratio >= 0.8 else "orange" if ratio >= 0.5 else "red"
        url = _badge_url("gates", f"{gates_passed_count}/{gates_total}", color)
        badges.append(f"![gates]({url})")

    # Per-metric badges (only those present in metrics)
    for key, label, color_fn, fmt_fn in _QUALITY_BADGE_DEFS:
        value = metrics.get(key)
        if value is not None:
            color = color_fn(value)
            formatted = fmt_fn(value)
            url = _badge_url(label, formatted, color)
            badges.append(f"![{label}]({url})")

    return " ".join(badges)


def build_badges(metrics: dict[str, float], gates_passed: bool,
                 project_meta: dict[str, Any] | None = None,
                 gates_passed_count: int = 0, gates_total: int = 0) -> str:
    """Build full badge block: project info line + quality metrics line."""
    lines: list[str] = []

    # Line 1: project info badges (version, python, license, AI cost, human time, model)
    if project_meta:
        project_line = _build_project_badges(project_meta)
        if project_line:
            lines.append(project_line)

    # Line 2: quality metric badges (pyqual status, gates, CC, coverage, etc.)
    quality_line = _build_quality_badges(metrics, gates_passed, gates_passed_count, gates_total)
    if quality_line:
        lines.append(quality_line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# README badge update
# ---------------------------------------------------------------------------

def update_readme_badges(
    readme_path: Path,
    metrics: dict[str, float],
    gates_passed: bool,
    project_meta: dict[str, Any] | None = None,
    gates_passed_count: int = 0,
    gates_total: int = 0,
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
    badge_line = build_badges(metrics, gates_passed, project_meta,
                              gates_passed_count, gates_total)
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
    gates_passed_count = sum(1 for g in gates if g["passed"])
    gates_total = len(gates)
    project_meta = collect_project_metadata(workdir, config)

    # 1. Generate YAML report
    report = generate_report(config, workdir)
    report_path = workdir / REPORT_FILE
    passed = report["pyqual_report"]["gates"]["passed"]
    total = report["pyqual_report"]["gates"]["total"]
    print(f"pyqual report: {report_path} ({passed}/{total} gates, {len(metrics)} metrics)")

    # 2. Update README badges
    if readme.exists():
        changed = update_readme_badges(
            readme, metrics, all_passed, project_meta,
            gates_passed_count, gates_total,
        )
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
