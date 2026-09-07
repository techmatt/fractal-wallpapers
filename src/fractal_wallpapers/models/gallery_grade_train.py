"""The fine-tier head: an order inside the render judge's own top, and how it is fitted.

## What this head is, and what it is not

The shipped render judge answers *is this picture worth keeping*. It answers it
well and at the good end of its own scale it saturates: over the `gallery_grade`
store's thousand rows the judge's `P(>=4)` correlates with a person's grade at
Spearman **+0.171**, and of the 237 rows it puts at `P(>=4) >= 0.99` one is a 1,
twenty-six are 2s and a hundred and nine are 3s. So a seating that walks the
judge's order and takes the first `n` is taking an order nobody fitted to the
question it is being asked.

This head is fitted to that question. It is the **second stage of a cascade
behind `p_ge4`** and never a standalone scalar: its output is undefined on a row
that never cleared the gate, because every row it was fitted on had cleared one.
A pool-wide ranking read off it would be a ranking over a population it has never
seen, and no reading here may be quoted as one.

## A separate network, initialised from the shipped judge

Same architecture as the render judge — [`head.build`] on the small backbone, the
four-tier CORN ordinal classifier — and the weights start at
`models/render/render.fp16.pt`, the shipped **weights-v6** artifact.

**Never a shared trunk.** A trunk this fit moved would be a judge flip: the pool's
`p_ge4` column would move under it, which empties the seating pool and forces a
full rescore. The initialisation is a copy and the two nets are strangers
afterwards.

## The 640 column, and what it costs

A grade was cast on the sheet's 1280x720 ss2 picture; this fits on the ledger's
stored **640x360** candidate, which is the column a mining pass and a seating
actually read. The two geometries are not resamplings of each other and they
disagree: over the landed thousand they correlate at r = 0.696, with **55** rows
reading `P(>=4) < 0.5` at label geometry against none at candidate geometry.

Fitting on the 640 column therefore accepts a **label-quality cost** — some rows
carry a verdict about a picture a little different from the one the head is shown
— and it is accepted deliberately, because that is where the head serves. The
alternative buys a cleaner fit for a head read at a geometry nothing seats at.

## The recipe is the shipped judge's, unchanged

Every behavioural key is read out of `render.fp16.pt`'s own committed config and
carried: twenty epochs, patience six, batches of thirty-two, the two learning
rates, the decay, the drop rates, the gradient clip, geometric augmentation only,
the sqrt class balance times the per-place weight, and the epoch chosen on
**AP(>=3)** over the stopping slice with **AUC(>=3)** as the fallback where the
slice holds one class. [`INHERITANCE`] lists what came across and what did not,
because "the same recipe" is a claim a reader has to be able to check.

Three things moved and each is declared there rather than discovered in the
numbers: the source geometry, the batch stratification, and the split seed.

## The split is ONE split, and that is the change that matters

`render_deploy` draws its 80/20 under the **run's own seed**, so its three seeds
sit on three different stopping slices — which is why `models/render/README.md`
warns that the 0.008 between two of its APs "is not a comparison of two heads".
That is sound for a band whose question is *how does this recipe do*; it is
useless for a grid whose question is *which arm*.

So [`SPLIT_SEED`] is fixed and every arm and every seed reads the same sides. The
training seed moves the initialisation's dropout draw and the sampler's order and
nothing else, and every run of the grid is read on identical rows.

**The 20% is the stopping slice and it is also the only held-out number there
is.** That is the shipped recipe's own trade, carried: the holdout's one job is
to stop the run. Every AP and AUC below is therefore optimistic by exactly one
early stop, it is *within-store* held out, and the store is not eval-eligible —
its population is 700 seats plus 300 runners-up at one location apiece with no
colour-ceiling representation, so no number here is a base rate about anything.

## Stratified by batch, because the three sittings are three scales

The first sitting's three batches disagree at chi-square 30.95 on 6 d.f.,
**p = 2.6e-05**: the 1s fall away 17 -> 6 -> 3 as the labeler finds the floor and
the third piles onto 3 at the expense of 4. The strata were near-identical by
construction, so that is the scale moving and not the draw.

A lineage is the hard constraint and the batch is the soft one: groups are taken
whole, and the holdout is filled by whichever remaining group most reduces the
per-batch shortfall. `batch` is a covariate and is never handed to the model.

## How much trunk to unfreeze is measured, not argued

Three arms, in [`ARMS`]. The parameter shares are worth having in front of you
before reading the table, because this backbone is top-heavy: `conv_head` alone
is **1,228,800** of its 2,496,867 parameters, so "just the last block" is already
more than half the net.

```text
frozen       classifier only                            3,843    0.15%
last_block   + blocks[4], conv_head, norm_head      1,360,003   54.5%
more         everything                             2,496,867  100.0%
```

**A frozen module is put in `eval()` for the pass as well**, so its batch-norm
running statistics do not move. A "frozen" trunk whose normalisation kept
adapting is a trunk that trained, quietly, and the arm would be measuring
something nobody named.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import storage
from fractal_wallpapers.models import head
from fractal_wallpapers.paths import repo_root, tracked_name, under

#: The schema every record here carries.
SCHEMA = 1

#: What this head is called, everywhere it is named. The store's own name, because
#: the corpus is what makes it a different head — not [`roster.HEADS`], which is
#: what a release carries, and this ships nothing.
HEAD = "gallery_grade"

#: The shipped artifact this head starts from, relative to the checkout.
SOURCE = Path("models") / "render" / "render.fp16.pt"

#: The 80/20 over lineages, and the seed it is drawn under. **Fixed**, not the
#: run's — see the module docstring: a grid answering "which arm" has to be read
#: on one slice.
HOLDOUT_SHARE = 0.20
SPLIT_SEED = 0

#: The column the stopping rule ranks by, the boundary a hit is counted at, the
#: epoch ceiling and the patience — [`render_deploy`]'s four, and the shipped
#: judge's.
#:
#: **Written down rather than imported, and that is the one thing in this module
#: that is a copy.** Everything below `import` here is stdlib, so that a base
#: install can build the command line: `render_deploy` reaches `metrics`, which
#: reaches numpy, and one constant imported from the wrong module is all it takes
#: to put two gigabytes of CUDA wheels on the `fetch-weights --check` path — which
#: is exactly how that property was lost once already, and what
#: `tests/test_base_install.py` exists to catch. `tests/test_gallery_grade_train.py`
#: holds these four to `render_deploy`'s, so the copy cannot drift in silence.
RANK_COLUMN, HIT_TIER = "p_ge3", 3
EPOCHS = 20
PATIENCE = 6

#: The seeds a full band runs. **Two, on Matt's call of 2026-09-06**, where every
#: other band here runs three: the split is fixed across the whole grid, so a seed
#: moves the initialisation's dropout draw and the sampler's order and nothing
#: else, and a second seed is enough to say whether an arm's gap is larger than
#: its own run-to-run spread. What two seeds cannot do is put an interval on that
#: spread, and no reading here claims one.
SEEDS = (0, 1)

#: How much trunk each arm unfreezes, as the `timm` child modules whose parameters
#: take a gradient. The classifier is in every arm because a head that trained
#: nothing would not be a head.
#:
#: `more` is **everything**, and that is a choice rather than the obvious reading
#: of the word. Three points spanning 0.2%, 54.4% and 100% of the parameters is a
#: wider span than any interior cut would give, and the full fine-tune is the arm
#: most at risk on a training side of a few hundred pictures — which is the risk
#: this comparison exists to price.
ARMS: dict[str, dict] = {
    "frozen": {
        "unfrozen": ("classifier",),
        "says": "the trunk is a fixed feature extractor; only the ordinal classifier learns",
    },
    "last_block": {
        "unfrozen": ("blocks.4", "conv_head", "norm_head", "classifier"),
        "says": (
            "the last block stage and the pointwise head above it. Half the net by "
            "parameter count, because conv_head alone is 49% of this backbone"
        ),
    },
    "more": {
        "unfrozen": (),  # empty means: nothing is frozen
        "says": "a full fine-tune — every parameter takes a gradient",
    },
}


class GradeTrainingError(RuntimeError):
    """A fine-tier head that cannot be fitted or read on what is here."""


def say(*parts) -> None:
    """[`train.say`], reached lazily so this module imports on a base install.

    It is the default `log` of every entry point here, and a default argument is
    evaluated at import — so `log=say` would be the numpy import this
    module is arranged to avoid, written as a default rather than as an import.
    """
    from fractal_wallpapers.models import train

    train.say(*parts)


# --------------------------------------------------------------------------- #
# Where things live.
# --------------------------------------------------------------------------- #
def head_dir(run: str | None = None) -> Path:
    """Where a run's checkpoints and records land. Beside the shipped heads.

    Not on [`roster.HEADS`], so no release carries it and `fetch-weights` never
    asks for it; the `.pt` files are ignored by the same `models/**/*.pt` rule
    every other head's are, so the weights stay out of history while the records
    that describe them do not.
    """
    base = repo_root() / "models" / HEAD
    return base / run if run else base


def run_name(arm: str, seed: int) -> str:
    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")
    return f"{arm}_seed{int(seed)}"


def run_dir(arm: str, seed: int) -> Path:
    return head_dir(run_name(arm, seed))


def root() -> Path:
    """The regenerable tree this fit's own readouts land in.

    Its own top-level name and **not** `artifacts/gallery_grade`, which holds the
    sheets' plans — the only thing that can rebuild a levelled picture as it was
    judged, and protection-held for that reason. A regenerable readout does not
    go into a subtree somebody has to be careful about deleting.
    """
    return under("gallery_grade_head")


def population_path() -> Path:
    return root() / "population.jsonl"


def split_path() -> Path:
    return root() / "split.json"


def band_path() -> Path:
    return root() / "band.json"


# --------------------------------------------------------------------------- #
# The population: a grade, and the candidate picture it was cast about.
# --------------------------------------------------------------------------- #
@dataclass
class Unit:
    """One training unit: a grade, and the ledger's 640x360 picture of that recipe.

    **[`finished_train.Picture`]'s fields, by name, and not its subclass.** The
    sampler, the class balance and the histogram are that module's and are reached
    unchanged — they read `.path`, `.score` and `.place` off whatever they are
    handed — but inheriting would mean importing it to *define* this class, and
    everything at this module's top level is stdlib so that a base install can
    build the command line. The duck-typed shape is all any of them needs, which
    is the argument [`finished_train.Crops`] already makes about `torch.Dataset`.

    ⚠ **The `score` field carries a GRADE**, and the two are different estimands —
    `data/gallery_grade/README.md`'s *This is not a fifth judge, and its 1 is not
    anybody's 1*. The field keeps that name because the sampler and the histogram
    read it, and re-typing a sampler to rename a field would measure the
    re-typing. The rename happens exactly once, in [`population`], and nothing
    downstream of it writes a store.

    `key` is the ledger key, which is also what the seeded per-picture jitter is
    drawn on through the parent's `name`.

    **The two judge readings are carried and are two different numbers.**
    `label_p_ge*` is the shipped judge on the 1280x720 sheet picture the verdict
    was cast on; `candidate_p_ge*` is `selected_on` — the same judge on the
    640x360 row a mining pass scored, which is both the picture this head is
    trained on and the column a seating walks. They correlate at r = 0.696 over
    the store, which is far too low for either to stand in for the other, so a
    baseline quoting one of them has to say which.
    """

    # [`finished_train.Picture`]'s eight, in its order and by its names.
    path: Path
    score: int
    side: str
    batch: str
    place: str
    partition: str
    mode: str
    name: str
    # And this store's own.
    key: str = ""
    leveled: bool = False
    seated: bool = False
    label_p_ge3: float | None = None
    label_p_ge4: float | None = None
    candidate_p_ge3: float | None = None
    candidate_p_ge4: float | None = None


def population(log=say) -> tuple[list[Unit], dict]:
    """Every graded row, joined to the ledger row whose picture it was cast about.

    One streaming pass over the ledger, which is the largest store here and is
    read a line at a time for [`curation.rank_key`]'s reason: the join needs four
    fields a row and parsing four hundred megabytes into dictionaries costs many
    times its own size for them.

    A row that will not resolve is **dropped and counted with its reason** rather
    than repaired: the store is append-only and the ledger is the authority on
    what is on disk.
    """
    from fractal_wallpapers.curation import candidate_ledger, retention
    from fractal_wallpapers.labeling import gallery_grade
    from fractal_wallpapers.models import finished_train
    from fractal_wallpapers.paths import Tiers, rehome

    graded = gallery_grade.resolved().graded()
    wanted: dict = {}
    unkeyed = 0
    for row in graded:
        key = gallery_grade.render_key(row)
        if key is None:
            unkeyed += 1
            continue
        wanted.setdefault(key, []).append(row)

    ledger = candidate_ledger.rows_path()
    if not ledger.is_file():
        raise GradeTrainingError(f"{ledger} is not there — run `curate candidate-ledger backfill`")

    found: dict = {}
    scanned = 0
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            scanned += 1
            stored = json.loads(line)
            key = retention.render_key_of(stored)
            if key is not None and key in wanted:
                found.setdefault(key, []).append(stored)
    log(f"[{HEAD}] {scanned:,} ledger rows scanned for {len(wanted):,} graded render keys")

    tiers = Tiers.current()
    units: list[Unit] = []
    dropped = {"unkeyed": unkeyed, "no_ledger_row": 0, "no_picture": 0, "picture_absent": 0}
    ambiguous = 0
    for key, rows in wanted.items():
        carriers = found.get(key) or []
        if not carriers:
            dropped["no_ledger_row"] += len(rows)
            continue
        if len(carriers) > 1:
            ambiguous += 1
        # Deterministic where a key is carried by more than one row: the ledger
        # key sorts, and a later leg re-rendering one of these recipes at another
        # regime is the harmless direction the retention guard already names.
        stored = sorted(carriers, key=lambda held: str(held.get("key")))[0]
        named = stored.get("picture")
        if not named:
            dropped["no_picture"] += len(rows)
            continue
        where = rehome(str(named), tiers)
        if where is None or not where.is_file():
            dropped["picture_absent"] += len(rows)
            continue
        for row in rows:
            reading = row.get("reading") or {}
            drawn = row.get("selected_on") or {}
            units.append(
                Unit(
                    path=where,
                    score=int(row["grade"]),
                    side="",
                    batch=str(row["batch"]),
                    place=repr(gallery_grade.place_of(row)),
                    partition=row.get("partition") or "",
                    mode=str(row["mode"]),
                    name=str(stored.get("key")),
                    key=str(stored.get("key")),
                    leveled=bool(row.get("leveled")),
                    seated=bool(row.get("seated")),
                    label_p_ge3=reading.get("p_ge3"),
                    label_p_ge4=reading.get("p_ge4"),
                    candidate_p_ge3=drawn.get("p_ge3"),
                    candidate_p_ge4=drawn.get("p_ge4"),
                )
            )

    storage.require_hot(*{unit.path.parent for unit in units}, what="fitting the fine-tier head")

    record = {
        "graded_rows": len(graded),
        "render_keys": len(wanted),
        "ledger_rows_scanned": scanned,
        "ledger_path": tracked_name(ledger),
        "resolved": len(units),
        "dropped": dropped,
        "keys_carried_by_more_than_one_ledger_row": ambiguous,
        "geometry": "the ledger's stored 640x360 candidate — not the 1280x720 sheet picture",
        "batches": _counted(unit.batch for unit in units),
        "grades": finished_train.histogram(units),
        "leveled": sum(1 for unit in units if unit.leveled),
        "seated": sum(1 for unit in units if unit.seated),
        "locations": len({unit.place for unit in units}),
    }
    total_dropped = sum(dropped.values())
    if total_dropped:
        log(f"[{HEAD}] dropped {total_dropped} row(s): {json.dumps(dropped)}")
    if not units:
        raise GradeTrainingError("no graded row resolved to a candidate picture")
    return units, record


def _counted(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


def write_population(log=say) -> tuple[Path, dict]:
    """Resolve the store against the ledger once and keep the answer.

    The ledger pass is the expensive half of a fit and it does not change between
    arms, so it is cached under the regenerable tree and every run reads it.
    """
    units, record = population(log=log)
    path = population_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "key": unit.key,
                        "picture": tracked_name(unit.path),
                        "grade": unit.score,
                        "batch": unit.batch,
                        "place": unit.place,
                        "partition": unit.partition,
                        "mode": unit.mode,
                        "leveled": unit.leveled,
                        "seated": unit.seated,
                        "label_p_ge3": unit.label_p_ge3,
                        "label_p_ge4": unit.label_p_ge4,
                        "candidate_p_ge3": unit.candidate_p_ge3,
                        "candidate_p_ge4": unit.candidate_p_ge4,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    (root() / "population.json").write_text(
        json.dumps({"schema": SCHEMA, **record}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path, record


def read_population() -> list[Unit]:
    """The cached join, re-homed against this machine's tiers."""
    from fractal_wallpapers.paths import Tiers, rehome

    path = population_path()
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} is not there — run `gallery-grade population` first, so that every arm "
            f"is fitted on one join rather than on its own."
        )
    tiers = Tiers.current()
    units: list[Unit] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise GradeTrainingError(f"{path}:{number}: schema {row.get('schema')!r}")
        units.append(
            Unit(
                path=rehome(row["picture"], tiers) or Path(row["picture"]),
                score=int(row["grade"]),
                side="",
                batch=row["batch"],
                place=row["place"],
                partition=row.get("partition") or "",
                mode=row["mode"],
                name=row["key"],
                key=row["key"],
                leveled=bool(row.get("leveled")),
                seated=bool(row.get("seated")),
                label_p_ge3=row.get("label_p_ge3"),
                label_p_ge4=row.get("label_p_ge4"),
                candidate_p_ge3=row.get("candidate_p_ge3"),
                candidate_p_ge4=row.get("candidate_p_ge4"),
            )
        )
    return units


