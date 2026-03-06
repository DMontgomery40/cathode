# Repository Agents (local-storyboard-video)

This file is for AI agents working in this repo.

## Start Here

1. Read `CLAUDE.md` for architecture and constraints.
2. `projects/<project>/plan.json` is the source of truth.
3. Keep pipeline behavior generic. Do not add domain-specific assumptions.

## Pipeline Contract

- Input: brief-driven storyboard generation.
- Source modes:
  - `ideas_notes`: director can create structure and wording
  - `source_text`: preserve facts while restructuring
  - `final_script`: minimal rewrite, mostly segmentation
- Scene type support in the shipped app:
  - `image`: generated still or uploaded image
  - `video`: uploaded clip with narration-aware trim/freeze behavior

## Image Actions (not interchangeable)

- **Generate/Regenerate Image**: new image from prompt via image generation model
- **Edit Image**: surgical edits to existing image
- **Refine Prompt**: LLM rewrites prompt text

## Important Defaults

- `meta.pipeline_mode = "generic_slides_v1"`
- `meta.render_profile`: 16:9, 1664x928, 24fps default
- `meta.image_profile`: persisted image provider defaults
- `meta.tts_profile`: persisted voice defaults
- Backfill legacy plans at load time; do not require one-time migrations.

## Quick Commands

- Run app: `./start.sh`
- Manual run: `/opt/homebrew/bin/python3.10 -m streamlit run app.py`
- Batch rebuild: `python3.10 batch_regenerate.py`

## Environment Variables

- `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` (director + refiners)
- `REPLICATE_API_TOKEN` (Qwen image generation, Replicate image edit, Chatterbox voice)
- `ELEVENLABS_API_KEY` (optional ElevenLabs TTS)
- `DASHSCOPE_API_KEY` or `ALIBABA_API_KEY` (optional DashScope image edit)

Provider UX:
- Keep provider selection env-driven. Only surface providers in the UI when they are actually configured.
- Preserve the local/manual visual workflow when cloud image generation is unavailable.

## Guardrails

- Keep prompts domain-agnostic.
- Keep docs and UI labels domain-agnostic.
- Do not introduce QC/publish flows tied to external systems in this fork.
