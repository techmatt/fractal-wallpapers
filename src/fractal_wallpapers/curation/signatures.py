"""The diversity rule's bound signature, swept once into a sidecar beside the scores.

The gallery leg's one expensive rule is the twin rule, and what it costs is not the
comparison — it is opening the JPEG. [`curation.rules.Twins`] screens a candidate
against the seated stack with a sound lower bound read off a **reduced** signature:
[`rules.BOUND_BLOCKS`] blocks of quantiles by
[`fractal_wallpapers.palettes.pixel_clouds.DIRECTIONS`] directions, four kibibytes
against the metric's hundred and twenty-eight. Only the fraction of a percent of
pairs the bound cannot settle ever needs the full cloud.

That reduced form is derived from the full one, so **making it costs a decode** —
about 16.8 ms a picture, and 96 ms before the metric came down to 256 directions — and a
pass that walks nine thousand rows pays for every
picture it opens. It is also the same number every time: the picture on disk does
not change, so the reduced signature is a property of the picture and not of the
pass. This is where it is kept.

## Why a store and not a faster pass

`BUILD_greedy_swap_solve` measured the leg and found the signatures were ~100% of
it: 4,624 made at n=150 for 443 s of a 461 s leg. Two prunes and a per-pass reduced
store took that to 289 signatures and 38.4 s, and a third idea — decoding in
parallel over three workers — was implemented, measured and **reverted**, because a
prefetch has to guess which candidates the walk will open and the only free guess
(the counted rules) over-fetches by more than the parallelism wins back.

A sidecar needs no guess. The signature is made once, for the whole clearing pool,
in a leg of its own; every later pass reads it instead of deriving it, and the pass
opens a picture only for the full-signature fetches the bound could not settle.
What the reverted read-ahead was trying to buy, without having to predict anything.

## What it actually bought, measured, and it is not the gallery leg

**At n=150 the store is a wash: 37.9 s without it, 36.9 s with it**, over an
identical gallery. Not what it was built for and worth stating plainly, because the
reason is structural rather than a tuning problem.

[`Twins.within`] asks [`reduced_of`] for the candidate's reduced form and then, for
the fraction the bound cannot settle, asks [`pixel_clouds.Clouds`] for that **same
key's** full cloud a few lines later. Without a sidecar the first call decodes the
picture into the Clouds read cache, so the second is a cache hit. With one, the
first call never touches Clouds, so the second is a cold decode. The store removes
289 reduced decodes at n=150 and hands back 325 full ones that used to be free.
Both records carry `full_signatures_fetched` **325**, which is how that is visible.

So the win is bounded by the candidates whose bound settles *everything* — the ones
that never need a full cloud at all — and the gallery leg's two prunes have already
removed almost all of those before a picture is opened. There is little left for a
store to save there.

**Where it does pay is a sweep that needs no full signatures**, and
`curate headroom --twin` is exactly that: it builds one reduced signature per place
to screen millions of pairs and reads the full cloud only for the few thousand
survivors. It used to build every one of them and throw them all away.

Measured over that sweep's own population — 4,496 places after the neutral
pre-selection, one picture each: the sidecar answers **all 4,496 in 0.7 s**, against
**429 s** to decode them at the 95 ms a picture that cost at 1024 directions; at 256 it
is 16.8 ms and the same decode is about 75 s. That is the sweep's whole
signature-building half, and it is where this store earns its 247 MB.

## Staleness is the picture's identity and never a clock

A row is stale when the recipe's picture is not the picture the row was read from —
that is the whole rule. Nothing here compares timestamps: `curate retention` moves
and drops pictures, a restore puts them back with new mtimes, and a store keyed on
time would re-sweep a pool nothing had changed while still missing a picture that
was replaced within the same second. The row carries the `picture` it was read from
and a mismatch is a re-read.

The two constants the reduction is taken at ride on the row for
[`curation.flatness`]'s reason: a signature reduced at other constants is a
different vector and must not be able to wear this one's name. Change either and
every row is stale at once, which is correct and is what [`by_recipe`] enforces.

## Regenerable, and not backed up

No [`curation.durability.Durable`], unlike the flatness sidecar. The whole store is
~245 MB and rebuilding it is one command and a few minutes over the standard
three-worker pool; a second copy of a derived store that size earns less than it
costs. The pictures are the durable thing and they already are one.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger

#: The schema every sidecar row carries.
SCHEMA = 1

#: What the sidecar is called, beside `scores.jsonl` in the ledger's own subtree.
SIDECAR_NAME = "reduced_signatures.jsonl"

#: How many pictures one worker takes at a time. Smaller than
#: [`curation.flatness.CHUNK`] because each reading comes back four kibibytes
#: rather than one float, and a worker's result list is held whole before it is
#: written.
CHUNK = 64

#: How many workers sweep by default. **Three**, the same number every leg that
#: drives the engine uses, for the same reason: this is a decode-bound sweep of
#: thousands of JPEGs and it should not make the desktop unusable.
WORKERS = 3


class SignatureError(RuntimeError):
    """The sidecar cannot be read, or the sweep cannot be run."""


def shape() -> tuple[int, int]:
    """`(blocks, directions)` — the constants a row is only valid at."""
    from fractal_wallpapers.curation import rules
    from fractal_wallpapers.palettes import pixel_clouds

    return rules.BOUND_BLOCKS, pixel_clouds.DIRECTIONS


# --------------------------------------------------------------------------- #
# The reading.
# --------------------------------------------------------------------------- #
def reduced(path) -> list | None:
    """One picture's reduced signature, flat. `None` when it cannot be opened.

    The one place this module makes a reading, and it is
    [`rules.reduce_signature`] over [`pixel_clouds.of_picture`] rather than a
    second derivation — the sidecar has to hold exactly what the pass would have
    computed or it is not a cache of it.
    """
    from fractal_wallpapers.curation import rules
    from fractal_wallpapers.palettes import pixel_clouds

    where = Path(path)
    if not where.is_file():
        return None
    try:
        made = pixel_clouds.of_picture(where)
    except Exception:  # noqa: BLE001 - an unreadable picture is a row, not a crash
        return None
    return rules.reduce_signature(made).reshape(-1)


def pack(vector) -> str:
    """One reduced signature as the base64 of its `float32` bytes, little-endian.

    `float32` and not the `float16` [`curation.embeddings`] packs its unit vectors
    at, because this store has to be **exact**. The bound is a lower bound on a
    metric and a value rounded the wrong way turns it into a slightly-too-large
    one, which would let a real twin be pruned; and `test_solve.py` pins the
    gallery bit-identical, which a lossy round-trip would break for nothing. Four
    bytes a float is 4 KiB a row and the store is regenerable.
    """
    import numpy

    return base64.b64encode(numpy.asarray(vector, dtype="<f4").tobytes()).decode("ascii")


def unpack(text: str):
    """The signature a row carries, back as the `float32` the bound reads."""
    import numpy

    return numpy.frombuffer(base64.b64decode(text), dtype="<f4")


def _chunk(payload: list) -> list:
    """One worker's share: `[(key, picture, path)]` in, `[(key, picture, packed)]` out."""
    out = []
    for key, picture, path in payload:
        made = reduced(path)
        out.append((key, picture, None if made is None else pack(made)))
    return out


