"""One seeded pass through the whole vertical: register, cut, judge, resolve, split.

Each piece has its own tests. This one is about the seams between them — that a
sheet's rows are the rows the store ends up holding, that a batch's registration
still governs the split three steps later, and that a second run of the same
seed produces the same holdout. It runs in CI, which is why the renderer is
injected: the seams do not need pixels, and a test that needed a built engine
would be a test that skips itself on the machine it matters on.
"""

from __future__ import annotations

import json

from fractal_wallpapers.labeling import intake, pins, sheets, store
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.labeling import split as split_module
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
