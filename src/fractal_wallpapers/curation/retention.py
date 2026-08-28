"""Which candidate pictures are worth the disk, and the counts that survive the rest.

At ten million attempts the ledger's rows are about 5 GB and the 640x360 JPEGs
they name are about 600 GB. The rows are the cheap half and they are the half
that answers questions; the pictures are the dear half and almost none of them
will ever be looked at again. **Storage has to scale with the locations
explored, not with the attempts made**, and this is the rule that makes it.

## Rows are never dropped. Only pictures are

Every attempt keeps its recipe row and its `colour` block, forever. That is not
a courtesy — recipe-key dedup is the ledger's whole reason for existing, and a
pass that could not tell it had already made a picture would re-render it. What
this drops is the JPEG the row points at, and the row then says so.

## What is kept

* **The top [`KEEP_PER_PAIR`] per (location, mode)**, ranked **within** the pair
  and never against an absolute probability. CORN's scale is train-prior
  calibrated, so every retrain moves the probability axis under a fixed cut; the
  per-mode crossovers already span 0.367 to 0.950, which means one number cannot
  be the bar for all of them. A rank inside a (location, mode) group asks the
  same question at every mode and survives a retrain.
* **Every row that ever carried a human label**, unconditionally and outside the
  ranking. A labeled picture is instrument: it is what a judge was trained or
  measured against, and losing it costs a number nobody can re-derive.
* **A reservoir sample, one in [`RESERVOIR_ONE_IN`] of the rest**, flagged as
  such. A store holding only its winners cannot answer why anything lost —
  reject autopsy and any future stratified sheet need material from the middle
  of the distribution, and 1 in 200 is enough to have some at every score.

Everything else keeps its row and loses its picture.

## Three aggregates, and why each one is not derivable from the survivors

A count over the kept rows is a count over the winners. These are computed over
**every** attempt, are bounded by their own key spaces, and are what is left
when the pictures are gone.

* **`(location, mode) -> attempts`, with the pool stamp.** The draw is a seeded
  permutation over the palette pool, so an attempt count is a *cursor* into that
  permutation — it says how much of the pool has been spent at this pair. Change
  the library or the group collapse and the cursor stops naming the same maps,
  which is why the stamp travels with the count rather than being assumed.
* **`(colormap, mode) -> attempts, successes`.** 822 by 18, bounded and small.
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

#: How many pictures one (location, mode) pair keeps, ranked within the pair.
#:
#: **Five.** Enough that a place has a set to choose a seat from and to draw a
#: sheet out of, and few enough that the total scales with pairs rather than
#: with attempts.
KEEP_PER_PAIR = 5

#: One in this many of the rest is kept anyway, flagged. **200**, which over the
#: ledger as it stands is a few hundred pictures — cheap enough to be free and
#: dense enough that a reject autopsy has material at every score.
RESERVOIR_ONE_IN = 200

#: Why a picture was kept, in the spelling the record and the row use.
RANKED = "ranked"
LABELED = "labeled"
RESERVOIR = "reservoir"
DROPPED = "dropped"
REASONS = (RANKED, LABELED, RESERVOIR, DROPPED)

#: The bar a candidate is counted a success at in [`by_map_mode`]. The seating
#: bar, named here rather than imported so this module stays readable off a
#: store and does not pull the gallery's constants into a count.
SUCCESS_BAR = 0.5


class RetentionError(RuntimeError):
    """A retention decision cannot be made from what is on the row."""


def _pair_of(row: dict) -> tuple:
    """`(location key, mode)` — the unit the ranking and the cursor are per."""
    return (
        str((row.get("location") or {}).get("key")),
        str((row.get("recipe") or {}).get("mode")),
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
def in_reservoir(key: str, one_in: int = RESERVOIR_ONE_IN) -> bool:
    """Is this recipe key in the reservoir sample?

    A hash of the key and not a random draw, so the answer is the same in every
    process that asks and a row's membership does not depend on the order a
    sweep reached it. sha256 rather than the builtin, which is salted per
    process and would put a different tenth of a percent in the sample on every
    run.
    """
    digest = hashlib.sha256(str(key).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % max(1, int(one_in)) == 0


def decide(
    rows: list,
    scores: dict | None = None,
    labeled: set | None = None,
    keep: int = KEEP_PER_PAIR,
    one_in: int = RESERVOIR_ONE_IN,
) -> dict:
    """`{recipe key: reason}` over every row. Decides; deletes nothing.

    `scores` is `{recipe key: p_ge4}` **on one judge artifact** — through
    [`candidate_ledger.scores_by_recipe`], because a ranking that mixed two
    judges' scales would order pictures by which judge happened to read them. A
    row with no score on that judge ranks last within its pair rather than being
    dropped outright: a picture nothing has an opinion about is not the same as
    a picture something thinks little of.
    """
    scored = {} if scores is None else scores
    marked = set() if labeled is None else labeled
    by_pair: dict = {}
    for row in rows:
        by_pair.setdefault(_pair_of(row), []).append(str(row["key"]))
    out: dict = {}
    for keys in by_pair.values():
        # Ranked WITHIN the pair. A tie falls to the key, so the decision is the
        # same on every machine and after any re-sort of the file.
        ordered = sorted(keys, key=lambda key: (-float(scored.get(key) or -1.0), key))
        for at, key in enumerate(ordered):
            out[key] = RANKED if at < int(keep) else DROPPED
    for row in rows:
        key = str(row["key"])
        if out.get(key) != DROPPED:
            continue
        if marked and render_key_of(row) in marked:
            out[key] = LABELED
        elif in_reservoir(key, one_in):
            out[key] = RESERVOIR
    return out


def kept(reason: str) -> bool:
    """Does this reason keep a picture? Every reason but [`DROPPED`] does."""
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

    822 maps by 18 modes, so bounded at about fifteen thousand rows however many
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
# What a prune would do. It does not do it.
# --------------------------------------------------------------------------- #
def prune_report(
    rows: list | None = None,
    scores: dict | None = None,
    labeled: set | None = None,
    keep: int = KEEP_PER_PAIR,
    one_in: int = RESERVOIR_ONE_IN,
    log=print,
) -> dict:
    """What a prune of the ledger as it stands **would** delete. Deletes nothing.

    The policy is going-forward, and this is the number that says what applying
    it backwards would cost — so that the decision to apply it backwards, if it
    is ever taken, is taken against a measurement. Sizes are a `stat` of each
    picture that is on this machine; a row whose picture is already gone is
    counted apart and contributes no bytes.
    """
    from pathlib import Path

    from fractal_wallpapers.paths import rehome

    stored = candidate_ledger.read() if rows is None else list(rows)
    if scores is None:
        read = candidate_ledger.read_scores()
        scores = {
            key: float(row.get("p_ge4") or 0.0)
            for key, row in candidate_ledger.scores_by_recipe(read).items()
        }
    marked = labeled_renders() if labeled is None else labeled
    log(f"[retention] {len(stored):,} row(s), {len(marked):,} human-labeled render key(s)")
    verdicts = decide(stored, scores, marked, keep=keep, one_in=one_in)
    tally = dict.fromkeys(REASONS, 0)
    by_mode: dict = {}
    bytes_dropped = 0
    bytes_kept = 0
    missing = 0
    no_picture = 0
    for row in stored:
        key = str(row["key"])
        reason = verdicts.get(key, DROPPED)
        tally[reason] += 1
        mode = str((row.get("recipe") or {}).get("mode"))
        held = by_mode.setdefault(mode, {**dict.fromkeys(REASONS, 0), "bytes_dropped": 0})
        held[reason] += 1
        if not row.get("picture"):
            no_picture += 1
            continue
        # `rehome` answers None for a stored name with no artifacts component,
        # which is not a name it knows anything about — the caller keeps what it
        # had. Every ledger picture is under the tree today; a fixture's is not.
        stored_name = str(row["picture"])
        path = rehome(stored_name) or Path(stored_name)
        try:
            size = path.stat().st_size
        except OSError:
            missing += 1
            continue
        if reason == DROPPED:
            bytes_dropped += size
            held["bytes_dropped"] += size
        else:
            bytes_kept += size
    return {
        "schema": SCHEMA,
        "applied": False,
        "policy": {
            "keep_per_location_mode": int(keep),
            "ranked": "within the (location, mode) pair, never against an absolute probability",
            "labeled": "every row that ever carried a HUMAN label, unconditionally",
            "reservoir_one_in": int(one_in),
            "rows_dropped": "never — only pictures",
        },
        "rows": len(stored),
        "pairs": len({_pair_of(row) for row in stored}),
        "locations": len({str((row.get("location") or {}).get("key")) for row in stored}),
        "verdicts": tally,
        "would_keep": sum(count for reason, count in tally.items() if kept(reason)),
        "would_delete": tally[DROPPED],
        "bytes": {
            "would_delete": bytes_dropped,
            "would_keep": bytes_kept,
            "would_delete_gib": round(bytes_dropped / 2**30, 3),
            "would_keep_gib": round(bytes_kept / 2**30, 3),
            "share_deleted": round(bytes_dropped / max(1, bytes_dropped + bytes_kept), 4),
        },
        "pictures": {"row_names_none": no_picture, "named_but_absent": missing},
        "by_mode": dict(sorted(by_mode.items(), key=lambda item: -item[1][DROPPED])),
    }


__all__ = [
    "DROPPED",
    "KEEP_PER_PAIR",
    "LABELED",
    "RANKED",
    "REASONS",
    "RESERVOIR",
    "RESERVOIR_ONE_IN",
    "SCHEMA",
    "SUCCESS_BAR",
    "RetentionError",
    "aggregates",
    "by_map_mode",
    "by_place_cell",
    "by_place_mode",
    "decide",
    "in_reservoir",
    "kept",
    "labeled_renders",
    "pool_stamp",
    "prune_report",
    "render_key_of",
]
