"""Re-rendering a recipe this project already has, in a mode it still buys.

A [`curation.mode_policy`] weight of 0 stops a mode being bought and leaves its
material standing — the ledger rows, the pictures and the labels all keep. What
weight 0 also does, and the ruling does not say out loud, is take every one of
those rows out of [`solve.pool`]: the gallery cannot seat them, so a place whose
only clearing candidate was in the ruled-out mode stops being a place the gallery
can reach at all. `exp_smoothing`'s ruling on 2026-09-04 stranded **574 places**
that way and cost 17 seats at `n = 1000`.

This leg is the answer to that, and it is deliberately the expensive one. For each
row of a retired mode that cleared the pool bar, it renders the **same recipe** —
same frame, same cap, same map, same palette knobs, same autolevel policy — with
the mode moved to one the project still buys, and merges what comes back as
ordinary candidate rows through the ordinary door.

## Why it re-renders instead of re-labelling

`EVAL_exp_smoothing_0904` measured the two arms as the same picture at 98.7% of
914 gallery seats and found the judge unable to order them apart: Pearson r
**0.99729** on `P(>=4)`, median delta +0.0001, and 11 crossings of the 0.50 gate
in 914 — five one way and six the other, which is the shape of noise. So it would
have been arithmetically defensible to move the mode field on the stranded rows
and keep their scores, for none of the render cost.

That is refused, and the reason is [`recipes.key_of`]: **a recipe key is a digest
of the engine spec**, so a row claiming a mode it was not rendered in names a
picture nobody made. Every reader that re-derives the picture from the row —
[`candidate_ledger.re_render`], `release.replay`, the website's figure resolver —
would then disagree with the disk, silently, and the row would still be wrong
after the disagreement was noticed. The two fields really are different fields:
`max |Δ|` over those pairs has a median of 40 of 255 and a minimum of 15. Only the
picture is the same, and a picture is not what a row is keyed on.

## What it does not do

It does not touch the source rows, move a weight, delete a picture, or re-key
anything. And it makes no claim that a twin is as good as its source: each one is
judged on its own render by the shipped judge, exactly as a mine's candidate is,
and a twin that comes back below the bar is a row that merged and does not clear.

## Three counts come out, and the row count is the least interesting

**Rows made** is what the engine drew. **Rows clearing** is how many cleared the
*target* mode's own bar in [`headroom`], which is the population a gallery sees.
**Places that regain a clearing row** is the only one the ruling's cost was
stated in, and it is bounded by neither of the others but by the retention rule:
every twin lands on `(location, target mode)`, where
[`candidate_ledger.RETAIN_PER_PAIR`] keeps three ranked *within* the pair by the
fitted rank key — so a place already holding three better-ranked rows in the
target mode absorbs its twin and gives nothing back. The record reports all three
and the prune's own verdict beside them.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import (
    candidate_ledger,
    depth,
    headroom,
    hunt,
    mine,
    mode_policy,
    recipes,
    release,
)
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree this leg's output lands in, under the regenerable tree. It is a
#: member of [`candidate_ledger.POOL_SUBTREES`], which is what makes its pictures
#: reachable by `curate candidate-ledger orphans`: a leg whose subtree that sweep
#: cannot enumerate is a leg whose killed run leaks its renders with no row
#: anywhere and nothing to notice.
UNIT = "remode"

#: What the two appended files, the per-candidate sequence and the record are called.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"
SEQUENCE_NAME = "sequence.jsonl"
RECORD_NAME = "remode.json"

#: How many engines this leg drives at once. **Three**, this machine's render
#: pool, the same number every leg here takes and a rule about the desktop rather
#: than a tuning knob. The priority half is [`engine.run`]'s, which spawns
#: below-normal by construction, so it is not this module's to remember.
WORKERS = 3

#: How long the leg may spend **rendering**, in wall seconds. Not the wall clock
#: of the invocation: reading the ledger and resolving the twins sit outside it —
#: [`curation.depth`] draws the same split and for the same reason, that a pilot
#: whose budget went on a store read renders nothing at all.
BUDGET_SECONDS = 3600.0


class RemodeRefused(RuntimeError):
    """A mode pair this leg will not render, or a population it cannot trust."""


# --------------------------------------------------------------------------- #
# Where it keeps things.
# --------------------------------------------------------------------------- #
def remode_dir(name: str) -> Path:
    """The subtree one leg owns: its rows, its pictures, its fields, its record."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    return remode_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    return remode_dir(name) / SCORES_NAME


