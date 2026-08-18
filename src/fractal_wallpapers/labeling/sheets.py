"""THE labeling sheet generator: two row sources, one cut, one page.

A sheet is one cut, one manifest, one export. It is built into an untracked run
directory, served by [`fractal_wallpapers.labeling.server`], and comes back as a
single `labels/<head>.json` that [`fractal_wallpapers.labeling.intake`] turns
into store rows. Nothing else writes a label.

## Two row sources, and everything after them is shared

This project asks a person two questions, and they are about different objects:

```text
location          is this PLACE worth rendering        two renders of one place
finished_render   is this PICTURE worth keeping        one finished render
```

They differ in what a unit is, what gets rendered, and which judge prefills the
suggestions — and in nothing else. So a [`Source`] owns exactly those three
things, and the cut, the ordering, the ids, the manifest, the row file, the
thumbnails, the page and the export are one implementation underneath both. Two
generators is how a project ends up with two answers to what an export is called,
which is a bug nobody sees until two tabs are open.

## A row carries its whole join

Every sheet row hands over the join its store keys on — the place for a location,
the place *and* the whole recipe for a finished render — because the sheet
directory is untracked and disposable and the store has to outlive it. The join
travels in one field, `join`, in the shape that store's own writer accepts, so
intake resolves it without reconstructing anything.

## Two renders, and the labeler judges from the second

A location unit is rendered twice from the same place: once through the
**canonical** colormap, which is what a head will see, and once through the
**vivid** one, which is what a person judges from. A crushing palette makes good
material look dead, and the verdict is about the location, not about one unlucky
map. Both maps are read off the committed library in `data/palettes/` by name and
the sheet refuses to build if either is missing: a sheet built against a colormap
that existed only in the process that built it is a sheet whose rows can never be
re-rendered.

A finished-render unit is already a picture — a mode, a map and every knob of the
palette pass — so it is rendered once, exactly as it is recorded.

## Correction mode is the design

The intended sheet serves a head's own decode as a **prefilled suggestion**,
orders the page good→bad by its score, and offers a sweep that accepts every
suggestion below a chosen row behind a confirmation. That is what makes a
labeling hour worth more than a blind one: the labeler spends it on the rows the
head got wrong. The two finished-render judges exist and do this. No location
head exists in this repository yet, and that sheet says so rather than pretending
— with the null scorer there are no suggestions, no sweep and no score order, and
the page serves a **seeded shuffle**, which is unsorted with respect to anything
but is still reproducible, and is not draw order, because draw order arrives in
blocks and a block of one source's material drags the bar.

**A suggestion is not a label.** A sheet row carries no score field at all. The
only thing that becomes a label is what a person exported from the page, and
intake refuses anything else, so an unreviewed suggestion cannot leave the page
as a verdict.

## The picture is named for the build, the unit for the page

A picture is written under its position in the *plan*, and the `u0001` id is
assigned after the order is fixed — so the id encodes the page position and
nothing else, and re-ordering a sheet does not invalidate a single render. That
second half is what makes a long cut resumable: a killed build finds its pictures
on disk and continues.
"""

from __future__ import annotations

import json
import random
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import finished, store
from fractal_wallpapers.paths import colormap_dir

#: The schema every sheet manifest and row carries.
SCHEMA = 1

#: The judge the location rig collects for.
LOCATION_HEAD = "location"

#: The map a location head sees, and the one a location label is stored against.
CANONICAL_COLORMAP = "twilight_shifted"

#: The map a person judges a location from.
VIVID_COLORMAP = "blue_orange"

#: What a location sheet renders at. Big enough to judge as a wallpaper, small
#: enough that a thousand of them is an afternoon rather than a night.
SHEET_RESOLUTION = (1280, 720)
SHEET_SUPERSAMPLE = 2

