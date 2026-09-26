"""The full set: every picture the Gallery tab shows, at 2560x1440 ss3, as JPEG.

The population is the kept records — [`tentative.kept`], the twenty-one the
explorer's Gallery tab reads — and a picture is one **recipe key**, not one seat:
eleven thousand seats name 6,299 distinct recipes, and a recipe seated by five
collections is drawn once. [`MEMBERSHIP_NAME`] is what says which collections seat
it, in which order, so a pack can be assembled from the one directory later.

## The render path is the verified one

`ss_cost_test_ckpt148` priced this population and checked the path it priced:
[`release.task_for`] into [`release.render_task`], with the **ledger** recipe and
the levelling curve the candidate lends upward ([`stamps.for_release`]). A render
lands as a PNG under [`WORK`], and the parent encodes it once with
[`votes.encode`] — the project's one JPEG encoder — at [`QUALITY`] and [`CHROMA`],
writes the explorer link back into the JPEG (Pillow does not carry a PNG's text
chunks into a JPEG), and renames the result into place. The engine's own JPEG
writer is the thumbnail writer, q90 at 4:2:0, and is not used for this.

**ss3 at q95 4:4:4, and why each.** ss4 priced at 80 wall hours over the set and
ss2 at 22, and ss2 moved every one of ten test pictures more than a q90 WebP pass
did — the dust-heavy seats grain visibly. ss3 is 9 samples a pixel against 16 and
4, and `fulls_ss3_ckpt148` checked it against ss4 on the same ten. q95 because
this is the full-resolution product and nothing downstream re-encodes it; 4:4:4
because a fractal's colour is its detail and 4:2:0 halves the colour resolution
of exactly the pixels that carry it.

## Resumable by construction

**A file named `<key>.jpg` in the output directory means that picture is done**,
and nothing else does. Every picture is made under [`WORK`] and renamed into
place, which is atomic on one volume, so a picture in the directory is a whole
one; a start deletes whatever [`WORK`] holds. [`PROGRESS_NAME`] is one row per
finished picture — key, seconds, bytes, a timestamp — and is for timing and the
report only: it is never asked what is done.

**One driver per directory.** [`LOCK_NAME`] is held through
[`process_control.hold`], an operating-system lock the process's death releases
however it dies, so a stale lock cannot exist; [`PID_NAME`] beside it names the
holder. A second `run` against a held directory refuses and names the pid, which
is what a resuming session attaches its waiter to.

**Pause is a file**, [`PAUSE_NAME`]: the gate [`run_pass`] asks before each row
declines, the rows in flight finish and are written, and the driver exits clean.
A start refuses while it exists, so resuming is deleting it and relaunching.
**An immediate stop is killing the driver's own pid**: it holds a kill-on-close
job ([`process_control.bind_children_to_parent`]) its workers and their engines
inherit, so they go with it, and whatever they had half made is only under
[`WORK`]. Never kill `fractal-engine.exe` by name.

## Order

The general n=1000 seats first, then the general n=2000, then the collections in
the keep list's order, each record in seat order — so a partial run is already
the general gallery, whole, before it is anything else.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.curation import release

#: The schema every row this module writes carries.
SCHEMA = 1

#: The geometry of the set: the full 2560x1440 frame at 3x3 samples a pixel.
REGIME = release.Regime((2560, 1440), 3)

#: The encode. q95 at full chroma resolution — see the module docstring.
QUALITY = 95
CHROMA = "444"

#: How long one row may take in the pool before it is killed. The slowest of the
#: ten priced rows was 93 s serial at ss4, which is about 55 s at ss3 and three
#: times that beside two siblings, so half an hour is ten times the worst seen.
DEADLINE = 1800.0

#: The deadline a failed row is retried under, once, at the end of a pass.
RETRY_DEADLINE = 3600.0

#: The names the output directory holds beside the pictures.
LOCK_NAME = "driver.lock"
PID_NAME = "driver.pid"
PAUSE_NAME = "PAUSE"
PROGRESS_NAME = "progress.jsonl"
FAILURES_NAME = "failures.jsonl"
MEMBERSHIP_NAME = "membership.jsonl"
WORK = "_work"

#: The two general records, which render first and in this order; every other
#: kept record is a collection and follows in the keep list's order.
FIRST = ("general", "general_n2000")


class FullSetRefused(RuntimeError):
    """The full set cannot be run against this directory now."""


class DriverRunning(FullSetRefused):
    """Another driver holds the directory. `pid` is the one it named, if it did."""

    def __init__(self, message: str, pid: int | None) -> None:
        super().__init__(message)
        self.pid = pid


def now() -> str:
    """A local timestamp with its offset, which is what a report quotes."""
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def membership() -> list[dict]:
    """One row per (collection, seat) over the kept records, **in render order**.

    `order` is the seat's place in its own record, from zero, and `seat` is the
    record's own seat number beside it.
    """
    from fractal_wallpapers.curation import tentative, viewers

    records = [
        (viewers.label_of(tentative.read_manifest(stamp)), stamp) for stamp in tentative.kept()
    ]
    rank = {name: index for index, name in enumerate(FIRST)}
    records.sort(key=lambda held: rank.get(held[0], len(FIRST)))
    out = []
    for collection, stamp in records:
        for order, row in enumerate(tentative.read_rows(stamp)):
            out.append(
                {
                    "schema": SCHEMA,
                    "collection": collection,
                    "stamp": stamp,
                    "order": order,
                    "seat": row.get("seat"),
                    "key": str(row["key"]),
                }
            )
    return out


def render_order(rows) -> list[str]:
    """The distinct keys of `rows`, each where it is first seated."""
    return list(dict.fromkeys(str(row["key"]) for row in rows))


def write_jsonl(path: Path, rows) -> Path:
    """Rows as JSONL, through a temporary renamed into place."""
    writing = path.with_name(path.name + ".writing")
    with writing.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    writing.replace(path)
    return path


def append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Rows of a log, skipping a killed run's half-written last line."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def done(out: Path) -> set[str]:
    """The keys whose picture is in the directory — the only record of what is done."""
    return {held.stem for held in Path(out).glob("*.jpg")}


# --------------------------------------------------------------------------- #
# The lock and the pause.
# --------------------------------------------------------------------------- #
def holder(out: Path) -> int | None:
    """The pid a driver of `out` wrote, or `None`. Says nothing about whether it lives."""
    try:
        return int((Path(out) / PID_NAME).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def running(out: Path) -> int | None:
    """The live driver's pid (0 if it named none), or `None` when nobody holds `out`.

    Asked by trying the lock: a lock this process can take is a lock nobody holds,
    and it is let go at once.
    """
    from fractal_wallpapers import process_control

    lock = Path(out) / LOCK_NAME
    if not lock.is_file():
        return None
    handle = process_control.hold(lock)
    if handle is not None:
        process_control.let_go(handle)
        return None
    return holder(out) or 0


def pause(out: Path) -> Path:
    """Ask the driver to stop after the rows in flight. The file it watches."""
    path = Path(out) / PAUSE_NAME
    path.write_text(f"paused at {now()}\n", encoding="utf-8", newline="\n")
    return path


def stop_now(out: Path) -> int | None:
    """Kill the live driver, and with it its workers and their engines. Its pid.

    Only a pid the **held** lock vouches for is killed: a pid file outlives its
    process, and the number in it may by now be somebody else's.
    """
    import signal

    pid = running(out)
    if not pid:
        return None
    os.kill(pid, signal.SIGTERM)
    return pid


@dataclass
class PauseGate:
    """The `leg` [`release.run_pass`] asks before each row: stop once `PAUSE` exists.

    It also carries the row deadline, which is the gate's to grant. `paused` says
    whether it ever declined, which is how the driver tells a paused pass from a
    finished one.
    """

    flag: Path
    deadline: float
    paused: bool = False
    seen: list[float] = field(default_factory=list)

    def may_start(self):
        if self.flag.exists():
            self.paused = True
            return f"{self.flag.name} is present"
        return None

    def timeout(self) -> float:
        return self.deadline

    def observe(self, seconds: float, ok: bool = True, expired: bool = False) -> None:
        if ok and not expired:
            self.seen.append(float(seconds))


# --------------------------------------------------------------------------- #
# One picture.
# --------------------------------------------------------------------------- #
def task_of(key: str, row: dict, borrowed: dict, work: Path) -> release.Task:
    """The verified path's task for one ledger row: ledger recipe, borrowed curve."""
    recipe = row.get("recipe") or {}
    if not recipe:
        raise FullSetRefused(f"{key} carries no recipe; there is nothing to render it from")
    return release.task_for(
        id=key,
        row=recipe,
        mode=recipe["mode"],
        colormap=recipe["colormap"],
        mode_params=recipe.get("mode_params"),
        curve=recipe.get("curve"),
        palette=recipe.get("palette"),
        autolevel=borrowed.get(key),
        output=work / f"{key}.png",
        geometry={**REGIME.geometry(), "maxiter": int(recipe["maxiter"])},
    )


