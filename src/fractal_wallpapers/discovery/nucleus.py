"""Minibrot nuclei: solving for one, measuring it, and naming it.

A *nucleus* is the center of a hyperbolic component — a parameter `c` whose
critical orbit returns exactly to zero after `p` steps. Around it sits a small
copy of the whole set, and that copy is what makes a nucleus worth finding: it
is a marker for a dense, structured neighbourhood, at a scale the search can
compute before rendering anything.

Three things live here, and they come off one recursion:

* **Newton** on `z_p(c) = 0`, with a divergence abort that is a *budget*
  argument rather than a magnitude threshold. See [`divergence_bound`].
* **The atom instrument `A`**, which turns that same recursion into the atom's
  size, its orientation, the working precision it needs, and an a-priori answer
  to "can `f64` still render a frame this size?".
* **A canonical name**, so the same atom found twice — by two operators, in two
  runs, from two different seeds — is recognisably one atom.

The arithmetic is `mpmath` at 60 decimal digits. That is not caution: Newton
needs accurate division, and a nucleus at period 30 sits at a scale where `f64`
has no digits left to localize it with. `f64` still renders the frame; it cannot
find its center.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mpmath as mp

#: Working precision for every Newton solve here, in decimal digits.
NUCLEUS_DPS = 60

#: Newton steps a nucleus solve is allowed.
#:
#: Large, and it is the divergence abort below that makes it affordable. Before
#: the abort, a seed that was never going to converge burned the entire budget,
#: so the budget *was* the cost of the search and raising it multiplied the price
#: of every failure — and failures are the majority of any Newton grid. The
#: budget was therefore held low, which made it silently a *quality* knob: a slow
#: converger needing one more step than the cap was recorded as "no nucleus
#: here", which is indistinguishable in the output from "no nucleus exists". The
#: abort decouples the two, and the source project measured a low cap discarding
#: 18.8% of findable nuclei. This buys them back for roughly what the convergers'
#: own extra iterations cost.
NEWTON_STEPS = 600

#: Significant digits a nucleus key rounds its coordinates to.
DEDUP_DPS = 22

#: Below this magnitude a "nucleus" is the `c = 0` period-1 degenerate, not a
#: place. Refused rather than returned.
ORIGIN_EPS = mp.mpf("1e-6")

#: A coordinate component below this is Newton noise, not structure.
#:
#: Safe by an enormous margin in both directions: at 60 digits the solver leaves
#: noise near `1e-50`, while a genuine off-axis nucleus is separated from the
#: axis by something of the order of its own structure scale, never `1e-20`. A
#: real-axis nucleus has an imaginary part of exactly zero.
SNAP_EPS = mp.mpf("1e-20")

#: One nat, in bits — the rate Newton retires magnitude at, far from any root.
NEWTON_BITS_PER_STEP = 1.4426950408889634

#: The divergence abort fires only this far above the provable requirement.
DIVERGENCE_SAFETY = 4.0

#: Pixel spacing below which `f64` samples quantize: two neighbouring pixel
#: centers round to the same number and the render stops being of the set.
SPACING_FLOOR = 1e-13

#: The presentation a finished wallpaper is rendered at, which the feasibility
#: figure is quoted against.
DEPLOY_WIDTH, DEPLOY_SUPERSAMPLE = 1280, 4

#: Frame width, in atom sizes, that a nucleus-centered view is framed at.
#:
#: A nucleus sits *inside* its own atom, which is interior and therefore black:
#: at `fw = size` the frame is mostly body, and below that it is entirely body.
#: Four sizes frames the atom as a small island ringed by its decorations, which
#: is both what the eye wants and what the gates can measure.
FRAME_MULTIPLE = 4.0

#: Decades of `f64` headroom an atom must have to be worth sourcing.
#:
#: A safety rail, not a selector: measured over 163 atoms in the source project
#: it excluded three, and the median admitted margin was 6.66 decades. It only
#: becomes a selector against a supply that deliberately reaches the small, deep
#: tail — which nothing here does yet.
MARGIN_MIN_DECADES = 1.0


def set_precision() -> None:
    """Put mpmath at this module's working precision."""
    mp.mp.dps = NUCLEUS_DPS


