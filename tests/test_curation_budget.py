"""The attempt budget: sized from release need, spread so every prefix is honest."""

from __future__ import annotations

from fractal_wallpapers.curation import budget, floors

SMOOTH, STRANGE = budget.SMOOTH, budget.STRANGE


def offer(**counts) -> dict:
    return {
        partition: [{"key": f"{partition}:{index}"} for index in range(n)]
        for partition, n in counts.items()
    }


def test_the_head_split_is_the_one_the_selection_spends() -> None:
    assert budget.head_slots(6, 0.5) == {SMOOTH: 3, STRANGE: 3}
    assert budget.head_slots(7, 0.5) == {SMOOTH: 3, STRANGE: 4}
    assert budget.head_slots(6, 0.0) == {SMOOTH: 6, STRANGE: 0}


def test_attempts_are_the_multiple_of_a_heads_own_slots() -> None:
    granted, record = budget.head_attempts({SMOOTH: 3, STRANGE: 1}, None)
    assert granted == {SMOOTH: 12, STRANGE: 4}
    assert record["scaled_to_budget"] is False


def test_a_tight_budget_scales_both_heads_proportionally_never_one() -> None:
    """An even split would level the head with the larger need down to the other —
    the mirror of the failure this module exists to fix."""
    granted, record = budget.head_attempts({SMOOTH: 5, STRANGE: 10}, 24)
    assert record["scaled_to_budget"] is True
    assert sum(granted.values()) == 24
    assert granted == {SMOOTH: 8, STRANGE: 16}


def test_attempts_are_budgeted_off_the_seated_slots_not_the_bare_mix() -> None:
    """A partition the guarantee seats is certain to be asked for a picture, so it
    must be budgeted attempts to find one with."""
    supply = offer(**{"mandelbrot": 20, "phoenix:classic": 20})
    plan, record = budget.plan(supply, 2, 0.5, guarantees=["phoenix:classic"])
    seated = record["seated_slots"]
    assert any("phoenix:classic" in v for v in seated.values())
    planned = {
        partition: sum(v.get(partition, 0) for v in record["planned_by_partition"].values())
        for partition in supply
    }
    assert planned["phoenix:classic"] >= floors.ATTEMPT_MULTIPLIER
    assert len(plan) == record["scheduled"]


def test_a_partition_seated_nothing_is_budgeted_nothing() -> None:
    seated = {"mandelbrot": 2, "phoenix": 0}
    assert budget.partition_attempts(seated, 100) == {"mandelbrot": 8, "phoenix": 0}


def test_a_thin_partition_short_fills_and_says_so() -> None:
    supply = offer(**{"mandelbrot": 1, "julia:mandelbrot": 20})
    plan, record = budget.plan(supply, 4, 0.5)
    assert record["supply_short"] > 0
    assert "mandelbrot" in next(iter(record["supply_short_by_partition"].values()))
    assert len(plan) == record["scheduled"] < record["planned"]


def test_every_prefix_of_the_plan_is_near_proportional() -> None:
    """A run stopped half way through has spent its half in the planned mix."""
    supply = offer(**{"mandelbrot": 40, "julia:mandelbrot": 40, "phoenix": 40})
    plan, record = budget.plan(supply, 12, 0.5)
    assert record["prefix_deviation"] <= 1.0
    half = plan[: len(plan) // 2]
    heads = {head: sum(1 for a in half if a.head == head) for head in budget.HEADS}
    assert abs(heads[SMOOTH] - heads[STRANGE]) <= 2


def test_a_locations_rank_is_carried_so_the_log_says_how_deep_the_budget_reached() -> None:
    supply = offer(**{"mandelbrot": 8})
    plan, _ = budget.plan(supply, 2, 0.0)
    ranks = [attempt.rank for attempt in plan if attempt.partition == "mandelbrot"]
    assert ranks == sorted(ranks)
    assert ranks[0] == 0


def test_the_two_heads_share_the_guarantees_rather_than_one_paying_for_all() -> None:
    owed, unplaced = budget.assign_guarantees(["a", "b", "c", "d"], {SMOOTH: 2, STRANGE: 2})
    assert not unplaced
    assert sorted(owed.values()).count(SMOOTH) == 2
    assert sorted(owed.values()).count(STRANGE) == 2


def test_a_guarantee_no_head_has_room_for_is_recorded_not_raised() -> None:
    """The selection knows the candidate counts and can say something true; a
    budget that aborted first would replace that message with a worse one."""
    owed, unplaced = budget.assign_guarantees(["a", "b", "c"], {SMOOTH: 1, STRANGE: 1})
    assert len(owed) == 2
    assert unplaced == ["c"]


def test_realized_fills_are_derived_from_the_log_not_counted_into_the_plan() -> None:
    rows = [
        {"head": SMOOTH, "partition": "mandelbrot"},
        {"head": SMOOTH, "partition": "mandelbrot"},
        {"head": STRANGE, "partition": "phoenix"},
    ]
    assert budget.realized(rows) == {
        SMOOTH: {"mandelbrot": 2},
        STRANGE: {"phoenix": 1},
    }


def test_the_fill_lines_carry_the_three_numbers_a_short_fill_is_read_from() -> None:
    supply = offer(**{"mandelbrot": 40})
    _, record = budget.plan(supply, 6, 0.5, budget=8)
    lines = budget.fill_lines(record, {SMOOTH: {"mandelbrot": 2}})
    assert all("wanted" in line and "budgeted" in line and "realized" in line for line in lines)
