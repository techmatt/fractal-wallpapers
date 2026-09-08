"""What decides a candidate's pixels, as one value with one name.

Until now there was no such value. A candidate travelled as five different
shapes — the flat row [`curation.colorize`] makes, the nested decision
[`curation.records`] writes, the flat row a reader takes a decision back as, the
render-cache row [`models.renders`] takes, and the engine spec that row becomes —
and the join between them lived in three adapters plus [`renders.SPEC_MEMBERS`],
an untyped tuple of member names. Nothing could be asked *have we already made
this picture*, because there was nothing to ask it of.

This is that value. A [`Recipe`] carries everything the picture is a function of
and nothing else, and [`key_of`] is its stable name.

## The frame is the one that was rendered

`framing.used`, never `framing.adopted`. A scan over a location's framings
adopts the best; a **fallback leg** then re-renders some of those locations at
the framing on record, and the row says which of the two it was
drawn at. 305 of the pool's 3,208 adopted pictures are fallback renders at the
original frame. A cache keyed on what was adopted misfiles every one of them —
it would hand a solver the refined frame's name for the original frame's pixels.
[`of_decision`] reads `framing.used` and takes the viewport that goes with it.

## What is in the key, and what is only carried

The key is a digest of **what the engine is told, plus what happens after the
engine is told it**.

The first half comes through [`renders.spec_of`], so there is one derivation in
this project of what a picture's engine input is rather than two that can drift.
Two members of that spec are dropped ([`PINNED`]) and both are paths: `output`
names where this render went, and `colormap_dir` is an absolute path into the
checkout. Leaving `colormap_dir` in would make the key different on every
machine and different again after the repository moved — which is why this is
its own digest and not [`renders.job_name`], whose digest carries it. That is
harmless where it lives: a render-cache file name is meaningless off the machine
that wrote it. It is not harmless here.

The second half is the **autolevel stamp**, and it is the reason the engine spec
alone is not enough. `band_autolevel/v1` re-renders through a colormap built
from `data/coloring/levels_band.json`, so the picture is a function of that
file's sha256 — and no digest in this project carries it. Two candidates with
one engine spec and two bands are two pictures.

`palette_group` is carried and **not** keyed. It decides no pixels: it is a fact
about the map, read from a tracked table that a re-clustering can move, and a
key that moved with it would re-key rows whose pixels never changed.

[`Recipe.pixels`] refuses when a member of the dataclass is in neither
[`KEYED`] nor [`CARRIED`], and again when the engine spec grows a member that is
in neither the keyed set nor [`PINNED`]. That is [`renders.field_job_name`]'s
discipline, for the same reason: a new axis has to be *classified*, and cannot
be left out of a key by being forgotten at a call site.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from pathlib import Path

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.curation import release
from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import renders
from fractal_wallpapers.palettes import groups as groups_module

#: The schema a recipe record carries.
SCHEMA = 1

#: How much of the sha256 names a recipe. Sixteen hex characters is 64 bits, the
#: same length and the same arithmetic as [`renders.NAME_LENGTH`]: at a million
#: recipes the chance of any two colliding is about 3e-8.
KEY_LENGTH = 16

#: The one regime every candidate in this project has been rendered at. Not a
#: default anything new relies on — [`of_decision`] reads the row's own geometry
#: and [`is_candidate_regime`] is how a reader asks whether it is this one.
CANDIDATE_REGIME = release.Regime((640, 360), 2)

#: What a picture with no autolevel stamp is: a mode the operator does not act on
#: ([`autolevel.applies_to`]), where there is no band in the picture's identity.
NO_AUTOLEVEL = None

#: What [`Recipe.pixels`] passes where an engine spec wants an output path. The
#: member is dropped from the digest, so the value is never read — it is spelled
#: once here rather than as a bare string at the one call site.
NO_OUTPUT = Path("_unwritten")

#: Members of [`renders.spec_of`]'s output that are **not** part of the picture.
#: Both are paths — where this render went, and where the colormaps were read
#: from on the machine that drew it. See the module docstring.
PINNED: tuple[str, ...] = ("output", "colormap_dir")

#: Members of [`Recipe`] the key is a digest of. **Being in this tuple does not
#: put a member in the digest** — [`_KEYED_THROUGH`] is what says how each one
#: gets there, and [`Recipe.pixels`] refuses a member listed here that has no
#: route. See that table for what the gap was.
KEYED: tuple[str, ...] = (
    "family",
    "viewport",
    "maxiter",
    "regime",
    "mode",
    "mode_params",
    "curve",
    "colormap",
    "palette",
    "autolevel",
)

#: Members of [`Recipe`] that are carried on the record and decide no pixels.
CARRIED: tuple[str, ...] = ("palette_group",)

#: **Where each keyed member lands in the digest**, as paths into [`Recipe.pixels`]'s
#: own output.
#:
#: This exists because [`KEYED`] did not key. The digest is built from two
#: derived blocks — the engine spec and the reduced stamp — and never from the
#: member list, so a member added to the dataclass and appended to `KEYED` was
#: *classified as part of the picture and left out of its name*, with nothing in
#: the tree noticing. Verified before it was closed: a member added to `Recipe`
#: and to `KEYED` left `key_of` byte-identical.
#:
#: A route is checked for **presence** on every call, which is what catches the
#: member nobody wired up and the route that names a spec key the engine stopped
#: emitting. It cannot catch a route that is present and ignored — that a member
#: actually *moves* the key is
#: `tests/test_candidate_ledger.py`'s perturbation guard, one case per member.
#:
#: **Two members reach the digest only on some modes, and that is the engine's
#: rule rather than a gap here.** `curve` is written onto the coloring's
#: transform for a field, a composite and a modulate and *not* for a direct trap,
#: which has no field to read through a curve; `mode_params` is only ever
#: non-empty on a direct trap, and [`engine_spec.coloring_of`] refuses settings
#: on anything else. Both route through `engine.coloring`, which is always
#: present, so the presence check holds on every mode and the perturbation guard
#: names the mode each one is provable on.
_KEYED_THROUGH: dict[str, tuple[str, ...]] = {
    "family": ("engine.family",),
    "viewport": ("engine.viewport",),
    "maxiter": ("engine.maxiter",),
    "regime": ("engine.resolution", "engine.supersample"),
    "mode": ("engine.coloring",),
    "mode_params": ("engine.coloring",),
    "curve": ("engine.coloring",),
    "colormap": ("engine.colormap",),
    "palette": ("engine.palette",),
    "autolevel": ("autolevel",),
}


def _reaches(material: dict, path: str) -> bool:
    """Whether `path` — dotted, into [`Recipe.pixels`]'s output — is there at all.

    Presence and not truthiness: `autolevel` is [`NO_AUTOLEVEL`] on every mode the
    operator does not act on, and a member whose value is legitimately null is
    still a member the digest carries.
    """
    here = material
    for step in path.split("."):
        if not isinstance(here, dict) or step not in here:
            return False
        here = here[step]
    return True


class RecipeError(RuntimeError):
    """A row that cannot become a recipe, or a recipe that cannot be named."""


@dataclass(frozen=True)
class Recipe:
    """Everything one candidate picture is a function of, and what it was made of.

    `viewport` is the frame the render was actually drawn at — `framing.used` —
    and `family`, `maxiter` and `regime` complete the geometry. `palette` is the
    seven-knob object the engine reads, spelled by [`finished.recipe`] so a
    recipe and the picture made from it cannot describe different passes.
    `autolevel` is the operator's stamp reduced to its identity, or [`NO_AUTOLEVEL`]
    where the mode takes no operator.
    """

    family: dict
    viewport: dict
    maxiter: int
    regime: release.Regime
    mode: str
    mode_params: dict
    curve: str
    colormap: str
    palette: dict
    autolevel: dict | None
    #: Which palette group the map belongs to. Carried, never keyed — see the
    #: module docstring.
    palette_group: str

    def render(self) -> dict:
        """The geometry block a render-cache row carries: the regime and this cap."""
        return {**self.regime.geometry(), "maxiter": int(self.maxiter)}

    def row(self) -> dict:
        """This recipe as the render-cache row [`renders.spec_of`] reads.

        The bridge, and the only one: everything that wants an engine spec out of
        a recipe goes through here, so a recipe and a render-cache row cannot
        describe two different pictures.
        """
        return {
            "family": self.family,
            "viewport": self.viewport,
            "mode": self.mode,
            "mode_params": dict(self.mode_params or {}),
            "curve": self.curve,
            "colormap": self.colormap,
            "recipe": self.palette,
            "render": self.render(),
        }

    def pixels(self) -> dict:
        """The material [`key_of`] digests: the engine's input, and the operator's.

        Refuses rather than proceeds on an unclassified member, at three levels.
        A field added to this dataclass and left out of [`KEYED`] and [`CARRIED`]
        would silently not be part of the picture's name; a member the engine
        spec grows that lands in neither [`_KEYED_SPEC`] nor [`PINNED`] would
        silently join it; and a member declared **keyed** that reaches none of
        the digest would be classified as deciding the pixels and left out of
        their name anyway, which is the one this returns through
        [`_KEYED_THROUGH`]. All three are decisions, and none of them is a
        decision a call site can make by forgetting.
        """
        unclassified = {field.name for field in fields(self)} - set(KEYED) - set(CARRIED)
        if unclassified:
            raise RecipeError(
                f"{sorted(unclassified)} is a member of Recipe and is in neither KEYED nor "
                f"CARRIED, so a recipe key does not say whether the picture depends on it. "
                f"Classify it: a member that decides pixels is keyed, a member that describes "
                f"them is carried."
            )
        spec = renders.spec_of(self.row(), NO_OUTPUT)
        loose = set(spec) - set(_KEYED_SPEC) - set(PINNED)
        if loose:
            raise RecipeError(
                f"{sorted(loose)} is in the engine spec and is in neither the keyed set nor "
                f"PINNED, so a recipe key does not say whether the picture depends on it. "
                f"Classify it: PINNED is for members that name a place rather than a picture."
            )
        material = {
            "schema": SCHEMA,
            "engine": {name: spec[name] for name in sorted(spec) if name not in PINNED},
            "autolevel": self.autolevel,
        }
        unrouted = [name for name in KEYED if name not in _KEYED_THROUGH]
        if unrouted:
            raise RecipeError(
                f"{unrouted} is in KEYED and _KEYED_THROUGH does not say where it lands in "
                f"the digest, so nothing here can tell whether the key carries it. Being "
                f"listed as keyed does not put a member in the key: say which path of "
                f"`pixels()` carries it, and prove it moves the key with a case in "
                f"tests/test_candidate_ledger.py."
            )
        absent = [
            f"{name} -> {path}"
            for name in KEYED
            for path in _KEYED_THROUGH[name]
            if not _reaches(material, path)
        ]
        if absent:
            raise RecipeError(
                f"{absent} names a keyed member whose route into the digest is not there. "
                f"Either the member never reached `pixels()` or the engine spec stopped "
                f"emitting what it rides in, and a key that silently stopped carrying a "
                f"member names a different picture under the same name."
            )
        return material

    def record(self) -> dict:
        """This recipe as a stored row carries it. Every member, keyed and carried."""
        return {
            "schema": SCHEMA,
            "family": self.family,
            "viewport": self.viewport,
            "maxiter": int(self.maxiter),
            "regime": self.regime.spelled,
            "mode": self.mode,
            "mode_params": dict(self.mode_params or {}),
            "curve": self.curve,
            "colormap": self.colormap,
            "palette_group": self.palette_group,
            "palette": self.palette,
            "autolevel": self.autolevel,
        }


#: What [`renders.spec_of`] emits that IS part of the picture. A declaration in
#: the sense [`renders.SPEC_MEMBERS`] is one — it is not derived, and it is not
#: meant to be: [`Recipe.pixels`] holds the live spec to it and refuses when the
#: two stop agreeing, so a member the engine grows is a decision taken here
#: rather than a member that quietly joined a key or quietly did not.
_KEYED_SPEC: tuple[str, ...] = (
    "schema",
    "family",
    "viewport",
    "resolution",
    "supersample",
    "maxiter",
    "coloring",
    "palette",
    "colormap",
)


def key_of(recipe: Recipe) -> str:
    """The stable name of one recipe: a digest of [`Recipe.pixels`].

    Machine-independent and checkout-independent, which is the whole reason it is
    not [`renders.job_name`]. Stable across a re-clustering of the palette groups,
    because the group is carried rather than keyed. It moves — correctly — when
    the engine's mode catalog moves, because the coloring the catalog holds is in
    the spec this digests.
    """
    material = json.dumps(recipe.pixels(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def stamp_of(autolevel_block: dict | None) -> dict | None:
    """One autolevel stamp reduced to what decides pixels.

    The stamp a row carries is a page of measurements — the curve it derived, the
    tone it read, what it clamped — and every one of those is *derived* from the
    render and the band. What the picture depends on is the operator, whether it
    was switched on, and which band it projected onto.

    `acted` is deliberately not in it. A row where the operator measured the
    render as already in band renders the engine's own bytes, and a row where it
    acted renders through a rebuilt colormap; but which of the two happens is a
    function of the picture, not an input to it, so keying on it would put a
    derived fact in an identity.
    """
    if not autolevel_block:
        return NO_AUTOLEVEL
    band = autolevel_block.get("band") or {}
    return {
        "operator": str(autolevel_block.get("operator") or ""),
        "switch": str(autolevel_block.get("switch") or ""),
        "band_sha256": str(band.get("sha256") or ""),
    }


def frame_used(row: dict) -> tuple[dict, int]:
    """`(viewport, maxiter)` of the frame this row was **rendered** at.

    The row's own `location.viewport` — which is already the used frame, because
    a leg that adopts a refinement re-frames the row before it hands it to the
    colorizer. This exists so that fact is asserted rather than assumed: where the
    row carries a framing block, the viewport must be the side the block's `used`
    names, and a row that disagrees is a row whose picture nothing can identify.
    """
    location = row.get("location") or {}
    viewport = location.get("viewport")
    maxiter = location.get("maxiter")
    if not isinstance(viewport, dict) or maxiter is None:
        raise RecipeError(f"{row.get('key')!r} carries no frame, so it names no picture")
    from fractal_wallpapers.curation import framing

    block = row.get("framing") or {}
    if block.get("used") == framing.ORIGINAL and block.get("adopted"):
        original = (block.get("original") or {}).get("viewport")
        if original and original != viewport:
            raise RecipeError(
                f"{row.get('key')!r} says it was rendered at the ORIGINAL framing, and its "
                f"viewport is neither that one nor readable as it. The picture on disk "
                f"cannot be identified from this row."
            )
    return viewport, int(maxiter)


def of_decision(row: dict, group_table: dict | None = None) -> Recipe:
    """The recipe behind one decision row — a run's release row or a pass's gate row.

    **The one adapter**, and it reads rather than assumes. `mirror` is set per
    site — [`colorize.render_row`] sets it from the map's own `kind` — and the
    curve is stated per recolour path, so both come off the row. The other six
    palette knobs are not on the row at all: the candidate path spends
    [`finished.recipe`]'s defaults, which is where they are read from, once.

    `mode_params` is `{}` for the same reason and with the same evidence: the
    candidate path is [`colorize.render_row`], which sets it empty, and no
    decision row in either store carries the member.
    """
    recipe = row.get("recipe") or {}
    viewport, maxiter = frame_used(row)
    regime = release.regime_from_geometry(recipe.get("render"))
    if regime is None:
        raise RecipeError(f"{row.get('key')!r} does not say what geometry it was rendered at")
    colormap = str(recipe.get("colormap") or "")
    if not colormap:
        raise RecipeError(f"{row.get('key')!r} names no colormap, so it names no picture")
    return Recipe(
        family=(row.get("location") or {}).get("family"),
        viewport=viewport,
        maxiter=maxiter,
        regime=regime,
        mode=str(recipe.get("mode") or ""),
        mode_params={},
        curve=str(recipe.get("curve") or ""),
        colormap=colormap,
        palette=finished.recipe(mirror=bool(recipe.get("mirror"))),
        autolevel=stamp_of(row.get("autolevel")),
        palette_group=groups_module.group_of(colormap, group_table),
    )


def of_record(block: dict) -> Recipe:
    """The recipe behind one **stored** row: [`Recipe.record`] read back.

    The inverse of `record`, and the reason the ledger row can drop everything
    else it used to carry. Two things a row must always be able to do rest on
    this one function:

    * **The recipe key stays recomputable.** `key_of(of_record(row["recipe"]))`
      is the row's own `key`, so the store's name for a picture is derived from
      the row rather than trusted off it.
    * **The picture stays re-renderable from the row alone.** `Recipe.row` on the
      value this returns is the engine spec, which is the whole of what a render
      needs.

    Refuses on a missing member rather than defaulting one. A recipe with a
    guessed `curve` digests to a key that names a different picture, and a
    silently wrong identity is worse than no identity at all.
    """
    wanted = ("family", "viewport", "maxiter", "regime", "mode", "curve", "colormap", "palette")
    missing = [name for name in wanted if block.get(name) is None]
    if missing:
        raise RecipeError(
            f"{missing} is missing from the stored recipe, so it names no picture. A recipe "
            f"read back with a member defaulted digests to a key for a different picture."
        )
    return Recipe(
        family=block["family"],
        viewport=block["viewport"],
        maxiter=int(block["maxiter"]),
        regime=release.regime_of(str(block["regime"])),
        mode=str(block["mode"]),
        mode_params=dict(block.get("mode_params") or {}),
        curve=str(block["curve"]),
        colormap=str(block["colormap"]),
        palette=block["palette"],
        autolevel=block.get("autolevel"),
        palette_group=str(block.get("palette_group")),
    )


def is_candidate_regime(recipe: Recipe) -> bool:
    """Whether this recipe stands at the one regime the candidate pool was made at."""
    return recipe.regime == CANDIDATE_REGIME


def autolevel_applies(mode_kind: str | None) -> bool:
    """Whether the operator acts on this mode's kind, through its own owner."""
    return bool(mode_kind) and autolevel.applies_to(str(mode_kind))


