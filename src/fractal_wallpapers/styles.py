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
turning a new reference image into a style; `data/styles/STACK.md` the stack's members.
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


#: The one JSON file under `data/styles/` that is neither a style nor its keeps: the
#: custom-mode catalog (`style_catalog.py`).
CATALOG_FILE = "catalog.json"


def names() -> list[str]:
    """Every style there is, by file name; `<name>.keeps.json` and the catalog are not."""
    return sorted(
        path.stem
        for path in styles_dir().glob("*.json")
        if not path.name.endswith(".keeps.json") and path.name != CATALOG_FILE
    )


def catalog_rows() -> list[dict[str, Any]]:
    """The catalog's rows as written, unchecked: what an alias is looked up in.

    `style_catalog.load` is the checked read; this one serves `load`, which the check
    itself calls.
    """
    path = styles_dir() / CATALOG_FILE
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("modes", [])


def alias_of(name: str) -> tuple[str, str | None] | None:
    """`(mode, colormap)` for a style name merged into a mode, or None.

    A style merged into a mode keeps resolving (`data/styles/README.md`'s *Palette
    sets*): to the palette entry that was it, or to the mode's default when none was
    kept.
    """
    for row in catalog_rows():
        if name in row.get("aliases", []):
            entry = next((e for e in row.get("palettes", []) if e.get("was") == name), None)
            return row["style"], entry["colormap"] if entry else None
    return None


def at_palette(document: dict[str, Any], colormap: str | None) -> dict[str, Any]:
    """The style at one of its mode's palette entries: the entry's values written into the
    stack and its map suggested. A map the set does not hold leaves the stack as it is.
    """
    from fractal_wallpapers import style_palettes

    if not colormap:
        return document
    row = next((r for r in catalog_rows() if r.get("style") == document["name"]), None)
    entry = style_palettes.entry_for(row, colormap) if row else None
    if entry is None:
        return document
    # From the mode's own stack, so an alias already at one entry moves to another whole.
    own = (styles_dir() / f"{document['name']}.json").read_text(encoding="utf-8")
    stack = style_palettes.apply(json.loads(own)["style"], entry.get("values") or {})
    return {**document, "style": stack, "suggested_colormap": colormap}


def load(name: str) -> dict[str, Any]:
    """Read one style file and check its outer shape; the engine checks the stack.

    `name` is a style under `data/styles/`, or the path of a draft `.json` anywhere,
    which is how a style is tuned before it joins the library: a draft is held to the
    same shape except that its file name need not be its name. A style merged into a
    mode (`alias_of`) reads as the mode at the palette that was it.
    """
    draft = name.endswith(".json")
    path = Path(name) if draft else styles_dir() / f"{name}.json"
    if not path.is_file() and not draft:
        alias = alias_of(name)
        if alias is not None:
            mode, colormap = alias
            return at_palette(load(mode), colormap)
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


def luminance_of(rgb):
    """Each pixel's linear (Rec. 709) luminance, from sRGB in [0, 1] (an `(…, 3)` array).

    What `tones` takes lightness from and `style_scout.ink` averages.
    """
    import numpy as np

    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def tones(path: Path, width: int = 640) -> dict[str, float]:
    """A picture's lightness distribution: what the tonal check compares.

    Lightness is CIE L* over 100, from the luminance of the decoded sRGB, read on a
    copy `width` pixels wide (the statistics are of areas, not of hairlines).
    `white` and `black` are the shares of the frame above 0.9 and below 0.1.
    """
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        drawn = image.width
        image = image.convert("RGB")
        image = image.resize((width, max(1, round(image.height * width / image.width))))
        rgb = np.asarray(image, dtype=np.float64) / 255.0
    luminance = luminance_of(rgb)
    knee = 6 / 29
    f = np.where(luminance > knee**3, np.cbrt(luminance), luminance / (3 * knee**2) + 4 / 29)
    lightness = (116 * f - 16) / 100
    return {
        "median": float(np.median(lightness)),
        "p10": float(np.percentile(lightness, 10)),
        "p90": float(np.percentile(lightness, 90)),
        "white": float((lightness > 0.9).mean()),
        "black": float((lightness < 0.1).mean()),
        "width": drawn,
    }


#: How far a render's lightness may sit from its style's reference and still hold
#: the style's balance. Fitted on round one of `floating_on_dreams`, where Matt kept
#: three of ten and found the others far too light: the three kept sit within 0.017
#: of the reference's median and 0.020 of its p10, and every one of the seven dropped
#: is 0.032 to 0.126 above its median. The white share is a ceiling, not a band: a
#: palette that floods the frame with near-white (pink, at 0.21 to 0.26 against the
#: reference's 0.13) was dropped too.
#:
#: `p90` is the one number the tone pass does not pin, so it is the one that tells a
#: stack's highlights from the reference's. Its band was read off `teal_tunnel` and
#: `glow_filaments`: the one `teal_tunnel` variant outside 0.10 (`bare_arches`, +0.108)
#: was dropped, and every `glow_filaments` render sat +0.30 to +0.46 hot except the one
#: variant Matt kept (`no_fog`, +0.093). A miss on every render of a stack is the
#: stack's to fix (narrower glows, less fog), not the locations'.
TONE_BAND = {"median": 0.03, "p10": 0.05, "p90": 0.10}