def orbit(c, steps: int, degree: int = 2):
    """`(z_n, dz_n/dc)` after `steps` of the critical orbit at parameter `c`.

    ```text
    z₀ = 0        z_{k+1} = z_k^d + c
    d₀ = 0        d_{k+1} = d · z_k^(d−1) · d_k + 1
    ```

    The derivative rides along because Newton needs it and it costs one multiply
    on top of an orbit that is being walked anyway.
    """
    z = mp.mpc(0)
    d = mp.mpc(0)
    if degree == 2:
        for _ in range(steps):
            d = 2 * z * d + 1
            z = z * z + c
    else:
        for _ in range(steps):
            power = z ** (degree - 1)
            d = degree * power * d + 1
            z = power * z + c
    return z, d


def divergence_bound(remaining_steps: int, safety: float = DIVERGENCE_SAFETY) -> float:
    """The magnitude, in bits, above which a solve provably cannot finish.

    Far from every root of a degree-`n` polynomial, Newton moves `c → c(1−1/n)`,
    so `|P|` shrinks by `(1−1/n)ⁿ → 1/e`: the iteration retires exactly **one nat
    per step**, whatever the period, the degree, or the starting point. A solve
    whose residual is `|z_p|` therefore needs at least `ln|z_p|` further steps
    before it can even reach `O(1)`. If that exceeds the budget the caller gave,
    the solve cannot converge and every remaining step is certain waste.

    **This is why the rule is phrased against the budget and not as a magnitude
    threshold.** A flat threshold was tried first and is wrong: there are real
    convergers that sit at `|z_p| ≈ 10⁶⁶` for a hundred and fifty iterations
    before turning, and any bound low enough to catch the burners at a tight
    budget kills those at a generous one. The feasibility form scales, so one
    rule is correct for both callers.

    Magnitude is read in bits — `mp.mag` is an exponent read, about twenty-five
    times cheaper than a logarithm, and this runs on every iteration of every
    solve. `safety` is headroom rather than a fit: it is free, because a solve
    that is going to diverge sits tens of thousands of nats above the bound.
    """
    return safety * NEWTON_BITS_PER_STEP * remaining_steps


@dataclass
class Solve:
    """What one Newton solve did."""

    c: object
    converged: bool
    steps: int
    #: `log₁₀|z_p(c)|` at the final iterate.
    residual_log10: float
    period: int
    degree: int
    #: The solve stopped because its residual could not be retired in the budget.
    diverged: bool = False


def newton_nucleus(
    c0, period: int, *, degree: int = 2, max_steps: int = NEWTON_STEPS, tol_dps_margin: int = 6
) -> Solve:
    """Newton on `z_p(c) = 0`: the period-`p` nucleus nearest `c0`.

    Non-convergence is the normal outcome, not an error — most seeds are not
    near a nucleus of the period being asked about. Callers discard a
    non-converged solve without reading its coordinate.
    """
    c = mp.mpc(c0)
    tolerance = mp.mpf(10) ** (-(mp.mp.dps - tol_dps_margin))
    residual = mp.inf
    diverged = False
    step_count = 0
    for step_count in range(1, max_steps + 1):
        z, d = orbit(c, period, degree)
        if mp.mag(z) > divergence_bound(max_steps - step_count):
            diverged = True
            residual = abs(z)
            break
        residual = abs(z)
        if d == 0:
            break
        step = z / d
        c = c - step
        if abs(step) < tolerance and residual < tolerance:
            break
    if not diverged:
        # `c` moved after `residual` was taken, so the residual has to be
        # re-measured at the final iterate. On the abort path `c` did *not*
        # move, so the residual already is `|z_p(c)|` — and skipping the
        # recompute skips the single most expensive orbit pass in the solve, the
        # escaped one whose exponents are what cost the arbitrary-precision work.
        z, _ = orbit(c, period, degree)
        residual = abs(z)
    return Solve(
        c=c,
        converged=bool(residual < tolerance and not diverged),
        steps=step_count,
        residual_log10=float(mp.log10(residual)) if residual > 0 else -999.0,
        period=period,
        degree=degree,
        diverged=diverged,
    )


