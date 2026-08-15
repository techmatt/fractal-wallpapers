"""Turning a share vector into whole slots, without zeroing anybody by accident.

The allocator says what fraction of the clock each partition should get. A batch
has a small whole number of node slots in it. Getting from the first to the second
is apportionment, and which rule you use decides what a *truncated* run looks
like.

**The rule is largest-deficit sequencing.** At every position the next slot goes
to the partition whose running count is furthest below its proportional share of
the positions handed out so far. Its subject is every *prefix*: at every length
each partition is held near its share, which is the only property that survives a
budget that stops early — and a budget that stops early is the normal case. The
cheaper rule, laying each partition's slots out at even spacing and sorting, does
not hold that; measured on a real cell population it drifts half again as far.

**Handing out `n` slots proportionally will zero somebody, structurally.** With
ten partitions and a batch of eight, proportional apportionment seats six and
zeroes four whatever their supply — and the partition with the smallest ratio is
zeroed first, every time, so the garnish never ships. The fix is a **guarantee**:
a named set of partitions comes out with at least one slot, and the remainder is
apportioned exactly as before.

**A guarantee is a floor, not a bonus**, which is why it is a fixed point rather
than "reserve, then apportion what is left". The naive form gives a guaranteed
partition its reservation *on top of* whatever the rule would have handed it
anyway — `natural + reserved` where the intent is `max(natural, reserved)`,
differing by exactly the reservation on every partition that did not need one. So
each round, any guaranteed partition the rule still zeroes is pinned at one and
taken out of the pool the rest share, until nothing is short. A partition the rule
already seats is never pinned and gains nothing from being named.

**Nothing is silently pro-rated.** More guarantees than slots is refused here
rather than shared out, because a pro-rated guarantee is not a guarantee. The
caller holds the ordering that decides who waits, and reports it.

**The prefix bound is a check, not a theorem.** Largest-deficit is provably tight
for two cells and comfortable on real populations, and with many cells and a
hundredfold supply skew it does exceed one. [`prefix_deviation`] is the metric,
exposed so a caller can assert the bound on the order it actually built.
"""

from __future__ import annotations


class SlotGuaranteeOverflow(ValueError):
    """More partitions are guaranteed a slot than there are slots."""


def sequence_by_deficit(weights: dict, n: int, caps: dict | None = None, tie=None) -> list:
    """The first `n` positions of the largest-deficit sequence over `weights`.

    `caps` bounds how many slots a partition can actually use — a queue of two
    nodes cannot fill three slots — and a capped-out partition drops out of the
    running rather than holding a slot nobody can spend. `tie` breaks equal
    deficits and defaults to `(weight, key)`, so the sequence is a pure function
    of its inputs.
    """
    keys = list(weights)
    weight = {k: max(0.0, float(weights[k])) for k in keys}
    total = sum(weight.values())
    limit = {k: (float("inf") if caps is None else int(caps.get(k, 0))) for k in keys}
    if total <= 0:
        return []
    tie = tie or (lambda k: (weight[k], k))
    taken = dict.fromkeys(keys, 0)
    out: list = []
    for position in range(1, int(n) + 1):
        live = [k for k in keys if taken[k] < limit[k] and weight[k] > 0]
        if not live:
            break
        pick = max(live, key=lambda k: (position * weight[k] / total - taken[k], *tie(k)))
        taken[pick] += 1
        out.append(pick)
    return out


def allocate_slots(weights: dict, n: int, caps: dict | None = None, guaranteed=()) -> dict:
    """`{partition: slots}` — `n` slots over `weights`, with a guaranteed floor.

    A guaranteed partition that cannot be seated at all — no weight, or no supply
    — is not seatable here and is quietly left out: the guarantee is about the
    rule zeroing it, never about conjuring a node for it to spend.
    """
    n = max(0, int(n))
    keys = list(weights)
    limit = {k: (None if caps is None else int(caps.get(k, 0))) for k in keys}
    seatable = [
        k for k in keys if float(weights.get(k, 0.0)) > 0 and (limit[k] is None or limit[k] > 0)
    ]
    pins = [k for k in sorted(set(guaranteed)) if k in seatable]
    if len(pins) > n:
        raise SlotGuaranteeOverflow(
            f"{len(pins)} partitions guaranteed a slot against {n} slot(s): {pins}. "
            f"Pro-rating a guarantee silently would make it not a guarantee — raise the "
            f"batch size, or decide which claims wait."
        )
    out = dict.fromkeys(keys, 0)
    if not seatable or n == 0:
        return out
    pinned: set = set()
    while True:
        free = {k: weights[k] for k in seatable if k not in pinned}
        share = dict.fromkeys(seatable, 0)
        free_caps = None if caps is None else {k: limit[k] for k in free}
        for k in sequence_by_deficit(free, n - len(pinned), free_caps):
            share[k] += 1
        short = [k for k in pins if k not in pinned and share[k] < 1]
        if not short:
            break
        pinned.update(short)
    for k in seatable:
        out[k] = 1 if k in pinned else share[k]
    return out


def prefix_deviation(sequence, weights: dict) -> float:
    """`max` over prefixes and partitions of `|count − L·w/W|` — the number the
    bound is about."""
    keys = list(weights)
    total = sum(max(0.0, float(weights[k])) for k in keys)
    if total <= 0:
        return 0.0
    taken = dict.fromkeys(keys, 0)
    worst = 0.0
    for length, key in enumerate(sequence, 1):
        taken[key] = taken.get(key, 0) + 1
        for k in keys:
            worst = max(worst, abs(taken[k] - length * max(0.0, float(weights[k])) / total))
    return worst


__all__ = [
    "SlotGuaranteeOverflow",
    "allocate_slots",
    "prefix_deviation",
    "sequence_by_deficit",
]
