"""Keeping the supply sidecar, which is the one thing here nothing else holds.

[`curation.intake`] writes `artifacts/curation/supply_scores.jsonl`: one row per
location the location head has an opinion about, upserted per ledger, tens of
thousands of rows and tens of megabytes of them. Everything else under
`artifacts/` is regenerable from something tracked — pictures from their own
records, views from their recipes, the render cache from the label stores. This
file is not regenerable from the checkout: it is the head's read of a **standing
supply** that lives on the walk ledgers, and the ledgers are under `artifacts/`
too.

So it gets what a tracked file gets for free, and it gets it explicitly: a second
copy on the other disk, a manifest in the history saying how many rows and which
bytes that copy is, a restore that counts before it believes, and a refusal at
the top of `curate run` when the live file has gone missing or gone short.

## Why it is archived under a manifest rather than tracked

Size and churn, and either one alone would settle it.

* **Size.** Tens of megabytes against a 1 MiB per-file history guard
  (`tests/test_history_purity.py`) and a 20 MB commit rule. Tracking it would
  need the large-text allowlist, which holds one entry and is a decision rather
  than a fix.
* **Churn.** [`intake.score`] rewrites the file **whole**, sorted by key, on
  every invocation — that is what makes scoring one binding not a deletion of
  another binding's rows. Every harvest night therefore produces a fresh
  full-size blob with a few thousand rows changed in the middle of it, and git
  stores each one entire. A month of nights is a clone nobody wants.

What is tracked instead is the *manifest*: the row count, the byte count, the
sha256, which head read them, and per-ledger counts. That is enough to know the
file is whole, enough to know when it is not, and it is a couple of kilobytes.

## The copy goes to the other tier, and it is a copy rather than a move

`storage archive` **moves** a subtree: a name lives in exactly one tier and the
collision guard exists to keep it that way. This is the opposite thing — two
copies on two disks on purpose — so the copy cannot live under
`artifacts/curation`, which is the name the tiers arbitrate. It gets its own
top-level name ([`BACKUP_UNIT`]) and it is addressed off the archive root
directly rather than through `under()`: a durable copy on the same disk as the
original is not a durable copy, and resolving through the tiers is exactly what
would put it there.

On a machine with no archive configured the copy is still written, hot, and
[`save`] says out loud that what it bought is ordering rather than durability.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

from fractal_wallpapers.paths import archive_root, hot_root, rehome, repo_root, tracked_name

#: The schema the manifest and the provenance record carry.
SCHEMA = 1

#: The top-level name of the regenerable tree the durable copy lives under. Its
#: own name and not `curation`, because `curation` is a name the two tiers
#: arbitrate between and this is the one file meant to be on both disks at once.
BACKUP_UNIT = "curation_backup"

#: What the sidecar is called, wherever it is.
SIDECAR_NAME = "supply_scores.jsonl"

#: How many bytes are read at a time when hashing. The file is tens of megabytes,
#: and reading it whole to hash it is the one avoidable spike here.
CHUNK = 1 << 20


class SidecarLost(RuntimeError):
    """The supply sidecar is missing, or is shorter than the manifest recorded."""


def manifest_path() -> Path:
    """The tracked manifest: what the sidecar was, last time anybody recorded it."""
    return repo_root() / "data" / "curation" / "supply_scores.manifest.json"


def sidecar_path() -> Path:
    """The live sidecar, wherever curation's subtree currently is."""
    from fractal_wallpapers.curation import intake

    return intake.scores_path()


def backup_path() -> Path:
    """The durable copy: on the archive tier where there is one, hot where there is not.

    Named off a root rather than through `under()`, because `under()` resolves to
    whichever tier the subtree is already on — which, for a copy that has never
    been written, is the hot one, beside the original it is supposed to survive.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / BACKUP_UNIT / SIDECAR_NAME


# --------------------------------------------------------------------------- #
# Measuring, which is the whole of what the manifest says.
# --------------------------------------------------------------------------- #
def measure(path: Path) -> dict:
    """`{rows, bytes, sha256}` for one file, in a single pass over its bytes.

    Rows are counted as newlines rather than by parsing, deliberately: the guard
    at the top of a run asks a size question, and it must not cost a JSON parse
    of every row to answer it. The sidecar's writer ends every row with a
    newline, so the two counts agree.
    """
    path = Path(path)
    digest = hashlib.sha256()
    rows = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
            rows += chunk.count(b"\n")
    return {"rows": rows, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def count_rows(path: Path) -> int:
    """Just the row count, for the guard. No hash and no parse."""
    rows = 0
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            rows += chunk.count(b"\n")
    return rows


def _by_ledger(path: Path) -> dict:
    """How many of the sidecar's rows each ledger last scored. One parse, in [`save`]."""
    tally: Counter = Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tally[str(json.loads(line).get("ledger"))] += 1
    return dict(sorted(tally.items()))


