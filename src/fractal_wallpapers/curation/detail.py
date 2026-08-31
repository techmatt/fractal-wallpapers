"""Readings of how much detail a finished picture holds, beside [`flatness`].

[`curation.flatness`] is the shipped rank key's only texture term, and it is a
*penalty*: the share of cells a plane fits with nothing left over. It says where
a picture is dead. It says nothing about how busy the rest of it is, and there is
a standing preference for busier pictures that the key cannot express.

These are the columns that make that preference readable. Each is a few lines
over one decoded picture, no engine call and no field:

- [`bits_per_pixel`] — the stored JPEG's own file size, as bits per pixel. The
  encoder spends bytes where there is structure to spend them on, so at a fixed
  quality this is the cheapest complexity reading there is: no decode at all.
- [`gradient_energy`] — mean gradient magnitude on the luminance, divided by the
  picture's own contrast. The normalization is the whole point: an unnormalized
  gradient mean ranks a high-contrast ramp above a low-contrast filigree, which
  is a reading of the palette rather than of the picture.
- [`spectral_slope`] — the exponent of a power-law fit to the radial power
  spectrum. Natural images sit near `k**-2`; a picture with fine structure
  everywhere decays *more slowly* and reads a **smaller** exponent. It is the one
  descriptor here that goes down as complexity goes up.
- [`flat_fraction`] — [`flatness.fraction`]'s rule at any cell size. `flat16_1.0`
  is the shipped one; 8, 32 and 64 read the same rule at other scales, and the
  scale is the question — a picture can be busy at 8 and dead at 64.

## They are read at a geometry and compared within one

Every one of these moves with resolution. A 16-pixel cell is a different fraction
of a 640-wide picture than of a 1280-wide one, a gradient is per-pixel, and bits
per pixel divides by the pixel count but not by what a pixel *covers*. So a
population read at two geometries holds two populations of numbers, and
[`standardize_within`] is the shape that says so: standardize inside a geometry,
never across.

## Nothing here is wired into the key

No caller in `curation` reads this module. It exists to be measured against the
label rows before anything is chosen, and the choosing is not this module's.
"""

from __future__ import annotations

import math
from pathlib import Path

from fractal_wallpapers.curation import flatness

#: The cell sizes read beside the shipped [`flatness.CELL`], in pixels.
CELLS = (8, 16, 32, 64)

#: The frequency band the power law is fitted over, as a share of the radial
#: extent. The bottom is dropped because the first few bins are the frame's own
#: shape rather than its texture; the top because JPEG quantization flattens the
#: last octave into the encoder's ringing and fitting there reads the codec.
SPECTRUM_BAND = (0.02, 0.5)

#: Below this the picture has no contrast to normalize a gradient by, and the
#: reading is `None` rather than an enormous number. 0-255 luminance units.
MIN_CONTRAST = 1e-3

#: Every column this module reads, in the order a table prints them. The shipped
#: `flat16_1.0` is deliberately not among them: it is already a column and this
#: module reads the three scales *beside* it.
COLUMNS = ("bpp", "grad_energy", "spectral_slope", "flat8_1.0", "flat32_1.0", "flat64_1.0")


class DetailError(RuntimeError):
    """A picture cannot be read."""


def flat_column(cell: int, threshold: float = flatness.THRESHOLD) -> str:
    """A cell size's column name, spelled [`flatness.COLUMN`]'s one way.

    The cell and the threshold both travel in the name, because a fraction read
    at other constants is a different number and must not be able to wear this
    one's.
    """
    return f"flat{int(cell)}_{float(threshold)}"


# --------------------------------------------------------------------------- #
# The readings.
# --------------------------------------------------------------------------- #
def luminance(path):
    """The picture's 0-255 luminance plane as float32, or `None`.

    One decode for every reading that needs one. `None` where the file cannot be
    opened, which the caller counts — no picture and no detail are different
    facts and neither may be spelled as a zero.
    """
    import numpy
    from PIL import Image

    try:
        with Image.open(Path(path)) as image:
            return numpy.asarray(image.convert("L"), dtype=numpy.float32)
    except Exception:
        return None


