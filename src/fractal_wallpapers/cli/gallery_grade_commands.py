"""`gallery-grade`: the fine-tier head, from the ledger join to the band's pick.

Seven verbs and they run in order. `population` and `split` are cheap and are
written down, because every arm has to be fitted on one join and read on one
slice. `preregister` writes the bar and has to run **before** any fit of its
band. `fit` and `band` are the only ones that cost a GPU — `band` being `fit`
over the whole grid, one run at a time. `read` and `accept` cost nothing.
"""

from __future__ import annotations

import argparse
import json

from fractal_wallpapers.cli.common import device_flag


def gallery_grade(args: argparse.Namespace) -> int:
    """The fine-tier head: an order inside the render judge's own top."""
    from fractal_wallpapers.models import gallery_grade_train as trainer

    if args.what == "population":
        path, record = trainer.write_population(corpus=args.corpus)
        print(json.dumps(record, indent=1))
        print(f"wrote {path}")
        return 0

    if args.what == "split":
        path, record = trainer.write_split(seed=args.seed, corpus=args.corpus)
        print(json.dumps({k: v for k, v in record.items() if not k.endswith("_of_row")}, indent=1))
        print(f"wrote {path}")
        return 0

    if args.what == "preregister":
        path, document = trainer.write_bar(
            band_name=args.band, corpus=args.corpus, recipe=args.recipe, force=args.force
        )
        print(json.dumps(document, indent=1))
        print(f"wrote {path}")
        return 0

    if args.what == "accept":
        path, document = trainer.acceptance(
            band_name=args.band, corpus=args.corpus, recipe=args.recipe
        )
        print(json.dumps(document, indent=1))
        print(f"wrote {path}")
        return 0 if document["verdict"] == "CLEARED" else 1

    if args.what == "score-pool":
        from fractal_wallpapers.curation import solve as solve_module

        arm, seeds, column = trainer.shipped_runs(
            band_name=args.band, corpus=args.corpus, recipe=args.recipe
        )
        candidates, _refused = solve_module.pool()
        record = trainer.score_pool(
            candidates,
            band=args.band,
            corpus=args.corpus,
            recipe=args.recipe,
            device=args.device,
        )
        print(
            json.dumps({**record, "picked": {"arm": arm, "seeds": seeds, "run": column}}, indent=1)
        )
        return 0

    if args.what == "fit":
        record = trainer.fit(
            arm=args.arm,
            seed=args.seed,
            band=args.band,
            corpus=args.corpus,
            recipe=args.recipe,
            device=args.device,
            epochs=args.epochs,
            workers=args.workers,
        )
        print(
            f"{record['run']}: epoch {record['best_epoch']}  "
            f"{record['stopping_rule']['ran_under']} "
            f"{trainer.selection_statistic(record):.4f}  "
            f"({record['wall_seconds']}s)"
        )
        return 0

    if args.what == "band":
        outcome = trainer.fit_band(
            band_name=args.band,
            corpus=args.corpus,
            recipe=args.recipe,
            device=args.device,
            epochs=args.epochs,
            workers=args.workers,
        )
        print(f"fitted {len(outcome['fitted'])}, already there {len(outcome['already_there'])}")

    path, record = trainer.write_band(band_name=args.band, corpus=args.corpus, recipe=args.recipe)
    print(json.dumps(record, indent=1))
    print(f"wrote {path}")
    return 0


def band_flag(parser, trainer_band: str, rules) -> None:
    """`--band`, which is the stopping rule the run is fitted under."""
    parser.add_argument(
        "--band",
        default=trainer_band,
        choices=sorted(rules),
        help=f"which stopping rule this run is fitted under (default {trainer_band})",
    )


def recipe_flag(parser, default: str, recipes) -> None:
    """`--recipe`, which is WHICH KNOBS — the third axis, beside rows and rule.

    On every verb that names a run, for `corpus_flag`'s reason: two arms fitted
    under different dropout are not two arms, and a bar, a band and a checkpoint
    all have to say which recipe they are about.
    """
    parser.add_argument(
        "--recipe",
        default=default,
        choices=sorted(recipes),
        help=(
            f"which knobs this run is fitted under (default {default}, the ADOPTED recipe): "
            + "; ".join(f"{k} — {v['says']}" for k, v in sorted(recipes.items()))
        ).replace("%", "%%"),
    )


def corpus_flag(parser, default: str, corpora) -> None:
    """`--corpus`, which is WHICH ROWS — a separate axis from `--band`'s rule.

    On **every** verb here, including the two that cost nothing, because a join,
    a split, a bar and a run all have to be about one set of rows and the only
    way to be sure of that is for each of them to say which.
    """
    parser.add_argument(
        "--corpus",
        default=default,
        choices=sorted(corpora),
        help=(
            f"which rows this is about (default {default}, the ADOPTED corpus — a refit on "
            f"a grown store names its own, so that a forgotten flag cannot overwrite the "
            f"join and split a shipped run refers to)"
        ),
    )


