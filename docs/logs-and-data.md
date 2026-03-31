# Pyqual Logs & Data Access

Pyqual records all pipeline activity to two storage backends:

| Storage | Location | Format | Contents |
|---------|----------|--------|----------|
| **Pipeline DB** | `.pyqual/pipeline.db` | SQLite (nfo) | Stage results, gate checks, pipeline events |
| **LLX History** | `.pyqual/llx_history.jsonl` | JSON Lines | LLM fix prompts, model selection, issue details |

## Pipeline Database (`.pyqual/pipeline.db`)

### Schema

Single table `pipeline_logs` with columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `timestamp` | TEXT | ISO 8601 with timezone (e.g. `2026-03-31T15:24:18.382456+00:00`) |
| `level` | TEXT | `INFO` (passed) or `WARNING` (failed) |
| `function_name` | TEXT | Event type — see below |
| `module` | TEXT | Always `pyqual.pipeline` |
| `kwargs` | TEXT | Python repr dict with all structured data |
| `duration_ms` | REAL | Execution time in milliseconds |
| `version` | TEXT | Pipeline name from `pyqual.yaml` |

Other columns (`args`, `arg_types`, `kwarg_types`, `return_value`, `return_type`, `exception`, `exception_type`, `traceback`, `environment`, `trace_id`, `llm_analysis`) exist in the schema but are typically NULL.

### Event Types

#### `pipeline_start`

Emitted once at the beginning of each `pyqual run`.

```
kwargs = {
    "event": "pipeline_start",
    "pipeline": "quality-loop-with-llx",
    "stages": 8,           # number of configured stages
    "gates": 3,            # number of quality gates
    "max_iterations": 3,
    "dry_run": False
}
```

#### `stage_done`

Emitted after every stage execution (including skipped stages).

```
kwargs = {
    "event": "stage_done",
    "pipeline": "quality-loop-with-llx",
    "stage": "fix",
    "tool": None,                           # or "pytest", "code2llm", etc.
    "command": "llx fix . --apply ...",
    "returncode": 0,                        # normalized (0 for allow_failure)
    "original_returncode": 0,               # raw exit code
    "ok": True,
    "skipped": False,
    "duration_s": 11.511,
    "optional": False,
    "allow_failure": False,
    "stdout_tail": "... last 2000 chars of stdout (for fix stages) ...",
    "stderr_tail": "... last 500 chars of stderr ..."
}
```

**Note on output capture:**
- `stderr_tail`: last 500 characters for all stages
- `stdout_tail`: last 500 characters normally, **2000 characters for fix stages** (to capture LLM responses)
- Skipped stages have `skipped: True` and no output

#### `gate_check`

Emitted for each quality gate after every iteration.

```
kwargs = {
    "event": "gate_check",
    "pipeline": "quality-loop-with-llx",
    "iteration": 1,
    "metric": "coverage",
    "value": 58.968,          # actual measured value
    "threshold": 55.0,        # configured threshold
    "operator": "ge",         # ge, le, gt, lt, eq
    "ok": True
}
```

#### `pipeline_end`

Emitted once when the pipeline completes (pass or fail).

```
kwargs = {
    "event": "pipeline_end",
    "pipeline": "quality-loop-with-llx",
    "final_ok": True,
    "iterations": 1,
    "total_duration_s": 62.114
}
```

## CLI Commands for Reading Data

### `pyqual logs` — Query pipeline.db

```bash
# All entries (table view)
pyqual logs

# Last N entries
pyqual logs --tail 10

# Only failures
pyqual logs --failed

# Filter by stage name
pyqual logs --stage fix
pyqual logs --stage validate

# Include captured stdout/stderr
pyqual logs --stage fix --output

# JSON output (for LLM/scripting)
pyqual logs --json
pyqual logs --json --failed

# Raw SQL query
pyqual logs --sql "SELECT * FROM pipeline_logs WHERE function_name='gate_check' AND kwargs LIKE '%ok%: False%'"
```

### `pyqual history` — Query LLX fix history

```bash
# Summary table
pyqual history

# Last 5 runs
pyqual history --tail 5

# Include full LLX prompts (model selection, issues, analysis payload)
pyqual history --prompts

# Include aider/llx stdout output
pyqual history --verbose

# Raw JSONL
pyqual history --json
```

### `pyqual watch` — Live tail during pipeline run

Run in a **second terminal** while `pyqual run` executes:

```bash
# Live tail of new pipeline.db entries
pyqual watch

# Include stage stdout/stderr as they appear
pyqual watch --output

# Show LLX fix prompts in real-time
pyqual watch --prompts

# Faster polling
pyqual watch --interval 0.5
```

## Direct SQL Access

### From Python

