What every release run decided, and out of what population.

```
gate/<run>.jsonl     one row per colorize attempt: kept, or dropped with a reason
release/<run>.jsonl  one row per scored candidate: released, or passed over
runs.jsonl           one row per run: the whole funnel, the cuts, the configuration
runs/<run>.json      that run's own summary, whole
```

**The two decision stores are directories, one file per run, and one reader over
all of them.** `records.read_decisions(stage)` hands back the whole store in key
order and `read_decisions(stage, run)` reads that run's file alone; nothing
downstream knows there is more than one file. The run is the shard axis because
it was already the key's axis — a re-run rewrites its own rows and a second run
only ever adds — so what changed is not the semantics but the growth: as one file
each these grew for as long as the project does, and `release.jsonl` was 918 KiB
against the 1 MiB `test_history_purity` guard by the third run. Per run the
ceiling is one run's rows, about 0.4 MiB for a six-hour production run, and a
fifth run does not make the fourth one's file any bigger.

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
