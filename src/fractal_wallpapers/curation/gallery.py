"""The gallery pass: one global selection over the whole pool, for what ships.

Curation has two phases and this is the second. A **run** is the pool phase — it
harvests, colorizes, records every candidate and every verdict on it, and keeps a
small `diagnostic` release for Matt's eye. It decides nothing about the
collection, because one night's few hundred attempts are the wrong population to
decide a collection out of. The **gallery pass** is the other half: one command
over everything the pool holds, choosing N wallpapers that are individually good
and collectively unalike.

It is a command and **not a run type**. There is no ledger binding, no pacing
clock and no harvest state, because none of those are things a selection over an
accumulated pool has. What it does have is an **identity**: each invocation is a
pass with its own id, its own record beside the runs rather than among them, and
its own slice of the pool's decision store. A new pass **supersedes** the
previous gallery; nothing is deleted, and the two records sit side by side saying
what each one chose out of what.

## The seven steps

```text
1  slots per partition   release_mix over a POOL-WIDE denominator
2  head split            per partition, by --strange-share
3  the distance          the neutral-render embeddings, refused unless whole
4  the locations         quality-weighted farthest point under a hard radius
5  the attempts          m locations near each chosen point, judged small
6  the seats             floors per head, then P(>=4); unfilled beats padded
7  the pictures          2560x1440 ss4 for the winners, and only for them
```

## Why farthest point and not clustering

A slot is a place in the finished collection, so the question at step 4 is *what
should the next wallpaper be least like*. K-means answers a different question —
it follows density, and this pool's density is a record of where the walk spent
its budget rather than of where the good pictures are. A neighborhood somebody
visited a thousand times would be handed a thousand times the slots.

So: the first pick of a partition is its strongest location by the location
head's `P(>=4)`, and every pick after it maximizes `distance x quality^gamma`
against the set already chosen, where `distance` is cosine distance to the
*nearest* chosen point. [`QUALITY_WEIGHT`] is `gamma` and it is a knob. Under all
of it is a **hard radius**: nothing within [`RADIUS`] of a chosen point may be
chosen, whatever its quality. The weight decides who wins among the eligible; the
radius decides who is eligible at all, and it is the one of the two that a person
can read off a sheet.

Both numbers are by eye, and the instrument that calibrates them is the **retro
table** every pass prints: the nearest chosen pairs, per partition and overall,
with their distances. A radius that is too tight shows up there as a table full
of pairs a person would call the same picture.

## The attempt leg, and why the pass has one at all

A pass that could only seat what the pool already held would be supply-bound on
day one — 1,050 candidates over 475 locations against 24,779 admitted locations,
so most of what the embedding can reach has never been coloured at all. Attempts
are cheap (about 2.5 s) and full-size renders are not (about 25 s, twice that
where the operator acts), so the pass spends the cheap thing to make the
expensive one worth spending: around each chosen point it takes the top `m`
locations by `P(>=4)` and tries each of them under `smooth` palette anchors and
`strange` distinct modes.

Those attempts are **pool rows like any other**, stamped with the pass id. The
pool grows by every one of them, and the next pass — or the next hand-labelling
batch — reads them the same way it reads a run's. What is *not* kept is the
palette head's working: 32 candidate maps are rendered to choose one, and the 31
that lost are deleted after the verdict, which keeps the pick and the scores and
throws away the pictures nobody will look at.

Every chosen point gets both heads' attempts, whichever head owns its slot,
because a mode draw is not free to repeat and the two heads' rosters are
disjoint. The slot's own head is what decides which of them may **fill** it: the
two judges' probabilities live on scales that were calibrated separately and a
list holding both is a list ordered by whichever scale runs higher.

## Unfilled beats padded

A slot with nothing above its head's floor is **output empty, with the reason
named**. That is the whole point of the floors acting here: an empty slot is a
statement about where the pool is thin, and it is the signal for where to label
or walk next. A padded slot is the same statement with the evidence removed.

Both measured floors act ([`floors.gallery_floor`]) — the strange head's 0.685
and the smooth head's 0.385 — which is not what happens at a run's release, where
only the strange one gates. The two decisions are different: a run's is about how
much of its own night is worth looking at, and this one is about what the
collection ships.

## What the pass leaves in the history, and what it leaves beside it

Everything a pass writes into `data/` scales with `n`; nothing does with the
attempts. The pass record and the winners' release rows are tracked; the attempt
rows are pool rows and go to [`curation.gallery_store`], under `artifacts/` with
a tracked manifest and an archive copy. [`write_records`] is where the split is
taken and says why, and [`tracked_bytes`] measures the result on every pass so
the claim stays checked rather than remembered.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.curation import budget as budget_module
from fractal_wallpapers.curation import (
    colorize,
    durability,
    embeddings,
    floors,
    gallery_store,
    intake,
    records,
    release,
    selection,
)
from fractal_wallpapers.curation import run as run_module
from fractal_wallpapers.paths import tracked_name
from fractal_wallpapers.supply import apportion
from fractal_wallpapers.supply import partitions as partition_module

#: The schema every pass record carries.
SCHEMA = 1

#: What a pass is called when the caller did not say: the next unused ordinal.
#: A pass is superseded rather than overwritten, so the names have to accumulate
#: — and they have to be guessable, because the pass id is what stamps every
#: attempt row it adds to the pool.
PASS_PREFIX = "gallery"

#: How many wallpapers a pass chooses when the caller did not say. Fifty, which
#: is the first size Matt asked for and a size a person can still hand-review
#: end to end; the design assumes a hand pass over the judges' top few hundred at
#: this N and expects the judges plus the diversity rule to carry it at a
#: thousand.
DEFAULT_N = 50

#: The **hard radius**, in cosine distance over the neutral-render embedding.
#: Nothing within this of an already-chosen point may be chosen.
#:
#: 0.07, from the first calibration read (`curate neighbours`, 2026-08-22):
#: nearest-neighbour distances have a median of 0.024 and an unrelated pair sits
#: at 0.275, and by eye 0.04 apart is the same kind of thing while 0.27 is the
#: same family in a different geometry. The design said to start between 0.05 and
#: 0.10 and let the retro table decide; this is the middle of that, and the table
#: is printed every pass so the decision stays available.
RADIUS = 0.07

#: `gamma` in `gain = distance x quality^gamma` — how much the farthest-point
#: draw is allowed to prefer a strong location over a distant one.
#:
#: **One**, which makes the gain a plain product: a location half as far but
#: twice as good is worth the same. Zero would be pure farthest point, which
#: spends slots on the most isolated locations in the pool whatever the judge
#: says about them; large gamma collapses to "best first" and leaves the spread
#: entirely to the radius. The product is the reading that keeps both halves
#: acting, and the radius is what stops the quality half from clustering.
QUALITY_WEIGHT = 1.0

#: `(m, smooth, strange)` — how many locations near a chosen point are tried, and
#: how many attempts each of them gets from each head. 3 locations x (2 smooth
#: palette anchors + 6 strange modes) = 24 attempts a slot, about a minute.
ATTEMPTS = (3, 2, 6)

#: The seed every draw in a pass is taken under: the palette anchors, and the
#: modes each location is tried in. Recorded on the pass record, so a pass is
#: reproducible from it alone.
DEFAULT_SEED = 0

#: What a winner is rendered at. The run's geometry, read from there rather than
#: restated: a gallery wallpaper and a diagnostic one are the same picture at the
#: same size, and two spellings of that is how they come to differ.
RESOLUTION = run_module.RELEASE_RESOLUTION
SUPERSAMPLE = run_module.RELEASE_SUPERSAMPLE

#: How many nearest pairs the retro table lists, per partition and overall.
RETRO_PAIRS = 8

#: How many refused-by-radius runners-up the second contact sheet shows per slot.
RUNNERS_UP = 3


class PassRefused(RuntimeError):
    """A gallery pass cannot start, and guessing would spend a full-size render."""


# --------------------------------------------------------------------------- #
# Where a pass lives.
# --------------------------------------------------------------------------- #
def pass_dir(pass_id: str) -> Path:
    """Where a pass's pictures and caches live. Ignored, and regenerable.

    Deliberately the **run tree** and not one of its own. The pass's attempts are
    pool rows, and `curation.rescore` finds any pool row's candidate render at
    `runs/<run>/pictures/<candidate>.jpg` off the row's own `run` field. A pass
    that stored its pictures somewhere else would be a pass whose rows the next
    re-score refuses to read.
    """
    return run_module.run_dir(pass_id)


def record_dir() -> Path:
    """Where the pass records live: beside the runs, never among them.

    `records.write_run` and `runs.jsonl` are keyed by run and read by the release
    reservation, the run listing and the sheet. A pass is not a run — it books no
    clock, it measures no release rate a later night should derive anything from —
    so it keeps its own directory rather than writing a record every one of those
    readers would have to learn to skip.
    """
    return records.root() / "gallery"


#: What a pass's own summary is called inside its directory. Everything about the
#: pass that is not per-slot: the knobs, the plan, the retro table, the timings.
RECORD_NAME = "pass.json"


def pass_record_dir(pass_id: str) -> Path:
    """One pass's tracked directory: its summary, its slots, its store's manifest."""
    return record_dir() / str(pass_id)


def record_path(pass_id: str) -> Path:
    return pass_record_dir(pass_id) / RECORD_NAME


def slots_path(pass_id: str, partition: str | None) -> Path:
    """Where one partition's slot rows go. The same file axis the pool splits on.

    A slot row carries the chosen point, its embedding index, the neighbourhood the
    attempts were spent on, the fill arithmetic and the seat, and it runs about a
    kilobyte. Fifty of them fit in one file and five hundred do not: at N=500 a
    single-file pass record lands around 1.3 MiB against the 1 MiB history guard,
    which is the same wall the decision stores hit and it is answered the same way.
    Partition, because that is the axis a slot is allocated on and therefore the
    axis the rows already arrive in blocks of.
    """
    return pass_record_dir(pass_id) / records.partition_file(partition)


def passes() -> list[str]:
    """Every pass on record, oldest ordinal first."""
    directory = record_dir()
    if not directory.is_dir():
        return []
    return sorted(
        (entry.name for entry in directory.iterdir() if (entry / RECORD_NAME).is_file()),
        key=_ordinal,
    )


def _ordinal(name: str) -> tuple:
    """Sort key over pass names: the numbered ones in order, anything else last."""
    if name.startswith(PASS_PREFIX) and name[len(PASS_PREFIX) :].isdigit():
        return (0, int(name[len(PASS_PREFIX) :]), name)
    return (1, 0, name)


def next_pass_id() -> str:
    """The next unused ordinal name. Never reuses one, even a deleted one's."""
    taken = {
        int(name[len(PASS_PREFIX) :])
        for name in passes()
        if name.startswith(PASS_PREFIX) and name[len(PASS_PREFIX) :].isdigit()
    }
    return f"{PASS_PREFIX}{(max(taken) + 1) if taken else 1}"


