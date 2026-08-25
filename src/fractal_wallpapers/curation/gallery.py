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
3  the distance          the neutral-render embeddings, CUT to the admitted
4  the locations         quality-weighted farthest point under a hard radius
5  the attempts          m locations near each chosen point, judged small   <-.
6  the seats             floors per head, then P(>=4); unfilled beats padded --'  k times
7  the pictures          2560x1440 ss4 for the winners, and only for them
```

Steps 5 and 6 are a loop, and everything either side of them happens once.

Step 7 is the one step that can be **left out without costing a decision**:
`--no-full-size` seats everything exactly as it would have and spends no release
render. The seats are recorded [`records.UNRENDERED`] — took the slot, no
picture, nothing failed — and the sheets fall back to each winner's 640x360
candidate and say which resolution they are showing. Re-running the same pass id
without the flag makes the pictures and lifts the rows to `released`. That is a
different thing from `--no-attempts`, which removes material the pass would
otherwise have decided over and so changes every number it reports.

## The re-seat loop, and what `below_bar` means now

A slot used to be married to the one point the farthest-point draw handed it, and
that turned out to be the whole of gallery1's shortfall. All eight of that pass's
unfilled slots were `below_bar`; all eight were the LAST slot of their partition,
which is by construction the point most remote from everything already chosen and
so the point most likely to sit somewhere the head that owns the slot dislikes on
principle; and all eight sat in partitions still holding thousands of admitted
locations. 128 candidates over eight slots, every one under the floor. That is a
statement about one draw, not about a pool.

So an unfilled slot **re-seats**: it takes the next point its partition's draw
offers — same radius, same weighting, the abandoned point still excluded — its
new neighbourhood is attempted, and the whole seating is taken again. Up to
[`RESEAT_TRIES`] neighbourhoods. `below_bar` on the record now means *k
neighbourhoods in a row failed*, and the slot keeps every point it stood on and
what each one held ([`Slot.tries`]), which is what the `below_floor` sheet is
built out of.

What the loop deliberately does **not** do is the other recovery. No floor moves
and nothing is seated from under one: unfilled still beats padded.

## The population the pass selects over

The embedding store is append-only and the admitted population is not, so the
store is a superset rather than a picture — a location `curate score` re-read and
put under the junk floor keeps its vector forever. [`admitted_only`] cuts the
rows to the current population before anything looks at them, which is what keeps
a withdrawn location out of the picker AND out of the attempt leg at once.

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

The **first** pick of a partition is the one place in that arithmetic with any
freedom in it, and it is drawn rather than taken: uniformly over the partition's
top [`DRAW_TOP_K`] by the same `quality^gamma` the gain uses, under a seed the
pass records. An argmax there made a second pass over an unchanged pool a longer
prefix of the first — the N=150 draw re-chose 142 of gallery3's 150 points — and
every pick after the first is measured against what is already chosen, so moving
the first one moves the whole draw. `--draw-top-k 1` is the argmax, exactly.

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
batch, or the next re-score, or the `below_floor` sheet — reads them the same way
it reads a run's. What is *not* kept is the palette head's working: 32 candidate
maps are rendered to choose one, and the 31 that lost are deleted after the
verdict, which keeps the pick and the scores and throws away the pictures nobody
will look at.

## Locations are cumulative, candidates are per-pass

The one thing the next pass does **not** do with those rows is seat them. A
location is discovered ground and the pass selects over every one the pool has
ever admitted; a candidate is a two-second recolour of a location, and a pass
ships only the recolours it took itself. [`pool_candidates`] is the whole of that
rule, and [`pool_rows`] is deliberately outside it so the `below_floor` sheet
keeps answering "did this partition hold something the slot never reached" out of
the entire pool.

Every chosen point gets both heads' attempts, whichever head owns its slot,
because a mode draw is not free to repeat and the two heads' rosters are
disjoint. The slot's own head is what decides which of them may **fill** it: the
two judges' probabilities live on scales that were calibrated separately and a
list holding both is a list ordered by whichever scale runs higher.

## Unfilled beats padded

A slot with nothing above its head's floor **after every re-seat it is allowed**
is output empty, with the reason named. That is the whole point of the floors
acting here: an empty slot is a statement about where the pool is thin, and it is
the signal for where to label or walk next. A padded slot is the same statement
with the evidence removed.

Both measured floors act ([`floors.gallery_floor`]), which is not what happens at
a run's release, where only the strange one gates. The two decisions are
different: a run's is about how much of its own night is worth looking at, and
this one is about what the collection ships. Neither height is quoted here — both
are restatements that move whenever the judge under them does, and the pass
record carries the pair it actually seated against.

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
import random
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers import process_control
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
from fractal_wallpapers.curation import framing as framing_module
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

#: How many of a partition's strongest live locations the **first pick** of its
#: draw is drawn from, uniformly, under the pass's own seed.
#:
#: Twenty-five. Everything after the first pick is deterministic — `distance x
#: quality**gamma` over whatever the radius left — so the first pick is the whole
#: of a draw's freedom, and an argmax there made a pass over an unchanged pool a
#: longer prefix of the pass before it: the N=150 draw re-chose 142 of gallery3's
#: 150 points, and the pass then spent its attempts where the last one already
#: had. Moving the first pick moves every pick after it, because every distance
#: the draw measures is measured against what is already chosen.
#:
#: Twenty-five and not the whole partition, because the first pick is still meant
#: to be a strong location and not merely a different one. `1` is the argmax this
#: draw took before the seed existed, exactly.
#:
#: Swept over the real pool at gallery3's knobs, n=150, four seeds each — points
#: re-chosen out of gallery3's 150, and the mean location `P(>=4)` of the points
#: chosen:
#:
#: ```text
#: top_k    1   142        0.9318   (the argmax)
#: top_k    5   83-105     0.9354
#: top_k   25    74-89     0.9365
#: top_k  100    71-84     0.9258
#: ```
#:
#: The draw does not pay for its freedom in point quality — at 25 it reads
#: *higher* than the argmax, because a different start lets the radius refuse a
#: different region and the gain finds stronger points elsewhere. 100 is where it
#: turns: barely more movement than 25, and the quality falls below the argmax.
DRAW_TOP_K = 25

#: **How many neighbourhoods a slot may try** before it reports `below_bar`.
#:
#: Three, from gallery1's readout. Every one of that pass's eight unfilled slots
#: was `below_bar`, and every one of them was the LAST slot of its partition —
#: which is the point of the draw most remote from everything already chosen, and
#: so the point most likely to sit somewhere the head that owns the slot dislikes
#: on principle. 128 candidates over eight slots, all 128 below the floor, in
#: partitions holding thousands of admitted locations each: that is a slot married
#: to one neighbourhood, not a pool out of material.
#:
#: One would be the old behaviour. Three is what makes `below_bar` a statement
#: about the *partition* — three neighbourhoods in a row, 3 x 18 attempts on the
#: strange head, all under the bar — at a cost of at most three times a slot's
#: attempts and only for the slots that fail. What it deliberately does not do is
#: the other recovery: no floor moves, and nothing is seated from under one.
RESEAT_TRIES = 3

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

#: How many of the nearest chosen pairs the `closest_pairs` sheet puts side by
#: side. Twelve, which is more than the [`RETRO_PAIRS`] the terminal prints and
#: for a different reason: the table is read for its numbers and this is read by
#: eye, so it wants enough rows that "these two are the same picture" would have
#: to be true of more than one of them before it is a finding about the radius.
CLOSEST_PAIRS = 12


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


#: What a pass's launch lock is called inside its own directory. The directory is
#: under `artifacts/`, so the file is ignored and regenerable like everything else
#: a pass leaves there.
LOCK_NAME = "pass.lock"


def claim_pass(pass_id: str, log=print) -> int:
    """Take the pass id for this process, or refuse. The handle, for `let_go`.

    **One launch per pass id.** Everything a pass makes is named by where it sits
    in the work rather than by which process made it — [`curation.framing.screen`]
    has the engine write `frame<i>.jpg` by position in its own batch and renames
    each one afterwards — so two launches of one pass id do not race for a
    resource, they *rename each other's files*. gallery3 was started twice by
    hand, and both processes ran several minutes and then died on a
    `FileNotFoundError` at a rename, which is as far from a legible collision as a
    failure gets.

    The lock is an operating-system hold on the file rather than the file's
    existence ([`process_control.hold`]), because a pass's normal shape is to be
    interrupted and resumed — gallery3 resumed three times — and a lock a killed
    process leaves behind must not be the thing that stops the resume. The hold
    dies with the process whatever kills it; the file it was taken on is takeable
    the moment nobody is inside.
    """
    directory = pass_dir(pass_id)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK_NAME
    held = process_control.hold(lock)
    if held is None:
        raise PassRefused(
            f"another process is already running the pass {pass_id} ({lock} is held). Two "
            f"launches of one pass id write into one framings/ directory, where the frames "
            f"are named by position in a batch and renamed afterwards, so each process "
            f"renames the other's files and both die minutes later on a rename that finds "
            f"nothing. Wait for it, or run a different pass id."
        )
    log(f"[pass] {pass_id} claimed; no second launch of it can start while this one runs")
    return held


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


def admitted_only(rows: list, matrix, scores: dict, log=print) -> tuple:
    """`(rows, matrix, dropped)` — the store cut down to the CURRENT population.

    The embedding store is **append-only**: a location embedded once keeps its
    vector forever, and re-scoring is free to move the reading underneath it. So
    the store is a superset of the admitted population rather than a picture of
    it — 29,051 rows against 29,046 admitted on 2026-08-22, the five being
    locations `curate score` re-read at the node regime and put under the junk
    floor.

    A location the sidecar now calls junk is not a place the collection may ship,
    and the pass is the one reader for whom that is expensive rather than
    cosmetic: an unpinned pass could choose such a point, spend a slot's attempts
    on its neighbourhood, and seat a wallpaper of somewhere the supply phase has
    already withdrawn. Cutting the rows here — before the picker, and before the
    neighbourhoods the attempt leg is planned off — is what makes it invisible to
    both at once, rather than a filter each of them has to remember.

    The cut is [`floors.passes_junk_floor`] over the sidecar's live `P(>=3)`, the
    same comparison [`embeddings.admitted`] makes; a key the sidecar does not
    hold at all is dropped for the same reason, since a location with no current
    reading has no current standing either.
    """
    keep = [
        index
        for index, row in enumerate(rows)
        if floors.passes_junk_floor((scores.get(str(row["key"])) or {}).get("p_ge3"))
    ]
    dropped = len(rows) - len(keep)
    if not dropped:
        return rows, matrix, 0
    log(
        f"[embed] {dropped} embedded location(s) are below the junk floor now and are "
        f"out of this pass's population: {len(keep):,} selected over"
    )
    if not keep:
        raise PassRefused(
            f"none of the {len(rows):,} embedded location(s) is in the admitted population "
            f"any more, so there is nothing to select over. Run `fractal-wallpapers curate "
            f"score` and `curate embed`."
        )
    return [rows[index] for index in keep], matrix[keep], dropped


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
        {head: int(split.get(head, 0)) for head in budget_module.KINDS}, sum(split.values())
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


