"""`walkthrough`: every inspection page of the README's path, as one portable folder."""

from __future__ import annotations

import argparse

from fractal_wallpapers.cli.common import display_path, resolve_output


def walkthrough(args: argparse.Namespace) -> int:
    """Write every page's bundle, the small whole files, and an index into one folder."""
    from fractal_wallpapers import bundle
    from fractal_wallpapers import walkthrough as walkthrough_module
    from fractal_wallpapers.curation import tentative

    out = resolve_output(args.out) if args.out else walkthrough_module.out_dir()
    stamp = args.stamp or tentative.viewable()
    try:
        listing = walkthrough_module.build(out, stamp, resolve_output(args.run))
    except (FileNotFoundError, tentative.TentativeRefused) as refusal:
        print(refusal)
        return 1
    print(display_path(out / "index.html"))
    print(bundle.said(out))
    return 1 if any(page.get("missing") for page in listing["pages"]) else 0


def add_commands(subcommands) -> None:
    """Register `walkthrough`."""
    parser = subcommands.add_parser(
        "walkthrough",
        help="every inspection page of the README's path, bundled into one folder",
        description=(
            "The last step of the README's path. Writes, into one folder: judges-check/, "
            "walk-stats/, candidates/, gallery/ and trace/, each a portable bundle "
            "(index.html, page.json and only the pictures it shows, re-encoded small); the "
            "harvest's summary.json, stats.json and the keep list's keep.jsonl; and an "
            "index.html linking them. Nothing is rendered or judged again: the first three "
            "are drawn from the page.json their own commands left, and a page whose command "
            "was not run is listed with that command. Default artifacts/walkthrough/."
        ),
    )
    parser.add_argument("--out", metavar="DIR", help="the folder (default artifacts/walkthrough)")
    parser.add_argument(
        "--stamp", help="the record to show and trace (default the newest one made here)"
    )
    parser.add_argument(
        "--run",
        default="artifacts/harvest",
        metavar="DIR",
        help="the harvest whose stats and summary go in (default artifacts/harvest)",
    )
    parser.set_defaults(handler=walkthrough)
