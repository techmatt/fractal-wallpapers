Tracked text records that the project is built from: labels, palettes, anchors,
and the tracked inputs to the training-tile build.

Three label stores, because three questions are being asked. `labels/` holds
verdicts on **places** — is this worth rendering — one row per location.
`smooth_render/` and `strange_render/` hold verdicts on **finished pictures** —
does this colouring of that place work — one row per picture, because a place
appears in them many times at many recipes and the verdicts differ.

`palettes/` is the colormap library. Seventy-seven of its maps were curated by
hand and are the ones a render chooses from; the rest arrived with the
finished-render corpora, because a row naming a map nobody holds is a verdict
about a picture nobody can rebuild.
