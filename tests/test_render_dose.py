"""The dose curve: what may not move between two points, and what the axis is cut on.

A dose curve is one claim — *this much data reads like this* — and it survives
exactly one property: **the holdout does not move**. Everything here checks that
property or the ways it could be broken quietly. That the fold's held-out rows
are untouched by the dose, so two points are compared on identical rows. That a
row outside the dose leaves the *training* side rather than the holdout, and that
the era cuts stay nested. That the cut is taken on the batch's registration date
and never on a row's own clock, because half a batch on each side of the axis is
two views of one draw compared against itself. And that the matched draw takes
whole lineages and lands on the row count it claims to match.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import render_cv, render_dose, render_grade, render_train

TRAINED_ON = {"train", render_train.SELECTION}


@pytest.fixture(scope="module")
def dealt(shipped_render_cache):
    """The population and the deal, derived once for every guard in this file."""
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short} — `renders plan` then `renders build`")
    return render_cv.pool(), render_cv.read_assignment()


def test_the_axis_is_cut_on_the_batch_and_the_cuts_are_ordered() -> None:
    """A dose point is a date, the dates increase, and both ends are named."""
    dates = [cut for _name, cut in render_dose.ERA_CUTS]
    assert dates == sorted(dates), "a dose axis whose points are out of order is not an axis"
    names = [name for name, _cut in render_dose.ERA_CUTS]
    assert render_dose.PRE_GROWTH in names and names[-1] == render_dose.GROWN


def test_every_batch_of_both_stores_carries_a_registration_date() -> None:
    """The cut is applied to a batch, so a batch nobody dated would drop out silently."""
    dates = render_dose.registration_dates()
    assert {kind for kind, _batch in dates} == set(render_train.KINDS)
    assert all(len(day) == 10 and day.count("-") == 2 for day in dates.values())


def test_two_draws_of_the_matched_leg_are_actually_independent() -> None:
    """Two draws under one seed would report zero spread and prove nothing."""
    seeds = {
        entry["draw_seed"] for entry in render_dose.POINTS.values() if entry["leg"] == "matched"
    }
    assert len(seeds) == 2


def test_the_stopping_rule_and_the_stop_slice_are_the_incumbent_band_s() -> None:
    """This band moves the data and nothing else, so neither may drift from that band."""
    assert render_dose.RULE == render_grade.SHIPPED_RULE
    assert render_dose.STOP_SHARE == render_grade.STOP_SHARE
    assert render_dose.STOP_SEED == render_grade.STOP_SEED


@pytest.mark.slow
def test_the_holdout_is_the_same_rows_at_every_dose_point(dealt) -> None:
    """The one property the whole design rests on.

    Two points on a curve read on different rows are two numbers about two
    populations, and their difference is unreadable. So the dose may move the
    training side and it may never move what the fold holds out.
    """
    population, document = dealt
    for fold in (0, 4):
        seen = {}
        for point in render_dose.POINTS:
            _rows, pictures, _split = render_dose.sides_for(point, fold, document, population)
            seen[point] = frozenset(
                (picture.kind, picture.name) for picture in pictures if picture.side == "eval"
            )
        distinct = set(seen.values())
        assert len(distinct) == 1, (
            f"fold {fold} holds out different rows at different dose points, so no two "
            f"points on this curve are comparable: {sorted(seen)}"
        )
        assert next(iter(distinct)), "a fold that holds nothing out has measured nothing"


@pytest.mark.slow
def test_the_era_cuts_are_nested_and_subtract_only_from_the_training_side(dealt) -> None:
    """A smaller dose is a subset of a larger one, and the graded rows are untouched."""
    population, document = dealt
    previous, previous_split = None, None
    for name, _cut in render_dose.ERA_CUTS:
        _rows, pictures, split = render_dose.sides_for(name, 0, document, population)
        trained = {
            (picture.kind, picture.name) for picture in pictures if picture.side in TRAINED_ON
        }
        if previous is not None:
            assert previous < trained, f"{name} is not a superset of the cut before it"
            assert split["test_pictures"] == previous_split["test_pictures"]
        previous, previous_split = trained, split


@pytest.mark.slow
def test_a_whole_batch_is_inside_the_dose_or_outside_it(dealt) -> None:
    """Never half of one.

    A batch is one population drawn by one method. Cutting it on the rows' own
    `recorded_at` would put two views of one draw on two sides of the axis — and
    rows do trickle into a batch after it is registered, so the two rules really
    do differ on this corpus rather than agreeing by luck.
    """
    population, document = dealt
    dates = render_dose.registration_dates()
    _rows, pictures, split = render_dose.sides_for(render_dose.PRE_GROWTH, 0, document, population)
    cut = split["dose"]["cut"]
    for picture in pictures:
        if picture.side in TRAINED_ON:
            assert dates[(picture.kind, picture.batch)] <= cut, (
                f"{picture.batch} trains at the {cut} dose although it was registered on "
                f"{dates[(picture.kind, picture.batch)]}"
            )


@pytest.mark.slow
def test_the_matched_draw_takes_whole_lineages_and_lands_on_the_row_count(dealt) -> None:
    """The one leg here that draws anything, and the two things a draw has to obey."""
    population, document = dealt
    _rows, _pictures, anchor = render_dose.sides_for(
        render_dose.PRE_GROWTH, 0, document, population
    )
    target = anchor["dose"]["train_pictures"] + anchor["dose"]["stop_pictures"]
    for point in ("matched_a", "matched_b"):
        _rows, pictures, split = render_dose.sides_for(point, 0, document, population)
        drawn = split["dose"]["train_pictures"] + split["dose"]["stop_pictures"]
        assert drawn <= target, f"{point} drew {drawn} rows against a target of {target}"
        assert drawn > 0.95 * target, (
            f"{point} landed {drawn} rows short of {target}; a matched draw that misses its "
            f"target by more than a few lineages is not matched"
        )
        taken: dict[int, set[bool]] = {}
        for picture, group in zip(pictures, document["group_of_row"], strict=True):
            if picture.side == "eval":
                continue
            taken.setdefault(int(group), set()).add(picture.side in TRAINED_ON)
        pinned = {repr(place) for place in render_train.pinned_everywhere()}
        straddling = [
            group
            for group, seen in taken.items()
            if len(seen) > 1
            and not any(
                picture.place in pinned
                for picture, other in zip(pictures, document["group_of_row"], strict=True)
                if int(other) == group
            )
        ]
        assert not straddling, (
            f"{point} took part of {len(straddling)} lineages, so a near-duplicate of a "
            f"training picture sits outside the dose it was drawn for"
        )


@pytest.mark.slow
def test_a_pinned_location_reaches_neither_the_training_side_nor_the_stop_slice(dealt) -> None:
    """Every dose point, not just the largest: a blind sheet is spent once."""
    population, document = dealt
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    assert pinned, "both stores pin an evaluation side; a test that found none proves nothing"
    for point in render_dose.POINTS:
        _rows, pictures, _split = render_dose.sides_for(point, 2, document, population)
        trespassing = [
            picture
            for picture in pictures
            if picture.place in pinned and picture.side in TRAINED_ON
        ]
        assert not trespassing, (
            f"{len(trespassing)} pinned pictures would be trained or stopped on at {point}"
        )
