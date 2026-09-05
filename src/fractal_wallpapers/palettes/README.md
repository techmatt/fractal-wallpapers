Which colors are available: palette assets, palette generation, and palette curation.

```
fractal-wallpapers palettes ingest --drop rare-colors-2026-08
fractal-wallpapers palettes provenance --source <archive> --images <pictures>
fractal-wallpapers palettes groups
fractal-wallpapers palettes reference-fields
fractal-wallpapers palettes carriers
fractal-wallpapers palettes strip --name "Bone Vault" --out artifacts/figures/bone.png
fractal-wallpapers palettes strip --manifest names.txt --width 1600 --height 120
```

`palettes` (plural) is the **library**; `palette` (singular) is the head that picks
between its maps. Nothing in this package loads a model.

`authored_import` is the other way in, and the only place authored OKLCH control
points become a gradient: a **drop** of generator batch files under
`data/palettes/batches/<drop>` is densified to 512 evenly spaced sRGB8 stops,
interpolated in OKLab through `space`, and every provenance row it writes carries
the drop's directory name as its `drop` stamp. `kind` is measured on the gradient
— the control points must close within `CLOSES`, and the dense table has to close
exactly — because `mirror = the map is not cyclic` is read off it everywhere and a
misclassification is silent in both directions. The claim that this is the
archive's densifier rather than a second one is a test, not a comment:
`tests/test_authored_import.py` re-densifies all 175 pre-drop authored maps from
the stops their provenance rows carry and requires the tracked files back stop for
stop.

`library_import` brings a map across from the source project's pooled library and
writes it here as stops. `space` measures how near two maps are — the gradient as
the renderer really spends it, sampled and converted to Oklab — which is what lets
the palette head's corpus build candidate sets that are near-ties by construction
rather than by luck.

`space` also owns the repository's single copy of the sRGB↔Oklab arithmetic, so the
autolevel operator and the palette descriptor cannot come to disagree about what a
colour is. Its sRGB→linear step is a 256-entry table rather than the transfer curve's
`**2.4`, taken whenever the caller hands over `uint8` — the whole of sRGB8 and
nothing else, so the table is that expression's own answer bit for bit. Hand it a
picture as it was decoded and a tone measurement runs about 30% faster; hand it
fractional values, as a gradient sampled between its stops gives, and it does the
arithmetic.

`lightness_and_chroma` is that arithmetic for a **picture**, and it exists because
a whole render is where the conversion stops being free: on a 640x360 candidate
`oklab` is 52 ms, and 31 ms of it is three `numpy.cbrt` calls run one element at a
time. It hands back the two channels a tone reading actually wants instead of an
array of three to slice, and splits the pixels over threads — a numpy ufunc drops
the GIL, so the cube roots are what a thread can carry away. **The split cannot
move a bit**: every step from a pixel's three bytes to its two numbers is
elementwise (`_oklab_of_linear`, the one copy of Ottosson's matrices, which
`oklab` is now a stack on top of), so a chunk read on its own thread is the bytes
one pass would have produced. That matters more than speed here — the tone band an
autolevel row projects onto is part of that render's identity, and a reading that
were merely close would rename every cached candidate. The thread count is a share
of the machine rather than the whole of it, because a build pass runs three worker
processes beside it (`READ_THREAD_CAP`, `READ_POOL_WIDTH`).

`codebook` is the colour vocabulary: **52 swatches** — 12 hues × {dark, light} ×
{muted, vivid} plus 4 neutrals — as points in Oklab, and one soft assignment that
turns any ramp or picture into a share vector over them. It is what
[`curation.colors`](../curation/README.md) counts with, and it holds no cut of any
kind. Two facts a reader needs before trusting a cell of it:

* **The ratified codebook calls these *anchors*; the code calls them *swatches*.**
  `anchor` already names the map a hard candidate set is built around — and it is
  spelled `anchor` on the very pool rows a census reads — plus a smoke-test
  location in `data/anchors.jsonl` and a `deep` center. The translation is stated
  in the module and in the persisted document's `note`.
* **A swatch's chroma is fitted to the sRGB gamut, per hue and lightness.** A fixed
  vivid chroma of 0.16 puts seven of the twelve dark-vivid swatches outside sRGB —
  dark green among them — and a census through those buckets would report the
  library's ~40 dark-green maps as absent. Where the gamut is too tight to hold
  both tiers apart (dark cyan, teal and yellow) the two land inside the
  assignment's own resolution; `closest_pairs` reports it and those cells are read
  together.

