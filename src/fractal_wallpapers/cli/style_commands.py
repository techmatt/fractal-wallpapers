"""`style`: the named layer stacks, and drawing a location in one."""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers import engine
from fractal_wallpapers.cli.common import resolve_output
from fractal_wallpapers.paths import tracked_name


def style(args: argparse.Namespace) -> int:
    """List the styles, show one, or render locations in one."""
    from fractal_wallpapers import styles

    try:
        if args.what == "list":
            for name in styles.names():
                document = styles.load(name)
                print(f"{name:<24} {document['suggested_colormap']:<24} {document['description']}")
            return 0
        if args.what == "show":
            print(json.dumps(styles.load(args.name), indent=2, ensure_ascii=False))
            return 0
        return render_style(args, styles)
    except styles.StyleError as refusal:
        print(refusal)
        return 1


def render_style(args: argparse.Namespace, styles) -> int:
    """Draw one location record, or every row of a manifest, in a style."""
    from fractal_wallpapers import locations

    document = styles.load(args.name)
    try:
        if args.location:
            rows = [locations.read_one(resolve_output(args.location), drawing=True)]
        else:
            rows = locations.read(resolve_output(args.manifest), drawing=True)
    except locations.LocationError as refusal:
        print(refusal)
        return 1

    for row in rows:
        row["render"] = {
            **row["render"],
            "resolution": list(args.resolution),
            "supersample": args.supersample,
        }
    if args.location:
        targets = [resolve_output(args.out)]
    else:
        directory = resolve_output(args.out_dir)
        directory.mkdir(parents=True, exist_ok=True)
        colormap = args.colormap or document["suggested_colormap"]
        targets = [
            directory / f"{index:02d}_{row.get('name') or locations.name_of(row)}_{colormap}.png"
            for index, row in enumerate(rows)
        ]

    for row, output in zip(rows, targets, strict=True):
        spec = styles.spec_of(row, document, output, colormap=args.colormap)
        try:
            report = engine.render_report(spec)
        except RuntimeError as refusal:
            print(str(refusal).removeprefix("engine failed: "))
            return 1
        report.pop("style", None)
        print(json.dumps({"output": tracked_name(output), **report}, ensure_ascii=False))
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    group = subcommands.add_parser(
        "style",
        help="the named layer stacks (data/styles/): list, show, or render a location in one",
    )
    group.set_defaults(handler=style)
    verbs = group.add_subparsers(dest="what", required=True)
    verbs.add_parser("list", help="every style, its suggested colormap and what it is")
    show = verbs.add_parser("show", help="print one style file whole")
    show.add_argument("name", help="a style name `style list` prints")

    render = verbs.add_parser(
        "render",
        help="draw a location record, or each row of a manifest, in a style with any colormap",
    )
    render.add_argument("name", help="a style name `style list` prints")
    where = render.add_mutually_exclusive_group(required=True)
    where.add_argument(
        "--location",
        metavar="FILE",
        help="one location record: the {family, viewport, maxiter} object `render` reads",
    )
    where.add_argument(
        "--manifest",
        metavar="FILE",
        help="a JSONL of location records, one picture per row, into --out-dir",
    )
    render.add_argument(
        "--colormap",
        help="any colormap `palettes list` prints (default: the style's suggested one)",
    )
    render.add_argument(
        "--resolution",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=[2560, 1600],
        help="output size in pixels (default: 2560 1600)",
    )
    render.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="samples per output pixel, per axis (default: 2)",
    )
    render.add_argument(
        "--out",
        default="artifacts/style.png",
        help="the picture, for --location (default: artifacts/style.png)",
    )
    render.add_argument(
        "--out-dir",
        default="artifacts/styles",
        help="where a --manifest run's pictures go (default: artifacts/styles)",
    )
