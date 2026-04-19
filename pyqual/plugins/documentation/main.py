"""Documentation plugin for pyqual — documentation completeness and quality.

Checks for:
- README.md presence and content quality
- LICENSE/COPYING file presence
- CONTRIBUTING.md presence
- CHANGELOG/HISTORY presence
- docs/ folder with documentation
- pyproject.toml metadata completeness
- README badges coverage
- Docstring coverage (from interrogate or pydocstyle)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pyqual.plugins import MetricCollector, PluginMetadata, PluginRegistry


@PluginRegistry.register
class DocumentationCollector(MetricCollector):
    """Documentation completeness and quality metrics.

    Measures:
    - Required files presence (readme, license, contributing, changelog)
    - Documentation folder coverage
    - README content quality (badges, sections)
    - pyproject.toml metadata completeness
    - Docstring coverage
    """

    name = "documentation"
    metadata = PluginMetadata(
        name="documentation",
        description="Documentation completeness: README, LICENSE, CONTRIBUTING, CHANGELOG, docs/, metadata",
        version="1.0.0",
        tags=["documentation", "readme", "license", "completeness", "quality"],
        config_example="""
metrics:
  readme_completeness_min: 80      # % README sections present
  doc_required_files_min: 3        # min count of README, LICENSE, CONTRIBUTING, CHANGELOG
  docstring_coverage_min: 70       # % docstring coverage
  license_present_eq: 1            # LICENSE file must exist
  docs_folder_present_eq: 1        # docs/ folder must exist

stages:
  - name: documentation_check
    tool: documentation
    when: always
    optional: true
