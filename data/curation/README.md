What every release run decided, and out of what population.

```
gate/<run>/<partition>.jsonl     one row per colorize attempt: kept, or dropped
release/<run>/<partition>.jsonl  one row per scored candidate: released, or passed over
runs.jsonl                       one row per run: the funnel, the cuts, the configuration
runs/<run>.json                  that run's own summary, whole
```

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

**Passed-over rows are here too**, and that is the half that is easy to skip. A
record of what shipped can count what passed and never learn what it passed out
of, which is the shape of every question about a release worth asking later.

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

Rows upsert by key and the key carries the run id, so a re-run replaces its own
rows byte for byte and a second run adds rows without touching the first. A
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
```
