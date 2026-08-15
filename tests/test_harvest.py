"""The quota and the loop: does the realized mix actually come out where it was
aimed, and does the run stay honest for hours.

The last two tests here are a **smoke harvest** — a small, seeded, real run
through the real engine — because everything above them can be true of a loop that
never ran a batch.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.discovery.walk import Limits, Policy, Walk
from fractal_wallpapers.supply.census import Census, MachineStock
from fractal_wallpapers.supply.harvest import Budget, Harvest, ReconcileError
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX
from fractal_wallpapers.supply.prices import load_table
from fractal_wallpapers.supply.quota import Quota
from fractal_wallpapers.supply.refill import Refill

POOL_FED = ["julia:mandelbrot", "phoenix"]


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


def census(currency: dict | None = None, partitions=ALL_PARTITIONS) -> Census:
    """A census with no ledgers and no corpus behind it, so a test states its own
    stock instead of inheriting whatever this checkout happens to hold."""
    currency = currency or {}
    return Census(
        counts={},
        currency={p: float(currency.get(p, 0.0)) for p in partitions},
        partitions=tuple(partitions),
        machine=MachineStock.empty(partitions),
    )


def quota(currency=None, partitions=ALL_PARTITIONS, **kwargs) -> Quota:
    kwargs.setdefault("external", {CLASSIC_PHOENIX})
    kwargs.setdefault("prices_config", load_table())
    return Quota(partitions, census=census(currency, partitions), **kwargs)


# --------------------------------------------------------------------------- #
# the quota
# --------------------------------------------------------------------------- #


def test_a_cold_start_allocation_is_well_defined() -> None:
    """No labels and no finds anywhere is this repository's state today. Every
    deficit is zero, so the clock spreads uniformly over the partitions a walk can
    serve — decided, not floored, and reported as such."""
    allocation = quota().allocation()
    served = [p for p in ALL_PARTITIONS if p != CLASSIC_PHOENIX]
    assert sum(allocation.share.values()) == pytest.approx(1.0)
    assert allocation.share[CLASSIC_PHOENIX] == 0.0
    assert all(allocation.share[p] == pytest.approx(1 / len(served)) for p in served)
    assert allocation.floored == set(), "a cold start was not decided by the floor"


def test_the_machine_leg_moves_the_deficit_and_both_reads_are_kept() -> None:
    """`deficit` is what the run allocates against; `deficit_labels_only` says how
    much of it the scorer's opinion moved. Asking that is the first thing anybody
    does, and it should be a read rather than a reconstruction."""
    stock = census({"mandelbrot": 30.0})
    stock.machine = MachineStock(
        counts={},
        currency={p: (50.0 if p == "phoenix" else 0.0) for p in ALL_PARTITIONS},
        discount=0.2,
        partitions=tuple(ALL_PARTITIONS),
    )
    held = Quota(ALL_PARTITIONS, census=stock, external={CLASSIC_PHOENIX})
    assert held.stock["phoenix"] == pytest.approx(10.0)
    assert held.deficit["phoenix"] == pytest.approx(0.0), "ten against a ratio-1 target of ten"
    assert held.deficit_labels_only["phoenix"] == pytest.approx(10.0)


def test_the_realized_mix_converges_on_the_intent_whatever_a_partition_costs() -> None:
    """The headline property, and the reason the quota measures rather than
    steers: a partition that happens to expand cheaply cannot buy itself a larger
    share of the clock, because the share is denominated in minutes."""
    held = quota({"mandelbrot": 100.0})
    minutes = {p: (0.05 if p.startswith("julia:") else 1.0) for p in ALL_PARTITIONS}
    served = [p for p in ALL_PARTITIONS if p != CLASSIC_PHOENIX]
    queues = dict.fromkeys(served, 50)
    for _ in range(400):
        slots, _ = held.slots(queues, 8)
        spent = 0.0
        for partition, n in slots.items():
            if n:
                held.charge(partition, n * minutes[partition], n)
                spent += n * minutes[partition]
                for _ in range(n):
                    held.credit(partition, 0.9)
        held.close_batch(spent)
    report = held.mix_report()
    assert report["gap_minutes_effective"] < 0.05
    for partition in served:
        row = report["minutes"][partition]
        assert row["realized"] == pytest.approx(row["effective"], abs=0.02)
    cheap = held.realized.slots["julia:mandelbrot"]
    dear = held.realized.slots["phoenix"]
    assert cheap > 10 * dear, "being cheap buys more turns, and not more of the clock"


def test_a_partition_that_finds_nothing_at_all_is_capped_out_of_service() -> None:
    """An unbounded stall on a queue full of dead ground would otherwise eat that
    partition's whole share of the run."""
    held = quota()
    served = [p for p in ALL_PARTITIONS if p != CLASSIC_PHOENIX]
    queues = dict.fromkeys(served, 50)
    for _ in range(200):
        slots, _ = held.slots(queues, 8)
        spent = 0.0
        for partition, n in slots.items():
            if n:
                held.charge(partition, float(n), n)
                spent += float(n)
        held.close_batch(spent)
    assert held.cost.capped == set(served)
    assert held.slots(queues, 8)[0] == dict.fromkeys(served, 0)


