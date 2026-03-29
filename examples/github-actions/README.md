# GitHub Actions Integration

Example of integrating pyqual with GitHub Actions CI/CD.

## .github/workflows/pyqual.yml

```yaml
name: pyqual Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pyqual
          pip install -e ".[dev]"
      
      - name: Run pyqual
        run: pyqual run
      
      - name: Upload metrics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pyqual-metrics
          path: .pyqual/
```

## pyqual.yaml (Project Root)

```yaml
pipeline:
  name: ci-quality-loop

  metrics:
    coverage_min: 80

  stages:
    - name: lint
      run: ruff check .
      when: always

    - name: test
      run: pytest --cov --cov-report=json:.pyqual/coverage.json
      when: always

  loop:
    max_iterations: 1  # CI should fail fast
    on_fail: block
```

## Notes

- `on_fail: block` stops immediately on failure
- `max_iterations: 1` for CI (no auto-fix loops)
- Artifacts preserve metrics for debugging
