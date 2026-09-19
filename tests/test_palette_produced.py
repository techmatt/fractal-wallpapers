"""The table of which colours each map has actually made.

What is pinned here is that the committed table is about the library it sits in,
that its columns are the wheel's twelve in the wheel's order, that a count is a
count of the map's own pictures, and that a name carrying a comma survives the
round trip — every reader of this file, here and on the website, reads it with
the csv module for exactly that reason.

The tally itself is a reading of an untracked artifact and is not re-taken here:
the ledger is three quarters of a gigabyte and is written to by any pass that is
running, so a test that recomputed it would be testing whichever pass ran last.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.palettes import codebook, produced


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    return produced.read()


def test_the_columns_are_the_wheel_in_the_wheels_order() -> None:
    """Twelve hue columns, in `codebook.HUES` order, after the name and the count.

    The order is load-bearing on the reading side: a consumer that took the
    columns positionally would file every map one spoke over.
    """
    assert produced.columns() == [
        produced.NAME_COLUMN,
        produced.COUNT_COLUMN,
        *(name for name, _ in codebook.HUES),
    ]
    assert len(produced.HUES) == 12


def test_every_map_in_the_library_has_a_row_and_nothing_else_does(rows) -> None:
    """One row per map, absences included — see the module docstring."""
    named = [row[produced.NAME_COLUMN] for row in rows]
    assert named == produced.library_names()
    assert len(named) == len(set(named))


def test_a_hue_count_never_exceeds_the_pictures_it_is_counted_over(rows) -> None:
    """A map cannot have made more pictures of a colour than it made pictures."""
    for row in rows:
        for hue in produced.HUES:
            assert 0 <= row[hue] <= row[produced.COUNT_COLUMN], f"{row[produced.NAME_COLUMN]}.{hue}"


def test_the_two_maps_held_out_of_the_pool_have_rows_of_nought(rows) -> None:
    """`blue_orange` and `atlas_grey` are in the library and out of the candidate
    pool, so they have made nothing. A row of zeros says that; an absent row would
    be indistinguishable from a map this library does not hold."""
    held = {row[produced.NAME_COLUMN]: row for row in rows}
    for name in ("blue_orange", "atlas_grey"):
        assert held[name][produced.COUNT_COLUMN] == 0
        assert all(held[name][hue] == 0 for hue in produced.HUES)


def test_the_table_reads_the_pictures_and_not_the_maps_name(rows) -> None:
    """`Greens` makes green and `Reds` makes red — and `Blues` makes **azure**.

    The third one is the point. The wheel is twelve 30-degree spokes of Oklab hue
    angle and matplotlib's `Blues` sits on the azure spoke, so a table that agreed
    with the name here would be a table reading names. All three are read off the
    pictures the passes actually drew.
    """
    held = {row[produced.NAME_COLUMN]: row for row in rows}

    def leads(name: str) -> str:
        row = held[name]
        return max(produced.HUES, key=lambda hue: (row[hue], hue))

    assert leads("Greens") == "green"
    assert leads("Reds") == "red"
    assert leads("Blues") == "azure"


def test_a_name_carrying_a_comma_survives_the_round_trip(tmp_path) -> None:
    """`Gold Field, Blood Spark` is a map. A reader that split on the character
    would read it as two."""
    made = [
        {produced.NAME_COLUMN: "Gold Field, Blood Spark", produced.COUNT_COLUMN: 7}
        | {hue: index for index, hue in enumerate(produced.HUES)},
    ]
    produced.write(made, tmp_path)
    assert produced.read(tmp_path) == made


def test_a_table_with_a_column_missing_is_refused(tmp_path) -> None:
    """A dropped column would otherwise read back as a family nothing ever made."""
    path = produced.record_path(tmp_path)
    thin = f"{produced.NAME_COLUMN},{produced.COUNT_COLUMN}\nviridis,3\n"
    path.write_text(thin, encoding="utf-8")
    with pytest.raises(produced.ProducedError):
        produced.read(tmp_path)
