"""That the fine-tier head is fitted on what it claims, and frozen where it says.

Four things this module can get wrong quietly, and one it cannot get wrong at all:

* **The arms.** "Frozen" has two halves — no gradient, and no batch-norm drift —
  and only the first is what a `requires_grad` sweep does. An arm left in
  `train()` adapts through its normalisation whatever its parameters do, and the
  comparison would be between two things nobody named.
* **The split.** Lineages have to go whole or the stopping slice is reading rows
  a hair away from ones it trained on, and the three sittings have to arrive in
  balance or the epoch is chosen on a scale the training side is not on.
* **The recipe.** It claims to be the shipped render judge's, read off that
  artifact's own config. A key that quietly defaulted would make the claim
  unfalsifiable, which is the failure `models/render/README.md`'s mislaunch
  section is about.
* **The pick.** One statistic chooses the epoch inside a run and the run inside
  the band, so nothing is selected on a number nothing was stopped on.

And the one it cannot: this is **not a judge**, and nothing here may become one
by accident — it is off the roster, off `finished.HEADS`, and its weights are
ignored by the same rule every other head's are.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.models import gallery_grade_train as trainer
from fractal_wallpapers.models import roster


def unit(key: str, grade: int, batch: str, place: str, **rest):
    """One training unit, with only the fields the thing under test reads."""
    return trainer.Unit(
        path=f"{key}.jpg",
        score=grade,
        side="",
        batch=batch,
        place=place,
        partition=rest.get("partition", ""),
        mode=rest.get("mode", "smooth"),
        name=key,
        key=key,
        leveled=rest.get("leveled", False),
        seated=rest.get("seated", False),
        label_p_ge3=rest.get("label_p_ge3"),
        label_p_ge4=rest.get("label_p_ge4"),
        candidate_p_ge3=rest.get("candidate_p_ge3"),
        candidate_p_ge4=rest.get("candidate_p_ge4"),
    )


def row_at(re_: float, im: float, width: float) -> dict:
    """A label row far enough from its neighbours to be its own lineage."""
    return {
        "family": {"kind": "mandelbrot"},
        "viewport": {"center_re": str(re_), "center_im": str(im), "width": str(width)},
    }


def corpus(n: int = 120) -> tuple[list, list[dict]]:
    """`n` units on `n` distinct places, cycling the three batches and the scale."""
    batches = ["n1000_0906_1", "n1000_0906_2", "n1000_0906_3"]
    units, rows = [], []
    for index in range(n):
        units.append(
            unit(f"k{index:04d}", 1 + index % 4, batches[index % 3], place=f"p{index:04d}")
        )
        rows.append(row_at(index * 3.0, index * 5.0, 0.1))
    return units, rows


# --------------------------------------------------------------------------- #
# It is not a judge, and cannot become one by accident.
# --------------------------------------------------------------------------- #
def test_this_head_is_not_on_the_roster_and_no_release_carries_it() -> None:
    assert trainer.HEAD not in roster.HEADS
    manifest = json.loads(roster.manifest_path().read_text(encoding="utf-8"))
    assert trainer.HEAD not in manifest["heads"]


def test_the_store_still_refuses_to_be_read_as_a_finished_corpus() -> None:
    """The separation `data/gallery_grade/README.md` asserts, restated from this side.

    A head fitted on this store is exactly the reader most likely to be handed
    to `finished.head_of` by somebody who thinks the two are the same shape.
    """
    from fractal_wallpapers.labeling import finished

    assert trainer.HEAD not in finished.HEADS
    with pytest.raises(finished.FinishedError):
        finished.head_of(trainer.HEAD)


def test_the_four_constants_copied_out_of_render_deploy_still_agree_with_it() -> None:
    """★ The one copy in the trainer, held to its source.

    Everything at that module's top level is stdlib, so a base install can build
    the command line — `render_deploy` reaches `metrics`, which reaches numpy, and
    one constant imported from the wrong module is all it takes to put the models
    extra on the `fetch-weights --check` path. So four values are written down
    rather than imported, and this is what stops the copy drifting in silence.
    """
    from fractal_wallpapers.models import render_deploy

    assert trainer.RANK_COLUMN == render_deploy.RANK_COLUMN
    assert trainer.HIT_TIER == render_deploy.HIT_TIER
    assert trainer.EPOCHS == render_deploy.EPOCHS
    assert trainer.PATIENCE == render_deploy.PATIENCE


def test_the_trainer_imports_without_the_models_extra() -> None:
    """The property `tests/test_base_install.py` proves in a subprocess, asserted
    here as the thing it is about: nothing heavy at this module's top level.

    Read off the source rather than by importing, because every interpreter that
    runs this suite has numpy and would pass an import test regardless.
    """
    import ast

    from fractal_wallpapers.paths import repo_root

    source = (
        repo_root() / "src" / "fractal_wallpapers" / "models" / "gallery_grade_train.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    reached = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            reached.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            reached.add(f"{node.module}.{node.names[0].name}")
    heavy = {name for name in reached if name.split(".")[0] in {"numpy", "torch", "timm", "PIL"}}
    assert not heavy, heavy
    # And the models modules that reach numpy for it.
    assert "fractal_wallpapers.models.metrics" not in reached
    assert "fractal_wallpapers.models.render_deploy" not in reached
    assert "fractal_wallpapers.models.finished_train" not in reached
    assert "fractal_wallpapers.models.train" not in reached


def test_the_weights_are_ignored_by_the_rule_every_other_head_s_are() -> None:
    from fractal_wallpapers.paths import repo_root

    ignored = (repo_root() / ".gitignore").read_text(encoding="utf-8")
    assert "models/**/*.pt" in ignored
    assert trainer.head_dir().is_relative_to(repo_root() / "models")


# --------------------------------------------------------------------------- #
# The arms.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def model():
    """One un-pretrained backbone at this head's shape, built once for the module."""
    pytest.importorskip("timm")
    from fractal_wallpapers.models import head

    return head.build(num_classes=4, backbone=_backbone(), pretrained=False)


