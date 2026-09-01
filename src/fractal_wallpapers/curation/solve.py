"""Choose the gallery: a stratified view, a greedy seed, and swaps to exhaustion.

One leg, one pool, one command. This project used to have two — a sequential
`curate seat` that walked a ranked list, and an exact `curate solve` that stated
the same intentions as a mixed-integer program and handed them to HiGHS. They
chose from **different pools** under two copies of most rules and two different
rules for one of them, which is a divergence nobody finds by reading either file.
Both are gone and this is what replaced them.

## Why the exact solve is retired

`PROBE_ilp_n1000` measured it against the thirty-minute bar production wants at
n=1000: killed at a hard 1800 s having reached stage 3 of round 1, with no
incumbent, no gap and no record. The bar was not missed narrowly — one
cutting-plane round did not finish, and the round count grows with `n`.

The headline was not branch-and-bound. **46% of the budget went to the greedy
seed** before the solver ran, and the seed still failed: 534 of 1000 seats. It
measured every pair of `[candidate, *seated]` once per candidate it considered,
so it was O(seats^2) per candidate and cubic overall. The model itself was free —
0.4 to 0.6 s to build, and *literally the same matrix* at n=150 and n=1000, only
the bounds moving — so shrinking the program buys nothing.

So the shipping method is **anytime**: it holds a valid gallery from its first
seat and improves it until it runs out of improvements or out of clock. Nothing
here claims optimality and nothing here needs a solver.

## The four steps

1. A **view** ([`curation.view`]): the pool above its per-mode bars, one row per
   place plus each place's best row per stratum, then per `(kind, mode, cell)`
   either the whole stratum or a band-blind slice of it. The pool is never
   mutated and the strata, their sizes and the draw seed are on the record.
2. The **rules** ([`curation.rules`]): one set-level predicate each, over
   incremental state. `admits` for the seed, `removals` for the swap loop, and
   never a sequential copy beside a set copy.
3. A **greedy seed** in the seating order this project already had — the mandated
   constraints from their own subpools scarcest first, then the ranked walk.
4. **1-swap improvement**: one seat out, one candidate in, accepted only on
   strict lexicographic improvement, until a full pass finds none.

## The objective, and it is strict

Lexicographic, in this order, and a swap is taken only if it improves one tier
without making an earlier one worse:

1. **seats filled** — every one above its own mode's bar, because that is what
   the pool is;
2. the **shortfall** against every demand the pass was given — the mode floors
   and any colour target — minimized. Fewer short seats is better and nothing is
   ever padded;
3. the **worst seated score**, maximized;
4. the **sum**.

The rank quantity is [`RANK_KEY`], the fitted five-column form the ranking
retention already uses. `p_ge4` alone is not it and is still reachable by name.

**A filled floor outranks the worst seat, and that is the ruling.** Matt's, and
it is what "grab where possible" means: a mode this pool *can* represent is
represented, and the price is paid out of the weakest seat rather than out of the
roster. The retired program had these two the other way round — its stage 2
maximized the floor and the mode penalty lived in stage 3 beneath it — and that
order needed a guard, because the worst seat is by construction a scarce mode's,
trading it for a strong `smooth` lifts the floor value, and a tier beneath it
cannot buy the representation back. Under this order there is nothing to guard: a
met demand is kept by the order itself, since giving it back is a tier-2 loss no
tier below it can pay for. The guard that used to reconcile them is gone, and so
is the reading that made it necessary. `swaps.by_tier` is where to read what the
loop actually traded, and a swap that fills a short floor at the cost of the worst
seat is now the ordinary case rather than the refused one.

## A shortfall is not infeasibility

Every unseated candidate is recorded with the rule that refused it, aggregated by
cell, family, mode and partition, and that aggregate is the product — it is the
"what do we make next" answer. But a shortfall here means *this leg did not find
it* and never *the pool does not hold it*. The only infeasibility claims this
project makes are [`curation.headroom`]'s necessary conditions.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import (
    candidate_ledger,
    ceiling,
    distinct,
    floors,
    mode_policy,
    rules,
    signatures,
    view,
)
from fractal_wallpapers.paths import rehome, tracked_name, under

#: The schema every record this module writes carries.
#:
#: **2**: the leg became the stratified view, the greedy seed and the 1-swap
#: loop, and the exact solve was retired. A schema 1 record is an ILP's — it
#: carries `relaxation`, `rounds` and `cuts`, and it was taken over a pool the
#: per-mode bars had never been applied to. The two are not comparable galleries
#: and no reader should try.
#:
#: The themed leg did **not** bump it. Its whole footprint on the record is the
#: `theme` block, which is `None` on every unthemed pass, and the rule that
#: actually ran was always named in `rules.diversity` — so two unthemed schema-2
#: galleries mean the same thing before and after it, which is what a schema
#: number is for. What is not comparable is a themed record against an unthemed
#: one, and that is a different diversity rule rather than a different schema.
SCHEMA = 2

#: The subtree this leg's record and its sheet land in.
UNIT = "solve"

#: The bar the record counts seats against, on **raw** `P(>=4)`.
#:
#: [`floors.RELEASE_ADVISORY`], which is the natural rank cutpoint of a CORN
#: probability and answers "would this head call the picture a fourth-class
#: wallpaper". It is deliberately NOT a measured crossover: no isotonic fit of a
#: human `q4` verdict against this head's fourth cutpoint exists, and the two
#: heights this project has fitted ([`floors.MEASURED_RELEASE_FLOORS`]) are both
#: `P(>=3)` and neither transfers to a different cutpoint.
#:
#: It is a **statistic on the record and not the pool rule**. What the pool is
#: is [`headroom.bars`] — the same height on `P(>=4)` for a mode with enough
#: places above it, and `P(>=3)` for one without — so a fallback mode's seats
#: are legitimately below this and the count says so rather than refusing them.
Q4_BAR = floors.RELEASE_ADVISORY

#: What the bar is a bar **on**. Spelled out because one head emits three
#: cutpoints and a count says nothing without naming which one it counted.
Q4_BASIS = (
    "raw P(>=4) from the render judge, against the natural rank cutpoint of a CORN "
    "probability. NOT a measured crossover: both release heights this project has fitted "
    "are P(>=3) and neither transfers to the fourth cutpoint. A human-derived q4 crossover "
    "replaces this, and a count taken across the change names its own bar"
)

#: How many seats of a gallery one production mode's floor is worth under the
#: **flat** rule: a hundredth, so the floor is `floor(n / 100)` — 0 at n=20, 1 at
#: 150, 10 at 1000. It is not the default any more; [`mode_policy.seat_floors`]
#: is, and `--flat-floor` is the way back to this one.
SEATS_PER_MODE_FLOOR = 100

#: The render judge's fourth cutpoint alone, which is what every gallery this
#: project shipped before 2026-08-28 was ordered by. Still reachable by name.
JUDGE_KEY = "p_ge4"

#: [`curation.rank_key`]'s fitted five-column form — the location head, both
#: judge cutpoints, the calibration stratum and the flatness column. **This is
#: the rank quantity the objective is stated in**: `p_ge4` alone is not it.
RANK_KEY = "rank-key"

#: The keys a caller may name.
KEYS = (RANK_KEY, JUDGE_KEY)

#: **The sort key this leg walks unasked**, since 2026-08-28: the fitted one.
#:
#: Matt's, off the contact sheets — the four-arm before/after at `n = 150` put
#: the fitted order beside the judge alone on one pool and he accepted it by eye.
#: It is an acceptance and not a measurement, and the record says which key ran
#: either way.
#:
#: It moves the **order and the objective** and nothing else. Every bar, the
#: clearing rule and the neutral pre-selection still read the judge's own columns.
DEFAULT_KEY = RANK_KEY

#: **The palette-group cap rule this leg runs under unasked**, since 2026-08-28:
#: the proportional one, `max(1, floor(GROUP_CAP_RATE * n))`. The ckpt-88 ruling.
#: [`ceiling.IDENTITY`] — one seat a map — is still what a caller gets by naming
#: it. Below `1 / ceiling.GROUP_CAP_RATE` seats the two produce the same cap.
DEFAULT_GROUP_CAP = ceiling.PROPORTIONAL

#: How many of the refused the contact sheet shows beside the seated, per rule.
#: Enough that a rule's refusals are a sample rather than an anecdote, few enough
#: that the page is one page.
SHOWN = 6

#: How many of the seats the bottom-quartile attribution block is cut at. A
#: quarter, of the seats and never of the pool: the question it answers is "which
#: legs are placing the weakest wallpapers this gallery ships".
BOTTOM_QUARTILE = 0.25

#: How many seats the swap loop tries removing for one candidate. **Eight.**
#:
#: A candidate nothing is in the way of could in principle replace any of `n`
#: seats, and evaluating all of them would make one pass `n` times the size of
#: the view. The eight it does try are the eight **weakest by the rank key**
#: inside the set of seats that could leave, which is where every tier's
#: improvement lives: the sum improves by removing the weakest, and so does the
#: worst seated score.
#:
#: This is the one heuristic in the loop and it is about *which* removals are
#: offered, never about which are accepted — acceptance is strict lexicographic
#: improvement and nothing weakens it. A pass that finds no swap has found none
#: in this neighbourhood, which is what the record says.
SWAP_DROPS = 8

#: How many improvement passes before the loop stops and says so. A backstop and
#: not an operating parameter: the loop's own stopping rule is a pass that takes
#: no swap, and every pass takes at least one swap or is the last.
SWAP_PASSES = 200

#: How long one release row gets before the worker kills it. **A backstop and
#: never a budget.** The release leg has no clock: every row it plans is rendered
#: to completion. What this bounds is the row that has stopped making progress at
#: all — a quarter of an hour against a leg whose median row at 1280x720 ss2 is
#: single-digit seconds and whose worst recorded row was 799 s.
ROW_BACKSTOP = 900.0

#: What a candidate that broke no rule and simply lost is recorded as. It is a
#: far weaker statement than any of [`rules.RULES`] and is kept apart for that
#: reason: a mine aimed at this population would be aimed at nothing.
UNSEATED = "the_leg_had_no_seat_left"

#: What a candidate below its own mode's bar is recorded as. Not a refusal by any
#: selection rule — it never entered the population the leg chooses from.
BELOW_BAR = "below_its_mode_bar"

#: What a candidate whose **place** the neutral pre-selection refused is recorded
#: as. Kept apart from [`rules.RULES`] for the same reason [`BELOW_BAR`] is: it
#: is pool construction and not a seat this leg declined to give.
SAME_PLACE = "another_place_is_the_same_place"

#: What a candidate outside a THEMED pass's cell is recorded as. Pool
#: construction like [`BELOW_BAR`] and never a rule: the row was not refused a
#: seat, it was never eligible for one, and a themed leg's whole reading is which
#: of its own eligible rows it could not seat.
OFF_THEME = "not_dominant_in_the_theme"

#: What a candidate the view never reached is recorded as. The view is a
#: deliberate restriction and a row outside it was refused by no rule at all, so
#: reporting it as one would put the leg's own budget on the rejection ledger
#: dressed as a fact about the wallpaper.
OUTSIDE_THE_VIEW = "the_view_did_not_reach_it"

#: The legs a seat can be placed by, spelled as the leg itself spells them.
LEGS = {
    "mandate": "the scarcity leg: each mandated constraint from its own subpool, scarcest "
    "first, taking that mandate's best candidate nothing refuses",
    "general_pool": "the ranked walk down whatever the scarcity leg left, in the leg's own "
    "sort key, with every counted ceiling applied as it goes",
    "swap": "the 1-swap improvement loop: this seat replaced another one on a strict "
    "lexicographic improvement",
}


class SolveRefused(RuntimeError):
    """The gallery cannot be chosen."""


# --------------------------------------------------------------------------- #
# The pool.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Candidate:
    """One ledger row, thinned to what a rule or the objective reads.

    Everything here is off the row. This leg renders nothing and opens no picture
    until the diversity rule asks one candidate for its pixel cloud.
    """

    key: str
    location: str
    partition: str
    mode: str
    group: str
    kind: str
    cells: tuple
    families: tuple
    score: float
    p_ge3: float
    picture: str

    @property
    def above_bar(self) -> bool:
        return self.score >= Q4_BAR


def pool(rows=None, scores=None, artifact=None, log=print) -> tuple[list[Candidate], dict]:
    """`(candidates, what was refused)` — everything this leg may seat.

    Five exclusions, each a fact about the candidate rather than a quality bar. A
    row in a mode [`curation.mode_policy`] weights **0** is refused: the standing
    is that this project has stopped buying that mode, and a gallery is the last
    place it would be spent. A row a **person rejected** is refused: the ledger
    keeps it and carries the rejection precisely so that this honours it. A row at
    a regime other than the one the pool was made at is refused, because a score
    read at one geometry does not transfer to another. A row with **no picture on
    disk** is refused — its recipe is complete and it could be drawn again, but
    the diversity rule is read off pixels, and a candidate it cannot evaluate is
    one that would be seated untested. A row with no score is refused because the
    objective *is* the score.

    **Naming a picture and having one are two questions, and this asks both.**
    Until 2026-08-28 it asked only the first, and the gap is not small: `curate
    retention` drops the picture of everything outside the top five per (location,
    mode), which at this store is 30,040 of 128,368 rows (23.4%). All of them were
    admitted, and the diversity rule — the one rule that opens a picture — could
    not read them and so *admitted* them too. Rows it could not evaluate were
    exactly the rows it stopped applying to.

    The two are counted apart, `no_picture` against `picture_absent`, because they
    are different facts about a row: one was never drawn, the other was drawn and
    swept. Only the second is expected to grow.
    """
    stored = candidate_ledger.stream() if rows is None else rows
    read = candidate_ledger.read_scores() if scores is None else list(scores)
    # On the LIVE judge only, for [`candidate_ledger.scores_by_recipe`]'s reason:
    # the sidecar is keyed on the artifact and a flattened join would put two
    # judges' scales into one objective.
    by_key = candidate_ledger.scores_by_recipe(read, artifact=artifact)
    refused = {
        "niche_mode": 0,
        "rejected": 0,
        "off_regime": 0,
        "no_picture": 0,
        "picture_absent": 0,
        "no_score": 0,
    }
    seen = 0
    projected: list[dict] = []
    for row in stored:
        seen += 1
        recipe = row.get("recipe") or {}
        # The mode this candidate COUNTS as — see [`mode_policy.routed_mode`]. It
        # is taken before the roster is asked, because a row whose picture is the
        # smooth field spent by rank is a smooth picture on both questions.
        mode = mode_policy.routed_mode_of(row)
        if not mode_policy.is_accepted(mode):
            refused["niche_mode"] += 1
            continue
        if row.get("rejected"):
            refused["rejected"] += 1
            continue
        if not row.get("at_candidate_regime"):
            refused["off_regime"] += 1
            continue
        if not row.get("picture"):
            refused["no_picture"] += 1
            continue
        colour = row.get("colour") or {}
        projected.append(
            {
                "key": str(row["key"]),
                "picture": str(row["picture"]),
                "location": str((row.get("location") or {}).get("key")),
                "partition": str(row.get("partition")),
                "mode": mode,
                "group": str(recipe.get("palette_group")),
                "cells": tuple(colour.get("cells") or ()),
                "families": tuple(colour.get("families") or ()),
            }
        )
    if not seen:
        raise SolveRefused(
            "the candidate ledger is empty, so there is nothing to choose over. Run "
            "`fractal-wallpapers curate candidate-ledger backfill` first."
        )
    present = candidate_ledger.present_pictures(projected)
    out: list[Candidate] = []
    for held in projected:
        if held["key"] not in present:
            refused["picture_absent"] += 1
            continue
        reading = by_key.get(held["key"])
        if reading is None or reading.get("p_ge4") is None:
            refused["no_score"] += 1
            continue
        out.append(
            Candidate(
                key=held["key"],
                location=held["location"],
                partition=held["partition"],
                mode=held["mode"],
                group=held["group"],
                kind=str(reading.get("head")),
                cells=held["cells"],
                families=held["families"],
                score=float(reading["p_ge4"]),
                p_ge3=float(reading.get("p_ge3") or 0.0),
                picture=held["picture"],
            )
        )
    out.sort(key=lambda candidate: (-candidate.score, candidate.key))
    log(f"[solve] {len(out):,} candidates; refused {refused}")
    return out, refused


def in_theme(candidates, cell: str) -> list:
    """Every candidate **dominant** in one colour cell. A themed pass's whole pool.

    Membership is the row's own dominance block and never the carrier table: the
    table says which palette maps tend to produce the cell, which is a prior about
    supply, and a gate built on a prior admits a picture nobody measured and
    refuses one somebody did. [`palettes.dominance`] is what wrote `colour.cells`,
    a row may carry several dominant cells or none, and this asks the one question
    it can answer.
    """
    wanted = str(cell)
    return [candidate for candidate in candidates if wanted in candidate.cells]


def picture_of(candidate: Candidate) -> Path:
    """Where one candidate's 640x360 render is on this machine."""
    return Path(rehome(candidate.picture))


