"""Bulk project initialization with LLM-based project type detection.

Scans subdirectories of a given folder, collects a fingerprint of each project,
sends it to an LLM with a JSON schema, and generates tailored pyqual.yaml configs.

Usage (CLI):
    pyqual bulk-init /path/to/workspace
    pyqual bulk-init /path/to/workspace --dry-run
    pyqual bulk-init /path/to/workspace --no-llm   # heuristic-only fallback
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pyqual.constants import DEFAULT_CC_MAX, README_EXCERPT_MAX_CHARS, TOP_LEVEL_FILES_MAX

import yaml

logger = logging.getLogger("pyqual.bulk_init")

# ---------------------------------------------------------------------------
# JSON Schema for LLM response
# ---------------------------------------------------------------------------

PROJECT_CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PyqualProjectConfig",
    "description": "LLM-generated pyqual configuration decisions for a single project.",
    "type": "object",
    "required": ["project_type", "has_tests", "skip"],
    "properties": {
        "project_type": {
            "type": "string",
            "enum": [
                "python",
                "node",
                "typescript",
                "php",
                "rust",
                "go",
                "shell",
                "mixed",
                "docs",
                "unknown",
            ],
            "description": "Primary language / ecosystem of the project.",
        },
        "skip": {
            "type": "boolean",
            "description": "True if this directory is not a real project (artifacts, data, venv, etc.).",
        },
        "skip_reason": {
            "type": ["string", "null"],
            "description": "If skip=true, short reason why.",
        },
        "has_tests": {
            "type": "boolean",
            "description": "Whether the project has an existing test suite.",
        },
        "test_command": {
            "type": ["string", "null"],
            "description": "Command to run tests, e.g. 'python3 -m pytest -q', 'npm test', 'make test'.",
        },
        "lint_command": {
            "type": ["string", "null"],
            "description": "Lint command, e.g. 'ruff check .', 'npm run lint'. null = use tool preset.",
        },
        "lint_tool_preset": {
            "type": ["string", "null"],
            "description": "Built-in pyqual tool preset for linting: 'ruff', 'pylint', 'flake8', or null.",
        },
        "build_command": {
            "type": ["string", "null"],
            "description": "Build command if applicable, e.g. 'npm run build'.",
        },
        "extra_excludes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Additional directories to exclude from code2llm/vallm analysis.",
        },
        "cc_max": {
            "type": "integer",
            "default": 15,
            "description": "Max cyclomatic complexity threshold.",
        },
        "extra_stages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "run"],
                "properties": {
                    "name": {"type": "string"},
                    "run": {"type": "string"},
                    "when": {
                        "type": "string",
                        "enum": ["always", "metrics_fail", "metrics_pass"],
                        "default": "always",
                    },
                    "optional": {"type": "boolean", "default": False},
                },
            },
            "description": "Additional custom stages beyond the standard analyze/validate/fix/test pipeline.",
        },
    },
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Default exclude lists
# ---------------------------------------------------------------------------

BASE_EXCLUDES_SPACE = (
    ".git .venv .venv_test build dist __pycache__ .pytest_cache "
    ".code2llm_cache .benchmarks .mypy_cache .ruff_cache node_modules"
)
BASE_EXCLUDES_COMMA = BASE_EXCLUDES_SPACE.replace(" ", ",")


# ---------------------------------------------------------------------------
# Project fingerprint
# ---------------------------------------------------------------------------

@dataclass
class ProjectFingerprint:
    """Lightweight summary of a project directory sent to LLM for classification."""

    name: str
    path: str
    manifests: list[str] = field(default_factory=list)
    has_tests_dir: bool = False
    has_src_dir: bool = False
    file_extensions: list[str] = field(default_factory=list)
    top_level_files: list[str] = field(default_factory=list)
    node_scripts: dict[str, str] = field(default_factory=dict)
    makefile_targets: list[str] = field(default_factory=list)
    composer_scripts: dict[str, str] = field(default_factory=dict)
    pyproject_build_system: str | None = None
    pyproject_test_deps: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_pyqual_yaml: bool = False
    readme_excerpt: str = ""


def _collect_top_level_entries(project_dir: Path, fp: ProjectFingerprint) -> None:
    for child in sorted(project_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_file():
            fp.top_level_files.append(child.name)
        elif child.is_dir():
            if child.name in ("tests", "test"):
                fp.has_tests_dir = True
            if child.name == "src":
                fp.has_src_dir = True


def _collect_manifests(project_dir: Path, fp: ProjectFingerprint) -> None:
    manifest_names = [
        "pyproject.toml", "setup.py", "setup.cfg",
        "package.json", "composer.json",
        "Cargo.toml", "go.mod",
        "Makefile", "Taskfile.yml",
    ]
    for manifest_name in manifest_names:
        if (project_dir / manifest_name).exists():
            fp.manifests.append(manifest_name)


def _collect_file_extensions(project_dir: Path) -> list[str]:
    exts: set[str] = set()
    for f in project_dir.glob("*.*"):
        if f.is_file() and not f.name.startswith("."):
            exts.add(f.suffix)
    for f in project_dir.glob("*/*.*"):
        if f.is_file() and not f.name.startswith("."):
            exts.add(f.suffix)
    return sorted(exts)


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _collect_json_scripts(project_dir: Path, filename: str) -> dict[str, str]:
    path = project_dir / filename
    if not path.exists():
        return {}
    data = _load_json_object(path)
    if data is None:
        return {}
    scripts = data.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def _collect_makefile_targets(project_dir: Path) -> list[str]:
    makefile = project_dir / "Makefile"
    if not makefile.exists():
        return []
    try:
        targets: list[str] = []
        for line in makefile.read_text(errors="ignore").splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):", line)
            if m and not m.group(1).startswith("."):
                targets.append(m.group(1))
        return targets[:30]
    except OSError:
        return []


def _collect_pyproject_metadata(project_dir: Path, fp: ProjectFingerprint) -> None:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return
    try:
        import tomllib
    except ImportError:
        try:
            import importlib as _il
            tomllib = _il.import_module("tomli")  # type: ignore[assignment]
        except ImportError:
            tomllib = None  # type: ignore[assignment]
    if tomllib is None:
        return
    try:
        data = tomllib.loads(pyproject.read_text(errors="ignore"))
        bs = data.get("build-system", {}).get("requires", [])
        fp.pyproject_build_system = bs[0] if bs else None
        dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        fp.pyproject_test_deps = [d for d in dev_deps if "pytest" in d.lower() or "test" in d.lower()]
    except Exception:
        pass


def _collect_readme_excerpt(project_dir: Path) -> str:
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme = project_dir / readme_name
        if readme.exists():
            try:
                return readme.read_text(errors="ignore")[:500]
            except OSError:
                return ""
    return ""


def collect_fingerprint(project_dir: Path) -> ProjectFingerprint:
    """Collect a lightweight fingerprint from a project directory."""
    fp = ProjectFingerprint(name=project_dir.name, path=str(project_dir))
    _collect_top_level_entries(project_dir, fp)
    _collect_manifests(project_dir, fp)
    fp.has_pyqual_yaml = (project_dir / "pyqual.yaml").exists()
    fp.has_dockerfile = (project_dir / "Dockerfile").exists() or (project_dir / "docker-compose.yml").exists()
    fp.file_extensions = _collect_file_extensions(project_dir)
    fp.node_scripts = _collect_json_scripts(project_dir, "package.json")
    fp.composer_scripts = _collect_json_scripts(project_dir, "composer.json")
    fp.makefile_targets = _collect_makefile_targets(project_dir)
    _collect_pyproject_metadata(project_dir, fp)
    fp.readme_excerpt = _collect_readme_excerpt(project_dir)
    return fp


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

LLM_SYSTEM_PROMPT = """\
You are a project classifier for pyqual, a declarative quality gate pipeline tool.
Given a project fingerprint (directory structure, manifests, scripts), determine
the best pyqual configuration for that project.

