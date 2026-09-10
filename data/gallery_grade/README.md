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
  **The two readings correlate at r = 0.62**, which is the number that says how to
  treat them: high enough that the draw did select the pictures it meant to, far too
  low to use either as a stand-in for the other. The disagreement is centred and
  heavy-tailed — a median of nothing with a fifth of a probability in each tail — so
  an aggregate over the store hides it and a per-row join is the only honest read.
  Over the landed 1,000 the same reading is **r = 0.696**, with **55** rows under 0.5
  at label geometry against **none at all** at candidate geometry — the direction is
  one-way, because a candidate had to read high to be drawn.

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

### And blind was the first sitting's property, not the store's — 2026-09-09

The anchors exist and a head is fitted on them, so the second sitting is a
**correction** page: `p_fine_correction_20260909`, 750 units over four blocks and
three sheets, prefilled with the fine head's own decode and read good→bad by its
expected grade. Blind is still `sheets.gallery_grade_source`'s default and there is
no flag — the plan decides, by stating a `suggestion` or not.

**Only the first two of the six things above turn over.** The prefill and the order
are this store's *own* head correcting itself, which is the opposite of the render
judge injecting the order this scale replaces; the card is untouched, so `facts`,
the caption and `columns` are still empty and no stratum is readable off it. Two
consequences a reader of these rows has to carry: the suggestion is a reading of the
row's **candidate at 640×360 ss2** and not of the 1280×720 picture the page served,
and a prefilled page measures **downward disagreement only**, so a correction rate
off that batch is a ceiling and not the head's report card.
`data/batch_caveats.md`'s *FOUR-BLOCKS-ONE-BATCH* is the entry, and the block a row
was drawn in lives on the row inside `selected_on.block`.

## What the first sitting landed, and the drift inside it

All 1,000 units, ingested 2026-09-06, labeler `matt`: **26 / 185 / 477 / 312** over the
four grades, 1,000 rows resolving to 1,000 renders over 815 locations, nothing
superseded and nothing unkeyed.

**The three batches do not agree, and the difference is the scale rather than the
draw.** They were cut as stratified thirds — near-identical on seated/refused, on the
kind and on the mode — so a distribution that moves across them is the labeler moving:

| batch | 1 | 2 | 3 | 4 | mean |
| ----- | - | - | - | - | ---- |
| `n1000_0906_1` | 17 | 66 | 140 | 111 | 3.033 |
| `n1000_0906_2` | 6 | 55 | 150 | 122 | 3.165 |
| `n1000_0906_3` | 3 | 64 | 187 | 79 | 3.027 |

χ² over the 3×4 table is **30.95 on 6 d.f., p = 2.6e-05**. The 1s fall away after the
first sitting — 17, then 6, then 3 — which is what *creating the anchors* looks like
from the outside: the first batch is the only one cast without a felt floor. The third
piles on 3 at the expense of 4. **A fit that pools the three is pooling three slightly
different scales**, and `batch` is on every row so it can be a covariate rather than a
surprise.

## What the second sitting landed — the correction page, 2026-09-09

`p_fine_correction_20260909`, 750 units over three sheets, labeler `matt`, ingested
in cast order: **275 / 185 / 160 / 130**, nothing superseded and nothing unkeyed. The
store now holds **1,750 rows over 1,462 locations, 945 of them seated**, at
**301 / 370 / 637 / 442**. It is one batch and **four populations** — three of them
conditioned draws — so the block on `selected_on.block` decides which rows a number
may be read over; `data/batch_caveats.md`'s *FOUR-BLOCKS-ONE-BATCH* is the file that
says which, and none of this is eval-eligible.

**This sitting is much harsher than the first, and that is the population and not
only the scale.** The first sitting drew from the pool at large and landed a mean of
3.07; this one draws from the fine head's own top, from the colour floor's seats and
from the coarse corpora's 3s, and lands **2.19**. The two are not comparable as
distributions. Two things do carry across: the drift is the same shape and bigger —
`top_band` moves from a block mean of 3.33 on sheet 1 to 2.14 and 2.37 on sheets 2
and 3, at χ² = 79.66 on 6 d.f. — and `sheet` is on every row for the same reason
`batch` is, so it can be a covariate. Unlike the first sitting the drift is
**inside one batch**, so `batch` alone will not reach it.

## The same row twice — what the 2026-09-10 sweep sitting measured

`aug_sweep_A_20260910` and `aug_sweep_B_20260910`, 200 units each, labeler `matt`, blind
and shuffled, ingested oldest drop first: **75 / 57 / 42 / 26** and **149 / 42 / 7 / 2**,
means 2.095 and 1.310. The store stands at **2,945 rows over 2,829 renders** at
**720 / 666 / 848 / 595**, with 116 renders superseded — which is the point of the sitting.

**116 of sheet A's units already carried a verdict, so this is the first measurement of
the scale float that is WITHIN a row rather than between rows.** Every earlier reading —
the three batches of the first sitting, the correction sitting's blocks — compared
different pictures graded at different times and could not separate the labeler moving
from the draw moving. Here it is one person, one row, twice.

