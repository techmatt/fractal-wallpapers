"""Choose the gallery by solving for it, instead of walking down a ranked list.

Every gallery this project has shipped was seated **sequentially**: a draw picked
places, a ranked list was walked, and each candidate was tested against what the
seats before it had already accumulated. That is cheap, and it is
order-dependent, and the order-dependence is not a detail — the colour ceiling
was a prefix rule with no recovery, so a picture seated at seat 3 could refuse a
better one at seat 40 and nothing could take the first seat back.

This is the other half of propose-then-solve. [`curation.candidate_ledger`] made
the proposal side durable — one row per recipe, every candidate this project has
ever rendered, with its colour and its place on the row. This module states the
selection as a **mixed-integer program** over that ledger and hands it to HiGHS.
One binary per candidate, the constraints as rows, and the answer is optimal
under them rather than optimal-given-the-order-it-happened-to-walk.

## What the program says

The objective is **lexicographic**: three solves, each freezing the value it
found as a constraint on the next.

1. how many of the seated clear [`Q4_BAR`],
2. the **floor** — the lowest score among the seated, maximized,
3. the **sum**, less the mode-floor penalty.

Ordered that way because the three answer different questions and the first two
are not tradeable against the third. A gallery of twenty where nineteen are
excellent and one is a mistake is worse than one where all twenty are merely
good, and a sum cannot say so: the twentieth picture's deficit is a rounding
error against nineteen scores near one. The floor stage is what makes the worst
seat the thing being maximized.

Hard: cardinality, **one candidate per location**, the diversity radius, the
palette-group cap, and the colour ceiling as a *budget* rather than a prefix
rule. Soft, and only in stage 3: the mode floors — a mode with no candidate at
all would otherwise make the program infeasible, and infeasibility is not the
answer to "nothing has ever been rendered in `itinerary` worth shipping".

## The two pairwise rules are generated, never materialized

The diversity radius and the group cap are both statements about a **pair** of
finished pictures, and the ledger holds fifteen thousand: a hundred and eighteen
million pairs, each costing a 512 KiB pixel-cloud signature to evaluate.

So they are **lazy**. Solve without them, look at the pairs, add a row for each
violated pair, solve again. It terminates on an incumbent that violates nothing,
and what it terminates on is optimal for the whole program and not only for the
rows that were generated: the generated program is a relaxation, so its optimum
bounds the full program's; the incumbent attains that bound and is feasible for
the full program; so it is the full program's optimum too.

## Two prunes, one sound and one not

The design this module replaced was to prune at **location** level — pairs whose
places are far apart cannot be near-duplicate pictures, so only close locations
need their candidates expanded. Measured over 79,621 cross-location pairs drawn
from the pool's top two thousand, that premise is false: 1,350 of them are closer
than 0.07 as pictures, and the furthest-apart pair of *places* that makes
one sits at cosine 0.583, past the 90th percentile of location distance. It is
the expected answer once stated plainly — this metric is over a picture's colour
cloud, and colour comes from the map rather than from the place, so two unrelated
frames through similar ramps are near-duplicates by construction. A prune at 0.40
would still keep 91% of the pairs and miss 96 real violations. **A correlated
proxy is not a prune**, and that one was a correlated proxy.

The metric admits a real one, and the difference is the whole lesson. It is a
mean of absolute differences, so the triangle inequality lower-bounds it from a
summary of each cloud: at the coarsest reading the distance between the two
clouds' **mean colours**, and at finer readings the same statement per band of
the cloud ([`BOUND_BLOCKS`]). A pair the bound puts at or beyond its own
threshold *provably* cannot violate, so it is never measured and never generated.
It settles 98% of pairs at four kibibytes each against the metric's five hundred
and twelve, and what that buys is not only the arithmetic: a round can screen
every pair among **everything a signature has ever been made of** — the greedy
seed's rejects and every earlier incumbent — instead of the incumbent's own pairs
alone, so the rows arrive many rounds before the incumbent would have found them.

The two rules are one test with two thresholds. Two seated pictures must be at
least [`ceiling.TAU`] apart in [`pixel_clouds.METRIC`] — the same distance
[`curation.seating`]'s twin test refuses inside, because it is the same question —
and two seated pictures of one **palette group** at least [`ceiling.TAU_GROUP`]
apart, which is that cap's own exemption distance and the larger of the two.

## Infeasibility is an answer, and it is the useful one

A conditioned hunt needs to know what to look for. So when the program cannot be
solved this does not raise: it solves an **elastic** version — every relaxable
row given a nonnegative slack, minimizing the slack — and reports the slacks as a
shortage list, then runs a deletion filter over the constraint blocks to say
which of them are irreducibly in conflict. "The `dark_vivid_lime` target is
eleven candidates short, and the eleven would have to come from these partitions"
is a work order. `INFEASIBLE` is not.

Under-fill is the same fact one seat smaller. The cardinality row asks for exactly
`n`; when nothing can fill the last seats, [`solve`] re-solves at `<= n` so the
seats that *can* be filled are, and the empty ones are on the record. **No
fallback leg**: nothing is ever seated by relaxing a rule it failed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, ceiling, floors, mode_policy
from fractal_wallpapers.paths import rehome, tracked_name, under

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree a solve's own output lands in, under the regenerable tree.
UNIT = "solve"

#: The bar stage 1 counts against, on **raw** `P(>=4)`.
#:
#: [`floors.RELEASE_ADVISORY`], which is the natural rank cutpoint of a CORN
#: probability and answers "would this head call the picture a fourth-class
#: wallpaper". It is deliberately NOT a measured crossover: no isotonic fit of a
#: human `q4` verdict against this head's fourth cutpoint exists, and the two
#: heights this project has fitted ([`floors.MEASURED_RELEASE_FLOORS`]) are both
#: `P(>=3)` and neither transfers to a different cutpoint.
#:
#: It is recorded on every solve for that reason. When the human-derived
#: crossover lands this height moves, and a count taken against one bar is not
#: comparable to a count taken against the other — so a solve names the bar it
#: counted against rather than leaving a reader to date the file.
Q4_BAR = floors.RELEASE_ADVISORY

#: What the bar is a bar **on**. Spelled out because one head emits three
#: cutpoints and a count says nothing without naming which one it counted.
Q4_BASIS = (
    "raw P(>=4) from the render judge, against the natural rank cutpoint of a CORN "
    "probability. NOT a measured crossover: both release heights this project has fitted "
    "are P(>=3) and neither transfers to the fourth cutpoint. A human-derived q4 "
    "crossover replaces this, and a count taken across the change names its own bar."
)

# The diversity distance this module used to spell `RADIUS = 0.07` is **retired**.
# Every reader of it now reads [`ceiling.TAU`], 0.0586, Matt's, off the twins
# ladder. Two spellings of one fact is a silent null: both were answering "do
# these two read as one wallpaper", so a pair one refused and the other passed was
# a disagreement between two numbers nobody had chosen between. There is one
# number and it is the one somebody set by eye. A caller needing a different
# distance for a different question names the caller and the question rather than
# reviving a second constant.

#: How many seats of a gallery one production mode's floor is worth: **a
#: hundredth**, so the floor is `floor(n / 100)` — 0 at n=20, 1 at 150, 10 at 1000.
#:
#: The flat one-per-mode it replaces asked eighteen of a twenty-seat gallery to be
#: spent on representation, which is not a debug gallery of the strongest pictures
#: but a survey of the modes. It also forced `trap_circle` — 2 clearing locations,
#: the better of them at `P(>=4) = 0.066` — into every gallery this project would
#: ever seat. A floor that scales says what the flat one meant, "this mode is
#: represented at all", at the sizes where representation is affordable, and says
#: nothing at the sizes where it is not.
SEATS_PER_MODE_FLOOR = 100

#: The mode-floor penalty, **per seat of the gallery**: `lambda = n * this`.
#:
#: A hundredth of a seat, so at `n=20` a missing mode costs 0.2 of objective —
#: heavy against the sum it comes off, because that sum is over scores that
#: saturate. The pool's top two hundred candidates sit between 0.998 and 1.000, so
#: swapping a seat to cover a mode costs thousandths and buys 0.2. It scales with
#: `n` because the sum does.
PENALTY_PER_SEAT = 1.0 / 100.0


def mode_floor(n: int) -> int:
    """The **flat** floor: how many seats every accepted mode is asked for, at `n`.

    **It is no longer the default.** [`curation.mode_policy.seat_floors`] is, per
    mode, since 2026-08-31; this is what `--flat-floor` puts back and what every
    gallery seated or solved before that date was seated or solved under, so it
    stays here as the baseline a floored-against-unfloored reading is taken
    against rather than as a rule anything reaches by not naming one.

    `floor(n / SEATS_PER_MODE_FLOOR)`, by integer division rather than a float
    times a rate, so the value at a rung is the value every reader computes.
    **Zero is a real answer**: below a hundred seats no mode is mandated at all,
    and a seating there is the strongest pictures the pool holds rather than a
    survey of the roster.

    Which modes it is asked *of* is [`curation.mode_policy.accepted`] and not the
    engine's production roster: a mode weighted 0 has no rows in the pool at all
    ([`pool`]), so a floor over it would be a mandate nothing could ever meet.
    """
    return int(n) // SEATS_PER_MODE_FLOOR


#: How many candidates the greedy seed walks, as a multiple of `n`.
#:
#: **Four.** The walk costs one pixel-cloud signature per candidate that clears
#: the two arithmetic tests, and the ones it clears are the pool's strongest — so
#: a walk that ran the whole ledger would spend fifteen thousand signatures to
#: seat a few hundred. Four `n` is where it stops looking; measured on the pool it
#: fills every seat well inside that, and a walk that does not is reported as
#: having filled what it could and keeps its cuts anyway.
SEED_REACH = 4

#: How many cutting-plane rounds before the loop gives up and says so.
#:
#: A backstop and not an operating parameter, but "a handful" was too small a
#: word for it: measured on the pool the loop takes 2 rounds at n=20, 3 at 40, 8
#: at 60, 7 at 80 and **18 at 120**, because a larger incumbent lands on more
#: near-duplicate pairs and each round removes only the ones it landed on. Sixty
#: is a stop, and a loop that reaches it is reporting a fact about the pool.
ROUNDS = 60

#: How long [`sweep`] may spend on the whole ladder, in seconds.
#:
#: A round cap bounds **rounds** and not time, and the two are not the same thing:
#: the rounds grow with `n`, and so does the pool of pairs each of them screens.
#: The ladder is still superlinear — measured on the pool at 5.0 s for n=20, 10.3
#: at 40, 37.6 at 60, 38.6 at 80 and 151.6 at 120 — it is just a great deal
#: shallower than the 19/31/125/131 it was before the bound and the column fix.
#:
#: So the ladder carries a clock, it stops on it, and the record says which rung
#: it stopped at and why. Twenty minutes, which is a coffee rather than an
#: afternoon; a caller who wants the whole ladder passes its own.
SWEEP_SECONDS = 20 * 60

#: Below this a solver's answer is read as zero. HiGHS returns 1e-11 for an
#: integer variable it decided is off.
EPSILON = 1e-6

#: How much of one seat stage 1 is allowed to break its own ties by.
#:
#: Stage 1 counts a 0/1 attribute over fifteen thousand columns, so its optimum
#: is enormously degenerate — 1,438 candidates clear the bar and any twenty of
#: them score the same — and branch-and-bound spends its whole time deciding
#: between answers that are equal. Adding `(this / n) * score` to each column
#: orders those ties by the score they would be ranked on anyway.
#:
#: It cannot move the count, which is the only thing stage 1 hands on. Every
#: score is a probability, so the bonus over `n` seats is at most `this`, and at
#: **a half** that is strictly less than the one whole seat a different count
#: differs by. Measured on the pool at n=20: 21.0 s to 1.3 s, same answer.
TIE_BREAK = 0.5

#: How many signatures [`Pairs`] holds before it forgets the oldest. 512 of them
#: is a quarter of a gibibyte, which is what an incumbent of a few hundred costs.
SIGNATURE_CACHE = 512

#: How many blocks of the metric's quantiles [`Pairs`]'s lower bound reads.
#:
#: **Four.** The bound is the triangle inequality applied per direction and per
#: block of quantiles — the mean of `|a - b|` is at least `|mean a - mean b|` —
#: so one block is the distance between the two clouds' mean colours, and
#: [`pixel_clouds.QUANTILES`] blocks is the metric itself. Every setting in
#: between is sound; the question is only how much it settles.
#:
#: Measured over 79,800 pairs drawn from the pool's top two thousand, at the
#: retired 0.07: one block settles 95.4% of pairs and leaves 2.7 survivors per real
#: violation, two settles 97.4% and leaves 1.6, four settles 97.9% and leaves 1.2,
#: sixteen settles 98.3% and leaves 1.0. Four is where the curve flattens, and it
#: is a sixteen-kibibyte signature against the metric's five hundred and twelve.
BOUND_BLOCKS = 4

#: What the bound is, carried in every record that prunes by it. A prune is only
#: as good as its soundness argument, and this project has shipped a prune whose
#: premise was false — see the module docstring on the location-level one.
BOUND = (
    "a sound lower bound on the pixel-cloud metric: the sorted projections are "
    f"grouped into {BOUND_BLOCKS} blocks of quantiles, and per direction and per block "
    "the mean of |a - b| is at least |mean a - mean b|. At one block that is the "
    "distance between the two clouds' mean colours. A pair the bound puts at or beyond "
    "its own threshold provably cannot violate, so it is never measured and never "
    "generated as a row."
)


def reduce_signature(made):
    """One full signature as its `[BOUND_BLOCKS, DIRECTIONS]` block means.

    The signature is `[QUANTILES, DIRECTIONS]` flattened, and the bound reads it
    as `BOUND_BLOCKS` contiguous groups of quantiles averaged down. Contiguous
    because the projections were sorted before they were read: a block of adjacent
    quantiles is a band of the cloud, and the bound is the triangle inequality
    over the bands.
    """
    import numpy

    from fractal_wallpapers.palettes import groups

    grid = numpy.asarray(made, dtype=numpy.float32).reshape(groups.QUANTILES, groups.DIRECTIONS)
    return grid.reshape(BOUND_BLOCKS, groups.QUANTILES // BOUND_BLOCKS, groups.DIRECTIONS).mean(
        axis=1
    )


#: What a near miss is: how many of the strongest unseated candidates the contact
#: sheet shows beside the gallery, with the rule that refused each one named.
NEAR_MISSES = 12


class SolveRefused(RuntimeError):
    """The program cannot be built, or the solver is not installed."""


def _scipy():
    """SciPy, or a refusal that says how to get it.

    The base install is deliberately thin, and this is the one leg that needs a
    MILP solver. Refused here rather than at an `ImportError` deep in a stage, so
    the message can name the extra.
    """
    try:
        import scipy  # noqa: F401
        from scipy.optimize import milp  # noqa: F401
    except ImportError as refusal:  # pragma: no cover - the message is the point
        raise SolveRefused(
            "solving the gallery needs SciPy's HiGHS binding, which the base install does "
            "not carry. `pip install -e .[solve]`, or `uv pip install scipy`."
        ) from refusal


# --------------------------------------------------------------------------- #
# The pool.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Candidate:
    """One ledger row, thinned to what a constraint or the objective reads.

    Everything here is off the row. The solve renders nothing and opens no
    picture until the cutting-plane loop asks one candidate for its pixel cloud.
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
    """`(candidates, what was refused)` — everything the solve may seat.

    Five exclusions, each a fact about the candidate rather than a quality bar. A
    row in a mode [`curation.mode_policy`] weights **0** is refused: the standing
    is that this project has stopped buying that mode, and a gallery is the last
    place it would be spent — its labels, its ledger rows and its pictures all
    stand, and it renders by name. A row a **person rejected** is refused: the
    ledger keeps it and carries the rejection precisely so that a solver honours
    it. A row at a regime other than the one the pool was made at is refused,
    because a score read at one geometry does not transfer to another. A row with
    **no picture on disk** is refused —
    its recipe is complete and it could be drawn again, but the diversity rule and
    the group cap are read off pixels, and a candidate no pairwise rule can
    evaluate is one that would be seated untested. A row with no score is refused
    because the objective *is* the score: such a row does not lose, there is
    simply nothing to rank it by.

    **Naming a picture and having one are two questions, and this asks both.**
    Until 2026-08-28 it asked only the first, and the gap is not small: `curate
    retention` drops the picture of everything outside the top five per (location,
    mode), which at this store is **30,040 of 128,368 rows (23.4%)**. All of them
    were admitted, and the twin rule — the one rule that opens a picture — could
    not read them and so *admitted* them too. Rows the diversity rule could not
    evaluate were exactly the rows it stopped applying to. Measured: re-seating
    `p2b_n150` on the same pool, the same bars and bit-identical scores reproduced
    147 of its 150 seats, and the three it took instead were three the record had
    refused as twins whose files had since gone — seated *because* their pictures
    were missing.

    The two are counted apart, `no_picture` against `picture_absent`, because they
    are different facts about a row: one was never drawn, the other was drawn and
    swept. Only the second is expected to grow.
    """
    stored = candidate_ledger.stream() if rows is None else rows
    read = candidate_ledger.read_scores() if scores is None else list(scores)
    # On the LIVE judge only, for [`candidate_ledger.scores_by_recipe`]'s reason:
    # the sidecar is keyed on the artifact and a flattened join would put two
    # judges' scales into one objective. A recipe read on an older artifact falls
    # into `no_score` below, which is where a recipe with no reading belongs.
    by_key = candidate_ledger.scores_by_recipe(read, artifact=artifact)
    refused = {
        "niche_mode": 0,
        "rejected": 0,
        "off_regime": 0,
        "no_picture": 0,
        "picture_absent": 0,
        "no_score": 0,
    }
    # The four refusals that read the row alone are taken in the stream, so the
    # only rows that survive into memory are the ones that could still be seated
    # — a projection of eleven fields, not the row. The two that need another
    # store come after, in the order they were always in: a row can be both
    # picture-absent and unscored, and which counter it lands in is a number this
    # has reported since it was written.
    seen = 0
    projected: list[dict] = []
    for row in stored:
        seen += 1
        recipe = row.get("recipe") or {}
        # The mode this candidate COUNTS as, which is the mode it was rendered in
        # unless its texture said nothing — see [`mode_policy.routed_mode`]. It is
        # taken here, before the roster is asked, because a row whose picture is
        # the smooth field spent by rank is a smooth picture on both questions:
        # whether the mode may be seated at all, and which pile it is seated in.
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
                # Everything downstream of the pool reads a candidate's mode off
                # here: the per-mode bars, the mode floors, the census of what was
                # seated. A caller wanting the mode that was *asked for* reads the
                # ledger row's own recipe, which is untouched.
                "mode": mode,
                "group": str(recipe.get("palette_group")),
                "cells": tuple(colour.get("cells") or ()),
                "families": tuple(colour.get("families") or ()),
            }
        )
    if not seen:
        raise SolveRefused(
            "the candidate ledger is empty, so there is nothing to solve over. Run "
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


def picture_of(candidate: Candidate) -> Path:
    """Where one candidate's 640x360 render is on this machine."""
    return Path(rehome(candidate.picture))


def by_location(candidates: list[Candidate]) -> dict:
    """`{location key: [indices into `candidates`]}`, in the order they arrived."""
    out: dict = {}
    for at, candidate in enumerate(candidates):
        out.setdefault(candidate.location, []).append(at)
    return out


def strongest_locations(candidates: list[Candidate], keep: int | None) -> list[str]:
    """The `keep` strongest locations by their best candidate. `None` keeps all.

    The truncation experiment's knob. Hard optimization against a learned score
    selects that score's upper tail, which is where a judge's false positives
    live; restricting what the program may reach is the one lever on that which
    costs nothing to try. It acts on **locations** and not on candidates because
    a gallery is a set of places.
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
# The pairwise rules, generated on demand.
# --------------------------------------------------------------------------- #
class Pairs:
    """The pixel-cloud distances the cutting-plane loop has had to measure.

    Signatures are half a mebibyte each and a tenth of a second to make, and the
    loop asks for `n^2/2` distances a round, so this holds three things and holds
    them differently: the **exact distances** forever, because they are one float
    and a later round asks for the same pair again; the **signatures** under a
    bound, because an incumbent of a few hundred is a few hundred megabytes; and
    the **bound signatures** forever, because they are a few kibibytes and they
    are what stops most pairs from ever needing the other two.

    ## The bound

    [`pixel_clouds.METRIC`] is a mean of absolute differences over
    `DIRECTIONS * QUANTILES` numbers, so the triangle inequality gives a lower
    bound on it for nothing: group the quantiles into [`BOUND_BLOCKS`] blocks, and
    per direction and per block the mean of `|a - b|` is at least
    `|mean a - mean b|`. At one block that is exactly the distance between the two
    clouds' **mean colours**; at more blocks it is the same statement read at
    finer resolution, and at `QUANTILES` blocks it is the metric itself.

    It is a *sound* bound and not a correlated proxy, which is the whole
    difference from the location-level prune this module's docstring buries: a
    pair the bound puts at or beyond its own threshold **cannot** violate, so it
    never needs a signature and never needs generating. Measured over 79,800 pairs
    drawn from the pool's top two thousand, it recovers 99.0% of the distance at
    the median and settles 97.9% of pairs at that distance, leaving 1.2 survivors per
    real violation. At one block it recovers 95.5% and settles 95.4%.
    """

    def __init__(self, candidates: list[Candidate], cache: int = SIGNATURE_CACHE):
        self.candidates = candidates
        #: How many full signatures are held. It is no longer tied to the size of
        #: an incumbent: a round used to compare every seat with every other in
        #: the full metric, so a cache that forgot one mid-round remade it for the
        #: next seat that asked. The bound does that comparison now, at a fraction
        #: of the bytes, and only the survivors are measured -- so what the cache
        #: has to hold is a round's survivors and not its seats.
        self.cache = max(1, int(cache))
        self._signatures: dict = {}
        self._order: list = []
        #: The bound signature of every candidate ever looked at, kept for good.
        self._reduced: dict = {}
        self._distance: dict = {}
        #: `{pair: its lower bound}` for the pairs the bound settled. Kept apart
        #: from the exact distances so nothing reports a bound as a measurement:
        #: the contact sheet's nearest-pair table is the radius's calibration
        #: instrument, and a bound in it would calibrate against the wrong number.
        self._lower: dict = {}
        self.made = 0
        self.measured = 0
        self.settled = 0
        self.screened = 0
        self.seconds = 0.0

    def signature(self, at: int):
        if at in self._signatures:
            return self._signatures[at]
        from fractal_wallpapers.palettes import pixel_clouds

        started = time.monotonic()
        made = pixel_clouds.of_picture(picture_of(self.candidates[at]))
        self.seconds += time.monotonic() - started
        self.made += 1
        self._reduced.setdefault(at, reduce_signature(made))
        self._signatures[at] = made
        self._order.append(at)
        while len(self._order) > self.cache:
            self._signatures.pop(self._order.pop(0), None)
        return made

    def reduced(self, at: int):
        """This candidate's bound signature, `[BOUND_BLOCKS, DIRECTIONS]`.

        Made from the full signature, because the block means are means of the
        **sorted** projections and there is no cheaper way to those than sorting
        them. So the bound saves nothing on the making of a signature and
        everything on the keeping of one and on the arithmetic between two.
        """
        if at not in self._reduced:
            self.signature(at)
        return self._reduced[at]

    def bounds(self, one: int, others: list) -> list:
        """A sound lower bound on the distance from `one` to each of `others`."""
        return self.bounds_against(self.reduced(one), [self.reduced(other) for other in others])

    def bounds_against(self, mine, stack) -> list:
        """The same, given the bound signatures already stacked. The screen calls
        it this way: a whole round is one stack walked with **views**, and
        re-stacking per row is the copy the seam above this exists to avoid."""
        import numpy

        from fractal_wallpapers.palettes import groups

        if len(stack) == 0:
            return []
        self.screened += len(stack)
        return [
            float(value)
            for value in numpy.abs(numpy.asarray(stack) - mine).sum(
                axis=(1, 2), dtype=numpy.float64
            )
            / (groups.DIRECTIONS * BOUND_BLOCKS)
        ]

    def known(self, one: int, other: int) -> float:
        """The best lower bound this holds on a pair: its distance if it was
        measured, its bound if it was screened, and zero if neither -- which is
        still a lower bound, and is what a test's lookup table leaves behind."""
        pair = (min(one, other), max(one, other))
        if pair in self._distance:
            return self._distance[pair]
        return self._lower.get(pair, 0.0)

    def distance(self, one: int, other: int) -> float:
        """One pair, measured exactly if it has not been. Through [`measure`], so
        there is one place a distance is made and one seam a caller can replace.

        A pair the bound **settled** is measured here too, which is the whole
        reason `screen` is a parameter: settled means *proven to clear its rule*
        and not *known to be this far apart*, so a caller that asked for the
        number is asking for something the screen never produced.
        """
        pair = (min(one, other), max(one, other))
        if pair not in self._distance:
            self.measure(list(pair), screen=False)
        return self._distance[pair]

    def rule_for(self, one: int, other: int) -> tuple[str, float]:
        """`(which rule, how far apart this pair has to be)`.

        [`ceiling.TAU`] for any two seated pictures; [`ceiling.TAU_GROUP`] where
        they are two pictures of one palette group, which is that cap's own
        exemption distance and the larger of the two. One test, so a pair is
        measured once whichever rule ends up naming it.
        """
        if self.candidates[one].group == self.candidates[other].group:
            return "group_cap", max(ceiling.TAU, ceiling.TAU_GROUP)
        return "diversity", ceiling.TAU

    def measure(self, order: list[int], screen: bool = True) -> None:
        """Decide every undecided pair of `order`. **The seam**, and one call.

        Decided is measured *or* settled: with `screen` on, a pair the bound puts
        at or beyond its own threshold is recorded as settled and never measured,
        because it provably cannot violate. Off, every pair is measured exactly,
        which is what [`distance`] asks for -- a caller asking for a number wants
        the number and not a bound on it.

        A whole sweep rather than a pair at a time, because the cost of this was
        never the arithmetic: it was moving half a mebibyte per signature through
        memory. The screen stacks a few kibibytes a seat instead of five hundred
        and twelve, and only the pairs it cannot settle are stacked in full.

        It is one method for a second reason. The suite replaces it with a lookup,
        so a test about which rule refuses a pair does not have to put two
        pictures on disk to make the pair.
        """
        import numpy

        from fractal_wallpapers.palettes import pixel_clouds

        # Stacked once, walked with views. The bound signature is small, but a
        # round screens every pair among everything a signature has been made of,
        # so a re-stack per row is quadratic in the stack rather than in a row.
        reduced = numpy.stack([self.reduced(at) for at in order]) if screen else None
        for at, one in enumerate(order):
            tail = order[at + 1 :]
            wanted = [
                (which, other)
                for which, other in enumerate(tail)
                if not (self.decided(one, other) if screen else self.measured_pair(one, other))
            ]
            if not wanted:
                continue
            if screen:
                rows = (
                    reduced[at + 1 :]
                    if len(wanted) == len(tail)
                    else reduced[[at + 1 + which for which, _other in wanted]]
                )
                keep = []
                for (which, other), bound in zip(
                    wanted, self.bounds_against(reduced[at], rows), strict=True
                ):
                    if bound >= self.rule_for(one, other)[1]:
                        self._lower[(min(one, other), max(one, other))] = float(bound)
                        self.settled += 1
                    else:
                        keep.append((which, other))
                wanted = keep
            if not wanted:
                continue
            survivors = [other for _which, other in wanted]
            mine = self.signature(one)
            others = numpy.stack([self.signature(other) for other in survivors])
            for other, gap in zip(survivors, pixel_clouds.distances(mine, others), strict=True):
                self._distance[(min(one, other), max(one, other))] = float(gap)
                self.measured += 1

    def decided(self, one: int, other: int) -> bool:
        """Whether this pair has been measured or settled by the bound."""
        return self.measured_pair(one, other) or (min(one, other), max(one, other)) in self._lower

    def measured_pair(self, one: int, other: int) -> bool:
        """Whether this pair has an exact distance, which is a stronger thing."""
        return (min(one, other), max(one, other)) in self._distance

    def violates(self, one: int, other: int) -> bool:
        """Whether these two are too close for the rule that governs them.

        Deciding it if it is undecided, and reading a settled pair as clearing:
        the bound only ever settles a pair by proving it at or beyond its own
        threshold, so there is no third answer to give.
        """
        self.measure([one, other])
        gap = self._distance.get((min(one, other), max(one, other)))
        return gap is not None and gap < self.rule_for(one, other)[1]

    def violations(self, chosen: list[int]) -> list[dict]:
        """Every pair of `chosen` that is too close, nearest first.

        The whole cost of a cutting-plane round, and the bound is why it stopped
        being quadratic in half a mebibyte: a pair the bound settled is known to
        clear its own rule, and is never looked at again.
        """
        order = list(chosen)
        self.measure(order)
        out = []
        for at, one in enumerate(order):
            for other in order[at + 1 :]:
                gap = self._distance.get((min(one, other), max(one, other)))
                if gap is None:
                    continue
                rule, bound = self.rule_for(one, other)
                if gap < bound:
                    out.append(
                        {
                            "a": self.candidates[one].key,
                            "b": self.candidates[other].key,
                            "distance": round(gap, 6),
                            "wanted": bound,
                            "rule": rule,
                            "pair": (min(one, other), max(one, other)),
                        }
                    )
        out.sort(key=lambda pair: pair["distance"])
        return out

    def closest(self, wanted: list, count: int) -> list[tuple]:
        """`[(pair, distance)]` -- the `count` nearest of `wanted`, exactly.

        Walked in the order of what is already **known**, which is a lower bound
        on every pair, and measured down that order until the next pair's bound is
        at or past the worst distance kept. From there nothing unmeasured can be
        nearer, so the answer is exact over a set most of which is never measured.
        """
        ranked = sorted(wanted, key=lambda pair: self.known(*pair))
        kept: list = []
        for pair in ranked:
            if len(kept) >= int(count) and self.known(*pair) >= kept[-1][1]:
                break
            kept.append((pair, self.distance(*pair)))
            kept.sort(key=lambda row: row[1])
            del kept[int(count) :]
        return kept

    def nearest_to(self, one: int, others: list) -> float | None:
        """How far `one` is from the nearest of `others`, exactly. `None` if none."""
        if not others:
            return None
        self.measure([one, *others])
        return self.closest([(min(one, other), max(one, other)) for other in others], 1)[0][1]

    def nearest(self, chosen: list[int], pairs: int = 10) -> list[dict]:
        """The closest pairs among `chosen`, whether or not any rule refuses them.

        THE calibration instrument: if two of these read as one picture, the
        radius is too small. Exact distances and
        never bounds, for that reason -- a threshold read off a lower bound is a
        threshold read too low.
        """
        order = list(chosen)
        self.measure(order)
        wanted = [
            (min(one, other), max(one, other))
            for at, one in enumerate(order)
            for other in order[at + 1 :]
        ]
        return [
            {
                "a": self.candidates[one].key,
                "b": self.candidates[other].key,
                "distance": round(gap, 6),
                "same_group": self.candidates[one].group == self.candidates[other].group,
            }
            for (one, other), gap in self.closest(wanted, int(pairs))
        ]

    def paid(self) -> list[int]:
        """Every candidate whose signature has been made. What a round screens.

        A cutting-plane round has always looked at the incumbent's own pairs,
        because looking wider meant a signature per candidate and the signature is
        the whole bill. The bound changed the second half of that and not the
        first: a pair of candidates *already paid for* costs the screen and
        nothing else, so a round can ask about every pair among everything it has
        ever made a signature of — the seed's rejects, and every earlier
        incumbent — and pay only for the pairs the bound cannot settle.
        """
        return sorted(self._reduced)

    def price(self) -> dict:
        from fractal_wallpapers.palettes import pixel_clouds

        decided = self.settled + self.measured
        return {
            "signatures_made": self.made,
            "pairs_measured": self.measured,
            "pairs_screened": self.screened,
            "pairs_settled_by_the_bound": self.settled,
            "settled_share": round(self.settled / decided, 4) if decided else None,
            "seconds_making_signatures": round(self.seconds, 1),
            "cache": self.cache,
            "bound_blocks": BOUND_BLOCKS,
            "bound": BOUND,
            "metric": pixel_clouds.METRIC,
        }


# --------------------------------------------------------------------------- #
# The program.
# --------------------------------------------------------------------------- #
#: What a slack on a block would mean. `over` is a row that can only exceed its
#: bound (a cap), `under` one that can only fall short of it (a demand), `exact`
#: the cardinality equality, which can do both and is read for the under side.
OVER, UNDER, EXACT = "over", "under", "exact"


@dataclass
class Program:
    """The rows of one solve, and what is needed to name them again afterwards.

    Built once per `(pool, n, targets)` and handed cuts as the loop finds them. It
    carries its constraints as named **blocks** because two readers want them by
    name rather than by row index: the elastic solve, which gives each block its
    own slack, and the deletion filter, which removes them a block at a time.
    """

    candidates: list[Candidate]
    n: int
    rule: ceiling.Rule
    modes: tuple
    #: `{cell: the fraction of the seats a target demands}`. Empty on an ordinary
    #: solve; the infeasibility demonstration is what sets it.
    targets: dict = field(default_factory=dict)
    #: `[(i, j)]` — every pair the cutting-plane loop has ruled out.
    cuts: list = field(default_factory=list)
    #: The violations behind those cuts, kept for the record.
    generated: list = field(default_factory=list)
    #: Whether cardinality is `== n` or `<= n`. The under-fill re-solve sets it.
    exact_cardinality: bool = True
    #: A floor **replacing the default**, which is
    #: [`curation.mode_policy.seat_floors`] — per mode, and what an unflagged
    #: `curate solve` is now solved under. A **mapping** is some other caller's
    #: per-mode floors; a **number** is one floor for every mode, which is both
    #: [`mode_floor`]'s flat `floor(n / 100)` (what `--flat-floor` asks for, and
    #: what every solve before 2026-08-31 ran under) and the artificial floor a
    #: unit-sized program needs to exercise stage 3's rows at all.
    #:
    #: The mapping shape is what lets the exact solver and [`curation.seating`]'s
    #: greedy be asked the same question, which is the only way either one checks
    #: the other.
    floor: int | dict | None = None

    @property
    def mode_floors(self) -> dict:
        """`{mode: how many seats its floor asks for}` in this program.

        Unset is the default rule, [`curation.mode_policy.seat_floors`], which is
        per mode; a number is the same floor for every mode. A mode a mapping does
        not name asks for nothing — the smooth side is every such mode under the
        default, because the floors are the strange side's distribution problem
        and the smooth side is one mode.
        """
        asked = mode_policy.seat_floors(self.n) if self.floor is None else self.floor
        if isinstance(asked, dict):
            return {name: max(0, int(asked.get(name, 0))) for name in self.modes}
        return {name: max(0, int(asked)) for name in self.modes}

    @property
    def mode_floor_rule(self) -> str:
        """One sentence naming where this program's floors came from.

        The default, the flat floor it replaced, or a caller's own — three
        answers that a record calling all of them `floor(n / 100)` could not tell
        apart, which is exactly what a floored-against-unfloored measurement asks
        of the record.
        """
        if self.floor is None:
            return (
                "the per-mode floor rule, curation.mode_policy.seat_floors(n): half each "
                "accepted strange mode's share of the strange seat budget. THE DEFAULT"
            )
        if isinstance(self.floor, dict):
            return "set per mode by the caller"
        if int(self.floor) == mode_floor(self.n):
            return (
                f"the FLAT floor, floor(n / {SEATS_PER_MODE_FLOOR}) = {int(self.floor)} for "
                "every mode. The default until the per-mode rule replaced it, and what "
                "`--flat-floor` asks for"
            )
        return f"an artificial flat {int(self.floor)} for every mode"

    @property
    def target_rule(self) -> str:
        """One sentence naming what a `--target t` asks of this program.

        The two spellings are not interchangeable and a record that called both
        of them "the target" could not say which one ran — see [`_target_row`].
        """
        if self.exact_cardinality:
            return "ceil(t * n) seats, a hard count against the n the cardinality row fixes"
        return (
            "t * the REALIZED seat count: sum(cell) >= t * sum(all), as "
            "(1 - t) * sum(cell) - t * sum(rest) >= 0. A share of the gallery that gets "
            "filled, because `<= n` no longer promises n of them"
        )

    @property
    def mode_floor(self) -> int:
        """The floor every mode asks for, where they all ask for the same thing.

        The **largest** floor asked otherwise, because that is what the deficit
        columns have to be bounded by and a smaller number would make the rows
        infeasible rather than soft. A reader wanting the rule as it was applied
        takes [`mode_floors`].
        """
        return max(self.mode_floors.values(), default=0)

    def __post_init__(self) -> None:
        self.locations = by_location(self.candidates)
        self.cell_members: dict = {}
        self.family_members: dict = {}
        self.mode_members: dict = {name: [] for name in self.modes}
        for at, candidate in enumerate(self.candidates):
            for cell in candidate.cells:
                self.cell_members.setdefault(cell, []).append(at)
            for family in candidate.families:
                self.family_members.setdefault(family, []).append(at)
            if candidate.mode in self.mode_members:
                self.mode_members[candidate.mode].append(at)

    @property
    def size(self) -> int:
        """How many binaries: one per candidate, and nothing else is integral."""
        return len(self.candidates)

    def blocks(self) -> list[tuple[str, str, list]]:
        """`[(name, kind, [(members, bound, what the row is about)])]`.

        `members` is a list of column indices, every coefficient one — which is
        every row here but the relaxed colour target, the one row that has to
        weight its columns. That row states `[(column, coefficient)]` instead and
        both readers go through [`members_of`]; see [`_target_row`].
        """
        out = [
            (
                "cardinality",
                EXACT if self.exact_cardinality else OVER,
                [(list(range(self.size)), self.n, f"{self.n} seats")],
            ),
            (
                "one_per_location",
                OVER,
                [
                    (members, 1, name)
                    for name, members in self.locations.items()
                    if len(members) > 1
                ],
            ),
            (
                "colour_ceiling_cells",
                OVER,
                [
                    (members, self.rule.allowed(cell, self.n), cell)
                    for cell, members in sorted(self.cell_members.items())
                ],
            ),
            (
                "colour_ceiling_families",
                OVER,
                [
                    (members, self.rule.allowed(family, self.n), family)
                    for family, members in sorted(self.family_members.items())
                ],
            ),
        ]
        if self.cuts:
            out.append(
                (
                    "pairwise",
                    OVER,
                    [
                        (
                            [one, other],
                            1,
                            f"{self.candidates[one].key}|{self.candidates[other].key}",
                        )
                        for one, other in self.cuts
                    ],
                )
            )
        if self.targets:
            out.append(
                ("colour_target", UNDER, [self._target_row(cell) for cell in sorted(self.targets)])
            )
        return out

    def _target_row(self, cell: str) -> tuple[list, float, str]:
        """One target's row, spelled for the cardinality this program is under.

        Under `== n` the seat count is known, so a target of `t` is the hard count
        [`ceiling.Rule.wanted`] gives: `ceil(t * n)` seats dominant in the cell.

        Under `<= n` it cannot be, and a hard count there is not a stricter
        reading of the target but a wrong one: it demands a share of seats the
        program is no longer promising to fill, so the re-solve is infeasible at
        every size below `n` and an under-fill under a target reports nothing at
        all. What a target means is a share of the gallery, so under `<= n` it is
        a share of the **realized** seat count:

            sum(cell) >= t * sum(all)   ->   (1 - t) * sum(cell) - t * sum(rest) >= 0

        which is linear, is the same row as `ceil(t * n)` wherever the seats do
        come to `n`, and is the same demand at every smaller size the pool can
        actually fill. It is the one row here that weights its columns.
        """
        members = self.cell_members.get(cell, [])
        if self.exact_cardinality:
            return (members, self.rule.wanted(cell, self.n), cell)
        share = float(self.targets[cell])
        inside = set(members)
        weighted = [(at, (1.0 - share) if at in inside else -share) for at in range(self.size)]
        return (weighted, 0.0, cell)

    def _untargeted(self) -> tuple[str, str]:
        """A cell and a family no target has moved, so the record can state the
        **default** allowance through [`ceiling.Rule.allowed`] rather than as a
        second copy of its arithmetic. A target raises the allowance of the cell it
        names, of that cell's family, and of the cells its carriers *also* deliver,
        so reading any of those would report the exception as the rule."""
        from fractal_wallpapers.palettes import dominance

        moved = (
            {dominance.family_of(cell) for cell in self.targets}
            | set(self.targets)
            | set(self.rule.implied)
        )
        cell = next(name for name in dominance.cells() if name not in moved)
        family = next(name for name in dominance.families() if name not in moved)
        return cell, family

    def config(self) -> dict:
        """Every constant this program stands on, for the record it writes."""
        return {
            "n": self.n,
            "candidates": self.size,
            "locations": len(self.locations),
            "cardinality": "== n" if self.exact_cardinality else "<= n",
            "target_rule": self.target_rule,
            "objective": [
                f"1. count of seats with raw P(>=4) >= {Q4_BAR}",
                "2. the minimum score among the seated, maximized",
                f"3. the sum of the seated scores, less {PENALTY_PER_SEAT} * n per "
                f"accepted mode below its own floor",
            ],
            "q4_bar": Q4_BAR,
            "q4_basis": Q4_BASIS,
            "radius": ceiling.TAU,
            "radius_from": "ceiling.TAU. `solve.RADIUS` is retired: one distance, one name",
            "tau_group": ceiling.TAU_GROUP,
            "mode_floor": self.mode_floor,
            "mode_floors": self.mode_floors,
            "mode_floor_rule": self.mode_floor_rule,
            "mode_floor_artificial": self.floor is not None,
            "mode_penalty": round(self.n * PENALTY_PER_SEAT, 6),
            "modes": list(self.modes),
            "ceiling": {
                "k": self.rule.k,
                "cell_allowance": self.rule.allowed(self._untargeted()[0], self.n),
                "family_allowance": self.rule.allowed(self._untargeted()[1], self.n),
                "allowance": "floor(k * t * n) + 1",
                "targets": dict(sorted(self.targets.items())),
                "targeted_allowance": {
                    cell: self.rule.allowed(cell, self.n) for cell in sorted(self.targets)
                },
                # What the target *implied*, beside what it asked for. A carrier
                # of one cell is dominant in others, and those are the rows the
                # lime hunt's shortage moved onto once the target itself was met.
                "implied": {
                    name: round(share, 6) for name, share in sorted(self.rule.implied.items())
                },
                "implied_allowance": {
                    name: self.rule.allowed(name, self.n) for name in sorted(self.rule.implied)
                },
                "implied_from": (
                    "the carrier table's measured co-dominance: of the (map, field) "
                    "deliveries where a targeted cell is dominant, the share that are "
                    "also dominant in the companion. A target of t raises a companion's "
                    "share by t * that rate, and the companion's family by the same "
                    "unless it is the target's own family, which the target already "
                    "raised and which counts a picture once."
                ),
            },
            "pairwise_rule": (
                f"two seated pictures of one palette group must be "
                f"{max(ceiling.TAU, ceiling.TAU_GROUP)} apart in the pixel-cloud metric and "
                f"any other two {ceiling.TAU} — solve.Pairs.rule_for, generated one row per "
                f"violating pair as the cutting plane finds it. There is NO per-group count "
                f"in this program and no flag that raises or lowers one"
            ),
        }


def members_of(members):
    """`(column, coefficient)` for one block row's members.

    A member is a plain column where its coefficient is one, which is every row a
    program states but the relaxed colour target — see [`Program._target_row`].
    Both readers of a row go through here, so a weighted row cannot be counted as
    an unweighted one by whichever of them was written first.
    """
    for member in members:
        if isinstance(member, tuple):
            yield int(member[0]), float(member[1])
        else:
            yield int(member), 1.0


def matrices(program: Program, skip=None):
    """The blocks as one sparse `A` with `lower` and `upper`, plus the row index.

    The index is `[(block name, what the row is about, kind)]` in row order, so a
    slack or a dual can be named without rebuilding anything.
    """
    import numpy
    from scipy import sparse

    skip = set(skip or ())
    rows, columns, weights, lower, upper, index = [], [], [], [], [], []
    at = 0
    for name, kind, block in program.blocks():
        if name in skip:
            continue
        for members, bound, about in block:
            for column, weight in members_of(members):
                rows.append(at)
                columns.append(column)
                weights.append(weight)
            if kind == EXACT:
                lower.append(float(bound))
                upper.append(float(bound))
            elif kind == UNDER:
                lower.append(float(bound))
                upper.append(numpy.inf)
            else:
                lower.append(-numpy.inf)
                upper.append(float(bound))
            index.append((name, about, kind))
            at += 1
    matrix = sparse.csr_array(
        (numpy.array(weights, dtype=numpy.float64), (rows, columns)),
        shape=(at, program.size),
    )
    return matrix, numpy.array(lower), numpy.array(upper), index


# --------------------------------------------------------------------------- #
# The three stages.
# --------------------------------------------------------------------------- #
def lexicographic(program: Program, seed: dict | None = None, log=print) -> dict:
    """The three stages, each frozen into the next.

    One column layout throughout — the binaries, then `t`, then one deficit per
    production mode — so the three matrices are the same matrix with rows added.

    Stage 2 wants the **minimum score among the seated**, which is not a linear
    function of the binaries, so it is one continuous `t` and one row per
    candidate: `x_i + t <= score_i + 1`. The big-M is exactly one because every
    score is a probability — an unseated candidate's row reads `t <= score + 1`,
    which cannot bind on a `t` already bounded above by one.

    Stage 3 adds `sum(x in mode m) + d_m >= floor_m` and pays `n *
    PENALTY_PER_SEAT` for each unit of `d`. Those rows exist only in this stage:
    the first two ask questions the penalty is not allowed to trade against —
    which is also the limit of what the floor can buy. A floor that would cost a
    point of the worst seated score is a floor this objective declines to fill,
    by construction, and [`curation.seating`]'s greedy is the leg that fills one
    unconditionally. The two agree wherever the floor is free.

    ## What an incumbent's own floor is worth

    Stage 2 was the whole cost of this — 9.8 s of an 11.1 s round at n=60, against
    1.1 s for stage 1 and 0.2 for stage 3 — and the reason is that `t` has no
    lower bound in it, so no amount of presolve can tell the solver that a
    candidate scoring 0.4 is not going to be seated in a gallery whose floor is
    0.97. **An incumbent says so.** Any feasible solution that attains `cleared`
    has some minimum score `L`, so the optimal floor is at least `L`, so no
    optimal solution seats anything scoring below `L` — and every such column can
    be fixed to zero without removing a single optimum. Measured at n=60: 9.8 s to
    0.36 s, 15,955 free columns to 305, same floor to twelve places.

    `seed` is where a better `L` than stage 1's own comes from: a greedy walk down
    the ranked list seats the strongest candidates it can, so its floor is
    normally the higher of the two. It is used **only** when its above-bar count
    matches the count stage 1 proved, because a solution that clears fewer is not
    a solution stage 2 is choosing among. When it matches `n` — the trivial upper
    bound on a count of `n` seats — stage 1 is proved by the seed and skipped.
    """
    import numpy
    from scipy import sparse
    from scipy.optimize import Bounds, LinearConstraint, milp

    base, low, high, _index = matrices(program)
    size = program.size
    modes = list(program.modes)
    width = size + 1 + len(modes)
    scores = numpy.array([candidate.score for candidate in program.candidates])
    above = numpy.array([1.0 if c.above_bar else 0.0 for c in program.candidates])
    pad = sparse.csr_array((base.shape[0], width - size))
    base = sparse.hstack([base, pad], format="csr")
    # One deficit column per mode, bounded by that mode's own floor: the row is
    # `seated + d >= floor`, so a bound of the floor is what makes it soft.
    asked = numpy.array([float(program.mode_floors[name]) for name in modes])
    ceiling_of = numpy.concatenate([numpy.ones(size), [1.0], asked])
    values: dict = {}
    started = time.monotonic()

    def answer(objective, matrix, lower, upper, columns=None):
        return milp(
            c=objective,
            constraints=LinearConstraint(matrix, lower, upper),
            integrality=numpy.concatenate(
                [numpy.ones(size, dtype=int), numpy.zeros(width - size, dtype=int)]
            ),
            bounds=Bounds(lb=numpy.zeros(width), ub=ceiling_of if columns is None else columns),
        )

    def below(bar: float):
        """The column bounds with every candidate under `bar` fixed to zero."""
        out = ceiling_of.copy()
        out[:size] = numpy.where(scores >= bar - EPSILON, 1.0, 0.0)
        return out

    # --- stage 1: how many clear the bar ---------------------------------- #
    proved = seed if seed and seed.get("feasible") and seed["above_bar"] >= program.n else None
    if proved is not None:
        # `n` seats cannot hold more than `n` above the bar, so a seed that holds
        # `n` attains the optimum and there is nothing for branch-and-bound to do.
        cleared = int(program.n)
        held = list(proved["chosen"])
        values["stage_one_from"] = "the seed, which holds every seat above the bar"
    else:
        objective = numpy.zeros(width)
        objective[:size] = -(above + (TIE_BREAK / max(1, program.n)) * scores)
        first = answer(objective, base, low, high)
        if first.status != 0:
            return {"feasible": False, "status": int(first.status), "message": str(first.message)}
        cleared = int(sum(above[at] for at in range(size) if first.x[at] > 0.5))
        held = [at for at in range(size) if first.x[at] > 0.5]
    values["above_bar"] = cleared
    log(f"[solve] stage 1: {cleared} of {program.n} clear the q4 bar")

    # --- what the incumbent proves about the floor ------------------------- #
    known = min((scores[at] for at in held), default=0.0)
    if seed and seed.get("feasible") and seed["above_bar"] == cleared:
        known = max(known, float(seed["floor"]))
    values["floor_at_least"] = round(float(known), 6)

    # --- stage 2: the floor ------------------------------------------------ #
    freeze = numpy.zeros((1, width))
    freeze[0, :size] = above
    floors_block = sparse.hstack(
        [
            sparse.eye_array(size, format="csr"),
            sparse.csr_array(numpy.ones((size, 1))),
            sparse.csr_array((size, len(modes))),
        ],
        format="csr",
    )
    second_matrix = sparse.vstack([base, sparse.csr_array(freeze), floors_block], format="csr")
    second_low = numpy.concatenate([low, [float(cleared)], numpy.full(size, -numpy.inf)])
    second_high = numpy.concatenate([high, [float(cleared)], scores + 1.0])
    objective = numpy.zeros(width)
    objective[size] = -1.0
    reachable = below(known)
    values["columns_free"] = int(reachable[:size].sum())
    second = answer(objective, second_matrix, second_low, second_high, columns=reachable)
    if second.status != 0:
        return {"feasible": False, "status": int(second.status), "message": str(second.message)}
    floor = float(second.x[size])
    values["floor"] = floor
    log(
        f"[solve] stage 2: floor {floor:.6f} over {values['columns_free']:,} of {size:,} "
        f"columns, the rest fixed off by an incumbent floor of {known:.6f}"
    )

    # --- stage 3: the sum, less the mode penalty --------------------------- #
    deficits = sparse.lil_array((len(modes), width))
    for at, name in enumerate(modes):
        for column in program.mode_members[name]:
            deficits[at, column] = 1.0
        deficits[at, size + 1 + at] = 1.0
    hold_floor = numpy.zeros((1, width))
    hold_floor[0, size] = 1.0
    third_matrix = sparse.vstack(
        [second_matrix, sparse.csr_array(hold_floor), sparse.csr_array(deficits)], format="csr"
    )
    third_low = numpy.concatenate(
        [
            second_low,
            [floor - EPSILON],
            asked,
        ]
    )
    third_high = numpy.concatenate([second_high, [numpy.inf], numpy.full(len(modes), numpy.inf)])
    penalty = program.n * PENALTY_PER_SEAT
    objective = numpy.zeros(width)
    objective[:size] = -scores
    objective[size + 1 :] = penalty
    # Not an optimality argument this time but an implication of the rows: with
    # `t >= floor` held and `x_i + t <= score_i + 1`, a candidate scoring under the
    # floor already has `x_i < 1`, and a binary under one is zero.
    third = answer(objective, third_matrix, third_low, third_high, columns=below(floor))
    if third.status != 0:
        return {"feasible": False, "status": int(third.status), "message": str(third.message)}
    chosen = [at for at in range(size) if third.x[at] > 0.5]
    missing = [name for at, name in enumerate(modes) if third.x[size + 1 + at] > EPSILON]
    values["sum"] = round(float(sum(program.candidates[at].score for at in chosen)), 6)
    values["modes_missing"] = missing
    values["penalty_paid"] = round(penalty * len(missing), 6)
    return {
        "feasible": True,
        "chosen": chosen,
        "values": values,
        "seconds": round(time.monotonic() - started, 2),
    }


def relaxation(program: Program, log=print) -> dict:
    """Stage 1 with the integrality dropped. The cheap read on feasibility.

    Taken first because an infeasible relaxation is an infeasible program, and
    the shortage list is what a caller wanted from an infeasible one anyway — so
    this is the read that decides whether anything pays for branch-and-bound.
    """
    import numpy

    matrix, low, high, _index = matrices(program)
    objective = numpy.array([-1.0 if c.above_bar else 0.0 for c in program.candidates])
    started = time.monotonic()
    answer = _linear(
        objective, matrix, low, high, numpy.zeros(program.size), numpy.ones(program.size)
    )
    seconds = round(time.monotonic() - started, 2)
    verdict = "feasible" if answer.status == 0 else str(answer.message)
    log(f"[solve] LP relaxation: {verdict} ({seconds}s)")
    return {
        "feasible": answer.status == 0,
        "status": int(answer.status),
        "message": str(answer.message),
        "above_bar": round(float(-answer.fun), 3) if answer.status == 0 else None,
        "seconds": seconds,
    }


def seed_greedily(program: Program, pairs: Pairs, reach: int = SEED_REACH, log=print) -> dict:
    """Walk the ranked list, seat what nothing refuses, and keep what refused it.

    **A primal heuristic and never a shipped answer.** Sequential seating is what
    this module replaced: it is order-dependent, it cannot take a seat back, and
    the whole finding behind the exact solve is that the order hides which rule
    was really binding. What a greedy walk is good for is the two things an exact
    solve cannot make for itself before it starts.

    * **Cuts.** Every pair the walk refuses as too close is a *valid row of the
      full program* — two pictures under their threshold can never both be seated,
      whoever noticed it — so seeding the pool with them is sound however bad the
      walk's own answer is. They are the rows the loop would otherwise spend a
      round each discovering, and they are the same rows: the walk refuses the
      strongest candidates, which is where the optimum lives too.
    * **A floor.** A feasible walk hands [`lexicographic`] an incumbent, and an
      incumbent's own minimum score is what fixes stage 2's columns.

    It walks at most `reach * n` candidates and it walks them in score order, so
    what it costs is one pixel-cloud signature per candidate that survives the two
    arithmetic tests — the ones the loop was going to make anyway.
    """
    started = time.monotonic()
    rule, n = program.rule, program.n
    seated: list = []
    places: set = set()
    counts: dict = {}
    cuts: list = []
    considered = 0
    for at, candidate in enumerate(program.candidates):
        if len(seated) >= n or considered >= max(1, int(reach)) * n:
            break
        if candidate.location in places:
            continue
        colours = (*candidate.cells, *candidate.families)
        if any(counts.get(name, 0) + 1 > rule.allowed(name, n) for name in colours):
            continue
        considered += 1
        pairs.measure([at, *seated])
        close = [other for other in seated if pairs.violates(at, other)]
        if close:
            cuts += [(min(at, other), max(at, other)) for other in close]
            continue
        seated.append(at)
        places.add(candidate.location)
        for name in colours:
            counts[name] = counts.get(name, 0) + 1
    read = {
        "seats": len(seated),
        "considered": considered,
        "cuts": len(cuts),
        "seconds": round(time.monotonic() - started, 2),
    }
    if len(seated) == n and satisfies(program, seated):
        read["feasible"] = True
        read["chosen"] = seated
        read["above_bar"] = sum(1 for at in seated if program.candidates[at].above_bar)
        read["floor"] = round(min(program.candidates[at].score for at in seated), 6)
    else:
        # Still worth every cut it found: a cut is a fact about a pair and not
        # about this walk. Only the incumbent is thrown away.
        read["feasible"] = False
        read["why_not"] = (
            f"filled {len(seated)} of {n} seats"
            if len(seated) < n
            else "filled every seat but broke a row a greedy walk does not read, which is "
            "a colour target: the walk seats by score and a target is a demand"
        )
    log(
        f"[seed] greedy: {read['seats']} seat(s) from {considered} candidate(s), "
        f"{len(cuts)} cut(s) seeded, feasible={read['feasible']} ({read['seconds']}s)"
    )
    return {**read, "pairs": [tuple(pair) for pair in dict.fromkeys(cuts)]}


def satisfies(program: Program, chosen: list[int]) -> bool:
    """Does this seat list clear **every row** of the program as it stands?

    Through [`matrices`] and not through a second reading of the rules, which is
    the point: a greedy walk knows about the ceiling and the places and the
    pairwise rules, and a program can carry rows it does not know about at all —
    a colour target does, and the cuts a previous round generated do. Asked as one
    sparse product, so a row added later is checked without anything being taught
    about it.
    """
    import numpy

    matrix, low, high, _index = matrices(program)
    vector = numpy.zeros(program.size)
    vector[list(chosen)] = 1.0
    taken = matrix @ vector
    return bool(numpy.all(taken >= low - EPSILON) and numpy.all(taken <= high + EPSILON))


def cutting_plane(
    program: Program,
    pairs: Pairs,
    rounds: int = ROUNDS,
    deadline: float | None = None,
    seed: dict | None = None,
    log=print,
) -> dict:
    """Solve, look at the incumbent's pairs, add the violated ones, solve again.

    Terminates on an incumbent that violates nothing, which is the full program's
    optimum and not merely this relaxation's — see the module docstring. A master
    that turns infeasible is also a termination and the honest one: the cuts are
    valid rows of the full program, so an infeasible master is an infeasible
    program.
    """
    history = []
    for round_at in range(1, int(rounds) + 1):
        if deadline is not None and time.monotonic() > deadline:
            raise SolveRefused(
                f"the cutting-plane loop ran out of its wall budget after {round_at - 1} "
                f"round(s), with {len(program.cuts)} pair(s) cut. What it had was an "
                f"incumbent that still violated a pairwise rule, so there is no answer to "
                f"report — only how far it got."
            )
        answer = lexicographic(program, seed=seed, log=log)
        if not answer["feasible"]:
            history.append({"round": round_at, "feasible": False, "cuts": len(program.cuts)})
            return {
                "feasible": False,
                "rounds": history,
                "cuts": len(program.cuts),
                "message": answer.get("message"),
            }
        picked = set(answer["chosen"])
        found = pairs.violations(sorted(set(pairs.paid()) | picked))
        # The loop terminates on the **incumbent**, and only on it: a violation
        # between two candidates the solver did not seat is a valid row to hold it
        # to next time, but it is not a reason to call this answer wrong.
        violated = [row for row in found if picked.issuperset(row["pair"])]
        standing = set(program.cuts)
        fresh = [row for row in found if row["pair"] not in standing]
        history.append(
            {
                "round": round_at,
                "above_bar": answer["values"]["above_bar"],
                "floor": round(answer["values"]["floor"], 6),
                "sum": answer["values"]["sum"],
                "modes_missing": len(answer["values"]["modes_missing"]),
                "violated_pairs": len(violated),
                "screened": len(pairs.paid()),
                "rows_added": len(fresh),
                "seconds": answer["seconds"],
            }
        )
        log(
            f"[solve] round {round_at}: floor {answer['values']['floor']:.4f}, "
            f"{len(violated)} violated pair(s) among the seated, {len(fresh)} new row(s) "
            f"over {len(pairs.paid())} screened, {len(program.cuts)} cut(s) standing"
        )
        if not violated:
            return {
                "feasible": True,
                "chosen": answer["chosen"],
                "values": answer["values"],
                "rounds": history,
                "cuts": len(program.cuts),
                "generated": [
                    {name: pair[name] for name in ("a", "b", "distance", "wanted", "rule")}
                    for pair in program.generated
                ],
            }
        program.cuts.extend(row["pair"] for row in fresh)
        program.generated.extend(fresh)
    raise SolveRefused(
        f"the cutting-plane loop did not converge in {rounds} rounds, with "
        f"{len(program.cuts)} pair(s) cut. That is a finding about the pool rather than a "
        f"bound to raise: the incumbent keeps landing on near-duplicate pairs."
    )


# --------------------------------------------------------------------------- #
# Infeasibility, as a shopping list.
# --------------------------------------------------------------------------- #
def elastic(program: Program, log=print) -> dict:
    """Every relaxable row given a slack; minimize the slack. The shortage list.

    An IIS says *which* rows are in conflict. This says **how many candidates
    short** each of them is, which is the number a conditioned hunt is sized by,
    and it is a different question: a program can be three short in one place or
    one short in three, and an irreducible subset names the same rows either way.

    Slacks are one-sided by the block's kind, so the answer reads as a shortage
    rather than as a signed residual. The cardinality equality gets the **under**
    side only, which is the side that means "these seats cannot be filled"; a
    demand that wanted more than `n` seats is absorbed by its own slack, so
    nothing here can be infeasible.
    """
    import numpy
    from scipy import sparse

    matrix, low, high, index = matrices(program)
    columns = list(range(len(index)))
    #: A cap is relieved by taking away, a demand and the cardinality equality by
    #: adding — one sign per row, and the slack is nonnegative either way.
    signs = [-1.0 if kind == OVER else 1.0 for _name, _about, kind in index]
    slack = sparse.csr_array(
        (numpy.array(signs), (numpy.array(columns), numpy.arange(len(columns)))),
        shape=(matrix.shape[0], len(columns)),
    )
    full = sparse.hstack([matrix, slack], format="csr")
    objective = numpy.concatenate([numpy.zeros(program.size), numpy.ones(len(columns))])
    started = time.monotonic()
    answer = _linear(
        objective,
        full,
        low,
        high,
        numpy.zeros(program.size + len(columns)),
        numpy.concatenate([numpy.ones(program.size), numpy.full(len(columns), numpy.inf)]),
    )
    if answer.status != 0:
        raise SolveRefused(
            "the elastic program is itself infeasible, which cannot happen while every "
            f"row carries a slack: {answer.message}"
        )
    short: dict = {}
    for at, (name, about, _kind) in enumerate(index):
        value = float(answer.x[program.size + at])
        if value > EPSILON:
            short.setdefault(name, []).append({"about": about, "short_by": round(value, 4)})
    for rows in short.values():
        rows.sort(key=lambda row: -row["short_by"])
    log(f"[solve] elastic: total slack {float(answer.fun):.3f} over {len(short)} block(s)")
    return {
        "total_slack": round(float(answer.fun), 4),
        "by_block": {
            name: {
                "rows": len(rows),
                "short_by": round(sum(row["short_by"] for row in rows), 4),
                "worst": rows[:12],
            }
            for name, rows in sorted(short.items())
        },
        "seconds": round(time.monotonic() - started, 2),
    }


def deletion_filter(program: Program, log=print) -> list[str]:
    """An irreducible infeasible subset **of the blocks**, by the deletion filter.

    Block granularity and not row granularity, on purpose: "the colour target and
    the colour ceiling cannot both hold" is a sentence somebody can act on, and
    "rows 14, 61 and 2,207" is not. Each step is one LP over a program with one
    block removed, so the whole filter is a handful of LPs.

    **Empty where the LP is feasible**, and that is a different answer rather than
    a missing one. The filter is over the relaxation, so it can only ever name a
    conflict the relaxation has; a program whose LP is feasible and whose MILP is
    not is infeasible over the *integers*, and every block would come back in the
    subset — a list of all six, which reads like a finding and is not one.
    """
    if relaxation_without(program, set())["feasible"]:
        log("[solve] no irreducible subset: the LP is feasible with every block held")
        return []
    keep = [name for name, _kind, block in program.blocks() if block]
    dropped: set = set()
    for name in list(keep):
        answer = relaxation_without(program, dropped | {name})
        if not answer["feasible"]:
            dropped.add(name)
    remaining = [name for name in keep if name not in dropped]
    log(f"[solve] irreducible infeasible subset: {remaining}")
    return remaining


def relaxation_without(program: Program, skip: set) -> dict:
    """Is the LP relaxation feasible with these blocks removed?"""
    import numpy

    matrix, low, high, _index = matrices(program, skip=skip)
    answer = _linear(
        numpy.zeros(program.size),
        matrix,
        low,
        high,
        numpy.zeros(program.size),
        numpy.ones(program.size),
    )
    return {"feasible": answer.status == 0, "message": str(answer.message)}


def _linear(objective, matrix, low, high, lower, upper):
    """One continuous HiGHS solve.

    Through `milp` with the integrality all zero rather than through `linprog`,
    because `LinearConstraint` states a two-sided row directly and `linprog` wants
    it split into an inequality half and an equality half — a split that would be
    a second spelling of the same rows, and the one place a `<=` could quietly
    become a `>=`.
    """
    import numpy
    from scipy.optimize import Bounds, LinearConstraint, milp

    return milp(
        c=objective,
        constraints=LinearConstraint(matrix, low, high),
        integrality=numpy.zeros(len(objective), dtype=int),
        bounds=Bounds(lb=lower, ub=upper),
    )


def shortage(program: Program, log=print) -> dict:
    """The whole infeasibility readout: what is short, where, and in which places.

    The partitions matter more than the counts do. A shortage list is the work
    order for a conditioned hunt, and a hunt is launched at a **partition**: "the
    `dark_vivid_lime` target is eleven short" says how much to look for, and "the
    pool's lime carriers are in `phoenix` and `julia:multibrot3`" says where.
    """
    read = elastic(program, log=log)
    read["irreducible_blocks"] = deletion_filter(program, log=log)
    read["verdict"] = _verdict(program, read)
    read["supply"] = {}
    for name, rows in read["by_block"].items():
        if name not in {"colour_target", "colour_ceiling_cells", "colour_ceiling_families"}:
            continue
        for row in rows["worst"]:
            read["supply"][row["about"]] = _supply_for(program, row["about"])
    if "cardinality" in read["by_block"]:
        read["supply"]["__the_pool__"] = _partitions(program, range(program.size))
    return read


def _verdict(program: Program, read: dict) -> str:
    """Which kind of infeasibility this is, in a sentence.

    A shortage list is only a work order when something is actually **short**, and
    a slack of zero means nothing is: every linear row can be met at once and what
    cannot be met is the requirement that a picture is seated or not seated. With
    pairwise rows standing that is the diversity radius, which no hunt for more of
    one colour will relieve — it is a statement about how alike the pool already
    is, and the answer to it is a smaller `n` or a wider pool.
    """
    if read["total_slack"] > EPSILON:
        return (
            f"{read['total_slack']:.1f} candidate(s) short across "
            f"{len(read['by_block'])} block(s). This is a supply shortage and a hunt "
            "is what spends it."
        )
    return (
        "NOT a supply shortage: the LP relaxation is feasible with every block held, so "
        f"no row is short of candidates. The program is infeasible over the integers, and "
        f"with {len(program.cuts)} pairwise row(s) standing that is the diversity radius "
        "refusing the combinations rather than the pool refusing the colours. A hunt for "
        "more of a colour does not relieve it; a smaller n or a wider pool does."
    )


def _supply_for(program: Program, colour: str) -> dict:
    members = program.cell_members.get(colour) or program.family_members.get(colour) or []
    return {
        "candidates": len(members),
        "locations": len({program.candidates[at].location for at in members}),
        "partitions": _partitions(program, members),
    }


def _partitions(program: Program, members) -> dict:
    per: dict = {}
    for at in members:
        name = program.candidates[at].partition
        per.setdefault(name, set()).add(program.candidates[at].location)
    return {name: len(keys) for name, keys in sorted(per.items(), key=lambda x: -len(x[1]))}


# --------------------------------------------------------------------------- #
# One solve, end to end.
# --------------------------------------------------------------------------- #
def rule_for(targets: dict | None = None) -> ceiling.Rule:
    """The ceiling's constants and targets.

    [`ceiling.Rule`] holds the allowance arithmetic and the target-to-family
    summation, and both are wanted here — a target raises the allowance of the
    cell it names and of that cell's family, and a second derivation of that
    would be a second answer.
    """
    return ceiling.Rule(targets=dict(targets or {}))


def solve(
    n: int = candidate_ledger.FIRST_SOLVE,
    candidates: list[Candidate] | None = None,
    targets: dict | None = None,
    locations: int | None = None,
    floor: int | dict | None = None,
    log=print,
) -> dict:
    """One gallery, solved. The record is the return value; nothing is written.

    `locations` truncates the reachable pool to that many strongest places; `None`
    is the whole ledger. `targets` is `{cell: fraction}` and is what makes a
    program hard enough to be infeasible on purpose. `floor` replaces the default
    per-mode floors — see [`Program.floor`]; `mode_floor(n)` is the flat one they
    replaced.
    """
    _scipy()

    started = time.monotonic()
    if candidates is None:
        candidates, refused = pool(log=log)
    else:
        refused = {}
    reachable = strongest_locations(candidates, locations)
    available = within(candidates, reachable) if locations is not None else candidates
    program = Program(
        candidates=available,
        n=int(n),
        rule=rule_for(targets),
        modes=tuple(mode_policy.accepted()),
        targets=dict(targets or {}),
        floor=floor,
    )
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": program.config(),
        "pool": {
            "refused": refused,
            "reachable_locations": len(reachable),
            "available": len(available),
            "truncated_to": locations,
        },
    }
    record["relaxation"] = relaxation(program, log=log)
    if not record["relaxation"]["feasible"]:
        record["feasible"] = False
        record["shortage"] = shortage(program, log=log)
        record["seconds"] = round(time.monotonic() - started, 2)
        return record

    pairs = Pairs(available)
    seed = seed_greedily(program, pairs, log=log)
    program.cuts.extend(seed["pairs"])
    record["seed"] = {name: seed[name] for name in seed if name not in {"pairs", "chosen"}}
    answer = cutting_plane(program, pairs, seed=seed, log=log)
    if not answer["feasible"]:
        record["feasible"] = False
        record["rounds"] = answer["rounds"]
        record["shortage"] = shortage(program, log=log)
        record["under_fill"] = _under_fill(program, pairs, log=log)
        record["pairs"] = pairs.price()
        record["seconds"] = round(time.monotonic() - started, 2)
        return record

    record["feasible"] = True
    record["values"] = answer["values"]
    record["rounds"] = answer["rounds"]
    record["cuts"] = answer["cuts"]
    record["generated_pairs"] = answer["generated"]
    record["pairs"] = pairs.price()
    record["seated"] = [_seat(program, at, pairs, answer["chosen"]) for at in answer["chosen"]]
    record["nearest_pairs"] = pairs.nearest(answer["chosen"])
    record["distribution"] = distribution(program, answer["chosen"])
    record["binding"] = binding(program, answer["chosen"])
    record["near_misses"] = near_misses(program, answer["chosen"], pairs, log=log)
    record["seconds"] = round(time.monotonic() - started, 2)
    log(f"[solve] {len(answer['chosen'])} seated in {record['seconds']}s")
    return record