Respond ONLY with valid JSON matching the provided schema. No markdown, no explanation.
"""


def _build_llm_prompt(fp: ProjectFingerprint) -> str:
    """Build the user prompt for LLM classification."""
    fp_dict = asdict(fp)
    # Trim large fields
    if len(fp_dict.get("readme_excerpt", "")) > README_EXCERPT_MAX_CHARS:
        fp_dict["readme_excerpt"] = f"{fp_dict['readme_excerpt'][:README_EXCERPT_MAX_CHARS]}..."
    if len(fp_dict.get("top_level_files", [])) > TOP_LEVEL_FILES_MAX:
        fp_dict["top_level_files"] = [*fp_dict["top_level_files"][:TOP_LEVEL_FILES_MAX], "..."]

    return (
        f"## Project fingerprint\n\n"
        f"```json\n{json.dumps(fp_dict, indent=2, ensure_ascii=False)}\n```\n\n"
        f"## Output JSON schema\n\n"
        f"```json\n{json.dumps(PROJECT_CONFIG_SCHEMA, indent=2)}\n```\n\n"
        f"Return a single JSON object matching the schema above. "
        f"Decide the best test/lint/build commands based on the project's manifests and scripts."
    )


@dataclass
class ProjectConfig:
    """Parsed LLM response — project-specific config decisions."""

    project_type: str = "unknown"
    skip: bool = False
    skip_reason: str | None = None
    has_tests: bool = False
    test_command: str | None = None
    lint_command: str | None = None
    lint_tool_preset: str | None = None
    build_command: str | None = None
    extra_excludes: list[str] = field(default_factory=list)
    cc_max: int = DEFAULT_CC_MAX
    extra_stages: list[dict[str, Any]] = field(default_factory=list)


def classify_with_llm(fp: ProjectFingerprint, model: str | None = None) -> ProjectConfig:
    """Send fingerprint to LLM, parse structured response."""
    from pyqual.llm import LLM

    llm = LLM(model=model)
    prompt = _build_llm_prompt(fp)

    response = llm.complete(
        prompt=prompt,
        system=LLM_SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=1000,
    )

    # Extract JSON from response (handle markdown fences)
    text = response.content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        json_lines = []
        in_fence = False
        for line in lines:
            if line.startswith("```") and not in_fence:
                in_fence = True
                continue
            if line.startswith("```") and in_fence:
                break
            if in_fence:
                json_lines.append(line)
        text = "\n".join(json_lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned invalid JSON for %s: %s", fp.name, exc)
        logger.debug("Raw LLM response: %s", response.content)
        return _classify_heuristic(fp)

    return ProjectConfig(
        project_type=data.get("project_type", "unknown"),
        skip=data.get("skip", False),
        skip_reason=data.get("skip_reason"),
        has_tests=data.get("has_tests", False),
        test_command=data.get("test_command"),
        lint_command=data.get("lint_command"),
        lint_tool_preset=data.get("lint_tool_preset"),
        build_command=data.get("build_command"),
        extra_excludes=data.get("extra_excludes", []),
        cc_max=data.get("cc_max", 15),
        extra_stages=data.get("extra_stages", []),
    )


# ---------------------------------------------------------------------------
# Heuristic fallback (no LLM)
# ---------------------------------------------------------------------------

def _classify_heuristic(fp: ProjectFingerprint) -> ProjectConfig:
    """Rule-based classification when LLM is unavailable."""
    # Skip non-projects
    skip_names = {"venv", ".venv", "node_modules", "__pycache__", "dist", "build"}
    if fp.name in skip_names:
        return ProjectConfig(skip=True, skip_reason="common artifact directory")
    if not fp.manifests and not fp.file_extensions:
        return ProjectConfig(skip=True, skip_reason="empty or data-only directory")

    # Skip directories that have no code manifests and only data/doc/config files
    _DATA_EXTS = {
        ".md", ".rst", ".txt", ".csv", ".json", ".yaml", ".yml", ".xml",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        ".wav", ".mp3", ".mp4", ".pdf", ".toon", ".log", ".bak",
        ".iml", ".ini", ".cfg", ".conf", ".lock", ".toml",
        ".html", ".css",
    }
    if not fp.manifests and set(fp.file_extensions) <= _DATA_EXTS:
        return ProjectConfig(skip=True, skip_reason="data/documentation-only directory")

    # Skip year-named archive directories (e.g. "2025") without manifests
    if fp.name.isdigit() and not fp.manifests:
        return ProjectConfig(skip=True, skip_reason="archive directory")

    has_python = "pyproject.toml" in fp.manifests or "setup.py" in fp.manifests
    has_node = "package.json" in fp.manifests
    has_composer = "composer.json" in fp.manifests
    has_makefile = "Makefile" in fp.manifests
    has_cargo = "Cargo.toml" in fp.manifests
    has_go = "go.mod" in fp.manifests

    # Python
    if has_python:
        test_cmd = "python3 -m pytest -q" if fp.has_tests_dir else "python3 -m pytest -q --co 2>/dev/null || true"
        return ProjectConfig(
            project_type="python",
            has_tests=fp.has_tests_dir,
            test_command=test_cmd,
            lint_tool_preset="ruff",
        )

    # Node.js / TypeScript
    if has_node:
        ptype = "typescript" if ".ts" in fp.file_extensions or ".tsx" in fp.file_extensions else "node"
        test_cmd = None
        lint_cmd = None
        build_cmd = None
        if "test" in fp.node_scripts:
            test_cmd = "npm test"
        if "lint" in fp.node_scripts:
            lint_cmd = "npm run lint"
        if "build" in fp.node_scripts:
            build_cmd = "npm run build"
        return ProjectConfig(
            project_type=ptype,
            has_tests="test" in fp.node_scripts,
            test_command=test_cmd,
            lint_command=lint_cmd,
            build_command=build_cmd,
        )

    # PHP
    if has_composer:
        test_cmd = "composer test" if "test" in fp.composer_scripts else None
        return ProjectConfig(
            project_type="php",
            has_tests="test" in fp.composer_scripts,
            test_command=test_cmd,
            lint_command="find . -name '*.php' -exec php -l {} \\;",
        )

    # Rust
    if has_cargo:
        return ProjectConfig(
            project_type="rust",
            has_tests=True,
            test_command="cargo test",
            lint_command="cargo clippy",
            build_command="cargo build",
        )

    # Go
    if has_go:
        return ProjectConfig(
            project_type="go",
            has_tests=True,
            test_command="go test ./...",
            lint_command="golangci-lint run",
        )

    # Makefile-only
    if has_makefile:
        test_cmd = "make test" if "test" in fp.makefile_targets else None
        lint_cmd = "make lint" if "lint" in fp.makefile_targets else None
        return ProjectConfig(
            project_type="mixed",
            has_tests="test" in fp.makefile_targets,
            test_command=test_cmd,
            lint_command=lint_cmd,
        )

    # Check for loose Python files
    py_exts = {".py"}
    if py_exts & set(fp.file_extensions):
        return ProjectConfig(
            project_type="python",
            has_tests=fp.has_tests_dir,
            test_command="python3 -m pytest -q --co 2>/dev/null || true",
        )

    # Docs-only
    md_exts = {".md", ".rst", ".txt"}
    if set(fp.file_extensions) <= md_exts | {""} :
        return ProjectConfig(skip=True, skip_reason="documentation-only directory")

    return ProjectConfig(project_type="unknown", skip=False)


# ---------------------------------------------------------------------------
# YAML generation
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Convert project name to a safe identifier for tool names."""
    return re.sub(r"[^a-z0-9]", "_", name.lower()).strip("_")


