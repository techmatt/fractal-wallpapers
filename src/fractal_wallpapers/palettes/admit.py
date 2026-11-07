"""Admit one colormap to the library: `fractal-wallpapers palettes add <map.json>`.

A style that matches its own map has to land it in `data/palettes/` with the two
tracked tables beside it agreeing that it is there. Done by hand that was three
steps, each with a trap: write the file, rerun `palettes carriers` over the whole
library (about eighty seconds, 2,703 recolours, to change one map's rows), and
splice a row of zeros into `palette_family_shares.csv`, because `palettes
produced` re-tallies the whole candidate ledger and churns every row a pass has
touched since it last ran. This is those three steps as one command, each made as
narrow as its table allows.

## What it writes, and what it does not

* **The map**, `data/palettes/<name>.json`, formatted by
  [`library_import.text_of`] — one stop a line, which is the shape every tracked
  map already round-trips through. Not written when the file handed over already
  *is* that file.
* **One row of `palette_family_shares.csv`**, all zeros, inserted at the map's
  place in the library's sorted order. Zero is exactly true and not a
  placeholder: that table counts candidate-ledger pictures drawn in a map, and none
  has been drawn in one the library did not hold. Every other line is untouched,
  and the table is refused rather than rewritten if it does not round-trip through
  [`produced.read`] / [`produced.text_of`] byte for byte. Under `--replace` an
  existing row is kept as it is: a re-tuned map keeps the pictures it has made.
* **This map's rows of `carriers.jsonl`**, measured exactly as [`carriers.run`]
  measures one map — its own recolour onto each reference field, read by
  [`dominance.of_picture`], turned into rows by [`carriers.rows_for`] or
  [`carriers.uncarried_row`] — with any rows it had dropped, the new ones spliced in
  at its library position, and the header's `maps`, `carriers` and `uncarried`
  recounted. The header's `seconds` is kept: it is what the last full build took,
  and this did not do one.

* **One admission row of `groups.jsonl`**, appended, for a map new to the library.
  The grouping is a ruling Matt approved merge by merge, and a rerun of `palettes
  groups` would re-decide it over the whole library, so it is never re-cut: M1 from
  the new map to every map already in the library, through [`groups.m1_to`] — one
  row of [`groups.m1`]'s matrix, number for number, without the pairwise loop over
  everything else — places it ([`groups.place`]) in the nearest group within
  [`groups.CUT`], or in a group of its own. Every existing line is untouched, so no
  group id moves. A `--replace` re-tune writes no row: the map keeps its group. The
  three nearest maps are printed beside it.

## Every refusal comes before the first write

All three texts are built and checked, and M1 is taken, before any file in the
library is opened for writing — the carrier text through `carriers.write` itself,
into a scratch directory, so its derivation check is the build's. A map reading on
a dominance threshold under rounding is refused there, as `palettes carriers`
would refuse it. A name differing only in case from one the library holds is
refused even under `--replace`: on NTFS the two are one file.

## The splice is what a full `palettes carriers` would write, apart from `seconds`

That holds, and for three reasons that each have a check behind them here:

1. **Every other map's rows are carried byte for byte.** The record is refused
   unless [`carriers.text_of`] of its own [`carriers.read`] is the file's text, so
   a read-and-rewrite cannot have moved a row it did not mean to.
2. **This map's rows are made by the full build's own calls, on a fresh picture.**
   The recolour is cached by path and [`colorize.recolored`] leaves a file already
   there alone, so a `--replace`d map would otherwise be read off the picture of
   the map it replaced. The three recolours are unlinked first, every time. The
   fold is the map's own `kind`, which is what `palette_sets.cyclic` reads.
3. **The order is the full build's**: library order, which is `sorted` over the
   stems, with each map's rows in [`carriers.rows_for`]'s order. The record is
   refused when the maps it names are not the library less this one, because then
   a full build would have changed rows this splice cannot measure.

What it rests on that it cannot check is that nothing else moved since the last
full build — the reference fields, the dominance rule, the engine's recolour. Any
of those moving is a reason for `palettes carriers`, not for this.
"""

