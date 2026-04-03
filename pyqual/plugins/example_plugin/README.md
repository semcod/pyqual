# Example Plugin for pyqual

Template plugin demonstrating the pyqual plugin structure.

## Purpose

This is a minimal example showing how to create a custom pyqual plugin. Use this as a starting point for your own plugins.

## Files

```
pyqual/plugins/example_plugin/
├── __init__.py      # Package exports
├── main.py          # Main plugin code with collector class
├── test.py          # Test suite
└── README.md        # This file
```

## Plugin Structure

### 1. main.py

Contains the `MetricCollector` subclass with:
- `name`: Unique plugin identifier
- `metadata`: PluginMetadata with description, version, tags, config_example
- `collect()`: Method to gather metrics from artifacts

### 2. __init__.py

Exports public API for the plugin package.

### 3. test.py

Test suite using pytest. Tests should cover:
- Plugin registration
- Metadata
- Metric collection
- Edge cases

### 4. README.md

Documentation for the plugin.

## Usage

### In pyqual.yaml

```yaml
metrics:
  example_metric_min: 0.8

stages:
  - name: example_stage
    run: echo '{"metric": 0.9}' > .pyqual/example.json
```

### CLI

```python
from pyqual import ExampleCollector

collector = ExampleCollector()
metrics = collector.collect(Path("."))
print(f"Example metric: {metrics.get('example_metric')}")
```

## Creating Your Own Plugin

1. Copy this directory:
   ```bash
   cp -r pyqual/plugins/example_plugin pyqual/plugins/my_plugin
   ```

2. Update files:
   - Rename `ExampleCollector` to your collector class
   - Update `name` attribute
   - Update `metadata` (description, version, tags)
   - Implement `collect()` method
   - Write tests
   - Update README

3. The plugin will be auto-discovered on next pyqual run

## Testing

Run the test suite:

```bash
cd /path/to/pyqual
pytest pyqual/plugins/example_plugin/test.py -v
```

## License

MIT License - same as pyqual
