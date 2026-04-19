"""Run command — main pipeline execution.

This is the core pyqual command that executes the pipeline loop until
quality gates pass.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
import yaml as _yaml

from pyqual.cli.main import app, console, stderr_console, setup_logging
from pyqual.cli_run_helpers import (
    build_run_summary as _build_run_summary,
    enrich_from_artifacts as _enrich_from_artifacts,
    extract_stage_summary as _extract_stage_summary,
    format_run_summary as _format_run_summary,
    get_last_error_line as _get_last_error_line,
)
from pyqual.config import PyqualConfig
from pyqual.constants import LLM_FIX_MAX_TOKENS
from pyqual.gates import GateSet
from pyqual.pipeline import Pipeline
from pyqual.tickets import sync_all_tickets
from pyqual.validation import EC, ErrorDomain, Severity, detect_project_facts, validate_config

try:
    from pyqual.integrations.llx_mcp import run_llx_fix_workflow
except Exception:  # pragma: no cover - llx MCP modules are optional
    run_llx_fix_workflow = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    pass


def _emit(text: str) -> None:
    """Emit text to stdout."""
    sys.stdout.write(text)
    sys.stdout.flush()


def _emit_yaml_items(items: list[dict], indent: int = 0) -> None:
    """Emit list of dicts as YAML to stdout."""
    fragment = _yaml.safe_dump(items, default_flow_style=False,
                                sort_keys=False, allow_unicode=True)
    prefix = " " * indent
    for line in fragment.rstrip().splitlines():
        _emit(f"{prefix}{line}\n")


def _build_stage_dict(result: Any, workdir: Path) -> dict[str, Any]:
    """Build a stage dict from a stage result."""
    sd: dict[str, Any] = {"name": result.name}
    if result.skipped:
        sd["status"] = "skipped"
    else:
        sd["status"] = "passed" if result.passed else "failed"
        sd["duration"] = round(result.duration, 1)
        metrics = _extract_stage_summary(result.name, result.stdout, result.stderr)
        sd.update(metrics)
        if not result.passed:
            sd["rc"] = result.returncode
            err = _get_last_error_line(result.stderr or result.stdout or "")
            if err:
                sd["stderr"] = err
    _enrich_from_artifacts(workdir, [sd])
    return sd


def _build_gate_dict(gate: Any, op_sym: dict[str, str]) -> dict[str, Any]:
    """Build a gate dict from a gate result."""
    return {
        "metric": gate.metric,
        "value": round(gate.value, 1) if gate.value is not None else None,
        "threshold": gate.threshold,
        "operator": op_sym.get(gate.operator, gate.operator),
        "passed": gate.passed,
    }


def _handle_config_env_error(
    failure: Any,
    config_path: Path,
    console: Any,
    auto_fix: bool,
) -> None:
    """Handle CONFIG or ENV domain errors with diagnostics and optional auto-fix."""
    code = failure.error_code
    console.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                  f"  rc={failure.returncode}")
    console.print("  [yellow]→ Detected CONFIG/ENV problem — running pre-flight diagnostics…[/yellow]")
    diag = validate_config(config_path)
    if diag.issues:
        for issue in diag.issues:
            badge = "[red]ERR [/]" if issue.severity.value == "error" else "[yellow]WARN[/]"
            console.print(f"    {badge}  {issue.code}  {issue.message}")
            if issue.suggestion:
                console.print(f"         [dim]→ {issue.suggestion}[/dim]")
        if auto_fix and diag.errors:
            console.print("\n  [yellow]--auto-fix-config: attempting LLM repair of pyqual.yaml…[/yellow]")
            _run_auto_fix_config(config_path, console, diag)
    else:
        console.print("  [dim]Pre-flight: config looks valid — problem is runtime environment.[/dim]")
        if failure.stderr:
            console.print(f"  [dim]stderr: {failure.stderr[:200]}[/dim]")
    console.print()


def _handle_llm_error(failure: Any, console: Any) -> None:
    """Handle LLM domain errors."""
    code = failure.error_code
    console.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                  f"  rc={failure.returncode}")
    console.print("  [yellow]→ LLM/fix-stage problem.[/yellow]")
    if code == EC.LLM_API_KEY_MISSING:
        console.print("  [red]API key missing.[/red] Set OPENROUTER_API_KEY in .env or environment.")
    elif code == EC.LLM_NETWORK_ERROR:
        console.print("  [red]Network error.[/red] Check connectivity to the LLM endpoint.")
    elif code == EC.LLM_FIX_FAILED:
        console.print("  [dim]Fix stage failed — project code may be too complex for one pass.[/dim]")
    if failure.stderr:
        console.print(f"  [dim]{failure.stderr[:200]}[/dim]")
    console.print()


def _handle_pipeline_error(failure: Any, console: Any) -> None:
    """Handle PIPELINE domain errors."""
    code = failure.error_code
    console.print(f"\n  [bold red]{code}[/bold red]  stage=[cyan]{failure.stage_name}[/cyan]"
                  f"  rc={failure.returncode}")
    if code == EC.PIPELINE_TIMEOUT:
        console.print(f"  [red]Stage timed out[/red] after {failure.duration:.0f}s."
                      " Increase 'timeout:' in the stage config.")
    else:
        console.print(f"  [red]Pipeline execution error.[/red]  {failure.stderr[:200]}")
    console.print()


def _run_auto_fix_config(cfg_path: Path, console: Any, diag: Any) -> None:
    """Auto-repair pyqual.yaml using LLM based on validation diagnostics."""
    from pyqual.llm import LLM
    from pyqual.validation import detect_project_facts
    workdir = cfg_path.parent
    facts = detect_project_facts(workdir)
    issues_text = "\n".join(
        f"  [{i.severity.value.upper()}] {i.code}: {i.message}"
        + (f" → {i.suggestion}" if i.suggestion else "")
        for i in diag.issues
    )
    prompt = (
        f"Fix this pyqual.yaml to resolve all validation errors.\n\n"
        f"Available tools on PATH: {', '.join(facts.get('available_tools', []))}\n"
        f"Language: {facts.get('lang', 'unknown')}\n\n"
        f"Current config:\n{facts.get('current_config', '')}\n\n"
        f"Issues:\n{issues_text}\n\n"
        "Output ONLY corrected YAML, no fences, no explanation."
    )
    try:
        llm = LLM()
        resp = llm.complete(prompt, temperature=0.1, max_tokens=LLM_FIX_MAX_TOKENS)
        new_yaml = resp.content.strip()
        if new_yaml.startswith("```"):
            new_yaml = "\n".join(line for line in new_yaml.splitlines()
                                 if not line.startswith("```")).strip()
        backup = cfg_path.with_suffix(".yaml.bak")
        cfg_path.rename(backup)
        cfg_path.write_text(new_yaml)
        console.print(f"  [green]pyqual.yaml rewritten[/green] (backup: {backup.name})")
        console.print("  [dim]Re-run 'pyqual run' to continue with the fixed config.[/dim]")
    except Exception as exc:
        console.print(f"  [red]Auto-fix failed: {exc}[/red]")


def _on_stage_error_impl(
    failure: Any,
    config_path: Path,
    console: Any,
    auto_fix_config: bool,
) -> None:
    """Implementation of stage error handling - dispatches by error domain."""
    domain = failure.domain

    if domain == ErrorDomain.CONFIG or domain == ErrorDomain.ENV:
        _handle_config_env_error(failure, config_path, console, auto_fix_config)
    elif domain == ErrorDomain.LLM:
        _handle_llm_error(failure, console)
    elif domain == ErrorDomain.PIPELINE:
        _handle_pipeline_error(failure, console)
    elif domain == ErrorDomain.PROJECT:
        pass  # expected — fix stage handles project issues; visible in YAML as status: failed


def _create_tickets_if_needed(
    result_final_passed: bool,
    cfg: PyqualConfig,
    workdir: Path,
    console: Any,
) -> None:
    """Create planfile tickets if gates failed and on_fail is set to create_ticket."""
    if result_final_passed:
        return
    if cfg.loop.on_fail != "create_ticket":
        return

    backends = cfg.loop.ticket_backends or ["markdown"]
    console.print(f"[yellow]Creating planfile tickets (backends: {', '.join(backends)})...[/yellow]")
    try:
        if "all" in backends:
            sync_all_tickets(workdir=workdir, dry_run=False, direction="from")
        else:
            from pyqual.tickets import sync_planfile_tickets
            for backend in backends:
                sync_planfile_tickets(backend, workdir=workdir, dry_run=False, direction="from")
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


def _rebuild_iterations_from_result(
    result: Any,
    all_iterations: list[dict[str, Any]],
    workdir: Any,
    op_sym: dict[str, str],
) -> None:
    """Emit YAML for each iteration and populate all_iterations when callbacks were not fired."""
    for iteration in result.iterations:
        iter_stages = [_build_stage_dict(stage, workdir) for stage in iteration.stages]
        for sd in iter_stages:
            _emit_yaml_items([sd], indent=2)
        gate_dicts = [_build_gate_dict(g, op_sym) for g in iteration.gates]
        if gate_dicts:
            _emit("  gates:\n")
            _emit_yaml_items(gate_dicts, indent=2)
        _emit(f"  all_gates_passed: {'true' if iteration.all_gates_passed else 'false'}\n")
        all_iterations.append({
            "iteration": iteration.iteration,
            "stages": iter_stages,
            "gates": gate_dicts,
            "all_gates_passed": iteration.all_gates_passed,
        })


@app.command()
def run(
    config: Path = typer.Option("pyqual.yaml", "--config", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    workdir: Path = typer.Option(Path("."), "--workdir", "-w"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show live pipeline log output."),
    stream: bool = typer.Option(False, "--stream", "-s",
                                help="Stream stage stdout/stderr in real-time (shows llx prompts, vallm output, etc)."),
    auto_fix_config: bool = typer.Option(False, "--auto-fix-config",
                                         help="Auto-repair pyqual.yaml when ENV/CONFIG errors are detected."),
) -> None:
    """Execute pipeline loop until quality gates pass.

    Output is streamed as YAML to stdout as each stage completes.
    Diagnostic messages go to stderr.
    """
    setup_logging(verbose, workdir)
    cfg = PyqualConfig.load(config)

    _workdir = Path(workdir).resolve()
    _config_path = (_workdir / config) if not Path(config).is_absolute() else Path(config)

    _sc = stderr_console
    import pyqual as _pq
    _ver = getattr(_pq, "__version__", "?")
    op_sym = {"le": "<=", "ge": ">=", "lt": "<", "gt": ">", "eq": "=="}

    # ── Streaming state ──
    _iter_stages: list[dict[str, Any]] = []
    _all_iterations: list[dict[str, Any]] = []

    # ── Emit YAML preamble ──
    _emit(f"pyqual: {_ver}\n")
    _emit(f"config: {config}\n")
    _emit(f"workdir: {_workdir}\n")
    _emit("iterations:\n")

    def _on_iter_start(num: int) -> None:
        _iter_stages.clear()
        _emit(f"- iteration: {num}\n")
        _emit("  stages:\n")

    def _on_stage_start(name: str) -> None:
        pass  # YAML streaming is the progress indicator; use `pyqual watch` for live logs

    def _on_stage_done(result: Any) -> None:
        sd = _build_stage_dict(result, _workdir)
        _iter_stages.append(sd)
        _emit_yaml_items([sd], indent=2)

    def _on_iteration_done(iteration: Any) -> None:
        gate_dicts = [_build_gate_dict(g, op_sym) for g in iteration.gates]
        _emit("  gates:\n")
        _emit_yaml_items(gate_dicts, indent=2)
        _emit(f"  all_gates_passed: {'true' if iteration.all_gates_passed else 'false'}\n")
        _all_iterations.append({
            "iteration": iteration.iteration,
            "stages": list(_iter_stages),
            "gates": gate_dicts,
            "all_gates_passed": iteration.all_gates_passed,
        })

    def _on_stage_error(failure: Any) -> None:
        _on_stage_error_impl(failure, _config_path, _sc, auto_fix_config)

    def _on_stage_output(name: str, line: str, is_stderr: bool) -> None:
        tag = "err" if is_stderr else "out"
        _sc.print(f"  [dim][{name}:{tag}][/dim] {line}")

    pipeline = Pipeline(cfg, workdir,
                        on_stage_start=_on_stage_start,
                        on_iteration_start=_on_iter_start,
                        on_stage_error=_on_stage_error,
                        on_stage_done=_on_stage_done,
                        on_stage_output=_on_stage_output if (stream or verbose) else None,
                        stream=stream or verbose,
                        on_iteration_done=_on_iteration_done)
    result = pipeline.run(dry_run=dry_run)

    # ── Emit final YAML fields ──
    # If callbacks weren't fired (e.g. no iterations), rebuild from result
    if not _all_iterations and result.iterations:
        _rebuild_iterations_from_result(result, _all_iterations, _workdir, op_sym)

    _emit(f"result: {'all_gates_passed' if result.final_passed else 'gates_not_met'}\n")
    _emit(f"total_time: {round(result.total_duration, 1)}\n")

    report = {"iterations": _all_iterations}
    summary = _build_run_summary(report)
    if summary:
        _emit(_yaml.safe_dump({"summary": summary}, default_flow_style=False,
                               sort_keys=False, allow_unicode=True))

    summary_text = _format_run_summary(summary)
    if summary_text:
        _sc.print(f"\n{summary_text}")

    _create_tickets_if_needed(result.final_passed, cfg, _workdir, _sc)

    if not result.final_passed:
        raise typer.Exit(1)
