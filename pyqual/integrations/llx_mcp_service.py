"""Persistent llx MCP service with health and metrics endpoints."""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

DEFAULT_MCP_PORT = 8000


@dataclass
class McpServiceState:
    """Runtime state exposed via health and metrics endpoints."""

    service_name: str = "llx-mcp"
    transport: str = "sse"
    started_at: float = field(default_factory=time.monotonic)
    started_at_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sse_sessions_total: int = 0
    sse_sessions_active: int = 0
    mcp_messages_total: int = 0
    mcp_messages_failed_total: int = 0
    http_requests_total: int = 0
    route_hits: Counter[str] = field(default_factory=Counter)
    last_activity_at: float | None = None
    last_error: str | None = None

    def mark_request(self, route: str) -> None:
        self.http_requests_total += 1
        self.route_hits[route] += 1
        self.last_activity_at = time.monotonic()

    def mark_session_open(self) -> None:
        self.sse_sessions_total += 1
        self.sse_sessions_active += 1
        self.last_activity_at = time.monotonic()

    def mark_session_close(self) -> None:
        self.sse_sessions_active = max(0, self.sse_sessions_active - 1)
        self.last_activity_at = time.monotonic()

    def mark_message(self, success: bool) -> None:
        self.mcp_messages_total += 1
        if not success:
            self.mcp_messages_failed_total += 1
        self.last_activity_at = time.monotonic()

    def mark_error(self, error: Exception | str) -> None:
        self.last_error = str(error)
        self.last_activity_at = time.monotonic()

    def uptime_seconds(self) -> float:
        return round(time.monotonic() - self.started_at, 3)

    def last_activity_seconds_ago(self) -> float | None:
        if self.last_activity_at is None:
            return None
        return round(time.monotonic() - self.last_activity_at, 3)

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.last_error is None else "degraded",
            "service": self.service_name,
            "transport": self.transport,
            "started_at": self.started_at_iso,
            "uptime_seconds": self.uptime_seconds(),
            "sse_sessions_total": self.sse_sessions_total,
            "sse_sessions_active": self.sse_sessions_active,
            "mcp_messages_total": self.mcp_messages_total,
            "mcp_messages_failed_total": self.mcp_messages_failed_total,
            "http_requests_total": self.http_requests_total,
            "last_activity_seconds_ago": self.last_activity_seconds_ago(),
            "last_error": self.last_error,
            "routes": dict(self.route_hits),
        }

    def metrics_text(self) -> str:
        lines: list[str] = []
        lines.extend(
            [
                "# HELP pyqual_mcp_uptime_seconds Service uptime in seconds.",
                "# TYPE pyqual_mcp_uptime_seconds gauge",
                f"pyqual_mcp_uptime_seconds {self.uptime_seconds():.3f}",
                "# HELP pyqual_mcp_sse_sessions_total Total SSE sessions opened.",
                "# TYPE pyqual_mcp_sse_sessions_total counter",
                f"pyqual_mcp_sse_sessions_total {self.sse_sessions_total}",
                "# HELP pyqual_mcp_sse_sessions_active Current active SSE sessions.",
                "# TYPE pyqual_mcp_sse_sessions_active gauge",
                f"pyqual_mcp_sse_sessions_active {self.sse_sessions_active}",
                "# HELP pyqual_mcp_messages_total Total MCP messages handled by the service.",
                "# TYPE pyqual_mcp_messages_total counter",
                f"pyqual_mcp_messages_total {self.mcp_messages_total}",
                "# HELP pyqual_mcp_messages_failed_total Total failed MCP message attempts.",
                "# TYPE pyqual_mcp_messages_failed_total counter",
                f"pyqual_mcp_messages_failed_total {self.mcp_messages_failed_total}",
                "# HELP pyqual_mcp_http_requests_total Total HTTP requests handled by the service.",
                "# TYPE pyqual_mcp_http_requests_total counter",
                f"pyqual_mcp_http_requests_total {self.http_requests_total}",
                "# HELP pyqual_mcp_last_activity_seconds_ago Seconds since the last observed activity.",
                "# TYPE pyqual_mcp_last_activity_seconds_ago gauge",
            ]
        )
        last_activity = self.last_activity_seconds_ago()
        if last_activity is None:
            lines.append("pyqual_mcp_last_activity_seconds_ago 0")
        else:
            lines.append(f"pyqual_mcp_last_activity_seconds_ago {last_activity:.3f}")

        lines.extend(
            [
                "# HELP pyqual_mcp_route_hits_total Requests per route.",
                "# TYPE pyqual_mcp_route_hits_total counter",
            ]
        )
        for route, count in sorted(self.route_hits.items()):
            route_label = _escape_label_value(route)
            lines.append(f'pyqual_mcp_route_hits_total{{route="{route_label}"}} {count}')

        return f"{chr(10).join(lines)}\n"


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _load_llx_server() -> Any:
    try:
        from llx.mcp.server import server as llx_server
    except ImportError as exc:  # pragma: no cover - runtime dependency error
        raise RuntimeError(
            "llx is required to run the MCP service. Install the llx package alongside pyqual."
        ) from exc
    return llx_server


def create_app(state: McpServiceState | None = None, llx_server: Any | None = None) -> Any:
    """Create an ASGI app that exposes the llx MCP server over SSE."""
    try:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse, PlainTextResponse, Response
        from starlette.routing import Mount, Route

        from mcp.server.sse import SseServerTransport
    except ImportError as exc:  # pragma: no cover - dependency error
        raise RuntimeError(
            "pyqual mcp-service requires the MCP runtime dependencies. Reinstall with `pip install -e '.[mcp]'` "
            "or `pip install mcp uvicorn starlette sse-starlette`."
        ) from exc

    service_state = state or McpServiceState()
    mcp_server = llx_server or _load_llx_server()
    transport = SseServerTransport("/messages/")

    async def health(_request: Any) -> JSONResponse:
        service_state.mark_request("health")
        return JSONResponse(service_state.health_payload())

    async def metrics(_request: Any) -> PlainTextResponse:
        service_state.mark_request("metrics")
        return PlainTextResponse(service_state.metrics_text(), media_type="text/plain; version=0.0.4; charset=utf-8")

    async def handle_sse(request: Any) -> Response:
        service_state.mark_request("sse")
        service_state.mark_session_open()
        try:
            async with transport.connect_sse(request.scope, request.receive, request._send) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp_server.create_initialization_options(),
                )
        except Exception as exc:
            service_state.mark_error(exc)
            raise
        finally:
            service_state.mark_session_close()
        return Response()

    async def handle_post_message(scope: Any, receive: Any, send: Any) -> None:
        service_state.mark_request("messages")
        try:
            await transport.handle_post_message(scope, receive, send)
        except Exception as exc:
            service_state.mark_message(False)
            service_state.mark_error(exc)
            raise
        else:
            service_state.mark_message(True)

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/metrics", metrics, methods=["GET"]),
            Route("/sse", handle_sse, methods=["GET"]),
            Mount("/messages/", app=handle_post_message),
        ]
    )


def run_server(host: str = "0.0.0.0", port: int = DEFAULT_MCP_PORT, state: McpServiceState | None = None) -> None:
    """Run the persistent MCP service with uvicorn."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency error
        raise RuntimeError(
            "pyqual mcp-service requires `uvicorn`. Reinstall with `pip install -e '.[mcp]'` or `pip install uvicorn`."
        ) from exc

    uvicorn.run(create_app(state=state), host=host, port=port, log_level="info")


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
