#!/usr/bin/env python3
"""Run project-analysis pipeline on target projects and report results."""

import sys
import time
import sqlite3
import ast
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pyqual.config import PyqualConfig
from pyqual.pipeline import Pipeline

PIPELINE_CONFIG = Path(__file__).parent / "examples" / "project_analysis" / "pyqual.yaml"

PROJECTS = [
    "/home/tom/github/wronai/nlp2cmd",
    "/home/tom/github/broxeen/broxeen",
]


def run_project(project_path: str) -> None:
    name = Path(project_path).name
    print(f"\n{'='*60}")
    print(f"  PROJECT: {name} ({project_path})")
    print(f"{'='*60}")

    config = PyqualConfig.load(PIPELINE_CONFIG)
    pipeline = Pipeline(config, workdir=project_path)

    t0 = time.monotonic()
    result = pipeline.run()
    total = time.monotonic() - t0

    print(f"\n--- {name} RESULTS ---")
    print(f"Duration: {total:.0f}s ({total/60:.1f} min)")
    print(f"Passed: {result.final_passed}")
    print(f"Iterations: {result.iteration_count}")

    for it in result.iterations:
        for s in it.stages:
            status = "SKIP" if s.skipped else ("OK" if s.passed else f"FAIL(rc={s.returncode})")
            dur = f"{s.duration:.1f}s"
            err = (s.stderr or "")[:120].replace("\n", " ")
            print(f"  {s.name:15s} {status:12s} {dur:>8s}  {err}")

    # Show nfo log summary
    db_path = Path(project_path) / ".pyqual" / "pipeline.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        total_rows = conn.execute("SELECT COUNT(*) FROM pipeline_logs").fetchone()[0]
        warnings = conn.execute("SELECT COUNT(*) FROM pipeline_logs WHERE level='WARNING'").fetchone()[0]
        conn.close()
        print(f"  nfo log: {total_rows} entries, {warnings} warnings")

    # Check generated outputs
    project_dir = Path(project_path) / "project"
    if project_dir.exists():
        files = sorted(project_dir.glob("*"))
        print(f"  Output files in project/: {len(files)}")
        for f in files[:15]:
            size = f.stat().st_size if f.is_file() else 0
            print(f"    {f.name:40s} {size:>10,d} bytes")
        if len(files) > 15:
            print(f"    ... and {len(files) - 15} more")

    print()


def main():
    print(f"Pipeline config: {PIPELINE_CONFIG}")
    print(f"Projects: {len(PROJECTS)}")

    for project in PROJECTS:
        if not Path(project).exists():
            print(f"SKIP: {project} not found")
            continue
        try:
            run_project(project)
        except Exception as e:
            print(f"ERROR on {project}: {e}")

    print("\n=== ALL DONE ===")


if __name__ == "__main__":
    main()
