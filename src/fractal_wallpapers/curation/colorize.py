"""One colorize attempt: a location becomes a candidate wallpaper with a verdict.

An attempt is four steps and each one is a decision this project already made
somewhere else, wired together here:

1. **A candidate set of maps** is built around a seeded anchor, out of the shipped
   palette pool ([`candidate_set`]).
2. **The palette head picks one**, on recolors of a single dumped field.
3. **The picture is rendered** in a mode the paying head owns, through the picked
   map, and the autolevel operator either moves its tone onto the band or hands
   back the render's own bytes.
4. **The finished-render judge for that mode scores it**, and the whole row —
   verdict, recipe, provenance — is one record.

## The candidate set: a neighbourhood, not a flavour

The source project drew its candidates from a *flavour* — a cluster of maps that
already resemble each other, computed over a palette library this repository holds
a subset of. That taxonomy does not transfer, and rebuilding it would be
rebuilding an artifact rather than a rule. What transfers is the *property* that
made those sets the right question: **the candidates look alike**, so the head is
asked to make a fine distinction rather than an obvious one, which is exactly
what it was distilled to do.

So a set here is [`palettes.space.neighbourhood`] — the thirty-two maps nearest a
drawn anchor in a fixed Oklab metric over the gradient *as the renderer spends
it*. Same width as the real sets the head was distilled and accepted on, same
tightness by construction, and it is a pure function of the tracked library and
the anchor. Anchors are drawn **without replacement across a run**, which is the
cheap spread rule: two locations in one release get their candidates from
different regions of palette space, so the release does not come out in one
colour by coincidence.

## The pick is made on one field, and the field is smooth

Every candidate is a *recolor* of one dumped smooth field: one iteration pass per
location instead of thirty-two, and the pictures the head reads are the smooth
640×360 renders it was distilled on. The chosen map then colours whatever mode
the attempt draws. That is the source's own arrangement and it is the right one
twice over — it is thirty times cheaper, and asking a head distilled on smooth
renders to rank a direct-trap picture would be asking it about a distribution
nobody trained it on.

## The mode is drawn inside the paying head's roster

The smooth judge owns the one smooth coloring; the strange judge owns every other
**production** mode the engine knows. The roster is read out of the engine's own
catalog at call time, so a mode cannot exist on one side of the boundary and not
the other, and the draw is seeded per attempt and recorded.

A mode the catalog tiers as *niche*, or that [`curation.mode_policy`] weights 0,
is renderable by name and can never be drawn here. Both exclusions live in
[`modes_for`] — the one place a mode is drawn — rather than at each of its
callers.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import engine, paths
from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.curation import budget as budget_module
from fractal_wallpapers.curation import floors, intake
from fractal_wallpapers.palettes import space

#: How many maps a candidate set holds. The width of the real sets the palette
#: head was distilled and accepted on — a narrower set is an easier question than
#: the one it was measured answering.
CANDIDATES = 32

#: What a candidate and the picture that gets judged are rendered at. The size
#: both finished-render judges read and the size the palette head's own pictures
#: were formed at, so one render answers both.
RESOLUTION = (640, 360)
SUPERSAMPLE = 2

#: The curve every attempt reads its mode's field through: the identity. A mode
#: names a field *and* a curve to read it through, and a curve set here would
#: replace the mode's own — which is a different picture from the one the judges
#: were trained on.
CURVE = "linear"

#: The one mode the smooth judge owns. Every other mode the engine knows belongs
#: to the strange judge, which is how both corpora were collected.
SMOOTH_MODE = "smooth"

#: What an id carries when the seating leg asked for the render rather than the
#: plan. A prefix and not a high range, because the plan grows between re-seat
#: rounds and a counter shared with it would collide. See [`attempt_id`].
ON_DEMAND_PREFIX = "d"


class ColorizeError(RuntimeError):
    """An attempt cannot be made."""


@dataclass(frozen=True)
class Candidate:
    """One finished candidate wallpaper: the recipe, the verdict, the provenance."""

    row: dict

    @property
    def score(self):
        return self.row.get("p_ge3")

    @property
    def key(self) -> str:
        return self.row["key"]


def modes_for(kind: str) -> list[str]:
    """The modes one KIND covers, read out of the engine's catalog at call time.

    Still a two-way split of the roster, and still the axis a slot is allocated
    on — it just no longer picks a model. `smooth` is one mode and everything
    else is the other, which is a fact about the engine rather than about how
    many judges there are.

    The **accepted** roster only: a mode the engine tiers niche, or that
    [`mode_policy`] weights 0, is renderable by name and is excluded from every
    draw. The exclusion happens here because this is the one place a curation mode
    is drawn, and it is read off [`mode_policy.accepted`] rather than filtered here
    so that both halves of the ruling — the engine's tier and this project's
    standing — keep their meaning in one place each.
    """
    from fractal_wallpapers.curation import mode_policy

    names = mode_policy.accepted()
    if kind == budget_module.SMOOTH:
        return [SMOOTH_MODE]
    return [name for name in names if name != SMOOTH_MODE]


def modes_drawn_for(plan, seed) -> list[str]:
    """The modes one location is tried in by the head that is paying for it.

    Drawn **without replacement, per location** rather than per attempt: the
    strange judge takes two draws at a location and a second draw that could
    repeat the first buys the same picture twice. So the sample is taken once,
    off the location and the head, and each attempt takes its own element — which
    is what lets the two attempts stay independent of each other and of the order
    they run in, and lets a resumed run re-derive the same pair.

    A head planned more modes than it owns is refused rather than served a
    repeat. It cannot happen with the shipped roster — the smooth judge is asked
    for one and the strange judge owns every other production mode — and a
    silently duplicated draw would be the one outcome that spends the attempt and
    buys nothing, which is precisely what a second draw exists to avoid.
    """
    roster = modes_for(plan.head)
    wanted = max(1, int(plan.modes_drawn))
    if wanted > len(roster):
        raise ColorizeError(
            f"{plan.head} is planned {wanted} mode(s) a location and owns {len(roster)}: "
            f"{sorted(roster)}. The draws are without replacement, so there is no honest "
            f"answer here — either the head's roster shrank or curation.budget's "
            f"MODES_PER_LOCATION asks for more than the engine has."
        )
    return random.Random((seed, plan.head, plan.key).__str__()).sample(roster, wanted)


#: What separates a mode from its settings on a roster, and what separates the
#: settings from each other. `@` and `,` because `:` is already a partition's
#: separator (`julia:multibrot4`) and a roster entry is read beside partition
#: names constantly.
SETTINGS_MARK = "@"
SETTINGS_JOIN = ","


def roster_entry(text: str) -> tuple[str, dict]:
    """One roster entry — `mode`, or `mode@opacity=0.6,threshold=0.2` — read apart.

    **A leg names a `(mode, settings)` pair and the mode stays a catalog name.**
    That is the whole discipline here. `renders.coloring_of` already writes a
    direct trap's `opacity` and `threshold` into the coloring block, and
    `recipes.KEYED` already holds `mode_params`, so a varied entry is a new recipe
    key and nothing that exists moves: no re-key, no re-render of anything already
    made, no human label voided. Inventing a *name* for the variant instead would
    do the opposite — [`mode_policy.check`] refuses unless its table and the
    engine's catalog describe the same roster, and a name the engine never heard
    of fails that on the way in.

    The settings are floats and are **not** validated against the mode here.
    [`renders.coloring_of`] is the one owner of which settings a coloring takes,
    and a second copy of that list is how the two come to disagree; a caller that
    wants the refusal early asks it, which is what [`check_roster`] does.
    """
    text = str(text).strip()
    if SETTINGS_MARK not in text:
        return text, {}
    mode, _, spelled = text.partition(SETTINGS_MARK)
    settings: dict = {}
    for part in spelled.split(SETTINGS_JOIN):
        name, mark, value = part.partition("=")
        if not mark or not name.strip():
            raise ColorizeError(
                f"{text!r}: {part!r} is not a setting. A roster entry is a mode, or a mode "
                f"and its settings as 'mode{SETTINGS_MARK}name=value{SETTINGS_JOIN}name=value'."
            )
        name = name.strip()
        if name in settings:
            raise ColorizeError(f"{text!r} names {name!r} twice, and they disagree")
        try:
            settings[name] = float(value)
        except ValueError as bad:
            raise ColorizeError(f"{text!r}: {name}={value!r} is not a number") from bad
    if not mode.strip():
        raise ColorizeError(f"{text!r} carries settings and no mode to apply them to")
    return mode.strip(), settings


def spelled(mode: str, settings: dict | None = None) -> str:
    """A `(mode, settings)` pair as one string. [`roster_entry`]'s inverse.

    **The key a draw is taken per.** A palette draw keyed on the bare mode would
    hand four variants of one mode a single seeded sample between them — the same
    map for all four at a place, and worse, one shared `taken` set, so the second
    variant would be refused every map the first spent. Keyed on this, each
    `(mode, settings)` pair draws as its own mode, which is what it is: a
    different recipe key, a different picture, a different row.

    Sorted, so two spellings of one pair are one string.
    """
    settings = dict(settings or {})
    if not settings:
        return str(mode)
    body = SETTINGS_JOIN.join(f"{name}={settings[name]:g}" for name in sorted(settings))
    return f"{mode}{SETTINGS_MARK}{body}"


def check_roster(entries: list, family: dict, log=print) -> list[tuple[str, dict]]:
    """Every roster entry read apart and proved renderable, before anything renders.

    Through [`renders.coloring_of`] on a stand-in row, which is the one owner of
    what a coloring takes: an entry naming a setting its mode does not have, or a
    mode the engine does not know, is refused here rather than three thousand
    candidates into a leg. `family` is a real one from the population, because
    `coloring_of` opens the itinerary address against the plane.
    """
    from fractal_wallpapers.models import renders

    out: list[tuple[str, dict]] = []
    for entry in entries:
        mode, settings = roster_entry(entry)
        try:
            renders.coloring_of(
                {"mode": mode, "mode_params": settings, "curve": CURVE, "family": family}
            )
        except renders.RenderCacheError as refusal:
            raise ColorizeError(f"roster entry {entry!r}: {refusal}") from refusal
        out.append((mode, settings))
    varied = [spelled(mode, settings) for mode, settings in out if settings]
    if varied:
        log(f"[roster] {len(out)} entr(ies), {len(varied)} carrying settings: {varied}")
    return out


def kind_of(mode: str) -> str:
    """A mode's coloring kind — `field`, `composite` or `direct`."""
    from fractal_wallpapers.models import renders

    known = renders.catalog()
    if mode not in known:
        raise ColorizeError(f"the engine has no mode named {mode!r}")
    return known[mode]["kind"]


