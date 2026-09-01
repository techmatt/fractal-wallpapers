"""How far apart two **pictures** are in colour. The palette metric, on pixels.

[`fractal_wallpapers.palettes.groups`] asks whether two colormaps are one choice
and answers it over each ramp's colour cloud. This asks whether two finished
pictures are one wallpaper, and answers it the same way over each picture's own
pixels. Same distance, same weighting, same lattice, same quantiles — the only
thing that changes is where the cloud comes from.

That matters more than the saving in code. A group is a statement about a *ramp*
and is order-free over it; a picture spends its ramp unevenly, so two members of
one group can make pictures a long way apart and two different maps can make
pictures that are the same wallpaper. Measured over gallery3, same-group pairs
run from 0.0121 to 0.4111 — a thirty-four-fold range whose median sits *above*
the median nearest-neighbour distance of the gallery at large. The group cap and
the twin test are therefore two instruments and neither substitutes for the
other, which is only visible because both are read in the same units.

## The cloud

A render's own pixels at [`codebook.CENSUS_SIZE`], in Oklab with `a` and `b`
scaled by [`groups.HUE_WEIGHT`], subsampled to [`SAMPLES`] rows on a **seeded
fixed permutation** so every picture is read at the same count and two readings
of one picture are the same reading. The signature is the projections onto
[`groups.DIRECTIONS`] half-sphere directions, sorted, read at
[`groups.QUANTILES`] evenly spaced quantiles; the distance between two of them is
the mean absolute difference, which is the sliced Wasserstein-1 distance the
grouping calls M1.

**All pixels, neutrals included**, and that is deliberate against the other
reading in this file's neighbourhood: [`dominance`] drops the neutrals because it
is answering *what colour is this*, and this keeps them because it is answering
*is this the same picture*, where two mostly-black renders being mostly black is
a real part of the answer. The two variants were measured against each other over
eleven thousand gallery3 pairs at Pearson 0.966, so the ordering barely moves —
but the chromatic-only distances run 5-15% lower at the percentiles a threshold
is set from, and a threshold carried across the two would be a threshold moved.

## What a signature costs

Half a mebibyte of float32 each, and about a tenth of a second to make. Both
numbers are why [`Clouds`] exists: a seating asks for the same picture's cloud at
every seat it survives, and a pass that recomputed would spend more time in this
module than in the renderer. The cache is bounded, because a pass with three
thousand candidates in reach would otherwise hold a gibibyte and a half of
signatures nobody is going to ask for again.
"""

from __future__ import annotations

import collections
from pathlib import Path

from fractal_wallpapers.palettes import codebook, groups

#: How many of a picture's pixels the cloud is read at. The same count
#: [`groups.SAMPLES`] reads a ramp at, so the two clouds are the same size and
#: the quantiles land on the same positions.
SAMPLES = 4096

#: The seed the subsample permutation is drawn under. Fixed, and fixed *here*: a
#: caller free to choose it could make two readings of one picture disagree.
SUBSAMPLE_SEED = 0

#: How many signatures [`Clouds`] keeps before it starts forgetting the ones
#: asked for longest ago. 1024 of them is half a gibibyte, which is the size at
#: which holding them stops being obviously cheaper than making them again.
CACHE = 1024

#: The metric, carried in every record that reads it.
METRIC = (
    f"sliced Wasserstein-1 between two pictures' pixel clouds: {SAMPLES} pixels of each "
    f"render at the codebook census size, sRGB8 to Oklab, a and b scaled by "
    f"{groups.HUE_WEIGHT} so a hue difference counts that many times a lightness "
    f"difference, projected onto {groups.DIRECTIONS} directions of a Fibonacci "
    f"half-sphere lattice and read at {groups.QUANTILES} evenly spaced quantiles. "
    "All pixels, neutrals included."
)

_LATTICE = None
_TAKE: dict = {}


def lattice():
    """The direction lattice, built once. [`groups.directions`] and nothing else."""
    global _LATTICE
    import numpy

    if _LATTICE is None:
        _LATTICE = groups.directions(groups.DIRECTIONS).astype(numpy.float32)
    return _LATTICE


def take(total: int):
    """Which of a picture's `total` pixels the cloud is read at.

    A permutation rather than a stride, so the sample is not a lattice over the
    picture's own geometry; seeded and cached per size, so every picture of one
    size is read at the same pixels and a second reading is the first one.
    """
    import numpy

    if total not in _TAKE:
        rng = numpy.random.default_rng(SUBSAMPLE_SEED)
        _TAKE[total] = rng.permutation(total)[:SAMPLES]
    return _TAKE[total]


def cloud(picture: Path):
    """One picture's weighted Oklab cloud, `[SAMPLES, 3]`."""
    from fractal_wallpapers.palettes import space

    flat = codebook.pixels(Path(picture)).reshape(-1, 3)
    return groups.weighted(space.oklab(flat)[take(flat.shape[0])], groups.HUE_WEIGHT)


