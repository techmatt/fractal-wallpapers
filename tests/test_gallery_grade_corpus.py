"""The frozen corpus, the recipe axis, and the one call that makes a fit repeat.

Three things adopted on 2026-09-10 that nothing else here would notice going
wrong. The corpus is tracked because it cannot be rebuilt — so the only thing
standing between it and a silent edit is its own checksum. The recipe is a third
naming axis, and a default that slipped would put a run in another band's
directory. And determinism is a promise a process either can keep or cannot,
which is decided by an environment variable read before torch is imported.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from fractal_wallpapers.models import gallery_grade_train as trainer

CORPUS = "twelve_sheets"


def _corpus_dir():
    return trainer.frozen_dir(CORPUS)


def _checksums() -> dict:
    return json.loads((_corpus_dir() / "checksums.json").read_text(encoding="utf-8"))


def test_every_frozen_file_still_hashes_to_what_it_says() -> None:
    """The whole reason these are tracked rather than regenerated.

    A frozen corpus that drifted by one byte would be a corpus the adopted column
    was not fitted on, and nothing else in this suite would say so: the fit reads
    it happily, the split still applies, and the numbers move by an amount nobody
    could attribute.
    """
    document = _checksums()
    assert document["corpus"] == CORPUS
    for name, said in document["files"].items():
        path = _corpus_dir() / name
        assert path.is_file(), name
        data = path.read_bytes()
        assert len(data) == said["bytes"], name
        assert hashlib.sha256(data).hexdigest() == said["sha256"], name


def test_the_corpus_is_the_one_the_adopted_column_was_fitted_on() -> None:
    document = _checksums()
    assert document["rows"] == 2829
    assert document["renders"] == 2829, "one row per render — the target is per render"
    assert document["split_seed"] == 20260910
    assert document["sides"] == {"stopping": 566, "train": 2263}
    assert len(document["sheets"]) == 12, "twelve, which is what the corpus is named for"


def test_the_two_files_over_the_limit_are_the_two_the_allowlist_excuses() -> None:
    """Ties `tests/test_history_purity.py`'s third entry to a fact rather than a claim."""
    limit = 1024 * 1024
    over = {
        name: said["bytes"] for name, said in _checksums()["files"].items() if said["bytes"] > limit
    }
    assert sorted(over) == ["population.jsonl", "targets.json"]


