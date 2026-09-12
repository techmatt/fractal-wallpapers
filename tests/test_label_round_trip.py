"""One seeded pass through the whole vertical: register, cut, judge, resolve, split.

Each piece has its own tests. This one is about the seams between them — that a
sheet's rows are the rows the store ends up holding, that a batch's registration
still governs the split three steps later, and that a second run of the same
seed produces the same holdout. It runs in CI, which is why the renderer is
injected: the seams do not need pixels, and a test that needed a built engine
would be a test that skips itself on the machine it matters on.

The second half is the same claim for a **repeated traversal of a folded map**,
which is its own file's worth of seam because that pair was refused on the
import path until 2026-09-11 while the candidate draw was making it by the
thousand. See [`the repeated traversal`] below.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from fractal_wallpapers.labeling import finished, intake, pins, sheets, store
from fractal_wallpapers.labeling import finished_import as finished_import_module
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import split as split_module
from fractal_wallpapers.models import renders
from fractal_wallpapers.supply import census
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

SEED = 11


def stub(row, canonical, vivid, resolution, supersample):
    del row, resolution, supersample
    for path in (canonical, vivid):
        path.write_bytes(b"")
    return {"maxiter": 500}


def units(count: int, spacing: float = 10.0) -> list[dict]:
    """`count` locations, each far enough from the next to be its own group."""
    return [
        {
            "family": {"kind": "mandelbrot"},
            "viewport": {"center_re": f"{i * spacing}", "center_im": "0.0", "width": "1.0"},
            "maxiter": 500,
        }
        for i in range(count)
    ]


def judge(tmp_path, sheet: sheets.Sheet) -> str:
    """What the page would have saved: a repeating 1-2-3-4 verdict, in the drop."""
    path = tmp_path / "export.json"
    path.write_text(
        json.dumps({row["unit"]: {"score": 1 + index % 4} for index, row in enumerate(sheet.rows)}),
        encoding="utf-8",
    )
    return str(path)


def run(tmp_path, unconditioned: bool) -> tuple:
    store.register(
        registry_module.Registration(
            batch="a_walk",
            method="everything one walk admitted",
            score_unconditioned=unconditioned,
            why="a test",
        )
    )
    known = store.registry()
    sheet = sheets.build(
        sheets.location_source(renderer=stub),
        units(40),
        directory=tmp_path / "sheet",
        batch="a_walk",
        seed=SEED,
        log=lambda _: None,
    )
    # The ONE ingest path, over the location store: same step, same guarantees,
    # same report as a finished-render sheet takes.
    intake.run(sheet=sheet.directory, labels=judge(tmp_path, sheet), labeler="matt", write=True)
    resolution = store.resolved()
    drawn = split_module.derive(
        resolution.scored(), known=known, seed=SEED, share=0.25, pinned=pins.pinned()
    )
    split_module.write(drawn)
    return sheet, resolution, drawn


def test_the_round_trip_lands_every_judged_unit_in_the_store(tmp_path, store_dir) -> None:
    sheet, resolution, _drawn = run(tmp_path, unconditioned=True)
    assert resolution.summary() == {
        "rows": 40,
        "locations": 40,
        "scored": 40,
        "superseded": 0,
        "unkeyed": 0,
    }
    assert {row["viewport"]["center_re"] for row in resolution.scored()} == {
        row["join"]["viewport"]["center_re"] for row in sheet.rows
    }


def test_the_split_lands_a_quarter_of_it_on_the_evaluation_side(tmp_path, store_dir) -> None:
    _sheet, _resolution, drawn = run(tmp_path, unconditioned=True)
    assert len(drawn.eval_rows) == 10
    assert drawn.straddling == []
    assert pins.pinned() == set(drawn.eval_rows)


def test_a_batch_that_was_not_unconditioned_reaches_no_holdout(tmp_path, store_dir) -> None:
    """The registration written before the sheet existed is still what decides the
    split, two steps and one page later."""
    _sheet, _resolution, drawn = run(tmp_path, unconditioned=False)
    assert drawn.eval_rows == {}
    assert drawn.recipe()["locations"]["eval_eligible"] == 0


def test_the_same_seed_draws_the_same_holdout(tmp_path, store_dir) -> None:
    _sheet, resolution, first = run(tmp_path, unconditioned=True)
    second = split_module.derive(resolution.scored(), known=store.registry(), seed=SEED, share=0.25)
    assert set(first.eval_rows) == set(second.eval_rows)


def test_the_supply_census_reads_what_the_rig_recorded(tmp_path, store_dir) -> None:
    """The census does not walk the label directory itself; it reads the store's
    resolution, so a verdict recorded through the rig is currency the same day."""
    run(tmp_path, unconditioned=True)
    stock = census.stock_census(ALL_PARTITIONS, ledger_paths=[])
    assert stock.counts["mandelbrot"] == {1: 10, 2: 10, 3: 10, 4: 10}
    assert stock.currency["mandelbrot"] == 10 + 0.1 * 10


# --------------------------------------------------------------------------- #
# The repeated traversal: one row, end to end, on the arm that was refused.
# --------------------------------------------------------------------------- #
#: A folded map traversed **twice**, which is four passes of the base ramp. The
#: pair `labeling.finished_import.recipe_of` refused until 2026-09-11 while
#: `curation.depth.palette_drawn` and `curation.hunt.recipe_for` were drawing it
#: — 226 such rows stand in the candidate ledger. The refusal was the wrong half:
#: `mirror` writes the opening colour again at 1.0, so the folded table closes and
#: a repeat of it has no junction. `engine/src/colormap.rs`'s
#: `every_folded_map_closes_so_a_repeat_has_no_seam` is that claim over the whole
#: tracked library; these are the claim that a verdict cast on such a picture
#: survives the trip into the store and back out to a renderer.
REPEATED_FOLD = {
    "gamma": 1.0,
    "cycles": 2.0,
    "phase": 0.25,
    "reverse": False,
    "mirror": True,
    "transfer": {"kind": "value"},
    "rolloff": {"kind": "none"},
}

#: A sequential map, so `mirror` is the fold rule's own answer for it rather than
#: a flag the test asserted into place. Named rather than drawn: a map that
#: changed kind under this test would make it pass for the wrong reason.
A_FOLDED_MAP = "cubehelix"

REPEAT_HEAD = "strange_render"


@pytest.fixture
def finished_store(tmp_path, monkeypatch):
    """An empty finished-render store with one registered batch, and the rig on it."""
    directory = tmp_path / "finished"
    monkeypatch.setattr(finished, "store_dir", lambda head: directory / finished.head_of(head))
    finished.register(
        REPEAT_HEAD,
        registry_module.Registration(
            batch="a_repeat_batch",
            method="a matched repeat draw, for a test",
            anchored=True,
            why="a test",
        ),
    )
    return directory


def repeat_renderer(join, output, leveled=None):
    """A renderer that writes a real, tiny picture — the thumbnailer opens it."""
    del join, leveled
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 5), (10, 20, 30)).save(output, "JPEG")


def repeat_unit(index: int, cycles: float) -> dict:
    """One plan unit at a stated recipe — a repeat, or its own unrepeated twin."""
    return {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": f"0.{index}", "center_im": "0.0", "width": "1.0"},
        "mode": "tia",
        "mode_params": {},
        "curve": "linear",
        "maxiter": 500,
        "colormap": A_FOLDED_MAP,
        "recipe": {**REPEATED_FOLD, "cycles": cycles},
    }


def test_the_named_map_is_still_sequential() -> None:
    """The fixture above is only a fold if its map is one, so ask rather than assume."""
    from fractal_wallpapers.curation import colorize

    assert A_FOLDED_MAP not in colorize.cyclic()


def test_a_repeated_fold_is_no_longer_refused_on_the_import_path() -> None:
    """`recipe_of` used to raise on exactly this; it is the source row's shape."""
    recipe = finished_import_module.recipe_of(
        {"gamma": 1.0, "n_cycles": 2, "phase": 0.25}, False, False, None
    )
    assert recipe["mirror"] is True, "a sequential map is folded, which is the map's own kind"
    assert recipe["cycles"] == 2.0
    assert recipe["phase"] == 0.25


