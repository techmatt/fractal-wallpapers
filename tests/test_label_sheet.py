"""The generator: two row sources, one cut, and what may become a label.

The invariant that does not bend in either mode or either source: **a suggestion
is not a label**. A sheet row carries no verdict, and the only thing that becomes
one is what a person exported from the page.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import intake, sheets, store

MANDELBROT = {"kind": "mandelbrot"}


def unit(index: int) -> dict:
    return {
        "family": MANDELBROT,
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "maxiter": 500,
    }


def stub(row, canonical, vivid, resolution, supersample):
    """A renderer that writes the two files and nothing else.

    Injected rather than mocked at the engine boundary: the sheet's job here is
    ordering, naming and recording, and holding the whole suite to a built
    release engine to test that would be a poor trade.
    """
    del row, resolution, supersample
    for path in (canonical, vivid):
        path.write_bytes(b"")
    return {"maxiter": 500}


class Head:
    """A scorer with an opinion, standing in for the head that will arrive."""

    name = "a_head"

    def __init__(self, scores):
        self.scores = scores

    def score(self, unit):
        return self.scores[unit["viewport"]["center_re"]]

    def admits(self, unit, score):
        return True


def build(tmp_path, units, scorer=None, seed=0, **kwargs):
    source = sheets.location_source(scorer=scorer, renderer=stub)
    return sheets.build(
        source,
        units,
        directory=tmp_path / "sheet",
        batch="a_batch",
        seed=seed,
        log=lambda _: None,
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# The location source.
# --------------------------------------------------------------------------- #
def test_without_a_head_the_page_is_a_seeded_shuffle(tmp_path) -> None:
    """Not draw order: it arrives in blocks, and a block of one source's material
    drags the bar for as long as it lasts."""
    units = [unit(i) for i in range(20)]
    first = build(tmp_path, units, seed=3)
    second = sheets.build(
        sheets.location_source(renderer=stub),
        units,
        directory=tmp_path / "again",
        batch="a_batch",
        seed=3,
        log=lambda _: None,
    )
    assert first.manifest["order"] == "shuffle"
    places = [row["join"]["viewport"] for row in first.rows]
    assert places == [row["join"]["viewport"] for row in second.rows]
    assert places != [u["viewport"] for u in units]


def test_with_a_head_the_page_is_ordered_good_to_bad(tmp_path) -> None:
    units = [unit(i) for i in range(4)]
    head = Head({"0.0": 0.1, "0.1": 0.9, "0.2": 0.5, "0.3": 0.7})
    sheet = build(tmp_path, units, scorer=head)
    assert sheet.manifest["order"] == "score"
    assert sheet.manifest["scorer"] == "a_head"
    assert [r["suggestion_score"] for r in sheet.rows] == [0.9, 0.7, 0.5, 0.1]


def test_the_unit_id_is_assigned_after_the_order_is_fixed(tmp_path) -> None:
    """So the id encodes the page position and nothing else — not the draw, not
    the score, not the fate."""
    sheet = build(tmp_path, [unit(i) for i in range(5)])
    assert [r["unit"] for r in sheet.rows] == ["u0001", "u0002", "u0003", "u0004", "u0005"]


def test_a_picture_is_named_for_the_build_so_re_ordering_costs_no_render(tmp_path) -> None:
    """The id moves when the order does; the file does not. That is what makes a
    long cut resumable."""
    head = Head({"0.0": 0.1, "0.1": 0.9})
    sheet = build(tmp_path, [unit(0), unit(1)], scorer=head)
    assert sheet.rows[0]["unit"] == "u0001"
    assert sheet.rows[0]["pictures"][0]["path"] == "vivid/0001.png"
    assert (sheet.directory / "vivid" / "0000.png").exists()
    assert (sheet.directory / "vivid" / "0001.png").exists()


def test_a_sheet_row_carries_no_verdict(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert "score" not in sheet.rows[0]
    assert sheet.rows[0]["suggestion"] is None


def test_both_companions_are_rendered_from_the_committed_library(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert (sheet.directory / "canonical" / "0000.png").exists()
    assert (sheet.directory / "vivid" / "0000.png").exists()
    assert sheet.rows[0]["join"]["render"]["colormap"] == sheets.CANONICAL_COLORMAP
    assert sheet.rows[0]["join"]["judged_from"] == sheets.VIVID_COLORMAP
    captions = [picture["caption"] for picture in sheet.rows[0]["pictures"]]
    assert captions == [
        f"judge from · {sheets.VIVID_COLORMAP}",
        f"stored against · {sheets.CANONICAL_COLORMAP}",
    ]


def test_a_colormap_outside_the_library_is_refused() -> None:
    with pytest.raises(sheets.SheetError, match="committed library"):
        sheets.colormap("a_map_that_was_never_committed")


def test_an_empty_sheet_is_refused(tmp_path) -> None:
    with pytest.raises(sheets.SheetError, match="nothing to judge"):
        build(tmp_path, [])


def test_a_sheet_reads_back_as_it_was_written(tmp_path) -> None:
    sheet = build(tmp_path, [unit(i) for i in range(3)])
    again = sheets.read(sheet.directory)
    assert again.manifest == sheet.manifest
    assert again.rows == sheet.rows


# --------------------------------------------------------------------------- #
# One shape, both sources.
# --------------------------------------------------------------------------- #
def test_a_sheet_hands_over_the_whole_join_its_store_keys_on(tmp_path) -> None:
    """The generator writes what the one ingest path reads, so the two cannot
    drift into two answers about what a sheet row is."""
    sheet = build(tmp_path, [unit(0)])
    read = intake.read_sheet(sheet.directory)
    assert read.head == sheets.LOCATION_HEAD
    assert set(intake.LOCATION_JOIN_KEYS) <= set(read.rows[0]["join"])


def test_the_manifest_says_which_source_cut_it_and_on_what_scale(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert sheet.manifest["kind"] == "location"
    assert sheet.manifest["head"] == sheets.LOCATION_HEAD
    assert sheet.manifest["tiers"] == list(store.SCORES)
    assert sheet.manifest["rubric"]


def test_a_finished_sheet_is_cast_on_the_same_scale_as_every_other(tmp_path) -> None:
    """Matt's decision: one scale, every head. The shipped strange judge still
    decodes to at most a 3, and that is the model's number, not the page's."""
    source = sheets.finished_source("strange_render", scores=([], 3))
    assert list(source.tiers) == [1, 2, 3, 4]
    assert source.head == "strange_render"


# --------------------------------------------------------------------------- #
# The populations.
# --------------------------------------------------------------------------- #
def test_units_come_off_a_walk_ledger_through_the_supply_reader(tmp_path) -> None:
    ledger = tmp_path / "walk.jsonl"
    rows = [
        {
            "schema": 1,
            "kind": "candidate",
            "fate": "survived",
            "score": 0.9,
            "family": MANDELBROT,
            "viewport": {"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
            "maxiter": 800,
        },
        {
            "schema": 1,
            "kind": "candidate",
            "fate": "interior_cap",
            "score": None,
            "family": MANDELBROT,
            "viewport": {"center_re": "0.2", "center_im": "0.0", "width": "1.0"},
        },
    ]
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    units = sheets.units_from_ledger(ledger)
    assert len(units) == 1
    assert units[0]["maxiter"] == 800


def test_units_come_off_a_stored_batch_at_its_current_verdict(store_dir, registered) -> None:
    known = registered("a_batch")
    store.append(
        [
            store.label_row(
                batch="a_batch",
                score=2,
                family=MANDELBROT,
                viewport={"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
                render={"maxiter": 900},
            )
        ],
        known=known,
    )
    units = sheets.units_from_batch("a_batch")
    assert len(units) == 1
    assert units[0]["maxiter"] == 900


def test_a_plan_unit_short_of_the_recipe_is_refused_before_a_pixel_is_rendered(tmp_path) -> None:
    """A finished render is a place AND how it was colored. Finding that out at
    the writer, one row at a time, is finding it out after the render bill."""
    plan = tmp_path / "plan.jsonl"
    plan.write_text(json.dumps({"family": MANDELBROT, "maxiter": 500}) + "\n", encoding="utf-8")
    with pytest.raises(sheets.SheetError, match="viewport, mode"):
        sheets.units_from_plan(plan)


def test_a_plan_reads_back_the_units_it_holds(tmp_path) -> None:
    plan = tmp_path / "plan.jsonl"
    written = {
        "family": MANDELBROT,
        "viewport": {"center_re": "0.1", "center_im": "0.0", "width": "1.0"},
        "mode": "threads",
        "maxiter": 800,
        "section": "promotion draw",
    }
    plan.write_text(json.dumps(written) + "\n", encoding="utf-8")
    assert sheets.units_from_plan(plan) == [written]
