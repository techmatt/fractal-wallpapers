"""The three pictures every palette sheet is judged on: the spec, not the pixels.

A sheet that mixes two fields is two instruments, and these three lived only in a
session scratchpad through three audit passes. What is tracked now is the spec —
twelve numbers a machine can make the field from — and what this checks is that
the spec is complete enough to be that: every member the engine needs, at the
geometry the sheets were built at, for three distinct modes.

Making the fields is an engine call and is not done here. The claim it would test
— that these numbers reproduce the dumps byte for byte — was verified once against
the surviving copies, and re-verifying it per test run would be paying three
iteration passes to learn that the engine is deterministic.
"""

from __future__ import annotations

from pathlib import Path

from fractal_wallpapers.palettes import reference_fields
from fractal_wallpapers.paths import colormap_dir


def test_there_are_three_and_they_are_the_three_classes() -> None:
    """One field per class of picture the library has to survive. A class missing
    would be a class no sheet ever asks a map about."""
    rows = reference_fields.read()
    assert [row["class"] for row in rows] == list(reference_fields.CLASSES)
    assert all(row["kind"] == reference_fields.FIELD_ROW for row in rows)


def test_no_coloring_speaks_twice() -> None:
    """The selection rule's one constraint: three different modes. Two fields in
    one mode would let a single coloring cast two of the three votes a sheet takes."""
    modes = [row["mode"] for row in reference_fields.read()]
    assert len(set(modes)) == len(modes) == 3


def test_a_spec_carries_everything_the_engine_needs_to_make_the_field_again() -> None:
    """The whole reason the dump is not tracked. A spec missing `maxiter` or a
    viewport digit is a field nobody can remake, and a megabyte of floats that
    only exists in one place is how these three nearly died."""
    for row in reference_fields.read():
        spec = reference_fields.spec(row, Path("out.f32"))
        assert set(spec) == {
            "schema",
            "family",
            "viewport",
            "resolution",
            "supersample",
            "maxiter",
            "mode",
            "colormap",
            "colormap_dir",
            "output",
        }
        assert spec["resolution"] == list(reference_fields.RESOLUTION)
        assert spec["supersample"] == reference_fields.SUPERSAMPLE
        assert spec["maxiter"] > 0
        # Strings, not floats: a viewport at 4e-11 across has no digits left in
        # `f64`, and a spec that rounded one would name a different place.
        assert all(isinstance(value, str) for value in row["viewport"].values())


def test_the_fields_land_under_artifacts_and_the_spec_lands_in_the_tree() -> None:
    """The split the module exists for: regenerable binary out, twelve numbers in."""
    assert reference_fields.record_path().parent == colormap_dir()
    assert reference_fields.record_path().suffix != ".json"
    assert (
        "artifacts" in reference_fields.dump_dir().parts
        or reference_fields.dump_dir().is_absolute()
    )
    for row in reference_fields.read():
        assert reference_fields.field_path(row).suffix == ".f32"


def test_the_record_survives_a_round_trip() -> None:
    """Written the way it is read. A rewrite that reordered the classes would move
    which picture a sheet's first column shows without changing a pixel."""
    rows = [row for row in reference_fields.read()]
    text = reference_fields.record_path().read_text(encoding="utf-8")
    assert all(reference_fields.text_of([row]).strip() in text for row in rows)
