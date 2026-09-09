"""The release pass: workers render, the parent writes, in plan order."""

from __future__ import annotations

import subprocess
from concurrent.futures import TimeoutError as FutureTimeout
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest

from fractal_wallpapers.curation import checks, pacing, release


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


@pytest.mark.slow
def test_a_row_that_raises_is_a_recorded_row(monkeypatch) -> None:
    """It never crosses the pool boundary, so one bad location cannot take the rest down."""
    from fractal_wallpapers.curation import colorize

    def boom(*args, **kwargs):
        raise ValueError("no such location")

    monkeypatch.setattr(colorize, "render", boom)
    result = release.render_task(task("a"))
    assert result.ok is False
    assert "no such location" in result.error


def test_a_rows_mode_settings_reach_the_render_rather_than_being_dropped(monkeypatch) -> None:
    """A `direct_trap_multiply` at `opacity=0.6` and a bare one are two different
    pictures — the settings are in the recipe key — and until 2026-09-04 the task
    had nowhere to carry them, so every release render of a varied seat was the
    **bare** mode under the varied seat's name. Silent, because the bare picture
    is a perfectly good picture of something else. Twelve of the thousand seats in
    `20260904T233233Z` are varied, which is how it was found."""
    from fractal_wallpapers.curation import colorize

    seen: dict = {}

    def render(row, mode, colormap, cyclic, output, **rest):
        seen.update(rest)
        return Path(output), None

    monkeypatch.setattr(colorize, "render", render)
    varied = release.Task(
        id="a",
        row={},
        colormap="x",
        mode="direct_trap_multiply",
        output="a.png",
        geometry={},
        mode_params={"opacity": 0.6},
    )
    assert release.render_task(varied).ok
    assert seen["mode_params"] == {"opacity": 0.6}
    # And a task that says nothing still renders, with nothing said.
    release.render_task(task("b"))
    assert seen["mode_params"] == {}


def test_a_release_task_is_constructed_in_exactly_one_place_in_the_tree() -> None:
    """**The guard that replaced counting keywords at call sites, and why.**

    There were two guards here. One counted `mode_params=` against `release.Task(`
    per module and one counted `autolevel=`, and both were green on 2026-09-08
    while **four of the five builders dropped `curve` and `palette`** — two more
    [`recipes.KEYED`] members, so an authored-palette row released as the plain
    picture under its own name. A guard that names the members somebody already
    thought of cannot catch the next one; that is the same lesson
    `test_renderer_agreement.py` is built on.

    So the claim is structural instead: `release.Task(` is constructed **once**,
    inside [`release.task_for`], whose picture-deciding parameters have no
    defaults. A builder that forgets a member gets a `TypeError`, and a member
    added to `KEYED` is added to one signature and every leg fails until it says
    what it passes.
    """
    import inspect

    from fractal_wallpapers import curation

    root = Path(inspect.getfile(curation)).parent
    sites = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8").count("Task(")
        for path in sorted(root.rglob("*.py"))
    }
    outside = {name: count for name, count in sites.items() if count and name != "release.py"}
    assert not outside, (
        f"{sorted(outside)} construct a release task directly. There is one builder — "
        f"`release.task_for` — and it is the only thing that can require every member "
        f"deciding the pixels. A second construction site is a second chance to forget one."
    )
    # One inside `release` itself and no more — the one `task_for` makes. `parity`
    # is the other place a task comes into being there and it re-points one it was
    # HANDED, through `dataclasses.replace`, so every field carries including one
    # added after this was written. `parity` was the fifth builder and was missed
    # in 2026-09-05 for exactly that reason, so it is pinned rather than counted.
    assert sites["release.py"] == 1, "release.py builds a task somewhere besides `task_for`"
    assert inspect.getsource(release.task_for).count("Task(") == 1
    assert "Task(" not in inspect.getsource(release.parity)
    assert "dataclasses.replace(task" in inspect.getsource(release.parity)