from __future__ import annotations

import bisect
import json
from pathlib import Path

from fractal_wallpapers.palettes import carriers, dominance, groups, produced, reference_fields

#: Characters a map's name may not hold, because the name is a filename on every
#: platform the library is read on and `~` is [`palettes.variants`]' mark.
FORBIDDEN = frozenset('<>:"/\\|?*~')

#: How many nearest maps the summary names.
NEAREST = 3

#: The two kinds a map may be, as `tests/test_colormaps.py` holds them.
KINDS = ("cyclic", "sequential")


class AddError(RuntimeError):
    """The map cannot be admitted. The message is the one line the command prints."""


# --------------------------------------------------------------------------- #
# The map itself.
# --------------------------------------------------------------------------- #
def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def problems(document) -> list[str]:
    """Everything wrong with one map document, as `tests/test_colormaps.py` reads one.

    Empty when the map is one the library would hold. The test's checks, in its
    order, plus the two that only a map arriving from outside can fail: that the
    name is a usable filename, and that the stops are the shape the test indexes.
    """
    if not isinstance(document, dict):
        return ["a colormap is a JSON object"]
    found = []
    if document.get("schema") != 1:
        found.append(f"schema is {document.get('schema')!r}, not 1")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        found.append("it names no `name`")
    elif (
        name != name.strip()
        or name.endswith(".")
        or name.startswith(".")
        or any(char in FORBIDDEN or ord(char) < 32 for char in name)
    ):
        found.append(f"{name!r} is not a name a library file can carry")
    if document.get("kind") not in KINDS:
        found.append(f"kind is {document.get('kind')!r}, not one of {list(KINDS)}")
    source = document.get("source")
    if not isinstance(source, str) or not source.strip():
        found.append("it says nowhere where it came from (`source`)")
    stops = document.get("stops")
    if not isinstance(stops, list) or len(stops) < 2:
        found.append("a gradient needs two ends (`stops`)")
        return found
    shaped = all(
        isinstance(stop, list)
        and len(stop) == 2
        and _is_number(stop[0])
        and isinstance(stop[1], list)
        for stop in stops
    )
    if not shaped:
        found.append("every stop is `[position, [r, g, b]]`")
        return found
    positions = [stop[0] for stop in stops]
    if positions != sorted(positions):
        found.append("stops are not in order")
    if positions[0] != 0.0 or positions[-1] != 1.0:
        found.append("stops do not span 0.0 to 1.0")
    if len(set(positions)) != len(positions):
        found.append("two stops share a position")
    for _, rgb in stops:
        if len(rgb) != 3 or not all(
            isinstance(channel, int) and not isinstance(channel, bool) and 0 <= channel <= 255
            for channel in rgb
        ):
            found.append(f"{rgb!r} is not an sRGB8 colour")
            break
    if document.get("kind") == "cyclic" and stops[0][1] != stops[-1][1]:
        found.append("a cyclic map closes on the colour it opened with")
    return found


def load(source: Path) -> dict:
    """The map document at `source`, refused unless the library could hold it."""
    source = Path(source)
    if not source.is_file():
        raise AddError(f"{source} is not a file")
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as refusal:
        raise AddError(f"{source} is not a JSON document: {refusal}") from refusal
    wrong = problems(document)
    if wrong:
        raise AddError(f"{source} is not a colormap the library can hold: {'; '.join(wrong)}")
    return document


def _library_dir(directory: Path | None) -> Path:
    from fractal_wallpapers.paths import colormap_dir

    return Path(directory) if directory is not None else colormap_dir()


def _same_file(one: Path, other: Path) -> bool:
    try:
        return other.is_file() and Path(one).samefile(other)
    except OSError:
        return False


