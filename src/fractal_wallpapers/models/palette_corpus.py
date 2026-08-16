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

## What a set is here, and how it is made hard on purpose

Thirty-two candidates — the size of a production set, not a compromise with it —
and **seventy per cent of the sets are near-ties by construction**.

A production set is one palette *flavour's* members: up to thirty-two maps that
already resemble each other, whose top two sit a twentieth of the set's own
spread apart. Two corpora have now been measured against that, and both times the
thing that failed was the fine distinction rather than the coarse one:

* 600 sets of 8, drawn uniformly, gave a head that reproduced the teacher's
  *order* at a rank correlation of 0.88 and its *top pick* 38% of the time;
* 800 sets of 20, drawn uniformly, moved that to 0.89 and 46% — and the median
  miss was the teacher's **second** favourite winning.

Widening a uniform draw only buys near-ties by accident. So they are bought on
purpose instead: a **hard** set is one map and the thirty-one nearest it in
[`palettes.space`], which measures how alike two gradients look as the renderer
spends them. Its members resemble each other for the same reason a flavour's
members do, and the whole library is covered because the anchors walk a seeded
permutation of the pool.

[`HARD_SHARE`] of the sets are built that way and the rest are uniform draws,
because a corpus of nothing but near-ties would teach a head to split hairs and
forget the shape of a preference — and the ordering arm, which passes, is a bar
too. The mix is declared before training and written into the split record.

What is matched is the *property*, not the partition: the flavour taxonomy is the
source project's own clustering over a library this repository holds a subset of,
and it is not reproduced here. The judged sets are still not the trained ones.

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
from fractal_wallpapers.palettes import space
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
#: bite. A partition that cannot supply its even share gives what it has and the
#: shortfall is spread over the ones that can. 2,000 of the 5,452 locations this
#: repository holds at [`FLOOR`] and above, which is what one afternoon of
#: rendering and four training runs fit into.
SETS = 2000

#: Candidates per set. Thirty-two, which is the size of a production candidate
#: set rather than an approach to it: 156 of the 377 vendored real sets hold
#: exactly this many and the rest are the flavours too small to. Affordable
#: because the field is dumped once per location, and trainable on eight
#: gigabytes because the batch is put through the net in halves.
CANDIDATES = 32

#: The share of sets built as palette-space neighbourhoods rather than uniform
#: draws. Declared here, before training, and carried into the split record.
#: Seventy per cent: enough that the head is mostly asked the fine question the
#: real sets ask, with 600 uniform sets left over — nearly the whole of the last
#: corpus — so the ordering arm has the population it was passing on.
HARD_SHARE = 0.70

#: The lowest human tier a location may be drawn at. A 2 has structure but is
#: unremarkable, and places like that do reach colorize — the source's own
#: colorize sheet is stratified from below a hundredth of a screen probability
#: upward. A 1 does not work as a picture at all, and asking which palette suits
#: it is asking about something nobody will render.
FLOOR = 2

#: Share of the corpus's locations held out, and it is drawn over locations so a
#: place's candidates cannot straddle the boundary.
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
    """One file per partition, which is the axis the draw is apportioned on.

    These are the repository's only tracked files over a mebibyte, and the size
    rule carries a named exemption for them rather than the corpus being split
    into numbered parts to fit under it — see `tests/test_history_purity.py`.
    """
    return row_dir() / f"{partition.replace(':', '_')}.jsonl"


def split_path() -> Path:
    return palette_sets.store_dir() / "split.json"


def held_out_path() -> Path:
    """The locations that have been on the held-out side and must stay there."""
    return palette_sets.store_dir() / "held_out.jsonl"


def carried_holdout() -> set[str]:
    """Every location a previous draw held out, as the repr of its location key.

    A corpus that grows must not grow into its own held-out side. The epoch this
    head ships at is chosen on the held-out distillation loss, and a location that
    was scoring that loss last time and is teaching the model this time makes the
    two readings incomparable in the one direction that flatters the second.

    So the held-out side is *data*, accumulated: the pin file names the locations,
    and it only ever gains rows. Locations it names that a later draw never picks
    are simply not in that corpus; nothing forces them back in.
    """
    path = held_out_path()
    if not path.is_file():
        return set()
    out = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise CorpusError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        out.add(repr(location_key(row["family"], row["viewport"])))
    return out


