"""Metric collector functions for GateSet.

Each function takes a workdir Path and returns a dict[str, float].
``_COLLECTORS`` is the ordered list used by GateSet._collect_metrics.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _read_artifact_text(workdir: Path, filenames: list[str]) -> str | None:
    """Read the first matching file from workdir or workdir/project."""
    for base in (workdir, workdir / "project"):
        for name in filenames:
            p = base / name
            if p.exists():
                try:
                    return p.read_text()
                except OSError:
                    continue
    return None


def _from_toon(workdir: Path) -> dict[str, float]:
    """Extract CC̄ and critical count from analysis_toon.yaml or analysis.toon."""
    result: dict[str, float] = {}
    text = _read_artifact_text(
        workdir,
        ["analysis.toon.yaml", "analysis_toon.yaml", "analysis.toon", "project_toon.yaml"],
    )
    if not text:
        return result
    cc_match = re.search(r"CC̄[=:]?\s*([\d.]+)", text)
    if cc_match:
        result["cc"] = float(cc_match.group(1))
    crit_match = re.search(r"critical[=:]?\s*(\d+)", text)
    if crit_match:
        result["critical"] = float(crit_match.group(1))
    return result


def _from_vallm(workdir: Path) -> dict[str, float]:
    """Extract vallm pass rate from validation_toon.yaml or errors.json."""
    result: dict[str, float] = {}
    text = _read_artifact_text(workdir, ["validation.toon.yaml", "validation_toon.yaml", "validation.toon"])
    if text:
        pass_match = re.search(r"passed:\s*(\d+)\s*\(([\d.]+)%\)", text)
        if pass_match:
            result["vallm_pass"] = float(pass_match.group(2))
    errors_path = workdir / ".pyqual" / "errors.json"
    if errors_path.exists():
        try:
            errors = json.loads(errors_path.read_text())
            if isinstance(errors, list):
                result["error_count"] = float(len(errors))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_coverage(workdir: Path) -> dict[str, float]:
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


def _from_bandit(workdir: Path) -> dict[str, float]:
    """Extract security issue counts from bandit JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "bandit.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            results = data.get("results", [])
            high = sum(1 for r in results if r.get("issue_severity") == "HIGH")
            medium = sum(1 for r in results if r.get("issue_severity") == "MEDIUM")
            low = sum(1 for r in results if r.get("issue_severity") == "LOW")
            result["bandit_high"] = float(high)
            result["bandit_medium"] = float(medium)
            result["bandit_low"] = float(low)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return result


