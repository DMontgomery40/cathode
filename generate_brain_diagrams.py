#!/usr/bin/env python3
"""Generate brain electrode diagrams from every viewing angle with labeled nodes.

These are proper EEG 10-20 system reference diagrams with electrode labels,
connecting arrows, and region indicators. Short labels (F3, Cz, Pz) are
in Qwen's reliable range.

Usage:
    /opt/homebrew/bin/python3.10 generate_brain_diagrams.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.runtime import load_repo_env
load_repo_env()

from core.image_gen import generate_image

OUTPUT_DIR = Path(__file__).parent / "template_deck" / "backgrounds" / "brain_diagrams"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = [
    # ── TRUE TOP-DOWN (aerial view, looking straight down at crown) ──
    (
        "topdown_10_20_full",
        "A medical diagram of the EEG 10-20 electrode system viewed from directly above "
        "the top of the head. The outline of the skull is a circle. Electrode positions are "
        "shown as small glowing teal dots with short labels: Fp1, Fp2 at the front, "
        "F3, Fz, F4 in the frontal row, C3, Cz, C4 in the central row, "
        "P3, Pz, P4 in the parietal row, O1, O2 at the back, T3, T4 on the sides. "
        "Thin luminous lines connect neighboring electrodes. The nose indicator points up. "
        "Dark navy background. Clean medical diagram style with soft teal glow on nodes. "
        "White text labels next to each dot.",
    ),
    (
        "topdown_frontal_highlight",
        "A medical diagram of the EEG 10-20 electrode system viewed from directly above "
        "the top of the head. Circular skull outline on dark navy background. "
        "The frontal electrodes Fp1, Fp2, F3, Fz, F4 are highlighted with bright amber-gold "
        "glowing dots and labels. All other electrodes (C3, Cz, C4, P3, Pz, P4, O1, O2, T3, T4) "
        "shown as dimmer teal dots with labels. Thin connecting lines between neighbors. "
        "Nose indicator at top. White text labels. Arrow pointing to frontal region labeled "
        "'Frontal Lobe'. Clean medical diagram.",
    ),
    (
        "topdown_central_highlight",
        "A medical diagram of the EEG 10-20 electrode system viewed from directly above "
        "the top of the head. Circular skull outline on dark navy background. "
        "The central electrodes C3, Cz, C4 are highlighted with bright amber-gold "
        "glowing dots and labels. All other electrodes shown as dimmer teal dots with labels. "
        "Thin connecting lines between neighbors. Nose indicator at top. "
        "White text labels. Arrow pointing to central region labeled 'Sensorimotor'. "
        "Clean medical diagram.",
    ),
    (
        "topdown_parietal_occipital_highlight",
        "A medical diagram of the EEG 10-20 electrode system viewed from directly above "
        "the top of the head. Circular skull outline on dark navy background. "
        "The posterior electrodes P3, Pz, P4, O1, O2 are highlighted with bright amber-gold "
        "glowing dots and labels. All other electrodes shown as dimmer teal dots with labels. "
        "Thin connecting lines between neighbors. Nose indicator at top. "
        "White text labels. Arrow pointing to back region labeled 'Parietal-Occipital'. "
        "Clean medical diagram.",
    ),
    (
        "topdown_temporal_highlight",
        "A medical diagram of the EEG 10-20 electrode system viewed from directly above "
        "the top of the head. Circular skull outline on dark navy background. "
        "The temporal electrodes T3, T4, T5, T6 are highlighted with bright amber-gold "
        "glowing dots and labels. All other electrodes shown as dimmer teal dots with labels. "
        "Thin connecting lines between neighbors. Nose indicator at top. "
        "White text labels. Arrows pointing to left and right sides labeled 'Temporal'. "
        "Clean medical diagram.",
    ),

    # ── LEFT LATERAL (side view, left hemisphere) ──
    (
        "lateral_left_full",
        "A left-side view of a translucent 3D human brain on dark navy background showing "
        "EEG electrode positions. Labeled glowing dots at: Fp1 (front top), F3 (upper front), "
        "F7 (front temple), C3 (top center), T3 (temple), P3 (upper back), T5 (lower back temple), "
        "O1 (back). Thin luminous lines connecting neighboring electrodes. White text labels "
        "next to each electrode dot. Arrows showing anterior-to-posterior flow along the cortex. "
        "Clean medical illustration style with soft teal and blue glow.",
    ),
    (
        "lateral_left_frontal_highlight",
        "A left-side view of a translucent 3D human brain on dark navy background. "
        "Frontal electrodes Fp1, F3, F7 are bright amber-gold glowing dots with white labels. "
        "Other electrodes (C3, T3, P3, T5, O1) are dimmer teal dots with labels. "
        "A translucent amber highlight covers the prefrontal cortex region. "
        "Thin connecting lines between electrodes. Arrow pointing to frontal lobe. "
        "Clean medical illustration.",
    ),

    # ── RIGHT LATERAL (side view, right hemisphere) ──
    (
        "lateral_right_full",
        "A right-side view of a translucent 3D human brain on dark navy background showing "
        "EEG electrode positions. Labeled glowing dots at: Fp2 (front top), F4 (upper front), "
        "F8 (front temple), C4 (top center), T4 (temple), P4 (upper back), T6 (lower back temple), "
        "O2 (back). Thin luminous lines connecting neighboring electrodes. White text labels "
        "next to each electrode dot. Arrows showing anterior-to-posterior flow along the cortex. "
        "Clean medical illustration style with soft teal and blue glow.",
    ),

    # ── FRONTAL (front-facing view) ──
    (
        "frontal_full",
        "A front-facing view of a translucent 3D human brain on dark navy background showing "
        "EEG electrode positions from the front. Labeled glowing dots visible: Fp1 and Fp2 at "
        "the top front, F3 and F4 below them, F7 and F8 at the temples, Fz at center top. "
        "Both hemispheres visible symmetrically. Thin luminous lines connecting electrodes. "
        "White text labels next to each dot. Clean medical illustration with soft teal glow.",
    ),
    (
        "frontal_asymmetry",
        "A front-facing view of a translucent 3D human brain on dark navy background. "
        "Left hemisphere electrodes (Fp1, F3, F7) glow amber-orange. "
        "Right hemisphere electrodes (Fp2, F4, F8) glow teal-blue. "
        "White text labels next to each electrode. A double-headed arrow between hemispheres "
        "labeled 'Asymmetry'. Thin connecting lines. Both hemispheres visible. "
        "Clean medical illustration showing left-right comparison.",
    ),

    # ── POSTERIOR (back view) ──
    (
        "posterior_full",
        "A back-of-head view of a translucent 3D human brain on dark navy background showing "
        "EEG electrode positions from behind. Labeled glowing dots visible: O1 and O2 at the "
        "occipital region, P3 and P4 above them, Pz at center, T5 and T6 at the temporal-occipital "
        "junction. Thin luminous lines connecting electrodes. White text labels next to each dot. "
        "Clean medical illustration with soft teal glow.",
    ),

    # ── CONNECTIVITY DIAGRAMS (arrows between regions) ──
    (
        "connectivity_coherence",
        "A top-down EEG electrode diagram on dark navy background showing brain connectivity. "
        "Electrode dots labeled Fp1, Fp2, F3, Fz, F4, C3, Cz, C4, P3, Pz, P4, O1, O2. "
        "Thick glowing teal arrows connecting F3-C3, F4-C4, Cz-Pz showing strong coherence. "
        "Thinner dimmer amber arrows connecting T3-T4, Fp1-Fp2 showing weaker coherence. "
        "Arrow thickness indicates connection strength. White text labels on electrodes. "
        "Clean medical diagram style.",
    ),
    (
        "connectivity_alpha_flow",
        "A top-down EEG electrode diagram on dark navy background showing alpha wave propagation. "
        "Electrode dots labeled with standard 10-20 positions. "
        "Glowing teal wave-like arrows flowing from O1, O2 (occipital, back) forward through "
        "P3, Pz, P4 toward C3, Cz, C4, showing posterior-to-anterior alpha rhythm propagation. "
        "Arrow direction indicates flow. Occipital region glows brightest. "
        "White text labels. Clean medical diagram.",
    ),
]


def main():
    total = len(TEMPLATES)
    print(f"Generating {total} brain diagram images...")
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
                apply_style=False,
                seed=200 + i,
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
