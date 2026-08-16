"""Which locations curation is offered, and in what order.

A release starts from everything every walk has ever found. This module turns
that union into an ordered offer — best first, per partition — and it answers
exactly one question plus the supply arithmetic that question implies. It does
not decide how many pictures to make ([`budget`]), it does not choose a palette
([`colorize`]), and it does not select a release ([`selection`]).

## The order is read at the moment it is used, and nothing is frozen

A ledger row records what a walk *found*: the gates it passed, its frame, its
family. It does not record a verdict about quality, because the walks that filled
these ledgers ran before any head existed — every row in them carries a null
score from the null scorer. So the score is a separate, re-runnable read
([`score`]), kept in a sidecar this module owns, and the ranking is `P(≥3)`
descending at read time.

**The ledgers are never rewritten.** A score written back into a ledger is a
verdict frozen on the day it was minted; when the head that produced it is
retrained the pipeline has to either believe a stale number or delete the row.
Both have happened, and the second one is worse: a head flip once took an intake
from about fourteen hundred locations to sixteen. Here a flip is a re-score of
the sidecar, the ledgers are untouched, and an old score degrades the *rank
quality* of a row rather than removing it.

## One reader, and it is the one the supply engine already has

`supply.ledgers.admitted_union` is the single union walk over every ledger: it
checks the schema, deduplicates on location identity rather than on a row id
(the ledgers overlap, and two runs mint the same node id for different places),
and reports what it could not key. Curation reaches it with its own predicate —
**structural gates only** — because admission at the walk's own good floor is a
different question from admission to a colorize, and asking the union for one
while meaning the other is how a population and its denominator come apart.

## The one enforcing cut, and the two numbers beside it

The junk floor acts, here, at the one site that draws the colorize pool. What
comes with it is arithmetic rather than judgement:

* [`emit_cap`] — a partition may release at most a quarter of its floor-passing
  supply, so a thin partition ships nothing rather than its own least-bad row;
* [`slots`] — the release mix apportioned into whole slots, with a guaranteed
  floor of one for any partition that has something worth keeping. Both go
  through `supply.apportion`, which already owns the largest-deficit rule and the
  guarantee fixed point; a second copy here would be a second answer.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import floors
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply import apportion, ledgers, release_mix
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import partition_of_row

#: The schema every score row carries.
SCHEMA = 1

#: The picture a location is judged on, pre-colour: the **canonical tile's** own
#: recipe. The location head is trained on those tiles and reads slot zero of
#: each location at deploy, so a curation intake that scored a different picture
#: would be asking a head about a distribution nobody trained it on.
#:
#: Measured rather than assumed: a plain render at this geometry differs from the
#: cached canonical tile of the same location by 0.02–0.77 of a channel level on
#: this repository's own tile cache, against a JPEG re-compression floor an order
#: of magnitude larger. The tile path reconstructs from an extended field and this
#: one does not; below that scale the two are the same picture.
VIEW_RESOLUTION = (640, 360)
VIEW_SUPERSAMPLE = 2
VIEW_MODE = "smooth"
VIEW_CURVE = "linear"


class IntakeError(RuntimeError):
    """The supply cannot be read, or cannot be scored."""


def store_dir() -> Path:
    """Where curation keeps what it derives from the ledgers. Ignored, re-derivable."""
    return repo_root() / "artifacts" / "curation"


def scores_path() -> Path:
    """The sidecar: one row per location the head has an opinion about."""
    return store_dir() / "supply_scores.jsonl"


def view_dir() -> Path:
    """Where the pictures the head is scored on live."""
    return store_dir() / "views"


# --------------------------------------------------------------------------- #
# The union, at the gates.
# --------------------------------------------------------------------------- #
def gate_survivors(paths=None) -> tuple[list[dict], dict]:
    """`(rows, diagnostics)` — every location any walk found and no gate refused.

    The pre-floor population, which is the denominator of every "N found, M above
    floor" line this module prints. A caller that only kept the passing rows
    could not recover it.
    """
    return ledgers.admitted_union(paths, admit=ledgers.passes_gates)


def canonical_map() -> str:
    """The colormap the location view is drawn through, read off the tile pool.

    The tile build reserves its low slots for named maps and slot zero carries
    the canonical view, so the deploy map is the first of those reservations. Read
    from the tracked table rather than typed here, because a map named in two
    places is a map that can be changed in one.
    """
    from fractal_wallpapers.models import tiles as tile_module

    floor = tile_module.palette_pool().get("floor") or []
    if not floor:
        raise IntakeError(
            f"{tile_module.pool_path()} reserves no floor palette, so nothing says which map "
            f"a location's canonical view is drawn through."
        )
    return str(floor[0][0])


def view_row(row: dict, colormap: str, cyclic: set[str]) -> dict:
    """One ledger row as the render-cache row its picture is made from.

    Through the same shape the finished-render cache uses, so `renders.spec_of`
    is the one place that knows how a row becomes an engine spec — here as
    everywhere else.
    """
    from fractal_wallpapers.labeling import finished

    return {
        "family": row["family"],
        "viewport": row["viewport"],
        "mode": VIEW_MODE,
        "mode_params": {},
        "curve": VIEW_CURVE,
        "colormap": colormap,
        "recipe": finished.recipe(mirror=colormap not in cyclic),
        "render": {
            "resolution": list(VIEW_RESOLUTION),
            "supersample": VIEW_SUPERSAMPLE,
            "maxiter": int(row["maxiter"]),
        },
    }


def view_name(row: dict, colormap: str, cyclic: set[str]) -> str:
    """The file name of one location's view: a digest of the whole recipe."""
    from fractal_wallpapers.models import renders

    return renders.job_name(view_row(row, colormap, cyclic))


