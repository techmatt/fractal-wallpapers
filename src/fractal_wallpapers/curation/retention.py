"""Which candidates are worth the disk, and the counts that survive the rest.

At ten million attempts the ledger's rows are about 5 GB and the 640x360 JPEGs
they name are about 600 GB. Both halves grow with the attempts made, and neither
answers a question about the tenth-best palette at a place nothing will ever
ship. **Storage has to scale with the locations explored, not with the attempts
made**, and this is the rule that makes it.

## One rule, for the row and for the picture it names

A picture is kept **if and only if its row is kept**. That is one sentence now
and it was two until 2026-08-29: a row rule at three per (location, mode) by the
shipped rank key, and a picture rule at five per pair by raw `P(>=4)`. The two
were not nested — a row in the top three by rank could be sixth by `P(>=4)` and
have lost its picture already — and 41 rows were in exactly that position, held
small by luck rather than by rule. One ranking, one constant, and a row on disk
is a row whose pixels a reader can still open.

## What is kept

* **The top [`candidate_ledger.RETAIN_PER_PAIR`] per (location, mode)**, ranked
  **within** the pair by the shipped [`curation.rank_key`] and never against an
  absolute probability. CORN's scale is train-prior calibrated, so every retrain
  moves the probability axis under a fixed cut; the per-mode crossovers already
  span 0.367 to 0.950, which means one number cannot be the bar for all of them.
  A rank inside a (location, mode) group asks the same question at every mode and
  survives a retrain.
* **Five protections**, each keeping a row the rank let go: a seat in a live
  release row, a human rejection, a human label joining it, a row named by the
  rank key's own fitted population, and a seat in a **tentative gallery** —
  [`curation.tentative`], a gallery recorded under a name so that its pictures
  can be referred to by ID, which is a promise the rank would otherwise break.
  They are spelled and applied in [`candidate_ledger.RETAINED_REASONS`], beside
  the transaction that acts on them.

Everything else loses its row and its picture together.

## What that costs, and it is not nothing

A dropped row is a recipe the `known` dedup in [`curation.hunt`] and
[`curation.mine`] can no longer see, so a later draw can pay again for a render
this project already made. That is the price of the rule rather than an
oversight — the alternative is an index of every recipe ever drawn, which grows
with the attempts, which is the thing being removed. [`repeat_draws`] prices it
off the `k` the surviving rows carry, and it **reports and never prevents**.

## This module decides. It does not delete

[`candidate_ledger.prune`] applies, in one transaction, and it is the only thing
in this project that removes a candidate. `tests/test_retention.py` pins that
there is no `unlink` in here: a report that can become a prune by accident is the
one failure mode a policy module has.

## Three aggregates, and why each one is not derivable from the survivors

A count over the kept rows is a count over the winners. These are computed over
**every** attempt, are bounded by their own key spaces, and are what is left
when the rest is gone.

* **`(location, mode) -> attempts`, with the pool stamp.** The draw is a seeded
  permutation over the palette pool, so an attempt count is a *cursor* into that
  permutation — it says how much of the pool has been spent at this pair. Change
  the library or the group collapse and the cursor stops naming the same maps,
  which is why the stamp travels with the count rather than being assumed.
* **`(colormap, mode) -> attempts, successes`.** 942 by 18, bounded and small.
  This is the "which palettes never work anywhere" signal, and it is the one
  thing a discard genuinely destroys: drop colormap identity with the picture
  and the question stops being askable at all.
* **`(location, cell) -> attempts, dominant hits`.** What this location's field
  can and cannot be made to look like. A targeted mine reads it to stop asking a
  place for green that has never once come out green.
"""

from __future__ import annotations

import hashlib

from fractal_wallpapers.curation import candidate_ledger

#: The schema every record here carries.
SCHEMA = 1

#: What the rank says about one row, in the spelling the record uses. The four
#: protections are [`candidate_ledger.RETAINED_REASONS`] and are applied there;
#: this is the ranking's own verdict, and there are only two of them.
RANKED = "ranked"
DROPPED = "dropped"
REASONS = (RANKED, DROPPED)