| earlier sitting | n | mean signed shift | earlier → now |
| --- | --- | --- | --- |
| `gallery_top_20260910` | 59 | **+0.068** ± 0.118 | 1.97 → 2.03 |
| `gallery_tail_20260910` | 32 | **−1.031** ± 0.159 | 2.94 → 1.91 |
| `p_fine_correction_20260909` | 10 | −0.500 ± 0.428 | 2.60 → 2.10 |
| `n1000_0906_*` | 15 | **−1.333** ± 0.232 | 3.53 → 2.20 |

Read on today's one scale those four groups sit within **0.25 tiers** of each other; their
earlier verdicts spread **1.19**. The pictures cannot move, so most of the spread was the
scale. Stratifying on the earlier grade shrinks the estimate to 0.5–0.7 tiers and
over-corrects doing it — the shift regresses on the earlier grade at slope −0.551, and the
earlier grade is carried on the very scale being measured. **Between 0.7 and 1.1 tiers of
the cross-sitting spread is float**, and a fit pooling sittings is pooling that.

⚠ **`anchored=false` records that a page had no anchors; it does not make two such pages
commensurable.** `n1000_0906_*` shares this sitting's footing and the same 15 rows come
back 1.33 tiers lower — the largest gap in the table. Treat the flag as a caveat, never as
a licence to compare two sittings' levels.

**The drift inside a page survives the shuffle and is now measurable free of the column.**
Both sheets fall as the sitting goes on — A at −0.425 ± 0.125 tiers per 100 cards, B at
−0.236 ± 0.070 — and sheet B is the first page here whose position effect is not
confounded with what the page was cut to compare.

## The store is not the picture, and the plan is what makes it one again

A row carries `leveled` as a **boolean** and never the directory. The path lives only in
`artifacts/gallery_grade/<draw>/<batch>/plan.jsonl`, so those plans are the only thing
that can rebuild the 373 levelled pictures as they were judged, and they are small.
**The sheets' rendered pictures are regenerable and the plans are not.**

`.leveled/` directories cannot be taken from under a *surviving* row — that is
`tests/test_leveled_identity.py`'s argument — but a row's candidate can leave the
ledger entirely. Measured 2026-09-06 against `tentative.protected_keys()`: all 700
seated candidates are protected by the record they were drawn from, and **233 of the
300 runners-up were not, 95 of them carrying a levelled colormap**. The runners-up are
the near-neighbour half this store exists to separate, and they were the prunable half.

## What holds them now

**A grade is a label, so the label protection holds it** — `RETAINED_LABELED`, the
class that already keeps a row a person has judged, and no second spelling beside it.
`curation.retention.labeled_renders` reads this store along with the two gates, human
origin only, keyed through the same `finished.render_key`; `candidate_ledger.prune`
fills the class from it, inside `merge`, inside every leg. Nothing new is declared and
nothing else changed.

The join is the recipe and not the regime, so in principle it could mark a sibling of
the picture a row was cast on rather than that picture — which would take a live
`.leveled/` with it, since a colormap dies with the JPEG it sits beside. Measured
2026-09-06 over the 308,419-row ledger the ckpt-112 mine left: **each of the 1,000
graded render keys is carried by exactly one ledger row, and it is the candidate the
draw named on `selected_on`.** All 1,000 pictures are on disk and all **373** levelled
directories are present. A later leg re-rendering one of these recipes at another
regime would put a second row on a key and both would be protected, which is the
harmless direction; `tests/test_gallery_grade_retention.py` asserts the direction that
is not — that the drawn candidate itself is reached — and pins the plans beside it.

`gallery_grade.plan_paths()` is where the plans are asked for, so nothing outside this
store's module spells their layout.

## The head fitted on it

`models/gallery_grade/` — built 2026-09-06, **adopted by nothing**. A separate
network at the render judge's architecture, initialised from its shipped
`weights-v6` artifact and fitted on these rows at the ledger's **640x360 candidate**
geometry rather than at the 1280x720 the verdicts were cast on. That is the column a
seating walks, and it accepts the label-quality cost this file's own caveat prices:
the two geometries correlate at r = 0.696 and 55 of the thousand read `P(≥4)` under
0.5 at label geometry against none at candidate geometry.

The store's population is what bounds what that head may claim, and the bound is
this file's: not eval-eligible, one row per location, no colour-ceiling
representation. Every number in `models/gallery_grade/README.md` is **within-store
held out** on a 201-row stopping slice, and the head is stage two of a cascade
behind `p_ge4` — undefined on the 85.7% of the pool that never clears the gate, and
never a pool-wide ranker.

The three sittings' drift is a covariate there rather than a surprise:
`gallery-grade split` balances the batches into the holdout exactly (67/67/67) — and
since 2026-09-09 it balances the **sheet**, the **block** and the **grade** instead,
the sheet being the finer constraint the correction sitting needed and a refinement
of the batch. The drift still shows in that holdout's labels at Kruskal p = 0.021
because stratification balances counts and not scales, and the head's residual
against them is flat at p = 0.63.
