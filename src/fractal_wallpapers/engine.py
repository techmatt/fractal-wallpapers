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

from fractal_wallpapers.paths import repo_root

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


def render_report(spec: dict) -> dict:
    """Render one viewport and return the engine's record of what it did.

    The report echoes the location's decimal strings back unchanged and fills in
    whatever the spec left open, so it — not the spec — is the thing worth
    writing to a record.
    """
    done = subprocess.run(
        [str(engine_path()), "render"],
        input=json.dumps(spec),
        capture_output=True,
        text=True,
        cwd=repo_root(),
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError(f"engine failed: {done.stderr.strip() or done.stdout.strip()}")
    return json.loads(done.stdout)


def render(spec: dict) -> Path:
    """Render one viewport described by `spec` and return the output path."""
    return Path(render_report(spec)["output"])
