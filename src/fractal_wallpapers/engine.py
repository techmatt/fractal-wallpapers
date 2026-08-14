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
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import colormap_dir, repo_root

__all__ = [
    "colormap_dir",
    "dump_field",
    "engine_path",
    "expand",
    "modes",
    "recolor",
    "render",
    "render_report",
    "run",
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


def run(subcommand: str, spec: dict | None = None) -> Any:
    """Hand `spec` to one of the engine's subcommands and return its report.

    Every call into the engine goes through here, so there is one place that
    knows how a spec is delivered, one place that decides what a failure looks
    like from Python, and one place to change when either does.
    """
    done = subprocess.run(
        [str(engine_path()), subcommand],
        input="" if spec is None else json.dumps(spec),
        capture_output=True,
        text=True,
        cwd=repo_root(),
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError(f"engine failed: {done.stderr.strip() or done.stdout.strip()}")
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


def modes() -> list[dict]:
    """List the named colorings the engine knows, with what each is for.

    The catalog lives in the engine — one list, so a mode cannot exist on one
    side of the boundary and not the other.
    """
    return run("modes")
