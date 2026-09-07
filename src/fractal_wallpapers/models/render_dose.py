"""A dose curve for the render judge: one recipe, increasing amounts of label data.

[`fractal_wallpapers.models.render_grade`] graded three *recipe* changes against
each other and adopted nothing. It never asked the era's own question. The stores
grew from 8,977 rows over 2,939 lineages to 10,299 over 3,649 while that band was
being designed, and strange fours went from 245 to 414 — the growth the labeling
existed for — and nothing has measured whether that helped.

This module is that measurement, and it is a **dose curve rather than an arms
comparison**. One recipe — the incumbent, the incumbent stopping rule, unchanged
in every other respect — is refit on increasing amounts of label data and read on
one holdout that does not move.

## Nothing here adopts anything

No `models/render/` artifact ships, no sidecar is re-scored, no floor moves, no
registry is opened for writing. Every run lands in the regenerable tree.

## The dose axis is BATCH REGISTRATION DATE, and that is a choice with a reason

A batch is registered before its first row exists — [`labeling.registry`] makes
that a property of the store rather than of anybody's discipline — so the
registration dates are a clock the corpus carries and nobody has to reconstruct.
The alternative was to work out what the shipped artifact actually saw, and that
is a reconstruction: the artifact's own population file joins on a file and a
line, and a tenth of its rows no longer address what they addressed.

The cut is applied to the row's **batch**, not to the row's `recorded_at`. Rows
do trickle into a batch after it is registered — 51 of `mode_correction`'s 1,000
were recorded after its registration row — but a batch is one population drawn by
one method, and splitting one population across two doses would put two views of
one draw on two sides of the axis. A whole batch arrives or it does not.

## The holdout is FIXED, and this is where the design earns its keep

Every point on the curve is read on **the same rows**: the five-way lineage deal
[`render_folds.assignment`] already wrote, re-used rather than re-dealt. At every
dose, fold `k`'s model trains on that dose's rows *outside* fold `k`'s lineages
and is read on fold `k`'s lineages — every row of them, whatever date they
arrived. Pooled over the folds, the holdout is all 10,299 rows at every point on
the curve, each one scored by a model blind to its lineage.

**A holdout lineage never trains at any dose.** That is what makes the axis
readable: the only thing that moves between two points is how many rows the model
was allowed to fit on.

⚠ **What this deviates from, and why.** The obvious construction is to draw the
holdout out of the lineages present in the *smallest* dose. On this corpus that
is unreadable, and the reason is worth writing down rather than rediscovering:
the rank key's columns need a candidate-ledger join, and **85% of the rows
that have one arrived in the last three days of the era**. A holdout confined to
lineages present before 2026-08-24 reaches 268 rows a person scored 3 or 4 that
the key can be read on at all, against 1,421 here — and at the earliest cut it
reaches 60. The declared primary would have been read on sixty rows. Holding the
holdout out of the *whole* deal keeps every invariant that construction was for —
identical rows at every point, no dose training on a holdout lineage — and costs
only this: a holdout lineage that arrived late is still held out at the early
doses, where it would not have been available to train on anyway.

## Two legs, and the second one is what says whether the first is about rows

**The era curve** is the dose axis above: the corpus as it actually stood at five
registration dates. Its slope is confounded on purpose — the new batches are more
rows *and* different rows, and the era bought both.

**The matched draw** unconfounds it. From the *grown* corpus, lineages are drawn
at random until the training side matches the pre-growth point's row count
exactly, twice under two independent seeds. If the same number of rows drawn from
the grown corpus reads like the grown corpus, the era bought composition; if it
reads like the pre-growth point, the era bought rows. And the **spread between
the two draws is the only honest noise floor this design has** — the era points
carry no draw at all, because a date is not a random variable.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.models import (
    finished_train,
    head,
    metrics,
    render_folds,
    render_grade,
    render_train,
    train,
)
from fractal_wallpapers.paths import repo_root, under

#: The schema every record here carries.
SCHEMA = 1

#: Draws in every interval here and its seed — [`render_folds`]'s own, so an
#: interval from this module and one from the grading band are the same statistic.
DRAWS, BOOTSTRAP_SEED = render_folds.DRAWS, render_folds.BOOTSTRAP_SEED

#: The stop slice, taken from [`render_grade`] unchanged: a fifth of the training
#: side's LINEAGE GROUPS, seeded per fold. It is drawn over the **whole** trainable
#: side and then cut down by the dose, so every point on the curve stops against a
#: nested subset of one population rather than against its own fresh draw.
STOP_SHARE, STOP_SEED = render_grade.STOP_SHARE, render_grade.STOP_SEED

#: The epoch ceiling and the patience. [`render_grade`]'s, and the same numbers
#: for the same reason: every stopping rule on the record picks an epoch under
#: fifteen. Only the incumbent rule runs here, so the patience is read off it
#: alone and the loop stops sooner than that band's did.
EPOCHS, PATIENCE = render_grade.EPOCHS, render_grade.PATIENCE

#: The stopping rule, and it is the incumbent's: the pooled cutpoint
#: cross-entropy over the stop slice, whose checkpoint is `best.pt`. This band
#: moves the data and nothing else, so the rule the shipped artifact was selected
#: under is the rule every point here is selected under.
RULE = render_grade.SHIPPED_RULE

#: The seed every run trains at. One seed, because the budget buys points on the
#: curve or repeats of one point and the curve is what was asked for. The matched
#: draw is what bounds run-to-run spread; see this module's header.
SEED = 0


class DoseError(RuntimeError):
    """A dose point that cannot be built, fitted or read on what is here."""


def root() -> Path:
    """Where the dose runs live: the regenerable tree, never a run directory."""
    return under("render_dose")


def run_dir(point: str, fold: int) -> Path:
    return root() / point / f"fold{fold}"


# --------------------------------------------------------------------------- #
# The dose points.
# --------------------------------------------------------------------------- #
#: The era curve, by batch registration date. Five cuts, and the corpus counts
#: beside each one are what the stores hold at that date — not what any point
#: trains on, which is smaller by a fold and by the pinned rows.
#:
#: `2026-08-24` is **the pre-growth point**: the shipped `enlarged_corpus` band
#: was trained that afternoon, after the manufactured rare-colour batch was
#: registered that morning and before anything else was. `2026-08-29` is the
#: whole grown corpus.
ERA_CUTS: tuple[tuple[str, str], ...] = (
    ("era_0815", "2026-08-15"),
    ("era_0817", "2026-08-17"),
    ("era_0824", "2026-08-24"),
    ("era_0827", "2026-08-27"),
    ("era_0829", "2026-08-29"),
)

#: The point the whole curve is read against, and the point the matched draw
#: matches: the corpus as it stood when the artifact that serves today was
#: trained.
PRE_GROWTH = "era_0824"

#: The largest point — the corpus as it stands.
GROWN = "era_0829"

POINTS: dict[str, dict] = {
    name: {
        "leg": "era",
        "cut": cut,
        "what": f"every row whose batch was registered on or before {cut}",
    }
    for name, cut in ERA_CUTS
}
for _draw, _seed in (("matched_a", 101), ("matched_b", 202)):
    POINTS[_draw] = {
        "leg": "matched",
        "matches": PRE_GROWTH,
        "draw_seed": _seed,
        "what": (
            f"lineages drawn at random from the GROWN corpus under seed {_seed} until the "
            f"training side matches {PRE_GROWTH}'s row count. The same quantity of rows, "
            f"different rows"
        ),
    }


def registration_dates() -> dict[tuple[str, str], str]:
    """`(kind, batch)` to the day that batch was registered, both stores.

    A batch name is only unique inside a store — `manufactured_rare_colors` is
    registered separately in each — so the kind is half the key.
    """
    out: dict[tuple[str, str], str] = {}
    for kind in render_train.KINDS:
        path = repo_root() / "data" / kind / "batches.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            out[(kind, str(row["batch"]))] = str(row["registered_at"])[:10]
    return out


# --------------------------------------------------------------------------- #
# The split: the deal's folds, the grading band's stop slice, this module's dose.
# --------------------------------------------------------------------------- #
def sides_for(point: str, fold: int, document: dict | None = None, population=None):
    """The population with every picture on the side this fold and this dose put it.

    [`render_grade.sides_for`] with one thing added and nothing else moved: a
    training or stop-slice picture whose batch is outside the dose is demoted to
    [`render_train.EXCLUDED`]. The holdout is untouched by the dose — that is the
    whole point of the design — and so is the exclusion of a pinned location.

    The stop slice is drawn **before** the dose is applied, over the whole
    trainable side, so the doses' stop slices are nested rather than independent.
    A slice re-drawn per dose would put a slice difference inside every contrast.
    """
    if point not in POINTS:
        raise DoseError(f"{point!r} is not a dose point here; they are {sorted(POINTS)}")
    entry = POINTS[point]
    document = document or render_folds.read_assignment()
    rows, pictures, record = population or render_folds.pool()
    group_of_row = [int(group) for group in document["group_of_row"]]
    rows, pictures, base = render_grade.sides_for(fold, document, (rows, pictures, record))

    dates = registration_dates()
    keep = _dose_filter(entry, rows, pictures, group_of_row, dates, base)

    demoted = {"train": 0, render_train.SELECTION: 0}
    for index, picture in enumerate(pictures):
        if picture.side in ("train", render_train.SELECTION) and not keep[index]:
            demoted[picture.side] += 1
            picture.side = render_train.EXCLUDED

    training = [p for p in pictures if p.side == "train"]
    choosing = [p for p in pictures if p.side == render_train.SELECTION]
    if not choosing:
        raise DoseError(f"{point} fold {fold} leaves no stop slice; the dose is too small")

    named = (
        {"cut": entry["cut"]}
        if entry["leg"] == "era"
        else {"matches": entry["matches"], "draw_seed": entry["draw_seed"]}
    )
    split = {
        **base,
        "dose": {
            "point": point,
            "leg": entry["leg"],
            "declared": entry["what"],
            **named,
            "held_out_of_training": demoted,
            "train_pictures": len(training),
            "stop_pictures": len(choosing),
            "train_lineages": len(
                {group_of_row[i] for i, p in enumerate(pictures) if p.side == "train"}
            ),
            "train_tiers": finished_train.histogram(training),
            "train_strange_fours": sum(
                1 for p in training if p.kind == "strange_render" and p.score >= 4
            ),
            "rule": (
                "a whole batch is inside the dose or outside it, by the day it was "
                "REGISTERED. The holdout never moves"
            ),
        },
    }
    return rows, pictures, split


def _dose_filter(entry, rows, pictures, group_of_row, dates, base) -> list[bool]:
    """Which pictures this dose lets train, as a mask over the whole population.

    The holdout and the pinned exclusions are already decided by the fold; this
    answers only the question the dose asks, and it answers it for every picture
    so that the caller never has to know which leg it is on.
    """
    if entry["leg"] == "era":
        cut = entry["cut"]
        return [
            dates[(picture.kind, picture.batch)] <= cut
            for picture, row in zip(pictures, rows, strict=True)
        ]

    # The matched leg: draw whole lineages out of the grown corpus until the
    # trainable side is the size the matched point's trainable side is. Lineages
    # rather than rows, because two views of one place on two sides of this
    # boundary is the leak the whole split exists to prevent.
    target = _trainable_rows(entry["matches"], pictures, dates, base)
    trainable = [
        index
        for index, picture in enumerate(pictures)
        if picture.side in ("train", render_train.SELECTION)
    ]
    by_lineage: dict[int, list[int]] = {}
    for index in trainable:
        by_lineage.setdefault(group_of_row[index], []).append(index)
    order = sorted(by_lineage)
    random.Random(int(entry["draw_seed"])).shuffle(order)

    keep = [False] * len(pictures)
    taken = 0
    for lineage in order:
        members = by_lineage[lineage]
        if taken + len(members) > target:
            continue
        for index in members:
            keep[index] = True
        taken += len(members)
    return keep


def _trainable_rows(point: str, pictures, dates, base) -> int:
    """How many rows the matched point's training side holds on this same fold.

    Counted off the fold's own sides rather than off a written record, so the
    match is exact on the fold it is made for and cannot drift from one.
    """
    cut = POINTS[point]["cut"]
    return sum(
        1
        for picture in pictures
        if picture.side in ("train", render_train.SELECTION)
        and dates[(picture.kind, picture.batch)] <= cut
    )


def plan(folds=(0, 1, 2, 3, 4), points=None) -> dict:
    """Every point's training side on every fold, before anything is fitted.

    What a launch is priced off and what a report quotes: the dose axis in rows,
    the strange fours beside it, and the holdout that does not move.
    """
    document = render_folds.read_assignment()
    population = render_folds.pool()
    out = {"schema": SCHEMA, "folds": list(folds), "points": []}
    for point in points or list(POINTS):
        cells = []
        for fold in folds:
            _rows, _pictures, split = sides_for(point, fold, document, population)
            cells.append(
                {
                    "fold": fold,
                    "train": split["dose"]["train_pictures"],
                    "stop": split["dose"]["stop_pictures"],
                    "lineages": split["dose"]["train_lineages"],
                    "strange_fours": split["dose"]["train_strange_fours"],
                    "holdout": split["test_pictures"],
                }
            )
        out["points"].append(
            {
                "point": point,
                **{k: v for k, v in POINTS[point].items() if k != "what"},
                "what": POINTS[point]["what"],
                "per_fold": cells,
                "mean_train": sum(c["train"] for c in cells) / len(cells),
                "mean_strange_fours": sum(c["strange_fours"] for c in cells) / len(cells),
                "holdout_rows": sum(c["holdout"] for c in cells),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Fitting and reading.
# --------------------------------------------------------------------------- #
def fit(point: str, fold: int, device: str = "auto", epochs: int | None = None, log=None) -> dict:
    """Fit the incumbent recipe on one dose point and one fold."""
    if point not in POINTS:
        raise DoseError(f"{point!r} is not a dose point here; they are {sorted(POINTS)}")
    document = render_folds.read_assignment()
    directory = run_dir(point, fold)
    directory.mkdir(parents=True, exist_ok=True)

    def split():
        _rows, pictures, record = sides_for(point, fold, document)
        return pictures, record

    return render_train.run(
        device=device,
        epochs=EPOCHS if epochs is None else int(epochs),
        seed=SEED,
        run_name=f"dose_{point}_fold{fold}",
        backbone=render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        target_dims=None,
        split=split,
        directory=directory,
        patience=PATIENCE,
        log=log or train.say,
    )


def read_out_of_fold(point: str, fold: int, device: str = "auto", log=train.say) -> dict:
    """Read this fold's held-out rows through this dose point's checkpoint.

    The holdout is the fold's own lineages and does not depend on the dose, so
    every point writes the same rows here and a later read can align them without
    intersecting anything quietly.
    """
    directory = run_dir(point, fold)
    checkpoint = directory / render_grade.CHECKPOINTS[RULE]
    if not checkpoint.is_file():
        raise DoseError(f"{checkpoint} does not exist — fit the run before reading it")
    document = render_folds.read_assignment()
    rows, pictures, _split = sides_for(point, fold, document)
    lineage = [int(group) for group in document["group_of_row"]]
    held = [
        (row, picture, group)
        for row, picture, group in zip(rows, pictures, lineage, strict=True)
        if picture.side == "eval"
    ]
    if not held:
        raise DoseError(f"fold {fold} holds nothing out, so there is nothing to read")

    model, config, where = render_train.load_checkpoint(checkpoint, device)
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    classes = int(config["classes"])
    log(f"{point} fold {fold}: reading {len(held)} held-out pictures")
    probabilities = train.score(
        model, [picture.path for _row, picture, _group in held], transform, where, classes, config
    )

    path = directory / f"out_of_fold_{RULE}.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (row, picture, group), probability in zip(held, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "point": point,
                "fold": fold,
                "seed": SEED,
                "rule": RULE,
                "epoch": config.get("best_epoch"),
                "lineage": int(group),
                "kind": picture.kind,
                "name": picture.name,
                "batch": row["batch"],
                "score": int(row["score"]),
                "partition": row.get("partition"),
                "mode": row["mode"],
                "curve": row["curve"],
                "colormap": row["colormap"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "point": point,
        "fold": fold,
        "epoch": config.get("best_epoch"),
        "rows": len(held),
        "wrote": str(path),
    }


def read_rows(point: str, fold: int) -> list[dict]:
    path = run_dir(point, fold) / f"out_of_fold_{RULE}.jsonl"
    if not path.is_file():
        raise DoseError(f"{path} does not exist — read the run's held-out rows first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def folds_read(point: str) -> list[int]:
    return sorted(
        int(path.parent.name.removeprefix("fold"))
        for path in (root() / point).glob(f"fold*/out_of_fold_{RULE}.jsonl")
    )


def pooled(point: str, folds=None) -> list[dict]:
    """One dose point's held-out reading over every fold it covers."""
    out: list[dict] = []
    for fold in folds if folds is not None else folds_read(point):
        out += read_rows(point, fold)
    return out


