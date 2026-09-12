Batch caveats: what a registration does not say, and what reading its rows wrong
would look like.

A registration (`*/batches.jsonl`) answers one question — was the *draw* free of a
model score, and did the *page* anchor on one — and that answer decides which side
of the split a batch may reach. It is deliberately not a place to keep everything
a reader has to know before quoting a number off a batch. That is what this file
is. Each entry below is a fact about how one live population was assembled that a
later reader would otherwise have to reconstruct from a run report, and that a
number quoted without it is simply wrong rather than approximate.

**This is the one file here that names live batches on purpose.** Everywhere else
a comment illustrates a *shape* — `<head>.<sheet>.json` rather than a drop that
exists — so that a search for a live name never answers out of a comment about a
different one. A caveat has no shape to illustrate: it is about the instance or it
is about nothing, and keeping it beside the registries is what makes it findable
from the rows it constrains.

Entries are added when a population is drawn, not when somebody is caught reading
it wrong. Ids below were checked against the registries on 2026-08-23 and are
spelled as those files spell them.

---

## OVERSAMPLED-AXIS — `repeat_axis_smooth_render_20260911` and `repeat_axis_strange_render_20260911`

**Half of this batch is a repeated traversal, against 0.605% of the pool.** The
two batches are one draw — `curate repetition`, `repeat_ckpt120`, seed 20260911 —
cut in two only because a mode routes to one finished store and a batch's rows all
belong to one. 246 tiles in **123 matched pairs**, 70 `smooth_render` and 176
`strange_render`.

**The oversampling ratio is about 82x and it is the point of the batch.** The
candidate ledger stood at **2,262 of 374,186 rows** (0.605%) carrying
`Palette.cycles != 1` when this was drawn; this page is 50%. Production draws it
lower still: `--vary-palette` is **off by default**, and when it is on
`depth.PALETTE_REPEATS` puts 0.3 of the *varied* shots at a repeat. So anything
later fitted on these rows inherits a prior about how common repeats are that is
two orders of magnitude off the pool's, and a rate quoted off this batch is a rate
about a deliberately enriched sample.

**Every tile is one half of a matched pair, so the rows are not independent.** The
repeat and its control share place, mode, mode settings, map, frame, cap, curve
and autolevel stamp, and differ in `Palette.cycles` alone — checked rather than
asserted, by re-deriving each control's recipe key through the call that made it.
A statistic over these 246 rows that treats them as 246 draws is wrong by roughly
the pair correlation; the readable quantity is the **within-pair** difference.

**No bar of any kind selected it, which is unlike every other batch in this file.**
Both heads read every tile and neither excluded one — including rows the render
judge scores at the floor. That is deliberate: the repeats the current heads
happen to tolerate are exactly the wrong sample for a sitting about whether the
axis is worth anything. It also means the usual conditioning sentence does not
apply here and the opposite one does — these are **not** rows that cleared
anything.

**The order is the fine head RUN over the tiles, not the pool's `p_fine` column.**
`gallery-grade score-pool` writes that column only for rows clearing the render
bar — 42,300 of 374,186 — which covered 8 of the 125 controls. So the page's order
comes from reading every tile through the shipped gallery-grade ensemble at
candidate geometry, and nothing was written back to `pool_scores.jsonl`. A reader
joining these rows to that column will find most of them absent from it.

**The prefill is the render judge's own decode and not the fine head's tier.** A
tier is a claim on one store's scale; the fine head's is a gallery grade.

**`cycles` is not the traversal count on the folded arm.** 40 of the 123 pairs use
a sequential map, which is baked as an out-and-back, so their `cycles = 2` is
**four** passes of the base ramp and their control's `cycles = 1` is two. The card
printed the traversal count; the row records `cycles`. The 83 cyclic pairs are at
`cycles` 2 (42) and 3 (41) and there the two numbers agree. The folded arm is
**32%** of the pairs against sequential maps' 15.3% of the library — a deliberate
over-share, not the pool's proportion.

**Two pairs were drawn and are not here.** The merge is an upsert through a door
that prunes, and the retention rule took 2 of the 125 repeats at locations already
holding a full keep. Both pairs came off the page whole, so the batch is 123 pairs
rather than 125 and no tile on it lacks a ledger row.

---

## DISJOINT-DRAW — `threads_promotion` and `itinerary_promotion`

*Registry: `strange_render/batches.jsonl`. 110 locations each, verified overlap 0.*

Two independent draws of the same shape over the same admitted stock — the
location head's own stock above the good floor, apportioned evenly across the
partitions — drawn separately, one render per location, and **sharing zero
locations**. Neither is a re-render of the other's rows in a second mode.

They support the promotion question they were bought for: each says what a human
makes of a mode this head had never scored, and the correction rate against the
head's prefilled tier is readable on each. What they cannot do is **compare the
two modes per location**. There is no location that appears in both, so any
threads-versus-itinerary difference read off these two batches is a difference
between two populations as much as between two modes, and the two populations
were drawn to be alike only in expectation. A per-location comparison needs a
paired draw, and no paired draw exists.

## `run9_plane_depth` is drawn over CANDIDATES, not admissions

*Registry: `labels/batches.jsonl`. 156 labeled rows out of 3,092 candidates.*

The population is run9's plane-channel **candidates** — the 3,092 in that
harvest's ledger — and not the ones that were admitted. So its keeper rate is a
rate over what the channel proposed, and the rate a harvest, a gate report or an
admitted-stock sheet quotes is a rate over what survived. The two differ by
exactly the gate, which is a large factor and not a constant one.

**And it is two width strata cut out of that candidate set, not a sample of it.**
Every candidate at width `<= 1e-6` was taken whole — 96 of them — and 60 more
were drawn at random from the 1e-5 decade, which holds 708. So the 156 rows cover
804 candidates and not 3,092, and inside those 804 the deep arm is sampled at 1.0
against the shallow arm's 0.085: the deep arm is **12% of the two strata and 62%
of the rows**. A rate pooled over all 156 is a rate over that reweighting. Read
the arms.

**The deviation is the estimand.** This batch exists to say how far the plane
channel's proposals sit from what gets kept; comparing its rate to an
admission-based keeper rate does not measure a discrepancy in the instrument, it
re-measures the gate and calls the answer a defect. Never put the two in the same
column.

## `release_bar_band` carries one run8h row

*Registry: `strange_render/batches.jsonl`. 55 rows, one of them run8h's.*

