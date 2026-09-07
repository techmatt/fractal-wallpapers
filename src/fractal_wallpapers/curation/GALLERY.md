What a seat may be refused for, the leg that fills the seats, and the upper bound
that leg is measured against. Split out of [`README.md`](README.md), which keeps the
architecture, the stores and the module index; the readings the sections here quote
are in [`MEASUREMENTS.md`](MEASUREMENTS.md), and the legs that make what this chooses
among are in [`LEGS.md`](LEGS.md).

## The pre-solver gallery pass, and what took its place

**Deleted on 2026-08-28**, ruled at ckpt 87. The command was spelled `curate
gallery` — a spelling this project no longer has, and **not** today's `curate
solve record`, which is a solve and not a draw. It was the second
phase: a quality-weighted farthest-point draw over the neutral embeddings picked
N locations, each chosen point bought a small judged attempt on its own
neighbourhood, and a sequential walk seated the winners under two floors, the
one-wallpaper-per-location rule and the colour ceiling. Four passes ran under it —
`gallery1` through `gallery4` — and **what they wrote is now their winners and
nothing else**: the rows in `data/curation/release/<pass>/`, and 14,316 rows in
the candidate ledger. Their pass records, slot rows, manifests and attempt store
were retired on 2026-09-06, Matt's ruling. Two things were established before
deleting: the numbers a doc priced a full-size leg off already sit in
[`MEASUREMENTS.md`](MEASUREMENTS.md), and no label row in any store resolved
through that store — all 26,066 of them resolve on their own join, `n_unkeyed`
zero in every store before and after.

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

Three commands went with the phase: `curate gallery` itself, `curate draw` (its step-4
point draw alone) and `curate on-demand` (the reconciliation of a pass's
extra-pick log with its attempt store, which had already run on every pass it was
written for). `curate gallery-store` outlasted them by nine days, because the four
passes' attempt rows were about a third of what the ledger's backfill could reach
— and it went on 2026-09-06 as well. What that costs is stated at
[`candidate_ledger.rebuild`](candidate_ledger/rebuild.py): a rebuild from scratch
would now produce a ledger short those rows. The rows already in the ledger are
untouched, and the ledger is durable, mirrored and checked, so a rebuild is not a
path anybody should be on.

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
twin        no picture within 0.034281 of two already-shipped ones
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
fractal-wallpapers curate solve run --n 1000 --no-render     # 52 s + ~19 s pool, measured
fractal-wallpapers curate solve run --n 2000 --no-render     # THE planning size (Matt)
fractal-wallpapers curate solve run --n 150 --no-swap        # the greedy seed alone
fractal-wallpapers curate solve run --n 150 --swap-seconds 300   # a clock on the loop only
fractal-wallpapers curate solve run --n 150 --flat-floor     # the pre-2026-08-31 mode floor
fractal-wallpapers curate solve run --n 150 --group-cap identity --key p_ge4 --spiral-cap none  # the incumbent
fractal-wallpapers curate solve run --n 150 --spiral-cap none     # no spiral share cap at all
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

### The six steps

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
5. **Augmenting chains** (`curation.augment`), `--augment on` unasked. One seat
   out and **two** in — the only stage that can move tier 1, because a 1-swap
   conserves the seat count and every unfilled seat was therefore the seed's.
6. **1-swap improvement again**, over the augmented gallery. It cannot lose a
   seat, so what it recovers is part of what step 5 spent.

**It is anytime at every step.** The gallery is valid from its first seat, so a
clock, a `Ctrl-C` or a pass cap leaves an answer rather than nothing. That is the
whole reason it replaced a method that had no answer at all until it had a proof.

### The record carries the whole reach funnel, so asking how far a solve reached needs no solve

**How much of the pool a pass actually saw is already written down.** Every
`solve.json` since 2026-08-31 carries a `population` block — `candidates`,
`clearing`, `after_the_preselection`, `in_the_view`, and the same three at
location level — which is the funnel from the store to the rows the leg could
seat, stage by stage. Beside it `diversity` carries the twin rule's own counters:
`candidates_tested`, `seat_comparisons_settled_by_the_bound` and
`...by_the_norm_screen`, `full_signatures_fetched`, `signatures_made`,
`reduced_from_the_sidecar`, and the constants the reduction ran at. `pool` and
`view` complete it — `refused` by cause, `reachable_locations`, and the view's
`per_stratum` breakdown.

The consequence is the point: **a question about reach is a read, not a leg.**
Nothing here needs the pool loaded, which matters under the one-pool-holding-
process rule — and re-running a solve to find out what an old one reached would
answer about today's store rather than the one that was there.

⚠ **"Every" needs its date.** 110 of the 121 records under
`artifacts/curation/solve/` carry both blocks; the 11 that do not are the
2026-08-26 set and `cc_before` / `cc_after` of 2026-08-31, all of which predate
them. And `diversity` is `None` by shape when a pass ran with no diversity rule,
though no record has actually been written that way.

### The augmenting chain — the stage that raises the seat count

A **level-preserving** move is exactly a 1-swap; the **terminal** move is a free
insert. So a chain of depth `k` is `(k-1)` swaps then one insert, and it is worth
**+1 seat**. Depth 2 is eject one and insert two; depth 3 is one more eject/insert
pair. `--augment-depth` takes 2 (default) or 3.

**What it reclaims is the colour the greedy overspends.** `READ_solve_bound` priced
the greedy at 1.96 cells a seat against an integer program's 1.80; the chains eject
3- and 4-cell seats and insert 1- and 2-cell rows. At n=750 every one of the 34
ejections was a 3- or 4-cell seat and 67 of the 68 entering rows were one-cell, for
a net colour footprint of −51.

**It is accepted by tier 1 alone, and it pays in the three tiers beneath.** A +1
chain wins the seat count strictly, so nothing below can refuse it — that is the
tier order working as ruled, not a hole in it. On the pool of 2026-09-04, before →
after the whole leg: at **n=750** 716 → 750 with the worst seat and the shortfall
both untouched; at **n=1000** 911 → 1000 with the worst seat 0.188159 → 0.093308
and the shortfall 0 → 3; at **n=2000** 1,621 → 1,930 with 0 → 13. The entering rows
sit around a 0.31 median rank key against 0.50 for the seats they displace — two
weaker wallpapers for one better one. Step 6 exists to buy back what it can, and at
n=1000 it buys all of it: the **shortfall goes 3 → 0** on the second swap loop with
the sum above the incumbent, so only the worst-seated tier pays for the chains.

**The seat count is carried by the stage and not by `rules.State`.** `refuses`
answers "may this sit beside the seated" and `n` is not one of its rules: the seed
carries `gallery.full` itself and the swap loop never needs to. This is the first
caller that *raises* the count. Unguarded at a rung where the pool fills, it took
94 chains and reported **194 seats of 100**, every one legal under every rule
`rules.py` holds. `augment.FULL` is spelled apart from `rules.RULES` because `n` is
the leg's budget and never a fact about the wallpaper.

**The diversity rule is asked once per candidate, not once per trial.**
`Twins.within` answers against the seated set as it stands, and ejecting only ever
removes rows from that answer — so `c` is admitted after ejecting `E` exactly when
`near[c] ⊆ E`. That turns the one expensive rule into set arithmetic. The asking is
**lazy**: only the rows every counted rule already admits are asked up front,
because the inversion is built from them (1,645 of 11,407 insertable at n=1000);
the rest are asked the first time a chain reaches one.

**`--augment-seconds` is a budget on the stage alone** and it stops at a chain
boundary, never inside one. The default is 300 s, which is a measurement: the
search exhausts in 1.0 s at n=750 and 5.8 s at n=1000, so it never binds at the
shipping rungs, while n=2000 ran 574 s without exhausting and there it binds and is
meant to. **The readout says which happened** — `exhaustive` on the depth block is
the difference between *no chain of depth ≤ 2 exists* and *none was found in the
time given*, and the blockage block is only interpretable beside it.

**At n=2000 it is a budget question and the exhaustive cost is unknown** — over
30 minutes, and nothing has run it to the end. What dominates there is the **chain
search and not the diversity rule**: the search is **40% of augment time at n=2000
against 91% at n=1000** [measured], so the next speedup at the larger rung is in the
search rather than in `Twins.within`. The shipped stage seats 1,795 at 300 s and
1,984 at 1,800 s, neither exhausted and no mode short.

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

### The sweep belongs at BOTH ends of a mining leg

`curate signatures sweep` is cheap and incremental, and the trap is treating it as a
thing you do before a leg. It is keyed on the **picture**, so a leg that merges tens
of thousands of new clearing candidates leaves the sidecar answering for a pool that
no longer exists, and the next solve derives the difference *inside itself*, serially,
one decode at a time.

Measured, `MINE_overnight_full_roster_centered` 2026-09-02: the sweep ran as a
pre-step at 18:28 and left 11,919 rows; the leg then took the clearing pool
11,711 → **15,546** and the post-preselection view 9,864 → **13,198**. The n=2000
solve that followed ran **2,185 s against the same solve's 618 s** the day before. The sweep run
afterwards read the difference — **3,835 rows in 31.53 s** over three workers — which is what the
solve had been doing one decode at a time.

So: sweep before the leg *and* after the last merge. `curate signatures coverage`
answers whether it is needed in one pass and costs nothing.

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

It is regenerable — **65.4 MB, 11,454 rows, 103 s** over the standard three-worker
pool with nothing unreadable, read 2026-09-01 and **253 MB over 44,346 rows** by
2026-09-06, the regeneration scaling with it — and it is mirrored anyway, through a
`durability.Durable` of its own that `merge` saves with the other three. The
argument that kept it out was size: it was 247 MB and 448 s until
`pixel_clouds.DIRECTIONS` came down to 256 on 2026-09-01, and a reduced signature
is 4 KiB now rather than 16. At a quarter of the bytes, a copy is cheaper than the
re-derivation a restore would otherwise pay.

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

**Where it earns its size is `curate headroom --twin`**, which builds one
reduced signature per place to screen millions of pairs and needs a full cloud only
for the few thousand survivors — so nothing cancels. Measured over that sweep's own
population, 4,496 places after the neutral pre-selection: the sidecar answers **all
4,496 in 0.7 s** against **429 s** to decode them at 95 ms a picture — both measured at
1024 directions; a signature is 16.8 ms now, so the same sweep would decode them in about
75 s and the sidecar's edge there is far smaller than it was. That sweep used to build
every one of them and throw them away.

### Three prunes in the swap loop, and all three are sound

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

**The third is the same set SCORED, and it is exact rather than a bound.** What
survives `hopeless` is a candidate with *some* releasable seat worth less than
itself, which is necessary for an improving swap and nowhere near sufficient —
tier 2 sits above the two tiers that comparison is about, and a removal's effect on
the shortfall has nothing to do with its value. So every counted removal is put
through `Gallery.after_swap`, the same arithmetic the loop below uses, and a
candidate that no counted removal improves is settled without a picture. Sound in
one line: `narrowed` returns a **subset** of the counted set, so if nothing in the
counted set beats the objective, nothing in the narrowed set does either.

**The eight-weakest shortcut looks equivalent and is not.** Scoring only
`weakest(counted, SWAP_DROPS)` was the first spelling and it is unsound: a removal
that takes a met demand short loses tier 2 whatever it is worth, so the eight
weakest can all lose there while a ninth wins on tier 4 — and the narrowing can
drop those eight out of `leaving`, putting the ninth inside the offered set. The
whole counted set is scanned for that reason, and `solve.PRECHECK_REMOVALS` (256)
bounds the **cost** and never the argument: a candidate the four counted rules all
admit has an empty requirement list, which intersects to every seated key, so those
— the ones the diversity rule alone refuses — are left to the old path rather than
scored a seat at a time against the single picture the scan is trying to save.
`test_the_eight_weakest_removals_are_not_enough_to_settle_a_candidate` is the pin on
why, and `test_the_scored_prune_takes_the_same_swaps_in_the_same_order` on the
identity.

**Measured on the pool of 2026-09-04**, one item at a time on an idle box, at the
same seats and the same swap sequence at both rungs: the swap loop goes **170.39 s
to 36.33 s at n=2000** (4.7x) and **14.06 s to 6.38 s at n=1000** (2.2x), settling
5,706 and 1,749 candidates by scoring. Signatures made fall **10,105 to 2,844** and
**1,256 to 884**. The whole pass, pool read and pre-selection aside, goes 230.83 s
to 96.17 s and 34.11 s to 26.31 s.

### What a pass costs is one store

`rules.Twins.reduced_of` keeps **one reduced signature per candidate for the life
of the pass**, unbounded on purpose: 4 KiB a row is **80 MB over the largest view
this project has built** — 19,518 rows, `n1000_after_thin_themes_0906`, 2026-09-06
— and the full 128 KiB signatures stay in the bounded
cache underneath. Every question the bound asks reads the reduced form; the full
one is fetched lazily and only for the candidates whose bound could not settle
everything — 99.9% of seat comparisons are settled, so most candidates never have
their cloud read back at all.

Deriving the reduced form through the bounded cache instead is what a view larger
than that cache cannot afford: measured before this store existed, **24,969
signatures for an 8,704-row view — 2.9 decodes a row** — and a pass cost the same
whether it took forty-seven swaps or none.

**And the path a signature is made from is resolved once per key, not once per
decode.** `rules.clouds_for.path_of` is asked every time a signature is made, and
both halves of it are dear: `paths.rehome` resolves the tier settings and the
subtree, and `is_file` is a stat against a tree holding hundreds of thousands of
files. Measured under `cProfile` on the n=2000 pass of
`READ_solve_bound_and_profile_0904`, it was **41.1 s of a 411 s call** — a tenth of
the leg re-deriving a path the pool had already proved present. A dictionary for
the life of the pass closes it, and it is worth **14 s of 216 s at n=2000** on its
own and nothing measurable at n=1000. It is worth **less** beside the scored prune
than in front of it, because the prune is what stopped the decodes happening.

**The bounded cache under it is `rules.SIGNATURE_CACHE` and it is 2048, which is
256 MiB a solve process.** It was 256 — 32 MiB — until `PROFILE_solve_large_n`
measured what that cost. A swap pass re-tests about 870 of the same rows on every
pass, and 256 entries against a view of 11,690 meant passes two, three and four
re-decoded what pass one had already read: **4,238 full signatures made for a leg
that needs 1,459**, and n=1000 at 112.4 s against 52.0 s. That 256 MiB is a real
charge against the **one pool-holding process per box** rule in the root
`CLAUDE.md` — the pool itself is the hundreds of megabytes that rule is about, and
this now sits beside it in the same process. Two solves at once was already
forbidden; this is one more reason.

**2048 was too small at n=2000 and the scored prune fixed it instead.** Simulated
2026-09-04 by replaying one n=2000 pass's own `Clouds.of` / `hold` / `let_go`
sequence — a replay, checked against the pass it came from before it was believed,
and a `hold` promotes a name **out** of the LRU while a `let_go` hands it back, so
a simulation of the bounded store alone would price a cache that does not exist:

| entries | MiB | decodes before the scored prune | after it |
|---|---|---|---|
| **2,048 (shipped)** | **256** | **10,105** | **2,844** |
| 4,096 | 512 | 4,341 | 2,844 |
| 8,192 | 1,024 | 4,341 | 2,844 |
| 16,384 | 2,048 | 4,341 | 2,844 |

Before the prune the pass touched 4,423 distinct pictures and decoded 10,105 of
them, so **5,764 of those decodes were the cache thrashing** and 4,096 entries
would have bought about 95 s for another 256 MiB. **As replayed on 2026-09-04**
the pass touched 2,844, of which 1,660 were seats promoted out of the LRU, and the
1,184 left fit inside 2,048 with room — every decode a picture the pass had never
read, and the curve **flat at every size**. So the prune did not merely make the
cache question cheaper to answer for the swap loop, it removed it, and the
constant stays at 2048 on that evidence rather than by default.

⚠ **That replay predates the augmenting chain by three hours and the conclusion
does not reach the pass that ships now.** The 2,844 was measured on `4300e4b`'s
solve; `384a78f` shipped the augmenting chain the same afternoon, and it is a
decode-making stage the scored prune does not cover. The two n=2000 records that
followed — stamps `20260904T234133Z` and `20260905T001615Z`, neither published —
make **10,912** and **15,279** full signatures against a **16,112-row view**.
Their swap loops are bit-identical (`settled_before_opening_a_picture` 34,994,
`swaps` 289, `candidates_considered` 57,081 in both) and the entire difference is
the augment budget, 300 s against 1800 s, for 174 seats against 363. So the extra
decodes are the chain's, not the loop's.

**What that does and does not license.** `signatures_made` counts decodes and no
counter records distinct pictures, so 10,912 and 15,279 against 16,112 rows are
**not** evidence that anything was decoded twice — both are under the view size,
and inferring re-decode from them is the exact mistake the miss-rate paragraph
below warns about. The honest statement is that the cache question is closed for
the swap loop and **has not been asked for the chain stage**, and that answering
it needs a fresh `Clouds.of` / `hold` / `let_go` replay of a pass that has one.

**A miss rate quoted as `made / (made + hits)` cannot answer this question**, and
`READ_solve_bound_and_profile_0904` read one that way and called the cache
undersized on it. That ratio counts a picture's *first* read as a miss, so it can
never fall below the compulsory rate — 15.3% here — and it is 15.4% after the
prune, when nothing is being evicted at all. What separates a cache that is too
small from one that has simply not seen the picture is the replay above.

Two smaller changes landed with it and neither is a knob. `Twins.hold` no longer
decodes a seat's full cloud when it sits down — the bound settles 99.77% of a
seat's comparisons off the reduced form, so the cloud is read on first real need
and **495 of 912 seats** were ever read at n=1000. And `Twins.within` runs a scalar
**norm screen** in front of the reduced bound: `| |a|₁ − |b|₁ | ≤ |a − b|₁`, so a
seat the screen puts beyond `TAU` provably cannot be a twin, and it settled
3,004,576 of 4,173,399 seat comparisons before anything was subtracted. All three
are **bit-identical** — same seats, same order, same objective at n=250 and n=1000,
with `full_signatures_fetched` and `seat_comparisons_measured` unmoved, which is
what says the screen changed only the arithmetic. `tests/test_solve.py` pins the
cache's identity and that `clouds_for` reads the constant **at call time**: it used
to bind it as a default argument, so moving the constant moved nothing.

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

### And the threshold it binds at is too high — `AUDIT_twin_refusals_short_modes`

Audited on 2026-09-02 over `overnight_after`, the n=2000 gallery that closed every census
floor and still fell 68 seats short. **The pairs the twin test refuses stop being duplicates
at about 0.65 τ**, read off contact sheets of refused ↔ seated pairs, per mode: ~0.60 τ for
`direct_trap_multiply`, ~0.62 for `smooth_stripe` and `smooth_angle_min`, ~0.58 for
`smooth_mean_angle`, and ~0.72 for `direct_trap_screen`, whose pool is one look and so reads
as similar further out. An independent statistic agrees and was not used to reach it: the
share of refused pairs made with the **same palette map** runs 93-98% below 0.4 τ and
collapses through 55% at 0.5-0.6 τ to 32% at 0.6-0.7 and 11% at 0.9-1.0, against a 0.2% base
rate. **66% of all twin refusals sit above 0.65 τ**, and all twenty of the farthest-refused
pairs sit at the threshold itself and are plainly different pictures.

Solved at **0.65 τ globally the gallery goes 1,033 → 1,569 seats and the shortfall 68 → 7**,
four of the five short modes closing outright. Two costs: **500 of the 1,033 seated pictures
are not in it** — the lexicographic objective reshuffles once there are more seats to fill —
and it holds **3,795 pairs the shipped threshold would refuse** against zero today.

**The ruling came the same day**: Matt took `TAU` to 0.65 τ globally on 2026-09-02, which is
the 0.03809 that stood until 2026-09-05, when he took it to 0.90 of *that* — 0.034281 — by
eye rather than off a sitting. `curation.ceiling.TAU` carries both moves and what the second
cost; the sentence above is what the audit said before either was taken and is left as it was
written.

**What the 2026-09-05 move was read off.** A 200-pair boundary sheet, Matt's eye:
**88 pairs were ruled too close and all 88 were admitted-side** — pairs the standing
threshold was letting through — which is 9% of the view. The fit never crossed 0.5 and
the objective is flat below 0.85x, so 0.90x is a choice inside a flat region and not a
crossing. At n=1000 τ moves **no seat count** — every candidate fills — and what it
moves is worst/sum and *which* thousand: **158 seats turned over at 0.90x** [measured].
⚠ **The twin rule holds back about 34% of the view at τ**; the rejection ledger's twin
count (41 on that record) undercounts it badly because twin runs last, so read the
crossing sweep and never the ledger column.

**The colour-and-geometry gate is dead, and was measured rather than dropped**:
**AUC 0.448** — below chance — so a signature that mixes colour with geometry cannot
separate the pairs a person calls twins. Two near-white pictures with different
geometry collapse in a colour signature, which is the mechanism. The shipped test is
the pixel-cloud metric alone; a themed pass swaps it for the geometry-only `Places`
rule at radius 0.07, and τ is not in the themed path at all.

**The record is already the refusal log, so an audit like this needs no re-solve.**
`solve.json`'s `diversity_refusals` carries, per refused candidate, the seat it collided with,
the measured distance and how many seats were inside the threshold. Two things to know when
reading it. The named seat is the seat **at the moment of refusal** and the swap loop may have
taken it back out afterwards — 930 of 6,976 here, carried by only 77 distinct keys — so a
reader joining against the finished `seated` block silently loses them. And `same_location` is
**structurally zero**: `location` precedes `twin` in [`rules.RULES`], so a candidate standing
where a seat already stands never reaches the twin test at all.

**A wider radius needs no solve either.** It can never add a seat, so its whole effect is the
seated pairs falling inside the new radius, each of which must lose one member: the seats
given up are a minimum vertex cover of that graph. Over `overnight_after` that is 389-765 of
1,033 seats at 1.25 τ and 458-911 at 1.5 τ, before any refill — which is why the widening
what-if was priced this way rather than solved.

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
* the **palette-group cap** is `ceiling.themed_group_cap` — `max(1, floor(0.05 n))`,
  twice the main gallery's rate. It was `ceil(2n/P)` until 2026-09-05, when the
  denominator went; `P` is still measured and recorded. `--themed-cap` names a
  number instead;
* `--target <cell>=1.0` and `--flat-floor`, which the flag sets as **defaults**
  and not as overrides — a themed pass naming its own target or its own floor
  keeps it. Without the target the cell allowance is `floor(K x (1/48) x n) + 1`
  and refuses the theme at nine seats.

Rows outside the cell are recorded `not_dominant_in_the_theme`, which is pool
construction and sits beside `below_its_mode_bar` rather than among the rules:
the row was not refused a seat, it was never eligible for one.

**Why a themed pass needs its own cap.** The main gallery's
`max(1, floor(0.025 n))` is a share of `n` alone. Over a pool holding a few dozen
maps rather than hundreds that is the **binding** rule at every size a themed
gallery would ship at — measured 2026-09-01, `dark_vivid_lime` seated 38 of 50,
90 of 150 and 124 of 200 with the cap refusing 300-435 rows against the diversity
rule's 1-27, and `sum_g min(cap, places g fields)` predicted the whole column.

**`max(1, floor(0.05 n))` since 2026-09-05. Matt's ruling.** Twice the main
gallery's rate, on `n` alone, so the two caps are one rule with two numbers.

It **replaced `ceil(2n/P)`** — twice the even share across the `P` groups that
could field the theme, `P` measured off the pool at solve time. What that bought
was a cap that moved with the pool, so no comparison a themed record takes part in
was a comparison of one rule: on 2026-09-05's pool the six n=200 themes ran at
caps of **3 to 8**, and the richer the theme the tighter its cap —
`dark_vivid_blue` P=164 → 3 against `dark_vivid_yellow` P=51 → 8, which is exactly
backwards from where the room is wanted. A rate on `n` is a number written down
once.

**What the move costs, priced before it was taken.** `FIX_owed_minor_0905` ran the
six `themed_<cell>_n200_after_8h_0905` populations again through the pool-view
door, one pool, both arms under the per-mode ceiling, `P` read off the pool and
handed back as `--themed-cap` for the OLD arm so the two differ in the cap alone:

| theme | P | cap | seats over the q4 bar | median | p10 | worst | `group_cap` refusals | seats turned over |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `dark_vivid_blue` | 164 | 3 → **10** | 195 → **196** | 0.9710 → 0.9704 | 0.782 → 0.753 | 0.0200 → **0.0567** | 968 → **6** | 72 |
| `dark_vivid_orange` | 138 | 3 → **10** | 189 → **198** | 0.9590 → **0.9710** | 0.746 → **0.797** | 0.0017 → **0.1105** | 664 → **52** | 71 |
| `dark_vivid_purple` | 100 | 4 → **10** | 193 → 193 | 0.9402 → **0.9579** | 0.757 → **0.788** | 0.0049 → **0.0201** | 1,447 → **35** | 64 |
| `dark_vivid_rose` | 85 | 5 → **10** | 194 → **196** | 0.9524 → **0.9583** | 0.810 → 0.800 | 0.0434 flat | 434 → **35** | 49 |
| `dark_vivid_green` | 65 | 7 → **10** | 152 → **155** | 0.8661 flat | 0.0283 flat | 0.0007 flat | 94 → **25** | 15 |
| `dark_vivid_yellow` | 51 | 8 → **10** | 102 → **109** | 0.5372 → **0.5914** | 0.0105 → 0.0143 | 0.0010 flat | 381 → **223** | 23 |

**All six still fill 200 of 200 and not one loses a seat over the bar.** The cap
stops being the wall — refusals fall by 42% (yellow) to 99% (blue) — and what
takes its place is the diversity rule and the supply, which is where a themed
gallery's limit belongs. The two thin themes move least in seats turned over (15
and 23) because their caps were already near 10; the four rich ones turn over 49
to 72 seats each, which is the size of the change and is the number to weigh
against a themed record's IDs if one is ever published.

**The one place it goes backwards is `p10` on the two richest**, blue 0.782 → 0.753
and rose 0.810 → 0.800, against every other column flat or better. That is the cap
doing what a looser cap does: a map good enough to take ten seats takes ten, and
the tenth is weaker than the seat some other map would have filled. It is under
four points on a decile of a gallery that gained a seat over the bar, and the
worst seat went the other way on blue by a factor of three.

`P` is still measured and still on the record — **groups fielding three or more
distinct PLACES** in the pool (`ceiling.THEMED_CAP_PLACES`) — and it denominates
nothing now. Places and not rows, because one wallpaper per location is absolute;
the floor of three is what keeps the reading honest, since a group holding one
fluke place can never take more than one seat however high the cap goes and
counting it would report a capacity that does not exist. Measured either way on
2026-09-01: lime 39 groups of which 29 clear the floor, green 65 of which 50, and
the places no group over the floor reaches at all are 13 (lime) and 17 (green).
**Nothing is dropped from the pool** — a sub-floor group still seats.

The cap is set **after** the bar and the pre-selection, with `P` read over exactly
the rows the leg may seat — which is why `solve` sets `rule.group_cap` there
rather than with the other constants. `ceiling.THEMED` is the rule's name on the
record and is deliberately **not** in `GROUP_CAP_RULES`: it is not a rule a caller
names, it is the rule a themed pass has.

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

#### `--explain-seats-of` answers the other question: what happened to THIS picture

The aggregate above is denominated in counts, so it can say *which rules cost this
pass its seats* and never *which of yesterday's seats each rule took*. A before/after
sheet needs the second on every card, and `--explain-seats-of <earlier record>` is
where it comes from: the pass reads that record's seats, and writes one entry each
into `rejection.explained` — `seated` if this gallery holds it, `not in the pool` if
the pool no longer has it at all, and otherwise the rule that refused it, in the same
vocabulary `reasons` counts.

**Named and never automatic.** The refusal map is one entry per candidate over a
hundred and fifty thousand of them; a record carrying all of it would be some forty
times the size of the one carrying the decisions. So the block is absent unless
somebody asked for it, and it holds exactly the keys they asked about.

#### A scratch driver asks the same two questions

`solve.solve` takes both halves in the signature and **neither has a CLI surface**,
which is deliberate: they are how a one-off read is taken without a subcommand, a
stamp or a record on disk.

* **`candidates=` is the pool view.** Unasked, `solve` calls `solve.pool()` itself;
  handed a list, it seats over exactly that list and nothing else re-derives it. Any
  filter of `pool()`'s own return is therefore a legal pool, and the useful one is
  *the pool less one leg's rows, by merge stamp* — which makes the pair of solves a
  **counterfactual** and is how to ask **what did leg X buy**. The bars, the rank key
  and the neutral pre-selection all read the rows in hand, so the narrowed pass is a
  whole pass and not a replay.
* **`explain=` is `--explain-seats-of` without the earlier record.** It takes any set
  of recipe keys and fills `rejection.explained` from them, in the same vocabulary:
  `seated`, `not in the pool`, or the rule that refused it. The flag's population is
  one gallery's seats; this is any handful of keys a driver is curious about.

Both were used this way in `READ_rare_cells_yield_0904` and
`READ_solve_bound_and_profile_0904`, and the first of the two is the evidence that
the door is a controlled read rather than an approximation: the pool with a night's
whole merge removed reproduced the tracked `20260904T080248Z` **key for key** at 941
seats, and the unfiltered pool reproduced `20260904T134242Z` key for key at 947.

**One caveat, and it bites exactly this read.** The leg is a greedy seed and local
search, not an exact optimum, and it is **not monotone in its candidate set** — the
same night's pool seated 947 with all of its rows and 952 with its `phoenix` rows
held out. A smaller pool seating more is a fact about the pass this project runs and
never a proof that rows can lower an optimum.

## `curate solve record` — a solve recorded under a stamp, and a browser over it

```
src/fractal_wallpapers/curation/tentative.py   the store, the aliases, the page
artifacts/curation/tentative/<stamp>/gallery.jsonl   one row per seat
artifacts/curation/tentative/<stamp>/manifest.json   what pool, what settings, what shortfall
artifacts/curation/tentative/<stamp>/index.html      the browser, NOT tracked — `browse` writes it
artifacts/curation/solve/tentative_n<N>_<stamp>/     that record's own solve, under the same stamp
```

```
fractal-wallpapers curate solve record                    # the production solve, recorded
fractal-wallpapers curate solve record --n 150            # a smaller one
fractal-wallpapers curate solve browse <stamp>            # write the page again
fractal-wallpapers curate solve resolve 49616c4b,a71f     # an ID or alias back to a recipe
fractal-wallpapers curate solve list                      # every record on this machine
```

**Renamed 2026-09-04, and there was an unrelated `curate gallery` before it.** These
four verbs were spelled `curate gallery <verb>` until this file documented that name
twice — once as the pre-solver draw deleted 2026-08-28, once as this — so they moved
under `curate solve`, whose leg they already were. Only the verb changed: the stamps,
the rows and `artifacts/curation/tentative/` are where they were.

A solve record is a **decision**, and `curate solve run --name n1000` rewrites it every
time it is run. It is not something a person can point at. To say "use this wallpaper and
that one" a reader needs a stable handle per picture, a page showing the pictures beside
their handles, and a guarantee that the picture is still on disk next week. A
**tentative gallery** is that: `record` runs `curate solve run` with nothing changed — same
pool, same bars, same rules, same objective, same draw seed — and writes the seats under
a UTC stamp that is **never written over**, because the IDs in it are what a figure
prompt names.

**A record is about a minute and a half, not the hours a leg is.** At `n=1000` over a
pool of ~169,000 candidates it ran **89 s end to end** — 58.5 s of that the solve
itself, the rest the pool load, the `centered` join and the page. Nothing here renders:
`record` is taken with `--no-render` and the tiles are the candidate pictures the solve
chose from, so the cost is reading and arithmetic. It still holds the pool, so it is one
of the processes the one-pool-holding-process rule counts.

**The ID is the ledger recipe key**, and the alias is its first eight characters,
lengthened only for the group that collides. Both resolve; a click on the alias in the
page copies the full key.

**The solve half is stamped too, with the same stamp.** `record` writes its solve record
to `artifacts/curation/solve/tentative_n<N>_<stamp>/`, not to `tentative_n<N>/` — the
stamp is the tentative folder's own, so the manifest's `solve.record` path points at the
solve that chose those seats and two records at the same `n` coexist instead of the
second overwriting the first's decision. `--solve-name` still names the directory
outright for a caller who wants to. It was not always so, and the two stamps recorded
before this landed share one unstamped solve directory: the earlier one's manifest names
a record that the later run overwrote, so that gallery's `config`, `shortfalls` and
`diversity_refusals` are gone. The rows, the manifest and the page are intact — those
were always stamped — so nothing a figure prompt names was lost.

**`index.html` is the standing debug tool for figure selection** — open the stamp's page
and filter by mode, cell, hue family or partition to find the wallpaper a figure wants,
then `curate solve resolve <alias>` to turn what you picked back into a recipe. A record
writes its page as it lands and `curate solve browse <stamp>` writes it again, which is
what a clone runs: the page is a derivation and is not tracked.

**It is also the eye-check over a whole record**, which is what the *group by* control
and the full-size view are for. Filtering answers *show me this cell*; grouping cuts the
whole record into sections in one scroll, which is how 48 cells get looked at without 48
clicks. **Grouping reads the LEADING cell or family and filtering reads the dominance
list** — deliberately, and they disagree: a seat dominant in three cells answers three
filters but stands in one section, so the section counts partition the seats and sum to
the seat count while the filter counts over-count exactly as the census does. Clicking a
picture opens it at the size the screen gives, and `←`/`→` step along the drawn order
with `esc` to close, so a filtered or grouped set is walked without returning to the
grid. **Selecting is the checkbox beside the alias, not the picture** — the two were one
gesture while a 224px tile was the only size there was, and a click that both opened and
selected put a stray ID in the copy tray on every look.

**Two files a stamp are TRACKED, and the pictures are not.** `gallery.jsonl` and
`manifest.json`, through a narrow un-ignore in `.gitignore` that names them one at a
time. It is the one deliberate hole in `artifacts/` and it is there because the site's
figures name wallpapers by these IDs: a clone that cannot resolve them cannot rebuild the
site. A third file appearing in a stamp is ignored until somebody decides otherwise, which
is why the un-ignore lists names rather than a pattern.

**`index.html` is not one of them, since 2026-09-05.** Matt's ruling: **a record is
`gallery.jsonl` plus `manifest.json`, and the page is a browse view derived from them.**
`curate solve browse <stamp>` writes it again from the rows alone, on any clone, so
tracking it was committing a derivation — 4.07 MB over the seven published stamps against
their rows' 3.60 MB, and a page rewritten by a `browse` is a diff of its whole body. It was
tracked until the ruling and left tracking by it; the files themselves stay on disk, and
`tests/test_tentative.py` holds the index to carrying no page for any stamp. An un-ignore
cannot say that on its own — it stops nothing git already holds — which is why the seven
were removed from the index by hand. **No `LARGE_TEXT_ALLOWLIST` entry was added and none
is implied**: a stamp gets one only when Matt permits it, per stamp.

**Tracked only once Matt PUBLISHES the stamp**, his ruling of 2026-09-04, and the hole is
per stamp because of it: the store is ignored by default and each published stamp is one
negation line beside `curation.tentative.PUBLISHED`, which is the same list in code.
Recording a gallery and committing it were one act until then, so a record too large to
track was a record that could not be made — an n=2000 record's `gallery.jsonl` is **over
the 1 MiB `tests/test_history_purity.py` allows**, at 1.06 MB for the 1,795 seats of
`20260904T234133Z` (its page was 1.18 MB and is now beside the question). Every
unpublished record stays in
the store, kept and read **by naming its stamp**; `tentative.latest()` — what an unstamped
`browse` or `resolve` means — walks published stamps only, so an experiment can never
become the default answer for a figure prompt and hand out IDs that exist on one machine.
`curate solve list` marks every line.

**Publication and durability are different questions, and the protection below is the
durable one.** An unpublished record is *kept*: `protected_keys` sweeps the whole store
whatever `PUBLISHED` says, so deleting the record is the only thing that releases its
seats. What publication buys is a clone; what it does not buy is protection, because that
was never scarce. What an unpublished record gives up is a Durable-class save, check or
restore and a place in an archive copy.

**The record is a protection class in the prune.** `candidate_ledger.RETAINED_TENTATIVE`
joins the four that were already there. It is needed for a sharper reason than the
release row's: a seat is chosen on the *gallery's* objective, over a view, against the
colour rules, and none of that is being in the top `RETAIN_PER_PAIR` of its own
(location, mode) pair — so the rank drops these routinely, and it takes the picture with the
row. Without the class an alias would stop resolving and nothing would say so.
`tests/test_tentative.py` pins it through a real prune, on `saved_by_a_protection`,
which counts exactly the protected keys the rank verdict dropped.

⚠ **A third of a gallery's seats cannot be re-derived, and the record is what ships
because of it.** Measured over two records: **33.4% of seats are
`acted_unrecoverable`** — **305 of 914** on `20260904T023748Z` and **243 of 1,000** on
`20260904T233233Z` — because a `depth` row's stored picture is the *levelled* picture
the judge scored and re-measuring derives a different curve. It is a STEM join; a key
join loses the `runs` and `reframe_draw` rows and reads lower. Re-rendering is not a
way out of this, which is why the website ships the stored file and never a re-draw
(`builder/checks.py`'s `seats`). The reader is `depth.levelling_of`, three-way, off
`sequence.jsonl`'s whole stamp.

**The page is one file and it opens over `file://`.** The rows are embedded as JSON
rather than fetched — a `fetch` of a sibling file is refused there — the styling is
inline, and the only external references are relative paths to the pool's own 640x360
candidate JPEGs. Filters on mode, hue family, colour cell, partition and `centered`, all
multi-select and all counted in the header; sort by rank, seat order or P(>=4); a search
box over ID and alias; a selection tray that copies every selected ID as one line. The
colour filters read a row's **whole** `cells`/`families` list rather than the leading
one, because dominance is thresholded and filtering on the leader alone hides a green
picture from the green filter whenever another colour leads it.

