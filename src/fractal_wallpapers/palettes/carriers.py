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
map carries anywhere, with the cell's share on all three fields — including the
fields where it does not carry, because the mean the draw weights by is a mean
over the fields and a mean over only the wins would rank a map that carries once
above one that nearly carries three times.

**Two members a reader sees are not on disk.** `fields` — which of the three the
cell was dominant on — and `mean` came off the row on 2026-09-06, and [`fill`]
puts both back at the read, so nothing above this module knows. See there for the
derivation and for what it was verified against; [`write`] re-checks it on every
build, which is the one moment the measured answer exists.

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
3,665 rows over 1,021 maps in **690,732 bytes**, which is 65.9% of
`test_history_purity`'s 1 MiB — small enough to keep in the history, where a
reader of a pass record that names a carrier can find out what the pass believed
about it. It grows at 3.71 rows and 685 bytes a map, the marginal rate measured
across one drop, so the headroom is 522 maps. It was 881,834 bytes and 84.1% until
the two derived members came off. The pictures behind it are not tracked: 2,703
recolours land under `artifacts/` and are remade by `fractal-wallpapers palettes
carriers` in about eighty seconds.
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

#: What a carrier row is **written** with. Everything a reader gets that is not
#: here is derived at the read — see [`fill`].
STORED: tuple[str, ...] = ("schema", "kind", "map", "cell", "family", "share")

#: What [`fill`] puts back, in the order a written row used to carry them.
DERIVED: tuple[str, ...] = ("fields", "mean")

#: Decimals a share is written to. Six, which is the codebook's own rounding and
#: two more than any decision reads.
PLACES = 6

#: What the recolour subtree is called under the regenerable tree. The path is
#: [`recolour_dir`] and not a constant: `under()` reads which tier that subtree is
#: on, and a constant would have to answer that question at import time.
RECOLOUR_UNIT = ("palettes", "carriers")


class CarrierError(RuntimeError):
    """The carrier table cannot be built or cannot be read."""


def recolour_dir() -> Path:
    """Where the recolours live. Ignored, regenerable, and about 40 MB.

    Through `under()` rather than a bare `Path("artifacts")`, which is what this
    was until 2026-09-02. That spelling is relative to the **shell's** working
    directory, so on a machine that has moved its hot root it wrote to a fourth
    place that is neither tier — and nothing would have said so, because a
    regenerable subtree that is not where it should be looks exactly like one
    nothing has built yet.
    """
    from fractal_wallpapers.paths import under

    return under(*RECOLOUR_UNIT)


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


# --------------------------------------------------------------------------- #
# The two derived members, and the seam they are derived at.
# --------------------------------------------------------------------------- #
def fill(rows: list) -> list:
    """Every carrier row with `fields` and `mean` put back. **The read.**

    Both are functions of `share`, which is the one member of a row that is a
    measurement, and both used to be stored beside it. They came off on
    2026-09-06 because the file is tracked and the history guard acts at 1 MiB:
    they were 191,102 of 881,834 bytes — 21.7% — and the record was at 84.1% of
    the guard with 189 maps of headroom, which is under two of the drops this
    library takes.

    * **`mean`** is exactly the mean of the three shares, which is what
      [`rows_for`] computed.
    * **`fields`** is which of the three reference fields the cell was dominant
      on, re-derived by applying [`palettes.dominance`]'s own rule — the one the
      header carries in prose — to the shares. A cell is dominant on a field when
      it holds [`dominance.CELL_ALONE`], or when it leads that field's shares and
      holds [`dominance.CELL_LEAD`].

    **The lead is taken over the map's own rows, and that is exact rather than an
    approximation.** A cell absent from the table was dominant on no field, so its
    share is under `CELL_ALONE` on every one of them and under `CELL_LEAD` on the
    one it might have led — otherwise the rule would have made it a carrier and
    given it a row. So the largest share among a map's rows on a field is the
    largest share over all 48 cells whenever the answer can change anything, and
    where it is not, both readings refuse. Ties break on the cell name, which is
    [`dominance._dominant`]'s own tiebreak.

    Verified over the whole committed table before either member was dropped:
    **10,995 of 10,995 (row, field) reads and 3,665 of 3,665 means**, no
    exception. [`write`] re-checks it on every build, at the one moment the true
    answer is in hand — see there.
    """
    out: list = []
    by_map: dict[str, list] = {}
    for row in rows:
        if row.get("kind") != CARRIER_ROW:
            continue
        missing = [
            klass
            for klass in reference_fields.CLASSES
            if (row.get("share") or {}).get(klass) is None
        ]
        if missing:
            # Fail closed. `share` is the one member of a carrier row that is a
            # measurement, and since the two derived members came off it is also
            # the only thing the rest of the row is made of — so a row short of it
            # is not a thin row, it is a row that says nothing. Carried through
            # instead, it would reach `table` as a `KeyError` on `mean` from
            # whichever draw happened to want that cell.
            raise CarrierError(
                f"carrier row {row.get('map')!r}/{row.get('cell')!r} names no share on "
                f"{missing}. `fields` and `mean` are derived from the three shares, so a row "
                f"without them carries no reading at all."
            )
        by_map.setdefault(str(row["map"]), []).append(row)
    leads: dict[tuple[str, str], str] = {}
    for name, mine in by_map.items():
        for klass in reference_fields.CLASSES:
            leader = min(mine, key=lambda row: (-float(row["share"][klass]), str(row["cell"])))
            leads[(name, klass)] = str(leader["cell"])
    for row in rows:
        if row.get("kind") != CARRIER_ROW:
            out.append(row)
            continue
        share = row["share"]
        fields = [
            klass
            for klass in reference_fields.CLASSES
            if float(share[klass]) >= dominance.CELL_ALONE
            or (
                leads[(str(row["map"]), klass)] == str(row["cell"])
                and float(share[klass]) >= dominance.CELL_LEAD
            )
        ]
        out.append(
            {
                **{key: row[key] for key in STORED if key in row},
                "fields": fields,
                "mean": round(sum(float(value) for value in share.values()) / len(share), PLACES),
            }
        )
    return out