The batch is a band draw weighted toward this head's own release bar — non
representative on purpose, aimed at where the keep decision is close — plus **one
row flagged by name in review**: `run8h|release|0081`, a julia:mandelbrot
`smooth_mean_angle` render that was released, carried here as unit `u0272` and
scored 4 by a human. It is the keep-direction row Matt flagged, and it is in the
batch because it was flagged, not because the band draw reached it.

So it is one row of 55 that is there for a reason none of the other 54 share. A
rate computed over all 55 includes a row selected for being a keep; drop it, or
say it is in, but do not quote the batch as a clean band draw. (Note it is *not*
one of the four rows in `curation/bar_exceptions.jsonl`, which are a different
decision about a different question — those are candidates kept in service below
the acting bar.)

## `mandelbrot_offer_body` is five equal head-score bands

*Registry: `labels/batches.jsonl`. 150 rows = 5 bands × 30.*

Five **equal-count** bands by the shipped location head's `P(>=3)`, thirty drawn
at random inside each, over the standing offer body: the mandelbrot rows of the
curation sidecar that clear the junk floor and that run9 neither served to a
colorize nor released.

Equal-count, not equal-width, and stratified by the head's own score — so the
pooled rate over all 150 is a rate over a **flattened** score distribution, not
over the offer body's. The offer body is not uniform in head score, so the pooled
number is not the body's rate and rescaling it needs the band populations, which
are in the sidecar rather than in these rows. Read the bands; the pool is a
convenience.

## `under_seen_modes` was swept from position 270, and the sweep leaves no mark

*Registry: `strange_render/batches.jsonl`. 504 rows = 9 modes x 56, one page,
ordered by the head's `P(>=4)` descending.*

The page's sweep accepts the head's suggested tier for every unlabeled row from
the current position to the end, and it writes the tier alone. Nothing in the
drop, the sheet or the stored row says which button produced a verdict — the
stored `suggested` is the only column that can disagree with `score`, so a row
where they differ was adjudicated and a row where they match may be either.
**161 of these 504 rows carry an override; the last of them is at position 269,
and all 235 rows after it agree with the suggestion exactly.** Read the first 269
as human and the rest as the head's own decode restated.

Two consequences. The prefix is not half the draw at random: the page is ordered
by score, so positions 1-269 are the 269 highest-`P(>=4)` rows of the whole sheet
and each mode contributes its own top — 14 rows for `direct_trap_lines`, 51 for
`smooth_mean_angle`. Any per-mode rate off this batch is a rate at that mode's
top and is a ceiling twice over. And the suffix's tier distribution is the head's:
the head suggested no 1 anywhere on this sheet, so all 12 of the batch's 1s are
inside the prefix and the pooled `>=3` rate over all 504 is diluted by 235 rows
nobody judged.

---

## TWO-BLOCKS-ONE-BATCH — `seated_and_head_top`

*Registries: both. 200 rows over 200 distinct locations, cut as two sheets —
`smooth_render` 103, `strange_render` 97 — because the batch spans both kinds.*

One batch name, **two populations drawn by two different rules**, told apart on the
row by `section` and nowhere else. Block one is the 150 seats of the `p2b_n150`
program: the clearing pool walked strongest-first under five selection rules after
a neutral pre-selection. Block two is 50 rows drawn strongest-first by the shipped
judge's `P(>=4)`, one per location, under **no** selection rule. Any rate quoted
over all 200 mixes a heavily-constrained selection with an unconstrained one and is
a rate about neither.

**The control block is not the naive top 50.** Drawn with no exclusion at all, 36
of the strongest 50 places are already seated and 29 are the *identical* ledger
row, so the block would have been 58% a copy of the block it exists to control. It
therefore skips places any seat holds and takes the next 50 — the one rule the
"no selection rule" block obeys. Its floor is `P(>=4) = 0.99789` and its top is
`1.0`: fifty places inside two thousandths, so "strongest-first" barely orders it
and a rank read off its position on the page means very little.

**Pinned, and 150 of the 200 rows actually are.** `eval_only` pins at *batch*
granularity in a finished store, so the whole batch is evaluation-side by
registration. The realized pin took the 150 rows whose place carries no
training-side row and left **50 contested and unpinned**, because pinning those
would have stranded older training rows on the wrong side of the split. The
earlier estimate of 92 was counted off the candidate *ledger* — 108 places carry
a ledger row from an earlier draw, which is what the render cache reads — and not
off the labeled stores, which hold a prior same-store row at 66 of the 200
places. A ledger row is not a train-side label; do not read one for the other.

**The verdicts, and the one rate to quote off them.** 200 human tiers came in
`1 / 13 / 108 / 78` against a page that prefilled tier 4 on 199 of 200 rows.
Quote them **by block or not at all**: the 150 seats are `1/12/91/46` (tier 4
**30.7%**, tier ≥3 91.3%) and the 50 control rows are `0/1/17/32` (tier 4
**64.0%**, tier ≥3 98.0%). The two differ at `p = 5e-5` and the gap survives
matching on head score and on store, so the whole-batch 39% describes neither
population.

**Both readings are on the SHEET row, not on the stored one, and they are not
interchangeable.** `selected_on` is the `640x360 ss2` reading the row was
*selected* on; `columns` is the judge's reading of the `1280x720 ss2` picture the
page actually serves. Over the seats the two differ by `-0.0020` in the mean and
by as much as `0.27` on 14 individual rows, so a per-row agreement rate computed
against the wrong one is wrong by more than it looks. Both live on the sheet row
under `artifacts/`, which is ignored; the stored row here carries neither, and
reaches them only through its own `sheet` and `unit`. It was the only
batch in either store whose sheet carried `selected_on` at all — 200 rows of
9,427 — until three more cut the same way on 2026-09-03:
`dtm_variants_20260902` (188), `phoenix_q3q4_20260903` (200) and
`judge_band_20260903` (300). So the pair is readable per row on **four** sheets
and 888 rows, and reconstructed everywhere else. (The 14-unit
`phoenix_classic_leg` sheet carries none, so a sheet's date does not answer
this — ask the row.)
Reconstructing it off the ledger is exact where it is possible: today's ledger
`P(>=4)` equals `selected_on` on all 200, to the last digit.

---

## ARGMAX-PER-PLACE — `dtm_variants_20260902` cells are the judge's pick, not a draw

*Registry: `strange_render`. 188 rows, one per location, ingested 2026-09-03.*

