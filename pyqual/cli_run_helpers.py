"""Helpers for the ``pyqual run`` command — stage summary extraction and report building.

These are pure functions with no CLI (typer/rich) dependencies, extracted from
``cli.py`` to reduce its size and improve testability.
"""

import re
from pathlib import Path
from typing import Any

from pyqual.constants import STAGE_OUTPUT_MAX_CHARS, TODO_HEAD_CHARS
from pyqual.stage_names import is_delivery_stage_name, is_fix_stage_name


def count_todo_items(todo_path: Path) -> int:
    """Count pending TODO items in TODO.md."""
    if not todo_path.exists():
        return 0
    content = todo_path.read_text()
    return content.count("- [ ]")


# ---------------------------------------------------------------------------
# Stage output → metric extraction
# ---------------------------------------------------------------------------

def extract_pytest_stage_summary(name: str, text: str) -> dict[str, Any]:
    lower = name.lower()
    if not any(kw in lower for kw in ("test", "pytest", "check")):
        return {}
    out: dict[str, Any] = {}
    m = re.search(r"(\d+) passed", text)
    if m:
        out["passed"] = int(m.group(1))
    m = re.search(r"(\d+) failed", text)
    if m:
        out["failed"] = int(m.group(1))
    m = re.search(r"(\d+) error", text)
    if m:
        out["errors"] = int(m.group(1))
    return out


def extract_lint_stage_summary(text: str) -> dict[str, Any]:
    m = re.search(r"Found (\d+) error", text)
    if m:
        return {"lint_errors": int(m.group(1))}
    if "All checks passed" in text:
        return {"lint_errors": 0}
    return {}


def extract_prefact_stage_summary(name: str, text: str) -> dict[str, Any]:
    m = re.search(r"\*?\*?Total issues:\*?\*?\s*(\d+)\s*active", text)
    if m:
        return {"tickets": int(m.group(1))}
    if "prefact" in name.lower():
        open_tickets = text.count("- [ ]")
        if open_tickets:
            return {"tickets": open_tickets}
    return {}


def extract_code2llm_stage_summary(name: str, text: str) -> dict[str, Any]:
    m = re.search(r"(\d+)\s+file", text)
    if m and ("analyze" in name.lower() or "code2llm" in name.lower()):
        out: dict[str, Any] = {"files": int(m.group(1))}
        m2 = re.search(r"([\d,]+)\s+line", text)
        if m2:
            out["lines"] = int(m2.group(1).replace(",", ""))
        return out
    return {}


def extract_validation_stage_summary(name: str, text: str) -> dict[str, Any]:
    lower_name = name.lower()
    if "valid" not in lower_name and "vallm" not in lower_name:
        return {}
    out: dict[str, Any] = {}
    m_cc = re.search(r"CC\u0304?[:\s=]+([0-9.]+)", text)
    if not m_cc:
        m_cc = re.search(r"\bcc[:\s=]+([0-9.]+)", text, re.IGNORECASE)
    if m_cc:
        out["cc"] = float(m_cc.group(1))
    m_crit = re.search(r"critical[:\s=]+([0-9]+)", text, re.IGNORECASE)
    if m_crit:
        out["critical"] = int(m_crit.group(1))
    return out


def extract_fix_stage_summary(name: str, text: str) -> dict[str, Any]:
    if not is_fix_stage_name(name):
        return {}
    out: dict[str, Any] = {}
    m = re.search(r"Selected:\s*\S+\s*\u2192\s*(.+)", text)
    if m:
        out["model"] = m.group(1).strip().split()[0]
    m_iss = re.search(r"Loaded (\d+) errors?", text)
    if m_iss:
        out["issues_loaded"] = int(m_iss.group(1))
    m2 = re.search(r"(\d+)\s+file[s]?\s+changed", text, re.IGNORECASE)
    if not m2:
        m2 = re.search(r"Applied\s+(\d+)\s+changes?", text, re.IGNORECASE)
    if not m2:
        m2 = re.search(r"(\d+)\s+file[s]?\s+(?:updated|modified|rewritten)", text, re.IGNORECASE)
    if m2:
        out["files_changed"] = int(m2.group(1))
    else:
        changed_files = set(re.findall(r"^\+\+\+ b/(.+)$", text, re.MULTILINE))
        if changed_files:
            out["files_changed"] = len(changed_files)
        else:
            m3 = re.search(r"(Applied|No changes|Updated|Modified|Fixed)[^\n]*", text, re.IGNORECASE)
            if m3:
                raw = m3.group(0)[:80]
                out["fix_status"] = re.sub(r"[^\x20-\x7e]", "", raw).strip()
    return out