def clear_work(work: Path, key: str) -> None:
    """Whatever one row left under [`WORK`]: its PNG, its levelled map, its temporaries."""
    for held in work.glob(f"{key}*"):
        if held.is_dir():
            shutil.rmtree(held, ignore_errors=True)
        else:
            held.unlink(missing_ok=True)


def finish(png: Path, out: Path, link: str | None) -> int:
    """Encode one finished render into place. The JPEG's byte count.

    Encoded under [`WORK`], stamped with its link there, and only then renamed
    into the output directory, so the name `<key>.jpg` never belongs to a partial
    file.
    """
    from PIL import Image

    from fractal_wallpapers.curation import embed_link, votes

    staged = png.with_suffix(".jpg")
    with Image.open(png) as image:
        votes.encode(image, staged, QUALITY, CHROMA)
    if link:
        embed_link.embed_file(staged, embed_link.query_of_url(link))
    final = Path(out) / staged.name
    staged.replace(final)
    return final.stat().st_size


# --------------------------------------------------------------------------- #
# The driver.
# --------------------------------------------------------------------------- #
def run(out: Path, workers: int = release.DEFAULT_WORKERS, log=print) -> dict:
    """Render every kept seat not yet in `out`, then retry the failures once.

    Refuses while [`PAUSE_NAME`] exists, and raises [`DriverRunning`] while
    another driver holds `out`.
    """
    from fractal_wallpapers import process_control

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    handle = process_control.hold(out / LOCK_NAME)
    if handle is None:
        pid = holder(out)
        raise DriverRunning(f"a driver already holds {out} (pid {pid})", pid)
    try:
        (out / PID_NAME).write_text(f"{os.getpid()}\n", encoding="utf-8", newline="\n")
        if (out / PAUSE_NAME).exists():
            raise FullSetRefused(f"{out / PAUSE_NAME} exists; delete it to resume")
        log(f"[full-set] driver {os.getpid()}: {process_control.bind_children_to_parent()}")
        return _run(out, workers, log)
    finally:
        (out / PID_NAME).unlink(missing_ok=True)
        process_control.let_go(handle)


