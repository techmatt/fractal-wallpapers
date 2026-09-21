"""The parabolic solver, against the four parameters that can be written down.

Every anchor here is a number this project did not compute: `1/4` and `−3/4` are
the main cardioid's cusp and its period-doubling point, `−5/4` is the period-2
disc's, and `−7/4` is the period-3 window's tangent bifurcation — the classic
exact value, and the one place premise 3 of the pilot prompt was worth checking
rather than believing, because the *nucleus* of that same window is
`−1.75487766…` and the two are a hundredth apart. A solver checked against its
own output is checked against nothing, so the acceptance is on the multiplier
residual and on these four.

The two failure modes the solve actually has are each given a test of their own,
because both were found here rather than reasoned about: the `0/1` end of a
**satellite** component's ray is a singular system and has to be refused rather
than returned, and classification by Newton on `f_c^p(z) = z` is singular at
exactly the point every offset is taken around.
"""

from __future__ import annotations

import math

import mpmath as mp
import pytest

from fractal_wallpapers.discovery import nucleus as nuc
from fractal_wallpapers.discovery import parabolic as par

#: The period-3 window's nucleus — the "airplane" — to more digits than `f64`.
AIRPLANE = "-1.754877666246692760049508896358532800"

#: The period-4 satellite on the real axis, hanging off the period-2 disc.
SATELLITE_4 = "-1.310702641336832841153042900750000000"


@pytest.fixture(autouse=True)
def working_precision():
    previous = mp.mp.dps
    par.set_precision()
    yield
    mp.mp.dps = previous


@pytest.mark.parametrize(
    ("nucleus_c", "period", "angle", "expected"),
    [
        (0, 1, (0, 1), "0.25"),
        (0, 1, (1, 2), "-0.75"),
        (-1, 2, (1, 2), "-1.25"),
        (AIRPLANE, 3, (0, 1), "-1.75"),
    ],
)
def test_the_four_parabolic_points_that_can_be_written_down(nucleus_c, period, angle, expected):
    solved = par.newton_parabolic(mp.mpc(nucleus_c), period, *angle)
    assert solved.converged
    assert abs(solved.c - mp.mpf(expected)) < mp.mpf("1e-50")


def test_the_main_cardioid_agrees_with_its_closed_form_at_every_angle_the_pilot_draws():
    """`μ/2 − μ²/4` for every `r/q` with `q ≤ 12`, solved rather than substituted."""
    worst = 0.0
    for q in range(1, 13):
        for r in range(q):
            if q > 1 and math.gcd(r, q) != 1:
                continue
            solved = par.newton_parabolic(0, 1, r, q)
            assert solved.converged, f"{r}/{q}"
            worst = max(worst, float(abs(solved.c - par.cardioid_parabolic(r, q))))
    assert worst < 1e-50, worst


def test_the_cusp_is_the_angle_zero_end_and_not_a_special_case():
    """`q = 1` goes through the same solve as every other angle.

    Worth pinning because the system *looks* degenerate there — `λ = 1` makes the
    first Jacobian row's leading entry `(f^p)'(z) − 1` exactly zero — and it is
    the second row that keeps the determinant off zero.
    """
    cusp = par.newton_parabolic(0, 1, 0, 1)
    assert cusp.q == 1
    assert cusp.multiplier_residual_log10 < -50
    assert abs(cusp.c - mp.mpf("0.25")) < mp.mpf("1e-50")


def test_an_angle_is_reduced_so_one_point_is_not_two_answers():
    half = par.newton_parabolic(0, 1, 1, 2)
    same = par.newton_parabolic(0, 1, 3, 6)
    assert (same.r, same.q) == (1, 2)
    assert abs(half.c - same.c) < mp.mpf("1e-50")


def test_the_two_components_whose_size_is_known_are_measured_right():
    """And measured off the component, never off `1/|A|`.

    The cardioid runs `1/4` to `−3/4` and the period-2 disc `−3/4` to `−5/4`, so
    the two scales are exactly `1` and `1/2`. [`nucleus.atom_instrument`]'s
    `window_scale` is the atom's *domain* and answers neither.

    **The two arrive by different routes and that is the geometry**: the period-2
    disc is a satellite of the cardioid, so its `0/1` end is the cardioid's own
    `1/2` point — one parameter belonging to two components, solvable from the
    parent and singular from the child. The disc is round about its nucleus, so
    the doubling radius gives `1/2` exactly anyway.
    """
    cardioid = par.component_scale(0, 1)
    assert cardioid.route == par.RAY_ENDS
    assert not cardioid.satellite
    assert abs(cardioid.scale - 1.0) < 1e-30
    disc = par.component_scale(-1, 2)
    assert disc.route == par.DOUBLING_RADIUS
    assert disc.satellite
    assert abs(disc.scale - 0.5) < 1e-30


