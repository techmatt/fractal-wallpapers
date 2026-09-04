"""Colorize: the candidate set, the mode roster, and the anchors that spread a run."""

from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import budget, colorize, release
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
    """The roster is the engine's own less what the policy weights 0, so a mode
    cannot exist on one side of the boundary and not the other, and a mode nobody
    has ruled on cannot arrive by default."""
    from fractal_wallpapers.curation import mode_policy

    smooth = colorize.modes_for(budget.SMOOTH)
    strange = colorize.modes_for(budget.STRANGE)
    roster = set(mode_policy.accepted())
    assert smooth == [colorize.SMOOTH_MODE]
    assert not set(smooth) & set(strange)
    assert set(smooth) | set(strange) == roster
    assert roster < set(engine.production_modes()), "the policy takes something out"
    assert not roster & set(mode_policy.niche()), "and what it takes out is not drawn"


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


# --------------------------------------------------------------------------- #
# The field cache's identity.
# --------------------------------------------------------------------------- #
#: The colormap directory the names below are digested against, standing in for
#: this machine's. `spec_of` reads the real one as an absolute path, so a name
#: digested through it is a function of where the checkout happens to sit: the
#: same field is one name here and another on either CI runner. That directory is
#: a location rather than anything about the picture, so it is the one member
#: held still for these pins; every other member is left free to move the name.
DIGEST_COLORMAP_DIR = PurePosixPath("/pinned/data/palettes")