def _from_secrets(workdir: Path) -> dict[str, float]:
    """Extract secrets scan metrics from secrets.json."""
    result: dict[str, float] = {}
    sec_path = workdir / ".pyqual" / "secrets.json"
    if sec_path.exists():
        try:
            data = json.loads(sec_path.read_text())
            if isinstance(data, list):
                severities = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                max_sev = 0
                for finding in data:
                    sev = finding.get("severity", "").lower()
                    max_sev = max(max_sev, severities.get(sev, 0))
                result["secrets_severity"] = float(max_sev)
                result["secrets_count"] = float(len(data))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_vulnerabilities(workdir: Path) -> dict[str, float]:
    """Extract vulnerability metrics from vulns.json."""
    result: dict[str, float] = {}
    vuln_path = workdir / ".pyqual" / "vulns.json"
    if vuln_path.exists():
        try:
            data = json.loads(vuln_path.read_text())
            if isinstance(data, list):
                critical = sum(1 for v in data if v.get("severity", "").lower() == "critical")
                result["vuln_critical"] = float(critical)
                result["vuln_count"] = float(len(data))
            elif isinstance(data, dict):
                vulns = data.get("vulnerabilities", [])
                critical = sum(1 for v in vulns if v.get("severity", "").lower() == "critical")
                result["vuln_critical"] = float(critical)
                result["vuln_count"] = float(len(vulns))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_sbom(workdir: Path) -> dict[str, float]:
    """Extract SBOM compliance metrics from sbom.json."""
    result: dict[str, float] = {}
    sbom_path = workdir / ".pyqual" / "sbom.json"
    if sbom_path.exists():
        try:
            data = json.loads(sbom_path.read_text())
            comps = data.get("components", [])
            total = len(comps)
            licensed = sum(1 for c in comps if c.get("licenses"))
            if total > 0:
                result["sbom_compliance"] = (licensed / total) * 100
            forbidden = sum(
                1 for c in comps
                for lic in (c.get("licenses", []) or [])
                if any(f in str(lic).upper() for f in ["GPL", "AGPL", "SSPL"])
            )
            result["license_blacklist"] = float(forbidden)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_vulture(workdir: Path) -> dict[str, float]:
    """Extract code health metrics from vulture.json."""
    result: dict[str, float] = {}
    vul_path = workdir / ".pyqual" / "vulture.json"
    if vul_path.exists():
        try:
            data = json.loads(vul_path.read_text())
            if isinstance(data, list):
                result["unused_count"] = float(len(data))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_pyroma(workdir: Path) -> dict[str, float]:
    """Extract packaging quality from pyroma.json."""
    result: dict[str, float] = {}
    pyr_path = workdir / ".pyqual" / "pyroma.json"
    if pyr_path.exists():
        try:
            data = json.loads(pyr_path.read_text())
            score = data.get("score") or data.get("rating")
            if isinstance(score, (int, float)):
                result["pyroma_score"] = float(score)
            elif isinstance(score, str) and score.upper() in "ABCDEF":
                result["pyroma_score"] = float(6 - ord(score.upper()[0]) + ord("A"))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_git_health(workdir: Path) -> dict[str, float]:
    """Extract repository health metrics from git_metrics.json."""
    result: dict[str, float] = {}
    git_path = workdir / ".pyqual" / "git_metrics.json"
    if git_path.exists():
        try:
            data = json.loads(git_path.read_text())
            age = data.get("main_branch_age_days")
            if age:
                result["git_branch_age"] = float(age)
            todos = data.get("todo_count")
            if todos:
                result["todo_count"] = float(todos)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_llm_quality(workdir: Path) -> dict[str, float]:
    """Extract LLM code quality metrics from humaneval.json and llm_analysis.json."""
    result: dict[str, float] = {}
    for fname in ["humaneval.json", "llm_analysis.json"]:
        path = workdir / ".pyqual" / fname
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if fname == "humaneval.json":
                    pass_at_1 = data.get("pass_at_1") or data.get("pass@1")
                    if pass_at_1:
                        result["llm_pass_rate"] = float(pass_at_1)
                else:
                    cc = data.get("avg_cyclomatic_complexity")
                    if cc:
                        result["llm_cc"] = float(cc)
                    hal = data.get("hallucination_rate")
                    if hal:
                        result["hallucination_rate"] = float(hal)
                    bias = data.get("prompt_bias_score")
                    if bias:
                        result["prompt_bias_score"] = float(bias)
                    eff = data.get("agent_iterations") or data.get("agent_efficiency")
                    if eff:
                        result["agent_efficiency"] = float(eff)
            except (json.JSONDecodeError, TypeError):
                pass
    return result


def _from_ai_cost(workdir: Path) -> dict[str, float]:
    """Extract AI cost metrics from costs.json."""
    result: dict[str, float] = {}
    cost_path = workdir / ".pyqual" / "costs.json"
    if cost_path.exists():
        try:
            data = json.loads(cost_path.read_text())
            cost = data.get("total_cost") or data.get("cost_usd")
            if cost:
                result["ai_cost"] = float(cost)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_benchmark(workdir: Path) -> dict[str, float]:
    """Extract benchmark metrics from asv.json."""
    result: dict[str, float] = {}
    bench_path = workdir / ".pyqual" / "asv.json"
    if bench_path.exists():
        try:
            data = json.loads(bench_path.read_text())
            if isinstance(data, list) and len(data) >= 2:
                curr = data[-1].get("result", {})
                prev = data[-2].get("result", {})
                for key in curr:
                    if key in prev and prev[key]:
                        reg = ((curr[key] - prev[key]) / prev[key]) * 100
                        result["bench_regression"] = reg
                        break
            if "version" in str(data):
                results = data.get("results", {})
                if results:
                    bench_times = [v for v in results.values() if isinstance(v, (int, float))]
                    if bench_times:
                        result["bench_time"] = sum(bench_times) / len(bench_times)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return result


