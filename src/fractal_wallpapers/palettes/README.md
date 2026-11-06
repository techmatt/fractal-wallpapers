Which colors are available: palette assets, palette generation, and palette curation.

```
fractal-wallpapers palettes list
fractal-wallpapers palettes ingest --drop <drop>
fractal-wallpapers palettes provenance --source <archive> --images <pictures>
fractal-wallpapers palettes groups
fractal-wallpapers palettes reference-fields
fractal-wallpapers palettes carriers
fractal-wallpapers palettes produced
fractal-wallpapers palettes color-mass [--only-new]
fractal-wallpapers palettes add data/palettes/<name>.json [--replace]
fractal-wallpapers palettes strip --name "Bone Vault" --out artifacts/figures/bone.png
fractal-wallpapers palettes strip --manifest names.txt --width 1600 --height 120 [--no-mirror]
```

`palettes` is the **library**; `palette` is the head that picks between its maps. Nothing
here loads a model.

**Every record beside the maps is `.jsonl`, never `.json`**: every library reader globs
`data/palettes/*.json` and takes the stem as a map name.

## Getting maps in, and the colour arithmetic

`authored_import` is the only place authored OKLCH control points become a gradient: a
**drop** under `data/palettes/batches/<drop>` is densified to 512 sRGB8 stops in OKLab
through `space`, each provenance row stamped `drop`. `kind` is measured on the gradient
(`CLOSES`), because `mirror = the map is not cyclic` is read off it everywhere;
`tests/test_authored_import.py` re-densifies the authored maps stop for stop.
`library_import` brings a source-project map across; `admit` (`palettes add`) admits
one map to the library, and the `palette admit` command with
`palette_sets.ADMITTED_DROPS` puts a drop in the pool.

`provenance` writes one row per made map to `data/palettes/provenance.jsonl` (an authored
map's brief and OKLCH control points; an extracted map's source image). It reads the
archive's batches and the tracked drops, so a rebuild cannot delete a drop's rows; `merge`
writes a drop without a rebuild. Matching is by name; an unmatched name is reported, never
guessed. Without `--images` a row records its stem and says the extension was not
recovered.

