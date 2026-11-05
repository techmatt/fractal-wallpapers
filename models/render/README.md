**The** finished-render judge: one head over both kinds, and what ships.

One judge answers for the smooth coloring (judged as a wallpaper) and the other
seventeen modes (judged as renderings): same input, same 1–4 scale.

**The two LABEL STORES are separate.** `data/smooth_render/` and `data/strange_render/`
are two corpora with two blind sheets, two base rates and two floors, under their own
names and drop paths. A **kind** is one of those two and selects a floor, a slot and a
mode roster; the **head** is this one.

## What ships

`render.fp16.pt`, staged from `deploy_v6_seed0`: of the `deploy_v6` band's three seeds,
the one whose chosen epoch scored best on its own stopping slice (AP(>=3) 0.8788 at epoch
12, against 0.8706 and 0.8577). `models/weights.json` names it. The previous head's
artifact, `render.v5.fp16.pt` from `deploy_seed1`, sits beside it, so a revert is one
re-ship.

⚠ **Those three APs are read on three different 1,606-row slices**, because the seed
moves the split as well as the initialization. The 0.008 between the first two is not a
comparison of two heads, and no number from a deploy band is a level. The three chosen
epochs (12, 13, 9) clustering is the band's evidence that the stopping rule reads signal.

The weights are not tracked. `best.pt` and `last.pt` are what training leaves in full
precision; `fractal-wallpapers fetch-weights` downloads the halved artifact and checks
it against `models/weights.json`.

## The two floors, one per kind, both on this judge's scale

A floor is a point on the probabilities a particular artifact emits, so the record
carries both the kind a floor is *for* and the head it is *on*.

```text
strange_render   0.785   ACTING at release selection      crossing 0.783400
smooth_render    0.780   measured, ADVISORY everywhere    crossing 0.779545
```

**`curation.floors.ACTING_RELEASE_BARS` is the one place that says which acts**, and it
holds `strange_render` alone. The smooth height is measured and written onto records but
removes no picture. `curate solve run` seats against `solve.Q4_BAR` on `P(>=4)`, a
cutpoint neither `P(>=3)` height transfers to.

A floor is the labels-derived crossover: isotonic regression of *the person said >=3*
on this head's `P(>=3)`, the lowest score whose fitted agreement reaches a half, rounded
up. At a flip both are re-fitted by `head floor --head <kind>`, which must reproduce and
refuses a stale stamp. THAT the strange cut acts is Matt's review verdict; only the
heights move, because the scale does.

```
fractal-wallpapers head floor --head strange_render     # re-fit, must reproduce
fractal-wallpapers curate rescore                       # the pool onto this scale
```

⚠ **Read a height against its own scale, never against the last head's.** A move at a
flip can come from the store growing or the scale moving; refit the retired artifact
over today's stores to separate them (at the last flip the corpus half was zero).

⚠ **The floor is fitted on a corpus that is largely a selection.** About 41% of the two
stores' rows come from sheets built to escape the top (`manufactured_rare_colors`,
`under_seen_modes`, `smooth_decision_bands`, the `p_ge4_calibration_*` slices); the
rest are base stores and top cuts, so to that extent the judge learns what earlier
judges promoted. Downstream, the thinnest colour cells clear their mode's bar at about
half the ledger-wide rate although the library and the draw make them. The only
instrument that moves this is what gets drawn next.

## The deploy bands

`renders deploy` (`src/fractal_wallpapers/models/README.md`'s *Training the head that
ships*) trains three seeds of the incumbent recipe on the whole corpus.
`render_deploy.BANDS` names each band; the first band's runs keep bare
`deploy_seed<N>` names and later bands prefix theirs (`--band`).

**`deploy_v6` has no bar and no acceptance read, by Matt's ruling for that retrain**:
adoption was unconditional and the acceptance is his eye on the sheets the flip
produced. `renders ship` passed the gate it always reads,
`comparison_enlarged_corpus.json`, which is a different band's verdict; do not read the
ship log as though something judged v6. The 598 pinned rows sit on the side the loop
never reads, so both blind sheets stay unspent.

**`enlarged_corpus`** retrained the shipped design on the manufactured rare-colour
batch at three seeds; `bar_enlarged_corpus.json` and `comparison_enlarged_corpus.json`.
It gated against a **joint** incumbent (`CANDIDATES[...]["incumbent"]` names which; a
candidate that omits it reads against the retired per-kind pair), and passed five of
five gated arms flat. The selection objective orders runs within a band only.

