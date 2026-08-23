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
"""

from __future__ import annotations

#: Every head this project trains, and therefore every head a release has to
#: carry. A release cut from a manifest that is missing one is a clone that
#: cannot run that head at all, and the only way to notice is to have written
#: the roster down somewhere a check can read it.
#:
#: **Three, not four.** `render` replaced `smooth_render` and `strange_render` on
#: 2026-08-23: one judge over both kinds, adopted on a non-inferiority band. The
#: two LABEL STORES keep their names and their paths — a store is a corpus and
#: those did not merge — so the old names still appear wherever they name stored
#: data. They are gone from the roster because a roster names what ships.
HEADS = ("location", "render", "palette")

__all__ = ["HEADS"]
