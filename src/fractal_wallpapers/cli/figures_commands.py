"""`figures`: the article's figures."""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import (
    resolve_output,
)


def figure_score_to_decision(args: argparse.Namespace) -> int:
    """Draw one frame per outcome the judges' ladder has, plus their provenance."""
    from fractal_wallpapers.models import decisions

    try:
        if args.coverage:
            spread = decisions.coverage(decisions.held_out(args.head, args.run))
            print(json.dumps(spread, indent=2))
            return 0
        report = decisions.draw(
            args.family, resolve_output(args.out_dir) if args.out_dir else None, args.head, args.run
        )
    except decisions.DecisionError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def add_commands(subcommands) -> None:
    """The figures the article needs that only this repository can draw."""
    group = subcommands.add_parser(
        "figures",
        help="draw a figure the article needs from this repository's own records",
        description=(
            "A figure here is a command rather than a saved picture: it is drawn from the "
            "tracked records and the shipped weights, so it can be redrawn when either "
            "moves. The pictures land under artifacts/, which is regenerable by definition."
        ),
    )
    steps = group.add_subparsers(dest="step", required=True)

    ladder = steps.add_parser(
        "judges-score-to-decision",
        help="one frame per outcome: refused, expandable, find, exceptional",
        description=(
            "Four held-out human-labeled locations of one family, one for each outcome the "
            "head's score lands in, each rendered as the canonical view the head read. The "
            "sidecar carries every frame's row key, the person's class and the head's own "
            "probabilities — the human label is shown, never used to choose the frame."
        ),
    )
    ladder.add_argument(
        "--family",
        default="julia:multibrot3",
        help="the partition to draw from (default: julia:multibrot3)",
    )
    ladder.add_argument("--head", default="location", help="which judge's ladder")
    ladder.add_argument("--run", help="a training run other than the shipped one")
    ladder.add_argument(
        "--coverage",
        action="store_true",
        help="print how every family's held-out rows spread across the four, and draw nothing",
    )
    ladder.add_argument(
        "--out-dir",
        help="where the frames land (default: artifacts/figures/judges_score_to_decision)",
    )
    ladder.set_defaults(handler=figure_score_to_decision)
