Turning compute into new good material where it is scarcest: the census, the
price, the allocation, and the loop that spends the clock on them.

A walk finds places. This package decides *which* places are worth finding next,
keeps deciding for hours, and can say afterwards where every minute went.

```
partitions   what the books are kept separately for
release_mix  one ratio table, shipped as data
currency     what a find is worth, and where the cuts are
location     what "the same location" means, once
ledgers      the union of everything every walk has found
census       stock, target, and the standing deficit
prices       cost to find: the measured estimate and the seed it starts from
apportion    a share vector into whole slots, without zeroing anybody
allocation   the floor, the water-filling, and the floor's carry
quota        the object a run holds; the only thing that decides the mix
refill       what to do about a partition whose queue has run dry
twins        Julia parameters derived from the parent plane's admissions
proven       roots at every location a human scored a keeper, at the frame they scored
saturation   cross-run memory, straight off the ledgers
novelty      the two levers against monotony: the discount and the share
autopsy      what each claim on the batch bought, in pictures — and why each refusal was one
tau_h        how good a cheap look must be before a real one is paid for
harvest      the production loop, and everything that keeps it honest
```

The loop is small to state:

```
census    what each partition holds, against what the release mix says it is owed
price     what a unit of currency costs there, measured as the run goes
allocate  intended share of the clock ∝ deficit ÷ price, with a floor everyone gets
serve     divide the batch's slots by how far each partition is below its intent
credit    what the batch found, deduplicated, back into the price and the stock
```

A batch's slots are claimed in a **ruled order**, and it is one-directional —
nothing below may eat what is above it:

```
1  floor      the carry's claimants, guaranteed their slot
2  share      the protected exploration fraction of what is left
3  contest    the deficit-priced rule over the remainder, lineage-discounted
```

**What a find is worth, and what a partition is therefore owed.** Currency is
`n4 + 0.1·n3` — `currency.CLASS_WEIGHT`, one table read by the standing deficit,
the in-run price and the readout alike, so moving a weight moves all three. A 4 is
the unit and a 3 is a tenth of one; 1 and 2 are recorded and worth nothing. Stock
is two legs and a location is in **exactly one**: the human's class where a human
has looked, and `MACHINE_STOCK_DISCOUNT` (0.2) × the machine's class where nobody
has. That is **precedence, never addition** — a labelling sheet is cut out of
ledger rows, so a location can be in both corpora, and adding the legs would count
it twice at a weight nobody chose. The discount sits well under the ~50% rate at
which machine-called keepers survive a human look, deliberately: a machine-filled
partition keeps a mild standing appetite until labels re-anchor it.

**The standing deficit is a launch snapshot.** The quota re-allocates every batch
because the *prices* move; the censused deficit does not, because human labels do
not arrive mid-run. So what changes inside a run is the price and the realized
share of minutes, and nothing else — a run's mix is steered against the stock it
opened with.

What follows is worth reading before changing anything here.

**A Julia twin's supply is manufactured by serving its parent.** The allocator
has always folded a twin's demand into its parameter plane on the ground that
descending the plane is what produces places worth taking the twin of — but for
the three higher degrees the step that turned a plane find into a Julia root did
not exist, so the fold was a promise nothing kept. `twins` is that step: an
admitted degree-`d` plane location's centre *is* a `c` for the degree-`d` Julia
family, and it becomes a root through the same seed object and the same cursor
the tracked degree-2 pool uses. Parameters closer than the pool's own c-spacing
floor to one already taken are skipped and recorded.

**The best mandelbrot supply this project has found came from its own labels.**
A dedicated 95-minute leg rooted the walk at the 471 distinct locations a human
had scored q3+ and interleaved them 2:1 with never-walked plane-pool roots. The
seeded roots put 91.6% of their finds over the junk floor and 53% of the sample
over the smooth head's advisory; the fresh roots returned the partition's historic
rate — 21 rows over the floor out of 333, one clearing. `proven` is that channel,
derived live from the label store rather than from a file, so a keeper labelled
this morning is a root this afternoon. It is off unless a run names it, and it is
interleaved rather than substituted: a channel fed by this project's own past
output cannot open new ground, and it runs out at the rate the store grows.

