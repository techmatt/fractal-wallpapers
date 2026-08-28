"""The colour ceiling and the targets: the three tests, the allowance, the steer.

Every claim here is one that decides which wallpaper ships. Nothing renders — the
lens is synthetic, so a candidate's colour and its pixel cloud are stated rather
than measured, and what is pinned is the arithmetic the seating takes over them.
What a real picture reads as is pinned off the committed carrier table in
`tests/test_palette_carriers.py`, which is the other half of the same claim.

**Everything below drives [`ceiling.Seating`] itself**, through [`offer`]. It
used to drive the pre-solver gallery pass's `seat`, which was the only caller the
state machine ever had; that pass was deleted on 2026-08-28 and [`offer`] is its
order restated at the level the ceiling defines it. Three groups of claims went
with the driver rather than being restated, because their subject is the driver
and not the ceiling: what a seating does with **no** rule at all, that a floor
still empties a seat under one, and the on-demand **extra picks** — the loop that
asked the renderer for up to three unseen colours before falling back lived in
that `seat` and nothing in `ceiling.py` implements it.

The last section pins the **literals**. Everything above it is arithmetic in
terms of the constants and would pass unchanged if one of them moved, and these
were calibrated by eye off sheets that are not in the tree — so there is nowhere
else a wrong value could be caught.
"""

from __future__ import annotations

import math

import numpy
import pytest

from fractal_wallpapers.curation import ceiling
from fractal_wallpapers.palettes import dominance, groups, pixel_clouds

SMOOTH, STRANGE = "smooth_render", "strange_render"
WIDTH = groups.DIRECTIONS * groups.QUANTILES


# --------------------------------------------------------------------------- #
# A synthetic lens: a candidate's colour and its cloud are stated, not measured.
# --------------------------------------------------------------------------- #
def cloud_at(value: float):
    """A signature every entry of which is `value`.

    The distance between two of these is exactly `|a - b|`, because the metric is
    the mean absolute difference over the whole vector. That is what lets a test
    say "these two pictures are 0.05 apart" and mean it in the shipping metric.
    """
    return numpy.full(WIDTH, float(value), dtype=numpy.float32)


class Eyes:
    """A lens over stated facts. Same surface as [`ceiling.Lens`], no pictures."""

    def __init__(self, colours=None, clouds=None, palettes=None):
        self.colours = dict(colours or {})
        self.clouds = dict(clouds or {})
        self.palettes = dict(palettes or {})
        self.held: set = set()

    @staticmethod
    def name_of(candidate: dict) -> str:
        return str(candidate["candidate"])

    def reading(self, candidate: dict):
        cells = self.colours.get(self.name_of(candidate))
        if cells is None:
            return None
        return dominance.of_shares(dict(cells))

    def cloud(self, candidate: dict):
        value = self.clouds.get(self.name_of(candidate))
        return None if value is None else cloud_at(value)

    def group(self, candidate: dict) -> str:
        return self.palettes.get(self.name_of(candidate), f"map:{candidate.get('colormap')}")

    def hold(self, candidate: dict) -> None:
        self.held.add(self.name_of(candidate))

    def release(self) -> None:
        self.held.clear()

    def price(self) -> dict:
        return {"readings": len(self.colours), "held": len(self.held)}


def green(share: float = 0.40) -> dict:
    """A share vector whose colour is `dark_vivid_green`, the rest neutral."""
    return {"dark_vivid_green": share, "black": 1.0 - share}


def red(share: float = 0.40) -> dict:
    return {"dark_vivid_red": share, "black": 1.0 - share}


def candidate(identifier: str, key: str = "a", head: str = SMOOTH, p_ge4: float = 0.9) -> dict:
    return {
        "candidate": identifier,
        "source": {"run": "run9", "candidate": identifier, "key": None},
        "origin": {"run": "run9", "candidate": identifier},
        "head": head,
        "partition": "mandelbrot",
        "key": key,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": identifier, "center_im": "0", "width": "1e-3"},
        "maxiter": 1000,
        "mode": "smooth",
        "colormap": f"map-{identifier}",
        "p_ge3": 0.99,
        "p_ge4": p_ge4,
    }


