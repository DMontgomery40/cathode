---
name: bettube-studio-short-form-vertical-video
description: Create or adapt betTube Studio briefs, scripts, and source-video plans for catchy 30-50 second vertical short-form videos for TikTok, Instagram Reels, YouTube Shorts, or similar feeds. Use when the user wants a short vertical video, reel, short, TikTok-style cutdown, hook-first social clip, or a short made from existing betTube Studio source material or an uploaded video.
---

# betTube Studio Short-Form Vertical Video

Use this skill to turn source material, an existing betTube Studio video idea, or supplied footage into a 30-50 second hook-first vertical short.

Default outcome:

1. select one sharp promise
2. choose an explicit short-form tier
3. build a first-3-second hook
4. write 3-5 fast beats with visible pattern changes
5. extract a source anchor card before visual prompting
6. choose a caption mode and timing/render path
7. pay off the promise before the CTA
8. hand betTube Studio a compact short-form brief through the first-class API/GUI surface

Read [references/short-form-retention.md](references/short-form-retention.md) when writing the hook, beat structure, captions, or CTA. Read [references/source-video-cutdown.md](references/source-video-cutdown.md) when adapting an existing video. Read [references/platform-specs-and-sources.md](references/platform-specs-and-sources.md) when platform specs, safe zones, or source links matter.
Read [references/tone-tiers-and-calibration.md](references/tone-tiers-and-calibration.md) when choosing audience tier, voice direction, visual intensity, motion intensity, or when the user asks to avoid cringe, Gen Alpha slang, cartoonish visuals, shaky motion, or autotuned narration.
Read [references/source-loyalty-and-captions.md](references/source-loyalty-and-captions.md) when generating visuals from source material, reviewing generated assets, choosing whether captions are necessary, timing captions, or implementing word-level/current-word caption highlighting.

## Hard Rules

- Make one short, not a compressed full explainer. Use one subject, one curiosity gap, one payoff.
- If the source is a long explainer/demo and the user wants public-feed/TikTok-style reach, start with a public reframe and fresh short-form visual concept. Do not default to trimming the original video shorter.
- Use source footage only when it is the proof moment, a reaction, or a strong visual anchor. Otherwise generate or plan new visuals built for the hook.
- Pick one tier before scripting: `mass-native-technical` or `dev-native-credible`. Do not mix both into one short unless the user explicitly asks for variants.
- The first 1-3 seconds must answer why the viewer should care now. No greetings, channel intros, agenda-setting, or "in this video."
- Open with the strongest result, contradiction, mistake, surprising visual, before/after, emotional moment, or demonstration.
- Keep the target runtime between 30 and 50 seconds unless the user explicitly asks otherwise.
- Use 3-5 beats. Each beat must reveal evidence, raise stakes, simplify the idea, or move toward the payoff.
- Renew attention every 3-5 seconds with a visual change, caption emphasis, example, cut, zoom, sound cue, B-roll switch, or contradiction.
- Captions are required. Write meaning chunks, not full transcripts.
- Choose the caption mode deliberately: word-level highlight, meaning-card captions, keyword labels, or no captions only when justified.
- Use final narration audio as the timing source. Use automated word-level caption timing when available; hand-timed caption cards are acceptable only as a fallback and must be visually checked against the final audio.
- Do not use current-word highlighting with approximate timings. If the words lead, lag, cover proof, or distract, downgrade to phrase/meaning cards or keyword labels.
- Pay off the exact hook before asking for action. Use one CTA only.
- Do not use deceptive clickbait. Withhold the answer if useful, but never misrepresent the topic, evidence, risk, or payoff.
- Do not use forced youth slang, fake shock, or random shake/zoom effects. Energy should come from the hook, proof, cuts, captions, and visual resets.
- Do not make fast narration by heavy post-speeding. Prefer native fast delivery from the TTS model; if only basic TTS is configured, tighten the script before raising audio speed.
- Every generated visual must stay loyal to the source context. Reject/regenerate assets that introduce a different domain, use-case, object class, sport, platform, workflow, or implication not supported by the source.
- Do source-fidelity checks both before and after generation: prompt-lint every visual request against the source anchor card, then inspect the actual generated frame/contact sheet before final render.

## betTube Studio Guardrails

- Preserve betTube Studio's brief -> director -> normalized plan pipeline. Do not hand-author `projects/<project>/plan.json` to fake a short-form feature.
- Prefer the first-class short-form surfaces when available:
  - React GUI: `/short-form`
  - FastAPI: `GET /api/short-form/options`, `POST /api/short-form/preview`, `POST /api/short-form/jobs`
  - Brief Studio / MCP: set `short_form_format="vertical_short"` on the canonical brief path
- For new betTube Studio projects, encode the short-form intent in `short_form_format`, `short_form_tier`, `short_form_approach`, `short_form_duration_seconds`, `platform_targets`, `hook_promise`, `payoff`, `source_anchor_card`, `source_context_lock`, `caption_strategy`, `voice_direction`, `motion_intensity`, and the usual `video_goal`, `tone`, `visual_style`, `must_include`, `must_avoid`, and `ending_cta`.
- Use `source_mode="source_text"` for notes/facts that need rewriting, `source_mode="ideas_notes"` for rough concepts, and `source_mode="final_script"` only when the user gave a finished script.
- Use `visual_source_strategy="video_preferred"` when the user provides footage, `mixed_media` when combining footage with generated scenes, and `images_only` only for still/motion-led shorts.
- Current betTube Studio v1 render validation supports `9:16` vertical shorts at `928x1664 @ 30fps` through ffmpeg. Still verify the actual project plan/render before promising a final MP4.

## Testing From Local Footage