#: What both finished-render corpora were collected at, and therefore what a
#: finished-render sheet renders at: a picture judged at a different geometry than
#: the corpus is a verdict about a different picture.
LABEL_RESOLUTION = (1280, 720)
LABEL_SUPERSAMPLE = 2
LABEL_FILTER = "lanczos3"

#: The overview grid's thumbnails. Small on purpose: three hundred full renders
#: in one page's sidebar is a page that never finishes loading.
THUMB_WIDTH = 320
THUMB_QUALITY = 80

MANIFEST_NAME = "sheet.json"
ROWS_NAME = "sheet.jsonl"


class SheetError(ValueError):
    """A sheet that cannot be built, served or ingested."""


def colormap(name: str) -> str:
    """Return `name`, having proved the committed library holds that map."""
    if not (colormap_dir() / f"{name}.json").is_file():
        raise SheetError(
            f"colormap {name!r} is not in the committed library ({colormap_dir().name}/). A "
            f"sheet renders through named, tracked maps only — a map that exists just in the "
            f"process that built the sheet cannot re-render a single one of its rows."
        )
    return name


# --------------------------------------------------------------------------- #
# What a source is.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Source:
    """One kind of thing to judge: what a unit is, what it renders to, who suggests.

    Everything else about a sheet is shared, so this carries only the three
    things that genuinely differ. `cut` renders one unit and returns the row
    without its id; `suggest` fills every row's suggestion in one pass, because
    a judge that reads pictures wants them all at once; `order` decides what the
    page's reading order is and says which rule it used.
    """

    kind: str
    head: str
    #: `(unit, directory, name) -> row`, minus the `unit` id the order assigns.
    cut: object
    #: `(rows, units, log) -> scorer name`. Fills `suggestion` and `columns`.
    suggest: object
    #: `(rows, seed) -> (indices, order mode)`.
    order: object
    #: The scale a person casts on this sheet, and what the tiers mean.
    tiers: tuple
    rubric: str
    #: What goes on the manifest under `render`, for a reader with no pictures.
    render_record: dict = field(default_factory=dict)
    #: Anything the cut learned that a reader of the manifest needs. Written
    #: under `cut` when it is not empty, and left off the manifest when it is.
    notes: dict = field(default_factory=dict)


@dataclass
class Sheet:
    """A built sheet: where it is, what it holds, and how it was ordered."""

    directory: Path
    manifest: dict
    rows: list

    def path(self, name: str) -> Path:
        return self.directory / name

    @property
    def head(self) -> str:
        return self.manifest["head"]

    @property
    def by_unit(self) -> dict[str, dict]:
        return {row["unit"]: row for row in self.rows}


# --------------------------------------------------------------------------- #
# The location source.
# --------------------------------------------------------------------------- #
def render_spec(row: dict, name: str, output: Path, resolution, supersample: int) -> dict:
    """The engine spec for one of a location unit's two renders."""
    spec: dict = {
        "schema": 1,
        "family": row["family"],
        "viewport": row["viewport"],
        "resolution": list(resolution),
        "supersample": supersample,
        "mode": "smooth",
        "colormap": name,
        "colormap_dir": str(colormap_dir()),
        "output": str(output),
    }
    if row.get("maxiter") is not None:
        spec["maxiter"] = row["maxiter"]
    return spec


def render_pair(row: dict, canonical: Path, vivid: Path, resolution, supersample: int) -> dict:
    """Render one location twice through the engine. The default renderer."""
    report = engine.render_report(
        render_spec(row, CANONICAL_COLORMAP, canonical, resolution, supersample)
    )
    engine.render_report(render_spec(row, VIVID_COLORMAP, vivid, resolution, supersample))
    return report


def family_line(family: dict) -> str:
    """A family as one line of page furniture. Every constant that identifies it."""
    degree = family.get("degree")
    line = str(family.get("kind", "?")) + (f" d={degree}" if degree else "")
    for name in ("c", "p", "z_prev"):
        if family.get(name):
            value = family[name]
            line += f" · {name}=({float(value[0]):.6g}, {float(value[1]):.6g})"
    return line