**`centered` is joined at record time and cannot be read off a seat.** Nothing
downstream of a walk carries the flag — not the embedding store, not the supply sidecar,
not the candidate ledger — so it comes from [`depth.centered_locations`] over the walk
ledgers, keyed on the location, which costs about 3.6 s once per record.

**What the browser cannot show**, and each is a fact about the store rather than the
page: the release-size picture, because a record is taken with `--no-render` and the
tiles are the candidate renders the solve chose from; the palette group and the seating
leg, which are on the solve record and not on a row; and any picture the prune had
already swept before the record existed, which shows as a "no picture on this disk" tile
and which the resolver reports as `picture_on_disk: false`.

## `curate votes build` — the folder friends open, and what it prices

```
src/fractal_wallpapers/curation/votes.py   the encoder, the builder, the page
artifacts/votes/<stamp>/full/sNNNN.jpg     2560x1440, the picture a click opens
artifacts/votes/<stamp>/thumbs/sNNNN.jpg   512x288, downscaled from the full, never the candidate
artifacts/votes/<stamp>/index.html         the viewer, one file, openable over file://
artifacts/votes/<stamp>/README.txt         the paragraph the friends read
artifacts/votes/<stamp>.zip                what actually gets sent
```

**`artifacts/votes/` and not `artifacts/curation/votes/`, deliberately.** `--out` takes
any directory and the module fixes none, but a kit is a gigabyte or two of finished bulk
that nothing in the loop reads once it has been sent — archive tier by the three-way rule
in `CLAUDE.md`, and the unit of an archive is a **top-level name** under `artifacts/`.
Inside `curation` it could never move on its own, because `curation` is the live pool and
can never move at all.