def strongest_locations(candidates: list[Candidate], keep: int | None) -> list[str]:
    """The `keep` strongest locations by their best candidate. `None` keeps all.

    Hard optimization against a learned score selects that score's upper tail,
    which is where a judge's false positives live; restricting what the leg may
    reach is the one lever on that which costs nothing to try. It acts on
    **locations** and not on candidates because a gallery is a set of places.
    """
    per: dict = {}
    for candidate in candidates:
        if candidate.score > per.get(candidate.location, -1.0):
            per[candidate.location] = candidate.score
    ranked = sorted(per.items(), key=lambda item: (-item[1], item[0]))
    if keep is None or int(keep) >= len(ranked):
        return [name for name, _ in ranked]
    return [name for name, _ in ranked[: max(1, int(keep))]]


def within(candidates: list[Candidate], locations) -> list[Candidate]:
    """`candidates` restricted to a set of locations, order preserved."""
    keep = set(locations)
    return [candidate for candidate in candidates if candidate.location in keep]


# --------------------------------------------------------------------------- #
# The rank key.
# --------------------------------------------------------------------------- #
def rule_for(targets: dict | None = None) -> ceiling.Rule:
    """The ceiling's constants and targets.

    [`ceiling.Rule`] holds the allowance arithmetic and the target-to-family
    summation, and both are wanted here — a target raises the allowance of the
    cell it names and of that cell's family, and a second derivation of that would
    be a second answer.
    """
    return ceiling.Rule(targets=dict(targets or {}))


def ranking_for(candidates, key: str = DEFAULT_KEY, log=print) -> tuple[dict | None, dict | None]:
    """`(the order this leg walks, what the key could read)` for one pool.

    `(None, None)` on [`JUDGE_KEY`], where the order is the candidate's own
    `P(>=4)` and there is nothing to resolve. On [`RANK_KEY`] it is
    [`rank_key.order_for`]'s mapping and its coverage record, and resolving it
    reads two stores — the flatness sidecar and the location readings — so this is
    the one place a pass pays for its key and it is paid once per pool.

    Named apart from [`solve`] because [`solve`] is arithmetic over candidates it
    is handed and this is I/O. A caller with an order already in hand passes it
    straight to `solve(order=...)` and never reaches here.
    """
    named = str(key)
    if named == JUDGE_KEY:
        return None, None
    if named != RANK_KEY:
        raise SolveRefused(f"the sort key is one of {KEYS}, not {key!r}")
    from fractal_wallpapers.curation import rank_key

    return rank_key.order_for(candidates, log=log)


def value_of(candidate, order: dict | None) -> float:
    """One candidate's value under the leg's own key. **The objective's quantity.**

    `order` is [`RANK_KEY`]'s mapping; `None` is [`JUDGE_KEY`], where the value is
    the candidate's own `P(>=4)`. A candidate the mapping cannot read is worth
    **zero** here and sorts last in [`ranking`] — it has not earned a place ahead
    of the rows the key could read, and a seating that reaches one is a seating
    the record counts under `order.unranked`.
    """
    if order is None:
        return float(candidate.score)
    held = order.get(candidate.key)
    return 0.0 if held is None else float(held)


def ranking(order: dict | None):
    """The sort key one pass walks its view in. Strongest first, ties by key.

    `None` is the incumbent: the render judge's `P(>=4)` off the candidate. A
    mapping is [`curation.rank_key`]'s, and a candidate it has no value for sorts
    **last** rather than at zero — zero is a real rank value under a fitted key,
    and a row nobody could read is not a row that scored badly.
    """
    if order is None:
        return lambda candidate: (0, -candidate.score, candidate.key)
    return lambda candidate: (
        (0, -float(order[candidate.key]), candidate.key)
        if candidate.key in order
        else (1, 0.0, candidate.key)
    )


