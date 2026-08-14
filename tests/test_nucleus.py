"""Newton on a nucleus, the divergence abort, and the atom instrument.

Two obligations are discharged here, and they pull in opposite directions.

The abort has to **fire** — a guard that never fires is untested — and it has to
fire on the property it claims, which is *feasibility against the budget* and
not magnitude. So it is proven by injection at a residual straddling the bound,
and proven to move with the budget: one seed, two budgets, two answers.

And the abort has to **change nothing else**. An ordinary solve is checked
value-for-value against a reimplementation of Newton without it, written out
here rather than reached by a flag on the code under test — a switch that turns
the guard off is still the subject supplying its own expectation.
"""

from __future__ import annotations

import math

import mpmath as mp
import pytest

from fractal_wallpapers.discovery import nucleus as nuc


@pytest.fixture(autouse=True)
def working_precision():
    previous = mp.mp.dps
    nuc.set_precision()
    yield
    mp.mp.dps = previous


def newton_without_the_abort(c0, period, *, degree=2, max_steps=nuc.NEWTON_STEPS, margin=6):
    """`newton_nucleus` as it would be with no divergence abort at all."""
    c = mp.mpc(c0)
    tolerance = mp.mpf(10) ** (-(mp.mp.dps - margin))
    residual = mp.inf
    steps = 0
    while steps < max_steps:
        steps += 1
        z, d = nuc.orbit(c, period, degree)
        residual = abs(z)
        if d == 0:
            break
        step = z / d
        c = c - step
        if abs(step) < tolerance and residual < tolerance:
            break
    z, _ = nuc.orbit(c, period, degree)
    residual = abs(z)
    return c, bool(residual < tolerance), steps


def identical(solve, reference):
    c, converged, steps = reference
    return solve.c == c and solve.converged == converged and solve.steps == steps


# --------------------------------------------------------------------------- #
# the bound is derived, not fitted
# --------------------------------------------------------------------------- #


def test_the_bound_is_the_magnitude_newton_could_retire_in_the_budget() -> None:
    """One nat per step, in bits, times the steps left. No free constant."""
    assert abs(nuc.NEWTON_BITS_PER_STEP - 1.0 / math.log(2)) < 1e-15
    for remaining in (1, 7, 59, 199):
        assert nuc.divergence_bound(remaining, safety=1.0) == pytest.approx(remaining / math.log(2))
        assert nuc.divergence_bound(remaining) == pytest.approx(
            nuc.DIVERGENCE_SAFETY * remaining / math.log(2)
        )
    assert nuc.divergence_bound(0) == 0.0


def test_the_bound_scales_with_the_budget() -> None:
    """The defining property. Flat, and the slow converger below would die."""
    assert nuc.divergence_bound(100) == pytest.approx(10 * nuc.divergence_bound(10))
    assert nuc.divergence_bound(199) > nuc.divergence_bound(59)


# --------------------------------------------------------------------------- #
# the abort fires, and only where it should
# --------------------------------------------------------------------------- #


def period_one_seed(magnitude_bits):
    """A period-1 seed whose residual *is* its own magnitude, so the bound can
    be straddled exactly."""
    return mp.mpc(mp.mpf(2) ** magnitude_bits, 0)


def test_the_abort_fires_on_a_seed_above_the_bound() -> None:
    seed = period_one_seed(nuc.divergence_bound(60 - 1) + 1)
    solve = nuc.newton_nucleus(seed, 1, max_steps=60)
    assert solve.converged is False
    assert solve.diverged is True
    assert solve.steps == 1, "the abort must stop on the first orbit pass"
    assert newton_without_the_abort(seed, 1, max_steps=60)[2] > solve.steps


def test_the_abort_does_not_fire_just_below_the_bound() -> None:
    """The other half of the straddle. Without it, a guard that aborted
    everything would pass the test above."""
    seed = period_one_seed(nuc.divergence_bound(60 - 1) - 1)
    solve = nuc.newton_nucleus(seed, 1, max_steps=60)
    assert solve.converged is True and solve.c == 0
    assert identical(solve, newton_without_the_abort(seed, 1, max_steps=60))