#: Three real places, and the names this project's derivation gives their fields.
#: Recorded rather than re-derived, because the whole property is that the
#: derivation may be rewritten and these must not move: `artifacts/curation/runs/
#: */fields/` is named by it, and a name that moved would re-dump every field this
#: project has ever paid for while the old ones sat beside them unread. They are
#: the derivation's output at [`DIGEST_COLORMAP_DIR`] rather than the literal file
#: names on any one disk, so a member renamed, added or dropped still moves them
#: and a `git clone` to a different directory does not.
SHIPPED_FIELD_NAMES = (
    (
        {"kind": "mandelbrot"},
        {"center_re": "-0.5", "center_im": "0.0", "width": "3.0"},
        3000,
        "daa28f5f490237ca",
    ),
    (
        {"kind": "multibrot", "degree": 3},
        {
            "center_re": "-0.11784803243926409",
            "center_im": "0.803838676554543",
            "width": "4.056617606305728e-05",
        },
        23409,
        "ebdf1212526126e3",
    ),
    (
        {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        8000,
        "4371b0b3100432b2",
    ),
)


@contextlib.contextmanager
def a_pinned_colormap_dir():
    """Hold `spec_of`'s one absolute path still, so a digest names the field
    rather than the checkout. Every name in this section goes through it — a
    perturbation compared against a pinned base while itself reading the real
    directory would differ for the wrong reason and pass whatever happened."""
    from fractal_wallpapers import engine_spec

    original = engine_spec.colormap_dir
    engine_spec.colormap_dir = lambda: DIGEST_COLORMAP_DIR
    try:
        yield
    finally:
        engine_spec.colormap_dir = original


def a_field_name(family, viewport, maxiter, changes=None) -> str:
    """One field's cache name, exactly as `colorize.field_of` asks for it."""
    from fractal_wallpapers.models import renders

    call = {
        "family": family,
        "viewport": viewport,
        "render": {
            "resolution": list(colorize.RESOLUTION),
            "supersample": colorize.SUPERSAMPLE,
            "maxiter": int(maxiter),
        },
        "mode": colorize.SMOOTH_MODE,
        "curve": colorize.CURVE,
    }
    with a_pinned_colormap_dir():
        return renders.field_job_name(**{**call, **(changes or {})})


def test_the_shipped_field_names_have_not_moved() -> None:
    """A field name is a digest of every field-side member, so this fails when
    one of them is renamed, added, dropped or given a different default — which
    is the whole reason to write the numbers down rather than derive them."""
    for family, viewport, maxiter, expected in SHIPPED_FIELD_NAMES:
        assert a_field_name(family, viewport, maxiter) == expected, family


def test_every_field_side_member_moves_the_field_name() -> None:
    """Declaring a member field-side is a claim that the field depends on it. A
    member that could be changed without moving the name would be one the cache
    is silently pooling over."""
    family, viewport, maxiter, base = SHIPPED_FIELD_NAMES[0]
    perturbed = {
        "family": {"kind": "multibrot", "degree": 3},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
        "render": {"resolution": [64, 36], "supersample": 2, "maxiter": 3000},
        "mode": "tia",
        "curve": "log",
    }
    from fractal_wallpapers.models import renders

    assert set(perturbed) | {"mode_params"} == set(renders.FIELD_IDENTITY), (
        "every declared field-side member needs a perturbation here, or the claim "
        "that it moves the name is untested"
    )
    for member, value in perturbed.items():
        assert a_field_name(family, viewport, maxiter, {member: value}) != base, member

    # `mode_params` only ever reaches a direct mode, so it is perturbed against a
    # base of its own rather than against the smooth field above.
    direct = {"mode": "direct_trap_ring", "curve": "linear"}
    assert a_field_name(family, viewport, maxiter, direct) != a_field_name(
        family, viewport, maxiter, {**direct, "mode_params": {"opacity": 0.9}}
    ), "mode_params"


def test_the_recolour_half_is_not_in_a_field_s_name() -> None:
    """A field is dumped once and recoloured thirty-two times. If the map were in
    the name, that would be thirty-two iteration passes instead of one."""
    from fractal_wallpapers.models import renders

    assert "colormap" in renders.RECOLOR_MEMBERS and "recipe" in renders.RECOLOR_MEMBERS
    assert "colormap" not in renders.FIELD_IDENTITY and "recipe" not in renders.FIELD_IDENTITY


# --------------------------------------------------------------------------- #
# One pick an attempt, the group filter on it, and the map a caller may name.
# --------------------------------------------------------------------------- #
def stub_colorizer(monkeypatch, tmp_path, made: list, names=None):
    """A colorizer whose renders and judgements are stated, so the wiring is what runs."""
    colorizer = object.__new__(colorize.Colorizer)
    colorizer.seed, colorizer.pool, colorizer.directory = 0, ["a"] * 40, tmp_path
    colorizer.cyclic, colorizer.band = set(), None
    colorizer.claimed, colorizer._groups = {}, {}
    names = names or [f"m{index}" for index in range(4)]
    monkeypatch.setattr(colorize, "candidate_set", lambda anchor, pool: list(names))
    monkeypatch.setattr(colorize, "modes_drawn_for", lambda plan, seed: ["smooth"])
    monkeypatch.setattr(colorize, "kind_of", lambda mode: "field")

    def render(row, mode, colormap, cyclic, output, **kwargs):
        del row, cyclic, kwargs
        made.append((str(output.name), mode, colormap))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"")
        return output, None

    monkeypatch.setattr(colorize, "render", render)
    monkeypatch.setattr(
        colorize.Colorizer, "score_picture", lambda self, picture: {"p_ge3": 0.9, "p_ge4": 0.8}
    )
    return colorizer


def location_row() -> dict:
    return {"family": "mandelbrot", "viewport": {}, "maxiter": 500}


def plan_for() -> budget.Attempt:
    return budget.Attempt(head=budget.SMOOTH, partition="mandelbrot", key="k", rank=0)


def test_an_attempt_is_one_picture_named_by_its_place_in_the_plan(monkeypatch, tmp_path) -> None:
    """The id IS the file name, and the file name is what resolves a row to a render."""
    made: list = []
    colorizer = stub_colorizer(monkeypatch, tmp_path, made)
    monkeypatch.setattr(
        colorize.Colorizer, "pick_palette", lambda self, row, names: ("m0", [1.0], None)
    )
    row = colorize.Colorizer.attempt(colorizer, plan_for(), location_row(), "a", 7)
    assert colorize.attempt_id(row) == "0007"
    assert row["picture"].endswith("0007.jpg")
    assert made == [("0007.jpg", "smooth", "m0")]
    assert "on_demand" not in row and "named" not in row and "group_skipped" not in row