That leg was one plane. Re-measured across all four parameter planes over a scored
active hour, the gap is wider rather than narrower: **135 proven roots returned
3,228 of the run's 3,303 admissions, and 61 never-walked pool roots returned 75**.
130 of the 135 produced at least one admission; 14 of the 61 did; the four
`home_view` roots produced none. The margin holds at every degree, and it is
largest at degree 2, where the pool's seven roots returned nothing at all.

**On the dynamical partitions the channel buys a frame, not a sampler.** Julia
and Phoenix have pools; a pool row is a *parameter*, so every root either one
hands over comes up at the family's home view and the walk descends from there.
A label row carries the frame the human scored. Measured over 30 active minutes
across `julia:mandelbrot`, the three twins and `phoenix`, proven roots on:

```
              served   admissions   per root   booked >=1   already walked on entry
proven          252         7,315       29.0    249 / 252              95 / 252
twin             74         1,079       14.6     62 /  74              68 /  74
pool             50           551       11.0     21 /  50              47 /  50
```

**Re-measured a third time on 2026-09-01, over ten active minutes with every
partition served and the channel on, the margin is wider still**: of 128 roots
served, **90 were proven and they returned 1,690 of the run's 1,789 admissions
(94.5%)**. The rest is a rounding — 6 twin roots returned 57, 2 `ranked_harvest`
pool roots returned 41, and the **21 `nucleus_grid` plane-pool roots and 4
`home_view` roots returned nothing at all**. A quarter of the roots this run
served booked zero. Note the root row says which channel it came from under
`provenance.channel` and *not* under `source`, which names the pool file the
entry was read out of: a tally by `source` puts 115 of these 128 roots under
`seed_file` and cannot see the channel at all.

Cost came out at **0.19–0.22 s/admission**, against 0.26–0.38 for the same five
partitions on run10 with the channel off. The margin is widest where the pool is
weakest: **2 of 29 phoenix `c`-pool roots booked anything at all**, against 57 of
59 proven ones. And the entry column is the surprise in the other direction — a
home-view root is the same point every prior run rooted at, so 90%+ of pool and
twin roots enter already saturated, where a labelled frame enters clean about two
times in three. Run the leg with `--partition <dynamical> --root-channel proven`.

**Four things about the channel are decided in `proven.py` and nowhere else.**
Its **tier floor is `min(currency.CLASS_WEIGHT)`** — the currency's own bottom
class rather than a fresh cut, which is tier **3**, so what counts as a proven
place is exactly what counts as a keeper and moving one moves both. It serves
**every registered partition**: `proven.SERVED` is `ALL_PARTITIONS`. It excluded
`phoenix:classic` until 2026-09-02, which left that partition's q3+ labels the
only ones in the store that became no roots; its queue now interleaves those
labelled places through the single home-view root a pinned plane has. The pool is
**interleaved at
`RATIO` (2) proven entries per pool entry**, never substituted: a channel fed by
this project's own past output cannot open new ground, so the fresh pool has to
keep coming through it. And the queue is ordered by a **digest of the location
key**, not by a shuffle — best tier first, and inside a tier by
`blake2b(key)`. That is what makes a resume exact: the order is the same on every
machine and stable as the label store grows, so a cursor one insertion ahead
costs one root served twice rather than re-ordering everything behind it. The
root id is that same digest, so a root's provenance names a place rather than a
position.

