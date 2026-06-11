# Deployment Guide

betTube Studio ships as a single web container (FastAPI serving `/api/*` plus the built React SPA from the same origin) and an optional MCP container for agent-driven runs.

## Docker

```bash
# Web control room (FastAPI + built React app on one origin)
docker compose up --build web          # http://localhost:9321

# MCP server over Streamable HTTP
docker compose --profile mcp up --build mcp   # port 8765, path /mcp
```

Standalone images:

```bash
docker build --target web -t bettube-studio .
docker run --rm -p 9321:9321 \
  -v "$PWD/projects:/app/projects" -v "$PWD/output:/app/output" bettube-studio
```

For approved internal package mirrors, pass `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` / `NPM_CONFIG_REGISTRY` as build args (see `compose.yaml`); no registry URLs are baked into the repo.

## Required environment

Provider keys are read from the environment (locally via `.env`, which is gitignored; in production inject them through your secret manager). Only set what you use:

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — storyboard/TTS LLM providers (at least one required)
- `REPLICATE_API_TOKEN` — image/video generation fallback
- `ELEVENLABS_API_KEY`, `DASHSCOPE_API_KEY`, `ALIBABA_API_KEY` — optional providers
- Proxy routing: `OPENAI_BASE_URL` + `LITELLM_API_KEY`/`AIPROXY_API_KEY`, `ANTHROPIC_BASE_URL` — see `.env.example` for the full reference

## Server configuration

- `BETTUBE_STUDIO_API_PORT` — FastAPI port (default 9321)
- `BETTUBE_STUDIO_CORS_ORIGINS` — comma-separated allowed origins. Defaults to the localhost dev ports; set this to the deployed frontend origin(s) when the SPA is served from a different origin. A literal `*` cannot be combined with credentialed requests — list origins explicitly.
- `BETTUBE_STUDIO_LOG_LEVEL` — Python logging level (default `INFO`). Logs go to stdout in `timestamp level logger message` format; swap the formatter in `server/logging_setup.py` if you need JSON.
- `BETTUBE_STUDIO_ENABLE_REMOTION` — master switch for the Remotion/motion surface (default off; see the Remotion section below).
- `BETTUBE_STUDIO_FRONTEND_DIST` — override the directory the SPA is served from (defaults to `frontend/dist`)
- `VITE_API_BASE_URL` — build-time base URL for the frontend API client; leave empty when FastAPI serves the SPA (same-origin `/api`)

## Health and observability

- `GET /api/health` returns `{"status": "ok"}`; the Docker image and compose file already wire it as the container health check.
- Background job logs persist per project under `projects/<name>/.bettube-studio/jobs/<job_id>.log`, and are exposed at `GET /api/projects/{project}/jobs/{job_id}/log`.

## Authentication

The server has no built-in authentication. Deploy it behind your standard reverse proxy / gateway with authentication, or keep it on a private network. Do not expose it directly to the internet as-is.

## State and persistence

All state is on the filesystem — there is no database:

- `projects/<name>/` — plan.json, generated assets, renders, job state
- `output/` — auxiliary render output

Mount both as volumes (compose already does). Backup = copy the directories.

## Remotion (optional, hidden by default)

The Remotion/motion surface is gated behind a master switch and is OFF by default. Two conditions must both hold before any motion option appears in the GUI:

1. `BETTUBE_STUDIO_ENABLE_REMOTION=1` in the server environment, and
2. the optional Remotion toolchain installed in `frontend/` (`npm install remotion @remotion/renderer @remotion/player @remotion/transitions` — these are deliberately not in `package.json`).

With the switch off, every project renders through `ffmpeg`, the scene preview uses the plain media player, and no motion scene type / motion composition family / Remotion engine option is shown. Nothing breaks when it is absent — the stub fallback is wired in `frontend/vite.config.ts` and `core/runtime.py` (`remotion_available()`). Do not enable it until your team has decided how to own the Remotion render path.