def thin(row: dict) -> dict:
    """One carrier row as it is stored: [`STORED`] and nothing [`fill`] derives."""
    if row.get("kind") != CARRIER_ROW:
        return row
    return {key: row[key] for key in STORED if key in row}


def text_of(rows: list) -> str:
    """The record as it is written: one JSON object a line, LF, UTF-8.

    Carrier rows are thinned on the way out, so a caller holding filled rows — a
    build, or a round-trip through [`read`] — writes the stored shape either way
    and the file cannot come to hold a derived member for some rows and not
    others.
    """
    return "".join(json.dumps(thin(row), ensure_ascii=False) + "\n" for row in rows)


def write(rows: list, directory: Path | None = None) -> Path:
    """Write the record where a reader of the library will find it.

    **The derivation is checked here and nowhere else can check it.** A build
    holds the true `fields` — read off the picture by [`dominance.of_picture`],
    not inferred from anything — so this is the one moment the derived answer can
    be compared against the measured one. A drop whose rounding pushed a share
    across a threshold would otherwise be a table that reads back subtly wrong
    with nothing red, and the rows it was wrong about would be exactly the
    marginal carriers a target leans on.

    A caller handing over already-thinned rows states nothing to check and is not
    checked; every row that carries `fields` or `mean` is.
    """
    disagreed = []
    for stated, derived in zip(rows, fill(rows), strict=True):
        if stated.get("kind") != CARRIER_ROW:
            continue
        for member in DERIVED:
            if member in stated and stated[member] != derived[member]:
                disagreed.append(
                    f"{stated['map']}/{stated['cell']}.{member}: measured {stated[member]!r}, "
                    f"derived {derived[member]!r}"
                )
    if disagreed:
        raise CarrierError(
            f"{len(disagreed)} carrier row(s) do not re-derive from their own shares, so the "
            f"table would read back saying something the pictures did not: "
            f"{disagreed[:3]}. `fields` and `mean` are dropped from the record and rebuilt by "
            f"`carriers.fill`; if the rule they are rebuilt by has moved, that function is "
            f"what has to move with it."
        )
    path = record_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


def read(directory: Path | None = None) -> list:
    """Every row of the tracked record, header first, with the derived members back.

    A reader sees the shape the file used to carry — [`fill`] is applied here, so
    no consumer of this table knows that two of its columns are not on disk.
    """
    path = record_path(directory)
    if not path.is_file():
        raise CarrierError(
            f"{path} is not there. `fractal-wallpapers palettes carriers` builds it, "
            "and it is tracked, so a clone has it already."
        )
    return fill(
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    )


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

    return recolored(field, name, mirror, recolour_dir() / klass / f"{name}.jpg")


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
