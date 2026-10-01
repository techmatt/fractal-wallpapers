"""Moving the pool's pictures to the archive, one file at a time, behind the kept ones.

`curation` is the live pool and never leaves the hot tier, so `storage archive`
cannot take it — and nearly all of its bytes are candidate JPEGs that nothing
reads between mines. This is the one move finer than a top-level name: a picture
at `curation/<group>/<leg>/pictures/<file>` is copied to the same place under
`pool_pictures/`, which is a top-level name like any other and lives on the
archive tier. `paths.Tiers.resolve` answers a pool picture from its hot copy
where there is one and from the mirror where there is not, so no record changes
and no reader is told.

## What moves and what stays

A picture moves when a candidate ledger row names it, its key is not protected
(`tentative.protected_keys()`: every kept record's seats and every pin), no kept
record's row names its file, and no `<stem>.leveled/` sits beside it. The last
is a guard rather than a rule: the levelled colormaps outside the kept set were
swept on 2026-09-30, and a picture with one is a picture somebody acted on. What
no ledger row names is not this command's business — it is `curate
candidate-ledger orphans`'.

## Copy, verify, then delete — and the delete is its own command

`archive` copies and verifies; it deletes nothing. `prune-hot` deletes the hot
copies, and re-checks each one against its mirror at the moment of deleting it:
the mirror file is there and the same size, and the key is still unprotected.
Between the two a picture is in both places, which is safe because hot wins.

## Restore, for a reader that cannot see the mirror

`restore --list <file>` brings named pictures back hot and out of the mirror, so a
later `prune-hot` cannot take them again. **The website is that reader**: its
builder resolves through its own copy of the tiers, which has no mirror, and its
figures pin seats of records that are not on the keep list. Fifty-six such seats'
pictures went to the mirror on 2026-09-30, `builder check`'s `seats` went red, and
they were restored. A new `archive` run plans them again — it reads protection off
`tentative.protected_keys()`, which those records are not in — so the run after
the next mine re-checks `builder check` before `prune-hot`.

## The record

`<archive>/pool_pictures/moved.jsonl`, one row a picture moved: the stored name,
its key and its size. It lives in the mirror because it is a fact about the
mirror, and it is what `prune-hot` and `status` read.
"""

from __future__ import annotations

import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

from fractal_wallpapers.paths import (
    ARCHIVE,
    POOL_NAME,
    POOL_PICTURES_NAME,
    ArchiveUnreachable,
    StorageRefusal,
    Tiers,
    is_pool_picture,
    stored_parts,
)

SCHEMA = 1
MOVED_NAME = "moved.jsonl"

#: The seeded byte check after the copy. Same size and seed as `storage.verify`.
SAMPLE_FILES = 400
SAMPLE_SEED = 0


class MirrorError(StorageRefusal):
    """The mirror cannot be made, or was made and does not verify."""


def _reachable_tiers() -> Tiers:
    tiers = Tiers.current()
    if tiers.archive is None:
        raise MirrorError("no archive root is configured, so there is nowhere to mirror to.")
    if not tiers.archive_is_reachable:
        raise ArchiveUnreachable(f"the archive at {tiers.archive} is not there. Plug it in.")
    return tiers


def moved_path(tiers: Tiers) -> Path:
    """The record of what the mirror holds, inside the mirror on the archive."""
    return tiers.archive / POOL_PICTURES_NAME / MOVED_NAME


def read_moved(tiers: Tiers) -> list[dict]:
    where = moved_path(tiers)
    if not where.is_file():
        return []
    with where.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def protected() -> tuple[set, set]:
    """`({protected key}, {file name a kept record's row names})`, read fresh."""
    from fractal_wallpapers.curation import tentative

    keys = tentative.protected_keys()
    names: set = set()
    for stamp in tentative.kept():
        for row in tentative.read_rows(stamp):
            for holder in (row, row.get("seat") or {}):
                stored = holder.get("picture") if isinstance(holder, dict) else None
                if stored:
                    names.add(str(stored).replace("\\", "/").rsplit("/", 1)[-1])
    return keys, names


