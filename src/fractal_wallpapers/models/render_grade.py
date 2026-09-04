"""Grading the render judge on a statistic that can resolve, and fitting the bar off it.

A cross-validation screen — deleted on 2026-09-04, recoverable from git history —
read three arms over these folds and came back null. The machinery was sound; the
**declared slice** was not. It cut the motivating
population down to 43 strange rows — 25 fours against 18 non-fours — by
restricting to the band where the shipped judge's `P(>=4)` sits in [0.60, 0.95),
and a 95% interval on an AUC over 43 rows is about +/-0.19. Only an enormous
effect was visible there, every arm's interval spanned zero, and a null on 43
rows is not a measurement.

This module re-runs that comparison against **the same question, unbanded**:
`AUC(>=4)` over every strange row a person scored 3 or 4. That is 1,021 rows over
the whole store and about 200 in any one fold, four to five times the declared
slice, and it is the statistic the screen's own report named as the better
instrument. The band is where a bar would *act*; it is not where the evidence is.

## ★ The primary is the RANK KEY, and that is a later correction

Everything above is the ckpt-88 reading and its arithmetic still stands. What
moved at ckpt 91 is what the comparison turns on. `P(>=4)` is **one of five
columns** [`curation.rank_key`] reads, and the key — not the column — is what
orders seats; so a retrain that improved the column and left the key alone would
have improved nothing anybody ships. [`key_delta`] is the declared primary: the
key **refit on each arm's own out-of-fold predictions**, ordering the rows a
person scored 3 or 4, pooled over both kinds.

Refitting per arm is deliberate rather than a convenience. CORN's scale is set by
the training prior, so every retrain moves the whole probability axis; a key
whose constants were fitted against the incumbent's scale would read a
candidate's columns at the wrong offset and report that move as a quality
change. Fitting per arm makes it drop out, and it is what an adoption would do
anyway — the key is *on* the adoption checklist, not beside it.

The strange-side `AUC(>=4)` over 3-or-4 rows stays on every table under
`motivating` and now decides nothing.

## Two things are tested at once and one of them is free

**Aspect.** Every band on the record reads 384x224 — which is 12:7 — of a
1280x720 picture, through a whole-frame `image.resize` with no crop at deploy.
Every picture this project draws is 16:9: the store's renders, the 640x360
candidate a mining pass scores, the location tiles. So the head has **never once
seen this material at its own aspect ratio**, in training or at deploy, and the
3.7% horizontal stretch is not a property of one corpus but of every reading the
judge has ever taken. [`ASPECT_DIMS`] closes it at the shipped width.

⚠ The **resolution** axis was arm B until ckpt 91 and is not an arm here any
more. Its gain was measured at label geometry, where 768x448 takes 37% of a
1280x720 source; mining scores the 640x360 candidate, where 384x224 already
takes 37% and 768x448 *exceeds the source*. That is a scoring check over two
retired checkpoints rather than a training run, and it is priced in minutes.

**The stopping rule.** The shipped recipe selects the epoch on the pooled
cutpoint cross-entropy and keeps epoch 5 of 40, while `AUC(>=4)` on that very
same slice is still climbing to epoch 11-13 on every seed on the record. Both
selections are readable from one run's epoch trace, so the second one costs no
training at all — [`render_train.run`]'s `second_selection` keeps a checkpoint at
each rule's own epoch and the loop is the same loop.

## Selecting on stop-slice `AUC(>=4)` is NOT the arm that already failed

The screen's `top_cutpoint_selection` arm chose **epoch 1** and cost the smooth side
significantly. That was a *proper scoring rule* — a cross-entropy — read at one
rare cutpoint, and an under-confident head minimizes it by never committing, so
selecting on it buys early stopping rather than ordering. AUC is rank-only: it
cannot be gamed by shrinking toward the prior, because shrinking every score
toward the prior does not reorder them. The two rules read the same boundary and
are not the same statistic, and the failure of one says nothing about the other.

## The split, and what is different from the screen's

The folds are [`render_folds`]'s, re-used rather than re-dealt: the same lineage
assignment, the same written artifact, the same exclusions. What changes is the
**stop slice**. `render_train`'s own rule draws 10% of the training side's
*places*, and a place is finer than a lineage — two near-duplicate frames can sit
on either side of it. So the stop slice here is [`STOP_SHARE`] of the training
side's **lineage groups**, seeded per fold so that every arm on a fold stops
against one population and the comparison is between arms rather than between
slices. It comes out of the training side and never out of the holdout: a run
that early-stopped on the graded split would make the graded number optimistic
and it could not also be the grading statistic.

## Nothing here adopts anything, and no LEVEL is claimed

No weights ship, `curation.floors.SCORING_HEAD` does not move, `models/` is not
written and no registry is opened. Nor is any number here an absolute: the stores
are overwhelmingly train-side and the incumbent's own AUCs are inflated on that
side, so every reading says which **arm** is better on identical rows and none of
them says how good any arm is. The crossovers [`crossovers`] fits are read at
**label geometry** — the store's own 1280x720 renders — and the judge is not
regime-robust, so they are not seating floors and no bar is set on them here.
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
    render_train,
    train,
)
from fractal_wallpapers.paths import under

#: The schema every record here carries.
SCHEMA = 1

#: The stop slice: what share of the training side's LINEAGE GROUPS is held back
#: to choose an epoch on, and the seed the draw is made under. Groups rather than
#: places, because a place is finer than a lineage and the whole discipline of
#: this split is that no lineage crosses a boundary. Seeded per fold, so every
#: arm on one fold stops against one population.
STOP_SHARE = 0.20
STOP_SEED = 0

#: The epoch ceiling and the patience, on the stop-slice statistic. Twenty rather
#: than the recipe's forty because every rule on the record picks an epoch under
#: fifteen; six because the two rules here peak several epochs apart and a
#: patience that stopped on the earlier one would truncate the later one's search.
EPOCHS = 20
PATIENCE = 6

#: Draws in every interval here and its seed — [`render_folds`]'s own, so that an
#: interval from that module and one from this are the same statistic.
DRAWS, BOOTSTRAP_SEED = render_folds.DRAWS, render_folds.BOOTSTRAP_SEED

#: The two stopping rules, by the name every record and every table uses.
SHIPPED_RULE = "cutpoint_cross_entropy"
AUC_RULE = "stop_slice_auc_ge4"

#: The floor the admitted volume in [`crossovers`] is counted against:
#: `curation.mine.PRIMED_BAR`, where a candidate is called primed. Read here and
#: never restated — this module measures against it and moves nothing.
PRIMED_BAR = 0.90


class GradingError(RuntimeError):
    """A run that cannot be fitted, read or graded on what is here."""


def root() -> Path:
    """Where the graded runs live: the regenerable tree, never a run directory."""
    return under("render_grade")


def run_dir(arm: str, fold: int, seed: int) -> Path:
    return root() / arm / f"fold{fold}_seed{seed}"


# --------------------------------------------------------------------------- #
# The arms.
# --------------------------------------------------------------------------- #
#: The realized input shape of every band on the record, read off the shipped
#: artifact rather than off a declaration. Arm B doubles both axes of it, which
#: is what preserves the convention: the resize is a whole-frame anisotropic
#: stretch with no crop at deploy, so doubling both axes keeps the same picture
#: at four times the pixels and changes nothing else about what arrives.
SHIPPED_DIMS = (head.TARGET_WIDTH, head.TARGET_HEIGHT)
DOUBLED_DIMS = (SHIPPED_DIMS[0] * 2, SHIPPED_DIMS[1] * 2)

#: **The aspect every picture this judge has ever read.** The stores' renders are
#: 1280x720, the candidate a mining pass scores is 640x360 and a location tile is
#: 640x360: 16:9 is not one corpus's convention here, it is the only shape this
#: project draws. The shipped input is 384x224, which is 12:7, and `head.resize`
#: is a bare whole-frame `image.resize` — so every picture the head has ever seen
#: arrived stretched 3.7% horizontally, in training and at deploy alike.
SOURCE_ASPECT = (16, 9)

#: Arm B's input: **the shipped width at the source's own aspect**. 384x216 is
#: exactly 16:9, so the picture arrives undistorted with every pixel of it still
#: in the frame.
#:
#: The gap admits three treatments and this is the one that gives up nothing a
#: verdict was about. **Padding** spends 3.6% of the input on a constant band and
#: teaches an edge no picture has. **Cropping** to 12:7 throws 46 columns of a
#: wallpaper away, and the store's verdicts are about whole frames. An
#: aspect-preserving resize costs 3.6% of the input pixels and nothing else.
#:
#: The **width is held at the shipped 384 on purpose**: this arm has to move
#: aspect alone. Resolution is what the `input_detail` check asks about, and an
#: arm that moved both could not answer either question.
ASPECT_DIMS = (SHIPPED_DIMS[0], SHIPPED_DIMS[0] * SOURCE_ASPECT[1] // SOURCE_ASPECT[0])

ARMS: dict[str, dict] = {
    "A": {
        "target_dims": None,
        "what": (
            "the shipped recipe, refit on these folds at this stop slice. Small backbone, "
            "four-class CORN, batch 32, sqrt class balance, geometric augmentation, the "
            "picture arriving at 384x224 by whole-frame stretch"
        ),
    },
    "B": {
        "target_dims": list(ASPECT_DIMS),
        "what": (
            "arm A with the aspect gap closed — 384x216, exactly the source's own 16:9, by "
            "the same whole-frame resize. Every pixel still arrives and none is padded or "
            "cropped away; the width is the shipped one, so resolution does not move"
        ),
    },
}


def negative_top_auc(labels, probabilities, classes: int) -> float:
    """`-AUC(>=4)` over the stop slice, as an epoch-selection objective to MINIMIZE.

    Negated so that it takes exactly [`render_train.run`]'s selection contract —
    one convention for both rules, rather than a maximizer and a minimizer that a
    reader has to keep apart.

    **Rank-only, and that is the whole reason it is not the arm that failed.**
    `render_folds.top_cutpoint_loss` was a cross-entropy at this same boundary and
    an under-confident head minimizes it by stopping at epoch 1. An AUC cannot be
    moved that way: shrinking every score toward the prior leaves the order
    alone.
    """
    import numpy

    labels = numpy.asarray(labels)
    scores = numpy.asarray(probabilities)[:, classes - 2]
    value = metrics.auc((labels >= classes).astype(int), scores)
    # An undefined AUC — one class absent from the slice — is not a good epoch
    # and is not a bad one. Returning `inf` keeps it from ever being selected
    # without pretending it scored zero.
    return float("inf") if value is None else -float(value)


AUC_SAYS = (
    "max AUC(>=4) over the stop slice, through the deploy transform. Rank-only, so an "
    "under-confident head cannot minimize it by refusing to commit — which is what the "
    "cross-entropy at this same boundary rewards"
)


# --------------------------------------------------------------------------- #
# The split: the screen's folds, this module's stop slice.
# --------------------------------------------------------------------------- #
def sides_for(fold: int, document: dict | None = None, population: tuple | None = None):
    """The population with every picture on the side this fold and rule put it.

    [`render_folds.sides_for`] with one thing moved: the stop slice is drawn over
    **lineage groups** at [`STOP_SHARE`] rather than over places at the trainer's
    own share. Holdout, exclusion and training sides are the screen's, unchanged,
    so the two modules grade the same partition of the same corpus.
    """
    document = document or render_folds.read_assignment()
    rows, pictures, record = population or render_folds.pool()
    fold_of_row = document["fold_of_row"]
    group_of_row = document["group_of_row"]
    if len(fold_of_row) != len(pictures):
        raise GradingError(
            f"the written assignment covers {len(fold_of_row)} rows and the corpus now holds "
            f"{len(pictures)}. The store grew under the folds: re-derive them and re-fit "
            f"every arm, or the arms are not comparable."
        )
    pinned = {repr(place) for place in render_train.pinned_everywhere()}

    for picture, where in zip(pictures, fold_of_row, strict=True):
        if where == fold:
            picture.side = "eval"
        elif picture.place in pinned:
            picture.side = render_train.EXCLUDED
        else:
            picture.side = "train"

    trainable = [
        (picture, group)
        for picture, group in zip(pictures, group_of_row, strict=True)
        if picture.side == "train"
    ]
    lineages = sorted({int(group) for _picture, group in trainable})
    # Seeded per fold rather than once: one seed over five folds would draw five
    # different slices anyway, and a seed that says which fold it is makes the
    # draw re-derivable from the fold alone.
    draw = random.Random(STOP_SEED * 1000 + fold)
    order = list(lineages)
    draw.shuffle(order)
    chosen = set(order[: max(1, round(len(order) * STOP_SHARE))])
    for picture, group in trainable:
        if int(group) in chosen:
            picture.side = render_train.SELECTION

    split = {
        "fold": fold,
        "of_folds": document["folds"],
        "seed": document["seed"],
        "rule": (
            "the fold's own lineages are the graded holdout and are never touched in "
            "training; a location pinned to either blind sheet never trains and is excluded "
            "outside its own fold; everything else trains"
        ),
        "unit": document["unit"],
        "population": record,
        "pinned_locations_union": len(pinned),
        "excluded_pictures": sum(1 for p in pictures if p.side == render_train.EXCLUDED),
        "test_pictures": sum(1 for p in pictures if p.side == "eval"),
        "stop_slice": {
            "share": STOP_SHARE,
            "seed": STOP_SEED * 1000 + fold,
            "drawn_over": (
                "LINEAGE GROUPS on this fold's training side, so no lineage crosses the "
                "boundary. The trainer's own rule draws places, which are finer"
            ),
            "lineages": len(chosen),
            "of_lineages": len(lineages),
            "pictures": sum(1 for p in pictures if p.side == render_train.SELECTION),
            "tiers": finished_train.histogram(
                [p for p in pictures if p.side == render_train.SELECTION]
            ),
            "comes_out_of": "the training side, never the holdout",
        },
    }
    return rows, pictures, split


# --------------------------------------------------------------------------- #
# Fitting and reading.
# --------------------------------------------------------------------------- #
def fit(arm: str, fold: int, seed: int, device: str = "auto", epochs: int | None = None, log=None):
    """Fit one arm on one fold at one seed, through the trainer every band used."""
    if arm not in ARMS:
        raise GradingError(f"{arm!r} is not an arm here; the arms are {sorted(ARMS)}")
    document = render_folds.read_assignment()
    directory = run_dir(arm, fold, seed)
    directory.mkdir(parents=True, exist_ok=True)

    def split():
        _rows, pictures, record = sides_for(fold, document)
        return pictures, record

    return render_train.run(
        device=device,
        epochs=EPOCHS if epochs is None else int(epochs),
        seed=seed,
        run_name=f"grade_{arm}_fold{fold}_seed{seed}",
        backbone=render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        target_dims=ARMS[arm]["target_dims"],
        split=split,
        directory=directory,
        second_selection=negative_top_auc,
        second_selection_says=AUC_SAYS,
        patience=PATIENCE,
        log=log or train.say,
    )


#: Which checkpoint each stopping rule keeps, and what a record calls it.
CHECKPOINTS = {SHIPPED_RULE: "best.pt", AUC_RULE: "best_second.pt"}


def read_out_of_fold(
    arm: str, fold: int, seed: int, rule: str = SHIPPED_RULE, device: str = "auto", log=train.say
) -> dict:
    """Read this fold's held-out rows through one rule's checkpoint, and write them.

    One row a picture, carrying its whole join and the rule that chose the epoch,
    so a later read can cut the population any way it needs without going back to
    the stores or guessing which selection produced a file.
    """
    if rule not in CHECKPOINTS:
        raise GradingError(f"{rule!r} is not a stopping rule here; they are {sorted(CHECKPOINTS)}")
    directory = run_dir(arm, fold, seed)
    checkpoint = directory / CHECKPOINTS[rule]
    if not checkpoint.is_file():
        raise GradingError(f"{checkpoint} does not exist — fit the run before reading it")
    document = render_folds.read_assignment()
    rows, pictures, _split = sides_for(fold, document)
    lineage = document["group_of_row"]
    held = [
        (row, picture, group)
        for row, picture, group in zip(rows, pictures, lineage, strict=True)
        if picture.side == "eval"
    ]
    if not held:
        raise GradingError(f"fold {fold} holds nothing out, so there is nothing to read")

    model, config, where = render_train.load_checkpoint(checkpoint, device)
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    classes = int(config["classes"])
    log(f"{arm} fold {fold} seed {seed} [{rule}]: reading {len(held)} held-out pictures")
    probabilities = train.score(
        model, [picture.path for _row, picture, _group in held], transform, where, classes, config
    )

    path = directory / f"out_of_fold_{rule}.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (row, picture, group), probability in zip(held, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "arm": arm,
                "fold": fold,
                "seed": seed,
                "rule": rule,
                "epoch": config.get("best_epoch"),
                "lineage": int(group),
                "kind": picture.kind,
                "name": picture.name,
                "batch": row["batch"],
                "score": int(row["score"]),
                "partition": row.get("partition"),
                "family": row["family"],
                "viewport": row["viewport"],
                "mode": row["mode"],
                "curve": row["curve"],
                "colormap": row["colormap"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "arm": arm,
        "fold": fold,
        "seed": seed,
        "rule": rule,
        "epoch": config.get("best_epoch"),
        "rows": len(held),
        "wrote": str(path),
    }


def read_rows(arm: str, fold: int, seed: int, rule: str) -> list[dict]:
    path = run_dir(arm, fold, seed) / f"out_of_fold_{rule}.jsonl"
    if not path.is_file():
        raise GradingError(f"{path} does not exist — read the run's held-out rows first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def pooled(arm: str, rule: str, seed: int, folds=None) -> list[dict]:
    """One arm-and-rule's held-out rows over every fold it has been read on."""
    if folds is None:
        folds = sorted(
            int(path.parent.name.split("_")[0].removeprefix("fold"))
            for path in (root() / arm).glob(f"fold*_seed{seed}/out_of_fold_{rule}.jsonl")
        )
    out: list[dict] = []
    for fold in folds:
        out += read_rows(arm, fold, seed, rule)
    return out


