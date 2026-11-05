Collecting human taste: the labeling rig and the stores it writes to.

```
store.py          the location records: the paths, the one writer, the one reader
registry.py       what generated a batch, registered before the batch has rows
groups.py         which locations would leak into each other, held out together
split.py          the seeded draw over those groups, shipped as data
pins.py           the evaluation pin, asserted on the location coordinate
finished.py       the finished-render stores: one per judge, keyed on the picture
attributes.py     the location-attribute stores (`spiral`, paired `repeat_ab`)
gallery_grade.py  1..4 GIVEN the bar was cleared: an order inside a gate's own top
sheets.py         THE generator: two row sources, one cut, one manifest, one page
server.py         serve one sheet on the first free port at or above --port
page.html         the page; export_control.js names and places its export
intake.py         THE ingest: a page's export resolved against its sheet, into a store
finished_import.py the one-time import of the source's two finished-render corpora
```

`finished_import` is **not** on a new label's path (`label build` → page → `label ingest` →
`finished.append`).

```
label register --batch NAME --method "how it was drawn" [--head H] [--score-unconditioned]
               [--anchored] [--eval-only] [--why "..."]
label build (--from-ledger L | --from-batch B | --from-plan P) --batch NAME [--head H]
            [--order-by rank|top|plan] [--rejection] [--reuse-renders] [--workers N]
            [--seed S] [--limit N] [--out-dir artifacts/sheet] [--no-scoring]
label sheets [--under artifacts] [--drops]
label serve --sheet artifacts/sheet [--port 8010]
label ingest --sheet artifacts/sheet --labeler matt [--labels FILE] --write
label pin --head spiral --from-plan <plan> --batch NAME --reserve N --seed S --write
label show
label split [--seed 0] [--share 0.20] --write
```

Without `--write`, `ingest`, `pin` and `split` print their plan and write nothing.

## The third kind of sheet: a location attribute

An **attribute** store asks what a place *is* (`spiral` / `not_spiral`) in named classes.
No judge reads the page, the order is a seeded shuffle, and a plan's prefill is a hint
(`prefill_note`). The page casts numbers; `label ingest` turns each into a class
through the manifest's `classes` and `words`.

### Reserving part of a sitting

`label pin` writes a seeded uniform sample of a plan's units to the attribute store's
`eval_split.jsonl` **before the sitting**, in the one batch so no card reveals them. Their
verdicts are collected; the pin forbids training on them.

### A PAIRED attribute: one tile, two renders, a comparative scale

`repeat_ab`'s unit is two pictures; `Attribute.paired` routes `label build` through
`sheets.comparison_source`. A unit is one composite (`sheets.composite`), the side order is
fixed and recorded under `render.sides`, the judge's reading of both halves travels under
`reading`, and a unit stating no prefill is refused. `--reuse-renders` is refused.
⚠ **A comparative ordinal is not a tier** (`data/repeat_ab/README.md`).

```
fractal-wallpapers curate repeat-ab plan --name <batch> --seed <seed> --units 250
fractal-wallpapers label build --head repeat_ab --batch <batch> \
    --from-plan artifacts/curation/repeat_ab/<batch>/plan.jsonl --out-dir artifacts/sheet/<batch>
```

## The fourth kind of sheet: a gallery grade

