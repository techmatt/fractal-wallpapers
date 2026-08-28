"""Buy width at one place, and measure what it buys against the head's rank.

[`curation.mine`] priced a location three ways at three candidates each and left
one question open, because at a second a candidate it could not afford to ask
it: **how deep does a location go?** A shared field made width nearly free on
the modes that have one — 0.165 s a candidate at forty against 0.976 s at one —
so this module spends that on the two numbers the route to a thousand seatable
places rests on.

## What is measured, and what it is conditional on

Forty candidates at a location, three draws:

* **NEAR-BAND** — a location whose best **field-mode** candidate already sits in
  `[SEATING_BAR, PRIMED_BAR)`. The cheapest known ore, and the arm that says how
  much further a place that has already shown something will go. Its mode is
  held at the incumbent's, so what varies is the palette and nothing else.
* **RANKED-BANDS** — never-opened locations drawn **across the whole of the
  location head's rank range within partition**, in equal-sized bands. The
  earlier mine took the top of the list and its validation run drew below it,
  which is two points; this produces the curve they are two points on.
* **FLAT** — never-opened, no quality conditioning, matched to the ranked draw's
  per-partition counts. The base rate, and the anchor under the bottom band.

**Every conclusion here is conditional on field modes.** A composite at forty
candidates is about 175 s a location and would spend the whole budget on one
arm's worth of places, so the roster is [`field_modes`] — the shareable modes,
less what standing rulings have taken out of the standard draw. Nothing here
says what a composite would have done.

**The near band and the breadth draws do not run the same roster.** The near
band holds an incumbent's mode; the breadth draws cycle. So a mode that pays at
depth and not at width is dropped from breadth alone, by [`BREADTH_DEMOTED`],
and keeps its near-band seat.

## The sequence is recorded whole

Every candidate is written to [`SEQUENCE_NAME`] as it lands, carrying its
location, its rank, its band, its mode and its `k`. A cumulative curve at any
`k` below the width reached is then arithmetic over that file, which is the
point: the run is expensive and re-running it to ask about `k = 17` would be
absurd.
"""

from __future__ import annotations

import collections
import json
import math
import random
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, framing, hunt, mine, recipes
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree a depth run's own output lands in, under the regenerable tree.
UNIT = "depth"

#: The two row files are [`curation.hunt`]'s byte for byte, so [`merge`] is that
#: module's upsert over these paths rather than a second one to keep honest.
ROWS_NAME = hunt.ROWS_NAME
SCORES_NAME = hunt.SCORES_NAME
RECORD_NAME = "depth.json"
SEQUENCE_NAME = "sequence.jsonl"
PICTURES = hunt.PICTURES
FIELDS = hunt.FIELDS

#: The two heights every readout here reports at, [`curation.mine`]'s, because
#: they are the same two questions and one set of scores answers each.
PRIMED_BAR = mine.PRIMED_BAR
SEATING_BAR = mine.SEATING_BAR

#: The draws, in the spelling every row and every tally uses. The first three
#: are the measurement; [`FLOOR`] is what a **production** run adds once the
#: measurement is in, and a measuring run leaves it empty.
NEAR = "near_band"
RANKED = "ranked_bands"
FLAT = "flat"
FLOOR = "mode_floor"
AIMED = "conditioned"
DRAWS = (NEAR, RANKED, FLAT, FLOOR, AIMED)

#: The draws a *measuring* run takes. [`FLOOR`] is deliberately not one of them:
#: it goes to the modes a census says are short of seats, which is a production
#: decision and would put a hand-picked mode mix into a curve about depth.
MEASURING = (NEAR, RANKED, FLAT)

#: What share of the render budget each draw is given. The ranked draw takes
#: half because it is the only one that produces a *curve* — its answer is
#: spread over [`RANK_BANDS`] bands inside each partition and every one of them
#: needs locations — where the other two each report a single rate.
SHARES = {NEAR: 0.25, RANKED: 0.50, FLAT: 0.25, FLOOR: 0.0, AIMED: 0.0}

#: How many palettes one (location, mode) pair gets in the [`FLOOR`] draw. Small
#: on purpose: that draw is short of *modes* and not of width, and the whole
#: point of spending it at a place already over the seating bar is that a few
#: shots there are worth many at a fresh one.
FLOOR_WIDTH = 4

#: How many candidates one location is offered. The width a shared field made
#: affordable, and the `k` the earlier mine's marginal curve was still climbing
#: at when it ran out at twelve.
WIDTH = 40

#: How many bands the head's rank range inside one partition is cut into. Equal
#: **counts**, not equal scores: the head's score distribution is not uniform and
#: a cut on the score would put most of a partition in one band.
RANK_BANDS = 10

#: Modes out of the standard draw by a standing ruling rather than by the
#: engine's own tier. `trap_circle` is niche as of checkpoint 84 — 2 threes and
#: 0 fours in 117 labeled rows — and the catalogue still calls it production, so
#: the ruling is applied at the draw. Its existing material stands.
DEMOTED = ("trap_circle",)

#: Modes the **near band** may hold but the two breadth draws do not cycle. A
#: mode lands here when it pays at depth and not at width, which is a different
#: ruling from [`DEMOTED`]: the location whose incumbent is one of these still
#: enters the near-band draw and still gets its forty palettes.
#:
#: `tia` is the first. Measured on `dc1`/`dc2` (2026-08-27): in breadth at k=20
#: it cleared the seating bar at .0208 against `smooth`'s .0515 and
#: `exp_smoothing`'s .0539, and at k=40 it cleared .0559 — level with them. Its
#: clears concentrate at few places, so a narrow set at many places wastes it.
#: It is also the dearest dump on the three-mode roster, 0.898 s against
#: `smooth`'s 0.354, and the field is dumped once per (location, mode): over an
#: eight-hour run at this shape that is about an hour of dumping bought back.
BREADTH_DEMOTED = ("tia",)

#: The seed every draw here is taken under unless a caller names another.
DEFAULT_SEED = 20260827

#: How long a depth run may spend **rendering**, in seconds.
BUDGET_SECONDS = 5400.0

#: How much longer the plan is than the budget prices it at. [`mine.PLAN_HEADROOM`]'s
#: reason, and more of it: the rate this run is sized off is a per-candidate mean
#: over a population whose cheap end and dear end differ by three times, and the
#: surplus of a plan is never started.
PLAN_HEADROOM = 1.6


class DepthRefused(RuntimeError):
    """A depth run cannot be planned off what this checkout holds."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def depth_dir(name: str) -> Path:
    """One depth run's own subtree: its rows, its scores, its sequence, its record."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    """The ledger rows this run has made so far, appended as each lands."""
    return depth_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    """The sidecar rows this run has made so far, appended as each lands."""
    return depth_dir(name) / SCORES_NAME


def sequence_path(name: str) -> Path:
    """One row a candidate, **in the order it was made**. The whole deliverable."""
    return depth_dir(name) / SEQUENCE_NAME


def record_path(name: str) -> Path:
    """What the run reports about itself: the plan, the price, the curves."""
    return depth_dir(name) / RECORD_NAME


def fields_dir(name: str) -> Path:
    """Where this run's dumped fields are, one per (location, mode)."""
    return depth_dir(name) / FIELDS


def pictures_dir(name: str) -> Path:
    """Where this run's candidate renders are, one per recipe key."""
    return depth_dir(name) / PICTURES


# --------------------------------------------------------------------------- #
# The roster.
# --------------------------------------------------------------------------- #
def field_modes(demoted=DEMOTED) -> list[str]:
    """Every production mode a dumped field can serve, less the demoted ones.

    Asked of [`colorize.shareable`] rather than filtered on a kind spelled here,
    because whether a coloring has one scalar field behind it is the engine's
    word and a mode added to the catalogue must not need an edit here to be
    drawn.
    """
    from fractal_wallpapers.curation import colorize

    out = [mode for mode in mine._production_modes() if colorize.shareable(mode)]
    return [mode for mode in out if mode not in set(demoted)]


