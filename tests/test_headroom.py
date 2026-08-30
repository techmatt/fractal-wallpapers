"""The census: what it counts, what it is allowed to claim, and what it prices.

Every test here runs on **synthetic candidates**, for [`test_solve`]'s reason: a
census is arithmetic over the ledger's own fields, and a test that had to render a
picture to check that two rows at one place count as one location would be a test
nobody runs.

The two things worth pinning hardest are not the arithmetic. They are that counts
are **distinct locations and never rows** — the whole point of the module — and
that the covering condition is stated in the direction that makes it sound: a
short row is provable infeasibility, a row with slack is never a claim that the
selection is possible.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import ceiling, embeddings, headroom, mode_policy, solve


@pytest.fixture(autouse=True)
def no_neutral_store(monkeypatch):
    """An empty neutral embedding store, for every test in this file.

    The pools here are synthetic and no place in them is in the real store, so the
    pre-selection would sweep twenty-nine thousand rows to learn that it can see
    none of them — half a second a test, over dozens of tests. An empty store is
    the same answer for none of the cost, and it exercises the branch that has to
    hold anyway: **a location with no descriptor is admitted, never dropped.** The
    pre-selection's own tests hand in a store of their own.
    """
    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: [])


def candidate(
    key,
    *,
    location=None,
    score=0.9,
    p_ge3=None,
    mode="smooth",
    group=None,
    cells=(),
    families=(),
    partition="mandelbrot",
    kind="smooth_render",
):
    """One synthetic candidate, its own place and its own palette group unless a
    test says otherwise, so a test about one axis is not silently about another."""
    return solve.Candidate(
        key=str(key),
        location=str(location if location is not None else key),
        partition=partition,
        mode=mode,
        group=str(group if group is not None else f"map:{key}"),
        kind=kind,
        cells=tuple(cells),
        families=tuple(families),
        score=float(score),
        p_ge3=float(score if p_ge3 is None else p_ge3),
        picture=f"artifacts/{key}.jpg",
    )


def clearing_pool(count, **rest):
    """`count` candidates that clear the default bar, one location each."""
    return [candidate(f"c{at}", score=0.9, **rest) for at in range(count)]


# --------------------------------------------------------------------------- #
# The bars, per mode.
# --------------------------------------------------------------------------- #
def test_a_mode_over_the_fallback_count_keeps_the_default_bar():
    read = headroom.bars(clearing_pool(headroom.FALLBACK_LOCATIONS))
    assert read["modes"]["smooth"]["rule"] == headroom.DEFAULT_COLUMN
    assert read["modes"]["smooth"]["q4_locations"] == headroom.FALLBACK_LOCATIONS
    assert "smooth" in read["on_default"]


def test_a_mode_one_location_short_of_the_count_falls_back_to_p_ge3():
    read = headroom.bars(clearing_pool(headroom.FALLBACK_LOCATIONS - 1))
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert "smooth" in read["on_fallback"]


def test_the_fallback_is_read_on_p_ge3_and_not_on_the_default_column():
    # Three locations over the q4 bar, so the mode falls back; forty more that
    # clear only P(>=3). The clearing population has to be all forty-three.
    pool = [candidate(f"high{at}", score=0.9) for at in range(3)]
    pool += [candidate(f"low{at}", score=0.1, p_ge3=0.8) for at in range(40)]
    read = headroom.bars(pool)
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert len(headroom.clearing(pool, read)) == 43


def test_a_mode_the_fallback_does_not_rescue_is_still_flagged_thin():
    pool = [candidate(f"c{at}", score=0.1, p_ge3=0.8) for at in range(4)]
    read = headroom.bars(pool)
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert read["modes"]["smooth"]["thin"] is True
    assert "smooth" in read["still_thin"]


def test_the_bars_report_both_columns_for_every_mode_whichever_rule_it_landed_on():
    read = headroom.bars(clearing_pool(3))
    held = read["modes"]["smooth"]
    assert {"q4_rows", "q4_locations", "q3_rows", "q3_locations"} <= set(held)


def test_a_mode_off_the_production_roster_is_counted_and_not_censused():
    read = headroom.bars([candidate("c0", mode="not_a_mode")])
    assert read["off_roster"] == {"not_a_mode": 1}
    assert "not_a_mode" not in read["modes"]


# --------------------------------------------------------------------------- #
# Counts are distinct locations.
# --------------------------------------------------------------------------- #
def test_many_rows_at_one_place_are_one_location_of_supply():
    pool = [candidate(f"c{at}", location="one", cells=("dark_vivid_blue",)) for at in range(60)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    row = next(row for row in block["rows"] if row["about"] == "dark_vivid_blue")
    assert row["rows"] == 60
    assert row["supply"] == 1


def test_the_location_row_counts_places_and_not_rows():
    pool = [candidate(f"c{at}", location=f"place{at % 4}") for at in range(40)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["one_per_location"]
    assert block["supply"] == 4
    assert block["short"] is True
    assert block["slack"] == -16


# --------------------------------------------------------------------------- #
# The covering condition, and the direction it is sound in.
# --------------------------------------------------------------------------- #
def test_the_cover_is_short_when_the_caps_cannot_hold_n_between_them():
    # Two cells, one location each, and at n=20 the per-cell allowance is one. So
    # the axis can hold two seats and the program asks for twenty.
    pool = [
        candidate("a", cells=("dark_vivid_blue",)),
        candidate("b", cells=("dark_vivid_red",)),
    ]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["supply"] == 2
    assert block["short"] is True


def test_a_location_dominant_in_no_cell_counts_toward_the_cover():
    pool = [candidate(f"c{at}", cells=()) for at in range(30)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["dominant_in_none"] == 30
    assert block["short"] is False


def test_the_cover_counts_a_multiply_dominant_location_once_per_cell():
    # The over-count is what makes the condition NECESSARY and never sufficient,
    # so it is pinned rather than fixed: one place in three cells contributes
    # three to the sum, and the block says so.
    pool = [candidate("a", cells=("dark_vivid_blue", "dark_vivid_red", "dark_muted_blue"))]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["usable_from_the_axis"] == 3


def test_the_cap_a_cover_row_carries_is_the_ceilings_own_allowance():
    pool = clearing_pool(4, cells=("dark_vivid_blue",))
    read = headroom.census(pool, ladder=(150,), log=lambda *_: None)
    row = next(
        row
        for row in read["curve"]["150"]["blocks"]["colour_ceiling_cells"]["rows"]
        if row["about"] == "dark_vivid_blue"
    )
    assert row["cap"] == solve.rule_for().allowed("dark_vivid_blue", 150)


# --------------------------------------------------------------------------- #
# The mode floors.
# --------------------------------------------------------------------------- #
def test_a_mode_with_no_clearing_candidate_is_short_at_its_own_floor():
    # At 150 seats the floor is one, which is the smallest n at which the block
    # asks for anything at all.
    read = headroom.census(clearing_pool(3), ladder=(150,), log=lambda *_: None)
    block = read["curve"]["150"]["blocks"]["mode_floors"]
    assert block["floor"] == 1
    row = next(row for row in block["rows"] if row["about"] == "stripe")
    assert row["supply"] == 0
    assert row["short"] is True
    assert "stripe" in block["empty"]


def test_below_a_hundred_seats_the_mode_floors_ask_for_nothing():
    """The `trap_circle` question, retired by arithmetic.

    A flat floor of one put every mode into a twenty-seat gallery, including one
    whose best clearing picture sits at `P(>=4) = 0.066`. `floor(n / 100)` is zero
    there, so the block asks for nothing and no mode is short.
    """
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["mode_floors"]
    assert block["floor"] == 0
    assert block["needs"] == 0
    assert all(row["short"] is False for row in block["rows"])


def test_the_floor_block_counts_places_towards_the_floor_and_not_modes():
    """The bug a flat floor of one could not show.

    Each mode needs `floor` distinct places of its own, so the supply the demand
    is read against is the sum over modes of `min(floor, its places)`. Counting
    modes-that-hold-anything instead is the same number only while the floor is
    one — at n=500 it read one row per mode against a demand of five times the
    roster, and called a pool short that is nowhere near it.
    """
    read = headroom.census(clearing_pool(3), ladder=(500,), log=lambda *_: None)
    block = read["curve"]["500"]["blocks"]["mode_floors"]
    assert block["floor"] == 5
    # The floor is asked of the modes a gallery may seat, not of the whole
    # production roster: a mode weighted 0 has no row in the pool to meet it with.
    assert block["needs"] == 5 * len(mode_policy.accepted())
    # One mode, three places, so three of the five it is asked for.
    assert block["supply"] == 3
    assert block["modes_holding_anything"] == 1
    assert block["short"] is True


def test_the_scaled_floor_always_fits_in_n_and_the_flat_one_did_not():
    # A roster of r modes at floor(n / 100) asks for at most 0.01*r*n, and r is
    # nowhere near a hundred, so the block can never fail to fit — which the flat
    # floor of one did at every n below the roster's size.
    roster = len(mode_policy.accepted())
    read = headroom.census(clearing_pool(3), ladder=(5, 150, 1000), log=lambda *_: None)
    for size in ("5", "150", "1000"):
        assert read["curve"][size]["blocks"]["mode_floors"]["fits_in_n"] is True
    assert solve.mode_floor(5) * roster == 0
    assert solve.mode_floor(1000) * roster == 10 * roster


# --------------------------------------------------------------------------- #
# The group cap, and the flag it does not raise.
# --------------------------------------------------------------------------- #
def test_the_group_cap_is_short_when_there_are_fewer_groups_than_seats():
    pool = [candidate(f"c{at}", group="map:one") for at in range(40)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["palette_group_cap"]
    assert block["supply"] == ceiling.GROUP_CAP
    assert block["short"] is True


def test_the_group_axis_does_not_raise_the_thin_flag():
    # 752 groups mostly holding a handful of places each is the ordinary state of
    # this store and not a finding. The rows still carry their own `thin`.
    pool = clearing_pool(40)
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["palette_group_cap"]
    assert block["flag_thin"] is False
    assert all(row["thin"] for row in block["rows"])
    assert not [item for item in read["curve"]["20"]["flagged"] if item["about"].startswith("map:")]


def test_a_thin_cell_is_flagged_even_with_slack_in_its_own_cap():
    pool = [
        candidate(f"c{at}", cells=("dark_vivid_lime",)) for at in range(headroom.THIN - 1)
    ] + clearing_pool(40, cells=("dark_vivid_blue",))
    read = headroom.census(pool, ladder=(1000,), log=lambda *_: None)
    flagged = {item["about"] for item in read["curve"]["1000"]["flagged"]}
    assert "dark_vivid_lime" in flagged


# --------------------------------------------------------------------------- #
# The default target vector.
# --------------------------------------------------------------------------- #
def test_the_default_vector_demands_no_explicit_colour():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_targets"]
    assert block["needs"] == 0
    assert block["short"] is False


def test_the_default_allowance_is_the_uniform_share_and_not_a_second_copy_of_it():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert (
        str(round(ceiling.CELL_SHARE, 6)) in read["curve"]["20"]["blocks"]["colour_targets"]["rule"]
    )


# --------------------------------------------------------------------------- #
# What one more costs.
# --------------------------------------------------------------------------- #
def test_the_render_cost_is_the_median_of_the_seconds_a_leg_stamped():
    rows = [
        {"recipe": {"mode": "smooth"}, "hunt": {"seconds": value}} for value in (0.1, 0.2, 0.3, 9.0)
    ]
    assert headroom.render_cost(rows)["smooth"]["median"] == pytest.approx(0.25)


def test_a_row_with_no_stamped_seconds_is_not_in_the_denominator():
    rows = [
        {"recipe": {"mode": "smooth"}, "hunt": {"seconds": 0.5}},
        {"recipe": {"mode": "smooth"}, "hunt": {}},
        {"recipe": {"mode": "smooth"}},
    ]
    assert headroom.render_cost(rows)["smooth"]["rows"] == 1


def test_the_marginal_cost_is_renders_per_win_times_the_winners_own_render_cost():
    pool = clearing_pool(4, cells=("dark_vivid_blue",))
    read = headroom.census(
        pool, ladder=(20,), costs={"smooth": {"median": 0.5}}, log=lambda *_: None
    )
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["colour_ceiling_cells"]["rows"]
        if row["about"] == "dark_vivid_blue"
    )
    assert row["renders_per_win"] == pytest.approx(1.0)
    assert row["seconds_per_win"] == pytest.approx(0.5)


def test_a_mode_row_is_priced_against_that_modes_own_renders():
    # Eight renders in `stripe`, two of which clear. The mode's rate is its own
    # 8/2 and never the whole ledger's, which would be 12/2 here.
    pool = clearing_pool(4)
    pool += [candidate(f"s{at}", mode="stripe", score=0.9) for at in range(2)]
    pool += [candidate(f"sl{at}", mode="stripe", score=0.01, p_ge3=0.01) for at in range(6)]
    read = headroom.census(
        pool, ladder=(20,), costs={"stripe": {"median": 1.0}}, log=lambda *_: None
    )
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["mode_floors"]["rows"]
        if row["about"] == "stripe"
    )
    assert row["supply"] == 2
    assert row["renders_per_win"] == pytest.approx(4.0)


def test_a_constraint_with_no_supply_prices_nothing_rather_than_dividing_by_zero():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["mode_floors"]["rows"]
        if row["about"] == "stripe"
    )
    assert row["renders_per_win"] is None
    assert row["seconds_per_win"] is None


# --------------------------------------------------------------------------- #
# What the record is allowed to say.
# --------------------------------------------------------------------------- #
def test_the_census_states_the_only_claim_it_is_making():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert "necessary conditions only" in read["reads"]
    assert "NOT a claim" in read["reads"]


def test_the_curve_costs_what_one_rung_costs_and_reports_every_rung_asked_for():
    read = headroom.census(clearing_pool(3), ladder=(20, 150, 500), log=lambda *_: None)
    assert sorted(read["curve"]) == ["150", "20", "500"]


def test_the_estimator_names_itself_as_unconditioned():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert "UNCONDITIONED" in read["estimator"]


# --------------------------------------------------------------------------- #
# The tracked ledger. Real rows, the real bars, the real curve.
# --------------------------------------------------------------------------- #
@pytest.fixture
def tracked_pool(tracked_ledger):
    """The session's one reading of the ledger. See `conftest.tracked_ledger`."""
    return tracked_ledger.pool, tracked_ledger.costs


