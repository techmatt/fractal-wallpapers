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

from fractal_wallpapers.curation import colorize, depth, hunt, mine

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


def test_a_niche_mode_is_out_of_the_draw_while_the_catalogue_still_ships_it():
    """`trap_circle` is niche by [`mode_policy`] and production by the catalogue.

    Both halves matter. The draw must not offer it, and it must still resolve —
    the ruling took the mode out of what is bought next, it did not delete the
    material already made in it.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import mode_policy

    assert mode_policy.weight_of("trap_circle") == mode_policy.NICHE
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
    places = {"place": {"key": "place", "maxiter": 100}}
    assert [row["key"] for row in depth.near_places(best, places, seed=1, count=5)] == ["place"]


def test_a_place_whose_only_field_candidate_is_over_the_bar_is_not_near_band():
    rows = [ledger_row("a", "place", mode="smooth")]
    best = depth.best_field_by_location(rows, {"a": 0.97}, roster={"smooth"})
    assert not depth.near_places(best, {"place": {}}, seed=1, count=5)


def test_the_near_band_draws_a_place_the_framing_scan_has_never_held_a_row_for():
    """The arm's population is the ledger's ratings; a framing row is not a ticket.

    `world["by_key"]` is what bounds it — a location there is renderable, framed
    or not — and the frame itself is resolved at draw time by `hunt.frame_for`.
    """
    rows = [ledger_row("a", "place", mode="smooth")]
    best = depth.best_field_by_location(rows, {"a": 0.60}, roster={"smooth"})
    by_key = {"place": {"key": "place", "viewport": {"width": "0.5"}, "maxiter": 100}}
    drawn = depth.near_places(best, by_key, seed=1, count=5)
    assert [row["key"] for row in drawn] == ["place"]
    frame = hunt.frame_for(by_key["place"], {})
    assert (frame["maxiter"], frame["adopted"], frame["from_scan"]) == (100, False, False)


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


def test_a_breadth_demoted_mode_keeps_its_near_band_seat_and_loses_the_cycle():
    """The two rulings are not the same ruling. `--modes` narrows the set a
    near-band incumbent must be in; this narrows only what breadth cycles."""
    plan, shape = build_a_plan(breadth_demoted=["smooth"])
    breadth = {shot.mode for shot in plan if shot.arm in (depth.RANKED, depth.FLAT)}
    near = [shot for shot in plan if shot.arm == depth.NEAR]
    assert "smooth" not in breadth
    assert near and {shot.mode for shot in near} == {"smooth"}, (
        "every seated place in the fixture holds smooth, and the near band holds "
        "the incumbent's mode"
    )
    assert shape["breadth_roster"] == [mode for mode in depth.field_modes() if mode != "smooth"]
    assert shape["breadth_demoted"] == ["smooth"]


def test_no_mode_is_standing_demoted_out_of_breadth_any_more():
    """`tia` was the one standing breadth demotion and [`mode_policy`] supersedes
    it: a mode weighted 2 that the draw which would buy more of it cannot reach is
    a demotion that confirms itself. The mechanism stays a per-run knob, because
    *drop from breadth and keep the near-band seat* is the one thing a weight in
    {0, 1, 2} cannot say.
    """
    from fractal_wallpapers.curation import mode_policy

    assert depth.BREADTH_DEMOTED == ()
    assert mode_policy.weight_of("tia") == mode_policy.PROMOTED
    assert "tia" in depth.field_modes(), "affordable, and an eligible incumbent"
    _plan, shape = build_a_plan()
    assert "tia" in shape["breadth_roster"]


def test_a_breadth_demotion_that_empties_the_cycle_is_refused():
    with pytest.raises(depth.DepthRefused, match="nothing to cycle"):
        build_a_plan(roster=["smooth"], breadth_demoted=["smooth"])


# --------------------------------------------------------------------------- #
# The conditioned draw.
# --------------------------------------------------------------------------- #
AIMED_SHARES = {depth.NEAR: 0.0, depth.RANKED: 0.3, depth.FLAT: 0.35, depth.AIMED: 0.35}


def test_the_aimed_arm_is_the_flat_draw_with_one_thing_changed():
    """The comparison is the point. If the aimed arm drew its places differently,
    or at a different width, its hit rate would not be readable against the flat
    arm's and the run would answer a question nobody asked."""
    plan, shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green")
    aimed = [shot for shot in plan if shot.arm == depth.AIMED]
    flat = [shot for shot in plan if shot.arm == depth.FLAT]
    assert aimed and flat
    assert {shot.mode for shot in aimed} == {shot.mode for shot in flat}, "one roster"
    assert max(shot.k for shot in aimed) == max(shot.k for shot in flat), "one width"
    assert not ({shot.location for shot in aimed} & {shot.location for shot in flat}), (
        "the two draws are disjoint, so no location is in both the arm and its control"
    )
    assert shape["cell"] == "dark_vivid_green"


def test_the_aimed_arm_draws_its_maps_through_the_carrier_table_and_the_flat_arm_does_not():
    plan, _shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green")
    aimed = {shot.colormap for shot in plan if shot.arm == depth.AIMED}
    flat = {shot.colormap for shot in plan if shot.arm == depth.FLAT}
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import carriers

    pool = list(colorize.pool(11))
    offers = {name for name, _share in carriers.for_cell("dark_vivid_green", within=pool)}
    assert offers, "the tracked table carries this cell inside the run's own pool"
    assert aimed <= offers, "every aimed map is one the table offers for the cell"
    assert not flat <= offers, "and the control is drawing from the whole pool"


def test_every_aimed_shot_says_what_it_was_drawn_for_and_no_other_shot_does():
    """A prior about the map, on the row, so a reader can tell an aimed candidate
    from a lucky one. It is never read as a claim about the picture."""
    plan, _shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green")
    for shot in plan:
        if shot.arm == depth.AIMED:
            assert shot.cell == "dark_vivid_green"
            assert shot.named()["drawn_for"] == "dark_vivid_green"
        else:
            assert shot.cell is None
            assert "drawn_for" not in shot.named()


