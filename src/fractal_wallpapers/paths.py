"""Where things are, and what an unfinished file is called while it is being made.

One definition of "the repository root", because two would eventually disagree.
Everything else in this package addresses files relative to it, so a checkout
works wherever it is cloned and whatever the working directory happens to be.

## Three roots, and two of them are the same tree

The repository holds what matters — records, labels, weights, code — and it is
small enough to clone without thinking. The `artifacts/` tree holds what a run
can always make again: tile caches, location views, render caches, the pictures
a study looked at. That tree grows to a hundred gigabytes, which is more than a
system drive wants to carry, so it is a *setting* rather than a place.

It is two settings, because the disk it moved to turned out to be a USB hard
drive and a hard drive is not a peer of an SSD. A pass over the tile cache is
about an hour of pure seeking there against four minutes on NVMe. So:

* the **hot root** is where work happens and where every write lands. Default:
  `artifacts/` under the checkout, which is what CI and a fresh clone get and is
  why neither has to know any of this exists;
* the **archive root** is slow bulk storage for what is finished with. Optional:
  a machine that has no second disk simply does not set it.

A top-level name of the tree lives in **exactly one** tier, and its tier is
simply where it physically sits — there is no registry of what is archived,
because a registry is a second answer that drifts away from the first one.
Reading resolves hot first and falls back to the archive; the same name present
in both tiers is refused rather than silently preferred, because a stale copy
that quietly wins is the one failure a two-tier store can have that nobody sees.
`storage archive` and `storage restore` move a name between the tiers.

## Records name the tree, never the disk

Because the roots are settings, records that name a file under the tree are
written in the tree's own terms — `artifacts/tiles/...`, never a drive letter —
and read back through `rehome`, which re-addresses a stored name against
wherever that name lives now. A record that spelled out one machine's disk would
be a record the next machine cannot use, and that is exactly the failure this
pair of functions exists to make impossible. It is also why archiving a subtree
disturbs nothing: a tracked name says nothing about which tier the bytes are on,
so a ledger name that is a sidecar's join key survives the move.

## Presence means complete

The other thing here is one naming convention, and it is here because two callers
need it and neither owns the other: every picture this project makes is written
to a temporary and renamed into place, so **a file's presence means it is
complete**. A release row and a location's canonical view both learned that the
hard way — the first from a deadline kill that left a decodable but unfinished
picture the resume counted as done, the second because its cache is addressed by
the digest of a recipe and nothing would ever re-make a truncated entry.

That convention is load-bearing twice over now: tier resolution asks whether a
name is *there*, and a half-copied subtree that answered yes would be a tier
answer that is wrong. It is why `storage` copies, verifies and only then deletes.
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

#: The two keys `local.toml` carries, and the environment variables that override
#: them. The variables are what a test and a one-off invocation use; the file is
#: what a machine uses, because a setting that has to be exported into every
#: shell is a setting a scheduled run silently does without.
HOT_ROOT_KEY = "hot_root"
HOT_ROOT_VARIABLE = "FRACTAL_WALLPAPERS_HOT_ROOT"
ARCHIVE_ROOT_KEY = "archive_root"
ARCHIVE_ROOT_VARIABLE = "FRACTAL_WALLPAPERS_ARCHIVE_ROOT"

#: The single-root name this pair replaced, refused rather than ignored. A
#: machine that still spells the old key is a machine that meant to put the tree
#: somewhere, and quietly reading nothing would send its next build to the
#: checkout — the same silent fallback `ArtifactsRootMissing` exists to prevent,
#: arriving through the settings file instead of through an unplugged disk.
RETIRED_ROOT_KEY = "artifacts_root"
RETIRED_ROOT_VARIABLE = "FRACTAL_WALLPAPERS_ARTIFACTS_ROOT"

#: What each tier is called wherever one is printed or recorded.
HOT = "hot"
ARCHIVE = "archive"


class StorageRefusal(RuntimeError):
    """Something about *where the tree is* stopped a command, not what it asked for.

    One base class because `cli.main` catches it once for every subcommand: these
    are refusals about the machine, and any command that touches the regenerable
    tree can raise any of them.
    """


class ArtifactsRootMissing(StorageRefusal):
    """A configured root is somewhere this machine cannot see it.

    An external disk that is not plugged in. Raised rather than fallen back from:
    the fallback would be an empty `artifacts/` under the checkout, and every
    cache in this project reads *absence* as "not built yet". A silent fallback
    would therefore not look like a missing disk. It would look like a hundred
    gigabytes of work that had never been done, and the next command would
    cheerfully start doing it again on the wrong drive.
    """


class ArchiveUnreachable(ArtifactsRootMissing):
    """The archive is configured, absent, and a name could only be answered there.

    The narrow half of the refusal above. With the archive unplugged, a name the
    hot tier holds is answered from the hot tier and nothing complains — hot-only
    work proceeds. A name the hot tier does *not* hold cannot be answered at all:
    "not built yet" and "on the disk you unplugged" are the same observation from
    here, and only one of them is safe to act on.
    """


class TierCollision(StorageRefusal):
    """One name, two tiers. Which copy is authoritative is now a guess.

    Never resolved by preferring a tier. Whichever one lost would go on being
    written to or read past in silence, and the two would drift until some
    number came out wrong months later.
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


