"""The provenance record: what it claims, and what it is not allowed to claim.

The archive it is built from is a read-only source project that a clone does not
have, so the *building* is not what a test can check. What a test can check is
the shipped record: that every row names a map this repository holds, that the
authored rows carry a whole brief, and that the record never quietly becomes a
second gradient for the engine to disagree with.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.palettes import provenance
from fractal_wallpapers.paths import colormap_dir


@pytest.fixture(scope="module")
def rows() -> dict:
    record = provenance.read()
    assert record, f"{provenance.record_path()} is missing"
    return record


def test_every_row_names_a_map_this_repository_holds(rows) -> None:
    """The name is the join key. A row for a map nobody ships is provenance for
    a gradient that cannot be looked at."""
    held = {path.stem for path in colormap_dir().glob("*.json")}
    assert set(rows) <= held
    for name, row in rows.items():
        assert row["name"] == name
        assert row["schema"] == provenance.SCHEMA
        assert row["source"] in (provenance.AUTHORED, provenance.EXTRACTED)


def test_an_authored_row_carries_the_whole_brief(rows) -> None:
    """The brief is the reason the record exists: by the time a map is 512 sRGB8
    stops, the mood that produced it is gone. A row missing half of it would be a
    row that recorded the easy half."""
    authored = [row for row in rows.values() if row["source"] == provenance.AUTHORED]
    assert authored, "no authored rows at all"
    for row in authored:
        for key in (
            "mood_family",
            "complexity_band",
            "generator",
            "batch",
            "mood",
            "architecture",
            "skeleton",
            "value_key",
            "complexity",
        ):
            assert row.get(key) not in (None, ""), f"{row['name']} has no {key}"
        assert isinstance(row["complexity"], int)
        assert row["stops"], f"{row['name']} carries no authored stops"


def test_an_authored_gradient_closes_on_the_colour_it_opened_with(rows) -> None:
    """The authored stops are a closed loop — that is what lets the densifier bake
    them seam-free, and it is the one property the checker beside them calls an
    error. A record that had lost it would be recording a different palette."""
    for row in rows.values():
        if row["source"] != provenance.AUTHORED:
            continue
        first, last = row["stops"][0], row["stops"][-1]
        assert first["pos"] == 0.0 and last["pos"] == 1.0, row["name"]
        for one, other in zip(first["oklch"], last["oklch"], strict=True):
            assert abs(one - other) < 1.001, row["name"]


def test_an_extracted_row_records_its_picture_and_nothing_else(rows) -> None:
    """`source: extracted` with the image filename, and no brief: there was no
    brief. A mood on an extracted row would be somebody's reading of a picture
    written down as if it were a decision."""
    extracted = [row for row in rows.values() if row["source"] == provenance.EXTRACTED]
    assert extracted, "no extracted rows at all"
    for row in extracted:
        assert row["image"].startswith(row["name"])
        assert set(row) == {"schema", "name", "source", "image", "image_suffix_recovered"}


def test_the_record_is_not_a_second_densifier(rows) -> None:
    """The dense sRGB8 file is the render truth. An authored row's OKLCH stops are
    provenance — a handful of control points, not a gradient — and the two must not
    be confusable: nothing here should look like something the engine could bake."""
    for row in rows.values():
        if row["source"] != provenance.AUTHORED:
            continue
        assert len(row["stops"]) <= 15, f"{row['name']} carries a dense ramp, not control points"
        dense = json.loads((colormap_dir() / f"{row['name']}.json").read_text(encoding="utf-8"))
        assert len(dense["stops"]) > len(row["stops"])
        assert "oklch" not in json.dumps(dense)


def test_the_batch_name_is_where_the_run_knobs_come_from() -> None:
    """A map's mood family and generator version are facts about the *run*, and
    the batch file's name is how that run was written down."""
    assert provenance.batch_conditioning("fire-ice_c3-4_v3_1") == {
        "mood_family": "fire-ice",
        "complexity_band": "3-4",
        "generator": "3.1",
    }
    with pytest.raises(provenance.ProvenanceError):
        provenance.batch_conditioning("batch")


def test_the_record_never_lands_where_a_colormap_would_be_read() -> None:
    """Same rule the grouping follows: `data/palettes/*.json` is the map library,
    and a file in there that is not a map would be read as one."""
    assert provenance.record_path().suffix != ".json"
    assert provenance.record_path().stem not in {
        path.stem for path in colormap_dir().glob("*.json")
    }
