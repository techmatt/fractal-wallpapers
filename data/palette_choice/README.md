Everything the palette head is made of, as text. Not `data/palettes/`, which
holds the colormaps themselves — this holds *choices between* them.

```
pool.json               the maps a colorize-time candidate set may hold
candidate_sets.jsonl    377 real candidate sets two production runs recorded
rows/<partition>.jsonl  the distillation corpus: one row per machine-labeled candidate
split.json              the held-out split, the hard/uniform mix, and who labeled the corpus
held_out.jsonl          locations a draw has held out, which no later draw may teach
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

One row per real colorize decision, vendored from **every** colorize-path batch
the source project recorded: a 180-row sheet spanning all ten partitions and a
197-row blind slice of multibrot3 and mandelbrot minibrots, both ranked by the
head this one is distilled from. Each row carries the location with every family
constant, the geometry, the palette flavour a real deficit model assigned it, the
candidate maps its head really chose between in library order, and which one it
picked. A set id names its batch, because it is the join key every score file
quotes.

Both batches are here for a reason that is arithmetic: a share measured on 180
sets carries an interval of about ±0.07, wide enough that a reading can straddle
the bar it is read against and say nothing; 377 sets carry about ±0.05. The two
batches are **not alike** — one is evenly spread and the other is deep in two
partitions — so every arm is reported per batch as well as pooled.

They are vendored so the acceptance read is repeatable without the other
repository, exactly as the finished-render yardsticks are. **None of their
locations may enter the corpus**: a set the head trained on is not an instrument,
and `tests/test_palette_sets.py` fails the build if one does.

The reconstruction of a set — a flavour's pool members in library order, capped
at 32 — is checked rather than trusted: every one of the recorded winners must
fall inside the set rebuilt for it, and the extraction writes nothing if a single
one does not.

## `rows/` — the corpus, sharded by partition

One row per candidate: the teacher's score *and* the location *and* the whole
recipe that made the picture, on the same line. `origin` is `teacher` on every
row and `teacher` carries the sha256 of the weights that cast it, so a row says
which function labeled it rather than merely that a machine did.

Sharded by partition because that is the axis the draw is apportioned on. These
are the repository's only tracked files over a mebibyte, and the size rule in
`tests/test_history_purity.py` carries a named exemption for this directory —
split from the binary rule, which still refuses a blob here.

A row also says what **kind** of set it belongs to. A `uniform` set is 32 maps
drawn from the pool; a `hard` one is a map and the 31 nearest it in palette space
(`src/fractal_wallpapers/palettes/space.py`), which is how a training set is made
to ask the near-tie question a production flavour asks. `anchor` names the map a
hard set was built around. The mix is declared before the draw and `split.json`
carries both the declared share and the measured tightness that checks it.

## `held_out.jsonl` — locations that may never move back

A corpus that grows must not grow into its own held-out side: the epoch this head
ships at is chosen on the held-out distillation loss, and a location that was
scoring that loss under one draw and teaching the model under the next makes the
two readings incomparable in the direction that flatters the second. So the
held-out side is data. The file only ever gains rows, and the next split pins
every location it names before drawing the rest of the share around them.

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
