"""The variant derivation: exact where it claims to be, and named mechanically."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import variants
from fractal_wallpapers.paths import colormap_dir

#: One cyclic map and one sequential one, both small enough to reason about by
#: hand. `jet` is the sequential case the seam rule was calibrated on.
CYCLIC_MAP = "twilight"
SEQUENTIAL_MAP = "jet"


def load(name: str) -> dict:
    return variants.read(colormap_dir() / f"{name}.json")


def colours(document: dict) -> list:
    return [list(rgb) for _position, rgb in document["stops"]]


def test_a_positional_axis_is_a_permutation_of_the_base_colours():
    """Phase, reversal and repetition invent no colour: the multiset is the base's."""
    base = load(CYCLIC_MAP)
    held = sorted(map(tuple, colours(base)[:-1]))
    for axis, dose in (("phase", 250), ("phase", 750), ("reverse", None), ("repeat", 3)):
        made = variants.derive(base, axis, dose)
        got = sorted(map(tuple, colours(made)[:-1]))
        repeats = dose if axis == "repeat" else 1
        assert got == sorted(held * repeats), f"{axis} moved a colour"


def test_a_full_turn_of_phase_is_the_base_map():
    """The rotation is index arithmetic on a closed ramp, so 1000 thousandths is identity."""
    base = load(CYCLIC_MAP)
    assert colours(variants.derive(base, "phase", 1000)) == colours(base)


def test_phase_rounds_to_a_whole_stop_and_says_what_landed():
    """A dose the stop count cannot express is rounded, and the record carries both."""
    base = load(SEQUENTIAL_MAP)  # 33 stops, so a 32-position loop
    made = variants.derive(base, "phase", 125)
    assert made["variant"]["dose"] == 125
    assert made["variant"]["landed"] == pytest.approx(4 / 32)


def test_reversal_is_its_own_inverse():
    for name in (CYCLIC_MAP, SEQUENTIAL_MAP):
        base = load(name)
        once = variants.derive(base, "reverse", None)
        twice = variants.derive({**once, "name": name}, "reverse", None)
        assert colours(twice) == colours(base)


def test_repetition_keeps_the_ramp_resolution():
    """A tiling is `times` copies of the open ramp, not a resample down to one."""
    base = load(CYCLIC_MAP)
    width = len(base["stops"]) - 1
    for times in (2, 3):
        made = variants.derive(base, "repeat", times)
        assert len(made["stops"]) == width * times + 1


def test_a_repetition_of_one_is_refused():
    with pytest.raises(variants.VariantError):
        variants.derive(load(CYCLIC_MAP), "repeat", 1)


def test_the_kind_flip_moves_the_kind_and_the_mirror_together():
    """`kind` and the recipe's `mirror` are one decision, and the engine refuses the pair."""
    for name, flipped, folds in (
        (CYCLIC_MAP, "sequential", True),
        (SEQUENTIAL_MAP, "cyclic", False),
    ):
        base = load(name)
        made = variants.derive(base, "kind", None)
        assert made["kind"] == flipped
        assert made["variant"]["mirror"] is folds
        assert variants.mirror_for(made["kind"]) is folds
        # The colours are untouched: this axis changes how the map is baked and
        # nothing about what is in it.
        assert colours(made) == colours(base)


def test_mirror_is_never_asked_for_on_a_cyclic_map():
    """The engine refuses that pair outright — `colormap.rs` says folding halves the cycle."""
    assert variants.mirror_for(variants.CYCLIC) is False
    assert variants.mirror_for(variants.SEQUENTIAL) is True


