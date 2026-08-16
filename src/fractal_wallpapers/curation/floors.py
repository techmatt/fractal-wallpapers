"""Every number that removes a picture between a find and a release, in one file.

Curation decides three times — which locations are worth colouring, which
coloured candidates are worth keeping, which kept candidates take one of the
release's slots — and each decision used to be a threshold typed at its own call
site. This module is the single owner of all of them, and the reason it exists is
that a threshold is a point on **one head's probability scale**: `0.20` on the
location head means "confidently junk" and means nothing at all on a head that
has been retrained since. A number with no owner is a number nobody can restate
when the scale under it moves.

## A cut either ACTS or it ANNOTATES, and it says which

Two of the numbers here remove a picture. Every other cut in curation is an
[`Advisory`]: it is computed, written onto the record, and never allowed to drop
a row. That split is deliberate and it is the shape the source project converged
on after a head flip took its intake from about fourteen hundred locations to
sixteen — because the cut that did it was a *frozen verdict*, stamped into a row
on the day it was minted and read as gospel by a pipeline that had moved on.

Nothing here is frozen. Every cut is a comparison against a probability that is
read at the moment it is used, so a different floor, a different order and a
different budget are all a re-read away, and a head flip degrades the *rank
quality* of the old rows instead of deleting them.

## The two that act

* [`JUNK_FLOOR`] — at intake, on the location head's `P(≥3)`. It says *do not
  spend colorize compute on this*. Deliberately coarse: it is not an operating
  point, no evaluation derived it, and it must not be made per-partition. It sits
  at the confidently-junk end of a scale and leaves every judgement of quality to
  the person at the sheet.
* the **good floor**, and it is not declared here. `supply.currency.GOOD_FLOOR`
  already owns "this find is worth keeping" on the same head and the same scale,
  and curation asks the same question at the slot guarantee. A second copy of one
  number under a second name is exactly the six-site restatement this module was
  written to end, so it is re-exported and never restated.

## The render heads only annotate, and that is a measurement gap being honest

A render head's floor would be its own production gate — the score above which a
finished picture is worth releasing. This project has never measured one: the two
render judges shipped at BORDERLINE and FAIL against their pre-registered bars,
so no number here would be a claim anybody could defend. What ships instead is an
advisory at each head's own natural rank cutpoint, written onto every release
record, so *"was a bar at this height buying anything"* stays answerable off the
accumulating record rather than only off runs made while a bar was enforcing.

Each advisory carries the sha256 of the shipped head it reads. That is this
repository's head version: a head is a file with a hash, the manifest names it,
and an advisory whose stamp disagrees with the live artifact refuses rather than
producing a plausible-looking column about a scale that no longer exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from fractal_wallpapers.supply.currency import GOOD_FLOOR

#: **The one enforcing cut curation owns.** At intake, on the location head's
#: stored `P(≥3)`: below this, a candidate does not get a colorize.
#:
#: Coarse on purpose, and read as a *semantic* statement rather than an operating
#: point — "the judging head is confident this is junk" — which is what makes it
#: the one cut a head flip can leave alone. Its cost is named rather than hidden:
#: the exact volume it removes drifts a little at each flip. Contrast the good
#: floor, which is a single-head cut and would have to be restated.
JUNK_FLOOR = 0.20

#: A partition emits at most `floor(passing supply / this)` pictures. The rule is
#: *show me one only if there were four to choose from*, and its whole point is
#: the zero: a partition with three floor-passing candidates ships nothing rather
#: than shipping its own least-bad row, and the run says so in one line.
THIN_SUPPLY_DIVISOR = 4

#: At most this many release picks from one near-duplicate group, per run. A cap,
#: not a quota — a group with one strong row still ships one. This is the whole
#: of the diversity rule, and it is deliberately something a person can read off
#: a sheet ("no more than two of one look") rather than a marginal-gain number.
CLUSTER_CAP = 2

#: Colorize attempts per release slot. A head's attempt budget is this times the
#: slots it is asked to fill, so the two heads are sized against release need and
#: never against each other.
#:
#: The same coarse four as [`THIN_SUPPLY_DIVISOR`], and the two meeting is not a
#: coincidence worth collapsing: they are about different populations — attempts
#: spent against candidates available — and a partition whose slots respect its
#: emit cap has `4·slots ≤ 4·floor(supply/4) ≤ supply`, so the two rules agree
#: exactly when they should. Moving either alone is a real change and reads as one.
ATTEMPT_MULTIPLIER = 4


class HeadStampMismatch(RuntimeError):
    """An advisory was asked to annotate against a head that is no longer live."""


@dataclass(frozen=True)
class Advisory:
    """One cut that is computed, recorded, and never allowed to remove a row.

    It carries the head whose scale its value lives on and the sha256 of the
    artifact it was set against, and [`annotates`] checks the stamp before it
    compares. An advisory **cannot** cut: there is no `gate()` here and no `acts`
    flag beside it, because a switch nobody may flip next to a method named for
    flipping it is an invitation.
    """

    #: The name a record writes.
    name: str
    #: The threshold, on `head`'s own probability scale.
    value: float
    #: Which head produced the score this is compared against.
    head: str
    #: The sha256 of the shipped artifact this value was set against.
    stamp: str
    #: One line: where this number came from.
    basis: str

    def check(self) -> None:
        """Raise unless the live shipped head is the one this value was set against."""
        live = live_stamp(self.head)
        if live != self.stamp:
            raise HeadStampMismatch(
                f"the {self.name!r} advisory ({self.value}) was set against "
                f"{self.head} sha256 {self.stamp[:12]}, but the live artifact is "
                f"{live[:12]}. {self.value} is a point on the first head's probability scale "
                f"and says nothing on the second's — re-state the advisory against the live "
                f"head and move the stamp, or restore the head the record names. Refusing to "
                f"annotate."
            )

    def annotates(self, score) -> bool | None:
        """`score >= value`, after the stamp check. `None` when there is no score.

        Tri-state on purpose. A render that failed is a decision with a reason and
        no score; recording it as `False` would make a crash indistinguishable
        from a bad wallpaper.
        """
        self.check()
        return None if score is None else float(score) >= self.value

    def __str__(self) -> str:
        return f"{self.name} {self.value:g} ({self.head} {self.stamp[:12]}, advisory)"


def live_stamp(head: str) -> str:
    """The sha256 of the head that is shipped right now, read at call time.

    Call time rather than import time, so a test can move the manifest and see
    the refusal, and so a long run that outlives a re-ship reads the re-ship
    rather than its own start-up snapshot.
    """
    from fractal_wallpapers.models import ship

    manifest = json.loads(ship.manifest_path().read_text(encoding="utf-8"))
    entry = (manifest.get("heads") or {}).get(head)
    if not entry or not entry.get("sha256"):
        raise HeadStampMismatch(
            f"no shipped artifact is recorded for {head!r}, so nothing can say which "
            f"probability scale a cut on it would live on. Ship the head first."
        )
    return str(entry["sha256"])


def _advisory(head: str, basis: str) -> Advisory:
    return Advisory(
        name=f"{head}_release",
        value=RELEASE_ADVISORY,
        head=head,
        stamp=live_stamp(head),
        basis=basis,
    )


#: Where the render heads' advisories sit: the natural rank cutpoint of a CORN
#: probability, which is the midpoint of the scale and not an operating point.
#: It answers "would this head call the picture a wallpaper", which is a sentence
#: about the head rather than a bar somebody measured.
RELEASE_ADVISORY = 0.50


def release_advisory(head: str) -> Advisory:
    """The advisory a finished-render head's score is annotated against.

    Built at call time so its stamp is the live artifact's, which is the whole
    point of the stamp: a cut object cached at import would carry the hash of
    whatever was shipped when the process started.
    """
    return _advisory(
        head,
        "the natural rank cutpoint of this head's own P(>=3) — not an operating point and "
        "no evaluation derived it. This project has never measured a release gate for a "
        "render head, and an advisory that pretended to be one would be a bar nobody could "
        "defend. It annotates so the question stays answerable off the record.",
    )


def passes_junk_floor(score) -> bool:
    """THE intake comparison. A missing score reads as not passing.

    A function rather than a bare `>=` at each site, for the same reason the good
    floor is one: an unscored candidate has no verdict to spend compute on, and
    that has to be decided in one place rather than three.
    """
    return score is not None and float(score) >= JUNK_FLOOR


def passes_good_floor(score) -> bool:
    """THE slot-guarantee trigger, on the same score at the higher of the two heights.

    Deliberately the good floor and not the junk floor. The guarantee asks *does
    this partition have anything worth keeping*, where intake only asks *is this
    not obvious junk*; a guarantee triggered at 0.20 would seat a partition whose
    whole supply the run itself would not call good.
    """
    from fractal_wallpapers.supply import currency

    return currency.passes_good_floor(score)


def emit_cap(passing: int) -> int:
    """The most a partition may release: `floor(passing supply / THIN_SUPPLY_DIVISOR)`."""
    return max(0, int(passing)) // THIN_SUPPLY_DIVISOR


def summary() -> dict:
    """Every cut, what it is on, and whether it acts. For a run's own banner."""
    return {
        "acting": {
            "junk_floor": {
                "value": JUNK_FLOOR,
                "head": "location",
                "where": "intake, the colorize draw",
            },
            "good_floor": {
                "value": GOOD_FLOOR,
                "head": "location",
                "where": "the slot guarantee's trigger",
                "owner": "supply.currency.GOOD_FLOOR — re-exported, never restated",
            },
        },
        "advisory": {"render heads": RELEASE_ADVISORY},
        "caps": {
            "thin_supply_divisor": THIN_SUPPLY_DIVISOR,
            "cluster_cap": CLUSTER_CAP,
            "attempt_multiplier": ATTEMPT_MULTIPLIER,
        },
    }


__all__ = [
    "ATTEMPT_MULTIPLIER",
    "CLUSTER_CAP",
    "GOOD_FLOOR",
    "JUNK_FLOOR",
    "RELEASE_ADVISORY",
    "THIN_SUPPLY_DIVISOR",
    "Advisory",
    "HeadStampMismatch",
    "emit_cap",
    "live_stamp",
    "passes_good_floor",
    "passes_junk_floor",
    "release_advisory",
    "summary",
]