def _run(out: Path, workers: int, log) -> dict:
    from fractal_wallpapers.curation import backfill, candidate_ledger, recipes
    from fractal_wallpapers.curation import stamps as stamps_module

    work = out / WORK
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    seated = membership()
    write_jsonl(out / MEMBERSHIP_NAME, seated)
    order = render_order(seated)
    finished = done(out)
    todo = [key for key in order if key not in finished]
    log(
        f"[full-set] {len(order)} pictures over {len(seated)} seats; {len(finished)} on disk, "
        f"{len(todo)} to render at {REGIME.spelled} q{QUALITY} {CHROMA}"
    )
    summary = {"total": len(order), "on_disk_at_start": len(finished), "planned": len(todo)}
    if not todo:
        return {**summary, "made": 0, "failed": [], "paused": False}

    rows = candidate_ledger.by_key(set(todo))
    borrowed = stamps_module.for_release(
        {key: rows[key] for key in todo if key in rows},
        backfill.read(),
        regime=recipes.CANDIDATE_REGIME.spelled,
        store="sequence",
    )
    log(f"[full-set] {len(borrowed)}/{len(todo)} inherit a levelling curve")

    failed: dict[str, str] = {}
    tasks = []
    for key in todo:
        try:
            if key not in rows:
                raise FullSetRefused(f"{key} is not in the candidate ledger")
            tasks.append(task_of(key, rows[key], borrowed, work))
        except (FullSetRefused, KeyError) as why:
            failed[key] = repr(why)
            row = {"schema": SCHEMA, "key": key, "error": repr(why), "attempt": 0, "at": now()}
            append(out / FAILURES_NAME, row)
    made = 0

    def sink(task, result, attempt: int) -> None:
        nonlocal made
        png = Path(task.output)
        error = result.error
        if result.ok:
            try:
                size = finish(png, out, result.info.get("link"))
                append(
                    out / PROGRESS_NAME,
                    {
                        "schema": SCHEMA,
                        "key": task.id,
                        "seconds": round(result.seconds, 2),
                        "bytes": size,
                        "at": now(),
                        "attempt": attempt,
                        "link": bool(result.info.get("link")),
                        "link_refused": result.info.get("link_refused"),
                    },
                )
                made += 1
                failed.pop(task.id, None)
            except Exception as why:  # noqa: BLE001 — a failed encode is a failed row
                error = f"encode: {why!r}"[:400]
        if error is not None:
            failed[task.id] = error
            append(
                out / FAILURES_NAME,
                {
                    "schema": SCHEMA,
                    "key": task.id,
                    "error": error,
                    "attempt": attempt,
                    "timed_out": result.timed_out,
                    "at": now(),
                },
            )
        clear_work(work, task.id)

    gate = PauseGate(out / PAUSE_NAME, DEADLINE)
    record = release.run_pass(tasks, workers, lambda t, r: sink(t, r, 1), log, leg=gate)
    retried: list[str] = []
    if not gate.paused:
        retry = [task for task in tasks if task.id in failed]
        retried = [task.id for task in retry]
        if retry:
            log(f"[full-set] retrying {len(retry)} failed row(s) once")
            gate = PauseGate(out / PAUSE_NAME, RETRY_DEADLINE)
            release.run_pass(retry, workers, lambda t, r: sink(t, r, 2), log, leg=gate)
    shutil.rmtree(work, ignore_errors=True)
    return {
        **summary,
        "made": made,
        "failed": [{"key": key, "error": error} for key, error in sorted(failed.items())],
        "retried": retried,
        "paused": gate.paused,
        "pass_seconds": record["seconds"],
    }


