"""Public Python API for pyqual — reusable interface for external tools.

This module provides a clean, high-level API for running quality pipelines
programmatically from other Python applications like prollama.

Example usage:
    >>> from pyqual import api
    >>> result = api.run_pipeline("pyqual.yaml", workdir=".")
    >>> print(result.final_passed)

Or with configuration object:
    >>> from pyqual import PyqualConfig, api
    >>> config = api.load_config("pyqual.yaml")
    >>> result = api.run(config, workdir=".")
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Callable

from pyqual.config import PyqualConfig
from pyqual.gates import GateSet, GateResult
from pyqual.pipeline import Pipeline, PipelineResult, StageResult, IterationResult
from pyqual.tools import get_preset, list_presets, ToolPreset

log = logging.getLogger("pyqual.api")

__all__ = [
    "load_config",
    "validate_config",
    "create_default_config",
    "run_pipeline",
    "run",
    "check_gates",
    "dry_run",
    "run_stage",
    "get_tool_command",
    "format_result_summary",
    "export_results_json",
    "shell",
    "shell_check",
]


def load_config(path: str | Path = "pyqual.yaml", workdir: str | Path = ".") -> PyqualConfig:
    """Load pyqual configuration from YAML file.
    
    Args:
        path: Path to pyqual.yaml (relative to workdir)
        workdir: Working directory for resolving relative paths
        
    Returns:
        Parsed and validated PyqualConfig object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    workdir_path = Path(workdir).resolve()
    config_path = workdir_path / path if not Path(path).is_absolute() else Path(path)
    return PyqualConfig.load(str(config_path))


def validate_config(config: PyqualConfig) -> list[str]:
    """Validate configuration and return list of errors (empty if valid)."""
    from pyqual.validation import validate_config as _validate
    errors = _validate(config)
    return [str(e) for e in errors]


def create_default_config(
    path: str | Path = "pyqual.yaml",
    profile: str | None = None,
    workdir: str | Path = "."
) -> Path:
    """Create a default pyqual.yaml config file.
    
    Args:
        path: Where to create the config file
        profile: Optional profile name (python, python-full, ci, lint-only, security)
        workdir: Working directory
        
    Returns:
        Path to created config file
    """
    from pyqual.profiles import get_profile
    
    target = Path(workdir) / path
    if target.exists():
        raise FileExistsError(f"Config already exists: {target}")
    
    if profile:
        content = get_profile(profile)
    else:
        content = """pipeline:
  name: quality-pipeline
  metrics:
    cc_max: 15
    critical_max: 10
  stages:
    - name: test
      tool: pytest
      optional: true
"""
    
    target.write_text(content)
    log.info("Created default config at %s", target)
    return target


def run(
    config: PyqualConfig,
    workdir: str | Path = ".",
    dry_run: bool = False,
    on_stage_start: Callable[[str], None] | None = None,
    on_stage_done: Callable[[StageResult], None] | None = None,
    on_iteration_start: Callable[[int], None] | None = None,
    on_iteration_done: Callable[[IterationResult], None] | None = None,
    stream_output: bool = False,
) -> PipelineResult:
    """Run a quality pipeline with the given configuration.
    
    Args:
        config: Pipeline configuration object
        workdir: Working directory for the pipeline
        dry_run: If True, don't actually execute commands
        on_stage_start: Callback when stage starts
        on_stage_done: Callback when stage completes
        on_iteration_start: Callback when iteration starts  
        on_iteration_done: Callback when iteration completes
        stream_output: If True, stream output in real-time
        
    Returns:
        PipelineResult with all iteration results
    """
    pipeline = Pipeline(
        config=config,
        workdir=workdir,
        on_stage_start=on_stage_start,
        on_stage_done=on_stage_done,
        on_iteration_start=on_iteration_start,
        on_iteration_done=on_iteration_done,
        stream=stream_output,
    )
    return pipeline.run(dry_run=dry_run)


