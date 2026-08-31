"""The complexity descriptors: what each one claims, and where it refuses.

Each descriptor here exists to say something [`flatness`] cannot — how busy the
*live* part of a picture is. So the tests are the orderings each one is being
asked for: noise above filigree above a ramp, a contrast change that must move
nothing, and a spectrum whose exponent falls as the structure gets finer.

Every one of these is arithmetic over a picture written in the test, so the whole
file is fast lane. Nothing here reads the tracked stores.
"""

from __future__ import annotations

import numpy
import pytest
from PIL import Image

from fractal_wallpapers.curation import detail, flatness


def picture(tmp_path, array, name="picture.png"):
    """One 8-bit greyscale picture on disk, written losslessly.

    PNG for [`test_flatness.picture`]'s reason: the plane fit's threshold is a
    residual RMS under 1.0 on a 0-255 scale, which is finer than JPEG's own
    quantization, so a lossy round trip would be testing the codec.
    """
    where = tmp_path / name
    Image.fromarray(numpy.clip(array, 0, 255).astype("uint8"), mode="L").save(where)
    return where


def noise(shape=(128, 128), scale=40.0, seed=7):
    return 128.0 + numpy.random.default_rng(seed).normal(0.0, scale, shape)


def ramp(shape=(128, 128)):
    return numpy.tile(numpy.linspace(0, 255, shape[1], dtype=numpy.float32), (shape[0], 1))


# --------------------------------------------------------------------------- #
# The gradient, in units of the picture's own contrast.
# --------------------------------------------------------------------------- #
def test_noise_carries_more_gradient_energy_than_a_ramp():
    assert detail.gradient_energy(noise()) > 10 * detail.gradient_energy(ramp())


def test_the_normalization_is_what_makes_it_a_reading_of_the_picture():
    """THE property the contrast divisor exists for.

    Doubling every pixel's distance from the mean doubles the gradient and
    doubles the contrast, so the reading must not move. Without the divisor this
    column would rank a picture by how hard its palette pushes, which is a fact
    about the colormap and not about the structure.
    """
    field = noise()
    stretched = 128.0 + (field - 128.0) * 1.9
    assert detail.gradient_energy(stretched) == pytest.approx(
        detail.gradient_energy(field), rel=1e-6
    )


def test_a_picture_with_no_contrast_has_no_gradient_reading():
    assert detail.gradient_energy(numpy.full((64, 64), 128.0)) is None


def test_a_picture_too_small_to_difference_reads_nothing():
    assert detail.gradient_energy(numpy.zeros((2, 2))) is None


# --------------------------------------------------------------------------- #
# The spectrum.
# --------------------------------------------------------------------------- #
def _sinusoid(shape, cycles):
    across = numpy.arange(shape[1], dtype=numpy.float32) / shape[1]
    return 128.0 + 80.0 * numpy.tile(numpy.cos(2 * numpy.pi * cycles * across), (shape[0], 1))


def test_the_exponent_falls_as_the_structure_gets_finer():
    """The sign convention, pinned: `P(k) ~ k**-a` and a busier picture reads a
    SMALLER `a`. Every other reading here goes up with complexity and this one
    goes down, which is exactly the way round to get wrong."""
    coarse = detail.spectral_slope(_sinusoid((128, 128), 3))
    fine = detail.spectral_slope(_sinusoid((128, 128), 40))
    assert fine < coarse


def test_white_noise_is_flat_and_reads_an_exponent_near_zero():
    assert detail.spectral_slope(noise((256, 256))) == pytest.approx(0.0, abs=0.35)


def test_a_blurred_field_is_steeper_than_the_field_it_came_from():
    field = noise((256, 256))
    blurred = field.copy()
    for _ in range(6):
        blurred = (
            blurred
            + numpy.roll(blurred, 1, 0)
            + numpy.roll(blurred, -1, 0)
            + numpy.roll(blurred, 1, 1)
            + numpy.roll(blurred, -1, 1)
        ) / 5.0
    assert detail.spectral_slope(blurred) > detail.spectral_slope(field) + 1.0


def test_a_constant_picture_has_no_spectrum_to_fit():
    assert detail.spectral_slope(numpy.full((64, 64), 200.0)) is None


def test_a_picture_smaller_than_the_lowest_band_reads_nothing():
    assert detail.spectral_slope(noise((8, 8))) is None


# --------------------------------------------------------------------------- #
# Bits per pixel.
# --------------------------------------------------------------------------- #
def test_bits_per_pixel_is_the_stored_size_over_the_pixel_count(tmp_path):
    where = picture(tmp_path, noise((64, 64)))
    assert detail.bits_per_pixel(where) == pytest.approx(
        where.stat().st_size * 8 / (64 * 64), rel=1e-9
    )


