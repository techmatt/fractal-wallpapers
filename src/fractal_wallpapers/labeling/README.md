Collecting human taste: the labeling rig and the two stores it writes to.

```
store.py          the location records: the paths, the one writer, the one reader
registry.py       what generated a batch, registered before the batch has rows
groups.py         which locations would leak into each other, and are held out together
split.py          the seeded draw over those groups, shipped as data
pins.py           the evaluation pin, asserted on the location coordinate
finished.py       the finished-render stores: one per judge, keyed on the picture
sheets.py         THE generator: two row sources, one cut, one manifest, one page
server.py         serve one sheet, to one browser, on the first free port at or above
page.html         the page: the row's pictures, the sheet's tiers, one export
export_control.js what an export is called and where it goes — one file, every page
intake.py         THE ingest: a page's export resolved against its sheet, into either store
corpus_import.py  the one-time import of the source project's location corpus
finished_import.py the one-time import of its two finished-render corpora
```

Everything runnable here is a `fractal-wallpapers label` subcommand:

```
label register --batch NAME --method "how the population was drawn" [--head smooth_render]
label build --from-ledger artifacts/walk/walk.jsonl --batch NAME
label build --from-plan artifacts/places.jsonl --batch NAME
label build --from-plan artifacts/promotion.jsonl --head strange_render --batch NAME
label build --from-plan <plan> --head smooth_render --batch NAME --order-by top
label sheets
label serve --sheet artifacts/sheet
label ingest --sheet artifacts/sheet --labeler matt --write
label show
label split --write
```

## Serving a sheet to label

A built sheet is a directory: `sheet.json` (the manifest), `sheet.jsonl` (the rows) and
the rendered pictures beside them. Serving one is two commands, and the server says what it is serving.

**1. See what is already built.** A sheet directory is named by whoever cut it and does
*not* have to match the batch inside it, so ask the manifests rather than reading the
directory names — `graduation_sheet` below holds the batch `threads_promotion`:

```
fractal-wallpapers label sheets --drops
```
```
artifacts/graduation_sheet          strange_render · threads_promotion · 3 units
                                    labels -> labels/strange_render.threads_promotion.json
artifacts/plane_deep_admissions     location · plane_deep_admissions · 172 units
                                    labels -> labels/location.plane_deep_admissions.json
artifacts/strange3_promotion        strange_render · strange3_promotion · 634 units
                                    labels -> labels/strange_render.strange3_promotion.json
artifacts/twin_top_slices           location · twin_top_slices · 96 units
                                    labels -> labels/location.twin_top_slices.json
```

`--under` looks somewhere other than `artifacts/`; `--drops` adds the file each sheet's page
saves to.

**2. Serve it.** One sheet, one port, and pick the port explicitly whenever more than one
sheet is open:

```
fractal-wallpapers label serve --sheet artifacts/graduation_sheet --port 8021
```

**`--port` is where it starts looking, not where it lands.** The bind is exclusive — a
server will not co-host a port another process holds, so no sheet ever serves half its
images out of another sheet's directory — but a clash does **not** fail. `server.serve`
walks upward from the port it was given and prints the one it got. So a sheet asked for
on 8020 while a forgotten server from another session still holds it comes up on 8021,
and a second sheet asked for on 8021 comes up on 8022. Both are correct; neither is where
you asked.

Which makes the printed line the only thing that says where a sheet is, and reading the
port back off your own command line the way to hand somebody the wrong sheet. That is not
hypothetical: it happened cutting `p_ge4_calibration_*`, where 8020 was still held by a
`run10_novel_ground` server nobody had stopped, and the URL the launch command implied was
serving a location sheet from a different batch on the same host.

It runs until stopped, so launch it in the background. It prints, flushed so a redirected
log shows it immediately, the URL and what it is serving:

```
serving <...>/artifacts/graduation_sheet
  -> http://127.0.0.1:8021/
  strange_render · threads_promotion · 3 units
  labels -> labels/strange_render.threads_promotion.json
```

The default port is 8010; the convention when several are open is 8020, 8021, … one per
sheet.

