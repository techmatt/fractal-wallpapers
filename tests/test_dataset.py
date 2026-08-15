"""Which locations get drawn, how often, and which of them the head may see.

The sampler's weights are three factors multiplied in a stated order, and the
order is the claim: a class balance applied last cannot change the biased ratio
inside a class. That is asserted here rather than argued in a comment.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import dataset

pytest.importorskip("numpy")
pytest.importorskip("torch")


def location(identifier, score=1, side=pins.TRAIN, group=0, biased=False) -> dataset.Location:
    return dataset.Location(
        location_id=identifier,
        score=score,
        side=side,
        partition="mandelbrot",
        group=group,
        batch="a_batch",
        biased=biased,
        tiles=[{"tile": 0, "level": "antialiased", "scale": 1.0, "shift_frac": 0.0, "path": "x"}],
    )


def test_a_location_with_no_tiles_is_refused_rather_than_dropped() -> None:
    """A build that silently covers a prefix trains a head on a prefix, and the
    head reports the numbers of a whole corpus."""
    rows = [
        {
            "location_id": 1,
            "score": 3,
            "side": "train",
            "partition": "mandelbrot",
            "group": 0,
            "batch": "a",
            "biased": False,
        }
    ]
    with pytest.raises(ValueError, match="have no tiles"):
        dataset.join(rows, {})


def test_a_neighbourhood_is_worth_one_location_however_many_frames_it_holds() -> None:
    crowd = [location(index, group=0) for index in range(20)]
    alone = [location(100 + index, group=index + 1) for index in range(5)]
    _, table = dataset.weights(crowd + alone)
    mass = table["sampled_mass"]["score1|unbiased"]
    assert mass == pytest.approx(1.0)
    weights, _ = dataset.weights(crowd + alone)
    # Every member of the twenty-strong group is worth a twentieth of a singleton.
    assert float(weights[0]) == pytest.approx(float(weights[-1]) / 20)


def test_the_class_balance_cannot_launder_the_source_down_weight_back_out() -> None:
    """`w_class` is a pure per-class scalar applied last, so it scales a class
    uniformly and leaves the biased/unbiased ratio inside it untouched."""
    locations = [
        *(location(index, score=1, group=index, biased=False) for index in range(10)),
        *(location(50 + index, score=1, group=50 + index, biased=True) for index in range(10)),
        *(location(80 + index, score=4, group=80 + index, biased=False) for index in range(2)),
    ]
    weights, table = dataset.weights(locations, beta=dataset.BETA_BIASED)
    unbiased = float(weights[0])
    biased = float(weights[10])
    assert biased / unbiased == pytest.approx(dataset.BETA_BIASED)
    # And the rare class is lifted, but only as a whole class.
    assert float(weights[20]) > unbiased
    assert set(table["class_count"]) == {1, 4}


def test_the_selection_slice_never_touches_the_evaluation_side() -> None:
    """An instrument is spent the moment it trains, and picking an epoch on it
    is a partial spend that leaves nothing red."""
    locations = [
        *(location(index, group=index // 3) for index in range(300)),
        *(location(1000 + index, side=pins.EVAL, group=1000 + index) for index in range(40)),
    ]
    record = dataset.assign_selection(locations, share=0.2, seed=0)
    by_side = dataset.sides(locations)
    assert len(by_side[pins.EVAL]) == 40
    assert by_side[dataset.SELECTION]
    assert record["realized_share"] == pytest.approx(0.2, abs=0.05)
    assert all(row.side == pins.EVAL for row in locations if row.location_id >= 1000)


def test_the_selection_slice_takes_whole_groups() -> None:
    """A slice that shares a neighbourhood with the training side is measuring
    what the head memorized, not what it learned."""
    locations = [location(index, group=index // 10) for index in range(300)]
    dataset.assign_selection(locations, share=0.3, seed=0)
    by_group: dict[int, set[str]] = {}
    for row in locations:
        by_group.setdefault(row.group, set()).add(row.side)
    assert all(len(sides) == 1 for sides in by_group.values())


def test_a_histogram_reports_an_absent_class_as_a_zero() -> None:
    """ "none" and "not counted" are different statements."""
    assert dataset.histogram([location(0, score=1)]) == {"1": 1, "2": 0, "3": 0, "4": 0}


def test_the_cutpoint_populations_nest() -> None:
    locations = [location(index, score=(index % 4) + 1) for index in range(40)]
    counts = dataset.positives_at_cutpoints(locations, 4)
    assert counts["ge2"] >= counts["ge3"] >= counts["ge4"] > 0


def test_a_training_example_draws_a_different_tile_each_epoch(tmp_path) -> None:
    """Otherwise the fan-out is thirty-two pictures and the head only ever sees
    one of them, forty times."""
    from PIL import Image

    one = location(0)
    one.tiles = []
    for index in range(32):
        path = tmp_path / f"tile{index}.png"
        Image.new("RGB", (8, 8), (index, 0, 0)).save(path)
        one.tiles.append({"tile": index, "path": str(path)})

    examples = dataset.training_set([one], lambda image, draw: image.getpixel((0, 0))[0], seed=0)
    drawn = []
    for epoch in range(8):
        examples.set_epoch(epoch)
        drawn.append(examples[0][0])
    assert len(set(drawn)) > 1, "the drawn tile never changed across eight epochs"

    # Reproducible all the same: the same seed and epoch give the same tile.
    again = dataset.training_set([one], lambda image, draw: image.getpixel((0, 0))[0], seed=0)
    again.set_epoch(3)
    assert again[0][0] == drawn[3]