def _shipped_pool() -> list[str]:
    """The shipped pool, as this repository holds it — before the collapse."""
    from fractal_wallpapers.models import palette_sets

    held = {path.stem for path in _colormap_dir().glob("*.json")}
    return [name for name in palette_sets.pool()["pool"] if name in held]


def pool(seed: int = 0) -> list[str]:
    """The maps a colorize may choose between: the shipped pool, collapsed by group.

    The shipped pool holds maps that are the same choice twice — a ramp and its
    colour-vision variant, a cyclic map and the same map phase-shifted. A candidate
    set that holds both asks the head to break a tie nobody can see, and two
    attempts that land on the two of them spend two slots on one look.

    So the pool is read through [`palettes.groups`]: one member per group, **drawn
    at random on `seed`**, singletons untouched. Nothing leaves the library and no
    member is retired — a different seed stands a different member up, which is why
    the draw is random rather than canonical. [`pool_record`] is what a run writes
    down about it, and `palettes.groups.COLLAPSE_ENV` turns it off.
    """
    from fractal_wallpapers.palettes import groups

    members = _shipped_pool()
    if groups.enabled():
        members, _record = groups.collapse(members, seed)
    if len(members) < CANDIDATES:
        raise ColorizeError(
            f"the palette pool holds {len(members)} maps this repository has, and a candidate "
            f"set needs {CANDIDATES}. Bring the pool's maps across before a colorize."
        )
    return members