**3. Check it is really up** before handing over the URL. The page fetches its own manifest
and rows, so a 200 on `/` alone does not prove the sheet loaded:

```
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8021/sheet.jsonl
```

Render filenames are positions in the **cut** order, not unit ids: a 96-unit sheet holds
`cut0000`–`cut0095`, and unit `u0096` may be `cut0061.png`. The prefix is there so the two
numbers cannot be confused on disk — nothing is called `0096.png`, so a filename guessed
from a unit id misses cleanly instead of returning another unit's picture. The manifest is
the only ordering. (Sheets built before the prefix hold bare `0061.png`; their rows name
their own paths, so they keep serving.)

### Where the labels land

Saving from the page writes `labels/<head>.<sheet>.json` — both halves, always, so two
sheets cut for the same judge cannot overwrite each other (see [`export_control.js`] and
`store.export_path`). `label sheets --drops` prints the name for every built sheet, and
`label serve` prints it for the one it is serving.

**Serving is not ingesting.** The drop sits in `labels/` until `label ingest` resolves it
against its sheet; until then the store is untouched. Drops written before sheets carried
their own name are called `<head>.json`, and re-ingesting one needs an explicit `--labels`.

## A verdict cast on a pinned location is WITHHELD, not written

A finished store's evaluation side is a **batch** — one registered `eval_only`, cut
blind — and its pin is asserted on the *location* so a later drop cannot re-render the
place under a fresh name. A verdict from any other batch at one of those places is
therefore neither thing this store holds: it may not train, because the instrument is
spent the moment it does, and it may not join the blind sheet either, because it was
cast against a prefilled suggestion. `label ingest` names those units, counts them, and
leaves them in the export:

```
"units": {"on the sheet": 246, "exported": 246, "not acted on": 0,
          "withheld on a pinned location": 9}
"withheld": {"rows": 9, "locations": 9, "units": ["u0007", "u0018", ...]}
```

Both blind sheets are derived by location, so a withheld row that *had* landed would
have grown a blind sheet by nine anchored rows and broken every paired comparison
against it. `tests/test_finished_store.py` holds the invariant this protects: no
non-`eval_only` row sits on a pinned place. The pin is never the thing that moves.

**The check runs before the write, and again after it.** It used to run only after,
so a drop that trespassed left the rows behind and raised — a store the suite
forbids, produced by the command that refuses to produce it. Both assertions stay:
the first on the rows as they were handed to a writer, the second on the rows as the
store read them back, and the report carries `asserted_before_writing` so which
reading held is on the record.

## What cutting a sheet costs, and why the number moves so much

A location unit is **two renders at 1280×720 ss2**, and that is the whole bill —
scoring the cut page afterwards is a minute whatever the page holds. Build it in the
background and estimate before committing, because the per-unit cost is not one
number and picking the wrong one is off by an order of magnitude:

| sheet | units | mean maxiter | s/unit |
|---|---|---|---|
| a degree-2 mandelbrot offer, all above the junk floor | 152 | 28,075 | **6.8** |
| run2's plane admissions, 1e-3 to 1e-9 | 172 | 24,777 | 7.4 |
| run9's plane channel at 1e-6 and deeper, gates *not* applied | 164 | 31,955 | **53.5** |
| run10's refusals and unattempted admissions, screened | 200 | 11,927 | **3.1** |

**Maxiter barely predicts it; what the pixels do predicts it.** The first three rows sit
within 30% on maxiter and span 8× on cost. A row that escapes early is cheap however
high the cap; a row the walk refused for `interior_cap` iterates nearly every sample
to that cap, and a sheet cut over *candidates* rather than admissions is full of them.
Degree costs too — degree 2 is the cheap corner, and the expensive sheet above was 64
of 96 multibrot4.

