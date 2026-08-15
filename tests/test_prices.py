"""The price: a ratio of two averages, a band around a measured seed.

Two of these tests are regressions against a design that looks obviously right and
is not — deferring a fruitless batch until yield arrives — and the failure it
produces is a partition that can never be served again, which is invisible in
every summary the run writes.
"""

from __future__ import annotations

import json
import math

import pytest

from fractal_wallpapers.supply import prices
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX

PAIR = ["a", "b"]


def model(**config) -> prices.CostToFind:
    return prices.CostToFind(PAIR, {"prices": {"a": 1.0, "b": 1.0}, **config})


# --------------------------------------------------------------------------- #
# the estimate
# --------------------------------------------------------------------------- #


def test_the_estimate_starts_at_exactly_the_seed() -> None:
    """The seed is a price, and the pair (seed × units, units) is how much
    evidence it is being given."""
    cost = model()
    assert cost.price("a") == pytest.approx(1.0)
    assert cost.ema_units["a"] == pytest.approx(prices.PRICE_SEED_UNITS)


def test_a_served_batch_moves_the_estimate_toward_what_it_measured() -> None:
    cost = model(price_ema=0.5)
    cost.charge("a", 4.0)
    cost.credit("a", 1.0)
    sample = cost.end_window()
    assert sample["a"] == pytest.approx(4.0), "the window's own rate"
    assert cost.raw["a"] == pytest.approx((0.5 * 1.0 + 0.5 * 4.0) / (0.5 * 1.0 + 0.5 * 1.0))


def test_a_fruitless_batch_prices_itself_instead_of_deferring_its_minutes() -> None:
    """The deferred design charges a partition's cost to a moment rather than to
    the batches that incurred it: two fruitless batches land on whatever closes
    next, against that one batch's single unit."""
    cost = model(price_ema=0.5)
    before = cost.price("a")
    cost.charge("a", 4.0)
    sample = cost.end_window()
    assert sample["a"] is None, "a fruitless window has no rate, and still moved the price"
    assert cost.price("a") > before
    assert cost.window_minutes["a"] == 0.0, "nothing was carried forward"


def test_sustained_fruitless_service_raises_the_price_without_running_away() -> None:
    """Direction is deliberate: sustained fruitless service should raise a price.
    The defect was a frozen price and evidence held hostage to a credit that never
    came, never a high price."""
    cost = model()
    seen = []
    for _ in range(40):
        cost.charge("a", 1.0)
        cost.end_window()
        seen.append(cost.price("a"))
    assert seen == sorted(seen), "monotone up"
    assert seen[-1] == pytest.approx(cost.seed["a"] * cost.clamp), "and bounded by the band"


def test_a_window_with_units_but_no_minutes_does_not_close() -> None:
    """A zero numerator would price the partition as free, which is the one
    direction the allocator amplifies."""
    cost = model()
    cost.credit("a", 5.0)
    assert cost.end_window() == {}
    assert cost.window_units["a"] == pytest.approx(5.0), "the units wait for their minutes"


def test_the_sample_weight_is_a_stated_function_rather_than_an_emergent_one() -> None:
    weight = prices.CostToFind.sample_weight
    assert weight(0.15, 0.0, 1.0) == 0.0
    assert weight(0.15, 1.0, 1.0) == pytest.approx(0.15), "parity pulls at exactly the rate"
    assert weight(0.15, 10.0, 1.0) > weight(0.15, 1.0, 1.0), "monotone in units"
    assert 0.0 <= weight(0.15, 1e9, 1.0) < 1.0


def test_the_estimate_stays_inside_its_band_and_the_raw_value_is_kept() -> None:
    """The clamp is visible rather than silent: a run at the band edge is quoting
    the band instead of its own measurement, and that has to be readable."""
    cost = model(price_clamp=2.0, price_ema=1.0)
    cost.charge("a", 100.0)
    cost.credit("a", 1.0)
    cost.end_window()
    assert cost.raw["a"] > 2.0
    assert cost.price("a") == pytest.approx(2.0)
    assert cost.summary()["clamped"] == ["a"]


# --------------------------------------------------------------------------- #
# the dry clock
# --------------------------------------------------------------------------- #


def test_a_partition_that_burns_the_cap_without_a_credit_is_capped() -> None:
    cost = model(cap_minutes=5.0)
    assert cost.charge("a", 4.0) is False
    assert cost.charge("a", 2.0) is True
    assert "a" in cost.capped


def test_a_credit_reopens_a_capped_partition_and_a_non_credit_does_not() -> None:
    """A partition producing nothing but refusals must still cap, so zero units is
    not a credit."""
    cost = model(cap_minutes=5.0)
    cost.charge("a", 6.0)
    cost.credit("a", 0.0)
    assert "a" in cost.capped
    cost.credit("a", 0.1)
    assert cost.capped == set()


# --------------------------------------------------------------------------- #
# the shipped tables
# --------------------------------------------------------------------------- #


def test_the_shipped_seed_covers_the_partition_registry() -> None:
    assert set(prices.load_table()["prices"]) == set(ALL_PARTITIONS)


def test_the_shipped_seed_table_is_what_the_regularizer_produces() -> None:
    """A shipped table has to be reproducible from its own evidence, or the next
    person to touch it cannot tell a derivation from a hand edit."""
    measured = prices.load_table(prices.measured_table_path())
    derived = prices.regularize(measured, source="data/supply/cost_to_find_measured.json")
    shipped = prices.load_table()
    assert derived["prices"] == shipped["prices"]
    assert derived["price_clamp"] == shipped["price_clamp"]
    assert (
        derived["_provenance"]["shrink_target_value"]
        == shipped["_provenance"]["shrink_target_value"]
    )


