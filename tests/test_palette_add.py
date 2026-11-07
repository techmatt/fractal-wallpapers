"""`palettes add`: one map admitted, every other row of both tables left as it was.

Every test here works on a small copy of the library under `tmp_path` — a handful
of maps, the produced table and the carrier table cut down to them, and the
grouping beside them — so nothing writes into `data/palettes`. The carrier rows a
splice writes are checked against the committed rows of the same map, which is the
claim the command makes: a splice is what a full `palettes carriers` would write.
"""

from __future__ import annotations

import json
import shutil

import numpy
import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.palettes import (
    admit,
    carriers,
    dominance,
    groups,
    produced,
    reference_fields,
)
from fractal_wallpapers.paths import colormap_dir

#: The small library: the two calibration carriers, the one uncarried map, a
#: group's two members, and two style maps. Sorted, as the library lists itself.
MAPS = sorted(
    ["Garnet Tide", "Green Vault", "atlas_grey", "bronze_packing", "twilight", "twilight_shifted"]
)

#: The map each test admits, held out of the small library's tables.
NEW = "yas"


def _carrier_text(names: list[str]) -> str:
    """The committed carrier record cut down to `names`, header recounted."""
    rows = carriers.read()
    header = dict(rows[0])
    kept = [row for row in rows[1:] if row["map"] in names]
    header["maps"] = len(names)
    header["carriers"] = sum(1 for row in kept if row["kind"] == carriers.CARRIER_ROW)
    header["uncarried"] = sum(1 for row in kept if row["kind"] == carriers.UNCARRIED_ROW)
    return carriers.text_of([header, *kept])


def _produced_text(names: list[str]) -> str:
    return produced.text_of([row for row in produced.read() if row[produced.NAME_COLUMN] in names])


@pytest.fixture
def library(tmp_path):
    """`(library dir, outside dir)`: the small library, and `yas` waiting outside it."""
    where = tmp_path / "palettes"
    where.mkdir()
    for name in MAPS:
        shutil.copyfile(colormap_dir() / f"{name}.json", where / f"{name}.json")
    shutil.copyfile(groups.record_path(), where / groups.RECORD_NAME)
    (where / produced.RECORD_NAME).write_text(_produced_text(MAPS), encoding="utf-8", newline="\n")
    (where / carriers.RECORD_NAME).write_text(_carrier_text(MAPS), encoding="utf-8", newline="\n")
    outside = tmp_path / "incoming"
    outside.mkdir()
    shutil.copyfile(colormap_dir() / f"{NEW}.json", outside / f"{NEW}.json")
    return where, outside


def _readings_from_rows(name: str) -> dict:
    """The `Reading`s the committed rows of `name` were written from, rebuilt from them.

    Enough of a reading for `rows_for`: the dominant cells per field, and each
    carried cell's share there. The rows are the measurement; nothing is invented.
    """
    rows = [row for row in carriers.read()[1:] if row["map"] == name]
    out = {}
    for klass in reference_fields.CLASSES:
        carried = [row for row in rows if row.get("kind") == carriers.CARRIER_ROW]
        out[klass] = dominance.Reading(
            cells=tuple(row["cell"] for row in carried if klass in row["fields"]),
            families=(),
            cell_shares={row["cell"]: row["share"][klass] for row in carried},
            family_shares={},
            neutral=next(
                (row["neutral"][klass] for row in rows if row["kind"] == carriers.UNCARRIED_ROW),
                0.0,
            ),
        )
    return out


# --------------------------------------------------------------------------- #
# The map document.
# --------------------------------------------------------------------------- #
def test_a_library_map_has_no_problems_and_a_broken_one_has_each_named() -> None:
    good = json.loads((colormap_dir() / f"{NEW}.json").read_text(encoding="utf-8"))
    assert admit.problems(good) == []
    for broken, said in (
        ({**good, "schema": 2}, "schema"),
        ({**good, "name": "a/b"}, "name a library file"),
        ({**good, "name": "base~hue-1"}, "name a library file"),
        ({**good, "kind": "diverging"}, "kind"),
        ({**good, "source": " "}, "source"),
        ({**good, "stops": good["stops"][::-1]}, "in order"),
        ({**good, "stops": good["stops"][:-1]}, "span"),
        ({**good, "stops": [[0.0, [0, 0, 0]], [1.0, [0, 0, 256]]]}, "sRGB8"),
        ({**good, "stops": [[0.0, [0, 0, 0]], [1.0, [0, 0, 1.0]]]}, "sRGB8"),
        ({**good, "kind": "cyclic"}, "closes"),
    ):
        assert any(said in problem for problem in admit.problems(broken)), (broken, said)