def _under_fill(program: Program, pairs: Pairs, log=print) -> dict:
    """The seats that CAN be filled, when `n` of them cannot.

    Not a fallback leg: no rule is relaxed and nothing is seated that failed one.
    The cardinality row alone goes from `== n` to `<= n`, and what comes back is
    the largest gallery every constraint admits — which is the number the
    shortage list is a shortage *against*.

    Every other rule is rebuilt **as the program stated it**, and the two that
    once were not are the reason this says so out loud. A target rebuilt as
    `ceil(t * n)` demands a share of seats nobody is promising to fill any more,
    which made this whole readout `filled: 0` for exactly the solves it exists
    for; the floor rebuilt as `None` silently put a `--flat-floor` solve back on
    the per-mode default. So the record states the rule that ran on both counts —
    [`Program.target_rule`] and [`Program.mode_floor_rule`] — on the infeasible
    branch too, where a reader has only those to go on.
    """
    reduced = Program(
        candidates=program.candidates,
        n=program.n,
        rule=program.rule,
        modes=program.modes,
        targets=program.targets,
        cuts=list(program.cuts),
        exact_cardinality=False,
        floor=program.floor,
    )
    stated = {
        "cardinality": "<= n",
        "target_rule": reduced.target_rule,
        "mode_floor_rule": reduced.mode_floor_rule,
        "mode_floors": reduced.mode_floors,
    }
    log("[solve] re-solving at <= n so the fillable seats are filled")
    answer = cutting_plane(reduced, pairs, log=log)
    if not answer["feasible"]:
        return {"filled": 0, "unfilled": program.n, "message": answer.get("message"), **stated}
    return {
        "filled": len(answer["chosen"]),
        "unfilled": program.n - len(answer["chosen"]),
        **stated,
        "values": answer["values"],
        "seated": [_seat(reduced, at, pairs, answer["chosen"]) for at in answer["chosen"]],
        "distribution": distribution(reduced, answer["chosen"]),
    }


