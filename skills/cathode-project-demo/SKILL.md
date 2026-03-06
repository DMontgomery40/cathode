---
name: cathode-project-demo
description: Turn software repositories, README/docs, feature notes, and screen recordings into short narrated demo videos by bootstrapping or reusing Cathode and driving its local app or MCP server. Use when Codex needs to make a product demo, launch video, feature walkthrough, or developer-facing explainer from a codebase or project brief.
---

# Cathode Project Demo

Use this skill to produce a local-first demo video with Cathode. Prefer the MCP path for repeatable agent-driven runs. Use the Streamlit app when the user wants manual scene edits before the final render.

## Quick Start

1. Pick the project to showcase. If the user is already in that repo, use the current workspace as `workspace_path` instead of cloning it again.
2. Bootstrap Cathode with `scripts/bootstrap_cathode.py`. Reuse an existing Cathode checkout with `--repo-path` when available. Clone only when no usable checkout exists.
3. Start Cathode:
   - Use the returned `mcp_stdio_command` or `mcp_http_command` for agent-driven runs.
   - Use the returned `app_command` when the user wants hands-on editing in the local UI.
4. Build the brief with repo context and dev-demo defaults. Read [references/dev-demo-workflow.md](references/dev-demo-workflow.md) before composing the `make_video` request.
5. After `make_video`, poll `get_job_status`. Read `project://{project_name}/plan` or `project://{project_name}/artifacts` when you need the storyboard or generated file inventory.

## Workflow

### Bootstrap Cathode

- Run `python3 scripts/bootstrap_cathode.py --repo-path /path/to/cathode` when Cathode is already checked out locally.
- Run `python3 scripts/bootstrap_cathode.py` to clone the default Cathode repo into `~/.cache/cathode`, create `.venv`, and emit the exact commands to launch the app or MCP server.
- Treat missing `python3.10`, `ffmpeg`, or `espeak-ng` as environment blockers. The helper reports them explicitly. Surface the missing dependency rather than guessing a workaround.
- Do not mutate an explicit user checkout. Use `--update` only for the managed checkout created by the helper itself.

### Gather The Minimum Brief

- Collect the audience, the core product claim, the target runtime, the desired tone, and the ending CTA.
- Use the product repo as `workspace_path` so Cathode can inspect a bounded set of text files automatically.
- Add `source_paths` for the highest-signal files only, such as `README.md`, launch docs, `package.json`, `pyproject.toml`, or feature spec notes.
- If the target repo is not local, clone that target repo or ask for the docs you need. The skill only needs it local so Cathode can inspect bounded source excerpts.
- If the brief is still thin, let Cathode elicit the missing audience or source material instead of inventing details.

### Apply Dev-Demo Defaults

- Keep runtime in the 60-120 second range unless the user asks for a longer explainer.
- Use a direct, credible tone. Avoid marketing claims the repo cannot support.
- Default the visual style to clean product demo or editorial explainer unless the user provides stronger art direction.
- For web products, default to a 50/50 blend of narrated slides and live walkthrough unless the user clearly wants one mode to dominate.
- Use `visual_source_strategy="mixed_media"` when the user has screen recordings, product clips, or UI captures.
- Use `visual_source_strategy="images_only"` when the story is conceptual or the user has no footage yet.
- Put differentiators, workflow steps, and proof points in `must_include`. Leave implementation trivia out unless it materially changes the user story.

### Drive Cathode

Use `make_video` with an intent that states the demo goal clearly, then supply the repo path and the brief fields Cathode cannot infer safely. A typical request includes:

```json
{
  "intent": "Create a 90-second product demo video for this developer tool.",
  "workspace_path": "/abs/path/to/target-repo",
  "source_paths": [
    "/abs/path/to/target-repo/README.md",
    "/abs/path/to/target-repo/docs/launch-plan.md"
  ],
  "audience": "engineering managers evaluating tools for their team",
  "target_length_minutes": 1.5,
  "tone": "clear, technical, confident",
  "visual_style": "clean editorial product demo",
  "visual_source_strategy": "mixed_media",
  "available_footage": "Screen recordings of onboarding, dashboard, and CLI workflow.",
  "must_include": "Problem, key workflow, why it is faster than the current approach, CTA to try the repo.",
  "run_until": "render"
}
```

### Review Outputs

- Inspect the final MP4 path from job status or the project artifacts resource.
- Read `projects/<project>/plan.json` when you need to tighten scenes, narration, or prompt text.
- Use the app for surgical edits. Use `rerun_stage` when only storyboard, assets, or render needs to be refreshed.
- When the product story depends on real interactions, capture browser states or clips before the final render and keep those assets in the project plan as the walkthrough half of the video.

## Resources

- `scripts/bootstrap_cathode.py`: Prepare or reuse a Cathode checkout and emit exact launch commands.
- `references/dev-demo-workflow.md`: Repo-to-demo-video guidance, including brief defaults and an MCP request pattern.
