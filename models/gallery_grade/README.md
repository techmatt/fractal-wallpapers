The **fine-tier head**: an order inside the render judge's own flat top. Built
2026-09-06 and **adopted 2026-09-07**, Matt's ruling on its pre-registered bar;
**refitted on the corrected corpus and re-adopted 2026-09-09** — same
architecture, same rule, 1,750 rows instead of 1,000. What ships is
`corrected_auc_ge4_more_seed1`.

The render judge answers *is this picture worth keeping* and saturates at the good
end of its own scale. This head answers *how good, given it already cleared the
bar* — the question the solve has to answer after the gate and has no column for.
It is a **separate network**, same architecture as the render judge and
initialised from its shipped `weights-v6` artifact, fitted on the `gallery_grade`
store's thousand human verdicts at the ledger's 640x360 candidate geometry.

⚠ **One reader, and it is the seating.** `solve.DEFAULT_KEY` is
`solve.CASCADE_KEY`, so an unflagged `curate solve run` orders on this head above
the bar. Everything else is where it was: `curation/rank_key.py` is untouched,
retention does not see it, `_prune_ranks` is unchanged, no bar or floor reads it,
and it is not on `models/roster.py` — that roster is heads a **render** goes
through. Adoption moved one constant and nothing else, which is the shape to keep:
what a prune keeps stays a separate question from what a gallery seats.

## Two bands, and the second one is the head

```text
band       stopping rule                       arms                    what it was for
ap_ge3     the shipped judge's, carried whole  frozen/last_block/more  the build
auc_ge4    this head's own boundary            last_block/more         the refit
```

**`ap_ge3` is the wrong boundary for this head and its own band is what proved
it.** An order inside the gate's top is 3-against-4, and `last_block_seed0` peaked
`AUC(>=4)` at 0.66 on an epoch whose `AP(>=3)` had dipped — the rule and the job
disagreeing inside one run. The first band's directories keep their bare
`<arm>_seed<N>` names because their records are on disk under them; every later
band prefixes its own.

`frozen` is not in the second band. It read `AUC(>=4)` 0.492 and 0.496 in the
first — chance, and *below* the judge's own 0.528 — so a linear read of the frozen
trunk has nothing to say about this boundary, and fitting it again would buy a
third row saying so.

## The refit: `auc_ge4`, 2026-09-06

Three seeds an arm, one split, one 201-row stopping slice.

```text
arm          trainable          mean AUC(>=4)  best    worst   spread  Spearman        epoch
last_block   1,360,003 54.47%         0.6454  0.6599  0.6308  0.0292  +.26 +.28 +.30   3,4,6
more         2,496,867  100.0%        0.7184  0.7193  0.7170  0.0023  +.40 +.40 +.43   7,7,7
judge candidate p_ge4                 0.5278                          +.090
shipped rank_key                      0.5434                          +.138
```

**`more` wins on the mean and ships its MEDIAN seed** — `auc_ge4_more_seed2`, not
the argmax. That rule is why the band runs three seeds: the first band showed
`more`'s AP surface flat enough across epochs that cuDNN nondeterminism moved the
chosen epoch from 16 to 3 between two identical runs, so the best of three seeds
is a coin flip rather than a fact about the arm.

⚠ **Stopping on the right boundary made the arm reproducible.** `more`'s spread
was **0.0333** under `ap_ge3` and is **0.0023** here, and all three seeds land on
epoch 7 where the first band's landed on 1 and 3. The flat surface was the rule's,
not the arm's.

## The bar, registered before the band existed

`bar_auc_ge4.json`, written before any run of this band was fitted;
`comparison_auc_ge4.json` is the read. The winning arm had to beat **both**
incumbents — the judge's own `p_ge4` column and the shipped `rank_key` a seating
actually ranks on — on **both** `AUC(>=4)` and Spearman against the grades, at
**every** seed. Twelve gated cells, no partial credit and no best-of.

**CLEARED, 12 of 12, worst margin +0.1735.** Against `rank_key`, the harder of the
two: `AUC(>=4)` +0.174 to +0.176 and Spearman +0.267 to +0.292 across the three
seeds. Both incumbents' heights are copied into the bar rather than referenced, so
a later re-fit of `rank_key` cannot move the height this band was judged at.

Naming both incumbents is `curation/render_grade.py`'s correction applied
unchanged: an arm that beat the judge's column and lost to the shipped key would
have improved nothing anybody ships.

