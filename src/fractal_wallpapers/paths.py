"""Where things are, and what an unfinished file is called while it is being made.

One definition of "the repository root", because two would eventually disagree.
Everything else in this package addresses files relative to it, so a checkout
works wherever it is cloned and whatever the working directory happens to be.

The other thing here is one naming convention, and it is here because two callers
need it and neither owns the other: every picture this project makes is written
to a temporary and renamed into place, so **a file's presence means it is
complete**. A release row and a location's canonical view both learned that the
hard way — the first from a deadline kill that left a decodable but unfinished
picture the resume counted as done, the second because its cache is addressed by
the digest of a recipe and nothing would ever re-make a truncated entry.
"""

from __future__ import annotations

from pathlib import Path

#: What an unfinished file is called. The extension stays last, because the
#: engine chooses its image format from it: `0000.png.writing` would be a JPEG.
WRITING_INFIX = ".writing"


def repo_root() -> Path:
    """Return the repository root, found by walking up from this file."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("could not locate the repository root")


def colormap_dir() -> Path:
    """Return the directory holding the tracked colormap files."""
    return repo_root() / "data" / "palettes"


def tracked_name(path) -> str:
    """A path as a **tracked** record may carry it: relative, forward slashes.

    A record git keeps that names one machine's drive letter and home directory
    means nothing on the machine that reads it next — and every acceptance
    record here names the bar it was read against. A path outside the checkout
    is left as it is, spelled with forward slashes, because rewriting it would
    be inventing a location rather than recording one.
    """
    path = Path(path)
    try:
        return path.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def writing_path(output: Path) -> Path:
    """Where a file is built before it becomes the file at `output`."""
    output = Path(output)
    return output.with_name(f"{output.stem}{WRITING_INFIX}{output.suffix}")


def sweep_writing(directory: Path) -> int:
    """Delete every abandoned temporary under `directory`. Returns how many.

    A killed process runs no `finally`, so the sweep is a caller's job at the
    point where partial output is discarded rather than a promise made at the
    point where it is written.
    """
    victims = [
        path
        for path in sorted(Path(directory).rglob(f"*{WRITING_INFIX}.*"))
        if path.is_file() and path.stem.endswith(WRITING_INFIX)
    ]
    for path in victims:
        path.unlink(missing_ok=True)
    return len(victims)


def anchors_file() -> Path:
    """Return the tracked record of anchor locations.

    A handful of places worth rendering that are known to say something: they
    are what a change to the engine gets compared at, so they are written down
    rather than retyped.
    """
    return repo_root() / "data" / "anchors.jsonl"
