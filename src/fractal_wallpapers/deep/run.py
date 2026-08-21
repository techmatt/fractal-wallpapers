"""One deep run: seats in, a ledger out, and the clock it is held to.

A deep run is the shallow walk's machinery pointed at material the shallow walk
cannot reach. It uses the same engine door, the same structural gates, the same
shipped location head and the same ledger — and changes six things, each of
which is a decision this module owns.

```text
roots      seats, from the two channels in `deep.roots` — never a family's home view
floor      `depth.MIN_WIDTH`, two decades below the shallow walk's
reframing  off, and see below
clock      its own per-leg ceilings, stated rather than inherited
seats      sized against the wall budget, and topped up mid-flight
lineages   capped, so walk time flows to cells nothing has saturated
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

## The seats are sized against the budget, and topped up inside the run

`deep_run1` was given eight hours and spent two hours ten. Its seat count was
picked by hand from conservative estimates, and the frontier emptied at 470 of
2000 node slots with three quarters of the budget unspent. That is not a run
that stopped early; it is a run that was sized wrong before it started.

So `--wall-budget` sizes the seating. [`fractal_wallpapers.deep.budget`] prices a
seat off that run's own record — sourcing, walk and the evaluation gallery that
follows — and the run seats as many as the budget buys after two margins. **And
when the frontier empties with budget still left, the run sources again into the
same run**: same ledger, same artifacts root, same [`roots.Standing`], seating
the family x band cells the earlier rounds left least full.

To be explicit about what that is and is not. This is **within-run
continuation**, not a follow-up run: a run topping up its own seats mid-flight is
a correctly sized run, and the rule against starting a new run on the heels of a
finished one is about launching runs. Every round is still held to
don't-start-what-cannot-finish — the same prospective gate the curation legs use,
against the same clock — so the last round is the last one the budget can afford,
not the one that discovers it could not.

## A lineage is capped, because monotony is a supply problem

`deep_run1` put 741 admissions on 15 of its 48 roots and 85 of them on one, and
the 162 frames of its floor gallery were largely one composition in 162 palettes.
A gallery can spread itself over lineages after the fact — that one had to — but
it cannot get back the walk time that went into the lineage it then thinned. So
the cap acts at supply time: [`LINEAGE_ADMISSIONS`] admissions per root, after
which the lineage stops expanding and its standing frontier nodes are evicted.

**Record-and-rank still governs.** Capped is not deleted: every row the lineage
already wrote keeps the fate it earned, nothing is retro-refused, and the
crossing lands in the ledger as its own row so a readout can say what the cap
cost and what it bought. That is also why a lineage can finish a run a little
over its cap — two of its nodes in one batch, the second already drawn when the
first closes it — and why that costs nothing: the overshoot is in the count, and
the batch slots stop from the crossing.
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
from fractal_wallpapers.deep import budget as budget_module
from fractal_wallpapers.deep import depth
from fractal_wallpapers.deep import roots as roots_module
from fractal_wallpapers.discovery import walk as walk_module
from fractal_wallpapers.paths import tracked_name

#: The two legs a deep run spends its own wall clock in, before curation sees
#: anything. Named here because this module is what paces them, and a leg name
#: that is a bare string in three places is a leg that stops being paced the day
#: one of them is misspelled.
SOURCING, WALK = "sourcing", "walk"

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

#: What one batch of the [`WALK`] leg may take before it is killed.
#:
#: A deep `expand` draws one probe and one node render per candidate at an
#: iteration cap near 50,000, so a batch is a real unit of work rather than the
#: fraction of a second a shallow one is. Sized off the shakedown's own per-batch
#: timings with the same four-times rule the other two legs get.
BATCH_CEILING = 900.0

#: What each of this mode's own two legs reserves for the work that must still
#: happen after it stops, and how much room it needs to risk a unit it has never
#: measured. Both in seconds, both against measured units of seconds to tens of
#: seconds, and both deliberately generous for the same reason curation's are: a
#: reserve that is too large costs one batch not attempted.
LEG_MARGIN = {SOURCING: 60.0, WALK: 60.0}
LEG_MINIMUM = {SOURCING: 30.0, WALK: 30.0}

#: Admissions any one lineage may book before a deep run stops expanding it.
#:
#: `deep_run1`'s 48 roots booked 741 admissions between them — an equal share of
#: 15 — but 15 roots booked all of it and the largest booked **85**. Twenty-four
#: is half again the equal share: enough that a genuinely fertile lineage runs
#: past its portion, not so much that it becomes the run. At that cap ten of that
#: run's lineages would have closed, and 446 of its 741 admissions — sixty per
#: cent — are walk time that would have gone somewhere else.
#:
#: The honest qualifier: in `deep_run1` there *was* nowhere else, because the
#: frontier emptied anyway. The cap is worth what the seating above it is worth,
#: and the two ship together for that reason.
LINEAGE_ADMISSIONS = 24

#: Nuclei a run stands on when nothing sizes them — no `--wall-budget` and no
#: `--seats`. The old default, kept so an unbudgeted run is the run it was.
DEFAULT_SEATS = 8

#: Batches a run runs when nothing sizes them, for the same reason.
DEFAULT_BATCHES = 12


@dataclass
class Limits:
    """How much deep walking to do, and how to divide it.

    Deliberately not [`fractal_wallpapers.discovery.walk.Limits`] with different
    numbers: **seats are the budget lever here**, and a seat is a nucleus rather
    than a batch or a rung. A leg is priced by how many places it stands in, and
    everything else in this object divides the work at one of them.
    """

    #: Nuclei this run will stand on. The budget lever.
    #:
    #: `None` means *nothing has said*, and is the only value that lets the wall
    #: budget size the seating: a number here — from `--seats` — is a person
    #: overriding the projection, and a default that looked like one would
    #: silently do the overriding for them.
    seats: int | None = None
    #: Share of the seats the Newton channel is asked for first.
    newton_share: float = 0.5
    #: Plane-seed anchors per family the Newton channel may walk down from.
    #:
    #: A ceiling on the whole run rather than on one round, and the Newton
    #: channel's entire supply: a budgeted run raises it to what its projection
    #: needs, because 8 a family is 32 anchors and a projection at eight hours
    #: asks for several hundred descents.
    anchors_per_family: int = 8
    #: Nodes expanded per batch.
    batch: int = 6
    #: Batches to run. `None` is sized from the seats, the same way [`seats`] is
    #: sized from the budget — batches are not this mode's lever and a number
    #: that has to be guessed alongside the seat count is a second way to be
    #: wrong about the same thing.
    batches: int | None = None
    #: Expansions any one seat's roots may pay for.
    root_expansions: int = 8
    #: Share of a batch's slots reserved for seats nothing has expanded yet.
    breadth_floor: float = 0.34
    #: Admissions any one lineage may book before the walk stops expanding it.
    #: `None` turns the cap off; [`LINEAGE_ADMISSIONS`] is the deep default.
    lineage_admissions: int | None = LINEAGE_ADMISSIONS
    #: Whether a run that empties its frontier with budget left sources again
    #: into the same run. On, and inert without a wall budget — there is no
    #: projection to say how much more the run can afford.
    reseat: bool = True


def walk_limits(limits: Limits, *, batches: int | None = None) -> walk_module.Limits:
    """The shallow walk's own limits object, filled from this mode's.

    The reserved reframing quota goes to zero because the operators are off — a
    quota that cannot be filled is slots the batch does not get — and the plane
    grace goes to zero because a deep root starts *inside* the band its material
    lives in, which is the one thing the grace exists to compensate for.
    """
    return walk_module.Limits(
        batch=limits.batch,
        batches=DEFAULT_BATCHES if batches is None else int(batches),
        root_expansions=limits.root_expansions,
        breadth_floor=limits.breadth_floor,
        operator_quota=0,
        plane_grace_rungs=0,
        lineage_admissions=limits.lineage_admissions,
    )


def gates() -> walk_module.Gates:
    """The structural gates, at this mode's floor and otherwise untouched.

    One field differs from the shallow walk's and it is the floor. The interior
    cap, the occupancy floor and the escape band are the same numbers the corpus
    and the head were built against — a deep frame is a frame, and a gate
    re-tuned for depth would be a second unmeasured opinion under the first.
    """
    return walk_module.Gates(min_width=depth.MIN_WIDTH)


def run_clock(wall_budget: float | None = None) -> pacing.Clock:
    """The clock a deep run's own two legs are paced against.

    Curation's machinery, this mode's legs. `may_start` is the same prospective
    gate — *would starting this unit put the run over?* — and the estimate is the
    same one: the longest unit of the class this run has finished, so a run at a
    depth where a batch costs four times the median sizes itself off its own
    batches rather than off `deep_run1`'s.

    Only the walk leg carries a kill deadline. A sourcing unit is a Newton
    descent, which is arbitrary-precision arithmetic **in this process** with no
    subprocess to take down — [`fractal_wallpapers.deep.roots.MAX_STEPS`] and
    `STEP_PROBES` are what bound one from the inside — so that leg is gated and
    measured and never killed.
    """
    return pacing.Clock(
        wall_budget,
        margins=LEG_MARGIN,
        minimums=LEG_MINIMUM,
        ceilings={WALK: BATCH_CEILING},
    )


@dataclass
class Deep:
    """One deep run: source the seats, stand on them, record everything."""

    out_dir: Path
    seed: int = 0
    limits: Limits = field(default_factory=Limits)
    #: The wall clock this run promises to finish inside, in seconds. `None` is
    #: an unpaced run sized by [`Limits.seats`] alone — what this mode did before
    #: `deep_run1` measured what that costs.
    wall_budget: float | None = None
    #: What a seat costs, for the projection. Defaults to `deep_run1`'s measured
    #: table; a run with its own numbers may hand them in.
    costs: budget_module.Costs = field(default_factory=budget_module.Costs)
    #: Whether the budget reserves the evaluation gallery's share of the clock.
    #: On: this run draws no finished frame, and a walk that spends to the last
    #: second is a walk nobody has time to look at. Off is a **walk-only** run.
    gallery_reserve: bool = True
    scorer: object | None = None
    colormap: str = "twilight_shifted"
    node_width: int = 384
    log: object = print

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
        self.rng = random.Random(self.seed)
        self.clock = run_clock(self.wall_budget)
        self.standing = roots_module.Standing()
        self.round = 0
        self.batch_index = 0

        self.projection = self._project()
        # Three ways a seat count is decided, in the order that respects who said
        # what: an explicit `--seats`, then the budget's own projection, then the
        # bare default. The tri-state on `Limits.seats` is what keeps the middle
        # one reachable — a default of 8 would out-rank every budget silently.
        if self.limits.seats is not None:
            self.seats_wanted = int(self.limits.seats)
        elif self.projection is not None:
            self.seats_wanted = self.projection.seats
        else:
            self.seats_wanted = DEFAULT_SEATS
        # Batches take the same three-way answer, in the same order. An
        # unbudgeted run keeps the ceiling it always had; a budgeted one gets one
        # sized to be out of the way, and lets the clock stop the leg.
        if self.limits.batches is not None:
            self.batches_allowed = int(self.limits.batches)
        elif self.projection is not None:
            self.batches_allowed = self._batches_for(self.seats_wanted)
        else:
            self.batches_allowed = DEFAULT_BATCHES
        self.walk = walk_module.Walk(
            out_dir=self.out_dir,
            seed=self.seed,
            limits=walk_limits(self.limits, batches=self.batches_allowed),
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
            seats_wanted=self.seats_wanted,
            batches_allowed=self.batches_allowed,
            wall_budget=self.wall_budget,
            projection=None if self.projection is None else self.projection.record(),
            lineage_admissions=self.limits.lineage_admissions,
            ceilings={**HUNG_CEILING, "batch": BATCH_CEILING},
            reframings_off_because="the shallow operators' framing wall is 1.21e-10",
        )
        self.sourcing: dict = {}
        self.rounds: list[dict] = []
        self.seats: list[roots_module.Seat] = []
        self.batch_seconds: list[float] = []
        self.killed_batches = 0

    # ---------------------------------------------------------------- budget
    def _project(self, *, spent: float = 0.0, admitted: int = 0):
        """How many seats this run can still afford, or `None` without a budget."""
        if self.wall_budget is None:
            return None
        return budget_module.project(
            self.wall_budget,
            costs=self.costs,
            spent=spent,
            admitted=admitted,
            gallery=self.gallery_reserve,
        )

    def _admitted(self) -> int:
        return self.walk.tally.get("tier:admitted", 0)

    def _batches_for(self, seats: int) -> int:
        """Batches enough to walk this many seats' projected nodes out.

        A ceiling, not a plan. Batches are not this mode's lever — the frontier
        empties on its own long before a generous ceiling binds, which is what
        `deep_run1` measured at 470 nodes of 2000 — so the number is sized to be
        out of the way and the clock is what actually stops the leg.
        """
        nodes = max(1.0, float(seats)) * self.costs.nodes_per_seat
        return max(DEFAULT_BATCHES, int(math.ceil(nodes / max(1, self.limits.batch))))

    def _reserve(self) -> None:
        """Take the gallery's share off what this run's own legs may spend.

        Every admission on the books promises the pass that follows this one a
        share of a frame, so the clock's budget falls as the run admits. Priced
        off admissions rather than off seats because admissions are the half of
        the ratio this run actually measures — a run whose seats turn out barren
        gets the room back, and one whose seats are fertile stops sooner with the
        frames it promised still payable.
        """
        if self.projection is None:
            return
        self.clock.budget = budget_module.spendable(
            self.projection.usable, self._admitted(), self.costs, gallery=self.gallery_reserve
        )

    # ------------------------------------------------------------------ seats
    def source(self, seats: int | None = None) -> list[roots_module.Seat]:
        """Fill seats, from both channels, and put a root on each framing.

        Called once by an unbudgeted run and once per round by a budgeted one.
        The seats **append**: same ledger, same root numbering, same
        [`roots.Standing`], so a second round descends from anchors the first did
        not spend and fills the family x band cells it left least full.
        """
        wanted = self.seats_wanted if seats is None else int(seats)
        self.round += 1
        started = time.monotonic()
        taken, sourcing = roots_module.sourced(
            wanted,
            self.rng,
            newton_share=self.limits.newton_share,
            anchors_per_family=self.limits.anchors_per_family,
            exclude=self.walk.ledger.path,
            standing=self.standing,
            clock=self.clock.leg(SOURCING) if self.wall_budget is not None else None,
            log=self.log,
        )
        sourcing["seconds"] = round(time.monotonic() - started, 2)
        sourcing["round"] = self.round
        sourcing["wanted"] = wanted
        sourcing["seats"] = len(taken)
        for offset, seat in enumerate(taken):
            index = len(self.seats) + offset
            # The seat itself goes on the record before its roots do. A root row
            # carries a viewport and a provenance; the seat carries the atom, the
            # ladder that reached it and the precision it was solved at, and a
            # row that had to be joined to a summary to be read would be a row
            # split across two files.
            self.walk.ledger.write("seat", seat_index=index, round=self.round, **seat.record())
            for framing in seat.framings:
                self.walk.add_root(
                    seat.family,
                    framing,
                    source=f"deep_{seat.channel}",
                    provenance={"seat_index": index, "round": self.round, **seat.provenance},
                )
        self.seats.extend(taken)
        self.sourcing = sourcing
        self.rounds.append(sourcing)
        self.walk.ledger.write("sourcing_round", **sourcing)
        self.log(f"[deep] round {self.round}: {len(taken)} seat(s) of {wanted} asked for")
        return taken

    # -------------------------------------------------------------------- run
    def run(self) -> dict:
        """Source, walk until the frontier or the clock runs out, and source again.

        The shallow walk's loop with three things added.

        **Every batch runs under a kill deadline** — [`BATCH_CEILING`], raised by
        this run's own measurements and never lowered — and a batch that is killed
        is *recorded as killed* and the run carries on to the next one. A deep
        expand is a real unit of work, fifty thousand iterations a sample and
        twice per candidate, and a run that discovers a hung one by never
        returning has lost the whole leg rather than one batch.

        **Every batch is gated before it starts.** Would this one put the run past
        what it may spend? If so the leg stops cleanly, with the arithmetic of the
        refusal in the record, rather than finding out afterwards.

        **A dry frontier is not the end of the run.** With budget left beyond the
        margin it is the signal to seat again — see [`_reseat`] — which is what
        turns `deep_run1`'s six unspent hours into breadth.
        """
        if not self.seats:
            self.source()
        while True:
            self._walk()
            if not self._reseat():
                break
        return self._summary()

    def _walk(self) -> None:
        """Expand batches until the batch ceiling, the frontier or the clock stops it."""
        leg = self.clock.leg(WALK)
        while self.batch_index < self.batches_allowed:
            self._reserve()
            decline = leg.may_start()
            if decline is not None:
                self.log(f"[deep] walk stopped on the budget: {decline}")
                return
            batch = self.walk.pop_batch()
            if not batch:
                return
            index = self.batch_index
            self.walk.batch_index = index
            self.batch_index += 1
            started = time.monotonic()
            try:
                with leg.unit() as unit:
                    self.walk.expand_batch(batch)
                    unit.ok = True
            except engine.EngineTimeout as killed:
                self.killed_batches += 1
                self.walk.ledger.write(
                    "batch_killed",
                    run_seed=self.seed,
                    batch=index,
                    nodes=[node["node_id"] for node in batch],
                    seconds=round(time.monotonic() - started, 2),
                    ceiling=leg.ceiling,
                    reason=str(killed),
                )
                self.log(f"[deep] batch {index} killed at {leg.ceiling:.0f}s")
                continue
            finally:
                self.batch_seconds.append(round(time.monotonic() - started, 2))
            self.walk.prune()
            self._tally("batches")
            self._tally("expanded", len(batch))

    def _reseat(self) -> bool:
        """Source another round into this same run, or say why not.

        Five refusals, and each of them is a different fact about the run.

        * No budget, or `--no-reseat`: nothing here is asked for.
        * The clock already declined a batch — the run is out of money, not out
          of frontier, and topping up seats it cannot walk is worse than stopping.
        * The frontier still holds a batch: the walk has not run out of places.
        * The projection affords no further seat.
        * A round that produced nothing. Both channels have finite supply — the
          anchor queues and fifty-odd ledger lineages — and a round that arrives
          empty is the supply saying so.
        """
        if self.wall_budget is None or not self.limits.reseat:
            return False
        if self.clock.stopped():
            return False
        if len(self.walk.frontier) >= self.limits.batch:
            return False
        self._reserve()
        room = self._project(spent=self.clock.elapsed(), admitted=self._admitted())
        if room is None or room.seats < 1:
            self.log("[deep] frontier dry and the budget affords no further seat")
            return False
        taken = self.source(room.seats)
        if not taken:
            self.log("[deep] frontier dry and both channels are out of supply")
            return False
        self.batches_allowed = self.batch_index + self._batches_for(len(taken))
        return True

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
            "rounds": self.rounds,
            "standing": self.standing.record(),
            "batches": self.walk.tally.get("batches", 0),
            "batch_seconds": self.batch_seconds,
            "killed_batches": self.killed_batches,
            "ceilings": {**HUNG_CEILING, "batch": BATCH_CEILING},
            "wall_budget": self.wall_budget,
            "projection": None if self.projection is None else self.projection.record(),
            "clock": self.clock.record(),
            # A run that ran out of clock and one that ran out of frontier both
            # finish with an empty frontier and a written ledger. The two are
            # different answers to "was this budget the binding constraint", and
            # that is the question the next run's seating is sized by.
            "budget_stopped": self.clock.stopped(),
            "lineages": self.walk.lineages(),
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
    "DEFAULT_BATCHES",
    "DEFAULT_SEATS",
    "HUNG_CEILING",
    "LEG_MARGIN",
    "LEG_MINIMUM",
    "LINEAGE_ADMISSIONS",
    "SOURCING",
    "WALK",
    "Deep",
    "Limits",
    "curation_clock",
    "gates",
    "run_clock",
    "walk_limits",
]
