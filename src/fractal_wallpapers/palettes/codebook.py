"""The colour codebook: fifty-two named places in Oklab, and how to read a picture through them.

A census of colour needs a vocabulary before it can count anything, and the
vocabulary has to be small enough to put in a table and stable enough that two
sessions a month apart mean the same thing by "dark green". This module is that
vocabulary: **twelve hues x {dark, light} x {muted, vivid}, plus four neutrals**,
every one of them a point in Oklab, and one function that turns any set of pixels
into a share vector over those fifty-two.

Nothing here filters, scores or gates. It describes.

## They are called swatches, and the codebook calls them anchors

Matt's ratified codebook says *anchor*, and this module says **swatch** for the
same fifty-two things. That is not a quiet rename, it is a collision: `anchor`
already means the map a hard candidate set was built around — and it is spelled
`anchor` on the very pool rows a colour census reads — as well as a named
smoke-test location in `data/anchors.jsonl` and a center in `deep`. A fourth
meaning, on the same row as the second, is a misread waiting to happen every time
somebody greps. So the codebook's *anchors* are this module's *swatches*, the
translation is stated here and once in the report, and nowhere else does the word
have to be disambiguated.

## Oklab, and only Oklab

Assignment happens in Oklab and never in HSV or RGB, because the question is
whether two colours look alike and sRGB distance does not answer it. The
conversion is [`fractal_wallpapers.palettes.space.oklab`] — the same Ottosson
matrices the engine carries in `colormap.rs`, read from the one place this
repository keeps them, so a swatch cannot mean one colour here and another there.

## The chroma of a swatch is fitted to the gamut, and that is not a detail

The obvious codebook puts every hue's vivid tier at one fixed chroma. It cannot
be built. At `L = 0.40` the sRGB gamut holds only `C = 0.077` of teal, `0.073` of
cyan and `0.086` of yellow, so a fixed vivid chroma of `0.16` would place **seven
of the twelve dark-vivid swatches outside sRGB** — dark green among them. No
pixel could ever be nearest to them, and a census run through that codebook would
report dark green as absent from a library that has forty maps carrying it. The
instrument would have manufactured its own headline.

So a swatch's chroma is `min(target, HEADROOM x max_chroma(L, hue))`: the stated
target where the gamut holds it, and as much as the gamut holds where it does
not. Every swatch is a colour that can actually appear in a picture.

**Three pairs stay unresolved and are reported rather than hidden.** At the dark
tone, cyan, teal and yellow have so little chroma range that their muted and
vivid swatches land 0.009 to 0.021 apart — closer than the assignment can
separate. That is a fact about sRGB at `L = 0.40`, not a tuning failure: those
hues *have* no vivid dark form. Read each of those two cells together.

## The share vector is soft, and the softness is calibrated rather than chosen

A pixel does not vote for one swatch. It spreads its weight by Gaussian falloff
in Oklab — `w = exp(-d^2 / 2 sigma^2)`, normalized per pixel — and an image's
share vector is the mean of those weights. Soft because the alternative puts a
knife edge between two swatches through the middle of a smooth gradient, and a
ramp that drifts across the edge would show as two hard blocks.

`sigma` is **0.015**, and it was fixed by measurement against three checks
declared before the sweep:

* a pure swatch's own share is its largest — **52 of 52**, so the dominant swatch
  of a synthetic single-colour image is always that colour;
* a neutral grey, at any lightness, puts **>= 0.99** of its mass on the four
  neutrals (measured worst case 0.996 over forty lightnesses). This is the check
  that matters most and it is the one that rejected the first codebook: with the
  neutrals at lightnesses that fell *between* the tone levels, a pure mid-grey
  landed on dark muted cyan, and every achromatic wallpaper in the pool would
  have donated a quarter of its mass to cyan and teal;
* the median pure-swatch self-share is **0.81** — soft at the boundaries without
  collapsing to a hard nearest-swatch assignment.

The neutrals are therefore the **zero-chroma column of the same lattice**: grey
at the two tone lightnesses, plus black and white at the ends.

## What a census reports, pre-registered

Per image or ramp: the share vector, the dominant swatch, the Shannon entropy of
the vector in bits, and the count of swatches above [`SMALL_SHARE`]. The entropy
and the count are the multi-colour signal that a single dominant share cannot
see — a rainbow map and a two-tone map can share a dominant swatch and differ by
two bits.

Across a population: the fraction of images whose share of a given swatch clears
[`SHARE_THRESHOLDS`]. Both are reported. The 25% figure is expected to be sparse,
and that is the reading it exists to give — whether a colour can *dominate* a
picture rather than merely appear in one.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

#: The codebook's schema, carried by the persisted document from the first row.
SCHEMA = 1

#: Twelve hues at thirty-degree steps of Oklab hue angle, named for what a reader
#: would call them. The wheel is anchored so that `red` sits at 30 degrees, which
#: is where sRGB's own red lands (29.2 degrees); every other name follows from the
#: step. A name is the article's, not a colour scientist's: `azure` is the blue-cyan
#: midpoint everybody recognizes in a fractal and has no shorter name.
HUES: tuple[tuple[str, float], ...] = (
    ("rose", 0.0),
    ("red", 30.0),
    ("orange", 60.0),
    ("yellow", 90.0),
    ("lime", 120.0),
    ("green", 150.0),
    ("teal", 180.0),
    ("cyan", 210.0),
    ("azure", 240.0),
    ("blue", 270.0),
    ("purple", 300.0),
    ("magenta", 330.0),
)

#: The two tones, as Oklab lightness. Far enough apart that a map's dark half and
#: its light half do not land in one cell, and inside the range where every hue
#: has some chroma to spend.
TONES: tuple[tuple[str, float], ...] = (("dark", 0.40), ("light", 0.75))

#: What `muted` and `vivid` mean as Oklab chroma, where the gamut holds them.
CHROMA_TARGETS: tuple[tuple[str, float], ...] = (("muted", 0.06), ("vivid", 0.16))

#: How much of a hue's available chroma a swatch may claim at its lightness. Short
#: of 1.0 so that a swatch clipped by the gamut still sits inside sRGB rather than
#: exactly on its boundary, where the round trip is numerically undecided.
HEADROOM = 0.95

#: The four neutrals: the zero-chroma column of the same lattice. `dark_gray` and
#: `light_gray` sit at the tone lightnesses on purpose — see the module docstring,
#: where putting them anywhere else is the bug this codebook was rebuilt to fix.
NEUTRALS: tuple[tuple[str, float], ...] = (
    ("black", 0.12),
    ("dark_gray", 0.40),
    ("light_gray", 0.75),
    ("white", 0.95),
)

#: The Gaussian width of the soft assignment, in Oklab units. Calibrated, not
#: chosen; the three checks it was fixed against are in the module docstring and
#: are asserted by `tests/test_colour_codebook.py`.
SIGMA = 0.015

#: A swatch is "present" in an image above this share. Used only for the
#: multi-colour count, which is a description of one image rather than a cut.
SMALL_SHARE = 0.05

#: The two pre-registered population thresholds: does this colour appear, and can
#: it dominate.
SHARE_THRESHOLDS: tuple[float, ...] = (0.10, 0.25)

#: How many places along a gradient a ramp census reads. Far denser than the
#: sparsest map in the library carries stops (33), so the census reads the ramp
#: rather than the sampling.
RAMP_SAMPLES = 1024

#: The census resolution for a picture, as (width, height). Chosen so that JPEG's
#: own scaled decode lands on it exactly for both sizes this project stores — the
#: 640x360 candidate render at 1/4 and the 1280x720 label crop at 1/8 — so no
#: resampling stands between the stored pixels and the count. 14,400 samples.
CENSUS_SIZE = (160, 90)


class CodebookError(RuntimeError):
    """A colour cannot be placed, or a picture cannot be read."""


def _lab(lightness: float, chroma: float, hue_degrees: float):
    """One OkLCh coordinate as Oklab. The whole of the polar conversion."""
    import numpy

    angle = math.radians(hue_degrees)
    return numpy.array(
        [lightness, chroma * math.cos(angle), chroma * math.sin(angle)], dtype=numpy.float64
    )


def _in_gamut(lab, tolerance: float = 0.004) -> bool:
    """Whether this Oklab colour survives a round trip through sRGB unclipped.

    `space.srgb` clips each channel independently and says so; a colour that
    clipped comes back as a different colour. Measuring the round trip is
    therefore the gamut test, and it needs no second implementation of the
    boundary.
    """
    import numpy

    from fractal_wallpapers.palettes import space

    return bool(numpy.linalg.norm(space.oklab(space.srgb(lab)) - lab) < tolerance)


def max_chroma(lightness: float, hue_degrees: float, steps: int = 40) -> float:
    """The most chroma sRGB holds at this lightness and hue, by bisection.

    Deterministic and a pure function of the two arguments, so the codebook it
    shapes is a function of nothing but the constants above.
    """
    low, high = 0.0, 0.45
    for _ in range(steps):
        middle = (low + high) / 2.0
        if _in_gamut(_lab(lightness, middle, hue_degrees)):
            low = middle
        else:
            high = middle
    return low


@lru_cache(maxsize=1)
def swatches() -> tuple[dict, ...]:
    """The fifty-two, in a fixed order: the forty-eight hues, then the four neutrals.

    The order is the artifact's column order and never changes, because a share
    vector persisted under one order and read under another is silently wrong.
    """
    from fractal_wallpapers.palettes import space

    built: list[dict] = []
    for hue_name, degrees in HUES:
        for tone_name, lightness in TONES:
            available = HEADROOM * max_chroma(lightness, degrees)
            for chroma_name, target in CHROMA_TARGETS:
                chroma = min(target, available)
                lab = _lab(lightness, chroma, degrees)
                built.append(
                    {
                        "swatch": f"{tone_name}_{chroma_name}_{hue_name}",
                        "kind": "hue",
                        "hue": hue_name,
                        "hue_degrees": degrees,
                        "tone": tone_name,
                        "chroma": chroma_name,
                        "lab": [round(float(value), 6) for value in lab],
                        "oklch": [lightness, round(float(chroma), 6), degrees],
                        "gamut_limited": bool(chroma < target),
                        "srgb": [int(round(float(value))) for value in space.srgb(lab)],
                    }
                )
    for neutral_name, lightness in NEUTRALS:
        lab = _lab(lightness, 0.0, 0.0)
        built.append(
            {
                "swatch": neutral_name,
                "kind": "neutral",
                "hue": None,
                "hue_degrees": None,
                "tone": None,
                "chroma": None,
                "lab": [round(float(value), 6) for value in lab],
                "oklch": [lightness, 0.0, None],
                "gamut_limited": False,
                "srgb": [int(round(float(value))) for value in space.srgb(lab)],
            }
        )
    return tuple(built)


def cell_names() -> tuple[str, ...]:
    """The forty-eight chromatic swatch **names**, in the codebook's own order.

    [`swatches`] without the swatches. The names are a pure product of [`HUES`],
    [`TONES`] and [`CHROMA_TARGETS`] — the colours are not, and [`max_chroma`]
    bisects the sRGB gamut 40 steps a combination through `numpy` to find them.
    So a caller that wants only the spelling pays **0.164 s and an import of
    numpy** for it, measured on this machine, and pays it at the moment it asks.

    That is affordable in a report and not affordable in a **parser**:
    `cli.build_parser` builds every group on every invocation, so
    `choices=dominance.cells()` on `--themed` would put a gamut bisection and
    numpy behind `fractal-wallpapers --help` and behind `fetch-weights --check`
    — which is the one import graph `tests/test_base_install.py` spawns a
    subprocess to keep stdlib-only. This is the reader that makes the closed list
    free.

    **It is a second spelling of an order [`swatches`] owns**, which that
    function's own docstring is right to warn about, so
    `tests/test_palette_codebook.py` holds the two to agreeing rather than
    trusting the loop nesting to stay copied correctly.
    """
    return tuple(
        f"{tone_name}_{chroma_name}_{hue_name}"
        for hue_name, _degrees in HUES
        for tone_name, _lightness in TONES
        for chroma_name, _target in CHROMA_TARGETS
    )


def names() -> tuple[str, ...]:
    """Every swatch name, in the codebook's own order."""
    return tuple(entry["swatch"] for entry in swatches())


