"""Parabolic parameters: where a hyperbolic component touches its neighbour.

A hyperbolic component of the Mandelbrot set is a set of parameters `c` whose
period-`p` cycle attracts, and the **multiplier** `λ = (f_c^p)'` sweeps the open
unit disc as `c` sweeps the component. The boundary is `|λ| = 1`, and the point
on it where `λ = e^{2πi r/q}` is where the component's `r/q` child is attached —
a bulb root when `q > 1`, the component's own **cusp** when `q = 1`.

Those points are what this module solves for, and the reason to want them is
pictorial rather than arithmetic. A Julia set at a parabolic `c` has a *parabolic
implosion*: the attracting cycle and the repelling one have collided, the basin
boundary grows the filigree of the Leau-Fatou flowers, and a neighbourhood of `c`
in parameter space produces Julia sets that are rich at a **shallow** zoom. This
project's supply for `julia:*` is root-bound — a Julia partition's places all
descend from some `c` — so a list of `c` aimed at parabolic points is a supply
question, not a rendering one. [`offsets`] is what turns one solved point into a
population of roots.

## The solve is exact, and that is the whole design

A parabolic parameter is the simultaneous solution of

```text
f_c^p(z) = z                       the cycle closes
(f_c^p)'(z) = e^{2πi r/q}          at the multiplier the child is attached at
```

in the two unknowns `(z, c)`, and [`newton_parabolic`] is Newton on exactly that
system at [`nucleus.NUCLEUS_DPS`]. Nothing here is fitted, tuned or read off a
scale, and that is deliberate: `discovery/README.md` records that a *tuned* aim
misses its target by a fixed fraction of `|λ|`, which is a fraction that does not
go away by making the tuning finer.

**The route to the root is continuation along the internal ray.** At `λ = 0` the
solution is the component's nucleus with `z` at the critical point, which
[`nucleus.newton_nucleus`] already hands over; the solver marches
`λ = t·e^{2πi r/q}` from `t = 0` to `t = 1`, Newton-correcting each step from the
previous answer. It never has to know whether the component is cardioid-like or
disc-like, and it needs no starting guess of its own — which is what makes one
function serve the main cardioid, the period-2 disc and a period-31 minibrot
cusp alike.

## The scale comes off the component, never off `|A|`

[`nucleus.atom_instrument`] reports `window_scale = 1/|A|`, and the website's
perturbation crate found that quantity to be the atom's **domain** rather than
its body — the body is about its square. So nothing here takes a size from it.
[`component_scale`] measures the component with the component: it solves the two
ends of the real internal ray, `r/q = 0/1` and `r/q = 1/2`, and reports the
distance between them. On the main cardioid that is `|1/4 − (−3/4)| = 1`, its
diameter along the axis; on the period-2 disc `|−3/4 − (−5/4)| = 1/2`, likewise.
It is one more solve of the same solver, so it cannot disagree with the aim.

## Classification answers a different question from "did it escape"

An offset `c* + ε·s·e^{iθ}` can land in three materially different places, and
they make three different pictures. Inside the component the Julia set is
connected with an attracting `p`-cycle; **outside `M`** it is a Cantor dust and
has no interior at all, which is the case [`unresolved_share`] leans on; and
inside `M` but outside the component means the offset fell into the child bulb
attached at that very root, where the cycle has period `p·q`. [`classify`] tells
the three apart by reading the multiplier of the nearby `p`-cycle rather than by
a pixel count, so it is exact where a render is a vote.

## Degree

The arithmetic is written for `z^d + c` throughout and the solver is **gated to
degree 2**, because the generalization is not free and the gate says so out loud.
At a degree-`d` nucleus the multiplier vanishes to order `d − 1`, so the `t = 0`
end of the internal ray — the one free starting point the design depends on — is
a singular start for every `d ≥ 3`: the multiplier's derivative with respect to
both unknowns is identically zero there and Newton has no direction to move in.
Making it work needs a predictor for the ray's first step, which is a different
piece of work from this one. Degree 6 could not be drawn at anyway; see
`labeling/README.md`'s *Degree 6 is never labelled*.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction

import mpmath as mp

from fractal_wallpapers.discovery import nucleus as nucleus_module

#: Newton steps one continuation step is allowed.
#:
#: Small on purpose: a continuation step starts from the previous step's answer,
#: so a step that needs more than a handful of corrections is a step that was too
#: long, and lengthening the budget hides that instead of fixing it. The march
#: below halves its step and retries, which costs the same corrections and leaves
#: a record of where the ray was hard.
STEP_NEWTON_MAX = 40

#: Continuation steps the ray is marched in, before any halving.
#:
#: The ray is short and smooth over most of its length and turns only near
#: `|λ| = 1`, so a uniform march is wasteful at one end and marginal at the
#: other. Sixteen is what the anchors in `tests/test_parabolic.py` converge in
#: with no halving at all on the main cardioid and the period-2 disc, and it
#: leaves the halving for the minibrot cusps, where it does fire.
RAY_STEPS = 16

#: How far a continuation step may be halved before the march gives up.
MAX_HALVINGS = 8

#: Residual, in decimal digits below the working precision, a solve must reach.
#:
#: The same margin [`nucleus.newton_nucleus`] holds itself to, for the same
#: reason: the last few digits of a 60-digit solve are the solver's own noise and
#: demanding them turns a converged solve into a non-converged one.
TOL_DPS_MARGIN = 6

#: Iterations the escape test in [`classify`] is allowed.
#:
#: Generous rather than policy-shaped, because this is arithmetic and not a
#: picture: an offset at `ε = 1e-4` inside the component has `|λ|` within about
#: `1e-4` of one, and an orbit settling onto that cycle needs order `1/(1 − |λ|)`
#: steps. The cap that renders the picture is a separate question and
#: [`unresolved_share`] is where it is asked.
CLASSIFY_CAP = 1 << 18

#: Escape radius for the classification orbit, in the degree's own units.
ESCAPE_RADIUS = 4.0


def set_precision() -> None:
    """Put mpmath at the precision every solve here runs at."""
    nucleus_module.set_precision()


def _tolerance():
    return mp.mpf(10) ** (-(mp.mp.dps - TOL_DPS_MARGIN))


@dataclass
class Parabolic:
    """One solved parabolic parameter, and what the solve had to do to get it."""

    #: The parameter itself, at working precision.
    c: object
    #: A point of the parabolic cycle, at working precision.
    z: object
    period: int
    degree: int
    #: The internal angle, in lowest terms. `q = 1` is the component's cusp.
    r: int
    q: int
    converged: bool
    #: `log₁₀` of the larger of the two residuals at the final iterate.
    residual_log10: float
    #: `log₁₀|λ_solved − e^{2πi r/q}|`, the one an anchor is accepted on.
    multiplier_residual_log10: float
    #: Continuation steps actually taken, halvings included.
    steps: int
    #: How often a step had to be halved. Zero on the two large components.
    halvings: int

    def as_strings(self, digits: int = nucleus_module.EMIT_DIGITS) -> tuple[str, str]:
        """`(re, im)` of `c`, written the way a record writes a coordinate."""
        return (
            mp.nstr(self.c.real, digits, strip_zeros=False),
            mp.nstr(self.c.imag, digits, strip_zeros=False),
        )


def _cycle_pass(z, c, period: int, degree: int):
    """One pass of `f_c^p` carrying everything Newton on the system needs.

    Returns `(z_p, v_p, u_p, m_p, dm_dz, dm_dc)` where `v = ∂z_k/∂z`,
    `u = ∂z_k/∂c`, `m = Π_{j<k} f'(z_j)` — the multiplier once `k = p` — and the
    last two are that product's derivatives in the two unknowns.

    **The multiplier's derivative is accumulated, never divided out.** The
    log-derivative form `∂m/∂z = m · Σ f''(z_j)/f'(z_j) · v_j` is shorter and is
    wrong exactly where this solver starts: at a nucleus `z_0` is the critical
    point, `f'(z_0) = 0`, and the sum's first term is a division by zero at the
    one place the continuation is guaranteed to visit. Carrying the product's
    derivative forward alongside the product costs two more multiplies a step and
    is defined everywhere.
    """
    z = mp.mpc(z)
    c = mp.mpc(c)
    v = mp.mpc(1)  # ∂z_k/∂z
    u = mp.mpc(0)  # ∂z_k/∂c
    m = mp.mpc(1)  # Π_{j<k} f'(z_j)
    dm_dz = mp.mpc(0)
    dm_dc = mp.mpc(0)
    for _ in range(period):
        if degree == 2:
            slope = 2 * z  # f'(z)
            curve = mp.mpc(2)  # f''(z)
            nxt = z * z + c
        else:
            power = z ** (degree - 2)
            slope = degree * power * z
            curve = degree * (degree - 1) * power
            nxt = power * z * z + c
        dm_dz = dm_dz * slope + m * curve * v
        dm_dc = dm_dc * slope + m * curve * u
        m = m * slope
        v = slope * v
        u = slope * u + 1
        z = nxt
    return z, v, u, m, dm_dz, dm_dc


def _newton_step(z, c, period: int, degree: int, target):
    """One Newton correction of the two-unknown system, or `None` if singular."""
    z_p, v, u, m, dm_dz, dm_dc = _cycle_pass(z, c, period, degree)
    f1 = z_p - z
    f2 = m - target
    a11, a12 = v - 1, u
    a21, a22 = dm_dz, dm_dc
    det = a11 * a22 - a12 * a21
    if det == 0:
        return None
    dz = (f1 * a22 - f2 * a12) / det
    dc = (a11 * f2 - a21 * f1) / det
    residual = max(abs(f1), abs(f2))
    return z - dz, c - dc, residual, max(abs(dz), abs(dc))


def _correct(z, c, period: int, degree: int, target):
    """Newton the system to convergence at one `λ`, or `None`."""
    tolerance = _tolerance()
    residual = mp.inf
    for _ in range(STEP_NEWTON_MAX):
        stepped = _newton_step(z, c, period, degree, target)
        if stepped is None:
            return None
        z, c, residual, motion = stepped
        if motion < tolerance and residual < tolerance:
            return z, c, residual
    if residual < tolerance:
        return z, c, residual
    return None


def newton_parabolic(
    nucleus_c,
    period: int,
    r: int,
    q: int,
    *,
    degree: int = 2,
    ray_steps: int = RAY_STEPS,
) -> Parabolic:
    """The parabolic parameter of this component at internal angle `r/q`.

    `nucleus_c` is the component's nucleus — the `c` whose critical orbit closes
    after `period` steps — which is what every store here already holds and what
    [`nucleus.identify_nucleus`] recovers from any point on the component.

    The angle is reduced to lowest terms first, so `2/4` and `1/2` are one
    question asked twice rather than two answers that have to agree. `r/q = 0/1`
    is the cusp: `λ = 1`, the root of the component itself.
    """
    if degree != 2:
        raise ValueError(
            f"the internal ray's t = 0 end is a singular start at degree {degree}: the "
            f"multiplier vanishes to order {degree - 1} at a degree-{degree} nucleus, so "
            f"both of its derivatives are zero there and Newton has no direction. Degree 2 "
            f"is what this solver is proven on; see this module's docstring."
        )
    set_precision()
    angle = Fraction(int(r), int(q))
    r, q = angle.numerator, angle.denominator
    turn = 2 * mp.pi * mp.mpf(r) / mp.mpf(q)
    unit = mp.mpc(mp.cos(turn), mp.sin(turn))

    z = mp.mpc(0)
    c = mp.mpc(nucleus_c)
    t = mp.mpf(0)
    span = mp.mpf(1) / ray_steps
    # The shortest step the march will take before calling the ray impassable.
    # Without it a singular endpoint is not refused, it is *crawled at*: the step
    # halves, the halved step succeeds, the next step tries the full span again
    # and fails again, and `t` creeps toward the singularity forever. The
    # period-4 satellite took 129 steps and 140 halvings that way and still came
    # back unconverged — a second and a half to say no.
    floor = span / (2**MAX_HALVINGS)
    taken = 0
    halvings = 0
    residual = mp.mpf(0)
    while t < 1:
        step = min(span, mp.mpf(1) - t)
        corrected = None
        # The halving budget is **per step**, not per march. Spent globally it
        # is a cap on how hard the whole ray may be, which on a long ray is
        # exhausted by one awkward step and then refuses every step after it for
        # a reason that is nothing to do with them.
        spent = 0
        while corrected is None:
            corrected = _correct(z, c, period, degree, (t + step) * unit)
            if corrected is None:
                if spent >= MAX_HALVINGS:
                    break
                spent += 1
                halvings += 1
                step = step / 2
        if corrected is None:
            break
        z, c, residual = corrected
        t = t + step
        taken += 1
        if step <= floor and t < 1:
            break

    _, _, _, multiplier, _, _ = _cycle_pass(z, c, period, degree)
    multiplier_residual = abs(multiplier - unit)
    tolerance = _tolerance()
    return Parabolic(
        c=c,
        z=z,
        period=int(period),
        degree=int(degree),
        r=r,
        q=q,
        converged=bool(t >= 1 and multiplier_residual < tolerance),
        residual_log10=float(mp.log10(residual)) if residual > 0 else -999.0,
        multiplier_residual_log10=(
            float(mp.log10(multiplier_residual)) if multiplier_residual > 0 else -999.0
        ),
        steps=taken,
        halvings=halvings,
    )


def cardioid_parabolic(r: int, q: int):
    """The main cardioid's parabolic point in closed form: `μ/2 − μ²/4`.

    The period-1 component is the one whose answer is known without solving
    anything, so it is the check the solver is held to rather than a shortcut the
    solver takes. Nothing in the pipeline calls this; `tests/test_parabolic.py`
    does.
    """
    set_precision()
    turn = 2 * mp.pi * mp.mpf(int(r)) / mp.mpf(int(q))
    mu = mp.mpc(mp.cos(turn), mp.sin(turn))
    return mu / 2 - mu * mu / 4


#: How a component's scale was arrived at. See [`component_scale`].
RAY_ENDS = "ray_ends"
DOUBLING_RADIUS = "doubling_radius"


@dataclass
class ComponentScale:
    """A component's own linear size, and which route measured it."""

    scale: float
    route: str
    #: `True` where the `0/1` end of the internal ray was singular — which is
    #: what a satellite component *is*, not a failure of the solve.
    satellite: bool