# --------------------------------------------------------------------------- #
# The read: what the location head says about the supply.
# --------------------------------------------------------------------------- #
def score(paths=None, device: str = "auto", limit: int | None = None, log=print) -> dict:
    """Render every gate-surviving location's canonical view and score it.

    Idempotent and resumable in both halves: a view already on disk is not
    re-rendered, and the sidecar is rewritten whole from the union so a re-run
    over more ledgers is a superset rather than an append nobody can deduplicate.
    """
    from fractal_wallpapers.models import renders, scoring, ship, train

    rows, diagnostics = gate_survivors(paths)
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise IntakeError(
            "no walk ledger holds a single gate-surviving candidate, so there is no supply to "
            "score. Run `fractal-wallpapers harvest` first."
        )

    colormap = canonical_map()
    cyclic = _cyclic_maps()
    directory = view_dir()
    directory.mkdir(parents=True, exist_ok=True)

    made = 0
    pictures = []
    for index, row in enumerate(rows, start=1):
        name = view_name(row, colormap, cyclic)
        output = directory / f"{name}.jpg"
        if not output.is_file():
            from fractal_wallpapers import engine

            engine.run("render", renders.spec_of(view_row(row, colormap, cyclic), output))
            made += 1
            if made % 25 == 0:
                log(f"{index}/{len(rows)} views rendered ({made} new)")
        pictures.append(output)

    model, config, where = scoring.load(ship.shipped_path("location"), device)
    log(f"scoring {len(pictures)} locations through the shipped location head on {where}")
    classes = int(config["classes"])
    probabilities = train.score(
        model, pictures, scoring.transform_of(config), where, classes, {"batch_size": 64}
    )

    stamp = floors.live_stamp("location")
    path = scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row, picture, probability in zip(rows, pictures, probabilities, strict=True):
            record = {
                "schema": SCHEMA,
                "head": "location",
                "head_sha256": stamp,
                "key": _key_text(row),
                "ledger": row.get("_ledger"),
                "node_id": row.get("node_id"),
                "partition": partition_of_row(row),
                "family": row["family"],
                "viewport": row["viewport"],
                "maxiter": row.get("maxiter"),
                "view": picture.name,
            }
            for index in range(classes - 1):
                record[f"p_ge{index + 2}"] = float(probability[index])
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "schema": SCHEMA,
        "head": "location",
        "head_sha256": stamp,
        "gate_survivors": len(rows),
        "views_rendered": made,
        "views_reused": len(rows) - made,
        "view": {
            "resolution": list(VIEW_RESOLUTION),
            "supersample": VIEW_SUPERSAMPLE,
            "mode": VIEW_MODE,
            "curve": VIEW_CURVE,
            "colormap": colormap,
        },
        "union": diagnostics,
        "wrote": str(path),
    }


def _cyclic_maps() -> set[str]:
    from fractal_wallpapers.models import palette_sets

    return palette_sets.cyclic()


def _key_text(row: dict) -> str:
    """A location key as a sidecar can carry it: JSON, so the join is exact."""
    key = key_of_row(row)
    if key is None:
        raise IntakeError(
            "a gate-surviving row carries no location identity, so its score could never be "
            "joined back to it. Every row the union keeps is keyable or is reported unkeyed."
        )
    return json.dumps(key, ensure_ascii=False)


def read_scores(path: Path | None = None) -> dict:
    """`{location key: row}` from the sidecar, schema-checked."""
    path = scores_path() if path is None else Path(path)
    if not path.is_file():
        raise IntakeError(
            f"{path} is missing — nothing has read the supply yet. Run "
            f"`fractal-wallpapers curate score` before an intake."
        )
    out = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise IntakeError(f"{path}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}")
        out[row["key"]] = row
    return out


# --------------------------------------------------------------------------- #
# The ranked offer.
# --------------------------------------------------------------------------- #
def rank_key(row: dict):
    """Best first: `P(≥3)` descending, then the location key.

    The tie-break is not cosmetic. A run has to be reproducible, and scores tie
    often enough — an unscored row, two frames of one shape — that leaving the
    order to whatever the union walk happened to produce would let two runs over
    the same ledgers pick different locations.
    """
    score_ = row.get("score")
    return (-(score_ if score_ is not None else -1.0), row["key"])


