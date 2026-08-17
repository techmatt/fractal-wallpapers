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
def test_the_two_judges_own_disjoint_modes_and_between_them_the_whole_roster() -> None:
    """The roster is the engine's own, so a mode cannot exist on one side of the
    boundary and not the other."""
    smooth = colorize.modes_for(budget.SMOOTH)
    strange = colorize.modes_for(budget.STRANGE)
    roster = set(engine.production_modes())
    assert smooth == [colorize.SMOOTH_MODE]
    assert not set(smooth) & set(strange)
    assert set(smooth) | set(strange) == roster


@needs_engine
def test_a_production_draw_can_never_yield_a_niche_mode() -> None:
    """The guard the tier rests on.

    A niche mode is a real mode — it resolves, it renders, its kind is known — and
    the *only* thing that is true of it is that no draw here can reach it. So the
    absence is asserted at the draw, and the presence everywhere else, because a
    tier that excluded a mode from the catalog outright would be a different and
    weaker claim.
    """
    catalog = {mode["name"]: mode for mode in engine.modes()}
    niche = {name for name, mode in catalog.items() if mode["tier"] == engine.NICHE}
    assert niche, "there is nothing to exclude, so this proves nothing"

    for head in (budget.SMOOTH, budget.STRANGE):
        drawn = colorize.modes_for(head)
        assert drawn, head
        assert not niche & set(drawn), f"{head} can draw {niche & set(drawn)}"

    # Still real modes: named in the catalog, resolvable, and kind-known.
    for name in niche:
        assert catalog[name]["coloring"]
        assert colorize.kind_of(name) in ("field", "composite", "modulate", "direct")


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


def test_an_attempt_killed_at_its_deadline_is_a_recorded_row_and_not_a_dead_run(
    monkeypatch, tmp_path
) -> None:
    """Every step that can fail is inside the try, the mode draw included: it
    reads the roster out of the engine, so it is an engine call like any other and
    a killed one would otherwise take the whole run down with it."""
    colorizer = object.__new__(colorize.Colorizer)
    colorizer.seed, colorizer.pool, colorizer.directory = 0, ["a"] * 40, tmp_path
    colorizer.cyclic, colorizer.band = set(), None

    def killed(_head):
        raise engine.EngineTimeout("engine modes was killed after 60.0s")

    monkeypatch.setattr(colorize, "modes_for", killed)
    monkeypatch.setattr(colorize, "candidate_set", lambda anchor, pool: ["a"])
    plan = budget.Attempt(head=budget.SMOOTH, partition="mandelbrot", key="k", rank=0)
    row = colorize.Colorizer.attempt(
        colorizer, plan, {"family": "mandelbrot", "viewport": {}, "maxiter": 500}, "a", 3
    )
    assert row["attempt"] == 3 and row["mode"] is None
    assert "EngineTimeout" in row["error"]
    assert row.get("p_ge3") is None, "a crash and a bad wallpaper are not the same number"
