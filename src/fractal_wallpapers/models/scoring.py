"""A trained head over a population: one row of probabilities per location.

Scoring is a separate step from training and from judging, and the file between
them is the reason. A checkpoint scored once can be read a dozen ways — pooled,
per partition, against another project's numbers, a year later — without the
model, the GPU or the tile cache being present. Folding the read into the trainer
would mean re-training to re-read.

**A score row carries its join**, the same rule the label store holds: the
probabilities *and* the family with every constant *and* the viewport, on one
line. A row keyed on an id whose meaning lives somewhere else is orphaned the day
that file moves, and the source project lost three hundred and seventy-nine hand
labels exactly that way.

**Every cutpoint is written, not just the scalar.** `P(≥3)` and `P(≥4)` are
different questions — one is "is this a wallpaper", the other is "is this worth
releasing" — and the supply engine's ten-fold weighting reads the second one
directly. A file that only carried the summed rank score would answer neither.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.models import dataset, head, train
from fractal_wallpapers.models import tiles as tile_module

#: The schema every score row carries.
SCHEMA = 1


def scores_path(name: str = "location", run: str | None = None) -> Path:
    """Where one run's read of the evaluation side is kept, tracked."""
    return train.head_dir(name, run) / "scores.jsonl"


def _relative(path: str) -> str:
    """A tile path as a tracked record may carry it: relative, forward slashes.

    The score file is tracked, and a tracked file that names one machine's drive
    letter and home directory means nothing on the machine that reads it next.
    """
    from fractal_wallpapers.paths import repo_root

    try:
        return Path(path).resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def load(path: Path, device: str = "auto"):
    """Rebuild a head from its checkpoint. The config in the file decides how.

    Nothing here names an architecture: a checkpoint that could only be loaded by
    code that already knew what it was is a checkpoint that stops loading the day
    the default changes.
    """
    import torch

    where = train.device_of(device)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    model = head.build(
        num_classes=int(config["classes"]),
        backbone=config["backbone"],
        pretrained=False,
    )
    model.load_state_dict({k: v.float() for k, v in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


def transform_of(config: dict):
    """The deploy transform this checkpoint was trained to be read through."""
    return head.Transform(
        tuple(config["mean"]),
        tuple(config["std"]),
        config["interpolation"],
        train=False,
    )


def run(
    name: str = "location",
    which: str = "best",
    side: str = pins.EVAL,
    device: str = "auto",
    into: str | None = None,
    log=train.say,
) -> dict:
    """Score one side of the build through a checkpoint, and write the rows."""
    import numpy

    checkpoint = train.checkpoint_path(name, which, into)
    model, config, where = load(checkpoint, device)
    transform = transform_of(config)

    rows = tile_module.read_locations()
    grouped = tile_module.tiles_by_location(tile_module.read_manifest())
    locations = dataset.join(rows, grouped)
    dataset.assign_selection(locations)
    by_id = {int(row["location_id"]): row for row in rows}

    wanted = [
        location
        for location in locations
        # The selection slice is training-side material; `side="train"` means
        # every location the head learned from, the slice included.
        if location.side == side or (side == pins.TRAIN and location.side == dataset.SELECTION)
    ]
    if not wanted:
        raise ValueError(f"no locations on side {side!r}")
    log(f"scoring {len(wanted)} locations on the {side} side through {checkpoint.name}")

    paths = [location.canonical() for location in wanted]
    probabilities = train.score(
        model, paths, transform, where, int(config["classes"]), {"batch_size": 64}
    )

    path = scores_path(name, into)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for location, probability in zip(wanted, probabilities, strict=True):
            source = by_id[location.location_id]
            row = {
                "schema": SCHEMA,
                "head": name,
                "run": into,
                "checkpoint": which,
                "location_id": location.location_id,
                "family": source["family"],
                "viewport": source["viewport"],
                "score": location.score,
                "side": side,
                "partition": location.partition,
                "group": location.group,
                "batch": location.batch,
                "canonical_tile": _relative(tile_module.canonical_of(location.tiles)["path"]),
            }
            for index in range(int(config["classes"]) - 1):
                row[f"p_{head.cutpoint_label(index)}"] = float(probability[index])
            row["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "head": name,
        "run": into,
        "checkpoint": str(checkpoint),
        "which": which,
        "side": side,
        "locations": len(wanted),
        "wrote": str(path),
    }


def read(path: Path | None = None, name: str = "location", run: str | None = None) -> list[dict]:
    """One run's scores, schema-checked."""
    path = scores_path(name, run) if path is None else Path(path)
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


__all__ = ["SCHEMA", "load", "read", "run", "scores_path", "transform_of"]
