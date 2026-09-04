"""What the engine is told, derived from a row. One derivation, and it is here.

Every picture in this project is described by a **row** — family, viewport, mode,
curve, colormap, recipe, render settings — and every picture is drawn by handing
[`fractal_wallpapers.engine`] a JSON spec built from one. [`spec_of`] is that
build, [`coloring_of`] is the half of it that resolves a mode name against the
engine's own catalog, and [`recipe`] is the palette pass in the shape a row
records and the engine reads.

## Why they are at the floor rather than in `models.renders`

They were in [`models.renders`] and `recipe` in [`labeling.finished`], which is
where they are *used* most — but not where they are used *first*.
[`engine_fingerprint`] draws six probes through this exact derivation, on purpose:
the number that names an engine build has to be a fingerprint of the production
path, not of a second way to ask for pixels. So the fingerprint reached up into
the render cache and the label store, from a module both of them import, through
imports written inside function bodies — and that arrow held `engine_fingerprint`
inside the tree's largest import cycle.

The arrow is turned around the way [`models.roster`] turned it around for `ship`:
this module imports `engine` and `paths` and nothing else, and the heavier modules
import *it*. `renders.spec_of`, `renders.coloring_of`, `renders.catalog`,
`renders.RenderCacheError` and `finished.recipe` all still resolve — they are
imported there rather than re-exported through a wrapper, so there is one function
object per name, which is the property [`curation.candidate_ledger`]'s `__init__`
had to be rewritten to keep. The five themselves are derivations over a dict with
no store behind them, and nothing redirects one.

**What a test does redirect is [`colormap_dir`], and it has to be redirected
here.** `spec_of` writes that one absolute path into the spec, so the field-name
digests in `tests/test_curation_colorize.py` pin it — and a fixture that pinned
`renders.colormap_dir` after this move would be holding a name `spec_of` no
longer reads, silently digesting the checkout instead of the field. That fixture
names this module.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.paths import colormap_dir


def recipe(
    gamma: float = 1.0,
    cycles: float = 1.0,
    phase: float = 0.0,
    reverse: bool = False,
    mirror: bool = False,
    transfer: dict | None = None,
    rolloff: dict | None = None,
) -> dict:
    """The palette pass, in the shape the engine reads and a row records.

    One object, spelled once: the render cache hands it to the engine verbatim,
    so a row and the picture made from it cannot describe different recipes.
    """
    return {
        "gamma": float(gamma),
        "cycles": float(cycles),
        "phase": float(phase),
        "reverse": bool(reverse),
        "mirror": bool(mirror),
        "transfer": transfer or {"kind": "value"},
        "rolloff": rolloff or {"kind": "none"},
    }


_CATALOG: dict[str, dict] | None = None


def catalog() -> dict[str, dict]:
    """`{mode: its coloring}` from the engine's own list, read once."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = {mode["name"]: mode["coloring"] for mode in engine.modes()}
    return _CATALOG


#: The field kind an address is written under, and where a *head* address opens
#: when the pixel is `z₀`.
#:
#: Matt's verdict of 2026-08-17: on a dynamical plane the `z₀` address spells its
#: leading symbol from the pixel's own angular sector, which draws a hard wedge
#: seam along the axes; `z₁` opens the address one step in, so every symbol is one
#: the recurrence produced. On a parameter plane `z₀ = 0` for every pixel, there is
#: no wedge to remove, and the engine refuses `z1` there.
#:
#: `ITINERARY` is the **field**'s name and not the mode's: `tail_itinerary` reads
#: the same field under a different window, so a join on the mode name would miss
#: it and a join on the field name catches both. That is the whole reason the
#: split below is written against `start` rather than against the mode.
ITINERARY = "itinerary"
Z1 = "z1"

#: The windows a caller asked for by name, which the plane does not get to move.
#:
#: A `start` the catalog wrote out is a decision already taken — `tail` is the
#: only one today — and the plane rule below applies to the one window that has a
#: leading digit to argue about. Absent means the field's own default, `z0`, which
#: is exactly the case the rule is for.
NAMED_STARTS = frozenset({"tail"})