def local_settings() -> dict:
    """This machine's settings, or an empty mapping where it has none.

    Read fresh every time rather than cached. Caching would mean a process that
    started with a disk unplugged could never be told it is plugged in now, and
    the answer costs one small file read.
    """
    settings_path = local_settings_path()
    if not settings_path.is_file():
        return {}
    return tomllib.loads(settings_path.read_text(encoding="utf-8"))


def refuse_the_retired_root(settings: dict) -> None:
    """Refuse a machine still configured with the single root these two replaced."""
    stated = (
        (
            f"the {RETIRED_ROOT_VARIABLE} environment variable",
            os.environ.get(RETIRED_ROOT_VARIABLE),
        ),
        (f"{RETIRED_ROOT_KEY} in {LOCAL_SETTINGS_NAME}", settings.get(RETIRED_ROOT_KEY)),
    )
    for where, value in stated:
        if value:
            raise ArtifactsRootMissing(
                f"{where} still names {value}, and one root is no longer what this reads. "
                f"The tree has two tiers now: {HOT_ROOT_KEY} is where work happens and every "
                f"write lands, {ARCHIVE_ROOT_KEY} is slow bulk storage for what is finished "
                "with. Say which of those that path is and delete the old name. Nothing is "
                "assumed for you: guessing hot would put a hundred gigabytes of cache behind "
                "a seek-bound disk, and guessing archive would hide every write from itself."
            )


def configured_root(key: str, variable: str) -> tuple[Path, str] | None:
    """`(root, where it was configured)`, or `None` where nothing configures it.

    The variable wins over the file when it is *set*, which includes being set to
    nothing: an empty value is how a shell — or a test — says "this machine has
    no such root", overriding a file that says otherwise. Absent from the
    environment entirely is a different statement and defers to the file.
    """
    settings = local_settings()
    refuse_the_retired_root(settings)
    stated = os.environ.get(variable)
    if stated is not None:
        if not stated.strip():
            return None
        return Path(stated), f"the {variable} environment variable"
    value = settings.get(key)
    if not value:
        return None
    return Path(str(value)), f"{key} in {LOCAL_SETTINGS_NAME}"


