"""The four shipped judges, as a reader calls them on a picture or a place.

Every leg in this project scores inside its own loop — a hunt scores what it
renders, `gallery-grade score-pool` scores the pool, a harvest scores what it
admits — and none of those is a door a person can hand one picture to. This is
that door, for `judges score` and `judges check`, and it adds no scoring of its
own: each head is loaded and read exactly the way its production caller reads it.

* `render` reads a picture stretched to 384x224 (`render_train.load_checkpoint`) and
  returns `P(>=2..4)`.
* `gallery_grade` reads the same, three seeds averaged
  (`gallery_grade_train.load_shipped`), and returns `P(>=2..4)`.
* `palette` reads a picture squashed to 224x224 (`palette_scoring.load`) and returns
  one scalar, comparable only inside one place's set of palettes.
* `location` reads a PLACE: it renders the place's own 640x360ss2 smooth view
  (`discovery.scoring.LocationScorer`) and returns `P(>=3)` and `P(>=4)`.

**The geometry they were fit on.** The render and gallery judges were trained and
deployed on the 640x360 candidate pictures a hunt writes (2x supersampled), and the
gallery judge's labels on 1280x720 renders of the same recipes; both stretch the
whole frame to 384x224 with no crop. A picture of another aspect is stretched too,
so a 16:9 picture is the only kind whose score means what a gallery's does. The
palette judge reads 640x360 pictures squashed to 224x224. The location judge never
reads a picture you hand it: it draws the place's own view.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

#: The judges a picture can be handed to, in the order a table prints them.
PICTURE_JUDGES = ("render", "gallery_grade", "palette")

#: Every judge, the location one last because it reads a place.
JUDGES = (*PICTURE_JUDGES, "location")

#: Batch sizes, each the one its production caller reads at.
BATCH = {"render": 32, "gallery_grade": 32, "palette": 64, "location": 64}


@dataclass
class Loaded:
    """One judge, ready: the model(s), its config, the device, and what loading cost."""

    name: str
    models: list
    config: dict
    where: str
    seconds: float


def load(name: str, device: str = "auto") -> Loaded:
    """Load one shipped judge. Raises `FileNotFoundError` without its weights."""
    from fractal_wallpapers.models import ship

    started = time.perf_counter()
    if name == "render":
        from fractal_wallpapers.curation import floors
        from fractal_wallpapers.models import render_train

        path = ship.shipped_path(floors.SCORING_HEAD)
        _need(path)
        model, config, where = render_train.load_checkpoint(path, device)
        models = [model]
    elif name == "gallery_grade":
        from fractal_wallpapers.models import gallery_grade_train

        _need(gallery_grade_train.shipped_path())
        models, config, where = gallery_grade_train.load_shipped(device=device)
    elif name == "palette":
        from fractal_wallpapers.models import palette_scoring

        path = ship.shipped_path("palette")
        _need(path)
        model, config, where = palette_scoring.load(path, device)
        models = [model]
    else:
        raise ValueError(f"{name!r} is not a picture judge; one of {', '.join(PICTURE_JUDGES)}")
    return Loaded(name, list(models), dict(config), str(where), time.perf_counter() - started)


def _need(path: Path) -> None:
    if not Path(path).is_file():
        raise FileNotFoundError(
            f"{path} is not on this machine. Run `fractal-wallpapers fetch-weights` first."
        )


def score_pictures(judge: Loaded, pictures: list[Path]) -> list[dict]:
    """One row per picture, in order. Probabilities for the ordinal judges, a scalar for
    the palette judge."""
    from fractal_wallpapers.models import head, train

    paths = [Path(picture) for picture in pictures]
    if not paths:
        return []
    if judge.name == "palette":
        from fractal_wallpapers.models import palette_head, palette_teacher

        values = palette_teacher.scored_with(
            judge.models[0],
            paths,
            palette_head.Transform(train=False),
            judge.where,
            batch_size=BATCH["palette"],
        )
        return [{"score": round(float(value), 6)} for value in values]
    config = judge.config
    transform = head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
        target=tuple(config.get("target_dims") or (head.TARGET_WIDTH, head.TARGET_HEIGHT)),
    )
    recipe = {**config, "batch_size": BATCH[judge.name]}
    classes = int(config["classes"])
    if len(judge.models) == 1:
        read = train.score(judge.models[0], paths, transform, judge.where, classes, recipe)
    else:
        read = train.score_many(judge.models, paths, transform, judge.where, classes, recipe)
        read = read.mean(axis=0)
    return [
        {f"p_ge{index + 2}": round(float(value), 6) for index, value in enumerate(row)}
        for row in read
    ]


def score_places(records: list[dict], device: str = "auto", log=print) -> tuple[list[dict], float]:
    """The location judge over location records `{family, viewport[, maxiter]}`.

    Returns `(rows, load seconds)`; each row is `{p_ge3, p_ge4, error, view}`. The
    judge renders each place's own 640x360ss2 view, cached by recipe digest.
    """
    from fractal_wallpapers import locations
    from fractal_wallpapers.discovery.scoring import LocationScorer

    started = time.perf_counter()
    scorer = LocationScorer(device=device, batch_size=BATCH["location"], regime=None, log=log)
    loaded = time.perf_counter() - started
    asked = [
        {
            "family": record["family"],
            "viewport": record["viewport"],
            "maxiter": int(record.get("maxiter") or locations.maxiter_of(record)),
        }
        for record in records
    ]
    out = []
    for reading in scorer.read(asked):
        out.append(
            {
                "p_ge3": None if reading.score is None else round(float(reading.score), 6),
                "p_ge4": None if reading.great is None else round(float(reading.great), 6),
                "error": reading.error,
                "view": None if reading.view is None else str(reading.view),
            }
        )
    return out, loaded
