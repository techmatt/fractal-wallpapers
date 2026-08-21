"""What a deep run costs, and how many seats a wall budget buys.

A deep run is priced in **seats** — a leg's cost is dominated by producing a
place to stand — so sizing one is a division: take the wall clock the run is
allowed, take out what is not walking time, and divide by what a seat costs end
to end. This module is that division, and the only place a per-seat number
lives.

The reason it exists is a measured failure. `deep_run1` was given eight hours
and spent **two hours ten minutes** of them. Its seat count was picked by hand
from conservative estimates, the frontier emptied at 470 of 2000 node slots, and
the run finished with three quarters of its budget unspent — which is not a run
that stopped early, it is a run that was **sized wrong before it started**. The
fix is to stop guessing: every number below was read off that run's own record.

## What one seat cost, at `deep_run1`'s measurements

Thirty-two seats, an idle machine, the shipped location head:

```text
sourcing   379 s / 32 seats             11.8 s   a stalled ladder costs what a seated one does
walk       290 s / 470 nodes             0.62 s  x 14.7 nodes a seat  =  9.1 s
gallery    254 frames / 741 admissions   0.34    x 12.8 s a frame x 23.2 a seat  =  102 s
                                                                        ------
                                                                        123 s a seat
```

**The gallery is two thirds of it and it is not optional.** `deep walk` does not
draw a finished frame — the gallery is the pass that follows it — but a run that
spends its whole budget walking is a run with no time left to look at what it
found, and `deep_run1` spent 61 of its 130 minutes there. So the reserve is
taken out of the budget before the seats are counted, and a walk-only run says
so explicitly rather than getting the room by accident.

## The reserve is priced off admissions, because admissions are measured

Seats are what a run buys; **admissions are what it makes**, and the ratio
between them is the one number here a run can check against itself as it goes.
So the gallery's share of the clock is `admissions x`
[`Costs.gallery_per_admission`], recomputed from the run's own tally at every
batch. A run whose seats turn out to be barren hands the walk back the room its
gallery is not going to need; one whose seats are fertile stops sooner, with the
frames it promised still payable.

## Two margins, because two different things go wrong

[`MARGIN_SHARE`] is estimate error, and it scales: every figure above is
`n = 1`, and a run at four times the seats is four times as exposed to each of
them being wrong. [`FIXED_RESERVE`] is the part that does *not* scale — staging,
the checks, the readouts and the report, which `deep_run1` measured at about
half an hour whatever the machine was doing. One number for both would be too
small for the first at eight hours and most of the budget at one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Share of a wall budget held back against the cost model being wrong.
#:
#: Every figure in [`Costs`] is one run's measurement, so the projection is a
#: point estimate with no spread behind it. Fifteen per cent is a seat count
#: rounded down rather than a promise the arithmetic cannot keep — and the
#: failure it guards is asymmetric: an over-seated run overruns its budget, an
#: under-seated one merely leaves room, which is the mistake `deep_run1` made
#: and the cheaper of the two by a wide margin.
MARGIN_SHARE = 0.15

#: Seconds held back for the work that is not seats, whatever the budget is.
#:
#: Staging, the pre-flight checks, the readouts and the writing: `deep_run1`
#: spent about thirty minutes there against seventy-five of compute, and none of
#: it moves when the seat count does.
FIXED_RESERVE = 1800.0


@dataclass(frozen=True)
class Costs:
    """What one seat costs, in seconds, from `deep_run1`'s own record.

    Every field is a division of two numbers that run reported. They are
    defaults and not constants: a run that measures its own may hand a different
    table in, which is the only way this stops being an `n = 1` estimate.
    """

    #: Sourcing seconds a seat costs — 379 s over 32 seats, both channels.
    #: Priced per seat *delivered* rather than per descent attempted, because a
    #: ladder that stalls costs what one that arrives does and a run buys seats.
    sourcing_per_seat: float = 11.8
    #: Frontier nodes one seat's roots go on to produce — 470 over 32.
    nodes_per_seat: float = 14.7
    #: Walk seconds a node costs — 290 s over 470 nodes, median batch 4.3 s.
    seconds_per_node: float = 0.62
    #: Admissions one seat books — 741 over 32.
    admissions_per_seat: float = 23.2
    #: Gallery frames drawn per admission — 254 of 741. Below one because a
    #: gallery is a *selection*: a quota per family x band cell, then rank.
    gallery_frames_per_admission: float = 0.343
    #: Seconds a gallery frame costs at evaluation geometry — 1920x1080 ss2,
    #: median 12.8 s of the 5.4-28.0 s measured, colorize included.
    seconds_per_gallery_frame: float = 12.8

    @property
    def walk_per_seat(self) -> float:
        """Walk seconds one seat's nodes cost."""
        return self.nodes_per_seat * self.seconds_per_node

    @property
    def gallery_per_admission(self) -> float:
        """Gallery seconds one admission books — the reserve's unit."""
        return self.gallery_frames_per_admission * self.seconds_per_gallery_frame

    @property
    def gallery_per_seat(self) -> float:
        """Gallery seconds one seat is expected to book, through its admissions."""
        return self.admissions_per_seat * self.gallery_per_admission

    def per_seat(self, *, gallery: bool = True) -> float:
        """What one seat costs end to end, the gallery included unless told not to.

        `gallery=False` is a **walk-only** run: the ledger and nothing else. It
        is not a saving — it is a different piece of work, and a run that takes
        it and then draws a gallery anyway has no budget for one.
        """
        legs = self.sourcing_per_seat + self.walk_per_seat
        return legs + self.gallery_per_seat if gallery else legs

    def record(self) -> dict:
        return {
            "sourcing_per_seat": self.sourcing_per_seat,
            "nodes_per_seat": self.nodes_per_seat,
            "seconds_per_node": self.seconds_per_node,
            "admissions_per_seat": self.admissions_per_seat,
            "gallery_frames_per_admission": self.gallery_frames_per_admission,
            "seconds_per_gallery_frame": self.seconds_per_gallery_frame,
            "walk_per_seat": round(self.walk_per_seat, 2),
            "gallery_per_admission": round(self.gallery_per_admission, 2),
            "per_seat": round(self.per_seat(), 2),
        }


