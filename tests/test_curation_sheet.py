"""The release sheet, and the two things it got wrong on the first real run.

It could not rank the top end — every released smooth row sat at a `P(≥3)` of
0.9999 and that is the end a reviewer is looking at — and it captioned a missing
autolevel stamp with a cause nothing on the row had observed, which on the four
killed rows was simply false.
"""

from __future__ import annotations

from fractal_wallpapers.curation import sheet


# --------------------------------------------------------------------------- #
# the top end
# --------------------------------------------------------------------------- #
def test_the_top_cutpoint_orders_rows_the_third_one_cannot() -> None:
    """Two rows a saturated `P(≥3)` calls identical, told apart by `P(≥4)`."""
    one = {"head": "smooth_render", "p_ge3": 0.9999, "p_ge4": 0.0569}
    two = {"head": "smooth_render", "p_ge3": 0.9999, "p_ge4": 0.9780}
    assert sheet.top_end(one) != sheet.top_end(two)
    assert "0.0569" in sheet.top_end(one)
    assert "0.9780" in sheet.top_end(two)


def test_the_number_is_named_as_the_unconditional_one() -> None:
    """A raw cutpoint sigmoid read as a probability is a different, larger number,
    and it is the one CORN's conditional training makes meaningless on its own."""
    assert "unconditional" in sheet.top_end({"p_ge3": 0.9, "p_ge4": 0.4})


def test_a_judge_with_three_classes_says_so_rather_than_showing_a_blank() -> None:
    """The strange head has no fourth class. That is a fact about its scale, and
    a blank cell would read as a missing measurement."""
    line = sheet.top_end({"head": "strange_render", "p_ge3": 0.5098, "p_ge4": None})
    assert "not on this judge's scale" in line


def test_a_row_with_no_score_at_all_is_a_third_state() -> None:
    """A render that failed has a reason instead of a number, and reporting it as
    an absent scale would blame the head for a crash."""
    line = sheet.top_end({"head": "smooth_render", "p_ge3": None, "p_ge4": None})
    assert "no score" in line


# --------------------------------------------------------------------------- #
# the caption
# --------------------------------------------------------------------------- #
def test_a_missing_stamp_no_longer_claims_a_cause_it_did_not_observe() -> None:
    line = sheet.autolevel_line(None)
    assert "the switch was off" not in line
    assert "does not say why" in line


def test_the_one_cause_that_is_on_the_row_is_read_rather_than_guessed() -> None:
    """A direct trap is a trap figure over a flat ground: the operator genuinely
    does not touch it, and the row's own mode kind says so."""
    line = sheet.autolevel_line(None, kind="direct")
    assert "palette-indifferent" in line


def test_a_field_render_with_no_stamp_is_not_excused_by_its_kind(tmp_path) -> None:
    """This is the killed row. The operator applies to a field coloring, so a
    missing stamp there is unexplained and the caption has to leave it that way."""
    del tmp_path
    line = sheet.autolevel_line(None, kind="field")
    assert "palette-indifferent" not in line
    assert "does not say why" in line


def test_a_stamp_that_acted_still_says_what_it_did() -> None:
    stamp = {
        "acted": True,
        "curve": {
            "black_pt": 0.1,
            "white_pt": 0.9,
            "exponent": 1.2,
            "out_ends": [0.05, 0.95],
            "black_guarded": True,
        },
    }
    line = sheet.autolevel_line(stamp, "this picture — ", "field")
    assert line.startswith("this picture — autolevel: acted")
    assert "black end guarded" in line


def test_an_in_band_stamp_is_a_verdict_and_not_a_silence() -> None:
    line = sheet.autolevel_line({"acted": False, "curve": {"reason": "already in band"}})
    assert "in band, identity" in line
    assert "already in band" in line


# --------------------------------------------------------------------------- #
# the page
# --------------------------------------------------------------------------- #
def _row(**over) -> dict:
    row = {
        "candidate": "0086",
        "verdict": "released",
        "picture": None,
        "location": {"partition": "mandelbrot", "family": {}, "viewport": {}, "maxiter": 1},
        "recipe": {"mode": "smooth", "mode_kind": "field", "colormap": "x"},
        "scores": {"head": "smooth_render", "p_ge3": 0.0119, "p_ge4": 0.001, "location_p_ge3": 0.7},
        "palette": {"anchor": "a", "candidates": ["a"]},
        "autolevel": None,
        "release_autolevel": None,
    }
    row.update(over)
    return row


def test_a_released_card_carries_both_cutpoints_and_an_honest_caption(tmp_path) -> None:
    page = sheet.build("r", [_row()], [], [], {"requested": 1}, tmp_path, tmp_path / "s.html")
    text = page.read_text(encoding="utf-8")
    assert "P(≥4) 0.0010" in text
    assert "the switch was off" not in text
    assert "does not say why" in text


def test_a_released_row_captions_each_of_its_two_renders(tmp_path) -> None:
    """The candidate the verdict was cast on and the picture that shipped are two
    different renders, and showing one while captioning the other is how a sheet
    says something false with every field true."""
    row = _row(release_autolevel={"acted": False, "curve": {"reason": "in band"}})
    page = sheet.build("r", [row], [], [], {}, tmp_path, tmp_path / "s.html")
    text = page.read_text(encoding="utf-8")
    assert "this picture —" in text and "the render judged —" in text


