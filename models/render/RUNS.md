Every tracked run directory under `models/render/`, and what each one is for.

Twenty-five of them, and a run name alone does not say which. Six belong to
`renders deploy` bands, nine to `renders train` candidates, four to its variants,
three are mislaunched, two are the ablation and one is a retired design. Each holds
`config.json` and `metrics.json`; a run that was read against a bar also holds
`scores_<kind>.jsonl`. The weights (`best.pt`, `last.pt`) are not tracked.

The bands themselves are declared in code, not here: `render_deploy.BANDS`,
`render_train.CANDIDATES`, `render_train.VARIANTS` and `render_train.MISLAUNCHED`.
This file is the index from a directory name back to one of those.

## The map

```text
run                      role                       backbone  seed  epoch  reads
deploy_v6_seed0          deploy band `deploy_v6`    small     0     12     SHIPS (weights-v6)
deploy_v6_seed1          deploy band `deploy_v6`    small     1     13     band mate
deploy_v6_seed2          deploy band `deploy_v6`    small     2      9     band mate
deploy_seed0             deploy band `deploy`       small     0      3     band mate
deploy_seed1             deploy band `deploy`       small     1     17     shipped weights-v5
deploy_seed2             deploy band `deploy`       small     2      9     band mate
enlarged_corpus_seed0    candidate `enlarged_corpus` small    0      5     comparison_enlarged_corpus
enlarged_corpus_seed1    candidate `enlarged_corpus` small    1      5     comparison_enlarged_corpus
enlarged_corpus_seed2    candidate `enlarged_corpus` small    2      4     comparison_enlarged_corpus
small_backbone_seed0     candidate `small_backbone` small     0      3     comparison_small_backbone
small_backbone_seed1     candidate `small_backbone` small     1      4     comparison_small_backbone
small_backbone_seed2     candidate `small_backbone` small     2      3     comparison_small_backbone
seed0                    candidate `medium`         medium    0     19     comparison.json (FAIL)
seed1                    candidate `medium`         medium    1     19     comparison.json (FAIL)
seed2                    candidate `medium`         medium    2     16     comparison.json (FAIL)
two_head_small_seed0     variant `two_head_small`   small     0      5     reported, never gated
two_head_small_seed1     variant `two_head_small`   small     1      1     reported, never gated
two_head_small_seed2     variant `two_head_small`   small     2      3     reported, never gated
two_head_seed0           variant `two_head`         medium    0     26     reported, never gated
strange_only_seed0       corpus-matched ablation    medium    0     19     no bar attached
strange_only_seed1       corpus-matched ablation    medium    1     31     no bar attached
mislaunch_medium_seed0   mislaunched                medium    0     20     answers no bar
mislaunch_medium_seed1   mislaunched                medium    1     26     answers no bar
mislaunch_medium_seed2   mislaunched                medium    2     28     answers no bar
forward_holdout_seed0    retired split design       small     0      1     nothing reads it
```

`small` is `mobilenetv4_conv_small.e2400_r224_in1k` and `medium` is
`mobilenetv4_conv_medium.e250_r384_in12k`. `epoch` is `metrics.json`'s
`best_epoch` — the epoch the run's own stopping rule chose, and **not a level**: a
seed moves the split as well as the initialization, so two runs' epochs are chosen
on two different slices.

## What each role means

**The two deploy bands** are `renders deploy`, three seeds each over the corpus as
it stood. `deploy` shipped weights-v5 out of `deploy_seed1`; `deploy_v6` shipped
weights-v6 out of `deploy_v6_seed0` on 2026-09-03 and `render.v5.fp16.pt` sits
beside the shipped artifact so a revert is one act. The first band keeps bare
`deploy_seed<N>` names because its records are on disk under them; every later band
prefixes its own. These six split 80/20 over **lineages** with a pinned 598 held
out, and nothing about a deploy run answers a bar — `deploy_v6` was adopted on
Matt's eye, unconditionally.

**The three candidates** are `renders train`, each with a bar written before its
band existed. `medium` reads FAIL and is superseded; `small_backbone` is the design
that ships, and its record carries **two** verdicts — the top-level `verdict` is the
strict per-seed conjunction and reads FAIL on one arm, `multiplicity.band_only_verdict`
is PASS, and the band-only reading is Matt's standing ruling of 2026-08-23.
`enlarged_corpus` reads PASS at `reading: "band"` and is gated against
`small_backbone` rather than against the retired per-kind pair.

**The four variant runs** are the candidate with one thing moved — one ordinal head
per kind on a shared backbone, at each backbone. They are reported in every
comparison and gate nothing, because a bar written about one design is not a bar a
different design may satisfy.

**The two ablation runs** are `--only strange_render`: one kind's share of exactly
the pooled split at exactly the candidate's recipe, so the only thing that moves is
whether the other kind's rows were in the batch. No bar is attached.
`comparison.json` names `strange_only_seed2` and the three `smooth_only_seed*` as
**absent** — they were never trained, and the record says so rather than reading a
band it does not have.

**The three mislaunched runs** trained at the medium backbone while the
`enlarged_corpus` band and its bar declare the small, because they were launched
without `--backbone` and took `RECIPE`'s pinned default. They were renamed out of
the band on 2026-08-24 and belong to none: `render_train.MISLAUNCH_BASIS` is carried
onto anything that reports them. Their best epochs — 20 / 26 / 28 against the band's
5 / 5 / 4 — are the shape of the failure, an under-fed larger backbone.

**The one holdout run** is the forward-holdout split design that ran before
`renders deploy`: every row registered after the incumbent trained went to the
comparison side, 2,415 rows of it against the deploy split's 598. It saturated —
those rows are 73% `>=3` by construction — and the design is retired rather than
parameterised. The directory is kept and no code reads it.

## What has no run directory here

`renders dose`, `renders grade` and the fold deal write through `paths.under` into
the regenerable tree — `render_dose/`, `render_grade/` and `render_folds/`, under
`artifacts/` while that subtree is hot — and never into a run directory.
`renders deploy` writes there too: `artifacts/render_deploy/` holds its records and
`models/render/<run>/` holds only the checkpoints and the two JSON files. A reader looking for those bands under `models/render/` will
not find them, and that is by construction: what is tracked here is a checkpoint's
recipe and its record, and a deal or a dose curve is neither.
