"""MCP workflow commands: mcp-fix, mcp-refactor, mcp-service.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer
from rich.table import Table

from pyqual.cli.main import app, console
from pyqual.constants import DEFAULT_MCP_PORT

try:
    from pyqual.integrations.llx_mcp import run_llx_fix_workflow
    from pyqual.integrations.llx_mcp import run_llx_refactor_workflow
except Exception:  # pragma: no cover - llx MCP modules are optional
    run_llx_fix_workflow = None  # type: ignore[assignment]
    run_llx_refactor_workflow = None  # type: ignore[assignment]

try:
    from pyqual.integrations.llx_mcp_service import run_server as run_llx_mcp_service
except Exception:  # pragma: no cover
    run_llx_mcp_service = None  # type: ignore[assignment]

if TYPE_CHECKING:
    pass


def _run_mcp_workflow(
    *,
    title: str,
    runner: Any,
    workdir: Path,
    project_path: str | None,
    issues: Path,
    output: Path,
    endpoint: str | None,
    model: str | None,
    file: list[str],
    use_docker: bool,
    docker_arg: list[str],
    json_output: bool,
    task: str | None = None,
) -> None:
    resolved_project_path = project_path or str(workdir)
    resolved_issues = issues if issues.is_absolute() else (workdir / issues).resolve()
    resolved_output = output if output.is_absolute() else (workdir / output).resolve()

    try:
        workflow_kwargs: dict[str, Any] = {
            "workdir": workdir,
            "project_path": resolved_project_path,
            "issues_path": resolved_issues,
            "output_path": resolved_output,
            "endpoint_url": endpoint,
            "model": model,
            "files": file,
            "use_docker": use_docker,
            "docker_args": docker_arg,
        }
        if task is not None:
            workflow_kwargs["task"] = task

        result = asyncio.run(runner(**workflow_kwargs))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        table = Table(title=title)
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("success", "yes" if result.success else "no")
        table.add_row("endpoint", result.endpoint)
        table.add_row("project path", result.project_path)
        table.add_row("report", str(resolved_output))
        table.add_row("tool calls", str(result.tool_calls))
        table.add_row("model", result.model or "auto")
        if result.error:
            table.add_row("error", result.error)
        console.print(table)

    if result.error:
        raise typer.Exit(1)
    if not result.success:
        raise typer.Exit(1)


@app.command("mcp-fix")
def mcp_fix(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Project directory on the host."),
    project_path: str | None = typer.Option(None, "--project-path", help="Project path as seen by the MCP service container."),
    issues: Path = typer.Option(Path(".pyqual/errors.json"), "--issues", help="Gate-failure JSON file to summarize."),
    output: Path = typer.Option(Path(".pyqual/llx_mcp.json"), "--output", help="Where to write the MCP run report."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="MCP SSE endpoint URL."),
    model: str | None = typer.Option(None, "--model", help="Override the model selected by llx."),
    file: list[str] = typer.Option([], "--file", help="Specific file to focus on (repeatable)."),
    use_docker: bool = typer.Option(False, "--use-docker", help="Let llx's aider tool run inside Docker."),
    docker_arg: list[str] = typer.Option([], "--docker-arg", help="Extra Docker arguments forwarded to llx's aider tool."),
    task: str = typer.Option("quick_fix", "--task", help="Analysis task hint for llx."),
    json_output: bool = typer.Option(False, "--json", help="Print the full JSON result."),
) -> None:
    """Run the llx-backed MCP fix workflow."""
    if run_llx_fix_workflow is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    _run_mcp_workflow(
        title="llx MCP fix",
        runner=run_llx_fix_workflow,
        workdir=workdir,
        project_path=project_path,
        issues=issues,
        output=output,
        endpoint=endpoint,
        model=model,
        file=file,
        use_docker=use_docker,
        docker_arg=docker_arg,
        json_output=json_output,
        task=task,
    )


@app.command("mcp-refactor")
def mcp_refactor(
    workdir: Path = typer.Option(Path("."), "--workdir", "-w", help="Project directory on the host."),
    project_path: str | None = typer.Option(None, "--project-path", help="Project path as seen by the MCP service container."),
    issues: Path = typer.Option(Path(".pyqual/errors.json"), "--issues", help="Gate-failure JSON file to summarize."),
    output: Path = typer.Option(Path(".pyqual/llx_mcp.json"), "--output", help="Where to write the MCP run report."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="MCP SSE endpoint URL."),
    model: str | None = typer.Option(None, "--model", help="Override the model selected by llx."),
    file: list[str] = typer.Option([], "--file", help="Specific file to focus on (repeatable)."),
    use_docker: bool = typer.Option(False, "--use-docker", help="Let llx's aider tool run inside Docker."),
    docker_arg: list[str] = typer.Option([], "--docker-arg", help="Extra Docker arguments forwarded to llx's aider tool."),
    json_output: bool = typer.Option(False, "--json", help="Print the full JSON result."),
) -> None:
    """Run the llx-backed MCP refactor workflow."""
    if run_llx_refactor_workflow is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    _run_mcp_workflow(
        title="llx MCP refactor",
        runner=run_llx_refactor_workflow,
        workdir=workdir,
        project_path=project_path,
        issues=issues,
        output=output,
        endpoint=endpoint,
        model=model,
        file=file,
        use_docker=use_docker,
        docker_arg=docker_arg,
        json_output=json_output,
    )


@app.command("mcp-service")
def mcp_service(
    host: str = typer.Option("0.0.0.0", "--host", help="Host interface to bind to."),
    port: int = typer.Option(DEFAULT_MCP_PORT, "--port", help="Port to listen on."),
) -> None:
    """Run the persistent llx MCP service with health and metrics endpoints."""
    if run_llx_mcp_service is None:
        console.print("[red]llx MCP modules not installed. Install: pip install pyqual[mcp][/red]")
        raise typer.Exit(1)
    try:
        run_llx_mcp_service(host=host, port=port)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
