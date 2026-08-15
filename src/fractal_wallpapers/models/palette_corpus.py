"""The distillation corpus: the teacher's opinion of pictures made here.

The teacher is a function, and a function can be asked as many questions as
anybody has patience for. So this corpus is not collected, it is **generated**:
draw locations, draw candidate maps, render every pair through this
repository's own engine, and write down what the teacher says about each. Every
row is machine-labeled and says so. Nothing here is a human verdict and none of
it goes near the three stores that hold them.

That is what makes the head regenerable. A checkpoint is a fact about a training
run; this corpus is the training run's whole input, in text, seeded, in the
history. If the head is ever retrained — a new backbone, a new loss, a bug found
in the loop — it is retrained on *this*, not on an approximation of it.

## The draw is the production input distribution, not parameter noise

Two axes, and both are sampled from what a release run really colours:

* **Locations** come from this repository's own label corpus, at the tiers that
  reach colorize — a place a human called unremarkable or better. Not from
  uniform noise over the plane: an unscreened draw over the parameter plane
  measured zero good locations in 144, and a palette head trained on what that
  produces would be an expert on pictures nothing will ever ask it about. The
  draw is apportioned across the **partitions** rather than following the
  corpus's own shape, so no partition is represented by a handful of places
  simply because it was cheap to label.
* **Maps** come from the shipped pool — [`palette_sets.pool`] — drawn without
  replacement inside a set.

Locations pinned to the location store's evaluation side are left out, and so is
every location the vendored production sets hold. The second is the one that
matters: a set the head trained on is not an instrument.

## What a set is here, and how it differs from a production one

Eight candidates, drawn uniformly from the whole pool. A production set is one
palette *flavour's* members — up to thirty-two maps that already resemble each
other — so it asks a harder question than a uniform draw does. That difference is
deliberate and declared rather than hidden: the flavour taxonomy is an artifact
of the source project's own clustering and does not exist here, and the head is
**judged** on the real sets, which is the direction an unmatched difference
should point. Training is the easier population; acceptance is the harder one.

## One row per candidate, and every row carries its whole join

The teacher's score *and* the location with every family constant *and* the
recipe that made the picture, on the same line. A row is enough to re-render its
own picture and re-ask the teacher about it. What is not on the row is folding —
that is read off the map, here as everywhere in this repository, because it is a
property of the map rather than of the render.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import pins, store
from fractal_wallpapers.models import palette_sets, renders
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply import partitions
from fractal_wallpapers.supply.location import location_key

#: The schema every record here carries.
SCHEMA = 1

#: What the corpus is called. One batch, because it is one seeded draw.
BATCH = "pool_draw_seeded"

#: The seed for every draw this module makes: the locations, the maps, the
#: order, and the held-out split.
SEED = 20260815

#: How many candidate sets to generate, before the per-partition supply caps
#: bite. Ten partitions and sixty each; a partition that cannot supply sixty
#: gives what it has and the shortfall is spread over the ones that can.
SETS = 600

#: Candidates per set. Eight is enough for the centred loss to have a stable
#: mean to remove, and a set is worth a set regardless — more maps at one place
#: buys less than the same renders spent at more places.
CANDIDATES = 8

#: The lowest human tier a location may be drawn at. A 2 has structure but is
#: unremarkable, and places like that do reach colorize — the source's own
#: colorize sheet is stratified from below a hundredth of a screen probability
#: upward. A 1 does not work as a picture at all, and asking which palette suits
#: it is asking about something nobody will render.
FLOOR = 2

#: Share of the corpus's locations held out, and it is drawn over locations so a
#: place's eight candidates cannot straddle the boundary.
HOLDOUT_SHARE = 0.20


class CorpusError(RuntimeError):
    """The corpus cannot be built from what is here."""


def cache_dir() -> Path:
    """Where the candidate pictures live. Ignored, and regenerable from the rows."""
    return repo_root() / "artifacts" / "palette"


def crop_dir() -> Path:
    return cache_dir() / "crops"


def plan_path() -> Path:
    return cache_dir() / "plan.jsonl"


def log_path() -> Path:
    return cache_dir() / "build.log"


def row_dir() -> Path:
    return palette_sets.store_dir() / "rows"


def batch_path(partition: str) -> Path:
    return row_dir() / f"{partition.replace(':', '_')}.jsonl"


def split_path() -> Path:
    return palette_sets.store_dir() / "split.json"


def supply() -> list[dict]:
    """Every location a candidate set may be drawn at, and why the rest are not.

    The label corpus at [`FLOOR`] and above, less two exclusions: places pinned
    to the location store's evaluation side, and every place the vendored
    production sets hold. The second is the instrument for this head and may
    never be taught; the first belongs to another head and is left alone on the
    same principle rather than because this head would spend it.
    """
    reserved = pins.pinned() | palette_sets.places()
    out = []
    for row in store.resolved().scored():
        if row["score"] < FLOOR:
            continue
        key = location_key(row["family"], row["viewport"])
        if key in reserved:
            continue
        out.append(row)
    return out


def apportion(available: dict[str, int], target: int) -> dict[str, int]:
    """How many sets each partition gets: an even share, capped by its supply.

    A partition that cannot fill its share gives what it has, and the shortfall
    is offered to the ones that can — repeatedly, because covering one shortfall
    can create another. `phoenix:classic` is the one that binds: its plane is a
    single pinned parameter point and the corpus holds two dozen places on it.
    """
    names = sorted(available)
    quota = {name: 0 for name in names}
    left = target
    while left > 0:
        room = [name for name in names if quota[name] < available[name]]
        if not room:
            break
        share = max(1, left // len(room))
        for name in room:
            take = min(share, available[name] - quota[name], left)
            quota[name] += take
            left -= take
            if left <= 0:
                break
    return quota


def draw(sets: int = SETS, candidates: int = CANDIDATES, seed: int = SEED) -> list[dict]:
    """The whole plan: which places, which maps, in which order.

    Seeded end to end. The locations are drawn per partition from a sorted list,
    so the draw is a function of the seed and the tracked corpus and of nothing
    else — not of a dictionary's iteration order and not of when it was run.
    """
    pool = palette_sets.pool()["pool"]
    if candidates > len(pool):
        raise CorpusError(f"a set of {candidates} cannot be drawn from a pool of {len(pool)}")

    by_partition: dict[str, list[dict]] = {}
    for row in supply():
        by_partition.setdefault(partitions.partition_of_family(row["family"]), []).append(row)
    quota = apportion({name: len(rows) for name, rows in by_partition.items()}, sets)

    generator = random.Random(seed)
    chosen: list[dict] = []
    for partition in sorted(by_partition):
        places = sorted(
            by_partition[partition],
            key=lambda row: repr(location_key(row["family"], row["viewport"])),
        )
        chosen.extend(
            {"partition": partition, "row": row}
            for row in generator.sample(places, quota[partition])
        )
    generator.shuffle(chosen)

    out = []
    for index, picked in enumerate(chosen):
        row = picked["row"]
        out.append(
            {
                "schema": SCHEMA,
                "batch": BATCH,
                "set": f"{index:04d}",
                "seed": seed,
                "partition": picked["partition"],
                "family": row["family"],
                "viewport": row["viewport"],
                "render": {
                    "resolution": list(palette_sets.RESOLUTION),
                    "supersample": palette_sets.SUPERSAMPLE,
                    "maxiter": int(row["render"]["maxiter"]),
                },
                "mode": palette_sets.MODE,
                "curve": palette_sets.CURVE,
                "candidates": generator.sample(pool, candidates),
                "location_score": int(row["score"]),
                "location_batch": row["batch"],
            }
        )
    return out


def write_plan(rows: list[dict]) -> Path:
    path = plan_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def read_plan() -> list[dict]:
    path = plan_path()
    if not path.is_file():
        raise CorpusError(f"{path} is missing — plan the corpus before building it")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def pictures(set_rows: list[dict], cyclic_maps: set[str]) -> list[tuple[str, dict]]:
    """`(name, row)` for every candidate of every set, one entry per picture.

    Two sets that draw the same map at the same place produce the same picture
    and share a file: the name is a digest of the whole spec, so the cache is
    keyed on what was rendered rather than on which set asked for it.
    """
    out = []
    for set_row in set_rows:
        for colormap in set_row["candidates"]:
            row = palette_sets.candidate_row(set_row, colormap, cyclic_maps)
            out.append((renders.job_name(row), row))
    return out


def build(set_rows: list[dict], limit: int | None = None, log: Path | None = None) -> dict:
    """Render every candidate that is not already on disk."""
    cyclic_maps = palette_sets.cyclic()
    jobs = pictures(set_rows, cyclic_maps)
    seen, unique = set(), []
    for name, row in jobs:
        if name not in seen:
            seen.add(name)
            unique.append((name, row))
    if limit is not None:
        unique = unique[:limit]

    crops = crop_dir()
    crops.mkdir(parents=True, exist_ok=True)
    log = log or log_path()
    log.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    rendered = skipped = 0
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"--- build: {len(unique)} pictures ---\n")
        handle.flush()
        for index, (name, row) in enumerate(unique, start=1):
            output = crops / f"{name}.jpg"
            if output.is_file():
                skipped += 1
                continue
            engine.run("render", renders.spec_of(row, output))
            rendered += 1
            if rendered % 100 == 0 or index == len(unique):
                spent = time.monotonic() - started
                rate = spent / max(rendered, 1)
                handle.write(
                    f"{index}/{len(unique)}  rendered {rendered}  skipped {skipped}  "
                    f"{rate:.3f}s each  {(len(unique) - index) * rate / 60:.1f} min left\n"
                )
                handle.flush()

    seconds = time.monotonic() - started
    on_disk = sorted(crops.glob("*.jpg"))
    return {
        "schema": SCHEMA,
        "asked": len(jobs),
        "pictures": len(unique),
        "rendered": rendered,
        "skipped": skipped,
        "seconds": round(seconds, 1),
        "seconds_each": round(seconds / rendered, 3) if rendered else None,
        "files": len(on_disk),
        "bytes": sum(path.stat().st_size for path in on_disk),
        "partial": limit is not None,
    }


def crop_of(row: dict) -> Path:
    """Where one candidate row's picture is, whether or not it has been made."""
    return crop_dir() / f"{renders.job_name(row)}.jpg"


