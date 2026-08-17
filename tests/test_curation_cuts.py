"""The cut owner: which numbers act, which only annotate, and what a stamp is for."""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import floors
from fractal_wallpapers.supply import currency


def test_the_good_floor_is_the_supply_engines_and_is_not_restated() -> None:
    """One number under one name. A second copy is the failure this module ends."""
    assert floors.GOOD_FLOOR is currency.GOOD_FLOOR


def test_the_junk_floor_is_below_the_good_floor() -> None:
    """Two heights on one scale: don't spend compute on it, and worth keeping."""
    assert 0.0 < floors.JUNK_FLOOR < floors.GOOD_FLOOR


def test_an_unscored_candidate_passes_neither_floor() -> None:
    """No verdict to be kept on, and none to spend compute on either."""
    assert floors.passes_junk_floor(None) is False
    assert floors.passes_good_floor(None) is False
    assert floors.passes_junk_floor(floors.JUNK_FLOOR) is True
    assert floors.passes_good_floor(floors.JUNK_FLOOR) is False


def test_the_thin_supply_cap_is_the_zero() -> None:
    """A partition with three floor-passing candidates ships nothing, not its
    own least-bad row."""
    assert floors.emit_cap(3) == 0
    assert floors.emit_cap(4) == 1
    assert floors.emit_cap(31) == 7


def test_an_advisory_refuses_to_annotate_against_a_head_it_was_not_set_against(
    tmp_path, monkeypatch
) -> None:
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    advisory = floors.Advisory("h_release", 0.5, "h", "abc", "for a test")
    assert advisory.annotates(0.9) is True

    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "def"}}}))
    with pytest.raises(floors.HeadStampMismatch):
        advisory.annotates(0.9)


def test_an_advisory_is_tri_state_so_a_crash_is_not_a_bad_wallpaper(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    advisory = floors.Advisory("h_release", 0.5, "h", "abc", "for a test")
    assert advisory.annotates(None) is None
    assert advisory.annotates(0.1) is False


def test_an_advisory_cannot_remove_a_row() -> None:
    """There is no gate() here, no seats() and no acts flag beside it, deliberately.

    A head whose cut acts gets a Bar, which is a different class with a different
    method, so the difference is visible at the call site and not hidden in a
    boolean somebody can set.
    """
    assert not hasattr(floors.Advisory, "gate")
    assert not hasattr(floors.Advisory, "seats")
    assert "acts" not in floors.Advisory.__dataclass_fields__


def test_an_unshipped_head_has_no_scale_for_a_cut_to_live_on(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    with pytest.raises(floors.HeadStampMismatch):
        floors.live_stamp("location")


def test_the_summary_says_which_cuts_act() -> None:
    summary = floors.summary()
    assert set(summary["acting"]) == {
        "junk_floor",
        "good_floor",
        *(f"{head}_release_bar" for head in floors.ACTING_RELEASE_BARS),
    }
    assert summary["advisory"]


def test_the_one_acting_release_bar_is_the_strange_head_and_it_is_a_real_head() -> None:
    """A misspelled head here is a bar that silently gates nothing at all."""
    from fractal_wallpapers.curation import budget

    assert set(floors.ACTING_RELEASE_BARS) == {budget.STRANGE}
    assert set(floors.ACTING_RELEASE_BARS) < set(budget.HEADS)
    assert floors.ACTING_RELEASE_BARS[budget.STRANGE] == floors.STRANGE_RELEASE_BAR


def test_the_smooth_head_still_only_annotates() -> None:
    """Its below-advisory rows belong to a mix-ratio decision nobody has taken."""
    from fractal_wallpapers.curation import budget

    assert floors.release_bar(budget.SMOOTH) is None
    assert isinstance(floors.release_cut(budget.SMOOTH), floors.Advisory)


def test_the_strange_head_gets_a_bar_and_refuses_to_pose_as_an_advisory() -> None:
    from fractal_wallpapers.curation import budget

    cut = floors.release_cut(budget.STRANGE)
    assert isinstance(cut, floors.Bar)
    assert cut.value == floors.STRANGE_RELEASE_BAR
    with pytest.raises(ValueError, match="ACTS"):
        floors.release_advisory(budget.STRANGE)


def test_a_bar_seats_nothing_without_a_score_while_the_record_keeps_the_third_state(
    tmp_path, monkeypatch
) -> None:
    """The comparison stays tri-state; the seating decision cannot have one."""
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    bar = floors.Bar("h_release", 0.5, "h", "abc", "for a test")
    assert bar.clears(None) is None
    assert bar.seats(None) is False
    assert bar.seats(0.4999) is False
    assert bar.seats(0.5) is True


def test_a_bar_refuses_to_seat_against_a_head_it_was_not_set_against(tmp_path, monkeypatch) -> None:
    """A bar is a point on one head's scale, and it says nothing on another's."""
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    bar = floors.Bar("h_release", 0.5, "h", "abc", "for a test")
    assert bar.seats(0.9) is True

    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "def"}}}))
    with pytest.raises(floors.HeadStampMismatch):
        bar.seats(0.9)