# --------------------------------------------------------------------------- #
# Where it stands.
# --------------------------------------------------------------------------- #
def status(out: Path, window: float = 3600.0) -> dict:
    """Pictures done out of the total, the recent rate and the projected finish.

    The rate is over the last `window` seconds of [`PROGRESS_NAME`], so a resumed
    run projects off how fast it is going now rather than its whole history.
    """
    out = Path(out)
    seated = read_jsonl(out / MEMBERSHIP_NAME)
    total = len(render_order(seated)) if seated else None
    on_disk = len(done(out))
    progress = read_jsonl(out / PROGRESS_NAME)
    stamped = [time.mktime(time.strptime(row["at"][:19], "%Y-%m-%dT%H:%M:%S")) for row in progress]
    recent = [at for at in stamped if at >= time.time() - window]
    rate = len(recent) / (window / 3600.0) if recent else None
    left = None if total is None else max(0, total - on_disk)
    finish_at = None
    if rate and left is not None:
        finish_at = time.strftime("%a %I:%M%p", time.localtime(time.time() + left / rate * 3600))
    return {
        "done": on_disk,
        "total": total,
        "per_hour": None if rate is None else round(rate, 1),
        "projected_finish": finish_at,
        "driver": running(out),
        "paused": (out / PAUSE_NAME).exists(),
        "failures_logged": len(read_jsonl(out / FAILURES_NAME)),
    }


__all__ = [
    "CHROMA",
    "DEADLINE",
    "FIRST",
    "MEMBERSHIP_NAME",
    "PAUSE_NAME",
    "PROGRESS_NAME",
    "QUALITY",
    "REGIME",
    "SCHEMA",
    "DriverRunning",
    "FullSetRefused",
    "PauseGate",
    "done",
    "finish",
    "membership",
    "pause",
    "render_order",
    "run",
    "running",
    "status",
    "stop_now",
    "task_of",
]