# --------------------------------------------------------------------------- #
# One intention.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Shot:
    """One candidate a depth run intends to make, before anything is rendered.

    [`mine.Unit`]'s members, so [`mine.make`] and [`hunt.Maker.recipe_for`] read
    this the way they read that one, plus the two this run exists to report
    against: where the location stood on the head's rank, and which band of that
    rank range it was drawn from.
    """

    arm: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: Which candidate this is at its location, counting only this run's own.
    k: int
    #: The rank band, or `incumbent` where the draw was not a rank draw at all.
    band: str
    #: The location's rank **within its partition**, 1 for the head's best, and
    #: `None` where the sidecar could not score it.
    rank: int | None = None
    #: That rank as a fraction of the partition's population, which is the axis
    #: the curve is drawn against — ranks are not comparable across partitions
    #: of different sizes and fractions are.
    rank_fraction: float | None = None
    #: The codebook cell the palette was drawn **for** on the [`AIMED`] arm, and
    #: `None` on every other. [`hunt.Try.cell`]'s member and its warning: a prior
    #: about the map, never a claim about the picture, whose colour is read off
    #: its own render like every other candidate's.
    cell: str | None = None

    def named(self) -> dict:
        """This intention as the ledger row carries it.

        `k` and the two rank members ride along for [`mine.Unit.named`]'s
        reason: this run's `sequence.jsonl` lives under the regenerable tree and
        the ledger does not, and a `k`-dependent correction — the winner's-curse
        multiplier above all — cannot be applied to a row that has forgotten
        which candidate at its location it was.
        """
        out = {
            "leg": self.arm,
            "mode": self.mode,
            "colormap": self.colormap,
            "band": self.band,
            "k": self.k,
            "rank": self.rank,
            "rank_fraction": self.rank_fraction,
        }
        if self.cell is not None:
            out["drawn_for"] = self.cell
        return out


# --------------------------------------------------------------------------- #
# The three draws.
# --------------------------------------------------------------------------- #
def best_field_by_location(rows: list, scores: dict, roster: set) -> dict:
    """`{location: {best, best_mode, partition, count}}` over **field modes only**.

    The near-band draw holds the incumbent's mode, and a location whose best
    candidate is a composite cannot hand one over: there is no field to dump and
    forty candidates there would cost what this whole run is budgeted at. So the
    band is read off the best candidate the location holds *in a mode this run
    can afford*, and a location with none is not in the draw.
    """
    out: dict = {}
    for row in rows:
        mode = str((row.get("recipe") or {}).get("mode"))
        if mode not in roster:
            continue
        key = str((row.get("location") or {})["key"])
        score = float(scores.get(str(row["recipe_key"]), 0.0))
        held = out.setdefault(
            key,
            {"best": -1.0, "count": 0, "partition": str(row.get("partition")), "best_mode": None},
        )
        held["count"] += 1
        if score >= held["best"]:
            held["best"] = score
            held["best_mode"] = mode
    return out


def near_places(best_field: dict, index: dict, seed: int, count: int) -> list:
    """`count` locations whose best field candidate sits in `[SEATING_BAR, PRIMED_BAR)`.

    Round-robin over partitions for [`hunt.spread`]'s reason: the price table is
    per partition and a draw that spent itself on one of them prices one of them.
    """
    pools: dict = {}
    for key, held in best_field.items():
        if not (SEATING_BAR <= held["best"] < PRIMED_BAR) or key not in index:
            continue
        pools.setdefault(held["partition"], []).append({**held, "key": key})
    pools = {name: sorted(rows, key=lambda row: str(row["key"])) for name, rows in pools.items()}
    return hunt.spread(pools, count, seed)