def test_a_picture_the_seating_asked_for_is_named_apart_from_the_plan(
    monkeypatch, tmp_path
) -> None:
    """An on-demand render cannot collide with a plan index the next round adds."""
    made: list = []
    colorizer = stub_colorizer(monkeypatch, tmp_path, made)
    row = colorize.Colorizer.attempt(
        colorizer,
        plan_for(),
        location_row(),
        "a",
        7,
        colormap="Green Vault",
        on_demand=True,
        mode="exp_smoothing",
    )
    assert colorize.attempt_id(row) == "d0007"
    assert row["picture"].endswith("d0007.jpg")
    assert row["on_demand"] is True
    assert made == [("d0007.jpg", "exp_smoothing", "Green Vault")], "the mode was NOT re-drawn"


def test_a_named_map_bypasses_the_head_and_is_scored_like_anything_else(
    monkeypatch, tmp_path
) -> None:
    """The carrier attempt and the extra pick: the caller says which map."""
    made: list = []
    colorizer = stub_colorizer(monkeypatch, tmp_path, made)

    def refuse(self, row, names):
        raise AssertionError("a named map must not ask the palette head")

    monkeypatch.setattr(colorize.Colorizer, "pick_palette", refuse)
    row = colorize.Colorizer.attempt(
        colorizer, plan_for(), location_row(), "a", 7, colormap="Green Vault"
    )
    assert row["colormap"] == row["named"] == "Green Vault"
    assert row["candidate_scores"] == [], "the head was not asked, so it said nothing"
    assert row["p_ge3"] == 0.9, "and the judge still judged it"
    assert colorizer.claimed, "and the plan will not pick its group again"


def test_a_group_another_attempt_already_picked_is_passed_over(monkeypatch, tmp_path) -> None:
    """The proposal-time group cap: a pure identity filter, no pixels and no state."""
    colorizer = stub_colorizer(monkeypatch, tmp_path, [], names=["m0", "m1", "m2"])
    colorizer._groups = {"m0": "g1", "m1": "g1", "m2": "g2"}
    scores = [0.9, 0.8, 0.7]
    assert colorizer.unclaimed(["m0", "m1", "m2"], scores, "m0") == ("m0", None)
    colorizer.claim("m0")
    pick, skipped = colorizer.unclaimed(["m0", "m1", "m2"], scores, "m0")
    assert pick == "m2", "m1 is the same choice as m0 and the head's next is taken instead"
    assert [entry["map"] for entry in skipped["passed"]] == ["m0", "m1"]
    assert skipped["passed"][0]["taken_by"] == "m0"


def test_a_set_whose_every_group_is_taken_still_colours_its_attempt(monkeypatch, tmp_path) -> None:
    """The filter degrades rather than refusing: a plan trading a picture for a
    property would be a plan that renders less the longer it runs."""
    colorizer = stub_colorizer(monkeypatch, tmp_path, [], names=["m0", "m1"])
    colorizer._groups = {"m0": "g1", "m1": "g1"}
    colorizer.claim("m0")
    pick, skipped = colorizer.unclaimed(["m0", "m1"], [0.9, 0.8], "m0")
    assert pick == "m0", "the head's own pick stands"
    assert skipped["exhausted"] is True


# --------------------------------------------------------------------------- #
# The screen an extra pick is chosen by.
# --------------------------------------------------------------------------- #
def test_the_next_pick_is_the_best_ranked_map_carrying_a_colour_nothing_tried_was(
    monkeypatch,
) -> None:
    from fractal_wallpapers.palettes import dominance

    colour = {
        "one": ("red",),
        "two": ("red",),
        "three": ("blue",),
        "four": (),
        "five": ("green",),
    }
    monkeypatch.setattr(
        dominance,
        "of_picture",
        lambda picture: dominance.Reading((), colour[str(picture)], {}, {}, 0.0),
    )
    names = ["one", "two", "three", "four", "five"]
    scores = [0.9, 0.8, 0.7, 0.6, 0.5]

    def recolour_of(name):
        return name

    assert colorize.another_colour(names, scores, recolour_of, {"one"}, {"red"}) == "three"
    assert colorize.another_colour(
        names, scores, recolour_of, {"one", "three"}, {"red", "blue"}
    ) == ("five")
    assert (
        colorize.another_colour(names, scores, recolour_of, set(), {"red", "blue", "green"}) is None
    ), "no colour left to try, and nothing is rendered to find that out"


