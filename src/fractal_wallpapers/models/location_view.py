"""The one picture a location is judged on, and the recipe that makes it.

The location head reads *places*, not wallpapers: one plain smooth render per
location, pre-colour decisions, at a fixed geometry through a fixed map. Two
callers need that picture and they must not be able to disagree about it —
[`fractal_wallpapers.discovery.scoring`], which scores a location the moment a
walk finds it, and [`fractal_wallpapers.curation.intake`], which re-scores the
whole standing supply before a release. A head asked about two different
distributions under one name is a head whose scores cannot be compared, and the
scores from those two sites *are* compared: the ledger's is what the census
reads, and the sidecar's is what the intake ranks on.

So the recipe lives here, once.

**It is the canonical tile's own recipe.** The head is trained on tiles and
reads slot zero of each location at deploy, so anything else would be asking it
about a distribution nobody trained it on. Measured rather than assumed: a plain
render at this geometry differs from the cached canonical tile of the same
location by 0.02–0.77 of a channel level on this repository's own tile cache,
against a JPEG re-compression floor an order of magnitude larger. The tile path
reconstructs from an extended field and this one does not; below that scale the
two are the same picture.

**The map is read off the tile pool, never typed.** The tile build reserves its
low slots for named maps and slot zero carries the canonical view, so the deploy
map is the first of those reservations. A map named in two places is a map that
can be changed in one.
"""

from __future__ import annotations

from pathlib import Path

#: What the picture is rendered at.
RESOLUTION = (640, 360)
SUPERSAMPLE = 2
MODE = "smooth"
CURVE = "linear"


class ViewError(RuntimeError):
    """Nothing says how a location's canonical view is drawn."""


def canonical_map() -> str:
    """The colormap the location view is drawn through, read off the tile pool."""
    from fractal_wallpapers.models import tiles as tile_module

    floor = tile_module.palette_pool().get("floor") or []
    if not floor:
        raise ViewError(
            f"{tile_module.pool_path()} reserves no floor palette, so nothing says which map "
            f"a location's canonical view is drawn through."
        )
    return str(floor[0][0])


def cyclic_maps() -> set[str]:
    """The maps that wrap, so a view knows whether its palette is mirrored."""
    from fractal_wallpapers.models import palette_sets

    return palette_sets.cyclic()


def view_row(row: dict, colormap: str, cyclic: set[str]) -> dict:
    """One location as the render-cache row its picture is made from.

    Through the same shape the finished-render cache uses, so `renders.spec_of`
    is the one place that knows how a row becomes an engine spec — here as
    everywhere else.
    """
    from fractal_wallpapers.labeling import finished

    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": MODE,
        "mode_params": {},
        "curve": CURVE,
        "colormap": colormap,
        "recipe": finished.recipe(mirror=colormap not in cyclic),
        "render": {
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": int(row["maxiter"]),
        },
    }


def view_name(row: dict, colormap: str, cyclic: set[str]) -> str:
    """The file name of one location's view: a digest of the whole recipe."""
    from fractal_wallpapers.models import renders

    return renders.job_name(view_row(row, colormap, cyclic))


def view_path(row: dict, colormap: str, cyclic: set[str], directory: Path) -> Path:
    """Where this location's view lives under `directory`."""
    return Path(directory) / f"{view_name(row, colormap, cyclic)}.jpg"


def render_view(row: dict, colormap: str, cyclic: set[str], directory: Path) -> tuple[Path, bool]:
    """`(picture, made)` — the location's view, rendered if it is not already there.

    Addressed by the digest of its own recipe, so two callers asking for the same
    location's view get one file and the second one pays nothing.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import renders

    output = view_path(row, colormap, cyclic, directory)
    if output.is_file():
        return output, False
    output.parent.mkdir(parents=True, exist_ok=True)
    engine.run("render", renders.spec_of(view_row(row, colormap, cyclic), output))
    return output, True


def summary(colormap: str) -> dict:
    """The recipe as a record carries it."""
    return {
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "mode": MODE,
        "curve": CURVE,
        "colormap": colormap,
    }


__all__ = [
    "CURVE",
    "MODE",
    "RESOLUTION",
    "SUPERSAMPLE",
    "ViewError",
    "canonical_map",
    "cyclic_maps",
    "render_view",
    "summary",
    "view_name",
    "view_path",
    "view_row",
]
