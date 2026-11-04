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
    """Every style there is, by file name."""
    return sorted(path.stem for path in styles_dir().glob("*.json"))


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
    spec["style"] = document["style"]
    if repeats(document["style"]) and not is_cyclic(name):
        spec["palette"] = {"mirror": True}
    return spec
