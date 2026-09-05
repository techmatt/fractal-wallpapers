"""`palette`: the palette head, from extraction to ship."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    device_flag,
)


def palette_extract(args: argparse.Namespace) -> int:
    """Vendor the real candidate sets a production colorize run recorded."""
    from fractal_wallpapers.models import palette_sets

    try:
        report = palette_sets.run(Path(args.source))
    except palette_sets.SetsError as refusal:
        print(refusal)
        return 1
    report["colormaps"].pop("names", None)
    print(json.dumps(report, indent=2))
    return 0


def palette_admit(args: argparse.Namespace) -> int:
    """Recompose the shipped pool for the drops admitted in the source."""
    from fractal_wallpapers.models import palette_sets

    try:
        report = palette_sets.admit()
    except palette_sets.SetsError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def palette_plan(args: argparse.Namespace) -> int:
    """Draw the distillation corpus: which places, which maps, in which order."""
    from fractal_wallpapers.models import palette_corpus

    try:
        rows = palette_corpus.draw(
            sets=args.sets,
            candidates=args.candidates,
            seed=args.seed,
            hard_share=args.hard_share,
        )
    except palette_corpus.CorpusError as refusal:
        print(refusal)
        return 1
    path = palette_corpus.write_plan(rows)
    from collections import Counter

    print(
        json.dumps(
            {
                "plan": str(path),
                "sets": len(rows),
                "candidates": sum(len(row["candidates"]) for row in rows),
                "per_partition": dict(sorted(Counter(r["partition"] for r in rows).items())),
                "seed": args.seed,
                "mix": palette_corpus.mix(rows),
            },
            indent=2,
        )
    )
    return 0


def palette_build(args: argparse.Namespace) -> int:
    """Render the candidate pictures, for the corpus, the real sets, or both."""
    from fractal_wallpapers.models import palette_corpus, palette_sets

    rows: list = []
    if args.which in ("corpus", "all"):
        rows.extend(palette_corpus.read_plan())
    if args.which in ("sets", "all"):
        rows.extend(palette_sets.read())
    print(json.dumps(palette_corpus.build(rows, limit=args.limit), indent=2))
    return 0


def palette_label(args: argparse.Namespace) -> int:
    """Ask the teacher about every candidate and write the machine-labeled rows."""
    from fractal_wallpapers.models import palette_corpus

    try:
        report = palette_corpus.label(Path(args.source), palette_corpus.read_plan())
    except (palette_corpus.CorpusError, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def palette_preregister(args: argparse.Namespace) -> int:
    """Write the palette head's bar, before there is a head to judge against it."""
    from fractal_wallpapers.models import palette_acceptance

    path = palette_acceptance.prereg_path()
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    print(json.dumps(palette_acceptance.preregister(), indent=2))
    return 0


def palette_train_head(args: argparse.Namespace) -> int:
    """Distil one palette head from the teacher's labels."""
    from fractal_wallpapers.models import palette_train

    try:
        record = palette_train.run(
            device=args.device,
            epochs=args.epochs,
            seed=args.seed,
            run_name=args.run,
            listwise=args.listwise,
        )
    except palette_train.TrainingError as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def palette_score(args: argparse.Namespace) -> int:
    """Score the real candidate sets through the student and through the teacher."""
    from fractal_wallpapers.models import palette_scoring

    print(
        json.dumps(
            palette_scoring.run(
                Path(args.source), which=args.which, device=args.device, into=args.run
            ),
            indent=2,
        )
    )
    return 0