def is_minimal(c, period: int, degree: int = 2) -> bool:
    """Whether `period` is the nucleus's true period rather than a multiple.

    Newton at a multiple of the real period converges perfectly well and returns
    the same point, so without this check the same atom is recorded once per
    multiple of its period, each time under a different and wrong period.
    """
    tolerance = mp.mpf(10) ** (-(mp.mp.dps - 6))
    return all(
        abs(orbit(c, q, degree)[0]) >= tolerance for q in range(1, period) if period % q == 0
    )


def canonical_nucleus_c(c, degree: int):
    """Rotate `c` into the fundamental sector of the family's own symmetry.

    `z^d + c` has `(d−1)`-fold rotational symmetry about the origin: `c` and
    `c·ω^k` with `ω = exp(2πi/(d−1))` are the *same atom* seen through the
    conjugacy `z → ωz` — same period, same size, a rotated field. A key built
    from raw coordinates cannot see that, so the rotational copies survive as
    separate "atoms" and every distinct-atom count is inflated by up to `d−1`.

    Unwinding whole sectors is itself one of those symmetry rotations, so the
    atom is unchanged by it. **Degree 2 is one-fold — the sector is the whole
    plane — so this is the identity there, explicitly and not by accident.**
    """
    c = mp.mpc(c)
    if degree <= 2 or c == 0:
        return c
    sector = 2 * mp.pi / (degree - 1)
    sectors = mp.floor(mp.arg(c) / sector)
    angle = -sector * sectors
    return c * mp.mpc(mp.cos(angle), mp.sin(angle))


def snap_near_zero(c):
    """Zero a coordinate component that is below [`SNAP_EPS`].

    A key rounds to significant digits, so a real-axis nucleus whose imaginary
    part is Newton noise stringifies differently on every solve — and one atom
    enters a population many times, once per seed that found it.
    """
    c = mp.mpc(c)
    return mp.mpc(
        mp.mpf(0) if abs(c.real) < SNAP_EPS else c.real,
        mp.mpf(0) if abs(c.imag) < SNAP_EPS else c.imag,
    )


def nucleus_key(c, degree: int, dps: int = DEDUP_DPS) -> str:
    """The canonical name of the atom at `c`: symmetry-folded, de-noised, rounded.

    Working precision is lifted well above the rounding so the rounding is
    meaningful — but the *caller* must have parsed `c` at adequate precision to
    begin with. A coordinate parsed as an `f64` has already lost its tail before
    it arrives here, and no amount of precision downstream puts it back.
    """
    with mp.workdps(max(mp.mp.dps, dps + 15)):
        folded = snap_near_zero(canonical_nucleus_c(c, degree))
        return f"{degree}:{mp.nstr(folded.real, dps)},{mp.nstr(folded.imag, dps)}"


def key_from_strings(center_re: str, center_im: str, degree: int, dps: int = DEDUP_DPS) -> str:
    """The canonical name, from stored decimal strings.

    **Normalization happens here, at the reader.** A ledger's coordinates are
    strings written by whoever wrote them; folding and snapping on the way *in*
    would mean trusting every writer to have done it the same way, and a writer
    that gets it wrong leaves rows that can never be reconciled afterwards. Read
    the strings at full precision and canonicalize on the way out, and a row
    written by an older or sloppier writer still lands on the right atom.
    """
    with mp.workdps(max(mp.mp.dps, dps + 15)):
        c = mp.mpc(mp.mpf(str(center_re)), mp.mpf(str(center_im)))
        return nucleus_key(c, degree, dps)


@dataclass
class Atom:
    """The atom at a nucleus: how big it is, which way up, and what it costs."""

    degree: int
    period: int
    #: `|A|`, the atom's inverse linear scale.
    abs_a: float
    log10_abs_a: float
    #: `arg A`, determined only modulo the ambiguity below.
    arg_a: float
    #: Frame width that frames the whole atom: `1/|A|`.
    window_scale: float
    #: `−arg A`.
    rotation: float
    #: `2π/(d−1)`: which of the `d−1` rotational copies this is. Zero at `d = 2`.
    rotation_ambiguity: float
    #: Decimal digits needed to localize a `1/|A|` frame.
    required_dps: int

    def f64_margin(
        self,
        width: int = DEPLOY_WIDTH,
        supersample: int = DEPLOY_SUPERSAMPLE,
        multiple: float = FRAME_MULTIPLE,
        spacing_floor: float = SPACING_FLOOR,
    ) -> float:
        """Decades of headroom before a `multiple × size` frame quantizes in `f64`.

        Pixel spacing at that framing is `multiple / (|A| · width · ss)`, and the
        wall is `spacing_floor`. **Negative predicts a failed render before any
        render is attempted** — which is how the source project discovered the
        wall in the first place, by rendering eight frames that came back
        quantized.
        """
        wall = math.log10(multiple) - math.log10(spacing_floor) - math.log10(width * supersample)
        return wall - self.log10_abs_a

    def feasible(self, **presentation) -> bool:
        """Whether this atom clears the feasibility rail at that presentation."""
        return self.f64_margin(**presentation) >= MARGIN_MIN_DECADES


