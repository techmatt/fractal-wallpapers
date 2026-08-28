"""One vector per admitted location, so the gallery pass can tell two places apart.

The gallery pass picks locations by **quality-weighted farthest point with a hard
radius**: the strongest location first, then whichever admitted location is
furthest from everything already chosen, refusing anything closer than `r` to a
pick. That needs a distance between two locations, and a distance between two
locations needs a picture of each that is comparable — one taken the same way
every time, saying nothing about a coloring that has not been chosen yet.

So this module keeps exactly that: for every location the location judge admits
over the junk floor, a **neutral render**
([`fractal_wallpapers.curation.neutral`]) and the **unit vector** a frozen
DINOv2 reads off it ([`fractal_wallpapers.models.embedding`]). Computed once,
keyed by location, appended to forever.

## Locations, not candidates, and the key is the exact one

A candidate is a location colored one way, and there are thirty-two of those per
location before anything is judged. Embedding candidates would measure palette
distance, which the neighborhood draw already handles and which the gallery pass
is explicitly not about.

The key is `supply.location.location_key` — the partition, the degree, the
identifying constants, and the three coordinates canonicalized — which is the
same string the supply sidecar keys its rows by and the same identity the
gallery pass will group over. Not the **group** id: a group is a position in a
connected-components labelling computed inside one `selection.grouped` call, it
means nothing outside that call, and a durable store cannot be keyed on it. The
grouping is derived from keyed rows at selection time; this is what it is derived
from.

## One JSONL, and the vector rides on the row

The obvious shape is a matrix beside an index, and it is the wrong one here: two
files that have to agree about row order is a thing that goes wrong quietly. A
row carries its own vector, base64 of `float16`, about a kilobyte on a row that
was already a few hundred bytes — and it carries **its whole join**, the family
and the viewport and the maxiter, so the store re-renders its own pictures
without the walk ledgers being present. That is the same rule a label row
follows and it is worth the bytes for the same reason.

Appending is therefore the whole write path: read which keys are already there,
render and embed the rest, append. Idempotent, resumable at any batch boundary,
and a future harvest's admissions are a second run of the same command.

## The pictures are hot; the vectors are what is made durable

The JPEGs are a couple of gigabytes and they are for **Matt's eye** — the only
way to answer whether "near in this space" means "looks alike". They regenerate
from the store's own rows at about a tenth of a second each. The vectors do not:
they cost a pass of the encoder over the whole population, and their input lives
under `artifacts/` like everything else. So the JSONL gets the
[`durability`] treatment — archived copy, tracked manifest, `save|check|restore`
— and the picture directory gets counted in that manifest and nothing more.

## What invalidates every row in here

The frozen choices: the colormap, the geometry, the mode, the curve, the
encoder, the dimension. [`neutral.stamp`] digests all of them together, the
manifest records the digest, and every row carries it. A leg that would append
rows under a different stamp refuses instead, because a store holding two
provenances is a store whose cosines are arithmetic between unrelated numbers.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from fractal_wallpapers.curation import durability, floors, neutral
from fractal_wallpapers.paths import archive_root, hot_root, tracked_name, under

#: The schema every stored row carries.
SCHEMA = 1

#: What the store is called, wherever it is.
STORE_NAME = "neutral_embeddings.jsonl"

#: How many locations are rendered and encoded before anything is written. A
#: crash loses at most this much work, and the encoder is handed a full batch.
LEG = 64

#: Seconds one neutral render may take before it is killed. These are 448x252 at
#: one sample per pixel and the slowest of them is well under a second; the bound
#: exists for the hung unit, which is the realistic way a leg of twenty-five
#: thousand renders stops making progress rather than fails.
UNIT_SECONDS = 90.0

#: The seed the pilot's stratified draw is taken under, recorded with it.
SAMPLE_SEED = 0

#: What the leg's exclusive claim on the store directory is called. Two legs
#: appending to one JSONL interleave half-written rows into it — measured, on
#: 2026-08-22, by starting this twice — and the store then holds duplicate keys
#: and lines that will not parse. See `models.train.claim`.
LOCK_NAME = "embedding.lock"


class StoreRefused(RuntimeError):
    """The embedding store cannot be read, or cannot be appended to."""


# --------------------------------------------------------------------------- #
# Where everything lives.
# --------------------------------------------------------------------------- #
def store_path() -> Path:
    """The store: one row per embedded location, wherever curation's subtree is."""
    return under("curation") / STORE_NAME


