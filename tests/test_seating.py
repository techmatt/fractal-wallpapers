"""The greedy: what it seats first, what it refuses, and what it records about it.

Synthetic candidates throughout, for [`test_headroom`]'s reason — the seating
reads colour, group, mode and score off the row and opens no picture, so nothing
here needs one.

The finding this file exists to pin is **fill by scarcity**. A walk down the
ranked list turns a satisfiable problem into an apparent infeasibility whenever
the mandated constraints are thin, and that is the ordinary state of this pool:
eighteen mode floors against twenty seats, eleven of the modes with a handful of
places each. `test_score_order_would_have_lost_the_thin_modes` is that failure
written down, and the two tests around it are the fix.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import candidate_ledger, ceiling, headroom, seating, solve


def modes_of(record) -> set:
    return {seat["mode"] for seat in record["seated"]}


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing, so a suite of two thousand tests stays readable."""


# --------------------------------------------------------------------------- #
# Fill by scarcity.
# --------------------------------------------------------------------------- #
def deep_and_shallow():
    """Two hundred `smooth` candidates and one each of two other modes.

    The shape the whole design is about: a mode with more supply than the gallery
    has seats, beside modes that can be seated exactly once.
    """
    pool = [candidate(f"deep{at}", mode="smooth", score=0.99) for at in range(200)]
    pool += [candidate("thin1", mode="stripe", score=0.60)]
    pool += [candidate("thin2", mode="threads", score=0.55)]
    return pool


def test_the_thin_modes_are_seated_before_the_deep_one():
    record = seating.seat(deep_and_shallow(), n=5, log=quiet)
    assert {"stripe", "threads"} <= modes_of(record)


def test_score_order_would_have_lost_the_thin_modes():
    # The failure the scarcity order exists to prevent, stated as arithmetic: the
    # five strongest candidates are all `smooth`, so a walk down the ranked list
    # seats five of one mode and reports two modes it could have held.
    ranked = sorted(deep_and_shallow(), key=lambda held: -held.score)[:5]
    assert {held.mode for held in ranked} == {"smooth"}


def test_the_scarcest_mandate_is_taken_first():
    pool = [candidate(f"a{at}", mode="smooth") for at in range(9)]
    pool += [candidate(f"b{at}", mode="stripe") for at in range(3)]
    pool += [candidate("c0", mode="threads")]
    order = [name for name, members in seating.scarcity(pool, ["smooth", "stripe", "threads"])]
    assert order == ["threads", "stripe", "smooth"]


def test_a_mode_with_nothing_at_all_stays_in_the_scarcity_order():
    order = dict(seating.scarcity([candidate("a")], ["smooth", "itinerary"]))
    assert order["itinerary"] == []


def test_a_seat_taken_for_a_mode_floor_says_which_floor_it_was_taken_for():
    record = seating.seat(deep_and_shallow(), n=5, log=quiet)
    taken = {seat["seated_for"] for seat in record["seated"]}
    assert "mode_floor:stripe" in taken
    assert "general_pool" in taken


# --------------------------------------------------------------------------- #
# One rule is hard.
# --------------------------------------------------------------------------- #
def test_two_candidates_at_one_place_cannot_both_be_seated():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = seating.seat(pool, n=5, log=quiet)
    assert record["filled"] == 1
    assert record["unfilled"] == 4


def test_the_hard_rule_is_never_relaxed_to_fill_a_seat():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = seating.seat(pool, n=5, log=quiet)
    assert len({seat["location"] for seat in record["seated"]}) == record["filled"]
    assert "relaxing a rule it failed" in record["config"]["no_fallback"]


