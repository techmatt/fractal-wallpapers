"""`identity`: hash the render battery through the built engine, and compare two builds."""

from __future__ import annotations

import argparse


def identity(args: argparse.Namespace) -> int:
    """Record the battery under a tag, and compare it with an earlier tag if one is named.

    Exits 1 when the comparison finds a difference, so a zero-behaviour claim is a
    command that passes rather than a reading somebody makes.
    """
    from fractal_wallpapers import identity_battery

    threads = None if args.threads == 0 else args.threads
    path = identity_battery.record(
        args.tag, edge_frames=args.edges, workers=args.workers, threads=threads
    )
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
    recording.add_argument(
        "--workers",
        type=int,
        default=identity_battery_default("WORKERS"),
        help="engines at once (default: %(default)s, the render pool's size; never more)",
    )
    recording.add_argument(
        "--threads",
        type=int,
        default=identity_battery_default("THREADS"),
        help="threads each engine uses (default: %(default)s, so the battery leaves the "
        "desktop half the box; 0 lets each engine take every core). Hashes do not depend "
        "on it",
    )
    recording.set_defaults(handler=identity)


def identity_battery_default(name: str) -> int:
    """A battery constant for a flag's default. This imports the battery when the parser
    is built, which the base install allows: it and `engine` are stdlib only."""
    from fractal_wallpapers import identity_battery

    return getattr(identity_battery, name)
