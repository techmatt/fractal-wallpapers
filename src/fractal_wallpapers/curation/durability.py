"""Keeping the files under `artifacts/` that the checkout cannot regenerate.

Some of what a run reads is not regenerable from the checkout at all. The supply
sidecar is the head's read of a **standing supply** that lives on the walk
ledgers, and the ledgers are under `artifacts/` too; the score amendment is
ninety thousand re-renders through a build that may have moved on; the hunt
frame index was cut from a scan nothing here builds any more. Everything else
under `artifacts/` comes back from something tracked — pictures from their own
records, views from their recipes, the render cache from the label stores.

So those files get what a tracked file gets for free, and they get it
explicitly: a second copy on the other disk, a manifest in the history saying
how many rows and which bytes that copy is, a restore that counts before it
believes, and a refusal at the top of `curate run` when a live file has gone
missing or gone short.

## One mechanism, and it names no file

This module is the mechanism only. [`Durable`] is the whole of what [`save`],
[`check`] and [`restore`] need to know about a file — where it lives, where its
copy goes, which tracked manifest describes it, and the commands to name in a
refusal — and each of them takes one. It knows about no particular file, and
that is a recent and deliberate change.

It was written around the supply sidecar, which was the first of these and for a
while the only one. The sidecar's paths lived here, `save()` with no argument
meant the sidecar, and the list of files a run refuses to start without reached
**up** from here into [`curation.amend`] and [`curation.hunt`] — two modules that
import this one. A floor module holding a list of its own callers is an import
cycle written small enough to look like a style choice, and it held this module
and the gallery passes' gate store inside the largest one in the tree.

The list, the sidecar and the zero-argument defaults are all in
[`curation.durables`] now. Every other durable is described where its file lives:
[`amend.durable`], [`hunt.frames_durable`], `candidate_ledger.store.durable_rows`
and `durable_scores`, `flatness.durable`, `signatures.durable`,
`embeddings.store`, `palettes.color_mass.sweep_log`.

## Why these are archived under a manifest rather than tracked

Size and churn, and either one alone would settle it.

* **Size.** Tens of megabytes against a 1 MiB per-file history guard
  (`tests/test_history_purity.py`) and a 20 MB commit rule. Tracking one would
  need the large-text allowlist, which holds one entry and is a decision rather
  than a fix.
* **Churn.** [`intake.score`] rewrites the sidecar **whole**, sorted by key, on
  every invocation — that is what makes scoring one binding not a deletion of
  another binding's rows. Every harvest night therefore produces a fresh
  full-size blob with a few thousand rows changed in the middle of it, and git
  stores each one entire. A month of nights is a clone nobody wants.

What is tracked instead is the *manifest*: the row count, the byte count, the
sha256, and whatever columns the file adds through [`Durable.facts`]. That is
enough to know the file is whole, enough to know when it is not, and it is a
couple of kilobytes.

## The copy goes to the other tier, and it is a copy rather than a move

`storage archive` **moves** a subtree: a name lives in exactly one tier and the
collision guard exists to keep it that way. This is the opposite thing — two
copies on two disks on purpose — so a copy cannot live under
`artifacts/curation`, which is the name the tiers arbitrate. They get their own
top-level name ([`BACKUP_UNIT`]) and are addressed off the archive root directly
rather than through `under()`: a durable copy on the same disk as the original is
not a durable copy, and resolving through the tiers is exactly what would put it
there.

On a machine with no archive configured the copy is still written, hot, and
[`save`] says out loud that what it bought is ordering rather than durability.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from fractal_wallpapers.paths import archive_root, rehome, repo_root, tracked_name

#: The schema the manifest and the provenance record carry.
SCHEMA = 1

#: The top-level name of the regenerable tree the durable copy lives under. Its
#: own name and not `curation`, because `curation` is a name the two tiers
#: arbitrate between and this is the one file meant to be on both disks at once.
BACKUP_UNIT = "curation_backup"

#: How many bytes are read at a time when hashing. The file is tens of megabytes,
#: and reading it whole to hash it is the one avoidable spike here.
CHUNK = 1 << 20


class DurableLost(RuntimeError):
    """A durable file is missing, or is shorter than its manifest recorded."""


@dataclass(frozen=True)
class Durable:
    """One file kept on two disks under a tracked manifest, and what to say about it.

    The whole of what [`save`], [`check`] and [`restore`] need to know. The three
    command strings are here rather than formatted at the raise site because a
    refusal that cannot tell the reader which command to run is a refusal they
    have to come back and ask about, and the commands differ per file.

    `facts` is how a file adds its own columns to its manifest — the sidecar's
    per-ledger split, the embedding store's fixed choices. It is handed the live
    path and returns a dict merged into the record; a file with nothing to add
    leaves it alone.
    """

    name: str
    live: Path
    copy: Path
    manifest: Path
    why_not_tracked: str
    save_command: str
    restore_command: str
    rebuild_command: str
    facts: Callable[[Path], dict] = field(default=lambda _: {})


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


# --------------------------------------------------------------------------- #
# The manifest.
# --------------------------------------------------------------------------- #
def read_manifest(durable: Durable) -> dict | None:
    """The manifest, or `None` where nothing has recorded this file yet."""
    path = durable.manifest
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != SCHEMA:
        raise DurableLost(f"{path}: schema {record.get('schema')!r}, expected {SCHEMA}")
    return record


def write_manifest(record: dict, durable: Durable) -> Path:
    """Write the manifest as tracked text. LF, because this file is in the history."""
    path = durable.manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def save(durable: Durable, when: str | None = None, log=print) -> dict:
    """Copy the file to the durable tier, and record what was copied.

    The copy and the manifest are written by one command because they are one
    claim. A manifest naming a count no copy has is worse than no manifest at
    all, because the restore path would believe it.
    """
    live = durable.live
    if not live.is_file():
        raise DurableLost(
            f"{live} is not there, so there is nothing to make durable. Run "
            f"`{durable.rebuild_command}` to build it, or "
            f"`{durable.restore_command}` if a copy already exists."
        )
    reading = measure(live)
    log(f"live   {tracked_name(live)}: {reading['rows']:,} rows, {reading['bytes']:,} bytes")

    copy = durable.copy
    copy.parent.mkdir(parents=True, exist_ok=True)
    writing = copy.with_suffix(copy.suffix + ".writing")
    shutil.copyfile(live, writing)
    writing.replace(copy)
    written = measure(copy)
    if written != reading:
        copy.unlink(missing_ok=True)
        raise DurableLost(
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
        **durable.facts(live),
        "recorded": str(date.today()) if when is None else str(when),
        "why_not_tracked": durable.why_not_tracked,
    }
    path = write_manifest(record, durable)
    log(f"wrote  {tracked_name(path)}")
    return record


def check(durable: Durable, log=print) -> dict:
    """Read the live file against its manifest, and name the disagreement.

    Five verdicts, and they are not two. `ok` is byte-identical. `grown` is the
    ordinary state between a harvest and the next [`save`] — more rows than the
    manifest recorded, which is what a scored harvest looks like. `changed` is
    the same count over different bytes. `short` and `missing` are the two this
    whole module exists for.
    """
    record = read_manifest(durable)
    live = durable.live
    out: dict = {
        "manifest": tracked_name(durable.manifest),
        "path": tracked_name(live),
        "recorded": None if record is None else record.get("rows"),
    }
    if record is None:
        out["verdict"] = "unrecorded"
        log(f"no manifest: nothing has recorded {durable.name} yet")
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
    copy = rehome(record["copy"]) or durable.copy
    out["copy"] = tracked_name(copy)
    out["copy_present"] = copy.is_file()
    log(f"{'copy':>10}  {out['copy']}: {'present' if out['copy_present'] else 'ABSENT'}")
    return out


def restore(durable: Durable, force: bool = False, log=print) -> dict:
    """Bring the durable copy back, counted against the manifest before it is believed.

    Two refusals, and they are the same rule from opposite sides: nothing is
    written until the copy has been proved to be what the manifest says, and
    nothing overwrites a live file that is **ahead** of the manifest, because
    that file is a scored harvest nobody has recorded yet.
    """
    record = read_manifest(durable)
    if record is None:
        raise DurableLost(
            f"{tracked_name(durable.manifest)} is not there, so there is no count to restore "
            f"against. A copy nothing can verify is not a restore path."
        )
    copy = rehome(record["copy"]) or durable.copy
    if not copy.is_file():
        raise DurableLost(
            f"the manifest names a copy at {record['copy']} and it resolves to {copy}, where "
            f"there is no file. If that is an external disk, plug it in."
        )
    reading = measure(copy)
    if reading["rows"] != int(record["rows"]) or reading["sha256"] != record["sha256"]:
        raise DurableLost(
            f"the copy at {copy} reads {reading['rows']:,} rows / sha "
            f"{reading['sha256'][:12]} against the manifest's {record['rows']:,} rows / "
            f"{str(record['sha256'])[:12]}. Nothing was written."
        )
    log(f"copy verified: {reading['rows']:,} rows, sha {reading['sha256'][:12]}")

    live = durable.live
    if live.is_file():
        here = count_rows(live)
        if here > int(record["rows"]) and not force:
            raise DurableLost(
                f"{tracked_name(live)} holds {here:,} rows and the manifest records "
                f"{record['rows']:,}. The live file is AHEAD of the copy — it is a harvest "
                f"nobody has run `{durable.save_command}` over — and restoring would "
                f"delete those rows. Save it first, or pass --force if it is known to be wrong."
            )
    live.parent.mkdir(parents=True, exist_ok=True)
    writing = live.with_suffix(live.suffix + ".writing")
    shutil.copyfile(copy, writing)
    writing.replace(live)
    back = measure(live)
    if back != reading:
        raise DurableLost(f"the restored file reads {back} against the copy's {reading}.")
    log(f"restored {tracked_name(live)}: {back['rows']:,} rows")
    return {"restored": tracked_name(live), "from": tracked_name(copy), **back}


# --------------------------------------------------------------------------- #
# The guard a run makes before it does anything else, one file at a time.
# --------------------------------------------------------------------------- #
def guard_one(durable: Durable, tag: str, log=print) -> dict:
    """Refuse over one durable that is gone, or has lost rows since it was recorded.

    Cheap on purpose — an existence test and a newline count, no hash and no
    parse — because it runs at the top of every `curate run` and these files are
    tens of megabytes each.

    Silent where there is no manifest. A checkout that has never recorded this
    file has nothing to be short *of*, and a guard that refused there would
    refuse every fresh clone's first run.
    """
    record = read_manifest(durable)
    if record is None:
        return {"verdict": "unrecorded"}
    live = durable.live
    recorded = int(record["rows"])
    if not live.is_file():
        raise DurableLost(
            f"{durable.name} is missing: {tracked_name(live)} is not there, and the "
            f"manifest records {recorded:,} rows at {str(record['sha256'])[:12]}. "
            f"{durable.why_not_tracked} Run `{durable.restore_command}` to bring back the "
            f"durable copy, or `{durable.rebuild_command}` to make it again from whatever "
            f"is still here."
        )
    rows = count_rows(live)
    if rows < recorded:
        raise DurableLost(
            f"{durable.name} has lost rows: {tracked_name(live)} holds {rows:,} and the "
            f"manifest records {recorded:,}. A run started here would decide over "
            f"{recorded - rows:,} rows fewer than the ones on record, and would say nothing "
            f"about it. Run `{durable.restore_command}`, or `{durable.save_command}` if the "
            f"shorter file is the truth."
        )
    log(f"[{tag}] {rows:,} rows, at or above the {recorded:,} on record")
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
    "Durable",
    "DurableLost",
    "check",
    "count_rows",
    "guard_one",
    "measure",
    "pool_ledgers",
    "provenance_path",
    "read_manifest",
    "restore",
    "save",
    "write_manifest",
]
