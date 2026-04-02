# Security Scanning Example

Quality gates for security scanning including secrets detection, vulnerability scanning, and SBOM compliance.

## Quick Start

```bash
# Install security tools
pip install bandit pip-audit
# Install trufflehog or gitleaks separately (see below)

# Run with pyqual
pyqual run
```

## Tools

| Tool | Purpose | Output File |
|------|---------|-------------|
| bandit | Python security issues | `.pyqual/bandit.json` |
| pip-audit | Dependency vulnerabilities | `.pyqual/vulns.json` |
| gitleaks/trufflehog | Secret scanning | `.pyqual/secrets.json` |
| sbom generator | SBOM generation | `.pyqual/sbom.json` |

## Metrics

| Metric | Description | Gate |
|--------|-------------|------|
| `bandit_high` | High severity issues | ≤ 0 |
| `bandit_medium` | Medium severity issues | ≤ 5 |
| `vuln_critical` | Critical vulnerabilities | ≤ 0 |
| `vuln_high` | High severity vulnerabilities | ≤ 0 |
| `secrets_found` | Leaked secrets count | ≤ 0 |
| `secrets_count` | Alias for secrets_found | ≤ 0 |
| `secrets_severity` | Max severity level (1-4) | ≤ 0 |
| `sbom_compliance` | SBOM completeness % | ≥ 95% |
| `license_blacklist` | Forbidden licenses | ≤ 0 |

### Secrets JSON Format

The secrets scanner outputs to `.pyqual/secrets.json`. Example format:

```json
[
  {"severity": "critical", "description": "AWS Access Key"},
  {"severity": "high", "description": "GitHub Token"},
  {"severity": "medium", "description": "Generic API Key"}
]
```

Severity mapping:
- `critical` = 4
- `high` = 3
- `medium` = 2
- `low` = 1
- unknown = 0

The `secrets_severity` metric returns the maximum severity level found.

## Installing Secret Scanners

```bash
# macOS
brew install trufflehog gitleaks

# Linux
# Download from GitHub releases:
# https://github.com/trufflesecurity/trufflehog/releases
# https://github.com/gitleaks/gitleaks/releases
```

## Generating Reports

```bash
# Bandit JSON
bandit -r . -f json -o .pyqual/bandit.json || true

# pip-audit JSON
pip-audit --format=json --output=.pyqual/vulns.json || true

# Gitleaks (default)
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . --report-format json --report-path .pyqual/secrets.json || true
fi

# TruffleHog (alternative)
if command -v trufflehog &> /dev/null; then
    trufflehog git file://. --json > .pyqual/secrets.json 2>/dev/null || true
fi

# SBOM (using cyclonedx or similar)
if command -v cyclonedx-py &> /dev/null; then
    cyclonedx-py -r -o .pyqual/sbom.json || true
fi
```

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for complete security scanning configuration.
