"""When the harvest has to stop, so that everything after it lands on time.

A production night is three invocations — harvest, `curate score`, `curate run` —
and only the first of them is sized in *active* minutes. That is the whole
difficulty: the thing a person actually wants to say is "be finished by seven",
and the number the harvest takes is neither a finish time nor even wall time. So
`--finish-by` is the translation, and this module is the arithmetic behind it.

```text
span    = finish_by - now
room    = span - release - curation - rescore - ledger_load - margin    (wall)
minutes = room / ACTIVE_TO_WALL                                         (active)
```

## Every subtraction is a measured leg, and it is named

Reserving "a couple of hours for the rest" is the version of this that cannot be
checked afterwards. Each term below is one leg, carrying the run it was measured
on, so a night that lands late is attributable to the term that was wrong rather
than to the reservation as a whole. [`Plan.record()`] puts all of them into the
harvest's own summary for exactly that reason: the readout can subtract what the
legs actually cost from what they were reserved and say which estimate to move.

## Two of the terms are read rather than written down

run10 landed **84 minutes inside** its finish-by, and every one of those minutes
was a term reserved at a number that had stopped being true. So the two terms
that move with the machine and with the run are no longer constants:

* [`release_rate`] reads the most recent tracked run's own release leg — wall per
  finished picture at the worker count it ran, scaled to this run's — because
  that rate halved the night `artifacts/curation` came off the archive and back
  onto NVMe, and nothing about the constant could have known;
* the closing re-score scales with what the harvest finds ([`rescore_seconds`]),
  because it re-reads the run's own gate survivors and a fixed tail keeps
  drifting as the nights get longer.

The re-score's dependence is circular — the harvest's room decides its find,
which decides the re-score, which decides the room — so [`plan`] solves it
instead of iterating.

## The reservation is sized from the release ceiling, not from what will be seated

`-n` is a cap and not a quota — every run on record under-filled it — so a
reservation sized on it is an over-reservation whenever the release comes up
short, and the harvest is that much shorter than it could have been. That is the
error this takes deliberately: an over-reserved release leg finishes early, and
an under-reserved one runs past the time somebody has to be awake for.

## What the ratio does and does not cover

[`ACTIVE_TO_WALL_DRAWING_VIEWS`] is the harvest's own overhead — the per-batch
refill, the scan, the closing gate-flip re-score — and it has *two* values
because it was measured on two different runs. A harvest that scores its own
gate renders draws no view at all, and the scan is then nearly free; one whose
judge reads some other geometry draws a view per survivor and it is not. Which
one a night gets is decided by the run's own config at plan time and printed with
the plan, because the difference is 36 minutes of walking on an eight-hour night.

**Nothing here paces anything.** The harvest's only backstop is still its own
active-minute budget, refusing to start a batch it cannot finish. This decides
what that budget is at launch and then has no further say — which is why the
margin is real money rather than a formality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

#: Wall seconds one finished release picture cost, at [`RELEASE_WORKERS`]. The
#: **fallback**, reached only on a checkout where no tracked run has finished a
#: release row: every real night reads the rate off the most recent tracked run
#: instead ([`release_rate`]).
#:
#: run9's release leg: 48 cold 2560x1440 ss4 rows in 2013.1 s of pass wall. Wall
#: per finished picture and not the mean row — the rows run concurrently and the
#: mean row (134.0 s) is inflated by exactly the factor the workers divide out.
#:
#: It is kept at run9's figure rather than refreshed to run10's 24.9 precisely
#: because it is the fallback: a clone with no release on record has no way to
#: know which disk its own `artifacts/curation` sits on, and the slower of the
#: two measurements is the one that over-reserves rather than under-reserves.
RELEASE_SECONDS_PER_PICTURE = 41.9

#: The worker count [`RELEASE_SECONDS_PER_PICTURE`] was measured at, and the
#: default a plan assumes the release leg will run at. Stated so the derived plan
#: can say it rather than implying it.
RELEASE_WORKERS = 4

#: What the rest of `curate run` costs, per colorize attempt: the intake's rank
#: over the whole standing supply, the attempts themselves, the selection and
#: every record. run9 again — 2629.3 s elapsed against a 2013.1 s release pass
#: leaves 616.2 s for everything else, over 240 attempts. run10 came in at 2.42
#: over 320, so the figure is left where it is: it is the term that has been
#: right twice.
#:
#: **This is the term the prompt's four did not have**, and leaving it out is not
#: conservative: the colorize leg runs between the harvest and the release, so a
#: night that reserved the release alone would spend a quarter of an hour of the
#: release's own reservation before the first full-resolution render started, and
#: the clock would stop the release leg short of the ceiling it was sized for.
#: At 80 slots it is about twenty minutes.
CURATION_SECONDS_PER_ATTEMPT = 2.57

#: Locations a release slot buys a colorize of. A copy of `curation.floors`'
#: `ATTEMPT_MULTIPLIER`, held here so this module stays import-free of curation
#: — and pinned against it by the suite, because two spellings of one number is
#: exactly what that module exists to end.
LOCATIONS_PER_SLOT = 4

#: Colorize attempts each of those locations costs, per head. The strange judge
#: tries every location it is given in **two** modes and the smooth judge in one,
#: so the attempt count is not the location count and the reservation has to know
#: the split. A copy of `curation.budget.MODES_PER_LOCATION`, pinned by the suite
#: for the same reason as the line above.
MODES_PER_STRANGE_LOCATION = 2

#: The share of the release's slots the strange judge fills, which is what turns
#: locations into attempts. A copy of `curation.run.STRANGE_SHARE`, pinned by the
#: suite. A night that will run `curate run --strange-share` at something else
#: says so at plan time; nothing here guesses.
STRANGE_SHARE = 0.5

#: What one row of the closing re-score costs: the read, the head, and the
#: sidecar upsert that rewrites the whole standing file. run10's leg — 282 s over
#: the 39,554 gate survivors its own ledger held.
CLOSING_RESCORE_SECONDS_PER_ROW = 0.00713

#: How many of those rows an active minute of harvest produces, which is what
#: makes the term scale instead of drift. run10 again: 39,554 gate survivors over
#: 317.28 active minutes.
#:
#: The two halves are kept apart because they move apart. The first is a fact
#: about the machine and the head; this is a fact about how fast the walk finds
#: ground, and the day the walk gets pickier only one of them changes.
SUPPLY_ROWS_PER_ACTIVE_MINUTE = 124.7

#: What the cross-run memories cost before the first batch, over the archive
#: root. Outside `--minutes` by construction: no batch has started.
#:
#: **120 s, down from 660, and the cost was removed rather than re-measured.**
#: The figure on record was 2m40s, then eleven minutes, then run10's 15.1; every
#: re-measurement was larger because the term was not measuring a load at all. It
#: was measuring three `rglob`s: `saturation.build`, `novelty.build` and
#: `twins.build` each asked `ledgers.ledger_paths(root)` for every `walk.jsonl`
#: under the archive, and that tree is overwhelmingly `views/`, `fields/` and
#: `tiles/`, so a seek-bound disk was walked end to end three times to find
#: thirty-two small text files. One pass measures **734.6 s**, 728 of it `tiles/`.
#:
#: A walk's run directory is a top-level name of the tree, so the ledgers were
#: never anywhere that needed searching for. `ledger_paths` looks each one up at
#: `<run directory>/walk.jsonl` — 0.08 s over the same archive — and the three
#: builders are handed one list, which leaves this term as what it always claimed
#: to be: reading the rows.
#:
#: What that costs, measured over run10's own 26 ledgers on the archive: 58.6 s
#: for all three builders, and the second and third were reading files the first
#: had just warmed. Reserved at roughly three times the one cold pass in that
#: measurement (28.4 s), because a launch reads them cold.
LEDGER_LOAD_SECONDS = 120.0

#: Wall minutes per active minute inside the harvest loop, for a run whose judge
#: draws its own views: the per-batch refill, the scan of every drawn view, and
#: the closing gate-flip re-score. Measured over a scored hour on the four
#: parameter planes. See `supply/README.md`.
ACTIVE_TO_WALL_DRAWING_VIEWS = 1.13

#: The same ratio for a run that **scores its own gate renders** — the shipped
#: arrangement, where the walk hands the head the picture the engine already made
#: and `scoring.rendered` stays at zero for the whole night.
#:
#: run10, whole: 4.2 minutes of overhead on 317.28 active — gate flips 133.1 s,
#: refill 2.8 s, the rest scan and checkpoint. Reserving the other ratio cost
#: that night 36 active minutes of walking, which is why the two are separate
#: constants rather than one number somebody lowered.
ACTIVE_TO_WALL_SCORING_GATE_RENDERS = 1.013

#: What is left unreserved, and it is not a formality — nothing downstream paces
#: this night. Twenty minutes, which is a little over the longest single release
#: row on record (run2's 1084.6 s): the release reservation is a *mean* rate, and
#: one row from the tail of that distribution lands entirely inside this.
MARGIN_SECONDS = 1200.0


class Unschedulable(ValueError):
    """A finish time leaves no room to harvest in, so nothing is guessed."""


def next_at(text: str, now: datetime) -> datetime:
    """The next `HH:MM` at or after `now`, as a local wall-clock time.

    Tomorrow's when it has already passed today, which is the only reading that
    makes `--finish-by 07:00` mean what it says at eleven at night. Equality goes
    to *tomorrow*: a finish time exactly now leaves nothing to do before it, and
    a night that scheduled itself zero minutes would report a plan rather than
    refuse one.
    """
    try:
        hour, minute = (int(part) for part in str(text).split(":"))
    except ValueError:
        raise Unschedulable(
            f"--finish-by {text!r} is not a HH:MM wall-clock time, e.g. 07:00"
        ) from None
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise Unschedulable(f"--finish-by {text!r} is not a time of day")
    at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return at if at > now else at + timedelta(days=1)


def active_to_wall(renders_views: bool) -> tuple[float, str]:
    """`(ratio, why)` — the overhead a night pays, decided by what it will draw.

    The condition is *whether the harvest renders views for its judge*, which is
    the thing `scoring.rendered` counts and the one difference between the two
    hours the two ratios were measured over.
    """
    if renders_views:
        return ACTIVE_TO_WALL_DRAWING_VIEWS, "the judge draws its own views"
    return ACTIVE_TO_WALL_SCORING_GATE_RENDERS, "the judge scores the gate renders"


def release_rate(workers: int = RELEASE_WORKERS) -> tuple[float, str]:
    """`(seconds per picture, where it came from)` at `workers` worker processes.

    Read off the most recent tracked run's own release leg, because this is the
    term that moved most and moved for a reason no constant could carry: run9
    measured 41.9 s with `artifacts/curation` on the archive and run10 measured
    24.9 s with it on NVMe, same code, same geometry.

    Scaled between worker counts as a straight inverse, which is the only rule
    the record supports and is stated rather than hidden: run10 realized 2.81x
    concurrency on four workers and run9 3.19x, so the scaling is *optimistic*
    off its measured point and a night that reserves at some other worker count
    is reserving on an extrapolation. There is a measurement at four.
    """
    from fractal_wallpapers.curation import records

    workers = max(1, int(workers))
    leg = records.latest_release_leg()
    if leg is None:
        return RELEASE_SECONDS_PER_PICTURE * RELEASE_WORKERS / workers, (
            f"the written-down rate: no tracked run has finished a release row "
            f"({RELEASE_SECONDS_PER_PICTURE:.1f}s at {RELEASE_WORKERS} workers)"
        )
    measured = leg["seconds"] / leg["rows"]
    return measured * leg["workers"] / workers, (
        f"{leg['run']}: {leg['seconds']:.1f}s over {leg['rows']} picture(s) at "
        f"{leg['workers']} worker(s) = {measured:.1f}s each"
    )


def release_attempts(release_slots: int, strange_share: float = STRANGE_SHARE) -> int:
    """Colorize attempts a release of `release_slots` slots costs.

    Locations first and modes second, because that is the order curation budgets
    in: each slot buys [`LOCATIONS_PER_SLOT`] locations, and the strange judge
    tries each of the locations it pays for in [`MODES_PER_STRANGE_LOCATION`]
    modes. Rounding follows `curation.budget.head_slots` so the two agree about
    an odd `n`.
    """
    slots = max(0, int(release_slots))
    strange = max(0, min(slots, int(round(slots * float(strange_share)))))
    smooth = slots - strange
    return LOCATIONS_PER_SLOT * (smooth + strange * MODES_PER_STRANGE_LOCATION)


def rescore_seconds(active_minutes: float) -> float:
    """What the closing re-score costs a harvest that walks `active_minutes`.

    It re-reads the run's own gate survivors, so it is a function of what the
    harvest found and not of the clock it found it on. Two measured facts
    composed — rows an active minute produces, seconds a row costs — rather than
    one blended rate, because they move apart.
    """
    rows = SUPPLY_ROWS_PER_ACTIVE_MINUTE * max(0.0, float(active_minutes))
    return CLOSING_RESCORE_SECONDS_PER_ROW * rows


@dataclass(frozen=True)
class Plan:
    """One night's arithmetic, whole: what was reserved and what is left to walk.

    Kept as the terms rather than as the answer, because "the harvest got five
    and a half hours" and "the harvest got five and a half hours because eighty
    release slots were reserved at run9's rate" are the same sentence until the
    reservation is on the record next to what it actually cost.
    """

    now: datetime
    finish_by: datetime
    release_slots: int
    attempts: int
    span: float
    release: float
    release_rate: float
    release_rate_source: str
    release_workers: int
    curation: float
    rescore: float
    ledger_load: float
    margin: float
    room: float
    ratio: float
    ratio_basis: str
    active_minutes: float

    def record(self) -> dict:
        """What the harvest's summary carries, so the readout can price it."""
        return {
            "started": self.now.isoformat(timespec="seconds"),
            "finish_by": self.finish_by.isoformat(timespec="seconds"),
            "span_minutes": round(self.span / 60.0, 2),
            "reserved_minutes": {
                "release": round(self.release / 60.0, 2),
                "curation": round(self.curation / 60.0, 2),
                "closing_rescore": round(self.rescore / 60.0, 2),
                "ledger_load": round(self.ledger_load / 60.0, 2),
                "margin": round(self.margin / 60.0, 2),
            },
            "release_slots": self.release_slots,
            "release_attempts": self.attempts,
            "release_seconds_per_picture": round(self.release_rate, 2),
            # Where the rate came from, in the record and not only on the console:
            # a night reserved off a measurement and a night reserved off the
            # written-down fallback are different nights, and the readout has to
            # be able to tell them apart months later.
            "release_rate_source": self.release_rate_source,
            "curation_seconds_per_attempt": CURATION_SECONDS_PER_ATTEMPT,
            "release_workers": self.release_workers,
            "active_to_wall": self.ratio,
            "active_to_wall_basis": self.ratio_basis,
            "rescore_seconds_per_row": CLOSING_RESCORE_SECONDS_PER_ROW,
            "supply_rows_per_active_minute": SUPPLY_ROWS_PER_ACTIVE_MINUTE,
            "harvest_wall_minutes": round(self.room / 60.0, 2),
            "harvest_active_minutes": round(self.active_minutes, 2),
        }

    def lines(self) -> list[str]:
        """The derived plan, printed at startup before a batch is served."""
        return [
            f"finish by {self.finish_by:%Y-%m-%d %H:%M}, {self.span / 60.0:.0f} min from now",
            f"reserved: release {self.release / 60.0:.0f} min "
            f"({self.release_slots} slots x {self.release_rate:.1f}s at "
            f"{self.release_workers} workers), rest of curate run {self.curation / 60.0:.0f} min "
            f"({self.attempts} attempts x {CURATION_SECONDS_PER_ATTEMPT:.2f}s), closing "
            f"re-score {self.rescore / 60.0:.1f} min "
            f"({SUPPLY_ROWS_PER_ACTIVE_MINUTE * self.active_minutes:.0f} rows x "
            f"{CLOSING_RESCORE_SECONDS_PER_ROW * 1000:.2f}ms), ledger load "
            f"{self.ledger_load / 60.0:.1f} min, margin {self.margin / 60.0:.0f} min",
            f"release rate from {self.release_rate_source}",
            f"harvest: {self.room / 60.0:.0f} min wall / {self.ratio:g} "
            f"({self.ratio_basis}) = {self.active_minutes:.0f} ACTIVE minutes",
        ]


