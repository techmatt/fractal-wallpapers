The **fine-tier head**: an order inside the render judge's own flat top. Built
2026-09-06, **not adopted** — the wiring is staged behind a flag that is off.

The render judge answers *is this picture worth keeping* and saturates at the good
end of its own scale. This head answers *how good, given it already cleared the
bar* — the question the solve has to answer after the gate and has no column for.
It is a **separate network**, same architecture as the render judge and
initialised from its shipped `weights-v6` artifact, fitted on the `gallery_grade`
store's thousand human verdicts at the ledger's 640x360 candidate geometry.

⚠ **Nothing reads it.** `curation/rank_key.py` is untouched, retention does not
see it, `_prune_ranks` is unchanged, and it is not on `models/roster.py`.
`solve.CASCADE_KEY` is the flag an adoption would flip and `solve.DEFAULT_KEY` is
still `rank-key`.

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

## What the cascade actually does to a gallery

⚠ **It is not a reordering of the top.** One pool solved twice at n=1000, once
under `rank-key` and once under `cascade`: the two share **175 seats of a
thousand**. 825 arrive and 825 depart.

That is the number to have in front of you before adopting anything here. The head
clears its bar on the rows a person graded, and what it does to a gallery is
replace five-sixths of it — which is a question about taste that no statistic on
this page answers.

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

## What every number here is, and is not

* **The 20% is the stopping slice and it is also the only held-out number there
  is.** That is the shipped recipe's own trade, carried unchanged: the holdout's
  one job is to stop the run. Every figure above is optimistic by exactly one
  early stop.
* **The store is not eval-eligible and nothing here is a base rate.** Its
  population is 700 seats plus 300 runners-up, one row per location, with no
  colour-ceiling representation — a ranker among rows at one location and nothing
  more. `data/gallery_grade/README.md` states the three separations that hold it
  apart from the two quality corpora.
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

## The batch effect, after stratification

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
fractal-wallpapers gallery-grade split         # the 80/20, batch-stratified, once
fractal-wallpapers gallery-grade preregister   # the bar, BEFORE any run of its band
fractal-wallpapers gallery-grade band          # every run not on disk, one at a time
fractal-wallpapers gallery-grade read          # the table above, and the pick
fractal-wallpapers gallery-grade accept        # the band against its bar
fractal-wallpapers gallery-grade score-pool    # the column the cascade order reads
fractal-wallpapers curate seat-sheet --n 1000  # what the two keys disagree about
```

Each band is **ten to thirteen minutes of fitting** on this box — a run is
81–144 s — plus a two-minute streaming pass over the ledger that every run
afterwards reads from `artifacts/gallery_grade_head/population.jsonl`. Reading the
above-bar pool through the picked run is **320 s for 37,424 pictures**, and the
two solves behind the seat sheet are about a minute each. One run at a time is not
a knob; `render/README.md`'s note on this machine's commit charge is why.