@pytest.mark.slow
def test_the_tracked_ledger_censuses_and_every_supply_is_a_location_count(tracked_pool):
    """One real census, end to end, and the one invariant it cannot break.

    No supply figure anywhere may exceed the number of distinct locations in the
    clearing population — which is the whole claim of the module, and the thing a
    row-count leaking into one of these tallies would violate immediately.
    """
    candidates, costs = tracked_pool
    read = headroom.census(candidates, costs=costs, log=lambda *_: None)
    places = read["population"]["clearing_locations"]
    assert 0 < places <= read["population"]["locations"]
    for block in read["curve"]["20"]["blocks"].values():
        for row in block.get("rows", []):
            assert row["supply"] <= places
            assert row["supply"] <= row["rows"] or row["rows"] == 0


@pytest.mark.slow
def test_every_mode_on_the_fallback_really_is_short_of_the_default(tracked_pool):
    """The fallback is a rule about supply and not a preference: a mode that
    landed on it has to have had fewer than the count at the default bar."""
    candidates, _costs = tracked_pool
    read = headroom.bars(candidates)
    for name in read["on_fallback"]:
        assert read["modes"][name]["q4_locations"] < headroom.FALLBACK_LOCATIONS
    for name in read["on_default"]:
        assert read["modes"][name]["q4_locations"] >= headroom.FALLBACK_LOCATIONS


