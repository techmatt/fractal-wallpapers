"""The colour ceiling and the targets: the three tests, the allowance, the steer.

Every claim here is one that decides which wallpaper ships. Nothing renders — the
lens is synthetic, so a candidate's colour and its pixel cloud are stated rather
than measured, and what is pinned is the arithmetic the seating takes over them.
The feature itself is pinned in `tests/test_colour_dominance.py`, over real
pictures, which is the other half of the same claim.
"""

from __future__ import annotations

import math

import numpy
import pytest

from fractal_wallpapers.curation import ceiling, floors, gallery
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


def slot(identifier: str, keys: list, head: str = SMOOTH, partition: str = "mandelbrot"):
    return gallery.Slot(
        id=identifier, partition=partition, head=head, point=keys[0], locations=list(keys)
    )


def quiet(_line) -> None:
    return None


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
        slots = [slot("0000", ["k"]), slot("0001", ["k"], partition="phoenix")]
        report = gallery.seat(
            slots,
            [candidate("a", "k", p_ge4=0.9), candidate("b", "k", p_ge4=0.8)],
            log=quiet,
            rule=ceiling.Rule(eyes),
        )
        assert report["filled"] == 2, "both slots filled; only one of them honestly"
        assert report["ceiling"]["rejections_by_test"]["group"] == refusals, f"gap {gap}"
        if refusals:
            refusal = report["ceiling"]["rejections"][0]
            assert refusal["test"] == "group"
            assert refusal["margin"]["which"] == "m01"
            assert refusal["margin"]["nearest"] == pytest.approx(gap, abs=1e-6)
            assert len(report["ceiling"]["fallbacks"]) == 1
        else:
            assert len(report["ceiling"]["exemptions"]) == 1
            assert report["ceiling"]["fallbacks"] == []


