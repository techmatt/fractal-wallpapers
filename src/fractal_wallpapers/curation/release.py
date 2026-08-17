"""The full-resolution pass: N pictures at release size, concurrently or serially.

A release render is the most expensive thing this project does. One is roughly
half engine and half the read-measure-rerender the autolevel operator may add, so
a serial pass leaves most of a many-core machine idle for most of its wall clock
whichever half is running. This module runs the pass as worker **processes** and
is the only thing that knows how.

## The one structural rule: workers render, the parent writes

A worker returns a picture on disk and a block of information about it, and
appends to nothing. Every record — the autolevel stamp, the timing, the caller's
own manifest — is written by the parent, from [`run_pass`]'s sink, **in plan
order**, once per task. That is what makes the concurrent pass's records
*identical* to the serial pass's rather than merely equivalent: an append-only log
with N writers has no order, and every record here is read downstream as an
ordered stream.

## The serial path is not a special case of the concurrent one

`workers <= 1` renders in this process: no pool, no pickling, no worker
initializer. It is the fallback, so it must not be a branch of the thing it is a
fallback *for* — and the two are held to each other by a real parity check on a
real plan rather than by construction ([`parity`]).

## Failure and interruption

* A row that raises comes back as a failed result and reaches the sink like any
  other. It never crosses the pool boundary, so one bad location cannot take the
  other rows down.
* A worker that **dies** — an out-of-memory kill is the realistic cause — breaks
  the pool for every future still outstanding. That is caught once and the
  remaining rows are rendered serially in the parent, because half a release is a
  worse outcome than a slow one. The fallback announces itself: a silent degrade
  to serial reads afterwards as "concurrency bought nothing".
* Each worker puts itself in a job object its engine children inherit, so a worker
  killed by anything at all takes its engine with it.
* A row that **hangs** is killed at the deadline its task carries, in the worker
  that started it, and comes back as a failed row. The parent keeps its own grace
  on top of that ([`KILL_GRACE`]) and takes the workers down itself if it expires,
  because a worker stuck somewhere the engine deadline cannot reach is exactly the
  case the worker's own bound cannot cover.

## Rows are submitted a window at a time, not all at once

A pass handed a gate ([`pacing.Leg`]) must be able to *not start* a row, and a
plan submitted in one go has started every row before the first one finishes.
So submission runs a window ahead of the sink's cursor — deep enough that no
worker ever waits for work, shallow enough that the gate still has a decision to
make — and the rows the gate declines are named in the record rather than
silently missing from it.

## Sizing is measured, not argued from core counts

Concurrency inflates each row's own wall clock — the engine already holds several
threads and the levelling pass is memory-bound — so the speedup is well under the
worker count, and the floor is the plan's single longest row. The defaults below
are a starting point that a run records and a measurement can move; nothing here
divides the machine by the worker count, because an over-provisioned sibling
engine is exactly what keeps the cores busy while another worker is in its
levelling pass.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field, replace
from pathlib import Path

from fractal_wallpapers import engine

#: How many worker processes a release pass uses by default.
DEFAULT_WORKERS = 3

#: How much longer than its own deadline a worker gets before the parent stops
#: waiting and kills it. Generous, because it is the backstop *behind* the
#: backstop: the worker bounds its own engine call, so this only fires when the
#: worker is stuck somewhere that bound cannot reach.
KILL_GRACE = 30.0

#: How many rows are submitted ahead of the sink's cursor. One deeper than the
#: worker count, so a worker never waits for the parent to notice it is free and
#: the gate still gets asked about every row before it starts.
SUBMIT_AHEAD = 1

#: What each worker's engine is told to use, passed **explicitly** at every
#: fan-out rather than inherited. Deliberately more than a fair share of a
#: twelve-thread machine: a worker in its levelling pass leaves cores that only
#: an over-provisioned sibling engine can take.
ENGINE_THREADS_PER_WORKER = 7

#: The environment variable the engine's thread pool reads.
THREADS_ENV = "RAYON_NUM_THREADS"


def engine_threads_for(workers: int) -> int | None:
    """Per-engine threads for `workers` engines; `None` at one, where there is no
    fan-out and the engine keeps its own default."""
    return None if workers <= 1 else ENGINE_THREADS_PER_WORKER


@dataclass(frozen=True)
class Task:
    """One release row. Everything in it survives a spawn pickle on any platform.

    `timeout` is the row's own kill deadline, decided by the parent when the row
    is submitted and carried across so the **worker** imposes it. A deadline the
    parent could only impose by waiting is not a deadline for the thing that is
    already stuck.
    """

    id: str
    row: dict
    colormap: str
    mode: str
    output: str
    geometry: dict
    timeout: float | None = None


@dataclass(frozen=True)
class Result:
    """What one row came out as.

    `stamp_pending` says there is an autolevel stamp in `info` for the **parent**
    to write. It is always the parent's job: the operator has no log writer of its
    own, so there is no switch here that a worker could get wrong and no path on
    which a stamp is written twice. False means there is nothing to write — a
    failure, or a coloring kind the operator does not touch.

    `timed_out` separates the row that was *killed* from the row that failed. Both
    are failed rows and only one of them is the run's own doing, and a pass whose
    estimate is formed off row timings must not learn the length of a deadline.
    """

    id: str
    ok: bool
    info: dict = field(default_factory=dict)
    seconds: float = 0.0
    error: str | None = None
    stamp_pending: bool = False
    timed_out: bool = False

    @property
    def stamp(self):
        return (self.info or {}).get("autolevel") if self.stamp_pending else None


def render_task(task: Task) -> Result:
    """Render one row under its own deadline. Never raises: a failed row is a recorded row."""
    started = time.monotonic()
    with engine.deadline(task.timeout) as bound:
        try:
            from fractal_wallpapers.curation import colorize
            from fractal_wallpapers.models import palette_sets

            picture, stamp = colorize.render(
                task.row,
                task.mode,
                task.colormap,
                palette_sets.cyclic(),
                Path(task.output),
                render_geometry=task.geometry,
            )
            return Result(
                task.id,
                True,
                {"picture": str(picture), "autolevel": stamp},
                time.monotonic() - started,
                None,
                stamp is not None,
            )
        except Exception as failure:  # noqa: BLE001
            return Result(
                task.id,
                False,
                {},
                time.monotonic() - started,
                repr(failure)[:400],
                False,
                bound.expired,
            )


def _worker(task: Task) -> Result:
    """The pooled unit. Module level and picklable by name — a spawned worker
    resolves it by name, so it cannot be a closure or a method."""
    return render_task(task)


def _worker_init(threads, quiet: bool) -> None:
    from fractal_wallpapers import process_control

    if threads is not None:
        os.environ[THREADS_ENV] = str(int(threads))
    priority = process_control.set_background_priority()
    cleanup = process_control.bind_children_to_parent()
    if not quiet:
        print(
            f"[release worker {os.getpid()}] threads={os.environ.get(THREADS_ENV)} "
            f"priority={priority} cleanup={cleanup}",
            flush=True,
        )


def _bounded(task: Task, leg) -> Task:
    """The task with the deadline it is being started under stamped into it."""
    return task if leg is None else replace(task, timeout=leg.timeout())


def _took(record: dict, leg, task: Task, result: Result, sink, log, note: str) -> None:
    """One finished row: counted, taught to the estimate, recorded, announced."""
    record["row_seconds"] += result.seconds
    if result.timed_out:
        record["killed"] += 1
    if leg is not None:
        leg.observe(result.seconds, result.ok, result.timed_out)
    sink(task, result)
    verdict = "ok" if result.ok else ("KILLED" if result.timed_out else "FAILED")
    log(f"[release] {task.id} {verdict} {result.seconds:.1f}s{note}")


def _serially(tasks, sink, record: dict, leg, log, note: str = " (serial)") -> None:
    """Render `tasks` in this process, gated one at a time.

    The fallback path and the one-worker path are the same code, which is the
    point: the serial path must not become a branch of the thing it is a fallback
    for. The gate is asked here too — a pass that stopped starting rows in the
    pool and then started them all in the parent would be no backstop at all.
    """
    for index, task in enumerate(tasks):
        decline = leg.may_start() if leg is not None else None
        if decline is not None:
            record["stopped"] = str(decline)
            record["not_started"] = [rest.id for rest in tasks[index:]]
            log(f"[release] BUDGET STOP before {task.id}: {decline}")
            return
        _took(record, leg, task, render_task(_bounded(task, leg)), sink, log, note)


def _kill_workers(pool, log) -> None:
    """Take the pool's workers down where they stand.

    Reaching for the executor's own process table is the only way to end a worker
    that is not going to answer: nothing in the public interface interrupts a
    running future. Each worker carries a job object, so its engine goes with it.
    """
    for process in list(getattr(pool, "_processes", {}).values()):
        try:
            process.kill()
        except Exception as failure:  # noqa: BLE001 — a worker already gone is the good case
            log(f"[release] worker {getattr(process, 'pid', '?')} would not die: {failure!r}")


def run_pass(tasks, workers: int, sink, log=print, leg=None) -> dict:
    """Render `tasks` and hand each result to `sink(task, result)` **in plan order**.

    The sink runs in the parent, exactly once per task, in the order `tasks` was
    given and never concurrently with itself. It is the only place records are
    written, which is the whole reason a worker renders with its stamp write
    suppressed and hands the stamp back instead.

    `leg` is the pass's share of the run's wall clock ([`pacing.Leg`]) and is
    optional: without one the pass renders every row, unbounded, exactly as it
    always has. With one, each row is asked for before it is started and carries
    the deadline it was granted.

    Returns a small record of what the pass *did* — the worker count, the engine
    threads, whether the serial fallback fired, which rows never started — for the
    caller to stamp into its own summary rather than restate.
    """
    tasks = list(tasks)
    workers = max(1, int(workers))
    started = time.monotonic()
    record = {
        "rows": len(tasks),
        "workers": workers,
        "engine_threads": engine_threads_for(workers),
        "fell_back_serial": 0,
        # The pass's own wall clock, which is the leg the next run budgets from.
        # Not the sum of the rows: under concurrency those two differ by exactly
        # the thing anybody wants to know.
        "seconds": 0.0,
        "row_seconds": 0.0,
        "killed": 0,
        "stopped": None,
        "not_started": [],
    }
    if not tasks:
        return record

    def close() -> dict:
        record["seconds"] = round(time.monotonic() - started, 1)
        record["row_seconds"] = round(record["row_seconds"], 1)
        return record

    if workers <= 1:
        _serially(tasks, sink, record, leg, log)
        return close()

    pool = ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_worker_init,
        initargs=(record["engine_threads"], False),
    )
    clean = False
    futures: dict = {}
    limits: dict = {}
    horizon = 0

    def fill(upto: int) -> None:
        """Submit rows up to `upto`, asking the gate about each one first."""
        nonlocal horizon
        while horizon < min(upto, len(tasks)) and record["stopped"] is None:
            decline = leg.may_start() if leg is not None else None
            if decline is not None:
                record["stopped"] = str(decline)
                record["not_started"] = [rest.id for rest in tasks[horizon:]]
                log(f"[release] BUDGET STOP before {tasks[horizon].id}: {decline}")
                return
            bounded = _bounded(tasks[horizon], leg)
            limits[horizon] = bounded.timeout
            futures[horizon] = pool.submit(_worker, bounded)
            horizon += 1

    try:
        log(
            f"[release] {len(tasks)} row(s) over {workers} worker process(es) at "
            f"{THREADS_ENV}={record['engine_threads']} (serial fallback: --workers 1)"
        )
        fill(workers + SUBMIT_AHEAD)
        for index, task in enumerate(tasks):
            if index not in futures:
                break  # the gate stopped the pass before this row was submitted
            grace = None if limits[index] is None else limits[index] + KILL_GRACE
            try:
                result = futures[index].result() if grace is None else futures[index].result(grace)
            except FutureTimeout:
                log(
                    f"[release] {task.id} HUNG past its {limits[index]:.0f}s deadline and a "
                    f"{KILL_GRACE:.0f}s grace - killing the pool and finishing in the parent"
                )
                _kill_workers(pool, log)
                _took(
                    record,
                    leg,
                    task,
                    Result(
                        task.id,
                        False,
                        {},
                        limits[index] + KILL_GRACE,
                        "killed: hung past its deadline and the parent's grace",
                        False,
                        True,
                    ),
                    sink,
                    log,
                    " (killed by the parent)",
                )
                rest = tasks[index + 1 :]
                record["fell_back_serial"] += len(rest)
                _serially(rest, sink, record, leg, log, " (serial, after a kill)")
                return close()
            except BrokenProcessPool as broken:
                rest = tasks[index:]
                record["fell_back_serial"] = len(rest)
                log(
                    f"[release] POOL BROKEN ({broken!r}) - rendering the remaining "
                    f"{len(rest)} row(s) serially in the parent rather than dropping them"
                )
                _serially(rest, sink, record, leg, log, " (serial, after the pool broke)")
                clean = True
                return close()
            except Exception as failure:  # noqa: BLE001
                result = Result(task.id, False, {}, 0.0, repr(failure)[:400], False)
            _took(record, leg, task, result, sink, log, f" [{index + 1}/{len(tasks)}]")
            fill(index + 1 + workers + SUBMIT_AHEAD)
        clean = True
    finally:
        # A clean end waits for the workers; an interrupted one cancels what has
        # not started and does not block on what has — each worker's own job
        # object takes its engine down with it.
        pool.shutdown(wait=clean, cancel_futures=not clean)
    return close()


def decodable(picture: Path) -> bool:
    """Whether a picture on disk can be read back at all.

    A truncated mid-write victim is removed here rather than left for the render
    to overwrite, so "already there" cannot mean "half there". This is a question
    about *bytes* and it is deliberately not the resume question: see
    [`resumable`].
    """
    if not picture.is_file():
        return False
    try:
        from PIL import Image

        with Image.open(picture) as opened:
            opened.verify()
        return True
    except Exception:  # noqa: BLE001 — truncated or corrupt: re-render it
        picture.unlink(missing_ok=True)
        return False


def timing_path(directory: Path) -> Path:
    """The release leg's own per-row record, which is what says a row finished."""
    return Path(directory) / "timing.jsonl"


