Judging finished renders: what to colour, how to colour it, what to keep, and
what to make at full size.

This is the last stage. Everything upstream produces *supply* — places a walk
found, judges trained on human verdicts, a palette head that ranks colour choices.
Curation spends it: it turns the union of every walk into a small set of finished
wallpapers and a durable account of why those and not the others.

```
binding    which ledgers this curation reads, declared once and never guessed
durability a file kept on two disks under a tracked manifest, and the run guard
rescore    the accumulated pool, read again through the heads shipped now
floors     every number that removes a picture, in one file
neutral    the one picture a location is EMBEDDED from, and its frozen recipe
embeddings one DINOv2 vector per admitted location, keyed and kept forever
intake     the ranked offer, best first per partition
budget     how many pictures to make, and for which judge
colorize   a candidate set of maps, the head's pick, a render, a verdict
selection  top-N per judge, under the slot and supply caps, the location rule
           — and the bar
gallery    the second phase: one pass over the whole pool for what ships
gallery_store  a pass's attempt rows: under artifacts/, manifest-tracked
release    the selected rows again at full size, workers rendering
pacing     the wall clock: what may still start, and what is killed
records    what the run decided, and out of what population
rejection  taking a released row back afterwards, without losing what the run did
below_bar  the glance sheet of what an acting bar would take back, to rule off
sheet      the same thing laid out for a person to disagree with
checks     the two claims only a re-render can settle
run        the wiring, and nothing else
```

```
fractal-wallpapers curate score --harvest artifacts/harvest_run3   # through the location head
fractal-wallpapers curate sidecar save                             # the supply, made durable
fractal-wallpapers curate embed                                    # a vector per admitted location
fractal-wallpapers curate embeddings save                          # the vectors, made durable
fractal-wallpapers curate neighbours -k 3 --sample 10              # does near mean alike?
fractal-wallpapers curate plan --harvest artifacts/harvest_run3    # making nothing
fractal-wallpapers curate run --run v1 --harvest artifacts/harvest_run3
fractal-wallpapers curate run --run v1 --ledger artifacts/harvest_run3/walk.jsonl \
    --wall-budget 28800                                            # eight hours, or less
fractal-wallpapers curate run --resume v1                          # carry on where it stopped
fractal-wallpapers curate below-bar                    # the read to take BEFORE reject
fractal-wallpapers curate reject --run v1 --rejector matt_review --date 2026-08-17
fractal-wallpapers curate reach --write scratch/unreached_keys.jsonl   # the gap, as a manifest
fractal-wallpapers curate score --ledger <l> --key-file scratch/unreached_keys.jsonl
fractal-wallpapers curate gallery --n 100                              # THE gallery pass
fractal-wallpapers curate gallery --n 100 --reseat 0                    # no re-seat: one draw
fractal-wallpapers curate gallery --n 100 --no-full-size                # seat, do not render
fractal-wallpapers curate gallery --pass gallery2                       # ...then make them
fractal-wallpapers curate gallery-store check --pass gallery1          # is the store whole?
fractal-wallpapers curate gallery --pass gallery1 --migrate            # out of the old layout
```

## A run accumulates; the gallery pass chooses

The two halves used to be one command, and Matt split them on 2026-08-22. The two
phases have names: **the pool phase** is `curate run`, and **the GALLERY PASS** is
`curate gallery` — one global selection over everything the pool holds, re-runnable,
each pass a record, the previous gallery superseded rather than deleted.

**A run is the pool phase.** It reads the offer, colorizes, records every candidate
it made and every verdict on it, and keeps a **diagnostic** release of ten pictures —
enough to see that the path works, that the heads are reading the material and
that the palette pass is not producing one look. It does not try to decide what is
worth shipping: that is a judgement over the whole accumulated pool, and one
night's attempts are a few hundred rows of it.

Three things follow, and all three are in this stage now:

* **A run never refuses a place because an earlier run released it.** `curate run`
  used to build the served index and veto every candidate whose place the
  collection already had — one run's seats deciding the next run's coverage, out
  of the fraction of the pool it happened to hold. One wallpaper per location
  still acts *inside* a run, through the counter both heads share, and
  `served_locations` is now read only by the collection-level passes.
* **Every release row says which collection it is in.** `records.DIAGNOSTIC` for a
  run's own, `records.GALLERY` for what the collection ships. A field and not a
  fourth verdict: the three verdicts answer whether there is a wallpaper at the
  end of the row, and this answers which set it belongs to.
* **Nothing released so far is the collection's.** All 1,050 rows on record are
  `diagnostic`, backfilled in the same commit, because none of them was ever
  chosen against a pool.

## `curate gallery` — the seven steps, and the two knobs that are by eye

One command, and **not a run type**: no ledger binding, no pacing clock, no
harvest state, because a selection over an accumulated pool has none of those.
Each invocation is a **pass** with its own id, its own record in
`data/curation/gallery/`, and its own slice of the pool's decision store.

```
1  slots per partition   release_mix over a POOL-WIDE denominator (24,843 admitted
                         locations, not one binding's offer); release_caps and the
                         guarantee re-derived over it. The thin-supply cap is
                         thousands wide at that denominator and binds nothing —
                         computed and reported anyway, so a pass and a run are
                         comparable.
2  head split            per PARTITION, by --strange-share (0.6). The heads are
                         dealt across a partition's picks by largest deficit, so
                         neither judge gets the whole top of a partition.
3  the distance          artifacts/curation/neutral_embeddings.jsonl, refused
                         unless `curate embeddings check` says it is whole, then
                         CUT to the currently admitted population
4  the locations         quality-weighted farthest point under a HARD RADIUS
5  the attempts          m locations near each chosen point, judged small     <-.
6  the seats             both measured floors ACT; P(>=4), P(>=3) tiebreak    --'
                         5 and 6 are a LOOP: an unfilled slot re-seats, up to
                         --reseat (3) neighbourhoods, and everything either
                         side of them happens once
7  the pictures          2560x1440 ss4 for the winners, and only for them
```

**A slot is not married to one neighbourhood.** When every candidate a slot's
neighbourhood produced lands under its head's floor, the slot **re-seats**: it
takes the next point its partition's draw offers, under the same radius and the
same weighting and with the abandoned point still excluded, its new
neighbourhood is attempted, and the whole seating is taken again. `--reseat`
(default 3) is how many neighbourhoods a slot may stand on, and the slot record
keeps every one of them and what each held. So **`below_bar` means *k
neighbourhoods in a row failed*, not one did.**

