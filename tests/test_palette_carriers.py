"""The carrier table, and the pixel-cloud metric a twin is measured in.

The table is the answer to "which map can make a picture of which colour", and a
colour target is refused at launch against it. What is pinned here is that the
committed table says what it is supposed to say about the two maps the calibration
named, that it is keyed the way it has to be keyed, and that the metric beside it
is the same metric the palette grouping uses.
"""

from __future__ import annotations

import json

import numpy
import pytest

from fractal_wallpapers.palettes import carriers, dominance, groups, pixel_clouds


def header() -> dict:
    rows = carriers.read()
    assert rows[0]["kind"] == carriers.METHOD_ROW
    return rows[0]


def rows() -> list:
    return [row for row in carriers.read() if row.get("kind") == carriers.CARRIER_ROW]


# --------------------------------------------------------------------------- #
# What the committed table says.
# --------------------------------------------------------------------------- #
def test_the_two_maps_the_calibration_named_carry_their_cells() -> None:
    """`Green Vault` carries green and `Garnet Tide` carries rose, on this table.

    The pin, and it is the pin because these two are the strongest carriers of the
    two cells the ceiling was calibrated against — the ones a `--target` would
    draw first. A table that stopped saying this would be a table a green target
    could not be met out of, and nothing else in the pass would notice.
    """
    table = carriers.table()
    assert table["dark_vivid_green"]["Green Vault"] == pytest.approx(0.548, abs=0.01)
    assert table["dark_vivid_rose"]["Garnet Tide"] == pytest.approx(0.537, abs=0.01)
    assert next(iter(table["dark_vivid_green"])) == "Green Vault", "and it leads its cell"
    assert next(iter(table["dark_vivid_rose"])) == "Garnet Tide"


def test_a_carrier_row_holds_the_share_on_every_field_and_not_only_where_it_won() -> None:
    """`Garnet Tide` is barely rose on the strange field, and its row says so.

    0.765 and 0.681 of the colour on two fields and **0.165** on the third, which
    is over `CELL_ALONE` and so still a carrier there — by the second clause of
    the rule rather than by leading, since the strange field's largest cell is a
    green one. The mean the draw weights by is a mean over the three fields, and
    taken over the wins alone it would rank a map that carries once above one that
    nearly carries three times, which is the opposite of what a prior is for.
    """
    row = next(
        row for row in rows() if row["map"] == "Garnet Tide" and row["cell"] == "dark_vivid_rose"
    )
    assert row["share"]["strange"] < dominance.CELL_ALONE * 1.2
    assert row["share"]["smooth"] > 4 * row["share"]["strange"]
    assert row["mean"] == pytest.approx(sum(row["share"].values()) / 3, abs=1e-6)
    assert row["family"] == "rose"


def test_the_table_is_keyed_to_the_map_and_the_group_would_not_have_done() -> None:
    """Two members of one palette group, disagreeing about their colour.

    `twilight` and `twilight_shifted` are M1 0.0105 apart — well inside the cut,
    and correctly one group — and they are not pictures of the same colour. The
    grouping is order-free over a ramp's cloud; dominance is area-weighted over a
    picture, so a phase shift moves the areas without moving the cloud.
    """
    table = groups.member_groups()
    assert table["twilight"] == table["twilight_shifted"]
    mine = {row["cell"] for row in rows() if row["map"] == "twilight"}
    theirs = {row["cell"] for row in rows() if row["map"] == "twilight_shifted"}
    assert mine and theirs
    assert mine != theirs, "one row a group would have picked one of these and lost the other"


def test_every_map_in_the_library_was_read_and_every_cell_has_a_carrier() -> None:
    head = header()
    assert head["maps"] == len(groups.library())
    assert head["fields"] == ["smooth", "strange", "parameter_plane"]
    carried = {row["cell"] for row in rows()}
    assert carried == set(dominance.cells()), "48 cells, and a target may name any of them"


def test_the_record_never_lands_where_a_colormap_would_be_read() -> None:
    """Every reader of the library globs `data/palettes/*.json` and takes the stem."""
    assert carriers.record_path().suffix == ".jsonl"
    assert carriers.record_path().stem not in set(groups.library())


def test_the_rule_the_table_was_read_by_is_carried_in_the_file() -> None:
    """A reader of the record never has to find the module that made it."""
    assert header()["dominance"] == dominance.RULE
    assert str(dominance.CELL_LEAD) in header()["dominance"]
    assert str(dominance.CELL_ALONE) in header()["dominance"]


def test_the_committed_rows_are_what_this_code_would_write() -> None:
    """The header is a function of the rows, so the file cannot drift from itself."""
    head = header()
    assert head["carriers"] == len(rows())
    assert carriers.text_of([head]).endswith("\n")
    assert json.loads(carriers.text_of([head]).strip()) == head


# --------------------------------------------------------------------------- #
# The draw a target's carrier attempts are made from.
# --------------------------------------------------------------------------- #
def test_the_draw_is_weighted_seeded_and_without_replacement() -> None:
    picked = carriers.draw("dark_vivid_green", 5, seed=0)
    assert len(picked) == len(set(picked)) == 5
    assert picked == carriers.draw("dark_vivid_green", 5, seed=0), "the seed is the whole of it"
    assert picked != carriers.draw("dark_vivid_green", 5, seed=1)
    assert set(picked) <= set(dict(carriers.for_cell("dark_vivid_green")))