def _head_of(path: Path) -> dict:
    """The head every row names, or the disagreement where they do not all name one."""
    stamps: Counter = Counter()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                stamps[str(json.loads(line).get("head_sha256"))] += 1
    if len(stamps) == 1:
        return {"head": "location", "head_sha256": next(iter(stamps))}
    return {"head": "location", "head_sha256": None, "head_sha256_counts": dict(stamps)}


# --------------------------------------------------------------------------- #
# The manifest.
# --------------------------------------------------------------------------- #
def read_manifest() -> dict | None:
    """The manifest, or `None` where nothing has recorded the sidecar yet."""
    path = manifest_path()
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != SCHEMA:
        raise SidecarLost(f"{path}: schema {record.get('schema')!r}, expected {SCHEMA}")
    return record


def write_manifest(record: dict) -> Path:
    """Write the manifest as tracked text. LF, because this file is in the history."""
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def save(when: str | None = None, log=print) -> dict:
    """Copy the sidecar to the durable tier, and record what was copied.

    The copy and the manifest are written by one command because they are one
    claim. A manifest naming a count no copy has is worse than no manifest at
    all, because the restore path would believe it.
    """
    live = sidecar_path()
    if not live.is_file():
        raise SidecarLost(
            f"{live} is not there, so there is nothing to make durable. Run "
            f"`fractal-wallpapers curate score` to build it, or "
            f"`fractal-wallpapers curate sidecar restore` if a copy already exists."
        )
    reading = measure(live)
    log(f"live   {tracked_name(live)}: {reading['rows']:,} rows, {reading['bytes']:,} bytes")

    copy = backup_path()
    copy.parent.mkdir(parents=True, exist_ok=True)
    writing = copy.with_suffix(copy.suffix + ".writing")
    shutil.copyfile(live, writing)
    writing.replace(copy)
    written = measure(copy)
    if written != reading:
        copy.unlink(missing_ok=True)
        raise SidecarLost(
            f"the copy at {copy} came out {written} against the live file's {reading}. "
            f"It has been removed rather than left there to be restored from."
        )
    log(f"copy   {tracked_name(copy)}: verified identical")
    if archive_root() is None:
        log(
            "NOTE: no archive root is configured, so the copy is on the same disk as the "
            "original. That is an ordering guarantee and not a durability one."
        )

    record = {
        "schema": SCHEMA,
        "path": tracked_name(live),
        "copy": tracked_name(copy),
        **reading,
        **_head_of(live),
        "rows_by_ledger": _by_ledger(live),
        "recorded": str(date.today()) if when is None else str(when),
        "why_not_tracked": (
            "tens of megabytes against a 1 MiB per-file history guard, and rewritten whole "
            "on every `curate score` because the sidecar upserts per ledger — so tracking it "
            "would add a fresh full-size blob to the history every harvest night. The "
            "manifest is what the history keeps; the bytes live on both tiers."
        ),
    }
    path = write_manifest(record)
    log(f"wrote  {tracked_name(path)}")
    return record


