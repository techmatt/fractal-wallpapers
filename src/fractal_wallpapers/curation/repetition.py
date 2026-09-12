"""How many times the gradient is traversed, asked of an eye rather than a head.

`Palette.cycles` says how many times a render walks its colormap across the
field. The pool has almost no opinion about it: **2,262 of 374,186 rows** stand
at anything but one, 0.605% of the store, and 44 of those are seated. Every one
of those rows arrived in the last few days or came in with the maker-era corpora,
so neither the render judge nor the fine head was fitted on a population that
contained the axis — and a head's reading of a picture whose defining property it
has never been trained against is not evidence about the property.

`palette_variant_mine_ckpt120` measured the heads *preferring* repeat 1 —
36.4% of matched pairs won at repeat 3 against 52.6% at repeat 1, monotone in the
tile count — and [`rotation.REPEAT`] holds the axis at 1 on that reading. This
leg exists to put a person in front of the same question, because the reading
that set the policy is the reading the policy makes self-confirming.

## The pair is the unit, and it is matched by construction

Every repeated tile is drawn beside its own unrepeated twin at the same place,
the same mode, the same settings, the same map and the same frame. `phase` is
held at **0** on both sides throughout: 1,713 of the 2,262 repeat rows in the
store carry a rotation as well, so the axis as the pool holds it is confounded
with the one [`rotation`] just measured, and a sitting that inherited that
confound would answer neither question.

What makes the match a property of the code rather than a promise is
[`plan_of`]: the control's own key is **re-derived** through
[`hunt.Maker.recipe_for`] with no overrides and checked against the key the store
holds it under. A control that does not reproduce is dropped and counted. So the
repeat and its control are two runs of one derivation differing in one member,
and a control carrying knobs the candidate path does not spend — a
[`label_migration`] row, say — cannot quietly become half of a pair whose other
half was built a different way.

## The rungs, and why the folded arm gets its own share

A **cyclic** map is walked end to end and meets itself, so `cycles` is the tile
count exactly: the rungs are 2 and 3. A **sequential** map is baked folded — an
out-and-back — so one pass is already two traversals of the base ramp and
`cycles = 2` is **four**. That is the smallest meaningful rung on that arm and
the only one it draws.

Sequential maps are 156 of the library's 1,021 and thinner still above any bar,
so letting the pool's proportions decide would put a handful of them on the page.
[`FOLDED_SHARE`] is a deliberate over-share instead, stated here and recorded on
the draw.

**The direct traps are excluded outright.** A trap figure over a flat ground has
no field for a traversal to cross, so the axis is a byte-for-byte no-op on them —
`engine/src/direct_trap.rs`, and the eye sheet of 2026-09-10 measured it at
eleven tiles to one sha256. The store holds **28** trap rows at `cycles != 1`
anyway, which are that many duplicate pictures under a name claiming a variant.

## It gates on nothing, and that is the point rather than an oversight

Every other draw in this project is aimed at a band, a bar or the top of a queue.
This one may not be: the repeats the current heads happen to tolerate are exactly
the wrong sample, and a page cut from them would measure the heads' existing
indifference and call it Matt's taste. So the population is every row that can
form a pair and no reading enters it. Both columns are **recorded** on every
tile and neither is a filter — `p_fine` orders the page and nothing else.

## The economics: a repeat is a recolour, and this leg pays full price anyway

`Palette.cycles` is spent after the field is read, so a repeat is in principle a
colormap lookup over a field somebody already dumped — [`colorize.recolored`] has
taken the whole palette pass since 2026-09-11.

**This leg gets none of that, by construction, and it is the right trade.** The
sharing is per (location, mode) *within a leg's own field cache*, and the draw
takes **one pair a location** so no place can carry the page — so every block
holds exactly one candidate and each repeat pays its own dump. The control's
field was dumped by whatever leg made it, weeks ago, and swept.

Measured on `repeat_ckpt120`: 125 repeats, **3.03 engine-seconds each**, 145 s of
wall on three workers. A full-price render for every tile, and it is 145 seconds
— so the spreading rule wins on every axis that matters here. A leg that wanted
the sharing back would have to draw several pairs at one place, which is the one
thing a 125-tile page must not do.

Rows land in the ledger through the ordinary door ([`merge`]), because a tile
Matt labels has to be a row a label can key to.

## The page's own order is read, not inherited

*Score everything and gate on nothing* has a second half the pool cannot supply.
`curate gallery-grade score-pool` writes `p_fine` for the rows clearing the render
bar and for no others — **42,300 of 374,186** — so the column it leaves covers
**8 of the first 125 controls drawn here**, and a page ordered off it would be 94%
unread tail. [`fine_for`] runs the head over every tile instead, at the candidate
geometry it was fitted at, and writes nothing. Running `score-pool` after the
merge is still worth doing for the gallery's sake; this leg no longer needs it.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import (
    candidate_ledger,
    colorize,
    depth,
    hunt,
    mine,
    recipes,
    release,
    remode,
)
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree this leg's output lands in, under the regenerable tree. It is a
#: member of [`candidate_ledger.POOL_SUBTREES`], which is what makes its pictures
#: reachable by `curate candidate-ledger orphans`: a leg whose subtree that sweep
#: cannot enumerate leaks every render of a killed run with no row anywhere.
UNIT = "repetition"

#: What the appended files and the records are called.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"
SEQUENCE_NAME = "sequence.jsonl"
DRAW_NAME = "draw.json"
RECORD_NAME = "repetition.json"
MERGE_NAME = "merge.json"
PLAN_NAME = "plan.jsonl"
SHEET_NAME = "sheet_plan.json"

#: The tile counts a **cyclic** map is repeated at. Two and three: `cycles` is
#: the traversal count exactly on a map that meets itself, and 1 is the control
#: rather than a sampled dose — the pool is already almost entirely 1.
CYCLIC_RUNGS: tuple[float, ...] = (2.0, 3.0)

#: The tile count a **folded** (sequential) map is repeated at. Two only, and it
#: is **four** passes of the base ramp — a folded map at `cycles = 1` is already
#: an out-and-back, so this is the smallest rung that means anything there.
FOLDED_RUNGS: tuple[float, ...] = (2.0,)

#: What share of the pairs the folded arm gets, against its **15.3%** of the
#: library (156 maps of 1,021) and less than that above any bar. A deliberate
#: over-share: the arm carries the rung whose traversal count the page has to
#: print to be honest, and a handful of tiles could not answer for it.
FOLDED_SHARE = 0.32

#: Tiles in one sitting, **controls included**. Half of it is repeats, which is
#: the oversampling this batch is: about **82x** the rate the store stands at
#: (0.605%) and further still above the rate production draws, where
#: `--vary-palette` is off by default and draws `cycles != 1` at 0.3 of the
#: varied shots when it is on. Anything fitted on these rows inherits that prior
#: and it is written down here, on the draw's record, and in
#: `data/batch_caveats.md` rather than left to be discovered.
TILES = 250

#: How many engines this leg drives at once. **Three**, this machine's render
#: pool, read off the module that owns it rather than restated — more than three
#: at once makes the desktop unusable while a leg runs.
WORKERS = release.DEFAULT_WORKERS

#: How long the render stage may spend, in wall seconds. Generous against the
#: work, which is at most [`TILES`]/2 candidates at a full render each: 125 of
#: them took **145 s** of wall on three workers, measured on `repeat_ckpt120`.
BUDGET_SECONDS = 1800.0


class RepetitionRefused(RuntimeError):
    """A draw this leg will not make, or a population it cannot trust."""


# --------------------------------------------------------------------------- #
# Where it keeps things.
# --------------------------------------------------------------------------- #
def repetition_dir(name: str) -> Path:
    """The subtree one batch owns: its rows, its pictures, its fields, its records."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    return repetition_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    return repetition_dir(name) / SCORES_NAME


