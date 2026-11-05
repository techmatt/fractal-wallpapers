Judging finished renders: what to colour, how to colour it, what to keep, and what to
make at full size. Upstream makes *supply* (places, judges, a palette head); curation
spends it on a small set of finished wallpapers and a durable account of why those.
This file is the package map and its rules; every record field is in the root
[`FORMATS.md`](../../../FORMATS.md).

```
GALLERY.md       the colour ceiling, `solve`, `headroom`, `mode_policy`, `growth`
LEGS.md          the legs that spend the pool: `pool-draw`, `hunt`, `mine`, `depth`, ...
MEASUREMENTS.md  every standing quantity this stage relies on
*_decisions.md   an append-only log beside each, and beside this file: the arguments
```

A heading in a `_decisions.md` log is never renamed; a new decision is appended there
and the rule it settles is stated in the reference file.

## Modules

```
supply     binding · rescore · amend · floors · neutral · embeddings · spiral_scores
           · served_locations · signatures · distinct · flatness · durability · durables
the pool   recipes (one key per candidate) · candidate_ledger/ · retention · stamps
           · backfill
making     colorize (THE place a curation picture is made) · framing · intake
           · budget · mode_policy · draw_weights
legs       hunt · mine · depth · shrinkage · remode · rotation · repetition · repeat_ab
           · phase_response · pool_draw · manufacture · label_migration
gallery    view · rules · rank_key · ceiling · headroom · growth · solve · augment
           · selection · tentative · targets · pins · veto · trace · k_sweep
release    release · full_set · fulls · packs · explorer_link · embed_link · votes
           · rejection · records · run · run_layout · pacing · checks
pages      page · sheet · seat_sheet · below_bar · candidate_page · viewers
           · label_fate · atlas/
colour     colors · color_sheets · swatch_frequency · palette_coverage
```

`candidate_ledger/` is `store` (files, tiers, manifests), `rows`, `ratchet`, `rerender`,
`sweep` (prune, orphans, the one picture deleter), `door` (`merge`), `rebuild`,
`inventory`. Each module's docstring carries its mechanics.

```
fractal-wallpapers curate score --harvest <dir>            # supply through the location head
fractal-wallpapers curate score --opened                   # places no walk ledger names
fractal-wallpapers curate embed                            # a vector per admitted location
fractal-wallpapers curate run --run <name> --ledger <walk.jsonl> --wall-budget 28800
fractal-wallpapers curate solve run --n 1000 --no-render --no-sheet   # under a minute
fractal-wallpapers curate solve record --collection <name>  # record + page; keeps
fractal-wallpapers curate solve release <stamp>            # let a kept record go
fractal-wallpapers curate solve browse|resolve|list
fractal-wallpapers curate below-bar                        # read BEFORE `curate reject`
```

## Three different things are called a ledger

* **The candidate ledger**, `artifacts/curation/candidate_ledger/`: one row per *recipe
  ever rendered*, written only through `candidate_ledger.merge`.
* **The supply ledgers**: a walk's `walk.jsonl`, one row per *location*. `--ledger`
  always means these; `curation.binding` declares which a curation reads.
* **The rejection ledger**: `solve.rejection`, the block on a solve's record
  (`artifacts/curation/solve/<name>/solve.json`) naming each unseated candidate's
  first refusing rule.

## The candidate ledger: what we have already made

`rows.jsonl`, `scores.jsonl`, `flatness.jsonl` and `reduced_signatures.jsonl` live hot;
`data/curation/candidate_ledger/` tracks their manifests and `ratchet.jsonl`; `merge`
mirrors all four to `<archive>/curation_backup/candidate_ledger/` and verifies them.
Verbs: `curate candidate-ledger census | free-slots | pictures | re-render | score |
prune [--dry-run] | ratchet | orphans | save | check`.

**The key is the pixels**: a digest of the engine spec (`renders.spec_of`) minus its
paths, plus the autolevel band's sha256. A re-framed location is a re-key
(`location.superseded_by`). A row carries its `colour` block (readers take colour off
the row), a `hunt` block with `k` (missing reads `None`, never 1), and an `engine`
fingerprint that is provenance, never a gate.

### Record everything; filter nothing

No quality bar admits a row; a human rejection rides on the row. **Scores are a
sidecar** keyed `(recipe key, judge artifact, regime)`: `rows.scores_by_recipe` joins on
the shipped head unless told otherwise and raises when an unnamed read meets two
regimes. ⚠ A leg's `scores.jsonl` uses that triple as `key`: **join on `recipe_key`**,
and treat a leg-wide clear rate of zero as a join fault.

### The step a judge adoption makes necessary

After a judge flip every row reads unscored and `solve.pool` refuses them all; `curate
candidate-ledger score` (resumable) is the fix. **`gallery-grade score-pool` runs after
any merge** and before a cascade solve: until it does, merged rows have no `p_fine` and
cannot be seated. It is minutes warm, several times that cold.