# --------------------------------------------------------------------------- #
# The primary: the shipped rank key, refit on each arm's own predictions.
# --------------------------------------------------------------------------- #
#: The members of [`curation.rank_key.COLUMNS`] a retrain does NOT move. The
#: place's own reading, the calibration stratum and the dead-space fraction are
#: facts about the picture rather than about the judge, so they are joined once
#: and every arm is handed the same ones; the two the judge owns are exactly what
#: an arm substitutes.
CARRIED_COLUMNS = ("loc_p_ge4", "stratum_score", "flat16_1.0")

#: The judge's own two columns in the key, in the order the key reads them.
JUDGE_COLUMNS = ("p_ge3", "p_ge4")


def columns_path() -> Path:
    """Where the arm-independent half of the key's rows is cached. Regenerable."""
    return root() / "rank_key_columns.json"


def rank_key_columns(rebuild: bool = False, log=train.say) -> dict:
    """The arm-independent half of the rank key's row, for every label row it has one.

    [`curation.rank_key.fit`]'s join, re-derived against the stores as they stand
    and **written nowhere tracked** — this grades, it does not ship a key. The
    shipped artifact's own `population.jsonl` is deliberately not reused: it was
    joined on a file and a line, the stores have been appended to and superseded
    since it was written, and a tenth of its rows no longer address what they
    addressed.

    Keyed by the **render job name**, which is what an out-of-fold reading
    already carries, so the two join without going back to either store.
    """
    cache = columns_path()
    if cache.is_file() and not rebuild:
        return json.loads(cache.read_text(encoding="utf-8"))

    from fractal_wallpapers.curation import candidate_ledger, flatness, intake, rank_key
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.models import renders

    labels = []
    for kind in rank_key.KINDS:
        for row in finished.resolved(kind).scored():
            identity = finished.render_key(row)
            if identity is not None:
                labels.append((kind, row, identity))
    log(f"[key] {len(labels):,} resolved scored label rows")

    wanted = {identity for _kind, _row, identity in labels}
    ledger: dict = {}
    with candidate_ledger.rows_path().open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            identity = rank_key.ledger_identity(row)
            if identity is not None and identity in wanted and identity not in ledger:
                ledger[identity] = row
    log(f"[key] {len(ledger):,} ledger rows join a label")

    location_scores = intake.read_scores()
    flat = flatness.by_recipe()
    lean = rank_key.thin_cells()
    scores = candidate_ledger.scores_by_recipe()
    kinds: dict = {}
    out: dict = {}
    dropped = {"no_ledger_row": 0, "no_score": 0, "no_flatness": 0, "no_location_reading": 0}
    for kind, row, identity in labels:
        entry = ledger.get(identity)
        if entry is None:
            dropped["no_ledger_row"] += 1
            continue
        key = str(entry["key"])
        reading = scores.get(key) or {}
        if reading.get("p_ge3") is None or reading.get("p_ge4") is None:
            dropped["no_score"] += 1
            continue
        value = flat.get(key)
        if value is None:
            dropped["no_flatness"] += 1
            continue
        place = location_scores.get(str((entry.get("location") or {}).get("key"))) or {}
        reading_of_place = place.get("p_ge4")
        if reading_of_place is None:
            dropped["no_location_reading"] += 1
        mode = str((entry.get("recipe") or {}).get("mode"))
        stripped = {name: member for name, member in row.items() if not name.startswith("_")}
        name = renders.job_name({**stripped, "_head": kind})
        cells = (entry.get("colour") or {}).get("cells") or ()
        out[f"{kind}:{name}"] = {
            "kind": kind,
            "name": name,
            "tier": int(row["score"]),
            "mode": mode,
            "loc_p_ge4": (
                rank_key.NO_LOCATION_READING
                if reading_of_place is None
                else float(reading_of_place)
            ),
            "stratum_score": rank_key.STRATUM_ORDER[rank_key.stratum_of(mode, cells, lean, kinds)],
            "flat16_1.0": float(value),
            "incumbent_p_ge3": float(reading["p_ge3"]),
            "incumbent_p_ge4": float(reading["p_ge4"]),
        }
    log(f"[key] {len(out):,} label rows carry every column; dropped {dropped}")
    document = {"schema": SCHEMA, "dropped": dropped, "rows": out}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    return document