## A corpus is which rows; a band is which stopping rule

Two axes, and until 2026-09-09 there was only ever one value on the second, so the
run names carried the band alone. The correction sitting made the distinction
load-bearing: a refit on a grown store is a different **corpus** under an unchanged
**rule**, and re-fitting under one name would have overwritten the join and the
split that `auc_ge4_more_seed2` — the run a seating orders on — refers to. A run on
disk that nothing can reproduce, with nothing looking broken.

```text
corpus       what it holds                                            file names
as_built     the three sittings of 2026-09-06, 1,000 rows             bare
corrected    every graded row, the 2026-09-09 sitting included        `corrected_` prefixed
```

`--corpus` is on **every** verb, `read` and `accept` included, so that a join, a
split, a bar and a run each say which rows they are about. ⚠ **The default is the
ADOPTED corpus and not the newest one** — `score-pool` writes the column a seating
orders on, so a default pointing at a staged refit would let an adoption happen by
forgetting a flag. Moving `CORPUS` is part of adopting a refit.

`as_built` **names its three batches** rather than excluding the new one, so
re-running its population gives the file it gave in 2026-09-06.

## What augmentation the recipe applies, transform by transform

Carried whole out of `render.fp16.pt` and recorded in the config only as the one
line *geometric only — border crop and both flips*, which is true and is not enough
to reason about. Read off the `head.Transform` `fit` actually constructs, it is:

```text
1 border crop     uniform(0, 0.05) PER EDGE, independently, rounded to pixels.
                  On a 640x360 candidate: up to 32 px off each of left and right,
                  18 off each of top and bottom. Mean retained area ~90%,
                  worst case ~81%. Skipped for a picture the crop would leave
                  under 8 px of.
2 resize          bicubic STRETCH to 384x224. Deterministic, and the same call at
                  deploy — which is the whole reason it is a function of its own.
3 horizontal flip p = 0.5
4 vertical flip   p = 0.5
5 JPEG re-encode  OFF   (`jpeg=None` at the call site)
6 brightness      OFF   (`brightness=0.0`)
7 contrast        OFF   (`contrast=0.0`)
8 normalize       ImageNet-12k mean/std off the backbone's own data config
```

Beside it, and part of the same answer: dropout 0.20, stochastic depth 0.10, weight
decay 0.05, grad clip 1.0, cosine 2e-4 backbone / 1e-3 head, batch 32, sqrt class
balance × per-place weight, and `more` is every parameter.

**The three that are off are off by ruling, not by accident** — `models/head.py`'s
*The transform is the same core in training and at deploy*: for a render judge the
palette is part of the label, so a colour jitter would move the answer with the
picture. A study that wants a colour axis here has to argue with that first, and
`scratch/augmentation_sweep_20260910_report.md` is where the ±1° and ±3° Oklab
probes landed — a mean ΔE of 0.0015 and 0.0046, far below anything a person could
respond to, so those two arms measured nothing and are not evidence either way.

## The refit on `corrected`, ADOPTED 2026-09-09

1,750 rows over 1,462 locations, 1,358 lineages; the split redrawn over everything
at 1,400 / 350. **No number here is comparable with the build corpus's**: the
201-row slice is gone and the 350-row one is not a superset of it.

```text
arm          mean AUC(>=4)  best    worst   spread   epochs
last_block          0.6695  0.6795  0.6537  0.0258   7, 8, 4
more                0.7113  0.7272  0.6959  0.0313   3, 6, 11
```

`more` wins the mean again and ships its median seed, `corrected_auc_ge4_more_seed1`
at epoch 6. **CLEARED, 12 of 12, worst margin +0.085** against
`corrected_bar_auc_ge4.json`, registered before any run of the band existed.

⚠ **The reproducibility the build corpus credited to the stopping rule did not
survive the corpus change.** `more`'s spread was 0.0023 on `as_built` under this
same rule and is **0.0313** here, and the three seeds land on epochs 3, 6 and 11
where they all landed on 7 before. The flat surface was not the rule's alone, and
the median pick is doing more work on this corpus than on the last one.

### Adopted 2026-09-09 — the column stayed, the level was re-matched

Matt's ruling. Three acts and none of them is the others: `CORPUS` moved to
`corrected`, the pool was re-scored through `corrected_auc_ge4_more_seed1`, and
`solve.DEFAULT_FINE_BAR` moved **0.50 → 0.184**.

