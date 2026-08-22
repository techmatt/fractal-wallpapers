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
  the author's own stops. `generator_prompt.md` beside it is the brief those runs
  were given, and `validate_palettes.py` is the mechanical checker it names —
  a standalone script for a reader to run on their own output, not a module of
  this package and not a subcommand.
* **extracted** — recovered from a picture somebody else made. The row records
  the image file, and nothing more.

The authored stops there are **provenance, never a second gradient**. Nothing
renders from them; the dense file above is the render truth. A map with no row
is a map nobody made — its `source` line already says all there is to say.

`fractal-wallpapers palettes provenance --source <archive>` rebuilds the record.
