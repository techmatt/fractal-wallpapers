"""Does one score mean the same thing at every regime? The bar, and the read.

The shipped location head was trained at one geometry — 640×360 with the field
sampled twice per pixel per axis — and it is only honest there. Read at a cheaper
regime its scores fall: seventy-odd percent of them move down, worst on
`multibrot3`, and they move far enough to cross the floors the supply engine acts
on. That is not noise a rescore can average out; it is a bias, so the fix is a
head that never learned the geometry in the first place.

## Two arms, and only one of them is the reason

**Overall** asks whether the candidate still judges a location as well as the
incumbent does at the canonical regime, on human labels. It is a
*non-inferiority* arm: the candidate does not have to be better, it has to not be
significantly worse. Regime robustness bought with a worse judge is not a trade
anybody asked for.

**Consistency** is the motivating arm and the one that has to move. It reads the
head's own `P(≥3)` at an ss1 regime against its own `P(≥3)` at the canonical one,
paired per location, and asks how well the two orders agree. Four slices — two
regimes, each all-family and `multibrot3` alone, because `multibrot3` is where
the incumbent is worst and a mean over families would hide it.

Both are read on **evaluation-split rows only**. A training row saw all three
regimes and would flatter a head for reproducing what it was shown.

## The comparison is paired, and the cluster is the group

Every interval here resamples whole neighbourhood **groups**, the unit the split
itself was drawn over, and scores both heads on the same resampled rows. Two
independently-bootstrapped intervals would carry the population's own difficulty
twice; resampling locations rather than groups would report an interval two to
three times too narrow, because six frames of one hot spot are not six pieces of
evidence. See [`fractal_wallpapers.models.metrics`].

## A rho is a property of the population as much as of the head

Read what this bar produced before writing another one. The evaluation split is
63% label-1 and **78% of its rows read below `P(≥3) = 0.05` at the canonical
regime** — zero at every geometry, agreeing trivially — so an all-family rank
correlation over the whole split starts at 0.99 and has almost nowhere to go. The
same statistic on the production sample that motivated this work, stratified over
partition × score band, read 0.963. Neither is wrong and they are not comparable.
A cross-regime claim has to say which rows it was measured on, and a bar meant to
resolve one should be written against rows where the score is contested.

## The band is what is judged; the staged pick is chosen somewhere else

Three seeds are trained. Each arm is read on the **median** seed by that arm's own
statistic — the median, not the best, because picking the best of three is the
thing pre-registration exists to stop — and all three are reported beside it.

Which seed gets staged is a different question with a different answer: the one
the *selection slice* chose, on the training side, under the selection objective.
An arm read on the evaluation side never picks a checkpoint, or the evaluation
side has silently paid for selection.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.models import metrics, scoring, train
from fractal_wallpapers.models import tiles as tile_module
from fractal_wallpapers.paths import tracked_name

#: The schema every record here carries.
SCHEMA = 1

#: The head this study is about.
HEAD = "location"

#: The shipped runs the candidate is measured against, and the one that serves.
#: `location.fp16.pt` was `seed0` while this bar was read; the other two exist
#: and are reported, because a difference smaller than the incumbent's own seed
#: spread is not a difference about the candidate.
INCUMBENT_RUNS = ("seed0", "seed1", "seed2")
SHIPPED_RUN = "seed0"

#: The candidate band: the same recipe at three seeds, trained over all three
#: regimes at once.
CANDIDATE_RUNS = ("seed0_all_regimes", "seed1_all_regimes", "seed2_all_regimes")

#: The number every floor in this project is a point on, and therefore the
#: number whose cross-regime agreement is worth measuring. `P(≥4)` is the other
#: half of the interface and is reported, never gated: at twenty-two positives on
#: this population its own order is mostly noise.
CONSISTENCY_FIELD = "p_ge3"

#: The partition the incumbent is worst on, and the slice that would disappear
#: into an all-family mean.
WORST_FAMILY = "multibrot3"

#: Draws and seed for every interval here. Fixed, and part of the bar.
DRAWS = 5000
BOOTSTRAP_SEED = 0


def prereg_path(head: str = HEAD) -> Path:
    """The bar, written before the candidate existed."""
    return train.head_dir(head) / "regime_prereg.json"


def acceptance_path(head: str = HEAD) -> Path:
    """What the bar says about the candidate band."""
    return train.head_dir(head) / "regime_acceptance.json"


def spelled(regime: tile_module.Regime) -> str:
    """A regime as a person writes it: the full form, before the elision.

    The regime owns its own spelling; this is the name this module's records
    already reach it by.
    """
    return regime.spelled


def slices() -> list[dict]:
    """The four consistency slices, in the order they are reported."""
    out = []
    for regime in tile_module.BUILT_REGIMES[1:]:
        for family in (None, WORST_FAMILY):
            out.append(
                {
                    "regime": spelled(regime),
                    "family": family or "all",
                    "key": f"{spelled(regime)}|{family or 'all'}",
                }
            )
    return out


def preregister(head: str = HEAD) -> dict:
    """The bar. Everything a verdict rests on, written down before any number."""
    canonical = spelled(tile_module.CANONICAL_REGIME)
    return {
        "schema": SCHEMA,
        "head": head,
        "study": "one head, three regimes",
        "question": (
            "Does a location head trained over all three cached regimes at once keep the "
            "incumbent's judgement at the canonical regime, while agreeing with itself far "
            "better at the two cheaper ones?"
        ),
        "regimes": {
            "canonical": canonical,
            "cheaper": [spelled(regime) for regime in tile_module.BUILT_REGIMES[1:]],
            "identity": (
                "every regime is addressed by its own tile names, manifest and build record; "
                "the draw axes of all 379,616 (location, slot) pairs are identical across "
                "the three, so a row is the same picture at three geometries"
            ),
        },
        "population": {
            "rule": (
                "the evaluation side of this repository's shipped split, every location "
                "read through its canonical tile at the regime being read"
            ),
            "side": "eval",
            "why_not_train": (
                "a training row saw all three regimes, so its cross-regime agreement is a "
                "measure of what the head was shown rather than of what it learned"
            ),
        },
        "runs": {
            "incumbent": list(INCUMBENT_RUNS),
            "shipped": SHIPPED_RUN,
            "candidate": list(CANDIDATE_RUNS),
            "checkpoint": "best",
            "precision": (
                "full precision on both sides. The shipped artifact is seed0's fp16 cast and "
                "reproduces its scores to 1.6e-06, which is far below anything read here"
            ),
        },
        "training": {
            "mix": (
                "every location label row at all three regimes — three tiles, one label, one row"
            ),
            "conditioning": (
                "none. The head is handed no regime input and no regime embedding: one score "
                "scale across regimes is the deliverable, and a head that could see the "
                "geometry would be free to keep a scale per geometry"
            ),
            "split": (
                "the existing location-grouped split, unchanged; a row's three tiles share its side"
            ),
            "augmentation": (
                "the shipped recipe's, unchanged. The three regimes are real pictures, not a jitter"
            ),
            "seeds": list(CANDIDATE_RUNS),
            "epoch_is_three_times_as_long": (
                "the epoch count, batch size, learning rates and schedule are the inherited "
                "recipe's, unchanged, and an epoch is now one pass per regime — so the "
                "candidate takes three times the gradient steps the incumbent did. That is "
                "what 'three tiles, one row' costs; shortening the schedule to match the "
                "step count would have been a re-tune of a recipe this project does not "
                "re-tune. Declared, not discovered"
            ),
        },
        "selection": {
            "rule": (
                "epoch and seed are chosen on the training-side selection slice, at the "
                "canonical regime, under the cutpoint cross-entropy"
            ),
            "population": (
                "the incumbent's own selection slice: seed 0, 10% of the training-side "
                "groups, taken whole"
            ),
            "never": (
                "consistency. No cross-regime statistic enters the choice of an epoch or of "
                "the staged seed — a candidate selected on the arm that gates it would be "
                "measuring its own selection"
            ),
            "staged_seed": (
                "the seed with the lowest selection-slice cutpoint cross-entropy at its own "
                "best epoch. Chosen on the training side, so the evaluation side pays for "
                "nothing"
            ),
            "differs_from_the_incumbent": (
                "the incumbent chose its epoch by maximizing average precision at the first "
                "cutpoint. That is a rank statistic and arm (a) below is a proper scoring "
                "rule, so a candidate selected on average precision would be judged on a "
                "statistic it never optimized. The population and the slice are the "
                "incumbent's; the objective is the one this bar gates on. Declared, and it "
                "is generous to the candidate on arm (a)"
            ),
        },
        "statistics": {
            "overall": (
                "the cutpoint cross-entropy of the unconditional probabilities against the "
                "human label at each cutpoint, averaged over the cutpoints. A proper scoring "
                "rule, and the established selection objective of every head here that reads "
                "its own probabilities. LOWER IS BETTER"
            ),
            "consistency": (
                f"Spearman rho between a head's own {CONSISTENCY_FIELD} at an ss1 regime and "
                f"its own {CONSISTENCY_FIELD} at {canonical}, paired per location over the "
                "slice. HIGHER IS BETTER"
            ),
            "interval": (
                f"a 95 percent paired cluster bootstrap, {DRAWS} draws at seed "
                f"{BOOTSTRAP_SEED}, resampling whole neighbourhood groups. Both heads are "
                "scored on the same resampled rows"
            ),
            "band": (
                "each arm is read on the MEDIAN candidate seed by that arm's own statistic, "
                "with all three reported. The median, not the best"
            ),
        },
        "arms": {
            "overall": {
                "gated": True,
                "regime": canonical,
                "against": SHIPPED_RUN,
                "rule": (
                    "the candidate is not significantly worse than the shipped incumbent. "
                    "PASS when the lower bound of the paired interval on "
                    "(candidate - incumbent) is at or below zero; FAIL when it is above"
                ),
                "margin": (
                    "none. The prompt's rule is a plain significance test, and a margin "
                    "would be a second decision nobody wrote down"
                ),
                "reported": (
                    "the same read against the incumbent's other two seeds, and every "
                    "cutpoint's AUC. Neither gates"
                ),
            },
            "consistency": {
                "gated": True,
                "slices": slices(),
                "rule": (
                    "ALL FOUR slices must significantly improve and none may worsen. A slice "
                    "IMPROVED when the lower bound of the paired interval on "
                    "(candidate rho - incumbent rho) is above zero, WORSENED when the upper "
                    "bound is below zero, NOT_RESOLVED otherwise. The arm passes only if all "
                    "four are IMPROVED"
                ),
                "against": SHIPPED_RUN,
                "recomputed": (
                    "the incumbent's rho is measured on these same rows, not carried from "
                    "the 500-row production sample that motivated this work"
                ),
            },
        },
        "verdicts": {
            "PASS": "both gated arms pass",
            "FAIL": "either gated arm fails",
        },
        "adoption": (
            "NOT part of this bar. A passing candidate is staged beside the shipped head and "
            "nothing in the serving path moves: a location retrain shifts the score scale "
            "every floor is calibrated against, and restating those floors is a separate, "
            "priced decision"
        ),
        "declared": [
            "The incumbent is the SHIPPED run and the arms gate against it alone. Its other "
            "two seeds are read the same way and reported, so a reader can see whether a "
            "difference is larger than the incumbent's own seed spread, but a head that does "
            "not serve is not the thing being replaced.",
            f"The {WORST_FAMILY} slice is thin and one-sided: 71 evaluation locations in 24 "
            "groups, 68 of them labelled 1. Its rho is therefore measured almost entirely in "
            "the head's low tail and its interval will be wide. It is gated anyway, because "
            "it is the slice the whole retrain is about — but a NOT_RESOLVED there is a "
            "statement about 24 clusters, not about the head.",
            "Selection uses a different objective from the incumbent's, on the incumbent's "
            "own slice and population. See `selection.differs_from_the_incumbent`: it is "
            "generous to the candidate on the overall arm and is declared rather than "
            "discovered.",
            "This is a same-input comparison, unlike the incumbent's own acceptance bar: "
            "both heads are read through the same tiles of the same locations, so what is "
            "left is the two heads.",
            "The candidate takes three times the gradient steps the incumbent did, because "
            "its epoch is three passes long and the schedule is the inherited one. See "
            "`training.epoch_is_three_times_as_long`.",
            "Adjacent-category label noise at these boundaries is larger than the "
            "differences the overall arm can resolve. Only the pre-declared test is read; "
            "small boundary deltas are reported and are not findings.",
        ],
        "amendments": [],
    }


def _rows_of(run: str, regime: tile_module.Regime, head: str = HEAD) -> dict[int, dict]:
    """One run's evaluation-side read at one regime, keyed by location."""
    path = scoring.scores_path(head, run, regime)
    if not path.is_file():
        raise ValueError(
            f"{path} is missing: run {run!r} has not been scored at {spelled(regime)}. "
            "Every arm here is paired row by row, so a missing read is a missing arm."
        )
    return {int(row["location_id"]): row for row in scoring.read(path)}


