Everything the palette head is made of, as text. Not `data/palettes/`, which
holds the colormaps themselves — this holds *choices between* them.

```
pool.json               the maps a colorize-time candidate set may hold
candidate_sets.jsonl    180 real candidate sets a production run recorded
rows/<partition>.jsonl  the distillation corpus: one row per machine-labeled candidate
split.json              the held-out split, and who labeled the corpus
```

Nothing outside `src/fractal_wallpapers/models/palette_sets.py` and
`palette_corpus.py` opens any of them.

## The honest story

This head is **not trained on human labels, and there are none here to train it
on.** The other three judges learned from thousands of verdicts a person cast;
the corpus that taught this one's ability — which of these colourings of this
place looks best — is a set of per-query tiered judgements that lives in the
source project and did not come across. So the head is **distilled from that
project's pretrained palette-preference head**: the teacher scores pictures made
*here*, by this engine through this colormap library, and the student is trained
to reproduce its whole score vector rather than only its winner.

What that buys is regenerability. `rows/` is the training run's entire input, in
text, seeded, in the history: a checkpoint is a fact about one run, and this is
the thing the run can be done again from — a new backbone, a new loss, a bug
found in the loop, all of it re-runnable without the source project and without
asking anybody for more labels. What it costs is stated plainly wherever this
head is read: the ground truth is a model. The student is **approximately
equivalent** to the teacher, and if the teacher has a taste nobody shares, this
head has inherited it exactly.

## `candidate_sets.jsonl` — the instrument

One row per real colorize decision, vendored from the source project's last
colorize-path batch. Each carries the location with every family constant, the
geometry, the palette flavour a real deficit model assigned it, the candidate
maps its head really chose between in library order, and which one it picked.

They are vendored so the acceptance read is repeatable without the other
repository, exactly as the finished-render yardsticks are. **None of their
locations may enter the corpus**: a set the head trained on is not an instrument,
and `tests/test_palette_sets.py` fails the build if one does.

The reconstruction of a set — a flavour's pool members in library order, capped
at 32 — is checked rather than trusted: every one of the 180 recorded winners
must fall inside the set rebuilt for it, and the extraction writes nothing if a
single one does not.

## `rows/` — the corpus, sharded by partition

One row per candidate: the teacher's score *and* the location *and* the whole
recipe that made the picture, on the same line. `origin` is `teacher` on every
row and `teacher` carries the sha256 of the weights that cast it, so a row says
which function labeled it rather than merely that a machine did.

Sharded by partition because that is the axis the draw is apportioned on, and
because a tracked file over a mebibyte fails `tests/test_history_purity.py`.

What is *not* on a row is folding — whether the map is mirrored to hide its seam.
That is a property of the map, read from `data/palettes/<name>.json` here as
everywhere else in this repository, and a row that carried it could disagree with
the map it names.

## `pool.json` — the shipped palette pool

The maps a colorize may choose between: the source project's production pool as
this repository holds it, 700 of its 987. A map is here because a tracked corpus
row or a vendored candidate set names it — nothing was brought across to round
the number up. Every candidate set is therefore complete, and the pool the corpus
draws from is a subset of the production one.
