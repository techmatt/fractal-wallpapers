"""The run that makes the head that ships: three seeds, one holdout, one artifact.

Every band before this one produced fold models and nothing deployable.
A cross-validation screen, since deleted, read three arms on one fifth of the
[`render_folds`] deal, [`render_grade`] graded two arms over all five at two
seeds, and [`render_dose`] read a curve — and
none of them ever trained a head on a whole corpus, because none of them was
supposed to. **This one is.** Three training runs that differ only in the seed,
and the best of them ships.

The recipe is the incumbent's, unchanged in every respect but the stopping rule
below. Nothing about capacity, aspect, input size or architecture moves.

## The split is a plain random eighty-twenty, and the twenty has ONE job

Over **lineages** — the near-duplicate neighbourhoods [`labeling.groups`] finds,
the unit every split and every interval in this project is drawn over, because
two frames a hair apart on one plane are the same picture twice.

There is no date carve-out, no comparison side and no holdout built around the
blind sheets. The 20% exists to stop the run and for nothing else, and it is
reported as what it is: a **selection** slice, not an instrument. The head this
produces is not read against the incumbent here at all — a forward draw on a live
pool is what compares two heads honestly, and this module's job is only to
produce the best head the labels support.

⚠ **So no number in this run's record is a level, and none of them is a
comparison.** The per-epoch table says which epoch the rule liked; it does not
say the head is good, and a stopping-slice statistic read as though it were a
test-set one would be reading a number the epoch was chosen on.

### The predecessor, and why it is not repeated

The run before this one held out every row registered after the shipped
artifact trained, so that the two heads could be compared on rows neither had
seen. It worked as designed and answered nothing: the post-cut rows were 73%
`>=3` by construction — drawn off the incumbent's own top and off calibration
bands — so the incumbent scored a perfect 1.000 in the top decile and a
precision-at-`>=3` comparison there cannot separate two heads. Worse, the
constraint cost the candidate exactly the rows the retrain existed for. **Both
of those are properties of the design rather than of the day it ran**, which is
why the forward holdout is gone from this module rather than parameterised, and
why [`render_train.MISLAUNCHED`]-style archaeology is not needed: the run it
produced is on disk, its report says what it said, and no code here reads it.

## The pin is obeyed exactly as the trainer already enforces it, and no further

[`render_train.run`] refuses to train on a place pinned to a blind sheet and
refuses to early-stop on one. That is the whole constraint this module honours.
It follows that a pinned place cannot sit on the training side, so **a lineage
carrying one is held out**; and that a pinned row cannot be in the stopping
statistic, so it sits on the side the trainer never touches. Both facts are
consequences of the trainer's own guard rather than a rule this module adds — the
blind sheets stay unspent because nothing here reads them, not because anything
here was designed around them.

That closure is 837 rows of 11,019 at this writing, 598 of them pinned outright.
It is under the 20% the split wants, so the draw fills the rest at random and the
holdout lands on its share rather than overshooting it. It was 802 of 10,299 for
the `deploy` band; the pinned count is the same 598 both times, because a sitting
grows the training side and the pin is the thing that never moves.

## The stopping rule is AVERAGE PRECISION at `>=3`

Rank the stopping slice by the head's own `P(>=3)`; a hit is a row a person
scored 3 or 4; the statistic is the area under the precision-recall curve of that
ranking.

**Not the pooled cutpoint cross-entropy the incumbent uses**, which is decided by
the `>=2` boundary and stops the run where the easy question is happy. **Not
precision at a single k**, which is what the predecessor stopped on and which
moved in steps of one row: at k=100 it chose epoch 1 over epoch 5 by a single
row while every other reading was still climbing. Average precision reads the
whole ranking at one boundary, so it cannot be decided by one row at one
cutpoint, and it still weights the top — which is where this head is used.

**Not AUC**, except as the fallback. [`AVERAGE_PRECISION_SAYS`] is what runs;
AUC(`>=3`) is what a run states it fell back to if average precision comes back
undefined, which happens only where the slice is all hits or all misses.

Both, plus precision at 4 / 10 / 20%, are logged **every epoch** whichever one is
choosing, so the rule's choice is inspectable against the readings it did not
make. The three fractions are the mine's own rates: over the live judge's score
rows in the candidate ledger, `curation.mine.SEATING_BAR` admits about a tenth
and `mine.PRIMED_BAR` about a twenty-fifth.

## Three seeds, and the seeds are the read on the rule

[`SEEDS`] runs the split three times. The seed moves the split and the
initialization together — one seed per run, not a grid — and **the run whose
chosen epoch has the best stopping-slice statistic is the one that ships.**

Three curves side by side are also the only evidence available here about whether
the rule is trustworthy: chosen epochs that cluster say the rule is reading
signal, and chosen epochs three seeds apart say it is reading noise. That read
costs three runs and nothing else, which is why it is here.

## What this does NOT do

It does not re-score the candidate pool. Matt has ruled that mixed-vintage scores
are accepted and the ledger is re-scored lazily, and the sidecar already carries
what that needs: every score row is keyed `(recipe, judge artifact, regime)` and
names its `judge_artifact` outright, so a row written after this ships is
attributable to this head and a row written before it names the one before.

It does not restate a floor either. Three acting bars stamp the render artifact
they were measured on and refuse from the first call after a flip, which is
[`cuts.Restatement`] working as designed — `head floor --head <kind>` is what
re-measures them and declaring the height is a person's edit to
`curation.floors`.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.labeling import groups
from fractal_wallpapers.models import (
    finished_train,
    metrics,
    render_folds,
    render_train,
    train,
)
from fractal_wallpapers.paths import under

#: The schema every record here carries.
SCHEMA = 1

#: The run whose artifact serves today, named so a report can say what "absent"
#: means on a score row that carries no judge of its own.
INCUMBENT_RUN = "enlarged_corpus_seed1"

#: What share of the rows the holdout is drawn to hold. The 20% of a plain
#: eighty-twenty; lineages are taken whole, so the realized share lands near this
#: rather than on it, and the realized share is what every record says.
HOLDOUT_SHARE = 0.20

#: The three seeds, each moving the split and the initialization together. One
#: seed per run rather than a grid: the question three of them answer is whether
#: the stopping rule agrees with itself, and that needs the split to move.
SEEDS: tuple[int, ...] = (0, 1, 2)

#: The name each seed's run and directory carries under `models/render/`.
RUN_PREFIX = "deploy_seed"

#: The band a run belongs to, and the first half of every name in it. One band is
#: one whole pass of this module — three seeds over the corpus as it stood — and
#: the band is in the name so that a later pass does not land on an earlier one's
#: checkpoints. [`DEPLOY`] is the pass that shipped weights-v5 and keeps the bare
#: `deploy_seed<N>` names it was written under; every later band prefixes its own.
DEPLOY = "deploy"
BAND = DEPLOY

#: What each band was, in one sentence. A band that is not here is a scratch pass:
#: nothing reads it and no artifact came out of it.
BANDS: dict[str, str] = {
    DEPLOY: (
        "the first pass of this module, 2026-08-30. Shipped weights-v5 out of "
        "deploy_seed1 at epoch 17, its chosen epochs 3/17/9 — a spread of fourteen, so "
        "the rule was not reading signal, and the shipping seed stopped at the cap"
    ),
    "deploy_v6": (
        "the same recipe and the same rule over the stores after the dtm-variants, "
        "judge-band, phoenix-q3q4 and phoenix-classic sittings landed, 2026-09-03. No "
        "recipe key moves; the corpus is what grew. Shipped weights-v6"
    ),
}

#: The fractions every epoch's precision is reported at. 0.10 is about the rate
#: the seating stage admits at (9.76% of the ledger's live score rows clear
#: `curation.mine.SEATING_BAR`); 0.04 is about the primed bar's (3.88% clear
#: `mine.PRIMED_BAR`); 0.20 is the loose end, reported so a reader can see
#: whether a reading turns on the choice. **None of them stops anything** — that
#: is the whole difference between this run and the one before it.
REPORTED_SLICES = (0.04, 0.10, 0.20)

#: The column the rule ranks by, and the boundary a hit is counted at. The same
#: boundary on purpose: a statistic at `>=3` read off an ordering by `P(>=3)` is
#: one question asked once, where ranking on one cutpoint and scoring on another
#: is two.
RANK_COLUMN = "p_ge3"
HIT_TIER = 3

#: The epoch ceiling and the patience. Twenty because every stopping rule ever
#: read on these stores picked an epoch under fifteen; six because a rule that
#: can run away ships a budget rather than a choice.
EPOCHS = 20
PATIENCE = 6


class DeployError(RuntimeError):
    """A split, a fit or a choice that cannot be made on what is here."""


def root() -> Path:
    """Where this run's derived records land. The regenerable tree."""
    return under("render_deploy")