# --------------------------------------------------------------------------- #
# The split: lineages whole, batches balanced.
# --------------------------------------------------------------------------- #
def sides_for(units: list[Unit], seed: int = SPLIT_SEED, rows: list[dict] | None = None) -> dict:
    """Put every unit on the side the seeded, batch-stratified 80/20 gives it.

    Lineages are the hard constraint and go whole. Inside that, the holdout is
    filled by whichever remaining lineage most reduces the **per-batch** shortfall
    — the three sittings are three slightly different scales, so a stopping slice
    that happened to over-weight one of them would be stopping on a scale the
    training side is not on.

    `rows` is the label rows the units came from, in the same order; the grouping
    rule reads a family and a viewport off them and this module does not carry a
    second spelling of either.
    """
    import random

    from fractal_wallpapers.labeling import groups
    from fractal_wallpapers.models import finished_train

    if rows is None:
        rows = label_rows_for(units)
    grouping = groups.assign(rows)
    if grouping.n_unplaced:
        raise GradeTrainingError(
            f"{grouping.n_unplaced} row(s) carry no location identity, so they cannot be "
            f"grouped. A holdout quietly holding ungrouped rows leaks by exactly the amount "
            f"nobody counted."
        )
    lineage = [int(group) for group in grouping.of_row]
    members: dict[int, list[int]] = {}
    for index, group in enumerate(lineage):
        members.setdefault(group, []).append(index)

    batches = sorted({unit.batch for unit in units})
    per_batch = {name: sum(1 for unit in units if unit.batch == name) for name in batches}
    target = {name: per_batch[name] * HOLDOUT_SHARE for name in batches}
    wanted = round(len(units) * HOLDOUT_SHARE)

    def vector(group: int) -> dict[str, int]:
        out = dict.fromkeys(batches, 0)
        for index in members[group]:
            out[units[index].batch] += 1
        return out

    order = sorted(members)
    random.Random(int(seed)).shuffle(order)
    remaining = list(order)
    held: set[int] = set()
    shortfall = dict(target)
    rows_held = 0
    while rows_held < wanted and remaining:
        # The group that most reduces the L1 shortfall, ties broken by the
        # shuffled order — so the draw is a function of the seed and the corpus.
        best, best_gain = None, None
        for group in remaining:
            counts = vector(group)
            gain = sum(
                abs(shortfall[name]) - abs(shortfall[name] - counts[name]) for name in batches
            )
            if best_gain is None or gain > best_gain:
                best, best_gain = group, gain
        held.add(best)
        for name, count in vector(best).items():
            shortfall[name] -= count
        rows_held += len(members[best])
        remaining.remove(best)

    if rows_held >= len(units):
        raise GradeTrainingError("the holdout swallowed the corpus; nothing is left to train on")

    for index, unit in enumerate(units):
        unit.side = "stopping" if lineage[index] in held else "train"

    training = [unit for unit in units if unit.side == "train"]
    stopping = [unit for unit in units if unit.side == "stopping"]
    return {
        "schema": SCHEMA,
        "rule": (
            f"a seeded {1 - HOLDOUT_SHARE:.0%}/{HOLDOUT_SHARE:.0%} over LINEAGES, filled by "
            f"whichever remaining lineage most reduces the per-BATCH shortfall. The holdout's "
            f"only job is to stop the run — it is the shipped judge's split with one seed for "
            f"every arm, so every run of the grid is read on one slice"
        ),
        "unit": "lineage — labeling.groups.assign",
        "seed": int(seed),
        "target_share": HOLDOUT_SHARE,
        "rows": len(units),
        "lineages": len(members),
        "grouping": grouping.summary(),
        "sides": {"train": len(training), "stopping": len(stopping)},
        "holdout_share": round(len(stopping) / len(units), 4),
        "holdout": {"target_rows": wanted, "rows": len(stopping), "lineages": len(held)},
        "batches": {
            "population": per_batch,
            "stopping": _counted(unit.batch for unit in stopping),
            "train": _counted(unit.batch for unit in training),
            "stopping_share_by_batch": {
                name: round(
                    sum(1 for unit in stopping if unit.batch == name) / max(per_batch[name], 1), 4
                )
                for name in batches
            },
        },
        "grades": {
            "train": finished_train.histogram(training),
            "stopping": finished_train.histogram(stopping),
        },
        "lineage_of_row": lineage,
        # The side each row landed on, carried so a later run APPLIES this split
        # rather than re-deriving one. Two derivations of one split are two
        # splits the day either input moves, and the whole point of a fixed seed
        # here is that every run of the grid reads the same rows.
        "side_of_row": [unit.side for unit in units],
        "key_of_row": [unit.key for unit in units],
    }


