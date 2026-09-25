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

**Three doors are swept and not one.** The registry finds its population by
looking for callers of `colorize.render`. A picture's inputs are enumerated in two
other places, and each has cost a wrong picture:

* `locations.spec_of`, which `render --manifest` builds its spec through and which
  never touches `colorize.render` at all. Its module was in `RENDERERS` for a
  *different* door the whole time, so the name being present is what kept the
  second one out of sight. [`LOCATION_DOOR`] is that half.
* **a spec written out as a dict literal and handed straight to the engine**,
  which neither of the first two sweeps can see at all, because such a site calls
  no builder to be caught calling. [`HAND_BUILT`] is that third half, and it is
  keyed by **function and not by module**, for the reason the second one exists:
  `cli.draw_commands` had three doors and one name.

The third sweep is the one this file claimed did not need to exist. Its docstring
said *"There are three such places and not two"*, meaning three **builders**, and
read as a completeness claim over the class. Nineteen sites write a spec out by
hand; two of them are the builders, so the claim was wrong by **seventeen**. What
it should have said is that a caller holding a whole row cannot drop a member of
it — which is true, and says nothing about a caller that never held a row.

**What the third sweep found, 2026-09-15.** A spec that names a `mode` and no
curve takes the **catalog's** transform, which is `log` for `trap_circle` and `de`
and `linear` for the other eighteen modes, while every production render writes
`colorize.CURVE` over it through `engine_spec.coloring_of`. `curation.colorize`
already knew — [`colorize.field_row`]'s docstring says a field dumped by mode name
"would carry the catalogued curve into its record and recolour every
`trap_circle` through a curve nobody rendered" — and three sites dumped by mode
name anyway. Two were defended at the far end by a recolour that stated the curve.
The third, `palette_coverage`, had three readers that did not: the panel was
selected, tiled and contact-sheeted under `log` for the three of its sixteen cells
that are `trap_circle`, and re-reading this machine's 56 dumps under the curve
production actually spends moves **three of the sixteen seats**.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from fractal_wallpapers import engine
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

#: The **drawn** case: a field mode at the candidate path's own curve with the two
#: palette knobs [`curation.depth`]'s `--vary-palette` draw moves. It is a third
#: case and not a narrowing of the authored one because the renderers that can
#: draw it are different: a candidate leg cannot name a curve and now *can* name a
#: palette, so this is the one case that crosses both halves of the registry —
#: `hunt` and `mine` draw it off an intention's `palette` member, the stored
#: renderers off the recipe, and all of them have to agree.
#:
#: It exists because that member is a **new route for `palette` into a picture**,
#: and every previous defect this file records was a renderer with a route it did
#: not spend. `mine.make` dropped `mode_params` for six days under a docstring
#: saying nothing else was altered.
DRAWN_MODE = "smooth"
DRAWN_PALETTE = {"phase": 0.37, "cycles": 2.0}


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
    #: Whether a **candidate leg** can ask for this case at all. A plan carries
    #: `mode_params` and `palette` and does not carry a curve, which is what keeps
    #: the authored case the stored renderers' alone.
    on_a_plan: bool = True


def _intended(recipe) -> dict:
    """What a candidate leg's intention carries to ask for **this** recipe.

    Off the recipe and never off the case, because every draw function here is
    also handed `case.bare` — by the must-differ arm — and a leg that took its
    settings from the case would draw the varied picture for both arms and make
    that guard pass on anything.

    The palette is the **overrides**, which is what an intention holds:
    [`hunt.Maker.palette_for`] lands them on the map's own bake, so a member equal
    to the plain pass is not one the draw moved.
    """
    from fractal_wallpapers.curation import colorize

    plain = _palette(mirror=recipe.colormap not in colorize.cyclic())
    return {
        "mode_params": dict(recipe.mode_params),
        "palette": {
            name: value for name, value in recipe.palette.items() if plain.get(name) != value
        },
    }


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
        on_a_plan=False,
    )


