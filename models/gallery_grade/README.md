The **fine-tier head**: an order inside the render judge's own flat top.

The render judge answers *is this picture worth keeping* and saturates at the good end
of its scale. This head answers *how good, given it already cleared the bar*. It is a
separate network, the render judge's architecture initialised from its shipped
artifact, fitted on the `gallery_grade` store's human verdicts at the ledger's 640x360
candidate geometry. Code: `src/fractal_wallpapers/models/gallery_grade_train.py`.

**What ships is `twelve_sheets_drop_high_asymmetric_auc_ge4_more_k3`**: an **ensemble of
seeds 0, 1 and 2** averaged on the probability scale, so no single checkpoint produces
the column. `shipped_runs()` is the one derivation of that name, and
`gallery_grade.fp16.pt` holds the three members in one file.

⚠ **One reader, and it is the seating.** `solve.DEFAULT_KEY` is `solve.CASCADE_KEY`, so
an unflagged `curate solve run` orders on this head above the bar, and
`solve.DEFAULT_FINE_BAR` (`0.030242`) narrows the seatable pool on the same column.
`curation/rank_key.py`, retention, `_prune_ranks` and every floor ignore it: what a
prune keeps stays a separate question from what a gallery seats.

## It ships

```
fractal-wallpapers gallery-grade ship           # halve the ensemble, measure it, write the row
fractal-wallpapers gallery-grade stamp-scores   # the one-way weights backfill for p_fine rows
fractal-wallpapers fetch-weights --head gallery_grade
```

It is in `models/roster.py` and ships under `roster.TAG` with the other three heads. A
head shipped after a package is published goes into a **new** dated tag and every row
is repointed; a published tag never gains an asset.

**One asset, k=3 members**, so a clone can never fetch part of the ensemble.
`export_fp16` writes the members, `load_shipped` reads them back, and the manifest row
says `members: 3` and `seeds: [0, 1, 2]` (15.4 MB, re-read bit-identical).

**The fp16 check reports rather than gates.** Over 8,000 pool rows (top 6,000 by
`rank_score` plus a seeded tail) half precision moved 4 rows across the bar and 2 seats
of the top 1,000. The older judges gate on constants ratified for their populations;
this head has no ratified bound, so the reading goes on the record instead.

⚠ **The `p_fine` rows in `artifacts/gallery_grade_head/pool_scores.jsonl` are stamped
with the fp32 checkpoints' digest, not this artifact's.** A clone scoring through the
published head writes differently-stamped rows; that is the guard working.
`gallery_grade_train.SCHEMA_NOTES["weights_are"]` says so on every row.

## Three axes name a run: corpus, band, recipe

```text
axis     flag        what it names                      shipped value
corpus   --corpus    which rows                         twelve_sheets
band     (verb)      which stopping rule                auc_ge4
recipe   --recipe    which knobs                        drop_high_asymmetric
```