def backup_path() -> Path:
    """The durable copy, beside the sidecar's on the archive tier.

    The same [`durability.BACKUP_UNIT`] and for the same reason: a copy that
    shared the `curation` name would be arbitrated onto one tier by the collision
    guard, which is the opposite of what a second copy is for.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / STORE_NAME


def manifest_path() -> Path:
    """The tracked manifest: what the store was, last time anybody recorded it."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "neutral_embeddings.manifest.json"


def store() -> durability.Durable:
    """The store as a [`durability.Durable`], which is how it is saved and checked."""
    return durability.Durable(
        name="the neutral-render embedding store",
        live=store_path(),
        copy=backup_path(),
        manifest=manifest_path(),
        why_not_tracked=(
            "one kilobyte of vector per location over twenty-five thousand locations, which "
            "is tens of megabytes against a 1 MiB per-file history guard, and it grows by an "
            "append every time a harvest adds admissions. The manifest is what the history "
            "keeps: the row count, the bytes, the sha256, the frozen choices every vector "
            "was made under, and the population it was counted against."
        ),
        save_command="fractal-wallpapers curate embeddings save",
        restore_command="fractal-wallpapers curate embeddings restore",
        rebuild_command="fractal-wallpapers curate embed",
        facts=_facts,
    )


def _facts(path: Path) -> dict:
    """The columns this store adds to its manifest: what made it, and over what."""
    stamps: dict[str, int] = {}
    partitions: dict[str, int] = {}
    choices: dict | None = None
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            stamps[str(row.get("stamp"))] = stamps.get(str(row.get("stamp")), 0) + 1
            key = str(row.get("partition"))
            partitions[key] = partitions.get(key, 0) + 1
            if choices is None:
                choices = row.get("choices")
    pictures = neutral.neutral_dir()
    files = list(pictures.glob("*.jpg")) if pictures.is_dir() else []
    # One stamp is the ordinary case and it is a bare field. More than one is the
    # failure the stamp exists for, and it gets the counts instead of a `null`
    # column on every healthy manifest.
    told = (
        {"stamp": next(iter(stamps))}
        if len(stamps) == 1
        else {"stamp": None, "stamp_counts": dict(sorted(stamps.items()))}
    )
    return {
        **told,
        "choices": choices,
        "rows_by_partition": dict(sorted(partitions.items())),
        "pictures": {
            # `tracked_name`, because this file is in the history: a manifest that
            # named one machine's drive letter would differ on every clone.
            "directory": tracked_name(pictures),
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "regenerable": (
                "yes, from this store's own rows: every row carries the family, the viewport "
                "and the maxiter its neutral render is made from. About a tenth of a second "
                "each, so they are counted here and not copied."
            ),
        },
    }


# --------------------------------------------------------------------------- #
# The population: what a full store is counted against.
# --------------------------------------------------------------------------- #
def admitted() -> list[dict]:
    """Every location over the junk floor, from the supply sidecar, keyed and sorted.

    THE denominator. The floor is [`floors.JUNK_FLOOR`] read through
    `floors.passes_junk_floor`, which is the same comparison intake makes when it
    decides what is worth spending a colorize on: there is no reason to embed a
    location the judge is confident is junk, and no reason for a stricter cut
    than the one that already decides what curation looks at.
    """
    rows = [row for row in _supply() if floors.passes_junk_floor(row.get("p_ge3"))]
    rows.sort(key=lambda row: str(row["key"]))
    return rows


