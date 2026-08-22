"""The one picture a location is EMBEDDED from, and the recipe that makes it.

The gallery pass selects locations, not candidates. Diversity is a question
about geometry — *have I already shipped a picture of somewhere that looks like
this* — and a location's coloring is chosen after it is picked, so the picture a
similarity is measured on has to be one that says nothing about the coloring.
That picture is the **neutral render**: the location's `smooth` field, through
one cyclic map, at one small geometry, with every palette knob at its default.

It is not the location head's view. [`fractal_wallpapers.models.location_view`]
owns *that* picture, at 640x360ss2 through whatever map the tile pool reserves
in its floor slot, and the two must not be the same function: the judged view
follows the pool, and this one may not move at all. Both draw `smooth` and both
draw one location, and that is where the resemblance ends.

## Every choice here is frozen, and the manifest is what makes a thaw visible

A vector is only comparable to a vector made the same way. Change the map, the
size, the supersample or the mode, and every stored vector becomes a reading of
a picture that no longer exists — silently, because a cosine between two vectors
of different provenance is still a number between -1 and 1. So the choices are
constants in one place, they go into [`CHOICES`], and [`stamp`] digests them.
The embedding store writes that digest into its manifest and onto every row it
appends, and refuses a row whose stamp is not today's.

**The map is `twilight_shifted`** — cyclic, so nothing is mirrored; wide enough
in lightness that the escape bands read as structure rather than as a pastel
wash, which the mid-chroma CET cyclic maps did not at this size. It is today's
canonical location-view map as well, and that is a coincidence worth stating
rather than relying on: this module spells the name, so the pool can reserve a
different floor palette tomorrow without invalidating twenty-five thousand
vectors.

**448x252 at one sample per pixel.** 16:9, which is what a wallpaper is; a
multiple of 14 on both axes, which is DINOv2's patch size, so the transformer
tiles the frame exactly and nothing is resized on the way in. One sample per
pixel because supersampling buys smoother edges for a human eye and the
embedding is not one — and it is the difference between a leg of hours and a leg
of half an hour.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fractal_wallpapers.paths import under

#: The cyclic map every neutral render is drawn through. Spelled here, never read
#: off the tile pool: see the module docstring on why the two must be able to
#: disagree.
COLORMAP = "twilight_shifted"

#: The frame, in pixels, and how many field samples each of them gets.
RESOLUTION = (448, 252)
SUPERSAMPLE = 1

#: The field and the curve. `smooth` because it is the one coloring every family
#: draws and the one the location judge already reads a place through.
MODE = "smooth"
CURVE = "linear"

#: The palette pass, all of it. A cyclic map wraps, so there is nothing to mirror,
#: and every other knob is at the value that does nothing.
MIRROR = False


class NeutralError(RuntimeError):
    """The neutral render cannot be described, or cannot be believed."""


def choices() -> dict:
    """Every frozen decision, as the manifest records it and a row is stamped with.

    The DINOv2 half is not in here: this module owns the picture and
    [`fractal_wallpapers.models.embedding`] owns the reading of it. The store
    joins the two, because a vector's provenance is both.
    """
    return {
        "colormap": COLORMAP,
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "mode": MODE,
        "curve": CURVE,
        "mirror": MIRROR,
    }


def stamp(extra: dict | None = None) -> str:
    """A short digest of the frozen choices, plus whatever the caller freezes too.

    Twelve hex characters, which is the same length the render cache names a job
    with. Long enough that two sets of choices will not collide, short enough to
    sit on every row of a twenty-five-thousand-row store.
    """
    material = json.dumps({**choices(), **(extra or {})}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def check_map() -> None:
    """Refuse if [`COLORMAP`] has stopped being cyclic, or has left the library.

    [`MIRROR`] is `False` because the map wraps. A map that stopped wrapping would
    make every neutral render a picture with a seam down the middle of its ramp,
    and nothing else here would notice. Called once at the top of a leg rather
    than per render: it reads the whole palette library.
    """
    from fractal_wallpapers.models import palette_sets

    cyclic = palette_sets.cyclic()
    if COLORMAP not in cyclic:
        raise NeutralError(
            f"the neutral render is drawn through {COLORMAP!r} with mirror={MIRROR}, and that "
            f"map is not in the cyclic set any more. Either the library changed or the name "
            f"is wrong; both invalidate every vector in the store."
        )


def neutral_row(row: dict) -> dict:
    """One location as the render-cache row its neutral picture is made from.

    Through the same shape everything else here renders from, so
    `renders.spec_of` stays the one place that knows how a row becomes an engine
    spec. `row` is anything carrying a family, a viewport and a maxiter: a walk
    ledger row, a supply sidecar row, a release record's `location` block.
    """
    from fractal_wallpapers.labeling import finished

    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": MODE,
        "mode_params": {},
        "curve": CURVE,
        "colormap": COLORMAP,
        "recipe": finished.recipe(mirror=MIRROR),
        "render": {
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": int(row["maxiter"]),
        },
    }


def neutral_name(row: dict) -> str:
    """The file name of one location's neutral render: a digest of the whole recipe.

    The geometry and the map are inside the digest, so a store whose fixed
    choices moved does not overwrite the pictures taken under the old ones — it
    simply stops finding them, which is the failure being visible rather than
    silent.
    """
    from fractal_wallpapers.models import renders

    return renders.job_name(neutral_row(row))


def neutral_dir() -> Path:
    """Where the neutral renders live. Under curation's own store, hot, ignored."""
    return under("curation") / "neutral"


def neutral_path(row: dict, directory: Path | None = None) -> Path:
    """Where this location's neutral render lives."""
    where = neutral_dir() if directory is None else Path(directory)
    return where / f"{neutral_name(row)}.jpg"


def render_neutral(row: dict, directory: Path | None = None) -> tuple[Path, bool]:
    """`(picture, made)` — the neutral render, drawn if it is not already there.

    Addressed by the digest of its own recipe, so a second pass over a location
    already in the store pays nothing, and a leg killed halfway resumes on the
    files it left behind.
    """
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import renders

    output = neutral_path(row, directory)
    if output.is_file():
        return output, False
    output.parent.mkdir(parents=True, exist_ok=True)
    engine.run("render", renders.spec_of(neutral_row(row), output))
    return output, True


__all__ = [
    "COLORMAP",
    "CURVE",
    "MIRROR",
    "MODE",
    "RESOLUTION",
    "SUPERSAMPLE",
    "NeutralError",
    "check_map",
    "choices",
    "neutral_dir",
    "neutral_name",
    "neutral_path",
    "neutral_row",
    "render_neutral",
    "stamp",
]