def test_one_seed_aborts_on_a_tight_budget_and_survives_a_generous_one() -> None:
    """Feasibility, not magnitude: a residual that cannot be retired in ten
    steps can be retired in six hundred, and the rule has to agree."""
    seed = period_one_seed(nuc.divergence_bound(10 - 1) + 1)
    tight = nuc.newton_nucleus(seed, 1, max_steps=10)
    roomy = nuc.newton_nucleus(seed, 1, max_steps=600)
    assert tight.converged is False and tight.steps == 1
    assert roomy.converged is True
    assert identical(roomy, newton_without_the_abort(seed, 1, max_steps=600))


def test_the_abort_fires_partway_into_a_wild_solve() -> None:
    """Not only at the seed. Both arms agree it did not converge, so no caller
    ever sees a different answer — only a cheaper one."""
    seed = mp.mpc("3.5", "2.5")
    solve = nuc.newton_nucleus(seed, 30)
    reference = newton_without_the_abort(seed, 30)
    assert solve.converged is False and reference[1] is False
    assert reference[2] == nuc.NEWTON_STEPS, "the reference must burn the budget here"
    assert solve.steps < reference[2]


def test_an_aborted_solve_reports_the_residual_that_tripped_it() -> None:
    """The abort skips the post-loop re-measure, because the coordinate did not
    move — so the residual is the one that fired the guard, not a stale value."""
    solve = nuc.newton_nucleus(mp.mpc("3.5", "2.5"), 30)
    in_bits = solve.residual_log10 * math.log(10) / math.log(2)
    assert in_bits > nuc.divergence_bound(nuc.NEWTON_STEPS - solve.steps)


# --------------------------------------------------------------------------- #
# ordinary solves are untouched
# --------------------------------------------------------------------------- #

CONVERGING = [
    (("-0.1592", "1.0317"), 3, 2),
    (("-1.7548776662", "0.0"), 3, 2),
    (("-1.31", "0.0"), 4, 2),  # the real-axis case the key's snapping is for
    (("0.7", "0.3"), 4, 3),
    (("-0.748", "0.263"), 5, 4),
    (("-0.786", "0.365"), 5, 5),
    (("-0.6", "0.5"), 6, 4),
]


@pytest.mark.parametrize(("seed", "period", "degree"), CONVERGING)
def test_an_ordinary_solve_is_value_identical_to_newton_without_the_abort(
    seed, period, degree
) -> None:
    start = mp.mpc(mp.mpf(seed[0]), mp.mpf(seed[1]))
    reference = newton_without_the_abort(start, period, degree=degree)
    assert reference[1], "a fixture that does not converge proves nothing"
    assert identical(nuc.newton_nucleus(start, period, degree=degree), reference)


def test_a_slow_converger_survives_when_the_budget_can_hold_it() -> None:
    """The solve that falsified a flat magnitude threshold: it sits at a
    residual around `10⁶⁶` for a hundred and fifty iterations and turns at 163.
    At the production budget it must be untouched; at a budget that could not
    have held it anyway, both arms must agree it failed."""
    seed = mp.mpc("-0.7453", "0.1127")
    reference = newton_without_the_abort(seed, 35, max_steps=nuc.NEWTON_STEPS)
    assert reference[1] and reference[2] > 100, reference
    assert identical(nuc.newton_nucleus(seed, 35), reference)
    assert newton_without_the_abort(seed, 35, max_steps=60)[1] is False
    assert nuc.newton_nucleus(seed, 35, max_steps=60).converged is False


# --------------------------------------------------------------------------- #
# the atom instrument
# --------------------------------------------------------------------------- #


