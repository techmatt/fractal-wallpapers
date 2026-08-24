"""The densifier: a port of the archive's, held to the maps it already produced.

Turning authored control points into a dense gradient is the one step in this
repository where a bug is invisible. A wrong colour in the middle of a segment
does not crash anything and does not look wrong — it looks like a different
palette, and the brief that would have caught it is in a file nobody opens.

So the test is not a tolerance. The 175 authored maps this repository shipped
before drops existed were densified by the source project, and each one's
provenance row carries the control points it was densified *from*. Densifying
them again here has to give back the tracked file, stop for stop. Anything else
means a map added tomorrow is baked by different arithmetic than a map added last
year, and half the library would be subtly off-brief with nothing to say so.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import authored_import, provenance
from fractal_wallpapers.paths import colormap_dir


@pytest.fixture(scope="module")
def authored() -> list[dict]:
    rows = [
        row
        for row in provenance.read().values()
        if row["source"] == provenance.AUTHORED and "drop" not in row
    ]
    assert rows, "no pre-drop authored rows to check the densifier against"
    return rows


def test_densifying_an_authored_row_reproduces_its_tracked_map(authored) -> None:
    """The whole claim: this is the archive's densifier, not a second one."""
    pytest.importorskip("numpy")
    for row in authored:
        tracked = json.loads((colormap_dir() / f"{row['name']}.json").read_text(encoding="utf-8"))
        assert authored_import.densify(row["stops"]) == tracked["stops"], row["name"]


def test_the_dense_gradient_agrees_with_the_kind_the_library_ships(authored) -> None:
    """`kind` is what every fold in this repository is read off. Measuring it here
    has to reach the same answer the tracked file carries, or one of the two is
    colouring a seam nobody asked for."""
    pytest.importorskip("numpy")
    for row in authored:
        tracked = json.loads((colormap_dir() / f"{row['name']}.json").read_text(encoding="utf-8"))
        dense = authored_import.densify(row["stops"])
        assert authored_import.kind_of(row["stops"], dense) == tracked["kind"], row["name"]


def test_a_gradient_that_does_not_close_is_sequential() -> None:
    """The bit the archive's densifier hard-coded. A palette whose ends do not meet
    is folded by everything downstream, and calling it cyclic would show the seam
    in every render of it."""
    pytest.importorskip("numpy")
    stops = [
        {"pos": 0.0, "oklch": [0.10, 0.02, 250.0], "role": "ground"},
        {"pos": 0.5, "oklch": [0.60, 0.12, 40.0], "role": "anchor"},
        {"pos": 1.0, "oklch": [0.95, 0.02, 90.0], "role": "glow"},
    ]
    dense = authored_import.densify(stops)
    assert authored_import.kind_of(stops, dense) == "sequential"
    assert dense[0][1] != dense[-1][1]

    stops[-1] = {**stops[0], "pos": 1.0}
    dense = authored_import.densify(stops)
    assert authored_import.kind_of(stops, dense) == "cyclic"
    assert dense[0][1] == dense[-1][1]


def test_a_densified_map_spans_the_range_evenly() -> None:
    """The same even re-indexing a converted map gets: a position column that says
    nothing about which door the map came in through."""
    pytest.importorskip("numpy")
    stops = [
        {"pos": 0.0, "oklch": [0.20, 0.05, 20.0], "role": "ground"},
        {"pos": 0.4, "oklch": [0.80, 0.10, 200.0], "role": "glow", "segment": "cliff"},
        {"pos": 1.0, "oklch": [0.20, 0.05, 20.0], "role": "ground"},
    ]
    dense = authored_import.densify(stops)
    assert len(dense) == authored_import.DENSE
    assert dense[0][0] == 0.0 and dense[-1][0] == 1.0
    assert [position for position, _ in dense] == [
        index / (authored_import.DENSE - 1) for index in range(authored_import.DENSE)
    ]


def test_stops_that_do_not_span_the_range_are_refused() -> None:
    """Rescaling them would stretch the palette rather than sample it, and the
    author's positions are where the author put the colours."""
    pytest.importorskip("numpy")
    with pytest.raises(authored_import.AuthoredImportError):
        authored_import.densify(
            [
                {"pos": 0.0, "oklch": [0.2, 0.05, 20.0], "role": "ground"},
                {"pos": 0.9, "oklch": [0.8, 0.05, 20.0], "role": "glow"},
            ]
        )


def test_every_tracked_drop_reads_and_ships_unique_names() -> None:
    """A drop is provenance for maps this repository ships, so it has to resolve:
    its batch names have to parse, and no two of its palettes may claim one name."""
    for drop in authored_import.drops():
        rows = authored_import.briefs(drop)
        assert rows, f"drop {drop} holds no palettes"
        for name, row in rows.items():
            assert row["drop"] == drop
            assert row["name"] == name
            assert (colormap_dir() / f"{name}.json").is_file(), f"{name} was never densified"


def test_a_rename_says_what_it_was_and_why() -> None:
    """The rename record is the only place a name changes, and a rename with no
    reason is a name nobody can defend later."""
    for drop in authored_import.drops():
        rows = authored_import.briefs(drop)
        renames = authored_import.renames_of(authored_import.drop_dir(drop))
        shipped = {row["shipped"] for row in renames.values()}
        assert shipped <= set(rows)
        for row in renames.values():
            assert rows[row["shipped"]]["emitted_name"] == row["emitted"]
            assert row["why"].strip()