## The mislaunch: why the backbone is checked at both ends

`enlarged_corpus`'s first three runs launched without `--backbone` and took `RECIPE`'s
pinned **medium**, while the band and its bar declared the small. They read FAIL, the gap
entirely in the scale term. `config.json`, both checkpoints' configs and `head audit`
all agreed with the wrong value; only the declaration knew. So
`render_train.check_declared_backbone` refuses at launch and
`render_train.check_written_backbone` refuses at the read. Those runs were removed;
`RUNS.md` lists what remains.

## The band, and the study that adopted it

`bar_small_backbone.json` is the non-inferiority bar this judge's design was registered
under, written before its band; `comparison_small_backbone.json` is the read. **Matt's
standing ruling: the non-inferiority reading is band-only**, and any future per-seed
conjunction must pre-state its false-alarm size at registration (`multiplicity` in the
record: fifteen one-sided 2.5% tests trip at least one about 31.6% of the time). Under
it this judge passes five of five gated arms. The superseded first candidate's
`bar.json`, `comparison.json` and `seed*` runs (medium backbone) stay exactly as read.

```
fractal-wallpapers renders train --head render --run seed0 --seed 0 \
    --backbone mobilenetv4_conv_small.e2400_r224_in1k
fractal-wallpapers renders score --head render --run seed0    # both sheets
fractal-wallpapers renders accept --head render               # against the bar
fractal-wallpapers renders ship  --head render --run seed0
fractal-wallpapers renders disagreements                      # pictures into scratch/
fractal-wallpapers renders glance --batch <name> --run <run>  # one batch, two orderings
```

`--only <kind>` trains the corpus-matched ablation, `--two-head` puts one ordinal
classifier per kind on the shared backbone, and `--backbone` re-asks the backbone. All
three are study arms and none gates. **A named run takes its band's declared backbone**
from its `CANDIDATES` entry, not `RECIPE`'s default; `--backbone` is for a run name no
band claims, and a contradicting value is refused.

**ONE run at a time, and the reason is the commit charge rather than the GPU.** A
trainer commits ~3.9 GiB and every Windows loader worker re-imports torch for ~1.05 GiB
more, ~8.1 GiB a run at four workers. About 117 GiB of this box's 127.8 GiB commit limit
is already committed by something that is no process's private bytes, so under 10 GiB
free is one run's worth. The failure is `OSError: [WinError 1455] The paging file is too
small` out of `torch/__init__.py` loading `cufft64_11.dll`; it is **not** a page-file
setting. Run one seed at a time with `renders deploy fit --workers 2` (~124 s an
epoch). The commit returns when a trainer is killed, but a killed *shell* does not kill
the fit it launched: check for a live `fractal-wallpapers renders deploy fit` before
relaunching.

**A render leg lives under the same ceiling**: its parent ~3.3 GB and each of three
workers ~0.9 GB, so a leg and a trainer is the arithmetic of two trainers.
`tests/README.md`'s *A lane sharing the box with a render leg* has the test lane's
side.

Both render caches must be **hot** first: `storage restore renders` (5.08 GiB over
10,558 files, about 77 s off the archive).

## What the study found

Pooling the kinds *helps* the data-poorer one: cross-entropy is monotone in how much is
shared. The first candidate's FAIL was capacity (too few strange rows for the medium
backbone), not pooling. Splitting the classifier per kind costs nothing at the small
backbone, so the shared classifier stays.

## Which boundary each sheet may be read at

```text
blind_minibrot  197 rows   2:6  3:95  4:96      gated at >=4, reported at >=3
blind_modes     150 rows   1:74 2:70  3:2  4:4  gated at >=2 and >=3
```

`blind_minibrot` has no tier-1 row, so its `>=2` AUC is undefined and refused by name;
its `>=4` cross-entropy is read for a cross-model claim only recalibrated.
`blind_modes` is **never read at `>=4`**: its four `>=4` rows are revisions from a later
anchored pass, while its `>=3` positive set is the same six rows either way. The suite
guards both; `render_acceptance`'s docstring has the reasoning.

## What is here

`render.fp16.pt`, the artifact. `release_floor_<kind>.json`, the two fitted floors.
`bar*.json` and `comparison*.json`, the bars and the reads. `<run>/config.json` and
`<run>/metrics.json`, each run's recipe and record; `<run>/scores_<kind>.jsonl`, that
run's read of each sheet, every row carrying its whole join. [`RUNS.md`](RUNS.md) maps
every run directory to the band or role it belongs to.
