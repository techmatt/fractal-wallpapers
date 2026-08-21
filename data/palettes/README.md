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