def _backbone() -> str:
    from fractal_wallpapers.models import head

    return head.SHIPPED_BACKBONES["render"]


def test_every_arm_names_modules_this_backbone_actually_has(model) -> None:
    """An arm whose prefix matched nothing would silently be the frozen arm."""
    names = {name for name, _ in model.named_parameters()}
    for arm, said in trainer.ARMS.items():
        for prefix in said["unfrozen"]:
            assert any(name == prefix or name.startswith(f"{prefix}.") for name in names), (
                f"arm {arm!r} unfreezes {prefix!r}, which this backbone has no parameter under"
            )


def test_the_three_arms_unfreeze_strictly_more_of_the_net_in_order(model) -> None:
    shares = [trainer.freeze(model, arm)["trainable_parameters"] for arm in trainer.ARMS]
    assert shares == sorted(shares), shares
    assert len(set(shares)) == 3, "two arms train the same parameters, so one of them is free"
    assert trainer.freeze(model, "more")["trainable_share"] == 1.0
    assert trainer.freeze(model, "frozen")["trainable_share"] < 0.01


def test_the_frozen_arm_trains_the_classifier_and_nothing_else(model) -> None:
    trainer.freeze(model, "frozen")
    training = {name for name, p in model.named_parameters() if p.requires_grad}
    assert training == {"classifier.weight", "classifier.bias"}


def test_a_frozen_module_is_put_in_eval_so_its_running_statistics_do_not_move(model) -> None:
    """The half of freezing a `requires_grad` sweep does not do.

    A batch-norm module in training mode updates its running mean and variance
    whatever its affine parameters do, so a trunk left in `train()` adapts to the
    corpus quietly and the arm measures something nobody named.
    """
    trainer.freeze(model, "last_block")
    trainer.set_train_mode(model, "last_block")
    assert not model.conv_stem.training, "the stem is frozen and is still in training mode"
    assert not model.blocks[0].training
    assert model.blocks[4].training
    assert model.conv_head.training
    assert model.classifier.training


def test_the_full_fine_tune_leaves_everything_in_training_mode(model) -> None:
    trainer.freeze(model, "more")
    trainer.set_train_mode(model, "more")
    assert model.conv_stem.training and model.blocks[0].training


def test_an_arm_nobody_declared_is_refused_rather_than_defaulted(model) -> None:
    with pytest.raises(trainer.GradeTrainingError):
        trainer.freeze(model, "half")


# --------------------------------------------------------------------------- #
# The split.
# --------------------------------------------------------------------------- #
def test_a_lineage_never_straddles_the_two_sides() -> None:
    """Two frames a hair apart on one plane are one picture twice.

    Sixty places, each duplicated a millionth of a width away so the pair is one
    lineage — a row-wise deal would put one of each pair on either side and the
    stopping slice would be reading rows it had trained on.
    """
    units, rows = [], []
    for index in range(60):
        for copy in range(2):
            units.append(
                unit(
                    f"k{index}_{copy}",
                    1 + (index + copy) % 4,
                    f"n1000_0906_{1 + index % 3}",
                    place=f"p{index}_{copy}",
                )
            )
            # A shift far below the neighbour tolerance, so the pair is one lineage.
            rows.append(row_at(index * 3.0 + copy * 1e-6, 0.0, 0.1))

    record = trainer.sides_for(units, seed=0, rows=rows)
    from fractal_wallpapers.labeling import groups

    lineage = groups.assign(rows).of_row
    sides: dict = {}
    for group, unit_ in zip(lineage, units, strict=True):
        sides.setdefault(group, set()).add(unit_.side)
    straddling = {group for group, seen in sides.items() if len(seen) > 1}
    assert not straddling, f"{len(straddling)} lineage(s) sit on both sides"
    assert record["sides"]["train"] + record["sides"]["stopping"] == len(units)


