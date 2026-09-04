"""`storage`: archive, restore and status over the three tiers."""

from __future__ import annotations

import argparse
import json


def storage_archive(args: argparse.Namespace) -> int:
    """Move a finished subtree to slow bulk storage."""
    from fractal_wallpapers import storage
    from fractal_wallpapers.paths import ARCHIVE

    print(json.dumps(storage.move(args.subtree, to=ARCHIVE), indent=2))
    return 0


def storage_restore(args: argparse.Namespace) -> int:
    """Bring an archived subtree back to where work happens."""
    from fractal_wallpapers import storage
    from fractal_wallpapers.paths import HOT

    print(json.dumps(storage.move(args.subtree, to=HOT), indent=2))
    return 0


def storage_status(args: argparse.Namespace) -> int:
    """One screen: every subtree, its tier, its size."""
    from fractal_wallpapers import storage

    report = storage.status(sizes=not args.no_sizes)
    print(f"hot     {report['hot']}")
    archive = report["archive"] or "(none configured)"
    print(f"archive {archive}{'' if report['archive_reachable'] else '   NOT REACHABLE'}")
    if report["archive"] and not report["archive_reachable"]:
        print("        Only the hot tier is listed below; archived subtrees are not shown.")
    print()
    totals: dict[str, list[int]] = {}
    for row in report["units"]:
        if row["tier"] == "BOTH":
            print(f"{row['name']:<28} BOTH TIERS — {row['collision']}")
            continue
        counted = totals.setdefault(row["tier"], [0, 0])
        counted[0] += row.get("files", 0)
        counted[1] += row.get("bytes", 0)
        size = (
            ""
            if args.no_sizes
            else f"{row['files']:>10,} files  {storage.bytes_said_plainly(row['bytes']):>12}"
        )
        print(f"{row['name']:<28} {row['tier']:<8}{size}")
    if not args.no_sizes:
        print()
        for tier, (files, size) in sorted(totals.items()):
            print(f"{tier:<28} {'':<8}{files:>10,} files  {storage.bytes_said_plainly(size):>12}")
    return 0


def add_commands(subcommands) -> None:
    """The two tiers: what is where, and moving a subtree between them."""
    storing = subcommands.add_parser(
        "storage",
        help="the hot and archive tiers: what is where, and moving a subtree between them",
        description=(
            "The regenerable tree lives on two disks. Work happens hot, on the fast one, "
            "and every write lands there; a subtree nothing is using archives to the slow "
            "one and reads through from there until it is restored. A subtree is in exactly "
            "one tier at a time, and which one is simply where its files are — there is no "
            "registry to fall out of step. Every move copies, verifies, and only then "
            "deletes the source."
        ),
    )
    steps = storing.add_subparsers(dest="step", required=True)

    def with_subtree(parser):
        parser.add_argument(
            "subtree",
            help="a top-level name of the artifacts tree, as `storage status` lists it",
        )
        return parser

    archiving = with_subtree(
        steps.add_parser(
            "archive",
            help="move a finished subtree to slow bulk storage",
            description=(
                "For a subtree nothing is actively reading. It stays readable — every name "
                "under it resolves through to the archive — but a random small-file read "
                "pattern over it is an order of magnitude slower, which is why the trainers "
                "refuse to run against one."
            ),
        )
    )
    archiving.set_defaults(handler=storage_archive)

    restoring = with_subtree(
        steps.add_parser(
            "restore",
            help="bring an archived subtree back to where work happens",
            description=(
                "The step before a retrain. Measured against a USB hard drive this is tens "
                "of minutes for a large cache, and it says so with an estimate before it "
                "starts rather than after."
            ),
        )
    )
    restoring.set_defaults(handler=storage_restore)

    showing = steps.add_parser(
        "status",
        help="every subtree, its tier and its size",
    )
    showing.add_argument(
        "--no-sizes",
        action="store_true",
        help="tiers only. Walking a million files for their sizes is minutes on the archive",
    )
    showing.set_defaults(handler=storage_status)
