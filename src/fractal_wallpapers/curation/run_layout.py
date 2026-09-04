"""Where a release run's regenerable files go, and at what size it draws them.

This is here rather than in [`curation.run`] because of who asks. `run` is the
release pass's wiring — a thousand lines that import a dozen modules and drive an
engine — and six modules that have nothing to do with running a pass were
importing all of it for `run_dir`: the ledger's picture resolver, the re-score
path, the below-bar sheet, the expressed census, the rejection leg and the two
re-render checks. Every one of them wants to *name a file a past run wrote*,
which is a fact about the layout and not about the pass.

So the layout is its own module, it imports [`paths.under`] and nothing else, and
`curation.run` is now imported by the command that runs a pass and by nothing
else. That is the shape an orchestrator is supposed to have: a leaf of the import
graph rather than a shared header.

**This is the regenerable side and it is deliberately not beside
[`curation.records`].** `records` owns where a run's *tracked* rows go, under
`data/curation/`; a run's pictures and caches are on the artifacts tier, resolved
through `under()` so they follow the subtree to whichever disk holds it. Reading
those two layouts out of one module is how a tracked file ends up written to the
regenerable tree, or the reverse — the mistake `src/fractal_wallpapers/README.md`
describes closing twice.
"""

from __future__ import annotations

from pathlib import Path

from fractal_wallpapers.paths import under

#: What a release picture is rendered at. Read by the two checks that re-render a
#: shipped row and compare — a parity check that drew at another size would be
#: measuring the size.
RELEASE_RESOLUTION = (2560, 1440)
RELEASE_SUPERSAMPLE = 4


def run_dir(run: str) -> Path:
    """Where a run's pictures and caches live. Ignored, and regenerable."""
    return under("curation", "runs", str(run))