def key_readings(rows: list[dict], carried: dict | None = None) -> list[dict]:
    """One arm's reading, put through a rank key **refit on that arm's own scores**.

    The shipped key standardizes and weights five columns, two of which are this
    judge's. A retrain moves the CORN scale by construction, so a key whose
    constants were fitted against the incumbent's scale would read a candidate's
    columns at the wrong offset and report the scale move as a quality change.
    Refitting per arm is what makes that drop out: each arm is ranked by the best
    key its own numbers support, which is also what an adoption would do — the
    key is on the adoption checklist rather than beside it.

    The fold is the **judge's own**, carried on the reading. So a row's key value
    comes from weights fitted without its fold and from a judge that never saw
    its lineage, and the two levels share one partition instead of drawing two.
    """
    import numpy

    from fractal_wallpapers.curation import rank_key

    held = (carried or rank_key_columns())["rows"]
    joined = [
        (row, held[f"{row['kind']}:{row['name']}"])
        for row in rows
        if f"{row['kind']}:{row['name']}" in held
    ]
    if not joined:
        raise GradingError(
            "no out-of-fold row joins the rank key's columns, so the key cannot be refit. "
            "Has `curate flatness sweep` run over the labeled rows?"
        )
    matrix = numpy.array(
        [
            [
                carried_row["loc_p_ge4"],
                float(row["p_ge3"]),
                float(row["p_ge4"]),
                carried_row["stratum_score"],
                carried_row["flat16_1.0"],
            ]
            for row, carried_row in joined
        ],
        dtype=float,
    )
    target = numpy.array([1.0 if int(row["score"]) >= 4 else 0.0 for row, _carried in joined])
    folds = numpy.array([int(row["fold"]) for row, _carried in joined])
    predicted = numpy.full(len(joined), numpy.nan)
    for fold in sorted(set(folds.tolist())):
        inside = folds == fold
        if inside.sum() == 0 or (~inside).sum() == 0 or len(numpy.unique(target[~inside])) < 2:
            continue
        mean, deviation = rank_key.standardize(matrix[~inside])
        beta = rank_key.logistic((matrix[~inside] - mean) / deviation, target[~inside])
        predicted[inside] = rank_key.predict(beta, (matrix[inside] - mean) / deviation)
    return [
        {**row, "key_value": float(value)}
        for (row, _carried), value in zip(joined, predicted, strict=True)
        if not numpy.isnan(value)
    ]