# --------------------------------------------------------------------------- #
# The readouts. Declared in `ABLATE_label_dose.md` before any number here existed.
# --------------------------------------------------------------------------- #
#: **Every number on this curve is a difference on identical rows.** The stores
#: are overwhelmingly train-side and the holdout is not a population anything
#: samples, so an AUC here says which dose orders these rows better and nothing
#: about how good any dose is. The absolute column is printed as context and no
#: bar is set on it.
READOUTS: dict = {
    "primary": {
        "name": "rank_key_auc_ge4_three_against_four",
        "population": (
            "every holdout row a human scored 3 or 4, BOTH KINDS POOLED, that the rank key's "
            "other three columns can be read for"
        ),
        "statistic": (
            "AUC at the >=4 boundary of the rank key REFIT on this point's own out-of-fold "
            "predictions, leave-one-fold-out, exactly as the grading band refit it per arm"
        ),
    },
    "secondary": [
        {"name": "strange_auc_ge4", "kind": "strange_render", "cutpoint": 4},
        {"name": "strange_auc_ge3", "kind": "strange_render", "cutpoint": 3},
    ],
    "guards": [
        {"name": "smooth_auc_ge4", "kind": "smooth_render", "cutpoint": 4},
        {"name": "smooth_auc_ge3", "kind": "smooth_render", "cutpoint": 3},
    ],
    "sparse_modes": (
        "PRE-DECLARED AND GATING NOTHING: the strange modes the two under-served-mode "
        "batches were drawn to fill. Counts there are single and double digits and a bar "
        "fitted on them would fit noise"
    ),
    "significance": (
        "95% paired bootstrap resampling whole LINEAGE GROUPS on pooled out-of-fold "
        "predictions, 5,000 draws"
    ),
    "no_level_claim": (
        "every number is a difference or a slope on identical rows; no absolute here is "
        "quotable as a level"
    ),
}