That gap was gallery1's whole shortfall. Every one of its eight unfilled slots
was `below_bar`; every one was the LAST slot of its partition — which is the
point of the draw most remote from everything already chosen, and so the one most
likely to sit somewhere its head dislikes on principle — and every one sat in a
partition still holding thousands of admitted locations. What the loop
deliberately does not do is the other recovery: no floor moves and nothing is
seated from under one.

**The pass selects over the CURRENT admitted population.** The embedding store is
append-only and the admitted population is not, so the store is a superset rather
than a picture: 29,051 rows against 29,046 admitted, the five being locations
`curate score` re-read at the node regime and put under the junk floor.
`gallery.admitted_only` cuts the rows before anything looks at them, so a
withdrawn location is invisible to the picker and to the attempt leg at once.

**The draw is `gain = distance x location P(>=4) ** gamma`,** where `distance` is
cosine distance to the *nearest* already-chosen point. The first pick of a
partition is its strongest location, with nothing to be far from. `--radius`
(0.07) is a hard constraint under all of it: nothing that close to a chosen point
may be chosen, whatever its quality. `--quality-weight` is `gamma` and defaults to
**1** — a plain product, so a location half as far and twice as good is worth the
same; `0` is pure farthest point, which spends slots on the most isolated places
in the pool whatever the judge says. Not k-means, which follows density: this
pool's density records where the walk spent its budget, so a neighbourhood
somebody visited a thousand times would take a thousand times the slots.

Both numbers are by eye, and every pass prints the instrument that calibrates
them: a **retro table** of the nearest chosen pairs, per partition and overall,
read off the points the pass *ended* on rather than the ones its first draw handed
out. If two rows of it read as one picture, the radius is too small.

**Four sheets a pass, all in `scratch/<pass>_*.html`,** self-contained and
disposable:

```
<pass>_sheet.html          the gallery: partition then rank, slot-labelled,
                           unfilled slots in place, retro table at the top
<pass>_runners_up.html     per chosen point, what the radius refused, at the
                           NEUTRAL render the distance was measured on
<pass>_below_floor.html    per UNFILLED slot: the best candidate every
                           neighbourhood it tried produced, scored against the
                           floor, plus the partition's best unchosen candidate
                           on the same head POOL-WIDE — the proof of whether the
                           partition held supply the slot never reached
<pass>_closest_pairs.html  the 12 closest chosen pairs across ALL partitions,
                           side by side with their cosine distance. The retro
                           table's eye-check; a filled slot shows its wallpaper
                           and an unfilled one its point's neutral render
```

Under `--no-full-size` the two sheets that show wallpapers show each winner's
candidate render instead, captioned with the resolution it actually is.

**Both measured floors act here, and only one of them acts at a run's release.**
`floors.gallery_floor` is that seam and it is the one place in this project where
a head's cut reads differently at two sites: `ACTING_RELEASE_BARS` still answers
*does this kind gate a run's release* and the smooth answer there is still
no, while the pass reads `MEASURED_RELEASE_FLOORS` on both kinds — strange 0.620,
smooth 0.530, both re-fitted on the one `render` judge on 2026-08-23. The two questions are different. A run's release is ten diagnostic
pictures out of one night, and a bar there decides how much of that night is worth
looking at; the pass decides what the collection ships out of everything, and a
slot it cannot fill above a measured floor **after every re-seat it is allowed**
is a fact about the pool. **Unfilled beats padded**: an empty slot is output with
its binding reason named, because it is the signal for where to label or walk
next.

**The pass has a colorize leg, and every chosen point gets both heads' attempts.**
`--attempts m,smooth,strange` (3,2,6) buys, for each chosen point, the top `m`
locations in its own radius by `P(>=4)`, each under `smooth` attempts on distinct
palette anchors and `strange` attempts on distinct modes — 24 attempts a slot,
about a minute. The attempts are **pool rows**, stamped with the pass id, so the
pool grows by every one of them; the plan is taken over the *union* of every
slot's locations, because two overlapping neighbourhoods asking for one location
would otherwise render the same pictures twice (the mode draw is seeded off the
location and the head). A re-seat **extends** that plan rather than rebuilding it
— an attempt's identity is its position in the plan, which is what the candidate
log resumes on and what the palette anchor is drawn on — so a killed pass resumes
every attempt back onto its own picture. The 31 palette candidates that lost are
deleted after the verdict — the row keeps the whole candidate set by name and the head's score for
each, which is what a later reader needs. `--no-attempts` skips the leg and is a
**dev affordance only**: without it the pass is bound to whatever fraction of the
admitted population some run happened to colour, which today is 475 locations out
of 24,843.

**`--no-full-size` skips step 7 and costs the pass no decision.** Every slot is
seated on the same candidates; what is not spent is 25 s a winner making a
2560x1440 picture of a choice that is perfectly judgeable off the 640x360 render
the head itself read. The seats are recorded **`unrendered`** — took the slot, no
picture, **nothing failed** — which is a fourth release verdict and not `killed`,
because `killed` means the render died and a reader has to be able to take a
verdict at face value. `records.served` still wants a picture, so an unrendered
seat can never become a link to nothing. Re-running the same `--pass` without the
flag renders the winners and lifts the rows to `released`: the attempts are all
still on disk, so the second invocation costs the release leg and nothing else.
Contrast `--no-attempts`, which removes material the pass would have decided over
and so changes every number it reports.

**One wallpaper per location acts inside the pass and the served index is not
read.** A run is excused from the index because it has the wrong population; the
pass has exactly the right one and is excused for a different reason — a pass
chooses the whole gallery at once and **supersedes** the previous one, so a pass
that refused every place the last pass shipped could not re-choose its own
gallery, and one that refused every place a run's diagnostic release sits on would
hand the collection's best locations to the ten pictures a night kept to prove its
path worked.

**The pass's pictures live in the run tree** (`artifacts/curation/runs/<pass>/`),
deliberately: `curation.rescore` finds any pool row's candidate render at
`runs/<run>/pictures/<candidate>.jpg` off the row's own `run` field, and a pass
that stored its pictures elsewhere would be a pass whose rows the next re-score
refuses to read. Both contact sheets are written to `scratch/`, self-contained
with their thumbnails embedded.

## What a pass puts in the history, and what it puts beside it

**Everything a pass tracks scales with `n`; nothing tracked scales with the
attempts.** That is a rule, it is measured on every pass, and
`tests/test_curation_gallery.py` pins it on a synthetic N=500 plan by writing the
same 500 seats under two attempt counts an order of magnitude apart and demanding
the tracked bytes come out the same to within the manifest's own digits.

