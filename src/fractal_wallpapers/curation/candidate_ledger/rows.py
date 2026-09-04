"""One ledger row, and the blocks it carries.

What a row *is*, apart from where it is kept: the recipe it stands on, the
location's two keys, the colour, the hunt block, and the sidecar's score row.
Pure shape — it builds dicts and reads them, and the only store it touches is
[`store`] below it.

## A superseded framing is a re-key, not a rebuild

Framing refinement is moving into harvest, and a harvest refinement **moves the
location key** ([`supply.ledgers.refined_of`]) — deliberately, because a walk's
refined frame simply is the location it found. That will re-key a large fraction
of the pool.

So the row's identity is the **recipe** and never the location key. A recipe
already carries the frame it was drawn at, so one row per recipe is one row per
(location, recipe) with the location's identity as a field rather than as part of
the name. When harvest re-frames a place, the rows standing on the old key keep
their pictures and their colours, and what changes is a field: `location.key`
gains a `superseded_by` beside it. Nothing is rebuilt and nothing is deleted.

Both keys are on every row and **neither is reconciled here**. 2,903 of the
15,488 renders on record carry a `location.key` that disagrees with the viewport
they were drawn at, and every one is a refined-frame row: the gallery pass
pins a location's identity to the frame on record while rendering somewhere else
inside it, which is what stops one place taking two seats. `location.key` is that
recorded identity; `location.frame_key` is the identity of the frame the pixels
are of. A reader that wants "the same place" takes the first; a reader that wants
"the same picture" takes the recipe key.
## The `hunt` block says what the draw intended

A row made by a hunt, a mine or a depth run carries the intention beside the
outcome: which leg drew it, which mode and colormap, which band or cell it was
drawn *for*, and **`k` — which candidate at its location it was**. That last one
is here rather than only in the run's own `sequence.jsonl` because those live
under the regenerable tree and the ledger does not, and the corrections a reader
has to make are `k`-dependent: a prime rate read off the maximum of `k` noisy
judgements is a winner's-curse estimate, and the multiplier that turns it into a
calibrated one is a function of `k`.

The field is **additive**, and every row written before the stamp existed has no
`k` at all. [`k_of`] returns `None` for those rather than 1, because a reader
that took a missing `k` for a first draw would report that whole history as
unselected and under-correct every estimate over it.
"""

from __future__ import annotations

import json

