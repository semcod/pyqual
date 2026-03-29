from __future__ import annotations

import json
from pathlib import Path

from pyqual.integrations.llx_mcp import build_fix_prompt
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

    assert "python -m pyqual.integrations.llx_mcp" in snippet
    assert "PYQUAL_LLX_MCP_URL" in snippet
    assert "llx_fix_success_min" in snippet


def test_build_fix_prompt_uses_issue_summary() -> None:
    prompt = build_fix_prompt(
        Path("/workspace/project"),
        [{"file": "app.py", "line": 12, "severity": "high", "message": "Missing type hint"}],
        {"selection": {"tier": "balanced", "model_id": "claude-sonnet-4"}},
    )

    assert "/workspace/project" in prompt
    assert "Missing type hint" in prompt
    assert "claude-sonnet-4" in prompt