def plan(tiers: Tiers, log=print) -> list[dict]:
    """Every picture that would move: `{key, picture, parts, bytes}`, in path order."""
    from fractal_wallpapers.curation import candidate_ledger
    from fractal_wallpapers.curation.candidate_ledger.store import POOL_SUBTREES

    keys, names = protected()
    log(f"[pictures] {len(keys):,} protected keys, {len(names):,} file names kept records name")
    wanted: dict = defaultdict(dict)
    skipped = defaultdict(int)
    for row in candidate_ledger.stream():
        stored = row.get("picture")
        parts = stored_parts(stored) if stored else None
        if not parts or not is_pool_picture(parts) or parts[1] not in POOL_SUBTREES:
            skipped["not a pool picture"] += 1
            continue
        if str(row["key"]) in keys or parts[4] in names:
            skipped["kept"] += 1
            continue
        wanted[tuple(parts[:4])][parts[4]] = {"key": str(row["key"]), "picture": str(stored)}

    out = []
    for directory, files in sorted(wanted.items()):
        here = tiers.in_place(directory)
        try:
            listing = {entry.name: entry for entry in os.scandir(here)}
        except OSError:
            skipped["no hot directory"] += len(files)
            continue
        for name, row in sorted(files.items()):
            entry = listing.get(name)
            if entry is None or not entry.is_file(follow_symlinks=False):
                skipped["not on the hot tier"] += 1
                continue
            if f"{Path(name).stem}.leveled" in listing:
                skipped["has a levelled colormap"] += 1
                continue
            out.append({**row, "parts": [*directory, name], "bytes": entry.stat().st_size})
    log(
        f"[pictures] {len(out):,} pictures, {sum(r['bytes'] for r in out) / 2**30:.2f} GiB, "
        f"would move; left: {dict(skipped)}"
    )
    return out


def _copy_one(source: Path, target: Path) -> None:
    import shutil

    temporary = target.with_name(f"{target.name}.copying")
    shutil.copy2(source, temporary)
    temporary.replace(target)


