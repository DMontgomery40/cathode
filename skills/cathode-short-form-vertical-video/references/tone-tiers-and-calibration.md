# Tone Tiers and Calibration

Use this reference when the short needs a calibrated audience/tone lane, especially for technical, AI, software, product, or scientific subjects.

## Tier Selector

Choose exactly one tier before scripting.

- `mass-native-technical`: broad cold feed, low prior knowledge, meme-native but not cringe.
- `dev-native-credible`: developers, AI builders, technical leads, researchers, DevRel-adjacent viewers.

If the source is technical and the user does not specify a tier, default to `dev-native-credible` when the topic is a tool, workflow, benchmark, repo, agent, codebase, eval, or product demo. Default to `mass-native-technical` when the topic is a broad science, culture, media, or human curiosity hook.

## Tier 1: Mass-Native Technical

Audience: cold public feed viewers who may not know or care about the technical domain yet.

Language:

- Translate the technical point into a human-visible tension.
- Use plain nouns before technical nouns.
- One joke, POV, contradiction, or relatable failure mode is enough.
- Keep claims bounded: "shows", "flags", "makes visible", "catches a pattern".
- Avoid strings of Gen Alpha slang. A native phrase is fine; stacked slang makes the short feel fake.

Visual style:

- Native vertical, bold, readable, and slightly heightened.
- Use expressive crops, simple props, before/after frames, clean generated metaphors, or one playful visual joke.
- Prefer editorial, semi-photoreal, polished UI mockups, or tasteful stylized images over cartoon emoji explosions.

Motion:

- High but purposeful.
- Reset every 2-4 seconds with a cut, punch-in, caption pop, split screen, reaction beat, or sound cue.
- No random shake. Motion must reveal, compare, or emphasize.

Captions:

- 3-7 words per card.
- Emphasize one keyword per card.
- Captions may carry humor, but never become a transcript wall.

Forbid:

- "You won't believe", "this changes everything", fake urgency, fake shock, stale memes, bro-coded hype, or more than one meme format.
- Misrepresenting the technical result for a bigger hook.
- Cartoons, neon, emojis, or reaction faces as the default visual language.

## Tier 2: Developer/AI Native Credible

Audience: developers, AI builders, technical leads, researchers, and DevRel-adjacent viewers.

Language:

- Open with a concrete technical tension, failure mode, benchmark surprise, tradeoff, or debugging moment.
- Use compact technical nouns when useful: eval, trace, latency, schema drift, context window, RAG, tool call, false positive.
- State the evidence boundary early when relevant: prototype, toy benchmark, one repo, synthetic eval, not production proof.
- Include one takeaway a developer could test, inspect, or argue with.
- Keep humor dry and precise. Prefer "this is where it breaks" over "this is insane".

Visual style:

- Clean technical native, not corporate.
- Use readable UI, terminal, code, diffs, trace timelines, eval tables, architecture fragments, or strong conceptual diagrams.
- If generating new visuals, make them editorial/semi-photoreal or polished data/product mockups with readable negative space.
- Avoid fake dashboards, unreadable code, hallucinated metrics, decorative AI fog, and generic robots.

Motion:

- Medium-high.
- Reset every 3-5 seconds with zooms into proof, highlight boxes, trace movement, diff reveals, or short proof cuts.
- Let dense proof breathe for 1-2 seconds longer than mass-native technical.
- No shake unless it is a deliberate single emphasis beat.

Captions:

- 3-8 words per caption card.
- Do not duplicate every spoken word.
- Captions should name the technical point, not decorate it.
- Use fewer overlays when code, UI, or charts need inspection.

Forbid:

- Overclaiming AI capability, benchmark laundering, "AGI", "10x", "autonomous", "production-ready" unless directly proven.
- Hiding caveats until the end.
- Fake code, impossible terminal output, invented citations, made-up performance numbers.
- Meme formats that make the author look technically unserious.
- Marketing adjectives without proof: revolutionary, seamless, game-changing, enterprise-grade, magic.

## Voice Calibration

Preferred direction:

```text
Naturally fast presenter. Clear consonants. Confident but not shouty. Dry humor, not influencer hype. No chipmunk pitch. No autotune-like gloss. Keep pauses short but real.
```

Implementation rules:

- Prefer native fast delivery from the TTS provider over post-speeding audio.
- If a TTS provider supports speed/instructions, request fast delivery there.
- Avoid post-speeding above about 1.05x except for tiny timing fixes.
- If only basic TTS is available, shorten the script instead of forcing 1.15x or faster.
- Test at least one steadier voice when a bright voice sounds synthetic at speed.

Recommended provider order when configured:

1. Cartesia Sonic 3/3.5 for native speed/emotion controls.
2. ElevenLabs v3 or multilingual v2 for creator-style voices with careful restraint.
3. OpenAI `gpt-4o-mini-tts` with voice instructions; use `marin` or `cedar` when available, otherwise test `alloy`, `echo`, or `onyx`.
4. Kokoro/Chatterbox local fallback when cloud providers are unavailable.

## Visual and Motion Knobs

When an output is "good but too much", adjust these first:

- Slang: replace stacked slang with dry specificity.
- Image prompt: replace "chaotic", "cartoon", "emoji", "neon explosion" with "editorial", "semi-photoreal", "clean product/data mockup", "controlled color", "readable negative space".
- Motion: lower zoom depth, remove shake, and use slower pan/scale instead.
- Caption size: keep readable but reduce all-caps frequency.
- Beat count: keep the same number of beats; do not turn it into a slow explainer.

## Prompt Snippets

Mass-native visual:

```text
Vertical 9:16 native short-form asset, editorial semi-photoreal with a playful metaphor, bold readable shapes, controlled color, no logos, no watermarks, no in-image text, leave clean caption space. Energetic but not cartoonish, no emoji cloud, no neon explosion.
```

Dev-native visual:

```text
Vertical 9:16 developer-native visual asset, clean semi-photoreal/product editorial style, readable UI/data metaphor, terminal or trace-inspired elements, controlled contrast, no logos, no watermarks, no in-image text, leave clean caption space. Credible, modern, not corporate stock, not cartoon.
```

Motion:

```text
Use deliberate slow push-ins, small pans, proof-focused highlight timing, and hard cuts. Avoid shake, bounce, random zooms, and decorative kinetic clutter.
```