def viewport_line(viewport: dict, maxiter) -> str:
    return (
        f"centre {viewport['center_re']}, {viewport['center_im']} · "
        f"width {viewport['width']} · maxiter {maxiter}"
    )


LOCATION_RUBRIC = (
    "<b>1–4, one scale, every family</b> — judge from the vivid render. "
    "<span class='s1'>1</span> dead or structureless; never ships · "
    "<span class='s2'>2</span> has structure but unremarkable; below the floor · "
    "<span class='s3'>3</span> a genuine wallpaper; this is the floor · "
    "<span class='s4'>4</span> the best of the good ones, worth surfacing first. "
    "A 4 is a tier on the same scale, not a new floor."
)


def location_source(
    scorer=None,
    renderer=None,
    resolution=SHEET_RESOLUTION,
    supersample: int = SHEET_SUPERSAMPLE,
) -> Source:
    """The source that asks whether a place is worth rendering."""
    canonical_map, vivid_map = colormap(CANONICAL_COLORMAP), colormap(VIVID_COLORMAP)
    render = render_pair if renderer is None else renderer
    if scorer is None:
        from fractal_wallpapers.discovery.scoring import NullScorer

        scorer = NullScorer()

    def cut(unit: dict, directory: Path, name: str) -> dict:
        canonical_png = directory / "canonical" / f"{name}.png"
        vivid_png = directory / "vivid" / f"{name}.png"
        for picture in (canonical_png, vivid_png):
            picture.parent.mkdir(parents=True, exist_ok=True)
        report = render(unit, canonical_png, vivid_png, resolution, supersample) or {}
        return {
            "join": {
                "family": unit["family"],
                "viewport": unit["viewport"],
                "render": {
                    "resolution": list(resolution),
                    "supersample": supersample,
                    "mode": "smooth",
                    "colormap": canonical_map,
                    "maxiter": report.get("maxiter", unit.get("maxiter")),
                },
                "judged_from": vivid_map,
            },
            "pictures": [
                {"caption": f"judge from · {vivid_map}", "path": f"vivid/{name}.png"},
                {"caption": f"stored against · {canonical_map}", "path": f"canonical/{name}.png"},
            ],
            "thumb": f"vivid/{name}.png",
            "facts": [
                family_line(unit["family"]),
                viewport_line(unit["viewport"], report.get("maxiter", unit.get("maxiter"))),
            ],
        }

    def suggest(rows: list[dict], units: list[dict], log) -> str:
        del log
        for row, unit in zip(rows, units, strict=True):
            # A location head would decode a tier here. None exists, and a sheet
            # that invented one would be serving a suggestion nobody stands behind.
            row["suggestion"] = None
            row["suggestion_score"] = scorer.score(unit)
        return getattr(scorer, "name", "null")

    def order(rows: list[dict], seed: int) -> tuple[list[int], str]:
        scores = [row["suggestion_score"] for row in rows]
        if any(score is not None for score in scores):
            indices = sorted(
                range(len(rows)),
                key=lambda i: (scores[i] is None, -(scores[i] or 0.0), i),
            )
            return indices, "score"
        indices = list(range(len(rows)))
        random.Random(seed).shuffle(indices)
        return indices, "shuffle"

    return Source(
        kind="location",
        head=LOCATION_HEAD,
        cut=cut,
        suggest=suggest,
        order=order,
        tiers=store.SCORES,
        rubric=LOCATION_RUBRIC,
        render_record={
            "resolution": list(resolution),
            "supersample": supersample,
            "canonical_colormap": canonical_map,
            "vivid_colormap": vivid_map,
        },
    )