⚠ **0.184 is a MATCHED constant, not a discovered one.** It is the level at which
the refit admits the same fraction of the pool the shipped head admitted at 0.50
— 27.76%, measured on the seed-`20260909` 8,000-row sample of that day's
above-bar pool. It was calibrated, not derived, and a reader must not take three
digits as three digits of meaning. It was fitted to one sample of one pool on one
day; **mining into the thin cells will quietly stop the match holding**, and the
right response to a drift is to re-derive against a fresh sample and read the
drift as information about the pool.

⚠ **The gate did not move.** The refit reads the pool far more strictly on this
column — 9.6% of that sample clears 0.50 against 27.8% — so holding the flag at
0.50 would have been a large unruled tightening dressed as continuity. Because
the admitted fraction is held, **the refit's benefit is in the ORDER inside the
admitted pool and not in a narrower admission**. A gallery taken after this act
is drawn from a same-sized population through a different ordering; any reading
of it as *choosier* is a reading nothing here supports.

**The column stayed `p_ge4`**, and the alternatives were measured rather than
assumed. At equal 27.76% admission, read on the corrected stopping fold:

```text
column        level    recall of 4s   4s among admitted   >=3 among admitted
p_ge4        0.1840          0.742              37.7%              70.9%
sqrt(p3*p4)  0.3249          0.708              37.7%              70.7%
rank_score   1.7416          0.663              38.6%              75.8%
p_ge3        0.6570          0.596              39.6%              76.9%
```

`p_ge4` keeps the most labelled 4s at equal admission and ties on 4-precision;
the trade the other columns offer is *fewer 1s and 2s for fewer 4s*. Two things
settled it beyond the table. **`p_ge3` is not a gated column** — `AUC(>=3)` was
never one of the two statistics this band's bar was stated on, where `p_ge4`
(AUC) and `rank_score` (Spearman) both are. And a level is a recorded parameter
where a column is a code change in `solve.at_fine_bar` plus a second ruling.
On the 111 rows held out by *both* splits the recall gap between the columns is
2 rows against 5 out of 35, which is not a difference worth either.

⚠ **`config.fine_head` is new and `config.fine_bar` cannot be read without it.**
0.50 under `auc_ge4_more_seed2` and 0.184 under `corrected_auc_ge4_more_seed1`
admit the same fraction; 0.50 under the second admits a third of it. A record
that does not name the field was taken before 2026-09-09 under the shipped head.

**The superseded scores are kept.** `score_pool` moves the live
`pool_scores.jsonl` to `pool_scores_<run>.jsonl` before writing — automatic, not
a flag, because every solve record ever taken resolves its cascade order out of
that one file and a silent overwrite would make `20260909T215815Z` and every
record before it unreproducible with nothing looking broken.

#### The admitted SET churned 93.3% while its size did not move

Over the whole re-scored pool — 42,300 rows, the exhaustive census rather than the
8,000-row sample the level was matched on — the shipped head admitted **11,637 rows
(27.51%)** at 0.50 and the adopted head admits **11,824 (27.95%)** at 0.184. The
match survives the census with a drift of **+0.44 points**, which is what says the
level stands unadjusted.

⚠ **Only 6,302 rows are admitted by both.** 5,335 leave and 5,522 arrive — a 93.3%
symmetric churn against the old admitted set. So a gallery taken after this act is
**a different pool of the same size, not a re-ranking of the old one**, and that is
a stronger statement than *the order inside the admitted pool changed* above: barely
half the pool being ordered is the pool that was there before. Any before/after
across the adoption compares two populations, and a seat that moved cannot be
attributed to the ordering without checking that both rows were admitted on both
sides.

#### Distinct places FELL while admitted rows rose, and nothing has been ruled on it

**6,683 → 6,235**, a loss of **448 distinct locations available to a seating**, at the
same time as admitted rows went 11,637 → 11,824. The refit's admitted set is simply
more concentrated per place: **1.90 rows a place against 1.74**.

**Recorded as an open observation and not as a problem.** It was not predicted, and
it is the one number in the adoption that could bind, because one seat per cluster
makes *places* and not rows the currency a seating spends — see `curation/GALLERY.md`'s
*What actually holds a thin colour down, and it is NOT the ceiling*, where clusters
are already the binding fact at n=1000. Nothing has been measured about what 448
fewer places costs a solve, and no ruling has been asked for. The thin cells
separately got **better** off in places under the refit and are reordered sharply
among themselves — `light_muted_blue` 146 → 405 and `dark_vivid_cyan` 106 → 221
against `dark_vivid_lime` 50 → 52 — so the loss is not concentrated where the colour
floor draws.

