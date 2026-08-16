"""Colorize: the candidate set, the mode roster, and the anchors that spread a run."""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import budget, colorize
from fractal_wallpapers.palettes import space


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


@needs_engine
def test_the_two_judges_own_disjoint_modes_and_between_them_the_whole_catalog() -> None:
    """The roster is the engine's own, so a mode cannot exist on one side of the
    boundary and not the other."""
    smooth = colorize.modes_for(budget.SMOOTH)
    strange = colorize.modes_for(budget.STRANGE)
    catalog = {mode["name"] for mode in engine.modes()}
    assert smooth == [colorize.SMOOTH_MODE]
    assert not set(smooth) & set(strange)
    assert set(smooth) | set(strange) == catalog


@needs_engine
def test_a_modes_kind_comes_from_the_catalog() -> None:
    assert colorize.kind_of("smooth") == "field"
    assert colorize.kind_of("smooth_stripe") == "composite"
    assert colorize.kind_of("direct_trap_ring") == "direct"
    with pytest.raises(colorize.ColorizeError):
        colorize.kind_of("no_such_mode")


def test_the_candidate_set_is_a_neighbourhood_and_the_anchor_leads_it() -> None:
    members = sorted({path.stem for path in _pool_dir().glob("*.json")})[:80]
    anchor = members[10]
    names = colorize.candidate_set(anchor, members, size=8)
    assert names[0] == anchor
    assert len(names) == 8
    assert len(set(names)) == 8


def test_a_neighbourhood_is_tighter_than_a_uniform_draw_of_the_same_width() -> None:
    """This is the whole reason the set is a neighbourhood: the head was distilled
    on sets whose members look alike, and a loose set is an easier question."""
    members = sorted({path.stem for path in _pool_dir().glob("*.json")})[:120]
    near = colorize.candidate_set(members[30], members, size=12)
    spread = members[::10][:12]
    assert space.tightness(near)["mean"] < space.tightness(spread)["mean"]


def test_anchors_are_drawn_without_replacement_so_a_run_spreads() -> None:
    members = [f"map{index}" for index in range(20)]
    drawn = colorize.anchors(members, 20, seed=0)
    assert sorted(drawn) == sorted(members)


def test_asking_for_more_anchors_than_the_pool_holds_wraps_rather_than_refusing() -> None:
    """Two attempts sharing a region of palette space is a real state, not an error."""
    members = [f"map{index}" for index in range(4)]
    drawn = colorize.anchors(members, 6, seed=1)
    assert len(drawn) == 6
    assert set(drawn) == set(members)


def test_the_anchors_are_a_function_of_the_seed_alone() -> None:
    members = [f"map{index}" for index in range(30)]
    assert colorize.anchors(members, 10, seed=7) == colorize.anchors(members, 10, seed=7)
    assert colorize.anchors(members, 10, seed=7) != colorize.anchors(members, 10, seed=8)


def test_a_candidate_row_reads_its_fold_off_the_map_and_never_off_the_row() -> None:
    row = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 500}
    cyclic = {"twilight_shifted"}
    folded = colorize.render_row(row, "smooth", "viridis", cyclic)
    unfolded = colorize.render_row(row, "smooth", "twilight_shifted", cyclic)
    assert folded["recipe"]["mirror"] is True
    assert unfolded["recipe"]["mirror"] is False


def test_the_curve_is_the_identity_so_a_mode_keeps_its_own() -> None:
    """A curve set here would replace the mode's, which is a different picture from
    the one the judges were trained on."""
    assert colorize.CURVE == "linear"


def _pool_dir():
    from fractal_wallpapers.paths import colormap_dir

    return colormap_dir()
