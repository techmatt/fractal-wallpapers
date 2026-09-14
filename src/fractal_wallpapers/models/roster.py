"""Which heads exist. Three strings, and nothing that knows how to run one.

The roster is the one fact about the judges that something outside `models/`
has to read. `fetch-weights --check` is the dry run a release is cut after, and
what it does is manifest JSON, a file stat and a sha256 — stdlib work, run by a
fresh clone that installed the base package and nothing else. It still has to
know which heads a complete release carries, and asking `ship` for that name
would hand a stdlib check the whole training stack: torch, timm, numpy, two
gigabytes of CUDA wheels, to read a tuple of three strings.

So the roster lives here and `ship` imports it, rather than the other way
around. The dependency arrow points from the heavy module to the light one,
which is the only direction that keeps the check runnable where it is run — and
this is the one module under `models/` that a base install can import.

[`manifest_path`] is here for the same argument and it arrived later, by the same
route. The file it names is the one `--check` reads, and it had **two**
derivations: `ship.manifest_path()` and a `Path("models") / "weights.json"` of
`cli.weights_commands`' own — because reaching for `ship` from the stdlib-only
path is exactly what the roster exists to avoid, so the command that needs it
most could not use it. It is one function here, `ship` imports it beside `HEADS`,
and [`fractal_wallpapers.cuts`] reads it without importing the training stack:
naming which artifact is shipped right now is a question about the manifest, not
about the code that writes it.
"""

from __future__ import annotations

from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: Every head this project trains, and therefore every head a release has to
#: carry. A release cut from a manifest that is missing one is a clone that
#: cannot run that head at all, and the only way to notice is to have written
#: the roster down somewhere a check can read it.
#:
#: **`render` replaced `smooth_render` and `strange_render`** on 2026-08-23: one
#: judge over both kinds, adopted on a non-inferiority band. The two LABEL STORES
#: keep their names and their paths — a store is a corpus and those did not merge
#: — so the old names still appear wherever they name stored data. They are gone
#: from the roster because a roster names what ships.
#:
#: **`gallery_grade` is the fourth and arrived 2026-09-14.** It is the fine head,
#: whose `p_fine` gates the seating bar, the cascade order and every veto row's
#: reading, and until this it was *unobtainable at any price*: off this tuple, no
#: manifest row, its checkpoints untracked like every other head's and in no
#: release, so a clone could read its configs and its per-sheet scores and never
#: run it. That shut the whole scored half of this repository behind a head nobody
#: outside this machine could get.
#:
#: ⚠ **Its asset is k=3 checkpoints in ONE file**, which is a shape no other row
#: here has. The shipped recipe averages three seeds on the probability scale, so
#: no single file produces the column — `gallery_grade_train.export_fp16` writes
#: the members into one artifact and `load_shipped` reads them back, and a release
#: still carries one asset per head. The manifest row says `members` and `seeds`
#: for that reason.
HEADS = ("location", "render", "palette", "gallery_grade")


def manifest_path() -> Path:
    """The tracked manifest `fetch-weights` reads: which artifact each head ships."""
    return repo_root() / "models" / "weights.json"


__all__ = ["HEADS", "manifest_path"]