def test_a_busy_jpeg_costs_more_bits_per_pixel_than_a_smooth_one(tmp_path):
    """The claim the column rests on: at a fixed quality the encoder spends its
    bytes where there is structure to spend them on."""
    busy, smooth = tmp_path / "busy.jpg", tmp_path / "smooth.jpg"
    for where, array in ((busy, noise((256, 256))), (smooth, ramp((256, 256)))):
        Image.fromarray(numpy.clip(array, 0, 255).astype("uint8"), mode="L").save(where, quality=90)
    assert detail.bits_per_pixel(busy) > 5 * detail.bits_per_pixel(smooth)


def test_a_picture_that_is_not_there_has_no_size(tmp_path):
    assert detail.bits_per_pixel(tmp_path / "nothing.jpg") is None


# --------------------------------------------------------------------------- #
# The other cell sizes.
# --------------------------------------------------------------------------- #
def test_the_shipped_cell_reads_exactly_what_the_shipped_column_reads(tmp_path):
    """The three new scales are only comparable to `flat16_1.0` if they are the
    same rule, so this pins that they ARE the same rule and not a copy of it."""
    where = picture(tmp_path, noise((128, 128), scale=3.0))
    assert detail.flat_fraction(where, flatness.CELL) == flatness.fraction(where)


def test_a_bigger_cell_is_harder_to_fit_flat_on_the_same_picture(tmp_path):
    """A cell a plane fits is a cell with no detail, and a larger cell has more
    for a plane to miss — so at one threshold the fraction falls with the cell.
    This is the whole reason to read four scales rather than one."""
    where = picture(tmp_path, noise((256, 256), scale=1.2))
    readings = [detail.flat_fraction(where, cell) for cell in detail.CELLS]
    assert readings == sorted(readings, reverse=True)
    assert readings[0] > readings[-1]


def test_the_column_name_carries_the_constants_it_was_read_at():
    assert detail.flat_column(16) == flatness.COLUMN
    assert detail.flat_column(64) == "flat64_1.0"


# --------------------------------------------------------------------------- #
# One picture, every column.
# --------------------------------------------------------------------------- #
def test_a_reading_carries_its_geometry_and_every_column(tmp_path):
    row = detail.read(picture(tmp_path, noise((72, 128))))
    assert row["geometry"] == "128x72"
    assert row["unreadable"] is False
    assert all(row[name] is not None for name in detail.COLUMNS)


def test_a_picture_that_cannot_be_opened_reads_every_column_as_nothing(tmp_path):
    where = tmp_path / "torn.jpg"
    where.write_bytes(b"not a picture")
    row = detail.read(where)
    assert row["unreadable"] is True
    assert row["geometry"] is None
    assert all(row[name] is None for name in detail.COLUMNS)


def test_the_sweep_is_the_same_answer_as_reading_each_one(tmp_path):
    pairs = [(str(at), picture(tmp_path, noise((64, 64), seed=at), f"{at}.png")) for at in range(3)]
    swept = detail.sweep(pairs, workers=1, log=lambda *_: None)
    assert {key: swept[key]["grad_energy"] for key, _ in pairs} == {
        key: detail.read(where)["grad_energy"] for key, where in pairs
    }


# --------------------------------------------------------------------------- #
# Comparing them.
# --------------------------------------------------------------------------- #
def test_standardization_is_taken_inside_a_geometry_and_never_across():
    """THE property [`standardize_within`] exists for. Two geometries whose raw
    values do not overlap at all still both centre on zero — a single mean over
    the pool would instead rank every picture at one geometry above every picture
    at the other, for no reason about the pictures."""
    rows = {
        "a": {"geometry": "640x360", "bpp": 1.0},
        "b": {"geometry": "640x360", "bpp": 3.0},
        "c": {"geometry": "1280x720", "bpp": 100.0},
        "d": {"geometry": "1280x720", "bpp": 300.0},
    }
    z = detail.standardize_within(rows, "bpp")
    assert z["a"] == pytest.approx(-1.0) and z["b"] == pytest.approx(1.0)
    assert z["c"] == pytest.approx(-1.0) and z["d"] == pytest.approx(1.0)


def test_a_row_with_no_reading_is_absent_rather_than_standardized_to_zero():
    rows = {"a": {"geometry": "g", "bpp": 1.0}, "b": {"geometry": "g", "bpp": None}}
    assert set(detail.standardize_within(rows, "bpp")) == {"a"}


def test_a_constant_geometry_standardizes_to_zero_rather_than_dividing_by_nothing():
    rows = {"a": {"geometry": "g", "bpp": 2.0}, "b": {"geometry": "g", "bpp": 2.0}}
    assert detail.standardize_within(rows, "bpp") == {"a": 0.0, "b": 0.0}


def test_the_rank_correlation_is_monotone_and_not_linear():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert detail.spearman(values, [1.0, 8.0, 27.0, 64.0, 125.0]) == pytest.approx(1.0)
    assert detail.spearman(values, list(reversed(values))) == pytest.approx(-1.0)


def test_the_rank_correlation_carries_ties_at_the_mean_rank():
    assert detail.spearman([1.0, 1.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0]) == pytest.approx(1.0)


def test_a_constant_side_has_no_rank_correlation():
    assert detail.spearman([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]) is None
