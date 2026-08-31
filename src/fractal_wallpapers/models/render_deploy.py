"""The run that makes the head that ships: one fit, a forward holdout, one comparison.

Every band before this one produced fold models and nothing deployable.
[`render_cv`] screened three arms on one fifth of a five-way deal, [`render_grade`]
graded two arms over all five at two seeds, and [`render_dose`] read a curve — and
none of them ever trained a head on a whole corpus, because none of them was
supposed to. **This one is.** One training run, one artifact, and the artifact
ships.

The recipe is the incumbent's, unchanged in every respect but the stopping rule
below. Nothing about capacity, aspect, input size or architecture moves.

## The split is FORWARD, and that is the whole design

Eighty-twenty over **lineages** — the near-duplicate neighbourhoods
[`labeling.groups`] finds, the unit every split and every interval in this
project is drawn over, because two frames a hair apart on one plane are the same
picture twice.

What lands in the twenty is not a random draw. Two constraints decide it, and a
third slice is drawn afterwards to make the first two usable:

1. **Every row labeled after the shipped artifact was trained.** The incumbent
   ran on 2026-08-24 and its own record says it fitted 8,502 pictures;
   [`SHIPPED_CUT`] cuts the batches at that day and leaves 8,452, which is that
   number to within the forty off-kind rows this population drops and the ten
   rows that have arrived since. So the cut is checked rather than asserted. Those
   later rows are **the one population on which the incumbent and this head can
   be compared fairly**, because neither of them has ever seen a row of it.
2. **Every place pinned to a blind sheet.** `eval_split.jsonl` pins the places
   carrying no training row, and they stay eval-side so that a forward-draw
   sitting is still possible later. They are held and **not spent**: they train
   nothing, they stop nothing, and the comparison is not read on them.
3. **A stopping slice**, drawn by lineage out of what is left. It has to be drawn
   rather than taken, because the first two constraints between them leave
   nothing a run may legally early-stop on — the post-growth rows are the
   comparison and a pinned row may never be touched. Stopping on the rows a
   comparison is later reported from is selection on the test set, and it is free
   to avoid.

⚠ **So this head trains on less data than the incumbent did**, and a reader has
to hold that when reading the comparison: the shipped artifact fitted 8,118
pictures and this one fits about seven thousand, because the post-growth rows
that grew the corpus are the holdout by construction. It is not refit on
train-plus-holdout afterwards — that is the right close for a final head and this
is not one.

**The 1s and 2s stay in the holdout.** Precision in a top slice only means
something when the rows a head could wrongly rank highly are present; a holdout
of 3s and 4s cannot punish anything.

## The stopping rule is TOP-SLICE PRECISION, and it is sized off the mine

The epoch is chosen by [`top_slice_precision`]: rank the stopping slice by the
head's own `P(>=3)`, take the top [`TOP_SLICE`], and count what fraction of them
a person scored 3 or 4.

**Not the pooled cutpoint cross-entropy the incumbent uses**, which is decided by
the `>=2` boundary and stops the run where the easy question is happy. **Not
AUC**, which reads the whole ordering and is dominated by its middle, where this
head is not used. **Not `>=4` alone**: strange fours run to single digits per
mode and a top-quartile-only signal is noise, while `>=3` is where the counts are
real.

`TOP_SLICE` is 10% because that is about what the supply engine actually
promotes: over the 122,516 score rows the live judge has written into the
candidate ledger, `curation.mine.SEATING_BAR` — `P(>=4) >= 0.50`, where the
seating stage counts — admits **9.76%**, and `mine.PRIMED_BAR` at 0.90 admits
**3.88%**. The readout reports the precision at all three of those fractions, so
a reader can see whether the answer turns on the one that chose the epoch.

**Rank-only, so it cannot be gamed by refusing to commit.** A head that shrinks
every probability toward the prior improves a cross-entropy at a rare cutpoint
and leaves the *order* alone — which is why `render_cv.top_cutpoint_selection`
stopped at epoch 1 and why this rule cannot. And it takes a patience and a hard
cap, because on these stores the AUC rule chose epochs from 3 to 16 and one run
took the ceiling.

## What this does NOT do

It does not re-score the candidate pool. Matt has ruled that mixed-vintage scores
are accepted and the ledger is re-scored lazily, and the sidecar already carries
what that needs: every score row is keyed `(recipe, judge artifact, regime)` and
names its `judge_artifact` outright, so a row written after this ships is
attributable to this head and a row written before it names the one before.
See this module's report for the census.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.labeling import groups
from fractal_wallpapers.models import (
    finished_train,
    head,
    metrics,
    render_cv,
    render_train,
    train,
)
from fractal_wallpapers.paths import repo_root, under

#: The schema every record here carries.
SCHEMA = 1

#: The day the shipped artifact's band was trained. Every batch registered after
#: it is post-growth and is held out; every batch registered on or before it is
#: what the incumbent could have seen.
#:
#: It is a date rather than a reconstruction of the artifact's own population for
#: the reason [`render_dose`] gives: a batch is registered before its first row
#: exists, so the registration clock is carried by the store, while the shipped
#: run's population file joins on a file and a line that a tenth of its rows no
#: longer address. The date is nevertheless checked against that run's own
#: recorded count — see this module's header.
SHIPPED_CUT = "2026-08-24"

#: The run whose artifact serves today, named so the report can say what "absent"
#: means on a score row that carries no judge of its own.
INCUMBENT_RUN = "enlarged_corpus_seed1"

#: How many rows the stopping slice is drawn to hold, and the seed it is drawn
#: under. Lineages are taken whole, so the realized count lands near this rather
#: than on it, and the realized count is what every record says.
#:
#: A thousand rows puts about a hundred in the top decile the rule reads, which
#: moves in steps of one percent — coarse enough to see and fine enough to
#: choose on. Larger would buy a smoother statistic out of a training side that
#: is already smaller than the incumbent's.
STOP_ROWS = 1000
STOP_SEED = 0

#: The fraction of a ranking the stopping rule reads, and the two others every
#: readout reports beside it. 0.10 is about the rate the seating stage admits at
#: (9.76% of the ledger's live score rows clear `mine.SEATING_BAR`); 0.04 is
#: about the primed bar's (3.88% clear `mine.PRIMED_BAR`); 0.20 is the loose end,
#: reported so that a reader can see the answer is not an artefact of the choice.
TOP_SLICE = 0.10
REPORTED_SLICES = (0.04, 0.10, 0.20)

#: The column a top slice is ranked by, and the boundary a hit is counted at.
#: They are the same boundary on purpose: a precision at `>=3` read off an
#: ordering by `P(>=3)` is one question asked once, where ranking on one cutpoint
#: and scoring on another is two.
RANK_COLUMN = "p_ge3"
HIT_TIER = 3

#: The epoch ceiling and the patience. Twenty because every stopping rule ever
#: read on these stores picked an epoch under fifteen; six because a rule that
#: can run away is a rule that ships a budget rather than a choice.
EPOCHS = 20
PATIENCE = 6

#: The seed the run trains at. One run, one seed — this is a head and not a band.
SEED = 0

#: The run's name, which is also the directory it lands in under `models/render/`.
RUN = "forward_holdout_seed0"

#: Draws in every interval here and its seed. The repository's own, so an
#: interval from this module and one from any band are the same statistic.
DRAWS, BOOTSTRAP_SEED = render_cv.DRAWS, render_cv.BOOTSTRAP_SEED


class DeployError(RuntimeError):
    """A split, a fit or a comparison that cannot be made on what is here."""


def root() -> Path:
    """Where this run's derived records land. The regenerable tree."""
    return under("render_deploy")