def _worker():
    """What every sweep worker does before it decodes anything: get out of the way."""
    from fractal_wallpapers import process_control

    process_control.set_background_priority()


# --------------------------------------------------------------------------- #
# Where it lives.
# --------------------------------------------------------------------------- #
def sidecar_path() -> Path:
    """The sidecar: one row per recipe key, beside the scores sidecar."""
    return candidate_ledger.store_root() / SIDECAR_NAME


def row(key: str, picture: str, packed: str) -> dict:
    """One sidecar row. The picture it was read from and the constants it was
    reduced at both travel on it — the first is what staleness is keyed on and the
    second is what makes the vector readable."""
    blocks, directions = shape()
    return {
        "schema": SCHEMA,
        "recipe_key": str(key),
        "picture": str(picture),
        "blocks": int(blocks),
        "directions": int(directions),
        "signature": packed,
    }


def read(path: Path | None = None) -> list[dict]:
    """Every sidecar row, signatures still packed. An absent sidecar reads empty —
    nothing has swept yet is a state, not a failure."""
    where = sidecar_path() if path is None else Path(path)
    if not where.is_file():
        return []
    out = []
    with where.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            held = json.loads(line)
            if held.get("schema") != SCHEMA:
                raise SignatureError(f"{where}:{number}: schema {held.get('schema')!r}")
            out.append(held)
    return out


