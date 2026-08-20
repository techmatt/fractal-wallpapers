"""Moving a subtree between the two tiers, and saying where everything is.

`paths` decides *where a name resolves*. This module is the only thing that
changes the answer: it copies a top-level subtree from one tier to the other,
verifies the copy, and only then deletes the source. Everything else in the
project reads the tree; nothing else moves it.

## The order is the whole design

Copy → verify → delete, in that order and never overlapped. A move that deleted
as it went would, on any interruption, leave a subtree that is half in each tier
— and tier resolution asks "is this name there", so both tiers would answer yes
and the collision guard would be the only thing standing between that and a
silently wrong read. Copying first means an interruption leaves the source
intact and the destination incomplete, which is the recoverable direction: run
the move again.

## What "verified" means here

Three checks, because each catches something the others do not:

* **per-directory file count and byte total** — the cheap structural check, and
  the one that catches a copy that stopped early. Per directory rather than in
  total, so a discrepancy names where it is;
* **manifest resolution** — a tile manifest names a third of a million files.
  After the move those names have to resolve, through the same `rehome` every
  reader uses, to files that are actually on the destination. This is the check
  that would have caught the manifest storing absolute paths, which nothing
  structural could see;
* **sampled sha256** — bytes, not metadata. A seeded sample, and the seed is in
  the report, because "we checked 600 files" is only reproducible if somebody
  can say which 600.

## It says how long it will take before it starts

The archive is a USB hard drive: about 55 small-file reads a second on one
thread, roughly 120 with concurrency, against 1,500 on the system NVMe. A
restore of the tile cache is therefore *hours*, and an operator who finds that
out forty minutes in has been misled by a tool that knew.

So a move measures itself before it commits to the wait — but the measurement is
a slice of the real copy, actual files, copied once and counted rather than read
and thrown away. That way it times the whole path, source read and destination
write at the concurrency the rest will use, rather than a read-only rehearsal
that would have measured the SSD on the way out and quoted an archiving operator
a number with nothing to do with what they were about to wait for. The estimate
is the larger of the two bounds it implies, because a subtree of a million small
files is seek-bound and a subtree of a few large ones is bandwidth-bound, and
only one of those numbers is the truth for any given subtree. What it actually
took is printed beside what it predicted.

The slice is a contiguous run at a seeded offset rather than a seeded sample of
the whole subtree, and that distinction cost a factor of seventeen before it was
fixed: the copy walks in sorted order, a random draw does not, and timing the
seeks a random draw forces measures something the copy never does.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fractal_wallpapers.paths import (
    ARCHIVE,
    ARTIFACTS_NAME,
    HOT,
    ArchiveUnreachable,
    StorageRefusal,
    Tiers,
    archive_root,
    rehome,
)

#: How many files the copy times itself over before it forecasts the rest, and
#: how many the verification hashes on both sides afterwards. The first is small
#: because a forecast is worth little; the second is not, because it is the only
#: check that reads bytes.
PROBE_FILES = 64
SAMPLE_FILES = 400

#: The draw both of those are taken under. Recorded in the report: a sample
#: nobody can redraw is a claim nobody can check.
SAMPLE_SEED = 0

#: Concurrent copies. The archive saturates by about four threads — it is
#: seek-bound, and concurrency buys roughly a factor of two, not a factor of the
#: thread count — so this is deliberately small. It is not a tuning knob so much
#: as an admission that one thread leaves half the disk's throughput unused.
WORKERS = 8


#: Named once so the two places that tell an operator how to configure an archive
#: cannot drift apart.
ARCHIVE_KEY_HINT = "archive_root in local.toml"


class StorageError(StorageRefusal):
    """A move cannot be made, or was made and did not verify."""


def bytes_said_plainly(count: int) -> str:
    """A byte count as a person reads it. GiB, because that is what disks report."""
    size = float(count)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.2f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def duration_said_plainly(seconds: float) -> str:
    """A duration as a person reads it, at the resolution the number deserves."""
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 90 * 60:
        return f"{seconds / 60:.1f} min"
    return f"{seconds / 3600:.1f} h"


def walk_files(root: Path) -> list[Path]:
    """Every file below `root`, in sorted order. Directories are not files here.

    Sorted so that two walks of the same tree — the source's and the
    destination's — line up row for row, and so a seeded sample drawn from one
    is the same sample drawn from the other.
    """
    found: list[Path] = []
    for here, _, names in os.walk(root):
        found.extend(Path(here) / name for name in names)
    found.sort()
    return found


def weigh(root: Path) -> dict[str, tuple[int, int]]:
    """`{directory relative to root: (files, bytes)}` — the structural fingerprint.

    Per directory rather than one total, because a total that disagrees says only
    that something is wrong and this says where.
    """
    tally: dict[str, tuple[int, int]] = {}
    for here, _, names in os.walk(root):
        where = Path(here).relative_to(root).as_posix()
        size = 0
        for name in names:
            try:
                size += (Path(here) / name).stat().st_size
            except OSError:
                size += 0
        tally[where] = (len(names), size)
    return tally


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def estimate(files: int, total_bytes: int, rates: tuple[float, float]) -> float:
    """Seconds the copy should take, at the rates the probe measured."""
    per_file, per_byte = rates
    by_count = files / per_file if per_file else 0.0
    by_bytes = total_bytes / per_byte if per_byte else 0.0
    return max(by_count, by_bytes)


def copy_tree(source: Path, destination: Path, files: list[Path], log=None) -> tuple[int, float]:
    """Copy these files, preserving the tree below `source`. `(bytes, seconds)`.

    Concurrent, and deliberately only a little: see `WORKERS`. Each file goes
    through `shutil.copy2` so timestamps survive, and every parent directory is
    made before the pool starts — a thread pool racing on `mkdir` is a class of
    bug this does not need to have.

    `log=None` copies silently, which is what the throughput probe wants: it is
    the first slice of the real copy rather than a separate measurement, so its
    files are copied once, by this, and counted.
    """
    for where in sorted({path.parent.relative_to(source) for path in files}):
        (destination / where).mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)

    written = 0
    done = 0
    started = time.perf_counter()
    step = max(len(files) // 20, 1)

    def one(path: Path) -> int:
        target = destination / path.relative_to(source)
        shutil.copy2(path, target)
        return target.stat().st_size

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for size in pool.map(one, files):
            written += size
            done += 1
            if log is not None and (done % step == 0 or done == len(files)):
                elapsed = max(time.perf_counter() - started, 1e-6)
                log(
                    f"  {done:,}/{len(files):,} files, {bytes_said_plainly(written)}, "
                    f"{done / elapsed:,.0f} files/s, "
                    f"{bytes_said_plainly(int(written / elapsed))}/s"
                )
    return written, max(time.perf_counter() - started, 1e-6)


def manifest_rows_resolve(destination: Path, unit: str, tiers: Tiers, log=print) -> dict:
    """Every path a manifest under this subtree names, resolved and checked.

    Only manifests that name files are read — a manifest of rows with no `path`
    is a record of something else and is skipped rather than guessed at. The
    resolution goes through `rehome` against a `Tiers` snapshot that already
    places this subtree at its destination, which is the same funnel every reader
    uses: this checks that the readers will find the files, not merely that some
    files are present.
    """
    checked = 0
    absent: list[str] = []
    found = sorted(destination.rglob("manifest*.jsonl"))
    if not found:
        log("  no manifest under this subtree; nothing here names files by path")
    for manifest in found:
        with manifest.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                stored = json.loads(line).get("path")
                if not stored:
                    continue
                where = rehome(stored, tiers)
                checked += 1
                if (where is None or not where.is_file()) and len(absent) < 5:
                    absent.append(stored)
        log(f"  {manifest.name}: {checked:,} rows resolved, {len(absent)} absent")
    if absent:
        raise StorageError(
            f"{ARTIFACTS_NAME}/{unit}: {len(absent)}+ manifest rows do not resolve to a file "
            f"at the destination, e.g. {absent}. Nothing was deleted."
        )
    return {"manifest_rows": checked}


def verify(source: Path, destination: Path, unit: str, tiers: Tiers, log=print) -> dict:
    """The three checks, in cost order. Raises rather than returning a verdict.

    Raising is the point: the caller's next statement deletes the source, and a
    boolean somebody forgot to read is how that happens anyway.
    """
    log("verifying: per-directory counts and bytes")
    here, there = weigh(source), weigh(destination)
    disagree = {
        where: (here.get(where), there.get(where))
        for where in sorted(set(here) | set(there))
        if here.get(where) != there.get(where)
    }
    if disagree:
        first = list(disagree.items())[:5]
        raise StorageError(
            f"{ARTIFACTS_NAME}/{unit}: {len(disagree)} directories differ between the tiers, "
            f"as (files, bytes) source vs destination: {first}. Nothing was deleted."
        )
    files = walk_files(source)
    total = sum(count for count, _ in here.values())
    log(f"  {len(here):,} directories, {total:,} files identical in count and bytes")

    log("verifying: manifest rows resolve at the destination")
    manifests = manifest_rows_resolve(destination, unit, tiers, log=log)

    log(f"verifying: sha256 of a seeded sample ({SAMPLE_FILES} files, seed {SAMPLE_SEED})")
    draw = random.Random(SAMPLE_SEED).sample(files, min(SAMPLE_FILES, len(files)))
    mismatched = []
    for path in draw:
        twin = destination / path.relative_to(source)
        if sha256_of(path) != sha256_of(twin):
            mismatched.append(path.relative_to(source).as_posix())
    if mismatched:
        raise StorageError(
            f"{ARTIFACTS_NAME}/{unit}: {len(mismatched)} sampled files differ byte for byte, "
            f"e.g. {mismatched[:5]}. Nothing was deleted."
        )
    log(f"  {len(draw):,} sampled files byte-identical")
    return {
        "directories": len(here),
        "files": total,
        "bytes": sum(size for _, size in here.values()),
        "sampled": len(draw),
        "sample_seed": SAMPLE_SEED,
        **manifests,
    }


def move(unit: str, *, to: str, log=print) -> dict:
    """Move one top-level subtree to the named tier. Copy, verify, then delete.

    `to` is `HOT` or `ARCHIVE`. The subtree must currently be in the other one:
    a name already where it is asked to go is a no-op and says so, and a name in
    neither tier is a typo, not a move.
    """
    tiers = Tiers.current()
    if to not in (HOT, ARCHIVE):
        raise StorageError(f"{to!r} is not a tier; there are two, {HOT} and {ARCHIVE}.")
    if tiers.archive is None:
        raise StorageError(
            f"no archive root is configured, so there is nowhere to move {unit} to or from. "
            f"Set {ARCHIVE_KEY_HINT}."
        )
    if not tiers.archive_is_reachable:
        raise ArchiveUnreachable(
            f"the archive at {tiers.archive} is not there, so nothing can be moved to or "
            "from it. Plug it in."
        )

    where = tiers.tier_of(unit)
    if where is None:
        raise StorageError(
            f"{ARTIFACTS_NAME}/{unit} is in neither tier — there is nothing there to move. "
            f"`storage status` lists the names that exist."
        )
    if where == to:
        log(f"{ARTIFACTS_NAME}/{unit} is already {to}. Nothing to do.")
        return {"unit": unit, "tier": to, "moved": False}

    source = (tiers.hot if where == HOT else tiers.archive) / unit
    destination = (tiers.hot if to == HOT else tiers.archive) / unit
    if destination.exists():
        raise StorageError(
            f"{destination} already exists, and this move would write into it. That is the "
            "collision this whole mechanism refuses; look at it and decide which copy is "
            "the truth."
        )

    if not source.is_dir():
        raise StorageError(
            f"{source} is a file, not a subtree. The unit these commands move is a top-level "
            f"directory of the tree; a loose file at the root of it belongs to nothing and "
            f"is better deleted than tiered."
        )

    log(f"{ARTIFACTS_NAME}/{unit}: {where} -> {to}")
    log(f"  from {source}")
    log(f"  to   {destination}")
    files = walk_files(source)
    if not files:
        raise StorageError(f"{source} holds no files. A move of nothing is not a move.")
    total_bytes = sum(path.stat().st_size for path in files)

    # The probe is the first slice of the real copy, not a rehearsal beside it:
    # it measures the whole path — reading the source and writing the
    # destination, at the concurrency the rest of the copy will use — and the
    # files it moves are moved, once. A read-only probe would have measured the
    # SSD on the way out and told an operator archiving to a USB disk a number
    # with no relationship to what they were about to wait for.
    #
    # A *contiguous run* at a seeded offset, not a seeded random sample of the
    # whole subtree. Both are fair samples of the population, but the copy walks
    # in sorted order and a random draw does not: measured that way, the forecast
    # is the cost of the seeks a random draw forces rather than the cost of the
    # work, which on one real restore over-quoted 4.9s as 87s. The offset is
    # seeded so the run is not always the same directory.
    start = random.Random(SAMPLE_SEED).randrange(max(1, len(files) - PROBE_FILES))
    draw = files[start : start + PROBE_FILES]
    probed_bytes, probed_in = copy_tree(source, destination, draw)
    rates = (len(draw) / probed_in, probed_bytes / probed_in)
    forecast = estimate(len(files), total_bytes, rates)
    log(
        f"  {len(files):,} files, {bytes_said_plainly(total_bytes)}. Measured on "
        f"{len(draw)} of them (seed {SAMPLE_SEED}): {rates[0]:,.0f} files/s, "
        f"{bytes_said_plainly(int(rates[1]))}/s."
    )
    log(f"  estimated: {duration_said_plainly(forecast)} for the copy. Starting.")

    already = set(draw)
    rest = [path for path in files if path not in already]
    written, copied_in = copy_tree(source, destination, rest, log=log)
    written += probed_bytes
    copied_in += probed_in
    log(
        f"copied {bytes_said_plainly(written)} in {duration_said_plainly(copied_in)} "
        f"({len(files) / copied_in:,.0f} files/s; estimate said "
        f"{duration_said_plainly(forecast)})"
    )

    # The snapshot the verification resolves against has to place this subtree at
    # its *destination*, which is where it is about to be — the source is still
    # on disk, so a fresh snapshot would see both and refuse for a collision that
    # is the move itself.
    settled = Tiers(tiers.hot, tiers.archive)
    settled.place(unit, destination)
    report = verify(source, destination, unit, settled, log=log)

    log(f"verified. Deleting the source copy at {source}")
    shutil.rmtree(source)
    return {
        "unit": unit,
        "from": where,
        "tier": to,
        "moved": True,
        "seconds": round(copied_in, 1),
        "files_per_second": round(len(files) / max(copied_in, 1e-6), 1),
        "estimated_seconds": round(forecast, 1),
        **report,
    }


def status(sizes: bool = True) -> dict:
    """Every top-level name of the tree, its tier, and what it holds.

    `sizes=False` skips the walk. Enumerating a million files on a USB hard drive
    is minutes of pure metadata reading, and an operator who only wants to know
    which tier something is on should not have to pay for that.
    """
    tiers = Tiers.current()
    rows = []
    for name in tiers.names():
        row: dict = {"name": name}
        try:
            row["tier"] = tiers.tier_of(name)
        except StorageRefusal as collision:
            row["tier"] = "BOTH"
            row["collision"] = str(collision)
            rows.append(row)
            continue
        where = tiers.unit(name)
        row["path"] = str(where)
        if sizes:
            if where.is_dir():
                weighed = weigh(where)
                row["files"] = sum(count for count, _ in weighed.values())
                row["bytes"] = sum(size for _, size in weighed.values())
            else:
                row["files"] = 1
                row["bytes"] = where.stat().st_size
        rows.append(row)
    return {
        "hot": str(tiers.hot),
        "archive": None if tiers.archive is None else str(tiers.archive),
        "archive_reachable": tiers.archive_is_reachable,
        "units": rows,
    }


def require_hot(*where: Path, what: str) -> None:
    """Refuse when any of these paths has resolved onto the archive tier.

    The rule "restore before you train" lives here rather than in anybody's
    memory. Training against the archive is not wrong, it is *slow* in a way that
    does not announce itself: the same pass that takes four minutes off the NVMe
    takes the better part of an hour off a USB hard drive, per epoch, and the
    only symptom is a job that looks like it hung.

    Takes the *already-resolved directory* each caller is about to read, not the
    name of a subtree. A caller pointed somewhere else — a test with its own
    thirty-two-tile corpus — is then asking about the place it will actually
    read, which is the only question worth answering, and the subtree to restore
    is read back off the path rather than restated beside it.
    """
    archive = archive_root()
    if archive is None:
        return
    archived = [
        Path(path).relative_to(archive).parts[0] for path in where if archive in Path(path).parents
    ]
    if not archived:
        return
    listing = "\n".join(f"  fractal-wallpapers storage restore {name}" for name in archived)
    raise StorageError(
        f"{what} reads {', '.join(f'{ARTIFACTS_NAME}/{name}' for name in archived)}, and that "
        f"is archived on slow storage. A training pass over it is a random small-file read "
        f"pattern — tens of minutes per epoch against a few minutes hot — so this refuses "
        f"instead of quietly taking all day:\n{listing}"
    )


__all__ = [
    "SAMPLE_FILES",
    "SAMPLE_SEED",
    "StorageError",
    "bytes_said_plainly",
    "duration_said_plainly",
    "move",
    "require_hot",
    "status",
    "verify",
    "weigh",
]