def run_dir() -> Path:
    """Where the checkpoints land: beside the shipped heads, as every band does."""
    return render_train.head_dir(RUN)


def registration_dates() -> dict[tuple[str, str], str]:
    """`(kind, batch)` to the day that batch was registered, both stores."""
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
# The split.
# --------------------------------------------------------------------------- #
#: The three parts of the holdout, by the name every record here uses. The
#: comparison side is `eval` because that is what [`render_train.run`] calls the
#: side it never touches, and the stopping slice is `SELECTION` for the same
#: reason: this module owns a split, not a second trainer.
COMPARISON, STOPPING = "eval", render_train.SELECTION


def sides_for(population=None) -> tuple[list[dict], list, dict]:
    """The whole corpus with every picture on the side the forward split puts it.

    One pass, and the order it decides things in is the order the constraints
    bind. A row whose batch postdates the incumbent, or whose place is pinned,
    puts its **whole lineage** on the comparison side; a lineage drawn afterwards
    out of what is left becomes the stopping slice; everything else trains.

    Lineage closure is why the holdout comes out larger than the two constraints
    alone: a pre-growth row sharing a neighbourhood with a post-growth one cannot
    train, or the head would fit a near-duplicate of a row it is judged on. Those
    carried rows sit on the comparison side and are **not** reported from it —
    the comparison is read on the post-growth rows themselves.
    """
    rows, pictures, record = population or render_cv.pool()
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise DeployError(
            f"{grouping.n_unplaced} rows carry no location identity, so they cannot be "
            f"grouped. A holdout quietly holding ungrouped rows leaks by exactly the amount "
            f"nobody counted."
        )
    lineage = [int(group) for group in grouping.of_row]
    dates = registration_dates()
    pinned = {repr(place) for place in render_train.pinned_everywhere()}

    post = [
        index
        for index, picture in enumerate(pictures)
        if dates[(picture.kind, picture.batch)] > SHIPPED_CUT
    ]
    pins = [index for index, picture in enumerate(pictures) if picture.place in pinned]
    held_lineages = {lineage[index] for index in post} | {lineage[index] for index in pins}

    for picture, group in zip(pictures, lineage, strict=True):
        picture.side = COMPARISON if group in held_lineages else "train"

    # The stopping slice, out of what the constraints left. Whole lineages, so a
    # near-duplicate of a training picture never chooses the epoch, and seeded so
    # the draw is a function of the corpus rather than of when it was run.
    available = sorted({group for group in lineage if group not in held_lineages})
    members: dict[int, list[int]] = {}
    for index, group in enumerate(lineage):
        members.setdefault(group, []).append(index)
    order = list(available)
    random.Random(STOP_SEED).shuffle(order)
    chosen: set[int] = set()
    taken = 0
    for group in order:
        if taken >= STOP_ROWS:
            break
        chosen.add(group)
        taken += len(members[group])
    for group in chosen:
        for index in members[group]:
            pictures[index].side = STOPPING
    if not chosen:
        raise DeployError(
            "the two holdout constraints leave no lineage to draw a stopping slice from, so "
            "this run would have to early-stop on the rows it is later compared on"
        )

    training = [picture for picture in pictures if picture.side == "train"]
    stopping = [picture for picture in pictures if picture.side == STOPPING]
    comparison = [picture for picture in pictures if picture.side == COMPARISON]
    post_rows = [index for index in post]
    split = {
        "schema": SCHEMA,
        "rule": (
            "80/20 over LINEAGES, forward: every row registered after the incumbent trained "
            "and every pinned place put their whole lineage on the comparison side, and a "
            "seeded lineage draw out of the remainder is the stopping slice"
        ),
        "unit": "lineage — labeling.groups.assign",
        "shipped_cut": SHIPPED_CUT,
        "population": record,
        "grouping": grouping.summary(),
        "rows": len(pictures),
        "constraints": {
            "post_growth_rows": len(post),
            "pinned_rows": len(pins),
            "both": len(set(post) & set(pins)),
            "union": len(set(post) | set(pins)),
            "carried_in_by_lineage_closure": len(comparison) - len(set(post) | set(pins)),
        },
        "sides": {
            "train": len(training),
            "stopping": len(stopping),
            "comparison": len(comparison),
        },
        "holdout_share": round((len(stopping) + len(comparison)) / len(pictures), 4),
        "stopping_slice": {
            "target_rows": STOP_ROWS,
            "seed": STOP_SEED,
            "lineages": len(chosen),
            "of_available_lineages": len(available),
            "rows": len(stopping),
            "tiers": finished_train.histogram(stopping),
            "drawn_over": "LINEAGES outside both constraints, so no pinned row is ever stopped on",
        },
        "comparison_slice": {
            "rows": len(comparison),
            "tiers": finished_train.histogram(comparison),
            "post_growth_rows": len(post_rows),
            "post_growth_tiers": finished_train.histogram([pictures[i] for i in post_rows]),
            "pinned_rows": len(pins),
            "reported_on": (
                "the post-growth rows only. The pinned rows are held and not spent, and the "
                "rows lineage closure carried in were seen by the incumbent"
            ),
        },
        "train_tiers": finished_train.histogram(training),
    }
    return rows, pictures, split