# --------------------------------------------------------------------------- #
# The finished-render source.
# --------------------------------------------------------------------------- #
FINISHED_RUBRIC = {
    "smooth_render": (
        "<b>1–4, judged as a wallpaper.</b> "
        "<span class='s1'>1</span> does not work · "
        "<span class='s2'>2</span> has structure but is unremarkable · "
        "<span class='s3'>3</span> a genuine wallpaper, the floor a picture ships at · "
        "<span class='s4'>4</span> the best of those. A 4 is a tier on the same scale, not a "
        "new floor."
    ),
    "strange_render": (
        "<b>1–4, judged as a rendering.</b> "
        "<span class='s1'>1</span> does not work · "
        "<span class='s2'>2</span> has structure but is unremarkable · "
        "<span class='s3'>3</span> a rendering worth keeping · "
        "<span class='s4'>4</span> exceptional — the best of those. A 4 is a tier on the same "
        "scale, not a new floor."
    ),
}


def thumbnail(picture: Path, output: Path) -> Path:
    """One overview cell. Kept if it is already there — a page rebuild is cheap."""
    from PIL import Image

    if output.is_file():
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(picture) as opened:
        image = opened.convert("RGB")
        height = max(1, round(image.height * THUMB_WIDTH / image.width))
        image = image.resize((THUMB_WIDTH, height), Image.LANCZOS)
    image.save(output, "JPEG", quality=THUMB_QUALITY)
    return output


def stated_recipe(recipe: dict) -> dict:
    """A plan's own palette pass, normalized through the one owner of that object.

    A revision sheet re-serves pictures the store already holds, and a picture
    the store holds was made through a recipe nobody is free to re-derive: two
    rows that differ in a gamma are two pictures and two identities. So a plan
    unit may hand over the whole recipe, and it hands over the **whole** one —
    a partial recipe topped up with defaults is a guess about what somebody was
    looking at when they judged it.
    """
    if not isinstance(recipe, dict):
        raise SheetError(f"a plan unit's recipe is {type(recipe).__name__}, not an object")
    missing = [key for key in finished.RECIPE_KEYS if key not in recipe]
    if missing:
        raise SheetError(
            f"a plan unit's recipe names no {', '.join(missing)}. Every knob of the palette "
            f"pass travels or the picture cannot be rebuilt."
        )
    unknown = sorted(set(recipe) - set(finished.RECIPE_KEYS))
    if unknown:
        raise SheetError(f"a plan unit's recipe carries {unknown}, which the engine never reads")
    return finished.recipe(**recipe)


def cached_picture(head: str, join: dict) -> Path | None:
    """The render cache's own picture for exactly this join, if it holds one.

    The cache names a picture by a digest of the whole engine spec, so a hit is
    the picture this sheet would have rendered — same renderer, same recipe,
    same geometry — and anything that differs anywhere at all is a miss. That is
    what makes reuse safe rather than an optimization somebody has to trust.
    """
    from fractal_wallpapers.models import renders

    try:
        name = renders.job_name({**join, "_head": head})
    except renders.RenderCacheError:
        return None
    path = renders.crop_dir(head) / f"{name}.jpg"
    return path if path.is_file() else None


def render_finished(join: dict, output: Path, colormaps: Path | None = None) -> None:
    """Render one finished unit through its own recipe, into `output`.

    Written to a temporary and renamed, so a killed build leaves no half-written
    picture for the resume to mistake for a finished one.
    """
    from fractal_wallpapers.models import renders
    from fractal_wallpapers.paths import writing_path

    scratch = writing_path(output)
    spec = renders.spec_of(join, scratch)
    if colormaps is not None:
        spec["colormap_dir"] = str(colormaps)
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch.unlink(missing_ok=True)
    engine.run("render", spec)
    scratch.replace(output)