def _seat(program: Program, at: int, pairs: Pairs, chosen: list[int]) -> dict:
    candidate = program.candidates[at]
    others = [other for other in chosen if other != at]
    nearest = pairs.nearest_to(at, others)
    return {
        "key": candidate.key,
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
        "nearest_seated": None if nearest is None else round(nearest, 6),
    }


# --------------------------------------------------------------------------- #
# What the answer looks like.
# --------------------------------------------------------------------------- #
def distribution(program: Program, chosen: list[int]) -> dict:
    """The realized spread over every axis a constraint acts on.

    Reported from the first solve rather than the first time somebody suspects a
    problem: a gallery that seated fourteen of eighteen modes and four of nine
    partitions is a fact about the pool, and it is only visible if it is printed
    when nothing is wrong.
    """
    seated = [program.candidates[at] for at in chosen]

    def tally(values) -> dict:
        out: dict = {}
        for value in values:
            out[value] = out.get(value, 0) + 1
        return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))

    return {
        "modes": {
            "held": len({c.mode for c in seated}),
            "of": len(program.modes),
            "counts": tally(c.mode for c in seated),
            "empty": sorted(set(program.modes) - {c.mode for c in seated}),
        },
        "partitions": {
            "held": len({c.partition for c in seated}),
            "counts": tally(c.partition for c in seated),
        },
        "cells": {
            "held": len({cell for c in seated for cell in c.cells}),
            "counts": tally(cell for c in seated for cell in c.cells),
            "dominant_in_none": sum(1 for c in seated if not c.cells),
        },
        "families": {
            "held": len({name for c in seated for name in c.families}),
            "counts": tally(name for c in seated for name in c.families),
        },
        "palette_groups": {
            "held": len({c.group for c in seated}),
            "repeated": {
                name: count for name, count in tally(c.group for c in seated).items() if count > 1
            },
        },
        "kinds": tally(c.kind for c in seated),
        "scores": {
            "min": round(min(c.score for c in seated), 6),
            "median": round(sorted(c.score for c in seated)[len(seated) // 2], 6),
            "max": round(max(c.score for c in seated), 6),
            "above_bar": sum(1 for c in seated if c.above_bar),
        },
    }


def binding(program: Program, chosen: list[int]) -> dict:
    """Which constraint rows are **tight** on this answer, by block.

    A tight row is not a binding one — a cap at its bound may cost nothing — but a
    block with no tight row anywhere cannot possibly be what limits the gallery,
    and that is the half of the question a sweep over `n` is asking.
    """
    picked = set(chosen)
    out: dict = {}
    for name, kind, block in program.blocks():
        tight = []
        for members, bound, about in block:
            # The row's own left-hand side and not a count of its members: a
            # weighted row (the relaxed colour target) is at its bound when its
            # coefficients sum there, which is not how many of its columns were
            # taken. For every other row the two are the same number.
            taken = sum(weight for at, weight in members_of(members) if at in picked)
            taken = int(taken) if float(taken).is_integer() else round(taken, 6)
            at_bound = abs(taken - bound) <= EPSILON
            if (kind in {OVER, EXACT} and taken >= bound - EPSILON) or (kind == UNDER and at_bound):
                tight.append({"about": about, "at": taken, "bound": bound})
        out[name] = {"rows": len(block), "tight": len(tight), "worst": tight[:8]}
    return out


#: Why a candidate the solve did not seat was not seated. Ordered: the first that
#: applies is the one reported, because a candidate whose location is already
#: taken is refused before anything measures its pixels.
WHY_NOT = (
    "location_already_seated",
    "colour_ceiling_cell",
    "colour_ceiling_family",
    "too_close_to_a_seat",
    "same_group_as_a_seat",
    "the_objective_preferred_another",
)


def near_misses(
    program: Program, chosen: list[int], pairs: Pairs, count: int = NEAR_MISSES, log=print
) -> list[dict]:
    """The strongest unseated candidates, each with the rule that refused it.

    The other half of the contact sheet, and the half that is read. A gallery on
    its own says what the program liked; a gallery beside the pictures it refused,
    each labelled with **which row refused it**, is what a person can disagree
    with. A near miss labelled `the_objective_preferred_another` cleared every
    constraint and simply lost the sum, which is a different and much weaker
    statement than "the ceiling refused it".
    """
    picked = set(chosen)
    seated_locations = {program.candidates[at].location for at in chosen}
    cells: dict = {}
    families: dict = {}
    for at in chosen:
        for cell in program.candidates[at].cells:
            cells[cell] = cells.get(cell, 0) + 1
        for family in program.candidates[at].families:
            families[family] = families.get(family, 0) + 1
    out = []
    for at, candidate in enumerate(program.candidates):
        if at in picked:
            continue
        why = None
        if candidate.location in seated_locations:
            why = "location_already_seated"
        elif any(
            cells.get(cell, 0) >= program.rule.allowed(cell, program.n) for cell in candidate.cells
        ):
            why = "colour_ceiling_cell"
        elif any(
            families.get(name, 0) >= program.rule.allowed(name, program.n)
            for name in candidate.families
        ):
            why = "colour_ceiling_family"
        else:
            pairs.measure([at, *chosen])
            close = [other for other in chosen if pairs.violates(at, other)]
            if close:
                same = any(program.candidates[o].group == candidate.group for o in close)
                why = "same_group_as_a_seat" if same else "too_close_to_a_seat"
            else:
                why = "the_objective_preferred_another"
        out.append(
            {
                "key": candidate.key,
                "location": candidate.location,
                "partition": candidate.partition,
                "mode": candidate.mode,
                "palette_group": candidate.group,
                "p_ge4": round(candidate.score, 6),
                "p_ge3": round(candidate.p_ge3, 6),
                "why_not": why,
                "picture": candidate.picture,
            }
        )
        if len(out) >= int(count):
            break
    log(f"[solve] {len(out)} near miss(es), {pairs.made} signature(s) made in all")
    return out


# --------------------------------------------------------------------------- #
# Where a solve's own output lives.
# --------------------------------------------------------------------------- #
def solve_dir(name: str) -> Path:
    """The directory one solve's record, renders and sheets sit in."""
    return under("curation", UNIT, str(name))


def write_record(name: str, record: dict) -> Path:
    """The solve record, as JSON beside its renders."""
    path = solve_dir(name) / "solve.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def read_record(name: str) -> dict:
    path = solve_dir(name) / "solve.json"
    if not path.is_file():
        raise SolveRefused(f"there is no solve called {name!r} at {tracked_name(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# What a solve ships.
# --------------------------------------------------------------------------- #
#: What the seats are rendered at. [`release.RELEASE_REGIME`] and not a second
#: opinion about it: every leg that ships a wallpaper ships the same pixels, and
#: the whole claim of this module is that only the *choosing* changed.
def release_regime():
    from fractal_wallpapers.curation import release

    return release.RELEASE_REGIME


#: How long one release row gets before the worker kills it. **A backstop and
#: never a budget.**
#:
#: The release leg has no clock: every row it plans is rendered to completion and
#: there is no knob that stops the leg early. What this bounds is the row that has
#: stopped making progress at all — a quarter of an hour against a leg whose
#: median row at 1280x720 ss2 is measured in single-digit seconds and whose worst
#: recorded row at four times the samples per axis was 799 s. A row that reaches
#: it comes back failed and named, and the leg carries on.
ROW_BACKSTOP = 900.0


def render_seats(
    name: str,
    record: dict,
    workers: int | None = None,
    regime=None,
    where: Path | None = None,
    timeout: float | None = ROW_BACKSTOP,
    log=print,
) -> dict:
    """Render every seat of a solve or a seating at release geometry. Mutates `record`.

    The same two facts a pass's release leg records and for the same reasons: the
    **geometry lands on each seat**, because the default has moved once already
    and a sheet that captioned every picture with today's default would relabel
    every wallpaper an earlier solve made; and the autolevel stamp is the *release
    render's own*, never the candidate's, because they are two renders and
    showing one under the other's caption is how a page says something false with
    every field on it true.

    No re-score. The release picture is the same recipe as the candidate the
    decision was taken on, at another size, and the judge's floors were fit on
    640x360 candidate renders. **Nothing here applies a bar of any kind**: every
    seat the walk chose is rendered and every render that succeeds is released.

    `where` is the directory the pictures and the stamp log land in, defaulting to
    the solve's own. [`curation.seating`] passes its seat directory: the two
    records carry the same `seated` shape, and a second copy of this leg beside
    it would be a second place for the geometry and the stamp rule to drift.

    `workers` is [`release.DEFAULT_WORKERS`] unless a caller says otherwise —
    the machine's three-at-below-normal render pool, read from the module that
    owns it. It was a literal 4 at this signature, which is one more engine than
    the desktop survives.

    `timeout` is [`ROW_BACKSTOP`], stamped onto every task so the **worker**
    imposes it. It is not a [`pacing.Leg`] and there is no gate: no row is ever
    declined, so the leg still runs to completion.
    """
    from fractal_wallpapers.curation import release

    regime = release_regime() if regime is None else regime
    workers = release.DEFAULT_WORKERS if workers is None else int(workers)
    wanted = {str(seat["key"]) for seat in record["seated"]}
    # A keyed lookup and not a read: this needs the recipes behind about a
    # hundred and fifty seats, and reading the whole ledger for them held every
    # other row in memory for the length of a release render pass.
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
        "walk chose is rendered, and a floor at shipping geometry does not exist",
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

    Presence stopped being the whole test the day the regime became a
    parameter, so the frame is read off the file.
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


# --------------------------------------------------------------------------- #
# The contact sheet.
# --------------------------------------------------------------------------- #
def contact_sheet(name: str, record: dict, output: Path | None = None) -> Path:
    """The twenty seated, and the strongest the program refused, on one page.

    Both halves, because a gallery on its own only says what the program liked. A
    near miss is captioned with **which row refused it**, which is the thing a
    person can disagree with: `the_objective_preferred_another` means every
    constraint passed and it lost the sum, and that is a far weaker statement than
    "the colour ceiling refused it".
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    output = solve_dir(name) / "contact_sheet.html" if output is None else Path(output)
    values = record.get("values") or {}
    spread = record.get("distribution") or {}
    seated = record.get("seated") or []
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>solve {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>solve {html.escape(name)}</h1>",
        f"<p class='lede'>{len(seated)} of {record['config']['n']} seat(s) filled from "
        f"{record['config']['candidates']:,} candidates over "
        f"{record['config']['locations']:,} locations. "
        f"{values.get('above_bar', '?')} clear the q4 bar ({Q4_BAR} on raw P(&ge;4)); "
        f"floor {_number(values.get('floor'))}; "
        f"{record.get('cuts', 0)} pairwise row(s) generated over "
        f"{len(record.get('rounds') or [])} cutting-plane round(s) in "
        f"{record.get('seconds')}s. Distribution review is yours.</p>",
        _spread_html(spread),
        f"<h2>Seated ({len(seated)})</h2>",
        "<div class='grid'>"
        + "".join(_seat_card(seat, name, sheet_module) for seat in seated)
        + "</div>",
    ]
    misses = record.get("near_misses") or []
    if misses:
        lines += [
            f"<h2>Near misses ({len(misses)})</h2>",
            "<p class='lede'>The strongest candidates the program did not seat, each with "
            "the row that refused it. These are the 640&times;360 candidate renders the "
            "judge itself read — nothing was rendered at release size for a picture that "
            "did not take a seat.</p>",
            "<div class='grid'>"
            + "".join(_miss_card(miss, sheet_module) for miss in misses)
            + "</div>",
        ]
    pairs = record.get("nearest_pairs") or []
    if pairs:
        rows = "".join(
            f"<tr><th>{pair['distance']:.4f}</th><td>{html.escape(pair['a'])}</td>"
            f"<td>{html.escape(pair['b'])}</td>"
            f"<td>{'same palette group' if pair['same_group'] else ''}</td></tr>"
            for pair in pairs
        )
        lines += [
            "<h2>The nearest seated pairs</h2>",
            f"<p class='lede'>The calibration instrument. The rule refuses anything under "
            f"{ceiling.TAU} in the pixel-cloud metric, and {ceiling.TAU_GROUP} inside one "
            f"palette "
            f"group. If two of these read as one wallpaper, the radius is too small.</p>",
            f"<table>{rows}</table>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _spread_html(spread: dict) -> str:
    if not spread:
        return ""
    rows = [
        (
            "modes",
            f"{spread['modes']['held']} of {spread['modes']['of']} held — "
            f"{', '.join(f'{k} {v}' for k, v in spread['modes']['counts'].items())}",
        ),
        ("partitions", ", ".join(f"{k} {v}" for k, v in spread["partitions"]["counts"].items())),
        (
            "hue families",
            f"{spread['families']['held']} of 12 — "
            + ", ".join(f"{k} {v}" for k, v in spread["families"]["counts"].items()),
        ),
        (
            "colour cells",
            f"{spread['cells']['held']} distinct, "
            f"{spread['cells']['dominant_in_none']} dominant in none",
        ),
        ("palette groups", f"{spread['palette_groups']['held']} distinct"),
        ("judge kinds", ", ".join(f"{k} {v}" for k, v in spread["kinds"].items())),
        (
            "scores",
            f"min {spread['scores']['min']:.4f}, median "
            f"{spread['scores']['median']:.4f}, max {spread['scores']['max']:.4f}",
        ),
    ]
    import html

    body = "".join(
        f"<tr><th>{html.escape(name)}</th><td>{html.escape(value)}</td></tr>"
        for name, value in rows
    )
    return f"<h2>What was realized</h2><table>{body}</table>"


def _seat_card(seat: dict, name: str, sheet_module) -> str:
    import html

    from fractal_wallpapers.curation import release

    picture = seat.get("release_picture")
    if picture:
        source = Path(rehome(picture))
        regime = release.regime_from_geometry(seat.get("release_geometry"))
        what = regime.spelled if regime is not None else "a release render of unrecorded size"
    else:
        source = picture_of_row(seat)
        what = "NO RELEASE RENDER YET - the 640x360 candidate the decision was taken on"
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if source is not None and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    facts = [
        what,
        f"{seat['partition']} - {seat['mode']} - {seat['palette_group']}",
        f"P(>=4) {_number(seat.get('p_ge4'))}, P(>=3) {_number(seat.get('p_ge3'))} "
        f"({seat.get('kind')})",
        f"dominant in {', '.join(seat.get('cells') or []) or 'nothing'}",
        f"{_number(seat.get('nearest_seated'))} from its nearest seated neighbour",
        sheet_module.autolevel_line(seat.get("release_autolevel"), "at release size"),
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(seat['key'])}</b><ul>{caption}</ul></figcaption></figure>"
    )


def _miss_card(miss: dict, sheet_module) -> str:
    import html

    source = picture_of_row(miss)
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if source is not None and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    facts = [
        f"REFUSED BY: {miss['why_not']}",
        f"{miss['partition']} - {miss['mode']} - {miss['palette_group']}",
        f"P(>=4) {_number(miss.get('p_ge4'))}, P(>=3) {_number(miss.get('p_ge3'))}",
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(miss['key'])}</b><ul>{caption}</ul></figcaption></figure>"
    )


def picture_of_row(row: dict) -> Path | None:
    """Where a seat's or a near miss's candidate render is, off the stored name.

    `None` for a row with no name **and** for a name this checkout cannot resolve:
    `rehome` answers `None` for a name with no artifacts component, and the
    unguarded `Path(None)` raised `TypeError` from inside a sheet build rather
    than showing the "no picture on disk" tile both callers already draw. The
    same shape crashed `seating.contact_sheet` on 2026-08-28.
    """
    name = row.get("picture")
    if not name:
        return None
    where = rehome(name)
    return None if where is None else Path(where)


def _number(value) -> str:
    return "-" if value is None else f"{float(value):.4f}"


# --------------------------------------------------------------------------- #
# The three cheap experiments.
# --------------------------------------------------------------------------- #
#: The sizes the full sweep visits. Geometric, because the question is *where* a
#: constraint starts binding rather than at exactly which seat, and a linear walk
#: to five hundred is four hundred and eighty solves to find out.
#:
#: It stops where **this project has actually measured**, which is the only thing
#: that has ever set this constant. It used to stop at 80 because a round held one
#: 512 KiB signature per seat and measured every pair of them; the bound settles
#: 98% of those pairs at a thirty-second of the bytes, and the stage-2 column fix
#: took the MILP inside a round from 11 s to under 2. What is left growing is the
#: **round count** — 2 at n=20, 3 at 40, 8 at 60, 7 at 80, 18 at 120 — because a
#: larger incumbent lands on more near-duplicate pairs, and a round removes only
#: the ones the pool it has screened can show it.
#:
#: Past the top rung the cost of the read is the finding, and it wants its own
#: study rather than a longer default. A caller with an afternoon passes its own
#: sizes. [`relaxation_ladder`] carries the same question to the top in seconds, on
#: every block except the two pairwise ones.
SWEEP = (20, 30, 40, 60, 80, 120, 160)


def sweep(
    candidates: list[Candidate] | None = None,
    sizes=SWEEP,
    seconds: float = SWEEP_SECONDS,
    log=print,
) -> dict:
    """Solve at each `n` and say **which constraint binds first, and where**.

    The census says nothing binds at twenty. This is the read that says where it
    starts: for every size it reports which blocks are tight, and the first size
    at which the program is infeasible names — through the deletion filter — the
    block that ran out of pool. That is what sizes a conditioned hunt.

    Each size gets its own cutting-plane loop and its own [`Pairs`], because a
    cut generated at one `n` is a valid row at another only by accident: the
    colour allowances move with `n`, so a different incumbent is reached.
    """
    _scipy()

    if candidates is None:
        candidates, _refused = pool(log=log)
    modes = tuple(mode_policy.accepted())
    out = []
    first_infeasible = None
    deadline = time.monotonic() + float(seconds)
    stopped = None
    for size in sizes:
        if first_infeasible is not None:
            break
        if time.monotonic() > deadline:
            stopped = int(size)
            log(f"[sweep] out of wall budget before n={size}")
            break
        program = Program(candidates=candidates, n=int(size), rule=rule_for(), modes=modes)
        pairs = Pairs(candidates)
        started = time.monotonic()
        read = relaxation(program, log=log)
        gave_up = None
        seeded = None
        if not read["feasible"]:
            answer = {"feasible": False, "rounds": [], "cuts": 0}
        else:
            seeded = seed_greedily(program, pairs, log=log)
            program.cuts.extend(seeded["pairs"])
            try:
                answer = cutting_plane(program, pairs, deadline=deadline, seed=seeded, log=log)
            except SolveRefused as refusal:
                # A ladder that lost every rung to the last one's round cap would
                # report nothing at all, and "the loop did not converge at this n"
                # is the finding rather than the failure: it says the incumbent
                # keeps landing on near-duplicate pairs at this size.
                gave_up = str(refusal)
                answer = {"feasible": False, "rounds": [], "cuts": len(program.cuts)}
        entry = {
            "n": int(size),
            "feasible": answer["feasible"],
            "converged": gave_up is None,
            "rounds": len(answer.get("rounds") or []),
            "cuts": answer.get("cuts", 0),
            "signatures": pairs.made,
            "seconds": round(time.monotonic() - started, 1),
            "seed": (
                None
                if seeded is None
                else {name: seeded[name] for name in seeded if name not in {"pairs", "chosen"}}
            ),
            "pairs": pairs.price(),
        }
        if gave_up is not None:
            entry["did_not_converge"] = gave_up
            out.append(entry)
            stopped = int(size)
            log(f"[sweep] n={size}: STOPPED — {gave_up}")
            break
        if answer["feasible"]:
            entry["values"] = {
                "above_bar": answer["values"]["above_bar"],
                "floor": round(answer["values"]["floor"], 6),
                "sum": answer["values"]["sum"],
                "modes_missing": len(answer["values"]["modes_missing"]),
            }
            entry["tight"] = {
                name: read_["tight"]
                for name, read_ in binding(program, answer["chosen"]).items()
                if read_["tight"]
            }
            entry["distribution"] = {
                axis: distribution(program, answer["chosen"])[axis]["held"]
                for axis in ("modes", "partitions", "cells", "families", "palette_groups")
            }
        else:
            entry["shortage"] = shortage(program, log=log)
            first_infeasible = int(size)
        out.append(entry)
        verdict = "ok" if entry["feasible"] else "INFEASIBLE"
        log(f"[sweep] n={size}: {verdict} ({entry['seconds']}s)")
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sizes": out,
        "first_infeasible": first_infeasible,
        "largest_feasible": max((row["n"] for row in out if row["feasible"]), default=None),
        "ladder": list(sizes),
        # Never left to be inferred from a short list. A rung nobody reached and a
        # rung that came back clean are different facts, and the whole point of a
        # bounded ladder is that it says which of the two it is.
        "stopped_at": stopped,
        "wall_budget_seconds": float(seconds),
        "without_the_pairwise_rules": relaxation_ladder(candidates, modes, log=log),
    }


def relaxation_ladder(candidates: list[Candidate], modes: tuple, log=print) -> dict:
    """The largest `n` the **non-pairwise** blocks admit, by bisection on the LP.

    The sweep above cannot be carried to a thousand seats: its cost is quadratic
    in `n` and every point of it is half a mebibyte. This can. With no cuts
    generated the program is cardinality, one-per-location and the two colour
    budgets, and its LP relaxation is a fraction of a second at any size.

    So it answers the half of "which constraint binds first" that is cheap and
    exact — where the pool of **places** runs out — and it names the block through
    the same deletion filter the shortage list uses. The diversity radius can only
    make that number smaller, and the sweep above is what measures how much.
    """

    def feasible(size: int) -> bool:
        program = Program(candidates=candidates, n=int(size), rule=rule_for(), modes=modes)
        return relaxation(program, log=lambda *_: None)["feasible"]

    low, high = 1, len(by_location(candidates)) + 1
    if feasible(high):
        return {"largest_feasible": high, "bounded": False}
    while high - low > 1:
        middle = (low + high) // 2
        if feasible(middle):
            low = middle
        else:
            high = middle
    program = Program(candidates=candidates, n=high, rule=rule_for(), modes=modes)
    blocks = deletion_filter(program, log=lambda *_: None)
    log(f"[sweep] without the pairwise rules the last feasible n is {low}; {blocks} conflict")
    return {
        "largest_feasible": low,
        "first_infeasible": high,
        "irreducible_blocks": blocks,
        "shortage": shortage(program, log=lambda *_: None),
        "locations": len(by_location(candidates)),
    }


#: The truncations the second experiment compares, as multiples of `n`. `None` is
#: the whole ledger.
TRUNCATIONS = (1.1, 2.0, 5.0, None)


def truncation(n: int = candidate_ledger.FIRST_SOLVE, candidates=None, log=print) -> dict:
    """Solve the same `n` against a smaller reachable pool, and compare.

    Hard optimization against a learned score selects that score's upper tail,
    which is where its false positives live. A smaller pool is one lever against
    that — the program cannot reach a location it was not offered — and this
    measures what the lever costs before anybody spends a label on it: how much
    of the floor, the sum and the realized spread is given up per location
    withheld.
    """
    _scipy()

    if candidates is None:
        candidates, _refused = pool(log=log)
    modes = tuple(mode_policy.accepted())
    out = []
    for multiple in TRUNCATIONS:
        keep = None if multiple is None else max(int(n), int(round(multiple * n)))
        reachable = strongest_locations(candidates, keep)
        available = within(candidates, reachable)
        program = Program(candidates=available, n=int(n), rule=rule_for(), modes=modes)
        pairs = Pairs(available)
        started = time.monotonic()
        read = relaxation(program, log=log)
        answer = {"feasible": False, "cuts": 0, "rounds": []}
        if read["feasible"]:
            seeded = seed_greedily(program, pairs, log=log)
            program.cuts.extend(seeded["pairs"])
            answer = cutting_plane(program, pairs, seed=seeded, log=log)
        entry = {
            "multiple": multiple,
            "locations_offered": len(reachable),
            "candidates_offered": len(available),
            "feasible": answer["feasible"],
            "seconds": round(time.monotonic() - started, 1),
        }
        if answer["feasible"]:
            spread = distribution(program, answer["chosen"])
            entry.update(
                {
                    "above_bar": answer["values"]["above_bar"],
                    "floor": round(answer["values"]["floor"], 6),
                    "sum": answer["values"]["sum"],
                    "modes_held": spread["modes"]["held"],
                    "partitions_held": spread["partitions"]["held"],
                    "families_held": spread["families"]["held"],
                    "modes_missing": len(answer["values"]["modes_missing"]),
                    "seated": [program.candidates[at].key for at in answer["chosen"]],
                }
            )
        else:
            entry["shortage"] = shortage(program, log=log)
        out.append(entry)
        log(f"[truncate] {multiple}: {entry.get('floor')} floor over {entry['locations_offered']}")
    whole = next((row for row in out if row["multiple"] is None), None)
    if whole and whole.get("seated"):
        for row in out:
            if row.get("seated"):
                row["shared_with_whole_pool"] = len(set(row["seated"]) & set(whole["seated"]))
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n": int(n),
        "truncations": out,
    }


__all__ = [
    "BOUND",
    "BOUND_BLOCKS",
    "Candidate",
    "EPSILON",
    "NEAR_MISSES",
    "PENALTY_PER_SEAT",
    "Pairs",
    "Program",
    "Q4_BAR",
    "ROW_BACKSTOP",
    "Q4_BASIS",
    "SEATS_PER_MODE_FLOOR",
    "ROUNDS",
    "SCHEMA",
    "SWEEP",
    "SEED_REACH",
    "SolveRefused",
    "TRUNCATIONS",
    "UNIT",
    "WHY_NOT",
    "binding",
    "by_location",
    "contact_sheet",
    "cutting_plane",
    "deletion_filter",
    "distribution",
    "elastic",
    "lexicographic",
    "matrices",
    "mode_floor",
    "near_misses",
    "picture_of",
    "picture_of_row",
    "pool",
    "read_record",
    "relaxation_ladder",
    "reduce_signature",
    "relaxation",
    "release_regime",
    "render_seats",
    "rule_for",
    "satisfies",
    "seed_greedily",
    "shortage",
    "solve",
    "solve_dir",
    "strongest_locations",
    "sweep",
    "truncation",
    "within",
    "write_record",
]
