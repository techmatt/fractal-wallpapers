"""The release pass: workers render, the parent writes, in plan order."""

from __future__ import annotations

from concurrent.futures.process import BrokenProcessPool

import pytest

from fractal_wallpapers.curation import release


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
    assert release.resumable(half) is False
    assert not half.exists()
    assert release.resumable(tmp_path / "missing.png") is False


def test_the_engine_thread_count_is_explicit_above_one_worker() -> None:
    assert release.engine_threads_for(1) is None
    assert release.engine_threads_for(3) == release.ENGINE_THREADS_PER_WORKER


def test_an_empty_plan_is_not_a_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        release, "ProcessPoolExecutor", lambda *a, **k: pytest.fail("no pool for no rows")
    )
    record = release.run_pass([], 3, lambda *_a: None, log=lambda _m: None)
    assert record["rows"] == 0
