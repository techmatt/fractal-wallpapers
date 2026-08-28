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
selection  top-N per judge, under the slot and supply caps, the location rule
           — and the bar
gallery    the second phase: one pass over the whole pool for what ships
gallery_store  a pass's attempt rows: under artifacts/, manifest-tracked
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
fractal-wallpapers curate gallery --n 100                              # THE gallery pass
fractal-wallpapers curate gallery --n 100 --no-refine                   # framings as recorded
fractal-wallpapers curate gallery --n 100 --refine-margin 0.10          # a stricter adoption
fractal-wallpapers curate gallery --n 100 --reseat 0                    # no re-seat: one draw
fractal-wallpapers curate gallery --n 100 --no-full-size                # seat, do not render
fractal-wallpapers curate gallery --n 100 --release-regime 2560x1440ss4 # the regime gallery1-3 shipped at
fractal-wallpapers curate gallery --pass gallery2                       # ...then make them
fractal-wallpapers curate gallery-store check --pass gallery1          # is the store whole?
fractal-wallpapers curate candidate-ledger backfill    # the cache, from what exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger save        # both files, made durable
fractal-wallpapers curate solve run --n 20             # THE solve: the gallery as a program
fractal-wallpapers curate solve sweep                  # which constraint binds first, and at what n
fractal-wallpapers curate solve truncate --n 20        # what a smaller reachable pool costs
fractal-wallpapers curate gallery --pass gallery1 --migrate            # out of the old layout
fractal-wallpapers curate manufacture --step register --write          # BEFORE anything
fractal-wallpapers curate manufacture --oversample 2.5                 # plan, build, select
fractal-wallpapers curate manufacture --step verify --sheet artifacts/<sheet>
```

## A run accumulates; the gallery pass chooses

The two halves used to be one command, and Matt split them on 2026-08-22. The two
phases have names: **the pool phase** is `curate run`, and **the GALLERY PASS** is
`curate gallery` — one global selection over everything the pool holds, re-runnable,
each pass a record, the previous gallery superseded rather than deleted.

**A run is the pool phase.** It reads the offer, colorizes, records every candidate
it made and every verdict on it, and keeps a **diagnostic** release of ten pictures —
enough to see that the path works, that the heads are reading the material and
that the palette pass is not producing one look. It does not try to decide what is
worth shipping: that is a judgement over the whole accumulated pool, and one
night's attempts are a few hundred rows of it.

Three things follow, and all three are in this stage now:

* **A run never refuses a place because an earlier run released it.** `curate run`
  used to build the served index and veto every candidate whose place the
  collection already had — one run's seats deciding the next run's coverage, out
  of the fraction of the pool it happened to hold. One wallpaper per location
  still acts *inside* a run, through the counter both heads share, and
  `served_locations` is now read only by the collection-level passes.
* **Every release row says which collection it is in.** `records.DIAGNOSTIC` for a
  run's own, `records.GALLERY` for what the collection ships. A field and not a
  fourth verdict: the three verdicts answer whether there is a wallpaper at the
  end of the row, and this answers which set it belongs to.
* **Nothing released so far is the collection's.** All 1,050 rows on record are
  `diagnostic`, backfilled in the same commit, because none of them was ever
  chosen against a pool.

## `curate gallery` — the seven steps, and the two knobs that are by eye

One command, and **not a run type**: no ledger binding, no pacing clock, no
harvest state, because a selection over an accumulated pool has none of those.
Each invocation is a **pass** with its own id, its own record in
`data/curation/gallery/`, and its own slice of the pool's decision store.

```
1  slots per partition   release_mix over a POOL-WIDE denominator (24,843 admitted
                         locations, not one binding's offer); release_caps and the
                         guarantee re-derived over it. The thin-supply cap is
                         thousands wide at that denominator and binds nothing —
                         computed and reported anyway, so a pass and a run are
                         comparable.
2  head split            per PARTITION, by --strange-share (0.6). The heads are
                         dealt across a partition's picks by largest deficit, so
                         neither judge gets the whole top of a partition.
3  the distance          artifacts/curation/neutral_embeddings.jsonl, refused
                         unless `curate embeddings check` says it is whole, then
                         CUT to the currently admitted population
4  the locations         quality-weighted farthest point under a HARD RADIUS
5a the framings          each location's frame scanned and the best adopted    <-.
                         if it beats the recorded one by --refine-margin        |
5  the attempts          m locations near each chosen point, judged small       |
                         plus one CARRIER attempt per location per --target      |
6  the seats             both measured floors ACT; P(>=4), P(>=3) tiebreak,   --'
                         then the COLOUR CEILING and the targets
                         5a, 5 and 6 are a LOOP: an unfilled slot re-seats, up
                         to --reseat (3) neighbourhoods, and everything either
                         side of them happens once
7  the pictures          1280x720 ss2 for the winners, and only for them.
                         --release-regime moves it; the pass record and
                         every release row say which pixels were made
```

**Steps 5 and 6 are two legs, and the names matter because they run whole rather
than interleaved.** `gallery.make_attempts` renders **every** planned attempt
first — one palette-head pick per attempt, `colorize.Colorizer.pick_palette` over
the set's thirty-two smooth-field recolours through `palette_head.top_pick` — and
only then does `gallery.seat` walk the slots, in `_seat_order` (pick position
first, then the partition's own order, so the partitions interleave), choosing
among candidates that **already exist**. A seat renders nothing except where the
colour ceiling bit and [`gallery.OnDemand`] is asked for one more picture — see
the ceiling below. That order is what makes a re-seat cheap: the attempts are on disk and
the second seating is arithmetic over them.

**`gallery.pool_candidates` applies TWO predicates, not one.** A row is seatable
only where its key is one of the slots' own neighbourhood locations **and**
`run_of(row) == pass_id`. The second is the ruling — locations are cumulative,
candidates are per-pass — and the first is what keeps a pass from seating a place
it never chose. Reading the rule as the maker-predicate alone gets the normal path
right by accident, because [`pool_rows`] has already set this pass's own rows
aside, and gets a re-seat round wrong.

**A slot is not married to one neighbourhood.** When every candidate a slot's
neighbourhood produced lands under its head's floor, the slot **re-seats**: it
takes the next point its partition's draw offers, under the same radius and the
same weighting and with the abandoned point still excluded, its new
neighbourhood is attempted, and the whole seating is taken again. `--reseat`
(default 3) is how many neighbourhoods a slot may stand on, and the slot record
keeps every one of them and what each held. So **`below_bar` means *k
neighbourhoods in a row failed*, not one did.**

**`--reseat` is this project's seat-to-budget lever, and it lives here rather
than in the supply engine.** The supply engine's levers are about a *clock* — the
per-partition floor, the exploration share, the discounted contest — and none of
them can move a seat, because a pass books no clock at all. What a re-seat spends
is attempts against a slot that is already allocated: the slot count never
changes, the partition never gains or loses one, and the only thing that moves is
which chosen point the slot stands on. Reaching for a supply flag to fill a
gallery slot is reaching for the wrong stage.

That gap was gallery1's whole shortfall. Every one of its eight unfilled slots
was `below_bar`; every one was the LAST slot of its partition — which is the
point of the draw most remote from everything already chosen, and so the one most
likely to sit somewhere its head dislikes on principle — and every one sat in a
partition still holding thousands of admitted locations. What the loop
deliberately does not do is the other recovery: no floor moves and nothing is
seated from under one.

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
location rule and its best held P(≥3) 0.881 against a floor of 0.575. It reads
`location_served` under `gallery.binding_reason`, and every count that says so
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

**The order at a seat is: the candidates that exist, then up to `EXTRA_PICKS` (3)
pictures rendered right there, then the least-violating fallback, flagged.** A
colour rule that could only refuse would spend its seats on that fallback, because
the pool it refuses out of was proposed by a quality judge that never had a colour
in the question. So the seating leg renders: the palette head's next-best maps of
the set it already scored for that location, screened for a hue family nothing
tried has been, in the attempt's own mode. Cost lands only on the seats the
ceiling bit, and it lands as a *render* rather than as an attempt — the field is
dumped and the thirty-two recolours are already scored. Rendering the same
material up front would have been 3,632 renders bought to change at most 150
decisions. [`gallery.OnDemand`] is the class that does it, and it is the whole of
what a ceiling costs. Its pictures are cached by `(location, mode, map)` in
`<pass>/on_demand.jsonl`, which is what keeps the re-seat replay free, and they go
into the attempt store as pool rows like any other, stamped `on_demand`.

The other half is solved one step earlier and for free: when the palette head
picks a map whose **group another attempt of the plan already picked**, its
next-ranked candidate takes that attempt instead. A pure identity filter, no
pixels and no state about pictures, recorded on the row as `group_skipped`.

**A re-seat replays the whole sequence.** The ceiling makes seating
path-dependent, so a slot that moves invalidates every seat after it in the walk
order — and only after it, which is why replaying is enough and patching is not.
Replaying arithmetic is free; replaying renders is not, which is what the
on-demand cache is for.

**The log and the store have to be reconciled, and there is a subcommand for it.**
`fractal-wallpapers curate on-demand --pass <id>` reads records only, renders
nothing, and writes identical bytes on a second run. It repairs two things that
came apart in opposite directions:

* the log carries `ledger: null` on every row written before `26c1c6a` taught the
  renderer to carry the asked-beside candidate's walk across. That commit repaired
  the 94 *shipped wallpapers* and left the log alone — and `OnDemand.__init__`
  loads its cache **out of the log**, so a resumed pass re-seats the null and
  re-creates the defect. gallery4 had 642 rows in that state;
* gallery3's 348 picks never reached the attempt store at all, because
  `extra.rows.values()` reached `write_records` in `d9a423f`, after that pass ran.
  They were on disk and invisible to `records.read_decisions(RELEASE) +
  gallery_store.read()`, which is every reader of the pool.

Both halves join on **`asked_by`** and never on the location key: an extra pick is
the same place in another palette, so the walk that found the candidate it was
asked beside is the walk that found this one. Two id namespaces are searched,
because a pick beside one of the pass's own attempts names it `4181` and a pick
beside a standing pool row names it `gallery1_0994`. The join is checked, not
trusted — a source at a different location refuses the whole run.

**There is no dry-replay subcommand, and `curate replay` is not it.** That one is
[`checks.replay`] — it re-derives every *released picture* from its own record and
is a claim about pixels. What calibrated the ceiling was a **dry replay of the
seating**: the pass's recorded candidates fed back through the seating loop at
swept settings, with the colour readings supplied rather than measured. That is
what [`ceiling.Lens`] is a class for instead of three functions — a caller can
hand the seating a different one and answer what a synthetic candidate is dominant
in without putting a render on disk. The scripts that did it were scratch and are
untracked; the seam they used is shipped, so the leg re-derives from the seam and
the pass records, but nothing on the command line runs it.

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

**The pass selects over the CURRENT admitted population.** The embedding store is
append-only and the admitted population is not, so the store is a superset rather
than a picture: 29,051 rows against 29,046 admitted, the five being locations
`curate score` re-read at the node regime and put under the junk floor.
`gallery.admitted_only` cuts the rows before anything looks at them, so a
withdrawn location is invisible to the picker and to the attempt leg at once.

**The draw is `gain = distance x location P(>=4) ** gamma`,** where `distance` is
cosine distance to the *nearest* already-chosen point. The first pick of a
partition is **drawn** from its top `--draw-top-k` (25) by that same
`quality ** gamma`, with nothing to be far from. `--radius`
(0.07) is a hard constraint under all of it: nothing that close to a chosen point
may be chosen, whatever its quality. `--quality-weight` is `gamma` and defaults to
**1** — a plain product, so a location half as far and twice as good is worth the
same; `0` is pure farthest point, which spends slots on the most isolated places
in the pool whatever the judge says. Not k-means, which follows density: this
pool's density records where the walk spent its budget, so a neighbourhood
somebody visited a thousand times would take a thousand times the slots.

**One launch per pass id, enforced at the door.** A pass claims
`artifacts/curation/runs/<pass>/pass.lock` before it reads anything, and a second
launch of the same id refuses immediately and says so. This is not tidiness: the
two launches would share one `framings/` directory, where the engine names each
frame by its position in its own batch and the caller renames it afterwards — so
each process renames the other's files and both die minutes later on a rename
that finds nothing. gallery3's first launch did exactly that. The claim is an
operating-system hold on the file rather than the file's existence, so a lock a
killed pass leaves on disk blocks nothing: the hold dies with the process however
it dies, and the resume that follows takes the id straight back. Delete the file
only if you enjoy deleting files; nothing reads it.

**The FIRST pick is seeded; everything after it is the arithmetic.** The draw
used to take `argmax` over quality for the first pick and `argmax` over the gain
for every pick after, and with no seed anywhere a pass at N=150 over the current
pool re-chose **all 100** of gallery2's points and 142 of gallery3's 150 — the
difference being gallery3's re-seats, not the draw. That is the whole explanation
for the 98 of gallery3's 150 chosen points that gallery2 had already chosen: the
deterministic prefix, not the pool's geometry. So the first pick of each
partition is now drawn uniformly from its top `--draw-top-k` (25), and because
every distance the draw measures is measured against what is already chosen, one
different start moves the whole partition. `--draw-top-k 1` is the old argmax
exactly. Swept at gallery3's knobs, four seeds each: **K=1 re-chooses 142 of
gallery3's 150 points, K=5 83–105, K=25 74–89, K=100 71–84** — and the freedom is
not paid for in point quality, whose mean `P(>=4)` runs 0.9318 / 0.9354 / **0.9365**
/ 0.9258 over the same four. K=100 is where it turns.

`--draw-seed` is the **root**, and absent it is *drawn and recorded* rather than
defaulted, because a default is how every pass over an unchanged pool comes out
the same pass again. Each partition derives its own seed off the root and the
record carries the **resolved integer** for the root and for every partition —
`config.draw_seed` and `plan.selection.<partition>.draw_seed` — so re-running one
partition's draw needs no re-derivation. Beside them the record carries
`config.draw_seed_given`, which says whether the root was typed or drawn, and
`config.draw_top_k`, because K decides how much of the pass the seed can move and
a reproduction needs both numbers. Re-running the pass needs
`--draw-seed <the number the pass printed>`. `--seed` is the other seed and they
are not interchangeable: that one reaches the palette anchors and the mode draws
in step 5, and it is on every pass record already.

**The `Draw` owns its RNG, and that is what makes a re-seat continuous.** A
re-seating slot asks the same live [`Draw`] for its *next* point, so the RNG has
to live where `nearest` and `live` live. A caller holding it would have to thread
it through every re-seat round or re-create it — and a re-created one hands the
same first pick back to a slot whose whole reason for asking is that the first
pick failed. Only the first pick of a partition is drawn; everything after it is
the gain and the radius, so a seeded pass is a different walk over one rule rather
than a randomized one.

Both numbers are by eye, and every pass prints the instrument that calibrates
them: a **retro table** of the nearest chosen pairs, per partition and overall,
read off the points the pass *ended* on rather than the ones its first draw handed
out. If two rows of it read as one picture, the radius is too small.

**Five sheets a pass, all in `scratch/<pass>_*.html`,** self-contained and
disposable:

```
<pass>_sheet.html          the gallery: partition then rank, slot-labelled,
                           unfilled slots in place, retro table at the top
<pass>_refined_pairs.html  up to 40 framings before and after, at the NODE
                           regime the head read them at, both scores under
                           each. Adopted first, then what the margin refused
<pass>_runners_up.html     per chosen point, what the radius refused, at the
                           NEUTRAL render the distance was measured on
<pass>_below_floor.html    per UNFILLED slot: the best candidate every
                           neighbourhood it tried produced, scored against the
                           floor, plus the partition's best unchosen candidate
                           on the same head POOL-WIDE — the proof of whether the
                           partition held supply the slot never reached
<pass>_closest_pairs.html  the 12 closest chosen pairs across ALL partitions,
                           side by side with their cosine distance. The retro
                           table's eye-check; a filled slot shows its wallpaper
                           and an unfilled one its point's neutral render
```

Under `--no-full-size` the two sheets that show wallpapers show each winner's
candidate render instead, captioned with the resolution it actually is.

**Both measured floors act here, and only one of them acts at a run's release.**
`floors.gallery_floor` is that seam and it is the one place in this project where
a head's cut reads differently at two sites: `ACTING_RELEASE_BARS` still answers
*does this kind gate a run's release* and the smooth answer there is still
no, while the pass reads `MEASURED_RELEASE_FLOORS` on both kinds. **The heights
are not written down on this page.** They are re-fitted at every judge flip and a
number narrated here goes stale silently — read the stamps: the `Restatement`s in
`floors.py`, the records they were fitted from at
`models/render/release_floor_<kind>.json`, and the one live pair in
[`models/render/README.md`](../../../models/render/README.md). `head floor --head
<kind>` re-fits and refuses when a standing height does not reproduce. The two
questions are different. A run's release is ten diagnostic
pictures out of one night, and a bar there decides how much of that night is worth
looking at; the pass decides what the collection ships out of everything, and a
slot it cannot fill above a measured floor **after every re-seat it is allowed**
is a fact about the pool. **Unfilled beats padded**: an empty slot is output with
its binding reason named, because it is the signal for where to label or walk
next.

Whichever cut a site reads, it reads it against a **live** score rather than the
one the night wrote: `records.live_reading()` prefers a row's `scores_current`
block, and that block carries `judge` (the artifact that produced the numbers)
beside `head` (the row's KIND, which is what picks a floor and a slot). Both are
the [record store](../../../data/curation/README.md)'s to explain and are not
restated here.

**A row without that block is not a row without a reading, and asking the wrong
one of those questions cost a reader two thirds of the pool.** A gallery pass
writes `scores_current` onto its release rows only, so gallery3's and gallery4's
10,846 attempt rows carry no such block — while their pass records say
`config.heads.render` was the artifact shipped today, which means their `scores`
block *is* the live reading. `rescore.artifact_of(row)` is the one place that
answers **which artifact a row's comparable reading stands on**: the current
block's own `head_sha256` where there is one, and the run's or pass's own summary
where there is not. `rescore.reading_on(row, stamp)` is that check in front of
`live_reading`, and it is what a floor-referenced population qualifies on.

Not the row's `bar.head_sha256`. That is the artifact the bar's **height** was
measured on — `floors.release_cut` builds it that way deliberately — and reading
bar provenance as score provenance is right by coincidence on today's rows and
wrong the first time the two come apart. Run summaries abbreviate the stamp to
sixteen hex characters and floors carry all sixty-four, so the comparison is a
prefix match on the shorter of the two.

**The pass has a colorize leg, and every chosen point gets both heads' attempts.**
`--attempts m,smooth,strange` (3,2,6) buys, for each chosen point, the top `m`
locations in its own radius by `P(>=4)`, each under `smooth` attempts on distinct
palette anchors and `strange` attempts on distinct modes — 24 attempts a slot,
about a minute. The attempts are **pool rows**, stamped with the pass id, so the
pool grows by every one of them; the plan is taken over the *union* of every
slot's locations, because two overlapping neighbourhoods asking for one location
would otherwise render the same pictures twice (the mode draw is seeded off the
location and the head). A re-seat **extends** that plan rather than rebuilding it
— an attempt's identity is its position in the plan, which is what the candidate
log resumes on and what the palette anchor is drawn on — so a killed pass resumes
every attempt back onto its own picture. The 31 palette candidates that lost are
deleted after the verdict — the row keeps the whole candidate set by name and the head's score for
each, which is what a later reader needs. `--no-attempts` skips the leg and is a
**dev affordance only**: candidates are per-pass, so a pass with no attempt leg
has nothing at all to seat and every slot comes back unfilled. What it still takes
whole is the selection — the slots, the head split, the point draw, the retro
table and the two embedding sheets — for the price of no render.

**Step 5a: the pass decides where a location is framed before it colours it, and
it is ON.** A walk stops on a frame because the gates let it through and the head
liked it, not because that is the best crop of what is there. So before a
location's attempts render, `curation.framing` scans a small window around the
frame the pool records — width `x{0.707, 1.0, 1.414}` at the current centre, then
at the best of those a recentring of `+-0.25` frame one axis at a time — draws
every one of them through `engine.screen` at the **node regime**, reads them
through the shipped location head, and adopts the best **only if it beats the
recorded framing by `--refine-margin` on `P(>=4)`**. Seven frames a location. It
is a strict improvement and never an argmax: an unmargined best-of-seven over
correlated reads of one place wins by construction whether or not the head can
tell the seven apart. Monotonicity is asserted rather than assumed, and a
violation raises and stops the pass.

**Only the frames that go on to attempts move.** The slot allocation, the
farthest-point draw, the hard radius and the neighbourhoods are all decided on
unrefined geometry, because the embedding store holds one vector per location at
its *recorded* framing and a picker choosing off refined geometry would be
choosing distances nobody has measured. The location's identity does not move
either: the key is unchanged, and one-wallpaper-per-location and the
near-duplicate grouping both still key on the **original** viewport, so a
location the pass widened by half cannot take a second seat beside itself. Every
attempt row and every gallery row carries **both viewports and both of the head's
readings**, under `framing`, and step 7 renders the refined one.

**The fallback, before an empty slot is allowed to count as failed.** A slot whose
every attempt landed under the bar was attempted on frames the pass *moved*, so
its refined locations are attempted once more at the framing the record holds —
same modes, seeded off the same location and head, so the two are a comparison
rather than a second roll — and the whole seating is taken again. Only then does
the slot re-seat. It costs nothing on a pass whose framings did not move.

**Priced per pass and never by an A/B leg**, the way the audit that proposed this
insisted: locations scanned, frames, seconds, the winner-not-original share, the
chosen-width and chosen-move histograms and the whole Δ distribution go in the
pass record under `refine`, and the per-location detail is a row each in the pass
directory's `framings.jsonl` — untracked, resumable, and never re-scanned by a
later re-seat round. `<pass>_refined_pairs.html` is the verdict that actually
matters: up to forty framings before and after at the node regime, adopted first,
then the ones the margin refused, which is the only way to see whether Δ is set
where it should be.

**Δ is in log-odds, and that is a measurement rather than a taste.** The margin
acts on `P(>=4)` — the statistic the pass seats by — but on the **log-odds** of it,
because the population this step actually sees is the pass's own neighbourhoods
and those are the strongest locations the pool holds. Over the first twenty
scanned, `P(>=4)` at the recorded framing ran **0.9285 to 1.0000, median 0.9998**.
An absolute margin there refuses everything however much better a framing is: a
Δ of 0.05 on the probability adopted **0 of 20**, and so did every Δ down to
0.005. The same twenty framings spread **-1.69 to +6.05 nats**. It is a monotone
re-scale, so the ordering, the `P(>=3)` tie-break and the monotonicity assertion
are the same claims they were.

**The default is 2.0 nats — a factor of 7.4 in the odds — and the flip rate is why
it is not lower.** The shipped location head is the **regime-robust** one adopted
on 2026-08-20 (`seed0_all_regimes`, `f8f80511...`, `weights-v2`), whose pooled
node-regime flip rate is **4.56%** and whose great-cut flip rate is **1.58%**. The
10.36% figure beside it in `src/fractal_wallpapers/models/README.md` is the head
that *retired* that day. On the first twenty, 2.0 nats took 7, 3.0 took 3 and 1.0
took 8.

**The `x1.0` rung is rendered rather than taken free, and the first scan is why.**
The design counted it free because the supply sidecar already holds that frame's
score at that regime. It does not agree: over the first twenty locations the
scan's own read of the recorded framing matched the sidecar on **6**, and the
largest gap was **0.0288 on `P(>=4)`** — more than the whole probability margin
that was originally proposed. The head is deterministic (batch shape moves a read
by 1e-7), the artifact is the same, and a fresh `location_view` render of the
frame is **byte-identical** to the scan's and scores identically. So the gap is a
fact about the picture the sidecar's number was read off — for 19 of the 20 a
walk's own gate render, which is not on the view-cache path and cannot be
re-checked. `identity.enforce` pins four settings and the engine build is not one
of them. Worth chasing; until then the pass measures rather than inherits, and
reports the agreement on every run.

**The margin was calibrated on the pass's neighbourhoods, and the pool is the
other end of the same scale.** A scan of every admitted location on 2026-08-26 —
28,090 of 29,051 embedded, 961 under the junk floor, 196,630 frames in 3.37 h —
put median `P(>=4)` at the recorded framing at **0.0009**, against the 0.9998 the
paragraphs above are measured at. Both ends are where log-odds has resolution and
the probability has none, so the same Δ 2.0 that took 26.9% of gallery4's 751
seats takes **67.8% of the pool**. Those adoptions are mostly real — the median
adopted location goes `P(>=4)` 0.00048 to 0.106 — but 30% of them move a location
from under 0.01 to under 0.01. **A refinement rate quoted off a pass does not
transfer to the pool, in either direction.**

**Where the pool-wide record lives, and how to make it again.** One row per
location under `artifacts/curation/frame_refit/scan.jsonl` (untracked, ~98 MB):
every rung of the window with its gain in nats, `P(>=4)`/`P(>=3)`, gate fate,
whether it was adoptable, and its viewport and cap — plus the winner, the verdict
at the standing margin and the refusal reason. Keeping every rung is what lets the
margin, the rung set and the width policy be re-decided without re-scanning; the
margin sweep from Δ1.0 (80.6% adopted) to Δ4.0 (41.3%) is a read of that file and
costs nothing.

```
python scratch/frame_refit_scan/scan.py            # resumable; --limit N, --out PATH
```

It is chunked 250 locations, **resumes by subtracting the location identities
already in the record** — never filenames or chunk indices — and names each chunk
directory by a digest of its own keys, so two runs at different chunk sizes cannot
collide. It closes by asserting the measured identities equal the intended
population and printing per-partition coverage; a shortfall exits non-zero rather
than reporting success.

**Price per partition, not pool-wide, and measure rather than model.** Render cost
does not follow the iteration cap: `phoenix` costs **1.7x** what its median maxiter
implies and `mandelbrot` **0.6x**, and `mandelbrot` at 26,912 median ran at 0.432
s/location against `julia:mandelbrot`'s 0.344 at 2.5x fewer iterations. Fixed
per-location overhead — JPEG encode, head read, engine launch — is about **70% of
a cheap location's cost**, so scaling a whole anchored rate by a power of maxiter
overstates the dear partitions roughly 2x. Order a long scan cheapest partition
first and an overrun then costs the dearest partition's tail rather than an
arbitrary slice of every one.

**`--no-refine` is the leg this repository had before the step existed**, exactly:
the same plan, the same seed, the same anchors, the same mode draws and the same
frames. `tests/test_curation_framing.py` pins that, along with the window
geometry, the margin refusing a planted sub-Δ winner, and the monotonicity abort.

**`--no-full-size` skips step 7 and costs the pass no decision.** Every slot is
seated on the same candidates; what is not spent is a release render of a choice
that is perfectly judgeable off the 640x360 render the head itself read. The seats are recorded **`unrendered`** — took the slot, no
picture, **nothing failed** — which is a fourth release verdict and not `killed`,
because `killed` means the render died and a reader has to be able to take a
verdict at face value. `records.served` still wants a picture, so an unrendered
seat can never become a link to nothing. Re-running the same `--pass` without the
flag renders the winners and lifts the rows to `released`: the attempts are all
still on disk, so the second invocation costs the release leg and nothing else.
Contrast `--no-attempts`, which removes material the pass would have decided over
and so changes every number it reports.

**One wallpaper per location acts inside the pass and the served index is not
read.** A run is excused from the index because it has the wrong population; the
pass has exactly the right one and is excused for a different reason — a pass
chooses the whole gallery at once and **supersedes** the previous one, so a pass
that refused every place the last pass shipped could not re-choose its own
gallery, and one that refused every place a run's diagnostic release sits on would
hand the collection's best locations to the ten pictures a night kept to prove its
path worked.

**The pool is deduped on the picture, not on the row.** One render lands on as
many rows as there are decisions about it: the run that made it, the pass that
seated it out of the pool, the pass that seated it again. Each of those rows
carries its own `<run>_<candidate>` name, so a pool keyed by name ranks the same
wallpaper twice and can seat it into two slots. `gallery.picture_id` resolves a
row to the render it is about by walking `source` all the way down —
`rescore.origin_of`, the same walk that finds the picture on disk — and a seat is
stamped with *that* id rather than with the id it was read under, which is what
stops the name growing a level per pass. It used to: `gallery2_0110` became
`gallery3_gallery2_0110` and would have become `gallery4_gallery3_gallery2_0110`,
and on 2026-08-24 that had 90 of the pool's 8,313 seatable rows standing for 87
pictures, three of them present three times. The rows on record are not rewritten
— a decision is a decision — the reader resolves them.

**The pass's pictures live in the run tree** (`artifacts/curation/runs/<pass>/`),
deliberately: `curation.rescore` finds any pool row's candidate render at
`runs/<run>/pictures/<candidate>.jpg` off the row's own `run` field, and a pass
that stored its pictures elsewhere would be a pass whose rows the next re-score
refuses to read. Both contact sheets are written to `scratch/`, self-contained
with their thumbnails embedded.

## The candidate ledger: what we have already made

A pass renders candidates, seats a few of them, and keeps a decision about each.
What it has never kept is an answer to the question a *solver* has to ask before
it does anything: **have we already made this picture?** The propose-then-solve
build starts here, and this is its first piece — a type that names a picture, and
a durable store of every picture named.

```
src/fractal_wallpapers/curation/recipes.py           the type, and the key
src/fractal_wallpapers/curation/candidate_ledger.py  the store, the backfill, the census
artifacts/curation/candidate_ledger/rows.jsonl       one row per recipe
artifacts/curation/candidate_ledger/scores.jsonl     one row per (recipe, judge, regime)
data/curation/candidate_ledger/rows.manifest.json    what the history keeps of the first
data/curation/candidate_ledger/scores.manifest.json  ...and of the second
<archive>/curation_backup/candidate_ledger/*.jsonl   the durable copies
```

```
fractal-wallpapers curate candidate-ledger backfill   # from what already exists
fractal-wallpapers curate candidate-ledger census --n 20 --out scratch/ledger_census.json
fractal-wallpapers curate candidate-ledger save       # both files, both manifests
fractal-wallpapers curate candidate-ledger check      # are they whole
```

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

## `curate solve` — the gallery as a program, not as a walk

The ledger above is the proposal side. This is the other half: the selection
stated as a **mixed-integer program** over it and handed to HiGHS, so the answer
is optimal under the rules rather than optimal-given-the-order-the-walk-took.

```
src/fractal_wallpapers/curation/solve.py       the program, the loop, the shortage list
artifacts/curation/solve/<name>/solve.json     the record: config, rounds, seats, spread
artifacts/curation/solve/<name>/release/       the seats at release geometry
artifacts/curation/solve/<name>/contact_sheet.html   the twenty, and what they beat
```

```
fractal-wallpapers curate solve run --n 20                   # one gallery, rendered
fractal-wallpapers curate solve run --n 20 --no-render       # decide, render nothing
fractal-wallpapers curate solve run --n 20 --locations 40    # only the 40 best places
fractal-wallpapers curate solve run --n 20 --target dark_vivid_lime=1.0   # a hard colour demand
fractal-wallpapers curate solve sweep                        # which constraint binds first, and at what n
fractal-wallpapers curate solve sweep --sweep-seconds 3600   # a longer ladder
fractal-wallpapers curate solve truncate --n 20              # what a smaller reachable pool costs
```

It needs SciPy's HiGHS binding, which is the `solve` extra (`pip install -e
.[solve]`) and not part of the base install. The leg loads no head: every score
it reads is off the ledger's sidecar, so a machine that solves does not need the
CUDA wheels.

**The objective is lexicographic**, three solves with each stage's value frozen
into the next: how many seats clear the q4 bar, then the **floor** — the lowest
score among the seated, maximized — then the sum, less the mode-floor penalty.
The floor stage is the one that matters: a gallery of twenty where nineteen are
excellent and one is a mistake is worse than one where all twenty are merely
good, and a sum cannot say so.

The q4 bar is **raw `P(>=4)` at 0.50**, which is the natural rank cutpoint of a
CORN probability and explicitly not a measured crossover — both release heights
this project has fitted are `P(>=3)` and neither transfers to a different
cutpoint. It is recorded on every solve so a count taken across the change names
its own bar.

**The pairwise rules are generated, never materialized.** The diversity radius
and the group cap are statements about a pair of finished pictures, and the
ledger holds 118 million pairs at 512 KiB a signature. So: solve without them,
look at the pairs, add a row for each violated pair, solve again. It terminates on
an incumbent that violates nothing, and that answer is optimal for the whole
program — the generated program is a relaxation, so its optimum bounds the full
one's, and the incumbent attains that bound while being feasible for it. At N=20
over the whole pool it converges in **two rounds**.

**The location-level prune does not work, and this is why.** The design was to
skip pairs whose *places* are far apart on the ground that they cannot be
near-duplicate pictures. Measured over 79,621 cross-location pairs drawn from the
pool's top two thousand: 1,350 of them are closer than 0.07 as pictures, and the
furthest-apart pair of places that makes one sits at cosine 0.583 — past the 90th
percentile of location distance. The metric is over a picture's **colour cloud**
and colour comes from the map rather than from the place, so two unrelated frames
through similar ramps are near-duplicates by construction. A cut at 0.40 would
still keep 91% of the pairs and miss 96 real violations. **A correlated proxy is
not a prune.**

**The metric admits a real one.** It is a mean of absolute differences over
`DIRECTIONS * QUANTILES` numbers, so the triangle inequality bounds it from below
out of a summary of each cloud: group the quantiles into `solve.BOUND_BLOCKS`
blocks and, per direction and per block, the mean of `|a - b|` is at least
`|mean a - mean b|`. At one block that is exactly the distance between the two
clouds' **mean colours**; at `QUANTILES` blocks it is the metric itself. A pair the
bound puts at or beyond its own threshold *provably* cannot violate, so it is
never measured and never generated. Measured over 79,800 pairs from the same
population, at the 0.07 radius:

| blocks | bytes a signature | settles | survivors per real violation |
|---|---|---|---|
| 1 | 4 KiB | 95.4% | 2.7 |
| 2 | 8 KiB | 97.4% | 1.6 |
| **4 (shipped)** | **16 KiB** | **97.9%** | **1.2** |
| 16 | 64 KiB | 98.3% | 1.0 |
| 128 (the metric) | 512 KiB | 100% | 1.0 |

What that buys is not mainly the arithmetic. It is that a round can screen every
pair among **everything a signature has ever been made of** — the greedy seed's
rejects and every earlier incumbent — instead of the incumbent's own pairs alone,
so rows arrive many rounds before the incumbent would have found them. It also
uncouples the signature cache from `n`: a round no longer compares every seat with
every other one in the full metric.

**A greedy walk seeds the cut pool, and never ships an answer.**
`solve.seed_greedily` seats down the ranked list and keeps every pair it refuses.
Those pairs are valid rows of the full program however bad the walk's own gallery
is — two pictures under their threshold can never both be seated, whoever noticed
it — and where the walk fills every seat, its own minimum score is what fixes stage
2's columns. It is never a shipped alternative to the exact solve: sequential
seating is what this design replaced, and it hides exactly the failure the n=1.1N
truncation exposed.

**Stage 2 was the whole cost of a round, and an incumbent is what removes it.**
Measured at n=60, an 11.1 s round was 1.1 s of stage 1, **9.8 s of stage 2** and
0.2 s of stage 3. Stage 2 maximizes the minimum seated score, and `t` has no lower
bound in it, so no presolve can tell HiGHS that a candidate scoring 0.4 is not
going into a gallery whose floor is 0.97. Any feasible solution that clears the
same count says so: the optimal floor is at least that solution's own, so no
optimal solution seats anything below it, and every such column can be fixed to
zero without removing an optimum. 15,955 free columns become 305, and 9.8 s
becomes 0.36 s for the same floor to twelve places.

**Continuing one live model does not help, and that was measured rather than
assumed.** The obvious next move is to stop rebuilding: hold one `highspy` model,
append the generated rows, and continue from the existing basis. HiGHS gives a MIP
no warm start. Over eight rounds at n=60, one live model with rows appended took
14.82 s against 14.87 s for a fresh build each round, and handing stage 1 its own
answer back as a MIP start moved it from 1.36 s to 1.31 s — the time is in proving
the bound, not in finding the incumbent. `scipy.optimize.milp` has no warm start to
give, and neither does the C++ interface underneath it, so the solve stays on SciPy
and takes on no second solver dependency.

**The sweep carries a clock, and says where it stopped.** A round cap bounds
rounds and not time, and the two are not the same thing: the rounds grow with `n`,
and so does the pool of pairs each of them screens. The shipped ladder stops at
**160**, which is where this project has measured; the whole run stops at
`--sweep-seconds` (1,200 by default) and the record names the rung it did not
reach. `relaxation_ladder` carries the same question to the top in seconds, on
every block except the two pairwise ones — and its answer is exact: **1,223**, the
location count, with `one_per_location` the block that runs out.

**Infeasibility is a shortage list.** A program that cannot be solved does not
raise: an elastic LP gives every relaxable row a slack and minimizes it, so the
answer says *how many candidates short* each block is, and a deletion filter over
the blocks says which of them are irreducibly in conflict. The partitions holding
each short colour are on the readout too, because that is what launches a
conditioned hunt. Under-fill is the same fact one seat smaller: the cardinality
row alone goes from `== n` to `<= n`, nothing is relaxed, and the empty seats stay
on the record.

**And sometimes it is not a shortage at all**, so `shortage.verdict` says which
kind it is. Both instruments are LPs, and a program whose LP is feasible while its
MILP is not has nothing short: the elastic read comes back at zero slack and the
deletion filter — which can only ever name a conflict the relaxation has — would
otherwise return every block, a list of six that reads like a finding and is not
one. It returns `[]` there instead, and the verdict names the integral cause: with
pairwise rows standing, the diversity radius is refusing the *combinations* rather
than the pool refusing the colours, and no hunt for more of a colour relieves it.

**`--target <cell>=<fraction>` is a hard demand**, and it also raises that cell's
and its family's ceiling allowance through `ceiling.Rule` — otherwise a demand
would be refused by the ceiling it asked for.

**And it raises the allowance of the cells it structurally implies.** A carrier of
one colour is dominant in more than one: on the reference fields a
`dark_vivid_lime` delivery lands `dark_muted_lime` 42% of the time,
`light_muted_lime` 34% and `dark_vivid_green` 8%. So a target that raised only its
own cell pushes its own seats against its companions' untargeted allowance of
three, and the program is infeasible for a reason nobody chose — which is exactly
where the lime hunt's shortage moved once the target itself was met.
`ceiling.Rule` raises a companion's share by `target x the measured co-dominance
rate`, and the companion's family by the same unless it is the target's own family
(which the target already raised, and which counts a picture once however many of
its cells that picture is dominant in). The rates come from
`palettes.carriers.co_dominance` over the tracked table's own deliveries, never
from an adjacency written down off the hue wheel. `config.ceiling.implied` on a
solve record and on a pass record says what moved.

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
scanned pool that carry no ledger recipe at all, `--per-location` candidates each,
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

**The frame is looked up, not recomputed.** Everything renders at the frame the
pool-wide refinement scan chose at `framing.MARGIN` — the winner where it adopted,
the recorded frame where it refused. `curate hunt frames` derives a thin index
(one row a location, 28,090 rows, about two seconds) off the 98 MB scan record, and
a scan row taken at another margin is **refused** rather than reinterpreted: the
margin belongs to that record, and re-deciding it is a read of every rung. Because
the frame is part of the recipe, a candidate stays valid if the margin later
moves — what a moved margin invalidates is where to draw next, not what was drawn.

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

## One field, many palettes — how a candidate is made

**`colorize.render` is still THE one place a curation picture is made, and it now
has two ways of making one.** Which one serves a candidate is not a caller's
decision and no caller can see it:

* a **field** coloring — seven of the eighteen production modes — is dumped once
  per `(location, mode)` into the unit of work's own `fields/` directory, and
  every palette at that pair is an `engine recolor`: a colormap lookup over an
  array on disk, with no iteration behind it;
* a **composite**, the **modulate** and the **direct traps** have no single scalar
  field, the engine refuses to dump one, and those take the full render they
  always did. The refusal is remembered against the mode, so a mine that draws
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
forty candidates is about 175 s a location — one arm's worth of places would eat
a ninety-minute budget — so the roster is `depth.field_modes()`: the shareable
production modes less `DEMOTED`. Nothing a depth run reports says what a
composite would have done.

**`trap_circle` is out of the draw and still in the catalogue.** The demotion to
niche is a ruling (checkpoint 84: 2 threes and 0 fours in 117 labeled rows) and
the engine's tier still says production, so it is applied at the draw through
`depth.DEMOTED`. Existing material in it stands.

**`tia` is out of BREADTH and still on the near band.** Two rulings, two
constants: `DEMOTED` takes a mode out of the run entirely, `BREADTH_DEMOTED`
takes it out of the ranked and flat draws and leaves it eligible as a near-band
incumbent. `tia` is the whole of the second list. It cleared the seating bar at
.0208 in breadth at k=20 against `smooth`'s .0515, and at k=40 it cleared .0559,
level with them (`dc1`/`dc2`, 2026-08-27) — its clears concentrate at few places,
so a narrow set at many places wastes it. It is also the dearest dump of the
three-mode roster, 0.898 s against `smooth`'s 0.354, and the field is dumped once
per (location, mode): about an hour bought back over an eight-hour run.
`--breadth-demoted` overrides it; `--breadth-demoted` with no values cycles the
whole roster. Note that `--modes` is the wrong instrument here — it is the roster
a near-band incumbent must also be in, so narrowing it drops the mode from both
draws.

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
fractal-wallpapers curate shrinkage --name d1 --per-arm 20 --workers 6
```

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

## What a pass puts in the history, and what it puts beside it

**Everything a pass tracks scales with `n`; nothing tracked scales with the
attempts.** That is a rule, it is measured on every pass, and
`tests/test_curation_gallery.py` pins it on a synthetic N=500 plan by writing the
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

`gallery.read_pass` puts the record back together — the summary with its slots
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
it took itself: `gallery.pool_candidates` keeps a pool row only where the row's
maker is this pass, which in the normal path is none of them. gallery3 seated 66
of its 150 slots on standing rows and in 59 of those the standing row merely
outranked the pass's own best at the same place — the pass had made something
there every time. With a deterministic draw putting 98 of its 150 points where
gallery2 had already looked, seating another pass's recolours was running half the
draws and calling the older half free.

**`gallery.pool_rows` stays outside that rule and reads both stores** — the
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

**`curate gallery` refuses the pre-split layout** — a tracked gate directory under
the pass id, or a passed-over release row in the history — before it spends
anything, because a pass run over it would upsert its winners into a directory
still holding every attempt the old code passed over. `curate gallery --pass <id>
--migrate` moves one pass across: attempt rows into the new store with its
manifest, the release directory rewritten to the winners alone. It reads and
writes records only and renders nothing. It is idempotent.

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
(**24,779** today), one **neutral render** through one fixed cyclic map at one
fixed small geometry, and the unit vector a frozen DINOv2 reads off it.

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
*default* rather than a constant: `gallery.RELEASE_REGIME`, moved by
`--release-regime <w>x<h>ss<n>`, with `gallery.FORMER_RELEASE_REGIME`
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

**`curate draw`** is step 4 alone: the point draw, claiming no pass and writing
nothing. `gallery --no-attempts` is the affordance for iterating on a pass; this
is the one for *comparing two selections*, which needs a selection that claims
nothing so both sides can be taken over one pool in either order.
`--no-amended` takes it over the standing scores, and the difference between the
two chosen sets is the entry bias the stale readings were buying. On gallery3's
settings (`-n 150 --radius 0.07 --quality-weight 1 --strange-share 0.6
--draw-top-k 1`) the standing-score draw reproduces **142 of gallery3's 150
seated points**; the eight that differ are the slots that re-seated.

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
fractal-wallpapers curate coverage --step probe --workers 6
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
maps, is 16,912 recolors at about 75 ms each: 21 minutes serial, about 6 with
`--workers 6`. The panel's own dumps are 56 iteration passes, about 40 seconds.
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