def pin_holdout(set_rows: list[dict]) -> dict:
    """Add this draw's held-out locations to the pin, and write it back."""
    known = carried_holdout()
    rows = []
    for row in set_rows:
        if row.get("side") != "holdout":
            continue
        key = repr(location_key(row["family"], row["viewport"]))
        if key in known:
            continue
        known.add(key)
        rows.append(
            {
                "schema": SCHEMA,
                "family": row["family"],
                "viewport": row["viewport"],
                "batch": row["batch"],
            }
        )
    path = held_out_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"pinned": len(known), "added": len(rows), "path": str(path)}


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


def anchors(pool: list[str], count: int, seed: int) -> list[str]:
    """Which map each hard set is built around: a seeded walk over the pool.

    A permutation rather than a draw with replacement, repeated as often as the
    count needs, so every map in the library anchors its own neighbourhood before
    any map anchors a second one. A corpus that sampled anchors independently
    would leave a tail of maps that never sat at the centre of a set.
    """
    generator = random.Random(f"anchors:{seed}")
    out: list[str] = []
    while len(out) < count:
        lap = list(pool)
        generator.shuffle(lap)
        out.extend(lap[: count - len(out)])
    return out


def draw(
    sets: int = SETS,
    candidates: int = CANDIDATES,
    seed: int = SEED,
    hard_share: float = HARD_SHARE,
) -> list[dict]:
    """The whole plan: which places, which maps, how hard, in which order.

    Seeded end to end. The locations are drawn per partition from a sorted list,
    so the draw is a function of the seed and the tracked corpus and of nothing
    else — not of a dictionary's iteration order and not of when it was run.

    A set is `hard` or `uniform`, and which it is is decided by position in the
    shuffled plan rather than by a coin: the first share of the plan is hard. The
    plan is already shuffled across partitions, so that is a random assignment
    with an exact realized share instead of an approximate one.
    """
    pool = palette_sets.pool()["pool"]
    if candidates > len(pool):
        raise CorpusError(f"a set of {candidates} cannot be drawn from a pool of {len(pool)}")
    if not 0.0 <= hard_share <= 1.0:
        raise CorpusError(f"a hard share of {hard_share} is not a share")

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

    hard = round(len(chosen) * hard_share)
    centres = anchors(pool, hard, seed)
    out = []
    for index, picked in enumerate(chosen):
        row = picked["row"]
        if index < hard:
            anchor = centres[index]
            members = space.neighbourhood(anchor, pool, candidates)
        else:
            anchor = None
            members = generator.sample(pool, candidates)
        out.append(
            {
                "schema": SCHEMA,
                "batch": BATCH,
                "set": f"{index:04d}",
                "seed": seed,
                "kind": "hard" if index < hard else "uniform",
                "anchor": anchor,
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
                "candidates": members,
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


def recolor_spec(row: dict, field: Path, output: Path) -> dict:
    """What the engine is told to colour a dumped field with, for one candidate.

    Everything geometric comes from the dump's own record — the grid, the place,
    the curve — so all that is named here is the map and how its gradient is
    spent. Which is exactly the axis a candidate set varies.
    """
    from fractal_wallpapers.paths import colormap_dir

    return {
        "schema": 1,
        "field": str(field),
        "colormap": row["colormap"],
        "colormap_dir": str(colormap_dir()),
        "palette": renders.spec_of(row, output)["palette"],
        "output": str(output),
    }


def build(set_rows: list[dict], limit: int | None = None, log: Path | None = None) -> dict:
    """Make every candidate picture that is not already on disk.

    **One iteration per location, not one per candidate.** A set's candidates are
    the same place through different maps, so the expensive stage — the escape-time
    field — is identical across all of them. The field is dumped once, every
    missing candidate is coloured off it, and the dump is thrown away: 0.22 s and
    then 0.042 s each, against 0.25 s each. On a corpus of twenty maps a location
    that is the difference between fourteen minutes and an hour.

    Nothing about the pictures changes. A recolor of a dumped field reproduces the
    render it came from **byte for byte** — the engine's own guarantee, and
    `tests/test_palette_corpus.py` holds it to that rather than taking it — so the
    cache is keyed on the same digest either way and a file made by one path is
    indistinguishable from one made by the other.
    """
    cyclic_maps = palette_sets.cyclic()
    crops = crop_dir()
    crops.mkdir(parents=True, exist_ok=True)
    log = log or log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    field = cache_dir() / "field.f32"

    wanted: list[tuple[dict, list[tuple[str, dict]]]] = []
    seen: set[str] = set()
    asked = 0
    for set_row in set_rows:
        missing = []
        for colormap in set_row["candidates"]:
            row = palette_sets.candidate_row(set_row, colormap, cyclic_maps)
            name = renders.job_name(row)
            asked += 1
            if name in seen or (crops / f"{name}.jpg").is_file():
                continue
            seen.add(name)
            missing.append((name, row))
        if missing:
            wanted.append((set_row, missing))
    needed = sum(len(missing) for _, missing in wanted)
    if limit is not None:
        trimmed, budget = [], limit
        for set_row, missing in wanted:
            if budget <= 0:
                break
            trimmed.append((set_row, missing[:budget]))
            budget -= len(missing[:budget])
        wanted = trimmed

    total = sum(len(missing) for _, missing in wanted)
    started = time.monotonic()
    rendered = fields = 0
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"--- build: {total} pictures over {len(wanted)} locations ---\n")
        handle.flush()
        for index, (_set_row, missing) in enumerate(wanted, start=1):
            first = missing[0][1]
            engine.run("dump-field", {**renders.spec_of(first, field), "output": str(field)})
            fields += 1
            for name, row in missing:
                engine.run("recolor", recolor_spec(row, field, crops / f"{name}.jpg"))
                rendered += 1
            if index % 25 == 0 or index == len(wanted):
                spent = time.monotonic() - started
                rate = spent / max(rendered, 1)
                handle.write(
                    f"location {index}/{len(wanted)}  pictures {rendered}/{total}  "
                    f"{rate:.3f}s each  {(total - rendered) * rate / 60:.1f} min left\n"
                )
                handle.flush()
    field.unlink(missing_ok=True)
    field.with_suffix(".json").unlink(missing_ok=True)

    seconds = time.monotonic() - started
    on_disk = sorted(crops.glob("*.jpg"))
    return {
        "schema": SCHEMA,
        "asked": asked,
        "pictures": total,
        "rendered": rendered,
        "fields": fields,
        "skipped": asked - needed,
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
    """Assign whole locations to `train` or `holdout`, seeded, honouring the pin.

    Over locations rather than over candidates: a place's candidates share a field
    and differ only in colour, so splitting them would put nearly the same picture
    on both sides of the boundary and report a held-out loss that is partly a
    training loss.

    Locations [`carried_holdout`] names are held out first and the seeded draw
    fills the rest of the share around them — see that function for why a corpus
    is not allowed to grow into its own held-out side.
    """
    places = sorted({repr(location_key(row["family"], row["viewport"])) for row in set_rows})
    pinned = carried_holdout() & set(places)
    wanted = max(1, round(len(places) * share))
    free = [place for place in places if place not in pinned]
    generator = random.Random(seed)
    generator.shuffle(free)
    held = set(pinned) | set(free[: max(0, wanted - len(pinned))])
    for row in set_rows:
        row["side"] = (
            "holdout" if repr(location_key(row["family"], row["viewport"])) in held else "train"
        )
    return {
        "schema": SCHEMA,
        "rule": (
            "a seeded draw over LOCATIONS, not over candidates: a place's candidates share "
            "one field and differ only in colour, so a split that let them straddle would "
            "report a held-out loss that is partly a training loss. Locations a previous "
            "draw held out are pinned to the held-out side and the draw fills around them"
        ),
        "seed": seed,
        "target_share": share,
        "locations": len(places),
        "held_out_locations": len(held),
        "carried_from_earlier_draws": len(pinned),
        "realized_share": len(held) / max(len(places), 1),
        "sets": {
            "train": sum(1 for row in set_rows if row["side"] == "train"),
            "holdout": sum(1 for row in set_rows if row["side"] == "holdout"),
        },
    }


def temperature(set_scores: list[list[float]]) -> float:
    """The scale a per-set softmax reads this corpus at: half a typical set's spread.

    The teacher's units mean nothing on their own — its scores here run from −77
    to 18 — so a listwise term cannot carry a constant temperature and mean the
    same thing. This is a rule instead of a number: the median within-set standard
    deviation, halved, so a candidate two deviations above its set's mean carries
    about `e**4` of the weight of an average one. That concentrates the term on
    the top handful of a set, which is where the misses are.

    Computed once from the labeled corpus and written into its split record, so
    the trainer reads a fact rather than recomputing a guess.
    """
    import numpy

    spreads = [
        float(numpy.std(numpy.asarray(scores, dtype=numpy.float64))) for scores in set_scores
    ]
    return float(numpy.median(spreads)) / 2.0


def mix(set_rows: list[dict]) -> dict:
    """The declared hard/uniform mix, realized and measured.

    The share is a decision; the *tightness* is the check on it. A hard set is
    meant to be a near-tie by construction, and the number that says whether it is
    is the mean palette-space distance between its members. Reported per kind and
    per side, so a corpus cannot claim a mix it does not have.
    """
    import numpy

    out: dict = {"declared_hard_share": HARD_SHARE, "kinds": {}}
    for kind in ("hard", "uniform"):
        group = [row for row in set_rows if row.get("kind") == kind]
        if not group:
            continue
        spreads = [space.tightness(row["candidates"])["mean"] for row in group]
        out["kinds"][kind] = {
            "sets": len(group),
            "share": len(group) / max(len(set_rows), 1),
            "palette_distance": {
                "mean": float(numpy.mean(spreads)),
                "median": float(numpy.median(spreads)),
            },
            "sides": {
                side: sum(1 for row in group if row.get("side") == side)
                for side in ("train", "holdout")
            },
            "distinct_candidate_sets": len({tuple(row["candidates"]) for row in group}),
        }
    out["maps_used"] = len({name for row in set_rows for name in row["candidates"]})
    return out


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
                "kind": set_row["kind"],
                "anchor": set_row["anchor"],
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

    directory = row_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # Cleared rather than overwritten: a re-draw can retire a partition or rename
    # a file, and a leftover from the last one would be read as corpus by
    # everything downstream — silently, because the reader globs the directory.
    for stale in directory.glob("*.jsonl"):
        stale.unlink()
    for partition, records in sorted(by_partition.items()):
        path = batch_path(partition)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        written[partition] = len(records)

    pin = pin_holdout(set_rows)
    width = len(set_rows[0]["candidates"]) if set_rows else 0
    per_set = [
        [float(value) for value in scores[start : start + width]]
        for start in range(0, width * len(set_rows), width)
    ]
    document = {
        **split,
        "batch": BATCH,
        "candidates_per_set": width,
        "listwise_temperature": temperature(per_set) if per_set else None,
        "mix": mix(set_rows),
        "teacher": identity,
        "pool": len(palette_sets.pool()["pool"]),
        "floor": FLOOR,
        "held_out_pin": pin,
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
        "mix": document["mix"],
        "teacher": {"name": identity["name"], "sha256": identity["sha256"]},
        "score": {
            "min": float(scores.min()),
            "median": float(sorted(scores)[len(scores) // 2]),
            "max": float(scores.max()),
        },
        "wrote": sorted(str(path) for path in row_dir().glob("*.jsonl"))
        + [str(split_path()), str(held_out_path())],
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
                "kind": row.get("kind", "uniform"),
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
    "HARD_SHARE",
    "HOLDOUT_SHARE",
    "SCHEMA",
    "SEED",
    "SETS",
    "CorpusError",
    "anchors",
    "apportion",
    "batch_path",
    "build",
    "cache_dir",
    "carried_holdout",
    "crop_dir",
    "crop_of",
    "draw",
    "grouped",
    "held_out_path",
    "label",
    "log_path",
    "mix",
    "pin_holdout",
    "plan_path",
    "read",
    "read_plan",
    "recolor_spec",
    "row_dir",
    "sides",
    "split_path",
    "supply",
    "temperature",
    "write_plan",
]
