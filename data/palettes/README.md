Colormaps, one JSON file per map, named for the map it holds.

Each file carries a `schema`, the map's `name` (which must match the filename),
its `kind` — `cyclic` if the last color returns to the first, `sequential`
otherwise — a one-line `source`, and the `stops`: `[position, [r, g, b]]` pairs
in sRGB8, in order, spanning `0.0` to `1.0`. The engine interpolates them in
OKLab, so the stops are control points rather than samples of a final gradient;
a dozen well-placed ones make a better map than a hundred evenly spaced ones.

`kind` is load-bearing rather than provenance the moment a coloring repeats the
gradient across a field: a sequential map's ends slam together at every wrap and
that seam is the most visible edge in the picture. **Folding** — baking the map
as an out-and-back — is the fix, and it is refused on a cyclic map, which has no
seam and whose cycle folding would halve. It is never applied on a map's behalf
either, because it halves how much of the gradient one pass shows, which is a
real change to the picture: it is a field of the render's own palette recipe
(`mirror`), and only a caller that sets it gets it. So `blue_orange`, the one
sequential map with a standing job here — the tile floor's second reservation and
the vivid render a labeler judges a location from — is drawn **fold-free** in
both, while a deploy-geometry location view of the same map would be folded. A
row naming a map says nothing about which gradient it got; its recipe does.

`tests/test_colormaps.py` holds these files to that shape.

**Nothing in production draws a palette knob, and exactly one leg in this
repository draws one at all.** `cycles`, `phase`, `gamma` and `reverse` are the
engine's, and every colorize this project makes is `finished.recipe()` at the
identity with `mirror` read off the map's cyclicity. The single exception is
`curate manufacture --step knobs` (`manufacture.KNOB_GRID`, six cells), which is a
**diagnostic** — it re-colours attempts that already missed their target swatch and
reports how many any cell would have rescued, as an upper bound on what a knob draw
could buy. It sweeps **cyclic maps only**, because `cycles` and `phase` are the two
the engine honours only on a map that wraps, and it renders nothing that ships.

Worth stating plainly because it is easy to assume otherwise: **no targeted seat
and no recolor path draws a knob.** A `curate gallery --target` carrier attempt
bypasses the palette head to pick its *map* and then renders at the identity
recipe like everything else, and `palettes recolor` / `strip` take the fold and
nothing more. So a hit rate measured anywhere in this pipeline is a fact about
where a pinned ramp lands on a field, never about an under-explored recipe.

Most of them were not curated: they arrived by mechanical conversion because a
labeled corpus row or a vendored candidate set names them, and their `source`
line says exactly that.

## The densifier is the engine's bake, and this directory ships only its input

Nothing here is a gradient. A file is control points, and turning them into
colors is `engine/src/colormap.rs` and nowhere else: the stops are converted to
**OKLab**, interpolated there, and baked once into a **4096-entry table of
linear-light RGB**. Perceptual interpolation because a gradient interpolated in
linear RGB is mathematically even and visually lumpy, and a table because a
2560×1440 render at 4× supersampling is 59 million lookups and the result only
ever takes 4096 distinct values.

Two properties of that bake are worth knowing before reading a picture:

* **A lookup is clamped, not wrapped.** `t` outside `[0, 1]` returns the end
  color rather than coming round the other side. What falling off the end means
  is the caller's decision, and the recipe's `cycles` and `phase` are where a
  caller says it.
* **Folding happens at bake time**, from the recipe's `mirror` — see above. The
  fold is applied to the stops before they are converted, so a folded map is a
  different 4096-entry table and not a different way of reading one table.

So **this repository ships dense sRGB8 and nothing else**: no OKLCH source, no
generator state, no baked table. The table is regenerated from these stops on
every load, which is what keeps one answer to "what colour is this map at 0.4".

**4096 is the table's width and never a file's.** `colormap.rs`'s `TABLE_SIZE` is
the bake; what is on disk here is one of four stop counts, and no map ships at
4096:

```text
 33 stops   156 maps        257 stops   334 maps
 34 stops    36 maps        512 stops   375 maps
```

The 512s are what `authored_import` densifies an OKLCH brief to; the rest arrived
by mechanical conversion at whatever resolution their source carried. A file with
4096 stops would be somebody's baked table checked in, which is the one thing the
paragraph above says this directory is not for.

### Reading a Python-side gradient against the Rust bake

The check that the two agree is a strip at the table's own width:

```python
strip.draw(name, out, 4096, 1, mirror=False)
```

One pixel per table entry, one row, unfolded. But the strip is not the table read
off directly, because **the coloring stage stretches every field against its own
0.5th and 99.5th percentiles** and a ramp is a field like any other. The stretch
is nearest-rank (`coloring.rs::percentile`, `CLIP_LOW` / `CLIP_HIGH`), so over a
4096-sample ramp the arithmetic is exact and known: `low` is sample
`round(0.005 × 4095) = 20`, `high` is sample `round(0.995 × 4095) = 4075`, and
pixel `i` therefore shows the map at