def extract_mypy_stage_summary(name: str, text: str) -> dict[str, Any]:  # noqa: ARG001
    m = re.search(r"Found (\d+) error[s]? in (\d+) file", text)
    if m:
        return {"mypy_errors": int(m.group(1)), "mypy_files": int(m.group(2))}
    return {}


def extract_bandit_stage_summary(text: str) -> dict[str, Any]:
    m = re.search(r"High: (\d+)\s+Medium: (\d+)\s+Low: (\d+)", text)
    if not m:
        return {}
    return {
        "bandit_high": int(m.group(1)),
        "bandit_medium": int(m.group(2)),
        "bandit_low": int(m.group(3)),
    }


# ---------------------------------------------------------------------------
# Composite stage summary
# ---------------------------------------------------------------------------

def extract_stage_summary(name: str, stdout: str, stderr: str) -> dict[str, str]:
    """Extract key metrics from stage output as YAML-ready key: value pairs."""
    text = f"{stdout or ''}\n{stderr or ''}"
    metrics: dict[str, str] = {}
    metrics.update(extract_pytest_stage_summary(name, text))
    metrics.update(extract_lint_stage_summary(text))
    metrics.update(extract_prefact_stage_summary(name, text))
    metrics.update(extract_code2llm_stage_summary(name, text))
    metrics.update(extract_validation_stage_summary(name, text))
    metrics.update(extract_fix_stage_summary(name, text))
    metrics.update(extract_mypy_stage_summary(name, text))
    metrics.update(extract_bandit_stage_summary(text))
    return metrics


# ---------------------------------------------------------------------------
# Artifact enrichment
# ---------------------------------------------------------------------------

def _enrich_analysis(workdir: Path, stages: list[dict[str, Any]]) -> None:
    """Enrich analyze/code2llm stage from analysis.toon.yaml header."""
    analysis = workdir / "project" / "analysis.toon.yaml"
    if not analysis.exists():
        return
    hdr = "\n".join(analysis.read_text(errors="replace").splitlines()[:2])
    m_f = re.search(r"(\d+)f\s+(\d+)L", hdr)
    m_cc = re.search(r"CC\u0304?=([0-9.]+)", hdr)
    m_cr = re.search(r"critical:(\d+)", hdr)
    for sd in stages:
        if sd["name"] in ("analyze", "code2llm") and sd.get("status") != "skipped":
            if m_f:
                sd.setdefault("files", int(m_f.group(1)))
                sd.setdefault("lines", int(m_f.group(2)))
            if m_cc:
                sd.setdefault("cc", float(m_cc.group(1)))
            if m_cr:
                sd.setdefault("critical", int(m_cr.group(1)))


def _enrich_validation(workdir: Path, stages: list[dict[str, Any]]) -> None:
    """Enrich validate/vallm stage from validation.toon.yaml header."""
    validation = workdir / "project" / "validation.toon.yaml"
    if not validation.exists():
        return
    hdr = "\n".join(validation.read_text(errors="replace").splitlines()[:5])
    m_v = re.search(r"(\d+)\u2713\s+(\d+)\u26a0\s+(\d+)\u2717", hdr)
    m_s = re.search(r"passed:\s*\d+\s*\(([0-9.]+)%\)", hdr)
    for sd in stages:
        if sd["name"] in ("validate", "vallm") and sd.get("status") != "skipped":
            if m_v:
                sd.setdefault("vallm_passed", int(m_v.group(1)))
                sd.setdefault("vallm_warnings", int(m_v.group(2)))
                sd.setdefault("vallm_errors", int(m_v.group(3)))
            if m_s:
                sd.setdefault("vallm_pass_pct", float(m_s.group(1)))