`space` owns the repository's single copy of the sRGB↔Oklab arithmetic. Handed `uint8`,
its sRGB→linear step is a bit-identical 256-entry table. `lightness_and_chroma` is that
arithmetic for a **picture**, split over threads; **the split cannot move a bit** (every
step is elementwise, through `_oklab_of_linear`, the one copy of Ottosson's matrices),
because the tone band an autolevel row projects onto is part of a render's identity.
Threads are a share of the box (`READ_THREAD_CAP`, `READ_POOL_WIDTH`).

`codebook` is the colour vocabulary: **52 swatches** (12 hues × {dark, light} × {muted,
vivid} plus 4 neutrals) in Oklab, and one soft assignment that turns a ramp or picture
into a share vector; [`curation.colors`](../curation/README.md) counts with it. **The
ratified codebook calls them *anchors*; the code calls them *swatches*** (`anchor` is
taken). Chroma is fitted to the sRGB gamut per hue and lightness; where both tiers cannot
be held apart `closest_pairs` says so and those cells are read together. `SIGMA` (0.015)
is pinned by `tests/test_color_codebook.py`. A picture is censused at **160×90**, JPEG's
own scaled decode of both stored sizes, duplicates collapsed first (`distinct`).

## Which map is which choice, and which map can make which colour

`groups` says **which maps are near enough to be one choice**: average linkage over M1, cut
at `0.039735`. The drawable pool collapses through it (one member per group) and the
gallery pass's group cap counts seats per group. The cut's **evidence is tracked**:
`data/palettes/groups_marks.jsonl` holds the pairs Matt marked SAME or DIFFERENT by eye,
and `groups.cut_from_marks()` recomputes the constant under a **one-sided rule**: never
merge a pair marked DIFFERENT. **A map arriving since is admitted, never re-cut**
(`groups.admit`, via `palettes add` or `palettes groups --admit`; `data/palettes/README.md`
has the rule). A full re-cut is Matt's ruling (`tests/test_palette_groups.py` pins it).

**A re-cut is dearer than the pin makes it look**: ids `m01…mNN` are numbered
tightest-first, so a merge shifts every later id that `color_mass` is keyed on. A re-cut
is `palettes groups` **plus** re-deriving `color_mass`.

**Library, candidate pool, drawn set: three counts, never the same number.** The
**library** is every file in `data/palettes` (`groups.library`). The **candidate pool**
is `models.palette_sets.pool()["pool"]`, smaller: `blue_orange` (instrument:
`labeling.sheets.VIVID_COLORMAP` and the tile floor's expansion in `engine/src/tiles.rs`)
and `atlas_grey` are held back, and a map added since is not in it until somebody puts
it there. What a colorize **draws** from is smaller again: `colorize.pool`
reads the pool through `groups.collapse`, one member a group. `colorize.pool_record`
names the group every absent map stood down for.

**The drawn count is seed-independent; which maps is not.** `collapse` draws the standing
member on the seed: Matt's rule, since no member deserves the slot permanently. `groups.canonical` is what a
record *names*, never what the pool draws. `FRACTAL_WALLPAPERS_PALETTE_GROUPS=off` turns
the collapse off for one run (read at call time; a typo falls back to the default).

**Comparing two maps means sampling positions through the bake, never comparing stop
lists**: the library ships stops at several resolutions and the engine bakes every one
into the same 4,096-entry table (`colormap.rs`'s `TABLE_SIZE`). M1 is the sliced
Wasserstein-1 between the maps' hue-weighted, unfolded Oklab clouds read through that
bake; `groups.cloud`, `weighted` and `m1` carry the constants.

`reference-fields` dumps the three pictures every palette sheet is judged on into
`artifacts/palettes/reference_fields/`. `carriers` answers **which map can make which
colour**: every map recoloured onto them (kept under `artifacts/palettes/carriers/`) and
read through `dominance`, one row per (map, cell) in `data/palettes/carriers.jsonl`. `fields` and `mean` are not stored: they
are derived at the read by `carriers.fill` (`STORED` against `DERIVED`), and `write`
re-checks the derivation on every build. Keyed to the **map**, never the group (members
disagree on their dominant cell), and a **prior, not a guarantee**: `curate hunt` draws
from it, then reads dominance on its own render. `co_dominance(cell)` gives the cells a
delivery of one colour also lands, which `curation.ceiling.Rule` raises allowances by.

`produced` answers **which colours a map has made**, off the candidate ledger's recorded
verdicts: one row a map in `data/palettes/palette_family_shares.csv`.

## The ramp bounds the colour, and three things after it leak

A map's ramp gives an **exact upper bound** on a picture's chromatic share of a family:
by the mediant inequality it is at most `max_p A(p,f)/T(p)` over the unfolded bake. The
bound holds of the **lookup**, not of the stored picture: supersampling and JPEG average
colour after the lookup (worst on high-frequency fields, `gaussian_int` and the direct
traps, which `autolevel.applies_to` excludes), and autolevel rewrites the stops. So a
ramp read is a **necessary condition on the map, not a prediction about the
picture**, and none at all for the noisy modes: a ramp that could lead a family delivered
it 23–33% of the time, one that could not 0.1–0.4%.

## `color_mass` — how much of each colour a (group, mode) pair actually makes

The bound says *can*; this says *does*. `data/palettes/color_mass/<mode>.jsonl`, one row
per drawable group, the **mean chromatic share per codebook cell** over every observation
of the pair, with no hole in the grid (`test_palette_color_mass`). Keyed on **(group,
mode)** and nothing finer (the pair carries 75% of the variance), stored **sparse** at
`color_mass.STORED_FLOOR` (0.01), residual `1 - sum(cells)`. Every row counts its two
populations apart (`census`, judged pool rows; `sweep`, a seeded two-location panel),
how many observations autolevel acted on, and how many made no chromatic pixel. The four `NOISY_MODES` are
flagged in each header and kept. `color_mass.UNMEASURED` names the engine mode with no
file (`tail_itinerary`); the completeness guard reads the roster less that tuple.

**A colormap drop opens a hole in the grid and a leg closes it** (`palettes.mass_sweep`):

```
fractal-wallpapers curate mass-sweep extend        render the panel for the maps with no row
fractal-wallpapers palettes color-mass --only-new  cut those pairs in, and only those
```

**`--only-new`, never a rebuild**: the census's per-observation record is not kept, so a
full `build` would drop it. `extend` appends only groups with no row, old rows
byte-identical. The cost a leg sizes on is
[`curation/MEASUREMENTS.md`](../curation/MEASUREMENTS.md)'s *What a `color_mass` close
costs a map* (about 138 s a map over the whole grid); all 18 modes are owed, since the
grid guard holds the map to them.

**`color_mass.delivering(cells, cutoff, within)` is the one reader that turns the map into
a cut** (`curate depth --draw-cells`): maps are expected to put at least `cutoff`
of a picture's colour in any of these cells, mode-conditional mass where the group has a
row and the **carrier prior** where it does not (a fallback, never an overrule), the max
over `mode_policy.accepted()`. `cutoff` unsaid is `dominance.CELL_LEAD`. A draw filter
alone: it writes nothing back. **Resolve the mode roster once** when calling `delivers` in
a loop (`mode_policy.accepted()` re-reads its record each call).

**Eighteen files, one per mode, because of the per-file history guard.**
`test_palette_color_mass.SPLIT_BYTES` (786,432) is a **split threshold, not a cap**: it
fires well before the guard, and the answer to a file outgrowing it is more shards,
never a bigger number or an allowlist entry. A file grows only with the library (one row
per drawable group).

```
fractal-wallpapers palettes color-mass          cut the map from the two measurements
fractal-wallpapers curate mass-sweep save|check|restore
```

The sweep log (`artifacts/curation/palette_mass_sweep/rows.jsonl`, one row per (group,
mode, location) with recipe and cost) is **not tracked and not hot**: a copy under
`<archive>/curation_backup/palette_mass_sweep/`, a tracked manifest at
`data/curation/palette_mass_sweep.manifest.json`. Nothing reads it; it is insurance, and
re-deriving it is 52.1 engine hours. `missing` is normal.

## `variants` — one map, one axis moved

[`variants`] asks *is this map better a quarter-turn round, reversed, or half as
saturated*, and the render path can only be told that through a **new map**: the recipe
key derives through `renders.spec_of`. Every variant is named `<base>~<axis>-<dose>`
(`~` because no tracked map carries one, so `base_of` is total).

⚠ **This module's `phase` is not the engine's `Palette.phase`**: here a phase rolls the
stops into a new map; there it moves where traversal of an unchanged map starts (they
diverge on a folded map). The recipe member per mode is [`curation/MEASUREMENTS.md`](../curation/MEASUREMENTS.md)'s
*What `Palette.phase` moves, by mode*.

Six axes: phase, reversal, repetition, cyclicity, Oklab chroma, Oklab lightness. **Nothing
is resampled**: the positional axes permute and tile the base's stops, so the identity is
the base byte for byte; the Oklab axes land through `autolevel.gamut_fit` and report the
stops the fit moved. `kind` and `mirror` move together through `mirror_for`.

**`write` takes a directory and has no default.** Admitting a variant to `data/palettes/`
takes three rebuilds, in this order:

1. **group it first** (`color_mass` rows are keyed on the group id, so a later re-group
   orphans them silently);
2. **`palettes carriers`** (`test_palette_carriers` pins the header's map count to the
   `data/palettes/*.json` glob);
3. **`curate mass-sweep extend`** then **`palettes color-mass --only-new`**.

Then `palette_sets.ADMITTED_DROPS` and `palette admit`. `palette_group` is *carried, not
keyed* (`recipes.CARRIED`), so a re-group never rebinds a seated row. `groups.group_of`
resolves a variant to its base map's group, read off the name, so the group cap counts
it as its base's look. A cyclicity flip is still zero M1 from its base (`groups.cloud`
discards `kind`).

### What the first sweep of the axis found

**The axis is real and not worth mining**: best-of-12 variants buy about two thirds of
the render judge's gain from drawing twelve other maps at the same clock, and under a
third of `fine_p_ge4`. Every positional axis is negative; **kind splits the baked phase
axis five to one** (sequential against cyclic, the seam `variants.seams` counts). The two
render heads want opposite saturation; **autolevel absorbs the baked lightness axis**, so
sweep it with `FRACTAL_WALLPAPERS_AUTOLEVEL` off or not at all; and in the twin metric a
rotation is far from its base while 1.5x chroma sits at about `ceiling.TAU`.

A variant with no carriers row is constrained (`solve.in_theme`) but un-aimable:
`delivering` and `carriers.draw` give it 0.0.

## `dominance` — what colour a picture is, and `pixel_clouds` — whether two are one picture

`dominance` is one definition read everywhere: the codebook census with the **neutrals
dropped from numerator and denominator**, so shares are of the picture's colour. A cell
is DOMINANT when it leads and holds ≥ 0.10, or holds ≥ 0.15 alone; over the twelve hue
families, 0.20 / 0.30. A picture may be dominant in several cells or none, and there is
no floor under the raw share (deliberate, named in the module). **The family union is
bounded at three by arithmetic** (`floor(1 / FAMILY_ALONE)`), and the measured mean is
1.25: three at once is under a tenth of a percent of the store.

`pixel_clouds` is M1 on 4,096 seeded **pixels** at census size; within
`curation.ceiling.TAU` two pictures are one wallpaper by the gallery's twin test. It does
not substitute for `groups`.

## `strip` — a map's gradient as a picture

`strip` computes no colour: it writes a ramp in the engine's dump format and calls
`recolor`, so the strip gets a wallpaper's bake, table and fold (folded unless cyclic;
`--no-mirror` unfolds). Coloring normalizes against its own 0.5th and
99.5th percentiles, so the outer half percent of a strip is the end colour held flat; no
choice of ramp values avoids that clip (the stretch is affine-invariant), and it cannot
be compensated for in the ramp, but it can be **inverted**: see
[`data/palettes/README.md`](../../../data/palettes/README.md#reading-a-python-side-gradient-against-the-rust-bake).

`strip.draw(..., colormap_dir=...)` (Python only; no CLI flag) draws the ramp a
*particular picture* was rendered through: autolevel writes its overriding stops to
`<run>/release/<stem>.leveled/<colormap>.json`, so point it there with the recipe's own
`mirror`. `data/palettes` gives the shipped map, the wrong one for a levelled picture.

```
fractal-wallpapers recolor --field f.f32 --colormap viridis --out out.png
fractal-wallpapers recolor --field f.f32 --colormap viridis --no-mirror --out flat.png
```