def _from_memory_profile(workdir: Path) -> dict[str, float]:
    """Extract memory metrics from mem.json."""
    result: dict[str, float] = {}
    mem_path = workdir / ".pyqual" / "mem.json"
    if mem_path.exists():
        try:
            data = json.loads(mem_path.read_text())
            peak = data.get("peak_memory_mb") or data.get("peak")
            if peak:
                result["mem_usage"] = float(peak)
            cpu = data.get("cpu_time_s") or data.get("cpu_time")
            if cpu:
                result["cpu_time"] = float(cpu)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_mypy(workdir: Path) -> dict[str, float]:
    """Extract mypy type error count from JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "mypy.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                errors = len(data)
            elif isinstance(data, dict):
                errors = len(data.get("errors", data.get("messages", [])))
            else:
                errors = 0
            result["mypy_errors"] = float(errors)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_ruff(workdir: Path) -> dict[str, float]:
    """Extract ruff linter error counts from JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "ruff.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                errors = len(data)
                fatal = sum(1 for e in data if e.get("severity") == "fatal" or str(e.get("code", "")).startswith("E"))
                warning = sum(1 for e in data if e.get("severity") == "warning" or str(e.get("code", "")).startswith("W"))
                result["ruff_errors"] = float(errors)
                result["ruff_fatal"] = float(fatal)
                result["ruff_warnings"] = float(warning)
            elif isinstance(data, dict):
                errors = len(data.get("violations", data.get("messages", [])))
                result["ruff_errors"] = float(errors)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _count_pylint_by_type(messages: list, type_name: str, symbol_prefix: str) -> float:
    """Count pylint messages matching a type or symbol prefix."""
    return float(sum(
        1 for m in messages
        if m.get("type") == type_name or str(m.get("symbol", "")).startswith(symbol_prefix)
    ))


def _from_pylint(workdir: Path) -> dict[str, float]:
    """Extract pylint score and error counts from JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "pylint.json"
    if not p.exists():
        return result
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, TypeError):
        return result
    if isinstance(data, list):
        result["pylint_errors"] = float(len(data))
        result["pylint_fatal"] = _count_pylint_by_type(data, "fatal", "F")
        result["pylint_error"] = _count_pylint_by_type(data, "error", "E")
        result["pylint_warnings"] = _count_pylint_by_type(data, "warning", "W")
    elif isinstance(data, dict):
        score = data.get("score") or data.get("rating")
        if score:
            result["pylint_score"] = float(score)
        messages = data.get("messages", [])
        result["pylint_errors"] = float(len(messages))
    return result


def _from_flake8(workdir: Path) -> dict[str, float]:
    """Extract flake8 violation count from JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "flake8.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                violations = len(data)
                errors = sum(1 for v in data if str(v.get("code", "")).startswith(("E", "F")))
                warnings = sum(1 for v in data if str(v.get("code", "")).startswith(("W",)))
                conventions = sum(1 for v in data if str(v.get("code", "")).startswith(("C", "N")))
                result["flake8_violations"] = float(violations)
                result["flake8_errors"] = float(errors)
                result["flake8_warnings"] = float(warnings)
                result["flake8_conventions"] = float(conventions)
            elif isinstance(data, dict):
                violations = data.get("violations", data.get("messages", []))
                result["flake8_violations"] = float(len(violations))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_interrogate(workdir: Path) -> dict[str, float]:
    """Extract docstring coverage from interrogate JSON output."""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "interrogate.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            coverage = data.get("coverage") or data.get("percent_covered")
            if coverage:
                result["docstring_coverage"] = float(coverage)
            total = data.get("total") or data.get("total_objects")
            documented = data.get("documented") or data.get("documented_objects")
            if total and documented is not None:
                result["docstring_total"] = float(total)
                result["docstring_missing"] = float(total - documented)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


# Ordered list of all active metric collector functions.
# This matches the call order in GateSet._collect_metrics.
_COLLECTORS = [
    _from_toon,
    _from_vallm,
    _from_coverage,
    _from_benchmark,
    _from_memory_profile,
    _from_secrets,
    _from_vulnerabilities,
    _from_bandit,
    _from_sbom,
    _from_vulture,
    _from_pyroma,
    _from_git_health,
    _from_llm_quality,
    _from_ai_cost,
    _from_mypy,
    _from_ruff,
    _from_pylint,
    _from_flake8,
    _from_interrogate,
]
