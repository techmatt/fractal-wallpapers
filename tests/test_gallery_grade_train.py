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
def test_the_two_metrics_are_unreadable_under_one_condition_and_it_is_the_same_one() -> None:
    """★ Why there is no fallback branch, kept as a pin after the branch went.

    The first band declared AUC(>=3) as the fallback for a slice AP could not be
    read on. It could never have fired: [`metrics.average_precision`] and
    [`metrics.auc`] return `None` under **exactly** the same condition — one class
    absent at the boundary — so no slice exists where the first fails and the
    second answers. That is what makes [`readable_at`] a single question asked
    once before a fit rather than a branch inside the loop, and the day either
    metric learns to answer on a degenerate slice this test fails and somebody
    re-reads whether the arrangement still holds.
    """
    from fractal_wallpapers.models import metrics

    for labels in ([3, 4, 3, 4], [1, 2, 1, 2]):
        for boundary in (3, 4):
            hits = [1 if grade >= boundary else 0 for grade in labels]
            scores = [0.1, 0.4, 0.2, 0.3]
            unreadable = metrics.average_precision(hits, scores) is None
            assert unreadable == (metrics.auc(hits, scores) is None)
            assert unreadable == (not trainer.readable_at(labels, boundary))


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


# --------------------------------------------------------------------------- #
# The band's own stopping rule, and the branch that is asked once.
# --------------------------------------------------------------------------- #
def test_a_slice_is_readable_at_a_boundary_only_when_it_holds_both_classes() -> None:
    assert trainer.readable_at([1, 2, 3, 4], 4)
    assert trainer.readable_at([3, 4], 4)
    assert not trainer.readable_at([4, 4, 4], 4)
    assert not trainer.readable_at([1, 2, 3], 4)
    assert not trainer.readable_at([], 4)


def test_each_rule_reads_its_own_boundary_off_its_own_column() -> None:
    """★ The correction this band exists for.

    `ap_ge3` ranks by `p_ge3` at the 3 boundary and `auc_ge4` by `p_ge4` at the 4
    boundary. A rule that read one cutpoint and scored another would be two
    questions asked as one, and the first band's whole finding is that the 3
    boundary is not the one a seating inside the gate's own top orders on.
    """
    import numpy

    from fractal_wallpapers.models import metrics

    labels = numpy.array([1, 2, 3, 4, 4, 3, 2, 4])
    # `p_ge3` orders one way and `p_ge4` the reverse, so a rule reading the wrong
    # column cannot accidentally agree with the right one.
    p3 = numpy.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    p4 = 1.0 - p3
    probabilities = numpy.stack([numpy.ones_like(p3), p3, p4], axis=1)

    value, rule = trainer.objective(labels, probabilities, "ap_ge3")
    assert rule == "ap_ge3"
    assert value == pytest.approx(-metrics.average_precision((labels >= 3).astype(int), p3))

    value, rule = trainer.objective(labels, probabilities, "auc_ge4")
    assert rule == "auc_ge4"
    assert value == pytest.approx(-metrics.auc((labels >= 4).astype(int), p4))


def test_a_rule_nobody_declared_is_refused_rather_than_defaulted() -> None:
    import numpy

    with pytest.raises(trainer.GradeTrainingError):
        trainer.objective(numpy.array([3, 4]), numpy.ones((2, 3)), "auc_ge2")


def test_an_unreadable_boundary_raises_here_rather_than_returning_infinity() -> None:
    """The first band's per-epoch fallback is gone and this is what replaced it.

    `readable_at` is asked before the loop, so reaching an unreadable boundary
    inside one is a fault rather than a branch — and a run that silently returned
    infinity every epoch would stop on its patience and call that a choice.
    """
    import numpy

    with pytest.raises(trainer.GradeTrainingError):
        trainer.objective(numpy.array([4, 4, 4]), numpy.full((3, 3), 0.5), "auc_ge4")


# --------------------------------------------------------------------------- #
# Bands.
# --------------------------------------------------------------------------- #
def test_the_first_band_keeps_bare_names_and_every_later_one_prefixes() -> None:
    """Renaming the first band's directories would make every report quoting
    `more_seed1` wrong about a run that still exists.

    The corpus is named on every call here rather than left to the default,
    because this is a test about the BAND axis and the default on the other one
    moves whenever a refit is adopted.
    """
    build = trainer.BUILD_CORPUS
    assert trainer.run_name("more", 1, trainer.FIRST_BAND, build) == "more_seed1"
    assert trainer.run_name("more", 1, "auc_ge4", build) == "auc_ge4_more_seed1"
    assert trainer.band_path(trainer.FIRST_BAND, build).name == "band.json"
    assert trainer.band_path("auc_ge4", build).name == "band_auc_ge4.json"