The batch sweeps four `direct_trap_multiply` mode-param cells — `opacity=0.4`,
`opacity=0.6`, `threshold=0.2`, and both raised — and the mining legs drew them
**balanced**, 1,248-1,249 candidates each over four legs. The page did not. It is
one card per location, and the card is that location's **best clearing row by the
candidate column's `P(>=3)`** — so which cell a place appears under is the render
judge's own argmax over the four, and a cell's 41-52 rows are the places where that
cell beat the other three by that reading.

So a per-cell rate off these labels is conditional on the judge having preferred
the cell there, and the four cells stand on four disjoint sets of places. Two
things follow for anybody reading the cell table. A cell's human rate cannot be
differenced against another cell's as if the settings were the only thing that
moved; and the cell that reads worst — `opacity=0.6,threshold=0.2`, mean tier 1.93
against 2.92-2.95 — is by construction the set of places where the *most* inked
variant was nonetheless the judge's pick, which is a population as much as it is a
setting. The unconfounded design exists and is `scratch/dtm_variants/variants/`:
20 places x 5 settings, same map, only the settings swapped. **It is a preview page
with no export path, so it has no verdicts on it**, and none of its 20 places is on
the labelled sheet. Serving it is what would settle the cell question.

**The cell stays in the production roster, ruled by Matt 2026-09-04.** A settings
cell leaves the roster only at **zero clears**, and this one is not near zero: over
all 1,023 rows carrying both knobs above their catalogued defaults, **80 clear the
pool bar (7.8%)** and 20 clear the primed bar 0.90 (2.0%), which is the best of the
five cells at the pool bar — `TIDY_render_cv_and_two_reads`, read over the whole
candidate ledger rather than over this page. The mean tier 1.93 above is the labels'
verdict on a *conditioned* population, and the paragraph above it says why that
number cannot be differenced against another cell's. So the two readings do not
disagree, and the one that decides a roster is the clear rate.

**The judge is what the settings move, and it moves a long way** [measured]. On
the *same picture*, matched on place and map, `opacity=0.6 + threshold=0.2` takes
the render judge's `P(≥4)` from **0.81 to 0.01** while near-white goes 0.36 → 0.00
and chroma rises 2.1x. Matt's eye is chroma-indifferent over the same batch, so
that swing is the judge's penalty on the tint and not a reading of the picture —
which is why a cell's *judge* rate and its *human* rate answer different questions
here.

**And the page was swept.** The last override is at position 164 of 188; the final
24 rows are the head's own 1s restated, and every one of the batch's 24 tier-1
verdicts is in that suffix. The correction rate is 47.9% over the page and 54.9%
over the hand-cast prefix, and the second is the one to quote.

---

## BAND-DRAW — `phoenix_q3q4_20260903` straddles the judge's own 0.5 crossing

*Registries: both. 200 rows over 200 distinct locations, cut as two sheets —
`smooth_render` 95, `strange_render` 105 — because the batch spans both kinds.*

One candidate-ledger row per LOCATION on `phoenix` and `phoenix:classic` — the
location's best row by the shipped render judge's `P(>=4)` at `640x360ss2` — with
every location already carrying a row in either finished store excluded, and then
the **100 locations immediately above and the 100 immediately below
`P(>=4) = 0.5`**. The band runs 0.7815 down to 0.2268 and crosses at 0.5030/0.4991.

**It is not the top of the pool, and the prompt that commissioned it assumed it
would be.** Ordering the eligible 1,438 locations by `P(>=4)` and taking 200 gives
a page running 1.0000 down to only **0.8608** — the judge's q4-confident head and
nothing else, on a plane whose pool is deep enough that two hundred rows never
leave it. This batch exists to find places the judge holds at q3 that are really
q4, and that population is at the boundary rather than at the top.

**So every rate read off these rows is conditional on the judge having put the
place near its own crossing.** It is not a base rate about the phoenix planes, and
it is not differenceable against a top-of-pool batch like `seated_and_head_top`:
half of this page is drawn from below a score the other batch's population never
went near.

**One row per location, and the row is the location's argmax over modes.** Which
mode a place appears under is the judge's own pick among that place's candidates,
the same shape `dtm_variants_20260902` has one section up — so a per-mode rate off
these labels is conditional on the mode having won its place, and the modes stand
on disjoint sets of places.

**Nothing was dropped for a pin.** All 200 places were checked against
`pins.every_pinned` (1,452 places) and against both finished pins — `smooth_render`
277, `strange_render` 180 — and **none** is pinned. Excluding the 97 phoenix
locations that already carry a finished-store row is what bought most of that.

**The exclusion leaked, and six cards landed on already-labelled places.** The
method line above says every location already carrying a row in either finished
store was excluded; at ingest, **6 of the 200** places already held one — two in
`smooth_render` (both `smooth_decision_bands`), four reaching `strange_render`
(`sparse_mode_head_top` twice, `p_ge4_calibration_strange`, and one whose prior row
is in the *other* store). Two of the six are exact **render-key** matches and landed
as revisions rather than fresh rows: a `direct_trap_lines` picture raised 2 to 3, and
a `smooth_stripe` one restated at 3. No instrument was spent — all three prior
batches are train-side and no place is pinned — and nothing is lost, because a
revision is a new row over a readable old one. It is a defect in that draw and not
in a shared helper: the place keys are digit-identical on both sides, so the join
that finds them now would have found them then, and `judge_band_20260903`'s draw
hours later makes the identical exclusion claim and misses **0 of 300**.

**The sitting is in, and the band has no q4 signal in it — which is the answer to
what it was cut to ask.** 200 verdicts, 2026-09-03. Over both stores the judge's
score does not order Matt's tiers inside this band at all: Spearman(`P(>=4)`, tier)
is **-0.029** on the `640x360ss2` column the draw was made on (p=0.69) and **+0.068**
at label geometry (p=0.34), and **39 of his 73 fours sit below 0.5** on the draw
column. Split at 0.5 the q4 rate runs **34.0% above against 39.0% below** — the wrong
way round. So a rate off these rows is not merely conditional on the band, it is a
rate over a population this judge cannot rank, and no threshold rescues it: the
best-separating cut for a four peaks at balanced accuracy **0.52-0.57**, which is
chance. What does survive is one reading and only at label geometry: on
`strange_render`, q3+ runs **94.0%** above 0.5 against **70.9%** below.

---

## THREE-SLICES — `judge_band_20260903` is three populations under one name

*Registries: both. 300 cards over 300 distinct locations, cut as two sheets —
`smooth_render` 123, `strange_render` 177 — because the batch spans both kinds.*

