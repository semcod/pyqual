# Attack Plugin for pyqual

Aggressive merge automation and conflict resolution plugin.

## Features

- **Attack Check**: Detect merge conflicts and branch divergence
- **Attack Merge**: Automated merge with configurable strategy (ours/theirs/union)
- **Auto PR Merge**: Integration with GitHub CLI for PR automation
- **Metrics Collection**: Track merge success rates and conflict resolution

## Usage

### CLI Commands (if implemented)

```bash
pyqual attack check --json
pyqual attack merge --strategy=theirs --json
pyqual attack pr-merge --number=42
```

### In pyqual.yaml

```yaml
metrics:
  attack_merge_conflicts: 0
  attack_auto_merges: 0

stages:
  - name: attack_check
    run: |
      python3 -c "
        from pyqual.plugins.attack import attack_check
        import json
        result = attack_check()
        print(json.dumps(result))
      " > .pyqual/attack_check.json

  - name: attack_merge
    run: |
      python3 -c "
        from pyqual.plugins.attack import attack_merge
        import json
        result = attack_merge(strategy='theirs')
        print(json.dumps(result))
      " > .pyqual/attack_merge.json
    when: metrics_pass
```

## Merge Strategies

- `ours`: Prefer local changes
- `theirs`: Prefer incoming changes (default, "attack" mode)
- `union`: Combine both changes

## Metrics Collected

- `attack_conflicts_detected`: Number of merge conflicts
- `attack_branches_behind`: Commits behind main
- `attack_can_fast_forward`: Whether fast-forward is possible
- `attack_merge_success`: Whether last merge succeeded
- `attack_merge_conflicts_resolved`: Number of conflicts auto-resolved
- `attack_merge_files_changed`: Files affected by merge

## Version

1.0.0
