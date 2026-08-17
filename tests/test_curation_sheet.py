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
