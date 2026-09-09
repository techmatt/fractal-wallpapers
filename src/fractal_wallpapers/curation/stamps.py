"""The **whole** autolevel stamp behind one candidate, wherever it was written down.

A recipe key names a picture, and [`curation.recipes.stamp_of`] keeps only what
decides that picture's pixels — the operator, the switch, the band's sha256. The
curve the operator derived is not in it, deliberately: it is a function of the
render rather than an input to it, and keying on it would re-key the store every
time a measurement moved.

So the curve lives on the **run record** instead, and this is the reader that
finds it again. It exists because levelling became a decide-once operation: a
release, a gallery seat and a kit all inherit the decision taken at candidate
geometry ([`coloring.autolevel.maybe_level`]'s `borrowed`), and inheriting it
means finding the row that took it.

## What has a curve to lend, and what does not

Three stores write one sequence row per candidate carrying the whole stamp, and
they write it in the same shape — `key`, and `autolevel` beside it:
`depth/<run>/sequence.jsonl`, `mine/<run>/sequence.jsonl` and
`remode/<run>/sequence.jsonl`. A gallery run's
own candidate rows carry it too, but nothing here reads those: a run releasing
its own seats already holds them in memory, and [`curation.run`] passes the stamp
straight across rather than going out to disk for what it just made.

**A mine leg recorded no stamp at all until 2026-09-08.** [`curation.mine.make`]
returned the whole stamp, the leg counted `autolevel_acted` off it and dropped
the rest, and only the reduced stamp survived on the ledger row — so a
mine-sourced candidate that acted was `acted_unrecoverable` **the day it was
made**, not as a backlog but as the shape of the leg. `mine` writes the same file
in the same shape now and is in [`SEQUENCE_STORES`]. What that does **not** do is
reach backwards: every mine and depth-through-mine row already in the pool still
has no curve on any record, which is why [`curation.backfill`] exists and why it
is a sweep over seats rather than a one-off migration.

## A batch, never a row at a time

The read is grouped by run and each run's sequence is streamed **once**, keeping
only the keys asked for — `candidate_ledger.by_key`'s discipline, for
`candidate_ledger.by_key`'s reason. The sequences run to 99.5 MiB on the largest
leg and 946 MiB over the 110 of them, and a per-row lookup would read one of
those files per seat.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.paths import under

#: The stores that write a whole stamp per candidate, and the file it is in.
#: Declared rather than discovered: a store added here is a decision about where
#: a curve may be inherited from, and a leg that writes no sequence row lends
#: nothing however many pictures it made.
#:
#: `mine` joined on 2026-09-08 and every mine leg before that date lends nothing:
#: the file is written from now on, and the rows already in the store are
#: [`curation.backfill`]'s to re-derive. A sweep does not have to know which of
#: the three wrote a run's file — [`sequence_paths`] tries all of them and a
#: missing one is not an error, because a run name belongs to exactly one store.
SEQUENCE_STORES: tuple[str, ...] = ("depth", "mine", "remode")

#: What one sequence row calls the two members read here.
KEY_FIELD, STAMP_FIELD = "key", "autolevel"


class StampError(RuntimeError):
    """A stamp cannot be read, or cannot be lent to the render that asked for it."""


def sequence_paths(run: str) -> list[Path]:
    """Every sequence file a run of this name could have written, in store order."""
    return [under("curation", store, str(run), "sequence.jsonl") for store in SEQUENCE_STORES]


def _from_run(run: str, wanted: set[str]) -> dict:
    """`{key: whole stamp}` for the wanted keys of one run. One pass, nothing held.

    Streamed line by line rather than read whole: the biggest of these is 99.5 MiB
    and the caller wants a few hundred of its rows.
    """
    out: dict = {}
    for path in sequence_paths(run):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                key = row.get(KEY_FIELD)
                if key in wanted and row.get(STAMP_FIELD):
                    # Last row wins, which is a re-render of the same recipe
                    # inside one leg replacing the stamp of the render it
                    # replaced. There is one picture on disk and this is its row.
                    out[key] = row[STAMP_FIELD]
    return out


def for_rows(rows: dict, amendments: dict | None = None) -> dict:
    """`{recipe key: whole stamp}` for a batch of ledger rows.

    `rows` is `{key: ledger row}` as [`candidate_ledger.by_key`] answers. The
    amendment overlay is read **first and preferred**, because a backfilled stamp
    is a stamp for a row whose leg wrote none and there is nothing under it to
    disagree with; where a run does hold the row, the amendment is a deliberate
    correction and still wins. See [`curation.backfill.read`].
    """
    amendments = {} if amendments is None else amendments
    # **The overlay is read through `rows` and never iterated on its own.** The
    # sidecar holds every seat ever backfilled and a caller asked about a batch;
    # answering for the rest is a dict of curves nobody requested, and it makes
    # "how many of these seats inherit one" unanswerable at the call site.
    found = {
        key: amendments[key]["autolevel"]
        for key in rows
        if (amendments.get(key) or {}).get("autolevel")
    }
    by_run: dict = {}
    for key, row in rows.items():
        if key in found:
            continue
        run = ((row or {}).get("provenance") or {}).get("run")
        if run:
            by_run.setdefault(str(run), set()).add(key)
    for run, wanted in by_run.items():
        found.update(_from_run(run, wanted))
    return found


def band_of(stamp: dict | None) -> str:
    """The sha256 of the band one stamp projected onto, or `""` where it says none."""
    return str(((stamp or {}).get("band") or {}).get("sha256") or "")


def borrowed_for(key: str, stamp: dict | None, row: dict | None = None, **source) -> dict | None:
    """One row's inherited levelling decision, or `None` where there is none.

    `None` rather than a refusal for the row nothing has a curve for: a seat whose
    leg recorded no stamp is `acted_unrecoverable`, that is a fact about the store
    and not an error, and the render it is about still has to be made — it simply
    decides for itself, exactly as it did before any of this existed.

    **The band is checked and a disagreement refuses.** A recipe key carries the
    band's sha256, so a stamp read for this key that names another band is a stamp
    for a different picture, and lending its curve would ship a wallpaper levelled
    onto a band its own key says it was not.
    """
    if not stamp or not stamp.get("curve"):
        return None
    if row is not None:
        wanted = str((((row.get("recipe") or {}).get("autolevel")) or {}).get("band_sha256") or "")
        if wanted and band_of(stamp) and wanted != band_of(stamp):
            raise StampError(
                f"{key}: the stamp found for this recipe projected onto band "
                f"{band_of(stamp)[:12]} and the recipe's own key carries "
                f"{wanted[:12]}. That is a curve from a different picture."
            )
    # What the source said about its own curve travels with it. Without this a
    # release that inherited a re-derivation would be indistinguishable from one
    # that inherited the curve its candidate actually shipped, and only the
    # second of those is a record.
    was = str(((stamp.get("provenance") or {}).get("curve")) or autolevel.DERIVED)
    return autolevel.borrowed_from(stamp, key=str(key), was=was, **source)


def for_release(rows: dict, amendments: dict | None = None, **source) -> dict:
    """`{key: borrowed}` for a release pass — the batch read, then packaged.

    THE door a release leg takes: one call before the pass, and every task built
    from its answer. A key missing from the result inherits nothing and renders as
    it always did.
    """
    stamps = for_rows(rows, amendments)
    out = {}
    for key, stamp in stamps.items():
        borrowed = borrowed_for(key, stamp, rows.get(key), **source)
        if borrowed is not None:
            out[key] = borrowed
    return out


__all__ = [
    "KEY_FIELD",
    "SEQUENCE_STORES",
    "STAMP_FIELD",
    "StampError",
    "band_of",
    "borrowed_for",
    "for_release",
    "for_rows",
    "sequence_paths",
]