def open_the_address(coloring: dict, family: dict) -> dict:
    """Put the plane's answer for where a **head** address opens into `coloring`.

    The **catalog listing has no family**, so the coloring `catalog()` holds is the
    parameter-plane form and this is what makes it the row's. Written explicitly
    rather than left to the engine's default: the job name is a digest of the spec
    that goes over the wire, so a choice the engine made after the digest would let
    two different pictures share one file.

    Every field of the coloring is walked, not just the modulate's texture, because
    the second way an address could arrive is the one nobody would look for. The
    plane is asked about only when there is an address to open, so the modes that
    read no address are untouched by a family the split has no answer for.

    **A window the catalog named is left exactly as it arrived.** `tail_itinerary`
    carries `"start": "tail"`, which is not a start the plane decides — a tail
    address never reads `z₀`, so there is no wedge for `z₁` to remove and the mode
    is one coloring on both planes. Overwriting it here would render the head mode
    under the tail mode's name, and the engine would not refuse it: `z1` is legal
    on the plane this branch is about. See [`NAMED_STARTS`].
    """
    addresses = [
        field
        for field in _fields_of(coloring)
        if field.get("kind") == ITINERARY and field.get("start") not in NAMED_STARTS
    ]
    if addresses and engine.pixel_is_z0(family):
        for field in addresses:
            field["start"] = Z1
    return coloring


def _fields_of(coloring: dict) -> list[dict]:
    """Every field this coloring reads. A direct trap makes none."""
    if coloring["kind"] == "field":
        return [coloring["field"]]
    if coloring["kind"] in ("composite", "modulate"):
        return [coloring["base"]["field"], coloring["texture"]["field"]]
    return []


def coloring_of(row: dict) -> dict:
    """The mode's coloring, with this row's curve, trap settings and plane in it.

    The curve lands on the **base** of a composite or a modulate and nowhere else:
    the texture lies over the base and the corpora set one curve per render, which
    is the one the base is read through.
    """
    mode = row["mode"]
    known = catalog()
    if mode not in known:
        raise RenderCacheError(f"the engine has no mode named {mode!r}")
    coloring = json.loads(json.dumps(known[mode]))
    curve = row["curve"]
    settings = row.get("mode_params") or {}
    open_the_address(coloring, row["family"])

    if coloring["kind"] == "field":
        coloring["transform"] = curve
    elif coloring["kind"] in ("composite", "modulate"):
        coloring["base"]["transform"] = curve
    elif coloring["kind"] == "direct":
        # The curve is NOT set here, and that is what the corpora did. A direct
        # trap has no field: its colour key is how near the orbit came, as a
        # fraction of the threshold, and the source's own path samples the
        # gradient at that key untouched — no stretch, no curve, no gamma. Two
        # rows that differ only in a curve are therefore the same picture here,
        # which is why they share one file.
        for name, value in settings.items():
            if name not in ("opacity", "threshold"):
                raise RenderCacheError(f"{mode}: no setting named {name!r}")
            coloring[name] = value
        settings = {}
    if settings:
        raise RenderCacheError(f"{mode} takes no settings, and this row carries {settings}")
    return coloring


def spec_of(row: dict, output: Path) -> dict:
    """The JSON object the engine reads, for one row."""
    render = row["render"]
    recipe = row["recipe"]
    return {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(render["resolution"]),
        "supersample": int(render["supersample"]),
        "maxiter": int(render["maxiter"]),
        "coloring": coloring_of(row),
        "palette": {
            "gamma": recipe["gamma"],
            "cycles": recipe["cycles"],
            "phase": recipe["phase"],
            "reverse": recipe["reverse"],
            "mirror": recipe["mirror"],
            "transfer": recipe["transfer"],
            "rolloff": recipe["rolloff"],
        },
        "colormap": row["colormap"],
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }


class RenderCacheError(RuntimeError):
    """A row that cannot become a picture."""