### What it does at `p_fine >= 0.50`, which is a fixed constant on a moved scale

**Recall of labelled 4s at the bar: train 0.663, stopping 0.405, gap 0.258.** The
train arm is the sanity arm and it is the reading to notice — a head with the
capacity to overfit 1,400 rows would sit near 1.0 and this one cannot fit two of
every three of its own training 4s. Per block the gap is **0.03** inside
`top_band` and **0.03** inside `floor_thin_cell`, and **0.317** on the
pre-existing rows: it is concentrated exactly where the sitting's exclusion left
old 4s beside new downward corrections at similar pictures.

⚠ **The head got much stricter and 0.50 did not.** Over a seeded 8,000-row sample
of the above-bar pool the clearing fraction goes **27.8% → 9.6%**, the median
reading 0.104 → 0.088 and the 75th percentile **0.581 → 0.207**. The level that
clears the same *count* on that sample is **0.184**. So a solve that keeps
`--fine-bar 0.50` against this head is applying a materially tighter cut than the
same flag applied to the shipped one, without the flag having moved.

### The bar is stated over the gate column, because a fifth of the slice has none

The sitting's 100 `low_anchor` rows are coarse-3 verdicts about 1280x720 pictures
that were **never candidates**, so they carry no `selected_on.p_ge4` — and neither
incumbent exists for them. 330 of the 350 stopping rows carry the column.

The baseline used to **refuse** a column absent anywhere and now **drops and
counts**, which is [`_rank_key_baseline`]'s own rule applied to its sibling; and
each run records `held_out_on_the_gate_column` beside `held_out`, so a bar stated
over that slice reads the arm there too. **Two populations must never wear one
number**: on `as_built` the two reads are the same 201 rows and the key is absent
from those records, which is what `acceptance` falls back on.

## What the cascade actually does to a gallery

⚠ **It is not a reordering of the top.** One pool solved twice at n=1000, once
under `rank-key` and once under `cascade`: the two shared **175 seats of a
thousand** on the pool of 2026-09-06, and **173** on the 272,457-row pool of
2026-09-07. 827 arrive and 827 depart.

That was the number in front of Matt when he **adopted it on 2026-09-07**. The head
clears its bar on the rows a person graded, and what it does to a gallery is
replace five-sixths of it — which is a question about taste that no statistic on
this page answers, and the ruling answered it.

**Where the five-sixths goes, measured 2026-09-07 at n=1000.** Of the 827 departing
seats, **166** are a different candidate at a location the cascade still seats and
**661** are a location that leaves the gallery altogether; the arriving side mirrors
it. One wallpaper per location is permanent, so those are the only two cases, and
the second is much the larger: this head is mostly changing *where* the gallery
looks, not which colouring of a place it prefers. It is not the two-stage constant
doing it — **both** arms seat 1,000 of 1,000 above the bar, so both were choosing
out of the same 38,884 rows. `curation/GALLERY.md`'s *`cascade` is the default
since 2026-09-07* carries the split.

**The cascade orders on the head's `p_ge4` and not on its `rank_score`**, because
`AUC(>=4)` — the statistic the bar is stated on — is read on that column. The two
order the above-bar pool at Spearman **0.92**, so they are genuinely different
orders; on this pool the difference is worth two seats of a thousand, which is
small and is not the reason to prefer the gated one.

```
artifacts/curation/seat_sheet/cascade_vs_rank_key/sheet.html   4.2 MB, 150 cards
```

150 of the 1,650 changed rows, sampled evenly across the fine head's score range
rather than off the top, sorted good to bad and marked arriving or departing. The
ledger's stored 640x360 pictures, nothing re-rendered. It ingests nowhere and is
not a label instrument — the captions are open so it cannot be read as one.

## The level reads as a quality target, Matt's ruling of 2026-09-07

**`p_ge4 >= 0.5` on this head may be read as an absolute quality target and not
only as a point in a ranking.** Matt's ruling, 2026-09-07, taken by eye: he checked
seat quality on the cascade's own galleries and is willing to treat a half on this
column as *this picture is good enough to seat*, rather than treating the head as a
pure order whose heights mean nothing on their own. **He will revisit it if
galleries produced under that reading come out bad**, which is the only thing that
would settle it — nothing on this page does.