def test_a_named_map_needs_no_candidate_set_and_no_anchor_in_the_pool(
    monkeypatch, tmp_path
) -> None:
    """An on-demand pick inherits its anchor from whatever row it was asked beside.

    That row may come from another pass under another seed, whose collapsed pool
    stood a different member of a group up — so the anchor it names can be a map
    this pass cannot reach. Building a neighbourhood around it would refuse, and
    the neighbourhood is not wanted: the caller has already said which map.
    """
    made: list = []
    colorizer = stub_colorizer(monkeypatch, tmp_path, made)

    def refuse(anchor, pool, size=32):
        raise AssertionError("a named map must not build a candidate set")

    monkeypatch.setattr(colorize, "candidate_set", refuse)
    row = colorize.Colorizer.attempt(
        colorizer,
        plan_for(),
        location_row(),
        "a-map-this-pool-does-not-hold",
        7,
        colormap="Green Vault",
    )
    assert row["candidates"] == []
    assert row["colormap"] == "Green Vault"


# --------------------------------------------------------------------------- #
# One field, every palette: the two paths, and that they are one picture.
# --------------------------------------------------------------------------- #
#: Where the pixel-exactness pin is taken. One place per plane, both dear enough
#: that the two paths have arithmetic to disagree about and neither so dear that
#: the pin costs a minute.
EXACTNESS_PLACES = (
    {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": "-0.75", "center_im": "0.1", "width": "0.05"},
        "maxiter": 4000,
    },
    {
        "family": {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]},
        "viewport": {"center_re": "0.1", "center_im": "0.2", "width": "0.5"},
        "maxiter": 3000,
    },
)

#: One folded map and one cyclic one, so the recolour is held to reproducing the
#: render's **bake** as well as its arithmetic. A mirror applied on one path and
#: not the other is the failure this pair would catch and a single map would not.
EXACTNESS_MAPS = ("viridis", "twilight_shifted")

#: **The raster the two exactness pins below are taken on, and the one thing here
#: that is not production's own.** `colorize.RESOLUTION` at `SUPERSAMPLE` 2 is a
#: 1280x720 iteration pass a unit, and the two pins were 116.6 s and 29.5 s of a
#: 563 s slow lane on this machine, 2026-08-31 — a quarter of it, for a property
#: that does not read the raster.
#:
#: What is kept is everything the property is about: the supersample **and its
#: downsample**, because the shared path recolours a field dumped at the sampled
#: size and the two paths have to agree about the reduction as much as about the
#: arithmetic; every shareable mode; both planes; both bakes; the operator on.
#: What shrinks is the pixel count and the iteration cap, and neither is a term
#: in "these two paths produce the same file" — the same code runs on every pixel
#: either way, and a divergence in it is a divergence at any size.
#:
#: The honest cost: a rarer per-pixel disagreement has fewer pixels to show up
#: in. That is the trade, it is the only one taken here, and the full-size pin
#: still exists on the operator's side — `test_autolevel_identity` renders its
#: twenty-eight probes at production geometry and holds them to pinned digests.
EXACTNESS_GEOMETRY = {"resolution": [256, 144], "supersample": colorize.SUPERSAMPLE}


def exactness_geometry(row: dict, cap: int = 800) -> dict:
    """The cheap raster, carrying a capped iteration count off the row's own."""
    return {**EXACTNESS_GEOMETRY, "maxiter": min(int(row["maxiter"]), cap)}


