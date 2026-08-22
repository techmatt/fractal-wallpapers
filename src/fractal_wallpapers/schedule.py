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

## The reservation is sized from the release ceiling, not from what will be seated

`-n` is a cap and not a quota — every run on record under-filled it — so a
reservation sized on it is an over-reservation whenever the release comes up
short, and the harvest is that much shorter than it could have been. That is the
error this takes deliberately: an over-reserved release leg finishes early, and
an under-reserved one runs past the time somebody has to be awake for.

## What the ratio does and does not cover

[`ACTIVE_TO_WALL`] is the harvest's own overhead — the per-batch refill, the
scan, the closing gate-flip re-score — measured over a scored hour that indexed
the hot tier alone. The archive-root ledger load is *bigger* than the start-up
inside that ratio and is reserved separately ([`LEDGER_LOAD_SECONDS`]), so the
two overlap by the minute or so the hot-tier start-up cost. The overlap is left
in: it reserves about a minute too much on a night eight hours long, and the
alternative is a term that has to be re-derived every time either measurement
moves.

**Nothing here paces anything.** The harvest's only backstop is still its own
active-minute budget, refusing to start a batch it cannot finish. This decides
what that budget is at launch and then has no further say — which is why the
margin is real money rather than a formality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

#: Wall seconds one finished release picture cost, at **4 worker processes**.
#: run9's release leg: 48 cold 2560x1440 ss4 rows in 2013.1 s of pass wall.
#:
#: Wall per finished picture and not the mean row — the rows run concurrently and
#: the mean row (134.0 s) is inflated by exactly the factor the workers divide
#: out. The number is tied to the worker count it was measured at and there is no
#: measurement at any other, so a night that reserves off this has to run its
#: release leg at `--workers 4`.
RELEASE_SECONDS_PER_PICTURE = 41.9

#: The worker count [`RELEASE_SECONDS_PER_PICTURE`] was measured at, stated so
#: the derived plan can say it rather than implying it.
RELEASE_WORKERS = 4

#: What the rest of `curate run` costs, per colorize attempt: the intake's rank
#: over the whole standing supply, the attempts themselves, the selection and
#: every record. run9 again — 2629.3 s elapsed against a 2013.1 s release pass
#: leaves 616.2 s for everything else, over 240 attempts.
#:
#: **This is the term the prompt's four did not have**, and leaving it out is not
#: conservative: the colorize leg runs between the harvest and the release, so a
#: night that reserved the release alone would spend a quarter of an hour of the
#: release's own reservation before the first full-resolution render started, and
#: the clock would stop the release leg short of the ceiling it was sized for.
#: At 80 slots it is about fourteen minutes.
CURATION_SECONDS_PER_ATTEMPT = 2.57

#: Colorize attempts a release slot buys. A copy of `curation.floors`'
#: `ATTEMPT_MULTIPLIER`, held here so this module stays import-free of curation
#: — and pinned against it by the suite, because two spellings of one number is
#: exactly what that module exists to end.
ATTEMPTS_PER_SLOT = 4

#: The closing re-score between the harvest and the release: `curate score` over
#: the ledgers the harvest just wrote, into curation's own sidecar. A fixed tail
#: of a minute or two whatever the harvest's length, because it reads the
#: standing supply's stored views rather than re-rendering them.
CLOSING_RESCORE_SECONDS = 120.0

#: What the cross-run memories cost before the first batch, over the archive
#: root. Outside `--minutes` by construction: no batch has started.
#:
#: **660 s, and that is a re-measurement.** The figure on record was 2m40s; the
#: 2026-08-21 smoke, with the launch's own `--ledgers`, took eleven minutes from
#: the ledger header to the first batch. The cause is structural rather than a
#: slow afternoon: `saturation.build`, `novelty.build` and `twins.build` each
#: call `ledgers.ledger_paths(root)`, which is an `rglob` over the *whole*
#: archive — a tree that is overwhelmingly `views/`, `fields/` and `tiles/` — so
#: a seek-bound disk is walked end to end three times before a row is read.
#:
#: The right fix is to stop keeping the ledgers inside the archive: they are
#: small text, they are read at the start of every run, and nothing else in that
#: tree is read at startup at all. Then this term goes to seconds and stops
#: needing to be reserved. Until then it is reserved at what it measures.
#:
#: The shipped `--ledgers artifacts` default indexes the hot tier's few ledgers
#: instead and costs a small fraction of this. It is the archive figure that is
#: reserved because cross-run novelty memory is the reason the flag is set at
#: all, and reserving the cheaper number would under-reserve the run that is
#: actually launched.
LEDGER_LOAD_SECONDS = 660.0