def resolve_draw_seed(seed: int | None = None) -> int:
    """The root seed a pass's draws run under: the one given, or one drawn now.

    A pass that was not given one **draws** it rather than defaulting to a fixed
    number, because a default is how every pass over an unchanged pool comes out
    the same pass. What makes the run reproducible is not the constant; it is that
    the resolved integer lands on the record, which is why this returns one and
    the caller writes it down before it spends anything.
    """
    return int(seed) if seed is not None else secrets.randbits(32)


def partition_draw_seed(root: int, partition: str) -> int:
    """The **resolved** seed one partition's draw runs under, off the root.

    Derived and not drawn, so a pass records one number and every partition's
    draw is recoverable from it — and derived per partition rather than shared,
    so a partition whose slot count changes does not move any other partition's
    first pick.

    The pass record carries what this returns, never the recipe: a reader holding
    the record can re-run one partition's draw without re-deriving anything, and a
    derivation that later changed would be caught by the recorded integer rather
    than silently followed.
    """
    return random.Random(f"{int(root)}:{partition}").getrandbits(64)


class Draw:
    """Quality-weighted farthest point over one partition, **resumable**.

    The same arithmetic [`choose`] always did, kept as state instead of run to
    completion inside one call. The first pick is **drawn** from the `top_k`
    strongest live locations by `quality^weight`; every pick after it maximizes
    `distance x quality^weight` over everything still outside `radius` of the
    points already drawn.

    **The draw owns its RNG**, and that is not a detail. A re-seat asks the same
    draw for its next point, so an RNG the caller held would either have to be
    threaded through every re-seat round or be re-created — and a re-created one
    hands back the same first pick to a slot whose whole reason for asking is that
    the first pick failed. The RNG belongs where `nearest` and `live` belong,
    which is here.

    Only the first pick is drawn. Everything after it is the arithmetic it always
    was: the seed decides where a partition starts, and the gain and the radius
    decide the rest, so a seeded pass is a different walk over the same rule
    rather than a randomized one.

    Resumable because a slot is not married to its first neighbourhood any more.
    When a slot's whole neighbourhood lands below its head's floor it **re-seats**
    — it asks this draw for the next point, under the same radius and the same
    weighting — and a draw that had to be restarted to answer that would either
    hand back a point it had already given out or forget which regions the radius
    has already refused. The state is the whole point: `nearest` and `live` are
    what make the second point a partition offers continuous with the first.

    A re-seated slot's abandoned point **stays excluded**. It was tried and it
    came up short, and the radius around it is exactly the region the re-seat is
    trying to leave.
    """

    def __init__(
        self,
        indices,
        matrix,
        quality,
        radius: float,
        weight: float,
        seed: int = 0,
        top_k: int = DRAW_TOP_K,
    ):
        import numpy

        self.order = list(indices)
        self.radius = float(radius)
        self.matrix = matrix
        self.taken = 0
        self.seed = int(seed)
        self.top_k = max(1, int(top_k))
        self.rng = random.Random(self.seed)
        if not self.order:
            self.block = None
            return
        self.block = matrix[self.order]
        self.scores = numpy.array(
            [max(0.0, float(quality[i])) for i in self.order], dtype=numpy.float64
        )
        self.weighted = self.scores ** float(weight)
        # Every point starts infinitely far from a chosen set that is still
        # empty, so the first pick is decided by quality alone — which is what
        # the design says it is, rather than by whatever the arithmetic would do
        # with a zero.
        self.nearest = numpy.full(len(self.order), numpy.inf)
        self.live = numpy.ones(len(self.order), dtype=bool)

    def _first(self):
        """The first pick: one of the `top_k` strongest live locations, drawn.

        Ranked on `quality**weight` and not on raw quality, so the same `gamma`
        governs both halves of the draw: at `gamma` of zero — pure farthest point
        — every location ties and the first pick is uniform over the partition,
        which is what "the judge is out of this draw" has to mean at the first
        pick too.
        """
        import numpy

        live = numpy.nonzero(self.live)[0]
        # Stable, so equal scores fall in index order and `top_k=1` is the argmax
        # this draw took before the seed existed.
        order = live[numpy.argsort(-self.weighted[live], kind="stable")]
        top = order[: self.top_k]
        return int(top[self.rng.randrange(len(top))])

    def next(self):
        """The next point this partition offers, or `None` when the radius runs it out."""
        import numpy

        if self.block is None or not self.live.any():
            return None
        first = self.taken == 0
        gains = numpy.where(
            self.live, self.weighted if first else self.nearest * self.weighted, -numpy.inf
        )
        best = self._first() if first else int(numpy.argmax(gains))
        if not numpy.isfinite(gains[best]):
            return None
        pick = Choice(
            index=self.order[best],
            key="",
            partition="",
            quality=float(self.scores[best]),
            distance=None if first else float(self.nearest[best]),
            gain=None if first else float(gains[best]),
        )
        self.taken += 1
        distances = 1.0 - (self.block @ self.block[best])
        self.nearest = numpy.minimum(self.nearest, distances)
        self.live &= distances >= self.radius
        return pick

    def take(self, k: int) -> list:
        """Up to `k` picks, or fewer where the radius runs the partition out."""
        picks = []
        while len(picks) < k:
            pick = self.next()
            if pick is None:
                break
            picks.append(pick)
        return picks

    def tally(self) -> dict:
        """What this draw has spent and what the radius cost, as it stands."""
        return {
            "eligible": len(self.order),
            "chosen": self.taken,
            # The RESOLVED seed, off the draw that actually ran under it, so the
            # number on the record cannot drift from the number in the RNG.
            "draw_seed": self.seed,
            "draw_top_k": self.top_k,
            # What the radius cost: every admitted location of this partition
            # that a chosen point pulled inside the radius, including the chosen
            # points themselves, which is why it is counted as a refusal of the
            # *rest*.
            "refused_by_radius": (
                0 if self.block is None else int((~self.live).sum()) - self.taken
            ),
        }


def choose(
    indices,
    matrix,
    quality,
    k: int,
    radius: float,
    weight: float,
    seed: int = 0,
    top_k: int = DRAW_TOP_K,
) -> tuple[list, dict]:
    """`(picks, tally)` — up to `k` of `indices`, farthest-point under the radius.

    `indices` are positions in `matrix`, whose rows are unit vectors, so cosine
    distance is `1 - dot`.

    Fewer than `k` come back when the radius runs the partition out of eligible
    points, and that is a real answer rather than a failure: it means the
    partition's admitted locations do not hold `k` visibly different places, which
    is exactly the fact an unfilled slot is there to report.

    A whole draw taken at once, for a caller that wants nothing more. The pass
    itself keeps the [`Draw`], because a re-seating slot asks it for one more.
    """
    if k <= 0:
        return [], {
            "eligible": len(list(indices)),
            "chosen": 0,
            "draw_seed": int(seed),
            "draw_top_k": max(1, int(top_k)),
            "refused_by_radius": 0,
        }
    draw = Draw(indices, matrix, quality, radius, weight, seed, top_k)
    return draw.take(k), draw.tally()


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
    #: Which re-seat this slot is on. Zero is the point the farthest-point draw
    #: gave it first; every increment is a neighbourhood that offered it nothing.
    try_index: int = 0
    #: **Every point this slot has stood on**, in order, with what each one
    #: offered and why it was left. The fields above are the *current* try; this
    #: is the history, and it is what makes `below_bar` readable as "k
    #: neighbourhoods in a row failed" rather than as a single verdict.
    tries: list = field(default_factory=list)
    #: True once this slot's partition has no point left outside the radius, so
    #: there is nothing further to re-seat to. Not a reason a slot is unfilled —
    #: the last try's reason is that — but the fact that stopped the loop.
    exhausted: bool = False

    def stand_on(self, pick, keys: list) -> None:
        """Take up a new point and its neighbourhood. The re-seat itself."""
        self.point = pick.key
        self.point_index = int(pick.index)
        self.quality = pick.quality
        self.distance = pick.distance
        self.locations = list(keys)

    def snapshot(self) -> dict:
        """This try, as the record keeps it. Rewritten each seating round.

        Each round re-runs the whole seating, so a slot that filled in round one
        can be refused in round two by a stronger slot taking its place — which
        means the *current* try's outcome is not settled until the last round.
        Written by index rather than appended, so a re-run of the seating
        refreshes the try it is about instead of recording it twice.
        """
        return {
            "try": self.try_index,
            "point": self.point,
            "point_index": self.point_index,
            "point_quality": self.quality,
            "nearest_chosen": self.distance,
            "locations": list(self.locations),
            "fill": dict(self.fill),
            "seated": None if self.seated is None else str(self.seated["candidate"]),
        }

    def record_try(self) -> None:
        """Put [`snapshot`] at this slot's try index, extending the history to reach it."""
        while len(self.tries) <= self.try_index:
            self.tries.append({})
        self.tries[self.try_index] = self.snapshot()


@dataclass
class Bench:
    """The population, the distance, and each partition's live [`Draw`].

    What a **re-seat** needs and nothing else. It exists because the second point
    a slot stands on has to be drawn out of the same state the first one came
    from — the same admitted rows, the same matrix, the same quality readings,
    and above all the same partly-spent draw — and threading six arguments back
    through the loop is how two of them come to disagree.
    """

    rows: list
    matrix: object
    quality: list
    by_partition: dict
    draws: dict
    m: int
    radius: float

    def keys_near(self, pick) -> list:
        """The `m` location keys a point's attempts are spent on, the point first."""
        return [
            str(self.rows[i]["key"])
            for i in neighbourhood(
                pick.index,
                self.by_partition.get(pick.partition, []),
                self.matrix,
                self.quality,
                self.m,
                self.radius,
            )
        ]

    def next_point(self, partition: str):
        """One more point out of a partition's draw, named, or `None` where it is spent."""
        draw = self.draws.get(partition)
        pick = None if draw is None else draw.next()
        if pick is None:
            return None
        pick.key = str(self.rows[pick.index]["key"])
        pick.partition = partition
        return pick


