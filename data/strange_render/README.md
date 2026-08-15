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

`score` runs 1 to 3: 1 does not work, 2 has structure but is unremarkable, 3 is a rendering
worth keeping. Three tiers, not four: this corpus was collected on three and there
is no fourth to read, which is why the ceiling lives on the store.

**The evaluation side is pinned, not drawn.** Every batch here conditions on
quality through the location head before its page exists, so none of them is an
unbiased draw and no rate read on one is a base rate. What separates them is
whether the page served a head's own verdict prefilled: 4 of 5 did,
and their labels measure agreement with that head. `blind_modes` is the one that did
not, and it is registered `eval_only` — bought to referee two heads on unanchored
labels, and spent the moment it enters a training split. The pin is asserted on
the **location**, so a later batch that re-renders a pinned place under a fresh
identifier cannot spend it by not naming it.