def _enrich_todo(workdir: Path, stages: list[dict[str, Any]]) -> None:
    """Enrich prefact stage from TODO.md header."""
    todo = workdir / "TODO.md"
    if not todo.exists():
        return
    head = todo.read_text(errors="replace")[:TODO_HEAD_CHARS]
    m_t = re.search(r"\*?\*?Total issues:\*?\*?\s*(\d+)\s*active(?:,\s*(\d+)\s*completed)?", head)
    if not m_t:
        return
    for sd in stages:
        if sd["name"] in ("prefact",) and sd.get("status") != "skipped":
            sd.setdefault("tickets", int(m_t.group(1)))
            if m_t.group(2):
                sd.setdefault("tickets_completed", int(m_t.group(2)))


def enrich_from_artifacts(workdir: Path, stages: list[dict[str, Any]]) -> None:
    """Enrich stage dicts with metrics read from artifact files on disk."""
    _enrich_analysis(workdir, stages)
    _enrich_validation(workdir, stages)
    _enrich_todo(workdir, stages)


# ---------------------------------------------------------------------------
# Run summary building
# ---------------------------------------------------------------------------

def infer_fix_result(stage: dict[str, Any]) -> str:
    files_changed = stage.get("files_changed")
    if isinstance(files_changed, (int, float)):
        return "changed" if float(files_changed) > 0 else "no_changes"

    status = str(stage.get("fix_status", "")).strip().lower()
    if not status:
        return "unknown"
    if "no changes" in status or "no change" in status:
        return "no_changes"
    if any(token in status for token in ("applied", "changed", "updated", "modified", "fixed")):
        return "changed"
    return "unknown"