**The last row is the same claim from the cheap end, and it is the one a cost estimate
gets wrong in the other direction.** It is a *candidate* sheet — judge refusals, gate
refusals, admissions nobody colorized — and it is the cheapest sheet on this page, at
half the maxiter and a mean interior fraction of 0.0029. The interior screen is why:
what makes a candidate sheet expensive is the interior-heavy rows, and the screen takes
every one of those off the page before a pixel is drawn. Scaled instead off a release
leg by field samples — a 2560×1440 ss4 row is 8× a location unit's two 1280×720 ss2
renders — the same sheet estimated at 8.75 s/unit and came in at 3.1, so **the sample
count is an upper bound and not a prediction**; a release row spends time on a palette
pass a sheet has no equivalent of, and its material is admissions rather than refusals.

Estimating one of these off the harvest's own steering view is the trap: that view is
640×360 ss2, so the pixel scaling is ×4 for the geometry and ×2 for the pair, and
applying it to the deep sheet above underestimated by **6.9×** — the steering views it
was measured on were shallow, gate-passing stock. Scale off a *built sheet* of similar
material instead, and when the material is deep or ungated, budget an hour per
hundred rows.

### Cutting a finished-render sheet out of the candidate pool

The pool in [`curation.candidate_ledger`] is 22,029 pictures that already exist, which
reads like a sheet nobody has to render. It is not, and three things are worth knowing
before estimating one.

**A sheet is cut for a KIND, and the kind names the store.** `finished_source` takes one
head and every verdict on that page lands in that head's store, so a population spanning
both kinds is **two sheets and two batches**, never one page. `p_ge4_calibration_*` is the
case: mode `smooth` is the smooth store, every other mode is the strange one, and a draw
banded across both had to be cut, registered, served and ingested twice.

**`--reuse-renders` misses every pool row, and it is not a near miss.** Candidates are
rendered at 640x360 ss2 and a finished sheet serves 1280x720 ss2; the cache keys a picture
by a digest of the whole engine spec, so the geometry alone makes it a different name.
Checked over all 1,144 rows eligible for that draw: **zero hits**, in both crop caches. The
render cache holds the *corpus* renders — 5,180 smooth and 3,322 strange — and nothing else.

**A levelled row cannot be re-served by naming its recipe.** The ledger keeps
[`curation.recipes.stamp_of`]'s reduced stamp, which deliberately drops `acted` because
whether the operator fired is a function of the picture rather than an input to it. So the
row cannot say whether it was levelled, and a sheet that rendered it through the base map
would serve a different picture under the same identity. The way through is
[`curation.manufacture`]'s: render at sheet geometry through `colorize.render` with
`level=True`, which writes `<stem>.leveled` beside the picture, then point the plan unit at
that directory by name. The plan's own `leveled` key is the whole mechanism.

**So it is two renders a unit, and the second one is the check.** The measure pass makes the
picture and the levelled map; `label build` renders again from the plan; and comparing the
two byte for byte is the only thing that proves the page serves what was measured. On
`p_ge4_calibration_*` that held on **246 of 246 rows, worst score gap 0.0** — which also
re-proves `field_sharing`'s recolour-is-the-render claim on a population outside its own
tests, since the measure pass recoloured a dumped field and the build did a full render.

**Measured cost**, 2026-08-26, six workers, post-`field_sharing`: 246 units at 1280x720 ss2
in **654 s**, 2.7 s/unit wall and 13.3 s/unit of work. The mix is what moves it — a
field mode amortises its dump over the operator's second pass, a composite has no field and
pays two iteration passes, and the composite tail alone took the marginal rate from 0.8 to
1.8 s/unit. Budget the second render too: the build leg cost about the same again.

**A direct-trap unit is one render and not two**, because `autolevel.applies_to` is `field`
and `composite` — a direct trap is a figure over a flat ground, its tone statistics describe
the ground, and the operator is excluded at the site that decides. Four of
`under_seen_modes`' nine modes are direct traps, so 224 of its 504 units skipped the
operator entirely and 108 of the remaining 280 were actually levelled. Estimate a mixed
sheet by kind, not by unit count.

