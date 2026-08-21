"""The deep run mode: the floor, the band, the ladder, and the clock.

Four of these are about arithmetic and run in milliseconds. Two are **smoke
tests against the real engine** — the mirror of its `f64` refusal, and a real
deep frame drawn at release geometry — because a mirror that is only checked
against itself is a comment, and the whole of this mode rests on the engine
still drawing what the mirror says it will.
"""

from __future__ import annotations

import random

import mpmath as mp
import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import pacing
from fractal_wallpapers.deep import centers, depth, roots
from fractal_wallpapers.deep import run as deep_run
from fractal_wallpapers.discovery import nucleus as nuc
from fractal_wallpapers.discovery import walk as walk_module


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

#: A real degree-2 nucleus deep enough to be a seat, and the seed that reaches
#: it. Seahorse valley, which is where every published deep Mandelbrot anchor in
#: this project's history has come from.
SEAHORSE = (-0.7453, 0.1127)
SEAHORSE_PERIOD = 61


# --------------------------------------------------------------------------- #
# The floor, the band, and the window they imply.
# --------------------------------------------------------------------------- #
def test_the_deep_floor_is_two_decades_below_the_shallow_one_and_shallow_is_untouched() -> None:
    assert pytest.approx(depth.SHALLOW_MIN_WIDTH / 100.0) == depth.MIN_WIDTH
    # The shallow walk's own default is read, not restated, so this fails the
    # day somebody moves it rather than agreeing with a stale copy.
    assert walk_module.Gates().min_width == 1e-9
    assert deep_run.gates().min_width == depth.MIN_WIDTH


def test_the_seat_window_is_exactly_the_two_floors_read_through_the_band() -> None:
    low, high = depth.SEAT_SIZES
    # An atom at the bottom of the window has its band floor exactly on this
    # mode's floor; one at the top has its money shot exactly on the shallow one.
    assert depth.band(low)[1] == pytest.approx(depth.MIN_WIDTH)
    assert depth.money_shot(high) == pytest.approx(depth.SHALLOW_MIN_WIDTH)
    assert depth.seats_this_size(low) and depth.seats_this_size(high)
    assert not depth.seats_this_size(low * 0.9)
    assert not depth.seats_this_size(high * 1.1)


def test_a_seat_is_deep_by_construction_and_not_by_how_far_a_walk_descended() -> None:
    # Every framing a seat contributes is at or below the shallow floor, so the
    # very first frame this mode draws is one the shallow walk cannot reach.
    _low, high = depth.SEAT_SIZES
    for framing in depth.ROOT_FRAMINGS:
        if framing == depth.BAND_TOP:
            continue
        assert framing * high <= depth.SHALLOW_MIN_WIDTH


def test_the_bands_tile_the_window_and_nothing_outside_it_is_in_one() -> None:
    bands = depth.bands()
    assert [name for name, _low, _high in bands] == list(depth.BAND_NAMES)
    # Edge to edge with no gap and no overlap, floor to the shallow floor.
    assert bands[0][1] == depth.MIN_WIDTH
    assert bands[-1][2] == depth.SHALLOW_MIN_WIDTH
    for lower, upper in zip(bands, bands[1:], strict=False):
        assert lower[2] == pytest.approx(upper[1])
        assert depth.band_of(lower[2]) == upper[0]
    # A frame the shallow walk could reach and one under this mode's floor are
    # both outside every band rather than folded into the nearest one — the deep
    # mode draws the first (a seat's widest root framing is forty atom sizes) and
    # a count of the bands has to be a count of the deep frames.
    assert depth.band_of(depth.SHALLOW_MIN_WIDTH) is None
    assert depth.band_of(depth.MIN_WIDTH * 0.9) is None
    assert depth.band_of(depth.MIN_WIDTH) == depth.BAND_NAMES[0]


