"""How deep this mode goes, and what that costs in digits and in `f64` headroom.

Three questions have one answer each, and all three are answered here so that no
other module in the deep mode holds a number about depth.

* **How deep may a frame go?** [`MIN_WIDTH`], and it is a policy — two decades
  below the shallow walk's floor, chosen against a measured wall rather than
  against the shallow floor's own provenance.
* **How is a nucleus framed?** The band, in atom sizes: [`BAND_TOP`] down to
  [`BAND_FLOOR`], with the money shot at [`MONEY_SHOT`]. That law is the whole
  of the harvest's geometry.
* **Can `f64` still draw it?** [`resolution_ulps`], which mirrors the engine's
  own refusal so a seat can be refused before anything is rendered.

## The floor is a policy, and the wall is a measurement

They are two different numbers and the difference is the point. The **wall** is
where `f64` stops resolving a view: neighbouring sample centers round to the
same coordinate, and the render becomes a picture of the arithmetic. It is
*relative* — it moves with the magnitude of the coordinates — and at a finished
wallpaper's geometry it falls between about `2e-12` and `9e-12` over the parts
of the plane a location can sit in.

The **floor** is where this mode decides to stop. `1e-11` sits between one and
two decades above the shallow floor's material and a factor of a few above the
wall's worst case, which is thin enough to be checked per seat rather than
assumed — see [`releasable`]. Nothing here widens a coordinate: the walk, the
score and the release are all `f64` end to end, and the arbitrary precision in
[`fractal_wallpapers.deep.centers`] exists only to *localize* a center, never to
render one.

## The band is a framing law, not a search

A nucleus sits inside its own atom, which is interior and therefore black, so
the frame that shows an atom is a multiple of its size and never a fraction of
it. Below [`BAND_FLOOR`] the atom fills the frame; above [`BAND_TOP`] the atom
is a speck in a view of its parent. The money shot is the framing that reads as
a picture: an island ringed by its decorations.

That is also why depth here comes from *which atom* rather than from how far a
walk descended. A seat is admissible when its own band lands below the shallow
floor and above [`MIN_WIDTH`], which is one inequality on the atom's size and is
the whole of [`SEAT_SIZES`].
"""

from __future__ import annotations

import math
import struct

from fractal_wallpapers.discovery import walk as walk_module

#: The deepest frame this mode will draw. Two decades below the shallow walk's
#: own floor.
#:
#: The basis is measured, not inherited. `measure_deep_probe` bisected for the
#: width at which adjacent sample centers first round together at a finished
#: wallpaper's geometry and found `1.42e-13` to `2.27e-12` depending on the
#: center's magnitude, with `≈4.5e-12` the worst case anywhere the set reaches.
#: `1e-11` is above all of it — but only by a factor of a few at the large-`|c|`
#: end, which is why [`releasable`] is a per-seat check and not a comment.
MIN_WIDTH = 1e-11

#: The shallow walk's floor, read from the walk rather than restated.
#:
#: It is not a bound on anything here; it is the line that makes a seat *deep*.
#: A nucleus whose money shot is above it is material the ordinary walk can
#: already reach, and this mode has no business spending a seat on it.
SHALLOW_MIN_WIDTH = walk_module.Gates().min_width

#: The widest framing of a nucleus the band holds, in atom sizes: the atom as a
#: small feature of its own neighbourhood.
BAND_TOP = 40.0

#: The framing a nucleus is worth looking at, in atom sizes.
MONEY_SHOT = 4.0

#: The narrowest framing of a nucleus the band holds, in atom sizes. Below this
#: the atom's own black body is most of the frame.
BAND_FLOOR = 2.0

#: The framings a seat contributes as roots, widest first.
#:
#: Two rather than the whole band: the top is where the walk gets to descend
#: through the band under its own policy, and the money shot is the frame that
#: is a picture, stood on directly rather than hoped for. Everything between
#: them the walk reaches by rung.
ROOT_FRAMINGS = (BAND_TOP, MONEY_SHOT)

#: Representable numbers a sample step must span before the engine refuses.
#:
#: A mirror of `engine/src/viewport.rs`'s `RESOLUTION_ULPS`, and the only copy of
#: it on this side. A mirror rather than a door because the question is asked
#: about *seats that do not exist yet* — a hundred candidate atoms before any of
#: them is framed — and a subprocess per answer is not a thing sourcing can
#: afford. `tests/test_deep_depth.py` holds the two honest against each other by
#: bisecting the engine's real refusal, which is the same discipline
#: `engine.DYNAMICAL_KINDS` is kept under.
RESOLUTION_ULPS = 4.0

