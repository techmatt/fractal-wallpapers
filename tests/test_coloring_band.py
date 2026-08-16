"""The tone band: what ships, what it refuses to default, and what it is measured on."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.coloring import autolevel, band

numpy = pytest.importorskip("numpy")


def test_the_shipped_band_loads_and_carries_its_own_digest() -> None:
    """A stamp names the band by contents, so a re-derivation that moved an edge
    is visible from the stamp alone."""
    record = band.load()
    assert record["schema"] == band.SCHEMA
    assert len(record["_sha256"]) == 64
    assert record["n_images"] >= 1
    for name, edges in band.bands(record).items():
        assert name in autolevel.STATISTICS
        assert edges[0] <= edges[1]


def test_the_shipped_band_names_no_machine() -> None:
    """The reference set lives outside this repository; what ships is the
    measurement and the names it was taken over, never a path."""
    text = band.record_path().read_text(encoding="utf-8")
    assert ":\\" not in text
    assert "/Users/" not in text
    assert "/home/" not in text


def test_a_statistic_nothing_could_measure_is_absent_rather_than_defaulted(tmp_path) -> None:
    path = tmp_path / "band.json"
    path.write_text(
        json.dumps(
            {
                "schema": band.SCHEMA,
                "bands": {"white_pt": {"band": [0.8, 0.99]}, "mid": {"band": [0.2, 0.7]}},
            }
        ),
        encoding="utf-8",
    )
    record = band.load(path)
    assert "black_pt" not in band.bands(record)


def test_a_band_from_a_different_schema_is_refused(tmp_path) -> None:
    path = tmp_path / "band.json"
    path.write_text(json.dumps({"schema": 99, "bands": {}}), encoding="utf-8")
    with pytest.raises(band.BandError):
        band.load(path)


def test_a_missing_band_says_how_to_derive_one(tmp_path) -> None:
    with pytest.raises(band.BandError, match="derive-band"):
        band.load(tmp_path / "absent.json")


def test_a_folder_with_no_picture_derives_nothing(tmp_path) -> None:
    (tmp_path / "notes.txt").write_text("not a wallpaper", encoding="utf-8")
    with pytest.raises(band.BandError):
        band.images_of(tmp_path)


def test_the_digest_notices_a_renamed_file_and_an_edited_one(tmp_path) -> None:
    from PIL import Image

    def write(name: str, value: int) -> None:
        Image.fromarray(numpy.full((8, 8, 3), value, dtype=numpy.uint8)).save(tmp_path / name)

    write("a.png", 10)
    first = band.set_digest(band.images_of(tmp_path))
    write("a.png", 11)
    assert band.set_digest(band.images_of(tmp_path)) != first
    write("a.png", 10)
    (tmp_path / "a.png").rename(tmp_path / "b.png")
    assert band.set_digest(band.images_of(tmp_path)) != first


def test_deriving_a_band_measures_every_picture_through_the_operators_own_reader(
    tmp_path,
) -> None:
    from PIL import Image

    for index, value in enumerate((40, 120, 200)):
        ramp = numpy.tile(
            numpy.linspace(0, value, 64, dtype=numpy.uint8)[:, None, None], (1, 64, 3)
        )
        Image.fromarray(ramp).save(tmp_path / f"{index}.png")
    record = band.derive(tmp_path)
    assert record["n_images"] == 3
    assert len(record["per_image"]) == 3
    assert record["measured_by"].startswith("coloring.autolevel.tone_stats")
    for name in autolevel.STATISTICS:
        assert record["bands"][name]["band"][0] <= record["bands"][name]["band"][1]