def aligned(runs, regimes, head: str = HEAD) -> dict:
    """Every run's read at every regime, over the locations all of them cover.

    Refuses a partial overlap rather than intersecting quietly. Two heads
    compared on different rows are not compared.
    """
    read = {
        (run, spelled(regime)): _rows_of(run, regime, head) for run in runs for regime in regimes
    }
    shared = set.intersection(*(set(rows) for rows in read.values()))
    widths = {key: len(rows) for key, rows in read.items()}
    odd = {key: width for key, width in widths.items() if width != len(shared)}
    if odd:
        raise ValueError(
            f"the reads do not cover the same locations: {len(shared)} are in all of them "
            f"and {odd} differ. A paired comparison on a quiet intersection is a comparison "
            "nobody can name the population of."
        )
    order = sorted(shared)
    return {"ids": order, "read": read, "locations": len(order)}


def _column(read: dict, run: str, regime: str, ids: list[int], field: str):
    import numpy

    rows = read[(run, regime)]
    return numpy.array([rows[identifier][field] for identifier in ids], dtype=float)


def _probabilities(read: dict, run: str, regime: str, ids: list[int], classes: int):
    import numpy

    from fractal_wallpapers.models import head as head_module

    rows = read[(run, regime)]
    return numpy.array(
        [
            [
                rows[identifier][f"p_{head_module.cutpoint_label(index)}"]
                for index in range(classes - 1)
            ]
            for identifier in ids
        ],
        dtype=float,
    )


