Judging finished renders: what to colour, how to colour it, what to keep, and
what to make at full size.

This is the last stage. Everything upstream produces *supply* — places a walk
found, judges trained on human verdicts, a palette head that ranks colour choices.
Curation spends it: it turns the union of every walk into a small set of finished
wallpapers and a durable account of why those and not the others.

```
README.md        the architecture, the stores, and the module index below
GALLERY.md       the colour ceiling, `solve`, `headroom`, `mode_policy`, `growth`
LEGS.md          the legs that spend the pool: `pool-draw`, `hunt`, `mine`, `depth`,
                 `shrinkage`, `remode`, `manufacture`
MEASUREMENTS.md  every dated reading, and the historical per-candidate rate table
```

```
binding    which ledgers this curation reads, declared once and never guessed
durability a file kept on two disks under a tracked manifest: save, check, restore
durables   which files those are, and the three a run refuses to start without
rescore    the accumulated pool, read again through the heads shipped now
amend      re-reading a location whose standing score was read off a picture nobody has
stamps     the whole autolevel stamp behind one recipe key, wherever a leg wrote it
backfill   a re-derived curve for the seats no leg wrote one for, in its own sidecar
floors     every number that removes a picture, in one file
neutral    the one picture a location is EMBEDDED from, and its frozen recipe
embeddings one DINOv2 vector per admitted location, keyed and kept forever
intake     the ranked offer, best first per partition
budget     how many pictures to make, and for which judge
colorize   a candidate set of maps, the head's pick, a render, a verdict
mode_policy  what standing each production mode has, as one table with one owner
framing    where a location's attempts are framed, decided before they render
recipes    what decides a candidate's pixels, as one value with one key
draw_weights  what a partition is worth in a breadth draw, in one table
candidate_ledger/ every recipe ever rendered, one row each, with its colour
  store      the two files, the tiers, the manifests, and reading rows out of them
  rows       one row and the blocks it carries, as shape with no store behind it
  ratchet    the high-water mark, and the deletions that account for a smaller store
  rerender   putting back a picture the row names, and reading a score onto it
  sweep      the retention rule, the orphan backstop, the one picture-delete verb,
             and `remove`: named rows out, told rather than decided
  door       THE door: `merge` — upsert, record, prune, and every leg comes through it
  rebuild    `backfill`: built out of the two decision stores that predate the ledger
  inventory  `census` and `feasibility`: what the pool holds, and what a solve can get
flatness   how much of a finished picture is dead space, as a column beside the scores
retention  which candidates are worth the disk, and the counts that survive the rest
hunt       render on purpose: breadth where the ledger is thin, colour where a solve was short
mine       price a PRIMED location three ways, and profile what one candidate costs
depth      buy width at one place, and measure what it buys against the head's rank
shrinkage  re-read a candidate set's winner at label geometry, and price the winner's curse
remode     a retired mode's clearing rows, rendered again in a mode still bought
rotation   the phases nothing ever asked: every passing recipe against five
           rotations of its own gradient, best of the six, and the row it replaces gone
headroom   what each selection constraint needs, holds, and costs to buy — no solver
growth     what more mining buys, at every gallery size — measured by subsampling the pool
growth_plot  six pictures of one growth sweep. Matplotlib, scratch only, legibility only
pool_draw  the UNAIMED draw: N pool locations at random, one seat-ranked picture each
view       what one pass may reach: strata, and band-blind slices of them
rules      one spelling per selection rule, over incremental state
rank_key   the fitted sort key retention ranks on and the cascade's own lower
           half. Deprecated as a SEATING key 2026-09-08; still resolved, not offered
signatures the diversity rule's bound signature, swept once into a sidecar
distinct   which places are visibly different places, decided before any colour
ceiling    the colour ceiling, and the targets that are the same feature with the sign flipped
spiral_scores  `P(spiral)` per location, so a gallery cap has a share to act on
served_locations  every location the collection has already released a wallpaper of
solve      THE gallery leg: the view, a greedy seed, 1-swap improvement,
           augmenting chains, and 1-swap improvement again
augment    the stage that RAISES the seat count: one seat out, two in. A 1-swap
           conserves the count, so tier 1 was frozen at the seed until this
tentative  one solve recorded under a stamp, with IDs, aliases and a browser
selection  top-N per judge, under the slot and supply caps, the location rule
           — and the bar
release    the selected rows again at full size, workers rendering
pacing     the wall clock: what may still start, and what is killed
records    what the run decided, and out of what population
rejection  taking a released row back afterwards, without losing what the run did
below_bar  the glance sheet of what an acting bar would take back, to rule off
sheet      the same thing laid out for a person to disagree with — plus
           `score_sheet`, the page a LEG reads its own pile on
colors     the colour census: what colours this project can make, picks, keeps and labels
color_sheets  what a colour cell actually looks like, so an eye can rule on it
swatch_frequency  every swatch, what it looks like, and how often the pool is it
palette_coverage  how many maps can put a swatch on a real share of an image
manufacture  forcing the rare swatches onto good places, and the sheets that ask
label_migration  every judged recipe re-expressed at candidate geometry, staged
           outside every store, read out, and merged through THE door
label_fate what became of every GALLERY-GRADE wallpaper a person graded 4, one
           rung at a time — and whatever holds each one's place, beside it
checks     the two claims only a re-render can settle
run_layout where a run's regenerable files go, and at what size it draws them
run        the wiring, and nothing else
```

```
fractal-wallpapers curate score --harvest artifacts/harvest_run3   # through the location head
fractal-wallpapers curate sidecar save                             # the supply, made durable
fractal-wallpapers curate embed                                    # a vector per admitted location
fractal-wallpapers curate embeddings save                          # the vectors, made durable
fractal-wallpapers curate frames save                             # the frame index, made durable
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
fractal-wallpapers curate candidate-ledger backfill    # the cache, from what exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger save        # both files, made durable
fractal-wallpapers curate candidate-ledger bare-varied # the rows whose picture is the bare mode
                       # under a varied key: a key manifest for `re-render --keys`, streamed
fractal-wallpapers curate headroom                     # the census: what is short, and what one more costs
fractal-wallpapers curate headroom --bars              # the per-mode bar table alone; no census, no solver
                       # what a before-and-after of a re-score is read off
fractal-wallpapers curate headroom --n 20 --n 150      # only these rungs of the ladder
fractal-wallpapers curate headroom --flat-floor        # bound the FLAT mode floor, for a baseline
fractal-wallpapers curate distinct                     # the neutral pre-selection read, and the radius sheet
fractal-wallpapers curate distinct --no-premise        # the join and the sheet, measuring no pixel cloud
fractal-wallpapers curate signatures sweep              # the bound signatures, once, for the clearing pool
fractal-wallpapers curate signatures coverage          # how much of the pool the sidecar can answer for
fractal-wallpapers curate solve run --n 20 --no-render # THE gallery leg: decide, render nothing
fractal-wallpapers curate solve run --n 150            # the gallery, then the pictures
fractal-wallpapers curate solve run --n 1000 --no-render   # 53 s MEASURED, 2026-09-04
fractal-wallpapers curate solve run --n 2000 --no-render   # THE planning size, ~2.5 min
fractal-wallpapers curate solve record                     # THAT solve, recorded, + the page
fractal-wallpapers curate solve record --n 200 --themed dark_vivid_green   # a THEMED record
fractal-wallpapers curate solve browse <stamp>             # the page again, off the rows
                       # filter, group by mode or cell, click a picture for the full size
fractal-wallpapers curate solve resolve <alias>,<alias>    # an ID back to a recipe
fractal-wallpapers curate solve list                       # every record on this machine
fractal-wallpapers curate label-fate keys --store scratch/label4_fate   # BEFORE the solve
fractal-wallpapers curate solve record --explain-keys scratch/label4_fate/keys.txt
fractal-wallpapers curate label-fate population --store scratch/label4_fate  # pool-holding
fractal-wallpapers curate label-fate fates --stamp <stamp> --store scratch/label4_fate
fractal-wallpapers curate label-fate competitors --stamp <stamp> --store scratch/label4_fate
fractal-wallpapers curate label-fate render --store scratch/label4_fate   # HOURS, 3 workers
fractal-wallpapers curate label-fate page --store scratch/label4_fate \
    --migration-store scratch/label_migration_0908 --repaired-seats-of <stamp>
fractal-wallpapers curate manufacture --step register --write          # BEFORE anything
fractal-wallpapers curate manufacture --oversample 2.5                 # plan, build, select
fractal-wallpapers curate manufacture --step verify --sheet artifacts/<sheet>
```

**The two solve figures above were `~6 min` and `10 min` and both were stale by
about 7x.** Measured on this machine, idle, 2026-09-04, over a 164,052-candidate
pool: `--n 1000 --no-render --no-sheet` is **53 s** end to end, of which the pool
read is 17 s and the solve itself 31 s; the `--n 2000` solve half measures 122 s,
so that line is about two and a half minutes on the same overhead. The old
figures predate the three speedups of `4300e4b` — which took the n=2000 pass from
275 s to 119 s — and the `~6 min` had said "scaled not measured" since it was
written. A figure nobody measured is a figure that goes stale without anything
looking wrong, which is why these two now name the day and the pool.

**A THEMED gallery can be recorded, and until 2026-09-05 it could not.** `--themed`
reached `curate solve run`, which writes a solve record and never a stamp — so a
themed gallery could be solved and never kept, and the six themed baselines are
what noticed. `record` now carries the same `--themed`, `--themed-cap` and
`--themed-radius`, out of one helper with `run`'s, and the cell target and the flat
floor the flag sets as defaults come from `cli.curate_commands.themed_demands` so
the two verbs cannot reach two different galleries. A themed record is a record
like any other: unpublished until Matt names its stamp, and nothing renders — the
page shows each seat's stored 640x360 candidate.

## Three different things are called a ledger

The word does three jobs in this stage and they are not versions of one another.
A reader who conflates them will look for a row in the wrong file:

* **The candidate ledger** — `artifacts/curation/candidate_ledger/`, one row per
  *recipe ever rendered*, with its colour and where its picture is.
  Manifest-tracked, written only through [`candidate_ledger.merge`]. This is what
  `curate candidate-ledger` and `curate solve` mean by "the ledger", and it is the
  one below. Since 2026-08-29 it is **two files of that shape and not one** — see
  "The two ledgers".
* **The supply ledgers** — a walk's own output, `walk.jsonl` under a harvest, one
  row per *location* the search found and scored. Plural because there are many
  of them, one per run, hot or archived; `--ledgers` and `--ledger` on the CLI
  always mean these. `curation.binding` is what declares which ones a curation
  reads. Nothing here writes one.
* **The rejection ledger** — [`solve.rejection`], the block on a gallery's
  record naming, for every candidate the walk did **not** seat, the first rule
  that refused it. A partition of the pool rather than a store: it is written
  inside `artifacts/curation/seat/<name>/seat.json` and nowhere else.

## The candidate ledger: what we have already made

A pass renders candidates, seats a few of them, and keeps a decision about each.
What it has never kept is an answer to the question a *solver* has to ask before
it does anything: **have we already made this picture?** The propose-then-solve
build starts here, and this is its first piece — a type that names a picture, and
a durable store of every picture named.

```
src/fractal_wallpapers/curation/recipes.py            the type, the key, and `of_record`
src/fractal_wallpapers/curation/candidate_ledger/     the store, the rebuild, the inventory
artifacts/curation/candidate_ledger/rows.jsonl        one row per recipe
artifacts/curation/candidate_ledger/scores.jsonl      ...and its scores
artifacts/curation/candidate_ledger/flatness.jsonl    ...and its dead-space column
artifacts/curation/candidate_ledger/reduced_signatures.jsonl   ...and its twin signatures
data/curation/candidate_ledger/*.manifest.json        what the history keeps of the four
<archive>/curation_backup/candidate_ledger/*.jsonl    the durable copies
```

**All four are mirrored**, by one door: `merge` copies `rows`, `scores`, `flatness`
and `reduced_signatures` to the archive and verifies each identical. The signature
sidecar was outside that until 2026-09-01, on the argument that it is
**regenerable from the pictures** — true, and it stopped being worth it when the
file shrank. It is the sidecar the **binding** constraint reads: the n=2000 solve
of 2026-09-01 served **9,371 of 9,388** signatures from it, and re-deriving all
11,636 rows is about **2.8 minutes** at `DIRECTIONS = 256` against ~19 at the 1024
it used before that constant moved. Copying 68.6 MB beats 2.8 minutes, so it is
copied.

**Both halves of that have grown by about 4x and the argument got stronger, not
weaker.** The store is **253 MB over 44,346 rows** on 2026-09-06 against the
11,636 rows the paragraph above was written on, so the re-derivation it is being
weighed against is proportionally longer — the 2.8 minutes is a 2026-09-01 reading
and has not been re-measured, so do not restate it as one. Copying is still the
cheap side. `curation/signatures.py`'s *What a row costs, and the figure that is
it divided by the wrong denominator* carries the per-row number and why 68.6 MB
was a correct reading rather than an error.

Two things about that copy. It is **conditional** — nothing in a merge fills the
signature sidecar, so a checkout that has never run `curate signatures sweep` has
no file to save and the door records `null` rather than refusing. And the manifest
counts rows by the shape **each row names** rather than by the current
`(BOUND_BLOCKS, DIRECTIONS)`: nothing sweeps old constants out, so the live file
held 11,454 rows at `4x256` and 182 still at `4x1024` on 2026-09-01, and a mirror
of bytes does not get to restate what those bytes are.

```
fractal-wallpapers curate candidate-ledger backfill   # from what already exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger prune      # back to the rule, ~35 s. RUNS FROM `merge`
fractal-wallpapers curate candidate-ledger prune --dry-run   # THE dry run. Touches nothing
fractal-wallpapers curate candidate-ledger free-slots --mode smooth --min-slots 2 \
    --out scratch/near_places.jsonl                   # where a leg has ROOM, and the manifest
fractal-wallpapers curate candidate-ledger pictures   # rows naming a picture that is not there
fractal-wallpapers curate candidate-ledger ratchet    # the high-water mark and what took rows off it
fractal-wallpapers curate candidate-ledger ratchet --census   # ...counted against the live store, ~15 s
fractal-wallpapers curate candidate-ledger re-render  # ...and put them back. ~1.5 pictures/s
fractal-wallpapers curate candidate-ledger score      # every picture through the judge shipped NOW
fractal-wallpapers curate candidate-ledger save       # the live files, their manifests
fractal-wallpapers curate candidate-ledger check      # are they whole
fractal-wallpapers curate flatness save               # its own durable. `merge` does this too
fractal-wallpapers curate signatures save             # ...and so is this one. `check`/`restore` too
```

⚠ **A score off this store is joined on one judge artifact and one regime, so a
caller either names the regime or inherits last-row-wins.** `rows.scores_by_recipe`
reads `artifact=None` as the live head and `regime=None` as *whatever the sidecar
holds* — correct only while the sidecar is single-regime, which is why an unnamed
read that finds one recipe at two regimes raises rather than flattening. Six
production callers pass neither. **And one reader is a writer's skip set rather
than a join, so it does not raise**: `candidate_ledger/rerender.py`'s `rescore`
builds its already-read set from `recipe_key` and the artifact alone, so under two
regimes it counts a recipe read at the *other* geometry as already scored and
leaves it unscored at the geometry the pool joins on. Both are argued in full under
*The two retired artifacts were dropped, 2026-09-06* below.

### The step a judge adoption makes necessary

**The morning after a flip this store holds a full set of scores and the pool is
empty.** Not a bug and not a migration that was forgotten: the sidecar is keyed
`(recipe, artifact, regime)` and `scores_by_recipe` joins on the live artifact
alone, so every row reads as *unscored on the head that ships* until it is read
again. `solve.pool` refuses all of them as `no_score` and every gallery, census
and headroom read over the ledger comes back empty. `curate candidate-ledger
score` is the step that closes it, and it is the only one — nothing else in this
tree reads a ledger picture through the judge.

⚠ **A LEG's own sidecar is keyed the same way, and a driver joining on `key`
scores the whole leg 0.0 in silence.** `artifacts/curation/depth/<leg>/scores.jsonl`
carries `key` as the triple `<recipe>|<artifact>|<regime>` with the recipe key in
its own `recipe_key` field, exactly as the ledger's sidecar does. A readout that
joins a leg's `rows.jsonl` on `key` therefore matches nothing, and because a missing
score reads as *did not clear* rather than as an error, the leg reports a clear rate
of zero and nobody is told. That is not hypothetical:
`scratch/two_arm_pilot_0906/readout.json` recorded `q4_clears: 0` for both arms of
the 2026-09-06 leg under a report quoting 1,177 and 3,870, and the same join was
written again the following night before it was caught. **Join on `recipe_key`**,
and treat a leg-wide rate of exactly zero as a join fault until proven otherwise.

It writes **beside** the retired artifact's rows and never over them: a picture
read by two judges is two facts, and the retired reading is what every
before-and-after comparison is taken against. **That is what a retired reading is
FOR, and it is also what makes it droppable once the comparison has been taken**
— see *The two retired artifacts were dropped* below. Resumable by chunk — 4,096
pictures at a time onto `scores.partial.jsonl`, folded into the sidecar in one
upsert at the end — so a kill costs the chunk in flight.

Measured over the whole store, weights-v4 to weights-v5 on 2026-08-31: **122,260
pictures in 20.2 min**, 101 a second, one CUDA judge at batch 128. The pass is
JPEG decode and not the forward: 7.4 ms a picture at batch 128 against 8.3 at 64,
so the batch buys almost nothing past there and a second GPU would buy less. It
also runs at half that rate on a cold page cache and at twice it on a warm one —
the first chunks read 88 a second and the last 195 — so the figure is a leg's
average and not a per-picture constant.

### The growth law

**Rows per location are bounded by `RETAIN_PER_PAIR` times the modes tried
there, plus the five protections. They are no longer a function of the attempts
made.** That sentence is the whole point of the store, and it holds because
`candidate_ledger.prune` runs inside `candidate_ledger.merge` — THE door every
leg comes through. A rule that ran anywhere else would be a rule the store
stopped obeying between the times somebody remembered it.

**The law runs one way, and that is what makes a free slot arithmetic.**
`retention.decide` keeps `min(K, attempts)` — it sorts a pair and takes the first
K, with no branch on how many the pair holds — so **a pair holding fewer than the
keep has never had more attempts than it holds.** Nothing was pruned away from
it. A free slot is therefore `K - len(pair)`, a subtraction over rows already in
hand, and never a scan of what a leg might once have rendered.

