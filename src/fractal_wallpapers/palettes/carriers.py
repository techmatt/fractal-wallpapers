"""Which map can make a picture of which colour. The table a target draws from.

A colour target is a request for pictures the pass has not made yet, and the seat
cannot choose what the plan never rendered: over gallery3's 3,632 attempts, 35 of
the 43 maps that can carry `dark_vivid_green` were never picked once, because the
palette head sees them as often as anything else and declines them — offered
4,334 times, picked 23, 0.17x the base rate. Re-ranking inside those
neighbourhoods cannot make a green gallery. Something has to *ask* for a green
map before the render happens, and this is the table it asks.

## What a row says, and what it does not

Every map in the library, recoloured onto the three pinned reference fields
([`fractal_wallpapers.palettes.reference_fields`]) and read through
[`fractal_wallpapers.palettes.dominance`]. A map **carries** a cell on a field
when that field's picture is dominant in the cell. One row per (map, cell) the
map carries anywhere, with the cell's share on all three fields and their mean —
including the fields where it does not carry, because the mean is what the draw
weights by and a mean over only the wins would rank a map that carries once above
one that nearly carries three times.

**It is a prior and not a guarantee**, and the size of the gap is on record.
Green collapses on the `strange` field — 14 maps against 33 on `smooth` — which
is the field class that held 90 of gallery3's 150 seats; only 4 of 43 green
carriers and 3 of 41 rose carriers dominate on all three. And gallery3's one
green seat came from `PRGn`, which this table calls a carrier of nothing green at
all. The field and the mode carry a real share of the outcome, so a carrier
attempt's dominance is read on **its own render** and never off this table.

## Per map, never per group

The obvious economy — one row per palette group, since the group is what the pool
draws — is wrong, and measurably. Members of one group disagree on their dominant
cell in **120 of 195 (group, field) reads**, and 96 of those disagreements cross
a hue family: `twilight` and `twilight_shifted` are M1 0.0105 apart and correctly
one group, and read `light_muted_azure` and `dark_vivid_purple` on the same
field. M1 is order-free over a ramp's colour cloud; dominance is area-weighted
over a picture, so a phase shift moves the areas without moving the cloud. A
table keyed to whichever member a seed stood up would be right about a third of
the library and confidently wrong about the rest.

## Tracked, small, and regenerable

`data/palettes/carriers.jsonl`: one method row, then one row per (map, cell).
Around two and a half rows a map, which is a few hundred kilobytes — small
enough to keep in the history, where a reader of a pass record that names a
carrier can find out what the pass believed about it. The pictures behind it are
not: 2,703 recolours land under `artifacts/` and are remade by
`fractal-wallpapers palettes carriers` in about eighty seconds.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers.palettes import dominance, groups, reference_fields

#: The schema every row carries, from its first line.
SCHEMA = 1

#: What the file is called, beside the maps it is about. JSONL and not `.json`,
#: for the reason [`fractal_wallpapers.palettes.groups`] gives: every reader of
#: the colormap library globs `data/palettes/*.json` and takes the stem as a map
#: name, so a `.json` file in there would be read as a colormap.
RECORD_NAME = "carriers.jsonl"

#: The two kinds of row: one header, then one per (map, cell).
METHOD_ROW = "method"
CARRIER_ROW = "carrier"

#: Decimals a share is written to. Six, which is the codebook's own rounding and
#: two more than any decision reads.
PLACES = 6

#: Where the recolours live. Ignored, regenerable, and about 40 MB.
RECOLOUR_DIR = Path("artifacts") / "palettes" / "carriers"


class CarrierError(RuntimeError):
    """The carrier table cannot be built or cannot be read."""


def record_path(directory: Path | None = None) -> Path:
    """`<dir>/carriers.jsonl`, beside the maps it is about."""
    from fractal_wallpapers.paths import colormap_dir

    return (Path(directory) if directory is not None else colormap_dir()) / RECORD_NAME


def method(maps: int, rows: int, seconds: float) -> dict:
    """The header row: what was read, how, and by what command."""
    return {
        "schema": SCHEMA,
        "kind": METHOD_ROW,
        "maps": int(maps),
        "carriers": int(rows),
        "fields": list(reference_fields.CLASSES),
        "geometry": {
            "resolution": list(reference_fields.RESOLUTION),
            "supersample": reference_fields.SUPERSAMPLE,
        },
        "seconds": round(float(seconds), 1),
        "dominance": dominance.RULE,
        "method": (
            "every map in the library recoloured onto the three pinned reference fields and "
            "read through the dominance rule above. A map CARRIES a cell on a field when that "
            "field's picture is dominant in the cell; a row is written for every (map, cell) "
            "the map carries on at least one field, with the cell's share on all three fields "
            "and their mean. Keyed to the MAP and never to the palette group: members of one "
            "group disagree on their dominant cell in 120 of 195 (group, field) reads. "
            "Regenerated by `fractal-wallpapers palettes carriers`."
        ),
    }


def text_of(rows: list) -> str:
    """The record as it is written: one JSON object a line, LF, UTF-8."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write(rows: list, directory: Path | None = None) -> Path:
    """Write the record where a reader of the library will find it."""
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


