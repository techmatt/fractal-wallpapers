"""Price a PRIMED location three ways, and profile what one candidate costs.

A gallery pass and a hunt both make candidates; neither one prices the thing a
collection is actually short of, which is a **place good enough to seat**. This
module asks that question with numbers: given the render loop exactly as it
stands, what does it cost to manufacture a location holding at least one
candidate the render judge calls a wallpaper, and by which route?

## PRIMED is derived, never stored

A location is PRIMED when it holds at least one candidate whose render-judge
`P(>=4)` clears [`PRIMED_BAR`]. That is read off the score sidecar at read time
and written into no row: a judge retrain moves every probability, and a boundary
stored beside the candidates would need a migration to follow it. [`primed`]
takes the bar as an argument for the same reason — the readout reports the mine
at more than one height and neither is baked in.

## Three arms, and what each is a control for

**DEEPEN** adds palettes at a location that already showed something, varying
the map alone and holding the frame and the mode the incumbent was drawn at.
Its deliverable is the marginal value of the k-th palette: the number that says
how wide a candidate set at one place should be.

**BREADTH-RANKED** opens never-opened admitted locations top-down on the
location head's rank **within partition**. Head scores are never pooled across
partitions — a cross-partition sort of them is a sort of nothing.

**BREADTH-FLAT** opens never-opened admitted locations with no quality
conditioning at all, matched to the ranked arm's per-partition counts. It is the
base rate, and it is the only thing that can say whether the head's rank buys
anything at the primed boundary.

The three are **interleaved** rather than run one after another, for
[`curation.hunt`]'s reason at a larger scale: the budget is spent at the
candidate boundary, and a mine that ran out on a concatenated plan would have
bought all of one arm and none of its own control.

## The loop is not touched

Every picture here is made by [`colorize.render`] through [`hunt.Maker`], the
same call with the same recipe as every candidate already in the ledger. What
this module adds is a **stopwatch around each stage** — the render, the judge,
the colour read, the row write — so the profile attributes wall clock without
changing what any of those stages do. The optimizations a readout proposes off
that profile are proposals; none of them is applied here.
"""

from __future__ import annotations

import collections
import json
import random
import statistics
import time
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, framing, hunt, recipes
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree a mine's own output lands in, under the regenerable tree.
UNIT = "mine"

#: What a mine's appended files and its record are called. The two row files are
#: [`curation.hunt`]'s, byte for byte, so [`merge`] is that module's upsert over
#: these paths rather than a second one to keep honest.
ROWS_NAME = hunt.ROWS_NAME
SCORES_NAME = hunt.SCORES_NAME
RECORD_NAME = "mine.json"
PROFILE_NAME = "profile.jsonl"
PICTURES = hunt.PICTURES
FIELDS = hunt.FIELDS

#: Where a candidate is PRIMED. Read at read time off the sidecar and stored
#: nowhere, so a judge retrain moves the boundary with no migration.
PRIMED_BAR = 0.90

#: The other height a readout reports at: `solve.Q4_BAR`, the bar the seating
#: stage actually counts against today. Both are reported because they are two
#: different questions and one set of scores answers each of them.
SEATING_BAR = 0.50

#: The three arms, in the spelling every row and every tally uses.
DEEPEN = "deepen"
RANKED = "breadth_ranked"
FLAT = "breadth_flat"
ARMS = (DEEPEN, RANKED, FLAT)

#: What share of the render budget each arm is given.
SHARES = {DEEPEN: 0.40, RANKED: 0.35, FLAT: 0.25}

#: The band a DEEPEN location is drawn from, on its best candidate's `P(>=4)`.
#: Two bands and not one: a location already over the bar can only say what a
#: further palette is worth at a known-good place, and a location under it is
#: the only kind a further palette can **convert**. Reported apart.
NEAR_BAND = (SEATING_BAR, PRIMED_BAR)
OVER_BAND = (PRIMED_BAR, 1.01)

#: How many new palettes a DEEPEN location is offered. Wide enough that the
#: marginal clear rate has somewhere to die.
DEEPEN_K = 12

#: How many candidates a breadth arm gives one location — [`hunt.PER_LOCATION`],
#: because the two breadth arms are the built path with the draw swapped.
PER_LOCATION = hunt.PER_LOCATION

#: How much longer the plan is than the budget prices it at. The budget is what
#: stops a mine and the plan is only what it stops in the middle of, so a plan
#: sized exactly to the rate stops the mine early wherever the rate came in high
#: — and the rate is a mean over a population whose median is under half of it.
#: Over-planning costs nothing: the surplus is never started.
PLAN_HEADROOM = 1.35

#: The seed every draw here is taken under unless a caller names another.
DEFAULT_SEED = 20260826

#: How long a mine may spend **rendering**, in seconds.
BUDGET_SECONDS = 7200.0


class MineRefused(RuntimeError):
    """A mine cannot be planned off what this checkout holds."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def mine_dir(name: str) -> Path:
    """One mine's own subtree: its rows, its scores, its profile, its record."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    """The ledger rows this mine has made so far, appended as each lands."""
    return mine_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    """The sidecar rows this mine has made so far, appended as each lands."""
    return mine_dir(name) / SCORES_NAME


def profile_path(name: str) -> Path:
    """One row a candidate: the stopwatch, and what the candidate was."""
    return mine_dir(name) / PROFILE_NAME


def record_path(name: str) -> Path:
    """What the mine reports about itself: the plan, the price, the arms."""
    return mine_dir(name) / RECORD_NAME


def fields_dir(name: str) -> Path:
    """Where this mine's dumped fields are, one per (location, mode)."""
    return mine_dir(name) / FIELDS


def pictures_dir(name: str) -> Path:
    """Where this mine's candidate renders are, one per recipe key."""
    return mine_dir(name) / PICTURES


# --------------------------------------------------------------------------- #
# The boundary, derived.
# --------------------------------------------------------------------------- #
def primed(values, bar: float = PRIMED_BAR) -> bool:
    """Whether a location holding these `P(>=4)` readings is PRIMED at `bar`."""
    return any(float(value) >= float(bar) for value in values)


def best_by_location(rows: list, scores: dict) -> dict:
    """`{location key: {best, count, partition, best_mode}}` off the ledger as it stands."""
    out: dict = {}
    for row in rows:
        key = str((row.get("location") or {})["key"])
        score = float(scores.get(str(row["key"]), 0.0))
        held = out.setdefault(
            key,
            {"best": -1.0, "count": 0, "partition": str(row.get("partition")), "best_mode": None},
        )
        held["count"] += 1
        if score >= held["best"]:
            held["best"] = score
            held["best_mode"] = str((row.get("recipe") or {}).get("mode"))
    return out


def taken_maps(rows: list) -> dict:
    """`{(location, mode with its settings): {colormaps already rendered there}}`.

    What stops a DEEPEN draw offering a place a map it already carries: the
    recipe key would collide, the loop would skip it, and the arm would report a
    k it never actually reached.

    **The mode half is [`colorize.spelled`] and not the bare mode**, so a mode
    drawn under settings has its own set. That is the same distinction the recipe
    key already makes — `mode_params` is in `recipes.KEYED` — and getting it wrong
    goes the expensive way: a `direct_trap_multiply@opacity=0.6` sharing the
    shipped mode's set would be refused every map the shipped one had ever spent,
    at exactly the places that hold the most of them. Every row written before
    anything carried settings spells as its bare mode, so no existing key moves.
    """
    from fractal_wallpapers.curation import colorize

    out: dict = {}
    for row in rows:
        recipe = row.get("recipe") or {}
        mode = colorize.spelled(str(recipe.get("mode")), recipe.get("mode_params"))
        key = (str((row.get("location") or {})["key"]), mode)
        out.setdefault(key, set()).add(str(recipe.get("colormap")))
    return out