**`retention.free_slots` is the one spelling of it**, and
`fractal-wallpapers curate candidate-ledger free-slots` is how a manifest is cut
from it — `--out` writes the places file `--near-places` and `--floor-places`
read, so the population a leg draws is the one that was counted rather than one
re-derived beside it. Nothing sizes an opener or counts a slot by hand any more.

Measured over the ledger on 2026-09-06, at the keep of the day and at the keep
that replaced it. The store did not move between the two readings; only K did:

| | pairs with room | free slots | places | rows in them | pairs over K |
|---|--:|--:|--:|--:|--:|
| K = 3 | 43,255 (37.7%) | 60,316 | 9,426 | 69,449 (24.4%) | 559 |
| **K = 5** | **114,709 (100.0%)** | **289,210** | **26,442** | 284,335 (99.9%) | **5** |

Over 114,744 pairs, 284,517 rows and 26,442 places. At K=5 the free share of
`K x pairs` capacity is 50.4% against 17.5% at K=3.

⚠ **The flip cost one reading of a free slot, and the arithmetic is not what
changed.** Under keep 3, a pair holding fewer than the keep had never had more
attempts, so *a free slot* also meant *an unexplored pair*. After the flip that
survives only for a pair holding fewer than **three**: a legacy pair sitting at
exactly 3 may have been pruned there at the old keep, and those attempts are
gone — nothing recovers them and nothing should try. The distribution says how
much of the store this is: **70,930 pairs sit at exactly 3, 61.8% of all pairs**,
against 17,061 at one and 26,194 at two. So **43,255 of the 114,709 pairs with
room — 37.7% — still carry the unexplored reading, and the other 71,454 do
not.** A slot is a row the merge will keep either way, so planning is unaffected
and every number in the table above is correct; what a free slot is *evidence of*
is the thing that narrowed.

Three things the phrasing has to keep straight, because each has been got wrong.
It is a percentage of **pairs**, not of the pool — the two columns are in the
table for that reason. "Attempts" means the ones the **merge ever saw**, so a
killed leg's renders are outside the arithmetic entirely, which is what
`curate candidate-ledger orphans` and `repeat_draws`' floor are for. And the law
is one-sided: the pairs over K are every one of them a
`candidate_ledger.RETAINED_REASONS` protection rather than a prune that failed.

This is the rule that would have caught the inverted near-band manifest —
[`LEGS.md`](LEGS.md)'s *`--near-places` is the same thing for the near band* — a
whole unit spent because *free slot* was inferred from *not taken by a floor arm*
instead of being subtracted directly.

#### The prune's binding surface is the pairs over K, and it is tiny

**The same one-sidedness bounds what a prune can do at all, and the bound is the
number to reach for before reading any pool-wide rank statistic.** Measured over
the ledger the ckpt-112 mine left, 2026-09-06: **119,231 pairs, of which 106 hold
more than the keep** — 0.09%. `retention.decide` sorts a pair and takes the first
K, so a pair holding K or fewer is kept **whole whatever the ranking says**. The
prune's whole binding surface is those 106 pairs.

That is a consequence of the flip and it will not last. The pool was pruned at
keep 3 while the keep was 3, so almost every pair was cut to at most 3 before the
keep rose to 5 — which leaves nearly every pair under the new keep with room in
it, and leaves the ranking with nothing to decide. Pairs will refill and the
surface will grow; a reading of it is dated, not structural.

**So a pool-wide count of rank changes does not price a change to the rank key,
and the two numbers differ by three orders of magnitude.** Dropping
`stratum_score` moved the top-ranked row on **17,335 of the 102,169 pairs holding
more than one row (17.0%)** — and changed the *kept set* on **31 pairs, 62 rows of
308,419**. Only the second number is what the merge would have done differently.
Quote a top-row count as what it is, a statement about the ordering, and price a
key against the pairs over K.

**And at K = 5 the manifest cut from it stops narrowing anything**, which is the
100.0% row of the table above read as a leg would spend it: over
`smooth`/`stripe`/`tia` at `--min-slots 2` it names 23,597 places against the
23,619 that hold a candidate in one of those modes at all. Cut it anyway — the
subtraction is what refuses the inverted shape — but size the leg off what
actually bounds it, which is the band and not the slots. Same heading of
[`LEGS.md`](LEGS.md) carries the measurement.

| | rows | on disk |
|---|---|---|
| before, 2026-08-29 | 366,236 | 1,057.3 MiB |
| after | 122,516 | 150.8 MiB |

**The stress test the size is read against is ten thousand hours.** A durable
record's size must scale with knowledge gained and never with work done, so
multiply a store's observed growth by `10,000 h ÷ hours run` and look at the
answer; if it is absurd, the design is wrong now rather than later. A file read
in full carries a stated bound, retention that drops the picture drops the row,
per-render facts go in counters or run records, and a leg's own measurement
record retires whole rather than being pruned by row.

Re-running the rule over the store is a fixed point: 122,516 of 122,516 rows
kept, nothing dropped, 18.4 s to decide. The 243,720 rows the rule let go were
**deleted** rather than archived, with their pictures, on Matt's ruling: everything removed is either retained already
or re-renderable from a retained recipe, and a second copy nobody could explain
later is worse than none. What that costs is real and is measured rather than
assumed — see *what the rule costs* below.

`RETAIN_PER_PAIR` is **five** and it is **the** constant: a picture is kept if
and only if its row is. It was **three** from 2026-08-29 until 2026-09-06, when
Matt raised it at ckpt 111's reading: simulated over 674,089 attempts, keep 4
holds 99.3% of today's live release seats at 1.221x the rows and keep 5 holds
100% at 1.385x — and since **retention is not retroactive**, an error toward the
cheaper keep is permanent while an error toward the dearer one is only disk. The
flip is not retroactive either: nothing re-ran, nothing was backfilled, no
existing row changed, and the attempts the old keep pruned stay pruned. It was
one of two until 2026-08-29, when
`retention.KEEP_PER_PAIR` kept five *pictures* a pair on a different ranking
(raw `P(>=4)`, not the rank key). The two were not nested, so a row in the top
three by rank could be sixth by `P(>=4)` and have lost its picture already — 41
rows were in exactly that position, and it stayed small by luck. One ranking,
one constant, one delete.

The row itself was cut against the reader sites and against two invariants: the
recipe key stays recomputable (`recipes.of_record` then `recipes.key_of`) and the
picture stays re-renderable from the row alone (`Recipe.row` is the engine spec).
Both are held by `tests/test_candidate_ledger.py`, the second pair over the live
store in the slow lane.

**Every sidecar is pruned in the same transaction as the rows.** `scores.jsonl`
and `flatness.jsonl` are keyed on the recipe key, so a ledger written without them
is two stores of rows nothing joins to. `candidate_ledger.prune` writes all three
to `.writing` names and renames only once all three are whole.

**And the pictures go first.** The order inside `prune` is a safety property, not
a preference: a crash after the record transaction would leave pictures nothing
names, which no reader can find and no run can free. A crash after the deletes
leaves rows naming absent pictures, which `curate candidate-ledger pictures`
reports, `solve.pool` refuses, and a second `prune` repairs — the ranking is a
deterministic function of the rows.

#### A prune writes down what it took, and that is what lets a census assert anything

Because the store deletes on purpose, no count over it can be pinned as a floor:
*the store only grows* stops being true the first time a leg merges, and the
census that asserted it went red and stayed red through 2026-09-07 with no repair
available except repointing the constant, which asserts nothing. So `prune` ends
its transaction by advancing a **high-water mark** and recording its own drops
against it, in `data/curation/candidate_ledger/ratchet.jsonl`
([`candidate_ledger.ratchet`](candidate_ledger/ratchet.py)), and the census asserts
a **ratchet** instead: the count now, plus every deletion recorded since the mark,
still reaches the mark. Loss is forgiven exactly when something accounted for it.

**This is the only recording site because it is the only deletion site.**
`store.write` is an upsert and removes nothing; `orphans` unlinks pictures no row
names and takes no row, so it deliberately writes nothing here — a sweep that
recorded its pictures in a guard over rows would be handing the census a licence
to lose rows it never lost. The mark is read **after** the three files are renamed
and is the store at its *peak*, before the rule took anything back.

#### The prune ranks on `rank_key` and a gallery seats on the cascade, and below the bar those are one order

**This is why the seating flip of 2026-09-07 left retention alone, and it is an
argument rather than an omission.** `_prune_ranks` reads
[`curation.rank_key`](rank_key.py); `solve.DEFAULT_KEY` has been
`solve.CASCADE_KEY` since that day. Read cold, that looks like two keys deciding
the same pool's fate by different lights. It is not, and there are four reasons in
a row.

**The cascade *contains* the rank key.** Above `solve.Q4_BAR` it orders on the
fine-tier head (`models/gallery_grade/`, fitted on human verdicts about pictures
that had already cleared the gate); below the bar it hands back each row's
`rank_key` value unchanged. So **below the bar the two keys are one order**, and
retention ranking on `rank_key` is already ranking on the cascade's own lower
half. There is no third key anywhere.

**The prune's population sits mostly below the bar, so the two mostly cannot
disagree.** A pair whose rows straddle the bar, or sit wholly beneath it, is
ordered identically by both. The disagreement can only bite where a prune's whole
decision is made among rows that are *all* above the bar — and that case had never
been counted until 2026-09-07. It is **877 of the 3,729 pairs at or over
`RETAIN_PER_PAIR`, 23.5%** and 23.6% weighted by rows; on those the two orders
name a different top row 70.6% of the time, and a different survivor *set* in 23.
Restricted to the pairs that actually delete something, the survivor set differs
in **23 of 30**. So it is rare that the question arises and near-certain that the
keys differ once it does. [`MEASUREMENTS.md`](MEASUREMENTS.md)'s *How much of the
prune is settled above the bar* carries the reading, including why real prune
decisions are not recoverable from any record.

**Seating-only was a ruling and the reason is containment.** A gallery's ceiling
holds a bad ordering *at a seat*: the row is still in the pool, `curate seat-sheet`
shows what the two keys disagree about, and the next solve reseats. `_prune_ranks`
has no such containment — it deletes the row and its picture permanently, and
[`MEASUREMENTS.md`](MEASUREMENTS.md) says why the deleted side of that decision
cannot afterwards be read back. A key adopted on one seating's worth of evidence
belongs on the reversible decision first.

**And `rank_key` cannot be retired while the cascade runs.** `solve.cascade_order`
builds the cascade out of `solve.ranking_for`'s `rank-key` mapping and lays the
fine head over its top; retiring `rank_key` would retire the cascade's below-bar
half with it. The two are one order, and that cuts both ways. **Deprecating
`rank-key` on 2026-09-08 is not that retirement**: what it took away is the
*offer* — `--key rank-key` is off `solve.OFFERED_KEYS` and a new gallery cannot be
seated on it by name — and it took away nothing else. `solve.KEYS` still holds all
three, `solve.ranking_for` still resolves it for a record that names it,
`_prune_ranks` still ranks on it, and the cascade still is it below the bar.

`curation/GALLERY.md`'s *`cascade` is the default since 2026-09-07* is the seating
half of this, and `tests/test_seat_sheet.py` pins that `_prune_ranks` reaches
`curation.rank_key` directly and names neither `DEFAULT_KEY` nor the cascade.

**The first cascade record is `20260908T144844Z`**, taken at n=1000 under
`--fine-bar 0.50`. Before it, all **62** records in the tentative store carried
`solve.config.sort_key_named` = `rank-key` — every one, published and unpublished,
counted 2026-09-07 — so anything read off a *tracked* stamp is still a rank-key
seating: the new record is unpublished, `tentative.latest()` resolves over
published stamps only, and every figure the site draws is on the old side of the
flip. What the record does close is the missing side of a comparison: a
cascade-versus-rank-key read at n=1000 no longer has to be derived against a fresh
in-memory solve, which is how `GALLERY.md`'s *The desire list is aimable at
cell × mode and nowhere else* had to take its reading.

### Putting a picture back

The prune was taken on an argument — **everything it removes is either retained
already or re-renderable from a retained recipe** — and `curate candidate-ledger
re-render` is that argument run as a command. It renders every picture the rows
still name and the disk does not have, and it selects on the retention rule and
nothing else: no bar, no mode roster, no clearing test. A second implicit picture
policy is what collapsing `KEEP_PER_PAIR` into the row rule deleted, and this is
the first place it would grow back.

**The same pixels, not similar ones.** Before any engine runs, each row's recipe
is rebuilt the way the *render path* builds it — palette knobs from the cyclic
set, the autolevel stamp from the shipped band — and digested. A row is rendered
only if that digest is the row's own key, because the scores and the flatness
reading in the sidecars were read on the pixels that used to be there, and
different pixels under the same name would silently invalidate both. Over the
57,135 rows this was first run on, **all 57,135 reproduced their own key** and
none was refused.

It writes pictures and nothing else — no row, no sidecar, no manifest.

Three numbers, measured on this machine on 2026-08-30 at three workers:

| | pictures a pair | wall | a picture |
|---|---|---|---|
| shared fields, sliced by row | 1.03 | 8.9 min / 240 | 2.23 s |
| **no** fields, same slice | 1.03 | 11.4 min / 240 | 2.85 s |
| shared fields, whole pairs | 2.49 | 6.6 min / 401 | 0.99 s |

**A shared field pays even for a pair with one picture**, which is the opposite
of what the mine's own numbers suggest — because the autolevel operator *paints
twice*, so one dumped field is amortised over two colourings before a second
picture is involved. So the leg takes whole pairs, and `--limit` slices by pair
rather than by row: a pilot that took one picture from each of many pairs pays
every dump and amortises none, and prices a leg that does not exist.

Two costs worth knowing. The cyclic-colormap set is read **once per worker** and
not once per task — there are thirty-two thousand tasks, and paying it per task
left half the pool idle behind a file read. And three engines already saturate
twelve cores, so effective concurrency tops out near **2.0**, not 3.0; that is
the three-worker rule doing its job rather than headroom going unused.

### The release pool's pictures come back the same way

`curate candidate-ledger re-render` is the ledger's. **`curate re-render` is the
pool's** — the release rows in the tracked store, resolved to the one candidate
render each is about. It exists because `curate rescore` refuses outright while
any of them is missing: a reading of most of the pool is not a reading of the
pool, and the pool's pictures live under the regenerable tree where a sweep can
take them.

**It read the gallery passes' attempt rows too until 2026-09-06**, when retiring
the gallery gate store took them out of `rescore.pool_rows()`. That is worth
knowing rather than tidying away: while it read them it put 3,530 attempt
pictures back that the orphan sweep had deleted the day before, which is how the
loop *The 09-02 sweep and `curate re-render` were a loop* records was found. The
pool is smaller now and the sweep no longer takes them, so neither half runs.

The adapter is `recipes.of_decision` rather than `of_record`, and the check is the
same one: the recipe the *render path* would derive is digested against the digest
of the row's own stored join, and only a row that reproduces is rendered. A row
that will not is recorded and skipped.

**A pool row is not a picture**, so the leg deduplicates before it renders. A
pass's attempt at an earlier run's candidate is a second row about one render, and
`origin_of` follows the `source` chain all the way down; on 2026-08-31 3,546 absent
rows named **3,484** absent renders. Rendering per row would pay for sixty-two
twice and would put two workers on one path.

Measured on 2026-08-31, three workers, over the 3,424 the leg proper took:

| | |
|---|---|
| reproduce their own recipe | **3,424 of 3,424**, 0 refused |
| made / failed | **3,424 / 0** |
| wall | **43.8 min** at 2.14 pictures a pair |
| a picture | **2.26 s** per engine, concurrency **2.95** |

That is **2.3x the ledger leg's 0.99 s** a picture at a comparable 2.5 pictures a
pair, and the difference is the frames: a pool location is a place a gallery pass
already liked, so it is deep and its iteration cap is high. Price a pool re-render
off this number and not off the ledger's. The concurrency is the other way round —
2.95 of three workers here against the ledger leg's 2.0 — because these pairs are
iteration-bound rather than contending on a shared dump.

`curate rescore` after it read all **16,029** rows in **280.7 s** (4,529 smooth,
11,500 strange) and put the whole pool on one artifact.

**A repair leg is a different regime from a bulk one, and 2026-09-07 is the
reading for it**: 38 absent renders, 38 of 38 reproducing their own recipe, 0
refused, 0 failed, **23.3 s wall** at 1.38 s a picture per engine. Concurrency
**2.25**, not the bulk leg's 2.95, because 38 pictures fall in 38 distinct
(location, mode) pairs — one picture a pair, so every dumped field is paid and
none is amortised, and the pool spends its time spawning. Price a repair off this
and a bulk leg off the table above. The pool went whole again in under half a
minute, which is the shape this command is for: `absent_pictures()` 38 → **0**,
and `curate rescore` stops refusing.

### What the rule costs

A dropped row is a recipe the `known` dedup in `hunt.run` and `mine.population`
can no longer see, so a later draw can pay again for a render this project
already made. That was the choice rather than an oversight: preventing it needs
an index of every recipe ever drawn, which grows with the attempts, which is the
thing being removed.

So it is **priced and never prevented**. Every merge reports `repeat_draws`,
read off the `k` each surviving row carries: a location showing three rows and a
deepest `k` of forty has had thirty-seven recipes rendered and dropped, and that
count survives the drop that made it. Over the store on 2026-08-29 it reads
116,097 invisible recipes across 12,774 of 18,424 locations — **a floor**, at
47.6% of the 243,720 actually dropped, because `k` counts within one leg and
32.0% of the rows predate the stamp. A floor is the right shape: the price is at
least this, and an exact figure needs the index this rule exists to not keep. If
the number turns out embarrassing, that is when something gets built.

### An upsert REPLACES, so a leg that offers a key the pool holds must not submit it

`records.upsert_file` carries a stored row's human `rejected` verdict across and
**nothing else**: everything else on the row — the picture, the provenance, the
`hunt` block, the colour, the engine field — is the incoming row's. That is right
for a leg re-merging its own partial and wrong for a leg whose rows *overlap*
somebody else's, which is a shape that arrived with
`curate label-migration merge`: the recipes it derives from the label stores are
candidate-geometry keys and **2,314 of its 5,329 scored rows stood at keys the pool
already held**. Submitting those would have rewritten 2,314 rows this leg does not
own, so the stage offers every scored row and submits only the keys the ledger
lacks, reporting both counts. It costs nothing to leave them: the byte-identity
sweep in the same store found 2,200 of the 2,314 staged pictures identical to the
ledger's own file.