def sequence_path(name: str) -> Path:
    return repetition_dir(name) / SEQUENCE_NAME


def draw_path(name: str) -> Path:
    return repetition_dir(name) / DRAW_NAME


def record_path(name: str) -> Path:
    return repetition_dir(name) / RECORD_NAME


def merge_path(name: str) -> Path:
    return repetition_dir(name) / MERGE_NAME


def plan_path(name: str) -> Path:
    return repetition_dir(name) / PLAN_NAME


def sheet_plan_path(name: str) -> Path:
    return repetition_dir(name) / SHEET_NAME


def fields_dir(name: str) -> Path:
    """Where this leg's dumped fields live. One per (location, mode)."""
    return repetition_dir(name) / "fields"


def pictures_dir(name: str) -> Path:
    """The repeat renders, named by **recipe key** — which is what lets a re-run
    find the picture it already made instead of drawing it a second time."""
    return repetition_dir(name) / candidate_ledger.PICTURES_NAME


# --------------------------------------------------------------------------- #
# The traversal count, which is not the `cycles` value.
# --------------------------------------------------------------------------- #
def traversals(cycles: float, folded: bool) -> float:
    """How many times the **base ramp** is walked. The number the page prints.

    A folded map is baked as an out-and-back, so every pass of it is two passes of
    the gradient the map was drawn as. `cycles = 2` on a sequential map is
    therefore **4x** and on a cyclic map it is 2x, and a card that printed
    `cycles` under both would be printing two different quantities under one
    label. The number Matt looks at and the number the row records must not be
    different things, so the row records `cycles` and the card prints this.
    """
    return float(cycles) * (2.0 if folded else 1.0)


# --------------------------------------------------------------------------- #
# The population: every row that can be half of a pair.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Control:
    """One unrepeated row this leg may put a repeat beside, and what is known of it."""

    key: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: Whether the map is baked folded, which is what [`traversals`] turns a rung
    #: into and which arm the control belongs to. Read off the cyclic set and
    #: never off the recipe — `mirror` is the map's bake.
    folded: bool
    picture: str
    #: The render judge's two columns, recorded and never gated on.
    p_ge4: float
    p_ge3: float
    #: The fine head's reading, or `None` where it has none. The page's order, and
    #: a row it cannot read sorts after every row it can rather than being cut.
    p_fine: float | None
    #: The whole stored recipe block, which is what the pair is built out of.
    recipe: dict


def population(log=print) -> dict:
    """Every row that could be half of a pair, with **no bar of any kind applied**.

    One streaming pass of the ledger and one filtered pass of the score sidecar —
    the two files are over half a gigabyte together and this wants a column off
    each, not the whole of either. `known` is every recipe key in the store,
    collected in the same pass because [`plan_of`] has to have it and a second
    pass for it would be another read of the rows file.

    Five exclusions, and each is about whether a **pair** can exist rather than
    about quality:

    * a direct trap, where the axis is a no-op, so a repeat would be a second
      recipe key for a byte-identical picture;
    * a row already carrying a traversal or a rotation, which is not a control;
    * a row off the candidate regime, whose picture is not the geometry the
      columns on it were read at;
    * a human rejection, which is honoured everywhere in this project;
    * a row with no picture on disk, whose repeat could share no dumped field and
      whose control side of the page could not be served.
    """
    from fractal_wallpapers.models import gallery_grade_train as grade

    began = time.monotonic()
    cyclic = colorize.cyclic()
    refused = {
        "direct_trap": 0,
        "already_repeated": 0,
        "rotated": 0,
        "off_regime": 0,
        "rejected": 0,
        "no_picture": 0,
        "picture_absent": 0,
        "no_score": 0,
    }
    known: set = set()
    held: list = []
    scanned = 0
    for row in candidate_ledger.stream():
        scanned += 1
        known.add(str(row["key"]))
        recipe = row.get("recipe") or {}
        palette = recipe.get("palette") or {}
        if colorize.kind_of(str(recipe.get("mode"))) == colorize.DIRECT_KIND:
            refused["direct_trap"] += 1
            continue
        if float(palette.get("cycles", 1.0) or 1.0) != 1.0:
            refused["already_repeated"] += 1
            continue
        if float(palette.get("phase", 0.0) or 0.0) != 0.0:
            refused["rotated"] += 1
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
        held.append(row)
    log(
        f"[repetition] {scanned:,} ledger row(s) in {time.monotonic() - began:.1f}s; "
        f"{len(held):,} could be a control"
    )
    live = candidate_ledger.live_artifact()
    keys = {str(row["key"]) for row in held}
    readings = candidate_ledger.scores_by_recipe(
        (
            score
            for score in candidate_ledger.stream_scores()
            if str(score.get("recipe_key")) in keys
        ),
        artifact=live,
    )
    present = candidate_ledger.present_pictures(held)
    fine = _fine_column(grade, log=log)
    controls: list[Control] = []
    for row in held:
        key = str(row["key"])
        reading = readings.get(key)
        if reading is None:
            refused["no_score"] += 1
            continue
        if key not in present:
            refused["picture_absent"] += 1
            continue
        recipe = dict(row.get("recipe") or {})
        colormap = str(recipe["colormap"])
        controls.append(
            Control(
                key=key,
                location=str((row.get("location") or {}).get("key")),
                partition=str(row.get("partition")),
                mode=str(recipe["mode"]),
                colormap=colormap,
                folded=colormap not in cyclic,
                picture=str(row.get("picture")),
                p_ge4=float(reading.get("p_ge4") or 0.0),
                p_ge3=float(reading.get("p_ge3") or 0.0),
                p_fine=fine.get(key),
                recipe=recipe,
            )
        )
    folded = sum(1 for control in controls if control.folded)
    log(
        f"[repetition] {len(controls):,} control(s) at "
        f"{len({control.location for control in controls}):,} location(s); "
        f"{folded:,} on a folded map, {len(controls) - folded:,} on a cyclic one"
    )
    return {
        "judge_artifact": live,
        "ledger_rows": scanned,
        "refused": refused,
        "controls": controls,
        "known": known,
        "fine_readings": len(fine),
        "seconds": round(time.monotonic() - began, 2),
    }


