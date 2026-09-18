"""A composite's texture weight as a per-candidate setting, and the draw that sets it.

The engine has always taken `texture_weight` on a composite; the catalog pins the
five screened ones at 0.85. `renders.coloring_of` is the one owner of which
settings a coloring takes, so the knob opens there, and `colorize.draw_texture_weights`
is the draw `curate hunt` and `curate depth` spend it through (`--texture-draw`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.cli import build_parser
from fractal_wallpapers.curation import colorize, recipes
from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import renders


def a_row(**changes) -> dict:
    row = {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.745", "center_im": "0.11", "width": "0.02"},
        "mode": "smooth_mean_angle",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": finished.recipe(),
        "render": {"resolution": [64, 36], "supersample": 1, "maxiter": 400},
    }
    row.update(changes)
    return row


def test_a_composite_takes_its_texture_weight_and_keeps_the_catalog_s_without_one() -> None:
    settled = renders.coloring_of(a_row())
    drawn = renders.coloring_of(a_row(mode_params={"texture_weight": 0.4}))
    assert settled["texture_weight"] == 0.85, "a bare row is the catalog's picture"
    assert drawn["texture_weight"] == 0.4
    assert {k: v for k, v in drawn.items() if k != "texture_weight"} == {
        k: v for k, v in settled.items() if k != "texture_weight"
    }, "only the weight moved"


def test_the_row_s_settings_are_not_spent_out_from_under_the_caller() -> None:
    row = a_row(mode_params={"texture_weight": 0.4})
    renders.coloring_of(row)
    assert row["mode_params"] == {"texture_weight": 0.4}


@pytest.mark.parametrize("weight", [-0.1, 1.2])
def test_a_weight_outside_the_unit_interval_is_refused(weight) -> None:
    with pytest.raises(renders.RenderCacheError, match="outside"):
        renders.coloring_of(a_row(mode_params={"texture_weight": weight}))


@pytest.mark.parametrize("mode", ["smooth", "direct_trap_ring", "itinerary"])
def test_a_mode_with_no_texture_to_weigh_refuses_the_weight(mode) -> None:
    with pytest.raises(renders.RenderCacheError):
        renders.coloring_of(a_row(mode=mode, mode_params={"texture_weight": 0.4}))


def test_a_drawn_weight_is_a_new_recipe_key() -> None:
    assert "mode_params" in recipes.KEYED
    assert renders.job_name(a_row(mode_params={"texture_weight": 0.4})) != renders.job_name(a_row())


def test_the_engine_draws_a_different_picture_at_a_different_weight(tmp_path) -> None:
    try:
        engine.engine_path()
    except FileNotFoundError:
        pytest.skip("no engine built")
    pictures = []
    for weight in (0.3, 0.9):
        output = tmp_path / f"w{weight}.png"
        report = engine.run(
            "render",
            renders.spec_of(a_row(mode_params={"texture_weight": weight}), output),
        )
        assert report["coloring"]["texture_weight"] == weight
        pictures.append(output.read_bytes())
    assert pictures[0] != pictures[1]


@dataclass(frozen=True)
class Shot:
    mode: str
    mode_params: dict = field(default_factory=dict)


ROSTER = ["smooth_mean_angle", "smooth_angle_min", "smooth_stripe", "threads", "smooth", "tia"]


def test_only_screened_composites_are_drawn_and_every_draw_is_in_the_span() -> None:
    shots = [Shot(mode) for mode in ROSTER * 20]
    out, tally = colorize.draw_texture_weights(shots, (0.3, 0.9), 7, log=lambda *_: None)
    assert len(out) == len(shots)
    assert tally["texture_drawn"] == 60 and tally["not_screened"] == 60
    for before, after in zip(shots, out, strict=True):
        if before.mode in ROSTER[:3]:
            weight = after.mode_params["texture_weight"]
            assert 0.3 <= weight <= 0.9
            assert weight == round(weight, colorize.TEXTURE_PLACES)
        else:
            assert after is before, "threads adds rather than screens; the rest have no texture"


def test_the_draw_is_seeded_and_keeps_settings_already_carried() -> None:
    shots = [Shot("smooth_stripe", {"other": 1.0}) for _ in range(12)]
    first, _ = colorize.draw_texture_weights(shots, (0.3, 0.9), 11, log=lambda *_: None)
    again, _ = colorize.draw_texture_weights(shots, (0.3, 0.9), 11, log=lambda *_: None)
    other, _ = colorize.draw_texture_weights(shots, (0.3, 0.9), 12, log=lambda *_: None)
    assert first == again
    assert first != other
    assert all(shot.mode_params["other"] == 1.0 for shot in first)
    assert len({shot.mode_params["texture_weight"] for shot in first}) > 1, "one draw a shot"


@pytest.mark.parametrize("span", [(0.9, 0.3), (-0.1, 0.5), (0.5, 1.5)])
def test_a_span_that_is_not_inside_the_unit_interval_is_refused(span) -> None:
    with pytest.raises(colorize.ColorizeError):
        colorize.draw_texture_weights([], span, 0, log=lambda *_: None)


@pytest.mark.parametrize(
    "argv",
    [
        ["curate", "hunt", "run", "--name", "x", "--texture-draw", "0.3", "0.9"],
        ["curate", "hunt", "plan", "--name", "x", "--texture-draw", "0.3", "0.9"],
        ["curate", "depth", "run", "--name", "x", "--texture-draw", "0.3", "0.9"],
        ["curate", "depth", "plan", "--name", "x", "--texture-draw", "0.3", "0.9"],
    ],
)
def test_both_verbs_take_the_span(argv) -> None:
    assert build_parser().parse_args(argv).texture_draw == [0.3, 0.9]
