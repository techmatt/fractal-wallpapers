"""How deep this mode goes, and what that costs in digits and in `f64` headroom.

Three questions have one answer each, and all three are answered here so that no
other module in the deep mode holds a number about depth.

* **How deep may a frame go?** [`min_width`], and it is a policy — two decades
  below the shallow walk's floor, chosen against a measured wall rather than
  against the shallow floor's own provenance, and raised one decade on the one
  plane whose arithmetic gives out visibly ([`DEGREE_MIN_WIDTH`]).
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

## And there is a third wall, above both, that this floor is aesthetic against

The coordinate wall is not where `f64` stops being *right*. A sample coordinate
can be perfectly distinct from its neighbour and the orbit run from it still be
decided by rounding — `julia_deep_eyetest`'s second addendum re-ran orbits at 50
digits and found escape counts wrong on 8–27% of sampled points at this floor,
on every plane this mode walks, with the onset anywhere from `1e-4` to `1e-10`
depending on the case. **The floor here does not chase that**, because on four
of the five measured cases none of it is visible: the picture is deterministic,
reproducible, and partly fictional in its finest texture, and it is judged as
art. The exception is degree 5, where wrong turns into *flat* — neighbouring
orbits collapse onto one value and the frame comes back a mosaic — and that is
what [`DEGREE_MIN_WIDTH`] raises the floor against. `deep/README.md` states the
contract; this module holds the number.

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

#: The deepest frame this mode will draw where a plane asks for nothing wider.
#: Two decades below the shallow walk's own floor.
#:
#: The basis is measured, not inherited. `measure_deep_probe` bisected for the
#: width at which adjacent sample centers first round together at a finished
#: wallpaper's geometry and found `1.42e-13` to `2.27e-12` depending on the
#: center's magnitude, with `≈4.5e-12` the worst case anywhere the set reaches.
#: `1e-11` is above all of it — but only by a factor of a few at the large-`|c|`
#: end, which is why [`releasable`] is a per-seat check and not a comment.
MIN_WIDTH = 1e-11

#: Floors that replace [`MIN_WIDTH`] on one plane, by multibrot degree.
#:
#: **Degree 5 stops a decade early, and the reason is the only visible failure
#: this mode has.** Every plane's escape counts are already partly wrong at
#: `1e-11` — measured against 50-digit orbits at 8.0%, 14.5% and 22.0% of
#: sampled points on the three planes `deep_run1` walked — and none of that
#: shows in a picture. Degree 5 fails differently: its neighbouring orbits do
#: not scatter, they *collapse*, and at `1e-11` two thirds of horizontally
#: adjacent samples come back bit-identical, which reads as a mosaic of flat
#: cells. Supersampling makes it worse rather than better (66.6% at ss1 rising
#: to 95.6% at ss8), because a finer grid puts the coordinates closer together
#: and closeness is exactly what the orbit cannot keep apart.
#:
#: `1e-10` is the rung above the onset, from the ladder in
#: `julia_deep_eyetest`'s second addendum. It is a floor on *plateau collapse*
#: and not on correctness: correctness is gone above it too, and the mode's
#: answer to that is the aesthetic contract in `deep/README.md`.
DEGREE_MIN_WIDTH = {5: 1e-10}


def min_width(degree: int | None = None) -> float:
    """The deepest frame this mode will draw on a plane of this degree.

    `None` is the mode's general floor — the answer where the question is asked
    about the window rather than about a plane. Every place that decides whether
    a *seat* exists asks with a degree.
    """
    if degree is None:
        return MIN_WIDTH
    return DEGREE_MIN_WIDTH.get(int(degree), MIN_WIDTH)


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

#: The names of the depth bands this mode's material is read in, deepest first.
#:
#: Three, over the two decades between [`MIN_WIDTH`] and [`SHALLOW_MIN_WIDTH`],
#: equal in log width. They exist because *a global rank does not reproduce the
#: window*: whichever way the scores happen to lean, one band ends up standing
#: for the whole mode, and the shakedown's own release is the measurement —
#: ranked by render score, its deepest release landed at `4.4x` this floor while
#: the mode's subject is the floor decade itself. A band is the unit a quota is
#: written in, and it is also the unit a *reading* is written in: an admission
#: rate quoted over the window says nothing about where in the window it holds.
BAND_NAMES = ("floor", "middle", "upper")


def bands() -> tuple[tuple[str, float, float], ...]:
    """`(name, low, high)` per band, deepest first — the window in equal log thirds."""
    ratio = (SHALLOW_MIN_WIDTH / MIN_WIDTH) ** (1.0 / len(BAND_NAMES))
    edges = [MIN_WIDTH * ratio**index for index in range(len(BAND_NAMES) + 1)]
    edges[-1] = SHALLOW_MIN_WIDTH
    return tuple((name, edges[index], edges[index + 1]) for index, name in enumerate(BAND_NAMES))


def band_of(width: float) -> str | None:
    """Which band a frame of this width sits in, or `None` if it is not deep.

    A frame above the shallow floor is material the ordinary walk can already
    reach — this mode draws such frames, because a seat's widest root framing is
    forty atom sizes — and one below this mode's floor should not exist at all.
    Both answer `None` rather than being folded into the nearest band, so a
    count of the bands is a count of the deep frames and nothing else.
    """
    width = float(width)
    for name, low, high in bands():
        if low <= width < high:
            return name
    return None


def band_ceiling(name: str) -> float:
    """The largest atom whose money shot lands in this band, for a ladder to aim at."""
    for band_name, _low, high in bands():
        if band_name == name:
            return high / MONEY_SHOT
    raise KeyError(name)


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


#: The atom sizes a seat may have where a plane asks for nothing wider: its
#: money shot below the shallow floor, its band floor above this mode's own. One
#: inequality, stated once — and [`seat_sizes`] is that same inequality read at a
#: plane's own floor.
SEAT_SIZES = (MIN_WIDTH / BAND_FLOOR, SHALLOW_MIN_WIDTH / MONEY_SHOT)


def seat_sizes(degree: int | None = None) -> tuple[float, float]:
    """The atom sizes a seat on a plane of this degree may have."""
    return (min_width(degree) / BAND_FLOOR, SHALLOW_MIN_WIDTH / MONEY_SHOT)


def seats_this_size(size: float, degree: int | None = None) -> bool:
    """Whether an atom of this size is one this mode is for, on this plane."""
    low, high = seat_sizes(degree)
    return math.isfinite(size) and low <= float(size) <= high


def open_bands(degree: int | None = None) -> tuple[str, ...]:
    """The depth bands a plane of this degree can be seated in, deepest first.

    A band lying wholly under a plane's own floor is not a thin cell to be aimed
    at and missed — it is a cell no descent on that plane can ever fill, and a
    sourcing round that keeps offering it spends real Newton descents on
    nothing. Degree 5 loses the `floor` band outright and keeps the part of
    `middle` above `1e-10`; every other plane keeps all three.
    """
    floor = min_width(degree)
    return tuple(name for name, _low, high in bands() if high > floor)


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
    "BAND_NAMES",
    "BAND_TOP",
    "DEGREE_MIN_WIDTH",
    "MIN_WIDTH",
    "MONEY_SHOT",
    "RELEASE_RESOLUTION",
    "RELEASE_SUPERSAMPLE",
    "RESOLUTION_ULPS",
    "ROOT_FRAMINGS",
    "SEAT_SIZES",
    "SHALLOW_MIN_WIDTH",
    "band",
    "band_ceiling",
    "band_of",
    "bands",
    "deepest_releasable_width",
    "min_width",
    "money_shot",
    "open_bands",
    "releasable",
    "resolution_ulps",
    "seat_sizes",
    "seats_this_size",
    "ulp",
]
