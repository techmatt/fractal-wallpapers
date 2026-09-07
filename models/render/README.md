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

`render.fp16.pt`, staged from `deploy_v6_seed0` — the seed of the `deploy_v6`
band's three whose chosen epoch scored best on its own stopping slice, AP(>=3)
0.8788 at epoch 12 against 0.8706 at epoch 13 and 0.8577 at epoch 9. It succeeded
`deploy_seed1` on 2026-09-03 as **weights-v6**, at the same recipe and the same
backbone, fitted on 8,815 pictures against that head's 8,239. v5's three runs stay
on disk under their own names and `render.v5.fp16.pt` sits beside the shipped
artifact, so a revert is one act: re-ship `deploy_seed1` at `weights-v5`.

⚠ **Those three APs are read on three different 1,606-row slices**, because the
seed moves the split as well as the initialization. The 0.008 between the first two
is not a comparison of two heads, and no number from this band is a level.

**The chosen epochs CLUSTERED this time — 12, 13 and 9, a spread of 4** — where
v5's were 3, 17 and 9, a spread of 14. Three curves agreeing about where the
stopping rule peaks is the only evidence this module can offer that the rule is
reading signal rather than noise, and v5's band could not offer it. The shipping
seed also stopped on its patience at epoch 18 rather than running into the cap, so
the uncapped final refit v5's band earned was not owed here and was not run.

The weights are not tracked. `best.pt` and `last.pt` are what training leaves in
full precision, and `fractal-wallpapers fetch-weights` downloads the halved
artifact and hash-checks it against `models/weights.json`.

## The two floors, one per kind, both on this judge's scale

A floor is a point on the probabilities a particular artifact emits, so the kind a
floor is *for* and the head it is *on* are different names now, and the record
carries both.

```text
strange_render   0.785   ACTING at release selection      crossing 0.783400
smooth_render    0.780   measured, ADVISORY everywhere    crossing 0.779545
```

**One of the two acts, and `curation.floors.ACTING_RELEASE_BARS` is the one place
that says which.** It holds `strange_render` and nothing else. The smooth height is
measured, recorded and written onto records; there is no leg in which it removes a
picture. It read differently at a second site until 2026-08-28, when `64c9612`
deleted the pre-solver gallery pass; `curate solve run` replaced that pass and seats
against `solve.Q4_BAR` on `P(>=4)`, a cutpoint neither of these `P(>=3)` heights
transfers to. So *measured* and *acting* are two facts about a height here, and this
table states both because for ten days it stated the second one wrongly.

**A flip moves these two for two reasons and the record separates them.** The store
grows and the scale moves, and a method that credited the whole move to one of them
would misstate a number somebody restates again. Fit on the *retired* weights-v5
artifact over the stores as they stand now, the strange crossing is **0.768239** and
the smooth is **0.618260** — which are v5's own recorded crossings to all six places.
So at the weights-v6 flip the corpus half is **exactly zero on both heads**: the 722
rows the two stores grew by moved neither height at all, and the scale is the whole
of +0.015161 on the strange bar and +0.161285 on the smooth floor.

⚠ **Read the heights against their own scale and never against the last one.** 0.785
is not a stricter bar than 0.770 was; it is very nearly the same crossing on a judge
that reads a little higher. The keeper share is 37.1% on both artifacts over the same
rows, because a keeper share is a fact about the labels and not about the head.

⚠ **The floor is fitted on a corpus that is largely a selection, so the baseline
IS the thing to chase.** A crossing is a point on the labels, and the labels are
whatever got put on a sheet. Of the **4,235 rows across the two stores**, the sheets
whose whole design is to escape the top are **1,746 (41%)** — `manufactured_rare_colors`
(496), `under_seen_modes` (504), `smooth_decision_bands` (500) and the two
`p_ge4_calibration_*` slices (246). The other **2,489 (59%)** are the base stores and
the named top cuts, `seated_and_head_top` and `sparse_mode_head_top` among them, and
to that extent what the judge learns a keeper looks like is what earlier judges already
promoted. The counterweights exist precisely because that is true. So this is
not a leak to plug somewhere else — there is no separate defect, the composition of
the corpus is the effect, and the only instrument that moves it is what gets drawn
next.

It is measurable downstream and it has been measured. Over the 169,082 candidates in
the ledger on 2026-09-03, the five colour cells thinnest in a 2000-seat solve clear
their own mode's bar at **4.3–9.1%** against a ledger-wide **12.6%**, while every one
of them has 24+ carriers in the library and 2,050+ rendered candidates on record. The
library can make those colours and the draw does make them; the judge does not keep
them. `scratch/draw_cells/read.md` carries the table.

