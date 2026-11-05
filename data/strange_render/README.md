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
{"schema": 1, "batch": "<batch>", "recorded_at": "<iso time>", "labeler": null, "origin": "human", "score": 2,
 "family": {"kind": "multibrot", "degree": 3}, "viewport": {"center_re": "<decimal>", "center_im": "<decimal>", "width": "<decimal>"},
 "mode": "tia", "mode_params": {}, "curve": "linear", "colormap": "gnuplot",
 "recipe": {"gamma": 1.0, "cycles": 1.0, "phase": 0.0, "reverse": false, "mirror": true, "transfer": {"kind": "value"}, "rolloff": {"kind": "none"}},
 "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 6341, "filter": "lanczos3"}, "partition": "multibrot3"}
```

`score` runs 1 to 4: 1 does not work, 2 has structure but is unremarkable, 3 is a
rendering worth keeping, 4 is one of the best of them. The **imported** rows stop at
3 (the source project collected this corpus on three tiers), and every row cast here
can reach 4. That ceiling is a fact about the source, so it lives on the importer as
`finished_import.SOURCE_SCALE` and never on the scale: this project's own is
`finished.SCALE`, 1..4 for both kinds.

## The evaluation side

**The evaluation side is pinned, not drawn.** Every batch here conditions on quality
through the location head before its page exists, so none is an unbiased draw and no
rate read on one is a base rate. Most pages served a head's own verdict prefilled, and
their labels measure agreement with that head. The **blind** batches (`blind_modes`, and
`blind_palettes_20260905`, a matched-pair sheet of a new colormap drop against the shipped
library) are registered `eval_only`: bought to referee on unanchored labels, and spent
the moment they enter a training split. There is no further unanchored reading to spend.
`seated_and_head_top` is `eval_only` too, though anchored: a population the head selected
is spent as an instrument the moment it trains one.

**The pin is asserted on the location**, so a later batch that re-renders a pinned place
under a fresh identifier cannot spend it by not naming it. **A verdict cast on a pinned
location never reaches these rows**: `label ingest` withholds it before writing, names the
units, and leaves them in the export. `finished.assert_pin_holds` checks both heads.

## Rows this judge does not answer for

**Routing is decided at the read, and originals are never modified.**
`finished.routes_to` is the call every reader makes: `hunt.kind_of` sends `smooth` to
`smooth_render` and every other mode here, and a render whose modulate texture said
nothing (`texture_flat`) routes to `smooth_render` too, because a modulate whose address
field has no span is the smooth field spent by rank, bit for bit. Those rows are not
mislabelled: the mode they name is the mode that was rendered.

- **`smooth` rows** that arrived with an early batch stay where they are;
  `finished.check` refuses a new row whose mode routes elsewhere, and
  `finished_train.population` derives the exclusion at the read.
- **Flat-textured rows**: `data/coloring/texture_flat.jsonl` is the register, keyed on the
  render geometry, and `finished.append` extends it at ingest. Each flat-textured row here
  has a **revision row** in `smooth_render` (same verdict, same render identity, its own
  batch, plus a `revision` block naming this store's file, line and recorded time), with
  the originating batch registered there with its flags copied verbatim. `finished.resolved`
  decides a row's kind by which store's directory it was read from, never by asking the
  register, which is why the revision row is needed.
- **Three flat rows stay here, flat and unrevised, by design**: they stand at places pinned
  to the **smooth** store's evaluation side, so a revision row would train that judge on
  its own instrument. That is the correct end state.

A future batch that re-rendered a place pinned in the *other* store would be
trespassing; `intake`'s pin check is what catches it.

## What a registration does not say

**[`../batch_caveats.md`](../batch_caveats.md)** holds how each live population was
actually assembled and what a rate quoted off it without that is wrong about (an
argmax-per-place page, a band draw, a mode-balanced top-of-band slice, a page swept from
mid-sheet whose tail restates the head's decode). Per-batch readings live there and in
the batch's own report, not here. A correction sheet cannot measure a judge, and an aimed
sitting is not a base rate.

**The source corpus is complete here.** All verdicts of the five imported batches are in
these rows, checked by rebuilding each and looking its key up. Two earlier sheets on the
same scale did not come and cannot: their row manifests were never tracked and their
identifiers are positional, so a re-derivation would bind each verdict to a plausible
picture rather than its own. The whole-tree accounting is in
[`../labels/README.md`](../labels/README.md).
