# Source-Video Cutdown Workflow

Use this reference when the user provides an existing video, transcript, long-form script, demo recording, or betTube Studio project and wants a short.

## Principle

Do not summarize the whole video. Find one self-contained moment with a hook, tension, and payoff, then reframe it as a standalone short.

If the user wants a public TikTok/Reels/Shorts style output from a technical or long-form explainer, do not assume the deliverable is a shorter edit of the source. First choose between:

- `literal cutdown`: source footage is already exciting, readable on mobile, and contains the payoff
- `mixed-media proof short`: source footage proves one beat, but new visuals/captions carry the story
- `public reframe`: the short is rebuilt around one broad-audience curiosity hook with fresh generated visuals

For public reframe, the source video is research/input, not the visual spine.

## Transcript-Free Local Test

If there is no transcript or LLM runtime:

1. Use `ffmpeg` or the available media toolchain to inspect duration, resolution, frame rate, and audio streams.
2. Generate a contact sheet at a steady interval such as one frame every 30-60 seconds.
3. Inspect the contact sheet for proof moments, visual anomalies, strong text cards, before/after changes, charts, product states, or evaluation/result screens.
4. Read nearby repo docs or scripts for factual grounding.
5. Decide whether the right output is literal cutdown, mixed-media proof short, or public reframe.
6. Select one candidate and write the beat plan before rendering or spending on generation.

The test artifact should record:

```text
Source path:
Duration/resolution:
Contact sheet path:
Short-form approach:
Selected timestamp or visual moment:
Hook:
Beat plan:
Risks:
Skill changes needed:
```

## Selection Pass

Scan the source for:

- strongest quote
- surprising result
- visible transformation
- before/after gap
- mistake or misconception
- emotional reaction
- proof moment
- demo moment
- one actionable step
- conflict or decision point
- visual anomaly

Reject segments that require too much setup, rely on inside context, or cannot pay off within 30-50 seconds.

For technical or scientific subjects, also scan for the evidence boundary: the point where a claim becomes unsupported, experimental, or narrower than a catchy hook might imply. Put that boundary in the short instead of burying it.

## Segment Shape

For each candidate, capture:

```text
Candidate title:
Source timestamp or excerpt:
Hook type:
Viewer promise:
Why it is standalone:
Required context:
Payoff:
Visual proof:
CTA:
Risk:
```

Pick the candidate with the clearest promise and least required context.

If all candidates need heavy setup or look like a compressed lecture, switch to public reframe: extract one weird result, one analogy, and one evidence boundary, then design fresh visuals specifically for that short.

## Rewrite Pass

1. Cut the original setup.
2. Rewrite the first line so it works without prior context.
3. Preserve any factual claim from the source.
4. Add only the minimum bridge context.
5. Bring the best source moment earlier.
6. End after the payoff instead of trailing into the next topic.
7. Add a CTA to the full video only after the short stands alone.

## Footage Plan

When footage is available:

- prefer source video where it proves the claim
- crop for a 9:16 composition when a vertical render path exists
- keep the speaker, action, cursor, product state, or proof centered
- avoid tiny desktop UI unless zoomed or reframed
- use text callouts to explain what the viewer should notice
- preserve useful original audio when it carries authenticity
- use voiceover when the source audio is noisy, slow, or context-heavy

## betTube Studio Handoff

Use `footage_paths` or `footage_manifest` for supplied clips. Add clip notes that tell the director why each clip matters.

Example note:

```text
Use this clip as proof of the payoff: it shows the before/after transition from the slow workflow to the finished result. Crop or zoom to keep the action readable on mobile.
```

Use `visual_source_strategy="video_preferred"` when the source clip should anchor the short. Use `mixed_media` when source footage only supports some beats.

## Review Questions

- Would this still make sense if the viewer never sees the long video?
- Does the first frame create a reason to stop scrolling?
- Is there exactly one promised payoff?
- Is the best source moment in the first half?
- Does any caption explain what the viewer should notice?
- Could the same idea be cut by 10 seconds without losing meaning?
