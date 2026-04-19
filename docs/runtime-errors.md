# Runtime Error Detection

Pyqual pipelines now automatically detect and track runtime errors from failed command executions. This feature provides visibility into application failures during testing, linting, and other pipeline stages.

## How it works

When a pipeline stage fails (non-zero exit code), pyqual automatically:

1. **Captures** the error details to `.pyqual/runtime_errors.json`
2. **Classifies** the error type based on return codes and stderr patterns
3. **Exposes** metrics for quality gates

**Note**: Runtime errors are captured from all failed stages, including optional stages (like `publish` or `push`). Optional stages are only skipped if the command doesn't exist, not if they fail with an error.

## Error classification

Runtime errors are automatically classified into these types:

- `timeout` - Command exceeded configured timeout (exit code 124, 125)
- `command_not_found` - Binary not found on PATH (exit code 127)
- `permission_denied` - Permission/execution error (exit code 126)
- `signal` - Terminated by signal (exit codes 128-129)
- `import_error` - Python import/module errors
- `syntax_error` - Syntax errors in code
- `runtime_exception` - Key/attribute errors and other exceptions
- `assertion_failed` - Assertion errors
- `test_failed` - Test failures (contains "test failed" or "failed tests")
- `unknown` - Unclassified errors

## Available metrics

Runtime errors expose the following metrics for gates:

- `runtime_errors` - Total count of all runtime errors
- `runtime_{type}` - Count by error type (e.g., `runtime_test_failed`, `runtime_syntax_error`)
- `runtime_errors_recent` - Errors from the last hour

## Example configuration

```yaml
name: my-project
stages:
  - name: test
    run: pytest
    timeout: 300
  - name: lint
    run: ruff check .
    timeout: 60

gates:
  - metric: runtime_errors
    operator: le
    threshold: 0
  - metric: runtime_test_failed
    operator: le
    threshold: 0
  - metric: runtime_syntax_error
    operator: le
    threshold: 0
  - metric: runtime_errors_recent
    operator: le
    threshold: 5

loop:
  max_iterations: 3
```

## Runtime errors file format

The `.pyqual/runtime_errors.json` file contains an array of error objects:

```json
[
  {
    "timestamp": "2024-01-01T10:00:00+00:00",
    "stage": "test",
    "command": "pytest",
    "tool": null,
    "returncode": 1,
    "duration_s": 1.234,
    "error_type": "test_failed",
    "message": "FAILED tests/test_example.py::test_case",
    "stdout_tail": "... last 500 chars of stdout ...",
    "stderr_tail": "... last 500 chars of stderr ..."
  }
]
```

The file automatically:
- Keeps only the last 100 errors to prevent unlimited growth
- Is created on-demand when errors occur
- Preserves chronological order (newest errors at the end)

## Integration with fix workflows

Runtime errors can be fed into fix workflows by adding a stage that consumes the errors:

```yaml
stages:
  - name: fix_runtime_errors
    when: metrics_fail
    run: llx fix . --apply --errors .pyqual/runtime_errors.json
```

This allows AI-powered tools to automatically attempt fixing runtime errors.

## Auto-tuning thresholds

Use the `pyqual tune` command to automatically optimize gate thresholds based on collected metrics:

```bash
# Preview suggested changes
pyqual tune --dry-run

# Apply aggressive thresholds (90% of current values)
pyqual tune --aggressive

# Apply conservative thresholds (with safety margin)
pyqual tune --conservative
```

The tune command analyzes your recent pipeline runs and suggests optimal thresholds for:
- `cc_max` - Cyclomatic complexity
- `vallm_pass_min` - Code quality score
- `coverage_min` - Test coverage
- `secrets_found_max` - Always set to 0

## Viewing runtime errors

You can inspect runtime errors directly:

```bash
# View all runtime errors
cat .pyqual/runtime_errors.json | jq

# View recent errors (last hour)
cat .pyqual/runtime_errors.json | \
  jq '[.[] | select(.timestamp > (now - 3600 | strftime("%Y-%m-%dT%H:%M:%S%z")))]'

# Count errors by type
cat .pyqual/runtime_errors.json | \
  jq 'group_by(.error_type) | map({error_type: .[0].error_type, count: length})'
```

## Best practices

1. **Set appropriate timeouts** for stages to detect hangs early
2. **Monitor `runtime_errors_recent`** to catch recurring issues
3. **Use specific error type gates** (e.g., `runtime_syntax_error`) for targeted quality control
4. **Clear errors periodically** in CI to prevent stale errors from affecting builds
5. **Integrate with fix workflows** to enable automatic remediation

### No runtime errors file
The file is only created when errors occur. If you expect errors but don't see the file:
- Check if stages are actually failing (non-zero exit codes)
- Verify stages aren't marked as `optional: true`
- Ensure `allow_failure` isn't set to True

### Stale errors affecting gates
Runtime errors persist across pipeline runs. To clear them:
```bash
rm .pyqual/runtime_errors.json
```

### Too many errors
The file automatically limits to 100 errors. If you need more history:
- Adjust the limit in `pipeline.py` (line 600)
- Or implement your own error rotation strategy