```
data/curation/gallery/<pass>/pass.json              knobs, the plan, the retro
                                                    table, the seating tally,
                                                    timings
data/curation/gallery/<pass>/<partition>.jsonl      one row per slot: the chosen
                                                    point (key + embedding index),
                                                    its neighbourhood, the fill
                                                    arithmetic, the seat by key,
                                                    the refusal by slug
data/curation/gallery/<pass>/gate.manifest.json     rows, bytes, sha256, population
data/curation/release/<pass>/<partition>.jsonl      the WINNERS, at most n of them
artifacts/curation/gallery/<pass>/gate.jsonl        every attempt, one pool row each
<archive>/curation_backup/gallery/<pass>/gate.jsonl the durable copy
```

`gallery.read_pass` puts the record back together — the summary with its slots
re-attached in slot order — so nothing has to know about the file axis. **The
slots split on partition for the same reason the decision stores do**: a slot row
runs about a kilobyte, N=500 is 1.3 MiB, and the history guard acts per file.
gallery1 at N=50 tracks **337 KB over twenty files, the largest 52 KB**.

**The attempts are the bulk and they are not in the history.** A pass makes
`locations x heads x draws` attempts per slot — 1,120 at n=50, ten times that at
n=500 — and a pool row carrying its whole join runs about 3.8 KB. They get the
`neutral_embeddings` treatment: under the regenerable tree, a copy on the archive
tier, a tracked manifest, and `curate gallery-store {check,save,restore}` over
them. The pass writes the copy and the manifest itself as its last act.

**A pass no longer writes a release row per attempt.** It used to write both a
gate row and a release row for every scored attempt, which is the same row twice
and the second copy in the history. Measured on gallery1's own 1,120 attempts,
the old layout would have tracked **7.84 MB** — 4.06 MB of release rows with the
largest partition file at 0.86 MiB against the 1 MiB guard, 3.59 MB of gate rows,
and a 197 KB single-file pass record — per pass, kept forever. The release store now answers
only the question it exists for, *which candidate took a slot*, and a pass takes
at most `n` of those decisions. What each slot passed over is not lost: it is on
the slot as `eligible` / `below_floor` / `location_served`, in the tracked pass
record, and the rows themselves are in the attempt store. A **run** still writes
its passed-over rows into the tracked store, and that is not an inconsistency —
a run's population is one night that will not exist again, and a pass's is the
accumulated pool, which is still there.

**A later pass reads both stores.** `gallery.pool_candidates` reads the release
store *and* every earlier pass's attempt store, because an earlier pass's
thousand-odd attempts are standing coloured judged candidates and are the largest
single block of material a second pass can seat without rendering anything.

**`curate gallery` refuses the pre-split layout** — a tracked gate directory under
the pass id, or a passed-over release row in the history — before it spends
anything, because a pass run over it would upsert its winners into a directory
still holding every attempt the old code passed over. `curate gallery --pass <id>
--migrate` moves one pass across: attempt rows into the new store with its
manifest, the release directory rewritten to the winners alone. It reads and
writes records only and renders nothing. It is idempotent.

## The gallery pass needs a distance, so every admitted location has a vector

The gallery pass picks by **quality-weighted farthest point with a hard radius**,
which needs to know how far apart two locations look. `curate embed` is what
answers that: for every location the location judge admits over the junk floor
(**24,779** today), one **neutral render** through one fixed cyclic map at one
fixed small geometry, and the unit vector a frozen DINOv2 reads off it.

* **Locations, never candidates.** A candidate is a location already coloured,
  and the gallery pass chooses the colouring afterwards. Palette diversity is the
  neighbourhood draw's job upstream.
* **Frozen choices, and a stamp that makes a thaw visible.** `twilight_shifted`,
  448x252 at one sample per pixel, `smooth`, linear, no mirror; DINOv2 ViT-S/14
  at 384 dimensions, L2-normalized, stored `float16`. `neutral.stamp()` digests
  all of it, the manifest records the digest, every row carries it, and a leg
  that would append a second provenance refuses.
* **Incremental and idempotent.** The keys already stored are subtracted before
  anything is drawn, so a later harvest's admissions are a second run of the same
  command and a killed leg resumes on the rows and pictures it left behind.
* **One writer.** The leg takes `artifacts/curation/embedding.lock` through
  `models.train.claim`. Two of these appending to one JSONL interleave
  half-written rows into it; that is measured, not hypothetical.
* **The vectors are durable, the JPEGs are not.** `curate embeddings
  save|check|restore`, the same three verbs `curate sidecar` has. The pictures
  regenerate from the store's own rows — every row carries its family, viewport
  and maxiter — so they are counted in the manifest and not copied.

**The mode table and the strange share are parameters, not constants.**
`--strange-modes` and `--strange-share` are part of a run's recorded shape, so a
resumed run takes the table it was planned with; the defaults are
`budget.MODES_PER_LOCATION` and `run.STRANGE_SHARE` — **0.6** from 2026-08-22, on
Matt's call, because the strange judge is the one with a seventeen-mode roster and
an acting bar to get past while the smooth judge has one coloring and an advisory.
A night's `--finish-by` reservation now asks `curation.budget` what that shape
will actually plan, instead of restating the attempt multiplier, the share and the
mode count in `schedule` — three copies that were correct only while all three of
the originals were fixed.

Everything a run makes at full size is **2560x1440 supersample 4** —
`run.RELEASE_RESOLUTION` and `run.RELEASE_SUPERSAMPLE`, one geometry for every
partition, every mode and every head, so nothing about a release row's cost or
its bytes depends on which slot it took, and `checks` re-derives against those
same two constants.

What follows is worth reading before changing anything.

**A candidate set is a neighbourhood and the pick is made on one field.** The
thirty-two maps are `palettes.space.neighbourhood(anchor, pool, 32)` — the
nearest maps to a drawn anchor in a fixed Oklab metric over the gradient as the
renderer spends it — so the head is asked the fine distinction it was distilled
to make rather than an obvious one, and the set is a pure function of the tracked
library and the anchor. Anchors are drawn **without replacement across a run**,
which is the cheap spread rule: two locations in one release do not come out of
the same region of palette space. Every candidate is a *recolor of one dumped
smooth field* — one iteration pass per location instead of thirty-two, and the
pictures the head reads are the smooth renders it was distilled on. The chosen
map then colours whatever mode the attempt actually draws.

