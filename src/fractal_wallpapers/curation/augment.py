"""The augmenting chain: the stage that raises the seat count the swap loop cannot.

[`curation.solve`]'s 1-swap loop conserves the seat count — one seat out, one
candidate in — so tier 1 of the objective is frozen at whatever the greedy seed
reached and every unfilled seat is the seed's. This is the smallest neighbourhood
that moves it.

## What a chain is, stated once

A **level-preserving** move is exactly a 1-swap: eject one seat `Y`, insert one
candidate the ejection admits. The **terminal** move is a free insert — a
candidate every rule admits once the ejections have happened. So

    a chain of depth k is (k - 1) level-preserving swaps then one insert,

and it is worth **+1 seat**. Depth 2 is eject one, insert two; depth 3 is one
more eject/insert pair. Acceptance needs no comparison: [`solve.Objective.order`]
puts seats first and strictly, so a +1 chain beats the incumbent whatever it does
to the three tiers beneath.

**And it does do something to them.** Measured on the pool of 2026-09-04: at
n=750 the gallery fills with the worst seated score and the shortfall both
untouched, but at n=1000 the worst seat goes 0.188159 to 0.093308 and the
shortfall 0 to 3, and at n=2000 it is 0.147448 to 0.055881 and 0 to 13. The
entering rows sit around a 0.31 median rank key against 0.50 for the seats they
displace — two weaker wallpapers for one better one. That is the strict tier
order working as ruled, and it is why the second swap loop runs after this stage:
it cannot lose a seat and it buys back what it can of tiers 2 to 4.

## What the chains actually do

They reclaim the colour the greedy overspends. `READ_solve_bound_and_profile_0904`
priced the greedy at 1.96 cells a seat against an integer program's 1.80; the
chains eject 3- and 4-cell seats and insert 1- and 2-cell rows. At n=750 every
one of the 34 ejections is a 3- or 4-cell seat and 67 of the 68 entering rows are
one-cell, for a net colour footprint of **-51**. What blocked the entering rows is
the cell allowance in 54 of 57 cases at that rung.

## One spelling per rule, and the ONE rule that is not in `rules.State`

Every insert and every eject is ruled by the shipped [`curation.rules.State`]: the
counted rules through `counted_refusal`, the whole ladder through `refuses`, which
puts the diversity rule last exactly as the seed and the swap loop do. The spiral
cap is read through `refuses_as_spiral` and never recomputed — its allowance is
`ceil(cap * (filled + 1))`, evaluated at the seat count the gallery *would* have,
which is already the right question for an insert and is why a chain applied one
insert at a time needs no special case.

**`State.refuses` does not know how big the gallery is.** It answers "may this
candidate sit beside the ones already seated", and `n` is not one of its rules:
the seed carries the seat count itself (`if gallery.full: break`) and the swap
loop never needs to, because a 1-swap conserves it. This stage is the first
caller that *raises* the count, so it is the first that has to carry the ceiling —
[`Pass.insert`] refuses at `filled >= n` under [`FULL`], which is deliberately not
one of [`rules.RULES`]: `n` is the leg's budget and never a fact about the
wallpaper, so a refusal here must not read as one. Measured before the guard was
written: at n=100, where this pool fills, the unguarded pass took 94 chains and
reported **194 seats of 100**, every one legal under every rule `rules.py` holds.

## Why the diversity rule is asked once per candidate and not once per trial

[`rules.Twins.within`] answers against the seated set as it stands. Ejecting seats
only ever *removes* rows from that answer, so if `near[c]` is the seated keys
inside tau before any ejection, then after ejecting `E`

    c is admitted by the diversity rule  <=>  near[c] is a subset of E.

That is exact, and it turns the one expensive rule into set arithmetic for the
whole search. The two staleness directions are not symmetric:

* an **ejection** shrinks the true `near`, so a stale answer is too large and
  would hide chains. Those are patched out of every set on acceptance, and the
  inversion is re-filed with them — without that re-filing the pass still fills
  n=1000 with 89 chains at the same worst and shortfall, but the sum lands
  553.385 against 553.453, because it cannot see the rows its own last chain
  released;
* an **insertion** grows it, so a stale answer is too small and merely proposes
  chains the live check then refuses. That costs work and never an answer, which
  is why insertions are not tracked.

**The asking is lazy, and the split is measured.** Only the [`Index.free_now`]
family has to be asked up front, because that is what [`Pass.invert`] is built
from — 1,645 rows of the 11,407 insertable at n=1000. The rest are asked the
first time a chain reaches one. Asking all of them up front was the prototype's
whole cost: a 122 s prologue in front of a 5.8 s search.

**Every `within` is asked with the state in its base position**, no trial ejection
in flight, because the subset rule above is stated against the base seating.
[`Pass.candidates_for`] is called before any eject for exactly that reason; inside
a depth-3 branch the state has moved, so a candidate nobody has asked about is
skipped rather than guessed at, which bounds that scan and is reported as a bound.
"""