def test_a_conditioned_share_with_no_cell_is_refused_rather_than_drawn_flat():
    with pytest.raises(depth.DepthRefused, match="no --cell"):
        build_a_plan(shares=AIMED_SHARES)


def test_a_cell_with_no_share_is_refused_rather_than_silently_ignored():
    with pytest.raises(depth.DepthRefused, match="no share of the budget"):
        build_a_plan(cell="dark_vivid_green")


def test_a_misspelt_cell_is_refused_at_the_plan_and_not_at_the_last_candidate():
    with pytest.raises(depth.DepthRefused, match="not a codebook cell"):
        build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_grene")


def test_the_hit_rate_counts_the_verdict_and_never_the_carrier_table():
    """Draw-biased, verdict-measured. A candidate drawn for green that came out
    rose is a miss; one drawn flat that came out green is a hit. The table is not
    consulted here at all."""
    made = [
        {"arm": depth.AIMED, "location": "a", "colormap": "m1", "cells": ["dark_vivid_green"]},
        {"arm": depth.AIMED, "location": "a", "colormap": "m2", "cells": ["dark_muted_rose"]},
        {"arm": depth.AIMED, "location": "b", "colormap": "m1", "cells": []},
        {"arm": depth.FLAT, "location": "c", "colormap": "m9", "cells": ["dark_vivid_green"]},
        {"arm": depth.FLAT, "location": "d", "colormap": "m8", "cells": ["blue"]},
        {"arm": depth.FLAT, "location": "e", "colormap": "m7", "cells": []},
        {"arm": depth.FLAT, "location": "f", "colormap": "m6", "cells": []},
    ]
    out = depth.hit_rate(made, "dark_vivid_green")
    assert out["cell"] == "dark_vivid_green"
    assert out[depth.AIMED]["candidates"] == 3
    assert out[depth.AIMED]["dominant"] == 1
    assert out[depth.AIMED]["rate"] == pytest.approx(1 / 3, abs=1e-5)
    assert out[depth.AIMED]["locations_with_a_hit"] == 1
    assert out[depth.AIMED]["maps_that_hit"] == 1
    assert out[depth.FLAT]["rate"] == pytest.approx(0.25)
    assert out["lift"] == pytest.approx(1.333, abs=0.001)
    assert out["renders_per_hit"] == pytest.approx(3.0)


def test_a_run_with_no_cell_reports_no_hit_rate_rather_than_an_empty_one():
    assert depth.hit_rate([{"arm": depth.FLAT, "location": "a", "cells": []}], None) is None


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


# --------------------------------------------------------------------------- #
# The matched pair: one band cut, one partition mix, no ranked draw to lean on.
# --------------------------------------------------------------------------- #
MATCHED_SHARES = {depth.NEAR: 0.0, depth.RANKED: 0.0, depth.FLAT: 0.5, depth.AIMED: 0.5}


def test_the_two_matched_arms_are_drawn_when_the_ranked_draw_takes_no_share():
    """A run that is only the arm and its control is the shape a colour question
    wants, and it used to plan nothing at all: both breadth draws were sized off
    the ranked draw's realized partition counts, which are empty when it has no
    share."""
    plan, shape = build_a_plan(shares=MATCHED_SHARES, cell="dark_vivid_green")
    assert {shot.arm for shot in plan} == {depth.FLAT, depth.AIMED}
    assert shape["matched_arms_sized_from"] == "their own shares"
    assert shape["ranked_by_partition"] == {}
    assert shape["matched_mix_agrees"], "the arm and its control ask for one mix"


def test_the_matched_mix_agrees_whichever_draw_sized_it():
    for shares in (MATCHED_SHARES, AIMED_SHARES):
        _plan, shape = build_a_plan(shares=shares, cell="dark_vivid_green")
        assert shape["matched_mix_agrees"]


def test_top_bands_cuts_both_matched_arms_and_leaves_the_ranked_draw_whole():
    """The curve is measured end to end and the comparison is measured in one
    band, so the cut lands on the two arms and never on the draw that is the
    curve."""
    plan, shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green", top_bands=2)
    assert shape["top_bands"] == 2
    for arm in (depth.FLAT, depth.AIMED):
        held = {shot.band for shot in plan if shot.arm == arm}
        assert held <= {"band00", "band01"}, f"{arm} stands in the strongest two bands"
    ranked = {shot.band for shot in plan if shot.arm == depth.RANKED}
    assert len(ranked) > 2, "the ranked draw still spans the bands it was cut at"


def test_unsaid_top_bands_leaves_every_draw_over_the_whole_rank_axis():
    _plan, shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green")
    assert shape["top_bands"] is None
    plan, _shape = build_a_plan(shares=MATCHED_SHARES, cell="dark_vivid_green")
    assert len({shot.band for shot in plan}) > 1


def test_strongest_bands_keeps_the_head_of_every_partition_and_none_of_the_tail():
    banded = {"mandelbrot": [["a"], ["b"], ["c"]], "phoenix": [["d"], ["e"], ["f"]]}
    assert depth.strongest_bands(banded, None) == banded
    assert depth.strongest_bands(banded, 2) == {
        "mandelbrot": [["a"], ["b"]],
        "phoenix": [["d"], ["e"]],
    }


def test_a_partition_spread_is_round_robin_and_never_asks_for_stock_that_is_not_there():
    banded = {"mandelbrot": [[1, 2, 3, 4]], "phoenix": [[5]], "multibrot3": [[6, 7]]}
    assert depth.spread_over_partitions(banded, 3) == {
        "mandelbrot": 1,
        "multibrot3": 1,
        "phoenix": 1,
    }
    # phoenix holds one place and multibrot3 two, so the remainder can only go to
    # mandelbrot however many rounds are walked.
    assert depth.spread_over_partitions(banded, 99) == {
        "mandelbrot": 4,
        "multibrot3": 2,
        "phoenix": 1,
    }
    assert depth.spread_over_partitions({"mandelbrot": [[]]}, 5) == {}