def atom_instrument(c, period: int, degree: int = 2, *, guard_digits: int = 15) -> Atom:
    """Measure the atom at nucleus `(c, period)`, from one orbit pass.

    ```text
    z_{k+1} = z_k^d + c
    z'_{k+1} = d·z_k^(d−1)·z'_k + 1                z'₀ = 0
    Λ        = Π_{k=1..n−1} d·z_k^(d−1)
    A        = Λ^(1/(d−1)) · z'_n
    ```

    Near a period-`n` nucleus the `n`-fold iterate conjugates to `w^d + C`, and
    the embedded copy is the whole multibrot pulled back by `C/A`. So `|A|` is
    the atom's inverse linear scale and `arg A` its orientation, and both fall
    out of quantities Newton already forms.

    **The exponent on `Λ` is `d/(d−1)`, and this is the trap.** Written flat as
    `Λ²` — correct at degree 2, where `d/(d−1)` *is* 2 — it under-sizes a degree
    `d ≥ 3` atom by a factor that starts around four and grows without bound with
    depth. Every frame built from the wrong law lands *inside* the atom's body
    and renders solid black. The law here is the general one, and `d = 2` is a
    case of it rather than an exception to it.

    The `(d−1)`-th root leaves `arg A` determined only modulo `2π/(d−1)`: that is
    an ambiguity about which of the rotational copies this is, not an error, and
    it is recorded alongside rather than resolved.
    """
    c = mp.mpc(c)
    z = mp.mpc(0)
    derivative = mp.mpc(0)
    multiplier = mp.mpc(1)
    for k in range(1, period + 1):
        if degree == 2:
            derivative = 2 * z * derivative + 1
            z = z * z + c
        else:
            power = z ** (degree - 1)
            derivative = degree * power * derivative + 1
            z = power * z + c
        if k <= period - 1:
            # The product excludes the critical point itself, where z = 0.
            multiplier = multiplier * (degree * z ** (degree - 1))
    a = multiplier ** (mp.mpf(1) / (degree - 1)) * derivative

    abs_a = float(abs(a)) if a != 0 else 0.0
    log10_abs_a = float(mp.log10(abs(a))) if a != 0 else float("inf")
    return Atom(
        degree=degree,
        period=period,
        abs_a=abs_a,
        log10_abs_a=log10_abs_a,
        arg_a=float(mp.arg(a)),
        window_scale=(1.0 / abs_a if abs_a > 0 else float("inf")),
        rotation=-float(mp.arg(a)),
        rotation_ambiguity=(2.0 * math.pi / (degree - 1) if degree > 2 else 0.0),
        required_dps=(
            max(NUCLEUS_DPS, int(math.ceil(log10_abs_a)) + guard_digits)
            if abs_a > 0
            else NUCLEUS_DPS
        ),
    )


#: How many significant digits a nucleus coordinate is written with.
#:
#: Enough to localize a frame four decades below the walk's own width floor, so
#: a stored nucleus does not have to be re-solved to be re-framed deeper later.
EMIT_DIGITS = 35