def run_pipeline(
    config_path: str | Path = "pyqual.yaml",
    workdir: str | Path = ".",
    dry_run: bool = False,
    **kwargs: Any,
) -> PipelineResult:
    """Run pipeline from config file path (convenience function).
    
    Args:
        config_path: Path to pyqual.yaml
        workdir: Working directory
        dry_run: If True, don't actually execute
        **kwargs: Additional arguments passed to run()
        
    Returns:
        PipelineResult
        
    Example:
        >>> result = api.run_pipeline("pyqual.yaml", workdir="/path/to/project")
        >>> if result.final_passed:
        ...     print("Quality gates passed!")
    """
    config = load_config(config_path, workdir)
    return run(config, workdir, dry_run, **kwargs)


def check_gates(config: PyqualConfig, workdir: str | Path = ".") -> list[GateResult]:
    """Check quality gates without running pipeline.
    
    Args:
        config: Pipeline configuration
        workdir: Working directory
        
    Returns:
        List of gate results
    """
    gate_set = GateSet(config.gates)
    return gate_set.check_all(Path(workdir))


def dry_run(config_path: str | Path = "pyqual.yaml", workdir: str | Path = ".") -> PipelineResult:
    """Simulate pipeline execution without running commands.
    
    Args:
        config_path: Path to pyqual.yaml
        workdir: Working directory
        
    Returns:
        PipelineResult showing what would be executed
    """
    return run_pipeline(config_path, workdir, dry_run=True)


def run_stage(
    stage_name: str,
    command: str | None = None,
    tool: str | None = None,
    workdir: str | Path = ".",
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a single stage/command directly.
    
    Args:
        stage_name: Name of the stage (for logging)
        command: Shell command to run (either command or tool required)
        tool: Tool preset name to run (e.g. "pytest", "ruff")
        workdir: Working directory
        timeout: Timeout in seconds (0 = no timeout)
        env: Additional environment variables
        
    Returns:
        Dict with returncode, stdout, stderr, duration, passed
        
    Raises:
        ValueError: If neither command nor tool is provided
        
    Example:
        >>> result = api.run_stage("test", tool="pytest", workdir=".")
        >>> if result["passed"]:
        ...     print("Tests passed")
    """
    import time
    from pyqual.constants import TIMEOUT_EXIT_CODE
    
    workdir_path = Path(workdir).resolve()
    
    if tool:
        preset = get_preset(tool)
        if not preset:
            raise ValueError(f"Unknown tool preset: {tool}")
        command = preset.shell_command(str(workdir_path))
    elif not command:
        raise ValueError("Either command or tool must be provided")
    
    log.info("Running stage '%s': %s", stage_name, command)
    
    env_vars = {**dict(subprocess.os.environ), **(env or {})}
    
    start = time.monotonic()
    try:
        effective_timeout = timeout if timeout > 0 else None
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workdir_path,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            env=env_vars,
            stdin=subprocess.DEVNULL,
        )
        duration = time.monotonic() - start
        return {
            "name": stage_name,
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "duration": round(duration, 3),
            "passed": proc.returncode == 0,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return {
            "name": stage_name,
            "returncode": TIMEOUT_EXIT_CODE,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "duration": round(duration, 3),
            "passed": False,
            "command": command,
        }
    except Exception as e:
        duration = time.monotonic() - start
        return {
            "name": stage_name,
            "returncode": 1,
            "stdout": "",
            "stderr": str(e),
            "duration": round(duration, 3),
            "passed": False,
            "command": command,
        }


def get_tool_command(tool_name: str, workdir: str | Path = ".") -> str:
    """Get the shell command for a built-in tool preset.
    
    Args:
        tool_name: Tool preset name (e.g. "pytest", "ruff", "mypy")
        workdir: Working directory
        
    Returns:
        Shell command string
        
    Raises:
        ValueError: If tool preset not found
        
    Example:
        >>> cmd = api.get_tool_command("pytest")
        >>> print(cmd)  # "pytest --cov-report=json:.pyqual/coverage.json -q"
    """
    preset = get_preset(tool_name)
    if not preset:
        raise ValueError(f"Unknown tool preset: {tool_name}")
    return preset.shell_command(str(workdir))


def format_result_summary(result: PipelineResult) -> str:
    """Format pipeline result as human-readable summary.
    
    Args:
        result: Pipeline result object
        
    Returns:
        Formatted summary string
    """
    lines = [
        f"Pipeline Result: {'PASS' if result.final_passed else 'FAIL'}",
        f"Iterations: {result.iteration_count}",
        f"Total Duration: {result.total_duration:.1f}s",
        "",
    ]
    
    for i, iteration in enumerate(result.iterations, 1):
        lines.append(f"Iteration {i}:")
        for stage in iteration.stages:
            status = "✓" if stage.passed else "✗"
            skip_mark = " (skipped)" if stage.skipped else ""
            lines.append(f"  {status} {stage.name}: {stage.duration:.1f}s{skip_mark}")
        
        if iteration.gates:
            lines.append(f"  Gates:")
            for gate in iteration.gates:
                status = "✓" if gate.passed else "✗"
                lines.append(f"    {status} {gate.metric}: {gate.value} {gate.operator} {gate.threshold}")
        lines.append("")
    
    return "\n".join(lines)


def export_results_json(
    result: PipelineResult,
    output_path: str | Path = ".pyqual/results.json"
) -> Path:
    """Export pipeline results to JSON file.
    
    Args:
        result: Pipeline result object
        output_path: Where to write the JSON file
        
    Returns:
        Path to written file
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "final_passed": result.final_passed,
        "iteration_count": result.iteration_count,
        "total_duration": result.total_duration,
        "iterations": [
            {
                "iteration": it.iteration,
                "all_gates_passed": it.all_gates_passed,
                "duration": it.duration,
                "stages": [
                    {
                        "name": s.name,
                        "passed": s.passed,
                        "skipped": s.skipped,
                        "returncode": s.returncode,
                        "duration": s.duration,
                        "command": s.command,
                        "tool": s.tool,
                    }
                    for s in it.stages
                ],
                "gates": [
                    {
                        "metric": g.metric,
                        "value": g.value,
                        "threshold": g.threshold,
                        "operator": g.operator,
                        "passed": g.passed,
                    }
                    for g in it.gates
                ],
            }
            for it in result.iterations
        ],
    }
    
    path.write_text(json.dumps(data, indent=2, default=str))
    log.info("Exported results to %s", path)
    return path


