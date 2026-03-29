from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

import pyqual.cli as cli_module
from pyqual.cli import app
from pyqual.integrations.llx_mcp import build_fix_prompt
from pyqual.integrations.llx_mcp import LlxMcpRunResult
from pyqual.integrations.llx_mcp_service import McpServiceState, create_app
from pyqual.plugins import LlxMcpFixCollector, install_plugin_config


def test_llx_mcp_plugin_collects_metrics(tmp_path: Path) -> None:
    pyqual_dir = tmp_path / ".pyqual"
    pyqual_dir.mkdir()
    (pyqual_dir / "llx_mcp.json").write_text(
        json.dumps(
            {
                "success": True,
                "tool_calls": 2,
                "analysis": {
                    "metrics": {"total_files": 12, "avg_cc": 4.5},
                    "selection": {"tier": "balanced"},
                },
                "aider": {
                    "returncode": 0,
                    "method": "docker",
                    "stdout": "fixed\n",
                    "stderr": "",
                },
            }
        )
    )

    metrics = LlxMcpFixCollector().collect(tmp_path)

    assert metrics["llx_fix_success"] == 1.0
    assert metrics["llx_fix_returncode"] == 0.0
    assert metrics["llx_fix_uses_docker"] == 1.0
    assert metrics["llx_tool_calls"] == 2.0
    assert metrics["llx_project_files"] == 12.0
    assert metrics["llx_avg_cc"] == 4.5
    assert metrics["llx_fix_tier_rank"] == 3.0


def test_llx_mcp_plugin_config_example_contains_stage() -> None:
    snippet = install_plugin_config("llx-mcp-fixer")

    assert "pyqual mcp-fix" in snippet
    assert "PYQUAL_LLX_MCP_URL" in snippet
    assert "llx_fix_success_min" in snippet


def test_mcp_fix_cli_invokes_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / ".pyqual" / "llx_mcp.json"
    captured: dict[str, object] = {}

    async def fake_run_llx_fix_workflow(**kwargs: object) -> LlxMcpRunResult:
        captured.update(kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"success": True, "tool_calls": 2}))
        return LlxMcpRunResult(
            success=True,
            endpoint="http://localhost:8000/sse",
            project_path="/workspace/project",
            issues_path=str(tmp_path / ".pyqual" / "errors.json"),
            prompt="Fix the project",
            tool_calls=2,
            analysis={"selection": {"tier": "balanced", "model_id": "claude-sonnet-4"}},
            aider={"success": True, "returncode": 0, "method": "docker"},
            issues=[],
            model="claude-sonnet-4",
        )

    monkeypatch.setattr(cli_module, "run_llx_fix_workflow", fake_run_llx_fix_workflow)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "mcp-fix",
            "--workdir",
            str(tmp_path),
            "--project-path",
            "/workspace/project",
            "--output",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured["project_path"] == "/workspace/project"
    assert captured["workdir"] == tmp_path
    assert output_path.exists()
    assert '"success": true' in result.output
    assert '"tool_calls": 2' in result.output


def test_mcp_service_cli_shows_friendly_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_llx_mcp_service(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("pyqual mcp-service requires `uvicorn`")

    monkeypatch.setattr(cli_module, "run_llx_mcp_service", fake_run_llx_mcp_service)

    runner = CliRunner()
    result = runner.invoke(app, ["mcp-service"])

    assert result.exit_code == 1
    assert "pyqual mcp-service requires `uvicorn`" in result.output


@pytest.mark.asyncio
async def test_persistent_mcp_service_exposes_health_and_metrics() -> None:
    class FakeServer:
        async def run(self, _read_stream: object, _write_stream: object, _options: object) -> None:
            return None

        def create_initialization_options(self) -> object:
            return object()

    app = create_app(state=McpServiceState(), llx_server=FakeServer())
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        health = health_response.json()
        assert health["status"] == "ok"
        assert health["service"] == "llx-mcp"
        assert health["transport"] == "sse"
        assert health["sse_sessions_active"] == 0

        metrics_response = await client.get("/metrics")
        assert metrics_response.status_code == 200
        metrics = metrics_response.text
        assert "pyqual_mcp_http_requests_total" in metrics
        assert 'pyqual_mcp_route_hits_total{route="health"}' in metrics
        assert 'pyqual_mcp_route_hits_total{route="metrics"}' in metrics


def test_build_fix_prompt_uses_issue_summary() -> None:
    prompt = build_fix_prompt(
        Path("/workspace/project"),
        [{"file": "app.py", "line": 12, "severity": "high", "message": "Missing type hint"}],
        {"selection": {"tier": "balanced", "model_id": "claude-sonnet-4"}},
    )

    assert "/workspace/project" in prompt
    assert "Missing type hint" in prompt
    assert "claude-sonnet-4" in prompt
