"""`renders`: the finished-render judges, their doses, deploys and grades."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fractal_wallpapers.cli.common import (
    device_flag,
    resolve_output,
)


def renders_plan(args: argparse.Namespace) -> int:
    """Turn a finished-render store into the pictures a build has to make."""
    from collections import Counter

    from fractal_wallpapers.models import renders

    jobs = renders.plan(args.head, seed=args.seed)
    path = renders.write_plan(args.head, jobs, seed=args.seed)
    print(
        json.dumps(
            {
                "head": args.head,
                "pictures": len(jobs),
                "seed": args.seed,
                "locations": len({json.dumps([j["family"], j["viewport"]]) for j in jobs}),
                "batches": dict(sorted(Counter(job["batch"] for job in jobs).items())),
                "modes": dict(sorted(Counter(job["mode"] for job in jobs).items())),
                "scores": dict(sorted(Counter(job["score"] for job in jobs).items())),
                "wrote": str(path),
            },
            indent=2,
        )
    )
    return 0


def renders_default_workers() -> int:
    """The render pool, read off the module rather than restated in a help string."""
    from fractal_wallpapers.models import renders

    return renders.DEFAULT_WORKERS


def renders_build(args: argparse.Namespace) -> int:
    """Render every picture of the plan, skipping the ones already on disk."""
    from fractal_wallpapers.models import renders

    report = renders.build(args.head, limit=args.limit, workers=args.workers)
    renders.build_record_path(args.head).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, indent=2))
    return 0


def renders_decode(args: argparse.Namespace) -> int:
    """Decode every crop of one head's cache once and keep the array beside it."""
    from fractal_wallpapers.models import renders

    report = renders.decode(args.head, limit=args.limit)
    print(json.dumps(report, indent=2))
    return 0


def renders_dose_plan(args: argparse.Namespace) -> int:
    """Every dose point's training side on every fold, before anything is fitted."""
    from fractal_wallpapers.models import render_dose, render_folds

    folds = [int(value) for value in args.folds.split(",")]
    points = args.points.split(",") if args.points else None
    try:
        document = render_dose.plan(folds, points)
    except (render_folds.FoldsError, render_dose.DoseError) as refusal:
        print(refusal)
        return 1
    path = render_dose.root() / "plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    for cell in document["points"]:
        print(
            f"{cell['point']:<12} {cell.get('cut') or ('matches ' + str(cell.get('matches'))):<12} "
            f"mean train {cell['mean_train']:8.1f}  mean strange fours "
            f"{cell['mean_strange_fours']:6.1f}  holdout {cell['holdout_rows']}"
        )
    print(f"wrote {path}")
    return 0


def renders_dose_fit(args: argparse.Namespace) -> int:
    """Fit the incumbent recipe on one dose point and one fold."""
    from fractal_wallpapers.models import render_dose, render_folds, render_train

    try:
        record = render_dose.fit(args.point, args.fold, device=args.device, epochs=args.epochs)
    except (
        render_folds.FoldsError,
        render_dose.DoseError,
        render_train.TrainingError,
    ) as refusal:
        print(refusal)
        return 1
    wanted = ("run", "best_epoch", "wall_seconds")
    print(json.dumps({key: record[key] for key in wanted if key in record}, indent=2))
    return 0


def renders_dose_read(args: argparse.Namespace) -> int:
    """Read one dose point's held-out rows through its own checkpoint."""
    from fractal_wallpapers.models import render_dose, render_folds

    try:
        record = render_dose.read_out_of_fold(args.point, args.fold, device=args.device)
    except (render_folds.FoldsError, render_dose.DoseError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(record, indent=2))
    return 0


def renders_dose_curve(args: argparse.Namespace) -> int:
    """The whole curve: every declared readout at every point, against one anchor."""
    from fractal_wallpapers.models import render_dose, render_folds

    folds = [int(value) for value in args.folds.split(",")] if args.folds else None
    points = args.points.split(",") if args.points else None
    try:
        path, document = render_dose.write_curve(points, folds, args.reference)
    except (render_folds.FoldsError, render_dose.DoseError) as refusal:
        print(refusal)
        return 1
    for cell in document["points"]:
        primary = cell["primary"]
        if primary.get("delta") is None:
            continue
        print(
            f"{cell['point']:<12} primary n {primary['n']:4d} (+{primary['positives']}) "
            f"{primary['candidate']:.4f}  delta vs {document['reference']} "
            f"{primary['delta']:+.4f} [{primary['lo']:+.4f}, {primary['hi']:+.4f}]"
        )
    print(f"wrote {path}")
    return 0


def renders_deploy_split(args: argparse.Namespace) -> int:
    """What one seed's holdout holds, before anything is fitted on it."""
    from fractal_wallpapers.models import render_deploy, render_folds

    band = args.band or render_deploy.BAND
    try:
        path, split = render_deploy.write_split(args.seed, band=band)
    except (render_folds.FoldsError, render_deploy.DeployError) as refusal:
        print(refusal)
        return 1
    print(json.dumps({k: v for k, v in split.items() if k != "population"}, indent=2))
    print(f"wrote {path}")
    return 0


