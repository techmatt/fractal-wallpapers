"""The atlas maker's arithmetic: the thinning, the tone words, the `level` spelling.

All stub rows and no store, so every guard here is fast-lane arithmetic. What reads the
ledger, the pool scores and a record is `curate atlas` itself, and its output is checked by
the website's contract test on ingest rather than here.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation.atlas import population, slots

VIEW = {"center_re": "0", "center_im": "0", "width": "4"}
PLATE = (400, 200)


def place(name: str, x: float, y: float, p_fine: float, seated: bool = False):
    held = population.Place(population.MANDELBROT, name, x, y)
    held.offer(p_fine, f"key-{name}")
    held.fine_at_bar = 1
    if seated:
        held.seat = {"key": f"key-{name}"}
    return held


def test_a_seat_is_placed_before_a_better_unseated_neighbour_and_absorbs_it() -> None:
    seated = place("a", 0.0, 0.0, 0.1, seated=True)
    better = place("b", 0.05, 0.0, 0.9)  # 5 px away at 0.01 of plane per pixel
    dots, tally = population.thin([better, seated], VIEW, PLATE, 12.0)
    assert [dot.place.place for dot in dots] == ["a"]
    assert dots[0].dropped == 1
    assert tally == {
        "queued": 2,
        "dropped": 1,
        "dots": 1,
        "mandelbrot": 1,
        "julia": 0,
        "seated": 1,
    }


def test_a_place_outside_the_radius_stands_and_a_dot_is_drawn_where_the_plane_says() -> None:
    dots, _ = population.thin(
        [place("a", 0.0, 0.0, 0.5), place("b", 1.0, 0.5, 0.4)], VIEW, PLATE, 12.0
    )
    assert [(dot.px, dot.py) for dot in dots] == [(200.0, 100.0), (300.0, 50.0)]


def test_a_julia_place_is_its_c_and_a_mandelbrot_place_is_its_whole_key() -> None:
    julia = json.dumps(["julia:mandelbrot", 2, [["-0.75", "0.1"]], "0.3", "0.2", "0.05"])
    mandel = json.dumps(["mandelbrot", 2, [], "-0.5", "0.25", "0.001"])
    assert population.position(julia) == (population.JULIA, '["-0.75", "0.1"]', -0.75, 0.1)
    assert population.position(mandel) == (population.MANDELBROT, mandel, -0.5, 0.25)
    assert population.position("not json") is None


@pytest.mark.parametrize(
    ("value", "spelled"),
    [
        (0.0, "0"),
        (1.0, "1"),
        (-2.5, "-2.5"),
        (0.45, "0.45"),
        (1e-7, "1e-7"),
        (0.000001, "0.000001"),
        (1.5e-9, "1.5e-9"),
        (123456789012345680000.0, "123456789012345680000"),
        (1e21, "1e+21"),
        (0.06518683957762614, "0.06518683957762614"),
    ],
)
def test_a_number_is_spelled_the_way_javascript_spells_it(value, spelled) -> None:
    assert slots.js_number(value) == spelled


def ledger_row(picture: str, switch: str = "on") -> dict:
    return {
        "picture": picture,
        "recipe": {"colormap": "meloni", "autolevel": {"switch": switch}},
    }


CURVE = {
    "applies": True,
    "identity": False,
    "black_pt": 0.05,
    "white_pt": 0.98,
    "exponent": 1.25,
    "out_ends": [0.0, 1.0],
}


def test_a_recorded_curve_is_carried_in_the_permalinks_level_spelling() -> None:
    row = ledger_row("artifacts/curation/depth/night/pictures/k.jpg")
    tone = slots.tone_of(row, {"acted": True, "curve": CURVE})
    assert tone == {
        "tone": slots.CURVED,
        "level": "band_autolevel/v1:0.05,0.98,1.25,0,1",
        "gap": None,
        "from": "depth/night",
    }


def test_a_rotation_seat_says_its_curve_is_lost_rather_than_guessing_one() -> None:
    row = ledger_row("artifacts/curation/rotation/ckpt/pictures/k.jpg")
    tone = slots.tone_of(row, None)
    assert tone["tone"] == slots.LOST and tone["level"] is None
    assert "rotation run" in tone["gap"]
    assert slots.refusals(row["recipe"], {"meloni"}, set(), tone["tone"]) == [
        "autolevel band_autolevel/v1"
    ]


def test_an_operator_that_did_not_act_needs_no_level_and_refuses_nothing() -> None:
    row = ledger_row("artifacts/curation/depth/night/pictures/k.jpg")
    assert slots.tone_of(row, {"acted": False, "curve": CURVE})["tone"] == slots.CLEAN
    assert slots.tone_of(ledger_row("x", switch="off"), None)["tone"] == slots.CLEAN
    assert slots.refusals(row["recipe"], {"meloni"}, set(), slots.CLEAN) == []


def test_the_refusals_are_the_short_forms_the_website_checks() -> None:
    recipe = {"colormap": "gone", "palette": {"mirror": True}, "curve": "log"}
    assert slots.refusals(recipe, {"meloni"}, set(), None) == ["colormap gone", "curve log"]
    recipe = {"colormap": "meloni", "palette": {"mirror": True}}
    assert slots.refusals(recipe, {"meloni"}, {"meloni"}, None) == ["mirror on a cyclic map"]