# --------------------------------------------------------------------------- #
# The soft rules record a shortfall rather than repairing one.
# --------------------------------------------------------------------------- #
def test_the_group_cap_refuses_a_second_seat_in_one_group():
    pool = [candidate(f"c{at}", group="map:one") for at in range(10)]
    record = seating.seat(pool, n=5, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["group_cap"] >= 1


def test_the_cell_allowance_refuses_past_the_ceilings_own_arithmetic():
    # At n=20 the per-cell allowance is one, so twenty candidates all dominant in
    # one cell seat exactly one of themselves.
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    assert solve.rule_for().allowed("dark_vivid_blue", 20) == 1
    record = seating.seat(pool, n=20, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["cell_allowance"] == 19


def test_an_unseated_mode_is_a_recorded_shortfall_and_not_a_refusal():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["held"] == 1
    assert "stripe" in shortfall["missing"]


def test_the_shortfall_block_says_a_greedy_shortfall_is_not_infeasibility():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    assert "never" in record["shortfalls"]["read"]
    assert "does not hold it" in record["shortfalls"]["read"]


def test_an_unfilled_seat_is_left_unfilled_rather_than_padded():
    record = seating.seat([candidate("a"), candidate("b")], n=20, log=quiet)
    assert record["filled"] == 2
    assert record["unfilled"] == 18
    assert len(record["seated"]) == 2


# --------------------------------------------------------------------------- #
# The rejection ledger.
# --------------------------------------------------------------------------- #
def test_every_candidate_not_seated_carries_exactly_one_reason():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    record = seating.seat(pool, n=20, log=quiet)
    assert sum(record["rejection"]["reasons"].values()) == len(pool) - record["filled"]


def test_the_first_rule_to_fail_is_the_one_recorded():
    # One place, one group, one cell: `location` is first in RULES and is what the
    # ledger has to say, otherwise the aggregate double-counts.
    pool = [
        candidate("a", location="one", group="map:one", cells=("dark_vivid_blue",)),
        candidate("b", location="one", group="map:one", cells=("dark_vivid_blue",)),
    ]
    record = seating.seat(pool, n=20, log=quiet)
    assert record["rejection"]["reasons"] == {"location": 1}


def test_a_candidate_below_its_modes_bar_is_not_recorded_as_refused_by_a_rule():
    pool = [candidate("a", score=0.9)] + [
        candidate(f"low{at}", score=0.01, p_ge3=0.01) for at in range(30)
    ]
    record = seating.seat(pool, n=20, log=quiet)
    assert record["rejection"]["reasons"][seating.BELOW_BAR] == 30
    assert set(record["rejection"]["reasons"]) <= {seating.BELOW_BAR}


def test_a_candidate_that_arrived_after_the_seats_ran_out_broke_no_rule():
    pool = [candidate(f"c{at}") for at in range(30)]
    record = seating.seat(pool, n=5, log=quiet)
    assert record["rejection"]["reasons"][seating.UNSEATED] == 25


def test_the_ledger_aggregates_by_cell_family_mode_and_partition():
    pool = [
        candidate(f"c{at}", cells=("dark_vivid_blue",), families=("blue",), partition="julia")
        for at in range(20)
    ]
    record = seating.seat(pool, n=20, log=quiet)
    by = record["rejection"]["by"]
    assert by["cells"]["dark_vivid_blue"]["rows"]["cell_allowance"] == 19
    assert by["families"]["blue"]["rows"]["cell_allowance"] == 19
    assert by["modes"]["smooth"]["rows"]["cell_allowance"] == 19
    assert by["partitions"]["julia"]["rows"]["cell_allowance"] == 19


def test_the_ledger_counts_distinct_locations_beside_the_rows():
    pool = [
        candidate(f"c{at}", location=f"place{at % 3}", cells=("dark_vivid_blue",))
        for at in range(20)
    ]
    record = seating.seat(pool, n=20, log=quiet)
    cell = record["rejection"]["by"]["cells"]["dark_vivid_blue"]
    assert cell["rows"]["location"] + cell["rows"].get("cell_allowance", 0) == 19
    assert max(cell["locations"].values()) <= 3


# --------------------------------------------------------------------------- #
# What it does not do.
# --------------------------------------------------------------------------- #
def test_the_seating_applies_no_pairwise_rule():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    assert "NOT applied" in record["config"]["pairwise"]


def test_the_lens_reads_the_row_and_never_decodes_a_picture():
    stored = [
        {
            "key": "a",
            "picture": "artifacts/a.jpg",
            "colour": {"cells": ["dark_vivid_blue"], "families": ["blue"]},
        }
    ]
    lens = seating.lens_for(stored)
    reading = lens._read("artifacts/a.jpg")
    assert reading is not None
    assert lens.taken == {"stored": 1, "decoded": 0}


def test_a_lens_over_a_row_the_ledger_never_saw_decodes_nothing_either():
    # `render_of` answers None for every candidate here, so an unknown picture
    # reads as no colour rather than sending a seating to a JPEG it has no path to.
    lens = seating.lens_for([])
    assert lens._read(None) is None


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #
def test_the_config_names_the_bar_each_mode_landed_on():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    assert record["config"]["bars"]["smooth"] in {
        headroom.DEFAULT_COLUMN,
        headroom.FALLBACK_COLUMN,
    }


def test_the_config_states_the_ceilings_own_constants_and_not_a_copy():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    assert record["config"]["ceiling"]["k"] == ceiling.K
    assert record["config"]["ceiling"]["group_cap"] == ceiling.GROUP_CAP
    assert record["config"]["mode_floor"] == solve.MODE_FLOOR


def test_the_default_seat_count_is_the_first_solve():
    record = seating.seat([candidate("a")], log=quiet)
    assert record["config"]["n"] == candidate_ledger.FIRST_SOLVE


def test_the_samples_are_the_strongest_of_each_rule():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",), score=at / 100.0) for at in range(60)]
    record = seating.seat(pool, n=20, log=quiet)
    shown = record["samples"]["cell_allowance"]
    assert len(shown) == seating.SHOWN
    assert [row["p_ge4"] for row in shown] == sorted((row["p_ge4"] for row in shown), reverse=True)


# --------------------------------------------------------------------------- #
# The tracked ledger. Real rows, the real greedy.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def tracked_pool():
    if not candidate_ledger.rows_path().is_file():
        pytest.skip("the candidate ledger has not been backfilled on this machine")
    candidates, _costs, _refused = headroom.population(log=quiet)
    return candidates


@pytest.mark.slow
def test_the_tracked_pool_seats_and_the_ledger_partitions_it(tracked_pool):
    """One real seating, and the invariant the rejection ledger exists for: every
    candidate is seated exactly once or refused for exactly one reason.

    A ledger that double-counted would inflate whichever axis it double-counted
    on, and that aggregate is what a leg would be aimed down.
    """
    record = seating.seat(tracked_pool, n=20, log=quiet)
    assert record["filled"] + sum(record["rejection"]["reasons"].values()) == len(tracked_pool)
    assert len({seat["location"] for seat in record["seated"]}) == record["filled"]


@pytest.mark.slow
def test_the_real_seating_breaks_no_rule_it_recorded_as_soft(tracked_pool):
    """Soft means the shortfall is recorded, never that the rule is exceeded: a
    greedy that passes over a candidate cannot end up over an allowance."""
    record = seating.seat(tracked_pool, n=20, log=quiet)
    assert record["shortfalls"]["cells"]["over_allowance"] == {}
    assert record["shortfalls"]["families"]["over_allowance"] == {}
    assert record["shortfalls"]["groups"]["over_cap"] == {}
