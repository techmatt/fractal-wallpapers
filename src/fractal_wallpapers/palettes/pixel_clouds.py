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
[`DIRECTIONS`] half-sphere directions, sorted, read at
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

**128 KiB of float32 each** — `[QUANTILES, DIRECTIONS]` at 128 by 256 — and about
thirty-five milliseconds to make. Both numbers are why [`Clouds`] exists: a seating
asks for the same picture's cloud at every seat it survives, and a pass that
recomputed would spend more time in this module than in the renderer. The cache is
bounded, because a pass with three thousand candidates in reach would otherwise hold
hundreds of mebibytes of signatures nobody is going to ask for again.

Both figures were four times worse until 2026-09-01: 512 KiB and about a tenth of a
second, at 1024 directions and with the sort running down the strided axis. See
[`DIRECTIONS`] and [`signature`].
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

#: How many half-sphere directions THIS metric slices along. **The twin metric's
#: own count, and deliberately not [`groups.DIRECTIONS`].**
#:
#: **256.** The slice count is the Monte Carlo sample size of a sliced
#: Wasserstein-1 estimate, so fewer slices is the same expectation with more
#: variance, and the sort over the projections is 86% of what a signature costs
#: and scales with it. `SOLVE_census_n2000` measured the trade over 731 pairs in
#: the 0.5-1.5x [`curation.ceiling.TAU`] band, each count given its own
#: `groups.directions` call because a 256-point Fibonacci lattice is not a prefix
#: of a 1024-point one: **1 twin verdict of 731 flipped at 256** against 0 at 512,
#: 3 at 128 and 4 at 64, and every flip sat within 0.05% of TAU at this count —
#: pairs whose correct verdict is arbitrary. Flip direction is balanced and the
#: ratio to the 1024-direction distance is centred on 1.0000 within 0.02%, so this
#: is added variance and **not a shift: `TAU` is not refitted and must not be.**
#: The exposure is small because the bound absorbs it — 99% of pairs are settled
#: without measuring, and only 6.1% of the comparisons a leg must measure sit
#: inside this count's own noise band.
#:
#: **Why not [`groups.DIRECTIONS`], which is 1024**: that constant is the
#: palette-group M1 matrix's, a different metric over different objects — sliced
#: W1 between colormap *ramps* rather than between finished pictures — and
#: `groups.m1` still defaults to it. Every stored group name (`m14`, `m57`, ...)
#: was cut under it, so moving it would invalidate the grouping the gallery's
#: palette-group cap counts against. The two metrics share `groups.QUANTILES`,
#: `groups.SAMPLES` and `groups.HUE_WEIGHT` and diverge only here.
DIRECTIONS = 256

#: How many signatures [`Clouds`] keeps before it starts forgetting the ones
#: asked for longest ago. 1024 of them is 128 MiB at [`DIRECTIONS`] = 256 — it was
#: half a gibibyte at 1024 directions, and the count came down without this having
#: to move.
CACHE = 1024

#: The metric, carried in every record that reads it.
METRIC = (
    f"sliced Wasserstein-1 between two pictures' pixel clouds: {SAMPLES} pixels of each "
    f"render at the codebook census size, sRGB8 to Oklab, a and b scaled by "
    f"{groups.HUE_WEIGHT} so a hue difference counts that many times a lightness "
    f"difference, projected onto {DIRECTIONS} directions of a Fibonacci "
    f"half-sphere lattice and read at {groups.QUANTILES} evenly spaced quantiles. "
    "All pixels, neutrals included."
)

#: `{direction count: lattice}`. Keyed on the count and not a bare singleton,
#: because every signature is a function of the count and a cached lattice built
#: at another one would answer in a different metric without raising anything.
_LATTICE: dict = {}
_TAKE: dict = {}