**Where that leg's pictures live, and why it is not `scratch/`.** A staging store
is under `scratch/label_migration_<stamp>`, and `store.POOL_SUBTREES` bounds the
orphan sweep to `<subtree>/<leg>/pictures` and no other shape — so the merge stage
**moves** the pictures it submits to
`artifacts/curation/label_migration/<store name>/pictures` (a rename, same volume)
and `label_migration` is a member of that tuple. The leg name is the store
directory's own name, so `provenance.run` on a ledger row names the store it came
from and the store's name locates its pictures in the pool.

**`gallery-grade score-pool` has to run after any merge**, before a solve on the
cascade key: `pool_scores.jsonl` is written whole in one pass and merged rows carry
no `p_fine` until it is rewritten, which makes them unseatable rather than merely
unranked. Measured 2026-09-08: 41,407 above-bar pictures in **362.5 s**.

**And `retention.decide` prices the rank alone, so it over-predicts a merge's
losses.** The same leg priced **241 of 5,329 rows pruned on arrival** and the door's
prune dropped **3** — none of them arrivals. The five protections are the gap, and
one of them catches this shape by construction: `a_label_row_joins_to_it` saved 252
rows, and every row of a label-migration merge has a label row joining to it by
definition. A pricing off `decide` is a floor on what survives, not an estimate of
what is lost.

### A merge is not atomic across the prune, and a held file breaks it halfway

`candidate_ledger.prune` deletes the doomed **pictures first and replaces its three
files after** — the comment at the site says so — so the two halves fail apart. On
Windows the replace raises `PermissionError: WinError 5` when anything else holds
`rows.jsonl` open, and the `except` unlinks the three `.writing` temps and re-raises.
What is left is a store where the pictures are gone, the rows that named them are
not, and the ratchet never advanced — and the merge that called it has already
written its rows, so the failure is *after* the part that matters and reports
nothing. `dtm_lc_smoke` hit this on 2026-09-07: 870 pictures deleted, 870 rows
surviving, and `depth.merge`'s report — `repeat_draws` included — never returned,
because it is built after `candidate_ledger.merge` comes back.

**The holder is usually a `label serve` left running**, which is exactly the kind of
process nobody remembers is up. Close them, then re-run
`curate candidate-ledger prune`: it is idempotent, it re-deletes nothing
(`0 of 870 picture(s) deleted`), and it reconciles the store. **`repeat_draws` is
not recoverable** — it is read against the ledger as it stood *before* the merge,
which by then no longer exists.

**The key is the pixels and nothing but the pixels.** It is a digest of the
engine spec — through `renders.spec_of`, so this project has one derivation of
what a picture's engine input is rather than two — with two members dropped and
one added.

The dropped members are both paths. `output` is where a render went, and
`colormap_dir` is an **absolute path into the checkout**: `renders.job_name`
digests it, so a render-cache file name is different on every machine and
different again after a clone moves. That is harmless where it lives — a cache
file name means nothing off the machine that wrote it — and it is not harmless
for a store keyed forever.

The added member is the **autolevel band's sha256**. `band_autolevel/v1`
re-renders through a colormap built from `data/coloring/levels_band.json`, so two
candidates with one engine spec and two bands are two pictures, and no other
digest here carries it. The band's `acted` flag is deliberately *not* keyed: it is
derived from the render rather than an input to it.

`palette_group` is carried on the row and never keyed. It decides no pixels, it
comes from a tracked table a re-clustering can move, and a key that moved with it
would re-key rows whose pixels never changed.

**Joining a labeled row to this ledger: the geometry is not what stops you, the
place is.** A finished-render row is always a fresh 1280x720 ss2 render and a
candidate is 640x360 ss2, so the obvious guess is that the render block makes the
keys unequal by construction. It does — of a key nothing here computes. Every
reader that has actually joined the two builds the label side with
`regime=recipes.CANDIDATE_REGIME` rather than the row's own geometry, and every
one of the ledger's rows is at that regime anyway (`headroom.population` refuses
`off_regime` and the count is 0), so there is no geometry axis on either side to
relax. Measured 2026-08-28 over 9,427 labeled rows: a key with `resolution` and
`supersample` dropped from `Recipe.pixels()` joins **exactly** the rows the exact
key joins — 1,051 — merges nothing, and loses nothing.

What separates the rest is that their **place was never a candidate**. 1,129 of
the 9,427 sit at a location this ledger holds; 5,278 name a family it holds at a
frame it does not, and 2,961 name a family it has never seen. A further 59 are
reachable only by moving to the other side of a `location.framing` block, which
is a different crop and therefore a different picture. So **12.0% is the ceiling
of any reader-side place-based join**, and the join is not blocked by decimal
text: the raw viewport strings and the Decimal-canonicalised
`supply.location.key_of_row` agree on all 9,427 rows.

The consequence for a reader is that a labeled row without a ledger row has **no
`P(>=4)` to be compared against, and never had one** — the reading was not lost,
it was never taken. Getting one is a render leg, not a re-key: one 640x360 ss2
render each for the 8,382 rows that lack it costs about 48 core-minutes at the
per-mode medians the ledger's own `hunt.seconds` stamps carry, or roughly 16
minutes over the standard three-worker pool.

### The two retired artifacts were dropped, 2026-09-06

Matt approved it at ckpt 111 and it ran at ckpt 112. The sidecar held **574,162
rows over three artifacts**; the two that are not `floors.SCORING_HEAD`'s shipped
judge were **289,645 rows, 50.45%, 142,024,632 bytes** — and the file went
281,976,831 -> 139,952,199. The surviving 284,517 is exactly the ledger's row
count, which is the shape to expect: every recipe carries one reading on the live
judge and no recipe carries two.

**Nothing read them, re-derived on the day rather than off a note.** Every
`scores_by_recipe` caller in the tree joins on the live artifact — `remode` and
`rerender` name it explicitly, the rest take the default — and no test reads a
real retired sha. The one reader that saw them at all was `mine`'s
`stale_scores` census, which reports and never gates, and now has nothing to
report. **And no recipe lost its only reading**: over all four gallery passes,
`retired-only` recipes were **0** — gallery1 731, gallery2 1,723, gallery3 2,748,
gallery4 5,292, each fully present on the live judge as well. All seven published
records browse.

What it costs is the stated principle that a picture read by two judges is two
facts. The before-and-after comparisons those rows backed have been taken; what
cannot be taken again is a *new* comparison against those two scales, and
re-reading 284,517 pictures on a retired judge is about 47 minutes at the rate
above rather than impossible. `score_amendments.jsonl` was left alone and
references **no** retired artifact — all 88,571 of its rows carry
`head: "location"` on one location-judge sha, which is a different head and a
different store.

**A score is joined on ONE judge artifact, and the join says so.** The sidecar is
keyed `(recipe key, artifact, regime)` because a number is comparable only inside
that triple. Both readers that mattered — `mine.population` and `solve.pool` —
flattened it to the recipe key alone, which is last-row-wins across artifacts:
two judges' scales in one ordering with nothing anywhere saying so. The store
held **three** artifacts over 574,162 sidecar rows when that was written, so that
half of the key was live: what those joins were right by luck about had happened.
It holds **one** over 284,517 rows since 2026-09-06 — the guard stays, because
what makes the key right is the next adoption and not the current census, and the
morning after one this store is back to two.
`candidate_ledger.scores_by_recipe` is the join now — the live head unless a
caller names an artifact — and a row read on any other is **omitted**, not
rescaled. `stale_scores` is the census of what was left behind, so a caller can
say how much of its population it has no score for. A recipe with no reading on
the live judge has no score, which is honest and different from having an old one.

**The regime half of that key has no filter, so a second one raises.** All
284,517 rows are `640x360ss2`, and six production callers — `solve.pool`,
`rank_key`, `mine`, `sweep`, `models/render_grade.py` and `cli/curate_commands`
— pass no regime at all, so for them the join is last-row-wins across regimes.
What breaks it is not drift: `regime` is a keyed member of a recipe, so a recipe
key already names its own geometry and `recipe_key -> regime` is a function
while every writer stamps the recipe's own. It stops being one the first time
something scores a recipe's picture at a geometry that is not the recipe's, and
**re-scoring at shipping geometry is exactly that** — a thing this tree already
contemplates and calls a separate act. Naming the regime at those six sites is
the precondition for it; until then a second regime is an **error** rather than
a feature, and an unnamed read that finds one recipe carrying two raises and
names both. `curation/remode.py` built its own flattened join by hand and was
outside the guard until 2026-09-06; it now takes `scores_by_recipe` over a
generator filtered to its own population, which keeps the streaming pass its
docstring promises and inherits the refusal. **One reader is still blind, and it
is a writer's skip set rather than a join**: `candidate_ledger/rerender.py`'s
`rescore` builds its already-read set from `recipe_key` and the artifact alone,
so under two regimes a recipe read only at the other geometry reads as done and
is left unscored at the geometry the pool joins on. Recorded there, under *The
step a judge adoption makes necessary*'s own argument, and not fixed — there is
one regime in the sidecar, so it is a precondition and not a bug.

**The `colour` block is the reading, and every reader takes it off the row.**
Every one of the 85,129 rows carries one, so nothing downstream opens a picture
to ask what colour it is. There used to be a lens for the case where the reader
had no row — `ceiling.Lens` with a `stored_of` served by
`candidate_ledger.reading_source()`, which decoded a JPEG when the store had
never seen the render — and it went on 2026-08-28 with the pass that was its
only caller: both surviving readers walk rows. The block is
a **lookup and never a second derivation** — `dominance.of_block` carries the
dominant names outright, so a threshold moved since a row was written cannot
quietly re-decide that row. Verified on 400 rows sampled at seed 20260827: the
block round-trips exactly, and a live decode of the picture reproduces all five
members on 400 of 400.

**The colour read does NOT reuse the judge's decode**, and the resemblance to a
double decode is the trap. The judge reads the full 640x360, resizes it to the
head's input size and normalizes it; the census wants nearest-neighbour on
purpose, so every sample is a colour really in the picture. And the census never
does a full decode — `codebook.pixels` asks libjpeg for a quarter-scale draft
straight to 160x90, **1.8 ms** against the judge's own full decode at 2.4 ms
over a 60-picture sample. Handing the judge's buffer over would cost more than
it saves. The `colour` stage's 12.3 ms is `codebook.shares`, 10 ms of it; the
decode is 15%.

**The `hunt` block says what the draw intended, `k` included.** A row made by a
hunt, a mine or a depth run carries its leg, its mode and colormap, the band or
cell it was drawn *for*, and `k` — which candidate at its location it was. `k`
is on the ledger row and not only in the run's own `sequence.jsonl` because
those live under `artifacts/` and the ledger does not, and the corrections a
reader has to make to a prime count are `k`-dependent: a rate read off the
maximum of `k` noisy judgements is a winner's-curse estimate and its multiplier
is a function of `k`. The field is **additive** — none of the 85,129 rows
written before it exists carries one — and `candidate_ledger.k_of` answers
`None` there rather than 1, because a missing `k` read as a first draw would
report that whole history as unselected and under-correct every estimate over it.

**The identity is the recipe, never the location key**, and that is what makes a
superseded framing a re-key rather than a rebuild. Framing refinement is moving
into harvest, where a refinement **moves** the location key
(`supply.ledgers.refined_of`) — so when it lands, the rows standing on the old key
keep their pictures and their colours, and one field changes:
`location.superseded_by`, beside `location.key`.

Both keys are on every row and neither is reconciled. The gallery pass pins a
location's identity to the frame on record while rendering somewhere else inside
it, which is what stops one place taking two seats — so `location.key` is that
recorded identity and `location.frame_key` is the identity of the frame the
pixels are of.

**`framing.used`, never `framing.adopted`.** The fallback leg re-renders a
location at its recorded frame after every refined attempt on a slot lands under
the bar. A cache keyed on what was adopted would file every one of those under
the refined frame's name.

**Record everything; filter nothing.** No quality bar admits a row: a floor is a
reading of a judge and both move, the recipe and the pixels do not. A row a
person *rejected* is in the ledger with its rejection on it, for a solver to
honour rather than to rediscover.

**Scores are a sidecar**, keyed `(recipe key, judge artifact, regime)`, because a
judge adoption invalidates every score in this project and nothing else. It also
makes the comparison honest: a recipe two passes both drew appears twice if two
artifacts read it.

**What the backfill found, on 2026-08-26.** 16,029 decision rows over the two
stores collapse to **15,488 renders** — 90 of the rows are re-stamps of a picture
another row made, and 451 are one render's gate row and release row, which are
two decisions and one JPEG. Those 15,488 renders are **15,362 recipes**: 126
renders were the same recipe drawn twice by two different passes, and every one
of the 128 pairs is byte-identical on disk. At 2.05-3.1 s an attempt that is four
to six minutes nothing needed to spend, and it is the number the cache exists to
drive to zero.

The 128 identical pairs also measure the judge: 59 of them disagree on `P(>=3)`,
the largest by 2.8e-7. Identical bytes, same artifact, seven decimals of
agreement and no more.

Every render is at one regime (640x360 ss2), every one still has its picture on
disk, none is recipe-only, and **no candidate render in any pass or any run
carries an engine stamp** — `engine_fingerprint` stamps a view directory and
candidates were never written to one — so the whole backfilled pool is
pre-stamp material accepted as unknown-engine, by rule. **That population is
182,132 rows** [measured], the candidate rows written before 2026-09-02; the pin
guards views only, and Matt's ruling is that pre-stamp material is accepted as
unknown-engine rather than re-rendered.

**A row written from 2026-09-02 says which build drew it, and nothing acts on
it.** `candidate_ledger.row` takes the identity digest — `engine_fingerprint`'s
six `IDENTITY_PROBES`, the one digest a stamp carries — under the top-level
`engine` field, and the three legs that write rows (`hunt`, `mine`, `depth`) ask
for it **once, before their render loop**, through `candidate_ledger.live_engine`:
the first call costs six probe renders and is cached for the process, so a
per-row ask would have hidden that cost across a hundred thousand rows. An engine
that will not fingerprint gives `UNKNOWN_ENGINE` rather than raising — a leg that
has already made pictures must not fail while writing them down.

It is **provenance and never a gate**, which is the whole ruling. The field is
outside `recipe`, so no recipe key moves and no picture is re-rendered for having
been stamped; `finished.check`, `curate solve` and `curate headroom` do not read
it; and a row whose stamp disagrees with the live build is admitted, scored and
seatable like any other. `candidate_ledger.engine_of` is the one reader-side
spelling and a missing field reads `unknown`, which is what the whole standing
pool is. Existing rows are untouched and there is no backfill: a backfill
**carries** whatever stamp a row already had rather than stamping it with today's
build, because the decision stores it re-derives from say nothing about an
engine. The cost is about **30 bytes on a ~1,290-byte row, 2.3%**.

**The census, at N=20.** Nothing binds. All 48 colour cells, all 12 families, all
18 production modes and all 822 drawable palette groups are held; none is empty.
The 20-point draw under the hard radius fills, with 79 locations refused by it.

What is *thin* is places and green. The ledger stands on **1,223 locations** —
2 recipes at the 25th percentile, 8 at the median, 44 at the deepest — so depth
per place is not the constraint and breadth of place is. And the green half of
the wheel is a quarter of the red half: 986 locations carry red, 248 carry lime,
258 green, 324 teal. The thinnest cell of the 48 is `dark_vivid_lime` at 44
locations. 227 of the 822 palette groups have exactly one recipe behind them.

## One field, many palettes — how a candidate is made

**`colorize.render` is still THE one place a curation picture is made, and it now
has two ways of making one.** Which one serves a candidate is not a caller's
decision and no caller can see it:

* a **field** coloring — seven of the nineteen production modes — is dumped once
  per `(location, mode)` into the unit of work's own `fields/` directory, and
  every palette at that pair is an `engine recolor`: a colormap lookup over an
  array on disk, with no iteration behind it;
* a **composite**, the two **modulates** and the **direct traps** have no single
  scalar field, the engine refuses to dump one, and those take the full render
  they always did. The refusal is remembered against the mode, so a mine that draws
  `threads` four hundred times pays for it once.

A caller opts in by naming a `fields=` directory — `hunt.Maker` and every mine
through it do, `colorize.Colorizer` uses the same directory its palette head's
own recolours already lived in — and what it is opting into is *where the cache
goes*, never *which path runs*. `colorize.sweep_fields` keeps the newest
`FIELDS_KEPT` (64, about 200 MB at 3.5 MB a field) and `field_of` touches on the
way past, so a field being spent on its tenth palette is not the oldest thing in
the directory.

**The recoloured picture is the rendered picture, byte for byte.** That is a test
and not a claim: `test_a_recolour_is_the_render_byte_for_byte` renders every
shareable mode on two planes through a folded map and a cyclic one, with the
autolevel operator on, and compares file digests. Over thirty candidates the
ledger already held, re-made through the new path: **30/30 recipe keys identical,
30/30 pictures byte-identical, 24/30 judge scores bit-identical and the other six
within 2.7e-7** — GPU inference noise over identical input bytes.

Two things had to be right for that:

* **The dump goes through `renders.spec_of`, not through a mode name.** A field
  dumped by name carries the *catalogue's* curve into its record, and
  `trap_circle` names `log` where curation renders through `linear` — so a
  recolour that inherited the record's curve would be a different picture for
  that one mode and for no other. The field's cache name (`renders.field_job_name`)
  and the spec it is dumped from are held to being one derivation by a test.
* **`engine recolor` applies the recipe's rolloff.** It used to call `shade` and
  stop, which was the render for exactly as long as every recipe in this project
  carried `rolloff: none` — a property of today's recipes rather than of the two
  paths. `coloring::toned` is now the one owner of that stage and both halves call
  it; `test_a_recolor_reproduces_the_render_through_every_stage_of_the_recipe`
  pins all four curves.

**The autolevel operator's second pass is a colormap swap over the same field**,
so on a shareable mode it is a second *recolour* rather than a second iteration
pass. That is where most of the saving lands, because 47.7% of candidates level.

**What it is worth, measured by `curate mine bench`** on nine never-opened
locations, eight maps each, the same location priced both ways:

| k | field before | field after | saving | composite |
|---|---|---|---|---|
| 1 | 0.976 s | 0.673 s | 14.1% | no change |
| 8 | 0.976 s | 0.217 s | 51.8% | no change |
| 20 | 0.976 s | 0.178 s | 55.0% | no change |
| 40 | 0.976 s | 0.165 s | 56.1% | no change |

A bare recolour is **0.041 s and flat in maxiter** where the render that made it
ranges 0.06–1.54 s. There is a saving even at k=1, and it is the autolevel pass
alone; everything above k=1 is the dump amortising.

**And on production's own mix**, `val2` against `mine1` at k=1, with the untouched
code paths correcting for the population: **field colorings 42.7% cheaper a
candidate** (54.0% on the 57% the curve fires on), **the whole loop 22.7%**. What
cannot share a field is 44.5% of candidates and 64.1% of the clock.

### A glance sheet at label geometry is the same sharing, and two numbers move

A hand-cut sheet that asks *what does this map look like* is the sharing turned
sideways — a few places, every map at each — and it is `colorize.render` with a
`fields=` directory and `render_geometry` set to `sheets.LABEL_RESOLUTION`, so what
an eye rules on is the picture the map would ship. `CHECK_dud_maps_0905` cut one
that way, ten maps at four places: **40 pictures in 11.6 s at three workers**, four
dumps, and the operator acted on **37 of 40**.

**A field at label geometry is 14.06 MiB, not the 3.5 MiB above.** That figure is
candidate geometry; 1280×720 at supersample 2 is four times the samples, and
`FIELDS_KEPT` at 64 would be 900 MB rather than 200. A driver that dumps at label
geometry sweeps its own `fields/` when it finishes instead of leaving them to
`sweep_fields`, which is sized for the smaller one.

**Three threads over `colorize.render` buy 1.67×, not 3×**, measured the same day
on 32 pictures over these four places: 0.569 s a picture serial against 0.341 s at
three. The engine is a subprocess, so threads are the whole pool and none of
`LEGS.md`'s *a scratch driver that drives a render pool needs a `__main__` guard*
applies — but the operator's `measure` stage is Python over a decoded JPEG, and at
this geometry it is enough of the clock to hold the concurrency under two. More
than three threads is still the desktop-usability rule and is not the lever; fewer
places and more maps at each is.

### `mine.make` dropped `mode_params`, so every varied candidate in the pool is the bare mode's picture

**Fixed 2026-09-08 in `FIX_ckpt116_mine_mode_params_0908`; the 10,664 rows already in
the pool were left as they are, deliberately.** What follows is what the defect was
and what it cost, because the rows are still there.

**It was one missing keyword.** `hunt.Maker.make` passes
`mode_params=dict(plan.mode_params or {})` into `colorize.render`; `mine.make` — the
call every `curate mine` and every `curate depth` leg actually renders through —
does not, so the parameter defaults to `{}`. A leg that names
`direct_trap_multiply@opacity=0.6,threshold=0.2` on its roster therefore *records*
the variant on its row, takes the variant's own recipe key (`mode_params` is in
`recipes.KEYED` and reaches the digest through `engine.coloring`, so the key is not
the problem), and **renders the bare mode**. `mine.make`'s own docstring claims it
is `hunt.Maker.make` "with the single `seconds` split eight ways and nothing else
altered … at the same recipe", which is what kept this invisible.

Measured 2026-09-08 over the pool: **10,664 rows carry a non-empty `mode_params`,
across thirteen legs, and every leg sampled has its stored picture reproduce
byte-for-byte as the bare-mode render.** Four probed rows a leg, own-params render
against bare-mode render against the stored file: bare matched 4/4 in every leg.
`dtm_lc_smoke`'s pictures are dated 2026-09-07, five days after the roster feature
landed, so this is not the pre-`52d6d80` era being rediscovered.

`direct_trap_multiply` is the only mode that has ever carried settings, so the
damage is bounded to it — and it is not only the pictures: each row's judge score
is a reading of the bare picture under the variant's key, so the whole
`dtm_variants` programme compared a mode with itself. The clean proof came from the
other direction, in `curation.label_migration`'s byte-identity sweep: 123 of 123
varied-dtm rows whose staged redraw differed from the ledger's file have a
**bare-mode** redraw that is byte-identical to it.

**A second renderer had the same hole and it would have undone the fix.**
`candidate_ledger.rerender.render_pair` — what puts a picture back — built its engine
spec by naming four members of `recipes.KEYED`, so a restored varied row was the bare
mode's picture; and `re_render`'s key guard rebuilt each row's key with `mode_params`
pinned to `{}`, so every varied row failed it and was refused. Protective by accident,
and it would have gone on refusing them after the pictures were correct. Both fixed
with the keyword, and the guard now rebuilds with the row's own settings — the row is
the only place a leg's chosen settings exist.

**The guard is one test over every renderer, and it had to be widened once already.**
It began as `tests/test_mine.py::test_the_two_makers_draw_the_same_picture_for_one_recipe`
over three renderers. The tree has **eight**, four more were found dropping `curve` and
`palette` the same week, and a registry somebody has to remember to add to is a registry
that goes stale — so it is now `tests/test_renderer_agreement.py`, which renders one
recipe through every renderer, compares the **bytes**, requires the bare arm to differ so
a guard on settings that move no pixels cannot pass, and **sweeps the tree for
`colorize.render` call sites** so a renderer added later is either covered or declared
exempt with its reason. An assertion that each site passes `mode_params` would have
caught this one argument and nothing else — and it did exactly that.

**What it cost, measured on the seats.** Twelve of the 1,000 seats of
`20260908T201911Z` carry a non-empty `mode_params`; seven of their stored pictures
were the bare mode's and were re-rendered. **Six of the seven collapse once the file
matches its key** — `P(≥4)` 0.94→0.002, 0.97→0.018, 0.95→0.011, 0.83→0.000 — so six
seats were held on a picture the pool would not have chosen. The record was
deliberately **not** re-solved: thousands of varied rows in the pool are still bare
under their own keys, so a fresh solve would be differently wrong rather than more
right.

**The rest of the pool was repaired on 2026-09-08 in
`PRECLOSEOUT_ckpt116_renderer_holes_and_repair_0908`.** All 10,664 were re-rendered
through the fixed path and re-scored, because every standing reading on them was about
another picture. `curate candidate-ledger bare-varied` is what names them: a row carrying
settings whose picture's path is under neither `hunt` nor `label_migration` went through
`mine.make` and was drawn bare, which is `label_fate.drawn_bare`'s rule reached rather
than restated. What that repair did **not** do is re-solve — see the next section.

### `release.Task` had the same hole twice more, and `curve`/`palette` was the second

`mode_params` was added to `release.Task` on 2026-09-04 after twelve release renders
of varied seats came out bare. **The same argument applies to `curve` and `palette`
and they were not there**: both are `recipes.KEYED` members, so a row whose recipe
names a `log` field or a sampled `gamma` renders — through the release path — as the
*plain* picture under that row's name. It went unnoticed while the pool held only
plain-recipe rows; `label_migration merge` ended that on 2026-09-08 by putting 3,015
rows derived from the two label corpora into the pool, a third of which carry knobs
the candidate path never spends. Both are on the task since `curate label-fate`,
default `None`, so every candidate leg renders exactly as it did.

### The fix was one builder, not four more keywords

**Closed 2026-09-08, and the closure is structural.** Five legs turn a stored row into
a release render — `solve.render_seats`, `checks.tasks_of`, `run`'s release leg,
`votes.render_fulls` and `label_fate.render` — and every one of them spelled the task
out inline. Four passed `mode_params` and dropped `curve` and `palette`. Two guards in
`tests/test_curation_release.py` counted `mode_params=` and `autolevel=` per builder and
were **green through all four**, which is the argument against fixing this by adding
keywords: the next member is the one nobody counted.

So there is now **one** builder, `release.task_for`, whose picture-deciding parameters
have no defaults. Forgetting one is a `TypeError`; a member added to `recipes.KEYED` is
added to one signature and every leg fails until it says what it passes. The guard is
correspondingly structural — `release.Task(` is constructed in exactly one place in the
tree, and the five legs are named as still going through it so a leg that quietly
stopped releasing is not read as compliance.

Two more renderers were fixed with them. `shrinkage._render_one` dropped all three
members **and** re-measured its levelling at label geometry rather than inheriting the
candidate's decision — pre-`87ad3eb` behaviour, and a second uncontrolled difference
inside the one quantity that module exists to measure, since a shrinkage read is defined
as *the geometry and nothing else moves*. It now reads the recipe through
`recipes.of_record` and takes its borrowed curve from `stamps.for_release`, batched in
the parent. `manufacture`'s render arm passes the row's settings; its recolour arm needs
none, settings being legal only on a direct trap, which has no field to dump.

### The `curve`/`palette` refusal was one rule doing two jobs, and a NEW MAP is neither

`render` refused a `fields=` directory beside **either** override. Read from the split
that decides it, the two halves fail differently and only one of them was ever about the
cache — so **since 2026-09-11 the refusal is the curve's alone**, and a palette override
rides the cache. `recolored` takes the whole pass; `test_a_recolour_is_the_render_byte_for_byte`
sweeps three of them and a second guard holds each path to the pass actually *moving* the
picture, because two paths agreeing is also what you get when both of them ignore it.
The split below is why, and it is unchanged apart from the verdict.

**The map is not in a field's identity at all.** `renders.RECOLOR_MEMBERS` is `colormap`
and `recipe`, and `field_job_name` pins both to constants — `FIELD_COLORMAP` and
`finished.recipe(mirror=False)` — so what a dump is a function of is the place, the
geometry, the mode and the curve, and nothing else. That is the whole of why one
iteration pass serves thirty-two candidates, and it means **a map this repository has
never rendered before is served by the field cache exactly as a shipped one is**.
`mirror` rides along with it: `recolored` takes it as a parameter and it is the one knob
of the seven a recolour does not pin, which is why a map's `kind` can vary over one
dumped field.

* **`curve` is field-side** (`renders.FIELD_IDENTITY`) and the hole is a call site rather
  than the cache: `_shared_field` never passes a curve down to `field_of`, and
  `engine recolor` reads the transform out of the dump's own record when the spec leaves
  it unsaid — so an overridden render served from the cache would paint the `linear`
  field wearing the override's name. `field_job_name` already digests a curve, so each
  distinct one would simply get its own field.
* **`palette` was recolour-side** and the hole was a dropped argument: `recolored` wrote
  `_plain_recipe(mirror)` and threw the other six knobs away. The Rust `RecolorSpec`
  already carried a full `Palette` and `fn recolor` spends it through `coloring::shade`
  and `coloring::toned` exactly as `fn render` does, so nothing about the cache ever
  stopped this. **Closed in `palette_variant_mine_ckpt120`**: `recolored` takes a
  `palette`, defaulting to the plain pass of its `mirror` so every call that predates it
  reads as it did, and `render` hands it the pass it keyed the row under.

**What that bought and what it cost.** A varied palette is now a **recolour**, so
`curate depth --vary-palette` prices its varied rows the way an unvaried leg prices its
plain ones on the three shareable modes — which is the only thing that makes *varied
against unvaried inside one leg* a comparison rather than two legs at two prices. The
phase sweep of 2026-09-11 is the demonstration: 100 points over 5 seats, twenty phases
each at candidate geometry, **50 s of wall on three workers** — five dumps and ninety-five
recolours where the old refusal would have made it a hundred renders.

`curve` keeps its refusal and `curation.candidate_ledger.rerender` keeps a refusal that
now names the curve alone. The one thing still unmeasured is whether a **levelled**
repaint composes with a non-identity `gamma` or `transfer`; the passes compared are
`phase` and `cycles` over the plain defaults, which is what the varied draw spends.

### A leg whose maps are not in the tracked library cannot go through `colorize.render`

`render` gives its first paint no way to reach another colormap directory —
`engine_spec.spec_of` hard-wires `paths.colormap_dir()`, and the only directory `paint`
ever takes is the autolevel operator's own levelled copy. It also reads the map's stops
out of that same directory to hand the operator. So a leg holding its maps elsewhere
calls the two halves itself: `colorize.field_of`, then
`colorize.recolored(..., colormap_dir=...)`, then `autolevel.maybe_level` with a
`rerender` that writes through `autolevel.overriding_colormap` into a scratch directory.
That is `render`'s own body with one string changed, and it is what
`palettes/README.md`'s *Variants — one map, one axis moved* was rendered through.

**What it costs, measured over 22,880 pictures on 2026-09-10** at candidate geometry
across `smooth`, `stripe`, `curvature` and `tia`: one recolour **62.3 ms**, the operator
28.0 ms when it does not act and 217.3 ms when it does — **186.1 ms of worker time a
candidate**, 66.4 ms of wall at the three-worker pool. The same places by the render path,
both levelled, run 1.5x to 2.1x that (smooth 151→315 ms, tia 91→137 ms), and the dump
being amortised is 0.05–0.20 s once per (location, mode). The ratio is this low because
half the clock is the operator, which both paths pay, and because candidate geometry is
small; the `curate mine bench` table above is the same measurement where iteration
dominates.

## `curate label-fate` — what became of every GALLERY-GRADE wallpaper somebody graded 4

Three stores hold a human 4 — `data/smooth_render/`, `data/strange_render/` and
`data/gallery_grade/` — and since `label-migration merge` every one of those verdicts
is a **ledger row by key**. So the question stops being *how does the pipeline score
pictures a person liked* and becomes *what happened to this one*, which has an exact
answer per row. Five rungs, first one that stops it: off the roster, below the coarse
bar, below the fine bar, refused by a named rule, seated.

### It reads ONE of the three, and which one is the whole point

**`data/gallery_grade/` alone since 2026-09-09** (`label_fate.STORE`). The page read
all three until then and put them on one index, which conflated two populations that
mean different things. A gallery-grade 4 is a verdict on **a candidate this pool
holds**, taken off a sheet drawn from the pool itself; a finished-render 4 is a
verdict on a picture from the finished corpora, carried back to a ledger key through
`label_migration.recipe_of`. **Whether a coarse-store 4 is a gallery-grade 4 is
unanswered** — nobody has graded those rows on the gallery-grade scale — so a fate
page over both asks a fate question of rows whose membership in the population is
itself the open question. That is a different question and it does **not** get a
second page here.

**The split is visible in rung 0 and rung 1, which are now empty.** Of the 312
gallery-grade 4s, **312 are in the ledger, 0 off the roster and 0 below the coarse
bar** — necessarily, since the sitting was drawn *from* the pool. Every one of the
117 off-roster and 492 below-coarse rows the old page counted was a finished-store
row, and reading them beside the gallery-grade ones as one distribution read a fact
about the *carry-back join* as a fact about the pipeline.

**Rung 0 stays in the vocabulary anyway.** `solve.pool` refuses before any bar runs —
a mode `mode_policy` weights 0, a recorded rejection, a swept picture — and folding
those into the coarse-bar count would say a bar refused a picture no bar ever read.
It is decided on `mode_policy.routed_mode_of` and not the recipe's mode, so a
modulate whose texture moved nothing is judged as the smooth picture it is. It reads
0 today because of what the population is, not because the rung stopped existing, and
a sitting drawn some other way would fill it.

**`p_fine` is recognition for every row on this page, and the page says so once.**
The population **is** the fine head's own corpus — 245 fitted on and 67 in its
stopping slice, `label_fate.FINE_TRAIN` + `FINE_STOPPING` = 312, the whole of it — so
the column the page sorts by is the head reading rows it was fitted to. The human
grade beside it is the only independent thing on a card. That is stated in the lede
and as the first line of the legend rather than in a footnote, because it is the one
caveat a reader who stops early has to have read. It is also why this is a page about
**fate** and not about accuracy: which rule stopped a wallpaper somebody wanted is a
question the record answers exactly, and how either head would score an unseen picture
is not a question this population can be asked. The old page's *two* contamination
figures went with the finished stores — `JUDGE_TRAIN`, 1,271 of the finished-render 4s
inside the render judge's own train side, is retired with them.

**Rungs 3 and 4 need `--explain-keys`, and that is the whole reason the flag exists.**
The fate of a row that took no seat lives only inside the pass that refused it:
`solve.rejection` keeps aggregates, and `rejection.explained` keeps one entry per key
*asked about*. A record can only be asked while it is being taken, so
`curate label-fate keys` runs **before** the solve and writes the manifest
`curate solve record --explain-keys` reads. `fates` refuses a record with no
`explained` block and one whose block does not name every row of this population —
a rung recovered from the aggregate columns would be a guess about which of several
rules acted first, and ending that guess is what joining the corpora to the ledger
bought.

**Both sides of a card are drawn fresh at one geometry**, because
`sheets.LABEL_RESOLUTION` and `release.RELEASE_REGIME` are the same `1280x720ss2` —
the geometry a person judges at and the geometry a wallpaper ships at. `render`
refuses if those two constants ever move apart rather than quietly drawing a pair at
two sizes. Each render is told the row's whole recipe (`mode_params`, `curve`,
`palette`) and **inherits** its levelling through `stamps.for_release`.

### The picture beside a refused card is not the seat at its place, and that took two goes

A card pairs the graded wallpaper with what beat it, and **which picture that is
depends on the rule that refused it**. The first version of this page paired every
card with the seat holding its *location*. For the 348 `cell_allowance` refusals that
is simply the wrong picture: the row that beat them filled the colour cell and stands
somewhere else entirely, and the seat at their own place had nothing to do with it.

**The pairing is `rules.State.counted_requirements`' own set for the rule that
refused** — the seats that rule would accept a departure from — with the **marginal**
member shown where the set has more than one: the weakest by the pass's own seating
key, which is the seat a 1-swap ejects first. `location` gives a one-member set, so
the seat at the place *is* the answer there and always was.

⚠ **It is deliberately not `rules.State.removals`**, and the difference cost a rebuild
to notice. `removals` intersects the requirement sets across *every* rule a candidate
fails and answers the stricter *would one seat leaving be enough*. **101 of the 102
location refusals here also fail the cell allowance**, so their intersection is empty
and `removals` names nothing — while the seat at their place plainly beat them. Both
are worth knowing, so the intersection is reported per card as *no single seat leaving
would have been enough* rather than used as the pairing. It is true of 234 of the 453
paired cards.

### The subtraction on a card is not a margin, and the card now says which leg placed the seat

