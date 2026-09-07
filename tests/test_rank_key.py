"""The fitted sort key: the arithmetic, the artifact, and what it refuses.

The fit itself needs two label corpora, a third of a gigabyte of ledger and the
supply sidecar, so it is not stood up here. What is pinned instead is everything
a seating stands on between the fit and the seat: the loaded form, the
standardization, the join identity, the fold assignment, and the two shipped
files — because a coefficient set nobody can account for is exactly the failure
the population record exists to prevent.
"""

from __future__ import annotations

import json

import numpy
import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import flatness, rank_key


def artifact(**overrides) -> dict:
    """A loadable artifact, with one weight per column and nothing else."""
    document = {
        "schema": rank_key.SCHEMA,
        "columns": list(rank_key.COLUMNS),
        "coefficients": {"intercept": 0.0} | {name: 1.0 for name in rank_key.COLUMNS},
        "standardization": {
            "mean": {name: 0.0 for name in rank_key.COLUMNS},
            "deviation": {name: 1.0 for name in rank_key.COLUMNS},
        },
        "fitted_at": "2026-08-28T00:00:00Z",
    }
    document.update(overrides)
    return document


def features(**overrides) -> dict:
    row = {name: 0.0 for name in rank_key.COLUMNS}
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# The loaded form.
# --------------------------------------------------------------------------- #
def test_the_key_is_the_standardized_linear_form_squashed():
    key = rank_key.Key(
        artifact(
            coefficients={"intercept": 0.5} | {name: 0.0 for name in rank_key.COLUMNS},
        )
    )
    assert key.score(features()) == pytest.approx(1 / (1 + numpy.exp(-0.5)))


def test_the_standardization_is_applied_and_not_only_recorded():
    key = rank_key.Key(
        artifact(
            standardization={
                "mean": {name: 0.0 for name in rank_key.COLUMNS} | {"p_ge4": 2.0},
                "deviation": {name: 1.0 for name in rank_key.COLUMNS} | {"p_ge4": 4.0},
            }
        )
    )
    # (2 - 2) / 4 = 0, so a candidate sitting exactly on the fit's mean
    # contributes nothing whatever its raw value is.
    assert key.score(features(p_ge4=2.0)) == pytest.approx(0.5)


def test_a_candidate_missing_a_column_is_refused_and_never_imputed():
    """A form that quietly filled a gap would be ranking a picture nobody read."""
    key = rank_key.Key(artifact())
    with pytest.raises(rank_key.RankKeyError):
        key.score({name: 0.0 for name in rank_key.COLUMNS if name != flatness.COLUMN})


def test_a_missing_artifact_refuses_rather_than_falling_back_to_the_judge(tmp_path):
    with pytest.raises(rank_key.RankKeyError):
        rank_key.load(tmp_path / "not-there.json")


def test_the_key_is_monotone_in_a_positive_weight():
    key = rank_key.Key(artifact())
    assert key.score(features(p_ge4=1.0)) > key.score(features(p_ge4=0.0))


# --------------------------------------------------------------------------- #
# The columns off a pool.
# --------------------------------------------------------------------------- #
def test_a_candidate_with_no_flatness_reading_is_left_out_of_the_ordering():
    pool = [candidate("a"), candidate("b")]
    built, gaps = rank_key.features_for(pool, locations={}, readings={"a": 0.1})
    assert set(built) == {"a"}
    assert gaps["no_flatness"] == 1


def test_a_place_the_location_head_has_never_read_scores_at_the_floor_and_is_counted():
    built, gaps = rank_key.features_for([candidate("a")], locations={}, readings={"a": 0.1})
    assert built["a"]["loc_p_ge4"] == rank_key.NO_LOCATION_READING
    assert gaps["no_location_reading"] == 1


# --------------------------------------------------------------------------- #
# The join.
# --------------------------------------------------------------------------- #
def test_the_ledger_identity_is_the_label_stores_own_render_key():
    """One identity across both sides, or the join is on two different things."""
    from fractal_wallpapers.labeling import finished

    family = {"kind": "julia", "degree": 2, "c": ["-0.1", "0.2"]}
    viewport = {"center_re": "0.0", "center_im": "0.0", "width": "1.0"}
    recipe = {name: 1.0 for name in finished.RECIPE_KEYS}
    label = {
        "family": family,
        "viewport": viewport,
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": "Aster Bloom",
        "recipe": recipe,
    }
    # The frame comes off the RECIPE. `location` carried a copy of it — byte
    # identical on all 366,236 rows on record — and does not any more.
    row = {
        "recipe": {
            "family": family,
            "viewport": viewport,
            "mode": "smooth",
            "mode_params": {},
            "curve": "linear",
            "colormap": "Aster Bloom",
            "palette": recipe,
        },
    }
    assert rank_key.ledger_identity(row) == finished.render_key(label)


def test_a_ledger_row_missing_a_palette_knob_carries_no_identity():
    """The palette half is checked BEFORE the place, so a row with every knob but
    one is dropped rather than joined on a partial recipe."""
    row = {
        "location": {
            "family": {"kind": "mandelbrot", "degree": 2},
            "viewport": {"center_re": "0.0", "center_im": "0.0", "width": "1.0"},
        },
        "recipe": {"mode": "smooth", "curve": "linear", "colormap": "x", "palette": {"gamma": 1.0}},
    }
    assert rank_key.ledger_identity(row) is None


