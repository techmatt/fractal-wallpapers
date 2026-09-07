"""`gallery-grade`: the fine-tier head, from the ledger join to the band's pick.

Five verbs and they run in order. `population` and `split` are cheap and are
written down, because every arm has to be fitted on one join and read on one
slice; `fit` and `band` are the only ones that cost a GPU — `band` being `fit`
over the whole grid, one run at a time — and `read` costs nothing at all.
"""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import device_flag


def gallery_grade(args: argparse.Namespace) -> int:
    """The fine-tier head: an order inside the render judge's own top."""
    from fractal_wallpapers.models import gallery_grade_train as trainer

    if args.what == "population":
        path, record = trainer.write_population()
        print(json.dumps(record, indent=1))
        print(f"wrote {path}")
        return 0

    if args.what == "split":
        path, record = trainer.write_split(seed=args.seed)
        print(json.dumps({k: v for k, v in record.items() if not k.endswith("_of_row")}, indent=1))
        print(f"wrote {path}")
        return 0

    if args.what == "fit":
        record = trainer.fit(
            arm=args.arm,
            seed=args.seed,
            device=args.device,
            epochs=args.epochs,
            workers=args.workers,
        )
        print(
            f"{record['run']}: epoch {record['best_epoch']}  "
            f"AP(>=3) {-record['best_selection_objective']:.4f}  "
            f"({record['wall_seconds']}s)"
        )
        return 0

    if args.what == "band":
        outcome = trainer.fit_band(device=args.device, epochs=args.epochs, workers=args.workers)
        print(f"fitted {len(outcome['fitted'])}, already there {len(outcome['already_there'])}")

    path, record = trainer.write_band()
    print(json.dumps(record, indent=1))
    print(f"wrote {path}")
    return 0


def add_commands(subcommands) -> None:
    from fractal_wallpapers.models.gallery_grade_train import ARMS, SPLIT_SEED

    group = subcommands.add_parser(
        "gallery-grade",
        help="the fine-tier head: an order inside the render judge's own flat top",
        description=(
            "A separate network, same architecture as the shipped render judge and "
            "initialised from its weights-v6 artifact, fitted on the gallery-grade store's "
            "1..4 verdicts at the ledger's 640x360 candidate geometry. It is STAGE TWO of a "
            "cascade behind p_ge4 and its output is undefined on a row that never cleared "
            "the gate — never a pool-wide ranker. Nothing here ships or is wired into "
            "selection."
        ),
    )
    steps = group.add_subparsers(dest="what", required=True)

    resolving = steps.add_parser(
        "population",
        help="join every graded row to the ledger row whose picture it was cast about",
        description=(
            "One streaming pass over the candidate ledger, cached under the regenerable "
            "tree so that every arm is fitted on one join. A row that will not resolve is "
            "dropped and counted with its reason rather than repaired."
        ),
    )
    resolving.set_defaults(handler=gallery_grade)

    splitting = steps.add_parser(
        "split",
        help="draw the 80/20 over lineages, filled to balance the three sittings",
        description=(
            "Lineages are the hard constraint and go whole; inside that the holdout is "
            "filled by whichever remaining lineage most reduces the per-batch shortfall, "
            "because the three sittings disagree at p = 2.6e-05. ONE seed for every arm and "
            "every seed of the band: an AP read on two different slices is not a comparison "
            "of two heads."
        ),
    )
    splitting.add_argument(
        "--seed",
        type=int,
        default=SPLIT_SEED,
        help=f"the draw's seed (default {SPLIT_SEED}, and moving it re-splits the whole band)",
    )
    splitting.set_defaults(handler=gallery_grade)

    fitting = steps.add_parser(
        "fit",
        help="fit one arm at one seed",
        description=(
            "The shipped judge's recipe unchanged — twenty epochs, patience six, the epoch "
            "chosen on stopping-slice AP(>=3) with AUC(>=3) as the fallback. ONE RUN AT A "
            "TIME on this box: a trainer commits about 4 GiB and every Windows loader worker "
            "re-imports torch for a gigabyte more."
        ),
    )
    fitting.add_argument(
        "--arm",
        required=True,
        choices=sorted(ARMS),
        # `%` doubled because argparse `%`-expands a help string as it prints it,
        # and an arm that says "49% of this backbone" is a `% o` conversion that
        # takes down this verb's whole `--help` and nothing else. The arms' own
        # sentences are prose and go into every record unescaped; the doubling
        # belongs here, at the one place argparse reads them.
        help="how much trunk takes a gradient: "
        + "; ".join(f"{k} — {v['says']}" for k, v in sorted(ARMS.items())).replace("%", "%%"),
    )
    fitting.add_argument("--seed", type=int, default=0, help="the training seed (default 0)")
    device_flag(fitting)
    fitting.add_argument("--epochs", type=int, help="override the recipe's epoch ceiling")
    fitting.add_argument("--workers", type=int, help="override the recipe's loader workers")
    fitting.set_defaults(handler=gallery_grade)

    banding = steps.add_parser(
        "band",
        help="fit every run of the grid that is not already on disk, one at a time",
        description=(
            "Sequential and not a knob: this box's commit charge cannot afford two "
            "trainers, and what that produces is a CUDA DLL failing to load, which reads "
            "as a machine fault rather than as scheduling. A run whose metrics.json is "
            "already there is skipped, so a killed band is resumed by re-launching it."
        ),
    )
    device_flag(banding)
    banding.add_argument("--epochs", type=int, help="override the recipe's epoch ceiling")
    banding.add_argument("--workers", type=int, help="override the recipe's loader workers")
    banding.set_defaults(handler=gallery_grade)

    reading = steps.add_parser(
        "read",
        help="the band: every run that has been fitted, and the pick",
        description=(
            "The pick is by stopping-slice AP, which is the rule the epoch was chosen "
            "under — one statistic decides the epoch inside a run and the run inside the "
            "band, so nothing is selected on a number nothing was stopped on."
        ),
    )
    reading.set_defaults(handler=gallery_grade)


__all__ = ["add_commands", "gallery_grade"]