⚠ **A ruling about a level is a ruling about THIS head's scale, and the head
has been replaced.** The `corrected` refit reads 9.6% of a pool sample at or
above 0.50 where the shipped head read 27.8%, so *this picture is good enough to
seat* names a different picture on it. **The 2026-09-09 adoption moved the
seating level to 0.184 to hold the admitted fraction**, which means the level a
solve cuts at is now a matched constant rather than a quality target read off
this column — see *Adopted 2026-09-09* above. Whether **0.184 on the refit** may
be read the way 0.50 on the shipped head was is a question this ruling does not
answer and Matt has not been asked.

⚠ **This supersedes the ckpt-113 line, which said the level was untrusted.** The
head shipped as an order inside a gate's top and was adopted on `AUC(>=4)` and
Spearman, both rank statistics, so until this ruling the honest statement was that
its heights had no meaning off the ranking. A later reader will otherwise take the
older line as current, which is why the ruling is written here and dated.

Nothing in the code changed with it: `solve.CASCADE_KEY` still lifts an above-bar
row to `1 + <fine p_ge4>` and orders on it, no bar or floor reads this head, and
`floors.ACTING_RELEASE_BARS` is untouched. It is a rule for **reading** the column
— what a 0.0018 seat in the weakest-twenty table means — and if it is ever wired
into a cut, that is a second ruling and a `Restatement`.

## What every number here is, and is not

* **The 20% is the stopping slice and it is also the only held-out number there
  is.** That is the shipped recipe's own trade, carried unchanged: the holdout's
  one job is to stop the run. Every figure above is optimistic by exactly one
  early stop.
* **The store is not eval-eligible and nothing here is a base rate.** Its
  population is 700 seats plus 300 runners-up, one row per location, with no
  colour-ceiling representation — a ranker among rows at one location and nothing
  more. `data/gallery_grade/README.md` states the three separations that hold it
  apart from the two quality corpora. That is a statement about the **corpus** and
  it is unchanged; what a reader may do with the head's **heights** is the ruling
  above.
* **The `ap_ge3` band ran two seeds** on Matt's call and `auc_ge4` runs three,
  which is what makes a median pick possible. The split is fixed across a grid
  either way, so a seed moves only the initialisation's dropout draw and the
  sampler's order. Three seeds still cannot put an interval on that spread, and
  nothing above claims one.
* **The cascade's coverage at the seat is 14.3%.** Over the pool of 2026-09-06 —
  260,862 candidates over 27,903 locations, out of a 308,419-row ledger —
  **37,424 rows over 10,585 locations clear their mode's bar**, every accepted
  mode on the default `p_ge4 >= 0.5` and none on the fallback. Those are the rows
  `score-pool` reads and the only ones the cascade orders. On the other 223,438
  this head has no output, because it never saw a row like them, and nothing is
  written for them: a score that exists only to be misread is worse than a gap.
  **Re-read on the 2026-09-07 pool — 277,542 candidates, 40,127 clearing — the
  cover is not merely equal in count but equal as a SET**: `clearing` and
  `above_bar` are the same 40,127 rows, again with every accepted mode on the
  default rule and none on the fallback. So a filter on `p_fine` narrows the
  seatable pool and can never be a coverage hole wearing one, which is what makes
  a filtered re-solve interpretable at all
  (`curation/GALLERY.md`'s *A `p_fine` bar on the view raises the objective and
  deletes the worst fifth*).

## The batch effect, after stratification

**Since 2026-09-09 the split balances the SHEET, the BLOCK and the GRADE**, not the
batch. The sheet refines the batch — every sheet sits inside exactly one batch, so
balancing sheets balances batches by summation — and it is the finer constraint the
correction sitting needed: its three cuts disagree at chi-square 69.39 over 750
rows, inside a single batch, where the 2026-09-06 sittings disagreed across three.
The block is there because a blocked draw's four populations run from mean grade
1.18 to 2.69, and the grade because block balance does not imply grade balance. All
three are **marginals rather than the cross**, filled greedily with lineages taken
whole; on `corrected` the worst marginal lands at 0.195 against a target of 0.200.

⚠ **A stratum is read by the SPLIT and never by the model.** Matt's ruling of
2026-09-09: the sheets' disagreement is accepted as label noise — no sheet term, no
reweighting, no exclusion. What the balance buys is that a train-against-stopping
gap moves for fit and not for which cuts landed on which side.

