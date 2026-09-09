"""Every renderer in this tree draws one recipe the same way, and it is about the bytes.

**The invariant.** A recipe names a picture. Several functions here turn one into
that picture — a hunt's maker, a mine's, a put-back, a backfill, a label
migration's re-expression, a shrinkage re-read, a release task, a manufacture
batch — and they are spellings of **one act**. Two that disagree are two pictures
under one name, and the one on disk is whichever ran last.

**Why it is a registry and not three assertions.** The same defect has now been
found six times, and every time it was a renderer building its engine spec by
naming *some* members of [`recipes.KEYED`] and silently dropping the rest:

* `mine.make` dropped `mode_params` for six days — 10,664 rows drawn bare under a
  varied key, their judge scores read off the wrong file.
* `rerender.render_pair` had it too, and `re_render`'s key guard pinned
  `mode_params={}` so every varied row was refused: protective by accident.
* `solve.render_seats`, `checks.tasks_of`, `run`'s release leg and
  `votes.render_fulls` all passed `mode_params` and dropped **`curve` and
  `palette`**, so an authored-palette row released as the plain picture.
* `shrinkage._render_one` dropped all three *and* re-measured its levelling at
  label geometry, putting a second uncontrolled difference into the one quantity
  that module exists to measure.
* `manufacture`'s render arm dropped `mode_params`.

An assertion that each site passes `mode_params` would have caught one argument
and nothing else — and it did: two guards in `test_curation_release.py` counted
that keyword and were green through all four `curve`/`palette` omissions. So this
renders one recipe every way there is and compares the **bytes**. Whichever member
the next renderer forgets is caught by the same guard, because a difference here
means they do not agree about the picture, whatever the reason.

**Every case has a must-differ arm.** Draw the same recipe with the varied member
dropped and require the picture to change. Without it the whole file would pass on
settings that move no pixels — which is exactly how the original bug survived every
guard the project already had.

**Two recipes, because one cannot carry all three members.** `mode_params` is legal
only on a direct trap ([`engine_spec.coloring_of`] refuses it elsewhere) and `curve`
is not written for one, so no single recipe varies both. [`VARIED`] is a direct trap
carrying settings; [`AUTHORED`] is a field mode carrying a non-default curve and
palette, which is what `label_migration merge` put 3,015 of into the pool.

**What each renderer can express is declared, not assumed.** A candidate leg
(`hunt`, `mine`) takes a plan rather than a stored recipe and *cannot* name a curve
or a palette — that is what "the candidate path" means, not a member it drops. Each
entry says which cases it draws and why, and [`test_every_renderer_in_the_tree_is_in_this_registry`]
holds the registry to the tree, so a renderer added later is either covered or
declared exempt with a reason.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
from pathlib import Path

import pytest

from fractal_wallpapers.curation import recipes

# --------------------------------------------------------------------------- #
# The two recipes, and the arm each must differ from.
# --------------------------------------------------------------------------- #
#: The place and frame every case is drawn at. A real location at a real depth,
#: because a picture with no structure in it is a picture every renderer agrees
#: about for the wrong reason.
PLACE = {"family": {"kind": "mandelbrot"}}
FRAME = {
    "viewport": {
        "center_re": "-0.7612572175676096",
        "center_im": "-0.08419961869150334",
        "width": "0.0001808092935632228",
    },
    "maxiter": 4000,
}

#: The settings the varied case carries. A roster cell — [`curation.depth`]'s own
#: spelling — rather than an invented pair, and the only mode this project has
#: ever varied.
VARIED_MODE = "direct_trap_multiply"
VARIED_SETTINGS = {"opacity": 0.6, "threshold": 0.2}

#: The authored case's mode and its two overrides. `log` against
#: [`colorize.CURVE`]'s `linear` is a different transform over the same field, and
#: the palette moves gamma, cycles, phase and the fold at once — every one of them
#: a knob the candidate path never spends and a row out of the label corpora may.
AUTHORED_MODE = "smooth"
AUTHORED_CURVE = "log"


def _palette(**knobs) -> dict:
    from fractal_wallpapers.labeling import finished

    return finished.recipe(**knobs)


def _recipe(mode: str, *, mode_params=None, curve=None, palette=None) -> recipes.Recipe:
    """One case as a whole [`recipes.Recipe`], at candidate geometry.

    The autolevel member is the **live** stamp for the mode, which is what every
    renderer here derives for itself: `recipes.live_stamp` answers `NO_AUTOLEVEL`
    on a direct trap, where the operator does not apply at all, and the shipped
    band's reduced stamp on a field mode, where it does.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    colormap = "viridis"
    return recipes.Recipe(
        family=PLACE["family"],
        viewport=FRAME["viewport"],
        maxiter=int(FRAME["maxiter"]),
        regime=recipes.CANDIDATE_REGIME,
        mode=mode,
        mode_params=dict(mode_params or {}),
        curve=colorize.CURVE if curve is None else curve,
        colormap=colormap,
        palette=_palette(mirror=colormap not in colorize.cyclic()) if palette is None else palette,
        autolevel=recipes.live_stamp(mode, colorize.band()),
        palette_group=groups_module.group_of(colormap, groups_module.member_groups()),
    )


