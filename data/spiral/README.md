Human verdicts on whether a location **is a spiral** — an attribute of the place, not a
judgement of its quality.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the verdicts, append-only, one row per location
eval_split.jsonl       the locations reserved as this store's evaluation side
split.json             how that reservation was drawn, and what share it realized
```

Nothing outside `src/fractal_wallpapers/labeling/attributes.py` opens any of them.

## This is not a fourth judge

The other three stores ask how *good* something is, all of them on one 1–4 scale.
This one asks what a place *is*, cast into two named classes:

```
spiral       a pure enough spiral that a gallery cap should count it
not_spiral   enough non-spiral content that the cap should not
```

The answer exists to be **counted** — it feeds a share cap in the solve and a
linear probe on the neutral embeddings — and never to be maximized. There is no
floor here, no tier, and nothing that pools with a quality corpus.

**The guard is an absent field.** A row carries `class` and no `score` key at
all, and the writer refuses one that carries a `score`. That is deliberate rather
than tidy: every quality reader in this repository keys on `score`, so a store
whose two classes had been written as `1` and `2` would read as a corpus of ones
and twos the first time somebody pooled the stores by field name. The page still
casts numbers — the export is one number per unit for every store there is — and
the number becomes a class once, at ingest.

## A row keys on the place and carries the picture

```json
{"schema": 1, "attribute": "spiral", "batch": "spiral_500_20260903", "recorded_at": "2026-09-04T00:00:00Z",
 "labeler": null, "origin": "human", "class": "spiral",
 "family": {"kind": "julia", "degree": 5, "c": ["-0.858", "0.590"]},
 "viewport": {"center_re": "0.105", "center_im": "-0.139", "width": "0.407"},
 "render": {"mode": "threads", "mode_params": {}, "curve": "linear", "colormap": "twilight_shifted",
            "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": true,
                       "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
            "resolution": [1280, 720], "supersample": 2, "maxiter": 8000, "filter": "lanczos3"},
 "partition": "julia:multibrot5", "selected_on": {"candidate": "<key>", "p_ge4": 0.99, "rank": 0.82}}
```

Latest-wins resolves on the **location**, exactly as the location corpus does: a
later sitting that draws the same place under a different palette is a second
opinion about the same place and supersedes the first. But the *picture* the
labeler judged was a finished render — the one a seating pass would reach for at
that place — so the whole render block travels beside the key. Nothing keys on
it. It is there so a sitting can be rebuilt, and so a later reading can ask
whether a `not_spiral` was about the place or about one unlucky coloring.
`selected_on` is the reading the row was **drawn** on, at candidate geometry, and
it is what a probe needs in order to say what population it measured.

## The reservation is intra-batch, and that is why it is in a file

`eval_only` in the registry is a flag on a **batch**. A sitting that reserves a
fifth of its own units has no second batch to hang it on: putting the reserved
units in one would print a different batch name on their cards and tell the
labeler exactly which ones they were. So the reservation is a seeded uniform draw
over the sitting's own plan, taken by `fractal-wallpapers label pin` **before any
verdict exists**, and written here.

**Reserving is not withholding.** The verdicts on those places are collected like
every other, and the ingest does not assert the pin — a hundred of the five
hundred sit on it by construction, and refusing them would refuse the drop the
reservation was made to collect. What the pin forbids is *training* on them, and
that is asserted by whoever builds a split, through
`attributes.assert_pin_holds`. This is the one place an attribute store's
guarantees are weaker than a finished store's, and the reason is that over there
the evaluation side is a whole batch cut blind.

## What is in here today

`spiral_500_20260903` — 500 locations drawn uniformly at seed `20260903` over the
9,086 locations holding at least one candidate row clearing its own mode's bar in
`headroom.bars`, one unit each, represented by the best-ranked clearing row a
seating pass would reach first. 100 of them are reserved, at the same seed.

It is registered `score_unconditioned: false`, and that is the flag failing
closed rather than a criticism of the draw: the draw *among* the 500 is uniform
and model-free, but the population it draws from is the pool, whose membership is
the render judge's `P(≥4) ≥ 0.5`. So no rate measured here is a rate about
fractal space; it is a rate about **the places a gallery could seat**, which is
the population the share cap will act on and therefore the one worth measuring.
`data/batch_caveats.md` carries the rest.
