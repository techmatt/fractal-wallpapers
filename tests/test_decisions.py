"""The four outcomes a judge's score becomes, and the frames that show them."""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import floors
from fractal_wallpapers.models import decisions
from fractal_wallpapers.supply import currency


def test_the_ladder_is_the_three_heights_and_nothing_of_its_own() -> None:
    """`decision_of` composes the owners of the junk floor, the keeper floor and
    the great cut. A fourth number here would be a fourth place to move one."""
    assert decisions.decision_of(floors.JUNK_FLOOR - 1e-9) == decisions.REFUSED
    assert decisions.decision_of(floors.JUNK_FLOOR) == decisions.EXPANDABLE
    assert decisions.decision_of(currency.GOOD_FLOOR - 1e-9) == decisions.EXPANDABLE
    assert decisions.decision_of(currency.GOOD_FLOOR) == decisions.FIND
    assert decisions.decision_of(currency.GOOD_FLOOR, currency.GREAT_CUT) == decisions.EXCEPTIONAL
    assert decisions.decision_of(currency.GOOD_FLOOR, currency.GREAT_CUT - 1e-9) == decisions.FIND


def test_a_reading_with_no_score_is_refused_and_not_a_fifth_outcome() -> None:
    """A crashed render and a bad location must not be the same number — but they
    are the same *decision*, because nothing downstream treats them apart."""
    assert decisions.decision_of(None) == decisions.REFUSED
    assert decisions.decision_of(None, 0.9) == decisions.REFUSED


def test_the_great_cut_cannot_lift_a_frame_over_the_keeper_floor() -> None:
    """The cut decides what a find is *called*, never whether it is one. A head
    confident about the top class and unconvinced about the floor is still below
    the floor."""
    assert decisions.decision_of(floors.JUNK_FLOOR, 1.0) == decisions.EXPANDABLE


def test_the_shipped_run_is_read_off_the_weights_manifest() -> None:
    """The frames have to come from the head production uses, not from whichever
    run last wrote a scores file beside it."""
    assert decisions.shipped_run("location")
    with pytest.raises(decisions.DecisionError):
        decisions.shipped_run("a head nobody ships")


@pytest.mark.slow
def test_the_family_the_figure_uses_reaches_all_four_outcomes() -> None:
    """The figure's whole content is the ladder, so its family has to have rungs.
    Checked against the shipped head's own tracked read of the held-out side."""
    pytest.importorskip("numpy", reason="resolving the scores path imports the training stack")
    rows = decisions.held_out()
    spread = decisions.coverage(rows)["julia:multibrot3"]
    assert all(spread[name] > 0 for name in decisions.DECISIONS), spread
    picks = decisions.chosen(rows, "julia:multibrot3")
    assert set(picks) == set(decisions.DECISIONS)
    for name, row in picks.items():
        assert decisions.decision_of(row["p_ge3"], row["p_ge4"]) == name
        assert row["side"] == "eval"
        assert row["score"] is not None


def test_a_family_that_cannot_show_the_ladder_is_refused_by_name() -> None:
    """A figure drawn from three of four outcomes is a figure with a hole in it,
    and the refusal has to say which rung is missing."""
    rows = [
        {"partition": "phoenix", "p_ge3": 0.01, "p_ge4": 0.0, "location_id": 1},
        {"partition": "phoenix", "p_ge3": 0.2, "p_ge4": 0.0, "location_id": 2},
    ]
    with pytest.raises(decisions.DecisionError, match="find"):
        decisions.chosen(rows, "phoenix")
    with pytest.raises(decisions.DecisionError):
        decisions.chosen(rows, "mandelbrot")


def test_the_pick_inside_an_outcome_is_the_median_and_not_the_best() -> None:
    """A typical member of the bucket, by a stated rule, so re-running the command
    draws the same frames — and so the figure is not four cherry-picked pictures."""
    rows = [
        {"partition": "p", "p_ge3": value, "p_ge4": 0.0, "location_id": index}
        for index, value in enumerate([0.5, 0.9, 0.6, 0.7])
    ]
    assert decisions.median_row(rows)["p_ge3"] == 0.6
    # Two middles: the lower one, chosen rather than averaged.
    assert decisions.median_row(rows[:2])["p_ge3"] == 0.5
    ties = [{"partition": "p", "p_ge3": 0.5, "p_ge4": 0.0, "location_id": key} for key in (9, 3, 7)]
    assert decisions.median_row(ties)["location_id"] == 7