`--head gallery_grade` asks how good a finished picture is **given that the render judge
let it through**, at `finished_source`'s geometry. By default the page is blind: no
prefill, a seeded shuffle, no `facts`, caption or `columns`. The judge's reading travels
unrendered under `reading`, beside `drawn_as`. **No batch here can be eval-eligible**
(`data/gallery_grade/README.md`; `data/batch_caveats.md`'s *NEVER-AN-INSTRUMENT*).

### Once the store has a head, the same sheet cuts as a correction page

A plan stating `suggestion`/`suggestion_score` per unit cuts a correction page (prefilled,
good→bad, sweep offered); there is no flag. The prefill is the fine head's reading of the
**candidate** at 640×360 ss2 (`sheets.GRADE_CORRECTION_NOTE` says so). A row the head
cannot read carries none: `sheets.stated_suggestions` refuses the mix unless `gaps` names
why, and unsuggested rows sort last (`curation.solve.at_fine_bar`). A row's draw block
survives ingest inside `selected_on`, which `intake` copies whole.

### Keep the plan

A row carries `leveled` as a boolean, not the directory, so the plan is the only thing
that rebuilds a levelled picture as judged; sheets are regenerable, plans are not.
`gallery_grade.plan_paths()` is the accessor. The label protection holds a graded row's
candidate in the pool (`curation/README.md`'s *What is kept, and why each rule is the
rule it is*).

### A REJECTION pass is a correction page whose population is not being reviewed

`label build --head gallery_grade --rejection` over a `curate veto sheet <stamp>` plan
collects the veto (`curation/GALLERY.md`'s *The veto*): only bad tiles are marked, so **the
sweep is off** (`Source.sweep`; every manifest carries `sweep`, absent meaning true; the
page hides and refuses it). `sheets.GRADE_REJECTION_NOTE`: *a tile you leave alone is NOT a
label*. `tests/test_veto.py` holds it.

### Cutting a sheet on the render pool

`--workers N` cuts on threads; about 3.7 s a picture on three, so 1,000 tiles is an hour.
Default 1 (CI); the box's ceiling is three.

## Serving a sheet to label

A sheet directory's name need not be its batch: find it with `label sheets --drops`. Serve
one sheet per port (8020, 8021, …; default 8010), backgrounded.
**`--port` is where it starts looking**: on a clash it walks upward, so **the printed URL
is the only thing that says where a sheet is**. Check `/sheet.jsonl` returns 200
before handing it over. Pictures are `cut####`, not unit ids.

### Where the labels land

Saving writes `labels/<head>.<batch>.json` (`store.export_path`). Serving is not ingesting.
**`labels/` is an inbox of what is unprocessed**: `label ingest --write` ends by moving the
drop to `labels/archive/` (`store.archive_export`, last; a repeat name becomes
`<name>-2.json`; a `--labels` file outside the inbox stays). Moved, never deleted, and a
spent drop re-ingested can revert later verdicts. A sitting is finished when its drops are
on disk: a page never exported leaves nothing.

#### And the ingest cannot tell which cut the drop came from

Two cuts of one batch share a drop name, and a drop joins by position: a shorter export
against a longer sheet is accepted with every row on the wrong picture. **Match the unit
count before ingesting**; retire a superseded cut once its replacement is labelled.

#### A hand-renamed drop is the working answer to one batch cut into several sheets

Save each sheet's export under its own name and run `label ingest --sheet <dir> --labels
<file>` per sheet, oldest first. Check no two drops are identical and each count matches one
cut; on a score-ordered page, position against verdict is strongly negative when bound
right. Each row records its `sheet`.

#### Cut a batch into sheets of UNEQUAL size

Equal cuts are interchangeable by count and by every aggregate. On a shuffled page use
units already holding a verdict as the check; two blind pages want different batches.

## Degree 6 is never labelled, and every door refuses it

**No row on `multibrot6` or `julia:multibrot6` is ever labelled** (Matt's ruling): degree 6
is the mining loop's generalization test, so everything label-fed is empty for it and its
roots come from the viewport sampler alone. The list is `supply/partitions.NEVER_LABELLED`,
and four doors refuse a row on it:

- `sheets.build`, **before** a directory is made or a picture cut (`SheetError`);
- `label ingest` (`intake.run`), before a row is built (`IntakeError`);
- `store.check` and `finished.check`, the two writers' row checks, so an import or a
  backfill that skips the ingest cannot land one either.

It is **refused, not withheld**: such a verdict is a sheet that should never have been cut.

## A verdict cast on a pinned location is WITHHELD, not written

A finished store's evaluation side is an `eval_only` batch, cut blind, pinned on the
*location*. Another batch's verdict at a pinned place may neither train nor join it, so
`label ingest` counts it as `withheld on a pinned location` and leaves it in the export
(pairs go whole). The pin is asserted before the write and after
(`asserted_before_writing`); `tests/test_finished_store.py` holds the invariant.

### Ingesting a NEW `eval_only` batch does not refresh the pin, and the store notices

The ingest never rewrites `data/<head>/split.json` or `eval_split.jsonl`. A finished store
pins by **batch** (the location head uses a seeded group draw). Pin only places with no
training row, leave the rest **contested and unpinned**, rebuild with `finished.write_pin`,
and assert the new side is a **superset** of the old first (`write_pin` truncates).

#### The contested places are the design, and the guard now asserts that design

`test_finished_train.py` asserts the pin is a subset of the evaluation side and no pinned
place carries a training row; the contested count is recorded, never asserted.

#### `eval_only` outranks the clock, and that is what stops the evaluation side shrinking

`store.resolution_order` ranks an `eval_only` row last on its key; the clock decides
within a side.

#### A pin may be written BEFORE the sitting, and one guard reads red while it waits

Reserve a blind sheet's training-free places when it is cut, under `split.json`'s
`reserved_before_the_sitting` (not `eval_only_batches`), bracketed by
`finished.assert_pin_holds`. Until the sitting lands
`test_the_pin_is_part_of_the_evaluation_side_and_carries_no_training_row` and
`test_the_evaluation_side_is_in_the_plan` read red. Clear them: label → `label ingest
--write` → settle the pin (stored rows replace the `score: null` placeholders; keys back to
`finished_import.pin_document`'s) → `renders plan` → `renders build`. Giving a reservation
up is deleting its rows from `eval_split.jsonl`, only for a sheet never to be labelled.

## What cutting a sheet costs, and why the number moves so much

Label geometry is `sheets.LABEL_RESOLUTION` and `LABEL_SUPERSAMPLE` (1280×720 ss2), its
one spelling. A location unit is two renders, a finished one one. **Cost follows the
material, not maxiter or unit count**: ~1 s a unit for `smooth`, 4–7 s textured, a minute
on `phoenix:classic`. Price off a similar built sheet or a pilot **stratified by mode**.

### Cutting a finished-render sheet out of the candidate pool

* **The kind names the store**: both kinds is two sheets and two batches.
* **Route by `finished.routes_to` on the join to be rendered**, not `kind_of` on the
  ledger row. On a register miss `label ingest` renders the span test (minutes on a deep
  partition) and appends to tracked `data/coloring/texture_flat.jsonl`; readers never do.
* **`--reuse-renders` misses every pool row** (640×360 candidates).
* **Measure first**: render each unit via `colorize.render(level=True)` into
  `<sheet dir>/full/<sheets.cut_name(i)>.jpg` at three workers, write `leveled` back into
  the plan, then `label build` reports `rendered: 0`; compare the two renders byte for byte.
* **Cut a leg's own rows before the merge**: retention prunes at `RETAIN_PER_PAIR`.

### A blind page is cut and then stripped

A blind `finished_source` page is cut, then `sheet.jsonl` gets `facts: []`, `columns: {}`,
empty captions, null suggestions and a seeded shuffle, and the manifest's
`order`/`scorer`/`suggested_by` become `shuffle`/`none`/`none` with a `withheld` note. No
render is paid. A gallery-grade sheet is blind already. The batch name is on the page: name
a blind one for its population, not what it tests.

## A rule answers the mostly-black frames, and nobody is asked again

Location sheets exclude `interior_fraction ≥ 0.12` (`sheets.INTERIOR_THRESHOLD`, rule
`interior_ge12_v1`) to the sheet's `excluded.jsonl`, never the store; a unit without the
statistic serves. A location the walk refused for `interior_cap` (0.30) never serves.

## One generator, two row sources

A `Source` owns what a unit is, what is rendered and who prefills; everything else is
shared. A location unit renders twice (canonical and vivid maps), a finished unit once.

### A revision sheet re-serves rows the store already holds

The plan states each unit's recipe, incumbent **suggestion** (`suggested_by`) and **batch**;
a `leveled` directory is checked by `curation.manufacture.verify`.

### Which judge prefills a finished-render sheet, and which reading orders it

`--head` names the store; the model is `curation.floors.SCORING_HEAD`. `--order-by` is
`rank` (expected tier), `top` (last cutpoint) or `plan` (`order_score`); it moves the
order, never the prefill. An adoption re-checks `sheets.score_pictures`,
`curation.colorize.Colorizer`, `curation.manufacture`, `curation.rescore` and
`models.release_floor`.

## One ingest, every store

`/labels/` is root-anchored in `.gitignore` so `data/labels/` stays tracked. Ingest
before the sheet moves: units number by row position, and a rebuild renumbers. `intake`
writes the whole join to the store the sheet's head names (`Records`), checks counts both
ways, never duplicates, appends a changed verdict, and asserts the pin.

### A swept row and an agreeing verdict are the same row afterwards

Nothing records which button cast a tier: `suggested ≠ score` was adjudicated, a match is
no evidence. The sweep runs to the end, so the last override bounds the hand-cast prefix.

### Reading a labelled batch back afterwards

Verdicts come from `store.resolved()` / `finished.resolved(head)`, by `store.order_of`
`(recorded_at, file, line)`; page text from `sheet.jsonl` on `unit`; pixel statistics
from the walk ledger on `(center_re, center_im, width)` **as strings**.

#### A slice tag survives ingest only as a UNIT-ID BLOCK

Sections come back as contiguous `u####` blocks; record the ranges in
`data/batch_caveats.md`.

## Re-rendering a stored row is `renders.spec_of`, never `colorize.render`

`colorize.render` builds its own recipe to make a candidate; it cannot reproduce a row.

## A label store and the candidate ledger barely overlap

Most finished-store renders join no ledger row (`curation.retention.render_key_of`);
`candidate_ledger.RETAINED_LABELED` keeps the ones that do, with their pictures.

## The scale is the corpus's; the class count is the model's

Every judge is cast on `finished.SCALE`, 1..4 (the imported corpora's is
`finished_import.SOURCE_SCALE`); a checkpoint's class count is in its own config.
`finished_train.refuse_inexpressible` refuses a pass that cannot express a verdict.

## The order is the design

A batch registers before it has rows; stores append and resolve latest-wins; the split is
drawn over `groups.py`'s groups and shipped. `--no-scoring` cuts an instrument. **A suggestion is not a label.**
