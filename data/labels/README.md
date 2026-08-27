Human verdicts on rendered locations: the currency everything downstream is
denominated in.

```
batches.jsonl          what generated each batch — registered before its rows exist
rows/<batch>.jsonl     the labels, append-only, one row per location
eval_split.jsonl       the locations pinned to the evaluation side, forever
split.json             the recipe that drew that pin, and what it realized
```

Nothing outside `src/fractal_wallpapers/labeling/store.py` opens any of them, and
`tests/test_label_store.py` fails the build if a second module tries.

**A row carries its whole join.** The score *and* the complete render parameters,
on the same line — the family with every constant, the viewport, and what was
rendered from them — so a labeled example is never split across two files that
have to be reconciled later.

```json
{"schema": 1, "batch": "gather_v6", "recorded_at": "2026-07-05", "labeler": "matt",
 "origin": "human", "score": 4, "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
 "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
 "render": {"resolution": [1280, 720], "supersample": 4, "mode": "smooth", "maxiter": 8000}}
```

`score` is 1 to 4, one scale across every family. A 4 is a picture worth
releasing and is the unit of currency; a 3 is a genuine wallpaper and is worth a
tenth of one; 1 and 2 are recorded and are worth nothing. A 4 is a tier on the
same scale, not a separate head and not a new floor.

**The family and the viewport are what make a row a location**, and every reader
keys on both. Two Julia views at the same coordinates with different `c` are
different fractals, so a record that carried only the viewport would silently
merge them. Coordinates stay decimal strings, verbatim, and are normalized at the
reader. `origin` is `human`, or `rule:<rule_id>` where a stated rule cast the
score instead of a person — the one place the two are told apart.

**Append-only, resolved at read time.** An original is never modified. A verdict
that changes is a new row, and the canonical reader takes the latest per location
over `recorded_at`, then file name, then line. A row whose latest score is `null`
is a location somebody looked at and did not judge; it is read past rather than
counted, which is how a label is withdrawn.

**A batch is registered before it has rows** (`batches.jsonl`). The registration
says how the population was drawn and carries three fields. Two are independent
facts, one about the draw and one about the page: `score_unconditioned` — no model
score anywhere in the selection — and `anchored` — the page served a head's own
verdict prefilled, or ordered the rows by its score. The third is not a fact about
the draw at all but a pin: `eval_only` says a batch was bought as an instrument and
may never train, and it outranks whatever the other two imply. Eval-eligibility is
derived from all three and never stored — `eval_only or (score_unconditioned and
not anchored)` — and a batch nobody registered fails closed to neither. Both
shipped instruments, `blind_minibrot` and `blind_modes`, are eligible by the pin
alone: neither draw was score-unconditioned, so the two flags on their own would
put both of them train-side.

**That fail-closed is an object, and a contradiction is worse than an omission.**
`registry.UNREGISTERED` is what an unregistered batch reads as — not
score-unconditioned, therefore not eval-eligible, therefore train-side — because
being unconditioned is a claim about a draw and has to be made explicitly. An
omission is safe: the one thing it cannot do is put a population into the
evaluation side by accident. A **contradiction** has no safe side to fail to,
because the file itself holds both answers, so it aborts instead: registering one
batch twice is fine while both rows say the same thing — re-running a registration
step is how anybody finds out it already ran — but a second row disagreeing about
the method or the flags is refused by `registry.read`, naming both rows, where it
used to win silently and let a batch change sides between two readings of one file.
`registry.refuse_contradiction` is the same rule one step earlier, at the
**writer**, so the contradicting row never reaches the file at all; without it the
read-side guard is a trap rather than a guard — the append succeeds and every
later read raises until somebody edits by hand. The fix for a registration that
really was wrong is to correct the row **in place** and say so in `why`, never to
append a second answer. The disqualifying property for an instrument is model-driven
selection, not non-randomness: a systematic sweep qualifies, "the top of the run's
own ranked queue" does not, and an anchored page's labels measure agreement with
the head that suggested them however good the draw was.

**What a registration does not say is in
[`../batch_caveats.md`](../batch_caveats.md)**: how a live population was actually
assembled, and what a rate quoted off it without that is wrong about. Two of this
store's batches have an entry there.