def check(log=print) -> dict:
    """Read the live sidecar against the manifest, and name the disagreement.

    Five verdicts, and they are not two. `ok` is byte-identical. `grown` is the
    ordinary state between a harvest and the next [`save`] — more rows than the
    manifest recorded, which is what a scored harvest looks like. `changed` is
    the same count over different bytes. `short` and `missing` are the two this
    whole module exists for.
    """
    record = read_manifest()
    live = sidecar_path()
    out: dict = {
        "manifest": tracked_name(manifest_path()),
        "path": tracked_name(live),
        "recorded": None if record is None else record.get("rows"),
    }
    if record is None:
        out["verdict"] = "unrecorded"
        log("no manifest: nothing has recorded this sidecar yet")
        return out
    if not live.is_file():
        out.update({"verdict": "missing", "rows": 0})
        log(f"MISSING {tracked_name(live)} — the manifest records {record['rows']:,} rows")
        return out
    reading = measure(live)
    out.update(reading)
    if reading["sha256"] == record.get("sha256"):
        out["verdict"] = "ok"
    elif reading["rows"] < int(record["rows"]):
        out["verdict"] = "short"
    elif reading["rows"] > int(record["rows"]):
        out["verdict"] = "grown"
    else:
        out["verdict"] = "changed"
    log(
        f"{out['verdict'].upper():>10}  live {reading['rows']:,} rows / "
        f"{reading['bytes']:,} bytes, manifest {record['rows']:,} rows / "
        f"{record['bytes']:,} bytes"
    )
    copy = rehome(record["copy"]) or backup_path()
    out["copy"] = tracked_name(copy)
    out["copy_present"] = copy.is_file()
    log(f"{'copy':>10}  {out['copy']}: {'present' if out['copy_present'] else 'ABSENT'}")
    return out


def restore(force: bool = False, log=print) -> dict:
    """Bring the durable copy back, counted against the manifest before it is believed.

    Two refusals, and they are the same rule from opposite sides: nothing is
    written until the copy has been proved to be what the manifest says, and
    nothing overwrites a live file that is **ahead** of the manifest, because
    that file is a scored harvest nobody has recorded yet.
    """
    record = read_manifest()
    if record is None:
        raise SidecarLost(
            f"{tracked_name(manifest_path())} is not there, so there is no count to restore "
            f"against. A copy nothing can verify is not a restore path."
        )
    copy = rehome(record["copy"]) or backup_path()
    if not copy.is_file():
        raise SidecarLost(
            f"the manifest names a copy at {record['copy']} and it resolves to {copy}, where "
            f"there is no file. If that is an external disk, plug it in."
        )
    reading = measure(copy)
    if reading["rows"] != int(record["rows"]) or reading["sha256"] != record["sha256"]:
        raise SidecarLost(
            f"the copy at {copy} reads {reading['rows']:,} rows / sha "
            f"{reading['sha256'][:12]} against the manifest's {record['rows']:,} rows / "
            f"{str(record['sha256'])[:12]}. Nothing was written."
        )
    log(f"copy verified: {reading['rows']:,} rows, sha {reading['sha256'][:12]}")

    live = sidecar_path()
    if live.is_file():
        here = count_rows(live)
        if here > int(record["rows"]) and not force:
            raise SidecarLost(
                f"{tracked_name(live)} holds {here:,} rows and the manifest records "
                f"{record['rows']:,}. The live file is AHEAD of the copy — it is a harvest "
                f"nobody has run `curate sidecar save` over — and restoring would delete "
                f"those rows. Save it first, or pass --force if it is known to be wrong."
            )
    live.parent.mkdir(parents=True, exist_ok=True)
    writing = live.with_suffix(live.suffix + ".writing")
    shutil.copyfile(copy, writing)
    writing.replace(live)
    back = measure(live)
    if back != reading:
        raise SidecarLost(f"the restored file reads {back} against the copy's {reading}.")
    log(f"restored {tracked_name(live)}: {back['rows']:,} rows")
    return {"restored": tracked_name(live), "from": tracked_name(copy), **back}