def signature(points):
    """`[directions * quantiles]` float32: the sorted projections read at the quantiles.

    Flattened rather than left as a matrix because the only thing anybody does
    with two of these is take the mean absolute difference, and a flat pair is one
    call instead of two.
    """
    import numpy

    samples = points.shape[0]
    projected = numpy.sort(numpy.asarray(points, dtype=numpy.float32) @ lattice().T, axis=0)
    where = groups._quantile_positions(samples, groups.QUANTILES)
    low = numpy.floor(where).astype(numpy.intp)
    high = numpy.minimum(low + 1, samples - 1)
    fraction = (where - low).astype(numpy.float32)[:, None]
    return numpy.ascontiguousarray(
        (projected[low] * (1.0 - fraction) + projected[high] * fraction).reshape(-1)
    )


def of_picture(picture: Path):
    """One picture's signature, end to end."""
    return signature(cloud(picture))


def distance(one, other) -> float:
    """W1 between two signatures. The number a threshold is set in."""
    import numpy

    return float(
        numpy.abs(numpy.asarray(one) - numpy.asarray(other)).sum(dtype=numpy.float64)
        / (groups.DIRECTIONS * groups.QUANTILES)
    )


def distances(one, others) -> list:
    """W1 from one signature to each of many, in the order they came in.

    One call rather than a loop of [`distance`], because the seating asks this of
    every already-shipped picture at every candidate it tests and the difference
    between a hundred and fifty small subtractions and one large one is the whole
    cost of the twin test.
    """
    import numpy

    if not len(others):
        return []
    mine = numpy.asarray(one, dtype=numpy.float32)
    stacked = numpy.asarray(others, dtype=numpy.float32)
    return [
        float(value)
        for value in numpy.abs(stacked - mine).sum(axis=1, dtype=numpy.float64)
        / (groups.DIRECTIONS * groups.QUANTILES)
    ]


class Clouds:
    """Signatures by name, made on demand and kept — the oldest asked-for dropped.

    Two stores and not one, because the two populations behave differently. A
    picture that has been **held** is one a seating will compare every later
    candidate against and must never be recomputed; a picture merely *read* is one
    of a candidate pool that mostly loses, and holding all of those is what would
    make this expensive. So `hold` is unbounded and small, and the read cache is
    bounded and large.
    """

    def __init__(self, path_of, cache: int = CACHE):
        #: `name -> Path`, so the cache is addressed by the caller's own ids.
        self.path_of = path_of
        self.cache = max(1, int(cache))
        self._held: dict = {}
        self._read: collections.OrderedDict = collections.OrderedDict()
        self.made = 0
        self.hits = 0

    def of(self, name: str):
        """The signature of one picture, or `None` where there is no picture to read."""
        if name in self._held:
            self.hits += 1
            return self._held[name]
        if name in self._read:
            self.hits += 1
            self._read.move_to_end(name)
            return self._read[name]
        picture = self.path_of(name)
        if picture is None or not Path(picture).is_file():
            return None
        made = of_picture(picture)
        self.made += 1
        self._read[name] = made
        while len(self._read) > self.cache:
            self._read.popitem(last=False)
        return made

    def hold(self, name: str) -> None:
        """Promote one picture's signature out of the bounded cache and keep it."""
        made = self.of(name)
        if made is not None:
            self._held[name] = made
            self._read.pop(name, None)

    def let_go(self, name: str) -> None:
        """Stop holding one picture, keeping it in the bounded cache instead.

        The swap loop's half of [`hold`]: a seat that leaves the gallery is a
        signature that must stop being kept forever, or a loop that takes a
        thousand seats in and out again holds every one of them. It goes back into
        the read cache rather than being thrown away, because a seat that has just
        been swapped out is exactly the picture most likely to be asked for next.
        """
        made = self._held.pop(name, None)
        if made is not None:
            self._read[name] = made
            while len(self._read) > self.cache:
                self._read.popitem(last=False)

    def release(self) -> None:
        """Drop everything held. A pass that starts again starts with nothing held."""
        self._held.clear()

    def price(self) -> dict:
        """What the cache did, for the pass record."""
        return {
            "samples": SAMPLES,
            "subsample_seed": SUBSAMPLE_SEED,
            "directions": groups.DIRECTIONS,
            "quantiles": groups.QUANTILES,
            "hue_weight": groups.HUE_WEIGHT,
            "cache": self.cache,
            "signatures_made": self.made,
            "cache_hits": self.hits,
            "held": len(self._held),
        }


__all__ = [
    "CACHE",
    "METRIC",
    "SAMPLES",
    "SUBSAMPLE_SEED",
    "Clouds",
    "cloud",
    "distance",
    "distances",
    "lattice",
    "of_picture",
    "signature",
    "take",
]