def label_rows_for(units: list[Unit]) -> list[dict]:
    """The store rows the units came from, in the units' order.

    The grouping rule reads a family and a viewport, which live on the label row
    and not on a training unit — so they are fetched from the store rather than
    copied onto the unit, where a stale copy could disagree with the corpus.
    """
    from fractal_wallpapers.labeling import gallery_grade

    by_place: dict[str, dict] = {}
    for row in gallery_grade.resolved().graded():
        by_place.setdefault(repr(gallery_grade.place_of(row)), row)
    out = []
    for unit in units:
        row = by_place.get(unit.place)
        if row is None:
            raise GradeTrainingError(f"no store row for place {unit.place}")
        out.append(row)
    return out


def write_split(seed: int = SPLIT_SEED, log=say) -> tuple[Path, dict]:
    units = read_population()
    record = sides_for(units, seed)
    path = split_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(
        f"[{HEAD}] split: train {record['sides']['train']} / stopping "
        f"{record['sides']['stopping']} over {record['lineages']} lineages"
    )
    return path, record


def read_split() -> dict:
    path = split_path()
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} does not exist — draw the split before fitting on it, so that every arm "
            f"is read on one slice rather than on its own."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def apply_split(units: list[Unit], document: dict | None = None) -> dict:
    """Put the written split's sides back onto a freshly read population.

    **Applied, never re-derived.** Re-running the draw would give the same answer
    today and a different one the day the store or the ledger moves, and a band
    whose runs quietly sat on two splits would be comparing arms across
    populations. The row order and the keys are both checked, because a file
    agreeing about a length is not a file agreeing about a corpus.
    """
    document = document or read_split()
    sides = document["side_of_row"]
    keys = document["key_of_row"]
    if len(sides) != len(units):
        raise GradeTrainingError(
            f"the split was drawn over {len(sides)} rows and the population holds "
            f"{len(units)}. Re-draw it: a split read onto a different corpus is not a split."
        )
    disagreeing = [
        index for index, (unit, key) in enumerate(zip(units, keys, strict=True)) if unit.key != key
    ]
    if disagreeing:
        raise GradeTrainingError(
            f"{len(disagreeing)} row(s) of the population are not the rows the split was "
            f"drawn over (first at index {disagreeing[0]}). Re-draw the split."
        )
    for unit, side in zip(units, sides, strict=True):
        unit.side = side
    return document