def renders_deploy_fit(args: argparse.Namespace) -> int:
    """Train one seed of the head that ships: the incumbent recipe, the new rule."""
    from fractal_wallpapers.models import render_deploy, render_folds, render_train

    try:
        record = render_deploy.fit(
            args.seed,
            device=args.device,
            epochs=args.epochs,
            rule=args.rule,
            band=args.band or render_deploy.BAND,
            workers=args.workers,
        )
    except (
        render_folds.FoldsError,
        render_deploy.DeployError,
        render_train.TrainingError,
    ) as refusal:
        print(refusal)
        return 1
    wanted = ("run", "best_epoch", "best_selection_objective", "wall_seconds", "stopped_early")
    print(json.dumps({key: record[key] for key in wanted if key in record}, indent=2))
    return 0


def renders_deploy_choose(args: argparse.Namespace) -> int:
    """The seeds' epoch tables side by side, and the one that ships."""
    from fractal_wallpapers.models import render_deploy

    seeds = (
        tuple(int(part) for part in args.seeds.split(",") if part.strip())
        if args.seeds
        else render_deploy.SEEDS
    )
    try:
        path, document = render_deploy.write_choice(seeds, band=args.band or render_deploy.BAND)
    except render_deploy.DeployError as refusal:
        print(refusal)
        return 1
    for curve in document["curves"]:
        print(
            f"seed {curve['seed']}  epochs run {curve['epochs_run']} of {curve['of_epochs']}  "
            f"chose epoch {curve['best_epoch']} at {curve['chosen_objective']:.4f}  "
            f"({curve['wall_seconds']:.0f}s)"
        )
    ships = document["ships"]
    print(
        f"ships: seed {ships['seed']} ({ships['run']}) epoch {ships['epoch']} at "
        f"{ships['chosen_objective']:.4f}; chosen epochs {document['chosen_epochs']} "
        f"spread {document['epoch_spread']}"
    )
    print(f"wrote {path}")
    return 0


def renders_grade_split(args: argparse.Namespace) -> int:
    """What one fold's split holds, before anything is fitted on it."""
    from fractal_wallpapers.models import render_folds, render_grade

    try:
        _rows, _pictures, split = render_grade.sides_for(args.fold)
    except (render_folds.FoldsError, render_grade.GradingError) as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: value for key, value in split.items() if key != "population"}, indent=2))
    return 0


def renders_grade_fit(args: argparse.Namespace) -> int:
    """Fit one arm on one fold at one seed, under both stopping rules at once."""
    from fractal_wallpapers.models import render_folds, render_grade, render_train

    try:
        record = render_grade.fit(
            args.arm, args.fold, args.seed, device=args.device, epochs=args.epochs
        )
    except (
        render_folds.FoldsError,
        render_grade.GradingError,
        render_train.TrainingError,
    ) as refusal:
        print(refusal)
        return 1
    print(
        json.dumps(
            {key: value for key, value in record.items() if key != "history"},
            indent=2,
            default=str,
        )
    )
    return 0


def renders_grade_read(args: argparse.Namespace) -> int:
    """Read one run's held-out rows through each stopping rule's own checkpoint."""
    from fractal_wallpapers.models import render_folds, render_grade

    rules = [args.rule] if args.rule else sorted(render_grade.CHECKPOINTS)
    reports = []
    try:
        for rule in rules:
            reports.append(
                render_grade.read_out_of_fold(
                    args.arm, args.fold, args.seed, rule=rule, device=args.device
                )
            )
    except (render_folds.FoldsError, render_grade.GradingError) as refusal:
        print(refusal)
        return 1
    print(json.dumps(reports, indent=2))
    return 0


def renders_grade_readout(args: argparse.Namespace) -> int:
    """Leg 1's whole table: the primary comparison, the decomposition, the standings."""
    from fractal_wallpapers.models import render_folds, render_grade

    folds = [int(value) for value in args.folds.split(",")] if args.folds else None
    seeds = [int(value) for value in args.seeds.split(",")]
    try:
        document = render_grade.readout(seeds, folds)
    except (render_folds.FoldsError, render_grade.GradingError) as refusal:
        print(refusal)
        return 1
    path = render_grade.root() / "readout.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    # The PRIMARY is the refit rank key's ordering, pooled over both kinds; the
    # judge's own strange-side column is printed under it and decides nothing.
    for comparison in document["comparisons"]:
        for name in ("primary", "motivating"):
            cell = comparison[name]
            if cell.get("delta") is None:
                continue
            print(
                f"{comparison['candidate']:>28} vs {comparison['reference']:<28} "
                f"{name:<11} n {cell['n']:4d} (+{cell['positives']}) "
                f"{cell['candidate']:.4f} vs {cell['reference']:.4f}  "
                f"delta {cell['delta']:+.4f} [{cell['lo']:+.4f}, {cell['hi']:+.4f}] "
                f"{cell['verdict']}"
            )
        print(f"{'':>28}    clears the bar: {comparison['clears_the_bar']}")
    print(f"wrote {path}")
    return 0