def held(name: str, source: Path, directory: Path | None = None) -> list[str]:
    """Where the library already holds `name`: its file, a produced row, a carrier row.

    The file counts only when it is not the one being admitted — a style may write
    `data/palettes/<name>.json` first and hand that file over, and that is a first
    admission rather than a replacement for as long as neither table names it.
    """
    where = _library_dir(directory)
    found = []
    target = where / f"{name}.json"
    if target.is_file() and not _same_file(Path(source), target):
        found.append(target.name)
    if any(row[produced.NAME_COLUMN] == name for row in produced_rows(directory)):
        found.append(produced.RECORD_NAME)
    if any(row.get("map") == name for row in _carrier_rows(directory)[1:]):
        found.append(carriers.RECORD_NAME)
    return found


def case_clashes(name: str, directory: Path | None = None) -> list[str]:
    """Every name the library or either table holds that differs from `name` only in case.

    `green vault.json` and `Green Vault.json` are one file on NTFS and on the default
    macOS volume, so admitting the first would overwrite the second's stops under
    its name while both tables went on naming the second. Refused always, `--replace`
    or not: a re-tune spells the name the way the library already does.
    """
    folded = name.casefold()
    held_names = set(groups.library(directory))
    held_names |= {row[produced.NAME_COLUMN] for row in produced_rows(directory)}
    held_names |= {str(row["map"]) for row in _carrier_rows(directory)[1:]}
    return sorted(each for each in held_names if each != name and each.casefold() == folded)


def map_text(document: dict, source: Path, directory: Path | None = None) -> tuple[str | None, str]:
    """`(text to write or None, what happens to the map file)`. Writes nothing."""
    from fractal_wallpapers.palettes import library_import

    target = _library_dir(directory) / f"{document['name']}.json"
    if _same_file(Path(source), target):
        return None, "already in the library"
    text = library_import.text_of(document)
    if target.is_file() and target.read_text(encoding="utf-8") == text:
        return None, "unchanged"
    return text, "replaced" if target.is_file() else "written"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# The produced table.
# --------------------------------------------------------------------------- #
def produced_rows(directory: Path | None = None) -> list[dict]:
    """The produced table, refused unless writing it back changes no byte."""
    path = produced.record_path(directory)
    try:
        rows = produced.read(directory)
    except (produced.ProducedError, ValueError, KeyError) as refusal:
        raise AddError(
            f"{path.name} cannot be read ({refusal}); rebuild it with `palettes produced`"
        ) from refusal
    if produced.text_of(rows) != path.read_text(encoding="utf-8"):
        raise AddError(
            f"{path.name} does not read back to its own text, so rewriting it would move "
            "rows this command does not mean to; rebuild it with `palettes produced`"
        )
    return rows


def produced_text(name: str, directory: Path | None = None) -> tuple[str | None, str]:
    """`(text to write or None, "added" | "kept")` for the produced table. Writes nothing.

    Refused unless the table covers exactly the library less this map, in sorted
    order: an insertion into a table about some other library, or one out of order,
    would be a row in a place a full `palettes produced` would not put it.
    """
    rows = produced_rows(directory)
    names = [row[produced.NAME_COLUMN] for row in rows]
    if names != sorted(names) or len(set(names)) != len(names):
        raise AddError(
            f"{produced.RECORD_NAME} is not one row per map in sorted order, so a row cannot "
            "be put in its place; rebuild it with `palettes produced`"
        )
    expected = set(groups.library(directory)) - {name}
    others = set(names) - {name}
    if others != expected:
        missing, extra = sorted(expected - others), sorted(others - expected)
        raise AddError(
            f"{produced.RECORD_NAME} is not about this library less {name!r} (missing "
            f"{missing[:3]}, extra {extra[:3]}); rebuild it with `palettes produced`"
        )
    if name in names:
        return None, "kept"
    zero = produced.rows_for({}, [name])[0]
    rows.insert(bisect.bisect_left(names, name), zero)
    return produced.text_of(rows), "added"