def palette_accept(args: argparse.Namespace) -> int:
    """Read the distilled head against its pre-registered bar."""
    from fractal_wallpapers.models import palette_acceptance

    try:
        report = palette_acceptance.read(runs=args.run or None)
    except palette_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def palette_ship(args: argparse.Namespace) -> int:
    """Stage the palette head's half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import palette_acceptance, ship

    verdict_path = palette_acceptance.acceptance_path()
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers palette accept` first.")
        return 1
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1
    print(
        json.dumps(
            ship.stage(
                name="palette", which=args.which, tag=args.tag, device=args.device, run=args.run
            ),
            indent=2,
        )
    )
    return 0


def add_commands(subcommands) -> None:
    """The palette head, end to end: it is distilled, so it has two extra steps."""
    from fractal_wallpapers.models import palette_corpus

    group = subcommands.add_parser(
        "palette",
        help="the palette head end to end: extract, plan, build, label, train, ship",
        description=(
            "The one head this project does not train from human labels: there is no "
            "palette-preference corpus here to train it on, so it is distilled from the "
            "source project's pretrained head. Two steps exist that the other heads do not "
            "— vendoring the real candidate sets that head was really asked, and generating "
            "a corpus for it to answer — and both write text records the rest of the chain "
            "reads, so the head is regenerable from this repository forever."
        ),
    )
    steps = group.add_subparsers(dest="step", required=True)

    extracting = steps.add_parser(
        "extract",
        help="vendor the real candidate sets a production colorize run recorded",
        description=(
            "Rebuilds each set from the source's pool, its flavour table and the cap its "
            "release driver applies, and refuses to write anything unless every one of the "
            "recorded winners falls inside the set rebuilt for it. Brings across every map "
            "those sets name that this repository does not already hold."
        ),
    )
    extracting.add_argument("--source", required=True, help="the source repository's root")
    extracting.set_defaults(handler=palette_extract)

    admitting = steps.add_parser(
        "admit",
        help="recompose the drawable pool for the drops this repository admits",
        description=(
            "`palettes ingest` is bake, not offer: a densified map renders immediately and "
            "is not in the shipped pool, so nothing picks it. This is the offer, and it is "
            "the half of `extract` that needs no source checkout — the inherited half of "
            "the pool is the source project's own and is carried from the record, while the "
            "admitted half is read off each provenance row's drop stamp. Add the drop to "
            "`palette_sets.ADMITTED_DROPS` first; this writes what that says."
        ),
    )
    admitting.set_defaults(handler=palette_admit)

    planning = steps.add_parser(
        "plan",
        help="draw the distillation corpus: which places, which maps",
        description=(
            "Locations from this repository's own label corpus at the tiers that reach "
            "colorize, apportioned evenly across the partitions and capped by what each can "
            "supply; maps drawn from the shipped pool. Seeded end to end, and the vendored "
            "sets' own locations are excluded — they are the instrument."
        ),
    )
    planning.add_argument(
        "--sets", type=int, default=palette_corpus.SETS, help="how many candidate sets"
    )
    planning.add_argument(
        "--candidates", type=int, default=palette_corpus.CANDIDATES, help="maps per set"
    )
    planning.add_argument("--seed", type=int, default=palette_corpus.SEED, help="the draw's seed")
    planning.add_argument(
        "--hard-share",
        type=float,
        default=palette_corpus.HARD_SHARE,
        help="the share of sets built as palette-space neighbourhoods rather than uniform draws",
    )
    planning.set_defaults(handler=palette_plan)

    building = steps.add_parser(
        "build",
        help="render the candidate pictures",
        description=(
            "Resumable: a picture already on disk is skipped before its field is iterated, "
            "and a file is named for a digest of its own recipe, so two sets that draw the "
            "same map at the same place share one file."
        ),
    )
    building.add_argument(
        "--which",
        default="all",
        choices=["corpus", "sets", "all"],
        help="the distillation corpus, the vendored real sets, or both (default)",
    )
    building.add_argument("--limit", type=int, help="stop after this many pictures")
    building.set_defaults(handler=palette_build)

    labeling = steps.add_parser(
        "label",
        help="ask the teacher about every candidate and write the rows",
        description=(
            "The teacher is resolved through the source project's own single-source "
            "pointer and read on this repository's pictures. Every row carries its whole "
            "join, the teacher's score, and the sha256 of the weights that cast it."
        ),
    )
    labeling.add_argument("--source", required=True, help="the source repository's root")
    labeling.set_defaults(handler=palette_label)

    registering = steps.add_parser(
        "preregister",
        help="write the bar, before there is a head to judge against it",
        description=(
            "The bar is equivalence with the teacher on the real sets, and its calibrating "
            "number is declared as a rule rather than a value: the renderer control, which "
            "is how far the teacher already disagrees with its own recorded choices when "
            "the picture is made here instead of there."
        ),
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=palette_preregister)

    training = steps.add_parser(
        "train",
        help="distil one palette head from the teacher's labels",
        description=(
            "A batch is sixteen candidate SETS, because the loss centres inside a set. The "
            "epoch is chosen on the held-out distillation loss — a proper scoring rule for "
            "the vector being distilled — and never on a rank statistic."
        ),
    )
    device_flag(training)
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--listwise",
        type=float,
        help=(
            "weight of the listwise term beside the regression (0 is the regression alone). "
            "Its temperature is read off the corpus, never passed here"
        ),
    )
    training.add_argument(
        "--run", help="name this run, so its records land in their own directory: a seed band"
    )
    training.set_defaults(handler=palette_train_head)

    reading = steps.add_parser(
        "score",
        help="read the real candidate sets through the student and the teacher",
        description=(
            "Both readings on the same pictures, so what is compared is two functions and "
            "not two rendering pipelines. One row per set: the location, the candidates in "
            "order, both score vectors, and both picks."
        ),
    )
    reading.add_argument("--source", required=True, help="the source repository's root")
    reading.add_argument("--which", default="best", choices=["best", "last"])
    device_flag(reading)
    reading.add_argument("--run", help="the named training run to score")
    reading.set_defaults(handler=palette_score)

    judging = steps.add_parser(
        "accept",
        help="read the distilled head against its pre-registered bar",
        description=(
            "The bar comes from the file and nothing here may invent one. More than one "
            "--run is the seed band: the arms are read on the MEDIAN run by the top-pick "
            "statistic, never on the best of them."
        ),
    )
    judging.add_argument("--run", action="append", help="a named run to judge (repeatable)")
    judging.set_defaults(handler=palette_accept)

    shipping = steps.add_parser(
        "ship",
        help="stage the half-precision artifact and its manifest entry",
        description=(
            "The same cast, re-read and hash the other three heads ship through. What "
            "differs is the statistic: this head's decisions are top picks and its ordering "
            "is counted in discordant candidate pairs."
        ),
    )
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    device_flag(shipping)
    shipping.add_argument("--run", help="the named training run to ship")
    shipping.add_argument(
        "--force", action="store_true", help="ship a head whose acceptance read failed"
    )
    shipping.set_defaults(handler=palette_ship)