def _fine_column(grade, log=print) -> dict:
    """`{recipe key: p_fine}` off the pool's own column, which is **bar-gated**.

    What `curate gallery-grade score-pool` wrote, and it is not the whole store:
    the fine head is deployed over rows clearing the render bar and nothing else
    ([`solve.at_fine_bar`]), so this covers **42,300 of 374,186** rows. That is
    fine for a reader asking what the pool thinks and useless as this page's
    order — measured on the first draw here, **8 of 125** controls carried one,
    which would have left 94% of the page in the unread tail.

    So this is the *cheap* source and [`fine_for`] is the one the sheet spends.
    Kept because it is free where it hits, and a reading the pool already holds is
    the reading the pool was seated on.
    """
    where = grade.pool_scores_path()
    if not where.is_file():
        log(
            f"[repetition] {tracked_name(where)} is not there, so no row carries a p_fine "
            f"yet. The draw is unaffected; the sheet reads its own through `fine_for`"
        )
        return {}
    out: dict = {}
    for line in where.open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row["key"])] = float(row.get("p_ge4") or 0.0)
    log(f"[repetition] {len(out):,} row(s) carry a p_fine on {grade.pool_scores_run()}")
    return out


def fine_for(pictures: dict, device: str = "auto", log=print) -> dict:
    """`{recipe key: p_fine}` by **running the head** on these pictures, bar or no bar.

    This is what *score everything and gate on nothing* costs, and it is the half
    of the instruction the pool's own column cannot satisfy. `score_pool` writes
    `p_fine` for the rows clearing the render bar, which is what the gallery needs
    and the opposite of what this page needs: the repeats the heads already
    tolerate are exactly the sample a sitting about the axis must not be cut from.

    The head is not *unable* to read the other rows — 42,300 of 374,186 is a
    deployment rule and not a capability — so this reads every tile on the page
    through it at the candidate geometry the head was fitted at.
    [`rotation.score_fine`] is that read, reached rather than restated: it
    resolves the shipped ensemble through `gallery_grade_train.shipped_runs` and
    averages on the probability scale, and a second spelling here would score this
    page on one column while the pool it is compared against stands on another.

    **Nothing is written.** `pool_scores.jsonl` is a one-shot file the gallery
    reads; a page's own ungated reading is not that file's business and writing it
    there would put readings below the bar into a column every downstream reader
    takes as bar-cleared.
    """
    from fractal_wallpapers.curation import rotation
    from fractal_wallpapers.paths import Tiers, rehome

    tiers = Tiers.current()
    keys, paths = [], []
    absent = 0
    for key, picture in pictures.items():
        where = None if not picture else rehome(str(picture), tiers)
        if where is None or not where.is_file():
            absent += 1
            continue
        keys.append(str(key))
        paths.append(where)
    if not paths:
        log("[repetition] no tile has a picture on disk; the page has no order to be read in")
        return {}
    readings, column = rotation.score_fine(paths, device=device, log=log)
    log(
        f"[repetition] {len(readings):,} tile(s) read through the fine head on {column}; "
        f"{absent:,} had no picture on disk"
    )
    return dict(zip(keys, readings, strict=True))


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Pair:
    """One control and the repeat drawn to sit beside it."""

    control: Control
    #: The `Palette.cycles` the repeat is rendered at.
    rung: float
    #: What both tiles are marked with on the page, so a reader can see the pair.
    pair: str

    def traversals(self) -> tuple[float, float]:
        """`(control, repeat)` — the true counts, which the card prints."""
        return (
            traversals(1.0, self.control.folded),
            traversals(self.rung, self.control.folded),
        )


