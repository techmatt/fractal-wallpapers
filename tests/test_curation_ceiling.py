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

import inspect
import math

import numpy
import pytest
from tests.test_solve import a_pool_the_fine_head_has_read  # noqa: F401 — autouse here too

from fractal_wallpapers.curation import ceiling
from fractal_wallpapers.palettes import dominance, groups, pixel_clouds

SMOOTH, STRANGE = "smooth_render", "strange_render"
WIDTH = pixel_clouds.DIRECTIONS * groups.QUANTILES


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
        assert rule.allowed("dark_vivid_green", seats) == math.floor(ceiling.K * seats / 48) + 1
        assert rule.allowed("green", seats) == math.floor(ceiling.K * seats / 12) + 1


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
    assert rule.allowed("dark_vivid_green", 150) == math.floor(ceiling.K * 0.05 * 150) + 1 == 23


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
    """And the numbers are the record's, not the wheel's.

    **The record moves when the library does, and this reading is of the table as
    it stands.** `dark_vivid_lime` is carried by 27 maps now against 24 before
    `classic-pairs-2026-09`, and its companion rate on `dark_muted_lime` read
    0.4211 over the smaller table and reads 0.380952 over this one — a delivery is
    a (map, field) picture, so three new carriers re-weight the denominator. What
    is being pinned is that the raise comes off the record at all, which is why the
    value is exact rather than a band.
    """
    rule = ceiling.Rule(targets={"dark_vivid_lime": 1.0})
    assert rule.implied["dark_muted_lime"] == pytest.approx(0.380952, abs=1e-3)
    assert rule.allowed("dark_muted_lime", 60) == 73, (
        "the cell the n=60 lime solve was thirteen short in, at an allowance of four"
    )
    assert rule.allowed("dark_vivid_red", 60) == 4, "an untouched cell keeps the default"


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
    assert ceiling.K == 3, (
        "Matt 2026-09-09 off the K sweep, replacing the 2 that family red at 2.45x uniform "
        "and dark_vivid_blue at 3.25x were what it acted on. At n=1000 the cell allowance "
        "goes 42 to 63 and the sum 1891 to 1939"
    )
    assert ceiling.KF == 1, (
        "Matt 2026-09-09, shipped with K=3 in one act: one fair share under, three over. "
        "floor(Kf * t * n) is 20 of a thousand seats and takes NO + 1"
    )
    assert ceiling.CELL_SHARE == 1.0 / 48.0, "uniform over the codebook's chromatic cells"
    assert ceiling.FAMILY_SHARE == 1.0 / 12.0, "uniform over its hue families"
    assert ceiling.TAU == 0.034281, (
        "Matt 2026-09-05, by eye and not off a sitting: exactly 0.90x the 0.03809 set "
        "2026-09-02, which was 0.65x the 0.0586 read off the twins ladder. ALL-PIXEL metric"
    )
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
    two ever converged the exemption would stop being a real gate.

    The **gap** is the pin and the ratio is the reading of it. It was 1.706 while
    `TAU` was 0.0586, 2.625 after the 2026-09-02 ruling took `TAU` to 0.65x that,
    and 2.917 since the 2026-09-05 ruling took it to 0.90x again. `TAU_GROUP` has
    not moved through either, so each loosening makes the exemption a wider gate
    than it was rather than a narrower one. So this is re-baselined a second time
    and the sentence above it is unchanged: what it guards is that they do not
    converge.
    """
    assert ceiling.TAU < ceiling.TAU_GROUP
    assert pytest.approx(2.917, abs=0.001) == ceiling.TAU_GROUP / ceiling.TAU


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
    """The store's two members out and back with nothing moved. If this drifted,
    a lens served off the ledger would be answering a different question from a
    lens served off the picture and nothing would say so.

    Two and not five: the share vectors came off the row on 2026-08-29 because no
    reader had ever opened one. What still has to round-trip is the pair that
    every reader does take."""
    from fractal_wallpapers.curation import candidate_ledger

    block = a_block()
    assert candidate_ledger.colour_block(dominance.of_block(block)) == {
        "cells": block["cells"],
        "families": block["families"],
    }


def test_a_block_written_under_the_old_shape_still_reads_its_shares_back():
    """The store stopped writing the shares; it did not stop being able to read
    a row that has them. Every row on disk before 2026-08-29 carries them."""
    reading = dominance.of_block(a_block())
    assert reading.cell_shares["dark_vivid_green"] == pytest.approx(0.42)
    assert reading.family_shares["green"] == pytest.approx(0.42)
    assert reading.neutral == pytest.approx(0.210567)


def test_of_block_carries_the_names_and_does_not_re_derive_them():
    """A threshold that moved since a row was written must not quietly re-decide
    that row. The block holds the dominant names outright, so it cannot."""
    absurd = dict(a_block(), cells=["dark_muted_rose"], families=["rose"])
    reading = dominance.of_block(absurd)
    assert reading.cells == ("dark_muted_rose",), "the stored name, not the largest share"
    assert reading.families == ("rose",)
    assert reading.carries("dark_muted_rose") and not reading.carries("dark_vivid_green")


# --------------------------------------------------------------------------- #
# The themed cap: three times the main gallery's rate, on `n` alone.
# --------------------------------------------------------------------------- #
class Row:
    """The two fields [`ceiling.capable_groups`] reads off a candidate."""

    def __init__(self, group, location):
        self.group = group
        self.location = location


def pool_of(sizes: dict) -> list:
    """`{group: how many distinct places it fields}` as rows, plus a repeat.

    Each group gets one extra row at a place it already holds, so a test that
    counted rows instead of places would read every size one too high.
    """
    rows = []
    for group, count in sizes.items():
        rows += [Row(group, f"{group}-{at}") for at in range(count)]
        rows.append(Row(group, f"{group}-0"))
    return rows


def test_the_themed_cap_is_three_times_the_main_gallerys_rate_on_n_alone():
    """A share of `n` since Matt's ruling of 2026-09-05, which replaced `ceil(2n/P)`
    — that moved with the pool, so two themes at one `n` ran under two caps and one
    theme ran under two caps either side of a night's mining, and no before/after on
    a theme was a controlled read. The share is Matt's value of 2026-09-12: at a
    twentieth the cap was 10 at n=200 and bound at 10 of 10 in four of the five
    cells solved that day."""
    assert ceiling.THEMED_GROUP_CAP_RATE == 0.075
    # Three times the general rate, and `0.075 != 3 * 0.025` in binary floating
    # point — the multiple is the argument and the literal is the constant, so the
    # two are asserted apart rather than chained.
    assert pytest.approx(3 * ceiling.GROUP_CAP_RATE) == ceiling.THEMED_GROUP_CAP_RATE
    assert ceiling.themed_group_cap(200) == 15
    assert ceiling.themed_group_cap(1000) == 75
    assert ceiling.themed_group_cap(150) == 11
    # It takes `n` and nothing else — the pool is not an argument any more, which
    # is the whole of the ruling.
    assert list(inspect.signature(ceiling.themed_group_cap).parameters) == ["n"]


def test_the_themed_cap_never_reaches_zero():
    """A cap of zero is a program with no seats in it. `floor(0.075 n)` is zero
    below fourteen seats, so a debug themed gallery keeps the identity cap there.
    A before/after on this rule has to be taken at **n=27 or above** — fourteen is
    where the floor stops acting, and from there to twenty-six the cap is one
    seat, which is what the identity cap says too."""
    assert ceiling.themed_group_cap(13) == 1
    assert ceiling.themed_group_cap(14) == 1
    assert ceiling.themed_group_cap(26) == 1, "still the identity cap's answer"
    assert ceiling.themed_group_cap(27) == 2, "the first n where the two rules differ"
    assert ceiling.themed_group_cap(40) == 3
    assert ceiling.themed_group_cap(0) == 1
    assert ceiling.themed_group_cap(-5) == 1


def test_P_counts_distinct_places_and_never_rows():
    """One wallpaper per location is absolute, so a group with fifty rows at one
    place can take exactly one seat and its capacity is one."""
    capable = ceiling.capable_groups(pool_of({"deep": 5, "flat": 3}), places=3)
    assert capable == {"deep": 5, "flat": 3}


def test_a_group_under_the_floor_is_not_counted_in_P():
    """P is a reading of what the pool can field: a group that can never take more
    than one seat would report a capacity that does not exist."""
    pool = pool_of({"deep": 9, "two": 2, "one": 1})
    assert set(ceiling.capable_groups(pool)) == {"deep"}
    assert set(ceiling.capable_groups(pool, places=1)) == {"deep", "two", "one"}
    assert ceiling.THEMED_CAP_PLACES == 3


def test_the_themed_cap_is_not_a_rule_a_caller_may_name():
    """It is the rule a themed pass HAS rather than one a caller names, so it is
    spelled for the record and kept out of the two `--group-cap` accepts."""
    assert ceiling.THEMED not in ceiling.GROUP_CAP_RULES
    with pytest.raises(ValueError, match="group cap rule"):
        ceiling.group_cap(150, ceiling.THEMED)


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing — the solve leg is chatty and this file is not."""


