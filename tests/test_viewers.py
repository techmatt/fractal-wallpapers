"""A viewer per planned gallery: which directory a record lands in, and the index's figures."""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import targets, tentative, viewers


def _manifest(name: str, asked: int) -> dict:
    return {"solve": {"name": name}, "seats": {"asked": asked, "shortfall": 0}}


def test_a_collection_record_is_labelled_by_its_solve_name() -> None:
    """The longest collection name wins, because `smooth` is a prefix of three others."""
    assert viewers.label_of(_manifest("targets_smooth_mean_angle_n300_20260919T000000Z", 300)) == (
        "smooth_mean_angle"
    )
    assert viewers.label_of(_manifest("targets_smooth_n800_20260919T000000Z", 800)) == "smooth"
    assert viewers.label_of(_manifest("targets_lime_n150_20260919T000000Z", 150)) == "lime"


def test_a_general_record_is_told_apart_by_size_only_off_the_recorded_one() -> None:
    at = tentative.RECORDED_SEATS
    assert viewers.label_of(_manifest(f"tentative_n{at}_20260919T000000Z", at)) == "general"
    assert viewers.label_of(_manifest("general_n2000_20260919T000000Z", 2000)) == "general_n2000"
    # A `targets_` name the table does not hold is not a collection.
    assert viewers.label_of(_manifest("targets_general_n2000_x", 2000)) == "general_n2000"


def test_the_target_is_the_tables_for_a_collection_and_the_ask_otherwise() -> None:
    assert viewers.target_of("lime", _manifest("x", 999)) == targets.seats_for("lime")
    assert viewers.target_of("general_n2000", _manifest("x", 2000)) == 2000


def test_quartiles() -> None:
    assert viewers.quartiles([]) == (None, None)
    assert viewers.quartiles([0.4]) == (0.4, 0.4)
    assert viewers.quartiles([0.0, 0.1, 0.2, 0.3, 0.4]) == pytest.approx((0.2, 0.1))


def test_two_records_under_one_label_are_refused_before_anything_is_written(monkeypatch) -> None:
    rows = [{"key": "a"}, {"key": "b"}]
    monkeypatch.setattr(tentative, "read_rows", lambda stamp: rows)
    monkeypatch.setattr(
        tentative, "read_manifest", lambda stamp: _manifest("targets_red_n400_x", 400)
    )
    written = []
    monkeypatch.setattr(tentative, "page", lambda *a, **k: written.append(a))
    with pytest.raises(viewers.ViewersRefused):
        viewers.build(["s1", "s2"], fine={"a": 0.5})
    assert written == []


def test_no_stamp_named_builds_the_whole_keep_list(monkeypatch, tmp_path) -> None:
    names = {"s1": "final139_red", "s2": "final139_general"}
    monkeypatch.setattr(tentative, "kept", lambda: ["s1", "s2"])
    monkeypatch.setattr(tentative, "read_rows", lambda stamp: [{"key": "a"}])
    monkeypatch.setattr(
        tentative,
        "read_manifest",
        lambda stamp: _manifest(names[stamp], tentative.RECORDED_SEATS),
    )
    monkeypatch.setattr(tentative, "viewer_dir", lambda: tmp_path)
    written = []
    monkeypatch.setattr(tentative, "page", lambda stamp, **_: written.append(stamp))
    viewers.build(fine={"a": 0.5}, log=lambda *_: None)
    assert written == ["s1", "s2"]
    index = (tmp_path / viewers.INDEX_NAME).read_text(encoding="utf-8")
    assert 'href="red/index.html"' in index and 'href="general/index.html"' in index


def test_no_stamp_and_an_empty_keep_list_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(tentative, "kept", lambda: [])
    with pytest.raises(viewers.ViewersRefused):
        viewers.build(fine={})


def test_the_index_reads_only_the_seats_the_head_has_read() -> None:
    rows = [{"key": "a"}, {"key": "b"}, {"key": "c"}]
    fine = {"a": 0.2, "b": 0.6}
    held = [fine[row["key"]] for row in rows if row["key"] in fine]
    assert viewers.quartiles(held)[0] == pytest.approx(0.4)
    page = viewers._index(
        [
            {
                "label": "red",
                "stamp": "s",
                "solve": "targets_red_n400_x",
                "seats": 398,
                "target": 400,
                "shortfall": 2,
                "p_fine_median": 0.4,
                "p_fine_q1": None,
                "unread": 1,
            }
        ]
    )
    assert 'href="red/index.html"' in page
    assert "398 / 400" in page and "mono warn" in page