def test_the_measured_table_is_what_the_deriver_produces_from_its_own_telemetry() -> None:
    shipped = prices.load_table(prices.measured_table_path())
    provenance = shipped["_provenance"]
    block = {
        "minutes_spent": provenance["minutes"],
        "units_found": provenance["units"],
    }
    derived = prices.derive([block], provenance["source_runs"], ALL_PARTITIONS)
    assert derived["prices"] == shipped["prices"]
    assert derived["_provenance"]["defaulted"] == provenance["defaulted"]
    assert derived["price_ema"] == prices.PRICE_EMA, "written at derivation time, not edited in"


def test_the_seed_table_round_trips_through_its_real_consumer() -> None:
    """Through the price model rather than through a second parser, so the file
    and the thing that reads it cannot drift."""
    table = prices.load_table()
    cost = prices.CostToFind(ALL_PARTITIONS, table)
    assert cost.prices() == pytest.approx(table["prices"])
    assert cost.clamp == table["price_clamp"]
    assert cost.ema == table["price_ema"]


def test_an_externally_supplied_partition_carries_a_stated_absence() -> None:
    """No walk ever serves it, so no walk can ever price it. The row is a
    permanent stated absence rather than a measurement waiting to arrive."""
    measured = prices.load_table(prices.measured_table_path())
    assert CLASSIC_PHOENIX in measured["_provenance"]["defaulted"]
    assert measured["prices"][CLASSIC_PHOENIX] == prices.SEED_PRICE


# --------------------------------------------------------------------------- #
# the shrinkage
# --------------------------------------------------------------------------- #


def test_shrinkage_keeps_the_measured_order_and_multiplies_every_log_ratio() -> None:
    """A tenfold signal survives as a fivefold one instead of being flattened to a
    bound — the whole reason this is shrinkage and not a clamp."""
    table = {
        "prices": {"cheap": 0.1, "middle": 1.0, "dear": 10.0},
        "_provenance": {"defaulted": []},
    }
    out = prices.regularize(table, alpha=0.5)["prices"]
    assert out["cheap"] < out["middle"] < out["dear"]
    assert out["middle"] == pytest.approx(1.0), "a partition at the median is unchanged"
    exact_low = prices.shrink(0.1, 1.0, 0.5)
    exact_high = prices.shrink(10.0, 1.0, 0.5)
    assert math.log(exact_high / exact_low) == pytest.approx(0.5 * math.log(10.0 / 0.1))
    assert prices.spread(out.values()) == pytest.approx(
        prices.spread([0.1, 10.0]) ** 0.5, rel=1e-3
    ), "the table's whole spread goes from S to S**alpha"


def test_a_defaulted_row_is_not_shrunk_and_does_not_set_the_median() -> None:
    """Shrinking it would manufacture a price for a partition nobody priced, and
    letting it into the median would drag the target toward the flat seed by
    however many partitions went unserved."""
    table = {
        "prices": {"measured": 0.2, "never_served": prices.SEED_PRICE},
        "_provenance": {"defaulted": ["never_served"]},
    }
    out = prices.regularize(table, alpha=0.5)
    assert out["prices"]["never_served"] == prices.SEED_PRICE
    assert out["_provenance"]["shrink_target_value"] == pytest.approx(0.2)


def test_a_table_with_no_measured_row_is_refused() -> None:
    """A flat table wearing a derived name reports itself as a measurement it is
    not, and afterwards the two are indistinguishable."""
    with pytest.raises(prices.PriceTableError):
        prices.regularize(
            {"prices": {"a": 3.0}, "_provenance": {"defaulted": ["a"]}},
        )


def test_a_partition_below_the_evidence_floor_is_defaulted_and_stamped() -> None:
    """Minutes over zero units is not a large price, it is no measurement — and
    writing the row out of the table would make "never served" indistinguishable
    from "never tracked"."""
    block = {"minutes_spent": {"a": 12.0, "b": 5.0}, "units_found": {"a": 0.1, "b": 20.0}}
    derived = prices.derive([block], ["test"], PAIR)
    assert derived["prices"]["a"] == prices.SEED_PRICE
    assert derived["_provenance"]["defaulted"] == ["a"]
    assert derived["_provenance"]["thin"] == ["a"], "served and productive, just not enough"
    assert derived["_provenance"]["price_raw"]["a"] == pytest.approx(120.0)


def test_pooling_sums_both_accumulators_and_divides_once() -> None:
    """Averaging two runs' live estimates would weight a run by how many windows
    it happened to flush rather than by how much work it did."""
    blocks = [
        {"minutes_spent": {"a": 10.0}, "units_found": {"a": 100.0}},
        {"minutes_spent": {"a": 90.0}, "units_found": {"a": 100.0}},
    ]
    derived = prices.derive(blocks, ["one", "two"], ["a"])
    assert derived["prices"]["a"] == pytest.approx(0.5)


def test_a_missing_table_names_the_command_that_makes_one(tmp_path) -> None:
    with pytest.raises(prices.PriceTableError, match="derive-prices"):
        prices.load_table(tmp_path / "absent.json")


def test_a_table_of_the_wrong_schema_is_refused(tmp_path) -> None:
    path = tmp_path / "table.json"
    path.write_text(json.dumps({"schema": 99, "prices": {"a": 1.0}}), encoding="utf-8")
    with pytest.raises(prices.PriceTableError, match="schema"):
        prices.load_table(path)
