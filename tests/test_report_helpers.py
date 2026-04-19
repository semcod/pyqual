from __future__ import annotations

import json
from pathlib import Path

import yaml


def make_project(tmpdir: Path, *, cc: float = 3.6, critical: int = 2,
                 vallm_pass: float = 85.0, coverage: float = 72.0) -> Path:
    """Create a minimal project tree with .pyqual/ and toon artifacts."""
    (tmpdir / ".pyqual").mkdir(exist_ok=True)
    (tmpdir / "project").mkdir(exist_ok=True)

    (tmpdir / "project" / "analysis.toon.yaml").write_text(
        f"# code2llm | CC̄={cc} | critical:{critical}\nHEALTH:\n  ok"
    )
    (tmpdir / "project" / "validation.toon.yaml").write_text(
        f"SUMMARY:\n  scanned: 100  passed: 85 ({vallm_pass}%)  warnings: 5"
    )
    (tmpdir / ".pyqual" / "coverage.json").write_text(
        json.dumps({"totals": {"percent_covered": coverage}})
    )
    return tmpdir


def write_config(tmpdir: Path) -> Path:
    """Write a minimal pyqual.yaml and return its path."""
    cfg_path = tmpdir / "pyqual.yaml"
    cfg_path.write_text(yaml.dump({
        "pipeline": {
            "name": "test-report",
            "metrics": {"cc_max": 15, "coverage_min": 60, "vallm_pass_min": 80},
            "stages": [
                {"name": "test", "run": "echo ok"},
            ],
        }
    }))
    return cfg_path
