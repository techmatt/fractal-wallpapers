Tracked text records that the project is built from: labels, palettes, anchors,
and the tracked inputs to the training-tile build.

Three label stores, because three questions are being asked. `labels/` holds
verdicts on **places** — is this worth rendering — one row per location.
`smooth_render/` and `strange_render/` hold verdicts on **finished pictures** —
does this colouring of that place work — one row per picture, because a place
appears in them many times at many recipes and the verdicts differ.

`palette_choice/` is the fourth head's material and the only one here that no
human wrote: the palette head is distilled from a pretrained teacher, and what is
committed is that teacher's answers plus the real candidate sets it was asked in
production. Its README says so in a paragraph, because a machine-labeled corpus
that does not announce itself is the kind of thing a reader takes for evidence.

`palettes/` is the colormap library. Seventy-seven of its maps were curated by
hand and are the ones a render chooses from; the rest arrived with the
finished-render corpora and with the palette head's vendored candidate sets,
because a row — or a recorded decision — naming a map nobody holds is about a
picture nobody can rebuild.