#: The bar a candidate is counted a success at in [`by_map_mode`]. The seating
#: bar, named here rather than imported so this module stays readable off a
#: store and does not pull the gallery's constants into a count.
SUCCESS_BAR = 0.5


class RetentionError(RuntimeError):
    """A retention decision cannot be made from what is on the row."""


def _pair_of(row: dict) -> tuple:
    """`(location key, mode with its settings)` — the unit the ranking and the cursor are per.

    **The mode half is [`colorize.spelled`], so a mode drawn under its own
    settings is its own pair.** `mode_params` is a keyed member of the recipe —
    `direct_trap_multiply@opacity=0.6` is a different key, a different file and a
    different picture — so it is a different coloring in exactly the sense
    `direct_trap_screen` is, and nobody would ask screen and multiply to compete
    for one pair's three seats.

    Sharing a pair is not neutral here, it is directional, and it points the wrong
    way. The rank key ranks within a pair by what the judge thinks, and on
    `direct_trap_multiply` that judge rewards precisely the fault a setting exists
    to fix: Spearman(in-mask chroma, `P(>=4)`) is **-0.269** over its clearing
    rows. A shared pair would therefore keep the whitest three of five at every
    place — deleting a variant sweep in the same transaction that admitted it, and
    hardest at the places that have been mined most, which are the places a sweep
    is aimed at.

    **No pair that exists moves.** Every row this store has ever held carries no
    settings and [`colorize.spelled`] is the bare mode wherever there are none, so
    this re-groups nothing already written. What it costs is bounded and is paid
    only where somebody varies a mode deliberately: such a place keeps
    [`candidate_ledger.RETAIN_PER_PAIR`] rows per **coloring** rather than three
    across all of them.
    """
    from fractal_wallpapers.curation import colorize

    recipe = row.get("recipe") or {}
    return (
        str((row.get("location") or {}).get("key")),
        colorize.spelled(str(recipe.get("mode")), recipe.get("mode_params")),
    )


# --------------------------------------------------------------------------- #
# The join back to the human labels.
# --------------------------------------------------------------------------- #
def render_key_of(row: dict):
    """One ledger row as [`labeling.finished.render_key`] spells the same picture.

    The join is the *recipe* and never the regime: a person who judged this
    colouring at 1280x720 judged this colouring, and the 640x360 candidate row
    naming the same place, mode and palette is the row that carried the label.
    """
    from fractal_wallpapers.labeling import finished

    recipe = row.get("recipe") or {}
    return finished.render_key(
        {
            "family": recipe.get("family"),
            "viewport": recipe.get("viewport"),
            "mode": recipe.get("mode"),
            "mode_params": recipe.get("mode_params"),
            "curve": recipe.get("curve"),
            "colormap": recipe.get("colormap"),
            "recipe": recipe.get("palette"),
        }
    )


def labeled_renders() -> set:
    """Every render key a **person** has ever cast a score on, over both heads.

    Human origin only. A rule-written row is a derivation this project can run
    again; a person's judgement is not, which is the whole reason the label store
    keeps the two apart.
    """
    from fractal_wallpapers.labeling import finished, store

    out: set = set()
    for head in finished.HEADS:
        for row in finished.read(head):
            if row.get("origin") != store.HUMAN:
                continue
            key = finished.render_key(row)
            if key is not None:
                out.add(key)
    return out


# --------------------------------------------------------------------------- #
# The decision.
# --------------------------------------------------------------------------- #
def keep_per_pair() -> int:
    """The one constant, read from the store that owns it.

    Read through a call rather than re-exported, so this module carries no second
    spelling of a number whose value is a settled decision recorded beside the
    replay that settled it.
    """
    return int(candidate_ledger.RETAIN_PER_PAIR)