One candidate-ledger row per LOCATION, the location's best by the shipped render
judge's `P(>=4)` at `640x360ss2`, with no location in two slices. Excluded before
the draw: the `phoenix`/`phoenix:classic` partitions and every
`direct_trap_multiply` row (both have their own sittings), every location already
carrying a row in either finished store, and every place in `pins.every_pinned`.

**The three slices answer three different questions and no rate pools across
them.** S1 is smooth's top end, S2 is the 3-vs-4 band across the roster, S3 is
rare colours. A number quoted over "this batch" is a number over a union nobody
designed.

**The slice is recoverable off a stored row only through the UNIT ID.**
`intake._finished_row` writes the join, the batch, the sheet name, the unit and
the suggested tier — not `facts`, not `selected_on`, not `section`. The sheets
were cut with `section` set to the slice, so the ids came out in contiguous
blocks, and these are them:

| sheet | S1 | S2 | S3 |
|---|---|---|---|
| `smooth_render` (123) | u0001–u0118 | — | u0119–u0123 |
| `strange_render` (177) | u0001–u0002 | u0003–u0122 | u0123–u0177 |

**S1 is a sliver at the band ceiling, not the band.** The rule was "the band
`P(>=4)` in [0.40,0.95), ordered by score, top 120", and the smooth band holds
**3,018 locations** — so the top 120 spans **0.9414 to 0.9500**, 0.0086 wide, and
holds not one of the head's threes. It is the marginal-four end and it is what
"smooth's top end" asked for; the slice that actually crosses the 3/4 boundary is
S2, at 0.4145 to 0.9499. Nothing about S1 is a reading over the band.

**S2's mode balance is the draw's, and four of its modes are ruled out of
production.** 120 split over the **16** strange-kind modes the band population
holds — `tail_itinerary` has none — as twelve modes at 9 and then
`gaussian_int` 7, `direct_trap_ring` 3, `trap_circle` 1, `smooth_trap_circle` 1.
The last four are `MODE_POLICY` weight 0: renderable by name, out of every draw
and out of the gallery. They are on the page because a judge scores pictures
rather than material standing, but a per-mode rate off them describes stock
nothing will seat.

**S3's cells are the ones the last solve did not fill.** Bar-clearing rows
(`P(>=4) >= 0.50`) whose dominant cell is below the allowance of **84** on
`solve/empty_modes_n2000`, taken 2026-09-02T16:41:50Z — 27 of the 48 cells are
below it and 21 sit exactly at it, which is why that record's `over_allowance` is
empty. The 60 cards cover **24 of the 27**; `dark_vivid_lime`, `dark_vivid_yellow`
and `light_vivid_lime` are not represented. Taking S1 and S2 first cost S3 178 of
its 3,891 eligible locations and did not bind.

**Four `itinerary` cards are in the strange store and are the smooth judge's
material.** They carry `texture_flat: true` at candidate geometry, which routes
them smooth off the ledger, and the register misses at label geometry so
`routes_to` sends them strange. They are tagged S1 (2) and S3 (2) on the strange
sheet. Nine cards in all read flat at `1280x720ss2` when the measure pass asked
the engine directly, so the count of degenerate modulates on that sheet is nine
and not four; nothing has extended the register at that geometry.

**Nothing was dropped for a pin.** All 300 places checked against
`pins.every_pinned` (1,452) and `smooth_render`'s own pinned set — **none** is
pinned. Excluding the 19,302 rows sitting on already-labelled places is what
bought that.

**The sitting is in, and the three slices are ordered three different ways — which
is the case against pooling them, measured.** 300 verdicts, 2026-09-03.
Spearman(`P(>=4)`, tier) at label geometry runs **0.113 (p=0.22) on S1, 0.341
(p=0.0001) on S2 and 0.491 (p=0.0001) on S3**, and pooled over all 300 the draw
column reads **0.083 (p=0.15)** — a union that looks unordered while two of its
three parts are ordered. Per slice: S1 q4 **0.339** and q3+ 0.975 over 118 smooth
cards; S2 q4 0.525, q3+ 0.917; S3 q4 0.500, q3+ 0.867.

**S1's disorder is not its narrowness.** Re-scored at label geometry the 0.0086
sliver spreads to **0.700–0.996**, 34x the width, and the tiers still do not follow
it (0.113, p=0.22); top 30 against bottom 30 by draw score is q4 0.333 against
0.367. Given a real spread over the same pictures the judge orders them no better,
so nothing is bought by re-cutting S1 wider — the addendum that would have done it
was never run.

**S2 cannot answer the 3-vs-4 crossing it was cut for, because the mode balance
took each mode's top.** The band runs 0.4145–0.9499 but **118 of the 120 sit above
0.5** — the two below are the whole `smooth_trap_circle` and one `gaussian_int` —
so there is no below-bar arm to difference against, and walking the judge's own
order the q4 rate never falls under a half at any depth. Read S2 as a top-of-band
per-mode page, never as a band split. **And its ordering is mostly the ruled-out
modes**: dropping the twelve weight-0 cards takes the draw column's rho from 0.240
(p=0.008) to **0.155 (p=0.11)**, while label geometry survives at 0.252 (p=0.009).
Those twelve read q3+ 0.583 / q4 0.250 against the 108 weighted cards' 0.954 /
0.556, which is the eye agreeing with `MODE_POLICY` — confounded with score (mean
0.612 against 0.895) and n=12.

**S3 is the only slice the judge ranks inside its own top, and the disagreement
there is colour-shaped.** All 60 clear the bar and the ordering is still the
strongest of the three (0.446 drawn, 0.491 label; 0.441/0.493 on the 55 strange
cards alone). Per colour family the judge sits at 0.91–1.00 mean `P(>=4)` almost
everywhere while the eye runs q3+ 0.667 to 1.000: `purple` (n=9) and `lime` (n=3)
are read 0.989 and 0.987 and given mean tier 3.00 and 2.67, against `orange` and
`red` at 1.000 q3+. Families overlap — a card dominant in several cells is counted
in each — so the per-family n's sum past 60.

**Every correction runs down, and the up direction is close to untestable here.**
162 corrections, **0 upward**: the head suggested 294 fours, Matt cast 134, and all
134 came out of those 294. Correction rate is 64.2% (79/123) smooth and 46.9%
(83/177) strange, neither page swept — last override at 119 of 123 and 177 of 177.
With a 4 prefilled on 98% of the page a correction rate off this batch measures
downward disagreement alone, which is the anchoring the registration warns about
rather than a defect in the draw.

---

## ONE-CARD-A-PLACE — `phoenix_classic_20260903` is a leg's own places, best card each