def test_a_repeated_fold_round_trips_from_plan_to_store_to_renderer(
    tmp_path, finished_store, monkeypatch
) -> None:
    """The whole trip, on the arm that was refused: a repeat beside its own twin.

    A sheet that renders and sorts and then cannot be ingested is the whole cost
    of a labelling sitting wasted, so this is asserted before a batch is drawn
    rather than after it comes back.
    """
    monkeypatch.setattr(store, "export_dir", lambda: tmp_path / "labels")
    units = [repeat_unit(1, cycles=2.0), repeat_unit(2, cycles=1.0)]
    sheet = sheets.build(
        sheets.finished_source(
            REPEAT_HEAD, renderer=repeat_renderer, scores=([[0.9, 0.2]] * len(units), 3)
        ),
        units,
        directory=tmp_path / "sheet",
        batch="a_repeat_batch",
        log=lambda _: None,
    )
    # The recipe reaches the sheet unrewritten — the fold and the traversal both.
    on_sheet = {row["join"]["recipe"]["cycles"]: row["join"]["recipe"] for row in sheet.rows}
    assert set(on_sheet) == {1.0, 2.0}
    assert all(recipe["mirror"] is True for recipe in on_sheet.values())

    export = tmp_path / "export.json"
    export.write_text(
        json.dumps({row["unit"]: {"score": 4} for row in sheet.rows}), encoding="utf-8"
    )
    report = intake.run(sheet=sheet.directory, labels=export, labeler="matt", write=True)
    assert report["units"]["exported"] == len(units)
    assert report["units"]["not acted on"] == 0

    stored = finished.resolved(REPEAT_HEAD).scored()
    assert len(stored) == len(units)
    assert sorted(row["recipe"]["cycles"] for row in stored) == [1.0, 2.0]
    assert all(row["recipe"]["mirror"] is True for row in stored)
    # Every knob survives, not just the two this test moves: a row whose recipe
    # is topped up with defaults anywhere on the trip names a different picture.
    for row in stored:
        assert row["recipe"] == {**REPEATED_FOLD, "cycles": row["recipe"]["cycles"]}
    # And a verdict on a repeat has a render key, which is what makes it a row
    # the store can hold rather than one the reader counts as unkeyed.
    assert all(finished.render_key(row) is not None for row in stored)

    # The last seam: the trainer's render cache reproduces the picture the verdict
    # was cast on. `plan` is what feeds it and it carries the recipe whole.
    planned = renders.plan(REPEAT_HEAD, seed=SEED)
    assert sorted(job["recipe"]["cycles"] for job in planned) == [1.0, 2.0]
    assert {job["colormap"] for job in planned} == {A_FOLDED_MAP}
    # Two traversals and one are two pictures, so they are two names on disk.
    assert len({job["name"] for job in planned}) == 2
