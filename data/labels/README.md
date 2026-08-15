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
says how the population was drawn and carries two flags: `score_unconditioned` —
no model score anywhere in the selection — and `anchored` — the page served a
head's own verdict prefilled, or ordered the rows by its score. Eval-eligibility
is derived from the two and never stored, and a batch nobody registered fails
closed to neither. The disqualifying property for an instrument is model-driven
selection, not non-randomness: a systematic sweep qualifies, "the top of the run's
own ranked queue" does not, and an anchored page's labels measure agreement with
the head that suggested them however good the draw was.

**The split is drawn once and shipped.** `eval_split.jsonl` is the evaluation
side, one row per location, and re-deriving it adds without ever releasing:
a location on that side is pinned there on its `c`-inclusive coordinate, so a
re-render under a fresh identifier cannot spend the instrument. Groups — same
plane, near seed, overlapping frame — move whole, and a group with one
ineligible member goes to the training side entire. `split.json` records the
seed, the target share and the share that was actually realized; the two are not
the same number and the second is the one to quote.

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
