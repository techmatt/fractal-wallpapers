Collecting human taste: the labeling rig and the two stores it writes to.

```
store.py          the location records: the paths, the one writer, the one reader
registry.py       what generated a batch, registered before the batch has rows
groups.py         which locations would leak into each other, and are held out together
split.py          the seeded draw over those groups, shipped as data
pins.py           the evaluation pin, asserted on the location coordinate
finished.py       the finished-render stores: one per judge, keyed on the picture
sheets.py         THE generator: two row sources, one cut, one manifest, one page
server.py         serve one sheet, to one browser, on one exclusively-bound port
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
sheet is open — the bind is exclusive, so a clash fails loudly instead of serving half the
images out of the other sheet's directory:

```
fractal-wallpapers label serve --sheet artifacts/graduation_sheet --port 8021
```

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

`ingest` exists because a sheet is cut somewhere untracked and its pictures live
somewhere untracked, and none of that may survive as part of what a label means.
It joins each exported unit to its sheet row **once**, and writes a row carrying
the whole join — the place for a location, and the place with the mode, its own
settings and its curve, the map, every knob of the palette pass and the geometry
for a finished render. The sheet says which judge it was cut for and that decides
which store it lands in; `Records` is that difference, spelled once. Both counts
are checked in both directions, a row already in a store is not written twice, a
verdict that changed is a new row rather than an edit, and the pin is asserted
after the write — so the step is safe to re-run, which is the only reason anybody
re-runs it after finding a mistake.

## The scale is the corpus's; the class count is the model's

Every judge here is cast on **1..4**, `strange_render` included. Its corpus was
*collected* on three tiers and its head *trained* on three classes, and neither of
those was ever a ceiling on what a person may write down. What a checkpoint can
emit lives in that checkpoint's own config, is read back by whoever loads it, and
moves only when the head is retrained — so the corpus was free to grow a tier the
incumbent could not see, which is exactly what the retrain to four then had to
learn from and what a capped store could never have collected. A training pass
whose recipe cannot express a verdict in its population refuses rather than
mis-fitting its top cutpoint.

## The order is the design

A batch is registered *before* it has rows, because "was a model score in the
selection" is answerable while the population is being drawn and is answered from
memory afterwards. A sheet is cut into an untracked run directory and comes back
as one export holding only what a person actually acted on. Both stores are
append-only: a verdict that changes is a new row, and the canonical reader
resolves latest-wins.

The split is drawn over location groups and shipped as data rather than computed
on demand, so a holdout does not move when the corpus grows. What is on the
evaluation side is pinned there on its `c`-inclusive coordinate — a re-render
under a fresh identifier is the same place and cannot spend the instrument.

The rig's design is correction mode: a head's own verdict prefilled, the page
ordered good→bad by its score, and a sweep that accepts everything below a chosen
row behind a confirmation. All three judges do this, and the location sheet
consults the same scorer the walk does. `--no-scoring` is the other mode — no
suggestions, no sweep, a seeded shuffle — and it is what an instrument is cut as.
The invariant holds in both modes and is the one worth stating twice: **a
suggestion is not a label**.