def digest_of(path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def shareable_modes() -> list:
    return [mode for mode in engine.production_modes() if colorize.shareable(mode)]


@needs_engine
def test_the_shareable_roster_is_the_engine_s_field_colorings() -> None:
    """Which modes can share a field is the engine's answer and not a list here: a
    coloring that maps one scalar through the map has a field to dump and every
    other shape does not."""
    from fractal_wallpapers.models import renders

    catalog = renders.catalog()
    for mode in engine.production_modes():
        assert colorize.shareable(mode) == (catalog[mode]["kind"] == colorize.FIELD_KIND), mode
    assert shareable_modes(), "no production mode has a field, which cannot be true"


@needs_engine
@pytest.mark.slow
def test_a_recolour_is_the_render_byte_for_byte(tmp_path) -> None:
    """THE property leg one rests on. A recolour that were merely *close* would move
    every judge score in the ledger without moving anything a reader could see, so
    this is held to the file's bytes and not to the picture's look.

    Over every shareable mode, both planes and both bakes, with the autolevel
    operator on — which is where the two paths differ most, because on the shared
    path the operator's second pass is a recolour of the same field rather than a
    second iteration of it.

    Taken on [`EXACTNESS_GEOMETRY`] rather than on production's raster; that
    constant carries the measurement and the trade.
    """
    cyclic = colorize.cyclic()
    band = colorize.band()

    def both_paths(at: int, row: dict, mode: str) -> int:
        """Every map at one (place, mode), which is one unit of the render pool.

        The colormaps stay serial inside a unit because that is exactly what they
        share: the field cache is keyed on the family, the viewport, the geometry,
        the mode and the curve, and never on the map. Two threads at one
        (place, mode) would be two writers of one `.f32`.
        """
        geometry = exactness_geometry(row)
        for colormap in EXACTNESS_MAPS:
            plain = tmp_path / f"plain{at}-{mode}-{colormap}.jpg"
            shared = tmp_path / f"shared{at}-{mode}-{colormap}.jpg"
            _, plain_stamp = colorize.render(
                row,
                mode,
                colormap,
                cyclic,
                plain,
                render_geometry=geometry,
                level=True,
                band=band,
            )
            _, shared_stamp = colorize.render(
                row,
                mode,
                colormap,
                cyclic,
                shared,
                render_geometry=geometry,
                level=True,
                band=band,
                fields=tmp_path / "fields",
            )
            assert digest_of(plain) == digest_of(shared), f"{mode}/{colormap} at {at}"
            assert plain_stamp == shared_stamp, f"{mode}/{colormap} at {at}: the stamp"
        return len(EXACTNESS_MAPS)

    units = [
        (at, row, mode) for at, row in enumerate(EXACTNESS_PLACES) for mode in shareable_modes()
    ]
    with ThreadPoolExecutor(max_workers=release.DEFAULT_WORKERS) as pool:
        checked = sum(pool.map(lambda unit: both_paths(*unit), units))
    assert checked == len(EXACTNESS_PLACES) * len(shareable_modes()) * len(EXACTNESS_MAPS)


@needs_engine
@pytest.mark.slow
def test_a_coloring_with_no_field_is_served_by_the_render_path_without_being_asked(
    tmp_path,
) -> None:
    """The fallback is automatic. A composite, a modulate and a direct trap have no
    single scalar field; the caller offers the same field cache and gets the same
    picture, made the way it always was.

    On [`EXACTNESS_GEOMETRY`], for that constant's reason.
    """
    row = dict(EXACTNESS_PLACES[0])
    geometry = exactness_geometry(row)
    cyclic = colorize.cyclic()
    from fractal_wallpapers.models import renders

    catalog = renders.catalog()
    kinds = {catalog[mode]["kind"]: mode for mode in engine.production_modes()}
    unshareable = [mode for kind, mode in sorted(kinds.items()) if kind != colorize.FIELD_KIND]
    assert len(unshareable) == 3, f"the engine grew a shape: {sorted(kinds)}"
    fields = tmp_path / "fields"
    band = colorize.band()

    def both_paths(mode: str) -> None:
        plain = tmp_path / f"plain-{mode}.jpg"
        shared = tmp_path / f"shared-{mode}.jpg"
        colorize.render(
            row, mode, "viridis", cyclic, plain, render_geometry=geometry, level=True, band=band
        )
        colorize.render(
            row,
            mode,
            "viridis",
            cyclic,
            shared,
            render_geometry=geometry,
            level=True,
            band=band,
            fields=fields,
        )
        assert digest_of(plain) == digest_of(shared), mode

    # One mode a worker, at the pool's own width. Nothing is shared between them:
    # the whole subject here is modes the field cache never writes for.
    with ThreadPoolExecutor(max_workers=release.DEFAULT_WORKERS) as pool:
        list(pool.map(both_paths, unshareable))
    assert not list(fields.glob("*.f32")), "a dump was written for a coloring that has no field"


@needs_engine
@pytest.mark.slow
def test_one_location_and_mode_iterate_once_however_many_palettes_are_asked_for(
    tmp_path, monkeypatch
) -> None:
    """The saving, stated as the property that buys it: k palettes at one (location,
    mode) are one `dump-field` and k `recolor`s, and never a second iteration pass."""
    row = dict(EXACTNESS_PLACES[0])
    calls: list = []
    real = engine.run

    def counted(subcommand, spec=None, log=None):
        calls.append(subcommand)
        return real(subcommand, spec, log=log)

    monkeypatch.setattr(engine, "run", counted)
    maps = ["viridis", "magma", "twilight_shifted", "cividis"]
    for colormap in maps:
        colorize.render(
            row,
            "smooth",
            colormap,
            colorize.cyclic(),
            tmp_path / f"{colormap}.jpg",
            level=False,
            fields=tmp_path / "fields",
        )
    assert calls.count("dump-field") == 1
    assert calls.count("recolor") == len(maps)
    assert calls.count("render") == 0
    assert len(list((tmp_path / "fields").glob("*.f32"))) == 1


def test_a_field_is_dumped_from_the_spec_a_render_is_built_from() -> None:
    """A field dumped by mode *name* would carry the catalogue's own curve into its
    record, and `trap_circle`'s is a log where curation renders through a linear.
    Every later recolour would read the record's curve and make a picture nobody
    rendered, so the dump goes through `renders.spec_of` like everything else."""
    from fractal_wallpapers.models import renders

    row = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 500}
    spec = renders.spec_of(colorize.field_row(row, "trap_circle", colorize.CURVE), Path("x"))
    assert spec["coloring"]["transform"] == colorize.CURVE
    assert renders.catalog()["trap_circle"]["transform"] == "log", (
        "trap_circle stopped being the mode whose catalogued curve differs from "
        "curation's, so this test is pinning nothing — pick the one that does"
    )


