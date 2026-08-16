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
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from pathlib import Path

#: How many worker processes a release pass uses by default.
DEFAULT_WORKERS = 3

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
    """One release row. Everything in it survives a spawn pickle on any platform."""

    id: str
    row: dict
    colormap: str
    mode: str
    output: str
    geometry: dict


@dataclass(frozen=True)
class Result:
    """What one row came out as.

    `stamp_pending` says there is an autolevel stamp in `info` for the **parent**
    to write. It is always the parent's job: the operator has no log writer of its
    own, so there is no switch here that a worker could get wrong and no path on
    which a stamp is written twice. False means there is nothing to write — a
    failure, or a coloring kind the operator does not touch.
    """

    id: str
    ok: bool
    info: dict = field(default_factory=dict)
    seconds: float = 0.0
    error: str | None = None
    stamp_pending: bool = False

    @property
    def stamp(self):
        return (self.info or {}).get("autolevel") if self.stamp_pending else None


def render_task(task: Task) -> Result:
    """Render one row. Never raises: a failed row is a recorded row."""
    started = time.monotonic()
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
        return Result(task.id, False, {}, time.monotonic() - started, repr(failure)[:400], False)


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


def run_pass(tasks, workers: int, sink, log=print) -> dict:
    """Render `tasks` and hand each result to `sink(task, result)` **in plan order**.

    The sink runs in the parent, exactly once per task, in the order `tasks` was
    given and never concurrently with itself. It is the only place records are
    written, which is the whole reason a worker renders with its stamp write
    suppressed and hands the stamp back instead.

    Returns a small record of what the pass *did* — the worker count, the engine
    threads, whether the serial fallback fired — for the caller to stamp into its
    own summary rather than restate.
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
    }
    if not tasks:
        return record

    if workers <= 1:
        for index, task in enumerate(tasks, start=1):
            result = render_task(task)
            sink(task, result)
            record["row_seconds"] += result.seconds
            log(
                f"[release] {index}/{len(tasks)} {task.id} "
                f"{'ok' if result.ok else 'FAILED'} {result.seconds:.1f}s (serial)"
            )
        record["seconds"] = round(time.monotonic() - started, 1)
        return record

    pool = ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_worker_init,
        initargs=(record["engine_threads"], False),
    )
    clean = False
    try:
        log(
            f"[release] {len(tasks)} row(s) over {workers} worker process(es) at "
            f"{THREADS_ENV}={record['engine_threads']} (serial fallback: --workers 1)"
        )
        futures = [pool.submit(_worker, task) for task in tasks]
        for index, (task, future) in enumerate(zip(tasks, futures, strict=True)):
            try:
                result = future.result()
            except BrokenProcessPool as broken:
                rest = tasks[index:]
                record["fell_back_serial"] = len(rest)
                log(
                    f"[release] POOL BROKEN ({broken!r}) - rendering the remaining "
                    f"{len(rest)} row(s) serially in the parent rather than dropping them"
                )
                for remaining in rest:
                    outcome = render_task(remaining)
                    record["row_seconds"] += outcome.seconds
                    sink(remaining, outcome)
                clean = True
                record["seconds"] = round(time.monotonic() - started, 1)
                return record
            except Exception as failure:  # noqa: BLE001
                result = Result(task.id, False, {}, 0.0, repr(failure)[:400], False)
            record["row_seconds"] += result.seconds
            sink(task, result)
            log(
                f"[release] {index + 1}/{len(tasks)} {task.id} "
                f"{'ok' if result.ok else 'FAILED'} {result.seconds:.1f}s"
            )
        clean = True
    finally:
        # A clean end waits for the workers; an interrupted one cancels what has
        # not started and does not block on what has — each worker's own job
        # object takes its engine down with it.
        pool.shutdown(wait=clean, cancel_futures=not clean)
    record["seconds"] = round(time.monotonic() - started, 1)
    record["row_seconds"] = round(record["row_seconds"], 1)
    return record


def resumable(picture: Path) -> bool:
    """Whether a full-resolution picture already on disk can be reused.

    Selection is deterministic from the candidate log, so a relaunch picks the
    same rows and any complete picture is the picture this run would have made. A
    truncated mid-write victim is removed here rather than left for the render to
    overwrite, so "already there" cannot mean "half there".
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
    "THREADS_ENV",
    "Result",
    "Task",
    "engine_threads_for",
    "parity",
    "render_task",
    "resumable",
    "run_pass",
]
