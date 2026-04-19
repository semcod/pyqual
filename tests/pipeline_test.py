import json as json_mod
import sqlite3
import ast
import tempfile
from pathlib import Path
from pyqual.config import PyqualConfig
from pyqual.pipeline import Pipeline
def test_pipeline_writes_nfo_sqlite_log() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".pyqual").mkdir()
        (p / "analysis_toon.yaml").write_text("CC̄=2.0 critical=0")
        (p / "validation_toon.yaml").write_text(
            "SUMMARY:\n  scanned: 100  passed: 95 (95.0%)")
        (p / ".pyqual" / "coverage.json").write_text(
            json_mod.dumps({"totals": {"percent_covered": 90.0}}))
        config_yaml = p / "pyqual.yaml"
        config_yaml.write_text("""
pipeline:
  name: log-test
  metrics:
    cc_max: 3.0
    coverage_min: 80
  stages:
    - name: noop
      run: echo ok
  loop:
    max_iterations: 1
""")
        config = PyqualConfig.load(config_yaml)
        pipeline = Pipeline(config, workdir=p)
        result = pipeline.run()
        db_path = p / ".pyqual" / "pipeline.db"
        assert db_path.exists(), "pipeline.db should be written by nfo"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM pipeline_logs ORDER BY rowid").fetchall()
        conn.close()
        assert len(rows) >= 3, f"Expected ≥3 log entries, got {len(rows)}"
        events = [r["function_name"] for r in rows]
        assert "pipeline_start" in events
        assert "stage_done" in events
        assert "gate_check" in events
        assert "pipeline_end" in events
        stage_row = next(r for r in rows if r["function_name"] == "stage_done")
        kwargs = ast.literal_eval(stage_row["kwargs"])
        assert kwargs["stage"] == "noop"
        assert "returncode" in kwargs
        assert "duration_s" in kwargs
        assert "ok" in kwargs  # 'ok' not 'passed' — avoids nfo PASS redaction
        end_row = next(r for r in rows if r["function_name"] == "pipeline_end")
        end_kw = ast.literal_eval(end_row["kwargs"])
        assert end_kw["final_ok"] is True  # 'final_ok' not 'final_passed"