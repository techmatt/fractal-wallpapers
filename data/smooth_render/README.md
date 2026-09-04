Human verdicts on the smooth coloring, judged as wallpapers — the judge that decides which finished
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
{"schema": 1, "batch": "blind_minibrot", "recorded_at": "2026-08-11T01:54:36", "labeler": null, "origin": "human", "score": 4,
 "family": {"kind": "multibrot", "degree": 3}, "viewport": {"center_re": "-0.11784803243926409", "center_im": "0.803838676554543", "width": "4.056617606305728e-05"},
 "mode": "smooth", "mode_params": {}, "curve": "linear", "colormap": "cmr.voltage",
 "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": true, "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
 "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 23409, "filter": "lanczos3"}, "partition": "multibrot3"}
```

`score` runs 1 to 4: 1 does not work, 2 has structure but is unremarkable, 3 is a genuine
wallpaper and is the floor a picture ships at, 4 is the best of those. Four tiers
on one scale, not a separate head and not a new floor.

**The evaluation side is pinned, not drawn.** Every batch here conditions on
quality through the location head before its page exists, so none of them is an
unbiased draw and no rate read on one is a base rate. What separates them is
whether the page served a head's own verdict prefilled: 12 of the 16 that hold rows did,
and their labels measure agreement with that head. `blind_minibrot` is the one that did
not, and it is registered `eval_only` — bought to referee two heads on unanchored
labels, and spent the moment it enters a training split. The pin is asserted on
the **location**, so a later batch that re-renders a pinned place under a fresh
identifier cannot spend it by not naming it.

**One hundred and twenty rows in here are revisions of `strange_render` originals** —
thirteen appended 2026-09-03 and the remaining 107 on 2026-09-04 — which is why this
store reads **6,300** rows against the 6,180 the batch arithmetic below gives. Each is an `itinerary` render whose modulate texture measured
flat at label geometry — so the picture is the smooth field spent by rank bit for bit
and the verdict is this judge's — carried over under its own batch with a `revision`
block naming the original's file, line and recorded time. The originals stay in the
other store; see `data/strange_render/README.md` for why a register entry alone could
not do this. **None sits at a place this store's pinned set holds, and three candidates
were skipped for exactly that** — `sparse_mode_head_top` lines 504, 505 and 515, whose
places are pinned to this store's evaluation side, so carrying them would have trained
this judge on its own instrument. They stay in the other store, unrevised.

The 2026-09-04 pass registered `itinerary_promotion`, `sparse_mode_head_top` and
`p_ge4_calibration_strange` here, with their `strange_render` flags copied verbatim so a
carried row's eval side and provenance are the original's. `manufactured_rare_colors` was
already registered in both. 104 crops were copied across and three were already present
under the same name, `renders.job_name` being head-independent.

**A verdict cast on a pinned location never reaches these rows.** The pin is asserted
on the location and `blind_minibrot` is derived from the pinned places, so `label
ingest` withholds such a verdict before it writes rather than growing a blind sheet
by a row that was not cast blind. No drop has yet had one here — the nine the
manufactured rare-colour drop lost were on the *other* store's pin. Its rows at those
places are stored and are EXCLUDED from training by the strict split, which is a
different rule and is the trainer's.

**The newest batch is this judge's own top end, and it does not order it.**
`judge_band_20260903`'s smooth sheet is 123 cards — 118 of them S1, the band
`P(>=4)` in [0.40,0.95) taken top-down, which over a 3,018-location band landed in
a 0.0086-wide sliver at 0.9414–0.9500. All 123 route here by `finished.routes_to`
on the built join, and the ingest resolved 123 of 123 with nothing withheld, **123
fresh and 0 revised**, moving this store from 6,057 rows to **6,180** and from
2,821 locations to **2,944**. Anchored and score-conditioned, so it is training
material. Where the judge is surest, two thirds of what it offers is a three: q4
**0.339** and q3+ 0.975 over the 118 `[human n=118]`, and Spearman(`P(>=4)`, tier)
is 0.007 on the draw column and 0.113 at label geometry — no ordering, and none
recovered by re-scoring, which spreads the same pictures over 0.700–0.996 and
leaves the tiers where they were. The page prefilled 4 on all 123, so its 64.2%
correction rate is downward disagreement and nothing else. Both readings and the
other two slices are in [`../batch_caveats.md`](../batch_caveats.md) under
THREE-SLICES.

**The source corpus is complete here.** All 4,795 verdicts it holds are in these
rows, checked on 2026-08-18 by rebuilding each one and looking its key up — not by
counting batches. Its eighth batch is absent on purpose: 364 renders were built for
it and nobody ever judged them, so there is no verdict there to miss. The whole-tree
accounting, including what stayed behind and why, is in
[`../labels/README.md`](../labels/README.md).
