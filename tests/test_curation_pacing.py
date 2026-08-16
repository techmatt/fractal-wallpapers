"""The wall-clock backstop: a gate that refuses to start, and a deadline that kills."""

from __future__ import annotations

import subprocess

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import pacing


class Ticker:
    """A clock a test moves by hand. Real time makes a budget test a flake."""

    def __init__(self, at: float = 0.0):
        self.at = float(at)

    def __call__(self) -> float:
        return self.at


def clock(budget=None, at=0.0, margins=None, minimums=None) -> tuple[pacing.Clock, Ticker]:
    ticker = Ticker(at)
    return pacing.Clock(budget, margins=margins, minimums=minimums, now=ticker), ticker


def test_the_gate_declines_before_the_overrun_rather_than_reporting_it() -> None:
    """A budget checked after a unit finishes does not prevent anything."""
    paced, ticker = clock(budget=140.0, margins={pacing.COLORIZE: 30.0})
    leg = paced.leg(pacing.COLORIZE)
    leg.observe(10.0)

    ticker.at = 100.0  # 100 spent + 10 estimated + 30 reserved = exactly the budget
    assert leg.may_start() is None
    ticker.at = 100.1
    decline = leg.may_start()
    assert decline is not None
    assert "estimated at 10s" in decline.reason
    assert paced.stopped()


def test_an_unbudgeted_run_starts_everything() -> None:
    paced, ticker = clock(budget=None, at=9_000.0)
    assert paced.leg(pacing.RELEASE).may_start() is None
    assert paced.remaining() == float("inf")
    assert not paced.stopped()


def test_the_estimate_is_this_run_s_longest_finished_unit() -> None:
    """The longest and not the mean: one row can cost twelve times the median
    because it is twelve times as deep, and the gate's job is to not overrun."""
    paced, _ = clock(budget=1000.0)
    leg = paced.leg(pacing.RELEASE)
    assert leg.estimate() is None
    for seconds in (16.0, 196.0, 20.0):
        leg.observe(seconds)
    assert leg.estimate() == 196.0


def test_a_failed_or_killed_unit_teaches_the_estimate_nothing() -> None:
    """A row that failed in a tenth of a second would drag the gate down to
    nothing; a row killed at its deadline measures the deadline, not the work."""
    paced, _ = clock(budget=1000.0)
    leg = paced.leg(pacing.RELEASE)
    leg.observe(120.0)
    leg.observe(0.1, ok=False)
    leg.observe(300.0, ok=True, expired=True)
    assert leg.estimate() == 120.0
    assert leg.killed == 1


def test_a_class_with_nothing_measured_needs_room_worth_spending() -> None:
    """It may start — that is the only way to get an estimate — but not on the
    last few seconds of a budget it has no reason to believe it can finish in."""
    paced, ticker = clock(budget=600.0, margins={pacing.RELEASE: 20.0})
    leg = paced.leg(pacing.RELEASE)
    assert leg.may_start() is None

    ticker.at = 600.0 - 20.0 - pacing.UNMEASURED_MINIMUM[pacing.RELEASE] + 0.1
    decline = leg.may_start()
    assert decline is not None
    assert decline.estimate is None
    assert "never measured" in decline.reason


def test_the_room_an_unmeasured_class_needs_is_its_own_and_not_the_other_leg_s() -> None:
    """One number for both legs is either most of a colorize budget or a rounding
    error on a release: the two differ by two orders of magnitude."""
    paced, ticker = clock(budget=200.0)
    ticker.at = 100.0
    assert paced.leg(pacing.COLORIZE).may_start() is None
    assert paced.leg(pacing.RELEASE).may_start() is None

    ticker.at = 145.0  # 55s left: enough for an unmeasured colorize, not for a render
    assert paced.leg(pacing.COLORIZE).may_start() is None
    assert paced.leg(pacing.RELEASE).may_start() is not None


def test_the_first_unit_of_a_class_is_bounded_by_what_the_budget_has_left() -> None:
    """The one hole a prospective gate cannot close by itself."""
    paced, ticker = clock(budget=600.0, margins={pacing.RELEASE: 20.0})
    leg = paced.leg(pacing.RELEASE)
    ticker.at = 100.0
    assert leg.timeout() == pytest.approx(480.0)

    unbudgeted, _ = clock(budget=None)
    assert unbudgeted.leg(pacing.RELEASE).timeout() == pacing.UNMEASURED_CEILING


def test_a_measured_unit_is_killed_at_a_multiple_of_the_class_s_own_cost() -> None:
    paced, ticker = clock(budget=10_000.0, margins={pacing.RELEASE: 20.0})
    leg = paced.leg(pacing.RELEASE)
    leg.observe(200.0)
    assert leg.timeout() == pytest.approx(pacing.HUNG_MULTIPLE * 200.0)

    leg.seen.clear()
    leg.observe(0.5)
    assert leg.timeout() == pacing.HUNG_FLOOR, "a fast class still gets a usable floor"

    ticker.at = 9_950.0
    assert leg.timeout() == pytest.approx(30.0), "the budget's own remainder wins"


