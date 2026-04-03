# Git Plugin for pyqual

Plugin providing git repository operations with secret scanning and push protection detection.

## Features

- **Git Operations**: status, add, commit, push
- **Secret Scanning**: Detects secrets before push using multiple scanners
- **Push Protection**: Detects GitHub Push Protection violations
- **Pre-flight Checks**: Validate before attempting push

## Installation

This plugin is included with pyqual by default.

## Usage

### CLI Commands

```bash
# Check repository status
pyqual git status

# Stage files
pyqual git add -A

# Scan for secrets
pyqual git scan

# Create commit
pyqual git commit -m "feat: update" --if-changed

# Pre-flight check (dry-run)
pyqual git push --dry-run

# Push with protection detection
pyqual git push --detect-protection
```

### In pyqual.yaml

```yaml
metrics:
  git_uncommitted_files_max: 0
  git_secrets_found_max: 0
  git_secrets_critical_max: 0
  git_push_protection_errors_max: 0

stages:
  - name: git_scan
    run: pyqual git scan --json

  - name: git_status
    run: pyqual git status --json

  - name: git_commit
    run: pyqual git commit -m "feat: update" --if-changed --json

  - name: git_preflight
    run: pyqual git push --dry-run --json

  - name: git_push
    run: pyqual git push --detect-protection --json
```

## Secret Detection

The plugin uses a layered approach to secret detection:

1. **trufflehog** (if available) - Most comprehensive, verifies secrets
2. **gitleaks** (if available) - Fast regex-based scanning
3. **Built-in patterns** - Always available fallback

### Detected Secret Types

| Type | Severity | Example |
|------|----------|---------|
| GitHub tokens | CRITICAL | `ghp_...` |
| AWS Access Keys | CRITICAL | `AKIA...` |
| Private Keys | CRITICAL | `-----BEGIN RSA PRIVATE KEY-----` |
| Stripe Live Keys | CRITICAL | `sk_live_...` |
| API Keys | HIGH | Various patterns |
| JWT Tokens | HIGH | `eyJ...` |
| Database URLs | MEDIUM | `postgres://user:pass@host` |

### False Positive Filtering

The plugin automatically filters common false positives:
- Placeholder values (`your_key_here`, `example`, `test`)
- Hex color codes in CSS contexts
- SHA/MD5 hash values

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `git_uncommitted_files` | Number of uncommitted files |
| `git_staged_files` | Number of staged files |
| `git_commits_ahead` | Commits ahead of remote |
| `git_secrets_found` | Total secrets detected |
| `git_secrets_critical` | Critical severity secrets |
| `git_secrets_high` | High severity secrets |
| `git_scan_success` | 1.0 if no secrets found |
| `git_push_success` | 1.0 if push succeeded |
| `git_push_protection_violation` | 1.0 if GH013 detected |

## Testing

Run the test suite:

```bash
cd /path/to/pyqual
pytest pyqual/plugins/git/test.py -v
```

## Configuration

### Environment Variables

- `PYQUAL_GIT_SCAN_TRUFFLEHOG`: Enable/disable trufflehog (default: true)
- `PYQUAL_GIT_SCAN_GITLEAKS`: Enable/disable gitleaks (default: true)

### External Dependencies

Optional but recommended:
- `trufflehog` - `brew install trufflehog` or `pip install trufflehog`
- `gitleaks` - `brew install gitleaks`

## API Usage

```python
from pyqual import git_status, scan_for_secrets, preflight_push_check

# Check status
status = git_status(cwd="/path/to/repo")
print(f"Branch: {status['branch']}, Ahead: {status['ahead']}")

# Scan for secrets
result = scan_for_secrets(cwd="/path/to/repo")
if not result["success"]:
    for secret in result["secrets_found"]:
        print(f"Found {secret['type']} in {secret['file']}:{secret['line']}")

# Pre-flight check
preflight = preflight_push_check(cwd="/path/to/repo")
if not preflight["can_push"]:
    print("Push blocked:", preflight["blockers"])
```

## License

MIT License - same as pyqual