def renders_grade_crossovers(args: argparse.Namespace) -> int:
    """The isotonic crossovers off pooled out-of-fold predictions, at LABEL geometry."""
    from fractal_wallpapers.models import render_folds, render_grade

    folds = [int(value) for value in args.folds.split(",")] if args.folds else None
    try:
        rows = render_grade.pooled(args.arm, args.rule, args.seed, folds)
        document = render_grade.crossovers(rows, args.kind)
    except (render_folds.FoldsError, render_grade.GradingError) as refusal:
        print(refusal)
        return 1
    document = {
        **document,
        "arm": args.arm,
        "rule": args.rule,
        "seed": args.seed,
        "folds": folds if folds is not None else "every fold read",
    }
    path = render_grade.root() / f"crossovers_{args.arm}_{args.rule}_{args.kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    print(
        json.dumps(
            {key: value for key, value in document.items() if key != "per_mode_ge3"}, indent=2
        )
    )
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path}")
    return 0


def renders_grade_autopsy(args: argparse.Namespace) -> int:
    """The pictures the two readings rank furthest apart, both ways, as one page."""
    from fractal_wallpapers.models import render_folds, render_grade

    folds = [int(value) for value in args.folds.split(",")] if args.folds else None
    seeds = [int(value) for value in args.seeds.split(",")]
    candidate_arm, candidate_rule = args.candidate.split("@")
    reference_arm, reference_rule = args.reference.split("@")
    try:
        document = render_grade.disagreements(
            render_grade.reading(candidate_arm, candidate_rule, seeds, folds),
            render_grade.reading(reference_arm, reference_rule, seeds, folds),
            tier=args.tier,
            rows=args.rows or render_grade.AUTOPSY_ROWS,
        )
        path = render_grade.autopsy_sheet(
            document,
            (args.candidate, args.reference),
            Path(args.output),
            note=f"Seed-averaged over {seeds}.",
        )
    except (render_folds.FoldsError, render_grade.GradingError) as refusal:
        print(refusal)
        return 1
    print(
        json.dumps({key: value for key, value in document.items() if "above" not in key}, indent=2)
    )
    print(f"wrote {path}")
    return 0


def renders_verify(args: argparse.Namespace) -> int:
    """Compare regenerated pictures against the ones the verdicts were cast on."""
    from fractal_wallpapers.models import renders

    try:
        report = renders.verify(Path(args.source), args.head, sample=args.sample, seed=args.seed)
    except renders.RenderCacheError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def judge_preregister(args: argparse.Namespace) -> int:
    """Write a finished-render judge's bar, before the head that it judges exists."""
    from fractal_wallpapers.models import finished_acceptance

    path = finished_acceptance.prereg_path(args.head)
    if path.is_file() and not args.force:
        print(f"{path} already exists. A bar rewritten after the numbers are in is not a bar;")
        print("pass --force only if no head has been trained against this one yet.")
        return 1
    try:
        bar = finished_acceptance.preregister(args.head, Path(args.source))
    except finished_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bar, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bar, indent=2))
    return 0


def judge_train(args: argparse.Namespace) -> int:
    """Train the finished-render judge on the render cache.

    `render` is the shipped judge and trains over both label stores pooled; the
    two superseded per-kind judges still train from here, because a superseded
    run has to stay reproducible for as long as its records are readable.
    """
    from fractal_wallpapers.models import finished_train, render_train

    if args.head == render_train.HEAD:
        try:
            record = render_train.run(
                device=args.device,
                epochs=args.epochs,
                seed=args.seed,
                run_name=args.run,
                only=args.only,
                per_kind=args.two_head,
                backbone=args.backbone,
            )
        except render_train.TrainingError as refusal:
            print(refusal)
            return 1
        print(json.dumps({k: v for k, v in record.items() if k != "history"}, indent=2))
        return 0
    try:
        record = finished_train.run(
            args.head,
            device=args.device,
            epochs=args.epochs,
            seed=args.seed,
            run_name=args.run,
        )
    except finished_train.TrainingError as refusal:
        print(refusal)
        return 1
    print(json.dumps({key: record[key] for key in record if key != "history"}, indent=2))
    return 0


def judge_score(args: argparse.Namespace) -> int:
    """Score a side of the judge's corpus through a trained checkpoint.

    `render` reads BOTH label stores, because one judge answers for both kinds and
    its blind sheets are one per kind. `--kind` narrows it to one of them.
    """
    from fractal_wallpapers.models import finished_scoring, render_train

    if args.head == render_train.HEAD:
        kinds = [args.kind] if args.kind else list(render_train.KINDS)
        try:
            for kind in kinds:
                print(
                    json.dumps(
                        render_train.score(
                            kind, which=args.which, device=args.device, run_name=args.run
                        ),
                        indent=2,
                    )
                )
        except render_train.TrainingError as refusal:
            print(refusal)
            return 1
        return 0
    print(
        json.dumps(
            finished_scoring.run(
                args.head,
                which=args.which,
                side=args.side,
                device=args.device,
                into=args.run,
            ),
            indent=2,
        )
    )
    return 0


