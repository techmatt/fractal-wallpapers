Colormaps, one JSON file per map, named for the map it holds.

Each file carries a `schema`, the map's `name` (which must match the filename),
its `kind` — `cyclic` if the last color returns to the first, `sequential`
otherwise — a one-line `source`, and the `stops`: `[position, [r, g, b]]` pairs
in sRGB8, in order, spanning `0.0` to `1.0`. The engine interpolates them in
OKLab, so the stops are control points rather than samples of a final gradient;
a dozen well-placed ones make a better map than a hundred evenly spaced ones.
`tests/test_colormaps.py` holds these files to that shape. Most were not curated:
they arrived by mechanical conversion because a labeled row or a vendored candidate
set names them, and their `source` line says so.

`kind` is load-bearing the moment a coloring repeats the gradient across a field: a
sequential map's ends slam together at every wrap. **Folding** (baking the map as an
out-and-back) is the fix; it is refused on a cyclic map, and never applied on a map's
behalf, because it halves how much gradient one pass shows. It is the render recipe's
`mirror`, and only a caller that sets it gets it. So `blue_orange` (the tile floor's
second reservation and the labeler's vivid render) is drawn **fold-free** there, while a
deploy-geometry view of the same map would be folded. A row naming a map says nothing
about which gradient it got; its recipe does.

**Nothing in production draws a palette knob.** `cycles`, `phase`, `gamma` and
`reverse` are the engine's; every colorize is `finished.recipe()` at the identity with
`mirror` read off the map's cyclicity. The one leg that draws one is `curate manufacture
--step knobs` (`manufacture.KNOB_GRID`), a **diagnostic** over cyclic maps only that
re-colours attempts which missed their target swatch and ships nothing. No targeted seat
and no recolor path draws a knob (`palettes strip` and `recolor` take the fold alone), so
a hit rate measured anywhere here is a fact about where a pinned ramp lands on a field.

## The densifier is the engine's bake, and this directory ships only its input

A file is control points; turning them into colors is `engine/src/colormap.rs` and
nowhere else: converted to **OKLab**, interpolated there, and baked once into a
**4096-entry table of linear-light RGB** (perceptual because linear-RGB interpolation is
visually lumpy; a table because a render only ever takes 4096 distinct values).

* **A lookup is clamped, not wrapped**: `t` outside `[0, 1]` returns the end color. The
  recipe's `cycles` and `phase` are where a caller says otherwise.
* **Folding happens at bake time**, to the stops before conversion, so a folded map is a
  different table.

So **this repository ships dense sRGB8 and nothing else**: no OKLCH source, no generator
state, no baked table. **4096 is the table's width and never a file's**: files ship at a
few stop counts (512 is what `authored_import` densifies a brief to; the rest are their
source's resolution), and a 4096-stop file would be a baked table checked in.

### Reading a Python-side gradient against the Rust bake

The check that the two agree is a strip at the table's own width:

```python
strip.draw(name, out, 4096, 1, mirror=False)
```

One pixel per table entry, unfolded. But **the coloring stage stretches every field
against its own 0.5th and 99.5th percentiles**, a ramp included. The stretch is
nearest-rank (`coloring.rs::percentile`, `CLIP_LOW` / `CLIP_HIGH`), so over 4096 samples
`low` is sample `round(0.005 × 4095) = 20`, `high` is `round(0.995 × 4095) = 4075`, and
pixel `i` shows the map at

```text
t = clamp((i - 20) / 4055, 0, 1)
```

Undo that and the strip reads the bake. Samples 0–20 are all `t = 0` and 4075–4095 all
`t = 1`: the ends are held flat, duplicated rather than lost, which is why the stretch is
invertible though not avoidable (flat runs read a few pixels longer on `viridis`; that is
sRGB8 quantization, not a wider clip). This does not contradict
[`palettes/README.md`](../../src/fractal_wallpapers/palettes/README.md)'s "cannot be
compensated for": that is about *avoiding* the clip (the stretch is affine-invariant);
the *mapping* is recoverable.

## Which maps are the same choice: `groups.jsonl`

`groups.jsonl` says which maps are near enough that picking between them is picking
nothing. The metric is M1, the sliced Wasserstein-1 distance between two maps' 4096-position
**unfolded** Oklab clouds read through the bake, `a` and `b` scaled by 4. Average linkage,
cut at **0.039735**, the midpoint between the widest pair marked SAME and the nearest
marked DIFFERENT on Matt's calibration sheet (`groups_marks.jsonl`). Every merge was
reviewed one at a time.

**The pool collapses through it at read time.** `curation.colorize.pool` keeps one member
per group, **drawn on the run's seed, not the canonical member**, because the members are
indistinguishable and none deserves the slot permanently. Nothing is deleted from this
directory, and the run record's `config.palette_pool` names the group every absent map
stood down for. `FRACTAL_WALLPAPERS_PALETTE_GROUPS=off` turns it off for one run. A
group's `canonical` member (the one with the most finished-render label rows) is what a
record or figure *names*.

**The three counts, and none of them is the same number.** The **library** is every file
in this directory. The **candidate pool** is `../palette_choice/pool.json`, smaller:
`blue_orange` (kept for the tile floor and the labeler's vivid render) and `atlas_grey`
(the plate ramp `curate atlas` draws through) are held back, and an ingested or added map
is not in it until somebody puts it there. `atlas_grey` is dominant in no cell, so
`carriers.jsonl` names it in an `uncarried` row, and a reader grouping the library by
colour (the website's library page) skips those maps. What a colorize **draws** from is
smaller again, one member a group. That count is seed-independent: a different `--seed`
stands a different member up, never a different number of them.

**A map arriving after the cut is admitted, never re-cut** (Matt's ruling): it joins the
nearest existing group when its mean M1 to that group's members is within the cut, else
starts its own, as one appended `admitted` row, so no group id the cut made moves and
nothing keyed on one (`color_mass`, a recipe's `palette_group`) shifts. A pre-cut
singleton a newcomer joins keeps its own id, `map:<name>`. `palettes add` admits the map
it adds; `palettes groups --admit <list>` admits a backlog in order. `groups.coverage()`
says every library map is either cut over or admitted. **Rerunning `palettes groups`
without `--admit` is a full re-cut and drops the admissions**: Matt's call, not a
refresh. A re-cut takes about five minutes, growing with the square of the library, and
reproduces the shipped file exactly.

## What a palette sheet is judged on: `reference_fields.jsonl`

Three fields are pinned, one coloured once, one the ramp sweeps across several times,
one a parameter plane: each the released `gallery3` location with the highest 64-bin
gradient entropy in its class, in three different modes. **The spec is tracked and the
dump is not**: a `.f32` field is a megabyte of floats, which
`fractal-wallpapers palettes reference-fields` remakes into
`artifacts/palettes/reference_fields/` from the twelve numbers in the record.

## A hue family is twelve 30° spokes, and a spoke is never a category

`codebook.rollup` folds the 52 swatches onto the twelve `HUES` spokes plus `neutral`, the
only colour *family* level here. A hue band drifting across a spoke midpoint reads as a
family flip when nothing flipped (pinks at 335–340° and 340–348° come out `rose` and
`magenta`), and about half the library sits on at least one soft edge. So a rollup is a
*reading*, and anything treating a family as a category needs a wheel-aware term, not a
per-family difference (a `|Δp|` family-presence gate over M1 was rejected).

## A sheet's JPEG settings are part of its recipe

A comparison sheet is an instrument and its encoder is one of its settings: record the
quality and chroma subsampling beside the pictures (the groups sheet was quality 70,
4:2:0). A re-render at another quality is a second instrument, not a refresh.

## The ramp as it was actually applied

On a **levelled** picture the render did not spend the tracked map: the autolevel operator
writes the map it used, under the map's own name, into `<run>/release/<stem>.leveled/`, so

```
strip.draw(name, out, colormap_dir=Path(run) / "release" / f"{stem}.leveled")
```

draws the ramp **as applied to that picture**; without the directory, the library's. The
two differ wherever the operator acted, which is most maps on the reference fields.

## Which maps a random pick may draw: `palettes_for_random_choice.csv`

**The maps that seated more than one wallpaper in the published n=1000 general gallery**,
as `palette name,count`. The website is the reader: a random pick wants maps the seating
has proven twice. A gallery row carries no colormap, so the derivation joins
`<stamp>/gallery.jsonl` on `key` to `<stamp>/recipes.jsonl` and counts
`recipe.colormap`. **It is a reading of one record, not a standing rule**: a later
publication re-derives it, and the count column lets a reader re-filter.

## Which colours a map has actually made: `palette_family_shares.csv`

`carriers.jsonl` says what a map **can** carry (three pinned reference fields); this says
what it **has** made, off the candidate ledger. One row per library map, `palette
name,pictures,` then the **twelve hue families in the wheel's order**: `pictures` is how
many ledger rows were drawn in that map, a hue column how many of those the dominance rule
calls dominant in that family (a picture may be dominant in several or none). **Counts,
not shares**: the share is `count / pictures`.

**The verdict is read back, never re-taken**: every ledger row carries
`colour.families`, written when the picture was rendered, so a moved threshold never
re-decides a picture (the reason `candidate_ledger.rows.colour_block` stores names).
**A map with no output gets a row of zeros**, so an absent row always means a map the
library does not hold.

```
fractal-wallpapers palettes produced
```

One streamed pass, about twenty seconds over a 567k-row ledger, no render. `tests/test_palette_produced.py` holds
the file to its shape and three calibration reads (**`Blues` reads `azure`**: the wheel is
Oklab hue angle). The website imports it with `python -m builder explorer --families`,
applies its own 5% bar and freezes the result on `explorer/palettes.jsonl`; the bar is
the site's, the measurement this table's.

## Where the made maps came from: `provenance.jsonl`

One row per map that was *made* rather than converted, keyed by name:

* **authored**: written as OKLCH control points against a stated brief, carrying the
  mood, colour architecture, lightness skeleton, value key, complexity, generator version
  and the author's own stops. The brief and its checker are in
  [`../palette_authoring`](../palette_authoring/).
* **extracted**: recovered from a picture somebody else made; the row records the image.

The authored stops are **provenance, never a second gradient**: the dense file is the
render truth. A map with no row is a map nobody made. `fractal-wallpapers palettes
provenance --source <archive>` rebuilds the record.

## Where a map added since came from: `batches/`

Maps authored here arrive as a **drop**: one directory under `batches/`, holding the
generator's output files exactly as written.

```
batches/<drop>/<mood family>_c<complexity band>_v<major>_<minor>.json
batches/<drop>/renames.json      only where a name had to change
fractal-wallpapers palettes ingest --drop <drop>
```

`ingest` densifies each palette's OKLCH control points in OKLab, writes the dense map and
upserts its provenance row. **The directory name is the batch stamp** (`drop` on every
row; a row without one predates drops). Cyclicity is measured on the gradient. A name the
library, the drop or the source project's pooled library already holds is refused until
`renames.json` says what the map ships as and why; re-ingesting after a rename reports the
map left under the old name, and removing it is a person's call. `ingest` is **bake, not
offer**: the map is renderable at once and not in `../palette_choice/pool.json`.

**One map, not a drop, comes in through `palettes add`** (how a style admits the map it
matched):

```
fractal-wallpapers palettes add data/palettes/<name>.json            first admission
fractal-wallpapers palettes add data/palettes/<name>.json --replace  a re-tune of it
fractal-wallpapers palettes add <map.json> --mode <mode>            a palette for a mode's set
fractal-wallpapers palettes remove <name>                           a map no tile kept leaves
```

A style's draft map already sits at `data/palettes/<name>.json` (renders read a map by
name), and handing over **that same file** is the first admission: the file is left as it
is and the tables and groups are written. A copy from elsewhere while the library file
exists needs `--replace`, and is still a first admission to the groups while no table
names the map. Never move the library file while a render reads it. A new map that carries `dark_vivid_lime` moves
`tests/test_curation_ceiling.py`'s pinned carrier-table reading: re-pin it, naming the map
in its docstring.

It validates the document as `tests/test_colormaps.py` does, writes `<name>.json`, rebuilds
`palette_family_shares.csv` from the candidate ledger as `palettes produced` would (a box
with no ledger gets the map's all-zero row only), splices the map's own rows into
`carriers.jsonl` from three fresh recolours (every other row byte for byte), and admits
the map to the groups. About forty seconds, half of it the ledger tally.
`palettes/admit.py`'s docstring has why each step is shaped as it is.

A drop's files stay here, not beside the brief, because a batch file and
`provenance.jsonl` are one record split in two.