def admitted_only(rows: list, matrix, scores: dict, log=print) -> tuple:
    """`(rows, matrix, dropped)` — the store cut down to the CURRENT population.

    The store is **append-only**: a location embedded once keeps its vector
    forever, and re-scoring is free to move the reading underneath it. So the
    store is a superset of the admitted population rather than a picture of it —
    29,051 rows against 29,046 admitted on 2026-08-22, the five being locations
    `curate score` re-read at the node regime and put under the junk floor.

    A location the sidecar now calls junk is not a place the collection may ship,
    and a leg that draws from the store is the reader for whom that is expensive
    rather than cosmetic: it could spend a location's renders on somewhere the
    supply phase has already withdrawn. Cutting the rows here — before anything
    is planned off them — is what makes it invisible to every stage at once
    rather than a filter each of them has to remember.

    The cut is [`floors.passes_junk_floor`] over the sidecar's live `P(>=3)`, the
    same comparison [`admitted`] makes; a key the sidecar does not hold at all is
    dropped for the same reason, since a location with no current reading has no
    current standing either.
    """
    keep = [
        index
        for index, row in enumerate(rows)
        if floors.passes_junk_floor((scores.get(str(row["key"])) or {}).get("p_ge3"))
    ]
    dropped = len(rows) - len(keep)
    if not dropped:
        return rows, matrix, 0
    log(
        f"[embed] {dropped} embedded location(s) are below the junk floor now and are "
        f"out of this population: {len(keep):,} left to draw from"
    )
    if not keep:
        raise StoreRefused(
            f"none of the {len(rows):,} embedded location(s) is in the admitted population "
            f"any more, so there is nothing to draw from. Run `fractal-wallpapers curate "
            f"score` and `curate embed`."
        )
    return [rows[index] for index in keep], matrix[keep], dropped


def _supply() -> list[dict]:
    """Every row of the supply sidecar, **amended**, or a refusal naming how to get one.

    One reader, because [`admitted`] and [`unreachable`] ask the same file two
    questions and a second opener would be a second answer to whether it is
    there.

    Through [`intake.read_scores`] and not by opening the file, because that is
    the door [`curation.amend`]'s re-read comes through. This store's denominator
    is the admitted population and admission is a comparison against a *score*: a
    reader that opened the sidecar directly would count a location in on a number
    read off a picture that no longer exists.
    """
    from fractal_wallpapers.curation import intake

    try:
        return list(intake.read_scores().values())
    except intake.IntakeError as absent:
        raise StoreRefused(
            f"{intake.scores_path()} is not there, so there is no admitted population to "
            f"read. Run `fractal-wallpapers curate score`, or `curate sidecar restore` if a "
            f"durable copy exists. ({absent})"
        ) from absent


def judged_pool() -> dict:
    """`{location key: partition}` for every location the accumulated pool judged.

    Every place curation has actually made a candidate of. They are not the
    population this store is counted against — that is [`admitted`] — and the two
    are worth reading together for one reason: a judged location the store cannot
    hold is a place the gallery pass cannot select, however good the wallpaper
    somebody already made of it. See [`unreachable`].

    **Both stores**, because the pool is in two places. A run's candidates are
    release rows; a gallery pass's attempts are rows in
    [`curation.gallery_store`], under `artifacts/` rather than in the history, and
    a pass makes more of them in one night than every run has made in total.
    """
    from fractal_wallpapers.curation import gallery_store, records

    pool: dict[str, str] = {}
    for row in [*records.read_decisions(records.RELEASE), *gallery_store.read()]:
        location = row.get("location") or {}
        pool.setdefault(str(location.get("key")), str(location.get("partition")))
    return pool


