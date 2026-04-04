"""Docs plugin for pyqual — documentation quality and coverage.

This plugin provides documentation analysis:
- README.md quality and completeness
- Docstring coverage (via interrogate)
- Link checking
- Changelog maintenance
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class DocsCollector(MetricCollector):
    """Documentation quality metrics collector."""

    name = "docs"
    metadata = PluginMetadata(
        name="docs",
        description="Documentation quality: README completeness, docstring coverage, link checking",
        version="1.0.0",
        tags=["documentation", "readme", "docstrings", "links", "quality"],
        config_example="""
metrics:
  docs_readme_sections_min: 5       # Minimum README sections
  docs_docstring_coverage_min: 80    # Docstring coverage %
  docs_broken_links_max: 0         # Broken external links
  docs_changelog_days_max: 30       # Days since last changelog update

stages:
  - name: docs_check
    run: |
      # Check README sections
      python3 -c "from pyqual.plugins.docs import check_readme; import json; r=check_readme(); json.dump(r, open('.pyqual/docs_readme.json','w'))"
      
      # Check docstring coverage
      interrogate pyqual --generate-badge .pyqual/docstring_badge.svg -v --format json > .pyqual/docstring_coverage.json 2>&1 || true
      
      # Check links
      lychee README.md --format json -o .pyqual/links.json || echo '[]' > .pyqual/links.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect documentation metrics from various sources."""
        result: dict[str, float] = {}

        # README analysis
        self._collect_readme_metrics(workdir, result)

        # Docstring coverage
        self._collect_docstring_metrics(workdir, result)

        # Link checking
        self._collect_link_metrics(workdir, result)

        # Changelog freshness
        self._collect_changelog_metrics(workdir, result)

        return result

    def _collect_readme_metrics(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract README quality metrics."""
        readme_path = workdir / "README.md"
        
        # Check for JSON report first
        readme_json_path = workdir / ".pyqual" / "docs_readme.json"
        if readme_json_path.exists():
            try:
                data = json.loads(readme_json_path.read_text())
                result["docs_readme_sections"] = float(data.get("section_count", 0))
                result["docs_readme_has_install"] = 1.0 if data.get("has_install", False) else 0.0
                result["docs_readme_has_usage"] = 1.0 if data.get("has_usage", False) else 0.0
                result["docs_readme_has_license"] = 1.0 if data.get("has_license", False) else 0.0
                result["docs_readme_code_blocks"] = float(data.get("code_blocks", 0))
                result["docs_readme_length"] = float(data.get("word_count", 0))
                return
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback: analyze directly
        if readme_path.exists():
            try:
                content = readme_path.read_text()
                sections = len(re.findall(r'^#{1,3}\s+', content, re.MULTILINE))
                result["docs_readme_sections"] = float(sections)
                result["docs_readme_has_install"] = 1.0 if "install" in content.lower() else 0.0
                result["docs_readme_has_usage"] = 1.0 if "usage" in content.lower() else 0.0
                result["docs_readme_has_license"] = 1.0 if "license" in content.lower() else 0.0
                result["docs_readme_code_blocks"] = float(content.count("```"))
                result["docs_readme_length"] = float(len(content.split()))
            except Exception:
                self._set_zero_readme(result)
        else:
            self._set_zero_readme(result)

    def _set_zero_readme(self, result: dict[str, float]) -> None:
        """Set zero values for README metrics."""
        result["docs_readme_sections"] = 0.0
        result["docs_readme_has_install"] = 0.0
        result["docs_readme_has_usage"] = 0.0
        result["docs_readme_has_license"] = 0.0
        result["docs_readme_code_blocks"] = 0.0
        result["docs_readme_length"] = 0.0

    def _collect_docstring_metrics(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract docstring coverage metrics."""
        coverage_path = workdir / ".pyqual" / "docstring_coverage.json"
        if not coverage_path.exists():
            result["docs_docstring_coverage"] = 0.0
            result["docs_missing_docstrings"] = 0.0
            return

        try:
            data = json.loads(coverage_path.read_text())
            
            # Try different interrogate output formats
            if isinstance(data, dict):
                coverage = data.get("coverage", data.get("percent_coverage", 0))
                if isinstance(coverage, (int, float)):
                    result["docs_docstring_coverage"] = float(coverage)
                else:
                    # Try to parse from summary
                    summary = data.get("summary", {})
                    coverage = summary.get("percent_covered", 0)
                    result["docs_docstring_coverage"] = float(coverage)
                    
                missing = data.get("missing", data.get("num_missing", 0))
                result["docs_missing_docstrings"] = float(missing)
            else:
                result["docs_docstring_coverage"] = 0.0
                result["docs_missing_docstrings"] = 0.0
        except (json.JSONDecodeError, TypeError):
            result["docs_docstring_coverage"] = 0.0
            result["docs_missing_docstrings"] = 0.0

    def _collect_link_metrics(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract link checking metrics."""
        links_path = workdir / ".pyqual" / "links.json"
        if not links_path.exists():
            result["docs_broken_links"] = 0.0
            result["docs_total_links"] = 0.0
            return

        try:
            data = json.loads(links_path.read_text())
            
            if isinstance(data, list):
                # lychee format
                broken = len([l for l in data if l.get("status") != "ok"])
                total = len(data)
            elif isinstance(data, dict):
                # Alternative format
                broken = len(data.get("fail_map", {}))
                total = len(data.get("success_map", {})) + broken
            else:
                broken = 0
                total = 0
                
            result["docs_broken_links"] = float(broken)
            result["docs_total_links"] = float(total)
        except (json.JSONDecodeError, TypeError):
            result["docs_broken_links"] = 0.0
            result["docs_total_links"] = 0.0

    def _collect_changelog_metrics(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract changelog freshness metrics."""
        changelog_paths = [
            workdir / "CHANGELOG.md",
            workdir / "CHANGES.md",
            workdir / "NEWS.md",
            workdir / "HISTORY.md",
        ]
        
        # Check for JSON report first
        changelog_json_path = workdir / ".pyqual" / "changelog.json"
        if changelog_json_path.exists():
            try:
                data = json.loads(changelog_json_path.read_text())
                result["docs_changelog_days"] = float(data.get("days_since_update", 999))
                result["docs_changelog_exists"] = 1.0 if data.get("exists", False) else 0.0
                result["docs_changelog_entries"] = float(data.get("entry_count", 0))
                return
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Check if any changelog exists
        for changelog_path in changelog_paths:
            if changelog_path.exists():
                result["docs_changelog_exists"] = 1.0
                # Can't determine days without git, set placeholder
                result["docs_changelog_days"] = 0.0  # Assume up to date if exists
                
                # Count version entries
                try:
                    content = changelog_path.read_text()
                    entries = len(re.findall(r'^##?\s*\[?v?\d+', content, re.MULTILINE | re.IGNORECASE))
                    result["docs_changelog_entries"] = float(entries)
                except Exception:
                    result["docs_changelog_entries"] = 0.0
                return
        
        # No changelog found
        result["docs_changelog_exists"] = 0.0
        result["docs_changelog_days"] = 999.0
        result["docs_changelog_entries"] = 0.0

    def get_config_example(self) -> str:
        """Return ready-to-use YAML configuration."""
        return self.metadata.config_example


def check_readme(readme_path: str = "README.md", cwd: Path | None = None) -> dict[str, Any]:
    """Analyze README.md for quality metrics.
    
    Args:
        readme_path: Path to README file
        cwd: Working directory
        
    Returns:
        Dict with README analysis
    """
    path = (cwd or Path.cwd()) / readme_path
    
    if not path.exists():
        return {
            "success": False,
            "error": f"README not found: {readme_path}",
            "exists": False,
            "section_count": 0,
            "has_install": False,
            "has_usage": False,
            "has_license": False,
            "code_blocks": 0,
            "word_count": 0,
        }
    
    try:
        content = path.read_text()
        
        # Count sections (headers)
        sections = len(re.findall(r'^#{1,3}\s+', content, re.MULTILINE))
        
        # Check for important sections
        has_install = any(pattern in content.lower() for pattern in [
            "## install", "### install", "## setup", "### setup",
            "getting started", "quick start", "installation"
        ])
        
        has_usage = any(pattern in content.lower() for pattern in [
            "## usage", "### usage", "## example", "### example",
            "## how to", "### how to", "how to use"
        ])
        
        has_license = any(pattern in content.lower() for pattern in [
            "## license", "### license", "licensed under", "## 📄 license"
        ])
        
        # Count code blocks
        code_blocks = content.count("```")
        
        # Word count
        words = len(content.split())
        
        return {
            "success": True,
            "exists": True,
            "section_count": sections,
            "has_install": has_install,
            "has_usage": has_usage,
            "has_license": has_license,
            "code_blocks": code_blocks // 2,  # Each block has opening and closing
            "word_count": words,
            "is_quality": sections >= 3 and has_install and has_usage,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "exists": True,
            "section_count": 0,
            "has_install": False,
            "has_usage": False,
            "has_license": False,
            "code_blocks": 0,
            "word_count": 0,
        }


def run_interrogate(
    paths: list[str] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run interrogate for docstring coverage.
    
    Args:
        paths: List of paths to analyze
        cwd: Working directory
        
    Returns:
        Dict with coverage results
    """
    paths = paths or ["."]
    cmd = ["interrogate", *paths, "--format", "json", "-v"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        # Parse output
        try:
            data = json.loads(result.stdout)
            coverage = data.get("coverage", 0)
            missing = len(data.get("missing", []))
            
            return {
                "success": True,
                "coverage": coverage,
                "missing": missing,
                "percent_covered": coverage,
                "is_adequate": coverage >= 80,
            }
        except json.JSONDecodeError:
            # Try to parse from stderr or text output
            return {
                "success": result.returncode == 0,
                "coverage": 0,
                "missing": 0,
                "raw_output": result.stdout,
            }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "interrogate not found — install with: pip install interrogate",
            "coverage": 0,
            "missing": 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "interrogate timed out",
            "coverage": 0,
            "missing": 0,
        }


def check_links(
    files: list[str] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Check for broken links in documentation.
    
    Uses lychee if available, falls back to basic regex check.
    
    Args:
        files: List of files to check
        cwd: Working directory
        
    Returns:
        Dict with link check results
    """
    files = files or ["README.md"]
    
    cmd = ["lychee", *files, "--format", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
        )
        
        try:
            data = json.loads(result.stdout)
            if isinstance(data, list):
                broken = [l for l in data if l.get("status") != "ok"]
                return {
                    "success": True,
                    "broken_links": broken,
                    "broken_count": len(broken),
                    "total_count": len(data),
                    "is_valid": len(broken) == 0,
                }
        except json.JSONDecodeError:
            pass
        
        return {
            "success": result.returncode == 0,
            "broken_count": 0,
            "total_count": 0,
            "raw_output": result.stdout,
        }
    except FileNotFoundError:
        return {
            "success": True,  # Don't fail if tool not installed
            "error": "lychee not found — install from: https://lychee.cli.rs/",
            "broken_count": 0,
            "is_valid": True,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "lychee timed out",
            "broken_count": 0,
        }


def docs_quality_summary(cwd: Path | None = None) -> dict[str, Any]:
    """Generate comprehensive documentation quality summary.
    
    Returns aggregated metrics from all documentation checks.
    """
    cwd = cwd or Path.cwd()
    
    readme = check_readme(cwd=cwd)
    interrogate_result = run_interrogate(cwd=cwd)
    links = check_links(cwd=cwd)
    
    # Collect metrics
    collector = DocsCollector()
    metrics = collector.collect(cwd)
    
    is_complete = (
        readme.get("has_install", False)
        and readme.get("has_usage", False)
        and readme.get("has_license", False)
        and readme.get("section_count", 0) >= 3
    )
    
    coverage_adequate = metrics.get("docs_docstring_coverage", 0) >= 80
    
    return {
        "success": True,
        "metrics": metrics,
        "readme": readme,
        "docstring_coverage": interrogate_result,
        "links": links,
        "is_complete": is_complete,
        "coverage_adequate": coverage_adequate,
        "recommendations": _generate_recommendations(readme, metrics),
    }


def _generate_recommendations(readme: dict, metrics: dict) -> list[str]:
    """Generate recommendations based on documentation analysis."""
    recs = []
    
    if not readme.get("has_install", False):
        recs.append("Add installation instructions to README")
    
    if not readme.get("has_usage", False):
        recs.append("Add usage examples to README")
    
    if not readme.get("has_license", False):
        recs.append("Add license section to README")
    
    if readme.get("section_count", 0) < 3:
        recs.append("Expand README with more sections (API, Contributing, etc.)")
    
    coverage = metrics.get("docs_docstring_coverage", 0)
    if coverage < 50:
        recs.append(f"Add docstrings to improve coverage (currently {coverage:.0f}%)")
    elif coverage < 80:
        recs.append(f"Consider adding more docstrings (currently {coverage:.0f}%)")
    
    broken = metrics.get("docs_broken_links", 0)
    if broken > 0:
        recs.append(f"Fix {int(broken)} broken external links")
    
    return recs
