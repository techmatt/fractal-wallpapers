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
each head's pieces are. `adoption` is the step after the last one: replacing a
shipped head moves the scale every cut on it is a point on, so it restates those
cuts against a fixed pool before it moves the artifact.

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

**384x216 ss1 is the node regime**, and it is not a study any more: it is the
frame a walk's `expand` draws every gate survivor at, so a steered harvest scores
that picture directly instead of rendering a second one at the deploy geometry.
`tiles.NODE_REGIME` is the name, and `discovery.identity` is what refuses a run
whose settings would make the two different pictures — including a check that the
iteration cap this manifest recorded is still the cap the engine gives that width.
Keep the `384x216ss1` manifest on the hot tier for that reason: it is read, in
prefix, at the start of every scored run.

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

**Two bars, two populations, and `--read` says which one authorized a staging.**
The steps above are read on the evaluation split. The `flip-` steps re-ask the
same question on production stock, at the gates the supply engine acts on:

```
fractal-wallpapers regime flip-preregister            # the second bar
fractal-wallpapers regime flip-score --limit 90       # rehearse the render leg
fractal-wallpapers regime flip-score                  # the whole draw
fractal-wallpapers regime flip-read                   # the band, against it
fractal-wallpapers regime stage --read stock          # if that one passed
```

`flip-score` draws 4,000 sidecar locations, seeded and stratified over partition
× the incumbent's stored canonical score band, excludes every location the label
store holds, renders each at all three regimes and reads all four runs over
every picture. It writes `artifacts/regime_flips/{draw,reads}.jsonl` and nothing
tracked; `flip-read` writes the verdict. Two facts about running it:

* **The canonical leg costs nothing — for the stock that has one.** A drawn
  location scored at the deploy geometry already has its canonical view in
  `artifacts/location_views` from the sidecar's own pass, and the digest that
  names it carries resolution and supersample, so that arm reads production's own
  files. A row a walk scored at the node regime has no deploy-geometry picture at
  all and renders one here; the sidecar says which kind a row is, and the name
  check only applies to the first.
* **`--limit` prices the cheapest stratum, not the draw.** The draw is written
  cell by cell from the smallest cell upward, so a prefix is one stratum of thin,
  high-scoring material. Take a budget on a spread across the whole draw.

Fan-out loses here the same way it loses in `discovery.scoring`, now measured at
a second regime: 60 uncached views at 640×360ss1 render at **2.45/s serially**,
2.27/s at three workers and 2.14/s at six, and the engine-seconds inflate
six-fold under contention while the wall clock gets worse. One worker is the
default and `--workers` is how the measurement gets re-taken.

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

**A consistency measurement needs a population where the score is contested.**
The evaluation split is 63% label-1 and 78% of its rows read below `P(≥3) = 0.05`
at the canonical regime; those rows agree at every geometry because they are zero
everywhere, so an all-family rank correlation over the whole split sits at 0.99
and can barely move. The same statistic on the 500 production rows that motivated
the work — stratified over partition × score band — read 0.963. Neither number is
wrong and they are not comparable: a rho is a property of the population as much
as of the head. Say which rows a cross-regime claim was measured on, and prefer
the ones a floor is actually decided on.

The second bar did exactly that and resolved every cell it gated. On 4,000 stock
locations the shipped head's pooled flip rate is 5.96% at 640×360ss1 and 10.36%
at 384×216ss1; the regime-robust candidate's are 3.06% and 4.56%, and all six
regime × gate cells improved. **The bias, not the noise, is what moved**: at the
incumbent's 384×216 junk floor 548 decisions turn off at the cheaper regime
against 30 that turn on, and the candidate's are 208 against 53.

**A retrained location head is not a drop-in.** Canonical-regime pass rates on
that same draw: junk floor 57.85% → 48.62%, good floor 36.75% → 32.80%, great cut
9.80% → 5.55% — and across the candidate band the junk floor ranges 44.07% to
63.50%. Every floor is calibrated against the shipped head's scale, so adoption
means restating them from a measurement, never from one seed's number.

## Adopting a head: `regime restate`, then `regime adopt`