def pool_record(seed: int = 0) -> dict:
    """What a run's record says about the pool it drew from.

    Names the group every stood-down map stood down for, so the question a reader
    asks first — *why is this map not in the candidate set* — is answered by the
    run record rather than by re-running the draw.
    """
    from fractal_wallpapers.palettes import groups

    members = _shipped_pool()
    if not groups.enabled():
        return {
            "collapsed": False,
            "switch": groups.COLLAPSE_ENV,
            "library": len(members),
            "pool": len(members),
        }
    _members, record = groups.collapse(members, seed)
    return {**record, "switch": groups.COLLAPSE_ENV}


def _colormap_dir() -> Path:
    from fractal_wallpapers.paths import colormap_dir

    return colormap_dir()


def candidate_set(anchor: str, members: list[str], size: int = CANDIDATES) -> list[str]:
    """The `size` maps nearest `anchor` in palette space, the anchor first."""
    return space.neighbourhood(anchor, members, size)


def anchors(members: list[str], count: int, seed: int) -> list[str]:
    """`count` anchors, drawn without replacement and seeded.

    Without replacement so a run's attempts spread across the library rather than
    clustering; seeded so the release is reproducible from the run record alone.
    A run asking for more attempts than the pool has maps wraps, which is a real
    state rather than a refusal — it only means two attempts share a region.
    """
    draw = random.Random(seed)
    out: list[str] = []
    while len(out) < count:
        shuffled = list(members)
        draw.shuffle(shuffled)
        out.extend(shuffled[: count - len(out)])
    return out


# --------------------------------------------------------------------------- #
# The field, dumped once per (location, mode).
# --------------------------------------------------------------------------- #
#: The one coloring kind that has a single scalar field behind it, and therefore
#: the only one a dump can serve. The engine's own word — `renders.catalog` reads
#: it out of the catalog — and the composites, the modulate and the direct traps
#: are the other three. See [`shareable`].
FIELD_KIND = "field"

#: Modes whose dump the engine has refused in this process, so the refusal is
#: paid once rather than once a candidate. A refusal is a fact about the mode's
#: coloring and not about the location, which is what makes it cacheable here.
_UNSHAREABLE: set[str] = set()


def shareable(mode: str) -> bool:
    """Whether one iteration pass at this mode can serve every palette at it.

    A property of the *coloring*, asked of the engine's catalog: only a mode that
    maps one scalar field through the map has a field to dump, and the engine
    refuses the rest. Callers do not ask this — [`render`] does, which is what
    keeps the fallback automatic rather than a decision each site remembers.
    """
    return mode not in _UNSHAREABLE and kind_of(mode) == FIELD_KIND


def field_row(row: dict, mode: str, curve: str, render_geometry: dict | None = None) -> dict:
    """One location as the render-cache row its **field** is dumped from.

    The recolour half is pinned to the constants [`renders.field_job_name`] names
    the field by, because a dump spends nothing on it: what a `dump-field` reads
    of this row is the place, the geometry and the coloring, and the coloring is
    built by the same [`renders.coloring_of`] a render is built by. That identity
    is the whole of why a recolour can be byte-identical to a render — the curve
    curation renders through **replaces** the mode's catalogued one, and a field
    dumped by mode *name* would carry the catalogued curve into its record and
    recolour every `trap_circle` through a curve nobody rendered.
    """
    from fractal_wallpapers.models import renders

    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": mode,
        "mode_params": {},
        "curve": curve,
        "colormap": renders.FIELD_COLORMAP,
        "recipe": _plain_recipe(False),
        "render": render_geometry or _geometry(row),
    }


def field_of(
    row: dict,
    directory: Path,
    mode: str = SMOOTH_MODE,
    curve: str = CURVE,
    render_geometry: dict | None = None,
) -> Path:
    """The location's field in one mode at candidate geometry, dumped once and reused.

    The one iteration pass a whole candidate set pays for. Every map at this
    (location, mode) is a recolor of this, which is what makes a thirty-two-wide
    set cost about as much as one render instead of thirty-two.

    `mode` used to be pinned to [`SMOOTH_MODE`], because the only caller was the
    palette head's own pictures and those are smooth by definition. It is the
    row's own mode now, so the same one pass serves the candidate the attempt
    actually renders — and the smooth default keeps the head's call reading as
    what it is.
    """
    from fractal_wallpapers.models import renders

    # Through `renders.field_job_name` rather than a dict spelled out here: the
    # members a dumped field depends on are declared once, beside `spec_of`, so a
    # field-side axis added to the engine cannot be left out of this cache's name
    # by being forgotten at this call site. It used to be spelled out here.
    geometry = render_geometry or _geometry(row)
    name = renders.field_job_name(
        family=row["family"],
        viewport=row["viewport"],
        render=geometry,
        mode=mode,
        curve=curve,
    )
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.f32"
    if path.is_file() and path.with_suffix(".json").is_file():
        # Touched on the way past, so [`sweep_fields`] can read *last used* off
        # the file rather than *last written*. Without this the field a run is
        # in the middle of spending forty palettes on is the oldest thing in the
        # directory by the second palette, and the sweep would drop it.
        os.utime(path, None)
        return path
    # The spec goes through `renders.spec_of`, so the coloring a field is dumped
    # for is built by the one derivation a render's coloring is built by. The
    # binary lands first and its record second, which is what lets the pair's
    # presence mean *complete*: a dump killed halfway leaves a field with no
    # record, and the check above re-dumps it.
    engine.dump_field(renders.spec_of(field_row(row, mode, curve, geometry), path))
    return path


def _geometry(row: dict) -> dict:
    return {
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "maxiter": int(row["maxiter"]),
    }


def _plain_recipe(mirror: bool) -> dict:
    from fractal_wallpapers.labeling import finished

    return finished.recipe(mirror=mirror)


