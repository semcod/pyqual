# llm_fix + llx MCP

This example shows how to connect `pyqual` to a Dockerized `llx` MCP service.

## What it does

- `llx` runs as an MCP SSE service in Docker.
- `pyqual` uses `pyqual mcp-refactor` as a pipeline stage.
- The helper first runs `llx_analyze`, then calls the `aider` MCP tool with a refactor prompt.
- The run result is saved to `.pyqual/llx_mcp.json`, which is also visible in `pyqual status`.

## Files

- `Dockerfile` - builds an image containing both `llx` and `pyqual`
- `docker-compose.yml` - starts the MCP service on `http://localhost:8000/sse`
- `pyqual.yaml` - pipeline config that uses the MCP refactor stage

## Quick start

1. Build and start the MCP service:

```bash
docker compose -f examples/llm_fix/docker-compose.yml up --build -d
```

2. Run the refactor workflow from your project directory:

```bash
pyqual mcp-refactor --workdir . --project-path /workspace/project
```

Or run the full pipeline with the refactor stage enabled:

```bash
export PYQUAL_LLX_MCP_URL=http://localhost:8000/sse
export PYQUAL_LLX_PROJECT_PATH=/workspace/project
pyqual run -c pyqual.yaml
```

3. Inspect the latest refactor run:

```bash
cat .pyqual/llx_mcp.json
pyqual status
```

## Recommended setup

- Use `PYQUAL_LLX_PROJECT_PATH=/workspace/project` so the host project maps to the same path inside the MCP container.
- Keep `PYQUAL_LLX_USE_DOCKER=false` unless you want the `aider` tool to spawn its own nested Docker container.
- If your llx routing relies on Ollama or another backend, expose that backend to the container as well.
- For local development, you can also start the persistent service with `pyqual mcp-service --host 0.0.0.0 --port 8000`.

## Plugin workflow

You can register the plugin with:

```bash
pyqual plugin add llx-mcp-fixer
```

That will append a ready-to-customize `llx-mcp-fixer` snippet to `pyqual.yaml`.