def draw(world: dict, tiles: int = TILES, seed: int = 0, share: float = FOLDED_SHARE) -> tuple:
    """`(pairs, shape)` — the matched draw, seeded and over **locations**.

    One pair a location, drawn without replacement, so no place can carry the
    page. The folded arm is drawn **first** because it is the scarce one: the
    maps are 15.3% of the library and the arm is asked for [`FOLDED_SHARE`] of
    the pairs, so drawing the plentiful arm first would leave it short at the
    places it needs.

    Rungs are dealt rather than sampled. The folded arm is all
    [`FOLDED_RUNGS`]; the cyclic arm splits its pairs evenly over
    [`CYCLIC_RUNGS`] and shuffles the assignment, which puts the same count on
    each rung instead of a multinomial's — a draw of 85 over two rungs at a coin
    flip lands 8 apart about a third of the time, and a rung comparison is what
    this page is for.
    """
    rng = random.Random(f"{int(seed)}|{UNIT}")
    wanted = max(1, int(tiles) // 2)
    by_place: dict = {}
    for control in world["controls"]:
        by_place.setdefault(control.location, []).append(control)
    folded_places = sorted(
        place for place, held in by_place.items() if any(one.folded for one in held)
    )
    cyclic_places = sorted(
        place for place, held in by_place.items() if any(not one.folded for one in held)
    )
    rng.shuffle(folded_places)
    rng.shuffle(cyclic_places)
    folded_wanted = min(len(folded_places), round(wanted * float(share)))
    taken: set = set()
    pairs: list[Pair] = []

    def pick(place: str, folded: bool) -> Control:
        """One control at a place, seeded — never the best, which would aim the draw."""
        choices = sorted(
            (one for one in by_place[place] if one.folded is folded), key=lambda one: one.key
        )
        return choices[rng.randrange(len(choices))]

    for place in folded_places:
        if len(pairs) >= folded_wanted:
            break
        taken.add(place)
        pairs.append(
            Pair(control=pick(place, True), rung=FOLDED_RUNGS[0], pair=f"p{len(pairs):04d}")
        )
    folded_drawn = len(pairs)
    cyclic_wanted = wanted - folded_drawn
    cyclic_taken = [place for place in cyclic_places if place not in taken][:cyclic_wanted]
    rungs = [CYCLIC_RUNGS[index % len(CYCLIC_RUNGS)] for index in range(len(cyclic_taken))]
    rng.shuffle(rungs)
    for place, rung in zip(cyclic_taken, rungs, strict=True):
        pairs.append(Pair(control=pick(place, False), rung=float(rung), pair=f"p{len(pairs):04d}"))

    rung_counts: dict = {}
    for pair in pairs:
        arm = "folded" if pair.control.folded else "cyclic"
        rung_counts.setdefault(arm, {}).setdefault(f"{pair.rung:g}", 0)
        rung_counts[arm][f"{pair.rung:g}"] += 1
    shape = {
        "seed": int(seed),
        "tiles_asked": int(tiles),
        "pairs_wanted": wanted,
        "pairs": len(pairs),
        "tiles": 2 * len(pairs),
        "folded_share_asked": float(share),
        "folded_share_drawn": round(folded_drawn / max(1, len(pairs)), 4),
        "folded_share_in_the_library": round(156 / 1021, 4),
        "folded_pairs": folded_drawn,
        "cyclic_pairs": len(pairs) - folded_drawn,
        "by_arm_and_rung": rung_counts,
        "eligible_locations": len(by_place),
        "folded_capable_locations": len(folded_places),
        "cyclic_capable_locations": len(cyclic_places),
        "modes": _tally(pair.control.mode for pair in pairs),
        "partitions": _tally(pair.control.partition for pair in pairs),
        "controls_the_fine_head_has_read": sum(
            1 for pair in pairs if pair.control.p_fine is not None
        ),
        "rung_assignment": "dealt evenly over the rungs and then shuffled, not sampled",
        "short_of_the_ask": wanted - len(pairs),
    }
    return pairs, shape


def _tally(values) -> dict:
    """`{value: count}`, most-used first — the shape every readout here reports in."""
    counts: dict = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


# --------------------------------------------------------------------------- #
# The plan: what has to be rendered, and the check that a pair is a pair.
# --------------------------------------------------------------------------- #
def plan_of(maker, pairs: list, known: set, log=print) -> tuple[list, dict]:
    """`(units, shape)` — the repeats to render, with every control re-derived.

    **The control's key is recomputed and checked**, which is what makes *the two
    tiles differ in the traversal and in nothing else* a property of the code.
    [`hunt.Maker.recipe_for`] with no overrides is exactly what made the control,
    so re-running it has to reproduce the key the store holds it under; the repeat
    is the same call with `palette={"cycles": n}` and
    [`hunt.Maker.palette_for`] lays that override over the same defaults. Two runs
    of one derivation, one member apart.

    A control that does not reproduce is **dropped**, not repaired. It means the
    row was made by some other path — a [`label_migration`] recipe carries knobs
    the candidate path never spends — so its repeat would differ from it in the
    traversal *and* in whatever else that path moved, and the pair would answer a
    question nobody asked.

    A repeat whose key the ledger already holds is not rendered and the pair
    **stays on the page**: 2,262 rows already carry a traversal, so a draw that
    lands on one is a tile this leg gets for free rather than a pair it loses.
    """
    units: list = []
    keys: dict = {}
    shape = {
        "pairs": len(pairs),
        "controls_that_did_not_reproduce": 0,
        "repeats_already_in_ledger": 0,
        "repeats_to_render": 0,
    }
    lost: list = []
    at = 0
    for pair in pairs:
        control = pair.control
        recipe = recipes.of_record(control.recipe)
        place, frame = remode.place_of(recipe), remode.frame_of(recipe)
        plain = mine.Unit(
            arm=UNIT,
            location=control.location,
            partition=control.partition,
            mode=control.mode,
            colormap=control.colormap,
            k=0,
            band=UNIT,
            mode_params=dict(recipe.mode_params or {}),
        )
        if recipes.key_of(maker.recipe_for(plain, place, frame)) != control.key:
            shape["controls_that_did_not_reproduce"] += 1
            lost.append(control.key)
            continue
        at += 1
        unit = mine.Unit(
            arm=UNIT,
            location=control.location,
            partition=control.partition,
            mode=control.mode,
            colormap=control.colormap,
            k=at,
            # The control this repeat is matched to. `band` is the mine's word
            # for the prior a draw was taken under, and the control is exactly
            # that here — so every readout a mine already has reads this leg.
            band=pair.pair,
            mode_params=dict(recipe.mode_params or {}),
            palette={"cycles": float(pair.rung)},
        )
        twin = maker.recipe_for(unit, place, frame)
        key = recipes.key_of(twin)
        keys[pair.pair] = key
        if key in known:
            shape["repeats_already_in_ledger"] += 1
            continue
        units.append((unit, pair, place, frame, key, twin))
    shape["repeats_to_render"] = len(units)
    shape["the_ones_that_did_not_reproduce"] = lost[:20]
    log(
        f"[repetition] {len(units):,} repeat(s) to render, "
        f"{shape['repeats_already_in_ledger']:,} already in the ledger, "
        f"{shape['controls_that_did_not_reproduce']:,} control(s) dropped for not reproducing"
    )
    return units, (shape | {"repeat_keys": keys})


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def run(
    name: str,
    *,
    tiles: int = TILES,
    seed: int = 0,
    share: float = FOLDED_SHARE,
    budget: float = BUDGET_SECONDS,
    workers: int = WORKERS,
    device: str = "auto",
    world: dict | None = None,
    log=print,
) -> dict:
    """One batch, drawn and rendered. Rows land as they land; the record comes back.

    [`remode.run`]'s shape, and it borrows that leg's workers outright —
    [`remode.render_block`], [`remode.blocks_of`], [`remode.place_of`] and
    [`remode.frame_of`] are generic over *a unit, a place, a frame and a key*,
    which is exactly this plan's shape. A second spelling of the render act is how
    a leg ends up stocking the pool with rows nothing else can be compared
    against, and [`mine.make`]'s own `mode_params` defect is what that costs.

    **This holds the pool.** [`population`] streams the ledger and its sidecar;
    nothing else that loads them may run beside it.
    """
    started = time.monotonic()
    world = population(log=log) if world is None else world
    pairs, drawn = draw(world, tiles=tiles, seed=seed, share=share)
    if not pairs:
        raise RepetitionRefused(
            "the draw came back empty, so there is no pair to render. Every control is a "
            "ledger row at cycles 1 and phase 0 with a picture on disk; a store with none "
            "of those is a store this leg has nothing to say about."
        )
    # The parent's Maker owns the field cache and derives every key. It never
    # judges, so it never loads the judge; the workers hold theirs.
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
    units, shape = plan_of(maker, pairs, world["known"], log=log)
    blocks = remode.blocks_of(units)
    build = candidate_ledger.live_engine()
    price = hunt.Price()
    clock = mine.Clock()
    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    sequence_file = sequence_path(name)
    artifact = hunt._artifact()
    made: list = []
    counts = {
        "planned": len(units),
        "made": 0,
        "failed": 0,
        "stopped_for_budget": 0,
        "autolevel_acted": 0,
        "fields_swept": 0,
        "workers": depth.workers_for(blocks, workers, log=log),
        "location_blocks": len(blocks),
    }
    by_at = {at: entry for block in blocks for at, entry in block}
    render_started = time.monotonic()
    deadline = render_started + float(budget)
    spent = 0.0

    def take(at: int, result: dict) -> None:
        """One landed repeat, written by the PARENT. Never by a worker."""
        nonlocal spent
        if "failed" in result:
            counts["failed"] += 1
            log(f"[repetition] {result.get('key')} failed: {result['failed']}")
            return
        unit, pair, _place, _frame, key, recipe = by_at[at]
        stages = result["stages"]
        origin = {
            "key": f"{name}|{at:05d}",
            "run": name,
            "candidate": f"{at:05d}",
            "location": {"key": unit.location, "partition": unit.partition},
        }
        stored = candidate_ledger.row(
            recipe=recipe,
            key=key,
            source=origin,
            colour=result["colour"],
            picture=tracked_name(Path(result["picture"])),
            texture_flat=result["texture_flat"],
            engine=build,
        )
        stored["hunt"] = candidate_ledger.hunt_block(
            {"seconds": round(stages.total(), 3), **unit.named()}
        )
        hunt._append(rows_file, stored)
        hunt._append(
            scores_file,
            candidate_ledger.score_row(
                key=key,
                artifact=artifact,
                regime=recipe.regime.spelled,
                head=hunt.kind_of(unit.mode, result["texture_flat"]),
                read=result["verdict"],
                source=origin,
            ),
        )
        spent += stages.total()
        price.add(unit.partition, stages.total(), band=unit.arm)
        counts["made"] += 1
        counts["autolevel_acted"] += int(result["acted"])
        verdict = result["verdict"]
        row = {
            "key": key,
            "pair": pair.pair,
            "of_key": pair.control.key,
            "location": unit.location,
            "partition": unit.partition,
            "mode": unit.mode,
            "colormap": unit.colormap,
            "folded": bool(pair.control.folded),
            "cycles": float(pair.rung),
            "traversals": traversals(pair.rung, pair.control.folded),
            "p_ge4": round(float(verdict.get("p_ge4") or 0.0), 6),
            "p_ge3": round(float(verdict.get("p_ge3") or 0.0), 6),
            "control_p_ge4": round(pair.control.p_ge4, 6),
            "control_p_ge3": round(pair.control.p_ge3, 6),
            # The repeat's reading minus its control's, on the render judge's own
            # column. **Recorded and never acted on**: this leg gates on nothing,
            # and a head that has not seen the axis is not evidence about it.
            "delta_p_ge4": round(float(verdict.get("p_ge4") or 0.0) - pair.control.p_ge4, 6),
            "acted": bool(result["acted"]),
            "seconds": round(stages.total(), 3),
            "picture": tracked_name(Path(result["picture"])),
        }
        made.append(row)
        hunt._append(
            sequence_file,
            {"schema": SCHEMA, "at": at, **row, "autolevel": result["autolevel"]},
        )
        clock.add(
            stages,
            {"partition": unit.partition, "mode": unit.mode, "acted": bool(result["acted"])},
        )

    def payload_of(block: list) -> tuple:
        return (
            name,
            device,
            str(fields_dir(name)),
            str(pictures_dir(name)),
            [
                (at, (unit, place, frame, key))
                for at, (unit, _pair, place, frame, key, _recipe) in block
            ],
            deadline,
        )

    if counts["workers"] <= 1:
        for block in blocks:
            if time.monotonic() >= deadline:
                continue
            for at, result in remode.render_block(payload_of(block)):
                take(at, result)
    else:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(
            max_workers=counts["workers"],
            initializer=depth._worker_init,
            initargs=(release.engine_threads_for(counts["workers"]),),
        ) as pool:
            for done, landed in enumerate(
                pool.map(remode.render_block, [payload_of(block) for block in blocks]), start=1
            ):
                for at, result in landed:
                    take(at, result)
                if done % 25 == 0:
                    counts["fields_swept"] += mine.colorize_module().sweep_fields(maker.fields)
    wall = time.monotonic() - render_started
    counts["stopped_for_budget"] = max(0, len(units) - counts["made"] - counts["failed"])
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": name,
        "config": {
            "tiles": int(tiles),
            "seed": int(seed),
            "folded_share": float(share),
            "cyclic_rungs": list(CYCLIC_RUNGS),
            "folded_rungs": list(FOLDED_RUNGS),
            "phase": 0.0,
            "phase_is": "held at 0 on BOTH sides throughout. 1,713 of the store's 2,262 "
            "repeat rows carry a rotation too, so the axis as the pool holds it is "
            "confounded with the one `curate rotate` measured",
            "gated_on": "nothing. Both columns are recorded on every tile and neither "
            "selects one — the repeats the current heads tolerate are the wrong sample",
            "budget_seconds": float(budget),
            "workers": counts["workers"],
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
            "held": "family, frame, maxiter, regime, mode, mode_params, curve, colormap and "
            "the autolevel stamp — carried because plan_of never names them. Moved: "
            "Palette.cycles, and the control's own key is re-derived and checked so that "
            "is provable rather than promised",
        },
        "population": {
            "ledger_rows": world["ledger_rows"],
            "refused": world["refused"],
            "controls": len(world["controls"]),
            "fine_readings": world["fine_readings"],
            "read_seconds": world["seconds"],
        },
        "draw": drawn,
        "plan": {key: value for key, value in shape.items() if key != "repeat_keys"},
        "counts": counts,
        "budget": {
            "is": "WALL seconds of rendering, spent by however many engines are on the leg",
            "allowed": float(budget),
            "render_wall": round(wall, 2),
            "wall_seconds": round(time.monotonic() - started, 2),
            "engine_seconds": round(spent, 2),
            "concurrency": round(spent / max(1e-9, wall), 3),
            "seconds_per_candidate": round(spent / max(1, counts["made"]), 4),
            "seconds_per_candidate_is": "per ENGINE, and it is a FULL render rather than "
            "a recolour: the draw takes one pair a location, so every block holds one "
            "candidate and shares its dump with nothing. See the module docstring",
        },
        "price": price.table(),
        "profile": clock.table(),
        "made": made,
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "sequence_path": tracked_name(sequence_file),
    }
    _write_json(record_path(name), record)
    _write_json(
        draw_path(name),
        {
            "schema": SCHEMA,
            "name": name,
            "draw": drawn,
            "repeat_keys": shape["repeat_keys"],
            "pairs": [
                {
                    "pair": pair.pair,
                    "control": pair.control.key,
                    "repeat": shape["repeat_keys"].get(pair.pair),
                    "location": pair.control.location,
                    "partition": pair.control.partition,
                    "mode": pair.control.mode,
                    "colormap": pair.control.colormap,
                    "folded": pair.control.folded,
                    "cycles": pair.rung,
                    "traversals": list(pair.traversals()),
                    "control_picture": pair.control.picture,
                    "control_p_ge4": round(pair.control.p_ge4, 6),
                    "control_p_ge3": round(pair.control.p_ge3, 6),
                    "control_p_fine": pair.control.p_fine,
                    "control_recipe": pair.control.recipe,
                }
                for pair in pairs
            ],
        },
    )
    log(
        f"[repetition] {counts['made']:,} repeat(s) in {wall:.0f}s of wall on "
        f"{counts['workers']} worker(s); {len(pairs):,} pair(s) drawn — "
        f"{tracked_name(record_path(name))}"
    )
    return record


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def merge(name: str, log=print) -> dict:
    """Upsert this leg's two files into the ledger and its sidecar.

    [`remode.merge`]'s body over this module's paths. Separate from the run for
    its reason too — the ledger is rewritten whole on every upsert, so a merge per
    candidate is not a write.

    **`curate gallery-grade score-pool` has to run after this.**
    `pool_scores.jsonl` is a one-shot file, so a repeat merged and not scored
    carries no `p_fine` — and `p_fine` is what the sheet is ordered in.
    """
    rows = hunt._read(rows_path(name))
    scores = hunt._read(scores_path(name))
    if not rows:
        raise RepetitionRefused(
            f"{tracked_name(rows_path(name))} holds no row, so there is nothing to merge. "
            f"This leg writes its rows as it makes them; an empty file means none landed."
        )
    written = candidate_ledger.merge(rows, scores, log=log)
    report = {
        "schema": SCHEMA,
        "name": name,
        "merged": len(rows),
        "ledger": written["ledger"],
        "scores": written["scores"],
        "recorded": written["recorded"],
        "repeat_draws": written["repeat_draws"],
        "pruned": written["pruned"],
        "locations_touched": len({str((row.get("location") or {})["key"]) for row in rows}),
        "next": "fractal-wallpapers gallery-grade score-pool — pool_scores.jsonl is "
        "one-shot and these rows carry no p_fine until it runs",
    }
    _write_json(merge_path(name), report)
    log(
        f"[repetition] merged {len(rows):,} row(s): the ledger holds "
        f"{written['ledger']['rows']:,} recipes, {written['ledger']['new']:,} of them new"
    )
    return report


