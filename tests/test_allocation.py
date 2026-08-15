"""The floor, the water-filling, the carry, and how a batch's slots are divided.

Three of these tests are about failures that took a production run each to find:
the floor that was allocated in every batch and served in none, the two silences
that are not the same silence, and the apportionment that structurally zeroes the
smallest partition at small batch sizes.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.supply.allocation import (
    FLOOR_FRACTION,
    FloorLedger,
    allocate,
    batch_slots,
    fold_dynamical_intent,
    share_gaps,
)
from fractal_wallpapers.supply.apportion import (
    SlotGuaranteeOverflow,
    allocate_slots,
    prefix_deviation,
    sequence_by_deficit,
)
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX

FOUR = ["a", "b", "c", "d"]
FLAT = dict.fromkeys(FOUR, 1.0)


# --------------------------------------------------------------------------- #
# the intended share
# --------------------------------------------------------------------------- #


def test_the_shares_sum_to_one_and_nobody_is_below_the_floor() -> None:
    allocation = allocate({"a": 100.0, "b": 1.0, "c": 0.0, "d": 0.0}, FLAT, FOUR, floor=0.05)
    assert sum(allocation.share.values()) == pytest.approx(1.0)
    assert all(v >= 0.05 - 1e-12 for v in allocation.share.values())


def test_the_floor_is_a_floor_and_not_a_quota() -> None:
    """A partition whose deficit already earns it more than the floor gets nothing
    extra. Reserving `n × floor` and splitting the rest would hand it the floor on
    top of its proportional share, which is what "nothing extra" denies."""
    allocation = allocate({"a": 100.0, "b": 1.0, "c": 0.0, "d": 0.0}, FLAT, FOUR, floor=0.05)
    floored = {"b", "c", "d"}
    assert allocation.floored == floored
    assert allocation.share["a"] == pytest.approx(1.0 - 3 * 0.05)
    assert all(allocation.share[p] == pytest.approx(0.05) for p in floored)


def test_a_partition_with_no_deficit_at_all_still_gets_its_floor() -> None:
    """Spending the whole clock on one stubborn deficit means never learning
    anything new about the rich partitions."""
    allocation = allocate({"a": 10.0, "b": 0.0, "c": 0.0, "d": 0.0}, FLAT, FOUR)
    assert allocation.share["b"] == pytest.approx(FLOOR_FRACTION)


def test_the_floor_is_the_re_entry_path_for_a_mispriced_partition() -> None:
    """Share is deficit ÷ price, so a wrong price stops the only service that
    would revise it. Nothing else in the design can reach a partition that is
    never served, which is why this property is load-bearing rather than a
    nicety."""
    deficits = {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0}
    prices = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1_000_000.0}
    allocation = allocate(deficits, prices, FOUR, floor=0.05)
    assert allocation.share["d"] == pytest.approx(0.05)
    assert allocation.bucket("d") == "floor"


def test_price_weighting_is_deficit_over_price() -> None:
    doubled = allocate({"a": 10.0, "b": 10.0}, {"a": 1.0, "b": 2.0}, ["a", "b"], floor=0.0)
    assert doubled.share["a"] == pytest.approx(2 / 3)
    assert doubled.share["b"] == pytest.approx(1 / 3)


def test_every_deficit_zero_spreads_uniformly_and_is_not_called_floor_driven() -> None:
    """A cold start was not decided by the floor, and tagging it floor-driven
    would report the floor binding on a run where it never bound anything."""
    allocation = allocate(dict.fromkeys(FOUR, 0.0), FLAT, FOUR, floor=0.05)
    assert allocation.share == {p: pytest.approx(0.25) for p in FOUR}
    assert allocation.floored == set()


def test_an_infeasible_floor_degrades_to_uniform_and_says_so() -> None:
    """A run that cannot honour the floor should still run — and every partition
    is tagged floored there, because the floor is exactly what could not be
    honoured."""
    allocation = allocate(dict.fromkeys(FOUR, 0.0), FLAT, FOUR, floor=0.5)
    assert sum(allocation.share.values()) == pytest.approx(1.0)
    assert allocation.floored == set(FOUR)


def test_an_externally_supplied_partition_gets_zero_and_keeps_its_key() -> None:
    """An explicit zero reads as `allocated nothing on purpose`; a missing key
    reads as a partition nobody tracked."""
    allocation = allocate({p: 10.0 for p in FOUR}, FLAT, FOUR, floor=0.05, external={"d"})
    assert allocation.share["d"] == 0.0
    assert "d" in allocation.share and allocation.external == {"d"}
    assert sum(allocation.share.values()) == pytest.approx(1.0)
    assert "d" not in allocation.floored, "never pinned up to the floor either"


def test_the_shipped_partition_set_allocates_with_classic_held_out() -> None:
    allocation = allocate(
        dict.fromkeys(ALL_PARTITIONS, 0.0),
        dict.fromkeys(ALL_PARTITIONS, 1.0),
        ALL_PARTITIONS,
        external={CLASSIC_PHOENIX},
    )
    assert allocation.share[CLASSIC_PHOENIX] == 0.0
    assert sum(allocation.share.values()) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# folding a twin's demand
# --------------------------------------------------------------------------- #


def test_an_unservable_twin_folds_its_intent_into_its_parameter_plane() -> None:
    """A `julia:X` partition cannot be walked into existence: serving X is what
    manufactures its supply, so the mix has to be judged on the folded column."""
    intent = {"mandelbrot": 0.2, "julia:mandelbrot": 0.3, "phoenix": 0.5}
    folded = fold_dynamical_intent(
        intent, {"mandelbrot": 5, "julia:mandelbrot": 0, "phoenix": 4}, list(intent)
    )
    assert folded["julia:mandelbrot"] == 0.0
    assert folded["mandelbrot"] == pytest.approx(0.5)
    assert intent["julia:mandelbrot"] == 0.3, "the stated intent is not mutated"


def test_a_twin_with_a_queue_keeps_its_own_intent() -> None:
    intent = {"mandelbrot": 0.2, "julia:mandelbrot": 0.3}
    folded = fold_dynamical_intent(intent, {"mandelbrot": 5, "julia:mandelbrot": 2}, list(intent))
    assert folded == intent


# --------------------------------------------------------------------------- #
# the floor's carry
# --------------------------------------------------------------------------- #


def test_an_unserved_floor_comes_due_at_one_over_the_floor_whatever_a_batch_costs() -> None:
    """The bound is exact and free: for a partition servable throughout and served
    nothing, debt is floor × T and the trigger is T ÷ batches, so both sides scale
    with the same clock and the claim comes due at batch twenty at a 5% floor —
    whether a batch costs six seconds or six minutes."""
    for cost in (0.1, 6.0, 600.0):
        ledger = FloorLedger(floor=0.05)
        realized = {"rich": 0.0, "poor": 0.0}
        due_at = None
        for batch in range(1, 40):
            ledger.settle(["rich", "poor"], cost)
            realized["rich"] += cost
            if ledger.claimants(["rich", "poor"], realized) == ["poor"]:
                due_at = batch
                break
        assert due_at == 20, f"at a batch cost of {cost} minutes"


def test_a_cheap_partition_converges_on_the_same_share_of_the_clock() -> None:
    """The carry is denominated in minutes, not turns. Being cheap buys more
    turns and not more time, which is what "a floor of 5% of the clock" says."""
    ledger = FloorLedger(floor=0.5)
    ledger.settle(["cheap"], 10.0)
    assert ledger.debts({"cheap": 5.0})["cheap"] == pytest.approx(0.0)
    assert ledger.debts({"cheap": 1.0})["cheap"] == pytest.approx(4.0)


def test_entitlement_accrues_only_over_minutes_a_partition_was_servable() -> None:
    """Otherwise a partition nobody could feed banks a claim while it waits and
    spends it in a burst the moment its queue refills — the run pays hours of
    arrears at once to a partition it could not have served for any of them."""
    ledger = FloorLedger(floor=0.05)
    for _ in range(10):
        ledger.settle(["awake"], 1.0)
    assert ledger.entitled().get("asleep") is None
    assert ledger.debts({})["awake"] == pytest.approx(0.5)


def test_an_externally_supplied_partition_banks_no_claim() -> None:
    ledger = FloorLedger(floor=0.05, external={"outside"})
    ledger.settle(["inside", "outside"], 10.0)
    assert "outside" not in ledger.entitled()
    assert ledger.unspent({}, ["inside", "outside"])["per_partition"].keys() == {"inside"}


def test_a_debt_is_a_claim_and_never_a_negative_balance() -> None:
    ledger = FloorLedger(floor=0.05)
    ledger.settle(["heavy"], 10.0)
    assert ledger.debts({"heavy": 100.0})["heavy"] == 0.0


def test_floor_never_needed_and_starved_are_reported_as_different_states() -> None:
    """Conflating them once made a working allocator read as broken. One partition
    was above its floor the whole time and had nothing to spend; the other could
    not be fed at all."""
    ledger = FloorLedger(floor=0.05)
    for _ in range(10):
        ledger.settle(["served"], 1.0)
    report = ledger.unspent({"served": 10.0}, ["served", "nothing_feeds_it"])
    assert report["per_partition"]["served"]["state"] == "spent"
    assert report["per_partition"]["nothing_feeds_it"]["state"] == "starved"
    assert report["starved"] == ["nothing_feeds_it"]
    assert report["alarms"] == [], "starved is not an unspent-floor alarm"


def test_a_partition_the_rule_declined_to_serve_raises_the_alarm() -> None:
    ledger = FloorLedger(floor=0.05)
    for _ in range(10):
        ledger.settle(["served", "ignored"], 1.0)
    report = ledger.unspent({"served": 10.0}, ["served", "ignored"])
    assert report["alarms"] == ["ignored"]
    assert report["per_partition"]["ignored"]["servable_minutes"] == pytest.approx(10.0)


def test_the_carry_is_disabled_before_the_first_charge() -> None:
    """There is no measured batch cost yet, and the share rule already opens
    correctly by serving the largest intent."""
    ledger = FloorLedger(floor=0.05)
    assert ledger.trigger() == 0.0
    assert ledger.claimants(["a"], {}) == []


# --------------------------------------------------------------------------- #
# dividing a batch
# --------------------------------------------------------------------------- #


def test_one_slot_is_exactly_serve_the_partition_furthest_below_its_intent() -> None:
    """The generalization has to reduce to the rule it generalizes, or the quota
    at a batch of one is a different quota."""
    intent = {"a": 0.5, "b": 0.3, "c": 0.2}
    realized = {"a": 10.0, "b": 0.0, "c": 0.0}
    queues = {"a": 5, "b": 5, "c": 5}
    gaps = share_gaps(intent, realized, queues)
    slots, _ = batch_slots(intent, realized, queues, 1)
    assert [p for p, n in slots.items() if n] == [max(gaps, key=lambda p: (gaps[p], p))]


def test_before_any_time_is_spent_the_first_slot_goes_to_the_largest_intent() -> None:
    """Which is correct, and is why there is no special case for it."""
    slots, _ = batch_slots({"a": 0.5, "b": 0.3}, {}, {"a": 5, "b": 5}, 1)
    assert slots == {"a": 1, "b": 0}


def test_bare_apportionment_at_a_small_batch_structurally_zeroes_partitions() -> None:
    """The control the guarantee exists for: at eight slots over ten partitions
    the smallest ratio is zeroed whatever its supply, every time."""
    weights = dict.fromkeys(ALL_PARTITIONS, 1.0) | {CLASSIC_PHOENIX: 0.2}
    bare = allocate_slots(weights, 8, caps=dict.fromkeys(ALL_PARTITIONS, 10))
    assert bare[CLASSIC_PHOENIX] == 0
    assert sum(bare.values()) == 8


def test_a_guaranteed_partition_is_seated_and_the_remainder_is_apportioned() -> None:
    weights = dict.fromkeys(ALL_PARTITIONS, 1.0) | {CLASSIC_PHOENIX: 0.2}
    caps = dict.fromkeys(ALL_PARTITIONS, 10)
    guaranteed = allocate_slots(weights, 8, caps=caps, guaranteed=[CLASSIC_PHOENIX])
    assert guaranteed[CLASSIC_PHOENIX] == 1
    assert sum(guaranteed.values()) == 8


def test_a_guarantee_is_a_floor_and_not_a_bonus() -> None:
    """A partition the rule already seats gains nothing from being named. The
    naive form — reserve, then apportion the rest — gives it its reservation on
    top of its natural share."""
    weights = {"a": 5.0, "b": 1.0}
    caps = {"a": 10, "b": 10}
    without = allocate_slots(weights, 6, caps=caps)
    with_it = allocate_slots(weights, 6, caps=caps, guaranteed=["a"])
    assert without == with_it


def test_more_guarantees_than_slots_is_refused_rather_than_shared_out() -> None:
    """A pro-rated guarantee is not a guarantee."""
    with pytest.raises(SlotGuaranteeOverflow):
        allocate_slots(FLAT, 2, caps=dict.fromkeys(FOUR, 5), guaranteed=FOUR)


def test_a_partition_cannot_be_given_more_slots_than_it_has_nodes() -> None:
    slots = allocate_slots({"a": 10.0, "b": 1.0}, 6, caps={"a": 2, "b": 10})
    assert slots["a"] == 2
    assert slots["a"] + slots["b"] == 6


def test_a_capped_partition_is_excluded_but_keeps_its_intent() -> None:
    slots, trace = batch_slots({"a": 0.9, "b": 0.1}, {}, {"a": 5, "b": 5}, 4, capped=["a"])
    assert slots.get("a", 0) == 0
    assert slots["b"] == 4
    assert trace["capped"] == ["a"]


def test_a_floor_claim_takes_a_slot_the_share_rule_would_not_have_given() -> None:
    """The carry's preemption, in slot form. A claim re-offered rather than
    accumulated is a claim that never comes due."""
    queues = dict.fromkeys(FOUR, 5)
    without, _ = batch_slots(FLAT, {}, queues, 2)
    assert without["a"] == 0, "four equal claims and two slots: two get nothing"
    with_claim, trace = batch_slots(FLAT, {}, queues, 2, claimants=["a"])
    assert with_claim["a"] == 1
    assert sum(with_claim.values()) == 2
    assert trace["guaranteed"] == ["a"]


def test_the_most_owed_claim_is_served_first() -> None:
    """The ordering is the ledger's, so who waits when there are more claims than
    slots is a fact about the debts rather than about the alphabet."""
    ledger = FloorLedger(floor=0.05)
    for _ in range(60):
        ledger.settle(["a", "b"], 1.0)
    assert ledger.claimants(["a", "b"], {"a": 1.0, "b": 0.0}) == ["b", "a"]


def test_claims_beyond_the_batch_size_wait_and_are_named() -> None:
    """Nothing is silently pro-rated: the ones that wait are reported, so a run
    that is systematically short of slots is visible rather than merely slow."""
    queues = dict.fromkeys(FOUR, 5)
    slots, trace = batch_slots(FLAT, {}, queues, 2, claimants=FOUR)
    assert sum(slots.values()) == 2
    assert trace["deferred_claims"] == ["c", "d"]


def test_slots_follow_the_intent_when_every_gap_has_closed() -> None:
    """There is no gap to rank by, so the slots follow what the gaps would say the
    moment one opened."""
    intent = {"a": 0.75, "b": 0.25}
    realized = {"a": 75.0, "b": 25.0}
    slots, trace = batch_slots(intent, realized, {"a": 9, "b": 9}, 4)
    assert trace["weight_source"] == "intent"
    assert slots == {"a": 3, "b": 1}


def test_the_sequence_holds_every_prefix_near_its_share() -> None:
    """The property that survives a budget that stops early, which is the normal
    case. A check on the order actually built, never a theorem about the rule."""
    weights = {"a": 43.0, "b": 36.0, "c": 290.0, "d": 48.0, "e": 98.0}
    order = sequence_by_deficit(weights, sum(int(v) for v in weights.values()))
    assert prefix_deviation(order, weights) < 1.0