def drawn_case() -> Case:
    """A palette a **draw** moved, over the candidate path's own curve.

    The pass is built the way [`hunt.Maker.palette_for`] builds it — the drawn
    knobs over the map's own bake — rather than spelled out, so a case that
    disagreed with the maker about `mirror` would be a case no candidate leg could
    reproduce and the failure would read as a renderer's.
    """
    from fractal_wallpapers.curation import colorize

    return Case(
        name="drawn",
        recipe=_recipe(
            DRAWN_MODE,
            palette=_palette(mirror="viridis" not in colorize.cyclic(), **DRAWN_PALETTE),
        ),
        bare=_recipe(DRAWN_MODE),
        members=("palette",),
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
        **_intended(recipe),
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
        **_intended(recipe),
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


def _draw_from_a_recipe_file(case, recipe, where: Path) -> Path:
    """`render --recipe FILE`, the door a published record is redrawn through.

    Written as a recipe file and run through the handler, because the file is the
    interface: a published stamp's `recipes.jsonl` is what a clone has, and what
    this guard is asking is whether a picture drawn from that file alone is the
    picture the leg that made it drew. It was measured byte-identical on one seat
    per mode across the published n=1000 record on 2026-09-14; this is what keeps
    it that way when a member is added.
    """
    from fractal_wallpapers.cli import draw_commands

    where.mkdir(parents=True, exist_ok=True)
    key = recipes.key_of(recipe)
    named = where / "recipes.jsonl"
    named.write_text(
        json.dumps({"schema": recipes.SCHEMA, "key": key, "recipe": recipe.record()}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    picture = where / f"{key}.jpg"
    args = argparse.Namespace(recipe=str(named), key=key, out=str(picture))
    assert draw_commands.render_recipe(args) == 0
    return picture


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


def _draw_atlas(case, recipe, where: Path) -> Path:
    """A gallery slot's thumbnail, through the job the atlas builds off a stored recipe.

    At candidate geometry rather than the atlas's own 400x225, for the reason
    `_draw_shrinkage` gives: a renderer compared at a second size is compared at nothing.
    """
    from fractal_wallpapers.curation.atlas import pictures

    picture = where / f"{recipes.key_of(recipe)}.jpg"
    job = pictures.job_of(
        recipe.record(),
        picture,
        recipes.CANDIDATE_REGIME.resolution,
        recipes.CANDIDATE_REGIME.supersample,
    )
    made = pictures.draw(job)
    assert made["made"], made.get("failed")
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


def _needs_the_shipped_judge(case) -> None:
    """Skip a case that reaches a candidate leg on a clone with no judge weights.

    `hunt.Maker.make` scores every picture it draws with the shipped render judge,
    after the picture is on disk. Without torch that call is a `ModuleNotFoundError`
    and `conftest` skips it; **with** torch and no `fetch-weights` it was a
    `FileNotFoundError` and a red — every `models` CI job from its first run to
    2026-09-25, because a runner has torch and never fetches. The pixels under test
    come before the judge, but the leg is the one production runs, so it is skipped
    whole rather than run with the judge stubbed. A case with no plan reaches no
    candidate leg and runs regardless.
    """
    from fractal_wallpapers.curation import floors
    from fractal_wallpapers.models import ship

    weights = ship.shipped_path(floors.SCORING_HEAD)
    if case.on_a_plan and not weights.is_file():
        pytest.skip(f"the shipped judge is not on this machine ({weights.name}); fetch-weights")


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
    # The atlas's gallery thumbnail: a stored row's recipe redrawn whole, so a reader
    # hovering a dot sees the wallpaper the row is and not a near miss of it.
    Renderer("atlas", "curation.atlas.pictures", STORED, _draw_atlas),
    # The CLI door, and the only entry here that is not a leg: `render --recipe`
    # is how a published record's seat is drawn on a machine with no pool, so
    # what it must agree with is every leg at once.
    Renderer("recipe file", "cli.draw_commands", STORED, _draw_from_a_recipe_file),
)


# --------------------------------------------------------------------------- #
# The guard.
# --------------------------------------------------------------------------- #
needs_engine = pytest.mark.skipif(
    not engine.is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


def _digest(picture: Path) -> str:
    """The bytes the encoder wrote, with the explorer link taken back out.

    A release render carries its link in its metadata and no other leg's does, so
    the whole file differed for every recipe a link can spell — the release leg red
    against nine agreeing renderers from `3c41ddd` on, on a box with the judge,
    and unseen in CI, where the candidate legs could not run. Every other byte,
    the compressed image data included, is still compared.
    """
    from fractal_wallpapers.curation import embed_link

    return hashlib.sha256(embed_link.strip(Path(picture).read_bytes())).hexdigest()


#: Renderers a case is **not** asked for, by name, with the reason. A candidate
#: leg that cannot express a member is not dropping it — see the module docstring
#: — and this says which leg and which case rather than leaving the absence to be
#: inferred from a filter.
NOT_ASKED: dict[tuple[str, str], str] = {
    ("drawn", "manufacture"): "a manufacture row names a place, a mode and a map and has no "
    "palette member to carry a draw. It is the one candidate leg the varied draw does not "
    "reach, and `curation.depth` is the leg that draw belongs to.",
}


def renderers_for(case: Case) -> list:
    """Which registry entries are asked to draw one case, and why the rest are not."""
    return [
        renderer
        for renderer in RENDERERS
        if (case.on_a_plan or renderer.takes == STORED)
        and (case.name, renderer.name) not in NOT_ASKED
    ]


@needs_engine
@pytest.mark.slow
@pytest.mark.parametrize(
    "case_of", [varied_case, authored_case, drawn_case], ids=["varied", "authored", "drawn"]
)
def test_every_renderer_draws_the_same_picture_for_one_recipe(case_of, tmp_path) -> None:
    """The whole point of the file. Bytes, over every renderer that can draw it."""
    case = case_of()
    _needs_the_shipped_judge(case)
    asked = renderers_for(case)
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
@pytest.mark.parametrize(
    "case_of", [varied_case, authored_case, drawn_case], ids=["varied", "authored", "drawn"]
)
def test_the_members_each_case_varies_actually_move_the_pixels(case_of, tmp_path) -> None:
    """Without this the file above would pass on a renderer that dropped every member.

    The case's own recipe against the same recipe with the varied members back at
    the candidate path's defaults, drawn through one renderer that can express
    both. Identical bytes here mean the case is testing nothing.
    """
    case = case_of()
    _needs_the_shipped_judge(case)
    draw = _draw_mine if case.on_a_plan else _draw_release
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
def _modules_where(matches) -> set[str]:
    """Every module in the package whose source `matches`, by dotted name.

    Source text and not an import graph, for the reason the sweep exists at all: a
    module is in the class whether or not anything in this process happens to
    import it, and a sweep that only saw what was loaded would go quiet on exactly
    the leg nobody remembered.
    """
    from fractal_wallpapers import curation

    root = Path(inspect.getfile(curation)).parent.parent
    return {
        path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        for path in sorted(root.rglob("*.py"))
        if matches(path.read_text(encoding="utf-8"))
    }


#: The door, as the two things a binding has to resolve to for a call to be one:
#: the module by its importable name, and the attribute on it. Written out because
#: the predicate below resolves a **binding** rather than matching a spelling, and
#: this is what it resolves the binding against.
LOCATIONS_MODULE = "fractal_wallpapers.locations"
LOCATION_DOOR_ATTRIBUTE = "spec_of"


def _dotted(node: ast.expr) -> str | None:
    """`a.b.c` for the expression a call was made through, or None if it is not one.

    Only `Name` and `Attribute`, because only those two can be a resolvable import
    binding. Anything else — a subscript, a call's return, a `getattr` — is a
    module this predicate cannot follow, and it says no rather than guessing.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


def _names_the_location_door(source: str) -> bool:
    """Whether this module calls [`locations.spec_of`], whatever it bound the module to.

    Read with `ast` rather than as text, because in this tree **every** string test
    available is wrong in one direction or the other. `spec_of(` on its own matches
    fifteen modules: `renders.spec_of` and `engine_spec.spec_of` are spelled the
    same and are the *documented normal path*, which the sweep above says in as many
    words. `locations.spec_of(` on its own would go quiet the first time somebody
    aliased the import, and `cli/spiral_commands.py` already aliases it
    (`as locations_module`). And pairing the two — "imports locations" **and**
    "contains `spec_of(`" — is not the conjunction it looks like: five modules
    import `locations` for `maxiter_of` and never go near this door, so the first of
    them to gain a `renders.spec_of(row, output)` line would be sent to declare a
    door it does not use. That is the very failure this file keeps recording, one
    level up: a match on a name rather than on the act.

    The pair was blind in the other direction too, and that half was found by
    running it: `discovery/boundary.py` writes `from fractal_wallpapers import
    engine, locations`, in which the substring `import locations` does not occur at
    all. One more import on one line is all it took, and nothing would have gone red
    to say so.

    So bind first, then match the call against the binding. `import
    fractal_wallpapers.locations [as X]` and `from fractal_wallpapers import
    locations [as X]` put a name on the **module**; `from fractal_wallpapers.locations
    import spec_of [as f]` puts one on the **function**; and a call counts only if it
    goes through one of those. `ast.walk` reaches imports inside a function body,
    which is where `cli/draw_commands.py` writes both of its.

    A **relative** import of the name is taken at its tail: a predicate handed only
    the source cannot resolve `..` to a package. There is one `locations` module in
    this tree, and the two mistakes are not symmetric — guessing wrong costs a
    declaration somebody deletes, where going quiet costs the sweep.

    A file that does not parse raises here rather than reading as unmatched, which
    is the same choice: an unparseable module in the package is a fault, and a
    sweep that swallowed it would report the tree clean.
    """
    # Parsing every module in the package costs 2.0 s against the 0.04 s the
    # sweep above spends on the same population, which is a second of real work
    # bought for one test and squarely what `@pytest.mark.slow` is for. It is
    # avoided rather than paid: a call that resolves to this function needs the
    # identifier written out somewhere in the file — at the call, or in the
    # `import ... as` that renamed it — so a module whose source never spells it
    # cannot be one, and 211 of the package's 226 files are answered without a
    # parse. `tests/README.md`'s *A count is not a cost* refused to share the
    # substring sweep for 35 ms; this is the same trade at fifty times the price.
    if LOCATION_DOOR_ATTRIBUTE not in source:
        return False
    tree = ast.parse(source)
    on_the_module: set[str] = set()
    on_the_function: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == LOCATIONS_MODULE:
                    # No `as` binds the ROOT package, so the call site reads
                    # `fractal_wallpapers.locations.spec_of(` and the dotted name is
                    # what has to match.
                    on_the_module.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            tail = (node.module or "").rsplit(".", 1)[-1]
            relative = node.level > 0
            from_the_package = node.module == "fractal_wallpapers" or (relative and not node.module)
            from_the_module = node.module == LOCATIONS_MODULE or (relative and tail == "locations")
            for alias in node.names:
                if from_the_package and alias.name == "locations":
                    on_the_module.add(alias.asname or alias.name)
                elif from_the_module and alias.name == LOCATION_DOOR_ATTRIBUTE:
                    on_the_function.add(alias.asname or alias.name)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        if isinstance(called, ast.Name) and called.id in on_the_function:
            return True
        if (
            isinstance(called, ast.Attribute)
            and called.attr == LOCATION_DOOR_ATTRIBUTE
            and _dotted(called.value) in on_the_module
        ):
            return True
    return False


#: Call sites of [`colorize.render`] that are **not** renderers of a stored
#: recipe, with the reason each is out. A measurement rig draws a *place* through
#: a mode and a map: it has no recipe key to reproduce and nothing downstream
#: reads its pictures as a candidate's. **Adding a name here is a claim somebody
#: checked**, in `label_fate.SETTINGS_AWARE_SUBTREES`' sense.
EXEMPT: dict[str, str] = {
    "curation.mine": "`mine.bench` prices the render and recolour paths against each other "
    "over a place, a mode and N maps. It stores nothing and names no recipe. `mine.make` "
    "is in the registry above and is the module's renderer.",
    "curation.phase_response": "renders one recipe at several phases over a stated panel "
    "and reads the pixels for what `Palette.phase` moves. A measurement rig in this "
    "table's own sense: it names no recipe key, no row reaches the pool, and levelling "
    "is off throughout, so its pictures are read for their differences and thrown away.",
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
    are the same list travelling to a worker.

    **This sweep covers one of the three doors, and says so.** It used to claim
    "there are three such places and not two" and mean three *builders*, which read
    as a completeness claim over the whole class and was not one: a site that writes
    its spec out as a dict literal calls no builder, so neither this sweep nor
    [`test_every_caller_of_the_location_door_is_declared`] can see it.
    [`test_every_hand_built_engine_spec_is_declared`] is the third, and the claim
    this docstring makes is now bounded to what it checks.

    A caller that goes through `renders.spec_of(row, output)` with a **complete**
    render-cache row — `Recipe.row`'s own output — cannot drop a member of it, which
    is why `models.renders` and `coloring.texture_flat` are not swept here and are
    not exemptions either. `labeling.sheets` was on that list and did not belong on
    it: `render_finished` holds a whole row, and `render_spec` beside it held none
    and wrote its own spec. It is in the third table now. `release.Task` is held to
    one construction site by `test_curation_release.py`.
    """
    calling = _modules_where(lambda source: "colorize.render(" in source)
    known = {renderer.module for renderer in RENDERERS} | set(EXEMPT)
    assert calling <= known, (
        f"{sorted(calling - known)} draw(s) a picture through `colorize.render` and is in "
        f"neither RENDERERS nor EXEMPT. Every path that turns a recipe into a picture is "
        f"held to drawing the same one; a path that does not turn a recipe into a picture "
        f"says so in EXEMPT, with why."
    )
    stale = {name for name in EXEMPT if name not in calling}
    assert not stale, f"{sorted(stale)} is exempted and no longer renders anything"


#: Modules that enumerate a picture's inputs through [`locations.spec_of`], the
#: **third** site, and what holds each one honest.
#:
#: **Membership in `RENDERERS` deliberately does not answer for a name here.** The
#: registry is keyed by module and a module has more than one door:
#: `cli.draw_commands` has been in it since the `recipe file` entry landed, that
#: entry draws through `colorize.render`, and the sweep above has been green on the
#: strength of the name ever since — while `render --manifest`, which never touches
#: `colorize.render` at all, went unswept for as long as it existed. A name that
#: answers for one door is a name that hides the next one, so this table is its own
#: and an entry is written out here or the sweep fails.
LOCATION_DOOR: dict[str, str] = {
    "cli.draw_commands": "`render --location` and `render --manifest`, which go "
    "`locations.read` -> `record` -> `locations.spec_of` -> `engine.render_report` and "
    "never reach `colorize.render`. It is NOT a registry entry drawing the three cases "
    "above and it cannot be one: a location record is a place plus a geometry, so it has "
    "no member for a curve, a palette pass or a mode's settings, and every case here "
    "varies one of those. That is the point rather than a gap — what this door cannot "
    "express it has to REFUSE rather than drop, so its guard is "
    "`locations.refuse_a_picture_this_cannot_draw` — asked at this door and at no "
    "other, since `screen` and `score-locations` read the same rows and draw "
    "nothing — held by `tests/test_locations.py`, in place of byte agreement.",
}


def test_every_caller_of_the_location_door_is_declared() -> None:
    """The second enumeration site gets the same treatment as the first.

    `locations.spec_of` is in the class the sweep above describes: it writes
    resolution, supersample, mode, colormap and maxiter into an engine spec member
    by member, off a record it read, which is a caller rebuilding a picture's
    inputs and naming some of them. It was found the way every instance of this
    defect is found — a manifest row that spelled its coloring flat drew at the
    module's hard-coded defaults, with exit 0 and no warning, because a key outside
    the `render` block was read by nothing and complained about by nothing.

    ## Why the location door is declared rather than registered

    Because it cannot draw the cases the registry compares. A location record is a
    place plus a geometry **by construction** — the absence of `curve`, `palette`
    and `mode_params` is what the shape IS, and `locations.UNCARRIED_RECIPE_MEMBERS`
    is that absence written down — so routing it through `release.task_for` would
    mean inventing those members, which moves the defaults problem up a level and
    changes the bytes of every `--location` render ever taken. A door that cannot
    express a member is held to refusing it, not to agreeing about it, and that is
    a guard in `tests/test_locations.py` rather than a digest here.

    What this sweep is for is the other half: that the door is *known about*. It
    was not, and the reason it was not is that its module was already in `RENDERERS`
    under a different door — so [`LOCATION_DOOR`] is a separate table on purpose.
    """
    calling = _modules_where(_names_the_location_door)
    assert calling <= set(LOCATION_DOOR), (
        f"{sorted(calling - set(LOCATION_DOOR))} build(s) an engine spec through "
        f"`locations.spec_of` and is not declared in LOCATION_DOOR. Naming resolution, "
        f"supersample, mode, colormap and maxiter into a spec one at a time is how every "
        f"defect this file records began; say which cases the door draws, or why it cannot "
        f"draw them and what refuses in their place."
    )
    stale = sorted(name for name in LOCATION_DOOR if name not in calling)
    assert not stale, f"{stale} is declared at the location door and no longer uses it"


def test_a_candidate_leg_is_declared_rather_than_assumed_to_drop_the_curve() -> None:
    """`hunt`, `mine` and `manufacture` take a plan and cannot name a **curve**.

    That is what the candidate path IS — [`colorize.render_row`] spends
    `colorize.CURVE` on every attempt with no way to say otherwise, and a leg that
    set it per attempt would be making pictures through a transform the judges were
    not fitted on. So the authored case is the stored renderers' alone, and this
    pins the reason rather than leaving their absence looking like an oversight.

    **The palette is no longer on that list**, and the change is deliberate rather
    than a drift: [`curation.depth`]'s varied draw puts a `phase` and a `cycles` on
    the intention itself, [`hunt.Maker.palette_for`] is the one derivation that
    turns them into a pass, and both candidate legs draw the `drawn` case above.
    The default is unchanged — an intention with no `palette` spends the plain one —
    so every leg that does not opt in makes exactly the pictures it made before.
    """
    from fractal_wallpapers.curation import colorize, hunt

    plan = colorize.render_row(
        {"family": {}, "viewport": {}, "maxiter": 256}, "smooth", "viridis", set()
    )
    assert plan["curve"] == colorize.CURVE
    assert plan["mode_params"] == {}
    assert plan["recipe"] == _palette(mirror=True)
    assert {renderer.name for renderer in RENDERERS if renderer.takes == CANDIDATE} == {
        "hunt",
        "mine",
        "manufacture",
    }
    # The three intentions are one duck type and the maker reads whichever it is
    # handed, so a member added to one of them and not the others is a leg that
    # silently cannot draw what the other two can.
    from fractal_wallpapers.curation import depth, mine

    for intention in (hunt.Try, mine.Unit, depth.Shot):
        held = {field.name for field in dataclasses.fields(intention)}
        assert {"mode_params", "palette"} <= held, intention.__name__


# --------------------------------------------------------------------------- #
# The third door: a spec written out by hand.
# --------------------------------------------------------------------------- #
#: The two keys that together mean *this literal is an engine spec*. `schema` is
#: written by a site building a whole spec and by no site overriding one member of
#: somebody else's — `{**spec, "colormap_dir": str(where)}` carries no `schema`,
#: and the three of those in this tree are redirections, not enumerations.
#: `colormap_dir` is the key nothing but an engine spec has ever carried.
SPEC_LITERAL_KEYS = frozenset({"schema", "colormap_dir"})


def _hand_built_specs(source: str) -> set[str]:
    """Every function in this module that writes an engine spec out as a literal.

    By **function** and not by module, which is the whole lesson of
    [`LOCATION_DOOR`]: `cli.draw_commands` is one module with three of these in it,
    and a table keyed on the module would have been satisfied by the first and
    blind to the other two — which is exactly how `render --manifest` went unswept
    for as long as it existed.

    Read with `ast`, so a spec assembled inside a `return` or nested in a call
    counts the same as one in a bare assignment.
    """
    tree = ast.parse(source)
    holder: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                holder[line] = node.name
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {
            key.value
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        if keys >= SPEC_LITERAL_KEYS:
            out.add(holder.get(node.lineno, "<module>"))
    return out


#: **Every site that writes an engine spec out by hand, and what keeps it honest.**
#:
#: The class this file is about, reached from the far side: not a caller holding a
#: row and naming some of its members, but a caller holding no row at all and
#: writing the spec itself. Such a site cannot be caught calling a builder, because
#: it calls none — so it is declared here or the sweep fails.
#:
#: **The question asked of each is the CURVE**, because that is the member a
#: hand-built spec drops without looking as though it dropped anything. A spec says
#: `mode` or `coloring` and never both; `mode` alone resolves through the engine's
#: catalog, which puts `Transform::Log` on `trap_circle` and `de` and
#: `Transform::Linear` on the other eighteen, while every production render has
#: `engine_spec.coloring_of` write `colorize.CURVE` over it.
#:
#: A **recolor** spec asks the same question one step later: `engine recolor` takes
#: `spec.transform.unwrap_or(record.transform)`, so a recolor that does not state
#: the curve inherits whatever its field's record says — right when that record was
#: written by the builder, wrong when it was written by a bare mode.
HAND_BUILT: dict[str, str] = {
    "engine_spec.spec_of": "the builder itself. Every other entry here is a site that does "
    "not use it.",
    "locations.spec_of": "the second builder, and [`LOCATION_DOOR`] is its own table. A "
    "location record has no member for a curve, so what this cannot express it refuses "
    "through `locations.refuse_a_picture_this_cannot_draw` rather than dropping.",
    "cli.draw_commands.render_spec": "`render` and `dump-field` from command-line "
    "ARGUMENTS, the one door here with no row behind it at all. It names a bare `mode` "
    "deliberately: this is the explore-one-picture door the article teaches, `--mode "
    "trap_circle` means the mode as the catalog describes it — 'read through a log curve' "
    "is that mode's own catalog line — and there is no stored recipe here whose curve it "
    "could be disagreeing with. `--discrete` takes the `coloring` door instead, an integer "
    "escape count not being a named mode.",
    "cli.draw_commands.recolor": "`recolor` from arguments. States no transform on purpose: "
    "the dumped field's own record is the right default for a door whose whole job is "
    "'colour this field again', and `--transform` is there for a caller who means otherwise.",
    "cli.draw_commands.screen": "a `screen` spec — a coarse occupancy scan over frames. No "
    "coloring, no recipe, no picture anybody keeps.",
    "curation.colorize.recolored": "states no transform, and is right not to: the fields it "
    "reads are [`colorize.field_of`]'s, dumped through `renders.spec_of` off "
    "[`colorize.field_row`], so their records carry the row's OWN curve and inheriting it "
    "is inheriting the builder's answer.",
    "curation.atlas.pictures.render_plate": "the atlas plate: one family's home view in "
    "`smooth` through `atlas_grey`, a backdrop the dots are drawn over. No recipe stands "
    "behind it, and it **states** `linear` rather than inheriting the catalog's.",
    "curation.framing.screen": "a `screen` spec. As `cli.draw_commands.screen`.",
    "curation.manufacture._leveled_recolor": "**states** `colorize.CURVE`, and its docstring "
    "carries why: `manufacture.verify` found the `trap_circle` disagreement here first.",
    "curation.palette_coverage.probe_cell": "**states** `colorize.CURVE`. Three of the "
    "shipped panel's sixteen cells are `trap_circle`.",
    "curation.palette_coverage._make_tile": "states no transform and inherits the record's, "
    "which is correct since `palette_coverage.dump` was routed through "
    "[`colorize.field_row`] on 2026-09-15. It was NOT correct before: the tiles a person "
    "sets the swatch bar by eye against were drawn at `log` for every `trap_circle` cell "
    "while `probe_cell` measured them at `linear`.",
    "curation.palette_coverage.contact_sheet": "as `_make_tile`, and the same fix reached "
    "it. This is the sheet the bar is read off.",
    "discovery.boundary.sample": "a `screen` spec. As `cli.draw_commands.screen`.",
    "discovery.reframing.screen_rungs": "a `screen` spec over a rung ladder.",
    "discovery.viewport_sampler.screen_batch": "a `screen` spec, for both draw schemes.",
    "discovery.walk.expand": "an `expand` spec: nodes, gates and a policy. It carries a "
    "colormap for the engine's own gate renders and names no mode, no curve and no recipe "
    "— there is no picture here a recipe could reproduce, which is why `walk` is in neither "
    "of the other two tables either.",
    "labeling.sheets.render_spec": "a location sheet's two renders. **Cannot** go through "
    "`renders.spec_of`: a unit out of `units_from_ledger` may carry `maxiter` of `None` and "
    "is meant to draw at the engine's own choice, where `spec_of` reads it through `int()`. "
    "It takes the coloring from `engine_spec.coloring_of` instead, so the curve is named "
    "rather than inherited — see [`sheets.SHEET_MODE`].",
    "models.palette_corpus.recolor_spec": "states no transform and inherits the record's. "
    "The field beside it is dumped through `renders.spec_of` in `build`, so the record is "
    "the builder's.",
    "models.tiles.spec": "a `tiles` spec — a mosaic over a manifest of locations. Its "
    "recipe member is the mosaic's, not one picture's.",
    "palettes.strip.draw": "recolors a **ramp this module wrote itself**, and it writes the "
    "record too — `strip.record` pins `transform` to `linear` beside the bytes. It controls "
    "both halves of the inheritance, which is why not stating the curve is safe here and is "
    "the one entry where that is true by construction rather than by the builder.",
}


def test_every_hand_built_engine_spec_is_declared() -> None:
    """The third door, swept the way the first two are.

    A site that writes its spec out as a literal is invisible to both sweeps above
    — it calls no builder to be caught calling — and it is the site most able to
    drop a member, because there is no row in front of it whose absence would show.
    Nineteen are in this tree — seventeen of them not a builder — and not one was
    declared anywhere.

    The population is found by the **shape of the literal** rather than by a name,
    for the reason `_names_the_location_door` gives at length: a name is the thing a
    module has more than one of. `{"schema": ..., "colormap_dir": ...}` is what an
    engine spec is and what nothing else in this tree is.
    """
    from fractal_wallpapers import curation

    root = Path(inspect.getfile(curation)).parent.parent
    found: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        # Package-relative, the way `_modules_where` spells it: `curation.colorize`,
        # `cli.draw_commands`, `locations`. A function is that plus its own name.
        module = path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        found |= {
            f"{module}.{name}" for name in _hand_built_specs(path.read_text(encoding="utf-8"))
        }

    assert found <= set(HAND_BUILT), (
        f"{sorted(found - set(HAND_BUILT))} write(s) an engine spec out as a dict literal "
        f"and is declared nowhere. Such a site names the engine's inputs one at a time with "
        f"no row in front of it, which is how every defect this file records began — and "
        f"the member it drops silently is the CURVE, because a bare `mode` resolves to the "
        f"catalog's transform and production writes `colorize.CURVE` over it. Say what this "
        f"site draws and what keeps its curve honest."
    )
    stale = sorted(name for name in HAND_BUILT if name not in found)
    assert not stale, f"{stale} is declared here and no longer writes a spec by hand"


def test_a_field_dumped_for_the_one_log_mode_records_the_curve_production_draws(tmp_path) -> None:
    """`trap_circle` is the mode the class was invisible on, so it is the pin.

    The engine's catalog reads `trap_circle` through a log curve — its own one-line
    description says so — and every production render of one goes through
    `engine_spec.coloring_of`, which writes [`colorize.CURVE`] over it. A dumped
    field's *binary* does not depend on that: `dump-field` writes the raw scalars
    before any normalization. Its **record** does, and a recolor that states no
    transform takes the record's.

    So the two sites that dump a field for a mode they were handed are pinned to
    recording the curve a render of that row would spend. Both named a bare mode
    until 2026-09-15 and recorded `log`.

    64x36, because what is under test is the record and not the pixels.
    """
    from fractal_wallpapers import engine, engine_spec
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.models import renders

    assert engine_spec.catalog()["trap_circle"]["transform"] == "log", (
        "this guard is pinned on `trap_circle` being the mode whose catalogued curve is not "
        "the one production draws. If the catalog changed, the pin moves with it."
    )
    geometry = {"resolution": [64, 36], "supersample": 1, "maxiter": 400}
    row = {**PLACE, "viewport": FRAME["viewport"], "maxiter": 400}
    output = tmp_path / "field.f32"
    engine.dump_field(
        renders.spec_of(colorize.field_row(row, "trap_circle", colorize.CURVE, geometry), output)
    )
    record = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert record["transform"] == colorize.CURVE, (
        f"a field dumped for `trap_circle` records {record['transform']!r}, so every recolor "
        f"that does not state a transform draws it through a curve no render of that row "
        f"ever spends."
    )