# --------------------------------------------------------------------------- #
# The three draws.
# --------------------------------------------------------------------------- #
def deepen_places(best: dict, places: dict, band: tuple, seed: int, count: int) -> list:
    """`count` locations whose best candidate sits in `band`, spread over partitions.

    Round-robin over partitions for [`hunt.spread`]'s reason — the price table is
    per partition, and an arm that spent itself on one of them prices one of them.

    `places` is the admitted population keyed by location — `world["by_key"]` —
    and a key it does not hold is dropped because there is no row to render from,
    not because no scan looked at it. This used to take the frame index, which
    made every unscanned location invisible to the arm; the frame itself comes
    from [`hunt.frame_for`] at draw time.
    """
    pools: dict = {}
    low, high = band
    for key, held in best.items():
        if not (low <= held["best"] < high) or key not in places:
            continue
        pools.setdefault(held["partition"], []).append({**held, "key": key})
    pools = {name: sorted(rows, key=lambda row: str(row["key"])) for name, rows in pools.items()}
    return hunt.spread(pools, count, seed)


def ranked_places(pools: dict, head_scores: dict, seed: int, count: int) -> list:
    """`count` never-opened locations, best-first **within** each partition.

    The rank is the location head's `P(>=3)` off the intake sidecar, which is what
    [`intake.rank_key`] orders an offer by. It is compared inside a partition and
    never across one. A location the sidecar cannot score sorts last rather than
    being dropped, so the pool this arm draws from and the pool the flat arm draws
    from are the same pool — a dropped row would unmatch the comparison silently.
    """
    ordered = {
        name: sorted(
            rows,
            key=lambda row: (
                -float((head_scores.get(str(row["key"])) or {}).get("p_ge3") or -1.0),
                str(row["key"]),
            ),
        )
        for name, rows in pools.items()
    }
    return _round_robin(ordered, count)


def flat_places(pools: dict, seed: int, want: dict) -> list:
    """Never-opened locations with no quality conditioning, `want` many per partition.

    `want` is the ranked arm's realised per-partition count scaled to this arm's
    share, so the two breadth arms differ in **how** a place was chosen and in
    nothing else. Where a partition cannot fill its quota the shortfall stands
    rather than being borrowed from another partition — a borrowed place would
    unmatch the comparison the arm exists to be.
    """
    out: list = []
    for name in sorted(pools):
        held = pools[name]
        take = int(want.get(name, 0))
        if take <= 0 or not held:
            continue
        out += random.Random(hunt.seed_of(seed, name)).sample(held, min(take, len(held)))
    return _interleave_by_partition(out)


def _round_robin(pools: dict, count: int) -> list:
    """One place from each partition in turn, in partition-name order."""
    order = sorted(pools)
    at = {name: 0 for name in order}
    out: list = []
    while len(out) < count:
        took = False
        for name in order:
            if len(out) >= count:
                break
            if at[name] < len(pools[name]):
                out.append(pools[name][at[name]])
                at[name] += 1
                took = True
        if not took:
            break
    return out


def _interleave_by_partition(places: list) -> list:
    """The same round-robin shape, over places already drawn."""
    pools: dict = {}
    for row in places:
        pools.setdefault(str(row["partition"]), []).append(row)
    return _round_robin(pools, len(places))


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Unit:
    """One candidate a mine intends to make, before anything is rendered."""

    arm: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: Which candidate this is at its location, counting only what this mine
    #: makes there. The x-axis of the DEEPEN arm's marginal curve.
    k: int
    #: The DEEPEN band this location was drawn from, or the cell a breadth arm's
    #: stratifier asked for. A prior about the draw and never a claim about the
    #: picture, whose colour is read off its own render.
    band: str
    #: The mode's own settings — [`hunt.Try.mode_params`], same name and same
    #: reason: these three intentions are one duck type and [`hunt.Maker`] reads
    #: whichever it is handed. Empty for every arm this module draws.
    mode_params: dict = dataclass_field(default_factory=dict)

    def named(self) -> dict:
        """This intention as the ledger row carries it.

        `k` is here rather than only in the run's own `sequence.jsonl` because
        the ledger outlives the run's `artifacts/` tree and the corrections a
        reader has to make to it are `k`-dependent: a prime rate read off the
        maximum of `k` noisy judgements is a winner's-curse estimate, and the
        multiplier that turns it into a calibrated one is a function of `k`.
        A row that does not say which candidate at its location it was cannot
        be corrected at all.
        """
        out = {
            "leg": self.arm,
            "mode": self.mode,
            "colormap": self.colormap,
            "band": self.band,
            "k": self.k,
        }
        if self.mode_params:
            out["mode_params"] = dict(self.mode_params)
        return out


def plan_deepen(places: list, taken: dict, maps: list, seed: int, k: int, band: str) -> list:
    """`k` fresh palettes at each place, at the mode its best candidate was drawn in.

    The mode is held because the arm is about the palette: a draw that moved the
    mode as well would measure the two together and could not say which of them
    the k-th candidate bought.
    """
    out: list = []
    for row in places:
        key = str(row["key"])
        mode = str(row.get("best_mode") or "")
        if not mode or mode == "None":
            continue
        spent = taken.get((key, mode), set())
        free = [name for name in maps if name not in spent]
        drawn = random.Random(hunt.seed_of(seed, key, mode)).sample(free, min(k, len(free)))
        for at, colormap in enumerate(drawn, start=1):
            out.append(
                Unit(
                    arm=DEEPEN,
                    location=key,
                    partition=str(row["partition"]),
                    mode=mode,
                    colormap=str(colormap),
                    k=at,
                    band=band,
                )
            )
    return out


def plan_breadth(arm: str, places: list, maps: list, seed: int, per_location: int) -> list:
    """The built path with the draw swapped: modes without replacement, palettes stratified.

    [`hunt.modes_for`] and [`hunt.Stratifier`] unchanged, on the same seed for
    both breadth arms, so the ranked arm and the flat one are offered the same
    modes and the same colours in the same order and differ only in **which
    places** they are offered at.
    """
    from fractal_wallpapers.palettes import dominance

    stratifier = hunt.Stratifier(list(dominance.cells()), maps, seed)
    roster = tuple(_accepted_modes())
    out: list = []
    for row in places:
        key = str(row["key"])
        for at, mode in enumerate(hunt.modes_for(key, per_location, seed, roster), start=1):
            picked = stratifier.next()
            if picked is None:
                return out
            cell, colormap = picked
            out.append(
                Unit(
                    arm=arm,
                    location=key,
                    partition=str(row["partition"]),
                    mode=str(mode),
                    colormap=str(colormap),
                    k=at,
                    band=str(cell),
                )
            )
    return out


def _accepted_modes() -> list:
    """The roster a default mine draws from: production, less what is weighted 0.

    [`curation.mode_policy.accepted`] and not `engine.production_modes`, because a
    mine is the leg that *buys more of* a mode and a niche mode is one this project
    has decided to stop buying. A caller naming `--modes` is taken as given, here
    as everywhere: the standing is a default and not a prohibition.
    """
    from fractal_wallpapers.curation import mode_policy

    return mode_policy.accepted()


def weave(plans: dict, shares: dict | None = None) -> list:
    """The arms woven together in proportion, so a truncation truncates all alike.

    Each arm's j-th candidate is placed at `(j + 0.5) / share` and the whole is
    sorted on that, which is [`hunt._turns`]'s placement over arms instead of
    partitions: every prefix of the woven plan holds the arms in their intended
    proportion, so a mine cut short at any point has spent its budget the way a
    mine that finished would have.
    """
    shares = dict(shares or SHARES)
    placed = []
    for arm in ARMS:
        held = plans.get(arm) or []
        share = float(shares.get(arm, 0.0)) or 1e-9
        placed += [((at + 0.5) / share, arm, at, unit) for at, unit in enumerate(held)]
    return [unit for _at, _arm, _index, unit in sorted(placed, key=lambda item: item[:3])]