def offer(state, seat_id: str, pool: list, remaining: int | None = None):
    """One seat decided through [`ceiling.Seating`]'s own surface. Returns the seated row.

    The sequential order the ceiling is written for: steer the pool, take the
    first candidate no test refuses, and where nothing clears, record the
    **least-violating** one as a fallback and seat it anyway — because a colour
    rule never empties a seat, and only a floor may.

    `remaining` is how many seats are left including this one, which is what the
    mandate reads; it defaults to one, the urgency at which every target that can
    still be met is mandated.
    """
    state.at(seat_id, 1 if remaining is None else remaining)
    sequence, _note = state.steer(pool)
    blocked = []
    for row in sequence:
        failures = state.failures(row)
        if not failures:
            state.take(row)
            state.done()
            return row
        state.reject(row, failures)
        blocked.append((ceiling.strain(failures), row, failures))
    state.done()
    if not blocked:
        return None
    _cost, row, failures = min(blocked, key=lambda entry: entry[0])
    state.fell_back(row, failures)
    state.take(row)
    return row


def seat_them(rule: ceiling.Rule, seats: list) -> tuple:
    """`(the report, what each seat took)` — one [`ceiling.Seating`] over `seats`.

    `seats` is `[(seat id, the candidates that seat may have)]`, in walk order,
    which is the one thing about a sequential seating the ceiling cares about:
    what an earlier seat took is what a later one is tested against.
    """
    state = rule.begin(len(seats))
    taken = {}
    for index, (seat_id, pool) in enumerate(seats):
        taken[seat_id] = offer(state, seat_id, list(pool), remaining=len(seats) - index)
    return state.report(), taken


# --------------------------------------------------------------------------- #
# 1. The feature, at both levels.
# --------------------------------------------------------------------------- #
def test_dominance_drops_the_neutrals_from_both_halves_of_the_share() -> None:
    """A picture four fifths black and one fifth green is a green picture."""
    reading = dominance.of_shares({"dark_vivid_green": 0.2, "black": 0.8})
    assert reading.cells == ("dark_vivid_green",)
    assert reading.cell_shares["dark_vivid_green"] == pytest.approx(1.0)
    assert reading.neutral == pytest.approx(0.8)


def test_a_cell_is_dominant_by_leading_or_by_size_and_a_picture_may_hold_two() -> None:
    lead = dominance.of_shares(
        {"dark_vivid_green": 0.11, **{name: 0.089 for name in dominance.cells()[:10]}}
    )
    assert lead.cells == ("dark_vivid_green",), "the largest, and over CELL_LEAD"

    both = dominance.of_shares({"dark_vivid_green": 0.5, "dark_vivid_rose": 0.5})
    assert set(both.cells) == {"dark_vivid_green", "dark_vivid_rose"}, "over CELL_ALONE each"

    thin = dominance.of_shares(dict.fromkeys(dominance.cells(), 1.0))
    assert thin.cells == (), "48 equal cells lead at 1/48, under CELL_LEAD"


def test_the_family_rule_is_the_same_rule_at_its_own_two_thresholds() -> None:
    """Green spread over its four cells: no dominant CELL, a dominant FAMILY."""
    share = {name: 0.06 for name in dominance.cells() if dominance.family_of(name) == "green"}
    rest = [name for name in dominance.cells() if name not in share]
    share.update(dict.fromkeys(rest, (1.0 - 4 * 0.06) / len(rest)))
    reading = dominance.of_shares(share)
    assert reading.cells == (), "0.06 of the colour each, under CELL_LEAD"
    assert reading.families == ("green",), "0.24 together, over FAMILY_LEAD"
    assert reading.family_shares["green"] == pytest.approx(0.24)


def test_there_is_no_floor_under_the_raw_share() -> None:
    """The reference picture: 0.27 of the colour, 0.21 of the pixels, green either way."""
    reading = dominance.of_shares({"dark_vivid_green": 0.209, "black": 0.209 / 0.270 - 0.209})
    assert reading.cells == ("dark_vivid_green",)
    assert reading.neutral > reading.cell_shares["dark_vivid_green"] * 0.0


