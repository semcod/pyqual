# Custom Plugins Example

Build your own `MetricCollector` plugins to extend pyqual with custom metrics.

## Files

- `performance_collector.py` — Custom collector that reads benchmark/performance JSON
- `code_health_collector.py` — Composite collector combining multiple code health signals
- `pyqual.yaml` — Pipeline config using custom plugin metrics

## Quick Start

```bash
cd examples/custom_plugins

# Register the plugin (from project root)
python performance_collector.py   # self-test mode
python code_health_collector.py   # self-test mode
```

## How It Works

1. Subclass `MetricCollector` and implement `collect(workdir) -> dict[str, float]`
2. Register with `PluginRegistry.register(YourCollector)`
3. Add gate thresholds to `pyqual.yaml` using the metric names your collector produces

## Plugin Structure

```python
from pyqual.plugins import MetricCollector, PluginRegistry, PluginMetadata

class MyCollector(MetricCollector):
    name = "my-tool"
    metadata = PluginMetadata(
        name="my-tool",
        description="What it does",
        version="1.0.0",
        tags=["custom"],
    )

    def collect(self, workdir: Path) -> dict[str, float]:
        # Read from workdir/.pyqual/<your-file>.json
        # Return dict of metric_name -> float_value
        return {}

PluginRegistry.register(MyCollector)
```

## Metrics Produced

### PerformanceCollector (`performance`)

| Metric | Description | Source |
|--------|-------------|--------|
| `perf_p50_ms` | Median latency (ms) | `.pyqual/performance.json` |
| `perf_p99_ms` | 99th percentile latency (ms) | `.pyqual/performance.json` |
| `perf_rps` | Requests per second | `.pyqual/performance.json` |
| `perf_error_rate` | Error rate (%) | `.pyqual/performance.json` |

### CodeHealthCollector (`code-health`)

| Metric | Description | Source |
|--------|-------------|--------|
| `health_score` | Weighted composite score (0-100) | computed |
| `health_tech_debt_hours` | Estimated tech debt (hours) | `.pyqual/code_health.json` |
| `health_todo_count` | Open TODO count | `.pyqual/code_health.json` |
| `health_dead_code_pct` | Dead code percentage | `.pyqual/code_health.json` |

## pyqual.yaml

See [pyqual.yaml](pyqual.yaml) for complete configuration with custom plugins.
