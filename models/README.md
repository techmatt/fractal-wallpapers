One home per trained head: tracked metadata here, fetched `.pt` weights land beside it.

`location/`, `render/`, `palette/` and `gallery_grade/` are the four the roster
carries and a release ships. `smooth_render/` and `strange_render/` are **superseded**: one
judge over both kinds replaced them on 2026-08-23, and their directories stay
because a head's pre-registration, its acceptance read and its own reading of
its blind sheet are the evidence of what was decided. Nothing fetches them.

The two LABEL STORES those names also belong to did not merge and are not
renamed — see `data/README.md`. A name here that is not on the roster names a
corpus or a retired judge, never something that ships.

`gallery_grade/` is a head **adopted for seating and for nothing else**, since
2026-09-07. It is stage two of a cascade behind the render judge's `p_ge4`,
fitted on the `gallery_grade` store, and `solve.DEFAULT_KEY` is that cascade — so
it orders the gallery above the bar and is read nowhere else: no floor, no bar,
no rank key, no retention.

⚠ **It is on the roster since 2026-09-14 and was off it until then.** The
argument for leaving it off was that the roster is heads a *render* goes through
and this one reads a finished picture that already passed one — which is true and
was the wrong conclusion. Off the roster it had no `weights.json` row and no
release, so a clone could read its configs and its per-sheet scores and **could
not obtain the weights at any price**: `p_fine` gates the seating bar, the
cascade order, the vetoes and growth, so the whole scored half of this repository
was shut behind one untracked file.

**Its asset is a shape no other row here has: k=3 checkpoints in one file.** The
shipped recipe averages three seeds on the probability scale, so no single
checkpoint produces the column and a release of three assets would let a clone
fetch two and score through a head nobody judged. `gallery-grade ship` writes
`gallery_grade.fp16.pt` holding the members, `gallery_grade_train.load_shipped`
reads them back, and the manifest row says `members` and `seeds`. A clone with no
run checkpoints scores the pool through that artifact; a machine holding *some*
of the runs does not fall through, because that is an interrupted fit and
scoring through a different artifact would hide it.

## The one weight here that is not ours

`curate embed` reads a frozen **DINOv2 ViT-S/14** from Hugging Face. It is not
re-hosted and should not be — it is somebody else's artifact — so it is not in
`weights.json` and `fetch-weights` does not know about it. What it has instead is
a pin, in `src/fractal_wallpapers/models/embedding.py`: `HF_REPO`, `REVISION` (a
hub commit, carried to timm through the `id@revision` spelling its own `hf_split`
reads) and `SHA256` of the 88,240,510-byte `model.safetensors`.

⚠ **`curate embed` needs the network the first time on any machine**: 84.2 MB
into `~/.cache/huggingface`, once. Every run after it is local, and
`models.embedding.verify()` hashes what was cached against the pin with no
network and no timm. Until 2026-09-14 this was `pretrained=True` against `main`
with no revision, no checksum and no size — whatever that repository held on the
day a machine first ran the command became this project's embedding basis, and a
store filled against one revision cannot be compared with one filled against
another.

`render/` carries twenty-five run directories and a name does not say which band
it realizes. [`render/RUNS.md`](render/RUNS.md) is the index: one line per
directory, to the band or role it belongs to.
