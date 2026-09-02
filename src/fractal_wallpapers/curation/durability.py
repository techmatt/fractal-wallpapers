"""Keeping the files under `artifacts/` that the checkout cannot regenerate.

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

## One implementation, several files, and there will be more

The sidecar was the first of these and for a while it was the only one, so this
module was written around it. It is not the only one now:
`curation.embeddings` keeps the neutral-render vectors the same way, the score
amendment and the hunt frame index the same way again, for the same reason — a
JSONL under `artifacts/` that costs a GPU leg to make again, or that cannot be
made again at all. So
the three verbs take a [`Durable`], which is the whole of what save, check and
restore need to know about a file: where it lives, where its copy goes, which
tracked manifest describes it, and the commands to name in a refusal. The
sidecar is [`sidecar`], one such value, and the zero-argument calls still mean
it.

[`guard`] is the one thing here that names its own list rather than taking a
[`Durable`] from the caller: a run refuses over the files in [`guarded`], which
are the supply, the score amendment and the hunt frame index, and over nothing
else. A file earns a place on that list by being unrecoverable *and* by being an
input the run reads without asking — a shorter one would send the leg out over a
supply nobody said had shrunk, or over framings nobody said had gone.

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
from collections.abc import Callable
from dataclasses import dataclass, field
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

#: What each of [`guarded`]'s files is called in a refusal and in the line the
#: guard prints. Short, because they are read at the top of every run's log.
GUARD_TAGS = ("sidecar", "amendment", "frames")


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


def sidecar() -> Durable:
    """The supply sidecar as a [`Durable`]. What a zero-argument call here means."""
    return Durable(
        name="the supply sidecar",
        live=sidecar_path(),
        copy=backup_path(),
        manifest=manifest_path(),
        why_not_tracked=(
            "tens of megabytes against a 1 MiB per-file history guard, and rewritten whole "
            "on every `curate score` because the sidecar upserts per ledger — so tracking it "
            "would add a fresh full-size blob to the history every harvest night. The "
            "manifest is what the history keeps; the bytes live on both tiers."
        ),
        save_command="fractal-wallpapers curate sidecar save",
        restore_command="fractal-wallpapers curate sidecar restore",
        rebuild_command="fractal-wallpapers curate score",
        facts=lambda path: {**_head_of(path), "rows_by_ledger": _by_ledger(path)},
    )


# --------------------------------------------------------------------------- #
# The manifest.
# --------------------------------------------------------------------------- #
def read_manifest(durable: Durable | None = None) -> dict | None:
    """The manifest, or `None` where nothing has recorded this file yet."""
    path = (sidecar() if durable is None else durable).manifest
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != SCHEMA:
        raise DurableLost(f"{path}: schema {record.get('schema')!r}, expected {SCHEMA}")
    return record


def write_manifest(record: dict, durable: Durable | None = None) -> Path:
    """Write the manifest as tracked text. LF, because this file is in the history."""
    path = (sidecar() if durable is None else durable).manifest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def save(durable: Durable | None = None, when: str | None = None, log=print) -> dict:
    """Copy the file to the durable tier, and record what was copied.

    The copy and the manifest are written by one command because they are one
    claim. A manifest naming a count no copy has is worse than no manifest at
    all, because the restore path would believe it.
    """
    durable = sidecar() if durable is None else durable
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


def check(durable: Durable | None = None, log=print) -> dict:
    """Read the live file against its manifest, and name the disagreement.

    Five verdicts, and they are not two. `ok` is byte-identical. `grown` is the
    ordinary state between a harvest and the next [`save`] — more rows than the
    manifest recorded, which is what a scored harvest looks like. `changed` is
    the same count over different bytes. `short` and `missing` are the two this
    whole module exists for.
    """
    durable = sidecar() if durable is None else durable
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


def restore(durable: Durable | None = None, force: bool = False, log=print) -> dict:
    """Bring the durable copy back, counted against the manifest before it is believed.

    Two refusals, and they are the same rule from opposite sides: nothing is
    written until the copy has been proved to be what the manifest says, and
    nothing overwrites a live file that is **ahead** of the manifest, because
    that file is a scored harvest nobody has recorded yet.
    """
    durable = sidecar() if durable is None else durable
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
# The guard a run makes before it does anything else.
# --------------------------------------------------------------------------- #
def guarded() -> tuple[Durable, ...]:
    """The files a `curate run` refuses to start without. **Three**, and the list is here.

    All three are inputs a run reads without being asked to, and none of them can
    be recovered from afterwards:

    * the **supply sidecar**, which is the standing supply the leg is offered;
    * the **score amendment**, which every reader of a seating score overlays on
      that sidecar — so a run started without it is not offered a smaller supply,
      it is offered the same supply at scores nobody has corrected. That is the
      worse of the two failures, because the count would look right;
    * the **hunt frame index**, which every mining leg draws its framings through.
      Its failure is the same shape and it is the least recoverable of the three:
      a location the index has no row for draws at the frame it already carries,
      by design, so a leg that lost the index renders a whole night successfully
      at unrefined framings and reports nothing unusual.

    A file is not on this list merely for being expensive. The embedding store
    and the two ledger sidecars are all expensive and all absent here: a run that
    starts without them fails loudly at the step that needs them, which is a
    different thing from a run that starts and quietly decides on stale numbers.
    """
    from fractal_wallpapers.curation import amend, hunt

    return (sidecar(), amend.durable(), hunt.frames_durable())


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


def guard(log=print) -> dict:
    """Refuse a run whose guarded files are gone, or have lost rows since recording.

    One verdict per file in [`guarded`], keyed by a short tag. It answers the
    questions that cannot be recovered from afterwards: is the standing supply
    still there, and are the corrections to it still there.
    """
    return {
        tag: guard_one(durable, tag, log=log)
        for tag, durable in zip(GUARD_TAGS, guarded(), strict=True)
    }


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
    "GUARD_TAGS",
    "SCHEMA",
    "SIDECAR_NAME",
    "Durable",
    "DurableLost",
    "backup_path",
    "check",
    "count_rows",
    "guard",
    "guard_one",
    "guarded",
    "manifest_path",
    "measure",
    "pool_ledgers",
    "provenance_path",
    "read_manifest",
    "restore",
    "save",
    "sidecar",
    "sidecar_path",
    "write_manifest",
]