def read(directory: Path | None = None) -> list:
    """Every row of the tracked record, header first."""
    path = record_path(directory)
    if not path.is_file():
        raise CarrierError(
            f"{path} is not there. `fractal-wallpapers palettes carriers` builds it, "
            "and it is tracked, so a clone has it already."
        )
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


#: The parsed table, held per file and invalidated by the file. Keyed on
#: `(path, mtime, size)`: [`table`] is three quarters of a megabyte of JSONL and
#: a *draw* reads it, so a conditioned arm asking for one (location, mode)'s
#: maps at a time was re-parsing the whole record thousands of times — 17.7 ms
#: each, minutes of planning for an answer that never changed. [`ceiling`] holds
#: its own read of this same file for the same reason. The stat is what makes it
#: safe to hold: `palettes carriers` rewrites the record in-process during a
#: build, and a cache keyed on the path alone would serve the old table after it.
_TABLES: dict = {}


def table(directory: Path | None = None) -> dict:
    """`{cell: {map: mean share}}`, largest mean first. What a draw reads.

    Memoized on the record's own `(path, mtime, size)`, so a rebuild is picked up
    and a sweep of draws is not a sweep of parses. The dict handed back is the
    cached one: **a caller must not write to it**, and none does — every reader
    here builds a new list or dict out of it.
    """
    path = record_path(directory)
    try:
        stamp = path.stat()
        key = (str(path), stamp.st_mtime_ns, stamp.st_size)
    except OSError:
        key = None
    if key is not None and key in _TABLES:
        return _TABLES[key]
    out: dict = {}
    for row in read(directory):
        if row.get("kind") != CARRIER_ROW:
            continue
        out.setdefault(str(row["cell"]), {})[str(row["map"])] = float(row["mean"])
    built = {
        cell: dict(sorted(maps.items(), key=lambda item: (-item[1], item[0])))
        for cell, maps in out.items()
    }
    if key is not None:
        _TABLES.clear()
        _TABLES[key] = built
    return built


def for_cell(cell: str, within=None, directory: Path | None = None) -> list:
    """`[(map, mean share)]` for one cell, strongest first.

    `within` is the set of maps the caller may actually draw — a pass's collapsed
    palette pool, which holds one member per group. Passing it is what makes the
    launch refusal say something true: a cell whose only carriers are maps this
    pass cannot reach is a cell this pass cannot hit, and refusing on the
    un-narrowed table would let the pass start and then come up SHORT for a reason
    nothing reported.
    """
    reachable = None if within is None else {str(name) for name in within}
    return [
        (name, share)
        for name, share in table(directory).get(str(cell), {}).items()
        if reachable is None or name in reachable
    ]


def deliveries(directory: Path | None = None) -> dict:
    """`{(map, field): {every cell that map is dominant in on that field}}`.

    The table read the other way round. A row says "this map carries this cell on
    these fields"; a **delivery** is one (map, field) picture, and what it is
    dominant in is a *set*, because the dominance rule admits more than one cell
    per picture. Nothing else in this module needs that view — a draw wants one
    cell's carriers — and [`co_dominance`] is the reader that does.
    """
    out: dict = {}
    for row in read(directory):
        if row.get("kind") != CARRIER_ROW:
            continue
        for klass in row.get("fields") or ():
            out.setdefault((str(row["map"]), str(klass)), set()).add(str(row["cell"]))
    return out


def co_dominance(cell: str, directory: Path | None = None) -> dict:
    """`{other cell: the share of this cell's deliveries that also land it}`.

    What a picture of one colour is **also** a picture of. A map drawn to carry
    `dark_vivid_lime` delivers 2.3 cells on the reference fields, and the extra
    ones are not noise and not adjacency on the wheel — they are measured, and
    they are what a colour target spends its neighbours' allowance on. The
    counterpart in [`curation.ceiling.Rule`] raises those cells' allowances in
    proportion, which is the difference between a target that can be met and a
    program that is infeasible for a reason nobody chose.

    Denominated in **deliveries and not maps**: a map that carries the cell on all
    three reference fields is three chances to land a companion, and a map that
    carries it on one is one. `{}` where nothing carries the cell at all, which is
    a fact [`for_cell`] reports better.
    """
    landed = [cells for cells in deliveries(directory).values() if str(cell) in cells]
    if not landed:
        return {}
    counts: dict = {}
    for cells in landed:
        for other in cells:
            if other != str(cell):
                counts[other] = counts.get(other, 0) + 1
    return {
        name: round(count / len(landed), PLACES)
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    }