@lru_cache(maxsize=1)
def points():
    """The fifty-two as an `[52, 3]` Oklab array, in codebook order."""
    import numpy

    table = numpy.asarray([entry["lab"] for entry in swatches()], dtype=numpy.float64)
    table.flags.writeable = False
    return table


def closest_pairs(limit: int = 8) -> list[tuple[float, str, str]]:
    """The nearest swatch pairs, so a reader can see what the codebook cannot separate.

    Reported rather than asserted away: the dark cyan, teal and yellow
    muted/vivid pairs are inside the assignment's own resolution because sRGB has
    almost no chroma there, and a reader of those cells has to know it.
    """
    import numpy

    table, labels = points(), names()
    found = [
        (float(numpy.linalg.norm(table[first] - table[second])), labels[first], labels[second])
        for first in range(len(labels))
        for second in range(first + 1, len(labels))
    ]
    return sorted(found)[:limit]


def document() -> dict:
    """The codebook as it is persisted beside every census that used it.

    Everything needed to reproduce an assignment: the geometry, the width, the
    thresholds and the fifty-two colours themselves. A census artifact carries
    this so that a share vector read next year is read under the codebook that
    produced it rather than under whatever this module says by then.
    """
    return {
        "schema": SCHEMA,
        "space": "oklab",
        "note": (
            "the ratified codebook's `anchor` is spelled `swatch` here; `anchor` already "
            "names the map a hard candidate set is built around, and it appears under that "
            "meaning on the pool rows a census reads"
        ),
        "geometry": {
            "hues": [{"hue": name, "degrees": degrees} for name, degrees in HUES],
            "tones": dict(TONES),
            "chroma_targets": dict(CHROMA_TARGETS),
            "headroom": HEADROOM,
            "neutrals": dict(NEUTRALS),
        },
        "assignment": {
            "kind": "gaussian",
            "sigma": SIGMA,
            "small_share": SMALL_SHARE,
            "share_thresholds": list(SHARE_THRESHOLDS),
        },
        "sampling": {"ramp_samples": RAMP_SAMPLES, "census_size": list(CENSUS_SIZE)},
        "swatches": list(swatches()),
        "closest_pairs": [
            {"distance": round(distance, 6), "swatches": [one, other]}
            for distance, one, other in closest_pairs()
        ],
    }