#: The batches that were drawn to fill under-served strange modes. The sparse-mode
#: readout is cut on the modes these served, and they are named rather than
#: derived so that a later reader knows which question the cut was about.
SPARSE_MODE_BATCHES = ("under_seen_modes", "sparse_mode_head_top")


def sparse_modes(rows: list[dict]) -> list[str]:
    """The strange modes the under-served-mode batches served, off the reading itself."""
    return sorted(
        {
            row["mode"]
            for row in rows
            if row["kind"] == "strange_render" and row["batch"] in SPARSE_MODE_BATCHES
        }
    )


def _paired(candidate: list[dict], reference: list[dict], cutpoint: int, kind: str | None) -> dict:
    """The paired AUC difference between two dose points at one cutpoint."""
    import numpy

    mine = {(row["kind"], row["name"]): row for row in candidate}
    theirs = {(row["kind"], row["name"]): row for row in reference}
    if set(mine) != set(theirs):
        raise DoseError(
            f"two dose points do not cover the same holdout — {len(set(mine) - set(theirs))} "
            f"only in the candidate and {len(set(theirs) - set(mine))} only in the reference. "
            f"The holdout is the thing that is not allowed to move."
        )
    pairs = [
        (mine[key], theirs[key])
        for key in sorted(mine)
        if kind is None or theirs[key]["kind"] == kind
    ]
    if not pairs:
        return {"n": 0, "positives": 0, "delta": None, "lo": None, "hi": None}
    labels = numpy.array([int(row["score"]) >= cutpoint for _m, row in pairs], dtype=float)
    ours = numpy.array([float(row[f"p_ge{cutpoint}"]) for row, _t in pairs])
    others = numpy.array([float(row[f"p_ge{cutpoint}"]) for _m, row in pairs])
    lineages = numpy.array([row["lineage"] for _m, row in pairs])
    out = metrics.paired_delta(labels, ours, others, lineages, draws=DRAWS, seed=BOOTSTRAP_SEED)
    out["n"] = len(pairs)
    out["positives"] = int(labels.sum())
    out["negatives"] = len(pairs) - int(labels.sum())
    out["lineages"] = int(len(set(lineages.tolist())))
    out["candidate"] = metrics.auc(labels, ours)
    out["reference"] = metrics.auc(labels, others)
    return out


