"""The numbers a judge is read in, and the interval that says how far to trust them."""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import metrics

numpy = pytest.importorskip("numpy")


def test_a_perfect_order_is_one_and_a_reversed_one_is_zero() -> None:
    labels = [0, 0, 1, 1]
    assert metrics.auc(labels, [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert metrics.auc(labels, [0.9, 0.8, 0.2, 0.1]) == 0.0


def test_ties_get_average_ranks() -> None:
    """A head that emitted one probability for two locations has said they are
    equivalent. Breaking the tie by row order rewards or punishes it for the
    sort the loader happened to do."""
    assert metrics.auc([0, 1], [0.5, 0.5]) == 0.5
    assert metrics.auc([0, 0, 1, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5
    forwards = metrics.auc([0, 1, 0, 1], [0.2, 0.2, 0.9, 0.9])
    backwards = metrics.auc([1, 0, 1, 0], [0.2, 0.2, 0.9, 0.9])
    assert forwards == backwards == 0.5


def test_a_population_with_one_class_has_measured_nothing() -> None:
    """`None`, never 0.5: a partition with no positives has not measured a bad
    head, and 0.5 reads as chance to everyone downstream."""
    assert metrics.auc([0, 0, 0], [0.1, 0.5, 0.9]) is None
    assert metrics.auc([1, 1], [0.1, 0.9]) is None
    assert metrics.average_precision([0, 0], [0.1, 0.9]) is None


def test_average_precision_rewards_the_top_of_the_order() -> None:
    """Two orders with the same AUC can have different AP — which is why AP is
    the training objective and AUC is the comparison."""
    labels = [1, 0, 0, 0, 1, 0, 0, 0]
    top = metrics.average_precision(labels, [9, 8, 7, 6, 5, 4, 3, 2])
    spread = metrics.average_precision(labels, [5, 9, 8, 7, 6, 4, 3, 2])
    assert top > spread


def test_the_bootstrap_resamples_groups_rather_than_locations() -> None:
    """Six views of one hot spot are one piece of evidence, not six. Resampling
    locations would report an interval that is far too narrow."""
    generator = numpy.random.default_rng(0)
    labels = numpy.array([0, 1] * 60)
    scores = labels + generator.normal(0, 1.0, size=len(labels))

    def statistic(indices):
        return metrics.auc(labels[indices], scores[indices])

    by_location = metrics.bootstrap(statistic, numpy.arange(len(labels)), draws=400, seed=0)
    clustered = metrics.bootstrap(statistic, numpy.arange(len(labels)) // 20, draws=400, seed=0)
    assert clustered["clusters"] == 6
    assert (clustered["hi"] - clustered["lo"]) > (by_location["hi"] - by_location["lo"])


def test_the_paired_delta_cancels_the_populations_own_difficulty() -> None:
    """Scoring both heads on the same resample is what makes the interval about
    the two heads rather than about which locations were drawn."""
    generator = numpy.random.default_rng(1)
    labels = numpy.array([0] * 100 + [1] * 100)
    strong = labels + generator.normal(0, 0.8, size=len(labels))
    weak = labels + generator.normal(0, 2.0, size=len(labels))
    groups = numpy.arange(len(labels)) // 4

    delta = metrics.paired_delta(labels, strong, weak, groups, draws=500, seed=0)
    assert delta["delta"] > 0
    assert delta["lo"] > 0, "a real difference should not straddle zero at this size"
    assert delta["ours"] > delta["theirs"]

    itself = metrics.paired_delta(labels, strong, strong, groups, draws=200, seed=0)
    assert itself["delta"] == 0.0
    assert itself["lo"] == itself["hi"] == 0.0


def test_a_resample_that_cannot_be_measured_is_counted_not_filled_in() -> None:
    labels = numpy.array([0, 0, 0, 0, 1])

    def statistic(indices):
        return metrics.auc(labels[indices], numpy.arange(len(labels))[indices])

    out = metrics.bootstrap(statistic, numpy.arange(5), draws=200, seed=0)
    assert out["undefined"] > 0