def component_scale(nucleus_c, period: int, *, degree: int = 2) -> ComponentScale:
    """The component's own linear size, measured off its own internal ray.

    **Not** `1/|A|`: [`nucleus.atom_instrument`] reports the atom's *domain* and
    the body is about its square, and this pilot's whole offset ladder is in
    units of this number.

    The direct route is the distance between the parabolic points at internal
    angles `0/1` and `1/2` — the cusp at one end of the real ray and the
    period-doubling point at the other. On the main cardioid that is
    `|1/4 − (−3/4)| = 1` and on a primitive minibrot it is the island's own
    length; both are components whose size can be written down independently, and
    it agrees with both.

    **A satellite component has no `0/1` end to measure**, and the solver is
    right to refuse it rather than return something. At the root of the period-2
    disc the two points of the 2-cycle have collided with the *parent's* fixed
    point, so `f²(z) = z` has a double root there and the system's Jacobian is
    singular — the degeneracy premise 2's "generically" is about. A satellite is
    round about its nucleus, so the fallback is twice the nucleus-to-doubling
    distance, which on the period-2 disc gives `2·|−1 − (−5/4)| = 1/2` exactly.
    The route is reported rather than folded away, because the two are the same
    number on a disc and differ by about 3/2 on a cardioid.
    """
    doubling = newton_parabolic(nucleus_c, period, 1, 2, degree=degree)
    if not doubling.converged:
        return ComponentScale(scale=0.0, route=RAY_ENDS, satellite=False)
    cusp = newton_parabolic(nucleus_c, period, 0, 1, degree=degree)
    if cusp.converged:
        return ComponentScale(
            scale=float(abs(cusp.c - doubling.c)), route=RAY_ENDS, satellite=False
        )
    return ComponentScale(
        scale=2.0 * float(abs(mp.mpc(nucleus_c) - doubling.c)),
        route=DOUBLING_RADIUS,
        satellite=True,
    )


