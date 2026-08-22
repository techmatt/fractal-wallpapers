What every release run decided, and out of what population.

```
gate/<run>/<partition>.jsonl     one row per colorize attempt: kept, or dropped
release/<run>/<partition>.jsonl  one row per scored candidate: released, or passed over
runs.jsonl                       one row per run: the funnel, the cuts, the configuration
runs/<run>.json                  that run's own summary, whole
bar_exceptions.jsonl             rows a ruling keeps in service below an acting bar
```

**`bar_exceptions.jsonl` is the one file here a person writes.** Everything else
is a run's own account of itself; this is a verdict about four rows of it. The
retroactive bar pass (`curate reject`) is a *rule* read live against today's cuts,
so it finds the same rows every time it is asked — and four run8h strange rows
below the 0.685 bar stay served on Matt's ruling. One row per excused release row,
keyed on that row's own `run|stage|candidate`, carrying the bar it sits under, the
score, who ruled and when and why. Per row and never per run or per head: an
exception naming a run would excuse rows that run has not made yet, and one naming
a head would retire the bar by the back door. It is read from the checkout rather
than from the record root, so a rehearsal that redirects the store under `scratch/`
does not stop the ruling applying.

**The two decision stores are trees, a file per run per partition, and one reader
over all of them.** `records.read_decisions(stage)` hands back the whole store in
key order and `read_decisions(stage, run)` reads that run's directory alone;
nothing downstream knows there is more than one file. Neither axis is invented for
the filesystem's sake — the run was already the key's axis, and the partition is
the axis every apportionment here is taken on, which is why
`data/palette_choice/rows/` is written the same way down to the file names.

What it buys is a ceiling that does not move with the project's age. As one file
per stage these grew for as long as the project does: `release.jsonl` was 918 KiB
against the 1 MiB `test_history_purity` guard by the third run. One file per run
alone would not have been enough either — the 240-attempt run that followed wrote
828 KiB of release rows. Per run and partition the largest file that run wrote is
195 KiB, and a run five times its size still fits.

**The pictures are regenerable and the population is not.** A run over ledgers
that have since grown, through heads that have since been re-shipped, cannot be
re-run to recover what it decided — and the rate anybody later wants to compute
has the deleted denominator in it. So the decisions accumulate here as tracked
text, and `runs.jsonl` carries the counts every stage of the funnel passed *out
of*, not only what survived.

**Every row carries its whole join.** The verdict and the location with every
family constant, the mode, the map, the recipe, the scores from both heads that
touched it, which kind of slot it took, and the autolevel stamp of the render the
decision was taken on — on one line. A row keyed on an identifier whose meaning
lives in another file is orphaned the day that file moves.

**There are two autolevel stamps per released row, and only one of them is here.**
The stamp on the row is the one from the render the *decision* was taken on, at
candidate geometry. The release render is a second pass and gets its own stamp,
written by the parent — never by a worker — to
`artifacts/curation/runs/<run>/release/autolevel_stamps.jsonl`, and that is the
one `curate replay` rebuilds a shipped picture from. A row's stamp does not
describe the wallpaper; the sidecar's does.

**Passed-over rows are here too**, and that is the half that is easy to skip. A
record of what shipped can count what passed and never learn what it passed out
of, which is the shape of every question about a release worth asking later.

**A release verdict is one of three, and they are not two.** `run.release_verdict`
reads a slot and a picture: a row that took no slot is `passed_over`, a row that
took one and has a full-resolution picture is `released`, and a row that took one
and has no picture is `killed` — its render died under it.

**A row that took a slot and has no picture is not a released row.** The release
verdict answers one question — is there a wallpaper at the end of this row — so a
row whose full-resolution render was killed reads `verdict: killed` with its
picture pointer cleared, rather than `released` pointing at the 640x360 candidate
JPEG the gate decision was taken on. That render is on disk and resolves, so the
difference is a listing serving a thumbnail as a wallpaper: `run3` released 39
rows, made 37 pictures and shipped two such links. What a release *serves* asks
for the picture as well as the verdict.

**A verdict taken after the run is added, never written over.** A released row a
later review takes back keeps `verdict: released` — that is what the run decided
and it stays true, and a store that edited it would delete the evidence the
release path had a defect — and gains a `rejected` block: who, when, why, and the
bar and artifact it failed. Scores are untouched. What a release *serves* is
released minus rejected, and every listing reads that rather than the raw
verdict. `run2`'s eleven below-bar strange rows are here on exactly those terms.

**A rejection can be a comparison instead of a measurement, and then it names the
row it lost to.** One wallpaper per location acts at selection from 2026-08-22 and
cannot reach backwards, so `curate retire-repeats` applied it once to the
collection that predates it: 27 locations were holding 59 wallpapers between them,
each kept the highest `P(>=3)` on its own head's scale, and the other **32** rows
carry a `rejected` block with `reason: location_served`, `bar: null` and a
`survivor` field holding the key of the wallpaper that kept the place. 185 served
became 153. A retired row is a second picture of a place the collection has, not a
bad picture — which is why no bar is read here and why the survivor is on the row:
a reader re-deriving it later would be re-deriving it against a collection that
has moved.

Rows upsert by key and the key carries the run id, so a re-run replaces its own
rows byte for byte and a second run adds rows without touching the first.
`runs/<run>.json` is the exception: it is written **whole** rather than upserted,
so a resume replaces it outright and the interrupted attempt's own wall-clock
record does not survive. What a resumed run reports is the resumed leg. A
rehearsal must not write here at all — `curate run --ephemeral` redirects the
whole store under `scratch/`, because a sixty-row smoke's decisions are
indistinguishable in an accumulated file from a real release's.

The pictures themselves, the candidate log and the run's release sheet land in
the untracked `artifacts/curation/runs/<run>/`.

```
fractal-wallpapers curate score
fractal-wallpapers curate plan -n 6
fractal-wallpapers curate run --run <name> -n 6
fractal-wallpapers curate reject --run <name> --rejector <who> --date <when>
fractal-wallpapers curate repeats
fractal-wallpapers curate retire-repeats --rejector <who> --date <when> --dry-run
```