def produced_row(name: str, directory: Path | None = None) -> str:
    """Insert the map's all-zero row in sorted place; `"added"` or `"kept"`."""
    text, verb = produced_text(name, directory)
    if text is not None:
        _write(produced.record_path(directory), text)
    return verb


# --------------------------------------------------------------------------- #
# The carrier table.
# --------------------------------------------------------------------------- #
def readings_of(
    document: dict,
    fields: dict | None = None,
    recolour_to: Path | None = None,
) -> dict:
    """`{class: Reading}` for one map, each off a recolour made fresh for this call.

    [`carriers._recoloured`]'s picture, with two differences that are both about
    where and not what. The engine reads the map out of a scratch directory holding
    only this document, in the bytes the library file will carry, so the map is
    measured **before** anything in the library is written and a refusal here
    leaves the library as it was. And an existing recolour is **unlinked first**,
    so a re-tuned map is never read off the picture of the map it replaced.
    """
    import tempfile

    from fractal_wallpapers.curation.colorize import recolored
    from fractal_wallpapers.palettes import library_import

    name = str(document["name"])
    fields = reference_fields.fields() if fields is None else fields
    where = carriers.recolour_dir() if recolour_to is None else Path(recolour_to)
    mirror = document["kind"] != "cyclic"
    readings = {}
    with tempfile.TemporaryDirectory(prefix="palettes-add-") as scratch:
        maps = Path(scratch)
        # The library's own formatting, so the engine is handed what the file says.
        (maps / f"{name}.json").write_text(
            library_import.text_of(document), encoding="utf-8", newline="\n"
        )
        for klass in reference_fields.CLASSES:
            picture = where / klass / f"{name}.jpg"
            picture.unlink(missing_ok=True)
            recolored(Path(fields[klass]), name, mirror, picture, colormap_dir=maps)
            readings[klass] = dominance.of_picture(picture)
    return readings


def carrier_state(name: str, directory: Path | None = None) -> tuple[dict, dict, list[str]]:
    """`(header, {map: rows}, library with name)`, refused unless a splice is exact.

    The two refusals are the two ways a splice could differ from a full build in a
    row it did not measure — see the module docstring.
    """
    path = carriers.record_path(directory)
    existing = _carrier_rows(directory)
    if carriers.text_of(existing) != path.read_text(encoding="utf-8"):
        raise AddError(
            f"{path.name} does not read back to its own text, so a splice would rewrite rows "
            "it did not measure; rebuild it with `palettes carriers`"
        )
    if not existing:
        raise AddError(f"{path.name} is empty; build it with `palettes carriers`")
    header, body = dict(existing[0]), existing[1:]
    if header.get("kind") != carriers.METHOD_ROW:
        raise AddError(f"{path.name} does not open on its method row")
    by_map: dict[str, list] = {}
    for row in body:
        by_map.setdefault(str(row["map"]), []).append(row)
    library = sorted(set(groups.library(directory)) | {name})
    others, expected = set(by_map) - {name}, set(library) - {name}
    if others != expected:
        missing, extra = sorted(expected - others), sorted(others - expected)
        raise AddError(
            f"{path.name} is not about this library less {name!r} (missing {missing[:3]}, "
            f"extra {extra[:3]}), so a full build would move rows a splice cannot; run "
            "`palettes carriers`"
        )
    return header, by_map, library


def _carrier_rows(directory: Path | None = None) -> list:
    """[`carriers.read`], with its refusals spoken as this command's."""
    try:
        return carriers.read(directory)
    except (carriers.CarrierError, ValueError, KeyError) as refusal:
        raise AddError(
            f"{carriers.RECORD_NAME} cannot be read ({refusal}); rebuild it with "
            "`palettes carriers`"
        ) from refusal