def unreachable(pool: dict | None = None) -> dict:
    """Which judged locations the admitted population does not contain, and why.

    Two causes and they are different problems. **Below the floor** is today's
    location head disagreeing with a colorize somebody paid for at the time — a
    judgement, and the floor is where it is on purpose. **Absent from the
    sidecar** is a location the standing supply has no row for at all, which is
    not a judgement about anything: it is a place whose ledger was never scored
    into the sidecar, so no cut has been applied to it and none can be.
    """
    pool = judged_pool() if pool is None else pool
    scored = {str(row["key"]): row.get("p_ge3") for row in _supply()}
    below = sorted(k for k in pool if k in scored and not floors.passes_junk_floor(scored[k]))
    absent = sorted(k for k in pool if k not in scored)
    return {
        "judged": len(pool),
        "admitted": len(pool) - len(below) - len(absent),
        "below_the_junk_floor": {"count": len(below), "keys": below},
        "absent_from_the_sidecar": {"count": len(absent), "keys": absent},
    }


def stratified(rows: list[dict], n: int, seed: int = SAMPLE_SEED) -> list[dict]:
    """`n` of `rows`, spread over the partitions in proportion to their supply.

    Through `supply.apportion`, which already owns the largest-deficit rule and
    the guaranteed floor. A pilot that drew uniformly would be four fifths julia
    and would say nothing about how the parameter planes behave.
    """
    import random

    from fractal_wallpapers.supply import apportion

    by_partition: dict[str, list[dict]] = {}
    for row in rows:
        by_partition.setdefault(str(row["partition"]), []).append(row)
    sizes = {name: len(members) for name, members in by_partition.items()}
    if n >= len(rows):
        return list(rows)
    share = apportion.allocate_slots(sizes, n, caps=sizes, guaranteed=tuple(sorted(sizes)))
    drawn = []
    for name in sorted(by_partition):
        members = list(by_partition[name])
        random.Random(f"{seed}:{name}").shuffle(members)
        drawn.extend(members[: share.get(name, 0)])
    drawn.sort(key=lambda row: str(row["key"]))
    return drawn


# --------------------------------------------------------------------------- #
# Rows: the vector rides on the row.
# --------------------------------------------------------------------------- #
def pack(vector) -> str:
    """One vector as the base64 of its `float16` bytes, little-endian."""
    import numpy

    return base64.b64encode(numpy.asarray(vector, dtype="<f2").tobytes()).decode("ascii")


def unpack(text: str):
    """The vector a row carries, back as `float32` for arithmetic."""
    import numpy

    return numpy.frombuffer(base64.b64decode(text), dtype="<f2").astype(numpy.float32)


def row_of(source: dict, vector, picture: str, stamp: str, choices: dict) -> dict:
    """One stored row: the join, the picture it was read from, and the vector."""
    return {
        "schema": SCHEMA,
        "key": str(source["key"]),
        "partition": str(source["partition"]),
        "family": source["family"],
        "viewport": source["viewport"],
        "maxiter": int(source["maxiter"]),
        "ledger": source.get("ledger"),
        "location_p_ge3": source.get("p_ge3"),
        "picture": picture,
        "stamp": stamp,
        "choices": choices,
        "vector": pack(vector),
    }


def stored_keys(path: Path | None = None) -> set[str]:
    """Which locations the store already holds. No vector is decoded to answer it."""
    path = store_path() if path is None else Path(path)
    if not path.is_file():
        return set()
    keys = set()
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA:
                raise StoreRefused(f"{path}:{number}: schema {row.get('schema')!r}")
            keys.add(str(row["key"]))
    return keys


def read(path: Path | None = None) -> list[dict]:
    """Every stored row, vectors still packed."""
    path = store_path() if path is None else Path(path)
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _first_row(path: Path) -> list[dict]:
    """`[the store's first row]`, or `[]` where there is no store. One line read."""
    path = Path(path)
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return [json.loads(line)]
    return []


