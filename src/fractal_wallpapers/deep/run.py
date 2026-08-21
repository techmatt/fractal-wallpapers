"""One deep run: seats in, a ledger out, and the clock it is held to.

A deep run is the shallow walk's machinery pointed at material the shallow walk
cannot reach. It uses the same engine door, the same structural gates, the same
shipped location head and the same ledger — and changes four things, each of
which is a decision this module owns.

```text
roots      seats, from the two channels in `deep.roots` — never a family's home view
floor      `depth.MIN_WIDTH`, two decades below the shallow walk's
reframing   off, and see below
clock      its own per-leg ceilings, stated rather than inherited
```

## Judging is the shipped head, unchanged, on record-and-rank

No deep-specific labels, no deep-specific calibration, no new gate. The head has
seen nothing below `1.8e-10` and one held-out row below `1e-9`, so its scale down
here is an extrapolation — and the answer to that is to *record* what it says
about every candidate, at every fate, and let a later reading decide whether the
extrapolation held. A floor invented for this mode would be a second, unmeasured
opinion stacked on top of an unmeasured one.

## The reframing operators are off, and the reason is a number

[`fractal_wallpapers.discovery.operators`] refuses any framing whose node-width
pixel spacing is within half a decade of the shallow `1e-13` wall, which puts its
floor at `1.21e-10` — an order of magnitude *above* this mode's own. Left on,
every snap and every neighbourhood find below that width comes back
`f64_spacing_wall` and the operator quota fills a batch with refusals.

Nothing is lost by that: the operators are Newton on a nucleus followed by a
framing in atom sizes, which is exactly what [`fractal_wallpapers.deep.roots`]
does — at the precision the atom asks for, against this mode's own floor, and as
a *source of seats* rather than as a triggered move. The deep mode has the
operator; it has it in the right place.

## The clock is stated, because a deep unit is a different class

Curation's hung-unit backstop only ever *raises* itself off units a run has
finished, so a class whose first row dies at the ceiling never teaches the run
that the class is slow. A deep release render was measured at **607 s** against a
shallow release's 16–452 s, which is inside the shallow `1800 s` ceiling — but
only by a factor of three, on the shallowest deep frame this mode produces. So
the ceilings here are declared, not inherited, and a run's own measurements may
only raise them: the same rule shallow has, applied to a distribution shallow has
never seen.

There is a third leg the shallow path does not have one for. A deep `expand` call
runs at an iteration cap near fifty thousand, and a hung one would take the
sourcing leg with it — so every batch runs under [`BATCH_CEILING`], and a batch
that hits it is recorded as a killed batch and the run carries on.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.curation import pacing
from fractal_wallpapers.deep import depth
from fractal_wallpapers.deep import roots as roots_module
from fractal_wallpapers.discovery import walk as walk_module
from fractal_wallpapers.paths import tracked_name

#: What a unit of each curation leg may take in a deep run before it is killed.
#:
#: **Declared, never inherited.** `pacing.HUNG_CEILING` is sized against the
#: shallow release distribution — 16 s to 452 s measured, backstopped at 1800 s —
#: and a deep release is a different class: 607 s for one 2560x1440 ss4 frame at
#: width 7.07e-11 and an iteration cap of 46,365, on an idle machine. That is
#: three times the shallow maximum before this mode has drawn anything near its
#: own floor, where the cap is higher and more of the frame runs to it.
#:
#: So: four times the measured deep render for the release leg, and the shallow
#: multiple carried onto the colorize leg's own measurement. The cost of setting
#: these high is that one genuinely hung unit takes this long to die; the cost of
#: setting them low is a finished deep picture killed at the wire, with a record
#: that reads as a release.
HUNG_CEILING = {pacing.COLORIZE: 1200.0, pacing.RELEASE: 2400.0}

#: What one batch of the sourcing leg may take before it is killed.
#:
#: A deep `expand` draws one probe and one node render per candidate at an
#: iteration cap near 50,000, so a batch is a real unit of work rather than the
#: fraction of a second a shallow one is. Sized off the shakedown's own per-batch
#: timings with the same four-times rule the other two legs get.
BATCH_CEILING = 900.0


@dataclass
class Limits:
    """How much deep walking to do, and how to divide it.

    Deliberately not [`fractal_wallpapers.discovery.walk.Limits`] with different
    numbers: **seats are the budget lever here**, and a seat is a nucleus rather
    than a batch or a rung. A leg is priced by how many places it stands in, and
    everything else in this object divides the work at one of them.
    """

    #: Nuclei this run will stand on. The budget lever.
    seats: int = 8
    #: Share of the seats the Newton channel is asked for first.
    newton_share: float = 0.5
    #: Plane-seed anchors per family the Newton channel may walk down from.
    anchors_per_family: int = 8
    #: Nodes expanded per batch.
    batch: int = 6
    #: Batches to run.
    batches: int = 12
    #: Expansions any one seat's roots may pay for.
    root_expansions: int = 8
    #: Share of a batch's slots reserved for seats nothing has expanded yet.
    breadth_floor: float = 0.34


def walk_limits(limits: Limits) -> walk_module.Limits:
    """The shallow walk's own limits object, filled from this mode's.

    The reserved reframing quota goes to zero because the operators are off — a
    quota that cannot be filled is slots the batch does not get — and the plane
    grace goes to zero because a deep root starts *inside* the band its material
    lives in, which is the one thing the grace exists to compensate for.
    """
    return walk_module.Limits(
        batch=limits.batch,
        batches=limits.batches,
        root_expansions=limits.root_expansions,
        breadth_floor=limits.breadth_floor,
        operator_quota=0,
        plane_grace_rungs=0,
    )


def gates() -> walk_module.Gates:
    """The structural gates, at this mode's floor and otherwise untouched.

    One field differs from the shallow walk's and it is the floor. The interior
    cap, the occupancy floor and the escape band are the same numbers the corpus
    and the head were built against — a deep frame is a frame, and a gate
    re-tuned for depth would be a second unmeasured opinion under the first.
    """
    return walk_module.Gates(min_width=depth.MIN_WIDTH)


@dataclass
class Deep:
    """One deep run: source the seats, stand on them, record everything."""

    out_dir: Path
    seed: int = 0
    limits: Limits = field(default_factory=Limits)
    scorer: object | None = None
    colormap: str = "twilight_shifted"
    node_width: int = 384
    log: object = print

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
        self.rng = random.Random(self.seed)
        self.walk = walk_module.Walk(
            out_dir=self.out_dir,
            seed=self.seed,
            limits=walk_limits(self.limits),
            policy=walk_module.Policy(node_width=self.node_width),
            gates=gates(),
            reframings=walk_module.Reframings(enabled=False),
            scorer=self.scorer,
            colormap=self.colormap,
        )
        self.walk.ledger.write(
            "deep_run",
            min_width=depth.MIN_WIDTH,
            shallow_min_width=depth.SHALLOW_MIN_WIDTH,
            seat_sizes=list(depth.SEAT_SIZES),
            band=[depth.BAND_TOP, depth.BAND_FLOOR],
            money_shot=depth.MONEY_SHOT,
            root_framings=list(depth.ROOT_FRAMINGS),
            resolution_ulps=depth.RESOLUTION_ULPS,
            limits=vars(self.limits),
            ceilings={**HUNG_CEILING, "batch": BATCH_CEILING},
            reframings_off_because="the shallow operators' framing wall is 1.21e-10",
        )
        self.sourcing: dict = {}
        self.seats: list[roots_module.Seat] = []
        self.batch_seconds: list[float] = []
        self.killed_batches = 0

    # ------------------------------------------------------------------ seats
    def source(self) -> list[roots_module.Seat]:
        """Fill the seats, from both channels, and put a root on each framing."""
        started = time.monotonic()
        self.seats, self.sourcing = roots_module.sourced(
            self.limits.seats,
            self.rng,
            newton_share=self.limits.newton_share,
            anchors_per_family=self.limits.anchors_per_family,
            exclude=self.walk.ledger.path,
            log=self.log,
        )
        self.sourcing["seconds"] = round(time.monotonic() - started, 2)
        for index, seat in enumerate(self.seats):
            # The seat itself goes on the record before its roots do. A root row
            # carries a viewport and a provenance; the seat carries the atom, the
            # ladder that reached it and the precision it was solved at, and a
            # row that had to be joined to a summary to be read would be a row
            # split across two files.
            self.walk.ledger.write("seat", seat_index=index, **seat.record())
            for framing in seat.framings:
                self.walk.add_root(
                    seat.family,
                    framing,
                    source=f"deep_{seat.channel}",
                    provenance={"seat_index": index, **seat.provenance},
                )
        return self.seats

    # -------------------------------------------------------------------- run
    def run(self) -> dict:
        """Expand batches until the seats' budget or the frontier runs out.

        The shallow walk's loop with one thing added: every batch runs under
        [`BATCH_CEILING`], and a batch that is killed is *recorded as killed* and
        the run carries on to the next one. A deep expand is a real unit of work
        — fifty thousand iterations a sample, twice per candidate — and a run
        that discovers a hung one by never returning has lost the whole leg
        rather than one batch.
        """
        if not self.seats:
            self.source()
        for index in range(self.limits.batches):
            self.walk.batch_index = index
            batch = self.walk.pop_batch()
            if not batch:
                break
            started = time.monotonic()
            try:
                with engine.deadline(BATCH_CEILING):
                    self.walk.expand_batch(batch)
            except engine.EngineTimeout as killed:
                self.killed_batches += 1
                self.walk.ledger.write(
                    "batch_killed",
                    run_seed=self.seed,
                    batch=index,
                    nodes=[node["node_id"] for node in batch],
                    seconds=round(time.monotonic() - started, 2),
                    ceiling=BATCH_CEILING,
                    reason=str(killed),
                )
                self.log(f"[deep] batch {index} killed at {BATCH_CEILING:.0f}s")
                continue
            finally:
                self.batch_seconds.append(round(time.monotonic() - started, 2))
            self.walk.prune()
            self._tally("batches")
            self._tally("expanded", len(batch))
        return self._summary()

    def _tally(self, name: str, amount: int = 1) -> None:
        """One more of something, in the walk's own counters.

        The walk's, not a second set: the counts a deep run reports are the same
        counters its candidate rows moved, and two tallies of one run is how a
        summary comes to disagree with the ledger under it.
        """
        self.walk.tally[name] = self.walk.tally.get(name, 0) + amount

    def _summary(self) -> dict:
        summary = {
            "mode": "deep",
            "seed": self.seed,
            "min_width": depth.MIN_WIDTH,
            "seats": [seat.record() for seat in self.seats],
            "sourcing": self.sourcing,
            "batches": self.walk.tally.get("batches", 0),
            "batch_seconds": self.batch_seconds,
            "killed_batches": self.killed_batches,
            "ceilings": {**HUNG_CEILING, "batch": BATCH_CEILING},
            "roots": self.walk.next_root_id - 1,
            "frontier": len(self.walk.frontier),
            "scorer": self.walk.scorer.name,
            "scoring": self.walk.scoring_record(),
            "identity": self.walk.identity,
            "counts": dict(sorted(self.walk.tally.items())),
            "depths": self.depths(),
            "ledger": tracked_name(self.walk.ledger.path),
        }
        self.walk.ledger.write("summary", **summary)
        self.walk.ledger.close()
        (self.out_dir / "deep_run.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        return summary

    def depths(self) -> dict:
        """What this run actually reached, by decade — the answer to *how deep*.

        Read off the ledger the run just wrote rather than accumulated as it
        went, so the table and the record cannot disagree.
        """
        from fractal_wallpapers.discovery import ledger as ledger_module

        buckets: dict[str, int] = {}
        admitted: dict[str, int] = {}
        deepest = None
        for row in ledger_module.read(self.walk.ledger.path):
            if row.get("kind") != "candidate":
                continue
            view = row.get("viewport") or {}
            try:
                width = float(view["width"])
            except (KeyError, TypeError, ValueError):
                continue
            decade = f"1e{_decade(width)}"
            buckets[decade] = buckets.get(decade, 0) + 1
            if row.get("fate") == ledger_module.SURVIVED:
                admitted[decade] = admitted.get(decade, 0) + 1
                deepest = width if deepest is None else min(deepest, width)
        return {
            "candidates_by_decade": dict(sorted(buckets.items())),
            "admitted_by_decade": dict(sorted(admitted.items())),
            "deepest_admitted_width": deepest,
        }


def _decade(width: float) -> int:
    """The decade a width sits in, floored, so `9.9e-10` and `1.0e-9` differ."""
    return int(math.floor(math.log10(width))) if width > 0 else 0


def curation_clock(wall_budget: float | None = None) -> pacing.Clock:
    """Curation's clock, with this mode's ceilings rather than the shallow ones.

    The one door between the deep mode and a release: `curate run --deep` builds
    its clock here, so the ceilings a deep release is held to are named in one
    place and a run's summary records which set it used.
    """
    return pacing.Clock(wall_budget, ceilings=HUNG_CEILING)


__all__ = [
    "BATCH_CEILING",
    "HUNG_CEILING",
    "Deep",
    "Limits",
    "curation_clock",
    "gates",
    "walk_limits",
]