def key_delta(candidate: list[dict], reference: list[dict]) -> dict:
    """The primary: two refit keys ordering the same human 3-against-4 rows.

    **Pooled over both kinds**, because the key's weights are shared over both
    and its ordering is what seats a wallpaper of either kind. Restricted to the
    rows a person scored 3 or 4, because that is the judgement a seating turns on
    and the one the shipped judge is measured not to make.
    """
    import numpy

    mine = {(row["kind"], row["name"]): row for row in candidate}
    theirs = {(row["kind"], row["name"]): row for row in reference}
    shared = sorted(set(mine) & set(theirs))
    pairs = [(mine[key], theirs[key]) for key in shared if int(theirs[key]["score"]) in {3, 4}]
    if not pairs:
        return {"n": 0, "positives": 0, "delta": None, "lo": None, "hi": None}
    labels = numpy.array([int(row["score"]) >= 4 for _mine, row in pairs], dtype=float)
    ours = numpy.array([float(row["key_value"]) for row, _theirs in pairs])
    others = numpy.array([float(row["key_value"]) for _mine, row in pairs])
    lineages = numpy.array([row["lineage"] for _mine, row in pairs])
    out = metrics.paired_delta(labels, ours, others, lineages, draws=DRAWS, seed=BOOTSTRAP_SEED)
    out["n"] = len(pairs)
    out["positives"] = int(labels.sum())
    out["negatives"] = len(pairs) - int(labels.sum())
    out["lineages"] = int(len(set(lineages.tolist())))
    out["candidate"] = metrics.auc(labels, ours)
    out["reference"] = metrics.auc(labels, others)
    out["joined"] = len(shared)
    out["per_kind"] = {}
    for kind in render_train.KINDS:
        members = [(mine_row, row) for mine_row, row in pairs if row["kind"] == kind]
        if not members:
            continue
        truth = [int(row["score"]) >= 4 for _mine_row, row in members]
        out["per_kind"][kind] = {
            "n": len(members),
            "positives": int(sum(truth)),
            "candidate": metrics.auc(truth, [float(m["key_value"]) for m, _r in members]),
            "reference": metrics.auc(truth, [float(r["key_value"]) for _m, r in members]),
        }
    return out