def weights(lab):
    """The soft assignment of every colour in `lab` to the fifty-two, `[..., 52]`.

    The exponent is taken against each pixel's *nearest* swatch rather than
    against zero. That is a numerical decision and not a modelling one: a colour
    far from every swatch — a saturated mid-tone the codebook has no cell near —
    otherwise makes every one of the fifty-two underflow to zero at this width,
    and the normalization that follows divides nothing by nothing. Shifting the
    exponent leaves every ratio identical and puts the largest term at one.
    """
    import numpy

    flat = numpy.asarray(lab, dtype=numpy.float64).reshape(-1, 3)
    table = points()
    # Through the Gram product rather than an explicit difference: a census reads
    # 14,400 pixels against 52 swatches per picture and there are twelve thousand
    # pictures, and materializing the [pixels, 52, 3] difference to square it is
    # the whole of the arithmetic. The expansion is one matmul, which is BLAS.
    # `maximum` puts back what the expansion loses to rounding — a squared
    # distance is never negative, and the exponent below would turn a -1e-17 into
    # a weight fractionally over one.
    squared = numpy.maximum(
        (flat * flat).sum(axis=1)[:, None]
        + (table * table).sum(axis=1)[None, :]
        - 2.0 * (flat @ table.T),
        0.0,
    )
    shifted = squared - squared.min(axis=1, keepdims=True)
    raw = numpy.exp(-shifted / (2.0 * SIGMA * SIGMA))
    return raw / raw.sum(axis=1, keepdims=True)


