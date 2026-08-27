"""Palette space: how near two maps are, so a candidate set can be made tight.

A production candidate set is not a uniform draw. It is one palette *flavour's*
members — up to thirty-two maps that already resemble each other — and that is
why its top two candidates sit a twentieth of the set's own spread apart. A head
trained on uniform draws is never asked a question that fine, and the first
distillation pass measured exactly that failure: it reproduced the teacher's
order on the real sets at 0.89 and its top pick 46% of the time, and the median
miss was the teacher's *second* favourite winning.

The flavour taxonomy itself cannot be brought across — it is the source project's
own clustering artifact, computed over a library this repository holds a subset
of. What can be brought across is the *property* that makes those sets hard:
their members look alike. So this module measures that directly, off the maps
themselves, and [`neighbourhood`] builds a set that has it.

## The distance is between two gradients as the renderer spends them

A map is a ramp of colour stops. What the picture shows is that ramp swept once
across the escape-time field — and for a **sequential** map, swept out and back,
because a map that does not close on the colour it opened with is folded to hide
its seam. That fold is a property of the map, read off its `kind`, here as
everywhere else in this repository. So the descriptor samples the gradient *as
spent*: folded for a sequential map, plain for a cyclic one.

Thirty-two samples, each converted to **Oklab**, and the distance is Euclidean
over the resulting 96 numbers. Oklab rather than sRGB because sRGB distance is
not perceptual and the question here is whether two pictures look alike; a plain
RGB metric calls two dark maps near-identical and two bright ones far apart when
a viewer would say the opposite.

Nothing here is fitted or tuned. It is a fixed function of the tracked colormap
library, so a set drawn through it is reproducible from the repository alone.
"""

from __future__ import annotations

import json
from functools import lru_cache

from fractal_wallpapers.paths import colormap_dir

#: How many places along a gradient are compared. Thirty-two, which is both the
#: size of a production candidate set and fine enough that a map with one narrow
#: band of a different colour is not read as identical to one without it.
SAMPLES = 32


class SpaceError(RuntimeError):
    """A map cannot be placed in palette space."""


def _linearise(channel):
    """The sRGB transfer curve, undone. The arithmetic, on whatever it is handed."""
    import numpy

    channel = numpy.asarray(channel, dtype=numpy.float64) / 255.0
    return numpy.where(channel <= 0.04045, channel / 12.92, ((channel + 0.055) / 1.055) ** 2.4)


@lru_cache(maxsize=1)
def _linear_table():
    """The same curve, evaluated once at every code an sRGB8 channel can hold."""
    import numpy

    table = _linearise(numpy.arange(256))
    table.flags.writeable = False
    return table


def _srgb_to_linear(channel):
    """[`_linearise`], by table where the input says a table is exact.

    A `uint8` array is the whole of sRGB8 and nothing else: 256 codes, none
    fractional, none out of range. So the curve over one is a lookup into 256
    values the same expression produced, bit for bit — not an approximation of
    it, which is why no tolerance appears anywhere near this. The `**2.4` is
    where a tone measurement spent about a third of its clock, and a picture
    arrives as `uint8`; anything else — a gradient sampled between its stops,
    say — is fractional and takes the arithmetic.
    """
    import numpy

    values = numpy.asarray(channel)
    if values.dtype == numpy.uint8:
        return _linear_table()[values]
    return _linearise(values)


def _oklab_of_linear(red, green, blue):
    """Linear-light R, G, B to Oklab's three channels, as three separate arrays.

    Ottosson's matrices, unmodified, and **the one copy of them**. [`oklab`] is
    this plus a stack; [`lightness_and_chroma`] is this without one, because a
    caller that wants two of the three channels should not pay to build an array
    it immediately takes apart again.

    Every step is elementwise, which is the property the fast reader is built on:
    the result for a pixel is a function of that pixel alone, so how the caller
    sliced, strided or chunked its input cannot move a bit of the answer.
    """
    import numpy

    long = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    medium = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    long, medium, short = numpy.cbrt(long), numpy.cbrt(medium), numpy.cbrt(short)
    return (
        0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short,
        1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short,
        0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short,
    )


def oklab(rgb):
    """sRGB8 `[..., 3]` to Oklab `[..., 3]`. Ottosson's matrices, unmodified.

    Hand it the picture's own `uint8` and the linearisation is a table lookup;
    see [`_srgb_to_linear`].
    """
    import numpy

    linear = _srgb_to_linear(rgb)
    return numpy.stack(_oklab_of_linear(linear[..., 0], linear[..., 1], linear[..., 2]), axis=-1)


#: Pixels below which a tone reading is one pass. A thread pool costs a couple of
#: tenths of a millisecond to raise and a picture this small is about that long
#: in total, so splitting it would be most of the work.
READ_SERIAL_BELOW = 1 << 15