# --------------------------------------------------------------------------- #
# The bar. Declared in `render_judge_grade.md` before any number here existed.
# --------------------------------------------------------------------------- #
#: **The primary is the RANK KEY, not the judge's own AUC.** `P(>=4)` is one of
#: five columns [`curation.rank_key`] reads, and the key is what orders seats —
#: so what a retrain has to move is the key's ordering, not a column's. The key
#: is refit per arm on that arm's own out-of-fold predictions, which is what
#: makes the CORN scale shift drop out: an arm is ranked by the best key its own
#: numbers support, and no comparison here carries a calibration sensitivity.
#:
#: Pooled over both kinds, because the key's weights are shared over both. The
#: strange-only `AUC(>=4)` over 3-or-4 rows that was the ckpt-88 primary stays on
#: every table under `motivating` and now decides nothing.
BAR: dict = {
    "primary": {
        "name": "rank_key_auc_ge4_three_against_four",
        "population": (
            "every holdout row a human scored 3 or 4, BOTH KINDS POOLED, that the rank "
            "key's other three columns can be read for"
        ),
        "statistic": (
            "AUC at the >=4 boundary of the rank key REFIT on this arm's own out-of-fold "
            "predictions, read out of fold on the judge's own partition"
        ),
        "requires": "significantly better — the paired interval's lower bound above zero",
    },
    "motivating": {
        "name": "strange_auc_ge4_three_against_four",
        "population": "strange holdout rows a human scored 3 or 4, UNBANDED",
        "statistic": "AUC at the >=4 boundary of the judge's own P(>=4) column",
        "requires": "DESCRIPTIVE — the ckpt-88 primary, reported and deciding nothing",
    },
    "primary_comparison": (
        "arm B under the AUC stopping rule against arm A under the SHIPPED stopping rule — "
        "the true incumbent. The stopping-rule effect and the aspect effect are separated "
        "afterwards, descriptively, by arm A under the AUC rule"
    ),
    "guards": [
        {"name": "strange_auc_ge3", "kind": "strange_render", "cutpoint": 3},
        {"name": "strange_auc_ge4", "kind": "strange_render", "cutpoint": 4},
        {"name": "smooth_auc_ge3", "kind": "smooth_render", "cutpoint": 3},
        {"name": "smooth_auc_ge4", "kind": "smooth_render", "cutpoint": 4},
    ],
    "guards_require": (
        "not significantly worse — the paired interval's upper bound at or above zero. "
        "Nothing is asked to improve. One judge scores both kinds, so a strange-side gain "
        "bought off the smooth side is not a winner"
    ),
    "significance": (
        "95% paired bootstrap resampling whole LINEAGE GROUPS on pooled out-of-fold predictions"
    ),
    "seeds": (
        "the seed BAND, never the better seed: arms are compared on the seed-AVERAGED "
        "statistic and both seeds are reported. No per-seed conjunction anywhere"
    ),
    "descriptive_only": (
        "per-mode, per-kind and per-seed numbers, reported with n and deciding nothing. "
        "Per-mode is PRE-DECLARED and gates nothing on purpose: a few hundred strange fours "
        "over eighteen modes puts single digits in most cells, and a per-mode bar would fit "
        "noise. It is reported because the sparse-mode agreement gap is what a retrain is "
        "trying to move and a pooled number hides it entirely"
    ),
    "no_level_claim": (
        "the stores are overwhelmingly train-side and the incumbent's own AUCs are inflated "
        "on that side, so every number here says which ARM is better on identical rows and "
        "none of them says how good any arm is. No absolute is quotable from this table"
    ),
}


def averaged(runs: list[list[dict]]) -> list[dict]:
    """Several seeds of one arm-and-rule as one reading: the mean of the probabilities.

    **The seed band, not the better seed.** Two seeds of one design are two draws
    from it, and picking whichever came out ahead reports the maximum of two
    draws as if it were the design. Averaging the per-picture probabilities and
    reading one statistic off the average is the seed-averaged statistic the bar
    asks for; both seeds' own numbers are reported beside it and decide nothing.
    """
    if not runs:
        raise GradingError("no runs to average")
    keyed = [{(row["kind"], row["name"]): row for row in run} for run in runs]
    common = set(keyed[0])
    for other in keyed[1:]:
        if set(other) != common:
            raise GradingError(
                f"two seeds of one arm do not cover the same pictures — {len(common ^ set(other))} "
                f"differ. Both seeds have to be read on the same folds."
            )
    out = []
    for key in sorted(common):
        first = keyed[0][key]
        merged = {**first, "seed": [run[key]["seed"] for run in keyed]}
        for cutpoint in (2, 3, 4):
            column = f"p_ge{cutpoint}"
            if column in first:
                merged[column] = sum(run[key][column] for run in keyed) / len(keyed)
        out.append(merged)
    return out


def _delta(pairs: list[tuple[dict, dict]], cutpoint: int) -> dict:
    """The paired AUC difference at one cutpoint, with its lineage interval."""
    import numpy

    if not pairs:
        return {"n": 0, "positives": 0, "lineages": 0, "delta": None, "lo": None, "hi": None}
    labels = numpy.array([int(row["score"]) >= cutpoint for _mine, row in pairs], dtype=float)
    ours = numpy.array([float(mine[f"p_ge{cutpoint}"]) for mine, _theirs in pairs])
    theirs = numpy.array([float(row[f"p_ge{cutpoint}"]) for _mine, row in pairs])
    lineages = numpy.array([row["lineage"] for _mine, row in pairs])
    out = metrics.paired_delta(labels, ours, theirs, lineages, draws=DRAWS, seed=BOOTSTRAP_SEED)
    out["n"] = len(pairs)
    out["positives"] = int(labels.sum())
    out["negatives"] = len(pairs) - int(labels.sum())
    out["lineages"] = int(len(set(lineages.tolist())))
    out["candidate"] = metrics.auc(labels, ours)
    out["reference"] = metrics.auc(labels, theirs)
    return out


def _verdict(interval: dict, better: bool) -> str:
    lo, hi = interval.get("lo"), interval.get("hi")
    if lo is None or hi is None:
        return "undefined"
    if better:
        return "better" if lo > 0 else "not better"
    return "worse" if hi < 0 else "not worse"


