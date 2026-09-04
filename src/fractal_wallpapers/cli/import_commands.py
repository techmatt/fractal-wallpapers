"""`import-labels` and `import-finished`: the build-era readers of the source project.

Both go at publication, and this module goes with them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def import_labels(args: argparse.Namespace) -> int:
    """Import the source project's location labels as flat rows."""
    from fractal_wallpapers.labeling import corpus_import

    try:
        report = corpus_import.run(Path(args.source), seed=args.seed, share=args.share)
    except corpus_import.CorpusImportError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def import_finished(args: argparse.Namespace) -> int:
    """Import the source project's finished-render corpora as flat rows."""
    from fractal_wallpapers.labeling import finished, finished_import

    heads = [args.head] if args.head else sorted(finished.HEADS)
    reports = {}
    for head in heads:
        try:
            reports[head] = finished_import.run(Path(args.source), head)
        except (finished_import.FinishedImportError, finished.FinishedError) as refusal:
            print(refusal)
            return 1
    print(json.dumps(reports, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """Register this group's commands, in the order they ship in."""
    bringing = subcommands.add_parser(
        "import-labels",
        help="import the source project's location labels into this store, as flat rows",
        description=(
            "Read another corpus through its own canonical reader, resolve every label once "
            "— amendment overlay applied, revision rows read past, one verdict per location "
            "as the maximum over its crops — and write flat rows here. Registers each batch "
            "it lands before writing a row of it, and draws the split when it is done."
        ),
    )
    bringing.add_argument("--source", required=True, help="the source repository's root")
    bringing.add_argument("--seed", type=int, default=0, help="the split draw's seed (default: 0)")
    bringing.add_argument(
        "--share", type=float, default=0.20, help="the evaluation side's target share"
    )
    bringing.set_defaults(handler=import_labels)

    finishing = subcommands.add_parser(
        "import-finished",
        help="import the source project's finished-render corpora into their stores",
        description=(
            "Read both finished-render corpora through the source's own resolution rules — "
            "one exported file per finished sheet, joined by image id, asserted in both "
            "directions — and write flat rows here. Every registration flag is read from the "
            "source and checked against this repository's table row by row; a single "
            "disagreement writes nothing. Brings across every colormap the rows name, because "
            "a row naming a map nobody holds is not a row that can be rendered."
        ),
    )
    finishing.add_argument("--source", required=True, help="the source repository's root")
    finishing.add_argument("--head", help="import only this judge's corpus instead of both")
    finishing.set_defaults(handler=import_finished)