def distinct(rgb):
    """The distinct sRGB8 colours in a picture, with how many pixels hold each.

    A render is drawn by sweeping one gradient across a field, so its pixels are
    samples of a ramp and repeat heavily: at census resolution the median
    candidate holds about five thousand distinct colours out of fourteen
    thousand pixels, and some hold under three hundred. Assigning each colour
    once and weighting by its count is the same arithmetic — agreement with the
    per-pixel computation is at 6e-15, which is float noise — for a third of the
    work.
    """
    import numpy

    flat = numpy.asarray(rgb).reshape(-1, 3).astype(numpy.uint32)
    packed = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
    values, counts = numpy.unique(packed, return_counts=True)
    colours = numpy.stack(
        [(values >> 16) & 255, (values >> 8) & 255, values & 255], axis=-1
    ).astype(numpy.uint8)
    return colours, counts


def shares(lab, counts=None):
    """One share vector over the fifty-two: the mean soft assignment of these colours.

    `counts` weights each colour by how many pixels held it — what [`distinct`]
    hands back. Without it every row of `lab` counts once, which is what a
    gradient's evenly spaced samples want.
    """
    import numpy

    assigned = weights(lab)
    if counts is None:
        return assigned.mean(axis=0)
    weighting = numpy.asarray(counts, dtype=numpy.float64)
    return (assigned * weighting[:, None]).sum(axis=0) / weighting.sum()