def judge_accept(args: argparse.Namespace) -> int:
    """Read a trained judge against its pre-registered bar.

    `render` is read against the non-inferiority bar its own band was registered
    under, which is a different document from the two superseded heads' — see
    [`fractal_wallpapers.models.render_acceptance`].
    """
    from fractal_wallpapers.models import finished_acceptance, render_train

    if args.head == render_train.HEAD:
        from fractal_wallpapers.models import render_acceptance

        try:
            report = render_acceptance.read(runs=args.run or None)
        except render_acceptance.ComparisonError as refusal:
            print(refusal)
            return 1
        path = render_acceptance.comparison_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(report, indent=2))
        return 0 if report["verdict"] != "FAIL" else 1

    try:
        report = finished_acceptance.read(args.head, runs=args.run or None)
    except finished_acceptance.AcceptanceError as refusal:
        print(refusal)
        return 1
    path = finished_acceptance.acceptance_path(args.head)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"] != "FAIL" else 1


def judge_ship(args: argparse.Namespace) -> int:
    """Stage a judge's half-precision artifact and its manifest entry."""
    from fractal_wallpapers.models import finished_acceptance, render_train, ship

    if args.head == render_train.HEAD:
        from fractal_wallpapers.models import render_acceptance

        verdict_path = render_acceptance.comparison_path()
        reading = "band_only_verdict"
    else:
        verdict_path = finished_acceptance.acceptance_path(args.head)
        reading = "verdict"
    if not verdict_path.is_file():
        print(f"{verdict_path} is missing: nothing has judged this head yet.")
        print("Run `fractal-wallpapers renders accept` first.")
        return 1
    report = json.loads(verdict_path.read_text(encoding="utf-8"))
    # The render judge is read BAND-ONLY, by Matt's standing ruling of 2026-08-23:
    # the per-seed conjunction runs one test per gated arm per seed and its
    # false-alarm size was never pre-stated, so it does not gate. The record
    # carries both readings and this is the one that ships.
    verdict = report.get("multiplicity", {}).get(reading, report["verdict"])
    if verdict == "FAIL" and not args.force:
        print(f"the acceptance read says {verdict}. Shipping a head that failed its own")
        print("pre-registered bar needs --force and a sentence about why.")
        return 1

    print(
        json.dumps(
            ship.stage(
                name=args.head, which=args.which, tag=args.tag, device=args.device, run=args.run
            ),
            indent=2,
        )
    )
    return 0


def judge_disagreements(args: argparse.Namespace) -> int:
    """Copy out the sheet rows the judge and a superseded head read most differently."""
    from fractal_wallpapers.models import render_acceptance

    try:
        report = render_acceptance.disagreements(
            run=args.run, per_kind=args.per_kind, out_dir=args.out_dir
        )
    except render_acceptance.ComparisonError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def judge_glance(args: argparse.Namespace) -> int:
    """Lay one batch's rows out under the candidate's ordering and the incumbent's."""
    from fractal_wallpapers.models import render_glance

    try:
        report = render_glance.write(
            batch=args.batch,
            run=args.run,
            path=resolve_output(args.out) if args.out else None,
            rows=args.rows if args.rows is not None else render_glance.ROWS,
            which=args.which,
            device=args.device,
        )
    except render_glance.GlanceError as refusal:
        print(refusal)
        return 1
    print(json.dumps(report, indent=2))
    return 0


