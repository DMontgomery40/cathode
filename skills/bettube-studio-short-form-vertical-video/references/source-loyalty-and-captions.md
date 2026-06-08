# Source Loyalty and Captions

Use this reference before final render whenever source material is being transformed into a generated-visual short or when captions are being produced.

## Gate Order

Use this order for source-driven shorts:

```text
source ingest -> source anchor card -> storyboard -> prompt source-fidelity lint -> generate visuals -> visual source QC -> caption timing from final audio -> caption QC -> final render
```

Public reframe can change the storytelling angle, but it must not change what the source is about.

## Source Anchor Card

Before generating visuals, write a compact lock:

```text
Subject:
Domain:
Setting:
Actors/users:
Primary objects:
Workflow/action:
Visual anchors:
Supported claims:
Evidence boundary:
Allowed metaphors:
Forbidden drift:
```

This is not domain-specific hardcoding. It is extracted from the current source. The generated visual prompts and QC review must preserve this lock.

Examples of drift to reject:

- object-class drift: a football workflow turns into cars, roads, drones, medical devices, crypto charts, or generic robots
- domain drift: a developer trace/eval workflow turns into consumer marketing or unrelated sci-fi
- claim drift: "research signal" becomes "diagnosis" or "proof"
- workflow drift: source review/evidence chain becomes autonomous action without inspection
- setting drift: browser/product workflow becomes unrelated hardware, dashboard, or environment

## Prompt Source-Fidelity Lint

Run this before paid image/video generation. Reject or rewrite a visual prompt when:

- it could plausibly describe a different domain than the source
- the metaphor is stronger than the source anchor and would change what viewers think the topic is about
- it adds a new industry, product, risk, platform, object class, user, metric, or claim not present in the source
- it drops every concrete source anchor and becomes generic AI stock imagery
- it implies deployment, autonomy, diagnosis, production readiness, or safety stakes not supported by the source

Each valid visual prompt should carry at least one concrete source anchor:

- setting anchor: where the source happens
- object anchor: what source objects/artifacts are visible
- workflow anchor: what action or process is happening
- interface/evidence anchor: UI, trace, chart, frame, source footage, data artifact, or proof object

Use dynamic negative constraints derived from the source anchor card:

```text
Avoid visuals that imply <unmentioned domains, object classes, settings, use cases, claims, or maturity>.
```

Do not make permanent domain-specific bans in the skill. Domain-specific avoid items belong only in the current source anchor card or scene prompt.

## Visual QC Gate

Run this gate after image generation and before final video assembly:

1. Build a contact sheet of generated visuals and a few representative final-video frames.
2. Compare every scene to the source context lock.
3. Mark each scene:
   - `pass`: source-faithful and readable
   - `minor`: acceptable metaphor, no misleading context
   - `fail`: introduces unsupported domain/object/workflow/claim
4. Regenerate any `fail` scene before final render.
5. Do not rely on prompt text as proof. Inspect the actual image.

The QC note should include:

```text
Scene:
Intended beat:
Observed visual:
Source-loyalty result:
Action:
```

When a reviewer or VLM is available, ask targeted questions instead of asking for a vague vibe check:

```text
What domain does this image appear to show?
What visible objects/actions are present?
Does it match the source anchor card?
What unsupported implication could a viewer infer?
Is this literal proof, a constrained metaphor, or decorative filler?
Should this pass, revise, or fail?
```

## Prompting for Source Loyalty

Use positive source anchors plus generic drift controls:

```text
Preserve the source context: <domain>, <setting>, <actors/users>, <primary objects>, <workflow/action>.
The scene may use a metaphor, but it must still read as <source domain/workflow>.
Avoid unrelated domains, object classes, platforms, vehicles, consumer products, medical/financial/security implications, or autonomous actions unless the source explicitly supports them.
```

Do not put a permanent domain-specific ban into the skill. Domain-specific avoid items belong only in the current brief, prompt, or scene request after the source anchor card is extracted.

## Caption Strategy

Default assumption: short-form videos need text. Captions support silent autoplay, comprehension, and retention. The question is not usually whether text exists, but how much and how precisely timed.

Captions are required when:

- narration carries the core idea
- the subject is technical, evidence-heavy, or easy to mishear
- viewers need terms, numbers, steps, code names, caveats, or proof boundaries
- the video must still work muted
- the visual alone does not explain the hook/payoff

Captions can be reduced or omitted when:

- visual action is self-explanatory
- readable UI/code/chart labels already carry the meaning
- silence, music, or reaction timing is the point
- captions would cover a proof moment or split attention from readable source footage

Choose one:

- `word-level highlight`: best for voice-led shorts where narration is the spine and word timing is accurate.
- `meaning-card captions`: best when visuals need inspection, word timing is unavailable, or timing confidence is weak.
- `keyword-only labels`: best for demos, code, charts, or dense UI where full captions would cover proof.
- `no captions`: only for music-first/visual-only cuts, self-explanatory proof footage, or when a platform/native caption layer will be added later.

If timing is weak, prefer fewer meaning-card captions over badly synced full captions.

## Preferred Caption Pipeline

1. Generate or collect final narration audio.
2. Make any silence cuts or timing edits.
3. Transcribe or align the final audio to word timestamps.
4. Group words into 1-2 line caption pages.
5. Render captions from word timestamps.
6. Visually verify in the final video.

Recommended tooling:

- WhisperX for Whisper transcription plus forced alignment when accuracy matters.
- `@remotion/captions` and `createTikTokStyleCaptions()` for programmatic caption pages/current-token rendering when using the Remotion path.
- Remotion whisper tooling or whisper.cpp when keeping transcription in the Node/Remotion ecosystem is more practical.
- ASS subtitles with karaoke tags (`\k`, `\kf`, `\ko`) when using ffmpeg/libass and deterministic burn-in.
- Auto-Subs or `pysubs2` for ASS generation, conversion, and retiming.
- Hand-authored ASS or meaning-card captions only as a fallback.

Plain SRT is not enough for current-word highlighting unless it was generated from word-level timings and the renderer still has access to those word timings.

## Word-Level Highlight Rules

- Highlight the current word or phrase, not the whole sentence.
- Keep 1-2 short lines on screen.
- Use high contrast and safe-zone margins.
- Avoid covering faces, code, charts, UI controls, or proof moments.
- If word timing confidence is poor, fall back to phrase-level or meaning-card captions.
- For developer-native shorts, keep highlighting subtle and turn it off when code, UI, charts, or caveats need inspection.

## Caption QC Gate

Before final delivery:

- Check captions are visible at phone size.
- Check no caption shows literal escape codes such as `\N`.
- Check captions do not extend after the audio ends.
- Check the strongest hook text appears in the first 1-3 seconds.
- Check captions do not obscure the proof moment.
- If using word highlighting, sample at least three points: opening hook, middle proof beat, final payoff.