def by_recipe(rows=None) -> dict:
    """`{recipe key: the picture it was read from}` for rows at the CURRENT shape.

    A row reduced at other constants is not a reading of the same thing, so it is
    dropped here rather than mixed in — which makes changing either constant a
    full re-sweep, silently and correctly.
    """
    blocks, directions = shape()
    held = read() if rows is None else list(rows)
    return {
        str(entry["recipe_key"]): str(entry.get("picture", ""))
        for entry in held
        if int(entry.get("blocks", -1)) == blocks and int(entry.get("directions", -1)) == directions
    }


def write(rows) -> tuple[Path, int, int]:
    """Upsert `rows` into the sidecar by recipe key. `(path, total, new)`."""
    path = sidecar_path()
    held = {str(entry["recipe_key"]): entry for entry in read(path)}
    before = len(held)
    for entry in rows:
        held[str(entry["recipe_key"])] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in sorted(held):
            handle.write(json.dumps(held[key], ensure_ascii=False) + "\n")
    return path, len(held), len(held) - before


# --------------------------------------------------------------------------- #
# What a reader gets.
# --------------------------------------------------------------------------- #
def for_candidates(candidates, path: Path | None = None) -> dict:
    """`{key: its reduced signature}` for the ones this store can answer for.

    **Only the keys asked for are kept.** The whole store is ~245 MB and a view is
    a fraction of it; holding the rest would put a quarter of a gibibyte behind a
    pass that will never look at it. A key whose row names a different picture than
    the candidate does is left out, which is the staleness rule doing its work at
    read time as well as at sweep time.
    """
    wanted = {str(held.key): str(held.picture or "") for held in candidates}
    if not wanted:
        return {}
    where = sidecar_path() if path is None else Path(path)
    if not where.is_file():
        return {}
    blocks, directions = shape()
    out: dict = {}
    # One `json.loads` a row and no fast path. A hand-rolled scan that reads the
    # key off the head of the line before parsing was written and MEASURED: 0.7 s
    # against 0.8 s over the 11,210-row store, which is 0.3% of a leg. It was taken
    # back out. The whole read is under a second and the store was never the cost —
    # see the module docstring for what actually is.
    with where.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("schema") != SCHEMA:
                raise SignatureError(f"{where}:{number}: schema {entry.get('schema')!r}")
            key = str(entry["recipe_key"])
            if key not in wanted or entry.get("signature") is None:
                continue
            if int(entry.get("blocks", -1)) != blocks:
                continue
            if int(entry.get("directions", -1)) != directions:
                continue
            if str(entry.get("picture", "")) != wanted[key]:
                continue
            out[key] = unpack(entry["signature"])
    return out


