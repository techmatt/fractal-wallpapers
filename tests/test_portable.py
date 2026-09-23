"""`storage export` and `storage import`: the roster, the manifest, and the refusals.

Everything here is a few small files in `tmp_path` on two fake tiers and a fake
checkout; nothing reads this machine's store. The roster itself is measured
(see `portable`'s module docstring) and what is guarded about it is structural:
every Durable is on it, and the levelling glob is `stamps.SEQUENCE_STORES`.
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path, PurePosixPath

import pytest

from fractal_wallpapers import cli, paths, portable

TREE_ROSTER = (
    portable.Entry("sidecar", portable.TREE, ("curation/supply.jsonl",), ("curate run",), "x"),
    portable.Entry("ledgers", portable.TREE, ("*/walk.jsonl",), ("census",), "x"),
    portable.Entry(
        "sequences", portable.TREE, ("curation/{depth,mine}/*/sequence.jsonl",), ("atlas",), "x"
    ),
    portable.Entry("inbox", portable.CHECKOUT, ("labels/*",), ("label ingest",), "x"),
)


@pytest.fixture
def box(tmp_path, monkeypatch):
    """Two tiers and a checkout, a few files on each, and the package pointed at them."""
    hot = tmp_path / "fast" / paths.ARTIFACTS_NAME
    archive = tmp_path / "slow" / paths.ARTIFACTS_NAME
    checkout = tmp_path / "checkout"
    for where in (hot, archive, checkout):
        where.mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(hot))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(archive))
    monkeypatch.setattr(portable, "repo_root", lambda: checkout)
    monkeypatch.setattr(portable, "tracked_files", lambda: set())
    files = {
        hot / "curation" / "supply.jsonl": b'{"a": 1}\n',
        hot / "curation" / "depth" / "leg1" / "sequence.jsonl": b'{"s": 1}\n',
        hot / "curation" / "depth" / "leg1" / "pictures" / "0001.jpg": b"not carried",
        hot / "curation" / "mine" / "leg2" / "sequence.jsonl": b'{"s": 2}\n',
        hot / "run_hot" / "walk.jsonl": b'{"w": "hot"}\n',
        archive / "run_cold" / "walk.jsonl": b'{"w": "cold"}\n',
        archive / "run_cold" / "views" / "v.jpg": b"not carried either",
        checkout / "labels" / "render.sheet1.json": b"{}",
    }
    for where, body in files.items():
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_bytes(body)
    return {"hot": hot, "archive": archive, "checkout": checkout, "tmp": tmp_path}


def _export(box) -> Path:
    to = box["tmp"] / "export"
    portable.export(to, roster=TREE_ROSTER, pictures=False, log=lambda *_: None)
    return to


def test_export_carries_exactly_the_roster_across_both_tiers_and_the_checkout(box) -> None:
    manifest = json.loads((_export(box) / portable.MANIFEST_NAME).read_text(encoding="utf-8"))
    named = {row["path"]: row["tier"] for row in manifest["files"]}
    assert named == {
        "artifacts/curation/supply.jsonl": paths.HOT,
        "artifacts/curation/depth/leg1/sequence.jsonl": paths.HOT,
        "artifacts/curation/mine/leg2/sequence.jsonl": paths.HOT,
        "artifacts/run_hot/walk.jsonl": paths.HOT,
        "artifacts/run_cold/walk.jsonl": paths.ARCHIVE,
        "labels/render.sheet1.json": portable.CHECKOUT,
    }
    assert all(len(row["sha256"]) == 64 for row in manifest["files"])
    assert manifest["files_count"] == 6
    assert not any(":" in row["path"] or row["path"].startswith("/") for row in manifest["files"])


def test_a_round_trip_lands_every_file_byte_identical_on_a_single_root_box(box, tmp_path) -> None:
    to = _export(box)
    fresh = tmp_path / "fresh" / paths.ARTIFACTS_NAME
    fresh_checkout = tmp_path / "fresh_checkout"
    fresh.mkdir(parents=True)
    fresh_checkout.mkdir()
    portable.repo_root = lambda: fresh_checkout  # the fixture's monkeypatch restores it
    report = portable.import_(to, fresh, log=lambda *_: None)
    assert report["files"] == 6
    # No archive on this box: the archive-tier ledger lands under the one root.
    assert (fresh / "run_cold" / "walk.jsonl").read_bytes() == b'{"w": "cold"}\n'
    assert (fresh / "curation" / "depth" / "leg1" / "sequence.jsonl").is_file()
    assert (fresh_checkout / "labels" / "render.sheet1.json").read_bytes() == b"{}"
    assert not (fresh / "curation" / "depth" / "leg1" / "pictures").exists()
    assert report["by_tier_landed"] == {paths.HOT: 5, portable.CHECKOUT: 1}


def test_an_archive_root_keeps_each_file_on_its_own_tier(box, tmp_path) -> None:
    to = _export(box)
    hot, cold = tmp_path / "h", tmp_path / "c"
    portable.repo_root = lambda: tmp_path / "co"
    portable.import_(to, hot, archive=cold, log=lambda *_: None)
    assert (cold / "run_cold" / "walk.jsonl").is_file()
    assert not (hot / "run_cold").exists()
    assert (hot / "run_hot" / "walk.jsonl").is_file()


def test_a_tampered_file_is_refused_and_nothing_is_written(box, tmp_path) -> None:
    to = _export(box)
    (to / "tree" / "curation" / "supply.jsonl").write_bytes(b'{"a": 2}\n')
    target = tmp_path / "fresh"
    with pytest.raises(portable.PortableRefusal, match="do not match"):
        portable.import_(to, target, log=lambda *_: None)
    assert not target.exists()


def test_a_file_the_manifest_does_not_name_is_refused(box, tmp_path) -> None:
    to = _export(box)
    (to / "tree" / "stray.jsonl").write_bytes(b"{}\n")
    with pytest.raises(portable.PortableRefusal, match="not in its manifest"):
        portable.import_(to, tmp_path / "fresh", log=lambda *_: None)
    assert not (tmp_path / "fresh").exists()


def test_an_existing_destination_is_refused_rather_than_overwritten(box, tmp_path) -> None:
    to = _export(box)
    fresh = tmp_path / "fresh"
    (fresh / "curation").mkdir(parents=True)
    (fresh / "curation" / "supply.jsonl").write_bytes(b"the truth, maybe\n")
    portable.repo_root = lambda: tmp_path / "co"
    with pytest.raises(portable.PortableRefusal, match="already exist"):
        portable.import_(to, fresh, log=lambda *_: None)
    assert (fresh / "curation" / "supply.jsonl").read_bytes() == b"the truth, maybe\n"
    assert not (fresh / "run_hot").exists()


def _split(to: Path, tmp_path: Path) -> tuple[Path, Path]:
    """An export as a transfer tool left it: the tree in one folder, the rest in another."""
    import shutil

    first, second = tmp_path / "part-001" / to.name, tmp_path / "part-002" / to.name
    shutil.copytree(to, first)
    shutil.move(str(first / "tree"), str(second.parent / "tree_moving"))
    second.mkdir(parents=True)
    shutil.move(str(second.parent / "tree_moving"), str(second / "tree"))
    return first, second


def test_an_export_split_across_two_roots_imports_as_one(box, tmp_path) -> None:
    first, second = _split(_export(box), tmp_path)
    fresh = tmp_path / "fresh"
    portable.repo_root = lambda: tmp_path / "co"
    with pytest.raises(portable.PortableRefusal, match="do not match"):
        portable.import_(first, fresh, log=lambda *_: None)
    report = portable.import_([first, second], fresh, log=lambda *_: None)
    assert report["files"] == 6 and len(report["from"]) == 2
    assert (fresh / "run_cold" / "walk.jsonl").read_bytes() == b'{"w": "cold"}\n'


def test_a_name_under_two_roots_with_different_bytes_is_refused(box, tmp_path) -> None:
    first, second = _split(_export(box), tmp_path)
    (first / "tree" / "curation").mkdir(parents=True)
    (first / "tree" / "curation" / "supply.jsonl").write_bytes(b'{"a": 9}\n')
    with pytest.raises(portable.PortableRefusal, match="different bytes"):
        portable.import_([first, second], tmp_path / "fresh", log=lambda *_: None)
    assert not (tmp_path / "fresh").exists()


def test_storage_import_takes_from_more_than_once() -> None:
    parsed = cli.build_parser().parse_args(
        ["storage", "import", "--from", "a", "--from", "b", "--root", "r"]
    )
    assert parsed.source == ["a", "b"]


def test_import_touches_nothing_the_manifest_does_not_name(box, tmp_path) -> None:
    to = _export(box)
    fresh = tmp_path / "fresh"
    (fresh / "other").mkdir(parents=True)
    (fresh / "other" / "keep.txt").write_bytes(b"mine")
    portable.repo_root = lambda: tmp_path / "co"
    portable.import_(to, fresh, log=lambda *_: None)
    written = {path.relative_to(fresh).as_posix() for path in fresh.rglob("*") if path.is_file()}
    assert written == {
        "other/keep.txt",
        "curation/supply.jsonl",
        "curation/depth/leg1/sequence.jsonl",
        "curation/mine/leg2/sequence.jsonl",
        "run_hot/walk.jsonl",
        "run_cold/walk.jsonl",
    }
    assert (fresh / "other" / "keep.txt").read_bytes() == b"mine"


def test_export_refuses_a_directory_that_already_holds_files(box) -> None:
    to = box["tmp"] / "export"
    to.mkdir()
    (to / "old.json").write_text("{}", encoding="utf-8")
    with pytest.raises(portable.PortableRefusal, match="already holds files"):
        portable.export(to, roster=TREE_ROSTER, pictures=False, log=lambda *_: None)


def test_an_unreachable_archive_refuses_rather_than_exporting_the_hot_half(box, monkeypatch):
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(box["tmp"] / "unplugged"))
    with pytest.raises(paths.ArchiveUnreachable):
        portable.export(box["tmp"] / "export", roster=TREE_ROSTER, pictures=False)


def test_tracked_files_never_travel_because_the_clone_brings_them(box, monkeypatch) -> None:
    monkeypatch.setattr(portable, "tracked_files", lambda: {"artifacts/curation/supply.jsonl"})
    rows = portable.resolve(TREE_ROSTER)
    assert "artifacts/curation/supply.jsonl" not in {row["path"] for row in rows}


def test_the_kept_placeholder_expands_to_the_keep_list_and_nothing_else(monkeypatch) -> None:
    monkeypatch.setattr(portable, "kept_stamps", lambda: ("S1", "S2"))
    assert portable._expand("curation/tentative/{kept}/gallery.jsonl") == [
        "curation/tentative/S1/gallery.jsonl",
        "curation/tentative/S2/gallery.jsonl",
    ]


def _kept_record(box, stamp: str, record: str | None) -> None:
    """One kept record on hot: a seat, and a manifest naming `record` as its solve."""
    where = box["hot"] / "curation" / "tentative" / stamp
    where.mkdir(parents=True)
    (where / "gallery.jsonl").write_bytes(b'{"key": "k"}\n')
    solve = {} if record is None else {"record": record}
    (where / "manifest.json").write_text(json.dumps({"solve": solve}), encoding="utf-8")


def test_the_kept_solves_placeholder_is_read_off_the_kept_manifests(box, monkeypatch) -> None:
    monkeypatch.setattr(portable, "kept_stamps", lambda: ("S1", "S2", "S3", "S4"))
    _kept_record(box, "S1", "artifacts/curation/solve/one/solve.json")
    _kept_record(box, "S2", "artifacts/curation/solve/two/solve.json")
    _kept_record(box, "S3", None)  # a manifest naming no solve contributes nothing
    # S4 is on the list and not on this box, which is how a pruned record reads.
    assert portable._expand("curation/solve/{kept_solves}/solve.json") == [
        "curation/solve/one/solve.json",
        "curation/solve/two/solve.json",
    ]


def test_a_kept_record_travels_with_the_solve_its_manifest_names(box, monkeypatch) -> None:
    """A manifest pointing at a file the export did not carry is the failure guarded here."""
    monkeypatch.setattr(portable, "kept_stamps", lambda: ("S1",))
    _kept_record(box, "S1", "artifacts/curation/solve/one/solve.json")
    for name in ("one", "discarded"):
        leg = box["hot"] / "curation" / "solve" / name
        leg.mkdir(parents=True)
        (leg / "solve.json").write_text(f'{{"name": "{name}"}}', encoding="utf-8")
    entry = next(entry for entry in portable.ROSTER if entry.name == "kept solve records")
    carried = {row["path"] for row in portable.resolve((entry,))}
    assert carried == {"artifacts/curation/solve/one/solve.json"}


def _with_reference(box, monkeypatch, *, carried: bool = True):
    """The fixture's roster plus the kept entry, and both checks kept on hot."""
    monkeypatch.setattr(
        portable, "REFERENCE", {"stamp": "S9", "name": "green9", "collection": "green"}
    )
    monkeypatch.setattr(portable, "GENERAL_CHECK", {"stamp": "G1", "name": "general1", "n": 1000})
    monkeypatch.setattr(portable, "kept_stamps", lambda: ("S9", "G1"))
    for stamp, n in (("S9", 1), ("G1", 1000)):
        if stamp == "S9" and not carried:
            continue
        record = box["hot"] / "curation" / "tentative" / stamp
        record.mkdir(parents=True)
        (record / "gallery.jsonl").write_bytes(b'{"key": "k"}\n')
        manifest = {
            "source_commit": "abc",
            "solve": {"config": {"n": n}, "record": "artifacts/curation/solve/x/solve.json"},
        }
        (record / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    entry = next(entry for entry in portable.ROSTER if entry.name == portable.KEPT_ENTRY)
    return (*TREE_ROSTER, entry)


def test_the_reference_travels_with_a_readme_the_manifest_names(box, monkeypatch, tmp_path):
    roster = _with_reference(box, monkeypatch)
    to = box["tmp"] / "export"
    manifest = portable.export(to, roster=roster, pictures=False, log=lambda *_: None)
    assert manifest["reference"]["n"] == 1
    assert "--collection green --no-render" in manifest["reference"]["invocation"]
    readme = (to / portable.REFERENCE_README).read_text(encoding="utf-8")
    assert "`S9`" in readme and portable.reference_invocation() in readme
    # The README is beside the manifest rather than in it, and verifying accepts it...
    portable.verify_export(to, portable.read_manifest(to), log=lambda *_: None)
    # ...but only as the bytes the manifest names.
    (to / portable.REFERENCE_README).write_text("edited\n", encoding="utf-8")
    with pytest.raises(portable.PortableRefusal, match="do not match"):
        portable.verify_export(to, portable.read_manifest(to), log=lambda *_: None)


def test_an_export_whose_reference_is_not_on_the_machine_refuses(box, monkeypatch) -> None:
    roster = _with_reference(box, monkeypatch, carried=False)
    with pytest.raises(portable.PortableRefusal, match="reference record S9"):
        portable.export(box["tmp"] / "export", roster=roster, pictures=False, log=lambda *_: None)


def test_both_checks_are_on_the_keep_list() -> None:
    """The reason neither needs a roster entry of its own.

    Both are kept records, so `{kept}` carries their rows and `{kept_solves}`
    their `solve.json`. A stamp that fell off the keep list is a README naming a
    comparison target the export does not carry.
    """
    from fractal_wallpapers.curation import targets, tentative

    assert portable.REFERENCE["stamp"] in portable.kept_stamps()
    assert portable.GENERAL_CHECK["stamp"] in portable.kept_stamps()
    assert portable.GENERAL_CHECK["n"] == tentative.RECORDED_SEATS
    assert portable.REFERENCE["collection"] in targets.TARGETS
    assert not any("{reference}" in p for entry in portable.ROSTER for p in entry.patterns)


def test_the_readme_names_the_general_check_beside_the_themed_one(box, monkeypatch) -> None:
    """Two checks, two invocations, and the README says they are different passes."""
    roster = _with_reference(box, monkeypatch)
    to = box["tmp"] / "export"
    manifest = portable.export(to, roster=roster, pictures=False, log=lambda *_: None)
    general = manifest["reference"]["general"]
    assert general["stamp"] == portable.GENERAL_CHECK["stamp"]
    assert general["invocation"] == portable.general_check_invocation()
    assert "--n 1000 --no-render" in general["invocation"]
    readme = (to / portable.REFERENCE_README).read_text(encoding="utf-8")
    assert f"`{portable.GENERAL_CHECK['stamp']}`" in readme
    assert portable.GENERAL_CHECK["name"] in readme
    assert portable.general_check_invocation() in readme
    # Both invocations are there and they are not the same command.
    assert portable.reference_invocation() in readme
    assert portable.reference_invocation() != portable.general_check_invocation()


def test_the_sequence_glob_is_the_stores_stamps_declares() -> None:
    from fractal_wallpapers.curation import stamps

    stores = portable.SEQUENCE_GLOB.split("{")[1].split("}")[0].split(",")
    assert tuple(stores) == tuple(stamps.SEQUENCE_STORES)
    assert any(portable.SEQUENCE_GLOB in entry.patterns for entry in portable.ROSTER)


def _durables():
    from fractal_wallpapers.curation import (
        amend,
        durables,
        embeddings,
        flatness,
        hunt,
        signatures,
        spiral_scores,
    )
    from fractal_wallpapers.curation.candidate_ledger import store
    from fractal_wallpapers.palettes import color_mass

    return (
        durables.sidecar(),
        amend.durable(),
        hunt.frames_durable(),
        store.durable_rows(),
        store.durable_scores(),
        flatness.durable(),
        signatures.durable(),
        embeddings.store(),
        spiral_scores.store(),
        color_mass.sweep_log(),
    )


def test_every_durable_is_on_the_roster(tmp_path, monkeypatch) -> None:
    """A Durable nobody added here is a file the next box would silently not have."""
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(tmp_path))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    patterns = [
        piece
        for entry in portable.ROSTER
        if entry.root == portable.TREE
        for raw in entry.patterns
        for piece in portable._expand(raw)
    ]
    missed = []
    for durable in _durables():
        live = Path(durable.live)
        if live.is_relative_to(tmp_path):
            named = live.relative_to(tmp_path).as_posix()
            found = any(fnmatch.fnmatchcase(named, p) for p in patterns)
        else:
            # `conftest.no_signature_sidecar` hangs that one store off a session
            # directory with a serial before its name, so only the name can be read.
            name = re.sub(r"^\d+_", "", live.name)
            found = any(PurePosixPath(p).name == name for p in patterns)
        if not found:
            missed.append(durable.name)
    assert missed == []


def test_the_two_verbs_are_on_the_storage_group() -> None:
    parser = cli.build_parser()
    exported = parser.parse_args(["storage", "export", "--to", "somewhere"])
    imported = parser.parse_args(["storage", "import", "--from", "a", "--root", "b"])
    assert exported.handler is cli.storage_export
    assert imported.handler is cli.storage_import
    assert imported.archive_root is None
