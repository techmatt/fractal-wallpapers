"""Where a gallery pass's attempt rows live, and why the history does not hold them.

A pass makes attempts the way a run makes attempts, and both are **pool rows**:
the location, the recipe, the palette draw, the judge's verdict, on one line
carrying its whole join. The difference is how many. A run's attempt count is
bounded by a night's clock and lands in the low hundreds; a pass's is
`locations x heads x draws` over `n` slots, which at n=50 is 1,120 rows and at
n=500 is over ten thousand. At about 3.8 KB a row that is four megabytes now and
forty megabytes at the next size up, per pass, kept forever, against a 1 MiB
per-file history guard.

So the pass's gate store gets what the supply sidecar and the neutral-render
embeddings get, for the same reason and by the same mechanism
([`curation.durability`]): the rows live under `artifacts/`, a copy goes to the
archive tier, and what the history keeps is a **manifest** — the row count, the
bytes, the sha256, and the population the rows were made over. The manifest is a
couple of kilobytes and does not move with `n`.

## What is tracked, and what is not

```text
data/curation/gallery/<pass>/pass.json            the pass record — knobs, plan, retro
data/curation/gallery/<pass>/<partition>.jsonl    one row per slot
data/curation/gallery/<pass>/gate.manifest.json   this store's manifest
data/curation/release/<pass>/<partition>.jsonl    the winners, and only the winners
artifacts/curation/gallery/<pass>/gate.jsonl      every attempt the pass made
```

Everything tracked scales with `n`. Nothing tracked scales with the attempts, and
`tests/test_curation_gallery.py` pins that on a synthetic N=500 plan by writing
the same seats twice under two attempt counts an order of magnitude apart and
demanding the tracked bytes come out identical.

## Why the attempts are not also release rows

They used to be: a pass wrote a gate row for every attempt **and** a release row
for every scored attempt, so each attempt was recorded twice and the second copy
was the one in the history. The release store answers *which candidate took a
slot*, and a pass takes at most `n` of those decisions. What every other attempt
was — a row in the pool, judged, not seated — is what this store says, and the
arithmetic of the losing is on the slot: `eligible`, `below_floor`,
`location_served` per slot, in the tracked pass record. The denominator survives;
the duplicate does not.

A run still writes its passed-over rows into the tracked release store, and that
is not an inconsistency. A run's release decision is taken over its own night's
few hundred candidates and the whole point of recording the losers is that the
population will not exist again. A pass's population is the accumulated pool,
which is still there.

## One flat file, keyed and upserted

The tracked stores split on partition because a 1 MiB guard acts per file. This
one is not tracked, so it has no reason to split, and one file is what
[`durability.Durable`] measures and copies. Rows upsert by key exactly as the
tracked stores' do, so a resumed pass re-recording its first 842 attempts writes
the same bytes back rather than a second copy of them.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import durability, records
from fractal_wallpapers.paths import archive_root, hot_root, under

#: The schema this store's manifest carries.
SCHEMA = durability.SCHEMA

#: What the store is called inside a pass's directory, wherever that directory is.
STORE_NAME = "gate.jsonl"

#: The subtree every pass's store sits in, under the regenerable tree and under
#: the backup unit. Its own level rather than beside `runs/`, because a pass is
#: not a run and the two trees are read by different things.
UNIT = "gallery"

#: What a pass's own summary is called inside its tracked directory: the knobs it
#: ran under, the plan, the retro table, the geometry it released at. Nothing
#: writes one any more — the pass that wrote them is deleted — and four of them
#: are on record, so this is the name a reader opens one by.
RECORD_NAME = "pass.json"

#: What a pass id starts with, and the prefix the ordinal is read off.
PASS_PREFIX = "gallery"


class LayoutRefused(RuntimeError):
    """A pass's records are in the layout that predates the store split."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree every pass's gate store lives in, on whichever tier it is on."""
    return under("curation", UNIT)


def store_path(pass_id: str) -> Path:
    """One pass's gate store: every attempt it made, one row each."""
    return store_root() / str(pass_id) / STORE_NAME


def backup_path(pass_id: str) -> Path:
    """The durable copy, beside the sidecar's and the embedding store's.

    Off a root rather than through `under()`, for [`durability`]'s reason: a copy
    that resolved through the tiers would land on whichever tier the original is
    already on, which is the one place a second copy is no use.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / UNIT / str(pass_id) / STORE_NAME


def manifest_dir(pass_id: str) -> Path:
    """The pass's own tracked directory: its summary, its slot rows, this manifest."""
    return records.root() / UNIT / str(pass_id)


def manifest_path(pass_id: str) -> Path:
    """The tracked manifest: what one pass's gate store was, last time it was saved."""
    return manifest_dir(pass_id) / "gate.manifest.json"