def test_a_name_the_library_holds_is_refused_without_replace(library) -> None:
    where, outside = library
    copy = outside / "Green Vault.json"
    shutil.copyfile(where / "Green Vault.json", copy)
    before = {path.name: path.read_bytes() for path in where.iterdir()}
    with pytest.raises(admit.AddError, match="already holds 'Green Vault'"):
        admit.run(copy, directory=where)
    assert {path.name: path.read_bytes() for path in where.iterdir()} == before


def test_a_library_file_that_neither_table_names_is_a_first_admission(library) -> None:
    where, outside = library
    shutil.copyfile(outside / f"{NEW}.json", where / f"{NEW}.json")
    assert admit.held(NEW, where / f"{NEW}.json", where) == []
    assert admit.held(NEW, outside / f"{NEW}.json", where) == [f"{NEW}.json"]


# --------------------------------------------------------------------------- #
# The two tables.
# --------------------------------------------------------------------------- #
def test_the_produced_row_is_inserted_in_order_and_every_other_line_is_untouched(
    library,
) -> None:
    where, _outside = library
    path = produced.record_path(where)
    before = path.read_text(encoding="utf-8").splitlines(keepends=True)
    assert admit.produced_row(NEW, where) == "added"
    after = path.read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(after) == len(before) + 1
    named = [row[produced.NAME_COLUMN] for row in produced.read(where)]
    assert named == sorted([*MAPS, NEW])
    added = after[1 + named.index(NEW)]
    assert added == NEW + ",0" * (1 + len(produced.HUES)) + "\n"
    assert [line for line in after if line != added] == before
    assert admit.produced_row(NEW, where) == "kept"
    assert path.read_text(encoding="utf-8").splitlines(keepends=True) == after


def test_a_ledger_tally_rebuilds_the_produced_table_whole(library) -> None:
    """Given the ledger's counts, the table is what `palettes produced` would write over
    the library plus the new map, so a stale row moves with the admission."""
    where, _outside = library
    counts = {"twilight": {"": 7, "blue": 3}, NEW: {"": 2, "orange": 2}}
    text, verb = admit.produced_text(NEW, where, counts)
    assert verb == "rebuilt"
    assert text == produced.text_of(produced.rows_for(counts, sorted([*MAPS, NEW])))
    with pytest.raises(admit.AddError, match="not in this library"):
        admit.produced_text(NEW, where, {"no_such_map": {"": 1}})


def test_the_carrier_splice_is_the_record_a_full_build_would_write(library) -> None:
    """Splice `yas` into a record without it and get the record with it, byte for byte."""
    where, outside = library
    shutil.copyfile(outside / f"{NEW}.json", where / f"{NEW}.json")
    made = admit.splice(NEW, _readings_from_rows(NEW), where)
    want = _carrier_text(sorted([*MAPS, NEW]))
    assert carriers.record_path(where).read_text(encoding="utf-8") == want
    header = carriers.read(where)[0]
    assert header["maps"] == len(MAPS) + 1
    assert header["carriers"] == sum(
        1 for row in carriers.read(where) if row.get("kind") == carriers.CARRIER_ROW
    )
    assert header["uncarried"] == 1, "atlas_grey"
    assert header["seconds"] == carriers.read()[0]["seconds"], "the last full build's, kept"
    assert made["rows"] == sum(1 for row in carriers.read() if row.get("map") == NEW)

    # And a second splice of the same readings — a --replace that changed nothing —
    # is the same file again, with the map's old rows dropped rather than doubled.
    admit.splice(NEW, _readings_from_rows(NEW), where)
    assert carriers.record_path(where).read_text(encoding="utf-8") == want