### The two retired artifacts were dropped

The sidecar holds the shipped judge's reading only; a retired one goes once its
before-and-after is taken. The artifact/regime guard stays for the next adoption.

### The growth law

**Rows per (location, mode) are bounded by `RETAIN_PER_PAIR` (5) plus the five
protections and one colour allowance, never by attempts**, because `prune` runs inside
`merge`. The protections (`store.RETAINED_PROTECTIONS`): a live release seat, a human
rejection, a human verdict, the rank key's fitted population, a kept record's seat.
`retention.FAMILY_ALLOWANCE` keeps at most one more row a pair, best in a colour family
the five miss.

The law runs one way, so a free slot is `K - len(pair)`: `retention.free_slots`, and
`curate candidate-ledger free-slots --out` for a leg's `--floor-places`. A near-band
manifest is `curate depth near-places`. Price a rank-key change by the kept set it
moves at pairs over K, never by pool-wide top-row changes.

**A prune deletes pictures first, then renames its three `.writing` files in.** A crash
between leaves rows naming absent pictures; a second `prune` repairs it. ⚠ On Windows a
held `rows.jsonl` (often a forgotten `label serve`) fails the rename: close it, re-run
`prune`. That merge's `repeat_draws` is lost. A prune records its drops against a
high-water mark in `ratchet.jsonl`, so a census asserts *count + recorded drops >= mark*.

### The prune ranks on `rank_key` and a gallery seats on the cascade, and below the bar those are one order

So `rank_key` cannot retire while the cascade runs (`tests/test_seat_sheet.py`); a pruned
row never gets a `p_fine`. The argument is in [`README_decisions.md`](README_decisions.md).

### And `retention.decide` prices the rank alone

So it over-predicts a merge's losses: the protections are the gap. A pricing off
`decide` is a floor on what survives.

### The stress test the size is read against is ten thousand hours

A durable record's size scales with knowledge, never with work: multiply its growth by
`10,000 h / hours run`, and if that is absurd the design is wrong now. A file read in
full states its bound; dropping a picture drops its row; per-render facts go in counters
or run records; a leg's `sequence.jsonl` retires whole, never row by row. A dropped
recipe is invisible to the `known` dedup: every merge prices it as `repeat_draws`.

### Putting a picture back

`curate candidate-ledger re-render` redraws what rows name and the disk lacks, only where
the rebuilt recipe digests to the row's key, by whole pairs. `curate re-render` does the
same for the tracked release rows; `curate rescore` refuses while one is missing.
**An upsert replaces** all but a human `rejected`, so a leg overlapping the pool submits
only keys the ledger lacks.

## `curate retention` — what survives what the rule drops

### What is kept, and why each rule is the rule it is

The top five per (location, mode),
ranked *within* the pair by `rank_key` (CORN's scale moves with each retrain, so no
absolute cut serves every mode); every row a human label joins
(`labeling.finished.render_key`, on the recipe, never the regime, gallery-grade
included); the other protections. The rest lose row and picture together.
`retention.py` decides and never deletes. Three aggregates survive every attempt:
`(location, mode)`, `(colormap, mode)` and `(location, cell)` counts.

### What retention does not reach, and the levelled colormaps swept on 2026-08-30

A prune takes a dropped row's picture and `<stem>.leveled/` only; `fields/` and run
records are outside it. The pool's levelled colormaps were swept except beside kept
seats, so **a sheet rebuilt from a swept candidate needs `re-render` first**, or
`pool_draw.leveled_dir` answers `None` and the plain map renders under the same identity.

#### A prune cannot take a surviving row's colormap, and the reason is structural

The doomed list and `pool_draw.leveled_dir` both derive `<stem>.leveled` from one row's
own picture, and no two rows name one picture (it is named by recipe key, or by attempt
index in one run directory). `tests/test_leveled_identity.py` pins it.

### Orphans, and sweeping a leg

`orphans` lists pictures no store names, the reference set built in the deleting call;
`--apply` deletes; an unmerged leg goes only by `--leg` or `--include-unmerged`. It walks
`<subtree>/<leg>/pictures` over `store.POOL_SUBTREES`, so `fields/` is unreachable.

### Sweeping a leg does not un-decide it

⚠ Its merge would still upsert rows naming gone pictures. A sweep writes `swept.json`, and `sweep.refuse_swept` guards `merge` and
`rotation.merge`. Delete it only after re-rendering.

## What is kept, published, discarded