def durable(pass_id: str) -> durability.Durable:
    """One pass's store as a [`durability.Durable`] — how it is saved and checked."""
    return durability.Durable(
        name=f"the gallery pass {pass_id}'s gate store",
        live=store_path(pass_id),
        copy=backup_path(pass_id),
        manifest=manifest_path(pass_id),
        why_not_tracked=(
            "one pool row per attempt at about 3.8 KB, and a pass makes locations x heads x "
            "draws of them per slot — 1,120 rows at n=50 and ten times that at n=500, "
            "against a 1 MiB per-file history guard, kept forever per pass. The manifest is "
            "what the history keeps: the row count, the bytes, the sha256, and the "
            "population the attempts were made over."
        ),
        save_command=f"fractal-wallpapers curate gallery-store save --pass {pass_id}",
        restore_command=f"fractal-wallpapers curate gallery-store restore --pass {pass_id}",
        # There is no rebuild, and the string has to say so rather than name a
        # command the CLI no longer has: `curate gallery` was the pass that made
        # these rows and it was retired on 2026-08-28 with the phase.
        rebuild_command=(
            "there is no rebuild — `curate gallery`, the pass that made these attempts, was "
            "retired on 2026-08-28 and the four passes it ran are history. Restore the copy"
        ),
        facts=_facts,
    )


def _facts(path: Path) -> dict:
    """The columns this store adds to its manifest: what the attempts were made over."""
    partitions: dict[str, int] = {}
    heads: dict[str, int] = {}
    verdicts: dict[str, int] = {}
    locations: set[str] = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            location = row.get("location") or {}
            name = str(location.get("partition"))
            partitions[name] = partitions.get(name, 0) + 1
            locations.add(str(location.get("key")))
            head = str((row.get("scores") or {}).get("head"))
            heads[head] = heads.get(head, 0) + 1
            verdict = str(row.get("verdict"))
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return {
        "stage": records.GATE,
        "locations": len(locations),
        "rows_by_partition": dict(sorted(partitions.items())),
        "rows_by_head": dict(sorted(heads.items())),
        "rows_by_verdict": dict(sorted(verdicts.items())),
    }


# --------------------------------------------------------------------------- #
# Reading and writing.
# --------------------------------------------------------------------------- #
def write(pass_id: str, rows) -> tuple[Path, int, int]:
    """Merge `rows` into one pass's store by key. `(path, total, new)`.

    [`records.upsert_file`], which is what the tracked stores are written with:
    same key, same ordering, same carry-forward of a verdict a person added. A
    re-run of the same pass writes byte-identical output.

    A pass with no attempts to record — `--no-attempts`, the dev affordance —
    leaves no file at all rather than an empty one, because an empty store and a
    store nobody has written are the same fact and only one of them needs a
    manifest to say so.
    """
    path = store_path(pass_id)
    if not rows and not path.is_file():
        return path, 0, 0
    total, new = records.upsert_file(path, rows)
    return path, total, new


def read(pass_id: str | None = None) -> list[dict]:
    """Every attempt row on record, or one pass's, in key order.

    `None` reads every pass, which is what the *next* pass needs: an earlier
    pass's attempts are standing pool candidates it can seat without rendering
    anything, exactly as an earlier run's released rows are.
    """
    names = [str(pass_id)] if pass_id is not None else stored_passes()
    rows = [row for name in names for row in _rows_of(store_path(name))]
    return sorted(rows, key=lambda row: str(row["key"]))


def record_path(pass_id: str) -> Path:
    """One pass's own summary, in the tracked tree beside its slot rows."""
    return manifest_dir(pass_id) / RECORD_NAME


def passes() -> list[str]:
    """Every pass on record, oldest ordinal first.

    Off the **tracked** records and not off the stores: a store lives under the
    regenerable tree and can be archived or absent, and the question every caller
    asks here — which passes exist, in which order — is a question about the
    history. [`stored_passes`] is the other one and they are not the same list.
    """
    directory = records.root() / UNIT
    if not directory.is_dir():
        return []
    return sorted(
        (entry.name for entry in directory.iterdir() if (entry / RECORD_NAME).is_file()),
        key=_ordinal,
    )


def _ordinal(name: str) -> tuple:
    """Sort key over pass names: the numbered ones in order, anything else last."""
    if name.startswith(PASS_PREFIX) and name[len(PASS_PREFIX) :].isdigit():
        return (0, int(name[len(PASS_PREFIX) :]), name)
    return (1, 0, name)


def stored_passes() -> list[str]:
    """Every pass with a store on this disk, by name."""
    root = store_root()
    if not root.is_dir():
        return []
    return sorted(entry.name for entry in root.iterdir() if (entry / STORE_NAME).is_file())