def _extract_todo_summary(stages: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract todo/prefact metrics from stage data."""
    result: dict[str, Any] = {}
    prefact_stage = next((s for s in stages if s.get("name") == "prefact"), None)
    if not prefact_stage or prefact_stage.get("status") == "skipped":
        return result
    tickets = prefact_stage.get("tickets")
    tickets_completed = prefact_stage.get("tickets_completed")
    if isinstance(tickets, (int, float)):
        result["todo_active"] = int(tickets)
    if isinstance(tickets_completed, (int, float)):
        result["todo_completed"] = int(tickets_completed)
    if isinstance(tickets, (int, float)) and isinstance(tickets_completed, (int, float)):
        result["todo_total"] = int(tickets) + int(tickets_completed)
    return result


def _extract_fix_summary(stages: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract fix-stage metrics from stage data."""
    result: dict[str, Any] = {}
    fix_stage = next(
        (
            s for s in stages
            if is_fix_stage_name(str(s.get("name", ""))) and s.get("status") != "skipped"
        ),
        None,
    )
    if not fix_stage:
        return result
    files_changed = fix_stage.get("files_changed")
    if isinstance(files_changed, (int, float)):
        result["fix_files_changed"] = int(files_changed)
    failed = fix_stage.get("failed")
    if isinstance(failed, (int, float)):
        result["fix_failed"] = int(failed)
    errors = fix_stage.get("errors")
    if isinstance(errors, (int, float)):
        result["fix_errors"] = int(errors)
    result["fix_result"] = infer_fix_result(fix_stage)
    return result


def _extract_delivery_summary(stages: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract publish/push failure details from stage data."""
    failures: list[str] = []
    for stage in stages:
        name = str(stage.get("name", "")).strip().lower()
        if not is_delivery_stage_name(name):
            continue
        if stage.get("status") != "failed":
            continue

        parts = [f"{name} failed"]
        rc = stage.get("rc")
        if isinstance(rc, (int, float)):
            parts[0] = f"{name} failed (rc={int(rc)})"
        stderr = str(stage.get("stderr", "")).strip()
        if stderr:
            parts.append(f": {stderr}")
        failures.append("".join(parts))

    if failures:
        return {"delivery_failures": failures}
    return {}


def build_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    stages = [
        stage
        for iteration in report.get("iterations", [])
        if isinstance(iteration, dict)
        for stage in iteration.get("stages", [])
        if isinstance(stage, dict)
    ]
    summary: dict[str, Any] = {}
    summary.update(_extract_todo_summary(stages))
    summary.update(_extract_fix_summary(stages))
    summary.update(_extract_delivery_summary(stages))
    return summary


def _format_ticket_summary(summary: dict[str, Any]) -> str | None:
    """Format ticket/TODO progress section."""
    todo_active = summary.get("todo_active", 0)
    todo_completed = summary.get("todo_completed", 0)
    todo_total = summary.get("todo_total", 0)
    todo_remaining = todo_total - todo_completed

    if todo_total == 0:
        return None

    ticket_parts = []
    if todo_completed > 0:
        ticket_parts.append(f"✓ {todo_completed} completed")
    if todo_remaining > 0:
        ticket_parts.append(f"○ {todo_remaining} remaining")
    if todo_active > 0 and todo_active != todo_remaining:
        ticket_parts.append(f"⚡ {todo_active} active")

    parts = [f"Tickets: {', '.join(ticket_parts)}"]
    pct = (todo_completed / todo_total) * 100
    parts.append(f"Progress: {pct:.0f}% ({todo_completed}/{todo_total})")
    return "; ".join(parts)


def _format_fix_summary(summary: dict[str, Any]) -> str | None:
    """Format fix stage outcomes section."""
    fix_result = summary.get("fix_result")
    if not fix_result or fix_result == "unknown":
        return None

    fix_parts = []
    files_changed = summary.get("fix_files_changed", 0)
    fix_failed = summary.get("fix_failed", 0)
    fix_errors = summary.get("fix_errors", 0)

    if files_changed > 0:
        fix_parts.append(f"✓ {files_changed} files changed")
    if fix_failed > 0:
        fix_parts.append(f"✗ {fix_failed} failed")
    if fix_errors > 0:
        fix_parts.append(f"⚠ {fix_errors} errors")

    if fix_parts:
        return f"Fix ({fix_result}): {' | '.join(fix_parts)}"
    return f"Fix: {fix_result}"


def _format_delivery_summary(summary: dict[str, Any]) -> str | None:
    """Format delivery/push outcomes section."""
    if "delivery_failures" not in summary:
        return None

    failures = summary["delivery_failures"]
    if isinstance(failures, list) and failures:
        return f"✗ Delivery failed: {'; '.join(str(item) for item in failures)}"
    return "✓ Delivered"


def format_run_summary(summary: dict[str, Any]) -> str:
    """Format run summary dict into human-readable string with ticket outcomes."""
    if not summary:
        return ""

    parts: list[str] = []

    # Each section is a separate helper
    ticket_section = _format_ticket_summary(summary)
    if ticket_section:
        parts.append(ticket_section)

    fix_section = _format_fix_summary(summary)
    if fix_section:
        parts.append(fix_section)

    delivery_section = _format_delivery_summary(summary)
    if delivery_section:
        parts.append(delivery_section)

    return f"[bold]Run summary[/bold]: {'; '.join(parts)}" if parts else ""


def get_last_error_line(text: str) -> str:
    """Return the last meaningful error line, filtering out informational noise."""
    if not text:
        return ""
    noise_prefixes = (
        "Using .gitignore", "Excluded ", "✓ ", "Results saved",
        "Processing ", "Scanning ", "Checking ", "Loading ", "Collecting ",
    )
    error_kws = ("error", "fail", "assert", "exception", "traceback",
                 "critical", "syntax", "invalid", "cannot", "no module")
    clean = [ln.strip() for ln in text.splitlines()
             if ln.strip() and not any(ln.strip().startswith(p) for p in noise_prefixes)]
    err_lines = [ln for ln in clean if any(kw in ln.lower() for kw in error_kws)]
    if err_lines:
        return err_lines[-1][:STAGE_OUTPUT_MAX_CHARS]
    return clean[-1][:STAGE_OUTPUT_MAX_CHARS] if clean else ""
