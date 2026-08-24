"""The production loop: turn a clock into new good material where it is scarcest.

A walk finds places. A harvest keeps finding them, for hours, in the partitions
that need it most — and that is a different program, because everything that goes
wrong over six unattended hours is invisible in a program that runs for six
seconds.

```text
per batch:  refill anything starved
            ask the quota how the batch's slots divide between partitions,
              in the ruled order: floor claims, exploration share, contest
            take each partition's slots off its own queue in that order,
              expand, score, reframe
            charge the minutes, credit the finds, close the price window
              and the share's own
            reconcile what was found against what was written
            checkpoint
```

Five things this loop does that a walk does not.

**The batch is divided between partitions by the quota**, not by priority alone.
Priority decides which of *one partition's* nodes to expand; the quota decides how
many of them it gets. Those are different questions, and letting the second fall
out of the first is exactly how a mix stops being enforced.

**Minutes are charged per partition, not per batch.** The engine expands one
family per call, and a family belongs to exactly one partition, so a batch that
spans four partitions produces four timed pieces of work rather than one number to
apportion after the fact. The price is measured, so it should be measured.

**Every batch reconciles, and a batch that does not balance ends the run.** Three
identities have to close: every candidate the engine reported was written with a
fate this project knows; everything that reached the frontier was either admitted
or expandable; and every admission either is a new location or is one the run
already had. A long unattended run that silently loses candidates is exactly the
failure a summary cannot show you afterwards — the numbers all look plausible,
because the missing ones are missing from both sides.

**The frontier is fed by more than the books count.** Expansion is gated at the
junk floor and booking at the good floor, so a batch pushes `admitted +
expandable` nodes and credits only `admitted`. The ratio of the first to the
nodes expanded is the run's growth rate, it is in every summary, and below one
the walk is dying however healthy the admission count looks.

**A batch is taken in two draws, and which one paid is recorded.** The
exploration share draws first, from lineages no ledger has ever booked from,
ranked by the plain priority — inside the share the head ranks and only the junk
floor kills. The contest draws the rest, ranked by a key that discounts a
lineage by what it has already booked *this run*. `pop_batch` removes what it
takes, so the two draws cannot overlap and the columns add to the slots the quota
handed out; the channel travels onto every candidate row, which is what lets the
autopsy show the two populations side by side afterwards.

**Admissions are counted as distinct locations**, and that is not bookkeeping
pedantry: a raw count of what a scorer waved through runs about twice what the
distinct-location count does, so a run that reports the raw number reports roughly
double the supply it produced, and the deficit it feeds is wrong by that factor.
Deduplicate, then count.

## Stopping and resuming

The budget is in **active minutes**, and the rule is never to *start* a batch that
cannot finish inside what is left, rather than to stop once the budget is already
blown. The checkpoint is written at the batch boundary, after the reconcile, so
every state a run can be resumed from is a state whose identities closed. What is
checkpointed is the frontier, the counters, the quota's realized tallies and price
accumulators, the floor ledger's accrual, and the random state — so a resumed run
is a continuation of the same run and not a fresh one that happens to share a
directory.

The floor ledger's accrual is restored rather than re-derived, deliberately: it is
a fact about batches this process never saw, and a resumed run that reset it would
re-offer the floor from scratch every session, which is a slower version of the
defect the carry exists to fix.
"""

from __future__ import annotations

import json
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.walk import NEUTRAL_PRIOR, Walk, family_key
from fractal_wallpapers.paths import tracked_name
from fractal_wallpapers.supply import novelty as novelty_module
from fractal_wallpapers.supply import saturation as saturation_module
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, partition_of_family
from fractal_wallpapers.supply.quota import Quota
from fractal_wallpapers.supply.refill import Refill

#: The checkpoint's schema. **5** because the readout's per-partition books
#: joined it — the share-against-contest split, its head-score histograms and the
#: saturation activations, all per partition. A session resumed from a schema-4
#: checkpoint would reopen those at zero and report medians and activation counts
#: covering the second session alone, with nothing on the page saying so. That is
#: the same silence every bump below was taken for.
#:
#: **4** was the exploration share: the
#: share is a *priced* quantity and the roots it is spent on are classified once,
#: so a session resumed from a schema-3 checkpoint would reopen at the start
#: share, throw away every batch of evidence the first session bought, and
#: re-classify from a root table it does not have. Refused rather than defaulted.
#:
#: **3** was the walk's plane roots, for the same shape of reason: a session that
#: rebuilt them would carry the grace for the roots it drew and not for the roots
#: the earlier session drew, which is two policies under one run seed.
STATE_SCHEMA = 5


#: Bins the head-score histogram divides `P(>=3)` into. A hundred, so the median
#: it answers is good to half a hundredth — which is a readout's precision and
#: not a cut's, and this is only ever read by a readout.
#:
#: A histogram rather than the scores themselves because this is checkpointed at
#: every batch boundary: a six-hour leg admits tens of thousands of locations, and
#: rewriting that list a thousand times is a real cost for a number nobody needs
#: to more than two decimal places.
SCORE_BINS = 100


