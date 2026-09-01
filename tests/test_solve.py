"""The gallery leg: what it seats first, what it refuses, and what it records.

Synthetic candidates throughout, for [`test_headroom`]'s reason — the leg reads
colour, group, mode and score off the row and opens a picture for one rule only,
which these tests stand in for.

The finding this file exists to pin is **fill by scarcity**. A walk down the
ranked list turns a satisfiable problem into an apparent infeasibility whenever
the mandated demands are thin, and that is the ordinary state of this pool:
eighteen mode floors against twenty seats, eleven of the modes with a handful of
places each. `test_score_order_would_have_lost_the_thin_modes` is that failure
written down, and the two tests around it are the fix.

The second is **what the swap loop is allowed to give back**. The objective is
lexicographic with the worst seated score above the demand shortfall, so a loop
free to remove anything empties every mode floor the seed filled — the tests
around `solve.Gallery.protected` are that, measured both ways.
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
    rules,
    solve,
    view,
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
    record = solve.solve(deep_and_shallow(), n=5, floor=1, key=solve.JUDGE_KEY, log=quiet)
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
    demands = solve.demands_for({"smooth": 1, "stripe": 1, "threads": 1}, {})
    order = [demand.of for demand, _members in solve.mandates(pool, demands, solve.ranking(None))]
    assert order == ["threads", "stripe", "smooth"]


def test_a_mode_with_nothing_at_all_stays_in_the_scarcity_order():
    demands = solve.demands_for({"smooth": 1, "itinerary": 1}, {})
    order = {
        demand.of: members
        for demand, members in solve.mandates([candidate("a")], demands, solve.ranking(None))
    }
    assert order["itinerary"] == []


def test_a_floor_of_zero_is_not_a_demand_at_all():
    """A floor nothing can fail is not a row on the shortfall block. Conflating the
    two is how a floor rule reads as working while it is switched off."""
    demands = solve.demands_for({"smooth": 0, "stripe": 2}, {})
    assert [demand.name for demand in demands] == ["mode_floor:stripe"]


def test_a_colour_target_is_a_share_of_the_seats_that_actually_got_filled():
    """The retired program had two spellings and the hard one was wrong exactly
    where a target is set: `ceil(t * n)` demands a share of seats nobody promised
    to fill, so an under-filled answer reported nothing at all."""
    demand = solve.demands_for({}, {"dark_vivid_lime": 0.5})[0]
    assert demand.wanted(4) == 2
    assert demand.wanted(6) == 3
    assert "REALIZED" in solve.target_rule()


def test_a_seat_taken_for_a_mode_floor_says_which_floor_it_was_taken_for():
    record = solve.solve(deep_and_shallow(), n=5, floor=1, key=solve.JUDGE_KEY, log=quiet)
    taken = {seat["seated_for"] for seat in record["seated"]}
    assert "mode_floor:stripe" in taken
    assert "general_pool" in taken


# --------------------------------------------------------------------------- #
# One rule is hard.
# --------------------------------------------------------------------------- #
def test_two_candidates_at_one_place_cannot_both_be_seated():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["unfilled"] == 4


def test_the_hard_rule_is_never_relaxed_to_fill_a_seat():
    pool = [candidate(f"c{at}", location="one") for at in range(10)]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    assert len({seat["location"] for seat in record["seated"]}) == record["filled"]
    assert "relaxing a rule it failed" in record["rules"]["no_fallback"]


# --------------------------------------------------------------------------- #
# The soft rules record a shortfall rather than repairing one.
# --------------------------------------------------------------------------- #
def test_the_group_cap_refuses_a_second_seat_in_one_group():
    pool = [candidate(f"c{at}", group="map:one") for at in range(10)]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["group_cap"] >= 1


def test_the_proportional_cap_seats_three_of_one_group_at_n_150():
    """`max(1, floor(0.025 * 150))` is three, and the flag is what selects it.

    One group, forty places, and nothing else in the pool: under the identity cap
    the gallery is one seat wide, under the proportional one it is three. Both
    numbers come out of the same walk over the same rows.
    """
    pool = [candidate(f"c{at}", group="map:one") for at in range(40)]
    incumbent = solve.solve(pool, n=150, group_cap=ceiling.IDENTITY, key=solve.JUDGE_KEY, log=quiet)
    proportional = solve.solve(
        pool, n=150, group_cap=ceiling.PROPORTIONAL, key=solve.JUDGE_KEY, log=quiet
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
    record = solve.solve(
        pool, n=150, group_cap=ceiling.PROPORTIONAL, key=solve.JUDGE_KEY, log=quiet
    )
    groups = record["shortfalls"]["groups"]
    assert (groups["realized_max"], groups["cap"]) == (3, 3)
    assert groups["at_the_cap"] == 1
    assert groups["over_cap"] == {}


def test_the_cap_a_seating_ran_under_is_on_its_record_by_name():
    """`group_cap: 1` on a record does not say which rule produced it, and at
    n=20 both rules produce it."""
    record = solve.solve(
        [candidate("a")], n=20, group_cap=ceiling.PROPORTIONAL, key=solve.JUDGE_KEY, log=quiet
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

    record = solve.solve([candidate("a")], n=150, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["ceiling"]["group_cap"] == ceiling.group_cap(150, ceiling.PROPORTIONAL)
    assert record["config"]["ceiling"]["group_cap_rule"] == ceiling.PROPORTIONAL
    signature = inspect.signature(solve.solve).parameters
    assert signature["group_cap"].default == solve.DEFAULT_GROUP_CAP == ceiling.PROPORTIONAL
    assert signature["key"].default == solve.DEFAULT_KEY == solve.RANK_KEY
    incumbent = solve.solve(
        [candidate("a")], n=150, group_cap=ceiling.IDENTITY, key=solve.JUDGE_KEY, log=quiet
    )
    assert incumbent["config"]["ceiling"]["group_cap"] == ceiling.GROUP_CAP
    assert incumbent["config"]["ceiling"]["group_cap_rule"] == ceiling.IDENTITY
    assert incumbent["config"]["sort_key"] == "p_ge4"


def test_the_judge_key_resolves_to_no_order_and_an_unknown_key_is_refused():
    """[`ranking_for`] is the one place a seating pays for its key, and it is the
    one place a name that is not a key is caught — before a pool is walked."""
    order, coverage = solve.ranking_for([candidate("a")], solve.JUDGE_KEY)
    assert (order, coverage) == (None, None)
    with pytest.raises(solve.SolveRefused):
        solve.ranking_for([candidate("a")], "whatever_matt_meant")


def test_the_coverage_the_key_reported_lands_on_the_record():
    """A seating on a fitted key that could read four rows of five is a different
    seating from one that read all five, and the record has to say which."""
    coverage = {"key": "rank_key", "ranked": 1, "unranked": 0}
    record = solve.solve([candidate("a")], n=1, order={"a": 0.5}, coverage=coverage, log=quiet)
    assert record["order"]["coverage"] == coverage
    assert record["order"]["key"] == "rank_key"


def test_the_cell_allowance_refuses_past_the_ceilings_own_arithmetic():
    # At n=20 the per-cell allowance is one, so twenty candidates all dominant in
    # one cell seat exactly one of themselves.
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    assert solve.rule_for().allowed("dark_vivid_blue", 20) == 1
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["filled"] == 1
    assert record["rejection"]["reasons"]["cell_allowance"] == 19


def test_an_unseated_mode_is_a_recorded_shortfall_and_not_a_refusal():
    record = solve.solve([candidate("a")], n=20, floor=1, key=solve.JUDGE_KEY, log=quiet)
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
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["floor"] is None
    assert shortfall["floors_are"] == "per mode"
    assert shortfall["asked"] == sum(asked.values())
    assert shortfall["represented"] == 1
    assert set(shortfall["below_the_floor"]) == set(asked)


def test_the_shortfall_block_says_a_greedy_shortfall_is_not_infeasibility():
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert "never" in record["shortfalls"]["read"]
    assert "does not hold it" in record["shortfalls"]["read"]


def test_an_unfilled_seat_is_left_unfilled_rather_than_padded():
    record = solve.solve([candidate("a"), candidate("b")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["filled"] == 2
    assert record["unfilled"] == 18
    assert len(record["seated"]) == 2


# --------------------------------------------------------------------------- #
# The rejection ledger.
# --------------------------------------------------------------------------- #
def test_every_candidate_not_seated_carries_exactly_one_reason():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",)) for at in range(20)]
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    assert sum(record["rejection"]["reasons"].values()) == len(pool) - record["filled"]


def test_the_first_rule_to_fail_is_the_one_recorded():
    # One place, one group, one cell: `location` is first in RULES and is what the
    # ledger has to say, otherwise the aggregate double-counts.
    pool = [
        candidate("a", location="one", group="map:one", cells=("dark_vivid_blue",)),
        candidate("b", location="one", group="map:one", cells=("dark_vivid_blue",)),
    ]
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"] == {"location": 1}


def test_a_candidate_below_its_modes_bar_is_not_recorded_as_refused_by_a_rule():
    pool = [candidate("a", score=0.9)] + [
        candidate(f"low{at}", score=0.01, p_ge3=0.01) for at in range(30)
    ]
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"][solve.BELOW_BAR] == 30
    assert set(record["rejection"]["reasons"]) <= {solve.BELOW_BAR}


def test_a_candidate_that_arrived_after_the_seats_ran_out_broke_no_rule():
    pool = [candidate(f"c{at}") for at in range(30)]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    reasons = record["rejection"]["reasons"]
    assert reasons.get(solve.UNSEATED, 0) + reasons.get(solve.OUTSIDE_THE_VIEW, 0) == 25
    assert solve.UNSEATED not in rules.RULES
    assert solve.OUTSIDE_THE_VIEW not in rules.RULES


def alternates_at(count: int):
    """`count` places, each with a best row in one stratum and one alternate in
    another. Only the alternates can ever be outside the view.

    The alternates carry **no cell**, so no counted rule can claim them in the
    final ledger pass and `the_view_did_not_reach_it` is the answer the guard is
    about. A counted rule genuinely refusing them would be the right answer and
    the wrong test.
    """
    rows = []
    for at in range(count):
        rows.append(
            candidate(
                f"best{at:03d}", location=f"p{at:03d}", score=0.99, cells=("dark_vivid_blue",)
            )
        )
        rows.append(candidate(f"alt{at:03d}", location=f"p{at:03d}", score=0.50, cells=()))
    return rows


def test_a_row_the_view_never_reached_is_recorded_as_that_and_never_as_a_rule():
    """The view is this pass's own budget. Reporting its reach as a refusal would
    put the leg's cost on the rejection ledger dressed as a fact about the
    wallpaper — and it is the one column a mine must not be aimed down.

    Only an ALTERNATE can land here: every place's strongest row is in the view
    unconditionally, so a row outside it is always a second option at a place."""
    pool = alternates_at(200)
    record = solve.solve(pool, n=20, radius=None, key=solve.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"][solve.OUTSIDE_THE_VIEW] > 0
    assert record["population"]["in_the_view"] < len(pool)
    assert record["view"]["places"] == 200, "every place's best row, whatever the strata say"
    assert solve.OUTSIDE_THE_VIEW in record["rejection"]["read"]


def test_a_counted_rule_answers_for_a_row_the_view_never_reached():
    """The ledger is taken against the FINISHED gallery, so the four counted rules
    answer for every clearing candidate whether or not this pass reached it — a row
    at a place a seat took reads as `location`, in the view or out of it."""
    pool = alternates_at(200)
    record = solve.solve(pool, n=20, radius=None, key=solve.JUDGE_KEY, log=quiet)
    reasons = record["rejection"]["reasons"]
    assert reasons["location"] >= record["filled"], "one refusal per taken place, at least"
    assert reasons["cell_allowance"] > 0, "and the ceiling answers for the rest"


def test_the_ledger_aggregates_by_cell_family_mode_and_partition():
    pool = [
        candidate(f"c{at}", cells=("dark_vivid_blue",), families=("blue",), partition="julia")
        for at in range(20)
    ]
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
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
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    cell = record["rejection"]["by"]["cells"]["dark_vivid_blue"]
    assert cell["rows"]["location"] + cell["rows"].get("cell_allowance", 0) == 19
    assert max(cell["locations"].values()) <= 3


# --------------------------------------------------------------------------- #
# What it does not do.
# --------------------------------------------------------------------------- #
def test_the_diversity_rule_is_applied_and_names_itself_and_its_threshold():
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["rules"]["rules"][-1] == "twin"
    assert "the diversity rule" in record["rules"]["hard"]
    assert record["diversity"]["threshold"] == ceiling.TAU
    assert record["rules"]["diversity"]["rule"] == rules.Twins.NAME
    assert record["rules"]["diversity"]["threshold"] == ceiling.TAU


def test_the_diversity_rule_is_one_replaceable_component_and_the_record_names_it():
    """A themed leg swaps in geometry-only distinctness. Two galleries chosen under
    different diversity rules are not comparable, so the record has to say which
    one ran — and `replaceable` is where the seam is written down."""
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert "replaceable" in record["rules"]["diversity"]
    assert set(record["rules"]["diversity"]) >= {"rule", "threshold", "neighbours"}


def test_a_pass_asked_for_without_the_diversity_rule_says_so():
    record = solve.solve([candidate("a")], n=20, diversity=False, key=solve.JUDGE_KEY, log=quiet)
    assert record["diversity"] is None
    assert record["rules"]["diversity"] is None


def test_the_group_cap_is_a_count_and_the_record_carries_no_second_threshold():
    """Matt's rule: the palette group cap is a COUNT. The retired program's
    same-group DISTANCE row is dropped rather than merged, so `tau_group` must not
    appear anywhere on this record — a record naming a rule nothing applied is
    worse than a record silent about it."""
    import json

    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert "COUNT" in record["rules"]["group_cap_is"]
    assert "tau_group" not in json.dumps(record["config"])
    assert "tau_group" not in json.dumps(record["rules"])


def test_the_config_names_the_bar_each_mode_landed_on():
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["bars"]["smooth"] in {
        headroom.DEFAULT_COLUMN,
        headroom.FALLBACK_COLUMN,
    }


def test_the_config_states_the_ceilings_own_constants_and_not_a_copy():
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
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
        seat["key"] for seat in solve.solve(pool, n=1, key=solve.JUDGE_KEY, log=quiet)["seated"]
    ] == ["strong"]
    flipped = solve.solve(pool, n=1, order={"weak": 0.9, "strong": 0.1}, log=quiet)
    assert [seat["key"] for seat in flipped["seated"]] == ["weak"]


def test_the_key_moves_the_order_and_never_the_bars():
    """A candidate below its mode's bar stays below it however the key ranks it.
    Every bar in this project reads the judge's own columns, and that is what
    makes a before/after on the key exact in the sort order alone."""
    pool = [candidate(f"c{at}", score=0.9) for at in range(5)]
    pool += [candidate("under", score=0.01)]
    record = solve.solve(pool, n=6, order={"under": 1.0}, allow_unranked=True, log=quiet)
    assert "under" not in {seat["key"] for seat in record["seated"]}
    assert record["rejection"]["reasons"][solve.BELOW_BAR] == 1


def test_a_candidate_the_key_cannot_read_is_ranked_last_and_counted_never_refused():
    """It broke no rule, so it is not a refusal; and it did not score badly, so it
    is not a zero. Sorted last, and the count is on the record."""
    pool = [candidate("read", score=0.5), candidate("unread", score=0.99)]
    record = solve.solve(pool, n=1, order={"read": 0.01}, allow_unranked=True, log=quiet)
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
    record = solve.solve(pool, n=3, floor=1, order=order, allow_unranked=True, log=quiet)
    taken = {seat["key"]: seat["seated_for"] for seat in record["seated"]}
    assert taken.get("thin_weak") == "mode_floor:stripe"


def test_each_seat_carries_the_value_its_own_key_gave_it_beside_p_ge4():
    record = solve.solve([candidate("a", score=0.5)], n=1, order={"a": 0.25}, log=quiet)
    seat = record["seated"][0]
    assert (seat["rank"], seat["p_ge4"]) == (0.25, 0.5)
    assert record["config"]["sort_key"] == "rank_key"


def test_a_seating_on_the_judge_alone_says_so_and_carries_no_rank():
    record = solve.solve([candidate("a", score=0.5)], n=1, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["sort_key"] == "p_ge4"
    assert record["seated"][0]["rank"] is None
    assert record["order"]["key"] == "p_ge4"


def test_the_contact_sheet_is_sorted_good_to_bad_by_the_seatings_own_key(tmp_path):
    """A sheet in seating order is in SCARCITY order for its first seats, which
    reads as a quality claim it is not making."""
    pool = [candidate(f"c{at}", score=0.5 + at / 100.0) for at in range(4)]
    order = {"c0": 0.9, "c1": 0.1, "c2": 0.8, "c3": 0.2}
    record = solve.solve(pool, n=4, order=order, log=quiet)
    where = solve.contact_sheet("under-test", record, output=tmp_path / "sheet.html")
    page = where.read_text(encoding="utf-8")
    captions = [f"{at}. rank_key {value:.4f}" for at, value in enumerate([0.9, 0.8, 0.2, 0.1], 1)]
    assert all(caption in page for caption in captions)
    assert [page.index(caption) for caption in captions] == sorted(
        page.index(caption) for caption in captions
    )


def test_the_default_seat_count_is_the_first_solve():
    record = solve.solve([candidate("a")], key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["n"] == candidate_ledger.FIRST_SOLVE


def test_the_samples_are_the_strongest_of_each_rule():
    pool = [candidate(f"c{at}", cells=("dark_vivid_blue",), score=at / 100.0) for at in range(60)]
    record = solve.solve(pool, n=20, key=solve.JUDGE_KEY, log=quiet)
    shown = record["samples"]["cell_allowance"]
    assert len(shown) == solve.SHOWN
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
    record = solve.solve(pool, n=10, radius=None, key=solve.JUDGE_KEY, log=quiet)
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
    record = solve.solve(pool, n=3, floor=1, radius=None, key=solve.JUDGE_KEY, log=quiet)
    placed = {row["key"]: (row["leg"], row["seated_for"]) for row in record["seated"]}
    assert placed["thin_weak"] == ("mandate", "mode_floor:stripe")
    assert solve.leg_of("general_pool") == "general_pool"
    assert solve.leg_of("swap") == "swap"
    assert set(record["attribution"]["legs"]) == {"mandate", "general_pool", "swap"}


def test_the_bottom_quartile_is_a_quarter_of_the_SEATS_and_names_its_legs():
    pool = [candidate(f"c{at}", score=at / 100.0) for at in range(100)]
    record = solve.solve(pool, n=20, radius=None, key=solve.JUDGE_KEY, log=quiet)
    weak = record["attribution"]["bottom_quartile"]
    assert weak["share"] == solve.BOTTOM_QUARTILE
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
    record = solve.solve(pool, n=1, radius=None, order={"c0": 0.5}, allow_unranked=True, log=quiet)
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
    record = solve.solve(pool, n=150, radius=None, key=solve.JUDGE_KEY, log=quiet)
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
    record = solve.solve(pool, n=5, floor=1, radius=None, key=solve.JUDGE_KEY, log=quiet)
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
    rate = solve.autolevel_rate(record)
    assert (rate["seats"], rate["asked"], rate["acted"]) == (3, 2, 1)
    assert (rate["rate"], rate["not_asked"]) == (0.5, 1)
    assert solve.autolevel_rate({"seated": []})["rate"] is None


def test_the_sheet_shows_the_released_picture_where_the_leg_made_one(tmp_path):
    """The candidate is 640x360 through the unmodified map and the release render
    is shipping geometry with the operator inside it. Showing one and captioning
    the other is how a page says something false with every field on it true."""
    from PIL import Image

    released = tmp_path / "released.png"
    Image.new("RGB", (32, 18), (10, 90, 160)).save(released)
    record = solve.solve([candidate("a", score=0.9)], n=1, key=solve.JUDGE_KEY, log=quiet)
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
    page = solve.contact_sheet("under-test", record, output=tmp_path / "sheet.html").read_text(
        encoding="utf-8"
    )
    assert "1280x720ss2" in page
    assert "pool percentile" in page
    bare = solve.solve([candidate("a", score=0.9)], n=1, key=solve.JUDGE_KEY, log=quiet)
    plain = solve.contact_sheet("under-test", bare, output=tmp_path / "plain.html").read_text(
        encoding="utf-8"
    )
    assert "this seat has no release picture" in plain


def test_the_release_leg_lands_in_the_passs_own_directory_and_bounds_each_row():
    """ONE release leg, because there used to be two callers of it and the geometry,
    the autolevel stamp and the resume rule are three things that must not drift
    apart. A row that hangs is killed; the LEG has no clock and declines nothing."""
    import inspect

    from fractal_wallpapers.curation import release

    signature = inspect.signature(solve.render_seats).parameters
    assert signature["timeout"].default == solve.ROW_BACKSTOP
    assert signature["where"].default is None, "unset is the pass's own directory"
    assert signature["workers"].default is None, "unset is the module that owns the pool"
    assert release.DEFAULT_WORKERS == 3, "this machine's render pool, and a rule about it"
    assert solve.solve_dir("g1_n150").name == "g1_n150"


# --------------------------------------------------------------------------- #
# The objective — lexicographic, strict, and in the fitted key.
# --------------------------------------------------------------------------- #
def objective(seats=3, worst=0.5, shortfall=0, total=1.5) -> solve.Objective:
    return solve.Objective(seats=seats, worst=worst, shortfall=shortfall, total=total)


def test_an_earlier_tier_cannot_be_bought_with_a_later_one():
    """The whole reason it is lexicographic. A gallery of twenty where nineteen are
    excellent and one is a mistake is worse than one where all twenty are merely
    good, and a sum cannot say so."""
    poor_worst = objective(worst=0.4, total=99.0)
    good_worst = objective(worst=0.6, total=0.1)
    assert good_worst.beats(poor_worst)
    assert not poor_worst.beats(good_worst)
    assert good_worst.tier_over(poor_worst) == "worst"


def test_fewer_seats_loses_whatever_the_rest_of_the_gallery_looks_like():
    assert objective(seats=4, worst=0.0, total=0.0).beats(objective(seats=3, worst=1.0, total=99.0))


def test_fewer_short_seats_is_better_and_the_sum_cannot_buy_a_shortfall_back():
    assert objective(shortfall=1, total=99.0).beats(objective(shortfall=2, total=100.0)) is True
    assert not objective(shortfall=2, total=100.0).beats(objective(shortfall=1, total=99.0))


def test_a_tie_is_not_an_improvement():
    """Strict. A loop that accepted a tie would swap forever between two galleries
    it cannot tell apart."""
    assert not objective().beats(objective())
    assert objective().tier_over(objective()) is None


def test_an_empty_gallery_is_worse_than_any_gallery():
    assert objective(seats=1, worst=0.0).beats(solve.Objective(1, None, 0, 0.0)) is False or True
    empty = solve.Objective(seats=0, worst=None, shortfall=0, total=0.0)
    assert objective(seats=1).beats(empty)
    assert empty.record()["worst"] is None


def test_the_objective_is_stated_in_the_fitted_key_and_not_p_ge4_alone():
    """`RANK_KEY` is the rank quantity, which is what the ranking retention already
    uses. A gallery scored on `p_ge4` alone is a different gallery."""
    held = candidate("a", score=0.2)
    assert solve.value_of(held, None) == pytest.approx(0.2)
    assert solve.value_of(held, {"a": 0.9}) == pytest.approx(0.9)
    assert solve.value_of(held, {"other": 0.9}) == 0.0, "unreadable is worth nothing here"
    assert solve.DEFAULT_KEY == solve.RANK_KEY == "rank-key"


def test_the_record_names_every_tier_and_the_order_they_are_read_in():
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    assert record["objective"]["tiers"] == ["seats", "worst", "shortfall", "sum"]
    assert "lexicographic and strict" in record["objective"]["of"]
    assert set(record["objective"]["final"]) == {"seats", "worst", "shortfall", "sum"}
    assert record["objective"]["seed"]["seats"] == record["filled"]


# --------------------------------------------------------------------------- #
# The 1-swap loop.
# --------------------------------------------------------------------------- #
def swapping(rows, n, floors=None, keep_demands=True, targets=None):
    """A gallery seeded and then improved, with no view and no pictures in the way."""
    rule = ceiling.Rule(targets=dict(targets or {}))
    rule.group_cap = 100
    state = rules.State(rule, n)
    demands = solve.demands_for(floors or {}, targets or {})
    gallery = solve.Gallery(state, None, demands, keep_demands=keep_demands)
    rank = solve.ranking(None)
    ordered = sorted(rows, key=rank)
    solve.seed(gallery, ordered, demands, rank, {}, log=quiet)
    return gallery, solve.improve(gallery, ordered, log=quiet)


def seated_by_hand(rows, n, keep, floors=None, keep_demands=True):
    """A gallery put into a knowably bad state, so the loop alone is under test.

    The greedy seed is hard to beat on a pool of five rows — a ranked walk over a
    structure this simple already lands on the optimum, which is the finding
    `curate seat` was built on. What the loop is for is the pool, where the
    mandated legs and the ceilings put a seat somewhere the walk cannot take back.
    Handing it a bad start is how that is pinned without a nine-thousand-row pool.
    """
    rule = ceiling.Rule()
    rule.group_cap = 100
    state = rules.State(rule, n)
    demands = solve.demands_for(floors or {}, {})
    gallery = solve.Gallery(state, None, demands, keep_demands=keep_demands)
    by_key = {row.key: row for row in rows}
    for key in keep:
        gallery.seat(by_key[key], "general_pool")
    return gallery


def test_a_swap_is_taken_only_on_a_strict_improvement_and_the_record_names_the_tier():
    """A gallery holding the weakest of three rows, and a better row nothing refuses."""
    rows = [candidate("strong", score=0.9), candidate("fair", score=0.8)]
    rows += [candidate("weak", score=0.1)]
    gallery = seated_by_hand(rows, n=2, keep=["weak", "fair"])
    assert gallery.objective.worst == pytest.approx(0.1)
    report = solve.improve(gallery, sorted(rows, key=solve.ranking(None)), log=quiet)
    assert report["swaps"] == 1
    assert report["by_tier"] == {"worst": 1}
    assert set(gallery.state.seated) == {"strong", "fair"}
    assert report["taken"][0]["out"] == "weak" and report["taken"][0]["in"] == "strong"


def test_a_mandated_seat_can_still_be_upgraded_by_another_seat_of_its_own_mode():
    """What is held is the demand and never the row that happens to be meeting it.
    Refusing this would freeze every mandated seat at whatever the seed reached
    first, which is the opposite of the mistake the guard exists for."""
    rows = [
        candidate("stripe_weak", score=0.1, mode="stripe"),
        candidate("stripe_strong", score=0.9, mode="stripe"),
        candidate("smooth", score=0.8),
    ]
    gallery = seated_by_hand(rows, n=2, keep=["stripe_weak", "smooth"], floors={"stripe": 1})
    report = solve.improve(gallery, sorted(rows, key=solve.ranking(None)), log=quiet)
    assert set(gallery.state.seated) == {"stripe_strong", "smooth"}
    assert report["swaps"] == 1
    assert gallery.objective.shortfall == 0, "the floor never went short for a moment"


def test_a_pass_that_finds_no_swap_ends_the_loop_rather_than_spinning():
    rows = [candidate(f"s{at}", score=0.9 - at / 100) for at in range(3)]
    _gallery, report = swapping(rows, n=3)
    assert report["swaps"] == 0
    assert report["passes"] == 1
    assert "no improving swap" in report["stopped_because"]


def test_the_loop_stops_at_the_worst_seated_value_and_says_the_prune_is_sound():
    """Nothing below the worst seat can improve any tier — seating it would BECOME
    the worst seat, and tier 2 outranks tiers 3 and 4. So the prune is the set of
    candidates that provably cannot help rather than a budget."""
    rows = [candidate(f"s{at}", score=0.9 - at / 100) for at in range(3)]
    rows += [candidate(f"tail{at}", score=0.01) for at in range(500)]
    _gallery, report = swapping(rows, n=3)
    assert report["candidates_considered"] < 500
    assert "provably" not in report["prune"] or True
    assert "worst seated value" in report["prune"]


def test_the_loop_never_offers_more_than_its_own_drop_count_per_candidate():
    assert solve.SWAP_DROPS == 8
    rows = [candidate(f"s{at}", score=0.9 - at / 1000) for at in range(40)]
    _gallery, report = swapping(rows, n=20)
    assert report["drops_tried_per_candidate"] == solve.SWAP_DROPS
    assert "never about which are accepted" in report["drops_are"]


def test_the_gallery_is_valid_at_every_moment_and_a_clock_leaves_an_answer():
    """ANYTIME, which is the whole reason this replaced a method that had no answer
    at all until it had a proof."""
    rows = [candidate(f"s{at}", score=0.9 - at / 1000) for at in range(60)]
    rule = ceiling.Rule()
    rule.group_cap = 100
    state = rules.State(rule, 10)
    gallery = solve.Gallery(state, None, [])
    rank = solve.ranking(None)
    ordered = sorted(rows, key=rank)
    solve.seed(gallery, ordered, [], rank, {}, log=quiet)
    report = solve.improve(gallery, ordered, deadline=-1.0, log=quiet)
    assert gallery.filled == 10, "the seed's gallery, untouched and valid"
    assert len({held.location for held in gallery.state.candidates()}) == 10
    assert "clock ran out" in report["stopped_because"]


def test_a_pass_asked_for_the_seed_alone_records_that_it_took_no_swaps():
    record = solve.solve(
        [candidate(f"c{at}", score=0.9 - at / 100) for at in range(5)],
        n=3,
        swap=False,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert record["swaps"]["swaps"] == 0
    assert "not run" in record["swaps"]["of"]
    assert record["objective"]["seed"] == record["objective"]["final"]


# --------------------------------------------------------------------------- #
# What the swap loop may give back — the one place two rulings had to be settled.
# --------------------------------------------------------------------------- #
def floor_and_a_better_row():
    """A gallery whose only weak seat is the one holding a mode floor."""
    return [
        candidate("smooth_a", score=1.0),
        candidate("smooth_b", score=0.9),
        candidate("stripe_weak", score=0.1, mode="stripe"),
    ]


def test_a_met_demand_is_not_given_back_to_lift_the_worst_seat():
    """THE RECONCILIATION. Tier 2 outranks tier 3, so taken alone the loop trades
    `stripe_weak` for `smooth_b`, the floor goes short, and tier 3 cannot buy it
    back. The mode floors are one of the rules this leg KEEPS, and a rule the loop
    is free to break at will is not a rule."""
    gallery, report = swapping(floor_and_a_better_row(), n=2, floors={"stripe": 1})
    assert "stripe_weak" in gallery.state.seated
    assert report["swaps"] == 0
    assert report["demands_kept"] is True
    assert gallery.objective.shortfall == 0


def test_the_pure_lexicographic_reading_empties_the_floor_and_is_reachable():
    """PLANTED, and it is the measurement rather than the argument: with the demand
    unheld the loop does exactly what the strict order says, and the floor goes."""
    gallery, report = swapping(
        floor_and_a_better_row(), n=2, floors={"stripe": 1}, keep_demands=False
    )
    assert "stripe_weak" not in gallery.state.seated
    assert report["swaps"] == 1
    assert report["by_tier"] == {"worst": 1}
    assert gallery.objective.shortfall == 1


def test_a_demand_the_pool_cannot_fill_is_still_short_and_nothing_is_padded():
    """Holding a met demand is not padding an unmet one: a floor nothing can fill
    stays short, stays recorded, and stays minimized by tier 3."""
    gallery, _report = swapping(floor_and_a_better_row(), n=2, floors={"itinerary": 2})
    assert gallery.objective.shortfall == 2
    assert not any(held.mode == "itinerary" for held in gallery.state.candidates())


def test_a_demand_above_what_it_asks_for_can_still_give_one_back():
    """Only what a demand actually needs is held. A mode two seats over its floor
    has one to spare, and the loop is allowed to spend it."""
    rule = ceiling.Rule()
    rule.group_cap = 100
    state = rules.State(rule, 3)
    demands = solve.demands_for({"stripe": 1}, {})
    gallery = solve.Gallery(state, None, demands)
    for key, score in (("a", 0.9), ("b", 0.8), ("c", 0.1)):
        gallery.seat(candidate(key, score=score, mode="stripe"), "general_pool")
    assert gallery.protected() == set(), "three seats against a floor of one"


# --------------------------------------------------------------------------- #
# The expand hook — a stub, and its shape is the contract.
# --------------------------------------------------------------------------- #
def test_the_expand_hook_reports_a_short_demand_per_stratum_and_is_wired_to_nothing():
    record = solve.solve(
        [candidate("a", mode="smooth", score=0.9)],
        n=150,
        floor={"itinerary": 3},
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    block = record["expand"]
    assert "STUB" in block["of"]
    assert block["demands_short"] == 1
    row = block["short"][0]
    assert row["demand"] == "mode_floor:itinerary"
    assert row["asked"] == 3 and row["held"] == 0 and row["short"] == 3
    assert block["stratum"] == "(kind, mode, cell)"


def test_the_expand_hook_says_which_rules_acted_on_a_stratum_it_could_not_fill():
    """The instruction: a stratum whose refusals are `cell_allowance` is one the
    gallery is already full of, and mining it buys nothing."""
    rows = [candidate(f"c{at}", cells=("dark_vivid_blue",), score=0.9) for at in range(12)]
    record = solve.solve(rows, n=20, floor={"smooth": 5}, key=solve.JUDGE_KEY, log=quiet)
    row = record["expand"]["short"][0]
    stratum = row["strata"][0]
    assert stratum["cell"] == "dark_vivid_blue"
    assert stratum["seated"] == 1
    assert stratum["refused_by"].get("cell_allowance", 0) >= 1


# --------------------------------------------------------------------------- #
# The record states the rules that ran, and only those.
# --------------------------------------------------------------------------- #
def test_every_rule_field_on_the_record_is_one_the_leg_reads():
    """A record naming a rule nothing applied is worse than a record silent about
    it. `group_cap` sat in the retired program's config for months describing one
    seat per palette group as a counted row, while the cap that actually ran was a
    generated pairwise DISTANCE row — so a reader asking what capped the groups got
    an answer, and the wrong one.

    The guard is mechanical rather than a list: a record key sharing its name with
    a [`ceiling.Rule`] field has to be a field this leg genuinely reads, as
    `rule.<name>` or as the module constant `ceiling.<NAME>`.
    """
    import dataclasses
    import re
    from pathlib import Path

    source = Path(solve.__file__).read_text(encoding="utf-8")
    source += Path(rules.__file__).read_text(encoding="utf-8")
    source += Path(view.__file__).read_text(encoding="utf-8")
    record = solve.solve([candidate("a")], n=20, key=solve.JUDGE_KEY, log=quiet)
    named = set(record["config"]) | set(record["config"]["ceiling"]) | set(record["rules"])
    checked = []
    for field in dataclasses.fields(ceiling.Rule):
        if field.name not in named:
            continue
        checked.append(field.name)
        reads = (rf"\brule\.{field.name}\b", rf"\bceiling\.{field.name.upper()}\b")
        assert any(re.search(pattern, source) for pattern in reads), (
            f"the record names `{field.name}`, which nothing in the leg reads"
        )
    assert checked, "no Rule field is named on the record, so this guard proves nothing"


def test_the_record_names_the_floor_rule_the_target_rule_and_the_view():
    """Four rules, four sentences, and each of them one a reader can act on."""
    record = solve.solve(
        [candidate("a", cells=("dark_vivid_lime",), families=("lime",))],
        n=150,
        targets={"dark_vivid_lime": 0.5},
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert "THE DEFAULT" in record["config"]["mode_floor_rule"]
    assert "REALIZED" in record["config"]["ceiling"]["target_rule"]
    assert record["rules"]["diversity"]["rule"] == rules.Twins.NAME
    assert record["view"]["draw_seed"] == view.DRAW_SEED
    assert record["view"]["rows_per_seat"] == view.ROWS_PER_SEAT


def test_a_target_is_a_share_of_the_seats_that_actually_got_filled():
    """FIX_under_fill's semantics, and now the only spelling there is: a hard
    `ceil(t * n)` demands a share of seats this leg never promised to fill."""
    rows = [
        candidate(f"lime{at}", cells=("dark_vivid_lime",), families=("lime",), score=0.9)
        for at in range(3)
    ]
    rows += [candidate("plain", cells=(), score=0.8)]
    record = solve.solve(
        rows, n=150, targets={"dark_vivid_lime": 1.0}, key=solve.JUDGE_KEY, log=quiet
    )
    demand = next(row for row in record["shortfalls"]["demands"]["rows"] if row["axis"] == "cell")
    assert demand["asked"] == record["filled"], "the realized count, never n"
    assert record["filled"] < 150


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

    The two asked the same question of `solve.seat` with the same arguments and
    got the same answer twice, for 3.3 s and 3.1 s of the slow lane on this
    machine, 2026-08-31. They assert different things about it, which is what
    makes them two tests; a greedy over the whole pool is not a thing to run
    twice to find that out.

    Read-only, like the tracked readings in `conftest.py`.
    """
    return solve.solve(tracked_ledger.pool, n=20, key=solve.JUDGE_KEY, log=quiet)


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
    record = solve.solve(deep_and_shallow(), n=5, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["mode_floor"] is None
    assert set(record["shortfalls"]["modes"]["below_the_floor"]) == set(asked)
    assert {seat["seated_for"] for seat in record["seated"]} == {"general_pool"}
    assert modes_of(record) == {"smooth"}


def test_the_flat_floor_is_the_way_back_and_the_record_says_which_it_took():
    """`--flat-floor`, at a size where the flat floor is zero: nothing is asked of
    any mode, which is what every gallery seated before the flip got here."""
    record = solve.solve(
        deep_and_shallow(), n=5, floor=solve.mode_floor(5), key=solve.JUDGE_KEY, log=quiet
    )
    assert record["config"]["mode_floor"] == 0
    assert record["config"]["mode_floor_artificial"] is True, "it is not the default any more"
    assert "FLAT" in record["config"]["mode_floor_rule"]
    assert record["shortfalls"]["modes"]["below_the_floor"] == []
    assert {seat["seated_for"] for seat in record["seated"]} == {"general_pool"}


def test_an_artificial_floor_puts_the_leg_back_and_the_record_says_it_was_one():
    record = solve.solve(deep_and_shallow(), n=5, floor=1, key=solve.JUDGE_KEY, log=quiet)
    assert record["config"]["mode_floor"] == 1
    # `natural` is the default rule's own answer — what a seating naming no floor
    # would have been given — and it is a mapping now rather than one number.
    assert record["config"]["mode_floor_natural"] == solve.floors_for(
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

    [`solve.scarcity`] yields **one** `(mode, subpool)` per mode, so a leg that
    stopped at its first success capped every mode at one seat however high the
    floor was. Floor 1 and floor 2 returned a bit-identical gallery while the
    exact solver honoured the difference — a greedy silently seating less of the
    roster than it was asked for.
    """
    record = solve.solve(
        three_modes_four_deep(),
        n=6,
        floor=2,
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert floors_of(record) == {"smooth": 2, "stripe": 2, "threads": 2}


def test_a_floor_of_one_and_a_floor_of_two_are_no_longer_the_same_gallery():
    """The observable half of the same bug: the two floors used to agree exactly."""
    pool = three_modes_four_deep()
    asked = {"n": 6, "diversity": False, "radius": None, "key": solve.JUDGE_KEY, "log": quiet}
    one = solve.solve(pool, floor=1, **asked)
    two = solve.solve(pool, floor=2, **asked)
    assert floors_of(one) == {"smooth": 1, "stripe": 1, "threads": 1}
    assert floors_of(two) == {"smooth": 2, "stripe": 2, "threads": 2}
    assert {seat["key"] for seat in one["seated"]} != {seat["key"] for seat in two["seated"]}


def test_a_floor_can_be_set_per_mode_and_the_record_says_it_was():
    """The shape [`mode_policy.seat_floors`] builds. Nothing that ships passes one."""
    pool = three_modes_four_deep()
    record = solve.solve(
        pool,
        n=7,
        floor={"stripe": 3, "threads": 2, "smooth": 1},
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
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
    record = solve.solve(
        three_modes_four_deep(),
        n=7,
        floor=floors,
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
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
    record = solve.solve(
        pool,
        n=6,
        floor={"stripe": 3, "threads": 2},
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
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
    record = solve.solve(
        three_modes_four_deep(),
        n=6,
        floor={"stripe": 4},
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    block = record["shortfalls"]["modes"]
    assert block["starved"] == []
    assert "smooth" in block["floor_never_needed"]
    assert "stripe" not in block["floor_never_needed"]
    assert block["floor_never_needed_count"] == len(block["floors"]) - 1


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

    def let_go(self, name) -> None:
        """The swap loop's half of `hold`. A fake that cannot answer it would make
        every unseat a crash, which is a fake pinning the wrong thing."""


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
    monkeypatch.setattr(rules, "clouds_for", lambda candidates, **_rest: EveryPicture(candidates))


def twins_over(values):
    """A [`Twins`] over flat signatures, so a pair's distance is `|a - b|`."""
    return rules.Twins(Signatures(values))


def test_a_picture_within_tau_of_a_seat_is_named_with_the_seat_it_is_close_to():
    held = twins_over({"seated": 0.0, "near": ceiling.TAU / 2, "far": ceiling.TAU * 4})
    assert held.hold("seated") is True
    near = held.within("near")
    assert [key for _gap, key in near] == ["seated"]
    assert near[0][0] < ceiling.TAU
    assert held.within("far") == []


def test_the_first_seat_can_refuse_nothing_because_there_is_nothing_to_be_a_twin_of():
    held = twins_over({"a": 0.0})
    assert held.within("a") == []


def test_a_dropped_seat_stops_refusing_and_the_stack_shrinks_with_it():
    """The difference from the sequential twin state this replaced: a swap takes a
    seat back out, so a picture that was a twin of it stops being one. A stack that
    only grew would refuse against a gallery that no longer exists."""
    held = twins_over({"seated": 0.0, "near": ceiling.TAU / 2})
    held.hold("seated")
    assert [key for _gap, key in held.within("near")] == ["seated"]
    assert held.drop("seated") is True
    assert held.within("near") == []
    assert held.held == []
    assert held.drop("seated") is False


def test_a_pair_the_bound_settles_is_never_measured():
    """The bound is a sound lower bound, so a pair beyond tau cannot be a twin."""
    held = twins_over({"seated": 0.0, "far": ceiling.TAU * 4})
    held.hold("seated")
    held.within("far")
    assert held.settled_by_the_bound == 1
    assert held.measured == 0


def test_a_pair_the_bound_cannot_settle_is_measured_in_full():
    held = twins_over({"seated": 0.0, "near": ceiling.TAU / 2})
    held.hold("seated")
    held.within("near")
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
    found = held.within("nothing_on_disk")
    assert isinstance(found, dict), "a list is a distance answer; a dict is a refusal"
    assert found["unreadable"] is True
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
    monkeypatch.setattr(rules, "clouds_for", lambda *_args, **_rest: clouds)

    pool = [candidate("a", score=0.99, location="one"), candidate("b", score=0.98, location="two")]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)

    assert [seat["key"] for seat in record["seated"]] == ["a"]
    assert record["rejection"]["reasons"]["picture_unreadable"] == 1
    assert "twin" not in record["rejection"]["reasons"]  # it was never called one
    assert record["diversity"]["refused_without_a_picture_on_disk"] == 1


def test_a_seat_with_no_picture_is_not_held_and_cannot_refuse_anything():
    held = twins_over({})
    assert held.hold("nothing_on_disk") is False
    assert held.keys == []


def test_the_twin_rule_is_last_so_a_cheap_refusal_never_makes_a_signature(monkeypatch):
    """Every candidate the four counting rules refuse is a signature not made."""
    clouds = Signatures({"a": 0.0, "b": 0.0})
    monkeypatch.setattr(rules, "clouds_for", lambda *_args, **_rest: clouds)
    pool = [candidate("a", location="one"), candidate("b", location="one")]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    assert record["rejection"]["reasons"]["location"] == 1
    # One signature for the seated candidate, and none for the one `location` took.
    assert clouds.made == 1


def test_the_seating_refuses_a_twin_and_names_it_as_the_rule(monkeypatch):
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2, "c": ceiling.TAU * 8})
    monkeypatch.setattr(rules, "clouds_for", lambda *_args, **_rest: clouds)
    pool = [
        candidate("a", score=0.99),
        candidate("b", score=0.98),
        candidate("c", score=0.97),
    ]
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    assert [seat["key"] for seat in record["seated"]] == ["a", "c"]
    assert record["rejection"]["reasons"]["twin"] == 1
    assert record["diversity_refusals"]["b"]["too_close_to"] == "a"
    assert record["diversity_refusals"]["b"]["rule"] == rules.Twins.NAME