def test_the_three_sittings_arrive_in_the_holdout_in_the_proportions_they_hold() -> None:
    """The stratification, which is the one thing this split adds to the shipped one.

    The three sittings disagree at p = 2.6e-05, so a stopping slice over-weighting
    one of them stops on a scale the training side is not on.
    """
    units, rows = corpus(120)
    record = trainer.sides_for(units, seed=0, rows=rows)
    for _batch, share in record["batches"]["stopping_share_by_batch"].items():
        assert abs(share - trainer.HOLDOUT_SHARE) < 0.05, record["batches"]


def test_the_split_is_a_function_of_the_seed_and_the_corpus() -> None:
    units, rows = corpus(90)
    first = trainer.sides_for(units, seed=0, rows=rows)["side_of_row"]
    again = trainer.sides_for(units, seed=0, rows=rows)["side_of_row"]
    assert first == again
    other = trainer.sides_for(units, seed=7, rows=rows)["side_of_row"]
    assert other != first, "the seed moved and the split did not"


def test_a_row_with_no_place_is_refused_rather_than_quietly_held_out() -> None:
    units, rows = corpus(30)
    rows[3] = {"family": None, "viewport": None}
    with pytest.raises(trainer.GradeTrainingError):
        trainer.sides_for(units, seed=0, rows=rows)


def test_a_split_read_onto_a_different_corpus_is_refused() -> None:
    """A band whose runs sat on two splits would compare arms across populations."""
    units, rows = corpus(60)
    document = trainer.sides_for(units, seed=0, rows=rows)
    with pytest.raises(trainer.GradeTrainingError):
        trainer.apply_split(units[:-1], document)

    moved = [unit(f"x{index}", 3, "n1000_0906_1", f"q{index}") for index in range(len(units))]
    with pytest.raises(trainer.GradeTrainingError):
        trainer.apply_split(moved, document)


def test_applying_a_split_puts_every_row_back_where_it_was() -> None:
    units, rows = corpus(60)
    document = trainer.sides_for(units, seed=0, rows=rows)
    for unit_ in units:
        unit_.side = ""
    trainer.apply_split(units, document)
    assert [unit_.side for unit_ in units] == document["side_of_row"]


# --------------------------------------------------------------------------- #
# The recipe, and the claim it makes.
# --------------------------------------------------------------------------- #
def test_the_recipe_is_read_off_the_shipped_artifact_and_not_restated() -> None:
    """A constant that drifted from the artifact would be an uncheckable claim."""
    shipped = {key: object() for key in trainer.CARRIED}
    recipe = trainer.recipe_from(shipped)
    for key in trainer.CARRIED:
        assert recipe[key] is shipped[key]


def test_a_shipped_config_missing_a_carried_key_refuses_rather_than_defaults() -> None:
    shipped = {key: 1 for key in trainer.CARRIED if key != "backbone_lr"}
    with pytest.raises(trainer.GradeTrainingError) as refused:
        trainer.recipe_from(shipped)
    assert "backbone_lr" in str(refused.value)


def test_the_three_moved_keys_each_say_what_they_were_and_why() -> None:
    moved = {change["key"] for change in trainer.INHERITANCE["chosen"]}
    assert moved == {"source_dims", "split_stratification", "split_seed"}
    for change in trainer.INHERITANCE["chosen"]:
        assert change["was"] and change["now"] and len(change["why"]) > 40


def test_the_recipe_says_the_head_is_a_cascade_stage_and_not_a_ranker() -> None:
    recipe = trainer.recipe_from(dict.fromkeys(trainer.CARRIED, 1))
    assert "p_ge4" in recipe["cascade"]
    assert "never a pool-wide ranker" in recipe["cascade"]


def test_the_source_geometry_is_the_candidate_column_the_seating_reads() -> None:
    from fractal_wallpapers.models import head

    recipe = trainer.recipe_from(dict.fromkeys(trainer.CARRIED, 1))
    assert recipe["source_dims"] == [head.SOURCE_WIDTH, head.SOURCE_HEIGHT] == [640, 360]