def load(path: Path | None = None):
    """`(rows, matrix)` — the store with its vectors unpacked into one array.

    The matrix is `float32` and every row of it is a unit vector, so a cosine
    between two locations is a dot product and the whole nearest-neighbour read
    is one matrix multiply.
    """
    import numpy

    rows = read(path)
    if not rows:
        return [], numpy.zeros((0, 0), dtype=numpy.float32)
    matrix = numpy.stack([unpack(row["vector"]) for row in rows])
    return rows, matrix


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def build(
    limit: int | None = None,
    device: str = "auto",
    sample: int | None = None,
    seed: int = SAMPLE_SEED,
    unit_seconds: float = UNIT_SECONDS,
    leg: int = LEG,
    log=print,
) -> dict:
    """Embed every admitted location the store does not already hold.

    Incremental and idempotent: the population is read, the keys already stored
    are subtracted, and what is left is rendered, encoded and appended. A second
    call with nothing new to do makes no picture and writes no row.

    `sample` takes a stratified draw of the outstanding population instead of all
    of it — the pilot — and `limit` takes a prefix, which is the cheaper thing to
    ask for when the question is only *does this run*.

    **Takes the lock first.** Two of these appending to one JSONL do not collide
    loudly: they compute the same outstanding list, render the same pictures, and
    interleave half-written rows into the store, which then has duplicate keys
    and lines that will not parse. This leg is forty minutes long and it is
    launched in the background, which is exactly the shape of thing that gets
    started twice.
    """
    from fractal_wallpapers.models import train

    neutral.check_map()
    choices = neutral.choices()
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = train.claim(path.parent, name=LOCK_NAME)
    try:
        return _fill(path, choices, limit, device, sample, seed, unit_seconds, leg, log)
    finally:
        lock.unlink(missing_ok=True)


