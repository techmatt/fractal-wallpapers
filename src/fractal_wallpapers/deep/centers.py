"""Newton on a nucleus, at the precision that nucleus actually needs.

The deep mode's roots are *produced*, not found: a walk cannot descend to a
place it cannot localize, and below the shallow floor `f64` has lost the digits
that say where an atom is. So a deep center comes off a Newton solve in
arbitrary precision and travels as **decimal strings** — through the ledger,
through the render spec, into the engine's own parser — and nothing on the way
narrows it.

[`fractal_wallpapers.discovery.nucleus`] already holds the solve, the atom
instrument and the canonical key. What this module adds is the two things a
*deep* center needs that a shallow reframing does not.

**The working precision is sized by the answer, not by a constant.** `nucleus`
runs every solve at a flat 60 decimal digits, and `Atom.required_dps` — the
precision an atom of that size actually needs — has been computed and recorded
and never acted on. Here it is acted on: a solve runs, the atom is measured, and
if the atom asks for more digits than the solve had, the solve is *redone* at
that precision and the atom re-measured, until the answer stops asking. At this
mode's depths it never asks — `required_dps` first exceeds 60 at `log₁₀|A| > 45`,
which is an atom about thirty decades smaller than anything here frames — so the
enforcement is a guarantee rather than a cost, and [`solve`] records the
precision it settled at so a later reading can see that for itself rather than
taking this paragraph's word for it.

**A center is written with digits sized for the frame it will carry.** The
shallow store writes 35 significant digits, which localizes a frame four decades
below the shallow floor; a deep center says which width it is for and gets the
digits for that plus a guard. Both are far more than `f64` can hold, and that is
the point — the string is the identity, and the `f64` view of it is made fresh
at each render.

Degree-general throughout: the size law's exponent is `d/(d−1)` and lives in
[`fractal_wallpapers.discovery.nucleus.atom_instrument`], which is where the
`d = 2` case is a case of the rule rather than an exception to it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mpmath as mp

from fractal_wallpapers.deep import depth
from fractal_wallpapers.discovery import nucleus as nuc

#: Digits above what a frame strictly needs, on the working precision.
#:
#: Generous, and free: a Newton solve converges quadratically, so the last
#: doubling of precision is a single extra step and the guard costs one
#: iteration rather than a proportion of the run.
WORKING_GUARD = 30

#: Digits above what a frame strictly needs, on the *written* center.
#:
#: Smaller than the working guard on purpose. A stored center is re-parsed to
#: `f64` at every render, so digits past the frame's own scale buy re-framing
#: room later and nothing else — and a row that is mostly zeros is a row that is
#: hard to read.
EMIT_GUARD = 15

#: Newton steps a deep solve is allowed.
#:
#: **Below [`fractal_wallpapers.discovery.nucleus.NEWTON_STEPS`], and that is a
#: measurement rather than thrift.** The divergence abort fires when a solve's
#: residual could not be retired *in the steps it has left*, so the budget is
#: also the abort's own threshold: raising it lets every burner run longer
#: before the abort can see it. On one ladder step over 24 probes of a degree-4
#: period-29 atom, a budget of 1200 cost 44 s and a budget of 150 cost 5.8 s
#: for the byte-identical five children — the convergers ran 9 to 16 iterations
#: at both. 200 is the observed maximum an order of magnitude over.
NEWTON_STEPS = 200


def working_dps(width: float, guard: int = WORKING_GUARD) -> int:
    """Decimal working precision that localizes a frame of `width`.

    Never below [`fractal_wallpapers.discovery.nucleus.NUCLEUS_DPS`], so a deep
    solve is never *less* precise than a shallow one — the sizing is a floor that
    rises with depth, not a budget that falls with it.
    """
    width = float(width)
    need = int(math.ceil(-math.log10(width))) if width > 0 else 20
    return max(nuc.NUCLEUS_DPS, need + int(guard))


def emit_digits(width: float, guard: int = EMIT_GUARD) -> int:
    """Significant digits a center is written with, to carry a frame of `width`."""
    width = float(width)
    need = int(math.ceil(-math.log10(width))) if width > 0 else 20
    return max(nuc.EMIT_DIGITS, need + int(guard))


@dataclass(frozen=True)
class DeepCenter:
    """A nucleus, its atom, and the band that atom is worth seeing in.

    The coordinates are decimal strings and are the identity of the place; every
    other field is a measurement about it, and every width is an `f64` because a
    width is a scale rather than a position.
    """

    degree: int
    period: int
    center_re: str
    center_im: str
    #: The canonical name of this atom — the same key a reframing would give it.
    key: str
    #: `1/|A|`: the atom's own linear scale.
    size: float
    log10_abs_a: float
    #: `[top, floor]` — the framings this nucleus is worth seeing at.
    band: tuple[float, float]
    #: The framing that is a picture: `4 × size`.
    money_shot: float
    #: The precision the solve settled at, and the precision the atom asked for.
    solved_dps: int
    required_dps: int
    #: `log₁₀|z_p(c)|` at the final iterate.
    residual_log10: float
    newton_steps: int
    #: Sample steps per unit of last place at the money shot, at release geometry.
    release_ulps: float

    def record(self) -> dict:
        """This center as a ledger row carries it."""
        return {
            "degree": self.degree,
            "period": self.period,
            "center_re": self.center_re,
            "center_im": self.center_im,
            "key": self.key,
            "size": self.size,
            "log10_abs_A": round(self.log10_abs_a, 6),
            "band": [self.band[0], self.band[1]],
            "money_shot": self.money_shot,
            "solved_dps": self.solved_dps,
            "required_dps": self.required_dps,
            "residual_log10": round(self.residual_log10, 4),
            "newton_steps": self.newton_steps,
            "release_ulps": round(self.release_ulps, 3),
        }

    @property
    def reflection_key(self) -> str:
        """The atom's name, with the plane's own mirror symmetry folded in too.

        `z^d + c` has real coefficients, so the field at `c̄` is the field at `c`
        reflected in the real axis: the same atom, the same period, the same
        size, a picture flipped. [`key`] does not fold that —
        [`fractal_wallpapers.discovery.nucleus.nucleus_key`] folds the `(d−1)`-fold
        *rotational* symmetry only, which is the identity at degree 2 — and it
        should not, because two conjugate locations are two locations and a
        ledger that merged them would lose one.

        A **seat** is a different question. A run with eight places to stand
        should not spend two of them on one place seen in a mirror, and the
        shakedown did exactly that: two plane-seed anchors walked down to
        `0.36239432546177071060 ± 0.11661245803520617789`, one atom, twice.
        """
        with mp.workdps(nuc.NUCLEUS_DPS + nuc.DEDUP_DPS):
            folded = mp.mpc(mp.mpf(self.center_re), abs(mp.mpf(self.center_im)))
            return nuc.nucleus_key(folded, self.degree)

    def viewport(self, framing: float) -> dict:
        """This center framed at `framing × size`, as decimal strings.

        The width is written at the same digit count the center is, so a
        viewport is one object written one way rather than a precise center
        beside a re-formatted width.
        """
        width = float(framing) * self.size
        return {
            "center_re": self.center_re,
            "center_im": self.center_im,
            "width": f"{width:.9e}",
        }


class NotANucleus(RuntimeError):
    """A solve was asked for a nucleus that is not there, or not this one."""


def solve(
    seed,
    period: int,
    *,
    degree: int = 2,
    width: float = depth.MIN_WIDTH,
    max_steps: int = NEWTON_STEPS,
    max_lifts: int = 4,
) -> DeepCenter:
    """Newton to the period-`p` nucleus near `seed`, at the precision it needs.

    The loop is the enforcement. A solve runs at the precision `width` implies,
    the atom is measured off the answer, and `Atom.required_dps` is compared
    against what the solve actually had. If it asks for more, everything is done
    again at that precision — the solve *and* the measurement, because an atom
    measured at too few digits is not a reason to trust its own precision
    figure. `max_lifts` bounds that at a number no real atom approaches; it is
    there so a pathological instrument cannot spin.

    Raises [`NotANucleus`] when Newton does not converge, when the period is not
    minimal, or when the instrument comes back degenerate. Those are three
    different facts and each says so.
    """
    period = int(period)
    dps = working_dps(width)
    lifted = 0
    while True:
        with mp.workdps(dps):
            answer = nuc.newton_nucleus(mp.mpc(seed), period, degree=degree, max_steps=max_steps)
            if not answer.converged:
                raise NotANucleus(
                    f"Newton did not reach a period-{period} nucleus from this seed at "
                    f"{dps} digits: |z_p| bottomed at 1e{answer.residual_log10:.1f} after "
                    f"{answer.steps} steps"
                    + (" and the solve was aborted as divergent" if answer.diverged else "")
                )
            folded = nuc.snap_near_zero(nuc.canonical_nucleus_c(answer.c, degree))
            if not nuc.is_minimal(folded, period, degree):
                raise NotANucleus(
                    f"the point Newton reached closes at a divisor of {period}, so {period} "
                    f"is a multiple of its real period and this is not that atom"
                )
            atom = nuc.atom_instrument(folded, period, degree)
            if not math.isfinite(atom.log10_abs_a) or atom.abs_a <= 0:
                raise NotANucleus(
                    f"the atom instrument came back non-finite at period {period}, so this "
                    f"nucleus has no size to frame against"
                )
            # The one thing the shallow path computes and never acts on. Lifting
            # re-solves as well as re-measures: an atom read at too few digits
            # cannot be trusted about how many digits it needs.
            if atom.required_dps > dps and lifted < max_lifts:
                dps = int(atom.required_dps) + WORKING_GUARD
                lifted += 1
                continue
            digits = emit_digits(width)
            center_re = mp.nstr(folded.real, digits, strip_zeros=False)
            center_im = mp.nstr(folded.imag, digits, strip_zeros=False)
            key = nuc.nucleus_key(folded, degree)
        size = atom.window_scale
        return DeepCenter(
            degree=int(degree),
            period=period,
            center_re=center_re,
            center_im=center_im,
            key=key,
            size=size,
            log10_abs_a=atom.log10_abs_a,
            band=depth.band(size),
            money_shot=depth.money_shot(size),
            solved_dps=dps,
            required_dps=int(atom.required_dps),
            residual_log10=answer.residual_log10,
            newton_steps=answer.steps,
            release_ulps=depth.resolution_ulps(
                center_re,
                center_im,
                depth.money_shot(size),
                depth.RELEASE_RESOLUTION[0],
                depth.RELEASE_SUPERSAMPLE,
            ),
        )


def periods_near(
    seed, degree: int, period_max: int, keep: int = 4, period_min: int = 2
) -> list[int]:
    """Periods worth trying at `seed`, smallest first, above `period_min`.

    [`fractal_wallpapers.discovery.nucleus.period_candidates`] with both ends
    passed rather than defaulted. The ceiling is passed because a deep atom's
    period is a multiple of its parent's and the shallow default stops above
    where this mode starts and below where it ends.

    **The floor is what makes a descent possible at all.** A probe seed a few
    atom-widths from a nucleus is still inside that nucleus's own atom domain,
    which is enormously larger than the atom, so "the smallest period that
    converges near the seed" is the *parent* on almost every probe — the 88%
    miss rate the reframing operators measured. A child's period is strictly
    greater than its parent's, so asking above the parent's period is asking for
    the thing being looked for rather than filtering for it afterwards.
    """
    ranked = nuc.period_candidates(seed, degree, max_period=int(period_max), keep=int(keep))
    return [period for period in ranked if period >= int(period_min)]


def nearest(
    seed,
    *,
    degree: int = 2,
    period_max: int = 64,
    period_min: int = 2,
    near: float,
    width: float = depth.MIN_WIDTH,
    keep: int = 4,
    max_steps: int = NEWTON_STEPS,
) -> tuple[DeepCenter | None, str, int]:
    """`(center, why-not, solves)` — the atom `seed` sits on, smallest period first.

    The smallest period that converges *within `near` of the seed* wins, because
    the smallest period is the largest component containing the point and that is
    the atom the point is "on".

    **`near` is not optional and it is what makes this a descent.** Newton from a
    seed deep in a minibrot's decorations converges perfectly well onto a
    period-3 giant a tenth of a plane away, and that giant is the largest
    component containing the seed by a wide margin. Without the bound every probe
    hands back an ancestor and the ladder cannot take a single step down.
    """
    with mp.workdps(working_dps(width)):
        seed = mp.mpc(seed)
        limit = mp.mpf(str(near))
        candidates = periods_near(seed, degree, period_max, keep, period_min)
    if not candidates:
        # Two different facts, and only one of them says the seed is a bad
        # place to look: an orbit that escaped at once is far exterior, while a
        # ranking with nothing above the parent's period is this ladder having
        # run out of reach at a perfectly good seed.
        with mp.workdps(working_dps(width)):
            ranked = periods_near(seed, degree, period_max, keep)
        why = "orbit_escaped_immediately" if not ranked else "no_period_above_the_parent"
        return None, why, 0
    refusal = "no_converge"
    for solves, period in enumerate(candidates, start=1):
        try:
            found = solve(seed, period, degree=degree, width=width, max_steps=max_steps)
        except NotANucleus as why:
            refusal = refusal_of(str(why))
            continue
        with mp.workdps(working_dps(width)):
            here = mp.mpc(mp.mpf(found.center_re), mp.mpf(found.center_im))
            if abs(here - seed) > limit:
                refusal = "nucleus_outside_the_probe"
                continue
        return found, "", solves
    return None, refusal, len(candidates)


def refusal_of(message: str) -> str:
    """The named reason behind a [`NotANucleus`], for a tally that can be read."""
    if "not minimal" in message or "real period" in message:
        return "not_minimal"
    if "non-finite" in message:
        return "degenerate_instrument"
    return "no_converge"


__all__ = [
    "EMIT_GUARD",
    "NEWTON_STEPS",
    "WORKING_GUARD",
    "DeepCenter",
    "NotANucleus",
    "emit_digits",
    "refusal_of",
    "nearest",
    "periods_near",
    "solve",
    "working_dps",
]
