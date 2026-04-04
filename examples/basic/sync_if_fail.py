#!/usr/bin/env python3
"""Minimal example: Check gates and sync tickets if they fail.

Uses pyqual.sync_from_gates() - new in pyqual 0.1.x
"""
from pathlib import Path
from pyqual.tickets import sync_from_gates

# Check gates and auto-sync tickets if any fail
result = sync_from_gates(workdir=Path("."), dry_run=False, backends=["markdown"])

if result["all_passed"]:
    print("✅ All gates passed — no tickets needed.")
else:
    print(f"❌ {len(result['failures'])} gate(s) failed: {', '.join(result['failures'])}")
    if result["synced"]:
        print(f"✅ Tickets synced to: {', '.join(result['backends'])}")