def archive(log=print) -> dict:
    """Copy every planned picture into the mirror and verify it. Deletes nothing.

    Resumable: a picture already in the mirror at the same size is not copied
    again, and the copy lands under a temporary name and is renamed into place, so
    a killed run leaves no file whose presence is a lie.
    """
    from concurrent.futures import ThreadPoolExecutor

    from fractal_wallpapers.storage import WORKERS, bytes_said_plainly, duration_said_plainly

    tiers = _reachable_tiers()
    moving = plan(tiers, log=log)
    if not moving:
        return {"planned": 0}
    mirror_root = tiers.archive / POOL_PICTURES_NAME
    if tiers.tier_of(POOL_PICTURES_NAME) not in (None, ARCHIVE):
        raise MirrorError(f"{POOL_PICTURES_NAME} is hot; restore is not this command's job.")
    pairs = [
        (tiers.in_place(row["parts"]), mirror_root.joinpath(*row["parts"][1:])) for row in moving
    ]
    for directory in sorted({target.parent for _, target in pairs}):
        directory.mkdir(parents=True, exist_ok=True)

    todo = []
    for (source, target), row in zip(pairs, moving, strict=True):
        try:
            if target.stat().st_size == row["bytes"]:
                continue
        except OSError:
            pass
        todo.append((source, target, row["bytes"]))
    total = sum(size for _, _, size in todo)
    log(
        f"[pictures] {len(todo):,} to copy ({bytes_said_plainly(total)}); "
        f"{len(pairs) - len(todo):,} already mirrored"
    )

    started = time.perf_counter()
    done = written = 0
    step = max(len(todo) // 200, 1)

    def one(job):
        source, target, size = job
        _copy_one(source, target)
        return size

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for size in pool.map(one, todo):
            done += 1
            written += size
            if done % step == 0 or done == len(todo):
                elapsed = max(time.perf_counter() - started, 1e-6)
                left = (len(todo) - done) / max(done / elapsed, 1e-6)
                log(
                    f"[pictures] {done:,}/{len(todo):,} copied, {bytes_said_plainly(written)}, "
                    f"{done / elapsed:,.0f} files/s, ~{duration_said_plainly(left)} left"
                )

    # Written before the verify, so a verify that fails still leaves the record of
    # what was copied, and written whole: it is the mirror's list, not this run's.
    record = moved_path(tiers)
    temporary = record.with_name(f"{record.name}.writing")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in moving:
            handle.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "key": row["key"],
                        "picture": row["picture"],
                        "bytes": row["bytes"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    temporary.replace(record)

    report = verify(tiers, log=log)
    return {
        "planned": len(moving),
        "copied": len(todo),
        "copied_bytes": total,
        "seconds": round(time.perf_counter() - started, 1),
        **report,
    }


def verify(tiers: Tiers | None = None, log=print) -> dict:
    """Every recorded picture is in the mirror at its size; a seeded sample matches bytes.

    Per directory, as `storage.verify` is, so a disagreement says where. Compares
    against the hot copy where one is still there and against the recorded size
    where it is not, which is what makes this the check after `prune-hot` too.
    """
    from fractal_wallpapers.storage import sha256_of

    tiers = _reachable_tiers() if tiers is None else tiers
    rows = read_moved(tiers)
    if not rows:
        raise MirrorError(f"no {MOVED_NAME} in the mirror: nothing has been archived")
    mirror_root = tiers.archive / POOL_PICTURES_NAME
    by_directory: dict = defaultdict(lambda: [0, 0, 0, 0])
    absent: list = []
    hot_left = 0
    for row in rows:
        parts = stored_parts(row["picture"])
        target = mirror_root.joinpath(*parts[1:])
        cell = by_directory["/".join(parts[1:4])]
        cell[0] += 1
        cell[1] += row["bytes"]
        try:
            size = target.stat().st_size
        except OSError:
            size = None
        if size is not None:
            cell[2] += 1
            cell[3] += size
        if size != row["bytes"] and len(absent) < 5:
            absent.append(row["picture"])
        if tiers.in_place(parts).is_file():
            hot_left += 1
    disagree = {where: cell for where, cell in by_directory.items() if cell[:2] != cell[2:]}
    if disagree:
        raise MirrorError(
            f"{len(disagree)} directories differ, as [files, bytes, mirrored files, mirrored "
            f"bytes]: {list(disagree.items())[:5]}; e.g. {absent}"
        )
    log(
        f"[pictures] {len(by_directory)} directories, {len(rows):,} pictures in the mirror "
        f"at their recorded sizes; {hot_left:,} still have a hot copy"
    )
    draw = random.Random(SAMPLE_SEED).sample(rows, min(SAMPLE_FILES, len(rows)))
    compared = mismatched = 0
    for row in draw:
        parts = stored_parts(row["picture"])
        hot = tiers.in_place(parts)
        if not hot.is_file():
            continue
        compared += 1
        if sha256_of(hot) != sha256_of(mirror_root.joinpath(*parts[1:])):
            mismatched += 1
    if mismatched:
        raise MirrorError(f"{mismatched} of {compared} sampled pictures differ byte for byte")
    log(f"[pictures] sha256 of {compared} sampled pictures (seed {SAMPLE_SEED}) identical")
    return {
        "pictures": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "directories": len(by_directory),
        "hot_copies_left": hot_left,
        "sampled": compared,
        "sample_seed": SAMPLE_SEED,
    }


def prune_hot(apply: bool = False, log=print) -> dict:
    """Delete the hot copy of every mirrored picture, re-checking each as it goes.

    Per picture, at the moment of deleting: the mirror copy is a file of the
    recorded size, the hot copy is the same size, and the key is not protected
    now — protection read fresh here, not carried from the copy. A picture failing
    any of them is kept and counted. Dry run unless `apply`.
    """
    tiers = _reachable_tiers()
    rows = read_moved(tiers)
    if not rows:
        raise MirrorError(f"no {MOVED_NAME} in the mirror: nothing has been archived")
    keys, names = protected()
    mirror_root = tiers.archive / POOL_PICTURES_NAME
    out = {"recorded": len(rows), "deleted": 0, "bytes": 0, "already_gone": 0, "kept": 0}
    refusals: dict = defaultdict(int)
    for row in rows:
        parts = stored_parts(row["picture"])
        hot = tiers.in_place(parts)
        if parts[0] != POOL_NAME or not is_pool_picture(parts):
            refusals["not a pool picture"] += 1
            continue
        if row["key"] in keys or parts[4] in names:
            refusals["protected"] += 1
            continue
        try:
            hot_size = hot.stat().st_size
        except OSError:
            out["already_gone"] += 1
            continue
        try:
            mirrored = mirror_root.joinpath(*parts[1:]).stat().st_size
        except OSError:
            mirrored = None
        if mirrored != row["bytes"] or hot_size != row["bytes"]:
            refusals["size disagrees"] += 1
            continue
        if apply:
            hot.unlink()
        out["deleted"] += 1
        out["bytes"] += hot_size
        if apply and out["deleted"] % 50_000 == 0:
            log(f"[pictures] {out['deleted']:,} hot copies deleted")
    out["kept"] = sum(refusals.values())
    out["refusals"] = dict(refusals)
    out["applied"] = bool(apply)
    out["gib"] = round(out["bytes"] / 2**30, 2)
    verb = "deleted" if apply else "would delete"
    log(f"[pictures] {verb} {out['deleted']:,} hot copies, {out['gib']} GiB; kept {dict(refusals)}")
    return out


def restore(named, log=print) -> dict:
    """Bring these pictures back to the hot tier, whole: copy, check, then drop the mirror.

    `named` is stored names (`artifacts/curation/...`). Each is copied back hot, its
    size checked against the record, and only then is its mirror copy deleted and
    its row dropped from the record — so a restored picture is an ordinary hot
    picture again, and `prune-hot` will not take it a second time. The reason to
    use it is a reader outside this package that cannot see the mirror: the
    website's figures resolve through their own copy of the tiers.
    """
    tiers = _reachable_tiers()
    rows = read_moved(tiers)
    wanted = {"/".join(["artifacts", *stored_parts(name)]) for name in named}
    mirror_root = tiers.archive / POOL_PICTURES_NAME
    out = {"asked": len(wanted), "restored": 0, "bytes": 0, "not_mirrored": 0}
    keep = []
    for row in rows:
        stored = "/".join(["artifacts", *stored_parts(row["picture"])])
        if stored not in wanted:
            keep.append(row)
            continue
        wanted.discard(stored)
        parts = stored_parts(stored)
        source, target = mirror_root.joinpath(*parts[1:]), tiers.in_place(parts)
        if not target.is_file():
            _copy_one(source, target)
        if target.stat().st_size != row["bytes"]:
            raise MirrorError(f"{target} came back at the wrong size; the mirror copy is kept")
        source.unlink()
        out["restored"] += 1
        out["bytes"] += row["bytes"]
    out["not_mirrored"] = len(wanted)
    record = moved_path(tiers)
    temporary = record.with_name(f"{record.name}.writing")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in keep:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(record)
    log(f"[pictures] restored {out['restored']:,} hot; {out['not_mirrored']} were not mirrored")
    return out


def status() -> dict:
    """What the mirror holds and how much of it is still hot as well."""
    tiers = Tiers.current()
    if not tiers.archive_is_reachable:
        return {"archive_reachable": False}
    rows = read_moved(tiers)
    hot_left = sum(1 for row in rows if tiers.in_place(stored_parts(row["picture"])).is_file())
    return {
        "archive_reachable": True,
        "mirror": str(tiers.archive / POOL_PICTURES_NAME),
        "pictures": len(rows),
        "bytes": sum(row["bytes"] for row in rows),
        "hot_copies_left": hot_left,
    }


__all__ = [
    "MirrorError",
    "archive",
    "plan",
    "protected",
    "prune_hot",
    "restore",
    "status",
    "verify",
]
