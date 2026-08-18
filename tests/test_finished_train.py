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
    """Everything but the class count, which strange's retrain moved to four."""
    smooth = finished_train.recipe_for("smooth_render")
    strange = finished_train.recipe_for("strange_render")
    assert smooth["classes"] == len(finished.SCALE)
    assert strange["classes"] == len(finished.SCALE)
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
def test_the_split_is_the_pin_and_the_selection_slice_comes_out_of_training(
    head_name: str, shipped_render_cache
) -> None:
    from fractal_wallpapers.models import renders

    if not finished.registry_path(head_name).is_file():
        pytest.skip(f"the {head_name} store has not been imported on this machine")
    if not renders.crop_dir(head_name).is_dir() or not renders.plan_path(head_name).is_file():
        pytest.skip("the render cache has not been built on this machine")
    if shipped_render_cache.missing(head_name):
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
    """The pin protects the MODEL's agreement with itself, not the corpus's scale.

    `classes` used to be checked against the store's ceiling, which made the two
    numbers one number: a corpus that grew a tier could not be collected without
    claiming the shipped head had learned it. What has to agree is the config
    written beside a checkpoint and that checkpoint's own output width — a head
    whose weights emit two cutpoints while its config claims three is one every
    reader of its scores misreads.

    It is NOT checked against today's recipe. A run record says what that run
    trained under, and a retrain that widens the recipe leaves the superseded
    run's directory readable exactly as it was; re-reading it against the current
    recipe would mean a retrain could only ever happen by destroying the baseline
    it is measured against.
    """
    configs = sorted(finished_train.head_dir(head_name).glob("**/config.json"))
    if not configs:
        pytest.skip(f"the {head_name} judge has not been trained on this machine")
    for path in configs:
        config = json.loads(path.read_text(encoding="utf-8"))
        assert config["head"] == head_name
        assert config["classes"] in finished.SCALE
        assert config["inherited"]["changed"]
        assert config["precision"] == "fp32"


@pytest.mark.parametrize("head_name", sorted(finished.HEADS))
def test_a_checkpoint_emits_as_many_cutpoints_as_its_config_claims(head_name: str) -> None:
    """The other half of the same pin, read off the weights rather than the JSON."""
    torch = pytest.importorskip("torch")
    checkpoints = sorted(finished_train.head_dir(head_name).glob("**/best.pt"))
    if not checkpoints:
        pytest.skip(f"the {head_name} judge has not been trained on this machine")
    for path in checkpoints:
        saved = torch.load(path, map_location="cpu", weights_only=False)
        classes = int(saved["config"]["classes"])
        final = [value for value in saved["state_dict"].values() if value.ndim >= 1][-1]
        assert final.shape[0] == classes - 1, (
            f"{path}: the config claims {classes} classes and the head emits "
            f"{final.shape[0]} cutpoints"
        )


def test_a_corpus_wider_than_the_recipe_refuses_to_train_rather_than_mis_fit(monkeypatch) -> None:
    """The decoupling's one real hazard, closed. A 4 handed to a three-class CORN
    head is a rank with no task to carry it, and the failure is a silently
    mis-fitted top cutpoint rather than a crash — so the pass says so instead,
    and names the one edit that fixes it.

    Both recipes now train the whole scale, so the narrow one this guards against
    has to be built here. That is the right way round: the guarantee is about any
    recipe narrower than its own population, not about a head that happened to be
    narrow on the day it was written."""
    assert finished_train.refuse_inexpressible("strange_render", [1, 2, 3, 4]) == 4
    assert finished_train.refuse_inexpressible("smooth_render", [1, 2, 3, 4]) == 4
    monkeypatch.setitem(finished_train.RECIPES["strange_render"], "classes", 3)
    assert finished_train.refuse_inexpressible("strange_render", [1, 2, 3]) == 3
    with pytest.raises(finished_train.TrainingError, match="IS the retrain"):
        finished_train.refuse_inexpressible("strange_render", [1, 3, 4])


def test_the_selection_objective_can_see_a_probability() -> None:
    """The defect this replaced: average precision is invariant to rescaling, so
    it cannot tell a well-scaled head from one whose probabilities collapsed. The
    loss is a proper scoring rule and can."""
    import numpy

    from fractal_wallpapers.models import metrics

    labels = numpy.array([1, 1, 2, 3, 4] * 20)
    scaled = numpy.tile(
        numpy.array(
            [
                [0.1, 0.05, 0.02],
                [0.1, 0.05, 0.02],
                [0.8, 0.3, 0.1],
                [0.9, 0.8, 0.3],
                [0.95, 0.9, 0.8],
            ]
        ),
        (20, 1),
    )
    # The same ORDER, squashed toward zero — a collapsed deploy-mode head.
    collapsed = scaled * 1e-3

    assert metrics.average_precision((labels >= 3).astype(int), scaled[:, 1]) == pytest.approx(
        metrics.average_precision((labels >= 3).astype(int), collapsed[:, 1])
    ), "average precision is supposed to be blind to this; if it is not, the premise moved"

    assert finished_train.validation_loss(
        labels, collapsed, 4
    ) > 5 * finished_train.validation_loss(labels, scaled, 4), (
        "the objective has to charge for a collapsed scale"
    )


def test_the_forced_change_is_recorded_as_forced() -> None:
    changed = {entry["key"]: entry for entry in finished_train.INHERITANCE["changed"]}
    assert "selection_statistic" in changed
    assert "FORCED" in changed["selection_statistic"]["why"]


def test_two_trainers_cannot_share_a_run_directory(tmp_path) -> None:
    """They do not collide loudly. They interleave their logs, take turns
    overwriting one checkpoint, and produce a run whose numbers belong to
    neither — which is what happened, and what took tens of minutes to see."""
    lock = finished_train._claim(tmp_path)
    assert lock.is_file()
    with pytest.raises(finished_train.TrainingError, match="already has"):
        finished_train._claim(tmp_path)
    lock.unlink()
    finished_train._claim(tmp_path).unlink()
