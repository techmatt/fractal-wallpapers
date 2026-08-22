"""`--finish-by`: turning a time somebody named into the harvest's active minutes.

Every number the derivation subtracts is a measured leg, so the tests here are
about the *arithmetic and the refusals* rather than about the constants — a
constant that moves because a leg was re-measured must not fail a test, and a
derivation that stops naming its terms must.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from fractal_wallpapers import schedule

EVENING = datetime(2026, 8, 22, 23, 0)


def test_a_finish_time_already_past_today_means_tomorrow() -> None:
    """The only reading that makes `--finish-by 07:00` mean what it says at eleven
    at night."""
    assert schedule.next_at("07:00", EVENING) == datetime(2026, 8, 23, 7, 0)
    assert schedule.next_at("23:30", EVENING) == datetime(2026, 8, 22, 23, 30)
    # Equality goes to tomorrow: a night that scheduled itself zero minutes would
    # report a plan rather than refuse one.
    assert schedule.next_at("23:00", EVENING) == datetime(2026, 8, 23, 23, 0)


@pytest.mark.parametrize("text", ["7", "0700", "25:00", "07:61", "seven", ""])
def test_a_finish_time_that_is_not_a_time_refuses(text: str) -> None:
    with pytest.raises(schedule.Unschedulable):
        schedule.next_at(text, EVENING)


def test_the_span_is_the_reservations_plus_the_harvest_and_nothing_else() -> None:
    """The arithmetic closes, which is the only property a reservation has."""
    plan = schedule.plan("07:00", 80, now=EVENING)
    assert plan.span == pytest.approx(8 * 3600)
    terms = (plan.release, plan.curation, plan.rescore, plan.ledger_load, plan.margin, plan.room)
    assert sum(terms) == pytest.approx(plan.span)
    assert plan.active_minutes == pytest.approx(plan.room / 60.0 / schedule.ACTIVE_TO_WALL)


def test_the_release_reservation_is_the_ceiling_times_the_measured_rate() -> None:
    """Sized on `-n` and not on what will be seated: `-n` is a cap and every run
    on record under-filled it, so this over-reserves whenever the release comes up
    short. An over-reserved release leg finishes early; an under-reserved one runs
    past the time somebody has to be awake for."""
    plan = schedule.plan("07:00", 80, now=EVENING)
    assert plan.release == pytest.approx(80 * schedule.RELEASE_SECONDS_PER_PICTURE)
    bigger = schedule.plan("07:00", 160, now=EVENING)
    assert bigger.release == pytest.approx(2 * plan.release)


def test_the_rest_of_curate_run_is_reserved_and_not_left_to_the_release_leg() -> None:
    """The colorize leg runs between the harvest and the release pass. A night that
    reserved the release alone would spend a quarter of an hour of the release's
    own reservation before the first full-resolution render started."""
    plan = schedule.plan("07:00", 80, now=EVENING)
    assert plan.curation == pytest.approx(
        80 * schedule.ATTEMPTS_PER_SLOT * schedule.CURATION_SECONDS_PER_ATTEMPT
    )
    assert plan.curation > 0
    assert plan.record()["release_attempts"] == 80 * schedule.ATTEMPTS_PER_SLOT


def test_the_attempt_multiple_here_is_the_one_curation_actually_uses() -> None:
    """Two spellings of one number is what `floors` exists to end. This module
    stays import-free of curation, so the coupling is pinned instead."""
    from fractal_wallpapers.curation import floors

    assert schedule.ATTEMPTS_PER_SLOT == floors.ATTEMPT_MULTIPLIER


def test_active_minutes_are_fewer_than_the_wall_they_came_from() -> None:
    """`--minutes` counts active time. A derivation that handed it wall minutes
    would over-book the clock by exactly the overhead the ratio exists to name."""
    plan = schedule.plan("07:00", 80, now=EVENING)
    assert plan.active_minutes < plan.room / 60.0
    assert schedule.ACTIVE_TO_WALL > 1.0


def test_a_span_the_reservations_do_not_fit_in_refuses_with_them_named() -> None:
    """A harvest handed four minutes is not a short harvest, it is a night nobody
    sized — and the reservations are the interesting half of the refusal."""
    with pytest.raises(schedule.Unschedulable) as refusal:
        schedule.plan("07:00", 80, now=datetime(2026, 8, 23, 6, 0))
    said = str(refusal.value)
    assert "release" in said and "margin" in said and "80 slots" in said


def test_the_record_carries_every_term_the_readout_has_to_subtract() -> None:
    """A night that lands late is attributable to the term that was reserved wrong
    only if the terms are on the record next to what they actually cost."""
    record = schedule.plan("07:00", 80, now=EVENING).record()
    assert set(record["reserved_minutes"]) == {
        "release",
        "curation",
        "closing_rescore",
        "ledger_load",
        "margin",
    }
    for field in ("started", "finish_by", "span_minutes", "harvest_active_minutes"):
        assert record[field] is not None
    # The rate and the worker count it was measured at travel together: the rate
    # means nothing without it and there is no measurement at any other.
    assert record["release_workers"] == schedule.RELEASE_WORKERS
    assert record["release_seconds_per_picture"] == schedule.RELEASE_SECONDS_PER_PICTURE


def test_the_printed_plan_states_the_derivation_rather_than_the_answer() -> None:
    lines = "\n".join(schedule.plan("07:00", 80, now=EVENING).lines())
    assert "07:00" in lines
    assert "ACTIVE" in lines
    assert str(schedule.ACTIVE_TO_WALL) in lines
