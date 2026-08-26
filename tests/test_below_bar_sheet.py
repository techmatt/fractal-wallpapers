"""The glance sheet of what an acting bar would take back.

Four claims. The page names exactly the rows the rejection pass names and no
others; it orders them good to bad; a ruling moves a row to its own section
rather than off the page; and an exclusion that names nothing refuses instead of
producing a sheet quietly one row short.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import below_bar, floors, records, rejection

HERE = {"kind": "mandelbrot"}
FRAME = {"center_re": "0", "center_im": "0", "width": "3"}

#: A strange score comfortably under the acting bar, and one comfortably over.
UNDER = floors.STRANGE_RELEASE_BAR.value - 0.2
OVER = floors.STRANGE_RELEASE_BAR.value + 0.2


@pytest.fixture(autouse=True)
def unbound():
    records.use(None)
    yield
    records.use(None)


def released(candidate: str, score: float, run: str = "whenever") -> dict:
    """One released strange row at a given score, with a picture to serve."""
    return records.decision(
        run=run,
        stage=records.RELEASE,
        candidate=candidate,
        verdict=records.RELEASED,
        row={
            "key": f"loc-{candidate}",
            "partition": "mandelbrot",
            "family": HERE,
            "viewport": FRAME,
            "head": "strange_render",
            "p_ge3": score,
        },
        picture=f"{candidate}.png",
    )


def test_the_page_holds_exactly_the_rows_the_rejection_pass_would_take() -> None:
    """One rule, read once. A sheet that re-derived the comparison could disagree
    with the pass it is the read for, and then neither could be trusted."""
    rows = [released("0000", UNDER), released("0001", OVER), released("0002", UNDER - 0.1)]
    cells = below_bar.condemned(rows)
    assert [cell["key"] for cell in cells] == [
        row["key"] for row, _ in rejection.below_acting_bar(rows)
    ]
    assert {cell["key"] for cell in cells} == {"whenever|release|0000", "whenever|release|0002"}


def test_the_rows_are_ordered_good_to_bad_and_carry_their_own_kind_s_floor() -> None:
    rows = [released(f"000{n}", UNDER - n / 100) for n in range(4)]
    cells = below_bar.condemned(rows)
    assert [cell["score"] for cell in cells] == sorted(
        (cell["score"] for cell in cells), reverse=True
    )
    assert {cell["floor"] for cell in cells} == {floors.STRANGE_RELEASE_BAR.value}
    assert all(cell["below_by"] > 0 for cell in cells)
    assert all(cell["kind"] == "strange_render" for cell in cells)


def test_a_ruled_row_leaves_the_count_and_keeps_a_place_on_the_page(monkeypatch) -> None:
    """The population is what a rejection pass would act on, so an excused row is
    not in it — and a reviewer who could not see the excused rows would read the
    page as the whole below-bar set, which it is not."""
    rows = [released("0000", UNDER), released("0001", UNDER - 0.1)]
    ruling = {
        "key": "whenever|release|0000",
        "ruled_by": "somebody",
        "date": "2026-01-01",
        "reason": "the picture is a wallpaper",
    }
    monkeypatch.setattr(rejection, "exceptions", lambda: {ruling["key"]: ruling})

    assert [cell["key"] for cell in below_bar.condemned(rows)] == ["whenever|release|0001"]
    held = below_bar.ruled(rows)
    assert [cell["key"] for cell in held] == ["whenever|release|0000"]
    assert held[0]["ruling"]["ruled_by"] == "somebody"

    page = below_bar.page(below_bar.condemned(rows), held, ["a line"])
    assert "whenever|release|0000" in page
    assert "held in service by somebody" in page


def test_an_exclusion_that_names_nothing_refuses(tmp_path) -> None:
    """A key that has moved would otherwise take a row off the sheet silently."""
    records.use(tmp_path)
    records.write_decisions(records.RELEASE, "whenever", [released("0000", UNDER)])
    with pytest.raises(ValueError, match="no such row is below an acting bar"):
        below_bar.write(tmp_path / "sheet.html", exclude=["whenever|release|9999"])


def test_the_sheet_is_one_self_contained_file_that_says_what_it_dropped(
    tmp_path, monkeypatch
) -> None:
    """It is copied out of the repository to be read, so a page pointing at files
    in an ignored tree would arrive empty — and a page that held twenty of
    twenty-one rows without saying so could not be checked against the store."""
    records.use(tmp_path)
    monkeypatch.setattr(below_bar.run_module, "run_dir", lambda run: tmp_path / run)
    records.write_decisions(
        records.RELEASE, "whenever", [released("0000", UNDER), released("0001", UNDER - 0.1)]
    )
    out = tmp_path / "sheet.html"
    report = below_bar.write(out, exclude=["whenever|release|0000"], reason="a stated call")

    assert report["below_bar"] == 2
    assert report["shown"] == 1
    assert report["no_picture_on_disk"] == ["whenever|release|0001"]
    page = out.read_text(encoding="utf-8")
    assert "whenever|release|0000" in page
    assert "a stated call" in page
    assert 'src="http' not in page and "<link" not in page
    # Written LF, on every platform: a sheet is copied and diffed like any other
    # text this repository writes.
    assert b"\r\n" not in out.read_bytes()


@pytest.mark.slow
def test_the_live_collection_sheet_names_the_rows_curate_reject_would_take() -> None:
    """Against the real record store: the sheet and the pass are one population."""
    rows = records.read_decisions(records.RELEASE)
    assert [cell["key"] for cell in below_bar.condemned(rows)] == [
        key
        for key, _ in sorted(
            (
                (str(row["key"]), records.live_reading(row)["p_ge3"])
                for row, _ in rejection.below_acting_bar(rows)
            ),
            key=lambda pair: (-pair[1], pair[0]),
        )
    ]
    # Every ruling in the tracked file that still names a served row is on the
    # page's second section, and none of them is in the first.
    held = {cell["key"] for cell in below_bar.ruled(rows)}
    assert held <= set(rejection.exceptions())
    assert not held & {cell["key"] for cell in below_bar.condemned(rows)}


def test_the_provenance_lines_carry_the_bar_and_the_exclusion() -> None:
    rows = [released("0000", UNDER)]
    cells = below_bar.condemned(rows)
    lines = below_bar.provenance(cells, [], {"whenever|release|0001"}, "because")
    joined = "\n".join(lines)
    assert json.dumps(floors.STRANGE_RELEASE_BAR.value) in joined or "0.62" in joined
    assert "whenever|release|0001" in joined and "because" in joined
    assert rejection.EXCEPTIONS_NAME in joined