def add_commands(subcommands) -> None:
    """The finished-render cache: plan the pictures, then make them."""
    caching = subcommands.add_parser(
        "renders",
        help="build the pictures a finished-render judge is trained on: plan, then render",
        description=(
            "A finished-render row records the recipe rather than the picture, so the "
            "pictures are regenerated here — every one of them, training and evaluation "
            "alike, through this repository's own coloring path. A head trained on one "
            "renderer's pictures and deployed against another's measures the difference "
            "between the two renderers."
        ),
    )
    steps = caching.add_subparsers(dest="step", required=True)

    planning = steps.add_parser(
        "plan",
        help="turn a store into the pictures a build has to make",
        description=(
            "One job per distinct picture: rows that share a place, a mode with its "
            "settings, a curve, a map and a recipe share a file. The plan is shuffled by a "
            "seed, so any prefix of it is a fair sample and a bounded rehearsal projects "
            "the whole build honestly."
        ),
    )
    planning.add_argument("--head", required=True, help="which judge's corpus")
    planning.add_argument("--seed", type=int, default=0, help="the shuffle's seed (default: 0)")
    planning.set_defaults(handler=renders_plan)

    building = steps.add_parser(
        "build",
        help="render every picture of the plan",
        description=(
            "Resumable by construction: a picture already on disk is skipped before its "
            "field is iterated, and a file is named for a digest of its own recipe, so a "
            "re-planned build re-uses everything it already has. Progress goes to "
            "build.log as it runs."
        ),
    )
    building.add_argument("--head", required=True, help="which judge's corpus")
    building.add_argument("--limit", type=int, help="stop after this many jobs of the plan")
    building.add_argument(
        "--workers",
        type=int,
        default=renders_default_workers(),
        help=f"engines this build drives at once (default {renders_default_workers()}, this "
        "machine's render pool; 1 renders in this process). Each is spawned below normal "
        "priority whatever this is set to",
    )
    building.set_defaults(handler=renders_build)

    decoding = steps.add_parser(
        "decode",
        help="keep every crop's decoded pixels beside it, so the loader stops decoding",
        description=(
            "The training loop is data-loading bound — the GPU sits near a tenth of its "
            "capacity while a worker decodes a 1280x720 JPEG — and the decode is about "
            "twelve of a thirty-millisecond example. This writes each crop's own pixels "
            "beside it once. Exactly the JPEG's pixels: no resize, no smaller "
            "intermediate, so a run over the cache and a run over the crops are the same "
            "run. About 3 GB a thousand pictures, in the ignored tree."
        ),
    )
    decoding.add_argument("--head", required=True, help="which judge's cache")
    decoding.add_argument("--limit", type=int, help="stop after this many crops")
    decoding.set_defaults(handler=renders_decode)

    checking = steps.add_parser(
        "verify",
        help="compare regenerated pictures against the ones the verdicts were cast on",
        description=(
            "The whole coloring recipe is reproduced from a record rather than shared, and "
            "every knob of it is a way to be quietly wrong: the picture still looks like a "
            "fractal and the verdict is about something else. Compares the pairs directly "
            "against the only honest yardstick — what re-compressing the judged picture "
            "costs. Needs the source project present."
        ),
    )
    checking.add_argument("--head", required=True, help="which judge's corpus")
    checking.add_argument("--source", required=True, help="the source repository's root")
    checking.add_argument("--sample", type=int, default=60, help="how many pairs to compare")
    checking.add_argument("--seed", type=int, default=0, help="the sample's seed (default: 0)")
    checking.set_defaults(handler=renders_verify)

    deploying = steps.add_parser(
        "deploy",
        help="train the head that ships: three seeds, one holdout, one artifact",
        description=(
            "Three training runs on the whole corpus under the incumbent recipe, differing "
            "only in the seed, with the epoch chosen by average precision at >=3 over the "
            "non-pinned part of a plain random 80/20 holdout drawn over lineages. The "
            "holdout's only job is to stop the run; nothing here is a comparison. The "
            "artifact of the seed whose chosen epoch scores best is the one that ships."
        ),
    )
    deployings = deploying.add_subparsers(dest="deploy_step", required=True)

    deploy_split = deployings.add_parser(
        "split",
        help="what one seed's holdout holds, before anything is fitted on it",
    )
    deploy_split.add_argument("--seed", type=int, default=0, help="which seed's split")
    deploy_split.add_argument(
        "--band",
        # The default lives in the module and is resolved in the handler, not
        # here: this parser is built on the base install, where the module's
        # import graph is not available. `tests/test_base_install.py` says so.
        help="which pass of this module the run belongs to (default: the module's, "
        "`deploy`, which is the pass that shipped weights-v5). One band is three seeds "
        "over the corpus as it stood, and the band is in every run name so a later pass "
        "does not land on an earlier one's checkpoints",
    )
    deploy_split.set_defaults(handler=renders_deploy_split)

    deploy_fitting = deployings.add_parser(
        "fit",
        help="train one seed of the head that ships",
    )
    deploy_fitting.add_argument("--seed", type=int, required=True, help="which seed's split")
    device_flag(deploy_fitting)
    deploy_fitting.add_argument("--epochs", type=int, help="override the epoch ceiling")
    deploy_fitting.add_argument(
        "--workers",
        type=int,
        help="loader subprocesses (default: the recipe's). An I/O knob and not a recipe "
        "key, written into the run's config like every other value. Each one re-imports "
        "torch on Windows, so this is what a box with no commit charge left is given",
    )
    deploy_fitting.add_argument(
        "--rule",
        default="average_precision",
        choices=("average_precision", "auc"),
        help="the stopping rule; AUC is the stated fallback",
    )
    deploy_fitting.add_argument(
        "--band",
        # The default lives in the module and is resolved in the handler, not
        # here: this parser is built on the base install, where the module's
        # import graph is not available. `tests/test_base_install.py` says so.
        help="which pass of this module the run belongs to (default: the module's, "
        "`deploy`, which is the pass that shipped weights-v5). One band is three seeds "
        "over the corpus as it stood, and the band is in every run name so a later pass "
        "does not land on an earlier one's checkpoints",
    )
    deploy_fitting.set_defaults(handler=renders_deploy_fit)

    deploy_choosing = deployings.add_parser(
        "choose",
        help="the seeds' epoch tables side by side, and the one that ships",
    )
    deploy_choosing.add_argument("--seeds", help="which seeds, comma separated (default: all)")
    deploy_choosing.add_argument(
        "--band",
        # The default lives in the module and is resolved in the handler, not
        # here: this parser is built on the base install, where the module's
        # import graph is not available. `tests/test_base_install.py` says so.
        help="which pass of this module the run belongs to (default: the module's, "
        "`deploy`, which is the pass that shipped weights-v5). One band is three seeds "
        "over the corpus as it stood, and the band is in every run name so a later pass "
        "does not land on an earlier one's checkpoints",
    )
    deploy_choosing.set_defaults(handler=renders_deploy_choose)

    dosing = steps.add_parser(
        "dose",
        help="one recipe on increasing amounts of label data, read on a holdout that does not move",
        description=(
            "A dose curve rather than an arms comparison. The incumbent recipe and the "
            "incumbent stopping rule are refit on the corpus as it stood at each of several "
            "batch-registration dates, and on random lineage draws of the grown corpus "
            "matched to the pre-growth row count. Every point is read on the same held-out "
            "rows. Nothing here adopts anything."
        ),
    )
    dosings = dosing.add_subparsers(dest="dose_step", required=True)

    dose_planning = dosings.add_parser(
        "plan",
        help="every dose point's training side on every fold, before anything is fitted",
        description=(
            "The dose axis in rows, the strange fours beside it, and the holdout that does "
            "not move. What a launch is priced off."
        ),
    )
    dose_planning.add_argument(
        "--folds", default="0,1,2,3,4", help="which parts of the deal, comma separated"
    )
    dose_planning.add_argument("--points", help="which dose points, comma separated (default: all)")
    dose_planning.set_defaults(handler=renders_dose_plan)

    dose_fitting = dosings.add_parser(
        "fit",
        help="fit the incumbent recipe on one dose point and one fold",
        description=(
            "The trainer every band on the record used, over the deal's own folds, with the "
            "rows outside the dose held out of training alongside the fold's own holdout."
        ),
    )
    dose_fitting.add_argument("--point", required=True, help="which dose point")
    dose_fitting.add_argument("--fold", type=int, required=True, help="which part of the deal")
    device_flag(dose_fitting)
    dose_fitting.add_argument("--epochs", type=int, help="override the epoch ceiling")
    dose_fitting.set_defaults(handler=renders_dose_fit)

    dose_reading = dosings.add_parser(
        "read",
        help="read one dose point's held-out rows through its own checkpoint",
        description=(
            "One row a picture, carrying its whole join and the dose point that produced it. "
            "Every point writes the same rows, which is what lets the curve be read paired."
        ),
    )
    dose_reading.add_argument("--point", required=True, help="which dose point")
    dose_reading.add_argument("--fold", type=int, required=True, help="which part of the deal")
    device_flag(dose_reading)
    dose_reading.set_defaults(handler=renders_dose_read)

    dose_curve = dosings.add_parser(
        "curve",
        help="every declared readout at every point, against one anchor",
        description=(
            "The rank key refit per point, the strange and smooth AUCs, and the sparse-mode "
            "slice — each as a paired difference against the pre-growth point on identical "
            "rows. No level is claimed anywhere."
        ),
    )
    dose_curve.add_argument(
        "--points", help="which dose points, comma separated (default: all read)"
    )
    dose_curve.add_argument("--folds", help="which folds, comma separated (default: all read)")
    dose_curve.add_argument(
        "--reference", default="era_0824", help="the anchor every difference is taken against"
    )
    dose_curve.set_defaults(handler=renders_dose_curve)

    grading = steps.add_parser(
        "grade",
        help="grade two arms on a statistic that can resolve, over the folds already dealt",
        description=(
            "The screen's folds re-used rather than re-dealt, graded on AUC(>=4) over every "
            "strange row a person scored 3 or 4 rather than on the band-restricted slice "
            "that could not resolve. Two arms — the shipped recipe and the same recipe at "
            "twice the input resolution — and two stopping rules read off one run each. "
            "Nothing here adopts anything."
        ),
    )
    gradings = grading.add_subparsers(dest="grade_step", required=True)

    splitting = gradings.add_parser(
        "split",
        help="what one fold's split holds, before anything is fitted on it",
        description=(
            "Holdout, training side and stop slice, with the stop slice's own draw. The "
            "slice is 20% of the training side's LINEAGE GROUPS rather than the trainer's "
            "share of its places, and it comes out of the training side and never out of "
            "the graded holdout."
        ),
    )
    splitting.add_argument("--fold", type=int, required=True, help="which part of the deal")
    splitting.set_defaults(handler=renders_grade_split)

    grade_fitting = gradings.add_parser(
        "fit",
        help="fit one arm on one fold at one seed",
        description=(
            "Runs the shipped trainer over this fold's split and keeps TWO checkpoints: the "
            "epoch the pooled cutpoint cross-entropy likes and the epoch stop-slice "
            "AUC(>=4) likes. One run, read twice, so the second stopping rule costs no "
            "training."
        ),
    )
    grade_fitting.add_argument("--arm", required=True, help="which arm: A or B")
    grade_fitting.add_argument("--fold", type=int, required=True, help="which part of the deal")
    grade_fitting.add_argument("--seed", type=int, required=True, help="the run's seed")
    device_flag(grade_fitting)
    grade_fitting.add_argument("--epochs", type=int, help="override the epoch ceiling")
    grade_fitting.set_defaults(handler=renders_grade_fit)

    grade_reading = gradings.add_parser(
        "read",
        help="read a run's held-out rows through each stopping rule's checkpoint",
        description=(
            "Every held-out row scored by the one model that never saw its lineage, once "
            "per stopping rule. Omit --rule for both."
        ),
    )
    grade_reading.add_argument("--arm", required=True, help="which arm")
    grade_reading.add_argument("--fold", type=int, required=True, help="which part of the deal")
    grade_reading.add_argument("--seed", type=int, required=True, help="the run's seed")
    grade_reading.add_argument("--rule", help="one stopping rule, or both if omitted")
    device_flag(grade_reading)
    grade_reading.set_defaults(handler=renders_grade_read)

    grade_readout = gradings.add_parser(
        "readout",
        help="the primary comparison, the decomposition and the standings",
        description=(
            "Arm B under the AUC stopping rule against arm A under the shipped one — the "
            "true incumbent — on the seed-AVERAGED reading, plus the two descriptive "
            "comparisons that separate the stopping-rule effect from the resolution effect."
        ),
    )
    grade_readout.add_argument("--seeds", default="0,1", help="the seed band, comma separated")
    grade_readout.add_argument("--folds", help="which folds, comma separated (default: all read)")
    grade_readout.set_defaults(handler=renders_grade_readout)

    grade_crossovers = gradings.add_parser(
        "crossovers",
        help="the isotonic P(>=3) and P(>=4) crossovers, at LABEL geometry",
        description=(
            "Isotonic regression of P(the human agreed) against the head's own probability, "
            "over pooled out-of-fold predictions. NOT seating floors: these are fitted at "
            "label geometry, the judge is not regime-robust, and re-scoring at shipping "
            "geometry is a separate act."
        ),
    )
    grade_crossovers.add_argument("--arm", required=True, help="which arm")
    grade_crossovers.add_argument("--rule", required=True, help="which stopping rule")
    grade_crossovers.add_argument("--seed", type=int, default=0, help="the run's seed")
    grade_crossovers.add_argument("--kind", default="strange_render", help="which store")
    grade_crossovers.add_argument("--folds", help="which folds, comma separated (default: all)")
    grade_crossovers.set_defaults(handler=renders_grade_crossovers)

    grade_autopsy = gradings.add_parser(
        "autopsy",
        help="the pictures the two readings rank furthest apart, both ways",
        description=(
            "Numbers alone do not close a comparison between two judges. This is the two "
            "halves an eye has to look at: the human fours one reading ranks far above the "
            "other, and the same the other way. Ranked by percentile within the strange "
            "held-out population, because the two probability scales differ by construction."
        ),
    )
    grade_autopsy.add_argument("--candidate", required=True, help="arm@rule, e.g. B@...")
    grade_autopsy.add_argument("--reference", required=True, help="arm@rule")
    grade_autopsy.add_argument("--seeds", default="0,1", help="the seed band, comma separated")
    grade_autopsy.add_argument("--folds", help="which folds, comma separated (default: all read)")
    grade_autopsy.add_argument("--tier", type=int, default=4, help="which human verdict")
    grade_autopsy.add_argument(
        "--rows",
        type=int,
        default=None,
        help="how many pictures per half (default: render_grade.AUTOPSY_ROWS)",
    )
    grade_autopsy.add_argument("--output", required=True, help="where the page is written")
    grade_autopsy.set_defaults(handler=renders_grade_autopsy)

    registering = steps.add_parser(
        "preregister",
        help="write a judge's bar, before there is a head to judge against it",
        description=(
            "Builds the bar out of the source project's committed reading of this judge's "
            "blind sheet — the only labels on it that no head suggested — and out of how "
            "precisely that sheet can tell two heads apart at all. Copies those figures in "
            "so the bar stays re-readable without the other repository, and refuses to "
            "overwrite a bar that already exists."
        ),
    )
    registering.add_argument("--head", required=True, help="which judge")
    registering.add_argument("--source", required=True, help="the source repository's root")
    registering.add_argument(
        "--force", action="store_true", help="overwrite a bar no head has been judged against"
    )
    registering.set_defaults(handler=judge_preregister)

    training = steps.add_parser(
        "train",
        help="train a judge on the built render cache",
        description=(
            "One epoch is one pass over pictures, not over places: a place that carries a "
            "dozen colorings contributes a dozen examples, because the differences between "
            "them are what is being learned. The sampler equalizes places so that a "
            "heavily-coloured one is still worth one place's gradient."
        ),
    )
    training.add_argument("--head", required=True, help="which judge")
    device_flag(training)
    training.add_argument("--epochs", type=int, help="override the recipe's epoch count")
    training.add_argument("--seed", type=int, help="override the recipe's seed")
    training.add_argument(
        "--only",
        help="render only: train the ABLATION instead — one kind's share of exactly the "
        "pooled split, under exactly this recipe. The arm that separates pooling from what "
        "pooling changed alongside it",
    )
    training.add_argument(
        "--two-head",
        action="store_true",
        help="render only: one backbone, TWO last layers — one ordinal head per kind. Shares "
        "every representation and lets the kinds keep two scales, at the cost of having to "
        "be told which kind it is reading",
    )
    training.add_argument(
        "--backbone",
        help="render only: train at a backbone other than the recipe's pinned one. The one "
        "value a joint judge cannot inherit, so the choice is worth being able to re-ask",
    )
    training.add_argument(
        "--run",
        help="name this run, so its checkpoint and records land in their own directory. "
        "What a seed band is made of; omit for the judge's one run",
    )
    training.set_defaults(handler=judge_train)

    reading = steps.add_parser(
        "score",
        help="score one side of a judge's corpus through a trained checkpoint",
        description=(
            "A score row carries its whole join — the place and the recipe that made the "
            "picture — plus the picture's own name, which is a digest of that recipe."
        ),
    )
    reading.add_argument("--head", required=True, help="which judge")
    reading.add_argument(
        "--kind",
        help="render only: read one label store's sheet rather than both",
    )
    reading.add_argument("--which", default="best", choices=["best", "last"])
    reading.add_argument("--side", default="eval", choices=["eval", "train"])
    device_flag(reading)
    reading.add_argument("--run", help="the named training run to score")
    reading.set_defaults(handler=judge_score)

    judging = steps.add_parser(
        "accept",
        help="read a trained judge against its pre-registered bar",
        description=(
            "The bar comes from the file and nothing here may invent one. Exits non-zero "
            "only on FAIL; BORDERLINE is a real answer and means the sheet could not "
            "resolve the question with one seed."
        ),
    )
    judging.add_argument("--head", required=True, help="which judge")
    judging.add_argument(
        "--run",
        action="append",
        help="a named run to judge (repeatable). More than one is the pre-registered "
        "escalation: the boundary is read on the MEDIAN run by its own statistic",
    )
    judging.set_defaults(handler=judge_accept)

    shipping = steps.add_parser(
        "ship",
        help="stage a judge's half-precision artifact and its manifest entry",
        description=(
            "Halves the weights, proves the artifact re-reads bit-identically, checks the "
            "shipped judge still orders its blind sheet the same way, hashes what was "
            "checked, and writes the manifest entry. Creating the release is a person's step."
        ),
    )
    shipping.add_argument("--head", required=True, help="which judge")
    shipping.add_argument("--which", default="best", choices=["best", "last"])
    shipping.add_argument("--tag", default="weights-v1", help="the release tag to name")
    device_flag(shipping)
    shipping.add_argument("--run", help="the named training run to ship")
    shipping.add_argument(
        "--force", action="store_true", help="ship a judge whose acceptance read failed"
    )
    shipping.set_defaults(handler=judge_ship)

    glancing = steps.add_parser(
        "glance",
        help="lay one batch's rows out under a candidate's ordering and the shipped one's",
        description=(
            "The read a band cannot give. A correction batch is anchored and train-side, so "
            "no rate quoted off it is a rate — what a person can still ask is whether the "
            "pictures come out in a better order. Two columns of the same rows, the pair of "
            "scores under each, and the rows that moved furthest either way. Lands in "
            "scratch/, decides nothing, and re-renders nothing."
        ),
    )
    glancing.add_argument(
        "--batch", required=True, help="the batch to lay out; a prefix, so a contrast arm comes too"
    )
    glancing.add_argument("--run", required=True, help="the candidate run to order by")
    glancing.add_argument("--which", default="best", choices=["best", "last"])
    # The default lives in the module and is resolved in the handler, not here:
    # this parser is built on the base install, where the module's import graph is
    # not available. `tests/test_base_install.py` is what says so.
    glancing.add_argument("--rows", type=int, help="rows per column (default: the module's, 12)")
    glancing.add_argument("--out", help="where the page lands (default: scratch/)")
    device_flag(glancing)
    glancing.set_defaults(handler=judge_glance)

    drawing = steps.add_parser(
        "disagreements",
        help="copy out the sheet rows the judge and a superseded head read most differently",
        description=(
            "Admissions and rejects, per kind: the rows where the shipped judge's "
            "probability at that sheet's own boundary sits furthest above the superseded "
            "head's, and the rows where it sits furthest below. Lands in scratch/, which is "
            "disposable."
        ),
    )
    drawing.add_argument("--run", help="the training run to read (default: the band's median)")
    drawing.add_argument(
        "--per-kind", type=int, default=6, help="rows per direction per kind (default: 6)"
    )
    drawing.add_argument("--out-dir", help="where the pictures land (default: scratch/)")
    drawing.set_defaults(handler=judge_disagreements)
