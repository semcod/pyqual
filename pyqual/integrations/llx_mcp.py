"""Client helpers for using the llx MCP service from pyqual."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT = "http://localhost:8000/sse"
DEFAULT_ISSUES_PATH = ".pyqual/errors.json"
DEFAULT_OUTPUT_PATH = ".pyqual/llx_mcp.json"
DEFAULT_PROMPT_LIMIT = 10

_TODO_CHECKLIST_RE = re.compile(r"^- \[(?P<state>[ xX])\]\s+(?P<body>.+)$")
_TODO_DETAIL_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+)\s+-\s+(?P<message>.+)$")


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


class LlxMcpClient:
    """Thin MCP client for the llx SSE service."""

    def __init__(self, endpoint_url: str | None = None):
        self.endpoint_url = endpoint_url or os.getenv("PYQUAL_LLX_MCP_URL", DEFAULT_ENDPOINT)

    @asynccontextmanager
    async def _session(self):
        try:
            from mcp.client.session import ClientSession
            from mcp.client.sse import sse_client
        except ImportError as exc:  # pragma: no cover - dependency error
            raise RuntimeError(
                "mcp is required for pyqual's llx integration. Install with: pip install pyqual[mcp]"
            ) from exc

        async with sse_client(self.endpoint_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                yield session

    @staticmethod
    def _extract_text_payload(result: Any) -> tuple[str, Any]:
        """Return the concatenated text and parsed JSON payload if possible."""
        text_parts: list[str] = []
        content = getattr(result, "content", []) or []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                text_parts.append(text)

        combined = "\n".join(text_parts).strip()
        if not combined:
            return "", None

        try:
            return combined, json.loads(combined)
        except json.JSONDecodeError:
            return combined, combined

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a named MCP tool and return a JSON-friendly payload."""
        async with self._session() as session:
            result = await session.call_tool(name, arguments or {})

        text, parsed = self._extract_text_payload(result)
        is_error = bool(getattr(result, "isError", False))
        return {
            "tool": name,
            "arguments": arguments or {},
            "is_error": is_error,
            "text": text,
            "data": parsed,
            "raw": result.model_dump(mode="json", by_alias=True, exclude_none=True),
        }

    async def analyze(self, project_path: str, toon_dir: str | None = None, task: str = "quick_fix") -> dict[str, Any]:
        """Run llx analysis and return the parsed payload."""
        payload = {"path": project_path, "task": task}
        if toon_dir:
            payload["toon_dir"] = toon_dir
        return await self.call_tool("llx_analyze", payload)

    async def fix_with_aider(
        self,
        project_path: str,
        prompt: str,
        model: str | None = None,
        files: list[str] | None = None,
        use_docker: bool = False,
        docker_args: list[str] | None = None,
    ) -> dict[str, Any]:
        """Invoke the llx `aider` tool with a prepared prompt."""
        payload: dict[str, Any] = {
            "path": project_path,
            "prompt": prompt,
            "use_docker": use_docker,
        }
        if model:
            payload["model"] = model
        if files:
            payload["files"] = files
        if docker_args:
            payload["docker_args"] = docker_args
        return await self.call_tool("aider", payload)


def _load_issue_source(issues_path: Path) -> dict[str, Any] | list[dict[str, Any]] | list[Any]:
    """Load the issue source file if it exists."""
    if not issues_path.exists():
        return []

    if issues_path.suffix.lower() in {".md", ".markdown"} or issues_path.name.lower() == "todo.md":
        return _load_todo_markdown(issues_path)

    try:
        data = json.loads(issues_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("errors", "messages", "findings", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return data
    return []


def _load_todo_markdown(issues_path: Path) -> list[dict[str, Any]]:
    """Load unchecked TODO checklist items from prefact-generated markdown."""
    try:
        lines = issues_path.read_text().splitlines()
    except OSError:
        return []

    issues: list[dict[str, Any]] = []
    for raw_line in lines:
        match = _TODO_CHECKLIST_RE.match(raw_line.strip())
        if not match or match.group("state").lower() != " ":
            continue

        body = match.group("body").strip()
        detail = _TODO_DETAIL_RE.match(body)
        if detail:
            issues.append(
                {
                    "file": detail.group("file").strip(),
                    "line": int(detail.group("line")),
                    "message": detail.group("message").strip(),
                    "severity": "todo",
                }
            )
            continue

        issues.append({"message": body, "severity": "todo"})

    return issues


def _issue_text(issue: Any) -> str:
    """Render one issue entry as a compact string."""
    if isinstance(issue, str):
        return issue
    if isinstance(issue, dict):
        parts: list[str] = []
        location = issue.get("file") or issue.get("path")
        line = issue.get("line") or issue.get("lineno")
        if location:
            loc = str(location)
            if line:
                loc = f"{loc}:{line}"
            parts.append(loc)
        severity = issue.get("severity") or issue.get("level")
        if severity:
            parts.append(str(severity))
        code = issue.get("code") or issue.get("symbol")
        if code:
            parts.append(str(code))
        message = issue.get("message") or issue.get("msg") or issue.get("description")
        if message:
            parts.append(str(message))
        if parts:
            return " - ".join(parts)
    return str(issue)


def _task_prompt_label(task: str) -> str:
    """Map llx task hints to prompt wording."""
    labels = {
        "explain": "explaining code",
        "quick_fix": "fixing code",
        "refactor": "refactoring code",
        "review": "reviewing code",
    }
    return labels.get(task, "fixing code")


def build_fix_prompt(
    project_path: Path,
    issues: dict[str, Any] | list[dict[str, Any]] | list[Any],
    analysis: dict[str, Any] | None = None,
    prompt_limit: int = DEFAULT_PROMPT_LIMIT,
    action_label: str = "fixing code",
) -> str:
    """Build a concise prompt for llx/aider from gate failures."""
    selected_model = None
    tier = None
    if analysis:
        selection = analysis.get("selection")
        if isinstance(selection, dict):
            selected_model = selection.get("model_id")
            tier = selection.get("tier")

    issue_lines: list[str] = []
    if isinstance(issues, dict):
        issue_lines.append(_issue_text(issues))
    else:
        for issue in list(issues)[:prompt_limit]:
            issue_lines.append(_issue_text(issue))

    issue_block = "\n".join(f"- {line}" for line in issue_lines) if issue_lines else "- No structured issues were found."
    analysis_block = json.dumps(analysis, indent=2, ensure_ascii=False) if analysis else "{}"

    return (
        f"You are {action_label} in {project_path}.\n"
        "Use the smallest safe changes that make the quality gates pass.\n"
        "Preserve existing behavior unless a change is clearly justified.\n"
        f"Selected model: {selected_model or 'auto'}\n"
        f"Selection tier: {tier or 'unknown'}\n\n"
        f"Issue summary:\n{issue_block}\n\n"
        f"Analysis payload:\n{analysis_block}\n\n"
        "Return code edits only."
    )


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