def add_commands(subcommands) -> None:
    from fractal_wallpapers.models.gallery_grade_train import (
        ARMS,
        BAND,
        CORPORA,
        CORPUS,
        RECIPE,
        RECIPES,
        RULES,
        SPLIT_SEED,
    )

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
    corpus_flag(resolving, CORPUS, CORPORA)
    resolving.set_defaults(handler=gallery_grade)

    splitting = steps.add_parser(
        "split",
        help="draw the 80/20 over lineages, filled to balance the sheets, blocks and grades",
        description=(
            "Lineages are the hard constraint and go whole; inside that the holdout is "
            "filled by whichever remaining lineage most reduces the summed shortfall over "
            "the sheet, block and grade marginals. The cuts are measurably different scales, "
            "the blocks are different populations, and a stopping slice over-weighting any "
            "of them stops on something the training side is not on. A stratum is read by "
            "the SPLIT and never by the model. ONE seed for every arm and every seed of the "
            "band: an AP read on two different slices is not a comparison of two heads."
        ),
    )
    splitting.add_argument(
        "--seed",
        type=int,
        default=SPLIT_SEED,
        help=f"the draw's seed (default {SPLIT_SEED}, and moving it re-splits the whole band)",
    )
    corpus_flag(splitting, CORPUS, CORPORA)
    splitting.set_defaults(handler=gallery_grade)

    registering = steps.add_parser(
        "preregister",
        help="write this band's bar, BEFORE any of its runs exists",
        description=(
            "The winning arm must beat both incumbents — the judge's own p_ge4 column and "
            "the shipped rank_key a seating actually ranks on — on AUC(>=4) and on Spearman "
            "against the grades, at every seed. Their heights are copied into the bar so it "
            "stays readable without re-deriving them, and it refuses to overwrite: a bar "
            "rewritten after its band is a bar fitted to what happened."
        ),
    )
    registering.add_argument(
        "--force",
        action="store_true",
        help="overwrite a bar no run has been read against",
    )
    band_flag(registering, BAND, RULES)
    corpus_flag(registering, CORPUS, CORPORA)
    recipe_flag(registering, RECIPE, RECIPES)
    registering.set_defaults(handler=gallery_grade)

    accepting = steps.add_parser(
        "accept",
        help="read the band against its registered bar",
        description=(
            "Every seed of the winning arm, against every incumbent, on every gated "
            "statistic — and the record carries each of those cells whether it passed or "
            "not, because a verdict without its arithmetic is one nobody can check. Exits "
            "non-zero when the band does not clear."
        ),
    )
    band_flag(accepting, BAND, RULES)
    corpus_flag(accepting, CORPUS, CORPORA)
    recipe_flag(accepting, RECIPE, RECIPES)
    accepting.set_defaults(handler=gallery_grade)

    scoring = steps.add_parser(
        "score-pool",
        help="read the whole seating pool through the band's picked run",
        description=(
            "Writes the column `curate solve --key cascade` resolves its order from. It "
            "opens each candidate's stored 640x360 JPEG once and renders nothing. The rows "
            "are a cascade's SECOND stage: ranking the whole file would rank rows this head "
            "never saw the like of, and the solve applies it above the bar and only there."
        ),
    )
    band_flag(scoring, BAND, RULES)
    corpus_flag(scoring, CORPUS, CORPORA)
    recipe_flag(scoring, RECIPE, RECIPES)
    device_flag(scoring)
    scoring.set_defaults(handler=gallery_grade)

    fitting = steps.add_parser(
        "fit",
        help="fit one arm at one seed",
        description=(
            "Twenty epochs, patience six, the epoch chosen on the band's own rule. Whether "
            "the stopping slice can carry that rule's boundary is asked ONCE, before the "
            "loop, and a run that cannot is launched under the other rule with that written "
            "into its record. ONE RUN AT A TIME on this box: a trainer commits about 4 GiB "
            "and every Windows loader worker re-imports torch for a gigabyte more."
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
    band_flag(fitting, BAND, RULES)
    corpus_flag(fitting, CORPUS, CORPORA)
    recipe_flag(fitting, RECIPE, RECIPES)
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
    band_flag(banding, BAND, RULES)
    corpus_flag(banding, CORPUS, CORPORA)
    recipe_flag(banding, RECIPE, RECIPES)
    device_flag(banding)
    banding.add_argument("--epochs", type=int, help="override the recipe's epoch ceiling")
    banding.add_argument("--workers", type=int, help="override the recipe's loader workers")
    banding.set_defaults(handler=gallery_grade)

    reading = steps.add_parser(
        "read",
        help="the band: every run that has been fitted, and the pick",
        description=(
            "Arms rank by the MEAN of the band's own statistic over their seeds, and the "
            "winner ships its MEDIAN seed — never the argmax, because the epoch surface is "
            "flat enough that the best of three seeds is a coin flip rather than a fact "
            "about the arm."
        ),
    )
    band_flag(reading, BAND, RULES)
    corpus_flag(reading, CORPUS, CORPORA)
    recipe_flag(reading, RECIPE, RECIPES)
    reading.set_defaults(handler=gallery_grade)


__all__ = ["add_commands", "corpus_flag", "gallery_grade", "recipe_flag"]