def run_name(seed: int, band: str = BAND) -> str:
    """`deploy_seed<N>` for the first band, `<band>_seed<N>` for every later one.

    The first band's names are bare because they were written before there was a
    second one and its records are on disk under them. Renaming those would make
    every report that quotes `deploy_seed1` wrong about a run that still exists.
    """
    if str(band) == DEPLOY:
        return f"{RUN_PREFIX}{int(seed)}"
    return f"{band}_seed{int(seed)}"


def run_dir(seed: int, band: str = BAND) -> Path:
    """Where one seed's checkpoints land: beside the shipped heads, as bands do."""
    return render_train.head_dir(run_name(seed, band))


# --------------------------------------------------------------------------- #
# The split.
# --------------------------------------------------------------------------- #
#: The two sides of the holdout, by the names [`render_train.run`] gives them.
#: The stopping slice is that function's `SELECTION` because this module owns a
#: split and not a second trainer; the pinned rows are `eval`, which is the side
#: that loop never touches at all.
STOPPING, PINNED = render_train.SELECTION, "eval"


def sides_for(seed: int, population=None) -> tuple[list[dict], list, dict]:
    """The whole corpus with every picture on the side a seeded 80/20 puts it.

    Lineages carrying a pinned place go first, because the trainer will not have
    them on either side it touches; the rest of the 20% is a seeded draw over
    whole lineages. Inside the holdout a pinned row lands on [`PINNED`] and every
    other row on [`STOPPING`], which is what keeps the pinned rows out of the
    statistic the epoch is chosen on without adding a constraint of this module's
    own.
    """
    rows, pictures, record = population or render_folds.pool()
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise DeployError(
            f"{grouping.n_unplaced} rows carry no location identity, so they cannot be "
            f"grouped. A holdout quietly holding ungrouped rows leaks by exactly the amount "
            f"nobody counted."
        )
    lineage = [int(group) for group in grouping.of_row]
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    if not pinned:
        raise DeployError(
            "neither store pins an evaluation side, so nothing here can tell a blind sheet "
            "from a training row. The pin is the trainer's guard and this split is built on it."
        )

    members: dict[int, list[int]] = {}
    for index, group in enumerate(lineage):
        members.setdefault(group, []).append(index)

    forced = {lineage[index] for index, picture in enumerate(pictures) if picture.place in pinned}
    forced_rows = sum(len(members[group]) for group in forced)

    wanted = round(len(pictures) * HOLDOUT_SHARE)
    order = sorted(group for group in members if group not in forced)
    random.Random(int(seed)).shuffle(order)
    drawn: set[int] = set()
    held_rows = forced_rows
    for group in order:
        if held_rows >= wanted:
            break
        drawn.add(group)
        held_rows += len(members[group])
    held = forced | drawn
    if held_rows >= len(pictures):
        raise DeployError("the holdout swallowed the corpus; there is nothing left to train on")

    for picture, group in zip(pictures, lineage, strict=True):
        if group not in held:
            picture.side = "train"
        else:
            picture.side = PINNED if picture.place in pinned else STOPPING

    training = [picture for picture in pictures if picture.side == "train"]
    stopping = [picture for picture in pictures if picture.side == STOPPING]
    held_pins = [picture for picture in pictures if picture.side == PINNED]
    if not stopping:
        raise DeployError("the holdout is all pinned rows, so there is nothing to stop on")

    split = {
        "schema": SCHEMA,
        "rule": (
            f"a seeded random {1 - HOLDOUT_SHARE:.0%}/{HOLDOUT_SHARE:.0%} over LINEAGES. No "
            f"date carve-out and no comparison side: the holdout's only job is to stop the "
            f"run. A lineage carrying a pinned place is held out first, because the trainer "
            f"refuses to train on one, and the pinned rows themselves sit on the side it "
            f"never touches so that they are out of the stopping statistic"
        ),
        "unit": "lineage — labeling.groups.assign",
        "seed": int(seed),
        "target_share": HOLDOUT_SHARE,
        "population": record,
        "grouping": grouping.summary(),
        "rows": len(pictures),
        "lineages": len(members),
        "sides": {
            "train": len(training),
            "stopping": len(stopping),
            "pinned_held": len(held_pins),
        },
        "holdout_share": round((len(stopping) + len(held_pins)) / len(pictures), 4),
        "holdout": {
            "target_rows": wanted,
            "rows": len(stopping) + len(held_pins),
            "lineages": len(held),
            "forced_by_a_pinned_place": {
                "lineages": len(forced),
                "rows": forced_rows,
                "pinned_rows": len(held_pins),
                "carried_in_by_lineage_closure": forced_rows - len(held_pins),
            },
            "drawn_at_random": {
                "lineages": len(drawn),
                "rows": held_rows - forced_rows,
                "of_available_lineages": len(order),
            },
        },
        "stopping_slice": {
            "rows": len(stopping),
            "lineages": len(
                {group for group, p in zip(lineage, pictures, strict=True) if p.side == STOPPING}
            ),
            "tiers": finished_train.histogram(stopping),
            "excludes": (
                "every pinned row. The trainer refuses to early-stop on a pinned place, so "
                "the statistic is read on the non-pinned part of the holdout"
            ),
        },
        "pinned_rows": {
            "rows": len(held_pins),
            "tiers": finished_train.histogram(held_pins),
            "side": PINNED,
            "spent": (
                "no. They train nothing, they stop nothing, and nothing in this module reads "
                "them — the two blind sheets are as unspent after this run as before it"
            ),
        },
        "train_tiers": finished_train.histogram(training),
    }
    return rows, pictures, split