`--corpus` and `--recipe` are on **every** verb that names a run, `read` and `accept`
included, so a join, split, bar and run each say what they are about. Each axis's first
value keeps bare file names (`as_built`, `ap_ge3`'s `<arm>_seed<N>`, `inherited`);
later values prefix theirs, so a refit never overwrites a run a seating refers to.

⚠ **The default is the ADOPTED corpus and recipe, not the newest**:
`gallery_grade_train.CORPUS` and `RECIPE`. `score-pool` writes the column a seating
orders on, so a default pointing at a staged refit would let an adoption happen by
forgetting a flag. Moving them is part of adopting a refit.

⚠ **The `twelve_sheets` corpus is frozen and tracked**: 2,829 rows over twelve
labelling sheets under `data/gallery_grade/corpus/twelve_sheets/` with checksums, and
both writers refuse to touch it. `gallery-grade population` reads the live store and
will not give them back. `data/gallery_grade/corpus/README.md` is the decision.

**Bands.** `ap_ge3` (the render judge's own rule) is the wrong boundary here: an order
inside the gate's top is 3-against-4, so every band since stops on `AUC(>=4)`. The
`frozen` arm (a linear read of the frozen trunk) reads chance on that boundary and is
not refitted; `last_block` and `more` (every parameter) are the arms, and `more` wins.

## The recipe

`drop_high_asymmetric`, carried from the render judge's config except for four knobs:
dropout 0.4 / stochastic depth 0.2, every CORN cutpoint's negative term at 2x, a fixed
30-epoch horizon keeping the `AUC(>=4)` checkpoint (no early stop), and a learned
per-sitting offset dropped at inference. Weight decay 0.05, grad clip 1.0, cosine 2e-4
backbone / 1e-3 head, batch 32, sqrt class balance x per-place weight. The transform:

```text
1 border crop     uniform(0, 0.05) per edge, independently; skipped under 8 px
2 resize          bicubic STRETCH to 384x224, the same call at deploy
3 horizontal flip p = 0.5
4 vertical flip   p = 0.5
5 JPEG re-encode  OFF   (`jpeg=None`)
6 brightness      OFF   (`brightness=0.0`)
7 contrast        OFF   (`contrast=0.0`)
8 normalize       ImageNet-12k mean/std off the backbone's data config
```

**The three that are off are off by ruling**: `models/head.py`'s *The transform is the
same core in training and at deploy*. The palette is part of the label, so a colour
jitter would move the answer with the picture.

## The bar, registered before the band existed

`gallery-grade preregister` writes the bar before any run of its band (`write_bar`
refuses afterwards); `accept` writes the comparison. The winning arm must beat **both**
incumbents (the render judge's `p_ge4` and the shipped `rank_key`) on **both**
`AUC(>=4)` and Spearman against the grades, at **every** seed: twelve gated cells, no
partial credit. Incumbent heights are copied into the bar, so a later refit of
`rank_key` cannot move it. The shipped recipe cleared 12 of 12 at worst margin +0.115.

**The split balances the SHEET, the BLOCK and the GRADE** as marginals, lineages taken
whole. ⚠ **A stratum is read by the split and never by the model**: Matt's ruling
accepts the sheets' disagreement as label noise (no sheet term, no reweighting, no
exclusion).

**What every number here is**: the 20% is both the stopping slice and the only held-out
read, and three choices land on it (the epoch, the arm by mean, the seed by median), so
every figure is optimistic. The bar is the one thing not chosen on it. The store is not
eval-eligible and nothing here is a base rate (`data/gallery_grade/README.md`). The
column covers only rows clearing their mode's bar; other rows get no output, so a
`p_fine` filter narrows the seatable pool and never hides a coverage hole.

## Adopted 2026-09-09 — the column stayed, the level was re-matched

**A seating level on this column is a MATCHED constant, not a discovered one.** At each
adoption `solve.DEFAULT_FINE_BAR` is set to the level at which the new head admits the
same fraction of the above-bar pool the previous head admitted: **27.76%**, held since
this adoption. It is not a tightening or a loosening, and a level means nothing apart
from the head it was matched on (`config.fine_head` must be read beside
`config.fine_bar`). Derive it against the pool of the day; mining into thin cells moves
the pool and the match drifts, and a drift is information about the pool.

**The gated column is `p_ge4`.** At equal admission on the stopping fold it keeps the
most labelled 4s:

```text
column        recall of 4s   4s among admitted   >=3 among admitted
p_ge4               0.742              37.7%              70.9%
sqrt(p3*p4)         0.708              37.7%              70.7%
rank_score          0.663              38.6%              75.8%
p_ge3               0.596              39.6%              76.9%
```

`p_ge3` is not a gated statistic, and a level is a recorded parameter where a column is
a code change in `solve.at_fine_bar` plus a ruling. Because the fraction is held, an
adoption changes **which rows** are admitted and their order, not how many: a
before/after across one compares two populations.

**Superseded scores are kept**: `score_pool` moves the live `pool_scores.jsonl` to
`pool_scores_<run>.jsonl` before writing, because every solve record resolves its
cascade order from that file.

**Reading the level as quality**: Matt's ruling allowed `p_ge4 >= 0.5` on the first
head to be read as *good enough to seat*. That ruling is about that head's scale; the
matched levels since are not quality targets, and whether one may be read that way has
not been asked. No bar or floor reads this head; wiring it into a cut is a second ruling
and a `Restatement`.

## What the de-drifted target is for

`data/gallery_grade/README.md`'s *Three ways to identify the footing* fits a normalized
view of the store. **Normalizing helps as an EVALUATION target and does nothing as a
TRAINING target**: every arm reads far better against normalized labels, but fitting on
them does not beat fitting on raw ones even when normalized labels score it, and it lets
more raw grade-1 rows above a matched bar (half the corpus changes tier). Train on raw
verdicts.

**The asymmetry lives in the threshold, not the loss**: upweighting CORN negatives 2x or
4x barely moved the escape rate, while holding escape at 5% instead of matching 27.76%
narrows the admitted pool about sixfold.

## A fit here does not reproduce, and the fix is one call

Without determinism, refitting the same recipe at the same seeds on the same rows gave a
different head: the matched bar moved 3.7x, the admitted set churned by half, and 516 of
1,000 seats changed. The input stream is a pure function of the seed (augmentation keyed
on `<row>:<epoch>`); the CUDA kernels diverge in the first epoch, and the flat 30-epoch
`AUC(>=4)` surface turns that into a different checkpoint.

★ **`torch.use_deterministic_algorithms(True)` makes it bit-for-bit reproducible, for
about 8% per epoch.** `CUBLAS_WORKSPACE_CONFIG=:4096:8` must be set before torch is
imported: `fractal_wallpapers.cli` sets it at entry, and `models/train.make_deterministic`
turns the flag on and **refuses** when the variable is absent. `drop_high_asymmetric`
calls it; other trainers do not yet. A whole 30-epoch run repeats bitwise (every loss,
logit and checkpoint tensor).

⚠ **Verify at the horizon you fit at**: `CosineAnnealingLR`'s `T_max` is the epoch
ceiling, so a 3-epoch and a 30-epoch run share only epoch 0.

**So a before/after across a refit is read against a replicate of the same recipe**
(other seeds, under determinism), never against zero, and **a level never transfers
between two runs**, even of one recipe. Derive it, always. Scoring and seating are
already exact: re-ensembling a stored pool-score block re-solves seat for seat, so a
seating that must come back is one whose column is kept.

### What a rebuild has to match

torch **2.6.0+cu124**, cuDNN **90100**, an **RTX 2060 SUPER**, `cudnn.benchmark` false,
and `CUBLAS_WORKSPACE_CONFIG`. Determinism is a promise about one machine and one build,
not about the recipe.

## Adopted 2026-09-10 — a k=3 ensemble, and a third axis to name it on

The shipped column is the k=3 ensemble of the shipped recipe, fitted under determinism
and reproduced bit for bit by the tracked machinery. Its matched bar is `0.030242`
(11,743 of 42,300 above-bar rows). An average pulls the tails in, so a k=3 column's mass
sits an order lower than a single head's; the gate is the same 27.76%.

**`score-pool` averages k checkpoints over one decode pass**: `train.score_many` returns
each head's probabilities and the caller averages them (a mean of logits would be a
different column). `shipped_runs` answers *which checkpoints is this recipe's column*.

## What is here, and how to run it

`<prefix>bar_auc_ge4.json` and `<prefix>comparison_auc_ge4.json`, each band's bar and
read. `<run>/config.json` (the recipe, including `inherited`: every key carried from the
render judge's config and the ones that were not), `<run>/metrics.json` (epoch trace,
wall clock, held-out read), `<run>/scores.jsonl` (the stopping slice, each row with its
whole join and both of the judge's columns). `gallery_grade.fp16.pt` is the shipped
artifact; `best.pt` / `last.pt` are ignored by `models/**/*.pt`.

```
fractal-wallpapers gallery-grade population    # join the store to the ledger, once
fractal-wallpapers gallery-grade split         # the 80/20, stratified, once
fractal-wallpapers gallery-grade preregister   # the bar, BEFORE any run of its band
fractal-wallpapers gallery-grade band          # every run not on disk, one at a time
fractal-wallpapers gallery-grade read          # the band's table, and the pick
fractal-wallpapers gallery-grade accept        # the band against its bar
fractal-wallpapers gallery-grade score-pool    # the column the cascade order reads
fractal-wallpapers curate seat-sheet --n 1000  # what the two keys disagree about
fractal-wallpapers curate solve run --n 1000 --fine-bar 0.50   # a non-default bar
```

**`score-pool` writes one file and two readers take it**: `cascade_order` lays `p_ge4`
over the rank key, and `solve.at_fine_bar` (`--fine-bar SCORE`) keeps rows at or above
a bar. Both refuse without `pool_scores.jsonl`, and both treat an unread row
conservatively (ordered last, excluded by the bar). The bar is on by default;
`fine_bar=None` in process is the unbarred population (`curation/GALLERY.md`'s *The bar
is a recorded parameter*). The cascade orders on `p_ge4`, not `rank_score`, because the
bar's `AUC(>=4)` is read on that column.

**Cost.** A band is about ten to thirteen minutes of fitting (81–144 s a run) plus a
two-minute streaming pass whose result every run reads from
`artifacts/gallery_grade_head/population.jsonl`. One run at a time is not a knob:
`models/render/README.md`'s *The band, and the study that adopted it* has the commit
charge. `train._pictures` scores at `num_workers=0`; reading a pool through several
checkpoints should share each decoded batch (`train.score_many`), and caching the
stopping slice's deploy-transform decode keeps a fit's epoch short, because a Windows
loader respawns its workers every epoch unless the epoch counter is in shared memory.
