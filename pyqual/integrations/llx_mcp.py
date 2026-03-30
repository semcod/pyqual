"""Client helpers for using the llx MCP service from pyqual."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from llx.mcp.client import LlxMcpClient  # canonical upstream
from llx.utils.issues import (  # canonical upstream
    build_fix_prompt,
    load_issue_source as _load_issue_source,
    load_todo_markdown as _load_todo_markdown,
    task_prompt_label as _task_prompt_label,
)

DEFAULT_ENDPOINT = "http://localhost:8000/sse"
DEFAULT_ISSUES_PATH = ".pyqual/errors.json"
DEFAULT_OUTPUT_PATH = ".pyqual/llx_mcp.json"
DEFAULT_PROMPT_LIMIT = 10


@dataclass
class LlxMcpRunResult:
    """Result of an llx MCP fix/refactor workflow."""

    success: bool
    endpoint: str
    project_path: str
    issues_path: str
    prompt: str
    tool_calls: int
    analysis: dict[str, Any] | None = None
    aider: dict[str, Any] | None = None
    issues: dict[str, Any] | list[dict[str, Any]] | None = None
    model: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for JSON output."""
        return asdict(self)


# _load_issue_source, _load_todo_markdown, _task_prompt_label, and
# build_fix_prompt are now imported from llx.utils.issues above.


def _resolve_issue_source(
    workdir: Path,
    issues_path: Path,
) -> tuple[Path, dict[str, Any] | list[dict[str, Any]] | list[Any]]:
    """Resolve issues, falling back from the default JSON file to TODO.md when empty."""
    resolved = issues_path if issues_path.is_absolute() else (workdir / issues_path).resolve()
    issues = _load_issue_source(resolved)

    if resolved.name == Path(DEFAULT_ISSUES_PATH).name and not issues:
        todo_path = (workdir / "TODO.md").resolve()
        if todo_path.exists():
            todo_issues = _load_todo_markdown(todo_path)
            if todo_issues:
                return todo_path, todo_issues

    return resolved, issues


async def run_llx_fix_workflow(
    workdir: Path,
    project_path: str,
    issues_path: Path,
    output_path: Path,
    endpoint_url: str | None = None,
    model: str | None = None,
    files: list[str] | None = None,
    use_docker: bool = False,
    docker_args: list[str] | None = None,
    task: str = "quick_fix",
) -> LlxMcpRunResult:
    """Run the analysis + fix/refactor workflow and save a JSON report."""
    client = LlxMcpClient(endpoint_url=endpoint_url)
    resolved_issues_path, issues = _resolve_issue_source(workdir, issues_path)

    try:
        analysis_response = await client.analyze(project_path, task=task)
        analysis_data = analysis_response.get("data")
        if not isinstance(analysis_data, dict):
            analysis_data = {"raw": analysis_response.get("text", "")}

        prompt = build_fix_prompt(
            Path(project_path),
            issues,
            analysis_data,
            action_label=_task_prompt_label(task),
        )
        selected_model = model
        if not selected_model:
            selection = analysis_data.get("selection") if isinstance(analysis_data, dict) else None
            if isinstance(selection, dict):
                selected_model = selection.get("model_id")

        aider_response = await client.fix_with_aider(
            project_path=project_path,
            prompt=prompt,
            model=selected_model,
            files=files or [],
            use_docker=use_docker,
            docker_args=docker_args,
        )
        aider_data = aider_response.get("data")
        if not isinstance(aider_data, dict):
            aider_data = {"raw": aider_response.get("text", "")}

        success = bool(aider_data.get("success"))
        result = LlxMcpRunResult(
            success=success,
            endpoint=client.endpoint_url,
            project_path=project_path,
            issues_path=str(resolved_issues_path),
            prompt=prompt,
            tool_calls=2,
            analysis=analysis_data,
            aider=aider_data,
            issues=issues,
            model=selected_model,
        )
    except Exception as exc:  # pragma: no cover - surfaced to CLI and pipeline
        result = LlxMcpRunResult(
            success=False,
            endpoint=client.endpoint_url,
            project_path=project_path,
            issues_path=str(resolved_issues_path),
            prompt="",
            tool_calls=0,
            issues=issues,
            error=str(exc),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return result


async def run_llx_refactor_workflow(
    workdir: Path,
    project_path: str,
    issues_path: Path,
    output_path: Path,
    endpoint_url: str | None = None,
    model: str | None = None,
    files: list[str] | None = None,
    use_docker: bool = False,
    docker_args: list[str] | None = None,
) -> LlxMcpRunResult:
    """Run the llx refactor workflow and save a JSON report."""
    return await run_llx_fix_workflow(
        workdir=workdir,
        project_path=project_path,
        issues_path=issues_path,
        output_path=output_path,
        endpoint_url=endpoint_url,
        model=model,
        files=files,
        use_docker=use_docker,
        docker_args=docker_args,
        task="refactor",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the llx MCP helper."""
    parser = argparse.ArgumentParser(description="Run the llx-backed MCP fix/refactor workflow.")
    parser.add_argument("--workdir", default=os.getenv("PYQUAL_LLX_PROJECT_ROOT", "."), help="Project working directory.")
    parser.add_argument("--project-path", default=os.getenv("PYQUAL_LLX_PROJECT_PATH"), help="Project path as seen by the MCP service container.")
    parser.add_argument("--issues", default=DEFAULT_ISSUES_PATH, help="Path to gate failure JSON.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Where to write the MCP run report.")
    parser.add_argument("--endpoint", default=os.getenv("PYQUAL_LLX_MCP_URL", DEFAULT_ENDPOINT), help="MCP SSE endpoint.")
    parser.add_argument("--model", default=None, help="Override the model selected by llx.")
    parser.add_argument("--file", dest="files", action="append", default=[], help="Specific file to focus on (repeatable).")
    parser.add_argument("--use-docker", action="store_true", default=os.getenv("PYQUAL_LLX_USE_DOCKER", "false").lower() in {"1", "true", "yes"}, help="Let llx's aider tool run inside Docker.")
    parser.add_argument("--docker-arg", dest="docker_args", action="append", default=[], help="Extra Docker arguments forwarded to llx's aider tool.")
    parser.add_argument("--task", default="quick_fix", choices=["refactor", "explain", "quick_fix", "review"], help="Analysis task hint.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point used by pyqual pipeline stages."""
    parser = build_parser()
    args = parser.parse_args(argv)

    workdir = Path(args.workdir).resolve()
    project_path = args.project_path or str(workdir)
    issues_path = Path(args.issues)
    if not issues_path.is_absolute():
        issues_path = (workdir / issues_path).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (workdir / output_path).resolve()

    result = asyncio.run(
        run_llx_fix_workflow(
            workdir=workdir,
            project_path=project_path,
            issues_path=issues_path,
            output_path=output_path,
            endpoint_url=args.endpoint,
            model=args.model,
            files=args.files,
            use_docker=bool(args.use_docker),
            docker_args=args.docker_args,
            task=args.task,
        )
    )

    if result.error:
        print(result.error)
        return 1

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