def hot_root() -> Path:
    """Where work happens and every write lands: the setting, or `artifacts/` here.

    Refuses a configured root that is not there. See `ArtifactsRootMissing` for
    why refusing beats falling back. The default is *not* checked for existence:
    an unmade `artifacts/` in a fresh checkout is a directory the first command
    creates, not a disk somebody forgot.
    """
    configured = configured_root(HOT_ROOT_KEY, HOT_ROOT_VARIABLE)
    if configured is None:
        return repo_root() / ARTIFACTS_NAME
    root, source = configured
    if not root.is_dir():
        raise ArtifactsRootMissing(
            f"the hot root is set to {root} by {source}, and no directory is there. "
            "If that is an external disk, plug it in; if the tree has moved, change the "
            "setting. Nothing falls back to the checkout: an empty tree at the default "
            "would read as a cache that was never built, and the next build would spend "
            "hours filling the wrong drive."
        )
    return root


def archive_root() -> Path | None:
    """Slow bulk storage for finished subtrees, or `None` on a machine without one.

    Unlike the hot root this does not refuse when it is absent, because absent is
    the ordinary state of a USB disk and most work never reaches it. The refusal
    moved to where it can be narrow: `Tiers.unit`, which knows whether the name
    being asked about is one only the archive could answer for.
    """
    configured = configured_root(ARCHIVE_ROOT_KEY, ARCHIVE_ROOT_VARIABLE)
    return None if configured is None else configured[0]


class Tiers:
    """Which tier each top-level name of the regenerable tree is in, right now.

    A *snapshot*: one instance reads the settings once and remembers what it
    found about each name it was asked about. That is for the caller re-homing a
    million manifest rows, which would otherwise stat two disks per row — the
    same reason `rehome` used to take an already-resolved root. Everything else
    calls `Tiers.current()` per question and pays one small file read for an
    answer that is never stale.

    The unit of tiering is a **top-level name**, not a file. It is what the
    `storage` commands move, it is what "a subtree lives in exactly one tier"
    means, and it is what makes resolution cost one lookup per subtree rather
    than one per file.
    """

    def __init__(self, hot: Path, archive: Path | None) -> None:
        self.hot = Path(hot)
        self.archive = None if archive is None else Path(archive)
        self._known: dict[str, Path] = {}

    @classmethod
    def current(cls) -> Tiers:
        """The tiers as this machine is configured this second."""
        return cls(hot_root(), archive_root())

    @property
    def archive_is_reachable(self) -> bool:
        """Whether the archive is configured *and* the disk holding it is here."""
        return self.archive is not None and self.archive.is_dir()

    def tier_of(self, unit: str) -> str | None:
        """`HOT`, `ARCHIVE`, or `None` for a name neither tier holds.

        Raises `TierCollision` where both do, because there is no true answer.
        """
        hot_here = (self.hot / unit).exists()
        cold_here = self.archive_is_reachable and (self.archive / unit).exists()
        if hot_here and cold_here:
            raise TierCollision(
                f"{ARTIFACTS_NAME}/{unit} is in both tiers: {self.hot / unit} and "
                f"{self.archive / unit}. One authoritative copy at a time is the whole rule "
                "here, and preferring one silently is how the other goes on being read or "
                "written for months. Compare them and delete the one that is not the truth."
            )
        if hot_here:
            return HOT
        if cold_here:
            return ARCHIVE
        return None

    def unit(self, unit: str) -> Path:
        """Where one top-level name of the tree actually is.

        A name in neither tier resolves **hot**: it does not exist yet, and what
        does not exist yet is made where writes land.
        """
        remembered = self._known.get(unit)
        if remembered is not None:
            return remembered
        hot_here = self.hot / unit
        if self.archive is not None and not self.archive.is_dir():
            if hot_here.exists():
                self._known[unit] = hot_here
                return hot_here
            raise ArchiveUnreachable(
                f"{ARTIFACTS_NAME}/{unit} is not in the hot tier ({self.hot}), and the "
                f"archive that could hold it — {self.archive} — is not there. Plug it in. "
                "Nothing falls back: from here an archived subtree and a cache nobody has "
                "built yet look exactly alike, and acting on the wrong one rebuilds tens of "
                "gigabytes that already exist. Work whose names are all hot is unaffected; "
                f"setting {ARCHIVE_ROOT_VARIABLE} to nothing says this machine has no "
                "archive at all, and stops it being consulted."
            )
        where = self.tier_of(unit)
        resolved = hot_here if where != ARCHIVE else self.archive / unit
        self._known[unit] = resolved
        return resolved

    def place(self, unit: str, where: Path) -> None:
        """Pin one name's tier in this snapshot, overriding what the disks say.

        Exactly one caller: the move in `storage`, verifying a copy while the
        source it is about to delete is still on disk. Asked fresh, that name is
        in both tiers and `tier_of` would refuse it for a collision — which is
        the right answer to every question except this one, where the collision
        is the move itself and the destination is the copy being checked.
        """
        self._known[unit] = Path(where)

    def resolve(self, parts) -> Path:
        """A relative name inside the tree, addressed against the tier that holds it."""
        named = [str(part) for part in parts if str(part) not in ("", ".")]
        if not named:
            return self.hot
        return self.unit(named[0]).joinpath(*named[1:])

    def names(self) -> list[str]:
        """Every top-level name either tier holds, sorted, without duplicates.

        The archive is skipped when it is not reachable rather than refused: the
        callers listing names are `storage status` and the walk over every
        ledger, and both would rather show what is here than nothing at all. What
        they must not do is show a half list *silently*, so both ask
        `archive_is_reachable` and say so.
        """
        found = {entry.name for entry in self.hot.iterdir()} if self.hot.is_dir() else set()
        if self.archive_is_reachable:
            found |= {entry.name for entry in self.archive.iterdir()}
        return sorted(found)