def test_a_ledger_row_with_no_readable_place_carries_no_identity_rather_than_raising():
    """`location_key` RAISES on a family it cannot place. This streams the whole
    ledger, so one malformed row raising would kill a fit over every other row."""
    assert rank_key.ledger_identity({"location": {}, "recipe": {}}) is None


# --------------------------------------------------------------------------- #
# The folds.
# --------------------------------------------------------------------------- #
def test_a_lineage_group_is_never_split_across_folds():
    """96 of the corpus's 625 groups span both stores. A group split across a
    boundary trains on one half of a lineage while testing the other."""
    consumed = [{"kind": rank_key.KINDS[at % 2]} for at in range(60)]
    grouping = {at: at // 4 for at in range(60)}
    folds = rank_key._folds(consumed, grouping)
    by_group: dict = {}
    for at, fold in folds.items():
        by_group.setdefault(grouping[at], set()).add(fold)
    assert all(len(seen) == 1 for seen in by_group.values())


def test_the_folds_are_balanced_within_a_group_of_slack_on_both_kinds():
    consumed = [{"kind": rank_key.KINDS[at % 2]} for at in range(200)]
    grouping = {at: at // 5 for at in range(200)}
    folds = rank_key._folds(consumed, grouping)
    for kind in rank_key.KINDS:
        sizes = [
            sum(1 for at, fold in folds.items() if fold == which and consumed[at]["kind"] == kind)
            for which in range(rank_key.FOLDS)
        ]
        assert max(sizes) - min(sizes) <= 10


# --------------------------------------------------------------------------- #
# The arithmetic, against something independent.
# --------------------------------------------------------------------------- #
def test_the_logistic_agrees_with_scipy_on_the_same_penalised_objective():
    """`sklearn` is not in this project's dependency set, so the IRLS is written
    here and has to be checked against something that was not."""
    from scipy.optimize import minimize

    rng = numpy.random.default_rng(0)
    columns = rng.normal(size=(200, 3))
    truth = numpy.array([1.5, -1.0, 0.4])
    target = (rng.random(200) < 1 / (1 + numpy.exp(-(columns @ truth + 0.3)))).astype(float)

    def objective(beta):
        eta = numpy.clip(numpy.hstack([numpy.ones((200, 1)), columns]) @ beta, -30, 30)
        return -numpy.sum(target * eta - numpy.log1p(numpy.exp(eta))) + 0.5 * rank_key.LAMBDA * (
            numpy.sum(beta[1:] ** 2)
        )

    reference = minimize(objective, numpy.zeros(4), method="BFGS", tol=1e-12).x
    assert numpy.allclose(rank_key.logistic(columns, target), reference, atol=1e-5)


def test_the_auc_agrees_with_a_brute_force_pair_count_ties_included():
    rng = numpy.random.default_rng(3)
    for _ in range(5):
        target = rng.integers(0, 2, 60).astype(bool)
        score = rng.integers(0, 5, 60).astype(float)
        wins = sum(
            1.0 if a > b else 0.5 if a == b else 0.0 for a in score[target] for b in score[~target]
        ) / (target.sum() * (~target).sum())
        assert rank_key.auc(target, score) == pytest.approx(wins)


# --------------------------------------------------------------------------- #
# The shipped artifact.
# --------------------------------------------------------------------------- #
def test_the_shipped_key_loads_and_carries_exactly_the_columns_it_is_read_with():
    """The tracked artifact and [`COLUMNS`] are one form. A column added to the
    code and not to the artifact would be a `KeyError` at the first seating."""
    key = rank_key.load()
    assert key.columns == rank_key.COLUMNS
    assert set(key.document["coefficients"]) == {"intercept", *rank_key.COLUMNS}


def test_the_shipped_key_records_every_label_row_it_was_fitted_on():
    """A selection rule fit on human labels is a category no eligibility guard
    covers. The record is the guard, and it has to reconcile with the artifact.

    **Uniqueness is per store and not global, which is a measured fact about the
    stores rather than a loosening.** This asserted a globally distinct recipe key
    until 2026-09-06 and that held only while no picture sat in both corpora. On
    the 3,278-row fit of that day, **52 do** — the same render, the same batch name
    and the same tier, at two different lines of two same-named files in
    `smooth_render` and `strange_render`. Each is therefore one label counted twice
    by the fit, once on each kind's side of the out-of-fold reading; at 1.6% of the
    population it moves nothing anybody reads, and de-duplicating it means deciding
    which store owns a mode both hold, which is not a question a guard settles.
    What is pinned here is what the record actually claims: no **label row** is
    recorded twice, and no render is consumed twice **within** a kind.
    """
    document = json.loads(rank_key.artifact_path().read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in rank_key.population_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == document["population"]["rows"]
    assert len({(row["kind"], row["file"], row["line"]) for row in rows}) == len(rows)
    assert len({(row["kind"], row["recipe_key"]) for row in rows}) == len(rows)
    for row in rows:
        assert row["kind"] in rank_key.KINDS
        assert 1 <= row["tier"] <= 4
        assert 0 <= row["fold"] < rank_key.FOLDS
        assert set(row["features"]) == set(rank_key.COLUMNS)


def test_the_shipped_key_was_fitted_on_the_flatness_column_that_ships():
    document = json.loads(rank_key.artifact_path().read_text(encoding="utf-8"))
    assert document["flatness"]["column"] == flatness.COLUMN
    assert document["flatness"]["cell"] == flatness.CELL
    assert document["flatness"]["threshold"] == flatness.THRESHOLD
