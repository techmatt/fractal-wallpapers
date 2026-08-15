"""The colormap conversion, held to the files it has to agree with.

A corpus names four hundred maps this repository did not curate, and they arrive
by mechanical conversion. The conversion is only trustworthy if it agrees with
the maps that were already here: a rule that produced a *different* gradient for
`twilight_shifted` than the tracked file holds would color one half of a corpus
one way and the other half another, and nothing downstream would say so.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import library_import

CYCLIC_HALF_OPEN = {
    "name": "wheel",
    "cycle": "cyclic",
    "mirror_needed": False,
    # Three stops on a four-point cycle: the closing one was left off.
    "stops": [[0.0, [10, 0, 0]], [0.25, [0, 10, 0]], [0.5, [0, 0, 10]], [0.75, [10, 10, 0]]],
}
CYCLIC_CLOSED = {
    "name": "closed",
    "cycle": "cyclic",
    "mirror_needed": False,
    "stops": [[0.0, [10, 0, 0]], [0.5, [0, 10, 0]], [1.0, [10, 0, 0]]],
}
SEQUENTIAL = {
    "name": "ramp",
    "cycle": "sequential",
    "mirror_needed": True,
    "stops": [
        [0.0, [0, 0, 0]],
        [0.25, [64, 64, 64]],
        [0.5, [128, 128, 128]],
        [0.75, [255, 255, 255]],
    ],
}


def test_a_half_open_cycle_gets_its_closing_stop_back() -> None:
    stops = library_import.stops_of(CYCLIC_HALF_OPEN)
    assert len(stops) == 5, "the closing stop was not added"
    assert stops[0][1] == stops[-1][1], "the map does not close on the color it opened with"
    assert [position for position, _ in stops] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert [rgb for _, rgb in stops[:4]] == [rgb for _, rgb in CYCLIC_HALF_OPEN["stops"]]


def test_a_closed_cycle_is_left_alone() -> None:
    stops = library_import.stops_of(CYCLIC_CLOSED)
    assert stops == [[0.0, [10, 0, 0]], [0.5, [0, 10, 0]], [1.0, [10, 0, 0]]]


def test_a_sequential_map_is_stretched_onto_the_whole_range() -> None:
    """Nothing is added — it runs end to end, so its far end simply moves to 1."""
    stops = library_import.stops_of(SEQUENTIAL)
    assert len(stops) == len(SEQUENTIAL["stops"])
    assert [position for position, _ in stops] == [0.0, 1 / 3, 2 / 3, 1.0]
    assert stops[-1][1] == [255, 255, 255]


def test_a_map_whose_two_cyclic_facts_disagree_is_refused() -> None:
    """`cycle` and `mirror_needed` are one fact written twice."""
    broken = {**SEQUENTIAL, "mirror_needed": False}
    with pytest.raises(library_import.PaletteImportError, match="one fact"):
        library_import.stops_of(broken)


def test_an_unevenly_spaced_map_is_refused_rather_than_re_indexed() -> None:
    """Re-indexing evenly would move colors relative to one another."""
    lumpy = {**SEQUENTIAL, "stops": [[0.0, [0, 0, 0]], [0.9, [1, 1, 1]], [1.0, [2, 2, 2]]]}
    with pytest.raises(library_import.PaletteImportError, match="evenly spaced"):
        library_import.stops_of(lumpy)


def test_a_converted_file_is_shaped_like_a_tracked_one() -> None:
    document = library_import.converted(CYCLIC_HALF_OPEN)
    assert document["schema"] == 1
    assert document["name"] == "wheel"
    assert document["kind"] == "cyclic"
    assert document["source"].strip()
    assert json.loads(library_import.text_of(document)) == document


def test_the_conversion_reproduces_every_map_that_is_already_tracked() -> None:
    """The one check that says the rule is the same rule.

    Skipped rather than failed where the source library is not on this machine:
    CI has no copy of it, and a test that cannot read its input has not found a
    defect.
    """
    from pathlib import Path

    from fractal_wallpapers.paths import colormap_dir

    source = Path("C:/Code/fractal-maker")
    if not (source / library_import.POOL).is_file():
        pytest.skip("the source colormap library is not on this machine")

    pool = library_import.read_pool(source)
    compared = 0
    for path in sorted(colormap_dir().glob("*.json")):
        entry = pool.get(path.stem)
        if entry is None:
            continue
        tracked = json.loads(path.read_text(encoding="utf-8"))
        converted = library_import.converted(entry)
        assert converted["kind"] == tracked["kind"], path.stem
        assert converted["stops"] == tracked["stops"], path.stem
        compared += 1
    assert compared > 70, f"only {compared} tracked maps were checked against the library"
