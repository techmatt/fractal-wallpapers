Judging finished renders: what to colour, how to colour it, what to keep, and
what to make at full size.

This is the last stage. Everything upstream produces *supply* — places a walk
found, judges trained on human verdicts, a palette head that ranks colour choices.
Curation spends it: it turns the union of every walk into a small set of finished
wallpapers and a durable account of why those and not the others.

```
binding    which ledgers this curation reads, declared once and never guessed
durability a file kept on two disks under a tracked manifest, and the run guard
rescore    the accumulated pool, read again through the heads shipped now
floors     every number that removes a picture, in one file
neutral    the one picture a location is EMBEDDED from, and its frozen recipe
embeddings one DINOv2 vector per admitted location, keyed and kept forever
intake     the ranked offer, best first per partition
budget     how many pictures to make, and for which judge
colorize   a candidate set of maps, the head's pick, a render, a verdict
framing    where a location's attempts are framed, decided before they render
recipes    what decides a candidate's pixels, as one value with one key
candidate_ledger  every recipe ever rendered, one row each, with its colour
headroom   what each selection constraint needs, holds, and costs to buy — no solver
view       what one pass may reach: strata, and band-blind slices of them
rules      one spelling per selection rule, over incremental state
signatures the diversity rule's bound signature, swept once into a sidecar
solve      THE gallery leg: the view, a greedy seed, and 1-swap improvement
distinct   which places are visibly different places, decided before any colour
selection  top-N per judge, under the slot and supply caps, the location rule
           — and the bar
gallery_store  four retired passes' attempt rows and pass records, still read
release    the selected rows again at full size, workers rendering
pacing     the wall clock: what may still start, and what is killed
records    what the run decided, and out of what population
rejection  taking a released row back afterwards, without losing what the run did
below_bar  the glance sheet of what an acting bar would take back, to rule off
sheet      the same thing laid out for a person to disagree with
manufacture  forcing the rare swatches onto good places, and the sheets that ask
checks     the two claims only a re-render can settle
run        the wiring, and nothing else
```

```
fractal-wallpapers curate score --harvest artifacts/harvest_run3   # through the location head
fractal-wallpapers curate sidecar save                             # the supply, made durable
fractal-wallpapers curate embed                                    # a vector per admitted location
fractal-wallpapers curate embeddings save                          # the vectors, made durable
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
fractal-wallpapers curate gallery-store check --pass gallery1          # is a retired pass's store whole?
fractal-wallpapers curate candidate-ledger backfill    # the cache, from what exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger save        # both files, made durable
fractal-wallpapers curate headroom                     # the census: what is short, and what one more costs
fractal-wallpapers curate headroom --n 20 --n 150      # only these rungs of the ladder
fractal-wallpapers curate headroom --flat-floor        # bound the FLAT mode floor, for a baseline
fractal-wallpapers curate distinct                     # the neutral pre-selection read, and the radius sheet
fractal-wallpapers curate distinct --no-premise        # the join and the sheet, measuring no pixel cloud
fractal-wallpapers curate signatures sweep              # the bound signatures, once, for the clearing pool
fractal-wallpapers curate signatures coverage          # how much of the pool the sidecar can answer for
fractal-wallpapers curate solve run --n 20 --no-render # THE gallery leg: decide, render nothing
fractal-wallpapers curate solve run --n 150            # the gallery, then the pictures
fractal-wallpapers curate solve run --n 1000 --no-render   # ~6 min, scaled not measured
fractal-wallpapers curate solve run --n 2000 --no-render   # the planning size, 10 min
fractal-wallpapers curate manufacture --step register --write          # BEFORE anything
fractal-wallpapers curate manufacture --oversample 2.5                 # plan, build, select
fractal-wallpapers curate manufacture --step verify --sheet artifacts/<sheet>
```

## The pre-solver gallery pass, and what took its place

**Deleted on 2026-08-28**, ruled at ckpt 87. `curate gallery` was the second
phase: a quality-weighted farthest-point draw over the neutral embeddings picked
N locations, each chosen point bought a small judged attempt on its own
neighbourhood, and a sequential walk seated the winners under two floors, the
one-wallpaper-per-location rule and the colour ceiling. Four passes ran under it —
`gallery1` through `gallery4` — and everything they wrote is still here and still
read: the pass records and slot rows in `data/curation/gallery/<pass>/`, the
winners in `data/curation/release/<pass>/`, the attempt rows behind
[`gallery_store`], and 14,316 of the candidate ledger's rows.

**What replaced it is propose-then-choose.** `curate solve` is the whole
choosing now — off the candidate ledger rather than off a draw's own attempts, so
it chooses among pictures that already exist. It draws no points: the ledger is
the proposal side and `curate hunt`, `curate mine` and `curate depth` are what add
to it. It renders its seats unless told `--no-render`, at
[`release.RELEASE_REGIME`], which is the geometry the pass shipped at and is now
named where every leg that ships a wallpaper reads it.

It was briefly two legs — a sequential `curate seat` and an exact `curate solve` —
and that pair is gone too. `curate seat` is retired; the exact solve is retired;
the one leg behind `curate solve` is the section below.

Three commands went with the phase: `curate gallery`, `curate draw` (its step-4
point draw alone) and `curate on-demand` (the reconciliation of a pass's
extra-pick log with its attempt store, which had already run on every pass it was
written for). `curate gallery-store` stays, because the four passes' attempt rows
are a third of the ledger's backfill.

What the pass established and the rest of this file still rests on is below: the
**colour ceiling** and its targets, which `curate solve` reads; the **binding reason** an empty seat records, which is how the four passes'
slot rows are still re-read; and the **framing refinement**, whose live home is
the walk's own close-of-run leg (`supply/harvest.py`) rather than a seating.

**A `centered` row is refined on its scale alone.** A location row carrying
`centered: true` — every nucleus location `discovery.reframing` writes, and
anything else whose centre *is* the location — has stage B switched off:
`framing.recentres` returns nothing for it, `framing.refine` plans no stage-B
frames for it, and the record says `centered` beside the decision. Three frames a
location instead of seven, and the reason is not the saving: a quarter-frame off a
solved nucleus is a crop of somewhere else wearing the atom's name, and the
minibrot the reframing channel exists to frame would be off centre in the picture
a gallery seats. The flag is read off the row through `framing.is_centered`, never
off a channel name, so a row that has never heard of the field and a row that says
`false` are one case.

### What an empty seat names, and why it is not the first rule that refused anything

A slot that goes unfilled records **one slug** and the counts that chose it:
`eligible`, `below_floor`, `location_served`, and under a ceiling
`ceiling.refused` / `ceiling.refused_by` / `ceiling.withheld`. The slug is the
field a reader trusts when asking whether under-fill is a *supply* problem or a
*colour* problem, and the two have opposite remedies — draw more points and lower
a floor, or loosen the ceiling.

It names the **deepest rule a candidate actually reached**, because that is the
one whose lifting would have filled the seat. The rules act in order — the
ceiling's mandate withholds, then the floor, then one-wallpaper-per-location,
then the ceiling's three tests — so a candidate counted `location_served` had
already cleared the floor, and naming the floor because something else was under
it sends the reader looking for supply that is already there. That is not
hypothetical: gallery4's seat `0153` recorded `below_bar` with 27 of its 30
candidates under the floor, while the 3 that cleared it were turned away by the
location rule and its best held P(≥3) 0.881 against a floor of 0.770. It reads
`location_served` under [`selection.binding_reason`], and every count that says so
was already on the tracked record — the pass does not have to be run again to
re-read it.

Two slugs are the gallery's alone. `ceiling` is every floor-clearer refused by
the colour ceiling, with `refused_by` naming which of group / dominance / twin
did it; it cannot be reached through a seating while the least-violating fallback
stands above it, since a seat with anything refused is seated by that fallback,
and it is written because the fallback is a policy and not a law. `mixed` is a
mandated cell having narrowed the sequence before any rule saw the rest, so no
single rule accounts for the seat and the counts beside it say the whole story.

The **release** leg (`selection._fill`, per partition rather than per seat) still
names the first cause that applies. It has no ceiling above it, its reason is a
field in every tracked run record, and re-reading those under a new rule is a
decision about the records rather than a fix.

### The colour ceiling, and the targets that are the same feature with the sign flipped

A pass used to judge each picture on its own and let the collection come out
however the pool happened to be coloured. gallery3's did: red at 2.10× uniform in
the supply *before* a seat was filled and 2.45× after, lime at 0.19×, seven of the
twelve hue families under one seat in twelve, and one picture in a hundred and
fifty green. `curation.ceiling` is the two levers that act on that, and they read
one feature — `palettes.dominance`, what colour a picture is.

Three tests at each seat, in order, the first failure naming the rejection:

```
group       one seat per palette group, unless this candidate's pixel cloud is
            more than 0.10 from EVERY picture that group already seated
dominance   pro rata: with n seats filled including this one, a colour may hold
            floor(K x t x n) + 1 of them, K = 2, t uniform (1/48 a cell, 1/12 a
            family) unless a --target moved it. Only a candidate DOMINANT in an
            over-allowance colour is refused; carrying some of it is fine
twin        no picture within 0.0586 of two already-shipped ones
```

The pro-rata form is the fix for what a cumulative whole-gallery budget did: that
one is denominated in a unit the gallery only fills to 79%, so two thirds of its
range can never fire, the one setting that does first fires at seat 110 of 150,
and — because the test is on the after-state — it then refuses everything carrying
that colour for the rest of the walk. `floor(K·t·n) + 1` has the warm-up in the
`+ 1`: the first seat may be any colour, and the allowance grows with the walk.

**A seat used to be allowed to ask for more pictures, and that is gone.** The
pre-solver pass ordered a seat as: the candidates that exist, then up to three
rendered right there, then the least-violating fallback, flagged — because a
colour rule that can only refuse spends its seats on the fallback, the pool
having been proposed by a quality judge that never had colour in the question.
The pass and its `ceiling.Seating` both went on 2026-08-28; the **idea** is kept
as a design note in the handoff docs and no code implements it. `curate solve` chooses among pictures
that already exist, so a seat with no acceptable colour is a shortage in the
ledger, and the answer to it is `curate hunt`'s conditioned leg or
`curate depth`'s conditioned draw. The four passes' on-demand rows are still in
their attempt stores, stamped `on_demand`, and are part of the ledger like any
other pool row.

The other half is solved one step earlier and for free: when the palette head
picks a map whose **group another attempt of the plan already picked**, its
next-ranked candidate takes that attempt instead. A pure identity filter, no
pixels and no state about pictures, recorded on the row as `group_skipped`.

**A re-seat replays the whole sequence.** The ceiling makes seating
path-dependent, so a slot that moves invalidates every seat after it in the walk
order — and only after it, which is why replaying is enough and patching is not.
Replaying arithmetic is free; replaying renders is not, which is what the
on-demand cache is for.

### `--target <cell>=<fraction>`

Asks for at least `ceil(fraction × N)` pictures dominant in one codebook cell,
repeatable. At each seat the pass reads `u = need / seats left`: above 1 the target
**mandates** — only candidates dominant in the cell are eligible; above 0.5 it
**prefers** — dominant candidates rank ahead of the rest and the judge's order
breaks the tie inside each half. Below that the judge decides alone. Setting a
target also replaces the ceiling's allowance for that cell **and for its family**,
and raises the allowance of the cells the target structurally implies (below), so
all of it is denominated in one vector.

A target never lowers a floor and never pads. An unmet one is reported **SHORT**,
in the record and in the log. What actually meets a target is something rendering
a map chosen *for* the colour, bypassing the palette head — the only way a colour
the head declines 83% below base rate ever reaches a seat. `curate hunt`'s
conditioned leg is that lever; the pass's own carrier-attempt plan was **deleted**
rather than repaired, because it seeded its draw on `hash()` over a tuple holding
a cell name, which Python randomizes per process, so a draw recorded as seeded was
not reproducible from its record. `hunt.seed_of` is sha256 and is the shape.

Refused before anything renders if the fractions sum above one, or if a targeted
cell has no carrier in the pass's own collapsed palette pool. `config.ceiling`,
`config.targets` and `config.target_feasibility` on the pass record carry every
constant and every carrier the launch checked.

**A target is also the only lever on the ceiling, which is what a THEMED gallery
needs.** Solve over a pool restricted to one dominant cell and that cell's own
allowance is `floor(K × (1/48) × n) + 1` — **9 seats at n=200** — so the program is
infeasible before any other rule acts, and there is no flag, constant or config that
raises an allowance except this one. `--target <cell>=1.0` puts it at
`floor(2 × 1.0 × n) + 1`, raises the family with it, and raises each companion the
carrier table measures by `t × rate`. Over a pool already filtered to the cell the
target's own demand costs nothing, because cardinality satisfies it.

**A target means a share of the seats that get filled, and under `<= n` that is how
it is spelled.** `_under_fill` relaxes cardinality and nothing else, so a target has
to survive the relaxation — and rebuilt as the hard `ceil(t × n)` it did not: it went
on demanding a share of seats the program had stopped promising, so the re-solve was
infeasible at every count below `n` and the record read `filled: 0` however many
seats the pool could really fill. The readout disappeared in exactly the case a
shortage list is read for. Under `<= n` the row is now

    sum(cell) >= t × sum(all)   as   (1 − t) × sum(cell) − t × sum(rest) >= 0

— linear, the same row wherever the seats do come to `n`, and the same demand at
every smaller size. It is the only weighted row in the program, which is why
`Program.blocks()` states members as `[(column, coefficient)]` there and both readers
of a row (`matrices`, `binding`) go through `solve.members_of`. `Program.target_rule`
names which of the two spellings ran and is on the record beside `cardinality`.

**The fix is guarded but not yet measured on a real pool.** The two instruments the
read used instead of this readout are still the only *measured* answers to "how big a
themed gallery is": the solve's own greedy seed (constructive) and `headroom.twin_bound`
(necessary), which agreed to within two seats on a 2026-08-31 `dark_vivid_green` pool,
88 and 90. Re-running the read's lime arm at n=200 against this under-fill is what would
retire them, and it has not been done.

