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
