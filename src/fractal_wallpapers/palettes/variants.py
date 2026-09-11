"""Named variants of one colormap: a single axis moved, baked into the stops.

A candidate set asks *which of these thirty-two maps suits this location*. This
module asks a different question — *is this map better a quarter-turn round, or
reversed, or half as saturated* — and it answers it the only way the render path
can be told about: by making a **new map**. The recipe key derives through
[`models.renders.spec_of`] minus `colormap_dir`, so a picture drawn under its
base map's name would be that base map's key wearing a different gradient, and
two different pictures under one key is the hole
[`curation.label_migration`] left twice.

So every variant here is **distinctly named**, mechanically, by the axis and the
dose that made it: `<base>~<axis>-<dose>`. `~` is the mark because no map in the
tracked library carries one, so a name splits back into its base at the first
occurrence and a reader can tell a variant from a map at a glance.

## Nothing is resampled

Every map this repository tracks carries evenly spaced stops with an explicit
closing stop at position 1.0, so the four *positional* axes — phase, reversal,
repetition, cyclicity — are exact permutations and tilings of the stop colours
the base map already has. No interpolation happens on this side at all, which
means the identity variant is the base map byte for byte and a delta measured
against the base is the axis and not a resampling artifact. Only the two Oklab
axes touch a colour, and they touch each stop independently.

## The two Oklab axes go out through the gamut fit and not through a clip

Scaling chroma up, or lightness in either direction, walks colours out of the
sRGB cube. Clipping each channel independently rotates hue and moves lightness,
which is exactly what a *lightness* rescale must not do, so both axes land
through [`coloring.autolevel.gamut_fit`] — the same bisection on chroma the
autolevel operator already uses, lightness kept. A variant therefore reports how
many of its stops the fit had to pull back, which is the honest reading of how
much of a dose actually arrived.

## Cyclicity is TWO facts and they have to move together

The engine refuses to fold a cyclic map — `colormap.rs`'s *colormap is cyclic, so
folding it would halve the cycle it was drawn to have* — and production folds
every map that is not cyclic. So a map's `kind` and the palette recipe's `mirror`
are one decision spelled twice, and [`mirror_for`] is the one spelling of it here.
A caller that flips a kind and leaves `mirror` alone gets an engine error on a
sequential-to-cyclic flip and a seam on the other one.

## What a positional axis does to a SEQUENTIAL map

Rotating or repeating a gradient whose ends do not meet slams those ends
together. That is not a defect of the derivation — it is what the axis *is* on a
map of that kind, and the fold the engine applies afterwards moves the seam into
the middle of the sweep rather than removing it. [`seams`] says how many a
variant carries so a reading can be split on it.

**Nothing here writes into the tracked library.** [`write`] takes a directory and
a variant goes wherever its leg keeps its maps; admitting one to
`data/palettes/` is a separate decision, and the things that would have to be
rebuilt for it are named in `palettes/README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

#: What separates a base map's name from the axis that varied it. `~` because no
#: map in the tracked library carries one, so `name.partition(MARK)` recovers the
#: base of a variant and leaves an ordinary map whole.
MARK = "~"

#: …and what separates an axis from its dose. A hyphen, which map names do carry
#: — `river-of-light-25` — and that is fine, because the split that matters is on
#: [`MARK`] and this one only ever happens to the right of it.
DOSE_MARK = "-"

#: The two kinds a colormap document can declare, which is the engine's own
#: `Kind` enum and not a list of this module's own.
CYCLIC = "cyclic"
SEQUENTIAL = "sequential"

#: How much larger than a ramp's ninetieth-percentile step a step has to be
#: before [`seams`] calls it a seam. Two and a half, which counts `jet`'s 128-code
#: wrap against its 40-code ninetieth and leaves the ordinary pace of every map in
#: the library alone.
SEAM_FACTOR = 2.5

#: …and the floor under that bar, in sRGB8 codes. A 512-stop conversion's steps
#: are a couple of codes apart, and a factor over that alone would call any
#: ordinary detail a seam.
SEAM_FLOOR = 16.0


class VariantError(RuntimeError):
    """A variant cannot be derived."""


def mirror_for(kind: str) -> bool:
    """Whether a render through a map of this `kind` folds it.

    THE one spelling of the pair. The engine refuses `mirror` on a cyclic map and
    production folds everything else, so the two are one decision — and a variant
    that moves `kind` has to move this with it or the render is refused.
    """
    return str(kind) != CYCLIC


def other_kind(kind: str) -> str:
    """The kind a cyclicity flip lands on."""
    return SEQUENTIAL if str(kind) == CYCLIC else CYCLIC


def _stops_of(document: dict) -> list:
    stops = [
        [float(position), [int(value) for value in rgb]] for position, rgb in document["stops"]
    ]
    if len(stops) < 2:
        raise VariantError(f"{document.get('name')!r} carries {len(stops)} stops; a ramp needs two")
    return stops


def _even(stops: list) -> bool:
    """Whether the stops sit on an even grid from 0.0 to 1.0.

    The precondition every positional axis here rests on: an even grid is what
    makes a rotation index arithmetic rather than an interpolation. Every map in
    the tracked library satisfies it — `palettes.library_import.stops_of` is what
    put them on it — so this is a guard against a hand-made document, not a
    branch the library ever takes.
    """
    last = len(stops) - 1
    if stops[0][0] != 0.0 or stops[-1][0] != 1.0:
        return False
    return all(abs(position - index / last) < 1e-9 for index, (position, _) in enumerate(stops))


def _at(colours: list) -> list:
    """A list of colours as stops on the even grid they imply."""
    last = len(colours) - 1
    return [[index / last, list(rgb)] for index, rgb in enumerate(colours)]


def seams(stops: list, kind: str) -> int:
    """How many places this ramp jumps — the seam count a positional axis buys.

    **Measured off the stops and not counted off the recipe.** A rotation of a
    map whose two ends happen to be near each other buys no visible seam and
    should not be reported as carrying one, and a *cyclic* map carries none by
    construction however it is rotated or tiled. What a sequential map picks up
    is one per fold-back: the place where its far end returns to its near one,
    which a rotation moves into the middle of the sweep and a repetition
    reproduces once per tile.

    The bar is [`SEAM_FACTOR`] times the ramp's own ninetieth-percentile step,
    floored at [`SEAM_FLOOR`] codes: a seam is a jump the gradient does not
    otherwise make, and denominating it in the ramp's own pace is what lets one
    rule read a 33-stop `jet` and a 512-stop wallpaper conversion. A median would
    not do it — `jet`'s wrap is 128 codes against a median interior step of about
    32, and eight medians is over the wrap.

    `kind` is taken for the same reason the rest of this module takes it: a
    cyclic ramp is read as a loop, so the pair at its ends is a step like any
    other and the engine's single sweep never reaches it.
    """
    if str(kind) == CYCLIC:
        return 0
    steps = [
        max(abs(a - b) for a, b in zip(stops[index][1], stops[index + 1][1], strict=True))
        for index in range(len(stops) - 1)
    ]
    if not steps:
        return 0
    ordered = sorted(steps)
    ninetieth = ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]
    return sum(1 for step in steps if step > max(SEAM_FACTOR * ninetieth, SEAM_FLOOR))


# --------------------------------------------------------------------------- #
# The axes.
# --------------------------------------------------------------------------- #
def phase(document: dict, thousandths: int) -> tuple[list, str]:
    """The gradient rotated `thousandths/1000` of a turn, read as a loop.

    The closing stop is dropped, the rest are rolled by whole positions, and a
    new closing stop is written back — so the result is a ramp of exactly the
    same length carrying exactly the same colours in a different order. The dose
    a caller asks for is rounded to a whole stop and [`realised`] says what
    actually landed, because a 511-stop map cannot be rotated by an eighth.
    """
    stops = _stops_of(document)
    open_ramp = [rgb for _position, rgb in stops[:-1]]
    width = len(open_ramp)
    step = int(round(float(thousandths) / 1000.0 * width)) % width
    rolled = open_ramp[step:] + open_ramp[:step]
    return _at([*rolled, rolled[0]]), document["kind"]


def reverse(document: dict) -> tuple[list, str]:
    """The gradient read from its far end back to its near one.

    The whole ramp reversed, closing stop included, so a cyclic map stays closed
    and a sequential one keeps both of its ends.
    """
    stops = _stops_of(document)
    return _at([rgb for _position, rgb in reversed(stops)]), document["kind"]


def repeat(document: dict, times: int) -> tuple[list, str]:
    """The gradient laid end to end `times` over, at its own resolution.

    Not a resample: the open ramp is tiled, so a map with 512 stops repeated
    three times carries 1,534 of them and every colour in it is one the base map
    already had.
    """
    if int(times) < 2:
        raise VariantError(f"a repetition of {times} is the base map, not a variant")
    stops = _stops_of(document)
    open_ramp = [rgb for _position, rgb in stops[:-1]]
    tiled = open_ramp * int(times)
    return _at([*tiled, tiled[0]]), document["kind"]


def flip_kind(document: dict) -> tuple[list, str]:
    """The same gradient declared the other kind, so production folds it or stops.

    The one axis that changes no colour at all. What it changes is whether the
    engine bakes an out-and-back, which is a different picture at every mode and
    is the reason `mirror` travels with it — see [`mirror_for`].
    """
    return _stops_of(document), other_kind(document["kind"])


def _rescaled(document: dict, scale: float, axis: str) -> tuple[list, str, int]:
    """Every stop's Oklab chroma or lightness scaled, then fitted back to gamut."""
    import numpy

    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.palettes import space

    stops = _stops_of(document)
    lab = space.oklab(numpy.asarray([rgb for _position, rgb in stops], dtype=numpy.float64))
    moved = lab.copy()
    if axis == "chroma":
        moved[:, 1:] *= float(scale)
    else:
        moved[:, 0] = numpy.clip(lab[:, 0] * float(scale), 0.0, 1.0)
    fitted = autolevel.gamut_fit(moved)
    # Counted on the ROUND TRIP and not on the fit's own bookkeeping: what a
    # reading wants to know is how much of the dose survived to sRGB8, and a stop
    # the fit left alone can still lose its dose to the 8-bit rounding.
    back = space.oklab(fitted.astype(numpy.float64))
    if axis == "chroma":
        wanted = numpy.hypot(moved[:, 1], moved[:, 2])
        got = numpy.hypot(back[:, 1], back[:, 2])
    else:
        wanted, got = moved[:, 0], back[:, 0]
    pulled = int(numpy.count_nonzero(numpy.abs(got - wanted) > 0.01))
    colours = [[int(value) for value in rgb] for rgb in fitted]
    return _at(colours), document["kind"], pulled