def ranked(paths=None, scores: dict | None = None) -> tuple[dict, dict]:
    """`({partition: [row, ...]}, diagnostics)` — the offer, best first per partition.

    Each returned row is the ledger's own row plus the three things the rest of
    curation joins on: its `key`, its `partition`, and the `score` the head gave
    it. A row the sidecar has no opinion about keeps a `None` score, sorts last,
    and never passes the junk floor — which is the same answer an unscored row
    gets everywhere else in this project.
    """
    survivors, diagnostics = gate_survivors(paths)
    scores = read_scores() if scores is None else scores

    offer: dict[str, list[dict]] = {}
    found: dict[str, int] = {}
    passing: dict[str, int] = {}
    good: dict[str, int] = {}
    unscored = 0
    for row in survivors:
        key = key_of_row(row)
        if key is None:
            continue
        text = json.dumps(key, ensure_ascii=False)
        partition = partition_of_row(row)
        read = scores.get(text)
        value = None if read is None else float(read.get("p_ge3"))
        if read is None:
            unscored += 1
        found[partition] = found.get(partition, 0) + 1
        if floors.passes_good_floor(value):
            good[partition] = good.get(partition, 0) + 1
        if not floors.passes_junk_floor(value):
            continue
        passing[partition] = passing.get(partition, 0) + 1
        offer.setdefault(partition, []).append(
            {**row, "key": text, "partition": partition, "score": value}
        )
    for partition in offer:
        offer[partition].sort(key=rank_key)

    diagnostics = dict(diagnostics)
    diagnostics.update(
        {
            "junk_floor": floors.JUNK_FLOOR,
            "good_floor": floors.GOOD_FLOOR,
            "found_by_partition": dict(sorted(found.items())),
            "passing_by_partition": dict(sorted(passing.items())),
            "good_by_partition": dict(sorted(good.items())),
            "found": sum(found.values()),
            "passing": sum(passing.values()),
            "good": sum(good.values()),
            "unscored": unscored,
        }
    )
    return offer, diagnostics


def supply_lines(diagnostics: dict) -> list[str]:
    """One line per partition the union saw, including the ones that emit nothing.

    A partition that vanishes from a readout because its supply died is the exact
    failure this line exists to make visible, so it gets a line with a zero on it
    rather than no line.
    """
    found = diagnostics.get("found_by_partition", {})
    passing = diagnostics.get("passing_by_partition", {})
    good = diagnostics.get("good_by_partition", {})
    out = []
    for partition in sorted(set(found) | set(passing) | set(good)):
        n_pass = passing.get(partition, 0)
        n_good = good.get(partition, 0)
        line = (
            f"{partition}: {found.get(partition, 0)} found, {n_pass} above the junk floor, "
            f"{n_good} above the good floor"
        )
        if not floors.emit_cap(n_pass):
            line += (
                " -> releases 1 (slot guarantee), then 0 (thin supply)"
                if n_good
                else " -> releases 0 (thin supply)"
            )
        out.append(line)
    return out


def emit_caps(offer: dict) -> dict:
    """`{partition: cap}` — the thin-supply cap over each partition's ranked offer."""
    return {partition: floors.emit_cap(len(rows)) for partition, rows in sorted(offer.items())}


def guaranteed(diagnostics: dict) -> list[str]:
    """The partitions a release owes a slot: every one with something worth keeping.

    The trigger is the good floor rather than the junk floor. Below about seven
    release slots the mix structurally zeroes the lowest-ratio partitions whatever
    their supply, so the garnish would never ship; the guarantee is one slot
    across the whole release and the remainder is the mix exactly as before.
    """
    return sorted(p for p, n in (diagnostics.get("good_by_partition") or {}).items() if n > 0)


def slots(partitions, n: int, guarantees=(), caps: dict | None = None) -> dict:
    """`{partition: slots}` — `n` release slots over the mix, with a guaranteed floor.

    Through `supply.apportion`, which owns the largest-deficit rule and the
    guarantee fixed point. The weights are the release mix restricted to the
    partitions this pass actually has candidates for: a partition with nothing to
    offer must not hold a slot hostage.
    """
    partitions = sorted(set(partitions))
    if not partitions or n <= 0:
        return dict.fromkeys(partitions, 0)
    weights = release_mix.shares(partitions)
    return apportion.allocate_slots(weights, int(n), caps=caps, guaranteed=guarantees)


__all__ = [
    "SCHEMA",
    "VIEW_CURVE",
    "VIEW_MODE",
    "VIEW_RESOLUTION",
    "VIEW_SUPERSAMPLE",
    "IntakeError",
    "canonical_map",
    "emit_caps",
    "gate_survivors",
    "guaranteed",
    "rank_key",
    "ranked",
    "read_scores",
    "score",
    "scores_path",
    "slots",
    "store_dir",
    "supply_lines",
    "view_dir",
    "view_name",
    "view_row",
]