def test_every_draw_records_the_seeds_it_was_taken_under():
    """A conditioned run is a measurement and a measurement nobody can re-take is
    an anecdote. The place draw and the palette draw at one arm are seeded apart,
    so one number on the record would not be the answer."""
    _plan, shape = build_a_plan(shares=AIMED_SHARES, cell="dark_vivid_green")
    seeds = shape["seeds"]
    assert seeds["base"] == 11
    assert seeds[depth.FLAT] == {"places": 12, "candidates": 11}
    assert seeds[depth.AIMED] == {"places": 13, "candidates": 13}
    assert set(seeds) == {"base", *depth.DRAWS}


# --------------------------------------------------------------------------- #
# The readout the conditioned arm exists for.
# --------------------------------------------------------------------------- #
def a_bars_table():
    return {
        "modes": {
            "smooth": {"column": "p_ge4", "bar": 0.5},
            "curvature": {"column": "p_ge3", "bar": 0.5},
        },
        "on_default": ["smooth"],
        "on_fallback": ["curvature"],
        "ledger_candidates": 1000,
        "ledger_clearing": 70,
        "ledger_clear_rate": 0.07,
    }


def a_made_row(arm, mode="smooth", p4=0.9, p3=0.99, cells=(), location="L", seconds=0.4):
    return {
        "arm": arm,
        "mode": mode,
        "p_ge4": p4,
        "p_ge3": p3,
        "cells": list(cells),
        "location": location,
        "seconds": seconds,
    }


def test_a_thin_mode_clears_on_its_own_fallback_column_and_not_on_the_default():
    table = a_bars_table()
    assert depth.clears_its_bar(a_made_row("flat", "curvature", p4=0.1, p3=0.8), table)
    assert not depth.clears_its_bar(a_made_row("flat", "smooth", p4=0.1, p3=0.8), table)


def test_a_mode_the_table_never_heard_of_falls_to_the_strict_column():
    table = a_bars_table()
    assert not depth.clears_its_bar(a_made_row("flat", "threads", p4=0.1, p3=0.99), table)
    assert depth.clears_its_bar(a_made_row("flat", "threads", p4=0.7, p3=0.99), table)


def test_the_three_factors_are_reported_apart_before_they_are_multiplied():
    """The composed price hides the one risk the arm exists to test — whether the
    maps that carry a colour make worse pictures — so the clear rate has to be
    readable on its own."""
    made = (
        [a_made_row(depth.AIMED, cells=["teal"], location=f"a{i}") for i in range(8)]
        + [a_made_row(depth.AIMED, p4=0.1, cells=["teal"], location=f"a{i}") for i in range(2)]
        + [a_made_row(depth.FLAT, cells=["teal"], location="f0")]
        + [a_made_row(depth.FLAT, location=f"f{i}") for i in range(1, 10)]
    )
    out = depth.dominant_and_clearing(made, "teal", a_bars_table())
    assert out["cell"] == "teal"
    assert out["ledger_clear_rate"] == 0.07
    assert out[depth.AIMED]["cell_hit_rate"] == 1.0
    assert out[depth.AIMED]["clear_rate"] == 0.8
    assert out[depth.AIMED]["dominant_and_clearing"] == 8
    assert out[depth.AIMED]["renders_per_win"] == 1.25
    assert out[depth.FLAT]["cell_hit_rate"] == 0.1
    assert out[depth.FLAT]["clear_rate"] == 1.0
    assert out[depth.FLAT]["renders_per_win"] == 10.0
    assert out["lift"]["cell_hit_rate"] == 10.0
    assert out["lift"]["clear_rate"] == 0.8
    assert out["renders_per_win_ratio"] == 8.0


def test_the_renders_per_place_is_reported_because_the_census_factor_needs_it():
    made = [a_made_row(depth.AIMED, location=f"a{i // 4}") for i in range(12)]
    made += [a_made_row(depth.FLAT, location=f"f{i // 6}") for i in range(12)]
    out = depth.dominant_and_clearing(made, "teal", a_bars_table())
    assert out[depth.AIMED]["renders_per_place"] == 4.0
    assert out[depth.FLAT]["renders_per_place"] == 6.0


def test_an_arm_that_never_hit_the_cell_reports_no_price_rather_than_infinity():
    made = [a_made_row(depth.AIMED), a_made_row(depth.FLAT)]
    out = depth.dominant_and_clearing(made, "teal", a_bars_table())
    assert out[depth.AIMED]["renders_per_win"] is None
    assert out["renders_per_win_ratio"] is None
    assert depth.dominant_and_clearing(made, None, a_bars_table()) is None


# --------------------------------------------------------------------------- #
# Three workers: the unit of work, the sizing, and the starvation case.
# --------------------------------------------------------------------------- #
def test_the_plan_is_sized_off_the_worker_count_because_the_rate_is_per_engine():
    """`--budget` is wall and `--rate` is one engine's seconds a candidate, so a
    leg on three engines can buy three times the plan in the same clock. Sizing
    off one engine plans a third of the hour and the leg stops having run out of
    plan rather than out of time — which reads on the record as a budget that was
    not spent and is really a plan that was not written."""
    one, shape_one = build_a_plan(workers=1)
    three, shape_three = build_a_plan(workers=3)
    assert shape_three["workers_sized_for"] == 3
    assert len(three) > len(one), "three engines buy more plan in the same wall clock"
    # Not exactly 3x: each draw's candidate count is floored into whole locations
    # at its own width before the weave, so the ratio lands near three and not on
    # it. What is pinned is the direction and the order of magnitude.
    assert 2.5 <= len(three) / max(1, len(one)) <= 3.5


