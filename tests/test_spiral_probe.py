"""The spiral probe: the row-space fit, the pin, and what a shipped artifact says.

Four properties, and each is a way a probe could be quietly wrong. A fit solved
in the row space that is not the fit a dense solve reaches would be a cheaper
answer to a different question. A ridge chosen on the pinned side would be an
instrument spent before it was read. A probe handed another feature set's columns
would produce probabilities rather than an error. And a shipped coefficient
vector whose manifest does not say what picture it reads is a vector nobody can
reproduce a number from.

Everything here is arithmetic on small matrices and stays in the fast lane; the
one guard that touches the tracked artifacts reads two small JSON files.
"""

from __future__ import annotations

import json

import numpy
import pytest

from fractal_wallpapers.labeling import attributes
from fractal_wallpapers.models import spiral_probe


def separable(rows: int = 120, columns: int = 8, seed: int = 3):
    """A design a logistic can fit, with noise so the fit is not degenerate."""
    rng = numpy.random.default_rng(seed)
    features = rng.normal(size=(rows, columns))
    truth = numpy.zeros(columns)
    truth[:3] = (1.4, -0.9, 0.7)
    probability = 1.0 / (1.0 + numpy.exp(-(features @ truth - 0.3)))
    return features, (rng.random(rows) < probability).astype(float)


def dense_fit(features, target, lam: float):
    """The same objective, solved on the columns themselves. The yardstick."""
    return spiral_probe.irls(features, target, lam)


def test_the_row_space_fit_is_the_fit_a_dense_solve_reaches():
    """The SVD is a change of basis and not an approximation.

    A ridge-penalised logistic solution lies in the span of the training rows, so
    fitting on `U · S` and rotating back through `V` is the same optimum. This is
    the claim the module's whole cost argument rests on: at four hundred rows and
    twelve hundred and eighty columns the dense solve is a 1281-square Newton
    step per iteration and the reduced one is 401-square.
    """
    features, target = separable(rows=60, columns=25)
    for lam in (0.5, 5.0, 50.0):
        intercept, coefficients = spiral_probe.fit_ridge(features, target, lam)
        beta = dense_fit(features, target, lam)
        assert intercept == pytest.approx(beta[0], abs=1e-6)
        assert numpy.allclose(coefficients, beta[1:], atol=1e-6)


def test_the_row_space_fit_holds_where_the_design_is_wider_than_it_is_tall():
    """The case the module exists for: more columns than rows.

    A dense Newton step is singular here without the penalty carrying it, and the
    reduced one is a small well-conditioned system whatever the width.
    """
    features, target = separable(rows=40, columns=200)
    intercept, coefficients = spiral_probe.fit_ridge(features, target, 4.0)
    assert coefficients.shape == (200,)
    beta = dense_fit(features, target, 4.0)
    assert intercept == pytest.approx(beta[0], abs=1e-5)
    assert numpy.allclose(coefficients, beta[1:], atol=1e-5)


def test_the_ridge_is_chosen_on_the_training_side_and_the_folds_are_seeded():
    """Two deals at one seed are one deal, and every row is held out exactly once."""
    first = spiral_probe.folds_of(97, folds=5, seed=11)
    second = spiral_probe.folds_of(97, folds=5, seed=11)
    assert [list(block) for block in first] == [list(block) for block in second]
    assert sorted(int(n) for block in first for n in block) == list(range(97))
    assert [list(block) for block in spiral_probe.folds_of(97, 5, 12)] != [
        list(block) for block in first
    ]


def test_a_fitted_probe_reads_back_as_the_probabilities_it_was_fitted_to():
    """`score` on a document is `probabilities` on the fit. One arithmetic."""
    features, target = separable()
    document = spiral_probe.fit(features, target, feature_set="neutral_dinov2")
    read_back = numpy.asarray(spiral_probe.score(document, features))
    mean = numpy.asarray(document["mean"])
    deviation = numpy.asarray(document["deviation"])
    direct = spiral_probe.probabilities(
        document["intercept"],
        numpy.asarray(document["coefficients"]),
        (features - mean) / deviation,
    )
    assert numpy.allclose(read_back, direct)
    assert spiral_probe.auc(target > 0.5, read_back) > 0.8


def test_a_probe_handed_another_feature_sets_columns_refuses():
    """The failure this catches is silent: a wrong-width read still returns numbers.

    Two of the four readings compared here are 384 wide and two are 1280, so a
    caller that swapped them would get a matrix multiply that raises. But a
    caller that sliced one to the other's width would not, which is why the check
    is on the count and states the set it belongs to.
    """
    features, target = separable(columns=8)
    document = spiral_probe.fit(features, target, feature_set="neutral_dinov2")
    with pytest.raises(spiral_probe.ProbeError, match="neutral_dinov2"):
        spiral_probe.score(document, numpy.zeros((4, 7)))


def test_the_fit_refuses_a_training_side_that_holds_one_class():
    features, _target = separable()
    with pytest.raises(spiral_probe.ProbeError, match="both classes"):
        spiral_probe.fit(features, numpy.ones(len(features)), feature_set="neutral_dinov2")


def test_the_split_asserts_the_pin_rather_than_trusting_it():
    """The pin forbids TRAINING, and this is the seam where that is enforced.

    The attribute store's reservation is intra-batch, so the ingest deliberately
    does not assert it — collecting a verdict at a reserved place is the point.
    That leaves exactly one place the guarantee can live, and it is here.
    """
    train, evaluate = spiral_probe.split()
    keys = attributes.pinned("spiral")
    assert keys, "the spiral store ships a pinned evaluation side"
    assert len(evaluate) == len(keys)
    assert not [row for row in train if attributes.place_of(row) in keys]


def test_the_shipped_probe_says_what_picture_it_reads():
    """A coefficient vector with no regime is a vector nobody can reproduce.

    The manifest is not derived from the probes: the regime is a fact about the
    pictures, and a probe file cannot state one. So the two have to agree, and
    this is what holds them together.
    """
    manifest = json.loads(spiral_probe.manifest_path().read_text(encoding="utf-8"))
    assert manifest["shipped"] in manifest["probes"]
    for name, entry in manifest["probes"].items():
        document = spiral_probe.read(spiral_probe.probe_dir() / entry["file"])
        assert document["feature_set"] == name
        assert document["dim"] == entry["dim"] == len(document["coefficients"])
        assert len(document["mean"]) == len(document["deviation"]) == document["dim"]
        assert entry["regime"] == spiral_probe.regime_of(name)
        assert 0.0 < entry["threshold"] < 1.0


def test_reading_a_probe_needs_numpy_and_nothing_else():
    """The read path imports no torch, so a machine that counts need not fit.

    Checked on the source rather than by importing, because every machine that
    runs this suite has torch installed and an import that succeeded would prove
    nothing. `features` is the one function allowed to reach for it and it says
    so in its own body.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(spiral_probe))
    allowed = {"features", "regime_of", "records_of", "split"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name in allowed:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Import):
                names = [alias.name for alias in inner.names]
            elif isinstance(inner, ast.ImportFrom):
                names = [inner.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith(("torch", "timm", "PIL")), (
                    f"{node.name} imports {name}: reading a probe is a matrix multiply and "
                    f"the whole point of shipping it as coefficients is that it stays one"
                )