def carrier_text(name: str, readings: dict, directory: Path | None = None) -> tuple[str, dict]:
    """`(the spliced record's text, summary)`, through every check `carriers.write` runs.

    Written first into a scratch directory **by `carriers.write` itself**, so the
    derivation check is the build's own and not a copy of it that could drift. A
    map whose measured `fields` do not re-derive from its rounded shares — a share
    of 0.1499996 written as 0.15, on the `CELL_ALONE` line — is refused here, before
    anything in the library is written. That is what `palettes carriers` does with
    such a map too: its `write` raises and the whole build stops, so matching it
    means refusing, never writing the row.
    """
    import tempfile

    header, by_map, library = carrier_state(name, directory)
    made = carriers.rows_for(name, readings)
    by_map[name] = made or [carriers.uncarried_row(name, readings)]
    rows = [row for each in library for row in by_map[each]]
    header["maps"] = len(library)
    header["carriers"] = sum(1 for row in rows if row["kind"] == carriers.CARRIER_ROW)
    header["uncarried"] = sum(1 for row in rows if row["kind"] == carriers.UNCARRIED_ROW)
    with tempfile.TemporaryDirectory(prefix="palettes-add-") as scratch:
        try:
            written = carriers.write([header, *rows], Path(scratch))
        except carriers.CarrierError as refusal:
            raise AddError(
                f"{name!r} reads on a dominance threshold, so its rows would not read back "
                f"as measured and `palettes carriers` would refuse it as well: {refusal}"
            ) from refusal
        text = written.read_text(encoding="utf-8")
    return text, {
        "rows": len(made),
        "cells": [row["cell"] for row in made],
        "uncarried": not made,
        "maps": header["maps"],
        "carriers": header["carriers"],
    }


def splice(name: str, readings: dict, directory: Path | None = None) -> dict:
    """Replace one map's rows of `carriers.jsonl` with the ones `readings` make."""
    text, summary = carrier_text(name, readings, directory)
    _write(carriers.record_path(directory), text)
    return summary


# --------------------------------------------------------------------------- #
# Where the map would sit among the groups.
# --------------------------------------------------------------------------- #
def _weighted_cloud(document: dict):
    stops = document["stops"]
    return groups.weighted(
        groups.cloud_of([stop[0] for stop in stops], [stop[1] for stop in stops])
    )


def nearest(document: dict, directory: Path | None = None, top: int = NEAREST) -> list:
    """`[(map, M1)]`: the `top` library maps nearest this one, nearest first."""
    return closest(distances(document, directory), top)


def closest(distance: dict, top: int = NEAREST) -> list:
    """`[(map, M1)]`, the `top` nearest of a [`distances`] reading, ties by name."""
    order = sorted(distance.items(), key=lambda item: (item[1], item[0]))
    return order[:top]