```text
t = clamp((i - 20) / 4055, 0, 1)
```

Undo that and the strip reads the bake. Samples 0–20 are all `t = 0` and
4075–4095 all `t = 1` — the ends held flat, duplicated rather than lost, which is
why the stretch is invertible even though it is not avoidable. Measured on
`viridis`, the flat runs come out 26 and 24 pixels rather than 21 and 21; the
extra pixels are sRGB8 quantization near the ends, not a wider clip.

**This does not contradict
[`palettes/README.md`](../../src/fractal_wallpapers/palettes/README.md)'s "cannot
be compensated for"** — that sentence is about *avoiding* the clip, and it is
right: the stretch is affine-invariant, so no choice of ramp values dodges it and
a strip always spends its outer half percent on the end colours. What is
recoverable is the *mapping*, because the index arithmetic above is fixed. Avoiding
and inverting are two different questions and only the second one has an answer.

## Which maps are the same choice: `groups.jsonl`

Nine hundred maps are not nine hundred choices. `groups.jsonl` says which of them
are near enough that picking between them is picking nothing — **65 groups over
143 of the 901 maps, the largest holding 6** — and
`fractal-wallpapers palettes groups` regenerates it. The metric is M1: the sliced
Wasserstein-1 distance between two maps' 4096-position **unfolded** Oklab clouds
read through the engine's own bake, with `a` and `b` scaled by 4 so a hue
difference counts four times a lightness difference of the same size. Average
linkage, cut at **0.039735** — the midpoint between the widest pair marked SAME
and the nearest pair marked DIFFERENT on a forty-six pair calibration sheet ruled
by eye on 2026-08-25, which the marks leave with no inversions. Every merge in the
file was reviewed one at a time.

**The pool collapses through it at read time.** `curation.colorize.pool` keeps one
member per group and stands the rest down — **drawn at random on the run's seed,
not the canonical member**, because the members are indistinguishable and none of
them deserves the slot permanently. Singletons are untouched, nothing is deleted
from this directory, and the run record's `config.palette_pool` names the group
every absent map stood down for. `FRACTAL_WALLPAPERS_PALETTE_GROUPS=off` turns it
off for one run. A group's `canonical` member — the one carrying the most
finished-render label rows — is what a record or a figure *names*; it is
deliberately not what the pool draws.

**The three counts, and none of them is the same number.** The **library** is 901
maps — every file in this directory. The **candidate pool** is 900: `pool.json`
next door, the library less `blue_orange`, the one sequential map held back for the
tile floor and the labeler's vivid render. What a colorize actually **draws** from
is 822, because 143 of the 900 collapse into 65 groups and each group stands one
member up (`757 singletons + 65 = 822`). The count is seed-independent — a
different `--seed` stands a different member up, never a different number of them
— so 822 is the width of the drawable pool for every run with the collapse on.

Regenerating the table is not cheap: `fractal-wallpapers palettes groups` is
**about five minutes** — 279 s measured on this repository's own machine for the
901 × 901 distance matrix, 1,024 projection directions at 128 quantiles each, plus
the linkage — and it rewrites `groups.jsonl` when it finishes. It reproduces: the
same run re-derived 65 groups over 143 maps against the shipped file exactly.

The table is worth about a slot in twenty: over gallery3's 150 recorded candidate
neighbourhoods, **97 held two or more members of one group** and the collapse
would have freed **199 of the 4,800 candidate places**.

## What a palette sheet is judged on: `reference_fields.jsonl`

A sheet asking "do these two maps look alike" has to show them on something, and
two sheets rendered through two different fields are two instruments. Three fields
are pinned here — one coloured once, one the ramp sweeps across several times, one
a parameter plane — each the released `gallery3` location whose stretched field
carries the highest 64-bin gradient entropy in its class, with the three
constrained to three different modes so no coloring speaks twice.

**The spec is tracked and the dump is not.** A `.f32` field is a megabyte of
little-endian floats, which the history guard keeps out and which
`fractal-wallpapers palettes reference-fields` remakes into
`artifacts/palettes/reference_fields/` from the twelve numbers in the record. That
split is the fix for how these three nearly died: they lived only in a session
scratchpad through three audit passes, and a cleanup of that directory would have
taken the calibration sheet's instrument with it. The regenerated dumps were
checked byte-for-byte against the surviving copies.

## A hue family is twelve 30° spokes, and a spoke is never a category

