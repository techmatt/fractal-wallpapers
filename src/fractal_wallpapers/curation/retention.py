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
  release row, a human rejection, a human verdict joining it — from either gate
  or from the conditional [`labeling.gallery_grade`] store, see
  [`labeled_renders`] — a row named by the rank key's own fitted population, and
  a seat in a **tentative gallery** —
  [`curation.tentative`], a gallery recorded under a name so that its pictures
  can be referred to by ID, which is a promise the rank would otherwise break.
  They are spelled and applied in [`candidate_ledger.RETAINED_PROTECTIONS`],
  beside the transaction that acts on them.
* **One colour allowance**, [`FAMILY_ALLOWANCE`], Matt's cut of 2026-09-15: up to
  one further row per pair that is best-in-a-family none of the kept five is
  dominant in. Not a protection — it is the rank term keeping a second row, so it
  is applied in [`decide`] with the ranking rather than beside the stores.

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

#: The prose this module's records carry on their `*_is` / `*_are` fields, in
#: one place. The builder reads it at write time and the row still carries the
#: sentence WHOLE — nothing here is a pointer, and a record read years later off
#: the archive tier needs no checkout to resolve. Not versioned either. The
#: argument for both, and the reason not to re-propose the pointer, is at
#: `fractal_wallpapers/README.md`'s *A record's prose has one copy in the source
#: and a whole copy on every row*.
SCHEMA_NOTES: dict[str, str] = {
    "bound_is": "how many of these rows COULD be a repeat: a draw at a location "
    "with nothing invisible cannot be, and a location cannot repeat more than it hides",
    "expected_is": "the sum over drawn rows of invisible / (pool - retained), which is "
    "the repeat rate if the maps a location has not been offered are exchangeable",
}


#: What the rank says about one row, in the spelling the record uses. The five
#: protections are [`candidate_ledger.RETAINED_PROTECTIONS`] and are applied
#: there; these are the ranking's own verdicts, and there are three of them.
RANKED = "ranked"
FAMILY = "kept_for_a_family"
DROPPED = "dropped"
REASONS = (RANKED, FAMILY, DROPPED)

