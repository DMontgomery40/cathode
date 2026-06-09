#!/bin/bash
# Start script for betTube Studio.
# Default mode: Streamlit app on 8517.
# React mode: FastAPI on 9321 + Vite on 9322 via `./start.sh --react`.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${BETTUBE_STUDIO_PYTHON:-$ROOT_DIR/.venv/bin/python3.10}"
FALLBACK_PYTHON="/opt/homebrew/bin/python3.10"

STREAMLIT_PORT="${STREAMLIT_PORT:-8517}"
BETTUBE_STUDIO_API_PORT="${BETTUBE_STUDIO_API_PORT:-9321}"
BETTUBE_STUDIO_FRONTEND_PORT="${BETTUBE_STUDIO_FRONTEND_PORT:-9322}"

MODE="streamlit"
EXTRA_ARGS=()
API_PID=""

usage() {
  cat <<'EOF'
Usage:
  ./start.sh                Start the legacy Streamlit app on 8517
  ./start.sh --streamlit    Start the legacy Streamlit app on 8517
  ./start.sh --react        Start FastAPI on 9321 and the React app on 9322
  ./start.sh --help         Show this help

Ports:
  STREAMLIT_PORT          Streamlit port (default: 8517)
  BETTUBE_STUDIO_API_PORT        FastAPI port (default: 9321)
  BETTUBE_STUDIO_FRONTEND_PORT   React/Vite port (default: 9322)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --react|react|--frontend|frontend|--web|web)
      MODE="react"
      shift
      ;;
    --streamlit|streamlit)
      MODE="streamlit"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

require_python() {
  if [[ ! -x "$PYTHON" ]] && [[ -x "$FALLBACK_PYTHON" ]]; then
    PYTHON="$FALLBACK_PYTHON"
  fi

  if [[ ! -x "$PYTHON" ]]; then
    echo "Error: Python 3.10 not found at $PYTHON or $FALLBACK_PYTHON"
    echo "Install with: uv python install 3.10 && uv venv --python 3.10 .venv"
    exit 1
  fi
}

require_npm() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm not found in PATH"
    echo "Install Node.js and npm before using --react mode."
    exit 1
  fi
}

load_env() {
  if [[ -f "$ROOT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
  fi
}

install_python_requirements_if_missing() {
  local imports="$1"
  shift
  local extras=("$@")

  if ! "$PYTHON" -c "$imports" >/dev/null 2>&1; then
    echo "Missing Python dependencies. Installing from pyproject.toml..."
    local target="$ROOT_DIR"
    if [[ ${#extras[@]} -gt 0 ]]; then
      local joined
      joined=$(IFS=,; echo "${extras[*]}")
      target="${ROOT_DIR}[${joined}]"
    fi
    # No index URL is baked in; uv/pip read UV_INDEX_URL / PIP_INDEX_URL /
    # PIP_EXTRA_INDEX_URL from the environment for approved-mirror corp installs.
    if command -v uv >/dev/null 2>&1; then
      uv pip install --python "$PYTHON" -e "$target"
    else
      "$PYTHON" -m pip install -e "$target"
    fi
  fi
}

install_frontend_requirements_if_missing() {
  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    echo "Missing frontend dependencies. Installing..."
    npm install --prefix "$ROOT_DIR/frontend"
  fi
}

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"

  for ((i = 1; i <= attempts; i++)); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done

  echo "Error: ${label} did not become ready at ${url}"
  return 1
}

run_streamlit() {
  install_python_requirements_if_missing \
    "import streamlit, kokoro, anthropic, openai, replicate"

  echo "Starting betTube Studio Streamlit app..."
  echo "Opening http://127.0.0.1:${STREAMLIT_PORT}"
  cd "$ROOT_DIR"
  local streamlit_cmd=(
    "$PYTHON"
    -m
    streamlit
    run
    app.py
    --server.port
    "${STREAMLIT_PORT}"
  )
  if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    streamlit_cmd+=("${EXTRA_ARGS[@]}")
  fi
  "${streamlit_cmd[@]}"
}

run_react_stack() {
  require_npm
  install_python_requirements_if_missing \
    "import fastapi, uvicorn; import streamlit, kokoro, anthropic, openai, replicate" \
    server
  install_frontend_requirements_if_missing

  trap cleanup EXIT INT TERM

  echo "Starting betTube Studio API..."
  echo "  API:      http://127.0.0.1:${BETTUBE_STUDIO_API_PORT}"
  echo "  Frontend: http://127.0.0.1:${BETTUBE_STUDIO_FRONTEND_PORT}"

  cd "$ROOT_DIR"
  "$PYTHON" -m uvicorn server.app:app --host 127.0.0.1 --port "${BETTUBE_STUDIO_API_PORT}" --reload &
  API_PID=$!

  wait_for_http "http://127.0.0.1:${BETTUBE_STUDIO_API_PORT}/api/health" "betTube Studio API"

  echo "Starting betTube Studio React app..."
  npm run dev --prefix "$ROOT_DIR/frontend" -- --host 127.0.0.1 --port "${BETTUBE_STUDIO_FRONTEND_PORT}"
}

require_python
load_env

case "$MODE" in
  react)
    run_react_stack
    ;;
  streamlit)
    run_streamlit
    ;;
  *)
    echo "Unknown mode: $MODE"
    usage
    exit 1
    ;;
esac