def test_a_field_s_name_and_the_spec_it_is_dumped_from_are_one_derivation() -> None:
    """The cache name is a digest of what the engine is told, so the row the dump
    goes through has to be the row the name was taken over. Two derivations that
    agreed today would be one field under two names the day one of them moved."""
    from fractal_wallpapers.models import renders

    row = {
        "family": {"kind": "multibrot", "degree": 3},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
        "maxiter": 2500,
    }
    for mode in ("smooth", "tia", "trap_circle"):
        by_hand = renders.field_job_name(
            family=row["family"],
            viewport=row["viewport"],
            render={
                "resolution": list(colorize.RESOLUTION),
                "supersample": colorize.SUPERSAMPLE,
                "maxiter": row["maxiter"],
            },
            mode=mode,
            curve=colorize.CURVE,
        )
        assert renders.job_name(colorize.field_row(row, mode, colorize.CURVE)) == by_hand, mode


def test_a_mode_moves_a_field_s_name_so_two_modes_are_never_one_field() -> None:
    """`field_of` took the row's own mode when it used to be pinned to smooth. A name
    that did not move with it would serve a `tia` candidate a smooth field, which is
    a wrong picture rather than a slow one."""
    row = {"family": {"kind": "mandelbrot"}, "viewport": {}, "maxiter": 500}
    from fractal_wallpapers.models import renders

    names = {
        mode: renders.job_name(colorize.field_row(row, mode, colorize.CURVE))
        for mode in ("smooth", "tia", "stripe", "curvature")
    }
    assert len(set(names.values())) == len(names), names