def plan(
    finish_by: str,
    release_slots: int,
    now: datetime | None = None,
    *,
    renders_views: bool = False,
    release_workers: int = RELEASE_WORKERS,
    strange_share: float = STRANGE_SHARE,
    rate: tuple[float, str] | None = None,
    curation_rate: float = CURATION_SECONDS_PER_ATTEMPT,
    ledger_load: float = LEDGER_LOAD_SECONDS,
    margin: float = MARGIN_SECONDS,
) -> Plan:
    """The harvest's active-minute budget, derived from when the night must end.

    Refuses rather than returning a small number when the reservations do not fit
    inside the span: a harvest handed four minutes is not a short harvest, it is
    a night nobody sized, and the reservations it would be running against are
    the interesting half of the refusal.

    The re-score is solved for rather than subtracted, because it depends on the
    room it is being subtracted from. With `c` the re-score's cost per wall second
    of harvest, `room + c·room = span - everything else`, which is one line and
    exact where iterating to a fixed point would be neither.
    """
    now = datetime.now() if now is None else now
    at = next_at(finish_by, now)
    span = (at - now).total_seconds()
    slots = max(0, int(release_slots))
    workers = max(1, int(release_workers))
    ratio, basis = active_to_wall(renders_views)
    rate_seconds, rate_source = release_rate(workers) if rate is None else rate

    release = slots * float(rate_seconds)
    attempts = release_attempts(slots, strange_share)
    curation = attempts * float(curation_rate)
    fixed = span - release - curation - ledger_load - margin
    per_wall_second = (
        CLOSING_RESCORE_SECONDS_PER_ROW * SUPPLY_ROWS_PER_ACTIVE_MINUTE / (60.0 * ratio)
    )
    room = fixed / (1.0 + per_wall_second)
    active_minutes = room / 60.0 / ratio
    rescore = rescore_seconds(active_minutes)
    if room <= 0:
        raise Unschedulable(
            f"{span / 60.0:.0f} min to {at:%H:%M} does not cover the "
            f"{(span - fixed) / 60.0:.0f} min reserved after the harvest: release "
            f"{release / 60.0:.0f} ({release_slots} slots), rest of curate run "
            f"{curation / 60.0:.0f} ({attempts} attempts), ledger load {ledger_load / 60.0:.1f}, "
            f"margin {margin / 60.0:.0f} — before the closing re-score, which is a share of "
            f"whatever room is left. Launch earlier, or ask for fewer release slots."
        )
    return Plan(
        now=now,
        finish_by=at,
        release_slots=slots,
        attempts=attempts,
        span=span,
        release=release,
        release_rate=float(rate_seconds),
        release_rate_source=rate_source,
        release_workers=workers,
        curation=curation,
        rescore=rescore,
        ledger_load=float(ledger_load),
        margin=float(margin),
        room=room,
        ratio=ratio,
        ratio_basis=basis,
        active_minutes=active_minutes,
    )


__all__ = [
    "ACTIVE_TO_WALL_DRAWING_VIEWS",
    "ACTIVE_TO_WALL_SCORING_GATE_RENDERS",
    "CLOSING_RESCORE_SECONDS_PER_ROW",
    "CURATION_SECONDS_PER_ATTEMPT",
    "LEDGER_LOAD_SECONDS",
    "LOCATIONS_PER_SLOT",
    "MARGIN_SECONDS",
    "MODES_PER_STRANGE_LOCATION",
    "RELEASE_SECONDS_PER_PICTURE",
    "RELEASE_WORKERS",
    "STRANGE_SHARE",
    "SUPPLY_ROWS_PER_ACTIVE_MINUTE",
    "Plan",
    "Unschedulable",
    "active_to_wall",
    "next_at",
    "plan",
    "release_attempts",
    "release_rate",
    "rescore_seconds",
]