# --------------------------------------------------------------------------- #
# The floors, and the demands they are one of.
# --------------------------------------------------------------------------- #
def mode_floor(n: int) -> int:
    """The **flat** floor: `floor(n / SEATS_PER_MODE_FLOOR)` seats for every mode.

    Not the default. [`mode_policy.seat_floors`] is, and this is what
    `--flat-floor` asks for — the rule every gallery seated before 2026-08-31 was
    seated under, kept reachable so a before/after can be taken.
    """
    return max(0, int(n) // SEATS_PER_MODE_FLOOR)


def floors_for(floor, modes) -> dict:
    """`{mode: its floor}` over `modes`, from either a number or a mapping.

    A number is the same floor for every accepted mode, which is the shape
    [`mode_floor`] returns. A mapping is per mode — what
    [`mode_policy.seat_floors`] builds — and a mode it does not name asks for
    nothing rather than inheriting a default, because a floor rule that silently
    floors a mode it never mentioned is not a rule anybody can read off its table.
    """
    if isinstance(floor, dict):
        return {name: max(0, int(floor.get(name, 0))) for name in modes}
    return dict.fromkeys(modes, max(0, int(floor)))


def floor_rule(n: int, floor: int | None, held: dict, natural: dict, modes: list) -> str:
    """One sentence naming the rule the floors in this record came from.

    Three answers and they are not interchangeable: the **default**, the **flat**
    floor the default replaced — which is what `--flat-floor` asks for and what
    every gallery before this flip was seated under — and a floor some caller made
    up. A record that said `floor(n / 100)` for all three, which this said while
    the flat floor was the default, is a record that cannot tell a measurement
    apart from its own baseline.

    Public because [`curation.headroom`] writes the same sentence into its census
    block, and the census naming the floors one way while the gallery leg names
    them another is the confusion this sentence exists to end.
    """
    if dict(held) == floors_for(natural, modes):
        return (
            "the per-mode floor rule, curation.mode_policy.seat_floors(n): half each "
            "accepted strange mode's share of the strange seat budget, summing to half "
            "of it. THE DEFAULT — a pass that named no floor was seated under this"
        )
    if floor is None:
        return "set per mode by the caller"
    if floor == mode_floor(n):
        return (
            f"the FLAT floor, floor(n / {SEATS_PER_MODE_FLOOR}) = {floor} for every "
            "accepted mode. It was the default until the per-mode rule replaced it, and "
            "it is what `--flat-floor` asks for"
        )
    return f"an artificial flat {floor} for every accepted mode"


def target_rule() -> str:
    """One sentence naming what a `--target t` asks of this leg.

    **A share of the realized seat count**, always. The retired program had two
    spellings — a hard `ceil(t * n)` while cardinality was `== n`, and a share of
    what got filled once it was `<= n` — and the hard one was wrong in exactly the
    case a target is set for: it demands a share of seats nobody is promising to
    fill, so an under-filled answer reported nothing at all. This leg never
    promises `n`, so there is one spelling and it is the second one.
    """
    return (
        "t * the REALIZED seat count: at least ceil(t * seats filled) of the seats "
        "dominant in the named cell. A share of the gallery that gets filled, because "
        "this leg does not promise n of them. It is a demand and it is soft: a target "
        "the pool cannot meet is a recorded shortfall and never a padded seat"
    )


@dataclass(frozen=True)
class Demand:
    """One thing the pass was told to seat some of, and how to count it.

    Two kinds today and they are one shape: a **mode floor** wants a fixed number
    of seats in one mode, and a **colour target** wants a share of the realized
    seats dominant in one cell. Both are soft, both are counted in tier 3 of the
    objective, and both are seated from their own subpool by the scarcity leg —
    so neither is a special case anywhere below this line.
    """

    name: str
    axis: str
    of: str
    #: A fixed count, for a mode floor. `None` for a share.
    seats: int | None = None
    #: A share of the realized seat count, for a colour target. `None` for a count.
    share: float | None = None

    def wanted(self, filled: int) -> int:
        """How many seats this demand asks for, given how many got filled."""
        if self.seats is not None:
            return int(self.seats)
        return int(math.ceil(float(self.share) * max(0, int(filled))))

    def taken(self, state) -> set:
        """Which seated keys count towards this demand. The axis store, by name."""
        store = state.modes if self.axis == "mode" else state.cells
        return set(store.get(self.of, ()))

    def held(self, state) -> int:
        return len(self.taken(state))

    def counts(self, candidate) -> bool:
        """Whether seating this candidate would count towards the demand."""
        return candidate.mode == self.of if self.axis == "mode" else self.of in candidate.cells


def demands_for(held: dict, targets: dict) -> list:
    """Every demand one pass carries, mode floors then colour targets.

    A floor of zero is not a demand: it cannot go short, and carrying it would put
    a row on the shortfall block that no gallery can fail — which is how a floor
    rule reads as working when it is switched off.
    """
    out = [
        Demand(name=f"mode_floor:{mode}", axis="mode", of=mode, seats=int(seats))
        for mode, seats in sorted(held.items())
        if int(seats) > 0
    ]
    out += [
        Demand(name=f"target:{cell}", axis="cell", of=cell, share=float(share))
        for cell, share in sorted((targets or {}).items())
        if float(share) > 0
    ]
    return out


# --------------------------------------------------------------------------- #
# The objective.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Objective:
    """The four tiers, and the only comparison anything in this module makes.

    Held as a value rather than as a number so that "better" is one function with
    one definition. `worst` is `None` on an empty gallery, which compares below
    every real value — an empty gallery is worse than any gallery.
    """

    seats: int
    worst: float | None
    shortfall: int
    total: float

    @property
    def order(self) -> tuple:
        """The tuple `>` compares. Shortfall negated so that every tier maximizes.

        The shortfall sits **above** the worst seated score, which is the ruling
        and the whole reason nothing here needs a guard: a swap that takes a met
        demand back below what it asks for loses on this tier, and no gain in the
        two beneath it can pay for that.
        """
        return (
            self.seats,
            -int(self.shortfall),
            -1.0 if self.worst is None else float(self.worst),
            float(self.total),
        )

    def beats(self, other: Objective) -> bool:
        """**Strict** lexicographic improvement. No tolerance and no tie accepted."""
        return self.order > other.order

    def tier_over(self, other: Objective) -> str | None:
        """Which tier this one first improves on. `None` where it does not beat it."""
        names = ("seats", "shortfall", "worst", "sum")
        for name, mine, theirs in zip(names, self.order, other.order, strict=True):
            if mine != theirs:
                return name if mine > theirs else None
        return None

    def record(self) -> dict:
        return {
            "seats": self.seats,
            "worst": None if self.worst is None else round(float(self.worst), 6),
            "shortfall": int(self.shortfall),
            "sum": round(float(self.total), 6),
        }


#: The objective, spelled once, for every record that carries one.
OBJECTIVE = (
    "lexicographic and strict, in this order: (1) seats filled, every one above its own "
    "mode's bar; (2) the shortfall against every demand — the mode floors and any colour "
    "target — minimized, and nothing padded; (3) the worst seated score, maximized; "
    "(4) the sum. The rank quantity is the fitted rank key and not p_ge4 alone. A filled "
    "floor outranks the worst seat by ruling: a demand this pool can meet is met, and the "
    "price comes out of the weakest seat rather than out of the roster. Nothing guards a "
    "met demand because the order itself keeps it"
)


class Gallery:
    """The seated set with its objective kept alongside, and the swap arithmetic.

    [`curation.rules.State`] answers what may be seated; this answers what seating
    it would be **worth**. They are apart because the rules are the same for every
    caller and the objective is this leg's, and because a themed leg that swaps the
    diversity rule out should not have to know how a swap is scored.

    The seated ranks are held sorted, so the worst seat and the second-worst — the
    two numbers tier 3 needs for every candidate swap — are the first two entries
    rather than a scan.

    **Nothing here guards a met demand.** It used to: under the retired order the
    worst seated score outranked the shortfall, so the loop would evacuate a mode
    floor to lift one seat and a `protected` set had to stop it. The tiers were
    swapped on 2026-08-31 and the guard went with them — a demand the gallery meets
    is kept by the order, because giving it back is a tier-2 loss and the two tiers
    beneath cannot pay for one.
    """

    def __init__(self, state, order: dict | None, demands: list):
        self.state = state
        self.order = order
        self.demands = list(demands)
        self._ranks: list = []
        #: `{seat key: its value}`. The sorted list answers "the worst seat"; this
        #: answers "the worst seat **inside this set**", which is what the swap
        #: loop's per-candidate prune asks once per row of the view.
        self._value_at: dict = {}
        self._total = 0.0

    # -- what is seated ------------------------------------------------- #
    @property
    def n(self) -> int:
        return self.state.n

    @property
    def filled(self) -> int:
        return self.state.filled

    @property
    def full(self) -> bool:
        return self.state.full

    def value(self, candidate) -> float:
        return value_of(candidate, self.order)

    def seat(self, candidate, why: str) -> None:
        import bisect

        value = self.value(candidate)
        self.state.seat(candidate, why)
        bisect.insort(self._ranks, (value, str(candidate.key)))
        self._value_at[str(candidate.key)] = value
        self._total += value

    def unseat(self, key):
        candidate = self.state.unseat(key)
        value = self.value(candidate)
        self._ranks.remove((value, str(candidate.key)))
        self._value_at.pop(str(candidate.key), None)
        self._total -= value
        return candidate

    # -- what it is worth ----------------------------------------------- #
    def shortfall(self, filled: int | None = None, count=None) -> int:
        """Total seats short across every demand, at a given fill.

        `count` lets a caller ask the question about a set it has not built: the
        swap loop hands it a function that adjusts one demand's tally for the seat
        going out and the one coming in, which is two comparisons rather than a
        copy of the state.
        """
        filled = self.filled if filled is None else int(filled)
        short = 0
        for demand in self.demands:
            got = demand.held(self.state) if count is None else count(demand)
            short += max(0, demand.wanted(filled) - got)
        return short

    def short_demands(self) -> list:
        """Every demand this gallery is currently short of. One pass's worth."""
        return [
            demand
            for demand in self.demands
            if demand.held(self.state) < demand.wanted(self.filled)
        ]

    def hopeless(self, candidate, counted: set, short: list) -> bool:
        """Whether **no** 1-swap seating `candidate` could improve any tier.

        Asked before the diversity rule is, and that is the point: a candidate
        this refuses never costs a pixel-cloud signature. It reads only
        [`rules.State.counted_removals`], which is dictionary lookups.

        The argument, tier by tier. Tier 1 cannot move — a 1-swap keeps the seat
        count. **Tier 2 is the exception and it is load-bearing**: the shortfall
        falls only if the arriving candidate covers a demand that is currently
        short, so a low-ranked row covering a starved mode is exactly the swap this
        prune must never refuse, and it is exempted first. For tier 4 the sum
        improves only if the arriving candidate is worth more than the seat that
        leaves, and every seat that could leave is in `counted` (the diversity rule
        only ever narrows it), so a candidate worth no more than the weakest member
        of `counted` cannot improve it. Tier 3 is the same bound from the other
        side: for the worst seat to rise, the seat that leaves must **be** the
        worst one, and then the weakest member of `counted` is the worst seat
        itself — so a candidate at or below it cannot improve that either.

        The tier swap of 2026-08-31 left this sound and made it slightly weaker:
        the exemption used to sit under two tiers this bound covers and now sits
        over them, so a candidate the value bound settles is refused only when it
        also covers nothing short. That is the same set it always was — the
        exemption was tested first before the swap too — and the prune is
        unchanged in code for that reason.
        """
        if any(demand.counts(candidate) for demand in short):
            return False
        if len(counted) >= self.filled:
            weakest = self.worst_value
        else:
            weakest = min(self._value_at[key] for key in counted)
        return weakest is not None and self.value(candidate) <= weakest

    @property
    def worst_value(self) -> float | None:
        """The weakest seated value, or `None` on an empty gallery. Tier 2."""
        return self._ranks[0][0] if self._ranks else None

    @property
    def objective(self) -> Objective:
        return Objective(
            seats=self.filled,
            worst=self.worst_value,
            shortfall=self.shortfall(),
            total=self._total,
        )

    def after_swap(self, out_key: str, arriving) -> Objective:
        """What the objective would be with `out_key` gone and `arriving` seated.

        Nothing is mutated. Every tier is arithmetic on the two candidates and the
        counts already held, which is what makes one pass of the loop linear in the
        view rather than quadratic in the seats.
        """
        leaving, _why = self.state.seated[str(out_key)]
        gone = (self.value(leaving), str(out_key))
        arrived = self.value(arriving)
        # `inf` where the leaving seat is the only one: the arriving candidate
        # then IS the worst seat, and reading a second entry that does not exist
        # is how a one-seat gallery used to crash the loop.
        if len(self._ranks) == 1:
            rest = math.inf
        else:
            rest = self._ranks[1][0] if self._ranks[0] == gone else self._ranks[0][0]
        return Objective(
            seats=self.filled,
            worst=min(arrived, rest),
            shortfall=self.shortfall(
                count=lambda demand: (
                    demand.held(self.state)
                    - (1 if demand.counts(leaving) else 0)
                    + (1 if demand.counts(arriving) else 0)
                )
            ),
            total=self._total - gone[0] + arrived,
        )

    def weakest(self, among, count: int) -> list:
        """The `count` weakest seated keys inside `among`, by the leg's key.

        The sorted rank list is walked from the bottom, so this is `count` steps
        and not a sort of the whole gallery — which matters because the swap loop
        asks it once per candidate in the view.

        **Every seat in `among` is offered.** There is no second filter here: what
        a swap may give back is the objective's business, and under the current
        tier order a removal that takes a met demand short loses on tier 2 and is
        refused by [`after_swap`] rather than hidden from it. This took a
        `protected` set and an `arriving` argument while the worst seat outranked
        the shortfall.
        """
        out = []
        for _value, key in self._ranks:
            if key not in among:
                continue
            out.append(key)
            if len(out) >= int(count):
                break
        return out


# --------------------------------------------------------------------------- #
# The greedy seed.
# --------------------------------------------------------------------------- #
def mandates(rows, demands: list, rank) -> list:
    """`[(demand, its subpool)]`, scarcest first. The seed's first leg.

    Ordering by score alone converts satisfiable problems into apparent
    infeasibility. Where the mode floors ask for most of the gallery — as the flat
    one-per-mode did at `n = 20`, eighteen of twenty seats over eleven modes that
    can field a handful of places between them — a walk down the ranked list
    spends its first seats on `smooth` and `exp_smoothing`, which have thousands
    of candidates each, and then reports that fifteen modes could not be seated.
    Every one of them could have been.

    So the demands are seated from their **own subpools first, scarcest first**,
    and only what is left over is drawn from the general pool by rank. The order
    is by how many distinct locations each demand can field, ascending: a mode
    with three eligible places is spent before a mode with eight hundred, because
    the three can only be spent one way.

    A demand with nothing at all is kept in the list rather than dropped, so the
    record says it was asked for and could not be met. Each subpool is in the
    **same** rank the general leg walks — a floor spent by one key while
    everything else went by another would be a gallery chosen two ways.
    """
    held: dict = {demand.name: [] for demand in demands}
    for candidate in rows:
        for demand in demands:
            if demand.counts(candidate):
                held[demand.name].append(candidate)
    ordered = sorted(
        demands,
        key=lambda demand: (len({c.location for c in held[demand.name]}), demand.name),
    )
    return [(demand, sorted(held[demand.name], key=rank)) for demand in ordered]


def seed(gallery: Gallery, rows, demands: list, rank, refused: dict, log=print) -> dict:
    """Fill the gallery greedily: the mandates from their own subpools, then the walk.

    This is the seating order this project already had, moved onto the set-level
    state. It is judged reasonable and its behaviour is deliberately unchanged: a
    candidate refused in the first leg is offered again in the second, because the
    state it was refused against has moved on, and nothing is ever seated by
    relaxing a rule it failed.

    What **is** different is the cost. The retired seed asked its pairwise rule for
    every pair of `[candidate, *seated]` at every candidate it considered, which is
    cubic in the gallery; this asks [`curation.rules.State.admits`], which reads
    the seated set once.
    """
    started = time.monotonic()
    taken: dict = {"mandate": 0, "general_pool": 0}
    for demand, members in mandates(rows, demands, rank):
        if gallery.full:
            break
        # Keep taking from this demand's subpool until it is met or the subpool is
        # spent. A leg that stopped at its first success would cap every mode at
        # one seat and quietly turn a floor of two into a floor of one.
        for candidate in members:
            if gallery.full or demand.held(gallery.state) >= demand.wanted(gallery.n):
                break
            why = gallery.state.refuses(candidate)
            if why is None:
                gallery.seat(candidate, demand.name)
                taken["mandate"] += 1
                refused.pop(candidate.key, None)
            else:
                refused[candidate.key] = why
                gallery.state.refusals[why] += 1

    for candidate in rows:
        if gallery.full:
            break
        if gallery.state.holds(candidate.key):
            continue
        why = gallery.state.refuses(candidate)
        if why is None:
            gallery.seat(candidate, "general_pool")
            taken["general_pool"] += 1
            refused.pop(candidate.key, None)
        else:
            refused[candidate.key] = why
            gallery.state.refusals[why] += 1

    seconds = time.monotonic() - started
    log(f"[solve] seed: {gallery.filled} of {gallery.n} seat(s) in {seconds:.1f}s")
    return {
        "of": "the mandated demands from their own subpools scarcest first, then the "
        "ranked walk. The seating order this project already had, on set-level state",
        "filled": gallery.filled,
        "asked": gallery.n,
        "by_leg": dict(taken),
        "objective": gallery.objective.record(),
        "seconds": round(seconds, 2),
    }


# --------------------------------------------------------------------------- #
# The 1-swap improvement.
# --------------------------------------------------------------------------- #
def improve(
    gallery: Gallery,
    rows,
    drops: int = SWAP_DROPS,
    passes: int = SWAP_PASSES,
    deadline: float | None = None,
    log=print,
) -> dict:
    """One seat out, one candidate in, to exhaustion. **Anytime and interruptible.**

    The gallery is valid at every moment: a swap is applied only after it has been
    scored, and the loop can stop at any point — a clock, a `Ctrl-C`, a pass cap —
    with a gallery nothing has to be undone from. That is the whole reason this
    method replaced an exact one that had no answer at all until it had a proof.

    ## The one prune, and it is sound

    A pass walks `rows` in rank order and **stops at the worst seated value**.
    Nothing below it can be in an improving swap: a 1-swap does not change the seat
    count, so tier 1 cannot move; seating a candidate worth less than the current
    worst makes the worst that candidate, so tier 2 gets worse; and the tiers are
    lexicographic, so a tier 3 or tier 4 gain cannot buy that. The prune is
    therefore not a budget — it is the set of candidates that provably cannot help
    — and it tightens on its own, because every swap that improves tier 2 raises
    the value the next pass stops at.

    ## What it costs

    Per candidate: an intersection of the **counted** rules' requirement sets,
    which is dictionary lookups; then [`Gallery.hopeless`], which is one more
    lookup; and only for what survives both, the diversity rule's one vectorized
    pass. The candidate's own reduced signature is made once and kept for the life
    of the pass, so a second pass over the same row costs no pixels at all.

    Those three together are what makes a pass that finds nothing cheap. Before
    them a pass cost the same whether it took forty-seven swaps or none, because
    every row in the view was decoded again on every pass.

    No 2-swaps. A 2-swap neighbourhood is the square of this one and this project
    has not measured that it buys anything; when it does, it is a separate ruling.
    """
    started = time.monotonic()
    taken: list = []
    by_tier: dict = {}
    walked = 0
    skipped = 0
    stopped = "a full pass found no improving swap"
    at_pass = 0
    try:
        for at_pass in range(1, int(passes) + 1):
            if not gallery.filled:
                stopped = "nothing was seated, so there is nothing to swap"
                break
            improved = 0
            floor_value = gallery.worst_value
            short = gallery.short_demands()
            for candidate in rows:
                if deadline is not None and time.monotonic() > deadline:
                    stopped = "the clock ran out; the gallery it stopped on is valid"
                    raise TimeoutError
                if gallery.value(candidate) < floor_value:
                    # Below the worst seat. Seating one of these makes IT the worst
                    # seat, so tier 3 gets worse and tier 4 cannot buy that back —
                    # but tier 2 sits above both, and a low-ranked row covering a
                    # demand the gallery is currently short of still improves it.
                    # That is the whole of "grab where possible" and it is usually a
                    # scarce mode's only row, so it is usually down here.
                    if not short:
                        # Nothing is short, so no tier above the worst seat can
                        # move: the rest of the walk is provably hopeless.
                        break
                    if not any(demand.counts(candidate) for demand in short):
                        continue
                if gallery.state.holds(candidate.key):
                    continue
                walked += 1
                counted = gallery.state.counted_removals(candidate)
                if not counted:
                    continue
                if gallery.hopeless(candidate, counted, short):
                    # Settled by arithmetic alone, so no picture is opened for it.
                    skipped += 1
                    continue
                leaving = gallery.state.narrowed(candidate, counted)
                if not leaving:
                    continue
                current = gallery.objective
                best, best_out = None, None
                for out_key in gallery.weakest(leaving, drops):
                    found = gallery.after_swap(out_key, candidate)
                    if found.beats(current) and (best is None or found.beats(best)):
                        best, best_out = found, out_key
                if best is None:
                    continue
                tier = best.tier_over(current)
                gone = gallery.unseat(best_out)
                gallery.seat(candidate, "swap")
                improved += 1
                short = gallery.short_demands()
                by_tier[tier] = by_tier.get(tier, 0) + 1
                taken.append(
                    {
                        "pass": at_pass,
                        "out": gone.key,
                        "in": candidate.key,
                        "tier": tier,
                        "objective": best.record(),
                    }
                )
                floor_value = gallery.worst_value
            log(f"[solve] swap pass {at_pass}: {improved} swap(s), {gallery.objective.record()}")
            if not improved:
                break
        else:
            stopped = f"the pass cap of {int(passes)} was reached, which is a backstop"
    except (TimeoutError, KeyboardInterrupt):
        if stopped.startswith("a full pass"):
            stopped = "interrupted; the gallery it stopped on is valid"
    seconds = time.monotonic() - started
    log(f"[solve] {len(taken)} swap(s) over {at_pass} pass(es) in {seconds:.1f}s — {stopped}")
    return {
        "of": "one seat out, one candidate in, accepted only on strict lexicographic "
        "improvement. No 2-swaps",
        "prune": "a pass stops at the worst seated value WHILE NOTHING IS SHORT: seating "
        "a candidate below it makes it the worst seat, so tier 3 gets worse and tier 4 "
        "cannot buy that back. With a demand short the walk runs on, because tier 2 sits "
        "above both and a low-ranked row covering a starved demand still improves it — "
        "only rows covering one are considered down there, which is a dictionary lookup "
        "and opens no picture. Sound rather than a budget",
        "second_prune": "and per candidate, against the weakest seat its own COUNTED rules "
        "would let leave — see solve.Gallery.hopeless. Sound by the same argument, and it "
        "is what keeps a hopeless candidate from ever costing a pixel-cloud signature",
        "settled_before_opening_a_picture": skipped,
        "drops_tried_per_candidate": int(drops),
        "drops_are": "the weakest seated by the leg's own key, inside the set of seats "
        "whose departure would admit the candidate. Every one of them is offered: what a "
        "swap may give back is the objective's business. The one heuristic here, and it is "
        "about which removals are OFFERED and never about which are accepted",
        "met_demands_are": "kept by the tier ORDER and by no guard. A removal that takes a "
        "met demand short loses tier 2, and tiers 3 and 4 cannot pay for one. This carried "
        "a `protected` set and a `demands_kept` flag while the worst seat outranked the "
        "shortfall; the tiers were swapped on 2026-08-31 and both went with them",
        "passes": at_pass,
        "pass_cap": int(passes),
        "candidates_considered": walked,
        "swaps": len(taken),
        "by_tier": dict(sorted(by_tier.items(), key=lambda item: -item[1])),
        "stopped_because": stopped,
        "objective": gallery.objective.record(),
        "seconds": round(seconds, 2),
        "taken": taken,
    }


# --------------------------------------------------------------------------- #
# The expand hook.
# --------------------------------------------------------------------------- #
def expand(viewed, gallery: Gallery, refused: dict) -> dict:
    """What the leg was short of, per stratum. **A stub: nothing is wired to mining.**

    The shape a mining leg could consume, and no more than that. For every demand
    that went short, the strata that could have fed it, what each held in the view
    and in the population behind it, and which rules acted on the rows it did not
    seat. That last column is the instruction: a stratum whose refusals are all
    `cell_allowance` is one the gallery is already full of and mining it buys
    nothing, while one whose refusals are all `location` is a stratum that exists
    only at places something else already took.

    It is emitted and written and read by nothing. When a mining leg reads it, the
    contract is this shape and this module is where it is stated.
    """
    per: dict = {}
    for candidate in viewed.rows:
        for stratum in view.strata_of(candidate):
            name = "|".join(stratum)
            held = per.setdefault(
                name,
                {
                    "stratum": name,
                    "kind": stratum[0],
                    "mode": stratum[1],
                    "cell": stratum[2],
                    "view_rows": 0,
                    "seated": 0,
                    "refused_by": {},
                },
            )
            held["view_rows"] += 1
            if gallery.state.holds(candidate.key):
                held["seated"] += 1
            why = refused.get(candidate.key)
            if why is not None:
                held["refused_by"][why] = held["refused_by"].get(why, 0) + 1
    short = []
    for demand in gallery.demands:
        wanted = demand.wanted(gallery.filled)
        got = demand.held(gallery.state)
        if got >= wanted:
            continue
        feeding = [
            held
            for held in per.values()
            if (held["mode"] == demand.of if demand.axis == "mode" else held["cell"] == demand.of)
        ]
        short.append(
            {
                "demand": demand.name,
                "axis": demand.axis,
                "of": demand.of,
                "asked": wanted,
                "held": got,
                "short": wanted - got,
                "strata": sorted(feeding, key=lambda held: -held["view_rows"]),
            }
        )
    return {
        "of": "per-stratum shortfall against the demands, in the shape a mining leg could "
        "consume. A STUB: nothing reads it and nothing is wired to mining",
        "stratum": "(kind, mode, cell)",
        "read": "a stratum whose refusals are cell_allowance is one the gallery is already "
        "full of and mining it buys nothing; one whose refusals are location exists only at "
        "places something else already took. Those are different instructions",
        "demands_short": len(short),
        "short": sorted(short, key=lambda row: -row["short"]),
    }


# --------------------------------------------------------------------------- #
# One pass, end to end.
# --------------------------------------------------------------------------- #
def solve(
    candidates=None,
    n: int = candidate_ledger.FIRST_SOLVE,
    rule: ceiling.Rule | None = None,
    targets: dict | None = None,
    floor: int | dict | None = None,
    locations: int | None = None,
    radius: float | None = distinct.PRESELECT_RADIUS,
    diversity: bool = True,
    group_cap: str = DEFAULT_GROUP_CAP,
    key: str = DEFAULT_KEY,
    order: dict | None = None,
    coverage: dict | None = None,
    allow_unranked: bool = False,
    theme: str | None = None,
    geometry_radius: float | None = None,
    rows_per_seat: int = view.ROWS_PER_SEAT,
    draw_seed: int = view.DRAW_SEED,
    swap: bool = True,
    drops: int = SWAP_DROPS,
    seconds: float | None = None,
    log=print,
) -> dict:
    """One gallery, chosen. The record is the return value; nothing is written.

    Pool construction first — the per-mode bars, then the neutral pre-selection at
    `radius` (`None` for none at all) — then the view, the seed and the swap loop.

    `floor` **replaces the default rule**, which is [`mode_policy.seat_floors`]:
    half each accepted strange mode's share of the strange seat budget, per mode.
    A **mapping** is one floor per mode; a **number** is the same floor for every
    accepted mode, which is both the flat [`mode_floor`] (`--flat-floor`) and the
    artificial floor a debug gallery uses. The record says which of the three.

    `targets` is `{cell: fraction}` and each one is a share of the **realized**
    seat count — see [`target_rule`]. `locations` truncates the reachable pool to
    that many strongest places. `seconds` is a wall budget for the swap loop
    alone: the seed always runs, and what the clock stops is improvement rather
    than the answer.

    `group_cap` names the palette-group cap rule and `key` the sort key. **Neither
    touches the pool**: the bars, the clearing rule and the neutral pre-selection
    all read the judge's own columns, so two passes differing in one of them
    differ in the order and in the cap and in nothing else.

    ## `theme` is the other gallery this leg builds

    Naming a cell makes this a **themed** pass, and it changes three things at
    once because the three are one decision:

    * the pool is the rows [`in_theme`] — dominant in that cell, read off each
      row's own dominance block — at the **relaxed** bar, `P(>=3) >= 0.50` for
      every accepted mode. A single-cell pool is q3-grade material and at the
      per-mode bars there is no pool to solve over;
    * the diversity rule is [`rules.Places`] at `geometry_radius` instead of the
      pixel-cloud twin test, because a single-cell pool is a near-duplicate pool
      under a metric over colour and the twin test would be refusing the theme;
    * nothing else. The caller still owns the target, the floor rule and the group
      cap, and a themed pass without `--target <cell>=1.0` is a pass the cell
      allowance refuses at nine seats — see [`ceiling.Rule.allowed`].

    Rows outside the cell are recorded [`OFF_THEME`], which is pool construction
    and not a refusal, so the rejection ledger stays a partition of the ledger.

    ## An unreadable clearing pool is a refusal, not a gallery

    A candidate the active key cannot read sorts last and cannot win a seat while
    a readable row is left, so a pool holding any is a pass that ignores them
    silently. A leg that merged without a flatness sweep left every row it wrote
    unreadable by [`RANK_KEY`]: `mine1h` merged 8,192 rows, cleared 1,326 into the
    pool and seated **none**, with nothing in the output saying so. So this
    raises. `allow_unranked` is the way past it and exists for one case — a
    picture on disk that will not decode, which has no reading and never will.
    """
    # Deferred: [`curation.headroom`] imports this module at the top, and its bars
    # are what the pool IS, so the dependency is real and only the import is late.
    from fractal_wallpapers.curation import headroom

    started = time.monotonic()
    if candidates is None:
        candidates, pool_refused = pool(log=log)
    else:
        pool_refused = {}
    reachable = strongest_locations(candidates, locations)
    if locations is not None:
        candidates = within(candidates, reachable)
    if order is None and str(key) != JUDGE_KEY:
        order, coverage = ranking_for(candidates, key, log=log)

    #: `{key: the rule that refused it, the last time it was offered}`.
    refused: dict = {}
    #: The rows the bars are taken over. A themed pass narrows it to its cell
    #: **before** the bars, so every count on the record is a count about the
    #: theme; the whole ledger is still walked for the rejection block below.
    population = candidates
    if theme is not None:
        population = in_theme(candidates, theme)
        for candidate in candidates:
            if str(theme) not in candidate.cells:
                refused[candidate.key] = OFF_THEME
        log(
            f"[solve] themed on {theme}: {len(population):,} of {len(candidates):,} "
            f"candidate(s) dominant in the cell, over "
            f"{len({c.location for c in population}):,} place(s)"
        )
        if not population:
            raise SolveRefused(
                f"no candidate in the ledger is dominant in {theme!r}, so there is no "
                "themed pool to solve over. `fractal-wallpapers curate colors` says which "
                "cells the pool actually holds"
            )

    # The accepted roster, not the engine's production one: a mode
    # [`mode_policy`] weights 0 has no rows in [`pool`] at all, so a floor over it
    # would be a mandate nothing could meet and an `unmet` row that is a policy
    # decision wearing the shape of a shortfall.
    modes = mode_policy.accepted()
    cap = ceiling.group_cap(n, group_cap)
    if rule is None:
        rule = rule_for(targets)
    rule.group_cap = cap
    natural = mode_policy.seat_floors(n)
    asked = natural if floor is None else floor
    held_floors = floors_for(asked, modes)
    #: The uniform floor, where the caller passed one. `None` says it was per mode.
    flat = None if isinstance(asked, dict) else int(asked)

    table = headroom.bars(population, relaxed=theme is not None)
    cleared = headroom.clearing(population, table)
    log(
        f"[solve] {len(cleared):,} of {len(population):,} candidates clear their mode's bar"
        + (" (relaxed: the P(>=3) crossing)" if theme is not None else "")
    )
    if radius is None:
        kept, preselection = list(cleared), {"skipped": "no neutral pre-selection was applied"}
    else:
        kept, preselection = distinct.preselect(cleared, radius=float(radius), log=log)
        survived = {candidate.key for candidate in kept}
        for candidate in cleared:
            if candidate.key not in survived:
                refused[candidate.key] = SAME_PLACE

    if order is not None:
        blind = [c for c in cleared if c.key not in order]
        if blind and not allow_unranked:
            raise SolveRefused(
                f"{len(blind):,} of {len(cleared):,} clearing candidate(s) carry no "
                f"{key!r} value, so they sort last and cannot win a seat while a readable "
                "row is left — which is a pass that silently ignores them rather than one "
                "that refuses them. The usual cause is a leg merged before its pictures "
                "were swept: run `fractal-wallpapers curate flatness sweep`, then solve "
                "again. Pass allow_unranked=True (`--allow-unranked`) only for a picture "
                "that is on disk and will not decode, which has no reading to take. "
                f"First few: {[c.key for c in blind[:3]]}"
            )
        if blind:
            log(
                f"[solve] {len(blind):,} clearing candidate(s) are unreadable by {key!r} and "
                "were allowed through: they sort last and no rule acts on them"
            )
    rank = ranking(order)
    unranked = 0 if order is None else sum(1 for c in kept if c.key not in order)

    viewed = view.stratify(
        kept,
        n=n,
        rule=rule,
        rank=rank,
        floors=held_floors,
        rows_per_seat=rows_per_seat,
        seed=draw_seed,
        log=log,
    )
    inside = {candidate.key for candidate in viewed.rows}

    # The reduced signatures the bound reads, from the sidecar where one has been
    # swept — see [`curation.signatures`]. Everything it answers for is a picture
    # this pass will not open; everything it misses is made on demand exactly as
    # before, so an unswept checkout is slower and never wrong.
    if not diversity:
        twins = None
    elif theme is not None:
        # Geometry-only distinctness, and the sidecar is not consulted: it holds
        # reduced pixel-cloud signatures, which this rule never reads.
        twins = rules.Places(
            rules.places_for(viewed.rows),
            {candidate.key: candidate.location for candidate in viewed.rows},
            tau=geometry_radius,
        )
        log(
            f"[solve] the diversity rule is {twins.NAME} at {twins.tau}: "
            f"{len(twins.places):,} place descriptor(s), no picture opened"
        )
    else:
        held_signatures = signatures.for_candidates(viewed.rows)
        if held_signatures:
            log(
                f"[solve] {len(held_signatures):,} of {len(viewed.rows):,} reduced "
                "signature(s) from the sidecar"
            )
        twins = rules.Twins(rules.clouds_for(viewed.rows), reduced=held_signatures)
    state = rules.State(rule, n, diversity=twins)
    demands = demands_for(held_floors, rule.targets)
    gallery = Gallery(state, order, demands)

    seeded = seed(gallery, viewed.rows, demands, rank, refused, log=log)
    swapped = (
        improve(
            gallery,
            viewed.rows,
            drops=drops,
            deadline=None if seconds is None else time.monotonic() + float(seconds),
            log=log,
        )
        if swap
        else {"of": "not run: this pass was asked for the seed alone", "swaps": 0, "taken": []}
    )

    # The ledger is taken against the **finished** gallery and not against the
    # moving state the seed happened to test each row under, which is what the
    # sequential leg this replaced could only do. The four counted rules are
    # dictionary lookups, so every clearing candidate can be asked; the diversity
    # rule is a signature apiece, so the rows it acted on keep its answer and no
    # row is asked for the first time here.
    #
    # It matters most for the rows the **view** did not reach. The view is this
    # pass's own budget and never a rule, and a row at a place a seat took was
    # refused by the location rule whether or not the pass could reach it — a
    # ledger reporting that as `the view did not reach it` would hide the columns
    # a mine is aimed down.
    for candidate in kept:
        if gallery.state.holds(candidate.key):
            continue
        counted = gallery.state.counted_refusal(candidate)
        if counted is not None:
            refused[candidate.key] = counted
        elif refused.get(candidate.key) in (None, UNSEATED, OUTSIDE_THE_VIEW):
            refused[candidate.key] = UNSEATED if candidate.key in inside else OUTSIDE_THE_VIEW
    for candidate in candidates:
        if not gallery.state.holds(candidate.key) and candidate.key not in refused:
            refused[candidate.key] = BELOW_BAR
    for key_name in list(refused):
        if gallery.state.holds(key_name):
            refused.pop(key_name)

    seated_rows = [
        _seated(candidate, why, None if order is None else order.get(candidate.key))
        for candidate, why in gallery.state.seated.values()
    ]
    seated_rows.sort(key=lambda row: (-_rank_of(row), str(row["key"])))
    placement = attribution(seated_rows, cleared, order, gallery, rule, n)
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": _config(
            n, rule, modes, table, flat, held_floors, natural, group_cap, order, key, theme
        ),
        "objective": {
            "of": OBJECTIVE,
            "tiers": ["seats", "shortfall", "worst", "sum"],
            "rank_quantity": "rank_key" if order is not None else JUDGE_KEY,
            "seed": seeded.get("objective"),
            "final": gallery.objective.record(),
            "above_q4_bar": sum(1 for row in seated_rows if row["p_ge4"] >= Q4_BAR),
            "q4_bar": Q4_BAR,
            "q4_basis": Q4_BASIS,
            "q4_bar_is": "a statistic on this record and not the pool rule. What the pool "
            "is is headroom.bars, which puts a mode without enough places above P(>=4) on "
            "P(>=3) instead — so a fallback mode's seats sit below this legitimately",
        },
        "pool": {
            "refused": pool_refused,
            "reachable_locations": len(reachable),
            "truncated_to": locations,
        },
        "theme": None
        if theme is None
        else {
            "cell": str(theme),
            "membership": "the row's own colour.cells dominance block, never the carrier "
            "table: the table is a prior about which maps make the cell and a gate built "
            "on a prior admits a picture nobody measured",
            "bar": "relaxed: P(>=3) >= "
            f"{headroom.FALLBACK_BAR} for every accepted mode, not the per-mode rule",
            "in_the_cell": len(population),
            "in_the_cell_locations": len({c.location for c in population}),
            "outside_the_cell": len(candidates) - len(population),
            "diversity": "geometry-only distinctness over the neutral descriptors. The "
            "pixel-cloud twin test is over a picture's COLOUR cloud, so a single-cell pool "
            "is a near-duplicate pool under exactly it",
        },
        "order": {
            "key": JUDGE_KEY if order is None else "rank_key",
            "of": "the render judge's P(>=4) on the candidate"
            if order is None
            else "a fitted rank key, applied to the ORDER and the OBJECTIVE — every bar, "
            "the clearing rule and the neutral pre-selection still read the judge's own "
            "columns",
            "ranked": len(kept) - unranked,
            "unranked": unranked,
            "unranked_are": "sorted last and never refused: no rule acted on them",
            "unranked_allowed": bool(allow_unranked),
            "coverage": coverage,
        },
        "preselection": preselection,
        "view": viewed.record(),
        "seed": seeded,
        "swaps": swapped,
        "population": {
            "candidates": len(candidates),
            "clearing": len(cleared),
            "after_the_preselection": len(kept),
            "in_the_view": len(viewed),
            "locations": len({c.location for c in candidates}),
            "clearing_locations": len({c.location for c in cleared}),
            "locations_after_the_preselection": len({c.location for c in kept}),
        },
        "filled": gallery.filled,
        "unfilled": n - gallery.filled,
        "seated": seated_rows,
        "attribution": placement,
        "shortfalls": _shortfalls(gallery, rule, modes, n, held_floors, cleared, refused),
        "rules": state.record(),
        "diversity": None if twins is None else twins.record(),
        "diversity_refusals": dict(sorted(state.refused_for.items())),
        "expand": expand(viewed, gallery, refused),
        "rejection": rejection(
            candidates, refused, log=log, order=rules.rules_for(state.diversity)
        ),
        "samples": samples(
            candidates, refused, against=_lost_to(state, preselection, cleared), rank=rank
        ),
        "seconds": round(time.monotonic() - started, 2),
    }
    block = record["shortfalls"]["modes"]
    log(
        f"[solve] {record['filled']} of {n} seat(s) in {record['seconds']}s; "
        f"{block['represented']} of {block['of']} mode(s) represented, "
        f"{block['below_the_floor_count']} below a floor "
        f"{'of ' + str(flat) if flat is not None else 'set per mode'}"
    )
    return record