# --------------------------------------------------------------------------- #
# The stopwatch.
# --------------------------------------------------------------------------- #
@dataclass
class Stages:
    """What one candidate's wall clock went on, in the order it was spent.

    The first mine reported five stages and `render` was 97.2% of them, which is
    a profile that names the loop's cost and says nothing about it. Four of these
    are inside what used to be that one number, and they are [`colorize`]'s own
    [`METER_STAGES`](colorize.METER_STAGES) rather than a second reading of them:

    * `dump` — the iteration pass a shared field pays **once** per (location,
      mode), and which every palette after the first at that pair pays nothing
      for. Zero on a coloring the engine will not dump.
    * `paint` — the colouring itself: a full iteration pass on the built path, a
      colormap lookup over a dumped field on the shared one.
    * `measure` — the autolevel operator reading the tone of the picture it was
      handed. **Python, not the engine**: a JPEG decode and an Oklab pass.
    * `repaint` — the operator's second colouring, on the levelled map. Zero
      where the curve did not act.

    `render` is kept as the sum of those four so the two profiles can be read
    against each other, and it is derived rather than measured for exactly that
    reason: a total that could disagree with its own parts is a total nobody can
    check.
    """

    dump: float = 0.0
    paint: float = 0.0
    measure: float = 0.0
    repaint: float = 0.0
    judge: float = 0.0
    colour: float = 0.0
    write: float = 0.0
    overhead: float = 0.0

    @property
    def render(self) -> float:
        """Everything that used to be called `render`, so the old total still exists."""
        return self.dump + self.paint + self.measure + self.repaint

    def take(self, meter: dict) -> None:
        """Read one candidate's meter off [`colorize.render`]."""
        for stage in colorize_module().METER_STAGES:
            setattr(self, stage, float(meter.get(stage) or 0.0))

    def total(self) -> float:
        return self.render + self.judge + self.colour + self.write + self.overhead

    def named(self) -> dict:
        return {
            "dump": round(self.dump, 4),
            "paint": round(self.paint, 4),
            "measure": round(self.measure, 4),
            "repaint": round(self.repaint, 4),
            "judge": round(self.judge, 4),
            "colour": round(self.colour, 4),
            "write": round(self.write, 4),
            "overhead": round(self.overhead, 4),
        }


class Clock:
    """A running attribution of the mine's wall clock, by stage and by cut."""

    def __init__(self):
        self.by_stage: dict = collections.defaultdict(float)
        self.by_cut: dict = collections.defaultdict(lambda: collections.defaultdict(float))
        self.counts: dict = collections.defaultdict(int)

    def add(self, stages: Stages, cuts: dict) -> None:
        block = stages.named()
        for stage, seconds in block.items():
            self.by_stage[stage] += seconds
        for axis, value in cuts.items():
            self.counts[f"{axis}={value}"] += 1
            for stage, seconds in block.items():
                self.by_cut[f"{axis}={value}"][stage] += seconds

    def table(self) -> dict:
        total = sum(self.by_stage.values()) or 1.0
        return {
            "total_seconds": round(total, 2),
            "by_stage": {
                stage: {"seconds": round(seconds, 2), "share": round(seconds / total, 4)}
                for stage, seconds in sorted(self.by_stage.items(), key=lambda item: -item[1])
            },
            "by_cut": {
                cut: {
                    "candidates": self.counts[cut],
                    "seconds": round(sum(block.values()), 2),
                    "per_candidate": round(sum(block.values()) / max(1, self.counts[cut]), 3),
                    **{stage: round(seconds, 2) for stage, seconds in sorted(block.items())},
                }
                for cut, block in sorted(self.by_cut.items(), key=lambda i: -sum(i[1].values()))
            },
        }