# --------------------------------------------------------------------------- #
# Step 3, first: the distance, and the refusal that comes before anything else.
# --------------------------------------------------------------------------- #
def load_embeddings(log=print):
    """`(rows, matrix, verdict)` — the store, refused unless it is whole.

    The check is `curate embeddings check` and it is run here rather than left to
    the operator, because everything downstream of it is expensive: a pass over a
    store that lost rows would choose its locations out of a population smaller
    than the one on record and would say nothing about it. `grown` is fine — that
    is what a store looks like between an embed and the next save.
    """
    verdict = durability.check(embeddings.store(), log=lambda _line: None)
    if verdict.get("verdict") in {"short", "missing", "unrecorded"}:
        raise PassRefused(
            f"the neutral-render embedding store is {verdict['verdict']}: "
            f"{verdict.get('rows', 0):,} rows live against {verdict.get('recorded')} on the "
            f"manifest. The pass picks its locations by how far apart they look, so a short "
            f"store is a pass silently unable to choose whatever it is missing. Run "
            f"`fractal-wallpapers curate embeddings restore`, or `curate embed` to make the "
            f"vectors again."
        )
    rows, matrix = embeddings.load()
    if not rows:
        raise PassRefused(
            "the embedding store holds no row, so there is no distance to select over. "
            "Run `fractal-wallpapers curate embed`."
        )
    log(f"[embed] {len(rows):,} embedded location(s), store {verdict['verdict']}")
    return rows, matrix, verdict


def colorize_row(row: dict) -> dict:
    """An embedding-store row spelled the way [`colorize.attempt`] reads one.

    THE row-shape adapter on the attempt side, and it exists because the pass
    feeds the colorizer out of a store no run has ever fed it out of. A run's rows
    come from [`intake.ranked`], which stamps `_ledger` on each one as it reads the
    walk ledger and calls the location head's reading `score`; an embedding row
    carries the same two facts already resolved, under `ledger` and
    `location_p_ge3`.

    Two spellings that do not line up produce no error and no warning — every
    attempt the pass makes is simply recorded with `ledger: null` and
    `location_score: null`, which is a pool row nothing can say where it came from
    or how good its place was. gallery1's first 1,120 attempts were written that
    way and had to be repaired by hand.
    """
    return {**row, "_ledger": row.get("ledger"), "score": row.get("location_p_ge3")}


def quality_of(row: dict, scores: dict) -> float:
    """A location's quality: the location head's `P(>=4)`, joined off the sidecar.

    `P(>=4)` and not the `P(>=3)` the embedding row carries, because the question
    a gallery slot asks is *is this worth shipping* rather than *is this not
    junk*, and the head emits both. A location the sidecar has no fourth-class
    reading for scores zero here rather than falling back to the third: a fallback
    would put it on a different scale from every other location in the same sort.
    """
    read = scores.get(str(row["key"]))
    if not read:
        return 0.0
    value = read.get("p_ge4")
    return 0.0 if value is None else float(value)


# --------------------------------------------------------------------------- #
# Steps 1 and 2: how many slots, where, and for which head.
# --------------------------------------------------------------------------- #
def population(rows: list[dict]) -> dict:
    """`{partition: admitted locations}` — the pool-wide denominator.

    Every embedded location, which is every location over the junk floor. This is
    what the slot allocation's caps and guarantee are re-derived over, and it is
    the whole point of the pass: a run's denominator is one binding's offer and
    this one is everything anybody has ever admitted.
    """
    out: dict[str, int] = {}
    for row in rows:
        name = str(row["partition"])
        out[name] = out.get(name, 0) + 1
    return dict(sorted(out.items()))


def slots_for(counts: dict, n: int, scores: dict, rows: list[dict]) -> tuple[dict, dict, list]:
    """`(slots, caps, guaranteed)` — `n` slots over the release mix, pool-wide.

    The caps are [`floors.release_cap`] over the pool-wide passing count, which
    over tens of thousands of admitted locations is a number in the thousands and
    therefore binds nothing. It is computed anyway, and reported, because the rule
    is the same rule — *show me one only if there were four to choose from* — and
    a pass that skipped it would be a pass nobody could compare to a run.

    The guarantee is [`intake.guaranteed`]'s trigger over the same population:
    every partition holding at least one location above the good floor is owed a
    slot, so a small N cannot structurally zero the low-ratio families.
    """
    caps = {name: floors.release_cap(count) for name, count in counts.items()}
    good: dict[str, int] = {}
    for row in rows:
        if floors.passes_good_floor((scores.get(str(row["key"])) or {}).get("p_ge3")):
            name = str(row["partition"])
            good[name] = good.get(name, 0) + 1
    guaranteed = sorted(name for name, count in good.items() if count)
    try:
        return intake.slots(counts, n, guaranteed, caps=caps), caps, guaranteed
    except apportion.SlotGuaranteeOverflow as overflow:
        # Refused rather than pro-rated, which is `apportion`'s rule and the right
        # one here: a gallery smaller than the number of families that have
        # something worth shipping is not a gallery with a thin partition in it,
        # it is a gallery that has to decide which families it leaves out — and
        # that is Matt's call, not an apportionment's.
        raise PassRefused(
            f"{len(guaranteed)} partition(s) hold a location above the good floor and are "
            f"each owed a slot, against the {n} this pass was asked for. -n has to be at "
            f"least {len(guaranteed)} for every family with something worth shipping to "
            f"appear in the gallery. ({overflow})"
        ) from overflow


def head_split(count: int, strange_share: float) -> dict:
    """`{head: slots}` for one partition. The run's arithmetic, per partition.

    Through [`budget_module.head_slots`] so the two phases round the share the
    same way. Per partition rather than over the whole pass, because §2 of the
    design splits it there: a partition with one slot gives it to the strange
    judge at a share above a half, and rounding the whole N first would let the
    remainder fall wherever the partition order happened to put it.
    """
    return budget_module.head_slots(count, strange_share)


def head_order(split: dict) -> list[str]:
    """Which head each of a partition's picks belongs to, in pick order.

    Largest-deficit over the two heads' slot counts, which is the rule this
    project already uses to lay a share out over whole positions — so every
    *prefix* of a partition's picks holds both heads near their share. It matters
    because the picks are quality-ordered: dealing the strange head every pick
    before the smooth head's first would hand one judge the whole top of the
    partition.
    """
    return apportion.sequence_by_deficit(
        {head: int(split.get(head, 0)) for head in budget_module.HEADS}, sum(split.values())
    )


# --------------------------------------------------------------------------- #
# Step 4: quality-weighted farthest point, under a hard radius.
# --------------------------------------------------------------------------- #
@dataclass
class Choice:
    """One chosen point, and the arithmetic that chose it."""

    index: int
    key: str
    partition: str
    quality: float
    #: Cosine distance to the nearest already-chosen point of this partition.
    #: `None` on the first pick, which had nothing to be far from.
    distance: float | None
    gain: float | None