def generate_pyqual_yaml(project_name: str, cfg: ProjectConfig) -> str:
    """Generate pyqual.yaml content from a ProjectConfig."""
    sn = _safe_name(project_name)

    excludes_list = BASE_EXCLUDES_SPACE.split()
    excludes_list.extend(cfg.extra_excludes)
    excludes_space = " ".join(excludes_list)
    excludes_comma = ",".join(excludes_list)

    lines: list[str] = []
    lines.append("pipeline:")
    lines.append(f"  name: {project_name}-quality")
    lines.append("")
    lines.append("  metrics:")
    lines.append(f"    cc_max: {cfg.cc_max}")
    lines.append("    critical_max: 0")
    lines.append("")

    # Custom tools
    lines.append("  custom_tools:")
    lines.append(f"    - name: code2llm_{sn}")
    lines.append("      binary: code2llm")
    lines.append("      command: >-")
    lines.append(f"        code2llm {{workdir}} -f toon -o ./project --no-chunk")
    lines.append(f"        --exclude {excludes_space}")
    lines.append('      output: ""')
    lines.append("      allow_failure: false")
    lines.append("")
    lines.append(f"    - name: vallm_{sn}")
    lines.append("      binary: vallm")
    lines.append("      command: >-")
    lines.append(f"        vallm batch {{workdir}} --recursive --format toon --output ./project")
    lines.append(f"        --exclude {excludes_comma}")
    lines.append('      output: ""')
    lines.append("      allow_failure: false")
    lines.append("")

    # Stages
    lines.append("  stages:")
    lines.append(f"    - name: analyze")
    lines.append(f"      tool: code2llm_{sn}")
    lines.append("      optional: true")
    lines.append("      timeout: 0")
    lines.append("")
    lines.append(f"    - name: validate")
    lines.append(f"      tool: vallm_{sn}")
    lines.append("      optional: true")
    lines.append("      timeout: 0")

    # Lint stage
    if cfg.lint_tool_preset:
        lines.append("")
        lines.append("    - name: lint")
        lines.append(f"      tool: {cfg.lint_tool_preset}")
        lines.append("      optional: true")
    elif cfg.lint_command:
        lines.append("")
        lines.append("    - name: lint")
        lines.append(f"      run: {cfg.lint_command}")
        lines.append("      when: always")

    # Build stage
    if cfg.build_command:
        lines.append("")
        lines.append("    - name: build")
        lines.append(f"      run: {cfg.build_command}")
        lines.append("      when: always")

    # Fix stage
    lines.append("")
    lines.append("    - name: fix")
    lines.append("      tool: prefact")
    lines.append("      optional: true")
    lines.append("      when: metrics_fail")
    lines.append("      timeout: 900")

    # Test stage
    if cfg.test_command:
        lines.append("")
        lines.append("    - name: test")
        lines.append(f"      run: {cfg.test_command}")
        lines.append("      when: always")

    # Extra stages from LLM
    for stage in cfg.extra_stages:
        lines.append("")
        lines.append(f"    - name: {stage['name']}")
        lines.append(f"      run: {stage['run']}")
        when = stage.get("when", "always")
        lines.append(f"      when: {when}")
        if stage.get("optional"):
            lines.append("      optional: true")

    # Loop + env
    lines.append("")
    lines.append("  loop:")
    lines.append("    max_iterations: 3")
    lines.append("    on_fail: report")
    lines.append("")
    lines.append("  env:")
    lines.append("    LLM_MODEL: openrouter/qwen/qwen3-coder-next")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bulk init orchestrator