def reseat_slots(slots: list, bench: Bench, log=print) -> dict:
    """Move every unfilled slot onto the next point its partition offers.

    **The gap gallery1 found.** A slot was married to the one point the
    farthest-point draw handed it, and the last points a partition gives out are
    by construction its most remote — so a slot could fail not because the
    partition was out of material but because the three-locations-by-eighteen-
    attempts neighbourhood it happened to land in was hostile to the head that
    owned it. gallery1's eight unfilled slots were all of them the last slot of
    their partition, all `below_bar`, and every one of them sat in a partition
    still holding thousands of admitted locations.

    So an unfilled slot re-seats: it takes the next point under the same radius
    and the same weighting, its neighbourhood is attempted, and the whole seating
    is taken again. `below_bar` after that means *k neighbourhoods in a row
    failed*, which is a statement about the partition; before it, it was a
    statement about one draw.

    **Every unfilled reason moves**, not only `below_bar`. `location_served` is a
    place a stronger slot took and `no_candidates` is a neighbourhood nothing
    rendered from, and the recovery from each is the identical one — stand
    somewhere else. What is never done is the other recovery: nothing is seated
    from below a floor, and no floor moves. Unfilled still beats padded.

    Slots move in id order, which is pick order, so where two slots of one
    partition both need a point the earlier pick takes the nearer one.
    """
    moved, spent = [], []
    for slot in sorted(slots, key=lambda s: s.id):
        if slot.seated is not None:
            continue
        pick = bench.next_point(slot.partition)
        if pick is None:
            slot.exhausted = True
            spent.append(slot)
            continue
        slot.try_index += 1
        slot.stand_on(pick, bench.keys_near(pick))
        moved.append(slot)
    if moved:
        log(
            f"[reseat] {len(moved)} unfilled slot(s) took a new point"
            + (f"; {len(spent)} had none left to take" if spent else "")
        )
    elif spent:
        log(f"[reseat] {len(spent)} unfilled slot(s) have no point left under the radius")
    return {
        "moved": len(moved),
        "exhausted": len(spent),
        "slots": sorted(slot.id for slot in moved),
    }


def plan_slots(
    rows,
    matrix,
    scores,
    n,
    strange_share,
    radius,
    weight,
    m,
    log=print,
    draw_seed: int = 0,
    top_k: int = DRAW_TOP_K,
):
    """Steps 1, 2 and 4 together: `(slots, plan, bench)`.

    One call because the three are one decision. How many slots a partition gets
    decides how many points are chosen in it; how the heads split decides what
    each of those points is asked for; and the chosen points are what the
    attempts and the seats are hung on.

    The [`Bench`] comes back with them because the draws are not finished: an
    unfilled slot asks its partition for one more point, and [`reseat_slots`] is where
    that happens.

    `draw_seed` is the pass's **root** seed and every partition derives its own
    off it ([`partition_draw_seed`]). The plan carries the root and each
    partition's tally carries the resolved integer its draw ran under, because a
    recipe on a record is a claim and an integer is a fact.
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

    bench = Bench(
        rows=rows,
        matrix=matrix,
        quality=quality,
        by_partition=by_partition,
        draws={},
        m=int(m),
        radius=float(radius),
    )

    slots: list[Slot] = []
    tallies, splits = {}, {}
    for name in sorted(allocation, key=partition_index):
        want = int(allocation.get(name, 0))
        if want <= 0:
            continue
        draw = Draw(
            by_partition.get(name, []),
            matrix,
            quality,
            radius,
            weight,
            partition_draw_seed(draw_seed, name),
            top_k,
        )
        bench.draws[name] = draw
        picks = draw.take(want)
        for pick in picks:
            pick.key = str(rows[pick.index]["key"])
            pick.partition = name
        split = head_split(len(picks), strange_share)
        splits[name] = {**split, "planned": want, "chosen": len(picks)}
        for pick, head in zip(picks, head_order(split), strict=True):
            slot = Slot(id=f"{len(slots):04d}", partition=name, head=head, point=pick.key)
            slot.stand_on(pick, bench.keys_near(pick))
            slots.append(slot)
        tally = draw.tally()
        tallies[name] = {**tally, "planned": want}
        log(
            f"[slots] {name:<18} {want} planned, {len(picks)} chosen "
            f"({split[budget_module.STRANGE]} strange / {split[budget_module.SMOOTH]} smooth) "
            f"out of {tally['eligible']:,} admitted"
        )

    plan = {
        "requested": int(n),
        "radius": float(radius),
        "quality_weight": float(weight),
        "draw_seed": int(draw_seed),
        "draw_top_k": max(1, int(top_k)),
        "strange_share": float(strange_share),
        "neighbourhood": int(m),
        "population": counts,
        "release_caps": caps,
        "guaranteed": guaranteed,
        "slots_by_partition": allocation,
        "head_split": splits,
        "selection": tallies,
        # Filled in after the re-seat loop by [`read_retro`], because the set of
        # chosen points is not settled until it stops: a re-seated slot stands
        # somewhere else, and a retro table over the points the first draw handed
        # out would be calibrating the radius against a gallery nobody has.
        "retro": {"by_partition": {}, "overall": []},
    }
    return slots, plan, bench


def read_retro(slots: list, matrix, pairs: int = RETRO_PAIRS) -> dict:
    """The retro table over the points the pass **ended on**, per partition and overall.

    Per partition AND overall, because they answer two questions. The
    per-partition table is where the radius is calibrated — a partition is what a
    slot is allocated in — and the overall one is where cross-partition
    similarity would show up if there were any, which the design deliberately does
    not act on at N=50 and wants visible anyway.
    """
    chosen = [
        Choice(
            index=slot.point_index,
            key=slot.point,
            partition=slot.partition,
            quality=slot.quality,
            distance=slot.distance,
            gain=None,
        )
        for slot in slots
        if slot.point_index >= 0
    ]
    by_partition: dict[str, list] = {}
    for pick in chosen:
        by_partition.setdefault(pick.partition, []).append(pick)
    return {
        "by_partition": {
            name: retro_table(picks, matrix, pairs)
            for name, picks in sorted(
                by_partition.items(), key=lambda cell: partition_index(cell[0])
            )
        },
        "overall": retro_table(chosen, matrix, pairs),
    }


# --------------------------------------------------------------------------- #
# Step 5: the attempts.
# --------------------------------------------------------------------------- #
#: What a planned attempt is framed at. [`REFINED`] is whatever the refine leg
#: decided for that location, which is the original framing wherever it adopted
#: nothing; [`ORIGINAL`] is the recorded framing, always, and it is what the
#: fallback leg asks for after every refined attempt on a slot landed under the
#: bar.
REFINED = "refined"
ORIGINAL = "original"


@dataclass(frozen=True)
class Try:
    """One planned attempt: a location, a head, its place in that head's draw — and
    which framing of the location it is rendered at."""

    key: str
    partition: str
    head: str
    rank: int
    modes_drawn: int
    mode_index: int
    #: [`REFINED`] or [`ORIGINAL`]. Part of the identity of a planned attempt and
    #: not of the [`budget_module.Attempt`] it becomes: the mode draw is seeded off
    #: the location and the head, so the two framings of one location draw the
    #: *same* modes — which is what makes the fallback a controlled comparison
    #: rather than a second roll of the dice.
    framing: str = REFINED

    def plan(self) -> budget_module.Attempt:
        return budget_module.Attempt(
            head=self.head,
            partition=self.partition,
            key=self.key,
            rank=self.rank,
            modes_drawn=self.modes_drawn,
            mode_index=self.mode_index,
        )


def attempt_plan(
    slots: list,
    ranks: dict,
    smooth: int,
    strange: int,
    already=(),
    framing: str = REFINED,
    keys: set | None = None,
) -> list[Try]:
    """Every attempt these slots ask for that `already` does not hold, in key order.

    Two slots whose neighbourhoods overlap ask for the same location's attempts,
    and rendering it twice would buy the same pictures twice — the mode draw is
    seeded off the location and the head, so the second set would be identical.
    So the plan is over the **union** of every slot's locations, and step 6 reads
    whichever of them its own neighbourhood names.

    `already` is the `(key, framing)` pairs a previous round of this pass has
    planned, and it is what makes the plan **extendable rather than rebuilt**. A
    re-seat adds neighbourhoods; the pass appends their attempts to the plan it
    already has, and never re-sorts it. That is not tidiness: an attempt's
    identity is its position in the plan — the candidate log resumes on it, and
    the palette anchor is drawn on it — so a plan whose front half re-ordered
    between two invocations would resume a killed pass onto other attempts'
    pictures.

    The pair and not the key, because one location can be planned twice: once at
    the framing the refine leg chose and once, if the slot standing on it came up
    empty, at the framing the record holds. `keys` narrows the plan to a named
    set, which is how the fallback asks for those locations and no others.
    """
    seen: dict[str, str] = {}
    for slot in slots:
        for key in slot.locations:
            if keys is not None and key not in keys:
                continue
            if (key, framing) not in already:
                seen.setdefault(key, slot.partition)
    out: list[Try] = []
    for key in sorted(seen):
        partition = seen[key]
        rank = ranks.get(key, 0)
        for index in range(max(0, smooth)):
            # The smooth judge owns one coloring, so its draws are distinct
            # PALETTE ANCHORS rather than distinct modes — `modes_drawn` stays at
            # one, and the anchor is what the two attempts differ in.
            out.append(Try(key, partition, budget_module.SMOOTH, rank, 1, 0, framing))
            del index
        for index in range(max(0, strange)):
            out.append(
                Try(key, partition, budget_module.STRANGE, rank, max(1, strange), index, framing)
            )
    return out


# --------------------------------------------------------------------------- #
# Step 5a: the framing every one of those attempts is rendered at.
# --------------------------------------------------------------------------- #
def framing_dir(directory: Path) -> Path:
    """Where the refine leg's node-regime scan pictures live, under the pass."""
    return Path(directory) / "framings"