def split_path(seed: int, band: str = BAND) -> Path:
    """Where one seed's split record lands. The first band's names stay bare."""
    stem = f"split_seed{int(seed)}" if str(band) == DEPLOY else f"split_{band}_seed{int(seed)}"
    return root() / f"{stem}.json"


def choice_path(band: str = BAND) -> Path:
    """Where one band's three curves and its pick land."""
    return root() / ("choice.json" if str(band) == DEPLOY else f"choice_{band}.json")


def write_split(seed: int, band: str = BAND) -> tuple[Path, dict]:
    _rows, _pictures, split = sides_for(seed)
    split["band"] = str(band)
    split["run"] = run_name(seed, band)
    path = split_path(seed, band)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, split


# --------------------------------------------------------------------------- #
# The stopping rule, and the readings logged beside it.
# --------------------------------------------------------------------------- #
def rank_scores(probabilities):
    """The column [`HIT_TIER`] is ranked on, out of a head's cutpoint probabilities."""
    import numpy

    return numpy.asarray(probabilities)[:, int(HIT_TIER) - 2]


def hits_of(labels):
    import numpy

    return (numpy.asarray(labels) >= int(HIT_TIER)).astype(int)


def precision_at(labels, scores, fraction: float, tier: int = HIT_TIER) -> dict:
    """What share of the top `fraction` of a ranking a person scored `tier` or better.

    Ties at the cut are taken in the order the sort gives, which is stable, so
    the statistic is a function of the scores and not of when it was called. `k`
    is at least one: a top slice of nothing is not a precision of zero.
    """
    import numpy

    labels = numpy.asarray(labels)
    scores = numpy.asarray(scores, dtype=float)
    if labels.size == 0:
        return {"k": 0, "hits": 0, "precision": None, "base_rate": None}
    k = max(1, int(round(len(scores) * float(fraction))))
    top = numpy.argsort(-scores, kind="stable")[:k]
    hits = int((labels[top] >= tier).sum())
    return {
        "k": k,
        "hits": hits,
        "precision": hits / k,
        "base_rate": float((labels >= tier).mean()),
    }


