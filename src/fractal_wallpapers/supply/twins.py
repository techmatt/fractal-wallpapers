"""The twin channel: Julia parameters derived from the parent plane's admissions.

Three partitions in this registry had no channel at all — and they are exactly
the twins this module serves. `julia:multibrot3`,
`julia:multibrot4` and `julia:multibrot5` are a third of the release's supporting
families and there is no tracked pool of degree-3, -4 or -5 Julia parameters to
seed them from — the two tracked `c`-pools are degree 2 and Phoenix, and nothing
in the walk crosses a family. So the allocator carried standing demand for them,
folded it into their parent planes every batch, and the parents manufactured
nothing, because the step that turns a parameter-plane find into a Julia root did
not exist. This module is that step.

```text
an admitted location of the degree-d parameter plane
        │  its centre IS a parameter of the degree-d Julia family
        ▼
    c = (centre_re, centre_im)      skipped if within the c-spacing floor
        │                           of a c this channel already accepted
        ▼
    a walk root for julia:multibrot-d, at the Julia home view
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

#: Twins that already have a tracked `c`-pool and are therefore not this channel's
#: job. The degree-2 pool is what a three-stage screen left — filament detail at
#: several scales together with a composed interior lake — and the centre of a
#: parameter-plane find is a coarser instrument than that, so it must not
#: displace it. Excluded here rather than at the draw, because a channel that
#: derives parameters no refill would ever spend puts a number in every readout
#: that means nothing.
POOLED_TWINS = frozenset({"julia:mandelbrot"})


def unpooled_planes(planes=PARAMETER_PLANES) -> tuple[str, ...]:
    """The parameter planes whose twin has no tracked pool of its own."""
    return tuple(p for p in planes if dynamical_twin(p) not in POOLED_TWINS)


def labelled_keeper(row: dict) -> bool:
    """Whether a human label on this location is a keeper verdict.

    The one predicate this module owns, and it is the currency's: a class the
    weights table pays for is a keeper. The other two legs need none — the ledger
    union is admitted-only by construction, and a run's own admission is what the
    harvest hands over.
    """
    score = row.get("score")
    return score is not None and money.units_of(int(score)) > 0.0


class TwinChannel:
    """The Julia parameters each twin partition can still be handed.

    Holds one accepted list per twin and the `c` values already on it. Both are
    append-only within a run: the refill's cursor moves forward over the list, and
    a `c` accepted once is what every later candidate is spaced against.
    """

    def __init__(self, *, planes=None, floor: float = C_SPACING_FLOOR, ledger=None):
        self.floor = float(floor)
        self.planes = tuple(unpooled_planes() if planes is None else planes)
        #: The twin partitions this channel can serve, in registry order.
        self.partitions = tuple(dynamical_twin(plane) for plane in self.planes)
        self._plane_of = dict(zip(self.partitions, self.planes, strict=True))
        self.ledger = ledger
        self._seeds: dict[str, list[JuliaSeed]] = {p: [] for p in self.partitions}
        self._used: dict[str, list[tuple[float, float]]] = {p: [] for p in self.partitions}
        self.offered: Counter = Counter()
        self.accepted: Counter = Counter()
        self.skipped: Counter = Counter()
        self.unusable: Counter = Counter()
        self.sources: dict[str, Counter] = {p: Counter() for p in self.partitions}
        self.skips: dict[str, list[dict]] = {p: [] for p in self.partitions}
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

    def _distance(self, twin: str, point: tuple[float, float]) -> tuple[float, int | None]:
        """`(distance to the nearest accepted c, its index)`, or `(inf, None)`."""
        nearest, where = math.inf, None
        for index, (x, y) in enumerate(self._used[twin]):
            gap = math.hypot(point[0] - x, point[1] - y)
            if gap < nearest:
                nearest, where = gap, index
        return nearest, where

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
        gap, where = self._distance(twin, point)
        if gap < self.floor:
            self.skipped[twin] += 1
            blocker = self._seeds[twin][where]
            if len(self.skips[twin]) < SKIP_SAMPLE:
                self.skips[twin].append(
                    {
                        "c": [canonical(viewport["center_re"]), canonical(viewport["center_im"])],
                        "source": source,
                        "distance": float(f"{gap:.6g}"),
                        "floor": self.floor,
                        "blocked_by": blocker.id,
                    }
                )
            self._record("twin_skip", twin=twin, plane=plane, source=source, distance=gap)
            return False

        seed = JuliaSeed(
            id=f"twin-{plane}-{len(self._seeds[twin]):04d}",
            c=(canonical(viewport["center_re"]), canonical(viewport["center_im"])),
            channel=f"twin:{source}",
        )
        self._seeds[twin].append(seed)
        self._used[twin].append(point)
        self.accepted[twin] += 1
        self.sources[twin][source] += 1
        self._record("twin_seed", twin=twin, plane=plane, source=source, seed_id=seed.id)
        return True

    def note(self, partition: str, row: dict) -> bool:
        """One admission the run just booked. A no-op outside the parameter planes."""
        if partition not in self.planes:
            return False
        return self.offer(row, "run")

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
        """Read the two standing legs of admitted stock, in that order.

        Labels first, deliberately: where a human has looked, that verdict is the
        one the census keeps, so it should also be the one that claims the space
        inside the c-spacing floor.
        """
        from fractal_wallpapers.supply import census, ledgers

        taken = Counter()
        for row in census.label_rows(label_paths):
            if labelled_keeper(row):
                taken["labels"] += int(self.offer(row, "labels"))
        rows, union = ledgers.admitted_union(ledger_paths)
        for row in rows:
            taken["ledgers"] += int(self.offer(row, "ledgers"))
        self.primed = {
            "accepted": dict(sorted(taken.items())),
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
        tail = (
            f"{plane} has admitted {self.offered.get(twin, 0)} location(s) this run and in the "
            f"record, of which {accepted} became twin parameters and "
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
        }

    # ---------------------------------------------------------------- the state

    def state(self) -> dict:
        """Everything a resumed run cannot re-derive.

        The accepted list is checkpointed whole rather than re-primed: the
        standing legs would come back identically, but the run's own admissions
        would not, and a c-spacing floor that forgot half its accepted parameters
        would hand out near-duplicates of what it had already spent.
        """
        return {
            "floor": self.floor,
            "seeds": {
                p: [[s.id, s.c[0], s.c[1], s.channel] for s in self._seeds[p]]
                for p in self.partitions
            },
            "offered": dict(self.offered),
            "accepted": dict(self.accepted),
            "skipped": dict(self.skipped),
            "unusable": dict(self.unusable),
            "sources": {p: dict(self.sources[p]) for p in self.partitions},
            "skips": {p: self.skips[p] for p in self.partitions},
            "primed": self.primed,
        }

    def load_state(self, state: dict) -> None:
        self.floor = float(state.get("floor", self.floor))
        for twin, rows in (state.get("seeds") or {}).items():
            if twin not in self._seeds:
                continue
            self._seeds[twin] = [
                JuliaSeed(id=row[0], c=(row[1], row[2]), channel=row[3]) for row in rows
            ]
            self._used[twin] = [(float(row[1]), float(row[2])) for row in rows]
        self.offered = Counter(state.get("offered") or {})
        self.accepted = Counter(state.get("accepted") or {})
        self.skipped = Counter(state.get("skipped") or {})
        self.unusable = Counter(state.get("unusable") or {})
        self.sources = {
            p: Counter((state.get("sources") or {}).get(p) or {}) for p in self.partitions
        }
        self.skips = {p: list((state.get("skips") or {}).get(p) or []) for p in self.partitions}
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
    "SKIP_SAMPLE",
    "TwinChannel",
    "build",
    "labelled_keeper",
    "unpooled_planes",
]