def test_the_unit_of_work_is_a_location_so_one_dump_serves_one_worker():
    """The hazard the whole design is built around. A field is dumped once per
    (location, mode) and every palette at that pair is a recolour of it — 56% of
    a candidate at width 40 — so a plan cut per *candidate* would hand one place
    to three workers and each would dump the same field. Cut at the location and
    the dump is paid once, by whoever owns the place.

    Which means: every shot at a location is in exactly one block, and no
    location appears in two.
    """
    plan, _shape = build_a_plan()
    world = a_world()
    maker = _StubMaker()
    blocks, _skipped, _unresolvable = depth.blocks_of(
        plan, world, maker, set(), log=lambda *_a: None
    )
    seen = [{shot.location for _at, shot, *_rest in block} for block in blocks]
    for block in seen:
        assert len(block) == 1, "a block is ONE location, never a mix"
    assert len(set().union(*seen)) == len(seen), "and no location is in two blocks"
    assert sum(len(block) for block in blocks) == len(plan)


def test_a_block_order_follows_the_weave_so_a_truncated_leg_keeps_its_proportions():
    """The weave exists so a leg that runs out of clock has spent it on the arms
    in the proportions it intended. Cutting into blocks keeps that one location
    coarser: blocks come back in the order each location FIRST appears in the
    weave, so a prefix of the blocks is a prefix of the weave rounded to whole
    places rather than an arbitrary reordering."""
    plan, _shape = build_a_plan()
    blocks, _skipped, _unresolvable = depth.blocks_of(
        plan, a_world(), _StubMaker(), set(), log=lambda *_a: None
    )
    first_appearance = [block[0][0] for block in blocks]
    assert first_appearance == sorted(first_appearance), "blocks are in weave order"


def test_a_recipe_the_ledger_already_holds_is_dropped_in_the_parent():
    """Before a worker is handed anything, for two reasons. The skip count is
    exact up front rather than three workers racing to discover the same thing;
    and `known` is a hundred and thirty thousand keys that would otherwise be
    pickled to every worker with every block."""
    plan, _shape = build_a_plan()
    maker = _StubMaker()
    world = a_world()
    every, _s, _u = depth.blocks_of(plan, world, maker, set(), log=lambda *_a: None)
    keys = {key for block in every for *_head, key in block}
    none_left, skipped, _u = depth.blocks_of(
        plan, world, _StubMaker(), set(keys), log=lambda *_a: None
    )
    assert none_left == [], "a plan the ledger already holds whole is no blocks at all"
    assert skipped == len(plan)


def test_a_leg_with_fewer_places_than_workers_runs_on_fewer_and_says_so():
    """The narrow legs here really are narrow — the near-band pool held 25
    locations for the two-mode field roster and 19 for the four direct traps —
    so this is not a theoretical branch. Three is the machine's ceiling and not
    a floor, and a worker with no place to take is a process spawned to idle."""
    said = []
    assert depth.workers_for([["a"], ["b"]], 3, log=said.append) == 2
    assert said and "fewer than the 3 worker(s)" in said[0]
    assert depth.workers_for([["a"], ["b"], ["c"], ["d"]], 3, log=said.append) == 3
    assert depth.workers_for([], 3, log=said.append) == 1, "never zero"


class _StubRecipe:
    """Enough of a recipe for [`recipes.key_of`], which digests `pixels()`."""

    def __init__(self, shot):
        self._pixels = {
            "location": shot.location,
            "mode": shot.mode,
            "colormap": shot.colormap,
            "k": shot.k,
        }

    def pixels(self) -> dict:
        return dict(self._pixels)


class _StubMaker:
    """`recipe_for` alone, which is all [`depth.blocks_of`] asks of a maker.

    A real one loads the band, the map table and the group table; none of that
    decides which block a shot lands in, and the judge — the expensive half — is
    the workers' and never the parent's.
    """

    def recipe_for(self, shot, place, frame):
        return _StubRecipe(shot)


# --------------------------------------------------------------------------- #
# The process boundary between a worker and the parent.
# --------------------------------------------------------------------------- #
def _reads_of_result() -> set:
    """Every `result["<key>"]` the parent's `take` asks for, off the source."""
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(depth.run)))
    take = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "take"
    )
    return {
        node.slice.value
        for node in ast.walk(take)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "result"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    } | {
        node.comparators[0].id and node.left.value
        for node in ast.walk(take)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.left.value, str)
        and isinstance(node.comparators[0], ast.Name)
        and node.comparators[0].id == "result"
    }