def location_scorer(device: str, log=print):
    """The shipped location head, reading at the node regime. One per pass.

    Constructed eagerly by [`run`] rather than on the first scan: the constructor
    resolves the artifact and the stack that reads it, so a machine with no
    weights refuses before the pass spends a render, while the model itself is
    still loaded lazily on the first batch.
    """
    from fractal_wallpapers.discovery import scoring as discovery_scoring
    from fractal_wallpapers.models import tiles as tile_module

    return discovery_scoring.LocationScorer(
        workers=1, device=device, regime=tile_module.NODE_REGIME, log=log
    )


def enforce_scan_identity(log=print) -> dict:
    """Refuse unless the scan's frames are the pictures this head was trained on.

    The whole design rests on one claim: [`engine.screen`] at the node regime
    draws the tile the location head reads. The walk already stands on that claim
    and checks it at a run's start; the pass stands on it too and checks it here,
    before it spends a frame — an unchecked scan would score every candidate
    framing off a distribution nobody trained the head on and record the result as
    a framing decision.
    """
    from fractal_wallpapers.discovery import identity
    from fractal_wallpapers.models import location_view
    from fractal_wallpapers.models import tiles as tile_module

    try:
        return identity.enforce(
            location_view.canonical_map(),
            tile_module.NODE_REGIME.tile[0],
            tile_module.NODE_REGIME,
            log=log,
        )
    except identity.IdentityBroken as broken:
        raise PassRefused(
            f"the framing scan cannot be taken on this checkout: {broken} Run with "
            f"--no-refine to take the pass on the framings the pool records."
        ) from broken


def refine_framings(
    keys,
    by_key: dict,
    directory: Path,
    *,
    scorer,
    scores: dict,
    margin: float,
    framings: dict | None = None,
    log=print,
) -> tuple[dict, list]:
    """`(framings, new)` — every named location's framing decided, resuming the log.

    Called once a round, over the locations that round's neighbourhoods added. A
    location already in the log keeps the decision it was given: the scan is seven
    node-regime renders and a re-seat round that re-scanned the locations it
    shares with the round before it would pay for them twice and could answer
    differently, which would re-frame attempts that are already on disk.
    """
    framings = (
        dict(framings)
        if framings
        else framing_module.completed(framing_module.log_path(directory), log)
    )
    wanted = [key for key in sorted(set(keys)) if key not in framings]
    if not wanted:
        return framings, []
    made = framing_module.refine(
        [by_key[key] for key in wanted],
        directory=framing_dir(directory),
        scorer=scorer,
        margin=margin,
        scores=scores,
        log=log,
    )
    for record in made:
        framing_module.append(framing_module.log_path(directory), record)
        framings[record["key"]] = record
    return framings, made


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


def make_attempts(
    directory: Path,
    plan: list,
    by_key: dict,
    seed: int,
    device: str,
    log=print,
    framings: dict | None = None,
):
    """Run every planned attempt, resuming whatever this pass already recorded.

    `(rows, counts)`. The candidate log is the record that an attempt is done —
    the same rule a run follows, and for the same reason: a picture on disk is
    evidence that a render wrote bytes and nothing else.

    `framings` is the refine leg's decision per location, and it does two things:
    it re-frames the row the colorizer is handed where a refinement was adopted,
    and it puts the whole before-and-after on every row that comes out. A row a
    later reader picks up therefore carries both viewports and both of the head's
    readings of them, whichever one it was rendered at.
    """
    log_path = directory / "candidates.jsonl"
    done = run_module.completed_attempts(log_path, log)
    carried = sum(1 for index in done if index < len(plan))
    if carried:
        log(f"[attempts] {carried} of {len(plan)} already recorded; carrying them across")
    anchors = colorize.anchors(colorize.pool(), max(1, len(plan)), seed)
    # Only what THIS plan asked for. A resumed pass's log already holds the
    # attempts its later re-seat rounds made, and round 0 asking the log what it
    # has would otherwise seat out of a pool the same round could not have seen
    # on a fresh run. Today the neighbourhood filter drops those rows anyway and
    # the two runs agree exactly; this is what keeps that true when the filter
    # changes rather than leaving it as a coincidence.
    rows = [row for index, row in sorted(done.items()) if index < len(plan)]
    counts = {"planned": len(plan), "resumed": len(done), "made": 0, "failed": 0}
    colorizer, seconds = None, 0.0

    for index, planned in enumerate(plan):
        if index in done:
            continue
        if colorizer is None:
            colorizer = colorize.Colorizer(directory, seed, device, log)
        started = time.monotonic()
        row = colorize.annotate(
            colorizer.attempt(
                planned.plan(), framed(by_key, framings, planned), anchors[index], index
            )
        )
        row["framing"] = framing_block(framings, planned)
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
    counts["dropped_candidate_jpegs"] = sweep_candidates(directory, _picked(rows, directory))
    counts["seconds"] = round(seconds, 1)
    counts["seconds_per_attempt"] = round(seconds / counts["made"], 2) if counts["made"] else None
    rows.sort(key=lambda row: row["attempt"])
    return rows, counts


# --------------------------------------------------------------------------- #
# Step 6: what takes each slot.
# --------------------------------------------------------------------------- #
def framed(by_key: dict, framings: dict | None, planned: Try) -> dict:
    """The row the colorizer is handed for one planned attempt.

    The recorded framing where the plan asks for it or nothing was adopted, and
    the refined one where it was. One place, so a row can never be re-framed on
    one path and left alone on another.
    """
    row = by_key[planned.key]
    if planned.framing == ORIGINAL:
        return row
    record = (framings or {}).get(planned.key)
    return row if record is None else framing_module.apply_to(row, record)


def framing_block(framings: dict | None, planned: Try) -> dict | None:
    """The before-and-after this attempt carries, or `None` where nothing scanned it."""
    record = (framings or {}).get(planned.key)
    return None if record is None else framing_module.block(record, planned.framing)


def _picked(rows: list, directory: Path) -> set:
    """`{field/map.jpg}` for every palette the pass's verdicts actually used.

    Off the attempt rows themselves and not off the location table, because one
    location can be attempted at two framings and each of those is a field of its
    own — a sweep that resolved the field through the table would delete the
    fallback leg's working the moment the two disagreed.
    """
    kept = set()
    for row in rows:
        if not row.get("colormap"):
            continue
        field_name = colorize.field_of(row, directory / "fields").stem
        kept.add(f"{field_name}/{row['colormap']}.jpg")
    return kept


def picture_id(row: dict, pool: dict | None = None) -> str:
    """The id of the PICTURE a pool row is about, `<run>_<candidate>`.

    Not the id of the row. A gallery pass re-records a candidate it seated out of
    the standing pool under its own pass id, so one render can arrive on three
    rows — the run that made it, the pass that shipped it, and the pass that
    shipped it again — and a pool keyed by row is a pool holding that render three
    times. `<run>_<candidate>` off [`rescore.origin_of`], which is the same walk
    down `source` that resolves a row to the render on disk, because "whose
    picture is this" has to have exactly one answer.

    `pool` is every row the caller can see, keyed by `key`, and it is what makes
    the walk more than one hop. Without it a row two passes deep resolves to the
    intermediate rather than to the picture — which is how the compounding hid.
    """
    from fractal_wallpapers.curation import rescore

    run, candidate = rescore.origin_of(row, pool)
    return f"{run}_{candidate}"