def sides(set_rows: list[dict], seed: int = SEED, share: float = HOLDOUT_SHARE) -> dict:
    """Assign whole locations to `train` or `holdout`, seeded.

    Over locations rather than over candidates: a place's eight candidates share
    a field and differ only in colour, so splitting them would put nearly the
    same picture on both sides of the boundary and report a held-out loss that is
    partly a training loss.
    """
    places = sorted({repr(location_key(row["family"], row["viewport"])) for row in set_rows})
    generator = random.Random(seed)
    generator.shuffle(places)
    held = set(places[: max(1, round(len(places) * share))])
    for row in set_rows:
        row["side"] = (
            "holdout" if repr(location_key(row["family"], row["viewport"])) in held else "train"
        )
    return {
        "schema": SCHEMA,
        "rule": (
            "a seeded draw over LOCATIONS, not over candidates: a place's candidates share "
            "one field and differ only in colour, so a split that let them straddle would "
            "report a held-out loss that is partly a training loss"
        ),
        "seed": seed,
        "target_share": share,
        "locations": len(places),
        "held_out_locations": len(held),
        "realized_share": len(held) / max(len(places), 1),
        "sets": {
            "train": sum(1 for row in set_rows if row["side"] == "train"),
            "holdout": sum(1 for row in set_rows if row["side"] == "holdout"),
        },
    }