def score_pictures(head: str, pictures: list[Path]) -> tuple[list, int]:
    """Every picture through the shipped judge. Unconditional cutpoints.

    Returns the probabilities and **the checkpoint's own class count**, which is
    what decides how far a decode can reach. The store is cast on
    [`finished.SCALE`] and is wider than one of these heads; a suggestion is a
    fact about the model and may never be stretched to the scale of the page.
    """
    from fractal_wallpapers.models import finished_scoring, scoring, ship, train

    model, config, where = finished_scoring.load(ship.shipped_path(head), "auto")
    classes = int(config["classes"])
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 32}
    )
    return probabilities, classes


def finished_source(
    head: str,
    seed: int = 0,
    resolution=LABEL_RESOLUTION,
    supersample: int = LABEL_SUPERSAMPLE,
    renderer=None,
    scores=None,
    reuse_cache: bool = False,
) -> Source:
    """The source that asks whether a finished picture is worth keeping.

    A unit names a place, a mode and a maxiter. It may also name the map it is to
    be rendered through; where it does not, the palette head picks one out of a
    seeded neighbourhood of the shipped pool, which is what a release run does.

    ## A revision sheet re-serves pictures the store already holds

    Three things a unit may carry exist for that sheet and no other. A **recipe**
    re-serves the picture a stored row was judged as, knob for knob, so the
    verdict cast on this page keys on the same render and lands as a revision of
    that row rather than beside it. A **suggestion** prefills the incumbent
    verdict — which on a re-judging pass is the stored label and not this head's
    decode, and is the only prefill that can name a tier the checkpoint cannot
    reach. And `reuse_cache` takes the picture off the render cache when the
    cache already holds this exact spec, which is most of a revision sheet.
    """
    from fractal_wallpapers.supply.partitions import partition_of_family

    head = finished.head_of(head)
    render = render_finished if renderer is None else renderer
    picked: dict = {"colorizer": None, "anchors": None, "cyclic": None}
    notes: dict = {"reused_from_cache": 0, "rendered": 0}

    def _map_for(unit: dict, index: int, directory: Path) -> tuple[str, bool]:
        """The map this unit is rendered through, and whether it is mirrored."""
        from fractal_wallpapers.curation import colorize
        from fractal_wallpapers.models import palette_sets

        if picked["cyclic"] is None:
            picked["cyclic"] = palette_sets.cyclic()
        name, mirror = unit.get("colormap"), unit.get("mirror")
        if name is None:
            if picked["colorizer"] is None:
                pool = colorize.pool()
                picked["colorizer"] = colorize.Colorizer(directory / "picks", seed=seed)
                picked["anchors"] = colorize.anchors(pool, unit["_of"], seed)
            candidates = colorize.candidate_set(picked["anchors"][index], picked["colorizer"].pool)
            name, _ = picked["colorizer"].pick_palette(
                {
                    "family": unit["family"],
                    "viewport": unit["viewport"],
                    "maxiter": unit["maxiter"],
                },
                candidates,
            )
        if mirror is None:
            mirror = name not in picked["cyclic"]
        return colormap(name), bool(mirror)

    def cut(unit: dict, directory: Path, name: str) -> dict:
        from fractal_wallpapers.curation import colorize

        if unit.get("recipe") is None:
            map_name, mirror = _map_for(unit, unit["_index"], directory)
            recipe_ = finished.recipe(mirror=mirror)
        else:
            # A unit that states its recipe states its map too: a recipe was
            # recorded against one gradient, and re-picking the map under it
            # would keep every knob and change the picture.
            if unit.get("colormap") is None:
                raise SheetError(
                    "a plan unit states a recipe and no colormap. The recipe was recorded "
                    "against one map; picking another under it is a different picture."
                )
            recipe_ = stated_recipe(unit["recipe"])
            map_name, mirror = colormap(unit["colormap"]), recipe_["mirror"]
        # The whole join, in the shape the finished store's own reader keys on, so
        # a verdict cast on this page is ingested without anything being rebuilt.
        # The recipe comes from `finished.recipe`, which is the one owner of that
        # object — the render cache hands the same one to the engine verbatim.
        join = {
            "family": unit["family"],
            "viewport": unit["viewport"],
            "mode": unit["mode"],
            "mode_params": unit.get("mode_params") or {},
            "curve": unit.get("curve") or colorize.CURVE,
            "colormap": map_name,
            "recipe": recipe_,
            "render": {
                "resolution": list(resolution),
                "supersample": supersample,
                "maxiter": int(unit["maxiter"]),
                "filter": LABEL_FILTER,
            },
            "partition": partition_of_family(unit["family"]),
        }
        picture = directory / "full" / f"{name}.jpg"
        leveled = unit.get("leveled")
        if not picture.is_file() and reuse_cache and leveled is None:
            held = cached_picture(head, join)
            if held is not None:
                picture.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(held, picture)
                notes["reused_from_cache"] += 1
        if not picture.is_file():
            render(join, picture, Path(leveled) if leveled else None)
            notes["rendered"] += 1
        facts = [
            f"{join['partition']} · {family_line(unit['family'])}",
            viewport_line(unit["viewport"], unit["maxiter"]),
            f"{unit['mode']} · {map_name}" + (" · mirrored" if mirror else ""),
        ]
        facts.extend(str(line) for line in (unit.get("facts") or []))
        return {
            "join": join,
            "section": unit.get("section") or "",
            "pictures": [{"caption": f"{unit['mode']} · {map_name}", "path": f"full/{name}.jpg"}],
            "thumb": f"thumb/{name}.jpg",
            "facts": facts,
            "_picture": picture,
            "_thumb": directory / "thumb" / f"{name}.jpg",
        }

    def suggest(rows: list[dict], units: list[dict], log) -> str:
        pictures = [row.pop("_picture") for row in rows]
        thumbs = [row.pop("_thumb") for row in rows]
        for picture, thumb in zip(pictures, thumbs, strict=True):
            thumbnail(picture, thumb)
        incumbent = [unit.get("suggestion") for unit in units]
        if any(value is not None for value in incumbent) and not all(
            value is not None for value in incumbent
        ):
            raise SheetError(
                "some plan units state a suggestion and some leave it to the head. A page "
                "whose prefills mean an incumbent verdict on one row and a decode on the next "
                "cannot be read back as either, so a sheet states all of them or none."
            )
        if scores is None:
            log(f"scoring {len(pictures)} pictures through the shipped {head}")
            probabilities, classes = score_pictures(head, pictures)
        else:
            probabilities, classes = scores
        for row, probability, stated in zip(rows, probabilities, incumbent, strict=True):
            row["columns"] = {
                f"p_ge{index + 2}": float(value) for index, value in enumerate(probability)
            }
            # The score orders the page whoever prefilled it: a revision sheet is
            # still worth most read good→bad by the judge the labels train.
            row["suggestion_score"] = float(sum(probability))
            if stated is None:
                # The decode reaches as far as the CHECKPOINT can, never as far as
                # the page can: this head emits `classes - 1` cutpoints and a tier
                # above them is one it has no opinion about.
                row["suggestion"] = min(
                    classes, 1 + sum(1 for value in probability if value >= 0.5)
                )
            elif stated not in finished.tiers(head):
                raise SheetError(
                    f"a plan unit states suggestion {stated!r}, which is not one of "
                    f"{finished.tiers(head)}"
                )
            else:
                row["suggestion"] = int(stated)
        return head

    def order(rows: list[dict], seed_: int) -> tuple[list[int], str]:
        """Sections in the order the plan introduced them, each good→bad inside."""
        del seed_
        sections: list[str] = []
        for row in rows:
            if row["section"] not in sections:
                sections.append(row["section"])
        indices = sorted(
            range(len(rows)),
            key=lambda i: (sections.index(rows[i]["section"]), -rows[i]["suggestion_score"], i),
        )
        return indices, "score" if len(sections) == 1 else "sections"

    return Source(
        kind="finished_render",
        head=head,
        cut=cut,
        suggest=suggest,
        order=order,
        tiers=finished.tiers(head),
        rubric=FINISHED_RUBRIC[head],
        render_record={
            "resolution": list(resolution),
            "supersample": supersample,
            "filter": LABEL_FILTER,
        },
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# The populations.
# --------------------------------------------------------------------------- #
def units_from_ledger(path: Path, admitted_only: bool = False) -> list[dict]:
    """Sheet units from a walk ledger — the material a run actually found.

    Read through the supply engine's ledger reader, so "what a walk found" has
    one definition and a sheet cannot be cut from a population the census does
    not agree exists. What is passed in is the *predicate*, so the schema check,
    the row-kind filter and the reader stay shared.

    **The default population is everything the structural gates let through**,
    which is not the same as everything the supply engine admits. Admission also
    requires a score above the keeper floor, and no scorer in this repository
    produces one yet — so admitted material is empty today, and the survivors are
    exactly the population the first labels have to be collected from. Once a
    head exists, `admitted_only` cuts the sheet to what it kept.
    """
    from fractal_wallpapers.supply import ledgers

    predicate = ledgers.is_admitted if admitted_only else ledgers.passes_gates
    rows = ledgers.admitted(Path(path), admit=predicate)
    return [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": row.get("maxiter"),
            "score": row.get("score"),
        }
        for row in rows
    ]


