#!/usr/bin/env python3
"""Generate all text-free template background images for the clinical video deck.

Calls Qwen (qwen/qwen-image-2512) via Replicate sequentially.
Output: template_deck/backgrounds/<template_name>.png

Usage:
    /opt/homebrew/bin/python3.10 generate_template_backgrounds.py
"""

import sys
import os
import time
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from core.runtime import load_repo_env
load_repo_env()

from core.image_gen import generate_image

OUTPUT_DIR = Path(__file__).parent / "template_deck" / "backgrounds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Each entry: (filename_stem, prompt)
# All prompts explicitly request NO TEXT to prevent Qwen text leakage.
TEMPLATES = [
    # 1. Cover hook -- cinematic dark gradient, brain atmosphere
    (
        "cover_hook",
        "A rich dark navy to deep charcoal vertical gradient background with a subtle "
        "radial light bloom in the upper-center area. Faint teal accent glow at the edges. "
        "Subtle brain wave line or neural particle field in the background. "
        "Ultra-clean, premium medical-brand aesthetic. "
        "No text, no labels, no letters, no numbers, no words, no logos.",
    ),
    # 2. Orientation / roadmap -- abstract path/nodes
    (
        "orientation",
        "A dark navy background with subtle geometric shapes: softly glowing dots connected "
        "by thin luminous lines suggesting a path or roadmap flowing from top to bottom. "
        "Abstract connected nodes with slight depth-of-field blur. Modern, minimal, clean. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 3. Synthesis summary -- split/divided panels
    (
        "synthesis_summary",
        "A dark navy background divided into a subtle 2x2 grid by thin glowing teal lines. "
        "Each quadrant has a soft darker recessed panel effect. Modern medical dashboard aesthetic. "
        "No text, no icons, no data, no labels, no letters, no numbers, no words.",
    ),
    # 4. Closing CTA -- warm, forward-looking, brain glow
    (
        "closing_cta",
        "A cinematic warm-toned background with a soft-glowing abstract brain illustration "
        "emerging from golden and teal light. Depth-of-field blur creating a forward-looking, "
        "hopeful atmosphere. Rich warm amber and teal tones on dark background. "
        "No text, no labels, no letters, no numbers, no words, no logos.",
    ),
    # 5. Clinical explanation -- brain with regions
    (
        "clinical_explanation",
        "A side-view 3D human brain on a dark navy gradient background, with neural pathways "
        "and connections softly illuminated in teal and blue. Translucent, anatomical-style "
        "with distinct region boundaries visible as soft glowing areas. Medical illustration style. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 6. Metric improvement -- gauge/arc comparison
    (
        "metric_improvement",
        "Two large semicircular gauge dials side by side on a dark navy background. "
        "Left gauge dimmer with red-orange tones. Right gauge brighter with teal-green tones. "
        "Subtle connecting arrow shape between them. Soft glow effects. "
        "No needle, no numbers, no text, no labels, no letters, no words.",
    ),
    # 7. Brain region focus -- top-down brain with electrode nodes
    (
        "brain_region_focus",
        "A top-down view of a translucent 3D human brain on a dark navy background, "
        "with subtle glowing electrode nodes at standard 10-20 EEG positions. "
        "Soft teal and blue lighting. Clean medical illustration style. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 8. Metric comparison -- split/divided abstract
    (
        "metric_comparison",
        "An abstract dark navy background with a clean vertical split down the center. "
        "Left half has a subtle warm amber gradient glow. Right half has a subtle cool teal "
        "gradient glow. Thin luminous divider line in the center. Modern, minimal composition. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 9. Timeline progression -- horizontal track with nodes
    (
        "timeline_progression",
        "A horizontal glowing teal line centered on a dark navy background, running left to "
        "right with 5 subtle circular milestone nodes along it. Soft radial glow around each node. "
        "Clean timeline aesthetic with depth. "
        "No text, no dates, no labels, no letters, no numbers, no words.",
    ),
    # 10. Analogy: porch light at dusk
    (
        "analogy_porch_light",
        "A warm golden porch light glowing on the front of a peaceful house at blue-hour dusk. "
        "Soft bokeh in the background garden. Warm amber light contrasting with cool blue "
        "twilight sky. Photorealistic, serene mood. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 11. Analogy: orchestra conductor
    (
        "analogy_orchestra",
        "A silhouette of an orchestra conductor with raised baton, backlit by warm stage "
        "lighting on a dark background. Soft bokeh of orchestra lights in the background. "
        "Dramatic, elegant mood. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 12. Analogy: rowing crew (synchrony)
    (
        "analogy_rowing",
        "An aerial view of a rowing crew of eight in perfect synchrony on calm dark water "
        "at dawn. Soft golden light reflecting on the water surface. The boat leaves a clean wake. "
        "No text, no labels, no letters, no numbers, no words, no logos.",
    ),
    # 13. Analogy: fog lifting (clarity)
    (
        "analogy_fog_lifting",
        "A mountain valley at sunrise with morning fog visibly lifting and dissolving. "
        "Warm golden sunlight breaking through from the right. Transition from misty gray-blue "
        "at bottom to clear sky at top. Photorealistic landscape. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 14. Analogy: balance scale
    (
        "analogy_balance_scale",
        "An elegant brass balance scale in perfect equilibrium on a dark navy background "
        "with soft directional lighting. One side glows with warm amber, the other with cool teal. "
        "Minimal, symbolic composition. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 15. Analogy: traffic intersection (attention)
    (
        "analogy_traffic",
        "An aerial night view of a well-organized city intersection with cars flowing smoothly "
        "through green lights. Teal and amber light trails from vehicle headlights and taillights. "
        "Clean urban geometry. "
        "No text, no signs, no labels, no letters, no numbers, no words.",
    ),
    # 16. Neural network abstract (general-purpose)
    (
        "neural_network_abstract",
        "An abstract network of softly glowing teal nodes connected by thin luminous lines "
        "on a dark navy background. Nodes vary in size and brightness, suggesting a neural network. "
        "Depth of field blur on distant nodes. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # 17. Subtle topographic contour (utility fallback)
    (
        "utility_contour",
        "A dark navy background with very subtle topographic contour lines in slightly lighter "
        "navy-gray, creating depth and texture without competing with overlaid content. "
        "Modern, technical, minimal. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
]


def main():
    total = len(TEMPLATES)
    print(f"Generating {total} template background images...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    successes = []
    failures = []

    for i, (name, prompt) in enumerate(TEMPLATES, 1):
        output_path = OUTPUT_DIR / f"{name}.png"
        if output_path.exists():
            print(f"[{i}/{total}] SKIP {name} (already exists)")
            successes.append(name)
            continue

        print(f"[{i}/{total}] Generating {name}...")
        t0 = time.time()
        try:
            generate_image(
                prompt=prompt,
                output_path=output_path,
                apply_style=False,  # no style suffix, we control the full prompt
                seed=42 + i,  # deterministic seeds for reproducibility
            )
            elapsed = time.time() - t0
            size_kb = output_path.stat().st_size / 1024
            print(f"         OK  {elapsed:.1f}s  {size_kb:.0f}KB  -> {output_path.name}")
            successes.append(name)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"         FAIL  {elapsed:.1f}s  {type(e).__name__}: {e}")
            failures.append((name, str(e)))

    print()
    print(f"Done: {len(successes)} succeeded, {len(failures)} failed out of {total}")
    if failures:
        print("Failures:")
        for name, err in failures:
            print(f"  - {name}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
