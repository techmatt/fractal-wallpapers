"""The release pass: workers render, the parent writes, in plan order."""

from __future__ import annotations

import subprocess
from concurrent.futures import TimeoutError as FutureTimeout
from concurrent.futures.process import BrokenProcessPool

import pytest

from fractal_wallpapers.curation import pacing, release


class Gate:
    """A leg that allows `allow` rows and then stops, without a real clock."""

    def __init__(self, allow: int, timeout: float | None = None):
        self.allow, self.timeout_seconds = allow, timeout
        self.observed: list = []

    def may_start(self):
        if self.allow <= 0:
            return "out of budget, for the test"
        self.allow -= 1
        return None

    def timeout(self):
        return self.timeout_seconds

    def observe(self, seconds, ok=True, expired=False):
        self.observed.append((round(seconds, 3), ok, expired))


def task(identifier: str) -> release.Task:
    return release.Task(
        id=identifier,
        row={},
        colormap="x",
        mode="smooth",
        output=f"{identifier}.png",
        geometry={},
    )


def recorder():
    """A sink that remembers the order it was called in — the property under test."""
    seen: list = []

    def sink(task_, result):
        seen.append((task_.id, result.ok))

    return seen, sink


def test_the_serial_path_is_taken_at_one_worker(monkeypatch) -> None:
    """No pool, no pickling, no worker initializer: it must not be a branch of the
    thing it is a fallback for."""
    started = []
    monkeypatch.setattr(release, "_worker_init", lambda *a: started.append(a))
    monkeypatch.setattr(
        release, "render_task", lambda t: release.Result(t.id, True, {}, 0.0, None, False)
    )
    seen, sink = recorder()
    record = release.run_pass([task("a"), task("b")], 1, sink, log=lambda _m: None)
    assert record["workers"] == 1
    assert record["engine_threads"] is None
    assert not started
    assert [identifier for identifier, _ in seen] == ["a", "b"]


def test_the_sink_runs_once_per_task_in_plan_order_however_the_pool_finished(
    monkeypatch,
) -> None:
    """An append-only log with N writers has no order, which is why the parent writes."""

    class Future:
        def __init__(self, identifier):
            self.identifier = identifier

        def result(self):
            return release.Result(self.identifier, True, {}, 0.0, None, False)

    class Pool:
        def __init__(self, *args, **kwargs):
            self.submitted = []

        def submit(self, _entry, task_):
            # Completed in the reverse of plan order, which is what a real pool does.
            self.submitted.insert(0, task_.id)
            return Future(task_.id)

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(release, "ProcessPoolExecutor", Pool)
    seen, sink = recorder()
    plan = [task("a"), task("b"), task("c")]
    release.run_pass(plan, 3, sink, log=lambda _m: None)
    assert [identifier for identifier, _ in seen] == ["a", "b", "c"]


def test_a_dead_worker_finishes_the_release_serially_and_announces_it(monkeypatch) -> None:
    """Half a release is a worse outcome than a slow one, and a silent degrade to
    serial reads afterwards as "concurrency bought nothing"."""

    class Broken:
        def result(self):
            raise BrokenProcessPool("worker died")

    class Pool:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, _entry, _task):
            return Broken()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(release, "ProcessPoolExecutor", Pool)
    monkeypatch.setattr(
        release, "render_task", lambda t: release.Result(t.id, True, {}, 0.0, None, False)
    )
    said: list = []
    seen, sink = recorder()
    record = release.run_pass([task("a"), task("b")], 3, sink, log=said.append)
    assert record["fell_back_serial"] == 2
    assert [identifier for identifier, _ in seen] == ["a", "b"]
    assert any("POOL BROKEN" in line for line in said)


def test_a_row_that_raises_is_a_recorded_row(monkeypatch) -> None:
    """It never crosses the pool boundary, so one bad location cannot take the rest down."""
    from fractal_wallpapers.curation import colorize

    def boom(*args, **kwargs):
        raise ValueError("no such location")

    monkeypatch.setattr(colorize, "render", boom)
    result = release.render_task(task("a"))
    assert result.ok is False
    assert "no such location" in result.error


def test_a_stamp_only_comes_back_when_there_is_one_to_write() -> None:
    with_stamp = release.Result("a", True, {"autolevel": {"acted": True}}, 0.0, None, True)
    without = release.Result("b", True, {"autolevel": None}, 0.0, None, False)
    assert with_stamp.stamp == {"acted": True}
    assert without.stamp is None


def test_a_truncated_picture_is_removed_rather_than_reused(tmp_path) -> None:
    """ "Already there" must not be able to mean "half there"."""
    half = tmp_path / "a.png"
    half.write_bytes(b"\x89PNG\r\n\x1a\n truncated")
    assert release.decodable(half) is False
    assert not half.exists()
    assert release.decodable(tmp_path / "missing.png") is False


def test_the_engine_thread_count_is_explicit_above_one_worker() -> None:
    assert release.engine_threads_for(1) is None
    assert release.engine_threads_for(3) == release.ENGINE_THREADS_PER_WORKER


