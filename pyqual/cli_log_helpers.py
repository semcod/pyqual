"""Helpers for ``pyqual logs``, ``pyqual watch``, and ``pyqual history`` commands.

Extracted from ``cli.py`` to reduce its size.  These are pure functions with
no typer/rich dependencies (except ``format_log_entry_row`` which returns
Rich markup strings).
"""

import ast
import sqlite3
from pathlib import Path

from pyqual.constants import LOG_DETAIL_MAX_LEN, PIPELINE_TABLE, TIMESTAMP_COL_WIDTH, TIMESTAMP_TIME_START


def query_nfo_db(db_path: Path, event: str = "", failed: bool = False,
                 tail: int = 0, sql: str = "", stage: str = "") -> list[dict]:
    """Query the nfo SQLite pipeline log and return structured dicts."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    if sql:
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Build query from filters
    where_clauses: list[str] = []
    params: list[str] = []

    if event:
        where_clauses.append("function_name = ?")
        params.append(event)

    if stage:
        where_clauses.append("kwargs LIKE ?")
        params.append(f"%'stage': '{stage}%")

    if failed:
        where_clauses.append("level = 'WARNING'")

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit = f"LIMIT {tail}" if tail > 0 else ""
    order = "ORDER BY rowid DESC" if tail > 0 else "ORDER BY rowid ASC"

    query = f"SELECT * FROM {PIPELINE_TABLE} {where} {order} {limit}"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    entries = [dict(r) for r in rows]
    if tail > 0:
        entries.reverse()
    return entries


def row_to_event_dict(row: dict) -> dict:
    """Parse an nfo SQLite row into a structured event dict.

    nfo stores kwargs as repr string in the 'kwargs' column.
    We parse it back to extract structured fields.
    """
    kwargs_raw = row.get("kwargs", "{}")
    try:
        data = ast.literal_eval(kwargs_raw) if isinstance(kwargs_raw, str) else kwargs_raw
    except (ValueError, SyntaxError):
        data = {}
    data["_timestamp"] = row.get("timestamp", "")
    data["_level"] = row.get("level", "")
    data["_function_name"] = row.get("function_name", "")
    data["_duration_ms"] = row.get("duration_ms")
    return data


def format_log_entry_row(entry: dict) -> tuple:
    """Return (ts, event_name, name, status, details) for one log entry."""
    ts = entry.get("_timestamp", "")[:TIMESTAMP_COL_WIDTH].replace("T", " ")[TIMESTAMP_TIME_START:]
    event_name = entry.get("event", entry.get("_function_name", ""))
    ok = entry.get("ok")
    status = "[green]PASS[/green]" if ok else ("[red]FAIL[/red]" if ok is False else "[dim]—[/dim]")
    name = ""
    details = ""

    if event_name == "stage_done":
        name = entry.get("stage", "")
        tool_info = f"tool:{entry['tool']}" if entry.get("tool") else ""
        rc_info = f"rc={entry.get('original_returncode', '?')}"
        dur = f"{entry.get('duration_s', 0):.1f}s"
        details = " ".join(filter(None, [tool_info, rc_info, dur]))
        if entry.get("skipped"):
            status = "[dim]SKIP[/dim]"
        if entry.get("stderr_tail"):
            details += f" err: {entry['stderr_tail'][:LOG_DETAIL_MAX_LEN]}"
    elif event_name == "gate_check":
        name = entry.get("metric", "")
        val = entry.get("value")
        thr = entry.get("threshold")
        op = {"le": "≤", "ge": "≥", "lt": "<", "gt": ">", "eq": "="}.get(str(entry.get("operator", "")), "?")
        val_s = f"{val:.1f}" if val is not None else "N/A"
        details = f"{val_s} {op} {thr}"
    elif event_name in ("pipeline_start", "pipeline_end"):
        name = entry.get("pipeline", "")
        parts: list[str] = []
        if event_name == "pipeline_start":
            parts.append(f"stages={entry.get('stages')}")
            parts.append(f"gates={entry.get('gates')}")
            parts.append(f"max_iter={entry.get('max_iterations')}")
            if entry.get("dry_run"):
                parts.append("DRY-RUN")
        else:
            parts.append("PASS" if entry.get("final_ok") else "FAIL")
            parts.append(f"iter={entry.get('iterations')}")
            dur_s = entry.get("total_duration_s", 0)
            parts.append(f"{dur_s:.1f}s" if isinstance(dur_s, (int, float)) else str(dur_s))
        details = " ".join(parts)
    else:
        details = str(entry)[:LOG_DETAIL_MAX_LEN]

    return ts, event_name, name, status, details
