<p align="center">
  <img src="docs/assets/cathode-logo.png" alt="Cathode logo" width="220">
</p>

# Cathode

Cathode is a local-first explainer-video pipeline with three main surfaces:

- a React + FastAPI control room for the current workspace-first UI
- a legacy Streamlit app for the older manual step-by-step path
- an MCP server for agent/client-driven runs

It turns rough notes, source text, or a finished script into a local project folder plus a rendered MP4, and it now supports classic, hybrid, and motion-first composition modes.

## Watch The Demo

<p align="center">
  <a href="https://youtu.be/HHHbcHobg-A">
    <img src="docs/assets/cathode-demo-youtube-card.png" alt="Watch the Cathode demo on YouTube" width="720">
  </a>
</p>

Cathode now has four practical lanes:

1. `React/FastAPI control room`
   Fill in Brief Studio, hit the primary button, watch the background job/logs, then land on the final MP4.
2. `Legacy Streamlit app`
   Use the older manual step-by-step path when you want a more explicit scene-by-scene workflow.
3. `MCP workflow`
   Call `make_video` from an agent or client and let Cathode build the local project in the background.
4. `Live demo workflow`
   Launch or attach to a real app, capture fresh footage, review it, then feed the approved clips into Cathode for final render.

If you only remember one thing, remember this:

- most users only need the React/FastAPI app or MCP path
- the packaged live-demo skill is for cases where real UI footage is the story
- the scene editor is there for surgical fixes, not because the happy path should feel heavy

## What It Does

- brief-driven storyboard generation with `source_mode` and `composition_mode`
- image scenes, video scenes, and Remotion-backed motion scenes
- a one-button GUI background job path plus storyboard-only/manual editing when you want it
- scene-by-scene narration, prompt, media, preview, and operator-log editing
- persisted demo-target metadata and reviewed footage manifests for live-demo runs
- local MP4 render through `ffmpeg` or Remotion, depending on the resolved render backend
- MCP tools and web API job routes for agent/client-driven video generation

## Pick A Lane

### 1. React/FastAPI Control Room

Use this for the current workspace-based UI.

```bash
./start.sh --react
```

The main workspaces are:

- `Brief`
- `Scenes`
- `Render`
- `Queue`
- `Settings`

In `Brief Studio`, there are now two clearly separate actions:

1. primary path: start the full background video run
2. secondary path: generate or rebuild only the storyboard

If demo-target context or reviewed footage is present, the GUI prefers the hybrid path automatically unless you explicitly choose something else.

### 2. Legacy Streamlit App

Use this when you want the older manual step-by-step flow.

```bash
./start.sh
```

This is still supported, but the React/FastAPI control room is the more current operator surface.

### 3. Agent / MCP

Use this when an agent or client should drive Cathode programmatically.

```bash
/opt/homebrew/bin/python3.10 cathode_mcp_server.py --transport stdio
```

The core tool is `make_video`. It can inspect a bounded workspace, accept explicit source files, persist demo-target metadata, and accept reviewed `footage_paths` / `footage_manifest` inputs for mixed-media demos.

The React GUI and the MCP path now converge on the same persisted background-job model instead of maintaining separate orchestration logic.
The web stack also exposes the same job model through `POST /api/jobs/make-video`.

### 4. Live Product Demo Skill

Use this when the video should prove a real running product.

The packaged skill now lives in:

- `skills/cathode-project-demo/`
- `.claude/skills/cathode-project-demo/`

Its flow is:

1. bootstrap Cathode
2. prepare a live capture session
3. launch or attach to the target app
4. capture fresh states in a real browser
5. review the footage
6. hand approved clips into Cathode
7. render

This path is capture-first and review-first. It does not assume existing README screenshots are good enough.
The QC pass is supposed to run inside Codex or Claude as a spawned reviewer sub-agent looking at extracted images only, not as some separate external “vision model” workflow. The reviewer prompt should stay tiny and human, more like “hey, check out my demo vid” than a schema dump.
The parent agent should save that raw reviewer reply, translate it into Cathode’s structured `accept / warn / retry` observations, and then let the deterministic review rules decide retries and handoff safety.

In practice, that review loop is:

1. `extract_review_frames.py` creates the image bundle.
2. A spawned worker sub-agent sees only those frames plus the short gut-check prompt.
3. The parent agent saves the raw reply, seeds `review_observations.template.json` with `init_review_observations.py`, fills the structured observations, and runs `review_bundle.py`.

The packaged live-demo lane now also has a real capture driver and retry-plan tool:

- `capture_live_demo.py`: run a Playwright-backed walkthrough from a capture plan and keep raw browser video, trace, screenshots, and a step manifest.
- `apply_retry_actions.py`: mutate the capture plan from bounded retry actions before rerunning capture.

## Remotion And Composition Modes

Cathode no longer stops at still-image and clip-only storyboards.

- `classic`
  image + video scenes, with `ffmpeg` as the default final render backend
- `hybrid`
  mix image, video, and motion scenes in one project; Remotion is the default render backend when the local toolchain is available
- `motion_only`
  build the project around motion scenes plus narration

Motion scenes are template-first in the current product and render through the local Remotion toolchain bundled in `frontend/`. The React app only exposes motion and hybrid options when the Remotion toolchain is actually runnable on this machine.

Important timing rule: narration audio is still the source of truth. Cathode computes scene durations, video trim/speed/hold behavior, and the Remotion manifest from the same timing contract, so hybrid renders stay in sync instead of drifting.

## Demo Assets

- Product demo: `docs/assets/__storyboard-demo.mp4`
- LocalLLaMA short demo: `docs/assets/localllama-demo.mp4`
- Mixed-media workflow clip: `docs/assets/ui-workflow-clip.mp4`
- Brief Studio screenshot: `docs/assets/brief-studio-focus.png`
- Motion scene workspace screenshot: `docs/assets/motion-scene-focus.png`
- Render workspace screenshot: `docs/assets/render-finished-focus.png`
- Sample prompt brief: `docs/demo-brief.md`

### Current UI

<p align="center">
  <img src="docs/assets/motion-scene-focus.png" alt="Cathode Scenes workspace showing a motion scene with Remotion preview controls" width="100%">
</p>

<p align="center">
  <img src="docs/assets/brief-studio-focus.png" alt="Cathode Brief Studio with source mode and composition mode controls" width="48%">
  <img src="docs/assets/render-finished-focus.png" alt="Cathode Render workspace with a finished video artifact" width="48%">
</p>

## Provider Model

Cathode is env-driven on purpose.

- `OPENAI_API_KEY`: OpenAI storyboard and optional OpenAI TTS
- `ANTHROPIC_API_KEY`: Anthropic storyboard
- `REPLICATE_API_TOKEN`: Qwen image generation, Replicate-backed image edit, and Chatterbox voice
- `CATHODE_LOCAL_IMAGE_MODEL`: optional local Hugging Face image generation for image scenes
- `ELEVENLABS_API_KEY`: ElevenLabs narration
- `DASHSCOPE_API_KEY` or `ALIBABA_API_KEY`: optional DashScope image edit
- `CATHODE_LOCAL_VIDEO_COMMAND` and/or `CATHODE_LOCAL_VIDEO_ENDPOINT`: optional local video generation for video scenes
- `CATHODE_LOCAL_VIDEO_MODEL`: optional local model label or path passed through to that backend
- Node + the installed frontend workspace: local Remotion motion/hybrid rendering
- Kokoro remains the always-available local voice option

Only configured providers appear in the UI. If you leave a key out, the UI stays quieter.

## Local Vs Cloud

Cathode is local-first, not cloud-hosted.

- the app runs locally
- projects live under `projects/<project>/`
- previews and final renders happen locally
- uploaded stills and clips stay local
- Kokoro is local TTS
- video scenes can use a local generation backend when configured
- motion and hybrid renders happen locally through Remotion when available
- persisted job state and logs live under `projects/<project>/.cathode/jobs/`

For visuals, the built-in AI image path can run either through Replicate or through a configured local Hugging Face Qwen model. If neither is configured, you can still upload stills yourself. Video scenes can come from reviewed footage, the live-demo agent path, or a configured local video backend. Motion scenes render through the local Remotion layer when the frontend toolchain is installed.

## Local Image Backend

Cathode can run Qwen Image locally in two ways:

- `torch` runtime for CUDA, CPU, or MPS through Hugging Face `diffusers`
- `mlx` runtime for Apple Silicon through `mflux`

Typical CUDA / generic torch setup:

```bash
/opt/homebrew/bin/python3.10 -m pip install -r requirements-local-image.txt
export CATHODE_LOCAL_IMAGE_RUNTIME=torch
export CATHODE_LOCAL_IMAGE_MODEL=Qwen/Qwen-Image-2512
```

Typical Apple Silicon MLX setup:

```bash
uv tool install --upgrade mflux
export CATHODE_LOCAL_IMAGE_RUNTIME=mlx
export CATHODE_LOCAL_IMAGE_MODEL=Qwen/Qwen-Image-2512
export CATHODE_LOCAL_IMAGE_MLX_MODEL=mlx-community/Qwen-Image-2512-8bit
```

Auto mode keeps the single product-facing provider in the UI and picks MLX on Apple Silicon when `mflux` is installed; otherwise it falls back to the torch path.

Optional tuning:

```bash
export CATHODE_LOCAL_IMAGE_RUNTIME=auto
export CATHODE_LOCAL_IMAGE_DEVICE=auto
export CATHODE_LOCAL_IMAGE_DTYPE=auto
export CATHODE_LOCAL_IMAGE_STEPS=50
export CATHODE_LOCAL_IMAGE_TRUE_CFG_SCALE=4.0
export CATHODE_LOCAL_IMAGE_MLX_CACHE_LIMIT_GB=
export CATHODE_LOCAL_IMAGE_MLX_LOW_RAM=0
```

## Local Video Backend

Cathode keeps local video generation generic and env-driven rather than baking in one model family.

Configure one of these:

- `CATHODE_LOCAL_VIDEO_COMMAND`: Cathode runs a local command and passes scene data through env vars such as `CATHODE_VIDEO_PROMPT`, `CATHODE_VIDEO_OUTPUT_PATH`, `CATHODE_VIDEO_DURATION_SECONDS`, `CATHODE_VIDEO_MODEL`, and `CATHODE_VIDEO_REQUEST_JSON`.
- `CATHODE_LOCAL_VIDEO_ENDPOINT`: Cathode sends a JSON POST request with `prompt`, `output_path`, `duration_seconds`, `width`, `height`, `fps`, `scene`, and `brief`.

Your local backend can satisfy the request in any of these ways:

- write the clip directly to `CATHODE_VIDEO_OUTPUT_PATH` / the request `output_path`
- return JSON with `output_path`
- return JSON with `url`
- return JSON with `b64_json`

Typical setup looks like this:

```bash
CATHODE_LOCAL_VIDEO_COMMAND='python /path/to/local_video_wrapper.py'
CATHODE_LOCAL_VIDEO_MODEL=/models/wan
```

Or:

```bash
CATHODE_LOCAL_VIDEO_ENDPOINT=http://127.0.0.1:8787/generate
CATHODE_LOCAL_VIDEO_MODEL=wan2.1
```

## Quick Start

```bash
./start.sh --react
```

Legacy Streamlit path:

```bash
./start.sh
```

Manual React + FastAPI run:

```bash
/opt/homebrew/bin/python3.10 -m uvicorn server.app:app --host 127.0.0.1 --port 9321 --reload
npm run dev --prefix frontend -- --host 127.0.0.1 --port 9322
```

Manual app run:

```bash
/opt/homebrew/bin/python3.10 -m streamlit run app.py --server.port 8517
```

Default port is `8517`. Override it with `STREAMLIT_PORT` when using `./start.sh`.
React mode uses `CATHODE_API_PORT` for FastAPI (default `9321`) and `CATHODE_FRONTEND_PORT` for Vite (default `9322`).

Final render now uses direct `ffmpeg` orchestration and auto-prefers hardware H.264 encoders when the local ffmpeg build supports them. Override with `CATHODE_VIDEO_ENCODER` or force CPU fallback with `CATHODE_DISABLE_HW_ENCODER=1`.
When Remotion is available and the project resolves to `motion_only` or `hybrid`, Cathode can switch the final render backend to Remotion automatically.

## MCP Server

Cathode also ships as an MCP server.

Run over stdio:

```bash
/opt/homebrew/bin/python3.10 cathode_mcp_server.py --transport stdio
```

Run over Streamable HTTP:

```bash
CATHODE_MCP_PORT=8765 /opt/homebrew/bin/python3.10 cathode_mcp_server.py --transport streamable-http
```

Docker:

```bash
docker build -t cathode-mcp .
docker run --rm -p 8765:8765 cathode-mcp
```

Primary MCP tools:

- `make_video`
- `get_job_status`
- `cancel_job`
- `rerun_stage`
- `list_projects`

Primary MCP resources:

- `project://{project_name}/plan`
- `project://{project_name}/artifacts`

## Setup

### System Dependencies

macOS:

```bash
brew install python@3.10 ffmpeg espeak-ng
```

Ubuntu / Debian:

```bash
sudo apt-get install python3.10 ffmpeg espeak-ng
```

### Python Dependencies

```bash
/opt/homebrew/bin/python3.10 -m pip install -r requirements.txt
```

### Environment

Copy `.env.example` to `.env` and fill in only what you need.

Example:

```bash
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
REPLICATE_API_TOKEN=
ELEVENLABS_API_KEY=
DASHSCOPE_API_KEY=
ALIBABA_API_KEY=
IMAGE_EDIT_PROVIDER=
IMAGE_EDIT_MODEL=qwen/qwen-image-edit-2511
CATHODE_LOCAL_IMAGE_MODEL=
CATHODE_LOCAL_IMAGE_RUNTIME=auto
CATHODE_LOCAL_IMAGE_MLX_MODEL=mlx-community/Qwen-Image-2512-8bit
CATHODE_LOCAL_IMAGE_DEVICE=auto
CATHODE_LOCAL_IMAGE_DTYPE=auto
CATHODE_LOCAL_IMAGE_STEPS=50
CATHODE_LOCAL_IMAGE_TRUE_CFG_SCALE=4.0
CATHODE_LOCAL_IMAGE_NEGATIVE_PROMPT=
CATHODE_LOCAL_IMAGE_MLX_CACHE_LIMIT_GB=
CATHODE_LOCAL_IMAGE_MLX_LOW_RAM=0
STREAMLIT_PORT=8517
CATHODE_VIDEO_ENCODER=auto
CATHODE_DISABLE_HW_ENCODER=0
CATHODE_LOCAL_VIDEO_COMMAND=
CATHODE_LOCAL_VIDEO_ENDPOINT=
CATHODE_LOCAL_VIDEO_MODEL=
CATHODE_LOCAL_VIDEO_API_KEY=
CATHODE_LOCAL_VIDEO_TIMEOUT_SECONDS=900
```

## Workflow

### Standard Cathode Project

Every Cathode project stores:

- a normalized brief
- composition mode
- storyboard scenes
- image, clip, motion, audio, and preview paths
- render metadata
- demo-target metadata under `meta.agent_demo_profile`
- optional style references
- optional reviewed footage manifest
- persisted background job metadata and logs under `.cathode/jobs/`

`projects/<project>/plan.json` is the source of truth.

### Brief Inputs

The core brief still revolves around:

- source mode
- composition mode
- goal
- audience
- target length
- tone
- visual style
- source material
- optional footage notes
- optional demo-target context (`workspace_path`, `app_url`, `launch_command`, `expected_url`, `repo_url`, `flow_hints`)

For live demos, add reviewed `footage_paths` or `footage_manifest` instead of only prose.

### Scene Behavior

- image scenes hold for narration duration
- video scenes trim to narration duration
- short clips can freeze on the last frame to stay in sync
- motion scenes render from normalized template props through Remotion
- reviewed footage clips can be copied into `clips/` and auto-assigned to `video` scenes
- final render uses `ffmpeg` or Remotion based on the resolved render backend

## Batch Rebuild

```bash
python3.10 batch_regenerate.py
python3.10 batch_regenerate.py --projects demo_one,demo_two
python3.10 batch_regenerate.py --dry-run
```

## Tests

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.10 -m pytest -q
```

## Repository Layout

```text
app.py
batch_regenerate.py
cathode_mcp_server.py
core/
core/remotion_render.py
frontend/
server/
prompts/
skills/
tests/
docs/assets/
projects/
output/
```

## License

MIT