def recolored(
    field: Path,
    colormap: str,
    mirror: bool,
    output: Path,
    colormap_dir: Path | None = None,
) -> Path:
    """One candidate picture: the dumped field through one map, no re-iteration.

    `colormap_dir` is what the autolevel pass needs and nothing else does: the
    operator's second render is the same spec with the map's *stops* re-baked,
    so pointed at the levelled directory this is that render without the second
    iteration pass behind it. The transform is left unsaid, so the recolor reads
    the curve out of the dump's own record — which [`field_row`] put there.

    A file already at `output` is left alone: the candidate recolours the palette
    head reads are cached that way and remaking one would spend a render for a
    picture that exists. A caller that means to overwrite unlinks first, which
    is what [`render`] does.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.is_file():
        engine.recolor(
            {
                "schema": 1,
                "field": str(field),
                "colormap": colormap,
                "colormap_dir": str(colormap_dir or _colormap_dir()),
                "palette": _plain_recipe(mirror),
                "output": str(output),
            }
        )
    return output


#: How many dumped fields a unit of work keeps on disk. One field at candidate
#: geometry is 3.5 MiB — 1280×720 `f32` — so an unswept mine would leave several
#: gigabytes behind, and it needs none of them: a plan is grouped by location
#: within each arm, so only a handful are live at once. Sixty-four is two hundred
#: megabytes and about twenty times what the woven plan actually holds open.
FIELDS_KEPT = 64

#: How often an attempt leg sweeps its render fields. Not every attempt: the
#: sweep stats the whole directory, and the half of it a pass protects runs to
#: thousands of files. Fifty is under [`FIELDS_KEPT`], so nothing accumulates
#: between two of them.
FIELDS_SWEPT_EVERY = 50


def sweep_fields(directory: Path, keep: int = FIELDS_KEPT, protect: set | None = None) -> int:
    """Drop all but the `keep` most recently used fields here. Returns how many went.

    A field is worth keeping exactly as long as there are palettes left to spend
    at its (location, mode), and nothing knows that better than when it was last
    read — which [`field_of`] records by touching it. Called from the loop rather
    than at the end of it, because the point is the high-water mark and not the
    leftovers.

    `protect` names fields that are the *pass's* rather than one candidate's, and
    it exists for one of them: the palette head's smooth field at each location is
    read again after the attempt leg is over — a re-seat asks for another colour at
    a seat, and [`curation.gallery`] resolves a candidate recolour's name through
    it. Sweeping those would turn a name lookup into an iteration pass, thousands
    of times.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    protect = protect or set()
    held = [path for path in directory.glob("*.f32") if path.name not in protect]
    held.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    dropped = 0
    for path in held[int(keep) :]:
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)
        dropped += 1
    return dropped


# --------------------------------------------------------------------------- #
# The render, and the operator on it.
# --------------------------------------------------------------------------- #
def render_row(
    row: dict,
    mode: str,
    colormap: str,
    cyclic: set[str],
    render: dict | None = None,
    mode_params: dict | None = None,
    curve: str | None = None,
    palette: dict | None = None,
):
    """One candidate as the render-cache row its picture is made from.

    `mode_params` is what a leg naming a `(mode, settings)` pair on its roster
    carries down to here — see [`roster_entry`]. It lands in the coloring block
    through `renders.coloring_of`, so it is in the recipe key, in the job name and
    on the ledger row's own `recipe`, which is what makes a varied candidate a new
    picture rather than an overwrite of the shipped one.

    ## `curve` and `palette` are overrides, and every candidate leg leaves them off

    The candidate path spends [`CURVE`] and [`_plain_recipe`] and always has:
    those two defaults are what "a candidate" means here, and a leg that set them
    per attempt would be making pictures the judges were not fitted on.
    [`curation.recipes.of_decision`] reads the same two off the same places for
    the same reason.

    They are parameters because **the label corpora are not the candidate path**.
    A finished-render row records the curve and all seven palette knobs somebody
    actually judged, and 6,420 of the 11,966 resolved rows carry knobs this path
    never produces with 868 on `log` rather than `linear` — so re-expressing one
    of those recipes at candidate geometry needs a door that takes them. That is
    [`curation.label_migration`], which stages and merges nothing.

    The **field cache cannot serve an override** and [`render`] refuses the pair
    rather than quietly ignoring one: a dumped field is named for its curve and
    [`recolored`] pins the palette to `_plain_recipe`, so a recolour under an
    override would be the plain picture wearing the override's name.
    """
    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": mode,
        "mode_params": dict(mode_params or {}),
        "curve": CURVE if curve is None else str(curve),
        "colormap": colormap,
        "recipe": _plain_recipe(colormap not in cyclic) if palette is None else dict(palette),
        "render": render or _geometry(row),
    }


#: The temporary-then-rename convention, re-exported rather than restated. It is
#: `paths`' because the location head's view cache writes through it too, and a
#: second spelling of "unfinished" is a sweep that misses half of them.
WRITING_INFIX = paths.WRITING_INFIX
writing_path = paths.writing_path
sweep_writing = paths.sweep_writing


#: The stages [`render`] will attribute its wall clock to when a caller hands it
#: a meter. Declared as a tuple so a reader of a profile knows the whole set, and
#: so a stage added here cannot be one a summing caller silently drops.
#:
#: `paint` is the first colouring — a full iteration pass on the built path, a
#: colormap lookup on the shared one. `dump` is the iteration pass a shared field
#: pays once per (location, mode) and nothing after it pays again. `measure` is
#: the autolevel operator reading the tone of the picture it was handed, which is
#: **Python** — a JPEG decode and an Oklab pass — and is the one stage here the
#: engine has nothing to do with. `repaint` is the operator's second colouring.
METER_STAGES = ("dump", "paint", "measure", "repaint")