# --------------------------------------------------------------------------- #
# The recipe, carried out of the shipped artifact.
# --------------------------------------------------------------------------- #
#: The behavioural keys this head takes from `render.fp16.pt`'s own config, read
#: off the file rather than restated — a constant that drifted from the artifact
#: would be a claim of "the same recipe" nobody could check.
CARRIED = (
    "classes",
    "backbone",
    "batch_size",
    "backbone_lr",
    "head_lr",
    "weight_decay",
    "drop_rate",
    "drop_path_rate",
    "grad_clip",
    "amp",
    "border_crop",
    "class_balance",
    "geometry",
    "loss",
    "sampler",
    "selection_cutpoint",
    "target_dims",
    "workers",
)

#: What the recipe inherited, and the three things it did not. "The same recipe"
#: is a claim a reader has to be able to check rather than take.
INHERITANCE = {
    "identical_to_the_shipped_render_judge": list(CARRIED) + ["epochs", "patience", "selection"],
    "chosen": [
        {
            "key": "source_dims",
            "was": "1280x720 — the sheet picture a verdict was cast on",
            "now": "640x360 — the ledger's stored candidate",
            "why": (
                "this head is read where a seating reads, and the two geometries are not "
                "resamplings of each other: they correlate at r = 0.696 over the landed "
                "thousand, with 55 rows under P(>=4) 0.5 at label geometry and none at "
                "candidate geometry. Fitting at the deployment column accepts a label-quality "
                "cost on purpose"
            ),
        },
        {
            "key": "split_stratification",
            "was": "lineages only",
            "now": "lineages whole, and the holdout filled to balance the three BATCHES",
            "why": (
                "the three sittings disagree at p = 2.6e-05 and the strata were "
                "near-identical by construction, so a stopping slice over-weighting one "
                "sitting would stop on a scale the training side is not on"
            ),
        },
        {
            "key": "split_seed",
            "was": "the run's own seed, so each seed sits on its own slice",
            "now": f"fixed at {SPLIT_SEED} for every arm and every seed",
            "why": (
                "the question here is WHICH ARM, and models/render/README.md says why the "
                "incumbent arrangement cannot answer it: an AP read on two different slices "
                "is not a comparison of two heads. The training seed still moves the "
                "initialisation and the sampler order"
            ),
        },
    ],
    "not_inherited": [
        {
            "key": "pretrained",
            "why": (
                "the backbone is not re-initialised from ImageNet at all — it starts at the "
                "shipped weights-v6 artifact, which is what makes this a second stage rather "
                "than a second judge"
            ),
        },
        {
            "key": "kinds",
            "why": (
                "the render judge is told no kind and this head is told no batch. The "
                "corpus is one store with one scale"
            ),
        },
    ],
}