def decide(rows: list, scores: dict | None = None, keep: int | None = None) -> dict:
    """`{recipe key: reason}` over every row. Decides; deletes nothing.

    `scores` is `{recipe key: rank value}` **on one basis** — the shipped rank key
    through [`candidate_ledger.prune`], or `P(>=4)` on a single judge artifact
    through [`candidate_ledger.scores_by_recipe`]. A ranking that mixed two bases
    would order rows by which basis happened to reach them. A row with no value
    ranks last within its pair rather than being dropped outright: a row nothing
    has an opinion about is not the same as a row something thinks little of,
    which is [`curation.solve`]'s own convention for the same case.

    Two verdicts and no protections. The protections are applied by the caller
    that holds the stores which answer them, which keeps this a pure function of
    the rows and their values — and so a thing that can be pinned on arithmetic.
    """
    scored = {} if scores is None else scores
    by_pair: dict = {}
    for row in rows:
        by_pair.setdefault(_pair_of(row), []).append(str(row["key"]))
    limit = keep_per_pair() if keep is None else int(keep)
    out: dict = {}
    for keys in by_pair.values():
        # Ranked WITHIN the pair. A tie falls to the key, so the decision is the
        # same on every machine and after any re-sort of the file.
        ordered = sorted(keys, key=lambda key: (-float(scored.get(key) or -1.0), key))
        for at, key in enumerate(ordered):
            out[key] = RANKED if at < limit else DROPPED
    return out


def kept(reason: str) -> bool:
    """Does this reason keep the row, and the picture on it? Everything but
    [`DROPPED`] does — the five protections included, which is why this takes a
    reason rather than testing against [`RANKED`]."""
    return reason != DROPPED


# --------------------------------------------------------------------------- #
# The three aggregates.
# --------------------------------------------------------------------------- #
def pool_stamp(pool: list) -> str:
    """A short digest of the palette pool a draw was made against.

    The count in [`by_place_mode`] is a cursor into a seeded permutation of this
    list, so the count means nothing without it: add a map, retire one, or move
    the group collapse and the k-th draw is a different map. Twelve hex
    characters, which tells two pools apart and is short enough to sit on every
    row of an aggregate.
    """
    return hashlib.sha256("\n".join(str(name) for name in pool).encode("utf-8")).hexdigest()[:12]


def by_place_mode(rows: list, stamp: str | None = None) -> dict:
    """`{(location, mode): {attempts, pool_stamp}}` — the cursor into the palette draw."""
    out: dict = {}
    for row in rows:
        held = out.setdefault(_pair_of(row), {"attempts": 0, "pool_stamp": stamp})
        held["attempts"] += 1
    return out


def by_map_mode(rows: list, scores: dict | None = None, bar: float = SUCCESS_BAR) -> dict:
    """`{(colormap, mode): {attempts, scored, successes}}` — which palettes work anywhere.

    942 maps by 18 modes, so bounded at about seventeen thousand rows however many
    attempts stand behind it. A success is a candidate at or over `bar` on the
    judge the scores were read on; a row with no score counts as an attempt and
    not as a failure, for [`decide`]'s reason, and `scored` is the denominator a
    rate has to be taken over.
    """
    scored = {} if scores is None else scores
    out: dict = {}
    for row in rows:
        recipe = row.get("recipe") or {}
        pair = (str(recipe.get("colormap")), str(recipe.get("mode")))
        held = out.setdefault(pair, {"attempts": 0, "scored": 0, "successes": 0})
        held["attempts"] += 1
        value = scored.get(str(row["key"]))
        if value is None:
            continue
        held["scored"] += 1
        held["successes"] += int(float(value) >= float(bar))
    return out


