Human verdicts on how good a finished picture is **given that it already cleared the
render judge's bar** — an order inside a gate's own top, which the gate does not supply.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the verdicts, append-only, one row per finished render
corpus/                a frozen training corpus for the head (its own README says why)
```

Nothing outside `src/fractal_wallpapers/labeling/gallery_grade.py` opens `batches.jsonl` or
`rows/`, and `tests/test_gallery_grade.py` holds that over every tracked source.

## This is not a fifth judge, and its 1 is not anybody's 1

The finished-render stores answer *is this picture worth keeping*, and at the good end of
their scale they saturate (`P(≥3)` near 1 over everything the gate passed, while `P(≥4)`
still spreads). The solve is handed a set it may seat and no order inside it; this store is
the corpus for a head fitted to that order. The scale is `gallery_grade.MEANINGS`, written
onto every sheet's manifest as its `rubric`:

```
1   genuinely surprised this cleared the bar, a clear reject
2   just above the bar, acceptable but not ideal
3   quite good, happy with it in the gallery, but not a favorite
4   an absolute favorite
```

A 1 here is a verdict about the gate, not the picture, so three separations are asserted:

* **It is not one of `finished.HEADS`.** `finished.head_of` raises on the name, and
  `models.finished_train.population` calls it first, so a retrain naming this store dies
  before reading a row.
* **A row carries `grade` and no `score` key.** `check` refuses a row with one (the
  protection `spiral/` established).
* **No batch is ever eval-eligible.** The population is model-selected twice over (it
  cleared a per-mode bar, then the solve seated or refused it), so `register` refuses
  `score_unconditioned` or `eval_only`. There is no `eval_split.jsonl` and no
  `assert_pin_holds`.

## Keyed on the picture

Latest-wins resolves on `finished.render_key`, so a picture is one picture across every
corpus that judges pictures; a place with a dozen recipes contributes a dozen rows. Row
shape (values illustrative):

```json
{"schema": 1, "batch": "<batch>", "recorded_at": "<iso time>", "labeler": "matt", "origin": "human", "grade": 3,
 "family": {"kind": "multibrot", "degree": 3}, "viewport": {"center_re": "…", "center_im": "…", "width": "…"},
 "mode": "tia", "mode_params": {}, "curve": "linear", "colormap": "<map>",
 "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": false, "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
 "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 36962, "filter": "lanczos3"}, "partition": "multibrot3",
 "seated": false, "refusal": "location", "pre_stamp": false,
 "reading": {"p_ge2": 1.0, "p_ge3": 0.999938, "p_ge4": 0.984019}}
