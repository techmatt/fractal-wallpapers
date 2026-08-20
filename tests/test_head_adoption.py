"""Adopting a head: the volume match, the refusals around it, and the flip's record.

Nothing here loads a head or reads a picture. What is under test is the
arithmetic that decides where a cut lands, the two windows the measurement is
only valid inside, and the tracked records the flip leaves behind — all of which
are readable off files and lists.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import floors
from fractal_wallpapers.models import adoption
from fractal_wallpapers.supply import currency


# --------------------------------------------------------------------------- #
# The rule.
# --------------------------------------------------------------------------- #
def test_the_restated_cut_passes_the_count_the_prior_passed() -> None:
    """The whole method: same count of the same pool, on the other head's scale."""
    incumbent = [0.9, 0.8, 0.7, 0.3, 0.1]
    candidate = [0.44, 0.42, 0.40, 0.20, 0.02]
    match = adoption.matched(0.5, incumbent, candidate)
    assert match["incumbent_passing"] == 3
    assert match["crossing"] == 0.40
    assert match["value"] == 0.40
    assert match["realized_passing"] == 3


def test_the_rounding_goes_down_so_a_restatement_removes_no_more_than_its_prior() -> None:
    """A floor rounded up removes supply the cut it restates did not remove.

    The opposite direction from the strange head's release bar, and the same
    rule underneath: round away from the change nobody measured.
    """
    match = adoption.matched(0.5, [0.9, 0.8, 0.1], [0.6031, 0.5044, 0.02])
    assert match["crossing"] == 0.5044
    assert match["value"] == 0.500
    assert match["value"] <= match["crossing"]
    assert match["realized_passing"] >= match["incumbent_passing"]


def test_a_cut_nothing_passes_and_a_cut_everything_passes_are_both_answerable() -> None:
    """Degenerate pools are not a crash and not a silent zero."""
    empty = adoption.matched(0.99, [0.1, 0.2], [0.3, 0.4])
    assert empty["incumbent_passing"] == 0
    assert empty["realized_passing"] == 0
    whole = adoption.matched(0.0, [0.1, 0.2], [0.3, 0.4])
    assert whole["incumbent_passing"] == 2
    assert whole["realized_passing"] == 2


# --------------------------------------------------------------------------- #
# The two windows.
# --------------------------------------------------------------------------- #
def test_restating_after_the_flip_refuses(monkeypatch) -> None:
    """The pool holds the candidate's reads by then; there is no prior left."""
    staged = adoption.candidate_record()
    monkeypatch.setattr(adoption.cuts, "live_stamp", lambda head: staged["sha256"])
    with pytest.raises(adoption.AdoptionError, match="already the shipped"):
        adoption.restate()


def test_restating_after_the_values_are_typed_in_refuses(monkeypatch) -> None:
    """The refusal that had to be found, and the reason it is a refusal.

    The natural order of a flip — measure, type the heights in, ship — leaves a
    window where the code carries the new numbers and the artifact has not moved.
    A restatement taken there matches the new heights against themselves, reports
    a tidy volume match, and means nothing. Every number it produces looks
    exactly like a number that was measured, so it cannot be left to a reader.

    Standing in that window means pretending some other head is live while the
    modules still declare the heights of the one that is.
    """
    monkeypatch.setattr(adoption.cuts, "live_stamp", lambda head: "a head that is not shipped")
    with pytest.raises(adoption.AdoptionError, match="already declared against"):
        adoption.restate()


def test_the_declared_cuts_are_the_ones_the_owning_modules_hold() -> None:
    """Read off the owners, never restated here — three names, two modules."""
    declared = adoption.declared_cuts()
    assert declared["junk floor"] is floors.JUNK_FLOOR_RESTATED
    assert declared["good floor"] is currency.GOOD_FLOOR_RESTATED
    assert declared["great cut"] is currency.GREAT_CUT_RESTATED


# --------------------------------------------------------------------------- #
# The records the flip left.
# --------------------------------------------------------------------------- #
def test_the_restatement_prices_the_artifact_that_serves() -> None:
    """A restatement of a file nobody ships is a measurement of nothing."""
    priced = adoption.restatement()
    assert priced["candidate"]["sha256"] == floors.live_stamp("location")
    assert priced["incumbent"]["sha256"] != priced["candidate"]["sha256"]
    assert priced["reference_pool"]["scored_by"] == priced["incumbent"]["sha256"], (
        "the pool has to be the retired head's own read of the standing supply"
    )


def test_every_declared_height_is_the_one_the_restatement_measured() -> None:
    """The code and the record must not be able to hold two different numbers."""
    priced = adoption.restatement()
    for name, declared in adoption.declared_cuts().items():
        measured = priced["cuts"][name]
        assert declared.value == measured["value"]
        assert declared.head_sha256 == priced["candidate"]["sha256"]
        assert measured["realized_passing"] >= measured["incumbent_passing"]


def test_the_adoption_record_carries_both_reads_with_their_verdicts() -> None:
    """They did not agree, and a record listing two paths would read as passed both."""
    record = json.loads(adoption.adoption_path().read_text(encoding="utf-8"))
    verdicts = {read["record"]: read["verdict"] for read in record["judged_by"]}
    assert verdicts["models/location/regime_acceptance.json"] == "FAIL"
    assert verdicts["models/location/flip_acceptance.json"] == "PASS"
    assert record["flipped"]["serving"]["sha256"] == floors.live_stamp("location")
    assert record["flipped"]["retired"]["sha256"] != record["flipped"]["serving"]["sha256"]


def test_the_adopted_candidate_is_recorded_as_adopted_and_is_not_a_second_file() -> None:
    """Two copies of the shipped head under two names is how the wrong one serves."""
    from fractal_wallpapers.models import ship

    record = json.loads(ship.candidate_record_path("location").read_text(encoding="utf-8"))
    assert record["adopted"] is True
    assert record["sha256"] == floors.live_stamp("location")
    assert not ship.candidate_path("location").exists()
