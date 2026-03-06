# CLAUDE.md

This file provides guidance to coding agents working in this repository.

## Project Overview

Storyboard Video Generator:
- Generic brief in Streamlit
- LLM director creates scenes in `plan.json`
- Per-scene image/clip + audio generation
- Final MP4 assembly

## Commands

```bash
# App
./start.sh

# Manual app run
/opt/homebrew/bin/python3.10 -m streamlit run app.py --server.port 8517

# Install dependencies
/opt/homebrew/bin/python3.10 -m pip install -r requirements.txt

# Batch rebuild + regenerate
python3.10 batch_regenerate.py
```

## Architecture

Core modules:
- `core/director.py`: brief-driven storyboard generation and refiners
- `core/image_gen.py`: image generation + image editing backends
- `core/voice_gen.py`: Kokoro / ElevenLabs / OpenAI TTS
- `core/video_assembly.py`: image-scene assembly to MP4
- `core/project_schema.py`: brief/plan/scene normalization and legacy backfill
- `core/workflow.py`: plan creation + storyboard rebuild helpers

Source of truth:
- `projects/<project>/plan.json`

## Data Model Highlights

`meta` defaults:
- `pipeline_mode = "generic_slides_v1"`
- `brief` (normalized)
- `render_profile` (v1 supports 16:9 at 1664x928)
- `image_profile`
- `tts_profile`

Scene defaults:
- `scene_type = "image"`
- `on_screen_text = []`

Legacy compatibility:
- Older plans with only `meta.input_text` are still supported and backfilled on load.

## Constraints

- Keep this repo use-case agnostic.
- Do not add domain-specific QC/publish dependencies.
- Provider UX is env-driven: configured backends should appear automatically without adding dashboard clutter.
- The shipped pipeline supports image scenes plus uploaded video clips in the main app.