def test_the_one_builder_refuses_a_task_that_does_not_name_every_picture_member() -> None:
    """`task_for` is only worth having if omission is an error rather than a default.

    One case per member, because the failure this closes is *one* forgotten
    keyword: four builders passed `mode_params` and dropped `curve` and `palette`,
    and every guard the project had was green.
    """
    whole = {
        "id": "a",
        "row": {"family": {}, "viewport": {}},
        "mode": "smooth",
        "colormap": "viridis",
        "mode_params": {},
        "curve": "linear",
        "palette": None,
        "autolevel": None,
        "output": "a.png",
        "geometry": {"resolution": [16, 9], "supersample": 1, "maxiter": 64},
    }
    assert release.task_for(**whole).row["maxiter"] == 64, "the row's cap comes off the geometry"
    for member in ("mode_params", "curve", "palette", "autolevel"):
        short = {name: value for name, value in whole.items() if name != member}
        with pytest.raises(TypeError):
            release.task_for(**short)


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


@pytest.mark.slow
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


def test_a_regime_round_trips_through_the_spelling_a_person_types() -> None:
    """`<w>x<h>ss<n>`, the same spelling the tile corpus uses for the same pair."""
    regime = release.regime_of("1280x720ss2")
    assert regime.resolution == (1280, 720)
    assert regime.supersample == 2
    assert regime.spelled == "1280x720ss2"
    assert regime.geometry() == {"resolution": [1280, 720], "supersample": 2}
    # A fresh dict every call: a caller stamps its row's maxiter into it.
    assert regime.geometry() is not regime.geometry()
    assert release.regime_from_geometry(regime.geometry()).spelled == regime.spelled
    assert release.regime_from_geometry(None) is None
    assert release.regime_from_geometry({"resolution": [640, 360]}) is None
    for refused in ("1280x720", "1280ss2", "", "twelve-eighty"):
        with pytest.raises(ValueError):
            release.regime_of(refused)
    with pytest.raises(ValueError):
        release.Regime((0, 720), 2)


def test_a_check_re_derives_the_pixels_the_row_shipped_and_not_todays_default() -> None:
    """Both checks compare BYTES, so the geometry has to come off the row.

    Every row written before `release_geometry` existed came out of a 2560x1440
    ss4 leg, which is the whole of what the fallback claims.
    """
    row = {
        "candidate": "0000",
        "location": {"family": {}, "viewport": {}, "maxiter": 900},
        "recipe": {"colormap": "viridis", "mode": "smooth"},
    }
    assert checks.regime_of_row(row).spelled == checks.UNRECORDED_REGIME.spelled
    assert checks.UNRECORDED_REGIME.spelled == "2560x1440ss4"

    shipped = {**row, "release_geometry": {"resolution": [1280, 720], "supersample": 2}}
    assert checks.regime_of_row(shipped).spelled == "1280x720ss2"
    task = checks.tasks_of("gallery4", [shipped], Path("out"))[0]
    assert task.geometry == {"resolution": [1280, 720], "supersample": 2, "maxiter": 900}


def test_a_varied_seat_renders_the_varied_mode_on_BOTH_parity_arms(monkeypatch, tmp_path) -> None:
    """`release.parity` was rebuilding each arm's task from six of the seven
    fields, so a plan carrying `mode_params` was checked as two renders of the
    BARE mode — which agree with each other perfectly. The check passed by
    dropping the thing it was checking, which is worse than no check: `curate
    parity` is what holds the concurrent release path to the serial one, and a
    varied seat is exactly the row where the two could diverge.

    Both arms are asserted, because the serial one alone would have passed before
    the fix as well: the bug was in the rebuild, and the rebuild ran per arm.
    """
    seen: dict = {}

    def run_pass(tasks, workers, sink, log=None, leg=None):
        held = list(tasks)
        seen[workers] = held
        for one in held:
            # The parity report hashes what the arm wrote, so the stub writes it.
            Path(one.output).write_bytes(b"pretend png for " + one.mode_params.__repr__().encode())
            sink(one, release.Result(one.id, True, {"picture": str(one.output)}, 0.0))
        return {"rows": len(held), "workers": workers}

    monkeypatch.setattr(release, "run_pass", run_pass)

    varied = release.Task(
        id="a",
        row={},
        colormap="x",
        mode="direct_trap_multiply",
        output=str(tmp_path / "a.png"),
        geometry={"resolution": [8, 8], "supersample": 1},
        timeout=12.0,
        mode_params={"opacity": 0.6, "threshold": 0.2},
    )
    report = release.parity([varied], workers=3, directory=tmp_path / "parity", log=lambda *_: None)

    assert set(seen) == {1, 3}, "one serial arm and one concurrent arm"
    for workers, tasks in seen.items():
        held = tasks[0]
        assert held.mode_params == {"opacity": 0.6, "threshold": 0.2}, (
            f"the {workers}-worker arm rendered the bare mode under the varied seat's name"
        )
        assert held.mode == "direct_trap_multiply" and held.timeout == 12.0
        assert held.geometry == varied.geometry and held.row == varied.row
    # The one field an arm may differ in, and it is the point of the rebuild.
    assert {Path(tasks[0].output).parent.name for tasks in seen.values()} == {
        "serial",
        "concurrent",
    }
    assert report["rows"] == 1


