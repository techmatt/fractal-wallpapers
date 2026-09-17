The legs that spend the render pool. Every subcommand here drives the engine, at
three workers below-normal, and writes what it makes into the candidate ledger.
Split out of [`README.md`](README.md), which keeps the architecture, the stores and
the module index; the rates these legs are sized off are in
[`MEASUREMENTS.md`](MEASUREMENTS.md), and what they are aimed at is decided in
[`GALLERY.md`](GALLERY.md).

This file states what each leg does today. The readings that argued it there — what
one sweep measured, what one pass found, what a night's arms bought — are in
[`LEGS_decisions.md`](LEGS_decisions.md), which is where a superseded rule goes and
where a figure keeps the date it was taken on.

## `curate pool-draw` — the one draw that is not aimed at anything

Every other sheet this project cuts is aimed: a band around a bar, a mode nobody
has scored, the top of a ranked queue. Those measure a **correction**, and a rate
read off one is a rate about the slice. A question like *what fraction of the
places a gallery could seat are spirals* cannot be answered from any of them, and
that is what this leg exists for.

The population is stated once and taken whole: every location holding at least
one candidate row that clears its own mode's bar in `headroom.bars`, read fresh.
That is deliberately `headroom`'s set and not a second opinion about supply — a
draw over a population the census does not agree exists is a draw nobody can
quote a rate off. It reads **9,086 locations** out of a pool of 169,160
candidates today (2026-09-03), on 21,544 clearing rows.

**One picture per location, and it is the one the solve would seat.** A location
carries dozens of candidates differing only in how they were coloured, so a
random one would measure the palette draw as much as the place. Each drawn
location is represented by its best-ranked clearing row under `solve.ranking` —
the row a seating pass walking this pool reaches first — so the card carries the
picture this project would actually ship from there, which is the only render a
question about a gallery cap can honestly be asked about. The draw itself is over
**locations**, uniformly and seeded, *after* that choice: drawing over rows would
weight a place by how many recipes happen to sit on it, which is a fact about
where mining legs have been.

It writes a finished-render sheet plan and the record of the draw, and it writes
nothing into any label store. Three things travel on each unit beyond the recipe:

* `leveled` — the `<stem>.leveled/` beside the candidate's own picture where the
  autolevel operator acted. **This is the one that gets forgotten**, and the
  failure is silent: `SHEET_judge_band_300` shipped plans without it, and the
  build did not notice because `cut` skips a unit whose picture already exists.
  What breaks is reproducibility — a rebuild after a sweep serves a different
  picture under the same identity. 105 of the 500 units in `spiral_500` carry
  one.
* `selected_on` — the reading the row was drawn on, at candidate geometry. The
  sheet renders at label geometry and reads a different number there; carrying
  both is what lets a later reader attribute a disagreement to the regime rather
  than to the labeler.
* `suggestion` and `columns`, where a prefill was asked for. `--like <alias>`
  names seats in a tentative gallery whose neutral embeddings seed a centroid,
  and each unit is prefilled by cosine to it, cut at the **median over the
  sheet's own units** — so exactly half the page is prefilled either way and the
  hint carries no claim about the rate it is being used to measure. Under five
  aliases resolving, the sheet ships blind and the record names the ones that
  were lost.

**It holds the pool**, and the one-pool-holding-process rule binds: it streams
the candidate ledger, reads the whole score sidecar, and resolves the rank key
over two more stores. The `spiral_500` draw took about four minutes.

### A `.leveled/` directory is swept only with its own picture, and a prune is still structurally safe

Two questions with opposite answers, which is why *can we delete these* keeps being
asked and keeps being answered wrongly in one direction or the other.

**Neither answer is *nothing can ever take one*, and that reading has been carried
before.** A `.leveled/` sits inside a `pictures/` directory, so
`curate candidate-ledger orphans` reaches it by the name its JPEG would have and
takes the ones no store names — the sweep working rather than a leak. What cannot
be written is the *bounded* sweep below.

**A sweep cannot be bounded, so there is no partial one either.** The reachable set
is not a fixed list: `pool_draw` represents each clearing location by its *current*
best-ranked row, so which candidate is drawable moves with the pool, with the bars
and with the next merge — a sweep would have to name the survivors in advance and
there is no moment at which it can. Nor is there a safe subset to take instead. Of
the 94,485 pool directories walked on 2026-09-06, the provably unreachable part is
1,483 directories and 0.09 GiB — **1.6% of the count and 1.3% of the bytes** — and
those are the ones carrying no ledger row at all, which is already
`curate candidate-ledger orphans`' sweep rather than a new one. There is no version
of this that pays.

**A prune is safe, and for a reason that is not a count.** `prune` builds its doomed
list as the `picture` of each row whose key is *not* in the kept set;
[`candidate_ledger.sweep._delete_colormap`] derives `<parent>/<stem>.leveled` from
that row's own picture; and [`pool_draw.leveled_dir`] derives
`<parent>/<stem>.leveled` from a **surviving** row's own picture. One expression,
three spellings. So a prune could take a live directory only if a dropped row and a
surviving row named the same picture — an identity question rather than a rank or a
policy one, and the answer is no. The measurement, the two stem shapes it holds
under, and the two halves of `tests/test_leveled_identity.py` that fail on different
things are in [`README.md`](README.md)'s *A prune cannot take a surviving row's
colormap, and the reason is structural*.

## `curate hunt` — rendering into a shortage instead of around it

The solve in [`GALLERY.md`](GALLERY.md) turns an impossible gallery into a **work
order**. This is what
spends it. A hunt renders candidates at places and in colours that were chosen on
purpose, writes them into the ledger, and leaves the same solve to be taken again
so the shortage can be measured against what it cost.

```
src/fractal_wallpapers/curation/hunt.py             the legs, the budget, the price
artifacts/curation/hunt/frames.jsonl                the frame index — DURABLE, see below
artifacts/curation/hunt/<name>/rows.jsonl           ledger rows, appended as each lands
artifacts/curation/hunt/<name>/scores.jsonl         sidecar rows, likewise
artifacts/curation/hunt/<name>/pictures/<key>.jpg   the candidate renders, named by recipe
artifacts/curation/hunt/<name>/hunt.json            the record: plan, price, coverage
artifacts/curation/hunt/<name>/contact_sheet.html   what it made, the two legs apart
```

```
fractal-wallpapers curate hunt frames --name any         # index the scan's chosen frames
fractal-wallpapers curate hunt plan   --name h1 --unconditional 600 --conditioned 600     --cell dark_vivid_lime --work-order julia:mandelbrot=19 --work-order mandelbrot=6
fractal-wallpapers curate hunt run    --name h1 --budget 1200 ...   # same flags, renders
fractal-wallpapers curate hunt run    --name h1 --budget 1200 --unconditional 600 --places tonight.jsonl   # only these places
fractal-wallpapers curate hunt merge  --name h1                     # fold into the ledger
fractal-wallpapers curate hunt sheet  --name h1                     # redraw the page
```

**The two legs answer two different questions and are interleaved so a budget
that runs out truncates both.** *Unconditional* buys breadth: locations from the
admitted pool that carry no ledger recipe at all, `--per-location` candidates each,
the palette **stratified across the codebook's 48 cells** rather than picked by
the palette head. *Conditioned* buys one colour: maps drawn from
`data/palettes/carriers.jsonl` for `--cell`, the head never asked, the partitions
spread by `--work-order` — which is the shortage list's own supply table.

**`--per-location` defaults to `hunt.PER_LOCATION = 3`, and it is uniform over the
roster.** Shallow on purpose — the thin axis is places, not depth at a place: the
ledger's median location already carries eight recipes and a gallery seats one of
them, so a fourth candidate at a fresh place beats a ninth at a stocked one. Every
mode in the leg's roster is cycled at the same count, which is what makes a
composite mixed in beside field modes expensive out of proportion to what it
delivers — the same shape *Three workers, cut at the location* below states for
`curate depth`. **"Full-roster" names
the draw's DOMAIN and never the per-place count**: a full-roster leg is one whose
draw may reach any partition on the roster, not one that renders every mode at
every place. `mine.PER_LOCATION` is this constant and not a second opinion about
it — a breadth arm gives one location the same three.

**The palette head is bypassed on both legs, and that is the point.** It is
offered the green carriers as often as anything else and takes them at 0.17x the
base rate; its argmax is what left the ledger carrying red at 986 locations and
lime at 248. A conditioned draw routed through `top_pick` would be offered its
carrier and would decline it, so it would not be conditioned at all.

**The colour is a prior about the map and never a verdict about the picture.** A
carrier is drawn *for* a cell and the candidate's dominance is read off its own
render; the record reports the two apart (`drawn_for` against `cells`, and
`delivery_rate` over them), because the field and the mode carry a real share of
the outcome.

### What bounds the minable population

**The location ledger's ratings, and nothing else.** A location is minable when
the location head's rating clears `floors.JUNK_FLOOR` in the supply sidecar, it is
embedded in the neutral store, and the candidate ledger does not already stand on
it. That is `hunt.drawable`, it is the one population `curate hunt`, `curate mine`
and `curate depth` all take, and the three arguments it used to have are now two.
Counted 2026-09-01: 102,552 sidecar locations, **36,868** over the junk floor and
every one of them embedded, 19,286 already open — **17,620 minable**.

**Two of the three rendering legs take a named-location filter, as of 2026-09-15,
and they narrow opposite populations.** `curate hunt plan|run --places FILE` cuts
both hunt legs to the locations a manifest names, out of the unopened pool above;
`curate depth run --floor-places FILE` cuts the mode-floor draw to named locations
out of the **opened** pool. `curate mine` takes neither. The two flags read the
same JSONL through the same parser — `depth.read_places` — so the pair is the
whole path from a crawl to a seat: `--places` opens the named locations, and
`--floor-places` picks the same names up once they are open. Pointed the wrong way
round each says so rather than drawing nothing quietly: `--floor-places` reports
that none of the named places is opened and drawable, and `--places` refuses with
the three reasons a named place can be missing from a hunt's population.

**A framing is an attribute a location may or may not carry, never an admission
ticket.** `hunt.frame_for` is the whole of the seam: where the pool-wide scan holds
a row, the leg draws the frame that scan chose; where it does not, the leg draws
`hunt.recorded_frame` — the `viewport` and `maxiter` the location's own store row
already carries, stamped `used: original`, `adopted: false`, `from_scan: false`. That
is exactly what `chosen_frame` returns for a scan row that *refused*, so the two
absences make the same picture and only the record tells them apart.

**The scan the index came from is deleted, so the index is now the durable half.**
`artifacts/curation/frame_refit/scan.jsonl` was 97.8 MiB with **no builder anywhere in
this repository** — only the reader `hunt.build_frames`, and the job that produced it
lived outside the tree. It was removed on 2026-09-02 after checking the index carried
all 28,090 of its rows (19,041 adopted) across, zero missing in either direction. So
`curate hunt frames` can no longer run and `frames.jsonl` cannot be rebuilt: back it up
with the other durables rather than treating it as a cache. Nothing about a leg
changes — `frame_for` reads the index, and a location it has no row for draws at the
frame it already carries, which was already the majority case.

**It is registered as a durable, and it is the guarded file whose loss is
silent.** `curate frames save|check|restore`, a copy under
`<archive>/curation_backup/frames.jsonl`, a tracked manifest at
`data/curation/hunt_frames.manifest.json`, and a place in `durables.guarded()`
so `curate run` refuses without it. Recorded 2026-09-02: **28,090 rows,
18,115,525 bytes**, sha `8c5341114dee`, **19,041 of them adopted** — all at margin
2.0, spread over nine partitions and none of them `phoenix:classic`. The manifest
counts the adopted rows separately because they are the whole value of the file:
the other 9,049 carry the framing their location already had, which `frame_for`
would draw anyway. Its `Durable.rebuild_command` is a sentence rather than a
command, because there is no rebuild at any price — the scan is gone and
`curate hunt frames` refuses.

**Until 2026-09-01 the rule was the other one and it was stale by construction.**
`drawable` dropped a location the scan held no row for, with no count and no log
line, so it read as an empty pool rather than as a filter — and the rule it
amounted to was "minable if it was present the last time someone ran a batch job".
Nothing in this repository builds that scan. Dropping the coupling moved the
never-opened population **9,605 → 17,620, +8,015 locations (+83.4%)**:

| unlocked | rows |
|---|--:|
| `harvest_reframe_night` | 2,212 |
| `reframe_g4` | 2,145 |
| `reframe_g2` | 1,351 |
| `reframe_g5` | 1,350 |
| `reframe_g1` | 628 |
| `harvest_run2` / `run3` / `run9` / `mandelbrot_sourcing` | 155 / 80 / 69 / 25 |

So it was never only the reframing channel: **329 of those 8,015 are ordinary
walk locations**, embedded after the scan was taken on 08-26, and the next
channel would have hit it the same way. The unlock is weighted to the partitions the channel
works in — `multibrot5` +2,786, `multibrot4` +1,830, `multibrot3` +764 — which
are the three the old pool was thinnest in. A further **763** locations that *are*
open were invisible to `mine`'s DEEPEN arm and `depth`'s NEAR and FLOOR arms for
the same reason; those three now bound on `world["by_key"]`, which is a row to
render from, and never on the frame index.

**The filter was protecting a policy and not a data dependency.** `recipe_for`
needs `frame["viewport"]` and `frame["maxiter"]` and nothing else, both are on the
embedding row, and drawing at the recorded frame was available the whole time.
Nothing else read the scan's columns: `by_key`, `known`, `taken`, `best`,
`head_scores` and `ledger_scores` are all sidecar and ledger.

**A `centered` location is not incomplete for having no scan row.** Its centre *is*
the location and its scale is the rung its head picked out of `reframing.RUNGS`, so
`hunt.wants_framing` says no for one and `hunt.unframed` — the census a scan would
be pointed at, which is not the population and gates nothing — never holds one. Two
things to know about that census. It reads the flag off the row exactly as
`framing.is_centered` does, and **neither the embedding store nor the supply sidecar
carries the flag today**, so on those two stores it counts every unframed location
alike; the flag lives on the walk ledger row. And `curation.framing`'s own docstring
argues the narrower position — that stage B is refused for a centered row while
stage A, the *scale*, is still an open question, half an octave either side of a
coarse ladder. The discovery-side refine leg still runs stage A for one. Nothing in
curation asks for a framing row at all.

**What is still true about the scan.** `curate hunt frames` derives a thin index
(one row a location, 28,090 rows, about two seconds) off the 98 MB scan record; a
scan row taken at another margin is **refused** rather than reinterpreted, because
the margin belongs to that record and re-deciding it is a read of every rung. Where
the record is missing entirely, `hunt.frames` now logs a line and returns `{}`
instead of refusing — a rebuild still refuses, because that is a caller naming the
scan. Because the frame is part of the recipe, a candidate stays valid if the
margin later moves: what a moved margin invalidates is where to draw next, not
what was drawn. Every leg's record carries `unopened_at_recorded_frame` beside
`unopened_drawable`, so a run says how much of its population drew unrefined.

**Rows land as candidates land**, one appended ledger row and one appended score
row per picture, so a killed hunt is a usable partial. `merge` is separate because
the ledger upserts by rewriting the whole file: forty megabytes a candidate is not
a write. The merge is idempotent, and a later `candidate-ledger backfill` does not
drop hunt rows — it upserts too, and a hunt has no decision store to be rebuilt
from.

**The recipe key is known before the engine runs**, which is what lets a hunt skip
a picture the ledger already holds instead of finding out afterwards. Every member
is a lookup or a default, including the autolevel stamp: `stamp_of` keeps the
operator, the switch and the band's sha256 and drops `acted` on purpose. That
stamp is built through `autolevel.make_stamp` and never spelled out — the band
record calls its digest `_sha256` and the stamp calls it `sha256`, and translating
that by hand is how a hunt comes to name identical pixels differently from the
pass that made them.

**The budget is render seconds, not wall clock, and it is enforced at the
candidate boundary** — nothing is started that cannot finish inside what is left,
priced at the dearest candidate that partition has cost *this run*. Not off
maxiter: `phoenix` cost 1.7x what its cap tier implied and `mandelbrot` 0.6x, and
fixed overhead is about 70% of a cheap location, so no power of the cap fits both
ends. The record's `price` table is the per-partition measurement, and it is what
sizes the next budget.

**A work order is proportional over every prefix.** Spelled as blocks — nineteen
`julia:mandelbrot` turns, then six `mandelbrot` — a ten-place leg would spend all
ten on the first partition and never reach the other eight. Each partition's k-th
turn is placed at `(k + 0.5) / weight` and the turns sorted on that.

**Seeds are digests and never `hash()`.** Python randomizes string hashing per
process, so a draw seeded on `hash()` over a tuple holding a cell name is recorded
as reproducible and is not — and the negative half of its range makes
`numpy.random.default_rng` refuse outright. `hunt.seed_of` is sha256.

## `curate mine` — what a PRIMED location costs, and by which route

A hunt renders into a shortage the solve named. This asks the question one level
up: **what does it cost to manufacture a place good enough to seat, and which
route is cheapest?** It renders through the unchanged loop and puts a stopwatch
on each stage, so the same run answers that and produces a cost profile.

```
src/fractal_wallpapers/curation/mine.py              the arms, the clock, the readout
artifacts/curation/mine/<name>/rows.jsonl            ledger rows, appended as each lands
artifacts/curation/mine/<name>/scores.jsonl          sidecar rows, likewise
artifacts/curation/mine/<name>/profile.jsonl         one row a candidate: the stopwatch
artifacts/curation/mine/<name>/sequence.jsonl        the same row plus the WHOLE autolevel
                                                     stamp, which is what a larger render
                                                     inherits. Since 2026-09-08
artifacts/curation/mine/<name>/pictures/<key>.jpg    the renders, named by recipe
artifacts/curation/mine/<name>/fields/<name>.f32     one dumped field a (location, mode),
                                                     swept to 64 as the run goes
artifacts/curation/mine/<name>/mine.json             the record: plan, price, profile, arms
artifacts/curation/mine/<name>/autopsy.html          primed and rejected, sorted by P(>=4)
artifacts/curation/mine/<name>/bench.json            the loop against its cheaper shapes
```

```
fractal-wallpapers curate mine run   --name m1 --budget 7200      # --rate off the records
fractal-wallpapers curate mine plan  --name m1 --budget 7200      # renders nothing
fractal-wallpapers curate mine bench --name m1     # price the loop's alternatives, and one --rate
fractal-wallpapers curate mine sheet --name m1     # redraw the autopsy page
fractal-wallpapers curate mine package --name m1 --out <dir>   # carry it to another machine
fractal-wallpapers curate mine unpack --from <dir>             # land it there, then `merge`
```

**`bench` ends on one `--rate`**, weighted by the plan `mine run` would draw at the
same `--k` and `--per-location`: each planned candidate priced at its own mode kind
and its own (location, mode) width off the benched blocks — a DEEPEN candidate shares
its dump across `k`, a breadth candidate pays one alone — plus the judge a picture.
The colour read, the row write and the loop's overhead are not in it. The first fresh
box hand-blended 0.5 off the table on 2026-09-16 and its leg ran at 1160 s / 586 =
1.98 s a candidate, so the table alone was misleading by that much.

**A package is the deliverable subset of a leg.** `package` copies `rows.jsonl`,
`scores.jsonl`, `sequence.jsonl`, `merge.json` (where the leg merged at home) and
`pictures/` with every `.leveled` beside them, and writes `package.json`: each file's
size and sha256, the engine build that packed it and the builds the rows name, the
tracked `rows.manifest.json`'s count and sha256 as the ledger it was mined against,
the counts, and the names left behind — `fields/`, a regenerable cache of hundreds of
megabytes a leg, and the run's readouts `mine.json`, `profile.jsonl`, `bench.json`
and `autopsy.html`. `unpack` refuses before writing on a file absent, changed or not
named, on a leg directory that already exists, and on rows whose `picture` names
another leg; it lands through a `.unpacking` sibling renamed into place, renames the
origin's `merge.json` to `merge.origin.json` so this machine's merge writes its own,
and writes `unpacked.json`. `--without-manifest` lands a hand-packed directory
**unverified and says so** — the one use was `m1_freshbox`, 2026-09-16.

**A package leaves out the rows its own prune already took.** A leg that merged at
home and has a row with no picture in `pictures/` lost that row to the origin's prune,
so `package` drops it from `rows.jsonl` and `scores.jsonl` (surviving lines copied
byte for byte) and `package.json`'s `counts` names `rows_packed` and
`rows_displaced_at_origin`. A leg with no `merge.json` packs every row. The case that
made the rule: `m1_freshbox`, hand-packed before it, arrived as 586 rows with 423
pictures; here those 163 had no flatness and so no rank, and the merge's prune took
exactly them again, plus 21 incumbents the other 423 displaced — against 48 on the
mining box, whose pool had not moved since its export.

**PRIMED is derived at read time and stored in no row.** A location is primed
when it holds at least one candidate whose render-judge `P(>=4)` clears the bar.
`mine.primed` takes the bar as an argument and the record reports every arm at
two of them, because a judge retrain moves every probability and a boundary
written beside the candidates would need a migration to follow it.

**Two bars, because the prompt's and the code's disagree.** `solve.Q4_BAR` is
`floors.RELEASE_ADVISORY` at **0.50**, and that is what the seating stage counts
against today. This module reports there and at **0.90**, and the difference is
not cosmetic: it is a factor of four in how many locations the same candidates
prime.

**Three arms, woven rather than concatenated.** Each arm's j-th candidate is
placed at `(j + 0.5) / share` and the whole plan sorted on that, so every prefix
holds the arms in their intended proportion — a mine killed at any point has
spent its budget the way a mine that finished would have. Which is not a nicety:
the flat arm is the ranked arm's only control, and a concatenated plan that ran
out would have bought the treatment and none of the control.

**The plan is 35% longer than the budget prices it at** (`PLAN_HEADROOM`). The
budget is what stops a mine; the plan is only what it stops in the middle of, and
a plan sized exactly to a measured mean stops the mine early whenever the mean
came in high — which it does, because every partition's median is under half its
mean. The surplus is never started and costs nothing.

**The rate is derived from the mine records, since 2026-09-16.** The CLI resolves
it through `mine.measured_rate()` — the cheapest `budget.spent / counts.made` of the
newest forty mine records that made fifty candidates, falling back to
`mine.PILOT_RATE` (0.8) — and prints the figure with its provenance; `--rate` still
overrides and `mine.run` still requires one, for the reason *`--rate` reads itself
off the records* gives below. Until then this paragraph said the CLI read
`depth.measured_rate(width)`, and it read nothing: `mine plan` without `--rate`
raised a `TypeError` in `build_plan`. A rate carried in by
hand from another pass prices another population, which is what the derivation
removes the occasion for.

**The two breadth arms differ in the draw and in nothing else.** Same
`per_location`, same `hunt.modes_for` roster, same `hunt.Stratifier` on the same
seed, matched on partition by construction, and no location in both. The ranked
arm sorts on the location head's `P(>=3)` **within** a partition and never across
one; a location the sidecar cannot score sorts last rather than being dropped, so
both arms draw from the same pool.

**The comparison is stratified and its interval is a cluster bootstrap.** Pooled
is reported and is not the answer: matching is a property of the plan, realised
counts drift, and a pooled rate over drifted counts mixes the arms' difference
with the partitions'. `mine.compare` reports a Mantel-Haenszel weighted mean of
the per-partition differences at weights `n_B * n_C / (n_B + n_C)`, with a
percentile interval resampling **locations** inside partition inside arm — a
location is the unit that was drawn and its candidates are not independent.

**The DEEPEN arm holds the mode and moves the palette alone**, at the mode its
best incumbent was drawn in, and it is offered no map that place already carries
in that mode. It draws from two bands reported apart: `[0.50, 0.90)`, the only
band a palette can *convert*, and `[0.90, ...]`, which can only say what a further
palette is worth where one already cleared. The near band is planned first, so a
truncated arm keeps the deliverable and loses the reference.

**`merge` is separate and idempotent**, for `curate hunt merge`'s reason: the
ledger is rewritten whole on every upsert.

**What one mine measured**, `mine1` on 2026-08-26, before the field was shared:
5,684 candidates in 7,169 s, at **1.26 s a candidate**. Seconds per PRIMED location at
0.90 — deepen a near-band place **38.7 s**, ranked breadth with deepening **114.6 s**,
ranked breadth alone **143.9 s**, flat breadth **593.3 s**. The ranked arm beats the
flat one by a stratified **+1.66 points** at 0.90 (95% CI [+0.21, +3.23]) and renders
1.6x cheaper besides. Its clock was one thing — render, **97.2%** of it — which named
the cost and said nothing about it.