#: What [`classify`] can say about an offset.
INSIDE_COMPONENT = "component"
INSIDE_OTHER = "interior_other"
OUTSIDE = "outside"

#: How close two orbit points have to be for the orbit to count as settled.
#:
#: Loose by `f64` standards and it has to be: the orbit is read after a warm-up
#: that is finite, and a parameter a hair inside the component approaches its
#: cycle geometrically at a rate that is *itself* a hair under one. A tighter
#: tolerance would not find a shorter period, it would call a settled orbit
#: unsettled and report the wrong side of the boundary.
SETTLE_TOLERANCE = 1e-9

#: Iterations between settling checks in [`_orbit_tail`].
SETTLE_CHECK_BLOCK = 1024


def _orbit_tail(c, degree: int, cap: int, period: int):
    """Walk the critical orbit and return its tail, or `None` if it escaped.

    The tail is `period + 1` consecutive points after a warm-up of the whole
    budget, which is what the two questions below both read. `f64` throughout:
    inside `M` the orbit is being *contracted* onto an attracting cycle, which is
    the numerically stable direction, and outside it the only thing asked is
    whether it left the disc.
    """
    point = complex(float(mp.mpf(c.real)), float(mp.mpf(c.imag)))
    z = 0j
    radius = ESCAPE_RADIUS**2
    walked = 0
    while True:
        # Walked in blocks so the settled majority pays for what it needed
        # rather than for the budget the slowest rung needs. An offset at
        # `ε = 1e-1` settles in a few hundred steps; one at `1e-5` may take
        # every step there is, and the block test costs `period` iterations.
        for _ in range(min(SETTLE_CHECK_BLOCK, cap - walked)):
            z = (z * z + point) if degree == 2 else (z**degree + point)
            if not math.isfinite(z.real) or not math.isfinite(z.imag):
                return None
            if z.real * z.real + z.imag * z.imag > radius:
                return None
        walked = min(walked + SETTLE_CHECK_BLOCK, cap)
        tail = [z]
        for _ in range(period):
            z = (z * z + point) if degree == 2 else (z**degree + point)
            tail.append(z)
        if walked >= cap or abs(tail[-1] - tail[0]) <= SETTLE_TOLERANCE:
            return tail