def sequence_path(name: str) -> Path:
    return remode_dir(name) / SEQUENCE_NAME


def record_path(name: str) -> Path:
    return remode_dir(name) / RECORD_NAME


def fields_dir(name: str) -> Path:
    """Where this leg's dumped fields live. One per (location, target mode)."""
    return remode_dir(name) / "fields"


def pictures_dir(name: str) -> Path:
    """The twin renders, named by **recipe key** — which is what lets a re-run find
    the picture it already made instead of drawing it a second time."""
    return remode_dir(name) / candidate_ledger.PICTURES_NAME


# --------------------------------------------------------------------------- #
# The population: the rows of one mode that clear that mode's own bar.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Source:
    """One row this leg means to render again, and the reading it cleared on.

    Deliberately **not** a [`solve.Candidate`]. That type is built by
    [`solve.pool`], which refuses a niche mode's rows before it makes one — which
    is the very condition this leg exists to repair, so a population read through
    it would always be empty. This carries the three columns
    [`headroom.rule_of`] and [`headroom.clears`] read, plus the stored recipe the
    twin is made from.
    """

    key: str
    location: str
    partition: str
    mode: str
    score: float
    p_ge3: float
    recipe: dict


def population(from_mode: str, log=print) -> dict:
    """Every row of `from_mode` that clears the bar its own mode landed on.

    **The bar is [`headroom`]'s arithmetic and is not restated here.**
    `headroom.bars` cannot be asked directly: its roster is
    [`mode_policy.accepted`], and the mode this leg is called about has usually
    just left it. So the rule comes from [`headroom.rule_of`] and the test from
    [`headroom.clears`], which are that function's own lines hoisted so both
    callers read one answer.

    The four other exclusions are [`solve.pool`]'s, and they are here for its
    reasons rather than as a quality filter: a human rejection is honoured, a row
    at another regime carries a score that does not transfer to this one, and a
    row whose picture is not on disk is one the diversity rule could never have
    read. **That makes this population the same one the drop was measured over**,
    which is the whole of what makes a before-and-after comparable.

    Two streaming passes and not two whole reads. The rows file is 275 MB and the
    score sidecar 252 MB, and this needs one mode's rows out of the first and the
    readings for exactly those keys out of the second — so it streams both and
    keeps the intersection, which is a few thousand rows rather than four hundred
    thousand. `known` is every recipe key in the store, built in the same pass
    because [`plan_of`] has to have it and a second pass for it would be another
    275 MB.
    """
    wanted = str(from_mode)
    refused = {"rejected": 0, "off_regime": 0, "no_picture": 0, "no_score": 0, "picture_absent": 0}
    known: set = set()
    held: list = []
    scanned = 0
    at = time.monotonic()
    for row in candidate_ledger.stream():
        scanned += 1
        known.add(str(row["key"]))
        if str((row.get("recipe") or {}).get("mode")) != wanted:
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
        f"[remode] {scanned:,} ledger row(s) in {time.monotonic() - at:.1f}s; "
        f"{len(held):,} are {wanted} with a picture named"
    )
    live = candidate_ledger.live_artifact()
    keys = {str(row["key"]) for row in held}
    # The join every other reader takes, so this leg inherits the second-regime
    # refusal in [`candidate_ledger.scores_by_recipe`] rather than being the one
    # site outside it. Fed a generator and not the stream itself: that function
    # materializes what it is handed, and the sidecar is the 252 MB the paragraph
    # above promises not to read whole — filtering on `keys` first is what keeps
    # this a streaming pass. The artifact is named because it is already in hand,
    # and an unnamed read would go back to the store for it.
    readings = candidate_ledger.scores_by_recipe(
        (
            score
            for score in candidate_ledger.stream_scores()
            if str(score.get("recipe_key")) in keys
        ),
        artifact=live,
    )
    present = candidate_ledger.present_pictures(held)
    sources: list = []
    for row in held:
        key = str(row["key"])
        reading = readings.get(key)
        if reading is None:
            refused["no_score"] += 1
            continue
        if key not in present:
            refused["picture_absent"] += 1
            continue
        sources.append(
            Source(
                key=key,
                location=str((row.get("location") or {}).get("key")),
                partition=str(row.get("partition")),
                mode=wanted,
                score=float(reading.get("p_ge4") or 0.0),
                p_ge3=float(reading.get("p_ge3") or 0.0),
                recipe=dict(row.get("recipe") or {}),
            )
        )
    rule = headroom.rule_of(sources)
    clearing = [source for source in sources if headroom.clears(source, rule)]
    log(
        f"[remode] {len(clearing):,} of {len(sources):,} scored {wanted} row(s) clear on "
        f"{rule}, at {len({source.location for source in clearing}):,} location(s)"
    )
    return {
        "from_mode": wanted,
        "rule": rule,
        "judge_artifact": live,
        "scanned": scanned,
        "in_mode": len(sources),
        "refused": refused,
        "clearing": clearing,
        "known": known,
        "ledger_rows": scanned,
        "seconds": round(time.monotonic() - at, 2),
    }