def source_path() -> Path:
    return repo_root() / SOURCE


def initial_state() -> tuple[dict, dict]:
    """`(the shipped judge's weights, its committed config)` — this head's start.

    Loaded through the same widening every reader of a halved artifact uses: the
    file is fp16 and the head runs in full precision.
    """
    import torch

    path = source_path()
    if not path.is_file():
        raise GradeTrainingError(
            f"{path} is not there. This head is initialised from the shipped render judge — "
            f"run `fractal-wallpapers fetch-weights` before fitting."
        )
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    head.assert_shipped_backbone(path, config)
    return {key: value.float() for key, value in saved["state_dict"].items()}, config


def recipe_from(config: dict) -> dict:
    """The shipped config's behavioural keys, plus this head's three own decisions."""
    missing = [key for key in CARRIED if key not in config]
    if missing:
        raise GradeTrainingError(
            f"the shipped artifact's config is missing {missing}, which this recipe carries "
            f"from it. A recipe that silently defaulted them would not be the one it claims."
        )
    recipe = {key: config[key] for key in CARRIED}
    recipe.update(
        {
            "epochs": EPOCHS,
            "patience": PATIENCE,
            "seed": 0,
            "source_dims": [head.SOURCE_WIDTH, head.SOURCE_HEIGHT],
            "augmentation": (
                "geometric only — border crop and both flips. No colour and no JPEG jitter: "
                "the colouring is what the grade is about"
            ),
            "selection": (
                f"max AP(>={HIT_TIER}) over the stopping slice, ranked by {RANK_COLUMN}, with "
                f"AUC(>={HIT_TIER}) as the fallback where the slice holds one class"
            ),
            "conditioning": "none — the picture is the input, and the head is told no batch",
            "cascade": (
                "stage two behind the render judge's p_ge4. Undefined on a row that never "
                "cleared the gate; never a pool-wide ranker"
            ),
        }
    )
    return recipe


# --------------------------------------------------------------------------- #
# The arms.
# --------------------------------------------------------------------------- #
def freeze(model, arm: str) -> dict:
    """Turn off the gradient everywhere this arm does not unfreeze, and say what it did.

    A module is unfrozen when its name is one of the arm's prefixes or sits under
    one. The empty tuple means nothing is frozen, which is the full fine-tune.
    """
    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")
    prefixes = ARMS[arm]["unfrozen"]
    trainable, total = 0, 0
    for name, parameter in model.named_parameters():
        total += parameter.numel()
        wanted = not prefixes or any(
            name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes
        )
        parameter.requires_grad_(bool(wanted))
        if wanted:
            trainable += parameter.numel()
    return {
        "arm": arm,
        "unfrozen": list(prefixes) or ["<everything>"],
        "says": ARMS[arm]["says"],
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_share": round(trainable / max(total, 1), 4),
    }


def set_train_mode(model, arm: str) -> None:
    """`train()` on the unfrozen part and `eval()` on the rest, every epoch.

    **This is the half of freezing that a `requires_grad` sweep does not do.** A
    batch-norm module in training mode keeps updating its running mean and
    variance whether or not its affine parameters take a gradient, so a "frozen"
    trunk left in `train()` adapts to the new corpus through its normalisation —
    quietly, and the arm would be measuring something nobody named.

    **Two passes, and the order is the whole of it.** `Module.eval()` applies to a
    module *and every descendant*, so a single pass that walked `named_modules()`
    eval-ing whatever did not match would eval `blocks` on its way past — taking
    `blocks.4` down with it — and then skip `blocks.4` for matching. The unfrozen
    roots are therefore put back into training mode afterwards, by name.
    """
    model.train()
    prefixes = ARMS[arm]["unfrozen"]
    if not prefixes:
        return
    for name, module in model.named_modules():
        if not name:
            continue
        if not any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            module.eval()
    named = dict(model.named_modules())
    for prefix in prefixes:
        if prefix in named:
            named[prefix].train()


# --------------------------------------------------------------------------- #
# The loader.
# --------------------------------------------------------------------------- #
class Pictures:
    """The training set over the pool's own JPEGs.

    **[`finished_train.Crops`]'s shape rather than its subclass**, for that class's
    own reason turned one step further: it is duck-typed because subclassing
    `torch.utils.data.Dataset` would mean importing torch to *define* it, and this
    module is arranged so that even `finished_train` is not imported to define
    anything. Defined at module level, though, and that is not negotiable — a
    Windows loader worker is spawned rather than forked, so the dataset is pickled
    and re-imported by name, and a class defined inside a function has no name for
    the child to find.

    It reads the JPEG directly where its shape-mate reads through
    [`renders.open_picture`], because that function answers out of the *render
    cache's* decoded sidecars and these pictures are the candidate pool's: the
    fast path would never hit, and the stat that misses it would be paid a million
    times over a band.
    """

    def __init__(self, rows: list[Unit], transform) -> None:
        self.rows = rows
        self.transform = transform
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        import random

        from PIL import Image

        row = self.rows[index]
        with Image.open(row.path) as opened:
            opened.load()
            image = opened.convert("RGB")
        # Seeded on the picture and the epoch, so a run reproduces and a picture
        # still gets a different crop every pass.
        return self.transform(image, random.Random(f"{row.name}:{self.epoch}")), row.score, index