def choose(indices, matrix, quality, k: int, radius: float, weight: float) -> tuple[list, dict]:
    """`(picks, tally)` — up to `k` of `indices`, farthest-point under the radius.

    `indices` are positions in `matrix`, whose rows are unit vectors, so cosine
    distance is `1 - dot`. The first pick is the strongest by `quality`; each
    pick after it maximizes `distance x quality^weight` over everything still
    outside `radius` of the chosen set.

    Fewer than `k` come back when the radius runs the partition out of eligible
    points, and that is a real answer rather than a failure: it means the
    partition's admitted locations do not hold `k` visibly different places, which
    is exactly the fact an unfilled slot is there to report.
    """
    import numpy

    order = list(indices)
    if not order or k <= 0:
        return [], {"eligible": len(order), "chosen": 0, "refused_by_radius": 0}
    block = matrix[order]
    scores = numpy.array([max(0.0, float(quality[i])) for i in order], dtype=numpy.float64)
    weighted = scores ** float(weight)
    # Every point starts infinitely far from a chosen set that is still empty, so
    # the first pick is decided by quality alone — which is what the design says
    # it is, rather than by whatever the arithmetic would do with a zero.
    nearest = numpy.full(len(order), numpy.inf)
    live = numpy.ones(len(order), dtype=bool)
    picks: list[Choice] = []
    while len(picks) < k:
        if not live.any():
            break
        if not picks:
            gains = numpy.where(live, weighted, -numpy.inf)
        else:
            gains = numpy.where(live, nearest * weighted, -numpy.inf)
        best = int(numpy.argmax(gains))
        if not numpy.isfinite(gains[best]):
            break
        picks.append(
            Choice(
                index=order[best],
                key="",
                partition="",
                quality=float(scores[best]),
                distance=None if not len(picks) else float(nearest[best]),
                gain=None if not len(picks) else float(gains[best]),
            )
        )
        distances = 1.0 - (block @ block[best])
        nearest = numpy.minimum(nearest, distances)
        live &= distances >= float(radius)
    return picks, {
        "eligible": len(order),
        "chosen": len(picks),
        # What the radius cost: every admitted location of this partition that a
        # chosen point pulled inside the radius, including the chosen points
        # themselves, which is why it is counted as a refusal of the *rest*.
        "refused_by_radius": int((~live).sum()) - len(picks),
    }


def retro_table(picks: list, matrix, pairs: int = RETRO_PAIRS) -> list[dict]:
    """The nearest pairs among a set of chosen points, closest first.

    THE calibration instrument. The radius and the weight are by eye, and the
    only way to see whether they were set right is to look at the two chosen
    wallpapers that ended up nearest each other and ask whether they are two
    pictures or one.
    """

    if len(picks) < 2:
        return []
    block = matrix[[pick.index for pick in picks]]
    distances = 1.0 - (block @ block.T)
    out = []
    for i in range(len(picks)):
        for j in range(i + 1, len(picks)):
            out.append(
                {
                    "cosine_distance": round(float(distances[i, j]), 4),
                    "a": {"key": picks[i].key, "partition": picks[i].partition},
                    "b": {"key": picks[j].key, "partition": picks[j].partition},
                }
            )
    out.sort(key=lambda cell: (cell["cosine_distance"], cell["a"]["key"], cell["b"]["key"]))
    return out[:pairs]


def neighbourhood(pick: int, indices, matrix, quality, m: int, radius: float) -> list[int]:
    """The `m` locations a chosen point's attempts are spent on.

    The point itself, then the strongest of everything within `radius` of it by
    `quality`. The point is **kept whatever its quality**: it is the location the
    selection chose, and a neighbourhood that could drop it would be spending the
    slot's attempts somewhere the pass never picked.
    """
    import numpy

    order = [i for i in indices if i != pick]
    if not order or m <= 1:
        return [pick]
    distances = 1.0 - (matrix[order] @ matrix[pick])
    near = [order[i] for i in numpy.nonzero(distances < float(radius))[0]]
    near.sort(key=lambda i: (-float(quality[i]), i))
    return [pick, *near[: max(0, m - 1)]]


# --------------------------------------------------------------------------- #
# The slots themselves.
# --------------------------------------------------------------------------- #
@dataclass
class Slot:
    """One place in the finished gallery, and everything decided about it."""

    id: str
    partition: str
    head: str
    #: The chosen point: the location the farthest-point draw picked.
    point: str
    #: Its row in the embedding store, which is the only thing that makes the
    #: distance re-derivable from the record. The key names the location and the
    #: index names the vector, and a reader holding one of the two would have to
    #: re-derive the other against a store that has since grown.
    point_index: int = -1
    #: The `m` locations this slot's attempts are spent on, the point first.
    locations: list = field(default_factory=list)
    quality: float = 0.0
    #: Cosine distance to the nearest point already chosen in this partition **at
    #: the moment this one was picked**, and `None` on a first pick, which had
    #: nothing to be far from. Not the distance to its nearest neighbour in the
    #: finished gallery: a later pick sits at least `radius` away but may still be
    #: closer than this. The retro table is what answers that, over the whole set
    #: at once, which is why it and not this is the calibration instrument.
    distance: float | None = None
    #: The seated candidate, or `None`. Filled at step 6.
    seated: dict | None = None
    #: Why it is empty, where it is. One of [`selection.UNFILLED_REASONS`].
    unfilled: str | None = None
    #: The arithmetic behind that, whether it filled or not.
    fill: dict = field(default_factory=dict)


def plan_slots(rows, matrix, scores, n, strange_share, radius, weight, m, log=print):
    """Steps 1, 2 and 4 together: `(slots, plan)`.

    One call because the three are one decision. How many slots a partition gets
    decides how many points are chosen in it; how the heads split decides what
    each of those points is asked for; and the chosen points are what the
    attempts and the seats are hung on.
    """
    quality = [quality_of(row, scores) for row in rows]
    by_partition: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_partition.setdefault(str(row["partition"]), []).append(index)

    counts = population(rows)
    allocation, caps, guaranteed = slots_for(counts, n, scores, rows)
    log(
        f"[slots] {sum(allocation.values())} slot(s) over {len(counts)} partition(s); "
        f"{len(guaranteed)} guaranteed"
    )

    slots: list[Slot] = []
    chosen: list[Choice] = []
    tallies, retro, splits = {}, {}, {}
    for name in sorted(allocation, key=partition_index):
        want = int(allocation.get(name, 0))
        if want <= 0:
            continue
        picks, tally = choose(by_partition.get(name, []), matrix, quality, want, radius, weight)
        for pick in picks:
            pick.key = str(rows[pick.index]["key"])
            pick.partition = name
        split = head_split(len(picks), strange_share)
        splits[name] = {**split, "planned": want, "chosen": len(picks)}
        for pick, head in zip(picks, head_order(split), strict=True):
            slots.append(
                Slot(
                    id=f"{len(slots):04d}",
                    partition=name,
                    head=head,
                    point=pick.key,
                    point_index=int(pick.index),
                    locations=[
                        str(rows[i]["key"])
                        for i in neighbourhood(
                            pick.index, by_partition[name], matrix, quality, m, radius
                        )
                    ],
                    quality=pick.quality,
                    distance=pick.distance,
                )
            )
        chosen.extend(picks)
        tallies[name] = {**tally, "planned": want}
        retro[name] = retro_table(picks, matrix)
        log(
            f"[slots] {name:<18} {want} planned, {len(picks)} chosen "
            f"({split[budget_module.STRANGE]} strange / {split[budget_module.SMOOTH]} smooth) "
            f"out of {tally['eligible']:,} admitted"
        )

    plan = {
        "requested": int(n),
        "radius": float(radius),
        "quality_weight": float(weight),
        "strange_share": float(strange_share),
        "neighbourhood": int(m),
        "population": counts,
        "release_caps": caps,
        "guaranteed": guaranteed,
        "slots_by_partition": allocation,
        "head_split": splits,
        "selection": tallies,
        # Per partition AND overall, because they answer two questions. The
        # per-partition table is where the radius is calibrated — a partition is
        # what a slot is allocated in — and the overall one is where
        # cross-partition similarity would show up if there were any, which the
        # design deliberately does not act on at N=50 and wants visible anyway.
        "retro": {"by_partition": retro, "overall": retro_table(chosen, matrix)},
    }
    return slots, plan


# --------------------------------------------------------------------------- #
# Step 5: the attempts.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Try:
    """One planned attempt: a location, a head, and its place in that head's draw."""

    key: str
    partition: str
    head: str
    rank: int
    modes_drawn: int
    mode_index: int

    def plan(self) -> budget_module.Attempt:
        return budget_module.Attempt(
            head=self.head,
            partition=self.partition,
            key=self.key,
            rank=self.rank,
            modes_drawn=self.modes_drawn,
            mode_index=self.mode_index,
        )


