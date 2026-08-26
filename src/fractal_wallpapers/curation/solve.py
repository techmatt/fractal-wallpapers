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

So they are **lazy**. Solve without them, look at the incumbent's own pairs, add
a row for each violated pair, solve again. It terminates on an incumbent that
violates nothing, and what it terminates on is optimal for the whole program and
not only for the rows that were generated: the generated program is a relaxation,
so its optimum bounds the full program's; the incumbent attains that bound and is
feasible for the full program; so it is the full program's optimum too.

The design this replaces was to **prune** at location level — pairs whose places
are far apart cannot be near-duplicate pictures, so only close locations need
their candidates expanded. Measured over 79,621 cross-location pairs drawn from
the pool's top two thousand, that premise is false: 1,350 of them are closer than
[`RADIUS`] as pictures, and the furthest-apart pair of *places* that makes one
sits at cosine 0.583, past the 90th percentile of location distance. It is the
expected answer once stated plainly — this metric is over a picture's colour
cloud, and colour comes from the map rather than from the place, so two unrelated
frames through similar ramps are near-duplicates by construction. A prune at 0.40
would still keep 91% of the pairs and miss 96 real violations. There is no sound
cut, and the cutting-plane loop means there does not need to be one.

The two rules are one test with two thresholds. Two seated pictures must be at
least [`RADIUS`] apart in [`pixel_clouds.METRIC`]; two seated pictures of one
**palette group** must be at least [`ceiling.TAU_GROUP`] apart, which is that
cap's own exemption distance and the larger of the two.

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

from fractal_wallpapers.curation import candidate_ledger, ceiling, floors
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

#: How far apart two seated **pictures** must be, in [`pixel_clouds.METRIC`].
#:
#: 0.07, and it is a *picture* distance, not the location-embedding cosine
#: [`gallery.RADIUS`] happens to share a number with. The two measure different
#: things: that one asks whether two places are the same place, before anything is
#: coloured; this asks whether two finished wallpapers are the same wallpaper.
#:
#: Loose on purpose, and readable against the two thresholds already set in this
#: metric. [`ceiling.TAU`] is 0.0586 — Matt's, off the twins ladder, where two
#: pictures *are* one wallpaper — and [`ceiling.TAU_GROUP`] is 0.10, where two
#: pictures are plainly different ones. This sits between them and nearer the
#: first: a collection-wide rule can afford to refuse a pair a twin test would
#: pass, because there are fifteen thousand candidates and twenty seats.
RADIUS = 0.07

#: How many seats one production mode's floor asks for. **One** — the floor is
#: "this mode is represented at all", which is the accounting gallery4 did not
#: have when it seated 13 of 18 modes and nothing anywhere said so.
MODE_FLOOR = 1

#: The mode-floor penalty, **per seat of the gallery**: `lambda = n * this`.
#:
#: A hundredth of a seat, so at `n=20` a missing mode costs 0.2 of objective —
#: heavy against the sum it comes off, because that sum is over scores that
#: saturate. The pool's top two hundred candidates sit between 0.998 and 1.000, so
#: swapping a seat to cover a mode costs thousandths and buys 0.2. It scales with
#: `n` because the sum does.
PENALTY_PER_SEAT = 1.0 / 100.0

#: How many cutting-plane rounds before the loop gives up and says so. A backstop
#: on a loop expected to take a handful, not an operating parameter: each round is
#: a fresh three-stage solve plus the incumbent's own signatures.
ROUNDS = 60

#: How long [`sweep`] may spend on the whole ladder, in seconds.
#:
#: A round cap bounds **rounds** and not time, and those stopped being the same
#: thing somewhere above n=60: the rounds grow with `n` and so does the MILP
#: inside each of them. Measured on the pool — 19 s at n=20, 41 s at 30, 31 s at
#: 40, 125 s at 60, 131 s at 80 — the ladder is superlinear with a ratio that has
#: been as bad as four between neighbouring rungs, and n=320 did not finish in
#: forty minutes.
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