class ShellHelper:
    """Shell helper utilities for external tool integration."""
    
    @staticmethod
    def run(
        command: str,
        cwd: str | Path | None = None,
        capture: bool = True,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling.
        
        Args:
            command: Shell command to run
            cwd: Working directory
            capture: If True, capture stdout/stderr
            timeout: Timeout in seconds
            env: Additional environment variables
            check: If True, raise CalledProcessError on non-zero exit
            
        Returns:
            CompletedProcess instance
        """
        env_vars = {**dict(subprocess.os.environ), **(env or {})}
        
        return subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            env=env_vars,
            check=check,
            stdin=subprocess.DEVNULL,
        )
    
    @staticmethod
    def check(
        command: str,
        cwd: str | Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Check if a command succeeds (returns True) or fails (returns False).
        
        Args:
            command: Shell command to run
            cwd: Working directory
            timeout: Timeout in seconds
            env: Additional environment variables
            
        Returns:
            True if command exits with code 0, False otherwise
        """
        try:
            result = ShellHelper.run(command, cwd, True, timeout, env, check=False)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def output(
        command: str,
        cwd: str | Path | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        """Run command and return stdout as string.
        
        Args:
            command: Shell command to run
            cwd: Working directory
            timeout: Timeout in seconds
            env: Additional environment variables
            
        Returns:
            stdout string (empty if command fails)
        """
        try:
            result = ShellHelper.run(command, cwd, True, timeout, env, check=False)
            return result.stdout or ""
        except Exception:
            return ""


# Convenience alias for shell helpers
shell = ShellHelper()


def shell_check(command: str, **kwargs: Any) -> bool:
    """Check if a shell command succeeds.
    
    Convenience function for quick command checks.
    
    Args:
        command: Shell command to run
        **kwargs: Additional arguments passed to ShellHelper.check()
        
    Returns:
        True if command succeeds
        
    Example:
        >>> if api.shell_check("which python"):
        ...     print("Python is available")
    """
    return ShellHelper.check(command, **kwargs)
