"""The seam a scorer arrives through, and the location head that arrived.

A walk consults a scorer twice: to *steer* — which survivors are worth expanding
next — and to *admit* — which survivors are worth recording as finds. Both are
questions about pictures, and for a long time nothing in this repository could
answer them, so the seam was built and the answer was null.

The answer is no longer null. [`LocationScorer`] renders each survivor's
canonical view and reads it through the shipped location head, and the walk
writes what the head said onto the ledger row. That closes a loop the first
production run left open: the machine leg of the standing deficit reads each
row's own `score`, so a harvest under the null scorer moved the books by exactly
zero — twenty-two thousand rows, every one `unclassed`, and a second run would
have computed the identical allocation and stalled in the identical place.

Three properties of the seam are worth stating.

* **A scorer sees a candidate, not a location.** It is handed the row the walk
  is about to record and returns a reading. It cannot move the frame, reject it
  on anything but the score, or write to the ledger, so a scorer swap cannot
  quietly change what the gates did.
* **`None` is a first-class answer and means "no opinion".** A candidate whose
  view could not be rendered carries a reason rather than a zero, because a
  crashed render and a bad location must not be the same number.
* **A reading carries both cutpoints.** `P(≥3)` decides admission at the keeper
  floor and `P(≥4)` is what separates a class 4 from a class 3 in the currency,
  which weights the two ten to one. A seam that carried only the scalar would
  make every machine-classed find a 3 forever.

## Scoring is the expensive half, and fanning it out does not pay

A canonical view costs about half a second of engine, against a harvest that
finds locations several times faster, so the obvious move is to render the views
in worker **processes** on the release pass's pattern. That pool is built here,
it is held to the serial path by [`parity`], and its default is **one worker**,
because the measurement says the fan-out loses:

```text
36 views, 12 logical CPUs           views/s
serial, engine takes the machine      1.82
3 workers x 4 engine threads          0.88
3 workers x unbounded threads         1.30
6 workers x 2 engine threads          0.84
```

The reason is not overhead — a trivial engine call costs 5.5 ms, so process
spawn is a rounding error on a half-second render. It is that **one 640×360
render already parallelizes across the whole machine.** Splitting twelve threads
between three engines is the same total work with three sets of ramp-up, and
oversubscribing them is the same work with contention. There is nothing here for
concurrency to recover; the only thing that would change the answer is a machine
with more cores than one view can use, and that is a measurement to re-take
rather than a constant to guess.

The pool stays for that day, and because a claim that concurrency does not pay is
worth being able to re-run. Three properties hold whichever arm runs:

* **workers render, the parent decides.** A worker is handed a resolved recipe
  and an output path and returns a picture on disk. It never loads a head, never
  names a file and never touches the ledger. The parent alone runs the head, in
  one batch, and hands the readings back in the order the candidates were given —
  which is what makes the pooled path's ledger *identical* to the serial path's
  rather than merely equivalent.
* **the serial path is not a branch of the concurrent one.** `workers <= 1`
  renders in this process, and the two are held to each other by [`parity`] on a
  real batch rather than by construction.
* **no torch in a worker.** A spawned worker that imported the training stack
  would pay seconds of start-up to do a job that is pure engine, and the head
  reads a batch of pictures far faster on one device than on four.

Views are addressed by the digest of their own recipe and shared with curation's
re-score, so a location scored during a harvest is not rendered a second time
when the intake reads it again.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fractal_wallpapers.models import location_view

#: Worker processes a scoring pass uses by default: **one**, which is the serial
#: path in this process.
#:
#: Measured, not assumed, and the measurement went the other way from the guess —
#: see the module docstring. A view render already spends the whole machine, so
#: every fan-out arm was slower than this one. `--score-workers N` is how the
#: measurement gets re-taken on a machine where that stops being true.
DEFAULT_WORKERS = 1

#: What each scoring worker's engine is told to use above one worker, passed
#: explicitly rather than inherited. A fair share of a twelve-thread machine at
#: three workers — deliberately a *share* and not an over-provision, because
#: these renders are compute-bound with no idle half for a sibling to fill, which
#: is exactly why the fan-out does not pay in the first place.
ENGINE_THREADS_PER_WORKER = 4

#: The environment variable the engine's thread pool reads.
THREADS_ENV = "RAYON_NUM_THREADS"


def engine_threads_for(workers: int) -> int | None:
    """Per-engine threads for `workers` engines; `None` at one, where there is no
    fan-out and the engine keeps its own default."""
    return None if workers <= 1 else ENGINE_THREADS_PER_WORKER


@dataclass(frozen=True)
class Reading:
    """What a scorer says about one candidate.

    `score` is the head's `P(≥3)` — the number every floor in this project is a
    point on — and `great` is its `P(≥4)`, which is a different question and the
    one the currency's ten-to-one weighting reads. `error` is set when there was
    no picture to ask about, so a failed render is a stated fact rather than a
    silent absence of opinion.

    `probabilities` is every cutpoint the head emitted, `P(≥2)` first — the two
    named fields are the two the walk spends, and a *tier* is not derivable from
    either of them alone. The labeling rig decodes one, so the whole vector
    travels rather than being read a second way out of a second call.
    """

    score: float | None = None
    great: float | None = None
    error: str | None = None
    probabilities: tuple = ()


#: The reading a scorer with nothing to say hands back.
NO_OPINION = Reading()


class Scorer(Protocol):
    """What the walk asks of a judge of pictures."""

    #: Recorded on every row, so a ledger says which judge produced its scores.
    name: str

    def score(self, candidate: dict) -> float | None:
        """A number for this candidate, or `None` for no opinion.

        Higher is better. The single-candidate door, kept because the labelling
        rig orders a sheet through it; the walk uses [`read`].
        """

    def read(self, candidates: list[dict]) -> list[Reading]:
        """One reading per candidate, in the order they were given.

        The batch door, because the expensive part of an opinion is a render and
        renders fan out. A scorer that has nothing to say returns a list of
        [`NO_OPINION`] and costs nothing.
        """

    def admits(self, candidate: dict, score: float | None) -> bool:
        """Whether this candidate is a find worth *booking* as one.

        Called only for candidates that already passed every structural gate,
        so a scorer that admits everything is the structural-gates-only policy.
        """

    def expandable(self, candidate: dict, score: float | None) -> bool:
        """Whether the walk may continue from this candidate.

        The other half of [`admits`], and deliberately a lower bar. Booking
        decides what the census counts; this decides what the frontier stands on,
        and a frontier that may only stand on its own admissions shrinks at any
        pass rate below one over the branching factor. Every admission is
        expandable — no scorer may answer `False` here and `True` there.
        """


class NullScorer:
    """No opinion about anything: structural gates decide, and nothing else.

    Kept, and not as dead code. It is what a walk on a machine with no weights
    runs, what the tests walk under, and what every ledger written before the
    head arrived was produced by — so a mixed corpus stays readable and the
    `scorer` field on a row says which of the two wrote it.
    """

    name = "null"

    def score(self, candidate: dict) -> float | None:
        del candidate
        return None

    def read(self, candidates: list[dict]) -> list[Reading]:
        return [NO_OPINION for _ in candidates]

    def admits(self, candidate: dict, score: float | None) -> bool:
        del candidate, score
        return True

    def expandable(self, candidate: dict, score: float | None) -> bool:
        del candidate, score
        return True


# --------------------------------------------------------------------------- #
# The renders, fanned out.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ViewTask:
    """One canonical view to make. Everything in it survives a spawn pickle.

    The `recipe` is resolved and the `output` is named **by the parent**, so a
    worker cannot decide what picture it is making or where it goes — which is
    what makes the two arms of [`parity`] comparable at all.
    """

    recipe: dict
    output: str


@dataclass(frozen=True)
class ViewResult:
    """What one view came out as. Never an exception: a failed view is a recorded one."""

    output: str
    ok: bool
    seconds: float = 0.0
    error: str | None = None


def render_view(task: ViewTask) -> ViewResult:
    """Render one canonical view. Never raises.

    Written to a temporary and renamed, so a file in the cache means a *finished*
    view. The cache is addressed by the digest of the recipe and shared with
    curation's re-score, so a view truncated by a kill would not be re-made by
    anything — it would be handed to the head, for the life of the cache.
    """
    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.models import renders

    started = time.monotonic()
    try:
        output = Path(task.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        scratch = paths.writing_path(output)
        scratch.unlink(missing_ok=True)
        engine.run("render", renders.spec_of(task.recipe, scratch))
        scratch.replace(output)
        return ViewResult(task.output, True, time.monotonic() - started)
    except Exception as failure:  # noqa: BLE001 — a failed view is a recorded view
        return ViewResult(task.output, False, time.monotonic() - started, repr(failure)[:400])


def _worker(task: ViewTask) -> ViewResult:
    """The pooled unit. Module level and picklable by name — a spawned worker
    resolves it by name, so it cannot be a closure or a method."""
    return render_view(task)


def _worker_init(threads, quiet: bool) -> None:
    from fractal_wallpapers import process_control

    if threads is not None:
        os.environ[THREADS_ENV] = str(int(threads))
    priority = process_control.set_background_priority()
    cleanup = process_control.bind_children_to_parent()
    if not quiet:
        print(
            f"[score worker {os.getpid()}] threads={os.environ.get(THREADS_ENV)} "
            f"priority={priority} cleanup={cleanup}",
            flush=True,
        )


def render_views(tasks, workers: int, log=print, quiet: bool = True) -> list[ViewResult]:
    """Render every task and return the results **in the order given**.

    A worker that dies takes the pool's outstanding futures with it, so the
    remaining views are made serially in the parent rather than lost: half a
    scored batch is a worse outcome than a slow one, and a walk whose ledger is
    missing scores for an arbitrary suffix of a batch is a ledger nobody can
    reconcile. The fallback announces itself.
    """
    tasks = list(tasks)
    workers = max(1, int(workers))
    if not tasks:
        return []
    if workers <= 1:
        return [render_view(task) for task in tasks]

    pool = ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_worker_init,
        initargs=(engine_threads_for(workers), quiet),
    )
    out: list[ViewResult] = []
    clean = False
    try:
        futures = [pool.submit(_worker, task) for task in tasks]
        for index, future in enumerate(futures):
            try:
                out.append(future.result())
            except BrokenProcessPool as broken:
                rest = tasks[index:]
                log(
                    f"[score] POOL BROKEN ({broken!r}) - rendering the remaining "
                    f"{len(rest)} view(s) serially in the parent rather than dropping them"
                )
                out.extend(render_view(task) for task in rest)
                clean = True
                return out
            except Exception as failure:  # noqa: BLE001
                out.append(ViewResult(tasks[index].output, False, 0.0, repr(failure)[:400]))
        clean = True
    finally:
        pool.shutdown(wait=clean, cancel_futures=not clean)
    return out


# --------------------------------------------------------------------------- #
# The head.
# --------------------------------------------------------------------------- #
class LocationScorer:
    """The shipped location head, reading every candidate a walk admits.

    The head is loaded on the **first batch that needs it**, not in the
    constructor: a walk whose frontier is empty, or a run that stalls before its
    first expansion, should not pay for a model it never asks anything.

    The views live in one cache shared with curation's re-score, because a view is
    addressed by the digest of its own recipe: the same location scored twice by
    two stages is one file and one render.
    """

    def __init__(
        self,
        *,
        directory: Path | None = None,
        workers: int = DEFAULT_WORKERS,
        device: str = "auto",
        batch_size: int = 64,
        log=print,
    ):
        self.directory = Path(directory) if directory is not None else view_dir()
        self.workers = max(1, int(workers))
        self.device = device
        self.batch_size = int(batch_size)
        self.log = log
        self.colormap = location_view.canonical_map()
        self.cyclic = location_view.cyclic_maps()
        self._head = None
        self.tally = {"read": 0, "rendered": 0, "reused": 0, "failed": 0, "render_seconds": 0.0}
        # Everything that can refuse is resolved **here**, not on the first batch:
        # the shipped artifact, its hash, and the stack that reads it. A harvest
        # is an unattended six-hour program, and a refusal it discovers an hour in
        # is a refusal it discovers with a ledger already half written.
        self._stamp = self.resolve_stamp()

    def resolve_stamp(self) -> str:
        """The sha256 of the artifact this scorer is, or a refusal saying why not."""
        import importlib.util

        from fractal_wallpapers.curation import floors
        from fractal_wallpapers.models import ship

        stamp = floors.live_stamp("location")
        checkpoint = ship.shipped_path("location")
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"{checkpoint} is not on this machine, so nothing can score what a walk finds. "
                f"Run `fractal-wallpapers fetch-weights`."
            )
        if importlib.util.find_spec("torch") is None:
            raise ModuleNotFoundError(
                "torch is not installed, so the location head cannot be read. Install the "
                "models extra, or walk on the structural gates alone."
            )
        return stamp

    @property
    def name(self) -> str:
        """The judge a ledger row names: the head, and the artifact it was."""
        return f"location:{self._stamp[:12]}"

    def stamp(self) -> str:
        return self._stamp

    def head(self):
        """`(model, config, device)` — loaded once, on first use."""
        if self._head is None:
            from fractal_wallpapers.models import scoring as scoring_module
            from fractal_wallpapers.models import ship

            self._head = scoring_module.load(ship.shipped_path("location"), self.device)
            self.log(
                f"[score] location head on {self._head[2]}, {self.workers} render worker(s) "
                f"at {THREADS_ENV}={engine_threads_for(self.workers)}"
            )
        return self._head

    # ------------------------------------------------------------- the seam

    def score(self, candidate: dict) -> float | None:
        """One candidate's `P(≥3)`. The batch door is [`read`]; this is the
        single-candidate one the protocol keeps."""
        return self.read([candidate])[0].score

    def read(self, candidates: list[dict]) -> list[Reading]:
        """Render every candidate's canonical view and read the batch through the head."""
        candidates = list(candidates)
        if not candidates:
            return []
        wanted, tasks = [], []
        pictures: list[Path | None] = []
        errors: list[str | None] = []
        for candidate in candidates:
            path = location_view.view_path(candidate, self.colormap, self.cyclic, self.directory)
            pictures.append(path)
            errors.append(None)
            if path.is_file():
                self.tally["reused"] += 1
                continue
            wanted.append(len(pictures) - 1)
            tasks.append(
                ViewTask(location_view.view_row(candidate, self.colormap, self.cyclic), str(path))
            )

        for index, result in zip(wanted, render_views(tasks, self.workers, self.log), strict=True):
            self.tally["render_seconds"] += result.seconds
            if result.ok:
                self.tally["rendered"] += 1
            else:
                self.tally["failed"] += 1
                pictures[index] = None
                errors[index] = result.error

        return self._readings(pictures, errors)

    def _readings(self, pictures, errors) -> list[Reading]:
        """The head over every view that exists, put back in the given order."""
        from fractal_wallpapers.models import scoring as scoring_module
        from fractal_wallpapers.models import train

        made = [(index, path) for index, path in enumerate(pictures) if path is not None]
        out = [
            Reading(None, None, error or "no view was rendered for this candidate")
            for error in errors
        ]
        if not made:
            return out
        model, config, where = self.head()
        classes = int(config["classes"])
        transform = scoring_module.transform_of(config)

        def through(paths, size):
            return train.score(model, paths, transform, where, classes, {"batch_size": size})

        paths = [path for _, path in made]
        try:
            probabilities = list(through(paths, self.batch_size))
        except Exception as failure:  # noqa: BLE001
            # One unreadable picture fails the whole batch, and a harvest is an
            # unattended program: retry alone so the damage is one row with a
            # reason rather than a run that stops six hours in.
            self.log(f"[score] batch of {len(paths)} would not read ({failure!r}) - one at a time")
            probabilities = []
            for path in paths:
                try:
                    probabilities.append(through([path], 1)[0])
                except Exception as alone:  # noqa: BLE001
                    probabilities.append(repr(alone)[:400])

        for (index, _path), probability in zip(made, probabilities, strict=True):
            if isinstance(probability, str):
                out[index] = Reading(None, None, probability)
                self.tally["failed"] += 1
                continue
            out[index] = Reading(
                float(probability[1]),
                float(probability[2]) if classes > 3 else None,
                None,
                tuple(float(value) for value in probability),
            )
            self.tally["read"] += 1
        return out

    def admits(self, candidate: dict, score: float | None) -> bool:
        """The keeper floor, which is the admission the supply engine already means.

        `supply.currency.passes_good_floor` owns that comparison for the census,
        the intake's slot guarantee and the ledger union's own admission
        predicate; asking it here is what makes "admitted" one word. A candidate
        below it is **recorded**, with the fate its score earned — record and
        rank, never gate and forget.
        """
        from fractal_wallpapers.supply import currency

        del candidate
        return currency.passes_good_floor(score)

    def expandable(self, candidate: dict, score: float | None) -> bool:
        """The junk floor, which is the same number curation spends compute on.

        `curation.floors.JUNK_FLOOR` owns it, and it is the *same* point on the
        *same* head's scale: "the judge is confident this is junk". A place the
        judge is merely unenthusiastic about is a place worth standing on, and
        expanding from it costs one engine call rather than a colorize.
        """
        from fractal_wallpapers.curation import floors

        del candidate
        return floors.passes_junk_floor(score)

    def summary(self) -> dict:
        return {
            "head": "location",
            "head_sha256": self.stamp(),
            "workers": self.workers,
            "engine_threads": engine_threads_for(self.workers),
            "view": location_view.summary(self.colormap),
            "view_dir": str(self.directory),
            **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in self.tally.items()},
        }


