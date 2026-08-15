"""The rig: how a sheet is ordered, what it renders, and what may become a label.

The invariant that does not bend in either mode: **a suggestion is not a label**.
A sheet row carries no verdict, and the only thing that becomes one is what a
person exported from the page.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import sheets, store

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


def build(tmp_path, units, **kwargs):
    return sheets.build(
        units, directory=tmp_path / "sheet", batch="a_batch", renderer=stub, **kwargs
    )


def test_without_a_head_the_page_is_a_seeded_shuffle(tmp_path) -> None:
    """Not draw order: it arrives in blocks, and a block of one source's material
    drags the bar for as long as it lasts."""
    units = [unit(i) for i in range(20)]
    first = build(tmp_path, units, seed=3)
    second = sheets.build(
        units, directory=tmp_path / "again", batch="a_batch", seed=3, renderer=stub
    )
    assert first.manifest["order"] == "shuffle"
    assert [r["viewport"] for r in first.rows] == [r["viewport"] for r in second.rows]
    assert [r["viewport"] for r in first.rows] != [u["viewport"] for u in units]


def test_with_a_head_the_page_is_ordered_good_to_bad(tmp_path) -> None:
    units = [unit(i) for i in range(4)]
    head = Head({"0.0": 0.1, "0.1": 0.9, "0.2": 0.5, "0.3": 0.7})
    sheet = build(tmp_path, units, scorer=head)
    assert sheet.manifest["order"] == "score"
    assert [r["suggestion_score"] for r in sheet.rows] == [0.9, 0.7, 0.5, 0.1]


def test_the_unit_id_is_assigned_after_the_order_is_fixed(tmp_path) -> None:
    """So the id encodes the page position and nothing else — not the draw, not
    the score, not the fate."""
    sheet = build(tmp_path, [unit(i) for i in range(5)])
    assert [r["unit"] for r in sheet.rows] == ["u0001", "u0002", "u0003", "u0004", "u0005"]


def test_a_sheet_row_carries_no_verdict(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert "score" not in sheet.rows[0]
    assert sheet.rows[0]["suggestion"] is None


def test_both_companions_are_rendered_from_the_committed_library(tmp_path) -> None:
    sheet = build(tmp_path, [unit(0)])
    assert (sheet.directory / "canonical" / "u0001.png").exists()
    assert (sheet.directory / "vivid" / "u0001.png").exists()
    assert sheet.rows[0]["render"]["colormap"] == sheets.CANONICAL_COLORMAP
    assert sheet.rows[0]["judged_from"] == sheets.VIVID_COLORMAP


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


def test_only_exported_units_become_labels(tmp_path, store_dir, registered) -> None:
    """The whole point of correction mode's guard rail: three rows are served
    with suggestions, one is judged, and one label exists."""
    known = registered("a_batch")
    sheet = build(tmp_path, [unit(i) for i in range(3)])
    rows = sheets.record(sheet, {"u0002": {"score": 4, "revealed": 0}}, labeler="matt", known=known)
    assert len(rows) == 1
    assert store.resolved().summary()["scored"] == 1


def test_a_label_for_a_unit_not_on_the_sheet_is_refused(tmp_path, store_dir, registered) -> None:
    known = registered("a_batch")
    sheet = build(tmp_path, [unit(0)])
    with pytest.raises(sheets.SheetError, match="not on this sheet"):
        sheets.record(sheet, {"u9999": {"score": 3}}, labeler="matt", known=known)


def test_a_recorded_label_carries_the_whole_join(tmp_path, store_dir, registered) -> None:
    known = registered("a_batch")
    sheet = build(tmp_path, [unit(0)])
    rows = sheets.record(sheet, {"u0001": {"score": 3}}, labeler="matt", known=known)
    assert rows[0]["family"] == MANDELBROT
    assert rows[0]["viewport"] == sheet.rows[0]["viewport"]
    assert rows[0]["render"]["colormap"] == sheets.CANONICAL_COLORMAP


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
