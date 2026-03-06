# CLAUDE.md

This file provides guidance to coding agents working in this repository.

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

# Manual app run
/opt/homebrew/bin/python3.10 -m streamlit run app.py --server.port 8517

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
