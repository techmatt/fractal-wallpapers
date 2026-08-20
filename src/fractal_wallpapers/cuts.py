"""What a cut on a head's probability scale is, and the stamp that pins it.

A threshold in this project is never a bare float. `0.20` means "the location
head is confident this is junk" only on the scale of *one* artifact, and the day
that artifact is replaced the same float is a point on a scale that no longer
exists. So a cut carries the head it reads, the sha256 of the artifact its height
was set against, and a comparison that refuses when the two disagree.

This module holds the **kinds**. It does not hold a single number: every value
lives with whoever owns the decision it makes — [`curation.floors`] for the
numbers that stand between a find and a release, [`supply.currency`] for what a
find is worth — and both reach the same types from here.

They have to reach them from one place, and that is the whole reason this module
is not inside either of them. Three of this repository's cuts sit on the location
head's scale, the junk floor in curation and the good floor and the great cut in
supply, and a shared *class* imported from one of those two would make the supply
engine depend on curation or the reverse. A type with no numbers in it depends on
neither.

## The two kinds, and why they are types rather than a flag

An [`Advisory`] is computed, recorded, and structurally unable to remove a row:
there is no `acts()` on it. A [`Bar`] is the other thing, named as the other
thing. A switch nobody may flip is an invitation; a class that cannot be asked
the question is not.

## The two kinds stamp themselves differently

An advisory is the *natural cutpoint of whatever scale is live*, so it stamps the
live artifact and only catches a re-ship that lands mid-run. A bar is a number
somebody measured on one named head, so it stamps **that** head —
[`Restatement.head_sha256`] — and refuses from the first call after a flip,
before anything has been decided against the wrong scale.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


class HeadStampMismatch(RuntimeError):
    """A cut was asked to read a score from a head it was not set against."""


@dataclass(frozen=True)
class Cut:
    """A threshold on one head's probability scale, and the artifact it reads.

    The shared half of the two things below: the number, whose scale it lives on,
    the stamp that pins that scale, and the tri-state comparison. What a cut is
    *allowed to do* with that comparison is the subclass's whole content.
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

    An advisory **cannot** cut: there is no `acts()` here and no flag beside it.
    A head whose cut acts gets a [`Bar`] instead, which is a different class with
    a different method, so the difference is visible at every call site rather
    than hidden in a boolean.
    """

    def annotates(self, score) -> bool | None:
        """What [`Cut.clears`] says, under the name that says it removes nothing."""
        return self.clears(score)

    def __str__(self) -> str:
        return f"{self.name} {self.value:g} ({self.head} {self.stamp[:12]}, advisory)"


@dataclass(frozen=True)
class Bar(Cut):
    """A cut that ACTS: below it, a row does not get whatever this cut guards.

    Four of them exist — the location head's junk floor, good floor and great
    cut, and the strange head's release bar — and what they guard is different at
    every site: a colorize, a rung of the walk, a slot guarantee, a class in the
    currency, a release seat. The comparison is one comparison, so it has one
    name and one method.
    """

    def acts(self, score) -> bool:
        """Whether a row scoring this is on the passing side of the cut.

        Strict where [`Cut.clears`] is tri-state, and that is the whole difference
        between recording a comparison and acting on one: a row with no score has
        nothing to stand on, so it does not pass. The record keeps the third
        state; the decision cannot have one.
        """
        return self.clears(score) is True

    def __str__(self) -> str:
        return f"{self.name} {self.value:g} ({self.head} {self.stamp[:12]}, ACTING)"


@dataclass(frozen=True)
class Restatement:
    """A bar's height, and the reading that put it there.

    A [`Bar`]'s `value` is a float and a float is unreadable on its own: 0.50 and
    0.685 are the same kind of thing only if you already know which head's scale
    each was measured on. So the height a bar is declared at is not a bare number
    in this repository — it is this, and it travels with the sha of the head it
    was read against, the method that read it, the population it was read over,
    and the day it was read.

    The sha is the load-bearing field. A bar is built with **it** as the stamp
    rather than with whatever is shipped right now, so a head flip makes every
    decision the bar takes refuse until somebody restates the number, instead of
    quietly comparing this head's probabilities against the last head's cutpoint.
    """

    #: The threshold, on the scale of the head named below and no other.
    value: float
    #: The sha256 of the artifact this height was measured against.
    head_sha256: str
    #: How it was measured, in enough detail to be re-run.
    method: str
    #: The population it was measured over. A method without one is half a
    #: recipe: "the fraction the incumbent's cut passed" names no fraction until
    #: it names what it passed a fraction *of*.
    reference_pool: str
    #: When, ISO. A restatement is an event; a bar with no date is a bar nobody
    #: can place against the retrains around it.
    date: str

    def __str__(self) -> str:
        return (
            f"{self.value:g} on {self.head_sha256[:12]}, restated {self.date} "
            f"over {self.reference_pool} — {self.method}"
        )


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


__all__ = [
    "Advisory",
    "Bar",
    "Cut",
    "HeadStampMismatch",
    "Restatement",
    "live_stamp",
]
