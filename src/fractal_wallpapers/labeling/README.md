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

**A page that is never exported leaves nothing, and a small page is how that
happens.** The drop is a page's only record: the sheet, the renders and the levelled
maps all survive a closed browser and none of them carries a verdict. So a sitting is
finished when its drops are on disk, not when its servers are stopped — count them
against `label sheets --drops` before tearing one down.
`phoenix_classic_20260903` is the case, and it is the *one-card* half of it that went
missing: the 34-card strange page exported and the single-card smooth page did not,
so 34 of 35 verdicts survive and the last one has to be re-served. Re-serving costs
nothing but the operator's second look — the picture is already rendered, so
`label build` reports `rendered: 0` and serves exactly what was measured.

**The second half of a drop's name is the BATCH, not the sheet directory** —
`store.export_path(manifest["head"], manifest["batch"])` is what both `label serve` and
`label sheets --drops` print. So the collision that name prevents is two *batches* under
one head; two *cuts of one batch* land on the same drop, and `label sheets --drops` shows
them doing it. Re-cutting a page — dropping duplicate places, re-ordering, screening — is
exactly that case, so it is the normal way to arrive here rather than a mistake.

**And the ingest cannot tell which cut the drop came from.** A drop is joined by position,
so a shorter export against a longer sheet of the same batch is accepted: every exported id
is on the sheet, and the units the drop does not name are reported as `not acted on`, which
is what a half-labelled page looks like too. Measured 2026-08-29 on a batch whose 745-unit
re-cut and 998-unit original share one drop: the correct sheet joined 745 of 745 with 21
withheld, and the original joined the same file at `exported 745, not acted on 253` and
offered **515 rows bound to the wrong pictures**, without an error. Match the *unit count*
to the drop before ingesting, and delete or rename the superseded cut once its replacement
is labelled.

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

### Ingesting a NEW `eval_only` batch does not refresh the pin, and the store notices

`label ingest` asserts the pin it *finds*; it never rewrites it. The pin document
(`data/<head>/split.json`) and the evaluation side (`data/<head>/eval_split.jsonl`)
are written by the one-time corpus import and by nothing else, so landing the first
rows of a newly registered `eval_only` batch leaves the store in a state
`tests/test_finished_store.py` rejects two different ways:

* leave the document alone and `eval_only_batches` no longer equals the batches of
  the rows the registry calls pinned;
* extend the pin to every place the new batch touches and the older **training**
  rows already on some of those places are stranded on the wrong side.

A batch registered `eval_only` pins at **batch** granularity here — every row of it is
the evaluation side. That is not the location head's rule, where a seeded draw over
groups decides and registration alone changes nothing; do not carry one store's
intuition to the other.

The resolution is the one the store's own refusal names — *fix the split, never the
pin*. Pin the places that carry no training row, and leave the rest **contested and
unpinned**: an instrument is only pinnable where it is not already spent. Rebuild the
side from the registry with `finished.write_pin`, and assert the new side is a
**superset** of the old before writing, because `write_pin` truncates and a pin that
can shrink is not a pin. Measured on a 200-unit two-store drop: 150 places pinnable,
50 contested.

#### The contested places are the design, and the guard now asserts that design

`test_finished_train.py` asserted `{eval-side places} ⊆ {pinned places}` until
2026-08-30, under the name `test_the_split_is_the_pin_...`. A contested place is
eval-side by its batch's registration while being deliberately absent from the pin, so
that assertion failed on **both** heads and no repair to the pin could close it: the
eligible repair — add only places carrying no training row — has an empty population,
and extending the pin to the contested places moves the failure one line down to the
stranding this section refuses.

It now asserts the containment that actually holds, one way: **the pin is a subset of
the evaluation side**, and **no pinned place carries a training row**. That second one
is the assertion the test exists for and it must always fail loudly. The contested
count is *recorded* rather than asserted — it moves with every batch anybody labels, so
a fixed number there would be a test that fails on ordinary work. Standing on
2026-08-30, read off `finished_train.population`:

| head | pinned | eval-side places | contested | pinned with no eval-side row |
|---|---|---|---|---|
| `smooth_render` | 277 | 300 | **23** | 0 |
| `strange_render` | 180 | 207 | **27** | 0 |

50 contested, which is `ca42265`'s own number. Do not repair the pin to move it.