**A run is bound to its ledgers, and nothing defaults to all of them.** `--ledger`
names them; `--harvest` names the run that wrote them and takes its `walk.jsonl`.
`curate run` resolves the binding at its entry, writes it into `run_plan.json`
beside `n` and the seed, and every stage downstream reads it from there — a resume
names no ledger and is bound by its own plan. An invocation that names none with
more than one ledger present **refuses and lists them**. The old default was to
read every `walk.jsonl` under `artifacts/`, which would have ranked one harvest's
17,251 unscored rows into another harvest's intake and printed one funnel over
both populations, with nothing raising and nothing looking wrong.

**The head's rank orders the offer; its level is not a quantity.** An earlier
standing rule said never to order or gate the mandelbrot offer by location-head
rank. `mandelbrot_offer_body` (n=150, five equal-count score bands over the
offer's junk-floor survivors, 2026-08-19) contradicts it on the order: quality
decays monotonically with the head's `P(≥3)` — ρ = 0.582 over the body, 0.410
within bands 1–4 alone, 90% keepers in the top two fifths against 46.7% in the
fourth — so intake's best-first read is right and the rule is retired. What that
batch did *not* rescue is the calibrated level: the head corrected downward on
38.7% of the body and upward on 4.0%, and seven of its 36 tier-4 prefills held.
The score is therefore a rank and never a height, and the only cuts placed on it
are floors.

**That validation measured the retired head's ranks.** It was read through
`4b60deb9…` in 2026-08-19, and the head serving since 2026-08-20 is a different
one that agrees with it at ρ = 0.891 over the standing supply. Reading the offer
best-first is still what this module does; whether the *candidate's* ranks decay
with quality as cleanly is **unmeasured**, and it stays unmeasured until a
decision needs it — a second 150-row body is a labelling batch, not a check.

**Two cuts act here; everything else annotates.** `floors` owns every threshold.
The junk floor removes a row at intake, on the location head's scale, saying no
more than *do not spend colorize compute on this*. The **strange kind's release
bar** removes one at selection: a strange row below 0.620 is not seated, and a
strange slot with nothing above it goes unfilled.

Both are [`Restatement`]s now, and so are the supply engine's two — the good floor
and the great cut, which sit on the same location head and are owned by
`supply.currency`. Those two are **not nested**, because they are cuts on two
different cutpoints of it: the good floor reads `P(≥3)` and the great cut reads
`P(≥4)`, so a frame can clear one and fail the other. `currency.good_class` reads
the floor **first** and answers `None` below it — a frame the run would not keep
has no verdict about how unkeepable it is — and only then asks the great cut
whether the keeper is a 4 or a 3.

A height is declared with the sha of the artifact it was
measured on, the cut is stamped with **that** sha rather than with whatever is
live, and a head flip therefore refuses at the first comparison instead of
quietly deciding on a scale that no longer exists. The junk floor was the last
holdout — described for most of a year as the one cut a flip could leave alone,
because it is coarse and semantic rather than calibrated. It was not: at the
2026-08-20 flip, 0.20 on the new head would have removed 2,086 more locations
from the colorize pool than 0.20 on the old one. Semantic is not scale-free.

Both render judges shipped as advisories — computed, written onto every record,
never allowed to drop a candidate — because neither had a measured release gate
and a bar without one is a number nobody can defend. The strange bar is an
exception taken deliberately, by review rather than by measurement: Matt read
`run2` on 2026-08-17, and all eleven released strange rows below the advisory were
bad, the head had been right about every one, and the release path had been
padding strange slots out of thin passing supply. Its *height* is no longer that
verdict: the 4-class retrain moved the head's whole probability scale, so the bar
was restated off the labels — the crossover where the head's own P(>=3) stops
disagreeing with the people who judged 3,085 pictures — and it landed at 0.685 on
that head's scale rather than at the advisory it was promoted from. The 2026-08-23
flip to one judge moved the scale again and the same crossover now reads **0.620**;
THAT it acts is still the 2026-08-17 verdict. **The smooth kind stays advisory** — its below-advisory rows belong to a mix-ratio decision that has not
been taken. An `Advisory` and a `Bar` are two classes rather than one class with
a flag, so which kind a head has is visible at every call site.

**Nothing is frozen into a row.** Scores are read at the moment they are used, out
of a sidecar this stage owns — upserted per ledger, so scoring one binding
replaces that binding's rows and leaves every other ledger's alone; the walk
ledgers themselves are never rewritten. The *read* back is the other way round —
`ranked` looks the sidecar up **unscoped**, because the binding decides which
places are on offer and a score is a statement about a place, so a location this
binding offers that some other invocation already scored keeps its number instead
of arriving unscored and dying at the floor. A
verdict stamped into a ledger on the day it was minted is a verdict the pipeline
must later either believe or delete, and deleting is how a head flip once took an
intake from about fourteen hundred locations to sixteen. Here a flip is a
re-score, and a stale score costs *rank quality* rather than a row.

**Closing a reach gap costs what the gap is, not what the ledger is.** `curate
reach` names the judged locations the pass cannot select, and it separates two
causes: *below the junk floor* is a judgement, and *absent from the sidecar* is a
place whose ledger was never scored. `curate reach --write <path>` writes the
second set as a **key manifest** — JSONL, one `{schema, key, partition}` a line —
and `curate score --key-file <path>` scores exactly those rows out of the bound
ledgers. Like `--limit`, it is a partial pass: it upserts what it looked at and
clears nothing, because deleting the rows it declined to score would be a partial
pass silently truncating a complete one.

That distinction is worth about an hour, and it used to be worth thirteen. On
2026-08-22 the 68 unreached locations sat on three old ledgers (`harvest`,
`walk_demo`, `walk_j`) holding 22,898 gate survivors between them; the 68
themselves cost one batch and took `curate reach` from 68 absent to **0**.
Scoring those ledgers whole was the separate, larger leg, and it was priced at
thirteen hours only while it was priced at the deploy geometry.

**A row that states no regime is read at the node one.** The head reads three
trained geometries and one scale acts across all of them, but the *picture* is not
one picture: a walk scores its own 384x216 ss1 gate render and stamps the regime
and the recipe's digest onto every row it writes. `curate score` reads a row at
the regime the row states — the walk's own picture where the digest still
describes it, a 384x216 ss1 re-render where it does not. A row that states none
has never been scored here at all, so this stage chooses, and the choice is
`intake.READ_REGIME`: the node regime, like every walk node, **never** the deploy
geometry. The regime is stamped onto the sidecar row as provenance, so an
unstated regime becomes a stated one the moment a score is written off it.

`artifacts/location_views` is therefore **frozen, full stop** — the read-only
record of what was scored at the deploy geometry before a walk scored its own
frames, and not a cache that grows by three gigabytes the first time old stock is
offered. That is a ruling and not an equivalence: it holds *because the location
head is regime-robust* — one scale across all three built regimes, the property
the adopted checkpoint was selected for — which is what makes a node-regime read
of old stock comparable with everything else in the pool.

**What the leg cost, measured.** 2026-08-22, RTX 2060 SUPER, hot tier: 22,630
never-scored rows of those three ledgers in **3,363 s over twelve 2,000-row
chunks**, one chunk a checkpoint, **0.149 s/row realized** against a 200-row
pilot's 0.123 (harvest) / 0.169 (walk_demo) / 0.029 (walk_j). Not the 2.89 s the
deploy geometry cost: these are gate survivors and the cost is what the pixels do,
not how many there are. About **8.1 s of that is fixed per invocation** — imports,
the head onto the GPU, the ledger read, and the sidecar rewritten whole — which is
what sets the chunk size. It wrote **1.48 GB / 22,898 files** into
`artifacts/node_views/384x216ss1/` and nothing anywhere else.

**The release budgets the colorize, never the other way round.** A judge's attempt
budget is a multiple of the slots it is asked to fill, and when the two cannot
both be afforded they scale down together. Volume that falls out of a spread over
render styles gives the one smooth coloring a sixteenth of the attempts however
many smooth slots the release wanted — a release starved by an allocation rule
that had no opinion about the release.

**Attempts and locations stopped being the same count.** `floors.ATTEMPT_MULTIPLIER`
is 4 *locations* a slot: how far into a partition's ranked offer a head reaches.
`budget.MODES_PER_LOCATION` is how many colorize attempts each of those locations
costs — 1 for the smooth judge, whose roster is the one smooth coloring, and **2
for the strange judge**, which draws two different modes per location without
replacement (`colorize.modes_drawn_for`, seeded off the location and the head so
a resume re-derives the pair). run10 seated 15 of 40 strange slots with 115
candidates below the acting bar and seven of nine partitions short, off one
uniformly drawn mode a location. The second draw reaches no further into the
offer, so the release cap's arithmetic is untouched and the location rule sees the
same places; what it buys is a second reading of each, at ~2.4 s. An 80-slot
release is 480 attempts, not 320.

**The funnel is printed with three denominators, not one.** `found` is every gate
survivor the binding holds, `scored` is how many of those the sidecar has an
opinion about, and `passing`/`good` are counted over `scored` and never over
`found`. The junk floor is the only cut intake applies — the survivors above it
are the whole offer, and everything else here annotates. The first production
run printed "22,751 found, 1,245 above the junk floor", which put every gate
survivor in a denominator only the scored prefix could reach, and reported a
fifth of the real rate.

**Nothing is padded, backfilled or redistributed.** A judge that cannot fill its
quota under the caps ships fewer and says so with the three numbers that make the
shortfall attributable. A slot a thin partition could not use is not handed to a
partition that had plenty: that is the thin-supply rule undone one level up. With
the strange bar acting the same rule has an edge — the allocation is still solved
over the partitions that have a *scored* candidate, not over the ones that have a
passing one, so a partition the bar empties holds its slot and leaves it unfilled
rather than exporting it. Every run reports planned against seated against
unfilled, per head and per partition, with the reason each shortfall bound on.

**One wallpaper per location, collection-wide** (Matt, 2026-08-22). A location is
never released twice — not in one run, not across runs, not in two modes or two
palettes. "Same location" is the near-duplicate group `labeling.groups.assign`
already defines, and `floors.CLUSTER_CAP` is now **1** over that grouping with the
whole collection as its scope. `curation.served_locations` reads the tracked
release records into an index of served places at run start;
`selection.grouped` groups the index and *both heads'* candidates in one call,
because a group id is a position in a connected-components labelling and tags
from two calls are unrelated — which is also what makes the cap apply to the
union of the two heads' seats rather than to each of them. A refused candidate is
logged `location_served` with a `cause` of `prior_run` or `this_run`, and the run
summary counts both. **Higher-ranked keeps**: the pool is score-ordered, so the
refused row is always the weaker reading. A resume excludes its own run from the
index or its second half would refuse every seat its first half took.

Read against run9, which had the old rule: 48 seats become **27** — 14 refused as
places an earlier run had served, 7 as a second seat inside run9. Both heads still
attempt every location, so what the second attempt buys is the better reading
rather than a second wallpaper — and the strange judge now makes two of its own
per location for the same reason, which is the one place the attempt plan has been
sized against this rule. `fractal-wallpapers curate repeats` is the report-only read of the rule
against what the collection already holds. Perceptual similarity is a different
question and is not this.

**The rule was applied backwards once, and that is a second way a row leaves
service.** The rule acts at selection and cannot reach backwards, so the
collection it began on was still holding 27 locations twice or more.
`curate retire-repeats` (Matt, 2026-08-22) keeps the highest `P(>=3)` of each
group **within its own kind, uncompared across kinds** — with ties to the later
run, and stamps the other 32 rows
`location_served` with the survivor's key on the row. 185 served became **153**,
zero locations hold more than one, and `tests/test_served_locations.py` pins both.
It is a separate pass from `curate reject` and not a mode of it: that one reads
the bars live and must go on excusing the four ruled run8h rows, while this one
reads no bar at all and can retire a perfectly good picture for being the second
one of a place. One of the four ruled rows was retired by it — the ruling settled
whether failing a bar takes a row out of service, which is not the question the
location rule asks — and a pass names any such row rather than skipping it.

**A release can be wrong, and taking a row back adds to the record.** `rejection`
stamps a released row with who rejected it, when, and against which bar and
artifact; `verdict` stays `released`, the scores are untouched, nothing is
deleted. `records.served` is what every listing, every check and the sheet read, so a row
leaves service everywhere at once — and it is three conditions rather than one:
released, not rejected, **and** with a release picture to serve. The third is not
redundant with the first. A set defined on the verdict alone would be one schema
change away from serving a link to nothing, which is exactly what the
[record store](../../../data/curation/README.md) records happening. The
sheet keeps it on the page under its own heading, because a review page that
disagreed with its own records would be the one thing a review page may not be.
`curate reject` applies today's acting bars to a run released before they acted,
which is a rule rather than a list, and re-running it rewrites the same bytes.

**A ruling that keeps a row in service is a tracked record, or it is not a
ruling.** That rule is live and idempotent, so it finds the same rows every time
it is asked — which is why an *unwritten* exception is dangerous rather than
merely undocumented. Four run8h strange rows sat below the 0.685 bar and stay
served on Matt's reading of the sheet — the exception is keyed on the row, so it
survived the flip that moved the bar to 0.620 and re-scored every score under it; `data/curation/bar_exceptions.jsonl` names
them one by one, with the bar, the score, who ruled and when, and
`rejection.below_acting_bar` passes over exactly those keys. It is per *row*: an
exception naming a run would go on excusing rows that run has not made yet, and
one naming a head would retire the bar by the back door. A pass names what it
excused in its report.

**The read to take before the pass is a page of pictures, not a list of keys.**
`curate below-bar` ([`below_bar`](below_bar.py)) draws every served wallpaper an
acting bar would take back today — one row each, the picture at 560px with the
key, the kind and the current `P(≥3)` against that kind's floor under it, best
score first — into `scratch/below_bar_glance.html`, self-contained and carrying
its own thumbnails. It decides nothing and writes nothing else: whether a picture
is a wallpaper is the one judgement no head here is asked for, and a bar that
moved under a row is a reason to look rather than a verdict.

The population is `rejection.below_acting_bar`'s own, so the sheet and the pass
cannot disagree; the rows a ruling holds in service are on the page under their
own heading and are **not** counted with the rest, because a reviewer shown only
the condemned rows would read the page as the whole below-bar set. A row can be
dropped by key with `--exclude`, which refuses a key that is not below the bar
today — a sheet quietly one row short cannot be checked against the store — and
prints the keys and the `--exclude-reason` on the page, since an exclusion is a
person's call rather than a rule.

**Serving order is score rank within the partition, within a kind.**
`records.score_rank` ranks every `(partition, kind)` pool separately and then
interleaves the pools by *position*, so no sort ever ranks a smooth picture
against a strange one and every prefix of a listing covers the partitions evenly — the
property the near-miss section needs, because it takes a prefix.

**One judge did not make the two kinds comparable, and this is the reason.** Until
2026-08-23 the answer was easy: two heads, two scales, nothing to compare. Now one
judge emits both and the scale is nominally shared — and the pools stay disjoint
anyway, because the two populations have different base rates and different floors.
A strange render at 0.55 is below its acting bar and a smooth one at 0.55 is above
its measured floor; the number is the same and the decision is opposite. Selection
pools stay per kind and floors stay per kind, whatever any bar says. The served set
used to come out in candidate order, which is the attempt number, which is
arrival order: a page led with whichever partition the attempt plan interleaved
first. Floors are untouched by this. The junk floor still acts at intake and an
acting release bar still refuses a seat; rank only orders what survived them.

**Where a run's clock goes.** Profiled serially over a real run: the release pass is
the run, and painting is the release pass. A full-resolution row is ~90% engine, and
inside the engine 97% is painting — resampling is 2.6% and process start, PNG encode
and the write together are 0.3%, so encode and file I/O are not worth counting here.
An attempt is 2.49 s, half of it the thirty-two candidate recolors (36.6 ms each, one
engine process apiece, each re-reading the same 3.7 MB field) — run10 came in at
2.42 over 320 of them. At the shipped shape that used to be roughly 80% release,
17% attempts; the second strange mode a location moves it, and run10's own legs
re-priced come to about 22.8 min of release against 19.4 of attempts.

**A run is sized by a clock as well as by `-n`, and the gate is prospective.** At
six pictures the size of a run is `-n`; at sixty it is the wall clock, because one
release row measured between 14.9 s and 1084.6 s (median 69.1 over 204 tracked
rows) turns "twenty rows" into an
answer between five minutes and six hours. `--wall-budget` is
checked *before* each unit — `elapsed + estimate + margin > budget` and it does not
start — off an estimate formed from this run's own finished units, with a hard kill
deadline covering the first unit of a class, which by construction has no estimate.
Stopping is an outcome: the summary says `budget_stopped`, which is neither
`completed` nor `crashed`, so a short release is attributable to the clock rather
than mistaken for thin supply.

**A deep release is a different cost class, and `--deep` is what says so.** The
hung-unit backstop (`pacing.HUNG_CEILING`) is a fixed ceiling per leg, sized
against the shallow release row distribution (`pacing.RELEASE_DISTRIBUTION`:
14.9-1084.6 s, median 69.1 s over the 204 tracked rows) and raised only by units a
run has *finished* — so a class whose first row dies at the ceiling never teaches the
run that the class is slow. Two 2560x1440 ss4 frames from
[the deep run mode](../deep/README.md) were measured at **531 s and 607 s**, at
widths `8.07e-10` and `7.07e-11` and iteration caps near 46 000. `curate run
--deep` swaps in `deep.run.HUNG_CEILING` (colorize 1200 s, release 2400 s) for
the whole run; the clock records which set each leg was held to, so a summary
says it rather than implying it. It is an *execution* flag, like `--workers`: it
is not part of a run's shape and a resume may carry a different one.

**A production night is three legs, and the wall budget is what the first two
leave.** Harvest, then `curate score` over the harvest it just wrote, then `curate
run` — separate invocations, so a failure in one does not take the finished work of
the ones before it. `--wall-budget` is the curation's alone, not the night's, so it
is computed at launch rather than written down: `total − harvest spent − reserve`,
where the reserve is what the readout and the write-up need after the last picture
lands. The other direction is `harvest --finish-by HH:MM --release-slots N`, which
reserves this leg's release pass out of the night's span and hands the harvest what
is left — see [the supply engine](../supply/README.md) for
every term it subtracts. A night capped at six hours with a three-hour harvest therefore hands the
curation a little under three, and the curation is the leg that will stop early —
`-n` binds it long before the clock does.

**Restore `artifacts/curation` before the night starts.** Both halves of this
stage live in it — `supply_scores.jsonl`, which every intake ranks against, and
`runs/<run>/release/`, where every full-resolution picture is written — so a night
launched with the subtree archived reads its supply and writes its pictures
seek-bound on a USB disk. `fractal-wallpapers storage restore curation` is the
pre-flight, and it is cheap next to what it saves: 895 directories, 28,112 files
and 6.01 GiB, measured at **2.8 min cold** (28–37 MiB/s across the bulk leg, 170
files/s) and 70 s over a warm source. `storage status --no-sizes` says which tier
it is on without walking the archive to answer.

**The supply sidecar is the one input a run cannot recover from, so it is kept
twice and counted before every run.** `artifacts/curation/supply_scores.jsonl` is
the location head's read of the standing supply — 67,586 rows as of 2026-08-22 —
and it is not regenerable from the checkout, because `curate score` rebuilds it
from the walk ledgers and those are under the regenerable tree too.
[`durability`](durability.py) owns what follows from that: a copy on the archive
tier under its own top-level name (`artifacts/curation_backup/`, a *copy* rather
than a `storage archive` move, which is why it cannot share the `curation` name
the tiers arbitrate), a tracked manifest at
`data/curation/supply_scores.manifest.json` carrying rows, bytes, sha256 and the
per-ledger split, and a guard at the top of `curate run` that refuses when the
live file is missing or shorter than the manifest records. The pre-flight is one
line:

```
fractal-wallpapers curate sidecar check      # live file against the manifest
fractal-wallpapers curate sidecar save       # after a harvest: fresh copy + manifest
fractal-wallpapers curate sidecar restore    # bring the copy back, count-verified
```

`save` after every `curate score` and before the release leg. `check` reports
`grown` between a harvest and the next `save`, which is the ordinary state and not
a fault; `short` and `missing` are the two it exists to catch, and they exit
non-zero.

**A run name is claimed once.** A `curate run` whose name already has a
`run_plan.json` refuses: continuing an interrupted run is `--resume`, and it is a
decision rather than a default. A `--resume` that contradicts the stored plan
refuses too, and names both shapes, because a second plan's attempts written into
the first plan's log is not a thing a later reader can unpick.

**An interrupted run is continued, not restarted.** `--resume` skips what the run
already finished, off the run's own candidate log and the pictures on disk. Its
plan comes from the sidecar it wrote at entry rather than from the command line, so
a forgotten flag cannot re-plan a run half of whose attempts are recorded; nothing
half-written is trusted; and the seam is checked arithmetically — `planned =
resumed + made + failed + not-started` on both legs, loudly and non-zero when it
does not balance.

## The colour census

[`colors`](colors.py) is a standing **record-and-rank** over colour: it carries no
cut, gates nothing, and exists to tell four situations apart that look identical
from a distance — a colour that *cannot be expressed*, one that is *never picked*,
one that is *picked but dies at the floor*, and one that was *never labelled*.
They have different fixes, which is the whole reason to separate them. It counts
through [`palettes.codebook`](../palettes/README.md) — 52 swatches in Oklab; the
ratified codebook's word for them is *anchor*, renamed here because `anchor`
already means the map a hard candidate set is built around and appears under that
meaning on the very rows this reads.

```
fractal-wallpapers curate colors                     # all four stages
fractal-wallpapers curate colors --stage library     # one stage
fractal-wallpapers curate colors --sheets            # + the two glance sheets
fractal-wallpapers curate colors --frequency         # + the swatch frequency sheet
```

```
artifacts/curation/colors/census.json          the readout, carrying its own codebook
artifacts/curation/colors/rows.jsonl           one row per map, candidate render, labelled crop
data/curation/colors/census.manifest.json      tracked: rows, bytes, sha256, population
scratch/color_census_by_swatch.html            the pool by dominant swatch, sampled
scratch/color_census_sparse.html               the sparsest cells, drawn whole
scratch/swatch_frequency.csv                   all 52 swatches by dominance, with carriage
scratch/swatch_frequency.html                  the same rows with the colours filled in
```

**The frequency sheet** ([`swatch_frequency`](swatch_frequency.py)) is the census's
four tables collapsed onto one page for somebody about to author a colormap: every
swatch, ordered by how often it is the *dominant* colour of a judged render, beside
its four notations, whether sRGB clipped its chroma, and how many maps carry it at
10% of their ramp — over the whole library and over the pool. It computes no new
number; it joins stage 1 to stage 3 and orders the result, so every cell is
checkable against the readout. `--frequency` reads the **merged** artifact, so it is
correct after a partial run. Two files because a csv cannot fill a cell with a
colour, and a name beside three coordinates does not tell an eye what is missing.

**A partial run merges.** `--stage library` recomputes a quarter of the census and
carries the other three stages whole, rows included, rather than deleting them —
the same reason `intake` upserts one binding's rows instead of rewriting the file.
A carried stage keeps its own `taken_at`, and the manifest reports
`stages_this_run` beside `stages_carried`, because a table dated today over a pool
that has since grown is worse than a visibly stale one.

A **manifest without an archive copy**, unlike the supply sidecar and the embedding
store above. Those cost a GPU leg or a standing supply the checkout cannot rebuild;
this re-runs in about five minutes over inputs that are all tracked or regenerable,
so what the history needs is provenance rather than a second disk.

**Stage 2 answers half of a tail question, and stage 3 answers the other half.** A
swatch the library carries and the pool never shows can fail in two places: the head
never picks a map carrying it, or the head picks one and the geometry never lands the
colour. The picks table settles the first — `offered` against `picked`, with
`expected_if_blind = offered / 32` — and the second is a **join of the two stages' rows
on `run` + `candidate`**, which asks what share the render actually gave a swatch its
chosen map carried at 10%. Both keys are on both row kinds and no re-render is needed.
Two things to know before trusting the join: the two stores overlap on identity, so a
little over a hundred pick rows share a `(run, candidate)` with another row and resolve
to the same render; and a handful of pick rows have no render at all. Neither can invent
a landing, so a *low* landing rate is still a real one.

**Stage 3 restricts rather than pools, and this is the part to keep straight.** A
judge's score is calibrated against its own training prior, so a stored number from
a retired checkpoint is not on the same scale as a committed floor. Everything
score-free — which colours the pool's renders *are* — runs over the whole pool
(4,642 renders). Everything floor-referenced runs only over rows whose
`scores_current` stamp is the very artifact that kind's floor was measured on, and
a row whose stamps disagree is **refused, not counted**.

Since the 2026-08-23 flip re-read the whole pool onto one artifact, that is 1,423
smooth and 3,219 strange — every one of the 4,642 renders, so the two halves now
coincide. **That is the state the restriction was written to dissolve into, not a
sign that it stopped biting**: the next head flip empties this half again until
`curate rescore` has run. The restriction is on the *scale* and never on the store,
so both stores are read; the floor half deduplicates by picture the way the
score-free half does, because 127 pictures are named by a row in each store. Both
halves resolve a row to its picture through the whole pool, so a pass over a pass
reaches the run that really rendered the frame — a single hop lands one row on a
path nobody ever wrote, and that row used to be reported as absent from disk.

The two claims this stage makes that a test cannot settle are settled by commands
against a real plan — `curate parity`, that a concurrently rendered release is
byte-identical to a serial one, and `curate replay`, that every released picture
re-derives from its own record.

## Coverage on pixels

[`palette_coverage`](palette_coverage.py) asks the census's question about
**pixels** instead of about a ramp: per swatch, how many maps can put that swatch
on 5% / 10% / 15% / 20% of an image. The two numbers come apart, and the reason is
mechanical — an escape-time field is not uniform over its own stretch (one panel
cell here puts 67% of its samples in the bottom decile of gradient position, and
another 53% in the top one), and production folds every non-cyclic map, so a
sequential map's far half is only reachable by field values near the middle of the
frame. A map can carry a colour across a quarter of its gradient and put it almost
nowhere.

```
fractal-wallpapers curate coverage                    # panel, probe, read
fractal-wallpapers curate coverage --step panel       # draw and choose the panel only
fractal-wallpapers curate coverage --step probe --workers 6
fractal-wallpapers curate coverage --step read        # tables off rows already written
fractal-wallpapers curate coverage --sheet            # + the contact sheet
fractal-wallpapers curate coverage --by-swatch        # + all 52 by scarcity on pixels
```

```
artifacts/curation/coverage/panel.json            the 16 cells and their field shapes
artifacts/curation/coverage/fields/*.f32          one dumped field per cell, reused by every recolor
artifacts/curation/coverage/rows.jsonl            one row per cell x map x fold
artifacts/curation/coverage/coverage.json         both tables, the false capabilities, the population
scratch/palette_coverage/coverage_tiles.html      the weakest picture each threshold admits
scratch/palette_coverage/coverage_by_swatch.html  all 52, thinnest on pixels first
scratch/palette_coverage/tiles/                   both sheets' tiles, named by what they show
```

**The by-swatch sheet** is the whole read on one page: 52 rows ordered by the 10%
count, scarcest first, each carrying the colour, its four counts against the same
four over the pre-existing library, a picture of what every rung admits, and the
maps reaching 20% with the drop's members marked. It orders on the **pixel** count
and never on the ramp one — they disagree hard enough to invert the order, so a page
about pixel scarcity sorted by ramp share would put its abundant half at the top.
Two things it is careful about: an empty band says *which* of the two things it is
(nothing reaches the rung, or everything that reaches it clears the next one too —
opposite findings that look identical as a blank cell), and the 20% carrier list is
cut at 12 and prints how many it dropped. Both sheets read the probe rows and
re-probe nothing; the tiles are recolored from the kept fields, because the probe
overwrote its pictures on purpose. A tile is named by the (swatch, rung, cell, map)
it shows, so the two sheets share files and the second costs nothing — the full 52
is 208 tiles, about 10 s and 38 MB.

**Two reads, two estimands, never pooled.** *Capability* is a max over the panel —
a map counts for a swatch if **one** cell showed it — and is bounded by the panel,
so a wider panel can only raise a count. *Realized supply* counts distinct maps
that have ever produced a pool render carrying the swatch, off the census's own
survival rows, and re-renders nothing; it is conditioned on what the walk found and
what the palette head picked, so it is a lower bound on capability. The gap between
them is the reading.

**The panel is selected, not drawn.** 56 pool rows over the seven probeable modes
are dumped and measured first, then 16 are chosen: the two hardest end-decile
pile-ups by construction, one cell per mode, then a spread over the `end_mass`
range preferring partitions the panel does not hold. A panel of good-looking
wallpapers would be a panel of well-spread fields and would overstate every count.
Only the **seven `field` modes** can be probed at all — a composite normalizes two
fields against the whole frame, a modulate looks up a different gradient place per
sample, and a direct trap is colour-valued before any gradient is spent, so none
has one scalar field to dump.

**Production settings, and a false capability.** Every palette knob is the identity
(gamma 1.0, cycles 1.0, phase 0.0, reverse off) and `mirror = colormap not in
cyclic`. Production samples none of those knobs, so the max is over the panel
alone. A sequential map is *also* probed with the fold off, which production never
does; a swatch it reaches only that way is reported apart and counted in neither
table. The reverse cannot arise — the engine refuses to fold a cyclic map.

**Runtime.** 16 cells x 901 maps, plus the unfolded arm for the 156 sequential
maps, is 16,912 recolors at about 75 ms each: 21 minutes serial, about 6 with
`--workers 6`. The panel's own dumps are 56 iteration passes, about 40 seconds.
Each recolor is censused and its JPEG overwritten rather than kept — keeping them
would be a gigabyte of pictures answering four hundred bytes each — so the contact
sheet re-makes the sixteen tiles it shows.

## What the finished collection expresses

[`expressed`](expressed.py) asks the same question one step further downstream,
about the pictures that exist rather than the maps that could make them:

```text
COVERAGE(s) = the fraction of finished wallpapers in which at least
              10% of the pixels are assigned to swatch s
```

```
fractal-wallpapers curate expressed                 # census, then read
fractal-wallpapers curate expressed --step census   # read every finished wallpaper only
fractal-wallpapers curate expressed --step read     # tables off a census already taken
```

```
artifacts/curation/expressed/pictures.jsonl   one row per finished wallpaper, four share vectors
artifacts/curation/expressed/expressed.json   the coverage vector, the budget, the agreement table
```

**The budget is the finding, and it is arithmetic.** Summed over a set of
swatches, COVERAGE *is* the mean number of them a picture expresses — the same
double sum read down the columns instead of across the rows. So a uniform floor
`f` over `k` swatches asks the average picture for `f * k` expressed colours, and
the largest `f` that can exist is `mean / k` whatever curation does. Both halves
are reported, all 52 and the 48 non-neutral, each with the whole histogram: the
population is 246 pictures over seven integers and every bar is a sentence about
what a floor would have to be true of.

**Population: the verdict, checked.** Every release row whose verdict is
`released` and whose full-size picture is on disk — the file is tested rather than
trusted, because a coverage vector short a picture is a number nobody can
reproduce. A row [`rejection`](rejection.py) took back afterwards is **kept**:
this is a question about colour, not about seating.

**Read at the shipped render's own resolution.** A share vector is not
scale-free, so the census reads the release PNG at 2560x1440 and the two cheap
instruments are priced against it rather than assumed. The 160x90 decode
[`codebook.of_picture`](../palettes/codebook.py) uses moves a swatch by at most
0.7 of a point over the released population and flips 12 of 12,792 threshold
cells. The **candidate render is a different picture** — half the supersampling
at a sixteenth of the area, levelled off its own histogram — and moves a median
of 2.1 points, up to 64. That is why a recolor pass would screen at candidate
geometry and never measure there.

**Runtime.** 246 pictures, four share vectors each, about 180 s. The recolor pass
the readout *prices* is not run: `recolor_cost` reports the cross product it
would need — 724 carrier maps over 194 field pictures and 52 that need a whole
re-render per map — so the decision to spend it is taken against a number.