# --------------------------------------------------------------------------- #
# The guard a run makes before it does anything else.
# --------------------------------------------------------------------------- #
def guard(log=print) -> dict:
    """Refuse a run whose supply sidecar is gone, or has lost rows since it was recorded.

    Cheap on purpose — an existence test and a newline count, no hash and no
    parse — because it runs at the top of every `curate run` and the file is tens
    of megabytes. It answers the one question that cannot be recovered from
    afterwards: is the standing supply still there.

    Silent where there is no manifest. A checkout that has never recorded the
    sidecar has nothing to be short *of*, and a guard that refused there would
    refuse every fresh clone's first run.
    """
    record = read_manifest()
    if record is None:
        return {"verdict": "unrecorded"}
    live = sidecar_path()
    recorded = int(record["rows"])
    if not live.is_file():
        raise SidecarLost(
            f"the supply sidecar is missing: {tracked_name(live)} is not there, and the "
            f"manifest records {recorded:,} rows of standing supply at "
            f"{str(record['sha256'])[:12]}. It is not regenerable from the checkout — the "
            f"ledgers it reads are under the regenerable tree too. Run "
            f"`fractal-wallpapers curate sidecar restore` to bring back the durable copy, or "
            f"`fractal-wallpapers curate score` to read the supply again from whatever "
            f"ledgers are still here."
        )
    rows = count_rows(live)
    if rows < recorded:
        raise SidecarLost(
            f"the supply sidecar has lost rows: {tracked_name(live)} holds {rows:,} and the "
            f"manifest records {recorded:,}. A run started here would be offered a supply "
            f"{recorded - rows:,} locations smaller than the one on record, and would say "
            f"nothing about it. Run `fractal-wallpapers curate sidecar restore`, or "
            f"`curate sidecar save` if the shorter file is the truth."
        )
    log(f"[sidecar] {rows:,} rows, at or above the {recorded:,} on record")
    return {"verdict": "ok", "rows": rows, "recorded": recorded}


# --------------------------------------------------------------------------- #
# Where the collection's rows came from, and whether those ledgers still read.
# --------------------------------------------------------------------------- #
def pool_ledgers() -> dict:
    """Which walk ledger each release record names, and where that ledger resolves now.

    Provenance and not a repair. A release row carries its whole join and
    re-renders from itself, so a row whose ledger is gone is still a wallpaper
    somebody can rebuild — what it cannot do is be **re-offered**, because
    `intake.ranked` starts from ledgers. This says how many rows are in that
    position, and it is a question that has to be asked through `rehome`: a
    ledger that has merely been archived is still readable, and looking for it
    on the hot tier alone would report it lost.
    """
    from fractal_wallpapers.curation import records

    rows = records.read_decisions(records.RELEASE)
    tally: dict[str, dict] = {}
    for row in rows:
        named = str((row.get("location") or {}).get("ledger"))
        cell = tally.setdefault(named, {"rows": 0, "runs": set()})
        cell["rows"] += 1
        cell["runs"].add(str(row.get("run")))
    ledgers = []
    for named in sorted(tally):
        cell = tally[named]
        where = rehome(named)
        present = bool(where and where.is_file())
        ledgers.append(
            {
                "ledger": named,
                "rows": cell["rows"],
                "runs": sorted(cell["runs"]),
                "resolves": present,
                "at": tracked_name(where) if where else None,
                "tier": _tier_of(named) if present else None,
            }
        )
    absent = [cell for cell in ledgers if not cell["resolves"]]
    return {
        "schema": SCHEMA,
        "note": (
            "which walk ledger each released row was drawn from, and whether that ledger "
            "still reads. A row whose ledger is gone still re-renders from its own join and "
            "still counts in every rate; what it cannot be is offered to another run. `tier` "
            "is a snapshot of where the file was on `read`, not a property of the ledger."
        ),
        "read": str(date.today()),
        "pool_rows": len(rows),
        "ledgers_named": len(ledgers),
        "ledgers_absent": len(absent),
        "rows_on_absent_ledgers": sum(cell["rows"] for cell in absent),
        "ledgers": ledgers,
    }


def _tier_of(named: str) -> str | None:
    """Which tier a stored artifacts name currently resolves on."""
    from fractal_wallpapers.paths import ARTIFACTS_NAME, Tiers

    parts = str(named).replace("\\", "/").split("/")
    if ARTIFACTS_NAME not in parts:
        return None
    unit = parts[parts.index(ARTIFACTS_NAME) + 1]
    return Tiers.current().tier_of(unit)


def provenance_path() -> Path:
    """The tracked record of what the collection's rows were drawn from."""
    return repo_root() / "data" / "curation" / "ledger_provenance.json"


__all__ = [
    "BACKUP_UNIT",
    "SCHEMA",
    "SIDECAR_NAME",
    "SidecarLost",
    "backup_path",
    "check",
    "count_rows",
    "guard",
    "manifest_path",
    "measure",
    "pool_ledgers",
    "provenance_path",
    "read_manifest",
    "restore",
    "save",
    "sidecar_path",
    "write_manifest",
]