# --------------------------------------------------------------------------- #
# The sheet plan.
# --------------------------------------------------------------------------- #
#: What every tile prints under it, in the order the card reads. Spelled once so
#: the two tiles of a pair carry the same three facts in the same places — a
#: reader comparing a pair should not have to find the numbers twice.
CARD = "{which} · {traversals:g}x · p_fine {fine} · p_coarse {coarse}"


def _spell(value: float | None) -> str:
    """One column as the card prints it, or the absence of it as a word.

    `—` and not `0.0000`: a row a head has never read is a row it has no opinion
    about, and a zero there is a reading. It is the same distinction the page's
    order spends — [`labeling.sheets.ORDERINGS`]' `plan`, where an unread row
    sorts after every read one instead of at the bottom of the scale.

    **Four significant figures and not four decimal places**, which matters here
    and would not on most pages: `p_coarse` over this population has a median of
    **0.0025**, so a fixed `.4f` printed `0.0000` under most of the batch and
    under both halves of a pair whose two readings differ by a factor of ten. The
    card exists to be compared across a pair; a format that flattens the
    comparison to `0.0000 · 0.0000` is not printing the number.
    """
    return "—" if value is None else f"{float(value):.4g}"


def sheet_plan(name: str, device: str = "auto", log=print) -> dict:
    """Both tiles of every pair as finished-render plan units, split by store.

    **Split by store, because a batch's rows all belong to one.**
    [`hunt.kind_of`] routes a mode to `smooth_render` or `strange_render` and
    [`labeling.finished.check`] refuses a row written to the other, so a draw
    spanning both modes is two batches and two sheets rather than one page that
    cannot be ingested. The two come out at **unequal sizes**, which is the
    labeling rig's own rule for binding a drop to a cut — see
    `labeling/README.md`'s *Cut a batch into sheets of UNEQUAL size*.

    Three things ride on every unit beyond the recipe:

    * `order_score`, the fine head's reading of the **candidate**, which is what
      the page is read good→bad in. Read at candidate geometry and never at the
      page's: that head was fitted at 640x360 and this page serves 1280x720, so a
      re-read here would be a different number wearing the same name. It comes
      from [`fine_for`] — the head **run** over every tile — and not from the
      pool's own column, because that column is bar-gated and covers 8 of a
      typical 125 controls. A tile whose picture is gone carries none, and
      [`labeling.sheets.finished_source`]'s `plan` ordering puts it after every
      row that has one.
    * `facts`, which is [`CARD`] — whether this tile is the repeat or the
      control, **the true traversal count** and not the `cycles` value, and both
      columns. Plus the pair's own name on both tiles, which is how the pair is
      visible on a page sorted by a score that does not keep them together.
    * `selected_on`, which [`labeling.intake`] copies onto the stored row whole.
      That is what makes the distribution recoverable from the store alone after
      the sheet directory is swept — including for the rows either head would
      have refused, which is the half of it this batch exists to collect.

    ## A pair whose row the prune took comes off the page, whole

    Merging is an upsert through the ordinary door and the door prunes, so a
    repeat can land and be taken in the same act: `repeat_ckpt120` lost **2 of
    125** that way, at locations already holding a full keep of better-ranked
    rows. A tile with no ledger row is a **label with nowhere to land**, which is
    the one thing this batch may not ship.

    So every drawn key is checked against the store — one streaming pass, about
    twelve seconds — and a pair missing either half is dropped **entirely**. Not
    just the missing tile: a control alone on a matched-pairs page is a tile with
    nothing to compare against, and it would still be counted in the arm shares
    the record reports.

    The **prefill is left to the render judge's own decode** and is not set here.
    A tier is a claim on one store's scale; the fine head's is a gallery grade and
    prefilling this page with it would put the wrong scale's number in the box a
    labeler corrects.
    """
    from fractal_wallpapers.models import gallery_grade_train as grade

    held = json.loads(draw_path(name).read_text(encoding="utf-8"))
    pairs, dropped = _pairs_the_store_still_holds(held["pairs"], log=log)
    held = {**held, "pairs": pairs}
    coarse = repeat_readings(
        name,
        {entry["repeat"] for entry in held["pairs"] if entry.get("repeat")},
        log=log,
    )
    # Every tile's own candidate picture: the control's off the draw, the repeat's
    # off this leg's rows. The pool's bar-gated column is read too and the head's
    # own reading wins where both exist — see [`fine_for`].
    pictures = {entry["control"]: entry.get("control_picture") for entry in held["pairs"]}
    pictures.update({str(row["key"]): row.get("picture") for row in hunt._read(rows_path(name))})
    fine = _fine_column(grade, log=log) | fine_for(pictures, device=device, log=log)
    by_head: dict = {}
    missing_fine = {"control": 0, "repeat": 0}
    no_coarse = 0
    for entry in held["pairs"]:
        recipe = entry["control_recipe"]
        head = hunt.kind_of(str(entry["mode"]))
        control_traversals, repeat_traversals = entry["traversals"]
        for which, key, cycles, count in (
            ("control", entry["control"], 1.0, control_traversals),
            ("repeat", entry["repeat"], entry["cycles"], repeat_traversals),
        ):
            if key is None:
                continue
            reading = _reading_of(key, entry, which, fine, coarse)
            if reading["p_fine"] is None:
                missing_fine[which] += 1
            if reading["p_ge4"] is None:
                no_coarse += 1
            by_head.setdefault(head, []).append(
                {
                    "family": recipe["family"],
                    "viewport": recipe["viewport"],
                    "maxiter": int(recipe["maxiter"]),
                    "mode": entry["mode"],
                    "mode_params": dict(recipe.get("mode_params") or {}),
                    "curve": recipe["curve"],
                    "colormap": entry["colormap"],
                    "recipe": _palette_at(recipe["palette"], cycles),
                    "leveled": _leveled_for(which, entry),
                    "order_score": reading["p_fine"],
                    "facts": [
                        CARD.format(
                            which=which,
                            traversals=count,
                            fine=_spell(reading["p_fine"]),
                            coarse=_spell(reading["p_ge4"]),
                        ),
                        f"pair {entry['pair']} · {entry['colormap']} "
                        f"({'folded' if entry['folded'] else 'cyclic'}) · cycles {cycles:g}",
                    ],
                    "selected_on": {
                        "candidate": key,
                        "pair": entry["pair"],
                        "arm": which,
                        "folded": bool(entry["folded"]),
                        "cycles": float(cycles),
                        "traversals": float(count),
                        "regime": recipe.get("regime"),
                        "p_fine": reading["p_fine"],
                        "p_ge4": reading["p_ge4"],
                        "p_ge3": reading["p_ge3"],
                        "batch": UNIT,
                    },
                }
            )
    for head, units in by_head.items():
        _write_jsonl(repetition_dir(name) / f"plan.{head}.jsonl", units)
    report = {
        "schema": SCHEMA,
        "name": name,
        "tiles": sum(len(units) for units in by_head.values()),
        "by_head": {head: len(units) for head, units in sorted(by_head.items())},
        "sizes_differ": len({len(units) for units in by_head.values()}) == len(by_head),
        "sizes_differ_is": "the rig binds a drop to a cut by unit count, so two cuts of "
        "one day's work at equal sizes are interchangeable and neither can be checked",
        "pairs": len(held["pairs"]),
        "dropped_for_having_no_ledger_row": dropped,
        "arms": {
            "folded": sum(1 for entry in held["pairs"] if entry["folded"]),
            "cyclic": sum(1 for entry in held["pairs"] if not entry["folded"]),
        },
        "rungs": _tally(f"{entry['cycles']:g}" for entry in held["pairs"]),
        "tiles_the_fine_head_has_not_read": missing_fine,
        "no_coarse_reading": no_coarse,
        "no_coarse_reading_is": "a tile neither this leg nor the sidecar has a render-judge "
        "reading for. Its card says so in words rather than printing a defaulted zero, and "
        "the row is on the page all the same — gating on nothing means gating on this too",
        "plans": {
            head: tracked_name(repetition_dir(name) / f"plan.{head}.jsonl") for head in by_head
        },
        "prefill": "left to the render judge's own decode. The fine head's tier is a "
        "gallery grade and this page's scale is not that one",
        "order": "the fine head RUN over every tile at candidate geometry, through "
        "sheets.finished_source(order_by='plan'). Not the pool's own p_fine column, "
        "which is gated at the render bar and covers a small minority of these rows",
    }
    _write_json(sheet_plan_path(name), report)
    log(
        f"[repetition] {report['tiles']:,} tile(s) planned: "
        + ", ".join(f"{count:,} {head}" for head, count in report["by_head"].items())
    )
    return report


