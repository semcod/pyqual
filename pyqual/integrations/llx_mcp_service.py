"""SSE transport wrapper for the llx MCP server."""

from __future__ import annotations

import argparse
import os
from typing import Any


def create_app() -> Any:
    """Create an ASGI app that exposes the llx MCP server over SSE."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse, Response
    from starlette.routing import Mount, Route

    from llx.mcp.server import server as llx_server
    from mcp.server.sse import SseServerTransport

    transport = SseServerTransport("/messages/")

    async def health(_request: Any) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "llx-mcp",
                "transport": "sse",
                "endpoint": "/sse",
            }
        )

    async def handle_sse(request: Any) -> Response:
        async with transport.connect_sse(request.scope, request.receive, request._send) as streams:
            await llx_server.run(
                streams[0],
                streams[1],
                llx_server.create_initialization_options(),
            )
        return Response()

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/sse", handle_sse, methods=["GET"]),
            Mount("/messages/", app=transport.handle_post_message),
        ]
    )


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the SSE server with uvicorn."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the MCP service."""
    parser = argparse.ArgumentParser(description="Run llx MCP over SSE for pyqual.")
    parser.add_argument(
        "--host",
        default=os.getenv("PYQUAL_LLX_MCP_HOST", "0.0.0.0"),
        help="Host interface to bind to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PYQUAL_LLX_MCP_PORT", "8000")),
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
