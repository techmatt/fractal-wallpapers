"""The grading harness: what it stops on, what it averages, and where it fits a crossover.

Four things a reader has to be able to check. That the stop slice is drawn over
LINEAGES and comes out of the training side rather than the graded holdout —
either failure makes the graded number optimistic and it could not also be the
grading statistic. That the second stopping rule is rank-only, which is the whole
of the argument that it is not the deleted screen's `top_cutpoint_selection`. That the seed
band is averaged rather than maximized, because reporting the better of two draws
reports the maximum of two draws as if it were the design. And that a crossover
carries the sentence saying it is not a floor.
"""

from __future__ import annotations

import numpy
import pytest

from fractal_wallpapers.models import render_folds, render_grade, render_train


@pytest.fixture(scope="module")
def dealt(shipped_render_cache, shipped_label_pool):
    """The population and the deal, derived once for every guard in this file.

    The population through `conftest.shipped_label_pool` — the session's one reading —
    and the deal **derived** rather than read off disk. A written assignment is dealt
    over the corpus of the day it was written, and these guards assert over row
    indices into it, so a store that has grown since reds every one of them for a
    reason that is not in the code. `assignment` is the same call a run makes.
    """
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short} — `renders plan` then `renders build`")
    return shipped_label_pool.pool(), shipped_label_pool.assignment()


def an_out_of_fold_row(name: str, score: int, p_ge4: float, **changes) -> dict:
    row = {
        "kind": "strange_render",
        "name": name,
        "score": score,
        "lineage": int(name[-1]) if name[-1].isdigit() else 0,
        "mode": "tia",
        "fold": 0,
        "seed": 0,
        "batch": "a_batch",
        "p_ge2": 0.9,
        "p_ge3": 0.7,
        "p_ge4": p_ge4,
    }
    row.update(changes)
    return row


def test_the_second_rule_is_rank_only_and_cannot_be_gamed_by_under_confidence() -> None:
    """The whole argument that this is not the arm that chose epoch 1.

    A head that shrinks every score toward the prior improves a cross-entropy at a
    rare cutpoint and leaves the ORDER alone. So the shipped selection objective
    moves and this one does not, which is the difference between the two.
    """
    labels = numpy.array([1, 2, 3, 4, 4, 2])
    confident = numpy.array([[0.9, 0.8, p] for p in (0.05, 0.10, 0.60, 0.95, 0.90, 0.20)])
    shrunk = numpy.array([[0.9, 0.8, 0.5 + (p - 0.5) * 0.05] for p in confident[:, 2]])
    assert render_grade.negative_top_auc(labels, confident, 4) == render_grade.negative_top_auc(
        labels, shrunk, 4
    )
    assert render_folds.top_cutpoint_loss(labels, confident, 4) != pytest.approx(
        render_folds.top_cutpoint_loss(labels, shrunk, 4)
    )


def test_an_undefined_auc_is_never_the_chosen_epoch() -> None:
    """A slice with no fours has not scored badly; it has not scored."""
    labels = numpy.array([1, 2, 3, 3])
    probabilities = numpy.array([[0.9, 0.8, p] for p in (0.1, 0.2, 0.3, 0.4)])
    assert render_grade.negative_top_auc(labels, probabilities, 4) == float("inf")


def test_the_seed_band_is_averaged_rather_than_maximized() -> None:
    """Both seeds' probabilities, meaned per picture. Not whichever came out ahead."""
    first = [an_out_of_fold_row("a1", 4, 0.2, seed=0)]
    second = [an_out_of_fold_row("a1", 4, 0.8, seed=1)]
    (merged,) = render_grade.averaged([first, second])
    assert merged["p_ge4"] == pytest.approx(0.5)
    assert merged["seed"] == [0, 1]