def attempt_plan(slots: list, ranks: dict, smooth: int, strange: int) -> list[Try]:
    """Every attempt the pass will make, deduplicated by location.

    Two slots whose neighbourhoods overlap ask for the same location's attempts,
    and rendering it twice would buy the same pictures twice — the mode draw is
    seeded off the location and the head, so the second set would be identical.
    So the plan is over the **union** of every slot's locations, and step 6 reads
    whichever of them its own neighbourhood names.
    """
    seen: dict[str, str] = {}
    for slot in slots:
        for key in slot.locations:
            seen.setdefault(key, slot.partition)
    out: list[Try] = []
    for key in sorted(seen):
        partition = seen[key]
        rank = ranks.get(key, 0)
        for index in range(max(0, smooth)):
            # The smooth judge owns one coloring, so its draws are distinct
            # PALETTE ANCHORS rather than distinct modes — `modes_drawn` stays at
            # one, and the anchor is what the two attempts differ in.
            out.append(Try(key, partition, budget_module.SMOOTH, rank, 1, 0))
            del index
        for index in range(max(0, strange)):
            out.append(Try(key, partition, budget_module.STRANGE, rank, max(1, strange), index))
    return out


def sweep_candidates(directory: Path, keep: set) -> int:
    """Delete every palette-candidate JPEG but the ones a verdict actually used.

    32 maps are rendered to choose one and the 31 that lost are working, not
    record: the row keeps the whole candidate set by name and the head's score for
    each, which is what a later reader needs, and the pictures are a recolor of a
    field that is still on disk. At 24 attempts a slot and 32 recolors an attempt
    this is the difference between a pass costing a few gigabytes and costing tens.
    """
    root = directory / "candidates"
    if not root.is_dir():
        return 0
    dropped = 0
    for picture in root.glob("*/*.jpg"):
        if str(picture.relative_to(root)).replace("\\", "/") in keep:
            continue
        picture.unlink(missing_ok=True)
        dropped += 1
    return dropped


def make_attempts(directory: Path, plan: list, by_key: dict, seed: int, device: str, log=print):
    """Run every planned attempt, resuming whatever this pass already recorded.

    `(rows, counts)`. The candidate log is the record that an attempt is done —
    the same rule a run follows, and for the same reason: a picture on disk is
    evidence that a render wrote bytes and nothing else.
    """
    log_path = directory / "candidates.jsonl"
    done = run_module.completed_attempts(log_path, log)
    if done:
        log(f"[attempts] {len(done)} of {len(plan)} already recorded; carrying them across")
    anchors = colorize.anchors(colorize.pool(), max(1, len(plan)), seed)
    rows = list(done.values())
    counts = {"planned": len(plan), "resumed": len(done), "made": 0, "failed": 0}
    colorizer, seconds = None, 0.0

    for index, planned in enumerate(plan):
        if index in done:
            continue
        if colorizer is None:
            colorizer = colorize.Colorizer(directory, seed, device, log)
        started = time.monotonic()
        row = colorize.annotate(
            colorizer.attempt(planned.plan(), by_key[planned.key], anchors[index], index)
        )
        seconds += time.monotonic() - started
        rows.append(row)
        run_module.append_attempt(log_path, row)
        counts["made" if row.get("p_ge3") is not None else "failed"] += 1
        verdict = (
            f"P(>=3) {row['p_ge3']:.4f}"
            if row.get("p_ge3") is not None
            else f"FAILED {row.get('error')}"
        )
        log(
            f"[attempts] {index + 1}/{len(plan)} {planned.head} {planned.partition} "
            f"{row.get('mode')}/{row.get('colormap')} {verdict}"
        )
    # Off EVERY row, resumed ones included, and after the loop rather than inside
    # it. Two attempts on one location draw two different anchors and therefore
    # two overlapping thirty-two-map neighbourhoods, so a sweep taken mid-loop
    # would delete a picture the next attempt is about to ask for; and a sweep
    # taken off this invocation's rows alone would leave a resumed pass's working
    # behind forever.
    counts["dropped_candidate_jpegs"] = sweep_candidates(
        directory, _picked(rows, by_key, directory)
    )
    counts["seconds"] = round(seconds, 1)
    counts["seconds_per_attempt"] = round(seconds / counts["made"], 2) if counts["made"] else None
    rows.sort(key=lambda row: row["attempt"])
    return rows, counts


# --------------------------------------------------------------------------- #
# Step 6: what takes each slot.
# --------------------------------------------------------------------------- #
def _picked(rows: list, by_key: dict, directory: Path) -> set:
    """`{field/map.jpg}` for every palette the pass's verdicts actually used."""
    kept = set()
    for row in rows:
        if not row.get("colormap"):
            continue
        field_name = colorize.field_of(by_key[row["key"]], directory / "fields").stem
        kept.add(f"{field_name}/{row['colormap']}.jpg")
    return kept


def candidate_of_pool_row(row: dict) -> dict:
    """A persisted release record as the flat candidate row the pass compares.

    THE row-shape adapter. A run's candidate is a flat dict — the shape
    `colorize.attempt` produces and `selection.entries` reads — and a recorded
    decision is the same facts under `location`, `recipe` and `scores`. Reading
    the pool means reading both, and one of them has to be spelled in the other's
    shape or every consumer grows two branches.

    The scores are **`scores_current`** where the row has one: that block is the
    live head's reading of the same picture, and a pass that ranked run2's
    three-class numbers against run10's four-class ones would be ordering the
    gallery by which artifact happened to score each row.
    """
    location = row.get("location") or {}
    recipe = row.get("recipe") or {}
    palette = row.get("palette") or {}
    read = row.get("scores_current") or row.get("scores") or {}
    return {
        "attempt": None,
        "candidate": f"{row['run']}_{row['candidate']}",
        "source": {"run": row["run"], "candidate": row["candidate"], "key": row["key"]},
        "head": read.get("head") or (row.get("scores") or {}).get("head"),
        "partition": location.get("partition"),
        "key": location.get("key"),
        "rank": None,
        "family": location.get("family"),
        "viewport": location.get("viewport"),
        "maxiter": location.get("maxiter"),
        "location_score": (row.get("scores") or {}).get("location_p_ge3"),
        "ledger": location.get("ledger"),
        "anchor": palette.get("anchor"),
        "candidates": palette.get("candidates"),
        "candidate_scores": palette.get("scores"),
        "mode": recipe.get("mode"),
        "mode_kind": recipe.get("mode_kind"),
        "curve": recipe.get("curve"),
        "colormap": recipe.get("colormap"),
        "mirror": recipe.get("mirror"),
        "render": recipe.get("render"),
        "autolevel": row.get("autolevel"),
        "p_ge2": read.get("p_ge2"),
        "p_ge3": read.get("p_ge3"),
        "p_ge4": read.get("p_ge4"),
        "rank_score": read.get("rank_score"),
        "scores_current": row.get("scores_current"),
        "error": None,
    }


def candidate_of_attempt(row: dict, pass_id: str) -> dict:
    """One of this pass's own attempts, in the same flat shape.

    `scores_current` is written here rather than left to a later re-score: the
    attempt was judged by the head that is shipped right now, so the two blocks
    are the same reading and saying so is cheaper than a pass over the pool to
    discover it.
    """
    return {
        **row,
        "candidate": f"{row['attempt']:04d}",
        "source": {"run": pass_id, "candidate": f"{row['attempt']:04d}", "key": None},
        "scores_current": {
            "head": row.get("head"),
            "head_sha256": floors.live_stamp(row["head"]) if row.get("head") else None,
            "p_ge2": row.get("p_ge2"),
            "p_ge3": row.get("p_ge3"),
            "p_ge4": row.get("p_ge4"),
            "rank_score": row.get("rank_score"),
        },
    }


def rank_key(candidate: dict):
    """Best first **within one head's list**: `P(>=4)`, then `P(>=3)`, then the id.

    Never across two heads. The two finished-render judges are calibrated
    separately, so a single sort over both orders the gallery by whichever head's
    scale runs higher — the failure this project has already made once, one stage
    upstream, and lost eighty-two release-eligible strange candidates to.

    `P(>=4)` leads because it is the question a gallery slot asks. `P(>=3)` breaks
    the tie, which matters more than it looks: at the top of a saturated
    distribution the third cutpoint is where the ordering still has resolution,
    and on a head with no fourth class at all it is the only column there is.
    """
    return (
        -(candidate.get("p_ge4") if candidate.get("p_ge4") is not None else -1.0),
        -(candidate.get("p_ge3") if candidate.get("p_ge3") is not None else -1.0),
        str(candidate.get("candidate")),
    )


