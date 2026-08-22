"""`--finish-by`: turning a time somebody named into the harvest's active minutes.

Every number the derivation subtracts is a measured leg, so the tests here are
about the *arithmetic and the refusals* rather than about the constants — a
constant that moves because a leg was re-measured must not fail a test, and a
derivation that stops naming its terms must.

Two of the terms are no longer constants at all: the release rate is read off the
most recent tracked run and the closing re-score scales with what the harvest will
find. Those get tests against a **run record fixture** rather than against the
tracked store, because the whole point of reading a record is that the answer
moves when the record does.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from fractal_wallpapers import schedule

EVENING = datetime(2026, 8, 22, 23, 0)

#: A release leg exactly as a run record carries one, at the rate run10 measured.
RUN10_RELEASE = {"rows": 55, "seconds": 1370.2, "workers": 4}


@pytest.fixture
def tracked_runs(tmp_path):
    """A record store holding whatever run records a test writes into it.

    Bound through `records.use`, which is the same redirect an ephemeral run
    takes, so nothing here can read or write the tracked store by accident.
    """
    from fractal_wallpapers.curation import records

    records.use(tmp_path)
    try:
        yield tmp_path / "runs"
    finally:
        records.use(None)


def write_run_record(directory, name: str, record: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


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
    plan = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"))
    assert plan.span == pytest.approx(8 * 3600)
    terms = (plan.release, plan.curation, plan.rescore, plan.ledger_load, plan.margin, plan.room)
    assert sum(terms) == pytest.approx(plan.span)
    assert plan.active_minutes == pytest.approx(plan.room / 60.0 / plan.ratio)


def test_the_release_reservation_is_the_ceiling_times_the_measured_rate() -> None:
    """Sized on `-n` and not on what will be seated: `-n` is a cap and every run
    on record under-filled it, so this over-reserves whenever the release comes up
    short. An over-reserved release leg finishes early; an under-reserved one runs
    past the time somebody has to be awake for."""
    plan = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"))
    assert plan.release == pytest.approx(80 * 24.9)
    bigger = schedule.plan("07:00", 160, now=EVENING, rate=(24.9, "a fixture"))
    assert bigger.release == pytest.approx(2 * plan.release)


def test_the_release_rate_is_read_off_the_most_recent_tracked_run(tracked_runs) -> None:
    """The term that moved most, and for a reason no constant could carry: run9
    measured 41.9 s a picture with `artifacts/curation` on the archive and run10
    measured 24.9 with it on NVMe, same code and same geometry."""
    write_run_record(
        tracked_runs, "older", {"run": "older", "finished": "2026-08-01T00:00:00", "release": {}}
    )
    write_run_record(
        tracked_runs,
        "newer",
        {"run": "newer", "finished": "2026-08-21T23:00:00", "release": RUN10_RELEASE},
    )
    rate, source = schedule.release_rate(4)
    assert rate == pytest.approx(1370.2 / 55)
    assert "newer" in source
    # A run that stopped before its release leg measured nothing, and skipping it
    # is not the same as having no measurement.
    assert "older" not in source


def test_a_run_that_never_released_is_skipped_rather_than_believed(tracked_runs) -> None:
    write_run_record(
        tracked_runs,
        "released",
        {"run": "released", "finished": "2026-08-01T00:00:00", "release": RUN10_RELEASE},
    )
    write_run_record(
        tracked_runs,
        "stopped",
        {
            "run": "stopped",
            "finished": "2026-08-21T23:00:00",
            "release": {"rows": 0, "seconds": 0.0, "workers": 4},
        },
    )
    rate, source = schedule.release_rate(4)
    assert rate == pytest.approx(1370.2 / 55)
    assert "released" in source


def test_with_no_release_on_record_the_written_down_rate_says_so(tracked_runs) -> None:
    """A fresh clone has no measurement, and the plan has to say which of the two
    it reserved off — a night reserved on the fallback is a different night."""
    rate, source = schedule.release_rate(schedule.RELEASE_WORKERS)
    assert rate == pytest.approx(schedule.RELEASE_SECONDS_PER_PICTURE)
    assert "no tracked run" in source


def test_the_rate_is_scaled_to_the_worker_count_this_night_will_run(tracked_runs) -> None:
    """A straight inverse, which is the only rule the record supports — and the
    reason the plan prints the count rather than implying it."""
    write_run_record(
        tracked_runs,
        "run",
        {"run": "run", "finished": "2026-08-21T23:00:00", "release": RUN10_RELEASE},
    )
    at_four, _ = schedule.release_rate(4)
    at_eight, _ = schedule.release_rate(8)
    assert at_eight == pytest.approx(at_four / 2)


def test_the_rest_of_curate_run_is_reserved_and_not_left_to_the_release_leg() -> None:
    """The colorize leg runs between the harvest and the release pass. A night that
    reserved the release alone would spend a quarter of an hour of the release's
    own reservation before the first full-resolution render started."""
    plan = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"))
    assert plan.curation == pytest.approx(plan.attempts * schedule.CURATION_SECONDS_PER_ATTEMPT)
    assert plan.curation > 0
    assert plan.record()["release_attempts"] == plan.attempts


def test_the_strange_head_costs_two_attempts_a_location_and_the_reservation_knows() -> None:
    """The attempt count stopped being `4n` the day the strange judge started
    drawing two modes a location, and a term that had not noticed would under-
    reserve the colorize leg by a quarter of an hour on an eighty-slot night."""
    # 40 smooth slots x 4 locations x 1 mode + 40 strange x 4 x 2 = 480.
    assert schedule.release_attempts(80, 0.5) == 480
    # A release with no strange share in it is the old arithmetic exactly.
    assert schedule.release_attempts(80, 0.0) == 80 * schedule.LOCATIONS_PER_SLOT
    assert schedule.release_attempts(80, 1.0) == 80 * schedule.LOCATIONS_PER_SLOT * 2


def test_the_attempt_multiple_here_is_the_one_curation_actually_uses() -> None:
    """Two spellings of one number is what `floors` exists to end. This module
    stays import-free of curation, so the coupling is pinned instead."""
    from fractal_wallpapers.curation import budget, floors
    from fractal_wallpapers.curation import run as run_module

    assert schedule.LOCATIONS_PER_SLOT == floors.ATTEMPT_MULTIPLIER
    assert budget.MODES_PER_LOCATION[budget.STRANGE] == schedule.MODES_PER_STRANGE_LOCATION
    assert budget.MODES_PER_LOCATION[budget.SMOOTH] == 1
    assert schedule.STRANGE_SHARE == run_module.STRANGE_SHARE


def test_the_split_between_the_heads_is_the_one_the_budget_spends() -> None:
    """A reservation sized against a different split than the selection spends is
    exactly a short-fill nobody can attribute."""
    from fractal_wallpapers.curation import budget

    for n in (0, 1, 7, 80, 81):
        slots = budget.head_slots(n, schedule.STRANGE_SHARE)
        wanted, _ = budget.head_attempts(slots, None)
        assert schedule.release_attempts(n) == sum(wanted.values())


def test_active_minutes_are_fewer_than_the_wall_they_came_from() -> None:
    """`--minutes` counts active time. A derivation that handed it wall minutes
    would over-book the clock by exactly the overhead the ratio exists to name."""
    plan = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"))
    assert plan.active_minutes < plan.room / 60.0
    assert plan.ratio > 1.0


def test_the_ratio_is_chosen_by_whether_the_night_draws_its_own_views() -> None:
    """run10 spent 1.3 wall minutes per 100 active and was reserved at 13, which
    cost that harvest 36 minutes of walking. The two numbers were measured on two
    different arrangements, so the fix is a condition rather than a lower number."""
    drawing, why_drawing = schedule.active_to_wall(True)
    gate, why_gate = schedule.active_to_wall(False)
    assert drawing == schedule.ACTIVE_TO_WALL_DRAWING_VIEWS
    assert gate == schedule.ACTIVE_TO_WALL_SCORING_GATE_RENDERS
    assert gate < drawing
    assert why_drawing != why_gate

    cheap = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"))
    dear = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "a fixture"), renders_views=True)
    assert cheap.active_minutes > dear.active_minutes
    assert cheap.record()["active_to_wall_basis"] == why_gate
    assert dear.record()["active_to_wall_basis"] == why_drawing


def test_the_closing_rescore_scales_with_what_the_harvest_will_find() -> None:
    """It re-reads the run's own gate survivors, so a fixed tail keeps drifting as
    the nights get longer: run10 reserved 2 minutes and spent 4.7."""
    short = schedule.plan("01:00", 4, now=EVENING, rate=(24.9, "a fixture"))
    long = schedule.plan("07:00", 4, now=EVENING, rate=(24.9, "a fixture"))
    assert long.rescore > short.rescore
    assert long.rescore / long.active_minutes == pytest.approx(short.rescore / short.active_minutes)
    # And it is solved for rather than iterated to: the terms still close.
    terms = (long.release, long.curation, long.rescore, long.ledger_load, long.margin, long.room)
    assert sum(terms) == pytest.approx(long.span)


def test_a_span_the_reservations_do_not_fit_in_refuses_with_them_named() -> None:
    """A harvest handed four minutes is not a short harvest, it is a night nobody
    sized — and the reservations are the interesting half of the refusal."""
    with pytest.raises(schedule.Unschedulable) as refusal:
        schedule.plan("07:00", 80, now=datetime(2026, 8, 23, 6, 0), rate=(24.9, "a fixture"))
    said = str(refusal.value)
    assert "release" in said and "margin" in said and "80 slots" in said


def test_the_record_carries_every_term_the_readout_has_to_subtract() -> None:
    """A night that lands late is attributable to the term that was reserved wrong
    only if the terms are on the record next to what they actually cost."""
    record = schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "the fixture")).record()
    assert set(record["reserved_minutes"]) == {
        "release",
        "curation",
        "closing_rescore",
        "ledger_load",
        "margin",
    }
    for field in ("started", "finish_by", "span_minutes", "harvest_active_minutes"):
        assert record[field] is not None
    # The rate, the worker count it was measured at, and where it was read: the
    # rate means nothing without the first, and a readout months later cannot tell
    # a measured night from a fallback night without the second.
    assert record["release_workers"] == schedule.RELEASE_WORKERS
    assert record["release_seconds_per_picture"] == pytest.approx(24.9)
    assert record["release_rate_source"] == "the fixture"
    assert record["active_to_wall"] == schedule.ACTIVE_TO_WALL_SCORING_GATE_RENDERS


def test_the_printed_plan_states_the_derivation_rather_than_the_answer() -> None:
    lines = "\n".join(
        schedule.plan("07:00", 80, now=EVENING, rate=(24.9, "run9's own leg")).lines()
    )
    assert "07:00" in lines
    assert "ACTIVE" in lines
    assert str(schedule.ACTIVE_TO_WALL_SCORING_GATE_RENDERS) in lines
    assert "run9's own leg" in lines
    assert "480 attempts" in lines


def test_run10s_own_night_re_derived_under_the_terms_that_replaced_its_own(
    tracked_runs,
) -> None:
    """The whole point of the four terms moving, in one arithmetic.

    run10 launched at 23:18:58 against an 07:00 finish-by and was handed 317.22
    active minutes. It finished at 05:36 — 84 minutes early — because four of the
    five reservations were wrong in the same direction: the release rate had
    halved, the ledger load was three directory walks, the ratio was measured on
    a night that drew views, and the re-score was a fixed tail on a supply that
    had doubled. Re-derived off run10's own record, the same night buys 375.
    """
    write_run_record(
        tracked_runs,
        "run10",
        {"run": "run10", "finished": "2026-08-22T05:36:04", "release": RUN10_RELEASE},
    )
    launch = datetime(2026, 8, 21, 23, 18, 58)
    plan = schedule.plan("07:00", 80, now=launch)

    assert plan.record()["release_seconds_per_picture"] == pytest.approx(24.91, abs=0.01)
    assert "run10" in plan.release_rate_source
    assert plan.active_minutes == pytest.approx(374.8, abs=0.5)
    # 317.22 was what the night was actually given.
    assert plan.active_minutes - 317.22 > 55, "the reservation gave back nearly an hour"
    # And the extra attempts the second strange mode costs are in the reservation
    # rather than eaten out of the release leg's own clock.
    assert plan.attempts == 480


def test_a_record_with_no_finish_stamp_is_older_than_every_stamped_one(tracked_runs) -> None:
    """The stamp started being written at a known moment, so its absence *is* a
    statement about age. Without that rule a fresh clone — where every file's mtime
    is the checkout — would derive tonight's reservation off whichever run the
    file system happened to touch last."""
    write_run_record(
        tracked_runs, "ancient", {"run": "ancient", "release": {**RUN10_RELEASE, "seconds": 4000.0}}
    )
    write_run_record(
        tracked_runs,
        "recent",
        {"run": "recent", "finished": "2026-01-01T00:00:00", "release": RUN10_RELEASE},
    )
    # `ancient` is the newer file on disk and the older run on the record.
    rate, source = schedule.release_rate(4)
    assert "recent" in source
    assert rate == pytest.approx(1370.2 / 55)