def missing(candidates, held=None) -> list:
    """`[(key, picture, path)]` for the candidates the sidecar cannot answer for.

    Absent, or holding a row read from a **different picture** than this candidate
    names. That second case is the whole staleness rule and it is why the row
    carries the picture: a recipe whose picture was re-rendered has a signature
    that is no longer a reading of it, and nothing about a clock would say so.
    """
    from fractal_wallpapers.paths import rehome

    known = by_recipe() if held is None else held
    out = []
    for candidate in candidates:
        key = str(candidate.key)
        picture = str(candidate.picture or "")
        if not picture:
            continue
        if known.get(key) == picture:
            continue
        where = rehome(picture)
        if where is not None:
            out.append((key, picture, Path(where)))
    return out


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
def sweep(candidates, workers: int = WORKERS, recompute: bool = False, log=print) -> dict:
    """Read every candidate the sidecar cannot answer for, and write the rows.

    Incremental by construction: a store already swept costs one read and no
    decodes. `recompute` re-reads every candidate instead, which is what to run
    after changing anything about the reduction itself.
    """
    import concurrent.futures
    import time

    started = time.monotonic()
    held = {} if recompute else by_recipe()
    outstanding = missing(candidates, held=held)
    log(f"[signatures] {len(outstanding):,} of {len(candidates):,} candidate(s) to read")
    made: list = []
    unreadable = 0
    if outstanding:
        payload = [outstanding[at : at + CHUNK] for at in range(0, len(outstanding), CHUNK)]
        # One worker reads here rather than spawning a pool to use one process:
        # the spawn is most of a second on Windows and buys nothing at all.
        if int(workers) <= 1:
            batches = map(_chunk, payload)
            done = 0
            for batch in batches:
                for key, picture, packed in batch:
                    if packed is None:
                        unreadable += 1
                        continue
                    made.append(row(key, picture, packed))
                done += 1
                if done % 10 == 0 or done == len(payload):
                    log(f"[signatures] {done * CHUNK:,} of {len(outstanding):,} read")
        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=int(workers), initializer=_worker
            ) as pool:
                done = 0
                for batch in pool.map(_chunk, payload):
                    for key, picture, packed in batch:
                        if packed is None:
                            unreadable += 1
                            continue
                        made.append(row(key, picture, packed))
                    done += 1
                    if done % 10 == 0 or done == len(payload):
                        log(f"[signatures] {done * CHUNK:,} of {len(outstanding):,} read")
    path, total, new = write(made) if made else (sidecar_path(), len(read()), 0)
    seconds = round(time.monotonic() - started, 2)
    log(f"[signatures] {len(made):,} row(s) written in {seconds}s; {total:,} held")
    return {
        "of": "one reduced pixel-cloud signature per recipe with a picture on disk, in "
        "the shape curation.rules.Twins reads for its bound",
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema": SCHEMA,
        "sidecar": str(path),
        "blocks": shape()[0],
        "directions": shape()[1],
        "population": len(candidates),
        "outstanding": len(outstanding),
        "read": len(made),
        "unreadable": unreadable,
        "rows": total,
        "new": new,
        "workers": int(workers),
        "recompute": bool(recompute),
        "stale_when": "the row's picture is not the picture the recipe names. NEVER a "
        "timestamp: retention moves pictures and a restore rewrites their mtimes",
        "seconds": seconds,
    }


def coverage(candidates, rows=None) -> dict:
    """How much of a population this store can answer for."""
    known = by_recipe(rows)
    have = sum(1 for held in candidates if known.get(str(held.key)) == str(held.picture or ""))
    return {
        "of": "candidates whose reduced signature is held AND was read from the picture "
        "the recipe currently names",
        "population": len(candidates),
        "held": have,
        "share": round(have / max(len(candidates), 1), 6),
        "rows": len(known),
        "blocks": shape()[0],
        "directions": shape()[1],
    }


__all__ = [
    "CHUNK",
    "SCHEMA",
    "SIDECAR_NAME",
    "WORKERS",
    "SignatureError",
    "by_recipe",
    "coverage",
    "for_candidates",
    "missing",
    "pack",
    "read",
    "reduced",
    "row",
    "shape",
    "sidecar_path",
    "sweep",
    "unpack",
    "write",
]