def _config(
    n: int,
    rule: ceiling.Rule,
    modes: list,
    table: dict,
    flat: int | None,
    held: dict,
    natural: dict,
    group_cap: str,
    order: dict | None,
    key: str,
    theme: str | None = None,
) -> dict:
    return {
        "n": n,
        "theme": None if theme is None else str(theme),
        "method": "a stratified view, a greedy seed, and 1-swap improvement to exhaustion. "
        "ANYTIME: the gallery is valid from its first seat and nothing here claims "
        "optimality. The exact solve it replaced is retired",
        "objective": OBJECTIVE,
        "order": "the mandated demands from their own subpools, scarcest first; then the "
        "general pool by the rank key; then swaps",
        "bars": {name: block["rule"] for name, block in sorted(table["modes"].items())},
        "bars_are": "the pool definition. curation.headroom.bars: P(>=4) for a mode with "
        "enough places above it, P(>=3) for one without"
        + (
            ". RELAXED for this themed pass: every accepted mode on the P(>=3) crossing"
            if theme is not None
            else ""
        ),
        "ceiling": {
            "k": rule.k,
            "cell_share": ceiling.CELL_SHARE,
            "family_share": ceiling.FAMILY_SHARE,
            "allowance": "floor(k * t * n) + 1",
            "group_cap": rule.group_cap,
            "group_cap_rule": str(group_cap),
            "group_cap_from": "ceiling.GROUP_CAP"
            if str(group_cap) == ceiling.IDENTITY
            else f"max(1, floor({ceiling.GROUP_CAP_RATE} * n))",
            "targets": dict(sorted(rule.targets.items())),
            "target_rule": target_rule(),
        },
        "sort_key": JUDGE_KEY if order is None else "rank_key",
        "sort_key_named": str(key),
        # The uniform floor, or `None` where the floors are per mode — which is
        # what the default rule builds. Both shapes are always in `mode_floors`.
        "mode_floor": flat,
        "mode_floors": dict(held),
        "mode_floor_rule": floor_rule(n, flat, held, natural, modes),
        # What nobody naming a floor would have got: the default rule's answer.
        "mode_floor_natural": floors_for(natural, modes),
        "mode_floor_artificial": dict(held) != floors_for(natural, modes),
        "modes": modes,
        "mode_policy": mode_policy.record(),
    }