""",
    )

    # Required documentation files
    REQUIRED_FILES = {
        "readme": ["README.md", "README.rst", "README.txt", "README"],
        "license": ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst", "COPYING", "COPYING.md"],
        "contributing": ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING.txt", "CONTRIBUTING"],
        "changelog": ["CHANGELOG.md", "CHANGELOG.rst", "HISTORY.md", "HISTORY.rst", "CHANGES.md", "NEWS.md"],
        "code_of_conduct": ["CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.rst"],
        "security": ["SECURITY.md", "SECURITY.rst"],
    }

    # README sections that indicate quality documentation
    README_SECTIONS = [
        ("installation", r"#+\s*(installation|install|getting started|quick start)"),
        ("usage", r"#+\s*(usage|how to use|examples|quickstart)"),
        ("api", r"#+\s*(api|reference|documentation|docs)"),
        ("contributing", r"#+\s*(contributing|development|how to contribute)"),
        ("license", r"#+\s*(license|licensing|legal)"),
        ("badges", r"!\[.*\]\(.*\)"),  # Any badge
        ("table_of_contents", r"#+\s*(table of contents|contents|toc)"),
    ]

    # Badge types we look for in README
    BADGE_PATTERNS = {
        "build": r"build|ci|github actions|gitlab|pipeline",
        "version": r"version|pypi|release|tag",
        "python": r"python|py\d|pypi.*py",
        "license": r"license|licence",
        "coverage": r"coverage|cov",
        "quality": r"quality|code quality|maintainability|sonar",
        "docs": r"docs|documentation|readthedocs|rtd",
        "downloads": r"download|downloads",
    }

    def _find_file(self, workdir: Path, names: list[str]) -> Path | None:
        """Find first matching file in workdir."""
        for name in names:
            path = workdir / name
            if path.exists():
                return path
        return None

    def _check_file_exists(self, workdir: Path, names: list[str]) -> bool:
        """Check if any of the named files exist."""
        return self._find_file(workdir, names) is not None

    def _read_pyproject(self, workdir: Path) -> dict[str, Any]:
        """Read pyproject.toml and return parsed dict."""
        p = workdir / "pyproject.toml"
        if not p.exists():
            return {}
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                # Fallback: minimal regex parsing
                return self._parse_pyproject_fallback(p)
        try:
            return tomllib.loads(p.read_text())
        except Exception:
            return {}

    def _parse_pyproject_fallback(self, path: Path) -> dict[str, Any]:
        """Minimal regex parser for pyproject.toml."""
        text = path.read_text()
        result: dict[str, Any] = {"project": {}}
        # Basic field extraction
        for key in ("name", "version", "description", "readme", "license", "requires-python"):
            m = re.search(rf'^\s*{key}\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if m:
                result["project"][key] = m.group(1)
        # Authors list
        if "authors" in text:
            result["project"]["authors"] = [{}]  # Simplified marker
        return result

    def _check_pyproject_metadata(self, workdir: Path) -> dict[str, float]:
        """Check pyproject.toml metadata completeness."""
        result: dict[str, float] = {}
        pyproject = self._read_pyproject(workdir)
        proj = pyproject.get("project", {})

        # Count required fields
        required_fields = ["name", "version", "description", "readme", "license", "requires-python"]
        present = sum(1 for f in required_fields if proj.get(f))
        result["pyproject_fields"] = float(present)
        result["pyproject_completeness"] = (present / len(required_fields)) * 100

        # Check for optional quality fields
        optional_fields = ["authors", "keywords", "classifiers", "urls"]
        optional_present = sum(1 for f in optional_fields if proj.get(f))
        result["pyproject_optional_fields"] = float(optional_present)

        # Has repository URL
        urls = proj.get("urls", {})
        has_repo = any(
            urls.get(k) for k in ["Repository", "Homepage", "Source", "Documentation"]
        )
        result["pyproject_has_repo_url"] = 1.0 if has_repo else 0.0

        return result

    def _analyze_readme(self, workdir: Path) -> dict[str, float]:
        """Analyze README content quality."""
        result: dict[str, float] = {}

        readme_path = self._find_file(workdir, self.REQUIRED_FILES["readme"])
        if not readme_path:
            result["readme_exists"] = 0.0
            result["readme_completeness"] = 0.0
            return result

        result["readme_exists"] = 1.0

        try:
            content = readme_path.read_text()
        except Exception:
            result["readme_completeness"] = 0.0
            return result

        # Check for sections
        sections_found = 0
        for section_name, pattern in self.README_SECTIONS:
            if re.search(pattern, content, re.IGNORECASE):
                sections_found += 1
                result[f"readme_has_{section_name}"] = 1.0
            else:
                result[f"readme_has_{section_name}"] = 0.0

        result["readme_sections_found"] = float(sections_found)
        result["readme_completeness"] = (sections_found / len(self.README_SECTIONS)) * 100

        # Analyze badges
        badges_found = 0
        for badge_type, pattern in self.BADGE_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                badges_found += 1
                result[f"readme_badge_{badge_type}"] = 1.0
            else:
                result[f"readme_badge_{badge_type}"] = 0.0

        result["readme_badges_count"] = float(badges_found)
        result["readme_badges_coverage"] = (badges_found / len(self.BADGE_PATTERNS)) * 100

        # Content length metrics
        lines = len(content.splitlines())
        result["readme_lines"] = float(lines)
        result["readme_length_ok"] = 1.0 if lines >= 20 else 0.0

        # Check for code examples
        has_code_blocks = "```" in content or "::" in content
        result["readme_has_code_examples"] = 1.0 if has_code_blocks else 0.0

        # Installation instructions
        has_install = re.search(r"(pip install|poetry add|conda install|setup.py)", content, re.IGNORECASE)
        result["readme_has_install"] = 1.0 if has_install else 0.0

        return result

    def _check_docs_folder(self, workdir: Path) -> dict[str, float]:
        """Check docs/ folder presence and content."""
        docs_paths = [workdir / "docs", workdir / "doc", workdir / "documentation"]
        docs_exists = any(p.exists() and p.is_dir() for p in docs_paths)
        result: dict[str, float] = {"docs_folder_exists": 1.0 if docs_exists else 0.0}
        if docs_exists:
            docs_path = next(p for p in docs_paths if p.exists())
            result.update(self._read_docs_details(docs_path))
        else:
            result.update({"docs_files_count": 0.0, "docs_has_index": 0.0,
                           "docs_has_api": 0.0, "docs_has_config": 0.0})
        return result

    def _read_docs_details(self, docs_path: Path) -> dict[str, float]:
        """Return content metrics for an existing docs folder."""
        doc_files = (
            list(docs_path.rglob("*.md"))
            + list(docs_path.rglob("*.rst"))
            + list(docs_path.rglob("*.txt"))
        )
        has_index = any(f.name.lower().startswith(("index", "readme", "home")) for f in doc_files)
        has_api = any("api" in f.name.lower() or "reference" in f.name.lower() for f in doc_files)
        has_conf = any((docs_path / f).exists() for f in ["conf.py", "mkdocs.yml", "mkdocs.yaml"])
        return {
            "docs_files_count": float(len(doc_files)),
            "docs_has_index": 1.0 if has_index else 0.0,
            "docs_has_api": 1.0 if has_api else 0.0,
            "docs_has_config": 1.0 if has_conf else 0.0,
        }

    def _check_required_files(self, workdir: Path) -> dict[str, float]:
        """Check presence of required documentation files."""
        result: dict[str, float] = {}

        required_count = 0
        for doc_type, filenames in self.REQUIRED_FILES.items():
            exists = self._check_file_exists(workdir, filenames)
            result[f"{doc_type}_exists"] = 1.0 if exists else 0.0
            if exists:
                required_count += 1

        result["doc_required_files_count"] = float(required_count)
        result["doc_required_files_pct"] = (required_count / len(self.REQUIRED_FILES)) * 100

        return result

    def _get_docstring_coverage(self, workdir: Path) -> dict[str, float]:
        """Get docstring coverage from interrogate output or estimate."""
        result: dict[str, float] = {}

        # Try interrogate JSON output first
        interrogate_path = workdir / ".pyqual" / "interrogate.json"
        if interrogate_path.exists():
            try:
                data = json.loads(interrogate_path.read_text())
                coverage = data.get("coverage") or data.get("percent_covered")
                if coverage is not None:
                    result["docstring_coverage"] = float(coverage)
                total = data.get("total") or data.get("total_objects")
                if total:
                    result["docstring_total"] = float(total)
                documented = data.get("documented") or data.get("documented_objects")
                if documented is not None and total:
                    result["docstring_missing"] = float(total - documented)
                return result
            except (json.JSONDecodeError, TypeError):
                pass

        # Try pydocstyle output
        pydocstyle_path = workdir / ".pyqual" / "pydocstyle.json"
        if pydocstyle_path.exists():
            try:
                data = json.loads(pydocstyle_path.read_text())
                if isinstance(data, list):
                    result["pydocstyle_errors"] = float(len(data))
                return result
            except (json.JSONDecodeError, TypeError):
                pass

        # No data available
        result["docstring_coverage"] = 0.0
        return result

    def _check_license_type(self, workdir: Path) -> dict[str, float]:
        """Check license file and identify type."""
        result: dict[str, float] = {}

        license_path = self._find_file(workdir, self.REQUIRED_FILES["license"])
        if not license_path:
            result["license_exists"] = 0.0
            result["license_spdx_score"] = 0.0
            return result

        result["license_exists"] = 1.0

        try:
            content = license_path.read_text()[:5000]  # First 5k chars
        except Exception:
            return result

        # Check for SPDX identifier in comments
        spdx_match = re.search(r"SPDX-License-Identifier:\s*(\S+)", content)
        if spdx_match:
            result["license_has_spdx"] = 1.0
            result["license_spdx_score"] = 100.0
        else:
            result["license_has_spdx"] = 0.0

        # Detect common licenses by content
        license_types = {
            "mit": r"permission\s+is\s+hereby\s+granted.*free\s+of\s+charge",
            "apache2": r"apache\s+license.*version\s*2",
            "gpl3": r"gnu\s+general\s+public\s+license.*version\s*3",
            "gpl2": r"gnu\s+general\s+public\s+license.*version\s*2",
            "bsd": r"redistribution\s+and\s+use.*source\s+and\s+binary\s+forms",
        }

        for lic_type, pattern in license_types.items():
            if re.search(pattern, content, re.IGNORECASE):
                result[f"license_type_{lic_type}"] = 1.0
                if "license_spdx_score" not in result:
                    result["license_spdx_score"] = 80.0  # Good but not perfect
                break
        else:
            # Unknown license type
            if "license_spdx_score" not in result:
                result["license_spdx_score"] = 50.0

        return result

    def collect(self, workdir: Path) -> dict[str, float]:
        """Collect all documentation metrics."""
        result: dict[str, float] = {}

        # Required files check
        result.update(self._check_required_files(workdir))

        # License analysis
        result.update(self._check_license_type(workdir))

        # README analysis
        result.update(self._analyze_readme(workdir))

        # pyproject.toml metadata
        result.update(self._check_pyproject_metadata(workdir))

        # Docs folder
        result.update(self._check_docs_folder(workdir))

        # Docstring coverage
        result.update(self._get_docstring_coverage(workdir))

        # Calculate overall documentation score
        scores = [
            result.get("readme_completeness", 0) * 0.25,
            result.get("doc_required_files_pct", 0) * 0.20,
            result.get("license_exists", 0) * 100 * 0.15,
            result.get("docs_folder_exists", 0) * 100 * 0.15,
            result.get("pyproject_completeness", 0) * 0.15,
            result.get("docstring_coverage", 0) * 0.10,
        ]
        result["documentation_score"] = sum(scores)

        return result