def test_a_gated_serial_pass_stops_at_a_row_boundary_and_names_what_never_started(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        release, "render_task", lambda t: release.Result(t.id, True, {}, 1.0, None, False)
    )
    seen, sink = recorder()
    gate = Gate(allow=1)
    record = release.run_pass([task("a"), task("b"), task("c")], 1, sink, lambda _m: None, gate)
    assert [identifier for identifier, _ in seen] == ["a"]
    assert record["not_started"] == ["b", "c"]
    assert "out of budget" in record["stopped"]
    assert gate.observed == [(1.0, True, False)]


def test_the_pool_is_not_handed_every_row_at_once(monkeypatch) -> None:
    """A plan submitted in one go has started every row before the first finishes,
    and a gate that cannot decline a row is not a gate."""
    submitted: list = []

    class Future:
        def __init__(self, identifier):
            self.identifier = identifier

        def result(self, timeout=None):
            return release.Result(self.identifier, True, {}, 0.0, None, False)

    class Pool:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, _entry, task_):
            submitted.append(task_.id)
            return Future(task_.id)

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(release, "ProcessPoolExecutor", Pool)
    plan = [task(name) for name in "abcdef"]
    seen, sink = recorder()
    record = release.run_pass(plan, 2, sink, lambda _m: None, Gate(allow=3))
    assert submitted == ["a", "b", "c"], "the window is workers + SUBMIT_AHEAD deep"
    assert [identifier for identifier, _ in seen] == ["a", "b", "c"]
    assert record["not_started"] == ["d", "e", "f"]


def test_a_row_carries_the_deadline_it_was_started_under_across_the_pool(monkeypatch) -> None:
    """A deadline the parent could only impose by waiting is no deadline for the
    thing that is already stuck."""
    submitted: list = []

    class Future:
        def result(self, timeout=None):
            return release.Result("a", True, {}, 0.0, None, False)

    class Pool:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, _entry, task_):
            submitted.append(task_.timeout)
            return Future()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(release, "ProcessPoolExecutor", Pool)
    _seen, sink = recorder()
    release.run_pass([task("a")], 2, sink, lambda _m: None, Gate(allow=9, timeout=42.0))
    assert submitted == [42.0]


def test_a_hung_worker_is_killed_by_the_parent_and_the_rest_finish_serially(
    monkeypatch,
) -> None:
    """The backstop behind the backstop: a worker stuck somewhere its own engine
    deadline cannot reach."""
    killed: list = []

    class Hung:
        def result(self, timeout=None):
            raise FutureTimeout()

    class Pool:
        def __init__(self, *args, **kwargs):
            self._processes = {1: type("P", (), {"pid": 1, "kill": lambda s: killed.append(1)})()}

        def submit(self, _entry, _task):
            return Hung()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(release, "ProcessPoolExecutor", Pool)
    monkeypatch.setattr(
        release, "render_task", lambda t: release.Result(t.id, True, {}, 0.5, None, False)
    )
    said: list = []
    seen, sink = recorder()
    gate = Gate(allow=9, timeout=1.0)
    record = release.run_pass([task("a"), task("b")], 2, sink, said.append, gate)
    assert killed == [1]
    assert seen == [("a", False), ("b", True)], "the killed row is recorded, then the rest run"
    assert record["killed"] == 1
    assert record["fell_back_serial"] == 1
    assert any("HUNG" in line for line in said)
    assert gate.observed[0] == (1.0 + release.KILL_GRACE, False, True)


def test_a_killed_row_is_a_failed_row_that_says_it_was_killed(monkeypatch) -> None:
    """The engine call is where the wall clock goes, so that is where it is cut —
    and a row that failed on its own must not be reported as a kill."""
    from fractal_wallpapers import engine
    from fractal_wallpapers.curation import colorize

    monkeypatch.setattr(colorize, "render", lambda *a, **k: (_ for _ in ()).throw(ValueError("no")))
    fell_over = release.render_task(release.Task("a", {}, "x", "smooth", "a.png", {}, timeout=5.0))
    assert (fell_over.ok, fell_over.timed_out) == (False, False)

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="fractal-engine", timeout=kwargs.get("timeout") or 0)

    monkeypatch.setattr(engine, "engine_path", lambda: "fractal-engine")
    monkeypatch.setattr(engine.subprocess, "run", hang)
    monkeypatch.setattr(colorize, "render", lambda *a, **k: engine.run("render", {}))
    killed = release.render_task(release.Task("b", {}, "x", "smooth", "b.png", {}, timeout=5.0))
    assert (killed.ok, killed.timed_out) == (False, True)
    assert "deadline" in killed.error


def test_the_pacing_leg_and_the_pass_agree_on_the_contract() -> None:
    """The pass takes any object with these three; `pacing.Leg` is the one it gets."""
    leg = pacing.Clock(100.0).leg(pacing.RELEASE)
    assert leg.may_start() is None
    assert leg.timeout() is not None
    leg.observe(1.0, ok=True, expired=False)
    assert leg.estimate() == 1.0


def test_an_empty_plan_is_not_a_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        release, "ProcessPoolExecutor", lambda *a, **k: pytest.fail("no pool for no rows")
    )
    record = release.run_pass([], 3, lambda *_a: None, log=lambda _m: None)
    assert record["rows"] == 0