def ranked_bands(pools: dict, head_scores: dict, bands: int = RANK_BANDS) -> dict:
    """`{partition: [band0, band1, ...]}` — each partition's pool cut into rank bands.

    Band 0 holds the head's best in that partition and the last band its worst.
    A location the sidecar cannot score sorts last rather than being dropped, so
    this pool and the flat draw's pool are the same pool: a dropped row would
    unmatch the control silently. Every row comes back carrying its `rank` and
    its `rank_fraction`, because a band is a convenience for the draw and the
    rank is what the curve is reported against.
    """
    out: dict = {}
    for name, held in pools.items():
        ordered = sorted(
            held,
            key=lambda row: (
                -float((head_scores.get(str(row["key"])) or {}).get("p_ge3") or -1.0),
                str(row["key"]),
            ),
        )
        total = len(ordered)
        annotated = [
            {
                **row,
                "rank": at + 1,
                "rank_fraction": round((at + 1) / max(1, total), 6),
                "head_p_ge3": float((head_scores.get(str(row["key"])) or {}).get("p_ge3") or -1.0),
            }
            for at, row in enumerate(ordered)
        ]
        cut = [[] for _band in range(int(bands))]
        for at, row in enumerate(annotated):
            at_band = min(int(bands) - 1, at * int(bands) // max(1, total))
            row["rank_band"] = at_band
            cut[at_band].append(row)
        out[name] = cut
    return out


def banded_places(banded: dict, seed: int, count: int, weights: dict | None = None) -> list:
    """`count` never-opened locations spread evenly over every (partition, band) cell.

    Round-robin over the cells rather than proportional to what each holds, for
    the same reason [`hunt.spread`] is round-robin over partitions: what is being
    bought here is a **curve**, and a draw proportional to stock would put nine
    tenths of it in the bands the pool happens to be fat in and leave the ends —
    which are the whole question — with two locations each.
    """
    cells = []
    for name in sorted(banded):
        for at, held in enumerate(banded[name]):
            if held:
                drawn = random.Random(hunt.seed_of(seed, name, at)).sample(held, len(held))
                cells.append(((name, at), drawn))
    order = _weighted_order([key for key, _held in cells], weights)
    stock = dict(cells)
    at_cell = dict.fromkeys(stock, 0)
    out: list = []
    while len(out) < count:
        took = False
        for key in order:
            if len(out) >= count:
                break
            held = stock[key]
            if at_cell[key] < len(held):
                out.append(held[at_cell[key]])
                at_cell[key] += 1
                took = True
        if not took:
            break
    return _interleave_by_partition(out)


def _weighted_order(cells: list, weights: dict | None) -> list:
    """One round of the draw, each band appearing as often as its weight.

    Unweighted, every (partition, band) cell gets one turn a round, which is the
    even spread a **measurement** wants. A production run knows what each band is
    worth — the measuring run reports primed-per-hour by band — and buys more
    turns where it pays, which is [`hunt._turns`]'s work order one axis down.
    Weights are per band and not per partition: what a depth run measures is a
    band's rate pooled over partitions, and weighting per partition would spend a
    measurement nobody has.
    """
    if not weights:
        return list(cells)
    out: list = []
    highest = max(_turns_for(weights, at) for _name, at in cells)
    for turn in range(max(1, highest)):
        for key in cells:
            if turn < _turns_for(weights, key[1]):
                out.append(key)
    return out or list(cells)


def _turns_for(weights: dict, at: int) -> int:
    """How many turns a round one band gets. Never negative, and 0 skips it."""
    return max(0, int(round(float(weights.get(_band_name(at), 1.0)))))


def _band_name(at: int) -> str:
    """A band's index as the weight table and the row both spell it."""
    return f"band{int(at):02d}"


def flat_places(banded: dict, taken: set, seed: int, want: dict) -> list:
    """Never-opened locations with no quality conditioning, `want` many per partition.

    Drawn from the same annotated pool as the ranked draw so every flat location
    carries its rank too — the control is a control on *how the place was
    chosen*, and knowing where the uniform draw happened to land on the rank axis
    is what lets the two be read against each other rather than only compared.
    """
    out: list = []
    for name in sorted(banded):
        held = [row for band in banded[name] for row in band if str(row["key"]) not in taken]
        take = int(want.get(name, 0))
        if take <= 0 or not held:
            continue
        out += random.Random(hunt.seed_of(seed, name)).sample(held, min(take, len(held)))
    return _interleave_by_partition(out)


def strongest_bands(banded: dict, keep: int | None) -> dict:
    """`banded` cut to its `keep` strongest rank bands. `None` keeps every band.

    What restricts the two **matched** draws — [`FLAT`] and [`AIMED`] — to one
    stretch of the head's rank axis. The ranked draw is deliberately not cut:
    its whole job is the curve end to end, and a curve measured over half the
    axis is a different measurement wearing the same name.

    The cut is by band and not by rank, so it lands on the same boundary in
    every partition however differently the partitions are stocked: with ten
    bands, `keep=5` is each partition's own top half.
    """
    if keep is None:
        return banded
    keep = max(1, int(keep))
    return {name: list(held)[:keep] for name, held in banded.items()}


def spread_over_partitions(banded: dict, places: int) -> dict:
    """`places` locations spread round-robin over the partitions that hold stock.

    The partition mix a matched draw takes when there is **no ranked draw to
    inherit one from**. Sizing the two breadth controls off the ranked draw's
    realized counts is right while a run is measuring the curve and buying the
    controls beside it; a run that is only the two matched arms would size them
    off a draw it did not take, which is a mix of zero.

    Round-robin and not proportional, for [`banded_places`]'s reason: what is
    being bought is a comparison between two arms, and a draw proportional to
    stock would put most of both arms in whichever partition the pool happens to
    be fat in and read as a fact about the colour.
    """
    stock = {name: sum(len(band) for band in held) for name, held in banded.items()}
    out: dict = dict.fromkeys(sorted(name for name, held in stock.items() if held), 0)
    if not out:
        return {}
    given = 0
    while given < int(places):
        took = False
        for name in list(out):
            if given >= int(places):
                break
            if out[name] < stock[name]:
                out[name] += 1
                given += 1
                took = True
        if not took:
            break
    return {name: count for name, count in out.items() if count}


def proven_places(best: dict, index: dict, seed: int, count: int, bar: float = SEATING_BAR):
    """`count` locations that already hold a candidate over `bar`, spread over partitions.

    The [`FLOOR`] draw's population. A mode short of seats is short of **good**
    material in that mode, and the cheapest place to look for it is a location
    that has already proved it can carry a wallpaper — the earlier mine measured
    a known-good place clearing at 2.7 times the near band's rate, and the near
    band at four times a fresh one. What is being varied here is the mode, so the
    place is held at the best evidence available.
    """
    pools: dict = {}
    for key, held in best.items():
        if float(held.get("best", -1.0)) < float(bar) or key not in index:
            continue
        pools.setdefault(str(held.get("partition")), []).append({**held, "key": key})
    pools = {name: sorted(rows, key=lambda row: str(row["key"])) for name, rows in pools.items()}
    return hunt.spread(pools, count, seed)


def plan_floor(places: list, modes: list, taken: dict, maps: list, seed: int, width: int) -> list:
    """`width` palettes in each named mode at each proven place, modes cycled.

    Cycled rather than blocked for [`plan_cycled_modes`]'s reason and one more:
    a run cut short by the clock should have spent itself evenly over the modes
    it was sent to serve, not filled the first two of them.
    """
    out: list = []
    modes = list(modes)
    if not modes:
        return out
    for row in places:
        key = str(row["key"])
        per_mode: dict = {}
        for at in range(int(width) * len(modes)):
            mode = modes[at % len(modes)]
            if mode not in per_mode:
                spent = taken.get((key, mode), set())
                free = [name for name in maps if name not in spent]
                pick = random.Random(hunt.seed_of(seed, key, mode))
                per_mode[mode] = pick.sample(free, min(int(width), len(free)))
            turn = at // len(modes)
            if turn >= len(per_mode[mode]):
                continue
            out.append(
                Shot(
                    arm=FLOOR,
                    location=key,
                    partition=str(row["partition"]),
                    mode=str(mode),
                    colormap=str(per_mode[mode][turn]),
                    k=at + 1,
                    band="proven",
                    rank=None,
                    rank_fraction=None,
                )
            )
    return out


def deficient_modes(rows: list, scores: dict, floor: int = 10, bar: float = SEATING_BAR) -> dict:
    """`{mode: seats short of `floor`}` off the ledger as it stands.

    A seat is a **distinct location** holding a candidate over `bar` in that mode,
    which is the unit the per-mode floor is stated in — a mode with ten clearing
    candidates at one place has one seat and not ten, because a collection seats
    a location once.
    """
    seats: dict = {}
    for row in rows:
        mode = str((row.get("recipe") or {}).get("mode"))
        if float(scores.get(str(row["recipe_key"]), 0.0)) < float(bar):
            continue
        seats.setdefault(mode, set()).add(str((row.get("location") or {})["key"]))
    out: dict = {}
    for mode in mine._production_modes():
        if mode in set(DEMOTED):
            continue
        short = int(floor) - len(seats.get(mode) or ())
        if short > 0:
            out[mode] = short
    return dict(sorted(out.items(), key=lambda item: -item[1]))


def _interleave_by_partition(places: list) -> list:
    """One place from each partition in turn, in partition-name order."""
    pools: dict = {}
    for row in places:
        pools.setdefault(str(row["partition"]), []).append(row)
    order = sorted(pools)
    at = dict.fromkeys(order, 0)
    out: list = []
    while len(out) < len(places):
        took = False
        for name in order:
            if at[name] < len(pools[name]):
                out.append(pools[name][at[name]])
                at[name] += 1
                took = True
        if not took:
            break
    return out


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
def plan_held_mode(places: list, taken: dict, maps: list, seed: int, width: int) -> list:
    """`width` fresh palettes at each place, at the mode its best candidate was drawn in.

    The mode is held because this arm is about the palette: a draw that moved the
    mode as well would measure the two together and could not say which of them
    the k-th candidate bought. Maps already spent at that (location, mode) are
    skipped — the recipe key would collide, the loop would refuse the duplicate,
    and the arm would report a `k` it never reached.
    """
    out: list = []
    for row in places:
        key = str(row["key"])
        mode = str(row.get("best_mode") or "")
        if not mode or mode == "None":
            continue
        spent = taken.get((key, mode), set())
        free = [name for name in maps if name not in spent]
        drawn = random.Random(hunt.seed_of(seed, key, mode)).sample(free, min(width, len(free)))
        for at, colormap in enumerate(drawn, start=1):
            out.append(
                Shot(
                    arm=NEAR,
                    location=key,
                    partition=str(row["partition"]),
                    mode=mode,
                    colormap=str(colormap),
                    k=at,
                    band="incumbent",
                    rank=row.get("rank"),
                    rank_fraction=row.get("rank_fraction"),
                )
            )
    return out


def flat_maps(seed: int, mode: str, width: int, maps: list) -> list:
    """`width` palettes for one (location, mode), uniform over the pool.

    What every breadth arm has always drawn. The mode is taken and unused: a map
    supply is a function of the pair, and [`aimed_maps`] would need it if the
    carrier table were ever read per mode.
    """
    return random.Random(seed).sample(maps, min(len(maps), int(width)))


def aimed_maps(cell: str):
    """A map supply for [`plan_cycled_modes`] biased toward one codebook cell.

    [`hunt.conditioned_maps`] over the **same pool** the flat draw samples: the
    carrier table weights the draw by each map's mean share of the cell, and the
    re-draw on a bumped seed is what stops one map meeting a target alone. A
    filter over the pool and not a second pool.

    **Draw-biased, verdict-measured.** The carrier table is a prior about a map
    and never a claim about a picture: group members disagree on their dominant
    cell in 120 of 195 reads, and `PRGn` has made a green seat as a non-carrier.
    So nothing here gates on the table — the candidate is rendered, the dominance
    is read off its own pixels like every other candidate's, and what came out
    dominant is what counts. A 60% hit rate costs 1.6x the renders on this arm
    and nothing anywhere else.

    A cell no map in the pool carries falls back to the flat draw rather than
    planning nothing: an arm that silently emptied would be reported as a share
    that bought no candidates, which reads as a budget that ran out.
    """

    def draw(seed: int, mode: str, width: int, maps: list) -> list:
        drawn = hunt.conditioned_maps(str(cell), int(width), list(maps), seed)
        return drawn or flat_maps(seed, mode, width, maps)

    return draw


def plan_cycled_modes(
    arm: str, places: list, roster: list, maps: list, seed: int, width: int, draw=None, cell=None
):
    """`width` candidates at each place, **cycling the roster** rather than blocking it.

    Cycled and not blocked, and that is the whole of it. A location given seven
    smooths and then seven stripes would have its per-candidate clear rate move
    with `k` for a reason that is not depth at all — the modes do not clear
    alike, and the first block's mode would own the head of every curve. Cycling
    makes the k-th candidate a draw from the same mixture at every k, which is
    the only shape in which "does the clear rate stay flat in k" is a question
    about palettes.

    The palettes are drawn without replacement **within** a (location, mode), so
    no recipe collides, and the roster is walked from a per-location offset so
    that `k = 1` is not the same mode everywhere.

    `draw(key, mode, width, maps)` is the palette ask, and the **whole** of what a
    conditioned run changes. Unsaid it is [`flat_maps`], the uniform sample this
    arm has always taken; [`aimed_maps`] biases the same pool toward one cell.
    Everything else about the arm — the places, the cycle, the width, the seed —
    is the same draw, which is what makes an aimed arm and a flat arm comparable
    at all.
    """
    out: list = []
    roster = list(roster)
    draw = flat_maps if draw is None else draw
    for row in places:
        key = str(row["key"])
        rng = random.Random(hunt.seed_of(seed, key))
        offset = rng.randrange(len(roster)) if roster else 0
        per_mode: dict = {}
        for at in range(int(width)):
            mode = roster[(offset + at) % len(roster)]
            if mode not in per_mode:
                per_mode[mode] = draw(hunt.seed_of(seed, key, mode), mode, int(width), maps)
            spent = per_mode[mode]
            turn = at // len(roster)
            if turn >= len(spent):
                continue
            out.append(
                Shot(
                    arm=arm,
                    location=key,
                    partition=str(row["partition"]),
                    mode=str(mode),
                    colormap=str(spent[turn]),
                    k=at + 1,
                    band=f"band{int(row.get('rank_band', -1)):02d}",
                    rank=row.get("rank"),
                    rank_fraction=row.get("rank_fraction"),
                    cell=None if cell is None else str(cell),
                )
            )
    return out


def weave(plans: dict, shares: dict | None = None) -> list:
    """The draws woven together in proportion, so a truncation truncates all alike.

    [`mine.weave`] over this module's draw names: every prefix of the woven plan
    holds the three in their intended proportion, so a run cut short at any point
    has spent its budget the way a run that finished would have. A location's own
    candidates keep their order inside that, which is what makes the sequence
    file a sequence.
    """
    shares = {**SHARES, **dict(shares or {})}
    placed = []
    for arm in DRAWS:
        held = plans.get(arm) or []
        share = float(shares.get(arm, 0.0)) or 1e-9
        placed += [((at + 0.5) / share, arm, at, shot) for at, shot in enumerate(held)]
    return [shot for _at, _arm, _index, shot in sorted(placed, key=lambda item: item[:3])]


def build_plan(
    world: dict,
    *,
    seed: int,
    rate: float,
    budget: float,
    width: int = WIDTH,
    near_width: int | None = None,
    bands: int = RANK_BANDS,
    top_bands: int | None = None,
    roster: list | None = None,
    breadth_demoted: tuple | list = BREADTH_DEMOTED,
    cell: str | None = None,
    shares: dict | None = None,
    band_weights: dict | None = None,
    floor_modes: list | None = None,
    floor_seats: int = 10,
    floor_width: int = FLOOR_WIDTH,
    log=print,
) -> tuple:
    """The draws sized off a per-candidate rate. `(plan, shape)`.

    `shares`, `band_weights` and `floor_modes` are what turn a **measuring** run
    into a **production** one. Unsaid, this takes the three measuring draws with
    every rank band on equal turns, which is the shape a curve wants. Said, the
    ranked draw buys extra turns in the bands that were measured to pay and the
    [`FLOOR`] draw takes a deliberate slice for the modes a census says are short
    of seats.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import dominance

    roster = list(roster if roster is not None else field_modes())
    if not roster:
        raise DepthRefused(
            "no shareable production mode survives the demotions, so a depth run has "
            "nothing it can afford to render forty of."
        )
    # The near band holds an incumbent's mode and the two breadth draws cycle a
    # roster, so they do not have to be the same set. [`BREADTH_DEMOTED`] is the
    # difference: a mode that pays at depth and not at width stays eligible as an
    # incumbent and stops being cycled at forty fresh places.
    breadth = [mode for mode in roster if mode not in set(breadth_demoted)]
    if not breadth:
        raise DepthRefused(
            f"every mode on the roster {sorted(roster)} is demoted out of breadth by "
            f"{sorted(breadth_demoted)}, so the ranked and flat draws have nothing to "
            f"cycle. Narrow the demotion or widen --modes."
        )
    maps = list(colorize.pool(seed))
    shares = {**SHARES, **dict(shares or {})}
    if shares.get(AIMED) and not cell:
        raise DepthRefused(
            f"a {AIMED!r} share of {shares[AIMED]} was given and no --cell to aim it at. "
            f"The arm is the flat draw with its palette ask biased toward one codebook "
            f"cell; without the cell it would be a second flat draw wearing another name."
        )
    if cell and not shares.get(AIMED):
        raise DepthRefused(
            f"--cell {cell} was given and the {AIMED!r} draw has no share of the budget, "
            f"so nothing would be aimed at it. Pass --shares with a {AIMED!r} entry."
        )
    if cell and str(cell) not in set(dominance.cells()):
        raise DepthRefused(
            f"{cell!r} is not a codebook cell. A misspelt cell would plan an aimed arm "
            f"no map carries and report it as a draw that bought nothing."
        )
    planned = PLAN_HEADROOM * float(budget) / max(float(rate), 1e-6)
    want = {arm: int(planned * float(share)) for arm, share in shares.items()}
    short = deficient_modes(world["rows"], world["ledger_scores"], floor=int(floor_seats))
    wanted_floor_modes = list(floor_modes if floor_modes is not None else short)
    best_field = best_field_by_location(world["rows"], world["ledger_scores"], set(roster))
    # A draw given no share is not drawn at all. `weave` would sort a zero-share
    # draw's candidates to the end where nothing would ever start them, but the
    # plan would still say it holds them and the record would report locations
    # this run never intended to open.
    # The two draws are priced apart because they *are* priced apart: a near-band
    # location holds its mode and pays one dump over the whole set, and a breadth
    # location cycles the roster and pays one dump per mode. The width at which
    # the marginal candidate stops paying is therefore not the same number for
    # the two of them, and a run sized off a measurement may say so.
    near_width = int(width if near_width is None else near_width)
    near = (
        near_places(best_field, world["index"], seed, max(1, want[NEAR] // max(1, near_width)))
        if want.get(NEAR)
        else []
    )
    banded = ranked_bands(world["pools"], world["head_scores"], bands)
    ranked = (
        banded_places(banded, seed, max(1, want[RANKED] // max(1, width)), weights=band_weights)
        if want.get(RANKED)
        else []
    )
    counts = collections.Counter(str(row["partition"]) for row in ranked)
    picked = {str(row["key"]) for row in ranked}
    # The two matched arms draw out of one band cut, so `--top-bands` moves both
    # or neither: a control taken from a different stretch of the rank axis than
    # the arm it controls is not a control.
    matched = strongest_bands(banded, top_bands)
    if ranked:
        # Sized off the ranked draw's realized partition counts, which is what a
        # run measuring the curve and buying the controls beside it wants.
        scale = float(shares[FLAT]) / max(1e-9, float(shares[RANKED]))
        flat_want = {name: max(1, round(count * scale)) for name, count in counts.items()}
        aimed_want = {name: max(1, round(count * scale)) for name, count in counts.items()}
    else:
        flat_want = spread_over_partitions(matched, max(1, want.get(FLAT, 0) // max(1, width)))
        aimed_want = spread_over_partitions(matched, max(1, want.get(AIMED, 0) // max(1, width)))
    flat = flat_places(matched, picked, seed + 1, flat_want) if want.get(FLAT) else []
    # The aimed arm's places are drawn exactly as the flat arm's are and out of
    # the same pools, disjoint from both draws above. That is the point: the two
    # differ in the palette ask and in nothing else, so the flat arm is the
    # control the aimed arm's dominance hit rate is read against.
    aimed = (
        flat_places(matched, picked | {str(row["key"]) for row in flat}, seed + 2, aimed_want)
        if want.get(AIMED)
        else []
    )
    per_place = max(1, int(floor_width) * max(1, len(wanted_floor_modes)))
    proven = (
        proven_places(world["best"], world["index"], seed, max(1, want[FLOOR] // per_place))
        if want.get(FLOOR)
        else []
    )
    plans = {
        NEAR: plan_held_mode(near, world["taken"], maps, seed, near_width),
        RANKED: plan_cycled_modes(RANKED, ranked, breadth, maps, seed, width),
        FLAT: plan_cycled_modes(FLAT, flat, breadth, maps, seed, width),
        FLOOR: plan_floor(proven, wanted_floor_modes, world["taken"], maps, seed, floor_width),
        AIMED: plan_cycled_modes(
            AIMED, aimed, breadth, maps, seed + 2, width, draw=aimed_maps(cell), cell=cell
        )
        if aimed
        else [],
    }
    for arm, held in plans.items():
        if not held:
            continue
        log(
            f"[depth] {arm}: {len(held):,} candidate(s) over "
            f"{len({shot.location for shot in held}):,} location(s)"
        )
    shape = {
        "rate_seconds": round(float(rate), 4),
        "plan_headroom": PLAN_HEADROOM,
        "budget_seconds": float(budget),
        "width": int(width),
        "near_width": int(near_width),
        "rank_bands": int(bands),
        "top_bands": None if top_bands is None else int(top_bands),
        "matched_arms_sized_from": RANKED if ranked else "their own shares",
        # Every draw here is seeded and the seeds are not one seed: a place draw
        # and a palette draw at the same arm are taken under different ones, and
        # a run nobody can re-take is a measurement nobody can check.
        "seeds": {
            "base": int(seed),
            NEAR: {"places": int(seed), "candidates": int(seed)},
            RANKED: {"places": int(seed), "candidates": int(seed)},
            FLAT: {"places": int(seed) + 1, "candidates": int(seed)},
            FLOOR: {"places": int(seed), "candidates": int(seed)},
            AIMED: {"places": int(seed) + 2, "candidates": int(seed) + 2},
        },
        "cell": None if cell is None else str(cell),
        "roster": roster,
        "breadth_roster": breadth,
        "demoted": list(DEMOTED),
        "breadth_demoted": list(breadth_demoted),
        "maps_in_pool": len(maps),
        "shares": {arm: float(value) for arm, value in shares.items()},
        "band_weights": dict(band_weights or {}),
        "wanted_candidates": want,
        "floor_seats": int(floor_seats),
        "floor_width": int(floor_width),
        "floor_modes": wanted_floor_modes,
        "seats_short_today": short,
        "near_band_pool": sum(
            1
            for held in best_field.values()
            if SEATING_BAR <= held["best"] < PRIMED_BAR and held["best_mode"]
        ),
        "ranked_by_partition": dict(sorted(counts.items())),
        "flat_wanted_by_partition": dict(sorted(flat_want.items())),
        "conditioned_wanted_by_partition": dict(sorted(aimed_want.items())),
        "matched_mix_agrees": dict(sorted(flat_want.items())) == dict(sorted(aimed_want.items())),
        "arms": {
            arm: {
                "candidates": len(held),
                "locations": len({shot.location for shot in held}),
                "partitions": hunt._tally(shot.partition for shot in held),
                "modes": hunt._tally(shot.mode for shot in held),
            }
            for arm, held in plans.items()
        },
    }
    return weave(plans, shares), shape


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def population(margin: float = framing.MARGIN, log=print) -> dict:
    """Everything the three draws are taken over, read once.

    [`mine.population`] plus the ledger rows themselves, which this module needs
    because its near-band draw reads the best candidate **per mode** and not only
    the best one.
    """
    world = mine.population(margin=margin, log=log)
    world["rows"] = candidate_ledger.read()
    return world


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #
def run(
    name: str,
    *,
    seed: int = DEFAULT_SEED,
    budget: float = BUDGET_SECONDS,
    rate: float,
    width: int = WIDTH,
    near_width: int | None = None,
    bands: int = RANK_BANDS,
    top_bands: int | None = None,
    roster: list | None = None,
    breadth_demoted: tuple | list = BREADTH_DEMOTED,
    cell: str | None = None,
    shares: dict | None = None,
    band_weights: dict | None = None,
    floor_modes: list | None = None,
    floor_width: int = FLOOR_WIDTH,
    floor_seats: int = 10,
    device: str = "auto",
    margin: float = framing.MARGIN,
    world: dict | None = None,
    log=print,
) -> dict:
    """One depth run, end to end. Rows land as candidates land; the record is returned.

    The budget is enforced at the candidate boundary through [`hunt.Price`], so
    nothing is started that cannot finish inside what is left. A killed run keeps
    everything it made: the two ledger files and the sequence are appended to as
    each candidate lands and the record is the only thing written at the end.
    """
    started = time.monotonic()
    world = population(margin, log=log) if world is None else world
    intended, shape = build_plan(
        world,
        seed=seed,
        rate=rate,
        budget=budget,
        width=width,
        near_width=near_width,
        bands=bands,
        top_bands=top_bands,
        roster=roster,
        breadth_demoted=breadth_demoted,
        cell=cell,
        shares=shares,
        band_weights=band_weights,
        floor_modes=floor_modes,
        floor_width=floor_width,
        floor_seats=floor_seats,
        log=log,
    )
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
    price = hunt.Price()
    clock = mine.Clock()
    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    sequence_file = sequence_path(name)
    artifact = hunt._artifact()
    known = set(world["known"])
    made: list = []
    counts = {
        "planned": len(intended),
        "made": 0,
        "already_in_ledger": 0,
        "failed": 0,
        "stopped_for_budget": 0,
        "autolevel_acted": 0,
        "fields_swept": 0,
    }
    spent = 0.0
    for at, shot in enumerate(intended, start=1):
        loop = mine.colorize_module().tick()
        place = world["by_key"].get(shot.location)
        frame = world["index"].get(shot.location)
        if place is None or frame is None:
            counts["failed"] += 1
            continue
        recipe = maker.recipe_for(shot, place, frame)
        key = recipes.key_of(recipe)
        if key in known:
            counts["already_in_ledger"] += 1
            continue
        reserve = price.of(shot.partition)
        if spent + reserve > float(budget):
            counts["stopped_for_budget"] = len(intended) - at + 1
            log(
                f"[depth] stopping at candidate {at}: {shot.partition} is priced at "
                f"{reserve:.2f}s and {float(budget) - spent:.2f}s remain of {budget:.0f}s"
            )
            break
        try:
            result = mine.make(maker, shot, place, frame, key, pictures=pictures_dir(name))
        except Exception as failure:  # noqa: BLE001 — a failed candidate is a recorded fact
            counts["failed"] += 1
            log(f"[depth] {key} failed: {failure!r}")
            continue
        stages = result["stages"]
        write_at = mine.colorize_module().tick()
        source = hunt.source_for(name, shot, place, frame, at)
        stored = candidate_ledger.row(
            recipe=recipe,
            key=key,
            source=source,
            colour=result["colour"],
            picture=tracked_name(result["picture"]),
        )
        stored["hunt"] = {"name": name, "seconds": round(stages.total(), 3), **shot.named()}
        scored = candidate_ledger.score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=hunt.kind_of(shot.mode),
            read=result["verdict"],
            source=source,
        )
        hunt._append(rows_file, stored)
        hunt._append(scores_file, scored)
        stages.write = mine.colorize_module().tick() - write_at
        stages.overhead = max(0.0, (mine.colorize_module().tick() - loop) - stages.total())
        spent += stages.total()
        price.add(shot.partition, stages.total())
        known.add(key)
        counts["made"] += 1
        counts["autolevel_acted"] += int(result["acted"])
        row = {
            "key": key,
            "arm": shot.arm,
            "band": shot.band,
            "k": shot.k,
            "location": shot.location,
            "partition": shot.partition,
            "rank": shot.rank,
            "rank_fraction": shot.rank_fraction,
            "mode": shot.mode,
            "mode_kind": mine._kind_of(shot.mode),
            "colormap": shot.colormap,
            "palette_group": recipe.palette_group,
            "maxiter": int(frame["maxiter"]),
            "acted": bool(result["acted"]),
            "cells": result["cells"],
            "p_ge4": round(float(result["verdict"].get("p_ge4") or 0.0), 6),
            "p_ge3": round(float(result["verdict"].get("p_ge3") or 0.0), 6),
            "seconds": round(stages.total(), 3),
            "stages": stages.named(),
            "picture": tracked_name(result["picture"]),
        }
        made.append(row)
        hunt._append(sequence_file, {"schema": SCHEMA, "at": at, **row})
        clock.add(
            stages,
            {
                "arm": shot.arm,
                "partition": shot.partition,
                "mode": shot.mode,
                "mode_kind": mine._kind_of(shot.mode),
                "acted": bool(result["acted"]),
            },
        )
        if counts["made"] % 200 == 0:
            counts["fields_swept"] += mine.colorize_module().sweep_fields(maker.fields)
            log(
                f"[depth] {counts['made']:,} made, {spent:.0f}s of {budget:.0f}s "
                f"({spent / max(1, counts['made']):.3f}s each) — "
                + " ".join(
                    f"{arm}:{sum(1 for r in made if r['arm'] == arm)}"
                    for arm in DRAWS
                    if any(r["arm"] == arm for r in made)
                )
            )
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": name,
        "config": {
            "seed": seed,
            "budget_seconds": float(budget),
            "rate_seconds": float(rate),
            "width": int(width),
            "near_width": shape["near_width"],
            "rank_bands": int(bands),
            "top_bands": shape["top_bands"],
            "seeds": shape["seeds"],
            "shares": shape["shares"],
            "primed_bar": PRIMED_BAR,
            "seating_bar": SEATING_BAR,
            "margin": float(margin),
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
            "field_modes_only": True,
            "cell": shape.get("cell"),
        },
        "plan": shape,
        "counts": counts,
        "budget": {
            "allowed": float(budget),
            "spent": round(spent, 2),
            "share": round(spent / float(budget), 4) if budget else None,
            "wall_seconds": round(time.monotonic() - started, 2),
        },
        "price": price.table(),
        "profile": clock.table(),
        "curves": curves(made),
        "hit_rate": hit_rate(made, shape.get("cell")),
        "dominant_and_clearing": dominant_and_clearing(
            made, shape.get("cell"), mode_bars(world["rows"])
        ),
        "by_mode": by_mode(made),
        "rank": rank_readout(made),
        "route": None,
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "sequence_path": tracked_name(sequence_file),
    }
    record["route"] = route_to(record["rank"], record["curves"], world, bands=int(bands))
    path = record_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[depth] {counts['made']:,} candidate(s) in {spent:.0f}s — {tracked_name(path)}")
    return record


def merge(name: str, log=print) -> dict:
    """Upsert one depth run's two files into the ledger and its sidecar.

    [`mine.merge`]'s body over this module's paths: the rows are a hunt's rows
    byte for byte, the upsert keys on the recipe, and merging a killed run's
    partial is the same operation as merging a finished one's.
    """
    rows = hunt._read(rows_path(name))
    scores = hunt._read(scores_path(name))
    if not rows:
        raise DepthRefused(
            f"{tracked_name(rows_path(name))} holds no row, so there is nothing to merge. "
            f"A depth run writes its rows as it makes them; an empty file means none landed."
        )
    written = candidate_ledger.merge(rows, scores, log=log)
    total, new = written["ledger"]["rows"], written["ledger"]["new"]
    report = {
        "schema": SCHEMA,
        "name": name,
        "merged": len(rows),
        "ledger": written["ledger"],
        "scores": written["scores"],
        "recorded": written["recorded"],
        "locations_added": len({str((row.get("location") or {})["key"]) for row in rows}),
    }
    log(
        f"[depth] merged {len(rows):,} row(s): the ledger holds {total:,} recipes, "
        f"{new:,} of them new"
    )
    return report


# --------------------------------------------------------------------------- #
# The readouts.
# --------------------------------------------------------------------------- #
def read_sequence(name: str) -> list:
    """The ordered candidate sequence off disk, which is what a killed run leaves."""
    return hunt._read(sequence_path(name))


def curves(made: list, bars=(SEATING_BAR, PRIMED_BAR)) -> dict:
    """Per draw and per bar: the cumulative prime curve, and the clear rate at each `k`.

    **Cumulative** is the chance a location is primed by its first `k`, which is
    what sets a candidate set's width — the `k` where its increment stops paying
    is the `k` to stop at. **Per-candidate** is the chance the k-th candidate
    itself clears, which is flat if palettes are exchangeable at a place and
    falling if the ordering is doing something.

    A location that never reached `k` is out of the denominator at `k`, not
    counted as a failure there: a run stopped by its budget would otherwise
    report the tail of every curve bending down for a reason that is the clock.
    """
    out: dict = {}
    for arm in DRAWS:
        held = [row for row in made if row["arm"] == arm]
        if not held:
            continue
        by_location: dict = {}
        for row in held:
            by_location.setdefault(row["location"], []).append(row)
        highest = max((row["k"] for row in held), default=0)
        block: dict = {
            "candidates": len(held),
            "locations": len(by_location),
            "max_k": highest,
            "seconds": round(sum(row["seconds"] for row in held), 2),
            "seconds_per_candidate": round(
                sum(row["seconds"] for row in held) / max(1, len(held)), 4
            ),
        }
        for bar in bars:
            tag = _tag(bar)
            curve = []
            previous = 0.0
            for k in range(1, highest + 1):
                at_k = [row for row in held if row["k"] == k]
                alive = [rows for rows in by_location.values() if len(rows) >= k]
                cleared = sum(
                    1 for rows in alive if any(row["p_ge4"] >= bar for row in rows if row["k"] <= k)
                )
                cumulative = cleared / max(1, len(alive))
                curve.append(
                    {
                        "k": k,
                        "candidates_at_k": len(at_k),
                        "locations_with_k": len(alive),
                        "cleared_at_k": sum(1 for row in at_k if row["p_ge4"] >= bar),
                        "per_candidate_clear_rate": round(
                            sum(1 for row in at_k if row["p_ge4"] >= bar) / max(1, len(at_k)), 5
                        ),
                        "cumulative_primed": cleared,
                        "cumulative_rate": round(cumulative, 5),
                        "marginal_gain": round(cumulative - previous, 5),
                    }
                )
                previous = cumulative
            block[tag] = curve
        out[arm] = block
    return out


def hit_rate(made: list, cell: str | None) -> dict | None:
    """What the aimed arm actually came out as, against the flat arm's base rate.

    **The verdict and not the draw.** The carrier table biased which maps the
    [`AIMED`] arm was offered; whether a picture is dominant in the cell is read
    off that picture's own pixels, and this counts the reads. A candidate hits
    when the cell is in the `cells` its row carries — nothing here consults the
    table a second time to decide whether it should have.

    [`FLAT`] is the control: the same places drawn the same way out of the same
    pools, at the same width, differing in the palette ask alone. `lift` is the
    ratio, and it is the number that says whether biasing the draw bought
    anything — a lift near 1 means the cell was as easy to hit by accident.
    """
    if not cell:
        return None
    out: dict = {"cell": str(cell)}
    for arm in (AIMED, FLAT):
        held = [row for row in made if row["arm"] == arm]
        hits = [row for row in held if str(cell) in (row.get("cells") or ())]
        out[arm] = {
            "candidates": len(held),
            "dominant": len(hits),
            "rate": round(len(hits) / len(held), 5) if held else None,
            "locations": len({row["location"] for row in held}),
            "locations_with_a_hit": len({row["location"] for row in hits}),
            "maps_drawn": len({row["colormap"] for row in held}),
            "maps_that_hit": len({row["colormap"] for row in hits}),
        }
    aimed, flat = out[AIMED]["rate"], out[FLAT]["rate"]
    out["lift"] = round(aimed / flat, 3) if aimed is not None and flat else None
    # What a hit rate below 1 costs: the renders on this arm and nothing else,
    # because every candidate is a candidate whatever colour it came out.
    out["renders_per_hit"] = round(1.0 / aimed, 3) if aimed else None
    return out


def mode_bars(rows=None, log=lambda *_args: None) -> dict:
    """The per-mode clearing rule, read off the whole ledger. `{mode: {column, bar}}`.

    [`curation.headroom.bars`]' policy and not a second copy of it: `P(>=4) >=
    0.50` for a mode that can field twenty-five distinct locations there, and
    `P(>=3) >= 0.50` for one that cannot. Derived over the **ledger**, never over
    the arm being measured — a rule refitted on a few hundred fresh candidates
    would move with the thing it is supposed to be measuring, and two arms would
    then be scored against two bars.

    Beside the table, `clear_rate` is what share of every candidate ever rendered
    clears its own mode's rule. It is the base rate an arm's clear rate is the
    interesting number *against*: the judge taxes every draw alike, so a
    conditioned arm that holds it has cost the pipeline nothing.
    """
    from fractal_wallpapers.curation import headroom

    candidates, _cost, _refused = headroom.population(rows=rows, log=log)
    table = headroom.bars(candidates)
    clearing = headroom.clearing(candidates, table)
    return {
        "modes": {
            name: {"column": block["rule"], "bar": block["bar"]}
            for name, block in table["modes"].items()
        },
        "on_default": list(table["on_default"]),
        "on_fallback": list(table["on_fallback"]),
        "ledger_candidates": len(candidates),
        "ledger_clearing": len(clearing),
        "ledger_clear_rate": round(len(clearing) / max(1, len(candidates)), 5),
    }


def clears_its_bar(row: dict, table: dict) -> bool:
    """Whether one made candidate clears its own mode's rule.

    A mode the table has never heard of falls to the default column, which is the
    same direction [`curation.labeling.registry`] fails in: the strict reading is
    the safe one when the population cannot answer for itself.
    """
    rule = (table.get("modes") or {}).get(str(row["mode"])) or {
        "column": "p_ge4",
        "bar": SEATING_BAR,
    }
    return float(row.get(str(rule["column"])) or 0.0) >= float(rule["bar"])


def dominant_and_clearing(made: list, cell: str | None, table: dict) -> dict | None:
    """The conditioned arm and its control, factor by factor, ending in one price.

    The census's marginal cost for a cell is **unconditioned** and it composes
    three independent things: renders per place explored, places per place that
    yields any clearing candidate, and clearing places per clearing place
    dominant in the cell. Conditioning the palette ask attacks the third factor
    alone. So this reports the factors apart before it multiplies them, because
    the risk the arm exists to test lives in the second one — whether the maps
    that carry a colour make *worse pictures* — and a single composed number
    hides exactly that.

    Every count here is **raw**: one read of one candidate's own render against
    its own mode's bar. Nothing here is a maximum over `k`, so nothing here needs
    the k-dependent multiplier a prime count does.
    """
    if not cell:
        return None
    out: dict = {
        "cell": str(cell),
        "bars": {
            "from": "headroom.bars over the whole ledger",
            "on_fallback": table.get("on_fallback"),
        },
        "ledger_clear_rate": table.get("ledger_clear_rate"),
    }
    for arm in (AIMED, FLAT):
        held = [row for row in made if row["arm"] == arm]
        places = {row["location"] for row in held}
        clearing = [row for row in held if clears_its_bar(row, table)]
        dominant = [row for row in held if str(cell) in (row.get("cells") or ())]
        both = [row for row in clearing if str(cell) in (row.get("cells") or ())]
        seconds = sum(float(row["seconds"]) for row in held)
        out[arm] = {
            "candidates": len(held),
            "locations": len(places),
            "renders_per_place": round(len(held) / len(places), 3) if places else None,
            "seconds": round(seconds, 1),
            "seconds_per_candidate": round(seconds / len(held), 4) if held else None,
            "clearing": len(clearing),
            "clear_rate": round(len(clearing) / len(held), 5) if held else None,
            "dominant": len(dominant),
            "cell_hit_rate": round(len(dominant) / len(held), 5) if held else None,
            "dominant_and_clearing": len(both),
            "rate": round(len(both) / len(held), 5) if held else None,
            "renders_per_win": round(len(held) / len(both), 2) if both else None,
            "seconds_per_win": round(seconds / len(both), 2) if both else None,
            "places_with_a_win": len({row["location"] for row in both}),
        }
    aimed, flat = out[AIMED], out[FLAT]
    out["lift"] = {
        name: (round(aimed[name] / flat[name], 3) if aimed.get(name) and flat.get(name) else None)
        for name in ("clear_rate", "cell_hit_rate", "rate")
    }
    # The one that decides. Below 1 the conditioned arm is dearer per win than
    # drawing uniformly and the whole arm is a loss, whatever the hit rate did.
    out["renders_per_win_ratio"] = (
        round(flat["renders_per_win"] / aimed["renders_per_win"], 3)
        if aimed.get("renders_per_win") and flat.get("renders_per_win")
        else None
    )
    return out


def by_mode(made: list, bars=(SEATING_BAR, PRIMED_BAR)) -> dict:
    """Per mode: what it cost, what it cleared, and over how many distinct locations."""
    out: dict = {}
    for mode in sorted({row["mode"] for row in made}):
        held = [row for row in made if row["mode"] == mode]
        block = {
            "candidates": len(held),
            "locations": len({row["location"] for row in held}),
            "seconds": round(sum(row["seconds"] for row in held), 2),
            "seconds_per_candidate": round(
                sum(row["seconds"] for row in held) / max(1, len(held)), 4
            ),
        }
        for bar in bars:
            block[_tag(bar)] = {
                "candidates_clearing": sum(1 for row in held if row["p_ge4"] >= bar),
                "clear_rate": round(
                    sum(1 for row in held if row["p_ge4"] >= bar) / max(1, len(held)), 5
                ),
                "locations_clearing": len({row["location"] for row in held if row["p_ge4"] >= bar}),
            }
        out[mode] = block
    return out


def rank_readout(made: list, bars=(SEATING_BAR, PRIMED_BAR), arms=(RANKED, FLAT)) -> dict:
    """Prime rate against the head's rank depth, pooled and per partition.

    The load-bearing number. The route to a thousand primed places needs the rate
    at rank sixteen thousand, not the rate at rank seventy-four, and the only way
    to have it is to have drawn there. Reported against the **band** rather than
    the raw rank because a rank is not comparable across partitions of different
    sizes; the band is a decile of the partition's own pool.
    """
    held = [row for row in made if row["arm"] in set(arms) and row.get("rank") is not None]
    out: dict = {"locations": len({row["location"] for row in held})}
    for bar in bars:
        tag = _tag(bar)
        cells: dict = {}
        for row in held:
            key = (str(row["partition"]), str(row["band"]))
            block = cells.setdefault(
                key,
                {"locations": set(), "primed": set(), "rank_fractions": [], "seconds": 0.0},
            )
            block["locations"].add(row["location"])
            block["seconds"] += float(row["seconds"])
            if row.get("rank_fraction") is not None:
                block["rank_fractions"].append(float(row["rank_fraction"]))
            if row["p_ge4"] >= bar:
                block["primed"].add(row["location"])
        pooled: dict = {}
        for (partition, band), block in cells.items():
            held_band = pooled.setdefault(
                band, {"locations": 0, "primed": 0, "seconds": 0.0, "rank_fractions": []}
            )
            held_band["locations"] += len(block["locations"])
            held_band["primed"] += len(block["primed"])
            held_band["seconds"] += block["seconds"]
            held_band["rank_fractions"] += block["rank_fractions"]
            del partition
        out[tag] = {
            "pooled": {
                band: {
                    "locations": block["locations"],
                    "primed": block["primed"],
                    "rate": round(block["primed"] / max(1, block["locations"]), 5),
                    "median_rank_fraction": (
                        round(statistics.median(block["rank_fractions"]), 4)
                        if block["rank_fractions"]
                        else None
                    ),
                    "seconds_per_location": round(block["seconds"] / max(1, block["locations"]), 3),
                    "primed_per_hour": (
                        round(3600.0 * block["primed"] / block["seconds"], 2)
                        if block["seconds"]
                        else None
                    ),
                }
                for band, block in sorted(pooled.items())
            },
            "by_partition": {
                f"{partition}/{band}": {
                    "locations": len(block["locations"]),
                    "primed": len(block["primed"]),
                    "rate": round(len(block["primed"]) / max(1, len(block["locations"])), 5),
                }
                for (partition, band), block in sorted(cells.items())
            },
            "slope": _log_odds_slope(cells),
        }
    return out


def _log_odds_slope(cells: dict) -> dict:
    """A straight line through the band rates in log odds, and what it extrapolates to.

    Two numbers and an honest label: the fitted decay per decile of rank, and the
    rate the line puts at the bottom of the pool. It is a summary of the measured
    bands and **not** a model of anything below them — a fit reported past the
    range it was taken over is a guess wearing a number's clothes.
    """
    per_band: dict = {}
    for (_partition, band), block in cells.items():
        held = per_band.setdefault(band, [0, 0])
        held[0] += len(block["locations"])
        held[1] += len(block["primed"])
    points = []
    for band, (locations, primed) in sorted(per_band.items()):
        if not locations:
            continue
        at = _band_index(band)
        rate = (primed + 0.5) / (locations + 1.0)
        points.append((float(at), math.log(rate / (1.0 - rate))))
    if len(points) < 3:
        return {}
    mean_x = sum(x for x, _y in points) / len(points)
    mean_y = sum(y for _x, y in points) / len(points)
    denominator = sum((x - mean_x) ** 2 for x, _y in points)
    if not denominator:
        return {}
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    intercept = mean_y - slope * mean_x
    return {
        "bands_fitted": len(points),
        "log_odds_per_band": round(slope, 5),
        "odds_ratio_per_band": round(math.exp(slope), 4),
        "fitted_rate_first_band": round(1.0 / (1.0 + math.exp(-(intercept + slope * 0.0))), 5),
        "fitted_rate_last_band": round(
            1.0 / (1.0 + math.exp(-(intercept + slope * max(x for x, _y in points)))), 5
        ),
    }


def _band_index(band: str) -> int:
    digits = "".join(character for character in str(band) if character.isdigit())
    return int(digits) if digits else 0


def route_to(
    rank: dict,
    curve: dict,
    world: dict,
    target: int = 1000,
    bar: float = PRIMED_BAR,
    bands: int = RANK_BANDS,
):
    """Hours to `target` distinct primed locations, off the measured band rates.

    Spend the pool **best band first**, which is what a run that knew these
    numbers would do, and stop when the target is reached or the pool runs out.
    Every input is measured here: the per-band prime rate, the seconds a location
    at this width, and how many never-opened locations each band still holds.
    """
    tag = _tag(bar)
    rates = (rank.get(tag) or {}).get("pooled") or {}
    if not rates:
        return {}
    stock = collections.Counter()
    for name, held in (world.get("pools") or {}).items():
        del name
        stock["total"] += len(held)
    # The stock splits evenly over the bands **by construction** — the bands are
    # equal counts of each partition's own pool — so the divisor is the band
    # count the draw was cut at and not however many of them a truncated run
    # happened to reach.
    per_band = max(1, int(bands))
    owned = sum(
        1
        for key, held in (world.get("best") or {}).items()
        if float(held.get("best", -1.0)) >= bar and key
    )
    ordered = sorted(rates.items(), key=lambda item: -float(item[1]["rate"] or 0.0))
    need = max(0, int(target) - owned)
    seconds = 0.0
    got = 0
    spent_locations = 0
    legs = []
    for band, block in ordered:
        available = stock["total"] // per_band
        rate = float(block["rate"] or 0.0)
        per_location = float(block["seconds_per_location"] or 0.0)
        if rate <= 0.0 or available <= 0:
            legs.append({"band": band, "rate": rate, "locations_available": available, "took": 0})
            continue
        wanted = math.ceil((need - got) / rate) if rate else 0
        took = min(available, max(0, wanted))
        got += took * rate
        seconds += took * per_location
        spent_locations += took
        legs.append(
            {
                "band": band,
                "rate": round(rate, 5),
                "locations_available": available,
                "took": took,
                "primed": round(took * rate, 1),
                "hours": round(took * per_location / 3600.0, 2),
            }
        )
        if got >= need:
            break
    return {
        "target": int(target),
        "bar": bar,
        "already_owned": owned,
        "needed": need,
        "unopened_stock": stock["total"],
        "locations_to_open": spent_locations,
        "primed_expected": round(got, 1),
        "hours": round(seconds / 3600.0, 2),
        "reaches_target": bool(got >= need),
        "legs": legs,
    }


def rejects(made: list, rows: int = 24, bar: float = SEATING_BAR) -> list:
    """The strongest of what neither bar admits, sorted by `P(>=4)`."""
    held = [row for row in made if row["p_ge4"] < bar]
    return sorted(held, key=lambda row: -row["p_ge4"])[: int(rows)]


def contact_sheet(name: str, record: dict, output: Path | None = None, rows: int = mine.SHEET_ROWS):
    """The primed and the rejected on one page, sorted by `P(>=4)` and split at the bars.

    [`mine.contact_sheet`] over this run's own `made` list, read back off the
    sequence file rather than carried in the record: the record of a run this
    wide would be tens of megabytes of rows nobody reads as JSON.
    """
    made = record.get("made") or read_sequence(name)
    return mine.contact_sheet(
        name,
        {**record, "made": made, "counts": record.get("counts") or {}},
        output=depth_dir(name) / "autopsy.html" if output is None else Path(output),
        rows=rows,
    )


def _tag(bar: float) -> str:
    return f"bar_{bar:.2f}".replace(".", "")


__all__ = [
    "AIMED",
    "BUDGET_SECONDS",
    "DEFAULT_SEED",
    "BREADTH_DEMOTED",
    "DEMOTED",
    "DRAWS",
    "FIELDS",
    "FLAT",
    "FLOOR",
    "FLOOR_WIDTH",
    "MEASURING",
    "NEAR",
    "PICTURES",
    "PLAN_HEADROOM",
    "PRIMED_BAR",
    "RANKED",
    "RANK_BANDS",
    "RECORD_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "SEATING_BAR",
    "SEQUENCE_NAME",
    "SHARES",
    "UNIT",
    "WIDTH",
    "DepthRefused",
    "Shot",
    "banded_places",
    "best_field_by_location",
    "build_plan",
    "by_mode",
    "contact_sheet",
    "curves",
    "hit_rate",
    "deficient_modes",
    "depth_dir",
    "aimed_maps",
    "field_modes",
    "flat_maps",
    "fields_dir",
    "flat_places",
    "merge",
    "near_places",
    "pictures_dir",
    "plan_cycled_modes",
    "plan_held_mode",
    "plan_floor",
    "population",
    "proven_places",
    "ranked_bands",
    "rank_readout",
    "read_sequence",
    "record_path",
    "rejects",
    "route_to",
    "rows_path",
    "run",
    "scores_path",
    "sequence_path",
    "weave",
]