def compare(
    candidate: list[dict],
    reference: list[dict],
    labels: tuple[str, str],
    carried: dict | None = None,
) -> dict:
    """One reading against another, on every arm of the declared bar.

    Refuses to intersect quietly: two readings taken on one written assignment
    cover the same pictures, so a difference in what they cover is a difference
    in what was fitted rather than something to work around.

    `carried` is [`rank_key_columns`], passed in when a caller is about to make
    several comparisons off one join. It is a parameter rather than a global
    cache because the join is a fact about the stores at one moment, and a table
    whose comparisons were drawn against two different joins would be a table
    nobody could account for.
    """
    mine = {(row["kind"], row["name"]): row for row in candidate}
    theirs = {(row["kind"], row["name"]): row for row in reference}
    if set(mine) != set(theirs):
        raise GradingError(
            f"the two readings do not cover the same pictures — {len(set(mine) - set(theirs))} "
            f"only in the candidate and {len(set(theirs) - set(mine))} only in the reference."
        )
    pairs = [(mine[key], theirs[key]) for key in sorted(mine)]

    strange = [pair for pair in pairs if pair[1]["kind"] == "strange_render"]
    band = [pair for pair in strange if int(pair[1]["score"]) in {3, 4}]
    motivating = _delta(band, 4)
    motivating["verdict"] = _verdict(motivating, better=False)
    motivating["what"] = BAR["motivating"]["population"]

    carried = carried or rank_key_columns()
    primary = key_delta(key_readings(candidate, carried), key_readings(reference, carried))
    primary["verdict"] = _verdict(primary, better=True)
    primary["what"] = BAR["primary"]["population"]

    guards = []
    for entry in BAR["guards"]:
        members = [pair for pair in pairs if pair[1]["kind"] == entry["kind"]]
        interval = _delta(members, int(entry["cutpoint"]))
        interval["verdict"] = _verdict(interval, better=False)
        guards.append({**entry, **interval})

    return {
        "schema": SCHEMA,
        "candidate": labels[0],
        "reference": labels[1],
        "bar": BAR,
        "draws": DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "rows": len(pairs),
        "lineages": len({row["lineage"] for _mine, row in pairs}),
        "primary": primary,
        "motivating": motivating,
        "guards": guards,
        "clears_the_bar": (
            primary["verdict"] == "better"
            and all(guard["verdict"] == "not worse" for guard in guards)
        ),
        "per_mode_ge4": per_mode(strange, 4),
        "per_mode_ge4_smooth": per_mode(
            [pair for pair in pairs if pair[1]["kind"] == "smooth_render"], 4
        ),
    }


def per_mode(pairs: list[tuple[dict, dict]], cutpoint: int) -> list[dict]:
    """Every mode's own AUC on both readings. **Descriptive, and gates nothing.**"""
    import numpy

    modes: dict[str, list] = {}
    for mine, theirs in pairs:
        modes.setdefault(theirs["mode"], []).append((mine, theirs))
    out = []
    for mode in sorted(modes):
        members = modes[mode]
        labels = numpy.array([int(row["score"]) >= cutpoint for _mine, row in members])
        out.append(
            {
                "mode": mode,
                "n": len(members),
                "positives": int(labels.sum()),
                "candidate": metrics.auc(
                    labels, [float(mine[f"p_ge{cutpoint}"]) for mine, _theirs in members]
                ),
                "reference": metrics.auc(
                    labels, [float(row[f"p_ge{cutpoint}"]) for _mine, row in members]
                ),
            }
        )
    return out


def standing(rows: list[dict]) -> dict:
    """One reading's own out-of-fold numbers, with a lineage interval on each."""
    import numpy

    out: dict = {"rows": len(rows), "per_kind": {}}
    for kind in render_train.KINDS:
        members = [row for row in rows if row["kind"] == kind]
        if not members:
            continue
        lineages = numpy.array([row["lineage"] for row in members])
        cell: dict = {"n": len(members)}
        for cutpoint in (2, 3, 4):
            labels = numpy.array([int(row["score"]) >= cutpoint for row in members], dtype=float)
            scores = numpy.array([float(row[f"p_ge{cutpoint}"]) for row in members])
            interval = metrics.bootstrap(
                lambda picked, labels=labels, scores=scores: metrics.auc(
                    labels[picked], scores[picked]
                ),
                lineages,
                draws=DRAWS,
                seed=BOOTSTRAP_SEED,
            )
            cell[f"auc_ge{cutpoint}"] = {
                "value": metrics.auc(labels, scores),
                "positives": int(labels.sum()),
                "lo": interval["lo"],
                "hi": interval["hi"],
            }
        band = [row for row in members if int(row["score"]) in {3, 4}]
        if band:
            labels = numpy.array([int(row["score"]) >= 4 for row in band], dtype=float)
            cell["three_against_four"] = {
                "n": len(band),
                "positives": int(labels.sum()),
                "auc_ge4": metrics.auc(labels, [float(row["p_ge4"]) for row in band]),
            }
        out["per_kind"][kind] = cell
    return out


def reading(arm: str, rule: str, seeds: list[int], folds=None) -> list[dict]:
    """One arm under one stopping rule, as the seed band averaged into one reading."""
    return averaged([pooled(arm, rule, seed, folds) for seed in seeds])


def epochs_of(arm: str, fold: int, seed: int) -> dict:
    """What each rule chose, and where the run actually stopped. Off the trace."""
    path = run_dir(arm, fold, seed) / "metrics.json"
    if not path.is_file():
        raise GradingError(f"{path} does not exist — the run wrote no trace")
    record = json.loads(path.read_text(encoding="utf-8"))
    history = record.get("history") or []
    return {
        "arm": arm,
        "fold": fold,
        "seed": seed,
        "epochs_run": len(history),
        SHIPPED_RULE: record.get("best_epoch"),
        AUC_RULE: record.get("second_selection_epoch"),
        "stopped_early": record.get("stopped_early"),
        "wall_seconds": record.get("wall_seconds"),
        "trace": [
            {
                "epoch": row["epoch"],
                "selection_loss": row.get("selection_loss"),
                "stop_slice_auc_ge4": (
                    None
                    if row.get("second_selection_loss") is None
                    else -float(row["second_selection_loss"])
                ),
                "selection_auc_ge3": row.get("selection_auc_ge3"),
            }
            for row in history
        ],
    }


#: The readings the leg-1 table is built out of, and what each one is for. The
#: PRIMARY comparison is the first pair; the other two are the decomposition,
#: which is descriptive and separates the stopping-rule effect from the
#: resolution effect rather than deciding anything.
COMPARISONS = (
    ("B", AUC_RULE, "A", SHIPPED_RULE, "PRIMARY — the candidate against the true incumbent"),
    ("A", AUC_RULE, "A", SHIPPED_RULE, "descriptive — the stopping rule alone"),
    ("B", SHIPPED_RULE, "A", SHIPPED_RULE, "descriptive — the resolution alone"),
    ("B", AUC_RULE, "B", SHIPPED_RULE, "descriptive — the stopping rule at 2x resolution"),
)


