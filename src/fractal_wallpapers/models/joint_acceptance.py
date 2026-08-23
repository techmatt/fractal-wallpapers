"""The bar the joint render candidate is read against, and the read.

## The bar is non-inferiority, and that is a ratified deviation

Every other bar in this project asks a candidate to *win* something. This one does
not, and the reason is that the benefit being bought is not a number. One head
over both kinds is one fewer store boundary, one fewer release artifact, one
fewer floor to calibrate and one fewer recipe to keep in step — and no
measurement of a sheet can show that. Matt ratified the benefit; the measurement
is only asked to show that nothing was paid for it.

So: the candidate is viable iff **no arm is significantly worse** than that kind's
own shipped head, at 95% on a paired cluster bootstrap, per seed and on the band.
Nothing is required to be better. An arm that improves is reported and changes no
verdict.

## Which boundary each sheet may be read at, and why one is refused outright

Each sheet informs exactly one boundary, fixed when it was drawn. Reading a sheet
at a boundary its draw does not support produces a number that looks like every
other number in the table and means nothing.

```text
blind_minibrot  197 rows   2:6  3:95  4:96      read at >=4
blind_modes     150 rows   1:74 2:70  3:2  4:4  read at >=2, reported at >=3
```

`blind_minibrot` has **no tier-1 row at all**, so its `>=2` boundary has no
negatives and its AUC there is undefined rather than perfect. Its `>=3` has six
negatives in 197 and is reported without being read.

`blind_modes` is **never read at `>=4`**, and this is the standing caveat that
outranks the arithmetic. Six of its rows sit at `>=3`; four of those six are the
*only* `>=4` rows on the sheet, and all four arrived on a later **anchored** pass
— a human re-reading rows the sheet had already scored 3, having seen a tier. The
store carries them as four superseded rows, latest-wins, and they are the entire
positive class at `>=4`. An AUC there would be an AUC over four non-blind rows on
a sheet whose whole value is that it is blind. Refused, not reported. The `>=3`
boundary carries the same four rows among its six positives and is gated anyway,
because it is a boundary the draw supports — but its interval is what decides,
never its point estimate.

**Note the count.** `models/strange_render/README.md` says six rows at `>=3`, four
of them revised up on an anchored pass. Those are two different sixes and only
four rows are superseded; the sheet holds 154 rows resolving to 150.

## The comparison is paired and the cluster is the neighbourhood group

Every interval resamples whole groups under the exact non-`c` rule — the same
unit every split in this project is drawn over — and scores both heads on the
same resampled rows. The eval-only pin is a different question and stays where it
is, asserted at the **unit**: one location, not its group.

On these two sheets the two units are nearly the same — 192 groups over 197
locations, 108 over 110 — so the choice barely moves an interval here. It is made
this way because it is the rule, not because it changed an answer.

## What is not controlled, and points the candidate's way

The smooth store grew after its incumbent trained: `released_top_end` and
`mandelbrot_mix_pricing` landed afterwards, and the candidate trains on 160
smooth rows the shipped smooth head never saw. That is a confound in the
candidate's favour and it is declared here rather than corrected in the bar — the
correction is a corpus-matched ablation, which is a separate arm and is reported
beside the verdict rather than folded into it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fractal_wallpapers.models import finished_scoring, joint_render, metrics, renders
from fractal_wallpapers.paths import repo_root

#: The schema every record here carries.
SCHEMA = 1

#: Draws in every interval here, and its seed. Part of the bar.
DRAWS, BOOTSTRAP_SEED = 5000, 0

#: What each kind's candidate is measured against: the run that actually serves,
#: and the band around it. The shipped run gates; the others are reported so a
#: reader can see whether a difference is larger than the incumbent's own spread.
#:
#: `smooth_render` ships the run at the root of its directory, which has no name;
#: `None` is how every path helper in this project spells that.
INCUMBENTS: dict[str, dict] = {
    "smooth_render": {"shipped": None, "band": (None, "seed1", "seed2")},
    "strange_render": {
        "shipped": "four_class_seed0",
        "band": ("four_class_seed0", "four_class_seed1", "four_class_seed2"),
    },
}

#: Every arm, in the order the tables report them. `direction` is which way the
#: statistic improves; `gated` says whether a significant loss fails the bar.
ARMS: tuple[dict, ...] = (
    {
        "key": "smooth_scoring_rule",
        "kind": "smooth_render",
        "sheet": "blind_minibrot",
        "statistic": "cutpoint_cross_entropy",
        "direction": "lower",
        "gated": True,
        "why": "the proper scoring rule on the smooth eval split, over all three cutpoints. "
        "This head's interface is its probabilities and a floor is a point on one of them",
    },
    {
        "key": "smooth_auc_ge4",
        "kind": "smooth_render",
        "sheet": "blind_minibrot",
        "statistic": "auc",
        "cutpoint": 4,
        "direction": "higher",
        "gated": True,
        "why": "the one boundary this sheet's draw supports, and the one production cuts on",
    },
    {
        "key": "smooth_auc_ge3",
        "kind": "smooth_render",
        "sheet": "blind_minibrot",
        "statistic": "auc",
        "cutpoint": 3,
        "direction": "higher",
        "gated": False,
        "why": "six negatives in 197. Reported so the table is complete; decides nothing",
    },
    {
        "key": "strange_scoring_rule",
        "kind": "strange_render",
        "sheet": "blind_modes",
        "statistic": "cutpoint_cross_entropy",
        "direction": "lower",
        "gated": True,
        "why": "the proper scoring rule on the strange eval split, over all three cutpoints",
    },
    {
        "key": "strange_auc_ge2",
        "kind": "strange_render",
        "sheet": "blind_modes",
        "statistic": "auc",
        "cutpoint": 2,
        "direction": "higher",
        "gated": True,
        "why": "the boundary this sheet was drawn to inform",
    },
    {
        "key": "strange_auc_ge3",
        "kind": "strange_render",
        "sheet": "blind_modes",
        "statistic": "auc",
        "cutpoint": 3,
        "direction": "higher",
        "gated": True,
        "why": "a boundary the draw supports, on six positives. The interval decides; the "
        "point estimate is not a finding in either direction",
    },
)

#: The reading this module will not make, and the sentence it makes instead.
REFUSED: dict[str, str] = {
    "strange_auc_ge4": (
        "blind_modes is never read at >=4. Its only four positives at that boundary are "
        "four rows a later ANCHORED pass revised up from 3, having seen a tier; they are "
        "the sheet's four superseded rows. An AUC over them is an AUC over the only "
        "non-blind rows on a blind sheet"
    ),
    "smooth_auc_ge2": (
        "blind_minibrot holds no tier-1 row, so its >=2 boundary has no negative class and "
        "its AUC there is undefined rather than perfect"
    ),
}

#: The corpus-matched control, per kind. One kind's share of exactly the pooled
#: split, at exactly the candidate's recipe — so the only thing that moves
#: between an ablation seed and the candidate seed of the same number is whether
#: the other kind's rows were in the batch.
#:
#: It answers what the incumbent comparison structurally cannot. Two things
#: changed alongside pooling and neither IS pooling: the smooth store grew after
#: its incumbent trained, and the strange incumbent's backbone is the small one a
#: single head cannot also be. Absent runs are reported as absent, never
#: silently skipped.
ABLATIONS: dict[str, tuple[str, ...]] = {
    kind: tuple(f"{kind.split('_')[0]}_only_seed{index}" for index in range(3))
    for kind in joint_render.KINDS
}


#: How the two architectures' losses aggregate, and why that is a fact worth
#: writing down rather than assuming.
#:
#: The worry is real and specific: if the shared arm took one mean over the
#: pooled batch while the split arm took a mean **per kind** and summed them, the
#: rarer kind's head would carry an effective weight of `n_pooled / n_kind` — about
#: 2.6x for strange — and the two arms would differ in learning rate rather than
#: in architecture. `tests/test_joint_render.py` proves they do not: both arms
#: reach one `corn_loss` over the whole batch through the same line, and every
#: row's weight is `1 / (tasks * pooled subset size)` whatever kind it is.
LOSS_PARITY = {
    "aggregation": (
        "identical. Both arms call head.loss_of once on a (batch, cutpoints) tensor; the "
        "split arm's tensor is a GATHER of each row's own kind's columns, not a pair of "
        "per-kind losses. Every row's weight is 1/(tasks x pooled subset size), verified "
        "exactly and kind-independent"
    ),
    "batch_composition": (
        "the same sampler over the same weights: `_loader` computes them from the training "
        "list regardless of the arm, and only the dataset class differs. The realized batch "
        "SEQUENCES do differ, because a wider classifier consumes more of the RNG at init — "
        "that is what a seed band is for, and it is inherent to changing an architecture "
        "rather than a defect in the aggregation"
    ),
    "gradient_clipping": (
        "on the global norm over all parameters, so the extra classifier rows can shift it "
        "only by their own share: the classifier is 0.045% of the medium head's parameters "
        "and 0.090% of the split one's, 0.152% and 0.30% at the small backbone. Bounded far "
        "below anything these sheets resolve"
    ),
    "defect_found": False,
}


class JointComparisonError(RuntimeError):
    """The bar cannot be built, or the candidate cannot be read against it."""


def _suffix(candidate: str) -> str:
    """One file name per candidate. The first one's records keep their plain names.

    Not a version number. A candidate is a design, its bar was written about that
    design, and the read of a superseded one stays exactly as it was read — the
    first band's FAIL is a file in git, not a thing to be overwritten by the next
    question.
    """
    return "" if candidate == "medium" else f"_{candidate}"


def bar_path(candidate: str = joint_render.CURRENT) -> Path:
    """The bar, as a file. Written before any score existed; never rewritten."""
    return joint_render.head_dir() / f"bar{_suffix(candidate)}.json"


def comparison_path(candidate: str = joint_render.CURRENT) -> Path:
    """What the bar says about the candidate band."""
    return joint_render.head_dir() / f"comparison{_suffix(candidate)}.json"


def bar(candidate: str = joint_render.CURRENT) -> dict:
    """Everything a verdict rests on, spelled out before a number exists."""
    entry = joint_render.CANDIDATES[candidate]
    return {
        "schema": SCHEMA,
        "study": "one render judge over both kinds",
        "candidate": candidate,
        "candidate_is": entry["what"],
        "backbone": entry["backbone"],
        "runs": list(entry["runs"]),
        "question": (
            "Would ONE head over the pooled smooth and strange stores be non-inferior to "
            "the two shipped heads, on each kind's own blind sheet?"
        ),
        "rule": (
            "NON-INFERIORITY, and it is a ratified deviation from this project's winner "
            "rule. The candidate is viable iff no gated arm is significantly worse than "
            "that kind's shipped head. Nothing is required to be better: the declared "
            "benefit is one head instead of two, which no sheet can measure"
        ),
        "significance": (
            f"95 percent paired cluster bootstrap, {DRAWS} draws at seed {BOOTSTRAP_SEED}, "
            "resampling whole neighbourhood groups under the exact non-`c` rule. Both heads "
            "are scored on the same resampled rows, so the population's own difficulty "
            "cancels"
        ),
        "band": (
            "three seeds, and the band IS the result — no staged pick. Every arm is read on "
            "each seed AND on the band's median seed by that arm's own statistic. An arm "
            "fails if it fails on the band or on any single seed"
        ),
        "arms": [dict(arm) for arm in ARMS],
        "refused": dict(REFUSED),
        "incumbents": {
            kind: {"shipped": row["shipped"], "band": list(row["band"])}
            for kind, row in INCUMBENTS.items()
        },
        "training": {
            "split": (
                "the INTERSECTION of the two stores' training sides: a location pinned in "
                "either store may not train. Stricter than what either incumbent faced, and "
                "the strictness costs the candidate"
            ),
            "conditioning": "none. The head is handed no kind",
            "recipe": (
                "the incumbents', which agree on every behavioural key but the backbone — "
                f"the one value a joint head cannot inherit. This candidate takes "
                f"{entry['backbone']}"
            ),
            "selection": (
                "the incumbents' objective, share and seed, over the pooled training side's "
                "places. A controlled variable"
            ),
        },
        "declared": [
            "Adjacent-category label noise at these boundaries is larger than the "
            "differences the sheets can resolve. The bootstrap verdicts are the result; a "
            "non-significant gap is not a finding in either direction, and small AUC "
            "differences at >=3 are read as nothing at all.",
            "The smooth store grew after its incumbent trained. The candidate trains on 160 "
            "smooth rows the shipped smooth head never saw, from `released_top_end` and "
            "`mandelbrot_mix_pricing`. That points the candidate's way and is NOT corrected "
            "in the bar; the corpus-matched ablation is reported beside the verdict.",
            "The two incumbents were selected under this same objective on their own "
            "slices, so the selection rule is a controlled variable and the selection "
            "POPULATION is the pooled analogue of theirs.",
            "A shared nominal scale would NOT license cross-kind ranking. Selection pools "
            "stay disjoint per kind and floors stay per kind, whatever this bar says.",
            "The gate is against each kind's SHIPPED run. The incumbent's other two seeds "
            "are read the same way and reported.",
            "CARRIED FORWARD from the first band, which learned it the hard way: sheet D's "
            ">=4 cross-entropy is dominated by the smooth incumbent's own calibration on an "
            "enriched sheet (CE 2.385, of which 1.744 is scale). ANY head 'wins' there by "
            "being less under-confident, so that arm is not read for a cross-model claim "
            "except recalibrated. The recalibrated split is reported below the table.",
        ],
        "verdicts": {
            "PASS": "no gated arm is significantly worse, on the band or on any seed",
            "FAIL": "some gated arm is significantly worse",
        },
        "adoption": "NOT part of this bar and not done anywhere. A passing candidate is a "
        "candidate; what adopting it would cost is written in the report and nowhere else",
    }


def write_bar(candidate: str = joint_render.CURRENT, *, force: bool = False) -> Path:
    """Ship one candidate's bar to its file. Refuses to overwrite one that exists.

    `force` is keyword-only, and that is not decoration. It read positionally
    once, so `write_bar("medium")` bound the candidate NAME to `force`, which is
    truthy — the call asking for a different candidate's bar was the very call
    that disabled the guard against rewriting one. A bar is the one file in this
    study that may never be rewritten, so its guard may not be switchable by a
    misplaced argument.
    """
    path = bar_path(candidate)
    if path.is_file() and not force:
        raise JointComparisonError(
            f"{path} already exists. A bar rewritten after the numbers are in is not a bar."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bar(candidate), indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _incumbent_rows(kind: str, run: str | None) -> dict[str, dict]:
    """One incumbent run's committed read of its own sheet, keyed by picture."""
    path = finished_scoring.scores_path(kind, run)
    if not path.is_file():
        raise JointComparisonError(
            f"{path} is missing: incumbent run {run!r} has no committed read of the {kind} "
            f"sheet. Every arm here is paired row by row."
        )
    return {row["name"]: row for row in finished_scoring.read(path)}