def usable(
    budget: float,
    *,
    margin_share: float = MARGIN_SHARE,
    fixed_reserve: float = FIXED_RESERVE,
) -> float:
    """The part of a wall budget a run may plan against — both margins taken out."""
    return max(0.0, float(budget) * (1.0 - float(margin_share)) - float(fixed_reserve))


def spendable(room: float, admitted: int, costs: Costs, *, gallery: bool = True) -> float:
    """What the run's own two legs may spend, the gallery's share taken out.

    The one line that keeps a walk from eating the pass that reads it: the room
    the sourcing and walk legs are held to is the usable budget less what the
    admissions already on the books have promised the gallery.
    """
    if not gallery:
        return max(0.0, float(room))
    return max(0.0, float(room) - max(0, int(admitted)) * costs.gallery_per_admission)


@dataclass(frozen=True)
class Projection:
    """How many seats a budget buys, and every number the answer was made of.

    Kept whole rather than reduced to an integer, because "this run seated 185"
    and "this run seated 185 because it read 22,680 s of usable budget against
    123 s a seat" are the same sentence until the arithmetic is in the record.
    """

    budget: float
    usable: float
    committed: float
    room: float
    seats: int
    gallery: bool
    costs: Costs = field(default_factory=Costs)

    @property
    def per_seat(self) -> float:
        return self.costs.per_seat(gallery=self.gallery)

    def record(self) -> dict:
        return {
            "wall_budget": round(self.budget, 1),
            "usable": round(self.usable, 1),
            "committed": round(self.committed, 1),
            "room": round(self.room, 1),
            "per_seat": round(self.per_seat, 2),
            "seats": self.seats,
            "nodes": round(self.seats * self.costs.nodes_per_seat),
            "gallery_reserved": self.gallery,
            "margin_share": MARGIN_SHARE,
            "fixed_reserve": FIXED_RESERVE,
            "costs": self.costs.record(),
        }


def project(
    budget: float,
    *,
    costs: Costs | None = None,
    spent: float = 0.0,
    admitted: int = 0,
    gallery: bool = True,
    margin_share: float = MARGIN_SHARE,
    fixed_reserve: float = FIXED_RESERVE,
) -> Projection:
    """How many more seats this budget can still afford.

    One function for both of the questions a budgeted run asks, because they are
    the same question with different arguments. At the start `spent` and
    `admitted` are zero and the answer is the initial seating; when the frontier
    empties they are the run's own measurements and the answer is how much more
    it may seat **into the same run**. Nothing here knows which call it is.
    """
    costs = costs or Costs()
    total = usable(budget, margin_share=margin_share, fixed_reserve=fixed_reserve)
    committed = max(0.0, float(spent)) + (
        max(0, int(admitted)) * costs.gallery_per_admission if gallery else 0.0
    )
    room = max(0.0, total - committed)
    per_seat = costs.per_seat(gallery=gallery)
    return Projection(
        budget=float(budget),
        usable=total,
        committed=committed,
        room=room,
        seats=int(room // per_seat) if per_seat > 0 else 0,
        gallery=gallery,
        costs=costs,
    )


__all__ = [
    "FIXED_RESERVE",
    "MARGIN_SHARE",
    "Costs",
    "Projection",
    "project",
    "spendable",
    "usable",
]