def readout(seeds: list[int], folds=None, arms=("A", "B")) -> dict:
    """Leg 1's whole table: the primary comparison, the decomposition, the standings.

    Every comparison is on the **seed-averaged** reading, which is what the bar
    asks for; each seed's own number is carried beside it and decides nothing.
    """
    readings = {
        (arm, rule): reading(arm, rule, seeds, folds) for arm in arms for rule in CHECKPOINTS
    }
    # One join, every comparison. See [`compare`] on why this is not a cache.
    carried = rank_key_columns()
    comparisons = []
    for candidate, candidate_rule, reference, reference_rule, why in COMPARISONS:
        if (candidate, candidate_rule) not in readings or (
            reference,
            reference_rule,
        ) not in readings:
            continue
        document = compare(
            readings[(candidate, candidate_rule)],
            readings[(reference, reference_rule)],
            (f"{candidate}@{candidate_rule}", f"{reference}@{reference_rule}"),
            carried,
        )
        document["why"] = why
        document["seed_averaged_over"] = list(seeds)
        # Each seed on its own, descriptive: the band the average came out of. A
        # comparison that reported only the mean would hide two seeds that
        # disagree about the sign.
        document["per_seed"] = [
            {
                "seed": seed,
                **{
                    key: value
                    for key, value in compare(
                        pooled(candidate, candidate_rule, seed, folds),
                        pooled(reference, reference_rule, seed, folds),
                        (candidate, reference),
                        carried,
                    )["primary"].items()
                    if key in ("n", "positives", "candidate", "reference", "delta", "lo", "hi")
                },
            }
            for seed in seeds
        ]
        comparisons.append(document)

    return {
        "schema": SCHEMA,
        "seeds": list(seeds),
        "folds": folds if folds is not None else "every fold read",
        "bar": BAR,
        "comparisons": comparisons,
        "standing": {
            f"{arm}@{rule}": standing(rows) for (arm, rule), rows in sorted(readings.items())
        },
        "epochs": [
            epochs_of(arm, fold, seed)
            for arm in arms
            for seed in seeds
            for fold in (
                folds
                if folds is not None
                else sorted(
                    int(path.parent.name.split("_")[0].removeprefix("fold"))
                    for path in (root() / arm).glob(f"fold*_seed{seed}/metrics.json")
                )
            )
        ],
    }


# --------------------------------------------------------------------------- #
# Leg 2: the crossovers, at LABEL geometry.
# --------------------------------------------------------------------------- #
def crossovers(rows: list[dict], kind: str = "strange_render") -> dict:
    """Where the head and the labels agree half the time, at each of two cutpoints.

    [`fractal_wallpapers.models.release_floor`]'s fit, over pooled out-of-fold
    predictions instead of over a shipped artifact's in-sample read: isotonic
    regression of `P(the human said >= t)` against the head's own `P(>=t)`,
    pool-adjacent-violators, ties pooled, and the crossing is the LOWEST score
    whose fitted agreement reaches a half.

    **Both cutpoints, because only one of them has ever been measured.** The `>=3`
    crossover is `curation.floors.STRANGE_RELEASE_BAR`'s statistic; the `>=4` one
    has never been fitted at all, because every row in the band a previous read
    looked at came back `>=3`.

    ⚠ **These are at LABEL geometry and they are NOT seating floors.** The store's
    rows are 1280x720 renders made by this repository's own coloring path; what
    the supply engine scores is a different regime and this judge is not
    regime-robust. Re-scoring at shipping geometry is a separate act and no bar
    is set on these numbers.
    """
    from fractal_wallpapers.models import release_floor

    members = [row for row in rows if row["kind"] == kind]
    if not members:
        raise GradingError(f"no {kind} rows to fit a crossover on")
    out: dict = {
        "kind": kind,
        "n": len(members),
        "geometry": "LABEL — the store's own 1280x720 renders, not shipping geometry",
        "not_a_floor": (
            "a crossover fitted at label geometry. The judge is not regime-robust and "
            "re-scoring at shipping geometry is a separate act; no bar is set here"
        ),
        "cutpoints": {},
    }
    for cutpoint in (3, 4):
        column = f"p_ge{cutpoint}"
        points = [
            (float(row[column]), 1.0 if int(row["score"]) >= cutpoint else 0.0) for row in members
        ]
        clustered = [
            (float(row[column]), 1.0 if int(row["score"]) >= cutpoint else 0.0, str(row["lineage"]))
            for row in members
        ]
        curve = release_floor.isotonic(points)
        where = release_floor.crossing(curve)
        keepers = sum(1 for _score, outcome in points if outcome)
        cell = {
            "crossing": where,
            "rounded_up_to_0_005": (
                release_floor.round_up_to_grid(where) if where is not None else None
            ),
            "interval_over_lineages": release_floor.bootstrap(clustered),
            "positives": keepers,
            "positive_share": round(keepers / len(points), 4),
            "admits": None,
            "admits_share": None,
            "primed_bar_admits": None,
            "primed_bar_admits_share": None,
        }
        if where is not None:
            admitted = sum(1 for score, _outcome in points if score >= where)
            cell["admits"] = admitted
            cell["admits_share"] = round(admitted / len(points), 4)
        # The volume the standing 0.90 admits on this same population and this
        # same scale, so the two numbers are comparable rather than two reads.
        over = sum(1 for score, _outcome in points if score >= PRIMED_BAR)
        cell["primed_bar"] = PRIMED_BAR
        cell["primed_bar_admits"] = over
        cell["primed_bar_admits_share"] = round(over / len(points), 4)
        out["cutpoints"][f"ge{cutpoint}"] = cell
    out["per_mode_ge4"] = _per_mode_crossovers(members, 4)
    out["per_mode_ge3"] = _per_mode_crossovers(members, 3)
    return out


#: The fewest rows and the fewest positives a per-mode crossover is reported at.
#: A crossover fitted on a handful of rows is a step function with a handful of
#: steps and it moves whole tenths on one verdict.
MODE_FLOOR_N, MODE_FLOOR_POSITIVES = 30, 5


def _per_mode_crossovers(rows: list[dict], cutpoint: int) -> list[dict]:
    """Per-mode crossovers where the count supports one. **Descriptive, with n.**"""
    from fractal_wallpapers.models import release_floor

    column = f"p_ge{cutpoint}"
    modes: dict[str, list] = {}
    for row in rows:
        modes.setdefault(row["mode"], []).append(row)
    out = []
    for mode in sorted(modes):
        members = modes[mode]
        points = [
            (float(row[column]), 1.0 if int(row["score"]) >= cutpoint else 0.0) for row in members
        ]
        positives = int(sum(outcome for _score, outcome in points))
        entry = {"mode": mode, "n": len(points), "positives": positives, "crossing": None}
        if len(points) >= MODE_FLOOR_N and positives >= MODE_FLOOR_POSITIVES:
            entry["crossing"] = release_floor.crossing(release_floor.isotonic(points))
        else:
            entry["withheld"] = (
                f"fewer than {MODE_FLOOR_N} rows or {MODE_FLOOR_POSITIVES} positives"
            )
        out.append(entry)
    return out


