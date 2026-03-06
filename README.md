# local-storyboard-video

`local-storyboard-video` is a local-first Streamlit app for turning a brief, script, or rough notes into a narrated explainer video.

It is built for the practical workflow:

1. Paste source material or a final script.
2. Let the director model turn it into scenes.
3. Use AI images, uploaded stills, uploaded clips, or a mix of both.
4. Generate narration scene by scene.
5. Render an MP4 on your own machine.

The point of the repo is straightforward: keep the workflow editable, keep the files local, and let people pay only for the underlying model calls they actually want to use.

In practice, the happy path is usually very short: generate the storyboard, batch-generate the assets, render the video. The scene-by-scene editor is there when you need surgical fixes, not because the default flow should feel heavy.

## Demo Assets

- Sample walkthrough brief: `docs/demo-brief.md`
- Product demo rendered from this repo: `docs/assets/storyboard-demo.mp4`
- Sample mixed-media workflow clip: `docs/assets/ui-workflow-clip.mp4`
- Expanded scene editor screenshot: `docs/assets/scene-preview-expanded.png`

![App home](docs/assets/app-home.png)

## What The App Supports

- Three source modes:
  - `ideas_notes`: AI can create structure and wording from rough notes.
  - `source_text`: AI preserves facts while rewriting for clarity.
  - `final_script`: AI mostly segments an already-written script into scenes.
- Two visual scene types:
  - `image`: generated still or uploaded image
  - `video`: uploaded clip with trim/speed/freeze controls
- Project-level visual strategy:
  - slides only
  - mixed media
  - video preferred
- Scene-by-scene editing for narration, visual prompts, on-screen text, images, clips, audio, and preview renders
- Local MP4 assembly with MoviePy/ffmpeg

## Provider Model

The UI is intentionally env-driven instead of exposing every possible backend knob.

- LLM provider:
  - `OPENAI_API_KEY` enables OpenAI
  - `ANTHROPIC_API_KEY` enables Anthropic
- Voice provider:
  - `Kokoro` is always available locally
  - `ELEVENLABS_API_KEY` enables ElevenLabs
  - `OPENAI_API_KEY` enables OpenAI TTS
  - `REPLICATE_API_TOKEN` enables Chatterbox on Replicate
- Image generation:
  - `REPLICATE_API_TOKEN` enables built-in AI image generation with Qwen Image 2512
  - without it, the app stays in upload/local-asset mode for visuals
- Image editing:
  - Replicate-backed `qwen/qwen-image-edit-2511` is the default and recommended path in this repo right now
  - `DASHSCOPE_API_KEY` or `ALIBABA_API_KEY` adds DashScope edit options in the sidebar

Only configured providers appear in the relevant dropdowns. If you want a quieter setup, leave keys out of `.env` and the UI will stay narrower.

## Local Vs Cloud

This repo is local-first, not cloud-hosted:

- the Streamlit app runs locally
- project files live under `projects/<project>/`
- previews and final renders happen locally
- Kokoro voice is local
- uploaded stills and uploaded clips are local

Out of the box, the built-in AI image generator is cloud-backed through Replicate. If you want a fully local visual workflow today, use uploaded stills/clips and keep the rest of the pipeline on your machine.

## Image Edit Caveat

The image edit feature is more backend-constrained than the rest of the pipeline.

- Type instructions into `Refine visual prompt`
- Click `Refine Prompt` to rewrite the prompt text
- Click `Edit Image` to apply those instructions directly to the current image

This repo defaults to the Replicate-backed Qwen Image Edit path because it is the most reliable option in the current app. DashScope edit models are still available when configured, but they are not the default.

## Quick Start

```bash
./start.sh
```

Manual launch:

```bash
/opt/homebrew/bin/python3.10 -m streamlit run app.py --server.port 8517
```

Default port is `8517`. Override it with `STREAMLIT_PORT` when using `./start.sh`.

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

Copy `.env.example` to `.env` and fill in only the providers you want.

Minimum useful setups:

- OpenAI or Anthropic only: storyboard drafting only
- OpenAI/Anthropic + Replicate: full AI storyboard + image generation
- Kokoro only: local narration generation if you already have visuals and a plan

Example:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
REPLICATE_API_TOKEN=...
ELEVENLABS_API_KEY=
DASHSCOPE_API_KEY=
ALIBABA_API_KEY=
IMAGE_EDIT_PROVIDER=
IMAGE_EDIT_MODEL=qwen/qwen-image-edit-2511
STREAMLIT_PORT=8517
```

## Workflow

### Step 1: Build Project Brief

Fill in:

- project name
- source mode
- goal
- audience
- target length
- tone
- visual style
- must-include / must-avoid guidance
- source material
- optional footage notes
- optional style reference images

The app saves this to `meta.brief` inside `projects/<project>/plan.json`.

### Step 2: Edit Scenes

For each scene you can:

- edit narration
- refine narration
- edit or refine the visual prompt
- generate an AI image
- upload/replace an image
- edit an existing image
- upload a video clip instead of using a still
- generate audio
- preview the scene

### Step 3: Render

Render timing is narration-led:

- image scenes hold for narration duration
- video scenes trim to narration length
- short clips can freeze on the last frame to stay in sync

## Batch Rebuild

```bash
python3.10 batch_regenerate.py
python3.10 batch_regenerate.py --projects demo_one,demo_two
python3.10 batch_regenerate.py --dry-run
```

Batch runs respect the project’s saved `tts_profile` and `image_profile`.

## Tests

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.10 -m pytest -q
```

## Repository Layout

```text
app.py
batch_regenerate.py
core/
prompts/
tests/
projects/              # generated at runtime; not populated in the repo
output/                # scratch output; ignored
```

## License

MIT