def test_a_band_ceiling_is_the_atom_whose_money_shot_lands_on_that_band_s_top() -> None:
    for name, _low, high in depth.bands():
        size = depth.band_ceiling(name)
        assert depth.money_shot(size) == pytest.approx(high)
        # The widest band's ceiling is the whole window's, so aiming at it is the
        # same as not aiming — which is what makes the ceiling a narrowing of one
        # rule rather than a second one.
        if name == depth.BAND_NAMES[-1]:
            assert size == pytest.approx(depth.SEAT_SIZES[1])


def test_a_seat_carries_the_band_of_the_frame_it_is_for() -> None:
    # Framings are widest first, so the band is read off the money shot and not
    # off the neighbourhood view above it.
    seat = roots.Seat(
        channel=roots.NEWTON,
        family={"kind": "mandelbrot"},
        center=None,
        framings=[
            {"center_re": "0", "center_im": "0", "width": "4e-10"},
            {"center_re": "0", "center_im": "0", "width": "4e-11"},
        ],
        provenance={},
    )
    assert seat.band == "floor"
    assert seat.record()["band"] == "floor"


# --------------------------------------------------------------------------- #
# The `f64` wall: the mirror, against the engine that owns it.
# --------------------------------------------------------------------------- #
def test_the_ulp_reading_is_the_arithmetic_and_not_a_constant() -> None:
    # Same width, same geometry, four times the coordinate magnitude: a quarter
    # of the headroom. An absolute rule cannot tell these apart.
    near = depth.resolution_ulps("0.2", "0.0", 6e-12, 2560, 4)
    far = depth.resolution_ulps("1.6", "0.0", 6e-12, 2560, 4)
    assert near == pytest.approx(8 * far, rel=0.02)
    assert depth.releasable("0.2", "0.0", 6e-12)
    assert not depth.releasable("1.6", "0.0", 6e-12)


@needs_engine
def test_the_mirror_and_the_engine_refuse_the_same_frames(tmp_path) -> None:
    """The one check that keeps `depth` from being a comment about `viewport.rs`.

    Bisected rather than sampled: the engine's boundary is found by asking it,
    and the mirror's is computed, and the two are required to be the same width
    to within the bisection's own resolution. Sixteen-pixel renders, so the
    whole thing costs a second.
    """

    def engine_draws(center_re: str, width: float) -> bool:
        spec = {
            "schema": 1,
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": center_re, "center_im": "0.0", "width": f"{width:.17e}"},
            "resolution": [16, 9],
            "supersample": 1,
            "maxiter": 32,
            "mode": "smooth",
            "colormap": "twilight_shifted",
            "colormap_dir": str(engine.colormap_dir()),
            "output": str(tmp_path / "probe.jpg"),
        }
        try:
            engine.render_report(spec)
        except RuntimeError as refusal:
            assert "unit of last place" in str(refusal)
            return False
        return True

    for center_re in ("0.25", "0.75", "1.5"):
        low, high = 1e-18, 1e-8
        for _ in range(60):
            probe = (low * high) ** 0.5
            if engine_draws(center_re, probe):
                high = probe
            else:
                low = probe
        mirrored = depth.resolution_ulps(center_re, "0.0", high, 16, 1)
        assert mirrored == pytest.approx(depth.RESOLUTION_ULPS, rel=1e-6)


@needs_engine
def test_the_engine_draws_a_frame_at_this_mode_s_floor_at_release_geometry(tmp_path) -> None:
    """The claim the whole mode rests on, asked of the thing that answers it.

    Not a picture check — a *refusal* check. Sixteen output pixels at the
    release supersample, which is the same sample spacing a 2560-wide release
    frame has and none of its cost.
    """
    center = "-0.74451152313168325131752900466643145"
    assert depth.releasable(center, "0.11256397475728084066996181415568268", depth.MIN_WIDTH)
    spec = {
        "schema": 1,
        "family": {"kind": "mandelbrot"},
        "viewport": {
            "center_re": center,
            "center_im": "0.11256397475728084066996181415568268",
            # Sixteen pixels at supersample 4 has the sample spacing a 2560-wide
            # frame at the floor does, scaled down with the frame.
            "width": f"{depth.MIN_WIDTH * 16 / 2560:.17e}",
        },
        "resolution": [16, 9],
        "supersample": 4,
        "maxiter": 512,
        "mode": "smooth",
        "colormap": "twilight_shifted",
        "colormap_dir": str(engine.colormap_dir()),
        "output": str(tmp_path / "floor.jpg"),
    }
    assert engine.render_report(spec)["output"]