def make(
    maker: hunt.Maker, unit, place: dict, frame: dict, key: str, pictures: Path | None = None
) -> dict:
    """Render one candidate through the unchanged loop, with a stopwatch on each stage.

    `pictures` names the directory the picture lands in, so a unit of work that
    keeps its own subtree — [`curation.depth`] does — makes candidates through
    this same call rather than through a second copy of it. Unnamed, it is this
    mine's own.

    [`hunt.Maker.make`] with the single `seconds` split eight ways and nothing
    else altered: the same [`colorize.render`], the same judge, the same colour
    read, in the same order and at the same recipe. The split is the profile's
    whole substance — a mine reporting one number a candidate could name no
    optimization, and naming them is half of what it was sent to do. Four of the
    eight come off the render's own meter rather than off a stopwatch here, so
    the parts of a colouring are attributed where they are spent.

    **The colour read does not reuse the judge's decode, and should not.** It
    looks like a double decode of one JPEG and is not one. The judge reads the
    full 640x360, resizes it to the head's input size and normalizes it, so its
    buffer is not the picture's pixels; the census needs a nearest-neighbour path
    on purpose, to keep every sample a colour that is really in the picture
    rather than an average of two that are not. And the census never does a full
    decode to begin with — [`codebook.pixels`] asks libjpeg for a quarter-scale
    draft straight to the census size, which measures at **1.8 ms** against the
    judge's own full decode at 2.4 ms, on a 60-picture sample. Handing over the
    judge's buffer would cost more than it saves and change a stored reading to
    do it. The `colour` stage's 12.3 ms is `codebook.shares` — a soft assignment
    of about six thousand distinct colours onto the 52 swatches, 10 ms of it —
    and the decode is 15%.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import dominance

    row = {
        "family": place["family"],
        "viewport": frame["viewport"],
        "maxiter": int(frame["maxiter"]),
    }
    stages = Stages()
    meter = dict.fromkeys(colorize.METER_STAGES, 0.0)
    reported: dict = {}
    picture, stamp = colorize.render(
        row,
        unit.mode,
        unit.colormap,
        maker.cyclic,
        (pictures_dir(maker.name) if pictures is None else Path(pictures)) / f"{key}.jpg",
        level=True,
        band=maker.band,
        fields=maker.fields,
        meter=meter,
        reported=reported,
    )
    stages.take(meter)
    at = colorize.tick()
    verdict = colorize.score_picture(maker.judge(), picture)
    stages.judge = colorize.tick() - at
    at = colorize.tick()
    reading = dominance.of_picture(picture)
    stages.colour = colorize.tick() - at
    return {
        "picture": picture,
        "stages": stages,
        "verdict": verdict,
        "acted": bool((stamp or {}).get("acted")),
        # The **whole** stamp, and `acted` beside it rather than instead of it.
        # `acted` is a boolean a curve cannot be rebuilt from, and a leg that
        # recorded only the boolean recorded that its picture is unreproducible:
        # [`coloring.autolevel.stops_from_stamp`] needs `curve`, and re-measuring
        # the render derives a different black point. `None` with the switch off,
        # which is the one case there is nothing to carry.
        "autolevel": stamp,
        "colour": candidate_ledger.colour_block(reading),
        "cells": list(reading.cells),
        # See [`hunt.Maker.make`]: the engine's word, not a reading of the picture.
        "texture_flat": bool(reported.get("texture_flat")),
    }


# --------------------------------------------------------------------------- #
# The population, read once.
# --------------------------------------------------------------------------- #
def population(margin: float = framing.MARGIN, log=print) -> dict:
    """Everything the three draws are taken over, read once.

    One read of the ledger and one of the embedding store, because both are tens
    of megabytes and every draw here is answered off the same rows.
    """
    from fractal_wallpapers.curation import intake

    index = hunt.frames(margin, log=log)
    places = hunt.scanned(log=log)
    stored = candidate_ledger.read()
    # On the LIVE judge only. The sidecar is keyed on the artifact because a
    # score is comparable inside one and not across two, and a join flattened to
    # the recipe key would be last-row-wins over whatever an adoption left behind.
    # A recipe with no reading on the live judge is left out and counted.
    read = candidate_ledger.read_scores()
    scores = {
        key: float(row.get("p_ge4") or 0.0)
        for key, row in candidate_ledger.scores_by_recipe(read).items()
    }
    stale = candidate_ledger.stale_scores(read)
    if stale:
        log(
            f"[mine] {sum(stale.values()):,} sidecar row(s) read on {len(stale)} other judge "
            f"artifact(s) are out of this draw: {stale}"
        )
    opened = hunt.opened_locations(stored)
    pools = hunt.drawable(places, opened)
    best = best_by_location(stored, scores)
    at_recorded = sum(1 for held in pools.values() for row in held if str(row["key"]) not in index)
    log(
        f"[mine] {len(best):,} opened location(s) in the ledger; "
        f"{sum(len(held) for held in pools.values()):,} admitted and never opened over "
        f"{len(pools)} partition(s), {at_recorded:,} of them at the frame they already carry"
    )
    return {
        "index": index,
        "places": places,
        "by_key": {str(row["key"]): row for row in places},
        "known": {str(row["key"]) for row in stored},
        "opened": opened,
        "pools": pools,
        "best": best,
        "taken": taken_maps(stored),
        "head_scores": intake.read_scores(amended=True),
        "ledger_scores": scores,
        "ledger_rows": len(stored),
    }


def build_plan(
    world: dict,
    *,
    seed: int,
    rate: float,
    budget: float,
    k: int = DEEPEN_K,
    per_location: int = PER_LOCATION,
    log=print,
) -> tuple:
    """The three arms sized off a measured per-candidate rate. `(plan, shape)`.

    The rate comes from the pilot and from nowhere else. A rate carried in from
    another pass prices another population: the partitions differ, the mode mix
    differs, and the last hunt's own table has one partition costing five times
    another.
    """
    from fractal_wallpapers.curation import colorize

    maps = list(colorize.pool(seed))
    planned = PLAN_HEADROOM * budget / max(rate, 1e-6)
    want = {arm: int(planned * share) for arm, share in SHARES.items()}
    # Half the DEEPEN arm in each band, so the marginal curve is reported both
    # for a place a palette can still convert and for one already over the bar.
    per_band = max(1, want[DEEPEN] // (2 * max(1, k)))
    deepen: list = []
    for band, bounds in (("near", NEAR_BAND), ("over", OVER_BAND)):
        places = deepen_places(world["best"], world["by_key"], bounds, seed, per_band)
        deepen += plan_deepen(places, world["taken"], maps, seed, k, band)
    ranked_wanted = max(1, want[RANKED] // max(1, per_location))
    ranked = ranked_places(world["pools"], world["head_scores"], seed, ranked_wanted)
    counts = collections.Counter(str(row["partition"]) for row in ranked)
    # The flat arm is matched to the ranked arm's realised per-partition counts,
    # scaled by the two arms' shares, and drawn from the pool with the ranked
    # arm's own places removed so no location stands in both.
    scale = SHARES[FLAT] / SHARES[RANKED]
    picked = {str(row["key"]) for row in ranked}
    left = {
        name: [row for row in held if str(row["key"]) not in picked]
        for name, held in world["pools"].items()
    }
    flat_want = {name: max(1, round(count * scale)) for name, count in counts.items()}
    flat = flat_places(left, seed + 1, flat_want)
    plans = {
        DEEPEN: deepen,
        RANKED: plan_breadth(RANKED, ranked, maps, seed, per_location),
        FLAT: plan_breadth(FLAT, flat, maps, seed, per_location),
    }
    for arm, held in plans.items():
        log(
            f"[mine] {arm}: {len(held):,} candidate(s) over "
            f"{len({unit.location for unit in held}):,} location(s)"
        )
    shape = {
        "rate_seconds": round(float(rate), 4),
        "plan_headroom": PLAN_HEADROOM,
        "budget_seconds": float(budget),
        "k": int(k),
        "per_location": int(per_location),
        "maps_in_pool": len(maps),
        "wanted": want,
        "ranked_by_partition": dict(sorted(counts.items())),
        "flat_wanted_by_partition": dict(sorted(flat_want.items())),
        "arms": {
            arm: {
                "candidates": len(held),
                "locations": len({unit.location for unit in held}),
                "partitions": hunt._tally(unit.partition for unit in held),
                "modes": hunt._tally(unit.mode for unit in held),
            }
            for arm, held in plans.items()
        },
    }
    return weave(plans), shape


# --------------------------------------------------------------------------- #
# The mine.
# --------------------------------------------------------------------------- #
def run(
    name: str,
    *,
    seed: int = DEFAULT_SEED,
    budget: float = BUDGET_SECONDS,
    rate: float | None = None,
    k: int = DEEPEN_K,
    per_location: int = PER_LOCATION,
    device: str = "auto",
    margin: float = framing.MARGIN,
    world: dict | None = None,
    log=print,
) -> dict:
    """One mine, end to end. Rows land as candidates land; the record is returned.

    The budget is enforced at the candidate boundary through [`hunt.Price`], so
    nothing is started that cannot finish inside what is left, and the record can
    say what was spent against what was allowed rather than how far past the last
    render ran.
    """
    started = time.monotonic()
    world = population(margin, log=log) if world is None else world
    if rate is None:
        raise MineRefused(
            "a mine is sized off a rate measured on its own target population, and none was "
            "given. Take a short `curate mine run` first and pass the seconds-a-candidate "
            "its record reports."
        )
    intended, shape = build_plan(
        world,
        seed=seed,
        rate=rate,
        budget=budget,
        k=k,
        per_location=per_location,
        log=log,
    )
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
    price = hunt.Price()
    clock = Clock()
    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    profile_file = profile_path(name)
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
        "shared_field": 0,
        "fields_swept": 0,
    }
    spent = 0.0
    for at, unit in enumerate(intended, start=1):
        loop = colorize_module().tick()
        place = world["by_key"].get(unit.location)
        if place is None:
            counts["failed"] += 1
            continue
        frame = hunt.frame_for(place, world["index"])
        recipe = maker.recipe_for(unit, place, frame)
        key = recipes.key_of(recipe)
        if key in known:
            counts["already_in_ledger"] += 1
            continue
        reserve = price.of(unit.partition)
        if spent + reserve > float(budget):
            counts["stopped_for_budget"] = len(intended) - at + 1
            log(
                f"[mine] stopping at candidate {at}: {unit.partition} is priced at "
                f"{reserve:.2f}s and {float(budget) - spent:.2f}s remain of {budget:.0f}s"
            )
            break
        try:
            result = make(maker, unit, place, frame, key)
        except Exception as failure:  # noqa: BLE001 — a failed candidate is a recorded fact
            counts["failed"] += 1
            log(f"[mine] {key} failed: {failure!r}")
            continue
        stages = result["stages"]
        write_at = colorize_module().tick()
        source = hunt.source_for(name, unit, place, frame, at)
        stored = candidate_ledger.row(
            recipe=recipe,
            key=key,
            source=source,
            colour=result["colour"],
            picture=tracked_name(result["picture"]),
            texture_flat=result["texture_flat"],
        )
        stored["hunt"] = candidate_ledger.hunt_block(
            {"seconds": round(stages.total(), 3), **unit.named()}
        )
        scored = candidate_ledger.score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=hunt.kind_of(unit.mode, result["texture_flat"]),
            read=result["verdict"],
            source=source,
        )
        hunt._append(rows_file, stored)
        hunt._append(scores_file, scored)
        stages.write = colorize_module().tick() - write_at
        stages.overhead = max(0.0, (colorize_module().tick() - loop) - stages.total())
        spent += stages.total()
        price.add(unit.partition, stages.total())
        known.add(key)
        counts["made"] += 1
        counts["autolevel_acted"] += int(result["acted"])
        counts["shared_field"] += int(colorize_module().shareable(unit.mode))
        row = {
            "key": key,
            "arm": unit.arm,
            "band": unit.band,
            "k": unit.k,
            "location": unit.location,
            "partition": unit.partition,
            "mode": unit.mode,
            "mode_kind": _kind_of(unit.mode),
            "texture_flat": result["texture_flat"],
            "colormap": unit.colormap,
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
        hunt._append(profile_file, {"schema": SCHEMA, **row})
        clock.add(
            stages,
            {
                "arm": unit.arm,
                "partition": unit.partition,
                "mode_kind": _kind_of(unit.mode),
                "mode": unit.mode,
                "acted": bool(result["acted"]),
                "partition_x_kind": f"{unit.partition}/{_kind_of(unit.mode)}",
            },
        )
        if counts["made"] % 100 == 0:
            counts["fields_swept"] += colorize_module().sweep_fields(maker.fields)
            log(
                f"[mine] {counts['made']:,} made, {spent:.0f}s of {budget:.0f}s "
                f"({spent / max(1, counts['made']):.2f}s each) — "
                + " ".join(f"{arm}:{sum(1 for r in made if r['arm'] == arm)}" for arm in ARMS)
            )
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": name,
        "config": {
            "seed": seed,
            "budget_seconds": float(budget),
            "rate_seconds": float(rate),
            "k": int(k),
            "per_location": int(per_location),
            "shares": dict(SHARES),
            "primed_bar": PRIMED_BAR,
            "seating_bar": SEATING_BAR,
            "margin": float(margin),
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
        },
        "population": {
            "scanned_admitted": len(world["places"]),
            "ledger_rows": world["ledger_rows"],
            "already_open": len(world["opened"]),
            "unopened_drawable": sum(len(held) for held in world["pools"].values()),
            "unopened_at_recorded_frame": sum(
                1
                for held in world["pools"].values()
                for row in held
                if str(row["key"]) not in world["index"]
            ),
            "unopened_wanting_framing": len(
                hunt.unframed(
                    [row for held in world["pools"].values() for row in held], world["index"]
                )
            ),
            "by_partition": {name: len(held) for name, held in sorted(world["pools"].items())},
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
        "arms": arm_readout(made, world),
        "made": made,
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "profile_path": tracked_name(profile_file),
    }
    path = record_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[mine] {counts['made']:,} candidate(s) in {spent:.0f}s — {tracked_name(path)}")
    return record


def colorize_module():
    """[`curation.colorize`], imported at call time like everything else here."""
    from fractal_wallpapers.curation import colorize

    return colorize


def _kind_of(mode: str) -> str:
    return colorize_module().kind_of(mode)


# --------------------------------------------------------------------------- #
# Folding a mine into the ledger.
# --------------------------------------------------------------------------- #
def merge(name: str, log=print) -> dict:
    """Upsert one mine's two files into the ledger and its sidecar.

    [`hunt.merge`]'s body over this module's paths rather than a second
    implementation of it: a mine's rows are a hunt's rows byte for byte, and the
    upsert keys on the recipe, so merging a mine twice writes the same bytes and
    merging a killed mine's partial is the same operation as merging a finished
    one's. Separate from the run for the reason the hunt's is — the ledger is
    rewritten whole on every upsert, and forty megabytes a candidate is not a
    write.
    """
    rows = hunt._read(rows_path(name))
    scores = hunt._read(scores_path(name))
    if not rows:
        raise MineRefused(
            f"{tracked_name(rows_path(name))} holds no row, so there is nothing to merge. "
            f"A mine writes its rows as it makes them; an empty file means none landed."
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
        # What this leg re-rendered because the retention rule had already
        # deleted it: a floor, reported and never prevented. See
        # [`retention.repeat_draws`].
        "repeat_draws": written["repeat_draws"],
        "pruned": written["pruned"],
        "locations_added": len({str((row.get("location") or {})["key"]) for row in rows}),
    }
    log(
        f"[mine] merged {len(rows):,} row(s): the ledger holds {total:,} recipes, "
        f"{new:,} of them new"
    )
    return report


# --------------------------------------------------------------------------- #
# What the loop could have cost. A measurement, not a change.
# --------------------------------------------------------------------------- #
#: How many maps one bench location is priced over. Wide enough that the fixed
#: cost of a dumped field is amortised the way a real candidate set would
#: amortise it, narrow enough to price several locations inside a few minutes.
BENCH_MAPS = 8

#: Which mode kinds the bench prices. The two that carry most of the bill; the
#: other two would only re-report the engine's own refusal, which is that a
#: dumped field needs one scalar field behind the picture.
BENCH_KINDS = ("field", "composite")

#: The widths a candidate's cost is reported at. `1` is the fixed cost with
#: nothing to amortise it over, `40` is the depth a shareable field makes
#: affordable, and the two between them are where the curve bends.
BENCH_K = (1, 8, 20, 40)


def bench(
    seed: int = DEFAULT_SEED,
    maps: int = BENCH_MAPS,
    world: dict | None = None,
    ks=BENCH_K,
    log=print,
):
    """Price one candidate against the width of the set it is drawn in.

    Four measurements at one location and one mode, over the same `maps`:

    * **built** — [`colorize.render`] with no field cache offered, once a map:
      one engine process and one full iteration pass per candidate.
    * **built, levelled** — the same with the autolevel operator on, which is a
      **second** full iteration pass wherever the curve fires. This is what the
      loop actually paid before this leg.
    * **shared field** — one `dump-field`, then [`colorize.render`] with the
      field cache offered, which makes every map after the first a `recolor`.
      Available only where the mode has a single scalar field behind it: the
      engine refuses a dump for the composites, the modulate and the direct
      traps, and that refusal is recorded here rather than worked around,
      because it is what bounds the saving.
    * **shared field, levelled** — the same with the operator on, where its
      second pass is a recolour too.
    * **judged in one batch** — the same pictures through the judge at
      `batch_size` = `maps` against one at a time, which is the only stage whose
      cost is a Python-side choice rather than an engine one. **Both judge
      figures are totals over `maps`** where every other timing here is per map;
      divide before setting either beside a candidate.

    Plus the **boundary itself**: an engine call that renders nothing, which is
    the floor under every one of the loop's crossings.

    ### Why the k table is derived rather than measured at every k

    The measurement is taken at `maps` maps and the table is computed from its
    unit costs — a dump spread over k, plus k colourings. Measuring 40 maps at
    every partition would be an hour of renders to re-derive an identity, and
    `maps = 8` is one of the reported widths, so the derivation is checked
    against a direct measurement at every location rather than assumed.

    Nothing here is written into the ledger and nothing here changes the loop.
    """
    import shutil
    import tempfile

    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import colorize

    world = population(log=log) if world is None else world
    pool = list(colorize.pool(seed))
    out: dict = {"schema": SCHEMA, "maps": int(maps), "k": list(ks), "locations": []}
    at = colorize.tick()
    for family in ({"kind": "mandelbrot"}, {"kind": "phoenix"}, {"kind": "multibrot", "degree": 3}):
        engine.home_view(family)
    out["boundary_seconds"] = round((colorize.tick() - at) / 3, 4)
    log(f"[bench] one engine crossing that renders nothing: {out['boundary_seconds']:.3f}s")
    picks = _bench_picks(world, seed)
    scratch = Path(tempfile.mkdtemp(prefix="mine-bench-"))
    try:
        for place, frame, mode in picks:
            out["locations"].append(
                _bench_one(place, frame, mode, pool[:maps], scratch, world, ks=ks, log=log)
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    out["per_candidate"] = bench_table(out["locations"], ks)
    return out


def per_candidate_at(block: dict, k: int) -> dict:
    """What one candidate costs at set width `k`, before and after, for one block.

    Before is the built path with the operator on — one iteration pass a
    candidate and a second one wherever the curve fires — and does not move with
    `k`, which is the whole complaint. After is one dump spread over `k` plus
    one colouring a candidate, and where the mode has no field to dump it is the
    before, unchanged and honestly so.
    """
    before = float(block["built_leveled_per_map"])
    shared = block["shared_field"]
    if not shared.get("available"):
        return {"before": round(before, 4), "after": round(before, 4), "saving": 0.0}
    after = float(shared["dump_seconds"]) / max(1, int(k)) + float(
        shared["leveled_recolour_per_map"]
    )
    return {
        "before": round(before, 4),
        "after": round(after, 4),
        "saving": round(1.0 - after / before, 4) if before else 0.0,
    }


def bench_table(blocks: list, ks=BENCH_K) -> dict:
    """The bench's headline: seconds a candidate against `k`, split by mode kind.

    Split rather than pooled because the two kinds are not one population any
    more — the whole of the saving lands on one of them, and a pooled mean would
    report a number no candidate is ever charged.
    """
    table: dict = {}
    for kind in sorted({str(block["mode_kind"]) for block in blocks}):
        held = [block for block in blocks if str(block["mode_kind"]) == kind]
        table[kind] = {
            "locations": len(held),
            "k": {
                str(k): {
                    stage: round(
                        sum(per_candidate_at(block, k)[stage] for block in held) / len(held), 4
                    )
                    for stage in ("before", "after", "saving")
                }
                for k in ks
            },
        }
    return table


def _bench_picks(world: dict, seed: int, kinds=BENCH_KINDS) -> list:
    """One never-opened location per partition, in one mode of each named kind.

    Every partition and not a sample of them, because the price table this is set
    beside is per partition and the two ends of it differ by three times. The
    kinds are named rather than exhaustive: `field` and `composite` carry most of
    the bill, and what a `direct` or `modulate` mode would show is the refusal the
    engine already documents — a dump needs one scalar field behind the picture.
    """
    from fractal_wallpapers.curation import colorize

    wanted: dict = {}
    for mode in _accepted_modes():
        kind = colorize.kind_of(mode)
        if kind in kinds:
            wanted.setdefault(kind, mode)
    picks = []
    for name in sorted(world["pools"]):
        held = world["pools"][name]
        if not held:
            continue
        row = random.Random(hunt.seed_of(seed, "bench", name)).choice(held)
        frame = hunt.frame_for(row, world["index"])
        for _kind, mode in sorted(wanted.items()):
            picks.append((row, frame, mode))
    return picks


def _bench_one(place, frame, mode, maps, scratch: Path, world: dict, ks=BENCH_K, log=print) -> dict:
    """One location, one mode, `maps` maps, priced four ways."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import colorize

    del world, engine
    row = {
        "family": place["family"],
        "viewport": frame["viewport"],
        "maxiter": int(frame["maxiter"]),
    }
    kind = colorize.kind_of(mode)
    cyclic = colorize.cyclic()
    band = colorize.band()
    here = scratch / str(hunt.seed_of(str(place["key"]), mode))
    here.mkdir(parents=True, exist_ok=True)

    def leg(tag: str, level: bool, fields: Path | None) -> tuple:
        """`maps` candidates one way. `(seconds a map, how many the curve acted on)`."""
        seconds, acted = [], 0
        for at, colormap in enumerate(maps):
            started = colorize.tick()
            _picture, stamp = colorize.render(
                row,
                mode,
                colormap,
                cyclic,
                here / f"{tag}{at}.jpg",
                level=level,
                band=band if level else None,
                fields=fields,
            )
            seconds.append(colorize.tick() - started)
            acted += int(bool((stamp or {}).get("acted")))
        return sum(seconds) / len(seconds), acted

    built_per_map, _ = leg("built", level=False, fields=None)
    built_leveled_per_map, built_acted = leg("builtlevel", level=True, fields=None)
    pictures = [here / f"built{at}.jpg" for at in range(len(maps))]

    shared: dict = {"available": False, "why": None}
    if colorize.shareable(mode):
        fields = here / "fields"
        try:
            started = colorize.tick()
            colorize.field_of(row, fields, mode=mode)
            dumped = colorize.tick() - started
            recolour_per_map, _ = leg("recolour", level=False, fields=fields)
            leveled_per_map, shared_acted = leg("recolourlevel", level=True, fields=fields)
            shared = {
                "available": True,
                "dump_seconds": round(dumped, 4),
                "recolour_per_map": round(recolour_per_map, 4),
                "leveled_recolour_per_map": round(leveled_per_map, 4),
                "leveled_acted": shared_acted,
            }
        except Exception as refusal:  # noqa: BLE001 — a refused dump is the measurement
            shared = {"available": False, "why": repr(refusal)[:200]}
    else:
        shared = {"available": False, "why": f"{mode} is a {kind} coloring: no single scalar field"}

    # **These two are TOTALS over `maps` pictures, and every other timing on this
    # block is per map.** `built_per_map`, `leveled_recolour_per_map` and the rest
    # divide; these do not, and the key names do not say so. A reader who sets
    # `judge_one_at_a_time` beside a per-candidate render is out by `maps` — an
    # eightfold at the default width, which is the difference between a judge that
    # is a sixth of a candidate and one that is larger than the whole of it.
    judge = colorize.load_judge()
    started = colorize.tick()
    for picture in pictures:
        colorize.score_picture(judge, picture)
    one_at_a_time = colorize.tick() - started
    started = colorize.tick()
    _batched(judge, pictures)
    batched = colorize.tick() - started
    block = {
        "partition": str(place["partition"]),
        "mode": mode,
        "mode_kind": kind,
        "maxiter": int(row["maxiter"]),
        "built_per_map": round(built_per_map, 4),
        "built_leveled_per_map": round(built_leveled_per_map, 4),
        "built_leveled_acted": built_acted,
        "shared_field": shared,
        "judge_one_at_a_time": round(one_at_a_time, 3),
        "judge_batched": round(batched, 3),
    }
    block["per_candidate"] = {str(k): per_candidate_at(block, k) for k in ks}
    log(
        f"[bench] {block['partition']}/{mode} ({kind}): built {built_leveled_per_map:.2f}s a map "
        f"levelled ({built_acted}/{len(maps)} acted), shared "
        + (
            f"{shared['leveled_recolour_per_map']:.3f}s a map after a "
            f"{shared['dump_seconds']:.2f}s dump"
            if shared.get("available")
            else "refused"
        )
        + f"; a candidate at k=40 {block['per_candidate']['40']['after']:.3f}s "
        f"against {block['per_candidate']['40']['before']:.3f}s"
    )
    return block


