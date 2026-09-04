"""`head`: the location head, from preregistration to ship."""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import (
    device_flag,
    write_tracked_json,
)
from fractal_wallpapers.labeling.finished import HEADS as FINISHED_HEADS


def one_regime(named: str):
    """One regime, by the name its files carry."""
    from fractal_wallpapers.models import tiles as tile_module

    try:
        return tile_module.regime_of(named)
    except ValueError as unparsed:
        raise SystemExit(str(unparsed)) from None


def head_regimes(args: argparse.Namespace) -> tuple:
    """The regimes a `head` subcommand was aimed at, canonical first.

    Named as they appear in the files a build wrote — `640x360ss1` — with the
    canonical one spelled out in full rather than by the empty segment it elides
    to in a name. No flag means the canonical regime alone, which is what the
    shipped head trains and scores at.
    """
    from fractal_wallpapers.models import tiles as tile_module

    stated = list(args.regime or [])
    if not stated:
        return (tile_module.CANONICAL_REGIME,)
    try:
        drawn = tuple(dict.fromkeys(tile_module.regime_of(name) for name in stated))
    except ValueError as unparsed:
        raise SystemExit(str(unparsed)) from None
    if tile_module.CANONICAL_REGIME not in drawn:
        raise SystemExit(
            "the canonical regime has to be one of them: the selection slice, the deploy "
            "view and every score file are read at it. Add --regime 640x360ss2."
        )
    return (
        tile_module.CANONICAL_REGIME,
        *(regime for regime in drawn if regime != tile_module.CANONICAL_REGIME),
    )


def head_train(args: argparse.Namespace) -> int:
    """Train one head on the built tiles."""
    from fractal_wallpapers.models import train

    record = train.train(
        name=args.head,
        device=args.device,
        epochs=args.epochs,
        seed=args.seed,
        run=args.run,
        regimes=head_regimes(args),
        selection=args.selection,
    )
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def head_score(args: argparse.Namespace) -> int:
    """Score one side of the build through a trained checkpoint."""
    from fractal_wallpapers.models import scoring

    print(
        json.dumps(
            scoring.run(
                name=args.head,
                which=args.which,
                side=args.side,
                device=args.device,
                into=args.run,
                regime=one_regime(args.regime),
            ),
            indent=2,
        )
    )
    return 0


def head_floor(args: argparse.Namespace) -> int:
    """Fit one finished-render head's release floor off its own labels."""
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.models import release_floor

    try:
        record = release_floor.run(args.head, device=args.device, resamples=args.bootstrap)
    except (release_floor.FloorFitError, floors.HeadStampMismatch, FileNotFoundError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    # A measurement, never a move: `curation.floors` is the only owner of a height
    # that acts, and putting this one there is somebody's decision.
    # Every MEASURED height is held to reproducing, not only the acting one. A
    # floor that is recorded and does not re-fit is a number nobody can check,
    # and whether it happens to gate today is a different question from whether
    # it is still true.
    standing = floors.MEASURED_RELEASE_FLOORS.get(args.head)
    if standing is not None:
        acting = args.head in floors.ACTING_RELEASE_BARS
        held = record["rounded_up_to_0_005"] == standing.value
        print(
            f"standing {'bar' if acting else 'floor (advisory)'} {standing.value:g} vs this "
            f"fit {record['rounded_up_to_0_005']:g} on the 0.005 grid "
            f"({record['rounded_up_3_places']:g} at three places): "
            f"{'REPRODUCED' if held else 'DOES NOT REPRODUCE'}"
        )
        if held and standing.head_sha256 != record["head_sha256"]:
            print(
                f"but the standing height is stamped {standing.head_sha256[:12]} and this "
                f"fit read {record['head_sha256'][:12]}: the height is right and the stamp "
                f"is stale. Restate it."
            )
            return 1
        return 0 if held else 1
    print(
        f"no measured floor on {args.head}. This is a reading, and wiring it into a "
        f"selection is a separate decision."
    )
    return 0


def head_audit(args: argparse.Namespace) -> int:
    """Read a run's clock against its own epochs, then re-score to settle it."""
    from fractal_wallpapers.models import audit

    report = audit.run(name=args.head, run_name=args.run, which=args.which, device=args.device)
    write_tracked_json(audit.audit_path(args.head, args.run), report)
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] == "REPRODUCED" else 1


def head_preregister(args: argparse.Namespace) -> int:
    """Write the bar, before the head that will be judged against it exists."""
    from fractal_wallpapers.models import acceptance

    path = acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    bar = acceptance.preregister(args.head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bar, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bar, indent=2))
    return 0


