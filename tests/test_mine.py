"""The mine: where the primed boundary is read, how the three arms draw, what the clock says.

Everything here is arithmetic over records, like [`test_hunt`] and for the same
reason: away from the two seconds a render takes, the module is draws over tables
and tallies over rows. So there is a fake ledger, a fake scan index and a fake
head sidecar, and never a picture.

The two properties worth pinning hardest are the ones a readout would be wrong
without. **PRIMED is derived**: no row carries it, [`mine.primed`] takes the bar
as an argument, and the same rows read at two bars give two answers. **The two
breadth arms differ only in the draw**: they are matched on partition by
construction, they never share a location, and the ranked one orders on the
location head within a partition and never across one — a pooled sort would
compare heights that are not on one scale, and a comparison of a mine's arms
built on that would be a comparison of nothing.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import mine

# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
PARTITIONS = ("mandelbrot", "phoenix", "julia:mandelbrot")


def ledger_row(key, location, partition="mandelbrot", mode="smooth", colormap="viridis"):
    """One ledger row, thinned to the members a mine reads off it."""
    return {
        "schema": 1,
        "key": key,
        "recipe_key": key,
        "partition": partition,
        "location": {"key": location},
        "recipe": {"mode": mode, "colormap": colormap},
    }


def made_row(arm, location, p_ge4, *, k=1, band="near", partition="mandelbrot", seconds=1.0):
    """One row of what a mine made, as [`mine.arm_readout`] reads it."""
    return {
        "key": f"{arm}-{location}-{k}",
        "arm": arm,
        "band": band,
        "k": k,
        "location": location,
        "partition": partition,
        "mode": "smooth",
        "mode_kind": "field",
        "colormap": "viridis",
        "palette_group": "map:viridis",
        "p_ge4": p_ge4,
        "p_ge3": min(1.0, p_ge4 + 0.05),
        "seconds": seconds,
        "acted": False,
        "cells": [],
    }


def pools(counts):
    """`{partition: [places]}` at the given depths, keys unique across partitions."""
    return {
        name: [{"key": f"{name}-{at}", "partition": name} for at in range(count)]
        for name, count in counts.items()
    }


# --------------------------------------------------------------------------- #
# The boundary is derived, and takes its height as an argument.
# --------------------------------------------------------------------------- #
def test_primed_is_a_function_of_the_bar_and_not_of_a_stored_flag():
    readings = [0.10, 0.62, 0.88]
    assert mine.primed(readings, bar=0.50)
    assert not mine.primed(readings, bar=0.90)


def test_a_location_with_no_candidate_is_not_primed_at_any_bar():
    assert not mine.primed([], bar=0.0)


def test_best_by_location_keeps_the_mode_the_best_candidate_was_drawn_in():
    rows = [
        ledger_row("a", "place-1", mode="smooth"),
        ledger_row("b", "place-1", mode="threads"),
        ledger_row("c", "place-2", mode="itinerary"),
    ]
    best = mine.best_by_location(rows, {"a": 0.2, "b": 0.91, "c": 0.4})
    assert best["place-1"]["best"] == pytest.approx(0.91)
    assert best["place-1"]["best_mode"] == "threads"
    assert best["place-1"]["count"] == 2
    assert best["place-2"]["best_mode"] == "itinerary"


def test_a_location_whose_candidates_are_all_unscored_still_carries_a_mode():
    """A missing score reads as zero, and the location is still drawable by DEEPEN."""
    best = mine.best_by_location([ledger_row("a", "place-1", mode="tia")], {})
    assert best["place-1"]["best"] == pytest.approx(0.0)
    assert best["place-1"]["best_mode"] == "tia"


def test_taken_maps_is_keyed_by_location_and_mode_together():
    rows = [
        ledger_row("a", "place-1", mode="smooth", colormap="viridis"),
        ledger_row("b", "place-1", mode="threads", colormap="magma"),
    ]
    taken = mine.taken_maps(rows)
    assert taken[("place-1", "smooth")] == {"viridis"}
    assert taken[("place-1", "threads")] == {"magma"}


# --------------------------------------------------------------------------- #
# The DEEPEN draw.
# --------------------------------------------------------------------------- #
def test_deepen_offers_no_map_the_place_already_carries_in_that_mode():
    places = [{"key": "place-1", "partition": "mandelbrot", "best_mode": "smooth"}]
    taken = {("place-1", "smooth"): {"viridis", "magma"}}
    units = mine.plan_deepen(places, taken, ["viridis", "magma", "cividis"], 7, 3, "near")
    assert [unit.colormap for unit in units] == ["cividis"]
    assert units[0].k == 1


def test_deepen_holds_the_mode_and_numbers_the_palettes_from_one():
    places = [{"key": "place-1", "partition": "phoenix", "best_mode": "threads"}]
    units = mine.plan_deepen(places, {}, list("abcdef"), 7, 4, "over")
    assert {unit.mode for unit in units} == {"threads"}
    assert [unit.k for unit in units] == [1, 2, 3, 4]
    assert len({unit.colormap for unit in units}) == 4
    assert {unit.band for unit in units} == {"over"}


def test_deepen_skips_a_place_whose_best_candidate_names_no_mode():
    places = [{"key": "place-1", "partition": "mandelbrot", "best_mode": None}]
    assert mine.plan_deepen(places, {}, list("abc"), 7, 3, "near") == []


def test_deepen_draws_only_inside_its_band_and_only_where_a_frame_is_known():
    best = {
        "in-band": {"best": 0.7, "partition": "mandelbrot", "best_mode": "smooth", "count": 1},
        "over-band": {"best": 0.95, "partition": "mandelbrot", "best_mode": "smooth", "count": 1},
        "no-frame": {"best": 0.7, "partition": "phoenix", "best_mode": "smooth", "count": 1},
    }
    index = {"in-band": {}, "over-band": {}}
    drawn = mine.deepen_places(best, index, mine.NEAR_BAND, seed=3, count=10)
    assert [row["key"] for row in drawn] == ["in-band"]


# --------------------------------------------------------------------------- #
# The two breadth arms differ in the draw and in nothing else.
# --------------------------------------------------------------------------- #
def test_ranked_orders_on_the_head_inside_a_partition_and_never_across_one():
    held = pools({"mandelbrot": 3, "phoenix": 3})
    head = {
        "mandelbrot-0": {"p_ge3": 0.1},
        "mandelbrot-1": {"p_ge3": 0.9},
        "mandelbrot-2": {"p_ge3": 0.5},
        "phoenix-0": {"p_ge3": 0.2},
        "phoenix-1": {"p_ge3": 0.8},
        "phoenix-2": {"p_ge3": 0.4},
    }
    drawn = [row["key"] for row in mine.ranked_places(held, head, seed=1, count=4)]
    # Round-robin over partitions, best-first inside each: a pooled sort would
    # have taken mandelbrot-1, phoenix-1, mandelbrot-2 in that order and left
    # the second partition's turn to the third round.
    assert drawn == ["mandelbrot-1", "phoenix-1", "mandelbrot-2", "phoenix-2"]


def test_a_location_the_head_cannot_score_sorts_last_rather_than_being_dropped():
    held = pools({"mandelbrot": 2})
    drawn = mine.ranked_places(held, {"mandelbrot-1": {"p_ge3": 0.3}}, seed=1, count=2)
    assert [row["key"] for row in drawn] == ["mandelbrot-1", "mandelbrot-0"]


def test_flat_takes_exactly_the_per_partition_counts_it_is_matched_to():
    held = pools({"mandelbrot": 20, "phoenix": 20, "julia:mandelbrot": 20})
    drawn = mine.flat_places(held, seed=5, want={"mandelbrot": 4, "phoenix": 2})
    counts = {name: 0 for name in PARTITIONS}
    for row in drawn:
        counts[row["partition"]] += 1
    assert counts == {"mandelbrot": 4, "phoenix": 2, "julia:mandelbrot": 0}


def test_a_partition_that_cannot_fill_its_quota_leaves_the_shortfall_rather_than_borrowing():
    held = pools({"mandelbrot": 1, "phoenix": 9})
    drawn = mine.flat_places(held, seed=5, want={"mandelbrot": 4, "phoenix": 4})
    assert sum(1 for row in drawn if row["partition"] == "mandelbrot") == 1
    assert sum(1 for row in drawn if row["partition"] == "phoenix") == 4


class Wheel:
    """[`hunt.Stratifier`] without the carrier table: the maps in turn, one cell.

    The real one asks `palettes.carriers` which maps make a codebook cell, which
    is a tracked table and a slow read. What this test is about is that the two
    breadth arms are offered the same sequence, and any deterministic wheel shows
    that.
    """

    def __init__(self, _cells, pool, _seed):
        self.pool = list(pool)
        self.at = 0

    def next(self):
        name = self.pool[self.at % len(self.pool)]
        self.at += 1
        return "dark_vivid_lime", name


def test_both_breadth_arms_are_offered_the_same_modes_and_colours_at_a_shared_key(monkeypatch):
    """The arms are the built path with the draw swapped, so the draw is all that differs."""
    monkeypatch.setattr(mine.hunt, "Stratifier", Wheel)
    maps = [f"map{at}" for at in range(40)]
    one = mine.plan_breadth(mine.RANKED, pools({"mandelbrot": 2})["mandelbrot"], maps, 11, 3)
    other = mine.plan_breadth(mine.FLAT, pools({"mandelbrot": 2})["mandelbrot"], maps, 11, 3)
    assert len(one) == 6
    assert [(u.location, u.mode, u.colormap, u.k) for u in one] == [
        (u.location, u.mode, u.colormap, u.k) for u in other
    ]
    assert {u.arm for u in one} == {mine.RANKED}
    assert {u.arm for u in other} == {mine.FLAT}


# --------------------------------------------------------------------------- #
# The weave: every prefix holds the arms in proportion.
# --------------------------------------------------------------------------- #
def test_every_prefix_of_the_woven_plan_holds_the_arms_in_their_shares():
    plans = {arm: [made_row(arm, f"{arm}-{at}", 0.0) for at in range(400)] for arm in mine.ARMS}
    woven = mine.weave({arm: rows for arm, rows in plans.items()})
    assert len(woven) == 1200
    for cut in (120, 400, 800):
        prefix = woven[:cut]
        for arm, share in mine.SHARES.items():
            seen = sum(1 for row in prefix if row["arm"] == arm) / cut
            assert seen == pytest.approx(share, abs=0.02), (arm, cut, seen)


def test_an_arm_with_nothing_planned_does_not_break_the_weave():
    woven = mine.weave({mine.DEEPEN: [1, 2, 3], mine.RANKED: [], mine.FLAT: []})
    assert woven == [1, 2, 3]


# --------------------------------------------------------------------------- #
# The stopwatch.
# --------------------------------------------------------------------------- #
def test_the_stages_of_one_candidate_sum_to_its_seconds():
    stages = mine.Stages(render=1.5, judge=0.25, colour=0.1, write=0.01, overhead=0.04)
    assert stages.total() == pytest.approx(1.9)
    assert sum(stages.named().values()) == pytest.approx(1.9)


def test_the_clock_attributes_the_same_seconds_to_every_cut_it_is_given():
    clock = mine.Clock()
    clock.add(mine.Stages(render=2.0, judge=0.5), {"arm": "deepen", "partition": "phoenix"})
    clock.add(mine.Stages(render=1.0, judge=0.5), {"arm": "deepen", "partition": "mandelbrot"})
    table = clock.table()
    assert table["total_seconds"] == pytest.approx(4.0)
    assert table["by_stage"]["render"]["share"] == pytest.approx(0.75)
    assert table["by_cut"]["arm=deepen"]["candidates"] == 2
    assert table["by_cut"]["arm=deepen"]["seconds"] == pytest.approx(4.0)
    assert table["by_cut"]["partition=phoenix"]["per_candidate"] == pytest.approx(2.5)


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def test_one_set_of_rows_reads_out_at_two_bars_with_two_answers():
    made = [
        made_row(mine.RANKED, "place-1", 0.95),
        made_row(mine.RANKED, "place-2", 0.62),
        made_row(mine.RANKED, "place-3", 0.01),
    ]
    block = mine.arm_readout(made)[mine.RANKED]
    assert block["bar_090"]["locations_primed"] == 1
    assert block["bar_050"]["locations_primed"] == 2
    assert block["locations"] == 3


def test_a_deepen_arm_cannot_claim_a_place_that_was_already_over_the_bar():
    made = [made_row(mine.DEEPEN, "place-1", 0.97, k=1)]
    world = {"best": {"place-1": {"best": 0.99, "partition": "mandelbrot"}}}
    block = mine.arm_readout(made, world)[mine.DEEPEN]
    assert block["bar_090"]["locations_primed"] == 1
    assert block["bar_090"]["locations_newly_primed"] == 0


def test_a_deepen_arm_claims_a_place_its_own_candidate_converted():
    made = [made_row(mine.DEEPEN, "place-1", 0.97, k=2)]
    world = {"best": {"place-1": {"best": 0.61, "partition": "mandelbrot"}}}
    block = mine.arm_readout(made, world)[mine.DEEPEN]
    assert block["bar_090"]["locations_newly_primed"] == 1


def test_seconds_per_primed_is_none_rather_than_a_division_by_zero():
    made = [made_row(mine.FLAT, "place-1", 0.02)]
    block = mine.arm_readout(made)[mine.FLAT]
    assert block["bar_090"]["locations_primed"] == 0
    assert block["bar_090"]["seconds_per_primed"] is None
    assert block["bar_090"]["candidates_per_primed"] is None


def test_the_marginal_curve_is_cumulative_over_k_and_never_falls():
    made = [
        made_row(mine.DEEPEN, "place-1", 0.1, k=1),
        made_row(mine.DEEPEN, "place-1", 0.95, k=2),
        made_row(mine.DEEPEN, "place-1", 0.2, k=3),
        made_row(mine.DEEPEN, "place-2", 0.3, k=1),
        made_row(mine.DEEPEN, "place-2", 0.4, k=2),
        made_row(mine.DEEPEN, "place-2", 0.99, k=3),
    ]
    curve = mine.marginal(made)["near"]["bar_090"]
    assert [row["cumulative_primed"] for row in curve] == [0, 1, 2]
    assert [row["marginal_gain"] for row in curve] == [0.0, 0.5, 0.5]
    assert [row["cleared_at_k"] for row in curve] == [0, 1, 1]
    assert all(row["candidates_at_k"] == 2 for row in curve)


def test_the_two_deepen_bands_are_reported_apart():
    made = [
        made_row(mine.DEEPEN, "near-1", 0.95, k=1, band="near"),
        made_row(mine.DEEPEN, "over-1", 0.10, k=1, band="over"),
    ]
    curves = mine.marginal(made)
    assert curves["near"]["bar_090"][0]["cumulative_primed"] == 1
    assert curves["over"]["bar_090"][0]["cumulative_primed"] == 0


# --------------------------------------------------------------------------- #
# Ranked against flat, and where a route runs out.
# --------------------------------------------------------------------------- #
def arm_rows(arm, primed_by_partition, plain_by_partition):
    """One location a count, primed where asked and not otherwise."""
    rows = []
    for name in sorted(set(primed_by_partition) | set(plain_by_partition)):
        for at in range(primed_by_partition.get(name, 0)):
            rows.append(made_row(arm, f"{arm}-{name}-hit{at}", 0.97, partition=name))
        for at in range(plain_by_partition.get(name, 0)):
            rows.append(made_row(arm, f"{arm}-{name}-miss{at}", 0.01, partition=name))
    return rows


def test_the_stratified_difference_ignores_a_partition_only_one_arm_reached():
    """A stratum with no control contributes no weight, rather than a pooled artefact."""
    made = arm_rows(mine.RANKED, {"mandelbrot": 5, "phoenix": 9}, {"mandelbrot": 5})
    made += arm_rows(mine.FLAT, {"mandelbrot": 2}, {"mandelbrot": 8})
    block = mine.compare(made, bars=(0.90,), draws=200)["bar_090"]
    assert block["by_partition"]["mandelbrot"]["difference"] == pytest.approx(0.30)
    assert block["by_partition"]["phoenix"]["difference"] is None
    assert block["stratified_difference"] == pytest.approx(0.30)
    # Pooled counts phoenix's nine unmatched hits and says 0.54 — 14 of 19 ranked
    # against 2 of 10 flat — which is the partitions' difference, not the arms'.
    assert block["pooled"]["difference"] == pytest.approx(0.5368, abs=1e-3)


def test_the_bootstrap_interval_covers_zero_when_the_arms_agree():
    made = arm_rows(mine.RANKED, {"mandelbrot": 5}, {"mandelbrot": 5})
    made += arm_rows(mine.FLAT, {"mandelbrot": 5}, {"mandelbrot": 5})
    block = mine.compare(made, bars=(0.90,), draws=1000)["bar_090"]
    assert block["stratified_difference"] == pytest.approx(0.0)
    assert block["ci95"]["low"] < 0.0 < block["ci95"]["high"]
    assert block["ci95"]["excludes_zero"] is False


def test_the_bootstrap_interval_clears_zero_on_a_wide_separation():
    made = arm_rows(mine.RANKED, {"mandelbrot": 40, "phoenix": 40}, {})
    made += arm_rows(mine.FLAT, {}, {"mandelbrot": 40, "phoenix": 40})
    block = mine.compare(made, bars=(0.90,), draws=1000)["bar_090"]
    assert block["stratified_difference"] == pytest.approx(1.0)
    assert block["ci95"]["excludes_zero"] is True


def test_a_route_whose_stock_is_too_small_is_reported_as_not_reaching_the_target():
    arms = mine.arm_readout(arm_rows(mine.RANKED, {"mandelbrot": 1}, {"mandelbrot": 9}))
    out = mine.extrapolate(arms, {mine.RANKED: 500, "owned_primed": 12}, target=1000)
    assert out[mine.RANKED]["primed_per_location"] == pytest.approx(0.1)
    assert out[mine.RANKED]["primed_the_stock_can_reach"] == 50
    assert out[mine.RANKED]["reaches_target"] is False
    assert out["already_owned"] == 12


def test_hours_to_target_is_seconds_a_location_over_primed_a_location():
    made = arm_rows(mine.RANKED, {"mandelbrot": 1}, {"mandelbrot": 9})
    for row in made:
        row["seconds"] = 3.6
    arms = mine.arm_readout(made)
    out = mine.extrapolate(arms, {mine.RANKED: 100_000}, target=1000)
    # Ten locations at 3.6 s each prime one, so a thousand cost 36,000 s.
    assert out[mine.RANKED]["hours_to_target"] == pytest.approx(10.0)
    assert out[mine.RANKED]["reaches_target"] is True