def make_atom(c, period: int, degree: int = 2) -> dict | None:
    """Canonicalize a nucleus and build its record, or `None` if it is degenerate.

    Degenerate means one of three things and never means "infeasible": the atom
    sits at the origin, the period is not minimal, or the instrument came back
    non-finite. **The feasibility margin is recorded and the atom is kept** —
    the rail belongs to whoever is sourcing, not to the record of what exists.
    """
    c = mp.mpc(c)
    if abs(c) < ORIGIN_EPS:
        return None
    folded = snap_near_zero(canonical_nucleus_c(c, degree))
    if not is_minimal(folded, period, degree):
        return None
    atom = atom_instrument(folded, period, degree)
    if not math.isfinite(atom.log10_abs_a) or atom.abs_a <= 0:
        return None
    return {
        "key": nucleus_key(folded, degree),
        "degree": degree,
        "period": period,
        "center_re": mp.nstr(folded.real, EMIT_DIGITS, strip_zeros=False),
        "center_im": mp.nstr(folded.imag, EMIT_DIGITS, strip_zeros=False),
        "window_scale": atom.window_scale,
        "log10_abs_A": round(atom.log10_abs_a, 6),
        "arg_A": round(atom.arg_a, 6),
        "required_dps": atom.required_dps,
        "f64_margin_decades": round(atom.f64_margin(), 4),
    }


def period_candidates(
    c, degree: int, max_period: int = 64, keep: int = 4, max_solves: int | None = None
) -> list[int]:
    """Periods worth trying at `c`, in the order Newton should try them.

    Along the critical orbit of a parameter inside a period-`p` component's atom
    domain, `|z_k|` is small at `k = p`. So one orbit pass ranks every period at
    once, and Newton runs a handful of times instead of sweeping the range —
    which is the difference between an operator that can fire on every rung and
    one that cannot.

    **The argmin is a multiple of the period, not the period, and taking it
    directly fails silently.** A nucleus is superattracting, so just off it
    `|z_{2p}| ≈ |z_p|²  ≪ |z_p|`, and the global minimum lands on a high multiple
    of `p` — never on `p`. Newton at that multiple returns a non-minimal
    solution, which is then rejected as degenerate, and the operator reports
    "nothing here" on a view squarely on top of a perfectly good atom. So the
    candidates are the argmins' **divisors**, tried smallest first: the smallest
    period is the largest containing component.

    Period 1 is skipped — its nucleus is `c = 0`, which is refused anyway. The
    orbit is walked in `f64` and truncated at escape: this is a *ranking*, Newton
    refines at full precision, and past escape the values say nothing about any
    atom domain.
    """
    z = complex(0.0, 0.0)
    point = complex(float(c.real), float(c.imag)) if hasattr(c, "real") else complex(c)
    escape = 2.0 ** (1.0 / max(degree - 1, 1)) * 2.0
    seen: list[tuple[float, int]] = []
    for k in range(1, max_period + 1):
        z = (z * z + point) if degree == 2 else (z**degree + point)
        magnitude = abs(z)
        if not math.isfinite(magnitude) or magnitude > escape:
            break
        seen.append((magnitude, k))
    if not seen:
        return []
    seen.sort()
    candidates: set[int] = set()
    for _magnitude, multiple in seen[: max(1, keep)]:
        candidates.update(d for d in range(2, multiple + 1) if multiple % d == 0)
    return sorted(candidates)[: max_solves or (3 * max(1, keep))]


def identify_nucleus(
    seed,
    *,
    degree: int = 2,
    near: float = 1e-2,
    periods: list[int] | None = None,
    period_max: int = 64,
    max_steps: int = NEWTON_STEPS,
) -> tuple[dict | None, str]:
    """The atom a point sits on: `(record, status)`.

    Tries each candidate period, keeps the first that converges to a minimal
    nucleus within `near` of the seed, and stops there — **smallest period
    wins**, because the smallest period is the largest component containing the
    point, and that is the atom the point is "on".

    `periods` is the ranked candidate list from [`period_candidates`]. Without
    it the whole range is swept, which is one full Newton solve per period and
    was measured as the single largest cost in the source project's operator
    set. The sweep is kept as the reference the ranked path is checked against.
    """
    seed = mp.mpc(seed)
    near = mp.mpf(str(near))
    for period in periods if periods is not None else range(1, period_max + 1):
        solve = newton_nucleus(seed, int(period), degree=degree, max_steps=max_steps)
        if not solve.converged or abs(solve.c - seed) > near:
            continue
        record = make_atom(solve.c, int(period), degree)
        if record is not None:
            record["seed_distance"] = float(abs(solve.c - seed))
            return record, "ok"
    return None, "no_nucleus_near_seed"