def chroma(document: dict, hundredths: int) -> tuple[list, str, int]:
    """Every stop's Oklab chroma scaled by `hundredths/100`, lightness kept."""
    return _rescaled(document, float(hundredths) / 100.0, "chroma")


def lightness(document: dict, hundredths: int) -> tuple[list, str, int]:
    """Every stop's Oklab lightness scaled by `hundredths/100`, hue and chroma kept.

    Kept *where the gamut allows*. Lightness is the axis the caller asked to
    move, so the fit spends chroma to keep it — which is the opposite trade from
    [`coloring.autolevel.cap_lightness`], where lightness is the thing being
    derived and chroma is what must survive.
    """
    return _rescaled(document, float(hundredths) / 100.0, "lightness")


#: Every axis, and the dose each is spelled in. The dose is an **integer** in the
#: unit named here and never a float, so a variant's name is exact and sorts.
AXES: dict = {
    "phase": "thousandths of a full turn",
    "reverse": "no dose",
    "repeat": "how many times the ramp is laid down",
    "kind": "the kind it is declared instead",
    "chroma": "hundredths of the base chroma",
    "light": "hundredths of the base lightness",
}

#: The doses this repository's first sweep of the axis ran, one entry a variant.
#: Twelve, inside the five-to-twenty a smoke was sized for: four phases because
#: rotation is the axis a cyclic library has most of, two repetitions, and a
#: symmetric pair either side of 1.0 on each Oklab axis so a direction can be
#: read rather than only a magnitude.
DOSES: tuple[tuple[str, int | None], ...] = (
    ("phase", 125),
    ("phase", 250),
    ("phase", 500),
    ("phase", 750),
    ("reverse", None),
    ("repeat", 2),
    ("repeat", 3),
    ("kind", None),
    ("chroma", 50),
    ("chroma", 150),
    ("light", 80),
    ("light", 120),
)


