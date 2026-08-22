"""One map's gradient as a picture: the ramp the renderer really spends.

A figure that shows a colormap has to show the *same* gradient a render of it
would. That is a stronger requirement than it sounds, because a colormap file is
control points and the gradient is what the engine's bake makes of them — OKLab
interpolation into a 4096-entry table, folded first where the recipe says
`mirror`. A strip drawn by interpolating the stops in Python would be a **second
densifier**, and the day the two disagreed the article would be illustrating a
gradient nothing renders.

So nothing here draws anything. This module writes a **field** — a horizontal
ramp of scalars, in the dump format the engine already reads — and hands it to
`recolor`. Rust makes every pixel of the strip, through the same bake, the same
table and the same fold as a wallpaper. The strip is a render of a colormap in
the most literal sense available.

## Folded where sequential, by the map's own `kind`

`mirror` defaults to the rule the whole repository colours by: a sequential map
is folded to hide the seam its two ends would otherwise show, a cyclic one is
not. That is read off the map, never off a caller — see
[`fractal_wallpapers.models.palette_sets.recipe_for`], which owns it. A caller
that wants the other picture — the unfolded ramp of a sequential map, which is
what a fold-free render like the tile floor's second reservation actually shows —
says so, and the strip records which it drew.

## The ends hold flat for half a percent, and that is the coloring's own doing

The coloring stage normalizes a field against its own 0.5th and 99.5th
percentiles, and clamps outside them. A ramp is no exception: the outer half
percent of the strip's width is the end colour held flat, and the middle 99% is
the gradient swept exactly once. It cannot be compensated for — the stretch is
affine-invariant, so no rescaling of the ramp moves it — and it should not be,
because it is what the same coloring does to every render this project makes. On
a cyclic map, and on a folded sequential one, both ends are the same colour
anyway, so what it costs is a hairline of flat at each edge.
"""

from __future__ import annotations

import json
import struct
import tempfile
from pathlib import Path

from fractal_wallpapers import engine

#: What a strip is drawn at when nobody says otherwise. Wide enough that a map
#: with one narrow band still shows it, short enough to sit under a paragraph.
WIDTH = 1600
HEIGHT = 120

#: The dump record's constants for a field this module writes. Stated rather
#: than implied: the engine refuses a record whose dtype or layout it cannot
#: read, which is what stops a field being read as a picture.
DTYPE = "f32_le"
LAYOUT = "row_major"

#: The location a synthetic field records. Nothing reads it — `recolor` takes the
#: grid, the curve and the map from the record and never the place — but the
#: record's shape requires one, and a strip is not of anywhere.
NOWHERE = {
    "family": "mandelbrot",
    "degree": 2,
    "center_re": "0",
    "center_im": "0",
    "width": "3",
}


class StripError(RuntimeError):
    """A strip cannot be drawn."""


def ramp(width: int, height: int) -> bytes:
    """A horizontal ramp as the engine's field format: little-endian `f32`, rows first.

    Every row is the same sweep, so the strip is a gradient and not a picture of
    one. `width - 1` in the denominator puts the last column at exactly 1.0,
    which is the colour the map closes on.
    """
    if width < 2 or height < 1:
        raise StripError(f"a strip needs at least 2×1 samples, got {width}×{height}")
    row = struct.pack(f"<{width}f", *(index / (width - 1) for index in range(width)))
    return row * height


def record(colormap: str, width: int, height: int, field_file: str) -> dict:
    """The sidecar that says what the ramp is, in the shape `recolor` reads.

    `supersample` is 1: there is nothing to antialias in a ramp, and a
    supersampled one would only average neighbouring gradient positions — which
    is what the gradient already is.
    """
    return {
        "schema": 1,
        "mode": "smooth",
        "field": {"kind": "smooth"},
        "transform": "linear",
        "colormap": colormap,
        "location": dict(NOWHERE),
        "maxiter": 1,
        "resolution": [int(width), int(height)],
        "supersample": 1,
        "samples": [int(width), int(height)],
        "interior_fraction": 0.0,
        "dtype": DTYPE,
        "layout": LAYOUT,
        "field_file": field_file,
    }


def mirror_for(colormap: str, override: bool | None = None) -> bool:
    """Whether this map is folded: the pipeline's rule, unless a caller overrode it."""
    if override is not None:
        return bool(override)
    from fractal_wallpapers.models import palette_sets

    return bool(palette_sets.recipe_for(colormap, palette_sets.cyclic())["mirror"])


def draw(
    colormap: str,
    output: Path,
    width: int = WIDTH,
    height: int = HEIGHT,
    mirror: bool | None = None,
    colormap_dir: Path | None = None,
) -> dict:
    """Draw one map's gradient to `output`, and return what was drawn.

    The ramp lands in a temporary directory that goes away with the call: it is
    an argument to the engine, not an artifact, and keeping it would make the
    strip a two-file thing to clean up.
    """
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.paths import colormap_dir as tracked_maps

    directory = Path(colormap_dir) if colormap_dir is not None else tracked_maps()
    if not (directory / f"{colormap}.json").is_file():
        raise StripError(f"{directory / f'{colormap}.json'} is missing — no map, no gradient")

    folded = mirror_for(colormap, mirror)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="palette_strip_") as scratch:
        field = Path(scratch) / "ramp.f32"
        field.write_bytes(ramp(int(width), int(height)))
        field.with_suffix(".json").write_text(
            json.dumps(record(colormap, int(width), int(height), field.name)),
            encoding="utf-8",
            newline="\n",
        )
        report = engine.recolor(
            {
                "schema": 1,
                "field": str(field),
                "colormap": colormap,
                "colormap_dir": str(directory),
                "palette": finished.recipe(mirror=folded),
                "output": str(output),
            }
        )
    return {
        "colormap": colormap,
        "mirror": folded,
        "resolution": [int(width), int(height)],
        "output": str(output),
        "seconds": report.get("seconds"),
    }


def names_from(manifest: Path) -> list[str]:
    """The map names in a manifest: one to a line, `#` starts a comment.

    A list of arguments rather than a record, which is why it is not JSONL: a
    batch subcommand takes a manifest because a Windows command line overflows
    long before the batch does, and what it needs to carry here is names.
    """
    lines = Path(manifest).read_text(encoding="utf-8").splitlines()
    names = [line.split("#", 1)[0].strip() for line in lines]
    return [name for name in names if name]


__all__ = [
    "DTYPE",
    "HEIGHT",
    "LAYOUT",
    "NOWHERE",
    "WIDTH",
    "StripError",
    "draw",
    "mirror_for",
    "names_from",
    "ramp",
    "record",
]
