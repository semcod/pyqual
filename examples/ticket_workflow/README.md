# Ticket Workflow Example

Demonstrates pyqual's planfile-backed ticket management — auto-creating TODO.md entries and syncing GitHub Issues when quality gates fail.

## Overview

When `on_fail: create_ticket` is set in `pyqual.yaml`, failed quality gates automatically trigger planfile's TODO.md sync. This example shows:

1. **Automatic ticket creation** from gate failures
2. **Manual TODO.md sync** via CLI and Python API
3. **GitHub Issues sync** via planfile's GitHub backend
4. **Bidirectional sync** between TODO.md and external backends

## Files

- `pyqual.yaml` — Pipeline config with `on_fail: create_ticket`
- `sync_tickets.py` — Programmatic ticket sync with multiple modes

## Quick Start

### CLI (built-in commands)

```bash
# Sync TODO.md through planfile
pyqual tickets todo

# Sync GitHub Issues
pyqual tickets github

# Sync both
pyqual tickets all

# Dry-run (preview only)
pyqual tickets todo --dry-run
```

### Python script

```bash
cd examples/ticket_workflow

# Sync TODO.md
python sync_tickets.py

# Sync GitHub Issues
python sync_tickets.py --github

# Create tickets from gate failures
python sync_tickets.py --from-gates

# Preview without writing
python sync_tickets.py --from-gates --dry-run
```

### Pipeline integration

```bash
# Run pipeline — failures auto-create TODO.md tickets
pyqual run -c pyqual.yaml
```

## How It Works

```
pyqual run → stages execute → gates check
                                   │
                         ┌── PASS ─┴── FAIL ──┐
                         │                     │
                      Done ✅          planfile sync
                                       → TODO.md updated
                                       → GitHub Issues synced
```

### Flow details

1. Pipeline runs stages (analyze, lint, test)
2. Gates are checked against thresholds
3. If any gate fails and `on_fail: create_ticket`:
   - pyqual calls `sync_todo_tickets()`
   - planfile's markdown backend updates `TODO.md`
   - Failed metrics become checklist items
4. On next run, fixed issues are marked as completed

## Configuration

```yaml
loop:
  on_fail: create_ticket   # triggers planfile TODO sync
```

### Sync directions

- `"both"` — sync in both directions (default)
- `"from"` — pull from external source into TODO.md
- `"to"` — push TODO.md items to external source

## Requirements

- `planfile` (included as pyqual dependency)
- `.planfile/` directory initialized in project root
- For GitHub sync: `GITHUB_TOKEN` environment variable

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for the complete ticket workflow configuration.