def completed(directory: Path) -> set[str]:
    """The ids the release leg recorded as finished, last row winning.

    **The completion stamp, not the file, is what a resume trusts.** A decodable
    picture proves a render wrote bytes; it does not prove the *row* is done, and
    on the autolevel path those are different claims — one unit deadline is spent
    by two full-resolution renders to one path, so a kill on the second leaves a
    perfectly readable picture that never got its operator pass. The first
    production run resumed four such rows as finished, reconciled `28 planned =
    28 resumed`, and shipped four pictures the record described wrongly.

    A row is done when the parent wrote a timing record saying so. Rows are
    upserted by id because a row killed once and made again has two, and only the
    last one describes the picture that exists.
    """
    import json

    path = timing_path(directory)
    if not path.is_file():
        return set()
    done: dict[str, bool] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a killed run's half-written last line
        if "id" in row:
            done[str(row["id"])] = bool(row.get("ok"))
    return {identifier for identifier, ok in done.items() if ok}


def resumable(identifier: str, picture: Path, done: set[str]) -> bool:
    """Whether a released row may be carried across a resume rather than remade.

    Both halves, and each one catches what the other cannot: the record says the
    row *finished*, and the decode says the picture it finished into is still
    there and still readable.
    """
    return str(identifier) in done and decodable(Path(picture))


