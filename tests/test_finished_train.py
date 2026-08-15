"""The finished-render trainers: the split, the sampler, and the recipes.

Three things a reader has to be able to check. That the blind sheet is the whole
evaluation side and never the training one — the failure there is silent and
permanent. That a place carrying nine colorings does not outvote nine places. And
that "the same recipe as the source project's" is a claim with a list behind it
rather than a sentence.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import finished_train


def a_picture(place: str, score: int, side: str = "train", **changes):
    fields = {
        "path": None,
        "score": score,
        "side": side,
        "batch": "mode_sweep",
        "place": place,
        "partition": "mandelbrot",
        "mode": "smooth",
        "name": f"{place}:{score}",
    }
    fields.update(changes)
    return finished_train.Picture(**fields)


def test_a_place_is_worth_one_place_however_many_ways_it_was_coloured() -> None:
    """Nine colorings of one place against one coloring each of nine places."""
    crowded = [a_picture("busy", 2, name=f"busy{index}") for index in range(9)]
    spread = [a_picture(f"place{index}", 2) for index in range(9)]
    raw, mass = finished_train.weights(crowded + spread)
    assert mass["largest_place"] == 9
    crowded_mass = sum(raw[: len(crowded)])
    spread_mass = sum(raw[len(crowded) :])
    assert abs(crowded_mass - spread_mass / 9) < 1e-12, (
        "one place's nine pictures should carry one place's worth of gradient"
    )


def test_the_class_balance_is_a_square_root_and_softens_rather_than_inverts() -> None:
    pictures = [a_picture(f"a{i}", 1) for i in range(100)] + [
        a_picture(f"b{i}", 4) for i in range(4)
    ]
    _, mass = finished_train.weights(pictures)
    raw_ratio = mass["raw_share"]["1"] / mass["raw_share"]["4"]
    sampled_ratio = mass["sampled_mass"]["1"] / mass["sampled_mass"]["4"]
    assert sampled_ratio < raw_ratio, "the imbalance was not softened at all"
    assert sampled_ratio > 1.0, "full inversion would make four pictures as loud as a hundred"


def test_the_two_recipes_carry_their_source_s_own_shape() -> None:
    smooth = finished_train.recipe_for("smooth_render")
    strange = finished_train.recipe_for("strange_render")
    assert smooth["classes"] == 4 and strange["classes"] == 3
    assert smooth["backbone"] != strange["backbone"]
    for recipe in (smooth, strange):
        assert recipe["epochs"] == 40
        assert recipe["batch_size"] == 32
        assert recipe["border_crop"] == 0.05
        assert recipe["amp"] == "off"
        assert "No colour" in recipe["augmentation"]


def test_every_changed_key_says_what_it_was_and_why() -> None:
    """ "The same recipe" is a claim a reader has to be able to check."""
    changed = finished_train.INHERITANCE["changed"]
    assert changed, "a recipe that changed nothing would say so with an empty list, not none"
    for entry in changed:
        assert set(entry) == {"key", "was", "now", "why"}
        assert entry["was"] != entry["now"]
        assert len(entry["why"]) > 60, f"{entry['key']}: the reason is the point of the entry"
    keys = {entry["key"] for entry in changed}
    assert keys.isdisjoint(finished_train.INHERITANCE["identical"])


def test_colour_augmentation_is_off_for_these_judges() -> None:
    """The coloring is the label, so a brightness jitter edits the verdict."""
    from fractal_wallpapers.models import head

    training = head.Transform(
        (0.5,) * 3, (0.5,) * 3, train=True, jpeg=None, brightness=0.0, contrast=0.0
    )
    assert training.jpeg is None
    assert training.brightness == 0.0 and training.contrast == 0.0
    # And the location head's own defaults are untouched by that being possible.
    default = head.Transform((0.5,) * 3, (0.5,) * 3, train=True)
    assert default.jpeg == head.JPEG_JITTER
    assert default.brightness == head.BRIGHTNESS


def test_the_transform_still_runs_with_the_colour_stages_off() -> None:
    pytest.importorskip("torch")
    from PIL import Image

    from fractal_wallpapers.models import head

    picture = Image.new("RGB", (128, 72), (10, 120, 200))
    plain = head.Transform(
        (0.5,) * 3, (0.5,) * 3, train=True, jpeg=None, brightness=0.0, contrast=0.0
    )
    tensor = plain(picture)
    assert tuple(tensor.shape) == (3, head.TARGET_HEIGHT, head.TARGET_WIDTH)


@pytest.mark.parametrize("head_name", sorted(finished.HEADS))
def test_the_split_is_the_pin_and_the_selection_slice_comes_out_of_training(head_name: str) -> None:
    from fractal_wallpapers.models import renders

    if not finished.registry_path(head_name).is_file():
        pytest.skip(f"the {head_name} store has not been imported on this machine")
    if not renders.crop_dir(head_name).is_dir() or not renders.plan_path(head_name).is_file():
        pytest.skip("the render cache has not been built on this machine")
    if renders.missing(head_name):
        pytest.skip("the render cache is incomplete on this machine")

    pictures, record = finished_train.population(head_name)
    by_side = finished_train.sides(pictures)
    pinned = {repr(key) for key in finished.pinned(head_name)}

    assert {picture.place for picture in by_side["eval"]} <= pinned
    for side in ("train", finished_train.SELECTION):
        assert not [p for p in by_side[side] if p.place in pinned], f"{side} touches the pin"
    assert by_side[finished_train.SELECTION], "nothing to choose an epoch on"
    # A place's pictures may not straddle the training side and the slice.
    training_places = {p.place for p in by_side["train"]}
    slice_places = {p.place for p in by_side[finished_train.SELECTION]}
    assert training_places.isdisjoint(slice_places)
    assert record["share"] == finished_train.SELECTION_SHARE


@pytest.mark.parametrize("head_name", sorted(finished.HEADS))
def test_a_trained_judge_records_what_it_trained_under(head_name: str) -> None:
    path = finished_train.config_path(head_name)
    if not path.is_file():
        pytest.skip(f"the {head_name} judge has not been trained on this machine")
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["head"] == head_name
    assert config["classes"] == finished.HEADS[head_name]
    assert config["inherited"]["changed"]
    assert config["precision"] == "fp32"
