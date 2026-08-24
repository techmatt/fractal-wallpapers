**The** finished-render judge: one head over both kinds, and what ships.

`smooth_render` judged the smooth coloring as a wallpaper and `strange_render`
judged the other seventeen as renderings. They took the same input, answered on
the same 1–4 scale, and differed in exactly one behavioural key — so the question
was whether the split was load-bearing. It was not, and on 2026-08-23 one judge
replaced both: one store boundary fewer, one release artifact fewer, one recipe
fewer to keep in step.

**The two LABEL STORES did not merge.** `data/smooth_render/` and
`data/strange_render/` are two corpora with two blind sheets, two base rates and
two floors, and they keep their names and their drop paths. What those names
select now is a floor, a slot and a mode roster — no longer a model. A **kind** is
one of those two; the **head** is this one.

## What ships

`render.fp16.pt`, staged from `enlarged_corpus_seed1` by the pre-declared pick
rule — the lowest frozen selection objective of the band, 0.372271 against 0.385630
and 0.377333. The band remains the honest performance read; the pick rule only
chooses which artifact carries it. It succeeded `small_backbone_seed0` on
2026-08-24, at the same design and the same backbone, on a corpus 487 rows larger.

The weights are not tracked. `best.pt` and `last.pt` are what training leaves in
full precision, and `fractal-wallpapers fetch-weights` downloads the halved
artifact and hash-checks it against `models/weights.json`.

## The two floors, one per kind, both on this judge's scale

A floor is a point on the probabilities a particular artifact emits, so the kind a
floor is *for* and the head it is *on* are different names now, and the record
carries both.

```text
strange_render   0.575   ACTING at release selection      crossing 0.573085
smooth_render    0.540   measured, advisory, gates nothing crossing 0.535952
```

**A flip moves these two for two reasons and the record separates them.** The store
grows and the scale moves, and a method that credited the whole drop to the scale
would misstate a number somebody restates again. Fit on the *retired* artifact over
the *grown* stores, the strange crossing is 0.614688 and the smooth is 0.527937 — so
0.005 of the strange bar's 0.045 drop is the 237 new rows and the rest is the scale,
and the smooth floor's whole 0.010 rise is the scale.

Both were re-fitted by `head floor --head <kind>` when the judge changed, and both
reproduce on re-fit — that check is the STOP condition, and it now bites on a
stale *stamp* as well as a moved height. THAT the strange cut acts is unchanged
and is Matt's review verdict of 2026-08-17; only the heights moved, because the
scale did.

```
fractal-wallpapers head floor --head strange_render     # re-fit, must reproduce
fractal-wallpapers curate rescore                       # the pool onto this scale
```

## The retrain that adopted: `enlarged_corpus`, 2026-08-24

The manufactured rare-colour batch grew both stores by 487 rows, and the shipped
design was retrained on them at three seeds — no recipe key moved, backbone
included. `bar_enlarged_corpus.json` is its bar and `comparison_enlarged_corpus.json`
is the read. **It passes five of five gated arms on the band and was adopted.**

The first candidate here gated against a **joint** incumbent rather than the retired
per-kind pair: `CANDIDATES[...]["incumbent"]` names which, and a candidate that omits
the key is read against the pair as before. `medium` and `small_backbone` are
untouched by that indirection and their records reproduce.

```text
smooth_scoring_rule   -0.0368  CI [-0.1013, +0.0266]   flat
strange_scoring_rule  -0.0004  CI [-0.0365, +0.0364]   flat
every AUC arm                                          flat
```

Growing the corpus costs nothing on either blind sheet, which is the only question
the bar asked. The order/scale decomposition says the same thing from the other
side: the candidate's scale term is at or below the incumbent's at three of the four
readable cutpoints, and best epoch lands at 5/5/4 against the incumbent's 3/4/3.

**This band was trained twice, and the first three runs are why
[`render_train.check_declared_backbone`] exists.** They were launched without
`--backbone`, so they took `RECIPE`'s pinned **medium** — the *first* candidate's
value — while this band and its bar both declare the small. The bar states the
recipe as "the incumbent's, unchanged in every key including the backbone", and
nothing read it. Those runs read FAIL, at +0.2045 and +0.0611 on the two
cross-entropy arms, with the entire gap in the scale term and best epoch at 20/26/28:
an under-fed larger backbone arriving over-confident, which is the same failure the
first band traced to capacity. Re-run at the declared backbone, every one of those
numbers goes flat.

Nothing in a run directory could have caught it. `config.json`, the config inside
both checkpoints and `head audit` all agreed with each other and with the wrong
value; the tell was a checkpoint 3.3x the expected size. So the declaration is
enforced at both ends now — before a launch spends hours, and before a written band
is read against a bar it may not answer. The three runs are kept as
`mislaunch_medium_seed*`, out of every band, named in `render_train.MISLAUNCHED`.