#### `eval_only` outranks the clock, and that is what stops the evaluation side shrinking

The two rules key on different things. A *place* is pinned at the location, but which
side a *row* is on is read off its batch's registration, and a resolution keeps one row
per **render key**. While that resolution ordered on the timestamp alone, a training
batch landing on a render key an `eval_only` batch already wrote **superseded it**, and
where that was the place's only eval-side row the place stopped being eval-side at all.
It happened twice: on 2026-08-29 two `sparse_mode_head_top` rows beat two
`seated_and_head_top` rows by **one second** each, and `strange_render` went from 207
eval-side places to 205 with nothing red and no writer intending it. The tiers agreed
in both cases, so nothing was corrupted — but the mechanism does not depend on their
agreeing, and `finished.assert_pin_holds` cannot see it: it asks whether a training row
sits on a *pinned* place, and a contested place is by construction not pinned.

Closed on 2026-08-30, **reader-side and with no stored row touched**.
`store.resolution_order` puts a row from a batch registered `eval_only` after every
other row about the same key, so the evaluation side wins a contested key whatever the
clock says; the clock still decides between two rows of the same side.
`store.resolve` and `finished.resolve` take the registry as `known` and
`store.resolved` / `finished.resolved` — the canonical readers — always pass their own
store's. A caller holding rows and no store gets the clock alone, which is stated at
the function rather than assumed. Restoring the rule moved **two rows** across both
stores, neither of them changing a tier, and put `strange_render` back to 207
eval-side places.

## What cutting a sheet costs, and why the number moves so much

A location unit is **two renders at 1280×720 ss2**, and that is the whole bill —
scoring the cut page afterwards is a minute whatever the page holds.

**The label geometry has one spelling and it is `sheets.LABEL_RESOLUTION`**
(`labeling/sheets.py`), with `LABEL_SUPERSAMPLE` and `LABEL_FILTER` beside it: what
both finished-render corpora were collected at, and therefore what a finished-render
sheet renders at — a picture judged at a different geometry is a verdict about a
different picture. `curation/shrinkage.py` imports it and **nothing else in the tree
does**, which is what makes it the single spelling rather than one of several.
Grepping the numbers instead lands on the wrong constant: `sheets.py` holds
`SHEET_RESOLUTION`/`SHEET_SUPERSAMPLE` at the *same* 1280×720 ss2 for the **location**
sheet, and `curation/manufacture.py` a third at those numbers again. They agree today
and nothing makes them; a change to what a person judges a finished render at is a
change to `LABEL_RESOLUTION` alone.
 Build it in the
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

Since 2026-08-27 that is enforced rather than remembered: `finished.check` asks
`hunt.kind_of` which store a row's mode routes to and refuses the row if it is not the
store being written. `rare_palette` is the batch that bought the guard — 40 of its
resolved rows are `smooth` and sit in `strange_render`. They stay there, because an
original is never modified; `finished_train.population` derives the exclusion at the
read instead. The numbers are in
[`data/strange_render/README.md`](../../../data/strange_render/README.md).

**A mode can route to the other store without being that mode.** A modulate —
`itinerary`, and `tail_itinerary` beside it — shifts its base's palette position by
an address field, and where that field has no span the shift is zero everywhere and
the picture is the `smooth` field spent by rank — *bit for bit*, not merely similar.
So such a row is the smooth judge's, whatever its `mode` says, and the rule names
neither mode: it is about the modulate shape. `finished.routes_to` is the call that knows: it takes the render's own
identity to `coloring.texture_flat`, the tracked register of which renders that is
true of, and hands the answer to `routed_to`. `check` uses it at the writer and
`finished_train.population` at the read, which is the same two-sided arrangement the
paragraph above describes — and for the same reason, since the rows already on record
are originals and are never rewritten.

**And a pool row's own `texture_flat` does not survive the trip to label geometry.**
`coloring.texture_flat.KEYED` holds `resolution` and `supersample`, so the register
entry a candidate earned at 640x360 ss2 is not the key the sheet's 1280x720 ss2 join
computes — `flat_for` misses, reads `False`, and `routes_to` sends the row to the
strange store while `hunt.kind_of` off the ledger row's stored flag sends it to the
smooth one. The two disagree exactly on the degenerate modulates, and `check` refuses
at the writer, after the page has been cut and labelled. So **a sheet drawn out of the
pool routes by `finished.routes_to` on the join it is about to render**, never by
`kind_of` on the ledger row. `phoenix_q3q4_20260903` is where this was found: its
top-200 draw held two `itinerary` rows carrying `texture_flat: true`, which the ledger
routes smooth and the sheet routes strange. The way to make the two agree is to
measure the modulate at label geometry and extend the register, and **since
2026-09-03 the ingest does exactly that**.