def test_a_record_about_another_library_is_refused_rather_than_spliced(library) -> None:
    where, outside = library
    (where / carriers.RECORD_NAME).write_text(
        _carrier_text([name for name in MAPS if name != "twilight"]),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(admit.AddError, match="missing \\['twilight'\\]"):
        admit.carrier_state(NEW, where)


def test_an_empty_carrier_record_is_a_refusal_and_not_a_crash(library) -> None:
    where, outside = library
    (where / carriers.RECORD_NAME).write_text("", encoding="utf-8", newline="\n")
    with pytest.raises(admit.AddError, match="is empty"):
        admit.carrier_state(NEW, where)


def test_a_produced_table_out_of_order_or_about_another_library_is_refused(library) -> None:
    where, outside = library
    path = produced.record_path(where)
    rows = produced.read(where)
    produced.write(rows[::-1], where)
    with pytest.raises(admit.AddError, match="sorted order"):
        admit.produced_text(NEW, where)
    produced.write([row for row in rows if row[produced.NAME_COLUMN] != "twilight"], where)
    with pytest.raises(admit.AddError, match="missing \\['twilight'\\]"):
        admit.produced_text(NEW, where)
    assert path.is_file()


def _files(where) -> dict:
    return {path.name: path.read_bytes() for path in where.iterdir()}


def test_a_map_on_a_dominance_threshold_is_refused_before_anything_is_written(
    library, monkeypatch
) -> None:
    """Measured `fields` that do not re-derive from the rounded shares: `carriers.write`
    refuses them, as a full build would, and here that refusal lands before the map
    file, the produced row or the carrier rows are written."""
    where, outside = library
    readings = _readings_from_rows(NEW)
    smooth = readings["smooth"]
    readings["smooth"] = dominance.Reading(
        cells=(*smooth.cells, "dark_vivid_green"),
        families=smooth.families,
        cell_shares={**smooth.cell_shares, "dark_vivid_green": 0.01},
        family_shares=smooth.family_shares,
        neutral=smooth.neutral,
    )
    monkeypatch.setattr(admit, "readings_of", lambda document, fields, recolour_to: readings)
    before = _files(where)
    with pytest.raises(admit.AddError, match="dominance threshold"):
        admit.run(outside / f"{NEW}.json", directory=where)
    assert _files(where) == before


def test_a_name_differing_only_in_case_is_refused_even_with_replace(library, monkeypatch) -> None:
    where, outside = library
    document = json.loads((where / "Green Vault.json").read_text(encoding="utf-8"))
    document["name"] = "green vault"
    copy = outside / "green vault.json"
    copy.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        admit, "readings_of", lambda document, fields, recolour_to: _readings_from_rows(NEW)
    )
    before = _files(where)
    for replace in (False, True):
        with pytest.raises(admit.AddError, match="only in case from 'Green Vault'"):
            admit.run(copy, replace=replace, directory=where)
    assert _files(where) == before


def test_the_whole_command_writes_four_things_and_never_recuts_the_grouping(
    library, monkeypatch
) -> None:
    where, outside = library
    cut = (where / groups.RECORD_NAME).read_bytes()
    monkeypatch.setattr(
        admit, "readings_of", lambda document, fields, recolour_to: _readings_from_rows(NEW)
    )
    report = admit.run(outside / f"{NEW}.json", directory=where)
    # The grouping gains one admission row and every line it held is untouched.
    grouping = (where / groups.RECORD_NAME).read_bytes()
    assert grouping.startswith(cut)
    added = groups.text_of([report["admission"]]).encode("utf-8")
    assert grouping == cut + added
    assert report["admission"]["map"] == NEW
    assert groups.admitted(where)[-1] == report["admission"]
    assert any(groups.RECORD_NAME in line for line in admit.lines(report))
    assert (where / f"{NEW}.json").read_bytes() == (colormap_dir() / f"{NEW}.json").read_bytes()
    assert report["map"] == "written" and report["produced"] == "added"
    assert [name for name, _ in report["nearest"]] == [
        name for name, _ in sorted(report["nearest"], key=lambda item: item[1])
    ]
    assert len(report["nearest"]) == admit.NEAREST

    # The second call is a re-tune: refused bare, admitted with replace, row kept, and
    # the grouping untouched: a re-tune keeps the group it has.
    with pytest.raises(admit.AddError, match="--replace"):
        admit.run(outside / f"{NEW}.json", directory=where)
    again = admit.run(outside / f"{NEW}.json", replace=True, directory=where)
    assert again["map"] == "unchanged" and again["produced"] == "kept"
    assert again["admission"] is None
    assert (where / groups.RECORD_NAME).read_bytes() == grouping


@pytest.mark.parametrize("from_outside", [False, True], ids=["the-library-file", "a-copy"])
def test_a_draft_map_already_in_the_library_is_admitted_to_the_grouping(
    library, monkeypatch, from_outside
) -> None:
    """A style's map sits at `data/palettes/<name>.json` before it is admitted. Handed
    over itself it is a first admission and the file is left alone; handed over from a
    copy it needs `--replace`, and either way it gains its one admission row."""
    where, outside = library
    shutil.copyfile(outside / f"{NEW}.json", where / f"{NEW}.json")
    cut = (where / groups.RECORD_NAME).read_bytes()
    monkeypatch.setattr(
        admit, "readings_of", lambda document, fields, recolour_to: _readings_from_rows(NEW)
    )
    source = outside / f"{NEW}.json" if from_outside else where / f"{NEW}.json"
    report = admit.run(source, replace=from_outside, directory=where)
    assert report["admission"] is not None and report["admission"]["map"] == NEW
    grouping = (where / groups.RECORD_NAME).read_bytes()
    assert grouping == cut + groups.text_of([report["admission"]]).encode("utf-8")
    assert report["map"] == ("unchanged" if from_outside else "already in the library")