from __future__ import annotations

import time

#: What [`Pass.insert`] calls the seat-count ceiling. **Not one of
#: [`rules.RULES`]** and spelled apart from them on purpose: `n` is this leg's
#: budget and never a fact about the wallpaper, so a refusal here must not land in
#: the rejection ledger dressed as one.
FULL = "the_gallery_is_full"

#: The deepest chain searched unasked. **Two**, and it is a measurement rather
#: than a preference: at n=2000 depth 3 bought 15 seats against depth 2's 294 and
#: cost a second full budget to do it, while at n=750 and n=1000 the gallery was
#: already full before depth 3 was asked anything. Three is reachable by flag.
DEFAULT_DEPTH = 2

#: The wall budget for the whole stage, unasked. **Five minutes.**
#:
#: Measured on the pool of 2026-09-04, this code, idle box: the stage takes
#: **48.1 s at n=750** and **72.1 s at n=1000**, and reaches exhaustion at both —
#: so at the two shipping rungs this is four times the headroom and never binds.
#: Nearly all of it is the diversity rule (45.7 s and 65.6 s); the chain search
#: itself is seconds.
#:
#: **n=2000 has not been measured on this path** and the budget is expected to
#: bind there: the prototype this came from searched 574 s at that rung without
#: exhausting depth 2, over a stage that was 2.2x slower than this one. That the
#: cap is *meant* to bind somewhere is the point — the stage is anytime, and a
#: rung whose neighbourhood cannot be exhausted should stop on a valid gallery
#: rather than run the leg for an hour. What it must never do is bind silently,
#: which is why `exhaustive` is on the depth block.
DEFAULT_SECONDS = 300.0

#: How many level-preserving swaps a depth-3 search tries per seat. A bound on
#: cost and reported as one: a depth-3 scan that finds nothing has found nothing
#: *under this fan-out*, which is a weaker statement than depth 2's exhaustion.
FAN_OUT = 8


class Refused(Exception):
    """A trial insert the shipped rules would not take. Carries the rule's name."""

    def __init__(self, why: str):
        super().__init__(why)
        self.why = why


class Index:
    """Which candidates one ejection would free. Counts only, no picture opened.

    Three populations, and the split is the two chain families:

    * `free_now` — every counted rule admits them as they stand, so
      `counted_requirements` is empty and `rules._intersect` hands back **every**
      seated key. While the gallery is under-filled a row here is refused by the
      diversity rule alone, so its chain ejects a near neighbour rather than a
      colour cell.
    * `freed_by[Y]` — a counted rule refuses them and `Y` is in every one of its
      requirement sets, so ejecting `Y` alone relieves the counted half.
    * `deep` — a counted rule refuses them and no single ejection relieves it:
      two disjoint blocking sets. Out of reach below depth 4, so they are counted
      and not searched.
    """

    def __init__(self, gallery, rows):
        state = gallery.state
        self.free_now: list = []
        self.freed_by: dict = {}
        self.deep: list = []
        for candidate in rows:
            if state.holds(candidate.key):
                continue
            if not state.counted_requirements(candidate):
                self.free_now.append(candidate)
                continue
            freed = state.counted_removals(candidate)
            if not freed:
                self.deep.append(candidate)
                continue
            for key in freed:
                self.freed_by.setdefault(key, []).append(candidate)