def test_two_seeds_that_do_not_cover_the_same_pictures_are_refused() -> None:
    """A quiet intersection would average two different populations together."""
    with pytest.raises(render_grade.GradingError):
        render_grade.averaged(
            [[an_out_of_fold_row("a1", 4, 0.2)], [an_out_of_fold_row("b2", 4, 0.8)]]
        )


def test_the_arms_differ_in_the_aspect_and_in_nothing_else() -> None:
    """Arm B closes the aspect gap at the SHIPPED width, and moves nothing else.

    The width is the load-bearing half. Aspect and resolution are two questions
    and the resolution one is answered by a scoring check over retired
    checkpoints, so an arm that widened the input while correcting the aspect
    would confound them and could answer neither.
    """
    assert render_grade.ARMS["A"]["target_dims"] is None
    assert render_grade.ARMS["B"]["target_dims"] == list(render_grade.ASPECT_DIMS)
    assert render_grade.ASPECT_DIMS[0] == render_grade.SHIPPED_DIMS[0]
    width, height = render_grade.ASPECT_DIMS
    assert width * render_grade.SOURCE_ASPECT[1] == height * render_grade.SOURCE_ASPECT[0]
    assert set(render_grade.ARMS["A"]) == set(render_grade.ARMS["B"])


def test_a_crossover_says_it_is_not_a_floor() -> None:
    """Fitted at label geometry on a judge that is not regime-robust. Say so, always."""
    rows = [
        an_out_of_fold_row(f"a{index}", 4 if index % 2 else 2, index / 40, lineage=index)
        for index in range(40)
    ]
    document = render_grade.crossovers(rows)
    assert "no bar is set here" in document["not_a_floor"]
    assert "LABEL" in document["geometry"]
    assert document["cutpoints"]["ge4"]["primed_bar"] == render_grade.PRIMED_BAR
    # Both cutpoints, because only one of them has ever been measured.
    assert set(document["cutpoints"]) == {"ge3", "ge4"}


def test_a_per_mode_crossover_is_withheld_where_the_count_cannot_support_one() -> None:
    """A crossover on a handful of rows moves whole tenths on one verdict."""
    rows = [an_out_of_fold_row(f"a{index}", 4, 0.5, mode="rare") for index in range(4)]
    (entry,) = render_grade._per_mode_crossovers(rows, 4)
    assert entry["crossing"] is None
    assert "withheld" in entry


@pytest.mark.slow
def test_the_stop_slice_comes_out_of_the_training_side_and_never_the_holdout(dealt) -> None:
    """A run that early-stopped on the graded split cannot also be graded on it."""
    population, document = dealt
    for fold in range(document["folds"]):
        _rows, pictures, split = render_grade.sides_for(fold, document, population)
        held = {picture.name for picture in pictures if picture.side == "eval"}
        stopping = {picture.name for picture in pictures if picture.side == render_train.SELECTION}
        assert held and stopping
        assert not (held & stopping), (
            f"fold {fold} chooses its epoch on {len(held & stopping)} of the rows it is "
            f"graded on, which makes the graded number optimistic"
        )
        assert split["stop_slice"]["pictures"] == len(stopping)


@pytest.mark.slow
def test_no_lineage_straddles_the_stop_slice_boundary(dealt) -> None:
    """The unit is the lineage throughout, not the place the trainer's own rule draws."""
    population, document = dealt
    for fold in range(document["folds"]):
        _rows, pictures, _split = render_grade.sides_for(fold, document, population)
        sides: dict[int, set] = {}
        for picture, group in zip(pictures, document["group_of_row"], strict=True):
            if picture.side in {"train", render_train.SELECTION}:
                sides.setdefault(int(group), set()).add(picture.side)
        straddling = [group for group, seen in sides.items() if len(seen) > 1]
        assert not straddling, (
            f"{len(straddling)} lineages in fold {fold} sit on both sides of the stop "
            f"slice, so a near-duplicate of a training picture chooses the epoch"
        )