from fractal_wallpapers.curation import recipes
from fractal_wallpapers.curation.candidate_ledger import store
from fractal_wallpapers.curation.candidate_ledger.store import (
    ASKED_FOR,
    ENGINE_FIELD,
    SCHEMA,
    UNKNOWN_ENGINE,
)
from fractal_wallpapers.supply import location as location_module


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def row(
    *,
    recipe: recipes.Recipe,
    key: str,
    source: dict,
    also_rendered: list = (),
    also_recorded: list = (),
    colour: dict | None = None,
    picture: str | None = None,
    rejected: dict | None = None,
    texture_flat: bool = False,
    engine: str | None = None,
) -> dict:
    """One ledger row: a recipe, where it stands, what colour it is, who made it.

    `source` is the decision row this was read from — its own `location` block,
    its `key`, its run and candidate.

    The two lists beside it are different facts and are counted apart, because
    conflating them costs the ledger the number it exists to report.
    `also_rendered` is every *other render* that digests to this recipe: seconds
    a pass spent on a picture another pass already had, and the thing a cache
    prevents. `also_recorded` is every other decision **row** about the render
    this one names — a pass writes a gate row for the attempt and a release row
    for the seat, one picture, two decisions — and is what a protection joining a
    recipe back to its seat reads.

    ## The row carries what a reader consumes, and two invariants

    It was three kilobytes and is now about half of that. What came off was
    derived from the reader sites and not from a field list: `colour.cell_shares`
    and `colour.family_shares`, which every consumer skips in favour of the
    already-thresholded `cells`/`families`; the fields stored twice
    (`recipe_key`, `regime`, `palette_group`, and `location`'s copy of the
    recipe's `family`, `viewport` and `maxiter`); and the fields nothing reads at
    all (`location.frame_key`, `location.ledger`, `location.framing`,
    `location.superseded_by`, `provenance.store`, `provenance.source_key`,
    `provenance.engine`, and the `hunt` block's copies of the mode, the colormap
    and the draw's own bookkeeping).

    Two things it must always be able to do, and both are what the `recipe` block
    is here whole for:

    * **The recipe key stays recomputable.** [`recipes.of_row`] rebuilds the
      dataclass off `recipe` alone and [`recipes.key_of`] digests it back to
      `key`. `tests/test_candidate_ledger.py` holds that over the live store.
    * **The picture stays re-renderable from the row alone.** The same rebuilt
      recipe is [`recipes.Recipe.row`], which is the engine spec.

    Everything derived is derived rather than stored — `at_candidate_regime` and
    `texture_flat` are the two exceptions, and for one reason each is a bare
    boolean nothing can re-derive from the row. The first: five readers take it,
    and a pool that silently came back **empty** is how the last attempt at this
    row was noticed. The second: it is the engine's own
    `RenderReport.texture_flat`, and re-deriving it costs a *render* — the picture
    is the only place the fact survives, and even then only as the absence of
    something. See [`fractal_wallpapers.curation.mode_policy.routed_mode`] for
    what a `True` means, and [`fractal_wallpapers.coloring.texture_flat`] for how
    the rows written before the engine reported it were filled in.

    It is deliberately **not** the flatness sidecar's shape
    ([`curation.flatness`]). That column is a reading of a picture by a rule that
    could be re-chosen, so it is keyed on the recipe and kept out of the row.
    This one has no constant to re-choose — the engine either had a span to
    normalize against or it did not — and it is measured blind to a dead texture
    layer by the sidecar, whose `flat16_1.0` reads 0.182 on the degenerate rows
    against 0.170 on the varying ones: a rank-swept smooth field has no dead
    space, so the column that measures dead space cannot see this.
    """
    location = source.get("location") or {}
    place = location.get("key")
    return {
        "schema": SCHEMA,
        "key": str(key),
        "partition": location.get("partition"),
        "location": {
            # The recorded identity: what the one-wallpaper-per-location cap
            # counts on, and what a refinement deliberately does NOT move.
            "key": place,
            # Whether the pixels are of the frame that identity names. The frame's
            # own key was here beside it and is not any more: it is
            # `_frame_key(recipe)` and nothing read it, while this is a bare
            # boolean the census reports and re-deriving it would put a
            # `location_key` call on every row of a sweep.
            "agrees": place == _frame_key(recipe),
        },
        "recipe": recipe.record(),
        "at_candidate_regime": recipes.is_candidate_regime(recipe),
        # Whether the coloring's texture layer said nothing, so this row routes as
        # smooth-with-rank. False on every mode that has no texture, which is
        # sixteen of the seventeen.
        "texture_flat": bool(texture_flat),
        "colour": colour_kept(colour),
        # Which build drew the pixels, as PROVENANCE and nothing else — see
        # [`engine_of`] for what does not read it. Unsaid is [`UNKNOWN_ENGINE`]:
        # this function renders nothing and asks nothing, so a caller that did
        # not name a build did not have one, and the whole backfilled pool is
        # exactly that. It is outside `recipe`, so the recipe key does not move.
        ENGINE_FIELD: str(engine or UNKNOWN_ENGINE),
        "provenance": {
            "run": source.get("run"),
            "candidate": source.get("candidate"),
            "also_rendered": list(also_rendered),
            "also_recorded": list(also_recorded),
        },
        "picture": picture,
        "rejected": rejected,
    }


def colour_kept(colour: dict | None) -> dict | None:
    """One colour block as the row stores it: the two thresholded lists, no shares.

    Takes a block rather than a [`palettes.dominance.Reading`] so that a colour
    *carried* from a row written under the old shape is cut the same way a fresh
    read is. `None` in, `None` out — a recipe with no picture has no colour, and
    an empty block would say something different.
    """
    if not colour:
        return None
    return {
        "cells": list(colour.get("cells") or []),
        "families": list(colour.get("families") or []),
    }


def scores_by_recipe(scores=None, artifact: str | None = None, regime: str | None = None) -> dict:
    """`{recipe key: score row}` for **one** judge artifact, refusing a mixed read.

    The sidecar is keyed `(recipe key, artifact, regime)` precisely because a
    number is comparable only inside that triple. A join that flattened it to the
    recipe key alone would be last-row-wins across artifacts: two judges' scales
    in one ordering, with nothing anywhere saying so. Today the store holds one
    artifact and one regime, so such a join is right by luck; the first adoption
    is what turns luck into a silent wrong answer, and an adoption is a thing
    this project plans to do.

    So the artifact is named — `None` means the live head — and a row read on any
    other is **left out**, counted, and reported by [`stale_scores`]. Omitted and
    not silently rescaled: a recipe with no reading on the live judge has no
    score, which is a different and honest thing from having an old one.
    """
    read = store.read_scores() if scores is None else list(scores)
    want = store.live_artifact() if artifact is None else str(artifact)
    return {
        str(row["recipe_key"]): row
        for row in read
        if str(row.get("judge_artifact")) == want
        and (regime is None or str(row.get("regime")) == str(regime))
    }


def stale_scores(scores=None, artifact: str | None = None) -> dict:
    """What a join on the live judge leaves behind: `{artifact: rows}`.

    A census and not a warning. A store holding two artifacts is the ordinary
    state after an adoption — the old readings are kept, because a picture read
    by two judges is two facts — and this is how a caller says how much of its
    population it is about to have no score for.
    """
    read = store.read_scores() if scores is None else list(scores)
    want = store.live_artifact() if artifact is None else str(artifact)
    out: dict = {}
    for row in read:
        held = str(row.get("judge_artifact"))
        if held != want:
            out[held] = out.get(held, 0) + 1
    return dict(sorted(out.items(), key=lambda item: -item[1]))


