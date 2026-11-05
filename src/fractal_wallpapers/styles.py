"""Styles: named, declarative layer stacks the engine composites per sample.

A style file under `data/styles/<name>.json` is the stack the engine draws (its
`style` member, handed through the render spec's `style` key untouched) and the
provenance a reader wants beside it: the reference image it was made from, which
existing pieces it reuses, which primitives it added, and the colormap it was
fitted with. The engine never sees the provenance, and Python never composites a
pixel — this module only reads the file and writes a spec.

A style renders with **any** colormap. The suggested one is what the stack was
fitted against, not a requirement; the website will choose a style and a palette
independently. `data/styles/README.md` has the file format and the procedure for
turning a new reference image into a style.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import colormap_dir, repo_root

#: The one schema a style file carries today.
SCHEMA = 1


class StyleError(ValueError):
    """A style that does not exist or does not read."""


def styles_dir() -> Path:
    """Where the style files live."""
    return repo_root() / "data" / "styles"


def names() -> list[str]:
    """Every style there is, by file name; a style's `<name>.keeps.json` is not one."""
    return sorted(
        path.stem for path in styles_dir().glob("*.json") if not path.name.endswith(".keeps.json")
    )


def load(name: str) -> dict[str, Any]:
    """Read one style file and check its outer shape; the engine checks the stack.

    `name` is a style under `data/styles/`, or the path of a draft `.json` anywhere,
    which is how a style is tuned before it joins the library: a draft is held to the
    same shape except that its file name need not be its name.
    """
    draft = name.endswith(".json")
    path = Path(name) if draft else styles_dir() / f"{name}.json"
    if not path.is_file():
        raise StyleError(f"no style '{name}' under {styles_dir()}; there are: {', '.join(names())}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise StyleError(f"style '{name}' has schema {document.get('schema')}, expected {SCHEMA}")
    for key in ("name", "description", "reference", "reuses", "adds", "suggested_colormap"):
        if key not in document:
            raise StyleError(f"style '{name}' has no '{key}'")
    if "style" not in document:
        raise StyleError(f"style '{name}' has no 'style'")
    if document["style"].get("name") != document["name"]:
        raise StyleError(f"style '{name}': its stack is named '{document['style'].get('name')}'")
    if not draft and document["name"] != name:
        raise StyleError(f"style file '{name}.json' names itself '{document['name']}'")
    return document


def repeats(style: dict[str, Any]) -> bool:
    """Whether any palette layer runs the map more than once across the frame."""
    return any(
        layer.get("kind") == "palette" and float((layer.get("palette") or {}).get("cycles", 1)) > 1
        for layer in style["layers"]
    )


def is_cyclic(colormap: str) -> bool:
    """Whether a colormap's file says it meets itself."""
    path = colormap_dir() / f"{colormap}.json"
    if not path.is_file():
        raise StyleError(f"no colormap '{colormap}' under {colormap_dir()}")
    return json.loads(path.read_text(encoding="utf-8")).get("kind") == "cyclic"


def reference_path(document: dict[str, Any]) -> Path:
    """Where a style's reference picture is: its `folder` is a sibling of this checkout."""
    reference = document["reference"]
    return repo_root().parent / reference["folder"] / reference["image"]


#: The lightness statistics `tones` reports, in the order it prints them.
TONES = ("median", "p10", "p90", "white", "black")


def tones(path: Path, width: int = 640) -> dict[str, float]:
    """A picture's lightness distribution: what the tonal check compares.

    Lightness is CIE L* over 100, from the luminance of the decoded sRGB, read on a
    copy `width` pixels wide (the statistics are of areas, not of hairlines).
    `white` and `black` are the shares of the frame above 0.9 and below 0.1.
    """
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        image = image.resize((width, max(1, round(image.height * width / image.width))))
        rgb = np.asarray(image, dtype=np.float64) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    luminance = linear @ np.array([0.2126, 0.7152, 0.0722])
    knee = 6 / 29
    f = np.where(luminance > knee**3, np.cbrt(luminance), luminance / (3 * knee**2) + 4 / 29)
    lightness = (116 * f - 16) / 100
    return {
        "median": float(np.median(lightness)),
        "p10": float(np.percentile(lightness, 10)),
        "p90": float(np.percentile(lightness, 90)),
        "white": float((lightness > 0.9).mean()),
        "black": float((lightness < 0.1).mean()),
    }


#: How far a render's lightness may sit from its style's reference and still hold
#: the style's balance. Fitted on round one of `floating_on_dreams`, where Matt kept
#: three of ten and found the others far too light: the three kept sit within 0.017
#: of the reference's median and 0.020 of its p10, and every one of the seven dropped
#: is 0.032 to 0.126 above its median. The white share is a ceiling, not a band: a
#: palette that floods the frame with near-white (pink, at 0.21 to 0.26 against the
#: reference's 0.13) was dropped too.
TONE_BAND = {"median": 0.03, "p10": 0.05}
WHITE_ALLOWANCE = 0.05
BLACK_ALLOWANCE = 0.05


def tone_misses(stats: dict[str, float], reference: dict[str, float]) -> list[str]:
    """Each way a render's lightness misses its reference's; empty when it holds."""
    misses = [
        f"{key} {stats[key]:.3f} vs {reference[key]:.3f}"
        for key, band in TONE_BAND.items()
        if abs(stats[key] - reference[key]) > band
    ]
    for key, allowance in (("white", WHITE_ALLOWANCE), ("black", BLACK_ALLOWANCE)):
        if stats[key] > reference[key] + allowance:
            misses.append(f"{key} {stats[key]:.3f} vs {reference[key]:.3f}")
    return misses


def projected(style: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """The stack, its projection's members overridden by the location's own.

    A style's projection says how it looks at any place (`{"log_polar": {"turns": 4}}`);
    what only one place knows — the `twist` that straightens its spiral, where its
    vanishing point sits best in the frame — rides on the location record as the same
    shape, `{"projection": {"log_polar": {"twist": 0.21}}}`, and is laid over it member
    by member. A style without that projection ignores the record's: a straight style
    stays straight wherever it is drawn.
    """
    overrides = row.get("projection") or {}
    own = style.get("projection") or {}
    if not overrides or not own:
        return style
    merged = {kind: {**members, **(overrides.get(kind) or {})} for kind, members in own.items()}
    return {**style, "projection": merged}


def spec_of(
    row: dict[str, Any],
    document: dict[str, Any],
    output: Path,
    colormap: str | None = None,
) -> dict[str, Any]:
    """The engine spec drawing one location record in a style.

    The record's place, geometry and cap are kept; its mode, coloring and palette are
    not, because the style is the whole colouring. `colormap` defaults to the style's
    suggested one. **The fold is the style's rule**: a sequential map is mirrored only
    when a palette layer repeats it, since at one traversal the fold would halve the
    ramp and run the near-set end back to the far field's colour.
    """
    from fractal_wallpapers import locations

    spec = locations.spec_of(row, output)
    spec.pop("mode", None)
    name = colormap or document["suggested_colormap"]
    spec["colormap"] = name
    spec["style"] = projected(document["style"], row)
    if repeats(document["style"]) and not is_cyclic(name):
        spec["palette"] = {"mirror": True}
    return spec
