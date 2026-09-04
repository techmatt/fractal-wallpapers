"""`coloring`: the band derivation, the flat texture, and the show."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def coloring_derive_band(args: argparse.Namespace) -> int:
    """Measure a reference set of finished wallpapers and derive the tone band."""
    from fractal_wallpapers.coloring import band

    try:
        record = band.derive(Path(args.source))
    except band.BandError as refusal:
        print(refusal)
        return 1
    if args.write:
        print(f"wrote {band.write(record)}")
    printable = {key: value for key, value in record.items() if key != "per_image"}
    print(json.dumps(printable, indent=2))
    if not args.write:
        print("(dry run - pass --write to replace the shipped band)")
    return 0


def coloring_texture_flat(args: argparse.Namespace) -> int:
    """Measure, or report, which renders' modulate texture said nothing."""
    from fractal_wallpapers.coloring import texture_flat

    try:
        if args.what == "show":
            print(json.dumps(texture_flat.summary(), indent=2))
            return 0
        if args.what == "stamp":
            print(json.dumps(texture_flat.stamp_ledger(), indent=2))
            return 0
        stores = tuple(args.store) if args.store else texture_flat.STORES
        record = texture_flat.measure_stores(stores=stores, workers=args.workers, limit=args.limit)
    except texture_flat.RegisterError as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    return 0


def coloring_show(args: argparse.Namespace) -> int:
    """Print the operator's switch and the band it is projecting onto."""
    from fractal_wallpapers.coloring import autolevel, band

    del args
    try:
        record = band.load()
    except band.BandError as refusal:
        print(refusal)
        return 1
    print(
        f"{autolevel.OPERATOR} · switch {'ON' if autolevel.enabled() else 'OFF'} "
        f"(default {autolevel.SWITCH_DEFAULT}, {autolevel.SWITCH_ENV}="
        f"{__import__('os').environ.get(autolevel.SWITCH_ENV)!r})"
    )
    print(
        f"band {record['_path']} · {record['n_images']} images · derived {record['derived']} "
        f"· sha256 {record['_sha256'][:16]}"
    )
    for name, edges in band.bands(record).items():
        print(f"  {name:<10} [{edges[0]:.4f}, {edges[1]:.4f}]")
    return 0


def add_commands(subcommands) -> None:
    """The tone band, the operator that projects onto it, and the texture register."""
    colouring = subcommands.add_parser(
        "coloring",
        help="the tone band, the autolevel operator and the flat-texture register",
        description=(
            "The autolevel operator pulls a render's tone onto a band of finished "
            "wallpapers that are already good, or — when it is already inside the band — "
            "leaves it exactly alone and hands back the render's own bytes. `texture-flat` "
            "is the other thing measured about a finished coloring here: which renders' "
            "modulate texture carried no information, and therefore route as smooth."
        ),
    )
    steps = colouring.add_subparsers(dest="step", required=True)

    showing = steps.add_parser("show", help="print the switch and the band it projects onto")
    showing.set_defaults(handler=coloring_show)

    deriving = steps.add_parser(
        "derive-band",
        help="measure a reference set of finished wallpapers and derive the band",
        description=(
            "Reads a folder of finished wallpapers and writes the tracked band record. The "
            "folder is only ever read, and what ships is the measurement plus the names it "
            "was taken over — never a path. A re-derivation that moves an edge is a new band "
            "and therefore a new decision, which is why it needs --write."
        ),
    )
    deriving.add_argument(
        "--from",
        dest="source",
        required=True,
        help="a folder of finished wallpapers, read only",
    )
    deriving.add_argument("--write", action="store_true", help="write it; otherwise print it")
    deriving.set_defaults(handler=coloring_derive_band)

    from fractal_wallpapers.coloring import texture_flat as texture_flat_module

    flat = steps.add_parser(
        "texture-flat",
        help="the register of renders whose modulate texture carried no information",
        description=(
            "A modulate lays a texture over a base and shifts the base's palette position "
            "by it. Where the texture has no span, the shift is zero everywhere and the "
            "picture is the base spent by rank BIT FOR BIT — so the render routes as "
            "`smooth` wherever a mode or a kind is decided. The engine reports it per "
            "render; this is the tracked measurement for the rows written before it did, "
            "keyed on the field side of the render so one probe answers for every map at a "
            "location. `measure` renders what it has not measured and nothing else."
        ),
    )
    flat.add_argument(
        "what",
        choices=["measure", "stamp", "show"],
        help="render every unmeasured identity the named stores hold, carry what it says "
        "onto the candidate-ledger rows, or print what the register already says",
    )
    flat.add_argument(
        "--store",
        action="append",
        choices=list(texture_flat_module.STORES),
        help="with `measure`: which store to take identities from, repeatable (default: "
        "both). The ledger is drawn at the candidate regime and the label stores at the "
        "shipping one, so a place in both is two identities and two probes",
    )
    flat.add_argument(
        "--workers",
        type=int,
        default=texture_flat_module.MEASURE_WORKERS,
        metavar="COUNT",
        help=f"with `measure`: how many engines to drive at once (default "
        f"{texture_flat_module.MEASURE_WORKERS}, this machine's render pool). More than "
        f"three, or any of them at normal priority, makes the desktop unusable",
    )
    flat.add_argument(
        "--limit",
        type=int,
        help="with `measure`: stop after this many identities. What a pilot prices the "
        "whole leg off",
    )
    flat.set_defaults(handler=coloring_texture_flat)
