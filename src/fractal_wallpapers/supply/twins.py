"""The twin channel: Julia parameters derived from the parent plane's admissions.

Three partitions in this registry had no channel at all. `julia:multibrot3`,
`julia:multibrot4` and `julia:multibrot5` are a third of the release's supporting
families and there is no tracked pool of degree-3, -4 or -5 Julia parameters to
seed them from — the only tracked `c`-pools are degree 2 and Phoenix, and nothing
in the walk crosses a family. So the allocator carried standing demand for them,
folded it into their parent planes every batch, and the parents manufactured
nothing, because the step that turns a parameter-plane find into a Julia root did
not exist. This module is that step.

**It serves the degree-2 twin too, and that is the later half of the story.**
The channel was held off `julia:mandelbrot` until 2026-09-12 on the ground that a
derived parameter must not displace the tracked pool a three-stage screen left.
What that exclusion protected was real but structural rather than about
coarseness — see [`POOLED_TWINS`] — and the result was that the one degree with a
curated pool was the only one that could not grow: 209 rows, no writer, and no
re-derivation command anywhere in this repository.

```text
an admitted location of the degree-d parameter plane
        │  its centre IS a parameter of the degree-d Julia family
        ▼
    c = (centre_re, centre_im)      skipped if within the c-spacing floor
        │                           of a c this channel already accepted,
        │                           or of one its twin's tracked pool holds
        ▼
    a walk root for julia:<plane>, at the Julia home view
```

**The seed is the same object the degree-2 channel hands over.** A twin's draw is
[`fractal_wallpapers.discovery.pools.JuliaSeed`], the refill's cursor moves over
it the same way, and the root is built by the same `entry.family(degree)` call —
so this is one channel more, not a second mechanism beside the first. The only
thing that differs is where the list comes from, and that is the point.

## "Admitted" is the project's word and this reads all three legs of it

A location is admitted when this project holds a keeper verdict on it, and the
standing deficit already says what that means: a human label at class 3 or 4, or
a machine score at or above the good floor. This channel reads the same two legs
of stock the census reads, plus the third the census cannot — **this run's own
admissions, as they land**. All three go through
[`fractal_wallpapers.supply.currency`], so there is no fourth floor here and
nothing to restate when the good floor moves.

Reading only the run's own admissions was the first shape, and it does not work
on the head that shipped: a plane seed root's first rung scores `1e-3` and below,
so a parameter plane admits nothing inside a short run and the channel it feeds
would be permanently empty on a machine with no history. The standing legs are
what make it a channel on day one rather than a channel in principle.

## The c-spacing floor is the pool's invariant and it applies here too

Julia similarity decays smoothly with `|Δc|` — measured across five decades, with
no knee — so the floor is a stated tolerance rather than a discovered edge: at
[`fractal_wallpapers.discovery.pools.C_SPACING_FLOOR`] the closest admitted pairs
render as near-duplicates about 7% of the time. A candidate `c` inside the floor
of one this channel already accepted is **skipped and recorded**, never silently
dropped: the skip rate is how a reader tells "the parent plane is barren" from
"the parent plane keeps finding the same basin", and those want opposite fixes.

The floor is per twin partition, because two twins of different degree are
different families and a distance between their parameters compares nothing.

**A twin that also holds a tracked pool has that pool's parameters reserved into
its floor**, which is what makes serving the degree-2 twin safe. Before this, two
floors ran over two disjoint sets and neither crossed: `pools.julia_pool` checks
spacing over the pool's own rows, and this channel spaces an offer against the
list *it* accepted, which starts empty. A derived `c` could therefore land on top
of a curated one and neither check would see it. A reservation claims floor space
without becoming a seed, so the pool is never re-derived and never queued twice.

## What is spaced against, and what is only counted

The floor refuses a collision with something **in the queue** — a pool row, or a
parameter this channel already accepted. It does not refuse a `c` this project has
merely walked before, and the reason is that nothing else does either: the proven
channel dedups on the location key alone, so the admitted stock already holds 45
pairs of "distinct" degree-2 and twin `c` inside the floor, the closest 1.8e-8
apart. Enforcing history here and nowhere else would be an asymmetric rule dressed
up as an invariant. So an accepted parameter that falls inside the floor of an
already-walked `c` is **counted and sampled** — `near_walked` in the readout — and
handed over anyway. The count is the evidence for fixing it at the proven channel,
where the gap actually is.

## Starved upstream is a state, not an error

A parent plane with no admissions yet cannot produce a `c`, and a twin whose
queue is empty for that reason is not broken — it is waiting on its parent. It
says so, with the parent's admission count and its own skip count, in the same
place every other deferred partition says why. A run whose twins are quiet and
whose readout does not explain it is how three partitions went unsupplied for a
whole production run without anyone being able to point at the reason.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from fractal_wallpapers.discovery import pools
from fractal_wallpapers.discovery.pools import C_SPACING_FLOOR, JuliaSeed
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import canonical
from fractal_wallpapers.supply.partitions import (
    PARAMETER_PLANES,
    UnregisteredPartition,
    degree_of_plane,
    dynamical_twin,
    partition_of_row,
)

#: Skips kept verbatim per twin, for the record. A count says how often the floor
#: acted; a handful of examples says where, which is the part a reader needs to
#: tell a barren plane from a plane stuck in one basin.
SKIP_SAMPLE = 12

#: What every seed this channel makes carries in its `channel`, and the thing that
#: tells a pooled twin's queue apart at the door where an entry becomes a root:
#: degree 2's queue holds two kinds of [`JuliaSeed`] and only the seed knows which
#: channel made it. A branch on the *partition* there would call a tracked pool row
#: a derived one, and the run record would then say the twin channel produced what
#: a three-stage screen did.
SEED_CHANNEL = "twin:"

#: Twins that also hold a tracked `c`-pool of their own. The same list this
#: constant has always held; what changed on 2026-09-12 is what it does.
#:
#: It named the twins this channel refused to serve, on the ground that the
#: degree-2 pool is what a three-stage screen left — filament detail at several
#: scales together with a composed interior lake — and that the centre of a
#: parameter-plane find is a coarser instrument than that, so it must not
#: *displace* it. **The displacement was literal rather than a judgement about
#: coarseness**: [`fractal_wallpapers.supply.refill.Refill._pool`] reads its twin
#: branch before its `julia:mandelbrot` branch, so a served degree-2 twin would
#: have had the derived list handed over *instead of* the pool's 209 rows rather
#: than alongside them. That is a queue collision, and a queue collision is fixed
#: where the queue is made.
#:
#: On the coarseness itself the record disagrees: inside `julia:mandelbrot` the
#: pool's own screened virgin rows return 0.71 (`near_boundary`) and 1.24
#: (`near_minibrot`) admissions a root against 19.05 for `ranked_harvest` and
#: 30.57 for `proven`. Per-root rates favour a channel fed by admitted stock by
#: construction, so that is not evidence a derived `c` is *better* — it is
#: evidence the screen was not buying what the exclusion said it was.
#:
#: So the list stays and its job is now spacing: a pooled twin has its pool's
#: parameters reserved into the c-spacing floor, and the channel serves it.
POOLED_TWINS = frozenset({"julia:mandelbrot"})


def tracked_pool(twin: str) -> list[JuliaSeed]:
    """The `c`-pool this twin already draws from, or an empty list.

    Read for its parameters' *positions*, never to be handed over: the refill
    queues the pool itself, and a pool row that arrived through here as well
    would be walked twice under one cursor.
    """
    if twin not in POOLED_TWINS:
        return []
    # One pooled twin, and the pool is the degree-2 one. A second would need its
    # own loader here rather than a branch somewhere else, which is the reason
    # this is a function and not a dict literal of imports.
    return pools.julia_pool()


def labelled_keeper(row: dict) -> bool:
    """Whether a human label on this location is a keeper verdict.

    The one predicate this module owns, and it is the currency's: a class the
    weights table pays for is a keeper. The other two legs need none — the ledger
    union is admitted-only by construction, and a run's own admission is what the
    harvest hands over.
    """
    score = row.get("score")
    return score is not None and money.units_of(int(score)) > 0.0


@dataclass(frozen=True)
class Spacing:
    """One `c` the floor is measured against, and what put it there.

    `source` is what a skip is reported by and it is the whole point of the type:
    "the parent plane keeps finding the same basin" and "the parent plane keeps
    finding what the curated pool already holds" are both 98% skip rates and they
    want opposite fixes.
    """

    point: tuple[float, float]
    #: The seed or pool row occupying this space, by id.
    id: str
    #: `twin` for a parameter this channel accepted, `pool` for a tracked pool row.
    source: str


class TwinChannel:
    """The Julia parameters each twin partition can still be handed.

    Holds one accepted list per twin and the `c` values already on it. Both are
    append-only within a run: the refill's cursor moves forward over the list, and
    a `c` accepted once is what every later candidate is spaced against.
    """

    def __init__(self, *, planes=None, floor: float = C_SPACING_FLOOR, ledger=None):
        self.floor = float(floor)
        self.planes = tuple(PARAMETER_PLANES if planes is None else planes)
        #: The twin partitions this channel can serve, in registry order.
        self.partitions = tuple(dynamical_twin(plane) for plane in self.planes)
        self._plane_of = dict(zip(self.partitions, self.planes, strict=True))
        self.ledger = ledger
        self._seeds: dict[str, list[JuliaSeed]] = {p: [] for p in self.partitions}
        self._used: dict[str, list[Spacing]] = {p: [] for p in self.partitions}
        #: `c` this project has walked before: counted against, never refused on.
        #: Deduplicated on the parameter's own strings, because the stock is tens
        #: of thousands of frames standing on a couple of hundred parameters and
        #: a floor measured against every frame would be measured against the
        #: same point seventy times.
        self._walked: dict[str, list[Spacing]] = {p: [] for p in self.partitions}
        self._walked_keys: set[tuple[str, str, str]] = set()
        self.offered: Counter = Counter()
        self.accepted: Counter = Counter()
        self.skipped: Counter = Counter()
        self.unusable: Counter = Counter()
        self.reserved: Counter = Counter()
        self.near_walked: Counter = Counter()
        self.sources: dict[str, Counter] = {p: Counter() for p in self.partitions}
        #: Which kind of occupant a skip collided with, per twin — see [`Spacing`].
        self.blocked_by: dict[str, Counter] = {p: Counter() for p in self.partitions}
        self.skips: dict[str, list[dict]] = {p: [] for p in self.partitions}
        self.near: dict[str, list[dict]] = {p: [] for p in self.partitions}
        self.primed: dict | None = None

    # ------------------------------------------------------------ the parameter

    def seeds(self, twin: str) -> list[JuliaSeed]:
        """The live accepted list. Returned, not copied: it grows as the run
        admits parent locations, and the refill's cursor is what reads it."""
        return self._seeds[twin]

    def plane_of(self, twin: str) -> str:
        return self._plane_of[twin]

    def degree_of(self, twin: str) -> int:
        return degree_of_plane(self._plane_of[twin])

    def _distance(self, taken: list[Spacing], point) -> tuple[float, Spacing | None]:
        """`(distance to the nearest of `taken`, which one)`, or `(inf, None)`."""
        nearest, which = math.inf, None
        for spacing in taken:
            gap = math.hypot(point[0] - spacing.point[0], point[1] - spacing.point[1])
            if gap < nearest:
                nearest, which = gap, spacing
        return nearest, which

    # ------------------------------------------------------------ the spacings

    def reserve(self, twin: str, seeds) -> int:
        """Claim floor space for parameters this twin already draws from elsewhere.

        A reservation is spacing and nothing else: it never enters the accepted
        list, is never handed over, and does not count as an offer. What it stops
        is this channel deriving a second copy of a `c` the twin's own tracked
        pool already queues — the collision the degree-2 exclusion used to prevent
        by refusing to run at all.
        """
        if twin not in self._used:
            return 0
        taken = 0
        for seed in seeds:
            try:
                point = (float(seed.c[0]), float(seed.c[1]))
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(point[0]) and math.isfinite(point[1])):
                continue
            self._used[twin].append(Spacing(point=point, id=seed.id, source="pool"))
            taken += 1
        self.reserved[twin] += taken
        return taken

    def walked(self, twin: str, row: dict) -> bool:
        """Note one `c` this project has already walked, for counting only.

        Returns whether it was new. A Julia row of one of this channel's twins
        carries its parameter in its family, and the admitted stock is the record
        of which Julia sets have been descended — which is what makes an accepted
        parameter "new" or merely new *to this channel*.
        """
        if twin not in self._walked:
            return False
        family = row.get("family")
        if not isinstance(family, dict):
            return False
        c = family.get("c")
        if not (isinstance(c, (list, tuple)) and len(c) == 2):
            return False
        key = (twin, str(c[0]), str(c[1]))
        if key in self._walked_keys:
            return False
        try:
            point = (float(c[0]), float(c[1]))
        except (TypeError, ValueError):
            return False
        if not (math.isfinite(point[0]) and math.isfinite(point[1])):
            return False
        self._walked_keys.add(key)
        self._walked[twin].append(
            Spacing(point=point, id=f"walked-{twin}-{len(self._walked[twin]):04d}", source="walked")
        )
        return True

    def offer(self, row: dict, source: str) -> bool:
        """Offer one admitted parent-plane location as a twin parameter.

        Returns whether it became a seed. Everything that does not — an unusable
        row, a `c` inside the floor — is counted, and the floor's refusals are
        also kept verbatim up to [`SKIP_SAMPLE`].
        """
        try:
            plane = partition_of_row(row)
        except UnregisteredPartition:
            return False
        if plane not in self.planes:
            return False
        twin = dynamical_twin(plane)
        viewport = row.get("viewport")
        if not isinstance(viewport, dict):
            self.unusable[twin] += 1
            return False
        try:
            point = (float(viewport["center_re"]), float(viewport["center_im"]))
        except (KeyError, TypeError, ValueError):
            self.unusable[twin] += 1
            return False
        if not (math.isfinite(point[0]) and math.isfinite(point[1])):
            self.unusable[twin] += 1
            return False

        self.offered[twin] += 1
        gap, blocker = self._distance(self._used[twin], point)
        if gap < self.floor:
            self.skipped[twin] += 1
            self.blocked_by[twin][blocker.source] += 1
            if len(self.skips[twin]) < SKIP_SAMPLE:
                self.skips[twin].append(
                    {
                        "c": [canonical(viewport["center_re"]), canonical(viewport["center_im"])],
                        "source": source,
                        "distance": float(f"{gap:.6g}"),
                        "floor": self.floor,
                        "blocked_by": blocker.id,
                        "blocked_by_source": blocker.source,
                    }
                )
            self._record(
                "twin_skip",
                twin=twin,
                plane=plane,
                source=source,
                distance=gap,
                blocked_by=blocker.source,
            )
            return False

        seed = JuliaSeed(
            id=f"twin-{plane}-{len(self._seeds[twin]):04d}",
            c=(canonical(viewport["center_re"]), canonical(viewport["center_im"])),
            channel=f"{SEED_CHANNEL}{source}",
        )
        self._seeds[twin].append(seed)
        self._used[twin].append(Spacing(point=point, id=seed.id, source="twin"))
        self.accepted[twin] += 1
        self.sources[twin][source] += 1
        # Counted after the accept, not before it: this is a reading of how much
        # of what the channel derives is ground the project has already been over,
        # and it changes nothing about whether the parameter is handed out.
        near, walked = self._distance(self._walked[twin], point)
        if near < self.floor:
            self.near_walked[twin] += 1
            if len(self.near[twin]) < SKIP_SAMPLE:
                self.near[twin].append(
                    {
                        "seed_id": seed.id,
                        "c": [seed.c[0], seed.c[1]],
                        "distance": float(f"{near:.6g}"),
                        "walked": [walked.point[0], walked.point[1]],
                    }
                )
        self._record(
            "twin_seed",
            twin=twin,
            plane=plane,
            source=source,
            seed_id=seed.id,
            near_walked=near < self.floor,
        )
        return True

    def note(self, partition: str, row: dict) -> bool:
        """One admission the run just booked. A no-op outside the parameter planes.

        A twin's own admission is not an offer — a Julia location's centre is a
        point of the `z`-plane and not a parameter — but it is one more frame of a
        `c`, so it is noted as walked and nothing else.
        """
        if partition in self._walked:
            self.walked(partition, row)
        if partition not in self.planes:
            return False
        return self.offer(row, "run")

    def _note_walked(self, row: dict) -> bool:
        """Note a standing-stock row as walked, if it is a Julia row of one of ours."""
        try:
            partition = partition_of_row(row)
        except UnregisteredPartition:
            return False
        return self.walked(partition, row)

    def _record(self, kind: str, **fields) -> None:
        """Write one row, if this channel was given a ledger to write to.

        Only the run's own offers reach the ledger row by row — the standing legs
        are read at start-up and summarized in a single `twin_channel` row, so a
        resumed session does not re-append a thousand lines about a corpus that
        has not moved.
        """
        if self.ledger is None or fields.get("source") != "run":
            return
        self.ledger.write(kind, **fields)

    # ------------------------------------------------------------- the priming

    def prime(self, label_paths=None, ledger_paths=None) -> dict:
        """Read the tracked pools, then the two standing legs of admitted stock.

        The pools first, and that order is the whole of the degree-2 repair: a
        reservation has to be in place before the first offer is measured against
        it, or the channel spends the run deriving what the pool already holds and
        the floor never says so. Labels before ledgers for the same reason one
        rung down — where a human has looked, that verdict is the one the census
        keeps, so it should also be the one that claims the space.

        The two standing legs are read once each and both are read for two things:
        a parameter-plane row is an *offer*, and a Julia row of one of this
        channel's twins is a `c` this project has already walked. The second is
        counted against, never refused on.
        """
        from fractal_wallpapers.supply import census, ledgers

        for twin in self.partitions:
            self.reserve(twin, tracked_pool(twin))
        taken = Counter()
        for row in census.label_rows(label_paths):
            self._note_walked(row)
            if labelled_keeper(row):
                taken["labels"] += int(self.offer(row, "labels"))
        rows, union = ledgers.admitted_union(ledger_paths)
        for row in rows:
            self._note_walked(row)
            taken["ledgers"] += int(self.offer(row, "ledgers"))
        self.primed = {
            "accepted": dict(sorted(taken.items())),
            "reserved": {p: self.reserved.get(p, 0) for p in self.partitions},
            "walked": {p: len(self._walked[p]) for p in self.partitions},
            "ledger_union": {k: union.get(k) for k in ("size", "ledgers")},
        }
        if self.ledger is not None:
            self.ledger.write("twin_channel", floor=self.floor, primed=self.primed, **self.counts())
        return self.primed

    # ------------------------------------------------------------- the readout

    def counts(self) -> dict:
        return {
            "offered": {p: self.offered.get(p, 0) for p in self.partitions},
            "accepted": {p: self.accepted.get(p, 0) for p in self.partitions},
            "skipped_inside_floor": {p: self.skipped.get(p, 0) for p in self.partitions},
            "blocked_by": {p: dict(sorted(self.blocked_by[p].items())) for p in self.partitions},
            "near_walked": {p: self.near_walked.get(p, 0) for p in self.partitions},
            "unusable": {p: self.unusable.get(p, 0) for p in self.partitions},
        }

    def starvation(self, twin: str, drawn: int = 0) -> str:
        """Why this twin has nothing to hand over, in one sentence.

        Two different states, and they want opposite readings: a channel with no
        parameters yet is waiting on its parent, and a channel whose parameters
        are all walked has been working.
        """
        plane = self._plane_of[twin]
        accepted = self.accepted.get(twin, 0)
        # A pooled twin's queue is its tracked pool and this channel together, so
        # a sentence naming only the channel would send a reader off to fill
        # something that is not what ran out.
        pooled = (
            f", alongside the {self.reserved.get(twin, 0)} row(s) of the tracked pool this twin "
            f"also draws from"
            if twin in POOLED_TWINS
            else ""
        )
        tail = (
            f"{plane} has admitted {self.offered.get(twin, 0)} location(s) this run and in the "
            f"record, of which {accepted} became twin parameters{pooled} and "
            f"{self.skipped.get(twin, 0)} fell inside the {self.floor:.1e} c-spacing floor of "
            f"one already taken"
        )
        if accepted and drawn >= accepted:
            return (
                f"the twin channel is exhausted: all {accepted} parameter(s) it derived have "
                f"been handed over and walked. {tail}. Serving {plane} is what derives more."
            )
        return (
            f"starved upstream: {tail}. The channel is wired and waiting on its parent, which "
            f"is a state and not a fault — serving {plane} is what fills it."
        )

    def summary(self) -> dict:
        return {
            "c_spacing_floor": self.floor,
            "primed": self.primed,
            **self.counts(),
            "sources": {p: dict(sorted(self.sources[p].items())) for p in self.partitions},
            "skip_sample": {p: self.skips[p] for p in self.partitions if self.skips[p]},
            "near_walked_sample": {p: self.near[p] for p in self.partitions if self.near[p]},
        }

    # ---------------------------------------------------------------- the state

    def state(self) -> dict:
        """Everything a resumed run cannot re-derive.

        The accepted list is checkpointed whole rather than re-primed: the
        standing legs would come back identically, but the run's own admissions
        would not, and a c-spacing floor that forgot half its accepted parameters
        would hand out near-duplicates of what it had already spent.

        The reservations are checkpointed for the same reason and it is the
        sharper one: they come from a tracked file, so a resumed run *could*
        re-read them — but a run that restored its seeds without them would have a
        floor that had forgotten the pool alone, which is the exact state the
        degree-2 exclusion existed to prevent, reached by resuming.

        The walked set is **not** checkpointed. It is a reading rather than an
        invariant, it re-derives identically from the standing legs, and it is the
        one list here that runs to hundreds of entries.
        """
        return {
            "floor": self.floor,
            "seeds": {
                p: [[s.id, s.c[0], s.c[1], s.channel] for s in self._seeds[p]]
                for p in self.partitions
            },
            "reserved": {
                p: [[s.id, s.point[0], s.point[1]] for s in self._used[p] if s.source == "pool"]
                for p in self.partitions
            },
            "offered": dict(self.offered),
            "accepted": dict(self.accepted),
            "skipped": dict(self.skipped),
            "unusable": dict(self.unusable),
            "near_walked": dict(self.near_walked),
            "sources": {p: dict(self.sources[p]) for p in self.partitions},
            "blocked_by": {p: dict(self.blocked_by[p]) for p in self.partitions},
            "skips": {p: self.skips[p] for p in self.partitions},
            "near": {p: self.near[p] for p in self.partitions},
            "primed": self.primed,
        }

    def load_state(self, state: dict) -> None:
        self.floor = float(state.get("floor", self.floor))
        reserved = state.get("reserved") or {}
        for twin, rows in (state.get("seeds") or {}).items():
            if twin not in self._seeds:
                continue
            self._seeds[twin] = [
                JuliaSeed(id=row[0], c=(row[1], row[2]), channel=row[3]) for row in rows
            ]
            # Reservations first, so a restored floor is the floor the first
            # session offered against rather than the same list minus its pool.
            self._used[twin] = [
                Spacing(point=(float(row[1]), float(row[2])), id=row[0], source="pool")
                for row in reserved.get(twin) or []
            ] + [
                Spacing(point=(float(row[1]), float(row[2])), id=row[0], source="twin")
                for row in rows
            ]
        self.offered = Counter(state.get("offered") or {})
        self.accepted = Counter(state.get("accepted") or {})
        self.skipped = Counter(state.get("skipped") or {})
        self.unusable = Counter(state.get("unusable") or {})
        self.near_walked = Counter(state.get("near_walked") or {})
        self.reserved = Counter({p: len(reserved.get(p) or []) for p in self.partitions})
        self.sources = {
            p: Counter((state.get("sources") or {}).get(p) or {}) for p in self.partitions
        }
        self.blocked_by = {
            p: Counter((state.get("blocked_by") or {}).get(p) or {}) for p in self.partitions
        }
        self.skips = {p: list((state.get("skips") or {}).get(p) or []) for p in self.partitions}
        self.near = {p: list((state.get("near") or {}).get(p) or []) for p in self.partitions}
        self.primed = state.get("primed", self.primed)


def build(
    ledger=None, label_paths=None, ledger_paths=None, floor: float = C_SPACING_FLOOR, planes=None
):
    """A primed twin channel — the one a harvest holds."""
    channel = TwinChannel(planes=planes, floor=floor, ledger=ledger)
    channel.prime(label_paths=label_paths, ledger_paths=ledger_paths)
    return channel


__all__ = [
    "POOLED_TWINS",
    "SEED_CHANNEL",
    "SKIP_SAMPLE",
    "Spacing",
    "TwinChannel",
    "build",
    "labelled_keeper",
    "tracked_pool",
]
