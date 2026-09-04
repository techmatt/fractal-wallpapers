The four judges as code: their architectures, training loops, and inference paths.

One vertical per head, in the order it runs. For the **location** head, which
judges a place before any colour is applied: `tiles` builds the pictures,
`head` and `dataset` say what a training example is, `train` runs the loop,
`scoring` reads a checkpoint over a population, `acceptance` judges the result
against a bar written down beforehand. `location_scoring` is the door beside
`scoring`: the shipped head over a list of places somebody named rather than over
a built corpus, which is what `fractal-wallpapers score-locations` runs.

**A score row has to say what produced it.** `location` names a slot, not a
model: the head in it gets retrained and re-shipped, and the floors that read it
are restated at the flip — `GOOD_FLOOR` and `JUNK_FLOOR` both were, on one day. So
every row `location_scoring` writes carries the sha256 of the shipped artifact it
was read through and the regime it was read at, the same two facts a
`cuts.Restatement` pins. A figure that prints a score against a floor and cannot
name the head it was scored under goes quietly stale.

```
fractal-wallpapers score-locations --manifest rows.jsonl --out scores.jsonl
```

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

**`embedding` is the one model here that is not a judge, and never trains.**
DINOv2 ViT-S/14 through timm, frozen, classifier head removed, read for the one
question *are these two pictures alike*: the gallery pass picks locations by how
far apart they look, and `curation.embeddings` keeps one 384-dimensional unit
vector per admitted location. Nothing here reads a label, nothing is shipped
through `ship`, and there is no bar to pre-register — the vector says nothing
about whether a wallpaper is good. What this repository decides is the picture
handed to it, which is `curation.neutral`'s, and the patch size is why that
picture is 448x252: DINOv2 tiles its input into 14-pixel patches, so the frame
goes in whole rather than through whichever resize the transform happened to
carry.

