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

The module map is the package's `README.md`.

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