```
# the whole record, at the defaults
fractal-wallpapers curate votes build <stamp> --out artifacts/votes/<stamp>
# forty seats first, so the viewer can be tried before a leg of hours
fractal-wallpapers curate votes build --out artifacts/votes/<stamp>_n40 --limit 40
# cheaper to make and smaller to send, and it shows
fractal-wallpapers curate votes build --out artifacts/votes/cheap --ss 2 --quality 80
# cheap everywhere but the mode that aliases worst — repeatable, one mode each
fractal-wallpapers curate votes build --out artifacts/votes/mixed \
    --ss 2 --ss-for smooth_mean_angle=4 --quality 85 --chroma 420
```

A recorded gallery is a decision this project took. A voting kit is that decision handed
to people who are not here, and what comes back is one small JSON file per person:
`{viewer, record, name, order_seed, votes: {<recipe key>: 1 | 2}, pages_visited,
exported_at}`. **There is no ingest yet and the schema is the contract** — the votes have
to exist before anything reads them, and `votes.VIEWER` names the shape so a friend's
copy of a kit outlives this checkout's memory of what wrote it.

**A filename carries the seat's position and nothing else.** No rank, no key, no mode: a
friend who can read a rank off a filename has been told the answer. The join lives in the
page, which embeds the seat list as JSON — `{"key": <recipe key>, "ss": <supersample>}`
per seat, in seat order — and the export carries the recipe key, the ID that survives
every later merge. **The supersample is in that list and not in the filename**, for the
same reason: a kit may render one mode finer than the rest, so a kit has to say which
seat got which, and a filename saying it is a second thing a friend can sort a page by.
The mode that decided it is not in the page at all.