# ---------------------------------------------------------------------------

@dataclass
class BulkInitResult:
    """Summary of a bulk-init run."""

    created: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_nonproject: list[tuple[str, str]] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped_existing) + len(self.skipped_nonproject) + len(self.errors)


def bulk_init(
    root: Path,
    *,
    use_llm: bool = True,
    model: str | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> BulkInitResult:
    """Scan subdirectories of *root* and generate pyqual.yaml for each project.

    Parameters
    ----------
    root:
        Parent directory whose immediate children are projects.
    use_llm:
        If True, classify projects via LLM.  Falls back to heuristics on failure.
    model:
        Override LLM model name.
    dry_run:
        If True, do not write files — only return what would be generated.
    overwrite:
        If True, regenerate pyqual.yaml even when one already exists.
    """
    result = BulkInitResult()

    subdirs = sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    for project_dir in subdirs:
        name = project_dir.name

        # Collect fingerprint
        try:
            fp = collect_fingerprint(project_dir)
        except Exception as exc:
            result.errors.append((name, f"fingerprint error: {exc}"))
            continue

        # Skip existing
        if fp.has_pyqual_yaml and not overwrite:
            result.skipped_existing.append(name)
            continue

        # Classify
        try:
            if use_llm:
                try:
                    cfg = classify_with_llm(fp, model=model)
                except Exception as exc:
                    logger.warning("LLM classification failed for %s, using heuristic: %s", name, exc)
                    cfg = _classify_heuristic(fp)
            else:
                cfg = _classify_heuristic(fp)
        except Exception as exc:
            result.errors.append((name, f"classification error: {exc}"))
            continue

        # Handle skip
        if cfg.skip:
            result.skipped_nonproject.append((name, cfg.skip_reason or ""))
            continue

        # Generate YAML
        try:
            yaml_content = generate_pyqual_yaml(name, cfg)
        except Exception as exc:
            result.errors.append((name, f"generation error: {exc}"))
            continue

        # Validate generated YAML
        try:
            parsed = yaml.safe_load(yaml_content)
            if not parsed or "pipeline" not in parsed:
                raise ValueError("missing 'pipeline' key")
        except Exception as exc:
            result.errors.append((name, f"YAML validation error: {exc}"))
            continue

        # Write
        if not dry_run:
            target = project_dir / "pyqual.yaml"
            target.write_text(yaml_content)
            (project_dir / ".pyqual").mkdir(exist_ok=True)

        result.created.append(name)

    return result