**"Ask the routing of the join" is only right when the join has been measured, and
on a MISS it has not been — it has been defaulted.** `flat_for` answers `False` for
an identity the register does not hold, which is `strange_render`, so a modulate
that really is flat at 1280x720 ss2 is written to the strange store *without a
refusal*: `check` compares two answers and both of them say strange. The disagreement
the paragraph above describes is the visible half of the failure and the quiet half
is this one. It fired twice at checkpoint 103, and it was 23 of the 224 label rows in
a mode with a texture at the time of the fix.

So `finished.append` — THE writer, and the one place a render identity is new — passes
`extend=True` down through `check` to `routes_to`, and a MISS there runs the engine's
span test at the row's own geometry through `coloring.texture_flat.extend_with`,
**appends** the entry to the tracked register and routes on the measurement. The
register self-extends at ingest instead of needing a backfill that has to find the
same rows again later. It never rewrites an entry — a held key comes back off the
register with no render, because a second measurement of one identity is a second
answer to a question that has one — and it never re-keys a label row. A failed span
test **refuses**, rather than letting a row route on the default while looking like a
measurement.

`extend` is off for every reader and that is load-bearing: `routes_to` is called per
row by `finished_train.population` over both stores, and a default that rendered on a
miss would turn a corpus read into a render leg, silently, on a machine that may
already be running one.

**The 23 already in the store were probed on 2026-09-03 and 13 of them measured FLAT.**
The forward fix repairs the next ingest and nothing already written, so the misses were
measured at their own geometry through `coloring.texture_flat.extend_with` and the
entries appended. That fixes one reader and not the other, and the split is the thing
to know: `finished_train.population` asks `routes_to`, so the appended entries drop
those rows out of the strange head's training population on their own — but
**`finished.resolved` decides a row's kind by which store's directory it was read from**
and never consults the register at all, so no measurement can re-attribute a row that is
already on disk. Each flat row therefore got a **revision row** in the smooth store: the
same verdict and the same render identity under its own batch — both batches were
already registered in both stores with identical flags — carrying a `revision` block
naming the strange original's file, line and recorded time. The originals stay exactly
where they are, none was modified, deleted or re-keyed, and the strange store's row
count did not move. None of the thirteen sits at a pinned place and
`finished.assert_pin_holds` was asserted on both heads before and after.

**120 of the 224 are flat and only 13 carry a revision.** The other **107** were
measured before this and are the accepted older arrangement — excluded from the strange
head's training by `population` and invisible to the smooth head — mostly
`itinerary_promotion` (59) and `sparse_mode_head_top` (40). So the two halves of one
population are now read two different ways, and extending the revision to the 107 is a
decision rather than a repair.

**Budget an ingest's probes by the partition and not by a constant.** The 23 cost
**435.9 s** between them, not the ~40 s a flat 1.7 s a probe predicts: the `judge_band`
rows ran 1.3-6.0 s each and the `phoenix:classic` rows ran **27-111 s**, because that
plane's admitted places carry 12k-22k iterations. A sheet cut from a deep partition can
put minutes of render inside what reads as a record write.

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

**A measure pass can BE the sheet's render, at three workers instead of one.** The
build renders serially in-process, and `cut` skips a unit whose picture is already on
disk — that is the resume path, and it is also a way to do the whole page in
parallel. Render each plan unit at label geometry through `colorize.render(level=True)`
into `<sheet dir>/full/<sheets.cut_name(i)>.jpg`, where `i` is the unit's index in
the plan **file**; `finished_source` sets no `screen`, so nothing reorders or drops a
unit before the cut and that index is stable. `label build` then reports
`rendered: 0` and serves exactly what was measured. `sparse_mode_head_top`
(2026-08-29) did 998 units this way in 47 min at three workers against about 35 min
serial for the wrong pictures, and the operator acted on **301 of 998, 30.2%**.

