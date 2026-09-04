"""A linear probe over frozen features: is this location a spiral?

Every other model in this directory is trained end to end. This one is not. It is
a **probe**: one logistic regression, fitted on features some frozen network
already produces, asking whether the answer is already in there. Nothing is
fine-tuned, no backbone moves, and the fitted artifact is a vector of
coefficients small enough to track in git as text.

## Why a probe and not a head

`spiral` is an attribute of a place rather than a judgement of it — see
[`fractal_wallpapers.labeling.attributes`] — and it feeds a share cap in the
gallery solve. A cap needs a *count* over thousands of locations, so the question
is whether an existing frozen reading of a location already separates the two
classes well enough to count with. Training a fifth network to find that out
would answer a different, more expensive question.

## The feature set is the experiment, and the label side is held still

Every probe here is fitted on the same verdicts and differs only in what it
reads. Four readings were compared and they are not interchangeable:

```text
neutral_dinov2   DINOv2 ViT-S/14 on the location's neutral render
location_head    the shipped location head's pre-logits, on its own canonical view
seated_dinov2    DINOv2 on the finished coloured picture a labeler was shown
render_head      the shipped render judge's pre-logits, on that same picture
```

The first two are readings of the **place**; the last two are readings of a
**picture of the place under one coloring somebody chose**, and the gap between
them is how much of the answer the coloring was hiding. It was 8.8 points of
balanced accuracy on the pinned hundred, in the place-reading's favour, which is
why the shipped probe reads a place.

**Only the two place-side sets are built here**, by [`features`]: a location
record is all either of them needs. The two seated sets are readings of a picture
a *seating pass* chose, so building one means resolving a pool — that belongs to
whoever holds the pool and is not a function of a location. They were the
controls and their numbers live in the report that fitted them.

## The fit is IRLS in the row space, which is exact and not an approximation

There are four hundred training rows against up to twelve hundred and eighty
feature columns, so the design is wide. A ridge-penalised logistic solution lies
in the span of the training rows whatever the width, so the fit runs on a thin
SVD's `U · S` — at most `n` columns — and the coefficients come back through `V`.
The penalty is unchanged by that rotation, because the two-norm of `β = Vγ` is
the two-norm of `γ`. This is the same objective a dense solve would reach and it
is far cheaper; `tests/test_spiral_probe.py` holds the two against each other.

The intercept is never penalised, and the ridge is chosen by k-fold
cross-validation on the **training side only**. The pinned evaluation side is
read once, at the end, by whoever reports — never by the fit.

## Reading a probe needs numpy and nothing else

The artifact is JSON: the standardization the features were centred by, the
coefficients, the intercept and the threshold. So the solve can spend torch and a
GPU while the thing that *counts* spirals over the standing supply is a matrix
multiply. `models/spiral/manifest.json` says which feature set each probe reads
and at which regime, because a coefficient vector is meaningless beside a reading
taken another way.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: The schema every probe document carries.
SCHEMA = 1

#: The class the probe's probability is the probability *of*. The other class is
#: everything else, and the store's own tuple is what says what those are.
POSITIVE = "spiral"

#: The ridge grid the penalty is chosen from, per training row. Scaled by the row
#: count at use, so a fit on a hundred rows and one on four hundred are asking the
#: same question of the same number.
LAMBDAS: tuple[float, ...] = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)

#: How many folds the ridge is chosen over, and the seed that deals them.
FOLDS = 5
FOLD_SEED = 20260903

#: Where the probability is cut when a probe is asked for a verdict rather than a
#: number. A share cap will sweep this; it is the default and not a constant.
THRESHOLD = 0.5

#: The place-side feature sets, and the picture each is read off. A seated set is
#: not in here on purpose — see the module docstring.
FEATURE_SETS: dict[str, str] = {
    "neutral_dinov2": "DINOv2 ViT-S/14 on the location's neutral render",
    "location_head": "the shipped location head's pre-logits, on its canonical view",
}

#: The set the shipped probe reads.
SHIPPED = "neutral_dinov2"


class ProbeError(RuntimeError):
    """A probe cannot be fitted, or cannot be read."""


def regime_of(feature_set: str) -> dict:
    """What picture a feature set is read off, spelled out for the manifest.

    A coefficient vector says nothing about the frame it was fitted over, and the
    two readings here are drawn through the same map at different geometries — so
    a manifest that named only the encoder would let one probe be handed the
    other's columns without a word.
    """
    from fractal_wallpapers.curation import neutral
    from fractal_wallpapers.models import embedding, head, location_view

    if feature_set == "neutral_dinov2":
        return {
            "picture": "neutral render",
            "encoder": embedding.VARIANT,
            "stamp": neutral.stamp(),
            **neutral.choices(),
        }
    if feature_set == "location_head":
        resolution, supersample = location_view.geometry()
        return {
            "picture": "the location head's canonical view",
            "encoder": f"models/location/location.fp16.pt pre-logits ({head.BACKBONE})",
            "colormap": location_view.canonical_map(),
            "resolution": list(resolution),
            "supersample": supersample,
            "mode": location_view.MODE,
            "curve": location_view.CURVE,
        }
    raise ProbeError(f"unknown feature set {feature_set!r} — known: {list(FEATURE_SETS)}")


def features(records: list[dict], feature_set: str = SHIPPED, *, directory=None, log=print):
    """One row of frozen features per location record, in the order given.

    `records` carry a family, a viewport and a maxiter — a label row, a ledger
    row's recipe, a walk find. The pictures are addressed by the digest of their
    own recipe, so a second pass over a location already drawn costs nothing.

    This is the half that needs torch. Everything else in this module is numpy,
    which is what lets a probe be *read* on a machine that could not fit one.
    """
    import numpy
    import torch
    from PIL import Image

    from fractal_wallpapers.curation import neutral
    from fractal_wallpapers.models import embedding, head, location_view, scoring, ship

    if feature_set not in FEATURE_SETS:
        raise ProbeError(f"unknown feature set {feature_set!r} — known: {list(FEATURE_SETS)}")
    where = Path(directory) if directory is not None else None

    if feature_set == "neutral_dinov2":
        neutral.check_map()
        pictures = [str(neutral.render_neutral(record, where)[0]) for record in records]
        log(f"[spiral] {len(pictures):,} neutral render(s) through {embedding.VARIANT}")
        model = embedding.build()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        config = embedding.data_config(model)
        return embedding.encode(model, pictures, device, config["mean"], config["std"])

    colormap = location_view.canonical_map()
    cyclic = location_view.cyclic_maps()
    view_dir = where if where is not None else Path("artifacts") / "spiral_probe_views"
    pictures = [
        location_view.render_view(record, colormap, cyclic, view_dir)[0] for record in records
    ]
    model, config, device = scoring.load(ship.shipped_path("location"), "auto")
    transform = head.Transform(
        tuple(config["mean"]), tuple(config["std"]), config["interpolation"], train=False
    )
    log(f"[spiral] {len(pictures):,} canonical view(s) through the location head")
    out = []
    with torch.no_grad():
        for start in range(0, len(pictures), 32):
            frames = []
            for path in pictures[start : start + 32]:
                with Image.open(path) as opened:
                    opened.load()
                    frames.append(transform(opened))
            stacked = torch.stack(frames).to(device)
            out.append(
                model.forward_head(model.forward_features(stacked), pre_logits=True)
                .float()
                .cpu()
                .numpy()
            )
    return numpy.vstack(out)


def probe_dir() -> Path:
    """Where the tracked probes and their manifest live."""
    return repo_root() / "models" / "spiral"


def probe_path(feature_set: str) -> Path:
    return probe_dir() / f"{feature_set}.json"


def manifest_path() -> Path:
    return probe_dir() / "manifest.json"


# --------------------------------------------------------------------------- #
# The fit.
# --------------------------------------------------------------------------- #
def standardize(matrix):
    """`(mean, deviation)` over the columns, a zero-variance column left alone."""
    import numpy

    mean = matrix.mean(axis=0)
    deviation = matrix.std(axis=0)
    deviation = numpy.where(deviation < 1e-12, 1.0, deviation)
    return mean, deviation


def irls(design_columns, target, lam: float, iterations: int = 200):
    """Ridge-penalised logistic by IRLS, returning `[intercept, *slopes]`.

    Damped: a step that does not improve the penalised log-likelihood is halved
    rather than taken. Separable data is ordinary at these widths, and an
    undamped Newton step on it walks off to a wall of infinities.
    """
    import numpy

    rows, width = design_columns.shape
    design = numpy.hstack([numpy.ones((rows, 1)), design_columns])
    beta = numpy.zeros(width + 1)
    penalty = numpy.eye(width + 1) * lam
    penalty[0, 0] = 0.0

    def objective(candidate):
        eta = numpy.clip(design @ candidate, -30, 30)
        loglik = float(numpy.sum(target * eta - numpy.logaddexp(0.0, eta)))
        return loglik - 0.5 * float(candidate @ penalty @ candidate)

    current = objective(beta)
    for _ in range(iterations):
        eta = numpy.clip(design @ beta, -30, 30)
        mu = 1.0 / (1.0 + numpy.exp(-eta))
        weight = numpy.clip(mu * (1 - mu), 1e-9, None)
        gradient = design.T @ (target - mu) - penalty @ beta
        hessian = design.T @ (design * weight[:, None]) + penalty
        try:
            step = numpy.linalg.solve(hessian, gradient)
        except numpy.linalg.LinAlgError:
            step = numpy.linalg.lstsq(hessian, gradient, rcond=None)[0]
        scale, proposed, value = 1.0, beta, current
        for _ in range(24):
            proposed = beta + scale * step
            value = objective(proposed)
            if value >= current:
                break
            scale *= 0.5
        else:
            break
        moved = float(numpy.max(numpy.abs(proposed - beta)))
        beta, current = proposed, value
        if moved < 1e-9:
            break
    return beta


def fit_ridge(features, target, lam: float):
    """`(intercept, coefficients)` in the ORIGINAL column space, fitted at `lam`.

    Solved on the thin SVD's `U · S` — see the module docstring on why that is
    the same solution and not an approximation.
    """
    import numpy

    features = numpy.asarray(features, dtype=numpy.float64)
    target = numpy.asarray(target, dtype=numpy.float64)
    left, singular, right = numpy.linalg.svd(features, full_matrices=False)
    keep = singular > (float(singular.max()) if singular.size else 0.0) * 1e-10
    reduced = left[:, keep] * singular[keep]
    beta = irls(reduced, target, lam)
    return float(beta[0]), right[keep].T @ beta[1:]


def folds_of(count: int, folds: int = FOLDS, seed: int = FOLD_SEED):
    """A seeded deal of `count` rows into `folds` held-out blocks."""
    import numpy

    order = numpy.random.default_rng(seed).permutation(count)
    return [order[block::folds] for block in range(folds)]


def probabilities(intercept: float, coefficients, features):
    """`P(spiral)` per row, from coefficients in the original column space."""
    import numpy

    linear = numpy.asarray(features, dtype=numpy.float64) @ coefficients + intercept
    return 1.0 / (1.0 + numpy.exp(-numpy.clip(linear, -30, 30)))


def auc(target, score) -> float:
    """Mann-Whitney AUC, ties at half."""
    import numpy

    target = numpy.asarray(target).astype(bool)
    score = numpy.asarray(score, dtype=float)
    if target.sum() == 0 or (~target).sum() == 0:
        return float("nan")
    unique, inverse, counts = numpy.unique(score, return_inverse=True, return_counts=True)
    order = numpy.argsort(score, kind="mergesort")
    ranks = numpy.empty(score.size, dtype=float)
    ranks[order] = numpy.arange(1, score.size + 1, dtype=float)
    sums = numpy.zeros(unique.size)
    numpy.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    positives = int(target.sum())
    return float(
        (ranks[target].sum() - positives * (positives + 1) / 2) / (positives * int((~target).sum()))
    )


def held_out(features, target, lam: float, folds: int = FOLDS, seed: int = FOLD_SEED):
    """Every row's probability, read by the fold that did not train on it."""
    import numpy

    features = numpy.asarray(features, dtype=numpy.float64)
    target = numpy.asarray(target, dtype=numpy.float64)
    out = numpy.zeros(len(target))
    for block in folds_of(len(target), folds, seed):
        mask = numpy.ones(len(target), dtype=bool)
        mask[block] = False
        mean, deviation = standardize(features[mask])
        intercept, coefficients = fit_ridge(
            (features[mask] - mean) / deviation, target[mask], lam * int(mask.sum())
        )
        out[block] = probabilities(intercept, coefficients, (features[block] - mean) / deviation)
    return out