**Three keys, from 2026-09-05: `1` clears, `2` is the thumbs-up, `3` is the star.** The
**vote values stay 1 and 2** — shifting those to make room for a neutral would invalidate
every label file already exported against a record, so the key numbering and the vote
numbering are deliberately apart. **Any of the three closes the fullscreen**, Average
included — Matt's ruling of 2026-09-05 after driving 2.0, reversing the first reading.
That reading was that clearing undoes a decision rather than taking one and should leave
the picture up; in the hand, Average *is* a decision — the verdict "this one is ordinary"
— and a key that sometimes closed and sometimes did not became the thing to keep track of,
which is the same objection that produced the three keys in the first place.

**Viewer 2.0 gives the neutral a button, and that is what moved the toggle.** The
fullscreen bar is three: **Average `(1)` · Thumbs up `(2)` · Star `(3)`**, left to right in
key order, and they **set** rather than toggle, exactly as the keys do. Before 2.0 the only
way to un-rate with a mouse was to press an already-pressed button, so a button had to
toggle; with an Average button the toggle becomes a second route to the same state and a
worse one, because it makes *Thumbs up* mean *un-like* on a picture already liked — the
one ambiguity the third key exists to remove. **The grid-tile buttons are unchanged and
still toggle**, having no third button to set neutral with. `viewer` on the export is
`"2.0"`, and deliberately not `votes/v2`: telling it from the first version's `votes/v1`
is telling two unrelated strings apart. **The schema under it is unchanged.**

