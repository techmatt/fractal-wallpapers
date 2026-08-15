"""The split: whole groups, eligible material only, and pins that never release.

Every test here is about one of the three ways an evaluation side stops being an
instrument — a biased row inside it, a group straddling the boundary, or a
location quietly moving to the training side when the corpus grew.
"""

from __future__ import annotations

from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import split as split_module
from fractal_wallpapers.labeling import store
from fractal_wallpapers.supply.location import key_of_row


def row(index: int, batch: str, width="1.0") -> dict:
    """One location per index, far enough apart to be its own group."""
    return {
        "schema": 1,
        "batch": batch,
        "score": 3,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": f"{index * 10}.0", "center_im": "0.0", "width": width},
        "recorded_at": "2026-01-01",
        "origin": "human",
    }


def known(**batches) -> dict:
    return {
        name: registry_module.Registration(
            batch=name, method="a draw", score_unconditioned=unconditioned
        )
        for name, unconditioned in batches.items()
    }


def test_the_draw_stops_at_the_target_share() -> None:
    rows = [row(i, "clean") for i in range(100)]
    drawn = split_module.derive(rows, known=known(clean=True), share=0.2)
    assert len(drawn.eval_rows) == 20
    assert drawn.realized() == 0.2


def test_only_eligible_material_reaches_the_evaluation_side() -> None:
    rows = [row(i, "clean" if i < 50 else "biased") for i in range(100)]
    drawn = split_module.derive(rows, known=known(clean=True, biased=False), share=0.2)
    assert {r["batch"] for r in drawn.eval_rows.values()} == {"clean"}


def test_a_short_eligible_pool_realizes_less_than_the_target_and_says_so() -> None:
    """A nominal share is not a realized one, and quoting the nominal figure is
    how a confidence interval ends up describing a population that was never
    drawn."""
    rows = [row(i, "clean" if i < 5 else "biased") for i in range(100)]
    drawn = split_module.derive(rows, known=known(clean=True, biased=False), share=0.2)
    recipe = drawn.recipe()
    assert recipe["target_eval_share"] == 0.2
    assert recipe["realized_eval_share"] == 0.05
    assert recipe["locations"]["eval_eligible"] == 5


def test_a_group_with_one_biased_member_goes_training_side_entire() -> None:
    """Overlapping frames are one group. One biased member makes the group
    ineligible, and the eligible locations it takes with it are counted rather
    than quietly lost."""
    rows = [row(0, "clean"), row(0, "biased")]
    rows[1]["viewport"]["center_re"] = "0.2"
    drawn = split_module.derive(rows, known=known(clean=True, biased=False), share=1.0)
    assert drawn.eval_rows == {}
    assert drawn.recipe()["eligible_locations_demoted_by_a_group_mate"] == 1


def test_no_group_straddles_when_nothing_is_pinned() -> None:
    rows = [row(i // 3, "clean") for i in range(30)]
    for index, item in enumerate(rows):
        item["viewport"]["center_re"] = f"{(index // 3) * 10}.{index % 3}"
    drawn = split_module.derive(rows, known=known(clean=True), share=0.3)
    assert drawn.straddling == []


def test_the_draw_is_seeded_and_reproducible() -> None:
    rows = [row(i, "clean") for i in range(100)]
    first = split_module.derive(rows, known=known(clean=True), seed=7)
    second = split_module.derive(rows, known=known(clean=True), seed=7)
    third = split_module.derive(rows, known=known(clean=True), seed=8)
    assert set(first.eval_rows) == set(second.eval_rows)
    assert set(first.eval_rows) != set(third.eval_rows)


def test_re_deriving_over_a_grown_corpus_carries_every_pin_forward() -> None:
    """The property the whole record exists for: last month's holdout is still
    this month's holdout, whatever arrived in between."""
    rows = [row(i, "clean") for i in range(50)]
    first = split_module.derive(rows, known=known(clean=True), share=0.2)
    pinned = set(first.eval_rows)

    grown = rows + [row(i, "clean") for i in range(50, 200)]
    second = split_module.derive(grown, known=known(clean=True), share=0.2, pinned=pinned)
    assert pinned <= set(second.eval_rows)
    assert second.recipe()["carried_forward"] == len(pinned)


def test_a_pin_survives_its_group_gaining_a_biased_member() -> None:
    """The pin is at unit granularity and outranks the group rule: the instrument
    keeps its side and the group straddles on purpose, which is reported."""
    original = row(0, "clean")
    drawn = split_module.derive([original], known=known(clean=True), share=1.0)
    pinned = set(drawn.eval_rows)

    neighbour = row(0, "biased")
    neighbour["viewport"]["center_re"] = "0.2"
    second = split_module.derive(
        [original, neighbour], known=known(clean=True, biased=False), share=1.0, pinned=pinned
    )
    assert pinned <= set(second.eval_rows)
    assert key_of_row(neighbour) not in second.eval_rows
    assert second.straddling


def test_the_shipped_record_round_trips(store_dir) -> None:
    rows = [row(i, "clean") for i in range(20)]
    drawn = split_module.derive(rows, known=known(clean=True), share=0.5)
    members, recipe = split_module.write(drawn)
    assert members.exists() and recipe.exists()

    read_back = split_module.read()
    assert {key_of_row(r) for r in read_back} == set(drawn.eval_rows)
    assert split_module.recipe()["realized_eval_share"] == 0.5
    assert all(r["group"] is not None for r in read_back)


def test_an_empty_corpus_splits_into_nothing(store_dir) -> None:
    drawn = split_module.derive([], known=store.registry())
    assert drawn.eval_rows == {}
    assert drawn.realized() == 0.0