# --------------------------------------------------------------------------- #
# The twin constraint.
# --------------------------------------------------------------------------- #
def test_the_twin_block_is_empty_and_says_so_when_no_sweep_was_handed_in():
    """The one block that cannot be answered from a row, and it is opt-in."""
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["twin_diversity"]
    assert block["short"] is False
    assert "NOT COUNTED" in block["rule"]
    assert "skipped" in read["twin_constraint"]


def test_the_upper_bound_is_the_places_less_a_matching():
    """A chain of four places holds at most two of them, and the matching says so.

    `a-b`, `b-c`, `c-d`: a greedy matching takes `a-b` and `c-d`, so the bound is
    4 - 2 = 2, which is exactly the largest set of pairwise non-twin places here.
    """
    read = headroom.twin_bound(
        ["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")], order=["a", "b", "c", "d"]
    )
    assert read["matching"] == 2
    assert read["upper_bound"] == 2
    assert read["greedy_independent_set"] == 2
    assert read["places_in_a_twin_pair"] == 4


def test_a_pool_with_no_twin_pair_is_bounded_by_its_own_size():
    read = headroom.twin_bound(["a", "b", "c"], [])
    assert read["matching"] == 0
    assert read["upper_bound"] == 3
    assert read["greedy_independent_set"] == 3


