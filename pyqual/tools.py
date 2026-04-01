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

Presets are loaded from:
1. ``pyqual/default_tools.json`` — built-in defaults (shipped with pyqual)
2. ``pyqual.tools.json`` — user overrides in the project directory
3. ``custom_tools:`` section in ``pyqual.yaml``
4. ``register_preset()`` calls at runtime
5. ``pyqual.tools`` entry point group (auto-discovered)

To override a built-in preset, create ``pyqual.tools.json`` next to your
``pyqual.yaml`` with the same key::

    {
      "pytest": {
        "binary": "pytest",
        "command": "pytest --cov=mypackage -q",
        "output": "",
        "allow_failure": false
      },
      "my-custom-tool": {
        "binary": "my-tool",
        "command": "my-tool check {workdir}",
        "output": ".pyqual/my-tool.json"
      }
    }
"""

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("pyqual.tools")

USER_TOOLS_FILE = "pyqual.tools.json"

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
# JSON → ToolPreset loader
# ---------------------------------------------------------------------------

_DEFAULT_TOOLS_PATH = Path(__file__).parent / "default_tools.json"


def _preset_from_dict(d: dict[str, Any]) -> ToolPreset:
    """Create a ToolPreset from a JSON dict."""
    return ToolPreset(
        binary=d["binary"],
        command=d["command"],
        output=d.get("output", ""),
        allow_failure=d.get("allow_failure", True),
    )


def _load_json_presets(path: Path) -> dict[str, ToolPreset]:
    """Load tool presets from a JSON file. Returns empty dict on error."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            log.warning("tools JSON %s: expected object at top level", path)
            return {}
        result: dict[str, ToolPreset] = {}
        for name, entry in raw.items():
            try:
                result[name.lower()] = _preset_from_dict(entry)
            except (KeyError, TypeError) as exc:
                log.warning("tools JSON %s: skipping '%s': %s", path, name, exc)
        return result
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to load tools JSON %s: %s", path, exc)
        return {}


def _load_default_presets() -> dict[str, ToolPreset]:
    """Load built-in presets from default_tools.json."""
    presets = _load_json_presets(_DEFAULT_TOOLS_PATH)
    if not presets:
        log.warning("No built-in tool presets loaded from %s", _DEFAULT_TOOLS_PATH)
    return presets


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

TOOL_PRESETS: dict[str, ToolPreset] = _load_default_presets()

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


def load_user_tools(workdir: Path | str = ".") -> int:
    """Load user tool overrides from ``pyqual.tools.json`` in *workdir*.

    Merges into ``TOOL_PRESETS``, overriding built-in presets with the same name.
    Returns the number of presets loaded/overridden.
    """
    user_file = Path(workdir) / USER_TOOLS_FILE
    if not user_file.exists():
        return 0
    user_presets = _load_json_presets(user_file)
    count = 0
    for name, preset in user_presets.items():
        was_override = name in TOOL_PRESETS
        TOOL_PRESETS[name] = preset
        action = "override" if was_override else "add"
        log.info("user tools: %s preset '%s' (binary=%s)", action, name, preset.binary)
        count += 1
    if count:
        log.info("Loaded %d tool preset(s) from %s", count, user_file)
    return count


def preset_to_dict(preset: ToolPreset) -> dict[str, Any]:
    """Serialize a ToolPreset to a JSON-compatible dict."""
    d: dict[str, Any] = {
        "binary": preset.binary,
        "command": preset.command,
        "output": preset.output,
    }
    if not preset.allow_failure:
        d["allow_failure"] = False
    return d


def dump_presets_json(names: list[str] | None = None) -> str:
    """Serialize current presets (or a subset) to JSON string.

    Useful for ``pyqual tools --json`` or generating a starter
    ``pyqual.tools.json`` file.
    """
    presets = TOOL_PRESETS if names is None else {
        k: v for k, v in TOOL_PRESETS.items() if k in names
    }
    return json.dumps(
        {k: preset_to_dict(v) for k, v in sorted(presets.items())},
        indent=2,
        ensure_ascii=False,
    )


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