**`externally_supplied` was a declaration with no supplier behind it, and it is
gone.** Audited 2026-09-02 (`AUDIT_phoenix_classic_funnel`), removed the same day.
The flag cost `phoenix:classic` three separate things — share `0.0` from
`allocation.allocate` before the floor loop ran, a first-and-unconditional `False`
from `refill.has_channel`, and exclusion from `proven.SERVED` — and **no job
outside the walk ever filled it in this repository.** Measured consequence: **0
candidate rows across all 41 walk ledgers on both tiers**, and therefore 0 in the
supply sidecar, 0 embedded, 0 in the candidate ledger and 0 eligible — against
3,336 admitted and 452 eligible for varied `phoenix`. Nothing downstream refused
it; the location head clears 6 of its 7 q3+ labels over the junk floor. **The
lesson is the third consequence rather than the first two**: a partition can be
declared out of the walk and starve in complete silence, because the same
declaration takes it out of the census that reports starvation. The flag and its
plumbing are deleted rather than set false — `Allocation.external`,
`FloorLedger.external`, `Quota.external`, `Refill.external` and
`release_mix.is_externally_supplied` are all gone — so there is no held-out set
for a partition to be put back into.

**Measured on the first leg that ever walked it** (2026-09-02,
`CRAWL_phoenix_classic_30min`, 8 roots, proven channel on): the leg stopped on
`nothing servable` at **0.66 active minutes of a 30-minute budget** — 120 frames,
97 scored, **8 admitted (6.7%)** against 54.0% for varied `phoenix` on a
comparable leg, 74 refused at the junk floor. **All 8 admissions came from proven
roots; the one fresh home-view root returned zero**, and only 2 of the 8 roots
booked anything. It died because `growth_per_expansion` came out **0.767** — under
1, so a frontier fed only by its own admissions shrinks — and the in-walk
reframing channel cannot prop it up: `reframing_undefined` fired on all 23
frontier nodes, because a dynamical viewport has no parameter-plane nucleus. **The
partition's supply ceiling is `1 + its labelled q3+ places`**, which is 8 today.
By the walk's own saturation distance 5 of the 8 admissions sit inside an earlier
one, so the plane converges on a few basins rather than offering variety.

**A pinned plane's fresh-root pool is one row, by construction.** No tracked pool
held the classic point: the phoenix seed pool's 96 rows all resolve to varied
`phoenix`, the plane pool and the deep run's anchors are parameter planes only,
and `data/anchors.jsonl`'s one classic row feeds engine comparison rather than
supply. `pools.classic_phoenix_pool()` is that missing row and there will never be
a second: the plane is one parameter point, so the only thing a fresh root can
vary is the frame, and varying the frame is what the walk does. Every further
*place* comes from the proven channel.

**The mix is decided where the batch is popped.** Weighting the *root draw* by
family cannot enforce a mix: anything that only changes what enters the frontier
is diluted by whatever multiplies fastest inside it. In the source project an
intended seventy-percent share realized at under twenty.

**Steering a mix is not enforcing one.** A per-batch argmax on price-weighted
deficit steers without ever measuring, so a stale price or an unrepresentative
first hour moves the realized share with nothing to pull it back. The quota
computes an intent, tracks realized *minutes*, and serves whoever is furthest
below.

**An entitlement that does not accumulate is not an entitlement.** The share gap
saturates at the intent, so a floored partition's claim is the same at the first
batch and the three hundredth. Unspent floor time is carried in minutes, and
comes due at batch twenty at a 5% floor — whatever a batch costs.

**A harvest's clock used to be mostly the steering view, and that line is gone.**
The head reads its verdict off the gate render `expand` already wrote, which is
byte-identical to the same location's tile at the node regime, so a harvest draws
no picture for scoring at all. What that removed is the line every earlier profile
here named first: rendering the deploy-geometry view was 56% of a batch's seconds
over three profiled batches, three quarters of a 135-active-minute harvest's active
clock (6,974 views, 6,096 s, none reused), and **58.7% of a whole production run's
clean wall** — 8,810 s of run9's harvest leg. A harvest's clock is now the engine's
own expansion rung and almost nothing else, and inside that rung the first place to
look is the focus finder rather than the escape-time iteration.