@dataclasses.dataclass(frozen=True)
class Case:
    """One recipe, the arm it must differ from, and what varying it is about."""

    name: str
    #: What the renderers must agree on.
    recipe: recipes.Recipe
    #: The same recipe with the varied members dropped back to the candidate
    #: path's own defaults. A renderer that ignores the members draws THIS, so a
    #: case whose two arms came out identical would pass on a dropped member.
    bare: recipes.Recipe
    #: The `KEYED` members this case is a test of.
    members: tuple


def varied_case() -> Case:
    return Case(
        name="varied",
        recipe=_recipe(VARIED_MODE, mode_params=VARIED_SETTINGS),
        bare=_recipe(VARIED_MODE),
        members=("mode_params",),
    )


def authored_case() -> Case:
    return Case(
        name="authored",
        recipe=_recipe(
            AUTHORED_MODE,
            curve=AUTHORED_CURVE,
            palette=_palette(gamma=0.55, cycles=2.0, phase=0.3, mirror=True),
        ),
        bare=_recipe(AUTHORED_MODE),
        members=("curve", "palette"),
    )


# --------------------------------------------------------------------------- #
# The registry: one entry a renderer.
# --------------------------------------------------------------------------- #
#: Cases a renderer can be asked to draw. `CANDIDATE` is a leg that takes a plan
#: and spends the candidate path's own curve and palette by definition; `STORED`
#: is one that takes a recipe somebody stored and must reproduce it whole.
CANDIDATE, STORED = "candidate", "stored"


@dataclasses.dataclass(frozen=True)
class Renderer:
    """One way this project turns a recipe into a picture."""

    name: str
    #: Which module it lives in, for the completeness guard below.
    module: str
    #: `CANDIDATE` or `STORED` — which cases it is asked to draw, and why a
    #: candidate leg is not "dropping" the members it cannot express.
    takes: str
    #: `draw(case, recipe, where) -> Path`, the picture it made.
    draw: object
    #: Set where the renderer is expected to REFUSE the authored case rather than
    #: draw it. `render_pair` is the one, deliberately: it serves rows out of the
    #: field cache, which cannot carry an override, so it counts such a row as
    #: failed rather than putting back the plain picture under its name.
    refuses_authored: bool = False


