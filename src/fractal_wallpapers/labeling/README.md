Collecting human taste: the labeling rig and the label store it writes to.

```
store.py          the paths, the one writer, the one reader — nothing else opens the records
registry.py       what generated a batch, registered before the batch has rows
groups.py         which locations would leak into each other, and are held out together
split.py          the seeded draw over those groups, shipped as data
pins.py           the evaluation pin, asserted on the location coordinate
sheets.py         cut a sheet, render each unit twice, record what comes back
server.py         serve one sheet, to one browser, on one exclusively-bound port
page.html         the page: two renders, four keys, one export
export_control.js what an export is called and where it goes — one file, every page
finished.py       the finished-render stores: one per judge, keyed on the picture
intake.py         a page's export resolved against its sheet, appended as rows
corpus_import.py  the one-time import of the source project's label corpus
```

Everything runnable here is a `fractal-wallpapers label` subcommand:

```
label register --batch NAME --method "how the population was drawn" [--head smooth_render]
label build --from-ledger artifacts/walk/walk.jsonl --batch NAME
label serve --sheet artifacts/sheet
label record --sheet artifacts/sheet --labeler matt
label ingest --sheet scratch/a_sheet --labeler matt --write
label show
label split --write
```

**A page saves to `labels/<head>.json`, and that is the whole convention.** The
name is the head the sheet was cut for, never a generic one: two sheets are open
in two tabs during a session, and `labels.json` twice is one file overwriting the
other. The rig takes the save itself — `PUT /labels/<head>.json` — so a session
does not end with a file in a download directory somebody has to move, and a
static server that refuses the endpoint gets the same file downloaded under the
same name. The drop is untracked and disposable; `record` and `ingest` are what
make it durable, and both read it by default so neither has to be told where the
page just wrote.

`ingest` exists because a finished-render sheet is cut somewhere untracked and
its pictures live somewhere untracked, and none of that may survive as part of
what a label means. It joins each exported unit to its sheet row **once**, and
writes a row carrying the whole join: the place, the mode with its own settings
and its curve, the map, every knob of the palette pass, and the geometry. Both
counts are checked in both directions, a row already in the store is not written
twice, and a verdict that changed is a new row rather than an edit — so the step
is safe to re-run, which is the only reason anybody re-runs it after finding a
mistake.

The order is the design. A batch is registered *before* it has rows, because
"was a model score in the selection" is answerable while the population is being
drawn and is answered from memory afterwards. A sheet is cut into an untracked
directory and rendered twice per unit — the canonical map a head will see, and
the vivid one a person judges from — and it comes back as one `labels.json`
holding only what a person actually acted on. `record` is the one path into the
store, and the store is append-only: a verdict that changes is a new row, and the
canonical reader resolves latest-wins per location.

The split is drawn over location groups and shipped as data rather than computed
on demand, so a holdout does not move when the corpus grows. What is on the
evaluation side is pinned there on its `c`-inclusive coordinate — a re-render
under a fresh identifier is the same place and cannot spend the instrument.

The rig's design is correction mode: a head's own verdict prefilled, the page
ordered good→bad, and a sweep that accepts everything below a chosen row behind a
confirmation. No head exists here yet, so the page serves a seeded shuffle with
no suggestions and no sweep. The invariant holds in both modes and is the one
worth stating twice: **a suggestion is not a label**.
