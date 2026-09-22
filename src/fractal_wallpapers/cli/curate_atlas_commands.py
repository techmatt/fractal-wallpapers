"""`curate atlas`: every kept place as a dot on a plate of its plane, for the website to ingest.

One step with no verbs. It reads the candidate ledger, the fine head's pool scores and a
named record, thins the qualifying places to dots, writes the record the website's
`builder atlas --ingest` reads, and draws the plate and three thumbnails a dot.
[`curation.atlas`] is the whole of it and its README says what the directory holds.
"""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import display_path, resolve_output


def curate_atlas(args: argparse.Namespace) -> int:
    """Make one plane's atlas: the record first, then the pictures it names."""
    from fractal_wallpapers.curation import atlas, tentative

    out = resolve_output(args.out) if args.out else None
    try:
        summary = atlas.make(
            plane=args.plane,
            record=args.record,
            radius_px=args.radius,
            out=out,
            pictures=not args.no_pictures,
        )
    except (atlas.AtlasRefused, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    print(json.dumps(summary, indent=2))
    where = out if out is not None else atlas.default_out(args.plane)
    print(f"{display_path(where / atlas.DOTS_NAME)} — what `builder atlas --ingest` reads")
    failed = (summary.get("thumbs") or {}).get("failed", 0)
    return 1 if failed else 0


def add_steps(steps) -> None:
    """The atlas maker."""
    from fractal_wallpapers.curation import atlas as atlas_module

    making = steps.add_parser(
        "atlas",
        help="every kept place as a dot on its plane's plate, with three thumbnails a dot",
        description=(
            "A place is on the atlas when at least one of its rows reads at or above the solve's "
            "fine bar. Seated places are queued first, then the rest by best fine score, and a "
            "place inside the absorption radius of a dot already standing is dropped. Writes "
            "dots.json, the plate and the thumbnails under artifacts/atlas/<plane>/, which is "
            "what the website's `builder atlas --ingest` reads. Holds the candidate pool while "
            "it reads, so it never runs beside a solve, a growth pass or the slow lane."
        ),
    )
    making.set_defaults(handler=curate_atlas)
    making.add_argument(
        "--record",
        default=None,
        help="the tentative record whose seats are placed first (default: the newest "
        "published one). Named rather than guessed where it matters: an unpublished record "
        "is reached only by its stamp — and while none is published, NAME ONE: the default "
        "refuses and says so.",
    )
    making.add_argument(
        "--plane",
        choices=sorted(atlas_module.PLANES),
        default="mandelbrot",
        help="the plane the plate draws and whose places are dotted (default: mandelbrot). "
        "The multibrot and phoenix planes are the same code with a different home view and "
        "join the table when the search has places on them.",
    )
    making.add_argument(
        "--radius",
        type=float,
        default=atlas_module.RADIUS_PX,
        help=f"the absorption radius in plate pixels (default {atlas_module.RADIUS_PX:g}). "
        f"The plate is {atlas_module.PLATE[0]}x{atlas_module.PLATE[1]}.",
    )
    making.add_argument(
        "--out",
        default=None,
        help="the directory to write (default: artifacts/atlas/<plane>).",
    )
    making.add_argument(
        "--no-pictures",
        action="store_true",
        help="write dots.json and stop: no plate and no thumbnails. For checking a thinning "
        "without spending the ninety seconds the pictures cost.",
    )