def test_a_twin_pair_outside_the_population_is_not_an_edge():
    # The sweep may have been taken over a wider pool than the census counts.
    read = headroom.twin_bound(["a", "b"], [("a", "b"), ("a", "z"), ("y", "z")])
    assert read["twin_pairs"] == 1
    assert read["upper_bound"] == 1


def test_the_bounds_say_which_of_them_is_a_necessary_condition():
    """The direction is the whole safety argument and it is on the record."""
    read = headroom.twin_bound(["a", "b"], [("a", "b")])
    assert "NECESSARY" in read["bounds"]
    assert "CONSTRUCTIVE" in read["bounds"]
    assert "one picture per place" in read["measured_over"]


def test_the_twin_block_is_short_when_the_bound_falls_under_n():
    swept = {
        "tau": ceiling.TAU,
        "places": 3,
        "pairs_screened": 3,
        "pairs": [{"a": "c0", "b": "c1"}, {"a": "c1", "b": "c2"}],
    }
    read = headroom.census(clearing_pool(3), ladder=(2, 20), twins=swept, log=lambda *_: None)
    assert read["curve"]["2"]["blocks"]["twin_diversity"]["supply"] == 2
    assert read["curve"]["2"]["blocks"]["twin_diversity"]["short"] is False
    assert read["curve"]["20"]["blocks"]["twin_diversity"]["short"] is True


# --------------------------------------------------------------------------- #
# The neutral pre-selection, at pool construction.
# --------------------------------------------------------------------------- #
def test_the_census_records_the_preselection_it_was_taken_over():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert read["preselection"]["radius"] == headroom.distinct.PRESELECT_RADIUS
    assert read["preselection"]["admitted_without_a_descriptor"] == 3
    assert read["population"]["after_the_preselection"] == 3


def test_a_census_without_the_preselection_says_it_was_not_applied():
    read = headroom.census(clearing_pool(3), ladder=(20,), radius=None, log=lambda *_: None)
    assert "skipped" in read["preselection"]