# --------------------------------------------------------------------------- #
# What the answer looks like.
# --------------------------------------------------------------------------- #
def _seated(candidate, why: str, rank: float | None = None) -> dict:
    """One seat's row. `rank` is the value the leg's own key gave it, written
    beside `p_ge4` and never over it: a sheet sorted good-to-bad has to sort by
    the key the leg actually walked, and a reader comparing two galleries has to
    be able to see both numbers."""
    return {
        "key": candidate.key,
        "seated_for": why,
        "rank": None if rank is None else round(float(rank), 6),
        "location": candidate.location,
        "partition": candidate.partition,
        "mode": candidate.mode,
        "kind": candidate.kind,
        "palette_group": candidate.group,
        "cells": list(candidate.cells),
        "families": list(candidate.families),
        "p_ge4": round(candidate.score, 6),
        "p_ge3": round(candidate.p_ge3, 6),
        "above_bar": candidate.above_bar,
        "picture": candidate.picture,
    }


def leg_of(seated_for: str) -> str:
    """Which of [`LEGS`] placed a seat, off the `seated_for` the leg stamped."""
    held = str(seated_for)
    if held == "swap":
        return "swap"
    return "general_pool" if held == "general_pool" else "mandate"


def _per_mode(gallery: Gallery, modes: list, held: dict, cleared: list, refused: dict) -> dict:
    """`{mode: what its floor asked for and what it got}` — the floor, seat by seat.

    Three facts per mode, because a mode short of its floor is short for one of two
    unrelated reasons and a single list conflates them. `clearing` is how many of
    that mode's candidates cleared their bar at all, and `refused_by` is which
    rules acted on the ones that were not seated — so a mode the **ceiling** beat
    reads apart from a mode the **pool** never held. The ceiling winning is the
    designed outcome, not a fault: a bar outranks a guarantee, and an unfilled
    floor beats a padded gallery.
    """
    supply: dict = {}
    acted: dict = {}
    for candidate in cleared:
        if candidate.mode in held:
            supply[candidate.mode] = supply.get(candidate.mode, 0) + 1
            why = refused.get(candidate.key)
            if why is not None:
                acted.setdefault(candidate.mode, {})
                acted[candidate.mode][why] = acted[candidate.mode].get(why, 0) + 1
    out: dict = {}
    for name in modes:
        asked = int(held.get(name, 0))
        seated = len(gallery.state.modes.get(name, ()))
        out[name] = {
            "floor": asked,
            "seated": seated,
            "short": max(0, asked - seated),
            "clearing": supply.get(name, 0),
            "refused_by": dict(sorted(acted.get(name, {}).items(), key=lambda item: -item[1])),
        }
    return out