def choose_lambda(features, target, lambdas=LAMBDAS, folds: int = FOLDS, seed: int = FOLD_SEED):
    """`(lambda, readings)` — the ridge, chosen on the training side alone.

    Cross-validated on AUC, because the threshold is swept afterwards and a rule
    that picked on accuracy at one cut would choose the ridge that happened to
    suit that cut.
    """
    import numpy

    readings = []
    for lam in lambdas:
        probability = held_out(features, target, lam, folds, seed)
        readings.append(
            {
                "lambda": float(lam),
                "auc": auc(target, probability),
                "accuracy": float(
                    numpy.mean(
                        (probability >= THRESHOLD) == (numpy.asarray(target, dtype=float) > 0.5)
                    )
                ),
            }
        )
    best = max(readings, key=lambda reading: (reading["auc"], -reading["lambda"]))
    return float(best["lambda"]), readings


def fit(
    features,
    target,
    *,
    feature_set: str,
    lambdas=LAMBDAS,
    folds: int = FOLDS,
    seed: int = FOLD_SEED,
    threshold: float = THRESHOLD,
    **provenance,
) -> dict:
    """THE fit: choose the ridge on the training side, then fit on all of it."""
    import numpy

    features = numpy.asarray(features, dtype=numpy.float64)
    target = numpy.asarray(target, dtype=numpy.float64)
    if features.ndim != 2 or len(features) != len(target):
        raise ProbeError(f"{features.shape} features against {target.shape} labels")
    if len(numpy.unique(target)) < 2:
        raise ProbeError("a probe needs both classes on the training side")
    lam, readings = choose_lambda(features, target, lambdas, folds, seed)
    mean, deviation = standardize(features)
    intercept, coefficients = fit_ridge((features - mean) / deviation, target, lam * len(target))
    return {
        "schema": SCHEMA,
        "attribute": "spiral",
        "positive": POSITIVE,
        "feature_set": feature_set,
        "dim": int(features.shape[1]),
        "train_rows": int(len(target)),
        "train_positives": int(target.sum()),
        "lambda": lam,
        "lambda_grid": readings,
        "folds": int(folds),
        "fold_seed": int(seed),
        "threshold": float(threshold),
        "mean": [float(value) for value in mean],
        "deviation": [float(value) for value in deviation],
        "intercept": float(intercept),
        "coefficients": [float(value) for value in coefficients],
        **provenance,
    }


