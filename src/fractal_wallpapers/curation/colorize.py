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
mode the engine knows. The roster is read out of the engine's own catalog at call
time, so a mode cannot exist on one side of the boundary and not the other, and
the draw is seeded per attempt and recorded.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers import engine
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


def modes_for(head: str) -> list[str]:
    """The modes one judge owns, read out of the engine's catalog at call time."""
    names = [mode["name"] for mode in engine.modes()]
    if head == budget_module.SMOOTH:
        return [SMOOTH_MODE]
    return [name for name in names if name != SMOOTH_MODE]


def kind_of(mode: str) -> str:
    """A mode's coloring kind — `field`, `composite` or `direct`."""
    from fractal_wallpapers.models import renders

    known = renders.catalog()
    if mode not in known:
        raise ColorizeError(f"the engine has no mode named {mode!r}")
    return known[mode]["kind"]


def pool() -> list[str]:
    """The maps a colorize may choose between: the shipped pool, as this repo holds it."""
    from fractal_wallpapers.models import palette_sets

    held = {path.stem for path in _colormap_dir().glob("*.json")}
    members = [name for name in palette_sets.pool()["pool"] if name in held]
    if len(members) < CANDIDATES:
        raise ColorizeError(
            f"the palette pool holds {len(members)} maps this repository has, and a candidate "
            f"set needs {CANDIDATES}. Bring the pool's maps across before a colorize."
        )
    return members


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
# The field, dumped once per location.
# --------------------------------------------------------------------------- #
def field_of(row: dict, directory: Path) -> Path:
    """The location's smooth field at candidate geometry, dumped once and reused.

    The one iteration pass an attempt pays for. Every candidate map is a recolor
    of this, which is what makes a thirty-two-wide set cost about as much as one
    render instead of thirty-two.
    """
    from fractal_wallpapers.models import renders

    name = renders.job_name(
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "mode": SMOOTH_MODE,
            "mode_params": {},
            "curve": CURVE,
            "colormap": "_field",
            "recipe": _plain_recipe(False),
            "render": _geometry(row),
        }
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.f32"
    if path.is_file() and path.with_suffix(".json").is_file():
        return path
    engine.dump_field(
        {
            "schema": 1,
            "family": row["family"],
            "viewport": row["viewport"],
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": int(row["maxiter"]),
            "mode": SMOOTH_MODE,
            "colormap": "twilight_shifted",
            "colormap_dir": str(_colormap_dir()),
            "output": str(path),
        }
    )
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