# --------------------------------------------------------------------------- #
# The centers: precision sized by the answer, coordinates as strings.
# --------------------------------------------------------------------------- #
def test_a_deep_center_is_decimal_strings_with_digits_for_its_own_frame() -> None:
    found = centers.solve(mp.mpc(*SEAHORSE), SEAHORSE_PERIOD)
    assert isinstance(found.center_re, str) and isinstance(found.center_im, str)
    # Far more digits than `f64` can hold, which is the point: the string is the
    # identity and the `f64` view of it is made fresh at every render.
    assert len(found.center_re.replace("-", "").replace(".", "").lstrip("0")) >= 30
    assert found.center_re != repr(float(found.center_re))
    assert depth.seats_this_size(found.size)
    assert found.band[0] > found.money_shot > found.band[1]


def test_the_precision_a_solve_runs_at_is_raised_to_what_the_atom_asks_for(monkeypatch) -> None:
    """The computed-and-ignored figure, acted on.

    `Atom.required_dps` first exceeds the shallow 60 at `log10|A| > 45`, which is
    thirty decades below anything this mode frames — so the enforcement cannot be
    shown by finding a deep enough atom. It is shown by starting *below* the
    requirement and watching the solve climb to it: a width of 1e0 sizes the
    working precision at the 60-digit floor, and the atom then asks for more.
    """
    shallow_start = centers.working_dps(1.0)
    assert shallow_start == nuc.NUCLEUS_DPS

    real = nuc.atom_instrument

    def demanding(c, period, degree=2, **kwargs):
        atom = real(c, period, degree, **kwargs)
        # What an atom thirty decades smaller than anything here would ask for.
        atom.required_dps = 140
        return atom

    monkeypatch.setattr(nuc, "atom_instrument", demanding)
    found = centers.solve(mp.mpc(*SEAHORSE), SEAHORSE_PERIOD, width=1.0)
    monkeypatch.undo()
    assert found.required_dps == 140
    assert found.solved_dps >= 140
    # And the unpatched solve settles at the width's own sizing, unlifted, which
    # is the honest statement that at v0 depths the rule never binds.
    plain = centers.solve(mp.mpc(*SEAHORSE), SEAHORSE_PERIOD)
    assert plain.required_dps == nuc.NUCLEUS_DPS
    assert plain.solved_dps == centers.working_dps(depth.MIN_WIDTH)


def test_the_size_law_is_degree_general_and_not_the_quadratic_one() -> None:
    """A degree-4 atom sized by the flat `lambda^2` law lands inside its own body.

    The general exponent is `d/(d-1)`, which at `d = 4` is `4/3`. Read off the
    instrument this module solves through, so a regression there fails here.
    """
    anchor = next(row for row in roots.anchors(200) if row["family"].get("degree") == 4)
    view = anchor["viewport"]
    found = centers.solve(
        mp.mpc(mp.mpf(view["center_re"]), mp.mpf(view["center_im"])),
        anchor["provenance"]["period"],
        degree=4,
        width=depth.MIN_WIDTH,
    )
    # The frame the pool recorded for this atom is the same `FRAME_MULTIPLE` the
    # band's money shot is, so the two must agree about how big the atom is.
    assert found.money_shot == pytest.approx(float(view["width"]), rel=1e-6)


