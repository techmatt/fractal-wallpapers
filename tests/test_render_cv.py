"""The grouped cross-validation harness: what it drops, what it deals, what it reads.

Four things a reader has to be able to check. That the swept rows — the ones the
page filled with the head's own suggestion — are out, because fitting on them is
fitting a model on its own output. That a lineage cannot straddle two folds and a
pinned location cannot reach a training side, which are the two ways this
measurement would silently become worthless. That the motivating slice is cut on
the *baseline's* score rather than on each arm's own. And that an arm declares its
own backbone rather than inheriting the module default, which is the trap
`render_train.MISLAUNCHED` is the record of.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import render_cv, render_train


@pytest.fixture(scope="module")
def dealt(shipped_render_cache):
    """The population and the deal, derived once for every guard in this file.

    Building the population sweeps both stores and digests a recipe per row, and
    three guards over five folds would otherwise pay for it seven times. Nothing
    here writes to it: `sides_for` reassigns every picture's side on every call,
    so one population answers for all five folds.
    """
    short = {kind: len(shipped_render_cache.missing(kind)) for kind in render_train.KINDS}
    if any(short.values()):
        pytest.skip(f"the render cache is short {short} — `renders plan` then `renders build`")
    return render_cv.pool(), render_cv.assignment()


def a_row(batch: str, unit: str | None = None, **changes) -> dict:
    row = {"batch": batch, "score": 3, "mode": "tia"}
    if unit is not None:
        row["unit"] = unit
    row.update(changes)
    return row


def an_out_of_fold_row(name: str, score: int, p_ge4: float, **changes) -> dict:
    row = {
        "kind": "strange_render",
        "name": name,
        "score": score,
        "lineage": int(name[-1]) if name[-1].isdigit() else 0,
        "mode": "tia",
        "p_ge2": 0.9,
        "p_ge3": 0.7,
        "p_ge4": p_ge4,
    }
    row.update(changes)
    return row


def test_the_sweep_bound_drops_the_suffix_and_nothing_else() -> None:
    """The last override is a floor on the hand-cast prefix, and only on it."""
    assert not render_cv.swept(a_row(render_cv.SWEPT_BATCH, "u0001"))
    assert not render_cv.swept(a_row(render_cv.SWEPT_BATCH, f"u{render_cv.LAST_OVERRIDE:04d}"))
    assert render_cv.swept(a_row(render_cv.SWEPT_BATCH, f"u{render_cv.LAST_OVERRIDE + 1:04d}"))
    assert render_cv.swept(a_row(render_cv.SWEPT_BATCH, "u0504"))


def test_the_bound_is_about_one_page_and_not_about_a_position() -> None:
    """Another batch's row at the same position was not swept and stays."""
    assert not render_cv.swept(a_row("mode_sweep", "u0400"))
    assert not render_cv.swept(a_row(render_cv.SWEPT_BATCH))


def test_an_arm_declares_its_own_backbone_rather_than_inheriting_one() -> None:
    """The trap three runs of the shipped band already fell into, once.

    `render_train.RECIPE` still carries the FIRST joint candidate's medium
    backbone, so an arm that did not re-ask the value would fit at a backbone no
    declaration names — internally consistent, consistently wrong, and invisible
    in every record the fold would write.
    """
    shipped = render_train.CANDIDATES["enlarged_corpus"]["backbone"]
    assert shipped != render_train.RECIPE["backbone"], (
        "the module default and the shipped band's declaration are different values, which "
        "is the whole reason an arm has to declare"
    )
    for arm, entry in render_cv.ARMS.items():
        assert entry.get("backbone"), f"arm {arm} declares no backbone"
        assert render_cv.declared_backbone(arm) == entry["backbone"]
    assert render_cv.ARMS["baseline"]["backbone"] == shipped, (
        "arm A is the shipped recipe unchanged, so it is the shipped band's own backbone"
    )


