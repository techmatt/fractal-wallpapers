"""`identity`: hash the render battery through the built engine, and compare two builds."""

from __future__ import annotations

import argparse


def identity(args: argparse.Namespace) -> int:
    """Record the battery under a tag, and compare it with an earlier tag if one is named.

    Exits 1 when the comparison finds a difference, so a zero-behaviour claim is a
    command that passes rather than a reading somebody makes.
    """
    from fractal_wallpapers import identity_battery

    path = identity_battery.record(args.tag, edge_frames=args.edges)
    print(f"recorded {path}")
    if args.against is None:
        return 0
    differ = identity_battery.compare(args.against, args.tag)
    print(f"{len(differ)} differ from {args.against}")
    for name in differ[:40]:
        print(f"  {name}")
    return 1 if differ else 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    recording = subcommands.add_parser(
        "identity",
        help="hash a fixed battery of renders, to hold an engine change to zero behaviour",
    )
    recording.add_argument(
        "tag",
        help="name for this recording, written to identity/<tag>.json under the hot root.",
    )
    recording.add_argument(
        "--against",
        metavar="TAG",
        help="compare with an earlier recording and exit 1 on any difference. "
        "Record before the change, rebuild, record again with this flag.",
    )
    recording.add_argument(
        "--edges",
        action="store_true",
        help="draw the edge frames of the engine's interior tests instead of the battery. "
        "The cardioid, the bulb, each Multibrot degree's disk and each Julia plane's "
        "attracting-cycle disk, at widths 1e-2 to 1e-9 and two caps.",
    )
    recording.set_defaults(handler=identity)