#: **How many further rows one pair may keep for a colour family its kept
#: [`keep_per_pair`] miss.** Matt's cut of 2026-09-15, and A(K=1) is its name in
#: the sizing that chose it.
#:
#: A pair's five are taken on the rank and the rank does not ask what colour a
#: picture is, so a place can be held five times in one family and lose the only
#: row it ever made in another. This keeps the best-ranked such row, one per
#: pair, for a family none of the five is dominant in.
#:
#: **Why this and not a named scarce set.** `family_slot_sizing_ckpt125` priced
#: both over a real pre-prune population. The scarce-set rule is far more
#: efficient per row — 1.7 rows a conversion against this rule's 18.7 — and it
#: was refused anyway: the set has to be hand-named, the store-derived version of
#: it is **empty at both bars**, and a list that has to be maintained goes stale
#: without anything failing. This rule needs no list and aims itself: **73 of its
#: 105 conversions landed in the five weakest families unprompted**.
#:
#: **What it costs is bounded and small.** Exact off the kept set: at most
#: **+14,933 rows, x1.0325 of the store, 3.32 GiB** — a pair can only absorb a
#: row for a family it does not already hold, and the kept five cover a median of
#: 5 of the twelve families and never all twelve. K=2 doubles the ceiling for 23
#: more conversions at 64 rows each, which is what ruled it out.
#:
#: **It binds at a FULL pair and nowhere else**, which is why it is cheap and
#: why it is not retroactive: 187,160 of 202,093 pairs have room, so the store
#: can grow 2.2x before this rule acts anywhere new, and a store already at the
#: keep has nothing beyond the five for an allowance to reach. The rows earlier
#: prunes took are gone and this does not go looking for them.
FAMILY_ALLOWANCE = 1

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
    for one pair's seats.

    Sharing a pair is not neutral here, it is directional, and it points the wrong
    way. The rank key ranks within a pair by what the judge thinks, and on
    `direct_trap_multiply` that judge rewards precisely the fault a setting exists
    to fix: Spearman(in-mask chroma, `P(>=4)`) is **-0.269** over its clearing
    rows. A shared pair would therefore keep the whitest few of every variant
    sweep at every place — deleting a variant sweep in the same transaction that admitted it, and
    hardest at the places that have been mined most, which are the places a sweep
    is aimed at.

    **No pair that exists moves.** Every row this store has ever held carries no
    settings and [`colorize.spelled`] is the bare mode wherever there are none, so
    this re-groups nothing already written. What it costs is bounded and is paid
    only where somebody varies a mode deliberately: such a place keeps
    [`candidate_ledger.RETAIN_PER_PAIR`] rows per **coloring** rather than one
    keep across all of them.
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
    """Every render key a **person** has ever cast a verdict on about a picture.

    Human origin only. A rule-written row is a derivation this project can run
    again; a person's judgement is not, which is the whole reason the label store
    keeps the two apart.

    **Every corpus that judges a picture, and not only the two gates.** The two
    [`labeling.finished`] heads answer *is this worth keeping*;
    [`labeling.gallery_grade`] answers how good one is *given* that it already
    cleared them, and its rows are keyed through the same
    [`labeling.finished.render_key`] on purpose — a picture is one picture across
    all three. A protection that read the gates alone would leave the third
    store's population prunable while reading, from the outside, as the label
    protection running.

    That is not hypothetical and it is what put this line here. The
    `gallery_grade` store's first sitting is 700 seated rows and **300
    runners-up**, and the runners-up are the near-neighbour half the store exists
    to separate — the hard negatives a head fitted on it has to learn from. The
    seated 700 are held by [`tentative.protected_keys`], because the record they
    were drawn from names them. Measured 2026-09-06, **233 of the 300 were held
    by nothing**, 95 of those carrying a `<stem>.leveled/` colormap that dies with
    its picture. Retention is not retroactive, so one merge before the head was
    fit would have taken them permanently.

    **The join reaches the exact candidate here rather than a sibling of it.**
    `render_key` is the recipe and never the regime, so in principle several
    ledger rows can answer to one key and a prune could keep the wrong one's
    picture — which would take a live `.leveled/` with it. Over the store as it
    stands, 2026-09-06: all 1,000 graded rows key into the ledger, each key is
    carried by **exactly one** of its 308,419 rows, and that row is the candidate
    the draw named on `selected_on`. `tests/test_gallery_grade_retention.py` is
    the pin, and it asserts the reach rather than the count.

    **Remembered against the stat of every row file it would read**, so a second
    call over unchanged stores is a few dozen `stat`s rather than 31k keys
    derived again (1.1 s, 2026-09-26). A prune, a rotation and an inventory each
    ask, and the fast lane's prune guards asked once per prune. A store written
    since, or pointed somewhere else, is a different signature and is read afresh.
    """
    from fractal_wallpapers.labeling import finished, gallery_grade, store

    signature = tuple(
        (str(path), stat.st_mtime_ns, stat.st_size)
        for path in [
            *(path for head in finished.HEADS for path in finished.row_paths(head)),
            *gallery_grade.row_paths(),
        ]
        for stat in (path.stat(),)
    )
    if _LABELED_RENDERS[0] == signature:
        return set(_LABELED_RENDERS[1])

    out: set = set()
    for head in finished.HEADS:
        for row in finished.read(head):
            if row.get("origin") != store.HUMAN:
                continue
            key = finished.render_key(row)
            if key is not None:
                out.add(key)
    # Every row of the store and not [`gallery_grade.resolved`]'s current ones: a
    # superseded verdict is still a picture a person opened and judged, and the
    # row that replaced it names the same render anyway. Latest-wins is a
    # question about what the store *says*; this is a question about what it
    # would have to be able to show.
    for row in gallery_grade.read():
        if row.get("origin") != store.HUMAN:
            continue
        key = gallery_grade.render_key(row)
        if key is not None:
            out.add(key)
    _LABELED_RENDERS[:] = [signature, frozenset(out)]
    return out