**The profile is eight stages now, and four of them are inside what used to be
`render`.** `Stages` takes them off `colorize.render`'s own meter: `dump` (the
iteration pass a shared field pays once a (location, mode)), `paint` (the colouring),
`measure` (the autolevel operator reading the picture's tone, in Python), `repaint`
(the operator's second colouring). `render` is kept as their sum and is derived, never
measured beside them.

**They are timed on `perf_counter` and not on `monotonic`.** `time.monotonic` is
`GetTickCount64` on Windows: 15.6 ms of resolution, which was invisible against a
1.26 s render and is half a stage now that a recolour is 31 ms.

**A validation mine against `mine1`'s own mix.** The two runs draw different
locations, so `composite`, `direct` and `modulate` — code paths this change does not
touch — are the control that prices the population, and the `field` cells are read
against them.

## `curate depth` — how deep a location goes, and where on the head's rank it stops paying

A mine prices a location at three candidates. This asks what a location is worth
when width is nearly free: **forty candidates at one place**, on the modes a
dumped field can serve, across the whole of the location head's rank range rather
than the top of it.

```
src/fractal_wallpapers/curation/depth.py             the draws, the curves, the route
artifacts/curation/depth/<name>/rows.jsonl           ledger rows, appended as each lands
artifacts/curation/depth/<name>/scores.jsonl         sidecar rows, likewise
artifacts/curation/depth/<name>/sequence.jsonl       one row a candidate, IN THE ORDER MADE
artifacts/curation/depth/<name>/pictures/<key>.jpg   the renders, named by recipe
artifacts/curation/depth/<name>/fields/<name>.f32    one dumped field a (location, mode)
artifacts/curation/depth/<name>/depth.json           the record: plan, price, curves, route
artifacts/curation/depth/<name>/autopsy.html         primed and rejected, sorted by P(>=4)
```

```
fractal-wallpapers curate depth plan  --name d1 --budget 5400   # renders nothing
fractal-wallpapers curate depth run   --name d1 --budget 5400   # --rate off the records
fractal-wallpapers curate depth merge --name d1                             # fold into the ledger
fractal-wallpapers curate depth sheet --name d1                             # redraw the autopsy
```

### `--modes` unsaid is the THREE shareable modes, not the policy's twelve

The help says *every shareable mode `curation.mode_policy` mines*, and both halves
of that bind: the default roster is `mined()` **intersected with** the modes a
dumped field can serve, which is `smooth`, `tia` and `stripe`. A leg meaning the
policy's roster names all twelve on the command line, the way `smoke_mine_20260910`
and `palette_variant_mine_ckpt120` both do.

**Something warns now**, since `score_and_resume_ckpt120`: `depth.resolve_split`
states the resolved roster before a plan is built and says `DEFAULTED to
depth.field_modes(), the shareable modes; mode_policy.mined() holds 12` when the
default was taken. It cost a pilot 229 of 726 rows at the merge to find out the
other way.

### The resolved split and the resolved roster are STATED, and both are merged

Two knobs here fill themselves in, and the defect was that neither said so.
`--shares` is **merged over `depth.SHARES`** rather than replacing it — which is
the better default, since a prompt names what it changes and inherits the rest —
so `{"ranked_bands": 1.0}` runs with the near-band and flat draws on 0.25 each and
spends a third of the leg on arms the caller thought it had turned off. The roster
is the paragraph above.

`depth.resolve_split` is where both are resolved and where both are announced,
before anything is planned:

```
[depth] resolved shares: near_band 0.25 · ranked_bands 1.00 · flat 0.25 · mode_floor 0.00 · conditioned 0.00 (asked ['ranked_bands'], 4 inherited from depth.SHARES)
[depth] ⚠ 2 draw(s) nobody named take a share of this leg: near_band 0.25, flat 0.25 — --shares MERGES over depth.SHARES, so spell the table whole to zero them
[depth] resolved roster: 3 mode(s) — smooth, tia, stripe (DEFAULTED to depth.field_modes(), the shareable modes; mode_policy.mined() holds 12)
```

⚠ **Since breadth was spent the inherited shares land somewhere specific, and it
was the worst place in the pool.** `near_band`, `ranked_bands` and `flat` all draw
off the never-opened and near-band populations, and after `on125_wide1`/`wide2`
took the drawable remainder there were **177** admitted never-opened locations left
(2026-09-15, down from 1,933 that morning), every one of them `phoenix:classic`.

**That stock is now GONE — `con125_phoenix_stripe` opened the last 177 and the
never-opened pool reads zero across all ten partitions.** So the hazard below is
historical for `ranked_bands` and `flat`: with nothing never-opened left they draw
nothing at all, and an inherited share on either is now clock that goes nowhere
rather than clock spent at 56x. `near_band` still draws. ⚠ **That zero did not last**: on
2026-09-16 `degree6_find_and_mine_ckpt128` read **45,844 admitted, never-opened places
over 12 partitions** (`[mine]`'s launch line), so a breadth arm meant for one partition
names `--partition-weights` with **every other partition at 0** — a partition left out
keeps its standing weight. **Read the resolved-shares
line anyway** — the reason it exists is that a prompt naming one arm is not a
prompt running one arm, and that is unchanged.

**On a fresh partition, opening a place is dear and deepening it is cheap, so a night
alternates the two.** `degree6_overnight_ckpt128` (2026-09-17, `multibrot6` +
`julia:multibrot6`) opened places with `ranked_bands` arms at 4.6–9.1 engine s a
candidate. Each candidate pays its own field dump there, even at width 2 over
`threads tia`. It then deepened the best opened places by naming them to the floor
draw: `--shares` `mode_floor` 1.0 spelled whole, `--floor-places FILE` (the top N by
best coarse P(>=4), excluding places already deepened), `--floor-modes threads tia
--floor-width 3`. The first four of those ran at 1.5–2.4 s a candidate, and their coarse clears per
1000 engine s went **60, 43, 25, 32** against the opening arms' **4.6, 9.1, 3.5, 7.6**.
The price rises as the manifest reaches lower-ranked, deeper places: 10.1 s by the last. The
places a manifest names under `Q4_BAR` are admitted by it, so a place opened an
hour earlier is reachable once merged. On the fine head it held too: deepening arms
made **9 of the night's 11 rows over `p_fine` 0.50**, and **6.6 rows over
`solve.DEFAULT_FINE_BAR` per 1000 engine s against the opening arms' 2.1**. `smooth` clears the coarse bar cheaply on d=6
but reads poorly on fine (5 of 62 over `solve.DEFAULT_FINE_BAR` at the mid-run read),
so it was dropped from the deepening roster.

So `--shares '{"mode_floor": 1.0}'` — the spell a recolour prompt naturally writes
— plans 7,080 `ranked_bands` candidates at 177 `phoenix:classic` places and 5,680
more in the near band, which is **13,000 of 35,520 shots on the band this project
decided to write off**: 20.911 engine s a candidate and 390.3 a clear, 56x the
floor draw. The plan's own warning is what catches it, and the fix is the table
spelled whole:

```
--shares '{"near_band": 0.0, "ranked_bands": 0.0, "flat": 0.0, "mode_floor": 1.0, "conditioned": 0.0}'
```

which plans 22,760 over 2,276 places — `PLAN_HEADROOM * workers * budget / rate`
and nothing else. **Read the resolved-shares line before every depth leg**; a
prompt that names one arm is not a prompt that runs one arm.

The warning line fires only where an **inherited non-zero** share stands beside an
asked one, which is exactly the case where clock goes somewhere nobody chose. The
record carries `split` — the resolved table, what was asked, what was inherited,
the roster and whether it was defaulted — so a past leg reads back the same two
facts a live one prints. `shares` and `roster` on the record were always the
resolved tables; what no reader could recover was which entries the caller chose.

**The durable fix is the statement and not a change to the merge.** This is the
same class as a builder that narrows a spec by naming some members and dropping
the rest: what is wrong is the silence, not the default. A misspelt draw is now
refused too — merged over nothing, it would leave the draw it meant to set on its
default and report the misspelling as a share.

### `--phase-draw` — the standing forward draw since 2026-09-13

**One uniform phase per candidate, and a shot is one render.** Matt's call of
2026-09-13, and what it replaced is the best-of-five rotation search
(`curate rotate mine`), not `--vary-palette` below — the three are different
questions and all three still exist. `depth.draw_phases` is the draw and
`mine_night2_ckpt124` is the night it became standing.

**Why a single draw beats a winner-keeps rule.** `mine_night_ckpt124` priced
best-of-five on the composites at full render price: 5x the engine seconds for
**3.12x** the above-bar rate (`p_fine >= 0.50`, 0.83% → 2.60%), with **no
recolour discount** — k=0..k=4 cost 5.316/5.335/5.425/5.355/5.365 s and only
14.3% of candidates came in under 1.5 s. Five candidates spent as five
independent draws return an expected 4.15% against best-of-five's 2.60%, which is
**1.6x more rows per engine second**. And the search is worse than expensive: a
shot merges at most one row, so keeping the argmax of five phases biases the
corpus toward whichever phase flattered a place. A single uniform draw is the
unbiased realisation of the same axis at a fifth of the price.

**Two things it deliberately does NOT do**, both of which `--vary-palette` does
on purpose and for reasons that do not transfer:

* **No mass held at phase 0.** `PALETTE_PHASE_HELD` is 0.3 because the varied leg
  is a matched-pair experiment and needs unvaried rows of its own to read
  against. This is not an experiment, it is how rows are made, and a 30% spike at
  one point of the turn would sit in the corpus at exactly the place the draw
  exists to spread away from.
* **No twin.** A twin doubles a shot to answer *does moving the phase beat
  leaving it alone*, which a production leg is not asking. Dropping it is the
  whole of the saving.

**`cycles` is left alone.** The repeat axis lost its own measurement —
`palette_variant_mine_ckpt120` read repeat 3 at 36.4% of matched pairs won
against repeat 1's 52.6%, monotone in the tile count — so this draw moves one
member and the identity stays the identity on the other.

**The direct traps draw bare**, for `--vary-palette`'s reason below and measured
the same way: `phase` is a byte-for-byte no-op on a mode with no field, so no
phase draw is spent on `direct_trap_screen`, `direct_trap_multiply` or
`direct_trap_lines`.

**Exclusive with `--vary-palette`, refused at the parser.** Both write
`Shot.palette`, so a plan carrying the two is two draws under one name.

### `--vary-palette` — moving the palette block, and nothing else

Off by default. On, every candidate draws a `phase` and a `repeat` alongside its
map — `Palette.phase` and `Palette.cycles`, the engine's own knobs for where the
traversal of the gradient starts and how many times it is traversed. **No map is
derived, written or admitted**: both are in `recipes.KEYED`, so a varied candidate
is a new picture beside the plain one and the library is the library the leg
started with. `depth.PALETTE_REPEATS` and `depth.PALETTE_PHASE_HELD` carry the
draw — repeat 1/2/3 at 0.7/0.2/0.1, phase exactly 0 at 0.3 and otherwise uniform
over the turn — and `Shot.palette` carries the result onto the row as
`palette_drawn`, `{}` for an identity draw.

**An identity draw is `{}` and takes the plain candidate key.** That is the point
of the draw returning overrides rather than a whole pass: the leg's own unvaried
rows key exactly as an unvaried leg's would and are readable against the pool
rather than being a second spelling of it.

**The direct traps are drawn bare and excluded from the varied draw.** A trap has
no field for a traversal to start anywhere in, so the axis is a no-op on those
modes — `engine/src/direct_trap.rs` on purpose, measured by the eye sheet of
2026-09-10 at eleven varied tiles to one sha256. A varied draw there would take a
second recipe key for a byte-identical picture.

**And the exclusion is the whole of what is wasted here: every other mode moves.**
`phase_flatness_ckpt122` rendered all nineteen production modes at three phases over
two places and two maps and found **0 of 180 non-trap cells byte-identical**, the
smallest mean Oklab ΔE 0.056 over 85.6% of the frame, and **no gap** in the ranking
of the fifteen — 1.51x end to end. So there is no accepted mode this draw spends
phase on for nothing, and no case here for narrowing the roster it draws over.
`MEASUREMENTS.md`'s *What `Palette.phase` moves, by mode* is the table, and what
moves the reading is the **map's kind** rather than the mode: a folded map responds
about twice as far as a cyclic one. `curate phase-response` is the leg.

**Every varied shot gets its phase-0 twin**, at the same location, mode and map and
immediately after it in the plan so the pair lands in one location block. *Does
adjusting the phase of a recipe you already have beat leaving it alone* is a
question about a matched pair, and the per-candidate draw cannot answer it — one
shot gets one draw, so the identity rows land at other places and other maps.

**Width against the keep is the thing to get right.** The twin doubles the rows at
a (location, mode) pair, against `RETAIN_PER_PAIR = 5`. Twelve modes cycled at
width 12 is one map a pair and two rows — prune-free. The same width over the
**default three-mode roster** is four maps a pair and eight rows: the
`pvmine_pilot_0911` pilot lost 229 of 726 at the merge, which is that arithmetic
and not a surprise.

### A roster entry is a mode, or a mode with its own settings

**Four of the five `direct_trap_multiply` cells are in the production roster**:
the bare mode plus `@opacity=0.4`, `@opacity=0.6` and `@threshold=0.2`, ruled
2026-09-04 on the rule that **a settings cell leaves only at zero clears**.

⚠ **`@opacity=0.6,threshold=0.2` is RETIRED and the rule did not retire it.**
Matt retired the both-knobs corner **by eye at ckpt 117, 2026-09-08**, reading the
whitewash sitting page — 40 places, five adjacent tiles a row, each cell against
its own row's bare — and that ruling stands and is the live one. It is not a clear
rate being overruled by a second clear rate: the zero-clears rule is a floor on
what the *judge* will admit, and Matt's eye is the instrument above it. So the
retirement leaves the rule untouched and takes one cell out from over it, and the
two 2026-09-04 readings below are the record of a decision that has since been
made a different way rather than an argument still standing. Every leg since has
run with the corner left out, including the 2026-09-12 sweep one heading down.

**The retirement is a ruling about what legs draw and not a code change**, which
is the same thing *Nothing in code ever excluded it* says one heading down about
the reinstatement it superseded: there is no switch to find either way. A roster
is what a leg passes in `--modes` / `--floor-modes`, and a retired cell is a cell
nobody names. So the check is that a leg's own record says which cells it ran, and
it does: `dtm_sweep_ckpt121`'s `plan.floor_modes` lists its five by name and the
corner is not one of them.

**What the retired cell reads, for the record.** Over every candidate-ledger row
carrying both knobs above their catalogued defaults, 1,023 rows at 869 places,
**80 clear the pool bar (7.8%)** and 20 clear the primed bar (2.0%) — the best of
the five at the pool bar. The label sheet reads it worst, mean tier 1.93 against
2.92-2.95, and `data/batch_caveats.md`'s ARGMAX-PER-PLACE entry is why those two
facts do not contradict: the cells there stand on four disjoint, judge-selected
populations, so a cell's human rate cannot be differenced against another's. Read
beside the retirement, the tier column is the reading that turned out to agree
with the eye.

**The head-to-head that caveat says the label sheet cannot give was taken on
2026-09-05.** `night_d` ran all eleven dear-mode entries
through one floor draw at the same 56 places under one seed, so the five cells stand
on **one population** and their rates *can* be differenced. Roughly 212 candidates
each:

| entry | q4 clear rate | engine s a clear |
|---|--:|--:|
| `direct_trap_multiply@opacity=0.6,threshold=0.2` *(retired since)* | **7.5%** | 49.7 |
| `direct_trap_multiply@opacity=0.6` | 6.1% | 56.4 |
| `direct_trap_multiply@opacity=0.4` | 5.2% | 70.4 |
| `direct_trap_multiply` (shipped) | 3.8% | 94.2 |
| `direct_trap_multiply@threshold=0.2` | 3.3% | 109.5 |

**Three of the four settings cells outclear the shipped mode and the both-knobs cell
doubles it**, which is the ledger-wide reading of 2026-09-04 reproduced on a matched
draw rather than on the whole store. None is anywhere near zero clears, so the rule
took none of them out — and three days later the eye took the top row out anyway,
which is what *the rule is a floor and not the decision* means in practice.
`direct_trap_screen` on that same leg is the cheapest mode of the night at
**17.6 engine s a q4 clear** — cheaper than any recolour — and `direct_trap_lines`
the second-worst at 3.3%; the direct traps are not one thing.

#### Sweeping PAST the roster's cells buys nothing, measured 2026-09-12

`dtm_pilot_ckpt121` and `dtm_sweep_ckpt121`, **6,885 candidates, 13,463 engine
seconds**, one axis moved at a time off `mode.rs`'s catalogued `opacity` 0.2 and
`threshold` 0.1, with `@opacity=0.6` carried as the on-population control and the
retired both-knobs corner left out. Floor draw at `--floor-width 1` over places
`--floor-untried direct_trap_multiply` says have never been asked, so the five cells
are one draw at one place and their rates **can** be differenced — 1,375-1,378
candidates each, and the merge kept all 6,885 with **nothing pruned**.

| cell | n | engine s/cand | clear @0.50 | 95% CI | engine s a clear |
|---|--:|--:|--:|---|--:|
| `@threshold=0.3` | 1,377 | 2.408 | 5.74% | [4.63, 7.09] | 41.9 |
| `@opacity=0.6` *(control)* | 1,378 | 1.361 | **5.15%** | [4.10, 6.45] | **26.4** |
| `@opacity=0.8` | 1,378 | 1.331 | 4.21% | [3.27, 5.40] | 31.6 |
| `@threshold=0.45` | 1,375 | 3.371 | 3.64% | [2.77, 4.76] | 92.6 |
| `@opacity=1` | 1,377 | 1.310 | 2.54% | [1.83, 3.51] | 51.6 |

**Nothing new beats the incumbent and the incumbent is the cheapest clear on the
sweep**, so no cell is proposed for the roster. The one cell that outreads it,
`@threshold=0.3` at 5.74% against 5.15%, has an interval that covers the control
comfortably and costs 1.8x as much a candidate — so on engine seconds a clear it is
**37% worse**, and that is the column a supply decision is made on.

**Both knobs are past their useful range at the roster's own values, and they fail
differently.** Opacity falls monotonically above 0.6 and `@opacity=1` halves the
control's rate on disjoint intervals — at full alpha the sample replaces the ground
at the trap's centre and the figure stops reading as ink on a field. Threshold peaks
somewhere at or under 0.3 and 0.45 is well past it, which is the value
`direct_trap_ring` and `direct_trap_lines` both ship and is evidently a *screened*
trap's range rather than a multiplied one's.

⚠ **The threshold axis is the dear one, which is the sizing fact.** A candidate at
`threshold=0.45` costs **2.57x** one at `opacity=1` — a wider trap admits more of
each orbit, so the per-hit compositing in [`direct_trap::trace`] runs more often —
and the cost is paid whether or not the extra ink helps. A sweep that spends equal
*candidates* on the two axes spends 1.9x the *clock* on threshold.

None of these rates is differenceable against `night_d`'s above. That leg drew 56
already-proven places and this one draws places the mode has never been asked at
all; the comparison this table supports is the one **inside** it.

**Nothing in code ever excluded it**, which is worth stating so nobody goes looking
for the switch: a roster is what a leg passes in `--modes` / `--floor-modes`, the
standing rosters ([`depth.dear_modes`], [`depth.centered_modes`]) derive from
`mode_policy`'s **bare mode names**, and no settings cell appears in
[`depth.CENTERED_EXCLUDED`] or anywhere else. The reinstatement is a ruling about
what legs should draw, recorded here and in the caveat, and not a code change.

`--modes` and `--floor-modes` take `direct_trap_multiply@opacity=0.6,threshold=0.2`
as readily as `smooth`. **The mode stays a catalog name and the settings ride
beside it**, which is the whole discipline: `mode_policy.check` refuses unless its
table and the engine's catalog describe the same roster, so inventing a *name* for
a variant fails on the way in, while varying `mode_params` is something
`renders.coloring_of` has always supported and `recipes.KEYED` has always keyed.

So a varied entry is a **new recipe key and a new job name**. Nothing re-keys,
nothing already rendered changes underneath its name, no sidecar score is voided
and no human label is invalidated. Measured on a live row:
`direct_trap_multiply` is key `0362d0cf894fb19e`; at `opacity=0.6` it is
`5b6d50a57287c064`, at `threshold=0.2` it is `b9f922488ff5164f`, and at both it is
`9fbabfc75e894f89`. The settings that are *not* overridden keep the catalogued
value — the `opacity=0.6` variant still carries the shipped `threshold` of 0.1 —
which is the difference between this and editing `engine/src/mode.rs`, where the
same change re-keys every row the ledger holds in that mode and voids every label
cast on one.

Four things follow, and each of them is a place this was got wrong first:

- **The palette draw is per `(mode, settings)`**, through `colorize.spelled`. Four
  variants keyed on the bare mode share one seeded sample — the same map for all
  four at every place — and the leg compares one picture against itself.
- **`mine.taken_maps` is per `(mode, settings)`** for the mirror reason: a variant
  inheriting the shipped mode's spent maps is refused most of the pool at exactly
  the places that have been mined most, which are the places a variant is aimed at.
- **A candidate carrying settings never takes the shared field.**
  `colorize.field_row` pins `mode_params` to `{}`, so a dump is filed under the
  bare mode's name; a varied candidate served out of that cache would be a
  recolour of the shipped mode's field wearing the variant's name. It takes the
  render path, where every direct trap already is.
- **`colorize.spelled` is the bare mode wherever there are no settings**, so every
  seed, every `taken` key and every plan this project has ever taken is unmoved.

**Retention does not know about any of this, and that is a live hazard.**
`retention._pair_of` is `(location, mode)` and `RETAIN_PER_PAIR` is 5, so five
rows at one place — the shipped one and four variants — are one pair, and a prune
keeps five of them by the shipped rank key. That the keep and the variant count
now coincide is luck: a sixth variant is one pair again and the prune drops one
of the six. On `direct_trap_multiply` that
ranking prefers the *whitest*: Spearman(in-mask chroma, `P(>=4)`) is **-0.269**
over its clearing rows. So a prune taken before somebody labels a variant sweep
deletes preferentially the rows the sweep was run to find. A labelled render is
protected, so the window is between the merge and the sitting.

### The floor draw is the one that takes a named population

`--floor-places FILE` is a places **manifest** — a JSONL of `{"schema": 1, "key":
...}` — and it is the only flag *here* that says which places. Every other draw
under `curate depth` picks its own off a rank, a band or a bar. It was the only
one in the project until 2026-09-15; `curate hunt --places` is its mirror over the
unopened pool and reads the same file through `depth.read_places`. It narrows the mode-floor draw alone,
because that draw is already the one over opened, proven locations, and a list of
places somebody read off the ledger is always exactly that. Keys the opened pool
does not hold are counted and named rather than dropped in silence: a leg that
quietly planned fewer places than it was handed would report a rate over a
population nobody chose.

A file and never arguments, on the standing rule — this population is hundreds of
places long and a Windows command line overflows a long way before it does.

⚠ **A leaned manifest is RE-FLATTENED whenever the plan is smaller than it.**
`build_plan` does not take `--floor-places` whole: it narrows `world["best"]` to
the named keys and then passes that through [`proven_places`] →
[`hunt.spread`] at `want[FLOOR] // per_place` places, **with no weights**, and
`spread` is a flat round-robin over partitions. So a manifest that carries the
standing draw-weight table — which is the only place the floor arm can carry it,
since nothing under this draw reads one — keeps its lean only while the plan is
larger than the manifest. Size the two together: a manifest at
`budget * concurrency / (width * price)` against a plan at `PLAN_HEADROOM *
workers * budget / rate` comes out about 1.6x covered, and the budget rather than
the plan is then what stops the leg. `sheet_leg_0905` was inside that by accident
(600 places against a plan of 1,347) and `maps_*_0905` by construction.

**And the flat round-robin under it has a price, measured 2026-09-08.**
`general_breadth_0908`'s floor unit drew with no manifest at all, so `spread` gave the
ten partitions an equal turn — and **`phoenix:classic` took 60.3% of that unit's engine
seconds for 9.3% of its candidates**, at **33.99 s a candidate** against 1.17–3.22 for
every other partition. There is no knob for it: `--partition-weights` bends
[`_cell_turns`] and so the ranked and matched draws, and nothing under this draw reads a
weight, so the only lever is a manifest — which the ⚠ above re-flattens whenever the
plan is larger than it. A floor unit run wide on this machine spends most of its clock
on one plane. Price it per partition before sizing the next one.

**A floor unit's prune-free room is the free slots at its own mode's pairs, and its
width is the one maximising `W · |places with room ≥ W|`** —
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What a floor leg may stand on is a FREE
SLOT, and `smooth` has almost none* has the counts that rule was cut from.

### A floor leg cannot weight its MODES, and the weighting is one unit each

[`plan_floor`] hands every entry of `--floor-modes` the same `--floor-width` at
every place in the manifest, and naming a mode twice does not double it: the draw
is cached per `colorize.spelled` entry and the second turn reads the same sample
back. So "weighted toward `smooth`" is not something one leg can be told. It is
**one unit a mode, and the budgets carry the weighting**.

**That costs no field sharing, which is the part worth knowing.** A field is
dumped once per *(location, mode)* — never once per location — so four modes at
one place and four places at one mode each pay four dumps. Splitting a leg by mode
buys disjoint places at exactly the same price, and disjoint places are breadth.

What it does cost is a setup and a merge each: `maps_*_0905`'s four units paid
about 70 s of pool load apiece outside their budgets.

### NO leg can weight its modes, and a wall-clock split is delivered by unit budgets

The section above is about the floor draw and the limit is the whole module's:
`plan_cycled_modes` cycles a roster **uniformly by count** at every place, and
`--modes` decides eligibility and nothing else. **There is no mode-side share of
the clock anywhere in this tree.** The partition axis has one —
[`draw_weights.SECONDS_SHARE`], declared shares of engine seconds converted to
turns by `w = s·U/p` off a measured price — written precisely because a share of
turns is not a share of seconds. The mode axis never got that machinery, and the
gap is not cosmetic: on the twelve-mode roster a uniform cycle spends per
candidate from 1.48 s (`smooth`) to 10.81 s (`smooth_stripe`), 7.3x.

**So a wall-clock split is spelled as one unit a roster, with `--budget` carrying
it.** `--budget` is WALL seconds, and `smoke_mine_20260910` asked `tia` and
`stripe` for 5% each against 90% for the other ten, ran 90 / 90 / 1620, and
realised **5.14% / 5.22% / 89.64%** of render wall — 4.97% / 5.00% on engine
seconds. Every unit must be **clock-bound** for the shares to be comparable; a
unit that empties its plan hands its remainder to nobody and the split is off by
whatever it left.

⚠ **Run the units BEFORE any merge, on one seed, and the places match for free.**
Breadth opens *never-opened* locations, so with nothing merged between them the
units walk the same ranked order and the small ones' places are a prefix-subset
of the big one's — 35 locations were common to all three that night, and on the
overlap the mode comparison controls the place, which no pooled rate can. Disjoint
rosters mean no unit can prune another's rows.

**Width is set by the prune and not by taste.** [`candidate_ledger.RETAIN_PER_PAIR`]
is 5, and a breadth unit puts `width / |roster|` rows on each (place, mode) pair, so
a ONE-mode unit at the twelve-mode width would land 12 on one pair and lose 7 at the
merge. Width **4** at one mode is prune-free and leaves a free slot for a later band;
the ten-mode unit at width 12 is ~1.2 a pair. All three units merged **1,661 of
1,661, prune-free**.

**Price a mixed roster per mode before sizing one**, because a uniform cycle spends
most of its clock on the composites and takes most of its rows off the two cheapest
modes. **And the ten are not one population**: `threads` and `direct_trap_screen`
clear at ordinary prices and are worth feeding, so a leg meaning *feed the others*
names those rather than the `smooth_*` composites.
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the twelve modes cost and what they
buy, measured 2026-09-10* has the ordering, at about a hundred candidates a mode.

### `--rate` reads itself off the records, since 2026-09-15

It **refused** without a value until then, telling the caller to pass "the seconds
a candidate a short run at this width reported" — a number no command reports
without a depth leg having already run at that width. So the one leg that
structurally could not calibrate from its own first minutes was the leg every
overnight prompt tells its units to calibrate from theirs. `hunt` sizes off counts
and truncates at the budget, which sidesteps the question; `mine` has the same
refusal and the same width-specific rate.

The number was written down the whole time. Every depth record carries
`config.width` and `budget.seconds_per_candidate` — per engine, the denomination
`--rate` is in — so `depth.measured_rate(width)` reads the newest forty records,
keeps those at this width that made at least `RATE_FLOOR_MADE = 50` candidates, and
takes the **cheapest**. The resolved figure and its provenance are printed before
the leg starts, so a plan sized off a leg and one sized off the pilot constant are
never the same-looking claim.

**The cheapest and not the median, because of which way it is safe to be wrong.**
`rate` is in the denominator of `PLAN_HEADROOM * workers * budget / rate` and the
surplus of a plan is never started, so under-estimating costs a tail nobody renders
and over-estimating ends the leg with budget in hand. Rates at one width spread by
an order of magnitude — width 12 reads 0.42 s on `u5_easy_night2` and 5.12 s on
`pvmine_0911` — so a middle would size half the legs short. With `PLAN_HEADROOM` at
1.6 the plan runs out only if tonight is cheaper than **0.6x the cheapest this width
has ever recorded**, and when that happens `counts.stopped_for_budget` is zero and
`budget.share` under one, which is the leg saying so.

`depth.PILOT_RATE = 0.4` is the fallback at a width nothing has run: the cheapest
per-candidate second in the 139 depth records on this machine, rounded down. Passing
`--rate` still overrides, and `depth.run` keeps it required — the resolution is the
CLI's, so `rotation`'s `plan_identity` can never find a default appearing under a
resume. That is `overnight_ckpt121`'s incident, and `MINE_RATE` is why it is written
down twice.

### A candidate's price is `dump/W + rest`, and the width is half of it

The 0.5895 s `sheet_leg_0905` reports is a **width-8** number and does not
transfer. Off that leg's own `sequence.jsonl`, splitting the `dump` stage (paid
once a pair) from everything else (paid once a candidate):

| mode | dump a pair | rest a candidate | at W=8 | at W=3 | at W=1 |
|---|--:|--:|--:|--:|--:|
| `smooth` | 0.44 | 0.466 | 0.521 | 0.613 | 0.906 |
| `tia` | 1.11 | 0.337 | 0.476 | 0.707 | 1.447 |
| `curvature` | 2.00 | 0.373 | 0.623 | 1.039 | 2.373 |
| `stripe` | 2.69 | 0.403 | 0.739 | 1.300 | 3.093 |

`phoenix:classic` is the same arithmetic an order of magnitude up: 16.2 s a dump
against 0.46 a candidate, which is 2.49 s at width 8 and 5.86 at width 1. **A
narrow unit is a dump-dominated unit**, so the cheap-mode ordering inverts with
the width — `stripe` is the dearest of the four at every width and `smooth` the
cheapest, but the gap runs from 1.4x at width 8 to 3.4x at width 1.

### `--near-places` is the same thing for the near band, added 2026-09-04

`--near-places FILE` takes the identical manifest and narrows the **near-band**
draw's population: the places whose best candidate in a roster mode sits between
the two bars. Unsaid, that population is the whole history of this pool — **3,450
places on 2026-09-04** — so a leg meaning *the places this night opened* could not
say it, and three flags away from being able to.

It matters more than the floor draw's version, because the near band is the one
arm whose yield is decided by what is already at the place. A pass over a place
already holding `RETAIN_PER_PAIR` rows in that mode is ranked out as it lands:
`draw_cells_smoke` kept **440 of 4,525 rows, 9.7%**, against a fresh place's
prune-free zero. So the difference between an aimed near band and an unaimed one
is smaller than the difference between a near band over tonight's places and one
over everybody's.

A named place holding no candidate in a mode this run can afford is counted and
named rather than dropped — it means the place was opened only in modes this leg
is not running — and a manifest that leaves none is **refused**, on
`--floor-places`' reason: a leg that quietly planned a near band over a population
nobody chose would report its rate over that one.

### Cut the manifest with `curate depth near-places`, and with nothing else

★ **The manifest and the draw were two rules, they disagreed, and the difference
was silent.** Landed 2026-09-12 as [`depth.near_manifest`], which applies the three
tests [`near_places`] applies — the place holds a candidate in a **roster mode**,
its best one is inside `[Q4_BAR, PRIMED_BAR)` on `P(>=4)`, and it is in the **admitted
embedded population** — and then counts free slots at the pair the draw will
actually render into. One population read, and `--out` writes the file
`--near-places` reads:

```
fractal-wallpapers curate depth near-places --min-slots 1 --out scratch/near_places.jsonl
```

**The third test is the one that had never been asked anywhere, and it is the one
that bit.** `world["by_key"]` is `hunt.scanned()` — the *embedded* locations less
the ones now under the junk floor — while a manifest is cut over the **ledger**,
and the ledger runs ahead of the embedding store. Measured 2026-09-12 over the
live store: **1,636 of 34,010 opened locations (4.9%) have never been embedded**,
and they are not spread evenly. `general_leg_0909`'s three band arms were handed
328, 255 and 236 places and planned **160, 87 and 68**; band 2 lost **168** of its
255 — 66% of that manifest. All three arms then ran out of planned work at 41%,
13% and 33% of their clock while being the cheapest work of the night. The arm's
own log said
`255 of 255 named place(s) hold a candidate in a mode this run can afford`, which
was true and was not the question; `build_plan` now reports every test's toll and
the record carries it as `near_attrition`.

⚠ **Letting the draw stand on them is a DIFFERENT change and has not been made.**
A location with no *framing* row draws at the frame it carries, by design — but a
location with no *embedding* row has never passed admission, and a near band
standing on one would put the mining draw and the seating on two populations. The
open question is the supply one: 1,636 opened locations are outside every draw
that reads `hunt.scanned`.

★ **One set of 168 places cost all three arms, and it is the same 168 each time.**
Measured 2026-09-12: the places band 1's manifest names and the draw will not
stand on are *exactly* the ones band 2's and band 3's name, and 328 − 168 = 160,
255 − 168 = 87, 236 − 168 = 68 — every one of the three shortfalls, to the place.
That follows from what they are: an unadmitted place is never drawn on, so its
room never falls and it is named again by the next cut. **166 of the 168 have no
supply row at all**, 2 are scored under the junk floor, and **none is embedded**.

⚠ **They are not one partition.** An earlier reading recorded band 2's 168 as
*every one a `julia:mandelbrot` location*; that is wrong and the sentence stood in
this file, in `depth.near_admits` and in the `near-places` help until 2026-09-12.
They span **ten** partitions — `multibrot3` **60**, `mandelbrot` 27,
`julia:multibrot3` 20, `julia:mandelbrot` **14 (8.3%)**, `multibrot5` 12,
`julia:multibrot5` 9, `julia:multibrot4` 8, `multibrot4` 8, `phoenix` 8,
`phoenix:classic` 2 — so the gap is a supply-phase one across the whole harvest
and not a quirk of one family.

★ **It is a SCORING backlog and not an embedding one, and `curate embed` closes
none of it.** Measured 2026-09-12, after the sentence above was written: the
embedding store holds **41,415** rows against **40,454** admitted, `curate embed`
reports `missing: 0, wrote: 0, complete: true`, and there is **nothing
outstanding at all**. Of the 1,636, **1,607 have no supply-sidecar row of any
kind**, 29 are scored and sit *under* the junk floor (`p_ge3` 0.0011 to 0.0989,
median 0.0512), and **0 are over the floor and unembedded** — which is the only
bucket `curate embed` can act on. [`embeddings.admitted`] is the sidecar read
through `floors.passes_junk_floor`, so a location the sidecar has never scored is
invisible to that command by construction: **`curate score` is what has to run,
and it has to run first.** The 29 want nothing done — a location the judge calls
junk is not one this collection may ship, which is what admission is for.

⚠ **Ordering, and it is the whole of the mistake above.** `curate score` fills the
sidecar, `curate embed` embeds what the sidecar admits. `discovery/README.md`'s
merge recipe already runs them in that order and says *and nothing else*; a
diagnosis that reaches for the second without asking whether the first has run
will price a backlog at zero and find nothing to do, which is exactly what
happened here.

### ⚠ No BINDING reaches the opened-but-unscored places, and `curate score --opened` is the door

★ **The line above is right that it is a scoring backlog and wrong that `curate
score` owes the work.** Measured 2026-09-15 over the live store: **1,607 of
42,113 opened locations have no supply-sidecar row**, which is the same 1,607 read
on 2026-09-12 — the number has not moved in three days, and it cannot, because
**not one of those places is on any walk ledger**. Bind all **54** ledgers across
both tiers, drop **every structural gate**, and take the whole **292,139-row**
union: it holds **zero** of them. This stage reads walk ledgers and there is
nothing there to read.

★ **`--opened` closed it the same day, and it is a POPULATION and not a fourth
filter.** `intake.opened_backlog` reads the **candidate ledger** — one row a
place, the family, viewport and maxiter the place's own candidate row carries —
so no binding is resolved and `--ledger`, `--harvest`, `--key-file`, `--limit`
and `--unscored` are all refused beside it: there is no walk binding for them to
narrow. Everything after the population is the stage's existing code, because a
row to stand on was the only thing these places ever lacked.

**The regime question the paragraph below called open was already answered in
`intake`.** A row that states no `score_regime` has never been scored here and is
read at `intake.READ_REGIME`, the node regime, exactly like every other piece of
standing stock in that position — the location head being regime-robust is what
makes that read comparable with the rest of the pool. These rows state none,
truthfully, so they take that path with nothing new decided. Every sidecar row
carries the regime it was read at, so a re-read at another geometry is one
command over the same keys if Matt wants a different answer.

**What it cost and what it bought, 2026-09-15**: 1,607 places, **106 s**, 1,607
node-regime renders and one head pass. **1,470 clear the junk floor (91.5%),
1,249 the keeper floor (77.7%), 609 the great cut (37.9%)** — against
**50.0% / 33.4% / 11.4%** on the same day's uniform 16,720-row pilot of fresh
ckpt-123 harvest supply. The best-evidenced places in the project read 2.3x the
keeper rate and 3.3x the great rate of what a walk finds, which is what *the
places outside the admitted population are disproportionately Matt's own graded
ones* looks like once somebody scores them.

⚠ **The sidecar row is necessary and not sufficient, and the second half is
`curate embed`.** Every draw stands on `hunt.scanned`, which is the **embedding
store** less what the junk floor has since dropped, so a place with a fresh
sidecar row is still invisible until it has a vector. `--opened` → `curate
sidecar save` → `curate embed` → `curate embeddings save` is the whole of it, and
the `--floor-places` leg that motivated this planned **0 candidates over 0
locations** before the embed and **17,640 over 1,470** after. A manifest naming
places `scanned` does not hold is not refused — it is silently narrowed to
nothing, and `[depth] --floor-places: N of M named place(s) are opened and
drawable` counts `world["best"]` rather than `world["by_key"]`, so it read
**1,607 of 1,607** on both sides of that change.

**Where they came from says why.** `provenance.run` on the 2,827 candidate rows at
those places reads **2,799 `label_migration_0908`**, 22 `ckpt120`, and six across
three later legs. `curate label-migration merge` derives rows from the **label
stores** at candidate geometry and never walks — so a place it opened has a
candidate row, a picture and a human grade, and no ledger row anywhere. The join
is sound and that is the point: 40,506 of the 42,113 opened keys *do* match a
sidecar row, so the 1,607 are a real absence rather than a spelling mismatch.

★ **So the places outside the admitted population are disproportionately Matt's
own graded ones**, which is the opposite of what a backlog usually means. Every
draw that stands on `hunt.scanned` stepped over them and the near band's manifest
cut named them and dropped them in silence, until the flag above existed; what no
amount of `curate score` *with a binding* could do is still true, and is why the
door is a population rather than another way of asking for one.

**The judged half of the list is four times the opened half, and `curate depth`
reaches only the opened one.** Every place carrying a human verdict ≥3 in the
location store or either finished store, less every place any of the 55 ledgers
names at all: **4,712**, of which **1,607 are opened and 3,105 were never opened
at all**. The 1,607 are exactly the opened-but-unscored set — the two populations
coincide to the row — so `--opened` closes the depth-reachable half whole.

⚠ **The other 3,105 are NOT `curate hunt --places`' population**, which the line
here claimed until 2026-09-16 and which is false for the same reason
`--floor-places` could not reach the 1,607. See the section below.

### ⚠ `curate hunt --places` cannot reach an unopened place either, and `--graded` is that door

★ **A hunt's population is the ADMITTED one, so a place with no sidecar row is
refused rather than hunted.** `hunt.scanned` is `embeddings.load` through
`admitted_only`, and `hunt.narrowed` **raises** `HuntRefused` when a manifest
leaves nothing. So the mirror-flag reading — *`--floor-places` names places the
ledger already stands on, `--places` names places it stands on none of, and the
pair is the path from a crawl to a seat* — holds only for places that are already
**scored and embedded**. It says nothing about a place no walk ever found, and
that is the whole of this population.

**Measured 2026-09-16 over the three label stores**, at a human verdict ≥3:

| | places |
|---|--:|
| graded, distinct | **6,202** |
| with a supply sidecar row | 3,092 |
| in the embedding store | 2,931 |
| **in neither** | **3,110** |

By store, the unreachable 3,110 split **2,025 location-only / 545 smooth_render /
481 strange_render / 59 both finished**, with **no location+finished overlap at
all**. That split is the explanation rather than a detail: a location-store row is
a *place* and not a picture, so it carries no recipe for `curate label-migration`
to derive a candidate from, and label-migration is what opened the 1,607. The
location store was never its population and never could have been.

★ **`curate score --graded` is the fifth population**, and it stands to `--opened`
exactly as `--opened` stands to a binding: `intake.graded_backlog` reads the three
label stores, mints one row a place at its best verdict — the family, the viewport
and the maxiter the label row already carries — and refuses `--ledger`,
`--harvest`, `--key-file`, `--limit` and `--unscored` beside it. It also refuses
**`--opened`**, which the three filters do not have to: the two populations
*overlap* at every place that is both graded and opened, and a pass claiming both
would mint that place twice under two different `ledger` names. Run `--graded`
second; a run of `--opened` shrinks it.

**Ordered best verdict first** — 860 at verdict 4, 2,250 at verdict 3 — so a
truncated pass is a pass over the better half rather than over whatever the stores
happened to list first.

⚠ **These places are dearer to score than the 1,607 were, by 5.7x.** The 1,607
cost 106 s for 1,607 node-regime renders, about 66 ms each. The graded backlog
smoked at **377 ms a place**: they are deep human-found zooms at 11,000–17,000
iterations where the opened set was standing walk stock. Budget the population at
its own rate and not at `--opened`'s.

**`maxiter` is the one field two rows at one place can disagree about**, and they
do — 205 of the 6,202 places, over 1,097 rows. **None of them is in the backlog**:
every one is a place a walk already reached, whose sidecar row settles it. The log
line counts the backlog's own disagreements for that reason, since quoting the
population's number would put a four-figure count beside a pass where the question
does not arise. A place is its family and its viewport in any case, never its
iteration count.

`curate score --unscored` is the door for the **other** backlog, the one that is
on the ledgers: 132,992 of 242,007 gate survivors across those 54 ledgers have no
sidecar row, and most of them sit on smoke, dedup and demo runs
(`dynamical_proven_smoke` 15,148, `harvest_engine_smoke` 8,581,
`demo_neighborhood` 7,407) that are not standing supply. **The binding is what
decides that, not the flag** — which is the whole of why there is no default.

⚠ **The roster is the second test and it is real but smaller.** The draw holds the
incumbent's mode, so a composite incumbent costs about 175 s a location — the arm
measured **6.2x dearer** on the twelve-mode roster — which is why
[`near_manifest`]'s roster defaults to [`field_modes`]'s three and not to
`mode_policy.mined()`'s twelve. Narrow the *manifest*; widening what the planner
admits re-prices the band by moving which incumbent wins the argmax, and that is
not this change. At band 2's cut, 284 places had room and **219 of them had a
`smooth`/`stripe`/`tia` incumbent**. The roster has been three since `curvature`
left the mines on 2026-09-06.

**`free-slots` is still the right verb for the free-slot census** and is unchanged;
what it is not is a near-band manifest, because it asks neither the band nor
admission and it sums a place's room over **every** pair it holds rather than the
incumbent's. Room in `stripe` buys nothing at a place whose incumbent is `smooth`.

⚠ **A near band over a PRUNE-FREE breadth arm's own places is the one shape that
buys nothing, and the two settings are in direct tension.** A breadth arm sized to
be prune-free puts exactly `RETAIN_PER_PAIR` rows on every (place, mode) it opens —
that is what "prune-free" means — and the near band then holds the incumbent's mode,
so every row it makes lands on a pair that is *already full*. Measured
2026-09-05: `thin_b1` ran width 12 over four modes, 3 a pair, and merged **2,634 of
2,634, prune-free**; `thin_b2` then took its 222 places and kept **89 of 912,
9.8%** — `draw_cells_smoke`'s 9.7% reproduced exactly, on fresh places, with the
narrowing the flag exists for. Two ways out, and they are choices about the
*breadth* arm rather than about this one: give the breadth arm a width **under** the
keep so the near band has room, or accept that the near band's value is pool
*quality* — the prune drops the weakest of the four and keeps the leg's best — and
not stock.

**The first way out was taken on 2026-09-05 and it does exactly what the arithmetic
says — no more.** `night_a1` ran **width 8** over the same four modes, 2 a pair
against a keep of 3, and merged **11,090 of 11,090, prune-free**, leaving one slot
free at every pair. `night_a2` then took its 1,388 places and netted **+218 rows —
one per place, which is one per free slot.** It made 8,720 rows to buy those 218,
kept 556 of them, and **493 of the 556 (88.7%) are q4 clears**: what the extra width
bought was the *right* three rows in each pair, not more rows. So the two ways out
are not alternatives after all — **width under the keep buys the near band exactly
`RETAIN_PER_PAIR - width/modes` rows a pair and the rest of its value is still
quality.** Size a near band for the quality and count the stock in free slots.

⚠⚠ **And there is a way to build that manifest EXACTLY BACKWARDS, which cost a
whole near-band unit on 2026-09-06.** `thin2_b_near` was given the proven near-band
places *less the ones the floor arms took*, on the reasoning above — and the floor
arms had taken every place that **had** a free slot, so what the subtraction left
was precisely the pairs already at the retention keep. It made **13,265 rows and
the merge kept 39 — 99.7% pruned**, for 1,392 s of render wall, a tenth of the
night. Every other unit that night lost under 5%, and the near band alone is 72%
of the night's whole 18,464-row prune drop.

**The rule is `free slot AND not taken`, never `not taken` alone.** A place is
worth a near-band pass because it has room, and "the floor arm did not take it" is
evidence of the opposite where the floor arm's own manifest was cut on free slots.
Both halves are cheap to compute, and since 2026-09-12 both of them plus the band
and the admission test are one command — see *Cut the manifest with `curate depth
near-places`* above:

```
fractal-wallpapers curate depth near-places --min-slots 2 --out scratch/near_places.jsonl
```

`--out` writes the manifest `--near-places` reads, best-stocked first, so the
population a leg draws is the one that was counted. **Cut it this way and not by
subtracting one manifest from another** — that subtraction is what went backwards.
The failure is silent at plan time: the draw plans, renders and reports a rate,
and only the merge says the rows were never going to be kept. `merge`'s
`kept at K=<keep>` line is the check, and it is worth reading after the FIRST
near-band unit of a night rather than after the last.

The arm is worth its clock on those terms: at **6.2 engine seconds per KEPT q4
clear** and **28.4 kept q4 clears a leg minute**, `night_a2` tied the recolour arm as
the cheapest buy of that night and beat both openers by 5-7x.

⚠ **At the keep of 5 the free-slot half stopped narrowing anything, and the whole
of `smooth`/`stripe`/`tia`'s near band is four engine-hours.** Measured
2026-09-06 by `MINE_ckpt112_two_arm_pilot_0906`, on the store the keep flip left:
`free-slots --mode smooth --mode stripe --mode tia --min-slots 2` names **23,597
places**, and **23,619** hold a candidate in one of those modes at all — so the
manifest is 99.9% of the population and the subtraction it exists to replace has
nothing left to take away. What bounds the arm is the **band**: only **2,954** of
those 23,597 hold a best field candidate between the two bars, and every one of the
2,954 is in the manifest, so `--near-places` and the unnarrowed draw plan the same
places here. Cut the manifest anyway — it is a subtraction rather than an inference,
it costs seconds, and it is what refuses the inverted shape above — but **do not
size a leg on the belief that it narrowed**. `armB_freeslots_0906` planned the whole
2,954 at width 12, made all **35,448** candidates with **nothing stopped for
budget**, and spent **14,318 engine seconds of a 17,500-second half**: the arm could
not absorb an even split of one afternoon, let alone a night.

**It will also exhaust its population far inside its budget, because the band is
narrow.** Of `thin_b1`'s 222 places every one held a candidate in a roster mode and
only **38** sat between the two bars, so the arm planned 912 candidates and finished
in **129 s of a 600 s cap**. Size a near band off the places that will be *in the
band*, which is a fraction of the places a leg opened, and have somewhere for the
unspent clock to go — `rare_cells_0904` and this leg both sent it to a fresh unit of
the opener arm.

⚠ **That reading inverted overnight on 2026-09-07, and the cause is the roster.**
`armB1_0906` ran the same arm over the same kind of band and was **stopped by the
clock 81 candidates short of exhausting it**, at a budget share of 1.0012 — where
`armB_freeslots_0906` had 1,142 s spare over a band five times larger. Two things
moved at once. The band **collapsed**: re-cut against the day's own scores it held
2,503 places, of which only **542 had room at their own incumbent pair** — 910 free
slots against the 5,799 the previous leg consumed, because that leg shut its own
channel and only the opener refills it. And the arm got **6.2x dearer**, because a
twelve-mode roster hands [`plan_held_mode`] composite incumbents. So a near band is
not reliably the arm with clock to spare: **it is bounded by slots and priced by the
incumbent's mode, and either can bind first.**

**Cut the manifest as free slots at the INCUMBENT's pair, not as free slots.** The
band and the room are different questions and the second is per (place, incumbent
coloring). `curate depth near-places` is that rule since 2026-09-12 and it is the
only spelling of it; `free-slots --mode X` answers one mode at a time and sums a
place's room over every pair it holds, which is the same trap one level down. Done
at the incumbent's pair the arithmetic is exact — `armB1_0906`'s manifest named **1,192 free slots
and its merge grew the ledger by 1,188**, four rows in twelve hundred. Everything
else it made, 5,775 rows, was displacement the prune resolved inside the pair.
`armB_0907` reproduced it a day later at a fifth the size: **460 free slots named,
458 rows of growth.**

**The band has two halves and only one of them is supply-limited.** The *with-room*
half is the places holding a free slot at their own incumbent pair; a breadth arm
refills it at about a fifth of what it opens, so **arm B cannot be given more clock
than arm A earns for it**. The *at-the-keep* half is two orders of magnitude larger,
a breadth arm cannot add to it at all, and a row enters it only by **beating an
incumbent** — net ledger growth is zero by construction, one row deleted per row
kept, and what it buys is quality inside the pair rather than stock. So weighting a
night toward the near band is a decision about **which half**, not about the split
between the arms. The three readings that rule is cut from are
[`LEGS_decisions.md`](LEGS_decisions.md)'s *The opener refills the band at about a
FIFTH of what it opens, and that is what bounds arm B*, *The displacement half is
not supply-limited, and that is what it is for*, and *What the near band buys,
decomposed by the incumbent mode, measured 2026-09-07* — the last for the price
split between a dumping incumbent and a dear one, and for the check that a unit's
mode *is* its incumbent's.

### A reframe leg's places are opened by `curate hunt --places`, at phase 0

A `reframe` leg writes **locations**, not pool rows, so everything it finds is
unopened, and `curate depth run --floor-places` cannot reach an unopened place — nor
a freshly opened one, since the floor draw stands on places already holding a
candidate over `Q4_BAR`. The whole path, as `reframe30_atlas_grey_ckpt127` ran
it on 2026-09-16 over `reframe_g12`:

```
fractal-wallpapers curate score --harvest artifacts/reframe_g12   # 201 scored, 28 s
fractal-wallpapers curate embed                                   # 197 admitted, 2m15s
# manifest: sidecar rows whose `ledger` is that walk.jsonl, over the junk floor
fractal-wallpapers curate hunt run --name <name> --places FILE --per-location 12 --unconditional <12 x places>
fractal-wallpapers curate hunt merge --name <name>
fractal-wallpapers gallery-grade score-pool
```

`--per-location 12` is every mode of `mode_policy.mined()` once — width 1 at pairs
that are empty by construction — and the palettes are stratified over the carrier
table's cells. **The hunt has no phase axis**: every candidate draws at phase 0, so
`--phase-draw`'s one-uniform-phase rule does not reach a reframe leg's first
opening. Measured: 2,364 candidates over 197 places in **2,914 s on three
workers**, 1.23 s a candidate; **221 over `Q4_BAR` (9.35%) at 117 of the 197
places**, `threads` and `smooth` 42 each down to `direct_trap_lines` 1. That hunt has
no `merge.json` (its merge failed at the prune, below); reconstructed after the fact
from the ledger and the displaced lists, **197 of its 197 places were new** to the
ledger, as they are by construction for a reframe leg.

**A merge record counts places two ways**, since `preclose_wallpapers_ckpt127`:
`locations_in_leg` is the distinct places the leg's rows stand on, and `locations_new`
is how many of those the ledger held no row at before the upsert — read off the same
pre-upsert pass [`retention.drawn_before`] makes, because after the upsert the leg's
own rows are the prior rows. The old `locations_added` was the first number under a
name that promised the second. `m1_freshbox`'s record carries both, backfilled: 138
and 118.

⚠ **`merge` can fail AFTER the rows land.** On that run the prune's final
`os.replace` of `rows.jsonl` raised `PermissionError` (WinError 5) — a transient lock
on a 640 MB file just written. The upsert, the scores and the flatness sweep had
already happened and the prune unlinks its temps before raising, so the store was
whole; what was skipped was the ratchet mark and the four durability saves. The
recovery is `curate candidate-ledger prune`, `candidate-ledger save`, `flatness
save` and `signatures save`, in that order — not a second `merge`. **Since
`merge_back_ckpt127` the replace is retried** on `PermissionError`, five times over
about ten seconds (`sweep.REPLACE_BACKOFF`), and says so on each wait; a lock held
past that still raises and the recovery above still applies.

### A counterfactual by merge stamp is only clean for an arm that PRUNED NOTHING

`GALLERY.md`'s *A scratch driver asks the same two questions* documents the pool-view
door as a controlled read and warns that the leg is not monotone in its candidate
set. There is a second limit it does not state, and a near-band arm walks straight
into it: **holding out a leg's rows does not undo that leg's prune.** The rows it
displaced are deleted, so the narrowed pool is not "the pool as if the leg never
ran" — it is that pool *minus the incumbents the leg destroyed*, which flatters the
arm being priced.

Measured 2026-09-07: the pool with the whole night held out read **260,570
candidates against the 260,862 the same pool held before the night**, despite also
carrying ~1,000 pilot rows the earlier read lacked. The 292-row deficit is
`armB1_0906`'s prune. A breadth arm has no such problem — `armA1_0906` and
`armA2_0906` dropped **0** rows between them, every candidate landing on a
never-opened pair — so credit an opener through the door freely and read a near-band
arm's counterfactual as an upper bound on what it bought.

**And do not read the objective's `worst` off one of these.** The same night's reads
gave worst **0.3317** on the full pool, **0.1963** with arm B held out and **0.3541**
with *both* arms held out — a quantity that falls when one arm leaves and rises when
two do is being set by where the greedy search landed. Seat attribution and the
arms' own clear rates priced that night; the objective could not.

The parameter under it is `near_named` and not `near_places`, which is what the
flag is called. `build_plan` calls [`near_places`] to take the draw, and a
parameter of that name would shadow the function for the whole of it.

### `--draw-maps` is the palette twin of it, and it is a draw filter and nothing else

`--draw-maps FILE` is a maps **manifest** — a JSONL of `{"schema": 1, "map": ...}`
rows, plus a `kind: "method"` header row that says how the cut was made and is the
one row that may name no map. It narrows what **every** draw in the run may offer,
which `--floor-places` deliberately does not: places are one draw's business and
palettes are all of them.

**It re-marks nothing.** No verdict, bar, retention rule or tracked colour record
reads it; a narrowed run writes the same rows a wide one would have, keyed the same
way, and the record says what it drew from (`config.maps_offered`,
`maps_drawn_from`, `maps_narrowed`). It is the mechanism for a leg aimed at the
colours a seating is thin in — cut the manifest off `data/palettes/color_mass/`,
drop the maps whose mass sits in the cells the seating is already full of, and the
run spends its palettes where a seat is still available.

Two refusals, both of them the design working:

- **A map the drawable pool does not hold is refused**, not dropped. The pool is
  `colorize.pool` at the **run's seed**, and the palette-group collapse stands a
  *different member* of each group up on a different seed — so a manifest cut at
  seed 0 and spent at seed 20260903 names maps that pool does not hold. Cut the
  manifest at the seed it will be spent at. (The colour decision is per *group*,
  which is what `color_mass` is keyed on, so re-cutting at another seed keeps the
  same groups and changes only which member stands up.)
- **A manifest leaving NO map is refused**, and a small one is not. Both cuts
  refused below `colorize.CANDIDATES` until 2026-09-09, on the grounds that the
  palette head asks a 32-map neighbourhood of each anchor — but **no arm here asks
  the head anything**: `flat_maps` samples the pool with a seeded RNG,
  `plan_held_mode` and `plan_floor` sample what a place has not spent, `aimed_maps`
  draws through the carrier table, and each takes `min(width, len(pool))`.
  `colorize.candidate_set` is reached only from `Colorizer.attempt` and
  `labeling.sheets`, and what renders here is `mine.make`, which takes the map off
  the shot. The bound was inherited from a path this leg does not take and it
  refused legitimate narrow manifests. (`colorize.pool`'s own `< CANDIDATES` guard
  is about the shipped **library** and still stands.)

#### Aiming the whole manifest at ONE DROP is the cheapest coverage there is

A manifest cut to a drop's own maps and spent through the **mode-floor** draw is
how a leg buys per-map coverage rather than per-cell colour, and the arithmetic is
worth stating because it is not the arithmetic of the cell filters above. With `L`
named places, `M` modes and `--floor-width W` out of a manifest of `N` maps, each
map lands at about `L * (1 - (1 - W/N)^M)` **distinct** locations — the modes are
drawn independently at a place, which is what makes width cheaper than places.
`sheet_leg_0905`, 2026-09-05: `L=600`, `M=4` field modes, `W=8`, `N=120` predicts
145 and realised a **median of 144, a minimum of 119** over the 120 maps.

**Measured price, and it is the cheapest depth leg on this page.** 19,200
candidates over 600 proven high-band places at `smooth`/`tia`/`stripe`/`curvature`,
three workers, **3,810 s of render wall** — 19,200 made, 0 failed, 0 stopped for
budget — at **0.5895 s a candidate per engine** and a concurrency of 2.97. The
dump is a third of it (33.1%) and the autolevel operator's `measure` another
30.8%, which is what a leg looks like when every candidate is a recolour: the
operator acted on **12,480 of 19,200 (65%)**.

⚠ **A forty-place pilot over-priced this leg by 1.7x.** `sheet_pilot` measured
**1.0022 s a candidate** on 42 places drawn out of the same high band under the
same roster and the same manifest, and the leg came in at 0.5895. Nothing about
the method differed; the pilot's 42 places were simply deeper than the 600's
median. A pilot over tens of places prices *those* places' depth, so read it as
an upper bound and set `--budget` off it rather than sizing the plan to it — this
one planned against 9,000 s and spent 3,810.

#### What a drop buys at the gallery is read as a PAIR of records, and the reach bounds it

A drop is aimed by the two sections above and read by solving twice over one config —
once before the leg merges and once after — and comparing the two tentative records.
`SOLVE_after_new_maps_0905` is the first such pair: seven records a side, a general
n=1000 and the six themed n=200s, **8 min 51 s** for all seven sequentially.

**Assert the config before reading anything.** τ, the spiral cap, the `threads` ceiling,
the themed cap and the mode floors all have to be identical, and the assertion is per
dimension off `config` on each `manifest.json` — a record that does not *name* a knob
ran without it. The themed group cap is the one that used to move on its own: while it
was `ceil(2n/P)` the grown pool changed it, so no themed pair taken before 2026-09-05 is
a comparison of one rule. It is a share of `n` since, but the **share** moved on
2026-09-12 — `0.05` to `0.075`, 10 seats to 15 at n=200 — so a pair straddling that date
is not one rule either, and a themed record made before it ran at two thirds of today's
cap. The assertion catches both: `config.ceiling.group_cap` is the number on each side.

⚠ **"One seat per location, so a new-map seat displaced some map" is false in practice.**
Of `classic-pairs-2026-09`'s 54 general seats, **4** took a place off another row; **33**
sit at a place the baseline gallery did not hold at all, and 17 were already seats. What
a drop displaces is a *location*, not a map — the general gallery dropped 99 places and
took 99 others. Read the pair at the gallery level and quote the same-place pairs as the
handful they are.

**The reach is what bounds the seat count, and it is the number to quote beside it.**
Only **508 of the baseline gallery's 1,000 seated places held a new-map row at all** and
only **412** were touched by the mine, because a floor leg stands on free slots and the
best places are already three-deep at `smooth`. So a low count means "has not competed at
the best places yet" and never "loses" — and against the ~508 places where the drop was
present, 54 seats is about a tenth.

**A leg that clears nothing seats nothing, and the clear rate predicts it.** The mine's
`curvature` unit cleared **0.29%** at 421.7 engine seconds a clear and its 693 rows took
**zero** seats across all seven records; `tia` at 8.42% took 49. And a drop reaches the
solver through **every** leg that ever drew it: `sheet_leg_0905`'s 5,091 surviving rows
sit at *proven* places and out-seat the mine's 10,121 on three of the six themes.

### `--draw-cells` is the same filter cut by RULE instead of by hand

`--draw-cells CELL …` narrows the same pool `--draw-maps` narrows, and the two
**compose — both filters apply**, because a manifest is a list somebody wrote down
and this is a rule with a threshold, and a leg that gave both meant the
intersection. Sparse, and unsaid it is every cell, which is `colorize.pool`
untouched and bit-for-bit what a run drew before the flag existed.

A map is kept when **any** listed cell clears the cutoff — not all of them, because
a pool cut to the maps serving all five thin cells at once is a handful of maps
spread over five cells, which is not a leg aimed at five colours but a leg aimed at
whatever those few maps happen to carry. The probability is
`palettes.color_mass.delivering`: **mode-conditional mass where there is a row for
the map's palette group, the carrier prior where there is not** (942 of 943 groups
are measured, and the one that is not — `blue_orange` — is not drawable, so **the
prior branch never fires on a map a leg can offer**; re-read 2026-09-12, the
reading was 822 of 823 before `classic-pairs-2026-09` was swept in), and the
**max** over `mode_policy.accepted()` rather than the mean,
because the pool is shared by every arm and every mode in the leg — a map dropped
for failing on modes the leg will not run is a map narrowed away for nothing.

`--draw-cutoff` defaults to `palettes.dominance.CELL_LEAD` (0.10) rather than to a
constant of its own, so the filter reads as *this pair is expected to be dominant
here*. At 0.10 the thinnest cell (`dark_vivid_lime`) offers **42** maps of the
942-map collapsed pool and at 0.15 it offers **32**. Those two readings were the
argument for the default while the cut was refused below 32; since 2026-09-09 only
an **empty** cut is refused, so they now say what the bar costs in supply rather
than where it becomes illegal — a leg cutting to a dozen maps is a leg that meant
to, and the message still names the cutoff because the cutoff is the knob that
fixes it. *(Read 2026-09-06,
after `classic-pairs-2026-09` was measured into `color_mass`; before that sweep the
same two readings were 40 and 28, so 120 maps of measured mass bought the thinnest
cell two offers at the default bar and four at the tighter one. The 822 the older
reading names is the pool before the drop, not a different rule.)*

**It reaches the near band, and that is the point.** The near band deepens a place
whose field is already dumped, so a recolour there costs a colour pass and nothing
else — the cheapest colour a leg can buy. Narrowing only the breadth draws would
leave the cheap arm spending its width on the colours the seating is already full
of. `plan.maps_after_the_manifest` against `plan.maps_drawn_from` says what each of
the two filters took.

**The filter narrows what is OFFERED and does not control what is DELIVERED, and
the gap is a fact about the mode's KIND.** Measured over `thin_cells_1h_0905`,
11,705 candidates on a pool cut to 389 maps of 822 for fifteen vivid cells:

| roster | share of rows landing a listed cell |
|---|--:|
| the four shareable **field** modes | **57–59%** |
| the five **composites** | 52–69% |
| `itinerary` | 85% |
| the three **direct traps**, `direct_trap_multiply`'s four settings cells included | **0–33%** |

**And the control the table wanted was taken on 2026-09-05: an UNAIMED leg puts
about a third of its rows in those same fifteen cells anyway.** `night_a1`,
`night_a2` and `night_a3` drew the whole 822-map pool with no `--draw-cells` at all
and landed **32.4%, 34.0% and 32.9%**; `night_b`, the same three field modes under
both filters, landed **59.6%** over 51,959 candidates. So the cut is worth **about
1.8x** on delivery and never more — the 57-59% above is not the filter's doing on
its own, it is 33 points of base rate plus 26 of aim.
The five `direct_trap_multiply` cells returned **0, 0, 2, 1 and 1** rows in any
listed cell out of 46 candidates each, and **not one q4 clear in a listed cell
between them**. That is [`palettes.color_mass.NOISY_MODES`] acting: their pictures
are not lookups into their own maps — supersampling and JPEG average colour *after*
the lookup — so the ramp read the cut is made on does not predict them. **A leg that
wants a thin cell should not spend its clock on the direct traps**, whatever
`delivering` says about the maps it offers them; buy those modes' pictures on their
own terms and let the colour fall where it falls.

**Every row a narrowed leg writes is stamped `hunt.drawn_cells` and `drawn_for`
beside it is the ASK's**, both `candidate_ledger.ASKED_FOR` and both
written only where there is an ask — [`LEGS_decisions.md`](LEGS_decisions.md)'s *The
aim is not what fails, and `direct_trap_multiply` has no vivid half*.

**Which makes the aim's hit rate a group-by over ledger rows, and the cheap route
agrees with the dear one.** `drawn_for` and `colour.cells` are on the same row, so
the rate is `asked == delivered` grouped by cell, with the flat control being every
row in the store carrying **no** ask — no leg's `sequence.jsonl` opened and no leg
still on disk. Read that way on 2026-09-15 over 7,820 stamped rows: **median lift
13.64x, range 5.4x to 31.27x**, against the **14.6x median** `overnight_mine_ckpt125`
read off `sequence.jsonl` the night before. The two routes agree inside the noise of
one prune, and only the ledger route survives the leg's directory being deleted.
⚠ The population is every aimed leg the store still holds, not one leg — narrow on
`provenance.run` for a single leg's rate.

⚠ **The filter SATURATES in the length of the cell list, and the default cutoff
hides it.** A map is kept when **any** listed cell clears the cutoff, so every cell
added makes the test easier, and `--draw-cutoff` is a per-cell bar that does not
know how many cells it is being asked about. Measured over `colorize.pool`'s 942
maps on 2026-09-14, on the non-`lime` cells with the most `tia`+`stripe` headroom:

| cells listed | @ 0.10 | @ 0.15 | @ 0.20 | @ 0.25 | @ 0.30 |
|---|--:|--:|--:|--:|--:|
| 8 | 610 (65%) | 480 | 386 | 311 | 243 (26%) |
| 19 | **938 (99.6%)** | 895 | 801 | 705 | **580 (62%)** |
| 25 | **940 (99.8%)** | 910 | 843 | 757 | 641 (68%) |

At the default 0.10 a nineteen-cell list is **not a filter at all** — it keeps 938
of 942 and the leg draws the untouched pool while its log reports a narrowing. It
takes **0.30 to cut nineteen cells to 580**, and 0.30 is a *quarter* to a third of
a picture's colour rather than the `CELL_LEAD` 0.10 at which a cell merely leads.
**Pick the cutoff against the length of the list** — `easy125_recolour` ran nineteen
cells at 0.30 for this reason. Checking afterwards that the cut happened is no
longer the caller's job:

**Since 2026-09-15 a saturating cut is REFUSED rather than reported.** A plan whose
cell cut keeps more than [`depth.CELLS_NARROW_AT`] — **0.90** — of the maps the
manifest left raises `DepthRefused`, at plan time and before a single field is
dumped. A warning was the other option and it is the wrong one, because the lie is
written onto the rows and not only into the log: a narrowed leg stamps
`hunt.drawn_cells` on every row it makes and `cells_narrowed` on its record, and
both say *this is not a base rate* — so a 24-cell list at the default put a
colour-narrowed provenance on 21,000 ledger rows that outlive the leg. The refusal
names the measured share and the three ways out (raise the cutoff, list fewer
cells, drop the flag and let the leg say it drew the whole pool); the share the cut
actually kept is on the plan as `cells_kept`, beside the bound it had to beat.

### `--cell` is a CYCLE, so a repeated cell is a weighted aim

[`_plan_aimed`] hands place `i` the cell at `cells[i % len(cells)]`, and nothing
between the parser and there deduplicates: `asked_cells` is built as a list, the
unservable-cell filter is a comprehension over it, and the known-cell check is a
membership test. **So listing a cell twice gives it twice the arm.** That is the
only way to spell a weighted aim with a flag whose type is a set, and it needs no
code — `--cell green_a green_a green_b cyan_a` is three-quarters green.

`easy125_wide` used a **41-slot cycle** to aim eight hue families in proportion
to each one's shortfall against n=500 (green 12 slots of 41, purple 1), split
within a family across its four cells by that cell's own remaining headroom, and
**woven one family at a time rather than emitted family by family** — the same
reason [`_plan_aimed`] cycles rather than concatenates, since a clock-bound leg
always truncates and a block layout starves whatever is last.

**Measured, and the aim is worth 4.5x to 6.6x at the FAMILY.** Against the matched
`flat` control in the same leg — same places, same bands, same width, differing in
the palette ask alone:

| aimed at | candidates | cell hit | family hit | flat control | lift |
|---|--:|--:|--:|--:|--:|
| green | 902 | 60.0% | 77.2% | 12.6% | **6.14x** |
| cyan | 686 | 48.4% | 65.9% | 11.4% | 5.76x |
| teal | 613 | 44.4% | 64.3% | 11.1% | 5.81x |
| yellow | 324 | 54.9% | 76.8% | 17.1% | 4.49x |
| rose | 168 | 53.6% | 70.8% | 10.8% | **6.55x** |
| purple | 84 | 33.3% | 63.1% | 11.0% | 5.76x |

**Read a family aim at the family and not at the cell.** `depth.hit_rate` counts
*dominant in the cell it was drawn for*, which is the right question for a cell aim
and the wrong one for a family aim: a `light_vivid_green` ask that came out
`dark_muted_green` is a miss in that column and a hit on what an n=500 family pass
seats on. The cell rate under-reads the family rate by 10 to 30 points here.

**And it cost nothing in quality.** The aimed arm cleared `P(>=3) >= 0.50` at
**44.89%** against the flat control's **40.30%** on the same leg — so conditioning
the palette draw did not buy its colour out of the judge's pocket.

**Read at the CELL the same aim runs 5.9x to 40.5x, median 14.6x, and it lands
53.4% of the time.** `on125_wide1` drew 3,084 candidates on a gap-weighted 41-cell
cycle against a same-leg flat control of 4,908, and **53.4% came out dominant in the
exact cell asked for** — `light_vivid_purple` **40.5x**, `dark_vivid_yellow` 24.4x,
`dark_vivid_cyan` 24.2x, `light_vivid_azure` 23.3x, down to `light_muted_yellow`
5.9x. **The lift is largest where the flat rate is smallest**, which is what an aim
is for and is why a cell table reads so much wider than the family table above it:
the aim cannot improve on a colour the pool already makes by accident. So **aiming is
free and it is large** — quote it at the cell when planning a cell, at the family
when planning a family, and never mix the two columns in one comparison.

### `sequence.jsonl` carries the whole autolevel stamp, and did not until 2026-09-02

**A boolean is not a record of what the operator did.** `band_autolevel/v1` renders
an acting candidate through a colormap it re-bakes from the tone band, so the
picture is not the engine's own bytes and nothing but the *curve* rebuilds it —
`autolevel.stops_from_stamp` reads `curve` and nothing else. The ledger row keeps
only the **reduced** stamp (operator, switch, band sha256), deliberately: the curve
is derived from the render and is not part of a recipe's identity. So the curve
lives on the run's own record or nowhere, and for `depth` it was nowhere.

`reframe_draw` puts the whole stamp on each `attempts.jsonl` row and a gallery
`runs` pass writes it to `release/autolevel_stamps.jsonl`; the depth sequence row
now carries it under the same key, `autolevel`, in the same shape, whenever there
is one to carry (`None` only with the switch off). One spelling across all three,
which is what lets the website's `builder/picks.py` read a stamp out of any run
store with one branch.

**Re-measuring is not a substitute and the numbers say so.** The same frame
redrawn and re-measured derives a black point of **0.6336** against the **0.5953**
the run stamped, on `ed49980b` — so a seat redrawn off a re-measurement is a
different picture published under the same name.

⚠ **That inference does not follow, and the same row is the counter-example.**
Re-run on 2026-09-08, `ed49980b03866364` re-derives a black point of **0.5379** —
a third value, further from the stamped one than the figure above — and the stop
list it rebuilds is **byte-identical to the `crisis-25.json` the row actually
shipped through**. The band is `black_pt ∈ (0, 0.3008)` and all three readings sit
outside it, so all three **project to the same edge** and the curve is the same
curve: `sides.black_pt == 1` on every one of them. The quantity that decides the
ramp is the *projected* statistic and never the raw one, which is the whole point
of *each projected onto its band — inside, itself; outside, the nearest edge*.

So the warning holds only where a re-measurement moves a statistic **across a band
edge**, and it is a claim about a statistic that was read as a claim about a
picture. Measured at scale on 2026-09-08: of 277 backfilled seats, **82 could be
compared against the ramp they shipped and 82 agreed, none differed**.

**Old rows are still left exactly as they are, and for a reason that survives all
of the above.** A tracked record is never edited in place, and a curve written
*into* the record from a re-measurement would be indistinguishable from the one the
run derived. What 2026-09-08 added instead is a **sidecar** — an append-only
`autolevel_backfill.jsonl` keyed by recipe key, overlaid at read time, with every
row marked `provenance.curve: rederived` and carrying its own verdict against the
shipped ramp. The objection was to putting a reconstruction where a record goes,
and it is answered by not doing that rather than by not reconstructing. `depth.levelling_of` reads a
row and answers `untouched`, `replayed` or `acted_unrecoverable` — the website's own
three words — and **241,552 of the 457,143 depth rows across 51 runs (52.8%) are
`acted_unrecoverable` forever**. The way out for one of them is its own file, which
is what `picks.seat_picture` copies. The trap the reader exists to avoid: an absent
stamp is falsy, so the obvious `stamp.get("acted")` answers *untouched* for a row
whose boolean says the operator fired.

**What it costs: ~1.16 KiB a row**, measured over `reframe_draw/q4_1h`'s 1,796
stamps — 1,167 bytes median on an acted row, 1,149 on one left alone, `band` 300 of
it, `curve` 373, `measured` 338. Against the sequence row's current ~824 bytes that
is roughly double. It is worth it and it is affordable for one reason: **it lands on
the run record, not on a durable store.** `artifacts/curation/depth/<run>/` is hot
tier and regenerable-or-discardable by the three-way rule; the candidate ledger,
which is the thing that has to stay small forever, is untouched and still carries
the reduced stamp alone. An arm A-sized leg (17,694 candidates) adds about 20 MiB.

The stamp is written on the **sequence** row and not on the in-memory `made` row:
`made` is held whole for the length of the leg and feeds `curves`, `by_mode` and
`rank_readout`, none of which reads a stamp.

**`mine` had the same gap and it was closed on 2026-09-08.** Its `rows.jsonl` is
ledger rows, so it carries the reduced stamp and no `acted` at all; the boolean was
on `profile.jsonl`, which nothing joins by key, and the curve was on nothing. The leg
writes `sequence.jsonl` in depth's shape now and `mine` is in
`stamps.SEQUENCE_STORES`, so a mine-sourced seat lends its curve like any other.

It mattered more than "whenever somebody wants it" made it sound. **`curation.depth`
renders through `mine.make` too**, so this was not one leg's gap: every candidate
either leg has ever made was `acted_unrecoverable` the day it was made, which is most
of the pool. Closing it does not reach backwards — the rows already in the store need
`curate autolevel backfill`, which re-derives rather than recovers.

**Field modes only, and every conclusion is conditional on that.** A composite at
forty candidates is **212 s a location, measured** — one arm's worth of places would
eat a ninety-minute budget — so the roster is `depth.field_modes()`: the shareable
modes `mode_policy` **mines**.

(That sentence read "about 175 s" and was a derivation off a per-candidate rate
until 2026-09-01, when `audit_comp40` measured the visit directly at **212.1 s mean
and 199.5 median** against a field visit's **27.7 / 21.6** and a direct trap's
**75.3 / 47.8** — the three-leg pilot in *Every per-candidate rate this project has
measured*, [`MEASUREMENTS.md`](MEASUREMENTS.md). The estimate was
21% low. What no depth run reports is still what a composite *clears*: these three
legs are unmerged, and their clear rates are the pilot's own.)

**That roster is three modes now, and it was six.** `smooth`, `tia`, `stripe`.
Three of the seven production field modes — `trap_circle`, `gaussian_int` and,
since 2026-09-04, `exp_smoothing` — are `mode_policy` weight 0, and the first two
were two of the cheapest things a depth run could render. The fourth is
`curvature`, which is **not** weight 0: it is on `mode_policy.UNMINED` since
2026-09-06, so the gallery still seats it and no mining leg draws it — see
[`GALLERY.md`](GALLERY.md)'s *`UNMINED` — out of the mines, in the gallery*. (This
paragraph said *four* and named `curvature` as a third weight-0 mode until
2026-09-01; `curvature` moved 0 → 1 on 2026-08-29 and `mode_policy`'s own docstring
carries the ruling. It said *five* and listed `exp_smoothing` until 2026-09-04, and
*four modes* naming `curvature` until 2026-09-06.) A depth leg is
still a narrower instrument than the one the curves were measured on; size one off
a fresh rate rather than off `dc1`'s.

**`trap_circle` is out of the draw and still in the catalogue.** Niche by
`mode_policy` (never given a 4 in 118 labeled rows) and production by the engine's
tier, so it is applied at the draw. Existing material in it stands: its labels,
its ledger rows and its pictures, and a verdict already exported on it still
ingests.

**A composite mode reaches a depth run only through its own leg.** `--modes` is not
checked against `colorize.shareable`, so a composite named there *runs* — it simply
pays a full render a candidate, because `colorize._shared_field` answers `None` for
a coloring with no single scalar field. Do not put one on a roster beside field modes:
`plan_cycled_modes` cycles the roster **uniformly**, so the dear modes take an equal
count and the great majority of the budget, and the single `--rate` that sizes the
plan is then a mean over per-candidate costs that differ by an order of magnitude.
Give them a separate run with `--modes <composite> ...` and their own rate.

**The roster is a filter on one default and nothing under it assumes a field.**
`depth.field_modes()` is read at exactly one site — `build_plan`'s `roster`
default — and every stage below it takes the roster it is handed. `blocks_of` cuts
at the location whatever the kind, `workers_for` counts blocks, `sweep_fields`
returns 0 on a directory that was never made, and `renders.FIELD_IDENTITY` names no
field for an unshareable mode, so the dump lifecycle is a no-op rather than a
special case. Eight legs on the record have already run this way: `sm_comp` made
4,246 composite candidates and `sm_direct` 5,932 direct ones on three workers with
zero failures, and `curate depth` is the **largest** producer of non-field rows in
the ledger — 11,497 of the 21,913, at the lowest share of any leg (10.8%), because
they all came through `--modes` and never through the default.

**Two things the record got wrong when it does, and one of them is fixed.**
`config.field_modes_only` was written `True` unconditionally until 2026-09-07, so
`cc_pilot` claims it while carrying 96 `smooth_angle_min` and `smooth_mean_angle`
candidates, and every unit of the overnight leg of 2026-09-06 claims it on the
twelve-mode mined roster. It is derived from the leg's own roster now
[`depth.field_modes_only`] and a record written since is worth reading; one written
before is not. The second stands: the single `--rate`
prices candidates, while `weave` holds the arms' proportions in **counts**: in
`cc_pilot` the `mode_floor` arm took 25.0% of its planned count — exactly the leg's
own 25.0% truncation — and **24.7% of the engine seconds against a declared 5%
share**, because its two composites cost 5.53 s a candidate against the field arms'
0.70–1.03. A share is a share of the plan, not of the budget, the moment two arms
run different kinds.

### A GENERAL leg cannot close a floor, and the reason is the roster

Measured by `general20`, 2026-09-01: twenty minutes unaimed and unconditioned, the
module's own neutral shares (near 0.25 / ranked 0.50 / flat 0.25), default width 40,
seed 20260902, three engines, **0.5461 s a candidate**. 6,557 candidates over 208
location blocks bought **55 new places** and moved the n=2000 gallery **885 -> 896
seats**, with the shortfall **unchanged at 200 and not one of the nine short modes
moving by a single seat**.

That is not bad luck, it is arithmetic on the roster. `depth.field_modes()` is the
**shareable** modes [`colorize.shareable`] accepts, and **every one of the nine modes
short at n=2000 fails that test** — five composites, three direct traps and one
modulate. The five it does draw are all at zero shortfall already. So the roster a
general leg draws and the set of modes carrying a deficit are **disjoint**, and no
amount of general mining moves the second one.

A general leg is therefore a way to buy **places**, which is what the twin rule
consumes; it is not a way to buy **floors**. Floors need `--modes` naming non-field
modes, which is the 1.9-7.4 s/candidate régime rather than this one's 0.55. Both are
worth running and they are not substitutes.

Two things this leg also measured, both against `empty_modes` — *What the two empty
modes actually cost, measured*, in [`MEASUREMENTS.md`](MEASUREMENTS.md). **The head's
rank buys far less on field modes**: `ranked_bands` beat its `flat` control **1.07x**
here against 1.5-2.2x on the composites, so the ranked arm's premium is a fact about
dear modes rather than about the rank. And the arms rank the other way round —
`near_band` cleared **90.2%** of its locations at **5.8 s a win** against
`ranked_bands` 45.8% / 16.7 s and `flat` 42.9% / 19.8 s, because a near-band place is
by construction one already sitting between the bars. Per-candidate clear rates were
`smooth` 11.08%, `exp_smoothing` 6.35%, `stripe` 5.73%, `tia` 3.61% and **`curvature`
0.51%** — 983 candidates for 5 clearing rows, which is the arm to question next.

**Draw the autopsy sheet BEFORE merging.** `depth merge` prunes at retention K=3 and
deletes the losers' pictures: it took 4,608 of `general20`'s 6,557 candidate JPEGs,
which is the whole bottom of the score ordering. A reject autopsy taken afterwards is
an autopsy of the survivors and cannot be anything else.

**The `mode_floor` arm escapes the roster, by design.** `deficient_modes` iterates
`mine._mined_modes()` — twelve of the thirteen accepted modes, `curvature` being
`UNMINED` — and `plan_floor` never intersects its
modes with `roster`; `test_the_floor_draw_holds_the_place_and_moves_the_mode` pins
that with `threads` and `itinerary`. What bounds it instead is `--floor-seats`,
and at its default of 10 the census returns **`{}` on today's ledger**: every
accepted mode holds at least 23 distinct locations over `P(>=4) >= 0.50`, so an arm
given a share would plan nothing and the other arms would run out of plan rather
than clock. The crossover is around 50, where it names
`direct_trap_multiply`, `direct_trap_lines`, `smooth_angle_min`,
`direct_trap_screen`, `smooth_mean_angle` and `smooth_curvature`, worst first.
Note that 10 is *below* what `mode_policy.seat_floors` guarantees at n = 1000,
which is 15 for a normal mode and 30 for a promoted one. A run aimed at a
named pair passes both `--floor-modes` and a `--floor-seats` above their floor —
`empty_modes` used **60**, at which `seats_short_today` reads `smooth_angle_min` 26
and `smooth_mean_angle` 19; at the default 10 the arm plans nothing and the other
arms run out of plan rather than clock.

**The crossover has moved a long way and it moves again inside one leg.** Re-read
2026-09-08 over 326,549 rows, the census is empty up to **120** — the thinnest
mined mode, `direct_trap_lines`, holds **146** seats against an n=1000 floor of 16,
and the roster runs 146 · 215 · 229 · 251 · 255 · 257 · 368 · 658 · 706 · 3,512 ·
3,591 · 8,857. The smallest round value naming the six-mode dear cluster and nothing
above it is **260**. But `--floor-seats` is a bar on a census the leg's own merges
move: `general_breadth_0908` derived 260 in its preflight, a `depth plan` probe
confirmed six modes, and by the time the floor unit planned — one breadth unit and
one merge later — three of the six were over the line and it drew **three**. So a
value derived before a multi-unit leg is stale at the unit that uses it: derive it
after the last merge before the floor unit, or name `--floor-modes` outright.

**And that census counts the raw recipe mode, not the routed one.** A modulate
whose texture said nothing is `smooth` everywhere the seating looks
(`mode_policy.routed_mode`), and `deficient_modes` does not ask: on 2026-09-01 it
reads `itinerary` at **152 seats where the routed count is 64**, over the 1,085
rows the engine reported `texture_flat`. `best_field_by_location` reads the raw
mode too, so a near-band incumbent can be a degenerate modulate. Neither is live
today — `itinerary` is off the default roster — and both would be the moment a run
named it.

Measured 2026-08-28 at `--width 24 --top-bands 5`, seed 20260827, this machine:

| roster | s/candidate | what it is |
|---|---|---|
| 6 breadth field modes | **0.497** | one dump a (location, mode), 4 palettes off each |
| 2 composites, no sharing | **0.696** | a full render every candidate |
| 2 field modes, near-heavy | **0.278** | `mine1h`, `--near-width 127` over 22 places |
| 4 direct traps, near-heavy | **0.743** | `mine1h`, `--near-width 136` over 11 places |

Every rate above is **one engine's**, which is what `--rate` wants. All four were
measured single-engine; a rate read off a three-worker leg carries that leg's
contention in it and would over-price a serial one by about 1.6x.

**The plan is fixed before the first render, and nothing about the leg is
adaptive.** `build_plan` returns the whole woven plan and `blocks_of` cuts it into
location blocks — the roster cycled *inside* a place, one block per location in the
order that location first appears in the weave — before a worker is handed anything.
From there the only thing that can end the leg early is the **clock**: `_render_block`
checks the parent's `deadline` before each candidate rather than only between blocks,
because a near-band block is `--near-width` candidates deep and a block that could not
stop inside itself would overrun the budget by minutes. **No stage reads a score to
decide what to render next.** Scores enter twice and both are upstream of the plan —
`population` reads the ledger so `best_field_by_location` can find the near band and
`deficient_modes` the floor draw, and `ranked_bands` sorts on the location head's
score — and everything downstream (`curves`, `hit_rate`, `by_mode`, `rank_readout`,
`route_to`) reads what was made and writes the record. Two things follow. A killed
leg is a **prefix** of the plan it was given rather than a different plan, which is
what makes the weave's arm proportions hold at any cut. And "what would this leg have
found at `k = 17`" is arithmetic over `sequence.jsonl` rather than a second run.

### Four knobs a general leg needs, added 2026-09-01

`MINE_overnight_full_roster_centered` wanted a leg that advanced the whole pool at
once while over-serving one population, and four things it asked for had no
spelling. Each is a plan-time filter or weight; none of them adds a store.

```
--centered {any,only,exclude}      the never-opened pool, cut on the walk ledger's flag
--partition-weights JSON           each PARTITION's share of the breadth draw, merged
                                   over the standing curation.draw_weights table
--floor-untried [MODE ...]         narrow the floor draw to places never tried in those modes
--cell CELL [CELL ...]             the aimed arm over several cells at once
```

**`centered` lives on the walk-ledger row and nothing under the draw carries it.**
A nucleus location is `centered` — its centre *is* the location and its scale is the
rung its head picked out of `discovery.reframing.RUNGS` — and `curation.framing`
reads the flag off the row that recorded the find. The embedding store drops it and
so does the supply sidecar, and `hunt.scanned`'s population is the embedding store's
rows: a draw that asked the pool directly would answer *not centered* for every
location in the collection, silently and with no error. So `depth.centered_locations`
joins it back at plan time, keyed on `supply.location.text_of_row` — the key the
embedding rows already carry — over `supply.ledgers.ledger_paths()`, read-only.
**3.6 s over 41 ledgers and 184,967 rows**, cached for the process. Deliberately not
a fourth sidecar: a manifest, a mirror and a staleness rule for a boolean that is
settled the moment a walk writes the row would cost more than the join does.

**The centered population is four partitions, not nine.** Measured 2026-09-01:
**5,805** centered location keys across every walk ledger, of which **4,797 of the
19,623 drawable** — admitted, above the junk floor, and carrying no ledger recipe.
Every one of them is in a *parameter* plane: `multibrot5` 2,534, `multibrot4` 1,648,
`multibrot3` 394, `mandelbrot` 221, and **zero** in the four `julia:*` partitions and
in `phoenix`. That is not a gap in the join, it is what a nucleus is: the operators
that snap to an atom run on the parameter planes. So a coverage floor over partitions
cannot be met by a centered arm and has to be met beside it.

**`--partition-weights` is the soft lean, and it is a different axis from
`--band-weights`.** A band weight says what a stretch of the head's rank axis is
worth and is a *measured* number; a partition weight says what a family is worth
in a draw and is a *declared* one. They multiply in `_cell_turns`, and neither is
a floor: a partition left out still gets its turn a round and none is capped, so
the shape stays "everyone, some more than others". `_interleave_by_partition`
takes the **same table the draw was taken under** — it did not until the
`overnight_c_pilot` reading, arm C of *What the four knobs bought* in
[`MEASUREMENTS.md`](MEASUREMENTS.md), and an unweighted interleave puts a leaned
draw's whole surplus in the tail a clock-bound leg never reaches.

### The standing draw-weight table, ruled 2026-09-02

`curation/draw_weights.py` is the one table and the one copy of the turn
arithmetic three draws share — `hunt`'s unconditional leg, `mine`'s two
`breadth_*` arms and `depth`'s ranked draw with the two matched arms sized off
it. Every partition is 1.0 except **`phoenix` and `phoenix:classic` at 0.25**.

The reading behind it is `dtm_variants` (1,362 candidates, 7,190.6 s): those two
partitions took **63.5% of the leg's clock for 10.6% of its candidates**, with
`phoenix:classic` alone at **51.5% of the clock for 5.3%** — 51.46 s a candidate
against 1.18 for `julia:multibrot5`. A weight scales a share and never removes a
partition, so the table holds a quarter and never a zero: a partition that should
get none of a release is *retired* from the registry, which is the rule
`release_mix.json` already states for its ratios.

```
--partition-weights '{"phoenix:classic": 1}'      # an aimed leg, at full weight
--partition-weights '{"mandelbrot": 3}'           # a release-mix lean, phoenix still 0.25
--partition-weights '{"phoenix": 0}'              # out of THIS leg's draw, by explicit ask
```

### The two phoenix planes are declared in SECONDS now, and the price is per band

Ruled 2026-09-04: **`phoenix:classic` 3% of a breadth leg's engine seconds,
`phoenix` 15%.** `draw_weights.SECONDS_SHARE` is the table that acts and
`DOWNWEIGHTED`'s turn weights are kept only so a record can say what the draw used
to do. A turn buys a *place*; what a place costs is a fact about the partition and
the arm, so declaring turns pinned the wrong quantity — at 0.25 turn weight
`phoenix:classic` was still taking 24.0% of the clock for 2.94% of the turns.

`draw_weights.converted` does the algebra, and it is one line: a partition drawing
`w` turns at `p` seconds a candidate spends `w·p`, so holding every undeclared
partition at its turn weight to share the `1 − Σs` nobody claimed gives
`U = Σ(undeclared w·p) / (1 − Σs)` and `w = s·U/p`.

**The price is keyed on `(partition, band)` and a band never inherits another's.**
This is the part that matters more than the conversion. Measured over nine legs,
`phoenix:classic` runs 17–31 s a candidate on the deep breadth arms and 1.2–1.5 s
in the near band — one plane, one weight, an order of magnitude apart, because a
near-band re-render is shallow. What the ruling comes to today, per band:

| band | seeded from | `phoenix:classic` | `phoenix` |
|---|---|--:|--:|
| `ranked_bands` | `rare_a2` | 25.419 s → **0.0411** | 2.817 s → **1.8521** |
| `flat` | `rare_a2` | 12.616 s → **0.0553** | 0.658 s → **5.3046** |
| `conditioned` | — | not asked: it draws under `flat`'s table |

(Reseeded 2026-09-04 off `rare_a2`. The reading it replaces, off
`mine_diverse_0903_c`, was `ranked_bands` 11.571 s → 0.0537 and `flat` 11.319 s →
0.0637 for `phoenix:classic`, and 2.255 s → 1.3789 / 0.897 s → 4.0194 for `phoenix`
— the same shape at a cheaper measured price, which is what a seed moving looks
like. `near_band` was `draw_cells_smoke`'s 1.470 s → 0.0778 and 0.383 s → 1.4923.)

**The `conditioned` band is no longer asked for a price**, and that is not a
convenience. It is the flat draw with its palette ask changed and nothing else, so
it draws under `flat`'s converted table. Asked for its own price it refused on every
leg — nothing has ever priced that band — and the arm then took the standing turn
weights while its own control ran a conversion, which is a control drawn from a
different partition mix than the arm it controls. `matched_mix_agrees` on the record
is what catches it.

Two readings worth carrying. **`phoenix` proper is not a dear partition** — its price
is inside the field on every band — so 15% of the clock *raises* it from 0.25 to
between 1.0 and 4.0; the quarter was starving a partition that costs what everything
else costs. And **`phoenix:classic` wants 0.034 to 0.078 depending only on the band**,
which is why one number a partition cannot express this ruling at all.

A band nothing has priced is not converted: `converted` raises `PriceMissing` rather
than inventing a price, `by_band` falls back to the standing turn weights, and the
record says which happened. Seeding reads `depth.json`'s `price` block, and where a
record predates the band split it is derived from that leg's own `sequence.jsonl`,
which carries `arm`, `partition` and `seconds` per row — so there is no cold start.
`hunt.recorded_prices` is **cached** (0.65 s a band, 3.35 s for the five, and
`depth.plan` asks for four of them); a guard that redirects the tree calls
`hunt.forget_recorded_prices()` first. **A guard that asserts a partition table has
to seat a price as well**, and none of them did until 2026-09-04: the seed is this
checkout's own `artifacts/` on a working machine and nothing at all on a clone, so
every plan test in `tests/test_depth.py` was asserting a table that depended on
whose box it ran on. `priced_bands` there pins one now, for the whole module.

Within a leg the price is an EMA at `hunt.EMA_ALPHA` = 0.1 over that leg's own served
candidates — a memory of about ten, short enough to catch the machine moving (`pc1` →
`pc20m` was 34% in six hours) and long enough to ignore one 280 s frame. Every leg
record reports the realized seconds share per partition and per band, so the next leg
never guesses.

**The override is merged over the table rather than replacing it**, so a leg says
what it is changing: a leg leaning toward the release mix cannot silently
re-inflate the pinned plane by not mentioning it, and a leg aimed at a phoenix
plane names one key. It reaches the plan and not only the declaration — the
record's `partition_weights` is the table the leg **ran**, and
`partition_weights_default` is what it inherited. Three things are deliberately
outside it: `hunt`'s conditioned leg (a work order already says which partitions
it means), the walk, harvest-production and proving legs' own `--partition`, and
the two other axes — `--band-weights` and `release_mix.json` — which multiply
with this rather than being overridden by it. `--centered only` is **not** an
exemption: it is a filter on the same breadth draw, so it draws under the table
like everything else, and a centered leg aimed at a dear partition uses the
override above.

Fractional weights only started acting on 2026-09-02. All three sites did the
arithmetic as `int(round(weight))`, which turns 0.25 into **zero turns** in the
ranked draw — the partition gone, which the rule forbids — and into **one turn**
at the interleave and in `hunt._turns`, which is no lean at all.
`draw_weights.turns_of` scales the table so its smallest positive weight buys one
turn, leaves an all-integer table exactly as it was, and `draw_weights.order`
lays the round out so every **prefix** leans too.

And a partition that drew nothing is now reported as a **zero** rather than being
absent from the record: `dtm_breadth2` ran `phoenix: 0` and its `depth.json` has
no phoenix key at all, so a partition a leg deliberately left out cannot be told
from one that did not exist when the leg ran.

⚠ **The ruling did not act for its first two days, and TWO things were stopping it.**
Both are fixed as of 2026-09-04; this is here because the shape of each is the shape
of the next one like it.

**One: the conversion was being thrown away.** `build_plan` resolved the standing
table into `partition_weights` and then handed **that** to [`draw_weights.by_band`]
as `overrides` — so `converted`'s last loop, the one that lets a leg aimed at a
phoenix plane keep its explicit turn weight, fired for all ten registered
partitions and wrote the turn weights back over each band's own conversion. The
record said so on every leg and nobody read it: `weight_conversion.<band>.converted`
`{}`, `overridden` naming every partition, `partition_weights_by_band` reading 0.25
for both planes. What it cost: `rare_a` spent **24.9% of its engine seconds on
`phoenix:classic` against a declared 3%** — 144 candidates at **35.75 s** each — and
**4.8% on `phoenix` against a declared 15%**. What reaches `by_band` now is what a
caller named and nothing else.

**Two: the round was laid out by TURN, so no draw ever saw the lean.**
`_weighted_order` built the round first-turn-of-every-cell, then second, and so on.
Every (partition, band) cell therefore got one place before any cell got two — and a
ranked draw of 265 places out of a 1,690-turn round never reaches the second pass.
Measured on `rare_a`'s own plan: `phoenix:classic` at **one turn against
mandelbrot's seventeen** still took 10 places of the first 265 against mandelbrot's
30. A 17:1 table drawing 3:1 is not a table. It is exactly the failure
[`draw_weights.order`] was written to prevent one axis up, and this section had
claimed for two days that every prefix leaned. It does now: each cell's k-th turn
sits at `(k + (band + 0.5)/bands) / turns` and the round is sorted on it. **The band
offset is load-bearing** — without it a one-turn cell sits at exactly 0.5, the
middle of the round, and all ten of a thin partition's band cells sit there
together, so a draw taking the first sixth of the round saw *none* of it.

**What the two together come to, `rare_a`'s settings, plan-only, no render:**

| band | | `phoenix` (15%) | `phoenix:classic` (3%) |
|---|---|--:|--:|
| `ranked_bands` | before | 2.5% | 22.2% |
| `ranked_bands` | after | **14.7%** | **5.3%** |
| `flat` | before | 0.8% | 15.7% |
| `flat` | after | 5.7% | **6.5%** |

Projected against the prices each band was converted at, which is the only
self-consistent way to read it — projecting one leg's weights against another
leg's prices is how you get a 41% that means nothing.

**`phoenix:classic` lands above its 3% and that is the design, ruled by Matt on the
day.** A partition's floor is **one place per draw**, not its share: `turns_of`
scales the table so the smallest positive weight buys one turn, and a weight is
never a gate. At 265 places and 25.4 s a candidate, one place is 5.3% — over the
declaration, and the declaration is what sizes the draw rather than what caps it.
The bar is that it is no longer a **third** of the leg. On the small `flat` arm one
place is 6.5% for the same reason and the same answer.

`phoenix` under-shoots on `flat` (5.7% against 15%) because that arm is 88 places
and stock and rounding bind before the weight does. A share is a share of a draw
big enough to express it.

**`--floor-untried` is the opened-but-shallow population.** The floor draw stands on
`proven_places` — a location already over `Q4_BAR` on `P(>=4)` — and this narrows that to
places holding **no recipe at all** in the named modes; unsaid, `depth.dear_modes()`,
the nine a dumped field cannot serve. The field there is known good and the whole
dear half of the roster has never been asked. Measured 2026-09-01: **19,504** opened
locations, **4,319** with any dear attempt, so **15,185** are untried and **15,169**
of those still resolve to a renderable row.

**`--cell` takes several cells and one place is aimed at exactly one.** The arm's
places are split round-robin over the cells in the order asked, so a leg sent at the
pool's thinnest colours serves them evenly and a truncation truncates them alike; a
place whose palettes came from two carrier tables could not answer *dominant in the
cell it was drawn for*, which is what the hit rate counts. `hit_rate` and
`dominant_and_clearing` return one block per cell, each read against the **whole**
flat control — the control is the same draw at every cell and splitting it would
price each cell's baseline off a fraction of it. A cell the carrier table cannot
serve out of the run's own map pool is **dropped at the plan and named** in
`shape.cells_unservable`, rather than left to `aimed_maps`' fallback: falling back to
a flat draw is right for one cell of many going thin mid-run and wrong as a plan,
because it would spend an aimed share on a second control and report it as a cell
that was served and bought nothing. On 2026-09-01 the table served **all 48** cells
out of the 822-map pool, so the drop has never fired in production — and it still
serves all 48 out of the 942-map pool, re-read 2026-09-12.

**A dear roster beside a field roster is what arm A is, and the warning above still
holds for prices.** "Do not put a composite on a roster beside field modes" is about
*pricing*: `plan_cycled_modes` cycles uniformly, so the dear modes take an equal
count and most of the seconds, and one `--rate` is then a mean over per-candidate
costs that differ by an order of magnitude. A leg that wants **breadth at a place**
— see it nine ways rather than three of thirteen — accepts exactly that, and pays
for it two ways: the mean rate is measured on the same mixture by the leg's own
pilot, and the arm gets its **own leg with its own wall budget** rather than a share
of a shared plan. That is the general answer to *a share of counts is not a share of
seconds*: run the arms as separate legs and the wall clock is the share.

### Retention discard is arithmetic, and no plan prints it

`curate retention` keeps [`candidate_ledger.RETAIN_PER_PAIR`] rows per (location,
mode), so what a leg loses at the merge is `(per_pair - K) / per_pair` at the
shipped keep K and nothing else. The same night, three shapes, measured when K
was 3:

| arm | width / modes | per pair | rows made | pruned | pictures |
|---|---|---|---|---|---|
| A | 22 / 11 | 2 | 17,694 | **0** | 0 |
| B | 4 / 6 (floor width) | 4 | 11,313 | 2,822 (25%) | 0.36 GiB |
| C | 40 / 5 | 8 | 45,675 | 28,526 (62.5%) | 4.21 GiB |
| D | 40 / 5 | 8 | 13,340 | 8,324 (62.4%) | 1.25 GiB |

Exact every time. **Breadth over modes is prune-free and depth in palettes is not** —
which is not an argument against width, because the discarded rows are the ones a
wider draw beat, and the clear rate they measured survives in `sequence.jsonl`. It is
an argument for knowing the number first: **a width at or under the keep is free
and every row above it is discarded**, so what `--floor-width` is compared against
is [`candidate_ledger.RETAIN_PER_PAIR`] and never a literal.

**This line has already inverted once, which is why it is written against K.** It
read "`--floor-width 4` is one over the keep and costs a quarter of an arm's
pictures for nothing" — true at K=3, and at K=5 that width is *under* the keep and
prune-free, so the advice as it stood would have cost an arm the quarter it was
warning about. The table's arms re-priced at the shipped keep: A and B are free,
and C and D's 8 a pair cost `(8-5)/8` — **37.5%** rather than the 62.5% they paid.

**The arithmetic holds only where the pairs are fresh, and on the near band they are
not.** A near-band pass deepens (location, mode) pairs that are *already* at
`RETAIN_PER_PAIR`, so every row it makes competes against a full keep of ranked incumbents
rather than against its own siblings, and the loss is a fact about the incumbents
instead of a function of `per_pair`. Measured 2026-09-03 on `draw_cells_smoke`: of the
4,525 rows the leg and its pilot made, **440 survived the merge — 9.7%** — and the
ledger went 194,037 -> 198,241 -> **194,114**, net +77 for ten minutes of leg. So a
near-band leg is a poor instrument for moving a thin cell's *stock*, whatever its
palettes are aimed at; what it moves is pool quality, because the prune drops the
weakest and keeps the leg's best.

**Which pairs are fresh is a subtraction, and that is the cheap half nobody
spends.** `retention.decide` keeps `min(K, attempts)`, so a pair holding fewer
than the keep has never had more — free slots are `K - len(pair)` over the rows
already in hand, never a scan. **`retention.free_slots` is the one spelling**, and
`curate candidate-ledger free-slots --out FILE` is the census over it, which is the
arithmetic the inverted manifest two sections below did without. A **near-band**
manifest wants `curate depth near-places` instead: free slots at the *incumbent's*
pair, intersected with the band and with the admitted population.

At the keep of 3 that was: 43,255 of 114,744 pairs, 37.7%, for 60,316 free slots.
**At the keep of 5 it is 114,709 pairs — 100.0% — for 289,210 free slots over
26,442 places**, both read 2026-09-06 over an unmoved store. The number is per
*pair* and not per row. ⚠ And the flip cost the *unexplored* reading on most of
them: 70,930 pairs sit at exactly 3 and may have been pruned there at the old
keep, so only the 43,255 under three are pairs nobody has finished looking at.
[`README.md`](README.md)'s *The growth law* carries the full statement and the
three ways the phrasing goes wrong.

**Pricing a change to the keep is a different question, and only one population
in the tree can answer it.** A K sweep needs the attempts a pair *lost*, ranked,
and the prune keeps no record of what it dropped. What does is `sequence.jsonl`:
**94 `depth` legs at 670,487 rows and one `remode` leg (`smooth_twins`) at 3,602
— 674,089 attempts**, measured 2026-09-06. It alone carries `rank` and
`rank_fraction`, which is what lets a pair be re-ranked at another K without a
rescore.

⚠ **`mine` is not as empty as it looks and the distinction is the field list, not
the file.** Four `mine` legs keep a `profile.jsonl` of **7,260 rows** carrying
`k`, `p_ge4` and `seconds` — enough to re-price K, and `README.md` already names
the `sequence.jsonl` / `profile.jsonl` pair together. What those rows lack is
`rank` and `rank_fraction`. `hunt` and the backfilled `runs` rows really do keep
no attempt log: `runs`' `candidates.jsonl` has an `attempt` index and **no `k`**,
so it cannot say how deep a pair went, and `reframe_draw`'s `attempts.jsonl` is
the same shape. The honest total, if the claim is *any* usable attempt log, is
**681,349 rows over 99 legs**.

### A scratch driver that drives a render pool needs a `__main__` guard

Windows spawns worker processes by re-importing the entry module, so a driver with
top-level code that reaches `depth.run` re-enters itself in every worker and the pool
dies with `BrokenProcessPool` **after** the population read and the plan — a minute or
two in, with nothing rendered. `curate depth` is safe because `cli/__main__.py` has the
guard and no module in `cli/` runs anything at import; anything under `scratch/` needs
its own.

**It is every entry to a spawning pool, not just `depth.run`, and the other failure
mode is worse than a `BrokenProcessPool`.** `solve.render_seats` — reusable for an
ad-hoc sheet, since `where=` redirects the output and any dict with a `seated` list
of keyed rows will do — reaches `release.run_pass`, which is also a spawning
executor. A guardless driver there does not die: each worker re-runs the whole leg,
which spawns three more workers, and the leg **recursively spawns** while writing
real pictures the whole time. What it looks like is a render that appears to be
working, several dozen idle `python.exe` and a `[solve] N seat(s) to render` line
printed once per generation. Kill the tree rather than waiting for it, and throw the
pictures away — a partially written PNG can still answer `_already` with the right
resolution, so a re-run would carry the corrupt ones across.

### The contact sheet a leg reads its own pile on is tracked, since 2026-09-08

**`curation.sheet.score_sheet` — do not copy a sheet script into `scratch/` again.**
Every leg since 2026-09-07 has rebuilt the same page by hand: rows sorted on the
gallery-grade head's `p_fine(>=4)` descending, cut at 0.90 / 0.75 / 0.50 / 0.25 /
0.10 with a sticky separator saying how many sit in the band and how many are above
the line, one data-URI tile a row so the page works over `file://`. The builder it
was copied from lived only in `scratch/`, which is gitignored, so each copy started
from whatever the previous report had quoted.

**The row shape is the caller's.** A ledger row and a gallery seat row carry the
score, the picture and the caption under different names — which is exactly why the
old builder could not be reused across legs — so `score_sheet` takes `score`,
`picture` and `lines` as callables over whatever the caller holds. A caption line is
plain text, or `(style, text)` with the style one of `sheet.LINE_STYLES`; the sheet
escapes every one of them, so a caller never hands this module markup. `by_score`,
`banded` and `tile` are the three pieces on their own, for a page that wants its own
frame around them.

A row the head has no reading for sorts to the tail and bands with the bottom rather
than being dropped: a missing score is a **coverage reading**, and it is drawn as an
em dash where a number would be. An empty band is left out, so the page reads as a
distribution rather than as a form.

### What an arm can and cannot be credited with

**The record credits its arms; the ledger does not.** `depth.json` carries the
census the plan was taken against (`plan.seats_short_today`), every arm's realized
candidates, locations, partitions and modes, and per arm its seconds,
seconds-per-candidate and cumulative primed locations at both bars — enough to price
one arm against another *inside* one run. Two axes it does not cross: `by_mode`
pools the arms and `curves[arm]` pools the modes, so a leg whose floor arm ran a
different roster cannot say what that roster cost there; and `curves` reads the flat
`P(>=4)` bars rather than each mode's own `headroom.bars` rule, which under-reports
any mode on the `P(>=3)` fallback. Both are recoverable from `sequence.jsonl`, whose
rows carry `arm`, `mode`, `seconds` and both probabilities together.

**A merge writes down what it did, and until 2026-09-15 three of the four legs did
not.** `hunt`, `mine` and `depth` each built a report off `candidate_ledger.merge`
— the manifests, the repeat draws, the prune — and returned it to a caller that
printed it, while `rotation`, `repetition` and `label_migration` all wrote a
`merge.json` beside their leg. So a night's displacement lived in a terminal and
died with it. `hunt.merge_report` is the one writer all four reach now; it takes
the leg's **rows file** rather than its name, so no module spells *where this leg
lives* a second time, and it names the file on the report.

**And the prune writes down WHICH rows it took, not only how many.**
`ratchet.jsonl` is tracked, keeps counts, and is what lets a census assert the
store only shrinks for reasons somebody wrote down — it cannot say which picture
went. So the 1,443 incumbents one night's merge displaced were unrecoverable in
principle: row gone, picture unlinked, no file naming either.
`sweep.write_displaced` writes the key, the place, the mode, the settings and the
picture path of every dropped row to
`artifacts/curation/candidate_ledger/displaced/<stamp>.jsonl`, inside the
transaction and after the three files are renamed, which is
`_record_the_ratchet`'s order and its reason. Untracked and beside the store: it is
hundreds of kilobytes a prune and it is forensics rather than a claim the history
has to carry. The recipe key is the ID a `re-render` keys on, so a displaced row is
buyable back.

**And five more columns, because buyable back is not the same as legible.**
`cells`, `families`, `p_ge3`, `p_ge4` and `rank_value` ride beside the six above
since 2026-09-15. The first four are copied off the row and the sidecar; the fifth
is what `_prune_ranks` actually ranked on, which is a fitted function of the two
probabilities and two more columns and is therefore **neither of them** — a file
carrying the probabilities alone could not say why the rule ordered a pair the way
it did. `families` is stored rather than derived because family dominance is not
the union of its cells': `palettes.dominance` cuts a family at `FAMILY_LEAD` /
`FAMILY_ALONE` against a *summed* mass and drops the shares, so a picture can be
dominant in a family no cell of which leads, and no reader can recover the one
column from the other.

**A `null` in one of the four numbers is a fact about the row, not a gap in the
file.** `scores_by_recipe` omits a recipe with no reading on the live judge rather
than rescaling an old one, and `retention.decide` ranks a valueless row last within
its pair — so an unread row is exactly the row a prune takes *first*, and this file
is densest in precisely the rows whose columns are null. `values` and `readings`
are required positionals on the writer for the matching reason: a caller that
forgot one would produce a file that looks complete and reads as a store with no
judge rather than as a writer with no arguments.

⚠ **The first such file on this machine is the one written on 2026-09-15**, because
the writer landed at 15:46Z and the two prunes before it ran at 10:49Z and 13:52Z.
There is nothing earlier to compare a night against, and a displacement question
asked of any merge before that date has no file to read.

### And a second file, for the rows the rank let go and the rule kept

`retention.FAMILY_ALLOWANCE` keeps up to one row a pair that is
best-in-a-colour-family the kept five miss, so since 2026-09-15 a prune decides in
two directions and `sweep.write_kept_for_a_family` records the other one:
`artifacts/curation/candidate_ledger/family_allowance/<stamp>.jsonl`, written
beside the displacement list, in the same transaction and to the same shape.

**`for_family` is the column that cannot be recomputed.** It is the family this row
earned its place with — the ones it is dominant in that *none of the pair's ranked
five* were — and it is measured against those five as they stood at that minute.
The next prune replaces them, so a reader asking later which colours the rule
bought has this file or has nothing. The rest of the row is the displacement list's
columns, which is deliberate: one prune's decision reads across the pair of files
and a reader who knows one knows the other.

**A row a protection was holding anyway is not in the file.** The allowance looks
below the top keep, and below the top keep is exactly where a protected row sits —
the rank let it go and a seat, a verdict or a fit kept it. So the rule *reaches*
rows it did not buy, a whole store of them on the first prune after it lands, and
a file that wrote those down would answer its own question with noise. They are
subtracted, `reached_a_protected_row` counts them on the record, and `rows` is
what the store owes to the rule — the number the **+14,933-row, 3.32 GiB** ceiling
is about.

**That is also why `kept_because` counts this reason LAST**, after the five
protections rather than beside the rank: counted first it would take a bite out of
every protection's count the moment the rule landed, and this project reads those
counts across months. Counted last, the file's length and
`kept_because[best_in_a_family_the_ranked_five_miss]` are one number.

⚠ **An empty reading is the normal one and is not a fault.** The allowance can only
keep a row *below* the top keep, so it binds at a full pair and a prune over a
store already at the keep rescues nothing — `{}` on the record and no file written.
A leg landing at never-opened places, where every pair is new and has room, is
expected to rescue **zero**, and that is the rule being forward-only rather than
the rule failing to fire.

**Past the merge the arm is gone.** `candidate_ledger.hunt_block` keeps two fields
of nine — `seconds` and `k` — so a merged row names its *run*
(`provenance.run`) and its index (`provenance.candidate`, which joins to
`sequence.at`) and never its draw. So crediting a seated picture back to the arm
that bought it is a join through a file under `artifacts/`, which is gitignored:
`data/curation/runs.jsonl` tracks six **release** runs and no mining leg at all, and
`cc_hour` has already lost its `depth.json` while keeping its rows. This is not the
same axis as the seating's own `leg` field, which says whether `solve` placed a seat
through `mode_floor` or `general_pool` — that is which door a finished candidate
walked through, not which budget paid for it.

**One past allocation is fully replayable and it is `dc2` (2026-08-27).** It is the
only leg on record whose floor roster came from the census rather than from
`--floor-modes`: 2,991 candidates over 9 modes at 56 proven places, 2,069 engine
seconds, buying **14 mode-seats** — 148 engine seconds a seat. Four of the nine were
composites or direct traps. `route_to`'s `hours` on any record is **engine** hours
while `--budget` is wall seconds, so divide by the leg's own `budget.concurrency`
before reading it as a clock.

### Three workers, cut at the location

`curate depth run --workers N`, **three** by default off `release.DEFAULT_WORKERS`.
It was single-engine until 2026-08-28, so an hour of mining spent one of the three
the locked rule allows.

**The unit of work is a LOCATION and that is the whole design.** A field is dumped
once per (location, mode) and every palette at that pair is a recolour of it — 56%
of a candidate at width 40 — so a plan cut per *candidate* hands one place to three
workers and each dumps the same field. That is not a smaller win, it is a **loss**:
the parallel leg would come out slower than the serial one. `blocks_of` cuts the
woven plan into one block a location, in the order each location first appears in
the weave, so the arm proportions the weave exists to hold survive one location
coarser.

**`--budget` is wall seconds and `--rate` is per engine.** Matt's ruling, and the
two only work read together: the plan is sized `PLAN_HEADROOM * workers * budget /
rate`, and sizing off one engine on a three-worker leg plans a third of the hour
and stops having run out of *plan*. The clock starts at the **first block**, not
at the call — the population read is a ledger sweep and a scan index, about 50 s
on this store, and charging it to a render budget made a 25 s pilot render nothing
at all. The record carries `render_wall` (what the budget governs), `wall_seconds`
(the whole call), `engine_seconds`, and `seconds_per_candidate`, which is **per
engine** and is the number a later `--rate` is read off.

**A worker hands back a dict, not [`mine.make`]'s result, and the two are two
lists.** `_render_block` runs in a `ProcessPoolExecutor` and spells the keys it
pickles; the parent's `take` writes the row off those. A key added to `mine.make`
and to `take` alone is not a missing field — it is a `KeyError` on the first
candidate that lands, after the plan, the population read and the first block have
all been paid, so the leg renders for minutes and writes **no row at all**. That
is what `texture_flat` did on 2026-08-31: it reached `take` three times at
`7ea2f44` and the worker's dict not at all, and every depth leg was dead for eight
hours with pictures on disk and an empty `rows.jsonl` as the only symptom.
`test_the_parent_reads_no_key_the_worker_does_not_spell` reads both sides off the
AST and holds them to each other.

**Workers render, the parent writes**, [`curation.release`]'s rule for its reason:
an append-only log with three writers has no order and `sequence.jsonl` is read
back as an ordered stream. Every row, score and sequence line is written by the
parent from `pool.map`'s plan order, so a three-worker leg writes the three files
a serial leg would have, in the same order, whatever order the workers finished in.

**Measured 2026-08-28**, one plan of 2,416 candidates at seed 20260901, `--width
24 --near-width 40 --top-bands 5` on `{gaussian_int, curvature}`, 180 wall seconds
each arm. The serial arm is given `rate/3` so `workers * budget / rate` lands on
the same plan and the two schedulers walk the same draws:

| arm | engine threads | made | candidates a wall second | against serial | s a candidate, per engine |
|---|---|---|---|---|---|
| 1 worker | default | 649 | 3.60 | 1.00x | 0.270 |
| 3 workers | default | 1,076 | 5.93 | 1.65x | 0.496 |
| 3 workers | **7** | **1,254** | **6.92** | **1.92x** | 0.424 |
| 3 workers | 4 | 1,219 | 6.62 | 1.84x | 0.442 |

**They do not saturate, and the record's `concurrency` figure says they do.** That
column is engine seconds over wall and reads 2.94x on the same leg that is really
1.92x faster: an engine sharing the machine costs 1.57x more per candidate, and
that inflation is counted as work. Candidates a wall second against a serial arm is
the only number here that means anything, and the record says so in
`concurrency_is`. The gap is contention and not starvation — this plan had 86
location blocks for 3 workers. `release.ENGINE_THREADS_PER_WORKER` (7) is worth
2.7 points of throughput over letting three engines each take the whole machine,
and it was **measured** here rather than assumed: 4 threads is worse than 7.

**Three is the number and `release.DEFAULT_WORKERS` is where it is written.** Every
leg that drives the engine takes its default from that one constant — a measure
pass, a sheet build, a hunt, a mine — and the count is the only part of the pool
shape a caller chooses, the below-normal priority coming from
[`process_control.child_priority_flags`] whatever the caller does. A prompt that
plans a leg around "two engines buy about 2x and it has never carried more" is
planning against a number this repository does not hold; the table above is the
one it does.

**And two more legs have now read `concurrency` as if it were the speedup, which
is the mistake the paragraph above exists to stop.** The ckpt-112 mine's two arms
ran at three workers on 2026-09-06 and reported **2.978x and 2.962x** — 18,201
engine seconds over 6,112 wall, and 14,318 over 4,833. Those are the inflated
column again, landing within a hundredth of the 2.94x measured here, and they are
**not** a throughput reading: nothing in that leg ran a serial arm, so nothing in
it measured a speedup at all. The 1.92x above is still the only figure this
project has for what a third worker buys, and it is from 2026-08-28.

**Starvation is a real case on the narrow legs.** `workers_for` runs the leg on
`min(workers, blocks)` and says so: the near-band pool held **25 locations** for
the two-mode field roster and **19** for the four direct traps, and a worker with
no place to take is a process spawned to idle.

**A 150 s pilot over-reads the rate, and by a knowable amount.** Budget seconds are
`stages.total()` and exclude the fixed start — the population read, the judge load and
the plan build, about 50 s — so a short run's *wall* carries it and a long run's does
not: `mine1h`'s two pilots measured wall/spent at **1.28** where the legs they sized
came in at **1.03 and 1.02**. Read the pilot's `spent / made` and never its wall.
Against those pilots the field leg realized **0.278 s** against 0.379 planned (27%
under, because the pilot's near band ran at width 24 and the leg's at 127, so the dump
amortised five times better) and the composite leg **0.743** against 0.653 (14% over).
Both spent over 99% of their budget, so the plan headroom absorbed the miss in both
directions.

**`--near-width` is the only way to spend a share on the near band, because the pool
is tiny.** `near_places` draws from the locations whose best candidate *in this run's
roster* sits in `[0.50, 0.90)`, and a narrow roster leaves very few: **25 places** for
`{gaussian_int, curvature}` and **19** for the four `direct_trap_*` modes, against
2,974 and 1,904 places that hold the roster at all. A share sized in candidates and
divided by `--width 24` asks for more places than exist, the draw comes back short and
the budget goes unspent. Size it the other way — `near_width ≈ share × budget / rate ×
PLAN_HEADROOM / places` — which is where `mine1h`'s 127 and 136 came from.

The composite leg is only 1.4× the field leg a *candidate* — the gap is nothing like
the 175 s a location the forty-wide figure above implies, because that figure is a
composite at forty and this is a composite at twelve. **Budget seconds are wall
seconds**: `spent` accumulates `stages.total()` and both legs measured wall/spent at
1.01–1.09, so a run sized to a deadline can subtract straight.

**The conditioned colour ask, ported from the hunt.** `mine.plan_breadth`
stratified its palette ask over all 48 cells through `hunt.Stratifier`; depth
replaced that with a flat `random.sample` over the pool and the ask was dropped
in the move without anything recording it. It is back as a fifth draw,
`conditioned`, on a share of zero unless a run asks for one:

```
fractal-wallpapers curate depth run --name d2 --rate 0.35 --budget 5400   --cell dark_vivid_green   --shares '{"near_band": 0.2, "ranked_bands": 0.25, "flat": 0.275, "conditioned": 0.275}'
```

The arm is the **flat draw with one thing changed**. Same pools, same
`flat_places` draw, same roster, same width — only the palette ask differs:
`aimed_maps` sends it through `hunt.conditioned_maps` and so through the carrier
table's mean-share weighting, where `flat_maps` samples the pool uniformly. That
is what makes the flat arm the *control*: `record.hit_rate` reads both arms' rate
of coming out dominant in the cell and reports the `lift` between them. A share
with no `--cell`, a `--cell` with no share, and a misspelt cell are all refused
at the plan rather than reported afterwards as a draw that bought nothing.

**The two arms do not share a seed, and `plan.seeds` is where the four numbers
are.** They cannot: the arms are drawn *disjoint*, so the place draws are offset
(`seed + 1` for flat, `seed + 2` for conditioned) and the conditioned arm's
palette cycle runs at `seed + 2` against the flat arm's `seed`. Everything a
comparison needs held fixed is held fixed and the seeds are not one of those
things — but a measurement nobody can re-take is an anecdote, so every draw's
place seed and candidate seed are on the record.

**`--top-bands N` stands both matched arms in the strongest N rank bands.** The
head's rank spreads the prime rate end to end, so an arm and a control drawn
over the whole axis are comparing two colour asks *and* two accidental rank
mixes. The cut is by band and not by rank, so it lands on the same boundary in
every partition however differently they are stocked: at the default ten bands,
`--top-bands 5` is each partition's own top half. **It never cuts the ranked
draw** — measuring the curve end to end is that draw's whole job.

**So `--top-bands` is not how a production run aims at the top of the rank.** A leg
told to draw from the strongest half of the head's rank and given `--top-bands 5`
gets a ranked draw over the *whole* axis, because that flag reaches only the matched
arms. `--band-weights` with the lower bands at `0` is what does it —
`_weighted_order` drops a zero-weight cell from the round entirely — so the top half
at the default ten bands is `'{"band05":0,"band06":0,"band07":0,"band08":0,"band09":0}'`.
`sparse_mode_harvest` (2026-08-29) wanted the top half and used that. A leg that
wants the **whole** of itself in the top half passes both: `--band-weights` for
the ranked draw and `--top-bands` for the two matched ones.

**Measured at `dark_vivid_lime` on 2026-08-31, and the two grades disagree.** 520
candidates against a matched 514-row flat control: **44.8% came out dominant in the
cell against the control's 0.78%** — a 57.6x lift, 22 of 24 carrier maps hitting, so
the draw does what it is for. At `P(>=4) >= 0.50` **not one of the 520 cleared**, and
read there the arm is a share that bought nothing. At `P(>=3) >= 0.50` **63 of the
233 dominant rows cross** — 27.0% of them, over 11 of the arm's 13 places, at 5.8 s a
crossing and **33.0 s a distinct location**, which is cheaper per location than the
same leg's unconditioned breadth arm managed at q4 (76.2 s). At the ACTING strange
bar of `P(>=3) >= 0.77` it is 33 rows over 8 places, 45.4 s a place. The top of that
ordering reads `P(>=3) 0.9989 / P(>=4) 0.0014`: the judge is confident these are
three-grade pictures and confident they are not fours. **So price a conditioned arm
at the grade it is bought for.** A themed leg aimed at a q3-graded collection is
live; the same rows aimed at a `P(>=4)` seating are not, and a leg reported only at
q4 will be written off for the wrong reason.

**The `conditioned` share gates the arm and does not size it.** `build_plan`
computes one `scale` — `shares[FLAT] / shares[RANKED]` — and applies it to the
ranked draw's realized per-partition counts for **both** matched arms, so
`aimed_want` is `flat_want` and the conditioned arm comes out exactly the size of
its control however large its own share is written. That share is read twice and
only twice: a non-zero one with no `--cell` is refused, and a `--cell` with a zero
one is refused. It also sizes the arm in the one case there is no ranked draw to
inherit a mix from. Anything else written there is a number with no effect.

**The matched arms cap on the thin partitions; the ranked draw does not.**
`flat_places` asks every partition for the same count — `round(ranked_in_partition
× scale)`, and the ranked draw is round-robin, so that count is near-uniform —
while the never-opened stock is **6:1** unequal across the nine partitions (2,071
places in `julia:mandelbrot` against 339 in `multibrot4`, top half, 2026-08-29).
The thin partitions run out, the fat ones keep stock nobody asked for, and both
matched arms come back short. `banded_places` is the only draw here that drains a
bounded pool gracefully, because it round-robins over (partition, band) cells and
keeps taking from whichever still hold something. **So a leg that has to consume a
bounded location pool gives the ranked draw the bulk of the share**: at
`0.5 / 0.25 / 0.25` the three arms planned 7,007 / 2,079 / 624 places and between
them took all 9,710.

★ **That pool is SPENT — zero in all ten partitions since 2026-09-15 — so breadth
is retired as an arm rather than shrunk.** `on125_wide1` and `on125_wide2` took the
drawable remainder and `con125_phoenix_stripe` took the last 177
`phoenix:classic` places behind them; re-read the same evening over a 459,548-row
ledger, `hunt.drawable` returns **every partition empty**, 40,454 admitted locations
against 42,113 opened. The arithmetic above is what a breadth leg used to be sized
by and is kept for the shape, not for a number to reach for. **A document still
describing never-opened stock as a lever is wrong rather than stale**, and the only
thing that refills this pool is `fractal-wallpapers walk`.

**READ IT anyway before planning any leg that draws off it, never carry a figure
in** — one call, `mine.population()["pools"]`, and a leg's own record carries it at
`route.unopened_stock`. That rule is why this reached zero on a measurement and not
on a surprise. What scales instead is the floor draw over proven places, which
[`MEASUREMENTS.md`](MEASUREMENTS.md)'s `easy125_wide` and `easy125_recolour` rows
price against each other, and a composite pointed at proven ground — *A composite is
worth pointing at proven ground* below.

### A recolour manifest saturates inside one night, and the second pass buys displacement

`on125_recolour1` and `on125_recolour2` are the same arm over the same
`--floor-places` manifest, back to back on 2026-09-15 with a merge between them.
The clear rate barely moved — 13.4% / 12.1% then 11.1% / 10.5% at `Q4_BAR` —
and **retention collapsed**: the first pass kept **42.6%** of its own rows, the
second **27.7%**, and the second moved the ledger by **+27 rows net against 9,995
made**. Every pair the first pass could fill was full when the second arrived, and
a sixth palette at a pair holding `RETAIN_PER_PAIR` is ranked out as it lands.

**That is not a wasted leg and it is not a second helping of the first one.** What
a saturated pass buys is *displacement* — a better row taking an incumbent's slot
— which is quality and shows up in a median rather than in a count. But it buys it
at the arm's full price, so **plan one pass over a manifest a night**, and spend a
second pass's clock on a population something has not already swept.

### The collapse is BETWEEN legs and not within one, and a rebuilt manifest undoes it

`fss125_recolour`, 2026-09-15, is the control the two above could not be: the same
arm at the same rate — **1.0141 s a candidate against `recolour2`'s 1.0097, 0.4%
apart** — over a manifest rebuilt that hour instead of reused. It kept **40.2%** of
its own rows (4,254 of 10,590) against `recolour1`'s 42.6% and `recolour2`'s 27.7%,
and moved the ledger **+1,941 net against `recolour2`'s +27**, on 6% more
candidates. **Rebuilding the manifest recovered essentially all of the lost
retention.**

**And retention does not decay inside a leg at all.** Kept share by decile of the
leg's own draw order, read off the displacement list's `run` and `candidate`:
`.395 .411 .368 .382 .415 .410 .414 .426 .376 .420` — flat, no trend, a 0.058
spread with the last decile above the first. So a recolour leg does **not** want
sizing differently and there is nothing to taper; what wants doing between legs is
**rebuilding the manifest**, which costs one pool load. The 42.6% -> 27.7% fall was
the population going stale under a reused shelf and nothing else.

**Order the manifest free-slot-first.** 5,754 proven places on the night, 2,817
carrying a free `(place, mode)` slot in the arm's two modes and 2,937 that can only
displace; the leg is clock-bound rather than manifest-bound — it reached 2,276 of
the 5,754 — so which half it meets first is the whole of what the ordering decides.
`curate candidate-ledger free-slots --out` is the census, and the two halves
concatenated are the file.

⚠ **A saturated manifest reads as a full pool, not as an empty one.** The tell is
not the clear rate — `recolour2` held 11.1%/10.5% — it is retention, and retention
is invisible until the merge. Rebuild rather than diagnose.

### A composite is worth pointing at proven ground, by about 5x

`on125_threads` drew `threads` at places a shareable mode had already proven
(`--floor-places` over the proven set, `--floor-untried threads`) and took **328
clearing places out of ~838 tried, 39%** — against the **8.2%** of `threads`
places in the standing ledger that carry an above-bar row. The standing figure is
over stock drawn blind; the prior is worth about **5x**. Per clear the leg is the
dearest productive arm here (21.0 engine s against the floor draw's 7.0), but per
*place* it is the cheapest after the floor draw — one clearing place every 7.7
candidates against breadth's one every 18.9 — and a collection is bounded by
places. **On any mode too dear for breadth, spend the draw on proven places
untried in it rather than on fresh ones.**

**On a breadth leg the never-opened pool caps the plan, not the clock.**
2026-08-29: 28,420 admitted locations, 8,714 of them already opened, **19,415
never opened**, and the top half of the head's rank inside each partition is
**9,710** of those. One field mode on three workers costs about `0.55 + 0.29 × k`
seconds a location, so at `k = 4` that whole top half is spent in **2h11m** and at
`k = 12` in 3h44m. `k` on such a leg is therefore not chosen for its own sake — it
is set by the pool and the deadline together — and a pilot that **over**-prices
the leg costs **wall clock** rather than candidates, which is the inverse of the
usual failure and happens for the same reason: the plan is bounded by places
rather than by the rate.

**A run that is only the arm and its control needs no ranked draw.** Both breadth
arms used to be sized off the ranked draw's *realized* partition counts, which
are empty when it has no share — so `--shares '{"flat": 0.5, "conditioned":
0.5}'` planned nothing at all and reported two arms that bought no candidates.
`spread_over_partitions` sizes them round-robin off their own shares instead
where there is no ranked draw to inherit a mix from, and `plan.matched_mix_agrees`
says on the record that the arm and its control asked for the same one.

**`merge` upserts, and the incoming row wins.** `candidate_ledger.write` keys on
the recipe, so a recipe some earlier leg already made is *re-attributed* to the
run being merged — its `provenance.run`, its `hunt` block and its `drawn_for` all
become this run's. `records._carry` holds back exactly one field, a human
`rejected` verdict, because that was never one of the row's inputs. Read
`merge`'s `new` against `merged` to see how much of a run was collision: a run
planned on never-opened locations can still collide, because the pool it was
planned against is the pool at *plan* time and other legs merge in between.

**Merging an arm changes the never-opened pool as well as the ledger.**
`hunt.opened_locations` calls a place open the moment it carries one recipe, so
every location an arm touched leaves the pool a later *unconditioned* breadth
draw is taken from — and which locations the arm touched was decided in part by
a colour ask. That is a selection effect on the population and not on a rate, so
no `drawn_for` filter reaches it; it is the reason a conditioned arm is merged on
a ruling rather than by default.

**`record.dominant_and_clearing` is the readout the arm exists for, and it
reports the factors before it multiplies them.** The census's marginal cost for a
cell (`940 s` for `light_vivid_teal`) is *unconditioned* and decomposes into
three independent things: renders per place explored (17.2), places per place
yielding any clearing candidate (3.47), and clearing places per clearing place
dominant in the cell (40.8). Conditioning the palette ask attacks the third
factor alone. The risk it carries is in the second — whether the maps that carry
a colour make *worse pictures* — so the clear rate is reported per arm against
the ledger-wide base rate (`headroom.bars`' per-mode rule, 7.0% of all 85,078
candidates) before the composed renders-per-(dominant ∧ clearing) price. Every
count in that block is **raw**: one read of one candidate against its own mode's
bar, never a maximum over `k`, so none of it needs a prime count's k-dependent
multiplier.

**The arm rates are a property of the roster, not constants.** `teal_conditioned`'s
4.70% flat against 1.41% conditioned is the figure everything since has been sized
off, and it was measured on a six-mode field roster whose bulk is `smooth` and
`exp_smoothing`. Aimed at weak modes the same three arms come apart. `mine1h`, both
legs at `--cell dark_vivid_lime`:

| leg | near band | flat | conditioned |
|---|---|---|---|
| 2 field modes | 460/2,687 = **17.1%** | 12/1,343 = **0.89%** | 32/1,343 = **2.38%** |
| 4 direct traps | 957/1,409 = **67.9%** | 35/705 = **4.96%** | 13/705 = **1.84%** |

The composite leg reproduced the reference points to within a fifth of a point; the
field leg **inverted** them, its conditioned arm clearing 2.7× its own control. So the
0.301 lift is not a fact about conditioning — on a roster whose modes are weak
everywhere, breadth is what buys nothing and the carriers happen to be maps those
modes survive. And the near band beats both by an order of magnitude on every roster
tried, which is a statement about where clearing candidates are and not about
palettes: on a mode that runs on the `p_ge3` fallback, a place chosen for holding a
candidate at `P(>=4) >= 0.50` clears that fallback with almost any map. Read the near
band's rate as "this place was already good", never as a yield a fresh place would
repeat.

**Draw-biased, verdict-measured, and it does not gate on the table.** The carrier
table is a prior about a map and never a claim about a picture — group members
disagree on their dominant cell in 120 of 195 reads, and `PRGn` once made a green
seat as a non-carrier. So the table decides only which maps are *offered*; the
candidate is rendered, its dominance is read off its own pixels like every other
candidate's, and what came out dominant is what counts. A 60% hit rate costs
1.6x the renders on that arm and nothing anywhere else — every candidate is a
candidate whatever colour it turned out to be. The shot carries `drawn_for` on
its ledger row so a reader can tell an aimed candidate from a lucky one.

**`BREADTH_DEMOTED` is empty, and it is a per-run knob rather than a standing.**
It takes a mode out of the ranked and flat draws and leaves it eligible as a
near-band incumbent, which is the one thing a `mode_policy` weight cannot say.
`tia` was the whole of it — it cleared `Q4_BAR` on `P(>=4)` at .0208 in breadth at
k=20 against `smooth`'s .0515, level with them only by k=40 (`dc1`/`dc2`,
2026-08-27), and it is the dearest dump of that three-mode roster at 0.898 s
against `smooth`'s 0.354. `mode_policy` supersedes that: `tia` is weight 2 on 31
fours in 310 labeled rows, and a standing that keeps a promoted mode out of the
draw which would buy more of it confirms itself. Set `--breadth-demoted` per run
for a mode that pays at depth and not at width. Note that `--modes` is the wrong
instrument here — it is the roster a near-band incumbent must also be in, so
narrowing it drops the mode from both draws.

**The rank bands are equal counts, not equal scores.** `ranked_bands` sorts each
partition's never-opened pool on the location head's `P(>=3)` **within** that
partition and cuts it into `--bands` equal-sized bands; `banded_places` then draws
round-robin over every (partition, band) cell. That even spread is the point — a
draw proportional to stock would put nine tenths of itself in the fat bands and
leave the ends, which are the question, with two locations each. Every row that
comes back carries its `rank` and its `rank_fraction`, because a rank is not
comparable across partitions of different sizes and a fraction is.

**The near band reads the best FIELD candidate, not the best one.** A place whose
best candidate is a composite has no field to dump, so `best_field_by_location`
takes the best candidate in a mode this run can afford and the band is read off
that. It is a selection this run makes and not a fact about the place.

**The modes are cycled inside a location and never blocked.** Seven of one mode
and then seven of another would move a location's own clear rate with `k` for a
reason that is not depth. Cycling makes the k-th candidate a draw from the same
mixture at every k, which is the only shape in which "is the clear rate flat in
k" is a question about palettes.

**The dump amortises over the mode and not over the width.** One field a
(location, mode): a near-band location holding its mode pays `dump/40`, a breadth
location cycling six modes pays `dump/6.7`. That is most of the difference
between the two arms' per-candidate cost, and it is a reason to hold the mode
wherever the question allows it.

**Where the two arms' clocks stand now.** `dc1` measured `measure` at 33.5% of
the whole run and 53.4% of a near-band candidate, which made the autolevel
operator's Python half the ceiling. Re-priced over 640 real candidates at the
candidate regime, eight places an arm, after that half was rewritten:

| arm | per candidate | dump | paint | measure | repaint |
|---|---|---|---|---|---|
| near-band, one mode over 40 | 168 → **129 ms** | 6.7% | 31.9% | 58.3% → **41.4%** | 20.0% |
| breadth, six modes over 40 | 305 → **257 ms** | 61.8% | 15.1% | 29.5% → **16.2%** | 7.0% |

`measure` itself went 98.0 → 53.3 ms near-band and 90.2 → 41.6 ms on breadth, on
the same pictures byte for byte. The two arms load it differently because they
fire the operator differently — 203 of 320 near-band against 148 of 320 on
breadth — and firing is what costs the curve. The shares are the new run's own,
so `paint` and `repaint` rise as a share of a loop that got shorter without them
moving.

**A location that never reached a width is out of that width's denominator.**
`curves` counts a location at `k` only if it made `k` candidates. Without that
rule a run stopped by its budget would report every curve bending down at the
width it stopped at, which is the clock and not the ore.

**The sequence file is the deliverable.** Every candidate is appended to
`sequence.jsonl` as it lands, carrying location, rank, band, mode and `k`, so a
cumulative curve at any width below the one reached is arithmetic over that file
rather than another run. `depth.read_sequence` is what a killed run is read back
through, and `merge` folds the partial rows in exactly as a finished run's.

**Production knobs, and what they are for.** Unsaid, a run takes the three
measuring draws with every band on equal turns. `--shares` re-weights the draws,
`--band-weights` gives a band extra turns a round (a weight of 0 keeps it out),
and `--floor-modes`/`--floor-width` turn on a fourth draw, `mode_floor`, which
holds a **proven** location — one already over `Q4_BAR` on `P(>=4)` — and cycles the
modes a census says are short of seats. `deficient_modes` counts a seat as a
distinct location and not a clearing candidate, because a collection seats a
location once.

**`--modes` is not filtered to what `field_modes()` returns, and that is how a
niche or non-shareable mode gets mined at all.** The roster defaults to the
shareable modes `mode_policy` accepts, but a named `--modes` is taken as given:
a composite, a modulate or a direct trap simply takes the render path, and
`trap_circle` can be drawn despite its weight of 0 — a standing is a default and
never a prohibition. Two consequences worth
knowing before sizing one. A non-shareable partition pays a full render per
candidate rather than one dump per (location, mode), so `k` buys nothing there and
the width should go to coverage instead. And **the cost axis is per-mode, not
per-kind**: on `sparse_mode_harvest` (2026-08-29) `smooth_curvature` cost 5.903 s a
candidate against `itinerary`'s 1.429 *inside one partition*, and `plan_cycled_modes`
cycles uniformly, so the dear mode took an equal count at four times the price and
ate the partition's breadth. Splitting field from composite is necessary and not
sufficient.

**When a pilot IS needed, pilot to a fraction of the leg and not to a fixed wall.**
Since 2026-09-15 `depth` and `mine` resolve `--rate` off the records at that width,
so the case left is a width nothing has run — where the fallback is
`depth.PILOT_RATE` and a pilot is what replaces it. A *short* one under-reads: on
`sparse_mode_harvest` a 180 s pilot priced its direct partition 13.6% low and its
composite partition **67%** low (1.8397 against 3.0803), every per-mode rate moving
the same direction, because 180 s reaches only the cheap head of the draw. The field
pilot, whose 852 candidates were a fifth of its leg, priced it to 0.4%. A low rate
costs *candidates* and never minutes — `--budget` is wall and the leg stops at it
either way, booking the shortfall to `counts.stopped_for_budget`. **The fraction is
about 20% of the leg's candidates**, on the target population, which is what the field
pilot's fifth was; a short pilot is a **floor** on the rate and never the rate.

**The two draws take their own width, because they are priced apart.** `--near-width`
overrides `--width` for the near band alone. It usually should: a near-band location
holds its mode and pays one dump over the whole set, and a breadth location cycles the
roster and pays one per mode, so the width at which the marginal candidate stops paying
is not one number.

**What two runs measured**, `dc1` (90 min, 12,869 candidates, 323 locations) and `dc2`
(4 h 55 m, 48,994 candidates, 2,108 locations), both on 2026-08-27:

* **Cost.** 0.417 s a candidate on six cycled field modes at k=40, 0.356 s on three at
  k=20, **0.260 s on the near band** where the mode is held. Per-candidate dump by mode
  in breadth: stripe .378 · gaussian_int .285 · curvature .268 · tia .147 ·
  exp_smoothing .147 · **smooth .056** — stripe's field costs seven times smooth's to
  dump, which is why it is the dearest field mode to draw.
* **Yield a location at k=40**, primed at 0.90: near band **46.3%**, breadth 13.8%.
  Near-band ore is 26.5 s a newly primed location against breadth's 101 s.
* **The per-candidate clear rate is flat in k out to 40.** Palettes are exchangeable at
  a place and the palette head's ordering does nothing a depth run can see.
* **The head's rank decays shallowly with depth.** Ten equal-count bands of each
  partition's never-opened pool, 1,845 locations at k=20: fitted odds ratio **0.842 a
  band**, .192 at the top and .048 at the bottom, a 4.0x spread end to end and a 2.4x
  ratio between the top four bands and the bottom six. Weighting the draw toward the top
  half pays; abandoning the bottom half does not.
* **`curvature` and `gaussian_int` are dead in breadth** — 3 clears at 0.50 in 3,212
  candidates, 0 at 0.90 — and `gaussian_int` cleared nothing in 332 further candidates
  at locations already over `Q4_BAR` on `P(>=4)`. `tia` needs depth: level with `smooth` at
  k=40 and less than half of it at k=20.
* **Disk.** 163-186 KB a picture, about 2 MB a cached field, 64 fields kept. `dc2` used
  9.7 GB against a 9.6 GB projection.

**What the winner's-curse read said**, `curate shrinkage` on `dc1`, 200 re-renders over
60 locations in 15 minutes: the mean drop in `P(>=4)` on a second reading is **-0.003 at
k=1** — indistinguishable from zero, which is what an unbiased judge gives when nothing
was selected — and **-0.042 at k=40**, with two thirds of winners falling. Prime rates
at k=40 are overstated by about **1.4x at both bars**. Quote a raw prime count as raw.

**Measured rates per arm shape, `mine_weak_modes` 2026-08-28, three engines.** These
replace every earlier per-candidate figure, which was single-engine and priced another
population. Read them as **per engine**, which is what `--rate` is:

| arm shape | s/cand per engine | cand/wall s | clear@0.50 | renders/clear |
|---|---|---|---|---|
| breadth k=3, 5-mode field roster | 4.377 | 0.684 | 1.72% | 58.0 |
| breadth k=40, same roster | 0.680 | 4.353 | 1.73% | 57.9 |
| near band, width 96 | 0.285 | 10.378 | 10.66% | 9.4 |
| composite breadth, width 24 | 2.843 | 1.053 | 0.57% | 175.6 |

* **The dump is the whole cost curve.** Solving the two breadth rates gives a **0.74 s
  render and a 3.43 s field dump**. At k=3 every candidate pays a whole dump, so k=3 is
  6.4x the per-render cost of k=40 while clearing at the same rate. Buy width unless
  locations, not candidates, are the scarce thing.
* **The near-band pool is opened by `--modes`, not by `--near-width`.** Near-band
  eligibility filters on the roster, so a two-mode roster saw **25** places and the full
  six-mode field roster sees **798** — 32x, at the same width. Mining also *consumes* the
  pool: 798 fell to 645 in one leg as places were primed past the upper bar.
* **The near band's 10.378 candidates a wall second is a FIRST pass over freshly opened
  places, and it does not survive retention on a worked pool.** That leg met each
  (location, mode) pair with room under `RETAIN_PER_PAIR`; a later pass over the same
  pairs is competing with ranked incumbents and keeps about a tenth of what it renders
  — see *Retention discard is arithmetic* above. Read the row as candidates bought, and
  price rows **kept** off the leg's own merge.
* **The near band cannot be aimed at a mode.** `plan_held_mode` holds the *incumbent's*
  mode, so the mix is whatever the primed places already are. One 35,306-candidate leg
  spent 26,954 of them on `smooth` and `exp_smoothing` and 480 on `curvature` and
  `gaussian_int`. `--modes` decides who is *eligible*, never the mix.
* **`--rate` sizes the plan only, so under-quote it.** A leg whose realized rate beats
  its pilot by more than `PLAN_HEADROOM` (1.6) runs out of *plan* and stops early with
  budget left. Quote a rate below the pilot's and the leg spends its budget to the
  second: measured 100.1% of budget on three legs quoted low, against a plan-limited leg
  that spent 1,038 s of 1,108.
* **Pilot the roster the leg will actually run**, and do not pilot unlike shapes
  concurrently. A k=40 pilot sharing the machine with a dump-heavy k=3 pilot came out
  **42% dear**; a composite pilot including the cheap `direct_trap_lines` under-priced a
  leg that dropped it and kept the dear `direct_trap_ring` by **89%**.
* **Three engines are 1.690x the wall throughput of one, not the record's
  `concurrency`.** Measured by re-running a leg's seed on one engine alone, which
  reproduces its draw exactly (440 of 440 identical recipes) so the comparison is
  location-matched: 0.4707 s/cand on three against 0.2652 on one. Contention costs
  1.775x per engine. The record's `concurrency` field read **2.958x** on that leg and
  over-reads by 1.75x. It is engine-seconds over wall and is not a speedup.
* **`config.field_modes_only` is derived since 2026-09-07 and was a hard-coded `true`
  before it.** `build_plan` still takes `--modes` verbatim with no
  `colorize.shareable()` check — the field is a *report* and never a gate — but it is
  now `depth.field_modes_only(plan["roster"])`, so a wholly composite roster records
  itself as one. **Every record written before that date claims field modes only
  whatever it ran**, so on an older record the field says nothing and the roster is
  what to read. The cost of a mixed roster is in the plan rather than in the record: it is
  cycled **uniformly**, so a composite mixed in beside field modes takes an equal count
  of the width at several times the unit cost and eats the breadth the leg was bought
  for. A composite wants its own bounded leg, not a seat on this one.
* **`--finish-by` is `harvest`'s alone and does not pace anything.** All five sites sit
  under the `harvest` parser and it is a *derivation* of `--minutes` — the clock picks
  the budget once, at launch, and nothing consults it again. `curate depth` does not
  have the flag at all: it sizes off a budget in **wall seconds** plus a rate measured
  at **its own width**, and refuses rather than guessing when the rate is absent. A
  gallery pass has no clock of either kind — it runs to completion, and the hours it
  is quoted at are an estimate with a hard-kill backstop behind them.

**The reframe channel's head-q4 nuclei clear at nine times the breadth rate for the
same money, `reframe_q4` 2026-09-01, three engines.** One hour of the standard
per-location draw over the top of `discovery.reframing`'s q4 slice, and the row to
read it against is the **breadth k=3** row above rather than the ledger-wide 7.0%:
the two cost within 7% of each other a candidate, which is what makes the clear
rates comparable at all.

| | population | rung | regime | k | s/cand | cand/wall s | clear@0.50 | renders/clear |
|---|---|---|---|--:|--:|--:|--:|--:|
| `mine_weak_modes` breadth | never-opened admitted, 5 field modes | scan's | 640x360ss2 | 3 | 4.377 | 0.684 | **1.72%** | 58.0 |
| `mine_weak_modes` near band | already over the bar | scan's | 640x360ss2 | 96 | 0.285 | 10.378 | 10.66% | 9.4 |
| `reframe_q4` | 1,252 head-q4 nuclei past `PRESELECT_RADIUS`, top-down | the head's picked rung | 640x360ss2 | 1 | 4.676 | 0.636 | **15.62%** | 6.4 |

`clear@0.50` is raw `P(>=4) >= 0.50` on one reading of one candidate, in all three
rows. `reframe_q4` drew **2,286 candidates over 762 places in 3,593 s**, one smooth
and two strange a location out of the production roster with the palette head
picking from a 32-wide neighbourhood — so its `k` of 1 is a candidate per (location,
mode) and every candidate pays a whole field dump, which is why it prices beside
k=3 and not beside k=40. **51.14%** of its rows also clear `P(>=3) >= 0.50`; **38.1%**
of its places produced a q4 row and **91.3%** a q3 row.

**It beats the near band, which is the part that is not arithmetic.** A near-band
place was chosen for already holding a candidate over the bar; these places had never
been drawn at all. Read it as a statement about the *population* — a solved nucleus
framed at the rung the location head picked — and not about this draw's shape, which
is production's unchanged.

**The head's rank pays across the slice it reached**, top to bottom of the 762 drawn:
24.56 / 17.32 / 14.25 / 11.62 / 10.53% over five equal bands of 152 places, and
55 / 42 / 36 / 31 / 27% of places producing a q4 row. A 2.3x spread end to end
*inside* a population every member of which the location head already called q4.

## `curate shrinkage` — what the winner of a wide set loses on a second look

A location is PRIMED on the **maximum of k noisy readings**, so a prime rate
captures noise as well as quality and does so more the wider the set is. The
calibration sheet measured the noise across one doubling of geometry: `P(>=4)`
moves by mean **-0.009** with sd **0.087**, and 46% of rows land in a different
0.10-wide band than the one they were drawn into. Unbiased, and imprecise — and
an unbiased-but-imprecise score fed into a maximum comes out biased upward.

```
src/fractal_wallpapers/curation/shrinkage.py         the draw, the re-read, the two curves
artifacts/curation/shrinkage/<name>/pairs.jsonl      one row a re-read candidate, both readings
artifacts/curation/shrinkage/<name>/pictures/        the label-geometry renders
artifacts/curation/shrinkage/<name>/shrinkage.json   the record: drop by width, both curves
```

```
fractal-wallpapers curate shrinkage --name d1 --per-arm 20
```

**Three render workers**, `shrinkage.WORKERS`, like every other leg here. It was
six until 2026-08-28 — the one leg in this stage that disagreed with the locked
rule — and three is a rule about this machine rather than a tuning knob: more
than three engines at once makes the desktop unusable while the leg runs.
`--workers` still takes another number.

It takes the candidate that was the running best of the first `k` at each of
`CHECKPOINTS`, re-renders **that** candidate at label geometry (1280x720 ss2)
through its own recipe, and scores it on the same shipped artifact. A candidate
that won at several checkpoints is rendered once and carries every width it won
at, which is most of the saving.

**Both curves are reported and neither replaces the other.** The raw curve is the
640x360 reading, which is what every prime count this project has quoted is; the
calibrated curve is the same locations and the same winners counted on the second
reading. They share a denominator by construction — a candidate the re-render
refused leaves both columns rather than scoring zero in one.

**It corrects nothing.** The label-geometry read is another single noisy reading,
not a truth. What it removes is the *selection*, by drawing the noise again after
the winner was chosen.

## `curate remode` — buying back what a weight-0 ruling stranded

Every other leg here spends supply on places the pool has not reached. This one
spends it on places the pool **used to** reach and stopped, and the thing that
stopped it was a ruling rather than a shortage.

A [`mode_policy`](GALLERY.md) weight of 0 leaves a mode's material standing — its
ledger rows, its pictures and its labels all keep — and takes every row of it out
of `solve.pool`. Those two facts together have a consequence the ruling does not
state: **a place whose only clearing candidate was in the ruled-out mode stops
being a place a gallery can reach at all.** When `exp_smoothing` went niche on
2026-09-04 that was **574 places** and 17 seats at `n = 1000`. The material was
not deleted and it was not usable either.

```
fractal-wallpapers curate remode plan  --name r1 --from-mode exp_smoothing --to-mode smooth
fractal-wallpapers curate remode run   --name r1 --from-mode exp_smoothing --to-mode smooth
fractal-wallpapers curate remode merge --name r1
fractal-wallpapers curate remode read  --name r1
```

```
src/fractal_wallpapers/curation/remode.py            the population, the twin, the leg
artifacts/curation/remode/<name>/rows.jsonl          ledger rows, appended as each lands
artifacts/curation/remode/<name>/scores.jsonl        sidecar rows, likewise
artifacts/curation/remode/<name>/sequence.jsonl      one row per twin, with its stamp
artifacts/curation/remode/<name>/pictures/<key>.jpg  the twin renders, named by recipe
artifacts/curation/remode/<name>/remode.json         the record: population, plan, carry
```

**The twin is one `replace` on the stored recipe, and everything else is held
because it is never named.** `remode.twin` reads the recipe back through
`recipes.of_record` and moves three members: the mode; `mode_params`, emptied,
because `renders.FIELD_IDENTITY` holds it and the target's settings space is not
the source's; and the autolevel stamp, **re-derived** through
`recipes.live_stamp` rather than copied, because whether the operator applies at
all is a function of the mode's *kind* — a `field` to `direct` twin has to drop
it. The frame, the cap, the regime, the curve, the map, the seven palette knobs
and the palette group are carried by not being mentioned, so a member added to
`recipes.Recipe` tomorrow is carried too.

**No framing lookup, and that is the point rather than an omission.** A framing
index answers *where should a fresh candidate be drawn*; adopting a refinement
here would move the frame and make the twin a different picture at a different
place. `remode.frame_of` reads the source row's own viewport and cap, and
`tests/test_remode.py` reads the function's source to keep a future edit from
adding one.

**Nothing is re-labelled, and it would have been cheaper.** The paired eye check
behind the `exp_smoothing` ruling found the two arms to be the same picture at
98.7% of 914 seats with the judge unable to order them apart, so moving the mode
field on the stranded rows and keeping their scores was arithmetically
defensible and free. It is refused because a **recipe key is a digest of the
engine spec**: a row claiming a mode it was not rendered in names a picture
nobody made, and every reader that re-derives a picture from a row would
disagree with the disk, silently. Each twin is rendered and judged on its own
merits like any candidate, and one that comes back under the bar is a row that
merged and does not clear.

### The bar is read twice, on two different populations

`plan` reports both and they are different questions. The **source rule** is
which column the retired mode's own rows cleared on, and it selects the
population — `headroom.rule_of`, which is `headroom.bars`'s own test hoisted out
of its loop precisely so a mode the roster no longer holds can be asked about.
The **target rule** is which column the target mode clears on in the pool the
twins are about to join, read off `solve.pool` through `headroom.bars`, and every
twin's `clears` is read against that. A clearing rate taken against the leg's own
output would move with the leg's own yield.

### What bounds what it can give back, and it is the retention rule

Three counts come out of `read` and **the row count is the least interesting**.
Rows made is what the engine drew; rows clearing is the population a gallery
sees; places that regain a clearing row is the figure the ruling's cost was
stated in — and that one is bounded by neither of the others. Every twin lands on
`(location, target mode)`, where `candidate_ledger.RETAIN_PER_PAIR` keeps its few
ranked **within the pair** by the fitted rank key, so a place already holding
three better-ranked rows in the target mode absorbs its twin and gives nothing
back. `merge` reports the prune's verdict beside its own row count for that
reason.

**`read` reports the crossings both ways and `crossed_up` is zero by
construction**, so a non-zero one is an assertion failing about `remode.population`
rather than a finding about a mode — [`LEGS_decisions.md`](LEGS_decisions.md)'s
*What the first leg bought, measured*.

### Three workers, cut at the location, and the sharing is worth less here

The standard shape: `depth.run`'s parent-resolves-and-writes arrangement, three
engines below normal, blocks cut at the location so one dumped field serves every
map at a place. The saving is real but **thinner than on a draw** — a retired
mode's clearing rows sit about one and a half to a place, not forty — so price
this leg nearer the k=1 end of `MEASUREMENTS.md`'s table than the k=40 end.

Its subtree is in `candidate_ledger.POOL_SUBTREES`, which is half of shipping a
leg here: `curate candidate-ledger orphans` enumerates those names and no others,
so a subtree missing from the tuple leaves a killed run's pictures on disk with no
row anywhere and nothing able to find them.

## `curate phase-response` — what the axis DOES, before anything asks what it is worth

Every other leg here adds to the pool or sweeps it. This one does neither: it renders a
small stated panel, reads the pixels, and writes a table. No head reads anything, no row
reaches the ledger, and nothing about the draw moves — which is what makes it the thing to
run before a ruling on what mining spends, rather than after.

```
fractal-wallpapers curate phase-response run  --name p1     # render the grid, read the pixels
fractal-wallpapers curate phase-response read --name p1     # the table, the control, the split
```

```
src/fractal_wallpapers/curation/phase_response.py          the panel, the metric, the cut
artifacts/curation/phase_response/<name>/rows.jsonl        one row a (mode, place, map, phase)
artifacts/curation/phase_response/<name>/record.json       the panel, the seed, the clock
```

**The four direct traps are the harness control and the command fails on them.** The axis
cannot reach a trap figure — `coloring::shade`'s `Direct` arm never receives the `Palette`
at all — so they must come back byte-identical, and a pass where they do not has a fault
rather than a finding. The table is still printed and the exit code is still 1, because a
reader who sees only the table cannot tell that it is void.

**Levelling is off, and that is what makes it a reading of the axis.** The autolevel
operator derives its curve off the picture's own histogram, so a phase shift moves the
histogram, which moves the curve, which moves the picture a second time. With the switch
on the column would be phase *plus* re-levelling and nothing in the reading could separate
them — the trap `palettes/README.md` records for the baked lightness axis, where the
operator acted on 100% of one dose's rows. **So the levelled arm is unmeasured**, and
production draws levelled.

**Both a place and a map are varied, and neither is decoration.** `coloring.rs`'s
`INTERIOR` is hard black and outside the map, so how much of a frame the axis can reach is
a property of the **place**; `mirror` is read off a map's own kind, so a folded ramp and a
cyclic one are different objects to traverse. The first pass found the second of those
carries nearly the whole spread and the first almost none of it — which is a finding about
the panel as much as about the axis, since a panel drawn from `gallery3`'s shallow half is
deep exterior views with almost no interior in them.

**A phase is finished or not started and no mode is ever cut.** `run` renders the grid's
baselines, then sweeps one phase at a time over the whole grid, so a `--budget` that binds
takes the largest doses from every mode at once. A mode-major sweep would have taken whole
rows out of a table whose whole question is per-mode.

`MEASUREMENTS.md`'s *What `Palette.phase` moves, by mode* is the reading: 304 renders in
108.5 s of wall, the control at 48 of 48, and **no accepted mode flat**.

**The whole pass is deterministic and it was checked rather than assumed**: run twice over
the same seed, every ΔE, percentile and identity in all 228 rows reproduced exactly, and
only the clock moved (268.5 engine seconds against 282.4). Which is the property the
byte-identity control needs to mean anything.

## `curate rotate` — the phases nothing ever asked, and the rows they replace

Every other leg here adds to the pool. This one **replaces** rows in it, and it is
the only thing in the project that does.

`Palette.phase` — where the traversal of the gradient starts — was not a member a
candidate leg could move until 2026-09-11. So every recipe in the store was chosen
at phase 0 with no alternative on the table, the pool is a **selected-at-phase-0
population**, and every head fitted on it inherits that and calls it quality. The
target to hold in mind is *what the store would look like if rotations had been on
the table from the beginning*. This does not reach it and is not meant to: it acts
on the rows that pass the shipped fine bar, and the point is the direction.

```
fractal-wallpapers curate rotate plan  --name r1                 # the census, rendering nothing
fractal-wallpapers curate rotate run   --name r1 --budget 24000  # render, read, decide
fractal-wallpapers curate rotate merge --name r1 --dry-run       # what it would take and add
fractal-wallpapers curate rotate merge --name r1                 # remove, then upsert
fractal-wallpapers curate rotate read  --name r1
fractal-wallpapers curate rotate mine  --name m1 --budget 18000  # the same question, on rows that do not exist yet
```

```
src/fractal_wallpapers/curation/rotation.py            the population, the draw, the decision
artifacts/curation/rotation/<name>/plan.jsonl          every row and the phases drawn for it
artifacts/curation/rotation/<name>/decisions.jsonl     all six candidates a row, both columns
artifacts/curation/rotation/<name>/rows.jsonl          the ledger rows the winners become
artifacts/curation/rotation/<name>/scores.jsonl        sidecar rows, likewise
artifacts/curation/rotation/<name>/removed.jsonl       the keys the adoptions replace
artifacts/curation/rotation/<name>/pictures/<key>.jpg  the adopted rotations, named by recipe
artifacts/curation/rotation/<name>/rotation.json       the record
```

### The dump is the whole economics, and it is also the whole coverage

A palette pass is spent **after** the field is read, so five rotations of one recipe
are five colormap lookups over one iteration pass. That is the only reason six
candidates a row is affordable at all: at full render price it would be six times
what the store originally cost, and as a recolour it is about one and a quarter.
The unit of work is therefore the **(location, mode) pair** and never the row —
`rerender.render_pair`'s arrangement and `remode.blocks_of`'s, reached rather than
restated.

It also bounds what the pass can reach, and the bound is the engine's rather than a
choice: only a `field` coloring has a single scalar field to dump. So the
composites, the modulates and the direct traps are out, and the traps are out
**twice over** — `phase` is a byte-for-byte no-op on a trap figure over a flat
ground, so a rotation of one would take a second recipe key for the same picture.
Everything else refused is recorded as **owed**: rotatable at full render price,
which is six iteration passes a row, and not done here.

### `--owed` — the other side of the dump, at full render price

The bound above is the engine's and the debt it leaves is real, so the flag that
takes it is a **swap** and not a widening: `--owed` takes the rows with no field to
dump and refuses the dumpable ones as `dumpable_not_owed`, which is the other arm's
work rather than a debt. The two arms partition the passing set.

Swapped, because the two are priced an order apart — six iteration passes a row
against one — so an arm holding both would report one seconds-a-row over two
prices, and would re-run the cheap half nobody asked for. The dedupe does not stop
that: a dumpable row's four losing rotations are recorded and **freed** rather than
merged, so nothing in the store says they were ever made.

It buys clock and no new code. `colorize.render` already renders these — a mode
with no field to dump falls through to the render path, which is where every direct
trap already is — so the flag lifts one refusal and nothing else about the pass
moves. The direct traps stay refused in **both** arms: `phase` is a byte-for-byte
no-op on a trap figure over a flat ground.

```
fractal-wallpapers curate rotate plan --name owed1 --owed                  # the census
fractal-wallpapers curate rotate run  --name owed1 --owed --budget 24000   # at full price
```

### A rotation carries its incumbent's own palette knobs

The rebuilt phase 0 has to digest back to the key the row is filed under — that is
`_resolve`'s guard and the proof a pass moved *only* the phase. It refused 43 rows
of `rotation_pass_ckpt120`, and **none of the 43 was misfiled**: every one digests
back to its own key out of its own stored recipe, as all 374,309 rows in the store
do. What did not reproduce was the *rebuild*, which was built at
`labeling.finished.recipe`'s defaults where those rows carry a tuned `gamma` —
every one of them, with `reverse` on 20 and a different `transfer` on 18. No
candidate leg draws those knobs; the label-import path wrote them, and all 43 carry
a human label, which is why they are in the passing set at all.

`Incumbent.pass_knobs` carries the **difference from the plain pass** forward onto
each rotation, so the rebuilt phase 0 is the row again and the rotations are that
row's pass with the phase moved. The difference and not the whole pass: an
intention's `palette` is what the draw *moved*, recorded on the row as
`palette_drawn`, and handing back the six knobs a plain pass already has would make
every row look like a varied draw. `mirror` is never in it — the colormap's bake,
derived off the map and refused as a draw — and `mirror_cycles_audit_ckpt120` proved
the derivation agrees with every row in the store in both directions. After the
change all 6,036 rotatable rows reproduce and the guard refuses none.

### Levelling: each candidate derives its own, which is the cheap answer and the sound one

Matt's ruling is that the curve is close enough either way — share the dump's, take
phase 0's, or let each derive. Deriving is what `colorize.render` already does with
`borrowed` unset, so it is *zero* code; and it is the only one of the three that
keeps the ledger's second invariant. A recipe key's autolevel member is
`recipes.stamp_of` — the operator, the switch and the band — and **never the curve
the operator derived**, so an inherited curve would put a picture in the store
under a key that a `re-render` of that row reproduces differently. What it costs is
the `measure` stage: a JPEG decode and an Oklab pass, in Python, per candidate.

### The tolerance is a factor of the STORED column, and that is the only reading that can refuse

`--tolerance` is relative because `p_fine` spans orders of magnitude down the pool:
a fixed margin would be the whole reading at the bottom and a rounding error at the
top. It is asked against the reading the pool **already carries** and not against
the pass's own re-score of phase 0, and the difference is whether it bites at all —
a rotation that wins best-of-six has beaten the fresh reading by construction, so a
factor on that would refuse nothing ever. What the stored column catches is all six
coming in far under what the store says the row is worth, which is a levelling, a
head or a picture that moved rather than a rotation to adopt.

**Re-scoring phase 0 is also the pass's own proof that nothing else moved.** The
row's picture is not re-rendered — it is read, by the same head in the same batch as
its five rotations — so the fresh reading and the stored one must agree, and they do
to seven decimals over every row the pass has visited.

**So the tolerance has never fired and cannot while that agreement holds**, and a
pass where it starts refusing is a pass to read rather than a factor to lower —
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the first pass found* has the
reading it has never fired over.

### Two rows are never removed, and the list here is longer than the ruling's

A row seated in **any** recorded gallery, and ⚠ a row carrying **any** human label,
coarse or fine, sheet or import: a hand label does not come back, and a label
pointing at a picture nobody has is worse than no label. If a held row's rotation
wins, **both** are kept — the guard refuses the removal and never the adoption.

`rotation.protections` honours those two and `sweep.prune`'s other three beside them
— a live release seat, a human rejection, and a row the rank key's own fitted
population names — on the argument that a pass which protects more rows than it was
asked to is safe in a direction a pass that protects fewer is not. Each is counted
apart on the record, so the two the ruling named can be read on their own.

### The removal is a second transaction on this store, and it records its loss

`sweep.remove` is the verb, and it is the second thing in the project that drops a
ledger row. The single-deletion-site rule it joins was protecting one property —
that the `ratchet` can account for every row this store has lost by reading the
transactions — and **that property is kept rather than spent**: `remove` writes its
loss down exactly as a prune does, and the ratchet's reading is unchanged by which
of the two wrote the row. What `remove` does *not* have is a rule: `prune` decides,
this one is told, and the caller owns every protection it meant to honour.

**The removal runs before the merge**, which is the one ordering decision here. A
rotation lands on the same `(location, mode)` pair its incumbent stands in — the
palette is not part of what `retention` pairs on — so merging first would hand the
prune a pair one row over its real size and let the rule evict a **third** row this
pass never decided anything about.

### `curate rotate mine` — the same question on rows that do not exist yet

Standard process and standard mode policy: the draw is `depth.build_plan`'s over
`mode_policy.mined()`'s twelve, and the one thing that differs from a production
depth leg is that each shot becomes a phase-0 control plus four rotations, all five
are read through the fine head, and the best of them is the row that merges.

⚠ **The four that lose are recorded and not merged, and both halves are the point.**
Merging all five would put four near-duplicates at one (location, mode) and spend
the retention rule's keep on them. Recording only the winner is the subtler failure
and is the selected-at-one-phase bias again one level up: a store that keeps the
argmax of five and forgets the five gives every rate read off it a winner's curse
with nothing beside it to correct by. `decisions.jsonl` carries all five with their
drawn phases and both columns.

**Width 12 over twelve modes is prune-free arithmetic, not a knob.** One map a
(location, mode), one row of the five merged, one row a pair against a keep of five.
`palette_variant_mine_ckpt120`'s pilot ran width 12 over `curate depth`'s *default*
roster — which is the three shareable modes and not the policy's twelve — and lost
229 of 726 rows at the merge. `--modes` defaults to the policy here for that reason.

**It aims like `curate depth run` does, since 2026-09-13.** This leg carries the
whole draw-shaping surface — `--floor-places`, `--floor-untried`, `--floor-modes`,
`--floor-width`, `--floor-seats`, `--near-places`, `--cell`, `--draw-cells`,
`--draw-cutoff`, `--draw-maps`, `--bands`, `--top-bands`, `--band-weights`,
`--partition-weights` — with the same readers and the same meanings. Before that it
took `--modes`, `--shares` and `--width` alone, which meant the rotation search was
reachable only on the draws nobody narrows: a leg wanting rotations **and** a named
floor population, or rotations **and** an aimed cell, could have either and not
both. `mine_night_ckpt124` is where that bit, on two of its five units at once.

⚠ **Every one of those flags is part of the plan's identity**, so the resume rules
below govern them exactly as they govern `--rate`. A leg drawn over a different
manifest is a different plan and `--from-block` across the two would skip blocks the
second plan never built. They ride on the record as `draw_identity`, written only
when the leg narrowed something — a leg that narrowed nothing produces the identity
it produced before the flags existed, which is what keeps every record written
before this date resumable.

#### A clock-bound leg is resumed by INDEX, never by re-drawing

`--budget` sizes the plan *and* is the deadline, so a second leg handed only the
clock it has left plans a smaller draw and starts it at the beginning. A resumed
leg says **both**: `--plan-budget` is the first leg's budget, which rebuilds its
block plan exactly so that block N here is block N there, and `--budget` is what is
left to spend on it.

⚠ **`--rate` is part of rebuilding the plan and is the one that is silently
wrong.** The plan is `PLAN_HEADROOM * workers * plan_budget / rate`, so a resume
that names `--plan-budget` and leaves `--rate` on its default rebuilds a different
plan — `mine_ckpt120` ran at 6.0 and the flag defaults to `MINE_RATE` 2.5, which is
11,520 shots against 27,648. **Restate every flag the first leg's record carries**;
`--width`, `--rotations`, `--seed`, `--shares` and `--modes` happen to default to
what that leg used, and `--rate` is the one that does not.

⚠ **`blocks_done` is NOT the resume index. `resume_from_block` is.**
`blocks_done` is incremented by `len(block)` once a whole **chunk** returns, while
each worker's `render_draw_group` breaks out of its own block list at the deadline
— so a leg cut mid-chunk counts the entire chunk as done. `mine_ckpt120` reports
`blocks_done: 400` against a `CHUNK_GROUPS` of 400 and a plan of 960, and its
`decisions.jsonl` holds **247** locations: block 245 with 11 of its 12 shots, block
246 with 3, and blocks 247-399 with nothing at all. `--from-block 400` would have
thrown away 153 never-rendered locations, about 1,836 shots.

Since 2026-09-12 every mine record carries **`resume_from_block`** — `blocks_skipped`
plus the distinct locations its `decisions.jsonl` actually holds, which is
[`rotation.resume_index`] and is recomputable off the files for a record written
before the field existed. It is printed in the leg's own closing summary beside the
flags to restate, so the number never needs the record read for it, and
`blocks_done` keeps its own meaning: the blocks handed to the pool.
`mine_ckpt120` answers 247 and the leg that resumed it, 247 skipped plus 129
decided, answers **376** — not the 647 `blocks_skipped + blocks_done` gives.
**An index above what any leg of this plan reached is refused at start-up**, before
the population read: passing one always discards work that was paid for, and four
hours in is the wrong place to find out. The refusal is `resumable`'s, matched on
the plan's identity — seed, rate, plan budget, width, workers, roster and the
non-zero shares — so a resume that left `--rate` on the default is refused too, by
the same guard and for the same reason.

Between the two there is one shot's worth of judgement. Resuming at the first
*incomplete* block re-renders the shots it already did, and a shot whose winner was
a rotation comes back as the best-of-four this section warns about; resuming at the
first *untouched* block abandons them. `overnight_ckpt121` took the second — 247
rather than 245, giving up ten shots to keep every decision a whole best-of-five.

Re-drawing is not the same act and the dedupe does not save it. Each shot's four
losers are recorded and **freed** rather than merged, so nothing in the store stops
them being made again; and a shot whose *control* never merged comes back as a
best-of-**four** read against the same control, which is a different number under
the same name. The record carries `plan_budget_seconds`, `from_block` and
`blocks_skipped` beside `blocks_planned`, so the halves read back as one leg.

```
fractal-wallpapers curate rotate mine --name m1 --rate 6 --budget 14400   # 247 of 960 rendered
fractal-wallpapers curate rotate mine --name m2 --rate 6 --plan-budget 14400 \
    --from-block 247 --budget 20000                              # and reports 376 at the end
```

#### ⚠ `--from-block` cannot continue a mining plan, because a merge moves it

**Everything the section above says about restating the flags is necessary and it
is not sufficient**, measured 2026-09-12. *Block N here is block N there* holds for
the flags and fails on the population: the block plan is a deterministic function
of the **drawable pool**, and merging a location takes it out of that pool for good.

The ranked draw — `banded_places` over `ranked_bands` over `world["pools"]` — is
`hunt.drawable`, which is the admitted population **less
`hunt.opened_locations`**. A leg's merge opens every location it decided, so those
locations leave the pool, `ranked_bands` re-cuts its bands over what is left, and
each `(partition, band)` cell is re-shuffled by `random.Random(...).sample(held,
len(held))` over changed membership. The plan that comes back is a different plan
of the same size.

Reconstructed both ways over the live store, and it reproduces exactly. Put
`mine_ckpt120`'s 247 locations and its resume's 129 back into the drawable pool and
rebuild: **247 of 247** of the first leg's blocks come back in order, block for
block. Take the first leg's own 247 out again and rebuild: its resume's 129 blocks
come back at indices 248-376, **129 of 129**, and **none of the first leg's 247
appears anywhere in that plan at all**.

Two things follow and they pull opposite ways:

- **No resume on this arm can re-render merged work**, which is why last night's
  leg was harmless and why the dedupe census reads zero. `already_in_ledger` counts
  a drawn recipe key the ledger already holds, and the ranked draw takes only
  locations the ledger has never stood on — so on a wholly ranked leg the count is
  **0 by construction** and is not evidence of anything. Rebuilt over the live
  pool: 46,080 candidate keys drawn, 0 already in the ledger, against 2,950 of
  `mine_ckpt120`'s 2,954 adopted keys sitting in the same `known` set the check
  reads. The set is right, the lookup is right, and the arm cannot produce a hit.
- **Nor can it continue anything.** `--from-block 247` skipped 247 blocks of the
  *resume's own* plan — 247 never-opened locations, about 2,964 shots, that nobody
  had rendered — and spent the clock on blocks 248-376 instead of 1-129. Nothing
  was lost for good, since an unrendered location stays drawable, but the index
  bought nothing either. **On a wholly ranked leg, `--from-block` is a way of
  taking a different slice of the same pool**, and the honest way to continue such
  a leg is to run it again with no index at all.

**Where it does bite is the arms that draw at OPENED locations** — `near_band`
(`near_places` over `world["best"]`), `mode_floor` (`floor_pool = world["best"]`)
and `conditioned`. There a location stays drawable after it merges, a re-run can
re-draw the same `(location, mode, colormap)`, and the dedupe fires — on exactly
**one of the five** candidates, the winner, because the four losers were freed and
no row names them. That is the worst of the five to drop: if the winner was the
`k=0` control, `made[0].k != 0` discards the whole shot, and if it was a rotation
the shot comes back as a best-of-four against the same control. On
`mine_ckpt120`'s own split — control won 1,136 of 2,954, a rotation 1,818 — a
re-entered block would silently drop **38.5%** of its shots and re-price the other
**61.5%**. `depth.SHARES` defaults `near_band` to 0.25, so a leg that does not
spell `--shares` puts a quarter of its clock on that arm. ⚠ **The right act on a
re-entered shot is to skip the whole shot, not one candidate of it**, and that is
what a fix has to change.

### The chunk is the interruption point, and it is what bounds the disk

A chunk of groups renders on the pool, the fine head reads everything the chunk made
in **one** batch, the decisions are taken, and every rotation that was not adopted
has its picture and its `<stem>.leveled/` unlinked before the next chunk starts. So
the disk holds one chunk of undecided candidates rather than a pass of them, and a
pass killed at the clock leaves no picture that is neither adopted nor gone. The
render pool is idle while the heads read, which is the trade the chunk size sets:
400 groups is about eleven minutes of rendering against about one of reading.

Its subtree is in `candidate_ledger.POOL_SUBTREES`, and it matters more here than at
any other leg: five-sixths of what this pass makes is garbage **by design**, so a
run killed mid-chunk leaves that whole chunk named by nothing.

**It holds the pool**, twice — the population read streams the ledger and the merge
rewrites it — and the one-pool-holding-process rule binds on both.

[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the first pass found* is the pass
this leg's shape was settled on.

## `curate repetition` — the axis neither head has been shown, put to an eye

`curate rotate` moves where a traversal starts. This moves **how many times it
happens**, and it does not decide anything: it renders a labelling set and stops.

The reason it cannot decide is the reason it exists. `Palette.cycles` stands at
something other than 1 on **2,262 of 374,186** ledger rows — 0.605%, 44 of them
seated — and every one of those arrived in the last few days or came in with the
maker-era corpora. So neither head was fitted on a population containing the axis,
and a head's reading of a picture whose defining property it has never been trained
against is not evidence about that property. `palette_variant_mine_ckpt120`
measured the heads preferring repeat 1 (36.4% of matched pairs won at repeat 3
against 52.6% at repeat 1) and `rotation.REPEAT` holds the axis at 1 on that
reading — which is a policy its own measurement makes self-confirming.

### The pair is proved, not promised

Every repeated tile sits beside its own unrepeated twin at the same place, mode,
settings, map and frame. `plan_of` re-derives each control's key through
`hunt.Maker.recipe_for` with no overrides and checks it against the key the store
holds it under; a control that does not reproduce is dropped and counted. The
repeat is the same call with `palette={"cycles": n}`, so the two tiles are two runs
of one derivation differing in one member.

On the first draw **0 of 125 controls failed to reproduce**, which is a stronger
statement about the pool than about this leg: every row it drew stands at exactly
the recipe `hunt.Maker` builds today.

**Phase is held at 0 on both sides.** 1,713 of the 2,262 repeat rows carry a
rotation too, so the axis as the pool holds it is confounded with the one
`curate rotate` just measured, and a sitting that inherited that confound would
answer neither question.

### The rungs, and the folded arm's own share

A cyclic map meets itself, so `cycles` is the traversal count exactly: rungs 2 and
3. A sequential map is baked folded, so one pass is already two traversals and its
one rung of 2 is **4x** the base ramp. The card prints the traversal count and the
row records `cycles`, because those are different numbers on one arm and the same
on the other.

Sequential maps are 156 of the library's 1,021 (15.3%), so `FOLDED_SHARE = 0.32`
over-shares them deliberately rather than letting the pool decide. A thin arm is
reported short rather than topped up from the other — the share is a claim about
what the page holds.

### It gates on nothing, which costs a second scoring pass

Every other draw here is aimed at a band, a bar or the top of a queue. This one may
not be: the repeats the current heads tolerate are exactly the wrong sample.

That collides with *sorted good→bad by the fine head*, because `gallery-grade
score-pool` writes `p_fine` only for rows clearing the render bar — **42,300 of
374,186**, which covered **8 of the first 125 controls**. So `repetition.fine_for`
**runs** the head over every tile at candidate geometry through
`rotation.score_fine`, and writes nothing: an ungated reading does not belong in a
column every downstream reader takes as bar-cleared. 248 pictures read in 2 s.

**So the card's `p_fine` is a reading of the CANDIDATE, and the page has no
label-geometry `p_fine` to recover.** The two numbers on a finished-render sheet
come off two geometries and there is no third: `columns` — `p_ge2/3/4`, and
`p_coarse` is that head's `p_ge4` — is the render judge on the 1280x720 tile the
page serves, while `selected_on.p_fine` and `selected_on.p_ge4` are the pool's own
640x360ss2 regime, which is where the fine head was fitted. A prompt asking for
`p_fine` *at label geometry* is therefore asking for something the build never
produced; the reading exists only if the sheet's own `full/cut####.jpg` are handed
back to `rotation.score_fine`, which costs 246 pictures in 6 s and is worth naming
as a re-score rather than passing off as recovered. It is not the same column:
on `repeat_axis_*_20260911` the candidate reading agrees with Matt's within-pair
sign on **43 of 56** decided pairs and the label-geometry re-score on **40 of 56**,
so the geometry the head was fitted at reads its own axis better.

### A pair whose row the prune took comes off the page whole

The merge is an upsert through the ordinary door and the door prunes, so a repeat
can land and be taken in the same act — `repeat_ckpt120` lost **2 of 125** that
way, at locations already holding a full keep of better-ranked rows. A tile with no
ledger row is a label with nowhere to land, so `sheet_plan` checks every drawn key
against the store and drops the whole pair, not just the missing tile.

### The sharing is given up on purpose, and it costs 145 seconds

A repeat is in principle a recolour off a dumped field. This leg gets none of that:
the draw takes **one pair a location** so no place can carry the page, so every
block holds one candidate and shares its dump with nothing. Measured on
`repeat_ckpt120`: 125 repeats at **3.03 engine-seconds each**, 145 s of wall on
three workers. Full price for every tile, and the page wins the trade outright.

**It holds the pool three times** — the population read, the merge and the sheet
plan's ledger check — and the one-pool-holding-process rule binds on all three;
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the first batch came to* is the
draw it was measured on.

## `curate repeat-ab` — the one repetition question the leg above left open

`curate repetition` **closed repetition as a general draw**: 121 matched pairs,
mean within-pair delta −0.273 tiers, `cycles = 3` a rout at −0.634 (p = 3e−6), and
the best arm exactly neutral. What it could not answer is what repetition does to
a picture that is **already good**, because that page gated on nothing and only 4
of its 121 baselines cleared `solve.DEFAULT_FINE_BAR` at all. That is the only
repetition Matt will consider, and it is what this leg draws.

**It renders nothing and merges nothing**, which is the sharpest difference from
the leg above. There is no variant candidate: the verdict keys on the location,
the baseline is already a ledger row, and the variant's recipe key is derived so
the row can name it. So there is no merge, no prune that can take a tile, no
`score-pool` owed afterwards, and no picture in a pool subtree the orphan sweep
has to know about. The leg writes `plan.jsonl` and `label build` renders the tiles
once, into the sheet directory, like every other sheet's pictures.

### The unit is one picture carrying two renders

One composite tile: the 1× render **left**, the same recipe at `cycles = 2`
**right**, equal halves at `sheets.LABEL_RESOLUTION`, the same crop, a 6-pixel
separator, nothing written on the image. One picture and not two because the
comparison is the one an eye makes in a single glance — two cards would let a
labeler scroll one out of view and answer from memory. **The side order is fixed
across a sitting** and is on the manifest under `render.sides`; a reading that
assumed the halves alternated would report the opposite result with nothing
looking wrong.

Both halves take the **baseline's** levelled colormap where it has one. The
operator's curve is a fact about the place and the mode rather than about the
traversal, and levelling the halves apart would move a second thing between them.

### The population is conditional, and that is the leg

Smooth-routed, above `solve.DEFAULT_FINE_BAR` on `p_fine` at candidate geometry,
`cycles = 1`, `phase = 0`, at the candidate regime, with a picture on disk, and
**no human verdict in either finished store**. So a rate read here is a rate about
pictures that already work at 1× and a **ceiling** on any rate about the pool.
The freshness rule is the `aug_sweep_A` failure being avoided: a page mixing
already-judged rows against fresh ones cannot be repaired afterwards, because a
difference between the two halves could be the axis or the history.

One unit per location, and at a place holding several qualifying rows the draw
picks one **seeded-uniform rather than the best** — the bar already made the
quality claim and a second one would aim the sitting at the top of a column it is
not about.

### Two deliberate deviations from this rig's defaults, both recorded

**The page is a seeded shuffle and every unit is prefilled at the neutral class.**
The premise of the sitting is that the heads cannot read this axis, so ordering
good→bad by a head or prefilling its decode would import exactly that error into
page position and into the anchor. `anchored` is `false` on the registration for
that reason and it is true rather than lenient. The render judge does read both
halves at label geometry and its readings ride on the row under `reading`, where
the page never sees them — which is what lets the head's direction be read against
Matt's later without re-rendering the sitting.

⚠ **The scale is comparative and is not a tier.** `1` the repeat is worse, `2`
neutral, `3` the repeat is better. The verdicts land in the `repeat_ab` attribute
store, whose rows carry `class` and no `score`, and they may never enter
`smooth_render`, `strange_render` or `gallery_grade` as themselves or transformed.
`data/repeat_ab/README.md` and `data/batch_caveats.md`'s *NOT-A-TIER* both say so.

**It holds the pool once**, in the population read, and no verdict from the first
sitting survives — Matt released the partial labels on 2026-09-12 and
`data/repeat_ab/` is a declared and empty store, in
[`LEGS_decisions.md`](LEGS_decisions.md)'s *What the first sitting came to*.

## `curate manufacture` — the one population here that is made rather than found

Everything else in this stage spends supply. This makes some. The colour-expression
census counted what the collection actually held and found **eight of the fifty-two
swatches on none of the 246 finished wallpapers and twenty-one on five or fewer**,
against a library with 38 to 258 maps able to reach each of those twenty-one. The
gap is not capability, and it is not something a floor can fix — the arithmetic
there says a per-swatch floor cannot exist above about five percent. Nothing has
ever *asked* for those colours, so this asks.

⚠ **That shortage is a 2026-08-24 reading and it has since closed.** Re-cut over
the 645 pictures released by 2026-09-06 the same list named **one** cell rather
than twenty-one, largely because the two passes aimed at those cells hit them —
[`MEASUREMENTS.md`](MEASUREMENTS.md)'s *What the finished collection expressed,
measured 2026-09-06*. The census was retired the same day, so nothing in this tree
answers *which colours is the collection short of* any more, and
[`manufacture.targets`] is a frozen list rather than a current one. A new batch
says what it aims at and why.

```
1  register    both arms, in both stores, BEFORE a pixel exists
2  plan        21 target swatches x 2 kinds x 2 arms; one location per row, a
               mode drawn the way a run draws one, maps off the coverage panel
3  screen      every attempt at 640x360 x2: censused, judged, nothing selected
4  confirm     the best attempt at each location again at 1280x720 x2 — the
               sheet's own geometry, and where BOTH cuts act
5  select      quotas filled from the confirmed share, under a per-map cap
6  read        the per-location hit rate, the yield, the geometry drift
```

**The screen is a pre-filter and the confirm is the decision.** A candidate-geometry
render is a quarter of the cost of the picture a person judges, so it is what the
overbuild is paid at — but nothing is *selected* there, because a new map can
wreck a picture an old map carried and the score that matters is the one on the
picture that will be on the sheet. Both cuts — a tenth of the pixels on the
target swatch, at least a 2 from the render judge — are read off the sheet render.

**The sheet serves that exact render, and it is checked rather than argued.** A
plan unit names the *levelled* colormap directory the autolevel operator wrote,
so `label build` renders through the same map and produces the same picture;
`curate manufacture --step verify --sheet <dir>` hashes every row both ways and
compares the sheet's own reading of the judge against the reading the cut was
taken on. Without the levelled directory the sheet would render through the map
as it was before the operator touched it, which is a different picture with the
same join.

**Production draws no palette knob, and that is the diagnostic's answer.** Every
colorize this repository makes is `finished.recipe()` at the identity — gamma
1.0, cycles 1.0, phase 0.0, no reverse, the value transfer, no rolloff — with
`mirror` read off the map's cyclicity rather than sampled. So the hit rate this
batch reports is a hit rate *against a draw that varied nothing*: a low one is a
fact about where a pinned ramp lands on a field, never an under-explored recipe.
Every map of the `rare-colors-2026-08` drop is cyclic, so every new-map row is
unfolded and its whole recipe is the identity.

**A tenth of the rows are a contrast arm** — the same target swatches forced
through maps the library held before the drop — in their own registered batch. A
correction on a drop row is otherwise confounded: two hundred maps authored in
one run against one brief is exactly the kind of thing a judge can have a blanket
opinion about, and without the arm nothing separates *this colour is wrong* from
*these maps are wrong*.

**One row per location, across both sheets.** A swatch quota that cannot be
filled at one row per location is reported short; it is never backfilled by
recolouring a cooperative location several ways, which would put one place on the
page under four maps and turn a correction rate into a fact about that place.
Locations come from the human q3+ tier first and the highest-scoring admitted
supply after it, and **every row stamps which tier it came from** — in
`data/curation/manufacture/<batch>/<kind>.jsonl`, keyed on the render identity a
verdict is cast on, because a store row carries the place and the recipe and
deliberately not what the page printed under the picture.

**What comes off these sheets is a ceiling.** The population is enriched twice
over, by location quality and by a passing score, so a correction rate measured
on it bounds what a correction rate could be and is never a base rate about the
pool.

## `curate label-migration` — the judged recipes, drawn again as candidates

Two corpora of human verdicts carry the whole recipe of the picture somebody judged,
at **label geometry** `1280x720ss2`. The pool stands at `640x360ss2`. This leg derives
the same recipe at candidate geometry — geometry changed and nothing else — draws it,
and reads it through the render judge and the fine head. **It stages**: nothing is
written into the candidate ledger, its sidecar, `pool_scores.jsonl` or either label
store, and merging is a separate act against a separate decision.

```
scratch/label_migration_<name>/
  recipes.jsonl        one row a derived recipe, its key, its label verdicts
  renders.jsonl        one row a staged render: stamp, levelling verdict, stop list
  scores.jsonl         both heads, at candidate geometry
  readout.json         the distributions, bars, places, expressibility, the prune
  index.html           label-4 pairs, judged beside candidate
  pictures/<key>.jpg   and <key>.leveled/<colormap>.json beside each one
  page_pictures/       the page's own copies, both sides at one width
```

**The store is under `scratch/` and not `artifacts/`** — a staged row is a reading
nothing in the pipeline may find by accident, and the three-way `artifacts/` decision
has no bin for *must not be read*.

**The population is human 3 and 4** ([`label_migration.KEPT_CLASSES`], Matt's ruling of
2026-09-08), `--classes` widens it back. The 1s and 2s buy calibration of the fine head
across the full human range, which is eval-instrument work, and they are a population
the head never meets in production: `score-pool` runs on coarse-clears only. **A key
carrying two verdicts is in if either qualifies** — those are `finished.crossovers`'
pairs, literally the same pixels judged in both stores.

**The corpora are not the candidate path and that needed a door.** The candidate path
spends `colorize.CURVE` and the plain palette; 6,420 of 11,966 resolved rows carry
palette knobs it never produces and 868 read their field through `log`. So
`colorize.render_row`/`render` grew `curve` and `palette` overrides, off by default —
this leg was the only caller until `curate label-fate` and `release.Task` joined it on
2026-09-08. The **`curve`** override refuses a `fields` directory, because a dumped field
is named for its curve and a recolour under one would be the plain field's picture
wearing the override's name; since 2026-09-11 the palette does not, `recolored` taking
the whole pass. This leg's rows carry both, so a staged render still takes the engine
path — it is the curve that puts it there.

**Measured 2026-09-08**, three workers below-normal, this machine: **1.59 s a picture
per engine, 1.77 a second wall** over 5,329 pictures in 40.6 min. Both heads read
5,329 in 92.5 s. The readout is a pool-holding process — it reads the ledger whole —
so it never runs beside another one.

**A killed leg loses its stamps, not its pictures.** `renders.jsonl` is written once at
the end, so a leg killed mid-flight leaves pictures whose autolevel curve is recorded
nowhere; `depth.levelling_of` reads those as `None` rather than guessing. Re-measuring
a curve off a finished picture gives a *different* curve — that is
`depth.ACTED_UNRECOVERABLE` — so the way back is to delete those pictures and redraw
them, which is what the resume does once their rows say nothing.

## `curate label-fate` — what became of every GALLERY-GRADE wallpaper somebody graded 4

Three stores hold a human 4 — `data/smooth_render/`, `data/strange_render/` and
`data/gallery_grade/` — and since `label-migration merge` all of them are **ledger
rows by key**. So this asks the exact question rather than the distributional one:
not *how does the pipeline score pictures a person liked*, but *what happened to this
one*. Five rungs, first that stops it.

**It reads the third store alone since 2026-09-09**, `label_fate.STORE`, and
`README.md`'s *It reads ONE of the three, and which one is the whole point* has why: a
gallery-grade 4 is a verdict on a candidate this pool holds, a finished-render 4 is a
verdict carried back to a ledger key, and whether the second implies the first is
unanswered. A page over both asked a fate question of rows whose membership in the
population was itself the open question. **The coarse-store 4s do not get a second
page here**; that is a different question and nobody has asked it yet.

```
scratch/label_fate_<name>/
  keys.txt             one ledger key a line — the solve's --explain-keys argument
  population.jsonl     one row a wallpaper: its verdicts, its ledger row, its rung,
                       the seat at its place and the row that beat it
  fates.json           which record filled rungs 3 and 4, and what it cost
  competitors.json     the pairing per rule, and what the rebuild had to prove
  renders.jsonl        one row a picture drawn, and which side of a card it is on
  index.html           the rung tables and the links
  <rung>-NN.html       150 cards a page, p_fine ascending, prev/next
  refused-<rule>-NN.html   the refused rung again, split by what refused it
  pictures/<key>.jpg   every side, fresh at 1280x720 ss2
  page_pictures/       the page's own reduced copies
```

**`keys` runs BEFORE the solve and the other four after it.** The fate of a row that
took no seat lives only inside the pass that refused it: `rejection.explained` holds
one entry per key *asked about*, and a record can only be asked while it is being
taken. That is what `curate solve record --explain-keys PATH` is for, and `fates`
refuses a record with no `explained` block or one whose block does not name every row
of the population — a rung recovered from the aggregate refusal columns would be a
guess about which of several rules acted first.

**Rung 0 is five of `solve.pool`'s six exclusions**, decided on
`mode_policy.routed_mode_of` and not the recipe's mode. The sixth is the **veto**
and it is absent by construction: this population is the gallery-grade store's
currently-resolved 4s and a veto is one of its currently-resolved 1s, so
latest-wins makes the two disjoint — `label_fate._off_the_roster` carries the
argument and is where it comes back if this population ever widens. Folding those into the
coarse-bar count would say a bar refused a picture no bar ever read. It is **counted
and not shown** on the page, Matt's call of 2026-09-08: no rule ever refused those
rows, so there is no comparison to draw. **On the gallery-grade population it reads
zero**, as does rung 1 — that sitting was drawn *from* the pool, so all 312 rows are
ledger rows above the coarse bar. Every off-roster and below-coarse row the old
three-store page counted came from a finished corpus.

⚠ **`competitors` re-applies the record's own fold before rebuilding the state.**
`solve.pool` sets no cluster, and `rules.State.places` is keyed on it, so a state
rebuilt from the bare pool answers the one-seat rule over *places* — and a row that
lost its **cluster's** seat to a sibling at another place comes back unrefused or
refused by the wrong rule. It moved 9 of 175 refusals on the first pooled record
built here. The relabel is read off `preselection.folds` and applied only where that
pass pooled; `label_fate._refolded` is the door.

**What a refused card is paired with depends on the rule that refused it**, and
`curation/README.md`'s *The picture beside a refused card is not the seat at its
place* has the whole of it. In short: `counted_requirements`' set for the acting rule,
marginal member where there is a choice; not `removals`, which answers the stricter
*would one departure be enough* and is empty for 234 of the 453 paired cards.
`competitors` rebuilds the pass's final state and **refuses unless it reproduces every
counted refusal the record wrote down**.

**Both sides of a card are drawn at one geometry**, because `sheets.LABEL_RESOLUTION`
and `release.RELEASE_REGIME` are the same `1280x720ss2`. `render` refuses if those two
constants ever move apart rather than quietly drawing a pair at two sizes. Every task
carries the row's whole recipe — `mode_params`, `curve` and `palette`, all three
`recipes.KEYED` members — and inherits its levelling through `stamps.for_release`.

**Measured 2026-09-08**, three workers below-normal, this machine: **2,231 pictures in
7,793.6 s — 2 h 10 min, 3.49 s a picture wall and 10.5 s an engine**, 0 failed. That
is 6.6x `label-migration`'s 1.59 s an engine at candidate geometry, against four times
the pixels, and the gap is the levelling: **only 352 of the 2,231 rows can inherit a
curve**, so 1,879 measure their own and take the operator's second full-resolution
pass. `curate autolevel backfill` is what would close that, and it was not run here.

⚠ **Estimate this on an idle box or not at all.** Measured beside a fast lane the
same leg ran at **5.5 pictures a minute** and beside nothing at **26.7** — a 4.9x
spread, and the first reading put the ETA at 6.5 hours against a true 2 h 10. The
`CLAUDE.md` rule about measuring a lane on an idle machine applies to estimating a
leg just as hard.

**A resume costs the rows it was holding and nothing else.** The picture is the
resume token — `release.decodable` is asked of each one — so a killed leg re-offers
only what is missing.

**A rung is a fact about a row AND a record**, so a second reading against a second
solve is the only way this leg can say a fate *changed* rather than that the page was
rebuilt. `page --against <earlier store>` joins the two populations by key and reports
`forward` / `back` / `unchanged` in the legend and every transition on the index.
**Forward is `RUNG_ORDER`, which is `RUNGS`' own order and not a ranking of
outcomes**: below-the-fine-bar → refused is forward, because the row got further
before something stopped it, and only a move to `seated` is a wallpaper that now
ships. A key the earlier store never held is `unmatched`, never movement — the
population moving is a different finding.

**The pictures of an earlier store are reusable, and the criterion is exact rather
than a guess.** A card's render is decided by the ledger recipe and by
`stamps.for_release`'s answer, and nothing else. So a key whose recipe is unchanged
and which has gained no `autolevel_backfill` row since the earlier leg built its
`borrowed` map draws the identical picture, and copying it in is the same page for
none of the engine time. `SOLVE_ckpt117_resolve_and_fate_0908` reused **1,910 of
2,250** that way and drew 340 — 312 late-backfilled keys plus 28 never drawn — which
is the difference between twenty minutes and two hours. **Take the criterion off the
stores' own timestamps**, not off a feeling: the backfill rows carry `at`, and
`sequence.jsonl` mtimes say whether the other half of `for_release` moved.
