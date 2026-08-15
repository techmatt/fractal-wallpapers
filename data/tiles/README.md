Tracked inputs to the training-tile build — the pictures a judge is trained on.

`palette_pool.json` is the palette axis of the fan-out, as data rather than as a
list in code: the colormaps a free tile may draw, the `floor` that reserves the
low tile slots so every location owns the deploy-canonical view and the vivid one
a labeler judges from, and the `invariance_holdout` kept out of the draw entirely
so a head can be tested on maps it has never seen. Every name here is a file
under `data/palettes/`.

Nothing else about the recipe lives here. How many tiles a location gets, how far
they may be shifted and zoomed, how the field is extended and how a crop is
reconstructed all belong to the engine's `tiles` module, which is what actually
draws them — and a constant written down in two places is a constant that drifts.
The build's own record of what it did lands in the untracked `artifacts/tiles/`.
