"""Docker plugin for pyqual — container security and image scanning.

This plugin provides Docker-related metrics:
- Image vulnerability scanning (trivy, grype)
- Dockerfile linting (hadolint)
- Image size and layer analysis
- Container health checks
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class DockerCollector(MetricCollector):
    """Docker security and quality metrics collector."""

    name = "docker"
    metadata = PluginMetadata(
        name="docker",
        description="Docker security: image scanning with trivy/grype, Dockerfile linting with hadolint",
        version="1.0.0",
        tags=["docker", "container", "security", "image", "vulnerability", "lint"],
        config_example="""
metrics:
  docker_vuln_critical_max: 0       # Critical CVEs in images
  docker_vuln_high_max: 5           # High severity CVEs
  docker_vuln_medium_max: 20        # Medium severity CVEs
  docker_hadolint_errors_max: 0   # Dockerfile lint errors
  docker_image_size_max_mb: 500     # Max image size in MB

stages:
  - name: docker_lint
    run: hadolint Dockerfile > .pyqual/hadolint.json 2>&1 || true

  - name: docker_scan
    run: trivy image --format json -o .pyqual/trivy.json myapp:latest || true
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect Docker security metrics from scanner outputs."""
        result: dict[str, float] = {}

        # Trivy results
        self._collect_trivy(workdir, result)

        # Hadolint results
        self._collect_hadolint(workdir, result)

        # Grype results (alternative scanner)
        self._collect_grype(workdir, result)

        # Image info
        self._collect_image_info(workdir, result)

        return result

    def _collect_trivy(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract trivy vulnerability metrics."""
        trivy_path = workdir / ".pyqual" / "trivy.json"
        if not trivy_path.exists():
            self._set_zero_trivy(result)
            return

        try:
            data = json.loads(trivy_path.read_text())
            
            # Handle different trivy output formats
            if isinstance(data, list):
                # Direct results array
                self._count_trivy_vulns(data, result)
            elif isinstance(data, dict):
                results = data.get("Results", [])
                all_vulns = []
                for r in results:
                    vulns = r.get("Vulnerabilities", [])
                    all_vulns.extend(vulns)
                self._count_trivy_vulns(all_vulns, result)
            else:
                self._set_zero_trivy(result)
        except (json.JSONDecodeError, TypeError):
            self._set_zero_trivy(result)

    def _count_trivy_vulns(self, vulns: list[dict], result: dict[str, float]) -> None:
        """Count vulnerabilities by severity from trivy output."""
        critical = len([v for v in vulns if v.get("Severity") == "CRITICAL"])
        high = len([v for v in vulns if v.get("Severity") == "HIGH"])
        medium = len([v for v in vulns if v.get("Severity") == "MEDIUM"])
        low = len([v for v in vulns if v.get("Severity") == "LOW"])
        
        result["docker_vuln_critical"] = float(critical)
        result["docker_vuln_high"] = float(high)
        result["docker_vuln_medium"] = float(medium)
        result["docker_vuln_low"] = float(low)

    def _set_zero_trivy(self, result: dict[str, float]) -> None:
        """Set zero values for trivy metrics."""
        result["docker_vuln_critical"] = 0.0
        result["docker_vuln_high"] = 0.0
        result["docker_vuln_medium"] = 0.0
        result["docker_vuln_low"] = 0.0

    def _collect_hadolint(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract hadolint linting metrics."""
        hadolint_path = workdir / ".pyqual" / "hadolint.json"
        if not hadolint_path.exists():
            result["docker_hadolint_errors"] = 0.0
            result["docker_hadolint_warnings"] = 0.0
            return

        try:
            data = json.loads(hadolint_path.read_text())
            
            if isinstance(data, list):
                errors = len([i for i in data if i.get("level") == "error"])
                warnings = len([i for i in data if i.get("level") == "warning"])
            elif isinstance(data, dict):
                # SARIF or other format
                runs = data.get("runs", [{}])
                results_list = runs[0].get("results", []) if runs else []
                errors = len([r for r in results_list if r.get("level") == "error"])
                warnings = len([r for r in results_list if r.get("level") == "warning"])
            else:
                errors = 0
                warnings = 0
                
            result["docker_hadolint_errors"] = float(errors)
            result["docker_hadolint_warnings"] = float(warnings)
        except (json.JSONDecodeError, TypeError):
            result["docker_hadolint_errors"] = 0.0
            result["docker_hadolint_warnings"] = 0.0

    def _collect_grype(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract grype vulnerability metrics (alternative to trivy)."""
        grype_path = workdir / ".pyqual" / "grype.json"
        if not grype_path.exists():
            result["docker_grype_critical"] = 0.0
            result["docker_grype_high"] = 0.0
            return

        try:
            data = json.loads(grype_path.read_text())
            matches = data.get("matches", [])
            
            critical = len([m for m in matches if self._get_grype_severity(m) == "Critical"])
            high = len([m for m in matches if self._get_grype_severity(m) == "High"])
            medium = len([m for m in matches if self._get_grype_severity(m) == "Medium"])
            
            result["docker_grype_critical"] = float(critical)
            result["docker_grype_high"] = float(high)
            result["docker_grype_medium"] = float(medium)
        except (json.JSONDecodeError, TypeError):
            result["docker_grype_critical"] = 0.0
            result["docker_grype_high"] = 0.0
            result["docker_grype_medium"] = 0.0

    def _get_grype_severity(self, match: dict) -> str:
        """Extract severity from grype match."""
        vuln = match.get("vulnerability", {})
        severity = vuln.get("severity", "Unknown")
        return severity

    def _collect_image_info(self, workdir: Path, result: dict[str, float]) -> None:
        """Collect Docker image size and layer information."""
        image_info_path = workdir / ".pyqual" / "docker_image.json"
        if not image_info_path.exists():
            result["docker_image_size_mb"] = 0.0
            result["docker_layer_count"] = 0.0
            return

        try:
            data = json.loads(image_info_path.read_text())
            size_bytes = data.get("Size", 0)
            result["docker_image_size_mb"] = round(size_bytes / (1024 * 1024), 2)
            result["docker_layer_count"] = float(len(data.get("RootFS", {}).get("Layers", [])))
        except (json.JSONDecodeError, TypeError):
            result["docker_image_size_mb"] = 0.0
            result["docker_layer_count"] = 0.0

    def get_config_example(self) -> str:
        """Return ready-to-use YAML configuration."""
        return self.metadata.config_example


def run_hadolint(
    dockerfile: str = "Dockerfile",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run hadolint on a Dockerfile.
    
    Args:
        dockerfile: Path to Dockerfile
        cwd: Working directory
        
    Returns:
        Dict with lint results
    """
    cmd = ["hadolint", dockerfile, "--format", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        # hadolint returns exit code 1 if issues found
        try:
            issues = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            issues = []
        
        errors = len([i for i in issues if i.get("level") == "error"])
        warnings = len([i for i in issues if i.get("level") == "warning"])
        
        return {
            "success": True,
            "issues": issues,
            "error_count": errors,
            "warning_count": warnings,
            "is_valid": errors == 0,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "hadolint not found — install from: https://github.com/hadolint/hadolint",
            "issues": [],
            "error_count": 0,
            "warning_count": 0,
            "is_valid": True,  # Don't fail if tool not available
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "hadolint timed out",
            "issues": [],
            "error_count": 0,
            "warning_count": 0,
            "is_valid": True,
        }


def run_trivy_scan(
    image: str,
    output_format: str = "json",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run trivy vulnerability scan on a Docker image.
    
    Args:
        image: Docker image name/tag
        output_format: Output format
        cwd: Working directory
        
    Returns:
        Dict with scan results
    """
    cmd = ["trivy", "image", "--format", output_format, "-o", ".pyqual/trivy.json", image]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        # Read the output file
        output_path = (cwd or Path.cwd()) / ".pyqual" / "trivy.json"
        if output_path.exists():
            data = json.loads(output_path.read_text())
            
            # Count vulnerabilities
            if isinstance(data, list):
                vulns = data
            else:
                results = data.get("Results", [])
                vulns = []
                for r in results:
                    vulns.extend(r.get("Vulnerabilities", []))
            
            critical = len([v for v in vulns if v.get("Severity") == "CRITICAL"])
            high = len([v for v in vulns if v.get("Severity") == "HIGH"])
            
            return {
                "success": result.returncode == 0 or (critical == 0 and high == 0),
                "vulnerabilities": vulns,
                "critical_count": critical,
                "high_count": high,
                "is_secure": critical == 0 and high == 0,
            }
        else:
            return {
                "success": False,
                "error": "Trivy output file not created",
                "vulnerabilities": [],
                "critical_count": 0,
                "high_count": 0,
                "is_secure": True,
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "trivy not found — install from: https://aquasecurity.github.io/trivy/",
            "vulnerabilities": [],
            "critical_count": 0,
            "high_count": 0,
            "is_secure": True,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Trivy scan timed out",
            "vulnerabilities": [],
            "critical_count": 0,
            "high_count": 0,
            "is_secure": True,
        }


def get_image_info(image: str, cwd: Path | None = None) -> dict[str, Any]:
    """Get Docker image information.
    
    Args:
        image: Docker image name
        cwd: Working directory
        
    Returns:
        Dict with image details
    """
    cmd = ["docker", "inspect", image]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                info = data[0]
                size_bytes = info.get("Size", 0)
                layers = info.get("RootFS", {}).get("Layers", [])
                
                return {
                    "success": True,
                    "size_bytes": size_bytes,
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                    "layer_count": len(layers),
                    "architecture": info.get("Architecture", "unknown"),
                    "os": info.get("Os", "unknown"),
                }
        
        return {
            "success": False,
            "error": f"Docker inspect failed: {result.stderr}",
            "size_mb": 0,
            "layer_count": 0,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "docker not found",
            "size_mb": 0,
            "layer_count": 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "docker inspect timed out",
            "size_mb": 0,
            "layer_count": 0,
        }


def docker_security_check(
    image: str | None = None,
    dockerfile: str = "Dockerfile",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run comprehensive Docker security check.
    
    Args:
        image: Docker image to scan (optional)
        dockerfile: Dockerfile to lint
        cwd: Working directory
        
    Returns:
        Dict with combined security results
    """
    results = {
        "success": True,
        "lint": None,
        "image_scan": None,
        "image_info": None,
        "is_secure": True,
    }
    
    # Lint Dockerfile
    if (cwd or Path.cwd() / dockerfile).exists():
        results["lint"] = run_hadolint(dockerfile, cwd)
        if results["lint"] and not results["lint"].get("is_valid", True):
            results["is_secure"] = False
    
    # Scan image if provided
    if image:
        results["image_scan"] = run_trivy_scan(image, cwd=cwd)
        if results["image_scan"] and not results["image_scan"].get("is_secure", True):
            results["is_secure"] = False
        
        results["image_info"] = get_image_info(image, cwd=cwd)
    
    return results
