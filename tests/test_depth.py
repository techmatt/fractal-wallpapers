"""The depth run: how the rank range is cut, how width is spent, and what the curves say.

Arithmetic over records, like [`test_mine`] and for its reason: away from the
render, this module is draws over tables and curves over rows. There is a fake
pool, a fake head sidecar and a fake sequence, and never a picture.

The properties worth pinning hardest are the ones a wrong readout would hide.
**The rank bands span the whole pool**, top to bottom and in equal counts, which
is the difference between this and the two earlier passes that took the top of
the list. **A location out of the denominator is not a failure**: a run stopped
by its budget must not report every curve bending down at the width it stopped
at. And **the modes are cycled and not blocked**, because a location given seven
of one mode and then seven of another would move its own clear rate with `k` for
a reason that is not depth.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import depth

PARTITIONS = ("mandelbrot", "phoenix", "julia:mandelbrot")


# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
def pools(counts):
    """`{partition: [places]}`, keys unique across partitions."""
    return {
        name: [{"key": f"{name}-{at:04d}", "partition": name} for at in range(count)]
        for name, count in counts.items()
    }


def heads(pool, best_first=True):
    """A head sidecar scoring every place, descending on the key's own order."""
    out = {}
    for held in pool.values():
        for at, row in enumerate(held):
            score = 1.0 - at / max(1, len(held)) if best_first else 0.5
            out[str(row["key"])] = {"p_ge3": score}
    return out


def ledger_row(key, location, partition="mandelbrot", mode="smooth", colormap="viridis"):
    return {
        "schema": 1,
        "key": key,
        "recipe_key": key,
        "partition": partition,
        "location": {"key": location},
        "recipe": {"mode": mode, "colormap": colormap},
    }


def made_row(arm, location, p_ge4, *, k=1, band="band00", partition="mandelbrot", mode="smooth"):
    return {
        "key": f"{arm}-{location}-{k}",
        "arm": arm,
        "band": band,
        "k": k,
        "location": location,
        "partition": partition,
        "rank": k,
        "rank_fraction": 0.5,
        "mode": mode,
        "mode_kind": "field",
        "colormap": "viridis",
        "p_ge4": p_ge4,
        "p_ge3": min(1.0, p_ge4 + 0.05),
        "seconds": 0.25,
        "acted": False,
        "cells": [],
    }


# --------------------------------------------------------------------------- #
# The roster is field modes, less what a ruling took out.
# --------------------------------------------------------------------------- #
def test_the_roster_is_only_modes_a_dumped_field_can_serve():
    from fractal_wallpapers.curation import colorize

    for mode in depth.field_modes():
        assert colorize.shareable(mode), f"{mode} cannot be served out of a dumped field"


def test_the_demoted_mode_is_out_of_the_draw_while_the_catalogue_still_ships_it():
    """`trap_circle` is niche by a ruling and production by the catalogue.

    Both halves matter. The draw must not offer it, and it must still resolve —
    the ruling demoted the mode, it did not delete the material already made in
    it.
    """
    from fractal_wallpapers import engine

    assert "trap_circle" in depth.DEMOTED
    assert "trap_circle" not in depth.field_modes()
    assert "trap_circle" in engine.production_modes()


# --------------------------------------------------------------------------- #
# The rank bands.
# --------------------------------------------------------------------------- #
def test_the_bands_cut_a_partition_into_equal_counts_top_to_bottom():
    pool = pools({"mandelbrot": 100})
    banded = depth.ranked_bands(pool, heads(pool), bands=10)
    sizes = [len(band) for band in banded["mandelbrot"]]
    assert sizes == [10] * 10
    assert banded["mandelbrot"][0][0]["rank"] == 1
    assert banded["mandelbrot"][-1][-1]["rank"] == 100


def test_a_place_the_sidecar_cannot_score_sorts_last_and_is_not_dropped():
    """The ranked pool and the flat pool have to be the same pool.

    A dropped row would unmatch the control silently, so an unscored place goes
    to the bottom band rather than out of the draw.
    """
    pool = pools({"mandelbrot": 4})
    scores = heads(pool)
    del scores["mandelbrot-0000"]
    banded = depth.ranked_bands(pool, scores, bands=2)
    everything = [row["key"] for band in banded["mandelbrot"] for row in band]
    assert set(everything) == {row["key"] for row in pool["mandelbrot"]}
    assert everything[-1] == "mandelbrot-0000"