#: The cheap size a tone check reads. The engine's tone pass meets its targets on the
#: finished picture (each pixel its block of supersamples averaged, since 2026-11-04),
#: so every size's picture holds them at its own resolution. The check reads a copy
#: resized to 640 wide, which averages a thin structure a second time, by more the
#: larger the picture: `teal_tunnel`'s `m_seed0` reads median 0.271 at 640x400 ss1 (the
#: picture the pass measured, so it holds by construction), 0.290 at 1280x800 ss2 and
#: 0.297 at 2560x1600 ss2, against 0.305 at both before the pass read the picture. The
#: draft is the full size's to about 0.01, at a quarter of its samples.
DRAFT_RESOLUTION = (1280, 800)
DRAFT_SUPERSAMPLE = 2

#: Below this width a picture's tones are a guide, never the check (see
#: [`DRAFT_RESOLUTION`]): a 640-wide picture is read exactly as the pass measured it,
#: and any small one says little of how a full-size render reads. `style tones` marks
#: such a row instead of passing it.
CHECKED_WIDTH = DRAFT_RESOLUTION[0]
#: How far above the reference's own share a picture's near-white and near-black may
#: sit (`TONE_BAND` holds the rest of the band).
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


#: The members of one public knob (`data/styles/README.md`'s *Public knobs*).
KNOB_KEYS = ("name", "label", "what", "default", "range", "set")


def targets(stack: Any, pointer: str) -> list[tuple[Any, Any]]:
    """Every `(container, key)` a knob pointer names in a stack.

    A pointer is `/`-separated, list indices as numbers; a `*` step matches every member
    of that list or object under which the rest of the pointer exists, so
    `/layers/*/light/azimuth` is every light's azimuth.
    """
    steps = [step for step in pointer.split("/") if step]
    found: list[tuple[Any, Any]] = []

    def walk(node: Any, rest: list[str]) -> None:
        step, more = rest[0], rest[1:]
        if step == "*":
            keys = range(len(node)) if isinstance(node, list) else list(node or {})
        elif isinstance(node, list):
            keys = [int(step)] if step.isdigit() and int(step) < len(node) else []
        else:
            keys = [step] if isinstance(node, dict) and step in node else []
        for key in keys:
            if not more:
                found.append((node, key))
            elif isinstance(node[key], (dict, list)):
                walk(node[key], more)

    if steps:
        walk(stack, steps)
    return found


def knob_writes(knob: dict[str, Any], value: float) -> list[tuple[str, float]]:
    """What a knob at `value` writes: `(pointer, number)` per target, `scale·value + offset`."""
    writes = []
    for target in knob["set"]:
        target = {"path": target} if isinstance(target, str) else target
        number = float(target.get("scale", 1.0)) * value + float(target.get("offset", 0.0))
        writes.append((target["path"], number))
    return writes


def check_public(document: dict[str, Any]) -> list[str]:
    """Each way a style's `public` block disagrees with its stack; empty when it holds.

    A knob's `default` is the kept version, so every value it writes at its default must
    be the stack's own, and the default must lie in its `range`.
    """
    problems = []
    knobs = (document.get("public") or {}).get("knobs") or []
    seen = set()
    for knob in knobs:
        name = knob.get("name", "?")
        missing = [key for key in KNOB_KEYS if key not in knob]
        if missing:
            problems.append(f"knob '{name}' has no {', '.join(missing)}")
            continue
        if name in seen:
            problems.append(f"knob '{name}' is named twice")
        seen.add(name)
        low, high = knob["range"]
        if not low <= knob["default"] <= high:
            problems.append(f"knob '{name}': default {knob['default']} outside {low}..{high}")
        for pointer, number in knob_writes(knob, float(knob["default"])):
            places = targets(document["style"], pointer)
            if not places:
                problems.append(f"knob '{name}': {pointer} names nothing in the stack")
            for node, key in places:
                if not isinstance(node[key], (int, float)) or abs(node[key] - number) > 1e-9:
                    problems.append(
                        f"knob '{name}': {pointer} is {node[key]} in the stack, {number:g} "
                        "at the knob's default"
                    )
                    break
    return problems


def with_knobs(document: dict[str, Any], settings: dict[str, float]) -> dict[str, Any]:
    """The style file with its stack turned to `settings`, `{knob name: value}`.

    Refuses a knob the style does not expose and a value outside its range: the range
    is the span the look holds over, which is the knob's whole promise.
    """
    import copy

    if not settings:
        return document
    knobs = {knob["name"]: knob for knob in (document.get("public") or {}).get("knobs") or []}
    stack = copy.deepcopy(document["style"])
    for name, value in settings.items():
        knob = knobs.get(name)
        if knob is None:
            offered = ", ".join(knobs) or "none"
            raise StyleError(f"style '{document['name']}' has no knob '{name}'; it has: {offered}")
        low, high = knob["range"]
        if not low <= value <= high:
            raise StyleError(f"knob '{name}' is {low}..{high}; {value:g} is outside it")
        for pointer, number in knob_writes(knob, value):
            for node, key in targets(stack, pointer):
                node[key] = int(round(number)) if isinstance(node[key], int) else number
    return {**document, "style": stack}


def parse_knobs(pairs: list[str] | None) -> dict[str, float]:
    """`--knob NAME=VALUE` arguments as `{name: value}`."""
    settings = {}
    for pair in pairs or []:
        name, sep, value = pair.partition("=")
        try:
            settings[name.strip()] = float(value)
        except ValueError:
            sep = ""
        if not sep or not name.strip():
            raise StyleError(f"--knob takes NAME=VALUE, a number; got '{pair}'")
    return settings


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
