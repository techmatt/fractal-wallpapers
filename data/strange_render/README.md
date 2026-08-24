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
whether the page served a head's own verdict prefilled: 7 of 8 did,
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

**What a registration does not say is in
[`../batch_caveats.md`](../batch_caveats.md)**: how a live population was actually
assembled, and what a rate quoted off it without that is wrong about. Three of this
store's batches have an entry there.

**The source corpus is complete here, and no fourth tier was collectable over there.**
All 2,810 verdicts of the five batches are in these rows, checked on 2026-08-18 by
rebuilding each one and looking its key up. Two earlier sheets on this same scale —
1,500 verdicts across a pilot and a scale sweep — did not come, and cannot: their row
manifests were never tracked and their identifiers are positional, so a re-derivation
would bind each verdict to a plausible picture rather than to its own. The whole-tree
accounting is in [`../labels/README.md`](../labels/README.md).