def test_a_draw_cannot_reach_a_map_the_pass_may_not_use() -> None:
    """`within` is the pass's collapsed pool: one member per palette group."""
    assert carriers.draw("dark_vivid_green", 5, seed=0, within=["Green Vault"]) == ["Green Vault"]
    assert carriers.draw("dark_vivid_green", 5, seed=0, within=["gray"]) == []


def test_asking_for_more_than_the_cell_has_gives_what_it_has() -> None:
    offers = carriers.for_cell("dark_vivid_lime")
    assert 0 < len(offers) < 400
    assert len(carriers.draw("dark_vivid_lime", 400, seed=0)) == len(offers)


# --------------------------------------------------------------------------- #
# The metric a twin is measured in.
# --------------------------------------------------------------------------- #
def test_the_pixel_cloud_metric_is_the_palette_metric_on_pixels() -> None:
    assert pixel_clouds.SAMPLES == groups.SAMPLES
    assert pixel_clouds.lattice().shape == (groups.DIRECTIONS, 3)
    width = groups.DIRECTIONS * groups.QUANTILES
    assert pixel_clouds.distance(numpy.zeros(width), numpy.full(width, 0.25)) == pytest.approx(0.25)
    assert pixel_clouds.distances(numpy.zeros(width), [numpy.full(width, 0.25)]) == [
        pytest.approx(0.25)
    ]


def test_the_subsample_is_seeded_so_two_readings_of_one_picture_agree() -> None:
    first = pixel_clouds.take(14400)
    assert len(first) == pixel_clouds.SAMPLES
    assert numpy.array_equal(first, pixel_clouds.take(14400))


def test_the_cache_keeps_what_is_held_and_forgets_what_is_merely_read() -> None:
    width = groups.DIRECTIONS * groups.QUANTILES
    del width
    store = pixel_clouds.Clouds(lambda name: None, cache=2)
    assert store.of("nothing") is None, "no picture, no cloud, and no crash"
    assert store.price()["signatures_made"] == 0


# --------------------------------------------------------------------------- #
# The marks the grouping's cut was read off, now that they are tracked.
# --------------------------------------------------------------------------- #
def test_the_cut_is_recomputable_from_the_marks_beside_it() -> None:
    assert groups.cut_from_marks() == groups.CUT
    assert len(groups.marks()) == 46


def test_the_marks_do_not_sort_cleanly_and_the_record_says_which_ones() -> None:
    """The cut splits two pairs Matt called the same, and merges none he called different.

    That is the one-sided rule the cut is read by, and it is the honest form of
    the claim: no height agrees with all forty-six marks, so the cut is chosen to
    never make the error that costs a wallpaper — merging two maps a person can
    tell apart — and pays for it by declining two merges a person would have made.
    """
    marks = groups.marks()
    same = [row for row in marks if row["mark"] == groups.SAME]
    different = [row for row in marks if row["mark"] == groups.DIFFERENT]
    assert not [row for row in different if row["m1"] < groups.CUT], "nothing wrongly merged"
    above = sorted(row["id"] for row in same if row["m1"] > groups.CUT)
    assert above == ["a02", "s06"], "and these two are the price"
    head = json.loads(groups.marks_path().read_text(encoding="utf-8").splitlines()[0])
    assert [row["id"] for row in head["same_above_the_cut"]] == above
    assert head["different_below_the_cut"] == []
    assert head["cut"] == groups.CUT


def test_the_grouping_record_points_at_its_own_evidence() -> None:
    head = json.loads(groups.record_path().read_text(encoding="utf-8").splitlines()[0])
    assert head["marks"] == groups.MARKS_RECORD_NAME
    assert groups.MARKS_RECORD_NAME in head["method"]
    assert groups.marks_path().is_file()


# --------------------------------------------------------------------------- #
# The read, held.
# --------------------------------------------------------------------------- #
def test_the_table_is_parsed_once_per_file_and_not_once_per_draw():
    """A draw reads the table, and a conditioned arm draws once per (location,
    mode). Re-parsing three quarters of a megabyte of JSONL at each of them put
    minutes of planning into an answer that never changed."""
    from fractal_wallpapers.palettes import carriers

    carriers.table()
    reads = 0
    real = carriers.read

    def counted(directory=None):
        nonlocal reads
        reads += 1
        return real(directory)

    carriers.read = counted
    try:
        for at in range(20):
            carriers.draw("dark_vivid_green", 4, at)
    finally:
        carriers.read = real
    assert reads == 0, f"{reads} re-parses over twenty draws of one cell"


def test_a_rebuilt_table_is_picked_up_rather_than_served_from_the_hold(tmp_path):
    """The cache is keyed on the file's own stamp, because `palettes carriers`
    rewrites the record in-process and a hold keyed on the path alone would go on
    answering out of the table it replaced."""
    from fractal_wallpapers.palettes import carriers

    header = carriers.method(maps=1, rows=1, seconds=0.0)
    first = {
        "schema": carriers.SCHEMA,
        "kind": carriers.CARRIER_ROW,
        "map": "one",
        "cell": "dark_vivid_green",
        "mean": 0.5,
        "fields": ["smooth"],
    }
    carriers.write([header, first], tmp_path)
    assert carriers.for_cell("dark_vivid_green", directory=tmp_path) == [("one", 0.5)]
    carriers.write([header, {**first, "map": "two", "mean": 0.25}], tmp_path)
    assert carriers.for_cell("dark_vivid_green", directory=tmp_path) == [("two", 0.25)]
