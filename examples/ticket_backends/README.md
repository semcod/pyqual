# Multi-Backend Ticket Sync Examples

Demonstrates pyqual's `ticket_backends` configuration for syncing failed quality gates to multiple backends simultaneously.

## Overview

When `on_fail: create_ticket` is set, pyqual can now sync tickets to multiple backends:
- **markdown** — TODO.md file (default, always available)
- **github** — GitHub Issues (requires GITHUB_TOKEN)
- **all** — shorthand for all configured backends

## Examples

### 1. Markdown Only (Default)
```yaml
loop:
  on_fail: create_ticket
  ticket_backends:
    - markdown
```

### 2. GitHub Issues Only
```yaml
loop:
  on_fail: create_ticket
  ticket_backends:
    - github
```
Requires: `GITHUB_TOKEN` environment variable

### 3. Both TODO.md and GitHub
```yaml
loop:
  on_fail: create_ticket
  ticket_backends:
    - markdown
    - github
```

### 4. All Configured Backends
```yaml
loop:
  on_fail: create_ticket
  ticket_backends:
    - all
```

## Files

- `markdown-only.yaml` — Sync only to TODO.md
- `github-only.yaml` — Sync only to GitHub Issues
- `both-backends.yaml` — Sync to both TODO.md and GitHub
- `all-backends.yaml` — Use 'all' shorthand

## Testing

```bash
# Validate each configuration
pyqual validate -c markdown-only.yaml
pyqual validate -c github-only.yaml
pyqual validate -c both-backends.yaml
pyqual validate -c all-backends.yaml

# Check status shows correct backends
pyqual status -c both-backends.yaml
```

## Flow

```
pipeline fails → on_fail: create_ticket → sync to all ticket_backends
                                              ↓
                                    ┌──────────┼──────────┐
                                    ↓          ↓          ↓
                                 TODO.md   GitHub     Both
```

## Environment Setup

For GitHub sync, set your token:
```bash
export GITHUB_TOKEN=ghp_xxxxxxxx
```

Or create `.env` file:
```
GITHUB_TOKEN=ghp_xxxxxxxx
```