def bits_per_pixel(path, size=None) -> float | None:
    """The stored file's size in bits, divided by its pixel count.

    Only meaningful for a lossy encoding at a fixed quality: a PNG's byte count
    is its compressor's opinion rather than an encoder's rate decision, so a
    caller reading one of those is reading something else. `size` is the
    picture's `(height, width)` when it is already known, to save the decode.
    """
    where = Path(path)
    if not where.is_file():
        return None
    if size is None:
        grey = luminance(where)
        if grey is None:
            return None
        size = grey.shape
    pixels = int(size[0]) * int(size[1])
    if pixels <= 0:
        return None
    return float(where.stat().st_size * 8) / pixels


def gradient_energy(grey) -> float | None:
    """Mean gradient magnitude over the luminance, in units of its own contrast.

    Central differences rather than Sobel: the picture is already a smooth field
    sampled at 2x and then downsampled, so there is nothing for a smoothing
    kernel to buy, and a two-tap difference is the one every reader can check.
    """
    import numpy

    if grey is None or grey.shape[0] < 3 or grey.shape[1] < 3:
        return None
    contrast = float(grey.std())
    if contrast < MIN_CONTRAST:
        return None
    dy = (grey[2:, 1:-1] - grey[:-2, 1:-1]) * 0.5
    dx = (grey[1:-1, 2:] - grey[1:-1, :-2]) * 0.5
    return float(numpy.sqrt(dx * dx + dy * dy).mean() / contrast)


def spectral_slope(grey, band=SPECTRUM_BAND) -> float | None:
    """The `a` of `P(k) ~ k**-a`, least squares in log-log on the radial average.

    Hann-windowed before the transform, because a picture is not periodic and the
    seam between its left and right edges otherwise puts a cross of spurious
    power through the middle of the spectrum and drags the fit toward it.
    """
    import numpy

    if grey is None or min(grey.shape) < 16:
        return None
    height, width = grey.shape
    window = numpy.hanning(height)[:, None] * numpy.hanning(width)[None, :]
    centred = (grey - grey.mean()) * window
    if not numpy.isfinite(centred).all() or float(numpy.abs(centred).max()) <= 0.0:
        return None
    power = numpy.abs(numpy.fft.fftshift(numpy.fft.fft2(centred))) ** 2
    down = numpy.arange(height) - height / 2.0
    across = numpy.arange(width) - width / 2.0
    # Cycles per picture-half on each axis, so a non-square frame's two axes are
    # on one scale and the radial average is over a circle rather than an ellipse.
    radius = numpy.sqrt(
        (down[:, None] / (height / 2.0)) ** 2 + (across[None, :] / (width / 2.0)) ** 2
    )
    bins = min(height, width) // 2
    index = numpy.clip((radius * bins).astype(int), 0, bins)
    total = numpy.bincount(index.ravel(), weights=power.ravel(), minlength=bins + 1)
    counted = numpy.bincount(index.ravel(), minlength=bins + 1)
    mean = total / numpy.maximum(counted, 1)
    low = max(int(band[0] * bins), 1)
    high = max(int(band[1] * bins), low + 2)
    take = numpy.arange(low, high)
    take = take[(counted[take] > 0) & (mean[take] > 0)]
    if take.size < 8:
        return None
    slope = float(numpy.polyfit(numpy.log(take / bins), numpy.log(mean[take]), 1)[0])
    return None if not math.isfinite(slope) else -slope


def flat_fraction(path, cell: int, threshold: float = flatness.THRESHOLD) -> float | None:
    """[`flatness.fraction`] at another cell size, and deliberately by calling it.

    The plane fit is the column's definition and there must be exactly one of it:
    a second copy here would be a second definition that could drift from the one
    the shipped key stands on.
    """
    return flatness.fraction(path, cell=int(cell), threshold=float(threshold))


def read(path, cells=CELLS) -> dict:
    """Every column for one picture, on one decode. `None` for what cannot read.

    `geometry` travels on the row because these numbers are not comparable across
    resolutions and a reader must never have to go and look it up.
    """
    grey = luminance(path)
    if grey is None:
        blanks = {flat_column(cell): None for cell in cells}
        return (
            {"path": str(path), "geometry": None, "unreadable": True}
            | blanks
            | {name: None for name in COLUMNS}
        )
    height, width = grey.shape
    out = {
        "path": str(path),
        "geometry": f"{width}x{height}",
        "unreadable": False,
        "bpp": bits_per_pixel(path, size=grey.shape),
        "grad_energy": gradient_energy(grey),
        "spectral_slope": spectral_slope(grey),
    }
    for cell in cells:
        out[flat_column(cell)] = flat_fraction(path, cell)
    return out