**The render pool is three workers at below-normal priority** — `CLAUDE.md`'s rule, and the
priority half is now `engine.run`'s rather than a caller's. Measured on `under_seen_modes`,
2026-08-27: the measure pass at six workers ran 297 units in **880 s** (2.96 s/unit wall);
the same pass at three ran its 207 remaining units in **712 s** (3.44 s/unit). Two thirds
of the workers for a sixth more per unit, which is what a leg that has to share a desktop
should be paying. `label build` is serial and is one engine whatever the pool is.


### A blind page is cut and then stripped

The page renders three things that describe a picture rather than being it, and a sheet
that must not editorialize has to lose all three: **`facts`** (the partition, the frame,
`mode · colormap`), **`columns`** (the judge's three cutpoints, printed in the meta line)
and the **caption** on each picture. `finished_source` writes them unconditionally, and
there is no flag — so a blind sheet is cut normally and `sheet.jsonl` is rewritten with
`facts: []`, `columns: {}` and empty captions afterwards.

What that costs is nothing, and the reason is worth stating: `intake._finished_row` reads
only the row's `join`, its `batch` and its `suggestion`, so the display fields are not part
of any verdict. The `join` stays complete and untouched on every row, which is what keeps
the ingest a join rather than a lookup. The manifest carries a `withheld` sentence saying
what came off, because a page with no facts on it and a page whose facts were never cut
look identical a month later.

**The batch name is on the page too**, in the section line, and so is `order`. Neither is
strippable and neither should be: they are what a labeler needs to know which sheet is in
front of them. A batch named after the thing being tested is how a blind sheet stops being
blind — `under_seen_modes` names a population, not a mode or a score.

## A rule answers the mostly-black frames, and nobody is asked again

A location whose frame is mostly the set's own interior renders mostly black, and that
verdict is settled. Over the 306 human verdicts of `run9_plane_depth` and
`mandelbrot_offer_body` (2026-08-19), **every** row at interior fraction ≥ 0.10 was
scored 1, and the highest-scoring keeper anywhere in them sits at 0.0960. So the location
sheet builder excludes a unit at **`interior_fraction ≥ 0.12`** — `sheets.INTERIOR_THRESHOLD`,
rule id `interior_ge12_v1` — before the cut, which on that evidence removes 65% of those
sittings' 1s and not one row a person scored 2 or better, at two renders saved each.

* **It reads a cached statistic and computes nothing.** `units_from_ledger` carries the
  walk's own `interior_fraction` across, and a location plan carries whatever its drawer
  copied in. A unit without the number **serves normally** — the manifest's `screen.measured`
  says how many units the rule could actually read, so "excluded nothing" and "saw nothing"
  are distinguishable. Cached interior at 384×216 ss1 tracks the near-black pixel share of
  the 1280×720 ss2 picture a person judges at r = 0.9999 over those 306 rows.
* **The verdicts stay derived.** Excluded units are written to `excluded.jsonl` in the sheet
  directory — the rule, the threshold, the value that fired it, the batch, and the full
  location — and are **never** written to the label store. An analysis that wants them as 1s
  in a denominator reads them from the rule at the moment it wants them; a stored row would
  be a verdict nobody could un-derive when the threshold moves.
* **It is not the walk's gate.** `discovery.walk.Gates.interior_cap` is 0.30 and decides
  where a walk may stand. This is a build-time decision about a page. Neither moves the other,
  and the sheet rule does not change a walk's gates or caps.
* **One consequence of those two numbers is worth knowing before planning a sheet.** The walk
  refuses at 0.30 and the screen answers at 0.12, so **a location the walk refused for
  `interior_cap` can never be served** — every such row is above the gate and therefore above
  the screen, by construction and not by luck. On run10 that is 11,762 of the run's 13,962
  structural refusals: a page cut over what the gates threw out can hold the other two gates
  and nothing from that one, so its share has to be drawn from `flat` and `occupancy_floor`
  or the sheet comes back a third short.

## One generator, two row sources

This project asks a person two questions, about two different objects — *is this
**place** worth rendering* and *is this **picture** worth keeping* — and they
differ in what a unit is, what gets rendered, and which judge prefills the
suggestions. A `Source` owns exactly those three things. The cut, the ordering,
the ids, the manifest, the row file, the thumbnails, the page and the export are
one implementation underneath both, because two generators is how a project ends
up with two answers to what an export is called, which is a bug nobody sees until
two tabs are open.

A location unit is rendered **twice**: through the canonical map, which is what a
head sees, and through the vivid one, which is what a person judges from — a
crushing palette makes good material look dead, and the verdict is about the
place. A finished-render unit is already a picture, so it is rendered once,
exactly as it is recorded, at the geometry both corpora were collected at.

A picture is named `cut0000` for its position in the **plan** and the `u0001` id
is assigned after the order is fixed, so the id encodes the page position and
nothing else — and re-ordering a sheet costs no render, which is what makes a
long cut resumable. The prefix keeps the two numberings apart on disk: they are
different numbers for the same unit, and without it one reads as the other.

### A revision sheet re-serves rows the store already holds

Re-judging a stored population is the same generator with three things stated by
the plan rather than derived. A unit's own **recipe** and map re-serve the exact
picture a verdict was cast on, so the new verdict keys on that render and lands
as a revision of it. A unit's own **suggestion** prefills the incumbent verdict —
which here is the stored label, not the head's decode, and is the only prefill
that can name a tier the shipped checkpoint cannot reach; the manifest records
`suggested_by`, because a prefill read back as agreement means one thing when a
model made it and another when the labeler did. And a unit's own **batch** keeps
the row's registration: one sheet re-serves rows from several batches at once,
and a row revised under somebody else's batch is a row whose side, anchoring and
draw method changed under it. The head still scores every row and still orders
the page good→bad, because that is what a correction sheet is worth.

`--reuse-renders` takes a picture off the head's render cache where the cache
already holds that spec. The cache names a picture by a digest of everything the
engine is told, so a hit is the same picture and anything different anywhere is
a miss.

A plan unit may also name a **`leveled`** directory — a colormap the autolevel
operator re-baked for one render — and then the sheet renders through that
instead of through the library's copy of the map. That is what lets a batch
screen a picture at the sheet's own geometry and be sure the page serves the same
one: the join is identical either way, so a unit that lost the name would come
back a different picture with the same identity. `curation.manufacture.verify` is
the check that says it did not.

### Which judge prefills a finished-render sheet, and which reading orders it

**The head a sheet is cut for names the STORE, not the model.** One judge reads
both kinds since 2026-08-23 — `curation.floors.SCORING_HEAD` — and it is the only
finished-render head `fetch-weights` brings down. A sheet that loaded
`models/<kind>/<kind>.fp16.pt` was reading a retired checkpoint on a scale nothing
else in this project still speaks, and on a fresh clone it was reading a file that
is not there.

`--order-by` says which reading the page is read good→bad by. `rank`, the
default, is the head's expected tier — the sum of its unconditional cutpoints,
which is what orders a page over the whole scale. `top` is the last cutpoint
alone, and it exists because the one below it saturates: the first production
run's released smooth rows had a median `P(≥3)` of 0.9999, so at the good end of a
page — the end a correction sheet is read from — `P(≥3)` cannot separate two rows
and `P(≥4)` still can. Only the ordering moves; `suggestion_score` on a row is the
expected tier either way.

**Five sites resolve a checkpoint through `floors.SCORING_HEAD`, and a judge
adoption has to re-check all five.** They are `sheets.score_pictures` (this one —
the sheet's prefills), `curation.colorize.Colorizer` (a candidate's verdict at
attempt time), `curation.manufacture` (the screen and confirm cuts),
`curation.rescore` (the whole pool re-read onto the live scale) and
`models.release_floor` (the floor fit itself). Each calls
`render_train.load_checkpoint(ship.shipped_path(judge), …)` off that one constant,
which is what makes "which model reads finished renders" a single edit — and what
makes a flip a five-site consequence rather than a one-line one. `models.
render_glance` is deliberately not on the list: it names `render_train.HEAD`
directly, because its whole job is reading an incumbent against a candidate.

## One ingest, two stores

**A page saves to `labels/<head>.<sheet>.json`, and that is the whole
convention.** The name is the head the sheet was cut for *and* the sheet's own
name, never a generic one and never the head alone: two sheets are open in two
tabs during a session, `labels.json` twice is one file overwriting the other, and
two sheets cut for one judge is the same collision with a worse ending — both
pages number their rows from `u0001`, so a shared drop is either refused for
being short or joined, unit for unit, against the wrong sheet's places. The rig
takes the save itself — `PUT /labels/<head>.<sheet>.json` — so a session
does not end with a file in a download directory somebody has to move, and a
static server that refuses the endpoint gets the same file downloaded under the
same name. The drop is untracked, ignored, and disposable; `label ingest` is what
makes it durable, and it reads the drop by default so it does not have to be told
where the page just wrote.

**`/labels/` is ignored, and the leading slash is the point.** The entry in
`.gitignore` is anchored at the repository root, so it hides the drop directory
and leaves `data/labels/` — the location head's tracked store — alone. Two
directories one path segment apart, one disposable and one the corpus, and an
unanchored `labels/` would have ignored both.

**Export and ingest in the same session.** A drop is only meaningful beside the
sheet it was cut from: units are numbered `u0001` upward *by position* in that
sheet's row file, so `intake.read_sheet` joins each verdict through
`artifacts/sheet/` and nothing else can. Both halves are ignored trees — the drop
under `labels/`, the sheet and its pictures under `artifacts/` — and a rebuilt
sheet renumbers. So a drop whose sheet is gone cannot be ingested, and a drop
joined against a *different* sheet of the same size would bind every verdict to a
plausible picture rather than to its own. Ingest before the sheet moves.

`ingest` exists because a sheet is cut somewhere untracked and its pictures live
somewhere untracked, and none of that may survive as part of what a label means.
It joins each exported unit to its sheet row **once**, and writes a row carrying
the whole join — the place for a location, and the place with the mode, its own
settings and its curve, the map, every knob of the palette pass and the geometry
for a finished render. The sheet says which judge it was cut for and that decides
which store it lands in; `Records` is that difference, spelled once. Both counts
are checked in both directions, a row already in a store is not written twice, a
verdict that changed is a new row rather than an edit, and the pin is asserted
**before** the write and again after it — so the step is safe to re-run, which is
the only reason anybody re-runs it after finding a mistake. Asserting only
afterwards left the store holding rows the suite forbids, once, on the first
attempt at the manufactured rare-colour drop.

**The imported rows of a store may stop short of its scale.** This project judges
on `finished.SCALE`, 1..4 for both kinds, and that is what every page serves and
every head emits. What the source project *collected* each corpus on is a
separate and smaller fact — `finished_import.SOURCE_SCALE`, 4 for smooth renders
and 3 for strange — and it lives on the importer because it is about pages served
years ago rather than about this store. A source row outside its own corpus's
ceiling is a misread file and the import refuses it; a row cast here is held to
`finished.SCALE`. Which is why 145 of the strange store's rows are tier 4 and not
one of them was imported.

### Reading a labelled batch back afterwards

An ingested row carries the place and the verdict, and deliberately not the facts the
sheet printed under the picture — the arm, the band, the walk fate. Reading a batch
back is therefore a three-way join, and each side has exactly one right source:

* **verdicts** come from `store.resolved()` — or `finished.resolved(head)` for the
  two finished-render stores, which is the same rule keyed on the render instead of
  the place — never from the drop and never from the row files directly; latest-wins
  is the resolver's job. The order is `store.order_of`: **`(recorded_at, file,
  line)`**, and **`labeler` is not in it**. Who cast a verdict is on the row and is
  never part of what supersedes what, so two people labelling one unit resolve by
  when rather than by whose name sorts first. Body rows are the ones whose
  `batch` is the sheet's own batch; anchors carry somebody else's and are excluded by
  that test rather than by position.
* **what the page said** — `facts`, `suggestion`, the head's `columns` — comes from the
  sheet's own `sheet.jsonl`, joined on `unit`.
* **what the pixels did** comes from the source walk ledger, joined on the viewport
  triple `(center_re, center_im, width)` as *strings*. They are the engine's own
  shortest round-tripping decimals on both sides, so the match is exact; parsing them
  to float first is how a join starts missing.

A `candidate` row in the ledger caches `interior_fraction`, `occupancy` and the
`escape` spread, which is what makes gate calibration cost nothing: the statistics are
already on disk and no picture has to be rendered again to get them. Two caveats worth
knowing before trusting them. They are measured on the **node render** (384×216 ss1),
not on the sheet's 1280×720 ss2 picture — `interior_fraction` is an area share and
transfers exactly (r = 0.9999 against the near-black pixel share of the canonical
render, over 306 rows), while `occupancy` counts detail tiles and is resolution-bound.
And `occupancy` is **absent on rows refused for `interior_cap`**, which is not missing
data but the refusal order showing through: the frame was thrown out before anything
measured it. Any rate computed over occupancy has a smaller denominator than the sheet,
and the rows it drops are the interior-heavy ones.

## The scale is the corpus's; the class count is the model's

Every judge here is cast on **1..4**, `strange_render` included. Its corpus was
*collected* on three tiers and its head *trained* on three classes, and neither of
those was ever a ceiling on what a person may write down. What a checkpoint can
emit lives in that checkpoint's own config, is read back by whoever loads it, and
moves only when the head is retrained — so the corpus was free to grow a tier the
incumbent could not see, which is exactly what the retrain to four then had to
learn from and what a capped store could never have collected. A training pass
whose recipe cannot express a verdict in its population refuses rather than
mis-fitting its top cutpoint (`finished_train.refuse_inexpressible`) — a 4 handed
to a three-class CORN head is a rank with no task to carry it, so the failure is
a silently mis-fitted top cutpoint rather than a crash.

Two pins hold that decoupling in place and neither of them is the store's scale.
A config beside a checkpoint has to agree with **that checkpoint's own output
width** — `classes - 1` cutpoints in the weights — because a head emitting two
cutpoints while its config claims three is one every reader of its scores
misreads. And a run's config is deliberately **not** re-checked against today's
`finished_train.RECIPES`: a config says what *that* run trained under, so a
retrain that widens the recipe leaves the superseded run readable exactly as it
was, instead of destroying the baseline it is measured against.

## The order is the design

A batch is registered *before* it has rows, because "was a model score in the
selection" is answerable while the population is being drawn and is answered from
memory afterwards. A sheet is cut into an untracked run directory and comes back
as one export holding only what a person actually acted on. Both stores are
append-only: a verdict that changes is a new row, and the canonical reader
resolves latest-wins.

The split is drawn over location groups and shipped as data rather than computed
on demand, so a holdout does not move when the corpus grows. A **group** is a
connected component of "these two would leak into each other", and `groups.py`
calls two locations neighbours only when all three of these hold: the same plane
*exactly* — same partition, same degree, every identifying constant but the seed
`c` equal digit for digit; their `c` within `C_TOLERANCE`; and their frames
overlapping, widths within `NEIGHBOR_SCALE` and centers within `NEIGHBOR_SHIFT`
of the smaller width. The non-`c` axes are exact because a family swept at one
fixed viewport — phoenix's five-hundred-row `p`/`z₋₁` sweep is the case that
forced it — otherwise folds hundreds of different fractals into one group, and
an under-grouped holdout costs the instrument where an over-grouped one only
costs granularity. What is on the
evaluation side is pinned there on its `c`-inclusive coordinate — a re-render
under a fresh identifier is the same place and cannot spend the instrument.

The rig's design is correction mode: a head's own verdict prefilled, the page
ordered good→bad by its score, and a sweep that accepts everything below a chosen
row behind a confirmation. All three judges do this, and the location sheet
consults the same scorer the walk does. `--no-scoring` is the other mode — no
suggestions, no sweep, a seeded shuffle — and it is what an instrument is cut as.
The invariant holds in both modes and is the one worth stating twice: **a
suggestion is not a label**.
