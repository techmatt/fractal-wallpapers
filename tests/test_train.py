"""The training loop, run for real on a corpus small enough to be a test.

Everything above this file can be true of a trainer that never trained. This one
builds a tiny population of real pictures, runs two epochs, and checks the things
that would be silent if they broke: that a partial build is refused, that the
evaluation pin is enforced at the location coordinate, and that what lands on
disk is a checkpoint another process can load and score with.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import head
from fractal_wallpapers.supply.location import location_key

pytest.importorskip("torch")
pytest.importorskip("timm")
numpy = pytest.importorskip("numpy")

FAMILY = {"kind": "mandelbrot"}


@pytest.fixture
def a_tiny_corpus(tmp_path, monkeypatch):
    """A population of real pictures, wired in where the real build would be."""
    from PIL import Image

    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    directory = tmp_path / "tiles"
    (directory / "cache").mkdir(parents=True)
    monkeypatch.setattr(tile_module, "tile_dir", lambda: directory)
    monkeypatch.setattr(train_module, "head_dir", lambda name="location": tmp_path / name)

    generator = numpy.random.default_rng(0)
    locations, manifest, pinned = [], [], set()
    for index in range(32):
        score = (index % 4) + 1
        # Distinct after canonicalization, which "-0.4" and "-0.40" are not:
        # the location key normalizes decimals, so a fixture that spelled them
        # that way would hold two names for one place.
        viewport = {"center_re": f"-{index}.5", "center_im": "0", "width": "3.0"}
        key = location_key(FAMILY, viewport)
        identifier = tile_module.location_id(key)
        side = pins.EVAL if index % 8 == 0 else pins.TRAIN
        if side == pins.EVAL:
            pinned.add(key)
        locations.append(
            {
                "schema": 1,
                "location_id": identifier,
                "family": FAMILY,
                "viewport": viewport,
                "score": score,
                "side": side,
                "partition": "mandelbrot",
                "group": index // 2,
                "batch": "a_batch",
                "biased": index % 3 == 0,
            }
        )
        for slot in range(2):
            path = directory / "cache" / f"{identifier}_{slot}.jpg"
            # A picture whose brightness carries the label, so two epochs of a
            # real loop have something to learn and the loss actually falls.
            shade = int(40 + 50 * score + generator.integers(-8, 8))
            Image.new("RGB", (head.SOURCE_WIDTH, head.SOURCE_HEIGHT), (shade, shade, shade)).save(
                path
            )
            manifest.append(
                {
                    "schema": 1,
                    "location_id": identifier,
                    "tile": slot,
                    "path": str(path),
                    "palette": "twilight_shifted",
                    "level": "antialiased",
                    "quality": 90,
                    "scale": 1.0,
                    "shift_frac": 0.0,
                    "partial": False,
                }
            )

    write(directory / "locations.jsonl", locations)
    write(directory / "manifest.jsonl", manifest)
    monkeypatch.setattr(pins, "pinned", lambda rows=None: set(pinned))
    return directory


def write(path, rows) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8", newline="\n"
    )


def test_the_trainer_refuses_a_build_that_is_missing_locations(a_tiny_corpus) -> None:
    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    rows = tile_module.read_manifest()
    write(a_tiny_corpus / "manifest.jsonl", rows[8:])
    with pytest.raises(ValueError, match="have no tiles"):
        train_module.population()


def test_a_bounded_rehearsals_tiles_are_refused(a_tiny_corpus) -> None:
    """A rehearsal writes real files. Training on them would train a real head on
    a prefix of the corpus and report the numbers of a whole one."""
    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    rows = tile_module.read_manifest()
    rows[0]["partial"] = True
    write(a_tiny_corpus / "manifest.jsonl", rows)
    with pytest.raises(ValueError, match="partial"):
        train_module.population()


def test_a_pinned_location_on_the_training_side_stops_the_run(a_tiny_corpus) -> None:
    """The failure the pin exists for, and the only place it can be caught: the
    coordinate. Everything downstream would read as a slightly better head."""
    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    rows = tile_module.read_locations()
    for row in rows:
        if row["side"] == pins.EVAL:
            row["side"] = pins.TRAIN
            break
    write(a_tiny_corpus / "locations.jsonl", rows)
    locations, _ = train_module.population()
    with pytest.raises(pins.EvalPinViolation, match="spent the moment it trains"):
        train_module.assert_the_pin_holds(locations)


def test_a_pin_the_build_cannot_find_is_a_pin_it_cannot_enforce(a_tiny_corpus) -> None:
    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    rows = [row for row in tile_module.read_locations() if row["side"] != pins.EVAL]
    tiles = tile_module.read_manifest()
    kept = {row["location_id"] for row in rows}
    write(a_tiny_corpus / "locations.jsonl", rows)
    write(a_tiny_corpus / "manifest.jsonl", [t for t in tiles if t["location_id"] in kept])
    locations, _ = train_module.population()
    with pytest.raises(pins.EvalPinViolation, match="cannot find"):
        train_module.assert_the_pin_holds(locations)


def test_two_epochs_leave_a_checkpoint_that_scores(a_tiny_corpus) -> None:
    from fractal_wallpapers.models import scoring
    from fractal_wallpapers.models import tiles as tile_module
    from fractal_wallpapers.models import train as train_module

    inherited = train_module.RECIPE.copy()
    # A smaller backbone and a corpus of thirty-two: what is under test is the
    # loop, not the architecture, and the shipped one is exercised by
    # `test_location_head`. Two epochs, because one cannot show a selection.
    #
    # One worker, not zero, and that is the whole reason the number is here. The
    # loader's workers are separate processes, so the dataset has to survive a
    # pickle; a zero-worker run never tries, and the failure lands at the first
    # batch of a real run after the corpus has been joined.
    train_module.RECIPE.update(
        {
            "backbone": "mobilenetv4_conv_small",
            "pretrained": False,
            "epochs": 2,
            "batch_size": 8,
            "workers": 1,
        }
    )
    try:
        record = train_module.train(device="cpu", log=lambda *_: None)
    finally:
        train_module.RECIPE.clear()
        train_module.RECIPE.update(inherited)

    assert record["locations"]["eval"] == 4
    assert record["locations"]["selection"] > 0
    assert len(record["history"]) == 2
    assert record["best_epoch"] in (0, 1)
    assert (
        record["locations"]["train"]
        + record["locations"]["selection"]
        + record["locations"]["eval"]
        == record["locations"]["total"]
    )
    # The resume snapshot is gone: a clean finish leaves nothing to continue.
    assert not (train_module.head_dir("location") / "resume.pt").exists()

    model, config, where = scoring.load(train_module.checkpoint_path("location", "best"), "cpu")
    assert config["classes"] == head.CLASSES
    assert config["precision"] == "fp32"
    probabilities = train_module.score(
        model,
        [tile_module.read_manifest()[0]["path"]],
        scoring.transform_of(config),
        where,
        int(config["classes"]),
        {"batch_size": 4},
    )
    assert probabilities.shape == (1, head.CLASSES - 1)
    assert (numpy.diff(probabilities, axis=1) <= 1e-12).all()