**The split is drawn once and shipped.** `eval_split.jsonl` is the evaluation
side, one row per location, and re-deriving it adds without ever releasing:
a location on that side is pinned there on its `c`-inclusive coordinate, so a
re-render under a fresh identifier cannot spend the instrument. Groups — same
plane, near seed, overlapping frame — move whole, and a group with one
ineligible member goes to the training side entire. `split.json` records the
seed, the target share and the share that was actually realized; the two are not
the same number and the second is the one to quote.

**The pin is asserted at LOCATION granularity, and that is the whole of what it
has to survive.** `finished.pinned()` keys the pinned set on the location rather
than on the render — deliberately, because a later batch that re-renders a pinned
place under a fresh identifier would otherwise train on the instrument without
ever naming it. A render key would pin one picture and leave the place open; the
location key pins the place and every picture of it. It has fired: the
manufactured rare-colour drop of 2026-08-24 drew nine of its locations from a
pinned set, and `label ingest` withheld all nine before writing.

**The trainers are where that pin is enforced, and they assert on the same
coordinate.** `labeling.pins` owns it, and every training pass routes through it
rather than re-deriving a side: `models/train.py` calls `pins.assert_eval` over
the split it built, and `models/render_train.py` refuses on the *union* of both
finished stores' pins, because a joint head is read on both blind sheets and
either instrument is spent by one trespassing row. Both keys the `c`-inclusive
coordinate through `supply.location.key_of_row`, which is the same key this store
resolves on — so a location cannot be one place to the split and another to the
trainer that reads it.

## Where these came from

The 11,303 locations here are the source project's label corpus, imported once
(`fractal-wallpapers import-labels --source <repo>`) and never re-derived. Its
labels lived in three registered places behind an amendment overlay; every one of
them was resolved through that project's own canonical reader at import, folded
to one verdict per location as the maximum over its crops, and written flat. None
of the overlay, sidecar or registry machinery came with them, and every batch was
renamed and re-registered on the way in from that project's own registry — which
is why exactly four batches are eval-eligible here: they are the four whose draws
carried no model score.

The evaluation side realizes **8.9%** of the corpus against a 20% target (1,002
locations of 11,303), because that is all the score-unconditioned material there
is: 1,050 eligible locations, 48 of which lost their side to a biased neighbour
in the same group. It is thin everywhere and absent in one place —
`phoenix:classic` has no unconditioned draw at all, and no number of further rows
fixes that retroactively. It needs a draw, not a bigger corpus.

Two caveats travel with the rows and do not block anything. Rates are quoted
across three render regimes, because that corpus was collected across three; and
the two correction pages' labels are ceilings, because they were cast against a
head's own suggestion.

## The source is exhausted

Audited row by row on 2026-08-18, across all four scales and the whole source tree
rather than the corpora the importers already knew about. **Every human label over
there that can reach a store here is in one** — 12,637 location rows folding to the
11,303 above, 4,795 in `data/smooth_render/`, 2,810 in `data/strange_render/`, each
verified by rebuilding the row and looking its key up here rather than by trusting a
batch name. Nothing was importable and nothing was added. There is no further
migration to run, and a future one would find the same three numbers.

What is left there is left for a reason, and neither pile is waiting on effort:

* **Orphaned, and dropped.** 1,879 verdicts whose join is gone — two render-mode
  batches whose row manifests were never tracked, and three ranker sheets whose
  tile-to-location manifests were disposable. Plus 6,600 candidate tiers over 1,100
  palette-preference passes, which is the whole story of
  [`../palette_choice/README.md`](../palette_choice/README.md). A verdict whose
  picture nobody can find again is not a label, and re-deriving one from a seeded
  sampler with positional identifiers would attach it to a *plausible* picture,
  which is worse than not having it.
* **Unmappable, and Matt's to call.** 808 verdicts on scales no head here has: 448
  accept/reject/leak classes on rectangles inside a frame, 224 ratings of colormaps
  in the abstract, 135 same-or-distinct judgements on *pairs* of locations, and one
  on a nucleus. The first and third still carry live joins; what they lack is a
  question this project asks.
