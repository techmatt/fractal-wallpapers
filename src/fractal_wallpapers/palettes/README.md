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
