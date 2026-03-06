FROM python:3.10-slim

LABEL org.opencontainers.image.title="Cathode MCP Server"
LABEL org.opencontainers.image.description="Cathode turns intent into video and exposes the workflow over MCP."
LABEL org.opencontainers.image.source="https://example.invalid/cathode"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CATHODE_MCP_TRANSPORT=streamable-http \
    CATHODE_MCP_HOST=0.0.0.0 \
    CATHODE_MCP_PORT=8765 \
    CATHODE_MCP_HTTP_PATH=/mcp

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["python", "cathode_mcp_server.py", "--transport", "streamable-http"]