def _loader(units: list[Unit], transform, recipe: dict, where: str):
    """The shipped judge's loader, over these rows. Sampler and weights are its."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    from fractal_wallpapers.models import finished_train

    examples = Pictures(units, transform)
    raw, mass = finished_train.weights(units)
    sampler = WeightedRandomSampler(
        torch.tensor(raw, dtype=torch.double), num_samples=len(units), replacement=True
    )
    loader = DataLoader(
        examples,
        batch_size=recipe["batch_size"],
        sampler=sampler,
        num_workers=recipe["workers"],
        pin_memory=(where == "cuda"),
        persistent_workers=False,
        drop_last=False,
    )
    return examples, loader, mass


# --------------------------------------------------------------------------- #
# The stopping rule.
# --------------------------------------------------------------------------- #
def objective(labels, probabilities) -> tuple[float, str]:
    """`(what to MINIMIZE, which rule produced it)` — AP(>=3), or AUC(>=3).

    Negated so the loop keeps one convention, and the rule that produced a number
    is returned beside it because a run that silently changed objective mid-band
    would stop on its patience and call the result a choice.

    ⚠ **The AUC fallback is unreachable and is kept anyway.**
    [`metrics.average_precision`] and [`metrics.auc`] both return `None` under
    exactly one condition and it is the same condition — one class absent at the
    boundary — so there is no slice where the first cannot be read and the second
    can. The branch is what the recipe declares and it costs nothing;
    `tests/test_gallery_grade_train.py` asserts that it is dead rather than
    leaving a reader to assume it fired.
    """
    from fractal_wallpapers.models import metrics, render_deploy

    hits = render_deploy.hits_of(labels)
    scores = render_deploy.rank_scores(probabilities)
    read = metrics.average_precision(hits, scores)
    if read is not None:
        return -float(read), f"ap_ge{HIT_TIER}"
    read = metrics.auc(hits, scores)
    if read is not None:
        return -float(read), f"auc_ge{HIT_TIER}"
    return float("inf"), "undefined"


# --------------------------------------------------------------------------- #
# The fit.
# --------------------------------------------------------------------------- #
def fit(
    arm: str,
    seed: int = 0,
    device: str = "auto",
    epochs: int | None = None,
    workers: int | None = None,
    log=say,
) -> dict:
    """Fit one arm at one seed, and write its checkpoints and its records.

    Resumable the way every trainer here is: an atomic snapshot an epoch, so a
    kill costs one epoch rather than the run, and a clean finish deletes it.
    """
    import numpy
    import torch

    from fractal_wallpapers.models import finished_train, metrics, train

    if arm not in ARMS:
        raise GradeTrainingError(f"{arm!r} is not an arm; the three are {sorted(ARMS)}")

    state, shipped = initial_state()
    recipe = recipe_from(shipped)
    recipe["seed"] = int(seed)
    if epochs is not None:
        recipe["epochs"] = int(epochs)
    if workers is not None:
        recipe["workers"] = int(workers)
    classes = int(recipe["classes"])

    units = read_population()
    split = apply_split(units)
    training = [unit for unit in units if unit.side == "train"]
    stopping = [unit for unit in units if unit.side == "stopping"]
    if not stopping:
        raise GradeTrainingError("the stopping slice is empty; there is nothing to stop on")

    where = train.device_of(device)
    train.set_seed(int(recipe["seed"]))
    log(
        f"[{HEAD}] device {where}  torch {torch.__version__}  arm {arm}  seed {recipe['seed']}  "
        f"train {len(training)} {finished_train.histogram(training)}  "
        f"stopping {len(stopping)} {finished_train.histogram(stopping)}"
    )

    model = head.build(
        num_classes=classes,
        backbone=recipe["backbone"],
        pretrained=False,
        drop_rate=recipe["drop_rate"],
        drop_path_rate=recipe["drop_path_rate"],
    )
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        named = (list(missing) + list(unexpected))[:3]
        raise GradeTrainingError(
            f"the shipped judge's weights do not fit this architecture: {len(missing)} missing "
            f"and {len(unexpected)} unexpected tensors (e.g. {named}). Same architecture is "
            f"the premise of this head, not an aspiration."
        )
    model = model.to(where)
    freezing = freeze(model, arm)
    log(
        f"[{HEAD}] arm {arm}: {freezing['trainable_parameters']:,} of "
        f"{freezing['total_parameters']:,} parameters train "
        f"({freezing['trainable_share']:.1%}) — {freezing['says']}"
    )

    data_config = head.data_config(model)
    head_parameters = [p for p in model.get_classifier().parameters() if p.requires_grad]
    head_ids = {id(parameter) for parameter in head_parameters}
    backbone_parameters = [
        p for p in model.parameters() if p.requires_grad and id(p) not in head_ids
    ]
    groups = [{"params": head_parameters, "lr": recipe["head_lr"]}]
    if backbone_parameters:
        groups.insert(0, {"params": backbone_parameters, "lr": recipe["backbone_lr"]})
    optimizer = torch.optim.AdamW(groups, weight_decay=recipe["weight_decay"])
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=recipe["epochs"])

    target = tuple(recipe["target_dims"])
    train_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=True,
        border_crop=recipe["border_crop"],
        jpeg=None,
        brightness=0.0,
        contrast=0.0,
        target=target,
    )
    deploy_transform = head.Transform(
        data_config["mean"],
        data_config["std"],
        data_config["interpolation"],
        train=False,
        target=target,
    )
    examples, loader, mass = _loader(training, train_transform, recipe, where)

    stopping_paths = [unit.path for unit in stopping]
    stopping_labels = numpy.array([unit.score for unit in stopping])
    stopping_batches = numpy.array([unit.batch for unit in stopping])
    cutpoint = min(int(recipe["selection_cutpoint"]), classes) - 2

    directory = run_dir(arm, seed)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        lock = train.claim(directory)
    except RuntimeError as taken:
        raise GradeTrainingError(str(taken)) from None
    resume = directory / "resume.pt"

    best_metric, best_state, best_epoch, best_rule, history = float("inf"), None, -1, "", []
    segments, start = [], 0
    if resume.is_file():
        saved = torch.load(resume, map_location="cpu", weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        schedule.load_state_dict(saved["schedule"])
        best_metric, best_epoch = saved["best_metric"], saved["best_epoch"]
        best_state, history = saved["best_state"], saved["history"]
        best_rule = saved.get("best_rule", "")
        segments = list(saved.get("segments") or [])
        start = saved["epoch"] + 1
        torch.set_rng_state(saved["torch_rng"].cpu().to(torch.uint8))
        if where == "cuda" and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(
                [state_.cpu().to(torch.uint8) for state_ in saved["cuda_rng"]]
            )
        numpy.random.set_state(saved["numpy_rng"])
        log(f"[{HEAD}] resumed at epoch {start} (best {best_metric:.4f} at epoch {best_epoch})")

    began = time.time()
    stopped_early: dict | None = None

    def launched(through: int) -> list[dict]:
        if through < start:
            return list(segments)
        return [
            *segments,
            {
                "from_epoch": start,
                "through_epoch": through,
                "wall_seconds": round(time.time() - began, 1),
            },
        ]

    for epoch in range(start, int(recipe["epochs"])):
        examples.set_epoch(epoch)
        set_train_mode(model, arm)
        clock, running, seen = time.time(), 0.0, 0
        for crops, labels, _index in loader:
            crops = crops.to(where, non_blocking=True)
            labels = labels.to(where)
            optimizer.zero_grad(set_to_none=True)
            loss = head.loss_of(model(crops), labels, num_classes=classes)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], recipe["grad_clip"]
            )
            optimizer.step()
            running += loss.item() * crops.size(0)
            seen += crops.size(0)
        schedule.step()

        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise GradeTrainingError(f"the head went non-finite at epoch {epoch}")

        probabilities = train.score(model, stopping_paths, deploy_transform, where, classes, recipe)
        value, rule = objective(stopping_labels, probabilities)
        record = {
            "epoch": epoch,
            "loss": running / max(seen, 1),
            "seconds": round(time.time() - clock, 1),
            "selection_loss": value,
            "selection_rule": rule,
            f"stopping_ap_ge{cutpoint + 2}": metrics.average_precision(
                (stopping_labels >= cutpoint + 2).astype(int), probabilities[:, cutpoint]
            ),
        }
        for index in range(classes - 1):
            record[f"stopping_auc_ge{index + 2}"] = metrics.auc(
                (stopping_labels >= index + 2).astype(int), probabilities[:, index]
            )
            record[f"stopping_mean_p_ge{index + 2}"] = float(probabilities[:, index].mean())
        record["stopping_spearman"] = metrics.spearman(
            stopping_labels, head.rank_score(probabilities)
        )
        # Per batch, reported and never selected on: the epoch is chosen on the
        # pooled slice, and these three columns are how a reader sees whether the
        # stratification bought anything.
        for name in sorted(set(stopping_batches.tolist())):
            mask = stopping_batches == name
            if mask.any():
                record[f"stopping_ap_ge{cutpoint + 2}_{name}"] = metrics.average_precision(
                    (stopping_labels[mask] >= cutpoint + 2).astype(int),
                    probabilities[mask, cutpoint],
                )
        history.append(record)
        log(
            f"[{HEAD}] epoch {epoch:2d}  loss {record['loss']:.4f}  "
            f"AP>={cutpoint + 2} {train.shown(record[f'stopping_ap_ge{cutpoint + 2}'])}  "
            + "  ".join(
                f"AUC>={index + 2} {train.shown(record[f'stopping_auc_ge{index + 2}'])}"
                for index in range(classes - 1)
            )
            + f"  rho {train.shown(record['stopping_spearman'])}  ({record['seconds']}s)"
        )

        if value < best_metric:
            best_metric, best_epoch, best_rule = value, epoch, rule
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        temporary = directory / "resume.pt.partial"
        torch.save(
            {
                "epoch": epoch,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "schedule": schedule.state_dict(),
                "best_metric": best_metric,
                "best_epoch": best_epoch,
                "best_rule": best_rule,
                "best_state": best_state,
                "history": history,
                "segments": launched(epoch),
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if where == "cuda" else None,
                "numpy_rng": numpy.random.get_state(),
            },
            temporary,
        )
        temporary.replace(resume)

        if epoch - best_epoch >= int(recipe["patience"]):
            stopped_early = {
                "at_epoch": epoch,
                "of_epochs": int(recipe["epochs"]),
                "patience": int(recipe["patience"]),
                "best_epoch": best_epoch,
            }
            log(
                f"[{HEAD}] stopping at epoch {epoch}: no improvement in "
                f"{recipe['patience']} epochs (best {best_epoch})"
            )
            break

    lock.unlink(missing_ok=True)
    last_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    if best_state is None:
        best_state = last_state

    config = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed),
        "arm": arm,
        **recipe,
        "initialised_from": {
            "artifact": str(SOURCE).replace("\\", "/"),
            "run": shipped.get("run"),
            "tag": "weights-v6",
            "says": "a COPY. Never a shared trunk — a moved trunk is a judge flip",
        },
        "freezing": freezing,
        "stopped_early": stopped_early,
        "best_epoch": best_epoch,
        "best_selection_rule": best_rule,
        "mean": list(data_config["mean"]),
        "std": list(data_config["std"]),
        "interpolation": data_config["interpolation"],
        "inherited": INHERITANCE,
        # The split's shape and never its per-row arrays: this file is tracked,
        # and three thousand entries naming every row would be a record nobody
        # reads carried in git forever. The arrays live in `split.json`, under
        # the regenerable tree, which is where the fit reads them from.
        "split": {key: value for key, value in split.items() if not key.endswith("_of_row")},
        "precision": "fp32",
    }
    torch.save({"state_dict": best_state, "config": config}, directory / "best.pt")
    torch.save({"state_dict": last_state, "config": config}, directory / "last.pt")
    if resume.is_file():
        resume.unlink()

    # The chosen epoch's own read of the stopping slice, one row at a time with
    # its whole join — so the band's table can be rebuilt without the GPU.
    model.load_state_dict({key: value.to(where) for key, value in best_state.items()})
    chosen = train.score(model, stopping_paths, deploy_transform, where, classes, recipe)
    _write_scores(directory, arm, seed, stopping, chosen, classes)

    read = _read_of(stopping_labels, chosen, cutpoint, classes)
    record = {
        "schema": SCHEMA,
        "head": HEAD,
        "run": run_name(arm, seed),
        "arm": arm,
        "seed": int(seed),
        "device": where,
        "wall_seconds": round(time.time() - began, 1),
        "segments": launched(history[-1]["epoch"] if history else int(recipe["epochs"]) - 1),
        "best_epoch": best_epoch,
        "best_selection_objective": best_metric,
        "best_selection_rule": best_rule,
        "stopped_early": stopped_early,
        "selection_metric": (
            f"AP(>={HIT_TIER}) over the stopping slice, maximized "
            f"(recorded negated, because the loop minimizes)"
        ),
        "freezing": freezing,
        "held_out": read,
        "held_out_is": (
            "the stopping slice. It is the shipped recipe's only holdout and the epoch was "
            "chosen on it, so every number here is optimistic by one early stop, and the "
            "store is not eval-eligible — this is a within-store reading and nothing more"
        ),
        "pictures": {"train": len(training), "stopping": len(stopping), "total": len(units)},
        "class_counts": {
            "train": finished_train.histogram(training),
            "stopping": finished_train.histogram(stopping),
        },
        "sampled_mass": mass,
        "history": history,
        "checkpoints": {
            "best": tracked_name(directory / "best.pt"),
            "last": tracked_name(directory / "last.pt"),
        },
    }
    (directory / "config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (directory / "metrics.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def fit_band(arms=None, seeds=SEEDS, device: str = "auto", log=say, **rest) -> dict:
    """Fit every run of the grid that is not already on disk, **one at a time**.

    Sequential and not a knob, for `models/render/README.md`'s reason: this box's
    commit charge cannot afford two trainers, and the failure it produces —
    `[WinError 1455] The paging file is too small`, out of a CUDA DLL load — looks
    like a machine fault rather than like scheduling.

    A run whose `metrics.json` is already there is skipped rather than re-fitted,
    so a killed band is resumed by re-launching it.
    """
    arms = tuple(arms or ARMS)
    done, ran = [], []
    for arm in arms:
        for seed in seeds:
            if (run_dir(arm, seed) / "metrics.json").is_file():
                done.append(run_name(arm, seed))
                log(f"[{HEAD}] {run_name(arm, seed)} is already fitted — skipping")
                continue
            record = fit(arm=arm, seed=seed, device=device, log=log, **rest)
            ran.append(record["run"])
    return {"fitted": ran, "already_there": done, "band": band(arms, seeds)}


def _read_of(labels, probabilities, cutpoint: int, classes: int) -> dict:
    """Every boundary's AP and AUC over one slice, plus the order statistic."""
    import numpy

    from fractal_wallpapers.models import metrics

    out: dict = {"rows": int(len(labels))}
    for index in range(classes - 1):
        hits = (numpy.asarray(labels) >= index + 2).astype(int)
        out[f"ap_ge{index + 2}"] = metrics.average_precision(hits, probabilities[:, index])
        out[f"auc_ge{index + 2}"] = metrics.auc(hits, probabilities[:, index])
    out["spearman"] = metrics.spearman(labels, head.rank_score(probabilities))
    out["cutpoint"] = cutpoint + 2
    return out


