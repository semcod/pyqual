"""Client helpers for using the llx MCP service from pyqual.

This module now delegates to ``llx.mcp.workflows`` which contains the
canonical implementation of LlxMcpRunResult, run_llx_fix_workflow, and
run_llx_refactor_workflow.  The thin re-exports here preserve
backward-compatible imports for existing pyqual code.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from llx.mcp.client import LlxMcpClient  # canonical upstream
from llx.mcp.workflows import (  # canonical upstream
    DEFAULT_ISSUES_PATH,
    DEFAULT_OUTPUT_PATH,
    LlxMcpRunResult,
    run_llx_fix_workflow,
    run_llx_refactor_workflow,
)
from llx.utils.issues import (  # canonical upstream
    build_fix_prompt,
    load_issue_source as _load_issue_source,
)

DEFAULT_ENDPOINT = "http://localhost:8000/sse"

# Re-export so existing ``from pyqual.integrations.llx_mcp import …``
# keeps working without changes.
__all__ = [
    "LlxMcpClient",
    "LlxMcpRunResult",
    "build_fix_prompt",
    "run_llx_fix_workflow",
    "run_llx_refactor_workflow",
    "_load_issue_source",
    "build_parser",
    "main",
]


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
