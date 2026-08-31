"""The 80/20 the ship head is stopped on, and the rule that reads it.

This is the run whose artifact ships, and its holdout has exactly one job — to
choose an epoch. So its guards are about the two things that would make that
choice worthless. **The holdout has to be a holdout**: whole lineages either
side of the boundary, because two frames a hair apart are the same picture
twice, and a head that fits a near-duplicate of a row it stops on has chosen its
epoch on a row it already knows.

And **the blind sheets have to stay unspent**. Nothing in this module reads them:
the trainer refuses to train on a pinned place and refuses to early-stop on one,
so a pinned lineage is held out and the pinned rows themselves sit on the side
the loop never touches, out of the stopping statistic. That is a consequence of
the trainer's guard rather than a rule this module adds, and the guards below say
so by asserting on both halves of it.

The rest is the stopping rule's own argument. It is rank-only, which is why it is
not `render_cv.top_cutpoint_selection` — the arm that chose epoch 1 by refusing
to commit — and it reads a whole ranking rather than one k, which is what the
rule it replaced did and what let a single row choose an epoch.
"""

from __future__ import annotations

import numpy
import pytest

from fractal_wallpapers.models import render_cv, render_deploy, render_train

HOLDOUT = {render_deploy.STOPPING, render_deploy.PINNED}
TOUCHED = {"train", render_deploy.STOPPING}


@pytest.fixture(scope="module")
def split(shipped_render_cache):
    """One seed's split, derived once for every guard in this file."""
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short} — `renders plan` then `renders build`")
    rows, pictures, record = render_deploy.sides_for(render_deploy.SEEDS[0], render_cv.pool())
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
    for rule, _says in render_deploy.RULES.values():
        assert rule(labels, confident, 4) == rule(labels, shrunk, 4)
    assert render_cv.top_cutpoint_loss(labels, confident, 4) != pytest.approx(
        render_cv.top_cutpoint_loss(labels, shrunk, 4)
    )


def test_the_rule_reads_a_whole_ranking_rather_than_one_k() -> None:
    """The reason average precision replaced precision at a single k.

    The rule it replaced moved in steps of one row: at k=100 a single row
    reordered between two epochs decides the run. Average precision reads every
    recall step, so moving one row inside the top slice moves it and moving one
    row from the middle to the bottom moves it too — a statistic a single
    cutpoint cannot pin.
    """
    labels = numpy.array([4, 1, 1, 3, 1, 1, 1, 1, 1, 1])
    top_heavy = numpy.array(
        [[0.9, p, 0.1] for p in (0.99, 0.5, 0.4, 0.95, 0.3, 0.2, 0.1, 0.1, 0.1, 0.1)]
    )
    # The same top decile, one hit moved from rank 4 to rank 9. Precision@10%
    # cannot see it; the rule that ships can.
    reshuffled = numpy.array(
        [[0.9, p, 0.1] for p in (0.99, 0.5, 0.4, 0.05, 0.3, 0.2, 0.1, 0.1, 0.1, 0.09)]
    )
    first = render_deploy.rank_scores(top_heavy)
    second = render_deploy.rank_scores(reshuffled)
    assert render_deploy.precision_at(labels, first, 0.10)["precision"] == pytest.approx(
        render_deploy.precision_at(labels, second, 0.10)["precision"]
    )
    assert render_deploy.average_precision_selection(
        labels, top_heavy, 4
    ) < render_deploy.average_precision_selection(labels, reshuffled, 4)


def test_the_rule_reads_the_boundary_it_scores() -> None:
    """Rank on `P(>=3)`, count a hit at tier 3. One question asked once."""
    assert f"p_ge{render_deploy.HIT_TIER}" == render_deploy.RANK_COLUMN
    assert render_deploy.RULE in render_deploy.RULES
    probabilities = numpy.array([[0.9, 0.4, 0.1], [0.8, 0.7, 0.2]])
    assert render_deploy.rank_scores(probabilities).tolist() == [0.4, 0.7]
    assert render_deploy.hits_of([2, 3, 4]).tolist() == [0, 1, 1]


def test_an_undefined_statistic_is_infinite_rather_than_a_win() -> None:
    """A slice with no hits has no ranking to read, and a rule that returned 0
    there would look like the best epoch the run ever had."""
    flat = numpy.array([[0.9, 0.4, 0.1]] * 4)
    for rule, _says in render_deploy.RULES.values():
        assert rule(numpy.array([1, 1, 2, 2]), flat, 4) == float("inf")


def test_the_rule_takes_a_patience_and_a_hard_cap() -> None:
    """A rule that can run away ships a budget rather than a choice."""
    assert render_deploy.EPOCHS > 0
    assert 0 < render_deploy.PATIENCE < render_deploy.EPOCHS


