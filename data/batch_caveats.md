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

**Pinned, and only half of it can actually be pinned.** `eval_only` is asserted,
but 108 of the 200 places already carry train-side rows from
`p_ge4_calibration_smooth`/`_strange`, `under_seen_modes`, `released_top_end`,
`itinerary_promotion` and `threads_promotion`. Those places' groups are not
eval-eligible, so a seeded split will not draw them however the batch is
registered. Treat the pinnable instrument as the other 92 places.

**Both readings are on the row and they are not interchangeable.** `selected_on`
is the `640x360 ss2` reading the row was *selected* on; `columns` is the judge's
reading of the `1280x720 ss2` picture the page actually serves. Over the seats the
two differ by `-0.0020` in the mean and by as much as `0.27` on 14 individual
rows, so a per-row agreement rate computed against the wrong one is wrong by more
than it looks.

---

### Reading this file from code

Nothing parses it. It is prose beside the registries on purpose: a caveat that a
reader has to obey is a caveat a reader has to *read*, and encoding these six as
flags would invite a downstream check to satisfy the flag and skip the paragraph.
The registration flags stay the two questions they have always been.