**The `gap` column was renamed `p_fine Δ` on 2026-09-09 and the old name was
wrong**, measured rather than suspected — `forced_seating_20260909`, Part A. It
reads as *how close this row came to a seat* and there is no such quantity on this
page: the rule that took the row compared no scores at all. `cell_allowance` is a
**count** against an allowance, `location` is a seat standing in a cluster, and
the competitor beside either is picked **after the fact** as the marginal seat —
the two rows never met. 127 of `20260909T173957Z`'s 173 paired cards carried a
negative value, which reads as *I scored higher and still lost* and is simply what
a rule that never read a score does.

**So the fact that explains a negative one goes on the card ahead of it: the leg
that placed the competitor.** Of those 105 negative `cell_allowance` competitors,
**zero** came from the ranked walk — 47 from `swap`, 47 from `augment`, 11 from a
mode floor's mandate. `general_pool` is the only leg the seating key orders; the
swap and the chain accept on the lexicographic objective and a mandate walks one
demand's subpool scarcest-first, so a seat from any of the other three says
nothing about how the two rows would have compared. A card whose competitor came
from the ranked walk gets no disclaimer, because there the two orders did meet.

The column itself stays — a competitor reading 0.01 above a refused row and one
reading 0.4 above it are different findings — under a label that cannot be read as
closeness, with the disclaimer beside the number and once at the top of every
refused slice.

**Under the colour floor the leg column is MORE load-bearing, not less.** Re-read on
the `K = 3` + floor record, the competitor was placed by a **mandate** on 103 of 144
cards — 50 `cell_floor` and 53 `mode_floor` — by `swap` on 14, and by the ranked walk
on only **27**. So 66 of the 81 negative-delta cards are now against a seat that no
seating key ordered at all, where before the floor existed the mandate accounted for
11 of 105. Adding a soft demand adds a leg that does not read the column the card
subtracts, so the disclaimer is doing more work on every record taken since
2026-09-09.

⚠ **The 0 / 0 / 64 / 175 / 73 above is a `K = 2`, no-floor, `p_fine ≥ 0.50` reading
and does not survive either ruling.** Rebuilt on the `K = 3` + floor record the same
312 rows read **0 / 0 / 64 / 168 / 80** — seven more of the graded 4s ship, with 25
refused → seated against 18 the other way and 269 unchanged. And the fine head's
adoption moved rung 2 itself: `label_fate`'s second rung **is**
`solve.DEFAULT_FINE_BAR`, so a fate readout taken after 2026-09-09 sits on a
different rung boundary *and* a different column, and no two of these three readings
are comparable. Read the rungs off the record's own `config.fine_bar` and
`config.fine_head`.

**Every count in this section is one record's**, `20260908T211552Z`, which is what
made the shape visible. The same population re-solved against the repaired pool as
`20260909T061451Z` reads 350 / 99 / 72 / 3 by rule against 348 / 102 / 71 / 3, 452
paired over 114 distinct rows, 218 where no single departure would have been enough,
and a rebuild reproducing 449 of 449. **The proportions are the finding and the
integers are not** — a greedy seed plus swaps plus augment lands somewhere else under
any perturbation, and only 892 of 1,000 seats survived this one.

**Those three are three-store readings.** The gallery-grade population alone, over
`20260909T173957Z` — the pooled fold, the fine bar at 0.50 — is **312 rows: 0 / 0 /
64 / 175 / 73** across the five rungs, and the 175 refusals split **120
`cell_allowance`, 51 `location`, 3 `twin`, 1 `spiral`** with **zero**
`another_place_is_the_same_place`. 173 paired over 77 distinct rows, 87 where one
departure would have been enough, 2 unpairable. The shape the narrower page makes
visible is that `cell_allowance` is more than twice `location` here: what stops a
wallpaper a person wanted is far more often the colour ceiling than another picture
at its own place.

**A pooled pass never writes `another_place_is_the_same_place` at all.** Since the
fold merges instead of deleting (2026-09-09), a row that loses its cluster's seat to a
sibling place is refused by the ordinary **`location`** rule, and its card carries the
sibling, the cluster the two are seated under, and **both spokes of the star** — each
place's neutral distance to the survivor, never the distance between the two, which
`distinct.suppress` does not measure. `label_fate._fold` is where a `location` card
gets that decoration, and it fires only where the seat that took it is at another
place. Today's record writes **zero** of the old refusal.

The constant is still read, because a record taken before that fold explains itself:
there the whole place went at pool construction, before a seat existed, and the card
names the place that absorbed it off the record's own `preselection.refusals` with the
distance the fold was taken at. `competitors` reads `refusals` on a destructive record
and `folds` on a pooled one — the same rows either way, and the second name exists
precisely because nothing was refused.

**The rebuild is proved before it is used.** `competitors` reconstructs the pass's
final `rules.State` from `solve.pool` and the record's own ceiling, then requires
`counted_refusal` to reproduce every refusal the record wrote down — 450 of them, exactly
— and refuses outright otherwise. The two it cannot be asked about are excluded by name
rather than by silence: `twin` is the diversity rule's, kept per key in the record's
`diversity_refusals`, and `another_place_is_the_same_place` is pool construction's. The
first run of the verb reported a 71-row disagreement that was exactly those, which is
the guard working.

### The page is an index and 21 slices, not one page

2,107 cards on one page is 2.1 MB of markup over 4,214 lazy images and the browser
stalls on it. Pages hold **150 cards** (`label_fate.PAGE_SIZE`), the rung is sorted
`p_fine` ascending and *then* cut so the split never reorders, and page 1 of a rung is
always its largest disagreements. Names are guessable — `below-the-fine-bar-03.html` —
and every page carries prev/next and a link back. **The refused rung is written twice**,
once by `p_fine` and once split by refusing rule, because those four are four different
questions.

**`OFF THE ROSTER` is counted and not shown**, Matt's call: no bar read those 117 rows
and no rule refused them, so there is no comparison to draw. The index carries the
count so the rungs still add to the population.

## `curate retention` — what survives what the rule drops

```
src/fractal_wallpapers/curation/retention.py   the policy, the aggregates, the report
```

```
fractal-wallpapers curate retention             # the three counts a discard must not destroy
fractal-wallpapers curate candidate-ledger prune --dry-run   # what a prune WOULD do. THE dry run
```

**Storage has to scale with the locations explored, not with the attempts made.**
At ten million attempts the ledger's rows are about 5 GB and the 640x360 JPEGs
they name are about 600 GB. The rows are the cheap half and the half that answers
questions; the pictures are the dear half and almost none of them will be looked
at again.

**Rows are never dropped. Only pictures are.** Every attempt keeps its recipe row
and its `colour` block forever — recipe-key dedup is the ledger's whole reason for
existing, and a pass that could not tell it had already made a picture would
re-render it. What goes is the JPEG the row points at.

**What is kept, and why each rule is the rule it is:**

* **Top 5 per (location, mode), ranked WITHIN the pair.** Not against an absolute
  probability: CORN's scale is train-prior calibrated so every retrain moves the
  probability axis under a fixed cut, and the per-mode crossovers already span
  0.367 to 0.950 — one number cannot be the bar for all of them. A rank inside a
  pair asks the same question at every mode and survives a retrain. A row with no
  score ranks last rather than being dropped outright: a picture nothing has an
  opinion about is not a picture something thinks little of.
* **Every row that ever carried a HUMAN label, unconditionally.** Outside the
  ranking entirely. A labeled picture is instrument — what a judge was trained or
  measured against — and losing it costs a number nobody can re-derive. The join
  is `labeling.finished.render_key` and it is on the *recipe*, never the regime:
  a person who judged this colouring at 1280x720 judged this colouring.

  **Every corpus that judges a picture, and not only the two gates.**
  `retention.labeled_renders` reads `labeling.gallery_grade` too, keyed through
  the same function, because a grade is a person's verdict about a picture and
  the store is the population a conditional head is fitted on. Its runners-up —
  the near neighbours the solve refused, which are the hard negatives that head
  has to learn from — are named by no record, so the rank drops them routinely.
  Measured 2026-09-06 before this line existed: **233 of 300 held by nothing, 95
  of them carrying a `<stem>.leveled/`**, which dies with the JPEG it sits beside.
  See `data/gallery_grade/README.md`'s *What holds them now* for where the join
  lands, and `tests/test_gallery_grade_retention.py` for the pin.
* **One in 200 of the rest, flagged.** A store holding only its winners cannot
  answer why anything lost. `in_reservoir` is a sha256 of the recipe key and not a
  draw, so the same set is kept in every process that asks — the builtin `hash()`
  is salted per process and would keep a different tenth of a percent every run.

**Three aggregates, all bounded by their key space and not by the attempts.** A
count over the kept rows is a count over the winners, so these are taken over
every attempt:

* `(location, mode) -> attempts`, **with the pool stamp**. The draw is a seeded
  permutation over the palette pool, so the count is a *cursor* into it — change
  the library or the group collapse and the same count names different maps, which
  is why the stamp travels with it rather than being assumed.
* `(colormap, mode) -> attempts, scored, successes`. 942 by 18. This is the "which
  palettes never work anywhere" signal and it is the one thing a discard genuinely
  destroys: drop colormap identity with the picture and the question stops being
  askable. An unscored row is an attempt and not a failure, which is why `scored`
  is a separate denominator.
* `(location, cell) -> attempts, dominant`. Read off each row's stored `colour`
  block and never off the carrier table — the table is a prior about a *map* and
  this is the record of what a *place* produced. Only pairs with a hit are rows: a
  colour a place has never delivered is the **absence** of a row, which is what a
  targeted mine tests for.

**No retroactive prune.** The policy is going-forward. `report` measures what
applying it backwards would cost so that the decision, if it is ever taken, is
taken against a number; it writes nothing and `tests/test_retention.py` pins that
the module contains no delete at all.

### What retention does not reach, and the levelled colormaps swept on 2026-08-30

`prune` rewrites three files against one key set and unlinks the pictures of the rows
it dropped. Three things beside a candidate are outside that transaction, and two of
them were the largest per-candidate artifacts on this disk.

**The levelled colormap was the biggest, and it is gone.** `colorize.render` writes the
autolevel operator's overriding colormap to `<key>.leveled/` beside every acted
candidate, `delete_pictures` unlinks the JPEG and leaves it, and it had reached
**206,147 directories / 14.93 GiB** — half again what the candidate JPEGs cost. Two
things were established before deleting any:

* **Nothing read a candidate's for content, on the day this was swept.** Every
  `colormap_dir` override in the package was either the tracked palette directory, or a
  directory written moments earlier in the same call, or
  `sheets.render_finished(..., colormaps=unit["leveled"])` — and that unit's name was set
  by `manufacture` to its own **sheet** subtree. A sweep of every `.jsonl`/`.json` under
  the tree found `.leveled` paths named in exactly four places: `manufacture/*/sheet`,
  `calibration/measure`, `correction/*/screen` and `mode_sheet/measure`.
  `run._discard_partials` is the only other caller and it only deletes one.

  ⚠ **That is no longer true and a re-sweep must not be argued from it.**
  `curation.pool_draw` landed on 2026-09-03 and `leveled_dir` reads the `.leveled/`
  **of a pool candidate** onto every plan unit, which `labeling.sheets` then renders
  through — see [`LEGS.md`](LEGS.md)'s *`curate pool-draw`*, where the failure is
  written down as the one that gets forgotten: a rebuild after a sweep serves a
  different picture under the same identity, silently, because the build skips a unit
  whose picture is already on disk. Re-swept 2026-09-06: **94,485 directories / 7.12 GiB
  in the pool** against 4,844 / 0.48 GiB everywhere else, and the record scan now finds
  a **fifth** shape — `pool_draw/spiral_500/plan.jsonl` names 105 of them. Nothing was
  deleted. The reachable set is not a fixed list either: `pool_draw` takes each
  location's **best clearing row** by rank, so which candidate is drawable moves with
  the pool and with the bars. Only 1,483 directories / 0.09 GiB have no ledger row at
  all, and those are `curate candidate-ledger orphans`' to take with their JPEGs.
* **They are regenerable, by re-rendering and not by replay.** The file is
  `curved_stops(the map's stops, the curve)`; the map is tracked, and the curve is
  `derive_curve(stats_of(the base render), the tracked band)` whose sha256 is on every
  ledger row. So the recipe on the row re-derives it exactly — through
  `colorize.render(level=True)`, one candidate render. It is **not** replayable from
  the row, because `recipes.stamp_of` deliberately drops the derived curve: a
  manufacture row carries the whole curve and can be replayed from it, a ledger row
  cannot. **What that costs is `dump + paint + measure` and it is measured** — over the
  674,089 attempts the `depth` legs' `sequence.jsonl` logs hold, `smooth` is 0.273 +
  0.060 + 0.065 = **0.398 engine-seconds cold and 0.125 amortised** over a (location,
  mode) pair whose field is dumped once; `stripe` is 1.989 cold. The `repaint` is the
  only stage a regeneration saves, so re-deriving one is nearly the price of the
  picture — and it **re-derives rather than reproduces**, which is why a plan that
  named one cannot be handed a fresh directory and called the same render.

  ⚠ **Measured, the re-derivation lands on the identical ramp — 82 of 82.** The
  backfill of 2026-09-08 (`curate autolevel backfill`, below) re-derived a curve for
  277 seats of `20260908T144844Z` and compared the stops it rebuilds against the
  `.leveled/` directory the seat actually shipped through, wherever that directory
  survived: **82 comparable, 82 `agrees`, 0 `differs`**. That does not make a
  re-derivation a reproduction — the base render it measures is a *new* render, and
  the caution above is about what the operation is rather than about what it happened
  to return — but it prices the caution, and it is the reason the backfill is worth
  having at all. The other 194 of the 277 had no surviving ramp to check against and
  are recorded `no_ramp` rather than assumed good.

**194,058 directories were swept, 12,089 excluded** — those four named subtrees, the
released and parity pictures, the label sheets' own `full/` renders, and everything
belonging to a leg the ledger cannot answer for.

#### A prune cannot take a surviving row's colormap, and the reason is structural

**The question keeps being asked and it has a closed answer: no prune can delete a
`.leveled/` that a surviving row still resolves through.** It is worth stating as a
property rather than as a count, because a count is re-taken after every merge and
this does not move.

Three spellings of the same expression, and the whole argument is that they are the
same expression. `prune` builds its doomed list as the `picture` of each row **whose
key is not in the kept set** and hands only that list to `delete_pictures`;
`_delete_colormap` derives `<parent>/<stem>.leveled` from that row's own picture;
and `pool_draw.leveled_dir` derives `<parent>/<stem>.leveled` from a **surviving**
row's own picture. So a prune can only take a live directory if a dropped row and a
surviving row name the same picture — which is not a rank question or a policy
question but an identity one.

**They cannot, and it is measured.** Over all **308,419 rows** of the ledger the
ckpt-112 mine left, 2026-09-06: 308,419 distinct `(directory, stem)` pairs, **zero
carried by more than one row**, every row naming a picture and every picture inside
the tree. The identity holds two different ways at once, which is why it is robust
to a leg naming its files differently: **294,893 rows name the picture after the
recipe key**, which is the ledger key itself and unique across the whole store —
`depth` 286,843, `mine` 4,476, `remode` 2,938, `hunt` 636 — and the other **13,526
name it by attempt index inside one run directory**, unique within that directory,
those being `runs` 11,402 and `reframe_draw` 2,124. Neither shape can put two rows
on one path, and the two shapes cannot collide with each other either, since no run
directory is shared between them.

**It is pinned now, in `tests/test_leveled_identity.py`, and in two halves that fail
on different things.** The fast half asks `_delete_colormap` and `pool_draw
.leveled_dir` for the same picture — behaviourally, by running the prune on a
throwaway tree and seeing what disappeared — over both live stem shapes and the
near-misses a derivation built on string surgery would get wrong. It needs no
ledger, and it fails the day the writer, the sweeper or the draw is edited alone.
The slow half is the scan, and it does not merely count collisions: it asserts the
**shape classification is total** and that no directory holds both shapes, so a leg
naming its files a third way fails at its first row rather than at its first
collision. 32 s on this machine, `--slow`, off `conftest.tracked_ledger`.

**Read the same pass for the other half of the transaction**: 308,419 of 308,419
pictures were on disk, none missing, so the pictures-then-records ordering completed
cleanly through the afternoon's prune of 29,402 rows. And **106,390 surviving rows
(34.5%) resolve a `.leveled/`** — that is the live set `pool_draw` can put on a plan,
against the 373 the first gallery-grade draw actually reached. **Those 373 are held
by a row now**, because `retention.labeled_renders` reads the `gallery_grade` store —
see *What is kept, and why each rule is the rule it is* above. They were not on
2026-09-06 morning: 233 of that draw's 300 runners-up were named by nothing at all,
and a `.leveled/` outlives nothing its picture does not.

⚠ **None of this defends a standalone sweep, and the 2026-08-30 one is the proof.**
The property belongs to `delete_pictures` because the row goes in the same
transaction, which is what its own docstring says and where it says the argument
stops. A sweep that ranks colormaps on their own has no such row, and that is how
about thirty `gallery_grade` rows came to be judged through a colouring their
candidate score was never read on — see `data/batch_caveats.md`'s
*NEVER-AN-INSTRUMENT*. Nothing here has been repaired; the finding is that there is
nothing on the prune path to repair.

**The orphan JPEG pile is not what it looks like.** 6,529 pictures in the candidate
directories carry no ledger row, but **none of them is unnamed**: 7,466 more are
`manufacture/`'s own live products (named relatively, `pictures/000002.jpg`, by
`screened.jsonl` and the plan files), 4,535 belong to unmerged legs, 11,028 are run
*attempt* pictures named by index rather than by recipe key, and the 1,775 left are
named by a study's own record — `depth/breadth_strange`, `depth/wm1_serial`,
`depth/smooth500_pilot` by their `sequence.jsonl`, and `shrinkage/dc1` by the
`pairs.jsonl` those 200 label-geometry re-reads *are*. Nothing was deleted here.

**A killed leg bypasses the retention rule entirely, and `curate candidate-ledger
orphans` is the backstop.** `prune` runs from `merge`, so a leg that *finishes* hands
its candidates to the ledger and the rule bounds them from that moment. A leg that is
killed never reaches `merge`: its pictures are on disk, no row was ever written for
them, and **no later prune can free them**, because a prune only ever decides about
rows it can see. Nothing else in this project can either, which is why the sweep
exists. It is a dry run unless `--apply` says so — the opposite way round from
`prune`, deliberately, because a prune decides about rows and this decides about files
nothing wrote down.

