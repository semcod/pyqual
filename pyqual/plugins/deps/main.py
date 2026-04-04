"""Deps plugin for pyqual — dependency management and freshness.

This plugin provides dependency analysis:
- Outdated package detection (pip list --outdated)
- Dependency tree analysis (pipdeptree)
- Requirements file validation
- License compatibility checking
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class DepsCollector(MetricCollector):
    """Dependency management metrics collector."""

    name = "deps"
    metadata = PluginMetadata(
        name="deps",
        description="Dependency management: outdated packages, dependency tree, requirements validation",
        version="1.0.0",
        tags=["dependencies", "outdated", "packages", "pip", "requirements", "licenses"],
        config_example="""
metrics:
  deps_outdated_max: 10             # Max outdated packages
  deps_vulnerable_max: 0           # Max known vulnerable deps
  deps_missing_reqs_max: 0          # Missing requirements entries
  deps_direct_deps_max: 50        # Max direct dependencies
  deps_licenses_unknown_max: 5      # Unknown license count

stages:
  - name: deps_check
    run: |
      pip list --outdated --format=json > .pyqual/outdated.json 2>&1 || echo '[]' > .pyqual/outdated.json
      pipdeptree --json > .pyqual/deptree.json 2>&1 || echo '{}' > .pyqual/deptree.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect dependency metrics from various sources."""
        result: dict[str, float] = {}

        # Outdated packages
        self._collect_outdated(workdir, result)

        # Dependency tree
        self._collect_deptree(workdir, result)

        # Requirements validation
        self._collect_requirements(workdir, result)

        # License analysis
        self._collect_licenses(workdir, result)

        return result

    def _collect_outdated(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract outdated package metrics."""
        outdated_path = workdir / ".pyqual" / "outdated.json"
        if not outdated_path.exists():
            result["deps_outdated_count"] = 0.0
            result["deps_outdated_major"] = 0.0
            return

        try:
            data = json.loads(outdated_path.read_text())
            
            if isinstance(data, list):
                outdated = data
            elif isinstance(data, dict):
                outdated = data.get("packages", [])
            else:
                outdated = []
            
            # Count total outdated
            result["deps_outdated_count"] = float(len(outdated))
            
            # Count major version outdated
            major_outdated = 0
            for pkg in outdated:
                current = pkg.get("version", "0.0.0")
                latest = pkg.get("latest_version", "0.0.0")
                
                try:
                    current_major = int(current.split(".")[0])
                    latest_major = int(latest.split(".")[0])
                    if latest_major > current_major:
                        major_outdated += 1
                except (ValueError, IndexError):
                    pass
            
            result["deps_outdated_major"] = float(major_outdated)
            
        except (json.JSONDecodeError, TypeError):
            result["deps_outdated_count"] = 0.0
            result["deps_outdated_major"] = 0.0

    def _collect_deptree(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract dependency tree metrics."""
        deptree_path = workdir / ".pyqual" / "deptree.json"
        if not deptree_path.exists():
            result["deps_direct_count"] = 0.0
            result["deps_transitive_count"] = 0.0
            result["deps_total_count"] = 0.0
            return

        try:
            data = json.loads(deptree_path.read_text())
            
            if isinstance(data, list):
                packages = data
            elif isinstance(data, dict):
                packages = data.get("packages", [])
            else:
                packages = []
            
            direct = len([p for p in packages if p.get("required_by") is None or len(p.get("required_by", [])) == 0])
            
            # Count transitive (has required_by but not top level)
            transitive = 0
            for pkg in packages:
                req_by = pkg.get("required_by", [])
                if req_by and len(req_by) > 0:
                    transitive += 1
            
            result["deps_direct_count"] = float(direct)
            result["deps_transitive_count"] = float(transitive)
            result["deps_total_count"] = float(len(packages))
            
        except (json.JSONDecodeError, TypeError):
            result["deps_direct_count"] = 0.0
            result["deps_transitive_count"] = 0.0
            result["deps_total_count"] = 0.0

    def _collect_requirements(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract requirements file metrics."""
        # Check for JSON report first
        req_json_path = workdir / ".pyqual" / "requirements_check.json"
        if req_json_path.exists():
            try:
                data = json.loads(req_json_path.read_text())
                result["deps_missing_reqs"] = float(data.get("missing_from_requirements", 0))
                result["deps_pins_incomplete"] = float(data.get("unpinned_packages", 0))
                return
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check if requirements.txt exists and parse directly
        req_path = workdir / "requirements.txt"
        if req_path.exists():
            try:
                content = req_path.read_text()
                lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
                
                # Count pinned vs unpinned
                pinned = sum(1 for l in lines if "==" in l or ">=" in l or "<=" in l or "~=" in l)
                unpinned = len(lines) - pinned
                
                result["deps_requirements_entries"] = float(len(lines))
                result["deps_pins_incomplete"] = float(unpinned)
                result["deps_missing_reqs"] = 0.0  # Cannot determine without pip
            except Exception:
                result["deps_requirements_entries"] = 0.0
                result["deps_pins_incomplete"] = 0.0
                result["deps_missing_reqs"] = 0.0
        else:
            result["deps_requirements_entries"] = 0.0
            result["deps_pins_incomplete"] = 0.0
            result["deps_missing_reqs"] = 0.0

    def _collect_licenses(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract license analysis metrics."""
        licenses_path = workdir / ".pyqual" / "licenses.json"
        if not licenses_path.exists():
            result["deps_licenses_unknown"] = 0.0
            result["deps_licenses_restrictive"] = 0.0
            return

        try:
            data = json.loads(licenses_path.read_text())
            
            if isinstance(data, list):
                packages = data
            elif isinstance(data, dict):
                packages = data.get("packages", [])
            else:
                packages = []
            
            # Count unknown licenses
            unknown = len([p for p in packages if not p.get("license") or p.get("license") in ["UNKNOWN", "", None]])
            
            # Count restrictive licenses
            restrictive_keywords = ["GPL", "AGPL", "SSPL", "proprietary", "commercial"]
            restrictive = len([
                p for p in packages
                if any(kw in str(p.get("license", "")).upper() for kw in restrictive_keywords)
            ])
            
            result["deps_licenses_unknown"] = float(unknown)
            result["deps_licenses_restrictive"] = float(restrictive)
            
        except (json.JSONDecodeError, TypeError):
            result["deps_licenses_unknown"] = 0.0
            result["deps_licenses_restrictive"] = 0.0

    def get_config_example(self) -> str:
        """Return ready-to-use YAML configuration."""
        return self.metadata.config_example


def get_outdated_packages(cwd: Path | None = None) -> dict[str, Any]:
    """Get list of outdated packages.
    
    Args:
        cwd: Working directory
        
    Returns:
        Dict with outdated packages list
    """
    cmd = ["pip", "list", "--outdated", "--format=json"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            try:
                packages = json.loads(result.stdout)
                
                # Categorize by severity
                major_outdated = []
                minor_outdated = []
                
                for pkg in packages:
                    current = pkg.get("version", "0.0.0")
                    latest = pkg.get("latest_version", "0.0.0")
                    
                    try:
                        current_parts = current.split(".")
                        latest_parts = latest.split(".")
                        
                        if int(latest_parts[0]) > int(current_parts[0]):
                            major_outdated.append(pkg)
                        else:
                            minor_outdated.append(pkg)
                    except (ValueError, IndexError):
                        minor_outdated.append(pkg)
                
                return {
                    "success": True,
                    "total": len(packages),
                    "major_outdated": len(major_outdated),
                    "minor_outdated": len(minor_outdated),
                    "packages": packages,
                    "has_major_outdated": len(major_outdated) > 0,
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse pip output",
                    "total": 0,
                    "packages": [],
                }
        else:
            return {
                "success": False,
                "error": result.stderr or f"pip exit code: {result.returncode}",
                "total": 0,
                "packages": [],
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pip not found",
            "total": 0,
            "packages": [],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "pip list timed out",
            "total": 0,
            "packages": [],
        }


def get_dependency_tree(cwd: Path | None = None) -> dict[str, Any]:
    """Get dependency tree using pipdeptree.
    
    Args:
        cwd: Working directory
        
    Returns:
        Dict with dependency tree
    """
    cmd = ["pipdeptree", "--json"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode == 0:
            try:
                packages = json.loads(result.stdout)
                
                direct = [p for p in packages if not p.get("required_by")]
                transitive = [p for p in packages if p.get("required_by")]
                
                return {
                    "success": True,
                    "total_packages": len(packages),
                    "direct_count": len(direct),
                    "transitive_count": len(transitive),
                    "packages": packages,
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse pipdeptree output",
                    "total_packages": 0,
                }
        else:
            return {
                "success": False,
                "error": result.stderr or "pipdeptree failed",
                "total_packages": 0,
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pipdeptree not found — install with: pip install pipdeptree",
            "total_packages": 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "pipdeptree timed out",
            "total_packages": 0,
        }


def check_requirements(
    req_file: str = "requirements.txt",
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Check requirements file for issues.
    
    Args:
        req_file: Path to requirements file
        cwd: Working directory
        
    Returns:
        Dict with requirements check results
    """
    req_path = (cwd or Path.cwd()) / req_file
    
    if not req_path.exists():
        return {
            "success": False,
            "error": f"Requirements file not found: {req_file}",
            "exists": False,
            "entries": 0,
            "unpinned_packages": 0,
        }
    
    try:
        content = req_path.read_text()
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        
        # Check for unpinned packages
        unpinned = []
        for line in lines:
            # Skip comments, options, and git URLs
            if line.startswith("-") or "git+" in line or "@" in line:
                continue
            
            # Check if version is pinned
            if "==" not in line and ">=" not in line and "<=" not in line and "~=" not in line:
                unpinned.append(line.split("#")[0].split(";")[0].strip())
        
        return {
            "success": True,
            "exists": True,
            "entries": len(lines),
            "unpinned_packages": len(unpinned),
            "unpinned_list": unpinned,
            "is_fully_pinned": len(unpinned) == 0,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "exists": True,
            "entries": 0,
            "unpinned_packages": 0,
        }


def deps_health_check(cwd: Path | None = None) -> dict[str, Any]:
    """Run comprehensive dependency health check.
    
    Returns aggregated metrics from all dependency checks.
    """
    cwd = cwd or Path.cwd()
    
    outdated = get_outdated_packages(cwd)
    tree = get_dependency_tree(cwd)
    reqs = check_requirements(cwd=cwd)
    
    # Collect metrics
    collector = DepsCollector()
    metrics = collector.collect(cwd)
    
    # Determine health status
    is_healthy = (
        not outdated.get("has_major_outdated", False)
        and reqs.get("is_fully_pinned", True)
        and metrics.get("deps_licenses_unknown", 0) < 5
    )
    
    recommendations = []
    
    if outdated.get("has_major_outdated", False):
        count = outdated.get("major_outdated", 0)
        recommendations.append(f"Update {count} packages with major version updates")
    
    if not reqs.get("is_fully_pinned", True):
        count = reqs.get("unpinned_packages", 0)
        recommendations.append(f"Pin {count} packages in requirements.txt for reproducible builds")
    
    if metrics.get("deps_licenses_unknown", 0) > 0:
        count = int(metrics.get("deps_licenses_unknown", 0))
        recommendations.append(f"Review {count} packages with unknown licenses")
    
    if tree.get("transitive_count", 0) > 50:
        recommendations.append("Consider reducing transitive dependencies")
    
    return {
        "success": True,
        "metrics": metrics,
        "outdated": outdated,
        "tree": tree,
        "requirements": reqs,
        "is_healthy": is_healthy,
        "recommendations": recommendations,
    }