**Two colours, named once and read everywhere a vote shows.** Thumbs-up is the gold the
star used through v1, `#fbbf24`; the star is a medium-dark green, `#16a34a`. The tile
border, the button that cast the vote and the two figures in the count strip all read them
off `--up` and `--star`, so a person learns the pair on the first page and no later screen
teaches a second vocabulary for the same two votes. The neutral button keeps the strip's
blue: it is the button that says nothing about the picture, which is the one lie a vote
colour there would tell.

**Two people on one computer, and the button that is not how you do it.** A name is a
slot — ratings live under `votes/<record>/<name>` — so a partner taking a turn types their
own name and gets their own walk and their own storage, and the first person gets hers
back by typing hers. Nothing has to be destroyed to share a machine, and the README says
so before it says anything about the button. **`Start over` is for leaving the computer
clean**: it erases every name's ratings *for this record* and it asks **twice**, an in-page
band carrying the count of exactly what would go, then the browser's own dialog. Two steps
of different kinds, because two of the same kind is one habit. The sweep is the record's
prefix and not the whole store — another kit's folder in the same browser is somebody
else's evening. A latent collision went with it: the remembered name was kept at
`votes/<record>/name` and now sits at `votes/<record>:name`, beside the slot prefix rather
than inside it, because a person actually called *name* would have overwritten it with
their votes object.

**Each page button carries the votes given on that page**, small type beneath the number,
thumbs-up and stars together, **zero drawn as `0` rather than left blank**. It is the one
affordance on the page that is not about the pictures, and it earns that: a page nobody
opened and a page somebody worked and liked nothing on are the same blank from the outside,
and only the first is worth going back to. Blank would mean *unknown* and nothing here is
unknown. The count is over the **walk** and not over the record — two people's page 3 hold
different pictures — and it names no picture, mode or vote, so there is still nothing to
sort by.

**Every seat is rendered again and the thumbnail comes off that render.** The stored
candidate is 640x360, the size the judges read, and it is far too small to vote on;
a grid of candidate thumbnails over a fullscreen of fresh renders would be showing people
one picture and asking about another. The two are different sizes under different
autolevel curves, because the release path measures its own curve at the frame it is
rendering. Nothing in a kit replays a candidate curve, so `depth.levelling_of`'s
three-way answer is a question about the 640x360 picture and never about this one.

**Twelve seats of `20260904T233233Z` were being rendered as the wrong picture, and it was
not this module's bug.** `release.Task` had no `mode_params`, so every release-size render
in the tree dropped them: a `direct_trap_multiply` at `opacity=0.6` came out as the bare
mode under the varied seat's name. Silent, because the bare picture is a perfectly good
picture of something else. The field is on the task from 2026-09-04 and all four builders
— `solve.render_seats`, `checks.tasks_of`, `run`'s release leg, `votes.render_fulls` —
read it off the recipe; `tests/test_curation_release.py` holds both halves, the value
reaching `colorize.render` and every builder naming it. **The solve's own release renders
under `artifacts/curation/solve/tentative_n1000_20260904T233233Z/release/` predate the fix
and those twelve are wrong there.**

### What a kit costs, measured

`scratch/votes_pilot` on 2026-09-04, six seats spanning the record's candidate-byte
distribution with a distinct mode at each — `smooth`, `threads`, `smooth_stripe`,
`smooth_angle_min`, `smooth_mean_angle`, `smooth_curvature`, 106 to 204 KiB of candidate.

**To make, on the locked three workers**: **13.9 s a picture at 2560x1440 ss2** and
**54.2 s at ss4** — leg wall clock over rows, which is the number a leg is sized off, not
the per-row mean (28.0 s and 106.8 s, inflated by concurrency). Sample-linear as ever: the
ratio is 3.9x for 4x the field samples, and it lines up with the 1280x720ss2 leg's 3.5 s
a row.

**Those two numbers are a floor and not a price, and the reason is how the six were
picked.** They span the *candidate byte* distribution, which is the right axis for the
encoding question and the wrong one for the timing question: they came out at a median
viewport width of **10^-2.1** against the record's **10^-4.6**, so the pilot priced the
shallow half of a pool where **31% of seats sit below 1e-6** and depth is what buys
iterations. The honest price is the forty-seat kit's, drawn in seat order and therefore
depth-representative: **76.2 s a picture at ss4**, a 3,047 s leg over forty rows of
47.3 s to 642.9 s, forty made and none killed. That is **1.4x the pilot's ss4 figure**,
and it puts a thousand seats at **21.2 h at ss4** and about **5.4 h at ss2** — the
second derived through the pilot's own 3.90x ratio rather than measured, because
nothing has run a deep ss2 leg. Price a kit off a sample drawn in **seat order**, never
off one drawn on a picture's own properties.

**ss1 measures 4.9 s a picture and it is sample-linear too**: 250 seats of the same record
in seat order, a 1,233.9 s leg on the locked three workers, 250 made and none failed,
2026-09-05. That is **15.6x** the ss4 rate against the 16x the sample count predicts, so
the fixed cost a seat carries — process spawn, PNG write, two JPEG encodes at 2560x1440 —
is still under a tenth of the field time even at the cheapest cell. A 250-seat kit is
**21 minutes**, which is what makes ss1 the cell you drive the viewer on. Its bytes are the
other half of the trade and they go the wrong way: **1,288 KiB a full**, 20% over ss4's
1,077 at the same q85/4:2:0, because supersampling removes exactly the noise a JPEG spends
most on. **342.9 MB zipped at 250 seats** — a kit for driving, not for sending.

**The pilot's byte prediction held even though its timing did not**, which is the shape
to expect: JPEG size is a fact about the picture and the six spanned that distribution on
purpose. It predicted 1,022 KiB a full at q85/4:2:0/ss4 and the forty came in at
**1,077 KiB mean, 1,438 KiB max** — within 5%. So a thousand seats is **1.13 GB**, off a
45.2 MB kit at forty.

**The thumbnails cost nothing and the fulls are the whole zip.** 2.0 MB for forty, so
50 MB at a thousand against 1.13 GB of fulls. And the zip **stores** the JPEGs rather
than deflating them: rebuilt both ways over the same forty, deflate bought 0.1 MB of
45.3 and would spend minutes of CPU doing it at a thousand.

**To send**: every cell of the quality x chroma grid puts a thousand fulls between
**0.88 and 2.88 GB**, at ss4:

| quality | 4:4:4 | 4:2:0 |
| --- | --- | --- |
| 80 | 1.11 GB | 0.88 GB |
| 85 | 1.35 GB | **1.05 GB** |
| 90 | 1.74 GB | 1.31 GB |
| 95 | 2.58 GB | 1.82 GB |

**The zip is the constraint and quality does not fix it.** The whole quality axis moves
the total by a factor of two and the floor is still most of a gigabyte, because a fractal
at 2560x1440 is high-entropy everywhere. Only the frame or the seat count would move it,
and both are Matt's call. The thumbnails are not the problem: 512x288 at q85 is about
20 KiB, so a thousand of them is ~20 MB.

**The supersample is the only decision on that sheet a person can see.** ss2 against ss4
is a mean absolute difference of **6.28** over the six seats, **4.81** after fitting to
1080p — against **3.71 to 6.09** for the entire quality axis from q95 to q80 inside the
busiest crop. So dropping to ss2 to save eleven hours costs *more* picture than dropping
five quality steps does, and it costs it as aliasing rather than as softness; the crops
show it plainly on `smooth_mean_angle`. Hence the defaults: **ss4, q85, 4:2:0**, one to
buy the picture and two to pay for it. ss4 is also 10% smaller in bytes at every cell,
because supersampling removes exactly the noise a JPEG spends most on.