def _candidate_rows(kind: str, run: str) -> dict[str, dict]:
    path = joint_render.scores_path(kind, run)
    if not path.is_file():
        raise JointComparisonError(
            f"{path} is missing: candidate run {run!r} has not read the {kind} sheet. "
            f"Run `fractal-wallpapers joint score --run {run}`."
        )
    return {row["name"]: row for row in joint_render.read(kind, run)}


def aligned(kind: str, candidate_runs: list[str], ablation_runs: list[str] | None = None) -> dict:
    """Every read of one sheet, over the pictures all of them cover.

    Refuses a partial overlap rather than intersecting quietly: two heads
    compared on different rows are not compared. The labels come from the rows
    themselves and are checked to agree across the reads, because a sheet whose
    verdicts moved between two reads is two populations wearing one name.
    """
    import numpy

    reads = (
        {f"incumbent:{run}": _incumbent_rows(kind, run) for run in INCUMBENTS[kind]["band"]}
        | {f"candidate:{run}": _candidate_rows(kind, run) for run in candidate_runs}
        | {f"ablation:{run}": _candidate_rows(kind, run) for run in ablation_runs or ()}
    )
    shared = set.intersection(*(set(rows) for rows in reads.values()))
    odd = {key: len(rows) for key, rows in reads.items() if len(rows) != len(shared)}
    if odd:
        raise JointComparisonError(
            f"the {kind} reads do not cover the same pictures: {len(shared)} are in all of "
            f"them and {odd} differ. A paired comparison on a quiet intersection is a "
            f"comparison nobody can name the population of."
        )
    names = sorted(shared)
    labels = None
    for key, rows in reads.items():
        theirs = numpy.array([rows[name]["score"] for name in names], dtype=float)
        if labels is None:
            labels = theirs
        elif not numpy.array_equal(labels, theirs):
            raise JointComparisonError(
                f"the {kind} reads disagree about the sheet's own labels ({key} differs). "
                f"Re-score every run against the store as it stands now."
            )
    template = reads[f"candidate:{candidate_runs[0]}"]
    clusters = joint_render.cluster_of([template[name] for name in names])
    return {
        "kind": kind,
        "names": names,
        "labels": labels,
        "groups": numpy.array(clusters),
        "reads": reads,
    }