def target_rule(to_mode: str, log=print) -> str:
    """Which column the **target** mode's rows clear on, read off the live pool.

    Read on the population the twins are about to join and never on the twins
    themselves: a clearing rate is a fact about a bar the rest of the pool
    already sets, and a rule derived from this leg's own output would move with
    this leg's own yield. It is [`solve.pool`] plus `headroom.bars`, which is what
    every other reader of a bar in this project does.
    """
    from fractal_wallpapers.curation import solve

    candidates, _refused = solve.pool(log=log)
    table = headroom.bars(candidates)
    held = (table["modes"].get(str(to_mode)) or {}).get("rule")
    if held is None:
        raise RemodeRefused(
            f"{to_mode!r} has no row in headroom.bars, so there is no bar to read a twin "
            f"against. Every accepted mode has one; a mode that does not is one "
            f"mode_policy weights 0, and this leg refuses those as targets anyway."
        )
    return str(held)


# --------------------------------------------------------------------------- #
# The twin.
# --------------------------------------------------------------------------- #
def twin(stored: dict, to_mode: str) -> recipes.Recipe:
    """The same picture's recipe with the mode moved, and nothing else touched.

    One `replace` on what [`recipes.of_record`] reads back, which is what makes
    *everything else held* a property of the code rather than a promise in a
    docstring: the frame, the cap, the regime, the curve, the colormap, the seven
    palette knobs and the palette group are all carried **because they are never
    named here**. A member added to [`recipes.Recipe`] tomorrow is carried too.

    The two that do move, and why each has to:

    * `mode_params` is emptied. `renders.FIELD_IDENTITY` holds it and the target
      mode's settings space is not the source's, so carrying a setting across
      would name a picture the engine would not draw. It is also what keeps a
      twin on [`colorize.render`]'s shared-field path — see [`_shared_field`],
      which sends a candidate with settings down the full render, once per map
      instead of once per place.
    * `autolevel` is re-derived through [`recipes.live_stamp`] rather than
      copied. The stamp is the operator's *identity* — the operator, the switch
      and the band's sha256 — and whether the operator applies at all is a
      function of the mode's **kind**. A twin that carried a stamp its own kind
      takes no operator for would digest to a key for a picture the pipeline
      cannot make. Where both modes are the same kind this is the same value the
      source carried, which is the ordinary case and not a reason to skip it.
    """
    return replace(
        recipes.of_record(stored),
        mode=str(to_mode),
        mode_params={},
        autolevel=recipes.live_stamp(str(to_mode)),
    )


def plan_of(sources: list, to_mode: str, known: set) -> tuple[list, dict]:
    """`(units, shape)` — one twin per source, minus the ones already in the ledger.

    Resolved in the parent and before anything renders, for
    [`depth.blocks_of`]'s two reasons: the skip count is then exact up front
    rather than three workers racing to discover the same key, and `known` is a
    hundred and eighty thousand keys nobody wants pickled to a worker per block.

    Units come out grouped by location, which is what lets [`blocks_of`] cut them
    so each place pays one field dump. `k` counts **this leg's** twins at a
    location and never the location's whole depth, which is what a mine's `k`
    counts too.
    """
    by_place: dict = {}
    for source in sources:
        by_place.setdefault(source.location, []).append(source)
    units: list = []
    already, unresolvable = 0, 0
    for place, group in by_place.items():
        at = 0
        for source in sorted(group, key=lambda held: held.key):
            try:
                recipe = twin(source.recipe, to_mode)
            except recipes.RecipeError:
                # A stored recipe missing a member names no picture, so it cannot
                # name a twin either. Counted rather than raised: one unreadable
                # row of several thousand is not a reason to render none of them.
                unresolvable += 1
                continue
            key = recipes.key_of(recipe)
            if key in known:
                already += 1
                continue
            at += 1
            units.append(
                (
                    mine.Unit(
                        arm=UNIT,
                        location=place,
                        partition=source.partition,
                        mode=str(to_mode),
                        colormap=str(recipe.colormap),
                        k=at,
                        # The mode this twin was made FROM. `band` is the mine's
                        # word for the prior a draw was taken under, which is
                        # exactly what the source mode is here — so the readouts
                        # a mine already has read this leg without an edit.
                        band=source.mode,
                    ),
                    source,
                    recipe,
                    key,
                )
            )
    shape = {
        "sources": len(sources),
        "source_locations": len(by_place),
        "twins": len(units),
        "twin_locations": len({unit.location for unit, _s, _r, _k in units}),
        "already_in_ledger": already,
        "unresolvable": unresolvable,
        "to_mode": str(to_mode),
    }
    return units, shape


