# Python Package (src-layout)

Example pyqual configuration for a Python package using src-layout.

## Project Structure

```
my-package/
├── src/
│   └── my_package/
│       ├── __init__.py
│       └── core.py
├── tests/
│   └── test_core.py
├── pyqual.yaml
└── pyproject.toml
```

## pyqual.yaml

```yaml
pipeline:
  name: my-package-quality

  metrics:
    coverage_min: 80

  stages:
    - name: lint
      run: ruff check src/ tests/
      when: always

    - name: test
      run: pytest tests/ -v --cov=src/my_package --cov-report=json:.pyqual/coverage.json
      when: always

  loop:
    max_iterations: 1
    on_fail: report
```

## Usage

```bash
cd my-package
pyqual init  # Creates default pyqual.yaml (customize as above)
pyqual run   # Execute quality pipeline
```
