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

* [`JUNK_FLOOR`] — on the location head's `P(≥3)`, at **two** sites now. At
  intake it says *do not spend colorize compute on this*; in the walk it says
  *do not stand on this*, which is the expansion half of a cut that used to do
  expansion and booking together. One number, one meaning — "the judging head is
  confident this is junk" — and both sites read it from here rather than
  restating it. Deliberately coarse: it is not an operating point, no evaluation
  derived it, and it must not be made per-partition. It sits at the
  confidently-junk end of a scale and leaves every judgement of quality to the
  person at the sheet.
* the **good floor**, and it is not declared here. `supply.currency.GOOD_FLOOR`
  already owns "this find is worth keeping" on the same head and the same scale,
  and curation asks the same question at the slot guarantee. A second copy of one
  number under a second name is exactly the six-site restatement this module was
  written to end, so it is re-exported and never restated.

## The render heads: one bar acts now, the other still only annotates

A render head's floor would be its own production gate — the score above which a
finished picture is worth releasing. This project measured neither: the two render
judges shipped at BORDERLINE and FAIL against their pre-registered bars. So both
shipped as advisories at each head's own natural rank cutpoint, written onto every
release record, on the reasoning that *"was a bar at this height buying anything"*
stays answerable off the accumulating record rather than only off runs made while
a bar was enforcing.

The strange head's advisory has since been **promoted to an acting bar**, and by
a review verdict rather than by a measurement. Matt read `run2` on 2026-08-17: the
eleven released strange rows that sat below 0.50 were all bad and the head had
been right about every one of them, and the path that seated them was padding
strange slots out of thin passing supply. So [`STRANGE_RELEASE_BAR`] acts at
release selection — a strange row below it is not seated, and a strange slot with
no passing supply goes unfilled. It is still not a measured operating point; a
labels-derived restatement is future work the label accumulator holds. The smooth
head stays advisory: its own below-advisory rows belong to a mix-ratio decision
that has not been taken.

That split is why there are two types here. An [`Advisory`] is computed, recorded,
and structurally unable to remove a row — no `gate()`, no `seats()`, no `acts`
flag beside it. A [`Bar`] is the other thing, named as the other thing, and
[`release_cut`] hands out whichever one a head actually has.

Both carry the sha256 of the shipped head they read. That is this repository's
head version: a head is a file with a hash, the manifest names it, and a cut whose
stamp disagrees with the live artifact refuses rather than producing a
plausible-looking column — or, now, a seating decision — about a scale that no
longer exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from fractal_wallpapers.supply.currency import GOOD_FLOOR

