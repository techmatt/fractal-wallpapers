Human verdicts on the strange colorings, judged as renderings — the judge that decides which finished
pictures survive.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the verdicts, append-only, one row per finished render
eval_split.jsonl       the renders pinned to the evaluation side, permanently
split.json             why that pin is the whole evaluation side, and what it holds
```

Nothing outside `src/fractal_wallpapers/labeling/finished.py` opens any of them.

**A row carries its whole join, and the join is a picture rather than a place.**
One location appears here many times — same coordinates, different coloring, and
genuinely different verdicts — so a row records everything it takes to make that
picture again: the family with every constant, the viewport, the mode with its
own settings, the curve the field is read through, the map, and every knob of the
palette pass.

```json
{"schema": 1, "batch": "baserate_audit", "recorded_at": "2026-08-11T15:17:30", "labeler": null, "origin": "human", "score": 2,
 "family": {"kind": "multibrot", "degree": 3}, "viewport": {"center_re": "0.17386469370365126", "center_im": "0.7502825947552454", "width": "5.927677479331776e-05"},
 "mode": "tia", "mode_params": {}, "curve": "linear", "colormap": "gnuplot",
 "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": true, "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
 "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 6341, "filter": "lanczos3"}, "partition": "multibrot3"}
```

`score` runs 1 to 4: 1 does not work, 2 has structure but is unremarkable, 3 is a
rendering worth keeping, 4 is one of the best of them. The **imported** rows stop at
3 — the source project collected this corpus on three tiers and there is no fourth to
read out of it — and every row cast here since can reach 4. 145 of these 3,322 do, and
all 145 were recorded in this repository. That ceiling is a fact about pages served
years ago rather than about this store, so it lives on the importer as
`finished_import.SOURCE_SCALE` and never on the scale: this project's own is
`finished.SCALE`, and it is 1..4 for both kinds.

**The evaluation side is pinned, not drawn.** Every batch here conditions on
quality through the location head before its page exists, so none of them is an
unbiased draw and no rate read on one is a base rate. What separates them is
whether the page served a head's own verdict prefilled: 11 of 12 did,
and their labels measure agreement with that head. `blind_modes` is the one that did
not, and it is registered `eval_only` — bought to referee two heads on unanchored
labels, and spent the moment it enters a training split. The pin is asserted on
the **location**, so a later batch that re-renders a pinned place under a fresh
identifier cannot spend it by not naming it.

**A verdict cast on a pinned location never reaches these rows.** The pin is asserted
on the location, and `blind_modes` is derived from the pinned places, so a later drop
that re-renders one of them would grow the blind sheet by a row that was not cast
blind. `label ingest` withholds those verdicts before it writes, names the units, and
leaves them in the export. It has happened once: the manufactured rare-colour drop of
2026-08-24 drew nine of its locations from this store's pinned set, and nine of its
246 verdicts are in `labels/` and not here.

**Forty rows in here are `smooth`, which this judge does not answer for.** They came
in with the `rare_palette` batch, and `hunt.kind_of` routes `smooth` to
`smooth_render` — every other mode is this store's. Originals are never modified, so
they stay exactly where they are: what changed on 2026-08-27 is that
`finished.check` now refuses a row whose mode routes elsewhere, so the writer cannot
make another one, and `finished_train.population` derives the exclusion at the read
rather than in the data. They cost this store's per-mode table a `smooth` row at 40
verdicts and second place by P(human>=3) — 0.625, behind `exp_smoothing`'s 0.631 —
and 7 of their 40 locations also carry a `smooth_render` row, which double-weights
those places across the two stores. Pooled, they move `>=3` from 0.2670 to 0.2628 and
`>=4` from 0.0636 to 0.0635. No render key of theirs is in both stores and no eval
pin holds one, so the evaluation side was never touched.

**And 110 rows in here are `itinerary` renders whose texture said nothing, which
routes them to `smooth_render` too.** A modulate shifts its base's palette position
by a normalized address field; where that field has no span the shift is zero
everywhere and the picture is the smooth field spent by rank *bit for bit*. So
those rows are the smooth judge's on the same rule the 40 above are, arrived at by
a different route — they are not mislabelled, the mode they name is the mode that
was rendered. **110 raw rows, 107 resolved renders of the 201 `itinerary` holds
(53.2%)**, measured 2026-08-31 off the engine's own `texture_flat` report;
`data/coloring/texture_flat.jsonl` is the register and `finished.routes_to` is the
call every reader makes.

Originals stay where they are, as ever, and the re-attribution is at the read.
What it costs this store's per-mode table is the whole of `itinerary`'s promotion
case: the mode reads **44 fours in 201 renders (21.9%)** as recorded and **16 in 94
(17.0%)** on the rows that are really its own, which is fourth of the seventeen
rather than first. The 107 that leave read 26.2%. Tier-3-or-better does not move at
all — 54.2% against 54.3% — so the whole difference is where the fours sat.

**No eval pin is touched.** None of the 107 comes from an `eval_only` batch
(`blind_modes`, `seated_and_head_top`), and none stands at a place this store's
pinned set holds; they are 59 `itinerary_promotion`, 40 `sparse_mode_head_top`, 6
`manufactured_rare_colors` and 2 `p_ge4_calibration_strange`, every one registered
`eval_only=false, score_unconditioned=false`. Three of them do stand at a place
**`smooth_render`'s** pinned set holds, which is worth knowing and costs nothing
today: the rows are physically in this store's files, so the smooth head's
population never reads them and cannot spend its instrument on them. A future
batch that re-rendered one of those three places for the smooth store would be
trespassing, and `intake`'s pin check is what would catch it.

**The newest batch buys the modes with the fewest keepers.** `under_seen_modes`,
2026-08-27: 504 verdicts, 56 on each of nine modes, drawn as the render judge's own
unfiltered top of each mode over the whole candidate ledger. All 504 route here —
`hunt.kind_of` sends everything but `smooth` to this store — and the ingest resolved
504 of 504 with nothing withheld and nothing already stored. It is registered
`score_unconditioned=false`, so it is training material and no rate off it is an eval
rate. It moved this store from 3,573 rows to 4,077 and from 1,149 locations to 1,524,
and it lifted `smooth_mean_angle`, `gaussian_int`, `smooth_curvature` and
`smooth_trap_circle` — the four thinnest by stored `>=3` count — by about 40% each.
Under-seen here means keepers, not rows: `direct_trap_multiply` was already this
store's largest mode at 338 rows and had 73 of them at `>=3`.

**And the newest batch buys a parameter space rather than a mode.**
`dtm_variants_20260902`, 2026-09-03: 188 verdicts, one per location, over four
`direct_trap_multiply` mode-param cells cut to answer whether the mode's whitewash
is a defect of the settings. All 188 route here and the ingest resolved 188 of 188
with nothing withheld, nothing already stored and nothing revised, moving this store
from 5,110 rows to 5,298 and from 2,001 locations to 2,174. It is anchored and
score-conditioned, so it is training material. Two readings off it are worth having
and one is not: the mode's tier-4 rate rises from 1.8% at the shipped settings to
21.8% under the variants, and the render judge's chroma penalty reproduces at
Spearman = -0.291 while a person's tiers sit at +0.023 — but the **per-cell** rates
are not a comparison between settings, because the page is one card per location and
the card is the judge's own argmax over the four. That is
[`../batch_caveats.md`](../batch_caveats.md)'s ARGMAX-PER-PLACE entry, and the
matched page that would settle it has never been served.

**And the newest batch buys a plane at the judge's own crossing, and finds the
judge cannot see it.** `phoenix_q3q4_20260903`, 2026-09-03: 105 verdicts here beside
95 in `smooth_render`, one card per location, drawn as the 100 phoenix locations
immediately above and the 100 immediately below the shipped judge's
`P(>=4) = 0.5`. Routing was asked of `finished.routes_to` on each built join rather
than of the ledger's stored flag — 105 of 105 route here — and the ingest resolved
105 of 105 with nothing withheld, **103 fresh and 2 revised**, moving this store from
5,298 rows to **5,403** and from 2,174 locations to **2,276**. It is anchored and
score-conditioned, so it is training material. The reading worth having is negative:
inside the band the judge's score does not order a person's tiers — Spearman
**+0.020** on the draw column, **+0.192** at label geometry over 105 rows — while the
same judge separates keepers from the rest at label geometry, q3+ **94.0%** above 0.5
against **70.9%** below. The per-mode table off these rows is thin and argmax-shaped
and both caveats are in [`../batch_caveats.md`](../batch_caveats.md) under BAND-DRAW,
which also records the six cards whose places were already labelled.

**What a registration does not say is in
[`../batch_caveats.md`](../batch_caveats.md)**: how a live population was actually
assembled, and what a rate quoted off it without that is wrong about. Four of this
store's batches have an entry there — including `under_seen_modes`, whose page was
swept from position 270 and whose last 235 rows are the head's own decode restated
rather than a verdict.

**The source corpus is complete here, and no fourth tier was collectable over there.**
All 2,810 verdicts of the five batches are in these rows, checked on 2026-08-18 by
rebuilding each one and looking its key up. Two earlier sheets on this same scale —
1,500 verdicts across a pilot and a scale sweep — did not come, and cannot: their row
manifests were never tracked and their identifiers are positional, so a re-derivation
would bind each verdict to a plausible picture rather than to its own. The whole-tree
accounting is in [`../labels/README.md`](../labels/README.md).