def _batched(judge, pictures: list) -> list:
    """The same judge over the same pictures in one batch. [`colorize.score_picture`]'s
    `batch_size` is 1 and every other member of the call is unchanged."""
    from fractal_wallpapers.models import scoring, train

    model, config, where = judge
    classes = int(config["classes"])
    transform = scoring.transform_of(config)
    probabilities = train.score(
        model, list(pictures), transform, where, classes, {"batch_size": len(pictures)}
    )
    return [float(values[classes - 2]) for values in probabilities]


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def arm_readout(made: list, world: dict | None = None, bars=(PRIMED_BAR, SEATING_BAR)) -> dict:
    """Per arm: what it rendered, what it opened, and what it primed at each bar.

    The primed count is derived here and stored nowhere, so the same rows read at
    another bar answer another question with no migration. A DEEPEN location is
    counted **newly** primed only where this mine's own candidates crossed a bar
    its incumbents had not: an arm cannot claim a place that was already over it
    before the arm started.
    """
    out: dict = {}
    for arm in ARMS:
        held = [row for row in made if row["arm"] == arm]
        if not held:
            continue
        by_location: dict = {}
        for row in held:
            by_location.setdefault(row["location"], []).append(row)
        seconds = sum(row["seconds"] for row in held)
        block = {
            "candidates": len(held),
            "locations": len(by_location),
            "seconds": round(seconds, 2),
            "seconds_per_candidate": round(seconds / max(1, len(held)), 3),
            "candidates_per_location": round(len(held) / max(1, len(by_location)), 2),
            "partitions": hunt._tally(row["partition"] for row in held),
            "p_ge4": _spread([row["p_ge4"] for row in held]),
        }
        for bar in bars:
            tag = f"bar_{bar:.2f}".replace(".", "")
            fresh = {
                key
                for key, rows in by_location.items()
                if primed((row["p_ge4"] for row in rows), bar)
            }
            already = set()
            if world is not None:
                already = {
                    key
                    for key in fresh
                    if float((world["best"].get(key) or {}).get("best", -1.0)) >= bar
                }
            block[tag] = {
                "bar": bar,
                "candidates_clearing": sum(1 for row in held if row["p_ge4"] >= bar),
                "locations_primed": len(fresh),
                "locations_newly_primed": len(fresh - already),
                "primed_rate": round(len(fresh) / max(1, len(by_location)), 5),
                "candidates_per_primed": round(len(held) / len(fresh), 1) if fresh else None,
                "seconds_per_primed": round(seconds / len(fresh), 1) if fresh else None,
                "by_partition": {
                    name: {
                        "locations": len(
                            {row["location"] for row in held if row["partition"] == name}
                        ),
                        "primed": len(
                            {key for key in fresh if by_location[key][0]["partition"] == name}
                        ),
                    }
                    for name in sorted({row["partition"] for row in held})
                },
            }
        if arm == DEEPEN:
            block["marginal"] = marginal(held, bars)
        out[arm] = block
    return out