def test_an_admission_joins_the_nearest_group_within_the_cut_or_starts_its_own() -> None:
    """[`groups.place`] on made-up distances: a group's distance is the mean to its
    members, the nearest within the cut is joined, and none within it starts one."""
    held = {"m01": ["a", "b"], "map:c": ["c"]}
    near = {"a": 0.01, "b": 0.05, "c": 0.032}
    row = groups.place("x", near, held)
    assert row["joined"] and row["group"] == "m01" and row["m1"] == 0.03
    far = {"a": 0.03, "b": 0.07, "c": 0.045}
    row = groups.place("x", far, held)
    assert not row["joined"] and row["group"] == "map:x"
    # The nearest group is the mean's: c at 0.045, not m01's nearer member at 0.03.
    assert row["nearest"] == "map:c" and row["m1"] == 0.045
    # A pre-cut singleton is joined under its own id, so nothing renames it.
    single = {"a": 0.2, "b": 0.2, "c": 0.01}
    assert groups.place("x", single, held)["group"] == "map:c"


# --------------------------------------------------------------------------- #
# The one-against-all metric.
# --------------------------------------------------------------------------- #
def test_one_row_of_m1_is_the_matrix_row_number_for_number() -> None:
    """At a quarter of the lattice, which keeps it fast and changes no step of either."""
    names = ["Garnet Tide", "Green Vault", "twilight", "twilight_shifted", NEW]
    count = groups.DIRECTIONS // 4
    matrix = groups.m1(names, count=count)
    points = groups.clouds(names)
    for index in (0, 2, 4):
        row = groups.m1_to(points[index], points, count=count, batch=2)
        assert numpy.array_equal(row, matrix[index]), names[index]


def test_nearest_reads_the_maps_off_the_library_it_is_pointed_at(library) -> None:
    where, outside = library
    document = json.loads((outside / f"{NEW}.json").read_text(encoding="utf-8"))
    near = admit.nearest(document, where, top=len(MAPS))
    matrix = groups.m1([*MAPS, NEW])
    want = sorted(zip(MAPS, matrix[-1][:-1].tolist(), strict=True), key=lambda item: item[1])
    assert near == [(name, float(value)) for name, value in want]


# --------------------------------------------------------------------------- #
# The real recolour, where the engine and the reference fields are on this box.
# --------------------------------------------------------------------------- #
def _fields_on_disk():
    if not engine.is_built():
        return None
    found = {row["class"]: reference_fields.field_path(row) for row in reference_fields.read()}
    return found if all(path.is_file() for path in found.values()) else None


def test_a_fresh_recolour_reads_back_the_committed_rows(tmp_path) -> None:
    """Three 160x90 recolours of `yas`, read as `carriers.run` reads one map."""
    fields = _fields_on_disk()
    if fields is None:
        pytest.skip("needs a built engine and the reference fields dumped")
    document = json.loads((colormap_dir() / f"{NEW}.json").read_text(encoding="utf-8"))
    stale = tmp_path / "recolours" / "smooth" / f"{NEW}.jpg"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"not the picture")
    readings = admit.readings_of(document, fields, tmp_path / "recolours")
    want = [row for row in carriers.read() if row.get("map") == NEW]
    assert carriers.rows_for(NEW, readings) == want, "and the stale picture was not read"


def test_remove_takes_an_admitted_map_out_of_every_table_and_nothing_else(library) -> None:
    """`palettes remove` is the inverse of an admission: a map no tile kept leaves."""
    where, _ = library
    gone = "copper_arms"
    shutil.copyfile(colormap_dir() / f"{gone}.json", where / f"{gone}.json")
    names = sorted([*MAPS, gone])
    (where / produced.RECORD_NAME).write_text(_produced_text(names), encoding="utf-8", newline="\n")
    (where / carriers.RECORD_NAME).write_text(_carrier_text(names), encoding="utf-8", newline="\n")
    grouping = groups.read(where)
    report = admit.remove(gone, directory=where)
    assert not (where / f"{gone}.json").exists()
    assert (where / produced.RECORD_NAME).read_text(encoding="utf-8") == _produced_text(MAPS)
    assert (where / carriers.RECORD_NAME).read_text(encoding="utf-8") == _carrier_text(MAPS)
    assert groups.read(where) == [row for row in grouping if row.get("map") != gone]
    assert report["groups"] == 1 and report["maps"] == len(MAPS)


def test_remove_refuses_a_map_the_grouping_cut_placed(library) -> None:
    where, _ = library
    before = _files(where)
    with pytest.raises(admit.AddError, match="cut placed it"):
        admit.remove("Garnet Tide", directory=where)
    assert _files(where) == before