def entropy_bits(share) -> float:
    """The Shannon entropy of a share vector, in bits. Zero to log2(52) = 5.70."""
    import numpy

    vector = numpy.asarray(share, dtype=numpy.float64)
    live = vector[vector > 1e-12]
    return float(-(live * numpy.log2(live)).sum())


def census(lab, counts=None) -> dict:
    """Everything the codebook says about one population of colours.

    The share vector rounded for storage, which swatch dominates it, how spread it
    is, and how many swatches are present at all. One shape whether the colours
    came from a gradient or from a picture, so the four stages report one table.
    """
    import numpy

    share = shares(lab, counts)
    labels = names()
    dominant = int(numpy.argmax(share))
    return {
        "shares": {
            labels[index]: round(float(share[index]), 6)
            for index in range(len(labels))
            if share[index] >= 1e-4
        },
        "dominant": labels[dominant],
        "dominant_share": round(float(share[dominant]), 6),
        "entropy_bits": round(entropy_bits(share), 4),
        "present": int((share >= SMALL_SHARE).sum()),
    }


def of_ramp(colormap: str, samples: int = RAMP_SAMPLES) -> dict:
    """One colormap's census, over the gradient a render of it really shows.

    Through [`space.spent`], which folds a sequential map and sweeps a cyclic one
    once — `mirror = the map is not cyclic`, the rule
    [`fractal_wallpapers.models.palette_sets.recipe_for`] owns and the engine
    enforces by refusing to fold a cyclic map at all. Read off the map's own
    `kind` here as everywhere else, never off a caller.
    """
    from fractal_wallpapers.palettes import space

    try:
        ramp = space.spent(colormap, samples)
    except space.SpaceError as refusal:
        raise CodebookError(str(refusal)) from refusal
    return census(space.oklab(ramp))


def pixels(picture: Path):
    """One picture's pixels at census resolution, as sRGB8.

    JPEG's own scaled decode does the downsampling — `draft` asks libjpeg for a
    fraction of the stored size, which costs a fraction of the work and never
    builds the full-size image. Both sizes this project stores land on
    [`CENSUS_SIZE`] exactly, so nothing is resampled; anything else is brought to
    it by nearest neighbour, which keeps every sample a colour that is really in
    the picture rather than an average of two that are not.
    """
    import numpy
    from PIL import Image

    path = Path(picture)
    if not path.is_file():
        raise CodebookError(f"{path} is not there, so it cannot be censused")
    with Image.open(path) as opened:
        opened.draft("RGB", CENSUS_SIZE)
        image = opened.convert("RGB")
        if image.size != CENSUS_SIZE:
            image = image.resize(CENSUS_SIZE, Image.NEAREST)
        return numpy.asarray(image, dtype=numpy.uint8)


def of_picture(picture: Path) -> dict:
    """One picture's census, at [`CENSUS_SIZE`], over its distinct colours."""
    from fractal_wallpapers.palettes import space

    colours, counts = distinct(pixels(picture))
    return census(space.oklab(colours), counts)


def rollup(share: dict) -> dict:
    """One share vector collapsed onto the twelve hue families and the neutrals.

    The reading granularity for anything thin. Fifty-two cells over eighty
    rejected candidates is one and a half per cell, which is noise wearing a
    number; thirteen families over the same rows is a table somebody can rule
    from. The artifact keeps all fifty-two either way.
    """
    families: dict[str, float] = {name: 0.0 for name, _ in HUES}
    families["neutral"] = 0.0
    for entry in swatches():
        value = float(share.get(entry["swatch"], 0.0))
        families["neutral" if entry["kind"] == "neutral" else entry["hue"]] += value
    return {name: round(value, 6) for name, value in families.items()}


__all__ = [
    "CENSUS_SIZE",
    "CHROMA_TARGETS",
    "HEADROOM",
    "HUES",
    "NEUTRALS",
    "RAMP_SAMPLES",
    "SCHEMA",
    "SHARE_THRESHOLDS",
    "SIGMA",
    "SMALL_SHARE",
    "TONES",
    "CodebookError",
    "census",
    "closest_pairs",
    "distinct",
    "document",
    "entropy_bits",
    "max_chroma",
    "names",
    "of_picture",
    "of_ramp",
    "pixels",
    "points",
    "rollup",
    "shares",
    "swatches",
    "weights",
]