def pool(rows=None, scores=None, log=print) -> tuple[list[Candidate], dict]:
    """`(candidates, what was refused)` — everything the solve may seat.

    Four exclusions, each a fact about the candidate rather than a quality bar. A
    row a **person rejected** is refused: the ledger keeps it and carries the
    rejection precisely so that a solver honours it. A row at a regime other than
    the one the pool was made at is refused, because a score read at one geometry
    does not transfer to another. A row with **no picture on disk** is refused —
    its recipe is complete and it could be drawn again, but the diversity rule and
    the group cap are read off pixels, and a candidate no pairwise rule can
    evaluate is one that would be seated untested. A row with no score is refused
    because the objective *is* the score: such a row does not lose, there is
    simply nothing to rank it by.
    """
    stored = candidate_ledger.read() if rows is None else list(rows)
    if not stored:
        raise SolveRefused(
            "the candidate ledger is empty, so there is nothing to solve over. Run "
            "`fractal-wallpapers curate candidate-ledger backfill` first."
        )
    read = candidate_ledger.read_scores() if scores is None else list(scores)
    by_key = {str(row["recipe_key"]): row for row in read}
    out: list[Candidate] = []
    refused = {"rejected": 0, "off_regime": 0, "no_picture": 0, "no_score": 0}
    for row in stored:
        if row.get("rejected"):
            refused["rejected"] += 1
            continue
        if not row.get("at_candidate_regime"):
            refused["off_regime"] += 1
            continue
        if not row.get("picture"):
            refused["no_picture"] += 1
            continue
        reading = by_key.get(str(row["key"]))
        if reading is None or reading.get("p_ge4") is None:
            refused["no_score"] += 1
            continue
        colour = row.get("colour") or {}
        out.append(
            Candidate(
                key=str(row["key"]),
                location=str((row.get("location") or {}).get("key")),
                partition=str(row.get("partition")),
                mode=str((row.get("recipe") or {}).get("mode")),
                group=str(row.get("palette_group")),
                kind=str(reading.get("head")),
                cells=tuple(colour.get("cells") or ()),
                families=tuple(colour.get("families") or ()),
                score=float(reading["p_ge4"]),
                p_ge3=float(reading.get("p_ge3") or 0.0),
                picture=str(row["picture"]),
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

    Signatures are half a mebibyte each and a hundred milliseconds to make, so
    both are kept and kept differently: the **distances** forever, because they
    are one float and a later round asks for the same pair again, and the
    **signatures** under a bound, because an incumbent of a few hundred is a few
    hundred megabytes.
    """

    def __init__(self, candidates: list[Candidate], cache: int = SIGNATURE_CACHE, hold: int = 0):
        self.candidates = candidates
        #: Never smaller than an incumbent, because a round compares every seat
        #: with every other and a cache that forgot one mid-round would make its
        #: signature again for the next seat that asked.
        self.cache = max(1, int(cache), 2 * int(hold))
        self._signatures: dict = {}
        self._order: list = []
        self._distance: dict = {}
        self.made = 0
        self.measured = 0
        self.seconds = 0.0

    def signature(self, at: int):
        if at in self._signatures:
            return self._signatures[at]
        from fractal_wallpapers.palettes import pixel_clouds

        started = time.monotonic()
        made = pixel_clouds.of_picture(picture_of(self.candidates[at]))
        self.seconds += time.monotonic() - started
        self.made += 1
        self._signatures[at] = made
        self._order.append(at)
        while len(self._order) > self.cache:
            self._signatures.pop(self._order.pop(0), None)
        return made

    def distance(self, one: int, other: int) -> float:
        """One pair, measured if it has not been. Through [`measure`], so there is
        one place a distance is made and one seam a caller can replace."""
        pair = (min(one, other), max(one, other))
        if pair not in self._distance:
            self.measure(list(pair))
        return self._distance[pair]

    def rule_for(self, one: int, other: int) -> tuple[str, float]:
        """`(which rule, how far apart this pair has to be)`.

        [`RADIUS`] for any two seated pictures; [`ceiling.TAU_GROUP`] where they
        are two pictures of one palette group, which is that cap's own exemption
        distance and the larger of the two. One test, so a pair is measured once
        whichever rule ends up naming it.
        """
        if self.candidates[one].group == self.candidates[other].group:
            return "group_cap", max(RADIUS, ceiling.TAU_GROUP)
        return "diversity", RADIUS

    def sweep(self, chosen: list[int]) -> dict:
        """`{(i, j): distance}` over every pair of `chosen`, measuring what is new."""
        order = list(chosen)
        wanted = [
            (min(one, other), max(one, other))
            for at, one in enumerate(order)
            for other in order[at + 1 :]
        ]
        if any(pair not in self._distance for pair in wanted):
            self.measure(order)
        return {pair: self._distance[pair] for pair in wanted}

    def measure(self, order: list[int]) -> None:
        """Fill in every unmeasured pair of `order`. **The seam**, and one call.

        A whole sweep rather than a pair at a time, because at two hundred seats
        the cost of this is not the arithmetic — it is moving half a mebibyte per
        signature through memory. Stacking once and walking the stack with
        **views** makes the traffic `n^2/2` rows; re-stacking per row, which is
        what a pair-at-a-time seam forces, makes it `n^2/2` copies of the whole
        stack — at 480 seats, a hundred and twenty gibibytes of memcpy for four
        gibibytes of subtraction. Measured: it is the difference between a sweep
        that finishes and one that does not.

        It is one method for a second reason. The suite replaces it with a lookup,
        so a test about which rule refuses a pair does not have to put two
        pictures on disk to make the pair.
        """
        import numpy

        from fractal_wallpapers.palettes import pixel_clouds

        stack = numpy.stack([self.signature(at) for at in order])
        for at, one in enumerate(order):
            tail = order[at + 1 :]
            keep = [
                which
                for which, other in enumerate(tail)
                if (min(one, other), max(one, other)) not in self._distance
            ]
            if not keep:
                continue
            # A whole tail is a VIEW, which is the point. Anything else copies
            # only the rows still wanted, which is the smaller bill either way.
            others = (
                stack[at + 1 :]
                if len(keep) == len(tail)
                else stack[[at + 1 + which for which in keep]]
            )
            for which, gap in zip(keep, pixel_clouds.distances(stack[at], others), strict=True):
                other = tail[which]
                self._distance[(min(one, other), max(one, other))] = float(gap)
                self.measured += 1

    def violations(self, chosen: list[int]) -> list[dict]:
        """Every pair of `chosen` that is too close, nearest first.

        The whole cost of a cutting-plane round: `len(chosen)` signatures and one
        stacked subtraction per seat over them.
        """
        out = []
        for (one, other), gap in self.sweep(chosen).items():
            rule, bound = self.rule_for(one, other)
            if gap < bound:
                out.append(
                    {
                        "a": self.candidates[one].key,
                        "b": self.candidates[other].key,
                        "distance": round(gap, 6),
                        "wanted": bound,
                        "rule": rule,
                        "pair": (one, other),
                    }
                )
        out.sort(key=lambda pair: pair["distance"])
        return out

    def nearest(self, chosen: list[int], pairs: int = 10) -> list[dict]:
        """The closest pairs among `chosen`, whether or not any rule refuses them.

        The calibration instrument, the same one [`gallery.retro_table`] is: if two
        of these read as one picture, the radius is too small.
        """
        out = [
            {
                "a": self.candidates[one].key,
                "b": self.candidates[other].key,
                "distance": round(gap, 6),
                "same_group": self.candidates[one].group == self.candidates[other].group,
            }
            for (one, other), gap in self.sweep(chosen).items()
        ]
        out.sort(key=lambda pair: pair["distance"])
        return out[: int(pairs)]

    def price(self) -> dict:
        from fractal_wallpapers.palettes import pixel_clouds

        return {
            "signatures_made": self.made,
            "pairs_measured": self.measured,
            "seconds_making_signatures": round(self.seconds, 1),
            "cache": self.cache,
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
        """`[(name, kind, [(indices, bound, what the row is about)])]`."""
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
                (
                    "colour_target",
                    UNDER,
                    [
                        (self.cell_members.get(cell, []), self.rule.wanted(cell, self.n), cell)
                        for cell in sorted(self.targets)
                    ],
                )
            )
        return out

    def _untargeted(self) -> tuple[str, str]:
        """A cell and a family no target has moved, so the record can state the
        **default** allowance through [`ceiling.Rule.allowed`] rather than as a
        second copy of its arithmetic. A target raises the allowance of the cell it
        names and of that cell's family, so reading either off a targeted name
        would report the exception as the rule."""
        from fractal_wallpapers.palettes import dominance

        moved = {dominance.family_of(cell) for cell in self.targets} | set(self.targets)
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
            "objective": [
                f"1. count of seats with raw P(>=4) >= {Q4_BAR}",
                "2. the minimum score among the seated, maximized",
                f"3. the sum of the seated scores, less {PENALTY_PER_SEAT} * n per "
                f"production mode below its floor of {MODE_FLOOR}",
            ],
            "q4_bar": Q4_BAR,
            "q4_basis": Q4_BASIS,
            "radius": RADIUS,
            "tau_group": ceiling.TAU_GROUP,
            "mode_floor": MODE_FLOOR,
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
            },
            "group_cap": (
                f"one seat per palette group, exempt at {ceiling.TAU_GROUP} in the pixel-cloud "
                f"metric — generated as a pairwise row, not as a per-group count"
            ),
        }


def matrices(program: Program, skip=None):
    """The blocks as one sparse `A` with `lower` and `upper`, plus the row index.

    The index is `[(block name, what the row is about, kind)]` in row order, so a
    slack or a dual can be named without rebuilding anything.
    """
    import numpy
    from scipy import sparse

    skip = set(skip or ())
    rows, columns, lower, upper, index = [], [], [], [], []
    at = 0
    for name, kind, block in program.blocks():
        if name in skip:
            continue
        for members, bound, about in block:
            for column in members:
                rows.append(at)
                columns.append(column)
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
        (numpy.ones(len(rows), dtype=numpy.float64), (rows, columns)),
        shape=(at, program.size),
    )
    return matrix, numpy.array(lower), numpy.array(upper), index


# --------------------------------------------------------------------------- #
# The three stages.
# --------------------------------------------------------------------------- #
def lexicographic(program: Program, log=print) -> dict:
    """The three stages, each frozen into the next.

    One column layout throughout — the binaries, then `t`, then one deficit per
    production mode — so the three matrices are the same matrix with rows added.

    Stage 2 wants the **minimum score among the seated**, which is not a linear
    function of the binaries, so it is one continuous `t` and one row per
    candidate: `x_i + t <= score_i + 1`. The big-M is exactly one because every
    score is a probability — an unseated candidate's row reads `t <= score + 1`,
    which cannot bind on a `t` already bounded above by one.

    Stage 3 adds `sum(x in mode m) + d_m >= MODE_FLOOR` and pays `n *
    PENALTY_PER_SEAT` for each unit of `d`. Those rows exist only in this stage:
    the first two ask questions the penalty is not allowed to trade against.
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
    values: dict = {}
    started = time.monotonic()

    def answer(objective, matrix, lower, upper):
        return milp(
            c=objective,
            constraints=LinearConstraint(matrix, lower, upper),
            integrality=numpy.concatenate(
                [numpy.ones(size, dtype=int), numpy.zeros(width - size, dtype=int)]
            ),
            bounds=Bounds(
                lb=numpy.zeros(width),
                ub=numpy.concatenate(
                    [numpy.ones(size), [1.0], numpy.full(len(modes), float(MODE_FLOOR))]
                ),
            ),
        )

    # --- stage 1: how many clear the bar ---------------------------------- #
    objective = numpy.zeros(width)
    objective[:size] = -(above + (TIE_BREAK / max(1, program.n)) * scores)
    first = answer(objective, base, low, high)
    if first.status != 0:
        return {"feasible": False, "status": int(first.status), "message": str(first.message)}
    cleared = int(sum(above[at] for at in range(size) if first.x[at] > 0.5))
    values["above_bar"] = cleared
    log(f"[solve] stage 1: {cleared} of {program.n} clear the q4 bar")

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
    second = answer(objective, second_matrix, second_low, second_high)
    if second.status != 0:
        return {"feasible": False, "status": int(second.status), "message": str(second.message)}
    floor = float(second.x[size])
    values["floor"] = floor
    log(f"[solve] stage 2: floor {floor:.6f}")

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
        [second_low, [floor - EPSILON], numpy.full(len(modes), float(MODE_FLOOR))]
    )
    third_high = numpy.concatenate([second_high, [numpy.inf], numpy.full(len(modes), numpy.inf)])
    penalty = program.n * PENALTY_PER_SEAT
    objective = numpy.zeros(width)
    objective[:size] = -scores
    objective[size + 1 :] = penalty
    third = answer(objective, third_matrix, third_low, third_high)
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


def cutting_plane(
    program: Program, pairs: Pairs, rounds: int = ROUNDS, deadline: float | None = None, log=print
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
        answer = lexicographic(program, log=log)
        if not answer["feasible"]:
            history.append({"round": round_at, "feasible": False, "cuts": len(program.cuts)})
            return {
                "feasible": False,
                "rounds": history,
                "cuts": len(program.cuts),
                "message": answer.get("message"),
            }
        violated = pairs.violations(answer["chosen"])
        history.append(
            {
                "round": round_at,
                "above_bar": answer["values"]["above_bar"],
                "floor": round(answer["values"]["floor"], 6),
                "sum": answer["values"]["sum"],
                "modes_missing": len(answer["values"]["modes_missing"]),
                "violated_pairs": len(violated),
                "seconds": answer["seconds"],
            }
        )
        log(
            f"[solve] round {round_at}: floor {answer['values']['floor']:.4f}, "
            f"{len(violated)} violated pair(s), {len(program.cuts)} cut(s) standing"
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
        program.cuts.extend(pair["pair"] for pair in violated)
        program.generated.extend(violated)
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
    """
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
    read["supply"] = {}
    for name, rows in read["by_block"].items():
        if name not in {"colour_target", "colour_ceiling_cells", "colour_ceiling_families"}:
            continue
        for row in rows["worst"]:
            read["supply"][row["about"]] = _supply_for(program, row["about"])
    if "cardinality" in read["by_block"]:
        read["supply"]["__the_pool__"] = _partitions(program, range(program.size))
    return read


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
    """The ceiling's constants and targets, with no lens.

    [`ceiling.Rule`] holds the allowance arithmetic and the target-to-family
    summation, and both are wanted here — a target raises the allowance of the
    cell it names and of that cell's family, and a second derivation of that
    would be a second answer. The **lens** is what a sequential seating uses to
    read a candidate's colour off its picture, and this program already has every
    colour on its rows, so there is nothing for one to do.
    """
    return ceiling.Rule(lens=None, targets=dict(targets or {}))


def solve(
    n: int = candidate_ledger.FIRST_SOLVE,
    candidates: list[Candidate] | None = None,
    targets: dict | None = None,
    locations: int | None = None,
    log=print,
) -> dict:
    """One gallery, solved. The record is the return value; nothing is written.

    `locations` truncates the reachable pool to that many strongest places; `None`
    is the whole ledger. `targets` is `{cell: fraction}` and is what makes a
    program hard enough to be infeasible on purpose.
    """
    _scipy()
    from fractal_wallpapers import engine

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
        modes=tuple(engine.production_modes()),
        targets=dict(targets or {}),
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

    pairs = Pairs(available, hold=int(n))
    answer = cutting_plane(program, pairs, log=log)
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
    """
    reduced = Program(
        candidates=program.candidates,
        n=program.n,
        rule=program.rule,
        modes=program.modes,
        targets=program.targets,
        cuts=list(program.cuts),
        exact_cardinality=False,
    )
    log("[solve] re-solving at <= n so the fillable seats are filled")
    answer = cutting_plane(reduced, pairs, log=log)
    if not answer["feasible"]:
        return {"filled": 0, "unfilled": program.n, "message": answer.get("message")}
    return {
        "filled": len(answer["chosen"]),
        "unfilled": program.n - len(answer["chosen"]),
        "values": answer["values"],
        "seated": [_seat(reduced, at, pairs, answer["chosen"]) for at in answer["chosen"]],
        "distribution": distribution(reduced, answer["chosen"]),
    }


def _seat(program: Program, at: int, pairs: Pairs, chosen: list[int]) -> dict:
    candidate = program.candidates[at]
    others = [other for other in chosen if other != at]
    nearest = min((pairs.distance(at, other) for other in others), default=None)
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
            taken = sum(1 for at in members if at in picked)
            if (kind in {OVER, EXACT} and taken >= bound) or (kind == UNDER and taken == bound):
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
            gaps = pairs.sweep([at, *chosen])
            close = [
                other
                for other in chosen
                if gaps[(min(at, other), max(at, other))] < pairs.rule_for(at, other)[1]
            ]
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
#: What the twenty are rendered at. [`gallery.RELEASE_REGIME`] and not a second
#: opinion about it: a solved gallery and a walked one ship the same pixels, and
#: the whole claim of this module is that only the *choosing* changed.
def release_regime():
    from fractal_wallpapers.curation import gallery

    return gallery.RELEASE_REGIME


def render_seats(name: str, record: dict, workers: int = 4, regime=None, log=print) -> dict:
    """Render every seat of a solve at release geometry. Mutates `record`.

    The same two facts a pass's release leg records and for the same reasons: the
    **geometry lands on each seat**, because the default has moved once already
    and a sheet that captioned every picture with today's default would relabel
    every wallpaper an earlier solve made; and the autolevel stamp is the *release
    render's own*, never the candidate's, because they are two renders and
    showing one under the other's caption is how a page says something false with
    every field on it true.

    No re-score. The release picture is the same recipe as the candidate the
    decision was taken on, at another size, and the judge's floors were fit on
    640x360 candidate renders.
    """
    from fractal_wallpapers.curation import release

    regime = release_regime() if regime is None else regime
    rows = {str(row["key"]): row for row in candidate_ledger.read()}
    where = solve_dir(name) / "release"
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
        "workers": int(workers),
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

    The frame is read off the file, [`gallery._at_regime`]'s rule: presence
    stopped being the whole test the day the regime became a parameter.
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
            f"<p class='lede'>The calibration instrument. The radius refuses anything under "
            f"{RADIUS} in the pixel-cloud metric, and {ceiling.TAU_GROUP} inside one palette "
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
    """Where a seat's or a near miss's candidate render is, off the stored name."""
    name = row.get("picture")
    return None if not name else Path(rehome(name))


def _number(value) -> str:
    return "-" if value is None else f"{float(value):.4f}"


# --------------------------------------------------------------------------- #
# The three cheap experiments.
# --------------------------------------------------------------------------- #
#: The sizes the full sweep visits. Geometric, because the question is *where* a
#: constraint starts binding rather than at exactly which seat, and a linear walk
#: to five hundred is four hundred and eighty solves to find out.
#:
#: It stops at 80, which is **where this project has actually measured**, and the
#: reason is the pairwise rules rather than HiGHS. A round holds one 512 KiB
#: signature per seat and measures every pair of them, so the loop's cost is
#: quadratic in `n` — and the *number of rounds* grows with `n` too, because a
#: larger incumbent lands on more near-duplicate pairs. Measured on the pool: 2
#: rounds and 1 generated row at n=20, 4 and 11 at n=30, 3 and 8 at n=40, 12 and
#: 68 at n=60. n=320 did not finish in forty minutes.
#:
#: Past here the cost of the read is the finding, and it wants its own study
#: rather than a longer default. A caller with an afternoon passes its own sizes.
#: [`relaxation_ladder`] carries the same question to the top in seconds, on every
#: block except the two pairwise ones.
SWEEP = (20, 30, 40, 60, 80)


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
    from fractal_wallpapers import engine

    if candidates is None:
        candidates, _refused = pool(log=log)
    modes = tuple(engine.production_modes())
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
        pairs = Pairs(candidates, hold=int(size))
        started = time.monotonic()
        read = relaxation(program, log=log)
        gave_up = None
        if not read["feasible"]:
            answer = {"feasible": False, "rounds": [], "cuts": 0}
        else:
            try:
                answer = cutting_plane(program, pairs, deadline=deadline, log=log)
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
    from fractal_wallpapers import engine

    if candidates is None:
        candidates, _refused = pool(log=log)
    modes = tuple(engine.production_modes())
    out = []
    for multiple in TRUNCATIONS:
        keep = None if multiple is None else max(int(n), int(round(multiple * n)))
        reachable = strongest_locations(candidates, keep)
        available = within(candidates, reachable)
        program = Program(candidates=available, n=int(n), rule=rule_for(), modes=modes)
        pairs = Pairs(available, hold=int(n))
        started = time.monotonic()
        read = relaxation(program, log=log)
        answer = (
            cutting_plane(program, pairs, log=log)
            if read["feasible"]
            else {"feasible": False, "cuts": 0, "rounds": []}
        )
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
    "Candidate",
    "EPSILON",
    "MODE_FLOOR",
    "NEAR_MISSES",
    "PENALTY_PER_SEAT",
    "Pairs",
    "Program",
    "Q4_BAR",
    "Q4_BASIS",
    "RADIUS",
    "ROUNDS",
    "SCHEMA",
    "SWEEP",
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
    "near_misses",
    "picture_of",
    "picture_of_row",
    "pool",
    "read_record",
    "relaxation_ladder",
    "relaxation",
    "release_regime",
    "render_seats",
    "rule_for",
    "shortage",
    "solve",
    "solve_dir",
    "strongest_locations",
    "sweep",
    "truncation",
    "within",
    "write_record",
]