# --------------------------------------------------------------------------- #
# Reading one.
# --------------------------------------------------------------------------- #
def read(path: Path) -> dict:
    """One probe document, schema-checked."""
    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise ProbeError(f"{path}: schema {document.get('schema')!r}, expected {SCHEMA}")
    for field in ("mean", "deviation", "coefficients", "intercept", "feature_set"):
        if field not in document:
            raise ProbeError(f"{path}: a probe carries no {field!r}")
    return document


def score(document: dict, features):
    """`P(spiral)` per row, through one probe. numpy and nothing else."""
    import numpy

    mean = numpy.asarray(document["mean"], dtype=numpy.float64)
    deviation = numpy.asarray(document["deviation"], dtype=numpy.float64)
    features = numpy.asarray(features, dtype=numpy.float64)
    if features.ndim != 2 or features.shape[1] != mean.size:
        raise ProbeError(
            f"this probe reads {mean.size} columns of {document['feature_set']!r} and was "
            f"handed {features.shape}. A coefficient vector is meaningless beside a reading "
            f"taken another way."
        )
    return probabilities(
        float(document["intercept"]),
        numpy.asarray(document["coefficients"], dtype=numpy.float64),
        (features - mean) / deviation,
    )


def write(document: dict, path: Path | None = None) -> Path:
    """Ship one probe as tracked text."""
    path = probe_path(document["feature_set"]) if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path