def _draw_hunt(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import hunt

    maker = _maker(hunt, where)
    plan = hunt.Try(
        leg="test",
        location="agreement",
        partition="mandelbrot",
        mode=recipe.mode,
        colormap=recipe.colormap,
        cell="test",
        k=1,
        mode_params=dict(recipe.mode_params),
    )
    return Path(maker.make(plan, PLACE, FRAME, recipe, recipes.key_of(recipe))["picture"])


def _draw_mine(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import hunt, mine

    maker = _maker(hunt, where)
    unit = mine.Unit(
        arm="test",
        location="agreement",
        partition="mandelbrot",
        mode=recipe.mode,
        colormap=recipe.colormap,
        k=1,
        band="test",
        mode_params=dict(recipe.mode_params),
    )
    made = mine.make(maker, unit, PLACE, FRAME, recipes.key_of(recipe), pictures=where / "pictures")
    return Path(made["picture"])


def _draw_put_back(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation.candidate_ledger import rerender

    picture = where / f"{recipes.key_of(recipe)}.jpg"
    report = rerender.render_pair(
        {
            "fields": str(where / "fields"),
            "rows": [
                {"key": recipes.key_of(recipe), "picture": str(picture), "recipe": recipe.record()}
            ],
        }
    )
    if report["failed"]:
        raise RefusedByDesign(report["why"][0])
    return picture


def _draw_backfill(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import backfill, colorize

    picture = where / f"{recipes.key_of(recipe)}.jpg"
    made, _stamp = backfill._rerender(
        {"recipe": recipe.record(), "picture": None}, colorize.band(), picture, colorize.cyclic()
    )
    return Path(made)


def _draw_label_migration(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import label_migration

    key = recipes.key_of(recipe)
    picture = where / f"{key}.jpg"
    rows = label_migration.render_chunk(
        {"rows": [{"key": key, "picture": str(picture), "recipe": recipe.record(), "standing": {}}]}
    )
    assert rows[0]["made"], rows[0]["why"]
    return picture


def _draw_shrinkage(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import shrinkage

    key = recipes.key_of(recipe)
    where.mkdir(parents=True, exist_ok=True)
    made = shrinkage._render_one(
        (
            {"key": key},
            {"recipe": recipe.record()},
            str(where),
            # Candidate geometry rather than this module's own label geometry:
            # what is under test is which members reach the engine, and a
            # renderer compared at a second size would be compared at nothing.
            list(recipes.CANDIDATE_REGIME.resolution),
            int(recipes.CANDIDATE_REGIME.supersample),
            None,
        )
    )
    assert made["picture"], made.get("why")
    return Path(made["picture"])


def _draw_release(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import release

    # **`.jpg` and not the `.png` a release writes.** The container is chosen by
    # the output's extension and is a different axis from the recipe; comparing a
    # PNG against a JPEG would fail on the encoder and say nothing about which
    # members reached the engine.
    picture = where / f"{recipes.key_of(recipe)}.jpg"
    where.mkdir(parents=True, exist_ok=True)
    stored = recipe.record()
    task = release.task_for(
        id=recipes.key_of(recipe),
        row=stored,
        mode=stored["mode"],
        colormap=stored["colormap"],
        mode_params=stored.get("mode_params"),
        curve=stored.get("curve"),
        palette=stored.get("palette"),
        autolevel=None,
        output=picture,
        geometry=recipe.render(),
    )
    result = release.render_task(task)
    assert result.ok, result.error
    return picture


def _draw_manufacture(case, recipe, where: Path) -> Path:
    from fractal_wallpapers.curation import manufacture

    row = {
        "attempt": 1,
        "group": "agreement",
        "target": "blue",
        "family": recipe.family,
        "viewport": recipe.viewport,
        "maxiter": int(recipe.maxiter),
        "mode": recipe.mode,
        "mode_params": dict(recipe.mode_params),
        "colormap": recipe.colormap,
    }
    made = manufacture._build_group(
        (
            [row],
            str(where),
            list(recipes.CANDIDATE_REGIME.resolution),
            int(recipes.CANDIDATE_REGIME.supersample),
        )
    )
    assert made[0]["picture"], made[0].get("error")
    return where / made[0]["picture"]


class RefusedByDesign(RuntimeError):
    """A renderer declining a case it says it cannot serve. Not a failure."""


def _maker(hunt, where: Path):
    """A `hunt.Maker` writing into `where` and nothing else.

    Deliberately not a redirected tier root: the judge, the band and the group
    table all resolve off the real tree, and a fixture that moved `artifacts/`
    under `tmp_path` would be testing the fixture. The ONE accessor that names a
    write target is the one redirected.
    """
    hunt.pictures_dir = lambda _name: where / "pictures"  # noqa: ARG005
    return hunt.Maker("agreement", log=lambda *_a: None, fields=where / "fields")


#: **Every renderer in the tree, and what it can be asked to draw.** Adding one
#: here is how a new renderer gets covered; leaving one out is caught by
#: `test_every_renderer_in_the_tree_is_in_this_registry`.
RENDERERS: tuple[Renderer, ...] = (
    Renderer("hunt", "curation.hunt", CANDIDATE, _draw_hunt),
    Renderer("mine", "curation.mine", CANDIDATE, _draw_mine),
    Renderer("put back", "curation.candidate_ledger.rerender", STORED, _draw_put_back, True),
    Renderer("backfill", "curation.backfill", STORED, _draw_backfill),
    Renderer("label migration", "curation.label_migration", STORED, _draw_label_migration),
    Renderer("shrinkage", "curation.shrinkage", STORED, _draw_shrinkage),
    # One entry for five legs: `solve`, `checks`, `run`, `votes` and `label_fate`
    # all build through `release.task_for` and render through `release.render_task`
    # since 2026-09-08, and `test_curation_release.py` holds them to it.
    Renderer("release", "curation.release", STORED, _draw_release),
    Renderer("manufacture", "curation.manufacture", CANDIDATE, _draw_manufacture),
)


# --------------------------------------------------------------------------- #
# The guard.
# --------------------------------------------------------------------------- #
def engine_is_built() -> bool:
    from fractal_wallpapers import engine

    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


def _digest(picture: Path) -> str:
    return hashlib.sha256(Path(picture).read_bytes()).hexdigest()


@needs_engine
@pytest.mark.slow
@pytest.mark.parametrize("case_of", [varied_case, authored_case], ids=["varied", "authored"])
def test_every_renderer_draws_the_same_picture_for_one_recipe(case_of, tmp_path) -> None:
    """The whole point of the file. Bytes, over every renderer that can draw it."""
    case = case_of()
    asked = [
        renderer for renderer in RENDERERS if case.name == "varied" or renderer.takes == STORED
    ]
    assert len(asked) >= 4, "a case drawn by fewer than four renderers is not a comparison"

    digests: dict = {}
    refused: dict = {}
    for renderer in asked:
        where = tmp_path / case.name / renderer.name.replace(" ", "_")
        try:
            digests[renderer.name] = _digest(renderer.draw(case, case.recipe, where))
        except RefusedByDesign as declined:
            assert renderer.refuses_authored and case.name == "authored", (
                f"{renderer.name} refused a case it does not declare it refuses: {declined}"
            )
            refused[renderer.name] = str(declined)

    expected = {r.name for r in asked if not (r.refuses_authored and case.name == "authored")}
    assert set(digests) == expected, f"{sorted(expected - set(digests))} drew nothing"
    assert len(set(digests.values())) == 1, (
        f"the renderers drew different pictures for the {case.name} recipe "
        f"({', '.join(case.members)}): { {name: value[:12] for name, value in digests.items()} }. "
        f"They are spellings of one act, and something is passed to one of them and not the "
        f"others."
    )


@needs_engine
@pytest.mark.slow
@pytest.mark.parametrize("case_of", [varied_case, authored_case], ids=["varied", "authored"])
def test_the_members_each_case_varies_actually_move_the_pixels(case_of, tmp_path) -> None:
    """Without this the file above would pass on a renderer that dropped every member.

    The case's own recipe against the same recipe with the varied members back at
    the candidate path's defaults, drawn through one renderer that can express
    both. Identical bytes here mean the case is testing nothing.
    """
    case = case_of()
    draw = _draw_release if case.name == "authored" else _draw_mine
    varied = _digest(draw(case, case.recipe, tmp_path / "varied"))
    plain = _digest(draw(case, case.bare, tmp_path / "plain"))
    assert varied != plain, (
        f"{', '.join(case.members)} makes no difference to these pixels, so every guard in "
        f"this file would pass on a renderer that dropped them. Choose a recipe that moves."
    )
    assert recipes.key_of(case.recipe) != recipes.key_of(case.bare), (
        "the two arms digest to one key, so the store could not tell them apart either"
    )


# --------------------------------------------------------------------------- #
# The registry is held to the tree.
# --------------------------------------------------------------------------- #
#: Call sites of [`colorize.render`] that are **not** renderers of a stored
#: recipe, with the reason each is out. A measurement rig draws a *place* through
#: a mode and a map: it has no recipe key to reproduce and nothing downstream
#: reads its pictures as a candidate's. **Adding a name here is a claim somebody
#: checked**, in `label_fate.SETTINGS_AWARE_SUBTREES`' sense.
EXEMPT: dict[str, str] = {
    "curation.mine": "`mine.bench` prices the render and recolour paths against each other "
    "over a place, a mode and N maps. It stores nothing and names no recipe. `mine.make` "
    "is in the registry above and is the module's renderer.",
    "curation.release": "`release.render_task` is the worker the registry drives; the module "
    "has one other call and it is that function.",
    "palettes.mass_sweep": "measures a colour census over (map, mode, place). Its pictures "
    "are read for their shares and thrown away.",
}


def test_every_renderer_in_the_tree_is_in_this_registry() -> None:
    """A renderer added later is covered or declared, and never merely missed.

    The registry above is the guard's population, and a population somebody has to
    remember to add to is a population that goes stale — which is how four
    `curve`/`palette` omissions sat under two green guards. So the tree is swept
    for the one door a curation picture is made by, and every module that calls it
    is either a registered renderer or an entry in [`EXEMPT`] with its reason.

    ## Why this door and not every `engine.run("render", …)` in the tree

    Because the defect has a shape. Every instance of it was a caller **rebuilding**
    a picture's inputs member by member and naming some of them —
    `colorize.render`'s signature, which takes the mode, the map, the settings, the
    curve and the palette as separate arguments, and `release.Task`'s fields, which
    are the same list travelling to a worker. Those two are the only places in this
    project where a picture's inputs are enumerated rather than handed over whole.

    Everything else goes through `renders.spec_of(row, output)` with a **complete**
    render-cache row — `Recipe.row`'s own output — and a caller holding the whole row
    cannot drop a member of it. That is why `models.renders`, `coloring.texture_flat`
    and `labeling.sheets` are not swept here and are not exemptions either: they are
    not in the class. `release.Task` is held to one construction site by
    `test_curation_release.py`, which is this sweep's other half.
    """
    from fractal_wallpapers import curation

    root = Path(inspect.getfile(curation)).parent.parent
    calling = set()
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "colorize.render(" not in source:
            continue
        calling.add(path.relative_to(root).with_suffix("").as_posix().replace("/", "."))
    known = {renderer.module for renderer in RENDERERS} | set(EXEMPT)
    assert calling <= known, (
        f"{sorted(calling - known)} draw(s) a picture through `colorize.render` and is in "
        f"neither RENDERERS nor EXEMPT. Every path that turns a recipe into a picture is "
        f"held to drawing the same one; a path that does not turn a recipe into a picture "
        f"says so in EXEMPT, with why."
    )
    stale = {name for name in EXEMPT if name not in calling}
    assert not stale, f"{sorted(stale)} is exempted and no longer renders anything"


def test_a_candidate_leg_is_declared_rather_than_assumed_to_drop_the_overrides() -> None:
    """`hunt`, `mine` and `manufacture` take a plan and cannot name a curve or a palette.

    That is what the candidate path IS — [`colorize.render_row`] spends
    `colorize.CURVE` and the plain recipe on every attempt, and a leg that set them
    per attempt would be making pictures the judges were not fitted on. So they are
    asked for the varied case only, and this pins the reason rather than leaving
    their absence from the authored case looking like an oversight.
    """
    from fractal_wallpapers.curation import colorize

    plan = colorize.render_row(
        {"family": {}, "viewport": {}, "maxiter": 256}, "smooth", "viridis", set()
    )
    assert plan["curve"] == colorize.CURVE
    assert plan["mode_params"] == {}
    assert {renderer.name for renderer in RENDERERS if renderer.takes == CANDIDATE} == {
        "hunt",
        "mine",
        "manufacture",
    }
