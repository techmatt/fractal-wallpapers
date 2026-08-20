The four judges as code: their architectures, training loops, and inference paths.

One vertical per head, in the order it runs. For the **location** head, which
judges a place before any colour is applied: `tiles` builds the pictures,
`head` and `dataset` say what a training example is, `train` runs the loop,
`scoring` reads a checkpoint over a population, `acceptance` judges the result
against a bar written down beforehand.

For the two **finished-render** judges, which answer the question after it —
does this particular colouring of a place work — the same five stages exist
under their own names: `renders` regenerates every judged picture from the recipe
its row carries, `finished_train` runs the loop over pictures rather than places,
`finished_scoring` reads a checkpoint, `finished_acceptance` judges it against its
own pre-registered bar. They share `head` (the ordinal model, the CORN loss and
the reading of its cutpoints as unconditional probabilities), `metrics`, and
`ship` — the fp16 cast, the re-read, the agreement check and the hash are the
same for every head, so they are written once and a four-field record says where
each head's pieces are.

The fourth, the **palette** head, is the one that is not trained from human
labels — there are none here to train it on — so it has two stages the others do
not. `palette_sets` vendors the real candidate sets a production colorize run put
in front of the head it is distilled from; `palette_corpus` generates a corpus by
rendering candidates here and asking that teacher (`palette_teacher`) about each.
Most of that corpus is made *hard on purpose* — a set is a map and its nearest
neighbours in `palettes/space`, so it asks the near-tie question a production
flavour asks instead of waiting for a uniform draw to ask it by accident.
After that the shape is the same: `palette_train` runs the loop over sets rather
than pictures, `palette_scoring` reads a checkpoint, `palette_acceptance` judges
it against its own pre-registered bar. Its model, transform and loss are in
`palette_head`, separately from `head`, because its answer is a choice inside a
set and not a tier on an ordinal scale — but it ships through the same `ship`,
supplying only its own agreement statistic.

## Both picture caches are addressed by their recipe

The **finished-render** cache (`renders`) and the location head's **deploy view**
(`location_view`) both name a file by `renders.job_name` — a sha256 of the whole
engine spec. Resolution and supersample are fields of that spec, so a view
rendered at another geometry gets its own file and three regimes can share one
directory without colliding.

The **tile** cache says the same thing in a readable name rather than a digest. A
tile is

```text
<out_root>/<location_id>/t<NN>_<palette>_s<scale>_sh<shift>_<level>_q<q><regime>.jpg
```

where `<regime>` is `_<w>x<h>ss<n>` — the tile size and the field supersample, the
two parts of the recipe a build chooses and every tile in it shares. The
**canonical regime elides**: at 640×360 supersample 2 the segment is empty, which
is the same convention `job_name` follows when a spec omits a field at its settled
default. That is what let this land on a corpus that already existed — re-running
the canonical build over the 379,616 cached tiles wrote 0 and skipped 379,616, and
regenerated a byte-identical manifest.

Each regime also gets its own `manifest<regime>.jsonl`, `build<regime>.json` and
`build<regime>.log`, because a manifest is rewritten whole by every build and the
join precondition is checked against exactly that file. The plan is *not* per
regime: one population behind every regime is what makes the caches comparable row
by row.

```
fractal-wallpapers tiles build                                # canonical, 640x360 ss2
fractal-wallpapers tiles build --supersample 1                # 640x360 ss1
fractal-wallpapers tiles build --tile 384x216 --supersample 1 # 384x216 ss1
```

Completeness per regime is the join precondition, not the exit code: every stored
row joins, 32 tiles each, no manifest row whose file is absent, nothing stamped
`partial`.

## Training and reading a head across regimes

A training example is a `(location, regime)` pair. `head train` takes a
repeatable `--regime`, and every regime named adds one pass over the whole
population to each epoch:

```
fractal-wallpapers head train --run seed0_all_regimes --seed 0     --regime 640x360ss2 --regime 640x360ss1 --regime 384x216ss1     --selection cutpoint_cross_entropy
```

Three things about that command are the whole design.

**The canonical regime has to be among them, and comes first.** It is what the
selection slice, the deploy view and the unsuffixed score file are read at, so a
list that starts elsewhere would silently move all three.

**A row's tiles at two regimes are one draw.** The slot is drawn per location per
epoch and shared across the regimes, so what the head sees is one picture at
several geometries — the augmentation is drawn per example, because two views
cropped and flipped identically would teach it that the crop is the invariant.
`dataset.join` refuses a regime short of a row rather than intersecting quietly.