def units_from_batch(batch: str) -> list[dict]:
    """Sheet units from a batch already in the store — the material to re-judge.

    Routed through the canonical reader, so a location whose verdict has already
    been revised is served at its current verdict and not at its first one.
    """
    resolution = store.resolved([store.batch_path(batch)])
    return [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": (row.get("render") or {}).get("maxiter"),
            "score": None,
        }
        for _key, row in sorted(resolution.current.items())
    ]


def units_from_plan(path: Path) -> list[dict]:
    """Sheet units from a written plan — the population somebody selected.

    A finished-render sheet's population is a decision (which modes, which band,
    how many of each) and this generator does not make it: a plan is a JSONL file
    of units, one per line, and the selection that produced it is the caller's and
    is recorded in the batch's registration. Every unit names its place, its mode
    and its iteration cap; a `section` groups it on the page and a `colormap`
    fixes its map where the plan already decided one.
    """
    path = Path(path)
    if not path.is_file():
        raise SheetError(f"{path} does not exist; a finished-render sheet is cut from a plan")
    units = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        unit = json.loads(line)
        missing = [key for key in ("family", "viewport", "mode", "maxiter") if key not in unit]
        if missing:
            raise SheetError(
                f"{path}:{number}: a plan unit names no {', '.join(missing)}. A finished render "
                f"is a place AND how it was colored, and a unit short of either is a picture "
                f"nobody can rebuild."
            )
        units.append(unit)
    if not units:
        raise SheetError(f"{path} holds no units")
    return units


