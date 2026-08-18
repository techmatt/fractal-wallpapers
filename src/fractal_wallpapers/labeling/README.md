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
label build --from-plan artifacts/promotion.jsonl --head strange_render --batch NAME
label serve --sheet artifacts/sheet
label ingest --sheet artifacts/sheet --labeler matt --write
label show
label split --write
```

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

A picture is named for its position in the **plan** and the `u0001` id is
assigned after the order is fixed, so the id encodes the page position and
nothing else — and re-ordering a sheet costs no render, which is what makes a
long cut resumable.

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

**A page saves to `labels/<head>.json`, and that is the whole convention.** The
name is the head the sheet was cut for, never a generic one: two sheets are open
in two tabs during a session, and `labels.json` twice is one file overwriting the
other. The rig takes the save itself — `PUT /labels/<head>.json` — so a session
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
row behind a confirmation. The two finished-render judges do this. No location
head exists here yet, so that sheet serves a seeded shuffle with no suggestions
and no sweep. The invariant holds in both modes and is the one worth stating
twice: **a suggestion is not a label**.
