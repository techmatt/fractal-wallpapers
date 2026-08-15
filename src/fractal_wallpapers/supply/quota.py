"""The quota: the object a run holds, and the only thing that decides the mix.

Everything else in this package is a rule. This is the thing that owns them
together — the census that says what is owed, the price that says what it costs,
the allocation that turns those into an intended share of the clock, the floor
ledger that makes the floor's claim accumulate, and the realized tally the whole
loop is scored against.

**The mix is decided where the batch is popped.** That is the one design decision
under this module and it was expensive to learn: weighting the *root draw* by
family cannot enforce a mix, because anything that only changes what enters the
frontier is diluted by whatever multiplies fastest inside it. In the source
project an intended seventy-percent share realized at under twenty over a hundred
and forty-nine batches, and neither mechanism that defeated it was a bad draw —
one channel manufactured supply from every find, and injected pools out-numbered
native roots inside the frontier.

**Steering a mix is not enforcing one.** A per-batch argmax on price-weighted
deficit steers without ever *measuring*: a stale price, a partition that happens
to expand cheaply, or an unrepresentative first hour all move the realized share
with nothing to pull it back. So this computes an intended share vector once per
batch from the standing deficits, tracks the realized share of active minutes, and
serves whichever servable partition is furthest below its intent. That is a quota
enforced at the population level, and it is the run's headline number rather than
a hope.

**Re-allocated every batch**, because the prices move. The censused deficit does
not — human labels do not arrive mid-run — but the allocation is cheap and a
vector cached at launch is a run steering on a price it has already disproved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.supply import census as census_module
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply import release_mix
from fractal_wallpapers.supply.allocation import (
    FLOOR_FRACTION,
    TWIN_ROUTE_GAIN,
    Allocation,
    FloorLedger,
    allocate,
    batch_slots,
    fold_dynamical_intent,
)
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS
from fractal_wallpapers.supply.prices import CostToFind


@dataclass
class Realized:
    """What the run actually spent, in every denomination worth asking about."""

    minutes: dict = field(default_factory=dict)
    by_bucket: dict = field(default_factory=dict)
    batches: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)
    candidates: dict = field(default_factory=dict)
    admitted: dict = field(default_factory=dict)


class Quota:
    """The standing deficit, the price, the allocation, and the realized mix."""

    def __init__(
        self,
        partitions=ALL_PARTITIONS,
        run_dir: Path | None = None,
        *,
        floor: float = FLOOR_FRACTION,
        prices_config: dict | None = None,
        census: census_module.Census | None = None,
        ratios: dict | None = None,
        external: set | None = None,
        twin_route_gain: float = TWIN_ROUTE_GAIN,
    ):
        self.partitions = list(partitions)
        self.run_dir = Path(run_dir) if run_dir is not None else None
        self.floor = float(floor)
        self.twin_route_gain = float(twin_route_gain)
        # Resolved ONCE at construction from the shipped table and passed to every
        # allocation. The flag is a property of the policy, not of the run, so
        # re-reading it per batch would let a mid-run edit move an allocation the
        # run is already being scored against.
        self.external = set(
            external if external is not None else release_mix.externally_supplied(self.partitions)
        )
        self.census = census if census is not None else census_module.stock_census(self.partitions)
        # THE quantity both the target's anchor and the deficit read. Held once
        # rather than recomputed at two sites, so they cannot come to disagree.
        self.stock = self.census.stock()
        self.ratios = release_mix.ratios(self.partitions) if ratios is None else dict(ratios)
        self.target, self.anchor = census_module.targets(self.stock, self.partitions, self.ratios)
        self.deficit = {
            p: max(0.0, self.target[p] - float(self.stock.get(p, 0.0))) for p in self.partitions
        }
        # The labels-only deficit alongside, computed from the same target vector.
        # "How much of this partition's quiet is the scorer's opinion" is the first
        # question anybody asks of an allocation the machine leg moved, and it
        # should be a read rather than a reconstruction.
        self.deficit_labels_only = {
            p: max(0.0, self.target[p] - float(self.census.currency.get(p, 0.0)))
            for p in self.partitions
        }
        self.cost = CostToFind(self.partitions, prices_config)
        self.floor_ledger = FloorLedger(floor=self.floor, external=set(self.external))
        self.realized = Realized(
            minutes=dict.fromkeys(self.partitions, 0.0),
            by_bucket={p: {"floor": 0.0, "deficit": 0.0} for p in self.partitions},
            batches=dict.fromkeys(self.partitions, 0),
            slots=dict.fromkeys(self.partitions, 0),
            candidates=dict.fromkeys(self.partitions, 0),
            admitted=dict.fromkeys(self.partitions, 0),
        )
        self._allocation: Allocation | None = None
        self._effective: dict | None = None
        self._servable: set = set()
        self._trace: dict = {}
        # Time-weighted mean of the vector the batches actually acted on. This is
        # what the realized mix must be scored against: the stated intent contains
        # demand for twins that cannot be walked into existence, and folding that
        # demand into the parent is the routing rule — so scoring against the
        # stated vector charges a run for doing exactly what it was told.
        self._effective_total: dict = dict.fromkeys(self.partitions, 0.0)
        self._effective_weight: float = 0.0

    # ---------------------------------------------------------- allocation

    def allocation(self) -> Allocation:
        return allocate(
            self.deficit, self.cost.prices(), self.partitions, self.floor, external=self.external
        )

    def minutes_per_slot(self) -> dict:
        """What a node has actually been costing, per partition.

        The quota allocates minutes and hands out slots, so something has to
        convert between them, and the honest converter is the run's own
        measurement. A partition nothing has served yet borrows the run's pooled
        mean, and a run that has served nothing at all uses one minute per slot —
        an arbitrary unit that cancels, because at that point every partition
        carries it.
        """
        served = sum(self.realized.slots.values())
        spent = sum(self.realized.minutes.values())
        pooled = (spent / served) if served > 0 else 1.0
        return {
            p: (self.realized.minutes[p] / self.realized.slots[p])
            if self.realized.slots.get(p, 0) > 0
            else pooled
            for p in self.partitions
        }

    def slots(self, queues: dict, n_slots: int) -> tuple[dict, dict]:
        """How the next batch's node slots divide between partitions."""
        allocation = self.allocation()
        self._allocation = allocation
        effective = fold_dynamical_intent(
            allocation.share, queues, self.partitions, self.twin_route_gain
        )
        self._effective = effective
        self._servable = {p for p, n in queues.items() if n > 0 and p not in self.cost.capped}
        claimants = self.floor_ledger.claimants(self._servable, self.realized.minutes)
        slots, trace = batch_slots(
            effective,
            self.realized.minutes,
            queues,
            n_slots,
            claimants=claimants,
            capped=self.cost.capped,
            minutes_per_slot=self.minutes_per_slot(),
        )
        debts = self.floor_ledger.debts(self.realized.minutes)
        self._trace = {
            **trace,
            "slots": {p: n for p, n in sorted(slots.items()) if n},
            "intended": {p: round(allocation.share.get(p, 0.0), 4) for p in self.partitions},
            "effective": {p: round(effective.get(p, 0.0), 4) for p in self.partitions},
            "floor_debt": {p: round(v, 4) for p, v in sorted(debts.items())},
            "floor_trigger_minutes": round(self.floor_ledger.trigger(), 4),
            "price": {p: round(v, 4) for p, v in sorted(self.cost.prices().items())},
            "queues": {p: int(queues.get(p, 0)) for p in self.partitions},
        }
        return slots, self._trace

    def effective_intent(self) -> dict:
        """The time-weighted mean of the vector the batches acted on."""
        if self._effective_weight <= 0:
            return dict(self._effective or self.allocation().share)
        return {p: v / self._effective_weight for p, v in self._effective_total.items()}

    # ---------------------------------------------------------- accounting

    def charge(self, partition: str, minutes: float, slots: int = 1) -> bool:
        """Account one partition's active minutes in the batch just served."""
        self.realized.minutes[partition] = self.realized.minutes.get(partition, 0.0) + minutes
        self.realized.batches[partition] = self.realized.batches.get(partition, 0) + 1
        self.realized.slots[partition] = self.realized.slots.get(partition, 0) + int(slots)
        bucket = self._allocation.bucket(partition) if self._allocation else "deficit"
        buckets = self.realized.by_bucket.setdefault(partition, {"floor": 0.0, "deficit": 0.0})
        buckets[bucket] = buckets.get(bucket, 0.0) + minutes
        return self.cost.charge(partition, minutes)

    def credit(self, partition: str, score, great=None) -> float:
        """One find landed in a partition. Returns the currency it was worth.

        A find below the keeper floor is not a credit and deliberately does not
        reset the partition's dry clock.
        """
        units = money.units_of(money.good_class(score, great))
        if units:
            self.cost.credit(partition, units)
        return units

    def close_batch(self, minutes: float) -> dict:
        """The batch boundary: the price window closes and the floor's clock ticks.

        Hung off one call rather than left to a driver to remember, so "one price
        sample per batch" and "the floor accrues over the minutes the run actually
        spent" are structural instead of conventions.
        """
        self.floor_ledger.settle(self._servable, minutes)
        if self._effective:
            for partition, value in self._effective.items():
                self._effective_total[partition] = (
                    self._effective_total.get(partition, 0.0) + value * minutes
                )
            self._effective_weight += minutes
        return self.cost.end_window()

    def note_candidates(self, partition: str, n: int) -> None:
        self.realized.candidates[partition] = self.realized.candidates.get(partition, 0) + int(n)

    def note_admission(self, partition: str, n: int = 1) -> None:
        self.realized.admitted[partition] = self.realized.admitted.get(partition, 0) + int(n)

    # ------------------------------------------------------------ reporting

    def realized_share(self, denomination: str = "minutes") -> dict:
        source = {
            "minutes": self.realized.minutes,
            "slots": self.realized.slots,
            "candidates": self.realized.candidates,
            "admitted": self.realized.admitted,
            "batches": self.realized.batches,
        }[denomination]
        total = sum(source.get(p, 0) for p in self.partitions)
        if total <= 0:
            return dict.fromkeys(self.partitions, 0.0)
        return {p: source.get(p, 0) / total for p in self.partitions}

    def mix_report(self) -> dict:
        """Realized against intended — the run's headline.

        Four denominations, because they answer different questions: minutes is
        what the quota allocates and therefore what it can be held to, candidates
        is where a root-weighted mix was first measured going wrong, admissions is
        what the corpus actually gains, and batches is how often each was touched.
        """
        allocation = self._allocation or self.allocation()
        effective = self.effective_intent()
        report: dict = {}
        for denomination in ("minutes", "slots", "candidates", "admitted", "batches"):
            got = self.realized_share(denomination)
            report[denomination] = {
                p: {
                    "intended": round(allocation.share.get(p, 0.0), 4),
                    "effective": round(effective.get(p, 0.0), 4),
                    "realized": round(got.get(p, 0.0), 4),
                    "delta": round(got.get(p, 0.0) - allocation.share.get(p, 0.0), 4),
                    "delta_effective": round(got.get(p, 0.0) - effective.get(p, 0.0), 4),
                }
                for p in self.partitions
            }
        report["gap_minutes"] = round(
            sum(abs(report["minutes"][p]["delta"]) for p in self.partitions) / 2.0, 4
        )
        # The gap that is a statement about the batch decision. The stated intent
        # carries demand for twins that cannot be walked into existence.
        report["gap_minutes_effective"] = round(
            sum(abs(report["minutes"][p]["delta_effective"]) for p in self.partitions) / 2.0, 4
        )
        report["effective_intent"] = {p: round(v, 4) for p, v in sorted(effective.items())}
        return report

    def floor_versus_deficit(self) -> dict:
        """How much realized time each bucket bought, per partition and in total."""
        per_partition = {
            p: {k: round(v, 3) for k, v in buckets.items()}
            for p, buckets in self.realized.by_bucket.items()
        }
        floor = sum(b.get("floor", 0.0) for b in self.realized.by_bucket.values())
        deficit = sum(b.get("deficit", 0.0) for b in self.realized.by_bucket.values())
        total = floor + deficit
        return {
            "per_partition": per_partition,
            "floor_minutes": round(floor, 3),
            "deficit_minutes": round(deficit, 3),
            "floor_share": round(floor / total, 4) if total else None,
            "deficit_share": round(deficit / total, 4) if total else None,
        }

    def unspent_floor(self) -> dict:
        return self.floor_ledger.unspent(self.realized.minutes, self.partitions)

    def trace_path(self) -> Path | None:
        return None if self.run_dir is None else self.run_dir / "quota.jsonl"

    def log_batch(self, batch: int, sample: dict | None = None) -> None:
        """Append one line saying what the last batch decided and why.

        Every slot a run spends should be attributable afterwards without
        re-deriving the rule that spent it, so the trace carries the intent, the
        vector it was folded to, the debts, the prices and the queues — not just
        the winner.
        """
        path = self.trace_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "schema": 1,
            "batch": batch,
            **self._trace,
            "realized": {p: round(v, 4) for p, v in self.realized_share("minutes").items()},
            "deficit": {p: round(self.deficit.get(p, 0.0), 3) for p in self.partitions},
            "price_sample": sample or {},
        }
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------- state

    def state(self) -> dict:
        return {
            "partitions": self.partitions,
            "floor": self.floor,
            "twin_route_gain": self.twin_route_gain,
            "deficit": self.deficit,
            "cost": self.cost.state(),
            "floor_ledger": self.floor_ledger.state(),
            "realized": {
                "minutes": self.realized.minutes,
                "by_bucket": self.realized.by_bucket,
                "batches": self.realized.batches,
                "slots": self.realized.slots,
                "candidates": self.realized.candidates,
                "admitted": self.realized.admitted,
            },
            "effective_total": self._effective_total,
            "effective_weight": self._effective_weight,
        }

    def load_state(self, state: dict, reopen_caps: bool = False) -> None:
        """Restore a checkpointed quota.

        The **deficit is re-censused** on resume rather than restored: the label
        corpus can gain a labelling sheet between sessions, and a resumed run
        reading a stale deficit would allocate against a corpus that no longer
        exists. The
        floor ledger's servable-minute accrual *is* restored, because it is a fact
        about batches this process never saw — a resumed run that reset it would
        re-offer the floor from scratch every session, which is a slower version of
        the defect the carry exists to fix.
        """
        realized = state.get("realized") or {}
        self.realized.minutes.update(
            {p: float(v) for p, v in (realized.get("minutes") or {}).items()}
        )
        self.realized.by_bucket.update(realized.get("by_bucket") or {})
        for name in ("batches", "slots", "candidates", "admitted"):
            getattr(self.realized, name).update(
                {p: int(v) for p, v in (realized.get(name) or {}).items()}
            )
        self.cost.load_state(state.get("cost") or {})
        self.floor_ledger.load_state(state.get("floor_ledger") or {})
        self._effective_total.update(
            {p: float(v) for p, v in (state.get("effective_total") or {}).items()}
        )
        self._effective_weight = float(state.get("effective_weight", self._effective_weight))
        if reopen_caps:
            self.cost.reopen_caps()

    def summary(self) -> dict:
        return {
            "currency": self.census.summary(),
            "externally_supplied": sorted(self.external),
            "stock": {p: round(self.stock.get(p, 0.0), 3) for p in self.partitions},
            "target": {p: round(self.target.get(p, 0.0), 3) for p in self.partitions},
            "target_rule": census_module.TARGET_RULE,
            "ratio": self.ratios,
            "anchor": None if self.anchor is None else round(self.anchor, 3),
            "deficit": {p: round(self.deficit.get(p, 0.0), 3) for p in self.partitions},
            # The two legs side by side: `deficit` is what the run allocates
            # against, and these say how much of it the machine leg moved.
            "deficit_labels_only": {
                p: round(self.deficit_labels_only.get(p, 0.0), 3) for p in self.partitions
            },
            "machine_contribution": {
                p: round(v, 3) for p, v in self.census.machine_leg().contribution().items()
            },
            "allocation": self.allocation().summary(),
            "cost": self.cost.summary(),
            "mix": self.mix_report(),
            "floor_versus_deficit": self.floor_versus_deficit(),
            "unspent_floor": self.unspent_floor(),
            "trace": None if self.trace_path() is None else str(self.trace_path()),
        }


__all__ = ["Quota", "Realized"]