def average_precision_selection(labels, probabilities, classes: int) -> float:
    """`-AP(>=3)` over the stopping slice, as an epoch objective to MINIMIZE.

    Negated so it takes [`render_train.run`]'s selection contract unchanged — one
    convention for every rule this project has, rather than a maximizer and a
    minimizer a reader has to keep apart.

    **Rank-only**, so shrinking every probability toward the prior cannot win it
    the way it wins a cross-entropy at a rare cutpoint. And it reads the whole
    ranking at one boundary rather than one k, which is what the rule before it
    did and what let a single row at k=100 choose the epoch.
    """
    del classes
    read = metrics.average_precision(hits_of(labels), rank_scores(probabilities))
    return float("inf") if read is None else -float(read)


def auc_selection(labels, probabilities, classes: int) -> float:
    """`-AUC(>=3)`, the fallback. Stated on the record whenever it is the one used."""
    del classes
    read = metrics.auc(hits_of(labels), rank_scores(probabilities))
    return float("inf") if read is None else -float(read)


AVERAGE_PRECISION_SAYS = (
    f"max average precision at >={HIT_TIER} over the non-pinned part of the holdout, ranked "
    f"by P(>={HIT_TIER}) and counting a row a person scored {HIT_TIER} or better as a hit, "
    f"through the deploy transform. Rank-only, and it reads the whole ranking rather than one "
    f"k — the rule it replaces moved in steps of one row"
)

