# Core Agent Rules

- Remotion is the deterministic manifestation layer for scenes that Claude dreams up.
- The planner owns deterministic mapping. Claude should express creative intent; core code should translate that into canonical `scene.composition`, `scene.motion`, overlays, transitions, and manifests.
- Keep the model-facing scene contract thin. Prefer `scene_type`, `speaker_name`, `on_screen_text`, `staging_notes`, `data_points`, and `transition_hint` over nested renderer mini-schemas.
- Continue reading legacy composition-hint fields from existing plans for compatibility, but do not make new prompt behavior depend on them.
- Preserve the raw-brief one-click flow. Director, workflow, planner, and render changes must keep the traced `pitch`-style path intact.
- Voice continuity is part of the product contract. Do not break the automatic speaker-to-voice planning behavior that turns recurring `speaker_name` values into stable scene-level overrides.
- Clip-audio video scenes are not narration-audio scenes. If a generated clip supplies final audio, keep reference audio separate from `audio_path` and do not let stale narration files influence timing or readiness.
- Paid-cost estimation and actual-cost recording belong in shared core helpers, not scattered per-route guesses. The system should be route-aware, provider-aware, and reusable across background jobs and scene endpoints.
- When adding new deterministic scene behaviors, prove them through planner normalization plus manifest/preview coverage instead of prose-only prompt tests.
