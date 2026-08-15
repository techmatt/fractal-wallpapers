"""The union of everything every walk has ever found.

A walk writes one ledger. The supply engine reads *all of them*, and this module
is the one reader — the machine leg of the standing deficit and the cross-run
saturation memory both come through here, so there is exactly one answer to
"what supply exists".

**Admitted means three things at once**, and they are checked in this order:

* *the gates passed* — a candidate any structural gate refused is a recorded
  refusal, not supply;
* *the score clears the keeper floor* — a candidate the scorer declined to score
  has no verdict to be kept on, so it is not admitted and is counted as such;
* *the location has not already been admitted* — the ledgers overlap, because a
  location found by one run can be found again by the next, and a union that
  counted it twice would let re-running a walk inflate a partition's stock.

**Deduplication is on location identity, never on a row id.** A ledger's node
ids are scoped to their run, so two runs mint the same id for different places.
Keying the union on identity is what makes it a statement about *places* rather
than about rows.

**The original files are only ever read.** Nothing here rewrites a ledger, mints
a prefixed copy of one, or re-keys a row. A union that edits its inputs cannot be
re-derived, and a copy under a scratch tree is a population that a cleanup
deletes.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.discovery import ledger as ledger_module
from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply import currency as money
from fractal_wallpapers.supply.location import key_of_row

#: The file every walk writes its record to.
LEDGER_NAME = "walk.jsonl"


def ledger_root() -> Path:
    """Where run directories accumulate."""
    return repo_root() / "artifacts"


def ledger_paths(root: Path | None = None, exclude: Path | None = None) -> list[Path]:
    """Every walk ledger under `root`, minus one — usually this run's own.

    `exclude` is resolved before comparison, because the caller's path came from a
    run directory and ours came from a directory walk: two spellings of one file
    is how a run ends up seeded with its own finds.
    """
    root = ledger_root() if root is None else Path(root)
    if not root.is_dir():
        return []
    own = Path(exclude).resolve() if exclude is not None else None
    return [
        path for path in sorted(root.rglob(LEDGER_NAME)) if own is None or path.resolve() != own
    ]


def rows(path: Path, kind: str | None = None):
    """Yield a ledger's rows, checking the schema on each.

    A tolerant reader on purpose in one respect only: a ledger is append-only and
    a run killed mid-write can leave a truncated final line, which is a real state
    and not a corrupt file. Everything else raises.
    """
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if not line.endswith("}"):
                    continue  # a killed run's half-written last line
                raise
            if row.get("schema") != ledger_module.SCHEMA:
                raise ValueError(
                    f"{path}:{number}: schema {row.get('schema')!r}, "
                    f"expected {ledger_module.SCHEMA}"
                )
            if kind is None or row.get("kind") == kind:
                yield row


def passes_gates(row: dict) -> bool:
    """Whether every structural gate let this candidate through."""
    return row.get("fate") == ledger_module.SURVIVED


def is_admitted(row: dict) -> bool:
    """THE admission predicate: the gates, then the keeper floor."""
    return passes_gates(row) and money.passes_good_floor(row.get("score"))


def admitted(path: Path, admit=None) -> list[dict]:
    """Every admitted candidate row of one ledger.

    `admit` replaces the whole predicate with a caller-supplied `row -> bool`. It
    exists so a second consumer can share this reader — and therefore the
    schema check, the namespacing and the deduplication — instead of growing a
    second walker that could disagree about what the population is.
    """
    predicate = is_admitted if admit is None else admit
    return [row for row in rows(path, kind="candidate") if predicate(row)]


def admitted_union(paths=None, admit=None) -> tuple[list[dict], dict]:
    """`(rows, diagnostics)` — the admitted union, in ledger order.

    Each returned row is the ledger's own row with `_ledger` added, naming the
    file it came from. The diagnostics carry what a census wants to print: the
    size, the per-ledger contribution, and how many rows an earlier ledger had
    already admitted the same location for.
    """
    paths = ledger_paths() if paths is None else [Path(p) for p in paths]
    root = repo_root()
    seen: dict = {}
    kept: list[dict] = []
    overlaps: list[str] = []
    per_ledger: dict = {}
    unkeyed = 0
    for path in paths:
        try:
            label = str(Path(path).resolve().relative_to(root).as_posix())
        except ValueError:
            label = str(path)
        taken = 0
        for row in admitted(path, admit):
            key = key_of_row(row)
            if key is None:
                # Counted, and kept: a row whose identity cannot be built is real
                # supply, and dropping it would understate a partition's stock.
                # What it cannot be is deduplicated, which is why it is reported.
                unkeyed += 1
            elif key in seen:
                overlaps.append(f"{seen[key]} vs {label}")
                continue
            else:
                seen[key] = label
            out = dict(row)
            out["_ledger"] = label
            kept.append(out)
            taken += 1
        per_ledger[label] = taken
    return kept, {
        "size": len(kept),
        "ledgers": len(paths),
        "per_ledger": per_ledger,
        "location_overlaps": len(overlaps),
        "overlap_sample": overlaps[:5],
        "unkeyed_rows": unkeyed,
    }


__all__ = [
    "LEDGER_NAME",
    "admitted",
    "admitted_union",
    "is_admitted",
    "ledger_paths",
    "ledger_root",
    "passes_gates",
    "rows",
]
