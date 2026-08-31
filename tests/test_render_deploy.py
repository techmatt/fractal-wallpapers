"""The forward split and the rule that stops on it: what may not leak, and what may not be gamed.

This is the run whose artifact ships, so its guards are about the two things that
would make its comparison worthless. **The forward holdout has to be forward** —
every row registered after the incumbent trained, and every pinned place, on the
side no training touches, with whole lineages either side of the boundary because
two frames a hair apart are the same picture twice. And **the stopping slice has
to be somewhere else again**: a run that early-stopped on the rows it is later
compared on has selected on its own test set, and a run that stopped on a pinned
row has spent a blind sheet.

The rest is the stopping rule's own argument. It is rank-only, which is why it is
not `render_cv.top_cutpoint_selection` — the arm that chose epoch 1 by refusing
to commit — and its top slice is sized at a fraction rather than a count so that
a slice of a different size asks the same question.
"""

from __future__ import annotations

import numpy
import pytest

from fractal_wallpapers.models import render_cv, render_deploy, render_train

HOLDOUT = {render_deploy.COMPARISON, render_deploy.STOPPING}
TOUCHED = {"train", render_deploy.STOPPING}


@pytest.fixture(scope="module")
def split(shipped_render_cache):
    """The forward split, derived once for every guard in this file."""
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short} — `renders plan` then `renders build`")
    rows, pictures, record = render_deploy.sides_for(render_cv.pool())
    return rows, pictures, record


def test_the_top_slice_is_a_fraction_and_never_fewer_than_one_row() -> None:
    """A top slice of nothing is not a precision of zero."""
    labels = numpy.array([1, 2, 3, 4])
    scores = numpy.array([0.1, 0.2, 0.3, 0.9])
    assert render_deploy.precision_at(labels, scores, 0.0)["k"] == 1
    assert render_deploy.precision_at(labels, scores, 0.5)["k"] == 2
    assert render_deploy.precision_at(labels, scores, 1.0)["k"] == 4
    assert render_deploy.precision_at([], [], 0.5)["precision"] is None