# --------------------------------------------------------------------------- #
# 2. The group cap, and the distance that exempts it.
# --------------------------------------------------------------------------- #
def test_one_seat_per_palette_group_unless_the_pictures_are_far_apart() -> None:
    """Two maps of one group: the second is refused unless its cloud is beyond tau_group.

    "Refused" and not "unseated": a colour rule never empties a seat, so the
    refused candidate comes back as the least-violating fallback and the slot
    fills either way. What moves is the record — a rejection and a flagged
    fallback against an exemption — and that is what a reader steers on.
    """
    for gap, refusals in ((ceiling.TAU_GROUP / 2, 1), (ceiling.TAU_GROUP * 2, 0)):
        eyes = Eyes(
            colours={"a": {"black": 1.0}, "b": {"black": 1.0}},
            clouds={"a": 0.0, "b": gap},
            palettes={"a": "m01", "b": "m01"},
        )
        report, taken = seat_them(
            ceiling.Rule(eyes),
            [("0000", [candidate("a", "k")]), ("0001", [candidate("b", "k")])],
        )
        assert all(taken.values()), "both seats filled; only one of them honestly"
        assert report["rejections_by_test"]["group"] == refusals, f"gap {gap}"
        if refusals:
            refusal = report["rejections"][0]
            assert refusal["test"] == "group"
            assert refusal["margin"]["which"] == "m01"
            assert refusal["margin"]["nearest"] == pytest.approx(gap, abs=1e-6)
            assert len(report["fallbacks"]) == 1
        else:
            assert len(report["exemptions"]) == 1
            assert report["fallbacks"] == []


def test_the_group_cap_is_measured_against_that_group_alone() -> None:
    """A near neighbour in another group does not spend this one's seat."""
    eyes = Eyes(
        colours={name: {"black": 1.0} for name in "abc"},
        clouds={"a": 0.0, "b": 0.0005, "c": 0.001},
        palettes={"a": "m01", "b": "m02", "c": "m03"},
    )
    report, _taken = seat_them(
        ceiling.Rule(eyes),
        [(f"{index:04d}", [candidate(name, "k")]) for index, name in enumerate("abc")],
    )
    assert report["rejections_by_test"]["group"] == 0
    assert report["rejections_by_test"]["twin"] == 1, "the third is a twin of two"


# --------------------------------------------------------------------------- #
# 3. The allowance: pro rata, warmed up by the +1, and only against a dominant.
# --------------------------------------------------------------------------- #
def test_the_allowance_is_floor_k_t_n_plus_one() -> None:
    rule = ceiling.Rule(Eyes())
    for seats in (1, 12, 24, 48, 150):
        assert rule.allowed("dark_vivid_green", seats) == math.floor(2 * seats / 48) + 1
        assert rule.allowed("green", seats) == math.floor(2 * seats / 12) + 1


def test_the_warm_up_is_the_plus_one_and_the_first_seat_may_be_any_colour() -> None:
    """No seat is ever refused for being the first of its colour."""
    rule = ceiling.Rule(Eyes())
    assert rule.allowed("dark_vivid_green", 1) == 1
    assert rule.allowed("green", 1) == 1
    assert rule.allowed("dark_vivid_green", 24) == 2, "a cell's second seat waits for n=24"
    assert rule.allowed("green", 6) == 2, "a family's second waits for n=6"


def test_a_target_replaces_the_allowance_for_its_cell_and_for_its_family() -> None:
    """`red` and not `rose`: green's carriers land a rose cell 1% of the time, and a
    cell a target's carriers reach at all is one this rule moves. Nothing green
    carries red on any reference field."""
    rule = ceiling.Rule(Eyes(), targets={"dark_vivid_green": 0.05})
    assert rule.share("dark_vivid_green") == 0.05
    assert rule.share("green") == 0.05, "the family of a targeted cell moves with it"
    assert rule.share("dark_vivid_red") == ceiling.CELL_SHARE
    assert rule.share("red") == ceiling.FAMILY_SHARE
    assert rule.allowed("dark_vivid_green", 150) == math.floor(2 * 0.05 * 150) + 1 == 16


