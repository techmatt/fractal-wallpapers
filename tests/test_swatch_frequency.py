"""Guard: the frequency sheet reports the census and never a second opinion of it.

The sheet exists to be ruled from — Matt reads it and then authors a colormap — so
what is worth pinning is not a number but the three ways a join like this goes
quietly wrong:

* a **swatch that dropped out**. The sheet's whole subject is the colours nothing
  is, and a row omitted because its count was zero would delete exactly the
  finding. All fifty-two appear or the sheet is answering a different question.
* a **colour recomputed rather than read**. The counts were taken under the
  codebook the census wrote into its own artifact; coordinates from anywhere else
  would put today's geometry beside yesterday's frequencies.
* the **order**. Descending by dominance is the falloff, and a tie broken by the
  alphabet would scatter a hue's four cells through the tail it is being read in.
"""

from __future__ import annotations

import csv

import pytest

from fractal_wallpapers.curation import swatch_frequency
from fractal_wallpapers.palettes import codebook

pytest.importorskip("numpy")


def readout(dominant: dict, carriage: dict | None = None, renders: int | None = None) -> dict:
    """A census readout holding only what the sheet joins."""
    swatches = {
        name: {"at_10pct": (carriage or {}).get(name, 0), "at_25pct": 0}
        for name in codebook.names()
    }
    return {
        "taken_at": "2026-01-01T00:00:00Z",
        "codebook": codebook.document(),
        "stages": {
            "library": {"metrics": {"swatches": swatches}, "pool_metrics": {"swatches": swatches}},
            "survival": {
                "pool": {
                    "renders": sum(dominant.values()) if renders is None else renders,
                    "dominant": dominant,
                }
            },
        },
    }


def test_every_swatch_gets_a_row_including_the_ones_nothing_is() -> None:
    """The sheet's subject is the holes. A swatch dropped for holding zero would be
    the one row the reader opened the file for."""
    table = swatch_frequency.rows(readout({"black": 10}))
    assert len(table) == 52
    assert {row["swatch"] for row in table} == set(codebook.names())
    assert table[0]["swatch"] == "black"
    assert all(row["dominant_renders"] == 0 for row in table[1:])


def test_the_order_is_dominance_then_the_codebook_rather_than_the_alphabet() -> None:
    """Ties are most of the tail. Alphabetical would scatter a hue's four cells
    through it; codebook order keeps them together."""
    table = swatch_frequency.rows(readout({"white": 5, "black": 5, "dark_vivid_red": 9}))
    assert [row["swatch"] for row in table[:3]] == ["dark_vivid_red", "black", "white"]
    assert [row["rank"] for row in table[:3]] == [1, 2, 3]
    order = codebook.names()
    tied = [row["swatch"] for row in table if row["dominant_renders"] == 0]
    assert tied == [name for name in order if name in set(tied)]


def test_the_colours_come_from_the_codebook_the_census_wrote() -> None:
    """Not from this module's import of it, which may have moved since."""
    document = codebook.document()
    document["swatches"][0] = {**document["swatches"][0], "srgb": [1, 2, 3]}
    built = readout({"black": 1})
    built["codebook"] = document

    lifted = {row["swatch"]: row for row in swatch_frequency.rows(built)}
    name = document["swatches"][0]["swatch"]
    assert lifted[name]["hex"] == "#010203"
    assert lifted[name]["srgb_r"] == 1
    # The live module still says otherwise, which is the whole point of reading
    # the persisted document rather than recomputing.
    assert codebook.swatches()[0]["srgb"] != [1, 2, 3]


def test_the_share_is_against_the_renders_the_census_counted() -> None:
    """Not against the tally's own sum: a dominant tally and a render count can
    differ, and dividing by the wrong one inflates every share on the page."""
    table = swatch_frequency.rows(readout({"black": 25}, renders=100))
    assert next(row for row in table if row["swatch"] == "black")["share_of_pool"] == 0.25


def test_a_readout_missing_a_stage_is_refused_rather_than_joined_to_zeroes() -> None:
    """A carried-forward artifact can hold three stages. Zeroes for the fourth
    would read as a library that carries nothing."""
    built = readout({"black": 1})
    del built["stages"]["library"]
    with pytest.raises(swatch_frequency.SheetError) as refusal:
        swatch_frequency.rows(built)
    assert "curate colors" in str(refusal.value)


def test_the_csv_round_trips_with_every_column_and_a_row_per_swatch(tmp_path) -> None:
    written = swatch_frequency.write_csv(
        swatch_frequency.rows(readout({"black": 3}, {"black": 7})), tmp_path / "sheet.csv"
    )
    read = list(csv.DictReader(written.read_text(encoding="utf-8").splitlines()))
    assert len(read) == 52
    assert list(read[0]) == list(swatch_frequency.COLUMNS)
    assert read[0]["swatch"] == "black" and read[0]["maps_at_10pct"] == "7"
    # LF whatever platform wrote it, like every other text file this repo makes.
    assert b"\r" not in written.read_bytes()


def test_the_page_fills_a_cell_with_the_swatch_itself(tmp_path) -> None:
    """The one thing the csv cannot do, and the reason the page exists at all."""
    table = swatch_frequency.rows(readout({"black": 1}))
    page = swatch_frequency.write_page(table, tmp_path / "sheet.html", 1, "2026-01-01T00:00:00Z")
    text = page.read_text(encoding="utf-8")
    for row in table:
        assert f"background:{row['hex']}" in text