#: How many resamples the ranked-against-flat comparison is bootstrapped over.
#: Enough for a 95% interval to be stable to about a point at the sizes a mine
#: reaches; the whole resample is a few thousand integers and costs nothing.
BOOTSTRAP_DRAWS = 4000


def compare(
    made: list, bars=(PRIMED_BAR, SEATING_BAR), draws: int = BOOTSTRAP_DRAWS, seed: int = 0
) -> dict:
    """RANKED against FLAT at the primed boundary, **stratified on partition**.

    Pooled is reported and is not the answer. The two arms are matched on
    partition by construction, but "matched" is a property of the plan and the
    realised counts can drift — a partition that ran out of stock, a budget that
    stopped mid-round — and a pooled rate over drifted counts mixes the arms'
    difference with the partitions' difference. The **stratified** difference is
    a Mantel-Haenszel weighted mean of the per-partition differences, at weights
    `n_ranked * n_flat / (n_ranked + n_flat)`, which is the estimator that is
    unbiased under exactly that drift.

    The uncertainty is a **cluster bootstrap over locations**, resampled inside
    partition and inside arm: a location is the unit that was drawn, and its
    candidates are not independent of each other. A candidate-level interval
    would be narrower and would be measuring the wrong population.
    """
    out: dict = {}
    per_arm = {
        arm: _locations_of([row for row in made if row["arm"] == arm]) for arm in (RANKED, FLAT)
    }
    for bar in bars:
        tag = f"bar_{bar:.2f}".replace(".", "")
        cells: dict = {}
        for arm, places in per_arm.items():
            for rows in places.values():
                held = cells.setdefault(rows[0]["partition"], {RANKED: [], FLAT: []})
                held[arm].append(1 if primed((row["p_ge4"] for row in rows), bar) else 0)
        strata = {
            name: {
                "ranked_locations": len(held[RANKED]),
                "ranked_primed": sum(held[RANKED]),
                "flat_locations": len(held[FLAT]),
                "flat_primed": sum(held[FLAT]),
                "difference": (
                    round(
                        sum(held[RANKED]) / len(held[RANKED]) - sum(held[FLAT]) / len(held[FLAT]),
                        5,
                    )
                    if held[RANKED] and held[FLAT]
                    else None
                ),
            }
            for name, held in sorted(cells.items())
        }
        point = _stratified(cells)
        spread = _bootstrap(cells, draws, seed)
        ranked = [value for held in cells.values() for value in held[RANKED]]
        flat = [value for held in cells.values() for value in held[FLAT]]
        out[tag] = {
            "bar": bar,
            "pooled": {
                "ranked": _rate(ranked),
                "flat": _rate(flat),
                "difference": (
                    round(sum(ranked) / len(ranked) - sum(flat) / len(flat), 5)
                    if ranked and flat
                    else None
                ),
            },
            "stratified_difference": None if point is None else round(point, 5),
            "ci95": spread,
            "ratio": (
                round((sum(ranked) / len(ranked)) / (sum(flat) / len(flat)), 3)
                if ranked and flat and sum(flat)
                else None
            ),
            "by_partition": strata,
        }
    return out


