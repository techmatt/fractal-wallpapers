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

from fractal_wallpapers.curation import (
    candidate_ledger,
    ceiling,
    distinct,
    embeddings,
    headroom,
    mode_policy,
    seating,
    solve,
)


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
    # An artificial floor of one, because `solve.mode_floor(5)` is zero and the
    # scarcity leg is what this file exists to pin.
    record = seating.seat(deep_and_shallow(), n=5, floor=1, key=seating.JUDGE_KEY, log=quiet)
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
    record = seating.seat(deep_and_shallow(), n=5, floor=1, key=seating.JUDGE_KEY, log=quiet)
    taken = {seat["seated_for"] for seat in record["seated"]}
    assert "mode_floor:stripe" in taken
    assert "general_pool" in taken


# --------------------------------------------------------------------------- #
# One rule is hard.
# --------------------------------------------------------------------------- #
def test_two_candidates_at_one_place_cannot_both_be_seated():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["unfilled"] == 4


def test_the_hard_rule_is_never_relaxed_to_fill_a_seat():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert len({seat["location"] for seat in record["seated"]}) == record["filled"]
    assert "relaxing a rule it failed" in record["config"]["no_fallback"]


# --------------------------------------------------------------------------- #
# The soft rules record a shortfall rather than repairing one.
# --------------------------------------------------------------------------- #
def test_the_group_cap_refuses_a_second_seat_in_one_group():
    pool = [candidate(f"c{at}", group="map:one") for at in range(10)]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["group_cap"] >= 1


def test_the_proportional_cap_seats_three_of_one_group_at_n_150():
    """`max(1, floor(0.025 * 150))` is three, and the flag is what selects it.

    One group, forty places, and nothing else in the pool: under the identity cap
    the gallery is one seat wide, under the proportional one it is three. Both
    numbers come out of the same walk over the same rows.
    """
    pool = [candidate(f"c{at}", group="map:one") for at in range(40)]
    incumbent = seating.seat(
        pool, n=150, group_cap=ceiling.IDENTITY, key=seating.JUDGE_KEY, log=quiet
    )
    proportional = seating.seat(
        pool, n=150, group_cap=ceiling.PROPORTIONAL, key=seating.JUDGE_KEY, log=quiet
    )
    assert incumbent["filled"] == 1
    assert proportional["filled"] == 3
    assert proportional["config"]["ceiling"]["group_cap"] == 3


def test_the_record_says_what_the_cap_actually_bound_to_and_not_only_what_it_was():
    """A cap of three is only a cap of three if something spent it. The ruling
    that raised it asked for the realized maximum to be reported rather than
    assumed, because a key that prefers good maps will want to spend it all."""
    pool = [candidate(f"c{at}", group="map:one") for at in range(40)]
    pool += [candidate("solo", group="map:two")]
    record = seating.seat(
        pool, n=150, group_cap=ceiling.PROPORTIONAL, key=seating.JUDGE_KEY, log=quiet
    )
    groups = record["shortfalls"]["groups"]
    assert (groups["realized_max"], groups["cap"]) == (3, 3)
    assert groups["at_the_cap"] == 1
    assert groups["over_cap"] == {}


def test_the_cap_a_seating_ran_under_is_on_its_record_by_name():
    """`group_cap: 1` on a record does not say which rule produced it, and at
    n=20 both rules produce it."""
    record = seating.seat(
        [candidate("a")], n=20, group_cap=ceiling.PROPORTIONAL, key=seating.JUDGE_KEY, log=quiet
    )
    assert record["config"]["ceiling"]["group_cap"] == 1
    assert record["config"]["ceiling"]["group_cap_rule"] == ceiling.PROPORTIONAL