def _shortfalls(
    gallery: Gallery,
    rule: ceiling.Rule,
    modes: list,
    n: int,
    held: dict,
    cleared: list,
    refused: dict,
) -> dict:
    """Every demand's shortfall and every ceiling's realized fill, recorded rather
    than repaired.

    **A mode nobody asked for is not a mode that went short.** `starved` is a floor
    above zero that went unfilled; `floor_never_needed` is a floor of zero, which
    no gallery can fail. Conflating them is how a floor rule reads as working when
    it is switched off — and how a real starvation hides inside a list most of
    whose entries were never at risk.
    """
    state = gallery.state
    per_mode = _per_mode(gallery, modes, held, cleared, refused)
    starved = [name for name in modes if per_mode[name]["short"] > 0]
    never = [name for name in modes if per_mode[name]["floor"] == 0]
    asked = {per_mode[name]["floor"] for name in modes}
    uniform = next(iter(asked)) if len(asked) == 1 else None
    counts = state.counts(state.cells)
    kin = state.counts(state.families)
    groups = state.counts(state.groups)
    held_modes = state.counts(state.modes)
    return {
        "seats": {"asked": n, "filled": state.filled, "unfilled": n - state.filled},
        "demands": {
            "of": "every demand this pass carried, mode floors and colour targets alike. "
            "The third objective tier is the sum of the `short` column",
            "short_total": gallery.shortfall(),
            "rows": [
                {
                    "demand": demand.name,
                    "axis": demand.axis,
                    "of": demand.of,
                    "asked": demand.wanted(state.filled),
                    "held": demand.held(state),
                    "short": max(0, demand.wanted(state.filled) - demand.held(state)),
                }
                for demand in gallery.demands
            ],
        },
        "modes": {
            "floor": uniform,
            "floors": {name: per_mode[name]["floor"] for name in modes},
            "floors_are": "one floor for every mode" if uniform is not None else "per mode",
            "asked": sum(per_mode[name]["floor"] for name in modes),
            "represented": sum(1 for name in modes if state.modes.get(name)),
            "of": len(modes),
            "per_mode": per_mode,
            "starved": starved,
            "starved_count": len(starved),
            "starved_are": "a floor above zero that went unfilled. Read `per_mode` for "
            "which: a mode with `clearing` above `seated` lost its seats to a rule named "
            "in `refused_by`, and one with `clearing` at `seated` had nothing left to seat",
            "floor_never_needed": never,
            "floor_never_needed_count": len(never),
            "floor_never_needed_are": "asked for nothing, so they cannot have gone short",
            "below_the_floor": starved,
            "below_the_floor_count": len(starved),
            "counts": dict(sorted(held_modes.items(), key=lambda item: -item[1])),
        },
        "cells": {
            "held": len(counts),
            "over_allowance": {
                cell: count
                for cell, count in sorted(counts.items())
                if count > rule.allowed(cell, n)
            },
            "counts": dict(sorted(counts.items(), key=lambda item: -item[1])),
        },
        "families": {
            "held": len(kin),
            "over_allowance": {
                family: count
                for family, count in sorted(kin.items())
                if count > rule.allowed(family, n)
            },
            "counts": dict(sorted(kin.items(), key=lambda item: -item[1])),
        },
        "groups": {
            "held": len(groups),
            "cap": rule.group_cap,
            # What the cap ACTUALLY bound to, which is the number the ruling that
            # raised it asked to see rather than assume: a cap of three is only a
            # cap of three if something spent it.
            "realized_max": max(groups.values(), default=0),
            "at_the_cap": sum(1 for count in groups.values() if count >= rule.group_cap),
            "counts": dict(sorted(groups.items(), key=lambda item: (-item[1], item[0]))[:20]),
            "over_cap": {
                group: count for group, count in sorted(groups.items()) if count > rule.group_cap
            },
        },
        "refusals_while_choosing": dict(sorted(state.refusals.items(), key=lambda i: -i[1])),
        "read": "a shortfall here is `this leg did not find it`, never `the pool does not "
        "hold it`. The only infeasibility claims are the census's necessary conditions",
    }


# --------------------------------------------------------------------------- #
# The leg attribution — where each seat came from, and how strong it was.
# --------------------------------------------------------------------------- #
def _percentiles(cleared, order: dict | None):
    """`(value -> percentile, readable, unreadable)` over the clearing pool.

    A candidate the key could not read sorts **last** in the walk, so it counts as
    below every readable row here too — anything else would quietly inflate every
    percentile by the size of the hole.
    """
    import bisect

    values = sorted(
        float(order[c.key]) if order is not None else float(c.score)
        for c in cleared
        if order is None or c.key in order
    )
    unreadable = len(cleared) - len(values)
    total = max(1, len(cleared))

    def of(value) -> float:
        if value is None:
            return 0.0
        return round(100.0 * (unreadable + bisect.bisect_left(values, float(value))) / total, 2)

    return of, len(values), unreadable