def _pairs_the_store_still_holds(pairs: list, log=print) -> tuple[list, dict]:
    """The pairs both of whose tiles are ledger rows, and what was dropped.

    One streaming pass. A repeat can be merged and pruned in the same act — the
    door upserts and then applies the retention rule — so *this leg made it* is
    not the same question as *the store holds it*, and only the second one decides
    whether a label cast on the tile has anywhere to land.
    """
    wanted = {str(entry["control"]) for entry in pairs}
    wanted |= {str(entry["repeat"]) for entry in pairs if entry.get("repeat")}
    present = {str(row["key"]) for row in candidate_ledger.stream() if str(row["key"]) in wanted}
    kept, lost = [], []
    for entry in pairs:
        absent = [
            which
            for which, key in (("control", entry["control"]), ("repeat", entry.get("repeat")))
            if key is None or str(key) not in present
        ]
        if absent:
            lost.append({"pair": entry["pair"], "missing": absent, "location": entry["location"]})
            continue
        kept.append(entry)
    dropped = {
        "pairs": len(lost),
        "tiles": 2 * len(lost),
        "why": "the candidate ledger does not hold one of the pair's two rows, so a verdict "
        "cast on that tile would key to nothing. The pair goes whole — a control with no "
        "repeat beside it is a tile with nothing to compare against",
        "the_ones_dropped": lost,
    }
    if lost:
        log(
            f"[repetition] {len(lost):,} pair(s) dropped: the store no longer holds both "
            f"tiles ({', '.join(one['pair'] for one in lost)})"
        )
    return kept, dropped