def blocks_of(units: list) -> list:
    """The plan cut at the **location**, in first-appearance order.

    The location is the unit of work for [`depth._render_block`]'s reason: one
    field is dumped per (location, mode) and every map at that pair is a recolour
    of it, so a plan cut per candidate hands one place to three workers and pays
    the dump three times over — which comes out slower than serial. Cut here, the
    dump is paid once by whichever worker owns the place.

    It is worth more on this leg than on a draw. A retired mode's rows at one
    place differ in the **map** and in nothing else, so a block is a dump followed
    by k recolours with nothing else in it.
    """
    order: dict = {}
    for at, entry in enumerate(units, start=1):
        order.setdefault(entry[0].location, []).append((at, entry))
    return list(order.values())


def place_of(recipe: recipes.Recipe) -> dict:
    """What [`mine.make`] reads off a place: the family, and nothing else.

    A draw leg gets this from the supply sidecar. This one has no draw — the place
    is wherever the source row already stands — so it comes off the recipe, which
    carries the family precisely because a recipe has to stay renderable from the
    row alone.
    """
    return {"family": recipe.family}


def frame_of(recipe: recipes.Recipe) -> dict:
    """The frame: the viewport the source was rendered at, and its cap.

    **No [`hunt.frame_for`] lookup, and that is the point rather than an
    omission.** A framing index answers *where should a fresh candidate be drawn*,
    and adopting a refinement here would move the frame — making the twin a
    different picture, at a different place, which is the one thing this leg must
    not do. `tests/test_remode.py` pins it against a future edit that adds one.
    """
    return {"viewport": recipe.viewport, "maxiter": int(recipe.maxiter)}


# --------------------------------------------------------------------------- #
# The workers.
# --------------------------------------------------------------------------- #
#: One [`hunt.Maker`] per worker **process**, built on the first block it is
#: handed and kept for every block after. [`depth._MAKER`]'s reason: the judge is
#: two seconds to load and 9.7 MiB on the card, so three of them are free and one
#: per block would be most of a short leg.
_MAKER: dict = {}


def _maker_for(name: str, device: str, fields: str):
    key = (str(name), str(device), str(fields))
    if key not in _MAKER:
        _MAKER[key] = hunt.Maker(name, device=device, log=lambda *_a: None, fields=Path(fields))
    return _MAKER[key]


