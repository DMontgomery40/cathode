# CLAUDE.md

This file provides guidance to coding agents working in this repository.

 **You MUST read ~/.codex/this/project/MEMORY.md and all links within to understand this repo and it's components**

## Project Overview

Cathode is a local-first explainer-video pipeline.

It supports:

- a Streamlit app for human-in-the-loop video creation
- an MCP server for agent/client-driven video creation
- local project storage under `projects/<project>/`
- image scenes, uploaded video scenes, narration generation, and final MP4 render

## Primary Commands

```bash
# Run the app
./start.sh

# Run the React/FastAPI app
./start.sh --react

# Manual app run
/opt/homebrew/bin/python3.10 -m streamlit run app.py --server.port 8517

# Manual React/FastAPI run
/opt/homebrew/bin/python3.10 -m uvicorn server.app:app --host 127.0.0.1 --port 9321 --reload
npm run dev --prefix frontend -- --host 127.0.0.1 --port 9322

# Run the MCP server over stdio
/opt/homebrew/bin/python3.10 cathode_mcp_server.py --transport stdio

# Run the MCP server over Streamable HTTP
CATHODE_MCP_PORT=8765 /opt/homebrew/bin/python3.10 cathode_mcp_server.py --transport streamable-http

# Batch rebuild / regenerate
python3.10 batch_regenerate.py

# Tests
PYTHONPATH=. /opt/homebrew/bin/python3.10 -m pytest -q
```

## Architecture

### User-facing entrypoints

- `app.py`: Streamlit UI
- `cathode_mcp_server.py`: MCP server
- `batch_regenerate.py`: simple batch rebuild/regenerate CLI

### Shared pipeline and storage

- `core/pipeline_service.py`: shared create/generate/render services
- `core/project_store.py`: local project persistence and artifact discovery
- `core/job_runner.py`: persisted background jobs
- `core/runtime.py`: provider availability and profile resolution
- `core/intake.py`: brief elicitation / bounded workspace inspection for headless requests

### Generation modules

- `core/director.py`: storyboard generation + narration/prompt refiners
- `core/image_gen.py`: image generation + image editing
- `core/voice_gen.py`: Kokoro / ElevenLabs / Chatterbox / OpenAI TTS
- `core/video_assembly.py`: final video assembly and per-scene previews
- `core/workflow.py`: normalized plan creation helpers
- `core/project_schema.py`: canonical brief / plan / scene normalization

## Source Of Truth

- `projects/<project>/plan.json`

Important persisted metadata:

- `meta.brief`
- `meta.render_profile`
- `meta.image_profile`
- `meta.tts_profile`
- `meta.video_path`

Important scene fields:

- `scene_type`
- `visual_prompt`
- `on_screen_text`
- `image_path`
- `video_path`
- `audio_path`
- `preview_path`

## Provider Model

The product is intentionally env-driven.

- LLM providers appear when `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` are present
- image generation uses Replicate when `REPLICATE_API_TOKEN` is present
- local image generation appears when `CATHODE_LOCAL_IMAGE_MODEL` is set
  - local image runtime can use torch/diffusers or Apple Silicon MLX, selected via `CATHODE_LOCAL_IMAGE_RUNTIME`
- image editing defaults to Replicate-backed `qwen/qwen-image-edit-2511`
- DashScope edit options appear only when `DASHSCOPE_API_KEY` or `ALIBABA_API_KEY` are present
- Kokoro is the always-available local voice path
- ElevenLabs, OpenAI TTS, and Chatterbox appear only when configured

Do not bloat the UI with raw provider plumbing.

## Constraints

- Keep the repo use-case agnostic.
- Keep prompts and labels generic.
- Prefer the fast happy path in demos and UX.
- Treat deep scene editing as optional power, not the main flow.
- Do not add work-specific publishing, review, or QC systems.

## Frontend Best Practices

### Parity is behavioral, not architectural

- Do not claim parity with Streamlit just because there is a matching route, component, or endpoint.
- Parity means the user can actually find the control, use it in the expected workspace, see the result, and recover from failure.
- If a feature is only technically present but buried in an irrelevant panel or awkward header slot, treat parity as incomplete.

### Put controls where the work happens

- Scene-specific actions belong in the Scenes workspace, close to the media stage and scene inspector.
- Project-wide actions may exist elsewhere, but if they are part of the day-to-day scene editing loop they should also be reachable from Scenes.
- Do not replace direct scene image/video replacement with only project-level library uploads.

### Verify the whole loop

- For uploads and generation actions, verify all of these before calling the fix done:
  - the intended user control is visible and usable
  - the correct API request is sent
  - the backend persists the change into `plan.json`
  - the React query/state layer refreshes
  - the media visibly changes in the relevant route
- "Endpoint exists" or "mutation returns 200" is not enough if the scene still looks unchanged.

### Make operator state visible

- Important actions need visible pending state, actionable error messages, and enough context to understand what provider/model/settings were used.
- If provider parameters materially affect output quality, expose the effective request/profile in the UI instead of making users guess.
- Surface persisted job logs and job requests in the app when they help debugging; do not force operators to inspect hidden files unless necessary.
- Unexpected server failures should return structured JSON with a short operator hint.

### Browser-first acceptance

- When the user is complaining about the product experience, trust the live browser over the code structure.
- Use real browser verification for final acceptance of placement, scroll behavior, upload actions, preview/render visibility, and error handling.
- Passing unit tests do not override a broken or misleading live UI.

 **You MUST read ~/.codex/this/project/MEMORY.md and all links within to understand this repo and it's components**