def _reading_of(key: str, entry: dict, which: str, fine: dict, coarse: dict) -> dict:
    """The three columns one tile prints.

    The coarse pair comes off the **draw** for a control and off this leg's own
    scores file for a repeat, because those are the two places they were actually
    read; nothing is re-read here and nothing is defaulted into existence. The
    fine column comes off the pool for both, which is the one column a merge and a
    `score-pool` make comparable across the pair.
    """
    if which == "control":
        return {
            "p_fine": fine.get(key, entry.get("control_p_fine")),
            "p_ge4": float(entry["control_p_ge4"]),
            "p_ge3": float(entry["control_p_ge3"]),
        }
    reading = coarse.get(key)
    return {
        "p_fine": fine.get(key),
        "p_ge4": None if reading is None else float(reading["p_ge4"]),
        "p_ge3": None if reading is None else float(reading["p_ge3"]),
    }


def repeat_readings(name: str, wanted: set, log=print) -> dict:
    """`{recipe key: {p_ge4, p_ge3}}` — the repeats' own render-judge readings.

    Two sources, and the cheap one first. This leg's own scores file covers every
    repeat it rendered and is a few hundred rows; a repeat drawn onto a key the
    ledger **already held** was never rendered here and has no row in it, so those
    keys — and only those — are fetched in one filtered pass of the score sidecar.

    The second pass is what stops a card printing `0.0000` under a picture nobody
    read here. A number on a card is a claim, and a defaulted zero under a repeat
    the pool already scores well would have the page arguing the opposite of the
    truth at the exact tile the sitting is about.
    """
    out: dict = {}
    for row in hunt._read(scores_path(name)):
        # `p_ge4` and `p_ge3` are TOP-LEVEL members of a score row, not a nested
        # block: `candidate_ledger.score_row` takes a `read` argument and spreads
        # it. Reading `row["read"]` here returned None for every repeat and
        # defaulted the card to 0.0000 under all 123 of them — exactly the false
        # number this function's second pass exists to prevent, arrived at from
        # the other side. Hence the refusal below rather than a `.get` default.
        if "p_ge4" not in row:
            raise RepetitionRefused(
                f"a row of {tracked_name(scores_path(name))} names no p_ge4. A score row "
                f"carries the judge's columns at its top level; a reader that defaults "
                f"them puts a zero on a card under a picture nobody read."
            )
        out[str(row.get("recipe_key") or row.get("key"))] = {
            "p_ge4": float(row["p_ge4"] or 0.0),
            "p_ge3": float(row["p_ge3"] or 0.0),
        }
    short = {str(key) for key in wanted if str(key) not in out}
    if not short:
        return out
    log(f"[repetition] {len(short):,} repeat(s) this leg did not render; reading the sidecar")
    readings = candidate_ledger.scores_by_recipe(
        (
            score
            for score in candidate_ledger.stream_scores()
            if str(score.get("recipe_key")) in short
        ),
        artifact=candidate_ledger.live_artifact(),
    )
    for key, reading in readings.items():
        out[str(key)] = {
            "p_ge4": float(reading.get("p_ge4") or 0.0),
            "p_ge3": float(reading.get("p_ge3") or 0.0),
        }
    return out


