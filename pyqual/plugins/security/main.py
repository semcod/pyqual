"""Security plugin for pyqual — comprehensive security scanning.

This plugin provides security analysis through multiple tools:
- bandit: Python security linter
- safety: Dependency vulnerability scanner
- pip-audit: PyPI audit for known CVEs
- detect-secrets: Credential scanning
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class SecurityCollector(MetricCollector):
    """Security metrics collector — aggregates findings from security scanners."""

    name = "security"
    metadata = PluginMetadata(
        name="security",
        description="Security scanning: bandit, pip-audit, safety, detect-secrets integration",
        version="1.0.0",
        tags=["security", "vulnerability", "bandit", "audit", "secrets", "safety"],
        config_example="""
metrics:
  security_bandit_high_max: 0        # Bandit HIGH severity issues
  security_bandit_medium_max: 5      # Bandit MEDIUM severity issues
  security_vuln_high_max: 0          # pip-audit HIGH severity CVEs
  security_vuln_critical_max: 0        # pip-audit CRITICAL severity CVEs
  security_secrets_found_max: 0      # detect-secrets findings
  security_safety_issues_max: 0        # safety package vulnerabilities

stages:
  - name: security_bandit
    run: bandit -r pyqual -f json -o .pyqual/bandit.json || true

  - name: security_audit
    run: pip-audit --format=json --output=.pyqual/audit.json || echo '[]' > .pyqual/audit.json

  - name: security_secrets
    run: detect-secrets scan --all-files > .pyqual/secrets.json || echo '{"results":{}}' > .pyqual/secrets.json

  - name: security_safety
    run: safety check --json > .pyqual/safety.json || echo '[]' > .pyqual/safety.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect security metrics from various scanner outputs."""
        result: dict[str, float] = {}

        # Bandit results
        self._collect_bandit(workdir, result)

        # pip-audit results
        self._collect_audit(workdir, result)

        # detect-secrets results
        self._collect_secrets(workdir, result)

        # safety results
        self._collect_safety(workdir, result)

        return result

    def _collect_bandit(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract bandit security metrics."""
        bandit_path = workdir / ".pyqual" / "bandit.json"
        if not bandit_path.exists():
            result["security_bandit_high"] = 0.0
            result["security_bandit_medium"] = 0.0
            result["security_bandit_low"] = 0.0
            return

        try:
            data = json.loads(bandit_path.read_text())
            results = data.get("results", [])
            
            result["security_bandit_high"] = float(
                len([r for r in results if r.get("issue_severity") == "HIGH"])
            )
            result["security_bandit_medium"] = float(
                len([r for r in results if r.get("issue_severity") == "MEDIUM"])
            )
            result["security_bandit_low"] = float(
                len([r for r in results if r.get("issue_severity") == "LOW"])
            )
            result["security_bandit_confidence_high"] = float(
                len([r for r in results if r.get("issue_confidence") == "HIGH"])
            )
        except (json.JSONDecodeError, TypeError):
            result["security_bandit_high"] = 0.0
            result["security_bandit_medium"] = 0.0
            result["security_bandit_low"] = 0.0

    def _collect_audit(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract pip-audit vulnerability metrics."""
        audit_path = workdir / ".pyqual" / "audit.json"
        if not audit_path.exists():
            result["security_vuln_critical"] = 0.0
            result["security_vuln_high"] = 0.0
            result["security_vuln_moderate"] = 0.0
            return

        try:
            data = json.loads(audit_path.read_text())
            if isinstance(data, dict):
                vulnerabilities = data.get("vulnerabilities", [])
            else:
                vulnerabilities = data if isinstance(data, list) else []
            
            result["security_vuln_critical"] = float(
                len([v for v in vulnerabilities if self._get_severity(v) == "CRITICAL"])
            )
            result["security_vuln_high"] = float(
                len([v for v in vulnerabilities if self._get_severity(v) == "HIGH"])
            )
            result["security_vuln_moderate"] = float(
                len([v for v in vulnerabilities if self._get_severity(v) in ("MODERATE", "MEDIUM")])
            )
        except (json.JSONDecodeError, TypeError):
            result["security_vuln_critical"] = 0.0
            result["security_vuln_high"] = 0.0
            result["security_vuln_moderate"] = 0.0

    def _get_severity(self, vuln: dict[str, Any]) -> str:
        """Extract severity from vulnerability data."""
        if isinstance(vuln, dict):
            severity = vuln.get("severity", vuln.get("fixed_versions", ""))
            if isinstance(severity, str):
                return severity.upper()
        return "UNKNOWN"

    def _collect_secrets(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract detect-secrets findings."""
        secrets_path = workdir / ".pyqual" / "secrets.json"
        if not secrets_path.exists():
            result["security_secrets_found"] = 0.0
            return

        try:
            data = json.loads(secrets_path.read_text())
            if isinstance(data, dict):
                findings = data.get("results", {})
                count = sum(len(v) for v in findings.values() if isinstance(v, list))
            else:
                count = len(data) if isinstance(data, list) else 0
            result["security_secrets_found"] = float(count)
        except (json.JSONDecodeError, TypeError):
            result["security_secrets_found"] = 0.0

    def _collect_safety(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract safety check vulnerabilities."""
        safety_path = workdir / ".pyqual" / "safety.json"
        if not safety_path.exists():
            result["security_safety_issues"] = 0.0
            return

        try:
            data = json.loads(safety_path.read_text())
            if isinstance(data, list):
                result["security_safety_issues"] = float(len(data))
            elif isinstance(data, dict):
                vulnerabilities = data.get("vulnerabilities", [])
                result["security_safety_issues"] = float(len(vulnerabilities))
            else:
                result["security_safety_issues"] = 0.0
        except (json.JSONDecodeError, TypeError):
            result["security_safety_issues"] = 0.0

    def get_config_example(self) -> str:
        """Return ready-to-use YAML configuration."""
        return self.metadata.config_example


def run_bandit_check(
    paths: list[str] | None = None,
    severity: str = "medium",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run bandit security check on Python code.
    
    Args:
        paths: List of paths to scan (defaults to ["."])
        severity: Minimum severity to report (low/medium/high)
        cwd: Working directory
        
    Returns:
        Dict with scan results
    """
    paths = paths or ["."]
    
    cmd = [
        "bandit", "-r",
        *paths,
        "-f", "json",
        "-ll" if severity == "low" else "-lll" if severity == "high" else "-ll",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode in (0, 1):  # 0 = no issues, 1 = issues found
            try:
                data = json.loads(result.stdout) if result.stdout else {}
                return {
                    "success": True,
                    "issues": data.get("results", []),
                    "metrics": data.get("metrics", {}),
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse bandit output",
                    "issues": [],
                }
        else:
            return {
                "success": False,
                "error": result.stderr or f"Bandit exit code: {result.returncode}",
                "issues": [],
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "bandit not found — install with: pip install bandit",
            "issues": [],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Bandit scan timed out",
            "issues": [],
        }


def run_pip_audit(
    output_format: str = "json",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run pip-audit to check for known vulnerabilities.
    
    Args:
        output_format: Output format (json/markdown)
        cwd: Working directory
        
    Returns:
        Dict with audit results
    """
    cmd = ["pip-audit"]
    
    if output_format == "json":
        cmd.extend(["--format=json"])
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode in (0, 1):  # 0 = no vulns, 1 = vulns found
            if output_format == "json" and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return {
                        "success": True,
                        "vulnerabilities": data if isinstance(data, list) else data.get("vulnerabilities", []),
                        "dependencies_scanned": len(data) if isinstance(data, list) else 0,
                    }
                except json.JSONDecodeError:
                    pass
            
            return {
                "success": True,
                "vulnerabilities": [],
                "dependencies_scanned": 0,
            }
        else:
            return {
                "success": False,
                "error": result.stderr or f"pip-audit exit code: {result.returncode}",
                "vulnerabilities": [],
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pip-audit not found — install with: pip install pip-audit",
            "vulnerabilities": [],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "pip-audit timed out",
            "vulnerabilities": [],
        }


def run_detect_secrets(
    baseline_file: str | None = None,
    all_files: bool = True,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run detect-secrets to find potential secrets.
    
    Args:
        baseline_file: Path to baseline file for comparison
        all_files: Scan all files (not just staged)
        cwd: Working directory
        
    Returns:
        Dict with scan results
    """
    cmd = ["detect-secrets", "scan"]
    
    if all_files:
        cmd.append("--all-files")
    
    if baseline_file:
        cmd.extend(["--baseline", baseline_file])
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                findings = data.get("results", {})
                total = sum(len(v) for v in findings.values() if isinstance(v, list))
                
                return {
                    "success": True,
                    "findings": findings,
                    "total_findings": total,
                    "baseline_present": bool(data.get("baseline")),
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "findings": {},
                    "total_findings": 0,
                    "baseline_present": False,
                }
        else:
            return {
                "success": False,
                "error": result.stderr or f"detect-secrets exit code: {result.returncode}",
                "findings": {},
                "total_findings": 0,
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "detect-secrets not found — install with: pip install detect-secrets",
            "findings": {},
            "total_findings": 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "detect-secrets scan timed out",
            "findings": {},
            "total_findings": 0,
        }


def security_summary(workdir: Path | None = None) -> dict[str, Any]:
    """Generate comprehensive security summary.
    
    Returns aggregated metrics from all security tools.
    """
    workdir = workdir or Path.cwd()
    
    collector = SecurityCollector()
    metrics = collector.collect(workdir)
    
    total_issues = (
        metrics.get("security_bandit_high", 0)
        + metrics.get("security_vuln_critical", 0)
        + metrics.get("security_vuln_high", 0)
        + metrics.get("security_secrets_found", 0)
    )
    
    return {
        "success": True,
        "metrics": metrics,
        "total_issues": int(total_issues),
        "is_secure": total_issues == 0,
        "tools_checked": ["bandit", "pip-audit", "detect-secrets"],
    }