def test_the_field_sweep_keeps_what_was_used_last_and_not_what_was_written_last(
    tmp_path,
) -> None:
    """A run spends forty palettes on one field, so *last written* is the wrong
    order: the field being spent is the oldest thing in the directory by the second
    palette. `field_of` touches on the way past and the sweep reads that."""
    import os

    directory = tmp_path / "fields"
    directory.mkdir()
    for index in range(6):
        (directory / f"f{index}.f32").write_bytes(b"x")
        (directory / f"f{index}.json").write_text("{}", encoding="utf-8")
        os.utime(directory / f"f{index}.f32", (1_700_000_000 + index, 1_700_000_000 + index))
    os.utime(directory / "f0.f32", None)
    assert colorize.sweep_fields(directory, keep=2) == 4
    left = sorted(path.stem for path in directory.glob("*.f32"))
    assert left == ["f0", "f5"], left
    assert sorted(path.stem for path in directory.glob("*.json")) == left, (
        "a field's record outlived the field it names"
    )


def test_the_palette_head_s_own_fields_are_not_swept(tmp_path) -> None:
    """They outlive the attempt that made them: a re-seat asks for another colour at
    a seat, and the gallery resolves a candidate recolour's NAME through one. A swept
    head field turns that lookup into an iteration pass, thousands of times."""
    import os

    directory = tmp_path / "fields"
    directory.mkdir()
    for index in range(6):
        (directory / f"f{index}.f32").write_bytes(b"x")
        (directory / f"f{index}.json").write_text("{}", encoding="utf-8")
        os.utime(directory / f"f{index}.f32", (1_700_000_000 + index, 1_700_000_000 + index))
    protect = {"f0.f32", "f1.f32"}
    assert colorize.sweep_fields(directory, keep=1, protect=protect) == 3
    left = sorted(path.name for path in directory.glob("*.f32"))
    assert left == ["f0.f32", "f1.f32", "f5.f32"], left


# --------------------------------------------------------------------------- #
# A roster entry is a mode and its settings.
# --------------------------------------------------------------------------- #
JULIA = {"kind": "julia", "degree": 4, "c": ["-0.8000969197766781", "0.07666925698290561"]}


def test_a_roster_entry_is_a_bare_mode_or_a_mode_with_its_settings() -> None:
    """The spelling, and that it round-trips.

    `@` and `,` rather than `:` because a roster entry is read beside partition
    names — `julia:multibrot4` — constantly, and one separator for two things is
    how a leg comes to be pointed at a partition it never meant.
    """
    assert colorize.roster_entry("smooth") == ("smooth", {})
    assert colorize.roster_entry("direct_trap_multiply@opacity=0.6,threshold=0.2") == (
        "direct_trap_multiply",
        {"opacity": 0.6, "threshold": 0.2},
    )
    assert colorize.roster_entry(" direct_trap_multiply@ opacity =0.4 ") == (
        "direct_trap_multiply",
        {"opacity": 0.4},
    )


def test_a_bare_mode_spells_as_itself_so_no_draw_already_taken_moves() -> None:
    """The property every seeded draw in the mining loop leans on.

    `spelled` is the key a palette draw and `mine.taken_maps` are per, and both
    used to be keyed on the bare mode. They still are wherever there are no
    settings — which is every row this project has ever written — so the change
    re-seeds nothing and re-keys nothing.
    """
    assert colorize.spelled("smooth") == "smooth"
    assert colorize.spelled("smooth", {}) == "smooth"
    assert colorize.spelled("smooth", None) == "smooth"
    # Sorted, so one pair has one spelling however the caller wrote it.
    assert colorize.spelled("direct_trap_multiply", {"threshold": 0.2, "opacity": 0.6}) == (
        "direct_trap_multiply@opacity=0.6,threshold=0.2"
    )
    assert colorize.spelled(
        "direct_trap_multiply", {"opacity": 0.6, "threshold": 0.2}
    ) == colorize.spelled("direct_trap_multiply", {"threshold": 0.2, "opacity": 0.6})


def test_the_settings_and_the_mode_round_trip_through_the_spelling() -> None:
    for mode, settings in [
        ("smooth", {}),
        ("direct_trap_multiply", {"opacity": 0.6}),
        ("direct_trap_multiply", {"opacity": 0.4, "threshold": 0.2}),
    ]:
        assert colorize.roster_entry(colorize.spelled(mode, settings)) == (mode, settings)