def test_the_floor_is_held_over_a_run_and_not_merely_allocated() -> None:
    """A floored partition allocated its share in every batch and served in none
    is the failure the carry exists for. Twenty batches at a 5% floor is the exact
    bound, so a run of a hundred has no excuse."""
    held = quota({"mandelbrot": 1000.0})
    served = [p for p in ALL_PARTITIONS if p != CLASSIC_PHOENIX]
    queues = dict.fromkeys(served, 50)
    for _ in range(100):
        slots, _ = held.slots(queues, 4)
        spent = 0.0
        for partition, n in slots.items():
            if n:
                held.charge(partition, float(n), n)
                spent += float(n)
        held.close_batch(spent)
    unspent = held.unspent_floor()
    assert unspent["alarms"] == []
    assert unspent["starved"] == []
    assert all(held.realized.minutes[p] > 0 for p in served)


def test_an_externally_supplied_partition_is_never_served_and_keeps_its_books() -> None:
    """It loses the clock and nothing else: the ratio, the target, the deficit and
    every tally key stay, because they are statements about labels and stay true."""
    held = quota({"mandelbrot": 30.0})
    queues = dict.fromkeys(ALL_PARTITIONS, 50)
    slots, _ = held.slots(queues, 8)
    assert slots[CLASSIC_PHOENIX] == 0
    assert held.ratios[CLASSIC_PHOENIX] == pytest.approx(0.2)
    assert held.target[CLASSIC_PHOENIX] == pytest.approx(2.0)
    assert CLASSIC_PHOENIX in held.deficit
    assert CLASSIC_PHOENIX not in held.unspent_floor()["per_partition"]


def test_a_capped_partition_keeps_its_intent_and_loses_its_slots() -> None:
    """Its unserved share shows up as a miss with a named cause rather than
    quietly redistributing."""
    held = quota()
    held.cost.capped.add("phoenix")
    slots, trace = held.slots(dict.fromkeys(ALL_PARTITIONS, 20), 8)
    assert slots["phoenix"] == 0
    assert trace["capped"] == ["phoenix"]
    assert trace["intended"]["phoenix"] > 0.0


def test_the_trace_says_what_every_batch_decided_and_why(tmp_path) -> None:
    """Every slot a run spends has to be attributable afterwards without
    re-deriving the rule that spent it."""
    held = quota(run_dir=tmp_path)
    held.slots(dict.fromkeys(ALL_PARTITIONS, 5), 4)
    held.charge("phoenix", 1.0)
    held.close_batch(1.0)
    held.log_batch(0, {"phoenix": None})
    row = json.loads((tmp_path / "quota.jsonl").read_text(encoding="utf-8").strip())
    for key in ("slots", "intended", "effective", "gap", "floor_debt", "price", "queues"):
        assert key in row, key


def test_the_quota_state_round_trips(tmp_path) -> None:
    held = quota({"mandelbrot": 30.0})
    held.slots(dict.fromkeys(ALL_PARTITIONS, 5), 4)
    held.charge("phoenix", 2.5)
    held.close_batch(2.5)
    restored = quota({"mandelbrot": 30.0})
    restored.load_state(held.state())
    assert restored.realized.minutes == held.realized.minutes
    assert restored.floor_ledger.total_minutes == held.floor_ledger.total_minutes
    assert restored.cost.raw == held.cost.raw


# --------------------------------------------------------------------------- #
# the loop's books
# --------------------------------------------------------------------------- #


def harvest(tmp_path, **kwargs) -> Harvest:
    walk = Walk(
        out_dir=tmp_path / "run",
        seed=20260814,
        limits=Limits(batch=4),
        policy=Policy(candidates=2, node_width=96),
    )
    kwargs.setdefault("budget", Budget(minutes=0.0, batches=2))
    return Harvest(walk, quota(), **kwargs)


def candidate(fate: str, node_id=None, re: str = "0.1") -> dict:
    return {
        "kind": "candidate",
        "fate": fate,
        "node_id": node_id,
        "score": None,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": re, "center_im": "0.0", "width": "0.5"},
    }


def test_a_fate_the_ledger_never_declared_ends_the_run(tmp_path) -> None:
    """A gate that can refuse a candidate without naming itself is a gate that can
    eat supply and still balance."""
    run = harvest(tmp_path)
    report = {"candidates": [candidate("mystery_gate")], "survivors": []}
    with pytest.raises(ReconcileError, match="declared fates"):
        run._account("mandelbrot", report, 1.0, 1)


