"""Metric collector functions for GateSet.

Each function takes a workdir Path and returns a dict[str, float].
``_COLLECTORS`` is the ordered list used by GateSet._collect_metrics.

NOTE: This module is being migrated to the plugin system. New collectors
should be implemented as plugins in pyqual/plugins/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyqual.plugins import MetricCollector

# Import plugin collectors (new plugin-based approach)
try:
    from pyqual.plugins.coverage import CoverageCollector
    _coverage_collector: CoverageCollector | None = CoverageCollector()
except ImportError:
    _coverage_collector = None

try:
    from pyqual.plugins.lint import LintCollector
    _lint_collector: LintCollector | None = LintCollector()
except ImportError:
    _lint_collector = None

try:
    from pyqual.plugins.security import SecurityCollector
    _security_collector: SecurityCollector | None = SecurityCollector()
except ImportError:
    _security_collector = None

try:
    from pyqual.plugins.code_health import CodeHealthCollector
    _code_health_collector: CodeHealthCollector | None = CodeHealthCollector()
except ImportError:
    _code_health_collector = None


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
    """Extract test coverage using plugin if available, fallback to legacy."""
    if _coverage_collector:
        return _coverage_collector.collect(workdir)
    # Legacy fallback
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
            num_branches = data.get("totals", {}).get("num_branches")
            covered_branches = data.get("totals", {}).get("covered_branches")
            if num_branches and covered_branches is not None and num_branches > 0:
                result["coverage_branch"] = (covered_branches / num_branches) * 100
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return result


def _from_bandit(workdir: Path) -> dict[str, float]:
    """Extract security metrics using plugin if available."""
    if _security_collector:
        metrics = _security_collector.collect(workdir)
        # Map plugin names to legacy names
        return {
            "bandit_high": metrics.get("security_bandit_high", 0.0),
            "bandit_medium": metrics.get("security_bandit_medium", 0.0),
            "bandit_low": metrics.get("security_bandit_low", 0.0),
        }
    # Legacy fallback""
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
    """Extract secrets metrics from secrets.json."""
    sec_path = workdir / ".pyqual" / "secrets.json"
    
    # Only process if secrets.json exists
    if not sec_path.exists():
        return {}
    
    result: dict[str, float] = {}
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
            result["secrets_found"] = result["secrets_count"]
        elif isinstance(data, dict):
            # Handle dict format (e.g., detect-secrets output)
            findings = data.get("results", {})
            if isinstance(findings, dict):
                count = sum(len(v) for v in findings.values() if isinstance(v, list))
                result["secrets_count"] = float(count)
                result["secrets_found"] = float(count)
                result["secrets_severity"] = 3.0  # High severity for secrets
    except (json.JSONDecodeError, TypeError):
        pass
    return result


def _from_vulnerabilities(workdir: Path) -> dict[str, float]:
    """Extract vulnerability metrics using plugin if available."""
    if _security_collector:
        metrics = _security_collector.collect(workdir)
        return {
            "vuln_critical": metrics.get("security_vuln_critical", 0.0),
            "vuln_high": metrics.get("security_vuln_high", 0.0),
            "vuln_medium": metrics.get("security_vuln_moderate", 0.0),
        }
    # Legacy fallback
    result: dict[str, float] = {}
    vuln_path = workdir / ".pyqual" / "vulns.json"
    if vuln_path.exists():
        try:
            data = json.loads(vuln_path.read_text())
            if isinstance(data, list):
                critical = sum(1 for v in data if v.get("severity", "").lower() == "critical")
                high = sum(1 for v in data if v.get("severity", "").lower() == "high")
                medium = sum(1 for v in data if v.get("severity", "").lower() == "medium")
                result["vuln_critical"] = float(critical)
                result["vuln_high"] = float(high)
                result["vuln_medium"] = float(medium)
                result["vuln_count"] = float(len(data))
            elif isinstance(data, dict):
                vulns = data.get("vulnerabilities", [])
                critical = sum(1 for v in vulns if v.get("severity", "").lower() == "critical")
                high = sum(1 for v in vulns if v.get("severity", "").lower() == "high")
                medium = sum(1 for v in vulns if v.get("severity", "").lower() == "medium")
                result["vuln_critical"] = float(critical)
                result["vuln_high"] = float(high)
                result["vuln_medium"] = float(medium)
                result["vuln_count"] = float(len(vulns))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_security(workdir: Path) -> dict[str, float]:
    """Aggregate all security metrics using plugin if available."""
    if _security_collector:
        metrics = _security_collector.collect(workdir)
        # Map plugin metric names to legacy names
        return {
            "bandit_high": metrics.get("security_bandit_high", 0.0),
            "bandit_medium": metrics.get("security_bandit_medium", 0.0),
            "bandit_low": metrics.get("security_bandit_low", 0.0),
            "vuln_critical": metrics.get("security_vuln_critical", 0.0),
            "vuln_high": metrics.get("security_vuln_high", 0.0),
            "vuln_medium": metrics.get("security_vuln_moderate", 0.0),
            "secrets_found": metrics.get("security_secrets_found", 0.0),
            "safety_issues": metrics.get("security_safety_issues", 0.0),
        }
    # Aggregate legacy security metrics
    result: dict[str, float] = {}
    result.update(_from_bandit(workdir))
    result.update(_from_vulnerabilities(workdir))
    result.update(_from_secrets(workdir))
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
    """Extract code health metrics using plugin if available."""
    if _code_health_collector:
        metrics = _code_health_collector.collect(workdir)
        return {"unused_count": metrics.get("unused_count", 0.0)}
    # Legacy fallback""
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
    """Extract packaging quality using plugin if available."""
    if _code_health_collector:
        metrics = _code_health_collector.collect(workdir)
        return {"pyroma_score": metrics.get("pyroma_score", 0.0)}
    # Legacy fallback
    result: dict[str, float] = {}
    pyr_path = workdir / ".pyqual" / "pyroma.json"
    if pyr_path.exists():
        try:
            data = json.loads(pyr_path.read_text())
            score = data.get("score")
            if score is None:
                score = data.get("rating")
            if isinstance(score, (int, float)):
                result["pyroma_score"] = float(score)
            elif isinstance(score, str) and score.upper() in "ABCDEF":
                result["pyroma_score"] = float(6 - ord(score.upper()[0]) + ord("A"))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_code_health(workdir: Path) -> dict[str, float]:
    """Aggregate all code health metrics using plugin if available."""
    if _code_health_collector:
        return _code_health_collector.collect(workdir)
    # Aggregate legacy code health metrics
    result: dict[str, float] = {}
    result.update(_from_vulture(workdir))
    result.update(_from_pyroma(workdir))
    result.update(_from_radon(workdir))
    result.update(_from_interrogate(workdir))
    return result


def _from_git_health(workdir: Path) -> dict[str, float]:
    """Extract repository health metrics from git_metrics.json."""
    result: dict[str, float] = {}
    git_path = workdir / ".pyqual" / "git_metrics.json"
    if git_path.exists():
        try:
            data = json.loads(git_path.read_text())
            age = data.get("main_branch_age_days")
            if age is not None:
                result["git_branch_age"] = float(age)
            todos = data.get("todo_count")
            if todos is not None:
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
                    pass_at_1 = data.get("pass_at_1")
                    if pass_at_1 is None:
                        pass_at_1 = data.get("pass@1")
                    if pass_at_1 is not None:
                        result["llm_pass_rate"] = float(pass_at_1)
                else:
                    cc = data.get("avg_cyclomatic_complexity")
                    if cc is not None:
                        result["llm_cc"] = float(cc)
                    hal = data.get("hallucination_rate")
                    if hal is not None:
                        result["hallucination_rate"] = float(hal)
                    bias = data.get("prompt_bias_score")
                    if bias is not None:
                        result["prompt_bias_score"] = float(bias)
                    eff = data.get("agent_iterations")
                    if eff is None:
                        eff = data.get("agent_efficiency")
                    if eff is not None:
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
            cost = data.get("total_cost")
            if cost is None:
                cost = data.get("cost_usd")
            if cost is not None:
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
            elif isinstance(data, dict):
                results = data.get("results", {})
                if isinstance(results, dict) and results:
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
            peak = data.get("peak_memory_mb")
            if peak is None:
                peak = data.get("peak")
            if peak is not None:
                result["mem_usage"] = float(peak)
            cpu = data.get("cpu_time_s")
            if cpu is None:
                cpu = data.get("cpu_time")
            if cpu is not None:
                result["cpu_time"] = float(cpu)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _from_radon(workdir: Path) -> dict[str, float]:
    """Extract maintainability using plugin if available."""
    if _code_health_collector:
        metrics = _code_health_collector.collect(workdir)
        return {"maintainability_index": metrics.get("maintainability_index", 0.0)}
    # Legacy fallback""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "radon.json"
    if not p.exists():
        return result
    try:
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            scores = [
                float(v["mi"]) for v in data.values()
                if isinstance(v, dict) and "mi" in v
            ]
            if not scores:
                scores = [
                    float(entry["mi"])
                    for entries in data.values()
                    if isinstance(entries, list)
                    for entry in entries
                    if isinstance(entry, dict) and "mi" in entry
                ]
            if scores:
                result["maintainability_index"] = round(sum(scores) / len(scores), 2)
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        pass
    return result


def _from_mypy(workdir: Path) -> dict[str, float]:
    """Extract lint metrics using plugin if available."""
    if _lint_collector:
        metrics = _lint_collector.collect(workdir)
        return {"mypy_errors": metrics.get("mypy_errors", 0.0)}
    # Legacy fallback""
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


def _from_lint(workdir: Path) -> dict[str, float]:
    """Extract lint metrics using plugin if available."""
    if _lint_collector:
        return _lint_collector.collect(workdir)
    # Aggregate legacy lint metrics
    result: dict[str, float] = {}
    result.update(_from_ruff(workdir))
    result.update(_from_mypy(workdir))
    result.update(_from_pylint(workdir))
    result.update(_from_flake8(workdir))
    return result


# Legacy individual lint collectors (used by _from_lint fallback)
def _from_ruff(workdir: Path) -> dict[str, float]:
    """Extract lint metrics using plugin if available."""
    if _lint_collector:
        metrics = _lint_collector.collect(workdir)
        return {
            "ruff_errors": metrics.get("ruff_errors", 0.0),
            "ruff_fatal": metrics.get("ruff_fatal", 0.0),
            "ruff_warnings": metrics.get("ruff_warnings", 0.0),
        }
    # Legacy fallback""
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
    """Extract lint metrics using plugin if available."""
    if _lint_collector:
        metrics = _lint_collector.collect(workdir)
        return {
            "pylint_errors": metrics.get("pylint_errors", 0.0),
            "pylint_fatal": metrics.get("pylint_fatal", 0.0),
            "pylint_warnings": metrics.get("pylint_warnings", 0.0),
            "pylint_score": metrics.get("pylint_score", 0.0),
        }
    # Legacy fallback""
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
        score = data.get("score")
        if score is None:
            score = data.get("rating")
        if score is not None:
            result["pylint_score"] = float(score)
        messages = data.get("messages", [])
        result["pylint_errors"] = float(len(messages))
    return result


def _from_flake8(workdir: Path) -> dict[str, float]:
    """Extract lint metrics using plugin if available."""
    if _lint_collector:
        metrics = _lint_collector.collect(workdir)
        return {
            "flake8_violations": metrics.get("flake8_violations", 0.0),
            "flake8_errors": metrics.get("flake8_errors", 0.0),
            "flake8_warnings": metrics.get("flake8_warnings", 0.0),
        }
    # Legacy fallback""
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


def _from_runtime_errors(workdir: Path) -> dict[str, float]:
    """Extract runtime error metrics from runtime_errors.json."""
    result: dict[str, float] = {}
    errors_path = workdir / ".pyqual" / "runtime_errors.json"
    if errors_path.exists():
        try:
            errors = json.loads(errors_path.read_text())
            if isinstance(errors, list):
                result["runtime_errors"] = float(len(errors))
                # Count by error type
                error_types = {}
                for error in errors:
                    error_type = error.get("error_type", "unknown")
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                # Expose common error types as metrics
                for error_type, count in error_types.items():
                    metric_name = f"runtime_{error_type}"
                    result[metric_name] = float(count)
                
                # Check for recent errors (last hour)
                from datetime import datetime, timezone, timedelta
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                recent_count = sum(
                    1 for error in errors
                    if datetime.fromisoformat(error.get("timestamp", "").replace("Z", "+00:00")) > one_hour_ago
                )
                result["runtime_errors_recent"] = float(recent_count)
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            pass
    return result


def _from_interrogate(workdir: Path) -> dict[str, float]:
    """Extract docstring metrics using plugin if available."""
    if _code_health_collector:
        metrics = _code_health_collector.collect(workdir)
        return {
            "docstring_coverage": metrics.get("docstring_coverage", 0.0),
            "docstring_total": metrics.get("docstring_total", 0.0),
            "docstring_missing": metrics.get("docstring_missing", 0.0),
        }
    # Legacy fallback""
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "interrogate.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            coverage = data.get("coverage")
            if coverage is None:
                coverage = data.get("percent_covered")
            if coverage is not None:
                result["docstring_coverage"] = float(coverage)
            total = data.get("total")
            if total is None:
                total = data.get("total_objects")
            documented = data.get("documented")
            if documented is None:
                documented = data.get("documented_objects")
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
    _from_runtime_errors,
    _from_secrets,
    _from_vulnerabilities,
    _from_bandit,
    _from_sbom,
    _from_vulture,
    _from_pyroma,
    _from_git_health,
    _from_llm_quality,
    _from_ai_cost,
    _from_radon,
    _from_mypy,
    _from_ruff,
    _from_pylint,
    _from_flake8,
    _from_interrogate,
]
