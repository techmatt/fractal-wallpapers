"""The wall clock a long run is held to, and what it may still start.

A run sized only by `-n` is sized by nothing at all once the numbers get real: a
release row measured between sixteen seconds and three and a half minutes turns
"twenty rows" into an answer between six minutes and an hour, and the only way to
find out which is to wait. `--wall-budget` is the other half of the sizing — the
run promises to be finished by a certain time — and this module is what makes the
promise true.

## The gate is prospective, and that is the whole idea

A budget checked *after* a unit finishes is a budget that reports overruns; it
does not prevent them. So nothing here asks "am I over?" — it asks, before each
unit, **"would starting this one put me over?"**, and stops cleanly at that
boundary if the answer is yes:

```text
elapsed + estimate(unit class) + margin(leg) > budget   ->   do not start it
```

Three things in that line are worth their own paragraph.

**The estimate comes from this run's own units.** Not from a constant, not from
the last run's record: the same plan on a machine with a busy GPU, or at a depth
that costs four times the iterations, is a different number, and a stale estimate
is worse than none because it is trusted. The estimate of a class is **the longest
one this run has finished** — a stop is cheap and an overrun is not, so the gate
errs by declining.

**A class with nothing measured yet is covered by a hard timeout instead.** The
first unit of a class has no estimate by construction, and letting it run
unbounded to obtain one would put the whole budget at the mercy of one hung
render. It gets what is left after the margin as a *kill* deadline, and it only
starts at all if that leaves it a real chance of finishing ([`UNMEASURED_MINIMUM`]).

**The margin is per leg, not once for the run.** What has to happen after a leg
stops is different for each leg — a stop in the colorize leg still has a
selection, a release plan and every record to write; a stop in the release leg
has the records only — and a single run-level margin is either too small for the
first or wasted on the second.

## A budget stop is a clean stop, and it says so

Stopping means: no unit is half done, every record is written for everything that
finished, and the summary reads `budget_stopped` — which is a different outcome
from `completed` and a different one again from `crashed`. A run that merely
stopped early and reported success would be indistinguishable from a run whose
supply ran out, which is exactly the question a short release is asked.

## The hung-unit backstop

Every unit runs under a kill deadline whether or not the gate is armed, because a
unit that never returns is not a budget problem — it is the failure the budget
cannot see. The deadline is imposed where the wall clock actually goes, on the
engine call ([`engine.deadline`]), so a killed unit comes back as a *failed row*
with its reason and the run carries on to the next one. Worker processes already
carry a job object that takes their engine down with them; this is the same
discipline for the units that run in the parent.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from fractal_wallpapers import engine

#: The two legs a run spends its wall clock in, and what each one reserves for
#: the work that must still happen after it stops. Seconds, and deliberately
#: generous against a measured teardown of about a second: the cost of reserving
#: too much is one unit not attempted, and the cost of reserving too little is a
#: run that breaks the promise the budget exists to make.
COLORIZE, RELEASE = "colorize", "release"
TEARDOWN_MARGIN = {COLORIZE: 30.0, RELEASE: 20.0}

#: The margin a leg not named above gets.
DEFAULT_MARGIN = 30.0

#: What a unit may take before it is killed, as a multiple of the longest one of
#: its class this run has already finished, and the floor under that multiple so
#: a class of very fast units does not get a kill deadline measured in
#: milliseconds. A hung render is what this catches; a slow one is not a fault.
HUNG_MULTIPLE = 4.0
HUNG_FLOOR = 60.0

#: What the first unit of a class gets, before this run has measured one: the
#: budget's own remainder, or this ceiling in a run with no budget at all. The
#: first unit of a class must never be effectively unbounded — that is the one
#: hole a prospective gate cannot close by itself.
UNMEASURED_CEILING = 1800.0

#: How much room, after the margin, a unit needs before this run will risk one of
#: a class it has never measured. Per leg like the margin, and for a stronger
#: reason: a candidate colorize is seconds at 640×360 and a release render was
#: measured between 16 and 196 seconds at 2560×1440 supersampled, so one number
#: for both is either most of a colorize budget or a rounding error on a release.
#: A few times the class's own typical unit — enough that anything near typical
#: finishes, not so much that a run declines work it could have done.
UNMEASURED_MINIMUM = {COLORIZE: 10.0, RELEASE: 60.0}

#: What a leg not named above needs.
DEFAULT_UNMEASURED_MINIMUM = 60.0


@dataclass(frozen=True)
class Decline:
    """One unit the gate refused to start, and the arithmetic behind the refusal.

    Kept whole rather than reduced to a message, because "the run stopped early"
    and "the run stopped early with eleven minutes of its budget unspent because
    one release row is measured at nine" are the same sentence until the numbers
    are in the record.
    """

    leg: str
    elapsed: float
    estimate: float | None
    margin: float
    budget: float
    remaining: float
    minimum: float = DEFAULT_UNMEASURED_MINIMUM

    @property
    def reason(self) -> str:
        if self.estimate is None:
            return (
                f"{self.leg}: {self.remaining:.0f}s left of a {self.budget:.0f}s budget and "
                f"{self.margin:.0f}s of it reserved for teardown, which is under the "
                f"{self.minimum:.0f}s this run needs to risk a unit it has never measured"
            )
        return (
            f"{self.leg}: {self.elapsed:.0f}s spent of a {self.budget:.0f}s budget, and the "
            f"next unit is estimated at {self.estimate:.0f}s against {self.remaining:.0f}s "
            f"left with {self.margin:.0f}s reserved for teardown"
        )

    def __str__(self) -> str:
        return self.reason

    def row(self) -> dict:
        return {
            "leg": self.leg,
            "elapsed": round(self.elapsed, 1),
            "estimate": None if self.estimate is None else round(self.estimate, 1),
            "margin": self.margin,
            "minimum": self.minimum,
            "budget": self.budget,
            "remaining": round(self.remaining, 1),
            "reason": self.reason,
        }


@dataclass
class Unit:
    """One unit of work in flight: what it was allowed, and what it did.

    `expired` is the killed-versus-failed distinction. A unit that raised because
    its location has no field and a unit that was killed at its deadline both come
    back as failed rows, and only one of them is a fault of this run's own making.
    """

    leg: str
    limit: float | None
    seconds: float = 0.0
    ok: bool = False
    expired: bool = False


@dataclass
class Leg:
    """One leg's view of the clock: what it may start, and for how long.

    Handed to the code that does the work, so the release pass takes one object
    rather than three callbacks and neither it nor the colorize loop has to know
    how an estimate is formed.
    """

    clock: Clock
    name: str
    margin: float
    minimum: float = DEFAULT_UNMEASURED_MINIMUM
    seen: list[float] = field(default_factory=list)
    killed: int = 0

    def estimate(self) -> float | None:
        """The longest unit of this class the run has finished, or `None` at zero.

        The longest and not the mean: the gate's job is to not overrun, and the
        distribution this is drawn from is the one where a single row costs twelve
        times the median because it is twelve times as deep.
        """
        return max(self.seen) if self.seen else None

    def may_start(self) -> Decline | None:
        """`None` to go ahead, or the `Decline` that stops the leg cleanly here."""
        budget = self.clock.budget
        if budget is None:
            return None
        elapsed = self.clock.elapsed()
        remaining = budget - elapsed
        estimate = self.estimate()
        if estimate is None:
            if remaining - self.margin < self.minimum:
                return self._decline(elapsed, None, budget, remaining)
            return None
        if elapsed + estimate + self.margin > budget:
            return self._decline(elapsed, estimate, budget, remaining)
        return None

    def _decline(self, elapsed, estimate, budget, remaining) -> Decline:
        decline = Decline(
            leg=self.name,
            elapsed=elapsed,
            estimate=estimate,
            margin=self.margin,
            budget=budget,
            remaining=remaining,
            minimum=self.minimum,
        )
        self.clock.declines.append(decline)
        return decline

    def timeout(self) -> float | None:
        """How long the next unit of this leg may take before it is killed.

        Two bounds and the tighter one wins: the hung-unit multiple over what this
        class costs, and whatever the budget actually has left. The second is what
        makes the deadline a promise rather than an estimate — a unit that passed
        the gate on a four-second estimate does not get to spend a minute.
        """
        estimate = self.estimate()
        if estimate is None:
            limit = UNMEASURED_CEILING
        else:
            limit = max(HUNG_FLOOR, HUNG_MULTIPLE * estimate)
        if self.clock.budget is not None:
            limit = min(limit, max(0.0, self.clock.remaining() - self.margin))
        return limit

    def observe(self, seconds: float, ok: bool = True, expired: bool = False) -> None:
        """Take one finished unit into the estimate — if it is one worth taking.

        Only a unit that *succeeded* teaches the estimate anything. A row that
        failed in a tenth of a second would drag the gate's estimate down to
        nothing and let the run start a unit it cannot afford; a row that was
        killed at its deadline says how long the deadline was, not how long the
        work is.
        """
        if expired:
            self.killed += 1
            return
        if ok:
            self.seen.append(float(seconds))

    @contextmanager
    def unit(self):
        """Run one unit under this leg's kill deadline, and time it.

        The caller sets `ok` on the yielded unit, because the units this paces do
        not raise on failure — a failed colorize is a recorded row, and a record
        with an error in it must not teach the gate that the work is cheap.
        """
        limit = self.timeout()
        running = Unit(leg=self.name, limit=limit)
        started = self.clock.now()
        bound = engine.Bound(limit)
        try:
            with engine.deadline(limit) as bound:
                yield running
        finally:
            running.seconds = self.clock.now() - started
            running.expired = bool(bound.expired)
            self.observe(running.seconds, running.ok, running.expired)

    def record(self) -> dict:
        return {
            "margin": self.margin,
            "unmeasured_minimum": self.minimum,
            "completed": len(self.seen),
            "killed": self.killed,
            "longest": round(max(self.seen), 1) if self.seen else None,
            "estimate": None if self.estimate() is None else round(self.estimate(), 1),
        }


class Clock:
    """The run's wall clock: one budget, one start, one leg per kind of unit.

    Started at construction, which is called at the run's entry — the budget
    covers the *whole* run, intake through the last release render, because a
    budget that starts when the expensive part starts is a budget that is already
    wrong by however long the setup took.
    """

    def __init__(
        self,
        budget: float | None = None,
        margins: dict | None = None,
        minimums: dict | None = None,
        now=None,
    ):
        self.now = now or time.monotonic
        self.budget = None if budget is None else max(0.0, float(budget))
        self.started = self.now()
        self.margins = dict(TEARDOWN_MARGIN if margins is None else margins)
        self.minimums = dict(UNMEASURED_MINIMUM if minimums is None else minimums)
        self.legs: dict[str, Leg] = {}
        self.declines: list[Decline] = []

    def elapsed(self) -> float:
        return self.now() - self.started

    def remaining(self) -> float:
        """Seconds left, or infinity when the run promised nothing."""
        return float("inf") if self.budget is None else self.budget - self.elapsed()

    def leg(self, name: str) -> Leg:
        if name not in self.legs:
            self.legs[name] = Leg(
                clock=self,
                name=name,
                margin=float(self.margins.get(name, DEFAULT_MARGIN)),
                minimum=float(self.minimums.get(name, DEFAULT_UNMEASURED_MINIMUM)),
            )
        return self.legs[name]

    def stopped(self) -> bool:
        """Whether the gate declined anything — the budget-stopped outcome itself."""
        return bool(self.declines)

    def record(self) -> dict:
        """What the clock did, for the run's summary."""
        return {
            "wall_budget": self.budget,
            "elapsed": round(self.elapsed(), 1),
            "legs": {name: leg.record() for name, leg in sorted(self.legs.items())},
            "declined": [decline.row() for decline in self.declines],
        }


__all__ = [
    "COLORIZE",
    "DEFAULT_MARGIN",
    "DEFAULT_UNMEASURED_MINIMUM",
    "HUNG_FLOOR",
    "HUNG_MULTIPLE",
    "RELEASE",
    "TEARDOWN_MARGIN",
    "UNMEASURED_CEILING",
    "UNMEASURED_MINIMUM",
    "Clock",
    "Decline",
    "Leg",
    "Unit",
]
