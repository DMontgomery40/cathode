# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10
ARG NODE_VERSION=22

FROM node:${NODE_VERSION}-bookworm-slim AS frontend-build

WORKDIR /build/frontend

ARG NPM_CONFIG_REGISTRY=""

COPY frontend/package.json frontend/package-lock.json ./
RUN if [ -n "${NPM_CONFIG_REGISTRY}" ]; then npm config set registry "${NPM_CONFIG_REGISTRY}"; fi \
    && npm ci

COPY frontend/ ./
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build \
    && npm prune --omit=dev

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="betTube Studio"
LABEL org.opencontainers.image.description="Local-first video pipeline with React/FastAPI, Streamlit, and MCP surfaces."
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    BETTUBE_STUDIO_MCP_TRANSPORT=streamable-http \
    BETTUBE_STUDIO_MCP_HOST=0.0.0.0 \
    BETTUBE_STUDIO_MCP_PORT=8765 \
    BETTUBE_STUDIO_MCP_HTTP_PATH=/mcp \
    BETTUBE_STUDIO_API_BASE_URL=http://127.0.0.1:9321 \
    CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        espeak-ng \
        ffmpeg \
        fonts-dejavu-core \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libgbm1 \
        libgtk-3-0 \
        libnss3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-build /usr/local/bin/npm /usr/local/bin/npm
COPY --from=frontend-build /usr/local/bin/npx /usr/local/bin/npx
COPY --from=frontend-build /usr/local/lib/node_modules /usr/local/lib/node_modules

# Dependency install from pyproject.toml. core/ + server/ + README.md are copied
# first (the build backend needs the packages and readme) so this layer is cached
# independently of app.py / prompts / scripts churn. No registry URL is baked in:
# PIP_INDEX_URL / PIP_EXTRA_INDEX_URL are build args for approved-mirror corp builds.
COPY pyproject.toml README.md ./
COPY core ./core
COPY server ./server
ARG PIP_INDEX_URL=""
ARG PIP_EXTRA_INDEX_URL=""
RUN python -m pip install --upgrade pip setuptools wheel \
    && set -- \
    && if [ -n "${PIP_INDEX_URL}" ]; then set -- "$@" --index-url "${PIP_INDEX_URL}"; fi \
    && if [ -n "${PIP_EXTRA_INDEX_URL}" ]; then set -- "$@" --extra-index-url "${PIP_EXTRA_INDEX_URL}"; fi \
    && python -m pip install "$@" .[server]

COPY . .
COPY --from=frontend-build /build/frontend/dist ./frontend/dist
COPY --from=frontend-build /build/frontend/node_modules ./frontend/node_modules

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/projects /app/output \
    && chown -R app:app /app

USER app

FROM runtime AS mcp
EXPOSE 8765
CMD ["python", "bettube_studio_mcp_server.py", "--transport", "streamable-http"]

FROM runtime AS streamlit
EXPOSE 8517
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8517"]

FROM runtime AS web
EXPOSE 9321
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9321/api/health', timeout=5).read()"
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "9321"]
