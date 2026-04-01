"""Persistent llx MCP service with health and metrics endpoints.

This module now delegates to ``llx.mcp.service`` which contains the
canonical implementation of McpServiceState, create_service_app, and
run_service.  The thin wrappers here preserve backward-compatible
imports for existing pyqual code and honour PYQUAL_LLX_MCP_* env vars.
"""

import argparse
import os
from typing import Any

from llx.mcp.service import (  # canonical upstream
    DEFAULT_MCP_PORT,
    McpServiceState,
    create_service_app,
    run_service as _llx_run_service,
)

# Re-export so existing ``from pyqual.integrations.llx_mcp_service import …``
# keeps working without changes.
__all__ = [
    "McpServiceState",
    "create_app",
    "run_server",
    "build_parser",
    "main",
    "DEFAULT_MCP_PORT",
]


def create_app(state: McpServiceState | None = None, llx_server: Any | None = None) -> Any:
    """Create an ASGI app — delegates to ``llx.mcp.service.create_service_app``."""
    return create_service_app(state=state, llx_server=llx_server)


def run_server(host: str = "0.0.0.0", port: int = DEFAULT_MCP_PORT, state: McpServiceState | None = None) -> None:
    """Run the persistent MCP service with uvicorn."""
    _llx_run_service(host=host, port=port, state=state)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the MCP service."""
    parser = argparse.ArgumentParser(description="Run llx MCP as a persistent SSE service for pyqual.")
    parser.add_argument(
        "--host",
        default=os.getenv("PYQUAL_LLX_MCP_HOST", "0.0.0.0"),
        help="Host interface to bind to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PYQUAL_LLX_MCP_PORT", str(DEFAULT_MCP_PORT))),
        help="Port to listen on.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the llx MCP service."""
    parser = build_parser()
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
