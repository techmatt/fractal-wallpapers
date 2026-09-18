"""How many seats each collection is solved for, as one table with one owner.

A **collection** is a gallery cut on one axis and solved on its own: one of the
twelve hue families, or one of the seven production modes a collection is kept
for. Nineteen of them, nineteen numbers, and until 2026-09-15 those numbers lived
in whichever prompt was running that night — retyped per prompt, which is how a
target drifts without anybody deciding it had. This module is the one place they
are written, and [`seats_for`] is the one place they are read.

**Changing a target is a one-line edit to [`TARGETS`].** Nothing else moves: the
solve path takes the table's number when `--n` is unsaid, `--n` overrides it, and
a collection the table does not name has no default at all rather than a
plausible-looking one.

## Why a module constant and not a data file

The other three tables of this shape — [`curation.mode_policy`]'s weights,
[`curation.floors`]' cuts, [`curation.solve`]'s mode ceilings — are module
constants carrying their argument at the site, and a target's argument is exactly
the kind that has to be read beside the number. A JSON file would carry nineteen
integers and no reason for any of them, and the reason is the whole of what stops
the next cut being retyped too.

## The general pass is not a collection and has no entry here

**There is no `general` key and there cannot be one.** The general gallery is the
pass with no `--collection` at all — the whole pool, unspliced and unfiltered —
and its size is [`tentative.RECORDED_SEATS`], which is where a prompt that wants
to change it goes. [`kind_of`] refuses any name the codebook and the mode roster
do not between them hold, so a `general` or `general_2000` entry added here would
be accepted by `--collection`'s `choices` and then refused by the very next call,
and [`check`] would fail on it. A second size for the general pool is therefore
`--n`, never a row in this table: `curate solve record --n 2000`.

This is worth saying because the table looks like the place a gallery size lives
and for nineteen of the twenty sizes it is. `solve_n2000_and_sweep_ckpt130` was
told `general: 1000` was here and it never was.

## Two axes, one table, and they are not comparable

A family pass and a mode pass are different measurements — the first runs the
geometry-only distinctness rule on a relaxed bar over a spliced pool, the second
runs the shipped twin test over a single-mode pool with the per-mode floors and
ceilings cleared — so the numbers here are not a ranking. `tia` at 1000 and
`lime` at 150 are two collections solved at those sizes, not a claim that one is
nearly seven times the other's worth. [`kind_of`] is what tells a reader
which pass a name asks for, and it is derived from the codebook and the mode
roster rather than restated, so a hue renamed in one place cannot become a mode
here.
"""

from __future__ import annotations

