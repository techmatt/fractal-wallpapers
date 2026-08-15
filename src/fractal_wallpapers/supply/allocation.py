"""How the clock is divided: a floor everyone gets, and a share the deficit earns.

Two rules, and the interesting part is that they are enforced at different time
scales.

## The intended share — floor-constrained proportional water-filling

```text
share ∝ deficit / price,   subject to  share ≥ FLOOR  for every partition
```

**A floor, not a quota.** A partition whose deficit already earns it more than the
floor gets nothing extra; a partition with no deficit at all still gets its floor.
Both halves of that sentence are true simultaneously only under water-filling —
normalize the price-weighted deficits, pin everything below the floor up to it,
redistribute what is left among the unpinned in proportion, and iterate, because
pinning one partition lowers the pool and can push another under. "Reserve `n ×
floor`, then split the rest" would hand a huge-deficit partition its floor *on
top of* its proportional share, which is exactly what "nothing extra" denies.

**Why a floor at all.** Spending the whole clock on one stubborn deficit means
never learning anything new about the rich partitions. The floor keeps every
partition's price fresh, keeps rich material flowing to a release's diversity
targets, and keeps the cross-feed alive — it is finds in the rich partitions that
trigger the reframings which reach into the poor ones.

**And it is the re-entry path for a mispriced partition.** Share is
`deficit / price`, so a wrong price stops the only service that would revise it.
Nothing else in this design can reach a partition that is never served.

**Externally supplied partitions get share 0.0 and keep their key.** They are
neither pinned up to the floor nor given any of the proportional pool, and the
remaining shares still sum to one. The key stays because every tally downstream is
shaped by this dict, and an explicit zero reads as "allocated nothing on purpose"
where a missing key reads as a partition nobody tracked.

## The floor's carry — because an entitlement that does not accumulate is not one

The share-gap rule cannot hold a floor, and the reason is structural rather than a
tuning problem. The gap is `intended − realized/total`, and since realized time is
never negative that gap is **bounded above by the intent** — 0.05 for a floored
partition, at the first batch and at the three hundredth alike. Nothing in it
grows with time unserved, so an unspent entitlement is re-offered every batch
rather than accumulated, and some competitor presents a larger gap almost every
time. In the source project three floored partitions were allocated their 5% in
all 361 batches of a run and served in zero of them.

So unspent entitlement is **carried, in minutes**. Each served batch accrues
`floor × minutes` to every partition that could have been served for it, and
spends what the served partitions actually took. When a servable partition's debt
reaches one mean batch it takes the next slot.

**The bound is exact and costs nothing.** For a partition servable throughout and
served nothing, `debt = floor × T` and `trigger = T / batches`, so the claim comes
due at `batches ≥ 1 / floor` — batch twenty at a 5% floor, whatever a batch costs,
because both sides scale with the same clock. Later than that means the partition
was unservable, capped, or the floor is not what it says.

**Minutes, not turns, is what keeps it a floor.** A cheap partition triggers,
takes its short batch, repays only what it took, and comes back sooner — so it
converges on the same 5% of the *clock*. Being cheap buys more turns, not more
time. And entitlement accrues only over minutes in which the partition was
actually servable, so a partition nobody could feed does not bank a claim while it
waits and then spend it in a burst when its queue refills.

## Two silences that are not the same silence

A partition can end a run having spent none of its floor for two completely
different reasons, and conflating them once made a working allocator read as
broken:

* **floor never needed** — its deficit share was above the floor the whole time,
  so the floor never bound anything and there was nothing to spend;
* **starved** — it had neither floor time nor deficit share, because nothing could
  feed it.

[`FloorLedger.unspent`] reports which, per partition, beside the servable minutes
that separate "the rule declined to serve it" from "nothing could".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fractal_wallpapers.supply.apportion import allocate_slots
from fractal_wallpapers.supply.partitions import (
    ALL_PARTITIONS,
    is_dynamical,
    parameter_plane_of,
)
from fractal_wallpapers.supply.prices import SEED_PRICE

#: Every partition floors at this share of the total clock.
FLOOR_FRACTION = 0.05

#: How much unspent floor entitlement, in mean batches, claims the next slot. One
#: mean batch is the weakest statement that makes the claim affordable — the
#: entitlement has literally bought a batch — and it is read from the run's own
#: minutes per batch rather than configured, so it tracks whatever a batch costs.
FLOOR_DEBT_TRIGGER_BATCHES = 1.0

#: A partition that spent no more than a tenth of its allocated floor minutes is
#: reported loud.
UNSPENT_FLOOR_ALARM = 0.90

#: A dynamical twin's unservable demand folds into its parameter plane at this
#: gain: serving the parent is what manufactures the twin's supply.
TWIN_ROUTE_GAIN = 1.0


@dataclass
class Allocation:
    """The intended share of the clock, per partition, and what set it."""

    share: dict
    floored: set
    weighted_deficit: dict
    floor: float
    #: Externally-supplied partitions held out of the floor and the pool. Recorded
    #: rather than inferred from a zero share: a partition can legitimately
    #: allocate to zero, and "we chose not to" and "the arithmetic came out zero"
    #: are different facts.
    external: set = field(default_factory=set)

    def bucket(self, partition: str) -> str:
        return "floor" if partition in self.floored else "deficit"

    def summary(self) -> dict:
        return {
            "share": {p: round(v, 4) for p, v in sorted(self.share.items())},
            "floored": sorted(self.floored),
            "external": sorted(self.external),
            "floor": self.floor,
            "floor_share_total": round(sum(self.share[p] for p in self.floored), 4),
            "weighted_deficit": {p: round(v, 5) for p, v in sorted(self.weighted_deficit.items())},
        }


def allocate(
    deficits: dict,
    prices: dict,
    partitions=ALL_PARTITIONS,
    floor: float = FLOOR_FRACTION,
    external: set | None = None,
) -> Allocation:
    """Intended time-share per partition. Every share is at least `floor`, the
    rest is proportional to price-weighted deficit, and the shares sum to one.

    The degenerate cases each have a reason rather than a fallback:

    * **every deficit zero** — a cold start, or a corpus already at its target.
      There is nothing to be proportional to, so the clock is spread uniformly.
      Those partitions are *not* tagged floor-driven unless one-over-`n` is itself
      below the floor: `floored` means "the floor is what set this share", and
      tagging a uniform split would report the floor binding on a run where it
      never bound anything.
    * **the floor is infeasible** (`floor × n ≥ 1`) — it degrades to uniform
      rather than raising, because a run that cannot honour the floor should still
      run, and every partition *is* tagged floored there, since the floor is
      exactly what could not be honoured.
    """
    external = set() if external is None else set(external)
    skipped = [p for p in partitions if p in external]
    served = [p for p in partitions if p not in external]
    zeros = dict.fromkeys(skipped, 0.0)
    n = len(served)
    if n == 0:
        return Allocation(
            share=zeros, floored=set(), weighted_deficit={}, floor=floor, external=set(skipped)
        )
    if floor * n >= 1.0:
        return Allocation(
            share={p: 1.0 / n for p in served} | zeros,
            floored=set(served),
            weighted_deficit=dict.fromkeys(served, 0.0),
            floor=floor,
            external=set(skipped),
        )

    weighted = {
        p: max(0.0, float(deficits.get(p, 0.0))) / max(float(prices.get(p, SEED_PRICE)), 1e-9)
        for p in served
    }
    total = sum(weighted.values())
    if total <= 0.0:
        return Allocation(
            share={p: 1.0 / n for p in served} | zeros,
            floored=(set(served) if 1.0 / n < floor else set()),
            weighted_deficit=weighted,
            floor=floor,
            external=set(skipped),
        )

    pinned: set = set()
    share = {p: weighted[p] / total for p in served}
    while True:
        below = [p for p in served if p not in pinned and share[p] < floor - 1e-12]
        if not below:
            break
        pinned.update(below)
        rest = [p for p in served if p not in pinned]
        pool = 1.0 - floor * len(pinned)
        for p in pinned:
            share[p] = floor
        remaining = sum(weighted[p] for p in rest)
        if not rest or pool <= 0.0:
            break
        for p in rest:
            share[p] = pool * (weighted[p] / remaining) if remaining > 0 else pool / len(rest)
    # Numerical tidy-up over the unpinned mass only, so the floor stays exact.
    rest = [p for p in served if p not in pinned]
    if rest:
        pool = 1.0 - floor * len(pinned)
        held = sum(share[p] for p in rest)
        if held > 0:
            for p in rest:
                share[p] = share[p] * pool / held
    share.update(zeros)
    return Allocation(
        share=share,
        floored=pinned,
        weighted_deficit=weighted,
        floor=floor,
        external=set(skipped),
    )


def fold_dynamical_intent(
    intended: dict, queues: dict, partitions=ALL_PARTITIONS, gain: float = TWIN_ROUTE_GAIN
) -> dict:
    """The vector a batch can actually act on.

    A `julia:X` partition cannot be walked into existence — it is fed by descending
    the parameter plane `X` and taking the twin of somewhere worth taking it of. So
    when a twin has intent and an empty queue, its intent folds into its parent's:
    serving the parent is what manufactures the twin's supply, and the mix has to
    be judged on the folded column or a run that serves the parent exactly as
    instructed is scored as over-serving it.

    Returns a new dict. The original is what the realized-versus-intended report is
    scored against, and must not be mutated into the thing the batch actually used.
    """
    effective = dict(intended)
    for partition in partitions:
        if not is_dynamical(partition) or queues.get(partition, 0) > 0:
            continue
        parent = parameter_plane_of(partition)
        if parent in effective:
            effective[parent] = effective[parent] + gain * intended.get(partition, 0.0)
            effective[partition] = 0.0
    return effective


@dataclass
class FloorLedger:
    """What the floor is owed and what it has been paid, per partition, in minutes.

    Realized time is deliberately *not* mirrored here: it lives with the run's
    counters and is passed in. A second copy of the spend is a second thing to keep
    in step, and an entitlement and a spend that stopped being read together is the
    whole defect this fixes.
    """

    floor: float = FLOOR_FRACTION
    external: set = field(default_factory=set)
    trigger_batches: float = FLOOR_DEBT_TRIGGER_BATCHES
    servable_minutes: dict = field(default_factory=dict)
    total_minutes: float = 0.0
    batches: int = 0

    def settle(self, servable, minutes: float) -> None:
        """One served batch: the clock advances for everyone, the claim accrues for
        whoever could have taken it."""
        minutes = float(minutes)
        self.total_minutes += minutes
        self.batches += 1
        for partition in servable:
            if partition in self.external:
                continue  # no clock, therefore no claim
            self.servable_minutes[partition] = self.servable_minutes.get(partition, 0.0) + minutes

    def entitled(self) -> dict:
        return {p: self.floor * m for p, m in self.servable_minutes.items()}

    def trigger(self) -> float:
        """The debt that buys a slot: `trigger_batches` × the run's own mean
        minutes per batch.

        Zero before the first charge, which disables the carry for the first batch —
        there is no measured batch cost yet, and the share rule already opens
        correctly by serving the largest intent.
        """
        return (self.trigger_batches * self.total_minutes / self.batches) if self.batches else 0.0

    def debts(self, realized: dict) -> dict:
        """Unspent entitlement per partition. Clamped at zero: a floor is a claim,
        not a balance a heavy partition can bank negative and later be charged for."""
        return {
            p: max(0.0, owed - float(realized.get(p, 0.0))) for p, owed in self.entitled().items()
        }

    def claimants(self, servable, realized: dict) -> list:
        """The servable partitions whose claim has come due, most-owed first.

        Named and pure so the decision and the record of it read the same rule
        instead of one deriving what the other did.
        """
        trigger = self.trigger()
        if trigger <= 0:
            return []
        debts = self.debts(realized)
        owed = [p for p in sorted(servable) if debts.get(p, 0.0) >= trigger]
        return sorted(owed, key=lambda p: (-debts[p], p))

    def unspent(
        self, realized: dict, partitions=ALL_PARTITIONS, threshold: float = UNSPENT_FLOOR_ALARM
    ) -> dict:
        """How much of each partition's promised floor the run actually kept.

        Measured against the **allocated** floor minutes rather than the
        servable-weighted entitlement the carry uses, deliberately: those answer
        different questions and the loud one must be the blunt one. The allocation
        promised this partition its share of the clock, and this is how much of that
        promise was kept.

        `state` separates the two silences: a partition whose floor never bound
        anything is not the same as one nothing could feed.
        """
        allocated = self.floor * self.total_minutes
        rows, alarms = {}, []
        for partition in partitions:
            if partition in self.external:
                continue  # allocated nothing on purpose
            spent = float(realized.get(partition, 0.0))
            servable = float(self.servable_minutes.get(partition, 0.0))
            unspent = (1.0 - spent / allocated) if allocated > 0 else None
            if servable <= 0.0:
                state = "starved"
            elif unspent is not None and unspent >= threshold:
                state = "unspent"
            else:
                state = "spent"
            rows[partition] = {
                "allocated_minutes": round(allocated, 4),
                "spent_minutes": round(spent, 4),
                "unspent_fraction": None if unspent is None else round(max(0.0, unspent), 4),
                "servable_minutes": round(servable, 4),
                "servable_fraction": (
                    round(servable / self.total_minutes, 4) if self.total_minutes > 0 else None
                ),
                "state": state,
            }
            if state == "unspent":
                alarms.append(partition)
        return {
            "threshold": threshold,
            "floor": self.floor,
            "allocated_minutes_per_partition": round(allocated, 4),
            "total_minutes": round(self.total_minutes, 3),
            "batches": self.batches,
            "trigger_minutes": round(self.trigger(), 4),
            "alarms": sorted(alarms),
            "starved": sorted(p for p, row in rows.items() if row["state"] == "starved"),
            "per_partition": rows,
        }

    def state(self) -> dict:
        return {
            "floor": self.floor,
            "trigger_batches": self.trigger_batches,
            "external": sorted(self.external),
            "servable_minutes": self.servable_minutes,
            "total_minutes": self.total_minutes,
            "batches": self.batches,
        }

    def load_state(self, state: dict) -> None:
        self.servable_minutes.update(
            {p: float(v) for p, v in (state.get("servable_minutes") or {}).items()}
        )
        self.total_minutes = float(state.get("total_minutes", self.total_minutes))
        self.batches = int(state.get("batches", self.batches))


def share_gaps(intended: dict, realized: dict, servable) -> dict:
    """How far below its intended share of realized time each servable partition
    sits.

    This is the quota, and it is a pure function of the intended shares and the
    minutes already spent — no per-node score, no probability, no randomness.
    Determinism is the point: a rule that is allowed to be lucky cannot be read as
    evidence about the allocator.

    Before any time has been spent every realized share is zero, so the gaps are
    the intents themselves and the first batch goes to the largest — which is
    correct, and is why there is no special case for it.
    """
    total = sum(max(0.0, v) for v in realized.values())
    gaps = {}
    for partition in servable:
        got = (realized.get(partition, 0.0) / total) if total > 0 else 0.0
        gaps[partition] = intended.get(partition, 0.0) - got
    return gaps


def batch_slots(
    intended: dict,
    realized: dict,
    queues: dict,
    n_slots: int,
    claimants=(),
    capped=(),
    minutes_per_slot: dict | None = None,
) -> tuple[dict, dict]:
    """`(slots, trace)` — how a batch's node slots are divided between partitions.

    The demand is the **share gap**: a partition that is behind its intended share
    of the clock is served ahead of one that is not, so the realized mix converges
    on the intent no matter what multiplies fastest inside the frontier.

    **A slot is not a minute, and the quota allocates minutes.** A node in one
    partition can cost twenty times what a node in another does, so handing out
    slots in proportion to a minute demand would systematically over-serve the
    expensive partitions and under-serve the cheap ones — the same confusion the
    floor's carry avoids by being denominated in minutes rather than in turns. So
    the demand is divided by what a slot has actually been costing in that
    partition, measured as the run goes:

    ```text
    slot demand(p) = max(0, intended(p) − realized share(p)) ÷ minutes per slot(p)
    ```

    At one slot, and with equal costs, this is exactly "serve whichever servable
    partition is furthest below its intent"; above one it is the same rule
    repeated, with every prefix held near the intent.

    Floor claimants are **guaranteed** a slot. That is the carry's preemption in
    slot form, and it is why the batch is not simply proportional: a claim that is
    re-offered rather than accumulated is a claim that never comes due.

    A capped partition is excluded but keeps its intent, so its unserved share
    shows up in the report as a miss with a named cause rather than quietly
    redistributing. Every queue's key survives into the returned slots, at zero,
    for the same reason: a tally that loses a partition cannot report it.
    """
    capped = set(capped)
    servable = {p: int(n) for p, n in queues.items() if n > 0 and p not in capped}
    cost = {p: max(1e-9, float((minutes_per_slot or {}).get(p, 1.0))) for p in servable}
    gaps = share_gaps(intended, realized, servable)
    weights = {p: max(0.0, v) / cost[p] for p, v in gaps.items()}
    fallback = False
    if sum(weights.values()) <= 0.0:
        # Every servable partition is at or above its intent — the mix is on
        # target. There is no gap to rank by, so the slots follow the intent
        # itself, which is what the gaps would say the moment one opened.
        weights = {p: max(0.0, intended.get(p, 0.0)) / cost[p] for p in servable}
        fallback = True
    if sum(weights.values()) <= 0.0:
        weights = {p: 1.0 / cost[p] for p in servable}
    due = [p for p in claimants if p in servable]
    guaranteed, deferred = due[:n_slots], due[n_slots:]
    allocated = allocate_slots(weights, n_slots, caps=servable, guaranteed=guaranteed)
    return {p: int(allocated.get(p, 0)) for p in queues}, {
        "gap": {p: round(v, 5) for p, v in sorted(gaps.items())},
        "minutes_per_slot": {p: round(v, 5) for p, v in sorted(cost.items())},
        "weight_source": "intent" if fallback else "share_gap",
        "guaranteed": sorted(guaranteed),
        "deferred_claims": sorted(deferred),
        "capped": sorted(capped),
    }


__all__ = [
    "FLOOR_DEBT_TRIGGER_BATCHES",
    "FLOOR_FRACTION",
    "TWIN_ROUTE_GAIN",
    "UNSPENT_FLOOR_ALARM",
    "Allocation",
    "FloorLedger",
    "allocate",
    "batch_slots",
    "fold_dynamical_intent",
    "share_gaps",
]