def k_of(row: dict) -> int | None:
    """Which candidate at its location this row was, or `None` where it cannot say.

    The `k` a planner stamps in the row's `hunt` block. It is **additive**: the
    85,129 rows written before the stamp existed carry no `k` at all, and a
    reader that treated a missing one as 1 would report the whole of that history
    as unselected first draws and under-correct every winner's-curse estimate
    over it. `None` is the honest answer and a caller has to decide what to do
    with it.
    """
    held = (row.get("hunt") or {}).get("k")
    try:
        return None if held is None else int(held)
    except (TypeError, ValueError):
        return None


def _frame_key(recipe: recipes.Recipe) -> str | None:
    """The location identity of the frame a recipe was drawn at, spelled as stored.

    Through [`supply.location.location_key`], which is this project's one answer
    to "the same location", and serialized the way the decision rows already
    serialize it so the two are comparable as strings.
    """
    try:
        return json.dumps(list(location_module.location_key(recipe.family, recipe.viewport)))
    except (KeyError, TypeError, ValueError):
        return None


def _framing(block: dict | None) -> dict | None:
    """The refine leg's verdict, thinned to what a re-key later needs.

    Both frames and which one was used. The scores that decided it stay on the
    decision row: this store is about pictures, and a framing's `P(>=4)` is about
    a location.
    """
    if not block:
        return None
    return {
        "adopted": bool(block.get("adopted")),
        "used": block.get("used"),
        "original_viewport": (block.get("original") or {}).get("viewport"),
        "refined_viewport": (block.get("refined") or {}).get("viewport"),
    }


def score_row(*, key: str, artifact: str, regime: str, head: str, read: dict, source: dict) -> dict:
    """One reading of one recipe by one judge artifact at one regime.

    Keyed on the three of them together, because that triple is what a number is
    only comparable within. `block` says whether this is what the run read on the
    night it ran or a later re-score's reading of the same picture — the same
    distinction [`records.live_reading`] draws, kept rather than collapsed.
    """
    return {
        "schema": SCHEMA,
        "key": f"{key}|{artifact}|{regime}",
        "recipe_key": str(key),
        "judge_artifact": str(artifact),
        "regime": str(regime),
        "head": str(head),
        "p_ge2": read.get("p_ge2"),
        "p_ge3": read.get("p_ge3"),
        "p_ge4": read.get("p_ge4"),
        "rank_score": read.get("rank_score"),
        "block": "scores_current" if source.get("scores_current") else "scores",
        "read_by": {"run": source.get("run"), "candidate": source.get("candidate")},
    }


def hunt_block(named: dict | None) -> dict:
    """The `hunt` block as the row keeps it: the seconds, the draw, and the colour ask.

    Two fields of nine, plus [`ASKED_FOR`] where there is an ask to carry.
    `seconds` is what [`headroom.render_cost`] prices a leg off; `k` is what
    [`k_of`] hands the winner's-curse correction, and it is the one field of the
    block that cannot be recovered from anywhere else. The other seven were the
    leg's name (which is `provenance.run`), its mode and its colormap (which are
    the recipe's), and four numbers about the draw that only the leg's own record
    ever read.

    **`drawn_for` was one of the seven and should not have been, and the store
    carries the hole.** `curation/README.md` names `hunt.drawn_for` as the exact
    separator a census drops before reading an unconditioned rate — but that is a
    reader with a person on the end of it, not a call site, and the 2026-08-29
    trace-of-readers cut found no code reading it and took it off. The whole store
    was rewritten in the same commit, so **the 3,042 rows the conditioned arm
    merged before that date have no stamp and cannot be filtered out of any rate
    taken over them, ever**. It is restored here, which repairs the next aimed leg
    and not any earlier one.
    """
    out = {"seconds": (named or {}).get("seconds"), "k": (named or {}).get("k")}
    for field in ASKED_FOR:
        held = (named or {}).get(field)
        if held:
            out[field] = held
    return out


def colour_block(reading) -> dict:
    """One [`palettes.dominance.Reading`] as a ledger row stores it.

    Its own function because two writers make ledger rows — this backfill, off
    pictures that already exist, and [`curation.hunt`], off a picture it has just
    rendered — and a colour block written two ways is two stores wearing one
    name.

    **The share vectors are not in it.** They were, at 678 bytes a row and 236 MB
    over the store, and no reader ever opened one: every consumer — the pool, the
    ceiling, the census, the retention aggregates, the rank key's stratum — takes
    the already-thresholded `cells` and `families`, which is the reading
    [`palettes.dominance.RULE`] has already made. A share vector kept beside the
    verdict it produced is the verdict stored twice, once in a form nothing can
    act on.
    """
    return {"cells": list(reading.cells), "families": list(reading.families)}
