# Docs Plugin

Documentation quality analysis for pyqual.

## Overview

The docs plugin ensures your project has high-quality documentation:

- **README analysis** — Checks for essential sections (Install, Usage, License)
- **Docstring coverage** — Measures Python docstring completeness via interrogate
- **Link checking** — Validates external links in documentation
- **Changelog freshness** — Ensures changelog is maintained

## Installation

```bash
pip install interrogate

# Optional: install lychee for link checking
# See: https://lychee.cli.rs/
cargo install lychee
```

## Metrics Collected

| Metric | Description | Target |
|--------|-------------|--------|
| `docs_readme_sections` | Number of README sections | ≥ 5 |
| `docs_readme_has_install` | Has installation section | 1.0 |
| `docs_readme_has_usage` | Has usage section | 1.0 |
| `docs_readme_has_license` | Has license section | 1.0 |
| `docs_docstring_coverage` | Docstring coverage % | ≥ 80% |
| `docs_missing_docstrings` | Missing docstrings count | 0 |
| `docs_broken_links` | Broken external links | 0 |
| `docs_changelog_exists` | Changelog exists | 1.0 |
| `docs_changelog_days` | Days since last update | ≤ 30 |

## Configuration Example

```yaml
pipeline:
  name: documentation-quality

  metrics:
    docs_readme_sections_min: 5
    docs_docstring_coverage_min: 80
    docs_broken_links_max: 0
    docs_changelog_days_max: 30

  stages:
    - name: docs_check
      run: |
        # Check README quality
        python3 -c "
          from pyqual.plugins.docs import check_readme, docs_quality_summary
          import json
          r = check_readme()
          json.dump(r, open('.pyqual/docs_readme.json', 'w'))
          s = docs_quality_summary()
          json.dump(s, open('.pyqual/docs_summary.json', 'w'))
        "
      when: first_iteration
      optional: true

    - name: docstring_coverage
      run: interrogate pyqual --generate-badge .pyqual/docstring_badge.svg -v --format json > .pyqual/docstring_coverage.json 2>&1 || true
      when: first_iteration
      optional: true

  loop:
    max_iterations: 1
    on_fail: report
```

## Programmatic API

```python
from pyqual.plugins.docs import (
    DocsCollector,
    check_readme,
    run_interrogate,
    check_links,
    docs_quality_summary,
)

# Check README quality
readme = check_readme()
print(f"Sections: {readme['section_count']}")
print(f"Has install: {readme['has_install']}")
print(f"Is quality: {readme['is_quality']}")

# Get docstring coverage
coverage = run_interrogate(paths=["myapp"])
print(f"Coverage: {coverage['coverage']:.1f}%")
print(f"Missing: {coverage['missing']} functions")

# Check external links
links = check_links(files=["README.md", "docs/*.md"])
print(f"Broken links: {links['broken_count']}")

# Full documentation summary
summary = docs_quality_summary()
print(f"Complete: {summary['is_complete']}")
print(f"Recommendations: {summary['recommendations']}")
```

## README Quality Criteria

A quality README should have:
1. **Title** (H1) — Project name
2. **Description** — What the project does
3. **Installation** — How to install
4. **Usage** — How to use it
5. **License** — License information

## Docstring Coverage

Uses `interrogate` to measure:
- Public modules
- Classes
- Methods
- Functions

Target: 80%+ coverage for production code.

## Tags

- `documentation`
- `readme`
- `docstrings`
- `links`
- `quality`

## Version

1.0.0