def by_place_cell(rows: list) -> dict:
    """`{(location, cell): {attempts, dominant}}` — what a place can be made to look like.

    Read off each row's stored `colour` block and never off the carrier table:
    the table is a prior about a *map* and this is the record of what a *place*
    actually produced. A targeted mine reads it to stop asking a location for a
    colour its field has never once delivered.

    `attempts` is every attempt at the location — the denominator every cell at
    that place shares — so a rate here is "how often this place came out this
    colour", not "how often a draw for this colour landed".

    Only the pairs with at least one hit are rows. The full product is 28,420
    locations by 48 cells and almost all of it is zero; a place that has never
    delivered a cell is the **absence** of a row, which is what a reader asking
    "has this ever been green" is testing for.
    """
    cells = _chromatic_cells()
    attempts: dict = {}
    hits: dict = {}
    for row in rows:
        place = str((row.get("location") or {}).get("key"))
        attempts[place] = attempts.get(place, 0) + 1
        for cell in (row.get("colour") or {}).get("cells") or ():
            if str(cell) in cells:
                hits[(place, str(cell))] = hits.get((place, str(cell)), 0) + 1
    return {
        pair: {"attempts": attempts[pair[0]], "dominant": count}
        for pair, count in sorted(hits.items())
    }


def _chromatic_cells() -> set:
    from fractal_wallpapers.palettes import dominance

    return set(dominance.cells())


def aggregates(rows: list, scores: dict | None = None, stamp: str | None = None) -> dict:
    """All three, in one sweep of the rows, with their key spaces reported.

    The sizes are the point of the arrangement: each is bounded by a key space
    and not by the attempt count, so this stays the same size whether it was
    built over 85,129 attempts or ten million.
    """
    place_mode = by_place_mode(rows, stamp)
    map_mode = by_map_mode(rows, scores)
    place_cell = by_place_cell(rows)
    return {
        "schema": SCHEMA,
        "attempts": len(rows),
        "pool_stamp": stamp,
        "place_mode": {"pairs": len(place_mode), "rows": place_mode},
        "map_mode": {"pairs": len(map_mode), "rows": map_mode},
        "place_cell": {"pairs": len(place_cell), "rows": place_cell},
    }


# --------------------------------------------------------------------------- #
# What the rule costs. It prices; it does not prevent.
# --------------------------------------------------------------------------- #
def drawn_before(rows: list) -> dict:
    """`{location: {retained, deepest_k, invisible}}` — the cursor the survivors carry.

    A leg stamps every candidate with **`k`, which candidate at its location it
    was** ([`candidate_ledger.hunt_block`]), and the compacted row keeps it. So a
    location that shows three surviving rows and a deepest `k` of forty has had
    thirty-seven recipes rendered and dropped, and the count survives the drop
    that made it — which is the whole reason this can be priced at all without an
    index of every recipe ever drawn.

    `invisible` is that difference, floored at zero. A location whose rows all
    predate the stamp reads `deepest_k` `None` and `invisible` 0: **no `k` is not
    a `k` of one**, and a reader that took it for one would report the whole
    pre-stamp history as never deepened.

    **It is a lower bound and it is meant to be read as one.** `k` counts within
    one leg, so a place two legs have worked has had more attempts than the
    deepest single `k`, and 32.0% of the rows standing on 2026-08-29 predate the
    stamp entirely. Over the store as it stands this reads 116,097 invisible
    recipes against 243,720 actually dropped — a floor at 47.6% of the truth. A
    floor is the right shape for the question: it says the price is *at least*
    this, and an exact answer needs the index this rule exists to not keep.
    """
    out: dict = {}
    for row in rows:
        place = str((row.get("location") or {}).get("key"))
        held = out.setdefault(place, {"retained": 0, "deepest_k": None, "invisible": 0})
        held["retained"] += 1
        k = (row.get("hunt") or {}).get("k")
        if k is not None:
            held["deepest_k"] = max(held["deepest_k"] or 0, int(k))
    for held in out.values():
        held["invisible"] = max(0, (held["deepest_k"] or 0) - held["retained"])
    return out


