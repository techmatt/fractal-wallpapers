"""`regime`: the acceptance split, the flips, and the staged restatement."""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import (
    device_flag,
    write_tracked_json,
)


def regime_preregister(args: argparse.Namespace) -> int:
    """Write the bar for the cross-regime study, before the candidate exists."""
    from fractal_wallpapers.models import regime_acceptance

    path = regime_acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("amend it in place — the record carries an append-only list for that.")
        return 1
    bar = regime_acceptance.preregister(args.head)
    write_tracked_json(path, bar)
    print(json.dumps(bar, indent=2))
    return 0


def regime_accept(args: argparse.Namespace) -> int:
    """Read the candidate band against the pre-registered cross-regime bar."""
    from fractal_wallpapers.models import regime_acceptance

    report = regime_acceptance.read(args.head)
    write_tracked_json(regime_acceptance.acceptance_path(args.head), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def flip_preregister(args: argparse.Namespace) -> int:
    """Write the second bar — flips on production stock — before any row is scored."""
    from fractal_wallpapers.models import regime_flips

    path = regime_flips.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("amend it in place — the record carries an append-only list for that.")
        return 1
    bar = regime_flips.preregister(args.head)
    write_tracked_json(path, bar)
    print(json.dumps(bar, indent=2))
    return 0


def flip_score(args: argparse.Namespace) -> int:
    """Draw the stock, render it at every regime, and read every run over it."""
    from fractal_wallpapers.models import regime_flips

    report = regime_flips.score(
        head=args.head,
        limit=args.limit,
        workers=args.workers,
        device=args.device,
    )
    print(json.dumps(report, indent=2))
    return 0


def flip_read(args: argparse.Namespace) -> int:
    """Read the band against the second bar."""
    from fractal_wallpapers.models import regime_flips

    report = regime_flips.read(args.head)
    write_tracked_json(regime_flips.acceptance_path(args.head), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


#: Which pre-registered read authorizes a staging, by the population it was made
#: on. Two bars judge this candidate and they are not interchangeable: one is the
#: evaluation split, the other is production stock.
STAGING_READS = {"split": "regime_acceptance", "stock": "regime_flips"}


def regime_restate(args: argparse.Namespace) -> int:
    """Restate every cut the candidate's scale moves, against a fixed pool."""
    from fractal_wallpapers.models import adoption

    path = adoption.restatement_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists, and the population it was measured against is the")
        print("shipped head's read of the sidecar — which a re-score replaces. Re-measuring")
        print("after a flip restates the candidate against itself.")
        return 1
    try:
        record = adoption.restate(head=args.head, device=args.device)
    except adoption.AdoptionError as refusal:
        print(refusal)
        return 1
    write_tracked_json(path, record)
    print(json.dumps(record, indent=2))
    return 0


def regime_adopt(args: argparse.Namespace) -> int:
    """Flip the shipped head to the staged candidate, at the restated cuts."""
    from fractal_wallpapers.models import adoption

    try:
        record = adoption.adopt(head=args.head, tag=args.tag or adoption.TAG)
    except adoption.AdoptionError as refusal:
        print(refusal)
        return 1
    write_tracked_json(adoption.adoption_path(args.head), record)
    print(json.dumps(record, indent=2))
    return 0


def regime_stage(args: argparse.Namespace) -> int:
    """Halve, verify and hash the winning seed — beside the shipped head."""
    import importlib

    from fractal_wallpapers.models import ship

    judge = importlib.import_module(f"fractal_wallpapers.models.{STAGING_READS[args.read]}")
    verdict_path = judge.acceptance_path(args.head)
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this candidate on the")
        print(f"{args.read} population yet. Run the read that writes it first.")
        return 1
    judged = json.loads(verdict_path.read_text(encoding="utf-8"))
    if judged["verdict"] == "FAIL" and not args.force:
        print(f"the {args.read} read says {judged['verdict']}. Staging a candidate that")
        print("failed its own pre-registered bar needs --force and a sentence about why.")
        return 1
    chosen = judged["staged"]["seed"] if "staged" in judged else judged["gated_on"]
    record = ship.stage_candidate(
        name=args.head,
        which=args.which,
        run=args.run or chosen,
        device=args.device,
        why=args.why,
        verdict=verdict_path,
    )
    print(json.dumps({key: record[key] for key in record if key != "agreement"}, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """One head, three regimes: the bar, the read against it, the candidate."""
    studying = subcommands.add_parser(
        "regime",
        help="judge a location head's agreement with itself across rendering regimes",
        description=(
            "The shipped location head learned one geometry and is only honest there: read "
            "at a cheaper regime its scores fall, worst on multibrot3, far enough to cross "
            "the floors the supply engine acts on. These steps write a bar for a head "
            "trained over every cached regime at once, read a seed band against it, and "
            "stage the winner beside the shipped head. There are two bars and two "
            "populations: the first is read on the evaluation split, where most rows agree "
            "trivially, and the flip- steps re-ask the same question on production stock at "
            "the gates the supply engine acts on. Adopting the winner is the last two "
            "steps and is priced rather than assumed: a location retrain moves the scale "
            "every floor is calibrated against, so `restate` measures where those floors "
            "land on the new scale and `adopt` flips what serves."
        ),
    )
    steps = studying.add_subparsers(dest="step", required=True)

    def with_head(parser):
        parser.add_argument("--head", default="location", help="which judge (default: location)")
        return parser

    registering = with_head(
        steps.add_parser(
            "preregister",
            help="write the bar, before there is a candidate to judge against it",
            description=(
                "Two arms: the candidate must not be significantly worse than the shipped "
                "head at the canonical regime on the repository's proper scoring rule, and "
                "all four cross-regime consistency slices must significantly improve. "
                "Refuses to overwrite an existing bar — amendments are appended to it."
            ),
        )
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no candidate has been judged against"
    )
    registering.set_defaults(handler=regime_preregister)

    judging = with_head(
        steps.add_parser(
            "accept",
            help="read the candidate band against the pre-registered bar",
            description=(
                "Every arm is a paired cluster bootstrap over the evaluation side, read on "
                "the MEDIAN seed of the band by that arm's own statistic. Exits non-zero "
                "on FAIL."
            ),
        )
    )
    judging.set_defaults(handler=regime_accept)

    staging = with_head(
        steps.add_parser(
            "stage",
            help="halve, verify and hash the winning seed as a candidate artifact",
            description=(
                "The same cast, re-read, agreement check and hash a shipment gets, into "
                "<head>.candidate.fp16.pt beside the shipped artifact. It does NOT write "
                "the weights manifest, so no serving path resolves it: adopting a candidate "
                "is a separate decision with a separate price."
            ),
        )
    )
    staging.add_argument("--which", default="best", choices=["best", "last"])
    device_flag(staging)
    staging.add_argument(
        "--run", help="the run to stage (default: the seed the bar's selection rule chose)"
    )
    staging.add_argument("--why", default="", help="one sentence: what this candidate is for")
    staging.add_argument(
        "--read",
        default="split",
        choices=sorted(STAGING_READS),
        help=(
            "which pre-registered read authorizes this staging, by the population it was "
            "made on: the evaluation split, or production stock (default: split)"
        ),
    )
    staging.add_argument("--force", action="store_true", help="stage a candidate whose read failed")
    staging.set_defaults(handler=regime_stage)

    registering_flips = with_head(
        steps.add_parser(
            "flip-preregister",
            help="write the second bar: decision flips on production stock",
            description=(
                "The first bar was read on the evaluation split, where 78% of rows read "
                "below P(>=3)=0.05 at every geometry and agree trivially — three of its "
                "four slices could not clear zero. This one re-asks the consistency "
                "question on the population the motivating numbers came from, at the gates "
                "the supply engine actually acts on. Refuses to overwrite an existing bar."
            ),
        )
    )
    registering_flips.add_argument(
        "--force", action="store_true", help="overwrite a bar no candidate has been judged against"
    )
    registering_flips.set_defaults(handler=flip_preregister)

    reading = with_head(
        steps.add_parser(
            "flip-score",
            help="draw the stock, render it at every regime, and read every run over it",
            description=(
                "The draw is the bar's: its size and its seed come out of the "
                "pre-registration, and every location the label store holds is excluded. "
                "Renders are reused, so a re-run costs the engine nothing it already paid."
            ),
        )
    )
    reading.add_argument(
        "--limit",
        type=int,
        help=(
            "read a prefix of the draw. The rehearsal a render budget is estimated from: "
            "it writes no verdict and the read refuses a population smaller than the bar's"
        ),
    )
    reading.add_argument(
        "--workers",
        type=int,
        help=(
            "render worker processes (default: the scorer's own, which is one — a single "
            "view already spends the whole machine, and every fan-out arm measures slower)"
        ),
    )
    device_flag(reading)
    reading.set_defaults(handler=flip_score)

    judging_flips = with_head(
        steps.add_parser(
            "flip-read",
            help="read the band against the second bar",
            description=(
                "A paired bootstrap over LOCATIONS — stock has no neighbourhood groups — on "
                "the seed the training-side selection rule froze. Exits non-zero on FAIL."
            ),
        )
    )
    judging_flips.set_defaults(handler=flip_read)

    restating = with_head(
        steps.add_parser(
            "restate",
            help="restate every cut the candidate's scale moves, before anything flips",
            description=(
                "The junk floor, the good floor and the great cut are points on the shipped "
                "head's probability scale and say nothing on another head's. Each is "
                "restated as the candidate score passing the SAME FRACTION of a fixed "
                "reference pool — the whole curation sidecar, read through the pictures its "
                "own scores were taken off. Refuses once the flip has happened: the "
                "fractions are the retired head's reads, and a re-score replaces them."
            ),
        )
    )
    device_flag(restating)
    restating.add_argument(
        "--force", action="store_true", help="overwrite a restatement nothing has flipped against"
    )
    restating.set_defaults(handler=regime_restate)

    adopting = with_head(
        steps.add_parser(
            "adopt",
            help="flip the shipped head to the staged candidate, at the restated cuts",
            description=(
                "Ships the candidate under the head's own asset name and checks that what "
                "landed is the artifact the two bars judged. Refuses unless the restatement "
                "is already recorded AND the modules that own the cuts already declare it — "
                "which is the refusal the cuts themselves would make on their first call, "
                "taken one step earlier."
            ),
        )
    )
    adopting.add_argument(
        "--tag", default=None, help="the release tag to name (default: the head's next one)"
    )
    adopting.set_defaults(handler=regime_adopt)