def seat(slots: list, candidates: list, log=print) -> dict:
    """Fill each slot with the best candidate its head may seat. Mutates `slots`.

    Two rules and one order. The **floor** ([`floors.gallery_floor`]) says a
    candidate below it may not take a slot at all; **one wallpaper per location**
    ([`floors.CLUSTER_CAP`]) says a near-duplicate group that already holds a seat
    may not take a second. Slots are filled in *pick order interleaved across
    partitions* — every partition's first pick, then every partition's second —
    so where two slots want one place the stronger pick keeps it and every prefix
    of the pass covers the partitions evenly.

    The grouping is taken **once**, over every candidate the pass can see, because
    a group id is a position in a connected-components labelling and tags from two
    calls are unrelated.
    """
    tags = selection.groups_of([_place(candidate) for candidate in candidates])
    group_of = {}
    for candidate, tag in zip(candidates, tags, strict=True):
        group_of[str(candidate["candidate"])] = tag

    by_location: dict[tuple, list] = {}
    for candidate in candidates:
        by_location.setdefault((str(candidate["key"]), str(candidate["head"])), []).append(
            candidate
        )

    floor_of = {head: floors.gallery_floor(head) for head in budget_module.HEADS}
    used: dict[str, int] = {}
    order = sorted(range(len(slots)), key=lambda i: _seat_order(slots, i))
    for position in order:
        slot = slots[position]
        pool = [
            candidate
            for key in slot.locations
            for candidate in by_location.get((key, slot.head), ())
        ]
        pool.sort(key=rank_key)
        floor = floor_of[slot.head]
        below = capped = 0
        for candidate in pool:
            if not floor.acts(candidate.get("p_ge3")):
                below += 1
                continue
            tag = group_of[str(candidate["candidate"])]
            if used.get(tag, 0) >= floors.CLUSTER_CAP:
                capped += 1
                continue
            used[tag] = used.get(tag, 0) + 1
            slot.seated = {**candidate, "group": tag}
            break
        slot.fill = {
            "eligible": len(pool),
            "below_floor": below,
            "location_served": capped,
            "floor": {"name": floor.name, "value": floor.value, "head_sha256": floor.stamp},
        }
        if slot.seated is None:
            slot.unfilled = (
                "below_bar" if below else selection.LOCATION_SERVED if capped else "no_candidates"
            )
            slot.fill["reason"] = slot.unfilled
            slot.fill["why"] = selection.UNFILLED_REASONS[slot.unfilled]

    filled = sum(1 for slot in slots if slot.seated)
    by_cell: dict = {}
    for slot in slots:
        cell = by_cell.setdefault(
            f"{slot.partition}/{slot.head}",
            {"slots": 0, "filled": 0, "unfilled": 0, "reasons": {}},
        )
        cell["slots"] += 1
        cell["filled"] += int(slot.seated is not None)
        cell["unfilled"] += int(slot.seated is None)
        if slot.unfilled:
            cell["reasons"][slot.unfilled] = cell["reasons"].get(slot.unfilled, 0) + 1
    log(f"[seat] {filled}/{len(slots)} slot(s) filled")
    for name, cell in sorted(by_cell.items()):
        if cell["unfilled"]:
            why = ", ".join(
                f"{count} {reason}" for reason, count in sorted(cell["reasons"].items())
            )
            log(f"[seat] {name:<32} {cell['filled']}/{cell['slots']} filled · {why}")
    return {
        "slots": len(slots),
        "filled": filled,
        "unfilled": len(slots) - filled,
        "wallpapers_per_location": floors.CLUSTER_CAP,
        "by_partition_head": dict(sorted(by_cell.items())),
        "floors": {
            head: {"name": cut.name, "value": cut.value, "head_sha256": cut.stamp}
            for head, cut in sorted(floor_of.items())
        },
    }


def partition_index(partition: str) -> int:
    """A partition's place in the canonical report order; unregistered ones last.

    The same rule [`records.score_rank`] sorts on, and tolerant for the same
    reason: a partition retired from the registry still has rows in the pool, and
    an ordering that raised on one would make the whole pass unreadable over a
    record it can otherwise read perfectly well.
    """
    try:
        return partition_module.ALL_PARTITIONS.index(partition)
    except ValueError:
        return len(partition_module.ALL_PARTITIONS)


def _seat_order(slots: list, index: int) -> tuple:
    """Pick position first, then the partition's own order. The interleave."""
    slot = slots[index]
    seen = [i for i, other in enumerate(slots) if other.partition == slot.partition]
    return (seen.index(index), partition_index(slot.partition), index)


def _place(candidate: dict) -> dict:
    """What the near-duplicate grouping needs off a candidate: the location."""
    return {"family": candidate.get("family"), "viewport": candidate.get("viewport")}


def pool_candidates(slots: list, pass_id: str) -> list[dict]:
    """Every candidate already in the pool that stands on one of this pass's locations.

    The whole reason the pass is worth running over an accumulated store: six runs
    have already coloured and judged 1,050 candidates, and any of them standing on
    a chosen point's neighbourhood is a wallpaper the pass can seat without
    rendering anything first.

    **Two stores, because the pool is in two places.** A run records every scored
    attempt in the tracked release store, and an earlier *pass* records its
    attempts in [`curation.gallery_store`] instead — untracked, manifest-described,
    and every bit as much a coloured judged candidate standing on a location. A
    reader of the release store alone would silently lose an earlier pass's
    thousand-odd attempts, which is the largest single block of material a second
    pass has to seat out of.

    Three exclusions, and each is a different fact. A row this pass wrote is
    already in hand, so reading it back would double it. A row a person
    **rejected** was taken out of service deliberately and a pass that re-seated
    it would be overruling the review. A row with no score never got one — a
    failed render is a decision with a reason and no number — and ranking it
    against a wallpaper is the comparison the record exists to prevent.
    """
    wanted = {key for slot in slots for key in slot.locations}
    seen: set[str] = set()
    out = []
    for row in [*records.read_decisions(records.RELEASE), *gallery_store.read()]:
        if row.get("run") == pass_id or records.is_rejected(row):
            continue
        if str((row.get("location") or {}).get("key")) not in wanted:
            continue
        candidate = candidate_of_pool_row(row)
        if candidate.get("p_ge3") is None or candidate.get("head") not in budget_module.HEADS:
            continue
        # An earlier pass's winner is in both stores — once as the attempt that
        # was made and once as the seat it took — and the two rows carry the same
        # `<run>_<candidate>` identity, so the second one read is the same
        # picture arriving twice into one ranked pool.
        if candidate["candidate"] in seen:
            continue
        seen.add(candidate["candidate"])
        out.append(candidate)
    return out


# --------------------------------------------------------------------------- #
# Step 7: the winners, at full size, and only the winners.
# --------------------------------------------------------------------------- #
def render_winners(slots: list, directory: Path, workers: int, log=print) -> dict:
    """Render every seated candidate at [`RESOLUTION`]. `(record)`; mutates `slots`.

    **No re-score.** The full-size picture is the same recipe as the candidate the
    decision was taken on, at four times the linear size, and reading it through
    the head again would be a second measurement wearing the first one's number —
    the floors were fit on 640x360 candidate renders and a height read at one
    geometry does not transfer to another.

    The operator runs *inside* the render ([`colorize.render`]), which is a second
    full-size render wherever it acts. That is why a pass's release leg is not
    simply `slots x 25 s`, and why the stamp it writes is its own rather than the
    candidate's: two renders, two measurements, two facts.
    """
    where = directory / "release"
    where.mkdir(parents=True, exist_ok=True)
    stamps = where / "autolevel_stamps.jsonl"
    geometry = {"resolution": list(RESOLUTION), "supersample": SUPERSAMPLE}
    swept = colorize.sweep_writing(where)
    if swept:
        log(f"[render] discarded {swept} unfinished render(s) left by an earlier attempt")

    tasks, done, reused = [], {}, []
    for slot in slots:
        if slot.seated is None:
            continue
        identifier = str(slot.seated["candidate"])
        picture = where / f"{identifier}.png"
        if picture.is_file():
            done[identifier] = picture
            reused.append(identifier)
            continue
        tasks.append(
            release.Task(
                id=identifier,
                row={
                    "family": slot.seated["family"],
                    "viewport": slot.seated["viewport"],
                    "maxiter": slot.seated["maxiter"],
                },
                colormap=slot.seated["colormap"],
                mode=slot.seated["mode"],
                output=str(picture),
                geometry={**geometry, "maxiter": int(slot.seated["maxiter"])},
            )
        )
    outcomes = {"rendered": 0, "failed": 0}
    written: dict = {}

    def sink(task, result):
        outcomes["rendered" if result.ok else "failed"] += 1
        if result.ok:
            done[task.id] = Path(result.info["picture"])
        else:
            log(f"[render] {task.id} failed at full resolution: {result.error}")
        if result.stamp is not None:
            written[task.id] = result.stamp
            with stamps.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps({"id": task.id, "autolevel": result.stamp}, ensure_ascii=False)
                    + "\n"
                )
        with release.timing_path(where).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    {
                        "id": task.id,
                        "seconds": round(result.seconds, 3),
                        "mode": task.mode,
                        "ok": result.ok,
                        **geometry,
                    }
                )
                + "\n"
            )

    started = time.monotonic()
    record = release.run_pass(tasks, workers, sink, log, leg=None)
    seconds = time.monotonic() - started
    stamped = _release_stamps(where)
    for slot in slots:
        if slot.seated is None:
            continue
        identifier = str(slot.seated["candidate"])
        slot.seated["release_picture"] = (
            str(done[identifier].relative_to(directory)) if identifier in done else None
        )
        slot.seated["release_autolevel"] = written.get(identifier, stamped.get(identifier))
    record["geometry"] = geometry
    record["reused"] = len(reused)
    record["counts"] = {
        "planned": len(tasks) + len(reused),
        "resumed": len(reused),
        "made": outcomes["rendered"],
        "failed": outcomes["failed"],
        "not_started": len(record["not_started"]),
    }
    record["seconds"] = round(seconds, 1)
    record["seconds_per_full_size"] = (
        round(seconds / outcomes["rendered"], 1) if outcomes["rendered"] else None
    )
    return record