**The merge stamp decides which question a leg is asked, and the stamp is the `hunt`
block on the row.** A leg that has merged handed the ledger everything it made, so
from then on the **ledger alone** is its reference set: a picture with no row is one
the retention rule already decided about, and a `sequence.jsonl` still naming it is a
measurement record outliving a decision. A leg that has **not** merged is skipped
whole and listed under `unmerged` with its counts, because its pictures are real work
with no row anywhere — which is what this command exists for and exactly what it must
not delete on its own initiative. No leg writes a stamp of its own; `hunt.merge`,
`mine.merge` and `depth.merge` build a report and the CLI prints it. The `hunt` block
separates exactly: of 177,993 rows, **166,118 carry one** — `depth` 158,628 · `mine`
4,566 · `reframe_draw` 2,283 · `hunt` 641, to the row — and the 11,875 that do not are
the whole of `runs`.

**Row presence alone is NOT the stamp, and `runs` is why.** Those legs are in this
ledger by `backfill`, which reads the two **decision stores** — so the ledger holds
what they decided about and never what they rendered: 11,875 rows against 15,578
pictures on disk. Sweeping them on row presence would have deleted 3,610 index-named
attempts out of `gallery1`–`gallery4` and the `run*` legs and called it garbage
collection. `store_named` on each `unmerged` entry tells the two kinds apart at a
glance: **0** is a killed leg to re-merge or delete, a **large** number is a
backfilled leg that cannot be re-merged at all.

**The reference set is the UNION over every store that names a picture, since
2026-09-07, and before that it was the ledger alone.** `_named_by_a_store` reads
the candidate ledger, the tracked release store, the tracked gate store and the
retired gallery passes' attempt rows under `artifacts/curation/gallery/<pass>/`,
and a picture any of the four names is kept. The ledger alone was not enough for
exactly the reason the paragraph above gives: `backfill` copied those decisions
into the ledger *once*, and the copy goes stale with every prune. `orphans` then
promised in its own docstring that a named backfilled leg *"keeps every picture
its decision stores named"* while implementing something weaker, which is how the
09-02 sweep and `curate re-render` became a loop — see *The 09-02 sweep and
`curate re-render` were a loop* below. The record carries a `reference` block
saying what each store contributed. **The merge stamp is still the ledger's
alone**: a decision row naming a picture is not evidence its leg merged, and
folding the decision stores into the stamp would read every backfilled `runs` leg
as merged and sweep it unasked.

**What the sweep can reach is narrower than what has to be kept**, and the roster
of the rest is [`../README.md`](../README.md)'s *The standing keep roster*:
`picture_dirs` walks `<subtree>/<leg>/pictures` and nothing else, so most of what
must survive is unreachable by it rather than exempted from it, and a ruling is
all that keeps it.

**Dry-run 2026-09-02** over 187,976 pictures: 32 unmerged legs holding **20,723
pictures (3.09 GiB)** skipped — **22 killed** (10 `depth`/`mine` legs and 12 `runs`
smoke legs, 5,238 pictures) and **10 backfilled `runs` legs** (15,485 pictures, 11,875
of them ledger-named) — and **1,135 named by no ledger row (182.2 MiB)**, every one of
them in two merged `depth` legs (`breadth_strange` 883, `smooth500_pilot` 252). The
rule this replaced kept those 1,135 because those legs' `sequence.jsonl` still names
them, and deleted 24.

**All three were then taken, on Matt's ruling, 2026-09-02.** The 1,135 went with a
plain `--apply` (0.178 GiB). The 10 backfilled legs were named with `--leg` and lost
their **3,610** un-decided attempts and 1,468 levelled colormaps (0.624 GiB) — and
**not** keeping every picture their decision stores named, which is what that
`--leg` run was thought to be doing. The 22 killed legs went **whole** — not
through this sweep, which is pictures-only by design, but through a one-off that
checked each path against the hot root and the leg shape first: **1.81 GiB over 11,216
files**, most of it the `fields/` and `candidates/` beside the pictures.

### The 09-02 sweep and `curate re-render` were a loop, and the union is what closed it

**Closed 2026-09-07.** The 3,610 pictures the 09-02 `--leg` sweep took out of the
ten backfilled `runs` legs came back the next morning: 3,615 of them, every one
dated 2026-09-03, the per-leg count of 09-03 files matching the per-leg unnamed
count on all ten. The writer is **`curate re-render`** — the pool's, `rescore.py`'s
`re_render`, not the ledger's — run twice inside `RETRAIN_render_v6`: a `--limit`
pilot that made **61** and stopped at 04:32:41, then the leg proper
04:32:55.8 → 04:59:55 that made **3,554**. 61 + 3,554 = 3,615 exactly, and
`artifacts/curation/pool_re_render/re_render.json` carries the leg's own half of
it (`made: 3554`, `failed: 0`, `refused: 0`, `wall_seconds: 1619.2`). The
arithmetic closes both ways: 15,485 − 3,610 + 3,615 − 495 = 14,995 pictures on
disk, the 495 being the drop in ledger-named `runs` rows over the same days, and
the orphan set measured 0.624 GiB against the sweep's own 0.624 GiB.

**Nothing in that set was garbage. All 3,615 were named by a real store, just not
by the candidate ledger** — **85** by the tracked gate store, **3,530** by
`artifacts/curation/gallery/<pass>/gate.jsonl`, matched 3,530 of 3,530 exactly. So
the sweep and the repair were pointed at the same files and the question was only
which of the two was wrong. It was the sweep, and `_named_by_a_store` is the fix:
the reference set is now the union, the loop is disarmed, and deleting the
pictures behind the kept attempt rows is available as a **named act** rather than
as a side effect of garbage collection.

The gallery half became invisible on 2026-09-07 rather than on 09-03: retiring the
gallery gate store stopped `rescore.pool_rows()` reading the attempt rows, which
is why the pool could put them back in the first place and no longer would.

**Measured after the union, 2026-09-07.** `orphans --include-unmerged`, a dry run
over all ten legs: **0 pictures would be deleted**, against the 3,615 the
ledger-only rule named. Every picture in every one of the ten is named by a store,
which is the arithmetic the audit predicted — 11,380 by the ledger, 85 by the two
tracked decision stores, 3,530 by the attempt rows, and 11,380 + 3,615 = 14,995,
the whole of what is on disk. Eight of the ten now report `store_named` *above*
their picture count (gallery4 6,866 against 6,620) because the stores also name
renders a prune has since taken; that is the reference set being wider than the
disk, which is the safe direction.

| | gallery4 | gallery3 | gallery2 | gallery1 | run10 | run3 | run9 | run2 | run8h | release_v1 |
|---|---|---|---|---|---|---|---|---|---|---|
| on disk | 6,620 | 3,843 | 2,415 | 1,089 | 311 | 234 | 234 | 114 | 111 | 24 |
| named by a store | 6,866 | 3,980 | 2,472 | 1,120 | 320 | 240 | 240 | 114 | 112 | 24 |
| **would delete** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **0** |

Whether the ten legs are worth keeping is still Matt's and still open. What has
changed is that it is now a question about **11.75 GiB of superseded attempts**
and not one a garbage sweep can answer by itself.

### The 11.75 GiB is not the 14,995 pictures, and only one of its subtrees is free

**Asked properly on 2026-09-07 and the two figures name different things.** The ten
legs hold 77,282 files and 11.76 GiB; `pictures/` — the 15,033 candidate renders the
census is about, 14,995 of them before the repair leg put 38 back — is **2.59 GiB of
it**. The rest is `candidates/` 6.39 GiB, `release/` 2.15 GiB, `framings/` 0.50 GiB,
and `fields/`, which is already empty on all ten.

**Nothing outside the ten names anything but `pictures/`.** Every json and jsonl
under `artifacts/`, `data/`, `labels/` and `models/` was read: **206 files mention a
leg path, 27,133 times, and every one of those mentions is a `pictures/` path.** So
the free subtree is the one whose own writer calls it a cache —
`runs/<leg>/candidates/<field stem>/<map>.jpg`, written in
[`colorize.Clouds.recolours`] and read only by a live pass, which
[`run._discard_partials`] describes as *swept after the attempt leg* and which no
index names, not even inside the leg. **48,632 files and 6.39 GiB, deleted
2026-09-07** under an isolation proved against a 330,763-path reference set built at
the moment of deletion: zero collisions, every path re-checked to be under one of
the ten legs' `candidates/`, and the six subtrees that had to stay still counted
before and after. `absent_pictures()` 0 → 0, the ledger's `missing_pictures()`
0 → 0, and the ratchet untouched at `rows` 308,419 / `recipe_key_named` 294,893 /
`run_index_named` 13,526, because no row moved.

**`framings/` is unreferenced from outside and was still kept**: its own
`framings.jsonl` names each trial by slug, so a store that survives the deletion
would be left naming nothing. That is the orphan sweep's rule applied to a subtree
rather than to a picture — delete what *nothing* names — and it is the line the
09-07 deletion was drawn on.

### Why `pictures/` cannot go, and it is not the ledger that stops it

Three answers, each measured rather than argued, and any one of them is enough:

- **644 of the 11,380 ledger keys in the ten legs are `tentative.protected_keys()`**
  — seats in recorded galleries, 62 stamps naming a leg picture, gallery4 330 of
  them. `protected_keys` sweeps published and unpublished stamps alike, and an
  older record whose pictures went is a page of broken thumbnails.
- **`absent_pictures()` would go 0 → 1,556 and `curate rescore` refuses outright.**
  The rows that name them are the **tracked** release store, so the *take the rows
  with the pictures* route is closed: those rows are decision history. All 1,050
  pictures of the six `run*`/`release_v1` legs are in that set, plus 506 across
  gallery1–4.
- **The gallery-grade head stands on 118 of them.** Its 1,000-unit population names
  118 leg pictures and all 1,000 units carry a human label; three labelling sheets
  under `artifacts/gallery_grade/n1000_0906/` name 36 by path, and
  `artifacts/sparse_mode_head_top_places/sheet.jsonl` names 148 more.

**Replayability was never the obstacle and is worth recording as settled.** All
11,380 ledger rows reproduce their own key under `candidate_ledger.rerender`'s own
guard — **11,380 of 11,380, zero refused** — and the legs' own `candidates.jsonl`
rows are 9,749 `untouched` and 4,749 `replayed` with **zero `acted_unrecoverable`**.
Not one picture in the ten legs is the only copy of what was judged. What stops the
deletion is that too many live things point at them, not that they could not be
drawn again.

**An unmerged leg is swept only when somebody names it.** `--leg <name>` takes one
(as the listing prints it, or just its last component) and is repeatable;
`--include-unmerged` takes all of them. A named leg is swept under the **same rule as
a merged one** — what the ledger names is kept, the rest goes — which is why the two
kinds need no separate handling: a killed leg has no rows and loses everything, a
backfilled `runs` leg loses only the renders nothing decided about. They are reported
apart, under `swept_unmerged`, so a person who named a leg can read back what naming
it cost. The listing stays the default precisely so that taking one is a sentence
somebody typed after reading it.

The safety is three properties and none of them is a promise made in a comment: the
enumeration is `<subtree>/<leg>/pictures` at a **fixed depth**, so a leg's `fields/` is
unreachable however large it gets; every directory is checked against the tier roots
**at the point of deciding** rather than trusted from whatever produced the list; and
the deletion is `delete_pictures` and nothing else, which is the one deleter in this
project and re-homes each name as it unlinks. And the reference set is built **in the
call that deletes**, off the stores themselves — never handed in and never carried over
from an earlier reading, because a sweep deciding against yesterday's measurement is a
sweep acting on a store that has since moved.

The run costs **17.7 s** over this store, 2026-09-07, at 328,714 pictures over 115 legs.
Split: the enumeration **1.08 s** (443,134 directory entries), the ledger pass **5.80 s**
(325,099 rows naming a picture), and the three decision stores **1.02 s** (17,079 rows,
53 MB of it the gallery attempt rows). **So the union costs a second**, which is the
answer to whether reading three more stores was affordable. The 9.9 s this used to
read was over 187,976 pictures and is not comparable; the figure it *is* comparable
against is the 31 s of the rule before it, which read every leg's own records with a
regex and spent two thirds of the run doing it.

**The ledger's pictures live in exactly five subtrees, and nothing it holds names a
field.** Swept 2026-09-02 over 177,993 rows: `depth` 158,628 · `runs` 11,875 · `mine`
4,566 · `reframe_draw` 2,283 · `hunt` 641, and no row points anywhere else at all.
That is the cheap test for whether a name under the regenerable tree is load-bearing —
grep the `picture` field, not the source. It also settles the dumped fields: **zero**
rows across `rows.jsonl`, `scores.jsonl` and `flatness.jsonl` name a `.f32`, so a
leg's `fields/` is a pure intermediate however large it gets (6.2 GiB across 54 depth
legs on that date, against 24.3 GiB of pictures in the same tree).

**A leg's `sequence.jsonl` / `profile.jsonl` is a measurement record, not a feature
store, and it must not be pruned row by row.** 361,221 rows over 43 legs, 295 MB, 69%
of them naming a key the ledger no longer holds — but `depth`'s own module docstring
says the sequence *is recorded whole* on purpose, because a cumulative prime curve at
any `k` is arithmetic over that file. Retention keeps the top few per pair, which is
exactly the winners, so dropping the rows whose candidate was pruned would leave every
curve in `depth.curves` computed over survivors and reading far too high. If these are
ever to shrink it is by retiring a finished leg's record **whole**, which is a decision
per leg. 285,250 of the picture paths these records name are already absent from disk,
so anything reading one — `depth.contact_sheet` does — already tolerates that.

### A per-cell retention arm cannot prune this store, and the shape says why

Replayed 2026-08-29 over 366,236 rows at 18,424 locations: a rule keeping the top
K per (location, mode) **union** the top K per (location, dominant cell) keeps
**65.8% of the rows at K=1** and frees 15.7 of 49.2 GiB. It is not a tuning
failure, it is the store's shape.

**Rows per location are median 12, p90 40, max 332 — and the two arms together
open median 22 of them.** A location carries median 1 mode but **median 21
distinct dominant cells**, because `colour.cells` is thresholded rather than
singular: a row is dominant in 2.36 cells on average and the codebook has 48. So
at K=1 only **1,819 of 18,424 locations (9.9%)** hold more rows than arms, and
everywhere else top-K reaches every row and refuses nothing. Restricting the arm
to the largest cell buys nothing either — 66.7% kept — because 12 rows over 48
cells rarely collide whichever cell you read. **The mode arm alone at K=1 keeps
13.4% and frees 84.9%**, which is the rule shape this module already ships.

The counterpart worth knowing before any prune is that **deleting rows is not
deleting pictures**. Rows are what `hunt.run` and `mine.population` build `known`
off; a deleted row is a recipe the next leg cannot tell it has already drawn, and
at K=1 that is **10.2 engine-hours** of re-render priced through
[`headroom.render_cost`]. And the two `(location, *)` aggregates above keep every
pair under such a rule — the arms *are* their key spaces — while every count in
them silently becomes a count over winners.

## What a pass puts in the history, and what it puts beside it

**Everything a pass tracks scales with `n`; nothing tracked scales with the
attempts.** That is a rule, it is measured on every pass, and
`tests/test_storage_tiers.py` pins the tier rule the store rests on; the N=500 plan that pinned the tracked bytes went with the pass, and the
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

`records.root() / "gallery" / <pass>` holds the record — the summary with its slots
re-attached in slot order — so nothing has to know about the file axis. **The
slots split on partition for the same reason the decision stores do**: a slot row
runs about a kilobyte, N=500 is 1.3 MiB, and the history guard acts per file.
gallery1 at N=50 tracks **337 KB over twenty files, the largest 52 KB**.

**`slot.fill.best` is not the seat's winner.** It is the neighbourhood's top
P(≥3) whatever the floor said about it — the evidence an unfilled slot is *for* —
and it is read before the one-wallpaper-per-location cap picks a seat, so it
routinely names a candidate that lost. On gallery3 it matches `slot.seated` on
**90 of 150** seats. The winner is `slot.seated`, and three records agree on it
independently: the seat's `picture` basename, the release row keyed
`<pass>|release|<candidate>` whose `slot.pass` is the pass, and a step-7 row in
`artifacts/curation/runs/<pass>/release/timing.jsonl`. That last file is how a
release picture is told from a leftover — one row per winner, carrying the
resolution and supersample it was actually made at, which is a per-pass decision
and not a constant.

**The attempts were the bulk, they were never in the history, and they are gone.**
A pass made `locations x heads x draws` attempts per slot — 1,120 at n=50, ten
times that at n=500 — and a pool row carrying its whole join runs about 3.8 KB, so
they got the `neutral_embeddings` treatment: under the regenerable tree, a copy on
the archive tier, a tracked manifest, and a `check`/`save`/`restore` verb over
them. **Retired on 2026-09-06 with the passes**, Matt's ruling: the store, its
manifests, the four passes' tracked pass records and slot rows, and the module
behind them. What survives of a pass is its **winners**, in
`data/curation/release/<pass>/` like every other release row, and the 14,316 rows
they put in the candidate ledger.

### The 53 MB of attempt rows under `artifacts/curation/gallery/` is KEPT

**Matt's ruling, 2026-09-07. It is held deliberately and it is not a sweep
candidate.** *(They gained a reader again the same day — `orphans` reads them to
build its reference set, and it is the only thing that does. See* The reference
set is the UNION over every store that names a picture*.)* The four passes'
`gate.jsonl` survived the retirement above —
**14,438 rows**, 1,120 / 2,472 / 3,980 / 6,866, 53 MB — and for one day **nothing
in the tree read them**, because `gallery_store.py` and `curate gallery-store`
went with the passes. So a future sweep met 53 MB of unreadable rows with no
manifest beside them and no code naming them, which is exactly the shape of
something to delete. It is not, and there is one reader again. They are the only judged-attempt data this project has: one pool
row per attempt carrying its whole join, made under two retired render heads
(`smooth_render` 3,782, `strange_render` 10,656) over populations that will not
exist again. **Not to be swept without a ruling from Matt.**