def _probabilities(context: dict, key: str, classes: int = 4):
    import numpy

    rows = context["reads"][key]
    return numpy.array(
        [
            [rows[name][f"p_ge{index + 2}"] for index in range(classes - 1)]
            for name in context["names"]
        ],
        dtype=float,
    )


def _statistic_of(arm: dict, labels, probabilities, classes: int = 4):
    if arm["statistic"] == "cutpoint_cross_entropy":
        return metrics.cutpoint_cross_entropy(labels, probabilities, classes)
    index = int(arm["cutpoint"]) - 2
    return metrics.auc((labels >= arm["cutpoint"]).astype(int), probabilities[:, index])


def _worse(arm: dict, low: float | None, high: float | None) -> bool:
    """Whether the paired interval says the candidate is significantly worse.

    `lower` statistics are worse when the delta is above zero; `higher` ones when
    it is below. An interval that could not be computed is not a pass — it is an
    arm that did not measure anything, and it says so.
    """
    if low is None or high is None:
        return False
    return low > 0.0 if arm["direction"] == "lower" else high < 0.0


def _median_run(values: dict, direction: str) -> str:
    """The median run by its own statistic. The median, not the best."""
    sign = 1.0 if direction == "lower" else -1.0
    ordered = sorted(
        (run for run in values if values[run] is not None), key=lambda run: sign * values[run]
    )
    if not ordered:
        raise JointComparisonError("no run produced this statistic, so no band can be read")
    return ordered[len(ordered) // 2]


def _paired(arm: dict, context: dict, left: str, right: str, classes: int = 4) -> dict:
    """One paired cluster-bootstrap read of `left` against `right` on this arm.

    `left - right` throughout, so the sign of a delta always means "the first
    named head, relative to the second" whichever pair is being read.
    """
    labels, groups = context["labels"], context["groups"]
    ours_all = _probabilities(context, left, classes)
    theirs_all = _probabilities(context, right, classes)

    def statistic(indices):
        ours = _statistic_of(arm, labels[indices], ours_all[indices], classes)
        theirs = _statistic_of(arm, labels[indices], theirs_all[indices], classes)
        return None if ours is None or theirs is None else ours - theirs

    interval = metrics.bootstrap(statistic, groups, draws=DRAWS, seed=BOOTSTRAP_SEED)
    ours = _statistic_of(arm, labels, ours_all, classes)
    theirs = _statistic_of(arm, labels, theirs_all, classes)
    better = (
        None
        if interval["lo"] is None
        else (interval["hi"] < 0.0 if arm["direction"] == "lower" else interval["lo"] > 0.0)
    )
    return {
        "ours": ours,
        "theirs": theirs,
        "delta": None if ours is None or theirs is None else ours - theirs,
        "ci": [interval["lo"], interval["hi"]],
        "clusters": interval.get("clusters"),
        "verdict": "WORSE"
        if _worse(arm, interval["lo"], interval["hi"])
        else ("BETTER" if better else "NOT_RESOLVED"),
    }


def ablation_arm(
    arm: dict, context: dict, candidate_runs: list[str], ablation_runs: list[str]
) -> dict:
    """The candidate against its own corpus-matched control, on one arm.

    Paired seed for seed, which is the tightest pairing available: seed *n* of
    the candidate and seed *n* of the ablation share a recipe, a split, a
    selection slice and a random seed, and differ only in whether the other
    kind's rows were in the batch. The band is the median of each side by this
    arm's own statistic, read against each other.

    No bar is attached. `BETTER` here is transfer and `WORSE` is interference,
    and either is a fact about this arm rather than about the verdict above.
    """
    # Paired on the SEED, not on position. A partial ablation set — one run that
    # died, one not yet trained — would otherwise pair seed 0 against seed 1 by
    # sliding along the list, and the tightest pairing available would quietly
    # become the loosest.
    by_seed = {run[-1]: run for run in ablation_runs}
    matched = {
        candidate: _paired(arm, context, f"candidate:{candidate}", f"ablation:{by_seed[seed]}")
        for candidate in candidate_runs
        if (seed := candidate[-1]) in by_seed
    }
    scored = {
        key: _statistic_of(
            arm, context["labels"], _probabilities(context, key), int(arm.get("classes", 4))
        )
        for key in (
            *(f"candidate:{run}" for run in candidate_runs),
            *(f"ablation:{run}" for run in ablation_runs),
        )
    }
    out = {
        "key": arm["key"],
        "kind": arm["kind"],
        "direction": arm["direction"],
        "ablation_band": {run: scored[f"ablation:{run}"] for run in ablation_runs},
        "seed_for_seed": matched,
    }
    # A band read needs a median, and two runs do not have one — `_median_run`
    # would hand back the worse of the two and it would be reported as a centre.
    # So the band is omitted below three and the seed-for-seed pairs carry it,
    # which is the tighter comparison anyway.
    if len(ablation_runs) < 3 or len(candidate_runs) < 3:
        out["band"] = None
        out["no_band_because"] = (
            f"{len(ablation_runs)} ablation run(s) against {len(candidate_runs)} candidate "
            f"run(s): a median needs three. The seed-for-seed pairs are the read"
        )
        return out
    way = arm["direction"]
    left = _median_run({run: scored[f"candidate:{run}"] for run in candidate_runs}, way)
    right = _median_run({run: scored[f"ablation:{run}"] for run in ablation_runs}, way)
    out["band_read_on"] = {"candidate": left, "ablation": right}
    out["band"] = _paired(arm, context, f"candidate:{left}", f"ablation:{right}")
    return out


def decomposition(context: dict, arms: dict[str, str], classes: int = 4) -> list[dict]:
    """Split each cutpoint's cross-entropy into a scale term and an order term.

    REPORTED, never gated. The bar is a proper scoring rule and a proper scoring
    rule is minimized only by probabilities that are both well ordered *and*
    correctly scaled — which is exactly its virtue and exactly why a bare number
    off it does not say which of the two moved.

    So each cutpoint's probabilities are recalibrated **on this sheet** by the
    same isotonic fit [`fractal_wallpapers.models.release_floor`] uses to place a
    floor, and the cross-entropy is read again. What survives the recalibration
    is the order; what the recalibration removed is the scale. The fit is
    in-sample and therefore optimistic — for BOTH heads, identically — so the gap
    between them is the fair thing to read and neither absolute number is.

    It earns its place here because the adoption path re-derives both floors by
    that very fit. A gap that lives entirely in the scale term is a gap adoption
    would re-measure anyway; a gap in the order term is not.
    """
    import numpy

    from fractal_wallpapers.models.release_floor import isotonic

    def entropy(truth, probability):
        probability = numpy.clip(probability, 1e-7, 1.0 - 1e-7)
        return float(
            -(truth * numpy.log(probability) + (1.0 - truth) * numpy.log(1.0 - probability)).mean()
        )

    labels = context["labels"]
    predicted = {name: _probabilities(context, key, classes) for name, key in arms.items()}
    out = []
    for index in range(classes - 1):
        cutpoint = index + 2
        truth = (labels >= cutpoint).astype(float)
        if truth.sum() == 0 or truth.sum() == len(truth):
            out.append({"cutpoint": cutpoint, "unreadable": "the sheet holds only one class here"})
            continue
        row = {"cutpoint": cutpoint, "positives": int(truth.sum())}
        for name, values in predicted.items():
            column = values[:, index]
            curve = dict(isotonic(list(zip(map(float, column), map(float, truth), strict=True))))
            recalibrated = numpy.array([curve[float(value)] for value in column])
            raw = entropy(truth, column)
            order = entropy(truth, recalibrated)
            row[name] = {
                "cross_entropy": raw,
                "order_term": order,
                "scale_term": raw - order,
                "auc": metrics.auc(truth, column),
            }
        out.append(row)
    return out


def scale_or_order(context: dict, left: str, right: str, classes: int = 4) -> dict:
    """Where the gap between two arms lives: in the thresholds, or in the order?

    A proper scoring rule is minimized only by probabilities that are both well
    ordered and correctly scaled, which is its virtue and also why a bare delta
    off it does not say which of the two moved. This splits the delta: what an
    in-sample isotonic recalibration removes is the **scale**, what survives it is
    the **order**, and each half gets its own paired interval over whole groups.

    It answers a question the bar cannot. A gap that is scale-only is a gap the
    adoption path re-derives anyway, because placing a release floor IS that fit.
    A gap in the order term is not.
    """
    import numpy

    from fractal_wallpapers.models.release_floor import isotonic

    def entropy(truth, probability):
        probability = numpy.clip(probability, 1e-7, 1.0 - 1e-7)
        return float(
            -(truth * numpy.log(probability) + (1.0 - truth) * numpy.log(1.0 - probability)).mean()
        )

    def order_term(truth, probability):
        curve = dict(isotonic(list(zip(map(float, probability), map(float, truth), strict=True))))
        return entropy(truth, numpy.array([curve[float(value)] for value in probability]))

    labels, groups = context["labels"], context["groups"]
    ours, theirs = _probabilities(context, left, classes), _probabilities(context, right, classes)
    cutpoints, totals = [], {"cross_entropy": 0.0, "order": 0.0, "scale": 0.0}
    for index in range(classes - 1):
        cutpoint = index + 2
        truth = (labels >= cutpoint).astype(float)
        if truth.sum() == 0 or truth.sum() == len(truth):
            cutpoints.append({"cutpoint": cutpoint, "unreadable": "one class only"})
            continue
        mine, yours = ours[:, index], theirs[:, index]
        raw = entropy(truth, mine) - entropy(truth, yours)
        order = order_term(truth, mine) - order_term(truth, yours)

        def statistic(picked, truth=truth, mine=mine, yours=yours):
            here = order_term(truth[picked], mine[picked])
            there = order_term(truth[picked], yours[picked])
            return here - there

        interval = metrics.bootstrap(statistic, groups, draws=DRAWS // 2, seed=BOOTSTRAP_SEED)
        auc = metrics.paired_delta(
            (labels >= cutpoint).astype(int), mine, yours, groups, draws=DRAWS, seed=BOOTSTRAP_SEED
        )
        for key, value in (("cross_entropy", raw), ("order", order), ("scale", raw - order)):
            totals[key] += value / (classes - 1)
        cutpoints.append(
            {
                "cutpoint": cutpoint,
                "positives": int(truth.sum()),
                "delta_cross_entropy": raw,
                "delta_order": order,
                "delta_scale": raw - order,
                "order_ci": [interval["lo"], interval["hi"]],
                "order_reads": (
                    "FLAT"
                    if interval["lo"] is None or (interval["lo"] <= 0 <= interval["hi"])
                    else "DIFFERS"
                ),
                "delta_auc": auc["delta"],
                "auc_ci": [auc["lo"], auc["hi"]],
                "auc_reads": (
                    "FLAT" if auc["lo"] is None or (auc["lo"] <= 0 <= auc["hi"]) else "DIFFERS"
                ),
            }
        )
    share = None if totals["cross_entropy"] == 0 else totals["scale"] / totals["cross_entropy"]
    return {
        "left": left,
        "right": right,
        "sign": "left minus right, so a positive delta means `left` is the worse of the two",
        "mean_over_cutpoints": totals,
        "scale_share_of_the_gap": share,
        "reads": (
            "SCALE ONLY — the two arms order this sheet alike and differ in where they put "
            "the probability"
            if share is not None
            and share > 0.9
            and all(row.get("order_reads", "FLAT") == "FLAT" for row in cutpoints)
            else "the order term carries part of the gap"
        ),
        "cutpoints": cutpoints,
    }


def _arm(arm: dict, context: dict, candidate_runs: list[str], classes: int = 4) -> dict:
    """One arm: the candidate band, the incumbent band, and every paired verdict."""
    labels = context["labels"]
    groups = context["groups"]
    predicted = {
        key: _probabilities(context, key, classes)
        for key in (
            *(f"candidate:{run}" for run in candidate_runs),
            *(f"incumbent:{run}" for run in INCUMBENTS[arm["kind"]]["band"]),
        )
    }
    scored = {key: _statistic_of(arm, labels, values, classes) for key, values in predicted.items()}
    shipped = f"incumbent:{INCUMBENTS[arm['kind']]['shipped']}"

    def against(candidate_key: str, incumbent_key: str) -> dict:
        def statistic(indices):
            ours = _statistic_of(arm, labels[indices], predicted[candidate_key][indices], classes)
            theirs = _statistic_of(arm, labels[indices], predicted[incumbent_key][indices], classes)
            return None if ours is None or theirs is None else ours - theirs

        interval = metrics.bootstrap(statistic, groups, draws=DRAWS, seed=BOOTSTRAP_SEED)
        ours, theirs = scored[candidate_key], scored[incumbent_key]
        delta = None if ours is None or theirs is None else ours - theirs
        worse = _worse(arm, interval["lo"], interval["hi"])
        better = (
            None
            if interval["lo"] is None
            else (interval["hi"] < 0.0 if arm["direction"] == "lower" else interval["lo"] > 0.0)
        )
        return {
            "ours": ours,
            "theirs": theirs,
            "delta": delta,
            "ci": [interval["lo"], interval["hi"]],
            "clusters": interval.get("clusters"),
            "verdict": "WORSE" if worse else ("BETTER" if better else "NOT_RESOLVED"),
        }

    band_run = _median_run(
        {run: scored[f"candidate:{run}"] for run in candidate_runs}, arm["direction"]
    )
    per_seed = {run: against(f"candidate:{run}", shipped) for run in candidate_runs}
    band = against(f"candidate:{band_run}", shipped)
    reported = {
        run: against(f"candidate:{band_run}", f"incumbent:{run}")
        for run in INCUMBENTS[arm["kind"]]["band"]
        if f"incumbent:{run}" != shipped
    }
    failed = band["verdict"] == "WORSE" or any(
        read["verdict"] == "WORSE" for read in per_seed.values()
    )
    return {
        **{key: arm[key] for key in ("key", "kind", "sheet", "statistic", "direction", "gated")},
        "cutpoint": arm.get("cutpoint"),
        "why": arm["why"],
        "candidate_band": {run: scored[f"candidate:{run}"] for run in candidate_runs},
        "incumbent_band": {
            str(run): scored[f"incumbent:{run}"] for run in INCUMBENTS[arm["kind"]]["band"]
        },
        "band_read_on": band_run,
        "band": band,
        "per_seed": per_seed,
        "against_the_incumbent_s_other_seeds": reported,
        "verdict": ("REPORTED" if not arm["gated"] else "FAIL" if failed else "PASS"),
    }


def _variant_split(contexts: dict, name: str, runs: list[str], bands: dict) -> dict:
    """One variant against the candidate it varies, split into scale and order.

    Both sides are read on their own band's median by the scoring rule, so the
    split describes the same two checkpoints the tables above report. `None` when
    the candidate it varies has not been scored — a variant read against nothing
    is a number with no comparison in it.
    """
    against = joint_render.VARIANTS[name]["against"]
    theirs = bands.get(against)
    if not theirs:
        return {"against": against, "unreadable": f"the {against} band is not scored here"}
    out = {"against": against}
    for kind, context in contexts.items():
        arm = next(
            a for a in ARMS if a["kind"] == kind and a["statistic"] == "cutpoint_cross_entropy"
        )
        pick = {
            side: _median_run(
                {
                    run: _statistic_of(
                        arm, context["labels"], _probabilities(context, f"candidate:{run}")
                    )
                    for run in group
                },
                arm["direction"],
            )
            for side, group in (("variant", runs), ("candidate", theirs))
        }
        out[kind] = scale_or_order(
            context, f"candidate:{pick['variant']}", f"candidate:{pick['candidate']}"
        )
        out[kind]["read_on"] = pick
    return out


def _multiplicity(arms: list[dict], candidate_runs: list[str]) -> dict:
    """How many chances the per-seed conjunction gives a good candidate to fail.

    REPORTED, and it changes no verdict — the bar says "per seed and on the band"
    and that is the bar. But the strict reading runs one test per gated arm per
    seed, each one-sided at 2.5%, and a reader is owed the size of that. Five
    gated arms and three seeds is fifteen chances, and a candidate that is
    *exactly* non-inferior everywhere still trips at least one about a third of
    the time. That is a property of the rule rather than evidence about the head,
    and it is why the band-only reading is reported beside it — not instead of it.
    """
    gated = [arm for arm in arms if arm["gated"]]
    tests = len(gated) * len(candidate_runs)
    return {
        "gated_arms": len(gated),
        "seeds": len(candidate_runs),
        "per_seed_tests": tests,
        "one_sided_alpha": 0.025,
        "chance_of_a_crossing_if_exactly_non_inferior": 1.0 - 0.975**tests,
        "crossed_per_seed": [
            f"{arm['key']}:{run}"
            for arm in gated
            for run, out in arm["per_seed"].items()
            if out["verdict"] == "WORSE"
        ],
        "crossed_on_the_band": [arm["key"] for arm in gated if arm["band"]["verdict"] == "WORSE"],
        "band_only_verdict": (
            "FAIL" if any(arm["band"]["verdict"] == "WORSE" for arm in gated) else "PASS"
        ),
        "note": (
            "the band-only verdict reads the same five arms on their own median seed — "
            "one test per arm rather than one per arm per seed"
        ),
    }


def read(runs: list[str] | None = None, candidate: str = joint_render.CURRENT) -> dict:
    """The whole read: every arm, every seed, and what the bar says about them.

    `candidate` names which registered design is being gated. Each has its own
    bar file, written before its band existed, and its own comparison record — a
    superseded candidate's read stays exactly as it was read.
    """
    import numpy

    path = bar_path(candidate)
    if not path.is_file():
        raise JointComparisonError(
            f"{path} is missing. The bar comes from the file and nothing here may invent one."
        )
    declared = json.loads(path.read_text(encoding="utf-8"))
    candidate_runs = list(runs or joint_render.CANDIDATES[candidate]["runs"])

    present = {
        kind: [run for run in ABLATIONS[kind] if joint_render.scores_path(kind, run).is_file()]
        for kind in joint_render.KINDS
    }
    variants = {
        name: [
            run
            for run in entry["runs"]
            if all(joint_render.scores_path(kind, run).is_file() for kind in joint_render.KINDS)
        ]
        for name, entry in joint_render.VARIANTS.items()
    }
    every = [run for runs in variants.values() for run in runs]
    variants_of = {
        name: [
            run
            for run in entry["runs"]
            if all(joint_render.scores_path(kind, run).is_file() for kind in joint_render.KINDS)
        ]
        for name, entry in joint_render.CANDIDATES.items()
    }
    contexts = {
        kind: aligned(
            kind,
            sorted({*candidate_runs, *every, *(r for v in variants_of.values() for r in v)}),
            present[kind],
        )
        for kind in joint_render.KINDS
    }
    arms = [_arm(arm, contexts[arm["kind"]], candidate_runs) for arm in ARMS]
    ablations = {
        "runs": {kind: present[kind] for kind in joint_render.KINDS},
        "absent": {
            kind: [run for run in ABLATIONS[kind] if run not in present[kind]]
            for kind in joint_render.KINDS
        },
        "what_it_is": (
            "one kind's share of exactly the pooled split, at exactly the candidate's "
            "recipe. Paired seed for seed against the candidate, so the only thing that "
            "moves is whether the other kind's rows were in the batch. NO BAR is attached"
        ),
        "arms": [
            ablation_arm(arm, contexts[arm["kind"]], candidate_runs, present[arm["kind"]])
            for arm in ARMS
            if present[arm["kind"]]
        ],
    }
    gated = [arm for arm in arms if arm["gated"]]
    # The seed each kind's own scoring-rule arm was read on, so the decomposition
    # below describes the same checkpoint the table above reports.
    band_run_of = {
        arm["kind"]: arm["band_read_on"]
        for arm in arms
        if arm["statistic"] == "cutpoint_cross_entropy"
    }
    verdict = "FAIL" if any(arm["verdict"] == "FAIL" for arm in gated) else "PASS"

    populations = {}
    for kind, context in contexts.items():
        labels = context["labels"]
        populations[kind] = {
            "sheet": next(arm["sheet"] for arm in ARMS if arm["kind"] == kind),
            "pictures": len(context["names"]),
            "clusters": int(len(numpy.unique(context["groups"]))),
            "tiers": {str(int(t)): int((labels == t).sum()) for t in sorted(set(labels.tolist()))},
        }

    return {
        "schema": SCHEMA,
        "head": joint_render.HEAD,
        "candidate": candidate,
        # `.get` rather than `[]`: the first candidate's bar was registered before
        # this study had a second one to distinguish it from, and a bar is never
        # rewritten to suit a later reader. Its fields are filled from the roster.
        "candidate_is": declared.get("candidate_is", joint_render.CANDIDATES[candidate]["what"]),
        "backbone": declared.get("backbone", joint_render.CANDIDATES[candidate]["backbone"]),
        "bar": {"rule": declared["rule"], "significance": declared["significance"]},
        "candidate_runs": candidate_runs,
        "populations": populations,
        "arms": arms,
        "refused": dict(REFUSED),
        "gain_on_the_smooth_side": _gain(arms),
        "scale_against_order": {
            "what_it_is": (
                "REPORTED, never gated. Each cutpoint's cross-entropy split into what an "
                "in-sample isotonic recalibration removes (the scale) and what survives it "
                "(the order). The same fit the release floors are placed by, so a gap that "
                "lives in the scale term is a gap adoption re-derives anyway"
            ),
            "read_on": {kind: band_run_of[kind] for kind in joint_render.KINDS},
            "cutpoints": {
                kind: decomposition(
                    contexts[kind],
                    {
                        "candidate": f"candidate:{band_run_of[kind]}",
                        "incumbent": f"incumbent:{INCUMBENTS[kind]['shipped']}",
                    },
                )
                for kind in joint_render.KINDS
            },
        },
        "against_the_corpus_matched_ablation": ablations,
        "loss_parity": LOSS_PARITY,
        "multiplicity": _multiplicity(arms, candidate_runs),
        "variants": {
            "what_they_are": (
                "the candidate with ONE thing moved. REPORTED, never gated: this bar was "
                "written about the registered candidate, and a bar a different design could "
                "satisfy is not a bar. Seed counts are stated because they are not bands"
            ),
            "read": {
                name: {
                    "runs": runs,
                    "seeds": len(runs),
                    "what": joint_render.VARIANTS[name]["what"],
                    "arms": [_arm(arm, contexts[arm["kind"]], runs) for arm in ARMS],
                    "against": joint_render.VARIANTS[name]["against"],
                    "scale_or_order": _variant_split(contexts, name, runs, variants_of),
                }
                for name, runs in variants.items()
                if runs
            },
            "absent": {
                name: [run for run in joint_render.VARIANTS[name]["runs"] if run not in runs]
                for name, runs in variants.items()
            },
        },
        "verdict": verdict,
        "adoption": declared["adoption"],
    }


def _gain(arms: list[dict]) -> dict:
    """Informational: does the data-poorer kind gain from being trained beside the other?

    No bar is attached and no verdict here changes the read above. It is the arms
    already computed, pointed the other way: a `BETTER` on a smooth arm is
    transfer if it is anything, and the confound named in [`bar`] is why "if".
    """
    out = {}
    for arm in arms:
        if arm["kind"] != "smooth_render":
            continue
        out[arm["key"]] = {
            "delta": arm["band"]["delta"],
            "ci": arm["band"]["ci"],
            "direction": arm["direction"],
            "band": arm["candidate_band"],
            "incumbent": arm["band"]["theirs"],
            "reads": arm["band"]["verdict"],
        }
    out["caveat"] = (
        "the candidate saw 160 smooth rows the shipped smooth head never did, so a BETTER "
        "here is transfer OR corpus growth. The corpus-matched ablation is the arm that "
        "separates them"
    )
    return out


def disagreements(
    run: str | None = None,
    per_kind: int = 6,
    out_dir: str | None = None,
    candidate: str = joint_render.CURRENT,
) -> dict:
    """Copy out the sheet rows the candidate and the incumbent read most differently.

    Admissions and rejects, per kind, at that sheet's own gated boundary: the rows
    where the candidate's probability sits furthest above the shipped head's, and
    the rows where it sits furthest below. The pictures are the render cache's
    own — nothing re-renders — and they land in `scratch/`, which is disposable.
    """
    destination = Path(out_dir) if out_dir else repo_root() / "scratch" / "joint_disagreements"
    written = {}
    for kind in joint_render.KINDS:
        arm = next(a for a in ARMS if a["kind"] == kind and a["statistic"] == "auc" and a["gated"])
        candidate_runs = [run] if run else list(joint_render.CANDIDATES[candidate]["runs"])
        context = aligned(kind, candidate_runs)
        chosen = run or _median_run(
            {
                name: _statistic_of(
                    arm, context["labels"], _probabilities(context, f"candidate:{name}")
                )
                for name in candidate_runs
            },
            arm["direction"],
        )
        index = int(arm["cutpoint"]) - 2
        ours = _probabilities(context, f"candidate:{chosen}")[:, index]
        theirs = _probabilities(context, f"incumbent:{INCUMBENTS[kind]['shipped']}")[:, index]
        delta = ours - theirs
        order = sorted(range(len(delta)), key=lambda i: delta[i])
        picked = {
            "rejects": order[:per_kind],
            "admissions": list(reversed(order[-per_kind:])),
        }
        crops = renders.crop_dir(kind)
        folder = destination / kind
        folder.mkdir(parents=True, exist_ok=True)
        sidecar = []
        for direction, indices in picked.items():
            for rank, position in enumerate(indices):
                name = context["names"][position]
                source = crops / f"{name}.jpg"
                target = folder / f"{direction}_{rank:02d}_{name}.jpg"
                if source.is_file():
                    shutil.copyfile(source, target)
                row = context["reads"][f"candidate:{chosen}"][name]
                sidecar.append(
                    {
                        "file": target.name,
                        "direction": direction,
                        f"candidate_p_ge{arm['cutpoint']}": float(ours[position]),
                        f"incumbent_p_ge{arm['cutpoint']}": float(theirs[position]),
                        "delta": float(delta[position]),
                        "human_score": int(context["labels"][position]),
                        "partition": row.get("partition"),
                        "mode": row["mode"],
                        "colormap": row["colormap"],
                        "family": row["family"],
                        "viewport": row["viewport"],
                    }
                )
        (folder / "rows.json").write_text(
            json.dumps(
                {
                    "kind": kind,
                    "sheet": arm["sheet"],
                    "boundary": arm["cutpoint"],
                    "candidate_run": chosen,
                    "incumbent_run": INCUMBENTS[kind]["shipped"],
                    "note": "the human score is shown and was never used to choose a row",
                    "rows": sidecar,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written[kind] = {"directory": str(folder), "pictures": len(sidecar), "run": chosen}
    return written


__all__ = [
    "ABLATIONS",
    "ARMS",
    "BOOTSTRAP_SEED",
    "DRAWS",
    "INCUMBENTS",
    "REFUSED",
    "SCHEMA",
    "JointComparisonError",
    "ablation_arm",
    "aligned",
    "bar",
    "bar_path",
    "decomposition",
    "comparison_path",
    "disagreements",
    "read",
    "scale_or_order",
    "write_bar",
]
