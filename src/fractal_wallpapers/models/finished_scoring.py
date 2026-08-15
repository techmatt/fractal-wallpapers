"""A trained finished-render judge over a population: probabilities per picture.

Scoring is a separate step from training and from judging, and the file between
them is the reason: a checkpoint scored once can be read a dozen ways — at either
boundary, per mode, against another project's numbers, a year later — without the
model, the GPU or the render cache being present.

**A score row carries its join**, the same rule the stores hold. The
probabilities *and* the place *and* the whole recipe that made the picture, on
one line. It also carries the picture's own name, which is a digest of that
recipe, so a reader can find the file without recomputing anything and a row
whose recipe was edited afterwards would no longer name it.

**Every cutpoint is written, not just the scalar**, and they are unconditional —
the running product of what CORN trained. Reading the raw sigmoids instead cost
the location head seven points of AUC at its release cutpoint, measured; the same
reading is used on both sides of every comparison here.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import finished_train, head, renders, train

#: The schema every score row carries.
SCHEMA = 1


def scores_path(head_name: str, run: str | None = None) -> Path:
    """Where one run's read of a sheet is kept, tracked."""
    return finished_train.head_dir(head_name, run) / "scores.jsonl"


def load(path: Path, device: str = "auto"):
    """Rebuild a judge from its checkpoint. The config in the file decides how."""
    import torch

    where = train.device_of(device)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    model = head.build(
        num_classes=int(config["classes"]), backbone=config["backbone"], pretrained=False
    )
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


def run(
    head_name: str,
    which: str = "best",
    side: str = "eval",
    device: str = "auto",
    into: str | None = None,
    log=train.say,
) -> dict:
    """Score one side of a judge's corpus through a checkpoint, and write the rows."""
    import numpy

    head_name = finished.head_of(head_name)
    checkpoint = finished_train.checkpoint_path(head_name, which, into)
    model, config, where = load(checkpoint, device)
    transform = head.Transform(
        tuple(config["mean"]), tuple(config["std"]), config["interpolation"], train=False
    )

    known = finished.registry(head_name)
    rows = finished.resolved(head_name).scored()
    from fractal_wallpapers.labeling import registry as registry_module

    wanted = []
    for row in rows:
        pinned = registry_module.lookup(known, row["batch"]).eval_only
        # The selection slice is training-side material, so `side="train"` means
        # every picture the head could have learned from.
        if (side == "eval") == bool(pinned):
            wanted.append(row)
    if not wanted:
        raise ValueError(f"no pictures on side {side!r}")

    names = [renders.job_name({**row, "_head": head_name}) for row in wanted]
    crops = renders.crop_dir(head_name)
    paths = [crops / f"{name}.jpg" for name in names]
    absent = [name for name, path in zip(names, paths, strict=True) if not path.is_file()]
    if absent:
        raise FileNotFoundError(
            f"{len(absent)} pictures of the {side} side are not in the render cache "
            f"(e.g. {absent[:3]}). Build it before scoring."
        )
    log(f"scoring {len(wanted)} pictures on the {side} side through {checkpoint.name}")

    classes = int(config["classes"])
    probabilities = train.score(model, paths, transform, where, classes, config)

    path = scores_path(head_name, into)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row, name, probability in zip(wanted, names, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "head": head_name,
                "run": into,
                "checkpoint": which,
                "name": name,
                "batch": row["batch"],
                "score": row["score"],
                "side": side,
                "partition": row.get("partition"),
                "family": row["family"],
                "viewport": row["viewport"],
                "mode": row["mode"],
                "mode_params": row.get("mode_params") or {},
                "curve": row["curve"],
                "colormap": row["colormap"],
                "recipe": row["recipe"],
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            record["rank_score"] = float(numpy.sum(probability))
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "head": head_name,
        "run": into,
        "checkpoint": str(checkpoint),
        "which": which,
        "side": side,
        "pictures": len(wanted),
        "wrote": str(path),
    }


def read(path: Path | None = None, head: str = "", run: str | None = None) -> list[dict]:
    """One run's scores, schema-checked."""
    path = scores_path(head, run) if path is None else Path(path)
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


__all__ = ["SCHEMA", "load", "read", "run", "scores_path"]
