import json
import re
from pathlib import Path
from .utils import _read_artifact_text

def _from_toon(workdir: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    text = _read_artifact_text(workdir, ["analysis.toon.yaml", "analysis_toon.yaml", "analysis.toon", "project_toon.yaml"])
    if not text: return result
    cc_match = re.search(r"CC̄[=:]?\s*([\d.]+)", text)
    if cc_match: result["cc"] = float(cc_match.group(1))
    crit_match = re.search(r"critical[=:]?\s*(\d+)", text)
    if crit_match: result["critical"] = float(crit_match.group(1))
    return result

def _from_vallm(workdir: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    text = _read_artifact_text(workdir, ["validation.toon.yaml", "validation_toon.yaml", "validation.toon"])
    if text:
        pass_match = re.search(r"passed:\s*(\d+)\s*\(([\d.]+)%\)", text)
        if pass_match: result["vallm_pass"] = float(pass_match.group(2))
    errors_path = workdir / ".pyqual" / "errors.json"
    if errors_path.exists():
        try:
            errors = json.loads(errors_path.read_text())
            if isinstance(errors, list): result["error_count"] = float(len(errors))
        except (json.JSONDecodeError, TypeError): pass
    return result

def _from_coverage(workdir: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    cov_path = workdir / ".pyqual" / "coverage.json"
    if not cov_path.exists(): cov_path = workdir / "coverage.json"
    if cov_path.exists():
        try:
            data = json.loads(cov_path.read_text())
            total = data.get("totals", {}).get("percent_covered")
            if total is not None: result["coverage"] = float(total)
        except (json.JSONDecodeError, TypeError, KeyError): pass
    return result

def _from_bandit(workdir: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    p = workdir / ".pyqual" / "bandit.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            results = data.get("results", [])
            result["bandit_high"] = float(sum(1 for r in results if r.get("issue_severity") == "HIGH"))
            result["bandit_medium"] = float(sum(1 for r in results if r.get("issue_severity") == "MEDIUM"))
            result["bandit_low"] = float(sum(1 for r in results if r.get("issue_severity") == "LOW"))
        except (json.JSONDecodeError, TypeError, KeyError): pass
    return result

def _from_secrets(workdir: Path) -> dict[str, float]:
    sec_path = workdir / ".pyqual" / "secrets.json"
    if not sec_path.exists(): return {}
    result: dict[str, float] = {}
    try:
        data = json.loads(sec_path.read_text())
        if isinstance(data, list):
            result["secrets_severity"] = float(max([{"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f.get("severity", "").lower(), 0) for f in data], default=0))
            result["secrets_count"] = float(len(data))
        elif isinstance(data, dict):
            count = sum(len(v) for v in data.get("results", {}).values() if isinstance(v, list))
            result["secrets_count"] = float(count)
    except (json.JSONDecodeError, TypeError): pass
    return result

def _from_vulnerabilities(workdir: Path) -> dict[str, float]:
    vuln_path = workdir / ".pyqual" / "vulns.json"
    if not vuln_path.exists(): return {}
    result: dict[str, float] = {}
    try:
        data = json.loads(vuln_path.read_text())
        if isinstance(data, list):
            result["vuln_critical"] = float(sum(1 for v in data if v.get("severity", "").lower() == "critical"))
            result["vuln_high"] = float(sum(1 for v in data if v.get("severity", "").lower() == "high"))
            result["vuln_medium"] = float(sum(1 for v in data if v.get("severity", "").lower() == "medium"))
    except (json.JSONDecodeError, TypeError): pass
    return result