def test_chroma_and_lightness_move_the_axis_they_name():
    """Each Oklab axis moves in the direction asked, measured back off the sRGB8 stops."""
    import numpy

    from fractal_wallpapers.palettes import space

    base = load(CYCLIC_MAP)
    before = space.oklab(numpy.asarray(colours(base), dtype=numpy.float64))
    for axis, dose, channel, up in (
        ("chroma", 50, "chroma", False),
        ("light", 120, "lightness", True),
        ("light", 80, "lightness", False),
    ):
        after = space.oklab(
            numpy.asarray(colours(variants.derive(base, axis, dose)), dtype=numpy.float64)
        )
        if channel == "chroma":
            was = numpy.hypot(before[:, 1], before[:, 2]).mean()
            now = numpy.hypot(after[:, 1], after[:, 2]).mean()
        else:
            was, now = before[:, 0].mean(), after[:, 0].mean()
        # `bool(...)`, because `now` and `was` are numpy scalars and a `numpy.bool_`
        # is not the Python singleton an `is` comparison would be asking about.
        assert bool(now > was) is up, f"{axis} {dose} moved {channel} the wrong way"


def test_a_seam_is_counted_on_a_rotated_sequential_map_and_never_on_a_cyclic_one():
    """Rotating a ramp whose ends do not meet puts the fold-back inside the sweep."""
    sequential = load(SEQUENTIAL_MAP)
    assert variants.derive(sequential, "phase", 500)["variant"]["seams"] == 1
    assert variants.derive(sequential, "repeat", 3)["variant"]["seams"] == 3
    assert variants.derive(sequential, "reverse", None)["variant"]["seams"] == 0
    cyclic = load(CYCLIC_MAP)
    for axis, dose in variants.DOSES:
        assert variants.derive(cyclic, axis, dose)["variant"]["seams"] == 0


def test_a_variant_name_is_mechanical_and_splits_back_to_its_base():
    assert variants.name_of("jet", "phase", 250) == "jet~phase-250"
    assert variants.name_of("jet", "reverse", None) == "jet~reverse"
    assert variants.name_of("jet", "repeat", 3) == "jet~repeat-3"
    assert variants.base_of("river-of-light-25~light-080") == "river-of-light-25"
    assert variants.base_of("river-of-light-25") == "river-of-light-25"
    assert variants.is_variant("jet~kind") and not variants.is_variant("jet")


def test_no_tracked_map_carries_the_mark():
    """What makes `base_of` total: the mark is a character the library does not use."""
    held = [path.stem for path in colormap_dir().glob("*.json")]
    assert held, "the tracked library is empty"
    assert not [name for name in held if variants.MARK in name]


def test_every_dose_names_a_declared_axis_and_the_family_is_the_doses():
    assert {axis for axis, _dose in variants.DOSES} <= set(variants.AXES)
    made = variants.family(load(CYCLIC_MAP))
    assert len(made) == len(variants.DOSES)
    assert len({one["name"] for one in made}) == len(variants.DOSES)


def test_a_variant_is_the_document_the_engine_reads():
    """`ColormapFile` names five members and denies nothing else at the top level."""
    made = variants.derive(load(CYCLIC_MAP), "phase", 250)
    assert {"schema", "name", "kind", "source", "stops"} <= set(made)
    assert made["kind"] in (variants.CYCLIC, variants.SEQUENTIAL)
    positions = [position for position, _rgb in made["stops"]]
    assert positions[0] == 0.0 and positions[-1] == 1.0
    assert positions == sorted(positions)
    assert all(0 <= value <= 255 for _p, rgb in made["stops"] for value in rgb)


def test_write_lands_where_it_is_pointed_and_never_defaults_to_the_library(tmp_path):
    made = variants.derive(load(CYCLIC_MAP), "chroma", 150)
    path = variants.write(made, tmp_path)
    assert path.parent == tmp_path
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == made["name"]
    assert "\r" not in path.read_bytes().decode("utf-8")
    with pytest.raises(TypeError):
        variants.write(made)  # the directory is required, not defaulted


def test_an_uneven_ramp_is_refused_rather_than_interpolated():
    document = {
        "schema": 1,
        "name": "hand made",
        "kind": "sequential",
        "source": "a test",
        "stops": [[0.0, [0, 0, 0]], [0.3, [10, 10, 10]], [1.0, [255, 255, 255]]],
    }
    with pytest.raises(variants.VariantError):
        variants.derive(document, "phase", 250)
