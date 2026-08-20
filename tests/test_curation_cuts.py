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
    """There is no gate() here and no acts() beside it, deliberately.

    A head whose cut acts gets a Bar, which is a different class with a different
    method, so the difference is visible at the call site and not hidden in a
    boolean somebody can set.
    """
    assert not hasattr(floors.Advisory, "gate")
    assert not hasattr(floors.Advisory, "acts")
    assert "acts" in dir(floors.Bar)


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
        "great_cut",
        *(f"{head}_release_bar" for head in floors.ACTING_RELEASE_BARS),
    }
    assert summary["advisory"]


def test_the_one_acting_release_bar_is_the_strange_head_and_it_is_a_real_head() -> None:
    """A misspelled head here is a bar that silently gates nothing at all."""
    from fractal_wallpapers.curation import budget

    assert set(floors.ACTING_RELEASE_BARS) == {budget.STRANGE}
    assert set(floors.ACTING_RELEASE_BARS) < set(budget.HEADS)
    assert floors.ACTING_RELEASE_BARS[budget.STRANGE] is floors.STRANGE_RELEASE_BAR


def test_the_smooth_head_still_only_annotates() -> None:
    """Its below-advisory rows belong to a mix-ratio decision nobody has taken."""
    from fractal_wallpapers.curation import budget

    assert floors.release_bar(budget.SMOOTH) is None
    assert isinstance(floors.release_cut(budget.SMOOTH), floors.Advisory)


def test_the_strange_head_gets_a_bar_and_refuses_to_pose_as_an_advisory() -> None:
    from fractal_wallpapers.curation import budget

    cut = floors.release_cut(budget.STRANGE)
    assert isinstance(cut, floors.Bar)
    assert cut.value == floors.STRANGE_RELEASE_BAR.value
    with pytest.raises(ValueError, match="ACTS"):
        floors.release_advisory(budget.STRANGE)


def test_the_acting_bar_is_stamped_with_the_head_its_height_was_measured_on() -> None:
    """The half of the stamp that is different for a bar.

    An advisory is the natural cutpoint of whatever scale is live, so it stamps
    the live artifact. A bar's height was *measured*, on one named head, and it
    stamps that one — which is what makes a flip refuse from the first call rather
    than only when a re-ship lands in the middle of a run.
    """
    from fractal_wallpapers.curation import budget

    cut = floors.release_cut(budget.STRANGE)
    assert cut.stamp == floors.STRANGE_RELEASE_BAR.head_sha256
    assert cut.stamp == floors.live_stamp(budget.STRANGE), (
        "the shipped head is not the one this bar was restated against — restate it"
    )


def test_a_restated_bar_carries_the_scale_the_method_and_the_day() -> None:
    """A bare float is unreadable: 0.50 and 0.685 are the same kind of thing only
    if you already know which head's probabilities each was read against."""
    restated = floors.STRANGE_RELEASE_BAR
    assert 0.0 < restated.value < 1.0
    assert len(restated.head_sha256) == 64
    assert "isotonic" in restated.method.lower()
    assert restated.reference_pool
    assert restated.date.count("-") == 2
    assert str(restated).startswith(f"{restated.value:g} on {restated.head_sha256[:12]}")


def test_a_head_flip_refuses_every_seating_decision_until_the_bar_is_restated(
    tmp_path, monkeypatch
) -> None:
    """The failure this restatement exists to make impossible.

    A retrain moves the whole probability scale, so yesterday's height is a point
    on a scale that no longer exists. The bar does not silently keep gating: it
    refuses, and the refusal names both artifacts.
    """
    from fractal_wallpapers.curation import budget
    from fractal_wallpapers.models import ship

    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {budget.STRANGE: {"sha256": "def"}}}))
    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    with pytest.raises(floors.HeadStampMismatch, match="re-state the cut"):
        floors.release_cut(budget.STRANGE).acts(0.99)


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
    assert bar.acts(None) is False
    assert bar.acts(0.4999) is False
    assert bar.acts(0.5) is True