def live_stamp(mode: str, band: dict | None = None):
    """The autolevel identity a render in this mode will carry **right now**.

    [`hunt.Maker.stamp_for`]'s body, hoisted to the module that owns the key it
    is a member of. Two re-render legs ask it — the ledger's and the pool's — and
    a third spelling of it is a third answer to what picture a row names, which
    is the failure [`stamp_of`] exists to prevent.

    Derivable rather than observed: the operator, the switch and the band's
    sha256 are all known before the engine runs, and `acted` is deliberately not
    among them.
    """
    from fractal_wallpapers.curation import colorize

    if not autolevel.enabled() or not autolevel_applies(colorize.kind_of(mode)):
        return NO_AUTOLEVEL
    return stamp_of(autolevel.make_stamp(band or colorize.band() or {}, {}, {}, 0, 0, acted=False))


__all__ = [
    "CANDIDATE_REGIME",
    "CARRIED",
    "KEYED",
    "KEY_LENGTH",
    "NO_AUTOLEVEL",
    "NO_OUTPUT",
    "PINNED",
    "SCHEMA",
    "Recipe",
    "RecipeError",
    "autolevel_applies",
    "frame_used",
    "is_candidate_regime",
    "key_of",
    "live_stamp",
    "of_decision",
    "of_record",
    "stamp_of",
]