def test_the_margin_is_per_leg_and_not_once_for_the_run() -> None:
    """A stop in the colorize leg still has a selection and every record to write;
    a stop in the release leg has the records only."""
    paced, _ = clock(budget=1000.0)
    assert paced.leg(pacing.COLORIZE).margin == pacing.TEARDOWN_MARGIN[pacing.COLORIZE]
    assert paced.leg(pacing.RELEASE).margin == pacing.TEARDOWN_MARGIN[pacing.RELEASE]
    assert paced.leg("something else").margin == pacing.DEFAULT_MARGIN
    assert paced.leg(pacing.COLORIZE).minimum == pacing.UNMEASURED_MINIMUM[pacing.COLORIZE]
    assert paced.leg("something else").minimum == pacing.DEFAULT_UNMEASURED_MINIMUM


def test_the_unit_context_times_the_work_and_keeps_the_kill_apart_from_the_failure() -> None:
    paced, ticker = clock(budget=1000.0)
    leg = paced.leg(pacing.COLORIZE)
    with leg.unit() as unit:
        ticker.at = 12.0
        unit.ok = True
    assert unit.seconds == 12.0
    assert unit.expired is False
    assert leg.estimate() == 12.0

    with leg.unit() as second:
        ticker.at = 20.0
        second.ok = False
    assert leg.estimate() == 12.0, "a failure does not move the estimate"


def test_the_record_carries_the_arithmetic_behind_the_stop() -> None:
    """ "The run stopped early" and "it stopped with eleven minutes unspent because
    one row is measured at nine" are the same sentence without the numbers."""
    paced, ticker = clock(budget=100.0, margins={pacing.COLORIZE: 30.0})
    leg = paced.leg(pacing.COLORIZE)
    leg.observe(40.0)
    ticker.at = 50.0
    assert leg.may_start() is not None

    record = paced.record()
    assert record["wall_budget"] == 100.0
    assert record["legs"][pacing.COLORIZE]["estimate"] == 40.0
    assert record["declined"][0]["remaining"] == 50.0
    assert record["declined"][0]["margin"] == 30.0


# --------------------------------------------------------------------------- #
# The deadline itself, at the one place a curation unit spends its wall clock.
# --------------------------------------------------------------------------- #
def engine_that_hangs(monkeypatch) -> list:
    """Stand in for the binary: record the timeout it was given, then hang under it.

    Unbounded it returns, because that is what a real call with no timeout does —
    a subprocess that was given no deadline cannot report having missed one.
    """
    given: list = []

    def hang(*args, **kwargs):
        given.append(kwargs.get("timeout"))
        if kwargs.get("timeout") is None:
            return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")
        raise subprocess.TimeoutExpired(cmd="fractal-engine", timeout=kwargs["timeout"])

    monkeypatch.setattr(engine, "engine_path", lambda: "fractal-engine")
    monkeypatch.setattr(engine.subprocess, "run", hang)
    return given


def test_an_engine_call_outside_a_deadline_is_not_timed_out(monkeypatch) -> None:
    """The default stays what it was: a render takes as long as it takes."""
    given = engine_that_hangs(monkeypatch)
    assert engine.run("render", {}) == {}
    assert given == [None]


def test_a_bounded_engine_call_is_killed_and_says_which(monkeypatch) -> None:
    given = engine_that_hangs(monkeypatch)
    with engine.deadline(5.0) as bound, pytest.raises(engine.EngineTimeout, match="render"):
        engine.run("render", {})
    assert bound.expired is True
    assert given[0] == pytest.approx(5.0, abs=0.5)


def test_a_nested_deadline_may_shorten_what_it_is_allowed_and_never_lengthen_it(
    monkeypatch,
) -> None:
    given = engine_that_hangs(monkeypatch)
    with engine.deadline(5.0):
        with engine.deadline(500.0), pytest.raises(engine.EngineTimeout):
            engine.run("render", {})
        with engine.deadline(1.0), pytest.raises(engine.EngineTimeout):
            engine.run("render", {})
    assert given[0] == pytest.approx(5.0, abs=0.5)
    assert given[1] == pytest.approx(1.0, abs=0.5)


def test_a_deadline_already_past_does_not_start_the_engine(monkeypatch) -> None:
    given = engine_that_hangs(monkeypatch)
    with engine.deadline(0.0), pytest.raises(engine.EngineTimeout):
        engine.run("render", {})
    assert given == [], "nothing was launched to be killed"


def test_the_deadline_is_put_back_when_the_block_ends(monkeypatch) -> None:
    given = engine_that_hangs(monkeypatch)
    with engine.deadline(5.0), pytest.raises(engine.EngineTimeout):
        engine.run("render", {})
    assert engine.run("render", {}) == {}
    assert given[-1] is None
