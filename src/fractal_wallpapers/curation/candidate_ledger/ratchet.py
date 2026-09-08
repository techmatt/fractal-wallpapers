"""The store only grows, and a loss that nothing accounts for is a defect.

A census of this store — how many rows it holds, and how many of them name their
picture by the recipe key against by a run index — used to be pinned as a
**floor**: the number somebody measured, asserted with `>=`, on the argument that
a store nothing deletes from can only climb past it. That argument was true while
nothing deleted, and [`sweep.prune`] deletes by design. A floor under a store
that loses rows on purpose fails on the first purposeful loss, and the only
repairs available are to repoint it at today's reading — which is to assert
nothing at all — or to leave it red.

So the invariant is a **ratchet** instead, and it is the same guard made honest:

    the count now, plus every deletion recorded since the mark, is at least the mark

Loss is allowed exactly when a transaction wrote down that it took it, and it is
caught the moment nothing did. The mark advances on growth and never on loss, so
what the guard remembers is the largest the store has ever been rather than the
largest it was on the day somebody last ran a census.

## Per counter, not per row

[`reading`] resolves each counter separately: a counter's mark is the last row
that advanced *it*, and its deletions are what was recorded after that row. A
single mark shared by all three, reset whole, would forgive accounted loss on a
counter that did not grow — which is this store's exact shape on 2026-09-07, with
`rows` climbing past its old mark while `run_index_named` fell 22 under the
displacement mine's merges. Reset together, those 22 accounted deletions would
have been dropped and the counter would have read short against a mark it never
reached again.

## One deletion site, so one recording site

Rows enter through [`door.merge`] and `store.write` is an upsert, which never
removes; the only writer that drops a row is `sweep._prune_file`, inside
[`sweep.prune`], and every leg that grows the store runs it. So there is one
place to record from and it is the transaction itself, rather than a caller who
has to remember. The orphan sweep and [`sweep.delete_pictures`] are deliberately
**not** recorded here: they unlink pictures and take no row, so no count this
module holds can move under them.

## Where the log lives, and why it is tracked

`data/curation/candidate_ledger/ratchet.jsonl` — in the history, beside the
manifests that describe the store's own untracked files. The store is tens of
megabytes and cannot be tracked; this is one row per merge and a clone that can
read it can read what this store has lost and when. It is also where a loss that
predates the ratchet gets entered *as a line somebody wrote*, which is the whole
difference between reconciling a gap and quietly re-baselining a constant.

**It does not follow `records.use`**, and that is deliberate rather than an
omission. A rehearsal redirects its *decision* records because a throwaway run's
verdicts must not accumulate beside a real release's — but a rehearsal that merges
rows prunes the **real** ledger, and a loss this store really took is a fact about
this store whoever caused it. A redirect here would hide exactly the deletions the
census then could not account for.

It resolves off `repo_root()` rather than off a tier, which makes it the same
hazard `tests/conftest.py`'s manifest guard exists for: a fixture that redirects
the store at the tier roots does not move this, and a prune under that fixture
would append a temporary store's counts to the history. [`log_path`] is patched
by the fixtures that prune, and the session guard holds the file still.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fractal_wallpapers.paths import repo_root

#: The schema every row of the log carries.
LOG_SCHEMA = 1


#: What the log is called, under `data/curation/candidate_ledger/`.
LOG_NAME = "ratchet.jsonl"


#: The two kinds of row. A `mark` says the store reached a size; a `deleted` says
#: a transaction took some of it away and how much.
MARK = "mark"
DELETED = "deleted"


#: The counters the ratchet holds, in the spelling `test_leveled_identity`'s
#: census uses. `rows` is every row there is; the other two split the rows that
#: name a picture by how that picture is named.
COUNTERS = ("rows", "recipe_key_named", "run_index_named")


#: The two naming shapes, and the counter each one lands in.
RECIPE_KEY = "recipe_key"
RUN_INDEX = "run_index"
COUNTER_OF = {RECIPE_KEY: "recipe_key_named", RUN_INDEX: "run_index_named"}


def log_path() -> Path:
    """The log, in the tracked tree. Redirected by name and not by a root."""
    return repo_root() / "data" / "curation" / "candidate_ledger" / LOG_NAME


# --------------------------------------------------------------------------- #
# The classification. One expression, and the census reads it too.
# --------------------------------------------------------------------------- #
def shape_of(stored, key) -> str:
    """Which of the two shapes names this picture: the recipe key, or an index.

    **The** spelling of the distinction, so that the census in
    `tests/test_leveled_identity.py` and the counts a prune records cannot come
    to disagree about what they are counting. A stem is either the row's own key
    or it is not; each shape is injective for its own reason, and the census is
    what asserts the classification stays total.

    The stem is taken off the **stored** name rather than off a re-homed path,
    which is the same answer for a cheaper question: [`paths.rehome`] re-roots a
    stored name and joins the parts below the artifacts component unchanged, so
    the last component — and therefore the stem — survives it exactly. Separators
    are normalised the way `rehome` normalises them, so a name a Windows run
    recorded with backslashes classifies the same on either platform.
    """
    stem = PurePosixPath(str(stored).replace("\\", "/")).stem
    return RECIPE_KEY if stem == str(key) else RUN_INDEX


def counts_of(pairs) -> dict:
    """The three counters over an iterable of `(key, stored picture)`.

    Every pair counts in `rows`; a pair naming no picture counts in neither shape,
    because there is no stem to classify. The census asserts that set is empty, so
    in a healthy store the two shapes sum to the rows — but this counts what is
    there rather than what should be.
    """
    found = dict.fromkeys(COUNTERS, 0)
    for key, picture in pairs:
        found["rows"] += 1
        if picture:
            found[COUNTER_OF[shape_of(picture, key)]] += 1
    return found


# --------------------------------------------------------------------------- #
# The log.
# --------------------------------------------------------------------------- #
def entries(path: Path | None = None) -> list[dict]:
    """Every row of the log, in the order it was appended. `[]` where none is."""
    where = log_path() if path is None else Path(path)
    if not where.is_file():
        return []
    rows = []
    with where.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append(record: dict, path: Path | None = None) -> Path:
    """Add one row. Tracked text, so `newline="\\n"` and nothing else."""
    where = log_path() if path is None else Path(path)
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return where


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def reading(path: Path | None = None) -> dict:
    """`{mark, deleted, marked_at}`, each resolved **per counter**.

    A counter's mark is the last row that advanced it; its deletions are the sum
    of every `deleted` row appended after that one. A counter no row has ever
    marked is absent from `mark`, which is a state the census refuses rather than
    passes over — an unmarked counter is a counter with no guard on it.
    """
    mark: dict = {}
    marked_at: dict = {}
    deleted = dict.fromkeys(COUNTERS, 0)
    for record in entries(path):
        counts = record.get("counts") or {}
        if record.get("event") == MARK:
            for name, value in counts.items():
                mark[name] = int(value)
                marked_at[name] = record.get("at")
                deleted[name] = 0
        elif record.get("event") == DELETED:
            for name, value in counts.items():
                deleted[name] = deleted.get(name, 0) + int(value)
    return {"mark": mark, "deleted": deleted, "marked_at": marked_at}


def advance(counts: dict, why: str, when: str | None = None, path: Path | None = None):
    """Mark the counters `counts` holds that are over their current mark.

    Only those, and this is the half that makes the reset safe: a mark row names
    the counters it advanced, [`reading`] zeroes a counter's deletions when it
    sees it named, and a counter that did not grow keeps the deletions that
    explain why it did not. Returns the row appended, or `None` where nothing
    grew — a store that shrank writes no mark.
    """
    standing = reading(path)["mark"]
    grown = {
        name: int(value)
        for name, value in counts.items()
        if name not in standing or int(value) > standing[name]
    }
    if not grown:
        return None
    record = {
        "schema": LOG_SCHEMA,
        "event": MARK,
        "at": _now() if when is None else str(when),
        "why": why,
        "counts": grown,
    }
    append(record, path)
    return record


def record_loss(
    counts: dict,
    why: str,
    when: str | None = None,
    note: str | None = None,
    path: Path | None = None,
):
    """Write down what a transaction took, so the ratchet can forgive it.

    Returns `None` where nothing was taken: a prune that dropped no row has
    nothing to account for, and a row of zeroes per merge would be the log's whole
    growth. `note` is for a loss that needs a sentence — a reconciliation of rows
    that went before anything recorded them has no transaction to point at.
    """
    taken = {name: int(value) for name, value in counts.items() if int(value)}
    if not taken:
        return None
    record = {
        "schema": LOG_SCHEMA,
        "event": DELETED,
        "at": _now() if when is None else str(when),
        "why": why,
        "counts": taken,
    }
    if note:
        record["note"] = note
    append(record, path)
    return record