**`--score-workers` is a flag with almost nothing left to do.** It never paid even
when there were views to fan out: the engine's own thread pool already saturates a
twelve-core machine on a single view, so worker processes re-slice the same silicon
rather than adding any. Measured on an idle machine over the same 96 real views,
wall seconds against `--score-workers 1`: two workers **0.88x**, four **1.01x**, six
**1.02x** — and at four the same 93 s of work reports 348 task-seconds, a 3.74x
inflation that cancels the fan-out exactly. run9 paid that penalty for real at four
workers: 1.73 s/view wall against 0.969 s/view serial. The flag stays because
curation's re-score of an old ledger still renders, and because a claim that
concurrency does not pay is worth being able to re-run. `curation.release` fans out
for a different reason and does earn it — half a release row is single-threaded
Python that leaves cores a sibling engine can take, worth 3.19x over four workers on
the same machine.

**Four levers stand between a long run and one composition, and they act at
different heights.** The walk's per-root expansion cap bounds what a root may
*spend*; the per-lineage admission cap (`--lineage-cap`, off by default in a
harvest and on for a deep run) bounds what it may *book*, and is the hard stop.
Under it are two soft ones in `novelty`, both run-command parameters and neither
stored on a row. The **lineage discount** multiplies a lineage's expected credit
by `max(f, 1/(1+k·n))` where `n` is that lineage's admissions *this run* — in the
contest only, evaluated at the pop rather than baked into the priority, because
`n` moves after a node is pushed and the Gumbel must not be re-rolled. The
**exploration share** reserves a fraction of the post-floor slots for roots whose
neighbourhood *no ledger* has ever booked an admission from, and prices that
fraction against its own admission rate. Inside the share the head ranks and only
the junk floor kills; the discount never reaches it.

**The exploration share cannot reach a floored partition, and the partitions with
the most unwalked ground are the floored ones.** Measured over a ten-minute
all-partition leg on 2026-09-01: the four julia twins carried a **non-empty
novel-root queue in all 114 batches** — peaks of 50, 53, 46 and 66 roots no ledger
had booked from — and took **0 of the run's 326 exploration slots** between them,
against 179 to `mandelbrot` and 84 to `multibrot3`. The mechanism is on every
quota card as `share.weight_source`, which read `intent` in all 114: the share is
drawn over the post-floor pool weighted by each partition's *intended* share, and
a partition whose intent is the 0.05 floor has spent that intent on its floor
slots, so it carries a vanishing weight in the draw that follows. With `wanted`
at one or two slots a batch, a floored partition essentially never wins one. The
run-wide realized share was **0.424**, comfortably over the 0.25 floor, which is
why the run-wide number cannot see this — `quota.exploration.realized.per_partition`
is where it shows, and a partition reading 0.0 there with a non-empty
`novel_queues` entry is this. Nothing is broken: the floor and the share are two
levers that compose badly, and which one should give is not settled here.

**A run's `--ledgers` names one root, and the two cross-run indexes are only as
wide as it.** Both `saturation` and `novelty` read the tree that flag points at,
and the flag's default is the literal string `artifacts`, which resolves through
`cli.resolve_output` to the **hot** tier — so a checkout whose production runs
have been archived builds both memories out of whatever happens to be local.
Naming the archive root explicitly is how a run gets the whole history, and it
costs one pass per index over every ledger there. `ledgers.ledger_paths` is the
one place that answers how many that is: with no root it searches **both** tiers,
with a root it searches that one, and the three counts move every time a subtree
changes tier — so ask it rather than quoting a number, and a run that prints a
ledger count smaller than expected is a run pointed at one tier.