`SIGMA` is 0.015, fixed by measurement against three checks declared before the
sweep and pinned by `tests/test_color_codebook.py`: a pure swatch dominates its own
cell 52/52, a neutral grey keeps ≥0.99 of its mass on the neutrals at every
lightness, and the median pure-swatch self-share is 0.81. The middle one is not
decoration — an earlier codebook with the neutrals between the tone levels sent a
pure mid-grey to dark muted cyan, which would have made every achromatic wallpaper
donate a quarter of its mass to cyan and teal.

A picture is censused at **160×90**, which is exactly what JPEG's own scaled decode
gives for both stored sizes — the 640×360 candidate render at ¼ and the 1280×720
label crop at ⅛ — so nothing is resampled between the stored pixels and the count.
Duplicate colours are collapsed before assignment (`distinct`), which is the same
arithmetic to 6e-15 and about three times faster.

## Which map is which choice, and which map can make which colour

Four records sit beside the library and none of them is a colormap. All four are
`.jsonl` for the reason above — a `.json` in `data/palettes/` is read as a map, and
the fourth is a whole subdirectory of them, where that glob cannot reach it at all.

`groups` says **which maps are near enough to be one choice**: average linkage over
M1, the sliced Wasserstein-1 distance between two maps' hue-weighted Oklab clouds
read through the engine's own bake, cut at `0.039735`. 901 maps, 65 groups, 143
maps in one. The drawable pool collapses through it — one member per group, drawn
on the run's seed — and the gallery pass's group cap counts seats per group.

The cut's **evidence is tracked beside it**: `data/palettes/groups_marks.jsonl`
holds the forty-six pairs Matt marked SAME or DIFFERENT by eye on 2026-08-25, and
`groups.cut_from_marks()` recomputes the committed constant from them. The marks
do not sort cleanly — two pairs marked SAME sit above the nearest pair marked
DIFFERENT — so the cut is read by a **one-sided rule**: never merge a pair marked
DIFFERENT, and pay for it by declining two merges a person would have made. Both
are named in the record's header, and `groups.jsonl`'s `marks` field points at it.

**Library, candidate pool, drawn set — three counts, and none of them is the same
number.** The **library** is every file in `data/palettes`: **901** maps
(`groups.library`). The **candidate pool** is
`models.palette_sets.pool()["pool"]`, **900** — 700 maps inherited as a *subset* of
the source project's own 987-map pool (nothing was brought across to round the
number up) plus the 200 of the one admitted drop. The one library map it does not
hold is `blue_orange`, which is instrument rather than choice: it is
`labeling.sheets.VIVID_COLORMAP`, the map a person judges a location from, and half
of the tile floor's palette expansion in `engine/src/tiles.rs`. What a colorize actually **draws** from is **822**, because
`colorize.pool` reads that 900 through `groups.collapse`: 143 of them fall in 65
groups, each group stands one member up and 78 stand down, leaving `757 singletons +
65 = 822`. The record `colorize.pool_record` writes on every run carries all of it,
and names the group every absent map stood down for.

**The 822 is seed-independent; which 822 is not.** `collapse` draws the standing
member with `random.Random(seed).randrange` inside each group, so a different
`--seed` stands a different member up and never a different *number* of them — two
seeds a day apart shared 790 of 822 maps. That is Matt's rule and the reason is what
a group means: its members are indistinguishable, so none of them deserves the slot
permanently, and always taking `groups.canonical` would quietly retire every other
member of every group while leaving it in the library. `canonical` is what a record
or a figure *names*; it is deliberately not what the pool draws.
`FRACTAL_WALLPAPERS_PALETTE_GROUPS=off` turns the collapse off for one run, read at
call time so a typo falls back to the default rather than silently widening a pool.