def curve(points=None, folds=None, reference: str = PRE_GROWTH) -> dict:
    """The whole curve: every declared readout at every point, against one anchor.

    The anchor is the pre-growth point, because the question is what the era's
    new labels bought and the era began there. Every interval is a paired
    difference against it on identical rows.
    """
    points = list(points or [name for name in POINTS if folds_read(name)])
    if reference not in points:
        raise DoseError(
            f"the anchor {reference!r} has no reading, so nothing can be read against it"
        )
    readings = {point: pooled(point, folds) for point in points}
    carried = render_grade.rank_key_columns()
    keyed = {point: render_grade.key_readings(rows, carried) for point, rows in readings.items()}

    modes = sparse_modes(readings[reference])
    out: dict = {
        "schema": SCHEMA,
        "readouts": READOUTS,
        "reference": reference,
        "folds": folds if folds is not None else "every fold read",
        "sparse_modes": modes,
        "points": [],
    }
    for point in points:
        rows = readings[point]
        cell: dict = {
            "point": point,
            "leg": POINTS[point]["leg"],
            "what": POINTS[point]["what"],
            "holdout_rows": len(rows),
            "epochs": {
                str(fold): read_rows(point, fold)[0]["epoch"]
                for fold in (folds if folds is not None else folds_read(point))
            },
        }
        cell["primary"] = render_grade.key_delta(keyed[point], keyed[reference])
        for entry in READOUTS["secondary"] + READOUTS["guards"]:
            cell[entry["name"]] = _paired(
                rows, readings[reference], int(entry["cutpoint"]), entry["kind"]
            )
        cell["sparse"] = _sparse_cell(rows, readings[reference], modes)
        out["points"].append(cell)
    return out