#: What a stage is timed on. **`perf_counter`, not `monotonic`**: `monotonic` is
#: `GetTickCount64` on Windows and its resolution is 15.6 ms, which was invisible
#: while a candidate was a 1.3 s render and is most of the answer now that one is
#: a 31 ms recolour. It is not a wall clock and nothing schedules on it — a budget
#: still reads `time.monotonic` — it only measures how long something took.
def tick() -> float:
    """Now, on the clock a duration here is measured against."""
    return time.perf_counter()


def _shared_field(
    row: dict,
    mode: str,
    render_geometry: dict | None,
    fields: Path | None,
    mode_params: dict | None = None,
) -> Path | None:
    """The dumped field this candidate can be a recolour of, or `None`.

    `None` three times over, and none of them a caller's: **no field cache was
    offered** — a one-off picture at a seat has no second palette to amortise a
    dump over — or **this coloring has no single scalar field**, which is the
    engine's word and covers the composites, the modulate and the direct traps, or
    **this candidate carries mode settings**. A dump the engine refuses costs
    nothing but the crossing, because it refuses before it iterates; the refusal is
    remembered against the mode anyway, so a mine that draws `threads` four hundred
    times pays it once.

    The third is the one worth stating. `renders.FIELD_IDENTITY` holds
    `mode_params`, so a field's name is *supposed* to depend on the settings — but
    [`field_row`] pins them to `{}` because nothing had ever varied them, and a
    varied candidate served out of that cache would be a recolour of the shipped
    mode's field wearing the variant's name. That is thirty-two wrong pictures per
    place, which is exactly the failure `field_job_name` refuses at. So a candidate
    with settings takes the render path, which is where every direct trap already
    is: the modes this door was opened for cannot dump anyway.
    """
    if fields is None or not shareable(mode) or dict(mode_params or {}):
        return None
    try:
        return field_of(row, Path(fields), mode=mode, render_geometry=render_geometry)
    except (RuntimeError, OSError):
        # A refusal is a fact about the mode, so it is remembered against the
        # mode. The candidate is still made — by the path that was there before.
        _UNSHAREABLE.add(mode)
        return None


def render(
    row: dict,
    mode: str,
    colormap: str,
    cyclic: set[str],
    output: Path,
    render_geometry: dict | None = None,
    level: bool = True,
    band: dict | None = None,
    fields: Path | None = None,
    meter: dict | None = None,
    reported: dict | None = None,
    mode_params: dict | None = None,
    curve: str | None = None,
    palette: dict | None = None,
) -> tuple[Path, dict | None]:
    """Render one candidate and level it. `(picture, stamp)`; the stamp may be `None`.

    THE one place a curation picture is made, so "every palette-mapped render is
    stamped" is true by construction rather than by four remembered edits. The
    direct-trap family is excluded here, where the kind is known, and not by a
    test inside the operator.

    ## The field is iterated once and spent many times

    `fields` names a directory the unit of work owns, and where one is given this
    largely stops being a render: the location's field **in this mode** is dumped
    there the first time it is asked for, and every later map at it — and the
    autolevel operator's second pass, which is the same field through a re-baked
    map — is a `recolor`, a colormap lookup over an array on disk. `curate mine
    bench` prices the two against each other.

    Which path serves a candidate is **not a caller's decision**. A composite, a
    modulate and a direct trap have no single scalar field behind them, the engine
    refuses to dump one, and those take the render path exactly as they did. A
    caller asks for a candidate; [`_shared_field`] decides, once per mode.

    `mode_params` is the mode's own settings, where a leg named a `(mode,
    settings)` pair on its roster ([`roster_entry`]). It reaches the coloring block
    through [`render_row`], so it is in the recipe key and in the job name: a
    varied candidate is a **new** picture beside the shipped one and never an
    overwrite of it. It also takes the render path unconditionally — see
    [`_shared_field`].

    `curve` and `palette` are [`render_row`]'s overrides and every candidate leg
    leaves them off; the one caller is [`curation.label_migration`], re-expressing
    a judged recipe at candidate geometry. **They refuse a `fields` directory**
    rather than being quietly dropped, for the reason `render_row` states — and
    the refusal is here rather than there because `render_row` is also called to
    describe a picture that is not being made.

    The two paths are held to producing the *same bytes* — not a similar picture,
    the same file — by `test_a_recolour_is_the_render_byte_for_byte`, because a
    recolour that were merely close would move every judge score in the ledger
    without moving anything a reader could see.

    `meter`, where a caller hands one over, is added to rather than replaced, and
    the stages are [`METER_STAGES`]. It exists because the profile that sent this
    leg had `render` at 97% of a mine's clock and could say nothing about what was
    inside it — and now that the iteration pass is gone from most candidates, what
    is inside it is the whole question.

    `reported` takes the **engine's own report** for this candidate, on the same
    terms: a dict the caller owns, updated rather than replaced. What the engine
    says about a render it just made — `interior_fraction`, and
    `texture_flat`, which says the modulate's texture moved nothing and the
    picture is its base spent by rank — used to be parsed and dropped on the
    floor here, and a ledger row built downstream could not carry a fact the
    engine had already computed. The recolour path fills nothing: a dumped field
    is re-coloured in this process and there is no engine to report. That is not a
    gap to paper over — [`shareable`] is false for every coloring that has a
    texture, so a mode whose report anybody reads never takes that path.

    **Nothing exists at `output` until the row is finished.** Every render lands
    on a temporary and is renamed into place at the end, which makes the file's
    presence mean *complete* rather than *started*. That is not a nicety: the
    autolevel path is two full-resolution passes to one path, and the first
    production run lost four rows to it — the deadline killed the second render,
    the first one's decodable picture stayed on disk, and the resume counted all
    four as finished. Every number balanced and four pictures carried no operator
    pass. A rename is atomic on both platforms this repository runs on, so the
    intermediate state has no name a reader can reach.
    """
    from fractal_wallpapers.models import renders

    if fields is not None and (curve is not None or palette is not None):
        raise RuntimeError(
            "a curve or palette override cannot be served out of the field cache: a dumped "
            "field is named for its curve and `recolored` pins the palette to the plain "
            "recipe, so the recolour would be the plain picture under the override's name. "
            "Pass fields=None for an overridden render."
        )
    output = Path(output)
    scratch = writing_path(output)
    recipe = render_row(row, mode, colormap, cyclic, render_geometry, mode_params, curve, palette)
    spec = renders.spec_of(recipe, scratch)
    mirror = bool(recipe["recipe"]["mirror"])
    output.parent.mkdir(parents=True, exist_ok=True)
    ticks = meter if meter is not None else {}

    def spent(stage: str, since: float) -> None:
        ticks[stage] = ticks.get(stage, 0.0) + (tick() - since)

    at = tick()
    field = _shared_field(row, mode, render_geometry, fields, mode_params)
    spent("dump", at)

    def paint(stage: str, colormap_dir: Path | None = None) -> None:
        """This candidate onto the temporary, by whichever path is serving it."""
        at = tick()
        scratch.unlink(missing_ok=True)
        if field is None:
            here = spec if colormap_dir is None else {**spec, "colormap_dir": str(colormap_dir)}
            report = engine.run("render", here)
            if reported is not None and isinstance(report, dict):
                reported.update(report)
        else:
            recolored(field, colormap, mirror, scratch, colormap_dir=colormap_dir)
        spent(stage, at)

    paint("paint")
    if not level or not autolevel.applies_to(kind_of(mode)):
        scratch.replace(output)
        return output, None

    entry = json.loads((_colormap_dir() / f"{colormap}.json").read_text(encoding="utf-8"))

    def rerender(stops):
        # Named for the FINAL picture, not the temporary: the levelled colormap is
        # a record of what this row was rendered through, and a resume looks for
        # it under the row's own name.
        directory = output.parent / f"{output.stem}.leveled"
        autolevel.overriding_colormap(colormap, stops, entry.get("kind"), directory)
        paint("repaint", directory)
        return scratch

    at = tick()
    repainted = ticks.get("repaint", 0.0)
    leveled = autolevel.maybe_level(
        scratch, {"name": colormap, "stops": entry["stops"], "mirror": mirror}, rerender, band
    )
    # The operator's own share is what it took MINUS the colouring it asked for,
    # which `paint` has already booked to `repaint`. Measured this way round
    # because the alternative is a timer inside `maybe_level`, and the operator
    # would then have to know it is being profiled.
    spent("measure", at)
    ticks["measure"] -= ticks.get("repaint", 0.0) - repainted
    Path(leveled.image).replace(output)
    return output, leveled.stamp


