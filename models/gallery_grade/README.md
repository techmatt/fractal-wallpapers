The **fine-tier head**: an order inside the render judge's own flat top. Built on
2026-09-06, adopted by nothing.

The render judge answers *is this picture worth keeping* and saturates at the good
end of its own scale. This head answers *how good, given it already cleared the
bar* — the question the solve has to answer after the gate and has no column for.
It is a **separate network**, same architecture as the render judge and
initialised from its shipped `weights-v6` artifact, fitted on the `gallery_grade`
store's thousand human verdicts at the ledger's 640x360 candidate geometry.

⚠ **Nothing here is wired into anything.** No floor moves, `curation/rank_key.py`
is untouched, the solve and retention do not read it, and it is not on
`models/roster.py`. Adoption is a later question against a bar nobody has written.

## The band, 2026-09-06 — three arms, two seeds

How much trunk to unfreeze was measured rather than argued. Every run is fitted on
**one** split and read on **one** 201-row stopping slice, which is the change from
`render_deploy`'s arrangement and the reason the arms can be compared at all —
that module draws its 80/20 under the run's own seed, so its seeds sit on three
different slices, and `render/README.md` says in as many words that an AP read
across two of them is not a comparison of two heads.

```text
arm          trainable            mean AP(>=3)  best    spread   AUC(>=4)      Spearman
frozen           3,843   0.15%          0.8509  0.8510  0.0002   0.492 0.496   +0.04 +0.05
last_block   1,360,003  54.47%          0.8674  0.8685  0.0022   0.599 0.611   +0.25 +0.27
more         2,496,867 100.00%          0.9084  0.9250  0.0333   0.677 0.715   +0.37 +0.43
```

**`more` wins and the ordering is monotone in how much trunk moves**, on every
statistic and at both seeds. The pick is `more_seed1`, by stopping-slice AP —
the same statistic the epoch was chosen on, so nothing is selected on a number
nothing was stopped on.

The baseline every one of those is read beside, recomputed on the same 201 rows
rather than quoted from anywhere:

```text
                                AP(>=3)   AUC(>=3)   AUC(>=4)   Spearman
judge candidate p_ge4            0.8040     0.574      0.528       +0.090
judge label     p_ge4            0.7995     0.557      0.517       +0.065
base rate >=3                    0.7811
```

`candidate_p_ge4` is the column a seating walks and is the number to beat.
`label_p_ge4` is the same judge on the picture the verdict was actually cast on —
the easier baseline, and it is here so that an arm losing to it cannot be excused
as having lost only to a geometry.

⚠ **`more` is the one arm that does not reproduce.** Fitted twice on identical
data with identical seeds, `frozen` and `last_block` came back bit-identical while
`more` moved its chosen epoch from 16 to 3 and from 11 to 1, at APs within 0.008
either way. The AP surface across epochs is nearly flat for a fully-unfrozen net,
so cuDNN's own nondeterminism decides which epoch wins; **the epoch on the record
is not a reproducible fact about this arm and the AP roughly is.**

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
* **Two seeds, not three**, on Matt's call of 2026-09-06. The split is fixed
  across the grid, so a seed moves only the initialisation's dropout draw and the
  sampler's order. Two says whether an arm's gap beats its own run-to-run spread;
  it cannot put an interval on that spread, and nothing above claims one.
* **The cascade's coverage at the seat is 14.3%.** Over the pool the census of
  2026-09-06 read — 260,862 candidates over 27,903 locations, out of a
  308,419-row ledger — **37,424 rows over 10,585 locations clear their mode's
  bar**, every accepted mode on the default `p_ge4 >= 0.5` and none on the
  fallback. Those are the rows that would carry a defined fine score. On the other
  85.7% this head has no output, because it never saw a row like them.

## The batch effect, after stratification

The three sittings are three slightly different scales — chi-square 30.95 on
6 d.f., p = 2.6e-05 over the store. The split balances their **counts** exactly
(67/67/67 in the holdout, 0.2006/0.2012/0.2012 of each sitting) and cannot balance
their scales, so the drift survives into the holdout's labels at Kruskal
**p = 0.021**. What does *not* survive is any effect on the head: its residual
against the labels is flat across the three, Kruskal **p = 0.63**.

Per sitting, on the picked run — the third is where it does worst, which is the
sitting that piled onto 3 at the expense of 4:

```text
n1000_0906_1   67   mean grade 3.000   AP(>=3) 0.916   AUC(>=4) 0.717   rho +0.488
n1000_0906_2   67              3.284           0.949            0.730       +0.420
n1000_0906_3   67              2.970           0.903            0.655       +0.295
```

## What is here

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
fractal-wallpapers gallery-grade population   # join the store to the ledger, once
fractal-wallpapers gallery-grade split        # the 80/20, batch-stratified, once
fractal-wallpapers gallery-grade band         # every run not on disk, one at a time
fractal-wallpapers gallery-grade read         # the table above, and the pick
```

The whole grid is **ten minutes of fitting** on this box — six runs at 81–133 s each, plus a
two-minute streaming pass over the ledger that every run afterwards reads from
`artifacts/gallery_grade_head/population.jsonl`. One run at a time is not a knob;
`render/README.md`'s note on this machine's commit charge is why.