def test_a_target_raises_the_cells_its_carriers_also_deliver() -> None:
    """The lime hunt's finding, as a rule.

    A carrier of one cell is dominant in more than that cell, so a target that
    raised only its own allowance pushes its own seats against its companions'
    untargeted three. The raise is the target's size times the **measured**
    co-dominance rate, and never an adjacency written down off the hue wheel.
    """
    rule = ceiling.Rule(
        Eyes(),
        targets={"dark_vivid_lime": 0.5},
        co_dominance={"dark_vivid_lime": {"dark_muted_lime": 0.4, "dark_muted_green": 0.1}},
    )
    assert rule.share("dark_muted_lime") == pytest.approx(ceiling.CELL_SHARE + 0.5 * 0.4)
    assert rule.share("dark_muted_green") == pytest.approx(ceiling.CELL_SHARE + 0.5 * 0.1)
    assert rule.share("green") == pytest.approx(ceiling.FAMILY_SHARE + 0.5 * 0.1), (
        "a companion in another family raises that family too"
    )
    assert rule.share("lime") == 0.5, (
        "a companion in the target's OWN family does not: the family row counts a "
        "picture once however many of its cells that picture is dominant in"
    )
    assert rule.share("dark_vivid_red") == ceiling.CELL_SHARE, "nothing else moves"


def test_the_implied_raise_is_read_off_the_tracked_carrier_table() -> None:
    """And the numbers are the record's, not the wheel's."""
    rule = ceiling.Rule(Eyes(), targets={"dark_vivid_lime": 1.0})
    assert rule.implied["dark_muted_lime"] == pytest.approx(0.4211, abs=1e-3)
    assert rule.allowed("dark_muted_lime", 60) == 54, (
        "the cell the n=60 lime solve was thirteen short in, at an allowance of three"
    )
    assert rule.allowed("dark_vivid_red", 60) == 3, "an untouched cell keeps the default"


def test_two_targets_in_one_family_add_up_under_it() -> None:
    """Both have to fit, so the family's allowance is their sum and not the larger."""
    rule = ceiling.Rule(Eyes(), targets={"dark_vivid_green": 0.05, "light_vivid_green": 0.03})
    assert rule.share("green") == pytest.approx(0.08)


def test_only_a_candidate_dominant_in_the_over_allowance_colour_is_refused() -> None:
    """Carrying some of a colour is fine; being it is what the ceiling acts on.

    Three seats of one cell at n<=24, where the allowance is one. The second
    picture that is dominant red is refused; a picture that is a third red without
    leading on it is not.
    """
    carries = {"dark_vivid_red": 0.14, "dark_vivid_blue": 0.86}
    assert dominance.of_shares(carries).cells == ("dark_vivid_blue",)
    eyes = Eyes(
        colours={"a": red(), "b": red(), "c": carries},
        clouds={"a": 0.0, "b": 1.0, "c": 2.0},
        palettes={name: f"m{index:02d}" for index, name in enumerate("abc")},
    )
    # One candidate a seat, so no seat is offered another seat's rejected row and
    # every refusal on the record is a refusal the walk actually took.
    report, taken = seat_them(
        ceiling.Rule(eyes),
        [(f"{index:04d}", [candidate(name, name)]) for index, name in enumerate("abc")],
    )
    refusals = report["rejections"]
    assert [row["candidate"] for row in refusals] == ["b"]
    assert refusals[0]["test"] == "dominance"
    assert refusals[0]["margin"]["which"] == "dark_vivid_red"
    assert refusals[0]["margin"]["allowed"] == 1
    assert taken["0001"]["candidate"] == "b", "refused, then seated as the fallback"
    assert taken["0002"]["candidate"] == "c", "a seventh red, not a red picture"
    assert report["fallbacks"][0]["candidate"] == "b"


# --------------------------------------------------------------------------- #
# 4. The twin test.
# --------------------------------------------------------------------------- #
def test_a_twin_is_m_pictures_inside_tau_and_not_one() -> None:
    inside = ceiling.TAU * 0.4
    eyes = Eyes(
        colours={name: {"black": 1.0} for name in "abc"},
        clouds={"a": 0.0, "b": inside, "c": 2 * inside},
        palettes={name: f"m{index:02d}" for index, name in enumerate("abc")},
    )
    report, taken = seat_them(
        ceiling.Rule(eyes),
        [(f"{index:04d}", [candidate(name, "k")]) for index, name in enumerate("abc")],
    )
    assert ceiling.TWINS == 2
    assert report["rejections_by_test"]["twin"] == 1, "one near neighbour is a pair, not a twin"
    assert taken["0001"] is not None
    refusal = report["rejections"][0]
    assert refusal["test"] == "twin"
    assert refusal["margin"]["which"] == 2
    assert refusal["margin"]["tau"] == ceiling.TAU