#: What a finished wallpaper is drawn at, which the seat check is quoted against.
#:
#: Read from curation rather than restated: a seat admitted against the wrong
#: geometry is a picture that fails at the last step of the run that made it.
RELEASE_RESOLUTION = (2560, 1440)
RELEASE_SUPERSAMPLE = 4


def band(size: float) -> tuple[float, float]:
    """`(top, floor)` — the framings a nucleus of this size is worth seeing at."""
    return BAND_TOP * float(size), BAND_FLOOR * float(size)


def money_shot(size: float) -> float:
    """The framing of this nucleus that is a picture rather than a diagram."""
    return MONEY_SHOT * float(size)


#: The atom sizes a seat may have: its money shot below the shallow floor, its
#: band floor above this mode's own. One inequality, stated once.
SEAT_SIZES = (MIN_WIDTH / BAND_FLOOR, SHALLOW_MIN_WIDTH / MONEY_SHOT)


def seats_this_size(size: float) -> bool:
    """Whether an atom of this size is one this mode is for."""
    low, high = SEAT_SIZES
    return math.isfinite(size) and low <= float(size) <= high


def ulp(value: float) -> float:
    """The distance from `value` to the next representable `f64` above it.

    The same answer `f64::from_bits(x.to_bits() + 1) - x` gives in the engine,
    written here through `struct` because Python's floats have no bit view of
    their own. Zero and the subnormals answer with the smallest positive `f64`,
    which is their true spacing.
    """
    value = abs(float(value))
    if not math.isfinite(value):
        return 1.0
    (bits,) = struct.unpack("<Q", struct.pack("<d", value))
    (nxt,) = struct.unpack("<d", struct.pack("<Q", bits + 1))
    return nxt - value


def resolution_ulps(
    center_re,
    center_im,
    width: float,
    pixels: int,
    supersample: int = 1,
    aspect: float = 9.0 / 16.0,
) -> float:
    """How many representable numbers one sample step of this view spans.

    The engine's whole `f64` question in one figure. Below `1` two neighbouring
    sample centers are the same number; below [`RESOLUTION_ULPS`] the engine
    refuses to draw the view at all.

    The magnitude used is the frame's *reach* rather than its center, because a
    sample coordinate is formed as `center + across × width` and it is the
    magnitude of that sum that decides what it rounds to.
    """
    width = float(width)
    step = width / (int(pixels) * int(supersample))
    if not math.isfinite(step) or step <= 0.0:
        return 0.0
    reach = max(
        abs(float(center_re)) + abs(width) / 2.0,
        abs(float(center_im)) + abs(width * aspect) / 2.0,
    )
    return step / ulp(reach)


def releasable(center_re, center_im, width: float) -> bool:
    """Whether `f64` still resolves this view at a finished wallpaper's geometry.

    **The check that decides whether a seat is worth taking**, and it is asked at
    the release geometry rather than the walk's because that is the one that runs
    out first: sixteen samples per output pixel over 2560 of them is a grid
    twenty-seven times finer than a walk node's. A seat whose money shot fails
    here is a seat whose every find would be refused at the last step of the run
    that made it.
    """
    return (
        resolution_ulps(center_re, center_im, width, RELEASE_RESOLUTION[0], RELEASE_SUPERSAMPLE)
        >= RESOLUTION_ULPS
    )


def deepest_releasable_width(center_re, center_im) -> float:
    """The narrowest frame `f64` can still draw here, at the release geometry.

    Reported alongside a seat so a refusal says *how far short* rather than only
    that it was short — and so the report can say which parts of the plane this
    mode's floor is actually reachable in.
    """
    samples = RELEASE_RESOLUTION[0] * RELEASE_SUPERSAMPLE
    magnitude = max(abs(float(center_re)), abs(float(center_im)))
    return RESOLUTION_ULPS * ulp(magnitude) * samples


__all__ = [
    "BAND_FLOOR",
    "BAND_TOP",
    "MIN_WIDTH",
    "MONEY_SHOT",
    "RELEASE_RESOLUTION",
    "RELEASE_SUPERSAMPLE",
    "RESOLUTION_ULPS",
    "ROOT_FRAMINGS",
    "SEAT_SIZES",
    "SHALLOW_MIN_WIDTH",
    "band",
    "deepest_releasable_width",
    "money_shot",
    "releasable",
    "resolution_ulps",
    "seats_this_size",
    "ulp",
]
