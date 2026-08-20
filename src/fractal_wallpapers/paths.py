"""Where things are, and what an unfinished file is called while it is being made.

One definition of "the repository root", because two would eventually disagree.
Everything else in this package addresses files relative to it, so a checkout
works wherever it is cloned and whatever the working directory happens to be.

Two roots, not one. The repository holds what matters — records, labels, weights,
code — and it is small enough to clone without thinking. The `artifacts/` tree
holds what a run can always make again: tile caches, location views, render
caches, the pictures a study looked at. That tree grows to a hundred gigabytes,
and on a machine whose system drive is smaller than that it belongs on another
disk. So the artifacts root is a *setting* — read from an untracked local file
or the environment, defaulting to `artifacts/` under the checkout, which is what
CI and a fresh clone get and is why neither has to know this exists.

Because it is a setting, records that name a file under it are written in the
tree's own terms — `artifacts/tiles/...`, never a drive letter — and read back
through `rehome`, which re-addresses a stored name against wherever the root is
now. A record that spelled out one machine's disk would be a record the next
machine cannot use, and that is exactly the failure this pair of functions
exists to make impossible.

The other thing here is one naming convention, and it is here because two callers
need it and neither owns the other: every picture this project makes is written
to a temporary and renamed into place, so **a file's presence means it is
complete**. A release row and a location's canonical view both learned that the
hard way — the first from a deadline kill that left a decodable but unfinished
picture the resume counted as done, the second because its cache is addressed by
the digest of a recipe and nothing would ever re-make a truncated entry.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path, PurePosixPath

#: What an unfinished file is called. The extension stays last, because the
#: engine chooses its image format from it: `0000.png.writing` would be a JPEG.
WRITING_INFIX = ".writing"

#: The directory the regenerable tree is called, wherever that tree actually
#: sits. It is the word records use to name a file under it, so it is also the
#: hinge `rehome` and `tracked_name` turn a stored name on.
ARTIFACTS_NAME = "artifacts"

#: The untracked, machine-local settings file, read from the repository root.
#: Absent in CI and in a fresh clone, which is the point: the default is the
#: behaviour everybody gets until somebody on one machine says otherwise.
LOCAL_SETTINGS_NAME = "local.toml"

#: The key `local.toml` carries, and the environment variable that overrides it.
#: The variable is what a test and a one-off invocation use; the file is what a
#: machine uses, because a setting that has to be exported into every shell is a
#: setting a scheduled run silently does without.
ARTIFACTS_ROOT_KEY = "artifacts_root"
ARTIFACTS_ROOT_VARIABLE = "FRACTAL_WALLPAPERS_ARTIFACTS_ROOT"


class ArtifactsRootMissing(RuntimeError):
    """The artifacts root is configured somewhere this machine cannot see it.

    An external disk that is not plugged in. Raised rather than fallen back from:
    the fallback would be an empty `artifacts/` under the checkout, and every
    cache in this project reads *absence* as "not built yet". A silent fallback
    would therefore not look like a missing disk. It would look like a hundred
    gigabytes of work that had never been done, and the next command would
    cheerfully start doing it again on the wrong drive.
    """


def repo_root() -> Path:
    """Return the repository root, found by walking up from this file."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("could not locate the repository root")


def local_settings_path() -> Path:
    """Where this machine's untracked settings live, whether or not it has any."""
    return repo_root() / LOCAL_SETTINGS_NAME


def configured_artifacts_root() -> tuple[Path, str] | None:
    """`(root, where it was configured)`, or `None` where nothing configures it.

    Asked fresh every time rather than cached. Caching would mean a process that
    started with the disk unplugged could never be told it is plugged in now, and
    the answer costs one small file read.
    """
    value = os.environ.get(ARTIFACTS_ROOT_VARIABLE)
    if value:
        return Path(value), f"the {ARTIFACTS_ROOT_VARIABLE} environment variable"
    settings_path = local_settings_path()
    if not settings_path.is_file():
        return None
    settings = tomllib.loads(settings_path.read_text(encoding="utf-8"))
    value = settings.get(ARTIFACTS_ROOT_KEY)
    if not value:
        return None
    return Path(str(value)), f"{ARTIFACTS_ROOT_KEY} in {LOCAL_SETTINGS_NAME}"


def artifacts_root() -> Path:
    """The root of the regenerable tree: the setting, or `artifacts/` in the checkout.

    Refuses a configured root that is not there. See `ArtifactsRootMissing` for
    why refusing beats falling back.
    """
    configured = configured_artifacts_root()
    if configured is None:
        return repo_root() / ARTIFACTS_NAME
    root, source = configured
    if not root.is_dir():
        raise ArtifactsRootMissing(
            f"the artifacts root is set to {root} by {source}, and no directory is there. "
            "If that is an external disk, plug it in; if the tree has moved, change the "
            "setting. Nothing falls back to the checkout: an empty tree at the default "
            "would read as a cache that was never built, and the next build would spend "
            "hours filling the wrong drive."
        )
    return root


def rehome(stored, root: Path | None = None) -> Path | None:
    """A path recorded under *an* artifacts tree, re-addressed against this one.

    Records under the tree name the files they made — a tile manifest names each
    of a million tiles — and they name them as the run that wrote them saw them.
    Move the tree and every one of those names points at nothing. So a stored
    name is read as *the part below the artifacts root*, and joined onto wherever
    the root is now; both spellings a record can carry, the relative
    `<tree>/<rest>` and one machine's absolute path, reduce to the same answer.

    `None` where the stored name has no artifacts component: that is not a name
    this function knows anything about, and the caller keeps whatever it had.
    Returning `None` rather than the input is what makes that distinguishable —
    a path handed back through `Path` would come back re-spelled in the local
    separator, which is a silent edit to a record's own bytes.

    `root` is for a caller re-homing many rows at once, so a batch resolves the
    setting once instead of once per row.
    """
    parts = PurePosixPath(str(stored).replace("\\", "/")).parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ARTIFACTS_NAME:
            here = artifacts_root() if root is None else Path(root)
            return here.joinpath(*parts[index + 1 :])
    return None


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

    A file under the artifacts root is the case where "outside the checkout" is
    not the same as "somewhere else". Wherever that root has been put, the tree
    below it is the same tree, so it is named `<tree>/<rest>` — the spelling a
    record carried when the tree sat in the checkout, and the spelling `rehome`
    reads back. That is not cosmetic: a ledger's name is the key curation's
    sidecar stores its rows under, and a name that changed when the tree moved
    would leave every stored row unmatchable and silently un-replaced.
    """
    path = Path(path)
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        pass
    try:
        below = resolved.relative_to(artifacts_root().resolve())
    except (ArtifactsRootMissing, ValueError):
        return path.as_posix()
    return (PurePosixPath(ARTIFACTS_NAME) / below.as_posix()).as_posix()


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