def test_the_ranked_draw_spans_the_whole_range_and_not_its_top():
    """The difference between this pass and the two it exists to join up."""
    pool = pools(dict.fromkeys(PARTITIONS, 100))
    banded = depth.ranked_bands(pool, heads(pool), bands=10)
    drawn = depth.banded_places(banded, seed=7, count=30)
    assert len({row["rank_band"] for row in drawn}) == 10
    assert max(row["rank"] for row in drawn) > 50


def test_a_band_weight_of_zero_keeps_that_band_out_and_the_rest_in():
    pool = pools({"mandelbrot": 100})
    banded = depth.ranked_bands(pool, heads(pool), bands=10)
    drawn = depth.banded_places(
        banded, seed=7, count=20, weights={"band09": 0, "band08": 0, "band00": 3}
    )
    bands = {row["rank_band"] for row in drawn}
    assert 9 not in bands and 8 not in bands
    counted = [row["rank_band"] for row in drawn]
    assert counted.count(0) > counted.count(1), "a weighted band should draw more often"


def test_the_flat_draw_never_lands_on_a_place_the_ranked_draw_took():
    pool = pools(dict.fromkeys(PARTITIONS, 60))
    banded = depth.ranked_bands(pool, heads(pool), bands=10)
    ranked = depth.banded_places(banded, seed=3, count=30)
    taken = {str(row["key"]) for row in ranked}
    flat = depth.flat_places(banded, taken, seed=4, want=dict.fromkeys(PARTITIONS, 5))
    assert not taken & {str(row["key"]) for row in flat}
    assert all(row.get("rank") is not None for row in flat), "the control carries its rank too"


# --------------------------------------------------------------------------- #
# The near band reads the best FIELD candidate, not the best one.
# --------------------------------------------------------------------------- #
def test_the_near_band_is_read_off_the_best_candidate_this_run_can_afford():
    """A place whose best is a composite has no field to dump.

    Forty candidates there would cost what the whole run is budgeted at, so the
    band is read off the best candidate in a mode the run can serve — and the
    composite, however good, is not what the arm holds its mode at.
    """
    rows = [
        ledger_row("a", "place", mode="smooth_stripe"),
        ledger_row("b", "place", mode="smooth"),
    ]
    scores = {"a": 0.95, "b": 0.60}
    best = depth.best_field_by_location(rows, scores, roster={"smooth", "stripe"})
    assert best["place"]["best"] == pytest.approx(0.60)
    assert best["place"]["best_mode"] == "smooth"
    index = {"place": {"maxiter": 100}}
    assert [row["key"] for row in depth.near_places(best, index, seed=1, count=5)] == ["place"]


def test_a_place_whose_only_field_candidate_is_over_the_bar_is_not_near_band():
    rows = [ledger_row("a", "place", mode="smooth")]
    best = depth.best_field_by_location(rows, {"a": 0.97}, roster={"smooth"})
    assert not depth.near_places(best, {"place": {}}, seed=1, count=5)


# --------------------------------------------------------------------------- #
# What a plan offers one place.
# --------------------------------------------------------------------------- #
def test_the_modes_are_cycled_so_one_of_them_does_not_own_the_head_of_the_curve():
    roster = ["smooth", "stripe", "tia"]
    maps = [f"map{at}" for at in range(20)]
    shots = depth.plan_cycled_modes(
        depth.RANKED,
        [{"key": "place", "partition": "mandelbrot", "rank": 1, "rank_band": 0}],
        roster,
        maps,
        seed=5,
        width=9,
    )
    assert len(shots) == 9
    ordered = [shot.mode for shot in sorted(shots, key=lambda shot: shot.k)]
    assert len(set(ordered[:3])) == 3, "the first three candidates are three modes"
    assert ordered[0] == ordered[3] == ordered[6], "and the roster then repeats"


def test_no_place_is_offered_a_map_it_already_carries_in_that_mode():
    """A colliding recipe would be skipped by the loop and the arm would report a
    `k` it never reached."""
    maps = ["a", "b", "c", "d"]
    shots = depth.plan_held_mode(
        [{"key": "place", "partition": "mandelbrot", "best_mode": "smooth"}],
        {("place", "smooth"): {"a", "b"}},
        maps,
        seed=1,
        width=4,
    )
    assert {shot.colormap for shot in shots} == {"c", "d"}
    assert [shot.k for shot in shots] == [1, 2]


