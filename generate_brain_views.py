#!/usr/bin/env python3
"""Generate brain background images from top-down and frontal views.

The first batch generated only lateral (side) views. These are the missing angles
needed for electrode mapping and clinical explanation slides.

Usage:
    /opt/homebrew/bin/python3.10 generate_brain_views.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.runtime import load_repo_env
load_repo_env()

from core.image_gen import generate_image

OUTPUT_DIR = Path(__file__).parent / "template_deck" / "backgrounds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = [
    # Top-down brain for electrode mapping (10-20 system)
    (
        "brain_region_focus_topdown",
        "A top-down view looking straight down at a translucent 3D human brain on a dark navy "
        "background. The brain is viewed from directly above, showing both hemispheres symmetrically. "
        "Subtle glowing nodes at standard EEG electrode positions: two at the front (frontal), "
        "two in the middle (central), two at the back (parietal/occipital), and one on each side "
        "(temporal). Soft teal and blue bioluminescent lighting. Clean medical illustration style. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # Frontal brain view
    (
        "brain_region_focus_frontal",
        "A front-facing view of a translucent 3D human brain on a dark navy background, "
        "looking straight at the frontal lobes. Both hemispheres visible symmetrically. "
        "The prefrontal cortex glows softly in teal-blue. Subtle electrode nodes visible on "
        "the surface. Clean, medical illustration style with soft volumetric lighting. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # Clinical explanation with frontal brain view
    (
        "clinical_explanation_frontal",
        "A front-facing view of a translucent 3D human brain on a dark navy gradient background, "
        "with neural pathways and synaptic connections softly illuminated in teal, blue, and gold. "
        "The brain faces the viewer directly showing both hemispheres. Anatomical illustration style "
        "with distinct region boundaries visible as soft glowing areas. "
        "No text, no labels, no letters, no numbers, no words.",
    ),
    # Top-down brain with activity heatmap style
    (
        "brain_region_focus_heatmap",
        "A top-down aerial view looking straight down at a 3D human brain on a dark navy background. "
        "The brain surface shows a heat map gradient of neural activity: cool blue in some regions, "
        "warm amber-orange in others, bright teal-green in active areas. Both hemispheres visible "
        "symmetrically from directly above. Medical neuroimaging visualization style. "
        "No text, no labels, no letters, no numbers, no words, no color bars.",
    ),
]


def main():
    total = len(TEMPLATES)
    print(f"Generating {total} brain view images...")
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
                apply_style=False,
                seed=100 + i,
            )
            elapsed = time.time() - t0
            size_kb = output_path.stat().st_size / 1024
            print(f"         OK  {elapsed:.1f}s  {size_kb:.0f}KB  -> {output_path.name}")
            successes.append(name)
        except Exception as e:
            elapsed = time.time() - t0
            print(f"         FAIL  {elapsed:.1f}s  {type(e).__name__}: {e}")
            failures.append((name, str(e)))

    print(f"\nDone: {len(successes)} succeeded, {len(failures)} failed out of {total}")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