**So it is two renders a unit, and the second one is the check.** The measure pass makes the
picture and the levelled map; `label build` renders again from the plan; and comparing the
two byte for byte is the only thing that proves the page serves what was measured. On
`p_ge4_calibration_*` that held on **246 of 246 rows, worst score gap 0.0** — which also
re-proves `field_sharing`'s recolour-is-the-render claim on a population outside its own
tests, since the measure pass recoloured a dumped field and the build did a full render.

**How much of a pool sheet the operator actually moves: 43%.** On
`seated_and_head_top` (2026-08-27, 200 candidate-ledger rows at 1280x720 ss2) the
operator was *offered* 192 of the 200 — the other eight are direct traps, which
`autolevel.applies_to` excludes at the site that decides — and it **acted on 85**.
Those 85 are rows a sheet built straight off the plan would have served as a
different picture under the same identity, and no number on the ledger row says
which 85 they are. So a measure pass is not optional on a sheet cut out of the
candidate pool: skipping it is not a rounding error, it is two fifths of the page.

**Measured cost of a correction sheet cut over the candidate pool**, 2026-08-27,
`seated_and_head_top`: the measure pass ran 200 units in **301 s wall** at three
workers (1.50 s/unit wall, 4.46 s/unit of work) and the two `label build` legs cut
103 + 97 units in about **250 s** between them. That is ~2.8 s/unit for the whole
two-pass arrangement against the 5.4 s/unit `p_ge4_calibration_*` cost below, and
the difference is the material rather than the machine: these are field-mode rows
at a mean 16,541 maxiter, so the operator's second pass is a recolour off a dumped
field and the eleven composite modes that dominate the older number are barely
present. **Estimate a sheet by its mode mix, not by its unit count** — the same
claim the four-row table above makes about maxiter.

**And within one mode, estimate it by where in the pool the draw came from.**
`smooth_decision_bands` (2026-08-29) is 500 rows of one mode, `smooth`, all
field, and its measure pass cost **5.90 s a unit** at three workers — 2,953 s for
the page — against `sparse_mode_head_top`'s 2.8 s a unit over nine modes four days
earlier. Nothing about the machine changed. The draw did: a sheet cut from the
**top** of the pool selects deep frames, and a deep frame is a high maxiter. There
is no mode mix left to explain a 2× when the sheet is single-mode, so budget a
top-of-pool sheet at roughly twice a sheet drawn across the same pool. The
operator acted on **267 of 500, 53.4%**, and `label build` reported
`rendered: 0, reused_from_cache: 0`.

Both renders verified byte for byte on **200 of 200 rows**, and the two readings
of the same picture at the two geometries are on every row (`selected_on` against
`columns`): mean shift `-0.0035` on `P(>=4)` over the seats and `-0.0000` over the
top-scored control, with single rows moving as far as `+0.27` and `-0.20`. The
judge is regime-stable in the *mean* and not per row, which is exactly why both
readings travel rather than one.

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


**A varied-`phoenix` pool sheet is cheap, and the pinned plane's 17x does not
carry over.** `phoenix_q3q4_20260903`, 2026-09-02: 200 units at 1280x720 ss2,
mean maxiter 10,706, measure pass **726.4 s wall at three workers** — 95 smooth
units in 123.6 s (1.39 s/unit wall, 4.11 s/unit work) and 105 strange in 602.8 s
(6.15 s/unit wall, 18.10 s/unit work). `LEG_phoenix_classic_supply` priced
`phoenix:classic` at **56.9 s a candidate** against 3.2 for the parameter planes,
and reading that as "phoenix is dear" over-budgets this sheet by an order of
magnitude: that leg's material sat near 1e-4 at 12,243-21,702 maxiter, and varied
`phoenix` drawn at the judge's own q3/q4 crossing does not.

**And the mode mix moves it 15x within one sheet.** Measured s/unit of work over
the 187 units the full pass made: `stripe` **44.2**, `smooth_angle_min` 45.5,
`direct_trap_lines` 43.0, `direct_trap_screen` 25.3, `direct_trap_multiply` 21.3,
`smooth_stripe` 19.9, `gaussian_int` 17.8, `tia` 14.9, `smooth_mean_angle` 13.1,
`curvature` 10.0, `exp_smoothing` 9.2, `itinerary` 7.8, `smooth` **4.1**,
`smooth_curvature` 4.6, `threads` 3.0.