⚠ **The two heights have nearly converged and that is new.** They sat 0.150 apart on
v5 and sit 0.005 apart on v6, because the smooth crossing moved ten times as far as
the strange one. The kinds are still two corpora with two fits; what changed is that
the joint head now says almost the same thing about where a keeper starts in each.

Both were re-fitted by `head floor --head <kind>` when the judge changed, and both
reproduce on re-fit — that check is the STOP condition, and it now bites on a
stale *stamp* as well as a moved height. THAT the strange cut acts is unchanged
and is Matt's review verdict of 2026-08-17; only the heights moved, because the
scale did.

```
fractal-wallpapers head floor --head strange_render     # re-fit, must reproduce
fractal-wallpapers curate rescore                       # the pool onto this scale
```

## The retrain that adopted: `deploy_v6`, 2026-09-03

Four sittings — `dtm_variants_20260902`, `judge_band_20260903`,
`phoenix_q3q4_20260903` and `phoenix_classic_20260903` — grew the two stores by 722
rows, 264 of them fours, and this band is v5's recipe run again over them. Nothing
about capacity, aspect, input size, architecture or the stopping rule moves; the
corpus is what changed, and the pooled population went 10,299 pictures over 3,649
lineages to **11,019 over 4,167**, training side 8,239 to **8,815**.

```text
deploy_v6_seed0   epoch 12   AP(>=3) 0.8788   AUC(>=3) 0.8919   p@10% 0.9814   ships
deploy_v6_seed1   epoch 13   AP(>=3) 0.8706                     19 of 20 epochs
deploy_v6_seed2   epoch  9   AP(>=3) 0.8577                     16 of 20 epochs
```

**There is no bar and no acceptance read here, by Matt's ruling for this retrain:**
adoption was unconditional, there is no incumbent comparison and no eval instrument,
and the acceptance is his eye on the sheets the flip produced. So this band writes no
`bar_*.json` and no `comparison_*.json`, and `renders ship` passed the gate it always
reads — `comparison_enlarged_corpus.json`, which is a *different band's* verdict and
which this band did not earn. That is worth knowing before anybody reads the ship log
as though something had judged v6.

The pinned rows are untouched: 598 of them, at identical tiers to v5's band, on the
side the loop never reads. **Both blind sheets are as unspent after this flip as
before it.**

`--band` is what keeps two passes of `renders deploy` apart. The first band's runs
keep their bare `deploy_seed<N>` names because their records are on disk under them;
every later band prefixes its own, and `render_deploy.BANDS` says what each one was.

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

**ONE run at a time, and the reason is the commit charge rather than the GPU.**
This used to say two at a time — the pipeline is data-loading bound, the GPU sits at
~20%, and an epoch cost ~68 s alone against ~80 s with a second run beside it. That
advice cost the `deploy_v6` band about an hour on 2026-09-03, because two runs at
once is what this box can no longer afford.

A trainer commits ~3.9 GiB and **every Windows loader worker re-imports torch for
~1.05 GiB more**, so the recipe's four workers is ~8.1 GiB a run. This machine's
commit limit is 127.8 GiB and about 117 GiB of it is already committed by something
that is not any process's private bytes — every process together accounts for 36.8
GiB and the pools for 5 GiB. Under 10 GiB free is one run's worth. The failure is
`OSError: [WinError 1455] The paging file is too small`, raised out of
`torch/__init__.py` loading `cufft64_11.dll`, and it is **not** a page-file setting:
`C:\pagefile.sys` is 96 GiB with 3 GiB in use.

So: one seed at a time, and `renders deploy fit --workers 2`. An epoch costs 124 s
that way against the ~75 s the band before it managed at four. Two more things are
worth knowing. The commit does come back when a trainer is killed — 127.5 GiB fell
to 117.0 GiB — so there is no leak to chase, only a baseline to live under. And a
killed *shell* does not kill the fit it launched, so an abandoned attempt goes on
holding its 9 GiB and the next launch fails for a reason that looks like the first
one; check for a live `fractal-wallpapers renders deploy fit` before relaunching.

**A render leg lives under the same ceiling and it is what usually holds it.** The
leg's parent holds ~3.3 GB and each of its three workers ~0.9 GB, about 6 GB
together, so a leg and a trainer at once is the same arithmetic as two trainers.
The test suite loses to it outright: run beside a leg the slow lane is killed at
77% with no summary and no traceback, which `tests/README.md`'s *A lane sharing
the box with a render leg* measures.

Both render caches have to be **hot** first — `storage restore renders`, 5.08 GiB
over 10,558 files, 77 s off the archive at 137 files/s.

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

And [`RUNS.md`](RUNS.md), which is the index a directory listing is not: one line
per run directory, to the band or role it belongs to. Twenty-five of them, across
two deploy bands, three candidates, two variants, an ablation, three mislaunches
and one retired design.