def _fill(path, choices, limit, device, sample, seed, unit_seconds, leg, log) -> dict:
    """The leg itself, inside the lock [`build`] took."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.models import embedding, train

    population = admitted()
    already = stored_keys(path)
    outstanding = [row for row in population if str(row["key"]) not in already]
    log(
        f"{len(population):,} admitted over the junk floor ({floors.JUNK_FLOOR:g}); "
        f"{len(already):,} already embedded; {len(outstanding):,} outstanding"
    )
    if sample is not None:
        outstanding = stratified(outstanding, sample, seed)
        log(f"stratified draw of {len(outstanding):,}, seed {seed}")
    if limit is not None:
        outstanding = outstanding[:limit]

    started = time.monotonic()
    if not outstanding:
        # The idempotent call, which is the ordinary one after the first leg. It
        # still counts the store against the population and still reports the
        # stamp — read off the store rather than recomputed, because the question
        # a second call answers is what is in there, not what a fresh one would
        # put there. No encoder is loaded and no picture is made.
        log("nothing to do")
        standing = _first_row(path)
        return _report(
            path,
            population,
            (standing[0].get("choices") if standing else choices),
            None,
            0,
            0.0,
            0.0,
            time.monotonic() - started,
            stamp=(str(standing[0].get("stamp")) if standing else None),
        )

    model = embedding.build()
    where = train.device_of(device)
    model = model.to(where)
    config = embedding.data_config(model)
    encoder = embedding.describe(model, device=where)
    marked = neutral.stamp(
        {"variant": encoder["variant"], "dim": encoder["dim"], "precision": encoder["precision"]}
    )
    _refuse_a_second_provenance(path, marked)
    log(f"{encoder['variant']} on {where}: {encoder['dim']} dimensions, {encoder['precision']}")
    log(f"stamp {marked}: {json.dumps(choices, sort_keys=True)}")

    wrote = 0
    render_seconds = embed_seconds = 0.0
    killed: list[str] = []
    refused: list[dict] = []
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for start in range(0, len(outstanding), leg):
            chunk = outstanding[start : start + leg]
            drawn, pictures = [], []
            clock = time.monotonic()
            for source in chunk:
                # Two ways one location does not become a picture, and they are
                # different problems: a hung render killed at the deadline, and a
                # render the engine refused. Neither may stop a leg of
                # twenty-five thousand — a leg that died on one bad row would die
                # on it again on every resume — so both are recorded and skipped.
                try:
                    with engine.deadline(unit_seconds):
                        picture, _ = neutral.render_neutral(source)
                except engine.EngineTimeout:
                    killed.append(str(source["key"]))
                    continue
                except RuntimeError as failure:
                    refused.append({"key": str(source["key"]), "why": str(failure)[:200]})
                    continue
                drawn.append(source)
                pictures.append(picture)
            render_seconds += time.monotonic() - clock
            if not drawn:
                continue
            clock = time.monotonic()
            vectors = embedding.encode(
                model, pictures, where, config["mean"], config["std"], embedding.BATCH
            )
            embed_seconds += time.monotonic() - clock
            for source, picture, vector in zip(drawn, pictures, vectors, strict=True):
                handle.write(
                    json.dumps(
                        row_of(source, vector, picture.name, marked, choices), ensure_ascii=False
                    )
                    + "\n"
                )
            handle.flush()
            wrote += len(drawn)
            done = start + len(chunk)
            log(
                f"{done:,}/{len(outstanding):,}: {wrote:,} written, "
                f"{render_seconds / max(wrote, 1):.3f} s/location rendering, "
                f"{embed_seconds / max(wrote, 1):.3f} s/location encoding"
            )

    if killed:
        log(f"{len(killed)} locations were killed at the {unit_seconds:g}s render deadline")
    for cell in refused:
        log(f"REFUSED {cell['key']}: {cell['why']}")
    return _report(
        path,
        population,
        choices,
        encoder,
        wrote,
        render_seconds,
        embed_seconds,
        time.monotonic() - started,
        killed=killed,
        refused=refused,
        stamp=marked,
    )


def _refuse_a_second_provenance(path: Path, marked: str) -> None:
    """Refuse to append under a stamp the store does not already carry.

    Reads one line rather than the store: the first row's stamp settles it, and
    every row after it is a kilobyte of base64 nothing here needs to see.
    """
    for row in _first_row(path):
        if str(row.get("stamp")) != marked:
            raise StoreRefused(
                f"{path} holds rows stamped {row.get('stamp')!r} and this leg would append "
                f"{marked!r}. Something in the frozen choices moved — the colormap, the "
                f"geometry, the mode, the encoder or its dimension — and a cosine between "
                f"the two stamps is arithmetic between unrelated numbers. Move the store "
                f"aside and rebuild it, or put the choice back."
            )


def _report(
    path: Path,
    population: list[dict],
    choices: dict,
    encoder: dict | None,
    wrote: int,
    render_seconds: float,
    embed_seconds: float,
    wall: float,
    killed: list[str] | None = None,
    refused: list[dict] | None = None,
    stamp: str | None = None,
) -> dict:
    """What the leg did, and whether the store now covers the population.

    The count verification is the point: a store that is one location short of
    its population is a gallery pass that silently cannot choose that place.
    """
    stored = stored_keys(path)
    wanted = {str(row["key"]) for row in population}
    missing = wanted - stored
    pool = judged_pool()
    return {
        "store": str(path),
        "stamp": stamp,
        "choices": choices,
        "encoder": encoder,
        "admitted": len(wanted),
        # The other population, and it is not this store's denominator: a judged
        # location the admitted set does not hold is a place the gallery pass
        # cannot select at all. `unreachable()` says which, and why.
        "judged_pool": {
            "judged": len(pool),
            "stored": len(set(pool) & stored),
            "unreachable": len(set(pool) - wanted),
        },
        "stored": len(stored),
        "wrote": wrote,
        "missing": len(missing),
        "complete": not missing,
        "killed": list(killed or ()),
        "refused": list(refused or ()),
        "seconds": {
            "render": round(render_seconds, 2),
            "encode": round(embed_seconds, 2),
            "wall": round(wall, 2),
            "render_per_location": round(render_seconds / wrote, 4) if wrote else None,
            "encode_per_location": round(embed_seconds / wrote, 4) if wrote else None,
        },
    }


# --------------------------------------------------------------------------- #
# The sanity read.
# --------------------------------------------------------------------------- #
def neighbours(k: int = 3, sample: int = 10, seed: int = SAMPLE_SEED, path=None) -> dict:
    """`k` nearest neighbours by cosine for `sample` random rows, with their pictures.

    The cheapest possible answer to the only question that matters about this
    store: does "near in this space" mean "looks alike"? It is not answered here
    — it is answered by somebody opening the JPEGs this names.
    """
    import random

    import numpy

    rows, matrix = load(path)
    if len(rows) <= k:
        raise StoreRefused(f"the store holds {len(rows)} rows, which is not enough for {k}")
    picked = random.Random(seed).sample(range(len(rows)), min(sample, len(rows)))
    out = []
    for index in picked:
        cosines = matrix @ matrix[index]
        cosines[index] = -numpy.inf
        near = numpy.argsort(-cosines)[:k]
        out.append(
            {
                "key": rows[index]["key"],
                "partition": rows[index]["partition"],
                "picture": rows[index]["picture"],
                "nearest": [
                    {
                        "key": rows[int(other)]["key"],
                        "partition": rows[int(other)]["partition"],
                        "picture": rows[int(other)]["picture"],
                        "cosine": round(float(cosines[int(other)]), 4),
                    }
                    for other in near
                ],
            }
        )
    return {
        "rows": len(rows),
        "pictures": str(neutral.neutral_dir()),
        "seed": seed,
        "background": background(matrix, seed=seed),
        "sample": out,
    }


#: Random pairs drawn to measure what an ordinary cosine looks like in this store.
BACKGROUND_PAIRS = 20_000


def background(matrix, pairs: int = BACKGROUND_PAIRS, seed: int = SAMPLE_SEED) -> dict:
    """What the cosine between two unrelated locations looks like, in quantiles.

    Without this the neighbour sample says nothing. A list of nearest neighbours
    at 0.96 reads as "barely distinguishable" until the background turns out to
    sit at 0.73 — and it would read as "well separated" on a store whose whole
    population sat at 0.96, which is the degenerate case this measurement is here
    to catch. It is also the first thing the gallery pass's hard radius has to be
    chosen against.
    """
    import numpy

    rows = matrix.shape[0]
    if rows < 2:
        return {"pairs": 0}
    rng = numpy.random.default_rng(seed)
    left, right = rng.integers(0, rows, pairs), rng.integers(0, rows, pairs)
    keep = left != right
    cosines = (matrix[left[keep]] * matrix[right[keep]]).sum(1)
    return {
        "pairs": int(keep.sum()),
        "min": round(float(cosines.min()), 4),
        "p01": round(float(numpy.percentile(cosines, 1)), 4),
        "median": round(float(numpy.median(cosines)), 4),
        "p99": round(float(numpy.percentile(cosines, 99)), 4),
        "max": round(float(cosines.max()), 4),
    }


def cover(keys, path=None) -> dict:
    """How many of `keys` the store holds, and which it does not.

    For asking a named population — the judged pool, say — whether the gallery
    pass can reach all of it.
    """
    stored = stored_keys(path)
    wanted = {str(key) for key in keys}
    return {
        "asked": len(wanted),
        "stored": len(wanted & stored),
        "absent": sorted(wanted - stored),
    }


__all__ = [
    "BACKGROUND_PAIRS",
    "LEG",
    "SAMPLE_SEED",
    "SCHEMA",
    "STORE_NAME",
    "UNIT_SECONDS",
    "StoreRefused",
    "admitted",
    "admitted_only",
    "background",
    "backup_path",
    "build",
    "cover",
    "judged_pool",
    "load",
    "manifest_path",
    "neighbours",
    "pack",
    "read",
    "row_of",
    "store",
    "store_path",
    "stored_keys",
    "stratified",
    "unpack",
    "unreachable",
]
