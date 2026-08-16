"""Autolevel: pull a render's tone onto the band, or leave it exactly alone.

A colormap is a ramp somebody drew, and it was drawn without knowing what field
it would be spent on. Sweep it across a location whose escape times all bunch at
one end and the picture comes out muddy, or blown out, or flat — not because the
map is bad but because this location spends it badly. This operator measures the
finished render, decides whether its tone sits inside the band of finished
wallpapers that are already good ([`band`]), and if it does not, pushes a
monotone tone curve through the *map's own stops* and renders again.

## The lever: measure the picture, apply on the palette

Every pixel of a palette-mapped render is a lookup into the map. So a monotone
curve `C` applied to the lookup table's Oklab lightness moves every pixel's
lightness by exactly `C` — exactly per sample, and to within antialiasing after
reconstruction. That is why the correction is *measured* on the rendered bytes
and *applied* on the colormap: the two are the same map, and applying it to the
stops keeps every pixel in the engine where it belongs. Python here reads an
image and writes a colour ramp; it does not make a pixel.

## The rule

* Three statistics per render, each projected onto its band — inside, itself;
  outside, the nearest edge. That is the smallest move that reaches the
  acceptable set, so the pull needs no strength parameter.
* **In band on all three is the exact identity**, and the operator then returns
  the base render's own file rather than making a second one. Being always-on and
  mostly identity is structural, not a hope: the curve is skipped, not applied at
  strength zero.
* The curve is piecewise with linear tails, so `0 → 0` and `1 → 1` always: a true
  black is never lifted and a true white never dimmed.
* Two chroma guards, and neither can ever turn a correction *on*. In
  **measurement**, the black point is read over neutral pixels only and declared
  unmeasurable when that subset is thin or its own black sits far above the
  all-pixel one, which leaves the dark end alone. In **application**, each stop's
  new lightness is walked back until at least [`CHROMA_RETAIN`] of its chroma
  survives the pull back into gamut.

## The direct-trap family is excluded by kind, not disabled inside the operator

A direct trap has no field behind it: its colour key is how near the orbit came,
and the picture is a thin bright figure over a flat ground. Its tone statistics
describe the ground rather than the picture, so the band says nothing about it.
[`applies_to`] reads the mode's kind out of the engine's own catalog and answers
no — at the one place that decides, rather than as a special case buried in the
measurement where a new direct mode would silently acquire a tone curve.

## The stamp replays

Everything the curve is a function of is stamped: the band it projected onto with
that record's own sha256, the three statistics it was derived from, the curve's
own coefficients. [`stops_from_stamp`] rebuilds the exact stop list from the
stamp alone — no image, no re-measurement — so a release render is reproducible
from its record and a row that acted can be checked against the picture it
claims to be.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.palettes import space

#: The operator's own name and version, stamped on every row it writes. A curve
#: derived by a different rule is a different operator and says so.
OPERATOR = "band_autolevel/v1"

#: The switch, and its one override. The default is what the tree ships; the
#: environment variable sets it for one run without editing source, which is how
#: a before/after pair is produced and how a leveled row is falsified.
SWITCH_DEFAULT = True
SWITCH_ENV = "FRACTAL_WALLPAPERS_AUTOLEVEL"

#: The three statistics, in the order every record writes them.
STATISTICS = ("black_pt", "white_pt", "mid")

#: What each one is, carried into the band record so it is defined where it is
#: measured rather than only where it is read.
DEFINITIONS = {
    "black_pt": (
        "P0.5 of Oklab L over NEUTRAL pixels (chroma <= 0.06); null when the chroma guard "
        "declares it unmeasurable (neutral share < 0.05, or a neutral black more than 0.10 "
        "above the all-pixel black)"
    ),
    "white_pt": "P99.5 of Oklab L, every pixel",
    "mid": "median Oklab L over the structure mask (L > 0.04)",
}

#: The robust black and white percentiles of Oklab L.
CLIP_LO, CLIP_HI = 0.5, 99.5

#: Oklab L floor of the structure mask the midtone is read over.
MASK_L = 0.04

#: Oklab chroma at or below which a pixel reads as neutral.
CHROMA_NEUTRAL = 0.06

#: A neutral subset thinner than this share reads no black point.
NEUTRAL_FRACTION_MIN = 0.05

#: A neutral black this far above the all-pixel black means the dark tail is
#: coloured rather than dim, and the black end is left alone.
DARK_MARGIN = 0.10

#: How few neutral pixels are too few for a percentile to mean anything.
NEUTRAL_PIXELS_MIN = 64

#: The share of a stop's chroma that must survive the gamut pull back.
CHROMA_RETAIN = 0.85

#: The band the curve's exponent is clamped to: at most a factor of two either
#: way, so no location's midtone can demand an arbitrary re-shaping.
EXPONENT_CLAMP = 2.0

#: A render whose white and black points are closer than this has no tonal range
#: to curve, and no curve is proposed.
MIN_RANGE = 0.05

#: How far each colormap segment is subdivided before the curve is applied. The
#: engine interpolates its stops in Oklab, and so does the subdivision, so this
#: is the identity for the palette to sRGB8 rounding and only makes the curve's
#: sampling finer.
DENSIFY = 8

_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off", "")


class AutolevelError(RuntimeError):
    """The operator cannot do what it was asked."""


def enabled() -> bool:
    """Is the operator on for *this* render? Read at call time, never at import.

    An unparseable value reads as the default and never as its own state: a typo
    in an environment variable must not move a production colorize in either
    direction, and with the switch shipping on that means it must not quietly
    turn one off either.
    """
    raw = os.environ.get(SWITCH_ENV)
    if raw is None:
        return SWITCH_DEFAULT
    raw = raw.strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return SWITCH_DEFAULT


def applies_to(kind: str) -> bool:
    """Whether the operator has anything to say about a render of this coloring kind.

    `field` and `composite` spend the palette across a range and are what the
    band was measured on. `direct` is a trap figure over a flat ground: its tone
    statistics describe the ground, so it is excluded here — at the site that
    decides — rather than by a test inside the measurement.
    """
    return kind in ("field", "composite")


# --------------------------------------------------------------------------- #
# Measurement.
# --------------------------------------------------------------------------- #
def tone_stats(image) -> dict:
    """One rendered picture (`uint8 [H, W, 3]`) to the statistics the band is read on.

    `black_pt` is the guarded black point and is the one the rule acts on;
    `black_pt_all` sits beside it so a record can say which renders the guard
    silenced and by how much.
    """
    import numpy

    lab = space.oklab(numpy.asarray(image, dtype=numpy.float64))
    lightness = lab[..., 0]
    chroma = numpy.hypot(lab[..., 1], lab[..., 2])
    mask = lightness > MASK_L

    all_black = float(numpy.percentile(lightness, CLIP_LO))
    white = float(numpy.percentile(lightness, CLIP_HI))
    middle = float(numpy.median(lightness[mask] if mask.any() else lightness))

    neutral = chroma <= CHROMA_NEUTRAL
    share = float(neutral.mean())
    neutral_black = (
        float(numpy.percentile(lightness[neutral], CLIP_LO))
        if int(neutral.sum()) > NEUTRAL_PIXELS_MIN
        else None
    )
    if neutral_black is None or share < NEUTRAL_FRACTION_MIN:
        black, why = None, f"neutral pixels {share:.3f} < {NEUTRAL_FRACTION_MIN}"
    elif neutral_black - all_black > DARK_MARGIN:
        black, why = (
            None,
            f"chromatic dark tail (neutral black {neutral_black:.3f} vs all {all_black:.3f})",
        )
    else:
        black, why = neutral_black, None

    return {
        "black_pt": black,
        "black_unmeasurable": why,
        "black_pt_all": all_black,
        "black_pt_neutral": neutral_black,
        "neutral_fraction": share,
        "white_pt": white,
        "mid": middle,
        "mask_fraction": float(mask.mean()),
        "mean_L": float(lightness.mean()),
    }


def stats_of(path: Path) -> dict:
    """The statistics of a picture on disk."""
    import numpy
    from PIL import Image

    with Image.open(path) as opened:
        array = numpy.asarray(opened.convert("RGB"), dtype=numpy.uint8)
    return tone_stats(array)


# --------------------------------------------------------------------------- #
# The curve.
# --------------------------------------------------------------------------- #
def project(value: float, band: tuple[float, float]) -> tuple[float, int]:
    """`(projected value, side)` — side is `-1` below the band, `+1` above, `0` inside."""
    low, high = band
    if value < low:
        return low, -1
    if value > high:
        return high, +1
    return value, 0


def derive_curve(statistics: dict, bands: dict) -> dict:
    """The tone curve for one render, or a refusal that says why.

    ```text
    L <= b      L * lo/b                            (tail: 0 -> 0)
    b < L < w   lo + (hi - lo) * ((L-b)/(w-b))**p    (core)
    L >= w      hi + (1-hi) * (L-w)/(1-w)            (tail: 1 -> 1)
    ```

    with `lo` and `hi` the projected black and white points and `p` the exponent
    that carries the midtone to its own projection. The result is the exact
    identity when all three statistics are already in band, which is the whole
    reason the operator is safe to leave on.
    """
    import numpy

    measured_black = statistics["black_pt"]
    black = measured_black if measured_black is not None else statistics["black_pt_all"]
    white, middle = statistics["white_pt"], statistics["mid"]

    if white - black < MIN_RANGE:
        return {
            "applies": False,
            "reason": f"degenerate range w-b={white - black:.3f} < {MIN_RANGE}",
            "black_pt": black,
            "white_pt": white,
            "exponent": 1.0,
            "out_ends": [black, white],
        }

    # A band a statistic has no entry for leaves that end alone, exactly as the
    # chroma guard does — an absent band is a refusal to say, not a zero.
    if measured_black is None or "black_pt" not in bands:
        low, black_side = black, 0
    else:
        low, black_side = project(measured_black, bands["black_pt"])
    high, white_side = project(white, bands["white_pt"]) if "white_pt" in bands else (white, 0)
    target, mid_side = project(middle, bands["mid"]) if "mid" in bands else (middle, 0)

    position = (middle - black) / (white - black)
    wanted = (target - low) / (high - low) if high > low else 0.5
    if not (1e-4 < position < 1 - 1e-4) or not (1e-4 < wanted < 1 - 1e-4):
        exponent = 1.0
    else:
        exponent = float(numpy.log(wanted) / numpy.log(position))
    exponent = float(numpy.clip(exponent, 1.0 / EXPONENT_CLAMP, EXPONENT_CLAMP))

    identity = abs(low - black) < 1e-9 and abs(high - white) < 1e-9 and abs(exponent - 1.0) < 1e-9
    return {
        "applies": True,
        "reason": None,
        "black_pt": black,
        "white_pt": white,
        "mid_in": middle,
        "exponent": exponent,
        "out_ends": [low, high],
        "mid_target": target,
        "mid_norm": position,
        "sides": {"black_pt": black_side, "white_pt": white_side, "mid": mid_side},
        "black_guarded": measured_black is None,
        "identity": identity,
        "clamped": abs(exponent - EXPONENT_CLAMP) < 1e-9
        or abs(exponent - 1.0 / EXPONENT_CLAMP) < 1e-9,
    }


def apply_curve(lightness, curve: dict):
    """The piecewise curve over an array of Oklab lightness."""
    import numpy

    black, white = curve["black_pt"], curve["white_pt"]
    exponent = curve["exponent"]
    low, high = curve["out_ends"]
    lightness = numpy.asarray(lightness, dtype=numpy.float64)
    out = numpy.empty_like(lightness)
    below = lightness <= black
    above = lightness >= white
    core = ~(below | above)
    out[below] = lightness[below] * (low / black) if black > 1e-9 else low
    position = (lightness[core] - black) / max(white - black, 1e-9)
    out[core] = low + (high - low) * position**exponent
    out[above] = (
        high + (1.0 - high) * (lightness[above] - white) / (1.0 - white)
        if white < 1.0 - 1e-9
        else high
    )
    return out


# --------------------------------------------------------------------------- #
# Colormap surgery: subdivide, curve, cap the chroma loss, fit back into gamut.
# --------------------------------------------------------------------------- #
def densify(stops: list, factor: int = DENSIFY) -> tuple:
    """`(positions, Oklab)` — every segment subdivided, interpolated in Oklab.

    The engine bakes its lookup table by interpolating the stops in Oklab, so
    subdividing in the same space is the identity for the palette and only makes
    the tone curve's sampling finer.

    **There is no wrap segment, and adding one would be a bug.** Every colormap
    this repository tracks carries an explicit stop at position 0 *and* at
    position 1 — a cyclic map's last stop is an explicit closing stop back to the
    colour it opened with — and the engine's own interpolation holds the end
    colours beyond the outermost stops rather than wrapping. Folding position 1
    around to 0 would put two stops on top of each other and leave the ramp
    spanning only as far as the second-to-last one, which is a different palette
    rather than a finer sampling of this one. Whether the engine *mirrors* the
    result is a separate decision it makes from the map's own kind, and it makes
    it on the stops this returns.
    """
    import numpy

    ordered = sorted((float(p), [int(c) for c in rgb]) for p, rgb in stops)
    lab = space.oklab(numpy.asarray([rgb for _, rgb in ordered], dtype=numpy.float64))
    positions, colours = [], []
    for index in range(len(ordered) - 1):
        first, second = ordered[index][0], ordered[index + 1][0]
        for step in range(factor):
            fraction = step / factor
            positions.append(first + (second - first) * fraction)
            colours.append(lab[index] + (lab[index + 1] - lab[index]) * fraction)
    positions.append(ordered[-1][0])
    colours.append(lab[-1])
    return positions, numpy.asarray(colours, dtype=numpy.float64)


def _in_gamut(lab):
    """`(inside, sRGB)` over `[n, 3]`. Asked by round trip, because the conversion clips.

    Asking the *clipped* output whether it is in range always answers yes. An
    in-gamut colour survives Oklab → sRGB → Oklab unchanged and an out-of-gamut
    one does not, which is the only question that distinguishes them.
    """
    import numpy

    rgb = space.srgb(lab)
    return numpy.max(numpy.abs(space.oklab(rgb) - lab), axis=-1) < 1e-6, rgb


def gamut_fit(lab):
    """Oklab `[n, 3]` to sRGB8 `[n, 3]`, pulling back by **chroma**, never by channel.

    Clipping each channel independently rotates hue and moves lightness, which is
    the one axis the curve exists to control. So an out-of-gamut colour has its
    `a` and `b` scaled down by a bisection until it fits, and its lightness is
    kept.
    """
    import numpy

    lab = numpy.asarray(lab, dtype=numpy.float64)
    inside, rgb = _in_gamut(lab)
    outside = numpy.flatnonzero(~inside)
    if outside.size:
        subset = lab[outside]
        low = numpy.zeros(outside.size)
        high = numpy.ones(outside.size)
        for _ in range(28):
            middle = 0.5 * (low + high)
            fits, _ = _in_gamut(
                numpy.stack([subset[:, 0], subset[:, 1] * middle, subset[:, 2] * middle], axis=-1)
            )
            low = numpy.where(fits, middle, low)
            high = numpy.where(~fits, middle, high)
        _, fitted = _in_gamut(
            numpy.stack([subset[:, 0], subset[:, 1] * low, subset[:, 2] * low], axis=-1)
        )
        rgb[outside] = fitted
    return numpy.rint(numpy.clip(rgb, 0.0, 255.0)).astype(numpy.int64)


def _chroma_after(lab):
    """The chroma that survives the gamut pull back, measured back in Oklab."""
    import numpy

    out = space.oklab(gamut_fit(lab).astype(numpy.float64))
    return numpy.hypot(out[:, 1], out[:, 2])


def cap_lightness(before, after, green_red, blue_yellow, retain: float = CHROMA_RETAIN):
    """Walk each new lightness back until its stop keeps `retain` of its chroma.

    Only the direction that costs chroma is capped, and the walk-back target is
    the stop's own original lightness — where retention is one by construction,
    because the stop came from a real sRGB8 colour. So the bisection always has a
    valid bracket.
    """
    import numpy

    before = numpy.asarray(before, dtype=numpy.float64)
    after = numpy.asarray(after, dtype=numpy.float64)
    green_red = numpy.asarray(green_red, dtype=numpy.float64)
    blue_yellow = numpy.asarray(blue_yellow, dtype=numpy.float64)
    chroma = numpy.hypot(green_red, blue_yellow)

    out = after.copy()
    capped = numpy.zeros(before.shape, dtype=bool)
    candidates = numpy.flatnonzero((chroma >= 1e-6) & (numpy.abs(after - before) >= 1e-9))
    if not candidates.size:
        return out, capped

    kept = _chroma_after(
        numpy.stack([after[candidates], green_red[candidates], blue_yellow[candidates]], axis=-1)
    ) >= (retain * chroma[candidates])
    acting = candidates[~kept]
    if acting.size:
        good, bad = before[acting].copy(), after[acting].copy()
        a, b = green_red[acting], blue_yellow[acting]
        threshold = retain * chroma[acting]
        for _ in range(18):
            middle = 0.5 * (good + bad)
            fits = _chroma_after(numpy.stack([middle, a, b], axis=-1)) >= threshold
            good = numpy.where(fits, middle, good)
            bad = numpy.where(~fits, middle, bad)
        out[acting] = good
        capped[acting] = True
    return out, capped


def curved_stops(stops: list, curve: dict) -> tuple[list, int]:
    """`(stops, how many the chroma cap held back)` — the leveled colour ramp."""
    import numpy

    positions, lab = densify(stops)
    moved = apply_curve(lab[:, 0], curve)
    capped_lightness, capped = cap_lightness(lab[:, 0], moved, lab[:, 1], lab[:, 2])
    rgb = gamut_fit(numpy.stack([capped_lightness, lab[:, 1], lab[:, 2]], axis=-1))
    out = [
        [round(float(position), 9), [int(value) for value in row]]
        for position, row in zip(positions, rgb, strict=True)
    ]
    return out, int(capped.sum())


# --------------------------------------------------------------------------- #
# The stamp.
# --------------------------------------------------------------------------- #
def make_stamp(record: dict, curve: dict, statistics: dict, capped: int, stops: int, acted: bool):
    """What a render produced under the operator carries.

    The whole curve is stamped rather than a summary, because [`stops_from_stamp`]
    has to rebuild the exact stop list from this alone. `measured` is the *base*
    render's own statistics, which is what proves a candidate re-render is the
    render the stamp is about.
    """
    return {
        "operator": OPERATOR,
        "switch": "on",
        "acted": bool(acted),
        "band": {
            "path": record.get("_path"),
            "sha256": record.get("_sha256"),
            "derived": record.get("derived"),
            "n_images": record.get("n_images"),
            "bands": {name: list(edges) for name, edges in _bands(record).items()},
        },
        "curve": {
            key: curve.get(key)
            for key in (
                "applies",
                "reason",
                "identity",
                "black_pt",
                "white_pt",
                "mid_in",
                "exponent",
                "out_ends",
                "mid_target",
                "mid_norm",
                "sides",
                "black_guarded",
                "clamped",
            )
        },
        "chroma_cap": {"retain": CHROMA_RETAIN, "capped": int(capped), "stops": int(stops)},
        "measured": statistics,
    }


def stops_from_stamp(stamp: dict, stops: list) -> list:
    """Replay: the leveled stop list from the stamp and the map's own stops.

    Refuses a stamp that did not act. There is no curved ramp for an identity
    row — the render *is* the base map's — and handing back the map's own stops
    would quietly make "replayed" mean two different things.
    """
    if not stamp.get("acted"):
        raise AutolevelError(
            "this stamp records an identity row: the render is the base map's own and there "
            "is no curved stop list to replay."
        )
    curved, _ = curved_stops(stops, stamp["curve"])
    return curved


def _bands(record: dict) -> dict:
    from fractal_wallpapers.coloring import band as band_module

    return band_module.bands(record)


# --------------------------------------------------------------------------- #
# The one entry point.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Leveled:
    """What one render came out as: a picture, and the stamp (`None` = switch off)."""

    image: Path
    stamp: dict | None

    @property
    def acted(self) -> bool:
        return bool(self.stamp and self.stamp.get("acted"))


def overriding_colormap(name: str, stops: list, kind: str, directory: Path) -> Path:
    """Write one map's leveled stops as a colormap the engine can be pointed at.

    The `kind` rides along unchanged, so the engine's fold decision and its bake
    are bit-identical to the production call and only the stop colours differ.
    The file keeps the map's own name, so the render spec that names a colormap
    is the same spec with one directory changed.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "name": name,
                "kind": kind,
                "source": f"{name}, leveled by {OPERATOR} for one render",
                "stops": stops,
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def maybe_level(base: Path, colormap: dict, rerender, record: dict | None = None) -> Leveled:
    """THE switch, and the whole operator behind it.

    `base`      the render the caller already made through the unmodified map.
    `colormap`  `{"name", "stops", "kind", "mirror"}` — the map as the engine
                holds it, plus whether this render folds it.
    `rerender`  `stops -> Path`; called **only** when the curve actually acts, so
                an in-band render costs one measurement and comes back as its own
                file.

    With the switch off this is `(base, None)` and `rerender` is never called:
    the off path is the pre-operator path with one boolean read in front of it,
    which is what keeps it a live contract rather than dead code.
    """
    if not enabled():
        return Leveled(base, None)
    from fractal_wallpapers.coloring import band as band_module

    record = band_module.load() if record is None else record
    statistics = stats_of(base)
    curve = derive_curve(statistics, band_module.bands(record))
    acts = bool(curve.get("applies")) and not curve.get("identity")
    if not acts:
        return Leveled(base, make_stamp(record, curve, statistics, 0, 0, acted=False))
    stops, capped = curved_stops(colormap["stops"], curve)
    return Leveled(
        rerender(stops), make_stamp(record, curve, statistics, capped, len(stops), acted=True)
    )


__all__ = [
    "CHROMA_NEUTRAL",
    "CHROMA_RETAIN",
    "CLIP_HI",
    "CLIP_LO",
    "DEFINITIONS",
    "DENSIFY",
    "EXPONENT_CLAMP",
    "MASK_L",
    "MIN_RANGE",
    "OPERATOR",
    "STATISTICS",
    "SWITCH_DEFAULT",
    "SWITCH_ENV",
    "AutolevelError",
    "Leveled",
    "applies_to",
    "apply_curve",
    "cap_lightness",
    "curved_stops",
    "densify",
    "derive_curve",
    "enabled",
    "gamut_fit",
    "make_stamp",
    "maybe_level",
    "overriding_colormap",
    "project",
    "stats_of",
    "stops_from_stamp",
    "tone_stats",
]