def candidate_of_pool_row(row: dict, pool: dict | None = None) -> dict:
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

    `candidate` is the **picture's** id ([`picture_id`]) and not the row's, which
    is what stops the name growing a level per pass: this id is what a seat is
    stamped with, so a re-stamp of a re-stamp resolves back to the same render
    rather than reading as a new one. `source` stays the row this was read from —
    the link, not the destination — because that is what [`rescore.origin_of`]
    walks and what a reader joining a pass to what it decided over needs.
    """
    location = row.get("location") or {}
    recipe = row.get("recipe") or {}
    palette = row.get("palette") or {}
    read = row.get("scores_current") or row.get("scores") or {}
    return {
        "attempt": None,
        "candidate": picture_id(row, pool),
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
        # Where the picture this row was decided on sits inside its own run's
        # directory. Carried because the `below_floor` sheet shows the best thing
        # a slot passed over, and a candidate out of the standing pool is as
        # likely to be that as one of this pass's attempts.
        "picture": row.get("picture"),
        # Which framing of its location this row was rendered at, and what the
        # location head made of the other one. Carried so the near-duplicate
        # grouping can key on the ORIGINAL frame for a standing row the same way
        # it does for one of this pass's own attempts.
        "framing": row.get("framing"),
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

    Through [`rescore.block`] and never spelled out here. This used to build the
    block itself and left `judge` off it, which made the pool's rows two shapes —
    a reader asking for the judge got an answer on every row but the ones a
    gallery pass had made.
    """
    from fractal_wallpapers.curation import rescore

    return {
        **row,
        "candidate": f"{row['attempt']:04d}",
        "source": {"run": pass_id, "candidate": f"{row['attempt']:04d}", "key": None},
        "scores_current": rescore.block(row.get("head"), row),
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

    floor_of = {head: floors.gallery_floor(head) for head in budget_module.KINDS}
    used: dict[str, int] = {}
    order = sorted(range(len(slots)), key=lambda i: _seat_order(slots, i))
    for slot in slots:
        # The whole seating is taken again after every re-seat, so this runs more
        # than once over the same slots. A slot filled in an earlier round can be
        # refused in a later one — the location rule is checked against a counter
        # that a re-seated slot's new place may now reach first — and a seat left
        # standing from the previous round would be a seat nothing re-decided.
        slot.seated, slot.unfilled, slot.fill = None, None, {}
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
        # The best thing this neighbourhood held, whatever the floor said about
        # it. Kept because it is the evidence an unfilled slot is FOR: the
        # `below_floor` sheet puts it beside the partition's best unchosen
        # candidate pool-wide, and "just under the floor while the partition holds
        # something well over it" and "nothing here at all" are different findings.
        slot.fill["best"] = _best_of(pool)
        slot.record_try()

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


def floor_key(candidate: dict):
    """Nearest the head's floor first: `P(>=3)`, then `P(>=4)`, then the id.

    **Not [`rank_key`], and the difference is the whole point.** `rank_key` orders
    by `P(>=4)` because that is the question a slot asks of a candidate it might
    seat; a **floor** acts on `P(>=3)`, and the two orderings genuinely disagree —
    a candidate at `P(>=4) 0.60, P(>=3) 0.62` outranks one at `0.50, 0.90` and is
    the one that fails a bar between those two `P(>=3)` values.

    So the witness an unfilled slot puts on the record is chosen on the floor's
    own axis. "The best candidate here scored 0.62 against the acting floor" is a
    claim about how close a neighbourhood came, and answering it with the
    highest-ranked row instead would understate the gap — reporting a slot as
    further from its bar than it was.
    """
    return (
        -(candidate.get("p_ge3") if candidate.get("p_ge3") is not None else -1.0),
        -(candidate.get("p_ge4") if candidate.get("p_ge4") is not None else -1.0),
        str(candidate.get("candidate")),
    )


def _best_of(pool: list) -> dict | None:
    """The candidate of a slot's pool that came nearest its head's floor.

    On [`floor_key`], because this is the evidence behind an unfilled slot and
    the floor is what it is evidence about.

    Small deliberately: it lands on every slot of the pass record, and a whole
    candidate row per try is the shape that made a pass cost megabytes.
    """
    if not pool:
        return None
    best = min(pool, key=floor_key)
    return {
        "candidate": str(best["candidate"]),
        "run": (best.get("source") or {}).get("run"),
        "key": best.get("key"),
        "head": best.get("head"),
        "mode": best.get("mode"),
        "colormap": best.get("colormap"),
        "p_ge3": best.get("p_ge3"),
        "p_ge4": best.get("p_ge4"),
        "picture": best.get("picture"),
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
    """What the near-duplicate grouping needs off a candidate: the location.

    The **original** viewport where the row carries one, which is the whole of the
    identity rule the refine leg is held to: a re-framed attempt is a second
    picture of the same place, and one-wallpaper-per-location has to count it
    against that place. Grouping on the frame that was actually rendered would
    let a location the pass widened by half take a second seat beside itself.
    """
    original = ((candidate.get("framing") or {}).get("original") or {}).get("viewport")
    return {
        "family": candidate.get("family"),
        "viewport": original or candidate.get("viewport"),
    }


def pool_candidates(slots: list, pass_id: str, rows: list | None = None) -> list[dict]:
    """The pool rows this pass may **seat**: on one of its locations, and its own.

    THE ruling, and it is one predicate: **locations are cumulative, candidates
    are per-pass**. A location is discovered ground and the pass selects over
    every one the pool has accumulated; a candidate is a two-second recolour of
    one, and a pass ships only the recolours it took itself. So a row has to stand
    on one of this pass's locations *and* have been made by this pass.

    What that costs and why it is worth it. gallery3 seated 66 of its 150 slots on
    standing rows, and in 59 of those the standing row simply outranked the pass's
    own best at the same place — not because the pass had made nothing there. The
    reason there was so much standing material exactly where it looked is that the
    draw was deterministic: 98 of its 150 chosen points were points gallery2 had
    already chosen. A pass that seats another pass's recolours at a point both
    passes chose is not selecting over a larger pool, it is running half the
    draws and calling the older half free.

    In the normal path this therefore comes back **empty**: [`pool_rows`] has
    already set this pass's own rows aside — they arrive in memory as the attempt
    leg makes them — so nothing left in the pool was made here. That is the rule
    working, not the function idling, and it is why the predicate lives here
    rather than at a call site: [`below_floor_sheet`] is handed the *un-narrowed*
    [`pool_rows`] and must keep seeing every standing row, because its whole claim
    is about the material a slot's neighbourhoods did not reach.

    `rows` is [`pool_rows`] already read, for a caller asking this once a re-seat
    round: the neighbourhoods move between rounds and the pool does not.
    """
    wanted = {key for slot in slots for key in slot.locations}
    everything = pool_rows(pass_id) if rows is None else rows
    return [
        candidate
        for candidate in everything
        if str(candidate["key"]) in wanted and run_of(candidate) == str(pass_id)
    ]


def pool_rows(pass_id: str) -> list[dict]:
    """Every judged candidate in the accumulated pool, one row per PICTURE.

    The pool as it stands, and **not** the set this pass may seat: that is
    [`pool_candidates`], which is this narrowed to the slots' neighbourhoods and
    to the rows this pass made itself. The two are split because the re-seat loop
    asks the seating question repeatedly — the neighbourhoods move every round,
    the pool does not — and because the `below_floor` sheet is answered out of
    *this* one. Its whole claim is about the material a slot's neighbourhoods did
    **not** reach, and a pool cut to what the pass may seat would answer it with
    the pass's own attempts.

    Three exclusions, and each is a different fact. A row this pass wrote is
    already in hand, so reading it back would double it. A row a person
    **rejected** was taken out of service deliberately, and a sheet that offered
    it as the partition's best unchosen candidate would be re-opening the review.
    A row with no score never got one — a failed render is a decision with a
    reason and no number — and ranking it against a wallpaper is the comparison
    the record exists to prevent.

    **Two stores, because the pool is in two places.** A run records every scored
    attempt in the tracked release store, and an earlier *pass* records its
    attempts in [`curation.gallery_store`] instead — untracked,
    manifest-described, and every bit as much a coloured judged candidate standing
    on a location.

    **Deduped on the picture and not on the row** ([`picture_id`]). One render
    lands on as many rows as there are decisions about it: the run that made it,
    the pass that seated it out of the pool, the pass that seated it again. Those
    rows carry three different `<run>_<candidate>` names for one wallpaper, and a
    pool keyed by name ranks the same picture two and three times and can seat it
    into two slots. The whole store is indexed first so the walk down `source` has
    every link it needs — a row two passes deep resolves to the picture only if
    the row between them is in hand.

    Where a picture arrives more than once the row kept is the one that **is** the
    picture — the run's or the pass's own attempt — rather than a later pass's
    re-stamp of it. Both carry the same scores, because a re-stamp copies the
    reading it seated on; what only the original carries is its own candidate
    render, which is what the `below_floor` sheet shows and what `rescore` reads.
    """
    everything = [*records.read_decisions(records.RELEASE), *gallery_store.read()]
    index = {str(row["key"]): row for row in everything}
    at: dict[str, int] = {}
    original: set[str] = set()
    out: list[dict] = []
    for row in everything:
        if row.get("run") == pass_id or records.is_rejected(row):
            continue
        candidate = candidate_of_pool_row(row, index)
        if candidate.get("p_ge3") is None or candidate.get("head") not in budget_module.KINDS:
            continue
        identity = str(candidate["candidate"])
        # A row IS the picture when its own `<run>_<candidate>` name is the id the
        # walk resolved to; anything else is a later pass's re-stamp of it.
        itself = f"{row['run']}_{row['candidate']}" == identity
        seen = at.get(identity)
        if seen is None:
            at[identity] = len(out)
            out.append(candidate)
        elif itself and identity not in original:
            out[seen] = candidate
        if itself:
            original.add(identity)
    return out


# --------------------------------------------------------------------------- #
# Step 7: the winners, at full size, and only the winners.
# --------------------------------------------------------------------------- #
def skip_winners(slots: list, log=print) -> dict:
    """Step 7, not taken. Mark every seat as having no full-size render yet.

    The **dev-and-review affordance** the attempt leg's `--no-attempts` is not:
    skipping the release leg costs the pass none of its decisions. Every slot is
    seated the same way on the same candidates; what is not spent is 25 s a
    winner making a 2560x1440 picture of a choice a person can judge perfectly
    well off the 640x360 render the judge itself read.

    The seats are recorded [`records.UNRENDERED`] — took the slot, no picture,
    nothing failed — and the contact sheets fall back to each winner's candidate
    render and say which resolution they are showing. Re-running the same pass id
    without the flag renders the winners and lifts the rows to `released`; the
    attempts are all still on disk, so that second invocation costs the release
    leg and nothing else.
    """
    seated = 0
    for slot in slots:
        if slot.seated is None:
            continue
        seated += 1
        slot.seated["release_picture"] = None
        slot.seated["release_autolevel"] = None
        # What tells [`_release_row`] this is a choice rather than a dead render.
        slot.seated["release_skipped"] = True
    log(f"[render] SKIPPED: --no-full-size, so {seated} seat(s) have no full-size picture yet")
    return {
        "skipped": "--no-full-size",
        "geometry": {"resolution": list(RESOLUTION), "supersample": SUPERSAMPLE},
        "reused": 0,
        "workers": 0,
        "counts": {
            "planned": 0,
            "resumed": 0,
            "made": 0,
            "failed": 0,
            "not_started": seated,
        },
        "seconds": 0.0,
        "seconds_per_full_size": None,
        "not_started": [],
    }


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
    the picture's own id ([`picture_id`]) and this pass's `run`, with `source`
    naming the row it was seated from. That is not a duplicate: the earlier row
    records a run deciding what to keep, and this one records the gallery pass
    deciding what to ship — two decisions about one picture, taken by two passes
    out of two populations. The id does not grow a level per pass, which is what
    lets the next pass read all three rows back as one wallpaper.
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
        {
            **records.decision(
                run=pass_id,
                stage=records.GATE,
                candidate=f"{row['attempt']:04d}",
                verdict="kept" if row.get("p_ge3") is not None else "dropped",
                row=row,
                reason=row.get("error"),
                picture=row.get("picture"),
            ),
            # Beside the decision rather than inside it: `location.viewport` is
            # the frame this row was rendered at, whichever one that is, and this
            # is the other one plus what the head said about each. A later pass
            # seats these rows, so the provenance has to survive the store.
            "framing": row.get("framing"),
        }
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

    **The `candidate` this stamps is the picture's id**, never the id of the row
    the seat was read off ([`picture_id`]). The two used to be the same thing and
    the difference is a level of prefix per pass: a pass that stamped what it read
    turned `gallery2_0110` into `gallery3_gallery2_0110`, the pass after it into
    `gallery4_gallery3_gallery2_0110`, and each of those names read back as a
    picture of its own. `run` says which pass took the decision and `source` says
    which row it took it over, so nothing is lost by the id not repeating them.
    """
    picture = candidate.get("release_picture")
    if picture:
        verdict, reason = records.RELEASED, None
    elif candidate.get("release_skipped"):
        # Nothing failed here: the pass was told not to make the picture. The
        # seat is as real as any other and the row says so, which is what keeps
        # `killed` meaning "the render died".
        verdict, reason = records.UNRENDERED, records.UNRENDERED_REASON
    else:
        verdict, reason = records.KILLED, records.KILLED_REASON
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
    # Both framings and both of the location head's readings, on the row the
    # collection ships. `location.viewport` is the frame the full-size picture was
    # rendered at — the refined one wherever one was adopted — and this says what
    # it was before and what the head made of the difference.
    row["framing"] = candidate.get("framing")
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
# The four sheets, for Matt's eye.
#
#   sheet          the gallery: partition then rank, slot-labelled, unfilled in place
#   runners_up     what the radius refused, at the neutral render it refused it on
#   below_floor    every unfilled slot's tries, against what its partition holds
#   closest_pairs  the retro table with the pictures attached
#
# Two of them are about what the pass CHOSE and two are about what it did not, and
# the second pair is the half that says whether a number on the first pair is a
# fact about the pool or a fact about where the pass happened to look.
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
        source, what = _seated_picture(seated, directory)
        body = (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )
        facts = [
            what,
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


def _seated_picture(seated: dict, directory) -> tuple:
    """`(path, what it is)` for a winner: the full-size render, or the candidate.

    A pass run with `--no-full-size` has taken every decision and made no
    wallpaper, so the sheet shows the 640x360 render the judge actually read and
    **says which one it is**. Showing a candidate under a caption that implies
    2560x1440 is the exact confusion `records.UNRENDERED` exists to keep out of
    the record, and a sheet is read by the same person.
    """
    picture = seated.get("release_picture")
    if picture:
        return Path(directory) / picture, f"{RESOLUTION[0]}x{RESOLUTION[1]} ss{SUPERSAMPLE}"
    candidate = candidate_picture(seated)
    return candidate, (
        f"NO FULL-SIZE RENDER YET - the {colorize.RESOLUTION[0]}x{colorize.RESOLUTION[1]} "
        f"candidate the decision was taken on"
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


def candidate_picture(candidate: dict) -> Path | None:
    """Where one candidate's own picture is, whichever run made it.

    Every pool row names its picture relative to the directory of the run that
    wrote it, and a gallery pass's directory IS a run directory ([`pass_dir`]) —
    which is the whole reason it is one. So one join answers for this pass's
    attempts and for six runs' candidates alike.
    """
    name = candidate.get("picture")
    where = run_of(candidate)
    if not name or not where:
        return None
    return run_module.run_dir(str(where)) / str(name)


def run_of(candidate: dict) -> str | None:
    """Which run made a candidate, whichever of the two shapes it arrived in.

    A flat candidate names it under `source`; the small dict a slot's try keeps
    ([`_best_of`]) has already resolved it to `run`. One reader, because a card
    that read only one of them prints `None|0417` for half the pool.
    """
    return candidate.get("run") or (candidate.get("source") or {}).get("run")


def best_unchosen(candidates: list, seated: set, partition: str, head: str) -> dict | None:
    """The partition's strongest candidate on one head that this pass did not seat.

    **Pool-wide** — over every candidate the pass could see, not only the ones
    standing on a slot's neighbourhoods. That is the point of it: an unfilled slot
    claims the pool had nothing for it, and the honest check on that claim is what
    the same partition and the same head hold *anywhere*. A number above the floor
    here beside an unfilled slot is a reach problem; nothing above the floor
    anywhere is a supply fact.

    On [`floor_key`] for the same reason [`_best_of`] is: the comparison this
    card exists to make is against a floor, so both sides of it are read on the
    floor's axis.
    """
    pool = [
        candidate
        for candidate in candidates
        if str(candidate.get("partition")) == partition
        and str(candidate.get("head")) == head
        and str(candidate.get("candidate")) not in seated
    ]
    return min(pool, key=floor_key) if pool else None


def below_floor_sheet(pass_id: str, slots: list, candidates: list, output) -> Path:
    """Every unfilled slot, every neighbourhood it stood on, and what the partition held.

    The sheet the re-seat loop is answerable to. Per unfilled slot it shows the
    **best candidate each try produced**, with its score against the floor that
    refused it, and beside them the partition's best unchosen candidate on the
    same head pool-wide. Three cards under a floor and a fourth well over it is a
    slot that looked in the wrong places; four cards under it is a partition whose
    material does not reach the bar, which is the finding an unfilled slot exists
    to make.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    seated = {str(slot.seated["candidate"]) for slot in slots if slot.seated is not None}
    unfilled = [slot for slot in slots if slot.seated is None]
    unfilled.sort(key=lambda s: (partition_index(s.partition), s.id))
    sections = []
    for slot in unfilled:
        floor = floors.gallery_floor(slot.head)
        cards = [
            _candidate_card(
                (attempt.get("fill") or {}).get("best"),
                floor,
                sheet_module,
                f"try {attempt.get('try', index)}",
                f"point {attempt.get('point')} - "
                + ((attempt.get("fill") or {}).get("why") or "seated"),
            )
            for index, attempt in enumerate(slot.tries)
        ]
        cards.append(
            _candidate_card(
                best_unchosen(candidates, seated, slot.partition, slot.head),
                floor,
                sheet_module,
                f"{slot.partition} pool-wide",
                "the partition's best unchosen candidate on this head, anywhere in the pool",
            )
        )
        sections.append(
            f"<h2>slot {html.escape(slot.id)} - {html.escape(slot.partition)} - "
            f"{html.escape(slot.head)} - {html.escape(str(slot.unfilled))}"
            f"{' - the draw is spent' if slot.exhausted else ''}</h2>"
            f"<p class='lede'>{len(slot.tries)} neighbourhood(s) tried; floor "
            f"{floor.name} at {floor.value:g}.</p>"
            "<div class='grid'>" + "".join(cards) + "</div>"
        )
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>gallery {pass_id} below the floor</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>gallery {pass_id} - the slots that stayed empty</h1>",
        f"<p class='lede'>{len(unfilled)} unfilled slot(s). For each, the best candidate every "
        f"neighbourhood it stood on produced, and then the partition's best unchosen candidate "
        f"on the same head pool-wide - the proof of whether the partition had supply the slot "
        f"never reached.</p>",
        *(sections or ["<p class='lede'>Every slot filled.</p>"]),
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _candidate_card(candidate: dict | None, floor, sheet_module, title: str, note: str) -> str:
    import html

    if not candidate:
        return (
            f'<figure><div class="frame"><div class="missing">no candidate</div></div>'
            f"<figcaption><b>{html.escape(title)}</b>"
            f"<ul><li>{html.escape(note)}</li></ul></figcaption></figure>"
        )
    picture = candidate_picture(candidate)
    body = (
        f'<img src="{sheet_module.thumbnail(picture)}" alt="">'
        if picture is not None and picture.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    clears = floor.clears(candidate.get("p_ge3"))
    facts = [
        note,
        f"P(>=3) {_number(candidate.get('p_ge3'))} against the {floor.value:g} floor - "
        + ("CLEARS" if clears else "below"),
        f"P(>=4) {_number(candidate.get('p_ge4'))}",
        f"{candidate.get('mode')} - {candidate.get('colormap')}",
        f"{run_of(candidate)}|{candidate.get('candidate')}",
        f"key {candidate.get('key')}",
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(title)}</b><ul>{caption}</ul></figcaption></figure>"
    )


#: How many before-and-after pairs the `refined_pairs` sheet lays out. Enough to
#: form a view of the head's framing taste at one reading; a pass at n=50 scans
#: three times this many locations, so the sheet is a sample and says so.
REFINED_PAIRS = 40


def refined_pairs_sheet(pass_id, records_, directory, output, margin=framing_module.MARGIN):
    """The framing scan, laid out for the eye that is the actual verdict on it.

    Original left, the window's best right, both at the node regime the head read
    them at, both scores under each. **The adopted ones first**, best gain first,
    because those are the frames that went on to attempts and are the decision
    being reviewed; then, where there is room, the ones the margin refused — which
    is the only way to see whether Δ is set where it should be. A sheet showing
    only what was adopted could not answer the question the margin exists for.

    No head decides whether a framing is a good framing. It decides the score the
    margin acts on, and this page is where a person disagrees with it.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    directory = Path(directory)
    adopted = sorted(
        (record for record in records_ if record["adopted"]),
        key=lambda record: -(record["gain"] or 0.0),
    )
    refused = sorted(
        (
            record
            for record in records_
            if not record["adopted"] and record.get("best") and record.get("original")
        ),
        key=lambda record: -(record["gain"] if record["gain"] is not None else -1.0),
    )
    shown = [*adopted[:REFINED_PAIRS], *refused[: max(0, REFINED_PAIRS - len(adopted))]]
    sections = [_pair_section(record, directory, sheet_module, html) for record in shown]
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>gallery {pass_id} refined framings</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>gallery {pass_id} - {len(shown)} framings, before and after</h1>",
        "<p class='lede'>"
        f"{len(adopted)} of {len(records_)} location(s) adopted a new framing at a margin of "
        f"{margin:g} on P(&gt;=4); {len(shown)} pair(s) shown, adopted first. Left is the frame "
        "the pool records and right is the best the window found - both at the node regime the "
        "location head read them at, which is the picture the decision was taken on and not the "
        "wallpaper that comes out of it. A row marked REFUSED is one the margin turned away, and "
        "it is there so the margin can be judged as well as the framings.</p>",
        *(sections or ["<p class='lede'>Nothing was scanned.</p>"]),
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _pair_section(record: dict, directory: Path, sheet_module, html) -> str:
    gain = record["gain"]
    verdict = (
        f"ADOPTED - {record['slug']}"
        if record["adopted"]
        else f"REFUSED - {record['refused']} - would have been {record['slug']}"
    )
    head = (
        f"<h2>{html.escape(verdict)}"
        + (f" - gain {gain:+.4f} on P(&gt;=4)" if gain is not None else "")
        + f"<br><small>{html.escape(record['key'])}</small></h2>"
    )
    cards = [
        _framing_card(record["original"], "original", record, directory, sheet_module, html),
        _framing_card(record["best"], "the window's best", record, directory, sheet_module, html),
    ]
    return head + "<div class='grid'>" + "".join(cards) + "</div>"


def _framing_card(side, what: str, record: dict, directory: Path, sheet_module, html) -> str:
    if side is None:
        missing = f'<div class="missing">no {html.escape(what)}</div>'
        return f'<figure><div class="frame">{missing}</div></figure>'
    source = directory / str(side.get("picture") or "")
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if side.get("picture") and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    viewport = side["viewport"]
    facts = [
        f"P(>=4) {_number(side.get('p_ge4'))}, P(>=3) {_number(side.get('p_ge3'))}",
        f"width {viewport['width']}, maxiter {side.get('maxiter')}",
        f"centre {viewport['center_re']}, {viewport['center_im']}",
        f"gates: {side.get('fate')}",
    ]
    if what != "original":
        facts.insert(1, f"x{record['width_scale']:g} width, move {record['slug'].split('_')[-1]}")
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(what)}</b><ul>{caption}</ul></figcaption></figure>"
    )


def closest_pairs_sheet(pass_id, slots, rows, matrix, directory, output, pairs=CLOSEST_PAIRS):
    """The `k` closest chosen pairs in the whole gallery, side by side. The eye-check.

    The retro table says how near the two nearest chosen points ended up; this is
    that number with the two pictures under it, which is the only form in which
    the question it asks — *are these two wallpapers or one* — can actually be
    answered. Across ALL partitions, because the radius acts inside a partition
    and the pairs that come out nearest are therefore the cross-partition ones,
    which is exactly the similarity nothing in the pass is looking at.

    A filled slot shows its wallpaper; an unfilled one shows the neutral render of
    the point it stands on, which is the picture the distance was measured on
    either way.
    """
    import html

    from fractal_wallpapers.curation import neutral
    from fractal_wallpapers.curation import sheet as sheet_module

    by_point = {slot.point: slot for slot in slots if slot.point_index >= 0}
    row_of = {str(row["key"]): row for row in rows}
    neutral_dir = neutral.neutral_dir()
    table = read_retro(slots, matrix, pairs)["overall"]
    sections = []
    for cell in table:
        cards = [
            _pair_card(
                by_point.get(side["key"]),
                row_of.get(side["key"]),
                directory,
                neutral_dir,
                sheet_module,
            )
            for side in (cell["a"], cell["b"])
        ]
        same = cell["a"]["partition"] == cell["b"]["partition"]
        sections.append(
            f"<h2>{cell['cosine_distance']:.4f} - {html.escape(cell['a']['partition'])} / "
            f"{html.escape(cell['b']['partition'])}"
            f"{' - same partition' if same else ' - across partitions'}</h2>"
            "<div class='grid'>" + "".join(cards) + "</div>"
        )
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>gallery {pass_id} closest pairs</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>gallery {pass_id} - the {len(table)} closest chosen pairs</h1>",
        "<p class='lede'>The retro table with its pictures attached. If any two of these read "
        "as one picture, the radius is too small - and a pair marked across partitions is one "
        "the radius never looked at, because it acts inside a partition only.</p>",
        *(sections or ["<p class='lede'>Fewer than two points were chosen.</p>"]),
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _pair_card(slot, row, directory: Path, neutral_dir: Path, sheet_module) -> str:
    import html

    if slot is None:
        return '<figure><div class="frame"><div class="missing">not chosen</div></div></figure>'
    seated = slot.seated
    if seated is not None:
        source, what = _seated_picture(seated, directory)
        what = f"the seated wallpaper - {what}"
    else:
        source = neutral_dir / str((row or {}).get("picture") or "")
        what = f"UNFILLED - {slot.unfilled} - the chosen point's neutral render"
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if source is not None and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    facts = [what, f"{slot.partition} - {slot.head}", f"key {slot.point}"]
    if seated is not None:
        facts.insert(1, f"{seated.get('mode')} - {seated.get('colormap')}")
        facts.insert(
            2,
            f"P(>=4) {_number(seated.get('p_ge4'))}, P(>=3) {_number(seated.get('p_ge3'))}",
        )
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>slot {html.escape(slot.id)}</b><ul>{caption}</ul></figcaption></figure>"
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
    reseat: int = RESEAT_TRIES,
    no_attempts: bool = False,
    full_size: bool = True,
    refine: bool = True,
    margin: float = framing_module.MARGIN,
    seed: int = DEFAULT_SEED,
    draw_seed: int | None = None,
    draw_top_k: int = DRAW_TOP_K,
    workers: int = release.DEFAULT_WORKERS,
    device: str = "auto",
    log=print,
) -> dict:
    """One gallery pass, end to end. Returns the pass's own record.

    **Takes the pass id first** ([`claim_pass`]), because two launches of one pass
    id share one `framings/` directory and the collision is silent for minutes.
    [`curation.framing.screen`] has the engine name each frame by its position in
    the batch and renames it afterwards, so two processes rename each other's
    files and both die on a missing one, several minutes in, with a log that reads
    like one pass behaving strangely.

    `no_attempts` skips step 5, and since candidates are per-pass
    ([`pool_candidates`]) that leaves the pass with nothing to seat: every slot
    comes back unfilled and the numbers about how full the gallery is are about
    nothing at all. What it still does whole is steps 1 to 4 and everything read
    off them — the slot allocation, the head split, the draw, the retro table and
    the two embedding sheets — which is what somebody iterating on the
    **selection** is looking at, and it costs no render to get. A **dev
    affordance** and never how a pass is really run.

    `draw_seed` is the root the point draws run under; absent, one is drawn and
    written to the record, because a pass nobody seeded is still a pass somebody
    has to be able to run again. `seed` is the other one and they are not
    interchangeable: that one is on every pass record already, meaning the palette
    anchors and the mode draws.

    `refine` is step 5a and it is **on**: before a location's attempts render, its
    framing is scanned and the best one adopted if it beats the recorded framing
    by `margin` ([`curation.framing`]). `refine=False` is the pass this repository
    took before the step existed, exactly — same plan, same seed, same attempts.
    """
    pass_id = str(pass_id or next_pass_id())
    held = claim_pass(pass_id, log)
    try:
        return _take(
            pass_id,
            n=n,
            radius=radius,
            quality_weight=quality_weight,
            strange_share=strange_share,
            attempts=attempts,
            reseat=reseat,
            no_attempts=no_attempts,
            full_size=full_size,
            refine=refine,
            margin=margin,
            seed=seed,
            draw_seed=draw_seed,
            draw_top_k=draw_top_k,
            workers=workers,
            device=device,
            log=log,
        )
    finally:
        process_control.let_go(held)


def _take(
    pass_id: str,
    *,
    n: int,
    radius: float,
    quality_weight: float,
    strange_share: float | None,
    attempts,
    reseat: int,
    no_attempts: bool,
    full_size: bool,
    refine: bool,
    margin: float,
    seed: int,
    draw_seed: int | None,
    draw_top_k: int,
    workers: int,
    device: str,
    log,
) -> dict:
    """The pass itself, inside the claim [`run`] took."""
    started = time.monotonic()
    share = run_module.STRANGE_SHARE if strange_share is None else float(strange_share)
    m, smooth, strange = parse_attempts(attempts)
    # Resolved here and written down below, whether it was given or drawn: a pass
    # nobody seeded is still a pass somebody has to be able to run again.
    root_seed = resolve_draw_seed(draw_seed)
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
        f"strange_share={share:g} attempts={m},{smooth},{strange} reseat={reseat} "
        + (f"refine at margin {margin:g}" if refine else "NO refine")
        + (" (SKIPPED: --no-attempts)" if no_attempts else "")
        + (" (no full-size renders)" if not full_size else "")
    )
    log(
        f"[pass] draw seed {root_seed} ({'given' if draw_seed is not None else 'drawn'}), "
        f"first pick out of the top {max(1, int(draw_top_k))} of each partition"
    )
    scanning = bool(refine) and not no_attempts
    scan_identity = enforce_scan_identity(log) if scanning else None
    scorer = location_scorer(device, log) if scanning else None

    # --- step 3, first: the distance, refused before anything is spent ------ #
    rows, matrix, store = load_embeddings(log)
    scores = intake.read_scores()
    log(f"[pass] {len(scores):,} location(s) in the supply sidecar")
    # THE population pin. Everything below selects, attempts and seats out of
    # `rows`, so cutting the fallen locations here is what keeps them out of all
    # three at once. See [`admitted_only`].
    rows, matrix, fallen = admitted_only(rows, matrix, scores, log)

    # --- steps 1, 2, 4 ----------------------------------------------------- #
    slots, plan, bench = plan_slots(
        rows,
        matrix,
        scores,
        n,
        share,
        radius,
        quality_weight,
        m,
        log,
        draw_seed=root_seed,
        top_k=draw_top_k,
    )
    plan["attempts"] = {"locations": m, "smooth": smooth, "strange": strange}
    plan["reseat"] = int(reseat)
    by_key = {str(row["key"]): colorize_row(row) for row in rows}
    ranks = _ranks(rows, scores)

    # --- steps 5 and 6, k times: attempt, seat, RE-SEAT what came up empty -- #
    #
    # One loop and not two legs, because a re-seat is a slot changing its mind
    # about where to spend attempts and the only way to know it should is to have
    # seated once already. The plan grows and is never rebuilt, so a resumed pass
    # lands every attempt back on its own index.
    standing_pool = pool_rows(pass_id)
    planned: list[Try] = []
    made: list[dict] = []
    attempt_counts: dict = {}
    seating: dict = {}
    rounds: list[dict] = []
    framings: dict = {}
    for round_number in range(max(0, int(reseat)) + 1):
        if round_number:
            movement = reseat_slots(slots, bench, log)
            # On the round that PRECEDED it, which is the round it is about, and
            # written before the break so a loop that stopped because nothing
            # could move says so rather than leaving a null nobody can read.
            rounds[-1]["reseated"] = movement
            if not movement["moved"]:
                break

        # --- steps 5a and 5 ------------------------------------------------- #
        if no_attempts:
            attempt_counts = {
                "planned": 0,
                "resumed": 0,
                "made": 0,
                "failed": 0,
                "skipped": "--no-attempts",
            }
        else:
            done = {(try_.key, try_.framing) for try_ in planned}
            fresh = attempt_plan(slots, ranks, smooth, strange, already=done)
            if scanning and fresh:
                # BEFORE the attempts, and only over the locations this round
                # added: a location already framed keeps its decision, so a
                # re-seat never re-frames a picture that is already on disk.
                framings, _ = refine_framings(
                    {try_.key for try_ in fresh},
                    by_key,
                    directory,
                    scorer=scorer,
                    scores=scores,
                    margin=margin,
                    framings=framings,
                    log=log,
                )
            planned += fresh
            log(
                f"[attempts] round {round_number}: {len(fresh)} new attempt(s) over "
                f"{len({try_.key for try_ in fresh})} location(s); {len(planned)} planned in all"
            )
            made, attempt_counts = make_attempts(
                directory, planned, by_key, seed, device, log, framings=framings
            )

        # --- step 6 --------------------------------------------------------- #
        mine = [candidate_of_attempt(row, pass_id) for row in made if row.get("p_ge3") is not None]
        standing = pool_candidates(slots, pass_id, rows=standing_pool)
        log(
            f"[seat] {len(mine)} attempt candidate(s) + {len(standing)} seatable out of the "
            f"{len(standing_pool)} standing row(s): candidates are per-pass, locations are not"
        )
        seating = seat(slots, mine + standing, log)
        rounds.append(
            {
                "round": round_number,
                "attempts_planned": len(planned),
                "filled": seating["filled"],
                "unfilled": seating["unfilled"],
                "fallback": None,
                "reseated": None,
            }
        )

        # --- the fallback, before the seat is allowed to count as failed ----- #
        #
        # A slot whose every attempt landed under the bar was attempted on frames
        # this pass MOVED, and the honest question before it re-seats is whether
        # the move is what emptied it. So its refined locations are attempted once
        # more at the framing the record holds — same modes, seeded off the same
        # location and head — and the whole seating is taken again. Only then is
        # the slot's emptiness a fact about the neighbourhood.
        fallback = _fallback_leg(
            slots,
            planned,
            framings,
            ranks,
            smooth,
            strange,
            enabled=scanning and not no_attempts and bool(seating["unfilled"]),
        )
        if fallback:
            planned += fallback
            log(
                f"[fallback] {len(fallback)} attempt(s) over "
                f"{len({try_.key for try_ in fallback})} location(s) at the ORIGINAL framing, "
                f"for {seating['unfilled']} unfilled slot(s)"
            )
            made, attempt_counts = make_attempts(
                directory, planned, by_key, seed, device, log, framings=framings
            )
            mine = [
                candidate_of_attempt(row, pass_id) for row in made if row.get("p_ge3") is not None
            ]
            before = seating["filled"]
            seating = seat(slots, mine + standing, log)
            rounds[-1]["fallback"] = {
                "attempts": len(fallback),
                "locations": len({try_.key for try_ in fallback}),
                "recovered": seating["filled"] - before,
            }
            rounds[-1]["filled"] = seating["filled"]
            rounds[-1]["unfilled"] = seating["unfilled"]
            rounds[-1]["attempts_planned"] = len(planned)

        if not seating["unfilled"]:
            break
    plan["retro"] = read_retro(slots, matrix)
    seating["reseat"] = _reseat_readout(slots, rounds, int(reseat))

    # --- step 7 ------------------------------------------------------------ #
    rendered = (
        render_winners(slots, directory, workers, log) if full_size else skip_winners(slots, log)
    )

    # --- what it leaves behind --------------------------------------------- #
    written = write_records(pass_id, slots, made, plan["guaranteed"], log)
    seconds = time.monotonic() - started
    gallery_rows = records.score_rank(
        [
            row
            for row in records.read_decisions(records.RELEASE, pass_id)
            if row.get("verdict") in {records.RELEASED, records.UNRENDERED}
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
        "refined_pairs": tracked_name(
            refined_pairs_sheet(
                pass_id,
                list(framings.values()),
                framing_dir(directory),
                sheet_dir() / f"{pass_id}_refined_pairs.html",
                margin=margin,
            )
        ),
        "below_floor": tracked_name(
            below_floor_sheet(
                pass_id, slots, mine + standing_pool, sheet_dir() / f"{pass_id}_below_floor.html"
            )
        ),
        "closest_pairs": tracked_name(
            closest_pairs_sheet(
                pass_id,
                slots,
                rows,
                matrix,
                directory,
                sheet_dir() / f"{pass_id}_closest_pairs.html",
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
            "reseat": int(reseat),
            "no_attempts": bool(no_attempts),
            "full_size": bool(full_size),
            "refine": bool(refine),
            "refine_margin": float(margin),
            "seed": int(seed),
            # The RESOLVED root, never a recipe and never `null`: a pass that drew
            # its own seed is reproducible only from what it wrote down.
            "draw_seed": int(root_seed),
            "draw_seed_given": draw_seed is not None,
            "draw_top_k": max(1, int(draw_top_k)),
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
            # The store is append-only and the population is not, so the two
            # counts are named as two: `rows` is what the pass selected over and
            # `below_junk_floor` is what the store still holds and the pass would
            # not look at. See [`admitted_only`].
            "stored": len(rows) + fallen,
            "below_junk_floor": fallen,
            "verdict": store.get("verdict"),
            "manifest": store.get("manifest"),
        },
        "plan": plan,
        "attempts": attempt_counts,
        # Step 5a, priced per pass rather than by an A/B leg: what the scan cost,
        # how often it moved a framing, which rung it moved to, and the whole Δ
        # distribution. Aggregates only — the per-location detail is a row each in
        # the pass directory's `framings.jsonl`, because this record is tracked.
        "refine": {
            "on": bool(refine),
            "margin": float(margin),
            "window": {
                "width_ladder": list(framing_module.WIDTH_LADDER),
                "recentre": framing_module.RECENTRE,
                "moves": [list(axis) for axis in framing_module.AXES],
                "frames_per_location": len(framing_module.WIDTH_LADDER) + len(framing_module.AXES),
                "scans_the_original": framing_module.SCAN_THE_ORIGINAL,
            },
            "identity": scan_identity,
            **framing_module.price(list(framings.values())),
        },
        "pool": {
            "standing_candidates": len(standing),
            "pass_candidates": len(mine),
            # What the pass selected LOCATIONS over and declined to seat out of.
            # The two numbers beside each other are the whole of the ruling.
            "standing_rows": len(standing_pool),
        },
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
    for name, where in sheets.items():
        log(f"[pass] sheet {name}: {where}")
    return record


def _fallback_leg(
    slots: list,
    planned: list,
    framings: dict,
    ranks: dict,
    smooth: int,
    strange: int,
    enabled: bool,
) -> list[Try]:
    """The attempts an unfilled slot is owed at the framing the record holds.

    Only for slots that are actually empty, and only for the locations of theirs
    whose framing the refine leg **moved** — a location it left alone was already
    attempted at its recorded framing, so asking for it again would render the
    same pictures twice.

    Empty where the fallback is off, where nothing is unfilled, or where every
    unfilled slot stands on locations nothing was adopted for. That last case is
    the common one and it is the point: the fallback costs nothing on a pass whose
    framings did not move.
    """
    if not enabled:
        return []
    wanted = {
        key
        for slot in slots
        if slot.seated is None
        for key in slot.locations
        if (framings.get(key) or {}).get("adopted")
    }
    if not wanted:
        return []
    return attempt_plan(
        slots,
        ranks,
        smooth,
        strange,
        already={(try_.key, try_.framing) for try_ in planned},
        framing=ORIGINAL,
        keys=wanted,
    )


def _reseat_readout(slots: list, rounds: list, allowed: int) -> dict:
    """What the re-seat loop recovered, and what it could not.

    The number the whole change is for: how many slots filled on a neighbourhood
    that was not the one the first draw gave them, and on which try. A slot still
    unfilled after `allowed` tries is reported with the count of neighbourhoods it
    actually stood on, because "one hostile draw" and "three in a row" are the
    two readings `below_bar` had to stop conflating.
    """
    on_try: dict[str, int] = {}
    for slot in slots:
        if slot.seated is None:
            continue
        on_try[str(slot.try_index)] = on_try.get(str(slot.try_index), 0) + 1
    unfilled = [slot for slot in slots if slot.seated is None]
    return {
        "allowed": int(allowed),
        "rounds": rounds,
        # Slots that filled, by which try filled them. `0` is the first point the
        # draw handed out — no re-seat needed — so everything above it is what
        # this loop bought.
        "filled_on_try": dict(sorted(on_try.items())),
        "recovered": sum(count for key, count in on_try.items() if int(key)),
        "unfilled": len(unfilled),
        "unfilled_tries": sorted(slot.try_index + 1 for slot in unfilled),
        "exhausted": sum(1 for slot in unfilled if slot.exhausted),
    }


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
        "try": slot.try_index,
        "exhausted": slot.exhausted,
        # Every neighbourhood this slot stood on, the current one last. About
        # 300 bytes a try and only unfilled slots collect more than one, so the
        # history costs the record what the finding is worth.
        "tries": list(slot.tries),
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
    "DRAW_TOP_K",
    "PASS_PREFIX",
    "QUALITY_WEIGHT",
    "RADIUS",
    "RESOLUTION",
    "RESEAT_TRIES",
    "CLOSEST_PAIRS",
    "RETRO_PAIRS",
    "RUNNERS_UP",
    "SCHEMA",
    "SUPERSAMPLE",
    "Bench",
    "Choice",
    "Draw",
    "LOCK_NAME",
    "PassRefused",
    "Slot",
    "Try",
    "attempt_plan",
    "best_unchosen",
    "below_floor_sheet",
    "claim_pass",
    "candidate_of_attempt",
    "candidate_of_pool_row",
    "candidate_picture",
    "choose",
    "closest_pairs_sheet",
    "admitted_only",
    "colorize_row",
    "floor_key",
    "head_order",
    "head_split",
    "load_embeddings",
    "make_attempts",
    "neighbourhood",
    "next_pass_id",
    "parse_attempts",
    "partition_draw_seed",
    "partition_index",
    "pass_dir",
    "picture_id",
    "passes",
    "plan_slots",
    "pool_candidates",
    "pool_rows",
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
    "read_retro",
    "resolve_draw_seed",
    "reseat_slots",
    "slots_path",
    "tracked_bytes",
    "write_pass",
    "write_records",
    "retro_table",
    "run",
    "run_of",
    "seat",
    "sheet_dir",
    "skip_winners",
    "slots_for",
    "sweep_candidates",
]
