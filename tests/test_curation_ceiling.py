"""The colour ceiling and the targets: the allowance, and what a target implies.

Every claim here is one that decides which wallpaper ships. Nothing renders and
nothing is measured off a picture — what is pinned is the arithmetic two readers
take over rows they already hold. What a real picture reads as is pinned off the
committed carrier table in `tests/test_palette_carriers.py`, which is the other
half of the same claim.

**This module used to drive `ceiling.Seating` through a synthetic lens**, and both
went on 2026-08-28 with the pre-solver gallery pass that was the state machine's
only caller. Twenty blocks went with them — the `Eyes` lens, the `offer` and
`seat_them` drivers, and every claim whose subject was the walk rather than the
allowance: the group cap's exemption, the twin test, the mandate-and-preference
urgency ladder, the least-violating fallback, the replay, and the pass record.
The rules they pinned are not unguarded: the group cap, the twin test and the
mode floor are `curation.seating`'s now and `tests/test_seating.py` pins them
where they live.

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
def test_the_allowance_is_floor_k_t_n_plus_one() -> None:
    rule = ceiling.Rule()
    for seats in (1, 12, 24, 48, 150):
        assert rule.allowed("dark_vivid_green", seats) == math.floor(2 * seats / 48) + 1
        assert rule.allowed("green", seats) == math.floor(2 * seats / 12) + 1


def test_the_warm_up_is_the_plus_one_and_the_first_seat_may_be_any_colour() -> None:
    """No seat is ever refused for being the first of its colour."""
    rule = ceiling.Rule()
    assert rule.allowed("dark_vivid_green", 1) == 1
    assert rule.allowed("green", 1) == 1
    assert rule.allowed("dark_vivid_green", 24) == 2, "a cell's second seat waits for n=24"
    assert rule.allowed("green", 6) == 2, "a family's second waits for n=6"


def test_a_target_replaces_the_allowance_for_its_cell_and_for_its_family() -> None:
    """`red` and not `rose`: green's carriers land a rose cell 1% of the time, and a
    cell a target's carriers reach at all is one this rule moves. Nothing green
    carries red on any reference field."""
    rule = ceiling.Rule(targets={"dark_vivid_green": 0.05})
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
    rule = ceiling.Rule(targets={"dark_vivid_lime": 1.0})
    assert rule.implied["dark_muted_lime"] == pytest.approx(0.4211, abs=1e-3)
    assert rule.allowed("dark_muted_lime", 60) == 54, (
        "the cell the n=60 lime solve was thirteen short in, at an allowance of three"
    )
    assert rule.allowed("dark_vivid_red", 60) == 3, "an untouched cell keeps the default"


def test_two_targets_in_one_family_add_up_under_it() -> None:
    """Both have to fit, so the family's allowance is their sum and not the larger."""
    rule = ceiling.Rule(targets={"dark_vivid_green": 0.05, "light_vivid_green": 0.03})
    assert rule.share("green") == pytest.approx(0.08)


def test_tau_is_read_in_the_shipping_metric() -> None:
    """The synthetic clouds are distances in the same units the constant is in."""
    assert pixel_clouds.distance(cloud_at(0.0), cloud_at(ceiling.TAU)) == pytest.approx(ceiling.TAU)


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
