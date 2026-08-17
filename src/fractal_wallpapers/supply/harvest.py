"""The production loop: turn a clock into new good material where it is scarcest.

A walk finds places. A harvest keeps finding them, for hours, in the partitions
that need it most — and that is a different program, because everything that goes
wrong over six unattended hours is invisible in a program that runs for six
seconds.

```text
per batch:  refill anything starved
            ask the quota how the batch's slots divide between partitions
            take each partition's slots off its own queue, expand, score, reframe
            charge the minutes, credit the finds, close the price window
            reconcile what was found against what was written
            checkpoint
```

Four things this loop does that a walk does not.

**The batch is divided between partitions by the quota**, not by priority alone.
Priority decides which of *one partition's* nodes to expand; the quota decides how
many of them it gets. Those are different questions, and letting the second fall
out of the first is exactly how a mix stops being enforced.

**Minutes are charged per partition, not per batch.** The engine expands one
family per call, and a family belongs to exactly one partition, so a batch that
spans four partitions produces four timed pieces of work rather than one number to
apportion after the fact. The price is measured, so it should be measured.

**Every batch reconciles, and a batch that does not balance ends the run.** Two
identities have to close: every candidate the engine reported was written with a
fate this project knows, and every survivor either is a new location or is one the
run already had. A long unattended run that silently loses candidates is exactly
the failure a summary cannot show you afterwards — the numbers all look plausible,
because the missing ones are missing from both sides.

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
from fractal_wallpapers.supply import saturation as saturation_module
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, partition_of_family
from fractal_wallpapers.supply.quota import Quota
from fractal_wallpapers.supply.refill import Refill

STATE_SCHEMA = 1


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
    """What the run has found, in the buckets the reconcile is written in."""

    batches: int = 0
    found: int = 0
    survived: int = 0
    distinct: int = 0
    duplicate: int = 0
    refused: Counter = field(default_factory=Counter)
    units: float = 0.0
    saturation_seen: int = 0
    saturation_discounted: int = 0

    def as_dict(self) -> dict:
        return {
            "batches": self.batches,
            "found": self.found,
            "survived": self.survived,
            "distinct_admissions": self.distinct,
            "duplicate_admissions": self.duplicate,
            "refused": dict(sorted(self.refused.items())),
            "currency": round(self.units, 4),
            "saturation_seen": self.saturation_seen,
            "saturation_discounted": self.saturation_discounted,
        }


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
        partitions=ALL_PARTITIONS,
    ):
        self.walk = walk
        self.quota = quota
        self.budget = budget or Budget()
        self.batch_size = int(batch_size if batch_size is not None else walk.limits.batch)
        self.refill = refill
        self.memory = memory
        self.saturation_strength = float(saturation_strength)
        self.partitions = list(partitions)
        self.run_dir = Path(walk.out_dir)
        self.tally = Tally()
        self.active_minutes = 0.0
        self.seen: set = set()
        self.batch = 0
        self._partition_cache: dict = {}

    # ------------------------------------------------------------- the shape

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
        self.walk.evict_capped()
        counts = dict.fromkeys(self.partitions, 0)
        for node in self.walk.frontier:
            partition = self.partition_of(node)
            counts[partition] = counts.get(partition, 0) + 1
        return counts

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
        queues = self.queues()
        refilled = {}
        if self.refill is not None:
            refilled = self.refill.run(queues, self.batch, self.active_minutes * 60.0)
            if refilled.get("roots"):
                queues = self.queues()

        slots, trace = self.quota.slots(queues, self.batch_size)
        served = {p: n for p, n in slots.items() if n > 0}
        if not served:
            return {"served": {}, "stalled": True, "queues": queues}

        self.walk.batch_index = self.batch
        minutes_total = 0.0
        per_partition = {}
        for partition in sorted(served):
            nodes = [node for node in self.walk.frontier if self.partition_of(node) == partition]
            taken = self.walk.pop_batch(pool=nodes, size=served[partition])
            if not taken:
                continue
            started = time.monotonic()
            report = self.walk.expand(taken)
            self._apply_memory(report)
            self.walk.trigger_reframings(report["survivors"])
            minutes = (time.monotonic() - started) / 60.0
            minutes_total += minutes
            counted = self._account(partition, report, minutes, len(taken))
            per_partition[partition] = {"nodes": len(taken), "minutes": round(minutes, 4)} | counted

        self.active_minutes += minutes_total
        sample = self.quota.close_batch(minutes_total)
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

    def _account(self, partition: str, report: dict, minutes: float, nodes: int) -> dict:
        """Charge the minutes, count the fates, credit the distinct finds, and
        prove the batch's books balance."""
        candidates = report["candidates"]
        fates = Counter(row["fate"] for row in candidates)
        unknown = set(fates) - set(ledger_module.FATES)
        if unknown:
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: fate(s) {sorted(unknown)} "
                f"are not in the ledger's declared fates. A gate that can refuse a candidate "
                f"without naming itself is a gate that can eat supply and still balance."
            )
        survived = fates.get(ledger_module.SURVIVED, 0)
        if survived != len(report["survivors"]):
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {survived} candidates recorded "
                f"as survived but {len(report['survivors'])} nodes reached the frontier."
            )

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
            units += self.quota.credit(partition, row.get("score"), row.get("score_great"))

        if len(candidates) != sum(fates.values()):
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {len(candidates)} candidates "
                f"found against {sum(fates.values())} fated."
            )
        if survived != distinct + duplicate:
            raise ReconcileError(
                f"[reconcile] batch {self.batch} in {partition}: {survived} survivors != "
                f"{distinct} distinct + {duplicate} duplicate."
            )

        self.quota.charge(partition, minutes, nodes)
        self.quota.note_candidates(partition, len(candidates))
        self.quota.note_admission(partition, distinct)
        self.tally.found += len(candidates)
        self.tally.survived += survived
        self.tally.distinct += distinct
        self.tally.duplicate += duplicate
        self.tally.units += units
        for fate, n in fates.items():
            if fate != ledger_module.SURVIVED:
                self.tally.refused[fate] += n
        return {
            "found": len(candidates),
            "survived": survived,
            "distinct": distinct,
            "duplicate": duplicate,
            "currency": round(units, 4),
        }

    def _apply_memory(self, report: dict) -> None:
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
            if density <= 0:
                continue
            self.tally.saturation_discounted += 1
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
        """Write the run's summary and close the ledger."""
        summary = self.summary(reason)
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
            "tally": self.tally.as_dict(),
            "queues": queues,
            "frontier": len(self.walk.frontier),
            "walk": {
                "seed": self.walk.seed,
                "roots": self.walk.next_root_id - 1,
                "counts": dict(sorted(self.walk.tally.items())),
                "probe": self.walk.governor.tally(),
                "ledger": str(self.walk.ledger.path),
            },
            # Which judge wrote the scores on this run's rows, and what its
            # renders cost. The census reads those scores, so a summary that did
            # not name the judge would leave a ledger nobody could attribute.
            "scorer": self.walk.scorer.name,
            "scoring": self.walk.scoring_record(),
            "quota": self.quota.summary(),
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
                "found": self.tally.found,
                "survived": self.tally.survived,
                "distinct": self.tally.distinct,
                "duplicate": self.tally.duplicate,
                "refused": dict(self.tally.refused),
                "units": self.tally.units,
                "saturation_seen": self.tally.saturation_seen,
                "saturation_discounted": self.tally.saturation_discounted,
            },
            "walk": {
                "frontier": self.walk.frontier,
                "expansions": {str(k): v for k, v in self.walk.expansions.items()},
                "next_node_id": self.walk.next_node_id,
                "next_root_id": self.walk.next_root_id,
                "visited_reframings": [list(k) for k in self.walk.visited_reframings],
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
            found=int(saved.get("found", 0)),
            survived=int(saved.get("survived", 0)),
            distinct=int(saved.get("distinct", 0)),
            duplicate=int(saved.get("duplicate", 0)),
            refused=Counter(saved.get("refused") or {}),
            units=float(saved.get("units", 0.0)),
            saturation_seen=int(saved.get("saturation_seen", 0)),
            saturation_discounted=int(saved.get("saturation_discounted", 0)),
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