def write_split(population=None) -> tuple[Path, dict]:
    _rows, _pictures, split = sides_for(population)
    path = root() / "split.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, split


# --------------------------------------------------------------------------- #
# The stopping rule.
# --------------------------------------------------------------------------- #
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


def top_slice_precision(labels, probabilities, classes: int) -> float:
    """`-precision@k` over the stopping slice, as an epoch objective to MINIMIZE.

    Negated so that it takes [`render_train.run`]'s selection contract unchanged
    — one convention for every rule this project has, rather than a maximizer and
    a minimizer a reader has to keep apart.

    **Rank-only.** Shrinking every probability toward the prior does not reorder
    anything, so an under-confident head cannot win this the way it wins a
    cross-entropy at a rare cutpoint.
    """
    import numpy

    column = int(HIT_TIER) - 2
    scores = numpy.asarray(probabilities)[:, column]
    read = precision_at(numpy.asarray(labels), scores, TOP_SLICE)
    return -float(read["precision"]) if read["precision"] is not None else float("inf")


SELECTION_SAYS = (
    f"max precision at the top {TOP_SLICE:.0%} of the stopping slice ranked by P(>={HIT_TIER}), "
    f"counting a row a person scored {HIT_TIER} or better as a hit, through the deploy "
    f"transform. Rank-only, and sized at the rate the seating stage actually admits"
)


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #
def fit(device: str = "auto", epochs: int | None = None, log=None) -> dict:
    """Train the head that ships: one run, the incumbent recipe, the new rule."""
    directory = run_dir()
    directory.mkdir(parents=True, exist_ok=True)

    def split():
        _rows, pictures, record = sides_for()
        return pictures, record

    return render_train.run(
        device=device,
        epochs=EPOCHS if epochs is None else int(epochs),
        seed=SEED,
        run_name=RUN,
        backbone=render_train.CANDIDATES["enlarged_corpus"]["backbone"],
        target_dims=None,
        split=split,
        directory=directory,
        selection=top_slice_precision,
        selection_says=SELECTION_SAYS,
        patience=PATIENCE,
        log=log or train.say,
    )