class Pass:
    """One augmenting pass over one finished gallery.

    Mutates the gallery it is handed and leaves every accepted chain applied. A
    trial that does not become a chain is unwound exactly, seat reason included.
    """

    def __init__(self, gallery, rows, log=print):
        self.gallery = gallery
        self.state = gallery.state
        self.rows = rows
        self.log = log
        self.twins = gallery.state.diversity
        self.chains: list = []
        self.counts: dict = {
            "proposed": 0,
            "passed_the_counted_rules": 0,
            "refused_by_a_counted_rule": 0,
            "refused_by_the_diversity_rule": 0,
            "refused_because_the_gallery_was_full": 0,
            "accepted": 0,
        }
        self.index: Index | None = None
        #: `{key: frozenset of seated keys inside tau}`, filled lazily. See the
        #: module docstring for why a stale entry is safe in one direction only.
        self.near: dict = {}
        self.unreadable: set = set()
        #: `{seat key: the rows only that seat refuses}`, and the rows nothing
        #: refuses at all. [`invert`] builds both.
        self.twin_waiting: dict = {}
        self.free_clear: list = []
        self.twin_seconds = 0.0
        self.twin_asked = 0

    # -- the diversity rule, asked once per candidate --------------------- #
    def ask(self, candidate) -> frozenset | None:
        """`near` for one candidate, made once and kept. `None` if unreadable.

        **Only ever called with the state in its base position.** See the module
        docstring: the subset rule this whole search runs on is stated against the
        seating as it stands, so an answer taken mid-chain would be an answer to a
        different question.
        """
        key = str(candidate.key)
        held = self.near.get(key)
        if held is not None or key in self.unreadable:
            return held
        if self.twins is None:
            self.near[key] = frozenset()
            return self.near[key]
        started = time.monotonic()
        answer = self.twins.within(key)
        self.twin_seconds += time.monotonic() - started
        self.twin_asked += 1
        if isinstance(answer, dict):
            self.unreadable.add(key)
            return None
        self.near[key] = frozenset(str(seat) for _gap, seat in answer)
        return self.near[key]

    def invert(self) -> None:
        """`twin_waiting[Y]` — the rows every counted rule admits that only `Y` refuses.

        A row in [`Index.free_now`] is refused by the diversity rule alone, so it
        is insertable after ejecting `Y` only when its whole `near` set is `{Y}` —
        which makes it eligible for **exactly one** seat in the gallery. Asking
        that seat by seat is a scan of the population per ejection; inverting it
        once makes the same answer a dictionary lookup.

        `free_clear` is the degenerate half: rows with an empty `near`, insertable
        after any ejection. While the gallery is under-filled it is empty by
        construction — a row no rule refuses is a row the seed would have seated —
        and it is carried because that stops being true once the gallery fills.
        """
        self.twin_waiting = {}
        self.free_clear = []
        for candidate in self.index.free_now:
            held = self.ask(candidate)
            if held is None:
                continue
            if not held:
                self.free_clear.append(candidate)
            elif len(held) == 1:
                self.twin_waiting.setdefault(next(iter(held)), []).append(candidate)

    def build(self) -> None:
        """The index, then the inversion. The only eager twin cost in the stage."""
        self.index = Index(self.gallery, self.rows)
        self.invert()

    # -- the arithmetic --------------------------------------------------- #
    def ready_for(self, ejected: frozenset, freed, lazily: bool) -> list:
        """The candidates whose twin answer is covered by `ejected`, best first.

        Sorted small-footprint first and then best by the leg's own key, which is
        the overspend this stage exists to reclaim: the way to buy a seat is to
        put cheap rows into the room an expensive one gives back.

        `lazily` says whether the state is in its base position and the diversity
        rule may therefore be asked. Inside a depth-3 branch it is not, and a
        candidate nobody has asked about is skipped rather than guessed at.
        """
        out = []
        for candidate in freed:
            held = self.ask(candidate) if lazily else self.near.get(str(candidate.key))
            if held is not None and held <= ejected:
                out.append(candidate)
        out.sort(key=lambda c: (len(set(c.cells)), -self.gallery.value(c), str(c.key)))
        return out

    def candidates_for(self, ejected: frozenset, lazily: bool = True) -> list:
        """Every row insertable once `ejected` is gone. Neither family is scanned whole."""
        freed = list(self.free_clear)
        for key in ejected:
            freed += self.twin_waiting.get(str(key), [])
            freed += self.index.freed_by.get(str(key), [])
        return self.ready_for(ejected, freed, lazily)

    def seats_by_preference(self) -> list:
        """`[(key, candidate)]` — biggest colour footprint first, weakest first.

        The seat worth ejecting is the one spending the most colour for the least
        rank. **It is a work list and it goes stale as it is walked**: an accepted
        chain ejects a seat, so a key further down may no longer be seated by the
        time the walk reaches it. Every caller re-checks with [`still_seated`];
        taking the list fresh per seat would be a sort of the whole gallery per
        seat, and skipping is the same answer.
        """
        held = [(str(key), candidate) for key, (candidate, _why) in self.state.seated.items()]
        held.sort(key=lambda pair: (-len(set(pair[1].cells)), self.gallery.value(pair[1]), pair[0]))
        return held

    # -- mutation, and its exact inverse ---------------------------------- #
    def still_seated(self, key: str) -> bool:
        """Whether this key is still a seat. See [`seats_by_preference`] on why."""
        return str(key) in self.state.seated

    def eject(self, key: str):
        """`(candidate, why)` — the shipped unseat, keeping what is needed to undo it."""
        candidate, why = self.state.seated[str(key)]
        self.gallery.unseat(str(key))
        return candidate, why

    def insert(self, candidate, why: str) -> None:
        """Seat one candidate, or raise [`Refused`]. The ceiling first, then the rules.

        The ceiling is asked here and nowhere else, and it is asked FIRST because
        it is the cheapest question and because a gallery at `n` has no legal
        insert whatever the rules say — see [`FULL`] and the module docstring.
        """
        if self.state.filled >= self.state.n:
            raise Refused(FULL)
        refused = self.state.refuses(candidate)
        if refused is not None:
            raise Refused(refused)
        self.gallery.seat(candidate, why)

    def undo(self, entered: list, ejected: list) -> None:
        """Unwind a trial: the inserts back out, then the ejects back in."""
        for candidate in reversed(entered):
            self.gallery.unseat(str(candidate.key))
        for candidate, why in reversed(ejected):
            self.gallery.seat(candidate, why)

    def _count(self, why: str) -> None:
        if why == FULL:
            self.counts["refused_because_the_gallery_was_full"] += 1
        elif self.twins is not None and why in (self.twins.NAME, "picture_unreadable"):
            self.counts["refused_by_the_diversity_rule"] += 1
        else:
            self.counts["refused_by_a_counted_rule"] += 1

    # -- accepting -------------------------------------------------------- #
    def accept(self, depth: int, ejected: list, entered: list, before) -> dict:
        """Record one applied chain, patch the twin answers, re-file the inversion."""
        gone = frozenset(str(candidate.key) for candidate, _why in ejected)
        for key, held in list(self.near.items()):
            if held & gone:
                self.near[key] = held - gone
        # Those sets just shrank, so a row whose twin blockers went from two to
        # one is newly reachable by a single ejection and belongs in
        # `twin_waiting` NOW rather than after the next sweep. See the module
        # docstring for what skipping this costs.
        self.invert()
        after = self.gallery.objective
        chain = {
            "depth": depth,
            "out": [self._row(candidate, why=why) for candidate, why in ejected],
            "in": [self._row(candidate) for candidate in entered],
            "objective_before": before.record(),
            "objective_after": after.record(),
            "opened_a_shortfall": after.shortfall > before.shortfall,
            "shortfall_delta": after.shortfall - before.shortfall,
        }
        self.chains.append(chain)
        self.counts["accepted"] += 1
        return chain

    def _row(self, candidate, why: str | None = None) -> dict:
        """One in- or out-row of a chain, for the record and the sheet.

        `blocked_by` is [`rules.State.counted_refusal`]'s own answer and never a
        second spelling of it; where every counted rule admits the row, what
        refused it was the diversity rule, and the name comes off the rule object.
        Taken at seat time, so an entering row says what stood in its way rather
        than what stands in it now — which after the chain is nothing.
        """
        blocked = self.state.counted_refusal(candidate)
        if blocked is None and why is None and self.twins is not None:
            blocked = self.twins.NAME if self.near.get(str(candidate.key)) else None
        return {
            "key": str(candidate.key),
            "location": str(candidate.location),
            "mode": str(candidate.mode),
            "group": str(candidate.group),
            "cells": sorted(set(candidate.cells)),
            "footprint": len(set(candidate.cells)),
            "rank_key": round(float(self.gallery.value(candidate)), 6),
            "p_ge4": round(float(candidate.score), 6),
            "spiral": bool(candidate.spiral),
            "picture": str(candidate.picture or ""),
            "seat_reason": why,
            "blocked_by": blocked,
        }

    # -- depth 2 ----------------------------------------------------------- #
    def depth_two(self, deadline: float | None = None) -> dict:
        """Eject one seat, insert two. To exhaustion, or to the budget.

        A sweep walks every seat in preference order; a sweep that accepts nothing
        is the exhaustion proof, and it is a real one because the index it ran
        against was rebuilt from the state that sweep started in. The clock is
        read between seats, so the stage stops at a chain boundary and never
        inside one.
        """
        started = time.monotonic()
        sweeps = 0
        exhausted = True
        stopped = "no chain of depth <= 2 found"
        pairs = 0
        while True:
            sweeps += 1
            self.build()
            took = 0
            for key, _seat in self.seats_by_preference():
                if deadline is not None and time.monotonic() > deadline:
                    stopped = "the budget ran out; the gallery it stopped on is valid"
                    exhausted = False
                    break
                found, tried = self.chain_at(key)
                pairs += tried
                if found is not None:
                    took += 1
            self.log(
                f"[augment] depth 2 sweep {sweeps}: {took} chain(s), "
                f"{self.gallery.objective.record()}"
            )
            if not took or not exhausted:
                break
        return {
            "depth": 2,
            "sweeps": sweeps,
            "pairs_tried": pairs,
            "exhaustive": exhausted,
            "stopped_because": stopped,
            "seconds": round(time.monotonic() - started, 2),
        }

    def chain_at(self, key: str) -> tuple:
        """`(the chain or None, pairs tried)` — one ejection's whole neighbourhood."""
        if self.state.filled >= self.state.n or not self.still_seated(key):
            return None, 0
        ready = self.candidates_for(frozenset({str(key)}))
        if len(ready) < 2:
            return None, 0
        before = self.gallery.objective
        ejected = [self.eject(key)]
        tried = 0
        for first in ready:
            try:
                self.insert(first, "augment")
            except Refused as refusal:
                self._count(refusal.why)
                continue
            for second in ready:
                if str(second.key) == str(first.key):
                    continue
                tried += 1
                self.counts["proposed"] += 1
                if self.state.counted_refusal(second) is not None:
                    self.counts["refused_by_a_counted_rule"] += 1
                    continue
                self.counts["passed_the_counted_rules"] += 1
                try:
                    self.insert(second, "augment")
                except Refused as refusal:
                    self._count(refusal.why)
                    continue
                return self.accept(2, ejected, [first, second], before), tried
            self.gallery.unseat(str(first.key))
        self.undo([], ejected)
        return None, tried

    # -- depth 3 ----------------------------------------------------------- #
    def depth_three(self, deadline: float | None = None, fan_out: int = FAN_OUT) -> dict:
        """One more eject/insert pair in front of the depth-2 scan.

        A level-preserving swap that **releases a colour unit** — the entering row
        spends strictly fewer cells than the seat it replaces — and then the
        depth-2 neighbourhood of the state it reaches. `fan_out` bounds how many
        such swaps are tried per seat, so a scan that finds nothing has found
        nothing under its bound and the readout says so.
        """
        started = time.monotonic()
        stopped = f"no chain of depth <= 3 found under a fan-out of {fan_out}"
        swaps = 0
        pairs = 0
        sweeps = 0
        while True:
            sweeps += 1
            self.build()
            took = 0
            out_of_time = False
            for key, seat in self.seats_by_preference():
                if self.state.filled >= self.state.n:
                    stopped = "the gallery filled"
                    break
                if deadline is not None and time.monotonic() > deadline:
                    stopped = "the budget ran out; the gallery it stopped on is valid"
                    out_of_time = True
                    break
                if not self.still_seated(key):
                    continue
                ready = self.candidates_for(frozenset({str(key)}))
                releasing = [row for row in ready if len(set(row.cells)) < len(set(seat.cells))][
                    :fan_out
                ]
                for first in releasing:
                    before = self.gallery.objective
                    ejected = [self.eject(key)]
                    try:
                        self.insert(first, "augment")
                    except Refused as refusal:
                        self._count(refusal.why)
                        self.undo([], ejected)
                        continue
                    swaps += 1
                    branch = Index(self.gallery, self.rows)
                    chain, tried = self._terminal(branch, ejected, [first], before)
                    pairs += tried
                    if chain is not None:
                        took += 1
                        break
                    self.undo([first], ejected)
            self.log(
                f"[augment] depth 3 sweep {sweeps}: {took} chain(s), "
                f"{self.gallery.objective.record()}"
            )
            if not took or out_of_time:
                break
        return {
            "depth": 3,
            "sweeps": sweeps,
            "level_preserving_swaps_tried": swaps,
            "fan_out": fan_out,
            "pairs_tried": pairs,
            "exhaustive": False,
            "exhaustive_is": "never claimed at this depth: the fan-out bounds the scan",
            "stopped_because": stopped,
            "seconds": round(time.monotonic() - started, 2),
        }

    def _terminal(self, branch: Index, ejected: list, entered: list, before) -> tuple:
        """`(a depth-3 chain from the state this branch reached or None, pairs tried)`."""
        gone_already = frozenset(str(candidate.key) for candidate, _why in ejected)
        tried = 0
        for key, _seat in self.seats_by_preference():
            if not self.still_seated(key):
                continue
            gone = frozenset({str(key)}) | gone_already
            freed = list(self.free_clear)
            for at in gone:
                freed += self.twin_waiting.get(str(at), [])
                freed += branch.freed_by.get(str(at), [])
            if len(freed) < 2:
                continue
            # The state has moved, so nothing new may be asked of the twin rule.
            ready = self.ready_for(gone, freed, lazily=False)
            if len(ready) < 2:
                continue
            second_out = self.eject(key)
            for first in ready:
                try:
                    self.insert(first, "augment")
                except Refused as refusal:
                    self._count(refusal.why)
                    continue
                for second in ready:
                    if str(second.key) == str(first.key):
                        continue
                    tried += 1
                    self.counts["proposed"] += 1
                    try:
                        self.insert(second, "augment")
                    except Refused as refusal:
                        self._count(refusal.why)
                        continue
                    return (
                        self.accept(3, ejected + [second_out], entered + [first, second], before),
                        tried,
                    )
                self.gallery.unseat(str(first.key))
            self.undo([], [second_out])
        return None, tried

    # -- why the rest cannot be bought ------------------------------------- #
    def blockage(self) -> dict:
        """What stands between the seats still empty and a chain. No picture opened.

        A depth-2 chain at `Y` needs **two** insertable rows once `Y` is gone, so
        the counts to read are how many seats offer none, one, and two or more.

        `two_or_more` above zero **beside an exhausted search** is the interesting
        answer: the pairs exist and conflict with each other, both wanting the same
        unit of colour the ejection released, which is saturation on cells rather
        than a shortage of waiting rows. Beside a search that ran out of budget it
        says nothing at all, and the `exhaustive` flag on the depth block is what
        tells the two apart.

        **It asks the diversity rule nothing.** A read-only diagnostic that opened
        pictures would be a diagnostic that costs more than the thing it describes,
        and it did: asking lazily here was **62 s of a 110 s stage at n=750, against
        a search of 48 s**. So it reads the answers the search already has and
        counts the rows it cannot speak for, which is a number worth reporting
        anyway — a row nothing ever asked about is a row no chain reached.
        """
        import collections

        started = time.monotonic()
        self.build()
        offering: collections.Counter = collections.Counter()
        reachable = 0
        cut = 0
        unasked = 0
        for key, _seat in self.seats_by_preference():
            here = (
                len(self.free_clear)
                + len(self.twin_waiting.get(str(key), ()))
                + len(self.index.freed_by.get(str(key), ()))
            )
            unasked += sum(
                1
                for row in self.index.freed_by.get(str(key), ())
                if str(row.key) not in self.near and str(row.key) not in self.unreadable
            )
            ready = self.candidates_for(frozenset({str(key)}), lazily=False)
            offering[min(len(ready), 2)] += 1
            reachable += here
            cut += here - len(ready)
        return {
            "unfilled": self.state.n - self.state.filled,
            "seats_offering_no_insertable_row": offering[0],
            "seats_offering_exactly_one": offering[1],
            "seats_offering_two_or_more": offering[2],
            "two_or_more_is": "a seat whose ejection leaves two rows every rule would admit "
            "SEPARATELY. Beside an EXHAUSTED search that means they conflict with each "
            "other — saturation on cells, not a shortage of waiting rows. Beside a search "
            "that ran out of budget it means nothing: read the depth block's `exhaustive`",
            # The next three are (seat, row) INCIDENCES summed over every seat, not
            # row counts: one row reachable from forty seats is forty here. Named
            # for what they are, because "rows" on a number thirty times the pool
            # is a statistic that reads as a fact about the pool and is not one.
            "reachable_incidences": reachable,
            "incidences_the_diversity_rule_cut": cut,
            "incidences_never_asked_about": unasked,
            "incidences_are": "(seat, row) pairs summed over the seats, never distinct rows. "
            "`never_asked` is counted inside `cut` because this block opens no picture of "
            "its own: a row there is one no chain ever reached, which is a fact about the "
            "search rather than about the row",
            "rows_out_of_reach_of_one_ejection": len(self.index.deep),
            "seconds": round(time.monotonic() - started, 2),
        }