#: **Collection to seats, and the only place a target is written.**
#:
#: Matt's cut of 2026-09-15, which lowered every one of the sixteen to raise
#: quality: the hue families ran at 500 and the modes at 1000 until then, and the
#: seating that fills a target from the tail is the seating whose median the cut
#: is aimed at. The argument for the three tiers, in the order they were set:
#:
#: * **400 for nine of the twelve families.** The families that filled or nearly
#:   filled 500 — `rose`, `red`, `orange`, `yellow`, `teal`, `azure`, `blue`,
#:   `purple`, `magenta`. A shorter seating drops the worst hundred outright and
#:   reads the themed bar at `4n = 1,600` rather than 2,000, which can only raise
#:   the bar or leave it where it was.
#: * **300 for `green` and `cyan`.** Both seated in the 280-400 range at 500 —
#:   they were filling from the bottom of their own stock, and a target above
#:   what a family can field is a shortfall reported every night rather than a
#:   decision.
#: * **150 for `lime`**, Matt's cut of 2026-09-15, from the 200 set the day
#:   before. The thinnest family in the library: 156 of 500 at the first reading,
#:   on 1,327 scored rows. At `4n = 600` it may now read a bar off its own stock
#:   instead of falling to the floor for want of stock at all.
#:
#:   ⚠ **It is the one target set below what the family currently fields, and
#:   that is known.** The cut was called against 176 of 200, but
#:   `family_slot_sizing_ckpt125` had already moved it to **188 of 200** on the
#:   same day, and the same reading puts `lime` at **242 places above the shipped
#:   fine bar** — a ratio over one, so the 200 was not against a supply wall. A
#:   target under the realized fill binds rather than relaxes: expect 150 of 150
#:   and the `cell_allowance` refusal column to carry what a shorter seating drops,
#:   the way `threads` at 400 does. The seating is the shorter one by decision, not
#:   because the stock ran out.
#: * **1000 for `tia`, 800 for `smooth` and `stripe`, 400 for `threads`.** The
#:   mode collections, cut by what each can field a *place* for: `tia` and
#:   `smooth` fill a thousand, `stripe` was reaching 785-981 and spending its
#:   whole augment budget to do it, and `threads` held 550 above-bar places in
#:   the entire ledger.
#: * **200 for `smooth_mean_angle` and `smooth_stripe`, 100 for `smooth_angle_min`**,
#:   Matt's sizes of 2026-09-17 off `mode_gallery_sizing_ckpt130`'s trial solves:
#:   the largest `n` each fills. Past it the three stop at 244, 198 and 294 seats
#:   however high `n` goes, on `location` and `spiral` rather than on colour, and
#:   the augmenting chains exhaust well inside their budget — the supply is the
#:   wall, not the clock. `smooth_angle_min` read 185 of 200 there, hence 100.
#:
#: **What the nineteen field, measured 2026-09-17** by `add_three_mode_collections_ckpt130`,
#: every one solved by `curate solve run --collection NAME --no-render --no-sheet` on
#: one pool of 449,507 candidates, the twelve families under the DEFAULT floor rule
#: (*A family pass floors at the DEFAULT rule* in `GALLERY.md`). Two quality columns,
#: and **they are two different judges**:
#:
#: * `p_ge4` is the **render judge's** `P(>=4)` on the seat — the gate reading, the
#:   one [`solve.Q4_BAR`] cuts at 0.5, so it can never read under that.
#: * `p_fine` is the **fine head's own column**, `solve.fine_column().read` — the
#:   quality reading from here on, and the column the seating bar is drawn on.
#:
#: ⚠ **This table called `p_ge4` "the seated `p_fine(>=4)` median" until
#: 2026-09-17**, and it was not: `smooth`'s 0.9536 there is its seated `p_ge4`, while
#: the fine head puts the same gallery at 0.27. A median quoted from an older copy of
#: this table, or from `solve_n2000_and_sweep_ckpt130`, is a `p_ge4`. `Δ` is `p_ge4`
#: against that reading of the sixteen, taken the same day over 447,655 candidates:
#:
#: | | seats | `p_ge4` median | Δ | `p_fine` median | `p_fine` q1 |
#: |---|---|---|---|---|---|
#: | `rose` | 400/400 | 0.9485 | −0.0037 | 0.2363 | 0.1173 |
#: | `red` | 400/400 | 0.9557 | −0.0099 | 0.4601 | 0.2970 |
#: | `orange` | 400/400 | 0.9301 | −0.0019 | 0.4662 | 0.2894 |
#: | `yellow` | 400/400 | 0.8880 | −0.0089 | 0.1932 | 0.0627 |
#: | `lime` | 150/150 | 0.8811 | −0.0047 | 0.1315 | 0.0556 |
#: | `green` | 300/300 | 0.8789 | −0.0025 | 0.1733 | 0.0600 |
#: | `teal` | 300/300 | 0.8936 | +0.0092 | 0.2312 | 0.0825 |
#: | `cyan` | 300/300 | 0.9105 | −0.0105 | 0.2093 | 0.0805 |
#: | `azure` | 400/400 | 0.9141 | −0.0021 | 0.1995 | 0.0859 |
#: | `blue` | 400/400 | 0.9427 | −0.0022 | 0.3075 | 0.1573 |
#: | `purple` | 400/400 | 0.9582 | +0.0006 | 0.2288 | 0.0984 |
#: | `magenta` | 400/400 | 0.9380 | −0.0014 | 0.2255 | 0.0889 |
#: | `tia` | 1000/1000 | 0.9174 | −0.0005 | 0.3210 | 0.1556 |
#: | `smooth` | 800/800 | 0.9525 | −0.0011 | 0.2748 | 0.1321 |
#: | `stripe` | 800/800 | 0.9428 | +0.0000 | 0.2985 | 0.1434 |
#: | `threads` | 400/400 | 0.9344 | +0.0002 | 0.3621 | 0.1810 |
#: | `smooth_mean_angle` | 200/200 | 0.8587 | new | 0.3137 | 0.1544 |
#: | `smooth_angle_min` | 100/100 | 0.8789 | new | 0.4284 | 0.2573 |
#: | `smooth_stripe` | 200/200 | 0.9167 | new | 0.2178 | 0.0971 |
#:
#: **All nineteen fill.** The families' `Δ` is the floor rule and not the pool: some
#: 1,850 candidates arrived between the two readings, the four old modes — which
#: floor at 0 either way — held to ±0.0011, and the families moved −0.0032 on the
#: mean, because the default rule re-seats a family toward the thin modes it floors.
#:
#: **The two columns do not rank the collections alike.** `orange` and `red` lead on
#: `p_fine` (0.47, 0.46); `purple` leads on `p_ge4` and is twelfth of nineteen on
#: `p_fine`; `smooth_angle_min` ties for last-but-one on `p_ge4` and is third on `p_fine`.
#: Ranking the nineteen on quality means ranking them on `p_fine`.
#:
#: **Where the augmenting chains still bind**: `magenta` (seed 356, 44 chains,
#: 15.1 s), `yellow` (366, 34), `purple` (372, 28), `smooth_mean_angle` and
#: `smooth_stripe` (177, 23 each), `stripe` (784, 16), `azure` (389, 11). Every
#: other collection is filled by its seed.
#:
#: **`threads` may go backwards at 400 and that is known.** The colour ceiling's
#: allowance is proportional to `n` — about 32 seats a cell at 500 and 26 at 400
#: — and it was already refusing rows on the allowance at 500, so the tighter cap
#: and the shorter seating pull against each other. What settles it is the
#: `cell_allowance` refusal column beside the median, not the fill.
TARGETS: dict[str, int] = {
    # The twelve hue families, in the codebook's own wheel order.
    "rose": 400,
    "red": 400,
    "orange": 400,
    "yellow": 400,
    "lime": 150,
    "green": 300,
    "teal": 300,
    "cyan": 300,
    "azure": 400,
    "blue": 400,
    "purple": 400,
    "magenta": 400,
    # The seven mode collections.
    "tia": 1000,
    "smooth": 800,
    "stripe": 800,
    "threads": 400,
    "smooth_mean_angle": 200,
    "smooth_angle_min": 100,
    "smooth_stripe": 200,
}