def _tail_multiplier(tail, degree: int) -> complex:
    """`Π f'(w_k)` over one period of a settled orbit — the cycle's own `λ`."""
    multiplier = 1 + 0j
    for w in tail[:-1]:
        multiplier *= (2 * w) if degree == 2 else (degree * w ** (degree - 1))
    return multiplier


def classify(c, period: int, seed=None, *, degree: int = 2, cap: int = CLASSIFY_CAP) -> str:
    """Where `c` sits relative to the component its parabolic point belongs to.

    Three answers, because they are three materially different pictures:

    * [`OUTSIDE`] — the critical orbit escapes, so the filled Julia set is a
      Cantor dust with **no interior**. That is what makes the unresolved share
      readable off a render at all; see `Part 3` of this module's own pilot and
      [`unresolved_share`] in `scratch`'s leg.
    * [`INSIDE_COMPONENT`] — the orbit settles onto an attracting cycle of
      minimal period `period`. The Julia set is connected with a `p`-cycle basin.
    * [`INSIDE_OTHER`] — inside `M`, on some other component. Just across a
      `r/q` bulb root that is the attached child, whose cycle has period `p·q`;
      the name does not claim which, only that it is not this one.

    **The cycle is read off the critical orbit and not solved for**, which is the
    correction that matters at these parameters. Newton on `f_c^p(z) = z` in `z`
    alone is singular at exactly the point every offset here is taken around —
    the parabolic cycle is a double root of that equation — so it reports "no
    cycle" for a whole neighbourhood of the target and the ring around a cusp
    comes back as [`INSIDE_OTHER`] throughout. The critical orbit is attracted to
    every attracting cycle there is, so walking it answers the same question with
    no root-finding at all. `seed` is accepted and unused, for callers written
    against the earlier shape.
    """
    del seed
    tail = _orbit_tail(c, degree, cap, period)
    if tail is None:
        return OUTSIDE
    if abs(tail[-1] - tail[0]) > SETTLE_TOLERANCE:
        return INSIDE_OTHER
    # Settled at `period`, but a divisor of it would have settled too: a fixed
    # point closes at every period there is. Minimality is what makes this the
    # component rather than one of its ancestors.
    for divisor in range(1, period):
        if period % divisor == 0 and abs(tail[divisor] - tail[0]) <= SETTLE_TOLERANCE:
            return INSIDE_OTHER
    return INSIDE_COMPONENT if abs(_tail_multiplier(tail, degree)) < 1 else INSIDE_OTHER