def recolored(field: Path, colormap: str, mirror: bool, output: Path) -> Path:
    """One candidate picture: the dumped field through one map, no re-iteration."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.is_file():
        engine.recolor(
            {
                "schema": 1,
                "field": str(field),
                "colormap": colormap,
                "colormap_dir": str(_colormap_dir()),
                "palette": _plain_recipe(mirror),
                "output": str(output),
            }
        )
    return output


# --------------------------------------------------------------------------- #
# The render, and the operator on it.
# --------------------------------------------------------------------------- #
def render_row(row: dict, mode: str, colormap: str, cyclic: set[str], render: dict | None = None):
    """One candidate as the render-cache row its picture is made from."""
    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": mode,
        "mode_params": {},
        "curve": CURVE,
        "colormap": colormap,
        "recipe": _plain_recipe(colormap not in cyclic),
        "render": render or _geometry(row),
    }


def render(
    row: dict,
    mode: str,
    colormap: str,
    cyclic: set[str],
    output: Path,
    render_geometry: dict | None = None,
    level: bool = True,
    band: dict | None = None,
) -> tuple[Path, dict | None]:
    """Render one candidate and level it. `(picture, stamp)`; the stamp may be `None`.

    THE one place a curation picture is made, so "every palette-mapped render is
    stamped" is true by construction rather than by four remembered edits. The
    direct-trap family is excluded here, where the kind is known, and not by a
    test inside the operator.
    """
    from fractal_wallpapers.models import renders

    recipe = render_row(row, mode, colormap, cyclic, render_geometry)
    spec = renders.spec_of(recipe, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    engine.run("render", spec)
    if not level or not autolevel.applies_to(kind_of(mode)):
        return output, None

    entry = json.loads((_colormap_dir() / f"{colormap}.json").read_text(encoding="utf-8"))
    mirror = bool(recipe["recipe"]["mirror"])

    def rerender(stops):
        directory = output.parent / f"{output.stem}.leveled"
        autolevel.overriding_colormap(colormap, stops, entry.get("kind"), directory)
        engine.run("render", {**spec, "colormap_dir": str(directory)})
        return output

    leveled = autolevel.maybe_level(
        output, {"name": colormap, "stops": entry["stops"], "mirror": mirror}, rerender, band
    )
    return leveled.image, leveled.stamp


# --------------------------------------------------------------------------- #
# The attempt.
# --------------------------------------------------------------------------- #
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
        self.pool = pool()
        self.cyclic = _cyclic()
        self.band = _band()
        self.palette, self.palette_config, self.where = palette_scoring.load(
            ship.shipped_path("palette"), device
        )
        self.palette_transform = palette_head.Transform(train=False)
        self.judges = {}
        self.device = device

    def judge(self, head: str):
        """One finished-render judge, loaded on first use and kept."""
        from fractal_wallpapers.models import finished_scoring, ship

        if head not in self.judges:
            self.judges[head] = finished_scoring.load(ship.shipped_path(head), self.device)
        return self.judges[head]

    def pick_palette(self, row: dict, names: list[str]) -> tuple[str, list[float]]:
        """Score every candidate map on this location and return the head's choice."""
        from fractal_wallpapers.models import palette_head, palette_teacher

        field = field_of(row, self.directory / "fields")
        pictures = [
            recolored(
                field,
                name,
                name not in self.cyclic,
                self.directory / "candidates" / field.stem / f"{name}.jpg",
            )
            for name in names
        ]
        scores = palette_teacher.scored_with(
            self.palette, pictures, self.palette_transform, self.where, 64
        )
        return names[palette_head.top_pick(scores)], [float(value) for value in scores]

    def score_picture(self, head: str, picture: Path) -> dict:
        """One finished picture through its judge: every cutpoint, unconditional."""
        from fractal_wallpapers.models import scoring, train

        model, config, where = self.judge(head)
        classes = int(config["classes"])
        transform = scoring.transform_of(config)
        probabilities = train.score(model, [picture], transform, where, classes, {"batch_size": 1})
        row = {f"p_ge{index + 2}": float(probabilities[0][index]) for index in range(classes - 1)}
        row["rank_score"] = float(sum(probabilities[0]))
        return row

    def attempt(self, plan: budget_module.Attempt, row: dict, anchor: str, index: int) -> dict:
        """One colorize, end to end, as the durable row it becomes.

        A failure is a recorded row with a reason and **no score**, never a zero:
        a crash and a bad wallpaper must not be the same number.
        """
        draw = random.Random((self.seed, index, plan.key).__str__())
        names = candidate_set(anchor, self.pool)
        mode = draw.choice(modes_for(plan.head))
        record = {
            "schema": intake.SCHEMA,
            "attempt": index,
            "head": plan.head,
            "partition": plan.partition,
            "key": plan.key,
            "rank": plan.rank,
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": row.get("maxiter"),
            "location_score": row.get("score"),
            "ledger": row.get("_ledger"),
            "anchor": anchor,
            "candidates": names,
            "mode": mode,
            "mode_kind": kind_of(mode),
            "curve": CURVE,
            "render": _geometry(row),
        }
        try:
            colormap, scores = self.pick_palette(row, names)
            picture = self.directory / "pictures" / f"{index:04d}.jpg"
            picture, stamp = render(
                row, mode, colormap, self.cyclic, picture, level=True, band=self.band
            )
            verdict = self.score_picture(plan.head, picture)
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


def _cyclic() -> set[str]:
    from fractal_wallpapers.models import palette_sets

    return palette_sets.cyclic()


def _band() -> dict | None:
    from fractal_wallpapers.coloring import band as band_module

    return band_module.load() if autolevel.enabled() else None


def annotate(record: dict) -> dict:
    """The advisory cut's verdict on one candidate, written onto its row.

    Tri-state, and `None` on a failed render for the reason the advisory itself
    is tri-state: a crash has no score to compare and recording it as a failure to
    clear the bar would make the two indistinguishable.
    """
    if record.get("head") is None:
        return record
    advisory = floors.release_advisory(record["head"])
    record["advisory"] = {
        "name": advisory.name,
        "value": advisory.value,
        "head_sha256": advisory.stamp,
        "clears": advisory.annotates(record.get("p_ge3")),
    }
    return record


__all__ = [
    "CANDIDATES",
    "CURVE",
    "RESOLUTION",
    "SMOOTH_MODE",
    "SUPERSAMPLE",
    "Candidate",
    "ColorizeError",
    "Colorizer",
    "anchors",
    "annotate",
    "candidate_set",
    "field_of",
    "kind_of",
    "modes_for",
    "pool",
    "recolored",
    "render",
    "render_row",
]