def test_every_row_resolves_to_a_per_render_target() -> None:
    """Read as JSON rather than through the trainer, so this costs no store.

    `population.jsonl`'s own `score` is the verdict as cast; what the band trains
    on is `targets.json`'s per-render `raw`. A row whose render key had no target
    would be a row the fit would refuse — which is the right behaviour and a bad
    way to find out.
    """
    where = _corpus_dir()
    targets = json.loads((where / "targets.json").read_text(encoding="utf-8"))["per_render"]
    render_of = json.loads((where / "render_key_of.json").read_text(encoding="utf-8"))
    split = json.loads((where / "split.json").read_text(encoding="utf-8"))
    keys = [
        json.loads(line)["key"]
        for line in (where / "population.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert keys == list(split["key_of_row"]), "the split is about these rows, in this order"
    for key in keys:
        assert key in render_of, key
        read = targets[render_of[key]]
        assert read["raw"] in (1, 2, 3, 4), key


def test_a_frozen_corpus_refuses_to_be_rebuilt_or_re_split() -> None:
    """Both writers, because either one of them silently succeeding loses the corpus."""
    assert trainer.frozen(CORPUS) is True
    assert trainer.frozen(trainer.BUILD_CORPUS) is False
    for reach in (trainer.write_population, trainer.write_split):
        with pytest.raises(trainer.GradeTrainingError, match="frozen"):
            reach(corpus=CORPUS)


def test_a_frozen_corpus_reads_from_the_tracked_tree_and_no_other_one_does() -> None:
    for name in ("population_path", "split_path"):
        reach = getattr(trainer, name)
        assert _corpus_dir() in reach(CORPUS).parents
        assert _corpus_dir() not in reach("corrected").parents


# --------------------------------------------------------------------------- #
# The recipe axis.
# --------------------------------------------------------------------------- #
def test_the_adopted_recipe_is_the_default_and_the_first_one_keeps_bare_names() -> None:
    """Moving this constant is an adoption, with a re-score and a bar move in it."""
    assert trainer.RECIPE == "drop_high_asymmetric", "adopted 2026-09-10"
    assert trainer.FIRST_RECIPE == "inherited"
    assert trainer.RECIPE in trainer.RECIPES
    build, first = trainer.BUILD_CORPUS, trainer.FIRST_RECIPE
    assert trainer.run_name("more", 0, "auc_ge4", build, first) == "auc_ge4_more_seed0"
    assert (
        trainer.run_name("more", 0, "auc_ge4", CORPUS, trainer.RECIPE)
        == "twelve_sheets_drop_high_asymmetric_auc_ge4_more_seed0"
    )


def test_the_three_axes_all_move_every_name_that_carries_them() -> None:
    """A default that slipped on any axis puts a run in another band's directory."""
    seen = set()
    for corpus in sorted(trainer.CORPORA):
        for band in sorted(trainer.RULES):
            for recipe in sorted(trainer.RECIPES):
                seen.add(trainer.run_name("more", 0, band, corpus, recipe))
                seen.add(str(trainer.bar_path(band, corpus, recipe)))
                seen.add(str(trainer.band_path(band, corpus, recipe)))
                seen.add(str(trainer.comparison_path(band, corpus, recipe)))
    expected = len(trainer.CORPORA) * len(trainer.RULES) * len(trainer.RECIPES) * 4
    assert len(seen) == expected


def test_a_recipe_nobody_declared_is_refused_rather_than_defaulted() -> None:
    with pytest.raises(trainer.GradeTrainingError):
        trainer.check_recipe("drop_low")
    with pytest.raises(trainer.GradeTrainingError):
        trainer.run_name("more", 0, "auc_ge4", "corrected", "drop_low")


def test_the_ensemble_column_names_how_many_heads_wrote_it() -> None:
    """A column is meaningless without its head, and an ensemble's head is k of them."""
    named = trainer.ensemble_name("more", (0, 1, 2), "auc_ge4", CORPUS, trainer.RECIPE)
    assert named.endswith("_more_k3")
    assert "seed" not in named
    assert named != trainer.run_name("more", 0, "auc_ge4", CORPUS, trainer.RECIPE)


def test_only_the_adopted_recipe_ensembles_and_it_runs_one_arm() -> None:
    assert trainer.RECIPES["drop_high_asymmetric"]["ensemble"] is True
    assert trainer.RECIPES["drop_high_asymmetric"]["arms"] == ("more",)
    assert trainer.RECIPES["inherited"]["ensemble"] is False
    assert trainer.RECIPES["inherited"]["arms"] == trainer.BAND_ARMS


# --------------------------------------------------------------------------- #
# The loss, and the promise.
# --------------------------------------------------------------------------- #
def test_the_asymmetric_loss_is_the_shipped_one_at_a_weight_of_one() -> None:
    """The equality the whole arm is stated against, asserted rather than assumed."""
    trainer.assert_symmetric_case()

    import torch

    from fractal_wallpapers.models import head

    torch.manual_seed(7)
    logits, ranks = torch.randn(48, 3), torch.randint(0, 4, (48,))
    symmetric = trainer.weighted_corn_loss(logits, ranks, 4, 1.0)
    asymmetric = trainer.weighted_corn_loss(logits, ranks, 4, 2.0)
    assert torch.allclose(symmetric, head.corn_loss(logits, ranks, num_classes=4), atol=1e-6)
    assert not torch.allclose(symmetric, asymmetric), "2x has to move something"


def test_the_cli_sets_the_cublas_workspace_before_anything_imports_torch() -> None:
    """`make_deterministic` refuses without it, so this is what stands behind the fit.

    Importing the package is what sets it, and importing it is the first thing a
    `fractal-wallpapers` process does.
    """
    import os

    import fractal_wallpapers.cli  # noqa: F401
    from fractal_wallpapers.models import train

    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == train.CUBLAS_WORKSPACE


def test_a_process_without_the_workspace_refuses_rather_than_fitting_anyway() -> None:
    """A fit that quietly could not keep its promise is worse than one that stops."""
    import os

    from fractal_wallpapers.models import train

    before = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ""
    try:
        with pytest.raises(train.NotDeterministic, match="CUBLAS_WORKSPACE_CONFIG"):
            train.make_deterministic()
    finally:
        if before is None:
            os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)
        else:
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = before