When the user points at a real video, run a lightweight source-video pass before claiming the skill works:

1. Inspect duration, resolution, frame rate, and audio availability.
2. Build a contact sheet or sample frames across the video.
3. Read nearby scripts, README files, or docs if the video has no transcript.
4. Extract a source anchor card: subject, domain, setting, actors/users, primary objects, workflow/action, visual anchors, supported claims, evidence boundary, allowed metaphors, and forbidden drift.
5. Decide whether this should be a literal cutdown, a mixed-media proof short, or a public reframe with fresh generated visuals.
6. Pick one standalone moment or one public-facing idea with a hook, tension, visual proof, and payoff.
7. Prompt-lint each proposed visual beat against the source anchor card before spending image/video generation.
8. Write a 30-50 second beat plan and a storyboard-only betTube Studio payload.
9. If feasible, produce a rough vertical prototype from the selected approach before spending further generation.

For scientific, medical, legal, financial, or technical evidence-heavy subjects, add an evidence-boundary beat. A catchy hook is not allowed to overclaim what the source proves.

## Public Reframe Pattern

Use this when the source material is technical, internal, long-form, or built for an audience that already cares.

1. Translate the idea into a broad human question: "what could this predict, reveal, prevent, rank, compare, or make visible?"
2. Choose one weird or emotionally legible element. Ignore the rest.
3. Write the first line for a cold viewer who has no context and does not care about the product yet.
4. Use technical nouns as flavor after the hook, not as the reason to watch.
5. Prefer fresh generated stills, motion cards, mock interfaces, exaggerated metaphors, or meme-like setups over cropped source footage.
6. Keep the evidence boundary visible: "research signal", "prototype", "shows a pattern", or "makes this inspectable" when the source does not prove more.

The decision should be explicit in the plan:

```text
Short-form approach: public reframe with fresh generated visuals
Reason: the long source video explains the whole system, but the short needs one public hook and one payoff.
Source footage role: optional proof/reference only, not the default visual spine.
```

## Brief Pattern

When calling betTube Studio, make the brief say this explicitly:

```text
Create a 30-50 second vertical short-form video. It must be hook-first, fast-paced, caption-led, and built around one clear payoff. The first 1-3 seconds should create a concrete reason to keep watching. Use 3-5 beats, visible pattern changes every 3-5 seconds, and one final CTA only after the payoff.
```

Add the subject-specific promise and constraints:

```text
Hook promise: <the specific tension/result/question>
Audience: <who is scrolling>
Payoff: <what they know, see, or feel by the end>
Must include: <proof/demo/source details>
Must avoid: generic intro, full-topic summary, misleading exaggeration, tiny unreadable text
CTA: <one action>
```

For `make_video`, a compact shape is:

```json
{
  "intent": "Create a 30-50 second hook-first vertical short from this source material.",
  "source_text": "<notes, transcript excerpt, or script>",
  "source_mode": "source_text",
  "audience": "<specific scrolling audience>",
  "short_form_format": "vertical_short",
  "short_form_tier": "mass-native-technical | dev-native-credible",
  "short_form_approach": "public-reframe | mixed-media-proof | source-cutdown",
  "short_form_duration_seconds": 42,
  "platform_targets": ["tiktok", "instagram-reels", "youtube-shorts"],
  "target_length_minutes": 0.75,
  "hook_promise": "<the specific tension/result/question>",
  "payoff": "<what they know, see, or feel by the end>",
  "tone": "fast, clear, confident, social-native",
  "voice_direction": "naturally fast presenter, clear consonants, no chipmunk pitch, no exaggerated influencer cadence",
  "visual_style": "vertical short-form, tight framing, kinetic captions, fast visual resets, tier-appropriate visual polish",
  "motion_intensity": "high but purposeful for mass-native; medium-high and inspectable for dev-native",
  "source_anchor_card": "Subject, domain, setting, actors/users, primary objects, workflow/action, visual anchors, supported claims, evidence boundary, allowed metaphors, and forbidden drift.",
  "source_context_lock": "Domain, setting, actors, objects, workflow, and claims that generated visuals must preserve.",
  "caption_strategy": "word-level highlight | meaning-card captions | keyword-only labels | no captions only when justified",
  "caption_timing_source": "Align from final narration audio after edits; do not rely on approximate line-level timing for current-word highlights.",
  "caption_renderer": "Prefer Remotion captions from word timestamps when using Remotion; otherwise use ASS/libass karaoke or phrase-card burn-in.",
  "must_include": "A first-3-second hook, 3-5 beats, captions, a payoff before the CTA.",
  "must_avoid": "Generic intro, broad summary, deceptive clickbait, more than one main idea, merely compressing the source video, generated visuals drifting away from source context, current-word captions without accurate word timing.",
  "ending_cta": "<single CTA>",
  "visual_source_strategy": "mixed_media",
  "run_until": "storyboard"
}
```

Use `run_until="storyboard"` first when testing a new short-form treatment or before spending paid image, video, or TTS calls.

## Output Checklist

Before calling the work done, verify:

- the hook is concrete and appears immediately
- the viewer can understand the topic without prior context
- the short has one main promise and payoff
- every beat has a job
- captions fit mobile safe zones and are not just raw transcript
- caption timing matches the actual audio; if word-level highlighting is used, highlighted words follow the spoken words
- caption mode is justified; bad word timing has been downgraded to phrase/meaning cards or keyword labels
- every visual prompt passed source-fidelity lint before generation
- generated visuals pass source-loyalty QC against the source context lock
- the CTA comes after value
- the tier is explicit and the language/visuals/motion match that tier
- narration sounds natively fast, not pitch-shifted or chipmunked
- any true vertical-render claim has been verified in the actual pipeline