```python
import sqlite3
import ast

conn = sqlite3.connect(".pyqual/pipeline.db")
conn.row_factory = sqlite3.Row

# All failed stages
rows = conn.execute("""
    SELECT timestamp, kwargs, duration_ms
    FROM pipeline_logs
    WHERE function_name = 'stage_done' AND level = 'WARNING'
    ORDER BY id DESC
""").fetchall()

for row in rows:
    kw = ast.literal_eval(row["kwargs"])
    print(f"{row['timestamp'][:19]}  {kw['stage']:<15} rc={kw['returncode']}  {kw.get('stderr_tail', '')[:80]}")
```

### Useful SQL Queries

```sql
-- Pipeline run history (pass/fail, duration)
SELECT timestamp, kwargs FROM pipeline_logs
WHERE function_name = 'pipeline_end'
ORDER BY id DESC LIMIT 10;

-- All gate failures
SELECT timestamp, kwargs FROM pipeline_logs
WHERE function_name = 'gate_check' AND level = 'WARNING'
ORDER BY id DESC;

-- Fix stage output (LLM responses)
SELECT timestamp, kwargs FROM pipeline_logs
WHERE function_name = 'stage_done'
  AND kwargs LIKE '%''stage'': ''fix''%'
  AND kwargs LIKE '%stdout_tail%'
ORDER BY id DESC LIMIT 5;

-- Coverage history over time
SELECT timestamp, kwargs FROM pipeline_logs
WHERE function_name = 'gate_check'
  AND kwargs LIKE '%''metric'': ''coverage''%'
ORDER BY id;

-- Stage durations for performance analysis
SELECT timestamp, kwargs, duration_ms FROM pipeline_logs
WHERE function_name = 'stage_done'
  AND kwargs NOT LIKE '%''skipped'': True%'
ORDER BY duration_ms DESC LIMIT 20;

-- Count runs per day
SELECT DATE(timestamp) as day, COUNT(*) as runs
FROM pipeline_logs
WHERE function_name = 'pipeline_start'
GROUP BY day ORDER BY day;
```

### From CLI (via `pyqual logs --sql`)

```bash
# Coverage trend
pyqual logs --sql "SELECT timestamp, kwargs FROM pipeline_logs WHERE function_name='gate_check' AND kwargs LIKE '%coverage%' ORDER BY id"

# Slowest stages
pyqual logs --sql "SELECT kwargs, duration_ms FROM pipeline_logs WHERE function_name='stage_done' ORDER BY duration_ms DESC LIMIT 10"

# Total pipeline runs
pyqual logs --sql "SELECT COUNT(*) as total_runs FROM pipeline_logs WHERE function_name='pipeline_end'"
```

## LLX History File (`.pyqual/llx_history.jsonl`)

Each line is a JSON object recording one LLX fix run:

```json
{
    "timestamp": "2026-03-31T15:05:51.123456",
    "stage": "fix",
    "model": "openrouter/qwen/qwen3-coder-next",
    "small_model": "claude-haiku-4-5-20251001",
    "issues_count": 5,
    "ok": true,
    "duration_s": 13.8,
    "prompt": "You are fixing code in /home/tom/...\nUse the smallest safe changes...\n\nIssue summary:\n- pyqual/cli.py - warning - Low maintainability index: 12.2 (threshold: 20)\n...\n\nAnalysis payload:\n{...}\n\nReturn code edits only.",
    "stdout_tail": "Generated fixes:\n..."
}
```

### Fields

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 when fix ran |
| `stage` | Stage name (usually `fix`) |
| `model` | Primary LLM model used |
| `small_model` | Secondary model for triage/classification |
| `issues_count` | Number of issues loaded from errors.json/TODO.md |
| `ok` | Whether fix completed successfully |
| `duration_s` | Fix duration in seconds |
| `prompt` | **Full LLX prompt** sent to the model (includes issues, analysis payload, instructions) |
| `stdout_tail` | Captured stdout from the fix tool |

### Reading from Python

```python
import json

with open(".pyqual/llx_history.jsonl") as f:
    for line in f:
        entry = json.loads(line)
        print(f"{entry['timestamp'][:19]}  model={entry['model']}  issues={entry['issues_count']}  ok={entry['ok']}")
        if entry.get("prompt"):
            print(f"  prompt: {entry['prompt'][:200]}...")
```

## Data Flow Diagram

```
pyqual run
  │
  ├─► pipeline.db (stage_done, gate_check, pipeline_start/end)
  │     └─► pyqual logs / pyqual watch / direct SQL
  │
  ├─► llx_history.jsonl (fix stage only: prompts, model, issues)
  │     └─► pyqual history --prompts
  │
  └─► stdout (streaming YAML — the primary user-facing output)
```

## What's NOT in the DB

| Data | Where to find it |
|------|-------------------|
| Full stage stdout (>2000 chars) | Use `pyqual run --stream` to see live |
| Vallm validation details | `./project/validation.toon.yaml` |
| Code analysis report | `./project/analysis.toon.yaml` |
| Prefact TODO items | `TODO.md` |
| Coverage report | `.pyqual/coverage.json` or `htmlcov/` |
| Git diff from fix stage | Use `git diff` or `git log` after push |
