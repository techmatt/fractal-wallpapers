"""The only interface to the Rust renderer.

Every pixel in this project is made by the `fractal-engine` binary. No other
Python module invokes it, imports a renderer, or computes image data itself:
if Python needs pixels, it calls through here and gets back a field or an
image path. Keeping the boundary in one file is what lets the engine change
(new fractal family, new precision, GPU backend) without touching Python.
"""

from __future__ import annotations

from pathlib import Path

ENGINE_BINARY_NAME = "fractal-engine"


def engine_path() -> Path:
    """Return the path to the built engine binary."""
    raise NotImplementedError("engine binary discovery is not implemented yet")


def render(spec: dict) -> Path:
    """Render one viewport described by `spec` and return the output path."""
    raise NotImplementedError("rendering is not implemented yet")