def test_a_primitive_island_is_measured_by_its_own_ray():
    """The period-3 window: cusp at `−7/4`, doubling at about `−1.7685`."""
    measured = par.component_scale(mp.mpc(AIRPLANE), 3)
    assert measured.route == par.RAY_ENDS
    assert not measured.satellite
    assert measured.scale == pytest.approx(0.0185291524, rel=1e-6)


def test_a_satellite_has_no_angle_zero_end_and_falls_back_rather_than_returning_zero():
    """The `0/1` solve is singular on a satellite, and that is the geometry.

    At a satellite's root the cycle has collided with its *parent's*, so
    `f^p(z) = z` has a double root and the system's Jacobian is singular. The
    solve refuses; the scale comes from the doubling radius instead, and says so.
    """
    nucleus_c = mp.mpc(SATELLITE_4)
    assert nuc.is_minimal(nucleus_c, 4)
    assert not par.newton_parabolic(nucleus_c, 4, 0, 1).converged
    measured = par.component_scale(nucleus_c, 4)
    assert measured.satellite
    assert measured.route == par.DOUBLING_RADIUS
    assert measured.scale == pytest.approx(0.1147925961, rel=1e-6)


def test_the_degree_gate_says_what_is_wrong_rather_than_solving_something_else():
    with pytest.raises(ValueError, match="singular start at degree 3"):
        par.newton_parabolic(mp.mpc("-0.5"), 2, 0, 1, degree=3)


def test_classification_reads_all_three_sides_around_a_bulb_root():
    """A `1/3` root has a component, a child and an exterior around it."""
    point = par.newton_parabolic(0, 1, 1, 3)
    scale = par.component_scale(0, 1).scale
    kinds = {o.classification for o in par.offsets(point, scale, [1e-2], thetas=12)}
    assert kinds == {par.INSIDE_COMPONENT, par.INSIDE_OTHER, par.OUTSIDE}


def test_the_component_side_of_a_cusp_is_not_reported_as_somewhere_else():
    """The regression the offset ring was built wrong by.

    Newton on `f_c^p(z) = z` in `z` alone is singular at the parabolic cycle —
    it is a double root of that equation — so a classifier built on it returns
    "no cycle" for a whole neighbourhood of the cusp and calls the *inside* of
    the main cardioid [`INSIDE_OTHER`]. Reading the cycle off the critical orbit
    has no such point.
    """
    point = par.newton_parabolic(0, 1, 0, 1)
    ring = par.offsets(point, 1.0, [1e-2], thetas=12)
    assert sum(o.classification == par.INSIDE_COMPONENT for o in ring) >= 8
    assert not any(o.classification == par.INSIDE_OTHER for o in ring)
    # A cusp has no attached bulb, so the two answers are the component and
    # the exterior, and both are present.
    assert any(o.classification == par.OUTSIDE for o in ring)


def test_a_point_well_inside_the_cardioid_is_the_component_and_one_outside_is_not():
    assert par.classify(mp.mpc("0.0"), 1) == par.INSIDE_COMPONENT
    assert par.classify(mp.mpc("-1.0"), 1) == par.INSIDE_OTHER
    assert par.classify(mp.mpc("-1.0"), 2) == par.INSIDE_COMPONENT
    assert par.classify(mp.mpc("1.0"), 1) == par.OUTSIDE


def test_minimality_is_what_keeps_an_ancestor_out_of_a_components_count():
    """`c = 0` closes at every period, and only period 1 is its component."""
    assert par.classify(mp.mpc("0.0"), 2) == par.INSIDE_OTHER
    assert par.classify(mp.mpc("0.0"), 4) == par.INSIDE_OTHER


def test_an_offset_below_the_ulp_floor_is_dropped_and_never_clamped():
    """A clamped offset would be recorded at an `ε` it is not at."""
    point = par.newton_parabolic(0, 1, 0, 1)
    ring = par.offsets(point, 1.0, [1e-2, 1e-18], thetas=12, ulp_floor=1e3)
    assert {o.epsilon for o in ring} == {1e-2}
    assert all(o.ulps >= 1e3 for o in ring)


def test_the_ulp_reading_is_taken_at_the_magnitude_of_the_point():
    """Which is the whole content of it: the same displacement is a different
    number of ulps beside `1/4` and beside `−1.75`."""
    near_origin = par.ulps_between(mp.mpf("0.25"), mp.mpf("0.25") + mp.mpf("1e-15"))
    far_out = par.ulps_between(mp.mpf("-1.75"), mp.mpf("-1.75") + mp.mpf("1e-15"))
    assert near_origin > far_out
    assert far_out == pytest.approx(1e-15 / math.ulp(1.75), rel=1e-9)


def test_a_march_reports_the_halvings_it_needed_rather_than_hiding_them():
    """The record of where the ray was hard, and the budget is per step.

    Spent globally, one awkward step exhausts it and every step after it is
    refused for a reason that has nothing to do with them — which is how the
    period-2 disc's `0/1` end came to look like a satellite.
    """
    solved = par.newton_parabolic(mp.mpc(AIRPLANE), 3, 1, 2)
    assert solved.converged
    assert solved.steps >= par.RAY_STEPS
