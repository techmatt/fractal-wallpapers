"""Turning compute into new good material where it is scarcest.

A walk finds places. This package decides *which* places are worth finding next,
keeps deciding for hours, and can say afterwards where every minute went.

The loop it closes is small to state and was expensive to get right:

```text
census    what each partition holds, against what the release mix says it is owed
price     what a unit of currency costs in each partition, measured as the run goes
allocate  intended share of the clock ∝ deficit ÷ price, with a floor everyone gets
serve     divide the batch's slots by how far each partition is below its intent
credit    what the batch found, deduplicated, back into the price and the stock
```

```text
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
novelty      the two levers against monotony: the discount and the share
autopsy      what each claim on the batch bought, in pictures
tau_h        how good a cheap look must be before a real one is paid for
harvest      the production loop, and everything that keeps it honest
```

Four ideas run through all of it, and each one is a mistake somebody made first.

**The mix is decided where the batch is popped.** Anything that only changes what
*enters* the frontier is diluted by whatever multiplies fastest inside it.

**Steering a mix is not enforcing one.** An intent that is never measured against
what actually happened drifts, and nothing pulls it back.

**An entitlement that does not accumulate is not an entitlement.** A claim
re-offered every batch and lost every batch is worth exactly nothing, however
often it is granted.

**An allocator indifferent to repetition buys one composition.** Scarcity says
where to look and says nothing about whether what comes back is the same picture,
so a batch's slots are claimed in a ruled order — floor, then a protected share
for ground no run has walked, then the deficit-priced contest, discounted by what
each lineage has already given this run.
"""

from __future__ import annotations

from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

__all__ = ["ALL_PARTITIONS"]