# --------------------------------------------------------------------------- #
# The per-mode ceiling: a share of the FILLED seats, one mode at a time.
# --------------------------------------------------------------------------- #
def seated_of(record) -> dict:
    """`{mode: how many seats it took}` off a finished record."""
    held: dict = {}
    for seat in record["seated"]:
        held[seat["mode"]] = held.get(seat["mode"], 0) + 1
    return held


def test_the_shipped_ceiling_is_threads_at_a_fifth_and_it_is_the_solves_own_default():
    """Matt's ruling of 2026-09-05. The default lives on `solve` and not only on
    the flag, for `DEFAULT_SPIRAL_CAP`'s reason: a bare call and a typed command
    must not be two answers to what this leg does."""
    from fractal_wallpapers.curation import solve

    assert solve.DEFAULT_MODE_CEILINGS == {"threads": 0.20}
    assert inspect.signature(solve.solve).parameters["mode_ceilings"].default == (
        solve.DEFAULT_MODE_CEILINGS
    )
    # The number it is set against: `threads` took 187 of 1,000 seats on
    # 2026-09-05, so a fifth is a GUARD above what the gallery does unaided.
    assert ceiling.share_of(0.20, 1000) == 200 > 187


def test_the_allowance_is_the_spiral_caps_arithmetic_and_not_a_second_spelling():
    """`ceil(share * (filled + 1))` through `ceiling.share_of`, which is also what
    a colour target and the spiral share cap are stated in. The `+ 1` is the same
    warm-up: without it the first seat of an empty gallery is refused for taking
    100% of nothing."""
    from fractal_wallpapers.curation import rules

    state = rules.State(ceiling.Rule(), n=100, mode_ceilings={"threads": 0.20})
    assert state.mode_allowance("threads") == ceiling.share_of(0.20, 1) == 1
    assert state.mode_allowance("smooth") is None, "a mode the ceiling does not name"
    assert state.spiral_allowance() is None, "and the two caps are independent"