def _spread(values) -> dict:
    held = sorted(values)
    if not held:
        return {"seats": 0, "min": None, "median": None, "max": None}
    return {"seats": len(held), "min": held[0], "median": held[len(held) // 2], "max": held[-1]}


def attribution(seated, cleared, order, gallery: Gallery, rule, n: int) -> dict:
    """Where every seat came from and how strong it was. **Mutates `seated`.**

    Three questions, and together they are the mining list rather than a summary
    of one:

    * for each seat, its **rank percentile inside the clearing pool** and which of
      [`LEGS`] placed it — so a leg spending seats on the tail is visible as a leg
      rather than as a handful of weak pictures;
    * which legs hold the bottom [`BOTTOM_QUARTILE`] of the seats by that
      percentile;
    * per mode and per cell, **how strong the best candidate the pool could offer
      was** — because a cell whose best available row sits at the fortieth
      percentile is a cell to go and make candidates for, and a cell merely at its
      allowance is a cell the gallery is already full of. Those are two different
      instructions and they are reported apart.

    The percentile is against the **clearing pool** and not the view: the view is
    this pass's own budget and the pre-selection refuses places, so a percentile
    against either would be measured against a population no mine can aim at.
    """
    percentile_of, readable, unreadable = _percentiles(cleared, order)
    for row in seated:
        row["leg"] = leg_of(row["seated_for"])
        row["rank_percentile"] = percentile_of(_rank_of(row))

    by_leg: dict = {}
    for row in seated:
        by_leg.setdefault(row["leg"], []).append(row["rank_percentile"])
    cut = max(1, int(round(BOTTOM_QUARTILE * len(seated)))) if seated else 0
    weakest = sorted(seated, key=lambda row: (row["rank_percentile"], row["key"]))[:cut]

    def tally(rows, values_of) -> dict:
        out: dict = {}
        for row in rows:
            for value in values_of(row):
                out[str(value)] = out.get(str(value), 0) + 1
        return dict(sorted(out.items(), key=lambda item: -item[1]))

    return {
        "percentile_of": "the seat's own rank value against every candidate that cleared "
        "its mode's bar, before the neutral pre-selection and before the view",
        "clearing_pool": {
            "candidates": len(cleared),
            "readable_by_the_key": readable,
            "unreadable_by_the_key": unreadable,
            "unreadable_sit_at": "the bottom, which is where the walk sorts them",
        },
        "legs": LEGS,
        "by_leg": {name: _spread(values) for name, values in sorted(by_leg.items())},
        "by_seated_for": tally(seated, lambda row: (row["seated_for"],)),
        "bottom_quartile": {
            "share": BOTTOM_QUARTILE,
            "seat_count": len(weakest),
            "percentile_at_or_below": weakest[-1]["rank_percentile"] if weakest else None,
            "by_leg": tally(weakest, lambda row: (row["leg"],)),
            "by_seated_for": tally(weakest, lambda row: (row["seated_for"],)),
            "by_mode": tally(weakest, lambda row: (row["mode"],)),
            "by_cell": tally(weakest, lambda row: row["cells"]),
            "seats": [
                {
                    "key": row["key"],
                    "rank_percentile": row["rank_percentile"],
                    "leg": row["leg"],
                    "seated_for": row["seated_for"],
                    "mode": row["mode"],
                    "cells": row["cells"],
                    "p_ge4": row["p_ge4"],
                }
                for row in weakest
            ],
        },
        "best_available": _best_available(cleared, order, percentile_of, gallery),
        "unmet": _unmet(gallery),
        "binding": _binding(gallery, rule, n),
    }


def _best_available(cleared, order, percentile_of, gallery: Gallery) -> dict:
    """Per mode and per cell, how strong the pool's **best** candidate was. Weakest first.

    The whole of the "go and make more of this" list. A mode or a cell whose best
    available candidate sits low in the clearing pool is one where the gallery had
    nothing good to seat, whatever it seated; ranked by how weak, so the list has
    an order somebody can work down.
    """
    axes = {"modes": lambda held: (held.mode,), "cells": lambda held: held.cells}
    out: dict = {}
    for axis, values_of in axes.items():
        best: dict = {}
        for candidate in cleared:
            value = (
                None
                if (order is not None and candidate.key not in order)
                else (float(candidate.score) if order is None else float(order[candidate.key]))
            )
            for name in values_of(candidate):
                held = best.setdefault(
                    str(name), {"rows": 0, "locations": set(), "best": None, "key": None}
                )
                held["rows"] += 1
                held["locations"].add(candidate.location)
                if value is not None and (held["best"] is None or value > held["best"]):
                    held["best"], held["key"] = value, candidate.key
        state = gallery.state
        seated = state.counts(state.modes if axis == "modes" else state.cells)
        rows = [
            {
                "name": name,
                "cleared_rows": held["rows"],
                "cleared_locations": len(held["locations"]),
                "best_rank": None if held["best"] is None else round(held["best"], 6),
                "best_percentile": percentile_of(held["best"]),
                "best_candidate": held["key"],
                "seated": seated.get(name, 0),
            }
            for name, held in best.items()
        ]
        out[axis] = sorted(rows, key=lambda row: (row["best_percentile"], row["name"]))
    return out


def _unmet(gallery: Gallery) -> list:
    """Every demand the pass asked for and did not get, and how far short.

    Only the things that **can** go unmet. The cell and family allowances and the
    palette-group cap are ceilings: a gallery cannot fall short of one, it can only
    bind against it, and that is [`_binding`] and a different instruction.
    """
    short = [
        {
            "constraint": "seats",
            "asked": int(gallery.n),
            "held": gallery.filled,
            "short": int(gallery.n) - gallery.filled,
        }
    ]
    for demand in gallery.demands:
        wanted = demand.wanted(gallery.filled)
        got = demand.held(gallery.state)
        if got < wanted:
            short.append(
                {
                    "constraint": demand.name,
                    "asked": wanted,
                    "held": got,
                    "short": wanted - got,
                }
            )
    return [row for row in short if row["short"] > 0]


def _binding(gallery: Gallery, rule: ceiling.Rule, n: int) -> dict:
    """Every ceiling that was actually spent to its last seat. Not a shortfall.

    A cell at its allowance means the gallery is already as full of that colour as
    the ceiling permits, so more candidates there buy nothing; a cell whose best
    available row is weak is the opposite instruction. Both lists exist so that a
    mine is not aimed at the first one.
    """
    state = gallery.state
    cells = state.counts(state.cells)
    families = state.counts(state.families)
    groups = state.counts(state.groups)
    return {
        "cells_at_the_allowance": {
            cell: count
            for cell, count in sorted(cells.items(), key=lambda item: -item[1])
            if count >= rule.allowed(cell, n)
        },
        "families_at_the_allowance": {
            family: count
            for family, count in sorted(families.items(), key=lambda item: -item[1])
            if count >= rule.allowed(family, n)
        },
        "groups_at_the_cap": {
            group: count
            for group, count in sorted(groups.items(), key=lambda item: (-item[1], item[0]))
            if count >= rule.group_cap
        },
        "read": "a ceiling spent to its last seat, which is the OPPOSITE instruction to a "
        "weak `best_available` row: more candidates here cannot be seated",
    }


# --------------------------------------------------------------------------- #
# The rejection ledger — the product.
# --------------------------------------------------------------------------- #
def rejection(candidates, refused: dict, log=print, order: tuple | None = None) -> dict:
    """For every candidate not seated, which rule killed it, aggregated four ways.

    By cell, by family, by mode and by partition, because those are the four axes a
    leg can be aimed down. A cell whose whole refusal column is `cell_allowance` is
    a cell the gallery is already full of; one whose column is `location` is a cell
    that exists only at places something else already took, and the answer to those
    two is not the same answer.

    Aggregated over **distinct locations** as well as rows, for the reason every
    count in this module is: a rule that refused four hundred rows at twelve places
    refused twelve wallpapers.
    """
    axes = {
        "cells": lambda candidate: candidate.cells,
        "families": lambda candidate: candidate.families,
        "modes": lambda candidate: (candidate.mode,),
        "partitions": lambda candidate: (candidate.partition,),
    }
    rows: dict = {name: {} for name in axes}
    places: dict = {name: {} for name in axes}
    overall: dict = {}
    for candidate in candidates:
        why = refused.get(candidate.key)
        if why is None:
            continue
        overall[why] = overall.get(why, 0) + 1
        for axis, values_of in axes.items():
            for value in values_of(candidate):
                rows[axis].setdefault(value, {}).setdefault(why, 0)
                rows[axis][value][why] += 1
                places[axis].setdefault(value, {}).setdefault(why, set()).add(candidate.location)
    log(f"[solve] {sum(overall.values()):,} candidates refused; {dict(sorted(overall.items()))}")
    return {
        "reasons": dict(sorted(overall.items(), key=lambda item: -item[1])),
        "by": {
            axis: {
                str(value): {
                    "rows": dict(sorted(reasons.items(), key=lambda item: -item[1])),
                    "locations": {
                        why: len(keys)
                        for why, keys in sorted(
                            places[axis][value].items(), key=lambda item: -len(item[1])
                        )
                    },
                }
                for value, reasons in sorted(rows[axis].items())
            }
            for axis in axes
        },
        "read": "the rule that refused each candidate the LAST time it was offered, in "
        f"{list(order or rules.RULES)} order. `{UNSEATED}` broke no rule and simply lost; "
        f"`{OUTSIDE_THE_VIEW}` was never reached, which is this pass's own budget and not "
        f"a fact about the wallpaper; `{BELOW_BAR}` never entered the population at all, "
        f"and `{SAME_PLACE}` was refused at pool construction because another place inside "
        f"the neutral pre-selection radius took it. `{OFF_THEME}` is pool construction too: "
        "a themed pass only ever chooses among rows dominant in its own cell",
    }


def samples(candidates, refused: dict, count: int = SHOWN, against: dict | None = None, rank=None):
    """`{rule: the strongest few it refused}` — the visual half of the ledger.

    Strongest first inside each rule, because a refusal of a weak candidate says
    nothing: the question a sheet answers is whether the rule is throwing away
    pictures a person would have kept.

    `against` is `{key: what it lost to}` for the two rules where the refusal is
    about a *pair* — the diversity rule and the pre-selection. A twin refusal shown
    on its own is unreadable: the whole question is whether the picture it was
    refused against is the same wallpaper, and that is a two-picture question.
    """
    rank = ranking(None) if rank is None else rank
    held: dict = {}
    for candidate in sorted(candidates, key=rank):
        why = refused.get(candidate.key)
        if why is None:
            continue
        mine = held.setdefault(why, [])
        if len(mine) < int(count):
            row = _seated(candidate, why)
            lost_to = (against or {}).get(candidate.key)
            if lost_to is not None:
                row["lost_to"] = lost_to
            mine.append(row)
    return held


def _lost_to(state, preselection: dict, cleared: list) -> dict:
    """`{candidate key: the picture it lost to}` for the two pairwise refusals.

    Both are keyed by **candidate**, because that is what the rejection ledger and
    the sheet are keyed by — but the two rules do not refuse the same kind of
    thing. The diversity rule names a seated candidate. The pre-selection names a
    *place*, and every row that place carries went with it, so each of them is
    given the picture the place lost to.
    """
    pictures = {candidate.key: candidate.picture for candidate in cleared}
    at_place: dict = {}
    for candidate in cleared:
        at_place.setdefault(candidate.location, []).append(candidate.key)
    # The two diversity rules measure in different spaces, so the gap is written
    # under the column it was measured in and never under a shared name: the sheet
    # already knows both, and a caption saying `0.048` without saying in what is a
    # caption a reader can only misread.
    threshold = ceiling.TAU if state.diversity is None else state.diversity.tau
    column = "neutral" if getattr(state.diversity, "NAME", None) == "geometry" else "pixel_cloud"
    out = {
        key: {
            "picture": pictures.get(found["too_close_to"]),
            column: found["distance"],
            "rule": f"{found['rule']}: under {threshold} of a seated picture, "
            f"in the {column} metric",
        }
        for key, found in state.refused_for.items()
    }
    for row in preselection.get("refusals") or []:
        lost = {
            "picture": row["lost_to_picture"],
            "neutral": row["distance"],
            "rule": f"the same place: under {preselection['radius']} in the neutral descriptor",
        }
        for key in at_place.get(row["location"], ()):
            out[key] = lost
    return out


def _rank_of(row: dict) -> float:
    """The value the leg's own sort key gave one seat.

    `rank` where the pass carried one and `p_ge4` where it did not, which is the
    same number under the incumbent key and the right one under any other.
    """
    held = row.get("rank")
    return float(row.get("p_ge4") or 0.0) if held is None else float(held)


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def solve_dir(name: str) -> Path:
    return under("curation", UNIT, str(name))


def write_record(name: str, record: dict) -> Path:
    path = solve_dir(name) / "solve.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def read_record(name: str) -> dict:
    path = solve_dir(name) / "solve.json"
    if not path.is_file():
        raise SolveRefused(f"no record at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# What a gallery ships.
# --------------------------------------------------------------------------- #
def release_regime():
    """What the seats are rendered at. [`release.RELEASE_REGIME`] and not a second
    opinion about it: every leg that ships a wallpaper ships the same pixels, and
    the whole claim of this module is that only the *choosing* changed."""
    from fractal_wallpapers.curation import release

    return release.RELEASE_REGIME


def render_seats(
    name: str,
    record: dict,
    workers: int | None = None,
    regime=None,
    where: Path | None = None,
    timeout: float | None = ROW_BACKSTOP,
    log=print,
) -> dict:
    """Render every seat at release geometry. Mutates `record`.

    Two facts land on each seat and for the same reasons a pass's release leg
    records them: the **geometry**, because the default has moved once already and
    a sheet that captioned every picture with today's default would relabel every
    wallpaper an earlier gallery made; and the autolevel stamp is the *release
    render's own*, never the candidate's, because they are two renders and showing
    one under the other's caption is how a page says something false with every
    field on it true.

    No re-score. The release picture is the same recipe as the candidate the
    decision was taken on, at another size, and the judge's floors were fit on
    640x360 candidate renders. **Nothing here applies a bar of any kind**: every
    seat the leg chose is rendered and every render that succeeds is released.

    `workers` is [`release.DEFAULT_WORKERS`] unless a caller says otherwise — the
    machine's three-at-below-normal render pool, read from the module that owns it.

    `timeout` is [`ROW_BACKSTOP`], stamped onto every task so the **worker**
    imposes it. There is no gate: no row is ever declined, so the leg runs to
    completion.
    """
    from fractal_wallpapers.curation import release

    regime = release_regime() if regime is None else regime
    workers = release.DEFAULT_WORKERS if workers is None else int(workers)
    wanted = {str(seat["key"]) for seat in record["seated"]}
    # A keyed lookup and not a read: this needs the recipes behind a few hundred
    # seats, and reading the whole ledger for them held every other row in memory
    # for the length of a release render pass.
    rows = candidate_ledger.by_key(wanted)
    missing = wanted - set(rows)
    if missing:
        raise SolveRefused(
            f"{len(missing)} seat(s) name a recipe the ledger does not hold — "
            f"{sorted(missing)[:3]}. A seat cannot be rendered without its recipe."
        )
    where = (solve_dir(name) / "release") if where is None else Path(where)
    where.mkdir(parents=True, exist_ok=True)
    stamps = where / "autolevel_stamps.jsonl"
    tasks, done, reused = [], {}, []
    for seat in record["seated"]:
        row = rows[seat["key"]]
        recipe = row["recipe"]
        picture = where / f"{seat['key']}.png"
        if _already(picture, regime, log):
            done[seat["key"]] = picture
            reused.append(seat["key"])
            continue
        tasks.append(
            release.Task(
                id=seat["key"],
                row={
                    "family": recipe["family"],
                    "viewport": recipe["viewport"],
                    "maxiter": recipe["maxiter"],
                },
                colormap=recipe["colormap"],
                mode=recipe["mode"],
                output=str(picture),
                geometry={**regime.geometry(), "maxiter": int(recipe["maxiter"])},
                timeout=None if timeout is None else float(timeout),
            )
        )
    log(f"[solve] {len(tasks)} seat(s) to render at {regime.spelled}, {len(reused)} already there")
    outcomes = {"rendered": 0, "failed": 0}
    written: dict = {}
    timings: list = []

    def sink(task, result):
        outcomes["rendered" if result.ok else "failed"] += 1
        if result.ok:
            done[task.id] = Path(result.info["picture"])
        else:
            log(f"[solve] {task.id} failed at release size: {result.error}")
        timings.append(
            {
                "key": task.id,
                "seconds": round(result.seconds, 2),
                "ok": result.ok,
                "mode": task.mode,
                "maxiter": int(task.geometry["maxiter"]),
            }
        )
        if result.stamp is not None:
            written[task.id] = result.stamp
            with stamps.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps({"id": task.id, "autolevel": result.stamp}, ensure_ascii=False)
                    + "\n"
                )

    started = time.monotonic()
    leg = release.run_pass(tasks, workers, sink, log, leg=None)
    seconds = time.monotonic() - started
    stamped = _stamps(stamps)
    for seat in record["seated"]:
        key = seat["key"]
        seat["release_picture"] = tracked_name(done[key]) if key in done else None
        seat["release_autolevel"] = written.get(key, stamped.get(key))
        seat["release_geometry"] = regime.geometry() if key in done else None
    priced = [row["seconds"] for row in timings if row["ok"]]
    record["render"] = {
        "regime": regime.spelled,
        "geometry": regime.geometry(),
        "where": tracked_name(where),
        "workers": int(workers),
        "row_backstop_seconds": None if timeout is None else float(timeout),
        "killed": leg.get("killed", 0),
        "no_bar": "nothing in this leg re-scores and nothing in it refuses: every seat the "
        "leg chose is rendered, and a floor at shipping geometry does not exist",
        "planned": len(tasks) + len(reused),
        "reused": len(reused),
        "made": outcomes["rendered"],
        "failed": outcomes["failed"],
        "not_started": len(leg.get("not_started", [])),
        "seconds": round(seconds, 1),
        "seconds_per_render": round(seconds / max(1, outcomes["rendered"]), 1),
        "row_seconds": {
            "min": round(min(priced), 2) if priced else None,
            "median": round(sorted(priced)[len(priced) // 2], 2) if priced else None,
            "max": round(max(priced), 2) if priced else None,
        },
        "timings": sorted(timings, key=lambda row: -row["seconds"]),
    }
    return record["render"]


def _already(picture: Path, regime, log=print) -> bool:
    """Whether a picture on disk may be carried across as this regime's.

    Presence stopped being the whole test the day the regime became a parameter,
    so the frame is read off the file.
    """
    if not Path(picture).is_file():
        return False
    from PIL import Image

    try:
        with Image.open(picture) as opened:
            size = opened.size
    except Exception as failure:  # noqa: BLE001 - unreadable is a re-render, not a crash
        log(f"[solve] {Path(picture).name} will not open ({failure!r}); making it again")
        return False
    return tuple(size) == tuple(regime.resolution)


def _stamps(path: Path) -> dict:
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[str(row["id"])] = row.get("autolevel")
    return out


def autolevel_rate(record: dict) -> dict:
    """The release leg's autolevel act rate **with its denominator**.

    Three numbers and not one, because the operator has three outcomes and a bare
    percentage hides two of them. A seat gets a stamp when the operator was asked;
    `acted` is the subset where the curve was not the identity. A seat with no
    stamp at all was **never asked** — its mode is a direct-trap kind, which
    [`autolevel.applies_to`] answers no for at the one place that decides — and it
    belongs in neither the numerator nor the denominator.
    """
    seated = record.get("seated") or []
    stamped = [row for row in seated if row.get("release_autolevel")]
    acted = [row for row in stamped if (row.get("release_autolevel") or {}).get("acted")]
    return {
        "seats": len(seated),
        "asked": len(stamped),
        "acted": len(acted),
        "rate": None if not stamped else round(len(acted) / len(stamped), 4),
        "not_asked": len(seated) - len(stamped),
        "denominator": "the seats the operator was ASKED about — a stamp on the release "
        "render. A seat whose mode is a direct-trap kind is never asked and is in "
        "neither half",
    }


# --------------------------------------------------------------------------- #
# The contact sheet.
# --------------------------------------------------------------------------- #
def contact_sheet(name: str, record: dict, rejected=None, output=None) -> Path:
    """The seated, and a sample of the refused with the rule that refused each.

    Both halves, because a gallery on its own says only what the rules liked. A
    refusal captioned with the rule that made it is the thing a person can
    disagree with — and here the captions are the *product*, because a column of
    `cell_allowance` and a column of `location` are two different instructions to
    whatever makes candidates next.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    output = solve_dir(name) / "contact_sheet.html" if output is None else Path(output)
    config = record["config"]
    shortfalls = record["shortfalls"]
    # Sorted by the leg's OWN key, best first, and never shuffled. A sheet in
    # seating order is in scarcity order for its first seats, which reads as a
    # quality claim it is not making; and a sheet sorted by `p_ge4` under a leg
    # that ranked on something else is a picture of a different walk.
    key_name = str(config.get("sort_key") or JUDGE_KEY)
    ranked_seats = sorted(
        record.get("seated") or [], key=lambda row: (-_rank_of(row), str(row.get("key")))
    )

    def frame(picture) -> str:
        # `rehome` answers None for a name with no artifacts component, and a
        # release picture written outside the tree is exactly that. Keep the name
        # the record carried rather than crashing on it.
        source = None if not picture else (rehome(picture) or Path(picture))
        return (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )

    def shown(row: dict) -> str:
        """The release render where the leg made one, the candidate otherwise.

        A sheet of a *released* gallery has to show the pictures that were
        released: the candidate is 640x360 through the unmodified map and the
        release render is the shipping geometry with the autolevel operator inside
        it, so the two are different pictures of one recipe.
        """
        return frame(row.get("release_picture") or row.get("picture"))

    def card(row: dict, caption: str, seat: bool = False) -> str:
        lost_to = row.get("lost_to") or {}
        body = shown(row)
        if lost_to.get("picture"):
            body = (
                f"<div class='pair'><div class='frame'>{body}</div>"
                f"<div class='frame'>{frame(lost_to['picture'])}</div></div>"
            )
        released = row.get("release_picture")
        geometry = row.get("release_geometry") or {}
        facts = [
            f"mode <b>{html.escape(str(row.get('mode')))}</b>",
            f"P(&ge;4) {row.get('p_ge4')} &middot; P(&ge;3) {row.get('p_ge3')}",
            f"cells {html.escape(', '.join(row.get('cells') or []) or 'none')}",
            f"group {html.escape(str(row.get('palette_group')))}",
            f"partition {html.escape(str(row.get('partition')))}",
        ]
        if row.get("rank_percentile") is not None:
            facts.append(
                f"pool percentile <b>{row['rank_percentile']}</b> &middot; leg "
                f"{html.escape(str(row.get('leg')))}"
            )
        if released:
            frame_at = "x".join(str(at) for at in (geometry.get("resolution") or []))
            facts.append(
                f"shown at <b>{html.escape(frame_at)}ss{geometry.get('supersample')}</b> "
                f"&middot; {sheet_module.autolevel_line(row.get('release_autolevel'))}"
            )
        elif seat:
            # Only a SEAT can be missing a release picture; a refused candidate was
            # never going to have one, and saying so on every refusal card would be
            # noise that reads as a fault.
            facts.append("shown as the <b>candidate</b> render: this seat has no release picture")
        if lost_to:
            gap = lost_to.get("pixel_cloud", lost_to.get("neutral"))
            facts.append(f"lost to the picture beside it at <b>{gap}</b>")
        return (
            "<figure>"
            + (body if lost_to.get("picture") else f"<div class='frame'>{body}</div>")
            + "<figcaption>"
            f"<b>{html.escape(caption)}</b><ul>"
            + "".join(f"<li>{fact}</li>" for fact in facts)
            + "</ul></figcaption></figure>"
        )

    objective = record.get("objective") or {}
    final = objective.get("final") or {}
    swaps = record.get("swaps") or {}
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>solve {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}"
        ".pair { display: grid; gap: .4rem; grid-template-columns: 1fr 1fr; }"
        "</style>",
        f"<h1>solve {html.escape(name)}</h1>",
        f"<p class='lede'>{record['filled']} of {config['n']} seat(s) filled from "
        f"{record['population'].get('in_the_view', 0):,} row(s) in the view over "
        f"{record['population'].get('locations_after_the_preselection', 0):,} locations that "
        f"clear their mode's bar and survive the neutral pre-selection. "
        f"{shortfalls['modes']['represented']} of {shortfalls['modes']['of']} modes "
        f"represented, against a floor of {shortfalls['modes']['floor']}"
        f"{'' if shortfalls['modes']['floor'] is not None else ' set per mode'}. "
        f"Sorted on <b>{html.escape(key_name)}</b>, palette-group cap "
        f"<b>{config['ceiling']['group_cap']}</b> "
        f"({html.escape(str(config['ceiling'].get('group_cap_rule', 'identity')))}). "
        f"Objective: worst <b>{final.get('worst')}</b>, shortfall "
        f"<b>{final.get('shortfall')}</b>, sum <b>{final.get('sum')}</b> after "
        f"<b>{swaps.get('swaps', 0)}</b> swap(s). Anytime: nothing here is optimal and a "
        "shortfall is not infeasibility.</p>",
        f"<h2>Seated ({record['filled']}), best first by <code>{html.escape(key_name)}</code></h2>",
        "<div class='grid'>"
        + "".join(
            card(row, f"{at}. {key_name} {_rank_of(row):.4f} — {row['seated_for']}", seat=True)
            for at, row in enumerate(ranked_seats, start=1)
        )
        + "</div>",
    ]
    for why, sample in sorted((rejected or {}).items()):
        if not sample:
            continue
        lines += [
            f"<h2>Refused by <code>{html.escape(why)}</code> ({len(sample)} shown)</h2>",
            "<div class='grid'>" + "".join(card(row, why) for row in sample) + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


__all__ = [
    "BELOW_BAR",
    "BOTTOM_QUARTILE",
    "DEFAULT_GROUP_CAP",
    "DEFAULT_KEY",
    "JUDGE_KEY",
    "KEYS",
    "LEGS",
    "OBJECTIVE",
    "OUTSIDE_THE_VIEW",
    "Q4_BAR",
    "Q4_BASIS",
    "RANK_KEY",
    "ROW_BACKSTOP",
    "SAME_PLACE",
    "SCHEMA",
    "SEATS_PER_MODE_FLOOR",
    "SHOWN",
    "SWAP_DROPS",
    "SWAP_PASSES",
    "UNIT",
    "UNSEATED",
    "Candidate",
    "Demand",
    "Gallery",
    "Objective",
    "SolveRefused",
    "attribution",
    "autolevel_rate",
    "contact_sheet",
    "demands_for",
    "expand",
    "floor_rule",
    "floors_for",
    "improve",
    "leg_of",
    "mandates",
    "mode_floor",
    "picture_of",
    "pool",
    "ranking",
    "ranking_for",
    "read_record",
    "rejection",
    "release_regime",
    "render_seats",
    "rule_for",
    "samples",
    "seed",
    "solve",
    "solve_dir",
    "strongest_locations",
    "target_rule",
    "value_of",
    "within",
    "write_record",
]