def attempt_id(row: dict) -> str:
    """The candidate id of one attempt row, and the file name of its picture.

    The plan index for an ordinary attempt, `d0007` for one the seating leg asked
    for on demand. Two namespaces and not one counter, because the plan **grows**
    between re-seat rounds: an on-demand render numbered off the plan's length in
    round zero would collide with a planned attempt in round one, and the two rows
    would be one picture on disk.

    The id **is** the picture's file name under the run's `pictures/`, which is
    what [`fractal_wallpapers.curation.rescore.picture_of`] assumes of every row
    in the pool.
    """
    if row.get("on_demand"):
        return f"{ON_DEMAND_PREFIX}{int(row['attempt']):04d}"
    return f"{int(row['attempt']):04d}"


def another_colour(names: list, scores, recolour_of, spent: set, families: set):
    """The head's next-best map carrying a hue family none of `families` holds.

    The **screen** the seating leg asks for an extra picture by, and it is a screen
    and never a verdict. Dominance is read here on the recolour of the location's
    *smooth* field, and the picture that gets made is the mode the attempt drew:
    over three hundred of gallery3's rows the family-mass difference between the
    two runs 0.005 for a smooth attempt and **0.396** for a strange one, against a
    total clamped mass of about 0.79. Half a strange picture's colour is in
    different families from the one this function looked at. So what it buys is a
    render that had a *reason* to be a different colour; what says what that render
    is of is its own picture, read at the seat like any other candidate.

    Walked in the head's own score order and stopped at the first hit: a recolour
    is an engine call and a census is about twenty milliseconds, so screening all
    thirty-two would cost more than the render it is choosing.
    """
    import numpy

    from fractal_wallpapers.palettes import dominance

    ranked = numpy.argsort(-numpy.asarray(scores, dtype=numpy.float64), kind="stable")
    for index in ranked:
        name = names[int(index)]
        if name in spent:
            continue
        picture = recolour_of(name)
        if picture is None:
            continue
        carried = set(dominance.of_picture(picture).families)
        if carried and not carried <= families:
            return name
    return None


# --------------------------------------------------------------------------- #
# The attempt.
# --------------------------------------------------------------------------- #
def load_judge(device: str = "auto"):
    """THE shipped finished-render judge, as a loaded `(model, config, where)`.

    A module function rather than only a method, because two legs want the judge
    and only one of them wants a palette head with it: a hunt
    ([`curation.hunt`]) is defined by not asking the palette head anything, and
    building a whole [`Colorizer`] to reach the judge would load two gigabytes of
    model to route around one of them.
    """
    from fractal_wallpapers.models import render_train, ship

    return render_train.load_checkpoint(ship.shipped_path(floors.SCORING_HEAD), device)


def score_picture(judge, picture: Path) -> dict:
    """One finished picture through a loaded judge: every cutpoint, unconditional."""
    from fractal_wallpapers.models import scoring, train

    model, config, where = judge
    classes = int(config["classes"])
    transform = scoring.transform_of(config)
    probabilities = train.score(model, [picture], transform, where, classes, {"batch_size": 1})
    row = {f"p_ge{index + 2}": float(probabilities[0][index]) for index in range(classes - 1)}
    row["rank_score"] = float(sum(probabilities[0]))
    return row