@dataclass
class Offset:
    """One aimed `c`, and the stratum it was drawn in."""

    c: object
    #: The parabolic point it was taken around.
    origin: Parabolic
    #: Displacement as a multiple of the component's own scale.
    epsilon: float
    #: Direction, in turns of `2π`.
    theta: float
    scale: float
    classification: str
    #: Distance from `c*`, in units of last place of `|c|` — the floor a pilot
    #: keeps offsets above so an offset is a different `f64` and not a rounding.
    ulps: float
    stratum: dict = field(default_factory=dict)


def ulps_between(a, b) -> float:
    """How many `f64` units of last place apart two parameters are.

    Read at the magnitude of the *point*, which is what decides the spacing: a
    displacement of `1e-17` beside `c = −1.75` is a third of an ulp and beside
    `c = 1e-3` is a thousand of them.
    """
    magnitude = float(abs(mp.mpc(a)))
    if magnitude == 0:
        return float("inf")
    spacing = math.ulp(magnitude)
    return float(abs(mp.mpc(a) - mp.mpc(b))) / spacing


def offsets(
    point: Parabolic,
    scale: float,
    epsilons,
    *,
    thetas: int = 12,
    degree: int = 2,
    ulp_floor: float = 1e3,
) -> list[Offset]:
    """The ring of aimed parameters around one parabolic point.

    `c* + ε·s·e^{iθ}` for each `ε` and each of `thetas` directions evenly spaced
    in turn — twelve by default, which puts one on the real ray in each
    direction and ten off it. Each is classified, and each carries the ulp
    distance so a caller can floor the ladder where an offset stops being a
    distinguishable `f64`.

    Offsets closer than `ulp_floor` units of last place are **dropped**, not
    clamped: a clamped offset would be recorded at an `ε` it is not at.
    """
    set_precision()
    out: list[Offset] = []
    for epsilon in epsilons:
        for index in range(thetas):
            theta = index / thetas
            turn = 2 * mp.pi * mp.mpf(theta)
            displacement = mp.mpf(str(epsilon)) * mp.mpf(str(scale))
            c = point.c + displacement * mp.mpc(mp.cos(turn), mp.sin(turn))
            ulps = ulps_between(point.c, c)
            if ulps < ulp_floor:
                continue
            out.append(
                Offset(
                    c=c,
                    origin=point,
                    epsilon=float(epsilon),
                    theta=float(theta),
                    scale=float(scale),
                    classification=classify(c, point.period, point.z, degree=degree),
                    ulps=ulps,
                )
            )
    return out