def _release_stamps(where: Path) -> dict:
    """Every autolevel stamp the release log holds, by candidate. Last write wins."""
    path = where / "autolevel_stamps.jsonl"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row["id"])] = row.get("autolevel")
    return out


# --------------------------------------------------------------------------- #
# What the pass leaves behind.
# --------------------------------------------------------------------------- #
def write_records(pass_id, slots, attempts, guaranteed, log=print) -> dict:
    """Everything the pass leaves behind, split by what its size does with `n`.

    Three stores and one identity.

    The **attempts** are pool rows — the location, the recipe, the palette draw,
    the judge's verdict, one line each carrying its whole join — and they go to
    [`curation.gallery_store`], under `artifacts/` with a tracked manifest and a
    copy on the archive tier. That is where the size is: `locations x heads x
    draws` per slot, 1,120 rows at n=50 and ten times that at n=500, at about
    3.8 KB a row, against a 1 MiB per-file history guard.

    The **release store** takes the winners and nothing else. It answers *which
    candidate took a slot*, a pass takes at most `n` of those decisions, and a row
    per losing attempt was the duplicate that made a pass cost eight megabytes of
    tracked text. What each slot passed over is on the slot — `eligible`,
    `below_floor`, `location_served` — in the pass record, so the denominator
    survives the rows.

    The pass's **summary** goes to [`record_dir`], beside `runs/` and not in it,
    because a pass books no clock and measures no release rate a later night
    should derive a reservation from.

    A seated row that came out of an **earlier run** is written again here, under
    this pass's own candidate id, with `source` naming the row it was seated from.
    That is not a duplicate: the earlier row records a run deciding what to keep,
    and this one records the gallery pass deciding what to ship — two decisions
    about one picture, taken by two passes out of two populations.
    """
    seated = {str(slot.seated["candidate"]): slot for slot in slots if slot.seated is not None}
    owed = set(guaranteed)
    first_of: dict[str, str] = {}
    for slot in sorted(
        (slot for slot in slots if slot.seated),
        key=lambda s: (partition_index(s.partition), s.id),
    ):
        first_of.setdefault(slot.partition, slot.id)

    attempt_rows = [
        records.decision(
            run=pass_id,
            stage=records.GATE,
            candidate=f"{row['attempt']:04d}",
            verdict="kept" if row.get("p_ge3") is not None else "dropped",
            row=row,
            reason=row.get("error"),
            picture=row.get("picture"),
        )
        for row in attempts
    ]
    store_path, store_rows, store_new = gallery_store.write(pass_id, attempt_rows)
    manifest = (
        gallery_store.save(pass_id, log=lambda line: log(f"[store] {line}"))
        if attempt_rows
        else None
    )

    release_rows = [
        _release_row(pass_id, slot.seated, slot, first_of, owed)
        for _, slot in sorted(seated.items())
    ]
    release_path, _, release_new = records.write_decisions(records.RELEASE, pass_id, release_rows)
    log(
        f"[records] {len(attempt_rows)} attempt row(s) under {tracked_name(store_path)}, "
        f"{len(release_rows)} winner(s) under {pass_id}"
    )
    return {
        "durable": records.is_durable(),
        "root": tracked_name(records.root()),
        # The two halves, named as two, because the whole point of the split is
        # that only one of them is in the history and only the other one grows
        # with the attempt count.
        "attempts": {
            "store": tracked_name(store_path),
            "rows": store_rows,
            "new": store_new,
            "manifest": None if manifest is None else tracked_name(manifest_path_of(pass_id)),
            "copy": None if manifest is None else manifest.get("copy"),
            "sha256": None if manifest is None else manifest.get("sha256"),
            "bytes": None if manifest is None else manifest.get("bytes"),
        },
        "release": f"{tracked_name(release_path)} (+{release_new})",
        "release_rows": len(release_rows),
    }


def manifest_path_of(pass_id: str) -> Path:
    """The tracked manifest describing this pass's attempt store."""
    return gallery_store.manifest_path(pass_id)


def tracked_bytes(pass_id: str) -> dict:
    """What one pass has put in the history, by file. The number the split is about.

    A reading, not a field: it is taken *after* everything is written — by
    [`cli.print_gallery`], and by anybody checking — because a total recorded
    inside the pass record would be a number that changed the file it measured.

    Everything counted here scales with `n`. Nothing here scales with the attempt
    count, and `tests/test_curation_gallery.py` pins that on a synthetic N=500
    plan rather than leaving it as something somebody remembers.
    """
    files: dict[str, int] = {}
    directory = pass_record_dir(pass_id)
    if directory.is_dir():
        for path in sorted(directory.iterdir()):
            if path.is_file():
                files[tracked_name(path)] = path.stat().st_size
    releases = records.decisions_dir(records.RELEASE, pass_id)
    if releases.is_dir():
        for path in sorted(releases.glob("*.jsonl")):
            files[tracked_name(path)] = path.stat().st_size
    return {
        "total": sum(files.values()),
        "largest": max(files.values(), default=0),
        "files": dict(sorted(files.items())),
    }


def _release_row(pass_id, candidate, slot, first_of, owed) -> dict:
    """One release row for one seated candidate: what the pass decided to ship.

    Only ever called for a slot that filled. A candidate the pass looked at and
    did not seat has its row in the attempt store and its arithmetic on the slot;
    [`records.PASSED_OVER`] is a run's verdict, written over a night's population
    that will not exist again, and a pass writing one per losing attempt was
    recording the same rows a second time in the history.
    """
    picture = candidate.get("release_picture")
    verdict = records.RELEASED if picture else records.KILLED
    reason = None if picture else records.KILLED_REASON
    row = records.decision(
        run=pass_id,
        stage=records.RELEASE,
        candidate=str(candidate["candidate"]),
        verdict=verdict,
        # Every release row this pass writes is the gallery's, the way every row a
        # run writes is that run's diagnostic. The verdict says whether there is a
        # wallpaper at the end of the row; this says which collection the decision
        # was taken for, and the two are different questions on purpose.
        collection=records.GALLERY,
        row=candidate,
        reason=reason,
        slot_source=(
            "guarantee"
            if first_of.get(slot.partition) == slot.id and slot.partition in owed
            else "mix"
        ),
        group=candidate.get("group"),
        picture=picture,
    )
    row["scores_current"] = candidate.get("scores_current")
    row["release_autolevel"] = candidate.get("release_autolevel")
    # Which slot this was decided against, and the arithmetic of the slot. On the
    # row rather than only on the pass record, because a pool row outlives the
    # pass that wrote it and a reader joining on the pass id alone could not say
    # which of fifty slots a wallpaper took or how far its place sat from the
    # nearest other place the pass chose.
    row["slot"] = {
        "pass": pass_id,
        "id": slot.id,
        "head": slot.head,
        "point": slot.point,
        "point_index": slot.point_index,
        "locations": list(slot.locations),
        "point_quality": slot.quality,
        "nearest_chosen": slot.distance,
    }
    row["source"] = candidate.get("source")
    return row


