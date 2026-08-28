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
    record = seating.seat(deep_and_shallow(), n=5, floor=1, log=quiet)
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
    record = seating.seat(deep_and_shallow(), n=5, floor=1, log=quiet)
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
    record = seating.seat([candidate("a")], n=20, floor=1, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["represented"] == 1
    assert "stripe" in shortfall["below_the_floor"]


def test_the_mode_block_counts_representation_apart_from_the_floor():
    """At twenty seats the floor asks for nothing, and `18 of 18 held` would lie.

    Under the flat floor the block reported held-against-floor and nothing else,
    so a vacuous floor would have read as a gallery holding every mode. What a
    reader of a small gallery wants is how many modes actually took a seat.
    """
    record = seating.seat([candidate("a")], n=20, log=quiet)
    shortfall = record["shortfalls"]["modes"]
    assert shortfall["floor"] == 0
    assert shortfall["asked"] == 0
    assert shortfall["represented"] == 1
    assert shortfall["below_the_floor"] == []


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
def test_the_seating_applies_the_pairwise_rule_and_the_solve_does_not_change():
    record = seating.seat([candidate("a")], n=20, log=quiet)
    assert "APPLIED" in record["config"]["pairwise"]
    assert record["config"]["rules"][-1] == "twin"
    assert "the twin test" in record["config"]["hard"]
    assert record["twins"]["tau"] == ceiling.TAU


def test_a_seating_asked_for_without_the_twin_test_says_so():
    record = seating.seat([candidate("a")], n=20, twin=False, log=quiet)
    assert "NOT applied" in record["config"]["pairwise"]
    assert record["twins"] is None


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
    assert record["config"]["mode_floor"] == solve.mode_floor(20)
    assert record["config"]["mode_floor_artificial"] is False


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


# --------------------------------------------------------------------------- #
# The mode floor, now a function of n.
# --------------------------------------------------------------------------- #
def test_below_a_hundred_seats_the_scarcity_leg_seats_nothing_for_a_floor():
    """The honest shape of a debug gallery: the strongest pictures, not a survey."""
    record = seating.seat(deep_and_shallow(), n=5, log=quiet)
    assert record["config"]["mode_floor"] == 0
    assert {seat["seated_for"] for seat in record["seated"]} == {"general_pool"}
    assert modes_of(record) == {"smooth"}


def test_an_artificial_floor_puts_the_leg_back_and_the_record_says_it_was_one():
    record = seating.seat(deep_and_shallow(), n=5, floor=1, log=quiet)
    assert record["config"]["mode_floor"] == 1
    assert record["config"]["mode_floor_natural"] == 0
    assert record["config"]["mode_floor_artificial"] is True
    assert any(seat["seated_for"].startswith("mode_floor:") for seat in record["seated"])


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


def test_a_candidate_with_no_picture_on_disk_is_admitted_and_counted():
    """A missing file is a fact about this checkout, not about the wallpaper."""
    held = twins_over({"seated": 0.0})
    held.hold("seated")
    assert held.refuses("nothing_on_disk") is None
    assert held.without_a_picture == 1


def test_a_seat_with_no_picture_is_not_held_and_cannot_refuse_anything():
    held = twins_over({})
    assert held.hold("nothing_on_disk") is False
    assert held.keys == []


def test_the_twin_rule_is_last_so_a_cheap_refusal_never_makes_a_signature(monkeypatch):
    """Every candidate the four counting rules refuse is a signature not made."""
    clouds = Signatures({"a": 0.0, "b": 0.0})
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)
    pool = [candidate("a", location="one"), candidate("b", location="one")]
    record = seating.seat(pool, n=5, log=quiet)
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
    record = seating.seat(pool, n=5, log=quiet)
    assert [seat["key"] for seat in record["seated"]] == ["a", "c"]
    assert record["rejection"]["reasons"]["twin"] == 1
    assert record["twin_refusals"]["b"]["twin_of"] == "a"


def test_a_twin_refusal_carries_the_picture_it_lost_to_onto_the_sheet(monkeypatch):
    clouds = Signatures({"a": 0.0, "b": ceiling.TAU / 2})
    monkeypatch.setattr(seating, "clouds_for", lambda *_args, **_rest: clouds)
    record = seating.seat([candidate("a", score=0.99), candidate("b", score=0.98)], n=5, log=quiet)
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
    record = seating.seat([candidate("a", score=0.99), candidate("b", score=0.98)], n=5, log=quiet)
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
    record = seating.seat(pool, n=5, log=quiet)
    shown = record["samples"][seating.SAME_PLACE]
    assert {row["key"] for row in shown} == {"b1", "b2"}
    assert all(row["lost_to"]["picture"] == "artifacts/a1.jpg" for row in shown)


def test_a_seating_asked_for_without_the_preselection_says_it_was_skipped():
    record = seating.seat([candidate("a")], n=5, radius=None, log=quiet)
    assert "skipped" in record["preselection"]