def test_a_band_nobody_declared_is_refused() -> None:
    with pytest.raises(trainer.GradeTrainingError):
        trainer.run_name("more", 0, "auc_ge2")


def _fitted(tmp_path, values: dict, band: str = "auc_ge4") -> None:
    """Write a `metrics.json` per `(arm, seed)` carrying the given statistics."""
    for (arm, seed), (statistic, spearman) in values.items():
        directory = tmp_path / trainer.run_name(arm, seed, band)  # the default corpus
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "metrics.json").write_text(
            json.dumps(
                {
                    "run": trainer.run_name(arm, seed, band),
                    "band": band,
                    "best_epoch": 3,
                    "best_selection_objective": -statistic,
                    "best_selection_rule": band,
                    "wall_seconds": 1.0,
                    "freezing": {"trainable_share": 0.5},
                    "held_out": {"rows": 201, "auc_ge4": statistic, "spearman": spearman},
                }
            ),
            encoding="utf-8",
        )


def test_the_arm_is_picked_on_the_mean_and_the_seed_on_the_median(tmp_path, monkeypatch) -> None:
    """★ Neither half is the argmax, and both halves matter.

    `more` here has the single best run of the band and the worse mean, so an
    argmax over runs would pick it. And inside the winning arm the median seed is
    not the best one — which is the point: the epoch surface is flat enough that
    the best of three seeds is a coin flip rather than a fact about the arm.
    """
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    monkeypatch.setattr(trainer, "_baselines_or_reason", lambda *_: {"unreadable": "not here"})
    _fitted(
        tmp_path,
        {
            ("last_block", 0): (0.70, 0.4),
            ("last_block", 1): (0.72, 0.4),
            ("last_block", 2): (0.74, 0.4),
            ("more", 0): (0.50, 0.4),
            ("more", 1): (0.60, 0.4),
            ("more", 2): (0.99, 0.4),
        },
    )
    read = trainer.band(seeds=(0, 1, 2))
    assert read["arms"]["last_block"]["mean_selection"] == pytest.approx(0.72)
    assert read["arms"]["more"]["mean_selection"] == pytest.approx(0.6967, abs=1e-4)
    assert read["pick"]["arm"] == "last_block", "the single best RUN is `more`, and it loses"
    assert read["pick"]["seed"] == 1, "the median seed, not the 0.74 one"
    assert read["pick"]["even_count_took_the_lower_middle"] is False