def _palette_at(palette: dict, cycles: float) -> dict:
    """The control's own palette pass with the traversal set. Every other knob is
    carried **because it is not named here** — the same property [`plan_of`]'s
    re-derivation check proves about the pair."""
    return {**dict(palette), "cycles": float(cycles)}


def _leveled_for(which: str, entry: dict) -> str | None:
    """The `<stem>.leveled/` beside a tile's own candidate picture, where one exists.

    Only the control's picture path is on the draw record; a repeat's is on this
    leg's own rows and is resolved by the caller that has them. Without it a
    rebuild renders a different picture under the same identity and nothing
    notices — `curation/LEGS.md`'s *`curate pool-draw`* is where that is written
    down.
    """
    from fractal_wallpapers.curation import pool_draw

    if which != "control":
        return None
    return pool_draw.leveled_dir(entry.get("control_picture"))


def _write_jsonl(path: Path, rows: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def read(name: str) -> dict:
    """One finished batch's record, read back. Raises if the leg never wrote one."""
    path = record_path(name)
    if not path.is_file():
        raise RepetitionRefused(
            f"{tracked_name(path)} does not exist, so there is no batch by that name on "
            f"this machine. `curate repetition run --name {name}` writes it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "BUDGET_SECONDS",
    "CYCLIC_RUNGS",
    "DRAW_NAME",
    "FOLDED_RUNGS",
    "FOLDED_SHARE",
    "MERGE_NAME",
    "PLAN_NAME",
    "RECORD_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "SEQUENCE_NAME",
    "SHEET_NAME",
    "TILES",
    "UNIT",
    "WORKERS",
    "Control",
    "Pair",
    "RepetitionRefused",
    "draw",
    "draw_path",
    "fields_dir",
    "merge",
    "merge_path",
    "pictures_dir",
    "plan_of",
    "plan_path",
    "population",
    "read",
    "record_path",
    "repetition_dir",
    "rows_path",
    "run",
    "scores_path",
    "sequence_path",
    "sheet_plan_path",
    "traversals",
]
