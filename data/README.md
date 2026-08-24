Tracked text records that the project is built from: labels, palettes, anchors,
and the tracked inputs to the training-tile build.

Three label stores, because three questions are being asked. `labels/` holds
verdicts on **places** — is this worth rendering — one row per location.
`smooth_render/` and `strange_render/` hold verdicts on **finished pictures** —
does this colouring of that place work — one row per picture, because a place
appears in them many times at many recipes and the verdicts differ.

Those two are named after the two judges that used to read them, and since
2026-08-23 one judge reads both. **The stores did not merge and are not renamed**:
a store is a corpus, these are two populations with two blind sheets and two
floors, and the names are what every row already written spells. What the names
select now is a floor, a slot and a mode roster — no longer a model.

None of them is where a labeling page writes. A page saves to an untracked
**drop** under `labels/` at the repository root, named for both the head and the
sheet, and `fractal-wallpapers label ingest` resolves what is in it against that
sheet and appends rows here. Nothing under the drop is tracked: a verdict that
only exists there is a verdict no store has resolved yet. The naming convention
and why it is both halves is
[the labeling rig's](../src/fractal_wallpapers/labeling/README.md#one-ingest-two-stores).

`batch_caveats.md` is what a registration deliberately does not carry: how a live
population was assembled, where that shapes what its rows can be asked, and what
reading them wrong looks like. It is the one file under `data/` that names live
batches on purpose — a caveat has no shape to illustrate — and it sits here rather
than in any one store because its entries span them.

`palette_choice/` is the fourth head's material and the only one here that no
human wrote: the palette head is distilled from a pretrained teacher, and what is
committed is that teacher's answers plus the real candidate sets it was asked in
production. Its README says so in a paragraph, because a machine-labeled corpus
that does not announce itself is the kind of thing a reader takes for evidence.

`palettes/` is the colormap library. Seventy-seven of its maps were curated by
hand and are the ones a render chooses from; the rest arrived with the
finished-render corpora and with the palette head's vendored candidate sets,
because a row — or a recorded decision — naming a map nobody holds is about a
picture nobody can rebuild. Two files in there are not maps and are named `.jsonl`
so no reader globbing `*.json` mistakes them for one: `provenance.jsonl` says how
the authored and extracted maps were made, and `clusters.jsonl` groups the library
for a figure. `batches/` holds the generator runs that authored the maps added
since, one directory per drop, and is the other half of what `provenance.jsonl`
records.

`palette_authoring/` is how a palette gets written in the first place: the brief a
generator run is given, a variant of it aimed at one colour region rather than one
mood, and the standalone checker both name. It sits apart from the library because
none of it is a colormap and none of it is read at render time — three files among
nine hundred maps are three files nobody finds.