**It is not the last copy, and the report that said so was reading the wrong
path.** `<archive>/curation_backup/gallery/<pass>/gate.jsonl` is there and all four
copies verify byte-for-byte against the sha256 the retired `gate.manifest.json`
carried — checked 2026-09-07. The claim that the archive was empty came of looking
for `curation_backup/` directly under the archive root; the tier puts it under
`<archive>/fractal-wallpapers/artifacts/`, which is what `paths` resolves and what
`storage archive` writes. **The manifests themselves are gone** — they were tracked
under `data/curation/gallery/<pass>/` and went out with the passes — so `git show
<the retirement>^:data/curation/gallery/<pass>/gate.manifest.json` is now the only
place the hashes live. That is the reason to keep this passage rather than a
`check` verb: there is no longer anything to run.

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

**Locations are cumulative, candidates are per-pass.** A later pass selects
locations over everything the pool has ever admitted, and seats only the recolours
it took itself: the pass's pool predicate kept a row only where the row's
maker is this pass, which in the normal path is none of them. gallery3 seated 66
of its 150 slots on standing rows and in 59 of those the standing row merely
outranked the pass's own best at the same place — the pass had made something
there every time. With a deterministic draw putting 98 of its 150 points where
gallery2 had already looked, seating another pass's recolours was running half the
draws and calling the older half free.

**The pass's own pool reader stayed outside that rule and read both stores** — the
release store *and* every earlier pass's attempt store — because the
`below_floor` sheet is answered out of it. Its claim is about the material a
slot's neighbourhoods did **not** reach, so it needs the whole pool; the predicate
lives in `pool_candidates` and not at that call site for exactly that reason.

What it *does* cut is three things, each a different fact: a row this pass wrote
(already in hand), a row with no score (a failed render is a decision with a reason
and no number), and a row a person **rejected**.

**Rejection does not propagate along a `source` chain, and that is worth knowing
before reading a pool.** The cut is `records.is_rejected(row)` evaluated per row.
A picture that a later pass seated out of the pool is on record **twice** — the
original attempt and the pass's re-stamp of it, joined by `source` — and rejecting
one of those two rows does not reject the other. So a rejected original leaves its
re-stamp in the pool, seatable, resolving through [`picture_id`] to the very
picture somebody took out of service. It has never fired: of the release store's
rows, 292 carry a `source` and 51 carry a `rejected` block, and **no row carries
both**. So this is a property of the predicate rather than a defect in the records,
and a reject pass that starts reaching pool rows has to resolve to the picture the
way the dedup does.

## `P(spiral)` rides on the same vector, and costs a dot product

`artifacts/curation/spiral_scores.jsonl` — one row per location, keyed on the
location key, saying what `models/spiral`'s shipped probe makes of the place. It
is `curation.spiral_scores`, its durable manifest is
`data/curation/spiral_scores.manifest.json`, and the reader is the gallery's share
cap (`curate solve --spiral-cap`, `rules.State.spiral_allowance`). **That cap runs
by default since 2026-09-04** at `solve.DEFAULT_SPIRAL_CAP = 0.10`, so this store
is now on the path of every solve rather than only of one that asked; a solve with
no store reads every location as UNKNOWN and the cap can refuse nothing, which is
no cap by a second route. The ruling and what it costs are in
[`GALLERY.md`](GALLERY.md)'s *The spiral share cap is a tenth by default*.

**The cost line: about 40 microseconds a location, and no render at all.** The
whole store — 40,734 locations, 10.9 MB — scores in **1.6 s** on the CPU. That is
because the probe's feature set *is* the neutral-render DINOv2 vector the embedding
store above already holds, so scoring a location is a 384-column dot product rather
than the ~0.05 s a render-and-encode costs. A location the embedding store has not
reached does need its picture drawn, and `spiral_scores.score_records` is that path
at the measured 0.051 s each — but on the pool as it stands that path has never
been needed: the first capped solve found **0 unknown locations over all 21,544
clearing candidates**, because the embedding store's admitted population is a
superset of the pool's.

Scoring runs at the end of `curate embed`, so a newly admitted location arrives
with a score instead of being drawable before it has one.

**The fp16 packing is not a caveat.** The store's vectors are `float16` and the
probe was fitted on `float32`; measured over the labeled 500, the round trip moves
`P(spiral)` by at most 1.3e-4 (mean 1.2e-5) and flips no verdict at 0.3, 0.5 or
0.7.

**A location with no row reads as unknown, and unknown counts toward nothing** —
it can neither fill the cap nor be refused by it. That asymmetry is deliberate and
is the one thing a reader here must not "simplify": a place nobody has scored and a
place the probe called flat are different facts, and conflating them would stop the
cap acting on exactly the locations nothing had looked at.

## The gallery pass needs a distance, so every admitted location has a vector

The gallery pass picks by **quality-weighted farthest point with a hard radius**,
which needs to know how far apart two locations look. `curate embed` is what
answers that: for every location the location judge admits over the junk floor
(**28,420** on 2026-08-27), one **neutral render** through one fixed cyclic map at
one fixed small geometry, and the unit vector a frozen DINOv2 reads off it. The
store holds **29,381** rows against that: it is append-only and keyed on the
location, so a location a later harvest re-framed or a later judge dropped keeps
the vector it was given. `curate embed` is the number that matters — it subtracts
what is stored and reports `complete` when nothing admitted is missing.

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

Everything **a run** makes at full size is **2560x1440 supersample 4** —
`run_layout.RELEASE_RESOLUTION` and `run_layout.RELEASE_SUPERSAMPLE`, one geometry for every
partition, every mode and every head, so nothing about a release row's cost or
its bytes depends on which slot it took.

**A gallery pass is 1280x720 ss2**, from 2026-08-25 on Matt's call, and it is a
*default* rather than a constant: `release.RELEASE_REGIME`, moved by
`--release-regime <w>x<h>ss<n>`, with `release.FORMER_RELEASE_REGIME`
(2560x1440ss4 — what gallery1 through gallery3 shipped at, and what the website's
figures are drawn off) still reachable there. A released wallpaper does not need
the full frame, and step 7 is the slow leg of a pass: a quarter of the pixels at
half the supersample is a **sixteenth of the field samples**.

**Measured, on gallery4's 249 winners:** 3.5 s a row of wall on 3 workers, 8.25 s
a row of CPU — against gallery3's 44.6 s and 121.5 s at 2560x1440 ss4 on 4. That
is a **14.7x** cut in row time for a 16x cut in samples, so the leg is very nearly
sample-linear and the whole of it fell from 6,684 s to 860 s. Per row the CPU
spread is min 1.6, median 5.2, q75 8.5, max 65.1: the tail is long because a
gallery draw seats deep locations, and the deep rows come **first** — the opening
fifty averaged 14.4 s against 7.7 s for rows 100-150, so a rate taken off the
first block over-reads the leg by about three quarters. Size a leg off the median
and the row count, never off its opening.

A release row carries no per-row clock. The leg logs one (`[release] <id>
<verdict> <n>s`), the pass record carries the aggregate (`render.row_seconds`,
`render.seconds_per_full_size`), and a per-row distribution has to be read back
off the pass's own stdout — so keep it if you intend to price the next pass.

So a diagnostic release and a shipped wallpaper are no longer the same picture at
the same size, and the two regimes are named apart rather than one read off the
other. What follows from that is the recording rule: the regime a pass used is on
the pass record (`config.release_geometry`) and on **every release row it writes**
(`release_geometry`, `null` where there is no picture), because `recipe.render` is
and always was the *candidate* geometry the verdict was cast on. `checks` reads
the regime off the row — `checks.regime_of_row`, falling back to
`checks.UNRECORDED_REGIME` for rows written before the field existed, every one of
which came from a 2560x1440 ss4 leg — so `parity` and `replay` re-derive the
pixels the row actually shipped rather than today's default. For the same reason
step 7 will not reuse a picture already on disk at another frame: it reads the
frame off the file and makes it again.

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

**And the anchor draw is the whole of it: there is no palette-cluster cap at
release.** Nothing in selection or in the release path groups the library at all.
**The gallery leg is the exception and has been since 2026-08-25** —
`ceiling.group_cap` caps the seats one [palette group](../palettes/groups.py) may
take, and a group is a linkage cluster of near-duplicate maps rather than a single
map — so this paragraph is about a **run's release** and never about the
collection. (That cap **costs nothing at n=1000 and is not what enforces diversity
there either**, on three independent measurements —
[`MEASUREMENTS.md`](MEASUREMENTS.md)'s *What the palette-group cap costs at n=1000,
measured 2026-09-07* — so the exception is a real difference in the code and not
much of one in the outcome.) It said otherwise until 2026-09-07 and was wrong on the day it was
written.

**The census and the solve priced two different caps until 2026-09-08, and the
census was the one that was wrong.** `candidate_ledger.inventory.feasibility` read
`ceiling.GROUP_CAP` — the **identity** cap of one seat a group — so its `group_cap`
row said `{"cap": 1, "needs": 1000, "holds": 942, "binds": true}` at n=1000 and had
said so since the proportional rule replaced the identity one on 2026-08-28, while
the seating ran `ceiling.group_cap(n, solve.DEFAULT_GROUP_CAP)` — **25** a group at
that rung, refusing nothing. A leg reading *`group_cap` binds* off a census and
*zero refusals* off a solve was reading two caps and not one contradiction, and it
cost a leg's readout twice. The row now prices the cap the solve runs, the way
`headroom`'s `palette_group_cap` block was corrected on 2026-08-31, and carries
`cap_rule` beside `cap`; it reads `{"cap": 25, "needs": 40, "holds": 942,
"binds": false}` at n=1000. **`needs` is groups and not seats** — `ceil(n / cap)` —
which is what it always was, the two being the same number only at a cap of one.

**Under the proportional rule this row can no longer bind on this pool at any n.**
`ceil(n / max(1, floor(0.025 n)))` peaks at **79 groups**, at n=79, where the
`max(1, ...)` floor is still holding the cap at one; from n=80 up it runs 40 to 60,
and from n=1000 up 40 to 42. So a store holding 942 groups clears it everywhere,
however large the gallery, and the row is a
necessary condition that is satisfied rather than one that was quietly dropped.
It binds on a pool of under eighty groups — a themed sub-pool is where to expect
that, and a themed pass prices `ceiling.themed_group_cap` rather than this.

**A group's population is a fact about the tracked colormap library and never
about the ledger.** `groups.group_of` is total — a map in `data/palettes/groups.jsonl`
takes its cluster's id, a map absent from it is its own group `map:<name>` — so a
row can only carry a group some map already had. The drawable pool is 942 groups
over 1,020 maps and **every one of the 942 already holds a ledger row**, which is
why no amount of mining moves the count: 750 new locations and 146 gallery-grade
rows over the night of 2026-09-08 produced **zero** new groups. The last thing that
moved it was the `classic-pairs-2026-09` drop of 2026-09-05, 822 → 942, and the
table has not been re-cut since 2026-08-25 — so those 120 maps are singletons by
default rather than by measurement.

**And 942 is the pool's number, not the view's.** Read over the seatable pool it
is 942; over the rows the fine head has scored, 934; over the `p_fine >= 0.50`
view, **762**; among a thousand seated, **477**. A group count quoted without the
population it was read over says very little. (A sixteen-way clustering was tracked beside the maps
until 2026-09-02 as a figure's record, read by nothing but the command that wrote
it; the website groups by dominant hue and it was deleted.) So two seated rows may
land in one region of palette space, and what stops that is the without-replacement
anchor draw upstream rather than a cap downstream. This is a
deliberate gap and not an oversight: palette-level diversity across the
collection is the colour-coverage floor's question, and until that leg exists the
honest statement is that nothing enforces it.

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
bar** removes one at selection: a strange row below `STRANGE_RELEASE_BAR` is not
seated, and a strange slot with nothing above it goes unfilled.

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
verdict: the bar is restated off the labels at every flip — the crossover where
the head's own P(>=3) stops disagreeing with the people who judged those pictures
— and it has moved at each one, because a retrain moves the whole probability
scale. **THAT it acts is the 2026-08-17 verdict and does not move; WHERE it sits
is a measurement, and this page does not carry the number.** `head floor --head
strange_render` re-fits it and refuses on a height that does not reproduce or a
stamp that has gone stale; `models/render/README.md` is where the live pair is
written down once. **The smooth kind stays advisory** — its below-advisory rows belong to a mix-ratio decision that has not
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

**"Regime-robust" is a within-tolerance claim, not identity, and the 2026-08-25
amendment is what that costs.** Re-reading the 28,072 regime-less rows at the node
regime instead of the 640x360 ss2 they were scored at moved **12.2% of them by
more than 0.02 on `P(>=4)`** — 42.5% on `P(>=3)` — and **956 of them fell under
the junk floor** while 330 rose over it, out of 28,576 admitted before the pass and
27,950 after. The engine is not the cause: the same pass re-rendered 20,985 cached
node views under one build and found a maximum |ΔP(≥4)| of 8.6e-07, and the 39,514
gate renders were bit-exact. The geometry is. So the two regimes are near enough to
rank one pool and not near enough to be one reading, and the rule that follows is
the operational one: **all seating reads one regime now, and nothing reads across.**
A number carried from a 640x360 read is amended before it is compared, never
compared as it stands.

**The RENDER judge has no such property, and the number is five times worse.**
Nothing had ever measured it: `SCORING_HEAD` reads candidates at 640x360 ss2 and
reads the pictures a person judges at the 1280x720 ss2 both corpora were collected
at, and those two readings had never been put side by side. Cutting
`p_ge4_calibration_*` did it for free — 246 pool candidates rendered again at label
geometry through their own recipes, scored through the same shipped artifact. On
the **133 rows whose levelling was identical at both sizes**, so that the only
thing that moved was the geometry, `P(>=4)` shifts by a mean of **-0.009** and a
standard deviation of **0.087**, and **61 of the 133 land in a different one of the
three 0.10-wide calibration bands than they were drawn into**. Re-levelling at the
new size adds to it rather than causing it: the 113 rows the operator acted on at
sheet geometry spread 0.114, which is the 0.087 with about 0.07 more in quadrature.

So the render judge is **unbiased and imprecise across regimes** — there is no
correction to carry, because the mean is already zero, and there is no reading
across either, because a single row's number moves by most of a band. Which is a
sharper rule than the location head's: a candidate's 640x360 `P(>=4)` ranks a pool
and must not be quoted as the score of the picture a person will see. A threshold
that acts — a floor, a bar, a screen — has to act on the regime it was measured
on, and `curation.floors`' stamps are what say which that is.

**And inside the band a bar would sit in, the score barely ranks at all.** The
labelled half of `p_ge4_calibration_*` — 246 rows, Matt's verdicts, fitted on the
label-geometry column — measures how much a `P(>=4)` between 0.60 and 0.95 actually
says about whether he calls a picture a 4. The answer is: very little. The logistic
slope is **+2.5 on smooth, +2.3 on colour·strange, +1.8 on composite and -0.7 on
colour·smooth**, so a 0.10 rise in the judge moves the human keep rate by about four
to six points, and in one stratum the wrong way; point-biserial `r` runs +0.18,
+0.15, +0.11, -0.05. The isotonic crossover is therefore **not identified** in any
stratum — 90% intervals 0.20 to 0.45 wide against a design priced at ±0.022, because
that pricing assumed a slope near 12 and the real one is five to seven times flatter.

That is a statement about **this band**, not about the judge overall: the sheet
deliberately excluded the tails where the judge is obviously right, so a flat
response in the middle is partly by construction. What it rules out is the thing a
bar needs — a place in [0.60,0.95) where the score separates keepers from the rest.

**What does separate them is which population a row is from.** At matched score and
within one store, a composite reads **+0.249 (95% [+0.051, +0.446])** higher on
P(human>=4) than a thin-colour candidate — the same judge number meaning materially
different things across two populations of the same corpus. Colour against smooth in
the other store is -0.086 (95% [-0.270, +0.102]) and is not resolvable. Both are
cluster-bootstrapped on location and neither pools the two stores.

Every number here is train-side and anchored: the batches are registered
`anchored: true`, so their labels measure agreement with the incumbent and are
train-side however the draw was made. Nothing is registered `eval_eligible` —
that is derived from the registration and never stored — and any rate off these
batches is a ceiling, under a probability scale a retrain moves whole.

### Nine modes the judge has barely seen, and the sheet that asks about them

`gaussian_int` · `curvature` · `smooth_curvature` · `smooth_mean_angle` ·
`smooth_trap_circle` · `direct_trap_lines` · `direct_trap_ring` ·
`direct_trap_multiply` · `direct_trap_screen`. Everything the pipeline believes about
these is a reading of `SCORING_HEAD`, which has seen almost no human verdict in any of
them, and the readings that look like a verdict are not one: `gaussian_int` cleared 0
of 332 at proven locations and `curvature` 0 of 1,604 in breadth, both at
`P(>=4) >= 0.50`, which says nothing about whether the pictures are human 3s. Every
one of the nine routes to `strange_render` — `hunt.kind_of` sends everything but
`smooth` there — so the population is one sheet and one batch.

**The material is not thin; the judgement is.** The ledger holds 14,415 rows across the
nine and, after excluding the labelled, the person-rejected and anything on a pinned
evaluation location, **630 to 894 distinct locations a mode**. `under_seen_modes` takes
the top 56 of each by `P(>=4)`, one row per (location, mode), unfiltered and
unstratified — the best material each mode owns rather than a band around a bar.

**What the top of a mode actually looks like is the finding.** Even taking the whole
ledger's best, the 56th row of a mode sits at a `P(>=4)` of **0.012 to 0.092**: the
scored supply runs out long before the draw does, and five of the nine top out under
0.90. At label geometry only **45 of the 504** rows reach 0.50, and the nine modes'
means run 0.12 to 0.30. That is the incumbent's own opinion of its own best, and it is
what makes the sheet evidence for a retrain rather than a demotion: no bar is read off
it and none should be.

**The geometry noise is smaller here than the calibration sheet measured.** Over the 396
rows whose levelling was identical at both sizes, `P(>=4)` moves by mean **+0.011**, sd
**0.065** — against `p_ge4_calibration_*`'s -0.009 / 0.087 — and rank is largely
preserved, Spearman **0.915** over all 504. Not a contradiction: this draw spans the
whole score range and most of its rows sit low, where the judge is confident, while the
calibration sheet deliberately took a 0.35-wide band in the middle where it is not.