def test_precision_counts_the_top_of_the_ranking_and_the_base_rate_of_the_whole() -> None:
    """Both numbers, because a precision without its base rate is not a lift."""
    labels = numpy.array([4, 1, 3, 1, 1, 1, 1, 1, 1, 1])
    scores = numpy.array([0.9, 0.8, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    read = render_deploy.precision_at(labels, scores, 0.3)
    assert read["k"] == 3
    assert read["hits"] == 2
    assert read["precision"] == pytest.approx(2 / 3)
    assert read["base_rate"] == pytest.approx(0.2)


def test_the_stopping_rule_is_rank_only_and_cannot_be_gamed_by_under_confidence() -> None:
    """The whole argument that this is not the arm that chose epoch 1.

    A head that shrinks every probability toward the prior improves a
    cross-entropy at a rare cutpoint and leaves the ORDER alone. This rule reads
    only the order, so the two heads score identically; the cross-entropy rule
    that failed does not.
    """
    labels = numpy.array([1, 2, 3, 4, 4, 2, 3, 1])
    confident = numpy.array(
        [[0.9, p, p / 2] for p in (0.05, 0.10, 0.60, 0.95, 0.90, 0.20, 0.70, 0.02)]
    )
    # Every column pulled toward the prior, so the two rules are compared on one
    # move rather than on which column each of them happens to read.
    shrunk = numpy.array([[0.5 + (v - 0.5) * 0.02 for v in row] for row in confident])
    assert render_deploy.top_slice_precision(
        labels, confident, 4
    ) == render_deploy.top_slice_precision(labels, shrunk, 4)
    assert render_cv.top_cutpoint_loss(labels, confident, 4) != pytest.approx(
        render_cv.top_cutpoint_loss(labels, shrunk, 4)
    )


def test_the_rule_reads_the_boundary_it_scores() -> None:
    """Rank on `P(>=3)`, count a hit at tier 3. One question asked once."""
    assert f"p_ge{render_deploy.HIT_TIER}" == render_deploy.RANK_COLUMN
    assert render_deploy.TOP_SLICE in render_deploy.REPORTED_SLICES


def test_the_rule_takes_a_patience_and_a_hard_cap() -> None:
    """A rule that can run away ships a budget rather than a choice."""
    assert render_deploy.EPOCHS > 0
    assert 0 < render_deploy.PATIENCE < render_deploy.EPOCHS


@pytest.mark.slow
def test_no_lineage_straddles_the_training_boundary(split) -> None:
    """Whole neighbourhoods either side, or the head fits a near-duplicate of its test."""
    from fractal_wallpapers.labeling import groups

    rows, pictures, _record = split
    grouping = groups.assign(rows)
    sides: dict[int, set] = {}
    for picture, group in zip(pictures, grouping.of_row, strict=True):
        sides.setdefault(int(group), set()).add(picture.side in HOLDOUT)
    straddling = [group for group, seen in sides.items() if len(seen) > 1]
    assert not straddling, (
        f"{len(straddling)} lineages sit on both sides of the training boundary, so the head "
        f"fits a near-duplicate of a row it is judged on"
    )


@pytest.mark.slow
def test_every_row_registered_after_the_incumbent_trained_is_held_out(split) -> None:
    """The forward half of the split, and the reason the comparison is fair at all."""
    _rows, pictures, record = split
    dates = render_deploy.registration_dates()
    trained = [
        picture
        for picture in pictures
        if picture.side in TOUCHED
        and dates[(picture.kind, picture.batch)] > render_deploy.SHIPPED_CUT
    ]
    assert not trained, (
        f"{len(trained)} rows registered after {render_deploy.SHIPPED_CUT} are trained or "
        f"stopped on, so the incumbent and this head cannot be compared on them"
    )
    assert record["constraints"]["post_growth_rows"] > 0


@pytest.mark.slow
def test_a_pinned_place_is_neither_trained_on_nor_stopped_on(split) -> None:
    """A blind sheet is spent once, and this run does not spend it."""
    _rows, pictures, _record = split
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    assert pinned, "both stores pin an evaluation side; a test that found none proves nothing"
    trespassing = [
        picture for picture in pictures if picture.place in pinned and picture.side in TOUCHED
    ]
    assert not trespassing, (
        f"{len(trespassing)} pinned pictures would be trained or stopped on, which spends an "
        f"instrument this run is not allowed to touch"
    )


@pytest.mark.slow
def test_the_stopping_slice_is_disjoint_from_the_comparison_side(split) -> None:
    """Stopping on the rows a comparison is reported from is selection on the test set."""
    _rows, pictures, record = split
    stopping = {
        (picture.kind, picture.name)
        for picture in pictures
        if picture.side == render_deploy.STOPPING
    }
    comparison = {
        (picture.kind, picture.name)
        for picture in pictures
        if picture.side == render_deploy.COMPARISON
    }
    assert stopping and comparison
    assert not (stopping & comparison)
    assert record["stopping_slice"]["rows"] == len(stopping)
    assert record["comparison_slice"]["rows"] == len(comparison)


@pytest.mark.slow
def test_the_holdout_keeps_the_ones_and_twos(split) -> None:
    """Precision in a top slice only bites where a wrong row could have been ranked."""
    _rows, _pictures, record = split
    for slice_name in ("stopping_slice", "comparison_slice"):
        tiers = record[slice_name]["tiers"]
        assert int(tiers.get("1", 0)) + int(tiers.get("2", 0)) > 0, (
            f"the {slice_name} holds no 1s or 2s, so a top slice of it cannot punish anything"
        )


@pytest.mark.slow
def test_the_shipped_cut_reproduces_the_incumbent_s_own_recorded_population(split) -> None:
    """The date is checked against the run it claims to date, not asserted.

    The incumbent's `metrics.json` records how many pictures it held. Cutting the
    batches at [`render_deploy.SHIPPED_CUT`] has to land on that number, give or
    take the rows this population drops and the handful labeled since — if it
    does not, the cut is dating the wrong day and every row on the wrong side of
    it is a row in the wrong half of the split.
    """
    import json

    rows, pictures, _record = split
    path = render_train.head_dir(render_deploy.INCUMBENT_RUN) / "metrics.json"
    if not path.is_file():
        pytest.skip(f"{path} is not on this machine")
    held = int(json.loads(path.read_text(encoding="utf-8"))["pictures"]["total"])
    dates = render_deploy.registration_dates()
    before = sum(
        1
        for picture in pictures
        if dates[(picture.kind, picture.batch)] <= render_deploy.SHIPPED_CUT
    )
    assert abs(before - held) < 0.02 * held, (
        f"cutting at {render_deploy.SHIPPED_CUT} leaves {before} rows and "
        f"{render_deploy.INCUMBENT_RUN} recorded {held}. The cut is dating the wrong day."
    )
    assert len(rows) == len(pictures)