#: What [`kind_of`] answers. A family pass and a mode pass are two different
#: measurements over two differently built pools; see the module docstring.
FAMILY = "family"
MODE = "mode"


class TargetRefused(KeyError):
    """A name that is not a collection, or a collection the table does not name."""


def collections() -> tuple[str, ...]:
    """Every collection the table names, in the table's own order."""
    return tuple(TARGETS)


def families() -> tuple[str, ...]:
    """The twelve hue families, in the codebook's wheel order.

    Read off [`palettes.codebook`] rather than off this table's keys, so that a
    family the table forgot is a `check` failure and not a shorter list.
    """
    from fractal_wallpapers.palettes import codebook

    return tuple(name for name, _degrees in codebook.HUES)


def modes() -> tuple[str, ...]:
    """The mode collections the table names, in the table's own order."""
    return tuple(name for name in TARGETS if name not in set(families()))


def kind_of(collection: str) -> str:
    """[`FAMILY`] or [`MODE`], derived and never restated.

    A hue family is one the codebook names; a mode is one
    [`curation.mode_policy`] accepts. A name that is both would be a collision
    between two vocabularies and is refused rather than resolved, because which
    pass it asked for would then depend on the order this function tested them.
    """
    from fractal_wallpapers.curation import mode_policy

    name = str(collection)
    is_family = name in set(families())
    is_mode = name in set(mode_policy.accepted())
    if is_family and is_mode:
        raise TargetRefused(
            f"{name!r} is both a codebook hue family and an accepted production mode, so "
            f"a collection under that name could be either pass. Rename one of them."
        )
    if is_family:
        return FAMILY
    if is_mode:
        return MODE
    raise TargetRefused(
        f"{name!r} is neither a codebook hue family nor an accepted production mode, so "
        f"it names no collection. The twelve families are {', '.join(families())}; the "
        f"mode collections this table carries are {', '.join(modes())}."
    )


def seats_for(collection: str, default: int | None = None) -> int:
    """**How many seats this collection is solved for.** The one read of the table.

    `default` is what an unnamed collection takes. Unsaid there is no default and
    the lookup refuses: a solve that silently seated a plausible number for a
    collection nobody had set a target for is exactly the drift this table was
    written to end, and a caller that genuinely wants a fallback says so.
    """
    name = str(collection)
    # The vocabulary check first, so a misspelt family is refused as a misspelling
    # rather than reported as a collection with no target.
    kind_of(name)
    if name in TARGETS:
        return int(TARGETS[name])
    if default is not None:
        return int(default)
    raise TargetRefused(
        f"{name!r} is a {kind_of(name)} and the target table does not name it, so this "
        f"pass has no size. Give --n, or add it to `curation.targets.TARGETS`."
    )