#: Wall minutes per active minute inside the harvest loop: the per-batch refill,
#: the scan, and the closing gate-flip re-score, measured over a scored hour on
#: the four parameter planes. See `supply/README.md`.
ACTIVE_TO_WALL = 1.13

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
    span: float
    release: float
    curation: float
    rescore: float
    ledger_load: float
    margin: float
    room: float
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
            "release_attempts": self.release_slots * ATTEMPTS_PER_SLOT,
            "release_seconds_per_picture": RELEASE_SECONDS_PER_PICTURE,
            "curation_seconds_per_attempt": CURATION_SECONDS_PER_ATTEMPT,
            "release_workers": RELEASE_WORKERS,
            "active_to_wall": ACTIVE_TO_WALL,
            "harvest_wall_minutes": round(self.room / 60.0, 2),
            "harvest_active_minutes": round(self.active_minutes, 2),
        }

    def lines(self) -> list[str]:
        """The derived plan, printed at startup before a batch is served."""
        return [
            f"finish by {self.finish_by:%Y-%m-%d %H:%M}, {self.span / 60.0:.0f} min from now",
            f"reserved: release {self.release / 60.0:.0f} min "
            f"({self.release_slots} slots x {RELEASE_SECONDS_PER_PICTURE:.1f}s at "
            f"{RELEASE_WORKERS} workers), rest of curate run {self.curation / 60.0:.0f} min "
            f"({self.release_slots * ATTEMPTS_PER_SLOT} attempts x "
            f"{CURATION_SECONDS_PER_ATTEMPT:.2f}s), closing re-score {self.rescore / 60.0:.0f} "
            f"min, ledger load {self.ledger_load / 60.0:.1f} min, margin "
            f"{self.margin / 60.0:.0f} min",
            f"harvest: {self.room / 60.0:.0f} min wall / {ACTIVE_TO_WALL:g} = "
            f"{self.active_minutes:.0f} ACTIVE minutes",
        ]


def plan(
    finish_by: str,
    release_slots: int,
    now: datetime | None = None,
    release_rate: float = RELEASE_SECONDS_PER_PICTURE,
    curation_rate: float = CURATION_SECONDS_PER_ATTEMPT,
    rescore: float = CLOSING_RESCORE_SECONDS,
    ledger_load: float = LEDGER_LOAD_SECONDS,
    margin: float = MARGIN_SECONDS,
    ratio: float = ACTIVE_TO_WALL,
) -> Plan:
    """The harvest's active-minute budget, derived from when the night must end.

    Refuses rather than returning a small number when the reservations do not fit
    inside the span: a harvest handed four minutes is not a short harvest, it is
    a night nobody sized, and the reservations it would be running against are
    the interesting half of the refusal.
    """
    now = datetime.now() if now is None else now
    at = next_at(finish_by, now)
    span = (at - now).total_seconds()
    slots = max(0, int(release_slots))
    release = slots * float(release_rate)
    curation = slots * ATTEMPTS_PER_SLOT * float(curation_rate)
    room = span - release - curation - rescore - ledger_load - margin
    if room <= 0:
        raise Unschedulable(
            f"{span / 60.0:.0f} min to {at:%H:%M} does not cover the "
            f"{(release + curation + rescore + ledger_load + margin) / 60.0:.0f} min reserved "
            f"after the harvest: release {release / 60.0:.0f} ({release_slots} slots), rest of "
            f"curate run {curation / 60.0:.0f}, re-score {rescore / 60.0:.0f}, ledger load "
            f"{ledger_load / 60.0:.1f}, margin {margin / 60.0:.0f}. Launch earlier, or ask for "
            f"fewer release slots."
        )
    return Plan(
        now=now,
        finish_by=at,
        release_slots=slots,
        span=span,
        release=release,
        curation=curation,
        rescore=float(rescore),
        ledger_load=float(ledger_load),
        margin=float(margin),
        room=room,
        active_minutes=room / 60.0 / float(ratio),
    )


__all__ = [
    "ACTIVE_TO_WALL",
    "ATTEMPTS_PER_SLOT",
    "CURATION_SECONDS_PER_ATTEMPT",
    "CLOSING_RESCORE_SECONDS",
    "LEDGER_LOAD_SECONDS",
    "MARGIN_SECONDS",
    "RELEASE_SECONDS_PER_PICTURE",
    "RELEASE_WORKERS",
    "Plan",
    "Unschedulable",
    "next_at",
    "plan",
]
