"""The pool pictures' archive mirror: where a picture resolves, and the loud failure.

`paths`' *The one name finer than a top-level name* is the rule; `picture_mirror`
moves the files. These pin the resolver's three answers (hot, mirror, hot
spelling for neither), that an unplugged archive raises for a picture whose hot
copy is gone and only for that, and that the readers which list or delete pictures
reach both places. Every root is a temporary directory: nothing here can see this
machine's real store.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import paths, picture_mirror
from fractal_wallpapers.curation import candidate_ledger
from fractal_wallpapers.curation.candidate_ledger import sweep

STORED = "artifacts/curation/depth/leg/pictures/{}.jpg"


@pytest.fixture
def roots(tmp_path, monkeypatch):
    hot, cold = tmp_path / "hot", tmp_path / "cold"
    (hot / "curation" / "depth" / "leg" / "pictures").mkdir(parents=True)
    (cold / "pool_pictures" / "depth" / "leg" / "pictures").mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(hot))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(cold))
    return hot, cold


def put(root, top, name, data=b"jpeg"):
    where = root / top / "depth" / "leg" / "pictures" / f"{name}.jpg"
    where.write_bytes(data)
    return where


def unplug(cold, monkeypatch):
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, str(cold.parent / "unplugged"))


def test_a_pool_picture_resolves_hot_then_mirror_then_hot_spelling(roots):
    hot, cold = roots
    both = put(hot, "curation", "both")
    put(cold, "pool_pictures", "both")
    mirrored = put(cold, "pool_pictures", "mirrored")
    assert paths.rehome(STORED.format("both")) == both, "hot wins"
    assert paths.rehome(STORED.format("mirrored")) == mirrored
    assert paths.rehome(STORED.format("neither")) == (
        hot / "curation" / "depth" / "leg" / "pictures" / "neither.jpg"
    ), "what exists nowhere resolves where writes land"


def test_only_the_pictures_shape_has_a_mirror(roots):
    hot, cold = roots
    (cold / "pool_pictures" / "depth" / "leg" / "fields").mkdir()
    (cold / "pool_pictures" / "depth" / "leg" / "fields" / "f.f32").write_bytes(b"x")
    assert paths.rehome("artifacts/curation/depth/leg/fields/f.f32").parent == (
        hot / "curation" / "depth" / "leg" / "fields"
    )
    assert not paths.is_pool_picture(["curation", "depth", "leg", "pictures", "x.leveled", "m"])


def test_an_unplugged_archive_raises_only_where_the_hot_copy_is_gone(roots, monkeypatch):
    hot, cold = roots
    kept = put(hot, "curation", "kept")
    unplug(cold, monkeypatch)
    assert paths.rehome(STORED.format("kept")) == kept, "a hot picture needs no archive"
    with pytest.raises(paths.ArchiveUnreachable):
        paths.rehome(STORED.format("moved"))


def test_no_archive_configured_answers_absent_as_before(roots, monkeypatch):
    hot, _ = roots
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    rows = [{"key": "gone", "picture": STORED.format("gone")}]
    assert candidate_ledger.present_pictures(rows) == set()


def test_present_pictures_counts_the_mirror_and_refuses_unplugged(roots, monkeypatch):
    hot, cold = roots
    put(hot, "curation", "hot")
    put(cold, "pool_pictures", "cold")
    rows = [{"key": name, "picture": STORED.format(name)} for name in ("hot", "cold", "none")]
    assert candidate_ledger.present_pictures(rows) == {"hot", "cold"}
    assert candidate_ledger.present_pictures(rows[:1]) == {"hot"}
    unplug(cold, monkeypatch)
    assert candidate_ledger.present_pictures(rows[:1]) == {"hot"}, "all hot: nothing to ask"
    with pytest.raises(paths.ArchiveUnreachable):
        candidate_ledger.present_pictures(rows)


def test_a_pass_over_a_directory_lists_it_and_agrees_with_the_stat(roots):
    hot, cold = roots
    for number in range(paths.LISTING_AFTER + 10):
        put(hot if number % 2 else cold, "curation" if number % 2 else "pool_pictures", number)
    tiers = paths.Tiers.current()
    for number in range(paths.LISTING_AFTER + 10):
        top, root = ("curation", hot) if number % 2 else ("pool_pictures", cold)
        found = paths.rehome(STORED.format(number), tiers)
        assert found == root / top / "depth" / "leg" / "pictures" / f"{number}.jpg"


def test_delete_pictures_takes_both_copies_and_refuses_unplugged(roots, monkeypatch):
    hot, cold = roots
    one, two = put(hot, "curation", "x"), put(cold, "pool_pictures", "x")
    out = sweep.delete_pictures([STORED.format("x")], log=lambda *_: None)
    assert out["deleted"] == 1 and not one.exists() and not two.exists()
    put(hot, "curation", "y")
    unplug(cold, monkeypatch)
    with pytest.raises(paths.ArchiveUnreachable):
        sweep.delete_pictures([STORED.format("y")], log=lambda *_: None)


def test_archive_then_prune_hot_moves_all_but_the_protected(roots, monkeypatch):
    hot, cold = roots
    for name in ("a", "b", "kept"):
        put(hot, "curation", name, data=name.encode() * 10)
    rows = [{"key": name, "picture": STORED.format(name)} for name in ("a", "b", "kept")]
    monkeypatch.setattr(candidate_ledger, "stream", lambda: iter(rows))
    monkeypatch.setattr(picture_mirror, "protected", lambda: ({"kept"}, set()))
    quiet = lambda *_: None  # noqa: E731
    report = picture_mirror.archive(log=quiet)
    assert report["planned"] == 2 and report["hot_copies_left"] == 2
    assert picture_mirror.prune_hot(apply=False, log=quiet)["deleted"] == 2
    assert (hot / "curation" / "depth" / "leg" / "pictures" / "a.jpg").exists(), "a dry run"
    assert picture_mirror.prune_hot(apply=True, log=quiet)["deleted"] == 2
    assert sorted(p.name for p in (hot / "curation/depth/leg/pictures").iterdir()) == ["kept.jpg"]
    assert paths.rehome(STORED.format("a")).read_bytes() == b"a" * 10
    assert candidate_ledger.present_pictures(rows) == {"a", "b", "kept"}
    assert picture_mirror.verify(log=quiet)["hot_copies_left"] == 0


def test_orphans_keeps_a_named_mirror_copy_and_sweeps_an_unnamed_one(roots, monkeypatch):
    hot, cold = roots
    named, stray = put(cold, "pool_pictures", "named"), put(cold, "pool_pictures", "stray")
    rows = [{"key": "named", "picture": STORED.format("named"), "hunt": {}}]
    monkeypatch.setattr(sweep.store, "stream", lambda: iter(rows))
    monkeypatch.setattr(sweep, "_decision_rows", lambda tiers: ([], {}))
    record = sweep.orphans(apply=True, log=lambda *_: None)
    assert record["named_by_nothing"] == 1
    assert named.exists() and not stray.exists()


def test_restore_brings_a_picture_back_hot_and_out_of_the_mirror(roots, monkeypatch):
    hot, cold = roots
    put(hot, "curation", "a", data=b"a" * 7)
    rows = [{"key": "a", "picture": STORED.format("a")}]
    monkeypatch.setattr(candidate_ledger, "stream", lambda: iter(rows))
    monkeypatch.setattr(picture_mirror, "protected", lambda: (set(), set()))
    quiet = lambda *_: None  # noqa: E731
    picture_mirror.archive(log=quiet)
    picture_mirror.prune_hot(apply=True, log=quiet)
    out = picture_mirror.restore([STORED.format("a")], log=quiet)
    assert out["restored"] == 1
    assert not (cold / "pool_pictures" / "depth" / "leg" / "pictures" / "a.jpg").exists()
    assert paths.rehome(STORED.format("a")).read_bytes() == b"a" * 7
    assert picture_mirror.read_moved(paths.Tiers.current()) == []