def write_pass(pass_id: str, record: dict) -> Path:
    """The pass's record, whole, into its own directory. A re-run replaces it.

    Not upserted and not appended to a shared listing: a pass is superseded by the
    next one rather than accumulated into it, and the record that says what the
    gallery is right now is the newest directory here.

    **The slots go to a file per partition** and the summary keeps everything else.
    One file held both until the numbers said what a slot costs — about a kilobyte,
    so N=500 is 1.3 MiB in one file against a 1 MiB history guard. The split is the
    one the decision stores already take, on the axis a slot is allocated on, and
    [`read_pass`] puts the record back together so no reader has to know.
    """
    directory = pass_record_dir(pass_id)
    directory.mkdir(parents=True, exist_ok=True)
    by_partition: dict[str, list[dict]] = {}
    for row in record.get("slots") or []:
        by_partition.setdefault(str(row.get("partition")), []).append(row)
    written = set()
    for name, rows in by_partition.items():
        path = slots_path(pass_id, name)
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )
        written.add(path.name)
    # A re-run over fewer partitions leaves no file behind claiming slots this pass
    # no longer has.
    for stale in directory.glob("*.jsonl"):
        if stale.name not in written:
            stale.unlink()

    summary = {key: value for key, value in record.items() if key != "slots"}
    summary["slots"] = {
        "count": len(record.get("slots") or []),
        "files": sorted(tracked_name(slots_path(pass_id, name)) for name in by_partition),
    }
    path = record_path(pass_id)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def read_pass(pass_id: str) -> dict:
    """One pass's record, put back together: the summary with its slots re-attached.

    In slot-id order, which is the order the draw chose them in, so a reader gets
    the same list [`run`] returned whatever the file axis under it happens to be.
    """
    record = json.loads(record_path(pass_id).read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for path in sorted(pass_record_dir(pass_id).glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    record["slots"] = sorted(rows, key=lambda row: str(row.get("id")))
    return record


# --------------------------------------------------------------------------- #
# The two sheets, for Matt's eye.
# --------------------------------------------------------------------------- #
def contact_sheet(pass_id: str, slots: list, plan: dict, directory, output) -> Path:
    """The gallery itself: every slot, filled or not, partition then rank.

    Filled and unfilled on **one page**, in slot order, because the empty ones are
    the finding. A sheet that only showed what was seated would report a forty-row
    gallery as a forty-row gallery instead of as fifty slots with ten places the
    pool could not fill.
    """
    from fractal_wallpapers.curation import sheet as sheet_module

    directory = Path(directory)
    order = sorted(slots, key=lambda s: (partition_index(s.partition), s.id))
    cards = [_slot_card(slot, directory, sheet_module) for slot in order]
    filled = sum(1 for slot in slots if slot.seated)
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>gallery {pass_id}</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>gallery {pass_id}</h1>",
        f"<p class='lede'>{filled} of {len(slots)} slot(s) filled, {plan['requested']} asked "
        f"for. Radius {plan['radius']:g} cosine, quality weight {plan['quality_weight']:g}, "
        f"strange share {plan['strange_share']:g}. Sorted by partition, then by the order the "
        f"farthest-point draw chose each place. Distribution review is yours.</p>",
        _retro_html(plan),
        "<h2>Slots</h2>",
        "<div class='grid'>" + "".join(cards) + "</div>",
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _slot_card(slot, directory: Path, sheet_module) -> str:
    import html

    if slot.seated is None:
        body = f'<div class="missing">UNFILLED — {html.escape(slot.fill.get("why") or "")}</div>'
        facts = [
            f"{slot.partition} - {slot.head}",
            f"chosen point {slot.point}",
            f"{slot.fill.get('eligible', 0)} candidate(s) on this neighbourhood; "
            f"{slot.fill.get('below_floor', 0)} below the floor, "
            f"{slot.fill.get('location_served', 0)} a place already seated",
        ]
    else:
        seated = slot.seated
        picture = seated.get("release_picture")
        source = directory / picture if picture else None
        body = (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )
        facts = [
            f"{slot.partition} - {slot.head}",
            f"{seated.get('mode')} - {seated.get('colormap')}",
            f"P(>=4) {_number(seated.get('p_ge4'))}, P(>=3) {_number(seated.get('p_ge3'))}",
            f"location P(>=3) {_number(seated.get('location_score'))}",
            f"from {seated['source']['run']}|{seated['source']['candidate']}",
            sheet_module.autolevel_line(
                seated.get("release_autolevel"), "at full size", seated.get("mode_kind")
            ),
            f"key {seated.get('key')}",
        ]
    near = "" if slot.distance is None else f" - {slot.distance:.4f} from its nearest neighbour"
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>slot {html.escape(slot.id)}</b>{html.escape(near)}"
        f"<ul>{caption}</ul></figcaption></figure>"
    )


def _number(value) -> str:
    return "-" if value is None else f"{float(value):.4f}"


def _retro_html(plan: dict) -> str:
    import html

    rows = [
        f"<tr><th>{cell['cosine_distance']:.4f}</th>"
        f"<td>{html.escape(cell['a']['partition'])}</td>"
        f"<td>{html.escape(cell['a']['key'])}</td>"
        f"<td>{html.escape(cell['b']['key'])}</td></tr>"
        for cell in plan["retro"]["overall"]
    ]
    if not rows:
        return ""
    return (
        "<h2>Retro table - the nearest chosen pairs</h2>"
        "<p class='lede'>The calibration instrument. If two of these read as one picture, the "
        "radius is too small.</p>"
        f"<table>{''.join(rows)}</table>"
    )


def runners_up_sheet(pass_id: str, slots: list, rows: list, matrix, radius: float, output) -> Path:
    """What the radius refused, beside the winner it was refused for.

    The other half of the calibration read. The retro table says how far apart the
    chosen points ended up; this says what the pass declined to choose in order to
    get there, at its **neutral render** — the same picture the distance was
    measured on, uncoloured, which is what makes the comparison the one the pass
    actually made rather than a comparison of two palette draws.
    """
    import html

    import numpy

    from fractal_wallpapers.curation import neutral
    from fractal_wallpapers.curation import sheet as sheet_module

    index_of = {str(row["key"]): position for position, row in enumerate(rows)}
    by_partition: dict[str, list[int]] = {}
    for position, row in enumerate(rows):
        by_partition.setdefault(str(row["partition"]), []).append(position)
    neutral_dir = neutral.neutral_dir()
    sections, shown = [], 0
    for slot in sorted(slots, key=lambda s: (partition_index(s.partition), s.id)):
        here = index_of.get(slot.point)
        if here is None:
            continue
        same = by_partition.get(slot.partition, [])
        distances = 1.0 - (matrix[same] @ matrix[here])
        near = [
            (float(distances[position]), same[position])
            for position in numpy.argsort(distances)
            if same[position] != here and float(distances[position]) < float(radius)
        ][:RUNNERS_UP]
        if not near:
            continue
        shown += len(near)
        cards = [_neutral_card(rows[here], 0.0, neutral_dir, sheet_module, "the chosen point")]
        cards += [
            _neutral_card(rows[position], distance, neutral_dir, sheet_module, "refused by radius")
            for distance, position in near
        ]
        seated = slot.seated
        won = "" if seated is None else f" - seated {html.escape(str(seated['candidate']))}"
        sections.append(
            f"<h2>slot {html.escape(slot.id)} - {html.escape(slot.partition)} - "
            f"{html.escape(slot.head)}{won}</h2>"
            "<div class='grid'>" + "".join(cards) + "</div>"
        )
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>gallery {pass_id} runners-up</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>gallery {pass_id} - refused by the radius</h1>",
        f"<p class='lede'>{shown} runner(s)-up over {len(sections)} slot(s). For each chosen "
        f"point, the nearest admitted locations the hard radius ({radius:g} cosine) refused, at "
        f"their neutral renders - the picture the distance was measured on.</p>",
        *sections,
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _neutral_card(row: dict, distance: float, neutral_dir: Path, sheet_module, what: str) -> str:
    import html

    picture = neutral_dir / str(row.get("picture") or "")
    body = (
        f'<img src="{sheet_module.thumbnail(picture)}" alt="">'
        if picture.is_file()
        else '<div class="missing">no neutral render on disk</div>'
    )
    facts = [
        what,
        f"cosine distance {distance:.4f}",
        f"location P(>=3) {_number(row.get('location_p_ge3'))}",
        f"key {row.get('key')}",
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{distance:.4f}</b><ul>{caption}</ul></figcaption></figure>"
    )


# --------------------------------------------------------------------------- #
# The pass itself.
# --------------------------------------------------------------------------- #
def sheet_dir() -> Path:
    """Where the two sheets are written: `scratch/`, which is disposable by rule.

    They embed their own thumbnails, so a page is a few hundred kilobytes of
    self-contained HTML that can be copied anywhere and opened. Neither is a
    record — everything on them is derived from the pass record and the pool —
    and a binary-carrying page is not something the history would take anyway.
    """
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "scratch"


def parse_attempts(text) -> tuple:
    """`"m,smooth,strange"` as three integers, or [`ATTEMPTS`] where nothing is said."""
    if text is None:
        return ATTEMPTS
    if isinstance(text, (tuple, list)):
        parts = list(text)
    else:
        parts = [piece.strip() for piece in str(text).split(",")]
    if len(parts) != 3:
        raise PassRefused(
            f"--attempts takes three counts, m,smooth,strange — the locations tried near each "
            f"chosen point, the smooth attempts each of them gets on distinct palette anchors, "
            f"and the strange attempts each gets on distinct modes. Got {text!r}."
        )
    try:
        m, smooth, strange = (int(piece) for piece in parts)
    except ValueError as bad:
        raise PassRefused(f"--attempts takes three integers: {text!r} ({bad})") from bad
    if m < 1:
        raise PassRefused("--attempts needs at least one location per chosen point")
    return (m, max(0, smooth), max(0, strange))


def run(
    pass_id: str | None = None,
    n: int = DEFAULT_N,
    radius: float = RADIUS,
    quality_weight: float = QUALITY_WEIGHT,
    strange_share: float | None = None,
    attempts=None,
    no_attempts: bool = False,
    seed: int = DEFAULT_SEED,
    workers: int = release.DEFAULT_WORKERS,
    device: str = "auto",
    log=print,
) -> dict:
    """One gallery pass, end to end. Returns the pass's own record.

    `no_attempts` skips step 5 and seats out of the standing pool alone. It is a
    **dev affordance** and never the default: without the attempt leg the pass is
    supply-bound on the fraction of the admitted population any run has happened
    to colour, and every number it reports about how full the gallery is is a
    number about that fraction rather than about the pool. It exists so somebody
    iterating on the selection does not pay an hour of renders per change.
    """
    started = time.monotonic()
    share = run_module.STRANGE_SHARE if strange_share is None else float(strange_share)
    m, smooth, strange = parse_attempts(attempts)
    pass_id = str(pass_id or next_pass_id())
    # Before anything is spent and before a row is written. A pass run over the
    # pre-split layout would upsert its winners into a release directory still
    # holding every attempt the old code passed over, and the store would come
    # out both layouts at once.
    gallery_store.refuse_old_layout(pass_id)
    directory = pass_dir(pass_id)
    directory.mkdir(parents=True, exist_ok=True)
    if record_path(pass_id).is_file():
        log(f"[pass] {pass_id} already has a record; this invocation replaces it")
    log(
        f"[pass] {pass_id}: n={n} radius={radius:g} quality_weight={quality_weight:g} "
        f"strange_share={share:g} attempts={m},{smooth},{strange}"
        + (" (SKIPPED: --no-attempts)" if no_attempts else "")
    )

    # --- step 3, first: the distance, refused before anything is spent ------ #
    rows, matrix, store = load_embeddings(log)
    scores = intake.read_scores()
    log(f"[pass] {len(scores):,} location(s) in the supply sidecar")

    # --- steps 1, 2, 4 ----------------------------------------------------- #
    slots, plan = plan_slots(rows, matrix, scores, n, share, radius, quality_weight, m, log)
    plan["attempts"] = {"locations": m, "smooth": smooth, "strange": strange}
    by_key = {str(row["key"]): colorize_row(row) for row in rows}
    ranks = _ranks(rows, scores)

    # --- step 5 ------------------------------------------------------------ #
    if no_attempts:
        made, attempt_counts = (
            [],
            {
                "planned": 0,
                "resumed": 0,
                "made": 0,
                "failed": 0,
                "skipped": "--no-attempts",
            },
        )
    else:
        planned = attempt_plan(slots, ranks, smooth, strange)
        log(
            f"[attempts] {len(planned)} attempt(s) over "
            f"{len({try_.key for try_ in planned})} location(s) for {len(slots)} slot(s)"
        )
        made, attempt_counts = make_attempts(directory, planned, by_key, seed, device, log)

    # --- step 6 ------------------------------------------------------------ #
    mine = [candidate_of_attempt(row, pass_id) for row in made if row.get("p_ge3") is not None]
    standing = pool_candidates(slots, pass_id)
    log(f"[seat] {len(mine)} attempt candidate(s) + {len(standing)} already in the pool")
    seating = seat(slots, mine + standing, log)

    # --- step 7 ------------------------------------------------------------ #
    rendered = render_winners(slots, directory, workers, log)

    # --- what it leaves behind --------------------------------------------- #
    written = write_records(pass_id, slots, made, plan["guaranteed"], log)
    seconds = time.monotonic() - started
    gallery_rows = records.score_rank(
        [
            row
            for row in records.read_decisions(records.RELEASE, pass_id)
            if row.get("verdict") == records.RELEASED and row.get("picture")
        ]
    )
    sheets = {
        "gallery": tracked_name(
            contact_sheet(pass_id, slots, plan, directory, sheet_dir() / f"{pass_id}_sheet.html")
        ),
        "runners_up": tracked_name(
            runners_up_sheet(
                pass_id, slots, rows, matrix, radius, sheet_dir() / f"{pass_id}_runners_up.html"
            )
        ),
    }
    record = {
        "schema": SCHEMA,
        "pass": pass_id,
        "collection": records.GALLERY,
        "seconds": round(seconds, 1),
        "config": {
            "n": int(n),
            "radius": float(radius),
            "quality_weight": float(quality_weight),
            "quality_weight_form": "gain = cosine distance to the nearest chosen point x "
            "location P(>=4) ** quality_weight",
            "strange_share": share,
            "attempts": {"locations": m, "smooth": smooth, "strange": strange},
            "no_attempts": bool(no_attempts),
            "seed": int(seed),
            "candidates_per_set": colorize.CANDIDATES,
            "colorize_geometry": {
                "resolution": list(colorize.RESOLUTION),
                "supersample": colorize.SUPERSAMPLE,
            },
            "release_geometry": {"resolution": list(RESOLUTION), "supersample": SUPERSAMPLE},
            "heads": run_module.head_stamps(),
        },
        "embeddings": {
            "rows": len(rows),
            "verdict": store.get("verdict"),
            "manifest": store.get("manifest"),
        },
        "plan": plan,
        "attempts": attempt_counts,
        "pool": {"standing_candidates": len(standing), "pass_candidates": len(mine)},
        "seating": seating,
        "render": rendered,
        "slots": [_slot_record(slot) for slot in slots],
        "order": [row["candidate"] for row in gallery_rows],
        "records": written,
        "sheets": sheets,
        "pass_dir": tracked_name(directory),
    }
    path = write_pass(pass_id, record)
    record["record"] = tracked_name(path)
    log(f"[pass] record {tracked_name(path)}")
    log(f"[pass] sheet {sheets['gallery']}")
    log(f"[pass] runners-up {sheets['runners_up']}")
    return record


def _ranks(rows: list, scores: dict) -> dict:
    """`{location key: rank in its partition by quality}` — best is zero.

    Carried onto every attempt so the pass's pool rows say how deep the draw
    reached, the same fact `curation.budget` puts on a run's attempts. Without it
    a later reader comparing a pass's attempts to a run's would have to re-derive
    the ordering against a population that has since grown.
    """
    by_partition: dict[str, list] = {}
    for row in rows:
        by_partition.setdefault(str(row["partition"]), []).append(row)
    out: dict[str, int] = {}
    for members in by_partition.values():
        members.sort(key=lambda row: (-quality_of(row, scores), str(row["key"])))
        for rank, row in enumerate(members):
            out[str(row["key"])] = rank
    return out


def _slot_record(slot) -> dict:
    """One slot as the pass record keeps it: what it asked for and what it got."""
    seated = slot.seated
    return {
        "id": slot.id,
        "partition": slot.partition,
        "head": slot.head,
        "point": slot.point,
        "point_index": slot.point_index,
        "point_quality": slot.quality,
        "nearest_chosen": slot.distance,
        "locations": list(slot.locations),
        "fill": slot.fill,
        "unfilled": slot.unfilled,
        "seated": None
        if seated is None
        else {
            "candidate": seated["candidate"],
            "source": seated["source"],
            "key": seated["key"],
            "mode": seated.get("mode"),
            "colormap": seated.get("colormap"),
            "group": seated.get("group"),
            "p_ge3": seated.get("p_ge3"),
            "p_ge4": seated.get("p_ge4"),
            "picture": seated.get("release_picture"),
            # The full-size render's autolevel stamp is NOT here. It is a kilobyte
            # of operator provenance, it is already on this candidate's release row
            # under the same id, and a copy on every slot was three quarters of
            # what a seated slot cost the history.
        },
    }


__all__ = [
    "ATTEMPTS",
    "DEFAULT_N",
    "DEFAULT_SEED",
    "PASS_PREFIX",
    "QUALITY_WEIGHT",
    "RADIUS",
    "RESOLUTION",
    "RETRO_PAIRS",
    "RUNNERS_UP",
    "SCHEMA",
    "SUPERSAMPLE",
    "Choice",
    "PassRefused",
    "Slot",
    "Try",
    "attempt_plan",
    "candidate_of_attempt",
    "candidate_of_pool_row",
    "choose",
    "colorize_row",
    "head_order",
    "head_split",
    "load_embeddings",
    "make_attempts",
    "neighbourhood",
    "next_pass_id",
    "parse_attempts",
    "partition_index",
    "pass_dir",
    "passes",
    "plan_slots",
    "pool_candidates",
    "population",
    "quality_of",
    "rank_key",
    "contact_sheet",
    "record_dir",
    "record_path",
    "render_winners",
    "runners_up_sheet",
    "manifest_path_of",
    "pass_record_dir",
    "read_pass",
    "slots_path",
    "tracked_bytes",
    "write_pass",
    "write_records",
    "retro_table",
    "run",
    "seat",
    "sheet_dir",
    "slots_for",
    "sweep_candidates",
]