def parity(tasks, workers: int, directory: Path, log=print) -> dict:
    """Render a real plan both ways and compare the bytes.

    The claim the concurrent path makes is not "equivalent output" but *the same
    file*, and the only way to know is to make both. Each row is rendered once in
    the parent and once through the pool, into two directories, and every pair is
    compared byte for byte along with the autolevel stamp each produced.
    """
    import hashlib

    directory = Path(directory)
    out = {}
    for arm, count in (("serial", 1), ("concurrent", max(2, int(workers)))):
        where = directory / arm
        where.mkdir(parents=True, exist_ok=True)
        arm_tasks = [
            Task(
                id=task.id,
                row=task.row,
                colormap=task.colormap,
                mode=task.mode,
                output=str(where / Path(task.output).name),
                geometry=task.geometry,
            )
            for task in tasks
        ]
        seen: dict = {}

        def sink(task, result, seen=seen):
            seen[task.id] = result

        record = run_pass(arm_tasks, count, sink, log)
        out[arm] = {
            "pass": record,
            "rows": {
                identifier: {
                    "ok": result.ok,
                    "error": result.error,
                    "sha256": (
                        hashlib.sha256(Path(result.info["picture"]).read_bytes()).hexdigest()
                        if result.ok
                        else None
                    ),
                    # Whether the operator MOVED this render, not whether it ran.
                    # A stamp is present on every palette-mapped row and says
                    # `acted: false` on the common in-band one; reading the
                    # stamp's presence as action would report every row as
                    # leveled and make the parity claim weaker than it is.
                    "acted": bool((result.info.get("autolevel") or {}).get("acted")),
                    "stamp": (result.info.get("autolevel") or {}).get("curve"),
                }
                for identifier, result in sorted(seen.items())
            },
        }

    identifiers = sorted(set(out["serial"]["rows"]) | set(out["concurrent"]["rows"]))
    disagreed = [
        identifier
        for identifier in identifiers
        if out["serial"]["rows"].get(identifier, {}).get("sha256")
        != out["concurrent"]["rows"].get(identifier, {}).get("sha256")
    ]
    return {
        "rows": len(identifiers),
        "identical": len(identifiers) - len(disagreed),
        "disagreed": disagreed,
        "held": not disagreed,
        "arms": out,
    }


__all__ = [
    "DEFAULT_WORKERS",
    "ENGINE_THREADS_PER_WORKER",
    "KILL_GRACE",
    "SUBMIT_AHEAD",
    "THREADS_ENV",
    "Result",
    "Task",
    "completed",
    "decodable",
    "engine_threads_for",
    "parity",
    "render_task",
    "resumable",
    "run_pass",
    "timing_path",
]
