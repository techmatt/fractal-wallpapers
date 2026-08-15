"""The two numbers a judge is read in, and the interval around them.

**AUC** — the probability that a randomly chosen good location scores above a
randomly chosen bad one. It is the number to quote when what matters is the
*order*: a queue is worked from the top, and how well the head sorts is the whole
question. It is also insensitive to the base rate, which is what makes it
comparable across populations that hold different amounts of good material.

**Average precision** — the area under precision against recall. It is the number
to quote when what matters is the *top* of the order, and it moves with the base
rate, which is why it is used here only as a training objective on one fixed
population and never as a cross-population comparison.

Ties get **average ranks**, not an arbitrary order. A head that emits the same
probability for two locations has said they are equivalent, and breaking that by
row order silently rewards or punishes it for the sort the loader happened to do.

## The interval is a cluster bootstrap, and the cluster is the group

Locations inside one neighbourhood group are not independent — they are frames a
hair apart on the same plane, often the same picture twice. Resampling
*locations* would treat six views of one hot spot as six pieces of evidence and
report an interval two to three times too narrow. So the bootstrap resamples
**groups**, whole, which is the same unit the train/evaluation split was drawn
over. That is the difference between a confidence interval and a decoration.
"""

from __future__ import annotations

import numpy


def _ranks(scores) -> numpy.ndarray:
    """Ranks 1..n with ties averaged."""
    scores = numpy.asarray(scores, dtype=numpy.float64)
    order = numpy.argsort(scores, kind="mergesort")
    ranks = numpy.empty(len(scores), dtype=numpy.float64)
    ranks[order] = numpy.arange(1, len(scores) + 1, dtype=numpy.float64)
    sorted_scores = scores[order]
    start = 0
    while start < len(sorted_scores):
        stop = start
        while stop + 1 < len(sorted_scores) and sorted_scores[stop + 1] == sorted_scores[start]:
            stop += 1
        if stop > start:
            ranks[order[start : stop + 1]] = (start + stop + 2) / 2.0
        start = stop + 1
    return ranks


def auc(labels, scores) -> float | None:
    """Area under the ROC curve, or `None` when one class is absent.

    `None` rather than a number, because a population with no positives has not
    measured a bad head — it has not measured anything, and 0.5 would read as
    "chance" to everyone downstream.
    """
    labels = numpy.asarray(labels, dtype=numpy.float64)
    positives = labels.sum()
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ranks = _ranks(scores)
    return float(
        (ranks[labels == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives)
    )


def average_precision(labels, scores) -> float | None:
    """Area under precision-recall, summed over the recall steps."""
    labels = numpy.asarray(labels, dtype=numpy.float64)
    if labels.sum() == 0 or labels.sum() == len(labels):
        return None
    order = numpy.argsort(-numpy.asarray(scores, dtype=numpy.float64), kind="mergesort")
    hits = labels[order]
    cumulative = numpy.cumsum(hits)
    precision = cumulative / numpy.arange(1, len(hits) + 1)
    return float((precision * hits).sum() / hits.sum())


def bootstrap(
    statistic,
    groups,
    draws: int = 5000,
    seed: int = 0,
) -> dict:
    """Resample whole groups and report the percentile interval of `statistic`.

    `statistic` is handed the indices of one resample and returns a number or
    `None`; resamples where it cannot be computed — a draw that happened to
    contain no positives — are counted and excluded rather than filled in.
    """
    groups = numpy.asarray(groups)
    unique, inverse = numpy.unique(groups, return_inverse=True)
    members = [numpy.where(inverse == index)[0] for index in range(len(unique))]
    generator = numpy.random.default_rng(seed)

    values = []
    undefined = 0
    for _ in range(draws):
        picked = generator.integers(0, len(members), size=len(members))
        indices = numpy.concatenate([members[index] for index in picked])
        value = statistic(indices)
        if value is None or not numpy.isfinite(value):
            undefined += 1
            continue
        values.append(value)
    if not values:
        return {"draws": draws, "undefined": undefined, "lo": None, "hi": None}
    array = numpy.asarray(values)
    return {
        "draws": draws,
        "undefined": undefined,
        "clusters": int(len(unique)),
        "lo": float(numpy.percentile(array, 2.5)),
        "hi": float(numpy.percentile(array, 97.5)),
        "median": float(numpy.percentile(array, 50)),
    }


def paired_delta(
    labels,
    ours,
    theirs,
    groups,
    draws: int = 5000,
    seed: int = 0,
) -> dict:
    """Δ AUC between two heads on one population, with a cluster interval.

    Paired: every resample scores both heads on the *same* drawn locations, so
    the population's own difficulty cancels and what is left is the difference
    between the two heads. Comparing two independently-bootstrapped intervals
    instead would widen the answer by the variance of the population twice over.
    """
    labels = numpy.asarray(labels, dtype=numpy.float64)
    ours = numpy.asarray(ours, dtype=numpy.float64)
    theirs = numpy.asarray(theirs, dtype=numpy.float64)

    def statistic(indices):
        mine = auc(labels[indices], ours[indices])
        yours = auc(labels[indices], theirs[indices])
        return None if mine is None or yours is None else mine - yours

    interval = bootstrap(statistic, groups, draws=draws, seed=seed)
    mine, yours = auc(labels, ours), auc(labels, theirs)
    interval["ours"] = mine
    interval["theirs"] = yours
    interval["delta"] = None if mine is None or yours is None else mine - yours
    return interval


__all__ = ["auc", "average_precision", "bootstrap", "paired_delta"]