def render_block(payload: tuple) -> list:
    """One location's twins, start to finish, in one worker. `[(at, result)]`.

    **Module level and taking a plain tuple**, because a Windows pool *spawns*: a
    closure over the plan would not pickle. The deadline is checked before each
    candidate rather than only between blocks — a place can carry a dozen twins,
    and a block that could not stop inside itself would overrun the budget by
    minutes.

    Through [`mine.make`], which is [`hunt.Maker.make`] with a stopwatch on each
    stage: the same [`colorize.render`], the same judge and the same colour read
    as every candidate already in the ledger. A leg that made its pictures its own
    way would be stocking a pool with rows nothing else could compare against.
    """
    name, device, fields, pictures, block, deadline = payload
    maker = _maker_for(name, device, fields)
    out = []
    for at, (unit, place, frame, key) in block:
        if time.monotonic() >= deadline:
            break
        try:
            result = mine.make(maker, unit, place, frame, key, pictures=Path(pictures))
        except Exception as failure:  # noqa: BLE001 — a failed candidate is a recorded fact
            out.append((at, {"failed": repr(failure)[:400], "key": key}))
            continue
        out.append(
            (
                at,
                {
                    "key": key,
                    "picture": str(result["picture"]),
                    "verdict": result["verdict"],
                    "colour": result["colour"],
                    "cells": result["cells"],
                    "acted": bool(result["acted"]),
                    # The whole stamp and not just the boolean: `acted` is not
                    # something a curve can be rebuilt from, and a row recording
                    # only it is a row recording that its picture is
                    # unreproducible. See [`depth._render_block`].
                    "autolevel": result["autolevel"],
                    "texture_flat": bool(result["texture_flat"]),
                    # The `Stages` dataclass itself, which the parent feeds
                    # straight to `mine.Clock.add`. A dict of it here would be a
                    # second spelling of the eight stage names.
                    "stages": result["stages"],
                },
            )
        )
    return out


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def run(
    name: str,
    *,
    from_mode: str,
    to_mode: str,
    budget: float = BUDGET_SECONDS,
    workers: int = WORKERS,
    device: str = "auto",
    world: dict | None = None,
    rule: str | None = None,
    log=print,
) -> dict:
    """One leg, end to end. Rows land as twins land; the record is returned.

    [`depth.run`]'s shape — the parent resolves every recipe and writes every
    row, the workers only make pictures — and the differences are all consequences
    of there being no draw here:

    * **There is no seed and no rate.** The plan is not sampled: it is *every*
      row of the source mode that clears, so a leg re-run over an unchanged
      ledger asks for exactly what it asked for before, and the door's upsert
      makes the second run free. `budget` still truncates, and what it truncates
      is whole locations.
    * **The frame is the source row's own** — see [`frame_of`].
    * `k` is the twin's index at its location and never the location's depth.
    """
    started = time.monotonic()
    if str(to_mode) == str(from_mode):
        raise RemodeRefused(
            f"{to_mode!r} is the mode these rows are already in, so every twin would "
            f"digest to a key the ledger already holds and this leg would render nothing."
        )
    # Refused rather than warned. A target this project has stopped buying is the
    # condition the leg exists to repair, and repairing it into a second weight-0
    # mode would strand the same material twice — for the full render cost.
    if not mode_policy.is_accepted(str(to_mode)):
        raise RemodeRefused(
            f"{to_mode!r} carries weight {mode_policy.weight_of(str(to_mode))} in "
            f"MODE_POLICY, so a twin rendered in it would leave solve.pool exactly the way "
            f"the source rows did. Re-render into a mode the project still buys."
        )
    world = population(from_mode, log=log) if world is None else world
    if str(world["from_mode"]) != str(from_mode):
        raise RemodeRefused(
            f"the population handed in was read for {world['from_mode']!r} and this leg "
            f"was asked for {from_mode!r}. A leg rendering one mode's rows selected under "
            f"another mode's bar would report a clearing rate about neither."
        )
    held_rule = target_rule(to_mode, log=log) if rule is None else str(rule)
    units, shape = plan_of(world["clearing"], to_mode, world["known"])
    blocks = blocks_of(units)
    # Once, before anything renders: the build every row this leg writes names.
    # See [`candidate_ledger.live_engine`] for why it is not asked per row.
    build = candidate_ledger.live_engine()
    # The parent's own Maker owns the field cache and sweeps it. It resolves
    # nothing — the recipes are already resolved — and never judges, so it never
    # loads the judge. The workers hold theirs.
    maker = hunt.Maker(name, device=device, log=log, fields=fields_dir(name))
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
        "already_in_ledger": shape["already_in_ledger"],
        "unresolvable": shape["unresolvable"],
        "failed": 0,
        "stopped_for_budget": 0,
        "autolevel_acted": 0,
        "clearing": 0,
        "fields_swept": 0,
    }
    # `depth.workers_for` and not a copy of it: three workers is the machine's
    # rule and not a floor, and a plan with fewer blocks than workers gets one
    # worker a block with the record saying so.
    counts["workers"] = depth.workers_for(blocks, workers, log=log)
    counts["location_blocks"] = len(blocks)
    by_at = {at: entry for block in blocks for at, entry in block}
    # The clock starts at the FIRST BLOCK and not at the call: `population` is a
    # whole-store sweep and charging it to a render budget makes a short pilot
    # render nothing. `render_wall` is what the budget governs; `wall_seconds` on
    # the record is the whole call.
    render_started = time.monotonic()
    deadline = render_started + float(budget)
    spent = 0.0

    def take(at: int, result: dict) -> None:
        """One landed twin, written by the PARENT. Never by a worker."""
        nonlocal spent
        if "failed" in result:
            counts["failed"] += 1
            log(f"[remode] {result['key']} failed: {result['failed']}")
            return
        unit, source, recipe, key = by_at[at]
        stages = result["stages"]
        # This leg's own source shape and not [`hunt.source_for`]: that one builds
        # a framing verdict out of a frame lookup, and there is no lookup here —
        # the frame is the source row's. Everything `candidate_ledger.row` reads
        # off a source is here and nothing beyond it is invented.
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
        scored = candidate_ledger.score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=hunt.kind_of(unit.mode, result["texture_flat"]),
            read=result["verdict"],
            source=origin,
        )
        hunt._append(rows_file, stored)
        hunt._append(scores_file, scored)
        spent += stages.total()
        price.add(unit.partition, stages.total(), band=unit.arm)
        counts["made"] += 1
        counts["autolevel_acted"] += int(result["acted"])
        verdict = result["verdict"]
        p_ge4 = round(float(verdict.get("p_ge4") or 0.0), 6)
        p_ge3 = round(float(verdict.get("p_ge3") or 0.0), 6)
        cleared = _clears(p_ge4, p_ge3, held_rule)
        counts["clearing"] += int(cleared)
        row = {
            "key": key,
            # The row this twin was made from, and its reading. On this leg's own
            # record and NOT on the ledger row: nothing in the ledger's shape says
            # "made from", and inventing a field there would be a field no reader
            # asks for. The join survives anyway — a twin differs from its source
            # only in the mode, so `remode.twin` run backwards recovers the key.
            "from_key": source.key,
            "from_mode": source.mode,
            "from_p_ge4": round(source.score, 6),
            "from_p_ge3": round(source.p_ge3, 6),
            "location": unit.location,
            "partition": unit.partition,
            "mode": unit.mode,
            "mode_kind": mine._kind_of(unit.mode),
            "texture_flat": result["texture_flat"],
            "colormap": unit.colormap,
            "palette_group": recipe.palette_group,
            "maxiter": int(recipe.maxiter),
            "k": unit.k,
            "acted": bool(result["acted"]),
            "cells": result["cells"],
            "p_ge4": p_ge4,
            "p_ge3": p_ge3,
            # The twin's reading minus its source's, on the column the bar is on.
            # **Not centred on zero even if the two modes are identical**, and the
            # reason is the population rather than the modes: a source is here
            # because it cleared, which selects on a noisy reading, so its twin
            # regresses. That is [`curation.shrinkage`]'s winner's curse arriving
            # by another route. See [`carry_readout`].
            "delta": round(
                (p_ge4 if held_rule == headroom.DEFAULT_COLUMN else p_ge3)
                - (source.score if held_rule == headroom.DEFAULT_COLUMN else source.p_ge3),
                6,
            ),
            "clears": cleared,
            "crossed": cleared != _clears(source.score, source.p_ge3, held_rule),
            "seconds": round(stages.total(), 3),
            "stages": stages.named(),
            "picture": tracked_name(Path(result["picture"])),
        }
        made.append(row)
        # On the sequence row and not on `row`: `made` is held whole for the
        # length of the leg and feeds the readout, which reads no stamp, so a
        # kilobyte a candidate there would be megabytes of curve nothing wants.
        hunt._append(
            sequence_file,
            {"schema": SCHEMA, "at": at, **row, "autolevel": result["autolevel"]},
        )
        clock.add(
            stages,
            {
                "partition": unit.partition,
                "mode": unit.mode,
                "mode_kind": mine._kind_of(unit.mode),
                "acted": bool(result["acted"]),
            },
        )
        if counts["made"] % 200 == 0:
            counts["fields_swept"] += mine.colorize_module().sweep_fields(maker.fields)
            log(
                f"[remode] {counts['made']:,} made ({counts['clearing']:,} clearing), "
                f"{time.monotonic() - render_started:.0f}s of {budget:.0f}s wall "
                f"({spent / max(1, counts['made']):.3f}s an engine each)"
            )

    def payload_of(block: list) -> tuple:
        # The block handed to a worker carries the place, the frame and the key
        # and NOT the Source or the Recipe: the parent keeps those in `by_at`, and
        # a recipe is the largest thing in the plan.
        return (
            name,
            device,
            str(fields_dir(name)),
            str(pictures_dir(name)),
            [
                (at, (unit, place_of(recipe), frame_of(recipe), key))
                for at, (unit, _source, recipe, key) in block
            ],
            deadline,
        )

    if counts["workers"] <= 1:
        # The serial path is the fallback and must not be a branch of the pool it
        # falls back FOR: no pool, no pickling, no second Maker. [`depth.run`]'s
        # rule, one leg over.
        for block in blocks:
            if time.monotonic() >= deadline:
                continue
            for at, result in render_block(payload_of(block)):
                take(at, result)
    else:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(
            max_workers=counts["workers"],
            initializer=depth._worker_init,
            initargs=(release.engine_threads_for(counts["workers"]),),
        ) as pool:
            for done, pairs in enumerate(
                pool.map(render_block, [payload_of(block) for block in blocks]), start=1
            ):
                for at, result in pairs:
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
            "from_mode": str(from_mode),
            "to_mode": str(to_mode),
            "source_rule": world["rule"],
            "source_rule_is": "the column the SOURCE mode's rows cleared on, by "
            "headroom.rule_of. It selects the population and is not the bar a twin is "
            "read against",
            "target_rule": held_rule,
            "target_rule_is": "the column the TARGET mode clears on in the pool the twins "
            "join, by headroom.bars over solve.pool. `clears` on every made row is this",
            "budget_seconds": float(budget),
            "workers": counts["workers"],
            "workers_asked": int(workers),
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
            "held": "frame, maxiter, regime, curve, colormap, every palette knob and the "
            "palette group — carried because remode.twin never names them. Moved: mode; "
            "mode_params emptied; the autolevel stamp re-derived for the target mode's kind",
        },
        "population": {
            "ledger_rows": world["ledger_rows"],
            "in_mode": world["in_mode"],
            "refused": world["refused"],
            "clearing": len(world["clearing"]),
            "clearing_locations": len({source.location for source in world["clearing"]}),
            "read_seconds": world["seconds"],
        },
        "plan": shape,
        "counts": counts,
        "budget": {
            "is": "WALL seconds of rendering, spent by however many engines are on the leg",
            "allowed": float(budget),
            "render_wall": round(wall, 2),
            "wall_seconds": round(time.monotonic() - started, 2),
            "wall_seconds_is": "the whole call, the population read included. `render_wall` "
            "is what the budget governs and it starts at the first block",
            "engine_seconds": round(spent, 2),
            "concurrency": round(spent / max(1e-9, wall), 3),
            "engine_threads": release.engine_threads_for(counts["workers"]),
            "seconds_per_candidate": round(spent / max(1, counts["made"]), 4),
            "seconds_per_candidate_is": "per ENGINE, which is what MEASUREMENTS.md's table "
            "is denominated in. Wall a candidate is this over `concurrency`",
        },
        "price": price.table(),
        "profile": clock.table(),
        "carry": carry_readout(made),
        "made": made,
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "sequence_path": tracked_name(sequence_file),
    }
    path = record_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(
        f"[remode] {counts['made']:,} twin(s) in {wall:.0f}s of wall on "
        f"{counts['workers']} worker(s); {counts['clearing']:,} clear on {held_rule} — "
        f"{tracked_name(path)}"
    )
    return record


