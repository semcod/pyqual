#!/usr/bin/env python3
"""Automated ticket closer based on pyqual quality gates.

Marks planfile tickets as 'done' if:
1. All quality gates in pyqual.yaml pass.
2. The ticket is currently 'open' or 'in_progress'.
3. (Optional) The ticket is related to recently modified files.
"""

import os
import subprocess
import sys
from pathlib import Path

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet
from planfile import Planfile, TicketStatus


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


def main():
    workdir = Path.cwd()
    config_path = workdir / "pyqual.yaml"
    
    if not config_path.exists():
        print(f"✗ pyqual.yaml not found in {workdir}")
        sys.exit(1)

    print("🔍 Evaluating Quality Gates...")
    config = PyqualConfig.load(config_path)
    gate_set = GateSet(config.gates)
    results = gate_set.check_all(workdir)
    
    all_passed = True
    for res in results:
        print(f"  {res}")
        if not res.passed:
            all_passed = False

    if not all_passed:
        print("\n❌ Quality gates failed. Skipping automated task closure.")
        sys.exit(0)  # Exit 0 as this is a normal conditional skip

    print("\n✅ All quality gates passed! Identifying tickets to close...")
    
    from planfile.core.store import PlanfileStore
    store = PlanfileStore(str(workdir))
    tickets = store.list_tickets("all")
    print(f"DEBUG: Found {len(tickets)} tickets in store {store.root}")
    changed_files = get_changed_files()
    
    closed_count = 0
    for ticket in tickets:
        if ticket.status in [TicketStatus.done]:
            continue
            
        # Match ticket to work:
        # 1. If ticket explicitly lists files, check if any matched
        # 2. If it is a strategy-linked ticket, check if its rule/context matches
        
        should_close = False
        
        # Files match
        ticket_files = ticket.sync.get("files", [])
        if any(f in changed_files for f in ticket_files):
            should_close = True
            
        # Simple heuristic: if it's in_progress, it's likely what we just fixed
        print(f"    Checking {ticket.id} status: {ticket.status} (type: {type(ticket.status)})")
        if str(ticket.status) == "in_progress" or ticket.status == TicketStatus.in_progress:
            should_close = True
            
        # Fallback if no specific file mapping: 
        # If the project is perfect, we might want to close all logic-related tasks 
        # But let's be conservative for now.

        if should_close:
            print(f"  ✓ Closing {ticket.id}: {ticket.title}")
            store.update_ticket(ticket.id, status=TicketStatus.done)
            closed_count += 1

    if closed_count > 0:
        print(f"\n🎉 Successfully marked {closed_count} tickets as DONE.")
    else:
        print("\nℹ️ No matching active tickets found to close.")


if __name__ == "__main__":
    main()
