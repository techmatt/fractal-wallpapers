"""The only interface to the Rust renderer.

Every pixel in this project is made by the `fractal-engine` binary. No other
Python module invokes it, imports a renderer, or computes image data itself:
if Python needs pixels, it calls through here and gets back a field or an
image path. Keeping the boundary in one file is what lets the engine change
(new fractal family, new precision, GPU backend) without touching Python.

The wire between the two halves is a JSON object on stdin and a JSON report on
stdout. That is a deliberate choice over an FFI binding: a spec is a value that
can be logged, diffed, replayed, and handed to the binary from a shell, and the
report that comes back is the record of what was actually rendered — including
the parameters Python left for the engine to decide, like the iteration cap.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import colormap_dir, repo_root

__all__ = [
    "DYNAMICAL_KINDS",
    "NICHE",
    "PARAMETER_KINDS",
    "PRODUCTION",
    "Bound",
    "EngineTimeout",
    "colormap_dir",
    "deadline",
    "dump_field",
    "engine_path",
    "expand",
    "home_view",
    "modes",
    "pixel_is_z0",
    "production_modes",
    "recolor",
    "render",
    "render_report",
    "run",
    "tiles",
]

ENGINE_BINARY_NAME = "fractal-engine"

#: Release first: a debug-built engine is ten times slower, so finding one is a
#: fallback for a fresh checkout, not a configuration.
BUILD_PROFILES = ("release", "debug")


def engine_path() -> Path:
    """Return the path to the built engine binary."""
    name = ENGINE_BINARY_NAME + (".exe" if sys.platform == "win32" else "")
    target = repo_root() / "engine" / "target"
    for profile in BUILD_PROFILES:
        candidate = target / profile / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"{name} is not built. Run: cargo build --release --manifest-path engine/Cargo.toml"
    )


class EngineTimeout(RuntimeError):
    """An engine call was killed for running past the deadline it was given."""


@dataclass
class Bound:
    """The deadline one block of engine calls is under, and whether it fired.

    Handed back by [`deadline`] so a caller can tell a unit that *failed* from a
    unit that was *killed*. Those are different facts about a run and a bare
    exception cannot carry the difference across a worker boundary.
    """

    seconds: float | None
    expired: bool = False


#: When the calls made in this process must be finished by, as a monotonic
#: instant, or `None` for the default: an engine call takes as long as it takes.
#: Process-wide because the deadline belongs to the *unit of work* the process is
#: in the middle of, and every engine call that unit makes is part of it.
_DEADLINE: float | None = None

#: The bounds currently open, innermost last, so an expiry can be reported to
#: every block that is waiting on it.
_BOUNDS: list[Bound] = []


@contextmanager
def deadline(seconds: float | None):
    """Bound every engine call made inside this block by one shared clock.

    A hung render is the realistic way a long run stops making progress, and it
    is not a thing the caller can interrupt: the wall clock disappears inside a
    subprocess that will never return. So the bound goes where the calls are made
    — one choke point, one timeout, the child killed by the same call that
    imposed it — rather than at each of the dozen places a picture is asked for.

    Nested blocks take the *earlier* of the two deadlines: an inner block may
    shorten what it is allowed, never lengthen it. `None` means unbounded, which
    stays the default: only a run that has promised to finish by a certain time
    has any business killing a render that would have succeeded.
    """
    global _DEADLINE
    previous = _DEADLINE
    until = None if seconds is None else time.monotonic() + max(0.0, float(seconds))
    if previous is not None:
        until = previous if until is None else min(previous, until)
    bound = Bound(None if seconds is None else float(seconds))
    _DEADLINE = until
    _BOUNDS.append(bound)
    try:
        yield bound
    finally:
        _BOUNDS.pop()
        _DEADLINE = previous


def _remaining() -> float | None:
    """Seconds an engine call may take, or `None` when nothing is bounding it."""
    return None if _DEADLINE is None else _DEADLINE - time.monotonic()


def _expire(subcommand: str, seconds: float) -> EngineTimeout:
    """Mark every open bound as fired and return the failure to raise."""
    for bound in _BOUNDS:
        bound.expired = True
    return EngineTimeout(
        f"engine {subcommand} was killed after {seconds:.1f}s: it ran past the deadline "
        f"the unit of work that started it was given"
    )


def run(subcommand: str, spec: dict | None = None, log: Path | None = None) -> Any:
    """Hand `spec` to one of the engine's subcommands and return its report.

    Every call into the engine goes through here, so there is one place that
    knows how a spec is delivered, one place that decides what a failure looks
    like from Python, and one place to change when either does.

    `log` sends the engine's progress to a file as it runs instead of holding it
    until the call returns. Most calls here take a second and want the message
    with the failure; a bulk build takes hours, and progress that only arrives at
    the end is not progress.

    Inside a [`deadline`] block the call is killed rather than waited on. The
    child dies with the timeout — `subprocess.run` kills it before it raises —
    and the engine starts no grandchildren, so there is nothing left behind.
    """
    command = [str(engine_path()), subcommand]
    text = "" if spec is None else json.dumps(spec)
    remaining = _remaining()
    if remaining is not None and remaining <= 0:
        raise _expire(subcommand, 0.0)
    started = time.monotonic()
    try:
        if log is None:
            done = subprocess.run(
                command,
                input=text,
                capture_output=True,
                text=True,
                cwd=repo_root(),
                check=False,
                timeout=remaining,
            )
            if done.returncode != 0:
                raise RuntimeError(f"engine failed: {done.stderr.strip() or done.stdout.strip()}")
            return json.loads(done.stdout)

        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            done = subprocess.run(
                command,
                input=text,
                stdout=subprocess.PIPE,
                stderr=handle,
                text=True,
                cwd=repo_root(),
                check=False,
                timeout=remaining,
            )
    except subprocess.TimeoutExpired:
        raise _expire(subcommand, time.monotonic() - started) from None
    if done.returncode != 0:
        raise RuntimeError(f"engine failed; its progress and error are in {log}")
    return json.loads(done.stdout)


def render_report(spec: dict) -> dict:
    """Render one viewport and return the engine's record of what it did.

    The report echoes the location's decimal strings back unchanged and fills in
    whatever the spec left open, so it — not the spec — is the thing worth
    writing to a record.
    """
    return run("render", spec)


def render(spec: dict) -> Path:
    """Render one viewport described by `spec` and return the output path."""
    return Path(render_report(spec)["output"])


def dump_field(spec: dict) -> dict:
    """Write the raw scalar field a render would have colored.

    Takes the same spec `render` does, and writes the field named by `output`
    plus a record beside it. Refused for the colorings that have no single
    scalar field behind them — the composites and the direct traps.
    """
    return run("dump-field", spec)


def recolor(spec: dict) -> dict:
    """Color a dumped field again, without iterating anything.

    Everything geometric comes from the dump's own record, so a spec that names
    only the field and where to write reproduces the render it came from; naming
    a colormap or a transform is what makes it an exploration.
    """
    return run("recolor", spec)


def expand(spec: dict) -> dict:
    """Take one rung of a walk from each of a batch of nodes.

    The one call the discovery half makes. It hands over places and a policy and
    gets back every candidate the engine drew, each with the gate that refused
    it or a thumbnail if none did — so the walk's own code never renders, never
    measures a field, and never has to agree with the engine about what a gate
    means.
    """
    return run("expand", spec)


def tiles(spec: dict, log: Path | None = None) -> dict:
    """Turn a plan of locations into training tiles, and report what was written.

    One iteration pass per location, every tile a colored crop of it. The whole
    recipe — how many tiles, how far they may be shifted and zoomed, which
    colormaps they may draw — is the engine's, so this side names the locations
    and reads back the record rather than restating a single constant of it.
    """
    return run("tiles", spec, log=log)


def home_view(family: dict) -> dict:
    """Where this family is framed when nothing says otherwise.

    The engine's `Family::home_view` table is the **only** owner of framing in
    this project, and this is the door to it. Python keeps no literal of its own:
    a duplicate is a thing that agrees with the engine until the day someone
    moves a row, and the day that happened a phoenix walk root saw two thirds of
    its set.

    Returns the three decimal strings a viewport is written in, so what comes
    back can be recorded and re-rendered exactly as the engine wrote it.
    """
    return json.loads(_home_view(json.dumps(family, sort_keys=True)))["viewport"]


@cache
def _home_view(key: str) -> str:
    """One subprocess per distinct family, for the whole process.

    A walk asks for a home view once per root and a refill once per draw, which
    is thousands of times for a handful of distinct families. The table is a
    constant of the binary, so the answer is cached on the family the question
    was asked about — keyed and returned as text because that is what a cache
    can hold safely.
    """
    return json.dumps(run("home-view", {"schema": 1, "family": json.loads(key)}))


#: The family kinds whose pixel is `z₀` — the dynamical planes. Every other kind
#: the engine renders reads the pixel as `c`.
#:
#: The engine's `Family::pixel_is_z0` is the owner of this split and this is the
#: only mirror of it on this side. A mirror rather than a door because the answer
#: is needed *per row* while building a render spec, and a subprocess per row is
#: not a thing a plan of eight thousand pictures can afford. What keeps the two
#: honest is a test, not a comment: `test_modes` resolves `itinerary` through the
#: engine over one family of every kind and checks the coloring against the one
#: this side built.
DYNAMICAL_KINDS = frozenset({"julia", "phoenix"})

#: The kinds whose pixel is the constant `c`: the parameter planes.
PARAMETER_KINDS = frozenset({"mandelbrot", "multibrot"})


def pixel_is_z0(family: dict) -> bool:
    """Whether this family reads the pixel as `z₀` rather than as `c`.

    The dynamical/parameter split, asked as one question, because two things now
    turn on it and both would otherwise re-derive it from a list of family names.
    Refused rather than defaulted for a kind nobody registered: guessing here puts
    a differently-addressed picture on record under a name that says otherwise.
    """
    kind = (family or {}).get("kind")
    if kind in DYNAMICAL_KINDS:
        return True
    if kind in PARAMETER_KINDS:
        return False
    raise ValueError(
        f"family kind {kind!r} is not one the engine renders, so which plane it is on cannot "
        f"be read. The kinds are {sorted(DYNAMICAL_KINDS | PARAMETER_KINDS)}."
    )


#: A mode a production draw may pick. The corpora were collected over these, and
#: the finished-render judges were trained on them.
PRODUCTION = "production"

#: A mode that is renderable on demand by name and excluded from every production
#: draw. Niche because it is expensive, unproven at scale, or interesting rather
#: than good — never because it is broken, which would keep it out of the catalog.
NICHE = "niche"


def modes() -> list[dict]:
    """List the named colorings the engine knows, with what each is for.

    The catalog lives in the engine — one list, so a mode cannot exist on one
    side of the boundary and not the other. Each entry carries its `tier`; a
    caller that *draws* a mode wants [`production_modes`] instead of this.
    """
    return run("modes")


def production_modes() -> list[str]:
    """Every mode a production draw may pick, in catalog order.

    **The one place the tier is enforced on this side of the boundary.** A caller
    that draws a mode reads this rather than filtering [`modes`] itself, so "a
    production draw cannot yield a niche mode" is a property of one function
    instead of a rule every draw site has to remember — which is the same reason
    the catalog itself lives in the engine and not here.
    """
    return [mode["name"] for mode in modes() if mode["tier"] == PRODUCTION]