def _keys_a_worker_spells() -> set:
    """Every string key `_render_block` puts in a dict it hands back."""
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(depth._render_block)))
    return {
        key.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def test_the_parent_reads_no_key_the_worker_does_not_spell():
    """A worker returns a DICT and not [`mine.make`]'s result, so the two are two lists.

    `curate depth run` renders in a `ProcessPoolExecutor` and every candidate is
    written by the parent off what the worker pickled back. A key added to
    `mine.make` and to the parent's `take` alone is not a missing field: it is a
    `KeyError` on the first candidate that lands, after the plan, the population
    read and the first block have all been paid — a leg that renders for minutes
    and writes no row.

    Bought on 2026-08-31 by `texture_flat`, which reached `take` three times and
    the worker's dict not at all, and killed every depth leg for eight hours.
    """
    reads = _reads_of_result()
    spelled = _keys_a_worker_spells()
    assert "texture_flat" in reads, "the guard is reading the wrong function"
    assert reads <= spelled, (
        f"the parent reads {sorted(reads - spelled)} out of a worker's result and "
        f"`_render_block` spells {sorted(spelled)}"
    )


# --------------------------------------------------------------------------- #
# The `centered` join: a flag that lives on the walk ledger and nowhere else.
# --------------------------------------------------------------------------- #
def test_the_centered_flag_reaches_the_draw_only_through_the_plan_time_join():
    """No store under the draw carries it, which is why the join exists.

    [`hunt.scanned`]'s population is the embedding store's rows, and those are
    written without the flag. So a draw that asked the pool directly would answer
    `not centered` for every location in the collection, silently.
    """
    from fractal_wallpapers.curation import framing

    row = {"key": "a", "partition": "mandelbrot"}
    assert framing.is_centered(row) is False, "absent reads as not centered, by design"
    assert "centered" not in row


def test_a_centered_draw_and_its_exclusion_partition_the_pool(monkeypatch):
    pool = pools({"mandelbrot": 6, "phoenix": 4})
    keys = frozenset({"mandelbrot-0000", "mandelbrot-0001", "phoenix-0000"})
    monkeypatch.setattr(depth, "centered_locations", lambda: keys)
    only = depth.by_centered(pool, depth.CENTERED_ONLY, log=lambda *_a: None)
    rest = depth.by_centered(pool, depth.CENTERED_EXCLUDE, log=lambda *_a: None)
    took = {str(row["key"]) for held in only.values() for row in held}
    left = {str(row["key"]) for held in rest.values() for row in held}
    whole = {str(row["key"]) for held in pool.values() for row in held}
    assert took == set(keys)
    assert took | left == whole and not (took & left), "a partition of the pool, both ways"


def test_an_unfiltered_draw_is_the_pool_object_itself_and_pays_no_join(monkeypatch):
    """`any` is what every leg drew before the flag existed, and it must not read
    41 walk ledgers to say so."""
    monkeypatch.setattr(
        depth, "centered_locations", lambda: pytest.fail("the join was taken for `any`")
    )
    pool = pools({"mandelbrot": 3})
    assert depth.by_centered(pool, depth.CENTERED_ANY, log=lambda *_a: None) is pool


def test_a_partition_with_no_centered_location_leaves_the_draw_rather_than_emptying_it(
    monkeypatch,
):
    pool = pools({"mandelbrot": 4, "phoenix": 4})
    monkeypatch.setattr(depth, "centered_locations", lambda: frozenset({"mandelbrot-0000"}))
    only = depth.by_centered(pool, depth.CENTERED_ONLY, log=lambda *_a: None)
    assert set(only) == {"mandelbrot"}, "an empty partition is dropped, not carried as []"


def test_a_misspelt_centred_filter_is_refused():
    with pytest.raises(depth.DepthRefused, match="not one of"):
        depth.by_centered(pools({"mandelbrot": 2}), "centred", log=lambda *_a: None)


def test_the_centered_cut_moves_the_ranked_draw_and_its_control_together(monkeypatch):
    """A control drawn from a different population than the arm it controls is
    not a control, so the cut lands on the pool both are banded out of."""
    keys = frozenset(f"mandelbrot-{at:04d}" for at in range(400))
    monkeypatch.setattr(depth, "centered_locations", lambda: keys)
    plan, shape = build_a_plan(centered=depth.CENTERED_ONLY)
    assert {shot.partition for shot in plan if shot.arm != depth.NEAR} == {"mandelbrot"}
    assert shape["centered"] == depth.CENTERED_ONLY
    assert set(shape["drawn_from"]) == {"mandelbrot"}
    assert set(shape["drawable"]) == set(PARTITIONS), "what the pool held is still reported"


# --------------------------------------------------------------------------- #
# The soft lean on the release mix.
# --------------------------------------------------------------------------- #
def test_a_partition_weight_buys_more_turns_and_starves_nobody():
    pool = pools(dict.fromkeys(PARTITIONS, 60))
    banded = depth.ranked_bands(pool, heads(pool), bands=3)
    drawn = depth.banded_places(banded, seed=5, count=60, partition_weights={"mandelbrot": 3})
    tally = {name: sum(1 for row in drawn if row["partition"] == name) for name in PARTITIONS}
    assert tally["mandelbrot"] > tally["phoenix"], "the weight leans the draw"
    assert min(tally.values()) > 0, "and it is a weight, not a floor: nobody is starved"


def test_the_band_axis_and_the_partition_axis_multiply():
    """They say different things — a band weight is measured, a partition weight
    is declared — so one must not quietly override the other."""
    pool = pools({"mandelbrot": 40, "phoenix": 40})
    banded = depth.ranked_bands(pool, heads(pool), bands=2)
    drawn = depth.banded_places(
        banded,
        seed=5,
        count=20,
        weights={"band01": 0},
        partition_weights={"mandelbrot": 3},
    )
    assert {row["rank_band"] for row in drawn} == {0}, "the zeroed band stays out"
    tally = {
        name: sum(1 for row in drawn if row["partition"] == name)
        for name in ("mandelbrot", "phoenix")
    }
    assert tally["mandelbrot"] > tally["phoenix"]


def test_an_unweighted_draw_is_unchanged_by_the_new_axis():
    pool = pools(dict.fromkeys(PARTITIONS, 30))
    banded = depth.ranked_bands(pool, heads(pool), bands=3)
    assert depth.banded_places(banded, seed=7, count=30) == depth.banded_places(
        banded, seed=7, count=30, partition_weights=None
    )


# --------------------------------------------------------------------------- #
# Opened-but-shallow: the dear half of the roster has never been asked.
# --------------------------------------------------------------------------- #
def test_the_dear_modes_are_exactly_what_a_dumped_field_cannot_serve():
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.curation import mine as mine_module

    assert set(depth.dear_modes()) | set(depth.field_modes()) == set(mine_module._accepted_modes())
    assert not (set(depth.dear_modes()) & set(depth.field_modes()))
    for mode in depth.dear_modes():
        assert not colorize.shareable(mode)


# --------------------------------------------------------------------------- #
# The centered roster: what an arm over the centered population draws.
# --------------------------------------------------------------------------- #
def test_the_centered_roster_is_the_dear_half_and_two_field_modes_less_the_ruling():
    """The eleven arm A ran, minus the one the eye-check sheet took off it.

    Pinned as a derivation and not as a list of names, so a mode that arrives in
    the engine's catalogue and is given a weight joins it without an edit — the
    only thing written out is the exclusion, which is a ruling.
    """
    roster = depth.centered_modes()
    assert set(roster) == (set(depth.dear_modes()) | set(depth.CENTERED_FIELD)) - set(
        depth.CENTERED_EXCLUDED
    )
    assert len(roster) == len(set(roster)), "a cycled roster must not draw a mode twice a turn"
    for mode in depth.CENTERED_FIELD:
        assert colorize.shareable(mode), "the cheap half of this roster is the shareable half"


def test_direct_trap_lines_is_off_the_centered_draw_and_nothing_else():
    """Matt's ruling, 2026-09-02: not a centered mode. A roster is where one arm
    spends and a weight is what a mode is worth, so the mode keeps its standing,
    its seat floor and every row already taken in it — it is out of this draw and
    out of nothing else. A test that let the two move together would make the next
    roster ruling read as a demotion."""
    from fractal_wallpapers.curation import mode_policy

    assert "direct_trap_lines" not in depth.centered_modes()
    assert "direct_trap_lines" in depth.dear_modes(), "still dear, still drawn elsewhere"
    assert mode_policy.weight_of("direct_trap_lines") == mode_policy.NORMAL


def test_every_mode_the_centered_roster_names_is_one_the_project_still_buys():
    """`CENTERED_FIELD` is written out, so it can outlive a weight-0 ruling that
    took one of its members out of every other draw. This is what would catch it."""
    from fractal_wallpapers.curation import mine as mine_module

    assert set(depth.centered_modes()) <= set(mine_module._accepted_modes())


def test_a_place_with_one_dear_attempt_is_out_of_the_untried_population():
    rows = [
        ledger_row("r1", "a", mode="smooth"),
        ledger_row("r2", "b", mode="smooth"),
        ledger_row("r3", "b", mode="threads"),
        ledger_row("r4", "c", mode="exp_smoothing"),
    ]
    assert depth.without_mode_attempt(rows, depth.dear_modes()) == {"a", "c"}


def test_a_place_the_ledger_has_never_opened_is_not_in_it_either():
    """The draw is *opened*-but-shallow. A never-opened place is the breadth
    draws' population and would be counted twice if it were here too."""
    assert depth.without_mode_attempt([ledger_row("r1", "a")], depth.dear_modes()) == {"a"}
    assert "z" not in depth.without_mode_attempt([ledger_row("r1", "a")], depth.dear_modes())


def test_the_floor_draw_narrowed_to_untried_places_leaves_the_tried_ones_out():
    world = a_world()
    world["rows"] = world["rows"] + [ledger_row("t0", "seated-0", mode="threads")]
    plan, shape = depth.build_plan(
        world,
        seed=11,
        rate=0.3,
        budget=600,
        width=8,
        bands=5,
        shares={depth.NEAR: 0.0, depth.RANKED: 0.0, depth.FLAT: 0.0, depth.FLOOR: 1.0},
        floor_modes=["itinerary"],
        floor_untried=depth.dear_modes(),
        floor_width=2,
        log=lambda *_args: None,
    )
    took = {shot.location for shot in plan}
    assert took, "the rest of the seated places are still drawable"
    assert "seated-0" not in took, "one threads attempt takes the place out of this draw"
    assert shape["floor_untried"] == depth.dear_modes()
    assert shape["floor_population"] == len(world["best"]) - 1


# --------------------------------------------------------------------------- #
# The aimed arm over several cells.
# --------------------------------------------------------------------------- #
THIN = ["light_vivid_lime", "dark_vivid_yellow", "light_vivid_teal"]


def test_several_cells_split_the_aimed_arm_and_a_place_is_aimed_at_exactly_one():
    plan, shape = build_a_plan(shares=AIMED_SHARES, cell=THIN)
    aimed = [shot for shot in plan if shot.arm == depth.AIMED]
    assert aimed
    assert {shot.cell for shot in aimed} == set(THIN)
    by_place: dict = {}
    for shot in aimed:
        by_place.setdefault(shot.location, set()).add(shot.cell)
    assert all(len(held) == 1 for held in by_place.values()), "one place, one cell"
    assert shape["cells"] == THIN
    assert shape["cell"] == THIN, "several cells are reported as several"


def test_one_cell_still_reports_itself_as_one_cell():
    _plan, shape = build_a_plan(shares=AIMED_SHARES, cell=["dark_vivid_green"])
    assert shape["cell"] == "dark_vivid_green"
    assert shape["cells"] == ["dark_vivid_green"]


def test_a_cell_the_carrier_table_cannot_serve_is_dropped_at_the_plan_and_named(monkeypatch):
    """The fallback to a flat draw is right for a cell that goes thin mid-run and
    wrong as a plan: it would spend an aimed share on a second control and report
    it as a cell that was served and bought nothing."""
    real = hunt.conditioned_maps
    monkeypatch.setattr(
        hunt,
        "conditioned_maps",
        lambda cell, count, pool, seed: [] if cell == THIN[0] else real(cell, count, pool, seed),
    )
    _plan, shape = build_a_plan(shares=AIMED_SHARES, cell=THIN)
    assert shape["cells_unservable"] == [THIN[0]]
    assert shape["cells"] == THIN[1:]


def test_a_run_whose_every_cell_is_unservable_is_refused_rather_than_drawn_flat(monkeypatch):
    monkeypatch.setattr(hunt, "conditioned_maps", lambda *_a, **_k: [])
    with pytest.raises(depth.DepthRefused, match="serves none of"):
        build_a_plan(shares=AIMED_SHARES, cell=THIN)


def test_the_per_cell_hit_rate_reads_each_cell_against_the_whole_flat_control():
    made = [
        {
            "arm": depth.AIMED,
            "location": "a",
            "colormap": "m1",
            "drawn_for": THIN[0],
            "cells": [THIN[0]],
        },
        {
            "arm": depth.AIMED,
            "location": "b",
            "colormap": "m2",
            "drawn_for": THIN[0],
            "cells": [],
        },
        {
            "arm": depth.AIMED,
            "location": "c",
            "colormap": "m3",
            "drawn_for": THIN[1],
            "cells": [],
        },
        {"arm": depth.FLAT, "location": "d", "colormap": "m9", "cells": [THIN[0]]},
        {"arm": depth.FLAT, "location": "e", "colormap": "m8", "cells": []},
    ]
    out = depth.hit_rate(made, THIN[:2])
    assert set(out["cells"]) == set(THIN[:2])
    first = out["cells"][THIN[0]]
    assert first[depth.AIMED]["candidates"] == 2, "only the shots drawn for this cell"
    assert first[depth.AIMED]["rate"] == pytest.approx(0.5)
    assert first[depth.FLAT]["candidates"] == 2, "and the whole control at every cell"
    assert out["cells"][THIN[1]][depth.AIMED]["candidates"] == 1


def test_the_partition_lean_survives_a_truncation():
    """The bug `overnight_c_pilot` found and the reason it was invisible.

    The draw leaned correctly and the interleave handed every partition one place
    a round, which put the whole surplus in the tail. A production leg is
    clock-bound and truncates, so the tail is never reached: the plan said
    39/38/17 and the leg realized 16-18 across all nine.
    """
    pool = pools({"mandelbrot": 60, "phoenix": 60, "julia:mandelbrot": 60})
    banded = depth.ranked_bands(pool, heads(pool), bands=3)
    weights = {"mandelbrot": 3, "julia:mandelbrot": 3}
    drawn = depth.banded_places(banded, seed=5, count=90, partition_weights=weights)
    whole = {name: sum(1 for row in drawn if row["partition"] == name) for name in pool}
    assert whole["mandelbrot"] > whole["phoenix"], "the draw leans"
    # And the PREFIX leans too, which is the whole point: what a truncated leg
    # takes is a prefix of this order.
    for cut in (18, 36, 54):
        head = drawn[:cut]
        tally = {name: sum(1 for row in head if row["partition"] == name) for name in pool}
        assert tally["mandelbrot"] > tally["phoenix"], (
            f"the first {cut} places came out {tally}, which is the flat spread the "
            f"unweighted interleave used to give"
        )
        assert tally["phoenix"] > 0, "and a lean is never a gate"


def test_an_unweighted_interleave_is_still_one_place_a_partition_a_round():
    places = [{"key": f"{name}-{at}", "partition": name} for name in ("a", "b") for at in range(3)]
    out = depth._interleave_by_partition(places)
    assert [row["partition"] for row in out] == ["a", "b", "a", "b", "a", "b"]


def test_a_weighted_interleave_gives_a_partition_its_turns_a_round():
    places = [{"key": f"{name}-{at}", "partition": name} for name in ("a", "b") for at in range(6)]
    out = depth._interleave_by_partition(places, {"a": 2})
    assert [row["partition"] for row in out][:6] == ["a", "a", "b", "a", "a", "b"]
    assert len(out) == len(places), "and nothing is dropped"


def test_a_zero_weight_at_the_interleave_does_not_starve_a_partition_the_draw_kept():
    places = [{"key": "a-0", "partition": "a"}, {"key": "b-0", "partition": "b"}]
    out = depth._interleave_by_partition(places, {"b": 0})
    assert {row["partition"] for row in out} == {"a", "b"}


def test_the_flat_control_leans_the_same_way_the_ranked_draw_does():
    """Otherwise the control is drawn from a different partition mix than the arm
    it controls, which is the same failure `--centered` avoids one axis up."""
    _plan, shape = build_a_plan(partition_weights={"mandelbrot": 3})
    ranked = shape["ranked_by_partition"]
    flat = shape["flat_wanted_by_partition"]
    assert ranked["mandelbrot"] > ranked["phoenix"]
    assert flat["mandelbrot"] > flat["phoenix"]


def test_a_truncated_aimed_arm_still_holds_every_cell():
    """The bug `overnight_d_pilot` found: the per-cell blocks were concatenated,
    so a leg that stopped early served the leading cells and starved the trailing
    ones. Six cells asked for, 2,570 of 4,240 candidates made, and the last two
    got zero. Every prefix has to hold every cell."""
    plan, shape = build_a_plan(shares=AIMED_SHARES, cell=THIN)
    aimed = [shot for shot in plan if shot.arm == depth.AIMED]
    assert len(aimed) > 3 * len(THIN)
    assert shape["cells"] == THIN
    for share in (0.25, 0.5, 0.75):
        cut = aimed[: max(len(THIN), int(len(aimed) * share))]
        assert {shot.cell for shot in cut} == set(THIN), (
            f"the first {share:.0%} of the aimed arm holds {sorted({s.cell for s in cut})}"
        )


def test_the_aimed_cells_are_cycled_over_places_and_not_blocked():
    plan, _shape = build_a_plan(shares=AIMED_SHARES, cell=THIN)
    aimed = [shot for shot in plan if shot.arm == depth.AIMED]
    by_place: dict = {}
    for shot in aimed:
        by_place.setdefault(shot.location, set()).add(shot.cell)
    assert all(len(held) == 1 for held in by_place.values()), "one place, one cell"
    order = []
    for shot in aimed:
        if not order or order[-1] != shot.cell:
            order.append(shot.cell)
    assert len(order) > len(THIN), (
        "the cell changes many times down the arm; a blocked plan changes it "
        f"{len(THIN)} times and no more"
    )


# --------------------------------------------------------------------------- #
# A leg names a (mode, settings) pair.
# --------------------------------------------------------------------------- #
#: A map pool wide enough that four variants at a place cannot collide by
#: exhaustion — the point being tested is that they draw APART, not that they
#: run out together.
MAPS = [f"map{at}" for at in range(20)]

VARIANTS = [
    "direct_trap_multiply",
    "direct_trap_multiply@opacity=0.6",
    "direct_trap_multiply@threshold=0.2",
    "direct_trap_multiply@opacity=0.6,threshold=0.2",
]


def test_every_variant_at_a_place_draws_its_own_palettes():
    """The failure this hook exists to avoid, pinned.

    Four variants of one mode keyed on the bare name share one seeded sample: the
    same map for all four at every place, and the leg is a comparison of one
    picture against itself. Keyed on `(mode, settings)` each draws as its own
    mode, which is what it is — a different recipe key, a different picture.
    """
    places = pools({"mandelbrot": 3})["mandelbrot"]
    shots = depth.plan_cycled_modes(depth.FLAT, places, VARIANTS, MAPS, seed=5, width=len(VARIANTS))
    by_place: dict = {}
    for shot in shots:
        by_place.setdefault(shot.location, []).append(shot)
    assert by_place, "the draw made nothing"
    for held in by_place.values():
        assert len(held) == len(VARIANTS), "every place gets every variant"
        assert {frozenset(shot.mode_params.items()) for shot in held} == {
            frozenset(depth.entry_of(one)[1].items()) for one in VARIANTS
        }
        assert {shot.mode for shot in held} == {"direct_trap_multiply"}, (
            "the mode stays a catalog name; mode_policy.check pins the roster against "
            "the engine and would refuse an invented one"
        )
        assert len({shot.colormap for shot in held}) > 1, (
            "the four variants drew one map between them, so the leg compares nothing"
        )


def test_a_bare_roster_draws_exactly_what_it_drew_before_settings_existed():
    """The re-seeding this change must not do.

    `spelled` is the bare mode wherever there are no settings, so the palette
    seed, the `taken` key and the plan are byte for byte what they were. A hook
    that moved them would have re-drawn every leg in this project's history into
    a different plan under the same seed.
    """
    places = pools({"mandelbrot": 4})["mandelbrot"]
    roster = ["smooth", "tia"]
    shots = depth.plan_cycled_modes(depth.FLAT, places, roster, MAPS, seed=5, width=6)
    assert shots and all(shot.mode_params == {} for shot in shots)
    assert all("mode_params" not in shot.named() for shot in shots), (
        "a bare draw's ledger row carries no empty settings block"
    )
    # The seed a bare mode draws under is the mode itself, unchanged.
    assert hunt.seed_of(5, places[0]["key"], "smooth") == hunt.seed_of(
        5, places[0]["key"], colorize.spelled("smooth", {})
    )


def test_a_variant_is_not_starved_of_the_maps_the_shipped_mode_already_spent():
    """`taken` is per (mode, settings) too, and this is why it has to be.

    A variant that inherited the shipped mode's spent maps would be refused most
    of the pool at exactly the places that have been mined most — which are the
    places a variant is aimed at. Every row written before settings existed spells
    as its bare mode, so nothing already recorded moves.
    """
    place = pools({"mandelbrot": 1})["mandelbrot"]
    key = place[0]["key"]
    taken = {(key, "direct_trap_multiply"): set(MAPS[:-1])}
    shipped = depth.plan_floor(place, ["direct_trap_multiply"], taken, MAPS, seed=3, width=4)
    varied = depth.plan_floor(
        place, ["direct_trap_multiply@opacity=0.6"], taken, MAPS, seed=3, width=4
    )
    assert len(shipped) == 1, "one map is free at the shipped mode"
    assert len(varied) == 4, "every map is free at a pair nothing has been drawn at"
    assert all(shot.mode_params == {"opacity": 0.6} for shot in varied)


def test_the_ledger_row_carries_the_settings_and_only_when_there_are_some():
    shot = depth.plan_floor(
        pools({"mandelbrot": 1})["mandelbrot"],
        ["direct_trap_multiply@opacity=0.4"],
        {},
        MAPS,
        seed=3,
        width=1,
    )[0]
    assert shot.named()["mode_params"] == {"opacity": 0.4}
    assert shot.named()["mode"] == "direct_trap_multiply"


def test_a_taken_map_table_spells_a_varied_row_apart_from_the_shipped_one():
    """`mine.taken_maps` reads the store, so this is the read side of the same rule."""

    def row(key, mode, params, colormap):
        return {
            "location": {"key": key},
            "recipe": {"mode": mode, "mode_params": params, "colormap": colormap},
        }

    table = mine.taken_maps(
        [
            row("p", "direct_trap_multiply", {}, "viridis"),
            row("p", "direct_trap_multiply", {"opacity": 0.6}, "magma"),
        ]
    )
    assert table[("p", "direct_trap_multiply")] == {"viridis"}
    assert table[("p", "direct_trap_multiply@opacity=0.6")] == {"magma"}


def test_a_places_manifest_is_a_file_of_keys_and_says_so_when_it_is_not(tmp_path):
    """A manifest and never a list of arguments: this population is hundreds long."""
    path = tmp_path / "places.jsonl"
    path.write_text(
        '{"schema": 1, "key": "a"}\n\n{"schema": 1, "key": "b"}\n{"schema": 1, "key": "a"}\n',
        encoding="utf-8",
    )
    assert depth.read_places(path) == ["a", "b"], "duplicates drop and file order holds"

    (tmp_path / "wrong.jsonl").write_text('{"schema": 9, "key": "a"}\n', encoding="utf-8")
    with pytest.raises(depth.DepthRefused):
        depth.read_places(tmp_path / "wrong.jsonl")
    with pytest.raises(depth.DepthRefused):
        depth.read_places(tmp_path / "absent.jsonl")
    (tmp_path / "empty.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(depth.DepthRefused):
        depth.read_places(tmp_path / "empty.jsonl")
