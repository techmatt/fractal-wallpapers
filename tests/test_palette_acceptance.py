"""The palette head's bar: what it measures, and what it refuses to do without."""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import palette_acceptance


def a_row(agreed: bool, spearman: float, regret: float, spread: float = 1.0, **extra) -> dict:
    return {
        "set": extra.get("set", "0000"),
        "candidates": extra.get("candidates", ["a", "b", "c"]),
        "score": extra.get("score", [0.0, 1.0, 0.5]),
        "teacher_score": extra.get("teacher_score", [0.0, 1.0, 0.5]),
        "agreed": agreed,
        "spearman": spearman,
        "discordant_pairs": extra.get("discordant_pairs", 0),
        "regret": regret,
        "teacher_spread": spread,
        "pick": extra.get("pick", "b"),
        "teacher_pick": extra.get("teacher_pick", "b"),
        "recorded_pick": extra.get("recorded_pick", "b"),
    }


def test_the_renderer_control_is_about_the_teacher_and_not_about_us() -> None:
    """It is the teacher disagreeing with its own recorded choice because the
    picture changed. A student cannot move it."""
    rows = [
        a_row(True, 1.0, 0.0, teacher_pick="a", recorded_pick="a", pick="a"),
        a_row(False, 0.5, 0.2, teacher_pick="a", recorded_pick="b", pick="c"),
    ]
    reading = palette_acceptance.measure(rows)
    assert reading["renderer_control"] == pytest.approx(0.5)
    assert reading["top_pick_agreement"] == pytest.approx(0.5)


def test_regret_is_normalized_by_what_was_at_stake() -> None:
    """A disagreement over two candidates the teacher rated within a hair of each
    other costs nothing; a bare agreement rate cannot tell that from picking
    something the teacher put near the bottom."""
    tight = palette_acceptance.measure([a_row(False, 0.9, 0.05, spread=5.0)])
    loose = palette_acceptance.measure([a_row(False, 0.9, 0.05, spread=0.1)])
    assert tight["mean_normalized_regret"] < loose["mean_normalized_regret"]


def test_a_set_whose_candidates_the_teacher_rated_identically_costs_nothing() -> None:
    reading = palette_acceptance.measure([a_row(False, 0.0, 0.0, spread=0.0)])
    assert reading["mean_normalized_regret"] == pytest.approx(0.0)


def test_the_bar_cannot_be_read_without_having_been_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(palette_acceptance, "prereg_path", lambda: tmp_path / "prereg.json")
    with pytest.raises(palette_acceptance.AcceptanceError):
        palette_acceptance.prereg()


def test_the_declared_bars_are_tight_enough_to_be_bars() -> None:
    """Loose enough and every head passes, which is not a check."""
    assert palette_acceptance.AGREEMENT_FLOOR >= 0.5
    assert palette_acceptance.ORDERING_FLOOR >= 0.7
    assert palette_acceptance.REGRET_CEILING <= 0.1


def test_the_written_bar_names_both_bars_of_the_gated_arm() -> None:
    if not palette_acceptance.prereg_path().is_file():
        pytest.skip("the bar has not been written")
    bar = palette_acceptance.prereg()
    names = {entry["name"] for entry in bar["arms"]["top_pick"]["bars"]}
    assert names == {"renderer control", "floor"}
    assert bar["arms"]["top_pick"]["gated"] is True
    assert bar["arms"]["production_argmax"]["gated"] is False


def test_the_bar_says_out_loud_that_the_ground_truth_is_a_model() -> None:
    """The single most important thing a reader of this head has to know."""
    if not palette_acceptance.prereg_path().is_file():
        pytest.skip("the bar has not been written")
    declared = " ".join(palette_acceptance.prereg()["declared"]).lower()
    assert "ground truth" in declared


def test_the_fp16_read_counts_picks_and_pairs_rather_than_probabilities() -> None:
    """This head's answer is a choice inside a set, so a moved score is not a
    changed answer and the check has to measure the answer."""
    before = [a_row(True, 1.0, 0.0, score=[0.0, 1.0, 0.5])]
    moved = palette_acceptance.fp16_agreement(before, [[0.0, 1.0, 0.4999]])
    flipped = palette_acceptance.fp16_agreement(before, [[0.0, 0.4, 0.5]])
    assert moved["decisions"]["changed"] == 0
    assert moved["ordering"]["worst_discordant_pairs"] == 0
    assert flipped["decisions"]["changed"] == 1


def test_a_run_that_never_scored_the_same_pictures_is_refused(tmp_path, monkeypatch) -> None:
    """The control is a fact about the teacher and the population. Two runs that
    disagree about it were scored against different pictures, and a band built
    from them would compare two things."""
    from fractal_wallpapers.models import palette_scoring

    del tmp_path
    monkeypatch.setattr(palette_acceptance, "prereg", lambda: {"population": {}, "declared": []})
    scored = {
        "a": [a_row(True, 1.0, 0.0, teacher_pick="x", recorded_pick="x")],
        "b": [a_row(True, 1.0, 0.0, teacher_pick="y", recorded_pick="x")],
    }
    monkeypatch.setattr(palette_scoring, "read", lambda run=None, path=None: scored[run])
    with pytest.raises(palette_acceptance.AcceptanceError):
        palette_acceptance.read(runs=["a", "b"])
