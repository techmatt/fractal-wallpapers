"""Palette space: what a distance between two maps means, and what it is used for."""

from __future__ import annotations

import json
import random

import pytest

from fractal_wallpapers.models import palette_sets
from fractal_wallpapers.palettes import space
from fractal_wallpapers.paths import colormap_dir


def test_black_and_white_are_the_ends_of_the_lightness_axis() -> None:
    """The descriptor is Oklab, so the numbers have to mean what Oklab says."""
    numpy = pytest.importorskip("numpy")
    values = space.oklab(numpy.asarray([[0, 0, 0], [255, 255, 255]], dtype=numpy.float64))
    assert values[0][0] == pytest.approx(0.0, abs=1e-6)
    assert values[1][0] == pytest.approx(1.0, abs=1e-3)
    assert abs(values[1][1]) < 1e-3 and abs(values[1][2]) < 1e-3


def test_the_linearisation_table_answers_every_code_exactly_as_the_arithmetic_does() -> None:
    """A `uint8` channel is linearised by table, and a table is only allowed to
    replace the `**2.4` it stands in for if it is that expression's own answer at
    all 256 codes — bit for bit, not to a tolerance. Otherwise every tone
    statistic in the repository quietly moves."""
    numpy = pytest.importorskip("numpy")

    codes = numpy.arange(256, dtype=numpy.uint8)
    by_table = space._srgb_to_linear(codes)
    by_arithmetic = space._linearise(numpy.arange(256))
    assert by_table.dtype == numpy.float64
    assert numpy.array_equal(by_table.view(numpy.uint64), by_arithmetic.view(numpy.uint64))

    # And through the conversion a measurement really calls, on a picture that
    # holds every code in every channel: the same numbers whichever dtype the
    # caller hands over.
    picture = numpy.stack([codes, numpy.roll(codes, 85), numpy.roll(codes, 170)], axis=-1).reshape(
        16, 16, 3
    )
    lab = space.oklab(picture)
    assert numpy.array_equal(
        lab.view(numpy.uint64),
        space.oklab(picture.astype(numpy.float64)).view(numpy.uint64),
    )


def test_a_sequential_map_is_sampled_folded_and_a_cyclic_one_is_not() -> None:
    """What the descriptor compares is the gradient the renderer really spends,
    and a map that does not close on the colour it opened with is folded to hide
    its seam. The fold is read off the map's kind, here as everywhere else."""
    names = {
        path.stem: json.loads(path.read_text(encoding="utf-8")).get("kind")
        for path in colormap_dir().glob("*.json")
    }
    numpy = pytest.importorskip("numpy")

    def palindrome(name: str) -> bool:
        return bool(numpy.allclose(space.spent(name), space.spent(name)[::-1]))

    sequential = [name for name, kind in names.items() if kind != "cyclic"]
    cyclic = [name for name, kind in names.items() if kind == "cyclic"]
    # A folded gradient goes out and comes back, so EVERY sequential map's samples
    # are a palindrome. A cyclic one is swept once — some of them happen to be
    # symmetric anyway, which is why this reads the population and not one map.
    assert all(palindrome(name) for name in sequential[:40])
    assert not all(palindrome(name) for name in cyclic[:40])


def test_a_map_is_at_no_distance_from_itself() -> None:
    numpy = pytest.importorskip("numpy")
    names = sorted(path.stem for path in colormap_dir().glob("*.json"))[:12]
    matrix = space.distances(names)
    assert numpy.allclose(numpy.diagonal(matrix), 0.0, atol=1e-9)
    assert numpy.allclose(matrix, matrix.T)


def test_a_neighbourhood_opens_on_its_own_anchor() -> None:
    pool = palette_sets.pool()["pool"]
    members = space.neighbourhood(pool[5], pool, 8)
    assert members[0] == pool[5]
    assert len(set(members)) == 8


def test_a_neighbourhood_is_measurably_tighter_than_a_uniform_draw() -> None:
    """This is the whole reason the module exists. A hard set is meant to ask a
    finer question than a uniform draw does, and the number that says whether it
    does is the mean distance between its members."""
    pool = palette_sets.pool()["pool"]
    generator = random.Random(0)
    near = [
        space.tightness(space.neighbourhood(anchor, pool, 32))["mean"]
        for anchor in generator.sample(pool, 12)
    ]
    far = [space.tightness(generator.sample(pool, 32))["mean"] for _ in range(12)]
    assert max(near) < min(far)


def test_a_set_cannot_be_drawn_from_a_pool_that_cannot_supply_it() -> None:
    with pytest.raises(space.SpaceError):
        space.neighbourhood("a", ["a", "b"], 5)
    with pytest.raises(space.SpaceError):
        space.neighbourhood("z", ["a", "b"], 2)


def test_a_map_nobody_holds_is_a_refusal_and_not_a_guess() -> None:
    with pytest.raises(space.SpaceError):
        space.ramp("a map this repository has never heard of")
