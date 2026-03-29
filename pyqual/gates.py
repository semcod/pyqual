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

    @staticmethod
    def _read_artifact_text(workdir: Path, filenames: list[str]) -> str | None:
        for base in (workdir, workdir / "project"):
            for name in filenames:
                p = base / name
                if p.exists():
                    try:
                        return p.read_text()
                    except OSError:
                        continue
        return None

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
        metrics.update(self._from_benchmark(workdir))
        metrics.update(self._from_memory_profile(workdir))
        metrics.update(self._from_secrets(workdir))
        metrics.update(self._from_vulnerabilities(workdir))
        metrics.update(self._from_bandit(workdir))
        metrics.update(self._from_sbom(workdir))
        metrics.update(self._from_vulture(workdir))
        metrics.update(self._from_pyroma(workdir))
        metrics.update(self._from_git_health(workdir))
        metrics.update(self._from_llm_quality(workdir))
        metrics.update(self._from_ai_cost(workdir))
        metrics.update(self._from_mypy(workdir))
        metrics.update(self._from_ruff(workdir))
        metrics.update(self._from_pylint(workdir))
        metrics.update(self._from_flake8(workdir))
        metrics.update(self._from_interrogate(workdir))

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

    def _from_toon(self, workdir: Path) -> dict[str, float]:
        """Extract CC̄ and critical count from analysis_toon.yaml or analysis.toon."""
        result: dict[str, float] = {}
        text = self._read_artifact_text(
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

    def _from_vallm(self, workdir: Path) -> dict[str, float]:
        """Extract vallm pass rate from validation_toon.yaml or errors.json."""
        result: dict[str, float] = {}
        text = self._read_artifact_text(workdir, ["validation.toon.yaml", "validation_toon.yaml", "validation.toon"])
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

    def _from_safety(self, workdir: Path) -> dict[str, float]:
        """Extract vulnerability counts from pip-audit/safety JSON output."""
        result: dict[str, float] = {}
        for fname in ["safety.json", "pip_audit.json"]:
            p = workdir / ".pyqual" / fname
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text())
                if isinstance(data, dict) and "vulnerabilities" in data:
                    vulns = data["vulnerabilities"]
                elif isinstance(data, list):
                    vulns = data
                else:
                    continue
                critical = high = medium = low = 0
                for v in vulns:
                    severity = v.get("severity", v.get("vulnerability_severity", "")).lower()
                    if "critical" in severity:
                        critical += 1
                    elif "high" in severity:
                        high += 1
                    elif "medium" in severity:
                        medium += 1
                    elif "low" in severity:
                        low += 1
                result["vuln_critical"] = float(critical)
                result["vuln_high"] = float(high)
                result["vuln_medium"] = float(medium)
                result["vuln_low"] = float(low)
                result["vuln_total"] = float(len(vulns))
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return result

    def _from_bandit(self, workdir: Path) -> dict[str, float]:
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

    def _from_secrets(self, workdir: Path) -> dict[str, float]:
        """Extract leaked secrets count from trufflehog/gitleaks JSON."""
        result: dict[str, float] = {}
        for fname in ["trufflehog.json", "gitleaks.json", "secrets.json"]:
            p = workdir / ".pyqual" / fname
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get("findings", data.get("results", [])))
                else:
                    count = 0
                result["secrets_found"] = float(count)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_pip_outdated(self, workdir: Path) -> dict[str, float]:
        """Extract outdated dependency counts from pip list --outdated JSON."""
        result: dict[str, float] = {}
        p = workdir / ".pyqual" / "outdated.json"
        if p.exists():
            try:
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    result["outdated_deps"] = float(len(data))
                elif isinstance(data, dict) and "packages" in data:
                    result["outdated_deps"] = float(len(data["packages"]))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_radon(self, workdir: Path) -> dict[str, float]:
        """Extract maintainability index and complexity from radon JSON."""
        result: dict[str, float] = {}
        for fname in ["radon_mi.json", "radon_cc.json"]:
            p = workdir / ".pyqual" / fname
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text())
                if "mi" in fname and isinstance(data, dict):
                    mi_values = [v.get("mi", 0) for v in data.values() if isinstance(v, dict)]
                    if mi_values:
                        result["mi_avg"] = float(sum(mi_values) / len(mi_values))
                        result["mi_min"] = float(min(mi_values))
                elif "cc" in fname and isinstance(data, dict):
                    cc_values = [v.get("rank", 0) for v in data.values() if isinstance(v, dict)]
                    if cc_values:
                        result["cc_rank_avg"] = float(sum(cc_values) / len(cc_values))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_mypy(self, workdir: Path) -> dict[str, float]:
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

    def _from_pytest_durations(self, workdir: Path) -> dict[str, float]:
        """Extract test execution time and slow test count from pytest JSON."""
        result: dict[str, float] = {}
        p = workdir / ".pyqual" / "pytest_durations.json"
        if p.exists():
            try:
                data = json.loads(p.read_text())
                total_time = data.get("duration", 0)
                slow_tests = len([t for t in data.get("tests", []) if t.get("duration", 0) > 1.0])
                result["test_time"] = float(total_time)
                result["slow_tests"] = float(slow_tests)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_benchmark(self, workdir: Path) -> dict[str, float]:
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

    def _from_memory_profile(self, workdir: Path) -> dict[str, float]:
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

    def _from_secrets(self, workdir: Path) -> dict[str, float]:
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

    def _from_vulnerabilities(self, workdir: Path) -> dict[str, float]:
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

    def _from_sbom(self, workdir: Path) -> dict[str, float]:
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

    def _from_vulture(self, workdir: Path) -> dict[str, float]:
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

    def _from_pyroma(self, workdir: Path) -> dict[str, float]:
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

    def _from_git_health(self, workdir: Path) -> dict[str, float]:
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

    def _from_llm_quality(self, workdir: Path) -> dict[str, float]:
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

    def _from_ai_cost(self, workdir: Path) -> dict[str, float]:
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

    def _from_ruff(self, workdir: Path) -> dict[str, float]:
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

    def _from_pylint(self, workdir: Path) -> dict[str, float]:
        """Extract pylint score and error counts from JSON output."""
        result: dict[str, float] = {}
        p = workdir / ".pyqual" / "pylint.json"
        if p.exists():
            try:
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    errors = len(data)
                    fatal = sum(1 for m in data if m.get("type") == "fatal" or str(m.get("symbol", "")).startswith("F"))
                    error = sum(1 for m in data if m.get("type") == "error" or str(m.get("symbol", "")).startswith("E"))
                    warning = sum(1 for m in data if m.get("type") == "warning" or str(m.get("symbol", "")).startswith("W"))
                    result["pylint_errors"] = float(errors)
                    result["pylint_fatal"] = float(fatal)
                    result["pylint_error"] = float(error)
                    result["pylint_warnings"] = float(warning)
                elif isinstance(data, dict):
                    score = data.get("score") or data.get("rating")
                    if score:
                        result["pylint_score"] = float(score)
                    messages = data.get("messages", [])
                    result["pylint_errors"] = float(len(messages))
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _from_flake8(self, workdir: Path) -> dict[str, float]:
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

    def _from_interrogate(self, workdir: Path) -> dict[str, float]:
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