def label(root: Path, set_rows: list[dict], device: str = "auto", log=print) -> dict:
    """Ask the teacher about every candidate and write the rows it answered about."""
    from fractal_wallpapers.models import palette_teacher

    cyclic_maps = palette_sets.cyclic()
    rows: list[dict] = []
    for set_row in set_rows:
        for colormap in set_row["candidates"]:
            rows.append(palette_sets.candidate_row(set_row, colormap, cyclic_maps))
    paths = [crop_of(row) for row in rows]
    absent = [path.name for path in paths if not path.is_file()]
    if absent:
        raise CorpusError(
            f"{len(absent)} candidate pictures are not in the render cache (e.g. "
            f"{absent[:3]}). Build them before labeling: a corpus of the subset that "
            f"happened to be on disk is a corpus nobody can reproduce."
        )

    identity = palette_teacher.identity(root)
    log(f"teacher {identity['name']} sha256 {identity['sha256'][:16]} on {len(paths)} pictures")
    model, where = palette_teacher.load(root, device)
    began = time.time()
    scores = palette_teacher.score(model, paths, where)
    log(f"scored in {time.time() - began:.1f}s on {where}")

    split = sides(set_rows)
    written: dict[str, int] = {}
    by_partition: dict[str, list[dict]] = {}
    cursor = 0
    for set_row in set_rows:
        for colormap in set_row["candidates"]:
            row = palette_sets.candidate_row(set_row, colormap, cyclic_maps)
            record = {
                "schema": SCHEMA,
                "batch": set_row["batch"],
                "set": set_row["set"],
                "side": set_row["side"],
                "origin": "teacher",
                "score": float(scores[cursor]),
                "partition": set_row["partition"],
                **row,
                "location_score": set_row["location_score"],
                "teacher": identity["sha256"],
                "seed": set_row["seed"],
            }
            by_partition.setdefault(set_row["partition"], []).append(record)
            cursor += 1

    row_dir().mkdir(parents=True, exist_ok=True)
    for partition, records in sorted(by_partition.items()):
        path = batch_path(partition)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        written[partition] = len(records)

    document = {
        **split,
        "batch": BATCH,
        "candidates_per_set": len(set_rows[0]["candidates"]) if set_rows else 0,
        "teacher": identity,
        "pool": len(palette_sets.pool()["pool"]),
        "floor": FLOOR,
        "held_out_from": (
            "the vendored production candidate sets, whose locations are the instrument this "
            "head is judged on and may never be taught, and the location store's own "
            "evaluation pin"
        ),
    }
    split_path().write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {
        "rows": sum(written.values()),
        "sets": len(set_rows),
        "per_partition": written,
        "split": split,
        "teacher": {"name": identity["name"], "sha256": identity["sha256"]},
        "score": {
            "min": float(scores.min()),
            "median": float(sorted(scores)[len(scores) // 2]),
            "max": float(scores.max()),
        },
        "wrote": [str(batch_path(name)) for name in sorted(written)] + [str(split_path())],
    }


def read() -> list[dict]:
    """Every labeled row, schema-checked, in a stable order."""
    directory = row_dir()
    if not directory.is_dir():
        raise CorpusError(f"{directory} is missing — build and label the corpus first")
    rows = []
    for path in sorted(directory.glob("*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise CorpusError(f"{path}:{number}: schema {row.get('schema')!r}, expected 1")
            rows.append(row)
    rows.sort(key=lambda row: (row["set"], row["colormap"]))
    return rows


def grouped(rows: list[dict] | None = None) -> list[dict]:
    """The rows folded back into sets: `{set, side, candidates, scores, rows}`."""
    rows = read() if rows is None else rows
    out: dict[str, dict] = {}
    for row in rows:
        entry = out.setdefault(
            row["set"],
            {
                "set": row["set"],
                "side": row["side"],
                "partition": row["partition"],
                "candidates": [],
                "scores": [],
                "rows": [],
            },
        )
        entry["candidates"].append(row["colormap"])
        entry["scores"].append(row["score"])
        entry["rows"].append(row)
    return [out[key] for key in sorted(out)]


__all__ = [
    "BATCH",
    "CANDIDATES",
    "FLOOR",
    "HOLDOUT_SHARE",
    "SCHEMA",
    "SEED",
    "SETS",
    "CorpusError",
    "apportion",
    "batch_path",
    "build",
    "cache_dir",
    "crop_dir",
    "crop_of",
    "draw",
    "grouped",
    "label",
    "log_path",
    "pictures",
    "plan_path",
    "read",
    "read_plan",
    "row_dir",
    "sides",
    "split_path",
    "supply",
    "write_plan",
]