def view_dir() -> Path:
    """Where the pictures the location head is read on live. Ignored, re-derivable."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "artifacts" / "location_views"


# --------------------------------------------------------------------------- #
# The check.
# --------------------------------------------------------------------------- #
def parity(candidates: list[dict], workers: int, directory: Path, log=print) -> dict:
    """Render one real batch of views both ways and compare the bytes and the scores.

    The claim the pooled path makes is not "equivalent scores" but *the same
    file*, and the only way to know is to make both. Each candidate's view is
    rendered once in the parent and once through the pool, into two directories,
    and both are read through the head — so a disagreement is attributable to the
    render or to the read rather than to either by elimination.
    """
    import hashlib

    directory = Path(directory)
    arms: dict = {}
    for arm, count in (("serial", 1), ("concurrent", max(2, int(workers)))):
        where = directory / arm
        scorer = LocationScorer(directory=where, workers=count, log=log)
        log(f"[parity] {len(candidates)} view(s), {arm} at {count} worker(s), into {where}")
        started = time.monotonic()
        readings = scorer.read(candidates)
        arms[arm] = {
            "seconds": round(time.monotonic() - started, 1),
            "scorer": scorer.summary(),
            "rows": [
                {
                    "score": None if reading.score is None else round(reading.score, 12),
                    "great": None if reading.great is None else round(reading.great, 12),
                    "error": reading.error,
                    "sha256": (
                        hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                    ),
                }
                for reading, path in zip(
                    readings,
                    [
                        location_view.view_path(row, scorer.colormap, scorer.cyclic, where)
                        for row in candidates
                    ],
                    strict=True,
                )
            ],
        }

    disagreed = [
        index
        for index, (one, two) in enumerate(
            zip(arms["serial"]["rows"], arms["concurrent"]["rows"], strict=True)
        )
        if one != two
    ]
    return {
        "rows": len(candidates),
        "identical": len(candidates) - len(disagreed),
        "disagreed": disagreed,
        "held": not disagreed and bool(candidates),
        "arms": arms,
    }


__all__ = [
    "DEFAULT_WORKERS",
    "ENGINE_THREADS_PER_WORKER",
    "NO_OPINION",
    "THREADS_ENV",
    "LocationScorer",
    "NullScorer",
    "Reading",
    "Scorer",
    "ViewResult",
    "ViewTask",
    "engine_threads_for",
    "parity",
    "render_view",
    "render_views",
    "view_dir",
]
