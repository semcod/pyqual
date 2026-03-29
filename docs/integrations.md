# Ecosystem Integrations

pyqual is intentionally small (~800 lines). It orchestrates, not implements. It reads metrics from tools you already use.

## code2llm → Complexity Metrics

```yaml
stages:
  - name: analyze
    run: code2llm ./ -f toon,evolution
```

pyqual reads from `analysis_toon.yaml` or `analysis.toon`:

```yaml
SUMMARY:
  CC̄=2.5          # average cyclomatic complexity
  critical=0       # critical issues count
```

**Metrics extracted:** `cc`, `critical`

## vallm → Validation Pass Rate

```yaml
stages:
  - name: validate
    run: vallm batch ./ --recursive --errors-json > .pyqual/errors.json
```

pyqual reads from `validation_toon.yaml` or reads `.pyqual/errors.json`:

```yaml
SUMMARY:
  scanned: 100
  passed: 95 (95.0%)    # vallm_pass metric
  warnings: 5
```

**Metrics extracted:** `vallm_pass`, `error_count`

## pytest → Coverage

```yaml
stages:
  - name: test
    run: pytest --cov --cov-report=json:.pyqual/coverage.json
```

pyqual reads from `.pyqual/coverage.json` (pytest-cov output):

```json
{
  "totals": {
    "percent_covered": 92.5
  }
}
```

**Metrics extracted:** `coverage`

## Custom Integrations

Extend `GateSet._collect_metrics()` to add your own sources:

```python
from pyqual.gates import GateSet

class MyGateSet(GateSet):
    def _collect_metrics(self, workdir: Path) -> dict[str, float]:
        metrics = super()._collect_metrics(workdir)
        # Add custom metric source
        metrics.update(self._from_my_tool(workdir))
        return metrics
    
    def _from_my_tool(self, workdir: Path) -> dict[str, float]:
        # Parse your tool's output
        return {"my_metric": 42.0}
```

## Integration Summary

| Tool | Output File | Metrics | Optional? |
|------|-------------|---------|-----------|
| code2llm | `analysis_toon.yaml` | `cc`, `critical` | Yes |
| vallm | `validation_toon.yaml` | `vallm_pass`, `error_count` | Yes |
| pytest | `.pyqual/coverage.json` | `coverage` | Yes |
| custom | any | any | — |

**All integrations are optional.** Stages can be any shell commands.