def draw(cell: str, count: int, seed: int, within=None, directory: Path | None = None) -> list:
    """`count` maps drawn for one cell, weighted by mean share, without replacement.

    Weighted rather than argmax because a target met by one map is a target met by
    one picture repeated: the top green carrier would take every carrier attempt
    the plan holds and the group cap would then refuse all but the first of them.
    Weighted rather than uniform because the table's mean share really does
    separate `Green Vault` at 0.548 from the tail at 0.10, and a draw that ignored
    it would spend a third of the attempts on maps that barely carry.
    """
    import numpy

    offers = for_cell(cell, within=within, directory=directory)
    if not offers or count <= 0:
        return []
    names = [name for name, _share in offers]
    weights = numpy.asarray([max(float(share), 0.0) for _name, share in offers])
    if weights.sum() <= 0.0:
        weights = numpy.ones(len(names))
    rng = numpy.random.default_rng(int(seed))
    size = min(int(count), len(names))
    picked = rng.choice(
        len(names), size=size, replace=False, p=(weights / weights.sum()).astype(float)
    )
    return [names[int(index)] for index in picked]


# --------------------------------------------------------------------------- #
# Building it.
# --------------------------------------------------------------------------- #
def _recoloured(field: Path, name: str, mirror: bool, klass: str) -> Path:
    """One map on one reference field. Through the one recolour path there is.

    [`fractal_wallpapers.curation.colorize.recolored`] is imported here rather
    than at module scope: it is the only spelling of "the dumped field through one
    map" in the repository and a second one is how two pictures of one map come to
    disagree, but `palettes` sits under `curation` in the import order and a
    module-level import would invert it.
    """
    from fractal_wallpapers.curation.colorize import recolored

    return recolored(field, name, mirror, RECOLOUR_DIR / klass / f"{name}.jpg")


def rows_for(name: str, readings: dict) -> list:
    """Every (map, cell) row one map's three readings produce.

    `readings` is `{class: Reading}`. A cell earns a row when it is dominant on at
    least one field; the row carries its share on all three, because the mean the
    draw weights by is a mean over the fields and not over the wins.
    """
    carried: dict = {}
    for klass in reference_fields.CLASSES:
        for cell in readings[klass].cells:
            carried.setdefault(cell, []).append(klass)
    out = []
    for cell, fields in sorted(carried.items()):
        share = {
            klass: round(readings[klass].share_of(cell), PLACES)
            for klass in reference_fields.CLASSES
        }
        out.append(
            {
                "schema": SCHEMA,
                "kind": CARRIER_ROW,
                "map": name,
                "cell": cell,
                "family": dominance.family_of(cell),
                "fields": fields,
                "share": share,
                "mean": round(sum(share.values()) / len(share), PLACES),
            }
        )
    return sorted(out, key=lambda row: (-row["mean"], row["cell"]))


def run(directory: Path | None = None, force: bool = False, log=print) -> dict:
    """Build the table over the whole library and write the tracked record.

    Every map, not the collapsed pool: see the module docstring. About eighty
    seconds for 2,703 recolours, and the recolours are kept, so a second run over
    an unchanged library is the census alone.
    """
    from fractal_wallpapers.models import palette_sets

    library = list(groups.library(directory))
    fields = reference_fields.fields(directory, force=force)
    cyclic = palette_sets.cyclic()
    started = time.perf_counter()
    rows: list = []
    counted: dict = {}
    for index, name in enumerate(library):
        readings = {}
        for klass, field in fields.items():
            picture = _recoloured(field, name, name not in cyclic, klass)
            readings[klass] = dominance.of_picture(picture)
        made = rows_for(name, readings)
        rows += made
        for row in made:
            counted[row["cell"]] = counted.get(row["cell"], 0) + 1
        if log and index % 200 == 199:
            done = index + 1
            rate = (time.perf_counter() - started) / done
            log(f"[carriers] {done}/{len(library)}, {rate * (len(library) - done):.0f}s left")
    seconds = time.perf_counter() - started
    header = method(len(library), len(rows), seconds)
    path = write([header, *rows], directory)
    if log:
        log(f"[carriers] {len(rows)} row(s) over {len(library)} map(s) in {seconds:.0f}s")
    return {
        **header,
        "record": str(path),
        "bytes": path.stat().st_size,
        "cells_carried": len(counted),
        "cells_uncarried": [cell for cell in dominance.cells() if cell not in counted],
        "by_cell": dict(sorted(counted.items(), key=lambda item: (-item[1], item[0]))),
    }


__all__ = [
    "CARRIER_ROW",
    "METHOD_ROW",
    "PLACES",
    "RECORD_NAME",
    "SCHEMA",
    "CarrierError",
    "co_dominance",
    "deliveries",
    "draw",
    "for_cell",
    "method",
    "read",
    "record_path",
    "rows_for",
    "run",
    "table",
    "text_of",
    "write",
]