class Colorizer:
    """The heads, the pool and the caches an attempt needs, loaded once.

    A class rather than a bag of parameters because the three models are the
    expensive part: loading them per attempt would dominate a small run, and
    threading them through six call sites is how one of them ends up loaded twice.
    """

    def __init__(self, directory: Path, seed: int, device: str = "auto", log=print):
        from fractal_wallpapers.models import palette_head, palette_scoring, ship

        self.directory = Path(directory)
        self.seed = int(seed)
        self.log = log
        self.pool = pool(self.seed)
        self.cyclic = cyclic()
        self.band = band()
        self.palette, self.palette_config, self.where = palette_scoring.load(
            ship.shipped_path("palette"), device
        )
        self.palette_transform = palette_head.Transform(train=False)
        self.judges = {}
        self.device = device
        #: `palette group -> the map an attempt of this plan already picked`. The
        #: proposal-time group cap, and the whole of its state: an identity table,
        #: no pictures and no distances. Seeded from the rows a resumed pass
        #: already recorded, so a resume claims what its own attempts claimed.
        self.claimed: dict = {}
        self._groups = None
        #: The smooth fields the palette head has been asked for this pass. They
        #: outlive the attempt that made them — the seating leg reads a candidate
        #: recolour's name through one — so [`sweep_fields`] is told to leave them
        #: alone. Everything else under `fields/` belongs to one candidate.
        self._head_fields: set = set()

    @property
    def fields(self) -> Path:
        """Where this pass's dumped fields live: one per (location, mode).

        The palette head's own recolours were always read off a field under here;
        what changed is that the attempt's *rendered* candidate is read off one
        too, so a location the head was asked about in `smooth` and then rendered
        in `smooth` iterates once for both.
        """
        return self.directory / "fields"

    def judge(self):
        """THE finished-render judge, loaded on first use and kept.

        One judge for both kinds since 2026-08-23. It used to be one per kind and
        the cache is kept because loading is the expensive part either way — what
        went away is the argument, so a caller can no longer reach the wrong
        model by naming a kind.
        """
        head = floors.SCORING_HEAD
        if head not in self.judges:
            self.judges[head] = load_judge(self.device)
        return self.judges[head]

    def pick_palette(self, row: dict, names: list) -> tuple:
        """Score every candidate map on this location and return the head's choice.

        `(colormap, scores, skipped)`. The pick is the head's argmax, **except**
        where that map's palette group has already been picked by another attempt
        of this plan: then the head's next-ranked candidate takes it, and the maps
        passed over are on the row.

        That filter is a pure identity check — no state about pictures, no pixels,
        no distances — and it makes the group cap a property of the **plan** rather
        than only of the seat. gallery3's 150 seats named 91 distinct groups and 59
        of them sat above one, with `wallhaven_wallhaven-1joljg` seven times: every
        one of those was a seat spent on a decision the pass had already taken, and
        none of them could have been undone at seating time because the
        alternatives were never rendered.

        It degrades rather than failing: a plan makes thousands of attempts and the
        pool holds hundreds of groups, so once every group in a set is claimed the
        filter stops acting and the head's own pick stands, recorded as
        `exhausted`.
        """
        from fractal_wallpapers.models import palette_head, palette_teacher

        pictures = self.recolours(row, names)
        scores = palette_teacher.scored_with(
            self.palette, pictures, self.palette_transform, self.where, 64
        )
        top = names[palette_head.top_pick(scores)]
        colormap, skipped = self.unclaimed(names, scores, top)
        self.claim(colormap)
        return colormap, [float(value) for value in scores], skipped

    def recolours(self, row: dict, names: list) -> list:
        """This location's smooth field through each named map. The head's own pictures.

        Cached on disk under the pass directory and swept after the attempt leg, so
        the seating leg asking for one again remakes it — which is a recolour and
        not an iteration pass, and is why an extra pick at a seat costs a render
        rather than a whole attempt.
        """
        field = field_of(row, self.fields)
        self._head_fields.add(field.name)
        return [
            recolored(
                field,
                name,
                name not in self.cyclic,
                self.directory / "candidates" / field.stem / f"{name}.jpg",
            )
            for name in names
        ]

    def group_of(self, colormap: str) -> str:
        """Which palette group a map belongs to; its own name where it is a group of one."""
        from fractal_wallpapers.palettes import groups as palette_groups

        if self._groups is None:
            self._groups = palette_groups.member_groups()
        return palette_groups.group_of(str(colormap), self._groups)

    def unclaimed(self, names: list, scores, top: str) -> tuple:
        """`(pick, skipped)` — the best-ranked map whose group no attempt has taken.

        `skipped` is `None` where the head's own pick stood, which is the ordinary
        case and costs the row nothing. Where every group in the set is already
        claimed the head's pick stands anyway and the block says `exhausted`: a
        plan that refused to colour an attempt at all would be a plan trading a
        picture for a property.
        """
        import numpy

        if self.group_of(top) not in self.claimed:
            return top, None
        passed = []
        for index in numpy.argsort(-numpy.asarray(scores, dtype=numpy.float64), kind="stable"):
            name = names[int(index)]
            group = self.group_of(name)
            if group not in self.claimed:
                return name, {"passed": passed, "for": name}
            passed.append({"map": name, "group": group, "taken_by": self.claimed[group]})
        return top, {"passed": passed[:1], "for": top, "exhausted": True}

    def claim(self, colormap) -> None:
        """Record that an attempt has picked this map, so the plan will not pick its group again."""
        if colormap:
            self.claimed.setdefault(self.group_of(str(colormap)), str(colormap))

    def score_picture(self, picture: Path) -> dict:
        """One finished picture through this colorizer's judge."""
        return score_picture(self.judge(), picture)

    def attempt(
        self,
        plan: budget_module.Attempt,
        row: dict,
        anchor: str,
        index: int,
        colormap: str | None = None,
        on_demand: bool = False,
        mode: str | None = None,
    ) -> dict:
        """One colorize, end to end, as the durable row it becomes.

        A failure is a recorded row with a reason and **no score**, never a zero:
        a crash and a bad wallpaper must not be the same number.

        `colormap`, where it is given, **bypasses the palette head entirely** and
        colours the attempt with the named map. Two callers want that and both
        want it for the same reason — the head is the step being routed around.
        A **carrier attempt** is planned that way because a target names a colour
        the head declines 83% below the rate it accepts everything else at; an
        **on-demand pick** is asked for at a seat where the ceiling refused
        everything the plan proposed. Either way the picture is judged by the same
        judge and read at the seat by the same rule, so it is a candidate and never
        a privilege.

        `mode` overrides the draw, for an on-demand pick that is a second colour of
        an attempt that already happened: it has to be the *same picture in a
        different palette*, which means the same mode and not a fresh draw.
        """
        # An attempt the caller has named a map for is not built around an anchor
        # and has no set: the head is not being asked. Skipping the neighbourhood
        # is not merely an economy — an on-demand pick inherits its anchor from a
        # standing row, and a row another pass made under another seed names a map
        # this pass's collapsed pool may not hold at all.
        names = [] if colormap is not None else candidate_set(anchor, self.pool)
        record = {
            "schema": intake.SCHEMA,
            "attempt": index,
            "head": plan.head,
            "partition": plan.partition,
            "key": plan.key,
            "rank": plan.rank,
            # Which of this location's mode draws this attempt is. On the row
            # because the readout's question about the second draw is whether it
            # seated anything the first one would not have, and that cannot be
            # asked of a log where the two attempts are indistinguishable.
            "mode_index": plan.mode_index,
            "modes_drawn": plan.modes_drawn,
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": row.get("maxiter"),
            "location_score": row.get("score"),
            "ledger": row.get("_ledger"),
            "anchor": anchor,
            "candidates": names,
            "mode": None,
            "mode_kind": None,
            "curve": CURVE,
            "render": _geometry(row),
        }
        if on_demand:
            record["on_demand"] = True
        try:
            # The roster is read out of the engine, so drawing the mode is an
            # engine call like any other and belongs inside the try: "a failed
            # attempt is a recorded row" is not true of a step taken before the
            # first one, and a killed attempt would take the whole run down.
            # Uniform over the paying head's roster, by Matt's call for the first
            # long run: steering this draw is a future lever, not an unmade decision.
            drawn = mode or modes_drawn_for(plan, self.seed)[plan.mode_index]
            record.update({"mode": drawn, "mode_kind": kind_of(drawn)})
            if colormap is None:
                colormap, scores, skipped = self.pick_palette(row, names)
                if skipped is not None:
                    record["group_skipped"] = skipped
            else:
                colormap, scores = str(colormap), []
                record["named"] = colormap
                self.claim(colormap)
            picture = self.directory / "pictures" / f"{attempt_id(record)}.jpg"
            # A pass makes one picture per (location, mode) and thousands of
            # locations, so the render's own fields are working and not record:
            # swept down as the leg goes, with the head's own left standing.
            # Every fiftieth attempt and not every one, because the sweep stats
            # the whole directory and the head's half of it is thousands of files.
            if index % FIELDS_SWEPT_EVERY == 0:
                sweep_fields(self.fields, protect=self._head_fields)
            picture, stamp = render(
                row,
                drawn,
                colormap,
                self.cyclic,
                picture,
                level=True,
                band=self.band,
                fields=self.fields,
            )
            verdict = self.score_picture(picture)
        except Exception as failure:  # noqa: BLE001 — a failed attempt is a recorded row
            record["error"] = repr(failure)[:400]
            record["picture"] = None
            return record
        record.update(
            {
                "colormap": colormap,
                "mirror": colormap not in self.cyclic,
                "candidate_scores": [round(value, 6) for value in scores],
                "picture": str(picture.relative_to(self.directory)),
                "autolevel": stamp,
                "error": None,
                **verdict,
            }
        )
        return record