def test_tau_is_read_in_the_shipping_metric() -> None:
    """The synthetic clouds are distances in the same units the constant is in."""
    assert pixel_clouds.distance(cloud_at(0.0), cloud_at(ceiling.TAU)) == pytest.approx(ceiling.TAU)


def test_a_picture_just_outside_tau_is_not_a_twin_of_anything() -> None:
    eyes = Eyes(
        colours={name: {"black": 1.0} for name in "abc"},
        clouds={"a": 0.0, "b": ceiling.TAU * 1.01, "c": ceiling.TAU * 2.02},
        palettes={name: f"m{index:02d}" for index, name in enumerate("abc")},
    )
    report, taken = seat_them(
        ceiling.Rule(eyes),
        [(f"{index:04d}", [candidate(name, "k")]) for index, name in enumerate("abc")],
    )
    assert len(taken) == 3 and all(taken.values())
    assert report["rejections"] == []


# --------------------------------------------------------------------------- #
# 5. Targets: the mandate, the preference, and SHORT.
# --------------------------------------------------------------------------- #
def urgency_rule(targets: dict, colours: dict) -> ceiling.Rule:
    return ceiling.Rule(
        Eyes(
            colours=colours,
            clouds=dict.fromkeys(colours, None),
            palettes={name: f"m{index:02d}" for index, name in enumerate(sorted(colours))},
        ),
        targets=targets,
    )


def test_the_mandate_fires_when_every_remaining_seat_is_needed() -> None:
    """Two seats left, two green pictures wanted: only green is eligible."""
    rule = urgency_rule({"dark_vivid_green": 0.5}, {"a": green(), "b": red()})
    state = rule.begin(4)
    assert rule.wanted("dark_vivid_green", 4) == 2
    state.at("0000", remaining=4)
    assert state.urgency()["dark_vivid_green"] == 0.5, "2 needed over 4 left"
    sequence, note = state.steer([candidate("b"), candidate("a")])
    assert "mandated" not in note
    assert note["preferred"] == "dark_vivid_green"
    assert [row["candidate"] for row in sequence] == ["a", "b"], "preferred first, then the judge"

    state.at("0002", remaining=2)
    sequence, note = state.steer([candidate("b"), candidate("a")])
    assert note["mandated"] == ["dark_vivid_green"]
    assert [row["candidate"] for row in sequence] == ["a"], "only the carrier is eligible"


def test_below_half_urgency_the_judge_decides_alone() -> None:
    rule = urgency_rule({"dark_vivid_green": 0.05}, {"a": green(), "b": red()})
    state = rule.begin(150)
    state.at("0000", remaining=150)
    assert state.urgency()["dark_vivid_green"] == pytest.approx(8 / 150)
    sequence, note = state.steer([candidate("b"), candidate("a")])
    assert note == {"urgency": {"dark_vivid_green": round(8 / 150, 4)}}
    assert [row["candidate"] for row in sequence] == ["b", "a"], "untouched"


def test_a_mandate_nothing_can_honour_does_not_empty_the_seat() -> None:
    rule = urgency_rule({"dark_vivid_green": 1.0}, {"b": red()})
    state = rule.begin(1)
    state.at("0000", remaining=1)
    sequence, note = state.steer([candidate("b")])
    assert note["mandate_unmet"] == ["dark_vivid_green"]
    assert [row["candidate"] for row in sequence] == ["b"]
    assert state.unmet == [{"seat": "0000", "cells": ["dark_vivid_green"]}]


def test_an_unmet_target_is_reported_short_and_never_padded() -> None:
    eyes = Eyes(
        colours={"a": red(), "b": red()},
        clouds={"a": None, "b": None},
        palettes={"a": "m01", "b": "m02"},
    )
    report, _taken = seat_them(
        ceiling.Rule(eyes, targets={"dark_vivid_green": 0.5}),
        [("0000", [candidate("a", "k")]), ("0001", [candidate("b", "k")])],
    )
    entry = report["targets"][0]
    assert entry == {
        "cell": "dark_vivid_green",
        "fraction": 0.5,
        "wanted": 1,
        "have": 0,
        "verdict": "SHORT",
        "short_by": 1,
    }
    assert [entry["cell"] for entry in report["targets"]] == ["dark_vivid_green"]
    assert "dark_vivid_green" not in report["dominance"]["cells"], "no seat was invented to hit it"


