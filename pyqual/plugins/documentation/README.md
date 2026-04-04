# Documentation Plugin

Documentation completeness and quality analysis for pyqual.

## Overview

The documentation plugin ensures your project has comprehensive documentation:

- **Required files** — Checks for README, LICENSE, CONTRIBUTING, CHANGELOG, etc.
- **README quality** — Analyzes sections, badges, code examples, installation instructions
- **License detection** — Identifies license type (MIT, Apache-2.0, GPL, etc.)
- **Documentation folder** — Checks docs/ folder structure and content
- **pyproject.toml** — Validates package metadata completeness
- **Docstring coverage** — Measures Python docstring coverage

## Metrics Collected

| Metric | Description | Target |
|--------|-------------|--------|
| `readme_exists` | README file exists | 1.0 |
| `readme_completeness` | % of required sections | ≥ 80% |
| `readme_sections_found` | Number of sections found | ≥ 5 |
| `readme_badges_count` | Number of badges | ≥ 3 |
| `license_exists` | LICENSE file exists | 1.0 |
| `license_spdx_score` | License clarity score | ≥ 80 |
| `docs_folder_exists` | docs/ folder exists | 1.0 |
| `docs_files_count` | Number of doc files | ≥ 5 |
| `pyproject_completeness` | Metadata completeness % | ≥ 80% |
| `docstring_coverage` | Python docstring % | ≥ 70% |
| `documentation_score` | Overall weighted score | ≥ 75 |

## Configuration Example

```yaml
pipeline:
  name: documentation-check

  metrics:
    readme_completeness_min: 80
    doc_required_files_min: 4
    docstring_coverage_min: 70
    license_present_eq: 1
    docs_folder_present_eq: 1

  stages:
    - name: documentation_check
      run: python3 -c "from pyqual.plugins.documentation import DocumentationCollector; import json; c=DocumentationCollector(); json.dump(c.collect(Path('.')), open('.pyqual/docs.json','w'))"
      when: first_iteration
      optional: true

  loop:
    max_iterations: 1
```

## Programmatic API

```python
from pyqual.plugins.documentation import DocumentationCollector
from pathlib import Path

# Analyze documentation
collector = DocumentationCollector()
metrics = collector.collect(Path("."))

# Check specific metrics
print(f"README completeness: {metrics['readme_completeness']:.1f}%")
print(f"Documentation score: {metrics['documentation_score']:.1f}")
print(f"License type MIT: {metrics.get('license_type_mit', 0)}")
print(f"Docstring coverage: {metrics.get('docstring_coverage', 0):.1f}%")

# Check for required sections
sections = ['installation', 'usage', 'contributing', 'license']
for section in sections:
    has_section = metrics.get(f'readme_has_{section}', 0)
    print(f"Has {section}: {bool(has_section)}")
```

## Documentation Best Practices

### README Structure

A quality README should have:
1. **Title and description** — Clear project name and purpose
2. **Badges** — Build status, version, coverage, license
3. **Installation** — How to install the package
4. **Usage** — Basic usage examples with code
5. **Contributing** — How to contribute (or link to CONTRIBUTING.md)
6. **License** — License type and link to LICENSE file

### Required Files

The plugin checks for:
- `README.md` — Project overview
- `LICENSE` — Legal terms
- `CONTRIBUTING.md` — Contribution guidelines
- `CHANGELOG.md` — Version history
- `CODE_OF_CONDUCT.md` — Community standards
- `SECURITY.md` — Security policy

### pyproject.toml Metadata

Complete metadata should include:
```toml
[project]
name = "myproject"
version = "1.0.0"
description = "A short description"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [{name = "Author", email = "author@example.com"}]
keywords = ["python", "package"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
]

[project.urls]
Repository = "https://github.com/user/repo"
Documentation = "https://readthedocs.org/projects/myproject"
```

## Tags

- `documentation`
- `readme`
- `license`
- `completeness`
- `quality`

## Version

1.0.0