def _locations_of(held: list) -> dict:
    out: dict = {}
    for row in held:
        out.setdefault(row["location"], []).append(row)
    return out


def _rate(values: list) -> dict:
    return {
        "locations": len(values),
        "primed": sum(values),
        "rate": round(sum(values) / len(values), 5) if values else None,
    }


def _stratified(cells: dict) -> float | None:
    """The Mantel-Haenszel weighted mean of the per-partition differences."""
    weight = 0.0
    total = 0.0
    for held in cells.values():
        one, other = held[RANKED], held[FLAT]
        if not one or not other:
            continue
        share = len(one) * len(other) / (len(one) + len(other))
        total += share * (sum(one) / len(one) - sum(other) / len(other))
        weight += share
    return None if not weight else total / weight


def _bootstrap(cells: dict, draws: int, seed: int) -> dict:
    """A percentile interval on [`_stratified`], resampling locations in their strata."""
    rng = random.Random(hunt.seed_of(seed, "compare"))
    values = []
    for _draw in range(int(draws)):
        resampled = {
            name: {
                arm: [rng.choice(held[arm]) for _at in held[arm]] if held[arm] else []
                for arm in (RANKED, FLAT)
            }
            for name, held in cells.items()
        }
        point = _stratified(resampled)
        if point is not None:
            values.append(point)
    if not values:
        return {}
    values.sort()
    return {
        "draws": len(values),
        "low": round(values[int(0.025 * len(values))], 5),
        "high": round(values[min(len(values) - 1, int(0.975 * len(values)))], 5),
        "excludes_zero": values[int(0.025 * len(values))] > 0.0,
    }


def extrapolate(arms: dict, stock: dict, target: int = 1000, bar: float = PRIMED_BAR) -> dict:
    """Hours to `target` DISTINCT primed locations by each route, and where each runs out.

    Off the measured rate and nothing else: primed locations a location opened,
    seconds a location, and how many locations the route can still reach. A route
    whose stock is smaller than the target cannot get there at any price, and
    saying so is the point of carrying the stock through.
    """
    tag = f"bar_{bar:.2f}".replace(".", "")
    out: dict = {"target": int(target), "bar": bar, "already_owned": stock.get("owned_primed")}
    for arm, block in arms.items():
        held = block.get(tag) or {}
        places = block.get("locations") or 0
        fresh = held.get("locations_newly_primed") or 0
        if not places:
            continue
        per_place = fresh / places
        seconds_per_place = (block.get("seconds") or 0.0) / places
        reachable = int(stock.get(arm) or 0)
        out[arm] = {
            "locations_opened": places,
            "newly_primed": fresh,
            "primed_per_location": round(per_place, 5),
            "seconds_per_location": round(seconds_per_place, 3),
            "hours_per_primed": (
                round(seconds_per_place / per_place / 3600, 3) if per_place else None
            ),
            "hours_to_target": (
                round(target / per_place * seconds_per_place / 3600, 1) if per_place else None
            ),
            "stock_locations": reachable,
            "primed_the_stock_can_reach": int(reachable * per_place),
            "reaches_target": bool(reachable * per_place >= target) if per_place else False,
        }
    return out


