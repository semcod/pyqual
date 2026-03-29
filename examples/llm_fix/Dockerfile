FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY llx /workspace/llx
COPY pyqual /workspace/pyqual

RUN python -m pip install --upgrade pip && \
    pip install -e /workspace/llx && \
    pip install aider-chat && \
    pip install -e "/workspace/pyqual[mcp]"

EXPOSE 8000

CMD ["python", "-m", "pyqual.integrations.llx_mcp_service", "--host", "0.0.0.0", "--port", "8000"]