# --------------------------------------------------------------------------- #
# 6. The fallback, and the replay.
# --------------------------------------------------------------------------- #
def test_a_seat_nothing_clears_takes_the_least_violating_and_says_so() -> None:
    """One group, two pictures on top of each other: the second still seats."""
    eyes = Eyes(
        colours={"a": red(), "b": {"dark_vivid_blue": 1.0}},
        # Inside tau_group, so the exemption does not act; outside tau, so this is
        # the group cap acting alone and not the twin test wearing its name.
        clouds={"a": 0.0, "b": ceiling.TAU_GROUP / 2},
        palettes={"a": "m01", "b": "m01"},
    )
    report, taken = seat_them(
        ceiling.Rule(eyes),
        [("0000", [candidate("a", "k")]), ("0001", [candidate("b", "j")])],
    )
    assert all(taken.values()), "a colour rule never leaves a seat empty; only a floor does"
    fell = report["fallbacks"]
    assert [row["candidate"] for row in fell] == ["b"]
    assert set(fell[0]["failed"]) == {"group"}, "far apart in colour, same map, same picture"
    assert fell[0]["seat"] == "0001"


def test_the_least_violating_is_fewest_tests_then_least_strain() -> None:
    group_only = [{"test": "group", "strain": 0.9}]
    twin_only = [{"test": "twin", "strain": 0.5}]
    both = [{"test": "group", "strain": 0.1}, {"test": "twin", "strain": 0.1}]
    assert ceiling.strain(twin_only) < ceiling.strain(group_only) < ceiling.strain(both)


def test_two_seatings_of_one_state_agree_exactly() -> None:
    """A replay is a replay: same seats, same pool, same rule, same answer."""
    eyes = Eyes(
        colours={name: red() for name in "abc"},
        clouds={"a": 0.0, "b": ceiling.TAU / 3, "c": 2 * ceiling.TAU / 3},
        palettes={name: "m01" for name in "abc"},
    )
    rule = ceiling.Rule(eyes)
    pool = [candidate(name, "k", p_ge4=0.9 - index / 10) for index, name in enumerate("abc")]
    seats = [(f"{index:04d}", [row]) for index, row in enumerate(pool)]
    once, _first = seat_them(rule, seats)
    twice, _again = seat_them(rule, seats)
    assert once["rejections"] == twice["rejections"]
    assert once["fallbacks"] == twice["fallbacks"]


# --------------------------------------------------------------------------- #
# 8. What a target refuses before it spends a render.
# --------------------------------------------------------------------------- #
def test_a_target_naming_something_that_is_not_a_cell_is_refused() -> None:
    with pytest.raises(ceiling.TargetRefused, match="not a chromatic cell"):
        ceiling.parse_target("green=0.05")
    with pytest.raises(ceiling.TargetRefused, match="not a chromatic cell"):
        ceiling.parse_target("black=0.05")
    with pytest.raises(ceiling.TargetRefused, match="cell.=.fraction"):
        ceiling.parse_target("dark_vivid_green")
    with pytest.raises(ceiling.TargetRefused, match="fraction in"):
        ceiling.parse_target("dark_vivid_green=2")
    assert ceiling.parse_target("dark_vivid_green=0.05") == ("dark_vivid_green", 0.05)


def test_targets_that_ask_for_more_than_one_collection_are_refused() -> None:
    with pytest.raises(ceiling.TargetRefused, match="only one collection"):
        ceiling.refuse_targets({"dark_vivid_green": 0.6, "dark_vivid_rose": 0.6}, ["viridis"])


def test_a_cell_with_no_carrier_this_pass_can_draw_is_refused_by_name() -> None:
    with pytest.raises(ceiling.TargetRefused, match="dark_vivid_green"):
        ceiling.refuse_targets({"dark_vivid_green": 0.05}, ["gray"])


def test_a_feasible_target_reports_what_it_may_draw_from() -> None:
    block = ceiling.refuse_targets({"dark_vivid_green": 0.05}, ["Green Vault", "gray"])
    assert block["cells"]["dark_vivid_green"]["carriers"] == 1
    assert block["cells"]["dark_vivid_green"]["best"][0]["map"] == "Green Vault"


