"""Code health plugin for pyqual — code quality and maintainability metrics.

Collects metrics from radon, vulture, pyroma, interrogate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class CodeHealthCollector(MetricCollector):
    """Code health metrics collector — maintainability, dead code, packaging quality."""

    name = "code_health"
    metadata = PluginMetadata(
        name="code_health",
        description="Code health: radon MI, vulture dead code, pyroma packaging, interrogate docs",
        version="1.0.0",
        tags=["code-health", "maintainability", "dead-code", "packaging", "documentation"],
        config_example="""
metrics:
  maintainability_index_min: 70.0    # Minimum radon maintainability index
  unused_count_max: 10                # Max vulture unused items
  pyroma_score_min: 8.0               # Minimum pyroma packaging score
  docstring_coverage_min: 80.0         # Minimum docstring coverage %

stages:
  - name: radon_mi
    run: radon mi pyqual -s -j > .pyqual/radon.json || echo '{}' > .pyqual/radon.json
  
  - name: vulture_dead
    run: vulture pyqual --json > .pyqual/vulture.json || echo '[]' > .pyqual/vulture.json
  
  - name: pyroma_check
    run: pyroma . -n > .pyqual/pyroma.json || echo '{"score": 0}' > .pyqual/pyroma.json
  
  - name: interrogate_docs
    run: interrogate pyqual --json > .pyqual/interrogate.json || echo '{"coverage": 0}' > .pyqual/interrogate.json
""",
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect code health metrics."""
        result: dict[str, float] = {}
        
        self._collect_radon(workdir, result)
        self._collect_vulture(workdir, result)
        self._collect_pyroma(workdir, result)
        self._collect_interrogate(workdir, result)
        
        return result

    def _collect_radon(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract maintainability index from radon JSON."""
        p = workdir / ".pyqual" / "radon.json"
        if not p.exists():
            return
            
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

    def _collect_vulture(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract dead code count from vulture JSON."""
        p = workdir / ".pyqual" / "vulture.json"
        if not p.exists():
            result["unused_count"] = 0.0
            return
            
        try:
            data = json.loads(p.read_text())
            if isinstance(data, list):
                result["unused_count"] = float(len(data))
        except (json.JSONDecodeError, TypeError):
            result["unused_count"] = 0.0

    def _collect_pyroma(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract packaging quality score from pyroma JSON."""
        p = workdir / ".pyqual" / "pyroma.json"
        if not p.exists():
            return
            
        try:
            data = json.loads(p.read_text())
            score = data.get("score")
            if score is None:
                score = data.get("rating")
            if isinstance(score, (int, float)):
                result["pyroma_score"] = float(score)
            elif isinstance(score, str) and score.upper() in "ABCDEF":
                # Convert letter grade to numeric (A=10, B=9, etc.)
                result["pyroma_score"] = float(10 - ord(score.upper()[0]) + ord("A"))
        except (json.JSONDecodeError, TypeError):
            pass

    def _collect_interrogate(self, workdir: Path, result: dict[str, float]) -> None:
        """Extract docstring coverage from interrogate JSON."""
        p = workdir / ".pyqual" / "interrogate.json"
        if not p.exists():
            return
            
        try:
            data = json.loads(p.read_text())
            coverage = data.get("coverage")
            if coverage is None:
                coverage = data.get("percent_covered")
            if coverage is not None:
                result["docstring_coverage"] = float(coverage)
            
            total = data.get("total") or data.get("total_objects")
            documented = data.get("documented") or data.get("documented_objects")
            if total and documented is not None:
                result["docstring_total"] = float(total)
                result["docstring_missing"] = float(total - documented)
        except (json.JSONDecodeError, TypeError):
            pass


def code_health_summary(workdir: Path | None = None) -> dict[str, Any]:
    """Generate comprehensive code health summary."""
    workdir = workdir or Path.cwd()
    collector = CodeHealthCollector()
    metrics = collector.collect(workdir)
    
    issues = sum(
        1 for k, v in metrics.items()
        if k in ("unused_count", "docstring_missing") and v > 0
    )
    
    return {
        "success": True,
        "metrics": metrics,
        "issues_found": issues,
        "is_healthy": issues == 0,
        "tools_checked": ["radon", "vulture", "pyroma", "interrogate"],
    }
