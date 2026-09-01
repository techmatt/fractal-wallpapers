"""The fitted sort key a seating may rank on, instead of the judge's `P(>=4)`.

A seating walks a ranked list, and until now the rank was one number: the render
judge's `P(>=4)` on the candidate. That judge is the best single column there is
— every alternative tried alone loses to it — but it is not the only column with
signal in it, and the ones beside it are **orthogonal** rather than competing.

This is the form that came out of measuring them, `rank_key_fit`, 2026-08-28:

```text
sigmoid( b0 + b1*loc_p_ge4 + b2*p_ge3 + b3*p_ge4 + b4*stratum + b5*flat16_1.0 )
```

the location head's `P(>=4)` for the place, the render judge at two cutpoints,
the calibration stratum, and [`curation.flatness`]'s dead-space fraction — each
standardized by the fit's own constants.

## What this form reads, out of fold, as shipped

**0.779 smooth against the incumbent's 0.671** and **0.850 strange against
0.826** — `d` of `+0.107` and `+0.024` — over the 1,051 label rows that join the
ledger, five folds grouped on lineage.

Those are the **shared-weight** numbers, which are the ones this ships on.
`rank_key_fit`'s headline 0.797 / 0.852 is the *per-kind* arm with a nested inner
selection, and quoting it for a shared fit would over-read what is shipped by two
points of AUC on smooth. `curate rank-key fit` prints these two figures on every
run so the artifact and its reference line move together.

## Shared weights, not per kind

Per-kind minus shared is unresolved on every arm tried, which is the ruling. On
**this** form it is `+0.018 [-.002,+.039]` on smooth and `+0.005 [-.005,+.014]`
on strange — the `+0.000 [-.011,+.012]` the ruling cites is the three-column base
arm, not the five-column one that ships, and the difference is worth naming: on
the shipped form the interval is close enough to excluding zero that per-kind
weights are unresolved rather than *shown* to buy nothing.

Shared is also the only fit the fold structure supports: 96 of the 625 lineage
groups span both corpora and carry 348 of the 1,051 rows, so folds drawn per kind
would train on one half of a lineage while testing the other.

## Two cutpoints and not an expected tier

`p_ge3` and `p_ge4` enter as free columns rather than as `1 + p2 + p3 + p4`.
Expected tier as a single column **loses** — `-0.030*` on strange — and the fit
weights `p_ge3` above `p_ge4` on smooth, which an expected tier cannot express.

## What is deliberately not in it

No colormap identity, no palette group, and no human label aggregated by map. A
key that read a map's own label history would be a selection rule fit on the
thing it selects. `hunt.seconds` and everything derived from it are out for a
different reason, and **it is not coverage**. The stated reason here was "on 44%
of rows"; post-prune it is on **90.3%** of the 122,516 standing (2026-08-30), and
the absence is not scattered — it is whole-run, 0% or 100% on every one of the 36
runs, and every row without it predates the stamp.

The exclusion still stands because of what the column *is*. It is the wall-clock
seconds one worker spent rendering, colouring and scoring that candidate — a
reading of the machine and its load at that moment, not of the picture. The same
picture measures differently for reasons that are nothing about itself: rendered
under three workers it prices **1.53×** what it prices serially, measured on this
box at 196 ms against 300 ms. A sort key carrying it would order the pool partly
by how busy the machine was when each row happened to be drawn, and would be
unreproducible by construction — re-rendering the recipe cannot recover the
number. What signal it does hold is a proxy for iteration count, which the recipe
already carries honestly.

It also has one job already: [`headroom.render_cost`] prices a leg off it, and a
selection rule reading the same column the budget reads couples the two.

`mode` is out because the smooth population is one mode and the column is not
evaluable there.

## The artifact is tracked, the fit is a command, and the population is on record

[`artifact_path`] is a few hundred bytes of coefficients and standardization
constants, tracked, carrying the population it was fit on.
[`population_path`] beside it names **every label row the fit consumed** — the
store, the batch, the file and line, the render key, the tier, the lineage group
and the fold. A selection rule fit on human labels is a category no eligibility
guard covers today: the eligibility rule is about judge training, and this is not
that. The record costs nothing now and would be expensive to reconstruct later.

`fractal-wallpapers curate rank-key fit` rebuilds both.

## It is a sort key and never a bar

Every bar in this project stays on the judge's own columns. [`headroom.bars`] and
[`headroom.clearing`] read `p_ge4` and `p_ge3`, the neutral pre-selection reads
places, and this changes the **order** the surviving pool is walked in and
nothing else. That is what makes a before/after exact: two seatings differing in
the sort key and in no other thing.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import flatness, records

#: The schema the artifact and every population row carries.
SCHEMA = 1

#: The subtree the artifact and its population record live in, under the tracked
#: store. Text, a few hundred kilobytes, well under the history guard.
UNIT = "rank_key"

#: The form, in the order the coefficients are written and read.
COLUMNS = ("loc_p_ge4", "p_ge3", "p_ge4", "stratum_score", flatness.COLUMN)

#: The calibration stratum as a number, ordered rather than one-hot.
#:
#: `thin_colour` is a candidate dominant in a swatch at most
#: [`expressed.THIN_PICTURES`] finished pictures express; `composite` is a mode
#: with no scalar field to dump. They are the two populations the render judge is
#: least calibrated on and they are ordered by how far from its training mass
#: they sit, which a three-column one-hot would spend two degrees of freedom to
#: say and n=342 cannot afford.
STRATUM_ORDER = {"composite": 2.0, "other": 1.0, "thin_colour": 0.0}

#: Five folds at 20%, groups taken whole, assigned once over the **pooled**
#: corpus. The seed is pinned because a re-fit that redrew them would report an
#: out-of-fold number against a different partition of the same rows.
FOLDS = 5
FOLD_SEED = 20260828

#: L2 on the standardized columns. Conditioning only — small enough not to shrink
#: a five-column fit meaningfully, large enough that a collinear pair cannot send
#: the IRLS step to infinity.
LAMBDA = 1e-3

#: What a candidate at a place the location head has no row for is scored at.
#:
#: **Zero**, which is the location head's own reading of a place nothing knows
#: anything about, and the conservative direction: an unknown place ranks below a
#: place measured to be good rather than above it. Every seating record says how
#: many of its candidates took it.
NO_LOCATION_READING = 0.0

#: The two finished-render stores, which are the two label corpora the fit joins.
KINDS = ("smooth_render", "strange_render")


class RankKeyError(RuntimeError):
    """The key cannot be fitted, or cannot be loaded."""


# --------------------------------------------------------------------------- #
# Where it lives.
# --------------------------------------------------------------------------- #
def artifact_dir() -> Path:
    return records.default_root() / UNIT


def artifact_path() -> Path:
    """The coefficients, the standardization, and the population they came from."""
    return artifact_dir() / "rank_key.json"


def population_path() -> Path:
    """Every label row the fit consumed, one per line."""
    return artifact_dir() / "population.jsonl"


# --------------------------------------------------------------------------- #
# The fitted key.
# --------------------------------------------------------------------------- #
class Key:
    """A loaded artifact: standardize, weight, squash. Nothing else.

    The sigmoid is monotone, so it changes no ordering — it is kept because the
    number a record carries beside a seat should be on the same scale as the
    `P(>=4)` it is being compared with, and a raw linear predictor is not.
    """

    def __init__(self, document: dict):
        self.document = document
        self.columns = tuple(document["columns"])
        standardization = document["standardization"]
        self.mean = [float(standardization["mean"][name]) for name in self.columns]
        self.deviation = [float(standardization["deviation"][name]) for name in self.columns]
        weights = document["coefficients"]
        self.intercept = float(weights["intercept"])
        self.weights = [float(weights[name]) for name in self.columns]

    def score(self, features: dict) -> float:
        """One candidate's key value. Raises on a missing column, deliberately —
        a form that quietly imputed one would rank a picture nobody has read."""
        total = self.intercept
        for name, mean, deviation, weight in zip(
            self.columns, self.mean, self.deviation, self.weights, strict=True
        ):
            value = features.get(name)
            if value is None:
                raise RankKeyError(f"no {name!r} for this candidate, so it cannot be ranked")
            total += weight * (float(value) - mean) / deviation
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, total))))

    def record(self) -> dict:
        """What a seating puts on its own record to say what it ranked on."""
        return {
            "columns": list(self.columns),
            "coefficients": dict(self.document["coefficients"]),
            "standardization": dict(self.document["standardization"]),
            "fitted_at": self.document.get("fitted_at"),
            "population": self.document.get("population"),
        }


def load(path: Path | None = None) -> Key:
    """The shipped key. Refuses rather than falling back to the judge alone."""
    where = artifact_path() if path is None else Path(path)
    if not where.is_file():
        raise RankKeyError(
            f"{where} is not there, so there is no fitted rank key to seat on. Run "
            f"`fractal-wallpapers curate rank-key fit`."
        )
    return Key(json.loads(where.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# The columns, off a pool.
# --------------------------------------------------------------------------- #
def thin_cells() -> set:
    """The colour cells at most [`expressed.THIN_PICTURES`] finished pictures hold."""
    from fractal_wallpapers.curation import expressed

    return set(expressed.readout()["thin"])


def stratum_of(mode: str, cells, thin: set, kinds: dict | None = None) -> str:
    """`composite`, `thin_colour` or `other` for one candidate."""
    from fractal_wallpapers.curation import colorize

    kinds = {} if kinds is None else kinds
    if mode not in kinds:
        try:
            kinds[mode] = colorize.kind_of(mode)
        except Exception:
            kinds[mode] = "unknown"
    if kinds[mode] == "composite":
        return "composite"
    return "thin_colour" if set(cells or ()) & thin else "other"


def features_for(candidates, locations=None, readings=None, thin=None) -> tuple[dict, dict]:
    """`({key: {column: value}}, what could not be read)` over a pool.

    Every column comes off a store that already exists — the ledger row, the
    supply sidecar, the flatness sidecar — so this opens no picture and renders
    nothing. The one column that can be absent is the flatness reading, and a
    candidate without one is **left out** rather than imputed: `solve.pool`
    already excludes a row whose picture is gone, so a gap here means the sweep
    has not run, which is a thing to fix and not a thing to paper over.
    """
    from fractal_wallpapers.curation import intake

    location_scores = intake.read_scores() if locations is None else locations
    flat = flatness.by_recipe() if readings is None else readings
    lean = thin_cells() if thin is None else set(thin)
    kinds: dict = {}
    out: dict = {}
    gaps = {"no_flatness": 0, "no_location_reading": 0}
    for candidate in candidates:
        reading = flat.get(candidate.key)
        if reading is None:
            gaps["no_flatness"] += 1
            continue
        place = location_scores.get(candidate.location) or {}
        loc = place.get("p_ge4")
        if loc is None:
            gaps["no_location_reading"] += 1
        out[candidate.key] = {
            "loc_p_ge4": NO_LOCATION_READING if loc is None else float(loc),
            "p_ge3": float(candidate.p_ge3),
            "p_ge4": float(candidate.score),
            "stratum_score": STRATUM_ORDER[
                stratum_of(candidate.mode, candidate.cells, lean, kinds)
            ],
            flatness.COLUMN: float(reading),
        }
    return out, gaps


def order_for(candidates, key: Key | None = None, log=print) -> tuple[dict, dict]:
    """`({candidate key: rank value}, the coverage record)` for a whole pool.

    A candidate with no value is simply absent from the mapping.
    [`curation.solve`] ranks such a candidate **last** and counts it, which is
    the honest place for a row the key cannot read: it is not refused by a rule
    and it has not earned a place ahead of rows that were read.
    """
    held = load() if key is None else key
    features, gaps = features_for(candidates)
    values = {name: held.score(row) for name, row in features.items()}
    record = {
        "key": "rank_key",
        "columns": list(held.columns),
        "fitted_at": held.document.get("fitted_at"),
        "candidates": len(candidates),
        "ranked": len(values),
        "unranked": len(candidates) - len(values),
        **gaps,
        "no_location_reading_scored_at": NO_LOCATION_READING,
    }
    log(
        f"[rank-key] {len(values):,} of {len(candidates):,} candidates ranked; "
        f"{gaps['no_flatness']:,} have no flatness reading, "
        f"{gaps['no_location_reading']:,} no location reading"
    )
    return values, record


# --------------------------------------------------------------------------- #
# The fit.
# --------------------------------------------------------------------------- #
def standardize(matrix):
    mean = matrix.mean(axis=0)
    deviation = matrix.std(axis=0)
    deviation[deviation < 1e-12] = 1.0
    return mean, deviation


def logistic(design_columns, target, lam: float = LAMBDA, iterations: int = 100):
    """IRLS with an L2 on the slopes; the intercept is not penalised.

    Hand-written because `sklearn` is not in this project's dependency set and a
    five-column logistic is thirty lines. Checked in the suite against
    `scipy.optimize` on the same penalised objective.
    """
    import numpy

    rows, width = design_columns.shape
    design = numpy.hstack([numpy.ones((rows, 1)), design_columns])
    beta = numpy.zeros(width + 1)
    penalty = numpy.eye(width + 1) * lam
    penalty[0, 0] = 0.0
    for _ in range(iterations):
        eta = numpy.clip(design @ beta, -30, 30)
        mu = 1.0 / (1.0 + numpy.exp(-eta))
        weight = numpy.clip(mu * (1 - mu), 1e-9, None)
        gradient = design.T @ (target - mu) - penalty @ beta
        hessian = design.T @ (design * weight[:, None]) + penalty
        try:
            step = numpy.linalg.solve(hessian, gradient)
        except numpy.linalg.LinAlgError:
            step = numpy.linalg.lstsq(hessian, gradient, rcond=None)[0]
        beta = beta + step
        if numpy.max(numpy.abs(step)) < 1e-9:
            break
    return beta


def predict(beta, design_columns):
    import numpy

    rows = design_columns.shape[0]
    design = numpy.hstack([numpy.ones((rows, 1)), design_columns])
    return 1.0 / (1.0 + numpy.exp(-numpy.clip(design @ beta, -30, 30)))


def auc(target, score) -> float:
    """Mann-Whitney AUC on the tier-4 boundary, ties at half."""
    import numpy

    target = numpy.asarray(target).astype(bool)
    score = numpy.asarray(score, dtype=float)
    if target.sum() == 0 or (~target).sum() == 0:
        return float("nan")
    unique, inverse, counts = numpy.unique(score, return_inverse=True, return_counts=True)
    order = numpy.argsort(score, kind="mergesort")
    ranks = numpy.empty(score.size, dtype=float)
    ranks[order] = numpy.arange(1, score.size + 1, dtype=float)
    sums = numpy.zeros(unique.size)
    numpy.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    positives = int(target.sum())
    return float(
        (ranks[target].sum() - positives * (positives + 1) / 2) / (positives * int((~target).sum()))
    )


def ledger_identity(row: dict) -> tuple | None:
    """A ledger row's [`labeling.finished.render_key`] — the join, and the only one.

    The place, the mode, the mode params, the curve, the colormap and the seven
    palette knobs. Geometry is deliberately not in it and neither is the autolevel
    stamp: every ledger row stands at the candidate regime and label rows carry no
    autolevel block at all, so a key holding either would join nothing.
    """
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.supply.location import location_key

    recipe = row.get("recipe") or {}
    try:
        place = location_key(recipe.get("family") or {}, recipe.get("viewport") or {})
    except Exception:
        # More tolerant than [`finished.render_key`], deliberately and in one
        # direction only. This streams a hundred and twenty-eight thousand rows of
        # accumulated history, and `location_key` RAISES on a family it cannot
        # place rather than returning None — so one malformed row would kill a fit
        # over every other row. A row with no readable place has no identity here
        # either way; the only thing caught is how it says so.
        return None
    if place is None:
        return None
    palette = recipe.get("palette") or {}
    if any(name not in palette for name in finished.RECIPE_KEYS):
        return None
    mode, curve, colormap = recipe.get("mode"), recipe.get("curve"), recipe.get("colormap")
    if not all(isinstance(value, str) for value in (mode, curve, colormap)):
        return None
    return (
        place,
        mode,
        json.dumps(recipe.get("mode_params") or {}, sort_keys=True),
        curve,
        colormap,
        json.dumps({name: palette[name] for name in finished.RECIPE_KEYS}, sort_keys=True),
    )


def _stream_rows(path: Path | None = None):
    """The ledger a line at a time. Streamed rather than read whole because the
    fit needs six fields per row and the ledger is the largest store here — it
    grows every leg, and parsing all of it into dictionaries costs many times its
    own size in memory for the six fields this actually reads."""
    from fractal_wallpapers.curation import candidate_ledger

    where = candidate_ledger.rows_path() if path is None else Path(path)
    if not where.is_file():
        raise RankKeyError(f"{where} is not there — run `curate candidate-ledger backfill`")
    with where.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _folds(consumed: list, grouping_of: dict) -> dict:
    """Five folds at 20%, groups whole, assigned once over both kinds.

    Each group goes to the fold that minimises the **worst** per-kind fill, so
    neither store's folds go lopsided to serve the other's.
    """
    import random

    members: dict = {}
    for at in range(len(consumed)):
        members.setdefault(grouping_of.get(at), []).append(at)
    order = sorted(members, key=lambda value: (value is None, value))
    random.Random(FOLD_SEED).shuffle(order)
    totals = {kind: sum(1 for e in consumed if e["kind"] == kind) for kind in KINDS}
    targets = {kind: max(totals[kind] / FOLDS, 1e-9) for kind in KINDS}
    sizes = {kind: [0] * FOLDS for kind in KINDS}
    out: dict = {}
    for group in order:
        rows = members[group]
        added = {kind: sum(1 for at in rows if consumed[at]["kind"] == kind) for kind in KINDS}

        def cost(fold: int, added=added) -> tuple:
            return (
                max((sizes[kind][fold] + added[kind]) / targets[kind] for kind in KINDS),
                sum(sizes[kind][fold] for kind in KINDS),
                fold,
            )

        fold = min(range(FOLDS), key=cost)
        for at in rows:
            out[at] = fold
            sizes[consumed[at]["kind"]][fold] += 1
    return out


def fit(rows=None, log=print) -> dict:
    """Join the label corpora to the ledger, fit the shared form, ship both files.

    Four stages and each one is reported before the next: how many label rows
    resolve, how many join the ledger, how many of those carry every column, and
    what the fit reads out of fold. A join that silently lost half the corpus
    would otherwise be a coefficient set nobody could account for.
    """
    import time

    import numpy

    from fractal_wallpapers.curation import intake
    from fractal_wallpapers.labeling import finished, groups

    started = time.time()

    # ---- the label side ---------------------------------------------------- #
    labels: list = []
    stores: dict = {}
    for kind in KINDS:
        resolution = finished.resolved(kind)
        stores[kind] = resolution.summary()
        for row in resolution.scored():
            identity = finished.render_key(row)
            if identity is not None:
                labels.append({"kind": kind, "row": row, "identity": identity})
    log(f"[rank-key] {len(labels):,} resolved scored label rows over {len(KINDS)} stores")

    # ---- the ledger side, streamed ----------------------------------------- #
    wanted = {entry["identity"] for entry in labels}
    ledger: dict = {}
    seen = 0
    collisions = 0
    for row in _stream_rows() if rows is None else rows:
        seen += 1
        identity = ledger_identity(row)
        if identity is None or identity not in wanted:
            continue
        if identity in ledger:
            collisions += 1
            continue
        ledger[identity] = row
    log(f"[rank-key] {seen:,} ledger rows, {len(ledger):,} join a label, {collisions} collisions")

    # ---- the columns -------------------------------------------------------- #
    location_scores = intake.read_scores()
    flat = flatness.by_recipe()
    lean = thin_cells()
    kinds: dict = {}
    scores = _scores_by_recipe()
    consumed: list = []
    dropped = {"no_ledger_row": 0, "no_score": 0, "no_flatness": 0, "no_location_reading": 0}
    for entry in labels:
        row = ledger.get(entry["identity"])
        if row is None:
            dropped["no_ledger_row"] += 1
            continue
        key = str(row["key"])
        reading = scores.get(key)
        if reading is None or reading.get("p_ge3") is None or reading.get("p_ge4") is None:
            dropped["no_score"] += 1
            continue
        value = flat.get(key)
        if value is None:
            dropped["no_flatness"] += 1
            continue
        place = location_scores.get(str((row.get("location") or {}).get("key"))) or {}
        loc = place.get("p_ge4")
        if loc is None:
            dropped["no_location_reading"] += 1
        colour = row.get("colour") or {}
        mode = str((row.get("recipe") or {}).get("mode"))
        label = entry["row"]
        consumed.append(
            {
                "kind": entry["kind"],
                "recipe_key": key,
                "location_key": str((row.get("location") or {}).get("key")),
                "batch": label.get("batch"),
                "file": label.get("_file"),
                "line": label.get("_line"),
                "recorded_at": label.get("recorded_at"),
                "tier": int(label["score"]),
                "mode": mode,
                "features": {
                    "loc_p_ge4": NO_LOCATION_READING if loc is None else float(loc),
                    "p_ge3": float(reading["p_ge3"]),
                    "p_ge4": float(reading["p_ge4"]),
                    "stratum_score": STRATUM_ORDER[
                        stratum_of(mode, colour.get("cells") or (), lean, kinds)
                    ],
                    flatness.COLUMN: float(value),
                },
            }
        )
    log(f"[rank-key] {len(consumed):,} rows carry every column; dropped {dropped}")
    if len(consumed) < len(COLUMNS) * 10:
        raise RankKeyError(
            f"only {len(consumed)} label rows carry every column, which is not a population "
            f"to fit five weights on. Has `curate flatness sweep` run over the labeled rows?"
        )

    # ---- lineage groups and folds, over the POOLED corpus -------------------- #
    grouping = groups.assign([entry["row"] for entry in labels])
    group_of_label = {id(entry["row"]): grouping.of_row[at] for at, entry in enumerate(labels)}
    by_recipe_label = {}
    for entry in labels:
        row = ledger.get(entry["identity"])
        if row is not None:
            by_recipe_label.setdefault(str(row["key"]), entry["row"])
    grouping_of = {
        at: group_of_label.get(id(by_recipe_label.get(entry["recipe_key"])))
        for at, entry in enumerate(consumed)
    }
    fold_of = _folds(consumed, grouping_of)
    for at, entry in enumerate(consumed):
        entry["group"] = grouping_of.get(at)
        entry["fold"] = fold_of.get(at, 0)

    # ---- the fit ------------------------------------------------------------ #
    matrix = numpy.array(
        [[entry["features"][name] for name in COLUMNS] for entry in consumed], dtype=float
    )
    target = numpy.array([1.0 if entry["tier"] >= 4 else 0.0 for entry in consumed])
    mean, deviation = standardize(matrix)
    beta = logistic((matrix - mean) / deviation, target)

    # ---- out of fold, per kind, against the incumbent ------------------------ #
    folds = numpy.array([entry["fold"] for entry in consumed])
    predicted = numpy.zeros(len(consumed))
    for fold in range(FOLDS):
        held = folds == fold
        if held.sum() == 0 or (~held).sum() == 0 or len(numpy.unique(target[~held])) < 2:
            continue
        inner_mean, inner_deviation = standardize(matrix[~held])
        inner = logistic((matrix[~held] - inner_mean) / inner_deviation, target[~held])
        predicted[held] = predict(inner, (matrix[held] - inner_mean) / inner_deviation)
    incumbent = numpy.array([entry["features"]["p_ge4"] for entry in consumed])
    out_of_fold: dict = {}
    for kind in KINDS:
        mask = numpy.array([entry["kind"] == kind for entry in consumed])
        if mask.sum() == 0:
            continue
        mine, theirs = auc(target[mask], predicted[mask]), auc(target[mask], incumbent[mask])
        out_of_fold[kind] = {
            "rows": int(mask.sum()),
            "tier4": int(target[mask].sum()),
            "auc": round(mine, 4),
            "incumbent_auc": round(theirs, 4),
            "d": round(mine - theirs, 4),
        }
        log(
            f"[rank-key] {kind}: n={int(mask.sum())} AUC {mine:.3f} against the incumbent's "
            f"{theirs:.3f} (d {mine - theirs:+.3f}), out of fold"
        )

    document = {
        "schema": SCHEMA,
        "fitted_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "form": "sigmoid(intercept + sum(w_c * (x_c - mean_c) / deviation_c))",
        "columns": list(COLUMNS),
        "weights": "SHARED over both stores; per-kind bought +0.000 [-.011,+.012] smooth "
        "and +0.001 [-.005,+.007] strange, unresolved on every arm tried",
        "coefficients": {"intercept": round(float(beta[0]), 6)}
        | {name: round(float(value), 6) for name, value in zip(COLUMNS, beta[1:], strict=True)},
        "standardization": {
            "mean": {
                name: round(float(value), 6) for name, value in zip(COLUMNS, mean, strict=True)
            },
            "deviation": {
                name: round(float(value), 6) for name, value in zip(COLUMNS, deviation, strict=True)
            },
        },
        "stratum_order": dict(STRATUM_ORDER),
        "no_location_reading_scored_at": NO_LOCATION_READING,
        "population": {
            "rows": len(consumed),
            "by_kind": {
                kind: sum(1 for entry in consumed if entry["kind"] == kind) for kind in KINDS
            },
            "tier4": int(target.sum()),
            "tier_mix": {
                str(tier): sum(1 for entry in consumed if entry["tier"] == tier)
                for tier in (1, 2, 3, 4)
            },
            "batches": dict(
                sorted(
                    {
                        str(entry["batch"]): sum(
                            1 for other in consumed if other["batch"] == entry["batch"]
                        )
                        for entry in consumed
                    }.items()
                )
            ),
            "label_stores": stores,
            "labels_resolved": len(labels),
            "joined_the_ledger": len(ledger),
            "dropped": dropped,
            "lineage_groups": len({entry["group"] for entry in consumed}),
            "folds": FOLDS,
            "fold_seed": FOLD_SEED,
            "fold_sizes": {
                kind: [
                    sum(1 for entry in consumed if entry["kind"] == kind and entry["fold"] == fold)
                    for fold in range(FOLDS)
                ]
                for kind in KINDS
            },
            "population_record": str(population_path().name),
        },
        "out_of_fold": out_of_fold,
        "flatness": {
            "column": flatness.COLUMN,
            "cell": flatness.CELL,
            "threshold": flatness.THRESHOLD,
        },
        "seconds": round(time.time() - started, 1),
    }

    artifact_dir().mkdir(parents=True, exist_ok=True)
    artifact_path().write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    with population_path().open("w", encoding="utf-8", newline="\n") as handle:
        for entry in sorted(consumed, key=lambda item: (item["kind"], item["recipe_key"])):
            handle.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "kind": entry["kind"],
                        "recipe_key": entry["recipe_key"],
                        "location_key": entry["location_key"],
                        "batch": entry["batch"],
                        "file": entry["file"],
                        "line": entry["line"],
                        "recorded_at": entry["recorded_at"],
                        "tier": entry["tier"],
                        "mode": entry["mode"],
                        "lineage_group": entry["group"],
                        "fold": entry["fold"],
                        "features": {
                            name: round(float(entry["features"][name]), 6) for name in COLUMNS
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    log(f"[rank-key] {artifact_path()}")
    log(f"[rank-key] {population_path()} — {len(consumed):,} label rows on record")
    return document


def _scores_by_recipe() -> dict:
    """`{recipe key: reading}` on the live judge, off the ledger's own sidecar."""
    from fractal_wallpapers.curation import candidate_ledger

    return candidate_ledger.scores_by_recipe()


__all__ = [
    "COLUMNS",
    "FOLDS",
    "FOLD_SEED",
    "KINDS",
    "LAMBDA",
    "NO_LOCATION_READING",
    "SCHEMA",
    "STRATUM_ORDER",
    "UNIT",
    "Key",
    "RankKeyError",
    "artifact_dir",
    "artifact_path",
    "auc",
    "features_for",
    "fit",
    "logistic",
    "ledger_identity",
    "load",
    "order_for",
    "population_path",
    "predict",
    "standardize",
    "stratum_of",
    "thin_cells",
]