def name_of(base: str, axis: str, dose: int | None) -> str:
    """`<base>~<axis>` or `<base>~<axis>-<dose>`. Stable, and a pure function.

    Zero-padded to three digits so a directory listing sorts by dose rather than
    by string, and so `phase-050` and `phase-500` cannot be confused by eye.
    `repeat` is the one axis whose dose is a count rather than a hundredth, and
    it is written as it reads.
    """
    if axis not in AXES:
        raise VariantError(f"{axis!r} is not an axis; the six are {sorted(AXES)}")
    if dose is None:
        return f"{base}{MARK}{axis}"
    token = f"{int(dose)}" if axis == "repeat" else f"{int(dose):03d}"
    return f"{base}{MARK}{axis}{DOSE_MARK}{token}"


def base_of(name: str) -> str:
    """The map a variant was derived from; the name itself where it is not one."""
    return str(name).partition(MARK)[0]


def is_variant(name: str) -> bool:
    return MARK in str(name)


def derive(document: dict, axis: str, dose: int | None) -> dict:
    """One variant of one map, as the colormap document the engine reads.

    The returned document carries a `variant` block beside the five members the
    engine wants — the base, the axis, the dose asked for and the dose that
    landed, the seam count and how many stops the gamut fit pulled back. The
    engine ignores it (`ColormapFile` names the members it reads and `source` is
    provenance), and a leg reading a directory of these does not have to
    re-derive what made each one.
    """
    if not _even(_stops_of(document)):
        raise VariantError(
            f"{document.get('name')!r} does not sit on an even grid from 0.0 to 1.0, so a "
            f"rotation of it would be an interpolation rather than a permutation. Every map "
            f"in the tracked library does; a hand-made document may not."
        )
    base = str(document["name"])
    pulled = 0
    if axis == "phase":
        stops, kind = phase(document, int(dose))
    elif axis == "reverse":
        stops, kind = reverse(document)
    elif axis == "repeat":
        stops, kind = repeat(document, int(dose))
    elif axis == "kind":
        stops, kind = flip_kind(document)
    elif axis == "chroma":
        stops, kind, pulled = chroma(document, int(dose))
    elif axis == "light":
        stops, kind, pulled = lightness(document, int(dose))
    else:
        raise VariantError(f"{axis!r} is not an axis; the six are {sorted(AXES)}")
    name = name_of(base, axis, dose)
    width = len(_stops_of(document)) - 1
    landed = None if axis != "phase" else round(int(round(dose / 1000.0 * width)) / width, 6)
    return {
        "schema": 1,
        "name": name,
        "kind": kind,
        "source": f"{base}, varied on {axis} by {AXES[axis]} = {dose}",
        "stops": stops,
        "variant": {
            "base": base,
            "axis": axis,
            "dose": dose,
            "dose_unit": AXES[axis],
            # The turn a rotation actually made, which is the dose rounded to a
            # whole stop. `None` off the phase axis, where a dose is exact.
            "landed": landed,
            "base_kind": document["kind"],
            "mirror": mirror_for(kind),
            "stops": len(stops),
            "seams": seams(stops, kind),
            "base_seams": seams(_stops_of(document), document["kind"]),
            "gamut_pulled": pulled,
        },
    }


def family(document: dict, doses=DOSES) -> list[dict]:
    """Every variant of one map, in the order [`DOSES`] names them."""
    return [derive(document, axis, dose) for axis, dose in doses]


def read(path: Path) -> dict:
    """One colormap document off disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(document: dict, directory: Path) -> Path:
    """One variant into a directory of its own. **Never the tracked library.**

    `newline="\\n"` like everything else that writes a text file here, so a
    variant directory that ever did get tracked would not arrive as a whole-file
    diff. The `directory` is required rather than defaulted: a default would make
    `data/palettes/` one forgotten argument away, and admitting a variant to the
    library is a decision with a carrier table and a palette grouping behind it.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document['name']}.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8", newline="\n")
    return path


__all__ = [
    "AXES",
    "CYCLIC",
    "SEAM_FACTOR",
    "SEAM_FLOOR",
    "DOSES",
    "DOSE_MARK",
    "MARK",
    "SEQUENTIAL",
    "VariantError",
    "base_of",
    "chroma",
    "derive",
    "family",
    "flip_kind",
    "is_variant",
    "lightness",
    "mirror_for",
    "name_of",
    "other_kind",
    "phase",
    "read",
    "repeat",
    "reverse",
    "seams",
    "write",
]