def distances(document: dict, directory: Path | None = None) -> dict:
    """`{map: M1}` from this map to every other map of the library.

    Every other map's cloud is read off its own file in `directory`, through
    [`groups.cloud_of`] — the arithmetic [`groups.cloud`] spends on the library —
    and the distances are [`groups.m1_to`], one row of [`groups.m1`].
    """
    import numpy

    where = _library_dir(directory)
    name = str(document["name"])
    others = [each for each in groups.library(directory) if each != name]
    if not others:
        return {}
    held_clouds = []
    for each in others:
        path = where / f"{each}.json"
        try:
            held_clouds.append(_weighted_cloud(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, KeyError, TypeError, IndexError) as refusal:
            raise AddError(
                f"{path.name} cannot be read as a colormap ({refusal}), so M1 to the library "
                "cannot be taken"
            ) from refusal
    points = numpy.stack(held_clouds).astype(numpy.float32)
    distance = groups.m1_to(_weighted_cloud(document).astype(numpy.float32), points)
    return {each: float(distance[index]) for index, each in enumerate(others)}


# --------------------------------------------------------------------------- #
# The command.
# --------------------------------------------------------------------------- #
def run(
    source: Path,
    replace: bool = False,
    directory: Path | None = None,
    fields: dict | None = None,
    recolour_to: Path | None = None,
) -> dict:
    """Admit the map at `source`. Refuses before writing anything, or writes all four:
    the map, its produced row, its carrier rows, and its groups admission row.

    `fields` is `{class: dumped field}` and `recolour_to` the recolour tree, both
    the real ones unless a caller — a test — hands its own.
    """
    source = Path(source)
    document = load(source)
    name = str(document["name"])
    where = _library_dir(directory)
    if source.resolve().parent == where.resolve() and source.stem != name:
        raise AddError(
            f"{source.name} is in the library but names itself {name!r}; a library map's "
            "name is its filename"
        )
    clashes = case_clashes(name, directory)
    if clashes:
        raise AddError(
            f"{name!r} differs only in case from {clashes[0]!r}, which the library already "
            "holds, and the two would be one file on a case-insensitive disk; spell it as "
            "the library does"
        )
    already = held(name, source, directory)
    if already and not replace:
        raise AddError(
            f"the library already holds {name!r} ({', '.join(already)}); pass --replace to "
            "re-tune it"
        )
    # Everything that can refuse does so before the library is touched: both tables
    # are checked to be spliceable, the map is measured off a scratch copy, all three
    # texts are built and checked, and M1 is taken. Only then is anything written.
    carrier_state(name, directory)
    produced_new, row = produced_text(name, directory)
    readings = readings_of(document, fields, recolour_to)
    carriers_new, spliced = carrier_text(name, readings, directory)
    map_new, wrote = map_text(document, source, directory)
    distance = distances(document, directory)
    near = closest(distance)
    # A map new to the library is admitted to the grouping; a re-tune keeps the group
    # it has, because a map that started one may have been joined since. New means no
    # table names it: a library file alone (a style's draft map, admitted from a copy
    # under --replace) has never been grouped.
    admission = None
    tabled = [where_held for where_held in already if where_held != f"{name}.json"]
    if not tabled and groups.read(directory):
        standing = groups.standing(list(distance), directory=directory)
        admission = groups.place(name, distance, standing)
    path = where / f"{name}.json"
    if map_new is not None:
        _write(path, map_new)
    if produced_new is not None:
        _write(produced.record_path(directory), produced_new)
    _write(carriers.record_path(directory), carriers_new)
    if admission is not None:
        with groups.record_path(directory).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(groups.text_of([admission]))
    return {
        "name": name,
        "path": str(path),
        "map": wrote,
        "produced": row,
        "carriers": spliced,
        "nearest": near,
        "twin": bool(near) and near[0][1] < groups.CUT,
        "admission": admission,
    }


def users(name: str) -> list[str]:
    """What still draws in a map: a catalog palette entry with keeps, or a style that
    suggests it and is not discarded."""
    from fractal_wallpapers import styles

    rows = {row["style"]: row for row in styles.catalog_rows()}
    found = []
    for row in rows.values():
        for entry in row.get("palettes", []):
            if entry["colormap"] == name and entry.get("keeps"):
                found.append(f"{row['style']}'s kept palette")
    for style in styles.names():
        if (rows.get(style) or {}).get("status") == "discarded":
            continue
        if styles.load(style)["suggested_colormap"] == name:
            found.append(f"style {style}'s suggested map")
    return found


def remove(name: str, directory: Path | None = None) -> dict:
    """Take a map out of the library: its file, produced row, carrier rows and groups
    admission row; and any keep-less entry naming it from a mode's palette set.

    The inverse of [`run`] for a map no tile kept (Matt's rule: only picked palettes
    are saved). Refused while anything still draws in it ([`users`]), and for a map the
    grouping's own cut placed or another map joined, which only a re-cut could move.
    Every refusal comes before the first write.
    """
    from fractal_wallpapers import style_catalog

    where = _library_dir(directory)
    path = where / f"{name}.json"
    if not path.is_file():
        raise AddError(f"the library holds no map {name!r}")
    using = users(name) if directory is None else []
    if using:
        raise AddError(f"{name!r} is still drawn in: {', '.join(using)}")
    rows = groups.read(directory)
    admitted = [r for r in rows if r.get("kind") == "admitted" and r.get("map") == name]
    joined = [
        r["map"]
        for r in rows
        if r.get("kind") == "admitted" and r.get("map") != name and r.get("group") == f"map:{name}"
    ]
    if rows and (not admitted or joined):
        why = f"{', '.join(joined)} joined its group" if joined else "the grouping's cut placed it"
        raise AddError(f"{name!r} cannot leave {groups.RECORD_NAME} by itself: {why}")
    produced_list = produced_rows(directory)
    kept_rows = [row for row in produced_list if row[produced.NAME_COLUMN] != name]
    header, by_map, library = carrier_state(name, directory)
    library = [each for each in library if each != name]
    body = [row for each in library for row in by_map[each]]
    header["maps"] = len(library)
    header["carriers"] = sum(1 for row in body if row["kind"] == carriers.CARRIER_ROW)
    header["uncarried"] = sum(1 for row in body if row["kind"] == carriers.UNCARRIED_ROW)
    carrier_new = carriers.text_of([header, *body])
    # Written last, in the order nothing reads half-done: the tables, then the map.
    _write(produced.record_path(directory), produced.text_of(kept_rows))
    _write(carriers.record_path(directory), carrier_new)
    if rows:
        _write(
            groups.record_path(directory), groups.text_of([r for r in rows if r not in admitted])
        )
    path.unlink()
    dropped = []
    if directory is None and style_catalog.catalog_path().is_file():
        catalog = json.loads(style_catalog.catalog_path().read_text(encoding="utf-8"))
        for row in catalog["modes"]:
            before = len(row.get("palettes", []))
            row["palettes"] = [e for e in row.get("palettes", []) if e["colormap"] != name]
            if len(row["palettes"]) != before:
                dropped.append(row["style"])
        if dropped:
            style_catalog.write(catalog)
    return {
        "name": name,
        "produced": len(produced_list) - len(kept_rows),
        "carriers": sum(len(rows_of) for each, rows_of in by_map.items() if each == name),
        "groups": len(admitted),
        "maps": header["maps"],
        "sets": dropped,
    }


def lines(report: dict) -> list[str]:
    """What the command prints: one line a table, then the nearest maps."""
    from fractal_wallpapers.paths import tracked_name

    carried = report["carriers"]
    if carried["uncarried"]:
        cells = "dominant in no cell on any field (an uncarried row)"
    else:
        cells = f"{carried['rows']} row(s): {', '.join(carried['cells'])}"
    out = [
        f"[add] {report['name']}: {tracked_name(Path(report['path']))} ({report['map']})",
        f"[add] {produced.RECORD_NAME}: row {report['produced']}",
        f"[add] {carriers.RECORD_NAME}: {cells}; header now {carried['maps']} maps, "
        f"{carried['carriers']} carrier rows",
    ]
    admission = report.get("admission")
    if admission is None:
        out.append(f"[add] {groups.RECORD_NAME}: unchanged (a re-tune keeps its group)")
    elif admission["joined"]:
        out.append(
            f"[add] {groups.RECORD_NAME}: admitted into {admission['group']} (mean M1 "
            f"{admission['m1']:.6f} within the cut {groups.CUT}); no group id moved"
        )
    else:
        out.append(
            f"[add] {groups.RECORD_NAME}: admitted as its own group {admission['group']} "
            f"(nearest {admission['nearest']} at mean M1 {admission['m1']}, over the cut "
            f"{groups.CUT})"
        )
    out.append(f"[add] nearest maps by M1 (cut {groups.CUT}):")
    out += [f"[add]   {other}  {distance:.6f}" for other, distance in report["nearest"]]
    return out


__all__ = [
    "FORBIDDEN",
    "KINDS",
    "NEAREST",
    "AddError",
    "carrier_state",
    "carrier_text",
    "case_clashes",
    "closest",
    "distances",
    "held",
    "lines",
    "load",
    "map_text",
    "nearest",
    "problems",
    "produced_row",
    "produced_text",
    "readings_of",
    "run",
    "splice",
]