**A stride pilot is not a mode sample, and this is the cheap way to learn it.**
Seven units taken at stride 16 off the strange plan priced it at 1.93 s/unit wall;
the full pass came in at 6.15, because those seven drew `exp_smoothing`,
`gaussian_int`, `tia` and one direct trap and missed all nineteen composites. A
pilot over a sheet whose cost is a mode mix has to be **stratified by mode**, not
strided over the file — one unit of each mode present is thirteen renders here and
would have priced the page inside 20%.

**The render pool is three workers at below-normal priority** — `CLAUDE.md`'s rule, and the
priority half is now `engine.run`'s rather than a caller's. Measured on `under_seen_modes`,
2026-08-27: the measure pass at six workers ran 297 units in **880 s** (2.96 s/unit wall);
the same pass at three ran its 207 remaining units in **712 s** (3.44 s/unit). Two thirds
of the workers for a sixth more per unit, which is what a leg that has to share a desktop
should be paying. `label build` is serial and is one engine whatever the pool is.


**A roster-wide band draw prices at four times a single-plane one, and the split is
the mode mix.** `judge_band_20260903` (2026-09-03) measured 300 units at three
workers in **899.8 s**, zero errors: `smooth_render`'s 123 in 146.3 s (**1.19
s/unit wall**, 3.53 s/unit work) and `strange_render`'s 177 in 753.5 s (**4.26
s/unit wall**, 12.66 s/unit work). The smooth half sits on
`phoenix_q3q4_20260903`'s 1.39 despite being drawn from the top of its band across
eight partitions, so a top-of-pool draw is not dear by itself — what is dear is
composites, and the strange sheet's sixteen modes cost 3.6x the smooth sheet's one
over the same geometry. The operator re-baked a map on **107 of 300** (45 smooth,
62 strange). Both `label build` legs reported `rendered: 0, reused_from_cache: 0`,
and 128 units re-rendered from the plan afterwards — every levelled one — matched
byte for byte.

**The pinned plane's own sheet price, measured: 54.1 s a unit at three workers.**
`phoenix_classic_20260903` (2026-09-03) measured 34 strange units in **1,838 s**
wall and 5,325 s of work — 156.6 s of work a unit, which is **26x**
`sparse_mode_head_top`'s 2.8 and 9x `smooth_decision_bands`' 5.9. This is the
`phoenix:classic` 17x arriving at the sheet: the same material the candidate leg
priced at 35.3 s a candidate at `640x360ss2`, re-rendered at four times the
pixels. Inside the page the spread is 9x — `direct_trap_screen` 41-45 s against
`threads` and `smooth_mean_angle` at 331-368 — so the mode-mix rule below still
holds; what changes is the constant. The one smooth unit cost 16.7 s. **Budget a
pinned-plane sheet at about a minute a card, and a parameter-plane sheet at a few
seconds**, and do not carry either figure across.

The operator was offered **21 of 34** (the other 13 are direct traps and the
modes `autolevel.applies_to` excludes) and **acted on 11**, 32.4% of the page —
between `seated_and_head_top`'s 43% and nothing, on a population an order of
magnitude dearer. Both builds reported `rendered: 0, reused_from_cache: 0`.

**Write the operator's `leveled` directory back into the plan before the build.**
`colorize.render` names it `<stem>.leveled` beside the picture and a plan that
does not carry the key renders through the library's base map instead: the build
itself will not notice, because `cut` skips a unit whose picture is already on
disk and reports `rendered: 0` either way. The gap only opens when somebody
rebuilds the sheet after the pictures are gone, and then it is a different picture
under the same identity on every levelled row — 107 of 300 here. `judge_band`'s
plans were repaired from `measure.json` and re-verified before the byte-for-byte
check, which is the check that would have caught it.

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
batches' 1s and not one row a person scored 2 or better, at two renders saved each.

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

### A swept row and an agreeing verdict are the same row afterwards

The sweep is the only path by which a suggestion becomes a label, and it writes
`scores[unit] = row.suggestion` — the *tier*, with nothing beside it. So the drop
carries `{"u0137": {"score": 3}}` whether a person looked at that picture and
agreed or accepted it from a hundred rows away, `intake.rows_of` stamps one
`recorded_at` on the whole ingest, and the stored row's `suggested` is the only
column that can disagree with `score`. **A row where they differ was adjudicated;
a row where they match is not evidence about the head**, and no count of
agreements read off a swept sheet is an agreement rate.