def shipped_artifact() -> Path:
    """The artifact that serves today, resolved through the manifest.

    `models/weights.json` is the only thing that answers *what ships*, so the
    incumbent column resolves through it rather than naming a file.
    """
    manifest = json.loads((repo_root() / "models" / "weights.json").read_text(encoding="utf-8"))
    entry = manifest["heads"][render_train.HEAD]
    path = repo_root() / "models" / render_train.HEAD / entry["asset"]
    if not path.is_file():
        raise DeployError(
            f"{path} is not here — `fractal-wallpapers fetch-weights` brings the shipped "
            f"artifact down, and the incumbent column cannot be read without it."
        )
    return path


def read_through(checkpoint: Path, label: str, device: str = "auto", log=train.say) -> Path:
    """Score the comparison side through one checkpoint and write the rows.

    Both heads are read through the same population in the same order, so the
    comparison never has to intersect anything afterwards.
    """
    rows, pictures, _split = sides_for()
    grouping = groups.assign(rows)
    lineage = [int(group) for group in grouping.of_row]
    dates = registration_dates()
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    held = [
        (row, picture, group)
        for row, picture, group in zip(rows, pictures, lineage, strict=True)
        if picture.side == COMPARISON
    ]
    if not held:
        raise DeployError("the comparison side is empty, so there is nothing to read")

    model, config, where = render_train.load_checkpoint(checkpoint, device)
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config["target_dims"]),
    )
    classes = int(config["classes"])
    log(f"{label}: reading {len(held)} comparison pictures through {checkpoint.name}")
    probabilities = train.score(
        model, [picture.path for _row, picture, _group in held], transform, where, classes, config
    )

    path = root() / f"comparison_{label}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (row, picture, group), probability in zip(held, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "head": label,
                "checkpoint": checkpoint.name,
                "epoch": config.get("best_epoch"),
                "lineage": int(group),
                "kind": picture.kind,
                "name": picture.name,
                "batch": row["batch"],
                "score": int(row["score"]),
                "registered": dates[(picture.kind, picture.batch)],
                "post_growth": dates[(picture.kind, picture.batch)] > SHIPPED_CUT,
                "pinned": picture.place in pinned,
                "mode": row["mode"],
                "partition": row.get("partition"),
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def read_rows(label: str) -> list[dict]:
    path = root() / f"comparison_{label}.jsonl"
    if not path.is_file():
        raise DeployError(f"{path} does not exist — read the comparison side through {label}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# --------------------------------------------------------------------------- #
# The comparison.
# --------------------------------------------------------------------------- #
#: **The one real comparison available, and it is narrow on purpose.** The
#: post-growth rows postdate the incumbent's training, so neither head has an
#: unfair claim on them — but they are also what was labeled most recently, which
#: on these stores means sparse strange modes and populations drawn off a head's
#: own top. It is a harder and narrower slice than a random one and **no level is
#: quotable from it for either head**.
COMPARISON_SAYS = (
    "top-slice precision at >=3 over the rows registered after the incumbent trained, on "
    "identical rows for both heads, with a 95% lineage bootstrap on the difference. The "
    "slice skews to whatever was labeled recently — by design, sparse strange modes and "
    "draws off a head's own top — so it is narrower and harder than a random slice and no "
    "LEVEL is claimed for either head"
)


def _delta_at(
    candidate, reference, fraction: float, column: str = RANK_COLUMN, tier: int = HIT_TIER
) -> dict:
    """The paired difference in precision@k, with a lineage interval on it.

    Precision at a slice is a property of a *population* rather than of a row, so
    the interval cannot come from a per-row paired delta: every resample has to
    re-rank both heads inside itself and take its own top slice. That is what
    this does, and it is why the statistic is written here rather than reached
    for in [`metrics`].
    """
    import numpy

    labels = numpy.array([int(row["score"]) for row in reference])
    ours = numpy.array([float(row[column]) for row in candidate])
    theirs = numpy.array([float(row[column]) for row in reference])
    lineages = numpy.array([row["lineage"] for row in reference])

    mine = precision_at(labels, ours, fraction, tier)
    others = precision_at(labels, theirs, fraction, tier)

    def statistic(picked):
        first = precision_at(labels[picked], ours[picked], fraction, tier)
        second = precision_at(labels[picked], theirs[picked], fraction, tier)
        if first["precision"] is None or second["precision"] is None:
            return None
        return first["precision"] - second["precision"]

    interval = metrics.bootstrap(statistic, lineages, draws=DRAWS, seed=BOOTSTRAP_SEED)
    return {
        "fraction": fraction,
        "column": column,
        "tier": tier,
        "n": len(reference),
        "lineages": int(len(set(lineages.tolist()))),
        "k": mine["k"],
        "base_rate": mine["base_rate"],
        "candidate": mine["precision"],
        "candidate_hits": mine["hits"],
        "reference": others["precision"],
        "reference_hits": others["hits"],
        "delta": mine["precision"] - others["precision"],
        "lo": interval["lo"],
        "hi": interval["hi"],
    }


def compare(
    candidate: str = RUN,
    reference: str = "shipped",
    only: str = "post_growth",
    column: str = RANK_COLUMN,
    tier: int = HIT_TIER,
) -> dict:
    """Both heads on identical comparison rows, at every reported slice.

    `only` names the cut of the comparison side this is read over.
    `post_growth` is the declared one; `pinned` reads the two blind sheets, which
    is descriptive and decides nothing; `all` reads the whole side, which
    includes rows the incumbent trained on and is therefore **not** a fair
    comparison — it is available for completeness and labelled.
    """
    mine, theirs = read_rows(candidate), read_rows(reference)
    keyed = {(row["kind"], row["name"]): row for row in mine}
    other = {(row["kind"], row["name"]): row for row in theirs}
    if set(keyed) != set(other):
        raise DeployError(
            f"the two heads did not read the same rows — {len(set(keyed) - set(other))} only "
            f"in the candidate. Both are read through one split; a difference is a bug."
        )
    cuts = {
        "post_growth": lambda row: bool(row["post_growth"]),
        "pinned": lambda row: bool(row["pinned"]),
        "all": lambda _row: True,
    }
    if only not in cuts:
        raise DeployError(f"{only!r} is not a cut of the comparison side; they are {sorted(cuts)}")
    keys = sorted(key for key in keyed if cuts[only](other[key]))
    if not keys:
        raise DeployError(f"the {only!r} cut of the comparison side is empty")
    candidate_rows = [keyed[key] for key in keys]
    reference_rows = [other[key] for key in keys]

    import collections

    return {
        "schema": SCHEMA,
        "candidate": candidate,
        "reference": reference,
        "cut": only,
        "says": COMPARISON_SAYS,
        "fair": only in {"post_growth", "pinned"},
        "rank_column": column,
        "hit_tier": tier,
        "declared": column == RANK_COLUMN and tier == HIT_TIER,
        "rows": len(keys),
        "kinds": dict(collections.Counter(row["kind"] for row in reference_rows)),
        "tiers": dict(collections.Counter(int(row["score"]) for row in reference_rows)),
        "draws": DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "slices": [
            _delta_at(candidate_rows, reference_rows, fraction, column, tier)
            for fraction in REPORTED_SLICES
        ],
    }


def epoch_curve() -> dict:
    """What the stopping rule saw, epoch by epoch, and where it stopped."""
    path = run_dir() / "metrics.json"
    if not path.is_file():
        raise DeployError(f"{path} does not exist — the run wrote no trace")
    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        "run": RUN,
        "rule": SELECTION_SAYS,
        "epochs_run": len(record.get("history") or []),
        "of_epochs": EPOCHS,
        "patience": PATIENCE,
        "best_epoch": record.get("best_epoch"),
        "stopped_early": record.get("stopped_early"),
        "wall_seconds": record.get("wall_seconds"),
        "trace": [
            {
                "epoch": row["epoch"],
                "top_slice_precision": (
                    None if row.get("selection_loss") is None else -float(row["selection_loss"])
                ),
                "selection_auc_ge3": row.get("selection_auc_ge3"),
            }
            for row in (record.get("history") or [])
        ],
    }