def test_a_bar_refuses_to_seat_against_a_head_it_was_not_set_against(tmp_path, monkeypatch) -> None:
    """A bar is a point on one head's scale, and it says nothing on another's."""
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "abc"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    bar = floors.Bar("h_release", 0.5, "h", "abc", "for a test")
    assert bar.acts(0.9) is True

    manifest.write_text(json.dumps({"schema": 1, "heads": {"h": {"sha256": "def"}}}))
    with pytest.raises(floors.HeadStampMismatch):
        bar.acts(0.9)


# --------------------------------------------------------------------------- #
# The three cuts on the location head's scale.
# --------------------------------------------------------------------------- #
def test_every_location_cut_is_a_restatement_against_the_head_that_serves() -> None:
    """The check that would have caught the flip, taken as an assertion.

    Three cuts sit on this head's probability scale and they are owned by two
    modules. All three must name the artifact that is shipped right now, or the
    supply engine is deciding against a scale nobody restated — and the failure
    is silent, because the comparison still returns a bool.
    """
    live = floors.live_stamp("location")
    for name, restated in (
        ("junk floor", floors.JUNK_FLOOR_RESTATED),
        ("good floor", currency.GOOD_FLOOR_RESTATED),
        ("great cut", currency.GREAT_CUT_RESTATED),
    ):
        assert restated.head_sha256 == live, f"the {name} was restated against another head"
        assert restated.reference_pool, f"the {name} names no population"
        assert restated.method, f"the {name} says nothing about how it was read"


def test_the_three_location_cuts_were_read_over_one_pool() -> None:
    """Three volume matches over three populations would be three claims."""
    pools = {
        floors.JUNK_FLOOR_RESTATED.reference_pool,
        currency.GOOD_FLOOR_RESTATED.reference_pool,
        currency.GREAT_CUT_RESTATED.reference_pool,
    }
    assert len(pools) == 1
    assert floors.LOCATION_POOL == currency.REFERENCE_POOL


def test_the_junk_floor_refuses_after_a_location_flip(tmp_path, monkeypatch) -> None:
    """The whole point of stamping the junk floor, which used to be a bare float.

    It was described for most of a year as the one cut a head flip could leave
    alone. A flip moves the *volume* it removes even where the sentence it stands
    for is unchanged, so it refuses like every other acting cut.
    """
    manifest = tmp_path / "weights.json"
    manifest.write_text(json.dumps({"schema": 1, "heads": {"location": {"sha256": "def"}}}))
    from fractal_wallpapers.models import ship

    monkeypatch.setattr(ship, "manifest_path", lambda: manifest)
    with pytest.raises(floors.HeadStampMismatch, match="re-state the cut"):
        floors.passes_junk_floor(0.9)
    with pytest.raises(floors.HeadStampMismatch, match="re-state the cut"):
        currency.passes_good_floor(0.9)
    with pytest.raises(floors.HeadStampMismatch, match="re-state the cut"):
        currency.good_class(0.9, 0.9)


def test_the_great_cut_no_longer_has_to_sit_above_the_good_floor() -> None:
    """Volume-matched independently, the two stopped being nested — say so.

    They were both 0.50 on an ordinal head, so clearing the great cut implied
    clearing the good floor and a class 4 was exactly the great-cut count. After
    the 2026-08-20 restatement the great cut sits below the good floor, and 200
    of the sidecar's rows clear one without the other. `good_class` reads the
    floor first, so the currency is unaffected — but a reader who assumed the
    nesting would count class 4s wrong.
    """
    assert currency.GREAT_CUT < currency.GOOD_FLOOR
    assert currency.good_class(0.30, 0.20) is None, "the floor decides first, always"
    assert currency.good_class(0.40, 0.20) == 4
    assert currency.good_class(0.40, 0.05) == 3
