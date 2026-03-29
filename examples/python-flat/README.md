# Python Flat Layout

Example for projects where Python modules are in the root directory.

## Project Structure

```
my-project/
├── my_module/
│   ├── __init__.py
│   └── utils.py
├── tests/
│   └── test_utils.py
├── pyqual.yaml
└── requirements.txt
```

## pyqual.yaml

```yaml
pipeline:
  name: flat-project-quality

  metrics:
    coverage_min: 70

  stages:
    - name: test
      run: pytest tests/ -v --cov=my_module --cov-report=json:.pyqual/coverage.json
      when: always

  loop:
    max_iterations: 1
    on_fail: report
```

## Key Differences from src-layout

- Coverage path points directly to module (no `src/` prefix)
- Simpler structure for small projects
- No separate build step needed