**A finished run's saturation verdict is re-derivable, exactly, and that is what
makes "novel" a readable property of a frame afterwards.** The index is a pure
function of the ledger set and the radius, so rebuilding it from the run's own
`--ledgers` root with the run's own ledger excluded — `saturation.build(paths=
ledgers.ledger_paths(root, exclude))` — and asking `VisitedIndex.density` about
each candidate's centre reproduces what the run decided. Rebuilt against run10 it
comes back at 65,022 visits over 26 ledgers in 420 identity buckets, and its
`seen`/`discounted` split lands on `tally.saturation_by_partition` row for row.

Two things that reproduction settles. **`saturation.seen` is the frontier feed,
not the candidate count** — `_apply_memory` asks only about survivors, so a
`not_admitted` row and every structural refusal carry no run-time verdict at all
and have to be queried after the fact, with the same index, to be classed either
way. And on run10 **not one admission on any parameter plane sat on undiscounted
ground**: 0 of 1,313 `survived` rows across mandelbrot and multibrot3/4/5, against
1,419 of 3,966 on the dynamical planes and phoenix. A draw conditioned on novelty gets
nothing from the four planes at this point in their history, and that is the
readout's 100% discount rate seen from the other side.

**A slot is not a minute.** The quota allocates the clock and hands out node
slots, so the slot demand is the minute demand divided by what a slot has been
costing in that partition. Being cheap buys more turns, not more time.

**An active minute is not a wall minute either, and `--minutes` counts the first
kind.** What is charged is `expand` plus `trigger_reframings`, per partition, per
batch. Three things are outside it: the start-up before the first batch — the
head onto the device, the proven derivation, the saturation index, the twin
channel, about a minute together — the per-batch refill, and the closing gate-flip
re-score, and the closing `curate score` over what the run found. The ratio has
**two measured values and the run's own config picks one**: a scored hour over the
four parameter planes that *drew its own views* measured **1.13× wall per active
minute**, and run10 — which scored the gate renders the walk had already made, so
`scoring.rendered` stayed at zero all night — measured **1.013×**. Reserving 1.13
for a night of the second kind cost run10 36 active minutes. Size a leg on the
ratio that matches how the night scores; `--minutes` alone will under-book the
clock either way, and the tail lands after the last batch rather than inside it.

Both are constants of `fractal_wallpapers/schedule.py` —
`ACTIVE_TO_WALL_DRAWING_VIEWS` (1.13) and `ACTIVE_TO_WALL_SCORING_GATE_RENDERS`
(1.013) — and **the run's own config picks between them, not the caller**: a run
that scores the gate renders the walk already made books 1.013, and one whose
judge draws its own views books 1.13. `schedule.plan` prints which it used and
why, so a night that lands late names the ratio it was reserved under instead of
leaving a reader to guess which kind of night it was.

**A run told one partition allocates its whole clock there.** `--partition` is
repeatable and defaults to every registered one; naming one keeps the books for
that partition alone, and its census, its price and its refill census all cover
it alone. That is a different object from a full run with a thin mix, and the
summary says which it was.

**Every batch reconciles, and a batch that does not balance ends the run.** Three
identities have to close: every candidate the engine reported was written with a
fate this project knows, everything that reached the frontier was either admitted
or expandable, and every admission is either a new location or one the run
already had. `ReconcileError` is a `SystemExit`, so the failure is a non-zero exit
rather than a line in a log — a long unattended run that silently loses
candidates is the one failure a summary cannot show afterwards, because the
missing rows are missing from both sides. The checkpoint (`harvest.STATE_SCHEMA`,
**5**) is written at the batch boundary *after* the reconcile, so every state a
run can resume from is one whose identities closed; what it holds is the
frontier, the counters, the quota's realized tallies and price accumulators, the
floor ledger's accrual and the random state.

**A checkpoint of an older schema is REFUSED at resume, not adopted.**
`Harvest.resume` raises on anything but the current number, and each bump was
taken for the same shape of reason: a schema-4 checkpoint carries no per-partition
readout books, so resuming from one would reopen the share-against-contest split,
the head-score histograms and the saturation activations at zero and then report
medians covering the second session alone, with nothing on the page saying so.
Refusing costs a run; adopting costs a number nobody can tell is wrong.

**`--finish-by HH:MM` derives `--minutes` from the time the night has to end.**
The span to the next `HH:MM`, less what has to happen after the harvest — the
release leg at `--release-slots` x wall-per-picture, the rest of `curate run` at
2.57 s an attempt, the closing `curate score`, the ledger load and a 20-minute
margin — and then divided by the ratio above, because `--minutes` is active time
and the span is wall. `fractal_wallpapers/schedule.py` owns every term, prints the
derivation at startup and writes it into `summary.json` as `finish_by`, so a night
that lands late is attributable to the term that was reserved wrong.

Two of those terms are **read rather than written down**, because run10 landed 84
minutes inside its finish-by on terms that had each stopped being true:

* the **release rate** comes off the most recent tracked run's own release leg
  (`data/curation/runs/<run>.json`, `release.seconds / release.rows` at
  `release.workers`, scaled to `--release-workers`). It halved — 41.9 s to 24.9 —
  the night `artifacts/curation` came off the archive and back onto NVMe. The
  written-down 41.9 is the fallback for a clone with no release on record, and the
  plan prints which of the two it used;
* the **closing re-score** scales with what the harvest will find, since it
  re-reads the run's own gate survivors: 7.13 ms a row at 124.7 rows an active
  minute. That dependence is circular and `schedule.plan` solves it rather than
  iterating.

The **ledger load** is 2 min and used to be 11. It was never a load: three
builders each `rglob`ed the archive for `walk.jsonl`, which is 734.6 s a pass on a
tree that is mostly `tiles/`. They now share one list, found by looking each
ledger up at `<run directory>/walk.jsonl` — see `ledgers.ledger_paths`.

`--release-slots` defaults to the **ten** a run keeps as its diagnostic release
(`curation.run.DEFAULT_N`), so the reservation and the run it reserves for name
the same release without being told twice. It had no default while a release was
a number somebody chose per night; a run does not choose one any more.

The colorize term beside it is derived rather than restated. It is
`curation.budget`'s own answer for the shape the night will run — the release
ceiling, `--strange-share`, `--strange-modes` — asked through the same functions
the run will spend, because `schedule` used to keep copies of the attempt
multiplier, the strange share and the modes each head draws, and those were
correct only while all three were constants of the project. The mode table is a
parameter of a run now.

**It derives and does not pace** — the active-minute budget is still the only
backstop, and the margin is real money.

**The launch prints what each channel can still reach**, one line per partition:
the pool's size, how much of it the label store put there, what has been drawn, or
the reason no draw can serve it. run10 opened with 39, 46 and 52 derived parameters
in its three julia twins against 413 to 507 in each parameter plane; all of the
small ones ran dry inside the night and the readout is where that surfaced, the
following morning. The proven count is beside the pool count because a queue two
channels deep exhausts two ways — `pool julia:mandelbrot: 1036 of 1036 entries
left, 827 of them proven roots` — and running out of `c` and running out of
labelled places are fixed by different things.

**Redirect a harvest's stdout through `python -u`.** It is block-buffered
otherwise, so a backgrounded leg writes an empty log for its whole first stretch
and there is no way to tell a run that is loading its ledgers from one that has
hung. The startup itself is not quick — the novelty and saturation memories are
built over every ledger under `--ledgers` before the first batch, which was about
**two minutes and 115 CPU-seconds over 7 ledgers** on 2026-09-02 — so the silence
is long enough to be worth reading.

**`--minutes` is also the only backstop a harvest has** — there is no
`--wall-budget` here, that flag belongs to `curate run`. It is a hard one: the loop
refuses to *start* a batch when the spent minutes plus the running mean batch would
overrun, so an over-run is bounded by nothing at all rather than by one batch. Pair
it with `--batches` sized off a short observed leg and whichever is tighter stops
the run; the summary says which one did.

```
fractal-wallpapers census
fractal-wallpapers harvest --minutes 90 --batch 8
fractal-wallpapers harvest --finish-by 07:00                      # derives --minutes
fractal-wallpapers harvest --finish-by 07:00 --release-slots 20 --release-workers 8
fractal-wallpapers harvest --finish-by 07:00 --strange-modes 3    # reserve for that night
fractal-wallpapers harvest --exploration-floor 0.25 --exploration-start 0.45
fractal-wallpapers harvest --no-exploration --lineage-discount 0   # neither lever
fractal-wallpapers harvest --partition mandelbrot --root-channel proven
fractal-wallpapers harvest --partition phoenix --root-channel proven      # at labelled frames
fractal-wallpapers harvest --partition phoenix:classic --root-channel proven  # the pinned plane
fractal-wallpapers derive-proven-seeds --partition mandelbrot --write   # to read it
fractal-wallpapers harvest --partition mandelbrot --seeds seeds.jsonl   # one leg, one book
fractal-wallpapers derive-prices --run artifacts/harvest --regularize --write
fractal-wallpapers derive-tau-h --write
```

## What a run writes for a readout to price it with

`summary.json` carries, beside the run-wide books:

* `tally.by_partition` — the exploration share against the deficit-priced contest
  **per partition**, each cell with its slots, finds, distinct admissions and the
  **median head score** of those admissions. The medians come off a 100-bin
  histogram rather than the scores themselves, because the cells are checkpointed
  at every batch boundary; `harvest.SCORE_BINS` is the resolution and it is a
  readout's, not a cut's.
* `tally.saturation_by_partition` — seen against discounted, per partition. The
  run-wide pair says whether the cross-run memory fired; this says where.
* `tally.minutes` — the charged clock split into `expand`, `reframe` and
  `refine`. The first two are inside `--minutes` and only their sum was recorded
  before. The third is the framing scan the walk takes **when it closes**, and it
  is a third bucket rather than a share of `reframe` on purpose: the reframing
  operators fire per batch off admissions and this fires once per run off the
  whole walk, so folding it in would make the operator suite look more expensive
  on exactly the runs that refined most. It is spent after `--minutes` is
  already gone, so it is charged and reported rather than budgeted.
* `walk.operators` — firings, seconds, seconds per firing and share of the charged
  clock, **per reframing operator**, and `refine_framing` beside them. The
  neighbourhood enumeration is the expensive one and is on by default in
  production; this is the first time a run prices it out of its own record
  instead of out of a replay. The availability and refusal counts sit beside it in
  `walk.counts` as `reframing:<operator>:<available|reason>`.
* `refine` — what the close-time framing scan cost and bought: locations scanned,
  frames drawn, the adopted share, the chosen-width and chosen-move histograms,
  the whole Δ distribution in nats, how many refinements crossed the keeper floor,
  and the walk's own gate render measured against a fresh one of the same frame.
  `walk.counts` carries `refine:scanned`, `refine:adopted`, `refine:below_margin`
  and `refine:admitted` beside it. See `discovery/README.md` for what the leg is
  and why its rows are appended rather than edited in.
* `quota.floor_versus_deficit.per_partition` and `quota.unspent_floor.per_partition`
  are two different questions and are already two blocks: the first is how many
  realized minutes each bucket bought, the second is whether the floor's promise
  was kept — `spent`, `unspent` or `starved`, with `starved` listed separately at
  `quota.unspent_floor.starved`. A partition whose floor never bound anything and
  one nothing could feed are not the same silence.

## Reading a run afterwards: `quota.jsonl` beside the ledger

Every batch appends one line to `<run>/quota.jsonl` — the intent, the vector it
was folded to, the floor's debts, the prices, the queues, and how many slots each
partition took under each channel. It is what makes a spent slot attributable
without re-deriving the rule that spent it, and the **channel autopsy reads it**:
a refused card names the floor that kept the row out of the books and, for a node
that reached the frontier and was never expanded, why the run never came back to
it — capped, outbid on partition, outbid on node rank, discounted lineage, or the
run stopped first. Each of those is read off the trace of the batches that node
actually sat through; a run with no trace file gets the floor half and no more.

**The sample is stratified by fate**, in proportion with a floor of two cards a
class, and it covers unpictured rows. run10's page drew 48 cards and not one of
them was a structural refusal, though `flat`, `interior_cap` and `occupancy_floor`
were 13,962 of that run's rejects: the engine draws a frame for a gate survivor
and for nothing else, and the sampler only drew rows that had a picture. The
sentences for those gates had shipped and no card could carry one. Re-run against
run10's records the page is 54 cards with six `interior_cap`, four `flat` and four
`occupancy_floor` among them, each saying what its gate is and that it has no
picture to show.