#: The readouts [`write_comparison`] writes, and what each one is.
#:
#: The first is the declared one. The second reads the **other** boundary, and it
#: is here because the declared one turned out to have no headroom on this slice:
#: the post-growth rows are 73% `>=3` by construction — they were drawn off the
#: incumbent's own top and off calibration bands — and both heads put `>=3` rows
#: in nearly the whole top quintile. A statistic where the incumbent scores 1.000
#: cannot say which head is better, and `>=4` is where the same population still
#: has a base rate worth ranking against.
READOUT_COLUMNS = (
    (RANK_COLUMN, HIT_TIER, "DECLARED — ranked by P(>=3), a hit is a human 3 or 4"),
    ("p_ge4", 4, "DESCRIPTIVE — ranked by P(>=4), a hit is a human 4. Gates nothing"),
)


def write_comparison(candidate: str = RUN, reference: str = "shipped") -> tuple[Path, dict]:
    cuts = []
    for column, tier, why in READOUT_COLUMNS:
        for cut in ("post_growth", "pinned", "all"):
            document = compare(candidate, reference, cut, column, tier)
            document["why"] = why
            cuts.append(document)
    document = {"schema": SCHEMA, "epoch": epoch_curve(), "cuts": cuts}
    path = root() / "comparison.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, document


__all__ = [
    "BOOTSTRAP_SEED",
    "COMPARISON",
    "COMPARISON_SAYS",
    "DRAWS",
    "EPOCHS",
    "HIT_TIER",
    "INCUMBENT_RUN",
    "PATIENCE",
    "RANK_COLUMN",
    "REPORTED_SLICES",
    "RUN",
    "SCHEMA",
    "SEED",
    "SELECTION_SAYS",
    "SHIPPED_CUT",
    "STOPPING",
    "STOP_ROWS",
    "STOP_SEED",
    "TOP_SLICE",
    "DeployError",
    "READOUT_COLUMNS",
    "compare",
    "epoch_curve",
    "fit",
    "precision_at",
    "read_rows",
    "read_through",
    "registration_dates",
    "root",
    "run_dir",
    "shipped_artifact",
    "sides_for",
    "top_slice_precision",
    "write_comparison",
    "write_split",
]