def size_estimate(c, period, degree):
    """The empirical minibrot size law, written out independently.

    `size = 1 / (b · Λ^(d/(d−1)))`, where `Λ` is the orbit derivative product and
    `b` its second-order correction. Reimplemented here, from the size side
    rather than the derivative side, so the identity below is a genuine
    cross-check rather than a restatement.
    """
    multiplier = mp.mpc(1)
    correction = mp.mpc(1)
    z = mp.mpc(0)
    for _ in range(1, period):
        if degree == 2:
            z = z * z + c
            multiplier = 2 * z * multiplier
        else:
            z = z**degree + c
            multiplier = degree * z ** (degree - 1) * multiplier
        if multiplier == 0:
            return mp.mpc(0)
        correction = correction + 1 / multiplier
    denominator = correction * multiplier ** (mp.mpf(degree) / (degree - 1))
    return 1 / denominator if denominator != 0 else mp.mpc(0)


@pytest.mark.parametrize(("seed", "period", "degree"), CONVERGING)
def test_the_instrument_is_the_inverse_of_the_size_law(seed, period, degree) -> None:
    """`|A| ≡ 1/|size|`, exactly and at every period.

    Not approximately and not asymptotically: the two are the same analytic
    quantity reached from two directions, so `A` is a *re-derivation* of the size
    law from the c-derivative rather than a second estimate to average with it.
    """
    start = mp.mpc(mp.mpf(seed[0]), mp.mpf(seed[1]))
    solve = nuc.newton_nucleus(start, period, degree=degree)
    atom = nuc.atom_instrument(solve.c, period, degree)
    size = abs(size_estimate(solve.c, period, degree))
    assert float(atom.abs_a * size) == pytest.approx(1.0, rel=1e-9)
    assert atom.window_scale == pytest.approx(float(size), rel=1e-9)


@pytest.mark.parametrize(("seed", "period", "degree"), [c for c in CONVERGING if c[2] >= 3])
def test_the_flat_squared_law_under_sizes_every_higher_degree_atom(seed, period, degree) -> None:
    """The trap, measured. Written flat as `Λ²` the law is right at degree 2 and
    wrong above it by `|Λ|^((d−2)/(d−1))`, always in the direction of a frame too
    small — which renders as solid black, because the frame lands inside the
    atom's own body. This pins the *sign and scale* of the error so the general
    law cannot quietly be replaced by the flat one.
    """
    start = mp.mpc(mp.mpf(seed[0]), mp.mpf(seed[1]))
    c = nuc.newton_nucleus(start, period, degree=degree).c

    multiplier = mp.mpc(1)
    correction = mp.mpc(1)
    z = mp.mpc(0)
    for _ in range(1, period):
        z = z**degree + c
        multiplier = degree * z ** (degree - 1) * multiplier
        correction = correction + 1 / multiplier
    flat = abs(1 / (correction * multiplier * multiplier))
    correct = nuc.atom_instrument(c, period, degree).window_scale

    assert float(flat) < correct, "the flat law must under-size, never over-size"
    assert float(correct / flat) > 2.0, "and by a factor that matters"


def test_the_instrument_predicts_the_f64_wall_before_any_render() -> None:
    """The margin is a pure function of the atom and the presentation, so it can
    refuse a location without one render being attempted."""
    atom = nuc.atom_instrument(nuc.newton_nucleus(mp.mpc("-0.1592", "1.0317"), 3).c, 3, 2)
    wide = atom.f64_margin(width=1280, supersample=4)
    finer = atom.f64_margin(width=1280, supersample=8)
    assert wide > finer, "a finer presentation has less headroom, not more"
    assert wide - finer == pytest.approx(math.log10(2))
    assert atom.feasible()


# --------------------------------------------------------------------------- #
# the canonical name
# --------------------------------------------------------------------------- #


def test_the_symmetry_fold_is_the_identity_at_degree_two() -> None:
    """Degree 2 is one-fold, so the sector is the whole plane. Explicitly the
    identity, so nobody has to wonder whether it happens to be."""
    for point in (mp.mpc("-1.31", "0"), mp.mpc("0.3", "-0.5"), mp.mpc("-0.1592", "1.0317")):
        assert nuc.canonical_nucleus_c(point, 2) == point