def test_the_floor_draw_holds_the_place_and_moves_the_mode():
    shots = depth.plan_floor(
        [{"key": "place", "partition": "mandelbrot"}],
        ["threads", "itinerary"],
        {},
        [f"map{at}" for at in range(10)],
        seed=2,
        width=3,
    )
    assert len(shots) == 6
    assert {shot.location for shot in shots} == {"place"}
    assert {shot.mode for shot in shots} == {"threads", "itinerary"}
    assert [shot.mode for shot in sorted(shots, key=lambda shot: shot.k)][:2] == [
        "threads",
        "itinerary",
    ], "the modes are cycled, so a truncated run served both"


def test_a_mode_is_short_by_distinct_locations_and_not_by_clearing_candidates():
    """Ten clearing candidates at one place is one seat, because a collection
    seats a location once."""
    rows = [ledger_row(f"k{at}", "one_place", mode="threads") for at in range(10)]
    scores = {f"k{at}": 0.99 for at in range(10)}
    short = depth.deficient_modes(rows, scores, floor=10)
    assert short["threads"] == 9


# --------------------------------------------------------------------------- #
# The weave.
# --------------------------------------------------------------------------- #
def test_every_prefix_of_the_woven_plan_holds_the_draws_in_proportion():
    plans = {
        depth.NEAR: [f"n{at}" for at in range(100)],
        depth.RANKED: [f"r{at}" for at in range(200)],
        depth.FLAT: [f"f{at}" for at in range(100)],
    }
    woven = depth.weave(plans)
    half = woven[: len(woven) // 2]
    assert 0.4 < sum(1 for item in half if item.startswith("r")) / len(half) < 0.6


def test_a_draw_given_no_share_contributes_nothing():
    plans = {depth.NEAR: ["n0"], depth.FLOOR: ["z0"]}
    woven = depth.weave(plans, {depth.NEAR: 1.0, depth.FLOOR: 0.0})
    assert woven[0] == "n0"


# --------------------------------------------------------------------------- #
# The curves.
# --------------------------------------------------------------------------- #
def test_a_location_that_never_reached_a_width_is_out_of_its_denominator():
    """A budget that stopped mid-location must not bend every curve down.

    One place gets four candidates and one gets two. At `k = 3` only the first
    place is alive, so the rate there is over one location and not two.
    """
    made = [made_row(depth.RANKED, "deep", 0.1, k=k) for k in (1, 2, 3, 4)]
    made += [made_row(depth.RANKED, "shallow", 0.95, k=k) for k in (1, 2)]
    curve = depth.curves(made, bars=(0.90,))[depth.RANKED]["bar_090"]
    at = {row["k"]: row for row in curve}
    assert at[1]["locations_with_k"] == 2 and at[1]["cumulative_primed"] == 1
    assert at[3]["locations_with_k"] == 1 and at[3]["cumulative_primed"] == 0
    assert at[3]["cumulative_rate"] == 0.0


def test_the_cumulative_curve_never_falls_and_the_marginal_gain_is_its_difference():
    made = [made_row(depth.NEAR, f"p{at}", 0.0, k=1) for at in range(4)]
    made += [made_row(depth.NEAR, f"p{at}", 0.95 if at < 2 else 0.1, k=2) for at in range(4)]
    curve = depth.curves(made, bars=(0.90,))[depth.NEAR]["bar_090"]
    assert [row["cumulative_rate"] for row in curve] == [0.0, 0.5]
    assert curve[1]["marginal_gain"] == pytest.approx(0.5)


def test_the_same_rows_read_at_two_bars_give_two_curves():
    made = [made_row(depth.NEAR, "p", 0.62, k=1)]
    both = depth.curves(made, bars=(0.50, 0.90))[depth.NEAR]
    assert both["bar_050"][0]["cumulative_primed"] == 1
    assert both["bar_090"][0]["cumulative_primed"] == 0


def test_the_rank_readout_reads_the_breadth_draws_and_leaves_the_near_band_out():
    """The near band's places were chosen on their incumbent, so their rank says
    nothing about what a rank buys."""
    made = [made_row(depth.RANKED, "r", 0.95, band="band03")]
    made += [made_row(depth.FLAT, "f", 0.1, band="band07")]
    made += [made_row(depth.NEAR, "n", 0.99, band="incumbent")]
    out = depth.rank_readout(made, bars=(0.90,))
    assert out["locations"] == 2
    assert set(out["bar_090"]["pooled"]) == {"band03", "band07"}


def test_the_route_spends_the_best_band_first_and_says_when_it_runs_out():
    rank = {
        "bar_090": {
            "pooled": {
                "band00": {"locations": 10, "primed": 5, "rate": 0.5, "seconds_per_location": 10.0},
                "band09": {"locations": 10, "primed": 1, "rate": 0.1, "seconds_per_location": 10.0},
            }
        }
    }
    world = {"pools": {"mandelbrot": [{}] * 100}, "best": {}}
    route = depth.route_to(rank, {}, world, target=6, bands=2)
    assert route["legs"][0]["band"] == "band00"
    assert route["reaches_target"]
    assert route["locations_to_open"] == 12


def test_the_route_counts_the_bands_it_was_cut_at_and_not_the_ones_it_reached():
    """A truncated run reaches fewer bands than it drew. Dividing the stock by
    what it reached would inflate every band's available pool."""
    rank = {
        "bar_090": {
            "pooled": {
                "band00": {"locations": 10, "primed": 1, "rate": 0.1, "seconds_per_location": 1.0}
            }
        }
    }
    world = {"pools": {"mandelbrot": [{}] * 100}, "best": {}}
    assert (
        depth.route_to(rank, {}, world, target=1, bands=10)["legs"][0]["locations_available"] == 10
    )


def test_a_route_whose_stock_cannot_reach_the_target_says_so_rather_than_extrapolating():
    rank = {
        "bar_090": {
            "pooled": {
                "band00": {"locations": 10, "primed": 1, "rate": 0.1, "seconds_per_location": 1.0}
            }
        }
    }
    world = {"pools": {"mandelbrot": [{}] * 10}, "best": {}}
    route = depth.route_to(rank, {}, world, target=1000, bands=1)
    assert not route["reaches_target"]
    assert route["primed_expected"] < 1000


# --------------------------------------------------------------------------- #
# The whole plan, on a world small enough to check by hand.
# --------------------------------------------------------------------------- #
def a_world(places=400, near=6):
    """A population with a pool to open, a near band to deepen, and proven places."""
    pool = pools(dict.fromkeys(PARTITIONS, places))
    index, by_key, rows, scores, best = {}, {}, [], {}, {}
    for held in pool.values():
        for row in held:
            index[str(row["key"])] = {"maxiter": 200, "viewport": {}}
            by_key[str(row["key"])] = {**row, "family": {"kind": "mandelbrot"}}
    for at in range(near):
        key = f"seated-{at}"
        rows.append(ledger_row(f"r{at}", key, mode="smooth"))
        scores[f"r{at}"] = 0.62
        index[key] = {"maxiter": 200, "viewport": {}}
        by_key[key] = {"key": key, "partition": "mandelbrot", "family": {"kind": "mandelbrot"}}
        best[key] = {"best": 0.62, "best_mode": "smooth", "partition": "mandelbrot"}
    return {
        "index": index,
        "by_key": by_key,
        "pools": pool,
        "rows": rows,
        "ledger_scores": scores,
        "best": best,
        "taken": {},
        "head_scores": heads(pool),
        "known": set(),
    }


def test_a_measuring_plan_takes_the_three_draws_and_leaves_the_floor_empty():
    plan, shape = build_a_plan()
    assert {shot.arm for shot in plan} == set(depth.MEASURING)
    assert shape["arms"][depth.FLOOR]["candidates"] == 0
    assert shape["roster"] == depth.field_modes()


def build_a_plan(**knobs):
    return depth.build_plan(
        a_world(),
        seed=11,
        rate=0.3,
        budget=600,
        width=8,
        bands=5,
        log=lambda *_args: None,
        **knobs,
    )


def test_a_production_plan_spends_its_floor_share_on_the_modes_that_are_short():
    plan, shape = build_a_plan(
        shares={depth.NEAR: 0.3, depth.RANKED: 0.4, depth.FLAT: 0.0, depth.FLOOR: 0.3},
        floor_modes=["threads", "smooth_mean_angle"],
        floor_width=2,
    )
    floor = [shot for shot in plan if shot.arm == depth.FLOOR]
    assert floor and {shot.mode for shot in floor} == {"threads", "smooth_mean_angle"}
    assert not [shot for shot in plan if shot.arm == depth.FLAT]
    assert shape["floor_modes"] == ["threads", "smooth_mean_angle"]


def test_the_floor_draw_stands_on_places_that_already_cleared_the_seating_bar():
    """A mode short of seats is short of good material in it, and a proven place
    is the cheapest evidence that a place can carry one at all."""
    plan, _shape = build_a_plan(
        shares={depth.NEAR: 0.0, depth.RANKED: 0.0, depth.FLAT: 0.0, depth.FLOOR: 1.0},
        floor_modes=["threads"],
        floor_width=2,
    )
    world = a_world()
    assert {shot.location for shot in plan} <= set(world["best"])