def test_the_motivating_slice_is_cut_on_the_baselines_score(monkeypatch) -> None:
    """A slice cut on each arm's own score would be a different population per arm."""
    low, high = render_cv.MOTIVATING_BAND
    inside, outside = (low + high) / 2, high + 0.02
    baseline = [
        an_out_of_fold_row("a1", 4, inside),
        an_out_of_fold_row("b2", 3, inside),
        an_out_of_fold_row("c3", 4, outside),
        an_out_of_fold_row("d4", 3, outside),
    ]
    # The candidate puts the band's two rows outside it and the other two in.
    candidate = [
        an_out_of_fold_row("a1", 4, outside),
        an_out_of_fold_row("b2", 3, outside),
        an_out_of_fold_row("c3", 4, inside),
        an_out_of_fold_row("d4", 3, inside),
    ]
    monkeypatch.setattr(
        render_cv, "pooled", lambda arm: candidate if arm == "candidate" else baseline
    )
    monkeypatch.setitem(render_cv.ARMS, "candidate", {"backbone": "x", "seed": 0, "what": "a test"})
    document = render_cv.compare("candidate", "baseline")
    assert document["motivating"]["n"] == 2, (
        "the slice is the two rows the BASELINE put in the band, whatever the candidate says"
    )


def test_two_arms_that_do_not_cover_the_same_pictures_are_refused() -> None:
    """A quiet intersection would hide a difference in what was fitted."""
    with pytest.raises(render_cv.CrossValidationError):
        render_cv.aligned(
            [an_out_of_fold_row("a1", 4, 0.7)],
            [an_out_of_fold_row("a1", 4, 0.7), an_out_of_fold_row("b2", 3, 0.7)],
        )


def test_a_guard_arm_is_read_as_not_worse_rather_than_as_better() -> None:
    """Nothing in the four guards is asked to improve; only to not lose."""
    assert render_cv._verdict({"lo": -0.02, "hi": 0.03}, better=False) == "not worse"
    assert render_cv._verdict({"lo": -0.09, "hi": -0.01}, better=False) == "worse"
    assert render_cv._verdict({"lo": 0.01, "hi": 0.08}, better=True) == "better"
    assert render_cv._verdict({"lo": -0.01, "hi": 0.08}, better=True) == "not better"
    assert render_cv._verdict({"lo": None, "hi": None}, better=True) == "undefined"


@pytest.mark.slow
def test_a_lineage_never_straddles_two_folds(dealt) -> None:
    """The unit the fold is drawn over is the unit it is drawn over, whole."""
    _population, document = dealt
    where: dict[int, int] = {}
    for group, fold in zip(document["group_of_row"], document["fold_of_row"], strict=True):
        assert where.setdefault(group, fold) == fold, (
            f"lineage {group} landed in two folds, which puts the same picture on both sides"
        )
    assert len(where) == document["grouping"]["groups"]


@pytest.mark.slow
def test_every_owned_row_is_held_out_exactly_once(dealt) -> None:
    _population, document = dealt
    counted = [0] * document["folds"]
    for fold in document["fold_of_row"]:
        counted[fold] += 1
    assert sum(counted) == document["population"]["rows"]
    assert min(counted) > 0
    # Dealt to the smallest fold each time, so the folds are close in size even
    # though the lineages they are made of are not.
    assert max(counted) - min(counted) < 0.02 * sum(counted)


@pytest.mark.slow
def test_a_pinned_location_never_reaches_a_training_side(dealt) -> None:
    """The pin is obeyed, so the trainer's own guard is left armed and passes."""
    population, document = dealt
    pinned = {repr(place) for place in render_train.pinned_everywhere()}
    assert pinned, "both stores pin an evaluation side; a test that found none proves nothing"
    for fold in range(document["folds"]):
        _rows, pictures, split = render_cv.sides_for(fold, document, population)
        trespassing = [
            picture
            for picture in pictures
            if picture.place in pinned and picture.side in {"train", render_train.SELECTION}
        ]
        assert not trespassing, (
            f"{len(trespassing)} pinned pictures would train in fold {fold}, which spends a "
            f"blind sheet the folds are not allowed to touch"
        )
        assert split["test_pictures"] > 0