AUC_SAYS = (
    f"max AUC at >={HIT_TIER} over the non-pinned part of the holdout — the FALLBACK, used "
    f"only where average precision is undefined on this slice"
)

#: The rule and the sentence that goes on the record with it. A tuple rather than
#: two constants, so a run cannot record one and use the other.
RULES = {
    "average_precision": (average_precision_selection, AVERAGE_PRECISION_SAYS),
    "auc": (auc_selection, AUC_SAYS),
}
RULE = "average_precision"


def readouts(labels, probabilities, classes: int) -> dict:
    """Every reading this run logs per epoch beside the one that chooses.

    `render_train.run` already writes `selection_ap_ge3` and `selection_auc_ge3`,
    so what is added here is the three precisions — the readings the predecessor
    stopped on, kept as readings so that the two runs' epoch tables are legible
    against each other.
    """
    del classes
    scores = rank_scores(probabilities)
    out = {}
    for fraction in REPORTED_SLICES:
        read = precision_at(labels, scores, fraction)
        out[f"precision_at_{int(round(fraction * 100)):02d}"] = read["precision"]
        out[f"precision_at_{int(round(fraction * 100)):02d}_k"] = read["k"]
    return out


# --------------------------------------------------------------------------- #
# The runs.
# --------------------------------------------------------------------------- #
def fit(
    seed: int,
    device: str = "auto",
    epochs: int | None = None,
    rule: str = RULE,
    band: str = BAND,
    workers: int | None = None,
    log=None,
):
    """Train one seed of the head that ships: the incumbent recipe, the new rule."""
    if rule not in RULES:
        raise DeployError(f"{rule!r} is not a stopping rule here; they are {sorted(RULES)}")
    objective, says = RULES[rule]
    directory = run_dir(seed, band)
    directory.mkdir(parents=True, exist_ok=True)

    def split():
        _rows, pictures, record = sides_for(seed)
        return pictures, record

    return render_train.run(
        device=device,
        epochs=EPOCHS if epochs is None else int(epochs),
        seed=int(seed),
        run_name=run_name(seed, band),
        backbone=render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        target_dims=None,
        split=split,
        directory=directory,
        selection=objective,
        selection_says=says,
        patience=PATIENCE,
        readouts=readouts,
        workers=workers,
        log=log or train.say,
    )