# --------------------------------------------------------------------------- #
# The cut.
# --------------------------------------------------------------------------- #
def build(
    source: Source,
    units: list[dict],
    directory: Path,
    batch: str,
    seed: int = 0,
    title: str = "",
    log=print,
) -> Sheet:
    """Build a sheet into `directory`. Returns what was written."""
    if not units:
        raise SheetError("no units: there is nothing to judge")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    rows = []
    for index, unit in enumerate(units):
        # `_index` and `_of` are how a source that draws per-unit resources — a
        # seeded palette neighbourhood — knows where in the cut it is. They are
        # read by `cut` and never reach a row.
        row = source.cut({**unit, "_index": index, "_of": len(units)}, directory, f"{index:04d}")
        # A REVISION sheet re-serves rows from several batches at once, and a row
        # revised under somebody else's batch is a row whose registration — train
        # or eval, anchored or not — silently changed under it. So a unit may
        # carry its own, and the sheet's `batch` is what a unit that names none
        # falls back to.
        row["_batch"] = unit.get("batch") or batch
        if not row["_batch"]:
            raise SheetError(
                f"unit {index} names no batch and the sheet names none either; every row "
                f"lands in a registered batch or its population is unanswerable"
            )
        rows.append(row)
        if (index + 1) % 10 == 0 or index + 1 == len(units):
            log(f"cut {index + 1}/{len(units)}")

    scorer = source.suggest(rows, units, log)
    indices, order_mode = source.order(rows, seed)
    ordered = [rows[index] for index in indices]

    sections: dict[str, int] = {}
    written = []
    for position, row in enumerate(ordered, start=1):
        # The id is assigned AFTER the order is fixed, so it encodes the page
        # position and nothing else — not the draw, not the score, not the fate.
        section = row.get("section") or ""
        sections[section] = sections.get(section, 0) + 1
        written.append(
            {
                "schema": SCHEMA,
                "unit": f"u{position:04d}",
                "batch": row.pop("_batch"),
                "section": section,
                "join": row["join"],
                "pictures": row["pictures"],
                "thumb": row["thumb"],
                "facts": row["facts"],
                "suggestion": row["suggestion"],
                "suggestion_score": row["suggestion_score"],
                "columns": row.get("columns") or {},
            }
        )

    manifest = {
        "schema": SCHEMA,
        "kind": source.kind,
        "head": source.head,
        "batch": batch,
        "batches": dict(sorted(Counter(row["batch"] for row in written).items())),
        "title": title or f"{source.head} · {batch}",
        "seed": seed,
        "order": order_mode,
        "scorer": scorer,
        # Who prefilled the suggestions, because it decides what they MEAN. A
        # head's decode read back as agreement is a measurement; an incumbent
        # verdict read back as agreement is the labeler agreeing with himself.
        "suggested_by": (
            "plan" if any(unit.get("suggestion") is not None for unit in units) else scorer
        ),
        "units": len(written),
        "tiers": list(source.tiers),
        "rubric": source.rubric,
        "sections": {name: count for name, count in sections.items() if name},
        "suggested_tiers": _histogram(written),
        "render": source.render_record,
        "built_at": store.now(),
    }
    if source.notes:
        manifest["cut"] = dict(source.notes)
    (directory / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with (directory / ROWS_NAME).open("w", encoding="utf-8", newline="\n") as handle:
        for row in written:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return Sheet(directory=directory, manifest=manifest, rows=written)


def _histogram(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        if row["suggestion"] is not None:
            out[str(row["suggestion"])] = out.get(str(row["suggestion"]), 0) + 1
    return dict(sorted(out.items()))


def read(directory: Path) -> Sheet:
    """Read a built sheet back."""
    directory = Path(directory)
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise SheetError(f"{directory} holds no {MANIFEST_NAME}; it is not a sheet")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    with (directory / ROWS_NAME).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise SheetError(f"{directory / ROWS_NAME}:{number}: schema {row.get('schema')!r}")
            rows.append(row)
    return Sheet(directory=directory, manifest=manifest, rows=rows)


__all__ = [
    "CANONICAL_COLORMAP",
    "FINISHED_RUBRIC",
    "LABEL_FILTER",
    "LABEL_RESOLUTION",
    "LABEL_SUPERSAMPLE",
    "LOCATION_HEAD",
    "LOCATION_RUBRIC",
    "MANIFEST_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SHEET_RESOLUTION",
    "SHEET_SUPERSAMPLE",
    "THUMB_QUALITY",
    "THUMB_WIDTH",
    "VIVID_COLORMAP",
    "Sheet",
    "SheetError",
    "Source",
    "build",
    "colormap",
    "family_line",
    "finished_source",
    "location_source",
    "read",
    "render_finished",
    "render_pair",
    "render_spec",
    "score_pictures",
    "thumbnail",
    "units_from_batch",
    "units_from_ledger",
    "units_from_plan",
    "viewport_line",
]
