"""Does repeating the gradient improve a picture that is already good at 1x?

`curate repetition` asked whether the repeat axis is worth drawing at all, and
the answer that came back on 2026-09-11 was no: over 121 matched pairs the mean
within-pair delta is **-0.273 tiers**, `cycles = 3` is a rout at -0.634, and the
one arm Matt is not against — a folded map at `cycles = 2`, four passes of the
base ramp — is *exactly neutral*, 7 wins against 7 losses and 25 ties. So
repetition is closed as a general draw.

What is not closed is the one question that draw could not answer. That page
**gated on nothing**, which was right for measuring the axis and means only 4 of
its 121 baselines cleared [`solve.DEFAULT_FINE_BAR`] at all: it measured what
repetition does to a picture drawn from the whole pool, and said nothing about
what it does to a picture that is *already good*. This leg asks that, and it is
the only repetition Matt will consider.

## One tile, two renders, a three-point comparative scale

The unit is a **single composite picture** — the 1x render on the left, the
repeated one on the right, equal size, same crop, a thin separator, nothing
written on the image. Matt casts `1` the repeat is worse, `2` neutral, `3` the
repeat is better, and those verdicts land in the `repeat_ab` attribute store.

⚠ **That scale is not the 1..4 quality scale and may never enter a quality
store.** A `3` here says *the repeat is the better picture*, not *tier 3*. The
protection is structural rather than advisory: an attribute row carries `class`
and [`labeling.attributes.check`] refuses one carrying a `score`, so the two
cannot be pooled by field name. See that module's docstring.

## The draw, and why each exclusion is there

Every unit is a smooth-routed ledger row at `cycles = 1` and `phase = 0` reading
above [`solve.DEFAULT_FINE_BAR`] on the fine head's `p_fine`, at the candidate
regime, with its picture on disk and no human verdict anywhere in either finished
store. The bar is the point of the leg. The last one is the `aug_sweep_A` failure
being avoided: a page mixing rows that already carry a verdict against rows that
do not cannot be repaired afterwards, because there is no way to tell whether a
difference between the two halves is the axis or the history. **One unit per
location**, so no place can carry the page.

`phase` is held at **0** on both halves. 1,713 of the store's 2,262 repeat rows
carry a rotation too, so the axis as the pool holds it is confounded with the one
[`rotation`] measured; a rotated variant here would answer neither question.

## The rung is `cycles = 2` and it is two different doses

A **cyclic** map is walked end to end and meets itself, so `cycles = 2` is a 2x
traversal. A **sequential** map is baked folded — an out-and-back — so one pass
is already two traversals and `cycles = 2` is **4x**. Those are the two arms that
did not lose on the ckpt-121 page: folded 4x at +0.000 and cyclic x2 at -0.171
(p = 0.66), against cyclic x3's -0.634 at p = 3e-6. `cycles = 3` is out.
[`repetition.traversals`] is the arithmetic and is reached rather than restated.

## Nothing is rendered into the pool and nothing is merged

This leg writes **a plan and nothing else**. The variant is not a candidate: the
verdict keys on the location, the baseline is already a ledger row, and the
variant's recipe key is derived here so the row can name it — so there is no
merge, no prune to lose a tile to, and no picture in a pool subtree for the
orphan sweep to have to know about. The two halves are rendered by
[`labeling.sheets.comparison_source`] at label geometry, once, into the sheet
directory, exactly as every other sheet's pictures are.

**It HOLDS THE POOL**: [`population`] streams the ledger and its score sidecar.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, recipes, repetition
from fractal_wallpapers.paths import tracked_name, under

#: The schema every record and every plan unit this module writes carries.
SCHEMA = 1

#: The subtree this leg's plan and record live under. **No pictures land here**
#: — see the module docstring — so it is deliberately not a member of
#: [`candidate_ledger.POOL_SUBTREES`]: that list is what the orphan sweep
#: enumerates, and a subtree holding no picture in it would be a name the sweep
#: walks for nothing.
UNIT = "repeat_ab"

PLAN_NAME = "plan.jsonl"
DRAW_NAME = "draw.json"
RECORD_NAME = "repeat_ab.json"

#: The traversal this sitting asks about. **Two, and one rung only.** On a cyclic
#: map that is a 2x traversal and on a folded one it is 4x, which are the two arms
#: the ckpt-121 labels did not reject — see the module docstring. `cycles = 3` is
#: out on the evidence and is not a flag.
CYCLES = 2.0

#: Held at 0 on **both** halves, so this measures the traversal and not the
#: rotation `curate rotate` already measured.
PHASE = 0.0

#: Units in one sitting. A unit is one composite tile, so this is 250 tiles and
#: 500 renders — not 125 pairs as [`repetition.TILES`] counts them.
UNITS = 250


class RepeatAbRefused(RuntimeError):
    """A draw this leg will not make, or a population it cannot trust."""


# --------------------------------------------------------------------------- #
# Where it keeps things.
# --------------------------------------------------------------------------- #
def batch_dir(name: str) -> Path:
    """The subtree one sitting owns: its plan and its records. No pictures."""
    return under("curation", UNIT, str(name))


def plan_path(name: str) -> Path:
    return batch_dir(name) / PLAN_NAME


def draw_path(name: str) -> Path:
    return batch_dir(name) / DRAW_NAME


def record_path(name: str) -> Path:
    return batch_dir(name) / RECORD_NAME


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
#: Why a row above the bar is still not one this sitting can ask about. Each is a
#: fact about whether the *comparison* can be made or read, never about quality —
#: the quality question was asked by the bar, upstream of all of these.
REFUSALS = (
    "not_smooth_routed",
    "already_repeated",
    "already_rotated",
    "rejected",
    "off_candidate_regime",
    "no_picture",
    "picture_absent",
    "already_labeled",
)


@dataclass(frozen=True)
class Baseline:
    """One 1x row this sitting may put a repeat beside, and what is known of it."""

    key: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: Whether the map is baked folded, which is what [`repetition.traversals`]
    #: turns the rung into. Read off the cyclic set and never off `mirror`, which
    #: is the map's bake rather than a fact about the gradient.
    folded: bool
    picture: str
    #: The fine head's reading of this candidate, which is what admitted it. At
    #: candidate geometry, because that is the geometry the head was fitted at.
    p_fine: float
    #: The render judge's two columns on the candidate. Recorded, never gated on.
    p_ge4: float
    p_ge3: float
    #: The whole stored recipe block, which is what both halves are built out of.
    recipe: dict


def labeled_places(log=print) -> tuple[set, set]:
    """`(render keys, locations)` a person has already judged in **either finished store**.

    The two gate corpora only. [`retention.labeled_renders`] is the wider set —
    it counts `gallery_grade` too, because a picture is one picture across all
    three and a prune must honour every verdict cast on it — and that is the right
    answer to *what may be deleted* and the wrong one to *what is fresh*: a
    gallery grade is a verdict about how good a picture is given the gate, cast on
    a scale this sitting is not on. The wider count is reported beside this one on
    the record so the choice is readable rather than silent.

    Both halves come back because the two exclusions are different: the render key
    is the row the prompt names, and the location is what the *verdict* keys on
    here, so a place judged under some other colouring is a place whose comparison
    a labeler has already seen material from.
    """
    from fractal_wallpapers.labeling import finished, store

    keys: set = set()
    places: set = set()
    for head in finished.HEADS:
        for row in finished.read(head):
            if row.get("origin") != store.HUMAN:
                continue
            key = finished.render_key(row)
            if key is not None:
                keys.add(key)
            place = finished.place_of(row)
            if place is not None:
                places.add(place)
    log(
        f"[repeat_ab] {len(keys):,} render key(s) at {len(places):,} place(s) carry a human "
        f"verdict in the two finished stores"
    )
    return keys, places


def population(bar: float | None = None, log=print) -> dict:
    """Every row this sitting could ask about, out of **one** stream of the ledger.

    The fine column comes from [`rotation.passing`] — the same accessor every
    other leg reads it through, so `p_fine` here and `p_fine` in the solve are one
    number off one run rather than two readings that agree until one moves. That
    column is what the bar is applied to and it is also what admits a row into
    this population at all: `gallery-grade score-pool` writes it above the render
    bar and nowhere else, which for once is exactly the population wanted.

    The labeled set is resolved before the stream and joined per row, because
    [`retention.render_key_of`] is arithmetic over a row that is already in hand.
    """
    from fractal_wallpapers.curation import budget as budget_module
    from fractal_wallpapers.curation import colorize, hunt, mode_policy, retention, rotation

    started = time.monotonic()
    admitted = rotation.passing(bar, log=log)
    labeled_keys, labeled_locations = labeled_places(log=log)
    cyclic = colorize.cyclic()
    refused = dict.fromkeys(REFUSALS, 0)
    held: list = []
    read = 0
    for row in candidate_ledger.stream():
        read += 1
        key = str(row["key"])
        value = admitted.get(key)
        if value is None:
            continue
        recipe = dict(row.get("recipe") or {})
        palette = dict(recipe.get("palette") or {})
        if hunt.kind_of(str(recipe.get("mode")), bool(row.get("texture_flat"))) != (
            budget_module.SMOOTH
        ):
            refused["not_smooth_routed"] += 1
            continue
        if float(palette.get("cycles") or 1.0) != 1.0:
            refused["already_repeated"] += 1
            continue
        if float(palette.get("phase") or 0.0) != PHASE:
            refused["already_rotated"] += 1
            continue
        if row.get("rejected"):
            refused["rejected"] += 1
            continue
        if not row.get("at_candidate_regime"):
            refused["off_candidate_regime"] += 1
            continue
        if not row.get("picture"):
            refused["no_picture"] += 1
            continue
        if retention.render_key_of(row) in labeled_keys:
            refused["already_labeled"] += 1
            continue
        held.append(row)
    log(
        f"[repeat_ab] {read:,} ledger row(s) in {time.monotonic() - started:.0f}s; "
        f"{len(admitted):,} above the bar, {len(held):,} of them askable"
    )
    keys = {str(row["key"]) for row in held}
    readings = candidate_ledger.scores_by_recipe(
        (
            score
            for score in candidate_ledger.stream_scores()
            if str(score.get("recipe_key")) in keys
        ),
        artifact=candidate_ledger.live_artifact(),
    )
    present = candidate_ledger.present_pictures(held)
    baselines: list[Baseline] = []
    for row in held:
        key = str(row["key"])
        if key not in present:
            refused["picture_absent"] += 1
            continue
        recipe = dict(row["recipe"])
        colormap = str(recipe["colormap"])
        reading = readings.get(key) or {}
        baselines.append(
            Baseline(
                key=key,
                location=str((row.get("location") or {}).get("key")),
                partition=str(row.get("partition") or ""),
                mode=mode_policy.routed_mode_of(row),
                colormap=colormap,
                folded=colormap not in cyclic,
                picture=str(row["picture"]),
                p_fine=float(admitted[key]),
                p_ge4=float(reading.get("p_ge4") or 0.0),
                p_ge3=float(reading.get("p_ge3") or 0.0),
                recipe=recipe,
            )
        )
    folded = sum(1 for one in baselines if one.folded)
    log(
        f"[repeat_ab] {len(baselines):,} baseline(s) at "
        f"{len({one.location for one in baselines}):,} location(s); "
        f"{folded:,} on a folded map, {len(baselines) - folded:,} on a cyclic one"
    )
    return {
        "ledger_rows": read,
        "above_the_bar": len(admitted),
        "bar": float(bar) if bar is not None else None,
        "refused": refused,
        "baselines": baselines,
        "labeled_render_keys": len(labeled_keys),
        "labeled_locations": len(labeled_locations),
        "locations_labeled_elsewhere": len(_keyed_locations(baselines, labeled_locations)),
        "judge_artifact": candidate_ledger.live_artifact(),
        "seconds": round(time.monotonic() - started, 2),
    }


def _keyed_locations(baselines: list, labeled_locations: set) -> set:
    """Which of this population's places carry a human verdict under some OTHER
    colouring — a reading and never a filter.

    The exclusion this leg applies is by render key, which is what the prompt
    names and what keeps the *picture* fresh. A place whose other colouring was
    judged is still a place Matt has seen, and the count of them belongs on the
    record so a later reader can ask whether it mattered rather than discovering
    the question.
    """
    from fractal_wallpapers.supply.location import location_key

    out: set = set()
    for one in baselines:
        place = location_key(one.recipe.get("family") or {}, one.recipe.get("viewport") or {})
        if place is not None and place in labeled_locations:
            out.add(one.location)
    return out


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
def draw(world: dict, units: int = UNITS, seed: int = 0) -> tuple[list, dict]:
    """`(baselines, shape)` — one unit a location, drawn without replacement.

    Seeded twice over and neither draw looks at a score. The *places* are shuffled
    and taken in that order, and at a place holding several qualifying rows one is
    picked at random rather than the best — taking the best would aim the sitting
    at the top of a column this page is not about, and the bar has already made
    the quality claim this leg stands on.

    The folded and cyclic arms are **not** balanced. `curate repetition` gave the
    scarce folded arm a deliberate over-share because its rung was the one the
    card had to be honest about; here the population is what the bar admits and
    the split it lands on is a fact about what is above the bar, which is the
    thing worth reporting.
    """
    rng = random.Random(f"{int(seed)}|{UNIT}")
    by_place: dict = {}
    for one in world["baselines"]:
        by_place.setdefault(one.location, []).append(one)
    places = sorted(by_place)
    rng.shuffle(places)
    drawn: list[Baseline] = []
    for place in places[: max(0, int(units))]:
        choices = sorted(by_place[place], key=lambda one: one.key)
        drawn.append(choices[rng.randrange(len(choices))])
    folded = sum(1 for one in drawn if one.folded)
    shape = {
        "seed": int(seed),
        "units_asked": int(units),
        "units": len(drawn),
        "short_of_the_ask": max(0, int(units) - len(drawn)),
        "eligible_locations": len(by_place),
        "cycles": CYCLES,
        "phase": PHASE,
        "folded_units": folded,
        "folded_traversals": repetition.traversals(CYCLES, True),
        "cyclic_units": len(drawn) - folded,
        "cyclic_traversals": repetition.traversals(CYCLES, False),
        "folded_share_drawn": round(folded / max(1, len(drawn)), 4),
        "folded_share_in_the_population": round(
            sum(1 for one in world["baselines"] if one.folded) / max(1, len(world["baselines"])),
            4,
        ),
        "arms_are_not_balanced": "the split is whatever the population above the bar holds. "
        "curate repetition over-shared its folded arm deliberately; here the share IS a "
        "reading and balancing it would spend the reading",
        "modes": _tally(one.mode for one in drawn),
        "partitions": _tally(one.partition for one in drawn),
        "colormaps": len({one.colormap for one in drawn}),
        "p_fine": _spread(one.p_fine for one in drawn),
        "picked_at_a_place": "seeded uniform over the qualifying rows there, never the "
        "best-scoring one: the bar made the quality claim and a second one would aim the draw",
    }
    return drawn, shape


def _tally(values) -> dict:
    """`{value: count}`, most-used first — the shape every readout here reports in."""
    counts: dict = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _spread(values) -> dict:
    held = sorted(float(value) for value in values)
    if not held:
        return {"n": 0}
    return {
        "n": len(held),
        "min": round(held[0], 6),
        "median": round(held[len(held) // 2], 6),
        "max": round(held[-1], 6),
    }


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
def variant_of(recipe: dict, cycles: float = CYCLES) -> tuple[dict, str]:
    """`(the variant's palette pass, its recipe key)` — the baseline with one knob moved.

    Every other member is carried **because it is not named here**, which is the
    same property [`repetition.plan_of`] proves by re-derivation: the family, the
    frame, the cap, the regime, the mode and its settings, the curve, the map and
    every remaining palette knob travel untouched, and the key is a digest of the
    whole engine spec, so a key that came back equal would mean the traversal had
    not moved.

    The key is taken at the **candidate regime**, which is the regime the stored
    recipe names and therefore the space the baseline's own key lives in. The
    halves are rendered at label geometry — a recipe key names a recipe, and
    naming the two halves in two different spaces would make them incomparable.
    """
    palette = {**dict(recipe.get("palette") or {}), "cycles": float(cycles)}
    variant = recipes.of_record({**dict(recipe), "palette": palette})
    key = recipes.key_of(variant)
    if key == recipes.key_of(recipes.of_record(dict(recipe))):
        raise RepeatAbRefused(
            f"the variant digests to the baseline's own key {key}, so the two halves of this "
            f"tile would be one picture. `cycles` is in the engine spec a recipe key is a "
            f"digest of; a key that does not move means the traversal did not."
        )
    return palette, key


def plan_of(drawn: list, seed: int = 0) -> tuple[list[dict], dict]:
    """The sheet units, one per drawn baseline, in the shape the comparison source cuts.

    Every unit states **both** halves whole — the map, the baseline's palette pass
    and the variant's — because the sheet derives neither. `suggestion` is the
    neutral ordinal on every unit and no head prefilled anything; `facts` prints
    the traversal count and never a column, so the card says what moved and
    nothing about what a model thinks of it.

    `selected_on` is what makes the row readable after this directory is swept:
    both recipe keys, the reading the baseline was **drawn** on at candidate
    geometry, which arm it is, and the traversal count. [`labeling.intake`] copies
    it onto the stored verdict whole.
    """
    from fractal_wallpapers.curation import pool_draw
    from fractal_wallpapers.labeling import attributes

    neutral = attributes.REPEAT_AB.classes.index("neutral") + 1
    units: list[dict] = []
    for one in drawn:
        recipe = one.recipe
        palette, key = variant_of(recipe)
        count = repetition.traversals(CYCLES, one.folded)
        units.append(
            {
                "family": recipe["family"],
                "viewport": recipe["viewport"],
                "maxiter": int(recipe["maxiter"]),
                "mode": str(recipe["mode"]),
                "mode_params": dict(recipe.get("mode_params") or {}),
                "curve": recipe["curve"],
                "colormap": one.colormap,
                "recipe": dict(recipe["palette"]),
                "variant_recipe": palette,
                "leveled": pool_draw.leveled_dir(one.picture),
                "suggestion": int(neutral),
                # The TRUE traversal count and not the `cycles` value, which are
                # two different numbers on a folded map — `repetition.traversals`,
                # and the same rule that module's card follows: the number Matt
                # looks at and the number the row records must not differ.
                "facts": [
                    f"right half: {count:g}x the gradient "
                    f"({'folded' if one.folded else 'cyclic'} map, cycles {CYCLES:g})"
                ],
                "selected_on": {
                    "candidate": one.key,
                    "variant": key,
                    "folded": bool(one.folded),
                    "cycles": float(CYCLES),
                    "traversals": float(count),
                    "phase": float(PHASE),
                    "regime": recipe.get("regime"),
                    "p_fine": round(one.p_fine, 6),
                    "p_ge4": round(one.p_ge4, 6),
                    "p_ge3": round(one.p_ge3, 6),
                    "batch": UNIT,
                },
            }
        )
    keys = {unit["selected_on"]["variant"] for unit in units}
    shape = {
        "units": len(units),
        "distinct_variant_keys": len(keys),
        "prefill": f"{neutral} on every unit — the neutral class, stated by this plan and "
        "not by any head",
        "order": "a seeded shuffle at the sheet, seed "
        f"{int(seed)}. Deliberately NOT good->bad: the premise is that the heads cannot "
        "read this axis, so a score order would put that error into page position",
        "leveled_units": sum(1 for unit in units if unit["leveled"]),
        "leveled_is": "the baseline's own <stem>.leveled/ colormap, given to BOTH halves. "
        "The operator's curve is a fact about the place and the mode, not about the "
        "traversal, and levelling the halves apart would move a second thing between them",
    }
    if len(keys) != len(units):
        raise RepeatAbRefused(
            f"{len(units)} unit(s) produced {len(keys)} distinct variant key(s), so two "
            f"tiles name one picture. One unit a location cannot collide unless a place "
            f"was drawn twice."
        )
    return units, shape


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def run(
    name: str,
    *,
    units: int = UNITS,
    seed: int = 0,
    bar: float | None = None,
    world: dict | None = None,
    log=print,
) -> dict:
    """Draw one sitting and write its plan. Renders nothing.

    **This holds the pool**: [`population`] streams the ledger and its sidecar,
    so nothing else that loads them may run beside it.
    """
    from fractal_wallpapers.curation import solve

    started = time.monotonic()
    world = population(bar=bar, log=log) if world is None else world
    drawn, shape = draw(world, units=units, seed=seed)
    if not drawn:
        raise RepeatAbRefused(
            "the draw came back empty. Every baseline is a smooth-routed ledger row at "
            "cycles 1 and phase 0, above the fine bar, at the candidate regime, with a "
            "picture on disk and no human verdict in either finished store — a store with "
            "none of those is one this sitting has nothing to ask about. "
            "`curate gallery-grade score-pool` is what writes the column the bar reads."
        )
    units_planned, plan = plan_of(drawn, seed=seed)
    _write_jsonl(plan_path(name), units_planned)
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": name,
        "config": {
            "units": int(units),
            "seed": int(seed),
            "cycles": CYCLES,
            "phase": PHASE,
            "phase_is": "held at 0 on BOTH halves. 1,713 of the store's 2,262 repeat rows "
            "carry a rotation too, so a rotated variant would confound this with the axis "
            "`curate rotate` measured",
            "bar": float(solve.DEFAULT_FINE_BAR if bar is None else bar),
            "bar_is": "p_fine(>=4) under the shipped fine head, at CANDIDATE geometry. It "
            "is a CONDITIONAL selection and the whole point of the leg: a rate measured "
            "here is a rate about pictures that are already good at 1x, and is a ceiling "
            "on any rate about the pool",
            "routed_kind": "smooth. `hunt.kind_of` routes the mode, so a modulate whose "
            "texture was flat counts as smooth here exactly as it does everywhere else",
            "freshness": "no row carrying a human verdict in EITHER finished store. A page "
            "mixing judged rows with unjudged ones is the aug_sweep_A failure and cannot be "
            "repaired afterwards",
            "one_per_location": True,
            "held": "family, frame, maxiter, regime, mode, mode_params, curve, colormap, "
            "the levelled band and every palette knob but one. Moved: Palette.cycles, and "
            "nothing else is named anywhere in `variant_of`",
            "scale": "1 the repeat is worse / 2 neutral / 3 the repeat is better. NOT the "
            "1..4 quality scale and never poolable with one — the store is `repeat_ab` and "
            "an attribute row carries no `score` key at all",
        },
        "population": {
            "ledger_rows": world["ledger_rows"],
            "above_the_bar": world["above_the_bar"],
            "refused": world["refused"],
            "baselines": len(world["baselines"]),
            "labeled_render_keys": world["labeled_render_keys"],
            "labeled_locations": world["labeled_locations"],
            "drawn_places_labeled_under_another_colouring": world["locations_labeled_elsewhere"],
            "judge_artifact": world["judge_artifact"],
            "read_seconds": world["seconds"],
        },
        "draw": shape,
        "plan": plan,
        "plan_path": tracked_name(plan_path(name)),
        "wall_seconds": round(time.monotonic() - started, 2),
    }
    _write_json(record_path(name), record)
    _write_json(
        draw_path(name),
        {
            "schema": SCHEMA,
            "name": name,
            "draw": shape,
            "units": [
                {
                    "baseline": one.key,
                    "variant": unit["selected_on"]["variant"],
                    "location": one.location,
                    "partition": one.partition,
                    "mode": one.mode,
                    "colormap": one.colormap,
                    "folded": one.folded,
                    "traversals": unit["selected_on"]["traversals"],
                    "p_fine": unit["selected_on"]["p_fine"],
                    "p_ge4": unit["selected_on"]["p_ge4"],
                    "p_ge3": unit["selected_on"]["p_ge3"],
                    "baseline_picture": one.picture,
                }
                for one, unit in zip(drawn, units_planned, strict=True)
            ],
        },
    )
    log(
        f"[repeat_ab] {len(units_planned):,} unit(s) planned at "
        f"{tracked_name(plan_path(name))}; {tracked_name(record_path(name))}"
    )
    return record


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _write_jsonl(path: Path, rows: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def read(name: str) -> dict:
    """One sitting's record, read back. Raises if the leg never wrote one."""
    path = record_path(name)
    if not path.is_file():
        raise RepeatAbRefused(
            f"{tracked_name(path)} does not exist, so there is no sitting by that name on "
            f"this machine. `curate repeat-ab plan --name {name} --seed <seed>` writes it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "CYCLES",
    "DRAW_NAME",
    "PHASE",
    "PLAN_NAME",
    "RECORD_NAME",
    "REFUSALS",
    "SCHEMA",
    "UNIT",
    "UNITS",
    "Baseline",
    "RepeatAbRefused",
    "batch_dir",
    "draw",
    "draw_path",
    "labeled_places",
    "plan_of",
    "plan_path",
    "population",
    "read",
    "record_path",
    "run",
    "variant_of",
]