#: The most threads one picture's tone reading is split over.
#:
#: It is a share of the machine rather than the whole of it, because this runs
#: *beside* the render pool's three workers — `curation.manufacture` builds
#: candidates over three processes, and four threads in each of three is a
#: twelve-core desktop exactly. A machine with fewer cores gets proportionally
#: fewer threads and, below six, none at all, which is the same rule and not a
#: special case. Correctness does not depend on the number: every chunk's
#: arithmetic is elementwise, so one thread and four reach the same bytes.
READ_THREAD_CAP = 4

#: How many workers the reading assumes are beside it. The render pool's own
#: width, restated rather than imported: a palette module that reached into
#: `curation` to learn a number would be the wrong direction of dependency.
READ_POOL_WIDTH = 3


@lru_cache(maxsize=1)
def _read_threads() -> int:
    """How many threads this machine gives one tone reading."""
    import os

    return max(1, min(READ_THREAD_CAP, (os.cpu_count() or 1) // READ_POOL_WIDTH))


def lightness_and_chroma(rgb):
    """A picture's Oklab lightness and chroma, flat and contiguous, read in parallel.

    Exactly `oklab(rgb)[..., 0]` and the hypot of the other two, flattened —
    and *exactly* is the word, not *near*. Every operation between a pixel's
    three bytes and its two numbers is elementwise ([`_oklab_of_linear`]), so a
    chunk of the picture read on its own thread produces the bytes that one pass
    over the whole of it would. The tone band an autolevel row projects onto is
    part of that render's identity, so a reading that were merely close would
    rename every cached candidate.

    What the split buys is the cube roots. Three `cbrt` calls over a candidate's
    pixels are about sixty percent of this conversion and numpy runs them one
    element at a time; they are also what a thread can carry away, because a
    numpy ufunc drops the GIL for the length of its loop.

    Flat rather than `[H, W]` because every statistic read off it — a
    percentile, a median over a mask, a mask's own share — is a fact about the
    multiset of pixels and not about where they sat.
    """
    from concurrent.futures import ThreadPoolExecutor

    import numpy

    pixels = numpy.asarray(rgb).reshape(-1, 3)
    count = int(pixels.shape[0])
    lightness = numpy.empty(count, dtype=numpy.float64)
    chroma = numpy.empty(count, dtype=numpy.float64)

    def read(low: int, high: int) -> None:
        part = pixels[low:high]
        lit, green_red, blue_yellow = _oklab_of_linear(
            _srgb_to_linear(part[:, 0]),
            _srgb_to_linear(part[:, 1]),
            _srgb_to_linear(part[:, 2]),
        )
        lightness[low:high] = lit
        numpy.hypot(green_red, blue_yellow, out=chroma[low:high])

    threads = _read_threads() if count >= READ_SERIAL_BELOW else 1
    if threads <= 1:
        read(0, count)
    else:
        edges = [(count * index) // threads for index in range(threads + 1)]
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for done in [
                pool.submit(read, edges[index], edges[index + 1]) for index in range(threads)
            ]:
                done.result()
    return lightness, chroma


def srgb(lab):
    """Oklab `[..., 3]` back to sRGB `[..., 3]` on the 0–255 scale, clipped.

    The inverse of [`oklab`] and on the same scale it reads, so the two compose:
    `oklab(srgb(lab))` is `lab` for any colour inside the gamut.

    Here rather than in the module that needs it, because a second copy of
    Ottosson's matrices is how two parts of one repository come to disagree about
    what a colour is. The autolevel operator pushes a tone curve through a
    colormap's stops in this space and has to come back out of it.

    **The clip is not a gamut fit.** A lightness the curve moved may leave the
    sRGB cube, and clipping each channel independently rotates hue *and* moves
    lightness — the one axis the curve exists to control. So the caller asks
    whether a colour survived the round trip and pulls its chroma back if it did
    not; this function just does the arithmetic and says what it did.
    """
    import numpy

    lab = numpy.asarray(lab, dtype=numpy.float64)
    lightness, green_red, blue_yellow = lab[..., 0], lab[..., 1], lab[..., 2]
    long = (lightness + 0.3963377774 * green_red + 0.2158037573 * blue_yellow) ** 3
    medium = (lightness - 0.1055613458 * green_red - 0.0638541728 * blue_yellow) ** 3
    short = (lightness - 0.0894841775 * green_red - 1.2914855480 * blue_yellow) ** 3
    linear = numpy.stack(
        [
            +4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
            -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
            -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short,
        ],
        axis=-1,
    )
    return numpy.clip(_linear_to_srgb(linear), 0.0, 1.0) * 255.0


def _linear_to_srgb(channel):
    import numpy

    channel = numpy.asarray(channel, dtype=numpy.float64)
    return numpy.where(
        channel <= 0.0031308,
        channel * 12.92,
        1.055 * numpy.abs(channel) ** (1.0 / 2.4) - 0.055,
    )


def ramp(name: str):
    """One map's stops as `(positions, sRGB8)`, read from the tracked library."""
    path = colormap_dir() / f"{name}.json"
    if not path.is_file():
        raise SpaceError(f"{path} is missing — a map cannot be placed without its stops")
    document = json.loads(path.read_text(encoding="utf-8"))
    stops = document.get("stops") or []
    if len(stops) < 2:
        raise SpaceError(f"{name} carries {len(stops)} stops; a gradient needs at least two")
    import numpy

    positions = numpy.asarray([float(stop[0]) for stop in stops], dtype=numpy.float64)
    colours = numpy.asarray([stop[1] for stop in stops], dtype=numpy.float64)
    return positions, colours, document.get("kind")


def spent(name: str, samples: int = SAMPLES):
    """The gradient a render of this map really shows, sampled evenly.

    A sequential map is folded — out along the ramp and back — because that is
    what the canonical coloring recipe does with one whose ends do not meet. A
    cyclic map is swept once. The fold is read off the map's `kind`, never off a
    row, which is the rule the whole repository colours by.
    """
    import numpy

    positions, colours, kind = ramp(name)
    where = numpy.linspace(0.0, 1.0, samples)
    if kind != "cyclic":
        where = 1.0 - numpy.abs(2.0 * where - 1.0)
    picked = numpy.stack(
        [numpy.interp(where, positions, colours[:, channel]) for channel in range(3)], axis=-1
    )
    return picked


@lru_cache(maxsize=256)
def _cached(names: tuple[str, ...]):
    import numpy

    return numpy.stack([oklab(spent(name)).reshape(-1) for name in names])


def table(names):
    """Every named map's descriptor, one row each, in the order given."""
    return _cached(tuple(names))


def distances(names):
    """The full `[n, n]` matrix of palette-space distances between named maps."""
    import numpy

    points = table(names)
    square = (points * points).sum(axis=1)
    gram = square[:, None] + square[None, :] - 2.0 * (points @ points.T)
    out = numpy.sqrt(numpy.maximum(gram, 0.0))
    # The identity the expansion above loses to rounding, put back: a map is at no
    # distance from itself, and a diagonal of 1e-7 would make a self-comparison
    # sort ahead of or behind a genuine tie depending on the map.
    numpy.fill_diagonal(out, 0.0)
    return out


def neighbourhood(anchor: str, names, size: int) -> list[str]:
    """The `size` maps nearest one anchor — the anchor itself first.

    This is the hard set's construction. It is the anchor's own neighbourhood
    rather than a cluster of the pool because a cluster gives one fixed set per
    cluster, and a pool of seven hundred maps only holds about twenty of those:
    every location would then be asked one of twenty questions. An anchor's
    neighbourhood is as tight and there is one per map, so the corpus can cover
    the whole library while every set it holds is a near-tie by construction.

    Ties are broken by name, so the set is a function of the library and the
    anchor and of nothing else.
    """
    import numpy

    names = list(names)
    if anchor not in names:
        raise SpaceError(f"{anchor!r} is not in the pool it is meant to anchor a set in")
    if size > len(names):
        raise SpaceError(f"a set of {size} cannot be drawn from a pool of {len(names)}")
    points = table(names)
    index = names.index(anchor)
    gaps = points - points[index]
    away = numpy.sqrt((gaps * gaps).sum(axis=-1))
    order = sorted(range(len(names)), key=lambda position: (away[position], names[position]))
    return [names[position] for position in order[:size]]


def tightness(names) -> dict:
    """How near a set's members are to each other, for a record to carry.

    The mean and the widest pairwise distance inside the set. A uniform draw and
    a neighbourhood draw are told apart by these two numbers, and a corpus that
    claims to hold hard sets should be able to show them.
    """
    import numpy

    matrix = distances(tuple(names))
    upper = matrix[numpy.triu_indices(len(names), k=1)]
    return {
        "mean": float(upper.mean()),
        "max": float(upper.max()),
        "candidates": len(names),
    }


__all__ = [
    "READ_POOL_WIDTH",
    "READ_SERIAL_BELOW",
    "READ_THREAD_CAP",
    "SAMPLES",
    "SpaceError",
    "distances",
    "lightness_and_chroma",
    "neighbourhood",
    "oklab",
    "ramp",
    "spent",
    "srgb",
    "table",
    "tightness",
]
