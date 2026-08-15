"""The training tiles: which locations, and the record of what was made of them.

The engine owns the *recipe* — how many tiles a location gets, how far each may
be shifted and zoomed, which reconstruction and which quality it draws. This
module owns the *population*: which locations are in the build, what each one is
worth as a training example, and which side of the evaluation boundary it is on.
Splitting it there means no constant is written down twice. The engine's report
carries the realized recipe back, and it is that report — not a restatement of it
here — that lands in the plan record.

## A location's id is derived from the location

Every draw in the fan-out is seeded by `(seed tag, location id, slot)`, so the id
is part of what a tile *is*. If it were a row number, adding one label to the
corpus would renumber everything after it and reshuffle the palette of every tile
in the build — a re-render of the whole corpus for a reason nobody would think to
look for. So the id is a digest of the location's own coordinate: a location
keeps its tiles forever, and two builds a year apart agree about every location
they share.

## The plan is shuffled, and the shuffle is what makes a prefix honest

Sorted by coordinate, the plan runs family by family and the deep, expensive
material lands contiguously. Any bounded rehearsal would then measure the cheap
end and project the whole build from it. A seeded shuffle makes every prefix a
fair sample of the whole, which is what lets `--limit` be a measurement rather
than a warm-up.

## Two files, written together

`plan.jsonl` is what the engine reads: a location, its frame, nothing else.
`locations.jsonl` is what the trainer reads: the same locations with their label,
their side, their partition and their group. They are written by one function
from one pass over the store, because a plan and a training manifest that
disagree about which location is which is the failure mode that survives every
test until the numbers come out wrong.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from fractal_wallpapers import engine
from fractal_wallpapers.labeling import groups as group_module
from fractal_wallpapers.labeling import pins, store
from fractal_wallpapers.labeling import registry as registry_module
from fractal_wallpapers.paths import colormap_dir, repo_root
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import partition_of_row

#: The schema every record here carries.
SCHEMA = 1

#: Names the fan-out. It is mixed into every draw, so changing it reshuffles the
#: palette, framing, reconstruction and quality of all 362,000 tiles — which is a
#: fresh build of the corpus, not a configuration change.
SEED_TAG = "location-tiles-v1"

#: The seed the plan's shuffle is drawn under.
PLAN_SEED = 0


def tile_dir() -> Path:
    """Where a build's records and pictures go. Rebuildable, so never tracked."""
    return repo_root() / "artifacts" / "tiles"


def plan_path() -> Path:
    """The engine's input: one location per line."""
    return tile_dir() / "plan.jsonl"


def locations_path() -> Path:
    """The trainer's input: the same locations, with what they are worth."""
    return tile_dir() / "locations.jsonl"


def manifest_path() -> Path:
    """The engine's output: one line per tile written."""
    return tile_dir() / "manifest.jsonl"


def cache_root() -> Path:
    """Where the tiles themselves land."""
    return tile_dir() / "cache"


def build_record_path() -> Path:
    """What the build was: the population, the realized recipe, the clock."""
    return tile_dir() / "build.json"


def pool_path() -> Path:
    """The palette axis, as tracked data."""
    return repo_root() / "data" / "tiles" / "palette_pool.json"


def palette_pool() -> dict:
    """The colormaps a tile may draw, and the floor that reserves the low slots."""
    return json.loads(pool_path().read_text(encoding="utf-8"))