# --------------------------------------------------------------------------- #
# The stopping rule.
# --------------------------------------------------------------------------- #
def test_the_objective_is_negated_average_precision_at_the_shipped_boundary() -> None:
    import numpy

    from fractal_wallpapers.models import metrics, render_deploy

    labels = numpy.array([1, 2, 3, 4, 3, 2])
    probabilities = numpy.array(
        [[0.9, 0.2, 0.1], [0.9, 0.4, 0.2], [0.9, 0.8, 0.3], [0.9, 0.95, 0.7]]
        + [[0.9, 0.7, 0.2]] * 2
    )
    value, rule = trainer.objective(labels, probabilities)
    expected = metrics.average_precision(
        render_deploy.hits_of(labels), render_deploy.rank_scores(probabilities)
    )
    assert rule == "ap_ge3"
    assert value == pytest.approx(-expected)


def test_the_declared_auc_fallback_is_unreachable_under_this_repository_s_metrics() -> None:
    """★ The fallback cannot fire, and this is the pin that says so out loud.

    The recipe declares AUC(>=3) as the fallback for a stopping slice AP cannot be
    read on. But [`metrics.average_precision`] and [`metrics.auc`] return `None`
    under **exactly** the same condition — one class absent at the boundary — so
    there is no slice where the first is unreadable and the second is not. The
    branch is kept because it is what the recipe declares and because it costs
    nothing; what is asserted here is that it is dead, so the day either metric
    learns to answer on a degenerate slice this test fails and somebody re-reads
    which rule a run actually stopped on.
    """
    import numpy

    from fractal_wallpapers.models import metrics

    for labels in ([3, 4, 3, 4], [1, 2, 1, 2]):
        hits = [1 if grade >= trainer.HIT_TIER else 0 for grade in labels]
        scores = [0.1, 0.4, 0.2, 0.3]
        assert metrics.average_precision(hits, scores) is None
        assert metrics.auc(hits, scores) is None
        probabilities = numpy.array([[0.9, score, 0.0] for score in scores])
        value, rule = trainer.objective(numpy.array(labels), probabilities)
        assert rule == "undefined" and value == float("inf")


# --------------------------------------------------------------------------- #
# The band's pick.
# --------------------------------------------------------------------------- #
def test_the_band_picks_on_the_statistic_the_epoch_was_chosen_on(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    written = {("frozen", 0): -0.80, ("frozen", 1): -0.81, ("more", 0): -0.90, ("more", 1): -0.70}
    for (arm, seed), objective in written.items():
        directory = tmp_path / trainer.run_name(arm, seed)
        directory.mkdir(parents=True)
        (directory / "metrics.json").write_text(
            json.dumps(
                {
                    "run": trainer.run_name(arm, seed),
                    "best_epoch": 3,
                    "best_selection_objective": objective,
                    "best_selection_rule": "ap_ge3",
                    "wall_seconds": 1.0,
                    "freezing": {"trainable_share": 0.5},
                    "held_out": {"rows": 201},
                }
            ),
            encoding="utf-8",
        )
    record = trainer.band(arms=("frozen", "more"), seeds=(0, 1))
    assert record["pick"] == {"arm": "more", "seed": 0, "run": "more_seed0"}
    assert record["arms"]["more"]["best_stopping_ap"] == 0.90
    assert record["arms"]["more"]["spread"] == pytest.approx(0.20)
    assert record["arms"]["frozen"]["mean_stopping_ap"] == pytest.approx(0.805)


def test_a_band_with_nothing_fitted_says_so_rather_than_picking(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    with pytest.raises(trainer.GradeTrainingError):
        trainer.band()


# --------------------------------------------------------------------------- #
# The tracked records this band leaves.
# --------------------------------------------------------------------------- #
def test_a_run_record_carries_no_per_row_array(tmp_path) -> None:
    """`config.json` is tracked, and three thousand entries naming every row would
    be a record nobody reads carried in git forever."""
    for path in sorted(trainer.head_dir().glob("*/config.json")):
        config = json.loads(path.read_text(encoding="utf-8"))
        assert not [key for key in config["split"] if key.endswith("_of_row")], path
    del tmp_path


def test_every_fitted_run_says_its_held_out_number_is_the_stopping_slice() -> None:
    """The one caveat a reader of this band must not lose: the epoch was chosen on
    the very slice the AP is read on, and the store is not eval-eligible."""
    found = sorted(trainer.head_dir().glob("*/metrics.json"))
    for path in found:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert "stopping slice" in record["held_out_is"]
        assert "not eval-eligible" in record["held_out_is"]