def cells_of(family: str) -> tuple[str, ...]:
    """The four codebook cells of one hue family, sorted."""
    from fractal_wallpapers.palettes import dominance

    if kind_of(family) != FAMILY:
        raise TargetRefused(f"{family!r} is a mode collection and has no codebook cells.")
    return tuple(sorted(cell for cell in dominance.cells() if dominance.family_of(cell) == family))


def pool_for(candidates, collection: str) -> tuple[list, int]:
    """`(the pool this collection is solved over, how many rows it holds)`.

    **A family is spliced and a mode is filtered**, and the asymmetry is the two
    axes, not an accident.

    A *mode* collection is a subset: `solve.Candidate.mode` already carries
    [`curation.mode_policy.routed_mode_of`], so the pass is the general pass over
    the rows in that mode and nothing about the solver changes.

    A *family* is not a subset of anything the solver can see. `--themed` is
    CELL-granular — `solve.in_theme` asks `cell in candidate.cells` over the 48 —
    and a hue family is a different axis of the same reading, carried on every
    ledger row's colour block as `families` at
    [`palettes.dominance`]'s FAMILY_LEAD / FAMILY_ALONE and onto
    `solve.Candidate.families`. No flag reaches it, so the family name is
    **appended to `cells`** on every row the store already calls dominant in it
    and the pass is then an ordinary themed pass on a cell spelled `lime`. Every
    reader agrees — `in_theme`, `themed_fine_bar`, the off-theme marking — and the
    per-seat `cell` is `cells[0]`, the real cell, untouched. The visible cost is
    one synthetic row in the record's cell table, named for the family and equal
    to the seat count, spelled without a tone or a chroma so a reader can tell it
    from the 48.
    """
    from dataclasses import replace

    name = str(collection)
    if kind_of(name) == MODE:
        held = [candidate for candidate in candidates if candidate.mode == name]
        return held, len(held)
    out = []
    held = 0
    for candidate in candidates:
        if name in candidate.families:
            out.append(replace(candidate, cells=(*tuple(candidate.cells), name)))
            held += 1
        else:
            out.append(candidate)
    return out, held


def rule_for(family: str):
    """The colour ceiling a **family** pass runs under: the allowance, no demand.

    `--themed CELL` sets `--target CELL=1.0`, and that flag does two jobs at once.
    It raises the cell's allowance out of the way — `floor(k * t * n) + 1` at the
    uniform 1/48 is 26 seats of 400, which would refuse the theme at seat 27 —
    *and* it states a demand. For one cell the demand is free, because every row
    in the pass is in the cell. For a family it is not: the pool spreads over four
    cells, and four quarter-demands would seed the pass scarcest-cell-first and
    report a shortfall against a distribution nobody asked for.

    So the two jobs are separated. The rule is built with all four of the family's
    cells at 1.0 — raising those four, their measured co-dominance companions and
    the family itself, exactly as the shipped themed path raises one cell's — and
    then the targets are emptied, so `demands_for` carries the mode floors and no
    colour demand at all. The allowance is taken; the demand is not.
    """
    from fractal_wallpapers.curation import ceiling

    rule = ceiling.Rule(targets={cell: 1.0 for cell in cells_of(family)})
    rule.targets = {}
    return rule


def check() -> dict:
    """Every key is a collection and every family has a target. The guard's body.

    Two failures it exists to catch, and the second is the one that would go
    unnoticed: a key that is neither a family nor a mode is a typo the solve path
    would report as *no target for this collection*, and a family missing from the
    table is a family whose nightly solve would refuse for want of a size.
    """
    bad = []
    for name in TARGETS:
        try:
            kind_of(name)
        except TargetRefused as refusal:
            bad.append(str(refusal))
    missing = [name for name in families() if name not in TARGETS]
    if missing:
        bad.append(f"no target for the hue famil{'y' if len(missing) == 1 else 'ies'} {missing}")
    nonsense = [name for name, seats in TARGETS.items() if int(seats) < 1]
    if nonsense:
        bad.append(f"a target below one seat: {nonsense}")
    return {"collections": len(TARGETS), "refusals": bad}