**Comparing two maps means sampling positions through the bake, never comparing stop
lists.** `data/palettes` ships control points at four different resolutions — 33
stops for 156 maps, 34 for 36, 257 for 334, 512 for 375 — and the engine bakes every
one of them into the same 4,096-entry table (`colormap.rs`'s `TABLE_SIZE`), so two
maps compared stop for stop are two different samplings of one curve. `groups.cloud`
therefore reads a map at `SAMPLES` (4,096) evenly spaced **unfolded** positions with
`numpy.interp` over the sorted stops in Oklab, holding the end colours outside the
outermost stops exactly as `colormap.rs`'s `interpolate` does above and below them —
and stops one step short of the engine, which ends in `oklab_to_linear_srgb`, because
coming back out of Oklab to measure a distance in it would be a round trip through a
clip. `weighted` then scales `a` and `b` by `HUE_WEIGHT` (4.0) and `m1` projects the
clouds onto `DIRECTIONS` (1,024) directions of a Fibonacci **half**-sphere — half
because the 1-D distance along a direction and along its opposite are one number —
reading each projection at `QUANTILES` (128) evenly spaced quantiles. That is the
whole of M1, and it is chunked over directions rather than over maps so the pass
stays inside a gigabyte. Unfolded on purpose: folding never adds colour, so the
unfolded read is the right superset of every mirrored one.

`reference-fields` dumps the three pictures every palette sheet is judged on —
one smooth, one the ramp sweeps across several times, one a parameter plane — from
tracked specs into `artifacts/palettes/reference_fields/`. The spec is twelve
numbers and is in the history; the field is a megabyte of floats and is not.

`carriers` answers **which map can make a picture of which colour**: every map in
the library recoloured onto those three fields and read through `dominance`, one
row per (map, cell) with the cell's share on all three fields and their mean.
About 90 seconds for 2,703 recolours, which land under
`artifacts/palettes/carriers/` and are kept, so a second run is the census alone.
3,220 rows over 901 maps, and every one of the 48 chromatic cells has a carrier.

It is keyed to the **map** and never to the palette group, and that is measured
rather than preferred: members of one group disagree on their dominant cell in 120
of 195 (group, field) reads and 96 of those cross a hue family. `twilight` and
`twilight_shifted` are one group and read `light_muted_azure` and
`dark_vivid_purple` on the same field, because M1 is order-free over a ramp's
cloud while dominance is area-weighted over a picture.

It is also a **prior and not a guarantee**. Only 4 of the green carriers and 3 of
the rose ones dominate on all three fields; green collapses on the `strange` field,
which is the class that held 90 of gallery3's 150 seats. So `curate hunt`'s
conditioned leg draws its maps from this table and then reads each candidate's
dominance **on its own render**.

`co_dominance(cell)` reads the same rows the other way round. A **delivery** is one
(map, field) picture, and the dominance rule admits more than one cell per picture,
so a delivery of one colour is usually a delivery of several: `dark_vivid_lime`
lands `dark_muted_lime` 42% of the time, `light_muted_lime` 34%, `light_vivid_lime`
18% and `dark_vivid_green` 8%, at 2.29 cells a delivery. That is what
`curation.ceiling.Rule` raises a target's *implied* allowances by, and the reason it
is read here rather than written down off the hue wheel: the wheel would say lime
borders green and yellow, and the library says lime's carriers land three other lime
cells before they land anything green. Denominated in deliveries and not in maps — a
map that carries the cell on all three fields is three chances to land a companion.

## The ramp bounds the colour, and three things after it leak

A map's ramp gives an **exact upper bound** on what a picture through it can be: a
picture's chromatic share of a family is `sum_p w_p A(p,f) / sum_p w_p T(p)` over the
unfolded bake's positions, and by the mediant inequality that is at most
`max_p A(p,f)/T(p)`, attained by a picture spending the whole ramp at one place. Folding
never adds colour, so the unfolded read is the right superset.

The bound holds of the **lookup** and not of the **picture this repository stores**, and
the difference is large enough to matter to anything reading colour off a render:

* **Supersampling and JPEG average colour after the lookup.** A high-frequency field —
  `gaussian_int`, and the direct traps above all — puts very different ramp positions in
  neighbouring subsamples, and their mean is a colour the ramp does not hold. Measured:
  `meloni` under `gaussian_int` reads red `0.458` against a ramp bound of `0.010`; the
  same recipe at one sample per pixel written as PNG reads `0.000`, exactly on the bound.
  `ss2` alone accounts for `0.222` of the gap and the JPEG for the rest.
* **Autolevel rewrites the stops**, so a levelled render is a lookup into a *different*
  map from the one that was screened. `within-25` under `smooth` reads teal `0.002`
  unlevelled and `0.266` levelled.
* The direct traps are the worst offenders and `autolevel.applies_to` excludes their kind,
  which is what isolates averaging rather than levelling as the dominant leak.

So a ramp read is a **necessary condition on the map, not a prediction about the picture**,
and it is not one at all for the noisy modes. Over 13,020 (group, mode) pairs rendered
directly, a ramp that could lead a hue family delivered it **23-33% of the time**, and a
ramp that could not delivered it in 0.1-0.4% — the bound is nearly one-sided, and loose.

That sweep is what says the library's colour is not the palette head's: the head's own
evidence had 5 (group, mode) pairs leading green and 10 leading teal, and rendering the
pairs it never chose found 1,705 and 1,563.

## `color_mass` — how much of each colour a (group, mode) pair actually makes

The bound above says *can*. This says *does*, and it is tracked:
`data/palettes/color_mass/<mode>.jsonl`, one row per palette group, the **mean chromatic
share per codebook cell** over every observation of that pair. All **14,796** pairs —
822 groups by the 18 modes it was measured on — with no hole in that grid. The engine
ships **19** production modes; `color_mass.UNMEASURED` names the one with no file
(`tail_itinerary`, catalogued after the sweep) and the completeness guard reads the
engine's roster *less* that tuple, so a mode added later is a named hole rather than a
red test. Measuring one costs a sweep leg, which is why the hole is declared instead.

```
fractal-wallpapers palettes color-mass          cut the map from the two measurements
fractal-wallpapers curate mass-sweep save       copy the sweep log to the archive tier
fractal-wallpapers curate mass-sweep restore    bring it back to cut the map again
```

Two measurements are unioned and **counted apart on every row**, because they are two
populations: `census` is 15,681 judged pool rows, which is where the palette head chose
to go and covers 5,075 pairs; `sweep` is 27,053 renders over a seeded two-location panel,
which covers the grid the head never visited. A reader weighting a pair by how much
production evidence stands behind it needs the split.

Keyed on **(group, mode)** and nothing finer, off a variance decomposition rather than a
preference: the pair term carries 75.0% of the variation in the 48-cell vector, the
partition within a pair 8.0%, the location-and-render residual 17.1%. Stored **sparse** at
`color_mass.STORED_FLOOR = 0.01` — a cell under one percent of the colour can neither lead
a cell nor carry a family — so a row holds about nine cells and the residual is
`1 - sum(cells)`. Every row also carries how many of its observations autolevel **acted**
on, because a mean whose evidence is all levelled is a different prediction, and how many
made no chromatic pixel at all (1,793 of 42,734 did, and they are in the denominator).

**`color_mass.delivering(cells, cutoff, within)` is the one reader that turns the map into
a cut**, and it is what `curate depth --draw-cells` narrows its palette pool with. It
answers *which maps are expected to put at least `cutoff` of a picture's colour in any of
these cells*, taking **mode-conditional mass where there is a row for the map's group and
the carrier prior where there is not** — the two tables answer the same question at
different keys, and only one of them is a measurement of this pipeline, so the prior is a
fallback and never an overrule. The **max** over `mode_policy.accepted()` and not the mean,
because a run's map pool is shared by every arm and every mode in it. `cutoff` unsaid is
`dominance.CELL_LEAD`, so the default reads as *expected to be dominant here*; the thinnest
cell in this library runs out of `colorize.CANDIDATES` between 0.10 and 0.15, which is what
makes 0.10 the loosest value that is still a bound. It is a **draw filter and nothing
else**: it re-marks no map, folds none and writes nothing back to the tracked records.

**Resolve the mode roster once when calling `delivers` in a loop.** `mode_policy.accepted()`
re-reads its record at about 13 ms a call, which is nothing once and **54 seconds** over the
4,110 (map, cell) pairs a five-cell cut of the pool asks — the shape `delivering` had before
it hoisted the call, and the same trap for any other caller.

The four `NOISY_MODES` — `gaussian_int`, `direct_trap_multiply`, `_ring`, `_screen` — are
**flagged in each file's header and kept**. Their pictures are not lookups into their own
maps, so the ramp bound does not apply to them; what they read is still what the pipeline
really produces, which is what a ceiling acts on.

**Eighteen files, one per mode, and that is the guard talking.** The whole map is 6.80 MB
against `test_history_purity`'s 1 MiB per-file cap, so it splits the way the tracked
release store splits on partition. Largest file 415 KiB.

The sweep log it was cut from — `artifacts/curation/palette_mass_sweep/rows.jsonl`, one row
per (group, mode, location) with the recipe and the cost, 25.7 MB — is **not tracked and
not hot**. It gets the `curation.durability` treatment the supply sidecar gets: a copy
under `<archive>/curation_backup/palette_mass_sweep/`, a tracked manifest at
`data/curation/palette_mass_sweep.manifest.json`, and `curate mass-sweep save|check|restore`.
It is insurance and nothing reads it: re-deriving it is 8.7 h over pictures that were
censused and deleted, and it is the only thing that would let the map be re-cut on other
terms — excluding the noisy modes, weighting the panel differently, rolling to families.
`check` reporting `missing` is its **resting state**, not an alarm; `durables.guard`
refuses over the supply sidecar and nothing else.

## `dominance` — what colour a picture is, and `pixel_clouds` — whether two are one picture

`dominance` is one definition read everywhere: the codebook's 52-cell census with
the **neutrals dropped from the numerator and the denominator**, so the shares are
of the picture's colour rather than of its pixels. A cell is DOMINANT when it leads
and holds ≥ 0.10, or holds ≥ 0.15 on its own; the same rule over the twelve hue
families at 0.20 / 0.30. A picture may be dominant in more than one cell and in
none. There is no floor under the raw share — mean neutral share over gallery3's
150 is 0.210 — which is deliberate and named in the module.

`pixel_clouds` is the palette metric on **pixels**: the same M1 `groups` uses,
over 4,096 seeded pixels of a render at census size instead of over a ramp. Two
pictures at distance 0.034281 are the same wallpaper by the gallery pass's twin test
(0.0586 until the 2026-09-02 ruling, 0.03809 until the 2026-09-05 one; see
`curation.ceiling.TAU`).
The two instruments do not substitute for each other — same-group pairs in
gallery3 run 0.0121 to 0.4111, a 34× range whose median sits *above* the median
nearest-neighbour distance of the gallery at large.

`provenance` recovers how the *made* maps were made and writes one row per map to
`data/palettes/provenance.jsonl`. It reads two sources of authored briefs — the
archive's batches and the tracked drops — so a rebuild cannot silently delete the
rows a drop put there; and `merge` is how a drop writes without a rebuild, because
the pictures the extracted maps were read from are not in the archive and a full
rebuild would replace each `image` with a bare stem. A row it writes carries: an authored map's mood family, generator
version, colour architecture, lightness skeleton, value key, complexity and its
author's own OKLCH control points; an extracted map's source image file and
nothing else. Matching is by name and an unmatched name on either side is
reported, never guessed at. The `--source` archive is the read-only source
project; `--images` is the directory of pictures the extracted maps were read
from, and without it a row records the stem it carries and says the extension was
not recovered.

Every record written beside the maps is `.jsonl` rather than `.json` **because
every reader of the library globs `data/palettes/*.json` and takes the stem as a
map name** — a record written as `.json` would be read as a colormap with no stops.

`strip` draws one map's gradient as a picture. It computes no colour: it writes a
horizontal ramp in the engine's own dump format and calls `recolor`, so the strip
comes out of the same OKLab bake, the same 4096-entry table and the same fold a
wallpaper gets. Interpolating stops in Python would be a second densifier, and the
day the two disagreed the article would be illustrating a gradient nothing
renders. The fold defaults to the pipeline's rule — folded unless the map is
cyclic — and `--no-mirror` asks for the unfolded ramp. The coloring stage
normalizes against its own 0.5th and 99.5th percentiles, so the outer half percent
of a strip's width is the end colour held flat; that is the same clip every render
gets and it cannot be *avoided*, because the stretch is affine-invariant and no
choice of ramp values dodges it. It can be **inverted**, which is a different
question: the stretch is nearest-rank over known sample positions, so which
gradient position each pixel shows is exact arithmetic — see
[`data/palettes/README.md`](../../../data/palettes/README.md#reading-a-python-side-gradient-against-the-rust-bake)
for the 4096-wide recipe and the index it turns on.

`--colormap-dir` (`strip.draw(..., colormap_dir=...)`) is what draws the ramp a
*particular picture* was rendered through rather than the map as shipped. When the
autolevel operator acts it writes its overriding stops to
`<run>/release/<stem>.leveled/<colormap>.json`, one directory beside the picture;
pointing `strip` at that directory and passing the recipe's own `mirror` gives the
gradient as applied. Pointing it at `data/palettes` instead gives a different
gradient, and on a levelled picture that is the wrong one.

The same wiring reaches `recolor`, which used to send no palette block at all and
therefore baked every sequential map through its seam:

```
fractal-wallpapers recolor --field f.f32 --colormap viridis --out out.png
fractal-wallpapers recolor --field f.f32 --colormap viridis --no-mirror --out flat.png
```
