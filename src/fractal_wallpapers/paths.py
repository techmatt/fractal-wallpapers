"""Where things are.

One definition of "the repository root", because two would eventually disagree.
Everything else in this package addresses files relative to it, so a checkout
works wherever it is cloned and whatever the working directory happens to be.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root, found by walking up from this file."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("could not locate the repository root")


def colormap_dir() -> Path:
    """Return the directory holding the tracked colormap files."""
    return repo_root() / "data" / "palettes"