@pytest.mark.slow
def test_a_pinned_location_reaches_neither_the_training_side_nor_the_stop_slice(dealt) -> None:
    """The stop slice is touched by the run, so the pin covers it too."""
    population, document = dealt
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    assert pinned, "both stores pin an evaluation side; a test that found none proves nothing"
    for fold in range(document["folds"]):
        _rows, pictures, _split = render_grade.sides_for(fold, document, population)
        trespassing = [
            picture
            for picture in pictures
            if picture.place in pinned and picture.side in {"train", render_train.SELECTION}
        ]
        assert not trespassing, (
            f"{len(trespassing)} pinned pictures would be trained or stopped on in fold "
            f"{fold}, which spends a blind sheet the folds may not touch"
        )


def carried_columns_for(rows: list[dict], flatness: float = 0.1) -> dict:
    """The arm-independent half of the rank key's row, for a synthetic population."""
    return {
        "rows": {
            f"{row['kind']}:{row['name']}": {
                "kind": row["kind"],
                "name": row["name"],
                "tier": int(row["score"]),
                "mode": row["mode"],
                "loc_p_ge4": 0.5,
                "stratum_score": 1.0,
                "flat16_1.0": flatness,
            }
            for row in rows
        }
    }


def test_the_key_is_refit_out_of_fold_on_the_arm_s_own_predictions() -> None:
    """The primary, and the one property that makes it a primary.

    An arm whose scale has moved must not be read through constants fitted
    against another arm's scale — CORN's axis is set by the training prior, so
    every retrain moves it and the move would report as a quality change. So the
    key's own weights come from the arm being read, out of the fold being read.
    """
    rows = [
        an_out_of_fold_row(
            f"a{index}", 4 if index % 3 == 0 else 3, index / 60, lineage=index, fold=index % 5
        )
        for index in range(60)
    ]
    carried = carried_columns_for(rows)
    read = render_grade.key_readings(rows, carried)
    assert len(read) == len(rows)
    assert all("key_value" in row for row in read)

    # The same reading with every probability shifted by a constant is the same
    # ORDER, so a refit key reads the same AUC off it. That is the calibration
    # sensitivity dropping out, stated as a test rather than as a claim.
    moved = [{**row, "p_ge3": row["p_ge3"] / 2, "p_ge4": row["p_ge4"] / 2} for row in rows]
    shifted = render_grade.key_readings(moved, carried)
    document = render_grade.key_delta(shifted, read)
    assert document["n"] == len(rows)
    assert document["candidate"] == pytest.approx(document["reference"], abs=1e-9)


def test_a_row_the_key_cannot_be_read_for_is_left_out_rather_than_imputed() -> None:
    """A rank the key never took is not a rank of zero. It is an absence."""
    rows = [
        an_out_of_fold_row(
            f"b{index}", 4 if index % 2 else 3, index / 20, lineage=index, fold=index % 5
        )
        for index in range(20)
    ]
    carried = carried_columns_for(rows[:12])
    read = render_grade.key_readings(rows, carried)
    assert len(read) == 12
    assert {row["name"] for row in read} == {row["name"] for row in rows[:12]}


def test_the_primary_pools_both_kinds_and_takes_only_the_three_and_four_rows() -> None:
    """Pooled because the key's weights are shared; 3-or-4 because that is the seat."""
    rows = [
        an_out_of_fold_row(f"c{index}", (index % 4) + 1, index / 40, lineage=index, fold=index % 5)
        for index in range(40)
    ]
    for index, row in enumerate(rows):
        row["kind"] = "smooth_render" if index % 2 else "strange_render"
    carried = carried_columns_for(rows)
    read = render_grade.key_readings(rows, carried)
    document = render_grade.key_delta(read, read)
    assert document["n"] == sum(1 for row in rows if int(row["score"]) in {3, 4})
    assert set(document["per_kind"]) == set(render_train.KINDS)
    assert document["delta"] == pytest.approx(0.0)