def under(*parts) -> Path:
    """A path inside the regenerable tree, on whichever tier its subtree is on.

    The one funnel every module names a place through: nothing builds a path out
    of a root and a string, because then nothing would find the archive.
    """
    return Tiers.current().resolve(parts)


def rehome(stored, tiers: Tiers | None = None) -> Path | None:
    """A path recorded under *an* artifacts tree, re-addressed against this one.

    Records under the tree name the files they made — a tile manifest names each
    of a million tiles — and they name them as the run that wrote them saw them.
    Move the tree and every one of those names points at nothing. So a stored
    name is read as *the part below the artifacts root*, and joined onto wherever
    that part lives now; both spellings a record can carry, the relative
    `<tree>/<rest>` and one machine's absolute path, reduce to the same answer,
    and so does the same name before and after its subtree was archived.

    `None` where the stored name has no artifacts component: that is not a name
    this function knows anything about, and the caller keeps whatever it had.
    Returning `None` rather than the input is what makes that distinguishable —
    a path handed back through `Path` would come back re-spelled in the local
    separator, which is a silent edit to a record's own bytes.

    `tiers` is for a caller re-homing many rows at once, so a batch resolves the
    settings once and each subtree's tier once instead of once per row.
    """
    parts = PurePosixPath(str(stored).replace("\\", "/")).parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ARTIFACTS_NAME:
            here = Tiers.current() if tiers is None else tiers
            return here.resolve(parts[index + 1 :])
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

    A file under either tier of the regenerable tree is the case where "outside
    the checkout" is not the same as "somewhere else". Wherever that tree has
    been put, and whichever tier this subtree currently sits on, it is the same
    tree, so it is named `<tree>/<rest>` — the spelling a record carried when the
    tree sat in the checkout, and the spelling `rehome` reads back. That is not
    cosmetic: a ledger's name is the key curation's sidecar stores its rows
    under, and a name that changed when the subtree was archived would leave
    every stored row unmatchable and silently un-replaced.
    """
    path = Path(path)
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        pass
    for root in (hot_root(), archive_root()):
        if root is None:
            continue
        try:
            below = resolved.relative_to(Path(root).resolve())
        except (OSError, ValueError):
            continue
        return (PurePosixPath(ARTIFACTS_NAME) / below.as_posix()).as_posix()
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