def test_the_ceiling_sits_last_among_the_counted_rules():
    """The placement IS the measurement: a candidate refused here is one every
    colour rule already admitted, so the column counts seats the ceiling cost and
    not seats the allowance would have refused anyway."""
    from fractal_wallpapers.curation import rules

    assert rules.RULES.index("mode_ceiling") == rules.RULES.index("spiral") + 1
    counted = rules.RULES[: rules.RULES.index("picture_unreadable")]
    assert counted[-1] == "mode_ceiling"


def test_the_ceiling_refuses_by_mode_and_names_itself_in_the_column():
    """Twelve `threads` candidates into six seats at a fifth: the ceiling takes
    the count down to what `ceil(0.20 * (filled + 1))` allows, and the refusals
    are attributed to it rather than to the rule above it."""
    from tests.test_headroom import candidate

    from fractal_wallpapers.curation import solve

    pool = [candidate(f"t{at}", mode="threads", score=0.99) for at in range(12)]
    pool += [candidate(f"s{at}", mode="smooth", score=0.50) for at in range(12)]
    record = solve.solve(
        pool, n=6, floor=0, diversity=False, radius=None, key=solve.JUDGE_KEY, log=quiet
    )
    assert seated_of(record)["threads"] == 2, "ceil(0.2 * 6) = 2, reached one seat at a time"
    assert record["rules"]["refusals_while_choosing"]["mode_ceiling"] > 0
    assert record["rules"]["mode_ceiling_seats"] == {"threads": 2}
    assert record["rules"]["mode_ceiling_allowance"] == {"threads": 2}
    # And with no ceiling the same pool seats `threads` everywhere it can.
    uncapped = solve.solve(
        pool,
        n=6,
        floor=0,
        mode_ceilings={},
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert seated_of(uncapped)["threads"] == 6
    assert uncapped["rules"]["refusals_while_choosing"]["mode_ceiling"] == 0
    assert uncapped["rules"]["mode_ceilings"] == {}


def test_the_ceiling_is_a_SET_constraint_and_the_swap_loop_reads_it_as_one():
    """A candidate the ceiling refuses can be seated if one seat of ITS OWN mode
    leaves, which is the same shape the group cap and the allowances state their
    requirement in — and is what lets the 1-swap trade inside a capped mode
    instead of writing it off."""
    from tests.test_headroom import candidate

    from fractal_wallpapers.curation import rules

    state = rules.State(ceiling.Rule(group_cap=99), n=10, mode_ceilings={"threads": 0.20})
    state.seat(candidate("t0", mode="threads"), "seeded")
    wanted = state.counted_requirements(candidate("t1", mode="threads"))
    assert wanted == [{"t0"}], "one seat of the same mode has to go"
    assert state.counted_refusal(candidate("t1", mode="threads")) == "mode_ceiling"
    assert state.counted_refusal(candidate("s0", mode="smooth")) is None


def test_a_mode_floor_the_ceiling_cannot_reach_goes_SHORT_rather_than_relaxing():
    """The collision is real at small `n` and the answer is the one the objective
    already gives everywhere else: unfilled beats padded. A floor of four
    `threads` against a fifth of six seats is two short, and the shortfall block
    says which rule refused."""
    from tests.test_headroom import candidate

    from fractal_wallpapers.curation import solve

    pool = [candidate(f"t{at}", mode="threads", score=0.99) for at in range(6)]
    pool += [candidate(f"s{at}", mode="smooth", score=0.50) for at in range(6)]
    record = solve.solve(
        pool,
        n=6,
        floor={"threads": 4, "smooth": 0},
        diversity=False,
        radius=None,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    block = record["shortfalls"]["modes"]["per_mode"]["threads"]
    assert block["seated"] == 2 and block["short"] == 2
    assert block["refused_by"]["mode_ceiling"] > 0


def test_the_ceiling_and_the_default_are_both_on_the_config_a_manifest_carries():
    """`config` is the block a tentative gallery's TRACKED manifest carries whole,
    which is the spiral cap's own argument for being there: a record that cannot
    say whether a rule ran is a record nothing can be compared with."""
    from tests.test_headroom import candidate

    from fractal_wallpapers.curation import solve

    # `radius=None` for the reason `tests/test_solve.py` keeps an empty embedding
    # store for: no place here is in the real neutral store, so the pre-selection
    # would sweep twenty-nine thousand rows to learn it can see none of them —
    # 1.3 s a call, and this file's claim is about `config` rather than the pool.
    pool = [candidate("a", mode="smooth", score=0.9)]
    capped = solve.solve(pool, n=4, radius=None, key=solve.JUDGE_KEY, log=quiet)
    assert capped["config"]["mode_ceilings"] == {"threads": 0.20}
    assert capped["config"]["mode_ceilings_default"] == solve.DEFAULT_MODE_CEILINGS
    uncapped = solve.solve(pool, n=4, mode_ceilings={}, radius=None, key=solve.JUDGE_KEY, log=quiet)
    assert uncapped["config"]["mode_ceilings"] == {}
    assert uncapped["config"]["mode_ceilings_default"] == solve.DEFAULT_MODE_CEILINGS, (
        "a record says what it ran AND what it would have run, so a reader of an "
        "uncapped record does not have to date it"
    )


def test_a_growth_rung_says_which_side_of_the_ruling_it_was_drawn_on():
    """A ladder is a series taken over weeks and this rule arrived on 2026-09-05,
    so a rung carries the ceilings it solved under exactly as it carries the
    spiral cap."""
    from fractal_wallpapers.curation import growth

    body = inspect.getsource(growth)
    assert '"mode_ceilings": dict(record["config"].get("mode_ceilings") or {})' in body


def test_the_ceiling_is_in_force_on_a_themed_pass_too():
    """A theme narrows the COLOUR and says nothing about the mode, so a runaway is
    a runaway there as well — which is why this is not one of the three things
    `--themed` swaps."""
    from tests.test_headroom import candidate

    from fractal_wallpapers.curation import solve

    # One palette group each: the THEMED group cap is `max(1, floor(0.075 n))`,
    # which is one seat a group at n=6, and a pool sharing one group would come up
    # short for that reason rather than for this one.
    pool = [
        candidate(
            f"t{at}",
            mode="threads",
            score=0.99,
            p_ge3=0.99,
            cells=("dark_vivid_lime",),
            group=f"map:t{at}",
        )
        for at in range(12)
    ]
    # In the theme too, and weaker, so the seats the ceiling refuses `threads` are
    # seats something can fill: a ceiling that stalls a gallery for want of any
    # other candidate would read as binding harder than it does.
    pool += [
        candidate(
            f"s{at}",
            mode="smooth",
            score=0.50,
            p_ge3=0.99,
            cells=("dark_vivid_lime",),
            group=f"map:s{at}",
        )
        for at in range(12)
    ]
    record = solve.solve(
        pool,
        n=6,
        theme="dark_vivid_lime",
        targets={"dark_vivid_lime": 1.0},
        floor=0,
        radius=None,
        key=solve.JUDGE_KEY,
        log=quiet,
    )
    assert record["config"]["mode_ceilings"] == {"threads": 0.20}
    assert seated_of(record)["threads"] == 2


# --------------------------------------------------------------------------- #
# `--mode-ceiling`, the counterfactual's flag.
# --------------------------------------------------------------------------- #
def folded(*flags) -> dict:
    """`--mode-ceiling`'s repeated arguments, parsed and folded as a handler does."""
    from fractal_wallpapers import cli
    from fractal_wallpapers.cli import curate_commands

    parsed = cli.build_parser().parse_args(["curate", "solve", "run", "--n", "150", *flags])
    return curate_commands.mode_ceilings_named(parsed.mode_ceiling)


def test_the_flag_folds_onto_the_shipped_ceiling_left_to_right():
    """Repeatable, and `none` clears everything to its left — which is how the
    uncapped arm of a counterfactual read is spelled."""
    from fractal_wallpapers.curation import solve

    assert folded() == solve.DEFAULT_MODE_CEILINGS
    assert folded("--mode-ceiling", "none") == {}
    assert folded("--mode-ceiling", "threads=0.15") == {"threads": 0.15}
    assert folded("--mode-ceiling", "smooth=0.5") == {"threads": 0.20, "smooth": 0.5}
    assert folded("--mode-ceiling", "none", "--mode-ceiling", "smooth=0.5") == {"smooth": 0.5}
    assert folded("--mode-ceiling", "smooth=0.5", "--mode-ceiling", "none") == {}


def test_zero_is_a_ceiling_and_never_the_spelling_for_none():
    """`ceiling.share_of(0, anything)` is zero, so a mode at 0 may take no seat at
    all and the refusal column fills. Keeping that apart from `none` is the same
    distinction `--spiral-cap` draws."""
    assert folded("--mode-ceiling", "threads=0") == {"threads": 0.0}
    assert ceiling.share_of(0.0, 1000) == 0


def test_a_mode_no_gallery_can_seat_is_refused_at_the_flag_and_not_at_the_seat():
    """A ceiling on a misspelt mode can never bind and would read on the record as
    a guard that held — `ceiling.parse_target`'s argument, one rule over."""
    import argparse

    from fractal_wallpapers.cli import curate_commands

    with pytest.raises(argparse.ArgumentTypeError, match="not a mode"):
        curate_commands.mode_ceiling_value("thredas=0.2")
    with pytest.raises(argparse.ArgumentTypeError, match="MODE=SHARE"):
        curate_commands.mode_ceiling_value("threads")
    with pytest.raises(argparse.ArgumentTypeError, match="not a share"):
        curate_commands.mode_ceiling_value("threads=x")
    with pytest.raises(argparse.ArgumentTypeError, match="not a share"):
        curate_commands.mode_ceiling_value("threads=-1")
