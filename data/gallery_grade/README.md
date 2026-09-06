Human verdicts on how good a finished picture is **given that it already cleared the
render judge's bar** — an order inside a gate's own top, which the gate does not supply.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the verdicts, append-only, one row per finished render
```

Nothing outside `src/fractal_wallpapers/labeling/gallery_grade.py` opens either of
them, and `tests/test_gallery_grade.py` holds that over every tracked source.

## This is not a fifth judge, and its 1 is not anybody else's 1

The two finished-render stores answer *is this picture worth keeping*. They answer it
well, and at the good end of their own scale they saturate — a shipping gallery's
released rows have a median `P(>=3)` of 0.9999. So the solve is handed a set of
pictures it may seat and **no order inside it**, and every choice made after the bar —
which of two near neighbours takes the seat, which seat a swap gives up — is made by a
quantity that was never fitted to that question.

This store is the corpus for a head that is. The scale is four ordinals and the
question is conditional:

```
1   genuinely surprised this cleared the bar, a clear reject
2   just above the bar, acceptable but not ideal
3   quite good, happy with it in the gallery, but not a favorite
4   an absolute favorite
```

**The premise, measured on the first sheet's own 334 pictures** at label geometry
(1280×720 ss2), through the shipped render judge: `P(≥3)` median **0.9986**, p05
0.9554 — saturated, no order left in it — while `P(≥4)` runs 0.0099 to 1.0000 with a
median of **0.9577** and p25 0.8613. So the gate separates a little at its own top and
mostly does not, over a population every member of which it passed. That is the gap
this store is the corpus for.

Over in `smooth_render/` a 1 is "this does not work". Here it is a verdict about the
gate rather than about the picture. **A number that plausibly reads as another
store's is worse than one that obviously does not**, so three separations are
asserted rather than intended:

* **It is its own store and not one of `finished.HEADS`.** `finished.head_of` raises
  on the name, and `models.finished_train.population` calls that on its own first
  line — so a retrain that named this store dies before it reads a row. There is
  nothing to opt out of because there is no path in.
* **A row carries `grade` and no `score` key at all.** Every quality reader in this
  project reaches for `score`; `check` refuses a row that has one. This is the
  protection `spiral/` established, and the argument is stronger here, because these
  really are 1s to 4s about finished pictures and would read as tiers *plausibly*.
* **No batch is ever eval-eligible.** The population is model-selected twice over —
  every row cleared a head's per-mode bar to be in the pool, and every row was then
  seated or refused by the solve's own constraints — so no draw from it is a base
  rate about anything. `register` refuses a registration carrying
  `score_unconditioned` or `eval_only`, which are the two flags `eval_eligible` is
  derived from. There is no `eval_split.jsonl` here and no `assert_pin_holds`: there
  is no side to protect.

## Keyed on the picture

Latest-wins resolves on `finished.render_key` — the same identity through the same
function, so a picture is one picture across all three corpora that judge pictures. A
place carrying a dozen recipes contributes a dozen rows on purpose; the differences
between them are what this head has to learn.

```json
{"schema": 1, "batch": "n1000_0906_1", "recorded_at": "2026-09-06T19:40:00Z", "labeler": "matt", "origin": "human", "grade": 3,
 "family": {"kind": "multibrot", "degree": 3}, "viewport": {"center_re": "0.0815", "center_im": "0.7682", "width": "1.6e-08"},
 "mode": "tia", "mode_params": {}, "curve": "linear", "colormap": "Lavender Bleach",
 "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": false, "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
 "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 36962, "filter": "lanczos3"}, "partition": "multibrot3",
 "seated": false, "refusal": "location", "pre_stamp": false,
 "reading": {"p_ge2": 1.0, "p_ge3": 0.999938, "p_ge4": 0.984019}}
```

## Five things beside the join, and none of them was on the card

* `seated` — whether the solve gave this row a seat in the record it was drawn from.
  The scale is conditional on clearing the bar and **not** on being seated, so this is
  a covariate rather than a stratum boundary.
* `refusal` — for an unseated row, the rule that refused it, in `curation.solve`'s own
  vocabulary. `null` on a seated row.
* `pre_stamp` — whether the candidate's own picture predates the autolevel stamp, so
  that a fresh render of it is a different picture. Flagged rather than dropped: a
  population with those places taken out would be biased away from wherever the older
  legs worked. **Every row in the store today reads `false`**, and that is a fact
  about the candidate ledger rather than a coincidence: measured 2026-09-06 over all
  **284,517** ledger rows, every recipe where `autolevel.applies_to` says the operator
  acts carries a stamp, and every recipe carrying none is a direct-trap kind the
  operator never touches. The pre-stamp population is the **depth** store's
  `sequence.jsonl`, not this one.
* `leveled` — whether the candidate's own `<stem>.leveled/` colormap was still on disk
  when the plan was cut, and therefore whether the sheet's picture went through it or
  through the plain map. This is the hazard `pre_stamp` was expected to be and is not
  — see the caveat.
* `reading` — the shipped render judge's cutpoints on the picture **this sheet
  rendered**, at label geometry. A column and never an order. It is not the number
  the row was drawn on, which is `selected_on` at candidate geometry, and the two
  disagree by more than a rounding: over the first sheet the median shift is +0.0001
  but p05 is **−0.2518** and p95 **+0.1627**, with **20 of 334** reading `P(≥4)` under
  0.5 at the geometry the person is judging them at. Both are on the row so a later
  reader can attribute a disagreement to the regime rather than to the labeler.

## The page is blind, and that is the point

No prefill, no sweep, no score order, no `facts`, no caption and no `columns`. A page
ordered by the render judge would be asking the labeler to reproduce the exact
ordering this head exists to replace, and a caption naming the mode and the map is a
stratum a labeler can read off the card. `sheets.gallery_grade_source` is the cut;
`data/batch_caveats.md` carries what the registrations do not.

There is **no anchor sheet for this scale**, because until the first sitting there
were no rows. The four sentences above are `gallery_grade.MEANINGS`, they go onto
every sheet's manifest as its `rubric` verbatim, and the first sitting is what creates
the anchors.
