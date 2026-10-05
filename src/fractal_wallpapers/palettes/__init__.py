"""Which colors are available."""

from __future__ import annotations

import json

from fractal_wallpapers.paths import colormap_dir


def drawable() -> dict[str, str]:
    """`{name: kind}` for every colormap the engine can draw, sorted by name.

    A colormap is `data/palettes/<name>.json`, and the name is exactly what
    `--colormap` and a spec's `colormap` take — slugs and display names alike
    (`twilight_shifted`, `Oxblood, Cyan, Cream`). The engine reads `<name>.json`
    and nothing else, so this lists the files rather than any catalog.
    """
    out: dict[str, str] = {}
    for path in sorted(colormap_dir().glob("*.json"), key=lambda held: held.stem.casefold()):
        try:
            kind = str(json.loads(path.read_text(encoding="utf-8")).get("kind") or "")
        except (OSError, ValueError):
            continue
        out[path.stem] = kind
    return out


def refuse_unknown(name: str | None) -> str | None:
    """A one-line refusal for a colormap name the engine has no file for, or `None`."""
    if name is None or (colormap_dir() / f"{name}.json").is_file():
        return None
    return (
        f"no colormap named {name!r}: the engine draws data/palettes/<name>.json and there is "
        f"none by that name. `fractal-wallpapers palettes list` prints every drawable name."
    )
