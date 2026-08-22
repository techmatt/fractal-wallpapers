Which colors are available: palette assets, palette generation, and palette curation.

```
fractal-wallpapers palettes provenance --source <archive> --images <pictures>
fractal-wallpapers palettes clusters
fractal-wallpapers palettes strip --name "Bone Vault" --out artifacts/figures/bone.png
fractal-wallpapers palettes strip --manifest names.txt --width 1600 --height 120
```

`palettes` (plural) is the **library**; `palette` (singular) is the head that picks
between its maps. Nothing in this package loads a model.

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

`provenance` recovers how the *made* maps were made and writes one row per map to
`data/palettes/provenance.jsonl`: an authored map's mood family, generator
version, colour architecture, lightness skeleton, value key, complexity and its
author's own OKLCH control points; an extracted map's source image file and
nothing else. Matching is by name and an unmatched name on either side is
reported, never guessed at. The `--source` archive is the read-only source
project; `--images` is the directory of pictures the extracted maps were read
from, and without it a row records the stem it carries and says the extension was
not recovered.

`clusters` groups the whole library — Ward's linkage over `space.distances`, cut
at sixteen, each cluster listing the five members nearest its own middle — into
`data/palettes/clusters.jsonl`. The distance matrix is rounded to twelve decimals
before linkage so the merge order cannot depend on the platform's BLAS, which is
what lets `tests/test_palette_clusters.py` hold the committed file to
regeneration. Both records are `.jsonl` rather than `.json` **because every reader
of the library globs `data/palettes/*.json` and takes the stem as a map name**.

`strip` draws one map's gradient as a picture. It computes no colour: it writes a
horizontal ramp in the engine's own dump format and calls `recolor`, so the strip
comes out of the same OKLab bake, the same 4096-entry table and the same fold a
wallpaper gets. Interpolating stops in Python would be a second densifier, and the
day the two disagreed the article would be illustrating a gradient nothing
renders. The fold defaults to the pipeline's rule — folded unless the map is
cyclic — and `--no-mirror` asks for the unfolded ramp. The coloring stage
normalizes against its own 0.5th and 99.5th percentiles, so the outer half percent
of a strip's width is the end colour held flat; that is the same clip every render
gets and it cannot be compensated for, because the stretch is affine-invariant.

The same wiring reaches `recolor`, which used to send no palette block at all and
therefore baked every sequential map through its seam:

```
fractal-wallpapers recolor --field f.f32 --colormap viridis --out out.png
fractal-wallpapers recolor --field f.f32 --colormap viridis --no-mirror --out flat.png
```