# --------------------------------------------------------------------------- #
# The calibrated literals.
# --------------------------------------------------------------------------- #
def test_every_ceiling_constant_is_pinned_at_the_value_it_was_calibrated_to():
    """These were read off sheets by eye and cannot be re-derived from anything
    in the tree. The rest of this file pins the *arithmetic* over them, and would
    pass unchanged on a moved threshold — so a change to one of these numbers is
    a change to which wallpapers ship that no other test would report."""
    assert ceiling.GROUP_CAP == 1, "gallery3: 59 of 91 groups sat above one seat"
    assert ceiling.TAU_GROUP == 0.10, "the twins sheet's three reference pairs, 0.0999-0.1000"
    assert ceiling.K == 2, (
        "family red at 2.45x uniform and dark_vivid_blue at 3.25x are what it acts on"
    )
    assert ceiling.CELL_SHARE == 1.0 / 48.0, "uniform over the codebook's chromatic cells"
    assert ceiling.FAMILY_SHARE == 1.0 / 12.0, "uniform over its hue families"
    assert ceiling.TAU == 0.0586, "Matt's, off the twins ladder, in the ALL-PIXEL metric"
    assert ceiling.TWINS == 2, "one near neighbour is a pair; three of a kind is noticed"
    assert ceiling.MANDATE == 1.0, (
        "u = 1 is every remaining seat, so anything less concedes the target"
    )
    assert ceiling.PREFER == 0.5, "half the remaining seats"
    assert ceiling.TESTS == ("group", "dominance", "twin"), "the order that names a rejection"
    assert ceiling.GROUP_CAP_RATE == 0.025, "Matt, ckpt 88: 1 up to n=40, 3 at n=150, 25 at n=1000"


# --------------------------------------------------------------------------- #
# The two group-cap rules.
# --------------------------------------------------------------------------- #
def test_the_identity_cap_is_one_seat_a_group_at_every_size():
    """The rule every gallery this project has shipped was seated under, and still
    the default. It does not read `n` at all."""
    assert [ceiling.group_cap(n) for n in (1, 20, 150, 1000)] == [1, 1, 1, 1]


@pytest.mark.parametrize(("seats", "cap"), [(20, 1), (39, 1), (40, 1), (150, 3), (1000, 25)])
def test_the_proportional_cap_is_the_three_sizes_the_ruling_names(seats, cap):
    assert ceiling.group_cap(seats, ceiling.PROPORTIONAL) == cap


def test_the_proportional_cap_never_reaches_zero():
    """`floor(0.025 * n)` is zero below forty seats, and a cap of zero is a
    program with no seats in it. So a debug gallery keeps the identity cap under
    either rule, which is why a before/after has to be taken where they differ."""
    assert ceiling.group_cap(0, ceiling.PROPORTIONAL) == 1
    assert ceiling.group_cap(20, ceiling.PROPORTIONAL) == ceiling.group_cap(20)


def test_an_unknown_cap_rule_is_refused_rather_than_read_as_the_default():
    with pytest.raises(ValueError):
        ceiling.group_cap(150, "whatever_matt_meant")


def test_the_two_rules_are_the_two_the_flag_offers():
    assert ceiling.GROUP_CAP_RULES == (ceiling.IDENTITY, ceiling.PROPORTIONAL)


def test_the_two_pixel_cloud_thresholds_stay_the_distance_apart_they_were_set():
    """[`TAU_GROUP`] is the *exemption* from the group cap and not a twin test at
    another number, so it has to be a distance nobody would argue about. If the
    two ever converged the exemption would stop being a real gate."""
    assert ceiling.TAU < ceiling.TAU_GROUP
    assert pytest.approx(1.706, abs=0.001) == ceiling.TAU_GROUP / ceiling.TAU


def test_every_calibrated_constant_reaches_the_pass_record():
    """A run compared against an older one on a moved constant is comparing two
    policies, so the record has to carry them rather than name the module."""
    config = ceiling.Rule().config()
    assert config["group_cap"] == ceiling.GROUP_CAP
    assert config["tau_group"] == ceiling.TAU_GROUP
    assert config["k"] == ceiling.K
    assert config["cell_share"] == ceiling.CELL_SHARE
    assert config["family_share"] == ceiling.FAMILY_SHARE
    assert config["tau"] == ceiling.TAU
    assert config["twins"] == ceiling.TWINS
    assert config["mandate"] == ceiling.MANDATE
    assert config["prefer"] == ceiling.PREFER
    assert config["tests"] == list(ceiling.TESTS)