**What the leg cost, measured.** 2026-08-22, RTX 2060 SUPER, hot tier: 22,630
never-scored rows of those three ledgers in **3,363 s over twelve 2,000-row
chunks**, one chunk a checkpoint, **0.149 s/row realized** against a 200-row
pilot's 0.123 (harvest) / 0.169 (walk_demo) / 0.029 (walk_j). Not the 2.89 s the
deploy geometry cost: these are gate survivors and the cost is what the pixels do,
not how many there are. About **8.1 s of that is fixed per invocation** — imports,
the head onto the GPU, the ledger read, and the sidecar rewritten whole — which is
what sets the chunk size. It wrote **1.48 GB / 22,898 files** into
`artifacts/node_views/384x216ss1/` and nothing anywhere else.

## The archive tier

The archive tier mirrors the hot tree's shape one level down: a run archived out
of `<hot>/<name>/` lands at `<archive>/<name>/`. `location_views` — the frozen
deploy cache above — lives there, and so do closed harvest runs (`harvest_run2`,
`3`, `9`, `10`), superseded gallery passes, and the smoke trees.

**`<hot>` and `<archive>` are placeholders on purpose.** They are this machine's
two artifacts roots, and a drive letter written into tracked source is exactly
what `tests/test_history_purity.py::test_no_absolute_paths_in_source` refuses —
this paragraph is the one place it has ever been broken, and spelling the roots
out here would also make the file wrong on any other checkout. Ask the settings
instead: `paths.hot_root()` and `paths.archive_root()` are the answer,
`paths.HOT_ROOT_KEY` and `paths.ARCHIVE_ROOT_KEY` name the settings that hold
them, and `fractal-wallpapers storage status` prints every subtree with its tier.

Restoring one is a copy back under the same name:

```
robocopy "<archive>\<name>" "<hot>\<name>" /E
```

Two rules hold on the way out. **`artifacts/curation/` never goes** — it stays on
the hot tier entire, pictures pruned in place under the retention policy rather
than moved. And a tree only leaves after a copy is verified equal on **both** file
count and byte sum, because the sources are deleted afterwards and a short copy is
silent.

## Levelling is decided once and replayed upward

The autolevel operator is a judgement about a picture somebody scored, and the
picture somebody scored is the 640x360 JPEG. Until 2026-09-08 every larger render
of that row **measured itself** — a release, a gallery seat, a kit — so the
wallpaper that shipped was levelled by a rule nobody had judged: the tone of a
2560x1440 PNG is not the tone of the candidate, and `coloring/README.md` measures
the JPEG round trip alone moving the derived stop list on **17 of 24** candidates.

The decision is now taken once, at candidate geometry, and inherited by every
render above it. `coloring.autolevel.maybe_level` takes a `borrowed` curve and
skips `stats_of`/`derive_curve` when it is given one; a caller distinguishes the
two by passing one or not, and every candidate leg passes none, which is the
deciding path unchanged. **Nothing entered an identity.** The reduced stamp
`recipes.stamp_of` keys on is the same three strings it always was — the operator,
the switch, the band's sha256 — so no recipe key moved, no picture renamed, and
no published record was orphaned. Proved rather than argued: `key_of` recomputed
over 20,000 live ledger rows before and after the change digests to the same
`4f9fc430…`, with all 20,000 still agreeing with their stored key.

What a borrowed row gives up is `measured`, which is `None` on it. That member is
the base render's own tone and a render that read no image has none; filling it
with the *source's* statistics would put a 640x360 fingerprint on a 2560x1440
stamp. The stamp says which of the two it is under `provenance.curve` —
`derived`, `borrowed`, or `rederived` for a backfill — and `depth.levelling_of`
needs no new word for any of it: a borrowed row carries `acted` and the whole
curve, so it reads `replayed` through the branch that was already there. The three
words the website's `builder/picks.py` owns did not move.

### `curate autolevel` — which seats can replay, and a curve for the ones that cannot

`curation.stamps` is the join: a recipe key to the whole stamp the leg that made
it wrote down, read in one pass grouped by leg. **Three** stores lend a curve now
— `depth/<run>/sequence.jsonl`, `mine/<run>/sequence.jsonl` and
`remode/<run>/sequence.jsonl`, one row per candidate carrying `key` and
`autolevel`, declared in `stamps.SEQUENCE_STORES`.

`mine` joined on 2026-09-08 and until it did, **a mine leg lent nothing**:
`mine.make` returned the whole stamp, the leg counted `autolevel_acted` off it and
dropped the rest, so a mine-sourced candidate that acted was
`acted_unrecoverable` *the day it was made* — not a backlog but the shape of the
leg, and most of the pool, `curation.depth` rendering through `mine.make` too.
The leg writes the file now. **That closure does not reach backwards**: every mine
row already in the store still has no curve anywhere, which is what makes the
backfill below a sweep rather than a one-off.

`curate autolevel survey` reads that, renders nothing, and prices the rest.
Over `20260908T144844Z` on 2026-09-08:

| | seats |
|---|---|
| already carry a whole stamp on a run record | 639 |
| take no operator at all (the direct-trap family) | 84 |
| have no curve on any record | 277 |
| …of those, still holding the `.leveled/` they shipped through | 82 |

`curate autolevel backfill` re-derives the 277 at candidate geometry through
`colorize.render`, the one door a candidate is ever made by, and appends the whole
stamp to `artifacts/curation/autolevel_backfill.jsonl` keyed by recipe key.
**274 seats in 320 s, 1.17 s each, zero failures**; 110 acted and 164 came back in
band. Every seat of the record is replayable after it: 916 replayable, 84 with no
operator, none left. Flushed every 25 seats, so a killed leg keeps what it did and
the next run skips it.

**A backfilled curve is a re-derivation, not a recovery.** The original base render
is gone — what is on disk is the levelled picture the judge scored — so the row
says `rederived` and carries its own verdict against the ramp that shipped. That
verdict came back **82 comparable, 82 agree, 0 differ**. What the source said about
its own curve travels with it, so a release that inherits a backfilled curve stamps
`was: rederived` and is never mistaken for one that inherited the original.

The sidecar is **not a Durable-class store**, on the three-way rule: it is hot,
it is regenerable at 1.17 s a seat by the command that made it, and the thing it
amends is untouched. It is also in the ignored tree, so a clone does not have it
and the website still ships the stored picture for a seat it cannot replay.

#### The store-wide sweep: `--record all`

`--record all` sweeps every seat of every recorded gallery instead of one
record's — `tentative.protected_keys`, which is what retention must keep and
therefore exactly what has to stay replayable. **Published or not**, because an
older record's IDs are the ones a clone resolves; and de-duplicated for free,
because a key seated in nine galleries is one picture and one render. `curate
autolevel survey --record all` prices it without rendering anything, and it is
the thing to run first: the answer is hours, and the seats that need a curve are
a fraction of the protected set rather than all of it.

**Swept store-wide on 2026-09-09 and it is closed: over 7,089 protected seats,
6,466 replayable, 623 take no operator at all, 0 left to backfill.** The last 60
cost **41.7 s, 0.69 s a seat, zero failures** — 12 agreed with the ramp they
shipped through and 48 had none to compare against. So **`no operator` is the whole
of what is unreplayable**, that being the direct-trap family, which has nothing to
recover; `acted_unrecoverable` is not a state any live seat is in.

**Expect the tail to refill and re-price it rather than trusting the zero.** A new
record seats rows whose leg wrote no curve down, so the number moves with every
record taken — those 60 were the three galleries recorded that afternoon. The
survey answers in seconds and renders nothing, which is why it is the thing to run
first and why this paragraph states a *rule* and a reading rather than a target.

## A standing score is a reading of a picture, and the picture can stop existing

The sidecar row names the view its score was read off — a regime and a file name
— and for most of this supply that name no longer describes anything. Three ways,
and `curate redraw` reports the split:

* **regime** — the row states no regime at all, which means it was read at
  640x360 ss2 before old stock started falling to the node regime. The picture is
  not lost: all 28,072 of those views are in `artifacts/location_views` on the
  archive tier, and they measure 640x360. What makes the score stale is that
  curation deliberately does not read there any more — the deploy cache is
  frozen, and `_picture_for` sends a regime-less row to the node regime like every
  walk node;
* **picture** — the score was read off a walk's own gate render, filed under the
  run's node id rather than under a digest, or off a view whose digest has since
  moved. `renders.job_name` digests the spec that goes over the wire and the spec
  carries the engine's own **mode catalog**, so a catalog entry gaining a field
  renames every view in the cache without changing a pixel;
* **engine** — the right file at the right name, with nothing saying which build
  drew it.

That third one is the one nothing could ask before. A view is addressed by a
digest of its recipe, and *which program carried the recipe out* is not in the
recipe. `identity.enforce` pinned four settings — colormap, cyclicity, node
frame, cap policy — and all four hold while the binary underneath them is a
different program. `fractal_wallpapers.engine_fingerprint` names the build by
what it draws: six pinned probes over four family kinds and six modes, rendered
through `renders.spec_of` at the node regime and digested to sixteen hex
characters, about 0.35 s and cached per process. It is preferred over a source
revision because it also catches a rebuild from unchanged source and a moved mode
catalog.

**Every view written now carries the build beside it.** One `drawn_by.jsonl` per
view directory — `{schema, view, engine}` a row, appended, last row winning — so
a re-render under a new build appends rather than rewrites and an interrupted
refresh has recorded exactly what it finished. A view no row claims is
`unknown`, which is not a fingerprint and is therefore stale: it is re-rendered
on read and never scored. That holds for a walk's gate render too
(`intake.gate_render` checks the stamp), so the ledger's own pictures stop being
believed on the strength of lying at the right coordinates.

**`curate redraw`** re-renders every stale view at the node regime, reads it
through the shipped location head, and appends the result to
`artifacts/curation/score_amendments.jsonl` — append-only, keyed by **(location
key, engine fingerprint)**, carrying the old score, the new score and the
fingerprint the old view was drawn under (`unknown` where nothing recorded it).
The sidecar itself is **never edited**: it is the record of what the seating was
actually decided on, and a pass that overwrote it would delete the only evidence.
Serial, because the engine threads inside one render; measured on 2026-08-25 at
**38 views/s** on the hot tier including the stamp write, so a whole 90k supply is
about 40 minutes of engine plus the head's own pass. Idempotent and resumable: a
second call over an unchanged supply through an unchanged engine writes nothing.
The amendment is regenerable in principle — from the sidecar, the engine and the
head — and only on a machine whose engine still fingerprints the same, which is
why it stopped being treated as a cache on 2026-09-02: it has a durable copy and
a tracked manifest like the sidecar (`curate amendments save|check|restore`), and
`curate run` refuses without it.

**Every reader of a seating score prefers the amendment, through one door.**
`intake.read_scores` overlays it and returns the same row shape, so the five read
sites need to know nothing: `intake.ranked` (which is `curate plan` and `curate
run`), the gallery pass's `admitted_only` cut, its `slots_for` guarantee, its
`quality_of` sort and its `_ranks` table, plus `embeddings.admitted` — the
denominator that decides which locations the pass can select at all — and
`manufacture.admitted_locations`. The last two used to open the file directly and
now do not. `read_scores(amended=False)` exists only for measuring the shift.

**The harvest side is deliberately left alone.** A walk scores the gate render it
*just made*, so `discovery.scoring`'s floor reads are current by construction and
have no cached picture to be stale about. What changed there is that those
renders are now stamped as they are made, which is what lets a later reader tell
them from a picture some other build drew.

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
replacement (`colorize.modes_drawn_for`, seeded on **`(seed, head, key)`** — the
run's own `--seed` as well as the location and the head — so a resume re-derives
the pair and two runs over one place draw differently). run10 seated 15 of 40 strange slots with 115
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

**The pass runs inside one collection at a time**, since 2026-08-27. The rule is per
collection and always was — a group holding a run's `diagnostic` picture and a
gallery seat of the same place is two collections agreeing about a location — but the
pass read the store unscoped, and by the time gallery4 shipped that read found 28
groups of which 27 were exactly that agreement. Running it as it stood would have
retired 27 wallpapers the rule does not reach. Scoped, it found the one real repeat:
`group#225` in `multibrot5`, two gallery4 seats of one place, `4758` retired behind
`d0094` on Matt's ruling of 2026-08-27 (`P(>=4)` 0.159 against 0.015, and the pass's
own `P(>=3)` ranking agrees). `curate repeats` still reads the whole store at once,
which is what it is for.

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
merely undocumented. Four run8h strange rows sat below the bar as it stood when
they were ruled on (0.685, on the retired artifact the row itself names) and stay
served on Matt's reading of the sheet — the exception is keyed on the row, so it
has survived every flip since, each of which moved the bar and re-scored every
score under it; `data/curation/bar_exceptions.jsonl` names
them one by one, with the bar as it was, the score, who ruled and when, and
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
[`durability`](durability.py) owns the mechanism and [`durables`](durables.py) the
list — the split is the note below. What follows is: a copy on the archive
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

**`grown` stops being ordinary before anything deletes or moves under the tree.**
The delta a `grown` reports is content that exists on one disk only, and the whole
point of the durable is that no such content should be there when the tree is
being operated on. Measured 2026-09-02, all three of the manually-saved durables
were behind at once — the supply by 15,194 rows and eleven days, the embedding
store by 10,669 rows (a GPU leg to remake), the reduced-signature sidecar by
21.7 MB — while the ledger's `rows`/`scores`/`flatness`, saved that morning,
matched their manifests to the byte. So the pre-flight for any tree surgery is
`curate sidecar save`, `curate embeddings save` and `curate signatures save`
first, and `check` on all of them after. Both files that had no durable at all on
that date have one now: `score_amendments.jsonl` (`curate amendments`) and
`artifacts/curation/hunt/frames.jsonl` (`curate frames`), and the guard at the top
of `curate run` covers all three of the supply, the amendment and the frame
index.

**The mechanism and the list are two modules, and the split closed an import
cycle.** [`durability`](durability.py) knows what a `Durable` is and how one is
saved, checked and restored; it names no file. [`durables`](durables.py) holds the
sidecar's own paths and `guarded()` — the three a run refuses to start without.
The old shape had `guarded()` reaching from inside `durability` **up** into
`amend` and `hunt`, two modules that import it, through imports written inside the
function body. That is a floor module holding a list of its own callers, and it
kept `durability` and the gallery passes' gate store inside the largest import
cycle in the tree:
breaking it took the tree's biggest strongly-connected component from **49 modules
to 47**. The zero-argument calls went with it — `durability.save()` meaning the
sidecar was the same accident from the other end, a mechanism whose default
argument was one caller's file — so `save`, `check`, `restore`, `read_manifest`
and `write_manifest` all take their `Durable` now, and `durables.sidecar()` is
spelled at the call site like every other one.

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

**What "the stored plan" is, exactly, is `run.SHAPE`.** Seven keys — `n`, `seed`,
`strange_share`, `modes`, `attempts`, `ledgers`, `ephemeral` — and they are the
whole of what a resume is compared against. A flag outside that tuple is an
*execution* setting and a resume may carry a different one: `--workers`, `--deep`,
`--device`, `--skip-release`. The split is the useful part of the rule, because it
says which flags a person may retype under pressure at four in the morning and
which ones change what the run is. Adding a knob that decides what gets made
without adding it here is how a resumed run silently becomes a second run.

**A ledger that has been archived is still readable, and only outputs say
otherwise.** `cli.resolve_input` and `cli.resolve_output` do the same resolution
against the checkout and the two tiers, and differ in exactly one thing: the
output form **refuses** a name that resolves to the archive, because writing there
puts fresh bytes behind a seek-bound disk and leaves one subtree spread across
both tiers. The input form carries no such guard. So `curate score --ledger
<archived>` is a legitimate read and needs no restore, while anything naming a
place to *write* into an archived subtree stops and names the restore command.
Reading and writing are different questions about the same path, and an input
held to an output's guard is a subtree somebody has to restore before they may so
much as look at it.

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
score-free — which colours the pool's renders *are* — runs over the whole pool.
Everything floor-referenced runs only over rows whose reading stands on the very
artifact that kind's floor was measured on, and a row on another artifact is
**refused, not counted**.

The test is the **artifact** and never which block the number is in — see
`rescore.reading_on` above. It used to be the block, and that made this half blind
to every gallery-pass attempt row: 4,975 pictures qualified where 15,488 do now,
smooth 1,557 to 4,307 and strange 3,418 to 11,181. A row nothing can **place** at
all — no current block and no run summary naming the head — is reported and left
out rather than refused, because a missing record is not evidence of a scale mix.

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

**A parity arm is the caller's task re-pointed, and that is load-bearing.**
`release.parity` used to rebuild each arm's `release.Task` from six of its seven
fields, dropping `mode_params` — so a plan carrying a varied seat was checked as
two renders of the **bare** mode, which agree with each other perfectly and pass.
A check that passes by discarding what it is checking is worse than no check, and
the failure is silent because the bare picture is a perfectly good picture of
something else. It is `dataclasses.replace(task, output=...)` since 2026-09-05:
the arm differs from the caller's task in the output path alone, so a field added
to the task later carries without an edit here.

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
fractal-wallpapers curate coverage --step probe --workers 3
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

**Every recolor path states its field curve, and this is the one that forgot.** A
dumped field records the curve it was dumped under, which is the *mode's own*; a
render states `colorize.CURVE` and `renders.coloring_of` writes it over the
mode's. Those two agree for every field mode but one — **`trap_circle` names
`log` and every other field mode names `linear`** — so a recolor that leaves
`transform` off its spec inherits the dump's curve and produces, for that one
mode and no other, a different picture from the render of the same row. The probe
passes the curve explicitly for exactly that reason; the shipped panel holds
three `trap_circle` cells of sixteen, so the omission was worth three cells of
every table on this page. `manufacture.render_through` is the other site that
states it, and the rule is the general one: a recolor spec that does not name its
transform is a picture nobody can join back to a render.

**Runtime.** 16 cells x 901 maps, plus the unfolded arm for the 156 sequential
maps, is 16,912 recolors at about 75 ms each: 21 minutes serial, and about 6 was
measured at `--workers 6`. It scales with the library and the library is 1,021
maps since `classic-pairs-2026-09`, so read those figures as a rate rather than
as a wall clock. That default is **three** since 2026-08-28 — every
probe is a recolor through the engine, so it is the locked render pool and not a
tuning knob — which puts it near 9 minutes at the release leg's measured 2.38x
concurrency gain on three. Re-measure rather than trusting that arithmetic. The panel's own dumps are 56 iteration passes, about 40 seconds.
Each recolor is censused and its JPEG overwritten rather than kept — keeping them
would be a gigabyte of pictures answering four hundred bytes each — so the contact
sheet re-makes the sixteen tiles it shows.