The same rebuild also dropped `floor=program.floor`, so a `--flat-floor` solve's
under-fill silently reverted to the default per-mode floors — soft either way, so it
moved the reported objective and not feasibility. Both rules are now carried through
and both are stated on the under-fill record, on the infeasible branch too:
`target_rule`, `mode_floor_rule`, `mode_floors`.

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
src/fractal_wallpapers/curation/candidate_ledger.py   the store, the backfill, the census
artifacts/curation/candidate_ledger/rows.jsonl        one row per recipe
artifacts/curation/candidate_ledger/scores.jsonl      ...and its scores
artifacts/curation/candidate_ledger/flatness.jsonl    ...and its dead-space column
artifacts/curation/candidate_ledger/reduced_signatures.jsonl   ...and its twin signatures
data/curation/candidate_ledger/*.manifest.json        what the history keeps of the three
<archive>/curation_backup/candidate_ledger/*.jsonl    the durable copies
```

**Three of the four are mirrored and one is not**, and that is the rule rather than
an oversight: `merge` copies `rows`, `scores` and `flatness` to the archive and
verifies each identical, and the signature sidecar is **regenerable from the pictures**
so it takes the same treatment as the score amendment — no durable copy, no manifest.
Worth knowing anyway, because the sidecar it omits is the one the **binding**
constraint reads: the n=2000 solve of 2026-09-01 served **9,371 of 9,388** signatures
from it. Re-deriving all 11,636 rows is about **2.8 minutes** at `DIRECTIONS = 256`,
against ~19 at the 1024 it used before that constant moved — so this is an annoyance
now and was close to an outage before.

```
fractal-wallpapers curate candidate-ledger backfill   # from what already exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger prune      # back to the rule, ~35 s. RUNS FROM `merge`
fractal-wallpapers curate candidate-ledger prune --dry-run   # THE dry run. Touches nothing
fractal-wallpapers curate candidate-ledger pictures   # rows naming a picture that is not there
fractal-wallpapers curate candidate-ledger re-render  # ...and put them back. ~1.5 pictures/s
fractal-wallpapers curate candidate-ledger score      # every picture through the judge shipped NOW
fractal-wallpapers curate candidate-ledger save       # the live files, their manifests
fractal-wallpapers curate candidate-ledger check      # are they whole
fractal-wallpapers curate flatness save               # its own durable. `merge` does this too
```

### The step a judge adoption makes necessary

**The morning after a flip this store holds a full set of scores and the pool is
empty.** Not a bug and not a migration that was forgotten: the sidecar is keyed
`(recipe, artifact, regime)` and `scores_by_recipe` joins on the live artifact
alone, so every row reads as *unscored on the head that ships* until it is read
again. `solve.pool` refuses all of them as `no_score` and every gallery, census
and headroom read over the ledger comes back empty. `curate candidate-ledger
score` is the step that closes it, and it is the only one — nothing else in this
tree reads a ledger picture through the judge.

It writes **beside** the retired artifact's rows and never over them: a picture
read by two judges is two facts, and the retired reading is what every
before-and-after comparison is taken against. Resumable by chunk — 4,096
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
there, plus the four protections. They are no longer a function of the attempts
made.** That sentence is the whole point of the store, and it holds because
`candidate_ledger.prune` runs inside `candidate_ledger.merge` — THE door every
leg comes through. A rule that ran anywhere else would be a rule the store
stopped obeying between the times somebody remembered it.

| | rows | on disk |
|---|---|---|
| before, 2026-08-29 | 366,236 | 1,057.3 MiB |
| after | 122,516 | 150.8 MiB |

Re-running the rule over the store is a fixed point: 122,516 of 122,516 rows
kept, nothing dropped, 18.4 s to decide. The 243,720 rows the rule let go were
**deleted** rather than archived, with their pictures, on Matt's ruling: everything removed is either retained already
or re-renderable from a retained recipe, and a second copy nobody could explain
later is worse than none. What that costs is real and is measured rather than
assumed — see *what the rule costs* below.

`RETAIN_PER_PAIR` is **three** and it is **the** constant: a picture is kept if
and only if its row is. It was one of two until 2026-08-29, when
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
pool's** — the release rows in the tracked store and every gallery pass's attempt
rows in its own, resolved to the one candidate render each is about. It exists
because `curate rescore` refuses outright while any of them is missing: a reading
of most of the pool is not a reading of the pool, and the pool's pictures live
under the regenerable tree where a sweep can take them.

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

**A score is joined on ONE judge artifact, and the join says so.** The sidecar is
keyed `(recipe key, artifact, regime)` because a number is comparable only inside
that triple. Both readers that mattered — `mine.population` and `solve.pool` —
flattened it to the recipe key alone, which is last-row-wins across artifacts:
two judges' scales in one ordering with nothing anywhere saying so. Today the
store holds **one** artifact and one regime and 0 of 85,129 keys are duplicated,
so those joins were right by luck; the first adoption is what turns luck into a
silent wrong answer, and an adoption is a thing this project plans to do.
`candidate_ledger.scores_by_recipe` is the join now — the live head unless a
caller names an artifact — and a row read on any other is **omitted**, not
rescaled. `stale_scores` is the census of what was left behind, so a caller can
say how much of its population it has no score for. A recipe with no reading on
the live judge has no score, which is honest and different from having an old one.

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
pre-stamp material accepted as unknown-engine, by rule.

**The census, at N=20.** Nothing binds. All 48 colour cells, all 12 families, all
18 production modes and all 822 drawable palette groups are held; none is empty.
The 20-point draw under the hard radius fills, with 79 locations refused by it.

What is *thin* is places and green. The ledger stands on **1,223 locations** —
2 recipes at the 25th percentile, 8 at the median, 44 at the deepest — so depth
per place is not the constraint and breadth of place is. And the green half of
the wheel is a quarter of the red half: 986 locations carry red, 248 carry lime,
258 green, 324 teal. The thinnest cell of the 48 is `dark_vivid_lime` at 44
locations. 227 of the 822 palette groups have exactly one recipe behind them.

## `curate solve` — one leg, one pool, one command

This is the whole of the choosing. It used to be two — a sequential `curate seat`
that walked a ranked list, and an exact `curate solve` that stated the same
intentions as a mixed-integer program and handed them to HiGHS. They chose from
**different pools** under two copies of most rules and two different rules for one
of them, and a divergence like that is not one anybody finds by reading either
file. Both are gone. `curate seat` is retired with them.

```
src/fractal_wallpapers/curation/view.py    what one pass may reach: strata, band-blind slices
src/fractal_wallpapers/curation/rules.py   one spelling per rule, over incremental state
src/fractal_wallpapers/curation/solve.py   the view, the seed, the swap loop, the record
artifacts/curation/solve/<name>/solve.json          the record
artifacts/curation/solve/<name>/release/            the seats at release geometry
artifacts/curation/solve/<name>/contact_sheet.html  the seats, and what each rule refused
```

```
fractal-wallpapers curate solve run --n 150                  # one gallery, rendered
fractal-wallpapers curate solve run --n 150 --no-render      # decide, render nothing
fractal-wallpapers curate solve run --n 1000 --no-render     # ~6 min, scaled not measured
fractal-wallpapers curate solve run --n 2000 --no-render     # THE planning size (Matt), 10 min
fractal-wallpapers curate solve run --n 150 --no-swap        # the greedy seed alone
fractal-wallpapers curate solve run --n 150 --swap-seconds 300   # a clock on the loop only
fractal-wallpapers curate solve run --n 150 --flat-floor     # the pre-2026-08-31 mode floor
fractal-wallpapers curate solve run --n 150 --group-cap identity --key p_ge4   # the incumbent
fractal-wallpapers curate solve run --n 150 --sheet-out <path>    # the sheet, elsewhere
fractal-wallpapers curate solve run --n 20 --target dark_vivid_lime=1.0   # a colour demand
fractal-wallpapers curate solve run --n 20 --locations 40    # only the 40 best places
fractal-wallpapers curate solve run --n 100 --themed dark_vivid_green --no-render  # THEMED
fractal-wallpapers curate solve run --n 100 --themed dark_vivid_green --themed-radius 0.05
```

It needs `numpy` and `pillow`, which is the `solve` extra (`pip install -e
.[solve]`). **It needs no solver**: SciPy went with the MILP. The leg loads no
head either — every score it reads is off the ledger's sidecar — so a machine that
chooses a gallery needs neither the CUDA wheels nor a MIP.

### The four steps

1. **The view** (`curation.view`). The pool above its per-mode bars and past the
   neutral pre-selection, thinned to what one pass may reach. **Two layers, and
   only one of them is ever cut.** Every place's strongest row by the pass's own
   key is in, always — that set is exactly what the sequential seating this leg
   replaced walked, so a view holding all of it cannot choose worse than that walk
   did. On top of it, that place's best row in each further `(kind, mode, cell)`
   stratum it can field — the **alternates** — and those are what a stratum's
   quota is spent on: the whole set at or below `SMALL_STRATUM` (8), or a
   **band-blind slice** sized at `ROWS_PER_SEAT` (2) times what `n` seats could
   spend on that stratum. Strata, sizes, strides and the draw seed land on the
   record, and the pool is never mutated.

   The first draft sized its quotas over both layers together, and it is worth
   knowing why that is wrong: it left the view reaching **1,768 of 4,496 places**,
   and the seed came back at a worst seated score of **0.299** where the retired
   greedy had reached **0.418** on the same pool. A view that can cut into the
   place-bests can choose worse than the walk it replaced. This one cannot.
2. **The rules** (`curation.rules`). One set-level predicate each, over incremental
   state: `admits` for the seed, `removals` for the swap loop, and never a
   sequential copy beside a set copy. The state holds which seats carry each cell,
   family, palette group and mode — *which*, not how many, because a swap has to
   know what to take out.
3. **The greedy seed.** The seating order this project already had: the mandated
   demands from their own subpools scarcest first, then the ranked walk.
4. **1-swap improvement.** One seat out, one candidate in, accepted only on strict
   lexicographic improvement, until a full pass finds none. No 2-swaps.

**It is anytime.** The gallery is valid from its first seat, so a clock, a `Ctrl-C`
or a pass cap leaves an answer rather than nothing. That is the whole reason it
replaced a method that had no answer at all until it had a proof.

### The objective, and why nothing guards a met demand

Lexicographic and strict, in this order: **(1)** seats filled, every one above its
own mode's bar because that is what the pool is; **(2)** the **shortfall** against
every demand — the mode floors and any colour target — minimized, and nothing
padded; **(3)** the **worst seated score**, maximized; **(4)** the sum. The rank
quantity is `solve.RANK_KEY`, the fitted five-column form; `p_ge4` alone is not it
and is still reachable by name.

**A filled floor above the worst seat is Matt's ruling**, and it is what "grab
where possible" means: a mode this pool can represent is represented, and the
price is paid out of the weakest seat rather than out of the roster. A swap that
fills a short floor at the cost of the worst seat is the ordinary case here, not
the refused one.

The retired program had these two the other way round — its floor stage sat above
the mode penalty — and that order needed a guard. The worst seat is by
construction a scarce mode's, so trading it for a strong smooth candidate lifted
tier 2 and nothing beneath could buy the representation back; `solve.Gallery`
carried a `protected` set, a `guards` lookup and a `keep_demands` flag to stop it,
and `curate solve`'s record carried a `demands_kept` field to say so. **All four
are gone.** Under this order a met demand is kept by the order itself: giving one
back is a tier-2 loss and the two tiers beneath cannot pay for it. `Gallery.weakest`
now offers every seat it reaches and `after_swap` refuses on the arithmetic, which
is where a refusal belongs.

Nothing pads. A demand the pool cannot fill is still short, still recorded and
still minimized by tier 2 — a shortfall is a finding, never something the leg
repairs by seating something it should not.

### The bound signature is swept once, not derived per pass

The twin rule is the only one that opens a picture, and what one signature costs is
**the sort, not the decode**. Measured stage by stage on 2026-09-01 at the 1024
directions the metric then used, 141 ms a signature: `codebook.pixels` **2.65 ms** — libjpeg's `draft` lands on `CENSUS_SIZE`
without building the full image — `space.oklab` 5.19 ms, the projection 4.49 ms, and
`numpy.sort` over the `[4096 samples, 1024 directions]` projections **121 ms, 86% of
it**. Until 2026-09-01 this paragraph read "the JPEG decode — about 96 ms", which was
the whole signature attributed to a stage costing 2% of it: the total was right and the
attribution was not, and it is recorded because it pointed every speedup at the wrong
place. `BUILD_greedy_swap_solve` measured the signatures at ~100% of the leg: 4,624 made
at n=150 for 443 s of a 461 s leg. Two prunes and a per-pass reduced store cut that to
289 signatures and 38.4 s, and
decoding in parallel over three workers was implemented, measured and **reverted** —
a prefetch has to guess which candidates the walk will open, the only free guess
(the counted rules) is a superset, and at n=150 the leg opens 289 pictures out of a
6,515-row view. A guess that over-fetches to a thousand loses to 289 on one core
however many workers it has.

`curation.signatures` is the same win without the guess. The reduced signature is a
property of the **picture**, so it is swept once over the clearing pool into
`artifacts/curation/candidate_ledger/reduced_signatures.jsonl` — one JSONL row a
recipe, the vector base64-packed as `float32` the way `curation.embeddings` packs
its unit vectors — and `solve` and `curate headroom --twin` read it instead of
deriving it. `float32` and not `float16` because the bound is a *lower* bound and a
value rounded the wrong way would let a real twin be pruned; the store round-trips
bit-identically and `test_signatures.py` pins that.

**Staleness is the picture's identity, never a clock.** The row carries the picture
it was read from and a mismatch is the only staleness there is — `curate retention`
moves pictures and a restore rewrites mtimes, so a time-keyed store would re-sweep
a pool nothing changed *and* miss a picture replaced inside one second. The two
reduction constants ride on the row too, so changing either invalidates the store
at once.

It is regenerable and gets no `durability.Durable`: **65.4 MB, 11,454 rows, 103 s**
over the standard three-worker pool with nothing unreadable. A second copy of a
derived store that size earns less than it costs. It was 247 MB and 448 s until
`pixel_clouds.DIRECTIONS` came down to 256 on 2026-09-01 — a reduced signature is
4 KiB now rather than 16.

**What it bought, measured: not the gallery leg.** At n=150 the leg is 37.9 s
without the sidecar and 36.9 s with it, over a bit-identical gallery — and the
reason is structural. `Twins.within` asks for the candidate's reduced form and
then, for the fraction the bound cannot settle, asks for that same key's full cloud
a few lines later; without a sidecar the first call decodes into the Clouds read
cache and the second is a hit, with one the first never touches Clouds and the
second is a cold decode. Both records show `full_signatures_fetched` **325**. The
store removes 289 reduced decodes and hands back 325 full ones. So the win is
bounded by candidates whose bound settles everything, and the swap loop's two
prunes have already removed nearly all of those. The store is still the right shape
— it is the read-ahead's benefit without the read-ahead's guess — but the gallery
leg is not where it shows up, and saying so is cheaper than re-deriving it later.

**Where it does earn its 65.4 MB is `curate headroom --twin`**, which builds one
reduced signature per place to screen millions of pairs and needs a full cloud only
for the few thousand survivors — so nothing cancels. Measured over that sweep's own
population, 4,496 places after the neutral pre-selection: the sidecar answers **all
4,496 in 0.7 s** against **429 s** to decode them at 95 ms a picture — both measured at
1024 directions; a signature is 16.8 ms now, so the same sweep would decode them in about
75 s and the sidecar's edge there is far smaller than it was. That sweep used to build
every one of them and throw them away.

### Two prunes in the swap loop, and both are sound

**The first is on the walk.** A pass goes down the view in rank order and stops at
the worst seated value. Nothing below it can be in an improving swap: a 1-swap does
not change the seat count so tier 1 cannot move; seating a candidate worth less
than the current worst makes the worst that candidate, so tier 3 gets worse; and
the tiers are lexicographic, so a tier 4 gain cannot buy that. The prune tightens
on its own, because every swap that improves tier 3 raises where the next pass
stops.

**It is conditional on nothing being short, and that is not a detail.** Tier 2 is
the shortfall and it sits *above* the worst seat, so a low-ranked row covering a
starved demand still improves the gallery — and a starved mode's only available
row is usually a weak one, which puts it below the floor. A walk that broke there
unconditionally could never reach the one swap "grab where possible" is about. So
with a demand short the walk runs on, considering only rows that cover one; that
test is a dictionary lookup and opens no picture. This was the tier swap's live
defect, caught by re-deriving the prune rather than by the n=150 replay, which
could not see it because that pool's shortfall is zero from the seed onward.

**The second is per candidate, and it is what keeps a pass cheap.** Every seat that
could leave for a candidate is in its **counted** removal set — the four counted
rules intersected, which is dictionary lookups — because the diversity rule can
only ever narrow it. So a candidate worth no more than the weakest member of that
set cannot improve tier 4 (the sum needs the arrival to beat the departure) and
cannot improve tier 2 either (for the worst seat to rise, the seat that leaves must
*be* the worst one, which puts the worst seat inside the set). It is decided before
any picture is opened. `solve.Gallery.hopeless` is the predicate.

Tier 3 is the exception and it is load-bearing: a low-ranked row covering a starved
mode is exactly the swap the third tier exists for, so a candidate counting towards
a currently-short demand is never hopeless.

**Measured on the pool at n=150**, with the reduced-signature store below: the
second prune settles **4,153** candidates without opening a picture and signatures
fall from **4,624 to 289** — counts off the record's own counters, which is what to
read, because this machine is usually shared and the wall times are upper bounds
under unknown load. The gallery is **bit-identical** either way: same seats in the
same order, the same 18 swaps, the same tier breakdown. `tests/test_solve.py` pins
that against an exhaustive neighbourhood walk, because a prune that moved the
answer would be a bug wearing a speedup's clothes.

The one heuristic is `SWAP_DROPS` (8): how many seats are *offered* for removal per
candidate — the weakest by the leg's own key inside the set whose departure would
admit it. It is about which removals are offered and never about which are
accepted.

### What a pass costs is one store

`rules.Twins.reduced_of` keeps **one reduced signature per candidate for the life
of the pass**, unbounded on purpose: 4 KiB a row is 37 MB over the largest view
this project builds, and the full 128 KiB signatures stay in the bounded
cache underneath. Every question the bound asks reads the reduced form; the full
one is fetched lazily and only for the candidates whose bound could not settle
everything — 99.9% of seat comparisons are settled, so most candidates never have
their cloud read back at all.

Deriving the reduced form through the bounded cache instead is what a view larger
than that cache cannot afford: measured before this store existed, **24,969
signatures for an 8,704-row view — 2.9 decodes a row** — and a pass cost the same
whether it took forty-seven swaps or none.

### What it costs, measured on this machine

The first two on the 98,457-candidate pool (11,210 clearing, 9,380 after the neutral
pre-selection over 4,496 places), idle, 2026-08-31; the n=2000 column on the
100,743-candidate pool the reframe-q4 merge left (11,574 clearing, 9,744 after
pre-selection over 4,791 places), 2026-09-01. All `--no-render`:

| | n=150 | n=1000 | n=2000 |
|---|---|---|---|
| view | 6,515 rows over 597 strata | 8,704 over 597 | 9,461 over 604 |
| seats | 150 of 150 | **653 of 1000** | **890 of 2000** |
| **signatures decoded** | **289** (was 4,624) | **19,113** (was 24,969) | **28,826** |
| swaps | 18 over 3 passes | 49 over 3 passes | 75 over 3 passes |
| seed | 22.3 s | 402.0 s | 947.3 s |
| swap loop | 7.1 s | 1,617.9 s | 2,632.1 s, ran out of improvements |
| whole leg, on a *shared* machine | 38.4 s (was 461.1 s) | 2,030.8 s (was 2,743.4 s) | 3,592.1 s |

**And this is the leg before the metric came down to 256 directions**, which is most of
what it cost. Measured the same day on the same pool, `--no-render`, same gallery at
n=150 seat for seat:

| | n=150 | n=2000 |
|---|---|---|
| whole leg | 46.1 s → **16.2 s (2.85x)** | 3,592.1 s → **607.2 s (5.9x)** |
| seed | 25.1 s → **4.5 s** | 947.3 s → **145.8 s** |
| swap loop | 9.4 s → **1.7 s** | 2,632.1 s → **451.3 s** |
| signatures decoded | 317 → 314 | 28,826 → 28,112 |

**And the gallery it chooses barely moves, which was checked against a control rather
than argued.** At n=150 it is **seat for seat identical** — same 150 places, same 26
swaps, same objective, every refusal count the same. At n=2000, against the same pool at
1024 directions (`control1024_n2000`, which is the retired metric exactly because the
sort rearrangement is byte-identical there):

| | 1024 | 256 |
|---|---|---|
| seats / shortfall / worst | 878 / 200 / 0.097761 | **all three identical** |
| sum | 422.86 | 421.56 (−0.3%) |
| places held | — | **863 of 878 (98.3%)** |
| whole leg | 2,517.6 s | **607.2 s** |

The first three objective tiers do not move. Over 5,700 twin verdicts, **5,674 agree**;
26 pairs the old metric called twins the new one does not (0.46%) and 13 the other way,
with the median distance on shared refusals moving **+0.000008** — three parts in ten
million of `ceiling.TAU`. **Read a diverging census against the pool first**: the
`census_n2000` comparison looked like a 22-seat shortfall regression and every seat of it
was `direct_trap_multiply` losing 183 of its 220 clearing rows to a merge, not the metric.

A gallery at the planning size is **ten minutes** now rather than an hour. **n=1000 was
not re-run**, so the only figure for it is the 2,030.8 s above; scaling by the n=2000
ratio puts it near six minutes and nothing has measured that.

The seconds are upper bounds — this machine is usually running something else — so
the **decode counts** are the figure to compare; they are off each record's own
counters and they predict the walls at all three sizes.

Against the retired program's **1800 s and no answer** at n=1000. The pool cannot
fill a thousand seats under these rules — 653 is what it holds — and the four mode
floors that go short are on the expand hook.

**A gallery at n=2000 is an hour and the swap loop still terminates**, which is worth
knowing before capping one: `--swap-seconds 3600` was set as insurance on that run and
never bound. The planning size is affordable.

**The seed is no longer the whole cost** — at n=2000 it is 947 s of 3,592 — but the
signature still is, at both of its stages. Both were taken on 2026-09-01; see *The twin
metric's two costs* below, and read this table as the leg **before** them.

### At the planning size the binding constraint is distinctness, not places

**n=2000 is the size the collection is being built toward** (Matt), and `SOLVE_census_n2000`
is the first census taken there. It reverses what the n=1000 record suggested.

**890 of 2,000 seats.** The refusal order inverts between the two sizes, because the cell
allowance is `floor(k * t * n) + 1` and doubles with n while the pool does not:

| rule | n=1000 rows | n=2000 rows | n=2000 distinct locations |
|---|---|---|---|
| `twin` | 3,275 | **4,090** | **2,785** |
| `cell_allowance` | **4,120** | 2,845 | 2,082 |
| `location` | 1,228 | 1,817 | **663** |
| `group_cap`, `family_allowance` | 0 | 0 | 0 |

**The twin test refuses 2,785 distinct locations against one-per-location's 663.** Places
are not what runs out — 4,791 survive pre-selection for 890 seats — and neither is colour
supply. Among refusals *while choosing* at n=2000 it is twin 6,431 rows against
cell_allowance 1,588. **The palette group cap and the family allowance have never fired at
any size**; the realized group maximum is 6 against a cap of 50.

**The colour ceiling binds at small n and stops binding by n=2000.** At n=150 the allowance
is 7 and **30 of 48 cells sit at it** with pool unseated behind them, which makes the
allowance the limit. At n=2000 the allowance is 84 and only **3 of 48** reach it; the other
45 are held down by the twin test — `dark_muted_azure` has 34 seats of an allowed 84 with
428 unseated places, 4 refused by the allowance and **336 by twin**.

**Read a shortfall against `curate headroom`, not on its own.** At n=2000 the leg's realized
shortfall is 178 seats, but the census proves only **61** of it: `mode_floors` needs 600 and
supplies 539, while `one_per_location` has +2,791 slack and the cell cover +1,880. The other
117 is candidates the pool held and the leg could not seat. **Only two modes are genuinely
empty** — `smooth_mean_angle` and `smooth_angle_min` hold 30 distinct clearing locations each
against a floor of 60 — and closing that provable gap is about **1.3 engine-hours** at the
census's own `seconds_per_win`. The other eight short demands had unseated pool behind them,
so they are a distinctness problem and mining more of the same places makes more twins.

**The census cannot yet price the constraint that binds.** `twin_diversity` reads supply 0 /
slack 0 unless a `--twin` sweep is handed in, so the one block that would bound distinctness
is the opt-in one. At 4,791 places that sweep is the minutes-to-hours leg — an attempt was
stopped unfinished at ~40 min — and everything above says the next census should pay for it.

### The twin metric's two costs, both now taken

Measured in `SOLVE_census_n2000` and taken in `EDIT_twin_metric_directions`. They are
different stages of the same signature and they compose.

**1. The sort runs on the contiguous axis, for a byte-identical answer.** `signature`
used to build `[SAMPLES, DIRECTIONS]` C-contiguous and sort `axis=0`, which is
`DIRECTIONS` independent sorts each striding `SAMPLES` floats apart. It now transposes
into a contiguous copy and sorts the last axis. The sort itself is much cheaper that way
— 8.1 ms against 13.2 ms at 256 directions, 32.2 against 84.9 at 1024 — but the copy
takes most of it back, so **end to end the rearrangement is 1.28x** and not the 1.75x
`SOLVE_census_n2000` projected off the sort alone. The transpose on the way out keeps the
flat form quantile-major, which is what `reduce_signature` reshapes against.

It is byte-identical, checked rather than assumed, because BLAS picks a kernel per shape
and could accumulate three terms in another order: today's code forced back to 1024
directions reproduces signatures captured before the edit over 40 real pictures —
**20,971,520 bytes, 0 differing elements of 5,242,880, `tobytes()` equal**.
`test_the_contiguous_sort_is_the_same_answer_as_the_strided_one` keeps the retired
formulation beside the shipped one and pins it, because a speedup whose output moved
would be a bug wearing a speedup's clothes.

**Why a copy rather than projecting straight into the transposed shape, which is the
trap.** `lattice @ points.T` gives `[DIRECTIONS, SAMPLES]` contiguous and bit-identical
for free, and it went in first. The projection's inner dimension is **3**, so there is
nothing in it to parallelise — and BLAS threads that shape anyway. The whole signature
went to **24.93 ms wall for 185 ms of CPU** against 9.57 ms and 9.38 ms with threads
capped: a spin-wait, 20x the CPU for 2.6x worse wall time, and three times worse again
inside `curation.signatures`' three-worker pool. At 256 directions `points @ lattice.T`
`[4096,256]` is 0.70 ms and threading helps it; `lattice @ points.T` `[256,4096]` is
5.79 ms wall for 56.6 ms of CPU.

**Nothing failed and no test caught it** — the answers were identical either way. It
surfaced as a number that made no sense: the sidecar sweep ran past 600 s where the
1024-direction sweep had been 448 s, on a signature four times cheaper.

**Two measured dead ends.** `numpy.einsum` with `optimize=True` is bit-identical and
looks nearly free, because it returns a **non-contiguous transposed view of the same
BLAS result** — timing it times the view, and sorting it strides again; with
`optimize=False` it is contiguous but its own accumulation is not bit-identical. And
`numpy.partition` to the 256 kth positions the 128 quantiles need is 181-246 ms against
the sort's 116 ms.

**2. The metric has its own direction count, at 256.** [`pixel_clouds.DIRECTIONS`], and
deliberately not `groups.DIRECTIONS`, which stays at 1024 for the palette-group M1
matrix — a different metric over colormap *ramps* rather than pictures, and the one
every stored group name was cut under. The audit behind that split: every non-test
reader of the shared constant was either the twin metric's (`pixel_clouds.lattice`,
`distance`, `distances`, `Clouds.price`, `METRIC`, `rules.reduce_signature`,
`rules.bound_width`, `signatures.shape`) or `groups.m1`'s own default. Nothing else
took it. `QUANTILES`, `SAMPLES` and `HUE_WEIGHT` are still shared.

Project-and-sort scales better than linearly in the count — 117 ms at 1024, 47 at 512,
22 at 256, 9.3 at 128 — because the metric is a Monte Carlo estimate over the lattice
and fewer slices is the same expectation with more variance. Measured over 731 pairs in
the 0.5-1.5x `TAU` band, each setting given its own `groups.directions(count)` call
because a 256-point Fibonacci lattice is not a prefix of a 1024-point one:

| DIRECTIONS | ms | descriptor | p95 error as % of TAU | twin decisions flipped |
|---|---|---|---|---|
| 512 | 32.9 | 256 KiB | 0.3% | **0 of 731** |
| 256 | 14.4 | 128 KiB | 0.8% | **1 of 731** |
| 128 | 7.3 | 64 KiB | 1.5% | 3 of 731 |
| 64 | 3.6 | 32 KiB | 3.0% | 4 of 731 |

Every flipped pair sat within **0.05% of TAU at 256** and 0.41% at 64, flip direction
is balanced, and the `got/reference` ratio is centred on 1.0000 within 0.02% — so it is
noise rather than bias and **a re-fitted `TAU` would buy nothing**. The exposure is
small because the bound removes it: **99.03%** of pairs over a 3,000-row sidecar sample
are settled without measuring, matching the leg's own 99.62% at n=2000, and only 6.1% of
the comparisons a leg must measure sit inside the 256-setting's own noise band. Scaled
onto the n=1000 record's 51,019 measured comparisons that is ~125 to ~1,570 flipped
comparisons depending on the estimator, 0.001-0.013% of the 11.94 M the leg makes.

**The prune stays sound at any count**: the bound is the identity
`|mean a - mean b| <= mean|a - b|` on the same projection vector, so it becomes an exact
bound for the narrower metric rather than an inexact one for the wider.

**`TAU` is not refitted and must not be.** The error is added variance centred on
1.0000, not a shift, so there is nothing for a refit to absorb — and a threshold moved
to chase it would silently change which pairs are twins for reasons that have nothing
to do with the pictures.

### Every signature is now a function of the direction count

This is the part that could fail silently, so it is keyed at every layer that holds one
— four, and the fourth was found by looking rather than by anything breaking. A stale
entry under a fresh key would compare two different metrics and **raise nothing**: both
are flat float32 vectors and the caller only ever takes an absolute difference.

| what holds a metric result | how a stale entry is caught |
|---|---|
| the reduced sidecar, `reduced_signatures.jsonl` | each row carries `blocks` and `directions`; `signatures.by_recipe` and `for_candidates` drop any row not matching `signatures.shape()`. The 11,210 rows swept at 1024 went to **0 accepted** the moment the count moved — a miss, and the picture is decoded as before |
| the direction lattice, `pixel_clouds._LATTICE` | keyed **per count** rather than one module singleton. Nothing in production moves the count inside a process; a test that sets `DIRECTIONS` is exactly the caller a stale singleton would answer wrongly |
| the in-memory cache, `pixel_clouds.Clouds` | the instance records the count it was built at and **drops everything** if it moves, held seats included. A miss costs a decode; a hit would cost a wrong answer |
| **`twins.json`**, replayed by `curate headroom --twin-from` | it recorded `tau` and not the count, so a sweep taken at 1024 would have been replayed as a twin count in a different metric. It now records `directions`, and `headroom.census` **refuses** a mismatch or an absent one rather than flagging it — there is nothing about a sweep's shape to give the metric away. The two files on disk are refused with a message naming the fix |

**There is no full-signature disk cache** — it was a proposal in the census report, not
something shipped, so there was nothing to invalidate. If one is ever built it needs the
count in its identity for the same reason, and it would now cost 1.4 GiB over the
clearing pool rather than 5.5 GiB.

A gallery's own record carries `diversity.directions` too, because two galleries chosen
at different counts are measured in different metrics and are no more comparable than
two chosen under different diversity rules.

### What was retired, and why

`PROBE_ilp_n1000` measured the exact solve against the thirty-minute bar
production wants: `curate solve run --n 1000 --no-render` was killed at a hard
1800 s having reached **stage 3 of round 1**, so there was no incumbent, no gap, no
seated set and no record. One cutting-plane round did not finish, `ROUNDS` is a
backstop of 60, and the round count grows with `n` (2 at n=20, 18 at n=120).

**The headline was the seed, not branch-and-bound.** 46% of the budget went to
`seed_greedily` before HiGHS ran, and it *failed* — 534 of 1000 seats, 6,282 cuts
— because it called `Pairs.measure([at, *seated])` once per considered candidate
and `measure` walks **every pair** of the list it is handed. O(seats²) per
candidate, cubic overall: invisible at n=150, 828 s at n=1000. Nothing in the
shipped leg may reuse that call shape, and `test_rules.py` guards it.

**Shrinking the model would have bought nothing.** The matrix was 98,457 binaries,
18,249 rows and 533,513 nonzeros *at both n=150 and n=1000* — identical, because
only the bounds moved — and it built in 0.4-0.6 s.

Gone with it: `Program`, `matrices`, `lexicographic`, `relaxation`,
`cutting_plane`, `seed_greedily`, `Pairs`, the elastic solve, the deletion filter,
the shortage list, `curate solve sweep`, `curate solve truncate`, and the SciPy
dependency. What stayed is everything that was never the ILP: the pool, the
per-mode bars, the ceiling, the release leg, the contact sheet, and the
`reduce_signature` bound below.

### The pairwise rule is now one rule and it is a count

Two divergences were merged rather than carried. The **palette group cap is a
COUNT** — `ceiling.PROPORTIONAL`, `max(1, floor(0.025 n))` seats a map — and the
program's same-group *distance* row is **dropped**, not merged: there is no second
threshold anywhere in the leg, and `tau_group` is deliberately absent from the
record because nothing reads it. The **diversity rule** is the twin test at
`ceiling.TAU`, one neighbour, and it is one replaceable component behind
`within`/`hold`/`drop`/`record`, so a themed gallery can swap in geometry-only
distinctness without touching anything else. The record names the rule and its
threshold, because two galleries chosen under different diversity rules are not
comparable — `rules.rules_for` is what puts the rule that actually ran in the
last slot of the order, so the rejection ledger never names a rule nothing ran.

`rules.Places` is that second implementation and it is a **replacement**, never a
complement: geometric distinctness over `curation.embeddings`' neutral
descriptors at `rules.GEOMETRY_RADIUS` (0.07), no picture opened at all. It reads
one descriptor per **location**, so a place's fifty rows share one — which is the
property a themed leg wants, because the colour is the theme. Its one divergence
from `Twins` is deliberate and written at both sites: a place with no descriptor
is **admitted and counted** rather than refused, the ruling `distinct.preselect`
already made for this store, and it is safe here only because one-per-location
sits above it so an unembedded place still takes at most one seat.

### `--themed <cell>` is the whole themed leg, and it is four things at once

Per `solver_design` §Themed, and they are one decision rather than four flags:

* the **pool** is the rows dominant in the cell — the row's own `colour.cells`
  block and never the carrier table, which is a prior about supply rather than a
  measurement of a picture — at the **relaxed bar**, `P(>=3) >= 0.50` for every
  accepted mode (`headroom.bars(relaxed=True)`). A single-cell pool is q3-grade
  material by measurement: `dark_vivid_green` holds 470 places at the per-mode
  bars against 1,209 at the crossing, `dark_vivid_lime` 266 against 457. At the
  per-mode bars a themed gallery has no pool;
* the **diversity rule** is `rules.Places` rather than the twin test;
* the **palette-group cap** is `ceiling.themed_group_cap` — `ceil(2n/P)`, twice
  the even share across the `P` groups that can field the theme, `P` measured off
  this pool at solve time. `--themed-cap` names a number instead;
* `--target <cell>=1.0` and `--flat-floor`, which the flag sets as **defaults**
  and not as overrides — a themed pass naming its own target or its own floor
  keeps it. Without the target the cell allowance is `floor(K x (1/48) x n) + 1`
  and refuses the theme at nine seats.

Rows outside the cell are recorded `not_dominant_in_the_theme`, which is pool
construction and sits beside `below_its_mode_bar` rather than among the rules:
the row was not refused a seat, it was never eligible for one.

**Why a themed pass needs its own cap, and what P counts.** The main gallery's
`max(1, floor(0.025 n))` is a share of `n` alone. Over a pool holding a few dozen
maps rather than hundreds that is the **binding** rule at every size a themed
gallery would ship at — measured 2026-09-01, `dark_vivid_lime` seated 38 of 50,
90 of 150 and 124 of 200 with the cap refusing 300-435 rows against the diversity
rule's 1-27, and `sum_g min(cap, places g fields)` predicted the whole column.
Matt's ruling is `ceil(2n/P)`: twice the even share, so a good map may take twice
its share and no map may take a gallery.

`P` is **groups fielding three or more distinct PLACES** in the pool
(`ceiling.THEMED_CAP_PLACES`). Places and not rows, because one wallpaper per
location is absolute. The floor is there because `P` is a **denominator**: a group
holding one fluke place can never take more than one seat however high the cap
goes, so counting it prices a capacity that does not exist and tightens the cap on
the groups doing the work. Measured either way on 2026-09-01: lime 39 groups of
which 29 clear the floor, green 65 of which 50. **Nothing is dropped from the
pool** — a sub-floor group still seats, it is only out of the denominator — and
the capacity it is out of the denominator on behalf of is 13 places (lime) and 17
(green), the places no group over the floor reaches at all. So the floor moves
`P` by about a quarter, loosening the cap ~30%, in exchange for pricing at most
13 or 17 seats.

The cap is computed **after** the bar and the pre-selection, over exactly the rows
the leg may seat — which is why `solve` sets `rule.group_cap` there rather than
with the other constants. `ceiling.THEMED` is the rule's name on the record and is
deliberately **not** in `GROUP_CAP_RULES`: it is not a rule a caller names, it is
the rule a themed pass has, and it needs a number no flag carries.

### The q4 bar is a statistic on the record, and the bars are the pool

`solve.Q4_BAR` is **raw `P(>=4)` at 0.50**, the natural rank cutpoint of a CORN
probability and explicitly not a measured crossover — both release heights this
project has fitted are `P(>=3)` and neither transfers to a different cutpoint. It
is a *count on the record* and not the pool rule: what the pool is is
`headroom.bars`, which puts a mode without enough places above `P(>=4)` on
`P(>=3)` instead, so a fallback mode's seats sit below this legitimately.

**What the bar buys, measured.** The `seated_and_head_top` correction sheet put
200 human tiers against it. Over the 150 seats of an `--n 150` gallery the bar
buys **tier ≥3 at 91.3%** and **tier 4 at 30.7%**, and raising it buys nothing on
the fourth cutpoint: tier-4 precision is 0.31 at 0.50 and 0.30 at 0.999, flat the
whole way up, while ≥3 precision climbs 0.913 → 1.000. Read `P(>=4)` as a *third*
-cutpoint screen with a fourth-cutpoint name. The worst-seat tier above is
therefore doing real work — it is the ≥3 floor it protects.

**Where `P(>=4)` is read at all, and where it only orders.** The column **acts as a
bar in exactly one place**: `headroom.clearing`, at `headroom.DEFAULT_BAR` — and
only for the modes that can field twenty-five distinct clearing locations there.
The others clear on `P(>=3) >= 0.50` (`headroom.FALLBACK_BAR`), so more than half
the mode roster never meets a `P(>=4)` bar. `curation.depth.mode_bars` and
`clears_its_bar` read the same rule and re-state nothing.

Everywhere else the column is an **ordering** and never a gate: `solve.pool`
(presence only — a row with no `p_ge4` is refused `no_score`),
`solve.strongest_locations`, `distinct.preselect` (which place represents a
near-cluster, and the walk order), `curation.mine`'s `best_by_location`,
`curation.framing`'s reframe choice. Since 2026-08-28 the leg's own order and its
objective are the **fitted** key rather than this column.

**Every acting bar in the release path is on `P(>=3)`, not `P(>=4)`.**
`selection.entries` builds its rank key from `p_ge3`; `floors.release_bar`,
`floors.gallery_floor` and `curation.rejection` all call `.acts()` on `p_ge3`. The
supply engine's `GOOD_FLOOR` and `GREAT_CUT` are on the **location** head. So the
sentence to carry is: *`P(>=4)` decides who is in the pool for seven modes and
decides the order for nobody any more; nothing at release reads it.*

### The location-level prune does not work, and this is why

The design was to skip pairs whose *places* are far apart on the ground that they
cannot be near-duplicate pictures. Measured over 79,621 cross-location pairs drawn
from the pool's top two thousand: 1,350 of them are closer than 0.07 as pictures,
and the furthest-apart pair of places that makes one sits at cosine 0.583 — past
the 90th percentile of location distance. The metric is over a picture's **colour
cloud** and colour comes from the map rather than from the place, so two unrelated
frames through similar ramps are near-duplicates by construction. A cut at 0.40
would still keep 91% of the pairs and miss 96 real violations. **A correlated proxy
is not a prune.**

**The metric admits a real one**, and it is `rules.BOUND`. It is a mean of absolute
differences over `DIRECTIONS * QUANTILES` numbers, so the triangle inequality
bounds it from below out of a summary of each cloud: group the **quantiles** into
`rules.BOUND_BLOCKS` blocks and, per direction and per block, the mean of `|a - b|`
is at least `|mean a - mean b|`. At one block that is exactly the distance between
the two clouds' **mean colours**; at `QUANTILES` blocks it is the metric itself. A
pair the bound puts at or beyond its threshold *provably* cannot violate, so it is
never measured. Measured over 79,800 pairs from the same population, at the retired
0.07 radius:

| blocks | bytes a signature | settles | survivors per real violation |
|---|---|---|---|
| 1 | 4 KiB | 95.4% | 2.7 |
| 2 | 8 KiB | 97.4% | 1.6 |
| **4 (shipped)** | **4 KiB** | **97.9%** | **1.2** |
| 16 | 64 KiB | 98.3% | 1.0 |
| 128 (the metric) | 128 KiB | 100% | 1.0 |

**The grouping axis is the quantiles and not the directions**, and both are sound
partitions — the bound holds either way. Grouping across directions averages a
hundred unrelated projections at one quantile and settles far less, and the table
above is the band grouping's. `test_pool.py` pins the one-block reading against the
mean colours, which is what makes the axis observable rather than a comment.

### `--target <cell>=<fraction>` is a share of the realized seats

One spelling, always. The retired program had two — a hard `ceil(t * n)` while
cardinality was `== n`, and a share of what got filled once it was `<= n` — and the
hard one was wrong in exactly the case a target is set for: it demands a share of
seats nobody is promising to fill, so an under-filled answer reported nothing at
all. This leg never promises `n`, so the demand is `ceil(t * seats filled)`, it is
seated from its own subpool by the scarcity leg beside the mode floors, and it
counts in the third objective tier.

It also raises that cell's and its family's ceiling allowance through
`ceiling.Rule` — otherwise a demand would be refused by the ceiling it asked for.

**And it raises the allowance of the cells it structurally implies.** A carrier of
one colour is dominant in more than one: on the reference fields a
`dark_vivid_lime` delivery lands `dark_muted_lime` 42% of the time,
`light_muted_lime` 34% and `dark_vivid_green` 8%. So a target that raised only its
own cell pushes its own seats against its companions' untargeted allowance of
three, and the demand is unmeetable for a reason nobody chose — which is exactly
where the lime hunt's shortage moved once the target itself was met. `ceiling.Rule`
raises a companion's share by `target x the measured co-dominance rate`, and the
companion's family by the same unless it is the target's own family (which the
target already raised, and which counts a picture once however many of its cells
that picture is dominant in). The rates come from `palettes.carriers.co_dominance`
over the tracked table's own deliveries, never from an adjacency written down off
the hue wheel. `config.ceiling.implied` says what moved.

### The expand hook is a stub, and its shape is the contract

`solve.expand` emits, per demand that went short, the strata that could have fed
it — what each held in the view, how many it seated, and which rules acted on the
rows it did not. That last column is the instruction: a stratum whose refusals are
all `cell_allowance` is one the gallery is already full of and mining it buys
nothing, while one whose refusals are all `location` exists only at places
something else already took. **Nothing reads it and nothing is wired to mining.**
When a mining leg does, the contract is this shape.

### The rejection ledger is taken against the finished gallery

For every candidate not seated, which rule killed it, aggregated by cell, family,
mode and partition, and over distinct **locations** as well as rows. The four
counted rules are dictionary lookups, so every clearing candidate is asked *after*
the leg finishes — against the gallery that was actually chosen, rather than
against the moving state the seed happened to test each row under, which is all
the sequential leg could do. The diversity rule is a signature apiece, so only the
rows it acted on carry its answer and no row is opened for the first time here.

Four names sit outside `rules.RULES` and are kept apart from it deliberately:
`the_leg_had_no_seat_left` (broke no rule and simply lost),
`the_view_did_not_reach_it` (**this pass's own budget**, and never a fact about the
wallpaper), `below_its_mode_bar` (never entered the population) and
`another_place_is_the_same_place` (the neutral pre-selection, at pool
construction). A mine aimed at any of the four would be aimed at nothing.

## `curate headroom` — the upper bound the gallery leg is measured against

The leg above is minutes and it is the wrong instrument for one question. Before
another leg spends hours making candidates, somebody has to know **which selection
constraints the pool cannot satisfy and how much each shortfall costs to buy**, and a
twenty-minute solve that reports "there are no light greens at all" spent twenty
minutes on a fact one pass over the rows already knew.

So the pair. `curate headroom` is O(rows) necessary conditions and no solver: the
**upper bound**. `curate solve` is what actually fills them: the **lower
bound**. Close together, the answer is known and the money goes on making candidates.
Far apart, the gap is what exact optimization is competing for.

```
src/fractal_wallpapers/curation/headroom.py   the census, the bars, the marginal cost
src/fractal_wallpapers/curation/distinct.py   the neutral pre-selection, and its premise
```

**Counts are distinct locations and never rows.** One wallpaper per location is
absolute, so a cell fifty recipes carry at one place is a cell a gallery can seat
exactly once. Every supply figure in both modules is a count of `location.key`.

### The bars, and why they are per mode

A candidate is supply only if it is worth seating. The default is `solve.Q4_BAR` on
raw `P(>=4)` — 0.50, the same bar the gallery record counts its seats against.
Six of the **fourteen** modes `mode_policy` accepts have fewer than twenty-five
distinct locations clearing that, so those fall back to `P(>=3) >= 0.50` and the
table **says which rule each mode landed on**: a mode censused under a lower bar is
not comparable to one censused under the default. The roster is `accepted()` and not
the engine's nineteen — a weight-0 mode has no row in the pool to bar. The reading
was taken on 2026-08-30 over the same fourteen: `tail_itinerary` was briefly a
fifteenth and was never in it, and it is weight 0 as of 2026-08-31, so the roster
the reading was taken over is the roster again.
Which mode is on which bar is the last column of the capability table under
`mode_policy` below, and is not restated here.

Both bars are flags on the arithmetic. Neither is a measured crossover, and the one
ACTING release bar — `P(>=3) >= 0.770` on strange_render — is *above* the fallback.
Nothing here re-scores at shipping geometry.

**Read on 2026-08-27 over 85,078 candidates at 4,956 places**, before `mode_policy`
existed and over all eighteen: seven modes on the default (`smooth`,
`exp_smoothing`, `tia`, `stripe`, `smooth_stripe`, `threads`, `itinerary`), eleven
on the fallback, and **four of those eleven the fallback does not rescue** —
`trap_circle` at 2 distinct places, `gaussian_int` at 18, `direct_trap_ring` at 20,
`smooth_trap_circle` at 23. 5,924 candidates over 1,427 places clear. Those four
became the standing mine instruction and are exactly the four `MODE_POLICY` now
weights 0.

⚠ **Do not quote "eleven on the fallback" as current.** That count was taken over
eighteen modes; the bar is now asked only of `accepted()`, and the four unrescued
modes are weight-0 and have no row in the pool to bar at all. The reading on
2026-08-30 is **eight on the default, six on the fallback, four with no bar** — the
last column of the capability table under `mode_policy` below. `tail_itinerary` is
a fifth with no bar and was never read: it arrived after that reading and was ruled
weight 0 before it had a candidate in the pool.

### The census is a covering condition, stated in one direction

A cap can never be infeasible on its own — nothing forces a gallery to use it. What
*is* a necessary condition is that the caps between them can hold `n` seats:

```text
n <= sum over the axis of min(its allowance, its distinct locations)
     + the locations dominant in nothing on the axis
```

A location dominant in three cells is counted in all three, so the sum is an
**over-count** and the condition is necessary and never sufficient. That is the
direction that makes it safe: a short row is provable infeasibility, and a row with
slack is not a claim that the selection is possible.

### The mode-floor block bounds the floors the legs actually take

`mode_policy.seat_floors(n)` — per mode, the section further down — is what an
unflagged `curate solve run` is floored by, so an
unflagged census bounds those and not something else. It bounded the flat
`floor(n / 100)` until 2026-08-31, which read a demand of **zero at `n = 20` where
the shipped seating asks for six**, and a census whose floor block is a different
rule from the seating's is a misread waiting to happen rather than a second opinion.

The arithmetic is per mode on both sides: each mode is asked for **its own** floor
in distinct locations, so the supply the demand is read against is

```text
sum over accepted modes of min(that mode's floor, its distinct clearing locations)
```

which is not the count of modes holding anything — those two agree only while every
floor is one, and under this rule the thirteen strange floors are not one number.
`smooth` is floored at zero by construction (the rule concerns the strange side), so
a pool of nothing but `smooth` reads supply 0 against a demand of 45 at `n = 150`.

`curate headroom --flat-floor` puts the flat floor back at every rung — it is a
function of `n` and a census walks a ladder, so it is a flag rather than a number —
and that is the baseline a floored-against-flat reading is taken against. The block
says which of the three it ran under in `floor_rule`, the same sentence
`config.mode_floor_rule` carries in a seating and a solve record, written by
`solve.floor_rule` and called from the census rather than copied into it. The
per-mode mapping is on `floors`; `floor` is the flat number when one was asked for
and `None` otherwise, exactly as `mode_floor` reads in a gallery record.

The floors sum to half the strange seat budget by construction, `ceil(0.3n)` and
never more, so this block can never ask for a gallery that will not fit. The flat
floor of **one** that both replaced could and did: eighteen of twenty seats at
`n = 20`, which is the `trap_circle` incident recorded below.

**Census schema 3.** A schema 2 census bounds the flat floor and is not a
comparable reading of the same pool.

#### What the flip found, measured 2026-08-31

One pool — 97,423 candidates, 11,137 clearing, 4,480 places after the neutral
pre-selection — censused both ways (`floor_default` beside `floor_flat`).

| n | floors ask | supply | short? | the flat floor asked |
|---:|---:|---:|:---|---:|
| 20 | 6 across 6 modes | 6 | no, slack 0 | 0 |
| 150 | 45 across 13 | 45 | no, slack 0 | 14 |
| 500 | 150 across 13 | 150 | no, slack 0 | 70 |
| 1000 | 300 across 13 | 296 | **short by 4** | 140 |

**At `n = 1000` the pool is provably short on the mode floors, and the flat reading
said nothing.** `smooth_mean_angle` holds 27 of the 30 it is asked for and
`smooth_angle_min` 29 of 30. It is a cheap mine instruction: 53.6 and 40.0 seconds
per win on those two modes, so the four places are about 201 render-seconds, ~67 s
of wall clock over the three-worker pool. The estimator is the unconditioned
ledger-wide rate and an aimed leg beats it.

`palette_group_cap` used to be short beside it there and **was not really short at
all** — see the note under the group cap below.

**The slack is exactly zero at every rung below that**, which is the shape to
notice rather than the comfort: supply meets the demand and never exceeds it,
because a mode's contribution is capped at its own floor by construction. One place
lost at any floored mode makes the block short. It is the tightest block in the
census.

### The group cap was a second spelling, and the census was the one that was wrong

Until 2026-08-31 the `palette_group_cap` block priced against `ceiling.GROUP_CAP` —
a flat **one seat a group**, the retired `curate seat` leg's cap — while the leg
that actually runs takes `ceiling.group_cap(n, solve.DEFAULT_GROUP_CAP)`, the
proportional `max(1, floor(0.025 n))`. At `n = 1000` that is 1 against **25**. The
census read 754 groups at one seat each, called the pool short by 246, and it was
the loudest short block in the record; the shipped leg at the same rung found **no
ceiling binding at all** and a realized maximum of **7** seats in any one group.
The block was not a tight bound on the rule — it was a different rule.

It is fixed by asking `ceiling` rather than spelling the cap again, the block now
carries `cap` and `cap_rule`, and the census is **schema 4**: a schema 3 reading of
this block is not comparable. The note it used to carry — that the count was the
`TIGHT form` and the pixels could exempt a second seat within `TAU_GROUP` — went
with it, because `curation.rules` **dropped** that same-group distance row rather
than merging it. The count is the whole cap and there is no second threshold.

**Why the census survived the question at all.** The gallery leg's own expand hook
reports a per-constraint shortfall, so the obvious move was to retire the census as
a second spelling of the rules. It does not cover it: `solve.expand` walks
`gallery.demands`, which is the mode floors and any colour target, and it runs
*after* a leg. It has no `one_per_location`, no cell or family ceiling, no group
cap, no twin bound, and no renders-per-win — and it cannot answer anything at a
rung nobody has solved, which is the census's whole job. The two are the upper and
lower bound of the same pair, and the fix was to make them agree rather than to
delete one.

### What one more costs

Slack alone is not a work order, because headroom is not equally purchasable. Every
row carries

```text
renders per win = renders on record / distinct clearing locations satisfying it
seconds per win = that x the median realized `hunt.seconds` of the modes that won
```

which is the **unconditioned** rate — what this project's whole render history
happened to produce, not what an aimed leg gets. Wall clock is a third of it: the
render pool is three workers. The realized per-mode render cost is on the ledger row
(`hunt.seconds`, 69,767 of the 85,129 rows carry one), and the median is used rather
than the mean because every mode's p90 is two to five times its median.

**There are aimed rows in that denominator now, and nothing filters them out.**
`_row` divides by every candidate on record without asking how any of them was
drawn, and since 2026-08-28 the ledger carries a conditioned arm: 3,042 rows drawn
*for* `light_vivid_teal`, merged beside their own 3,041-row flat control. So a
census taken after that date reports an unconditioned rate on every cell except the
one an arm aimed at, and on that one it reports an aimed leg's rate under the
estimator's name. The separator is **`hunt.drawn_for`**, and it is exact: it is
present on the aimed row alone and absent on every other row in the store — the
control arm's included, which is what makes the control still readable as base
rate. Drop those rows *before* the census to read the true rate; there is no
correction to apply afterwards, because the aimed rows move the numerator and the
denominator by different factors. The same caveat rides on `depth.mode_bars`'
`ledger_clear_rate`, which is the base rate the next arm's clear rate will be
quoted against.

### The greedy fills by scarcity, not by score

Ordering by score alone converts satisfiable problems into apparent infeasibility.
Wherever the mode floors ask for most of the gallery — as the flat one-per-mode did at
`n = 20`, eighteen of twenty seats — a ranked walk seats five `smooth` and reports
fifteen modes it could have held. Every one of them could have been seated.

So the mandated constraints are seated from their own subpools first, **scarcest
first**, and only what is left over is drawn by score. Two rules are hard — one
wallpaper per location, and the twin test; the cell and family allowances, the mode
floors and the group cap are soft with the shortfall recorded. No fallback leg, no
least-violating rescue: unfilled beats padded.

**The scarcity leg keeps seating a mode until its floor is met.** It used not to:
it visited each mode once and `break`ed on the first candidate nothing refused, so a
floor above 1 was recorded as `unmet` and never acted on by this walk. Measured
2026-08-29, `curate seat --n 150 --mode-floor 2` (as it then was) returned a **bit-identical** gallery
to `--mode-floor 1` — 0 seats different, the same 13 mode counts, `cell_allowance`
4,570 either way — while `solve` carried the floor properly as
`sum(x in m) + d_m >= floor_m` with a penalty. Fixed 2026-08-30: the inner walk stops
on the floor or on a spent subpool, never on its own first success.

The two solvers agree at a floor of 2 wherever the floor is **free**, which is the
limit of what an agreement between them can mean. The exact solver's mode floor is
soft and third in a lexicographic objective, so a floor that would cost a point of the
worst seated score is a floor it declines to fill; the greedy fills one
unconditionally. `test_the_greedy_and_the_exact_solver_seat_the_same_rows_at_a_floor_of_two`
is the pin, and it is built so the floor costs nothing.

### Both gallery decisions flipped on 2026-08-28, and the incumbent is still reachable

Built at ckpt 88 behind flags; **both are the default since 2026-08-28**. The cap is
the ckpt-88 ruling, the key is Matt's acceptance by eye on the four-arm contact sheets
at `n = 150`. `curate solve run` with no flag now seats the proportional cap on the fitted
key; the walk every earlier gallery took is two named flags away and the record says
which rule and which key it ran under, by name, either way.

```
curate solve run --n 150                                    proportional + rank-key
curate solve run --n 150 --group-cap identity --key p_ge4   the incumbent, whole
curate solve run --n 150 --group-cap {identity,proportional}   the palette-group cap
curate solve run --n 150 --key {rank-key,p_ge4}             the sort key
curate solve run --n 150 --sheet-out <path>                 the contact sheet, elsewhere
curate solve run --n 150 [--release-regime WxHssN] [--workers 3]
```

`solve.DEFAULT_KEY` and `solve.DEFAULT_GROUP_CAP` are the two constants, and
`solve.ranking_for` is the one place a pass pays for its key — it reads the
flatness sidecar and the location scores, once per pool. `seat(order=...)` overrides
it, which is what a sweep seating one pool four ways passes.

**The flag is the seating's, and `curate solve` has no equivalent.** There the cap is a
*generated pairwise row* and never a counted one: `solve.Pairs.rule_for` asks a same-group
pair for `max(TAU, TAU_GROUP) = 0.10` and every other pair for `TAU`. The solve record
used to carry a `group_cap` field describing one seat per palette group, which no block
ever wrote — it is now `pairwise_rule` and states the row that actually runs, and
`tests/test_solve.py` holds every `ceiling.Rule` field named on that record to being one
`solve.py` genuinely reads. So there is no cap to name, raise or switch off in a solve — the only way to run one without
it is to make `rule_for` return the diversity rule for every pair, which is a code change
and not a flag. Neither is there any way to turn the cap **off** in the seating: both rules
go through `max(1, ...)`, so the lowest either reaches is one seat a group. A caller inside
the process can pass `seat(rule=ceiling.Rule(group_cap=...))` with any integer, and that is
the whole of the raise-past-binding lever.

**`--group-cap proportional` is `max(1, floor(0.025 n))`** — 1 up to n=40, 3 at n=150,
25 at n=1000 — against `ceiling.GROUP_CAP = 1`, the identity cap. The `max(1, ...)` is
not a rounding convenience: `floor(0.025 n)` is zero below forty seats and a cap of
zero is a program with no seats in it, **so a debug gallery at n=20 keeps the identity
cap under either rule and a before/after has to be taken at n=150 or above.** The cap
of 1 was a quality mechanism as well as a ceiling — it forced an n-seat gallery onto n
distinct maps and pushed the seating down the map-quality tail by construction — so
the realized maximum per map is a number the record now **reports** rather than
assumes: `shortfalls.groups.realized_max` and `at_the_cap` beside the cap itself.

**`--key rank-key` moves the ORDER and nothing else.** Every bar on the path stays on
the judge's own columns — `headroom.bars` chooses a mode's rule on `p_ge4`,
`headroom.clearing` applies it, and the neutral pre-selection is about places — so two
seatings differing in this flag differ in the sort order and in no other thing, which
is what makes a before/after exact. A candidate the key cannot read is sorted **last**
and counted under `order.unranked`; that is not one of the *rules* refusing it,
because no rule acted on it — but the seating as a whole now refuses rather than
quietly sorting it to the bottom (below).

The contact sheet is sorted **good to bad by the seating's own key** and captioned with
it. A sheet in seating order is in *scarcity* order for its first seats, which reads as
a quality claim it is not making. Where the release leg has run it shows the **released**
picture and says so on the card; the candidate render is 640x360 ss2 through the
unmodified map and the release render is shipping geometry with the autolevel operator
inside it, so showing one under the other's caption would say something false with every
field on the card true.

### The release leg — the seats at shipping geometry, and no bar anywhere in it

`solve.render_seats` with the seating's own directory, so the geometry, the autolevel
stamp and the resume rule live in one place rather than two. Pictures and
`autolevel_stamps.jsonl` land in `artifacts/curation/seat/<name>/release/`, each seat
gains `release_picture`, `release_geometry` and `release_autolevel`, and the record is
rewritten after the leg.

* **Regime is `release.RELEASE_REGIME`, 1280x720 ss2**, moved by `--release-regime`.
  Full wallpaper resolution is not this.
* **Three workers**, `release.DEFAULT_WORKERS`, each below-normal with its engine in a
  job object. Not four: `render_seats` carried a literal 4 at its signature until
  2026-08-28, which is one more engine than this desktop survives.
* **No clock.** There is no `pacing.Leg`, no gate and no budget knob: every planned row
  is started and the leg runs to completion. What bounds it is `solve.ROW_BACKSTOP`,
  900 s stamped on each task so the *worker* imposes it — the hang detector, and a row
  that reaches it comes back failed and named while the leg carries on.
* **No bar, and no re-score.** Every seat the walk chose is rendered and every render
  that succeeds is released. See below.

**Measured, on the 150 seats of `g1_n150` at 1280x720 ss2 on 3 workers, 2026-08-28.**
150 cold rows, 0 failed, 0 killed, 0 not started: **566 s of wall, 3.8 s a row**, against
1,348 s of CPU and 8.99 s a row — a **2.38x** concurrency gain, which is gallery4's 2.39x
on the same regime to two places. Per row the CPU spread is min 1.61, q1 3.75, median 6.22,
q3 10.19, p90 21.28, max 52.03 s. 233 MB of PNG for 150 pictures. Estimating a leg off the
gallery pass's own 3.45 s a row over-priced this one by 9%; both numbers are wall on three
workers and both are the right shape to size the next leg with. The autolevel operator
**acted on 60 of the 144 seats it was asked about (41.7%)**; the six it was never asked
about are the four `direct_trap_*` seats and the two `itinerary` seats, whose kinds
`autolevel.applies_to` answers no for.

**Releasing only the seats that changed is a copy, not a flag.** `solve._already`
carries a picture across when `<seat key>.png` is on disk in the leg's own `release/`
at the regime's resolution, so the way to re-seat and pay for the delta alone is:
seat once with `--no-sheet` to learn the delta, copy the unchanged seats' PNGs — and
their lines of `autolevel_stamps.jsonl`, which is where `render_seats` reads a reused
seat's stamp back from — into the new seating's `release/`, then seat again with
`--release`. Measured re-seating `g1_n150` as `g2_n150` after `mine1h`: **23 rendered,
127 reused, 53.4 s of render and 110 s for the whole pass**, against 566 s for the
same 150 cold. Seat keys are recipe keys, so an unchanged seat's file name is
unchanged by construction and nothing has to be matched up by hand.

#### No floor is read at shipping geometry, anywhere in this project

Worth writing down because it is easy to assume otherwise. The rule *select on the
candidate score, then re-score the shortlist at shipping geometry and let that be the
floor* is **not implemented**, in this path or in any other, and the two release legs
say so in their own docstrings: `solve.render_seats` and its caller both
refuse to re-score, on the reasoning that the heads' floors were fitted on 640x360
candidate renders and a height read at one geometry does not transfer to another.

What acts instead, and all of it on the **candidate** column:

| where | cut | column |
|---|---|---|
| `headroom.clearing`, pool construction | `solve.Q4_BAR` = `floors.RELEASE_ADVISORY` = 0.50 | the candidate's `P(>=4)` |
| the same, for a mode with fewer than `FALLBACK_LOCATIONS`=25 clearing places | `floors.RELEASE_ADVISORY` = 0.50 | the candidate's `P(>=3)` |
| `selection.py` (a run) | `floors.STRANGE_RELEASE_BAR` = 0.770, strange only | the candidate's `P(>=3)` |

The third does not act on the `curate solve` path at all — the leg's only bar is the
first two. `headroom.bars` already carries this on its own record under `provisional`,
and that block is the honest statement of the position: the bars here are
candidate-column bars, nothing re-scores at shipping geometry, and no crossover fitted
at label geometry is transported onto this column. **Moving that is a ruling, not a
fix**, and nothing in the release leg should improvise one.

### The leg attribution on the record, which is the mining list

Schema 3. Every seat carries **`rank_percentile`** — its own rank value against the
whole clearing pool, before the neutral pre-selection — and **`leg`**, which of the two
legs placed it. There are exactly two and they are spelled as the walk spells them:
`mode_floor` (the scarcity leg, each mandated mode from its own subpool, scarcest first)
and `general_pool` (the ranked walk). There is no `cell fill` leg; the cell allowance is
a ceiling applied *inside* the ranked walk and never a stage that places a seat.

`attribution` then aggregates three things a mine can be aimed with:

* **`bottom_quartile`** — the weakest quarter of the *seats* by percentile, tallied by
  leg, by mode and by cell.
* **`best_available`** — per mode and per cell, how strong the pool's **best** candidate
  was, weakest first. This is the "go and make more of this" list.
* **`unmet`** against **`binding`**, and they are opposite instructions. Only seats and
  mode floors can go *unmet*; an allowance and a cap are ceilings, which a seating binds
  against and cannot fall short of. A cell at its allowance is a cell the gallery is
  already as full of as the rule permits, and aiming a mine there buys nothing; a cell
  whose `best_available` row is weak is the one to aim at.

A candidate the key could not read sorts last in the walk, and it counts at the
**bottom** of every percentile here for the same reason — anything else would inflate
every percentile by the size of the hole.

### `curate flatness` — the dead-space column, in a sidecar beside the scores

```
curate flatness sweep [--workers 3] [--all] [--recompute]
curate flatness coverage
curate flatness {save,check,restore}
```

Tile each picture into 16-pixel cells, fit `z = a x + b y + c` to every cell by least
squares, and count the cells whose residual RMS is under 1.0 on the 0-255 luminance
scale. **The plane term is the whole of it**: a smooth ramp across a cell is not
detail, and a variance screen would score that cell as the busiest thing in the pool.

`flat16_1.0`, and the constants are not a knob — the cell size and the threshold were
chosen by a nested selection that never saw the fold it scored, unanimously across all
five outer folds, out of two cell sizes and three thresholds. It ranks **backwards** on
its own (AUC 0.407 smooth / 0.480 strange: more dead space is a worse picture) and
earns its place on top of the judge on both kinds, which is why it is a column of the
rank key and never a bar.

One row per recipe key in `flatness.jsonl`, beside `scores.jsonl` in the ledger, with
its own manifest under `data/curation/candidate_ledger/`. **No ledger row is edited.**
It was regenerable from the pictures until the pictures started being swept, which is
why it was made durable on 2026-08-29 before anything else touched it.

**`candidate_ledger.merge` records it, along with the rows and the scores.** Until
2026-08-30 the door saved two of the store's three files and the sidecar's manifest
was current only because somebody had run `curate flatness save` by hand — a writer
that has to remember, which is the exact shape the two other manifests went stale in.
The save is conditional where theirs are not, because `durability.save` refuses a
file that is not there; in practice `prune` rewrites all three, so the sidecar exists
by the time the save reaches it and a merge that swept nothing records zero rows.

**What this does not buy:** `curate candidate-ledger check` still reads the rows and
the scores alone, so a short or missing sidecar is *not* what makes that command exit
1 — `curate flatness check` is a separate call with its own exit code. Extending the
one to cover the other is a decision about what counts as a build failure and has not
been taken.

The sweep is about 7.5 ms a picture and incremental: a store already swept costs one
read of the sidecar and no decodes at all. `--all` sweeps every ledger row
whose picture is on disk rather than the pool — the pool excludes a row a person
rejected and a row off the candidate regime, and the rank key has to be *fitted* on
some of those.

**A merged leg is invisible to a rank-key seating until this has been swept.** The
sidecar is keyed on the recipe, so every candidate a hunt, a mine or a depth run
merges arrives without a reading — and `rank_key` needs the column, so those rows
come back **unranked**, which the walk sorts *last* and never refuses. They are in
the pool, they clear their bars, they are counted in the clearing population, and
none of them can win a seat while a ranked row is left. `mine1h` merged 8,192 rows
and seated **none** of them: the record said `unranked: 8192, no_flatness: 8192` and
1,326 of the 7,353 clearing candidates were `unreadable_by_the_key`. A sweep
afterwards cost **33.3 s** for those 8,192 pictures and the same seating then moved
23 seats. So the order is `merge` → `flatness sweep` → `seat`, and the two places
that say whether it was done are `order.coverage.no_flatness` on the seat record and
`curate flatness coverage`.

**And a seating on a key it cannot read now REFUSES, which is the whole reason to
know the order.** `solve.solve` raises `SolveRefused` when any clearing candidate
carries no value for the active key, naming the count, the first few keys and the
sweep command that fills the gap. The argument is in the message: such a row sorts
last and cannot win a seat while a readable one is left, so a seating that let it
through would be **silently ignoring** it rather than deciding about it — and
`mine1h` is what that looks like, 1,326 clearing candidates and no line of output
saying they had no chance. The refusal is not a bar and is not on the judge's
columns; it fires before the walk and the pool is unchanged by it. `--allow-unranked`
is the way past, and it is for exactly one case: a picture that is on disk and will
not decode has no reading and never will, so a pool holding one would otherwise be
unseatable forever. It is not the flag for *the sweep has not been run* — there the
refusal is doing its job. Allowed through, the rows are logged and counted under
`order.unranked` / `unranked_allowed`, and `unreadable_by_the_key` on the record is
how many of the clearing population they were.

### `curate rank-key` — what the gallery leg ranks on instead of the judge alone

```
curate rank-key fit     re-fit and rewrite both tracked files
curate rank-key show    print the shipped one
```

```text
sigmoid( b0 + b1 loc_p_ge4 + b2 p_ge3 + b3 p_ge4 + b4 stratum + b5 flat16_1.0 )
```

the location head's `P(>=4)` for the place, the render judge at **both** cutpoints, the
calibration stratum (`composite` 2 / `other` 1 / `thin_colour` 0) and the flatness
column, each standardized by the fit's own constants.

Fitted on 2026-08-28 over the **1,051** label rows that join the ledger (342 smooth /
709 strange, 625 lineage groups, tier mix 1.2 / 31.1 / 41.7 / 26.0%), it reads out of
fold **0.779 smooth against the incumbent's 0.671** and **0.850 strange against
0.826**. Those are the shared-weight figures; `rank_key_fit`'s headline 0.797 / 0.852
is the *per-kind* arm with a nested inner selection and is not what ships.

**Shared weights over both stores**, and per-kind is unresolved on every arm tried. On
this five-column form specifically it is `+0.018 [-.002,+.039]` on smooth and
`+0.005 [-.005,+.014]` on strange — the `+0.000 [-.011,+.012]` the ruling cites is the
*three-column base* arm. Shared is also the only fit the folds support, since 96 of the
625 lineage groups span both stores and carry 348 of the rows.

Two cutpoints and not an expected tier: `1 + p2 + p3 + p4` as a single column **loses**
(`-0.030*` on strange), and the fit weights `p_ge3` above `p_ge4` on smooth, which an
expected tier cannot express. No colormap identity, no palette group and no label
history aggregated by map — a key reading a map's own human history would be a
selection rule fit on the thing it selects. Nothing derived from `hunt.seconds` either:
it is on 44% of rows, and a form that has to score the whole ledger cannot carry a
column most of the ledger does not have.

It ships **two** tracked files under `data/curation/rank_key/`:

```
rank_key.json      the coefficients, the standardization constants, the population
population.jsonl   EVERY label row the fit consumed
```

The second is the point. A selection rule fit on human labels is a category no
eligibility guard covers — the eligibility rule is about judge *training* — so the
record is the guard: per row the store, the batch, the source file and line, the recipe
key, the tier, the lineage group and the fold it landed in. It costs nothing now and
would be expensive to reconstruct later.

### The mode floors are per mode, and they are the default

**`mode_policy.seat_floors(n)` is what a seating and a solve take by naming nothing**,
since 2026-08-31. Each accepted strange mode is floored at half its share of the
strange seat budget, weighted `2 * promoted + 1 * normal`, so the floors sum to half
that budget by construction and the other half is the gallery's to spend on whatever
is strongest. The rule is in `mode_policy` and the section under it is where it is
derived and measured.

`solve.mode_floor(n)` — `floor(n / 100)`, 0 at 20 seats, 1 at 150, 10 at 1000 — is now
the **flat** floor rather than the default, and `curate solve run --flat-floor` /
`curate solve run --flat-floor` is what asks for it. It is what every gallery seated
before that date was seated under, which makes it the baseline a floored-against-flat
reading is taken against. `curate solve run --mode-floor N` still puts an artificial flat
floor of `N` back. The record names which of the three it ran under, in
`config.mode_floor_rule` — and so does the census, in its `mode_floors` block's
`floor_rule`, off the same `solve.floor_rule`. The census is floored by this rule
too, since 2026-08-31; `curate headroom --flat-floor` is its way off.

Two older readings, both still worth the line they take. The flat floor `mode_floor`
replaced was **one per mode**, which spent eighteen of a twenty-seat gallery on
representation and forced `trap_circle` — 2 clearing places, the better at
`P(>=4) = 0.066` — into every gallery this project would ever seat. And measured on
2026-08-27, the same twenty seats under those two: at floor 0 the gallery is `smooth`
14, `exp_smoothing` 4, `smooth_trap_circle` 1, `smooth_curvature` 1 — **4 modes**; at
an artificial floor of 1 it is 18 modes, one seat each but for `smooth` at 3.

### The twin test is the diversity rule, and it is the last one

`ceiling.TAU = 0.0586` in the pixel-cloud metric, against every already-seated
picture, sequentially. It is **not** in the solve and the solve's complexity does not
change: a rule that reads the seats already taken costs one signature per surviving
candidate, where a solver carries it as a quadratic family of rows.

It runs last of the five because it is the only one that opens a picture. Every
candidate the four counting rules refuse is a signature not made, and each comparison
against a seat is screened by `solve.BOUND` — the same sound lower bound the cutting
plane uses — so a seat the bound puts at or beyond tau is never measured.

**`solve.RADIUS` (0.07) is retired.** Two spellings of one fact is a silent null:
both were answering "do these two read as one wallpaper", so a pair one refused and
the other passed was a disagreement between two numbers nobody had chosen between.
Every reader now reads `ceiling.TAU`, which is the one somebody set by eye. Note that
the seating and the solve refuse on the **first** neighbour inside tau, where the
shipped seating refuses on the second (`ceiling.TWINS = 2`); the two
are different policies and both records say which they applied.

**A quarter of the ledger has no picture, and both readers of one now fail closed.**
While the picture rule ran on its own ranking at its own K, the store dropped the
picture of everything outside the top five per (location, mode) and kept the row — so
**30,040 of
the ledger's 128,368 rows (23.4%) name a JPEG that is not there**, permanently and by
design. No reader had been checked against that. `solve.pool`'s `no_picture` exclusion
tested that a row *named* a picture and never that the file existed, so it admitted all
of them; they then reached the twin rule, which reads pixels and **admitted** what it
could not read, on the reasoning that a missing file is a fact about the checkout
rather than about the wallpaper. True, and the wrong direction to fail in: the
diversity rule stopped applying to exactly the candidates nothing could check.

It is visible in a replay. Re-seating `p2b_n150` on the same pool, the same bars, the
same pre-selection and bit-identical scores reproduced **147 of its 150 seats**, and
the three it took instead were three the record had refused as twins whose files had
since gone — seated *because* their pictures were missing.

**Closed on 2026-08-28, in both places.** `solve.pool` excludes a row whose picture is
not on disk and counts it apart as `picture_absent` — drawn-then-swept is a different
fact from never-drawn, and only the first grows. `Twins.refuses` refuses a candidate it
cannot read, under its own rule name `picture_unreadable` rather than as a twin, which
is what the file that vanishes mid-pass needs. Both are pinned by planted-failure
tests. Existence is answered once per pool by `candidate_ledger.present_pictures`, which
shares one `Tiers` snapshot and lists each pictures directory once — 21 directories,
3.6 s over the whole store, against 215 s for a naive `rehome`-and-stat per row.

**What it cost the pool, measured before it was closed:** at the `p2b_n150` pool,
clearing rows fall **5,924 → 4,851** and distinct clearing places **1,427 → 1,427**.
Zero places lost, because retention keeps the top five *per (location, mode)* and every
location therefore keeps its best. No mode goes short of its floor at n=150 or n=1000
on missing files alone. Two colour cells do, and only at n=1000: `dark_vivid_lime`
(46 → 30 places against an allowance of 42) and `dark_vivid_yellow` (45 → 37) — the
thin cells, where this was always going to bite first. Re-rendering the 17 rows that
would restore both is **3.9 core-seconds** at the ledger's own per-mode median. Not
spent; the number is here so the decision is one.

`fractal-wallpapers curate candidate-ledger pictures` is the reader for this state,
counted and grouped by mode and by run.


**The rejection ledger is the product.** For every candidate not seated, the first
rule that refused it, aggregated by cell, family, mode and partition — a cell whose
whole refusal column is `cell_allowance` is a cell the gallery is already full of,
and one whose column is `location` exists only at places something else already took.
Those are not the same instruction. A greedy shortfall is "this walk did not find
it" and never "the pool does not hold it"; the census's necessary conditions are the
only infeasibility claims this project makes.

### `curate distinct` — two rules under one word, and where each went

"Diversity" was hiding two questions. *Are these two the same place*, answered by the
neutral descriptors; *do these two read as one wallpaper*, answered by the pixel-cloud
twin test. They are near-orthogonal, so one rule cannot be both, and both are placed:

| question | rule | where it acts |
|---|---|---|
| the same place? | cosine `distinct.PRESELECT_RADIUS = 0.02` over the neutral descriptors | pool construction, before the walk |
| one wallpaper? | `ceiling.TAU = 0.0586` in the pixel cloud | set-level, last rule of `curate solve` |

`RADII` stays a set of candidates to look at, and the sheet — near pairs at each
radius, ordered by distance, as pictures — is the instrument. That is how
`ceiling.TAU`, `ceiling.TAU_GROUP` and the retired pass's draw radius were all set, and every one
of them is recorded with who set it.

The pre-selection is a greedy suppression over **places**, each represented by its
strongest clearing candidate, strongest first; a place inside the radius of a place
already kept is refused and everything that place carries goes with it. A location
with no neutral descriptor is **admitted**, never dropped — a place can be newer than
the last embedding leg, and refusing on that would make the pre-filter a function of
when the store was last built. Measured 2026-08-27 over the 1,427 clearing places:
425 near pairs touch 250 of them (17.5%), and the greedy refuses **139 places, 9.7%**
— the suppression keeps one of each cluster, so the share refused is not the share
touched. In rows that is 600 of 5,924.

The premise the whole decoupling rests on is that far in the neutral descriptor
implies far in the coloured pixels, and it is **measured** rather than assumed: this
project has already shipped one prune whose premise was false, and a correlated proxy
is not a prune. The sample is stratified over a ladder whose low bands are the
candidate radii themselves, because an equal-width ladder over this store's own
spread puts every radius inside the first band and never measures the region a
decision is in.

**It does not hold.** Over the 1,427 places of the clearing pool on 2026-08-27:
Pearson 0.034 and Spearman 0.063 across 1,200 stratified pairs, and the exact sweep
over all 1,017,451 pairs finds **6,720 twin pairs** at a median neutral distance of
0.226 — a pre-filter at 0.10, which already refuses 98% of the pool, removes 413 of
them. So **pairwise diversity does not move to pool construction**, the pixel-cloud
twin test is not demotable to a residual, and a neutral radius is a different rule
answering a different question — which is the one it now answers, on its own terms,
at 0.02. The twin test stays where a pairwise rule about pictures has to be: in the
seating walk.

### `curate headroom --twin` — the one block that opens a picture

Every other block is arithmetic over the ledger. The twin constraint cannot be
answered from a row, so its sweep is **opt-in** and a census taken without it says
the block was not counted. What it reports is a bound on a bound:

```text
n <= (places) - (the size of any matching in the twin graph)
```

necessary, because any set of pairwise non-twin places takes at most one endpoint of
each matched edge. A greedy independent set walked strongest-first is reported beside
it as the **constructive** lower bound. The relation is measured over one picture per
place — that place's strongest clearing candidate — so the upper bound is a necessary
condition for the program restricted to those pictures and a flag rather than a proof
for the unrestricted one. The block says so.

**Where the bound stands, and what a merge does to it.** Over the merged ledger on
2026-08-28: 1,791 places, 10,642 twin pairs, maximal matching 753, **upper bound
1,038**, greedy independent set 532. The sweep costs about ten minutes — a signature
a picture at ~116 ms, then the exact metric on the few thousand pairs the bound cannot
refuse (13,708 of 1,602,945 screened here). Merging `teal_conditioned` moved it
1,013 -> 1,038, so 25 of that merge's 40 new places survived as non-twin. It is the
tightest block that is not provably short: at n=1000 its slack is 38 and
`mode_floors` sits exactly on its needs. (`palette_group_cap` read -240 here under
the flat cap that was corrected on 2026-08-31; under the cap the leg applies it is
not short at that rung.) The greedy
lower bound stays far below 1,000, so a thousand-seat gallery is bounded from above and
unproven from below.

**A pool filtered to one colour is a near-duplicate pool, and this is the block that
says by how much.** Measured 2026-08-31 over the rows dominant in one cell and above
their kind's gallery floor: `dark_vivid_green` 881 places, **35,213 twin pairs of
387,640 screened (9.1%)**, upper bound 460, greedy set 90; `dark_vivid_lime` 339 places,
**8,308 of 57,291 (14.5%)**, upper bound 179, greedy set 45. Against the whole pool's
0.66% that is a 14x to 22x concentration, and the constructive yield falls from 30% of
places to 13%. It is structural rather than a supply shortage: `pixel_clouds.METRIC` is
over a picture's **colour cloud** and colour comes from the map rather than the place, so
selecting on the dominant cell selects for pictures that are near-duplicates of each
other under exactly the rule a gallery uses to refuse duplicates. It is the same argument
the location-level prune above failed on, with the sign flipped. **So a themed gallery
under the twin test is bounded by `TAU` and not by its bar, its cap or its floors** — at
n=200 the ceiling needs `--target <cell>=1.0` to admit the theme at all, and past that no
arm fills. That is the reading `--themed` acts on: it swaps the twin test out.

**And with the twin test out, the binding rule is the palette-group cap.** Measured
2026-09-01 over the two themed pools at the relaxed bar, geometry-only distinctness at
0.07, `--target <cell>=1.0` and `--flat-floor`:

```
                       n=50  100  150  200  300  400  600   pool
dark_vivid_lime  seats   38   66   90  124  154  185  217   476 rows / 424 places / 39 groups
                 cap    435  389  360  300  255  171  101   <- rows the group cap refused
                 geom     1    6   12   27   35   84  119
dark_vivid_green seats   50  100  150  200  289  356  405  1209 rows / 1097 places / 65 groups
                 cap   1095 1009  985  755  735  548  251
                 geom     2   13   25   87  139  246  492
```

`sum_g min(cap, places group g can field)` predicts the lime column to within a few seats
to n=300 — 39, 71, 100, 145, 183 — so **at any size a themed gallery would ship at, more
pictures through the same maps buy nothing**; new palette groups dominant in the cell do.
The two columns cross near n=400, and past there geometry is the ceiling: the galleries
land at 217 and 405 against a greedy walk at 0.07 that leaves 233 and 435 places. Green
fills exactly through n=200 and lime never fills. `→ scratch/SOLVE_themed_lime_green`.
The seats are weak — worst seated rank key 0.0125 (lime) and 0.0241 (green) at n=200,
against 0.418 for the main gallery at n=150 — which is what the relaxed bar buys.
A themed solve costs 3–8 s at every rung, because the geometry rule opens no picture.

## `curate hunt` — rendering into a shortage instead of around it

The solve above turns an impossible gallery into a **work order**. This is what
spends it. A hunt renders candidates at places and in colours that were chosen on
purpose, writes them into the ledger, and leaves the same solve to be taken again
so the shortage can be measured against what it cost.

```
src/fractal_wallpapers/curation/hunt.py             the legs, the budget, the price
artifacts/curation/hunt/frames.jsonl                the frame index, derived from the scan
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

**A framing is an attribute a location may or may not carry, never an admission
ticket.** `hunt.frame_for` is the whole of the seam: where the pool-wide scan holds
a row, the leg draws the frame that scan chose; where it does not, the leg draws
`hunt.recorded_frame` — the `viewport` and `maxiter` the location's own store row
already carries, stamped `used: original`, `adopted: false`, `from_scan: false`. That
is exactly what `chosen_frame` returns for a scan row that *refused*, so the two
absences make the same picture and only the record tells them apart.

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

## `mode_policy` — what standing each mode has, in one table

`curation/mode_policy.py` is the only place a mode's standing is written.
`MODE_POLICY` maps every one of the engine's nineteen **production** modes to a
weight in `{0, 1, 2}` — five niche, seven normal, seven promoted — and
`mode_policy.check()` refuses unless the table and the engine's catalog name the
same roster.

```
fractal-wallpapers curate solve run --n 150 --name n150   # seats over accepted() only
python -c "from fractal_wallpapers.curation import mode_policy; print(mode_policy.check())"
```

**One row's mode is not always the mode it was drawn in.** `mode_policy.routed_mode`
is the second thing this module owns and the only place the rule is spelled: a
modulate whose texture had no span to normalize against produced the `smooth`
field spent by rank *bit for bit*, so the row routes as `smooth` everywhere a mode
or a kind is decided. It holds because every catalogued composite and the modulate
are built on the same smooth base, which the engine asserts over its whole catalog.
`itinerary` is the one production mode it can apply to today. The flag rides on the
ledger row as a bare boolean; `solve.pool` takes it before it asks the roster, so
the per-mode bars, the mode floors and the seated census all follow without asking
again, and `candidate_ledger.census` takes it on the modes axis. Nothing is renamed
and no picture moves — the recipe still says `itinerary` and the file on disk is
untouched. The register behind it, and what it costs to fill, is
[`data/coloring/README.md`](../../../data/coloring/README.md).

**The 0 is wired in three places.** A weight-0 mode is out of
the **labeling rosters** and the **default mining rosters** (both through
`colorize.modes_for`, `mine._accepted_modes` and `hunt.plan`, so the mode draw, the
mine, the hunt and `manufacture` all honour it), out of the **depth roster**
(`depth.field_modes`), and out of **gallery emission** — `solve.pool` refuses the
row and counts it as `niche_mode`, which is the one pool both the greedy seating
and the census read. The mode floors in `solve`, `headroom` and
`candidate_ledger.feasibility` are asked of `accepted()` for the same reason: a
floor over a mode with no rows in the pool is a mandate nothing could meet.

**Weights 1 and 2 differ at the seat, and that is the whole of what a 2 buys.**
There is still no MODE-side cap anywhere — `rules.RULES` has none — but the floor
an *unflagged* seating and an unflagged solve take is `mode_policy.seat_floors(n)`,
which floors a promoted mode at twice a normal one. The section below is the rule
and what it measured.

### The seat floors that make a 2 mean something — ON by default since 2026-08-31

`mode_policy.seat_floors(n)` is the rule that turns the weights load-bearing, and
**it is the default**: `curate solve run` is floored per mode by
naming nothing. `--flat-floor` is the way off, back to `solve.mode_floor`'s flat
`floor(n / 100)`. `test_the_floor_rule_is_the_default_and_a_flag_is_what_turns_it_off`
asserts both halves on the parser and on the record a seating writes, and
`test_the_exact_solver_is_floored_by_the_same_rule_the_greedy_is` pins that the two
legs answer one question.

**Why it is on rather than measured further.** Matt's ruling, ckpt 94: diversity
definitionally makes a better gallery, so the floors ARE the design — the
10,000-hour frame, `N / 100`, "novelty is worth a 3" — and the measurements below
are a pathology check that passed rather than the case for the rule. The open
question the flip leaves is the price, which is what the reject autopsy is for.

```
curate solve run --n 150 --name n150                     # floored per mode
curate solve run --n 150 --flat-floor --name n150_flat   # the flat floor, for a baseline
python -c "from fractal_wallpapers.curation import mode_policy as m; print(m.seat_floors(1000))"
```

#### What the rule does, measured at n = 150 under routing

`flip_flat` (`--flat-floor`, one seat a mode) beside `flip_floored` (the default),
on **one pool** — 97,423 candidates, 11,137 clearing, 4,480 places after the
neutral pre-selection — same rank key, same proportional group cap, 2026-08-31,
after the modulate re-routing and with `tail_itinerary` at weight 0. **The flip is
not conditional on any of it**: the ruling is above, and this is the pathology
check.

**Both filled 150 of 150 and all 14 modes, and every floor was filled — `starved`
is empty on both.** The floors ask for 45 of the 150 seats, and because each was
filled the census's covering bound over those modes, `sum of min(floor, that mode's
clearing places)`, is exactly the 45 they need.

**Three of the thirteen floors bind**: `itinerary` (1 seat under the flat floor,
floor 5, took **6**), `direct_trap_lines` (1 → 2) and `direct_trap_multiply`
(1 → 2). The other ten were already above their floor and the rule asked them for
nothing.

**And it moved 46 of the 150 seats, not 7.** That is the finding, and it is the
same shape the pre-routing reading found (52 there). Filling three floors demands
seven seats; what changes is a third of the gallery, because the scarcity leg
seats 45 before the general leg starts and every one of those takes a location, a
colour cell and a palette group out of what the general leg then sees. By mode:
`itinerary` +5, `stripe` +3, `curvature` `direct_trap_screen` `smooth_angle_min`
+2 each, against `smooth_stripe` −7, `threads` −6, `smooth_curvature` −3,
`tia` −1. `smooth` is unmoved at 33 both ways.

**Of the 45 seats the floor leg placed, 22 would have been seated anyway** — the
flat gallery holds them too — so **23 seats exist only because a floor bound**.
That is the price, and it is what the autopsy sheet lays out beside the 46 seats
the flat gallery held and the floored one does not.

The refusal ledger says the same from the other side: `cell_allowance` 2,773 →
**3,095**, `the_greedy_had_no_seat_left` 6,002 → 5,655, `twin` 99 → **68**,
`group_cap` 4 → **19**, `location` 291 → 332.

**The two orderings still disagree about whether it is better.** The floored
gallery has the better worst seat on the judge's own column (`P(>=4)` 0.5184
against 0.5070), holds **128** seats above `P(>=4) = 0.90` against 121, and sums
1.10 higher on `p_ge4` — while summing **2.20 lower** on the fitted `rank_key` it
was actually sorted by, with a worse floor there (0.4185 against 0.4309). Every
seat clears the q4 bar in both. A rule that improves the judge's raw fourth
cutpoint and costs the fitted key is a rule whose acceptance is a ruling and not a
number's, which is what ckpt 94 was.

Records `artifacts/curation/seat/flip_floored/seat.json` and `.../flip_flat/`;
sheets beside them; the reject autopsy is `scratch/flip_floor_autopsy.html`, which
pairs each of the 23 with the displaced seat it shares a palette group or colour
cell with.

* `mode_policy.STRANGE_SEAT_SHARE = 0.60` is the strange share of a gallery's
  **seats**, declared and not measured. It is **not** `run.STRANGE_SHARE`, which
  carries the same number and splits a release's *mining slots* between the heads
  at `budget.head_slots`. One name over two stages is the confusion this repository
  keeps paying for, so the seat-side name says `SEAT`. The knob is the floor's
  denominator and nothing else: no rule asks a finished gallery whether it realized
  the share.
* Over the **13 accepted strange modes** — `accepted()` less `smooth`, read from
  `colorize.modes_for(budget.STRANGE)` — `2·promoted + 1·normal` sums to 20 and
  distributes the strange budget fully. Each mode's floor is **half** its share, so
  the floors sum to exactly half the budget and the other half is the gallery's to
  spend on whatever is strongest. At `n = 1000`: budget 600, floors summing to 300,
  30 a promoted mode and 15 a normal one.
* The halves are fractional, so they are integerized by **largest remainder**, ties
  by weight then by name. That is deliberately *not* `supply.apportion`'s rule,
  which is largest-*deficit* sequencing and whose subject is every prefix of a batch
  that may stop early; nothing stops early here and the only property asked is that
  the floors sum. An odd budget rounds the house up: `(budget + 1) // 2`.
* No mode gets a bare 1 by exception, `direct_trap_multiply` included. Smooth is not
  in the table at all — `colorize.modes_for` returns `[SMOOTH_MODE]` unconditionally
  on the smooth branch, so the smooth side is one mode by construction and has no
  distribution to solve.
* **Where a floor collides with a ceiling the ceiling wins and the floor goes
  unfilled.** `solve.solve(floor=...)` takes the
  mapping, and the seating record reports the collision per mode under
  `shortfalls.modes.per_mode` — `clearing` above `seated` means a rule named in
  `refused_by` took the seats, `clearing` at `seated` means the pool held nothing
  more. `starved` (a floor above zero that went unfilled) and `floor_never_needed`
  (a floor of zero, which no gallery can fail) are separate lists, because the old
  single one read as working when the floor was switched off.

**Nothing is deleted.** A niche mode keeps its labels, its ledger rows and its
pictures; it renders by name; `--modes` names it and is taken as given; and a
verdict already exported on it still ingests — which is what let the head-top drop
be counted against the standings it was collected to test, and moved `curvature`
out of the niche set on 2026-08-29.

**Two layers, one word.** The engine's `Tier::Niche` (`de`) is a claim about what
the finished-render corpora were collected over and lives in Rust; this table is a
claim about what is worth collecting next, and it has to express a third value a
two-valued tier cannot. `check()` refuses if a mode carries both.

### Every mode's capabilities, in one table

What each of the nineteen production modes can do, so nothing below has to say it
again in prose. Every column but the last is read straight out of code —
`colorize.kind_of`, `colorize.shareable`, `autolevel.applies_to`, `MODE_POLICY` —
and re-deriving it is `python -c` over those four names, never a measurement.

| mode | kind | shareable / field dumpable | `autolevel` | weight | bar |
|---|---|:-:|:-:|:-:|---|
| `smooth` | field | yes | yes | 1 normal | `P(>=4)` |
| `tia` | field | yes | yes | 2 promoted | `P(>=4)` |
| `stripe` | field | yes | yes | 2 promoted | `P(>=4)` |
| `exp_smoothing` | field | yes | yes | 1 normal | `P(>=4)` |
| `curvature` | field | yes | yes | 1 normal | `P(>=4)` |
| `gaussian_int` | field | yes | yes | **0 niche** | none |
| `trap_circle` | field | yes | yes | **0 niche** | none |
| `smooth_stripe` | composite | no | yes | 2 promoted | `P(>=4)` |
| `threads` | composite | no | yes | 2 promoted | `P(>=4)` |
| `smooth_mean_angle` | composite | no | yes | 2 promoted | `P(>=3)` fallback |
| `smooth_angle_min` | composite | no | yes | 2 promoted | `P(>=3)` fallback |
| `smooth_curvature` | composite | no | yes | 1 normal | `P(>=3)` fallback |
| `smooth_trap_circle` | composite | no | yes | **0 niche** | none |
| `direct_trap_screen` | direct | no | **no** | 1 normal | `P(>=3)` fallback |
| `direct_trap_multiply` | direct | no | **no** | 1 normal | `P(>=3)` fallback |
| `direct_trap_lines` | direct | no | **no** | 1 normal | `P(>=3)` fallback |
| `direct_trap_ring` | direct | no | **no** | **0 niche** | none |
| `itinerary` | modulate | no | **no** | 2 promoted | `P(>=4)` |
| `tail_itinerary` | modulate | no | **no** | **0 niche** | none |

Nineteen modes over **four** kinds, not three: `itinerary` and `tail_itinerary`
are the `modulate`s. Seven field · six composite · four direct · two modulate.
Five niche, seven normal, seven promoted; thirteen carry the autolevel operator
and seven are shareable.

`tail_itinerary` is the same address as `itinerary` read off the **end** of the
orbit rather than the start, so every capability column is the modulate's and not
a judgement about the new mode: unshareable and undumpable because a modulate has
no single scalar index behind it, outside `autolevel` because the operator re-bakes
the colormap a modulate reads a different place in per sample, and never in a
near-band draw because that draw's roster is `depth.field_modes`, the shareable
ones.

**Its weight is a judgement about the new mode, and it is 0.** It arrived at 1
provisionally, on no labels, so that a mode nothing may draw would get its contact
sheet; it got one and Matt ruled it not gallery-worthy — the frequency of address
changes is too abrupt (ckpt 94). No further draws were bought, so there is no rate
to quote and there never will be. Nothing is deleted: the catalog entry stays, the
engine renders it by name, and its pictures are where they were.

**`shareable` and "a field is dumpable" are one column, not two.** `colorize.shareable`
is `kind_of(mode) == FIELD_KIND` and nothing else, so the two agree on all nineteen.
The only way they can ever part is `colorize._UNSHAREABLE`, a per-process cache of
modes the engine refused a dump for at runtime; it is empty on a fresh interpreter,
so a document that prints both columns is printing the same column twice.

**The bar is the one column that is not a code constant.** A mode falls back to
`P(>=3) >= 0.50` when fewer than `headroom.FALLBACK_MIN` (25) distinct locations
clear `P(>=4) >= 0.50`, which is a fact about the pool on the day. The column above
is read off the newest seating record — `mode_policy_switch_n150`, 2026-08-30, over
275,822 candidates of which 20,028 cleared — and it moves when the pool moves.
`config.bars` on any `solve.json` is the authority for that record's own pass. A
niche mode has no bar because it has no row in the pool to bar: `solve.pool` refuses
it upstream.

**And it has moved twice on 2026-09-01 alone.** Re-read that morning over a pool of
100,743 candidates (125,697 ledger rows less 24,906 refused `niche_mode` and 48
rejected), of which 11,574 clear: `direct_trap_multiply` was the only mode left on
the fallback. The five that came off it — `smooth_mean_angle`, `smooth_angle_min`,
`smooth_curvature`, `direct_trap_screen`, `direct_trap_lines` — reached 40, 33, 49,
39 and 31 distinct clearing locations against `FALLBACK_LOCATIONS`' 25.

Merging that afternoon's three cost pilots added 108 `direct_trap_multiply` rows and
took it off too, at **exactly 25** locations, so **`on_fallback` is now empty** and
every accepted mode is on `P(>=4) >= 0.50`. Its measured clear rate reads **13.99% →
2.20%** across that flip: the bar moved, not the mode, and 134 clearing locations
became 25 because the question changed. Read a per-mode clear rate beside the rule it
was taken under or it is not a number. At exactly 25 the flip is fragile — one prune
or rescore moves it back, `bars` is derived at read time from no stored row, and
nothing warns.

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
artifacts/curation/mine/<name>/pictures/<key>.jpg    the renders, named by recipe
artifacts/curation/mine/<name>/fields/<name>.f32     one dumped field a (location, mode),
                                                     swept to 64 as the run goes
artifacts/curation/mine/<name>/mine.json             the record: plan, price, profile, arms
artifacts/curation/mine/<name>/autopsy.html          primed and rejected, sorted by P(>=4)
artifacts/curation/mine/<name>/bench.json            the loop against its cheaper shapes
```

```
fractal-wallpapers curate mine run   --name pilot --rate 1.84 --budget 480   # measure the rate
fractal-wallpapers curate mine merge --name pilot                            # fold into the ledger
fractal-wallpapers curate mine run   --name m1 --rate <measured> --budget 7200
fractal-wallpapers curate mine plan  --name m1 --rate <measured> --budget 7200   # renders nothing
fractal-wallpapers curate mine bench --name m1     # price the loop's alternatives
fractal-wallpapers curate mine sheet --name m1     # redraw the autopsy page
```

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

**The rate is measured on the mine's own target population and is required.**
`run` refuses without `--rate`. A rate carried in from another pass prices another
population; the recommended shape is a short run first, then its measured figure.

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
fractal-wallpapers curate depth plan  --name d1 --rate 0.35 --budget 5400   # renders nothing
fractal-wallpapers curate depth run   --name d1 --rate 0.35 --budget 5400
fractal-wallpapers curate depth merge --name d1                             # fold into the ledger
fractal-wallpapers curate depth sheet --name d1                             # redraw the autopsy
```

**Field modes only, and every conclusion is conditional on that.** A composite at
forty candidates is **212 s a location, measured** — one arm's worth of places would
eat a ninety-minute budget — so the roster is `depth.field_modes()`: the shareable
modes `mode_policy` accepts.

(That sentence read "about 175 s" and was a derivation off a per-candidate rate
until 2026-09-01, when `audit_comp40` measured the visit directly at **212.1 s mean
and 199.5 median** against a field visit's **27.7 / 21.6** and a direct trap's
**75.3 / 47.8** — the three-leg pilot in the rate section below. The estimate was
21% low. What no depth run reports is still what a composite *clears*: these three
legs are unmerged, and their clear rates are the pilot's own.)

**That roster is five modes now, and it was six.** `smooth`, `tia`, `stripe`,
`exp_smoothing`, `curvature`. Two of the seven production field modes —
`trap_circle` and `gaussian_int` — are `mode_policy` weight 0, and they were two of
the cheapest things a depth run could render. (This paragraph said *four* and named
`curvature` as a third weight-0 mode until 2026-09-01; `curvature` moved 0 → 1 on
2026-08-29 and `mode_policy`'s own docstring carries the ruling.) A depth leg is
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

**Two things the record gets wrong when it does.** `config.field_modes_only` is
written `True` unconditionally, so `cc_pilot` claims it while carrying 96
`smooth_angle_min` and `smooth_mean_angle` candidates. And the single `--rate`
prices candidates, while `weave` holds the arms' proportions in **counts**: in
`cc_pilot` the `mode_floor` arm took 25.0% of its planned count — exactly the leg's
own 25.0% truncation — and **24.7% of the engine seconds against a declared 5%
share**, because its two composites cost 5.53 s a candidate against the field arms'
0.70–1.03. A share is a share of the plan, not of the budget, the moment two arms
run different kinds.

### What the two empty modes actually cost, measured

`smooth_mean_angle` and `smooth_angle_min` are the pair the n=2000 census called "nothing in the
pool". They are **composites, not field modes** — no dump to amortise, a full render a candidate —
and the dearest pair on the roster after `smooth_stripe`. `empty_modes`, 2026-09-01, this machine
idle, three engines below-normal, `--width 8 --floor-width 4`, seed 20260827, 979 candidates in
1,813.5 s render wall at concurrency 2.989:

| arm | population | `smooth_angle_min` | `smooth_mean_angle` |
|---|---|---|---|
| `ranked_bands` | never-opened, head-ranked | 0.090 · **75 s** | 0.059 · **129 s** |
| `mode_floor` | proven places | 0.097 · **66 s** | 0.032 · 229 s |
| `flat` | never-opened, unconditioned | 0.040 · 202 s | 0.040 · 218 s |
| **all arms** | | **10 wins · 85 s** | **6 wins · 160 s** |

Location clear rate · **wall** seconds a clearing location; engine seconds are 2.989x these. The
bar is each mode's own `headroom.bars` rule, `P(>=4) >= 0.50` for both since they came off the
`P(>=3)` fallback that morning — a rate quoted against the older rule is a different number.

**Three things to carry forward.** The head's rank buys money: `ranked_bands` beats the
unconditioned `flat` control 2.2x and 1.5x, and flat is the worst arm for both. The census priced
the two within 0.4 s of each other and **`smooth_mean_angle` actually costs 1.9x per win**, being
both the slower render and the thinner clear rate (1.84% against 2.66%) — allocate to them
separately. And the census's own figure was **76.5 / 76.9 s a win against a realized 113 s pooled,
1.47x optimistic**, because it was carried in from another leg's rates.

**Mining one short mode does not necessarily cut the shortfall.** The 16 clearing locations this
leg bought moved `smooth_mean_angle` 21 -> 25 and `smooth_angle_min` 18 -> 22 at n=2000, and the
total shortfall stayed at **200**: `smooth_curvature` lost 6, `smooth_stripe` 3 and `threads` 1 in
the same pass. A place seated in one mode is a place not seated in another, so in a gallery where
ten demands are short, a mine that does not add **places** moves seats between them. These 16
added only 9 to the view (4,750 -> 4,759) — the `mode_floor` wins were at places the view already
held. What refuses these two is `below_its_mode_bar` and then `one_per_location`, at 2-3x what
twin refuses; that is the opposite of the gallery-wide ranking and it is a supply problem.

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

Two things this leg also measured, both against `empty_modes` above. **The head's
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
`mine._accepted_modes()` — all fourteen — and `plan_floor` never intersects its
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
`tia` was the whole of it — it cleared the seating bar at .0208 in breadth at
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
holds a **proven** location — one already over the seating bar — and cycles the
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

**Pilot to a fraction of the leg, not to a fixed wall.** `--rate` has to come from a
run at this width on this population, and a *short* one still under-reads: on
`sparse_mode_harvest` a 180 s pilot priced its direct partition 13.6% low and its
composite partition **67%** low (1.8397 against 3.0803), every per-mode rate moving
the same direction, because 180 s reaches only the cheap head of the draw. The field
pilot, whose 852 candidates were a fifth of its leg, priced it to 0.4%. A low rate
costs *candidates* and never minutes — `--budget` is wall and the leg stops at it
either way, booking the shortfall to `counts.stopped_for_budget`.

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
  at locations already over the seating bar. `tia` needs depth: level with `smooth` at
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
* **`config.field_modes_only` is stamped `true` unconditionally** and is not enforced:
  `build_plan` takes `--modes` verbatim with no `colorize.shareable()` check, so a
  wholly composite roster runs and its record still claims field modes only. Do not read
  that field. The cost of that is in the plan rather than in the record: the roster is
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

## Every per-candidate rate this project has measured

⚠ **These are historical, measured under different conditions, and not comparable
across rows.** A rate is a joint fact about the mode roster, the width `k`, the
engine count, the picture geometry and whether the field was shared — change any one
and the number moves by more than the spread of this whole table. Nothing here is a
constant, none of it sizes a leg you have not piloted, and the depth roster moved to
five field modes on 2026-08-29, so **every row below predates the current roster**.
Pilot the roster the leg will actually run.

This caveat is stated once, here. Everywhere else in these documents that quotes a
rate should point at this table rather than repeat the warning.

**Read `s/cand` as per ENGINE**, which is what `--rate` wants and what
`budget.seconds_per_candidate` records. A rate read off a three-worker leg carries
that leg's contention: three engines cost about 1.6–1.8x per candidate over one.

| s/cand | mode or roster | eng | k | date | population drawn | record |
|--:|---|:-:|--:|---|---|---|
| 1.26 | production mix, before the shared field | 1 | 3 | 08-26 | 5,684 cand / 7,169 s | `mine1` |
| 0.976 | field, **before** field sharing | 1 | 1 | 08-26 | 9 never-opened places x 8 maps | `curate mine bench` |
| 0.673 | field, after | 1 | 1 | 08-26 | same | `mine bench` |
| 0.217 | field, after | 1 | 8 | 08-26 | same | `mine bench` |
| 0.178 | field, after | 1 | 20 | 08-26 | same | `mine bench` |
| 0.165 | field, after | 1 | 40 | 08-26 | same | `mine bench` |
| 0.041 | a bare recolour, flat in maxiter | 1 | — | 08-26 | same | `mine bench` |
| 0.417 | 6 cycled field modes | 3 | 40 | 08-27 | `dc1`/`dc2`, 61,863 cand | depth curves |
| 0.356 | 3 field modes | 3 | 20 | 08-27 | same | depth curves |
| 0.260 | near band, mode held | 3 | — | 08-27 | same | depth curves |
| 0.898 | `tia` dump, 3-mode roster | 3 | — | 08-27 | same | depth curves |
| 0.497 | 6 breadth field modes | 1 | 24 | 08-28 | seed 20260827 | `curate depth` |
| 0.696 | 2 composites, **no sharing** | 1 | 24 | 08-28 | seed 20260827 | `curate depth` |
| 0.278 | 2 field modes, near-heavy | 1 | 24/127 | 08-28 | `mine1h` field leg | `curate depth` |
| 0.743 | 4 direct traps, near-heavy | 1 | 24/136 | 08-28 | `mine1h` composite leg | `curate depth` |
| 0.270 | `{gaussian_int, curvature}` | 1 | 24/40 | 08-28 | 649 of a 2,416 plan, seed 20260901 | worker bench |
| 0.496 | same | 3 | 24/40 | 08-28 | 1,076 of the same plan | worker bench |
| 0.424 | same, `ENGINE_THREADS_PER_WORKER` 7 | 3 | 24/40 | 08-28 | 1,254 | worker bench |
| 0.442 | same, 4 engine threads | 3 | 24/40 | 08-28 | 1,219 | worker bench |
| 0.2652 | one leg's seed re-run serially | 1 | — | 08-28 | 440 of 440 identical recipes | `mine_weak_modes` |
| 0.4707 | the same leg | 3 | — | 08-28 | location-matched to the row above | `mine_weak_modes` |
| 4.377 | WIDE, weak modes | 3 | 3 | 08-28 | 2,726 renders / 3,988 s | `mine_weak_modes` |
| 0.680 | DEEP, weak modes | 3 | 40 | 08-28 | 4,520 renders / 1,038 s | `mine_weak_modes` |
| 0.285 | NEAR, weak modes | 3 | 96 | 08-28 | 35,306 renders / 3,402 s | `mine_weak_modes` |
| 2.843 | COMP, 3 composites | 3 | 24 | 08-28 | 2,107 renders / 2,002 s | `mine_weak_modes` |
| 1.480 | `direct_trap_lines` alone | 3 | 24 | 08-28 | 849 renders / 422 s | `mine_weak_modes` |
| 0.4505 | `trap_circle`,`gaussian_int`,`curvature` | 3 | 60 | 08-29 | 45,104 cand / 6,833 s | `sparse_mode_harvest` P1 |
| 0.501 | `gaussian_int` | 3 | 60 | 08-29 | 15,035 cand | same leg |
| 0.500 | `curvature` | 3 | 60 | 08-29 | 15,034 cand | same leg |
| 0.350 | `trap_circle` | 3 | 60 | 08-29 | 15,035 cand | same leg |
| 1.646 | `direct_trap_screen` | 3 | 12 | 08-29 | 1,977 cand | `sparse_mode_harvest` P2 |
| 1.469 | `direct_trap_lines` | 3 | 12 | 08-29 | 1,978 cand | same leg |
| 2.360 | `direct_trap_ring` | 3 | 12 | 08-29 | 1,977 cand | same leg |
| 0.953 | `itinerary` — never shareable, full render | 3 | — | 08-29 | `mode_policy` pricing | `mode_policy` |
| 0.239 | `smooth`, priced beside it | 3 | — | 08-29 | same | `mode_policy` |
| 0.3433 | `smooth` alone, whole leg | 3 | 12 | 08-29 | 116,520 cand / 9,710 places | `smooth_500` |
| 0.4777 | `smooth`, that leg's own pilot | 3 | 4 | 08-29 | 11,138 cand | `smooth_500` |
| 0.3558 | `smooth`, ranked-bands arm | 3 | 12 | 08-29 | 84,084 cand / 7,007 places | `smooth_500` |
| 0.3132 | `smooth`, flat arm | 3 | 12 | 08-29 | 24,948 cand / 2,079 places | `smooth_500` |
| 0.3038 | `smooth`, conditioned arm | 3 | 12 | 08-29 | 7,488 cand / 624 places | `smooth_500` |
| 4.676 | production draw, 1 smooth + 2 strange, palette head | 3 | 1 | 09-01 | 2,286 cand / 762 head-q4 nuclei | `reframe_q4` |
| 0.692 | 5 accepted **field** modes | 3 | 40 | 09-01 | 1,400 cand / 35 whole visits | `audit_field40` |
| 1.883 | 3 accepted **direct traps** | 3 | 40 | 09-01 | 1,440 cand / 36 whole visits | `audit_direct40` |
| 7.360 | 5 **composites** + `itinerary` | 3 | 40 | 09-01 | 328 cand / 7 whole visits | `audit_comp40` |
| 0.5461 | 5 accepted **field** modes, all three arms | 3 | 40 | 09-01 | 6,557 cand / 208 blocks | `general20` |

**The three 09-01 rows are one matched pilot** — `ranked_bands` at share 1.0, seed
20260901, the never-opened drawable pool banded across the whole rank range, nothing
merged — so they are the one place in this table where three kinds are comparable.
Per **visit** (40 candidates at a place) they are **27.7 / 75.3 / 212.1 s** mean and
**21.6 / 47.8 / 199.5** median. Their medians are 0.372 / 1.157 / 5.231, which is
where the mean-vs-median warning below bites hardest: sizing a field leg off the
median over-plans it by 86%.

Where the visit goes, and it is not the same shape three times. A field visit is
**9.13 s of dump** — five modes at 1.83 s each, 33% of the leg — then 0.463 s a
candidate for the recolour, judge, colour and autolevel. A direct trap is **86.3%
`paint`** and nothing else: no dump, and `autolevel.applies_to` excludes the kind, so
`repaint` and `measure` are exactly 0. A composite is 59.1% `paint` and **33.6%
`repaint`** — the operator's second pass is a second *full render* there, so a third
of a composite visit is the autolevel curve firing.

On a wall hour at three workers, and applying each mode's own `headroom.bars` rule
over the standing pool, that is **15,133 / 5,601 / 1,448** candidates an hour and
**1,378 / 109 / 99** clearing ones — field buys **13.9x** the seatable pictures of
composite and **12.7x** of direct trap. On these pilots' own fresh clear rates
(4.71% / 4.24% / 1.83%) it is 713 / 237 / 27, which is 27x and 3.0x; the pool's
rates are the higher pair because the pool holds legs that aimed at those modes.

**The direct figure read 330 an hour and 4.2x for half a day, and the bar is why.**
Merging the three pilots put `direct_trap_multiply` over `FALLBACK_LOCATIONS` at
exactly 25, its rule flipped off the `P(>=3)` fallback, and the leg's mixed pool rate
went 5.88% → 1.94%. Nothing about the mode changed and no row was re-rendered. This
is the sharpest example in this file of why a per-mode rate is meaningless apart from
the rule it was taken under — and of why a *ratio* between two modes on different
columns is not a comparison at all.

**Every `s/cand` above is a MEAN, and the flat-vs-ranked comparison needs the
median beside it.** A per-candidate cost is long-tailed — `mine1`'s per-partition
means run 0.67 to 2.06 against medians of 0.42 to 1.05 — so the two answer
different questions and neither substitutes: a **mean** is what sizes a plan,
because `PLAN_HEADROOM * workers * budget / rate` is arithmetic over the *sum*,
and a **median** is what a candidate typically costs. Quoting one alone hides
which. Both read off the rows themselves, `hunt.seconds` on `mine1`'s
`rows.jsonl` and `seconds` on `smooth_500`'s `sequence.jsonl`, per arm:

| leg | arm | n | mean | median | mean/median |
|---|---|--:|--:|--:|--:|
| `mine1` 08-26 | `deepen` | 2,274 | 0.7064 | 0.4690 | 1.51 |
| `mine1` 08-26 | `breadth_ranked` | 1,989 | 1.3000 | 0.7030 | 1.85 |
| `mine1` 08-26 | `breadth_flat` | 1,421 | 2.0848 | 0.8750 | 2.38 |
| `smooth_500` 08-29 | `conditioned` | 7,488 | 0.3038 | 0.1980 | 1.53 |
| `smooth_500` 08-29 | `flat` | 24,948 | 0.3132 | 0.2280 | 1.37 |
| `smooth_500` 08-29 | `ranked_bands` | 84,084 | 0.3558 | 0.2520 | 1.41 |

**"The ranked arm renders 1.6x cheaper than the flat one" is a mean and only a
mean.** On medians the same two arms are **1.24x** apart, so most of that gap is
`breadth_flat`'s tail — an unconditioned draw takes places nobody chose and a few
of them are very dear — rather than its typical candidate. The direction survives
the change of statistic and the size does not, which is the whole reason both are
here.

**And the sign is not a standing fact about the two draws.** On `smooth_500`,
one mode and the whole top half of the head's rank, the ranked arm is the
**dearer** of the two — 1.14x on the mean and 1.11x on the median — because that
leg's ranked draw is spread over five bands and the flat draw is not, so the two
are drawing from differently-stocked partitions. `mine1`'s ordering is `mine1`'s.

**Per-mode dump cost in breadth**, one number a mode, `dc1`/`dc2` 2026-08-27:
`stripe` .378 · `gaussian_int` .285 · `curvature` .268 · `tia` .147 ·
`exp_smoothing` .147 · **`smooth` .056**. Stripe's field costs seven times smooth's
to dump, which is why it is the dearest field mode to draw.

**What the spread is made of, and it is not noise.** The table runs 0.041 to 4.377,
a hundredfold, and four mechanisms account for nearly all of it. **Field sharing**:
one dump amortised over `k` palettes, 0.976 to 0.165 from k=1 to k=40 on the same
places. **Coloring kind**: a mode with no dumpable field pays a full render every
candidate, which is `itinerary` at 0.953 against `smooth`'s 0.239 on the same day.
**Where the draw came from**: a near-band place holds its mode and pays one dump
over the whole set; a breadth place cycles the roster and pays one per mode.
**Contention**: three engines are ~1.7x per candidate over one, and the record's
`concurrency` field is engine-seconds over wall and is **not** a speedup.

**A pilot over-reads a short leg's rate by a knowable amount.** Budget seconds are
`stages.total()` and exclude the fixed start — the population read, the judge load
and the plan build, about 50 s — so a short run's wall carries it and a long run's
does not. `mine1h`'s pilots measured wall/spent at 1.28 where the legs came in at
1.03 and 1.02. Read a pilot's `spent / made`, never its wall. And do not pilot
unlike shapes concurrently: a k=40 pilot sharing the machine with a dump-heavy k=3
pilot came out 42% dear, and a composite pilot including the cheap
`direct_trap_lines` under-priced a leg that dropped it by 89%.

**Rates in other units live elsewhere and never belong in this table.** A gallery
release is priced per **row** (3.5 s/row on gallery4's 249 winners at 1280x720 ss2
on three workers, against gallery3's 44.6 s at 2560x1440 ss4 on four), and a
labeling measure pass per **unit** (2.8 s/unit over nine modes, 5.90 s/unit on a
single-mode sheet cut from the top of the pool). A row and a unit are a finished
picture; a candidate is 640x360 ss2. Mixing the three is how a leg gets priced an
order of magnitude wrong.


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
* `(colormap, mode) -> attempts, scored, successes`. 822 by 18. This is the "which
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

* **Nothing reads a candidate's for content.** Every `colormap_dir` override in the
  package is either the tracked palette directory, or a directory written moments
  earlier in the same call, or `sheets.render_finished(..., colormaps=unit["leveled"])`
  — and that unit's name is set by `manufacture` to its own **sheet** subtree. A sweep
  of every `.jsonl`/`.json` under the tree finds `.leveled` paths named in exactly four
  places: `manufacture/*/sheet`, `calibration/measure`, `correction/*/screen` and
  `mode_sheet/measure`. `run._discard_partials` is the only other caller and it only
  deletes one.
* **They are regenerable, by re-rendering and not by replay.** The file is
  `curved_stops(the map's stops, the curve)`; the map is tracked, and the curve is
  `derive_curve(stats_of(the base render), the tracked band)` whose sha256 is on every
  ledger row. So the recipe on the row re-derives it exactly — through
  `colorize.render(level=True)`, one candidate render. It is **not** replayable from
  the row, because `recipes.stamp_of` deliberately drops the derived curve: a
  manufacture row carries the whole curve and can be replayed from it, a ledger row
  cannot.

**194,058 directories were swept, 12,089 excluded** — those four named subtrees, the
released and parity pictures, the label sheets' own `full/` renders, and everything
belonging to a leg the ledger cannot answer for.

**The orphan JPEG pile is not what it looks like.** 6,529 pictures in the candidate
directories carry no ledger row, but **none of them is unnamed**: 7,466 more are
`manufacture/`'s own live products (named relatively, `pictures/000002.jpg`, by
`screened.jsonl` and the plan files), 4,535 belong to unmerged legs, 11,028 are run
*attempt* pictures named by index rather than by recipe key, and the 1,775 left are
named by a study's own record — `depth/breadth_strange`, `depth/wm1_serial`,
`depth/smooth500_pilot` by their `sequence.jsonl`, and `shrinkage/dc1` by the
`pairs.jsonl` those 200 label-geometry re-reads *are*. Nothing was deleted here.

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

### What the gallery leg costs at n=150 on this machine

Measured 2026-09-01 over the 100,743-candidate pool, idle machine, `--no-render`:
**`curate solve run --n 150` is 44.6 s** — pool and view 11.2 s, the seed 24.5 s and
the swap loop 8.9 s, over a view of 6,818 rows. The five-minute figure this
paragraph used to carry was the leg before `curation.signatures` and the two swap
prunes; the table under *What it costs* is the one to read. The retired history is the
comparison worth keeping: on 2026-08-29 over a 275,822-candidate pool the exact
solve was 238 s at n=150 and **did not terminate at all** at n=1000, while the
sequential `curate seat` was 51 s at n=150 and had no objective to report.

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

**Joining a pass's seats to their colour.** `curate expressed` keys its census the
same way, so `artifacts/curation/expressed/pictures.jsonl` filtered to
`run == <pass>` is one row per seat and joins on the candidate id with no path
matching. Its `picture` field is the absolute release picture the row was computed
on; comparing that path and re-reading the file with `expressed.full_shares` is
what proves a census row is about the picture in front of you.

**The attempts are the bulk and they are not in the history.** A pass makes
`locations x heads x draws` attempts per slot — 1,120 at n=50, ten times that at
n=500 — and a pool row carrying its whole join runs about 3.8 KB. They get the
`neutral_embeddings` treatment: under the regenerable tree, a copy on the archive
tier, a tracked manifest, and `curate gallery-store {check,save,restore}` over
them. The pass writes the copy and the manifest itself as its last act.

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

## `curate manufacture` — the one population here that is made rather than found

Everything else in this stage spends supply. This makes some. `expressed` counted
what the collection actually holds and found **eight of the fifty-two swatches on
none of the 246 finished wallpapers and twenty-one on five or fewer**, against a
library with 38 to 258 maps able to reach each of those twenty-one. The gap is
not capability, and it is not something a floor can fix — the arithmetic there
says a per-swatch floor cannot exist above about five percent. Nothing has ever
*asked* for those colours, so this asks.

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
`run.RELEASE_RESOLUTION` and `run.RELEASE_SUPERSAMPLE`, one geometry for every
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
release.** `data/palettes/clusters.jsonl` exists and groups the library sixteen
ways, but it is a *figure's* record — `palettes clusters` is its only reader, and
nothing in selection, in the release path or in the gallery pass consults it. So
two seated rows may land in one cluster, and what stops that is the without-
replacement anchor draw upstream rather than a cap downstream. This is a
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
The amendment is regenerable from the sidecar, the engine and the head, so unlike
the sidecar it gets no durable copy and no manifest.

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
[`durability`](durability.py) owns what follows from that: a copy on the archive
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
measured at `--workers 6`. That default is **three** since 2026-08-28 — every
probe is a recolor through the engine, so it is the locked render pool and not a
tuning knob — which puts it near 9 minutes at the release leg's measured 2.38x
concurrency gain on three. Re-measure rather than trusting that arithmetic. The panel's own dumps are 56 iteration passes, about 40 seconds.
Each recolor is censused and its JPEG overwritten rather than kept — keeping them
would be a gigabyte of pictures answering four hundred bytes each — so the contact
sheet re-makes the sixteen tiles it shows.

## What the finished collection expresses

[`expressed`](expressed.py) asks the same question one step further downstream,
about the pictures that exist rather than the maps that could make them:

```text
COVERAGE(s) = the fraction of finished wallpapers in which at least
              10% of the pixels are assigned to swatch s
```

```
fractal-wallpapers curate expressed                 # census, then read
fractal-wallpapers curate expressed --step census   # read every finished wallpaper only
fractal-wallpapers curate expressed --step read     # tables off a census already taken
```

```
artifacts/curation/expressed/pictures.jsonl   one row per finished wallpaper, four share vectors
artifacts/curation/expressed/expressed.json   the coverage vector, the budget, the agreement table
```

**The budget is the finding, and it is arithmetic.** Summed over a set of
swatches, COVERAGE *is* the mean number of them a picture expresses — the same
double sum read down the columns instead of across the rows. So a uniform floor
`f` over `k` swatches asks the average picture for `f * k` expressed colours, and
the largest `f` that can exist is `mean / k` whatever curation does. Both halves
are reported, all 52 and the 48 non-neutral, each with the whole histogram: the
population is 246 pictures over seven integers and every bar is a sentence about
what a floor would have to be true of.

**Population: the verdict, checked.** Every release row whose verdict is
`released` and whose full-size picture is on disk — the file is tested rather than
trusted, because a coverage vector short a picture is a number nobody can
reproduce. A row [`rejection`](rejection.py) took back afterwards is **kept**:
this is a question about colour, not about seating.

**Read at the shipped render's own resolution.** A share vector is not
scale-free, so the census reads each release PNG at whatever that picture is —
`full_shares` takes the size off the file and writes it onto the row — and the two
cheap instruments are priced against it rather than assumed. The numbers below
were taken over a population made entirely at 2560x1440; a pass shipping another
regime is a different population, and the pass record's `release_geometry` is what
tells them apart. The 160x90 decode
[`codebook.of_picture`](../palettes/codebook.py) uses moves a swatch by at most
0.7 of a point over the released population and flips 12 of 12,792 threshold
cells. The **candidate render is a different picture** — half the supersampling
at a sixteenth of the area, levelled off its own histogram — and moves a median
of 2.1 points, up to 64. That is why a recolor pass would screen at candidate
geometry and never measure there.

**Runtime.** 246 pictures, four share vectors each, about 180 s. The recolor pass
the readout *prices* is not run: `recolor_cost` reports the cross product it
would need — 724 carrier maps over 194 field pictures and 52 that need a whole
re-render per map — so the decision to spend it is taken against a number.