def location_id(key: tuple) -> int:
    """A stable id for one location, derived from the coordinate itself.

    Fifty-two bits of a BLAKE2b digest over the canonical key. Fifty-two because
    that is what every JSON reader carries exactly, and the id travels through
    JSON on both sides of the engine boundary; a value that a parser silently
    rounds is an id that silently collides. Collisions are checked at plan time
    rather than argued about here.
    """
    digest = hashlib.blake2b(json.dumps(key).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") & ((1 << 52) - 1)


def plan(rows: list[dict], known: dict | None = None, seed: int = PLAN_SEED) -> list[dict]:
    """Turn resolved label rows into the build's population, shuffled.

    Every row that carries a location and a score is in it. A location the head
    may not train on is *still* in the build — it has to be scored through the
    same pictures every other location is scored through, or the evaluation is
    measuring the render as well as the head.
    """
    known = store.registry() if known is None else known
    scored = [row for row in rows if row.get("score") is not None and key_of_row(row) is not None]
    grouping = group_module.assign(scored)
    pinned = pins.pinned()

    out = []
    seen: dict[int, tuple] = {}
    for index, row in enumerate(scored):
        key = key_of_row(row)
        identifier = location_id(key)
        if identifier in seen and seen[identifier] != key:
            raise ValueError(
                f"two locations share the id {identifier}: {seen[identifier]!r} and {key!r}. "
                "The id is a digest of the coordinate, so a collision means two different "
                "places would share a tile directory and half the pictures would be of the "
                "wrong one."
            )
        seen[identifier] = key
        batch = str(row.get("batch"))
        out.append(
            {
                "schema": SCHEMA,
                "location_id": identifier,
                "family": row["family"],
                "viewport": row["viewport"],
                "score": int(row["score"]),
                "side": pins.EVAL if key in pinned else pins.TRAIN,
                "partition": partition_of_row(row),
                "group": grouping.of_row[index],
                "batch": batch,
                # A batch drawn with a model's score in the loop, or served on a
                # page that prefilled one, is worth less as evidence about the
                # world — the sampler reads this and nothing else does.
                "biased": not registry_module.eval_eligible(known, batch),
            }
        )
    random.Random(seed).shuffle(out)
    return out


def write_plan(population: list[dict]) -> tuple[Path, Path]:
    """Write the engine's plan and the trainer's manifest. Returns both paths."""
    plan_file, locations_file = plan_path(), locations_path()
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    with plan_file.open("w", encoding="utf-8", newline="\n") as handle:
        for row in population:
            handle.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "location_id": row["location_id"],
                        "family": row["family"],
                        "viewport": row["viewport"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    with locations_file.open("w", encoding="utf-8", newline="\n") as handle:
        for row in population:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return plan_file, locations_file


def read_locations(path: Path | None = None) -> list[dict]:
    """The trainer's manifest, schema-checked."""
    path = locations_path() if path is None else Path(path)
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise ValueError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        rows.append(row)
    return rows


def spec(limit: int | None = None) -> dict:
    """The build spec the engine reads.

    States the population and the palette axis and nothing else: every geometric
    constant of the recipe is the engine's own default, so this cannot drift
    away from what the tiles were actually made with.
    """
    pool = palette_pool()
    return {
        "schema": SCHEMA,
        "locations": str(plan_path()),
        "out_root": str(cache_root()),
        "manifest": str(manifest_path()),
        "colormap_dir": str(colormap_dir()),
        "seed_tag": SEED_TAG,
        "recipe": {
            "palette_pool": pool["draw"],
            "floor_palette": [[name, count] for name, count in pool["floor"]],
        },
        **({"limit": limit} if limit is not None else {}),
    }


def build(limit: int | None = None, log: Path | None = None) -> dict:
    """Run the engine over the plan and return its report."""
    return engine.tiles(spec(limit), log=log)


def read_manifest(path: Path | None = None) -> list[dict]:
    """Every tile row of a build.

    Read whole rather than streamed: the corpus-wide manifest is a third of a
    million rows and the trainer needs all of them grouped by location before it
    can hand out a single example.
    """
    path = manifest_path() if path is None else Path(path)
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def tiles_by_location(rows: list[dict]) -> dict[int, list[dict]]:
    """Group manifest rows by location, each location's tiles in slot order."""
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(int(row["location_id"]), []).append(row)
    for tiles in grouped.values():
        tiles.sort(key=lambda row: int(row["tile"]))
    return grouped


#: The tile every location is guaranteed to own, and the one a deployed judge is
#: handed: the canonical framing, the deploy colormap, antialiased, at the
#: engine's own JPEG quality. It is slot 0 by the recipe's floor, and it is
#: pinned rather than drawn — see the engine's `tiles` module.
CANONICAL_SLOT = 0


def canonical_of(tiles: list[dict]) -> dict:
    """The canonical view among a location's tiles.

    Refuses rather than substituting. A location whose canonical tile is missing
    is a location the evaluation cannot score the way it will be scored in
    production, and an aliased or reframed stand-in would be a quieter version of
    the same wrong answer.
    """
    for row in tiles:
        if int(row["tile"]) == CANONICAL_SLOT:
            if row["level"] != "antialiased" or row["scale"] != 1.0 or row["shift_frac"] != 0.0:
                raise ValueError(
                    f"location {row['location_id']}: slot {CANONICAL_SLOT} is not the canonical "
                    f"view ({row['level']}, scale {row['scale']}, shift {row['shift_frac']}). "
                    "The recipe pins that slot; a build where it is a draw has no deploy view."
                )
            return row
    raise ValueError("this location has no canonical tile")


__all__ = [
    "CANONICAL_SLOT",
    "PLAN_SEED",
    "SCHEMA",
    "SEED_TAG",
    "build",
    "build_record_path",
    "cache_root",
    "canonical_of",
    "location_id",
    "locations_path",
    "manifest_path",
    "palette_pool",
    "plan",
    "plan_path",
    "pool_path",
    "read_locations",
    "read_manifest",
    "spec",
    "tile_dir",
    "tiles_by_location",
    "write_plan",
]