**The head is told nothing.** No regime input, no conditioning. One score scale
across regimes is the deliverable, and a head that could see the geometry would
be free to keep a scale per geometry.

`--selection` names the objective the epoch is chosen on, over the training-side
selection slice at the canonical regime. `ap_ge2` is the shipped head's, carried
from the source project; `cutpoint_cross_entropy` is the repository's proper
scoring rule and the one every other head here selects on.

Reading is per regime too — `head score --regime 384x216ss1` writes
`scores_384x216ss1.jsonl` beside the canonical `scores.jsonl`, the same elision
the tile cache uses:

```
fractal-wallpapers head score --run seed0_all_regimes --regime 640x360ss1
fractal-wallpapers regime preregister      # the bar, before the candidate exists
fractal-wallpapers regime accept           # the band, against the bar
fractal-wallpapers regime stage            # the winner, beside the shipped head
```

**A score file's `group` is a fact about the manifest that was current when it
was written.** Group ids are assigned over the whole scored store, so an ingest
renumbers them — 943 of the location head's 1,002 evaluation rows changed group
id between two builds whose clustering was identical at 530 groups. Any read
that resamples clusters has to score every arm against *one* manifest, or its
interval is drawn over a partition nobody holds.

`regime stage` writes `location.candidate.fp16.pt` and a tracked `candidate.json`
and deliberately does **not** touch `weights.json`. `fetch-weights` resolves the
manifest, so a candidate is invisible to every serving path until someone adopts
it — which for the location head means restating the floors its scale is
calibrated against, and is a separate decision.

## Budgeting a tile build

Cost tracks what the pixels do, not how many rows there are, and the rate is a
property of the *population* a build covers rather than of the class label. Two
measurements, both per location, all 32 tiles, one field pass:

| label | s/location — 2026-08-19 top-up, 488 fresh rows, 640×360 ss2 | s/location — whole corpus, 640×360 ss1 |
|---|---|---|
| 1 | 23.4 | 0.72 |
| 2 | 2.2 | 0.42 |
| 3 | 1.8 | 0.31 |
| 4 | 0.6 | 0.27 |

The two columns are not the same measurement scaled. Dropping the supersample from
2 to 1 cuts the field's samples fourfold; the rest of the 33× gap in class 1 is
that the top-up's rows were four deep-plane ingests, where an interior-heavy
location iterates to a very high cap, and the corpus's other 5,000 class-1 rows do
not. **Take a rate from the population you are about to build, not from the last
build's table**, and take it *stratified* with enough rows per class: class 1
carries the long tail, and it is the only class where the sample size shows.

| pilot | projected | actual | error |
|---|---|---|---|
| corpus-wide mean (2026-08-19 top-up) | 558 s | 2,044 s | 3.7× low |
| 3 per class (640×360 ss1, whole corpus) | 3,842 s | 6,304 s | 1.6× low |
| 25 per class (640×360 ss1, whole corpus) | 6,263 s | 6,304 s | 0.7% low |

Nearly all of it is the field at ss2; at ss1 the two halves are comparable — the
whole-corpus build spent 4,153 s in the field against 2,130 s in the tiles,
because the tile side is the same 32 JPEGs however the field was sampled.

Disk, measured over the three built regimes (379,616 tiles each):

| regime | KiB/tile | GiB |
|---|---|---|
| 640×360 ss2 | 68.9 | 24.95 |
| 640×360 ss1 | 74.3 | 26.89 |
| 384×216 ss1 | 30.5 | 11.04 |

Dropping the supersample makes the cache **bigger** at the same output size:
point-sampled tiles carry high-frequency aliasing that JPEG spends bits on. Size
does not track pixel count either — 384×216 is 36% of the pixels but 41% of the
bytes, because a smaller frame is not a smoother one.

Each stage writes a record the next one reads rather than being called from
inside it, so a training run can be re-scored and a score can be re-judged
without any of it happening again.

Everything here needs `pip install -e ".[models]"` — torch and timm are not in
the base install, because rendering fractals, walking the plane, running the
supply engine and collecting labels all work without them.

One exception, and it is the reason the exception is written down: `roster` is
the tuple of head names and nothing else, stdlib-only on purpose, because
`fetch-weights --check` runs on the base install and has to know which heads a
complete release carries. `ship` imports the roster from there. Any other module
here that a base install can import is an accident, not a second exception.