A record is a stamp under `artifacts/curation/tentative/`. Kept is `tentative.kept()`,
`PUBLISHED` plus the keep file, the only thing `protected_keys()` reads. `solve record`
keeps by default (`--no-keep`, or `solve release`); an unkept record is discarded.
Publishing is Matt's: a `PUBLISHED` line and a `.gitignore` line, which
`tests/test_tentative.py` holds equal; a `--force-fill` record never publishes. An
unstamped read means `tentative.DEFAULT`. A collection's size is `targets.TARGETS`, its
pool `targets.pool_for`. `solve run`/`record` and `growth` hold the pool: one per box.

### The 53 MB of attempt rows under `artifacts/curation/gallery/` is KEPT

The retired gallery passes' `gate.jsonl` are the only judged-attempt data under the
retired render heads, and `orphans` reads them. **Not to be swept without Matt's
ruling.** A pass's winners are in `data/curation/release/<pass>/`.

## `curate label-fate`

What became of each gallery-grade 4: off the roster, below the coarse bar, below the
fine bar, refused by a rule, seated. Verbs `keys` (before the solve, for `solve record
--explain-keys`), `population`, `fates`, `competitors`, `render`, `page`.

### It reads ONE of the three, and which one is the whole point

`data/gallery_grade/` alone (`label_fate.STORE`): its 4s are verdicts on this pool's own
candidates.

### The picture beside a refused card is not the seat at its place, and that took two goes

A card shows the marginal member of `rules.State.counted_requirements` for the refusing
rule; only for `location` is that the seat at the place.

## The archive tier

A tree archived from `<hot>/<name>/` lands at `<archive>/<name>/` (`paths.hot_root()`,
`paths.archive_root()`; never spelled in tracked text; `storage status` prints tiers). It
leaves only once a copy matches on file count and bytes. **`artifacts/curation/` never
leaves**, except unkept pool pictures: `storage pictures archive`, then `prune-hot
--apply`, read back by `paths.Tiers.resolve`. Training refuses mirrored pictures
(`require_hot`); an unplugged disk raises `ArchiveUnreachable`, never a smaller pool.

Two durables are saved by hand: `curate sidecar save` after every `curate score`, `curate
embeddings save` after `curate embed`. ⚠ Before anything deletes or moves under the tree,
run both and `curate signatures save`, then `check` each: `grown` is content on one disk.

## Every release render carries its explorer link

`release.render_task` writes the explorer's link into the metadata (`embed_link`
mirrors the site's `explorer/stamp.js`):

| Field | PNG | JPEG |
|---|---|---|
| `fractal-explorer <query>` | `iTXt` `fractal-explorer` | `COM` |
| XMP `dc:source` = URL | `iTXt` `XML:com.adobe.xmp` | `APP1` XMP |
| EXIF `ImageDescription` = URL | — | `APP1` Exif |

The query is `explorer_link.query_of`, base `EXPLORER_URL`. A picture no link draws
exactly ships with none and a reason in `info["link_refused"]`. Pixels never move.

## The full set: every Gallery picture at 2560x1440 ss3

`full_set` renders each recipe the kept records seat to `<key>.jpg` at `REGIME`, JPEG q95
4:4:4, with the borrowed levelling curve; `REGIME` is the one spelling of full size.
`DEADLINE` is an hour, a retry two.

```
fractal-wallpapers curate full-set run|status --out <dir>
fractal-wallpapers curate full-set pause --out <dir> [--now]
```

Done means `<key>.jpg` exists (built in `_work/`, renamed in); to redraw, delete it.
`membership.jsonl` is what packs read. One driver per directory: a second exits 3. Pause
writes `PAUSE`; delete it to resume. ⚠ Stop a driver with `pause`, never by stopping the
process that launched it, and never kill `fractal-engine.exe` by name.

## Wallpaper packs

`packs` zips the full set into eighteen downloads plus `packs.json`, uploading nothing:
the general n=1000 in three parts, best 30/100/200 (nested), twelve hue collections.
Order is `packs.SEED`'s until `--order FILE`; hues take `--orders DIR`; `--forced` pins
members into a best pack and every larger one. JPEGs are stored, so links travel. An
incomplete pack refuses (exit 2) without `--allow-partial`. Budget ~1.1 GB a zip.

```
fractal-wallpapers curate packs status --full <dir>
fractal-wallpapers curate packs build --full <dir> --out <dir> [--only best-30 rose]
```

## Levelling is decided once and replayed upward

The autolevel decision is taken at candidate geometry; larger renders pass a `borrowed`
curve to `coloring.autolevel.maybe_level`. `curation.stamps` finds each seat's stamp;
`curate autolevel survey` lists who replays, and `backfill --record <stamp>|all` or
`--atlas <plane>` re-derives a curve for the rest.

## The colour census and coverage

`curate colors` separates a colour that cannot be expressed, is never picked, dies at
the floor, or was never labelled; it gates nothing. `curate coverage` asks how many maps
put each swatch on 5-20% of an image's pixels.