# --------------------------------------------------------------------------- #
# The reject autopsy: where the two readings disagree most about a human 4.
# --------------------------------------------------------------------------- #
#: How many rows each half of the autopsy sheet carries.
AUTOPSY_ROWS = 20


def _percentiles(rows: list[dict], column: str) -> dict:
    """Each row's rank of `column` within this population, as a fraction of it.

    Ranks and not probabilities, because the two readings are on two probability
    scales — CORN's scale is set by the training prior and the stopping rule
    moves it — and a raw difference between them would mostly be that move. What
    a bar reads here is order, so what the eye is shown is order too.
    """
    order = sorted(range(len(rows)), key=lambda index: float(rows[index][column]))
    out: dict = {}
    for place, index in enumerate(order):
        out[(rows[index]["kind"], rows[index]["name"])] = place / max(len(rows) - 1, 1)
    return out


def disagreements(
    candidate: list[dict], reference: list[dict], tier: int = 4, rows: int = AUTOPSY_ROWS
) -> dict:
    """The pictures the two readings rank furthest apart, both ways.

    **Ranked within the strange population, not within the tier.** A row's rank
    is what a cut acts on, so a row a person scored 4 that one reading puts at
    the 90th percentile and the other at the 40th is the thing a reject autopsy
    is about, whether or not any other four moved.
    """
    strange = [row for row in reference if row["kind"] == "strange_render"]
    keyed = {(row["kind"], row["name"]): row for row in candidate}
    mine = _percentiles([keyed[(row["kind"], row["name"])] for row in strange], "p_ge4")
    theirs = _percentiles(strange, "p_ge4")
    moved = [
        {
            "kind": row["kind"],
            "name": row["name"],
            "mode": row["mode"],
            "score": int(row["score"]),
            "batch": row["batch"],
            "fold": row["fold"],
            "candidate_percentile": mine[(row["kind"], row["name"])],
            "reference_percentile": theirs[(row["kind"], row["name"])],
            "moved": mine[(row["kind"], row["name"])] - theirs[(row["kind"], row["name"])],
            "candidate_p_ge4": float(keyed[(row["kind"], row["name"])]["p_ge4"]),
            "reference_p_ge4": float(row["p_ge4"]),
        }
        for row in strange
        if int(row["score"]) == tier
    ]
    moved.sort(key=lambda entry: entry["moved"])
    return {
        "tier": tier,
        "population": len(strange),
        "of_tier": len(moved),
        "candidate_above": list(reversed(moved[-rows:])),
        "reference_above": moved[:rows],
    }


def autopsy_sheet(document: dict, labels: tuple[str, str], output: Path, note: str = "") -> Path:
    """The disagreement halves as one page. Numbers alone do not close this."""
    import html as html_module

    from fractal_wallpapers.curation import sheet as sheet_module
    from fractal_wallpapers.models import renders

    def card(entry: dict) -> str:
        picture = renders.crop_dir(entry["kind"]) / f"{entry['name']}.jpg"
        thumbnail = sheet_module.thumbnail(picture) if picture.is_file() else ""
        body = (
            f'<img src="{thumbnail}" alt="">'
            if thumbnail
            else '<div class="missing">no picture on disk</div>'
        )
        facts = [
            f"human <b>{entry['score']}</b> &middot; {html_module.escape(entry['mode'])}",
            f"{labels[0]} pct <b>{entry['candidate_percentile']:.2f}</b> "
            f"(P {entry['candidate_p_ge4']:.3f})",
            f"{labels[1]} pct <b>{entry['reference_percentile']:.2f}</b> "
            f"(P {entry['reference_p_ge4']:.3f})",
            f"moved <b>{entry['moved']:+.2f}</b> &middot; fold {entry['fold']}",
        ]
        return f"<figure>{body}<figcaption>" + "<br>".join(facts) + "</figcaption></figure>"

    halves = (
        (
            f"{labels[0]} ranks these human-{document['tier']}s far ABOVE {labels[1]}",
            document["candidate_above"],
            "What the candidate reading buys, if it buys anything. These are pictures a "
            "person put at the top tier that the incumbent reading ranks low.",
        ),
        (
            f"{labels[1]} ranks these human-{document['tier']}s far above {labels[0]}",
            document["reference_above"],
            "What the candidate reading gives up. A candidate that clears the bar on "
            "average can still be worse in a way an average hides, and this is the half "
            "that would show it.",
        ),
    )
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>render judge grade: where the two readings disagree</title>",
        f"<style>{sheet_module.STYLE}</style>",
        "<h1>Where the two readings disagree about a human 4</h1>",
        f"<p class='lede'>Percentile of <code>P(&ge;4)</code> within the "
        f"{document['population']:,} strange held-out rows, on each reading's own scale. "
        f"{document['of_tier']:,} of them are human {document['tier']}s. Ranks rather than "
        f"probabilities: the two scales differ by construction and a bar reads order. "
        f"{html_module.escape(note)}</p>",
    ]
    for heading, entries, lede in halves:
        lines += [
            f"<h2>{html_module.escape(heading)} ({len(entries)})</h2>",
            f"<p class='lede'>{html_module.escape(lede)}</p>",
            "<div class='grid'>" + "".join(card(entry) for entry in entries) + "</div>",
        ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


__all__ = [
    "ARMS",
    "ASPECT_DIMS",
    "CARRIED_COLUMNS",
    "JUDGE_COLUMNS",
    "SOURCE_ASPECT",
    "columns_path",
    "key_delta",
    "key_readings",
    "rank_key_columns",
    "AUC_RULE",
    "AUC_SAYS",
    "BAR",
    "BOOTSTRAP_SEED",
    "CHECKPOINTS",
    "DOUBLED_DIMS",
    "DRAWS",
    "EPOCHS",
    "MODE_FLOOR_N",
    "MODE_FLOOR_POSITIVES",
    "PATIENCE",
    "PRIMED_BAR",
    "SCHEMA",
    "SHIPPED_DIMS",
    "SHIPPED_RULE",
    "STOP_SEED",
    "STOP_SHARE",
    "GradingError",
    "AUTOPSY_ROWS",
    "autopsy_sheet",
    "averaged",
    "disagreements",
    "compare",
    "crossovers",
    "fit",
    "negative_top_auc",
    "per_mode",
    "COMPARISONS",
    "epochs_of",
    "pooled",
    "read_out_of_fold",
    "readout",
    "reading",
    "read_rows",
    "root",
    "run_dir",
    "sides_for",
    "standing",
]