# --------------------------------------------------------------------------- #
# The levelling decision, inherited rather than retaken.
# --------------------------------------------------------------------------- #
def test_a_rows_inherited_curve_reaches_the_render_rather_than_being_dropped(monkeypatch) -> None:
    """`mode_params`' failure, one field over. A task that dropped the curve would
    render a picture that measured itself at release geometry — a perfectly good
    picture of a levelling nobody judged, under the seat's own name."""
    from fractal_wallpapers.curation import colorize

    seen: dict = {}

    def render(row, mode, colormap, cyclic, output, **rest):
        seen.update(rest)
        return Path(output), None

    monkeypatch.setattr(colorize, "render", render)
    borrowed = {"curve": {"applies": True, "identity": False}, "from": {"key": "abc"}}
    inheriting = release.Task(
        id="a",
        row={},
        colormap="x",
        mode="smooth",
        output="a.png",
        geometry={},
        autolevel=borrowed,
    )
    assert release.render_task(inheriting).ok
    assert seen["borrowed"] == borrowed
    # A seat with no curve on any record still renders, deciding for itself.
    release.render_task(task("b"))
    assert seen["borrowed"] is None


def test_every_keyed_member_the_task_carries_reaches_the_render(monkeypatch) -> None:
    """The fast mirror of `test_renderer_agreement.py`'s authored case.

    That one proves it on the pixels and costs an engine; this one costs nothing and
    says *which* argument went missing when it does. Both exist because the four
    builders that dropped `curve` and `palette` were handing them to a task that
    would have carried them — the members were never put on the task at all, and
    nothing between the task and `colorize.render` would have noticed either.
    """
    from fractal_wallpapers.curation import colorize

    seen: dict = {}

    def render(row, mode, colormap, cyclic, output, **rest):
        seen.update(rest)
        return Path(output), None

    monkeypatch.setattr(colorize, "render", render)
    palette = {"gamma": 0.55, "cycles": 2.0, "mirror": True}
    whole = release.task_for(
        id="a",
        row={"family": {}, "viewport": {}},
        mode="smooth",
        colormap="viridis",
        mode_params={"opacity": 0.6},
        curve="log",
        palette=palette,
        autolevel=None,
        output="a.png",
        geometry={"resolution": [16, 9], "supersample": 1, "maxiter": 64},
    )
    assert release.render_task(whole).ok
    assert seen["mode_params"] == {"opacity": 0.6}
    assert seen["curve"] == "log"
    assert seen["palette"] == palette


def test_every_leg_that_releases_a_row_goes_through_the_one_builder() -> None:
    """The all-of-them claim, now that there is one door to check they take.

    Five legs turn a stored row into a release render and each spelled the task
    out inline until 2026-09-08. Naming them here is the other half of
    `test_a_release_task_is_constructed_in_exactly_one_place_in_the_tree`: that
    one says nothing builds a task directly, this one says these five still build
    tasks at all, so a leg that quietly stopped releasing anything is not read as
    compliance.
    """
    import inspect

    from fractal_wallpapers.curation import label_fate, run, solve, votes

    for module in (checks, label_fate, run, solve, votes):
        source = inspect.getsource(module)
        assert "release.task_for(" in source, (
            f"{module.__name__} releases rows and no longer builds a task through "
            f"`release.task_for` — either it stopped releasing, or it found another way "
            f"to build one, and the second is how this bug class returns"
        )
