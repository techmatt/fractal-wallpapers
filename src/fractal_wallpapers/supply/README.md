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

Five things are worth reading before changing anything here.

**A Julia twin's supply is manufactured by serving its parent.** The allocator
has always folded a twin's demand into its parameter plane on the ground that
descending the plane is what produces places worth taking the twin of — but for
the three higher degrees the step that turned a plane find into a Julia root did
not exist, so the fold was a promise nothing kept. `twins` is that step: an
admitted degree-`d` plane location's centre *is* a `c` for the degree-`d` Julia
family, and it becomes a root through the same seed object and the same cursor
the tracked degree-2 pool uses. Parameters closer than the pool's own c-spacing
floor to one already taken are skipped and recorded.

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

**A slot is not a minute.** The quota allocates the clock and hands out node
slots, so the slot demand is the minute demand divided by what a slot has been
costing in that partition. Being cheap buys more turns, not more time.

```
fractal-wallpapers census
fractal-wallpapers harvest --minutes 90 --batch 8
fractal-wallpapers harvest --partition mandelbrot --seeds proven.jsonl   # one leg, one book
fractal-wallpapers derive-prices --run artifacts/harvest --regularize --write
fractal-wallpapers derive-tau-h --write
```