Those two steps are the priced flip, and they run in that order once. `restate`
measures where each acting cut lands on the candidate's scale by **volume**: the
score that passes the same fraction of one fixed reference pool as the retired
head's cut passed. The pool is the whole curation sidecar — 28,072 locations, read
through the canonical views their own stored scores were taken off — so the
measurement costs the head and not the engine (219 s serially on one GPU; the
renders were already cached). `adopt` promotes the candidate's bytes under the
shipped asset name, checks the hash against the record the bars judged, retires
the candidate file and writes `adoption.json`.

The 2026-08-20 location flip moved all three cuts, and they were **not** the same
kind of number before it. Junk floor 0.20 → 0.100, good floor 0.50 → 0.385, great
cut 0.50 → 0.105.

**A restatement holds volume, not rows.** At the restated heights the pool passes
15,182 / 10,529 / 3,062 against the retired head's 15,161 / 10,508 / 3,034 — the
fractions by construction — but 13.5%, 14.6% and 9.9% of the pool changes side at
the three cuts, and the two heads' rank agreement over the pool is ρ = 0.891 on
`P(≥3)`. The judgement moved; the amount of material did not.

**Two facts about artifacts that a flip is the only place to learn.** A `torch`
archive carries its own file name inside itself, so halving one checkpoint into
`<head>.candidate.fp16.pt` and into `<head>.fp16.pt` gives two different files —
and `torch.save` is not byte-reproducible run to run even into the same name: a
re-cast of the retired head's own checkpoint here hashed `f1bb53c2…` where the
manifest recorded `4b60deb9…`. So `ship.promote` **copies** the judged bytes
rather than re-making them, and a retired artifact's hash is not recoverable from
its checkpoint — what holds those bytes is the release asset published under the
old tag, which is why the old manifest row is left in git history rather than
edited away.

## Running a band that takes hours

Three seeds over three regimes is six hours of GPU. Three things go wrong at that
length, and all three have now gone wrong here, so they are written down rather
than rediscovered.

**One trainer per directory, and the directory says so.** Every trainer takes
`train.claim` — an exclusive `training.lock` beside the checkpoints, released only
after the run is written down. Without it two processes do not collide loudly:
they interleave their logs, take turns overwriting one checkpoint, and leave a
record that belongs to neither. If a launcher can be started twice — a shell
script that survived a kill, a watchdog re-armed by hand — assume it was.

**The tell is in the arithmetic, not in the log.** A log can be *overwritten* by a
concurrent writer holding a truncating handle, so it will happily show one clean
run. What cannot be faked is that `wall_seconds` in `metrics.json` must be at
least the sum of `history[*].seconds`. When it is far less, a second process
wrote that record. When epoch times jump — 172 s to 293 s here — something else
is on the GPU.

**Auditing a run whose provenance is in doubt** does not need the log at all.
Re-score the *selection slice* through `head_best.pt` and compare against what
that run's `metrics.json` says its best epoch scored. Agreement to ~1e-8 proves
the checkpoint and the record are the same trajectory, whoever wrote them; a
snapshot is read once at startup and replaced atomically, so two trajectories
cannot mix mid-run.

**A long run gets killed, so resuming has to work — and it is the one path that
only runs after something already went wrong.** `torch.load(resume,
map_location=<device>)` maps *every* tensor onto the GPU, including the
random-number state, which is a CPU byte tensor and is refused there. The file
loads and the run dies several lines later at `set_rng_state`, which reads as a
corrupt snapshot rather than as a wrong argument. Snapshots load onto the CPU.
`tests/test_training_resume.py` pins it, planted red where there is a device.

**A stalled run looks alive.** On Windows a loader with `num_workers > 0` and
`persistent_workers=False` respawns its workers every epoch — forty times in a
forty-epoch run — and one of those spawns can deadlock: the process stays up, the
GPU falls to a few percent, the workers vanish and the log stops. `nvidia-smi`
plus the log's mtime tells them apart in one look. Do not raise
`persistent_workers`: the workers hold their own copy of the dataset and would
never see `set_epoch`, so every epoch would redraw epoch zero's tiles. Watch the
log instead and relaunch on silence — with a working resume that costs the epoch
in flight. `scratch/regime_band_watchdog.sh` is the shape.

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