def score_bin(score) -> int | None:
    """Which bin one head score falls in, or `None` for a row with no score."""
    if score is None:
        return None
    return min(SCORE_BINS - 1, max(0, int(float(score) * SCORE_BINS)))


def median_of(histogram) -> float | None:
    """The median of a bin-counted distribution, as the crossing bin's midpoint."""
    counts = list(histogram or [])
    total = sum(counts)
    if not total:
        return None
    seen, half = 0, total / 2.0
    for index, count in enumerate(counts):
        seen += count
        if seen >= half:
            return round((index + 0.5) / SCORE_BINS, 4)
    return None


def _channel_cell() -> dict:
    return {
        "slots": 0,
        "found": 0,
        "admitted": 0,
        "distinct": 0,
        "expandable": 0,
        "refused": 0,
        "scores": [0] * SCORE_BINS,
    }


class ReconcileError(SystemExit):
    """A batch's books do not balance. The run stops here, loudly."""


@dataclass
class Budget:
    """When to stop."""

    #: Active minutes across every session of this run. Zero disables the cap.
    minutes: float = 10.0
    #: Batches across every session. `None` disables the cap.
    batches: int | None = None


@dataclass
class Tally:
    """What the run has found, in the buckets the reconcile is written in.

    Two of these are new and they are the split: `admitted` is what the books
    count, `expandable` is what the frontier stands on and the books do not. Their
    sum is the frontier's feed, and `feed / expanded` is the growth rate that says
    whether the walk is alive — the one number a run whose frontier was quietly
    dying had no way to report.
    """

    batches: int = 0
    expanded: int = 0
    found: int = 0
    admitted: int = 0
    expandable: int = 0
    distinct: int = 0
    duplicate: int = 0
    refused: Counter = field(default_factory=Counter)
    units: float = 0.0
    saturation_seen: int = 0
    saturation_discounted: int = 0
    #: What each claim on the batch bought, keyed by channel — the exploration
    #: share against the deficit-priced contest. Counted here rather than derived
    #: from the ledger afterwards because the reconcile is written in these
    #: buckets and a column nothing balances is a column nobody can trust.
    by_channel: dict = field(default_factory=dict)
    #: The same split **per partition**, with a head-score histogram on each cell.
    #: The run-wide row above cannot answer the question the share was added for
    #: — a share that returns its admissions out of one partition is a share that
    #: has not spread — and the medians are what separate "more finds" from
    #: "better finds".
    by_partition: dict = field(default_factory=dict)
    #: Saturation activations per partition: how many survivors the cross-run
    #: memory looked at, and how many it actually discounted. The run-wide pair
    #: above says whether the lever fired at all; this says where.
    saturation_by_partition: dict = field(default_factory=dict)
    #: Where a batch's charged minutes went. `expand` is the engine and the head;
    #: `reframe` is the operator suite the survivors trigger — the neighbourhood
    #: enumeration among them, which is the expensive one. Both are inside
    #: `--minutes` and only their sum was ever recorded.
    expand_minutes: float = 0.0
    reframe_minutes: float = 0.0
    #: The framing scan the walk takes when it closes. A third bucket and not a
    #: share of `reframe`: the operators fire per batch off admissions and this
    #: fires once per run off the whole walk, so folding it in would make the
    #: operator suite look more expensive on exactly the runs that refined most.
    refine_minutes: float = 0.0

    def channel(self, name: str) -> dict:
        return self.by_channel.setdefault(name, _channel_cell())

    def cell(self, partition: str, name: str) -> dict:
        return self.by_partition.setdefault(partition, {}).setdefault(name, _channel_cell())

    def saturation(self, partition: str) -> dict:
        return self.saturation_by_partition.setdefault(partition, {"seen": 0, "discounted": 0})

    def charged(self) -> float:
        """Minutes this run charged to something it can name. The three buckets."""
        return self.expand_minutes + self.reframe_minutes + self.refine_minutes

    def feed(self) -> int:
        """Nodes this run pushed onto the frontier from its own expansions."""
        return self.admitted + self.expandable

    def growth(self) -> float | None:
        """Frontier nodes gained per node expanded. Below 1 the walk is dying."""
        return self.feed() / self.expanded if self.expanded else None

    def as_dict(self) -> dict:
        growth = self.growth()
        return {
            "batches": self.batches,
            "expanded": self.expanded,
            "found": self.found,
            "admitted": self.admitted,
            "expandable": self.expandable,
            "frontier_feed": self.feed(),
            "growth_per_expansion": None if growth is None else round(growth, 3),
            "distinct_admissions": self.distinct,
            "duplicate_admissions": self.duplicate,
            "refused": dict(sorted(self.refused.items())),
            "currency": round(self.units, 4),
            "saturation_seen": self.saturation_seen,
            "saturation_discounted": self.saturation_discounted,
            "by_channel": {k: _channel_report(v) for k, v in sorted(self.by_channel.items())},
            # Per partition, and the histogram is folded to its median on the way
            # out: the bins are a checkpoint's business and the summary is a
            # readout's, and a hundred-column row per cell is a page nobody reads.
            "by_partition": {
                partition: {name: _channel_report(cell) for name, cell in sorted(channels.items())}
                for partition, channels in sorted(self.by_partition.items())
            },
            "saturation_by_partition": {
                partition: dict(cell)
                for partition, cell in sorted(self.saturation_by_partition.items())
            },
            "minutes": {
                "expand": round(self.expand_minutes, 4),
                "reframe": round(self.reframe_minutes, 4),
                "refine": round(self.refine_minutes, 4),
                "reframe_share": (
                    round(self.reframe_minutes / self.charged(), 4) if self.charged() > 0 else None
                ),
                "refine_share": (
                    round(self.refine_minutes / self.charged(), 4) if self.charged() > 0 else None
                ),
            },
        }


