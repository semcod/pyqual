"""Lint plugin for pyqual — code quality linting metrics.

Collects metrics from ruff, pylint, flake8 JSON outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class LintCollector(MetricCollector):
    """Lint metrics collector — aggregates findings from linters."""

    name = "lint"
    metadata = PluginMetadata(
        name="lint",
        description="Code linting: ruff, pylint, flake8, mypy integration",
        version="1.0.0",
        tags=["lint", "ruff", "pylint", "flake8", "mypy", "code-quality"],
        config_example="""
metrics:
  ruff_errors_max: 50            # Max ruff errors allowed
  pylint_errors_max: 20          # Max pylint errors
  flake8_violations_max: 30       # Max flake8 violations
  mypy_errors_max: 100            # Max mypy type errors

stages:
  - name: ruff_lint
    run: ruff check pyqual tests --output-format=json > .pyqual/ruff.json || echo '[]' > .pyqual/ruff.json
  
  - name: mypy_types
    run: mypy pyqual --ignore-missing-imports --output=json > .pyqual/mypy.json || echo '[]' > .pyqual/mypy.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect lint metrics from various linter outputs."""
        result: dict[str, float] = {}
        
        self._collect_ruff(workdir, result)
        self._collect_mypy(workdir, result)
        self._collect_pylint(workdir, result)
        self._collect_flake8(workdir, result)
        
        return result

    def _collect_ruff(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract ruff linter metrics."""
        p = workdir / ".pyqual" / "ruff.json"
        if not p.exists():
            result["ruff_errors"] = 0.0
            return
            
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                errors = len(data)
                fatal = sum(1 for e in data if e.get("severity") == "fatal" 
                           or str(e.get("code", "")).startswith("E"))
                warning = sum(1 for e in data if e.get("severity") == "warning"
                             or str(e.get("code", "")).startswith("W"))
                result["ruff_errors"] = float(errors)
                result["ruff_fatal"] = float(fatal)
                result["ruff_warnings"] = float(warning)
            elif isinstance(data, dict):
                errors = len(data.get("violations", data.get("messages", [])))
                result["ruff_errors"] = float(errors)
        except (json.JSONDecodeError, TypeError):
            result["ruff_errors"] = 0.0

    def _collect_mypy(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract mypy type error count."""
        p = workdir / ".pyqual" / "mypy.json"
        if not p.exists():
            result["mypy_errors"] = 0.0
            return
            
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
            result["mypy_errors"] = 0.0

    def _collect_pylint(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract pylint score and error counts."""
        p = workdir / ".pyqual" / "pylint.json"
        if not p.exists():
            return
            
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, TypeError):
            return
            
        if isinstance(data, list):
            result["pylint_errors"] = float(len(data))
            result["pylint_fatal"] = float(sum(
                1 for m in data 
                if m.get("type") == "fatal" or str(m.get("symbol", "")).startswith("F")
            ))
            result["pylint_warnings"] = float(sum(
                1 for m in data 
                if m.get("type") == "warning" or str(m.get("symbol", "")).startswith("W")
            ))
        elif isinstance(data, dict):
            score = data.get("score") or data.get("rating")
            if score is not None:
                result["pylint_score"] = float(score)
            messages = data.get("messages", [])
            result["pylint_errors"] = float(len(messages))

    def _collect_flake8(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract flake8 violation count."""
        p = workdir / ".pyqual" / "flake8.json"
        if not p.exists():
            return
            
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                violations = len(data)
                errors = sum(1 for v in data if str(v.get("code", "")).startswith(("E", "F")))
                warnings = sum(1 for v in data if str(v.get("code", "")).startswith(("W",)))
                result["flake8_violations"] = float(violations)
                result["flake8_errors"] = float(errors)
                result["flake8_warnings"] = float(warnings)
            elif isinstance(data, dict):
                violations = data.get("violations", data.get("messages", []))
                result["flake8_violations"] = float(len(violations))
        except (json.JSONDecodeError, TypeError):
            pass


def lint_summary(workdir: Path | None = None) -> dict[str, Any]:
    """Generate comprehensive lint summary."""
    workdir = workdir or Path.cwd()
    collector = LintCollector()
    metrics = collector.collect(workdir)
    
    total_errors = (
        metrics.get("ruff_errors", 0)
        + metrics.get("pylint_errors", 0)
        + metrics.get("flake8_violations", 0)
        + metrics.get("mypy_errors", 0)
    )
    
    return {
        "success": True,
        "metrics": metrics,
        "total_errors": int(total_errors),
        "is_clean": total_errors == 0,
        "tools_checked": ["ruff", "pylint", "flake8", "mypy"],
    }