def epoch_curve(seed: int, band: str = BAND) -> dict:
    """What one seed's rule saw, epoch by epoch, and where it stopped."""
    path = run_dir(seed, band) / "metrics.json"
    if not path.is_file():
        raise DeployError(f"{path} does not exist — seed {seed} wrote no trace")
    record = json.loads(path.read_text(encoding="utf-8"))
    history = record.get("history") or []
    return {
        "run": run_name(seed, band),
        "band": str(band),
        "seed": int(seed),
        "rule": record.get("selection_metric"),
        "epochs_run": len(history),
        "of_epochs": EPOCHS,
        "patience": PATIENCE,
        "best_epoch": record.get("best_epoch"),
        "chosen_objective": (
            None
            if record.get("best_selection_objective") is None
            else -float(record["best_selection_objective"])
        ),
        "stopped_early": record.get("stopped_early"),
        "wall_seconds": record.get("wall_seconds"),
        "stopping_rows": (record.get("pictures") or {}).get("selection"),
        "trace": [
            {
                "epoch": row["epoch"],
                "loss": row.get("loss"),
                "chosen_on": (
                    None if row.get("selection_loss") is None else -float(row["selection_loss"])
                ),
                "ap_ge3": row.get("selection_ap_ge3"),
                "auc_ge3": row.get("selection_auc_ge3"),
                **{
                    key: row.get(key)
                    for key in row
                    if key.startswith("precision_at_") and not key.endswith("_k")
                },
            }
            for row in history
        ],
    }


def choose(seeds=SEEDS, band: str = BAND) -> dict:
    """The three curves side by side, and the seed that ships.

    **The best chosen-epoch statistic wins**, which is the rule declared before
    any of them ran. The spread of the chosen epochs is reported beside it
    because it is the read on whether the rule is trustworthy at all: epochs that
    cluster say it is reading signal, epochs three seeds apart say it is not.
    """
    curves = [epoch_curve(seed, band) for seed in seeds]
    scored = [curve for curve in curves if curve["chosen_objective"] is not None]
    if not scored:
        raise DeployError("no seed recorded a chosen objective, so there is nothing to choose on")
    winner = max(scored, key=lambda curve: curve["chosen_objective"])
    epochs = [curve["best_epoch"] for curve in scored]
    return {
        "schema": SCHEMA,
        "band": str(band),
        "was": BANDS.get(str(band), "a scratch pass: no artifact came out of it"),
        "rule": RULE,
        "says": RULES[RULE][1],
        "seeds": list(seeds),
        "curves": curves,
        "ships": {
            "seed": winner["seed"],
            "run": winner["run"],
            "epoch": winner["best_epoch"],
            "chosen_objective": winner["chosen_objective"],
            "checkpoint": str(run_dir(winner["seed"], band) / "best.pt"),
        },
        "chosen_epochs": epochs,
        "epoch_spread": (max(epochs) - min(epochs)) if epochs else None,
        "objective_spread": round(
            max(curve["chosen_objective"] for curve in scored)
            - min(curve["chosen_objective"] for curve in scored),
            6,
        ),
    }


def write_choice(seeds=SEEDS, band: str = BAND) -> tuple[Path, dict]:
    document = choose(seeds, band)
    path = choice_path(band)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, document


__all__ = [
    "AUC_SAYS",
    "BAND",
    "BANDS",
    "DEPLOY",
    "AVERAGE_PRECISION_SAYS",
    "EPOCHS",
    "HIT_TIER",
    "HOLDOUT_SHARE",
    "INCUMBENT_RUN",
    "PATIENCE",
    "PINNED",
    "RANK_COLUMN",
    "REPORTED_SLICES",
    "RULE",
    "RULES",
    "RUN_PREFIX",
    "SCHEMA",
    "SEEDS",
    "STOPPING",
    "DeployError",
    "auc_selection",
    "average_precision_selection",
    "choice_path",
    "choose",
    "epoch_curve",
    "fit",
    "hits_of",
    "precision_at",
    "rank_scores",
    "readouts",
    "root",
    "run_dir",
    "run_name",
    "sides_for",
    "split_path",
    "write_choice",
    "write_split",
]
