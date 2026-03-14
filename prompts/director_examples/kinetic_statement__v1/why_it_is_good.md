# Why It Works

A genuinely excellent kinetic statement piece with strong directing instincts, clear narrative architecture, and a luxury motion aesthetic that matches the brief precisely. The triptych structure (Fast / Repeatable / Saleable) is well-staged and the bookend technique (opening obsidian sweep closing the bracket at Scene 11) shows real directorial craft. Some staging notes request renderer behaviors (echoing ghosts, self-drawing underlines, waveform animations) that Cathode's deterministic layer cannot reliably execute without brittle custom Remotion code — this is the primary weakness.

## Strengths
- Narrative arc is complete and purposeful: invisible labor → tuned system → triptych of outcomes → proof → sell the work → reward
- Bookend visual motif (obsidian light sweep) is explicitly called out and intentionally varied on return, giving the planner a clear compositional rule to follow
- Triptych scenes (3-4-5-6) demonstrate best practice: solo kinetic beats followed by synthesis scene with all three words together and a connecting rule
- on_screen_text is populated in every scene with exact copy, making deterministic overlay straightforward
- transition_hint alternates fade/wipe with narrative logic rather than arbitrarily
- data_points field used appropriately in Scene 8 to anchor the three proof statements separately from on_screen_text
- Typographic contrast instructions (lighter gray first line, heavier white/gold second line) give the renderer concrete weight-class cues
- Palette shift — cool blue-charcoal opening warming to amber-gold at Scene 2 climax — is described as a deliberate narrative beat, useful for image generation prompts
- Narration is tight and voiceover-ready; single-sentence or near-single-sentence beats throughout
- Scene 3 ('Fast.') explicitly references 'luxury automotive film' as a style anchor, grounding the motion intent without fabricating renderer instructions

## Prompting Notes
- Teach: bookend visual motif — explicitly reuse opening visual language in closing scene with a described variation (slower, more settled) to signal narrative resolution
- Teach: triptych pattern — solo kinetic word scenes followed immediately by synthesis scene showing all three together with a unifying graphic element
- Teach: populate both data_points AND on_screen_text when the content serves dual roles (proof statement + display text)
- Teach: describe palette transitions as narrative beats ('warm gold cuts into cool palette for the first time') so the planner can sequence image prompts accordingly
- Teach: reference a real-world motion genre or film style ('luxury automotive title card') as a style anchor in staging_notes rather than a fabricated renderer instruction
- Warn: self-drawing SVG paths (underlines, connecting rules) and ghost/echo opacity stacks should be flagged as custom Remotion work, not assumed as standard surfaces
- Warn: animated generative graphics (waveforms settling, shapes compounding) need asset_id references or should be simplified to static image prompts the planner can source
- Improve: set video_scene_kind to 'kinetic_text' or 'title_card' for motion_only scenes so the planner can route to correct scene templates
- Improve: add approximate duration in seconds per scene (e.g. '~4s') in staging_notes or a dedicated field so 45-second pacing can be verified arithmetically
- Improve: populate composition_intent with layout descriptor ('center-dominant', 'left-aligned triptych') rather than leaving null
