"""Built-in tool presets for pipeline stages.

Instead of writing complex shell commands with output redirection and error
handling, declare ``tool: ruff`` in your stage and pyqual handles everything:

    stages:
      - name: lint
        tool: ruff

pyqual will:
1. Check if the tool binary exists (``shutil.which``)
2. Skip gracefully when ``optional: true`` and tool is missing
3. Run the correct command with JSON output
4. Capture output to ``.pyqual/<tool>.json`` automatically
5. Never fail the pipeline on a non-zero exit code from a lint/scan tool

External packages can register presets via:
- ``register_preset(name, preset)`` at runtime
- ``pyqual.tools`` entry point group (auto-discovered)
- ``custom_tools:`` section in ``pyqual.yaml``
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("pyqual.tools")

# ---------------------------------------------------------------------------
# Tool preset definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolPreset:
    """Definition of a built-in tool invocation preset."""

    binary: str
    command: str
    output: str
    allow_failure: bool = True

    def is_available(self) -> bool:
        """Check if the tool binary is on PATH."""
        return shutil.which(self.binary) is not None

    def shell_command(self, workdir_token: str = ".") -> str:
        """Return the full shell command string with output capture."""
        cmd = self.command.replace("{workdir}", workdir_token)
        if self.output:
            if " -o " in cmd or " --output " in cmd or " --output=" in cmd:
                return cmd
            return f"{cmd} > {self.output}"
        return cmd


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

TOOL_PRESETS: dict[str, ToolPreset] = {
    # -- Linters --
    "ruff": ToolPreset(
        binary="ruff",
        command="ruff check {workdir} --output-format=json",
        output=".pyqual/ruff.json",
    ),
    "pylint": ToolPreset(
        binary="pylint",
        command="pylint --output-format=json {workdir}",
        output=".pyqual/pylint.json",
    ),
    "flake8": ToolPreset(
        binary="flake8",
        command="flake8 --format=json {workdir}",
        output=".pyqual/flake8.json",
    ),
    "mypy": ToolPreset(
        binary="mypy",
        command="mypy --output=json {workdir}",
        output=".pyqual/mypy.json",
    ),

    # -- Documentation --
    "interrogate": ToolPreset(
        binary="interrogate",
        command="interrogate --generate-badge=never --format=json {workdir}",
        output=".pyqual/interrogate.json",
    ),

    # -- Complexity / maintainability --
    "radon": ToolPreset(
        binary="radon",
        command="radon mi {workdir} -j",
        output=".pyqual/radon.json",
    ),

    # -- Security --
    "bandit": ToolPreset(
        binary="bandit",
        command="bandit -r {workdir} -f json -o .pyqual/bandit.json",
        output="",
    ),
    "pip-audit": ToolPreset(
        binary="pip-audit",
        command="pip-audit --format=json --output=.pyqual/vulns.json",
        output="",
    ),
    "trufflehog": ToolPreset(
        binary="trufflehog",
        command="trufflehog git file://{workdir} --json",
        output=".pyqual/secrets.json",
    ),
    "gitleaks": ToolPreset(
        binary="gitleaks",
        command="gitleaks detect --source {workdir} --report-format json --report-path .pyqual/secrets.json",
        output="",
    ),
    "safety": ToolPreset(
        binary="safety",
        command="safety check --json",
        output=".pyqual/safety.json",
    ),

    # -- Testing --
    "pytest": ToolPreset(
        binary="pytest",
        command="pytest --cov --cov-report=json:.pyqual/coverage.json -q",
        output="",
        allow_failure=False,
    ),
    # -- Analysis --
    "code2llm": ToolPreset(
        binary="code2llm",
        command="code2llm {workdir} -f all -o ./project --no-chunk",
        output="",
        allow_failure=False,
    ),
    "vallm": ToolPreset(
        binary="vallm",
        command="vallm batch {workdir} --recursive --format toon --output ./project",
        output="",
        allow_failure=False,
    ),

    # -- Documentation --
    "code2docs": ToolPreset(
        binary="code2docs",
        command="code2docs {workdir} --readme-only",
        output="",
        allow_failure=True,
    ),

    # -- Duplication detection --
    "redup": ToolPreset(
        binary="redup",
        command="redup scan {workdir} --format toon --output ./project",
        output="",
        allow_failure=True,
    ),

    # -- Prefactoring / refactoring suggestions --
    "prefact": ToolPreset(
        binary="prefact",
        command="prefact -a",
        output="",
        allow_failure=True,
    ),

    # -- LLX-driven code fixing (reads TODO.md generated by prefact) --
    "llx-fix": ToolPreset(
        binary="llx",
        command="llx fix . --apply $([ -f TODO.md ] && echo '--errors TODO.md')",
        output="",
        allow_failure=True,
    ),
    # -- LLX-driven code fixing (reads .pyqual/errors.json gate failures) --
    "llx-fix-json": ToolPreset(
        binary="llx",
        command="llx fix . --apply $([ -f .pyqual/errors.json ] && echo '--errors .pyqual/errors.json')",
        output="",
        allow_failure=True,
    ),

    # -- Aider AI pair-programmer --
    "aider": ToolPreset(
        binary="aider",
        command="aider --yes-always --message \"$(cat TODO.md 2>/dev/null || echo 'Fix all issues')\"",
        output="",
        allow_failure=True,
    ),

    # -- SBOM --
    "cyclonedx": ToolPreset(
        binary="cyclonedx-py",
        command="cyclonedx-py -r -o .pyqual/sbom.json",
        output="",
    ),
}


_BUILTIN_NAMES: frozenset[str] = frozenset(TOOL_PRESETS.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_preset(name: str) -> ToolPreset | None:
    """Look up a tool preset by name (case-insensitive)."""
    return TOOL_PRESETS.get(name.lower())


def list_presets() -> list[str]:
    """Return sorted list of available preset names."""
    return sorted(TOOL_PRESETS.keys())


def is_builtin(name: str) -> bool:
    """Return True if *name* is a built-in (not externally registered) preset."""
    return name.lower() in _BUILTIN_NAMES


def register_preset(name: str, preset: ToolPreset, *, override: bool = False) -> None:
    """Register a custom tool preset at runtime.

    Call this from your own package, plugin, or ``conftest.py``:

        from pyqual.tools import ToolPreset, register_preset

        register_preset("my-linter", ToolPreset(
            binary="my-linter",
            command="my-linter check {workdir} --json",
            output=".pyqual/my-linter.json",
        ))

    Then use in pyqual.yaml:

        stages:
          - name: lint
            tool: my-linter

    Raises ``ValueError`` if *name* already exists and *override* is False.
    """
    key = name.lower()
    if key in TOOL_PRESETS and not override:
        raise ValueError(
            f"Tool preset '{name}' already registered. "
            f"Pass override=True to replace it."
        )
    TOOL_PRESETS[key] = preset
    log.info("registered tool preset: %s (binary=%s)", key, preset.binary)


def register_custom_tools_from_yaml(custom_tools: list[dict[str, Any]]) -> int:
    """Register tool presets from the ``custom_tools:`` YAML section.

    Expected format in pyqual.yaml::

        custom_tools:
          - name: my-linter
            binary: my-linter
            command: "my-linter check {workdir} --json"
            output: .pyqual/my-linter.json
            allow_failure: true

    Returns the number of presets registered.
    """
    count = 0
    for entry in custom_tools or []:
        name = entry.get("name", "").strip()
        if not name:
            raise ValueError("custom_tools entry missing 'name' field.")
        binary = entry.get("binary", name)
        command = entry.get("command", "")
        if not command:
            raise ValueError(f"custom_tools entry '{name}' missing 'command' field.")
        preset = ToolPreset(
            binary=binary,
            command=command,
            output=entry.get("output", ""),
            allow_failure=entry.get("allow_failure", True),
        )
        register_preset(name, preset, override=True)
        count += 1
    return count


def load_entry_point_presets() -> int:
    """Discover and load tool presets from ``pyqual.tools`` entry point group.

    Third-party packages can declare presets in their ``pyproject.toml``::

        [project.entry-points."pyqual.tools"]
        my-linter = "my_package:MY_PRESET"

    Where ``MY_PRESET`` is a ``ToolPreset`` instance.

    Returns the number of presets loaded.
    """
    count = 0
    try:
        from importlib.metadata import entry_points
        eps = entry_points()
        # Python 3.12+ returns SelectableGroups, older returns dict
        group = eps.select(group="pyqual.tools") if hasattr(eps, "select") else eps.get("pyqual.tools", [])
        for ep in group:
            try:
                obj = ep.load()
                if isinstance(obj, ToolPreset):
                    register_preset(ep.name, obj)
                    count += 1
                elif callable(obj):
                    result = obj()
                    if isinstance(result, ToolPreset):
                        register_preset(ep.name, result)
                        count += 1
                else:
                    log.warning("entry_point '%s': expected ToolPreset, got %s", ep.name, type(obj).__name__)
            except Exception as exc:
                log.warning("Failed to load entry_point '%s': %s", ep.name, exc)
    except Exception as exc:
        log.debug("entry_points discovery unavailable: %s", exc)
    return count


def resolve_stage_command(
    tool_name: str,
    workdir: str = ".",
) -> tuple[str, bool]:
    """Resolve a tool name to (shell_command, allow_failure).

    Raises ``ValueError`` if the tool preset is unknown.
    """
    preset = get_preset(tool_name)
    if preset is None:
        raise ValueError(
            f"Unknown tool preset: '{tool_name}'. "
            f"Available: {', '.join(list_presets())}. "
            f"Use 'run:' for custom commands."
        )
    cmd = preset.shell_command(workdir)
    return cmd, preset.allow_failure
