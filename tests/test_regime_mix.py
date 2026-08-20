"""One head, three regimes: what a mixed example is, and what the bar refuses.

The claims here are the ones a comment cannot make stick. A regime mix is only
comparable row by row if every regime holds every row; a row's three tiles are
one draw at three geometries rather than three unrelated pictures; the sampler's
mass table still describes the mix after it is tripled; and the bar reads the
median seed of a band rather than its best.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import dataset, regime_acceptance
from fractal_wallpapers.models import tiles as tile_module

pytest.importorskip("numpy")
pytest.importorskip("torch")

CHEAP = tile_module.BUILT_REGIMES[1].tag


def row(identifier: int, score: int = 1, group: int = 0, side: str = pins.TRAIN) -> dict:
    return {
        "location_id": identifier,
        "score": score,
        "side": side,
        "partition": "mandelbrot",
        "group": group,
        "batch": "a_batch",
        "biased": False,
    }


def tiles(identifier: int, where: str, count: int = 4) -> list[dict]:
    return [
        {
            "tile": slot,
            "level": "antialiased",
            "scale": 1.0,
            "shift_frac": 0.0,
            "path": f"{where}/{identifier}/t{slot:02d}.jpg",
        }
        for slot in range(count)
    ]


def test_a_regime_short_of_a_row_is_refused_rather_than_intersected() -> None:
    """A mix whose composition nobody wrote down is not a smaller mix."""
    rows = [row(1), row(2)]
    canonical = {1: tiles(1, "ss2"), 2: tiles(2, "ss2")}
    with pytest.raises(ValueError, match="comparable row by row"):
        dataset.join(rows, canonical, {CHEAP: {1: tiles(1, "ss1")}})


def test_a_regime_with_fewer_slots_is_refused_too() -> None:
    """Same slot count, or the trio a row contributes is not one draw."""
    rows = [row(1)]
    with pytest.raises(ValueError, match="comparable row by row"):
        dataset.join(rows, {1: tiles(1, "ss2")}, {CHEAP: {1: tiles(1, "ss1", count=3)}})


def test_a_rows_three_tiles_are_one_draw_at_three_geometries(tmp_path) -> None:
    """The regimes differ by geometry and by nothing else. If the slot were drawn
    per example the head would be shown three unrelated pictures and asked to
    agree about them, which is a different and much harder question."""
    from PIL import Image

    for where in ("ss2", CHEAP):
        for slot in range(4):
            directory = tmp_path / where / "7"
            directory.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (8, 8), (slot, 0, 0)).save(directory / f"t{slot:02d}.png")

    def drawn(where: str) -> list[dict]:
        return [
            {
                "tile": slot,
                "level": "antialiased",
                "scale": 1.0,
                "shift_frac": 0.0,
                "path": str(tmp_path / where / "7" / f"t{slot:02d}.png"),
            }
            for slot in range(4)
        ]

    joined = dataset.join([row(7)], {7: drawn("ss2")}, {CHEAP: {7: drawn(CHEAP)}})
    examples = dataset.training_set(
        joined, lambda image, draw: image.getpixel((0, 0))[0], seed=0, regimes=("", CHEAP)
    )
    assert len(examples) == 2, "a row is one example per regime"
    for epoch in range(6):
        examples.set_epoch(epoch)
        assert examples[0][0] == examples[1][0], "the two regimes drew different slots"


def test_tripling_the_index_space_leaves_the_sampled_mass_alone() -> None:
    """Every location is repeated the same number of times, so the class by
    source mass table still describes the mix it is written beside."""
    locations = dataset.join(
        [row(index, score=(index % 4) + 1, group=index // 3) for index in range(24)],
        {index: tiles(index, "ss2") for index in range(24)},
    )
    _, one = dataset.sampler(locations, regimes=1)
    draw, three = dataset.sampler(locations, regimes=3)
    assert one["sampled_mass"] == three["sampled_mass"]
    assert three["regimes"] == 3
    assert draw.num_samples == 3 * len(locations)


def test_the_bar_gates_on_four_slices_and_names_them() -> None:
    """Two cheap regimes, each all-family and multibrot3 alone. A mean over
    families would hide the partition the whole retrain is about."""
    bar = regime_acceptance.preregister()
    named = bar["arms"]["consistency"]["slices"]
    assert len(named) == 4
    assert {entry["family"] for entry in named} == {"all", regime_acceptance.WORST_FAMILY}
    assert {entry["regime"] for entry in named} == {
        regime_acceptance.spelled(regime) for regime in tile_module.BUILT_REGIMES[1:]
    }
    assert bar["amendments"] == [], "a bar starts with nothing appended to it"


def test_the_bar_forbids_selecting_on_the_arm_that_gates() -> None:
    """A candidate selected on consistency would be measuring its own selection."""
    bar = regime_acceptance.preregister()
    assert "consistency" in bar["selection"]["never"]


def test_an_arm_reads_the_median_of_the_band_not_its_best() -> None:
    """Picking the best of three is the thing pre-registration exists to stop."""
    lower_is_better = regime_acceptance._median_run(
        {"a": 0.10, "b": 0.20, "c": 0.30}, better=lambda value: value
    )
    higher_is_better = regime_acceptance._median_run(
        {"a": 0.10, "b": 0.20, "c": 0.30}, better=lambda value: -value
    )
    assert lower_is_better == "b" and higher_is_better == "b"


def test_the_staged_seed_is_chosen_on_the_training_side(tmp_path, monkeypatch) -> None:
    """The evaluation side never picks a checkpoint. It is also refused outright
    if a run in the band selected on a different objective — two objectives are
    not one band."""
    for index, loss in enumerate([0.31, 0.27, 0.44]):
        directory = tmp_path / "models" / "location" / f"seed{index}_all_regimes"
        directory.mkdir(parents=True)
        (directory / "metrics.json").write_text(
            json.dumps(
                {
                    "best_epoch": index,
                    "selection_objective": "cutpoint_cross_entropy",
                    "best_selection_objective": -loss,
                }
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(regime_acceptance.train, "repo_root", lambda: tmp_path)
    chosen = regime_acceptance.staged_seed()
    assert chosen["seed"] == "seed1_all_regimes"
    assert chosen["band"]["seed1_all_regimes"]["selection_cutpoint_cross_entropy"] == pytest.approx(
        0.27
    )

    (tmp_path / "models" / "location" / "seed0_all_regimes" / "metrics.json").write_text(
        json.dumps(
            {"best_epoch": 0, "selection_objective": "ap_ge2", "best_selection_objective": 0.9}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not one band"):
        regime_acceptance.staged_seed()


def test_a_regime_round_trips_through_the_name_its_files_carry() -> None:
    for regime in tile_module.BUILT_REGIMES:
        assert tile_module.regime_of(regime.tag or "canonical") == regime
        assert tile_module.regime_of(regime_acceptance.spelled(regime)) == regime
    with pytest.raises(ValueError, match="not a regime"):
        tile_module.regime_of("640x360")


def test_a_score_file_is_per_regime_and_the_canonical_one_keeps_its_name() -> None:
    """Two regimes in one file is a population scored twice with no column
    saying which reading is which."""
    from fractal_wallpapers.models import scoring

    canonical = scoring.scores_path("location", "seed0")
    cheap = scoring.scores_path("location", "seed0", tile_module.BUILT_REGIMES[1])
    assert canonical.name == "scores.jsonl"
    assert cheap.name == "scores_640x360ss1.jsonl"
    assert canonical.parent == cheap.parent


def _score_rows(directory, run, regime, ids, labels, groups, families, probabilities) -> None:
    """A score file of the shape `scoring.run` writes, for the read to consume."""
    from fractal_wallpapers.models import scoring

    path = directory / f"scores{regime.tag}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, identifier in enumerate(ids):
            row = {
                "schema": scoring.SCHEMA,
                "head": "location",
                "run": run,
                "checkpoint": "best",
                "regime": regime_acceptance.spelled(regime),
                "location_id": identifier,
                "score": labels[index],
                "side": "eval",
                "partition": families[index],
                "group": groups[index],
                "batch": "a_batch",
                "p_ge2": probabilities[index][0],
                "p_ge3": probabilities[index][1],
                "p_ge4": probabilities[index][2],
            }
            handle.write(json.dumps(row) + "\n")


def test_the_read_runs_end_to_end_and_gates_on_both_arms(tmp_path, monkeypatch) -> None:
    """A candidate that is the incumbent's equal at the canonical regime and
    keeps its order at the cheap ones passes; the incumbent, whose cheap-regime
    scores are shuffled, is what it is measured against."""
    import random as stdlib_random

    import numpy

    monkeypatch.setattr(regime_acceptance.train, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(regime_acceptance, "DRAWS", 200)

    draw = stdlib_random.Random(0)
    count = 300
    ids = list(range(count))
    families = ["mandelbrot" if index % 4 else regime_acceptance.WORST_FAMILY for index in ids]
    groups = [index // 3 for index in ids]
    labels = [1 + (index % 4) for index in ids]
    truth = [draw.random() for _ in ids]

    def probabilities(values):
        return [[min(0.999, v + 0.2), v, max(0.001, v - 0.2)] for v in values]

    for run in regime_acceptance.INCUMBENT_RUNS:
        directory = tmp_path / "models" / "location" / run
        for regime in tile_module.BUILT_REGIMES:
            # The incumbent keeps its order at the canonical regime and loses a
            # great deal of it anywhere else — the symptom this study exists for.
            noise = 0.0 if regime.tag == "" else 0.35
            values = [min(0.999, max(0.001, v + draw.uniform(-noise, noise))) for v in truth]
            _score_rows(
                directory, run, regime, ids, labels, groups, families, probabilities(values)
            )

    for run in regime_acceptance.CANDIDATE_RUNS:
        directory = tmp_path / "models" / "location" / run
        for regime in tile_module.BUILT_REGIMES:
            values = [min(0.999, max(0.001, v + draw.uniform(-0.01, 0.01))) for v in truth]
            _score_rows(
                directory, run, regime, ids, labels, groups, families, probabilities(values)
            )
        (directory / "metrics.json").write_text(
            json.dumps(
                {
                    "best_epoch": 3,
                    "selection_objective": "cutpoint_cross_entropy",
                    "best_selection_objective": -0.3,
                }
            ),
            encoding="utf-8",
        )

    bar = regime_acceptance.preregister()
    regime_acceptance.prereg_path().parent.mkdir(parents=True, exist_ok=True)
    regime_acceptance.prereg_path().write_text(json.dumps(bar), encoding="utf-8")

    report = regime_acceptance.read()
    assert report["population"]["locations"] == count
    assert set(report["consistency"]["slices"]) == {
        entry["key"] for entry in bar["arms"]["consistency"]["slices"]
    }
    assert report["consistency"]["verdict"] == "PASS"
    assert all(entry["verdict"] == "IMPROVED" for entry in report["consistency"]["slices"].values())
    # The judged seed is the median of the band, never an endpoint chosen for
    # being the best.
    for entry in report["consistency"]["slices"].values():
        ordered = sorted(entry["band"], key=lambda run: -entry["band"][run])
        assert entry["judged_on"] == ordered[1]
    assert report["overall"]["verdict"] in ("PASS", "FAIL")
    assert numpy.isfinite(report["overall"]["against"]["seed0"]["ci"][0])


def test_a_read_refuses_a_quiet_intersection(tmp_path, monkeypatch) -> None:
    """Two heads compared on different rows are not compared."""
    monkeypatch.setattr(regime_acceptance.train, "repo_root", lambda: tmp_path)
    for run in (*regime_acceptance.INCUMBENT_RUNS, *regime_acceptance.CANDIDATE_RUNS):
        ids = list(range(10 if run == regime_acceptance.SHIPPED_RUN else 12))
        for regime in tile_module.BUILT_REGIMES:
            _score_rows(
                tmp_path / "models" / "location" / run,
                run,
                regime,
                ids,
                [1] * len(ids),
                list(range(len(ids))),
                ["mandelbrot"] * len(ids),
                [[0.5, 0.4, 0.3]] * len(ids),
            )
    with pytest.raises(ValueError, match="do not cover the same locations"):
        regime_acceptance.aligned(
            (*regime_acceptance.INCUMBENT_RUNS, *regime_acceptance.CANDIDATE_RUNS),
            tile_module.BUILT_REGIMES,
        )