def _write_scores(directory: Path, arm: str, seed: int, units, probabilities, classes: int) -> None:
    """The chosen epoch's read of the stopping slice, a row carrying its join."""
    import numpy

    path = directory / "scores.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for unit, probability in zip(units, probabilities, strict=True):
            row = {
                "schema": SCHEMA,
                "head": HEAD,
                "run": run_name(arm, seed),
                "key": unit.key,
                "grade": unit.score,
                "batch": unit.batch,
                "place": unit.place,
                "partition": unit.partition,
                "mode": unit.mode,
                "leveled": unit.leveled,
                "seated": unit.seated,
                "judge_label_p_ge4": unit.label_p_ge4,
                "judge_candidate_p_ge4": unit.candidate_p_ge4,
            }
            for index in range(classes - 1):
                row[f"p_ge{index + 2}"] = float(probability[index])
            row["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_run(arm: str, seed: int) -> dict:
    path = run_dir(arm, seed) / "metrics.json"
    if not path.is_file():
        raise GradeTrainingError(f"{path} is not there — that run has not been fitted")
    return json.loads(path.read_text(encoding="utf-8"))


def baselines() -> dict:
    """The shipped judge's own columns over the stopping slice, at both geometries.

    **Recomputed on this band's own rows rather than quoted from anywhere.** The
    numbers on the store's README are over all thousand rows; these are over the
    two hundred the arms are read on, and a table that mixed the two would be
    comparing an arm against a different population's baseline.

    `candidate_p_ge4` is the one a seating actually walks and is therefore the
    number to beat. `label_p_ge4` is the same judge on the picture the verdict was
    cast on, and it is here because it is the *easier* baseline — it reads the
    exact pixels the person saw — so an arm that fails to beat it has not merely
    lost to the deployment column.
    """
    import numpy

    from fractal_wallpapers.models import metrics

    units = read_population()
    apply_split(units)
    stopping = [unit for unit in units if unit.side == "stopping"]
    labels = numpy.array([unit.score for unit in stopping])
    out: dict = {"rows": len(stopping), "base_rates": {}}
    for boundary in (2, 3, 4):
        out["base_rates"][f"ge{boundary}"] = round(float((labels >= boundary).mean()), 4)
    for column in ("candidate_p_ge3", "candidate_p_ge4", "label_p_ge3", "label_p_ge4"):
        values = [getattr(unit, column) for unit in stopping]
        present = [value is not None for value in values]
        if not all(present):
            out[column] = {"rows_carrying_it": sum(present), "of": len(stopping), "read": None}
            continue
        scores = numpy.array(values, dtype=float)
        read: dict = {"rows_carrying_it": len(scores)}
        for boundary in (2, 3, 4):
            hits = (labels >= boundary).astype(int)
            read[f"ap_ge{boundary}"] = metrics.average_precision(hits, scores)
            read[f"auc_ge{boundary}"] = metrics.auc(hits, scores)
        read["spearman"] = metrics.spearman(labels, scores)
        out[column] = read
    return out


def band(arms=None, seeds=SEEDS) -> dict:
    """Every run that has been fitted, the baseline it is read beside, and the pick.

    **The pick is by stopping-slice AP**, which is the rule the epoch was chosen
    under: one statistic decides the epoch inside a run and the run inside the
    band, so nothing is selected on a number nothing was stopped on.
    """
    arms = tuple(arms or ARMS)
    rows = []
    for arm in arms:
        for seed in seeds:
            try:
                said = read_run(arm, seed)
            except GradeTrainingError:
                continue
            rows.append(
                {
                    "arm": arm,
                    "seed": int(seed),
                    "run": said["run"],
                    "best_epoch": said["best_epoch"],
                    "stopping_ap": -float(said["best_selection_objective"]),
                    "rule": said.get("best_selection_rule"),
                    "trainable_share": said["freezing"]["trainable_share"],
                    "wall_seconds": said["wall_seconds"],
                    "held_out": said["held_out"],
                }
            )
    if not rows:
        raise GradeTrainingError("no run in this band has been fitted")
    per_arm: dict = {}
    for row in rows:
        per_arm.setdefault(row["arm"], []).append(row["stopping_ap"])
    best = max(rows, key=lambda row: row["stopping_ap"])
    return {
        "schema": SCHEMA,
        "head": HEAD,
        "arms": {
            arm: {
                "seeds": len(values),
                "mean_stopping_ap": round(sum(values) / len(values), 4),
                "best_stopping_ap": round(max(values), 4),
                "spread": round(max(values) - min(values), 4),
            }
            for arm, values in sorted(per_arm.items())
        },
        "pick": {"arm": best["arm"], "seed": best["seed"], "run": best["run"]},
        "pick_rule": "the highest stopping-slice AP, which is the rule the epoch was chosen on",
        "baseline": _baselines_or_reason(),
        "baseline_is": (
            "the shipped judge's own columns over these same rows. `candidate_p_ge4` is the "
            "one a seating walks and is the number to beat; `label_p_ge4` is the same judge "
            "on the picture the verdict was cast on, which is the easier baseline"
        ),
        "runs": sorted(rows, key=lambda row: (-row["stopping_ap"], row["run"])),
    }


def _baselines_or_reason() -> dict:
    """The baseline, or why it could not be read. A band is still worth writing
    without it, and a missing block that raised would take the table with it."""
    try:
        return baselines()
    except (GradeTrainingError, OSError) as unreadable:
        return {"unreadable": str(unreadable)}


def write_band(arms=None, seeds=SEEDS) -> tuple[Path, dict]:
    record = band(arms, seeds)
    path = band_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path, record


__all__ = [
    "ARMS",
    "CARRIED",
    "EPOCHS",
    "HEAD",
    "HOLDOUT_SHARE",
    "INHERITANCE",
    "PATIENCE",
    "SCHEMA",
    "SEEDS",
    "SOURCE",
    "SPLIT_SEED",
    "GradeTrainingError",
    "Unit",
    "band",
    "baselines",
    "fit",
    "freeze",
    "head_dir",
    "initial_state",
    "objective",
    "population",
    "read_population",
    "read_run",
    "read_split",
    "recipe_from",
    "root",
    "run_dir",
    "run_name",
    "set_train_mode",
    "sides_for",
    "write_band",
    "write_population",
    "write_split",
]