def test_an_unflagged_seating_now_takes_the_proportional_cap_and_the_fitted_key():
    """Both defaults flipped on 2026-08-28 and the incumbent stayed reachable.

    The cap half is checked here on the walk itself; the key half is checked on
    the parameter rather than on a resolved order, because resolving one reads two
    stores and this is a fast-lane test about a default and not about a fit.
    """
    import inspect

    record = seating.seat([candidate("a")], n=150, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["ceiling"]["group_cap"] == ceiling.group_cap(150, ceiling.PROPORTIONAL)
    assert record["config"]["ceiling"]["group_cap_rule"] == ceiling.PROPORTIONAL
    signature = inspect.signature(seating.seat).parameters
    assert signature["group_cap"].default == seating.DEFAULT_GROUP_CAP == ceiling.PROPORTIONAL
    assert signature["key"].default == seating.DEFAULT_KEY == seating.RANK_KEY
    incumbent = seating.seat(
        [candidate("a")], n=150, group_cap=ceiling.IDENTITY, key=seating.JUDGE_KEY, log=quiet
    )
    assert incumbent["config"]["ceiling"]["group_cap"] == ceiling.GROUP_CAP
    assert incumbent["config"]["ceiling"]["group_cap_rule"] == ceiling.IDENTITY
    assert incumbent["config"]["sort_key"] == "p_ge4"


def test_the_judge_key_resolves_to_no_order_and_an_unknown_key_is_refused():
    """[`ranking_for`] is the one place a seating pays for its key, and it is the
    one place a name that is not a key is caught — before a pool is walked."""
    order, coverage = seating.ranking_for([candidate("a")], seating.JUDGE_KEY)
    assert (order, coverage) == (None, None)
    with pytest.raises(seating.SeatingRefused):
        seating.ranking_for([candidate("a")], "whatever_matt_meant")


def test_the_coverage_the_key_reported_lands_on_the_record():
    """A seating on a fitted key that could read four rows of five is a different
    seating from one that read all five, and the record has to say which."""
    coverage = {"key": "rank_key", "ranked": 1, "unranked": 0}
    record = seating.seat([candidate("a")], n=1, order={"a": 0.5}, coverage=coverage, log=quiet)
    assert record["order"]["coverage"] == coverage
    assert record["order"]["key"] == "rank_key"


def test_the_cell_allowance_refuses_past_the_ceilings_own_arithmetic():
    # At n=20 the per-cell allowance is one, so twenty candidates all dominant in
    # one cell seat exactly one of themselves.
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    assert solve.rule_for().allowed("dark_vivid_blue", 20) == 1
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["cell_allowance"] == 19


def test_an_unseated_mode_is_a_recorded_shortfall_and_not_a_refusal():
    record = seating.seat([candidate("a")], n=20, floor=1, key=seating.JUDGE_KEY, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["represented"] == 1
    assert "stripe" in shortfall["below_the_floor"]


def test_the_mode_block_counts_representation_apart_from_the_floor():
    """Held-against-the-floor is not held, and the two are further apart than ever.

    Under the flat floor this read a vacuous floor of zero at twenty seats and
    would have called a one-candidate pool `18 of 18 held`. Under the per-mode
    rule the floor at twenty is real — six strange modes at one seat each — so the
    same pool is below six floors while holding one mode, and the block has to say
    both. `floor` is `None` because the modes do not all ask for the same thing.
    """
    asked = {name: seats for name, seats in mode_policy.seat_floors(20).items() if seats}
    record = seating.seat([candidate("a")], n=20, key=seating.JUDGE_KEY, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["floor"] is None
    assert shortfall["floors_are"] == "per mode"
    assert shortfall["asked"] == sum(asked.values())
    assert shortfall["represented"] == 1
    assert set(shortfall["below_the_floor"]) == set(asked)


def test_the_shortfall_block_says_a_greedy_shortfall_is_not_infeasibility():
    record = seating.seat([candidate("a")], n=20, key=seating.JUDGE_KEY, log=quiet)
    assert "never" in record["shortfalls"]["read"]
    assert "does not hold it" in record["shortfalls"]["read"]


def test_an_unfilled_seat_is_left_unfilled_rather_than_padded():
    record = seating.seat([candidate("a"), candidate("b")], n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["filled"] == 2
    assert record["unfilled"] == 18
    assert len(record["seated"]) == 2


# --------------------------------------------------------------------------- #
# The rejection ledger.
# --------------------------------------------------------------------------- #
def test_every_candidate_not_seated_carries_exactly_one_reason():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    assert sum(record["rejection"]["reasons"].values()) == len(pool) - record["filled"]


def test_the_first_rule_to_fail_is_the_one_recorded():
    # One place, one group, one cell: `location` is first in RULES and is what the
    # ledger has to say, otherwise the aggregate double-counts.
    pool = [
        candidate("a", location="one", group="map:one", cells=("dark_vivid_blue",)),
        candidate("b", location="one", group="map:one", cells=("dark_vivid_blue",)),
    ]
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"] == {"location": 1}


def test_a_candidate_below_its_modes_bar_is_not_recorded_as_refused_by_a_rule():
    pool = [candidate("a", score=0.9)] + [
        candidate(f"low{at}", score=0.01, p_ge3=0.01) for at in range(30)
    ]
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"][seating.BELOW_BAR] == 30
    assert set(record["rejection"]["reasons"]) <= {seating.BELOW_BAR}


def test_a_candidate_that_arrived_after_the_seats_ran_out_broke_no_rule():
    pool = [candidate(f"c{at}") for at in range(30)]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"][seating.UNSEATED] == 25


def test_the_ledger_aggregates_by_cell_family_mode_and_partition():
    pool = [
        candidate(f"c{at}", cells=("dark_vivid_blue",), families=("blue",), partition="julia")
        for at in range(20)
    ]
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
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
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    cell = record["rejection"]["by"]["cells"]["dark_vivid_blue"]
    assert cell["rows"]["location"] + cell["rows"].get("cell_allowance", 0) == 19
    assert max(cell["locations"].values()) <= 3


# --------------------------------------------------------------------------- #
# What it does not do.
# --------------------------------------------------------------------------- #
def test_the_seating_applies_the_pairwise_rule_and_the_solve_does_not_change():
    record = seating.seat([candidate("a")], n=20, key=seating.JUDGE_KEY, log=quiet)
    assert "APPLIED" in record["config"]["pairwise"]
    assert record["config"]["rules"][-1] == "twin"
    assert "the twin test" in record["config"]["hard"]
    assert record["twins"]["tau"] == ceiling.TAU


def test_a_seating_asked_for_without_the_twin_test_says_so():
    record = seating.seat([candidate("a")], n=20, twin=False, key=seating.JUDGE_KEY, log=quiet)
    assert "NOT applied" in record["config"]["pairwise"]
    assert record["twins"] is None


def test_the_config_names_the_bar_each_mode_landed_on():
    record = seating.seat([candidate("a")], n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["bars"]["smooth"] in {
        headroom.DEFAULT_COLUMN,
        headroom.FALLBACK_COLUMN,
    }


def test_the_config_states_the_ceilings_own_constants_and_not_a_copy():
    record = seating.seat([candidate("a")], n=20, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["ceiling"]["k"] == ceiling.K
    assert record["config"]["ceiling"]["group_cap"] == ceiling.GROUP_CAP
    assert record["config"]["mode_floor"] is None, "the default floors are per mode"
    assert record["config"]["mode_floor_artificial"] is False


# --------------------------------------------------------------------------- #
# The sort key.
# --------------------------------------------------------------------------- #
def test_an_order_walks_the_pool_in_its_own_key_and_not_the_judges():
    """The whole of what the flag does: the same pool, the same rules, one seat,
    and which candidate takes it is the key's answer rather than `P(>=4)`'s."""
    # `p_ge3` high on both, so the fallback bar admits them and this test is
    # about the ORDER rather than about which of them cleared.
    pool = [candidate("weak", score=0.10, p_ge3=0.99), candidate("strong", score=0.99)]
    assert [
        seat["key"] for seat in seating.seat(pool, n=1, key=seating.JUDGE_KEY, log=quiet)["seated"]
    ] == ["strong"]
    flipped = seating.seat(pool, n=1, order={"weak": 0.9, "strong": 0.1}, log=quiet)
    assert [seat["key"] for seat in flipped["seated"]] == ["weak"]


def test_the_key_moves_the_order_and_never_the_bars():
    """A candidate below its mode's bar stays below it however the key ranks it.
    Every bar in this project reads the judge's own columns, and that is what
    makes a before/after on the key exact in the sort order alone."""
    pool = [candidate(f"c{at}", score=0.9) for at in range(5)]
    pool += [candidate("under", score=0.01)]
    record = seating.seat(pool, n=6, order={"under": 1.0}, allow_unranked=True, log=quiet)
    assert "under" not in {seat["key"] for seat in record["seated"]}
    assert record["rejection"]["reasons"][seating.BELOW_BAR] == 1


def test_a_candidate_the_key_cannot_read_is_ranked_last_and_counted_never_refused():
    """It broke no rule, so it is not a refusal; and it did not score badly, so it
    is not a zero. Sorted last, and the count is on the record."""
    pool = [candidate("read", score=0.5), candidate("unread", score=0.99)]
    record = seating.seat(pool, n=1, order={"read": 0.01}, allow_unranked=True, log=quiet)
    assert [seat["key"] for seat in record["seated"]] == ["read"]
    assert record["order"]["unranked"] == 1
    assert record["rejection"]["reasons"].get("group_cap") is None


def test_the_mode_floor_leg_walks_the_same_key_as_the_general_leg():
    """A mode floor spent by the judge's order while everything else went by
    another key would be a gallery seated two ways."""
    pool = [candidate(f"deep{at}", mode="smooth", score=0.99) for at in range(5)]
    pool += [candidate("thin_weak", mode="stripe", score=0.60)]
    pool += [candidate("thin_strong", mode="stripe", score=0.95)]
    order = {"thin_weak": 0.99, "thin_strong": 0.01}
    record = seating.seat(pool, n=3, floor=1, order=order, allow_unranked=True, log=quiet)
    taken = {seat["key"]: seat["seated_for"] for seat in record["seated"]}
    assert taken.get("thin_weak") == "mode_floor:stripe"


def test_each_seat_carries_the_value_its_own_key_gave_it_beside_p_ge4():
    record = seating.seat([candidate("a", score=0.5)], n=1, order={"a": 0.25}, log=quiet)
    seat = record["seated"][0]
    assert (seat["rank"], seat["p_ge4"]) == (0.25, 0.5)
    assert record["config"]["sort_key"] == "rank_key"


def test_a_seating_on_the_judge_alone_says_so_and_carries_no_rank():
    record = seating.seat([candidate("a", score=0.5)], n=1, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["sort_key"] == "p_ge4"
    assert record["seated"][0]["rank"] is None
    assert record["order"]["key"] == "p_ge4"


def test_the_contact_sheet_is_sorted_good_to_bad_by_the_seatings_own_key(tmp_path):
    """A sheet in seating order is in SCARCITY order for its first seats, which
    reads as a quality claim it is not making."""
    pool = [candidate(f"c{at}", score=0.5 + at / 100.0) for at in range(4)]
    order = {"c0": 0.9, "c1": 0.1, "c2": 0.8, "c3": 0.2}
    record = seating.seat(pool, n=4, order=order, log=quiet)
    where = seating.contact_sheet("under-test", record, output=tmp_path / "sheet.html")
    page = where.read_text(encoding="utf-8")
    captions = [f"{at}. rank_key {value:.4f}" for at, value in enumerate([0.9, 0.8, 0.2, 0.1], 1)]
    assert all(caption in page for caption in captions)
    assert [page.index(caption) for caption in captions] == sorted(
        page.index(caption) for caption in captions
    )


def test_the_default_seat_count_is_the_first_solve():
    record = seating.seat([candidate("a")], key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["n"] == candidate_ledger.FIRST_SOLVE


def test_the_samples_are_the_strongest_of_each_rule():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",), score=at / 100.0) for at in range(60)]
    record = seating.seat(pool, n=20, key=seating.JUDGE_KEY, log=quiet)
    shown = record["samples"]["cell_allowance"]
    assert len(shown) == seating.SHOWN
    assert [row["p_ge4"] for row in shown] == sorted((row["p_ge4"] for row in shown), reverse=True)


# --------------------------------------------------------------------------- #
# The leg attribution — the mining list.
# --------------------------------------------------------------------------- #
def test_every_seat_carries_its_percentile_in_the_clearing_pool_and_the_leg_that_placed_it():
    """The two facts the next mine is aimed with. The percentile is against the
    CLEARING pool and not the pre-selected one: the pre-selection refuses places,
    so a percentile against what survived it is measured against a population no
    mine can aim at."""
    pool = [candidate(f"c{at}", score=at / 100.0) for at in range(100)]
    record = seating.seat(pool, n=10, radius=None, key=seating.JUDGE_KEY, log=quiet)
    top = record["seated"][0]
    assert top["leg"] == "general_pool"
    # Fifty of the hundred clear the bar at 0.50, so the strongest sits one place
    # from the top of a fifty-row pool and never of the pool that was handed in.
    assert top["rank_percentile"] == 98.0
    assert record["attribution"]["clearing_pool"]["candidates"] == 50
    assert record["attribution"]["by_leg"]["general_pool"]["seats"] == 10
    assert record["attribution"]["by_seated_for"] == {"general_pool": 10}


def test_a_seat_the_scarcity_leg_placed_is_attributed_to_the_mode_floor_and_not_the_walk():
    """The whole point of the block: a floor spending a seat deep in the tail is
    visible as a LEG rather than as one weak picture somebody has to notice."""
    pool = [candidate(f"strong{at}", score=0.9, mode="smooth") for at in range(20)]
    pool += [candidate("thin_weak", score=0.51, mode="stripe")]
    record = seating.seat(pool, n=3, floor=1, radius=None, key=seating.JUDGE_KEY, log=quiet)
    placed = {row["key"]: (row["leg"], row["seated_for"]) for row in record["seated"]}
    assert placed["thin_weak"] == ("mode_floor", "mode_floor:stripe")
    assert seating.leg_of("general_pool") == "general_pool"
    assert set(record["attribution"]["legs"]) == {"mode_floor", "general_pool"}


def test_the_bottom_quartile_is_a_quarter_of_the_SEATS_and_names_its_legs():
    pool = [candidate(f"c{at}", score=at / 100.0) for at in range(100)]
    record = seating.seat(pool, n=20, radius=None, key=seating.JUDGE_KEY, log=quiet)
    weak = record["attribution"]["bottom_quartile"]
    assert weak["share"] == seating.BOTTOM_QUARTILE
    assert weak["seat_count"] == 5
    assert sum(weak["by_leg"].values()) == 5
    assert len(weak["seats"]) == 5
    assert [row["rank_percentile"] for row in weak["seats"]] == sorted(
        row["rank_percentile"] for row in weak["seats"]
    )


def test_a_candidate_the_key_cannot_read_counts_at_the_bottom_of_every_percentile():
    """It sorts last in the walk, so anything else here would inflate every
    percentile by the size of the hole."""
    pool = [candidate(f"c{at}", score=0.9) for at in range(4)]
    record = seating.seat(pool, n=1, radius=None, order={"c0": 0.5}, allow_unranked=True, log=quiet)
    assert record["attribution"]["clearing_pool"]["unreadable_by_the_key"] == 3
    assert record["seated"][0]["rank_percentile"] == 75.0


def test_the_weak_cells_and_the_full_cells_are_two_lists_and_not_one():
    """A cell at its allowance and a cell whose best row is weak are OPPOSITE
    instructions to a mine, so they are never in the same list."""
    # At n=150 the per-cell allowance is seven, so nine blue candidates spend it
    # and one lime candidate does not. At n=20 every allowance is one and the two
    # lists would be the same list.
    pool = [candidate(f"strong{at}", cells=("dark_vivid_blue",), score=0.9) for at in range(9)]
    pool += [candidate("weak", cells=("dark_muted_lime",), score=0.51)]
    record = seating.seat(pool, n=150, radius=None, key=seating.JUDGE_KEY, log=quiet)
    weakest = record["attribution"]["best_available"]["cells"][0]
    assert weakest["name"] == "dark_muted_lime"
    assert weakest["best_percentile"] == 0.0
    assert weakest["cleared_rows"] == 1
    assert "dark_vivid_blue" in record["attribution"]["binding"]["cells_at_the_allowance"]
    assert "dark_muted_lime" not in record["attribution"]["binding"]["cells_at_the_allowance"]


def test_only_a_constraint_that_CAN_go_unmet_is_reported_as_short():
    """Seats and mode floors can go unmet. An allowance and a cap are ceilings: a
    seating binds against one, it cannot fall short of one."""
    pool = [candidate("a", mode="smooth")]
    record = seating.seat(pool, n=5, floor=1, radius=None, key=seating.JUDGE_KEY, log=quiet)
    unmet = {row["constraint"]: row for row in record["attribution"]["unmet"]}
    assert unmet["seats"]["short"] == 4
    assert unmet["mode_floor:stripe"] == {
        "constraint": "mode_floor:stripe",
        "asked": 1,
        "held": 0,
        "short": 1,
    }
    assert not any(row["constraint"].startswith("cell") for row in record["attribution"]["unmet"])


# --------------------------------------------------------------------------- #
# The release leg, and the sheet of what it made.
# --------------------------------------------------------------------------- #
def test_the_act_rate_denominator_is_the_seats_the_operator_was_ASKED_about():
    """A direct-trap seat is never asked, so it belongs in neither half. A bare
    percentage over all the seats would report the operator as quieter than it is."""
    record = {
        "seated": [
            {"key": "a", "release_autolevel": {"acted": True}},
            {"key": "b", "release_autolevel": {"acted": False}},
            {"key": "c", "release_autolevel": None},
        ]
    }
    rate = seating.autolevel_rate(record)
    assert (rate["seats"], rate["asked"], rate["acted"]) == (3, 2, 1)
    assert (rate["rate"], rate["not_asked"]) == (0.5, 1)
    assert seating.autolevel_rate({"seated": []})["rate"] is None


def test_the_sheet_shows_the_released_picture_where_the_leg_made_one(tmp_path):
    """The candidate is 640x360 through the unmodified map and the release render
    is shipping geometry with the operator inside it. Showing one and captioning
    the other is how a page says something false with every field on it true."""
    from PIL import Image

    released = tmp_path / "released.png"
    Image.new("RGB", (32, 18), (10, 90, 160)).save(released)
    record = seating.seat([candidate("a", score=0.9)], n=1, key=seating.JUDGE_KEY, log=quiet)
    record["seated"][0].update(
        release_picture=str(released),
        release_geometry={"resolution": [1280, 720], "supersample": 2},
        release_autolevel={
            "acted": True,
            "curve": {
                "black_pt": 0.1,
                "white_pt": 0.9,
                "out_ends": [0.0, 1.0],
                "exponent": 1.0,
            },
        },
    )
    page = seating.contact_sheet("under-test", record, output=tmp_path / "sheet.html").read_text(
        encoding="utf-8"
    )
    assert "1280x720ss2" in page
    assert "pool percentile" in page
    bare = seating.seat([candidate("a", score=0.9)], n=1, key=seating.JUDGE_KEY, log=quiet)
    plain = seating.contact_sheet("under-test", bare, output=tmp_path / "plain.html").read_text(
        encoding="utf-8"
    )
    assert "this seat has no release picture" in plain


def test_the_release_leg_lands_in_the_seatings_own_directory_and_bounds_each_row():
    """One leg for a solve and a seating, so the geometry, the stamp rule and the
    resume rule cannot drift into two. A row that hangs is killed; the LEG has no
    clock and declines nothing."""
    from fractal_wallpapers.curation import solve

    seen = {}

    def spy(name, record, **kwargs):
        seen.update(name=name, **kwargs)
        return {}

    original = solve.render_seats
    solve.render_seats = spy
    try:
        seating.release_seats("g1_n150", {"seated": []})
    finally:
        solve.render_seats = original
    assert seen["where"] == seating.seat_dir("g1_n150") / "release"
    assert seen["timeout"] == solve.ROW_BACKSTOP
    assert seen["workers"] is None


# --------------------------------------------------------------------------- #
# The tracked ledger. Real rows, the real greedy.
# --------------------------------------------------------------------------- #
@pytest.fixture
def tracked_pool(tracked_ledger):
    """The session's one reading of the ledger. See `conftest.tracked_ledger`."""
    return tracked_ledger.pool


@pytest.fixture(scope="module")
def tracked_seating(tracked_ledger):
    """**One** real seating of the tracked pool, read by both guards below.

    The two asked the same question of `seating.seat` with the same arguments and
    got the same answer twice, for 3.3 s and 3.1 s of the slow lane on this
    machine, 2026-08-31. They assert different things about it, which is what
    makes them two tests; a greedy over the whole pool is not a thing to run
    twice to find that out.

    Read-only, like the tracked readings in `conftest.py`.
    """
    return seating.seat(tracked_ledger.pool, n=20, key=seating.JUDGE_KEY, log=quiet)


@pytest.mark.slow
def test_the_tracked_pool_seats_and_the_ledger_partitions_it(tracked_pool, tracked_seating):
    """One real seating, and the invariant the rejection ledger exists for: every
    candidate is seated exactly once or refused for exactly one reason.

    A ledger that double-counted would inflate whichever axis it double-counted
    on, and that aggregate is what a leg would be aimed down.
    """
    record = tracked_seating
    assert record["filled"] + sum(record["rejection"]["reasons"].values()) == len(tracked_pool)
    assert len({seat["location"] for seat in record["seated"]}) == record["filled"]


@pytest.mark.slow
def test_the_real_seating_breaks_no_rule_it_recorded_as_soft(tracked_seating):
    """Soft means the shortfall is recorded, never that the rule is exceeded: a
    greedy that passes over a candidate cannot end up over an allowance."""
    record = tracked_seating
    assert record["shortfalls"]["cells"]["over_allowance"] == {}
    assert record["shortfalls"]["families"]["over_allowance"] == {}
    assert record["shortfalls"]["groups"]["over_cap"] == {}


# --------------------------------------------------------------------------- #
# The mode floors: per mode, and the default since 2026-08-31.
# --------------------------------------------------------------------------- #
def test_a_gallery_too_small_for_the_flat_floor_is_floored_by_the_rule_anyway():
    """The smallest consequence of the flip.

    `floor(n / 100)` was zero below a hundred seats, so this leg did nothing there
    and a five-seat gallery was the strongest pictures the pool held. The per-mode
    rule asks for two of the three strange seats at `n = 5`, and this pool holds
    neither of the two modes it names — so the leg still places nothing, and the
    difference is that the record now says two floors went unfilled rather than
    that nothing was asked.
    """
    asked = {name: seats for name, seats in mode_policy.seat_floors(5).items() if seats}
    record = seating.seat(deep_and_shallow(), n=5, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["mode_floor"] is None
    assert set(record["shortfalls"]["modes"]["below_the_floor"]) == set(asked)
    assert {seat["seated_for"] for seat in record["seated"]} == {"general_pool"}
    assert modes_of(record) == {"smooth"}


def test_the_flat_floor_is_the_way_back_and_the_record_says_which_it_took():
    """`--flat-floor`, at a size where the flat floor is zero: nothing is asked of
    any mode, which is what every gallery seated before the flip got here."""
    record = seating.seat(
        deep_and_shallow(), n=5, floor=solve.mode_floor(5), key=seating.JUDGE_KEY, log=quiet
    )
    assert record["config"]["mode_floor"] == 0
    assert record["config"]["mode_floor_artificial"] is True, "it is not the default any more"
    assert "FLAT" in record["config"]["mode_floor_rule"]
    assert record["shortfalls"]["modes"]["below_the_floor"] == []
    assert {seat["seated_for"] for seat in record["seated"]} == {"general_pool"}


def test_an_artificial_floor_puts_the_leg_back_and_the_record_says_it_was_one():
    record = seating.seat(deep_and_shallow(), n=5, floor=1, key=seating.JUDGE_KEY, log=quiet)
    assert record["config"]["mode_floor"] == 1
    # `natural` is the default rule's own answer — what a seating naming no floor
    # would have been given — and it is a mapping now rather than one number.
    assert record["config"]["mode_floor_natural"] == seating.floors_for(
        mode_policy.seat_floors(5), mode_policy.accepted()
    )
    assert record["config"]["mode_floor_artificial"] is True
    assert any(seat["seated_for"].startswith("mode_floor:") for seat in record["seated"])


def floors_of(record) -> dict:
    """`{mode: seats the scarcity leg placed for it}` — the floor leg's own tally.

    Read off `seated_for` rather than off the mode counts, because a mode can also
    pick up seats from the general walk and the question here is what the floor
    itself bought.
    """
    out: dict = {}
    for seat in record["seated"]:
        if seat["seated_for"].startswith("mode_floor:"):
            out[seat["mode"]] = out.get(seat["mode"], 0) + 1
    return out


def three_modes_four_deep():
    """Four candidates in each of three modes, one place and one group apiece."""
    pool = [candidate(f"s{at}", mode="stripe", score=0.99) for at in range(4)]
    pool += [candidate(f"t{at}", mode="threads", score=0.98) for at in range(4)]
    pool += [candidate(f"d{at}", mode="smooth", score=0.97) for at in range(4)]
    return pool


def test_a_floor_of_two_seats_two_of_each_mode_and_not_one():
    """The leg keeps seating a mode until its floor is met, not until it seats once.

    [`seating.scarcity`] yields **one** `(mode, subpool)` per mode, so a leg that
    stopped at its first success capped every mode at one seat however high the
    floor was. Floor 1 and floor 2 returned a bit-identical gallery while the
    exact solver honoured the difference — a greedy silently seating less of the
    roster than it was asked for.
    """
    record = seating.seat(
        three_modes_four_deep(),
        n=6,
        floor=2,
        twin=False,
        radius=None,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    assert floors_of(record) == {"smooth": 2, "stripe": 2, "threads": 2}


def test_a_floor_of_one_and_a_floor_of_two_are_no_longer_the_same_gallery():
    """The observable half of the same bug: the two floors used to agree exactly."""
    pool = three_modes_four_deep()
    asked = {"n": 6, "twin": False, "radius": None, "key": seating.JUDGE_KEY, "log": quiet}
    one = seating.seat(pool, floor=1, **asked)
    two = seating.seat(pool, floor=2, **asked)
    assert floors_of(one) == {"smooth": 1, "stripe": 1, "threads": 1}
    assert floors_of(two) == {"smooth": 2, "stripe": 2, "threads": 2}
    assert {seat["key"] for seat in one["seated"]} != {seat["key"] for seat in two["seated"]}


def test_a_floor_can_be_set_per_mode_and_the_record_says_it_was():
    """The shape [`mode_policy.seat_floors`] builds. Nothing that ships passes one."""
    pool = three_modes_four_deep()
    record = seating.seat(
        pool,
        n=7,
        floor={"stripe": 3, "threads": 2, "smooth": 1},
        twin=False,
        radius=None,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    assert floors_of(record) == {"stripe": 3, "threads": 2, "smooth": 1}
    assert record["config"]["mode_floor"] is None
    assert record["config"]["mode_floors"]["stripe"] == 3
    assert record["config"]["mode_floors"]["curvature"] == 0
    assert record["shortfalls"]["modes"]["floors_are"] == "per mode"


def test_the_policys_own_floors_are_a_floor_the_seating_accepts():
    """The rule and the leg meet, without anything that ships putting them together.

    The point of building it inert is that enabling it is one call, not a project.
    """
    floors = mode_policy.seat_floors(1000)
    record = seating.seat(
        three_modes_four_deep(),
        n=7,
        floor=floors,
        twin=False,
        radius=None,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    assert record["config"]["mode_floors"]["stripe"] == floors["stripe"]
    assert record["config"]["mode_floors"]["smooth"] == 0
    assert record["filled"] == 7


def test_the_ceiling_wins_the_collision_and_the_floor_goes_unfilled():
    """A bar outranks a guarantee, and an unfilled floor beats a padded gallery.

    Three `stripe` candidates in one colour cell whose allowance is one, against a
    floor of three. The seating takes the one the ceiling permits, leaves the
    floor two short, and says so — it does not relax the cell to fill a mandate.
    """
    pool = [
        candidate(f"s{at}", mode="stripe", score=0.99, cells=("dark_vivid_blue",))
        for at in range(3)
    ]
    pool += [candidate(f"t{at}", mode="threads", score=0.98) for at in range(2)]
    record = seating.seat(
        pool,
        n=6,
        floor={"stripe": 3, "threads": 2},
        twin=False,
        radius=None,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    block = record["shortfalls"]["modes"]
    assert block["per_mode"]["stripe"] == {
        "floor": 3,
        "seated": 1,
        "short": 2,
        "clearing": 3,
        "refused_by": {"cell_allowance": 2},
    }
    assert block["per_mode"]["threads"]["short"] == 0
    assert block["starved"] == ["stripe"]
    assert {row["constraint"] for row in record["attribution"]["unmet"]} == {
        "seats",
        "mode_floor:stripe",
    }


def test_a_floor_of_zero_is_never_needed_and_is_not_a_starved_mode():
    """The two facts the old single list conflated.

    A mode nobody asked for cannot have gone short, and a real starvation hiding
    inside a list most of whose entries were never at risk is a shortfall nobody
    reads.
    """
    record = seating.seat(
        three_modes_four_deep(),
        n=6,
        floor={"stripe": 4},
        twin=False,
        radius=None,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    block = record["shortfalls"]["modes"]
    assert block["starved"] == []
    assert "smooth" in block["floor_never_needed"]
    assert "stripe" not in block["floor_never_needed"]
    assert block["floor_never_needed_count"] == len(block["floors"]) - 1


def test_the_greedy_and_the_exact_solver_seat_the_same_rows_at_a_floor_of_two():
    """Solver against solver, so the claim stands whatever the real pool holds.

    Seven candidates and six seats, every score equal, so the exact solver's first
    two stages — the count above the bar and the worst seated score — are tied on
    every feasible gallery and its **mode penalty** is what decides. `s1` and `c2`
    share a place, so the one-per-location rule leaves exactly two galleries: two
    of each mode, or one `stripe` and three `smooth`. The first carries no mode
    deficit, so it is the unique optimum, and a greedy honouring the floor has to
    land on it.

    It is worth saying what this test does **not** claim. The exact solver's mode
    floor is soft and third in a lexicographic objective, so a floor that costs it
    a point of the worst seated score is a floor it declines to fill. This pool is
    built so the floor costs nothing, which is the case where the two solvers are
    answering the same question at all.
    """
    pool = [
        candidate("c0", mode="smooth", score=0.90, location="C0"),
        candidate("c1", mode="smooth", score=0.90, location="C1"),
        candidate("c2", mode="smooth", score=0.90, location="SHARED"),
        candidate("s0", mode="stripe", score=0.90, location="S0"),
        candidate("s1", mode="stripe", score=0.90, location="SHARED"),
        candidate("t0", mode="threads", score=0.90, location="T0"),
        candidate("t1", mode="threads", score=0.90, location="T1"),
    ]
    record = seating.seat(
        pool, n=6, floor=2, twin=False, radius=None, key=seating.JUDGE_KEY, log=quiet
    )
    program = solve.Program(
        candidates=list(pool),
        n=6,
        rule=solve.rule_for(),
        modes=tuple(mode_policy.accepted()),
        floor=2,
    )
    answer = solve.lexicographic(program, log=quiet)
    assert answer.get("feasible", True)
    exact = sorted(pool[at].key for at in answer["chosen"])
    assert sorted(seat["key"] for seat in record["seated"]) == exact
    assert exact == ["c0", "c1", "s0", "s1", "t0", "t1"]


# --------------------------------------------------------------------------- #
# The twin test — the diversity rule, placed.
# --------------------------------------------------------------------------- #
class Signatures:
    """A [`pixel_clouds.Clouds`] whose signatures are a lookup, so a test needs no
    pictures.

    It replaces the making of a signature and nothing else — the bound, the metric
    and the sequential state above it are all the shipped code. Every signature is
    flat, so the distance between two of them is exactly the difference between
    the two values a test asked for, and a threshold is a number rather than a
    property of some picture. `made` and `hits` count the way the real cache
    counts, because one of the tests below is about how many signatures a walk
    pays for.
    """

    def __init__(self, values):
        import numpy

        from fractal_wallpapers.palettes import groups

        self.values = {
            key: numpy.full(groups.QUANTILES * groups.DIRECTIONS, value, dtype="float32")
            for key, value in values.items()
        }
        self.made = 0
        self.hits = 0
        self._seen: set = set()

    def of(self, name):
        held = self.values.get(str(name))
        if held is None:
            return None
        if str(name) in self._seen:
            self.hits += 1
        else:
            self._seen.add(str(name))
            self.made += 1
        return held

    def hold(self, name) -> None:
        pass


class EveryPicture(Signatures):
    """A [`Signatures`] that answers for any key, each far beyond [`ceiling.TAU`].

    So the twin rule runs, reads every candidate, and refuses none of them.
    """

    def __init__(self, candidates=()):
        super().__init__({})
        self._spread: dict = {}
        for held in candidates:
            self.of(getattr(held, "key", held))

    def of(self, name):
        import numpy

        from fractal_wallpapers.palettes import groups

        key = str(name)
        if key not in self.values:
            self._spread[key] = len(self._spread) * 1.0
            self.values[key] = numpy.full(
                groups.QUANTILES * groups.DIRECTIONS, self._spread[key], dtype="float32"
            )
        return super().of(key)


@pytest.fixture(autouse=True)
def every_candidate_has_a_picture(monkeypatch):
    """Every fixture candidate reads back a signature, spread far apart.

    Until 2026-08-28 the twin rule **admitted** a candidate whose picture it
    could not open. These fixtures name pictures that were never on disk, so the
    rule was silently inert through most of this file and nothing said so — the
    same reliance that let three seats of `p2b_n150` be taken by candidates whose
    JPEGs had been swept. It refuses now, and that made the reliance visible.

    This fixture states the assumption instead of leaning on a bug: the rule
    runs, every candidate is readable, and none is a twin. A test that wants a
    twin, an unreadable candidate, or a signature count installs its own
    `clouds_for` after this one and wins.
    """
    monkeypatch.setattr(seating, "clouds_for", lambda candidates, **_rest: EveryPicture(candidates))


def twins_over(values):
    """A [`Twins`] over flat signatures, so a pair's distance is `|a - b|`."""
    return seating.Twins(Signatures(values))


def test_a_picture_within_tau_of_a_seat_is_refused_as_a_twin():
    held = twins_over({"seated": 0.0, "near": ceiling.TAU / 2, "far": ceiling.TAU * 4})
    assert held.hold("seated") is True
    found = held.refuses("near")
    assert found is not None
    assert found["twin_of"] == "seated"
    assert found["pixel_cloud"] < ceiling.TAU
    assert held.refuses("far") is None


def test_the_first_seat_can_refuse_nothing_because_there_is_nothing_to_be_a_twin_of():
    held = twins_over({"a": 0.0})
    assert held.refuses("a") is None


def test_a_pair_the_bound_settles_is_never_measured():
    """The bound is a sound lower bound, so a pair beyond tau cannot be a twin."""
    held = twins_over({"seated": 0.0, "far": ceiling.TAU * 4})
    held.hold("seated")
    held.refuses("far")
    assert held.settled_by_the_bound == 1
    assert held.measured == 0


def test_a_pair_the_bound_cannot_settle_is_measured_in_full():
    held = twins_over({"seated": 0.0, "near": ceiling.TAU / 2})
    held.hold("seated")
    held.refuses("near")
    assert held.settled_by_the_bound == 0
    assert held.measured == 1


def test_a_candidate_with_no_picture_on_disk_is_refused_and_not_called_a_twin():
    """PLANTED: the file is missing, and the rule must fail closed.

    This pinned the opposite until 2026-08-28 — "a missing file is a fact about
    this checkout, not about the wallpaper", which is true and is still the wrong
    direction to fail in. Admitting meant the diversity rule stopped applying to
    exactly the candidates nothing could check, and `p2b_n150` seated three of
    them. The refusal carries its own name: "I could not read this" is not "this
    is a duplicate", and the rejection ledger must not conflate them.
    """
    held = twins_over({"seated": 0.0})
    held.hold("seated")
    found = held.refuses("nothing_on_disk")
    assert found is not None
    assert found["unreadable"] is True
    assert "twin_of" not in found
    assert held.without_a_picture == 1
    assert held.record()["refused_without_a_picture_on_disk"] == 1


def test_a_seating_refuses_a_candidate_whose_picture_vanishes_mid_pass(monkeypatch):
    """PLANTED: the file is there when the pool is built and gone when it is read.

    The pool guard cannot catch this one — it is the race the twin rule has to
    fail closed on — so the refusal is recorded under `picture_unreadable` and
    the seat is left unfilled rather than given away untested.
    """
    clouds = EveryPicture()
    vanished = {"b"}
    original = clouds.of
    monkeypatch.setattr(
        clouds, "of", lambda name: None if str(name) in vanished else original(name)
    )
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)

    pool = [candidate("a", score=0.99, location="one"), candidate("b", score=0.98, location="two")]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)

    assert [seat["key"] for seat in record["seated"]] == ["a"]
    assert record["rejection"]["reasons"]["picture_unreadable"] == 1
    assert "twin" not in record["rejection"]["reasons"]  # it was never called one
    assert record["twins"]["refused_without_a_picture_on_disk"] == 1


def test_a_seat_with_no_picture_is_not_held_and_cannot_refuse_anything():
    held = twins_over({})
    assert held.hold("nothing_on_disk") is False
    assert held.keys == []


def test_the_twin_rule_is_last_so_a_cheap_refusal_never_makes_a_signature(monkeypatch):
    """Every candidate the four counting rules refuse is a signature not made."""
    clouds = Signatures({"a": 0.0, "b": 0.0})
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)
    pool = [candidate("a", location="one"), candidate("b", location="one")]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"]["location"] == 1
    # One signature for the seated candidate, and none for the one `location` took.
    assert clouds.made == 1


def test_the_seating_refuses_a_twin_and_names_it_as_the_rule(monkeypatch):
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2, "c": ceiling.TAU * 8})
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)
    pool = [
        candidate("a", score=0.99),
        candidate("b", score=0.98),
        candidate("c", score=0.97),
    ]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    assert [seat["key"] for seat in record["seated"]] == ["a", "c"]
    assert record["rejection"]["reasons"]["twin"] == 1
    assert record["twin_refusals"]["b"]["twin_of"] == "a"


def test_a_twin_refusal_carries_the_picture_it_lost_to_onto_the_sheet(monkeypatch):
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2})
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)
    record = seating.seat(
        [candidate("a", score=0.99), candidate("b", score=0.98)],
        n=5,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    shown = record["samples"]["twin"][0]
    assert shown["lost_to"]["picture"] == "artifacts/a.jpg"
    assert shown["lost_to"]["pixel_cloud"] < ceiling.TAU


# --------------------------------------------------------------------------- #
# The neutral pre-selection, at pool construction.
# --------------------------------------------------------------------------- #
def store_of(vectors) -> list:
    """A neutral embedding store of two-dimensional unit vectors, by angle.

    Two dimensions rather than three hundred and eighty-four because the cosine
    between two unit vectors is the whole of what the pre-selection reads, and an
    angle is a distance a test can state.
    """
    import math

    return [
        {"key": key, "vector": embeddings.pack([math.cos(angle), math.sin(angle)])}
        for key, angle in vectors.items()
    ]


def test_two_places_inside_the_radius_lose_the_weaker_one():
    import math

    # cos(0.1) is 0.995, so the pair sits at 0.005 — inside the 0.02 radius.
    rows = store_of({"a": 0.0, "b": 0.1, "c": math.pi / 2})
    kept, record = distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.98), candidate("c", score=0.97)],
        rows=rows,
        log=quiet,
    )
    assert {held.key for held in kept} == {"a", "c"}
    assert record["places_refused"] == 1
    assert record["refusals"][0]["location"] == "b"
    assert record["refusals"][0]["lost_to"] == "a"


def test_the_strongest_place_in_a_cluster_is_the_one_kept():
    rows = store_of({"a": 0.0, "b": 0.1})
    kept, _record = distinct.preselect(
        [candidate("a", score=0.10), candidate("b", score=0.99)], rows=rows, log=quiet
    )
    assert {held.key for held in kept} == {"b"}


def test_a_place_with_no_descriptor_is_admitted_and_counted():
    """A place can be newer than the last embedding leg, and refusing on that would
    make the pre-filter a function of when the store was last built."""
    kept, record = distinct.preselect([candidate("a"), candidate("b")], rows=[], log=quiet)
    assert len(kept) == 2
    assert record["admitted_without_a_descriptor"] == 2
    assert record["places_refused"] == 0


def test_refusing_a_place_takes_every_row_that_place_carries():
    rows = store_of({"a": 0.0, "b": 0.1})
    pool = [
        candidate("a1", location="a", score=0.99),
        candidate("b1", location="b", score=0.98),
        candidate("b2", location="b", score=0.50),
    ]
    kept, record = distinct.preselect(pool, rows=rows, log=quiet)
    assert {held.key for held in kept} == {"a1"}
    assert record["candidates_refused"] == 2


def test_the_preselection_refusal_is_not_one_of_the_seating_rules(monkeypatch):
    """It is pool construction, and the ledger says which of the two it was."""
    rows = store_of({"a": 0.0, "b": 0.1})
    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: rows)
    record = seating.seat(
        [candidate("a", score=0.99), candidate("b", score=0.98)],
        n=5,
        key=seating.JUDGE_KEY,
        log=quiet,
    )
    assert seating.SAME_PLACE not in seating.RULES
    assert record["rejection"]["reasons"][seating.SAME_PLACE] == 1
    assert record["preselection"]["places_refused"] == 1
    assert record["population"]["after_the_preselection"] == 1


def test_a_preselection_refusal_carries_the_place_it_lost_to_onto_the_sheet(monkeypatch):
    """Keyed by candidate and not by place, because the sheet is.

    Every row the refused place carried went with it, so each of them is shown
    against the picture the place lost to — an earlier version keyed this by
    location and the sheet showed one picture where the whole point is two.
    """
    rows = store_of({"a": 0.0, "b": 0.1})
    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: rows)
    pool = [
        candidate("a1", location="a", score=0.99),
        candidate("b1", location="b", score=0.98),
        candidate("b2", location="b", score=0.50),
    ]
    record = seating.seat(pool, n=5, key=seating.JUDGE_KEY, log=quiet)
    shown = record["samples"][seating.SAME_PLACE]
    assert {row["key"] for row in shown} == {"b1", "b2"}
    assert all(row["lost_to"]["picture"] == "artifacts/a1.jpg" for row in shown)


def test_a_seating_asked_for_without_the_preselection_says_it_was_skipped():
    record = seating.seat([candidate("a")], n=5, radius=None, key=seating.JUDGE_KEY, log=quiet)
    assert "skipped" in record["preselection"]


def test_a_clearing_pool_the_key_cannot_read_is_refused_rather_than_seated_around() -> None:
    """The `mine1h` failure, written down. A leg that merges without a flatness
    sweep leaves every row it wrote unreadable by the fitted key; those rows sort
    last, which is the right order and the wrong silence — they cannot win a seat
    while any readable row is left, and nothing in the output said so. 8,192 rows
    merged, 1,326 of them clearing, none seated, no warning.

    The refusal names the count and the command, because the reader of it is
    somebody who has just merged and is about to conclude the ore was worthless.
    """
    pool = [candidate("read"), candidate("blind1"), candidate("blind2")]
    with pytest.raises(seating.SeatingRefused) as refusal:
        seating.seat(pool, n=3, order={"read": 0.9}, log=quiet)
    said = str(refusal.value)
    assert "2 of 3" in said, "the count is the point: how much of the pool is invisible"
    assert "curate flatness sweep" in said, "and the command that fixes it"


def test_allow_unranked_is_the_way_past_it_and_the_record_says_it_was_used() -> None:
    """For the one case a sweep cannot fix: a picture on disk that will not decode
    has no reading and never will, so a pool holding one would be unseatable
    forever. The record carries the flag so a later reader can tell a seating that
    had a whole pool from one that was told to proceed without one."""
    pool = [candidate("read"), candidate("blind")]
    record = seating.seat(pool, n=2, order={"read": 0.9}, allow_unranked=True, log=quiet)
    assert record["order"]["unranked"] == 1
    assert record["order"]["unranked_allowed"] is True
    assert record["filled"] == 2, "an unranked row still seats once the readable ones are spent"


def test_the_judge_key_needs_no_flatness_and_is_never_refused_for_one() -> None:
    """`p_ge4` is read off the candidate, so there is no store to be short of and
    no pool it cannot read. The refusal is a property of a *fitted* key."""
    pool = [candidate("a"), candidate("b")]
    record = seating.seat(pool, n=2, key=seating.JUDGE_KEY, log=quiet)
    assert record["order"]["unranked"] == 0
    assert record["order"]["unranked_allowed"] is False