def marginal(held: list, bars=(PRIMED_BAR, SEATING_BAR)) -> dict:
    """The DEEPEN arm's whole point: what the k-th palette at a place is worth.

    Two readings at every k. **Per-candidate** is the chance the k-th palette
    itself clears, which is flat if palettes are exchangeable and falling if the
    draw is ordered. **Cumulative** is the chance a location is primed by its
    first k, which is what sets a candidate set's width: the k where its
    increment stops paying is the k to stop at.
    """
    out: dict = {}
    for band in sorted({row["band"] for row in held}):
        rows = [row for row in held if row["band"] == band]
        by_location: dict = {}
        for row in rows:
            by_location.setdefault(row["location"], []).append(row)
        places = len(by_location)
        highest = max((row["k"] for row in rows), default=0)
        block: dict = {"locations": places, "candidates": len(rows), "max_k": highest}
        for bar in bars:
            tag = f"bar_{bar:.2f}".replace(".", "")
            curve = []
            previous = 0.0
            for k in range(1, highest + 1):
                at_k = [row for row in rows if row["k"] == k]
                cleared = {
                    key
                    for key, rows_here in by_location.items()
                    if any(row["p_ge4"] >= bar for row in rows_here if row["k"] <= k)
                }
                alive = sum(1 for rows_here in by_location.values() if len(rows_here) >= k)
                cumulative = len(cleared) / max(1, places)
                curve.append(
                    {
                        "k": k,
                        "candidates_at_k": len(at_k),
                        "locations_with_k": alive,
                        "cleared_at_k": sum(1 for row in at_k if row["p_ge4"] >= bar),
                        "per_candidate_clear_rate": round(
                            sum(1 for row in at_k if row["p_ge4"] >= bar) / max(1, len(at_k)), 5
                        ),
                        "cumulative_primed": len(cleared),
                        "cumulative_rate": round(cumulative, 5),
                        "marginal_gain": round(cumulative - previous, 5),
                    }
                )
                previous = cumulative
            block[tag] = curve
        out[band] = block
    return out


# --------------------------------------------------------------------------- #
# The autopsy sheet.
# --------------------------------------------------------------------------- #
#: How many candidates each band of the autopsy sheet shows. The page answers one
#: question — does the judge's boundary look like a boundary to an eye — and a
#: few dozen either side of it answers that where hundreds only fill a scroll.
SHEET_ROWS = 24


def contact_sheet(name: str, record: dict, output: Path | None = None, rows: int = SHEET_ROWS):
    """The primed and the rejected on one page, sorted by `P(>=4)` and split at the bars.

    Three bands and not two, because the interesting reject is not the worst one:
    it is the candidate that came within a few points of the bar and did not
    clear it. Every band is sorted the same way and laid out the same way, so the
    comparison across a boundary is the eye's rather than the caption's.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    output = mine_dir(name) / "autopsy.html" if output is None else Path(output)
    made = sorted(record.get("made") or [], key=lambda row: -row["p_ge4"])
    counts = record.get("counts") or {}
    bands = (
        (
            f"PRIMED — P(&ge;4) &ge; {PRIMED_BAR}",
            [row for row in made if row["p_ge4"] >= PRIMED_BAR],
            "Every one of these primes its location on its own. A location holding one is "
            "a place this collection could seat, which is the unit the mine prices.",
        ),
        (
            f"Spanning the bar — {SEATING_BAR} &le; P(&ge;4) &lt; {PRIMED_BAR}",
            [row for row in made if SEATING_BAR <= row["p_ge4"] < PRIMED_BAR],
            "Over the bar the seating stage counts against today and under the one this "
            "mine calls primed. This is the band the two heights disagree about, and the "
            "only one where the choice of bar changes what the mine bought.",
        ),
        (
            f"Rejected — P(&ge;4) &lt; {SEATING_BAR}",
            # NOT sliced here: every band's heading says "N of M", and a band
            # that arrived pre-cut says "24 of 24" — which reads as *everything
            # was rejected and all of it is shown*, on the one band where the
            # denominator is the whole run.
            [row for row in made if row["p_ge4"] < SEATING_BAR],
            "The strongest of what neither bar admits. If these look like the band above "
            "them, the judge is the thing to look at next and not the draw.",
        ),
    )
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>mine {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>mine {html.escape(name)} — reject autopsy</h1>",
        # The arms this run actually holds, not a fixed three: a page that says
        # three over a two-arm comparison reads as an arm that bought nothing.
        f"<p class='lede'>{counts.get('made', 0):,} candidate(s) over "
        f"{', '.join(sorted({str(row['arm']) for row in made})) or 'no arm'}, sorted by "
        f"P(&ge;4). No quality bar admitted any of them; the bands below are read off the "
        f"scores at page time and are stored in no row.</p>",
    ]
    for heading, held, lede in bands:
        if not held:
            continue
        shown = held[:rows]
        lines += [
            f"<h2>{heading} ({len(shown)} of {len(held)})</h2>",
            f"<p class='lede'>{lede}</p>",
            "<div class='grid'>" + "".join(_card(row, sheet_module) for row in shown) + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _card(row: dict, sheet_module) -> str:
    import html

    from fractal_wallpapers.paths import rehome

    source = Path(rehome(row["picture"])) if row.get("picture") else None
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if source is not None and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    facts = [
        f"{row['arm']} - k{row['k']} - {row['band']}",
        f"{row['partition']} - {row['mode']} ({row['mode_kind']}) - {row['palette_group']}",
        f"map {row['colormap']}, dominant in {', '.join(row.get('cells') or []) or 'nothing'}",
        f"P(>=4) {row['p_ge4']:.4f}, P(>=3) {row['p_ge3']:.4f}, {row['seconds']}s"
        + (" - levelled" if row.get("acted") else ""),
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(row['key'])}</b><ul>{caption}</ul></figcaption></figure>"
    )


def _spread(values: list) -> dict:
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "max": round(ordered[-1], 5),
        "p99": round(ordered[min(len(ordered) - 1, int(0.99 * len(ordered)))], 5),
        "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 5),
        "median": round(statistics.median(ordered), 5),
    }


__all__ = [
    "ARMS",
    "BENCH_K",
    "BENCH_KINDS",
    "BENCH_MAPS",
    "BOOTSTRAP_DRAWS",
    "BUDGET_SECONDS",
    "DEEPEN",
    "DEEPEN_K",
    "DEFAULT_SEED",
    "FIELDS",
    "FLAT",
    "NEAR_BAND",
    "OVER_BAND",
    "PER_LOCATION",
    "PICTURES",
    "PLAN_HEADROOM",
    "PRIMED_BAR",
    "PROFILE_NAME",
    "RANKED",
    "RECORD_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "SEATING_BAR",
    "SHARES",
    "SHEET_ROWS",
    "UNIT",
    "Clock",
    "MineRefused",
    "Stages",
    "Unit",
    "arm_readout",
    "bench",
    "bench_table",
    "best_by_location",
    "build_plan",
    "compare",
    "contact_sheet",
    "deepen_places",
    "extrapolate",
    "fields_dir",
    "flat_places",
    "make",
    "marginal",
    "merge",
    "mine_dir",
    "per_candidate_at",
    "pictures_dir",
    "plan_breadth",
    "plan_deepen",
    "population",
    "primed",
    "profile_path",
    "ranked_places",
    "record_path",
    "rows_path",
    "run",
    "scores_path",
    "taken_maps",
    "weave",
]
