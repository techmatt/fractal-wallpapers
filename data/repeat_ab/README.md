Human verdicts on whether **repeating the gradient improves a picture that is
already good at 1×** — a comparison between two renders of one place, not a
judgement of either on its own.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the verdicts, append-only, one row per location
```

Nothing outside `src/fractal_wallpapers/labeling/attributes.py` opens any of them.
It is the second store that module owns and the first **paired** one — see
`Attribute.paired`.

## ⚠ This scale is not the 1–4 quality scale

```
repeat_worse    1   the repeat is the worse picture
neutral         2   no difference
repeat_better   3   the repeat is the better picture
```

A `3` here says *the repeat won*. It does **not** say *tier 3*. There is no
rescaling, offset or other transformation that makes these commensurable with
`smooth_render`, `strange_render` or `gallery_grade`, because they are answers to
a different question: those three ask how good one picture is, this asks which of
two is better. **Putting a verdict from here into a quality store corrupts every
reading taken off that store.**

**The guard is an absent field.** A row carries `class` and no `score` key at all,
and `attributes.check` refuses one that carries a `score` — the same protection
`data/spiral/` stands behind, and the reason this store could be *declared* rather
than built. Every quality reader in this repository keys on `score`, so a store
whose three classes had been written as `1`, `2` and `3` would read as a corpus of
ones, twos and threes the first time somebody pooled the stores by field name.

The page still casts numbers, because the rig's export is one number per unit for
every store there is; the number becomes a class once, at ingest.

## The unit is ONE picture carrying two renders

A tile is a single composite: the 1× render on the **left**, the repeat on the
**right**, equal halves at `sheets.LABEL_RESOLUTION`, the same crop, a 6-pixel
separator, nothing written on the image. **The side order is fixed across a
sitting** and the sheet manifest records it in `render.sides` — a reading that
assumed the halves alternated would report the opposite result with nothing
looking wrong.

One picture and not two because the comparison this store collects is the one an
eye makes in a single glance; two cards would let a labeler scroll one out of view
and answer from memory.

## A row keys on the place and carries BOTH recipes

```json
{"schema": 1, "attribute": "repeat_ab", "batch": "<batch>", "recorded_at": "…Z",
 "labeler": "matt", "origin": "human", "class": "neutral",
 "family": {…}, "viewport": {…},
 "render": {"mode": "smooth", "mode_params": {}, "curve": "linear", "colormap": "<map>",
            "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, …},
            "resolution": [1280, 720], "supersample": 2, "maxiter": 12840, "filter": "lanczos3"},
 "partition": "<partition>", "sheet": "<sheet>", "unit": "u0001", "suggested": 2,
 "selected_on": {"candidate": "<baseline key>", "variant": "<variant key>",
                 "folded": false, "cycles": 2.0, "traversals": 2.0, "phase": 0.0,
                 "regime": "640x360ss2", "p_fine": …, "p_ge4": …, "p_ge3": …},
 "reading": {"baseline": {"p_ge2": …, "p_ge3": …, "p_ge4": …},
             "variant": {…}, "read_at": {…}}}
```

`render` is the **baseline** half, whole, in the shape every other store spells a
finished render. The variant is the same block with `Palette.cycles` moved and
nothing else, and `selected_on` names both recipe keys so the pair is recoverable
after the sheet directory is swept. Latest-wins resolves on the **location**,
exactly as `spiral` does.

`reading` is what the shipped render judge said about each half at the geometry
the labeler saw. It is a **covariate and never a verdict**: it is there so the
head's own direction can be read against Matt's without re-rendering the sitting,
and the page never saw it.

## There is no pin here, and that is a fact about the sittings so far

`spiral` reserves a fifth of its own sitting because a probe is fitted on it.
Nothing is fitted on this store, and nothing may be without Matt saying so, so
there is no split to protect and `eval_split.jsonl` does not exist. A sitting that
was ever going to train something would draw one first, through `label pin`, the
same way — see `data/spiral/README.md`.

## What is in here today — NOTHING, and that is the current state

**No batch is registered and no row has ever been written.** `batches.jsonl` does
not exist, which `labeling.registry.read` treats as an empty registry — the state
a fresh checkout is in. The store is *declared* and unused, which is the shape the
absent-`score` guard above made possible in the first place.

One sitting was drawn and let go. `repeat_ab_ckpt121` cut 250 composite tiles at
250 places on 2026-09-11, was part-labelled, and Matt parked palette replication
and ruled the partial verdicts released rather than kept — so the sheet, its 1,000
pictures and the registration were deleted on 2026-09-12 without a row ever being
ingested. The draw's own numbers survive in
[`curation/LEGS.md`](../../src/fractal_wallpapers/curation/LEGS.md)'s *What the
first sitting came to*; nothing here depends on them.

A later sitting registers its own batch before its rows exist, the way every other
store does.