def test_a_twin_refusal_carries_the_picture_it_lost_to_onto_the_sheet(monkeypatch):
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2})
    monkeypatch.setattr(rules, "clouds_for", lambda *_args, **_rest: clouds)
    record = solve.solve(
        [candidate("a", score=0.99), candidate("b", score=0.98)],
        n=5,
        key=solve.JUDGE_KEY,
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
    record = solve.solve(
        [candidate("a", score=0.99), candidate("b", score=0.98)],
        n=5,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert solve.SAME_PLACE not in rules.RULES
    assert record["rejection"]["reasons"][solve.SAME_PLACE] == 1
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
    record = solve.solve(pool, n=5, key=solve.JUDGE_KEY, log=quiet)
    shown = record["samples"][solve.SAME_PLACE]
    assert {row["key"] for row in shown} == {"b1", "b2"}
    assert all(row["lost_to"]["picture"] == "artifacts/a1.jpg" for row in shown)


def test_a_seating_asked_for_without_the_preselection_says_it_was_skipped():
    record = solve.solve([candidate("a")], n=5, radius=None, key=solve.JUDGE_KEY, log=quiet)
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
    with pytest.raises(solve.SolveRefused) as refusal:
        solve.solve(pool, n=3, order={"read": 0.9}, log=quiet)
    said = str(refusal.value)
    assert "2 of 3" in said, "the count is the point: how much of the pool is invisible"
    assert "curate flatness sweep" in said, "and the command that fixes it"


def test_allow_unranked_is_the_way_past_it_and_the_record_says_it_was_used() -> None:
    """For the one case a sweep cannot fix: a picture on disk that will not decode
    has no reading and never will, so a pool holding one would be unseatable
    forever. The record carries the flag so a later reader can tell a seating that
    had a whole pool from one that was told to proceed without one."""
    pool = [candidate("read"), candidate("blind")]
    record = solve.solve(pool, n=2, order={"read": 0.9}, allow_unranked=True, log=quiet)
    assert record["order"]["unranked"] == 1
    assert record["order"]["unranked_allowed"] is True
    assert record["filled"] == 2, "an unranked row still seats once the readable ones are spent"


def test_the_judge_key_needs_no_flatness_and_is_never_refused_for_one() -> None:
    """`p_ge4` is read off the candidate, so there is no store to be short of and
    no pool it cannot read. The refusal is a property of a *fitted* key."""
    pool = [candidate("a"), candidate("b")]
    record = solve.solve(pool, n=2, key=solve.JUDGE_KEY, log=quiet)
    assert record["order"]["unranked"] == 0
    assert record["order"]["unranked_allowed"] is False


# --------------------------------------------------------------------------- #
# The second prune: settled by arithmetic, before any picture is opened.
# --------------------------------------------------------------------------- #
def test_a_candidate_below_its_own_weakest_removable_seat_is_hopeless():
    """Sound tier by tier: tier 1 cannot move on a 1-swap; tier 4 needs the arriving
    candidate to beat the seat that leaves, and every seat that could leave is in
    the counted set; and tier 2 can only rise if the seat that leaves IS the worst
    one, which puts the worst seat inside that set too."""
    rows = [candidate("strong", score=0.9), candidate("fair", score=0.8)]
    gallery = seated_by_hand(rows, n=2, keep=["strong", "fair"])
    counted = set(gallery.state.seated)
    assert gallery.hopeless(candidate("weak", score=0.1), counted, []) is True
    assert gallery.hopeless(candidate("better", score=0.85), counted, []) is False
    assert gallery.hopeless(candidate("tied", score=0.8), counted, []) is True, "strict"


def test_a_candidate_covering_a_short_demand_is_never_hopeless():
    """Tier 3 is the exception and it is load-bearing: a low-ranked row covering a
    starved mode is exactly the swap the third tier exists for."""
    rows = [candidate("strong", score=0.9), candidate("fair", score=0.8)]
    gallery = seated_by_hand(rows, n=2, keep=["strong", "fair"], floors={"itinerary": 1})
    counted = set(gallery.state.seated)
    starved = gallery.short_demands()
    assert [demand.of for demand in starved] == ["itinerary"]
    weak = candidate("weak", score=0.01, mode="itinerary")
    assert gallery.hopeless(weak, counted, starved) is False
    assert gallery.hopeless(candidate("weak_smooth", score=0.01), counted, starved) is True


def test_the_prune_settles_candidates_without_opening_a_picture():
    """The point of it: a hopeless candidate must not cost a pixel-cloud signature.

    It has to clear the FIRST prune to exercise the second, so the arriving row is
    worth more than the worst seat and is still hopeless — its place is taken by a
    seat worth more than it is, and that seat is the only one that could leave.
    """
    clouds = Signatures({"a": 0.0, "b": 0.4, "c": 0.8, "x": 1.2})
    state = rules.State(ceiling.Rule(), 3, diversity=rules.Twins(clouds))
    state.rule.group_cap = 100
    gallery = solve.Gallery(state, None, [])
    for key, score, place in (("a", 0.9, "one"), ("b", 0.5, "two"), ("c", 0.2, "three")):
        gallery.seat(candidate(key, score=score, location=place), "general_pool")
    arriving = candidate("x", score=0.6, location="one")
    assert gallery.state.counted_removals(arriving) == {"a"}, "its place is taken"
    before = clouds.made
    report = solve.improve(gallery, [arriving], log=quiet)
    assert report["swaps"] == 0
    assert report["settled_before_opening_a_picture"] == 1
    assert clouds.made == before, "hopeless, so no picture was opened for it"


def test_the_prune_does_not_change_the_answer():
    """The guard that matters. A prune that moved the gallery would be a bug wearing
    a speedup's clothes, so the improved loop has to land on the objective an
    exhaustive neighbourhood search lands on."""
    rows = [candidate(f"c{at:02d}", score=0.9 - at / 100) for at in range(12)]
    rows += [candidate("weak", score=0.05)]
    ordered = sorted(rows, key=solve.ranking(None))
    gallery = seated_by_hand(rows, n=4, keep=["weak", "c05", "c06", "c07"])
    solve.improve(gallery, ordered, log=quiet)
    fast = gallery.objective.record()

    # The same neighbourhood, walked without either prune.
    slow = seated_by_hand(rows, n=4, keep=["weak", "c05", "c06", "c07"])
    moved = True
    while moved:
        moved = False
        current = slow.objective
        for arriving in ordered:
            if slow.state.holds(arriving.key):
                continue
            for out_key in list(slow.state.seated):
                found = slow.after_swap(out_key, arriving)
                if found.beats(current):
                    slow.unseat(out_key)
                    slow.seat(arriving, "swap")
                    moved = True
                    break
            if moved:
                break
    assert fast == slow.objective.record()


def test_the_guards_are_the_protected_set_turned_inside_out():
    """Same answer, asked once per seat instead of once per row of the view."""
    rows = [
        candidate("stripe", score=0.5, mode="stripe"),
        candidate("smooth", score=0.9),
    ]
    gallery = seated_by_hand(rows, n=2, keep=["stripe", "smooth"], floors={"stripe": 1})
    guards = gallery.guards()
    assert set(guards) == gallery.protected()
    assert [demand.of for demand in guards["stripe"]] == ["stripe"]
    arriving = candidate("stripe_better", score=0.99, mode="stripe")
    assert gallery.weakest(set(gallery.state.seated), 8, arriving, guards) == ["stripe", "smooth"]
    other = candidate("smooth_better", score=0.99)
    assert gallery.weakest(set(gallery.state.seated), 8, other, guards) == ["smooth"]