`codebook.rollup` folds the 52 swatches onto the twelve `HUES` spokes plus
`neutral`. That is the only colour *family* level this repository has, and it is
30° wide — so a hue band that drifts across a spoke midpoint reads as a family
flip when nothing about the picture flipped. Two maps whose pink runs 335–340° and
340–348° come out one all-`rose` and one all-`magenta`, a full categorical
difference from eight degrees.

**It is not an edge case.** Reading each map's family *mass* over its cloud and
calling a family "present" above a soft 2–8% ramp, **473 of the 901 maps sit on at
least one soft edge** — azure 111, yellow 98, orange 94, cyan 92, rose 90, teal 85,
red 72, magenta 69, blue 68, lime 64, green 64, purple 61 — with a mean neutral
mass of 25%. So a rollup is a *reading*, useful for a thin table somebody has to
rule from, and anything that treats a family as a category needs a wheel-aware
term rather than a per-family difference. A family-presence gate built on `|Δp|`
was tried over M1 and rejected: it closed 98.8% of all pairs and, on the
calibration sheet, separated the pair Matt marked SAME while rescuing nothing.

## A sheet's JPEG settings are part of its recipe

A comparison sheet is an instrument, and its encoder is one of its settings. The
page the groups cut was ruled on was written at **quality 70, 4:2:0**, and nothing
said so: the pass that extended it had to recover those numbers by re-encoding the
page's own pictures and finding where the round trip bottomed out, then match them
— because a page whose new thumbnails are sharper than its old ones cannot be
judged by eye. Raw comparison
read a mean channel difference of 9–15 before the codec was accounted for and 4.36
after, against the codec's own floor of 11.31 on that content. Record the quality
and the subsampling beside the pictures; a re-render at another quality is a second
instrument, not a refresh.

## The ramp as it was actually applied

`palettes.strip` draws a map through the engine's bake, so a strip is the gradient
the render spent — but on a **levelled** picture the render did not spend the
tracked map. The autolevel operator writes the map it actually used, under the
map's own name, into `<run>/release/<stem>.leveled/`, so:

```
strip.draw(name, out, colormap_dir=Path(run) / "release" / f"{stem}.leveled")
```

draws the ramp **as applied to that picture**, and the same call without the
directory draws the library's. The two differ wherever the operator acted, which
on the reference fields was 551, 546 and 622 of 901 maps — so a figure pairing a
levelled wallpaper with its library ramp is showing two different gradients and
captioning them as one.

## Where the made maps came from: `provenance.jsonl`

Two groups of maps here were *made* rather than converted, and what made them is
not recoverable from a dense file. `provenance.jsonl` holds one row per such map,
keyed by name:

* **authored** — written as OKLCH control points against a stated brief, and
  carrying it: the mood, the colour architecture, the lightness skeleton, the
  value key, the complexity, the generator version that emitted the batch, and
  the author's own stops. The brief those runs were given, and the checker their
  output is held to, are in [`../palette_authoring`](../palette_authoring/).
* **extracted** — recovered from a picture somebody else made. The row records
  the image file, and nothing more.

The authored stops there are **provenance, never a second gradient**. Nothing
renders from them; the dense file above is the render truth. A map with no row
is a map nobody made — its `source` line already says all there is to say.

`fractal-wallpapers palettes provenance --source <archive>` rebuilds the record.

## Where a map added since came from: `batches/`

The 175 maps this repository started with were authored in the source project and
their briefs are in its read-only archive. Maps authored since arrive as a
**drop** — one directory under `batches/`, holding the generator's own output
files exactly as it wrote them, one file per run:

```
batches/<drop>/<mood family>_c<complexity band>_v<major>_<minor>.json
batches/<drop>/renames.json      only where a name had to change
fractal-wallpapers palettes ingest --drop <drop>
```

`ingest` interpolates each palette's OKLCH control points in OKLab, writes the
dense map beside the others, and upserts its provenance row. **The directory name
is the batch stamp**: every row a drop produces carries it as `drop`, and a row
with no `drop` is a map from before drops existed — which is how a census or a
preference read separates one from the other without any old row being rewritten.

Whether a map is cyclic is measured on the gradient rather than taken from the
drop it arrived in, and a name the library, the drop or the source project's
pooled library already holds is refused until `renames.json` says what the map
ships as and why. Re-ingesting a drop after a rename reports the map left behind
under the old name; removing it is a person's call, not the ingest's.

`ingest` is **bake, not offer**: a densified map is renderable immediately and is
not in `../palette_choice/pool.json`, so nothing picks it until somebody adds it
there.

A drop's files stay here rather than beside the brief that produced them, because a
batch file and `provenance.jsonl` are one record split in two — the row a shipped
map carries and the run that emitted it — and nothing reads one without the other.
[`../palette_authoring`](../palette_authoring/) holds the input side: the brief, the
variant of it the `rare-colors-2026-08` runs were given, and the checker.