def _sparse_cell(candidate: list[dict], reference: list[dict], modes) -> dict:
    """The sparse-mode slice: pooled over those modes, and each of them on its own."""
    import numpy

    wanted = set(modes)
    picked = [row for row in candidate if row["kind"] == "strange_render" and row["mode"] in wanted]
    names = {(row["kind"], row["name"]) for row in picked}
    mine = [row for row in candidate if (row["kind"], row["name"]) in names]
    theirs = [row for row in reference if (row["kind"], row["name"]) in names]
    pooled_delta = _paired(mine, theirs, 4, "strange_render") if mine else {"n": 0, "delta": None}
    per_mode = []
    lookup = {(row["kind"], row["name"]): row for row in reference}
    for mode in sorted(wanted):
        members = [row for row in picked if row["mode"] == mode]
        labels = numpy.array([int(row["score"]) >= 4 for row in members])
        per_mode.append(
            {
                "mode": mode,
                "n": len(members),
                "positives": int(labels.sum()),
                "candidate": metrics.auc(labels, [float(row["p_ge4"]) for row in members]),
                "reference": metrics.auc(
                    labels,
                    [float(lookup[(row["kind"], row["name"])]["p_ge4"]) for row in members],
                ),
            }
        )
    return {"pooled": pooled_delta, "per_mode": per_mode}


def write_curve(points=None, folds=None, reference: str = PRE_GROWTH) -> tuple[Path, dict]:
    document = curve(points, folds, reference)
    path = root() / "curve.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, document


__all__ = [
    "BOOTSTRAP_SEED",
    "DRAWS",
    "EPOCHS",
    "ERA_CUTS",
    "GROWN",
    "PATIENCE",
    "POINTS",
    "PRE_GROWTH",
    "READOUTS",
    "RULE",
    "SCHEMA",
    "SEED",
    "SPARSE_MODE_BATCHES",
    "STOP_SEED",
    "STOP_SHARE",
    "DoseError",
    "curve",
    "fit",
    "folds_read",
    "plan",
    "pooled",
    "read_out_of_fold",
    "read_rows",
    "registration_dates",
    "root",
    "run_dir",
    "sides_for",
    "sparse_modes",
    "write_curve",
]