def _clears(p_ge4: float, p_ge3: float, rule: str) -> bool:
    """[`headroom.clears`] over two bare numbers, for a reading with no row yet.

    A twin is judged before any `Source` or `Candidate` exists for it, so this
    hands the two columns to the same test rather than restating the heights — a
    shim over one answer, and never a second one.
    """
    return headroom.clears(
        Source(key="", location="", partition="", mode="", score=p_ge4, p_ge3=p_ge3, recipe={}),
        rule,
    )


def carry_readout(made: list) -> dict:
    """How much of the source mode's standing the twins actually carried.

    `clearing` is the rate, and it is the number the leg is answerable on.

    **`crossed_up` is zero by construction on any real population here, and that
    is a fact about the selection rather than about the modes.** Every source is
    in the plan *because it cleared*, so the only crossing available to a twin is
    downward — a symmetry test cannot be run on this set, and reading a one-sided
    count as evidence that the modes differ would be wrong. It is reported in both
    directions anyway, because `crossed_up` is the assertion: a non-zero one means
    a source that did not clear reached the plan, which is a defect in
    [`population`] and not a finding about a mode.

    `delta` is subject to the same selection and **should not be expected to sit
    on zero even if the two modes are pixel-identical**: a source was chosen on a
    high noisy reading, so its twin regresses toward the mean. That is
    [`curation.shrinkage`]'s winner's curse reached by another route, and it is
    why the honest comparison of two modes is a *paired* draw over an unselected
    population — which is what `EVAL_exp_smoothing_0904` did, over all 914 seats,
    to get its symmetric 5-versus-6. What `delta` is good for here is a sanity
    bound: a median far from zero, or a mean the size of the bar, would say the
    twins are not the same picture at all.
    """
    import statistics

    if not made:
        return {"made": 0}
    deltas = [row["delta"] for row in made]
    clearing = [row for row in made if row["clears"]]
    return {
        "made": len(made),
        "clearing": len(clearing),
        "clearing_rate": round(len(clearing) / len(made), 4),
        "locations": len({row["location"] for row in made}),
        "clearing_locations": len({row["location"] for row in clearing}),
        "crossed_down": sum(1 for row in made if row["crossed"] and not row["clears"]),
        "crossed_up": sum(1 for row in made if row["crossed"] and row["clears"]),
        "crossed_is": "a twin on the other side of the bar from its own source. crossed_up "
        "is 0 BY CONSTRUCTION — every source is in the plan because it cleared, so the only "
        "crossing available is downward, and this is not a symmetry test. A non-zero "
        "crossed_up means a source that did not clear reached the plan",
        "delta": {
            "mean": round(statistics.fmean(deltas), 6),
            "median": round(statistics.median(deltas), 6),
            "min": round(min(deltas), 6),
            "max": round(max(deltas), 6),
            "higher": sum(1 for value in deltas if value > 0),
            "lower": sum(1 for value in deltas if value < 0),
        },
        "autolevel_acted": sum(1 for row in made if row["acted"]),
        "by_partition": {
            partition: {
                "made": sum(1 for row in made if row["partition"] == partition),
                "clearing": sum(
                    1 for row in made if row["partition"] == partition and row["clears"]
                ),
                "seconds": round(
                    sum(row["seconds"] for row in made if row["partition"] == partition), 2
                ),
            }
            for partition in sorted({row["partition"] for row in made})
        },
    }


