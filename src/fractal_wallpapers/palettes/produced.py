"""Which colours a map actually makes. The table read off the pictures.

[`carriers`] beside this one asks what a map *can* carry, and answers it by
recolouring three pinned reference fields. This asks the other question — what
has this map, in the hands of the passes that have run, actually produced — and
answers it off the candidate ledger, which is every picture this project has
rendered and kept. A map whose gradient is full of teal but whose every mined
picture came out amber is a teal map by the first reading and an amber one by
this one, and the two are not the same fact.

## What a row says

One row per map in the library. `pictures` is how many ledger rows were drawn in
it; each hue column is how many of those the dominance rule calls **dominant** in
that family. A picture may be dominant in more than one family and may be
dominant in none, so the hue columns do not sum to `pictures` in either
direction.

**Counts and not shares**, because the count is what was measured and the share
is `count / pictures`, which a reader can take exactly rather than at whatever
precision a rounded column happened to keep.

**The reading is [`palettes.dominance`]'s and is not taken again here.** Every
ledger row carries the verdict the rule already made — `colour.families`, written
when the picture was rendered — so this is a tally of stored answers and decodes
nothing. That is deliberate: a threshold that moved since a row was written must
not quietly re-decide what that picture was, which is the same reason
[`curation.candidate_ledger.rows.colour_block`] stores the names rather than the
shares.

## A map with no output gets a row, not an absence

`blue_orange` and `atlas_grey` are in the library and out of the candidate pool —
the first is the tile floor's reservation and the labeler's vivid render, the
second is the atlas plate's ramp — so neither has ever been drawn at a candidate.
They get a row of zeros, the way [`carriers`] writes an `uncarried` row rather
than leaving a map absent: a reader can then tell *made nothing of that colour*
from *not in this library at all*, which an absent row cannot say.

## Tracked, small, and regenerable

`data/palettes/palette_family_shares.csv`, in the shape
`palettes_for_random_choice.csv` set: a CSV beside the maps it is about, with
this module's docstring and `data/palettes/README.md` carrying the method that a
CSV has nowhere to put. About fifty kilobytes over the library, well under
`test_history_purity`'s 1 MiB. The ledger it is read from is a regenerable
artifact and is not tracked; `fractal-wallpapers palettes produced` rebuilds the
table in about a minute.
"""

from __future__ import annotations

import csv
import io
import time
from pathlib import Path

from fractal_wallpapers.palettes import codebook, dominance

#: What the file is called, beside the maps it is about. CSV and not `.json`,
#: for the reason [`carriers`] gives: every reader of the colormap library globs
#: `data/palettes/*.json` and takes the stem as a map name.
RECORD_NAME = "palette_family_shares.csv"

#: The name column, spelled the way `palettes_for_random_choice.csv` spells it so
#: that a reader of one file can read the other without learning a second word.
NAME_COLUMN = "palette name"

#: How many ledger pictures were drawn in the map.
COUNT_COLUMN = "pictures"

#: The twelve hue families, in the codebook's wheel order, which is the order the
#: columns are written in and the order anything that lists them uses.
HUES: tuple[str, ...] = tuple(name for name, _ in codebook.HUES)


class ProducedError(RuntimeError):
    """The table cannot be built from what is on this machine."""


def record_path(directory: Path | None = None) -> Path:
    """`<dir>/palette_family_shares.csv`, beside the maps it is about."""
    from fractal_wallpapers.paths import colormap_dir

    return (Path(directory) if directory is not None else colormap_dir()) / RECORD_NAME


def library_names(directory: Path | None = None) -> list[str]:
    """Every map in the library, by name, sorted the way the directory lists them."""
    from fractal_wallpapers.paths import colormap_dir

    where = Path(directory) if directory is not None else colormap_dir()
    return sorted(path.stem for path in where.glob("*.json"))


def columns() -> list[str]:
    """The header row: the name, the picture count, then the twelve families."""
    return [NAME_COLUMN, COUNT_COLUMN, *HUES]


def tally(log=None) -> tuple[dict[str, dict[str, int]], int]:
    """`({map: {family: pictures dominant in it, "": pictures}}, rows read)`.

    One streamed pass over the ledger. It is three quarters of a gigabyte and a
    solve may be appending to it while this runs, so the rows go by one at a
    time and the pool is never loaded — [`candidate_ledger.store.stream`]'s own
    discipline, for its reason.
    """
    from fractal_wallpapers.curation.candidate_ledger import store

    counts: dict[str, dict[str, int]] = {}
    read = 0
    for row in store.stream():
        read += 1
        name = (row.get("recipe") or {}).get("colormap")
        if not name:
            continue
        held = counts.setdefault(str(name), {"": 0})
        held[""] += 1
        for family in (row.get("colour") or {}).get("families") or []:
            held[str(family)] = held.get(str(family), 0) + 1
        if log is not None and read % 100_000 == 0:
            log(f"[produced] {read:,} ledger row(s)")
    if read == 0:
        raise ProducedError(
            "the candidate ledger is empty or absent on this machine, so no map has any "
            "output to read"
        )
    return counts, read


def rows_for(counts: dict[str, dict[str, int]], names: list[str]) -> list[dict]:
    """One row per map in the library, in the library's own order."""
    out = []
    for name in names:
        held = counts.get(name) or {}
        row = {NAME_COLUMN: name, COUNT_COLUMN: int(held.get("", 0))}
        for hue in HUES:
            row[hue] = int(held.get(hue, 0))
        out.append(row)
    return out


def text_of(rows: list[dict]) -> str:
    """The record as it goes on disk: a header, then one line per map."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write(rows: list[dict], directory: Path | None = None) -> Path:
    """Write the record where a reader of the library will find it."""
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


def read(directory: Path | None = None) -> list[dict]:
    """Every row of the tracked record, counts as integers.

    Refuses a file whose header is not this module's: a table with a column
    missing would otherwise read back as a library where that family was never
    produced, which is a sentence about the pictures and not about the file.
    """
    path = record_path(directory)
    if not path.is_file():
        raise ProducedError(f"no table at {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or ()) != columns():
            raise ProducedError(
                f"{path} has columns {reader.fieldnames!r}, not {columns()!r}, so it is not "
                "this table"
            )
        return [
            {NAME_COLUMN: row[NAME_COLUMN]}
            | {column: int(row[column]) for column in (COUNT_COLUMN, *HUES)}
            for row in reader
        ]


def run(directory: Path | None = None, log=print) -> dict:
    """Rebuild the table, and report what it was read from."""
    started = time.monotonic()
    names = library_names(directory)
    if not names:
        raise ProducedError("the colormap library is empty, so there is nothing to read")
    counts, read = tally(log=log)
    unknown = sorted(set(counts) - set(names))
    if unknown:
        raise ProducedError(
            f"{len(unknown)} map(s) the ledger names are not in this library: {unknown[:3]} — "
            "a table keyed to names the library does not hold would address nothing"
        )
    rows = rows_for(counts, names)
    path = write(rows, directory)
    seconds = time.monotonic() - started
    return {
        "record": str(path),
        "maps": len(rows),
        "with_output": sum(1 for row in rows if row[COUNT_COLUMN] > 0),
        "pictures": sum(row[COUNT_COLUMN] for row in rows),
        "ledger_rows": read,
        "dominance": dominance.RULE,
        "seconds": round(seconds, 1),
    }