#: `[signature, keys]` of the last [`labeled_renders`] read.
_LABELED_RENDERS: list = [None, frozenset()]


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


def free_slots(rows, keep: int | None = None) -> dict:
    """`{(location key, coloring): slots}` — how many rows a pair can still take.

    **The one spelling of an arithmetic that was being done by hand in leg rigs,
    and got done backwards once.** `keep - len(pair)`, over the rows already in
    hand, for every pair the rows name; pairs at or over the keep are left out
    rather than carried at zero, so the mapping is *where there is room* and a
    caller cannot accidentally plan onto a full pair by iterating it.

    **It is a subtraction and never a scan**, and that is a property of the rule
    rather than an optimisation. [`decide`] keeps `min(keep, attempts)` on the
    rank — it sorts a pair and takes the first `keep`, with no branch on how many
    the pair holds — so a pair holding fewer than the keep has never had more
    attempts than it holds and nothing was pruned away from it. There is
    therefore nothing to go looking for.

    **[`FAMILY_ALLOWANCE`] does not change that**, and it is worth saying because
    it looks as though it must: the allowance can only keep a row *below* the
    top `keep`, so it acts at a full pair and never at one with room. A pair this
    reports two slots on is a pair the allowance has never touched. What it does
    change is the other direction — a full pair may now hold `keep + 1` — so this
    reports zero slots there, exactly as it does for a pair held over the keep by
    a protection.

    ⚠ **The keep moved 3 -> 5 on 2026-09-06 and one reading of this did not
    survive it.** Under keep 3, a pair holding fewer than the keep had never had
    more *attempts*, so a free slot also meant an unexplored pair. After the flip
    that reading holds only for a pair holding fewer than **three**: a legacy pair
    sitting at exactly 3 may have been pruned there at the old keep, so its two
    new slots are room rather than evidence that nobody has looked. The
    arithmetic is unchanged and is still exactly right for planning — a slot is a
    row the merge will keep either way. What is gone is *free slot therefore
    unexplored*, and the attempts the old keep pruned are not recoverable.
    [`README.md`](README.md)'s *The growth law* carries the same caveat.

    `rows` is anything iterable of ledger rows — the stream included, since this
    reads each row once and holds only the counts.
    """
    limit = keep_per_pair() if keep is None else int(keep)
    held: dict = {}
    for row in rows:
        pair = _pair_of(row)
        held[pair] = held.get(pair, 0) + 1
    return {pair: limit - count for pair, count in held.items() if count < limit}


def free_slot_census(rows, keep: int | None = None) -> dict:
    """What [`free_slots`] adds up to, in the shape a report and a plan both want.

    Counted apart because the three counts are not each other and each has been
    quoted for another: **pairs** with room, **slots** across them, and the
    **places** those pairs stand on. 37.7% of pairs held fewer than three on
    2026-09-06 while the rows in them were 24.4% of the ledger, and a sentence
    that says "37.7% of the pool" is wrong by half.
    """
    limit = keep_per_pair() if keep is None else int(keep)
    slots = free_slots(rows, keep=limit)
    return {
        "schema": SCHEMA,
        "keep": limit,
        "pairs_with_room": len(slots),
        "free_slots": sum(slots.values()),
        "places_with_room": len({pair[0] for pair in slots}),
    }


def _families_of(row: dict) -> tuple:
    """The colour families this row is dominant in, off the row's own block.

    `colour.families` is **stored and not derived**, which is why this reads it
    rather than computing it off `colour.cells`: family dominance is a higher cut
    against a summed mass, so a picture can be dominant in a family no cell of
    which leads and in a cell whose family does not.
    `candidate_ledger.sweep._prune_meta` carries the same argument at the site
    that reads it.

    A row with no block reads empty and is never kept by [`FAMILY_ALLOWANCE`],
    which is the right answer rather than a gap: a row nothing has read a colour
    off cannot be the row that makes a family reachable. 47 of 3,000 sampled
    store rows are in that position.
    """
    return tuple((row.get("colour") or {}).get("families") or ())