def cyclic() -> set[str]:
    """The maps production does NOT fold, off the palette sets' own answer."""
    from fractal_wallpapers.models import palette_sets

    return palette_sets.cyclic()


def band() -> dict | None:
    """The autolevel band every render here levels onto, or `None` with the switch off."""
    from fractal_wallpapers.coloring import band as band_module

    return band_module.load() if autolevel.enabled() else None


def annotate(record: dict) -> dict:
    """This head's release cut, and its verdict on one candidate, onto the row.

    Written under `bar` where the head's cut acts and under `advisory` where it
    only annotates, so the field name says which one a reader is looking at
    rather than a flag inside it. Every scored row of a gated head carries the
    bar, released or not: the record of what a bar removed is the population half
    of the question anybody later asks about what it bought.

    Tri-state either way, and `None` on a failed render for the reason the cut
    itself is tri-state: a crash has no score to compare and recording it as a
    failure to clear would make the two indistinguishable. The *seating* decision
    is not tri-state — see [`floors.Bar.seats`] — and it is taken at selection,
    not here.
    """
    if record.get("head") is None:
        return record
    cut = floors.release_cut(record["head"])
    written = {
        "name": cut.name,
        "value": cut.value,
        "head_sha256": cut.stamp,
        "clears": cut.clears(record.get("p_ge3")),
    }
    if isinstance(cut, floors.Bar):
        record["bar"] = {**written, "acts": True}
    else:
        record["advisory"] = written
    return record


__all__ = [
    "CANDIDATES",
    "CURVE",
    "ON_DEMAND_PREFIX",
    "RESOLUTION",
    "SMOOTH_MODE",
    "SUPERSAMPLE",
    "WRITING_INFIX",
    "Candidate",
    "ColorizeError",
    "Colorizer",
    "anchors",
    "annotate",
    "another_colour",
    "attempt_id",
    "band",
    "candidate_set",
    "cyclic",
    "FIELDS_KEPT",
    "FIELDS_SWEPT_EVERY",
    "METER_STAGES",
    "FIELD_KIND",
    "field_of",
    "field_row",
    "kind_of",
    "load_judge",
    "modes_drawn_for",
    "modes_for",
    "pool",
    "pool_record",
    "recolored",
    "shareable",
    "tick",
    "sweep_fields",
    "render",
    "render_row",
    "score_picture",
    "sweep_writing",
    "writing_path",
]
