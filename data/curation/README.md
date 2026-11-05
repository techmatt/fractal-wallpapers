What every release run decided, and out of what population.

```
gate/<run>/<partition>.jsonl     one row per colorize attempt: kept, or dropped
release/<run>/<partition>.jsonl  one row per scored candidate: released, or passed over
runs.jsonl                       one row per run: the funnel, the cuts, the configuration
runs/<run>.json                  that run's own summary, whole
manufacture/<batch>/<kind>.jsonl what a manufactured row was made FOR, keyed on its render
bar_exceptions.jsonl             rows a ruling keeps in service below an acting bar
pins.txt                         explorer links to rows every solve seats first — edited by prompts
pins.json                        each of those links resolved to its ledger row (`curate pins resolve`)
rank_key/                        the rank key's fit and its population (`curation.rank_key`)
*.manifest.json                  what an untracked store is, so a loss shows (below)
candidate_ledger/ratchet.jsonl   how large the candidate ledger has ever been, and what took rows off
ledger_provenance.json           which walk ledger each released row was drawn from
```

`release/gallery1`–`gallery4` are the release-store rows of the retired gallery passes; they
carry `collection: "gallery"`, a `slot` block, and, for a row re-seated from a run, a
`source` block naming the row it came from under the id `<run>_<candidate>`.

**A link this repository writes is the explorer's permalink v4.** `pins.query_of` is the one
writer: it spells a view as `explorer/permalink.js` does, defaults left out, and writes the
cap as `n` whenever it is not `engine.maxiter_for` at `w`. `EXPLORER_BASE` says `v=4`. The
explorer reads v1 to v4, so the `v=3` links in `pins.txt` stay valid, and `parse` reads a
pin by place and mode whatever its version.

## Manifests: tracked descriptions of untracked stores

Each `*.manifest.json` records an untracked store's row count, byte count and sha256 plus
its own axes; the bytes live on both storage tiers (`curation.durability`). A store too big
or too churned for the per-file history guard is described here rather than tracked.

| manifest | untracked store (paths relative to `artifacts/curation/`) | kept by |
|---|---|---|
| `supply_scores.manifest.json` | `supply_scores.jsonl`, the location head's read of the supply | `curate sidecar save\|check\|restore`; rebuilt by `curate score` |
| `score_amendments.manifest.json` | the score amendment overlaid on that sidecar | `curation.amend` |
| `hunt_frames.manifest.json` | the hunt frame index every mining leg draws framings through | `curation.hunt` |
| `neutral_embeddings.manifest.json` | `neutral_embeddings.jsonl`, one 384-d DINOv2 vector per admitted location | `curate embed`; `curate embeddings save\|check\|restore` |
| `spiral_scores.manifest.json` | the spiral attribute's scores | `curation.spiral_scores` |
| `palette_mass_sweep.manifest.json` | the palette colour-mass sweep | `curate mass-sweep save\|check\|restore` |
| `colors/census.manifest.json` | the colour census | `curation.colors` |
| `candidate_ledger/rows.manifest.json` | `candidate_ledger/rows.jsonl`, one row per recipe ever rendered | `curate candidate-ledger backfill\|census\|save\|check\|restore` |
| `candidate_ledger/scores.manifest.json` | `scores.jsonl` beside it, one row per (recipe, judge artifact, regime) | as above |
| `candidate_ledger/flatness.manifest.json`, `signatures.manifest.json` | the ledger's flatness and signature sidecars | `curation.flatness`, `curation.signatures` |

`curate run` refuses to start when a **guarded** file is missing or holds fewer rows than
its manifest records: the supply sidecar, the score amendment and the hunt frame index
(`curation.durables.guarded`), the inputs a run would otherwise read silently at stale
values. The embedding manifest also records the **frozen choices** (colormap, geometry,
mode, encoder) and their digest, since changing any of them makes every stored vector a
reading of a picture that no longer exists. The candidate-ledger package's `store` half is
what a reader of those files wants; its key type is `curation.recipes`.

**`candidate_ledger/ratchet.jsonl` asserts a ratchet, not a census.** The ledger deletes by
design (`candidate_ledger.sweep.prune` on every merge), so what holds is: the count now, plus
every deletion recorded since the high-water mark, reaches that mark. Rows are `mark` and
`deleted`, resolved per counter; `prune` is the only writer. The first two rows were written
by hand and say so (the baseline mark and one reconciliation of unrecorded loss); never
re-baseline the mark. Read it with `curate candidate-ledger ratchet [--census]`;
`tests/test_leveled_identity.py` holds the store to it and `tests/test_ratchet.py` the
arithmetic.

**`ledger_provenance.json`** names the walk ledgers the released rows were drawn from, a
snapshot rather than a property. Regenerate it with `curate ledgers --write`, which resolves
through the tier funnel (the hot tier alone reports archived ledgers as lost).

## The decision stores

**Two trees, a file per run per partition, one reader.** `records.read_decisions(stage)`
reads the whole store in key order and `read_decisions(stage, run)` one run; nothing
downstream knows there is more than one file. Per run and partition keeps every file well
under the per-file history guard however long the project runs; `data/palette_choice/rows/`
is laid out the same way.