def test_an_even_seed_count_takes_the_lower_middle_and_says_so(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    monkeypatch.setattr(trainer, "_baselines_or_reason", lambda *_: {"unreadable": "not here"})
    _fitted(tmp_path, {("more", 0): (0.60, 0.4), ("more", 1): (0.80, 0.4)})
    read = trainer.band(arms=("more",), seeds=(0, 1))
    assert read["pick"]["seed"] == 0
    assert read["pick"]["even_count_took_the_lower_middle"] is True


# --------------------------------------------------------------------------- #
# The bar.
# --------------------------------------------------------------------------- #
def _bar(tmp_path, band: str = "auc_ge4") -> None:
    (tmp_path / trainer.bar_path(band).name).write_text(
        json.dumps(
            {
                "band": band,
                "registered_at": "2026-09-06T00:00:00Z",
                "gated": {
                    "incumbents": list(trainer.GATED_INCUMBENTS),
                    "statistics": list(trainer.GATED_STATISTICS),
                },
                "incumbents": {
                    "candidate_p_ge4": {"auc_ge4": 0.53, "spearman": 0.09},
                    "rank_key": {"auc_ge4": 0.54, "spearman": 0.14},
                },
            }
        ),
        encoding="utf-8",
    )


def test_a_bar_refuses_to_be_rewritten_after_its_band(tmp_path, monkeypatch) -> None:
    """A bar rewritten after the fact is a bar fitted to what happened, which is
    the whole thing pre-registration is for."""
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    _bar(tmp_path)
    with pytest.raises(trainer.GradeTrainingError):
        trainer.write_bar(log=lambda *_args: None)


def test_the_bar_gates_every_seed_and_one_failing_cell_fails_the_band(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    monkeypatch.setattr(trainer, "_baselines_or_reason", lambda *_: {"unreadable": "not here"})
    _bar(tmp_path)
    _fitted(
        tmp_path,
        {("more", 0): (0.70, 0.30), ("more", 1): (0.71, 0.30), ("more", 2): (0.72, 0.30)},
    )
    _, document = trainer.acceptance(log=lambda *_args: None)
    assert document["verdict"] == "CLEARED"
    # Four cells a seed — two incumbents by two statistics — at three seeds.
    assert len(document["cells"]) == 12
    assert document["worst_margin"] == pytest.approx(0.16, abs=1e-9)

    # One seed slipping under one incumbent on one statistic fails the band.
    _fitted(tmp_path, {("more", 1): (0.71, 0.13)})
    _, document = trainer.acceptance(log=lambda *_args: None)
    assert document["verdict"] == "NOT CLEARED"
    assert [cell["statistic"] for cell in document["failures"]] == ["spearman"]
    assert document["failures"][0]["incumbent"] == "rank_key"


def test_a_bar_stated_over_the_gate_column_reads_the_arm_there_too(tmp_path, monkeypatch) -> None:
    """★ Two populations must never wear one number.

    A row drawn from outside the seating pool carries no candidate reading, so
    neither incumbent exists for it — the correction sitting's `low_anchor`
    hundred are exactly that. Comparing an arm's AUC over the whole stopping
    slice against a column's over the four fifths of it that has the column
    would flatter or punish the arm for a reason that is not the arm.
    """
    monkeypatch.setattr(trainer, "head_dir", lambda run=None: tmp_path / run if run else tmp_path)
    monkeypatch.setattr(trainer, "_baselines_or_reason", lambda *_: {"unreadable": "not here"})
    _bar(tmp_path)
    _fitted(
        tmp_path,
        {("more", 0): (0.70, 0.30), ("more", 1): (0.71, 0.30), ("more", 2): (0.72, 0.30)},
    )
    # The whole slice clears; the slice the incumbents exist on does not.
    for seed in (0, 1, 2):
        path = tmp_path / trainer.run_name("more", seed, "auc_ge4") / "metrics.json"
        said = json.loads(path.read_text(encoding="utf-8"))
        said["held_out_on_the_gate_column"] = {"rows": 330, "auc_ge4": 0.51, "spearman": 0.30}
        path.write_text(json.dumps(said), encoding="utf-8")

    bar = tmp_path / trainer.bar_path("auc_ge4").name
    stated = json.loads(bar.read_text(encoding="utf-8"))
    stated["population"] = {"rows": 350, "slice": "gate_column", "gate_column_rows": 330}
    bar.write_text(json.dumps(stated), encoding="utf-8")

    _, document = trainer.acceptance(log=lambda *_args: None)
    assert document["verdict"] == "NOT CLEARED", "read over the whole slice this would pass"
    assert {cell["read_on"] for cell in document["cells"]} == {"held_out_on_the_gate_column"}
    assert {cell["rows"] for cell in document["cells"]} == {330}

    # A bar over the whole slice reads the whole slice, and the same runs clear.
    stated["population"]["slice"] = "all"
    bar.write_text(json.dumps(stated), encoding="utf-8")
    _, document = trainer.acceptance(log=lambda *_args: None)
    assert document["verdict"] == "CLEARED"
    assert {cell["read_on"] for cell in document["cells"]} == {"held_out"}


def test_the_bar_names_both_incumbents_and_not_the_easier_one() -> None:
    """An arm that beat the judge's column and lost to the shipped key would have
    improved nothing anybody ships — `curation.render_grade` made exactly this
    correction for the render judge, and it is the same correction here."""
    assert set(trainer.GATED_INCUMBENTS) == {"candidate_p_ge4", "rank_key"}
    assert set(trainer.GATED_STATISTICS) == {"auc_ge4", "spearman"}


# --------------------------------------------------------------------------- #
# The corpus: which rows, as against which stopping rule.
# --------------------------------------------------------------------------- #
def test_the_build_corpus_keeps_the_bare_names_and_every_later_one_says_which() -> None:
    """A refit on a grown store must not overwrite what a shipped run refers to.

    The adopted run's own `split` block names `split.json`, so a corpus that
    reused the file would leave a run on disk that nothing could reproduce and
    nothing would look broken.
    """
    # The default is the ADOPTED corpus, which is `corrected` since 2026-09-09 —
    # `score-pool` writes the column a seating orders on, so an unflagged verb
    # must mean the head that is live rather than the newest one fitted. Moving
    # it is an act with a re-score and a bar move in it, never a tidy-up.
    assert trainer.CORPUS in trainer.CORPORA
    assert trainer.CORPUS == "corrected", "adopted 2026-09-09"
    assert trainer.BUILD_CORPUS == "as_built", "the corpus whose files carry bare names"
    assert trainer.run_name("more", 2, "auc_ge4", trainer.BUILD_CORPUS) == "auc_ge4_more_seed2"
    assert trainer.run_name("more", 2, "auc_ge4", "corrected") == "corrected_auc_ge4_more_seed2"
    assert trainer.run_name("more", 1, trainer.FIRST_BAND, "corrected") == "corrected_more_seed1"

    for corpus in sorted(trainer.CORPORA):
        paths = {
            trainer.population_path(corpus),
            trainer.split_path(corpus),
            trainer.band_path("auc_ge4", corpus),
            trainer.bar_path("auc_ge4", corpus),
            trainer.comparison_path("auc_ge4", corpus),
        }
        assert len(paths) == 5
    for name in ("population_path", "split_path", "band_path", "bar_path", "comparison_path"):
        reach = getattr(trainer, name)
        assert reach(corpus=trainer.BUILD_CORPUS) != reach(corpus="corrected"), name

    assert trainer.population_path(trainer.BUILD_CORPUS).name == "population.jsonl"
    assert trainer.split_path(trainer.BUILD_CORPUS).name == "split.json"
    assert trainer.bar_path("auc_ge4", trainer.BUILD_CORPUS).name == "bar_auc_ge4.json"
    assert trainer.bar_path("auc_ge4", "corrected").name == "corrected_bar_auc_ge4.json"


def test_a_corpus_nobody_declared_is_refused_rather_than_defaulted() -> None:
    for reach in (trainer.check_corpus, trainer.population_path, trainer.split_path):
        with pytest.raises(trainer.GradeTrainingError):
            reach("everything")
    with pytest.raises(trainer.GradeTrainingError):
        trainer.run_name("more", 0, "auc_ge4", "everything")


def test_the_build_corpus_names_its_batches_rather_than_excluding_the_new_one() -> None:
    """So that re-running its population a year from now gives the file it gives today."""
    held = trainer.CORPORA[trainer.BUILD_CORPUS]["batches"]
    assert held and set(held) == {"n1000_0906_1", "n1000_0906_2", "n1000_0906_3"}
    assert trainer.CORPORA["corrected"]["batches"] is None, "every graded row, named as such"


# --------------------------------------------------------------------------- #
# The strata, which the split reads and the model never does.
# --------------------------------------------------------------------------- #
def test_a_row_from_before_the_blocked_draws_still_carries_every_stratum() -> None:
    """A missing stratum is a shortfall nothing can be measured against."""
    assert trainer.block_of({"batch": "n1000_0906_1"}) == trainer.PRE_EXISTING
    assert trainer.block_of({"selected_on": {"block": "top_band"}}) == "top_band"
    assert trainer.sheet_of({"batch": "n1000_0906_1"}) == "n1000_0906_1"
    assert trainer.sheet_of({"batch": "b", "sheet": "b_2"}) == "b_2"

    bare = unit("k0", 3, "n1000_0906_1", place="p0")
    mine = trainer.strata_of(bare)
    assert set(mine) == set(trainer.STRATA)
    assert mine == {"sheet": "n1000_0906_1", "block": trainer.PRE_EXISTING, "grade": "3"}


def test_the_holdout_takes_every_sheet_block_and_grade_in_proportion() -> None:
    """The stratification, which is the one thing this split adds to the shipped one.

    Four blocks over three cuts and four grades, unevenly composed on purpose —
    a fill that balanced only the count would take a slice that is mostly one
    block, and the train-vs-stopping gap would then move for a reason that is
    not fit.
    """
    blocks = ["top_band", "near_bar", "floor_thin_cell", "low_anchor", trainer.PRE_EXISTING]
    units, rows = [], []
    for index in range(400):
        block = blocks[index % len(blocks)]
        pre = block == trainer.PRE_EXISTING
        held = unit(
            f"k{index:04d}",
            1 + (index // 5) % 4,
            "n1000_0906_1" if pre else "correction",
            place=f"p{index:04d}",
        )
        held.block = block
        held.sheet = "n1000_0906_1" if pre else f"correction_{1 + index % 3}"
        units.append(held)
        rows.append(row_at(index * 3.0, index * 5.0, 0.1))

    record = trainer.sides_for(units, seed=0, rows=rows)
    for family in trainer.STRATA:
        for value, read in record["strata"][family].items():
            assert abs(read["share"] - trainer.HOLDOUT_SHARE) < 0.06, (family, value, read)
    assert record["worst_stratum_drift"]["drift"] < 0.06, record["worst_stratum_drift"]


def test_the_sheet_is_a_split_coordinate_and_never_a_model_input(tmp_path) -> None:
    """Matt's ruling of 2026-09-09: the cuts' disagreement stays label noise.

    The `Unit` the loader is handed carries `sheet` and `block`, so the guard
    that matters is that nothing downstream of the split reads either. A
    training example is a picture and a grade, and the recipe carries no key
    naming a cut — the head is told no batch and these are two more of the same.
    """
    from PIL import Image

    picture = tmp_path / "one.jpg"
    Image.new("RGB", (64, 36), (9, 9, 9)).save(picture)

    units, rows = corpus(60)
    for held, cut in zip(units, ["a", "b", "c"] * 20, strict=True):
        held.path, held.sheet, held.block = picture, cut, "top_band"
    trainer.sides_for(units, seed=0, rows=rows)

    examples = trainer.Pictures(units, lambda image, _random: image)
    example = examples[0]
    assert len(example) == 3, "a picture, a grade and an index — no cut and no block"
    assert example[1] == units[0].score
    assert not {"sheet", "block"} & set(trainer.CARRIED)


# --------------------------------------------------------------------------- #
# The pool scores, which are one-shot.
# --------------------------------------------------------------------------- #
def test_a_rescore_keeps_the_scores_it_supersedes_under_the_name_of_their_run(
    tmp_path, monkeypatch
) -> None:
    """★ Every solve record ever taken resolves its order out of one file.

    Overwriting it makes every prior record's ordering unreproducible with
    nothing looking broken, so the archive is part of the write and not a flag.
    It is named for the run that made the scores because a `p_ge4` means nothing
    without the head behind it: 0.50 admits 27.8% of a pool under one of these
    heads and 9.6% under the other.
    """
    monkeypatch.setattr(trainer, "root", lambda: tmp_path)
    assert trainer.keep_superseded_pool_scores(log=lambda *_: None) is None, "nothing to keep"

    live = trainer.pool_scores_path()
    live.write_text(
        json.dumps({"schema": 1, "head": trainer.HEAD, "run": "auc_ge4_more_seed2", "key": "a"})
        + "\n",
        encoding="utf-8",
    )
    assert trainer.pool_scores_run() == "auc_ge4_more_seed2"

    kept = trainer.keep_superseded_pool_scores(log=lambda *_: None)
    assert kept is not None and kept.name == "pool_scores_auc_ge4_more_seed2.jsonl"
    assert not live.exists(), "the live file is MOVED, so a half-written re-score cannot pass"
    assert json.loads(kept.read_text(encoding="utf-8"))["key"] == "a"

    # A second archive of one run never overwrites the first: the first is the
    # file the records taken under it were made against.
    live.write_text(
        json.dumps({"schema": 1, "head": trainer.HEAD, "run": "auc_ge4_more_seed2", "key": "b"})
        + "\n",
        encoding="utf-8",
    )
    again = trainer.keep_superseded_pool_scores(log=lambda *_: None)
    assert again != kept and again.name.startswith("pool_scores_auc_ge4_more_seed2_")
    assert json.loads(kept.read_text(encoding="utf-8"))["key"] == "a", "the first is untouched"


def test_the_live_pool_scores_are_never_named_for_a_corpus() -> None:
    """One file, whatever head wrote it — `solve` reads that path and only it.

    A corpus-suffixed live file would mean a seating had to know which head was
    adopted to find its own column, which is the question adoption exists to
    answer once. The corpus shows up in the archive names and in the `run` field
    on every row, never in the path a reader resolves.
    """
    assert trainer.pool_scores_path().name == "pool_scores.jsonl"
    assert trainer.superseded_pool_scores_path("x").name == "pool_scores_x.jsonl"
