"""`spiral`: fit and read the spiral score."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    resolve_output,
)


def spiral_records(named: str) -> list[dict]:
    """Location records out of a JSONL file: a label row, a plan, a walk's finds."""
    from fractal_wallpapers import locations as locations_module

    rows = []
    for line in Path(named).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        source = row.get("recipe") if isinstance(row.get("recipe"), dict) else row
        rows.append(
            {
                "family": source["family"],
                "viewport": source["viewport"],
                "maxiter": locations_module.maxiter_of(
                    source if "render" in source else {"render": source, **source}
                ),
            }
        )
    return rows


def spiral_fit(args: argparse.Namespace) -> int:
    """Fit the probe on the store's training side and ship it as tracked text."""
    from fractal_wallpapers.models import spiral_probe

    train, evaluate = spiral_probe.split()
    features = spiral_probe.features(
        spiral_probe.records_of(train), args.set, directory=args.pictures
    )
    document = spiral_probe.fit(
        features,
        spiral_probe.targets(train),
        feature_set=args.set,
        threshold=args.threshold,
        description=spiral_probe.FEATURE_SETS[args.set],
    )
    shown = {
        key: value
        for key, value in document.items()
        if key not in ("mean", "deviation", "coefficients", "lambda_grid")
    }
    if not args.write:
        print(json.dumps(shown, indent=2))
        print(f"(dry run - {len(evaluate)} pinned rows untouched; pass --write to ship it)")
        return 0
    path = spiral_probe.write(document)
    documents = [
        spiral_probe.read(spiral_probe.probe_path(name))
        for name in spiral_probe.FEATURE_SETS
        if spiral_probe.probe_path(name).is_file()
    ]
    manifest = spiral_probe.write_manifest(documents)
    print(json.dumps({**shown, "wrote": [str(path), str(manifest)]}, indent=2))
    return 0


def spiral_read(args: argparse.Namespace) -> int:
    """Read a file of locations through the shipped probe and count the spirals."""
    import numpy

    from fractal_wallpapers.models import spiral_probe

    records = spiral_records(args.locations)
    document = spiral_probe.read(spiral_probe.probe_path(document_set := args.set))
    probability = numpy.asarray(
        spiral_probe.score(
            document, spiral_probe.features(records, document_set, directory=args.pictures)
        )
    )
    out = resolve_output(args.out) if args.out else None
    if out is not None:
        with out.open("w", encoding="utf-8", newline="\n") as handle:
            for record, value in zip(records, probability, strict=True):
                handle.write(
                    json.dumps(
                        {
                            "schema": spiral_probe.SCHEMA,
                            "family": record["family"],
                            "viewport": record["viewport"],
                            "feature_set": document_set,
                            "p_spiral": round(float(value), 6),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    print(
        json.dumps(
            {
                "locations": len(records),
                "feature_set": document_set,
                # The standing sweep UNIONED with the probe's own cut, so the acting
                # threshold is always one of the columns and a cut that already sits
                # on a sweep point collapses deliberately rather than by accident:
                # spelled `(0.3, document["threshold"], 0.7)`, a threshold of 0.3
                # silently reported two columns where a reader saw three.
                "at": {
                    str(cut): {
                        "spiral": int((probability >= cut).sum()),
                        "share": round(float((probability >= cut).mean()), 4),
                        "acting": cut == float(document["threshold"]),
                    }
                    for cut in sorted({0.3, 0.5, 0.7, float(document["threshold"])})
                },
                "wrote": str(out) if out is not None else None,
            },
            indent=2,
        )
    )
    return 0


def add_commands(subcommands) -> None:
    """The spiral probe: fit one on frozen features, read a population through it."""
    from fractal_wallpapers.models import spiral_probe

    probing = subcommands.add_parser(
        "spiral",
        help="the linear probe over frozen features: is this location a spiral",
        description=(
            "Nothing here is trained. A probe is one logistic regression over features a "
            "frozen network already produces, fitted on the `spiral` attribute store's "
            "training side and read on the pinned side by whoever reports. The ridge is "
            "chosen by cross-validation on the training side alone, and the shipped "
            "artifact is a coefficient vector small enough to track as text."
        ),
    )
    steps = probing.add_subparsers(dest="step", required=True)

    def with_set(parser):
        parser.add_argument(
            "--set",
            default=spiral_probe.SHIPPED,
            choices=sorted(spiral_probe.FEATURE_SETS),
            help=f"which frozen reading (default: {spiral_probe.SHIPPED})",
        )
        return parser

    fitting = with_set(
        steps.add_parser(
            "fit",
            help="fit the probe on the store's training side",
            description=(
                "The split is cut on the store's own pin and the pin is asserted on the "
                "training side before a feature is computed. The pinned rows are never read "
                "here - a blind slice is spent the moment it trains."
            ),
        )
    )
    fitting.add_argument(
        "--threshold",
        type=float,
        default=spiral_probe.THRESHOLD,
        help=f"where a probability becomes a verdict (default: {spiral_probe.THRESHOLD})",
    )
    fitting.add_argument(
        "--pictures", help="render the probe's own pictures here instead of their store"
    )
    fitting.add_argument("--write", action="store_true", help="ship it; otherwise print the plan")
    fitting.set_defaults(handler=spiral_fit)

    reading = with_set(
        steps.add_parser(
            "read",
            help="count the spirals in a file of locations",
            description=(
                "Every row is rendered at the probe's own regime, read through its frozen "
                "encoder and multiplied through the coefficients. Reports the share called "
                "`spiral` at three cuts, because a cap acts on a share."
            ),
        )
    )
    reading.add_argument("--locations", required=True, help="a JSONL of location records")
    reading.add_argument("--out", help="write one probability row per location")
    reading.add_argument(
        "--pictures", help="render the probe's own pictures here instead of their store"
    )
    reading.set_defaults(handler=spiral_read)