**The selection objective is not comparable across the two candidates** — 0.372–0.386
against 0.386–0.392 — because the slice is drawn over the pooled training side's
places and that side grew: 222 places / 757 pictures against 259 / 620. It orders
runs *within* a band and nothing else, and the pick rule is the only thing that
reads it across one.

`renders glance --batch <name> --run <run>` cuts the qualitative read a band cannot
give: one batch's rows under two heads' orderings, side by side, into `scratch/`.

## The band, and the study that adopted it

Three seeds, and **the band is the result**. `bar_small_backbone.json` is the
non-inferiority bar this judge was registered under, written before its band
existed; `comparison_small_backbone.json` is the read.

Matt's standing ruling of 2026-08-23: the non-inferiority reading is **band-only**,
here and from now on, and any future per-seed conjunction must pre-state its
false-alarm size at registration. Under that reading this judge passes five of five
gated arms. The record keeps both readings — the strict conjunction crosses once,
on `strange_auc_ge3` seed2, at a CI upper bound of −0.0036 over six positives, and
`multiplicity` in the record carries the arithmetic that says fifteen tests at
one-sided 2.5% trip at least one about 31.6% of the time against a perfect
candidate.

The superseded first candidate is here too — `bar.json`, `comparison.json` and the
`seed*` runs at the medium backbone — because its FAIL is what sent the study at
the backbone, and a superseded read stays exactly as it was read.

```
fractal-wallpapers renders train --head render --run seed0 --seed 0 \
    --backbone mobilenetv4_conv_small.e2400_r224_in1k
fractal-wallpapers renders score --head render --run seed0    # both sheets
fractal-wallpapers renders accept --head render               # against the bar
fractal-wallpapers renders ship  --head render --run seed0
fractal-wallpapers renders disagreements                      # pictures into scratch/
```

`--only <kind>` trains the corpus-matched ablation, `--two-head` puts one ordinal
classifier per kind on the shared backbone, and `--backbone` re-asks the one value
a joint judge cannot inherit. All three are study arms and none of them gates.

**A named run takes its band's declared backbone, and `--backbone` may not override
it.** `RECIPE` still carries the first candidate's medium; every band since has
re-asked that value in its own `CANDIDATES` entry, and the trainer reads the entry
rather than the module default. So the `--backbone` above is for a run name no band
claims — under one that a band does, a value contradicting the declaration is
refused rather than obeyed.

**Two runs at a time is the right way to spend this machine.** The pipeline is
data-loading bound, not compute bound: the GPU sits at ~20% and an epoch costs
~68 s alone against ~80 s with a second run beside it. Both render caches have to
be **hot** first — `storage restore renders`, 3.9 GiB over 8,021 files.

## What the study found

Pooling *helps* the data-poorer kind: the corpus-matched ablation put cross-entropy
monotone in how much is shared, and the medium backbone on strange rows alone read
0.639/0.680 against 0.422/0.487/0.450 pooled. The first band's FAIL traced to
capacity — 2,935 strange rows under-feed the medium backbone — and not to pooling.
Splitting the classifier per kind costs +0.101 at that backbone and nothing at all
at this one, all three seeds FLAT, so the shared classifier's apparent
regularisation was standing in for data rather than for thresholds.

## Which boundary each sheet may be read at

```text
blind_minibrot  197 rows   2:6  3:95  4:96      gated at >=4, reported at >=3
blind_modes     150 rows   1:74 2:70  3:2  4:4  gated at >=2 and >=3
```

`blind_minibrot` holds no tier-1 row, so its `>=2` AUC is **undefined** rather than
perfect, and it is refused by name. Its `>=4` cross-entropy is dominated by the
retired smooth head's calibration on a sheet enriched 3.95x, so **any** head "wins"
there by being less under-confident — that arm is read for a cross-model claim only
recalibrated.

`blind_modes` is **never read at `>=4`**. A later anchored pass revised four rows
from 3 to 4 and those four are the entire `>=4` positive class, so an AUC there is
an AUC over the only non-blind rows on a blind sheet. The same revision moved them
**within** the `>=3` class, so that boundary's positive set is identical before and
after — six rows either way — and gating there is sound. The two facts look alike
and the suite guards both. The sheet holds 154 rows resolving to 150, with **four**
superseded, not six.

## What is here

`render.fp16.pt`, the artifact. `release_floor_<kind>.json`, the two fitted floors.
`bar*.json` and `comparison*.json`, the bars and the reads. `<run>/config.json` and
`<run>/metrics.json`, each run's recipe and record. `<run>/scores_<kind>.jsonl`,
that run's read of each sheet with every row carrying its whole join.
