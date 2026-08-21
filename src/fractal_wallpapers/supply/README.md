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
proven       parameter-plane roots at every location a human scored a keeper
saturation   cross-run memory, straight off the ledgers
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

Eight things are worth reading before changing anything here.

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

**A slot is not a minute.** The quota allocates the clock and hands out node
slots, so the slot demand is the minute demand divided by what a slot has been
costing in that partition. Being cheap buys more turns, not more time.

**An active minute is not a wall minute either, and `--minutes` counts the first
kind.** What is charged is `expand` plus `trigger_reframings`, per partition, per
batch. Three things are outside it: the start-up before the first batch — the
head onto the device, the proven derivation, the saturation index, the twin
channel, about a minute together — the per-batch refill, and the closing gate-flip
re-score, which is a fixed tail of a minute or two whatever the run's length. A
scored hour over the four parameter planes measured **1.13× wall per active
minute**, so an hour of `--minutes` is a bit over an hour of machine. Size a leg on
that ratio; `--minutes` alone will under-book the clock, and the tail lands after
the last batch rather than inside it.

**`--minutes` is also the only backstop a harvest has** — there is no
`--wall-budget` here, that flag belongs to `curate run`. It is a hard one: the loop
refuses to *start* a batch when the spent minutes plus the running mean batch would
overrun, so an over-run is bounded by nothing at all rather than by one batch. Pair
it with `--batches` sized off a short observed leg and whichever is tighter stops
the run; the summary says which one did.

```
fractal-wallpapers census
fractal-wallpapers harvest --minutes 90 --batch 8
fractal-wallpapers harvest --partition mandelbrot --root-channel proven
fractal-wallpapers derive-proven-seeds --partition mandelbrot --write   # to read it
fractal-wallpapers harvest --partition mandelbrot --seeds seeds.jsonl   # one leg, one book
fractal-wallpapers derive-prices --run artifacts/harvest --regularize --write
fractal-wallpapers derive-tau-h --write
```