def run(
    gallery,
    rows,
    depth: int = DEFAULT_DEPTH,
    seconds: float | None = DEFAULT_SECONDS,
    log=print,
) -> dict:
    """Augment one seeded, swapped gallery. The record block is the return value.

    The gallery is mutated in place and is valid at every moment: a chain is
    applied only once every one of its inserts has been admitted, so the stage can
    stop on its budget with nothing to undo.
    """
    started = time.monotonic()
    before = gallery.objective
    walk = Pass(gallery, rows, log=log)
    deadline = None if seconds is None else time.monotonic() + float(seconds)
    phases = {"depth_2": walk.depth_two(deadline=deadline)}
    if int(depth) >= 3:
        phases["depth_3"] = walk.depth_three(deadline=deadline)
    blocked = walk.blockage()
    after = gallery.objective
    seconds_taken = time.monotonic() - started
    log(
        f"[augment] {len(walk.chains)} chain(s), {before.seats} -> {after.seats} seat(s) "
        f"in {seconds_taken:.1f}s"
    )
    return {
        "of": "augmenting chains: (k-1) level-preserving 1-swaps then one free insert, "
        "worth +1 seat each. The stage that raises the seat count, which a 1-swap cannot",
        "accepted_by": "the objective as ruled — a +1 chain wins tier 1 strictly, so it is "
        "taken whatever it does to the shortfall, the worst seat and the sum. What it did "
        "to them is on `objective` and on every chain, and the swap loop after this stage "
        "is what buys back what it can",
        "ceiling": f"the seat count is carried HERE and not by rules.State, under "
        f"{FULL!r}: `n` is this leg's budget and never a fact about the wallpaper",
        "depth": int(depth),
        "budget_seconds": None if seconds is None else float(seconds),
        "phases": phases,
        "counts": walk.counts,
        "chains": walk.chains,
        "blockage": blocked,
        "seats_before": before.seats,
        "seats_after": after.seats,
        "gained": after.seats - before.seats,
        "objective_before": before.record(),
        "objective_after": after.record(),
        "chains_opening_a_shortfall": sum(1 for c in walk.chains if c["opened_a_shortfall"]),
        "diversity_rule": {
            "candidates_asked": walk.twin_asked,
            "seconds": round(walk.twin_seconds, 2),
            "asked_lazily": "only the rows every counted rule already admits are asked up "
            "front, because the inversion is built from them; the rest are asked the first "
            "time a chain reaches one",
            "unreadable": len(walk.unreadable),
        },
        "seconds": round(seconds_taken, 2),
    }


__all__ = ["DEFAULT_DEPTH", "DEFAULT_SECONDS", "FAN_OUT", "FULL", "Index", "Pass", "run"]