def _channel_report(cell: dict) -> dict:
    """One channel cell as a summary reads it: the counts, and the median score.

    The distinct admissions are what the median is over, because they are what
    the deficit is fed with — a channel scored on everything it found would be
    reporting the gate's opinion of its candidates rather than its own supply.
    """
    row = {key: value for key, value in cell.items() if key != "scores"}
    row["distinct_per_slot"] = (
        round(row["distinct"] / row["slots"], 4) if row.get("slots") else None
    )
    row["median_head_score"] = median_of(cell.get("scores"))
    return row


class Harvest:
    """One production run: a walk, a quota, and everything that keeps them honest."""

    def __init__(
        self,
        walk: Walk,
        quota: Quota,
        *,
        budget: Budget | None = None,
        batch_size: int | None = None,
        refill: Refill | None = None,
        memory: saturation_module.VisitedIndex | None = None,
        saturation_strength: float = saturation_module.STRENGTH,
        discount_k: float = novelty_module.DISCOUNT_K,
        discount_floor: float = novelty_module.DISCOUNT_FLOOR,
        partitions=ALL_PARTITIONS,
        finish_by: dict | None = None,
    ):
        self.walk = walk
        self.quota = quota
        self.budget = budget or Budget()
        self.batch_size = int(batch_size if batch_size is not None else walk.limits.batch)
        self.refill = refill
        self.memory = memory
        self.saturation_strength = float(saturation_strength)
        # The lineage discount's two parameters. Run-command arguments and never
        # stored on a row: the discount is a price this run put on its own
        # repetition, and a fate recorded under it would be a verdict the next
        # run could not restate.
        self.discount_k = float(discount_k)
        self.discount_floor = float(discount_floor)
        self.partitions = list(partitions)
        # The wall-clock plan `--finish-by` derived this run's budget from, or
        # `None` for a run whose minutes were named outright. Carried whole into
        # the summary rather than reduced to the number it produced: a night that
        # lands late is attributable to the term that was reserved wrong, and the
        # terms are the only part of that a later reader cannot reconstruct.
        self.finish_by = finish_by
        self.run_dir = Path(walk.out_dir)
        self.tally = Tally()
        self.active_minutes = 0.0
        self.seen: set = set()
        self.batch = 0
        self._partition_cache: dict = {}

    # ------------------------------------------------------------- the shape

    @property
    def exploration(self):
        """The protected exploration share, or `None`. It lives on the quota —
        the object that divides the batch's slots — and is read from here so the
        loop has one answer rather than a second copy of the same object."""
        return self.quota.exploration

    def partition_of(self, node: dict) -> str:
        """The partition a frontier node belongs to, cached on its family identity.

        Cached on the family's canonical spelling rather than on the object, so a
        frontier rebuilt from a checkpoint hits the same cache entries as the one
        that wrote it.
        """
        key = family_key(node["family"])
        cached = self._partition_cache.get(key)
        if cached is None:
            cached = partition_of_family(node["family"])
            self._partition_cache[key] = cached
        return cached

    def queues(self) -> dict:
        """Frontier nodes per partition — the servability the quota reads, and the
        quantity a low-water mark has to be measured in."""
        return self.scan()[0]

    def scan(self) -> tuple[dict, dict]:
        """`(queues, novel queues)` — the frontier counted once, twice over.

        The second is the stock the exploration share can be spent on: nodes whose
        root's lineage no ledger has ever booked an admission from. Counted in the
        same pass because the frontier is four thousand nodes at its cap and the
        quota asks both questions about the same instant — two walks could
        disagree about a node the eviction dropped between them.
        """
        self.walk.evict_capped()
        counts = dict.fromkeys(self.partitions, 0)
        novel = dict.fromkeys(self.partitions, 0)
        for node in self.walk.frontier:
            partition = self.partition_of(node)
            counts[partition] = counts.get(partition, 0) + 1
            if self.exploration is not None and self.is_novel(node):
                novel[partition] = novel.get(partition, 0) + 1
        return counts, novel

    def is_novel(self, node: dict) -> bool:
        """Whether this node's lineage is one the exploration share protects."""
        root_id = int(node["root_id"])
        return self.exploration.member(root_id, self.walk.roots.get(root_id))

    def contest_key(self, node: dict) -> float:
        """The contest's ranking number: the node's priority with its score term
        discounted by what its lineage has already booked **this run**.

        Evaluated here rather than written into the node, because `n` moves after
        the node is pushed and the Gumbel draw must not be re-rolled. Under the
        null scorer every score term is the neutral prior and this returns the
        priority unchanged, which is the honest state and not a disabled lever.
        """
        booked = self.walk.admitted.get(int(node["root_id"]), 0)
        discount = novelty_module.lineage_discount(booked, self.discount_k, self.discount_floor)
        return node["priority"] + (discount - 1.0) * node.get("score_term", NEUTRAL_PRIOR)

    def mean_batch_minutes(self) -> float:
        return self.active_minutes / self.tally.batches if self.tally.batches else 0.0

    def exhausted(self) -> str | None:
        """Why the loop should stop before starting another batch, or `None`.

        The rule is never to *start* a batch that cannot finish inside the
        remaining budget, so an over-run is bounded by one batch rather than by
        however long the last one took.
        """
        if self.budget.batches is not None and self.tally.batches >= self.budget.batches:
            return "batch budget"
        if self.budget.minutes and (
            self.active_minutes + self.mean_batch_minutes() > self.budget.minutes
        ):
            return "active-time budget"
        return None

    # ------------------------------------------------------------- one batch

    def run_batch(self) -> dict:
        """Serve one batch. Returns what it did, or `None` for nothing servable."""
        queues, novel = self.scan()
        refilled = {}
        if self.refill is not None:
            refilled = self.refill.run(queues, self.batch, self.active_minutes * 60.0)
            if refilled.get("roots"):
                queues, novel = self.scan()

        share_slots, slots, trace = self.quota.slots(queues, self.batch_size, novel)
        served = {p: share_slots.get(p, 0) + slots.get(p, 0) for p in queues}
        served = {p: n for p, n in served.items() if n > 0}
        if not served:
            return {"served": {}, "stalled": True, "queues": queues}

        self.walk.batch_index = self.batch
        minutes_total = 0.0
        per_partition = {}
        spent: dict = {}
        for partition in sorted(served):
            taken, channels = self._take(
                partition, share_slots.get(partition, 0), slots.get(partition, 0)
            )
            if not taken:
                continue
            started = time.monotonic()
            report = self.walk.expand(taken)
            self._apply_memory(partition, report)
            expanded_at = time.monotonic()
            self.walk.trigger_reframings(report["survivors"])
            finished_at = time.monotonic()
            # Both halves are charged — an operator's clock is this run's clock —
            # but only their sum was ever recorded, and the neighbourhood
            # enumeration is the expensive operator this project has. Split here,
            # where the two calls are, rather than derived afterwards from a
            # ledger that does not carry seconds.
            self.tally.expand_minutes += (expanded_at - started) / 60.0
            self.tally.reframe_minutes += (finished_at - expanded_at) / 60.0
            minutes = (finished_at - started) / 60.0
            minutes_total += minutes
            counted = self._account(partition, report, minutes, len(taken), channels)
            for name, row in counted["by_channel"].items():
                into = spent.setdefault(name, {"slots": 0, "admissions": 0})
                into["slots"] += row["slots"]
                into["admissions"] += row["distinct"]
            per_partition[partition] = {"nodes": len(taken), "minutes": round(minutes, 4)} | counted

        self.active_minutes += minutes_total
        sample = self.quota.close_batch(minutes_total)
        priced = self._price_share(spent)
        self.quota.note_share_pricing(priced)
        self.walk.prune()
        self.tally.batches += 1
        self.quota.log_batch(self.batch, sample)
        self.batch += 1
        return {
            "batch": self.batch - 1,
            "served": per_partition,
            "minutes": round(minutes_total, 4),
            "refill": refilled,
            "trace": trace,
        }

    def _take(self, partition: str, share: int, contest: int) -> tuple[list, dict]:
        """One partition's nodes, taken under the two claims in order.

        The share draws first, from its own members only and ranked by the plain
        priority — the head ranks inside the share and nothing else does. The
        contest then draws from whatever is left, ranked by the discounted key.
        Taking the share first is what makes it protected: `pop_batch` removes what
        it takes from the frontier, so the second draw cannot re-take a share node
        and the two counts add up to the slots the quota handed out.

        Returns the batch and a `node_id -> channel` map, which is how an
        admission is attributed afterwards to the claim that paid for it.
        """
        channels: dict = {}
        taken: list = []
        if share > 0 and self.exploration is not None:
            pool = [
                node
                for node in self.walk.frontier
                if self.partition_of(node) == partition and self.is_novel(node)
            ]
            for node in self.walk.pop_batch(pool=pool, size=share):
                node["channel"] = novelty_module.SHARE
                channels[node["node_id"]] = novelty_module.SHARE
                taken.append(node)
        if contest > 0:
            pool = [node for node in self.walk.frontier if self.partition_of(node) == partition]
            for node in self.walk.pop_batch(pool=pool, size=contest, key=self.contest_key):
                node["channel"] = novelty_module.CONTEST
                channels[node["node_id"]] = novelty_module.CONTEST
                taken.append(node)
        return taken, channels

    def _price_share(self, spent: dict) -> dict | None:
        """Close the exploration share's own window on the batch just served.

        Priced on **distinct** admissions, which is the same number the deficit is
        fed with: a channel scored on raw admissions would price itself at about
        twice what it bought, and the two channels do not duplicate at the same
        rate — the share is by construction ground nobody has walked.
        """
        if self.exploration is None:
            return None
        return self.exploration.settle(
            spent.get(novelty_module.SHARE) or {"slots": 0, "admissions": 0},
            spent.get(novelty_module.CONTEST) or {"slots": 0, "admissions": 0},
        )

    def _account(
        self, partition: str, report: dict, minutes: float, nodes: int, channels: dict
    ) -> dict:
        """Charge the minutes, count the fates, credit the distinct finds, and
        prove the batch's books balance.

        Three identities close here rather than two, because the frontier and the
        books are now fed by different populations: what reached the frontier is
        the admitted *plus* the expandable, and only the admitted are supply.
        """
        candidates = report["candidates"]
        # Which claim paid for each candidate's parent. A row whose parent is not
        # in the map came from a node this batch did not take, which cannot
        # happen — so it is counted under the contest and would show up as a
        # channel column that does not add to the batch's slots.
        channel_of = {
            row.get("parent_node_id"): channels.get(
                row.get("parent_node_id"), novelty_module.CONTEST
            )
            for row in candidates
        }
        per_channel: dict = {}
        for name in set(channels.values()):
            per_channel[name] = _channel_cell()
            per_channel[name]["slots"] = sum(1 for v in channels.values() if v == name)
        fates = Counter(row["fate"] for row in candidates)
        unknown = set(fates) - set(ledger_module.FATES)
        if unknown:
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: fate(s) {sorted(unknown)} "
                f"are not in the ledger's declared fates. A gate that can refuse a candidate "
                f"without naming itself is a gate that can eat supply and still balance."
            )
        admitted = fates.get(ledger_module.SURVIVED, 0)
        expandable = fates.get(ledger_module.EXPANDABLE, 0)
        if admitted + expandable != len(report["survivors"]):
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {admitted} admitted plus "
                f"{expandable} expandable but {len(report['survivors'])} nodes reached the "
                f"frontier."
            )

        for row in candidates:
            name = channel_of.get(row.get("parent_node_id"))
            bucket = per_channel.get(name)
            if bucket is None:
                continue
            bucket["found"] += 1
            if row["fate"] == ledger_module.SURVIVED:
                bucket["admitted"] += 1
            elif row["fate"] == ledger_module.EXPANDABLE:
                bucket["expandable"] += 1
            else:
                bucket["refused"] += 1

        distinct = duplicate = 0
        units = 0.0
        for row in candidates:
            if row["fate"] != ledger_module.SURVIVED:
                continue
            key = key_of_row(row)
            # A row with no resolvable identity is counted as distinct: it is real
            # supply, and the alternative is silently dropping it. It simply
            # cannot suppress a later copy of itself.
            if key is not None and key in self.seen:
                duplicate += 1
                continue
            if key is not None:
                self.seen.add(key)
            distinct += 1
            bucket = per_channel.get(channel_of.get(row.get("parent_node_id")))
            if bucket is not None:
                bucket["distinct"] += 1
                # The head's read of this admission, into the channel's histogram.
                # Only distinct admissions, because those are what the deficit is
                # fed with and the median has to be about the same population the
                # counts beside it are.
                index = score_bin(row.get("score"))
                if index is not None:
                    bucket["scores"][index] += 1
            units += self.quota.credit(partition, row.get("score"), row.get("score_great"))
            # A booked location may be another partition's supply: the twin
            # channel derives a Julia parameter from an admitted parameter-plane
            # find. Offered once per *distinct* admission, so a duplicate cannot
            # spend the c-spacing floor twice.
            if self.refill is not None:
                self.refill.note_admission(partition, row)

        if len(candidates) != sum(fates.values()):
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {len(candidates)} candidates "
                f"found against {sum(fates.values())} fated."
            )
        if admitted != distinct + duplicate:
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {admitted} admitted != "
                f"{distinct} distinct + {duplicate} duplicate."
            )

        self.quota.charge(partition, minutes, nodes)
        self.quota.note_candidates(partition, len(candidates))
        self.quota.note_admission(partition, distinct)
        self.tally.expanded += nodes
        self.tally.found += len(candidates)
        self.tally.admitted += admitted
        self.tally.expandable += expandable
        self.tally.distinct += distinct
        self.tally.duplicate += duplicate
        self.tally.units += units
        for fate, n in fates.items():
            if fate not in (ledger_module.SURVIVED, ledger_module.EXPANDABLE):
                self.tally.refused[fate] += n
        for name, row in per_channel.items():
            for into in (self.tally.channel(name), self.tally.cell(partition, name)):
                for field_name, value in row.items():
                    if field_name == "scores":
                        for index, count in enumerate(value):
                            into["scores"][index] += count
                    else:
                        into[field_name] += value
        return {
            "by_channel": {
                name: {k: v for k, v in row.items() if k != "scores"}
                for name, row in per_channel.items()
            },
            "found": len(candidates),
            "admitted": admitted,
            "expandable": expandable,
            "distinct": distinct,
            "duplicate": duplicate,
            "currency": round(units, 4),
        }

    def _apply_memory(self, partition: str, report: dict) -> None:
        """Discount a survivor whose neighbourhood earlier runs already walked.

        Applied to ordinary descent only — the population a scorer has an opinion
        about — and never to a reframing's proposal, which holds a reserved floor
        precisely because nothing has been trained on it. It multiplies the *score*
        term of the priority and leaves the exploration draw alone, so a saturated
        place with a great score loses to a fresh place with a merely good one and
        still beats a fresh place with a bad one.

        With no scorer wired in, every score term is the neutral prior and this
        moves nothing. That is the honest state and not a disabled mechanism: there
        is no quality signal to discount yet, and the memory starts biting the day
        one arrives.
        """
        if self.memory is None or self.saturation_strength <= 0:
            return
        by_node = {row.get("node_id"): row for row in report["candidates"] if row.get("node_id")}
        for node in report["survivors"]:
            row = by_node.get(node["node_id"])
            if row is None:
                continue
            density = self.memory.density(
                partition_of_family(node["family"]),
                saturation_module.identity_of(node["family"]),
                node["center_re"],
                node["center_im"],
            )
            self.tally.saturation_seen += 1
            self.tally.saturation(partition)["seen"] += 1
            if density <= 0:
                continue
            self.tally.saturation_discounted += 1
            self.tally.saturation(partition)["discounted"] += 1
            discount = saturation_module.discount(density, self.saturation_strength)
            score = row.get("score")
            term = NEUTRAL_PRIOR if score is None else float(score)
            node["priority"] += (discount - 1.0) * term

    # ---------------------------------------------------------------- the run

    def run(self) -> dict:
        """Serve batches until the budget or the frontier runs out."""
        stopped = None
        while True:
            stopped = self.exhausted()
            if stopped is not None:
                break
            outcome = self.run_batch()
            if outcome.get("stalled"):
                stopped = "nothing servable"
                break
            self.checkpoint()
        return self.finish(stopped or "budget")

    def finish(self, reason: str) -> dict:
        """Refine the walk's best framings, write the run's summary, close the ledger.

        The refine leg is the last thing the walk does and the first thing this
        does, in that order: it is a statement about the whole walk, so it cannot
        run until there is a whole walk to rank, and the summary has to be able to
        report what it cost. Its minutes are charged to their own bucket — the
        run's `--minutes` budget is already spent by the time this is reached,
        and hiding a close-time leg inside the operator suite's clock would make
        the operators look more expensive on the runs that refined most.
        """
        started = time.monotonic()
        refined = self.walk.refine_framings(log=print)
        self.tally.refine_minutes += (time.monotonic() - started) / 60.0
        summary = self.summary(reason) | {"refine": refined}
        (self.run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        self.walk.ledger.write("summary", **summary)
        self.walk.ledger.close()
        return summary

    def summary(self, reason: str) -> dict:
        queues = self.queues()
        return {
            "stopped": reason,
            "batches": self.tally.batches,
            "active_minutes": round(self.active_minutes, 3),
            "budget_minutes": self.budget.minutes,
            "finish_by": self.finish_by,
            "tally": self.tally.as_dict(),
            "queues": queues,
            "frontier": len(self.walk.frontier),
            "walk": {
                "seed": self.walk.seed,
                "roots": self.walk.next_root_id - 1,
                "counts": dict(sorted(self.walk.tally.items())),
                "probe": self.walk.governor.tally(),
                # What each reframing operator fired and what it cost. The
                # per-operator availability and refusal counts are in `counts`
                # above (`reframing:<operator>:<available|reason>`); this is the
                # price beside them, which nothing recorded before.
                "operators": self._operator_report(),
                "ledger": tracked_name(self.walk.ledger.path),
            },
            # Which judge wrote the scores on this run's rows, and what its
            # renders cost. The census reads those scores, so a summary that did
            # not name the judge would leave a ledger nobody could attribute.
            "scorer": self.walk.scorer.name,
            "scoring": self.walk.scoring_record(),
            # What the run asserted about the picture that judge was handed, and
            # the one line that re-asks it on this run's own survivors. The second
            # is a report: nothing above it reads the number.
            "identity": self.walk.identity,
            "gate_flips": self.walk.gate_flips(),
            "quota": self.quota.summary(),
            # The two novelty levers, side by side with what they cost and bought.
            # Both are reported whether or not they are on: a run that turned one
            # off and a run that never had it are different runs, and a readout
            # that omits the row cannot say which this was.
            "exploration": (
                {"status": "off"}
                if self.exploration is None
                else self.exploration.summary() | {"bought": self._channel_report()}
            ),
            "lineage_discount": {
                "status": "off" if self.discount_k <= 0 else "on",
                "k": self.discount_k,
                "floor": self.discount_floor,
                "note": (
                    "no scorer is wired in, so every score term is the neutral prior and the "
                    "discount cannot reorder anything"
                    if self.walk.scorer.name == "null"
                    else None
                ),
            },
            "lineages": self.walk.lineages(),
            "refill": (
                None
                if self.refill is None
                else self.refill.summary(self.active_minutes * 60.0)
                | {"deferred": self.refill.deferred(queues)}
            ),
            "saturation": (
                {"status": "off"}
                if self.memory is None or self.saturation_strength <= 0
                else {
                    "status": "on",
                    "strength": self.saturation_strength,
                    "index": self.memory.summary(),
                    "seen": self.tally.saturation_seen,
                    "discounted": self.tally.saturation_discounted,
                    "note": (
                        "no scorer is wired in, so every score term is the neutral prior and "
                        "the discount cannot reorder anything"
                        if self.walk.scorer.name == "null"
                        else None
                    ),
                }
            ),
        }

    def _operator_report(self) -> dict:
        """Firings, seconds, and the share of the run's charged clock each took.

        Against `reframe_minutes` rather than against the whole leg, because the
        question an operator is switched off to answer is what it costs relative
        to the other operators and to the expansion it is triggered by — and both
        are here.
        """
        total = self.tally.charged() * 60.0
        rows = {}
        for name, cell in sorted(self.walk.operator_seconds.items()):
            rows[name] = {
                "firings": cell["firings"],
                "seconds": round(cell["seconds"], 3),
                "seconds_per_firing": (
                    round(cell["seconds"] / cell["firings"], 4) if cell["firings"] else None
                ),
                "share_of_charged_clock": (
                    round(cell["seconds"] / total, 4) if total > 0 else None
                ),
            }
        return rows

    def _channel_report(self) -> dict:
        """What each claim on the batch spent and returned, off the run's own
        tally rather than off the share's pricing accumulators — the second are
        smoothed and are evidence, not a count."""
        return {
            name: _channel_report(self.tally.channel(name))
            for name in (novelty_module.SHARE, novelty_module.CONTEST)
        }

    # ------------------------------------------------------------- the state

    def state_path(self) -> Path:
        return self.run_dir / "state.json"

    def checkpoint(self) -> None:
        """Write the batch boundary's state, atomically.

        Written to a sibling and renamed, so a kill during the write leaves the
        previous checkpoint intact rather than half of the next one.
        """
        state = {
            "schema": STATE_SCHEMA,
            "batch": self.batch,
            "active_minutes": self.active_minutes,
            "tally": {
                "batches": self.tally.batches,
                "expanded": self.tally.expanded,
                "found": self.tally.found,
                "admitted": self.tally.admitted,
                "expandable": self.tally.expandable,
                "distinct": self.tally.distinct,
                "duplicate": self.tally.duplicate,
                "refused": dict(self.tally.refused),
                "units": self.tally.units,
                "saturation_seen": self.tally.saturation_seen,
                "saturation_discounted": self.tally.saturation_discounted,
                "by_channel": self.tally.by_channel,
                "by_partition": self.tally.by_partition,
                "saturation_by_partition": self.tally.saturation_by_partition,
                "expand_minutes": self.tally.expand_minutes,
                "reframe_minutes": self.tally.reframe_minutes,
                "refine_minutes": self.tally.refine_minutes,
            },
            "walk": {
                "frontier": self.walk.frontier,
                "expansions": {str(k): v for k, v in self.walk.expansions.items()},
                "next_node_id": self.walk.next_node_id,
                "next_root_id": self.walk.next_root_id,
                "visited_reframings": [list(k) for k in self.walk.visited_reframings],
                # Which roots the expansion grace applies below. A resumed run that
                # rebuilt this from nothing would silently drop the grace for every
                # root the first session drew, and the ledger would carry two
                # policies under one run seed.
                "plane_roots": sorted(self.walk.plane_roots),
                # What each root is. A resumed session classifies the frontier's
                # lineages against the cross-run index, and a node minted in the
                # first session names a root this process never drew — so without
                # this the share would quietly stop protecting half its members.
                "roots": {str(k): v for k, v in self.walk.roots.items()},
                "admitted": {str(k): v for k, v in self.walk.admitted.items()},
                "saturated": sorted(self.walk.saturated),
                "counts": self.walk.tally,
                "rng": _rng_state(self.walk.rng),
            },
            "quota": self.quota.state(),
            "seen": [list(key) for key in self.seen],
            "refill": (
                None
                if self.refill is None
                else {
                    "cursor": self.refill.cursor,
                    "last_refill": self.refill.last_refill,
                    "seconds": self.refill.seconds,
                    "draws": self.refill.draws,
                    "roots_added": self.refill.roots_added,
                    # Checkpointed whole. The standing legs would re-prime
                    # identically, but the parameters derived from *this run's*
                    # admissions would not, and a c-spacing floor that forgot half
                    # its accepted parameters hands out near-duplicates of what it
                    # has already spent.
                    "twins": (None if self.refill.twins is None else self.refill.twins.state()),
                }
            ),
        }
        path = self.state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.writing")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    def resume(self) -> bool:
        """Adopt a checkpoint if one is there. Returns whether it was."""
        path = self.state_path()
        if not path.is_file():
            return False
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("schema") != STATE_SCHEMA:
            raise ValueError(f"{path}: schema {state.get('schema')!r}, expected {STATE_SCHEMA}")
        self.batch = int(state["batch"])
        self.active_minutes = float(state["active_minutes"])
        saved = state.get("tally") or {}
        self.tally = Tally(
            batches=int(saved.get("batches", 0)),
            expanded=int(saved.get("expanded", 0)),
            found=int(saved.get("found", 0)),
            admitted=int(saved.get("admitted", 0)),
            expandable=int(saved.get("expandable", 0)),
            distinct=int(saved.get("distinct", 0)),
            duplicate=int(saved.get("duplicate", 0)),
            refused=Counter(saved.get("refused") or {}),
            units=float(saved.get("units", 0.0)),
            saturation_seen=int(saved.get("saturation_seen", 0)),
            saturation_discounted=int(saved.get("saturation_discounted", 0)),
            by_channel={k: dict(v) for k, v in (saved.get("by_channel") or {}).items()},
            by_partition={
                partition: {name: dict(cell) for name, cell in channels.items()}
                for partition, channels in (saved.get("by_partition") or {}).items()
            },
            saturation_by_partition={
                partition: dict(cell)
                for partition, cell in (saved.get("saturation_by_partition") or {}).items()
            },
            expand_minutes=float(saved.get("expand_minutes", 0.0)),
            reframe_minutes=float(saved.get("reframe_minutes", 0.0)),
            refine_minutes=float(saved.get("refine_minutes", 0.0)),
        )
        walk_state = state.get("walk") or {}
        self.walk.frontier = list(walk_state.get("frontier") or [])
        self.walk.expansions = {
            int(k): int(v) for k, v in (walk_state.get("expansions") or {}).items()
        }
        self.walk.next_node_id = int(walk_state.get("next_node_id", self.walk.next_node_id))
        self.walk.next_root_id = int(walk_state.get("next_root_id", self.walk.next_root_id))
        self.walk.visited_reframings = {
            (row[0], row[1]) for row in (walk_state.get("visited_reframings") or [])
        }
        self.walk.plane_roots = {int(root) for root in (walk_state.get("plane_roots") or [])}
        self.walk.roots = {int(k): v for k, v in (walk_state.get("roots") or {}).items()}
        self.walk.admitted = {int(k): int(v) for k, v in (walk_state.get("admitted") or {}).items()}
        self.walk.saturated = {int(root) for root in (walk_state.get("saturated") or [])}
        self.walk.tally = dict(walk_state.get("counts") or {})
        if walk_state.get("rng"):
            self.walk.rng.setstate(_rng_from_state(walk_state["rng"]))
        self.quota.load_state(state.get("quota") or {}, reopen_caps=True)
        self.seen = {tuple(_tuples(key)) for key in (state.get("seen") or [])}
        if self.refill is not None and state.get("refill"):
            saved_refill = state["refill"]
            self.refill.cursor = {k: int(v) for k, v in (saved_refill.get("cursor") or {}).items()}
            self.refill.last_refill = {
                k: int(v) for k, v in (saved_refill.get("last_refill") or {}).items()
            }
            self.refill.seconds = float(saved_refill.get("seconds", 0.0))
            self.refill.draws = int(saved_refill.get("draws", 0))
            self.refill.roots_added = int(saved_refill.get("roots_added", 0))
            if self.refill.twins is not None and saved_refill.get("twins"):
                self.refill.twins.load_state(saved_refill["twins"])
        return True


def _tuples(value):
    """JSON turns every tuple into a list. A location key is nested tuples, and it
    has to come back as one or a resumed run cannot recognize its own finds."""
    if isinstance(value, list):
        return tuple(_tuples(item) for item in value)
    return value


def _rng_state(rng: random.Random) -> list:
    version, internal, gauss = rng.getstate()
    return [version, list(internal), gauss]


def _rng_from_state(state) -> tuple:
    version, internal, gauss = state
    return (int(version), tuple(int(v) for v in internal), gauss)


__all__ = ["Budget", "Harvest", "ReconcileError", "STATE_SCHEMA", "Tally"]