@pytest.mark.parametrize(
    "text",
    [
        "direct_trap_multiply@opacity",
        "direct_trap_multiply@=0.6",
        "direct_trap_multiply@opacity=wide",
        "direct_trap_multiply@opacity=0.6,opacity=0.4",
        "@opacity=0.6",
    ],
)
def test_a_roster_entry_that_is_not_a_mode_and_its_settings_is_refused(text) -> None:
    with pytest.raises(colorize.ColorizeError):
        colorize.roster_entry(text)


def test_a_setting_a_mode_does_not_take_is_refused_before_anything_renders() -> None:
    """At plan time, through the one owner of what a coloring takes.

    `renders.coloring_of` decides which settings a coloring has, and a second copy
    of that list here is how the two come to disagree. The value of asking early is
    the whole of it: a leg is three thousand candidates long, and a refusal on the
    first one is a leg that has to be started again.
    """
    assert colorize.check_roster(
        ["smooth", "direct_trap_multiply@opacity=0.6"], JULIA, log=_quiet
    ) == [
        ("smooth", {}),
        ("direct_trap_multiply", {"opacity": 0.6}),
    ]
    for bad in ["direct_trap_multiply@wibble=0.6", "smooth@opacity=0.6", "nosuchmode"]:
        with pytest.raises(colorize.ColorizeError):
            colorize.check_roster([bad], JULIA, log=_quiet)


def _quiet(*_args, **_kwargs) -> None:
    """A log that says nothing, so a check under test does not print."""


def test_a_render_row_carries_the_settings_into_the_coloring_block() -> None:
    """Which is what makes a varied candidate a NEW picture rather than an overwrite.

    `mode_params` is in `recipes.KEYED` and in `renders.SPEC_MEMBERS`, so it is in
    the recipe key and in the job name. The shipped constants that were not
    overridden survive — the variant moves `opacity` and keeps the catalogued
    `threshold` — which is the difference between a mode-param variant and an edit
    to the catalog.
    """
    row = {
        "family": JULIA,
        "viewport": {"center_re": "0", "center_im": "0", "width": "1"},
        "maxiter": 4000,
    }
    plain = colorize.render_row(
        row, "direct_trap_multiply", "twilight_shifted", {"twilight_shifted"}
    )
    varied = colorize.render_row(
        row,
        "direct_trap_multiply",
        "twilight_shifted",
        {"twilight_shifted"},
        mode_params={"opacity": 0.6},
    )
    assert plain["mode_params"] == {}
    assert varied["mode_params"] == {"opacity": 0.6}

    from fractal_wallpapers.models import renders

    assert renders.coloring_of(plain)["opacity"] == 0.2
    assert renders.coloring_of(varied)["opacity"] == 0.6
    assert renders.coloring_of(varied)["threshold"] == renders.coloring_of(plain)["threshold"]
    assert renders.job_name(plain) != renders.job_name(varied)


def test_a_candidate_carrying_settings_never_takes_the_shared_field(tmp_path) -> None:
    """`field_row` pins `mode_params` to `{}`, so a shared field cannot serve one.

    `renders.FIELD_IDENTITY` holds `mode_params` — a field's name is supposed to
    depend on the settings — but nothing has ever varied them, so the dump is
    written under the bare mode's name. A varied candidate served out of that
    cache would be a recolour of the shipped mode's field wearing the variant's
    name: the same failure `field_job_name` refuses at, arriving by a different
    door. So it takes the render path, where every direct trap already is.
    """
    row = {
        "family": JULIA,
        "viewport": {"center_re": "0", "center_im": "0", "width": "1"},
        "maxiter": 4000,
    }
    assert colorize._shared_field(row, "smooth", None, None) is None, "no cache offered"
    assert colorize._shared_field(row, "smooth", None, tmp_path, {"opacity": 0.6}) is None
    assert colorize._shared_field(row, "direct_trap_multiply", None, tmp_path) is None
