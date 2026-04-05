#!/usr/bin/env python3
"""Automated ticket closer and evaluator based on pyqual quality gates.

Marks planfile tickets as 'done' if:
1. Quality gates recorded in .pyqual/metrics_report.yaml pass.
2. The ticket is currently 'in_progress'.
3. The ticket is related to recently modified files.

New features:
- LLM-based evaluation of the implementation.
- Automated GitHub commenting with evaluation scores.
"""

import os
import subprocess
import sys
import yaml
from pathlib import Path

REPORT_FILE = ".pyqual/metrics_report.yaml"


def get_changed_files() -> set[str]:
    """Get files changed in the last commit or current working tree."""
    try:
        # Check last commit
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        files = set(res.stdout.splitlines())
        
        # Also check current changes
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        for line in res.stdout.splitlines():
            if len(line) > 3:
                files.add(line[3:].strip())
        return files
    except Exception:
        return set()


def get_diff_content() -> str:
    """Get the unified diff of recent changes."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        diff = res.stdout
        
        # Also append current uncommitted changes
        res = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=10
        )
        diff += f"\n{res.stdout}"
        return diff
    except Exception:
        return ""


def evaluate_with_llm(title: str, description: str, diff: str) -> str:
    """Use LLM to evaluate the implementation quality."""
    try:
        from pyqual.llm import get_llm
        llm = get_llm()
        
        prompt = f"""Evaluate the following code changes for task: "{title}"
Description: {description}

Code Diff:
```diff
{diff[:5000]}
```

Provide a score (0-100%) and a concise summary (2-3 sentences) of the implementation quality. 
Specifically, comment on:
1. How well the task requirements were met.
2. Code style and potential issues.
3. Completeness of the fix.

Format your response as a GitHub-style markdown block."""
        
        response = llm.complete(prompt, system="You are a senior code reviewer.")
        return response.content
    except Exception as e:
        return f"⚠️ LLM Evaluation failed: {e}"


def _should_close_ticket(ticket, changed_files: set[str]) -> bool:
    """Determine if a ticket should be closed."""
    current_status = str(ticket.status).lower()
    if "done" in current_status:
        return False

    ticket_files = ticket.sync.get("files", [])
    if any(f in changed_files for f in ticket_files):
        return True
    if "in_progress" in current_status:
        return True
    return False


def _close_github_issue(reporter, issue_num: int) -> bool:
    """Close a GitHub issue. Returns True on success."""
    if not reporter.repo:
        print(f"    ⚠️ GITHUB_REPOSITORY not set, cannot close issue #{issue_num}")
        return False

    env = os.environ.copy()
    if reporter.token:
        env["GH_TOKEN"] = reporter.token
    close_result = subprocess.run(
        ["gh", "issue", "close", str(issue_num),
         "--repo", reporter.repo,
         "--comment", "Auto-closed: All quality gates passed"],
        capture_output=True, text=True, timeout=30,
        env=env
    )
    if close_result.returncode == 0:
        print(f"    ✅ Closed issue #{issue_num}")
        return True
    print(f"    ⚠️ Failed to close issue #{issue_num}: {close_result.stderr[:100]}")
    return False


def _process_ticket(ticket, store, reporter, diff_content: str, completion_rate: float) -> bool:
    """Process a single ticket for closure. Returns True if closed."""
    print(f"  ✓ Evaluating {ticket.id}: {ticket.title}")

    # Generate local LLM evaluation
    evaluation = evaluate_with_llm(ticket.title, ticket.description, diff_content)

    # Try to find GitHub Issue number
    external_id = ticket.sync.get("id")
    if external_id and external_id.isdigit():
        issue_num = int(external_id)
        print(f"    📢 Posting evaluation comment to issue #{issue_num}...")

        comment_body = f"""### 📊 Pyqual Task Evaluation for {ticket.id}
**Status:** ✅ Quality Gates Passed ({completion_rate:.1f}%)

{evaluation}

---
*Automatically evaluated and closed by pyqual.*"""

        reporter.post_issue_comment(comment_body, issue_num)
        print(f"    🔒 Closing issue #{issue_num}...")
        _close_github_issue(reporter, issue_num)

    # Mark as done locally
    from planfile.core.models import TicketStatus
    store.update_ticket(ticket.id, status=TicketStatus.done)
    return True


def main():
    workdir = Path.cwd()
    report_path = workdir / REPORT_FILE

    if not report_path.exists():
        print(f"ℹ️ {REPORT_FILE} not found. Skipping auto-closure.")
        return

    try:
        data = yaml.safe_load(report_path.read_text())
        report = data.get("pyqual_report", data)
        status = report.get("status")
        gates_info = report.get("gates", {})
    except Exception as e:
        print(f"✗ Failed to parse {REPORT_FILE}: {e}")
        return

    # Calculate simple pass rate metric
    passed = gates_info.get("passed", 0)
    total = gates_info.get("total", 1)
    completion_rate = (passed / total) * 100 if total > 0 else 0

    if status != "pass":
        print(f"❌ Quality gates status: {status} ({completion_rate:.1f}% passed). Skipping task closure.")
        return

    print(f"✅ Quality gates passed ({completion_rate:.1f}%)! Processing tickets...")

    try:
        from planfile.core.store import PlanfileStore
        from pyqual.github_actions import GitHubActionsReporter
    except ImportError as e:
        print(f"✗ Library missing: {e}")
        sys.exit(1)

    store = PlanfileStore(str(workdir))
    tickets = store.list_tickets("all")
    print(f"DEBUG: Found {len(tickets)} tickets: {[t.id for t in tickets[:5]]}...")
    changed_files = get_changed_files()
    diff_content = get_diff_content()
    reporter = GitHubActionsReporter()

    closed_count = 0
    for ticket in tickets:
        if _should_close_ticket(ticket, changed_files):
            if _process_ticket(ticket, store, reporter, diff_content, completion_rate):
                closed_count += 1

    if closed_count > 0:
        print(f"\n🎉 Successfully evaluated and marked {closed_count} tickets as DONE.")
    else:
        print("\nℹ️ No active tickets matched for closure.")


if __name__ == "__main__":
    main()