```

## Five things beside the join, and none of them was on the card

* `seated`: whether the solve seated the row in the record it was drawn from. A covariate,
  not a stratum: the scale is conditional on clearing the bar, not on a seat.
* `refusal`: for an unseated row, the `curation.solve` rule that refused it; `null` if seated.
* `pre_stamp`: whether the candidate's picture predates the autolevel stamp. Every row
  reads `false`: every recipe the operator acts on carries a stamp in the ledger.
* `leveled`: whether the candidate's `<stem>.leveled/` colormap was on disk when the plan
  was cut, so whether the sheet rendered through it (boolean only; see below).
* `reading`: the shipped render judge's cutpoints on the picture **this sheet rendered**, at
  label geometry. A column, never an order. It is not `selected_on` (the candidate-geometry
  reading the row was drawn on); the two correlate at about r = 0.7 with heavy tails, and
  rows read low at label geometry that read high at candidate geometry. Join per row; an
  aggregate hides it.

## The page is blind, and that is the point

By default there is no prefill, sweep, score order, `facts`, caption or `columns`
(`sheets.gallery_grade_source`): a page ordered by the render judge would ask the labeler to
reproduce the order this head replaces, and a caption is a stratum. Since the head exists a
plan may state a `suggestion` and cut a **correction** page (prefilled with the head's own
candidate-geometry decode, read good→bad); the card stays empty either way, and a
prefilled page measures downward disagreement only, so its correction rate is a ceiling.
`--rejection` is the veto's page. `labeling/README.md`'s *The fourth kind of sheet* has the
mechanics; `data/batch_caveats.md` carries what registrations do not.

## What the batches are

| batch | rows | 1 / 2 / 3 / 4 | page |
| --- | ---: | --- | --- |
| `n1000_0906_1`–`_3` | 1,000 | 26 / 185 / 477 / 312 | blind, stratified thirds |
| `p_fine_correction_20260909` | 750 | 275 / 185 / 160 / 130 | correction, four blocks, three sheets |
| `gallery_top_20260910` | 545 | 210 / 165 / 100 / 70 | score-ordered, three randomized cuts |
| `gallery_tail_20260910` | 250 | 14 / 58 / 98 / 80 | score-ordered |
| `aug_sweep_A_20260910` | 200 | 75 / 57 / 42 / 26 | blind; 116 units re-grade earlier rows |
| `aug_sweep_B_20260910` | 200 | 149 / 42 / 7 / 2 | blind |
| `gallery_rejection_20260914` | 8 | 8 / 0 / 0 / 0 | rejection pass (veto) |

`p_fine_correction_20260909` is one batch and four populations: the block on
`selected_on.block` decides what a number may be read over (`data/batch_caveats.md`'s
*FOUR-BLOCKS-ONE-BATCH*). Every row carries `batch` and `sheet`, so either can be a
covariate.

## What the first sitting landed, and the drift inside it

The three `n1000_0906` batches were cut as stratified thirds, so a distribution that moves
across them is the labeler moving, not the draw:

| batch | 1 | 2 | 3 | 4 | mean |
| ----- | - | - | - | - | ---- |
| `n1000_0906_1` | 17 | 66 | 140 | 111 | 3.033 |
| `n1000_0906_2` | 6 | 55 | 150 | 122 | 3.165 |
| `n1000_0906_3` | 3 | 64 | 187 | 79 | 3.027 |

χ² over the 3×4 table is **30.95 on 6 d.f., p = 2.6e-05**; the 1s fall away as the anchors
form. **A fit that pools sittings pools slightly different scales.** The same drift shows
inside later pages, and grades given to the same row twice (the 116 re-graded units) differ
by sitting: most of the spread between sittings' levels is scale float, not pictures.
⚠ `anchored=false` records that a page had no anchors; it does not make two such pages
commensurable.

## Three ways to identify the footing, and they are not equally strong

The de-drifted training view models a grade as
`g = z + alpha[sitting] + delta[cut] + beta[cut] * x`, `x` the page position in hundreds of
cards. Nothing in the store is rewritten.

* **A RANDOMIZED CUT is the strongest evidence, and it is free.** Cuts assigned at random
  are one population, so every difference in mean grade is the cut
  (`gallery_top_20260910`'s three cuts span about 0.8 tiers). **Randomize the cut of a
  multi-sheet page at plan time.** Balanced (`p_fine_correction`) or stratified
  (`n1000_0906`) cuts are one assumption weaker.
* **The re-graded rows carry level BETWEEN sittings, and nothing else does.** The link graph
  is a star centred on `aug_sweep_A_20260910`; a sitting with under about fifteen links
  shares one level across its cuts.
* **A SCORE-ORDERED page's position slope is identified through the pair shift**: regress
  the shift between two readings of one picture on the earlier card's position, so the
  picture cancels. Keying the correction on the **sheet** beats keying it on the batch.

⚠ **De-drifting is a better target to be SCORED against than to be TRAINED on**: see
`models/gallery_grade/README.md`'s *What the de-drifted target is for*.

## The store is not the picture, and the plan is what makes it one again

A row carries `leveled` as a **boolean**, never the directory. The path lives only in
`artifacts/gallery_grade/<draw>/<batch>/plan.jsonl`, so those small plans are the only thing
that can rebuild a levelled picture as judged. **Rendered sheets are regenerable; plans are
not.** `gallery_grade.plan_paths()` is the one accessor.

## What holds them now

**A grade is a label, so the label protection holds it**: `RETAINED_LABELED`, with no second
spelling. `curation.retention.labeled_renders` reads this store with the two finished
stores (human origin only, keyed through `finished.render_key`), and
`candidate_ledger.prune` fills the class from it inside every merge. The join is the recipe,
not the regime: a second ledger row on a key is protected too (the harmless direction);
`tests/test_gallery_grade_retention.py` asserts that the drawn candidate itself is reached,
and pins the plans.

## The head fitted on it

`models/gallery_grade/` is a separate network at the render judge's architecture, fitted on
these rows at the ledger's **640x360 candidate** geometry (the column a seating walks). Its
claims are bounded by this store: not eval-eligible, within-store held out, and stage two of
a cascade behind `p_ge4`, undefined where the gate does not clear and never a pool-wide
ranker. `gallery-grade split` balances the holdout by sheet, block and grade.