def test_the_group_cap_is_measured_against_that_group_alone() -> None:
    """A near neighbour in another group does not spend this one's seat."""
    eyes = Eyes(
        colours={name: {"black": 1.0} for name in "abc"},
        clouds={"a": 0.0, "b": 0.0005, "c": 0.001},
        palettes={"a": "m01", "b": "m02", "c": "m03"},
    )
    slots = [slot(f"{index:04d}", ["k"], partition=name) for index, name in enumerate("abc")]
    report = gallery.seat(
        slots,
        [candidate(name, "k", p_ge4=0.9 - index / 10) for index, name in enumerate("abc")],
        log=quiet,
        rule=ceiling.Rule(eyes),
    )
    assert report["ceiling"]["rejections_by_test"]["group"] == 0
    assert report["ceiling"]["rejections_by_test"]["twin"] == 1, "the third is a twin of two"


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
    # One candidate a slot, so no slot is offered another slot's rejected row and
    # every refusal on the record is a refusal the walk actually took.
    slots = [slot(f"{index:04d}", [name], partition=name) for index, name in enumerate("abc")]
    report = gallery.seat(
        slots,
        [candidate(name, name, p_ge4=0.9 - index / 10) for index, name in enumerate("abc")],
        log=quiet,
        rule=ceiling.Rule(eyes),
    )
    refusals = report["ceiling"]["rejections"]
    assert [row["candidate"] for row in refusals] == ["b"]
    assert refusals[0]["test"] == "dominance"
    assert refusals[0]["margin"]["which"] == "dark_vivid_red"
    assert refusals[0]["margin"]["allowed"] == 1
    assert slots[1].seated["candidate"] == "b", "refused, then seated as the fallback"
    assert slots[2].seated["candidate"] == "c", "a seventh red, not a red picture"
    assert report["ceiling"]["fallbacks"][0]["candidate"] == "b"


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
    slots = [slot(f"{index:04d}", ["k"], partition=name) for index, name in enumerate("abc")]
    report = gallery.seat(
        slots,
        [candidate(name, "k", p_ge4=0.9 - index / 10) for index, name in enumerate("abc")],
        log=quiet,
        rule=ceiling.Rule(eyes),
    )
    assert ceiling.TWINS == 2
    assert slots[1].seated is not None, "one near neighbour is a pair, not a twin"
    refusal = report["ceiling"]["rejections"][0]
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
    slots = [slot(f"{index:04d}", ["k"], partition=name) for index, name in enumerate("abc")]
    report = gallery.seat(
        slots,
        [candidate(name, "k", p_ge4=0.9 - index / 10) for index, name in enumerate("abc")],
        log=quiet,
        rule=ceiling.Rule(eyes),
    )
    assert report["filled"] == 3
    assert report["ceiling"]["rejections"] == []


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
    slots = [slot("0000", ["k"]), slot("0001", ["k"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [candidate("a", "k", p_ge4=0.9), candidate("b", "k", p_ge4=0.8)],
        log=quiet,
        rule=ceiling.Rule(eyes, targets={"dark_vivid_green": 0.5}),
    )
    entry = report["ceiling"]["targets"][0]
    assert entry == {
        "cell": "dark_vivid_green",
        "fraction": 0.5,
        "wanted": 1,
        "have": 0,
        "verdict": "SHORT",
        "short_by": 1,
    }
    assert [entry["cell"] for entry in report["ceiling"]["targets"]] == ["dark_vivid_green"]
    assert not any("dark_vivid_green" in report["ceiling"]["dominance"]["cells"] for _ in [0]), (
        "no seat was invented to hit it"
    )


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
    slots = [slot("0000", ["k"]), slot("0001", ["j"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [candidate("a", "k"), candidate("b", "j", p_ge4=0.8)],
        log=quiet,
        rule=ceiling.Rule(eyes),
    )
    assert report["filled"] == 2, "a colour rule never leaves a seat empty; only a floor does"
    fell = report["ceiling"]["fallbacks"]
    assert [row["candidate"] for row in fell] == ["b"]
    assert set(fell[0]["failed"]) == {"group"}, "far apart in colour, same map, same picture"
    assert slots[1].fill["ceiling"]["fallback"]["candidate"] == "b"


def test_the_least_violating_is_fewest_tests_then_least_strain() -> None:
    group_only = [{"test": "group", "strain": 0.9}]
    twin_only = [{"test": "twin", "strain": 0.5}]
    both = [{"test": "group", "strain": 0.1}, {"test": "twin", "strain": 0.1}]
    assert ceiling.strain(twin_only) < ceiling.strain(group_only) < ceiling.strain(both)


def test_a_re_seat_replays_the_sequence_and_the_seats_before_it_do_not_move() -> None:
    """The whole sequence is retaken, so a slot that moved cannot change its elders.

    Path dependence is what the ceiling adds, and it only ever runs forwards: the
    state a seat is tested against is what the seats BEFORE it in the walk took.
    So re-deciding a later slot leaves every earlier one on the candidate it had.
    """
    colours = {name: red() for name in "abcd"}
    eyes = Eyes(
        colours=colours,
        clouds={"a": 0.0, "b": 1.0, "c": 2.0, "d": 3.0},
        palettes={name: f"m{index:02d}" for index, name in enumerate("abcd")},
    )
    rule = ceiling.Rule(eyes)
    pool = [
        candidate("a", "k"),
        candidate("b", "j", p_ge4=0.8),
        candidate("c", "j", p_ge4=0.7),
        candidate("d", "i", p_ge4=0.6),
    ]
    slots = [slot("0000", ["k"]), slot("0001", ["j"], partition="phoenix")]
    first = gallery.seat(slots, pool, log=quiet, rule=rule)
    before = slots[0].seated["candidate"]

    # The second slot stands somewhere else and the whole seating is taken again.
    slots[1].locations = ["i"]
    second = gallery.seat(slots, pool, log=quiet, rule=rule)
    assert slots[0].seated["candidate"] == before
    assert slots[1].seated["candidate"] == "d"
    assert first["ceiling"]["seats"] == second["ceiling"]["seats"] == 2


def test_two_seatings_of_one_state_agree_exactly() -> None:
    """A replay is a replay: same slots, same pool, same rule, same answer."""
    eyes = Eyes(
        colours={name: red() for name in "abc"},
        clouds={"a": 0.0, "b": ceiling.TAU / 3, "c": 2 * ceiling.TAU / 3},
        palettes={name: "m01" for name in "abc"},
    )
    rule = ceiling.Rule(eyes)
    pool = [candidate(name, "k", p_ge4=0.9 - index / 10) for index, name in enumerate("abc")]
    slots = [slot(f"{index:04d}", ["k"], partition=name) for index, name in enumerate("abc")]
    once = gallery.seat(slots, pool, log=quiet, rule=rule)
    twice = gallery.seat(slots, pool, log=quiet, rule=rule)
    assert once["ceiling"]["rejections"] == twice["ceiling"]["rejections"]
    assert once["ceiling"]["fallbacks"] == twice["ceiling"]["fallbacks"]


# --------------------------------------------------------------------------- #
# 7. Without a rule, the seating is the seating it was.
# --------------------------------------------------------------------------- #
def test_no_rule_means_no_ceiling_anywhere_on_the_record() -> None:
    slots = [slot("0000", ["k"])]
    report = gallery.seat(slots, [candidate("a", "k")], log=quiet)
    assert "ceiling" not in report
    assert "ceiling" not in slots[0].fill
    assert "palette_group" not in slots[0].seated
    assert floors.CLUSTER_CAP == 1


def test_the_floors_still_act_under_a_ceiling_and_nothing_is_seated_from_under_one() -> None:
    low = dict(candidate("a", "k", head=STRANGE))
    low["p_ge3"] = 0.1
    slots = [slot("0000", ["k"], head=STRANGE)]
    report = gallery.seat(slots, [low], log=quiet, rule=ceiling.Rule(Eyes()))
    assert slots[0].seated is None
    assert slots[0].unfilled == "below_bar"
    assert report["ceiling"]["fallbacks"] == []


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


def test_targets_that_ask_for_more_than_one_gallery_are_refused() -> None:
    with pytest.raises(ceiling.TargetRefused, match="only one gallery"):
        gallery.refuse_targets({"dark_vivid_green": 0.6, "dark_vivid_rose": 0.6}, ["viridis"])


def test_a_cell_with_no_carrier_this_pass_can_draw_is_refused_by_name() -> None:
    with pytest.raises(ceiling.TargetRefused, match="dark_vivid_green"):
        gallery.refuse_targets({"dark_vivid_green": 0.05}, ["gray"])


def test_a_feasible_target_reports_what_it_may_draw_from() -> None:
    block = gallery.refuse_targets({"dark_vivid_green": 0.05}, ["Green Vault", "gray"])
    assert block["cells"]["dark_vivid_green"]["carriers"] == 1
    assert block["cells"]["dark_vivid_green"]["best"][0]["map"] == "Green Vault"


# --------------------------------------------------------------------------- #
# 9. The extra picks: what stands between a refusal and a fallback.
# --------------------------------------------------------------------------- #
class Renderer:
    """An `OnDemand` that states its pictures instead of making them."""

    def __init__(self, offers: dict):
        #: `map -> (colour share vector, cloud value)` this fake will hand back.
        self.offers = dict(offers)
        self.asked: list = []

    def spend(self, candidate: dict, spent: set, families: set):
        self.asked.append((str(candidate["candidate"]), frozenset(spent), frozenset(families)))
        for name, (_share, _cloud) in self.offers.items():
            if name not in spent:
                return {**candidate, "candidate": f"d-{name}", "colormap": name, "p_ge3": 0.99}
        return None

    def price(self) -> dict:
        return {"rendered": len(self.asked)}


def test_a_refused_seat_asks_for_a_colour_it_has_not_tried_before_falling_back() -> None:
    """The whole shape of the addendum: refuse, render, seat — and only then fall back."""
    eyes = Eyes(
        colours={"a": red(), "b": red(), "d-Green Vault": green()},
        clouds={"a": 0.0, "b": 1.0, "d-Green Vault": 2.0},
        palettes={"a": "m01", "b": "m02", "d-Green Vault": "m03"},
    )
    slots = [slot("0000", ["k"]), slot("0001", ["j"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [candidate("a", "k"), candidate("b", "j", p_ge4=0.8)],
        log=quiet,
        rule=ceiling.Rule(eyes),
        extra=Renderer({"Green Vault": (green(), 2.0)}),
    )
    assert report["ceiling"]["rejections_by_test"]["dominance"] == 1, "the second red"
    assert report["ceiling"]["fallbacks"] == [], "and it did not have to fall back"
    assert slots[1].seated["candidate"] == "d-Green Vault"
    assert slots[1].fill["ceiling"]["extra_picks"] == 1
    assert report["ceiling"]["on_demand"]["seats_that_asked"] == 1
    assert report["ceiling"]["on_demand"]["seats_it_filled"] == 1


def test_the_extra_picks_are_bounded_and_then_the_fallback_takes_the_seat() -> None:
    """Three colours a seat cannot use is a seat the neighbourhood cannot fill."""
    extras = {f"map{index}": (red(), 3.0 + index) for index in range(9)}
    eyes = Eyes(
        colours={"a": red(), "b": red(), **{f"d-{name}": red() for name in extras}},
        clouds={
            "a": 0.0,
            "b": 1.0,
            **{f"d-{name}": 3.0 + index for index, name in enumerate(extras)},
        },
        palettes={
            "a": "m01",
            "b": "m02",
            **{f"d-{name}": f"g{index}" for index, name in enumerate(extras)},
        },
    )
    renderer = Renderer(extras)
    slots = [slot("0000", ["k"]), slot("0001", ["j"], partition="phoenix")]
    report = gallery.seat(
        slots,
        [candidate("a", "k"), candidate("b", "j", p_ge4=0.8)],
        log=quiet,
        rule=ceiling.Rule(eyes),
        extra=renderer,
    )
    assert gallery.EXTRA_PICKS == 3
    assert len(renderer.asked) == 3, "bounded per seat, and it is the seat that is bounded"
    assert slots[1].fill["ceiling"]["extra_picks"] == 3
    assert len(report["ceiling"]["fallbacks"]) == 1, "and then the least-violating one"
    assert report["ceiling"]["on_demand"]["seats_it_filled"] == 0


def test_a_seat_that_filled_or_that_was_empty_never_asks_for_a_render() -> None:
    """The cost lands on the seats the ceiling bit, and on no others."""
    eyes = Eyes(colours={"a": red()}, clouds={"a": 0.0}, palettes={"a": "m01"})
    renderer = Renderer({"Green Vault": (green(), 2.0)})
    filled = [slot("0000", ["k"])]
    gallery.seat(filled, [candidate("a", "k")], log=quiet, rule=ceiling.Rule(eyes), extra=renderer)
    assert renderer.asked == [], "it seated on the first candidate"

    empty = [slot("0000", ["nobody"])]
    gallery.seat(empty, [], log=quiet, rule=ceiling.Rule(eyes), extra=renderer)
    assert empty[0].unfilled == "no_candidates"
    assert renderer.asked == [], "nothing was refused, so there is nothing to render around"


def test_what_the_seat_has_already_tried_is_read_off_the_pictures() -> None:
    """The screen avoids colours the seat's own renders turned out to be.

    Not the colours the recolours predicted: the recolour is a smooth field and
    the attempt drew a mode, and over gallery3's strange rows half the picture's
    colour lands in different families from the one the screen looked at.
    """
    eyes = Eyes(
        colours={"a": red(), "b": {"dark_vivid_blue": 1.0}},
        clouds={"a": 0.0, "b": ceiling.TAU_GROUP / 2},
        palettes={"a": "m01", "b": "m01"},
    )
    renderer = Renderer({"Green Vault": (green(), 2.0)})
    slots = [slot("0000", ["k"]), slot("0001", ["j"], partition="phoenix")]
    gallery.seat(
        slots,
        [candidate("a", "k"), candidate("b", "j", p_ge4=0.8)],
        log=quiet,
        rule=ceiling.Rule(eyes),
        extra=renderer,
    )
    _who, spent, families = renderer.asked[0]
    assert families == frozenset({"blue"}), "what the refused picture WAS, not what its map is"
    assert "map-b" in spent
