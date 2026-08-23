One head over both kinds — a candidate, measured against the two that ship.

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

## The bar is non-inferiority, which is a ratified deviation

Every other bar in this project asks a candidate to win something. This one asks
only that nothing was paid: the candidate is viable iff **no gated arm is
significantly worse** than that kind's shipped head, at 95% on a paired cluster
bootstrap, per seed and on the band. The benefit being bought is one head instead
of two, and no sheet can measure that — Matt ratified the benefit, and the
measurement is asked only about the cost.

`bar.json` is that bar as a file, written before any score existed; `read` loads
it and may not invent one. `comparison.json` is what it says about the band.

## What runs, and in what order

```
fractal-wallpapers joint train --run seed0 --seed 0     # ~50 min on one RTX 2060
fractal-wallpapers joint score --run seed0              # both sheets, ~30 s
fractal-wallpapers joint compare                        # the band against both incumbents
fractal-wallpapers joint disagreements                  # pictures into scratch/
```

Three seeds, and **the band is the result** — there is no staged pick, because
nothing is being staged. Every arm is read on each seed and on the band's median
seed by that arm's own statistic.

Both render caches have to be **hot** before any of this: training refuses when
either resolves through the archive, and `fractal-wallpapers storage restore
renders` is the one command that fixes it. The two caches together are 3.9 GiB
over 8,021 files and restore in under two minutes from the external disk.

The first read of this bar says **FAIL**, on one arm unanimously: the candidate is
worse than the strange incumbent on the proper scoring rule, on the band and on
all three seeds (+0.124 [+0.040, +0.216]). Three further gated arms fail only under
the strict per-seed conjunction, where one seed of three crosses while the band
does not. Read the variants below before reading that as a verdict about pooling.

## The ablation arm, and what it found

`--only <kind>` trains one kind's share of *exactly* the pooled split, under exactly this
recipe. The filter is applied after every side is decided, so the ablation's training side
is the pooled training side intersected with a kind and its selection slice is the pooled
slice intersected with the same kind. Drawing a slice over one kind's own places would
move two things at once.

It exists because two things changed alongside pooling and neither is pooling: the smooth
store grew after its incumbent trained, and the strange incumbent's backbone is the small
one a single head cannot also be.

**It inverted the reading of the FAIL.** On the strange sheet, cutpoint cross-entropy is
monotone in how much is shared — medium backbone on strange rows alone 0.639/0.680,
pooled with two last layers 0.523, pooled with one 0.422/0.487/0.450, the small-backbone
incumbent 0.326/0.362/0.303. Pooling *helps* (paired per seed, −0.217 [−0.362, −0.079]
and −0.193 [−0.376, −0.031]); 2,935 strange rows under-feed the medium backbone and the
smooth rows regularise it. What costs the strange side is the backbone.

## The variants

Each moves ONE thing about the design and each is **reported, never gated** — this bar was
written about the registered candidate, and a bar a different design could satisfy is not
a bar. Seed counts are stated because they are not bands.

```
fractal-wallpapers joint train --run two_head_seed0 --seed 0 --two-head
fractal-wallpapers joint train --run small_backbone_seed0 --seed 0 \
    --backbone mobilenetv4_conv_small.e2400_r224_in1k
```

`--two-head` is one backbone with **two last layers**, one ordinal head per kind. It needs
no new module: a CORN head over `classes` tiers emits `classes - 1` logits, and one
`Linear` of twice that width IS two independent heads — the rows of a linear map do not
interact, and an example of one kind reaches only its own kind's rows. `cutpoints_of` is
the gather, and the suite asserts the gradient isolation rather than assuming it. Note it
is **conditioned** and the candidate is not: it has to be told which kind it is reading.
Result: significantly *worse* on the strange sheet at matched seed (+0.101 [+0.007,
+0.203]). The shared classifier was doing regularisation work.

`--backbone` re-asks the one value a joint head cannot inherit. At the strange incumbent's
small backbone the design clears **every** gated arm at one seed, with a selection
objective of 0.386 against the medium band's 0.496–0.563 — it beat the medium's
best-of-forty after one epoch.

**Timing is not a reason to prefer the small backbone's speed**: this pipeline is
data-loading bound, not compute bound, and the two backbones cost the same per epoch on
identical rows (30.5 s against 32.2 s). A joint seed is ~45 min on one RTX 2060 either way.

## The split rule is stricter than either incumbent faced

The two stores stamp disjoint evaluation sides: 197 locations pinned to
`blind_minibrot`, 110 to `blind_modes`, no location in both. A joint head is read
on both, so both instruments have to stay clean, and its training side is the
**intersection** of the two training sides — a location pinned in either store is
out, whichever store its row came from.

That costs 28 smooth rows over 5 locations the smooth incumbent trained on
perfectly legitimately. The direction is deliberate: every deviation from the
incumbents' conditions here costs the candidate, so a non-inferiority verdict is
not something the split bought.

## Which boundary each sheet may be read at

```text
blind_minibrot  197 rows   2:6  3:95  4:96      gated at >=4, reported at >=3
blind_modes     150 rows   1:74 2:70  3:2  4:4  gated at >=2 and >=3
```

`blind_minibrot` holds no tier-1 row, so its `>=2` AUC is **undefined** rather
than perfect, and it is refused by name.

`blind_modes` is **never read at `>=4`**. Its only four positives there are four
rows a later *anchored* pass revised up from 3, having seen a tier; they are the
sheet's four superseded rows, and an AUC over them is an AUC over the only
non-blind rows on a blind sheet. Refused, not reported.

Watch the counts, because two sixes live next to each other. Six rows sit at
`>=3`; **four** rows are superseded, and those four are the whole `>=4` positive
class. The sheet holds 154 rows resolving to 150.

## What is here

`bar.json`, the bar. `<run>/config.json` and `<run>/metrics.json`, the recipe and
the run. `<run>/scores_smooth_render.jsonl` and `<run>/scores_strange_render.jsonl`,
that run's read of each sheet with every row carrying its whole join.
`comparison.json`, the read against the bar. The weights are `best.pt` and
`last.pt` and are not tracked — the same rule that keeps every other head's out.