@pytest.mark.parametrize("degree", [3, 4, 5])
def test_rotational_copies_of_one_atom_share_one_name(degree) -> None:
    """`z^d + c` has `(d−1)`-fold symmetry, so `c` and `c·ω^k` are one atom seen
    through a conjugacy. A key built from raw coordinates would count them as
    `d−1` separate atoms and inflate every distinct-atom number by that much.
    """
    c = mp.mpc("0.7", "0.3")
    keys = set()
    for k in range(degree - 1):
        angle = 2 * mp.pi * k / (degree - 1)
        keys.add(nuc.nucleus_key(c * mp.mpc(mp.cos(angle), mp.sin(angle)), degree))
    assert len(keys) == 1, keys


def test_axis_noise_is_snapped_away_so_one_atom_keeps_one_name() -> None:
    """A key rounds to significant digits, so a real-axis nucleus whose
    imaginary part is solver noise stringifies differently on every solve — and
    one atom enters a population once per seed that found it."""
    clean = mp.mpc("-1.31", "0")
    noisy = mp.mpc("-1.31", mp.mpf("3e-41"))
    other = mp.mpc("-1.31", mp.mpf("1e-3"))
    assert nuc.nucleus_key(noisy, 2) == nuc.nucleus_key(clean, 2)
    assert nuc.nucleus_key(other, 2) != nuc.nucleus_key(clean, 2)


def test_the_key_is_formed_at_the_reader_from_the_stored_strings() -> None:
    """Normalizing at read is what lets a row written by any writer land on the
    right atom. Parsing the stored strings as `f64` first would lose the tail
    that the rounding is supposed to be reading."""
    solve = nuc.newton_nucleus(mp.mpc("-0.1592", "1.0317"), 3)
    record = nuc.make_atom(solve.c, 3, 2)
    assert record is not None
    assert nuc.key_from_strings(record["center_re"], record["center_im"], 2) == record["key"]


# --------------------------------------------------------------------------- #
# candidate periods
# --------------------------------------------------------------------------- #


def test_the_candidate_periods_are_the_divisors_and_not_the_raw_argmin() -> None:
    """The correction that makes the whole probe work.

    A nucleus is superattracting, so just off it the orbit's smallest value lands
    on a high *multiple* of the period, never on the period. Newton at that
    multiple returns a non-minimal solution which is then rejected, and the
    operator reports "nothing here" while standing on a perfectly good atom. So
    the candidates are the argmins' divisors, smallest first.
    """
    solve = nuc.newton_nucleus(mp.mpc("-0.1592", "1.0317"), 3)
    just_off = solve.c + mp.mpc("1e-9", "1e-9")
    candidates = nuc.period_candidates(just_off, 2, 64, 4)
    assert 3 in candidates, candidates
    assert candidates == sorted(candidates), "smallest period first"
    assert 1 not in candidates, "period 1 is the c = 0 degenerate"

    record, status = nuc.identify_nucleus(just_off, near=1e-3, periods=candidates)
    assert status == "ok" and record["period"] == 3


def test_a_point_that_escapes_at_once_offers_no_candidate_periods() -> None:
    assert nuc.period_candidates(mp.mpc("10", "10"), 2, 64, 4) == []


def test_the_origin_and_a_non_minimal_period_are_both_refused() -> None:
    """Neither is a place. A record for either would be an atom that is not one."""
    assert nuc.make_atom(mp.mpc("1e-9", "0"), 4, 2) is None
    period_three = nuc.newton_nucleus(mp.mpc("-0.1592", "1.0317"), 3).c
    assert nuc.make_atom(period_three, 3, 2) is not None
    assert nuc.make_atom(period_three, 6, 2) is None, "6 is a multiple of the true 3"