def head_accept(args: argparse.Namespace) -> int:
    """Read a trained head against the pre-registered bar."""
    from fractal_wallpapers.models import acceptance

    report = acceptance.read(args.head, runs=args.run or None)
    path = acceptance.acceptance_path(args.head)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def head_ship(args: argparse.Namespace) -> int:
    """Stage the half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import acceptance, ship

    verdict_path = acceptance.acceptance_path(args.head)
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers head accept` first.")
        return 1
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1

    print(
        json.dumps(
            ship.stage(
                name=args.head,
                which=args.which,
                tag=args.tag,
                device=args.device,
                run=args.run,
            ),
            indent=2,
        )
    )
    return 0


def add_commands(subcommands) -> None:
    """A judge, end to end: pre-register the bar, train, score, judge, ship."""
    from fractal_wallpapers.models import release_floor as release_floor_module

    judging = subcommands.add_parser(
        "head",
        help="a judge end to end: preregister, train, score, accept, ship",
        description=(
            "The five steps are separate commands on purpose. Each writes a record the next "
            "one reads, so a training run can be re-scored and a score can be re-judged "
            "without any of it happening again — and so the bar is written down before the "
            "head it judges exists."
        ),
    )
    steps = judging.add_subparsers(dest="step", required=True)

    def with_head(parser):
        parser.add_argument("--head", default="location", help="which judge (default: location)")
        return parser

    registering = with_head(
        steps.add_parser(
            "preregister",
            help="write the bar, before there is a head to judge against it",
            description=(
                "Builds the bar out of the incumbent head's committed scores on this "
                "repository's own evaluation side, and out of how precisely that population "
                "can tell two heads apart at all. Refuses to overwrite an existing bar."
            ),
        )
    )
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=head_preregister)

    training = with_head(steps.add_parser("train", help="train a head on the built tiles"))
    device_flag(training)
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--regime",
        action="append",
        metavar="WxHssN",
        help="a geometry to draw the tiles at, e.g. 640x360ss1 (repeatable). Every regime "
        "given adds a pass over the whole population to each epoch — the same label row, "
        "the same slot, a different geometry — and the head is told nothing about which "
        "one it is looking at. The canonical 640x360ss2 must be among them; omit the flag "
        "for it alone, which is the shipped recipe",
    )
    training.add_argument(
        "--selection",
        choices=["ap_ge2", "cutpoint_cross_entropy"],
        help="which objective chooses the epoch, over the training-side selection slice at "
        "the canonical regime (default: the recipe's own)",
    )
    training.add_argument(
        "--run",
        help="name this run, so its checkpoint and records land in their own directory. "
        "What a seed band is made of; omit for the head's one run",
    )
    training.set_defaults(handler=head_train)

    reading = with_head(
        steps.add_parser(
            "score",
            help="score one side of the build through a trained checkpoint",
            description=(
                "Every location goes through its canonical tile — the deploy view — so the "
                "number is the one a deployed judge would produce. A score row carries its "
                "whole join, the same rule a label row does."
            ),
        )
    )
    reading.add_argument("--which", default="best", choices=["best", "last"])
    reading.add_argument("--side", default="eval", choices=["eval", "train"])
    device_flag(reading)
    reading.add_argument("--run", help="the named training run to score (default: the head's own)")
    reading.add_argument(
        "--regime",
        default="640x360ss2",
        metavar="WxHssN",
        help="the geometry to read the pictures at (default: 640x360ss2, the deploy view). "
        "Anything else writes scores<regime>.jsonl beside the canonical read",
    )
    reading.set_defaults(handler=head_score)

    auditing = with_head(
        steps.add_parser(
            "audit",
            help="prove a run's record and its checkpoint are one trajectory",
            description=(
                "Two readings, and only the second settles anything. The clock reading "
                "compares wall_seconds against the sum of the epoch seconds and says what "
                "that can prove — which is less than it looks, because the wall starts "
                "after a resume loads and the history does not. The re-score reads the "
                "run's own selection slice back through its checkpoint and reproduces the "
                "record's best epoch, which needs no log and no clock. Writes audit.json "
                "beside the record."
            ),
        )
    )
    auditing.add_argument("--which", default="best", choices=["best", "last"])
    device_flag(auditing)
    auditing.add_argument("--run", help="the named training run to audit (default: the head's own)")
    auditing.set_defaults(handler=head_audit)

    flooring = steps.add_parser(
        "floor",
        help="fit a finished-render head's release floor off its own labels",
        description=(
            "Score every labeled picture of this head's corpus through the SHIPPED "
            "artifact, fit P(the human said >=3) against the head's own P(>=3) as a "
            "monotone curve, and read the lowest score whose fitted agreement reaches a "
            "half. The floor is that crossing rounded UP. Writes the value with the head "
            "sha, the row count, a place-clustered bootstrap interval and a hash of both "
            "inputs — and changes no cut: `curation.floors` owns every height that acts, "
            "and moving one there is a decision somebody takes after reading this. Where "
            "the head already has an acting bar this is a TEST of it, and exits non-zero "
            "when the re-fit does not reproduce the standing number."
        ),
    )
    flooring.add_argument(
        "--head",
        required=True,
        choices=sorted(FINISHED_HEADS),
        help="which finished-render judge to fit",
    )
    device_flag(flooring)
    flooring.add_argument(
        "--bootstrap",
        type=int,
        default=release_floor_module.BOOTSTRAP,
        help=f"resamples in the place-clustered interval "
        f"(default: {release_floor_module.BOOTSTRAP}; 0 to skip it)",
    )
    flooring.set_defaults(handler=head_floor)

    judging_step = with_head(
        steps.add_parser(
            "accept",
            help="read a trained head against the pre-registered bar",
            description=(
                "The bar comes from the file and nothing here may invent one. Exits non-zero "
                "only on FAIL; BORDERLINE is a real answer and means the population could not "
                "resolve the question with one seed."
            ),
        )
    )
    judging_step.add_argument(
        "--run",
        action="append",
        help="a named run to judge (repeatable). More than one is the pre-registered "
        "escalation: each cutpoint is read on the MEDIAN run by its own statistic",
    )
    judging_step.set_defaults(handler=head_accept)

    shipping = with_head(
        steps.add_parser(
            "ship",
            help="stage the half-precision artifact and its manifest entry",
            description=(
                "Halves the weights, proves the artifact re-reads bit-identically, checks the "
                "shipped head still orders the evaluation side the same way, hashes what was "
                "checked, and writes the manifest entry. Creating the release is a person's "
                "step."
            ),
        )
    )
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    device_flag(shipping)
    shipping.add_argument("--run", help="the named training run to ship (default: the head's own)")
    shipping.add_argument(
        "--force", action="store_true", help="ship a head whose acceptance read failed"
    )
    shipping.set_defaults(handler=head_ship)
