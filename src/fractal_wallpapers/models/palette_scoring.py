"""A trained palette head over the real candidate sets: both readings, per set.

Scoring is a separate step from training and from judging, and the file between
them is the reason: a checkpoint scored once can be read a dozen ways — against
the teacher, against what the production run actually chose, per flavour, per
partition, a year later — without the model, the GPU or the render cache being
present.

**The unit of a row is a set**, not a candidate, because the unit of this head's
job is a set: a location arrives with a list of maps and one of them is chosen.
A row therefore carries the location, the candidate list in order, *both* score
vectors aligned to it, and the two picks. That is the whole join for the only
question anybody asks of this head, on one line.

Both readings are taken on **the same pictures** — this repository's renders of
the same candidates, through the same transform. The teacher is re-read here
rather than quoted from the source's records, and that is the difference between
comparing two functions and comparing two pipelines. What the source's own run
chose is carried too, as a third column, but it was chosen on a different
picture and it is never the thing the student is scored against.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.models import metrics, palette_corpus, palette_head, palette_sets

#: The schema every score row carries.
SCHEMA = 1


def scores_path(run: str | None = None) -> Path:
    """Where one run's read of the real sets is kept, tracked."""
    from fractal_wallpapers.models import palette_train

    return palette_train.head_dir(run) / "scores.jsonl"


def load(path: Path, device: str = "auto"):
    """Rebuild a palette head from its checkpoint. The config in the file decides how."""
    import torch

    from fractal_wallpapers.models import train

    where = train.device_of(device)
    saved = torch.load(path, map_location="cpu", weights_only=False)
    config = saved["config"]
    model = palette_head.build(backbone=config["backbone"], pretrained=False)
    model.load_state_dict({key: value.float() for key, value in saved["state_dict"].items()})
    return model.to(where).eval(), config, where


def paths_of(sets: list[dict]) -> tuple[list[Path], list[dict]]:
    """Every candidate picture of every set, flat, with the row that made it."""
    cyclic_maps = palette_sets.cyclic()
    out, rows = [], []
    for entry in sets:
        for colormap in entry["candidates"]:
            row = palette_sets.candidate_row(entry, colormap, cyclic_maps)
            rows.append(row)
            out.append(palette_corpus.crop_of(row))
    return out, rows


def read_both(root: Path, checkpoint: Path, device: str = "auto", log=print) -> list[dict]:
    """Score the vendored sets through the student and through the teacher."""
    from fractal_wallpapers.models import palette_teacher

    sets = palette_sets.read()
    paths, _ = paths_of(sets)
    absent = [path.name for path in paths if not path.is_file()]
    if absent:
        raise FileNotFoundError(
            f"{len(absent)} candidate pictures of the real sets are not in the render cache "
            f"(e.g. {absent[:3]}). Build them before scoring."
        )

    model, config, where = load(checkpoint, device)
    log(f"student {checkpoint.name} over {len(paths)} pictures in {len(sets)} sets")
    ours = palette_teacher.scored_with(model, paths, palette_head.Transform(train=False), where, 64)
    del model

    teacher, teacher_where = palette_teacher.load(root, device)
    identity = palette_teacher.identity(root)
    log(f"teacher {identity['name']} sha256 {identity['sha256'][:16]} over the same pictures")
    theirs = palette_teacher.score(teacher, paths, teacher_where)
    del teacher

    rows, cursor = [], 0
    for entry in sets:
        width = len(entry["candidates"])
        mine = ours[cursor : cursor + width]
        yours = theirs[cursor : cursor + width]
        cursor += width
        my_pick = palette_head.top_pick(mine)
        your_pick = palette_head.top_pick(yours)
        rows.append(
            {
                "schema": SCHEMA,
                "head": "palette",
                "run": config.get("run"),
                "set": entry["set"],
                "source_batch": entry["source_batch"],
                "partition": entry["partition"],
                "flavour": entry["flavour"],
                "family": entry["family"],
                "viewport": entry["viewport"],
                "render": entry["render"],
                "mode": entry["mode"],
                "curve": entry["curve"],
                "candidates": entry["candidates"],
                "score": [float(value) for value in mine],
                "teacher_score": [float(value) for value in yours],
                "pick": entry["candidates"][my_pick],
                "teacher_pick": entry["candidates"][your_pick],
                "recorded_pick": entry["chosen"],
                "agreed": bool(my_pick == your_pick),
                "spearman": metrics.spearman(mine, yours),
                "discordant_pairs": metrics.discordant_pairs(mine, yours),
                "regret": palette_head.regret(mine, yours),
                "teacher_spread": palette_head.spread(yours),
            }
        )
    if cursor != len(ours):
        raise ValueError(f"{cursor} candidates scored but {len(ours)} pictures were read")
    return rows


def run(root: Path, which: str = "best", device: str = "auto", into: str | None = None, log=print):
    """Score the real sets through one checkpoint, and write the rows."""
    from fractal_wallpapers.models import palette_train

    checkpoint = palette_train.checkpoint_path(which, into)
    rows = read_both(Path(root), checkpoint, device, log)
    path = scores_path(into)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({**row, "checkpoint": which}, ensure_ascii=False) + "\n")
    return {
        "head": "palette",
        "run": into,
        "checkpoint": str(checkpoint),
        "sets": len(rows),
        "candidates": sum(len(row["candidates"]) for row in rows),
        "wrote": str(path),
    }


def read(run: str | None = None, path: Path | None = None) -> list[dict]:
    """One run's scores, schema-checked."""
    path = scores_path(run) if path is None else Path(path)
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


__all__ = ["SCHEMA", "load", "paths_of", "read", "read_both", "run", "scores_path"]
