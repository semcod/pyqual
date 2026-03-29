# Monorepo Setup

Example for monorepo with multiple packages.

## Structure

```
monorepo/
├── packages/
│   ├── package-a/
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyqual.yaml    # Package-specific config
│   └── package-b/
│       ├── src/
│       ├── tests/
│       └── pyqual.yaml
├── pyqual.yaml            # Root config (runs all)
└── pyproject.toml
```

## Root pyqual.yaml

Runs quality checks across all packages:

```yaml
pipeline:
  name: monorepo-quality

  metrics:
    coverage_min: 80

  stages:
    - name: package-a
      run: cd packages/package-a && pyqual run
      when: always

    - name: package-b
      run: cd packages/package-b && pyqual run
      when: always

    - name: integration
      run: pytest tests/integration/ -v
      when: always

  loop:
    max_iterations: 1
    on_fail: report
```

## Package-Specific pyqual.yaml

```yaml
# packages/package-a/pyqual.yaml
pipeline:
  name: package-a-quality

  metrics:
    coverage_min: 90  # Higher standard for core package

  stages:
    - name: test
      run: pytest tests/ -v --cov=src/package_a --cov-report=json:.pyqual/coverage.json
      when: always

  loop:
    max_iterations: 2
    on_fail: report
```

## Usage

```bash
# Check entire monorepo
cd monorepo
pyqual run

# Check single package
cd packages/package-a
pyqual run
```