What survives is a bound, and it is worth taking because it is free. The sweep
fills unlabeled rows from the current position **to the end** and never
overwrites, so on a page a labeler walked top-down the swept rows are a
contiguous **suffix**. The last position carrying an override is therefore a
floor on the hand-cast prefix, and every row after it is indistinguishable from a
default. On `under_seen_modes` that is position 269 of 504: 161 overrides, none
below 269, and all 235 rows after it agreeing exactly. A page ordered by a score
makes the prefix the head's own top, which is the population a statistic about
the head wants anyway — and it makes the suffix's tier distribution the head's
rather than a person's, so a sheet whose head never suggests a 1 comes back with
every 1 it holds inside the prefix.

The fix, when a session needs to be able to tell them apart, is a second sheet
or a second pass and not a flag: nothing in the drop, the sheet or the store
records which button produced a tier.

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

#### A slice tag survives ingest only as a UNIT-ID BLOCK

A draw made of several populations wants the population on the stored row, and
the obvious places do not carry it: `intake._finished_row` writes the join, the
batch, the sheet name, the unit and the suggested tier, so `facts` and
`selected_on` die with the sheet directory — which is untracked and disposable.
`section` does not reach the store row either.

What survives is the **id**, and `section` is what shapes it. `build` fixes the
order before it numbers anything, `finished_source.order` sorts sections in the
order the plan introduced them and each good→bad inside, so a sectioned plan
comes back as contiguous `u####` blocks, one per section. Write the ranges down
beside the batch — `data/batch_caveats.md` is where — and a per-slice read off
`finished.resolved(head)` is a comparison on the unit id and needs nothing else.

The cost is that the page no longer reads good→bad end to end: it reads
good→bad *within* each block. `judge_band_20260903` is the worked example, at
three slices over two sheets.

## Re-rendering a stored row is `renders.spec_of`, never `colorize.render`

A finished-render row carries its whole join, so drawing its picture again is
`models.renders.spec_of` handed that join and nothing else.
[`curation.colorize.render`] is **not** that path and cannot be made into it: it
builds its own recipe — `colorize.CURVE`, `finished.recipe(mirror=colormap not in
cyclic)`, empty `mode_params` — because it exists to *make* a candidate rather
than to reproduce one, and a caller cannot hand it a curve or a palette pass.
Over the `strange_render` store **2,302 of 3,990 rows (58%)** name a curve, a
trap setting or a palette pass that is not the one it would build, so a page that
re-renders through it serves a different picture under the same identity for well
over half its rows. Measured 2026-08-29; the shape of it is that the maker-era
corpora swept trap settings and gammas and this repository's own hunts do not.

The **operator** half of `colorize.render` is still the thing to copy, and it is
short: `autolevel.maybe_level` around the render, with
`autolevel.overriding_colormap` writing the re-baked map into a directory the
second `engine.run("render", …)` is pointed at through `colormap_dir`. Note what
it does not cover — `autolevel.applies_to` is `field` and `composite` only, so
the four `direct_trap_*` modes and the two modulates get no operator pass **by
kind**, which is a third of the strange roster and is not a measurement about those
pictures.

Every one of those 3,990 rows resolves through `spec_of`, and every one of the
671 colormaps they name is in the library. A row that will not resolve is
therefore a real fault rather than a standing gap in the imported corpora.

## A label store and the candidate ledger barely overlap

**709 of the 4,030 resolved `strange_render` renders join a candidate-ledger row**
(2026-08-29), and the join is [`curation.retention.render_key_of`] — the recipe,
never the regime. The other 3,321 are the maker-era import and the separately
manufactured sheets, which were never candidates here. Two things follow. A
per-mode reading that needs the judge's `P(≥4)` on a *labeled* row cannot get it
off the ledger sidecar for five rows in six, and has to re-score the picture. And
the ledger's third protection — `candidate_ledger.RETAINED_LABELED`, a row a
label row joins to survives the prune whatever the rank says, and now keeps its
picture with it — is a promise about the rows that join: on the 709 that do,
none is missing its picture, and the remaining 3,321 have no ledger picture to
keep.

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