*Registries: both. 35 rows over 35 distinct locations, cut as two sheets —
`smooth_render` 1 and `strange_render` 34. Registered 2026-09-03.*

The population is one depth leg and nothing else. `pc20m` ran twenty minutes on
`phoenix:classic` at width 3 over the full eleven-mode roster and opened **35
never-opened locations**, 103 candidates; this batch is those 35 places, one card
each, and the card is the place's **best candidate by the render judge's `P(>=4)`**
at `640x360ss2`. So it is score-conditioned twice: the leg's ranked arm chose the
places on the *location* head's rank within partition, and this chose the card on
the *render* judge's.

Three things a rate off these rows would get wrong.

**A per-mode rate is a rate over argmaxes.** Which mode a place appears under is
the render judge's pick among the three that place was offered, so the eight modes
on the strange page stand on eight disjoint sets of places and cannot be
differenced against each other. The leg's own per-mode rates, over the full 103
candidates rather than the 35 winners, are in `curation/MEASUREMENTS.md`.

**The whole batch sits below the judge's own q4 bar.** Not one of the 103
candidates cleared `P(>=4) >= 0.50` and the leg's maximum is **0.371**, so the
strongest card on the page is a place the judge is unsure about. The page runs
0.3709 down to 0.0005 on the strange side and holds a single 0.0045 card on the
smooth. Read it as *what the judge thinks is the best of a fresh plane*, never as
a keeper population.

**Every clear rate on this plane is a ceiling.** The render judge carries almost
no `phoenix:classic` q4 labels — 38 places in the whole project hold a human q3+
verdict there, 13 of them q4 — so its probabilities on this partition are an
extrapolation. That is the reason this sitting exists.

**And the plane's labels are split three ways across the stores, so a "how many
labels are there" answer depends on which store is asked** [measured, ckpt 103].
The LOCATION store holds **73 rows, 7 of them q3+ and 1 q4**; the finished stores
hold **`strange_render` 103 rows / 30 q4** and **`smooth_render` 210 rows / 20 q4**
on the plane. An earlier reading of "one q4 label on the whole plane" was the
location store alone. What is scarce here is **places, not verdicts** — q3+ places
went 38 → 72 over this era.

**Four of the six `itinerary` cards are degenerate modulates.** The engine reported
`texture_flat` at `1280x720ss2` on all four; `texture_flat.KEYED` holds the
geometry and nothing has measured this plane's modulates there, so
`finished.routes_to` calls them not-flat and they ingest strange — while being the
smooth judge's material by the project's own rule. The measure pass holds the
measurement (`scratch/phoenix_classic_20m/strange_render/measure.json`) if anybody
wants to extend the register.

**Nothing was dropped for a pin, and nothing was already labelled.** All 35 places
checked against `pins.every_pinned` (1,452), `smooth_render`'s 277 and
`strange_render`'s 180 — none is pinned, and none of the 35 carried a
finished-store row before this sheet, which is what a leg over never-opened
locations should look like.

**Ingested 2026-09-03, and the strange page only: 34 of the 35.** The one-card
`smooth_render` page was served and never exported —
`labels/smooth_render.phoenix_classic_20260903.json` does not exist anywhere in the
checkout, while its sheet, its render and its levelled map all do
(`scratch/phoenix_classic_20m/smooth_render`). A drop is the only record a page
leaves, so the card is re-labellable at zero render cost and is *not* recoverable
without re-serving. `smooth_render` is therefore unchanged by this batch: 210
`phoenix:classic` rows, 20 of them q4, exactly as before. The strange ingest read
34 on the sheet / 34 exported / 0 not acted on / 0 withheld, 34 fresh and 0 revised,
pin ok at 180 pinned places and `asserted_before_writing: true`; a second run reports
`already stored: 34, to write: 0`.

**The head suggested no fours at all, and a person cast sixteen.** Its page is 14
twos and 20 threes; the verdicts are 18 threes and 16 fours, and **every four came
out of a 2 or a 3** — seven from twos, nine from threes. Twelve of the sixteen sit
under a label-geometry `P(>=4)` of 0.02. That is the ceiling in this entry's last
paragraph being *reached* rather than merely warned about, and it is the reason a
`P(>=4)` bar read off this plane means nothing today.

**After the sitting the plane holds 72 q3+ places, 29 of them with a q4** — against
the 38 and 13 below, which were the pre-sitting figures. **34 of those 72 roots are
this one page**, so a single 34-card sheet is now 47% of `phoenix:classic`'s entire
proven supply and 16 of its 24 tier-4-credited roots. Note the two ways to count a
four here: 29 places *hold* a q4 verdict somewhere, while the proven channel credits
a place to the first store that has it and reads **24** at tier 4 — the channel's
number is the one a root draw sees.

---

## Five batches reach the candidate ledger; the other twenty-one do not

*Registries: both. Measured 2026-08-28 over the 9,427 resolved scored rows.*

A finished-render row carries its whole recipe, so nothing about the *picture* is
missing from any of these batches. What is missing from most of them is the
**model column**: `P(>=4)` exists only for rows whose recipe is a row of the
candidate ledger, and only four batches were drawn over that ledger —
`p_ge4_calibration_smooth` (123), `p_ge4_calibration_strange` (115),
`released_top_end` (116), `under_seen_modes` (496) and `seated_and_head_top`
(200), which join at 100%. Everything else was drawn over the **location
supply**, whose places mostly never became candidates: 1,051 of 9,427 join by
recipe key, 1,045 of those are in today's pool and 667 clear the production
screen.

Two consequences a rate would get wrong. First, **the joining rows are the
selected top**: their tier mix is `1/2/3/4 = 1.2 / 31.1 / 41.7 / 26.0%` against
the non-joining `26.8 / 38.8 / 24.6 / 9.8%`, so any base rate read off the
joinable corpus is a rate over draws that were already cut on the judge. Second,
**a batch's reach is not about its age but about its source**: the ten batches
registered 2026-08-15 and the July imports reach neither the ledger nor the
supply sidecar — 0 rows of 7,552 — because those places have since been
superseded out of the standing pool, while `threads_promotion`,
`itinerary_promotion` and `release_bar_band` reach the supply at 100% and the
ledger at 20/110, 22/110 and 9/55.