def test_every_reported_readout_is_logged_and_none_of_them_stops_anything() -> None:
    """The predecessor's rule survives as a reading, so two epoch tables are legible
    against each other — but it is not what chooses."""
    labels = numpy.array([4, 3, 2, 1] * 25)
    probabilities = numpy.column_stack(
        [numpy.full(100, 0.9), numpy.linspace(0.99, 0.01, 100), numpy.full(100, 0.1)]
    )
    logged = render_deploy.readouts(labels, probabilities, 4)
    for fraction in render_deploy.REPORTED_SLICES:
        assert f"precision_at_{int(round(fraction * 100)):02d}" in logged
    assert render_deploy.RULE == "average_precision"
    # And they may not collide with a column the trainer writes itself, which is
    # what `render_train.run` refuses on: two runs whose history columns mean
    # different things cannot be read against each other.
    written = {"epoch", "loss", "seconds", "selection_loss", "second_selection_loss"}
    written |= {f"selection_auc_ge{tier}" for tier in (2, 3, 4)}
    written |= {f"selection_mean_p_ge{tier}" for tier in (2, 3, 4)}
    written |= {"selection_ap_ge3"} | {f"selection_loss_{kind}" for kind in render_train.KINDS}
    assert not (set(logged) & written)


@pytest.mark.slow
def test_no_lineage_straddles_the_training_boundary(split) -> None:
    """Whole neighbourhoods either side, or the head stops on a near-duplicate of
    a row it trained on."""
    from fractal_wallpapers.labeling import groups

    rows, pictures, _record = split
    grouping = groups.assign(rows)
    sides: dict[int, set] = {}
    for picture, group in zip(pictures, grouping.of_row, strict=True):
        sides.setdefault(int(group), set()).add(picture.side in HOLDOUT)
    straddling = [group for group, seen in sides.items() if len(seen) > 1]
    assert not straddling, (
        f"{len(straddling)} lineages sit on both sides of the training boundary, so the head "
        f"chooses its epoch on a near-duplicate of a row it fitted"
    )


@pytest.mark.slow
def test_a_pinned_place_is_neither_trained_on_nor_stopped_on(split) -> None:
    """A blind sheet is spent once, and this run does not spend it."""
    _rows, pictures, record = split
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    assert pinned, "both stores pin an evaluation side; a test that found none proves nothing"
    trespassing = [
        picture for picture in pictures if picture.place in pinned and picture.side in TOUCHED
    ]
    assert not trespassing, (
        f"{len(trespassing)} pinned pictures would be trained or stopped on, which spends an "
        f"instrument this run is not allowed to touch"
    )
    # And the other half of it: every pinned row is present, on the untouched
    # side. A split that lost them would pass the assertion above by deletion.
    held = [picture for picture in pictures if picture.side == render_deploy.PINNED]
    assert {picture.place for picture in held} <= pinned
    assert len(held) == sum(1 for picture in pictures if picture.place in pinned)
    assert record["pinned_rows"]["rows"] == len(held)


@pytest.mark.slow
def test_the_holdout_is_the_declared_share_and_the_stopping_slice_is_the_rest_of_it(
    split,
) -> None:
    """20% over lineages, and the statistic reads the part of it that is not pinned."""
    _rows, pictures, record = split
    holdout = [picture for picture in pictures if picture.side in HOLDOUT]
    assert record["holdout_share"] == pytest.approx(len(holdout) / len(pictures), abs=5e-5)
    # Lineages are taken whole, so the realized share lands near the target
    # rather than on it. A point either side of it is a split that stopped
    # filling somewhere else entirely.
    assert abs(record["holdout_share"] - render_deploy.HOLDOUT_SHARE) < 0.02
    stopping = {
        (picture.kind, picture.name)
        for picture in pictures
        if picture.side == render_deploy.STOPPING
    }
    pinned_held = {
        (picture.kind, picture.name) for picture in pictures if picture.side == render_deploy.PINNED
    }
    assert stopping and pinned_held
    assert not (stopping & pinned_held)
    assert len(stopping) + len(pinned_held) == len(holdout)


@pytest.mark.slow
def test_the_stopping_slice_keeps_the_ones_and_twos(split) -> None:
    """A ranking statistic only bites where a wrong row could have been ranked high."""
    _rows, _pictures, record = split
    tiers = record["stopping_slice"]["tiers"]
    assert int(tiers.get("1", 0)) + int(tiers.get("2", 0)) > 0, (
        "the stopping slice holds no 1s or 2s, so a ranking of it cannot punish anything"
    )
    assert int(tiers.get("3", 0)) + int(tiers.get("4", 0)) > 0, (
        "the stopping slice holds no hits, so the rule is undefined on it"
    )


@pytest.mark.slow
def test_the_three_seeds_draw_three_different_holdouts(shipped_render_cache) -> None:
    """The seed has to move the split, or three runs are one run three times.

    The pinned lineages are forced into every one of them and that part is meant
    to be identical; what has to differ is the draw on top.
    """
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short}")
    drawn = []
    for seed in render_deploy.SEEDS:
        _rows, pictures, record = render_deploy.sides_for(seed, render_cv.pool())
        drawn.append(
            frozenset(
                (picture.kind, picture.name)
                for picture in pictures
                if picture.side == render_deploy.STOPPING
            )
        )
        assert record["seed"] == seed
    for first in range(len(drawn)):
        for second in range(first + 1, len(drawn)):
            assert drawn[first] != drawn[second], (
                f"seeds {render_deploy.SEEDS[first]} and {render_deploy.SEEDS[second]} drew "
                f"the same stopping slice, so the third seed is buying nothing"
            )
