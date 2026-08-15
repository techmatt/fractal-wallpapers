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
corpus_import.py  the one-time import of the source project's label corpus
```

Everything runnable here is a `fractal-wallpapers label` subcommand:

```
label register --batch NAME --method "how the population was drawn"
label build --from-ledger artifacts/walk/walk.jsonl --batch NAME
label serve --sheet artifacts/sheet
label record --sheet artifacts/sheet --labels labels.json --labeler matt
label show
label split --write
```

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