#: **The one enforcing cut curation owns.** On the location head's `P(≥3)`:
#: below this, a candidate does not get a colorize at intake, and the walk does
#: not expand from it.
#:
#: Coarse on purpose, and read as a *semantic* statement rather than an operating
#: point — "the judging head is confident this is junk" — which is what makes it
#: the one cut a head flip can leave alone, and what lets two stages this far
#: apart share it. Its cost is named rather than hidden: the exact volume it
#: removes drifts a little at each flip. Contrast the good floor, which is a
#: single-head cut and would have to be restated.
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
class Cut:
    """A threshold on one head's probability scale, and the artifact it reads.

    The shared half of the two things below: the number, whose scale it lives on,
    the stamp that pins that scale, and the tri-state comparison. What a cut is
    *allowed to do* with that comparison is the subclass's whole content, and it
    is a type rather than a flag on purpose — a switch nobody may flip is an
    invitation, and a class that cannot be asked the question is not.
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
                f"the {self.name!r} cut ({self.value}) was set against "
                f"{self.head} sha256 {self.stamp[:12]}, but the live artifact is "
                f"{live[:12]}. {self.value} is a point on the first head's probability scale "
                f"and says nothing on the second's — re-state the cut against the live "
                f"head and move the stamp, or restore the head the record names. Refusing to "
                f"compare."
            )

    def clears(self, score) -> bool | None:
        """`score >= value`, after the stamp check. `None` when there is no score.

        Tri-state on purpose. A render that failed is a decision with a reason and
        no score; recording it as `False` would make a crash indistinguishable
        from a bad wallpaper.
        """
        self.check()
        return None if score is None else float(score) >= self.value


@dataclass(frozen=True)
class Advisory(Cut):
    """A cut that is computed, recorded, and never allowed to remove a row.

    An advisory **cannot** cut: there is no `gate()` here, no `seats()` and no
    `acts` flag beside it. A head whose cut acts gets a [`Bar`] instead, which is
    a different class with a different method, so the difference is visible at
    every call site rather than hidden in a boolean.
    """

    def annotates(self, score) -> bool | None:
        """What [`Cut.clears`] says, under the name that says it removes nothing."""
        return self.clears(score)

    def __str__(self) -> str:
        return f"{self.name} {self.value:g} ({self.head} {self.stamp[:12]}, advisory)"


@dataclass(frozen=True)
class Bar(Cut):
    """A cut that ACTS: a row below it does not take a release slot.

    The only one of these is the strange head's, and it exists by Matt's review
    verdict of 2026-08-17 rather than by a measurement — see the module docstring.
    Its `basis` says so, and it says so on every row it stamps, because a bar that
    reads like a measured operating point is exactly the frozen verdict this
    module was written to avoid.
    """

    def seats(self, score) -> bool:
        """Whether a row scoring this may take a slot.

        Strict where [`Cut.clears`] is tri-state, and that is the whole difference
        between recording a comparison and acting on one: a row with no score has
        nothing to seat it on, so it is not seated. The record keeps the third
        state; the seating decision cannot have one.
        """
        return self.clears(score) is True

    def __str__(self) -> str:
        return f"{self.name} {self.value:g} ({self.head} {self.stamp[:12]}, ACTING)"


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


#: Where a render head's advisory sits: the natural rank cutpoint of a CORN
#: probability, which is the midpoint of the scale and not an operating point.
#: It answers "would this head call the picture a wallpaper", which is a sentence
#: about the head rather than a bar somebody measured.
RELEASE_ADVISORY = 0.50

#: **The strange head's ACTING release bar.** The same height as the advisory it
#: was promoted from, and a second number rather than an alias of the first
#: because it is a second decision: the advisory is a property of the scale, this
#: is a policy about what may ship. Moving either alone is a real change and has
#: to read as one.
STRANGE_RELEASE_BAR = 0.50

#: Which render heads' release cut ACTS, and at what height. Everything not in
#: here gets an [`Advisory`]. Spelled out rather than imported from `budget.HEADS`
#: only because that module already imports this one; the suite checks the
#: spelling against it.
ACTING_RELEASE_BARS = {"strange_render": STRANGE_RELEASE_BAR}

#: Why the one acting bar acts. Carried onto every row it stamps, because a bar
#: whose provenance is a review verdict must not read like a measured one.
STRANGE_BAR_BASIS = (
    "an ACTING bar by Matt's review verdict of 2026-08-17, not by a measurement: every one "
    "of run2's eleven released strange rows below this height was bad and the head was right "
    "about all eleven, and the release path that seated them was padding strange slots from "
    "thin passing supply. Promoted from the advisory at the same height. A labels-derived "
    "restatement of the bar is future work; the label accumulator holds it."
)


def release_cut(head: str) -> Advisory | Bar:
    """The release cut on a finished-render head's score — whichever kind it has.

    THE dispatcher, and the reason a caller never decides for itself whether a
    head gates: [`ACTING_RELEASE_BARS`] is the one place that answers it, and
    every other site reads the answer off the returned type.

    Built at call time so its stamp is the live artifact's, which is the whole
    point of the stamp: a cut object cached at import would carry the hash of
    whatever was shipped when the process started.
    """
    if head in ACTING_RELEASE_BARS:
        return Bar(
            name=f"{head}_release",
            value=float(ACTING_RELEASE_BARS[head]),
            head=head,
            stamp=live_stamp(head),
            basis=STRANGE_BAR_BASIS,
        )
    return release_advisory(head)


def release_bar(head: str) -> Bar | None:
    """The acting bar this head is gated on, or `None` where nothing gates it.

    What the release selection asks. `None` is not a weaker bar — it is no bar,
    and the selection must go on picking exactly as it did before.
    """
    cut = release_cut(head)
    return cut if isinstance(cut, Bar) else None


def release_advisory(head: str) -> Advisory:
    """The advisory a finished-render head's score is annotated against.

    Only the heads with no acting bar have one. Asking for an advisory on a head
    whose cut acts is a category error rather than a weaker reading of it, so it
    refuses: a caller that got an object with no `seats` back would go on to seat
    a row the bar had rejected.
    """
    if head in ACTING_RELEASE_BARS:
        raise ValueError(
            f"{head!r}'s release cut ACTS at {ACTING_RELEASE_BARS[head]} — it is a Bar, not an "
            f"advisory. Call release_cut() and read the type, or release_bar() if the question "
            f"is whether this head gates."
        )
    return Advisory(
        name=f"{head}_release",
        value=RELEASE_ADVISORY,
        head=head,
        stamp=live_stamp(head),
        basis="the natural rank cutpoint of this head's own P(>=3) — not an operating point "
        "and no evaluation derived it. No release gate has been measured for this head, and "
        "an advisory that pretended to be one would be a bar nobody could defend. It "
        "annotates so the question stays answerable off the record.",
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
                "where": "intake, the colorize draw; and the walk's expansion tier",
            },
            "good_floor": {
                "value": GOOD_FLOOR,
                "head": "location",
                "where": "the slot guarantee's trigger; and the walk's booking tier",
                "owner": "supply.currency.GOOD_FLOOR — re-exported, never restated",
            },
            **{
                f"{head}_release_bar": {
                    "value": value,
                    "head": head,
                    "where": "release selection: a row below it is not seated, and a slot "
                    "with no passing supply goes unfilled",
                    "basis": STRANGE_BAR_BASIS,
                }
                for head, value in sorted(ACTING_RELEASE_BARS.items())
            },
        },
        "advisory": {
            "render heads with no acting bar": RELEASE_ADVISORY,
            "acting instead": sorted(ACTING_RELEASE_BARS),
        },
        "caps": {
            "thin_supply_divisor": THIN_SUPPLY_DIVISOR,
            "cluster_cap": CLUSTER_CAP,
            "attempt_multiplier": ATTEMPT_MULTIPLIER,
        },
    }


__all__ = [
    "ACTING_RELEASE_BARS",
    "ATTEMPT_MULTIPLIER",
    "CLUSTER_CAP",
    "GOOD_FLOOR",
    "JUNK_FLOOR",
    "RELEASE_ADVISORY",
    "STRANGE_BAR_BASIS",
    "STRANGE_RELEASE_BAR",
    "THIN_SUPPLY_DIVISOR",
    "Advisory",
    "Bar",
    "Cut",
    "HeadStampMismatch",
    "emit_cap",
    "live_stamp",
    "passes_good_floor",
    "passes_junk_floor",
    "release_advisory",
    "release_bar",
    "release_cut",
    "summary",
]