def test_a_survivor_that_never_reached_the_frontier_ends_the_run(tmp_path) -> None:
    """The two halves are produced by different code paths, which is what makes
    comparing them worth doing."""
    run = harvest(tmp_path)
    report = {"candidates": [candidate(ledger_module.SURVIVED, node_id=7)], "survivors": []}
    with pytest.raises(ReconcileError, match="reached the frontier"):
        run._account("mandelbrot", report, 1.0, 1)


def test_admissions_are_counted_as_distinct_locations(tmp_path) -> None:
    """A raw count of what a scorer waved through runs about twice what the
    distinct-location count does, so a run reporting the raw number reports
    roughly double the supply it produced."""
    run = harvest(tmp_path)
    rows = [
        candidate(ledger_module.SURVIVED, node_id=1, re="0.1"),
        candidate(ledger_module.SURVIVED, node_id=2, re="0.100"),  # the same location
        candidate(ledger_module.SURVIVED, node_id=3, re="0.2"),
        candidate("flat"),
    ]
    counted = run._account("mandelbrot", {"candidates": rows, "survivors": rows[:3]}, 1.0, 2)
    assert counted == {
        "found": 4,
        "survived": 3,
        "distinct": 2,
        "duplicate": 1,
        "currency": 0.0,
    }
    assert run.quota.realized.admitted["mandelbrot"] == 2


def test_the_books_balance_across_every_named_bucket(tmp_path) -> None:
    run = harvest(tmp_path)
    rows = [candidate(fate) for fate in ("flat", "interior_cap", "occupancy_floor")]
    rows.append(candidate(ledger_module.SURVIVED, node_id=1))
    counted = run._account("phoenix", {"candidates": rows, "survivors": rows[-1:]}, 1.0, 1)
    assert counted["found"] == counted["survived"] + sum(run.tally.refused.values())


# --------------------------------------------------------------------------- #
# a real, small, seeded run
# --------------------------------------------------------------------------- #


@needs_engine
def test_a_smoke_harvest_serves_more_than_one_partition_and_balances(tmp_path) -> None:
    """Small and seeded, through the real engine: two batches over the two
    pool-fed partitions."""
    walk = Walk(
        out_dir=tmp_path / "run",
        seed=20260814,
        limits=Limits(batch=4, root_expansions=3),
        policy=Policy(candidates=2, node_width=96),
    )
    run = Harvest(
        walk,
        quota(run_dir=tmp_path / "run"),
        budget=Budget(minutes=0.0, batches=2),
        batch_size=4,
        refill=Refill(walk, low_water=2, per_draw=2, external={CLASSIC_PHOENIX}),
    )
    summary = run.run()

    assert summary["batches"] == 2
    assert summary["stopped"] == "batch budget"
    tally = summary["tally"]
    assert tally["found"] == tally["survived"] + sum(tally["refused"].values())
    assert tally["survived"] == tally["distinct_admissions"] + tally["duplicate_admissions"]
    assert tally["currency"] == 0.0, "no scorer, so nothing is a keeper yet"

    served = {p for p, row in summary["quota"]["mix"]["minutes"].items() if row["realized"] > 0}
    assert served <= set(POOL_FED), "only the pool-fed partitions can be served here"
    assert (tmp_path / "run" / "quota.jsonl").is_file()

    # The partitions no channel can feed are named with a reason, never silently
    # absent — and the externally-supplied one is not called starved at all.
    deferred = summary["refill"]["deferred"]
    assert "mandelbrot" in deferred and "julia:multibrot3" in deferred
    assert CLASSIC_PHOENIX not in deferred


@needs_engine
def test_a_killed_run_resumes_rather_than_restarting(tmp_path) -> None:
    """The checkpoint is written after the reconcile, so every state a run can be
    resumed from is a state whose books balanced."""

    def build(batches: int) -> Harvest:
        walk = Walk(
            out_dir=tmp_path / "run",
            seed=20260814,
            limits=Limits(batch=4, root_expansions=3),
            policy=Policy(candidates=2, node_width=96),
        )
        return Harvest(
            walk,
            quota(run_dir=tmp_path / "run"),
            budget=Budget(minutes=0.0, batches=batches),
            batch_size=4,
            refill=Refill(walk, low_water=2, per_draw=2, external={CLASSIC_PHOENIX}),
        )

    first = build(1)
    assert first.resume() is False
    first.run()
    found = first.tally.found

    second = build(3)
    assert second.resume() is True, "a checkpoint is there and is adopted"
    assert second.batch == 1
    assert second.tally.found == found
    assert second.seen, "the locations already found came back as identities"
    summary = second.run()
    assert summary["batches"] == 3
    assert summary["tally"]["found"] > found
    assert summary["active_minutes"] > first.active_minutes