It is not a key problem and no re-keying fixes it; the geometry axis people reach
for first accounts for **0 rows**. See
[the recipe key's note](../src/fractal_wallpapers/curation/README.md).

## `spiral_500_20260903` is UNIFORM OVER THE POOL, which is not uniform over anything else

*Registry: `spiral/batches.jsonl`. 500 locations, 100 of them reserved. The first
attribute batch, and the first batch here that records no tier.*

Registered `score_unconditioned: false`, and the flag is right even though the
draw is a seeded uniform sample. The 500 were drawn with no model in the choice
*among* them, but the population they were drawn from is the candidate pool, and
membership in that is the render judge's `P(>=4) >= 0.5` at candidate geometry —
9,086 locations out of a store of 169,160 candidates. So the flag fails closed,
correctly, and it costs this batch nothing: `eval_eligible` is not what protects
the probe here.

**What a rate off it means, and what it does not.** A spiral share measured on
these 500 is a share of *the places a gallery could seat*. It is not a share of
the locations this project has ever rendered, not a share of the walk's finds,
and not a share of fractal space. That is the population the share cap will act
on, which is why it is the one worth measuring — but a number quoted off it
without that sentence is about a different set every time somebody guesses which.

**A second conditioning, one level down.** Each location is represented by its
best-ranked clearing row rather than by a random one of its candidates, so the
*picture* on the card is selected by `solve.ranking`. That is the picture the
project would ship from that place, and it is deliberate; it also means the
sitting cannot say anything about how the answer would move under a different
coloring of the same place. The row carries its whole render block so that
question stays askable later, and 105 of the 500 went through the autolevel
operator's re-baked map.

**`anchored` is false and the page still prefilled every card.** The prefill is a
cosine to the centroid of six locations Matt picked out of the
`20260903T234205Z` tentative gallery — `f047b594`, `3c38e848`, `a513e397`,
`769339fd`, `cbd3e34f`, `857dfb91`, all six resolving to neutral embeddings — cut
at the median over the sheet's own 500 units, so exactly 250 were prefilled
`spiral`. It is not any head's decode and not a tier, which is what `anchored`
asks about, and the page says so in its own words. It is still a suggestion a
labeler can agree with out of tiredness: the honest reading of an agreement rate
here is agreement with *those six pictures*, and the threshold was a median
rather than anything fitted, so it carries no prior about the answer.

**The reservation is inside the batch.** 100 of the 500 are pinned in
`spiral/eval_split.jsonl` at seed `20260903`, drawn before any verdict existed.
There is no `eval_only` batch, because a second batch name would have printed on
the reserved cards. Their verdicts are collected like every other and the ingest
does not assert the pin; what the pin forbids is training on them.

## GLOBAL-ASSIGNMENT — `new_maps_top4_20260905` is four rows a map, not four rows a place

*Registries: both. 480 rows over 480 distinct locations — 241 in
`smooth_render`, 239 in `strange_render`, under one batch name in two stores.*

The population is the four best pictures of each of the 120 maps of drop
`classic-pairs-2026-09`, and the word doing the work is **each**. It is not a
top-480: it is a bipartite assignment that maximises the judge's total expected
tier subject to **exactly four rows per map, one row per location across the
whole 480, and at most 60 rows per family**. Three consequences.

**A map's four rows are not that map's four best pictures.** They are its four
best *at locations no other map took*, and the maps compete: a map whose
candidates pile up where a stronger map's do gets its later choices. So the
per-map mean tier this batch will produce is a lower bound on what the map can
do, and the gap is largest for the maps that lost ties. It is also the reason the
sheet is worth having — a per-map argmax would have handed one strong place to a
dozen maps and measured the place.

**A per-location comparison across maps does not exist here, by construction.**
Every location appears once. There is no place where two maps can be differenced,
so any map-versus-map reading off this batch is a difference between 120
populations of four as much as between 120 maps.

**And the mode is the assignment's pick, not a draw.** Each (map, location) edge
carries the better of that place's four field-mode candidates, so the mode mix —
`smooth` 241, `stripe` 132, `tia` 96, `curvature` 11 — is the judge's ranking of
the modes at these places and not a sample of anything. `curvature`'s 11 is a
statement about `curvature` losing ties, not about a draw that under-served it.

The 600 locations behind it were themselves cut on the judge: every one carries a
candidate at `P(>=4) >= 0.90` on the live artifact, unpinned, spread over the
standing partition weights. So this batch conditions on quality twice — the place
and the picture — and both flags read `score_unconditioned: false, anchored:
true`. Nothing measured on it is a rate about the world.

## MATCHED-PAIRS — `blind_palettes_20260905` answers one boundary and no other

*Registry: `strange_render/batches.jsonl`. 100 rows, 50 pairs, `eval_only`.*

Fifty pairs of locations, one member drawing its map out of the 120 of drop
`classic-pairs-2026-09` and the other out of the 822 shipped maps. Everything
else is matched inside the pair: the same **mode** (one roster —
`tia`/`stripe`/`curvature`, 17/17/16 in each arm), the same **partition**, and
the same bucket of the location's own `P(>=4)` to a twentieth. Realised arm means
0.84966 against 0.85054. The map and the mode are seeded uniform draws and no
finished-render score is anywhere in the selection.

**The boundary it informs is `P(>=3)`, new library against shipped library, and
that is the whole of it.** It is 100 rows: a per-mode or per-partition split of
it is a handful of cards an arm, and a `P(>=4)` read off it is a tail the design
was not powered for. The two arms draw 44 and 48 distinct maps, so it is also not
a statement about any one map.

`score_unconditioned` is **false** and the flag is right: the locations are the
proven pool — places already holding a candidate over the seating bar — so a
model score is in the population even though nothing chose *among* them. What
protects this batch is `eval_only`, not the flag.

**Its places were pinned before it had a verdict**, 100 of them, in
`strange_render/eval_split.jsonl`, and settled into ordinary label rows when the
sitting landed the same day. See `labeling/README.md`'s *A pin may be written
BEFORE the sitting* for the arc and for the two guards a reservation holds red
while it waits.

## NEVER-AN-INSTRUMENT — `gallery_grade`'s whole store, `n1000_0906_1/2/3` included

*Registry: `gallery_grade/batches.jsonl`. 1,000 units over three batches, none eval-eligible.*

**This caveat is about the store and not about one batch, and it is the only one
here that is.** Everything `gallery_grade` can ever hold is drawn from a solved
gallery record, and a solved record is model-selected twice over: a row is in the
pool at all only because it cleared its own mode's bar in `curation.headroom.bars`
— a reading of the render judge — and it is then seated or refused by the solve's
own constraints, which are the gallery's rules rather than anything about the
world. So **no draw from this store is a base rate about anything**, at any size,
however it is stratified, and no slice of it can serve as an evaluation set for
any head. `gallery_grade.register` refuses a registration carrying
`score_unconditioned` or `eval_only` for exactly that reason, and
`gallery_grade.eval_eligible()` is the reading of the file that says the refusal
held.

That is not a defect. The estimand is *conditional on the gate* by design, so a
population selected by the gate is the population the question is about. What it
forbids is reading a rate off it — "x% of the gallery is a 4" is a statement about
this solve's constraints as much as about the pictures.

### What the three batches are

One thousand rows drawn from the tentative record `20260906T133236Z` (solve
`n1000_after_thin_themes_0906`, `n = 1000`, pool stamp `b4833fd6`), split into three
stratified thirds — 334/333/333 — each independently representative on the
seated/refused split, the kind and the mode, so a sitting that stops after any
batch still holds a usable population. Seed 20260906.

* **700 seats**, drawn uniformly at random from that record's 1,000.
* **300 that cleared their mode's bar and were refused a seat**, weighted toward the
  two *near-neighbour* refusals — all 38 `twin` (a near-duplicate of a seated
  picture) and 262 `location` (a second row at a place a seat took) — because near
  neighbours of gallery members are what a ranking head inside the gate's top has
  to separate. The colour ceiling was to be the remainder and **the remainder came
  to zero**: the two near-neighbour classes supply 4,496 rows against 300 asked. So
  `cell_allowance`, which refused 22,258 rows in that solve, is **not represented at
  all**, and a fit read off these rows says nothing about the pictures the colour
  rules turned down.
* The refusal reasons are per-key, off a **counterfactual replay** of that record's
  own solve through the pool-view door with `explain` over every candidate key. The
  replay reproduced the record's 1,000 seats exactly and its nine refusal counts to
  the row, and wrote no solve record.

### Two things a reader has to know before counting anything

**More than one row per location, on purpose.** A `location` refusal is by
definition a second row at a place a seat took, so 262 of the 300 sit at one of the
record's own seats and 185 of them sit at a place the 700 also carries. The draw is
capped at **one refused row per location** — a place contributes at most one of the
300 — but the union is **815 distinct locations over 1,000 rows**, not 1,000. Any
per-location statistic has to say which.

**The seated/refused split is 700/300 by construction and is not a rate.** The
record itself refused 31,596 rows that cleared their bar for its 1,000 seats. This
population is 70% seated because it was drawn that way.

### The levelled colormap, which is the hazard `pre_stamp` was expected to be

**No row here is pre-stamp and none can be**: measured over all 284,517 candidate
ledger rows on 2026-09-06, every recipe the autolevel operator acts on carries a
stamp and every recipe carrying none is a direct-trap kind it never touches. The
pre-stamp population is the *depth* store's `sequence.jsonl`, a different store.

What does bite is the other half. The operator writes its overriding colormap to
`<stem>.leveled/` beside the candidate's picture, the plan carries that directory,
and the sheet renders through it — but the sweep of 2026-08-30 deleted 194,058 of
them before `curate pool-draw` existed to read one. **373 of the 1,000 rows carry a
levelled colormap and rendered through it**; 94 more are direct-trap kinds the
operator never acts on, and the remaining 533 rendered through the plain map. Some
of those 533 are rows the operator declined — it is in band on most pictures — and
some are rows whose colormap was swept, and the row itself cannot say which. The
split by picture age bounds it: **44.6% of the 762 rows made after the sweep carry
one against 22.9% of the 144 made before it**, so on the order of thirty rows lost
theirs to that sweep and are being judged through a colouring their candidate score
was not read on. `leveled` is on every row so a later fit can exclude them; the
after-the-sweep rate is also well under the 65% act rate `curate mine` recorded on a
high-band leg, so 44.6% is a floor on how many pictures the operator really touched
rather than a reading of the operator.

**And the levelled rows grade lower — inside one judge and not the other.** Over the
landed sitting the levelled rows mean 2.992 against 3.124 (Mann-Whitney p = 7.6e-04),
but split by the judge that drew them it is `strange_render`'s alone: 3.024 against
3.177 there (p = 0.001) and 2.882 against 2.886 over `smooth_render` (p = 0.46). So
this is not a levelling effect a fit can subtract off as one number, and it is
confounded with the kind either way — the levelled share is 42.7% of the smooth rows
against 36.0% of the strange ones.

### The three batches are three slightly different scales

Cut as stratified thirds and cast in one evening in batch order, they disagree at
χ² = 30.95 on 6 d.f., **p = 2.6e-05**, with the 1s falling 17 → 6 → 3 across the
sittings. The strata are near-identical by construction, so the movement is the
labeler finding the scale, not the population. `data/gallery_grade/README.md`'s *What
the first sitting landed, and the drift inside it* carries the table. Anything
comparing batches here is comparing anchorings.

## FOUR-BLOCKS-ONE-BATCH — `p_fine_correction_20260909` is four populations and one drop name

*Registry: `gallery_grade/batches.jsonl`. 750 units over 750 distinct locations,
three sheets, one batch. The NEVER-AN-INSTRUMENT entry above governs it too.*

The second sitting on this scale and the first **correction** one: the fine head
now exists, so 650 of the 750 carry its own decode as a prefilled suggestion and
the page is read good→bad by its expected grade. That changes what almost every
number off this batch means, and four things have to travel with it.

### The four blocks, and which of them a number may be read over

A block survives ingest only inside `selected_on.block`, which `intake` carries
onto the stored row because the plan stated it. Nothing else on the row says which
population it came from — `facts` and the sheet directory are untracked and the
page is not sectioned, so the unit ids interleave the four.

| block | units | rule | conditioned on |
|---|---:|---|---|
| `top_band` | 300 | `p_fine(≥4) ≥ 0.85`, of 6,245 such | the fine head |
| `near_bar` | 200 | `0.40 ≤ p_fine(≥4) ≤ 0.65`, of 3,724 | the fine head |
| `floor_thin_cell` | 150 | seats of `20260909T215815Z` carrying a `cell_floor:` stamp | the colour floor |
| `low_anchor` | 100 | the coarse corpora's score-3 rows, accepted modes only | nothing but the mode roster |

**Only `low_anchor` is an unconditioned draw**, and it is unconditioned over the
*coarse* corpora rather than over the pool — so it is not a base rate either, and
the store's own refusal to be an instrument is unchanged.

### A prefilled page measures downward disagreement only

The correction rate off these 750 is a **ceiling** on the head's error and not its
report card: a page ordered by a head, with that head's tier under every card,
collects the rows a person bothered to move. And `top_band` is judge-selected, so
near-all-downward corrections there are what that selection produces rather than a
finding. The sweep leaves no mark — see *`under_seen_modes` was swept from position
270* above — so an agreement read off a swept suffix is not an agreement.

**The prefill is a reading of the CANDIDATE at 640×360 ss2**, which is not the
1280×720 ss2 picture on the page. The fine head was fitted at candidate geometry
and nothing here re-reads it at label geometry, so a disagreement between the
suggestion and the grade carries a regime shift inside it. The shipped *render*
judge's reading of the served picture is on every row under `reading`, at label
geometry, and is the only column here read on the picture a person actually saw.

**`low_anchor`'s 100 carry no suggestion at all.** The fine head is defined over
rows clearing the render bar and has no output for any other row, so those rows sit
after every row it could read — `solve.at_fine_bar`'s rule for the same column —
and the sweep cannot turn a gap into a tier. Their job is to stop a retrain
drifting upward under a batch that is overwhelmingly downward corrections.

### The mode mix is a cap and a floor's own, and the two do not mean the same thing

`tia`, `threads` and `stripe` are 50.8% of this store's standing 1,000 rows and
34.4% of the clearing pool; here they are **21.3%** (72 / 31 / 57 of 750). Blocks
1, 2 and 4 cap each of the three at **4% of the block** and otherwise water-fill
toward even coverage over the 13 accepted modes. **Block 3 is not capped**: its
population is the seats the K=3 colour floor bought and capping it would change
what the block measures, so 88 of its 150 are those three modes. A per-mode
statistic pooled over the batch is therefore pooled over two different mode rules,
and `smooth` at 100 of 750 is the *even-coverage* answer rather than the pool's
55% — which is also why the batch is 650 strange-kind against 100 smooth-kind.

### One batch, three sheets, ONE drop name — export and ingest each before opening the next

`store.export_path` names a drop for the head and the **batch**, so all three
sheets save to `labels/gallery_grade.p_fine_correction_20260909.json` and the
second page's export **replaces** the first's. The three cuts are 251 / 250 / 249
units, and `intake` joins a drop to a sheet by position, so a drop read against the
wrong cut of the same batch binds verdicts to plausible wrong pictures without an
error — the 2026-08-29 case in `labeling/README.md`'s *And the ingest cannot tell
which cut the drop came from* is exactly this shape. The batch is one batch on
purpose (three registrations differing only by a sheet index would make the three
sheets non-comparable for no gain), so the discipline is the operator's: **label a
sheet, export it, `label ingest --sheet artifacts/sheet/p_fine_correction_20260909_<n>`,
and only then open the next.**

**What happened instead cost nothing, and it is worth knowing it works.** Sheet 1's
drop was copied aside as `…​.sheet1.json` before sheet 2 went up, and sheets 2 and 3
were saved by hand as `… pt2.json` and `… pt3.json`, so no export replaced another
and all three were ingested afterwards through `--labels`. The unit count is what
made that safe — 251 / 250 / 249 are distinct, one drop matches one cut — and the
confirmation is that Spearman of page position against verdict came back
`−0.745 / −0.477 / −0.494` where a misbound drop reads near zero. The recipe is in
`labeling/README.md`'s *A hand-renamed drop is the working answer to one batch cut
into several sheets*. It is a second-best to ingesting between pages, not a
replacement: three cuts of equal length would leave the count with nothing to say.

### The three sheets are three scales, and the sheet is on the row

Labelled 2026-09-09 in sheet order over about half an hour, they disagree at
**χ² = 69.39 on 6 d.f., p = 7.5e-12** over the whole 750, and the disagreement is
not spread evenly across the blocks. It is **`top_band`** — χ² = 79.66, p = 1.4e-13,
sheet 1 giving **no 1s at all** to its 100 rows against 32 and 28 on sheets 2 and 3,
and a block mean of 3.33 / 2.14 / 2.37 — and `floor_thin_cell` behind it
(p = 7.7e-04). At the bottom the three sheets agree: `near_bar` p = 0.07,
`low_anchor` p = 0.20. The sheets are near-identical by construction, and measured:
mean `p_fine` inside `top_band` is 0.9414 / 0.9480 / 0.9317 and the render judge's
own reading of the served picture 0.865 / 0.887 / 0.890 — if anything sheet 1's
rows are the *slightly worse* ones. So the movement is the labeler, in the same
shape `n1000_0906_*` moved above, except that here it is inside **one batch** and
therefore inside any number a reader pools. **A `top_band` false-positive rate off
this batch is a mean of 10% / 68% / 57%, and quoting the pooled 45% hides that.**
What makes it recoverable is that `intake` writes the sheet directory's name onto
every row: `row["sheet"]` is `p_fine_correction_20260909_1/2/3`, so a sheet term is
available to any fit and a per-sheet read costs nothing.

### Coarse 3 is fine 1, and `low_anchor` is where that is measured

The 100 `low_anchor` rows are the coarse corpora's score-**3** rows, and Matt graded
**84 of them 1, 14 of them 2, 2 of them 3 and none 4** — mean 1.18, 98% at or under
2. That is the whole coarse-to-fine scale relation at the bottom end and nothing
else in the tree measures it: a middling coarse render is a gallery-grade reject,
not a gallery-grade middle. The offset is about two tiers and it is flat across
modes (per-mode means 1.00–1.56 over 4–9 rows each) and across kinds (strange 1.17,
smooth 1.25). **Any retrain that mixes a coarse tier into a fine target without
this offset is mixing two scales**, and the block exists so the mixing has a
measured number rather than an assumption.

### Two smaller things

**`refusal` is null on every row here, seated or not.** This leg ran no
counterfactual replay of the record's solve, so an unseated row says only that it
holds no seat in `20260909T215815Z` — it does not say which rule refused it. On
`n1000_0906_*` the same field is the rule. 245 of the 750 are seats of that record
(150 of them block 3's, which are seats by construction).

**103 of the 750 locations already carry a graded row** from `n1000_0906_*` under a
*different* picture. The exclusion is per render and not per place — 64 draws were
dropped as already graded — so a per-location read across the two sittings is a
read over two colourings of one place, which is the difference this head exists to
learn and not a duplicate.

---

### Reading this file from code

Nothing parses it. It is prose beside the registries on purpose: a caveat that a
reader has to obey is a caveat a reader has to *read*, and encoding these as
flags would invite a downstream check to satisfy the flag and skip the paragraph.
The registration flags stay the two questions they have always been.