The three sittings are three slightly different scales — chi-square 30.95 on
6 d.f., p = 2.6e-05 over the store. The split balances their **counts** exactly
(67/67/67 in the holdout, 0.2006/0.2012/0.2012 of each sitting) and cannot balance
their scales, so the drift survives into the holdout's labels at Kruskal
**p = 0.021**. What does *not* survive is any effect on the head: its residual
against the labels is flat across the three, Kruskal **p = 0.35** on
`auc_ge4_more_seed2` and p = 0.63 on the first band's pick.

Per sitting, on `auc_ge4_more_seed2` — the third is where it does worst, which is
the sitting that piled onto 3 at the expense of 4:

```text
n1000_0906_1   67   mean grade 3.000   AP(>=3) 0.865   AUC(>=4) 0.722   rho +0.423
n1000_0906_2   67              3.284           0.932            0.751       +0.434
n1000_0906_3   67              2.970           0.890            0.637       +0.340
```

## What is here

`bar_auc_ge4.json` and `comparison_auc_ge4.json`, the band's bar and its read.
`<arm>_seed<N>/config.json` — the recipe that run was fitted under, including
`inherited`, which lists every key carried out of `render.fp16.pt`'s own config
and the three that were not. `<arm>_seed<N>/metrics.json` — the epoch trace, the
wall clock and the held-out read. `<arm>_seed<N>/scores.jsonl` — that run's read
of the stopping slice, one row per picture carrying its whole join and **both** of
the judge's columns under names that say which geometry each is.

The weights are not tracked: `best.pt` and `last.pt` sit in each run directory and
are ignored by the same `models/**/*.pt` rule every other head's are. There is no
`fp16` artifact and no entry in `models/weights.json`, because nothing ships.

```
fractal-wallpapers gallery-grade population    # join the store to the ledger, once
fractal-wallpapers gallery-grade split         # the 80/20, stratified, once
fractal-wallpapers gallery-grade band --corpus corrected       # a refit's own files
fractal-wallpapers gallery-grade preregister   # the bar, BEFORE any run of its band
fractal-wallpapers gallery-grade band          # every run not on disk, one at a time
fractal-wallpapers gallery-grade read          # the table above, and the pick
fractal-wallpapers gallery-grade accept        # the band against its bar
fractal-wallpapers gallery-grade score-pool    # the column the cascade order reads
fractal-wallpapers curate seat-sheet --n 1000  # what the two keys disagree about
fractal-wallpapers curate solve run --n 1000 --fine-bar 0.50   # the same column as a BAR
```

**`score-pool` writes one file and two readers take it.** `cascade_order` lays
`p_ge4` over the top of the rank key, and `solve.at_fine_bar` — `--fine-bar SCORE`,
since 2026-09-07 — narrows the seatable pool to the rows reading at or above a bar
on the same column. Both refuse without `pool_scores.jsonl` rather than falling
back, and both take an unread row the conservative way: the order leaves it behind
every row the head could read, and the bar excludes it. **The bar is off by
default** and this head's adoption did not change that —
`curation/GALLERY.md`'s *The bar is a recorded parameter and the default is still
no bar*.

Each band is **ten to thirteen minutes of fitting** on this box — a run is
81–144 s — plus a two-minute streaming pass over the ledger that every run
afterwards reads from `artifacts/gallery_grade_head/population.jsonl`. Reading the
above-bar pool through the picked run is **320 s for 37,424 pictures**, and the
two solves behind the seat sheet are about a minute each. One run at a time is not
a knob; `render/README.md`'s note on this machine's commit charge is why.

**That pool pass is decode-bound and `score_pool` pays it single-threaded.**
`train._pictures` uses `num_workers=0`, which is right for a scorer that runs once;
it is the wrong shape for reading a pool through *several* checkpoints, and the
difference is not marginal. Measured 2026-09-10 on the same 42,300 above-bar rows:
**345 s** through `score-pool`, against **91 s** for a pass at six workers that puts
three checkpoints on each decoded batch before dropping it — one decode, three
columns. An ensemble read one checkpoint at a time costs `k` × 345 s and buys
nothing; the pattern is in `scratch/aug_sweep_0910/score_many.py`. The same trick is
worth more inside a fit: caching the deploy-transform decode of the stopping slice
took an epoch of the fine head from 30 s to 5 s, because a Windows loader **respawns
its workers every epoch** unless the dataset's epoch counter lives in shared memory.