def test_the_dominance_thresholds_are_pinned_and_the_family_pair_is_twice_the_cell_pair():
    """The rule that decides what a picture is *of*. Nothing else in the tree
    fixes these literals, and the ceiling refuses only a DOMINANT candidate — so
    a moved threshold moves what the ceiling acts on at all."""
    assert dominance.CELL_LEAD == 0.10
    assert dominance.CELL_ALONE == 0.15
    assert dominance.FAMILY_LEAD == 0.20
    assert dominance.FAMILY_ALONE == 0.30
    assert pytest.approx(2 * dominance.CELL_LEAD) == dominance.FAMILY_LEAD
    assert pytest.approx(2 * dominance.CELL_ALONE) == dominance.FAMILY_ALONE
    assert dominance.CELL_LEAD < dominance.CELL_ALONE, "lead-and-be-worth-naming, or be large alone"
    for value in (dominance.CELL_LEAD, dominance.CELL_ALONE, dominance.FAMILY_LEAD):
        assert str(value) in dominance.RULE, "the record spells the rule out, and has to stay right"


# --------------------------------------------------------------------------- #
# The stored reading.
# --------------------------------------------------------------------------- #
def a_block(cells=("dark_vivid_green",), families=("green",)):
    """A ledger row's `colour` block, in the store's own spelling."""
    return {
        "cells": list(cells),
        "families": list(families),
        "cell_shares": {"dark_vivid_green": 0.42, "dark_muted_rose": 0.0301},
        "family_shares": {"green": 0.42, "rose": 0.0301},
        "neutral": 0.210567,
    }


def test_a_stored_colour_block_round_trips_through_a_reading_exactly():
    """The store's five members out and back with nothing moved. If this drifted,
    a lens served off the ledger would be answering a different question from a
    lens served off the picture and nothing would say so."""
    from fractal_wallpapers.curation import candidate_ledger

    block = a_block()
    assert candidate_ledger.colour_block(dominance.of_block(block)) == block


def test_of_block_carries_the_names_and_does_not_re_derive_them():
    """A threshold that moved since a row was written must not quietly re-decide
    that row. The block holds the dominant names outright, so it cannot."""
    absurd = dict(a_block(), cells=["dark_muted_rose"], families=["rose"])
    reading = dominance.of_block(absurd)
    assert reading.cells == ("dark_muted_rose",), "the stored name, not the largest share"
    assert reading.families == ("rose",)
    assert reading.carries("dark_muted_rose") and not reading.carries("dark_vivid_green")


def test_a_lens_given_a_store_reads_it_and_never_touches_the_picture():
    """The saving. A ledger-driven seating holds the reading already; decoding
    the JPEG to be told what the row says is the whole of what this removes."""
    seen: list = []

    def render_of(candidate):
        return f"{candidate['candidate']}.jpg"

    def stored_of(picture):
        seen.append(picture)
        return a_block()

    lens = ceiling.Lens(render_of, lambda _candidate: "group", stored_of=stored_of)
    reading = lens.reading({"candidate": "one"})
    assert reading.cells == ("dark_vivid_green",)
    assert seen == ["one.jpg"], "asked the store, by render path"
    assert lens.price()["readings_stored"] == 1
    assert lens.price()["readings_decoded"] == 0


def test_a_lens_whose_store_has_never_seen_the_render_falls_back_to_the_picture(tmp_path):
    """A pass seating its own fresh candidates has no row about them yet, so the
    store misses and the seating is exactly what it was."""
    picture = tmp_path / "nothing.jpg"
    lens = ceiling.Lens(
        lambda candidate: picture,
        lambda _candidate: "group",
        stored_of=lambda _picture: None,
    )
    assert lens.reading({"candidate": "one"}) is None, "no picture on disk, and no stored block"
    assert lens.price()["readings_stored"] == 0
    assert "one" in lens.unreadable


def test_a_lens_with_no_store_at_all_is_the_lens_that_was_there_before():
    lens = ceiling.Lens(lambda _candidate: None, lambda _candidate: "group")
    assert lens.stored_of is None
    assert lens.reading({"candidate": "one"}) is None