def _median_run(values: dict, better) -> str:
    """The median run by its own statistic — the pre-registered escalation.

    `better` orders the runs; the middle one is returned. With three runs that is
    the second of the sorted three, whichever direction the statistic improves in.
    """
    ordered = sorted(values, key=lambda run: better(values[run]))
    return ordered[len(ordered) // 2]


def overall(context: dict, classes: int = 4) -> dict:
    """Arm (a): is the candidate a worse judge at the canonical regime?"""
    import numpy

    ids, read = context["ids"], context["read"]
    canonical = spelled(tile_module.CANONICAL_REGIME)
    labels = _column(read, SHIPPED_RUN, canonical, ids, "score")
    groups = _column(read, SHIPPED_RUN, canonical, ids, "group")

    predicted = {
        run: _probabilities(read, run, canonical, ids, classes)
        for run in (*INCUMBENT_RUNS, *CANDIDATE_RUNS)
    }
    scored = {
        run: metrics.cutpoint_cross_entropy(labels, values, classes)
        for run, values in predicted.items()
    }
    judged = _median_run({run: scored[run] for run in CANDIDATE_RUNS}, better=lambda value: value)

    against = {}
    for incumbent in INCUMBENT_RUNS:

        def statistic(indices, incumbent=incumbent):
            ours = metrics.cutpoint_cross_entropy(
                labels[indices], predicted[judged][indices], classes
            )
            theirs = metrics.cutpoint_cross_entropy(
                labels[indices], predicted[incumbent][indices], classes
            )
            return ours - theirs

        interval = metrics.bootstrap(statistic, groups, draws=DRAWS, seed=BOOTSTRAP_SEED)
        delta = scored[judged] - scored[incumbent]
        gated = incumbent == SHIPPED_RUN
        against[incumbent] = {
            "ours": scored[judged],
            "theirs": scored[incumbent],
            "delta": delta,
            "ci": [interval["lo"], interval["hi"]],
            "clusters": interval.get("clusters"),
            "gated": gated,
            "verdict": "FAIL" if interval["lo"] > 0 else "PASS",
        }

    cutpoints = {}
    from fractal_wallpapers.models import head as head_module

    for index in range(classes - 1):
        label = head_module.cutpoint_label(index)
        truth = (labels >= index + 2).astype(int)
        cutpoints[label] = {
            "positives": int(truth.sum()),
            "candidate": {
                run: metrics.auc(truth, predicted[run][:, index]) for run in CANDIDATE_RUNS
            },
            "incumbent": {
                run: metrics.auc(truth, predicted[run][:, index]) for run in INCUMBENT_RUNS
            },
        }

    return {
        "statistic": "cutpoint cross-entropy against the human label, lower is better",
        "regime": canonical,
        "locations": len(ids),
        "clusters": int(len(numpy.unique(groups))),
        "band": {run: scored[run] for run in CANDIDATE_RUNS},
        "incumbent_band": {run: scored[run] for run in INCUMBENT_RUNS},
        "judged_on": judged,
        "against": against,
        "auc_reported_only": cutpoints,
        "verdict": against[SHIPPED_RUN]["verdict"],
    }


def consistency(context: dict) -> dict:
    """Arm (b): does the head still say the same thing at a cheaper regime?"""
    import numpy

    ids, read = context["ids"], context["read"]
    canonical = spelled(tile_module.CANONICAL_REGIME)
    families = [read[(SHIPPED_RUN, canonical)][identifier]["partition"] for identifier in ids]
    groups_all = _column(read, SHIPPED_RUN, canonical, ids, "group")

    out = {}
    for entry in slices():
        keep = numpy.array(
            [
                index
                for index, family in enumerate(families)
                if entry["family"] == "all" or family == entry["family"]
            ]
        )
        kept = [ids[index] for index in keep]
        groups = groups_all[keep]

        def rho_of(run, entry=entry, kept=kept):
            here = _column(read, run, entry["regime"], kept, CONSISTENCY_FIELD)
            there = _column(read, run, canonical, kept, CONSISTENCY_FIELD)
            return here, there

        rho = {}
        columns = {}
        for run in (*INCUMBENT_RUNS, *CANDIDATE_RUNS):
            here, there = rho_of(run)
            columns[run] = (here, there)
            rho[run] = metrics.spearman(here, there)
        judged = _median_run({run: rho[run] for run in CANDIDATE_RUNS}, better=lambda value: -value)

        def statistic(indices, judged=judged, columns=columns):
            ours = metrics.spearman(columns[judged][0][indices], columns[judged][1][indices])
            theirs = metrics.spearman(
                columns[SHIPPED_RUN][0][indices], columns[SHIPPED_RUN][1][indices]
            )
            return None if ours is None or theirs is None else ours - theirs

        interval = metrics.bootstrap(statistic, groups, draws=DRAWS, seed=BOOTSTRAP_SEED)
        verdict = (
            "IMPROVED"
            if interval["lo"] is not None and interval["lo"] > 0
            else "WORSENED"
            if interval["hi"] is not None and interval["hi"] < 0
            else "NOT_RESOLVED"
        )
        out[entry["key"]] = {
            "regime": entry["regime"],
            "family": entry["family"],
            "locations": len(kept),
            "clusters": int(len(numpy.unique(groups))),
            "band": {run: rho[run] for run in CANDIDATE_RUNS},
            "incumbent_band": {run: rho[run] for run in INCUMBENT_RUNS},
            "judged_on": judged,
            "delta": rho[judged] - rho[SHIPPED_RUN],
            "ci": [interval["lo"], interval["hi"]],
            "verdict": verdict,
        }

    return {
        "statistic": (
            f"Spearman rho of a head's own {CONSISTENCY_FIELD} at an ss1 regime against its "
            f"own at {canonical}, paired per location"
        ),
        "slices": out,
        "verdict": "PASS" if all(s["verdict"] == "IMPROVED" for s in out.values()) else "FAIL",
    }


def staged_seed(runs=CANDIDATE_RUNS, head: str = HEAD) -> dict:
    """Which seed ships as the candidate: the one the selection slice chose.

    Read off each run's own metrics record, on the training side, under the
    objective that run selected on. The evaluation side never sees this choice.
    """
    band = {}
    for run in runs:
        record = json.loads(train.metrics_path(head, run).read_text(encoding="utf-8"))
        if record.get("selection_objective") != "cutpoint_cross_entropy":
            raise ValueError(
                f"run {run!r} selected on {record.get('selection_objective')!r}, and the bar "
                "says the staged seed is the one with the lowest selection-slice cutpoint "
                "cross-entropy. Two objectives are not one band."
            )
        band[run] = {
            "best_epoch": record["best_epoch"],
            # The record stores the maximized orientation; the objective itself
            # is the cross-entropy, which is its negation.
            "selection_cutpoint_cross_entropy": -record["best_selection_objective"],
        }
    pick = min(band, key=lambda run: band[run]["selection_cutpoint_cross_entropy"])
    return {
        "rule": "lowest selection-slice cutpoint cross-entropy at its own best epoch",
        "band": band,
        "seed": pick,
    }


def read(head: str = HEAD) -> dict:
    """The whole bar, read against the candidate band."""
    bar = json.loads(prereg_path(head).read_text(encoding="utf-8"))
    regimes = tile_module.BUILT_REGIMES
    context = aligned((*INCUMBENT_RUNS, *CANDIDATE_RUNS), regimes, head)

    first = overall(context)
    second = consistency(context)
    verdict = "PASS" if first["verdict"] == "PASS" and second["verdict"] == "PASS" else "FAIL"
    return {
        "schema": SCHEMA,
        "head": head,
        "prereg": tracked_name(prereg_path(head)),
        "prereg_question": bar["question"],
        "runs": {"incumbent": list(INCUMBENT_RUNS), "candidate": list(CANDIDATE_RUNS)},
        "regimes": [spelled(regime) for regime in regimes],
        "population": {"locations": context["locations"], "side": "eval"},
        "overall": first,
        "consistency": second,
        "staged": staged_seed(head=head),
        "verdict": verdict,
    }


__all__ = [
    "BOOTSTRAP_SEED",
    "CANDIDATE_RUNS",
    "CONSISTENCY_FIELD",
    "DRAWS",
    "HEAD",
    "INCUMBENT_RUNS",
    "SCHEMA",
    "SHIPPED_RUN",
    "WORST_FAMILY",
    "acceptance_path",
    "aligned",
    "consistency",
    "overall",
    "preregister",
    "prereg_path",
    "read",
    "slices",
    "spelled",
    "staged_seed",
]