# --------------------------------------------------------------------------- #
# the near-miss prefix
# --------------------------------------------------------------------------- #
def test_the_near_miss_section_is_not_handed_to_one_head_by_its_scale(tmp_path) -> None:
    """`from_records` takes a PREFIX of the passed-over rows, so an order that
    sorted both judges' probabilities together gave the whole section to whichever
    head's scale runs higher. Ranked on each head's own scale, the strange row is
    its partition's best and leads."""
    from fractal_wallpapers.curation import records
    from fractal_wallpapers.curation import sheet as sheet_module

    def passed(candidate: str, head: str, score: float) -> dict:
        return {
            **_row(),
            "candidate": candidate,
            "verdict": "passed_over",
            "reason": None,
            "picture": None,
            "scores": {"head": head, "p_ge3": score, "p_ge4": None, "location_p_ge3": 0.5},
        }

    rows = [
        passed("0001", "smooth_render", 0.9999),
        passed("0002", "smooth_render", 0.9998),
        passed("0003", "strange_render", 0.72),
    ]
    ordered = records.score_rank(rows)
    assert [row["candidate"] for row in ordered][:2] == ["0001", "0003"]

    page = sheet_module.from_records("r", rows, {}, tmp_path, tmp_path / "s.html")
    assert "Passed over (3)" in page.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# the score sheet
# --------------------------------------------------------------------------- #
def _scored(key: str, value) -> dict:
    return {"key": key, "p_fine": value}


def _fine(row: dict):
    return row["p_fine"]


def test_the_order_is_the_score_descending_and_an_unread_row_is_last() -> None:
    """A row the head has no reading for is a coverage fact, so it sorts to the
    tail rather than being dropped — the sheet that hid it hid the reading."""
    rows = [_scored("a", 0.2), _scored("b", None), _scored("c", 0.9)]
    assert [row["key"] for row in sheet.by_score(rows, _fine)] == ["c", "a", "b"]


def test_a_tie_breaks_on_the_key_so_the_same_pile_redraws_the_same_bytes() -> None:
    rows = [_scored("z", 0.5), _scored("a", 0.5)]
    assert [row["key"] for row in sheet.by_score(rows, _fine)] == ["a", "z"]


def test_a_row_falls_in_the_first_band_whose_floor_it_clears() -> None:
    rows = sheet.by_score([_scored("a", 0.90), _scored("b", 0.7499), _scored("c", 0.75)], _fine)
    bands = sheet.banded(rows, _fine)
    assert [(label, [row["key"] for row in held]) for label, held, _above in bands] == [
        ("0.90 and up", ["a"]),
        ("0.75 &ndash; 0.90", ["c"]),
        ("0.50 &ndash; 0.75", ["b"]),
    ]


def test_an_empty_band_is_left_out_and_above_counts_what_precedes_it() -> None:
    """The separator's number a reader wants is how much of the page is better
    than what follows, and a page of empty sections reads as a form."""
    rows = sheet.by_score([_scored("a", 0.95), _scored("b", 0.96), _scored("c", 0.05)], _fine)
    bands = sheet.banded(rows, _fine)
    assert [(label, len(held), above) for label, held, above in bands] == [
        ("0.90 and up", 2, 0),
        ("below 0.10", 1, 2),
    ]


def test_an_unread_row_bands_with_the_bottom_and_its_tile_says_so() -> None:
    rows = sheet.by_score([_scored("a", 0.95), _scored("b", None)], _fine)
    label, held, _above = sheet.banded(rows, _fine)[-1]
    assert label == "below 0.10" and [row["key"] for row in held] == ["b"]
    assert "&mdash;" in sheet.tile(None, [], score=None)


def test_a_caption_line_is_escaped_and_an_unknown_style_is_refused() -> None:
    """The caller names text, never markup — which is the whole of why this takes
    a style name out of a fixed vocabulary instead of an HTML string."""
    import pytest

    drawn = sheet.tile(None, ["<script>", ("mono", "a&b")], score=0.5, index=3)
    assert "&lt;script&gt;" in drawn and "a&amp;b" in drawn and "<script>" not in drawn
    assert '<div class="mono">' in drawn and "#3" in drawn
    with pytest.raises(ValueError, match="caption line's style"):
        sheet.tile(None, [("shouty", "no")])


def test_a_picture_this_machine_does_not_hold_draws_a_placeholder(tmp_path) -> None:
    """A sheet is read on whichever box has the store, and the tiers move."""
    assert "picture not on disk" in sheet.tile(tmp_path / "gone.jpg", ["x"], score=0.1)


def test_the_page_is_the_bands_in_order_with_one_tile_a_row(tmp_path) -> None:
    """Last night's leg sheet, in the shape it was hand-built in: rows carrying a
    score under the caller's own name, a caption the caller composed, ranks
    running 1..n over the whole page rather than restarting inside each band."""
    rows = [_scored("a", 0.95), _scored("b", 0.60), _scored("c", 0.61)]
    out = sheet.score_sheet(
        rows,
        score=_fine,
        lines=lambda row: [("strong", row["key"])],
        picture=lambda _row: None,
        title="a leg's clears",
        lede="<b>3</b> row(s)",
        output=tmp_path / "sheet.html",
    )
    page = out.read_text(encoding="utf-8")
    assert page.index("0.90 and up") < page.index("0.50 &ndash; 0.75")
    assert page.count("<figure>") == 3
    assert "#1" in page and "#3" in page
    assert "<b>3</b> row(s)" in page  # the lede is the caller's HTML and is not escaped
    assert "0.7500" not in page


def test_a_sheet_over_nothing_is_still_a_page(tmp_path) -> None:
    out = sheet.score_sheet(
        [],
        score=_fine,
        lines=lambda _row: [],
        picture=lambda _row: None,
        title="empty",
        lede="",
        output=tmp_path / "sheet.html",
    )
    assert "nothing to lay out" in out.read_text(encoding="utf-8")