def repeat_draws(drawn: list, standing: dict, pool: int) -> dict:
    """What one leg re-rendered because the rule had already deleted it.

    `drawn` is the rows a leg is merging, `standing` is [`drawn_before`] over the
    ledger **as it stood before the merge**, and `pool` is how many maps the draw
    could choose between ([`curation.colorize.pool`]).

    Two numbers rather than one, because only one of them is exact. **`bound`**
    is how many of this leg's rows *could* be repeats — a draw at a location with
    no invisible recipes cannot be one, and a location cannot repeat more than it
    has hidden — and it is a fact about the rows. **`expected`** is how many
    probably are: a draw at a location lands on one of its `invisible` recipes
    with probability `invisible / (pool - retained)` if the maps left over are
    exchangeable, which is the draw's own assumption and not a new one.

    Both are floors, because [`drawn_before`] is: a location's `invisible` count
    is what one leg's `k` can prove and not what the store has actually dropped.
    The exact count needs the set of dropped recipe keys, which is the index this
    rule exists to not keep. So this **reports and never prevents**: it is here to
    say whether the price is worth building something for, and that is a later
    decision.
    """
    at_risk = 0
    bound = 0
    expected = 0.0
    per_place: dict = {}
    for row in drawn:
        place = str((row.get("location") or {}).get("key"))
        held = standing.get(place)
        if not held or held["invisible"] <= 0:
            continue
        at_risk += 1
        seen = per_place.setdefault(place, 0)
        per_place[place] = seen + 1
        bound += 1 if seen < held["invisible"] else 0
        left = max(1, int(pool) - int(held["retained"]))
        expected += min(1.0, held["invisible"] / left)
    return {
        "rows": len(drawn),
        "at_locations_with_deleted_rows": at_risk,
        "locations": len(per_place),
        "bound": bound,
        "bound_is": "how many of these rows COULD be a repeat: a draw at a location "
        "with nothing invisible cannot be, and a location cannot repeat more than it hides",
        "expected": round(expected, 2),
        "expected_is": "the sum over drawn rows of invisible / (pool - retained), which is "
        "the repeat rate if the maps a location has not been offered are exchangeable",
        "pool": int(pool),
    }


# --------------------------------------------------------------------------- #
# What a prune would do. It does not do it.
# --------------------------------------------------------------------------- #
def prune_report(rows: list, values: dict, keep: int | None = None) -> dict:
    """What [`candidate_ledger.prune`] would drop, off rows and rank values already read.

    Arithmetic and no store: the caller has done the reads, and this is the
    ranking's own arithmetic over them. `candidate_ledger.prune(apply=False)` is
    the door that does the reads and calls this, so there is one dry run in this
    project and not two.
    """
    verdicts = decide(rows, values, keep=keep)
    tally = dict.fromkeys(REASONS, 0)
    by_mode: dict = {}
    pictures = 0
    unnamed = 0
    for row in rows:
        reason = verdicts.get(str(row["key"]), DROPPED)
        tally[reason] += 1
        mode = str((row.get("recipe") or {}).get("mode"))
        held = by_mode.setdefault(mode, dict.fromkeys(REASONS, 0))
        held[reason] += 1
        if not row.get("picture"):
            unnamed += 1
        elif reason == DROPPED:
            pictures += 1
    return {
        "schema": SCHEMA,
        "applied": False,
        "keep_per_location_mode": keep_per_pair() if keep is None else int(keep),
        "rows": len(rows),
        "pairs": len({_pair_of(row) for row in rows}),
        "locations": len({str((row.get("location") or {}).get("key")) for row in rows}),
        "verdicts": tally,
        "pictures_named_by_a_dropped_row": pictures,
        "rows_naming_no_picture": unnamed,
        "by_mode": dict(sorted(by_mode.items(), key=lambda item: -item[1][DROPPED])),
    }


__all__ = [
    "DROPPED",
    "RANKED",
    "REASONS",
    "SCHEMA",
    "SUCCESS_BAR",
    "RetentionError",
    "aggregates",
    "by_map_mode",
    "by_place_cell",
    "by_place_mode",
    "decide",
    "drawn_before",
    "keep_per_pair",
    "kept",
    "labeled_renders",
    "pool_stamp",
    "prune_report",
    "render_key_of",
    "repeat_draws",
]
