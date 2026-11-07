"""Which heads exist. A few strings, and nothing that knows how to run one.

The roster is the one fact about the judges that something outside `models/`
has to read. `fetch-weights --check` is the dry run a release is cut after, and
what it does is manifest JSON, a file stat and a sha256 — stdlib work, run by a
fresh clone that installed the base package and nothing else. It still has to
know which heads a complete release carries, and asking `ship` for that name
would hand a stdlib check the whole training stack: torch, timm, numpy, two
gigabytes of CUDA wheels, to read a tuple of strings.

So the roster lives here and `ship` imports it, rather than the other way
around. The dependency arrow points from the heavy module to the light one,
which is the only direction that keeps the check runnable where it is run — and
this is the one module under `models/` that a base install can import.

[`manifest_path`] is here for the same argument. The file it names is the one
`--check` reads, and the stdlib-only command that needs it most cannot reach for
`ship` to find it. So it is one function here: `ship` imports it beside `HEADS`,
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
#: **`render` is one judge over both kinds**, smooth and strange. The two LABEL
#: STORES keep the names `smooth_render` and `strange_render` and their paths — a
#: store is a corpus and those are two corpora — so those names appear wherever
#: they name stored data, and never here, because a roster names what ships.
#:
#: **`gallery_grade` is the fine head**, whose `p_fine` gates the seating bar, the
#: cascade order and every veto row's reading. A head off this tuple has no
#: manifest row and is in no release, so a clone could read its configs and its
#: per-sheet scores and never run it; the scored half of this repository needs
#: this one in the release like the rest.
#:
#: ⚠ **Its asset is k=3 checkpoints in ONE file**, which is a shape no other row
#: here has. The shipped recipe averages three seeds on the probability scale, so
#: no single file produces the column — `gallery_grade_train.export_fp16` writes
#: the members into one artifact and `load_shipped` reads them back, and a release
#: still carries one asset per head. The manifest row says `members` and `seeds`
#: for that reason.
HEADS = ("location", "render", "palette", "gallery_grade")


#: **The release every head ships in**, and there is one of it: one dated tag for
#: every head, so a clone's `fetch-weights` resolves one release to assemble one
#: set of judges (Matt's decision of 2026-09-14). **One package, one tag, one asset
#: per head.**
#:
#: **Dated rather than numbered, deliberately.** The version history of a head is
#: its `sha256` in [`manifest_path`] and that file's git history; a tag is a name
#: for a set of bytes somebody uploaded on a day. A number implies a sequence a
#: reader has to trace back, and says nothing about *which* heads are in it or
#: when.
#:
#: ⚠ **A published tag is NEVER moved.** A future change cuts a new dated tag and
#: rewrites these rows to point at it; it does not replace assets under this name.
#: That is the whole reason a clone can trust a sha256 it fetched last month — a
#: moved asset under a trusted name is the one failure a hash check cannot catch,
#: because the manifest that names the hash moves with it.
#:
#: It lives here rather than in `ship`, with [`HEADS`] and for [`HEADS`]' reason:
#: `fetch-weights` is stdlib-only and runs on a base install, and the tag is
#: something it has to be able to check without the training stack.
TAG = "weights-2026-09-14"


def manifest_path() -> Path:
    """The tracked manifest `fetch-weights` reads: which artifact each head ships."""
    return repo_root() / "models" / "weights.json"


__all__ = ["HEADS", "TAG", "manifest_path"]