def _rows_of(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def save(pass_id: str, log=print) -> dict:
    """Copy the store to the durable tier and write its manifest. One claim, one call."""
    return durability.save(durable(pass_id), log=log)


def check(pass_id: str, log=print) -> dict:
    """Read the live store against its manifest, and name the disagreement."""
    return durability.check(durable(pass_id), log=log)


def restore(pass_id: str, force: bool = False, log=print) -> dict:
    """Bring the durable copy back, counted against the manifest before it is believed."""
    return durability.restore(durable(pass_id), force=force, log=log)


# --------------------------------------------------------------------------- #
# The layout that predates the split, and the refusal that names it.
# --------------------------------------------------------------------------- #
def old_layout(pass_id: str) -> dict | None:
    """What a pass still holds in the pre-split layout, or `None` if it is clean.

    Two symptoms and either one is enough. A **tracked gate directory** is the
    store this module took over. **Passed-over release rows** are the duplicate:
    one row per losing attempt in the history, which is the half that made a pass
    cost eight megabytes of tracked text.
    """
    gate = records.decisions_dir(records.GATE, pass_id)
    tracked_gate = sorted(gate.glob("*.jsonl")) if gate.is_dir() else []
    passed_over = [
        row
        for row in records.read_decisions(records.RELEASE, pass_id)
        if row.get("verdict") == records.PASSED_OVER
    ]
    if not tracked_gate and not passed_over:
        return None
    return {
        "pass": str(pass_id),
        "gate_dir": gate,
        "gate_files": tracked_gate,
        "passed_over": passed_over,
    }


def refuse_old_layout(pass_id: str) -> None:
    """Raise unless `pass_id`'s records are in the layout this module writes.

    Before anything is spent, and before a single row is written: a pass that ran
    over the old layout would upsert its winners into a directory still holding
    every attempt it passed over, and the store would come out both layouts at
    once.
    """
    found = old_layout(pass_id)
    if found is None:
        return
    raise LayoutRefused(
        f"{pass_id}'s records are in the layout that predates the store split: "
        f"{len(found['gate_files'])} tracked gate file(s) under "
        f"{found['gate_dir']} and {len(found['passed_over']):,} passed-over release row(s) "
        f"in the history. Attempt rows now live in {store_path(pass_id)}, untracked and "
        f"described by {manifest_path(pass_id)}, and the release store keeps the winners "
        f"alone. [`migrate`] below moves them — records only, nothing rendered. It is a "
        f"function and not a subcommand because the pass it served, `curate gallery`, was "
        f"retired on 2026-08-28: the four passes are history and every one of them was "
        f"moved before it became history, so this refusal fires only over records restored "
        f"from before the split."
    )


def migrate(pass_id: str, log=print) -> dict:
    """Move one pass out of the pre-split layout. Records only; nothing is rendered.

    The tracked gate rows become this store's rows; the release store is rewritten
    from the rows that actually took a slot. The release directory is **rewritten
    rather than upserted**, because an upsert never deletes and the whole point
    here is to drop the passed-over duplicates.
    """
    found = old_layout(pass_id)
    if found is None:
        log(f"[migrate] {pass_id} is already in the current layout; nothing to do")
        return {"pass": str(pass_id), "moved": 0, "dropped": 0, "kept": 0}

    moved = [row for path in found["gate_files"] for row in _rows_of(path)]
    if moved:
        path, total, new = write(pass_id, moved)
        log(f"[migrate] {len(moved):,} gate row(s) -> {path} ({total:,} rows, +{new:,})")
        save(pass_id, log=log)
    for path in found["gate_files"]:
        path.unlink()
    if found["gate_dir"].is_dir() and not any(found["gate_dir"].iterdir()):
        found["gate_dir"].rmdir()

    directory = records.decisions_dir(records.RELEASE, pass_id)
    keep = [
        row
        for row in records.read_decisions(records.RELEASE, pass_id)
        if row.get("verdict") != records.PASSED_OVER
    ]
    if directory.is_dir():
        for stale in sorted(directory.glob("*.jsonl")):
            stale.unlink()
    if keep:
        records.upsert_directory(directory, keep)
    log(
        f"[migrate] release store rewritten: {len(keep):,} winner(s) kept, "
        f"{len(found['passed_over']):,} passed-over row(s) dropped"
    )
    return {
        "pass": str(pass_id),
        "moved": len(moved),
        "dropped": len(found["passed_over"]),
        "kept": len(keep),
    }


__all__ = [
    "SCHEMA",
    "STORE_NAME",
    "UNIT",
    "LayoutRefused",
    "backup_path",
    "check",
    "durable",
    "manifest_dir",
    "manifest_path",
    "migrate",
    "old_layout",
    "read",
    "refuse_old_layout",
    "restore",
    "save",
    "store_path",
    "store_root",
    "stored_passes",
    "write",
]
