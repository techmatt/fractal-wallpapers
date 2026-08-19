"""The proven channel: roots at the places a human already called good.

The parameter planes have no sampler — an unscreened draw over the higher degrees
measured zero good locations in a hundred and forty-four — so a plane root comes
from the tracked nucleus-grid pool, an explicit seed file, or a reframing of
somewhere the walk already reached. A dedicated mandelbrot leg tested a fourth
source and it beat all of them: **descend beside a location a human has scored a
keeper**. Over 95 active minutes the seeded roots put 91.6% of their finds over
the junk floor and half of the sample over the smooth head's advisory, where the
same run's never-walked plane-pool roots returned the partition's historic rate —
21 rows over the floor out of 333, one clearing.

That leg ran on a seed file built by hand and thrown away, which is the reason
this module exists. The seed set is not an artifact to keep: it is **a query over
the label store**, re-derived every time it is asked for, so a keeper labelled
this morning is a root this afternoon without anybody remembering to refresh a
file. Nothing here reads `data/labels` — the store's resolver is the one reader,
and it hands back one row per location with the latest verdict on it.

```text
the label store, resolved            one row per location, latest verdict wins
        │  score >= TIER_FLOOR, cast by a human, on a parameter plane
        ▼
    one seed row per location         id, family, viewport, tier, label batch
        │  best tier first; inside a tier, ordered by a digest of the location
        ▼
    a refill channel per plane        interleaved RATIO:1 with that plane's pool
```

## Why the order is a digest and not a shuffle

The refill's cursor walks the list in order and hands over the first entries
nobody has taken, so the order decides which proven places a short run actually
reaches. Two properties are wanted at once, and a seeded shuffle — what the
hand-built file used — has only the first:

* **spread**, so eight roots drawn in one refill are not eight frames of the same
  basin. Location-key order would hand over neighbours together;
* **stability under insertion**, so a label added today lands *in* the queue
  rather than re-shuffling every entry behind it.

The second one is about resuming. A killed run checkpoints its refill *cursor* —
an index — and re-derives this queue when it comes back, so anything that moves
the entries between the two moves what that index points at. Under a shuffle a
single new label re-deals the whole list and the cursor means nothing; ordered by
digest, one insertion ahead of the cursor costs one root served twice and one not
served, and everything else is where it was.

Sorting on a digest of the location key gives both, and it is the same on every
machine — unlike `hash`, and unlike a shuffle whose output moves when one element
is added. The id is that digest too, so a root's provenance names a place rather
than a position in a file that has since grown.

## What "proven" is a claim about, and what it is not

A human scored *this location* a keeper. It is not a claim about the frames below
it — the leg's own reject sample says nothing structural separates the finds that
clear the smooth head from the ones that do not — and it is not a claim the
channel can renew on its own. **The supply runs out at the rate the label store
grows**, which is the honest reading of a channel that feeds on its own past
output, and it is why the fresh pool is interleaved rather than displaced.

The tier floor is the currency's own bottom class, not a new cut: a class the
weights table pays for is a keeper, here as everywhere else.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import PARAMETER_PLANES, partition_of_family

#: The schema every derived seed row carries, from the first row.
SCHEMA = 1

#: What this channel is called wherever a root's provenance is read back.
CHANNEL = "proven"

#: The label class a location has to reach to become a root. The currency's
#: lowest paid class rather than a number of this module's own: a class the
#: weights table pays for is a keeper, and a second floor here would be a second
#: answer to what a keeper is.
TIER_FLOOR = min(money.CLASS_WEIGHT)

#: Proven roots handed over per root of the partition's other pool. The fresh
#: pool is interleaved rather than displaced because this channel feeds on the
#: label store's past output and cannot open new ground; crowding the pool out
#: would leave the run with no way to find anywhere a human has not been.
RATIO = 2

#: The partitions this channel serves. The parameter planes, and only them: the
#: dynamical families have screened `c`-pools of their own, and a plane is the
#: side with no sampler at all. A pool's entries are also of one shape per
#: partition, and the interleave below relies on that.
SERVED = PARAMETER_PLANES

#: Characters of the location digest an id carries. 48 bits over a corpus of a
#: few thousand locations; the digest is the sort key as well, so a collision
#: would be two rows in one place in the queue rather than a lost root.
ID_DIGITS = 12


def digest_of(key: tuple) -> str:
    """A stable digest of one location key, identical on every machine.

    `hash` is not: it is salted per process, so a queue ordered by it would come
    back in a different order on the next run of the same command.
    """
    text = json.dumps(key, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()


def seed_id(key: tuple) -> str:
    """The id one proven location is always known by."""
    return f"proven-{digest_of(key)[:ID_DIGITS]}"


def qualifies(row: dict, tier_floor: int) -> bool:
    """Whether one resolved label row is a proven root.

    Human verdicts only. A `rule:` row is a stated rule rather than somebody's
    taste, and this channel's whole claim is that a person looked at the place.
    """
    from fractal_wallpapers.labeling import store

    score = row.get("score")
    return score is not None and int(score) >= int(tier_floor) and row.get("origin") == store.HUMAN


def seed_row(row: dict, key: tuple) -> dict:
    """One label row as the seed row a walk can be rooted at."""
    return {
        "schema": SCHEMA,
        "id": seed_id(key),
        "family": row["family"],
        "viewport": row["viewport"],
        "provenance": {
            "channel": CHANNEL,
            "tier": int(row["score"]),
            "batch": row.get("batch"),
        },
    }


def derive(
    *,
    tier_floor: int = TIER_FLOOR,
    partitions=SERVED,
    label_paths=None,
    rows: list[dict] | None = None,
) -> dict:
    """Build the proven seed set from the label store. `{rows, record}`.

    Deterministic for a fixed store: no draw, no clock, and a total order that
    does not depend on the order the rows were read in.
    """
    from fractal_wallpapers.supply import census

    served = tuple(partitions)
    resolved = census.label_rows(label_paths) if rows is None else list(rows)
    kept: list[tuple[str, dict]] = []
    tiers: Counter = Counter()
    per_partition: Counter = Counter()
    for row in resolved:
        if not qualifies(row, tier_floor):
            continue
        # The key first: it is `None` for exactly the rows whose partition cannot
        # be resolved either, so nothing below has to handle an unregistered one.
        key = key_of_row(row)
        if key is None:
            continue
        partition = partition_of_family(row["family"])
        if partition not in served:
            continue
        kept.append((partition, seed_row(row, key)))
        tiers[int(row["score"])] += 1
        per_partition[partition] += 1

    # Best tier first, then the location's digest: see the module docstring.
    # The digest is already the tail of the id, so the sort reads it back rather
    # than recomputing it.
    kept.sort(key=lambda pair: (-pair[1]["provenance"]["tier"], pair[1]["id"]))
    ordered = [seed for _partition, seed in kept]
    return {
        "rows": ordered,
        "record": {
            "channel": CHANNEL,
            "tier_floor": int(tier_floor),
            "partitions": {p: per_partition.get(p, 0) for p in served},
            "tiers": {str(tier): tiers[tier] for tier in sorted(tiers, reverse=True)},
            "rows": len(ordered),
            "labels_read": len(resolved),
        },
    }


def by_partition(rows: list[dict], partitions=SERVED) -> dict[str, list[dict]]:
    """The derived rows split into the queues the refill draws from, in order."""
    out: dict[str, list[dict]] = {p: [] for p in partitions}
    for row in rows:
        partition = partition_of_family(row["family"])
        if partition in out:
            out[partition].append(row)
    return out


def interleave(proven: list, other: list, ratio: int = RATIO) -> list:
    """`ratio` proven entries per entry of the partition's other pool.

    One list, because the refill holds one cursor per partition — and one cursor
    is the right shape here rather than a limitation: what the interleave buys is
    that neither channel can be crowded out by the other, and two cursors served
    in whatever order a queue drains would decide that by accident.
    """
    step = max(1, int(ratio))
    out: list = []
    taken = given = 0
    while taken < len(proven) or given < len(other):
        out.extend(proven[taken : taken + step])
        taken += step
        if given < len(other):
            out.append(other[given])
            given += 1
    return out


def render(rows: list[dict]) -> str:
    """The seed set as a seed file's exact bytes."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write(rows: list[dict], path: Path) -> Path:
    """Emit the seed set, so it can be read, diffed, or passed as `--seeds`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(rows), encoding="utf-8", newline="\n")
    return path


def compare(rows: list[dict], path: Path) -> dict:
    """The derived set against a seed file, by location and not by id.

    Growth is expected and is the point — the store gains keepers and the channel
    gains roots. What needs an explanation is the other direction: a location the
    file had and a fresh derivation does not means a verdict was withdrawn,
    lowered, or is no longer readable, and none of those should pass unnoticed.
    """
    path = Path(path)
    if not path.is_file():
        return {"compared": False, "reason": f"{path} does not exist", "derived": len(rows)}
    theirs: dict[tuple, dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if (row.get("provenance") or {}).get("channel") != CHANNEL:
                continue
            key = key_of_row(row)
            if key is not None:
                theirs[key] = row
    ours = {key_of_row(row): row for row in rows}
    ours.pop(None, None)
    gained = [key for key in ours if key not in theirs]
    lost = [key for key in theirs if key not in ours]
    return {
        "compared": True,
        "file": str(path),
        "derived": len(ours),
        "in_file": len(theirs),
        "gained": len(gained),
        "lost": len(lost),
        "gained_tiers": dict(
            sorted(Counter(ours[key]["provenance"]["tier"] for key in gained).items())
        ),
        "gained_batches": dict(
            sorted(Counter(ours[key]["provenance"]["batch"] for key in gained).items())
        ),
        "lost_sample": [theirs[key].get("id") for key in lost[:10]],
    }


class ProvenChannel:
    """The proven roots each partition can still be handed, derived once per run.

    Derived at build rather than read from a file, and cached for the run's
    length rather than re-derived per draw: the store does not move while a
    harvest is running, and a channel that re-read it every refill would spend
    the loop's clock proving that.
    """

    def __init__(
        self,
        rows: list[dict],
        *,
        record: dict | None = None,
        ratio: int = RATIO,
        partitions=SERVED,
    ):
        self.ratio = int(ratio)
        self.record = dict(record or {})
        served = tuple(partitions)
        self._seeds = {p: rows for p, rows in by_partition(rows, served).items() if rows}
        #: The partitions this channel can serve, in registry order. A partition
        #: with no proven location yet is absent rather than empty: the refill
        #: asks this list whether a channel exists at all.
        self.partitions = tuple(p for p in served if p in self._seeds)

    def seeds(self, partition: str) -> list[dict]:
        """The proven roots for one partition, in the order they are handed over."""
        return self._seeds.get(partition, [])

    def pool(self, partition: str, other: list) -> list:
        """This partition's whole refill queue: proven interleaved with its pool."""
        return interleave(self.seeds(partition), list(other), self.ratio)

    def summary(self) -> dict:
        return {
            "channel": CHANNEL,
            "ratio": self.ratio,
            "tier_floor": self.record.get("tier_floor"),
            "seeds": {p: len(self._seeds[p]) for p in self.partitions},
            "tiers": self.record.get("tiers"),
        }


def build(
    *,
    tier_floor: int = TIER_FLOOR,
    partitions=SERVED,
    label_paths=None,
    rows: list[dict] | None = None,
    ratio: int = RATIO,
) -> ProvenChannel:
    """The channel a harvest holds, derived from the label store as it stands.

    `partitions` may be a run's whole partition list; what this channel serves is
    that list's intersection with the planes, because a run naming one partition
    should get the channel for that one and not for every plane in the registry.
    """
    served = tuple(p for p in partitions if p in SERVED)
    derived = derive(tier_floor=tier_floor, partitions=served, label_paths=label_paths, rows=rows)
    return ProvenChannel(derived["rows"], record=derived["record"], ratio=ratio, partitions=served)


__all__ = [
    "CHANNEL",
    "ID_DIGITS",
    "RATIO",
    "SCHEMA",
    "SERVED",
    "TIER_FLOOR",
    "ProvenChannel",
    "build",
    "by_partition",
    "compare",
    "derive",
    "digest_of",
    "interleave",
    "qualifies",
    "render",
    "seed_id",
    "seed_row",
    "write",
]