**The pictures are regenerable and the population is not**, so decisions accumulate here
as tracked text, passed-over rows included, and `runs.jsonl` carries the count every funnel
stage passed *out of*.

**Every row carries its whole join**: the verdict, the location with every family constant,
the mode, map, recipe, both heads' scores, the slot kind and the autolevel stamp of the
render the decision was taken on.

**`release_geometry`** is the frame and field supersample of the shipped picture
(`recipe.render` is the candidate geometry). A solve picks it per pass (`--release-regime`,
1280x720ss2 by default); `null` on a row with no picture; rows predating the field came from
2560x1440 ss4 (`curation.checks.UNRECORDED_REGIME`). A colour census is a census at one
release geometry.

**Two autolevel stamps per released row.** The row's is the decision render's, at candidate
geometry; the release render's is written by the parent to
`artifacts/curation/runs/<run>/release/autolevel_stamps.jsonl`, and that is what
`curate replay` rebuilds a shipped picture from.

**A release verdict is one of three** (`run.release_verdict`): no slot is `passed_over`; a
slot with a full-resolution picture is `released`; a slot whose render died is `killed`, its
picture pointer cleared, so a candidate JPEG is never served as a wallpaper.

**Which collection a picture is in is a field, not a verdict**: `collection` is
`diagnostic` for what a run keeps and `gallery` for what the collection shipped. A run
writes `diagnostic` on every row. The rows predating the field were backfilled to
`diagnostic` once, the one rewrite of recorded data this store has had.

**Two readings of a row's picture, one of them a decision.** `scores` is what the run read on
the night, and is never overwritten. `curate rescore` re-reads every candidate through the
judge shipped now into `scores_current` (with that head's sha256 and `judge`; `head` stays
the row's kind). Every cut reads `records.live_reading` (`scores_current` where present). An
absent `scores_current` does not mean a stale reading: `rescore.artifact_of` finds the
artifact from the block or the run's own summary, and `rescore.reading_on` qualifies on the
artifact, never the field name.

**A verdict taken after the run is added, never written over.** A released row a review takes
back keeps `verdict: released` and gains a `rejected` block (who, when, why, the bar and
artifact it failed); what a release *serves* is released minus rejected. A rejection by
comparison (`curate retire-repeats`, one wallpaper per location) carries
`reason: location_served`, `bar: null` and a `survivor` naming the wallpaper that kept the
place.

**`bar_exceptions.jsonl` is the one file here a person writes**: one row per excused release
row, keyed on its `run|stage|candidate`, with the bar it sat under, the score, who ruled,
when and why. Per row, never per run or head: a run-wide exception would excuse rows not yet
made, a head-wide one would retire the bar. It is read from the checkout, not the record
root, so a redirected rehearsal still honours it. Its readers are `rejection.py` and
`below_bar.py`, through `rejection.below_acting_bar`; pool readers exclude *rejected* rows
(`records.is_rejected`), and an excused row is not rejected, so it stays seatable.

**Rows upsert by key and the key carries the run id**, so a re-run replaces its own rows and a
second run adds. `runs/<run>.json` is written whole, so a resumed run reports the resumed leg.
A rehearsal writes nothing here: `curate run --ephemeral` redirects the store under
`scratch/`. Pictures, the candidate log and the release sheet land in the untracked
`artifacts/curation/runs/<run>/`.

```
fractal-wallpapers curate score
fractal-wallpapers curate embed
fractal-wallpapers curate embeddings save
fractal-wallpapers curate plan -n 6
fractal-wallpapers curate run --run <name> -n 6
fractal-wallpapers curate reject --run <name> --rejector <who> --date <when>
fractal-wallpapers curate repeats
fractal-wallpapers curate retire-repeats --rejector <who> --date <when> --dry-run
```

## `manufacture/` — the half of a manufactured row a label store cannot hold

`curate manufacture` forces rare swatches onto places a person already scored a keeper and
serves the results for correction. The verdicts land in `data/<kind>/rows/` with the whole
render join; **why the picture was made** lands here: one row per selected sheet row, per
kind, keyed on its `render_key`:

```text
target       which thin swatch this row was manufactured for
arm          `new` for a rare-colours-drop map, `contrast` for one the library held
tier         `human_q3` or `admitted`: which population the location came from
sheet        what the codebook and the judge read off the picture SERVED
candidate    the same two readings at candidate geometry, where the screen ran
```

`batch.json` beside them is the selection: rows per kind, shortfalls, the rows-per-map
distribution, and the tier and arm splits. Two kinds are two files to stay under the
per-file guard.

**The arm is a batch and the tier is a row**: `manufactured_rare_colors` and
`manufactured_rare_colors_contrast` are registered per store, because each arm is a draw;
both tiers are one draw, so the tier rides on the row.

**These rows and the verdicts are the durable halves; the cut sheets are not.** A
manufacture pass's `artifacts/<name>/` sheet directories may be deleted once ingested;
nothing tracked names, counts or resolves through them, which is the rule for every sheet
directory.
