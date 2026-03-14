#!/usr/bin/env python3
"""Harvest, judge, preview, and optionally promote Cathode director examples."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.director_golden import harvest_scenario, materialize_run, promote_example


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_ids", nargs="+", help="Scenario ids from prompts/director_example_scenarios/")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Anthropic model to use")
    parser.add_argument("--skip-judge", action="store_true", help="Skip the Anthropic judge pass")
    parser.add_argument("--skip-preview", action="store_true", help="Skip Remotion preview rendering")
    parser.add_argument(
        "--promote",
        nargs=3,
        metavar=("RUN_DIR", "EXAMPLE_ID", "TITLE"),
        help="Promote a completed run dir into prompts/director_examples/",
    )
    parser.add_argument(
        "--materialize-run",
        metavar="RUN_DIR",
        help="Turn a harvested run into a real mini project with generated assets and a short rendered video.",
    )
    parser.add_argument("--scene-count", type=int, default=3, help="How many scenes to include in a materialized mini project")
    parser.add_argument(
        "--intents",
        default="",
        help="Comma-separated intents for promotion, for example: multi_voice_pitch,kinetic_statement",
    )
    args = parser.parse_args()

    if args.promote:
        run_dir, example_id, title = args.promote
        intents = [value.strip() for value in args.intents.split(",") if value.strip()]
        promote_example(
            run_dir=Path(run_dir),
            example_id=example_id,
            title=title,
            intents=intents,
        )
        return

    if args.materialize_run:
        materialize_run(
            run_dir=Path(args.materialize_run),
            scene_count=args.scene_count,
        )
        return

    for scenario_id in args.scenario_ids:
        result = harvest_scenario(
            scenario_id=scenario_id,
            model=args.model,
            judge=not args.skip_judge,
            render_preview=not args.skip_preview,
        )
        print(f"{scenario_id}: {result['run_dir']}")


if __name__ == "__main__":
    main()
