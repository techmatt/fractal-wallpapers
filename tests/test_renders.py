"""The render cache: what a row becomes on its way to being a picture.

The cache is the one place a recorded recipe turns back into pixels, so the
properties worth holding are all about that translation. A curve that composed
with the mode's own instead of replacing it, a trap setting that never reached
the engine, a file name that did not depend on the recipe — each produces
plausible pictures that are not the ones anybody judged.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import renders


def a_row(**changes) -> dict:
    row = {
        "schema": 1,
        "batch": "mode_sweep",
        "score": 2,
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.5", "center_im": "0.0", "width": "3.0"},
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": "twilight_shifted",
        "recipe": finished.recipe(),
        "render": {"resolution": [64, 36], "supersample": 1, "maxiter": 200},
        "_head": "strange_render",
    }
    row.update(changes)
    return row


def test_the_row_s_curve_replaces_the_mode_s_own() -> None:
    """`trap_circle` is the one mode with a curve of its own, so it is the one
    place a composed curve and a replacing one differ visibly."""
    assert renders.catalog()["trap_circle"]["transform"] == "log"
    straight = renders.coloring_of(a_row(mode="trap_circle", curve="linear"))
    assert straight["transform"] == "linear", "the mode's own curve survived"
    curved = renders.coloring_of(a_row(mode="trap_circle", curve="log"))
    assert curved["transform"] == "log"


def test_a_composite_s_curve_lands_on_its_base() -> None:
    coloring = renders.coloring_of(a_row(mode="smooth_stripe", curve="log"))
    assert coloring["kind"] == "composite"
    assert coloring["base"]["transform"] == "log"
    assert coloring["texture"]["transform"] == "linear", "the texture is a screen over the base"


def test_a_trap_s_own_settings_reach_the_engine() -> None:
    coloring = renders.coloring_of(
        a_row(mode="direct_trap_ring", mode_params={"opacity": 0.3, "threshold": 0.12})
    )
    assert coloring["kind"] == "direct"
    assert coloring["opacity"] == 0.3
    assert coloring["threshold"] == 0.12
    assert coloring["transform"] == "linear"


def test_a_setting_the_mode_does_not_take_is_refused() -> None:
    with pytest.raises(renders.RenderCacheError, match="takes no settings"):
        renders.coloring_of(a_row(mode="smooth", mode_params={"opacity": 0.3}))


JULIA = {"kind": "julia", "c": ["-0.8", "0.156"]}


def test_an_itinerary_row_carries_the_plane_s_own_address_start() -> None:
    """The one catalogued setting the family decides rather than the name.

    It has to be written into the spec rather than left to the engine, because the
    file name below is a digest of the spec: an address the engine opened after the
    digest would put two different pictures in one file.
    """
    over_c = renders.coloring_of(a_row(mode="itinerary"))
    assert "start" not in over_c["texture"]["field"], "a parameter plane has no wedge to remove"

    over_z = renders.coloring_of(a_row(mode="itinerary", family=JULIA))
    assert over_z["texture"]["field"]["start"] == "z1"
    assert over_z["base"] == over_c["base"], "only the address moved"


def test_the_plane_moves_only_the_itinerary_row_s_name() -> None:
    """Adopting `z₁` renamed the dynamical-plane `itinerary` pictures and nothing
    else: every other mode makes the same coloring on both planes, so the family is
    the only part of its name that changed."""
    for mode in renders.catalog():
        over_c = renders.coloring_of(a_row(mode=mode, mode_params=_settings(mode)))
        over_z = renders.coloring_of(a_row(mode=mode, family=JULIA, mode_params=_settings(mode)))
        assert (over_c == over_z) == (mode != "itinerary"), mode


def _settings(mode: str) -> dict:
    """The trap settings a direct-trap row carries; every other mode takes none."""
    return {"opacity": 0.3, "threshold": 0.12} if mode.startswith("direct_trap") else {}


def test_the_whole_recipe_reaches_the_spec() -> None:
    recipe = finished.recipe(
        gamma=0.5,
        cycles=3.0,
        phase=0.25,
        reverse=True,
        mirror=False,
        transfer={"kind": "edge", "weight": 0.25},
        rolloff={"kind": "soft_knee", "knee": 0.35},
    )
    spec = renders.spec_of(a_row(recipe=recipe), "out.jpg")
    assert spec["palette"] == {
        "gamma": 0.5,
        "cycles": 3.0,
        "phase": 0.25,
        "reverse": True,
        "mirror": False,
        "transfer": {"kind": "edge", "weight": 0.25},
        "rolloff": {"kind": "soft_knee", "knee": 0.35},
    }
    assert spec["maxiter"] == 200
    assert spec["colormap"] == "twilight_shifted"


def test_a_picture_s_name_depends_on_every_part_of_its_recipe() -> None:
    """Two rows that make the same picture share a file; anything else does not."""
    base = a_row()
    same = a_row(batch="rare_palette", score=3)
    assert renders.job_name(base) == renders.job_name(same), "a verdict changed the picture"

    for changed in (
        a_row(recipe=finished.recipe(gamma=0.9)),
        a_row(recipe=finished.recipe(phase=0.5)),
        a_row(recipe=finished.recipe(reverse=True)),
        a_row(recipe=finished.recipe(mirror=True)),
        a_row(recipe=finished.recipe(rolloff={"kind": "soft_knee", "knee": 0.35})),
        a_row(curve="log"),
        a_row(colormap="viridis"),
        a_row(mode="tia"),
        a_row(viewport={"center_re": "0.0", "center_im": "0.0", "width": "3.0"}),
        a_row(render={"resolution": [64, 36], "supersample": 2, "maxiter": 200}),
    ):
        assert renders.job_name(base) != renders.job_name(changed), changed


def test_the_evaluation_side_is_in_the_plan() -> None:
    """A held-out picture is scored through the same renderer the training side
    was learned from, or the number measures the render as much as the head."""
    for head in finished.HEADS:
        if not finished.registry_path(head).is_file():
            pytest.skip(f"the {head} store has not been imported on this machine")
        pinned = finished.pinned(head)
        jobs = renders.plan(head)
        places = {finished.place_of(job) for job in jobs}
        assert set(pinned) <= places, f"{head}: a pinned location is not in the plan"


def test_a_regenerated_picture_is_the_picture_that_was_judged() -> None:
    """The check that found the one defect the recipe transfer had.

    An edge-transfer floor two orders of magnitude too small left a third of the
    tonal range wrong on the 1,303 rows that use it and nothing wrong anywhere
    else — invisible to every other test here, because the pictures were still
    fractals and the head would still have trained on them.

    Skipped where the source project or a complete cache is absent: CI has
    neither, and a check that cannot read its input has not found a defect.
    """
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from pathlib import Path

    source = Path("C:/Code/fractal-maker")
    if not (source / "data").is_dir():
        pytest.skip("the source project is not on this machine")
    for head in finished.HEADS:
        if not renders.plan_path(head).is_file() or renders.missing(head):
            pytest.skip("the render cache is not complete on this machine")

    for head in finished.HEADS:
        report = renders.verify(source, head, sample=24)
        floor = report["recompression_floor"]["median"]
        assert report["delta"]["median"] <= floor, (
            f"{head}: the typical regenerated picture is further from the judged one "
            f"({report['delta']['median']:.2f}) than re-compressing it costs ({floor:.2f}). "
            f"Furthest: {report['furthest'][:2]}"
        )
        assert report["delta"]["max"] <= 4 * floor, (
            f"{head}: one regenerated picture is {report['delta']['max']:.2f} from the judged "
            f"one. Something in its recipe did not reach the engine: {report['furthest'][0]}"
        )