def lattice(count: int | None = None):
    """The direction lattice for `count` directions, built once per count.

    Cached **per count** rather than as one singleton. Every signature is a
    function of the direction count, so a lattice built at one count and handed to
    a caller expecting another is a silently different metric — and the only way
    the count moves inside one process is a test that sets [`DIRECTIONS`], which
    is exactly where a stale singleton would not raise.
    """
    import numpy

    wanted = DIRECTIONS if count is None else int(count)
    if wanted not in _LATTICE:
        _LATTICE[wanted] = groups.directions(wanted).astype(numpy.float32)
    return _LATTICE[wanted]


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
    """`[quantiles * directions]` float32: the sorted projections read at the quantiles.

    Flattened rather than left as a matrix because the only thing anybody does
    with two of these is take the mean absolute difference, and a flat pair is one
    call instead of two. Quantile-major, which is the layout
    [`curation.rules.reduce_signature`] reshapes back to.

    **The projection is transposed into a contiguous copy and sorted along its last
    axis.** The sort is 86% of what a signature costs — not the JPEG decode, which is
    2% — and the shipped form sorted `[samples, directions]` along `axis=0`, which is
    [`DIRECTIONS`] independent sorts each striding `samples` floats apart. The sort
    itself is far cheaper along the contiguous axis — 8.1 ms against 13.2 ms at 256
    directions, 32.2 against 84.9 at 1024 — but the transpose copy takes most of that
    back, so end to end the rearrangement is **1.28x** (90.7 ms to 71.1 ms over the
    projection, sort and quantile read at 1024). The count is where the rest is:
    6.59x on its own, **7.66x together**, and 90.7 ms to 11.8 ms.

    **Why a copy rather than projecting straight into `[directions, samples]`.**
    `lattice() @ points.T` produces that shape directly and is bit-identical, and it
    was what this did first. But the projection's inner dimension is **3**, so there
    is nothing in it to parallelise, and BLAS threads that shape anyway: measured at
    256 directions it is **5.79 ms wall for 56.6 ms of CPU** against 0.70 ms for the
    `[samples, directions]` shape, and it took the whole signature from 9.6 ms to
    **24.9 ms wall and 185 ms of CPU** — a spin-wait, and three times worse again
    inside `curation.signatures`' three-worker pool. `numpy.einsum` is not the way
    out either: with `optimize=True` it returns a non-contiguous *view* of the same
    BLAS result, so the sort goes back to striding, and with `optimize=False` its own
    loop is not bit-identical.

    The values are the same values whichever way they are laid out, and that is
    checked rather than assumed — BLAS picks a kernel per shape and could accumulate
    three terms in a different order. `tests/test_palette_carriers.py` pins both the
    byte-identity and the quantile-major layout.
    """
    import numpy

    samples = points.shape[0]
    projected = numpy.sort(
        numpy.ascontiguousarray((numpy.asarray(points, dtype=numpy.float32) @ lattice().T).T),
        axis=-1,
    )
    where = groups._quantile_positions(samples, groups.QUANTILES)
    low = numpy.floor(where).astype(numpy.intp)
    high = numpy.minimum(low + 1, samples - 1)
    fraction = (where - low).astype(numpy.float32)
    # `[directions, quantiles]`, transposed on the way out because the flat form is
    # quantile-major and every reader of it reshapes on that assumption.
    read = projected[:, low] * (1.0 - fraction) + projected[:, high] * fraction
    return numpy.ascontiguousarray(read.T.reshape(-1))


def of_picture(picture: Path):
    """One picture's signature, end to end."""
    return signature(cloud(picture))


def distance(one, other) -> float:
    """W1 between two signatures. The number a threshold is set in."""
    import numpy

    return float(
        numpy.abs(numpy.asarray(one) - numpy.asarray(other)).sum(dtype=numpy.float64)
        / (DIRECTIONS * groups.QUANTILES)
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
        / (DIRECTIONS * groups.QUANTILES)
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
        #: The direction count every entry in this instance was made at. A
        #: signature is a function of the count, so an instance that outlived a
        #: change to it would compare two different metrics under one key and
        #: raise nothing — see [`Clouds.of`].
        self.directions = DIRECTIONS
        self.made = 0
        self.hits = 0

    def of(self, name: str):
        """The signature of one picture, or `None` where there is no picture to read."""
        if self.directions != DIRECTIONS:
            # The count moved under us. Everything held is in the old metric, so
            # it is dropped rather than mixed: a miss costs a decode, a hit here
            # would cost a wrong answer.
            self.release()
            self._read.clear()
            self.directions = DIRECTIONS
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
            "directions": DIRECTIONS,
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
