One head over both kinds — candidates, measured against the two that ship.

`smooth_render` judges the smooth coloring as a wallpaper; `strange_render` judges
the other seventeen as renderings. Both take a finished picture and answer on the
same 1–4 scale, under recipes that differ in exactly one behavioural key. So the
question is whether the split is load-bearing: would **one** head over the pooled
stores judge each kind as well as that kind's own head does? If it would, the
system is simpler by one store boundary, one release artifact, one floor to
calibrate and one recipe to keep in step.

**Nothing here is adopted, and nothing here ships.** `joint_render` is on no
roster, in no release manifest and in no serving path. The shipped heads, their
floors, their acceptance records and every wire in the supply and curation paths
are untouched by this directory's existence.

## Two candidates, because the backbone could not be inherited

The two incumbent recipes agree on every behavioural key **but the backbone** —
medium for smooth renders, small for strange — and one head has one backbone. That
value is therefore a choice rather than an inheritance, and it has been asked
twice. Each candidate is a whole design plus the runs that realize it, each has
its own bar written before its band existed, and each keeps its own record: a
superseded candidate's read stays exactly as it was read.

```text
medium          bar.json                 comparison.json                 FAIL
small_backbone  bar_small_backbone.json  comparison_small_backbone.json  FAIL (see below)
```

`CURRENT` in `joint_render.py` names the one a bare read is about.

## The bar is non-inferiority, which is a ratified deviation

Every other bar in this project asks a candidate to win something. This one asks
only that nothing was paid: the candidate is viable iff **no gated arm is
significantly worse** than that kind's shipped head, at 95% on a paired cluster
bootstrap, per seed and on the band. The benefit being bought is one head instead
of two, and no sheet can measure that — Matt ratified the benefit, and the
measurement is asked only about the cost.

**Both readings are reported, and on the second candidate they disagree.** The
strict conjunction runs one test per gated arm per seed — five arms, three seeds,
fifteen one-sided 2.5% tests — so a candidate that is *exactly* non-inferior
everywhere still trips at least one about **31.6%** of the time. `multiplicity`
in the record carries that arithmetic beside the verdict. It changes no verdict;
the bar is the bar.

## What runs, and in what order

```
fractal-wallpapers joint train --run small_backbone_seed0 --seed 0 \
    --backbone mobilenetv4_conv_small.e2400_r224_in1k
fractal-wallpapers joint score --run small_backbone_seed0     # both sheets, ~30 s
fractal-wallpapers joint compare                              # the CURRENT candidate
fractal-wallpapers joint disagreements                        # pictures into scratch/
```

Three seeds, and **the band is the result** — there is no staged pick, because
nothing is being staged. A joint seed is ~45 min on one RTX 2060, or ~52 min with
two training at once.

**Two runs at a time is the right way to spend this machine.** The pipeline is
data-loading bound, not compute bound: the GPU sits at ~20% and an epoch costs
~68 s alone against ~80 s with a second run beside it, so two streams finish
1.68x the work. Both render caches have to be **hot** first — training refuses
when either resolves through the archive, and `storage restore renders` is the one
command that fixes it (3.9 GiB over 8,021 files, under two minutes).

## What the two bands found

The first band failed, unanimously, on the strange proper scoring rule (+0.124
[+0.040, +0.216]). **It was not pooling.** The ablation arm (`--only <kind>`,
which trains one kind's share of exactly the pooled split) showed cross-entropy
monotone in how much is shared — medium backbone on strange rows alone
0.639/0.680, pooled 0.422/0.487/0.450 — so pooling *helps*, significantly, and
2,935 strange rows simply under-feed the medium backbone.

The second band re-asked the backbone. Every gated arm passes on the band, and
`strange_scoring_rule` — the arm that failed unanimously before — reads −0.025
[−0.077, +0.027]. One seed of one arm crosses under the strict conjunction, at a
CI upper bound of −0.0036 on a boundary with six positives, which is what makes
the two readings disagree.

## The variants

Each moves ONE thing and each is **reported, never gated** — a bar is written
about one design, and a bar a different design could satisfy is not a bar. Every
variant names the candidate it varies and shares that candidate's backbone, so
the comparison moves one thing rather than two.

```
fractal-wallpapers joint train --run two_head_small_seed0 --seed 0 --two-head \
    --backbone mobilenetv4_conv_small.e2400_r224_in1k
```

`--two-head` is one backbone with **two last layers**, one ordinal head per kind.
It needs no new module: a CORN head over `classes` tiers emits `classes - 1`
logits, and one `Linear` of twice that width IS two independent heads — the rows
of a linear map do not interact, and an example of one kind reaches only its own
kind's rows. `cutpoints_of` is the gather, and the suite asserts the gradient
isolation rather than assuming it. It is **conditioned** and the candidates are
not: it has to be told which kind it is reading.

At the medium backbone it lost by +0.101, and that gap is **entirely scale** —
+0.1008 = −0.0026 order + 0.1034 scale, with every order term and every AUC flat.
At the small backbone the gap vanishes: paired seed for seed on the strange sheet
it is −0.016 / +0.015 / +0.024, all three FLAT. So the shared classifier's
apparent regularisation was standing in for data, not for thresholds.

## Loss aggregation is at parity between the arms, and that is checked

The failure it forecloses: if the shared arm took one mean over the pooled batch
while the split arm took a mean **per kind** and summed them, the rarer kind's
head would carry an effective weight of `n_pooled / n_kind` — about 2.6x for
strange — and the two arms would differ in learning rate rather than in
architecture. Both reach one `corn_loss` through one call site, and every row's
weight is `1 / (tasks x pooled subset size)` whatever kind it is; the suite proves
it at the derivative. Batch *sequences* do differ, because a wider classifier
consumes more RNG at init — inherent to changing an architecture, and what a seed
band is for. Grad-clip is on the global norm and the classifier is 0.045% to
0.090% of the medium head's parameters, 0.152% to 0.30% of the small one's.

## Which boundary each sheet may be read at

```text
blind_minibrot  197 rows   2:6  3:95  4:96      gated at >=4, reported at >=3
blind_modes     150 rows   1:74 2:70  3:2  4:4  gated at >=2 and >=3
```

`blind_minibrot` holds no tier-1 row, so its `>=2` AUC is **undefined** rather
than perfect, and it is refused by name. Its `>=4` cross-entropy is dominated by
the smooth incumbent's own calibration on a sheet enriched 3.95x, so **any** head
"wins" there by being less under-confident — that arm is read for a cross-model
claim only recalibrated.

`blind_modes` is **never read at `>=4`**. A later anchored pass revised four rows
from 3 to 4, and those four are the entire `>=4` positive class — an AUC over them
is an AUC over the only non-blind rows on a blind sheet. But the same revision
moved them **within** the `>=3` class, so that boundary's positive set is
identical before and after (six rows either way) and gating there is sound. The
two facts look alike and the suite guards both. The sheet holds 154 rows resolving
to 150, with **four** superseded — not six.

## What is here

`bar*.json`, the bars. `<run>/config.json` and `<run>/metrics.json`, the recipe
and the run. `<run>/scores_smooth_render.jsonl` and
`<run>/scores_strange_render.jsonl`, that run's read of each sheet with every row
carrying its whole join. `comparison*.json`, the reads against the bars. The
weights are `best.pt` and `last.pt` and are not tracked — the same rule that keeps
every other head's out.
