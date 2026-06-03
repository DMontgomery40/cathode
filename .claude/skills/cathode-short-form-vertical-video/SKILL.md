---
name: cathode-short-form-vertical-video
description: Create or adapt betTube Studio briefs, scripts, and source-video plans for catchy 30-50 second vertical short-form videos for TikTok, Instagram Reels, YouTube Shorts, or similar feeds. Use when Claude needs a short vertical video, reel, short, TikTok-style cutdown, hook-first social clip, or a short made from existing betTube Studio source material or an uploaded video.
---

# betTube Studio Short-Form Vertical Video

This Claude-facing mirror points at the canonical betTube Studio skill resources in the repository root.

Use the canonical resources here:

- [`skills/cathode-short-form-vertical-video/SKILL.md`](../../../skills/cathode-short-form-vertical-video/SKILL.md)
- [`skills/cathode-short-form-vertical-video/references/short-form-retention.md`](../../../skills/cathode-short-form-vertical-video/references/short-form-retention.md)
- [`skills/cathode-short-form-vertical-video/references/source-video-cutdown.md`](../../../skills/cathode-short-form-vertical-video/references/source-video-cutdown.md)
- [`skills/cathode-short-form-vertical-video/references/platform-specs-and-sources.md`](../../../skills/cathode-short-form-vertical-video/references/platform-specs-and-sources.md)
- [`skills/cathode-short-form-vertical-video/references/tone-tiers-and-calibration.md`](../../../skills/cathode-short-form-vertical-video/references/tone-tiers-and-calibration.md)
- [`skills/cathode-short-form-vertical-video/references/source-loyalty-and-captions.md`](../../../skills/cathode-short-form-vertical-video/references/source-loyalty-and-captions.md)

Default workflow:

1. identify one short-form promise and audience
2. choose one tier: `mass-native-technical` or `dev-native-credible`
3. write a first-3-second hook
4. create 3-5 fast beats with captions and visual resets
5. for long explainers or public-feed requests, choose a public reframe with fresh generated visuals unless the footage itself is the proof moment
6. extract a source anchor card, prompt-lint visuals against it, and reject/regenerate assets that drift into unsupported domains, objects, workflows, or claims
7. choose a caption mode and timing path; prefer final-audio word-level timing/current-word highlight when accurate, otherwise use meaning cards or keyword labels
8. calibrate voice, visuals, and motion so energy does not come from forced slang, cartoon overload, heavy shake, or chipmunked speed
9. pay off the hook before one CTA
10. for real footage, sample frames/contact sheets before choosing the hook
11. use betTube Studio's first-class `/short-form` GUI/API surface, or set `short_form_format="vertical_short"` on Brief Studio/MCP `make_video`