**`--ss-for <mode>=<n>` buys that decision back per mode**, repeatable, and it makes the
leg **one render pass per distinct supersample rather than one overall**, cheapest first
so the fulls a person can look at start landing early. Each pass is the locked three
workers in turn and never two pools at once. It is **per mode and never per seat**: the
modes are what a person can say a sentence about, and a table with single seats in it
would be a kit nobody could describe. An override naming a mode the record does not hold
is **legal, not refused** — a `--limit` cut holds whatever modes its first N seats carry
— and the manifest's `encoding.regime_for` (what was asked) beside `encoding.seats_at`
(what the record's modes turned it into) is where one that fired on nothing shows up.
`votes.SUPERSAMPLES` is what either flag takes, and **2 and 4 are the priced pair** — the
argument above is a comparison between exactly those two, and anything else is a cell of
the pilot's grid nobody has looked at.

**`--ss 1` is on that list and is not one of them.** It is the debugging cell: a kit in
minutes rather than hours, which is what makes the whole friends' flow — paging, voting,
export — something a person can drive end to end in an afternoon instead of after a leg.
It pays for that in the currency the ss2-against-ss4 measurement already named as the
visible one, aliasing, and nothing has priced its bytes or its picture. **A kit at ss1 is
for driving, not for sending.**

**The busy crops are found rather than guessed**: `flatness`'s own per-16-pixel plane fit,
summed over a 512x288 window with a summed-area table, and the window is chosen once off
the ss4 render and reused for every regime — a window found per regime would put the two
crops in different places, and the sheet's last row is a claim they are the same crop.

**The fast lane drives the whole builder without an engine.** `votes.render_fulls` is the
seam and it is replaced, but `arrived` is called on this side of it, so the encode, the
downscale, the page and the zip are all exercised. `tests/test_votes.py` names candidate
pictures that do not exist on disk at all, so a kit that reached for one could not be
built there rather than quietly shipping the wrong picture.

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
Six of the **fourteen** modes `mode_policy` accepted then had fewer than twenty-five
distinct locations clearing that, so those fall back to `P(>=3) >= 0.50` and the
table **says which rule each mode landed on**: a mode censused under a lower bar is
not comparable to one censused under the default. The roster is `accepted()` and not
the engine's nineteen — a weight-0 mode has no row in the pool to bar. The reading
was taken on 2026-08-30 over the same fourteen: `tail_itinerary` was briefly a
fifteenth and was never in it, and it is weight 0 as of 2026-08-31, so the roster
the reading was taken over was the roster again. **It is thirteen since
2026-09-04**, when `exp_smoothing` went to weight 0 — it was one of the eight on
the default bar, so the current split of that same reading is seven on the
default and six on the fallback. Nothing was re-measured; a mode leaving the
roster takes its row out of the pool and its bar with it.
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
weight 0 before it had a candidate in the pool. `exp_smoothing` is a **sixth** with
no bar as of 2026-09-04 and *was* read, on the default — so the eight is seven now
and the table below is the place to read it off rather than this paragraph.

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
floor is one, and under this rule the twelve strange floors are not one number.
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
estimator's name. The separator is **`hunt.drawn_for`**, and it is exact by
construction: it is written on the aimed row alone and on no other row — the
control arm's included, which is what makes the control still readable as base
rate. Drop those rows *before* the census to read the true rate; there is no
correction to apply afterwards, because the aimed rows move the numerator and the
denominator by different factors. The same caveat rides on `depth.mode_bars`'
`ledger_clear_rate`, which is the base rate the next arm's clear rate will be
quoted against.

**And for four days the separator was not on any row at all, which is a hole this
store keeps.** `449643d` (2026-08-29) cut the ledger row to its readers by tracing
sixteen call sites, found nothing in *code* reading `hunt.drawn_for`, and took it
off with six other `hunt` fields — the paragraph above is a reader with a person on
the end of it, and a trace of call sites cannot see one. The same commit rewrote
the whole store, so **the 3,042 rows the conditioned arm merged before that date
have no stamp and can never be filtered out of a rate taken over them**; measured
2026-09-03, `drawn_for` appears on 0 of the store's rows. `candidate_ledger.ASKED_FOR`
restores it and `tests/test_candidate_ledger.py` pins it, which repairs the next
aimed leg and no earlier one. The lesson is the general one and it is cheap to
state: **a field a README tells a human to filter on is a field with a reader**, and
the trace has to include the prose.

**And it under-prices a win that only a non-shareable mode can deliver, by up to
an order of magnitude.** `seconds_per_win` is `renders_per_win` — a count over the
**whole ledger**, which is dominated by the cheap shareable modes — times
`_mixed_cost`, the mean of the medians of the modes that *already* won. Neither
half is the marginal mode. Measured over the store of 2026-09-02, 166,118 of
177,993 rows carrying `hunt.seconds`: the ledger-wide median render is **0.333 s**,
the five accepted **shareable** modes run 0.217 s (`tia`) to 0.269 s
(`exp_smoothing`), and the nine accepted **non-shareable** ones run 0.947 s
(`direct_trap_lines`) to **5.64 s** (`smooth_stripe`) — a median-of-medians of
2.52 s against 0.239 s, **10.6x**, and the dearest mode is **16.9x** the
ledger-wide median. (`exp_smoothing` went to weight 0 on 2026-09-04 and was the
**dearest** of the shareable five, so the accepted shareable half is four now and
its top end is lower than the 0.269 quoted here. That moves the gap wider rather
than narrower, so nothing this paragraph concludes turns on it and the reading
has not been re-taken.)

**This is not a corner case, because the modes the pool is short of are exactly
the dear ones.** The four mode floors short at n=1000 — `smooth_angle_min` 6,
`itinerary` 5, `smooth_mean_angle` 4, `smooth_stripe` 3 — are all four
non-shareable, at 3.67 s, 2.22 s, 3.83 s and 5.64 s a render. A census row for one
of those quotes a price built from a mix the shortage is by definition not in.
It is a **reader caveat and not a record fix**: the arithmetic is right about what
it computes and the shape *Three workers, cut at the location* in
[`LEGS.md`](LEGS.md) states for `curate depth` is the same one — a
roster cycled uniformly charges a composite an equal count of the width at several
times the unit cost. Price a composite work order off that mode's own median in
the table above, never off a census row's `render_seconds`.

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

**A third default joined them on 2026-09-04 and the incumbent line grew a third
flag with it** — see *The spiral share cap is a tenth by default* below. An
invocation that means the pre-flip gallery has to say `--spiral-cap none`, because
saying nothing no longer means no cap.

```
curate solve run --n 150                                  # proportional + rank-key + 0.10
curate solve run --n 150 --group-cap identity --key p_ge4 --spiral-cap none  # the incumbent, whole
curate solve run --n 150 --group-cap {identity,proportional}  # the palette-group cap
curate solve run --n 150 --key {rank-key,p_ge4,cascade}   # the sort key
curate solve run --n 150 --spiral-cap {SHARE,none}        # the spiral share cap
curate solve run --n 150 --sheet-out <path>               # the contact sheet, elsewhere
curate solve run --n 150 [--release-regime WxHssN] [--workers 3]
```

`solve.DEFAULT_KEY` and `solve.DEFAULT_GROUP_CAP` are the two constants, and
`solve.ranking_for` is the one place a pass pays for its key — it reads the
flatness sidecar and the location scores, once per pool. `seat(order=...)` overrides
it, which is what a sweep seating one pool four ways passes.

### `cascade` is staged and OFF, 2026-09-06

`solve.CASCADE_KEY` is the third key and nothing runs it unasked: `DEFAULT_KEY` is
still `rank-key`. Above `Q4_BAR` it orders on the **fine-tier head** —
`models/gallery_grade/`, fitted on human verdicts about pictures that had already
cleared the gate — and below the bar it hands the rank key's own values straight
back. The head's output is undefined down there, so the two stages are separated
by a constant rather than mixed: an above-bar row is `1 + <fine score>` and a
below-bar row is its rank-key value. The above-bar order is the head's **`p_ge4`**
and not its `rank_score`: `AUC(>=4)` is the statistic the head's bar is stated on
and it is read on that column, and the two order this pool at Spearman 0.92 —
a different order, and one nothing gated.

It needs a column and refuses without one:

```
fractal-wallpapers gallery-grade score-pool          # reads the ABOVE-BAR rows only
fractal-wallpapers curate solve run --n 1000 --key cascade
fractal-wallpapers curate seat-sheet --n 1000        # what the two keys disagree about
```

⚠ **It is not a reordering of the top, and the seat count is how you find that
out.** At n=1000 over the pool of 2026-09-06 the two keys share **175 seats of a
thousand**: 825 arrive and 825 depart. `curate seat-sheet` solves one pool twice
and lays out only those rows, sorted good to bad by the fine head and marked
arriving or departing — capped at 150 cards sampled across the score range, on
the ledger's stored 640x360 pictures, ingesting nowhere.

**Seating only.** Retention does not read it and `_prune_ranks` is untouched —
what the prune keeps is a separate question from what a gallery seats, and a key
that moved both would have moved the one nobody looked at.

### The spiral share cap is a tenth by default

**`solve.DEFAULT_SPIRAL_CAP = 0.10` since 2026-09-04. Matt's ruling.** It was
`None`, which means **every solve record on this machine that does not name the
flag ran uncapped** and is not comparable with one that ran under this. Of the
tracked tentative galleries, two are capped and they are capped for different
reasons: `20260904T023748Z` named the flag, and `20260904T233233Z` is the first
record taken after the ruling and did not have to. Between them,
`20260904T080248Z` and `20260904T134242Z` ran uncapped, and the three before
`20260904T023748Z` carry no spiral block at all because the store did not exist
yet. **A record's `config.spiral_cap` is the only thing worth reading here**; the
dates are what made the list, not what settles it.

What the cap costs and what it acts on, off `20260904T023748Z`, which is the first
gallery that ran one: **27 seats of 1000** at `n = 1000` (914 against 941), every
demand still met, 14 of 14 modes represented, and it **bound to the last seat** —
`ceil(0.10 x 914) = 92` allowed and exactly 92 taken. The population it narrowed
was 27.75% spiral on the clearing rows and the gallery was **already 26.4%** before
any cap existed, so the diversity rule and the colour allowance between them were
suppressing spirals by about a point and a half. A tenth is under half of what the
gallery was doing unaided, which is why this is a ruling and not a tuning. The 27
seats are a **net** figure and the churn under them is larger: **24% of the gallery
turned over** [measured] to give them back.

**It binds to the last seat at every rung it has been run at**, which is the shape
rather than the number: **101 of 101, 180 of 180, 199 of 199** allowed and taken,
beside the 92 of 92 above. `ceil(0.10 x (filled + 1))` is evaluated during a walk
that fills by scarcity, so the allowance a mandated spiral meets is the allowance at
*that* seat and not at the finished count — which is why a cap denominated in `n`
would not bind here. Spirals are a **location** property: the clearing pool runs
about **28% spiral** and a seating takes **20.8%** of them before any cap.

**Three answers and not two, so `0` is not the spelling for `none`.** `none` (or
`off`) runs no cap at all and the `spiral` refusal column is zero by construction;
`1.0` runs the cap and lets it not bind, which is what a record that should *say*
it ran a cap is spelled with; `0` runs a cap whose allowance is zero, so no spiral
may be seated at all and the refusal column fills. `curate_commands.spiral_cap_value`
is the converter that keeps the three apart.

**The cap is on the record's `config` block as of the same day**, beside `n` and
the bars, and not only in the `spiral` block it was in. `config` is what a
tentative gallery's tracked `manifest.json` carries whole, and the `spiral` block
is not tracked at all — so until this moved, a tracked gallery could not say
whether it had run capped. A reader had to infer it from a zero in the refusal
column, which is exactly what a cap that ran and did not bind also produces. **A
growth row carries it too**, copied off `config` onto every rung by `growth.py`, for
the same reason at one remove: a ladder is a series taken over weeks, and a rung
drawn after the ruling is not comparable with one drawn before it, so each says
which it is rather than leaving a reader to date it.

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

### The per-mode ceiling — `threads` at a fifth, and it is a guard

**`solve.DEFAULT_MODE_CEILINGS = {"threads": 0.20}` since 2026-09-05. Matt's
ruling.** It is `{}` for every record before that, so a record that does not name
`config.mode_ceilings` ran with **no per-mode ceiling** and is not comparable with
one that ran under this.

**It is the spiral share cap's shape, deliberately.** A fraction of the seats
**filled** rather than of `n`, through `ceiling.share_of` — the one spelling a
colour target is also stated in — evaluated at `ceil(share x (filled + 1))`, with
the same `+ 1` warm-up: without it the first seat of an empty gallery is refused
for taking 100% of nothing. It is a **set** constraint, so the 1-swap loop can
trade inside a capped mode instead of writing the mode off; and it is counted
**last**, after `spiral`, so the `mode_ceiling` column counts seats the ceiling
cost and not seats a colour allowance would have refused anyway. Everything
`spiral_allowance` argues about why a swap needs no second spelling applies here
unchanged.

**What it is set against.** The post-8h n=1000 census: `threads` took **187 of
1,000 seats** on a pool it is 2.5% of — **7.5x a pool-mirror and 6x its own floor
of 31**, the largest such gap on the roster, against `smooth` at 0.26x its mirror
on 62.7% of the pool. A fifth is above the 187, so it is a guard against a runaway
and not a target, and **the reading it gives is the refusal column**.

**It does bind, and the pin says where.** The n=1000 pair was taken over one pool
in `FIX_owed_minor_0905`, and the uncapped arm reproduces the on-disk
`tentative_n1000_20260905T153850Z` **key for key** — so the pool had not drifted
and the two arms differ in the ceiling alone. They are not the same gallery:
**53 candidates were refused `mode_ceiling` and 71 of the 1,000 seats turned
over.** The objective is identical on the three tiers that matter — 1,000 seats, 0
shortfall, worst seat 0.151677 either way — and the capped arm is **better on tier
4**, sum 589.431 against 590.576.

And what it did to `threads` is the opposite of what a ceiling reads as: **187 →
190 seats.** The finished gallery never touched the ceiling, whose allowance at
1,000 filled seats is 201; `stripe` gained 5 and `smooth` lost 4, with eight of
the thirteen modes moving by 1 to 5 and five not moving at all. So the ceiling did
not hold a mode down — it perturbed the walk, and the walk found a better gallery.
That is the shape doing it rather than the number. `ceil(0.20 x (filled + 1))` is
evaluated **during the walk**, and the walk fills by scarcity — so a mandated
`threads` seat drawn at seat 40 meets an allowance of 9 whatever the final count
would have been. The spiral share cap has been binding for the same reason since
2026-09-04. A ceiling denominated in `n` would not bind here and would also not be
a ceiling on anything until the gallery was finished.

**Three answers, and `MODE=0` is not the spelling for `none`.**
`--mode-ceiling none` (or `off`) clears every ceiling to its left and is how the
uncapped arm of a counterfactual is spelled; `--mode-ceiling threads=0` runs a
ceiling whose allowance is zero, so `threads` may take no seat at all and the
column fills. The flag is **repeatable and folds left to right onto the shipped
ceiling**, so `--mode-ceiling smooth=0.5` adds a second mode and keeps the first.
A mode no gallery can seat is refused at the flag rather than at the seat, for
`ceiling.parse_target`'s reason: a ceiling on a misspelt mode can never bind and
would read on the record as a guard that held.

**On `config`, and on a growth row.** `config` is what a tentative gallery's
tracked `manifest.json` carries whole, so a tracked gallery can say which ceilings
ran; a record also carries `mode_ceilings_default`, so a reader of an uncapped
record does not have to date it. `growth.py` copies the block onto every rung for
the spiral cap's reason at one remove: a ladder is a series taken over weeks.

**It applies at every `n` and to a themed pass too.** A theme narrows the colour
and says nothing about the mode, so a runaway is a runaway there as well — it is
not one of the three things `--themed` swaps. Two of the six themed n=200 reads
saw it act, at 1 and 10 refusals, and both gained a seat over the q4 bar by it.

**The collision it can have is with a mode floor, and the objective already
answers it.** At small `n` a fifth of the filled seats is one or two, so a floor
asking for more goes **SHORT** and `shortfalls.modes.per_mode.<mode>.refused_by`
names `mode_ceiling`. Unfilled beats padded: nothing is seated by relaxing a rule
it failed. At the shipping rungs the two are far apart — `threads` floors at 31
against an allowance of 200 at n=1000.

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
sigmoid( b0 + b1 loc_p_ge4 + b2 p_ge3 + b3 p_ge4 + b4 flat16_1.0 )
```

the location head's `P(>=4)` for the place, the render judge at **both** cutpoints, and
the flatness column, each standardized by the fit's own constants.

**Four columns since 2026-09-06**, and the fifth is worth knowing about. It was a
calibration stratum, `composite` 2 / `other` 1 / `thin_colour` 0, and the bottom level
read the colour-expression census's thin-swatch list — so the key had a soft colour
nudge in it, acting
at the solve and again at the merge prune where it deletes rows permanently. Matt ruled
that out: the colour ceiling already holds any one colour down as a hard constraint at
the seat, and no cell is owed seats.

**What that cost, on one population and one partition.** Refit over the same 1,051 rows
and the same folds, dropping the column loses **0.025 of AUC on strange**
(`0.850 → 0.825`, `[-0.038,-0.012]` on a lineage-grouped paired bootstrap) and takes the
whole margin over the raw judge with it; smooth is unmoved at `+0.004 [-0.016,+0.024]`
(`0.779 → 0.783`). **None of that loss is the colour half.** Keeping a bare composite
indicator and dropping only the thin level costs `-0.002 [-0.007,+0.004]` on strange;
keeping the thin level and dropping composite costs `-0.012 [-0.019,-0.006]`. The signal
was the *mode*, wearing a colour term's name. No composite column replaced it — that is
a decision left open, not an oversight.

The five-column form was fitted on 2026-08-28 over those 1,051 label rows that join the
ledger (342 smooth / 709 strange, 625 lineage groups, tier mix 1.2 / 31.1 / 41.7 /
26.0%) and read out of fold **0.779 smooth against the incumbent's 0.671** and **0.850
strange against 0.826**. Those are the shared-weight figures; the *per-kind* arm with a
nested inner selection reads higher and is not what ships. `curate rank-key fit`
re-joins the stores as they stand and prints its own, over a larger corpus than that.

**Shared weights over both stores**, and per-kind is unresolved on every arm tried. On
the five-column form specifically it was `+0.018 [-.002,+.039]` on smooth and
`+0.005 [-.005,+.014]` on strange — the `+0.000 [-.011,+.012]` the ruling cites is the
*three-column base* arm, and neither has been re-taken on the four-column one. Shared is
also the only fit the folds support, since 96 of the 625 lineage groups span both stores
and carry 348 of the rows.

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

`ceiling.TAU = 0.034281` in the pixel-cloud metric, against every already-seated
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
| one wallpaper? | `ceiling.TAU = 0.034281` in the pixel cloud | set-level, last rule of `curate solve` |

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

**The walk is quadratic in places, and it was the pool that grew rather than the
code that slowed.** `READ_solve_bound_and_profile_0904` read the pre-selection at
22.52 s against about 12 s a fortnight earlier and could not say which it was. The
walk asks each offered place for its distance to every place already kept, and the
retired spelling gathered those kept rows with a fancy index — which **copies**: at
8,740 places over 384 columns that is tens of gigabytes of memcpy in a pass.
Measured 2026-09-04 on one pool, the same walk truncated to a share of its places:

| places offered | fancy index | contiguous block |
|---|---|---|
| 2,185 | 1.64 s | 0.86 s |
| 4,370 | 5.28 s | 1.05 s |
| 6,555 | 11.44 s | 1.30 s |
| **8,740** | **20.22 s** | **1.61 s** |

Four times the places is **12.3x** the time on the old spelling — an exponent of
1.81 — and **1.9x** on the new one, which is sub-linear because what is left is the
store read. So there was no regression to find: `places_asked` went 6,982 on
2026-09-02 to 9,314 on 2026-09-04, and 1.334 squared is 1.78. Writing the kept
descriptors into one preallocated block and reading a contiguous prefix of it takes
the shipped pool's walk from **21.02 s to 1.69 s** with the same kept set, the same
refusals and the same distances. `tests/test_distinct.py` pins the two spellings
against each other at three radii, because "the same values" is a claim about a BLAS
kernel and not something to assume.

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

## `curate growth` — what more mining buys, at every gallery size

The question a mining leg is bought to move, asked with numbers: **does N
candidates' worth of mining buy a better gallery, and at which sizes?** Nothing in
this repository can answer it from the history, because the history was never
snapshotted — the candidate ledger is a live store that grows and is pruned, and
no copy of the pool as it stood in August exists to solve against.

So `curation/growth.py` asks it the other way round, from the pool as it stands.
Draw a **fraction of the visits** that made this pool, solve the gallery over what
those visits produced, and read the curve off the rungs. Re-run after each mining
leg, it accumulates a chronological series on its own: each run is a new stamped
folder under `artifacts/curation/growth/<stamp>/`, nothing overwrites a
predecessor, and the top rung of the next run is the pool this one could only
reach by extrapolating.

```
fractal-wallpapers curate growth run                    # the whole ladder
fractal-wallpapers curate growth run --fraction 8 --n 1000 --name probe
fractal-wallpapers curate growth plot <stamp>           # six PNGs into scratch/
```

### The unit of subsampling is a VISIT, and that is the whole design

A **visit** is `(location, leg)` — one mining leg opening one place, read off each
ledger row's `location.key` and its `provenance.run`. Drawing *rows* instead would
not be a smaller history: it would be the same history with the depth arm silently
switched off, and it would price a place at a twelfth of what a place costs. A
visit comes with every candidate row it produced, whole.

Rows carrying no `provenance.run` — the pre-ledger imports — form **one pseudo-leg
per location**, so each such place is a visit of its own rather than one enormous
visit nothing could subsample. On this store today that case is empty: all 177,993
rows name one of 54 legs, over 21,813 places and **27,630 visits**.

### Restricting the pool is the only change, and that is enforceable

Every rung is solved by `solve.solve` with nothing but `n` and the restricted
candidate list — no radius, no cap, no draw seed, no floor of its own — so a rung's
gallery is the gallery `curate solve run` would have chosen from that pool.
`tests/test_growth.py` pins it by solving the top rung twice, once through the
sweep and once directly, and comparing.

The fitted rank order is computed **once** over the whole pool and restricted,
which is identical to computing it per subsample: `rank_key.order_for` scores each
candidate against a key loaded from disk and never against its neighbours. That is
what makes 114 solves affordable — the flatness sidecar and the location readings
are read once instead of once a cell.

A subsample that cannot fill `n` is a **finding**, not an error. That is the curve.

### The output schema is the durable part

`growth.jsonl` is what the website's `pipeline-growth` figure bakes from, so the
schema is documented at the top of `growth.py` — every field, its unit, and which
of them are approximate — and `curation/growth_plot.py` is deliberately not its
only reader. Two labels are approximate and say so on every row: `attempts` counts
the ledger rows *surviving* in the drawn visits, and retention keeps three per
`(location, mode)`, so it is a floor on what was attempted; `mining_seconds` sums
`hunt.seconds` over the same rows and is blind to any row written before that
stamp existed. Both are summed over the visits actually drawn rather than scaled
from the nominal fraction, because the draw is random and its realized effort is
not its expected effort.

`manifest.json` beside it carries the **pool stamp** — a sha256 over the sorted
candidate keys — which is what says whether two runs are comparable directly or
only as a series.

The plots are `scratch/growth_<stamp>/`: fill %, seated median, seated p10,
selection lift, floors met and colour spread, all against `n`, one line per rung
with a min/max band across the three seeds and a legend in millions of attempts.
`matplotlib` is **not** a dependency of this project and is not in any extra — the
jsonl is the product and the pictures are a convenience — so `curate growth plot`
refuses with the install line if it is absent: `uv pip install matplotlib` against
the checkout's `.venv`, which is what this machine has.

**Four finished labeling subtrees are on the archive tier as of 2026-09-02** —
`mode_sheet`, `calibration`, `correction` and `palette_mass_sweep_calib`, 0.57 GiB over
1,577 files. They were promoted to **top-level names** first and archived as
themselves, because the unit of tiering is a top-level name and `curation` is the live
pool: archiving one of its children in place would put `curation` in both tiers and
every `under("curation", …)` would raise `TierCollision`. Nothing addresses the four by
path, so the promotion costs nothing; each comes back with one command, e.g.
`fractal-wallpapers storage restore mode_sheet`.

## `mode_policy` — what standing each mode has, in one table

`curation/mode_policy.py` is the only place a mode's standing is written.
`MODE_POLICY` maps every one of the engine's nineteen **production** modes to a
weight in `{0, 1, 2}` — six niche, six normal, seven promoted — and
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

**A recorded gallery seat's `mode` is the ROUTED mode, and the catalogue mode is
only on the ledger row.** `solve.pool` takes `routed_mode_of` before it asks the
roster and the seat carries what came out, so `tentative.rows_of` writes it to
`gallery.jsonl` and a reader comparing that against the ledger's `recipe.mode`
finds them unequal on exactly the degenerate modulates. **The one place the
catalogue mode can be read back is `recipe["mode"]` on the candidate-ledger row the
seat's `key` names** — `recipes.of_record(row["recipe"]).mode` — and it sits on the
same row as the `texture_flat` boolean that explains the difference, so nothing is
lost and no reader needs a workaround. Measured on stamp `20260902T161757Z`:
**18 of 746 seats** disagree, every one of them seat `smooth` against recipe
`itinerary`, and every one carries `texture_flat: true`. They span nine run stores,
so it is not a property of one leg. Ten of the eighteen were rendered after the
engine began reporting the flag and carry its own word; the other eight predate it
and were filled by the backfill register, where `texture_flat.flat_for` answers
`true` for all eight and `false` for the ten it was never asked to probe. Both
routes agree, and `routed_mode_of` answers `smooth` for all eighteen.

**The same shape a record later, and the incident that says why it is worth
repeating.** On stamp `20260904T023748Z`: **17 of 914 seats**, every one seat
`smooth` against recipe `itinerary`, every one `texture_flat` — no other seat of
the 914 disagrees with its recipe, so the disagreeing set is exactly the routed
one at both sizes. **A leg that read `gallery.mode` and re-rendered at it drew 17
wrong pictures and reported them as stale files**, a finding that survived until
the seats were re-rendered at `recipe["mode"]` and came back sha256-identical, 17
of 17. A reader that renders a seat renders at `recipe["mode"]` on the ledger row
the `key` names; `gallery.mode` answers which pile the row is *counted* in and is
not a render instruction. The site does not make the mistake — `picks.wallpaper_row`
reads `recipe["mode"]` and draws all 17 as `itinerary`.

**The row's `mode_params` are the recipe's and its `mode` is the routed one, and
they are deliberately not taken from the same place.** A seat carries the settings
the picture was actually rendered under — `recipe.mode_params`, off the ledger row
`solve.pool` built the candidate from — so `direct_trap_multiply` at `opacity=0.6`
is a different gallery row from the bare mode instead of being indistinguishable
from it. The pairing is only ever a spelling and never a claim that a roster named
that pair: on the eighteen routed seats above, the mode says `smooth` while the
settings belong to the `itinerary` recipe underneath. A reader that needs the
catalogue mode joins to the ledger on `key`, exactly as this section already says.
The field is **forward only** — every record written before it carries no
`mode_params`, and an absent one reads as `{}`, which is also what a bare seat
writes, so nothing tracked was rewritten and the two spellings are one row.

**The 0 is wired in three places.** A weight-0 mode is out of
the **labeling rosters** and the **default mining rosters** (both through
`colorize.modes_for`, `mine._mined_modes` and `hunt.plan`, so the mode draw, the
mine, the hunt and `manufacture` all honour it), out of the **depth roster**
(`depth.field_modes`), and out of **gallery emission** — `solve.pool` refuses the
row and counts it as `niche_mode`, which is the one pool both the greedy seating
and the census read. The mode floors in `solve`, `headroom` and
`candidate_ledger.feasibility` are asked of `accepted()` for the same reason: a
floor over a mode with no rows in the pool is a mandate nothing could meet.

### `UNMINED` — out of the mines, in the gallery

**A second list beside the weights, and a different axis from them.** `curvature`
is on it, Matt's ruling of 2026-09-06, and the standing is about **quality**: its
pictures are rarely good and the gallery only wants a handful, so buying more of
it buys material the gallery will not seat. It is not recorded as expensive — that
would invite the wrong repair, which is to make it cheaper and start mining again.

**Why not a weight of 0.** A 0 answers a bigger question than the one that was
asked. It takes a mode out of `accepted()` and with it `solve.pool`, the seat
floors, the per-mode bars, the census axis and gallery emission, and it **strands
places** — 574 locations and 17 seats the last time a mode was ruled 0. The ruling
here is that the gallery keeps its handful; a 0 would take the handful away.

So an unmined mode is **accepted in every respect but the draw**. `mode_policy.mined()`
is `accepted()` less `UNMINED`, and it is what `mine._mined_modes`, `hunt.plan`'s
roster and every `depth` roster derived from them read; everything that asks *may
this be seated, censused, barred or floored* still asks `accepted()` and cannot
tell the difference. `depth.deficient_modes` reads `mined()` too, because what it
answers is what the floor arm should go and buy. `mode_policy.check()` refuses a
name in `UNMINED` that `accepted()` does not hold, and both `check()` and
`record()` carry `mined` and `unmined` so a leg read back later can say whether a
mode was absent because nothing drew it or because nothing could.

**What still draws it**: a leg naming it in `--modes`, and `curate remode` as a
target — both are somebody naming the mode out loud, and the standing is a default
rather than a prohibition. `curvature` was a **field** mode, so `depth.field_modes()`
is three where it was four; the dear nine and `centered_modes()` are unchanged.

**The stock the floor is protected by**, read 2026-09-06 over the pool at the
per-mode bars with the census's own 0.02 neutral pre-selection: **345 clearing
locations over 496 rows**, against a floor of **3 at n = 200** and **16 at
n = 1000**. Fifth-largest stock of the twelve strange modes. That is the number the
ruling is revisited against, and `curate headroom` is where it is re-read.

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
10,000-hour frame, `N / 100`, "novelty is worth a 3" — and the measurements under
*What the rule does, measured at n = 150 under routing* in
[`MEASUREMENTS.md`](MEASUREMENTS.md) are a pathology check that passed rather than
the case for the rule. The open
question the flip leaves is the price, which is what the reject autopsy is for.

```
curate solve run --n 150 --name n150                     # floored per mode
curate solve run --n 150 --flat-floor --name n150_flat   # the flat floor, for a baseline
python -c "from fractal_wallpapers.curation import mode_policy as m; print(m.seat_floors(1000))"
```

### Every mode's capabilities, in one table

What each of the nineteen production modes can do, so nothing in
[`LEGS.md`](LEGS.md) has to say it again in prose. Every column but the last is
read straight out of code — `colorize.kind_of`, `colorize.shareable`,
`autolevel.applies_to`, `MODE_POLICY` —
and re-deriving it is `python -c` over those four names, never a measurement.

| mode | kind | shareable / field dumpable | `autolevel` | weight | bar |
|---|---|:-:|:-:|:-:|---|
| `smooth` | field | yes | yes | 1 normal | `P(>=4)` |
| `tia` | field | yes | yes | 2 promoted | `P(>=4)` |
| `stripe` | field | yes | yes | 2 promoted | `P(>=4)` |
| `exp_smoothing` | field | yes | yes | **0 niche** | none |
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
Six niche, six normal, seven promoted; thirteen carry the autolevel operator
and seven are shareable.

**Three of the seven field modes are niche**, which is why the shareable column
and the weight column have to be read together: shareable says a dumped field can
serve the mode, and weight says whether anything will ask. `exp_smoothing` is the
newest of the three and the only mode on this table demoted for **duplication** —
see `mode_policy`'s own paragraph on it.

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