# --------------------------------------------------------------------------- #
# The ladder.
# --------------------------------------------------------------------------- #
def test_a_ladder_step_asks_only_for_periods_above_the_parent_s() -> None:
    """The one thing that makes a descent a descent.

    Without the floor the smallest converging period near any probe seed is the
    parent itself — the seed is inside the parent's own atom domain, which is
    enormously larger than the atom — and the ladder cannot take a step.
    """
    seed = mp.mpc(*SEAHORSE)
    with mp.workdps(centers.working_dps(depth.MIN_WIDTH)):
        unfloored = centers.periods_near(seed, 2, 120)
        floored = centers.periods_near(seed, 2, 120, period_min=40)
    assert unfloored, "the ranking found nothing at all, so this test proves nothing"
    assert min(unfloored) < 40
    assert floored == [period for period in unfloored if period >= 40]


def test_a_ladder_records_every_rung_whether_or_not_it_arrived() -> None:
    anchor = next(row for row in roots.anchors(200) if row["family"]["kind"] == "mandelbrot")
    found, why, ladder = roots.descend(anchor, random.Random(0), max_steps=1)
    assert ladder, "the anchor itself is rung zero and is always recorded"
    assert ladder[0]["step"] == 0
    assert ladder[0]["period"] == anchor["provenance"]["period"]
    if found is None:
        assert why and not why.endswith(":")
    else:
        assert depth.seats_this_size(found.size)
    # Every rung is strictly smaller than the one above it.
    sizes = [rung["size"] for rung in ladder]
    assert sizes == sorted(sizes, reverse=True)


def test_a_ladder_will_not_start_where_there_is_no_nucleus_to_start_from() -> None:
    julia = {
        "id": "j",
        "family": {"kind": "julia", "degree": 2, "c": [-0.4, 0.6]},
        "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "3.0"},
        "provenance": {"period": 3},
    }
    found, why, ladder = roots.descend(julia, random.Random(0))
    assert found is None
    assert why == "no_nucleus_on_this_plane"
    assert ladder == []


# --------------------------------------------------------------------------- #
# The clock.
# --------------------------------------------------------------------------- #
def test_the_deep_ceilings_are_stated_rather_than_inherited() -> None:
    for leg in (pacing.COLORIZE, pacing.RELEASE):
        assert deep_run.HUNG_CEILING[leg] > pacing.HUNG_CEILING[leg]
    # And the shallow ones are not moved by the deep mode existing.
    assert pacing.HUNG_CEILING == {pacing.COLORIZE: 600.0, pacing.RELEASE: 1800.0}


def test_a_deep_curation_clock_carries_them_onto_its_legs() -> None:
    clock = deep_run.curation_clock()
    assert clock.leg(pacing.RELEASE).ceiling == deep_run.HUNG_CEILING[pacing.RELEASE]
    # A measurement may still only raise it, which is the shallow rule and the
    # reason a slow class is not a killed class.
    clock.leg(pacing.RELEASE).observe(10.0)
    assert clock.leg(pacing.RELEASE).timeout() == deep_run.HUNG_CEILING[pacing.RELEASE]
    clock.leg(pacing.RELEASE).observe(deep_run.HUNG_CEILING[pacing.RELEASE])
    assert clock.leg(pacing.RELEASE).timeout() > deep_run.HUNG_CEILING[pacing.RELEASE]


def test_the_deep_walk_turns_the_shallow_operators_off_and_says_so(tmp_path) -> None:
    run = deep_run.Deep(out_dir=tmp_path / "deep", log=lambda *_: None)
    assert run.walk.reframings.enabled is False
    assert run.walk.limits.operator_quota == 0
    assert run.walk.limits.plane_grace_rungs == 0
    assert run.walk.gates.min_width == depth.MIN_WIDTH
    run.walk.ledger.close()
    header = [
        row
        for row in (tmp_path / "deep" / "walk.jsonl").read_text(encoding="utf-8").splitlines()
        if '"deep_run"' in row
    ]
    assert len(header) == 1
    assert "1.21e-10" in header[0]