**And a fifth thing reads a store without being a judge of a picture at all.**
`spiral_probe` fits and reads the location-*attribute* store — `spiral` or
`not_spiral`, named classes rather than a tier — so `curation.spiral_scores` can
give a gallery cap a share to act on. It ships nothing through `ship`, has no
floor, and its `--head` names a store the labeling rig cuts sheets for; see
[the labeling rig](../labeling/README.md#the-third-kind-of-sheet-a-location-attribute).

**The rest of what is here is the machinery around a retrain, and it is named
here because the prose below describes the studies without naming the modules
that ran them.** For the render judge, four modules stand in a chain:
`render_folds` owns the fittable corpus and the lineage deal every held-out read
is drawn on; `render_grade` graded three recipe changes and adopted nothing;
`render_dose` read a label-quantity curve off the same deal; and `render_deploy`
is the one that trains a whole corpus and produces the artifact that ships.
`render_glance` lays one batch's rows under two heads' orderings for an eye.
`render_acceptance` is the bar the joint candidate is read against, and
`release_floor` fits the two per-kind floors that sit on the head it produces.
For the location head, `regime_acceptance` judges a candidate trained across
regimes against its own pre-registered bar, and `regime_flips` is the render leg
that re-reads the pool when one is adopted.

A note for anyone retiring a band: **`render_grade` is doing double duty.**
`render_dose` imports its `STOP_SHARE`, `STOP_SEED`, `EPOCHS`, `PATIENCE`,
`SHIPPED_RULE`, `CHECKPOINTS`, `sides_for`, `rank_key_columns`, `key_readings`
and `key_delta`, so the concluded comparison and the shared fitting machinery are
one file. Deleting the band takes the machinery with it, which is the shape that
made the CV harness's delete cost three live consumers.

**The render cache is a precondition, and it answers off the corpus.** `renders
plan` lays the jobs out and `renders build` makes them, but `renders.missing` —
which is what says whether a trainer may start — is derived from the **store's
own verdicts** rather than from the written plan. Those two answer different
questions: a plan is a record of what a build was asked for, the store grows with
every ingest of a labeling session, and a plan that predates those rows reports a
full cache while the trainer refuses. `renders verify` re-derives a seeded sample
and compares, and `renders ship` will not stage anything until `renders accept`
has written a verdict — a `FAIL` needs `--force` and a sentence about why.

**A JPEG re-encode floor measured through PIL is ~27x too high unless you pass
`subsampling=0`.** The engine writes quality 90 at **4:4:4** chroma
(`JPEG_QUALITY`, `engine/src/resample.rs`); PIL drops to 4:2:0 at that quality
and keeps 4:4:4 only from 95, so a floor taken by re-encoding through PIL is
mostly chroma decimation and not the codec. Measured on gallery material at 640x360
on 2026-09-04: **4.68 mean absolute channel difference against a real 0.169**, and
4.68 sits just under the website's `SEAT_TOLERANCE = 6.0` — which would make any
real difference between two renders read as compression noise. `verify`'s own
`recompression_floor` re-encodes the same way at `JPEG_FLOOR_QUALITY = 75` and
reads **7.36** on that material; there the inflation is *lenient* rather than
wrong, since `closer_than_a_recompression` only gets easier to satisfy against a
generous floor. Anywhere a floor is used to argue that a difference is **not**
real, pass `subsampling=0`.

**Budget a whole cache at about two and a quarter seconds a picture, and build it
with ONE engine.** Measured 2026-08-30 over the 10,552-picture plan both stores
now carry, on adjacent hundred-job slices of the shuffled plan: **2.11 s serially
against 2.65 s at three engines**, so `renders.DEFAULT_WORKERS` is 1 and
`--workers` exists to re-take the measurement rather than to raise it. The engine
iterates one field across every core it can see, so a second process does not
find an idle machine — it finds this one. That is the same direction and about
the same size as `discovery.scoring`'s fan-out and the flip leg's, now measured a
third time. A cache built from nothing is **about five hours** and it is the
dominant cost of any retrain that starts without one.

**`renders decode` is the lever that speeds every arm at once.** The training
loop is data-loading bound — the GPU sits near 10% while a worker decodes a
1280x720 JPEG — and on this machine the decode is **12.3 ms of a 29.6 ms
example**. `renders decode` writes each crop's own pixels beside it once, about
2.7 MB a picture and roughly 3 GB a thousand, and `renders.open_picture` serves
them to the loader. It is **exactly the JPEG's pixels**: no resize, no smaller
intermediate, so a run over the cache and a run over the crops are the same run.
An array at anything smaller would put a second resize in the chain, and then the
recipe a band was fitted at would depend on whether a cache happened to be warm.
A truncated array reads as a miss and the crop is still the authority.

**Every score file holds UNCONDITIONAL `P(≥k)`.** CORN trains cutpoint `k`
conditionally — given the row cleared the cutpoint below — so the answer a floor
is a point on is the *running product* of those sigmoids, which is what
`head.probabilities` returns and what every `p_ge*` column of every `scores.jsonl`
here carries. Reading the raw sigmoids instead cost the location head seven
points of AUC at its release cutpoint, measured, and the product reading is used
on both sides of every comparison in this repository.

**A band has to have trained at the backbone its bar was written about, and that
is checked at both ends.** `render_train.check_declared_backbone` refuses at
*launch*, before a run spends hours: a named run takes its band's declared value
and a `--backbone` contradicting it is refused rather than obeyed.
`render_train.check_written_backbone` refuses at the *read*, and it is what sees
the failure that already happened — `render_acceptance.read` calls it over the
band's runs before it compares anything, because a written band read against a bar
it cannot answer is worse than no read. Two ends are needed because nothing in a
run directory can catch this on its own: `config.json`, both checkpoints' own
configs and `head audit` all agree with each other and with the wrong value, since
the only place that says what the band was *supposed* to be is the declaration.
`render_train.MISLAUNCHED` names the runs that were kept out of every band on
exactly those grounds.

**A bar is appended to, never edited.** `prereg.json` carries an `amendments`
list and `finished_acceptance.amended(bar, arm)` folds it over the arm as
written — the original stays byte-identical and every amendment sits beside it
with the day and the reason, so both what a read *was* held to and what it was
originally going to be held to are recoverable. The **ordering** arm is the one
this must never move, and nothing does. The amendment that exists closed a
different kind of gap: the interface arm asserted the number of cutpoints a
checkpoint emits as a literal, so a head widened to four classes failed it for
being the shape it was authorised to be. `finished_acceptance.cutpoints_of` now
reads it off `finished_train.RECIPES` instead, because those two *are* one
number — a `K`-class CORN head has `K-1` conditional subtasks and writes `K-1`
columns.

## Both picture caches are addressed by their recipe

The **finished-render** cache (`renders`) and the location head's **deploy view**
(`location_view`) both name a file by `renders.job_name` — a sha256 of the whole
engine spec. Resolution and supersample are fields of that spec, so a view
rendered at another geometry gets its own file and three regimes can share one
directory without colliding.

**The spec carries the engine's own mode catalog, so a catalog change renames
every cached view.** `spec_of` builds `coloring` by deep-copying `catalog()[mode]`
— the engine's description of that coloring, as the engine reports it — which is
right, because that object is literally what goes over the wire. What follows is
that a catalog entry *gaining a field* re-digests every row that names its mode
and orphans every picture already on disk, without a pixel having changed. That
is not a bug to design out: a name that ignored part of the spec would be a name
two different pictures could share, which is the failure that costs thirty-two
wrong candidates rather than one stale file.

**The engine fingerprint makes the reverse case visible, and only after the
fact.** The digest says what the engine was *told*; it cannot say which build
carried it out, so a rebuilt engine draws different pixels under an unchanged
name. `engine_fingerprint` names the build by what it draws, and each view
directory carries a `drawn_by.jsonl` — `{schema, view, engine}` a row, appended,
last row winning — so a picture whose build nobody recorded reads as `unknown`
and is re-rendered on read. It is evidence *after* the render, never a guard
before it: nothing consults a fingerprint to decide what to draw.

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

The second bar did exactly that and resolved every cell it gated, and **the head
it was reading as the candidate is the head that ships now** — `seed0_all_regimes`,
sha `f8f80511…`, under `weights-v2`, adopted on 2026-08-20. Written the way the
bar was read, incumbent first: on 4,000 stock locations the **retired** head's
(`seed0`, `4b60deb9…`) pooled flip rate is 5.96% at 640×360ss1 and 10.36% at
384×216ss1, and the **shipped** regime-robust head's are 3.06% and 4.56%, with all
six regime × gate cells improved. Per gate at 384×216ss1 the shipped head reads
6.53% at the junk floor, 5.58% at the good floor and 1.58% at the great cut.
**The bias, not the noise, is what moved**: at the retired head's 384×216 junk
floor 548 decisions turn off at the cheaper regime against 30 that turn on, and
the shipped head's are 208 against 53.

Read the two names carefully anywhere this section says *shipped* or *candidate*:
`flip_acceptance.json` was written before the flip and calls `seed0` the
incumbent, and the paragraphs below about what adoption costs are about the
decision as it stood then. The manifest is the only thing that answers *what
ships* — `models/weights.json` and `models/location/adoption.json`.

**A retrained location head is not a drop-in.** Canonical-regime pass rates on
that same draw: junk floor 57.85% → 48.62%, good floor 36.75% → 32.80%, great cut
9.80% → 5.55% — and across the candidate band the junk floor ranges 44.07% to
63.50%. Every floor is calibrated against the shipped head's scale, so adoption
means restating them from a measurement, never from one seed's number.

## The read a band cannot give: `renders glance`

`glance` ([`render_glance`](render_glance.py)) is the qualitative half, and it
exists because a non-inferiority band answers only whether a retrain **costs**
anything on the blind sheets. It cannot answer what a correction batch was bought
to answer, and on this project's rules it never will: manufactured rows are
anchored, incumbent-screened and train-side forever, so every read of them is a
read of a population enriched twice to produce it, and a rate quoted off one is a
ceiling.

So the read is a person's. It lays one batch's rows out **twice** — once in the
incumbent's order, once in the candidate's — with both scores under each picture,
and names the rows that moved furthest either way. What a reader is looking for is
whether the pictures the batch was cut for came up, and whether anything they would
not have promoted came up with them.

```
fractal-wallpapers renders glance --batch <name> --run <run>
```

Two things it is careful about. It draws
`artifacts/renders/<kind>/crops/<name>.jpg` — the picture both heads were trained
on and read natively — rather than the sheet render a person labelled, because
asking two heads to order rows at a geometry neither was read at adds a difference
that belongs to neither of them. And **it decides nothing and writes nothing into
any record**: one self-contained HTML file into `scratch/`, which is disposable.

## The deal a held-out read is drawn on: `render_folds`

[`render_folds`](render_folds.py) owns the two things `renders grade`, `renders
dose` and `renders deploy` all stand on: the **pool**, every row of both
finished-render stores that may be fitted on paired with the picture it was cast
on; and the **deal**, those rows' lineages dealt into five parts so a model can be
read on rows whose near-duplicate neighbourhood it never saw. The deal is written
to `artifacts/render_folds/assignment.json` so two runs claiming the same holdout
are reading one file rather than each dealing its own.

The cross-validation harness that priced the dose and grade arms was deleted on
2026-09-04 as having no consumer under the "Matt is the instrument" ruling; it is
recoverable from git history if a retrain eval is ever revisited.

## Grading a retrain: `renders grade`

The deleted cross-validation screen read three arms and came back null, and its own
report named why:
the declared slice was **band-restricted on top of a 20% holdout** and came to 43
strange rows, where a 95% interval on an AUC is about ±0.19. The machinery was
sound; the statistic could not resolve. [`render_grade`](render_grade.py) re-runs
the comparison on the same question **unbanded** — `AUC(≥4)` over every strange
holdout row a person scored 3 or 4, which is 209 rows on fold 0 and 1,021 over the
whole store — and fits the release crossovers off the same artifact. **Nothing here
adopts anything** either: no weights ship, `curation.floors.SCORING_HEAD` does not
move, `models/` is not written, and everything lands under `artifacts/render_grade/`.

```
fractal-wallpapers renders grade split  --fold 0                    # what the split holds
fractal-wallpapers renders grade fit    --arm A --fold 0 --seed 0   # one arm, one fold, one seed
fractal-wallpapers renders grade read   --arm A --fold 0 --seed 0   # both rules' held-out reads
fractal-wallpapers renders grade readout --seeds 0,1                # the primary comparison
fractal-wallpapers renders grade crossovers --arm A --rule <rule> --seed 0
fractal-wallpapers renders grade autopsy --candidate B@<rule> --reference A@<rule> --output <path>
```

**The folds are `render_folds`'s, re-used rather than re-dealt.** Same
`artifacts/render_folds/assignment.json`, same lineage grouping over the pooled corpus,
same two exclusions and same non-exclusion. What moves is the **stop slice**:
`render_train`'s own rule draws 10% of the training side's *places*, and a place is
finer than a lineage, so this draws 20% of the training side's **lineage groups**,
seeded per fold. Every arm on a fold therefore stops against one population, and the
comparison is between arms rather than between slices. The slice comes out of the
training side and never out of the holdout — a run that early-stopped on the graded
split would make the graded number optimistic and could not also be the grading
statistic.

**Two stopping rules come off one run, and the second is free.** `render_train.run`
takes a `second_selection` and keeps a checkpoint at each rule's own best epoch:
`best.pt` for the shipped rule (pooled cutpoint cross-entropy) and `best_second.pt`
for stop-slice `AUC(≥4)`. `patience` stops the loop only when **no** rule has
improved for that many epochs — the two peak several epochs apart on this corpus, so
a patience read off the earlier one would truncate the later one's search and the
comparison would be between a rule and a budget.

⚠ **Selecting on stop-slice `AUC(≥4)` is not the deleted screen's
`top_cutpoint_selection`, which failed.** That was a *proper scoring rule* read at one rare cutpoint, and an
under-confident head minimizes it by never committing — it chose epoch 1. An AUC is
rank-only: shrinking every score toward the prior does not reorder them.

**The realized preprocessing, read off the shipped artifact rather than a
declaration:** `geometry: stretch`, `source_dims [1280, 720]`, `target_dims
[384, 224]`. There is **no crop at deploy** — `head.resize` is a whole-frame
anisotropic `image.resize`, so 16:9 arrives as 12:7 and the head has never seen this
material at its own aspect ratio. 384×224 is 9.3% of the source pixels. Arm B doubles
both axes to 768×448, which keeps that convention exactly and changes nothing else.

Measured on this machine, 2026-08-27, one fold of 5,608 training pictures:

| arm | input | per epoch |
|---|---|---|
| A | 384×224 | 70.8 s |
| B | 768×448 | 104.0 s |

**Four times the pixels costs 1.47× the wall, not 4×** — the loop is data-loading
bound (the GPU sits near 10% while a worker decodes a 1280×720 JPEG), which is the
same arithmetic the screen's own table showed for two folds at once. What 2×
linear *does* cost is card memory: arm B holds about **4.8 GB of an 8 GB card**, so
two arm-B runs cannot share it and a concurrent pair has to be one A and one B.

**What the first full run of this found, 2026-08-27.** Arm B — 2× linear — did not
clear the declared bar: seed-averaged `AUC(≥4)` over the 209-row unbanded 3-vs-4
slice is +0.0414 against arm A, 95% [−0.0103, +0.0945]. But the same arm is
**significantly better on the whole strange population's ≥4 boundary**, +0.0393
[+0.0048, +0.0776] over 714 rows — the same effect size, resolved only because that
population is 3.4× larger. **The miss is power, not substance**, and the lesson is
that even unbanded, one fold's 3-vs-4 slice is too small: pooling all five folds puts
1,021 rows behind it. The AUC stopping rule bought +0.0064 on the mean and its
premise did not hold — `AUC(≥4)` peaked at epoch 5–6 in all four runs rather than
11–13. What it did buy is **stability**: epoch 5–6 every run, where the
cross-entropy rule chose 2, 7, 6 and 4.

**What the ckpt-91 band found on the grown stores, 2026-08-30.** Five folds, two
seeds, 20 runs, graded on the refit rank key over 1,421 human 3-or-4 rows pooled
across both kinds. **Nothing cleared the bar and nothing was adopted.** The
declared primary — the aspect arm under the AUC stopping rule against the
incumbent — reads **−0.0035 [−0.0250, +0.0178]**, and every non-inferiority guard
is *not worse*. The decomposition is the interesting part: **aspect alone buys
+0.0116 [−0.0046, +0.0275] and the AUC stopping rule alone buys +0.0105 [−0.0062,
+0.0285], and the two do not compose** — the rule applied on top of the aspect arm
gives back −0.0151 [−0.0312, +0.0004]. One interval anywhere excludes zero in a
good direction: the stopping rule on arm A lifts smooth `AUC(≥4)` by **+0.0090
[+0.0020, +0.0161]**.

⚠ **384x216 confounds aspect with the backbone's pretrained height** and the band
cannot separate them. `mobilenetv4_conv_small.e2400_r224_in1k` is trained at 224,
and the arm corrects the aspect by dropping 8 pixels below it. The clean re-ask is
**400x225** — exactly 16:9, at or above the native height. Until that runs the
+0.0116 is not evidence about aspect.

⚠ **AN INTERIM READ OF THIS BAND REVERSED ITS OWN SIGN.** At three folds and one
seed the aspect contrast read −0.0316 [−0.0572, −0.0055] — CI-excluding, and
*worse*. Completing the band moved it to +0.0116. A partial band is not a small
version of a whole one; nothing here may be read before its last run lands.

⚠ **THE STOPPING RULE'S STABILITY CLAIM HAS INVERTED — do not re-quote the
paragraph above.** On the grown stores the cross-entropy rule chose epochs **4–7**
across the ten arm-A runs and the AUC rule chose **3–16**, one of them taking the
epoch cap. The 2026-08-27 reading was the other way round. The rule's *mean* is
still worth something; its stability is now the other rule's.

**The resolution axis is NOT closed at candidate geometry, and the gain is at
INFERENCE.** The re-entry instrument predicted `input_detail` would lose its edge
at 640x360, where 768x448 exceeds the source and reads an upsample. It does not:
strange `AUC(≥3)` is +0.0272 [+0.0059, +0.0483] at candidate geometry against
+0.0278 [+0.0067, +0.0489] at label geometry, over 1,795 rows. Reading arm B's own
checkpoint at arm A's input size separates why: **B's weights at 384x224 buy
nothing** (strange `AUC(≥3)` +0.0090 [−0.0162, +0.0327]) and cost smooth `AUC(≥4)`
−0.0334 [−0.0651, −0.0039], while **B's weights at 768x448 against the same weights
at 384x224 carry the whole gain** (+0.0407 [+0.0111, +0.0711] smooth `AUC(≥4)`).
**Train big and deploy small is refused by measurement**: adoption means the 4x
forward pass on every scored candidate forever, which makes it a throughput
question against the mining budget rather than a training one.

⚠ **AND THE SHIPPED HEAD GAINS NOTHING AT 768x448 — IT LOSES.** Every reading above
is of arm B, a checkpoint *trained* at 768x448. The shipped `models/render/render.fp16.pt`
was trained at 384x224, and read at 768x448 over the same 1,795 rows it is worse on
all four columns, two of them CI-excluding: smooth `AUC(≥3)` **−0.0197 [−0.0323,
−0.0076]**, strange `AUC(≥3)` **−0.0501 [−0.0761, −0.0270]**, smooth `AUC(≥4)`
−0.0124 [−0.0310, +0.0060], strange `AUC(≥4)` −0.0263 [−0.0574, +0.0026]. Paired
bootstrap over lineage groups, one checkpoint read twice.

**So `input_detail` is a JUDGE ADOPTION and not a config change.** There is no
setting that buys the +0.02 on the head that serves today; taking the gain means
training at 768x448 and shipping those weights, which re-scores every row of the
candidate ledger's score sidecar. The throughput question above is real but it is
the *second* cost, not the only one.

**The `P(≥4)` crossover does not exist, and that is worth not re-deriving.** Over
pooled out-of-fold predictions across all five folds (8,977 rows), the `P(≥3)`
crossover is **0.5693**, 95% over lineages [0.504, 0.642] — which reproduces
`curation.floors.STRANGE_RELEASE_BAR`'s in-sample 0.575 to within 0.006, the first
independent check that height has had. The `P(≥4)` crossover reads 0.9853 with **370
of 1,000 resamples finding no crossing at all**, and under the AUC stopping rule there
is no crossing whatever (902 of 1,000). The precision curve says why: 30.6% at
`P(≥4) ≥ 0.50`, 41.0% at 0.90, 40.0% at 0.99. Against a 6.7% base rate that is a real
6× lift, but **no height on this scale admits a majority-four population at any
volume**. `curation.mine.PRIMED_BAR` at 0.90 admits 39 strange rows of which 16 are
human fours.

**The crossovers are at LABEL geometry and are not seating floors.** They are
`release_floor`'s fit — isotonic, PAVA, ties pooled, the lowest score whose fitted
agreement reaches a half — run over pooled out-of-fold predictions instead of a
shipped artifact's in-sample read, at both `P(≥3)` and `P(≥4)`. The store's rows are
1280×720 renders from this repository's own coloring path; what the supply engine
scores is a different regime and this judge is not regime-robust. Re-scoring at
shipping geometry is a separate act and no bar is set on these numbers.

## Training the head that ships: `renders deploy`

Every band before this one produced fold models and nothing deployable. This is
three runs on the whole corpus under the incumbent recipe, differing only in the
seed, and the best of them is the artifact that ships.

```
fractal-wallpapers renders deploy split --seed 0    # what one seed's holdout holds
fractal-wallpapers renders deploy fit --seed 0      # one seed, ~13 min on this box
fractal-wallpapers renders deploy fit --seed 1
fractal-wallpapers renders deploy fit --seed 2
fractal-wallpapers renders deploy choose            # the three curves, and the winner
```

A driver that loops the seeds must carry an `if __name__ == "__main__":` guard.
The loader workers are **spawned** on Windows and re-import the driver by path, so
a script without one re-runs the whole band inside every worker and the second
copy dies on the first one's `training.lock`.

**The split is a plain random eighty-twenty over lineages, seeded, and the twenty
has one job: to stop the run.** No date carve-out, no comparison side, no holdout
built around the blind sheets. The head this produces is not read against the
incumbent here at all — a forward draw on a live pool is what compares two heads
honestly, and nothing in this module is a level or a comparison.

**The pin is honoured exactly as the trainer already enforces it.**
`render_train.run` refuses to train on a place pinned to a blind sheet and refuses
to early-stop on one, so a lineage carrying a pinned place is held out and the
pinned rows themselves land on the `eval` side the loop never touches — out of the
stopping statistic, and unspent. On the stores of 2026-09-03 that closure is 837
rows of 11,019 with 598 pinned outright, comfortably under the 20% the split
wants, so the draw fills the rest at random: **train 8,815, stopping 1,606, pinned
598**, holdout exactly 20.0% at all three seeds. It read 802 of 10,299 and train
8,239 / stopping 1,462 for the `deploy` band on 2026-08-30 — the pinned 598 is
unchanged across both, which is what a pin is for.

**The epoch is chosen by average precision at `≥3`** over the non-pinned part of
the holdout, ranked by the head's own `P(≥3)`. Not the incumbent's pooled cutpoint
cross-entropy, which is decided by the `≥2` boundary; not AUC, which is the stated
fallback where AP is undefined; and **not precision at a single k**, which is what
the predecessor stopped on and which moved in steps of one row — at k = 100 it
chose epoch 1 over epoch 5 by a single row while every other reading was still
climbing. Every epoch logs AP(≥3), AUC(≥3) and precision at 4 / 10 / 20% whichever
rule is choosing, so the choice is inspectable against the readings it did not
make. Patience 6, cap 20.

**Three seeds are the read on the rule.** The seed moves the split and the
initialization together, the best chosen-epoch AP ships, and the spread of the
three chosen epochs is the only available evidence about whether the rule is
reading signal or noise.

⚠ **The forward-holdout design that ran before this one is retired, not
parameterised.** It held out every post-cut row so the two heads could be compared
on rows neither had seen. The comparison saturated — those rows are 73% `≥3` by
construction, drawn off the incumbent's own top and off calibration bands, so the
incumbent scored a perfect 1.000 in the top decile — and the constraint cost the
candidate exactly the new strange fours the retrain existed for. Its run is still
on disk at `models/render/forward_holdout_seed0/`; no code reads it.

**Nothing here adopts anything by itself.** `renders deploy` writes checkpoints
under `models/render/<run>/` and records under `artifacts/render_deploy/`; staging
and the flip are `ship.stage_candidate` and `ship.promote`, which are separate
acts.

⚠ **A render flip is not free, and `models/adoption.py` does not cover it** — its
`HEAD` is `"location"`. Three ACTING bars stamp the render artifact they were
measured on and refuse on their first call afterwards: `strange_render_release`,
`strange_render_gallery`, `smooth_render_gallery`. Refitting them is
`head floor --head <kind>` against the new artifact, then re-declaring the two
heights with new stamps in `curation.floors` — `STRANGE_RELEASE_BAR` carries the
first two bars and `SMOOTH_RELEASE_FLOOR` the third. Until that is done a flip
stops the curation run's release and gallery paths. **Retire the outgoing bytes
first**: `torch.save` is not byte-reproducible, so a retired artifact's hash is not
recoverable from its checkpoint. The copy kept beside the maker artifacts, under
`retired_weights/render-weights-vN/` with its manifest, is the only thing a later
forward draw can score a live pool through.

## Adopting a head: `regime restate`, then `regime adopt`

Those two steps are the priced flip, and they run in that order once — **between
two refusals**, and the second one had to be found. The obvious refusal is after
the artifact moves: the pool then holds the candidate's own reads and the
fractions being matched against no longer exist. The other is a run taken while
the *code* already carries the new heights and the artifact has not moved, which
is exactly the window the natural order of this work opens — measure, type the
numbers in, flip. A restatement taken there matches the candidate against itself,
reports a tidy volume match, and means nothing, so `restate` reads what the
owning modules declare and refuses when any cut is stamped against something
other than the live head. It is caught in the command rather than in a report,
because every number it would produce looks exactly like a number that was
measured.

`restate`
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

Three seeds over three regimes is **eight and a half hours of GPU** — 30,391 s of
epoch time across the band's three records. Six hours is what the three
`wall_seconds` add up to, and two of those three cover only the epochs since a
relaunch, which is the whole of the next-but-one paragraph. Three things go wrong
at that length, and all three have now gone wrong here, so they are written down
rather than rediscovered.

**One trainer per directory, and the directory says so.** Every trainer takes
`train.claim` — an exclusive `training.lock` beside the checkpoints, released only
after the run is written down. Without it two processes do not collide loudly:
they interleave their logs, take turns overwriting one checkpoint, and leave a
record that belongs to neither. If a launcher can be started twice — a shell
script that survived a kill, a watchdog re-armed by hand — assume it was.

**The arithmetic is a weaker tell than it looks, and here is exactly how weak.**
A log can be *overwritten* by a concurrent writer holding a truncating handle, so
it will happily show one clean run. The arithmetic was supposed to be what cannot
be faked: `wall_seconds` at least the sum of `history[*].seconds`, and far less
than it means a second process. **It does not mean that.** The clock starts after
the resume snapshot loads and `history` is restored *from* that snapshot, so a run
killed at epoch nine and relaunched records forty epochs and a wall that only ever
covered thirty-one — and nothing is wrong with it. Two of this band's three
records read that way, and both are relaunches. What the arithmetic *can* prove is
the case where not even the final epoch fits inside the wall: no resume explains
that. `models.audit.serial_time` is the reading, and every record written since
carries `segments` — one entry per launch, each naming its epochs and its own wall
— which makes the strict check exact instead of a guess. When epoch times jump —
172 s to 293 s here — something else is on the GPU.

**Auditing a run whose provenance is in doubt** does not need the log or the clock
at all. `fractal-wallpapers head audit --run <run>` re-scores the *selection
slice* through `head_best.pt` and compares against what that run's `metrics.json`
says its best epoch scored, writing `audit.json` beside the record — because a
procedure whose only trace is a commit message is one nobody reading the run
directory will find. Agreement to ~1e-8 proves the checkpoint and the record are
the same trajectory, whoever wrote them; a snapshot is read once at startup and
replaced atomically, so two trajectories cannot mix mid-run.

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
stdlib-only on purpose, because `fetch-weights --check` runs on the base install.
It holds the tuple of head names — which heads a complete release carries — and
`manifest_path()`, the tracked `models/weights.json` that lists them. `ship`
imports both from there. Any other module here that a base install can import is
an accident, not a second exception.

`manifest_path` moved here on 2026-09-04 and the move fixed a duplication rather
than only a layering: `ship.manifest_path()` was one derivation of that path and
`cli.weights_commands` carried a second, `Path("models") / "weights.json"` of its
own, precisely because the command that needs it most could not reach `ship`
without pulling torch onto its own stdlib-only path. There is one derivation now,
and `fractal_wallpapers.cuts` — which every module stating a floor reaches — reads
which artifact is shipped through it instead of importing the training stack.

## What a score becomes, and the figure of it

`decisions` is the one place the four outcomes a location head's reading lands in
are spelled: **refused** below the junk floor, **expandable** below the keeper
floor, **find** above it, **exceptional** once `P(≥4)` clears the great cut. It
composes `curation.floors.passes_junk_floor`, `supply.currency.passes_good_floor`
and `supply.currency.good_class` rather than restating any of them, so moving a
height still moves it in one place.

```
fractal-wallpapers figures judges-score-to-decision --coverage
fractal-wallpapers figures judges-score-to-decision --family julia:multibrot3
```

The figure it draws is four frames, one per outcome, from **held-out
human-labeled rows** of one family — the shipped head's own tracked read of the
evaluation side, resolved through `models/weights.json`'s `run`. Each frame is
that location's canonical view, rendered rather than copied out of a tile cache
so a fresh clone can redraw it; the engine's `maxiter` policy reproduces the tile
build's cap exactly, so the picture is the one the head read. Inside an outcome
the pick is the **median by `P(≥3)`**, ties broken by the row key — a typical
member rather than a cherry-picked one, and the same four every run. The sidecar
`frames.jsonl` carries every frame's row key, the person's class and the head's
own probabilities: the human label is shown and never used to choose the frame.

`--coverage` prints how every partition's held-out rows spread across the four
and draws nothing, which is how a family is chosen. `julia:multibrot3` is the
default because it is the only one whose spread is healthy in all four buckets.