def merge(name: str, log=print) -> dict:
    """Upsert this leg's two files into the ledger and its sidecar.

    [`mine.merge`]'s body over this module's paths rather than a third copy of
    it: a twin's row is a mine's row byte for byte, the upsert keys on the recipe,
    and so merging twice writes the same bytes and merging a killed leg's partial
    is the same operation as merging a finished one's. Separate from the run for
    the same reason too — the ledger is rewritten whole on every upsert, and forty
    megabytes a candidate is not a write.

    **The prune is the number to read off this and it is not the merge's row
    count.** Every twin lands on `(location, target mode)`, where
    [`candidate_ledger.RETAIN_PER_PAIR`] keeps three ranked by the fitted rank
    key — so a place already holding three better-ranked rows in that mode absorbs
    its twin and the store comes out the size it went in. `pruned` says how many.
    """
    rows = hunt._read(rows_path(name))
    scores = hunt._read(scores_path(name))
    if not rows:
        raise RemodeRefused(
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
        # What this leg re-rendered because the retention rule had already deleted
        # it: a floor, reported and never prevented. See [`retention.repeat_draws`].
        "repeat_draws": written["repeat_draws"],
        "pruned": written["pruned"],
        "locations_touched": len({str((row.get("location") or {})["key"]) for row in rows}),
    }
    log(
        f"[remode] merged {len(rows):,} row(s): the ledger holds "
        f"{written['ledger']['rows']:,} recipes, {written['ledger']['new']:,} of them new"
    )
    return report


def read(name: str) -> dict:
    """One finished leg's record, read back. Raises if the leg never wrote one."""
    path = record_path(name)
    if not path.is_file():
        raise RemodeRefused(
            f"{tracked_name(path)} does not exist, so there is no leg by that name on this "
            f"machine. `curate remode run --name {name}` writes it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "BUDGET_SECONDS",
    "RECORD_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "SEQUENCE_NAME",
    "UNIT",
    "WORKERS",
    "RemodeRefused",
    "Source",
    "blocks_of",
    "carry_readout",
    "fields_dir",
    "frame_of",
    "merge",
    "pictures_dir",
    "place_of",
    "plan_of",
    "population",
    "read",
    "record_path",
    "remode_dir",
    "render_block",
    "rows_path",
    "run",
    "scores_path",
    "sequence_path",
    "target_rule",
    "twin",
]