def _chunk(payload: list) -> list:
    """One worker's share: `[(key, path)]` in, `[(key, reading)]` out."""
    return [(key, read(path)) for key, path in payload]


def sweep(pairs, workers: int = flatness.WORKERS, log=print) -> dict:
    """`[(key, path)]` in, `{key: reading}` out, over a small pool of workers.

    Three by default and for [`flatness.WORKERS`]'s reason: this is a
    decode-bound sweep and it should not make the desktop unusable while it runs.
    About 25 ms a picture at 640x360, most of it the four plane fits and the
    transform.
    """
    import time
    from concurrent.futures import ProcessPoolExecutor

    started = time.time()
    pairs = [(str(key), str(path)) for key, path in pairs]
    payloads = [pairs[at : at + flatness.CHUNK] for at in range(0, len(pairs), flatness.CHUNK)]
    out: dict = {}
    log(f"[detail] {len(pairs):,} picture(s) at ~25 ms each over {workers} worker(s)")
    if int(workers) <= 1 or not payloads:
        for payload in payloads:
            out.update(dict(_chunk(payload)))
    else:
        with ProcessPoolExecutor(max_workers=int(workers)) as pool:
            for done, got in enumerate(pool.map(_chunk, payloads), start=1):
                out.update(dict(got))
                log(f"[detail] {done}/{len(payloads)} chunk(s), {time.time() - started:.0f}s")
    unreadable = sum(1 for row in out.values() if row.get("unreadable"))
    log(f"[detail] {len(out):,} read, {unreadable} unreadable, {time.time() - started:.0f}s")
    return out


# --------------------------------------------------------------------------- #
# Comparing them.
# --------------------------------------------------------------------------- #
def standardize_within(rows, column: str) -> dict:
    """`{key: z}` for one column, with the mean and deviation taken per geometry.

    A population read at two resolutions holds two populations of numbers, and a
    single mean over both would rank every picture at the larger geometry above
    every picture at the smaller for no reason about the pictures. A geometry
    whose column is constant standardizes to zero rather than dividing by nothing.
    """
    import numpy

    by_geometry: dict = {}
    for key, row in rows.items():
        value = row.get(column)
        if value is None:
            continue
        by_geometry.setdefault(row.get("geometry"), []).append((key, float(value)))
    out: dict = {}
    for members in by_geometry.values():
        values = numpy.array([value for _, value in members], dtype=float)
        mean, deviation = float(values.mean()), float(values.std())
        if deviation < 1e-12:
            out.update({key: 0.0 for key, _ in members})
            continue
        out.update({key: (value - mean) / deviation for key, value in members})
    return out


def spearman(left, right) -> float | None:
    """Rank correlation, ties at the mean rank. `None` on a constant side."""
    import numpy

    left = numpy.asarray(left, dtype=float)
    right = numpy.asarray(right, dtype=float)
    if left.size < 3 or left.size != right.size:
        return None

    def ranked(values):
        order = numpy.argsort(values, kind="mergesort")
        places = numpy.empty(values.size, dtype=float)
        places[order] = numpy.arange(1, values.size + 1, dtype=float)
        unique, inverse, counts = numpy.unique(values, return_inverse=True, return_counts=True)
        sums = numpy.zeros(unique.size)
        numpy.add.at(sums, inverse, places)
        return (sums / counts)[inverse]

    a, b = ranked(left), ranked(right)
    if a.std() < 1e-12 or b.std() < 1e-12:
        return None
    return float(numpy.corrcoef(a, b)[0, 1])


__all__ = [
    "CELLS",
    "COLUMNS",
    "MIN_CONTRAST",
    "SPECTRUM_BAND",
    "DetailError",
    "bits_per_pixel",
    "flat_column",
    "flat_fraction",
    "gradient_energy",
    "luminance",
    "read",
    "spearman",
    "spectral_slope",
    "standardize_within",
    "sweep",
]