def decide(rows: list, scores: dict | None = None, keep: int | None = None) -> dict:
    """`{recipe key: reason}` over every row. Decides; deletes nothing.

    `scores` is `{recipe key: rank value}` **on one basis** — the shipped rank key
    through [`candidate_ledger.prune`], or `P(>=4)` on a single judge artifact
    through [`candidate_ledger.scores_by_recipe`]. A ranking that mixed two bases
    would order rows by which basis happened to reach them. A row with no value
    ranks last within its pair rather than being dropped outright: a row nothing
    has an opinion about is not the same as a row something thinks little of,
    which is [`curation.solve`]'s own convention for the same case.

    Three verdicts and no protections. The protections are applied by the caller
    that holds the stores which answer them, which keeps this a pure function of
    the rows and their values — and so a thing that can be pinned on arithmetic.

    ## The third verdict is the family allowance

    [`FAMILY_ALLOWANCE`] carries the rule and the argument for it. Here it is
    arithmetic: below the top `keep` the rows stay in rank order, and the first
    one carrying a family **none of the kept five is dominant in** is kept as
    [`FAMILY`]. Taken best-ranked first, which is the only ordering that needs no
    second rule to break a tie between two families — and each one taken adds its
    families to the represented set, so `k > 1` cannot spend two slots on one
    family.

    **A row's families come off the row** ([`_families_of`]), so a caller handing
    stubs that carry no colour block gets exactly today's two verdicts. That is a
    real case rather than a defensive one: `curation.label_migration` prices a
    merge off pair-and-value stubs, and it is written down there.
    """
    scored = {} if scores is None else scores
    by_pair: dict = {}
    for row in rows:
        by_pair.setdefault(_pair_of(row), []).append(row)
    limit = keep_per_pair() if keep is None else int(keep)
    allowance = int(FAMILY_ALLOWANCE)
    out: dict = {}
    for held in by_pair.values():
        # Ranked WITHIN the pair. A tie falls to the key, so the decision is the
        # same on every machine and after any re-sort of the file.
        ordered = sorted(
            held, key=lambda row: (-float(scored.get(str(row["key"])) or -1.0), str(row["key"]))
        )
        for at, row in enumerate(ordered):
            out[str(row["key"])] = RANKED if at < limit else DROPPED
        seated = {name for row in ordered[:limit] for name in _families_of(row)}
        taken = 0
        for row in ordered[limit:]:
            if taken >= allowance:
                break
            missing = [name for name in _families_of(row) if name not in seated]
            if not missing:
                continue
            out[str(row["key"])] = FAMILY
            seated.update(missing)
            taken += 1
    return out


def kept(reason: str) -> bool:
    """Does this reason keep the row, and the picture on it? Everything but
    [`DROPPED`] does — the five protections and [`FAMILY`] included, which is why
    this takes a reason rather than testing against [`RANKED`].

    ⚠ **`== RANKED` and this are different questions since 2026-09-15**, and
    while the rank had one keeping verdict they read the same. A caller asking
    *is this row kept* wants this; one asking *is this row in the top K* wants
    `== RANKED`, and getting the second where it meant the first is a miscount
    and not a crash. Both are live and each is right where it stands:
    `label_migration`'s displacement test and `test_candidate_ledger.pruned_rows`
    ask this, while [`candidate_ledger.prune`]'s `saved_by_a_protection` asks
    `== RANKED` deliberately — a protection is credited with saving a row the
    top K let go, whatever the allowance then did with it, so that a count read
    across months does not move because this rule landed."""
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
        "bound_is": SCHEMA_NOTES["bound_is"],
        "expected": round(expected, 2),
        "expected_is": SCHEMA_NOTES["expected_is"],
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
    "FAMILY",
    "FAMILY_ALLOWANCE",
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
    "free_slot_census",
    "free_slots",
    "keep_per_pair",
    "kept",
    "labeled_renders",
    "pool_stamp",
    "prune_report",
    "render_key_of",
    "repeat_draws",
]
