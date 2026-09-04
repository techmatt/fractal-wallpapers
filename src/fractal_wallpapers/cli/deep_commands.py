"""`deep`: the run mode for the release-stock tail."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    build_scorer,
    display_path,
    resolve_output,
    scoring_flags,
)


def deep_roots(args: argparse.Namespace) -> int:
    """Fill the seats and print them, standing on none of them."""
    import random

    from fractal_wallpapers.deep import roots as roots_module
    from fractal_wallpapers.deep import run as deep_module

    seats, sourcing = roots_module.sourced(
        deep_module.DEFAULT_SEATS if args.seats is None else args.seats,
        random.Random(args.seed),
        newton_share=args.newton_share,
        anchors_per_family=args.anchors,
    )
    if args.out:
        path = resolve_output(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for seat in seats:
                handle.write(json.dumps(seat.record(), ensure_ascii=False) + "\n")
        print(f"{len(seats)} seat(s) -> {display_path(path)}")
    print(json.dumps({"seats": [seat.record() for seat in seats], "sourcing": sourcing}, indent=2))
    return 0 if seats else 1


def deep_walk(args: argparse.Namespace) -> int:
    """Source the seats, stand on them, and record everything that is seen."""
    from fractal_wallpapers.deep import run as deep_module

    limits = deep_module.Limits(
        # `seats` and `batches` stay `None` unless a flag said otherwise, which
        # is what lets the wall budget size them. A default filled in here would
        # out-rank the projection with a number nobody chose.
        seats=args.seats,
        newton_share=args.newton_share,
        anchors_per_family=deep_anchor_pool(args),
        batch=args.batch,
        batches=args.batches,
        root_expansions=args.root_expansions,
        lineage_admissions=args.lineage_cap if args.lineage_cap > 0 else None,
    )
    if args.reseat is not None:
        limits.reseat = bool(args.reseat)
    run = deep_module.Deep(
        out_dir=resolve_output(args.out_dir),
        seed=args.seed,
        limits=limits,
        wall_budget=args.wall_budget,
        evaluation_reserve=not args.no_evaluation_reserve,
        scorer=build_scorer(args),
        colormap=args.colormap,
        node_width=args.node_width,
    )
    if run.projection is not None:
        print(json.dumps({"projection": run.projection.record()}, indent=2))
        if run.seats_wanted < 1:
            print(
                f"the budget affords no seat: {args.wall_budget:.0f}s leaves "
                f"{run.projection.room:.0f}s usable against {run.projection.per_seat:.0f}s a seat"
            )
            return 1
    if not run.source():
        print("no seats: neither channel produced a nucleus this mode can frame")
        return 1
    print(json.dumps(run.run(), indent=2))
    return 0


def deep_anchor_pool(args: argparse.Namespace) -> int:
    """Anchors per family the Newton channel may draw on for this whole run.

    `--anchors` is a floor rather than the answer when a budget is in play. The
    flag's default is eight, which is 32 anchors over the four parameter planes;
    a projection at eight hours asks for a few hundred descents and would run the
    queues dry in its first round. So a budgeted run raises the pool to what its
    own projection needs, at `deep_run1`'s measured arrival rate, and the flag
    still wins whenever it is set higher.
    """
    import math

    from fractal_wallpapers.deep import budget as budget_module
    from fractal_wallpapers.deep import roots as roots_module
    from fractal_wallpapers.deep import run as deep_module

    if args.wall_budget is None:
        return args.anchors
    seats = args.seats
    if seats is None:
        seats = budget_module.project(
            args.wall_budget, evaluation=not args.no_evaluation_reserve
        ).seats
    # One anchor a family is a count of the families the tracked pool solved, read
    # rather than written down: the day a fifth parameter plane is seeded, the
    # pool this asks for divides by five without anything here being edited.
    families = max(1, len(roots_module.anchors(1)))
    wanted = math.ceil(
        max(0, int(seats)) * float(args.newton_share) * roots_module.DESCENTS_PER_SEAT / families
    )
    return max(args.anchors, wanted, deep_module.DEFAULT_SEATS)


def add_commands(subcommands) -> None:
    """`deep roots` and `deep walk`: the run mode for the release-stock tail."""
    from fractal_wallpapers.deep import depth
    from fractal_wallpapers.deep import run as deep_module

    diving = subcommands.add_parser(
        "deep",
        help="the deep run mode: source, score and record below the shallow walk's floor",
        description=(
            f"A separate sourcing mode for the tail the ordinary walk cannot reach. Its "
            f"floor is {depth.MIN_WIDTH:.0e} against the shallow walk's "
            f"{depth.SHALLOW_MIN_WIDTH:.0e}, and depth comes from WHICH ATOM it stands on "
            f"rather than from how far it descended: a seat is a nucleus whose own framing "
            f"band already lands below the shallow floor. Pure f64 end to end - there is no "
            f"perturbation kernel here - so a seat is refused up front unless f64 still "
            f"resolves its money shot at release geometry. Release the ledger it writes "
            f"with `curate run --deep --harvest <out-dir>`, which swaps in this mode's own "
            f"hung-unit ceilings."
        ),
    )
    steps = diving.add_subparsers(dest="step", required=True)

    def seat_flags(parser):
        parser.add_argument(
            "--seats",
            type=int,
            default=None,
            help=f"nuclei this run stands on. THE budget lever of this mode. Left unset it "
            f"is sized from --wall-budget where there is one, and is "
            f"{deep_module.DEFAULT_SEATS} where there is not",
        )
        parser.add_argument(
            "--newton-share",
            type=float,
            default=deep_module.Limits().newton_share,
            help="share of the seats the Newton channel is asked for first; whatever it "
            "cannot fill the continuation channel does, in the same call",
        )
        parser.add_argument(
            "--anchors",
            type=int,
            default=deep_module.Limits().anchors_per_family,
            help="plane-seed atoms per family a Newton ladder may start from, deepest first",
        )
        parser.add_argument("--seed", type=int, default=0, help="run seed (default: 0)")
        return parser

    sourcing = seat_flags(
        steps.add_parser(
            "roots",
            help="fill the seats and print them, standing on none of them",
            description=(
                "Both channels. `newton` tracks the boundary down from a tracked plane-seed "
                "atom, one Newton solve per rung at the precision the atom itself asks for, "
                "until an atom's band lands in this mode's window; `continuation` takes "
                "places earlier ledgers already admitted at the shallow floor. Every miss "
                "is counted with the reason, and every ladder is printed whether or not it "
                "arrived."
            ),
        )
    )
    sourcing.add_argument("--out", help="also write one seat per line to this JSONL file")
    sourcing.set_defaults(handler=deep_roots)

    walking = seat_flags(
        steps.add_parser(
            "walk",
            help="source the seats, stand on them, and record every fate",
            description=(
                "The shipped location head judges, at its own existing floors, with no "
                "deep-specific gate and no deep-specific calibration - it has seen nothing "
                "below 1.8e-10, so what this run buys is the record of what it said, at "
                "every fate, about material two decades below where it was trained."
            ),
        )
    )
    walking.add_argument(
        "--batch", type=int, default=deep_module.Limits().batch, help="nodes expanded per batch"
    )
    walking.add_argument(
        "--batches",
        type=int,
        default=None,
        help=f"batches to run. Left unset it is sized from the seats - a generous ceiling, "
        f"since the frontier empties long before it binds - and is {deep_module.DEFAULT_BATCHES} "
        f"for an unbudgeted run",
    )
    walking.add_argument(
        "--root-expansions",
        type=int,
        default=deep_module.Limits().root_expansions,
        help="expansions any one seat's roots may pay for",
    )
    walking.add_argument(
        "--wall-budget",
        type=float,
        metavar="SECONDS",
        help="size the seating against this, and stop cleanly rather than start a batch that "
        "would overrun it. Covers this run AND the evaluation frames that follow it: a "
        "seat is priced sourcing + walk + evaluation off deep_run1's measurements, so eight "
        "hours buys about 184 seats where that run took 32 and spent a quarter of its clock",
    )
    walking.add_argument(
        "--no-evaluation-reserve",
        action="store_true",
        help="a WALK-ONLY run: price a seat at sourcing and walk alone and let the budget "
        "buy far more of them. Not a saving - a run that takes this and then draws a "
        "frames anyway has no budget for them",
    )
    reseating = walking.add_mutually_exclusive_group()
    reseating.add_argument(
        "--reseat",
        dest="reseat",
        action="store_true",
        default=None,
        help="source again into the same run when the frontier empties with budget left "
        "(on by default, and inert without --wall-budget)",
    )
    reseating.add_argument(
        "--no-reseat",
        dest="reseat",
        action="store_false",
        help="stop when the frontier empties, whatever the budget has left",
    )
    walking.add_argument(
        "--lineage-cap",
        type=int,
        default=deep_module.LINEAGE_ADMISSIONS,
        help=f"admissions any one lineage may book before the walk stops expanding it "
        f"(default: {deep_module.LINEAGE_ADMISSIONS}; 0 turns the cap off). deep_run1 put "
        f"741 admissions on 15 of its 48 roots and 85 on one, and its floor frames were "
        f"largely one composition. Nothing is retro-refused: expansion stops, fates stand",
    )
    walking.add_argument(
        "--node-width",
        type=int,
        default=384,
        help="node render width in pixels; a scored run refuses any other",
    )
    walking.add_argument(
        "--colormap", default="twilight_shifted", help="colormap the gate renders are drawn through"
    )
    walking.add_argument(
        "--out-dir",
        default=str(Path("artifacts") / "deep"),
        help="where the ledger and thumbnails go (default: artifacts/deep)",
    )
    scoring_flags(walking)
    walking.set_defaults(handler=deep_walk)
