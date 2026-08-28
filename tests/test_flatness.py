"""The dead-space column: what it reads, and the sidecar it lands in.

The reading's whole claim is the plane term — a cell a plane fits with nothing
left over holds no detail, however much its pixel values vary across it. So the
tests that matter here are the two a variance screen would get wrong: a **ramp**
is flat and a **noise field** is not.
"""

from __future__ import annotations

import numpy
import pytest
from PIL import Image

from fractal_wallpapers.curation import candidate_ledger, flatness


def picture(tmp_path, array, name="picture.jpg"):
    """One 8-bit greyscale picture on disk, written losslessly.

    PNG and not JPEG: the reading is a residual RMS under 1.0 on a 0-255 scale,
    which is finer than JPEG's own quantization, so a lossy round trip would be
    testing the codec rather than the column.
    """
    where = tmp_path / name
    Image.fromarray(numpy.clip(array, 0, 255).astype("uint8"), mode="L").save(
        where.with_suffix(".png")
    )
    return where.with_suffix(".png")


# --------------------------------------------------------------------------- #
# The reading.
# --------------------------------------------------------------------------- #
def test_a_uniform_picture_is_entirely_dead_space(tmp_path):
    flat = picture(tmp_path, numpy.full((64, 64), 128.0))
    assert flatness.fraction(flat) == 1.0


def test_a_smooth_ramp_is_dead_space_and_a_variance_screen_would_disagree(tmp_path):
    """THE property the plane term exists for.

    A ramp across the picture has a large variance in every cell and no detail in
    any of them. A variance screen would call this the busiest picture in the
    pool; the plane leaves nothing behind, so it reads as entirely dead.
    """
    ramp = numpy.tile(numpy.linspace(0, 255, 64, dtype=numpy.float32), (64, 1))
    assert ramp.var() > 1000
    assert flatness.fraction(picture(tmp_path, ramp)) == 1.0


def test_a_noise_field_holds_no_dead_space(tmp_path):
    noise = numpy.random.default_rng(0).integers(0, 256, (64, 64)).astype(numpy.float32)
    assert flatness.fraction(picture(tmp_path, noise)) == 0.0


def test_a_half_dead_picture_reads_a_half(tmp_path):
    array = numpy.zeros((32, 64), dtype=numpy.float32)
    array[:, 32:] = numpy.random.default_rng(1).integers(0, 256, (32, 32))
    assert flatness.fraction(picture(tmp_path, array)) == pytest.approx(0.5)


def test_a_picture_that_cannot_be_opened_reads_none_and_never_zero(tmp_path):
    """No detail and no picture are different facts. A zero would merge them, and
    the merged number would rank an unreadable candidate as the flattest thing in
    the pool."""
    missing = tmp_path / "not-there.jpg"
    assert flatness.fraction(missing) is None


def test_a_picture_smaller_than_one_cell_reads_none(tmp_path):
    assert flatness.fraction(picture(tmp_path, numpy.zeros((8, 8)))) is None


# --------------------------------------------------------------------------- #
# The sidecar.
# --------------------------------------------------------------------------- #
@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate_ledger, "store_root", lambda: tmp_path)
    return tmp_path


def test_the_sidecar_round_trips_by_recipe_key(store):
    flatness.write([flatness.row("a", 0.25), flatness.row("b", 0.5)])
    assert flatness.by_recipe() == {"a": 0.25, "b": 0.5}


def test_a_sidecar_that_has_never_been_swept_reads_empty_rather_than_raising(store):
    assert flatness.read() == []
    assert flatness.by_recipe() == {}


def test_writing_upserts_by_key_and_counts_only_the_new(store):
    flatness.write([flatness.row("a", 0.25)])
    _path, total, new = flatness.write([flatness.row("a", 0.75), flatness.row("b", 0.1)])
    assert (total, new) == (2, 1)
    assert flatness.by_recipe()["a"] == 0.75


def test_a_reading_taken_at_other_constants_is_left_out_and_not_flattened(store):
    """The join names its column for [`candidate_ledger.scores_by_recipe`]'s
    reason: a store holding two cell sizes must not silently become one ordering
    with nothing anywhere saying which reading a seat was taken on."""
    other = flatness.row("a", 0.25) | {"column": "flat32_2.0", "flat32_2.0": 0.25}
    flatness.write([other, flatness.row("b", 0.5)])
    assert flatness.by_recipe() == {"b": 0.5}


def test_the_row_carries_the_constants_it_was_read_at(store):
    row = flatness.row("a", 0.25)
    assert (row["cell"], row["threshold"], row["column"]) == (
        flatness.CELL,
        flatness.THRESHOLD,
        flatness.COLUMN,
    )


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
class Candidate:
    """The two fields the sweep reads. Not a `solve.Candidate`, on purpose: the
    sweep also runs over raw ledger rows, which have no score."""

    def __init__(self, key, picture):
        self.key = key
        self.picture = picture


def test_the_sweep_reads_what_the_sidecar_does_not_hold_and_skips_what_it_does(
    store, tmp_path, monkeypatch
):
    made = picture(tmp_path, numpy.full((64, 64), 10.0), name="one")
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda _path: made)
    pool = [Candidate("a", "artifacts/a.png"), Candidate("b", "artifacts/b.png")]

    first = flatness.sweep(pool, workers=1, log=lambda *_a, **_k: None)
    assert (first["swept"], first["read"]) == (2, 2)

    second = flatness.sweep(pool, workers=1, log=lambda *_a, **_k: None)
    assert (second["swept"], second["already_read"]) == (0, 2)


def test_coverage_names_what_the_key_would_not_be_able_to_rank(store, monkeypatch):
    flatness.write([flatness.row("a", 0.25)])
    pool = [Candidate("a", "artifacts/a.png"), Candidate("b", "artifacts/b.png")]
    report = flatness.coverage(pool)
    assert (report["with_a_reading"], report["without"]) == (1, 1)
    assert report["share"] == 0.5


def test_a_candidate_whose_picture_this_checkout_cannot_resolve_is_counted_apart(
    store, monkeypatch
):
    monkeypatch.setattr("fractal_wallpapers.paths.rehome", lambda _path: None)
    record = flatness.sweep(
        [Candidate("a", "artifacts/a.png")], workers=1, log=lambda *_a, **_k: None
    )
    assert record["no_resolvable_picture"] == 1
    assert record["swept"] == 0