def write_manifest(documents: list[dict], extra: dict | None = None) -> Path:
    """What each shipped probe reads, at which regime, and where it cuts.

    The probes themselves are a wall of coefficients; this is the file a person
    reads. It is not derived from them — the regime is a fact about the pictures
    and a coefficient vector cannot state one.
    """
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema": SCHEMA,
        "attribute": "spiral",
        "positive": POSITIVE,
        "shipped": SHIPPED,
        "probes": {
            held["feature_set"]: {
                "file": f"{held['feature_set']}.json",
                "reads": FEATURE_SETS.get(held["feature_set"], held.get("description", "")),
                "regime": regime_of(held["feature_set"]),
                "dim": held["dim"],
                "threshold": held["threshold"],
                "lambda": held["lambda"],
                "train_rows": held["train_rows"],
                "train_positives": held["train_positives"],
            }
            for held in documents
        },
        **(extra or {}),
    }
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


# --------------------------------------------------------------------------- #
# The split.
# --------------------------------------------------------------------------- #
def split(name: str = "spiral") -> tuple[list[dict], list[dict]]:
    """`(train, evaluation)` — the store's cast rows, cut on its own pin.

    The pin is asserted on the training side here, so no caller can build the
    split without asserting it — see
    [`fractal_wallpapers.labeling.attributes.assert_pin_holds`] on why the
    assertion belongs to whoever builds a split rather than to the ingest.
    """
    from fractal_wallpapers.labeling import attributes

    keys = attributes.pinned(name)
    rows = attributes.resolved(name).cast()
    train = [row for row in rows if attributes.place_of(row) not in keys]
    evaluate = [row for row in rows if attributes.place_of(row) in keys]
    attributes.assert_pin_holds(name, train)
    return train, evaluate


def targets(rows: list[dict]):
    """`1` where a row says [`POSITIVE`], `0` otherwise."""
    import numpy

    return numpy.array([1.0 if row.get("class") == POSITIVE else 0.0 for row in rows])


def records_of(rows: list[dict]) -> list[dict]:
    """Attribute rows as the location records [`features`] renders from."""
    from fractal_wallpapers import locations

    return [
        {
            "family": row["family"],
            "viewport": row["viewport"],
            "maxiter": locations.maxiter_of(row),
        }
        for row in rows
    ]


__all__ = [
    "FEATURE_SETS",
    "FOLDS",
    "FOLD_SEED",
    "LAMBDAS",
    "POSITIVE",
    "SCHEMA",
    "SHIPPED",
    "THRESHOLD",
    "ProbeError",
    "auc",
    "choose_lambda",
    "features",
    "fit",
    "fit_ridge",
    "folds_of",
    "held_out",
    "irls",
    "manifest_path",
    "probabilities",
    "probe_dir",
    "probe_path",
    "read",
    "records_of",
    "regime_of",
    "score",
    "split",
    "standardize",
    "targets",
    "write",
    "write_manifest",
]
