"""Cross-run memory: the walk stops re-buying ground earlier runs already walked.

Every run before this one started with no memory of where its predecessors went.
A basin three runs had already worked ranked exactly like untouched territory, and
the frontier bought it again.

**The memory is the ledgers.** Every walk already records, durably and per run,
every place it confirmed. Loading them costs a fraction of a second and a query
costs microseconds, so nothing here justifies a second store that could drift from
the one that already exists — and there is nothing to maintain, nothing that can
go stale, and nothing to migrate when the scorer is retrained.

```text
priority  ×=  1 / (1 + STRENGTH × density)
density    =  prior visits v with dist(candidate, v) ≤ RADIUS × v.width,
              in the same partition AND at the same parameter identity
```

**Soft, never exclusionary.** The discount falls to `1/(1+n)` at `n` shadowing
visits and reaches zero only in the limit, so a saturated region is strongly
disfavoured and still reachable: a partition whose entire frontier is saturated
keeps picking its best candidate rather than stalling. A subtracted penalty would
be unbounded below, and "saturated" would eventually mean "unreachable".

**Scale-aware on the *visit's* frame, not the candidate's.** A visit at width `w`
shadows a disc of radius `RADIUS × w` centred on itself. A deep confirmation
shadows almost nothing; a whole-set one shadows a neighbourhood. One run passing
through a wide frame does not exhaust what is inside it, but a hundred deep
confirmations in one basin do exhaust that basin.

**Identity-aware, and this is load-bearing.** Inside a Julia or Phoenix partition
the coordinate is a point of the *dynamical* plane, so two views at the same place
with different parameters are different fractals. A coordinate-only index reads a
twin partition as half shadowed where the true answer is a tenth, and reads
another as shadowed at all where nothing has ever been visited twice — it would
discount exactly the channels the next run exists to serve.

**No quality filter, no deduplication, no decay.** A place that was checked and
rejected was still visited: the descent spent its budget there. And "is it any
good" is a cut on a score whose meaning moves with the scorer, so a
quality-filtered memory would silently re-shape itself at every retrain. Regions
do not un-exhaust either; the answer to "that was a while ago" is a different
channel, not a half-life.

**Scope: the order of one partition's candidates, and nothing else.** Roots are
exempt, reframings are exempt, and which *partition* is served is untouched — the
quota picks that from queue lengths and standing deficits, so a per-candidate
discount cannot move the mix.

**The radius is set against a share, not by taste.** The failure mode is a term
that fires at full strength on nearly every candidate, which subtracts a
near-constant from every priority and reorders nothing. So the bar is: at most a
few percent of candidates may be *saturated* — within a tenth of the full
discount — pooled, and at most a tenth of them in any one partition. The adopted
radius is the round value comfortably inside that, not the largest value that
squeaks past it.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from fractal_wallpapers.supply import ledgers
from fractal_wallpapers.supply.location import IDENTIFYING_CONSTANTS, canonical
from fractal_wallpapers.supply.partitions import partition_of_row

#: A visit at width `w` shadows a disc of radius `RADIUS × w` around itself.
RADIUS = 0.30

#: How hard the discount bites. Zero disables the mechanism entirely — priorities
#: come out byte-identical and no ledger is read.
STRENGTH = 1.0

#: A candidate is *saturated* when its discount is within a tenth of full, which
#: is `density ≥ 9` at unit strength. The share of a population that is saturated
#: is what the radius is calibrated against.
SATURATED_DENSITY = 9


def discount(density: float, strength: float = STRENGTH) -> float:
    """The soft saturation discount, `1 / (1 + strength × density)`."""
    if strength <= 0.0 or density <= 0.0:
        return 1.0
    return 1.0 / (1.0 + strength * float(density))


def identity_of(family: dict) -> tuple:
    """The parameter identity a partition's coordinates are read against.

    The family's constants as canonical decimal strings — exact, with no
    tolerance, because that is what they are. A parameter-plane family has no
    constants and therefore one identity, which is right: there is only one
    parameter plane per degree.
    """
    names = IDENTIFYING_CONSTANTS.get(family.get("kind"), ())
    return tuple(
        None if family.get(name) is None else tuple(canonical(v) for v in family[name])
        for name in names
    )


class VisitedIndex:
    """How many prior visits shadow a point, per partition and identity.

    Built once at the start of a run and never mutated: this is *cross*-run
    memory, and the current run's own coverage is a different thing. A frozen
    index is also what makes a resume rebuild the identical memory.

    One uniform grid per (partition, identity, width octave). A visit in octave
    `o = ⌊log₂ w⌋` has radius `RADIUS·w ≤ RADIUS·2^(o+1)`, which is that octave's
    cell size — so every disc covering a query point has its centre inside the
    three-by-three block of cells around that point, and the scan is exact rather
    than approximate.
    """

    def __init__(self, radius: float = RADIUS):
        if not float(radius) > 0.0:
            raise ValueError(f"radius multiple must be positive; got {radius!r}")
        self.radius = float(radius)
        self._cells: dict = {}
        self._octaves: dict = {}
        self.visits = 0
        self.unusable = 0
        self.per_partition: Counter = Counter()
        self.sources: list[str] = []

    def _cell_size(self, octave: int) -> float:
        return self.radius * (2.0 ** (octave + 1))

    def add(self, partition: str, identity: tuple, center_re, center_im, width) -> bool:
        """Register one visit.

        Returns `False`, and counts it, for a row that cannot be placed. Counted
        rather than raised: a ledger spans every schema the project has ever
        written, and one unusable legacy row must not take a run's start-up down —
        but a silently dropped population is how a memory quietly becomes empty.
        """
        try:
            x, y, w = float(center_re), float(center_im), float(width)
        except (TypeError, ValueError):
            self.unusable += 1
            return False
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(w) and w > 0.0):
            self.unusable += 1
            return False
        key = (partition, identity)
        octave = math.floor(math.log2(w))
        size = self._cell_size(octave)
        cell = (octave, math.floor(x / size), math.floor(y / size))
        self._cells.setdefault(key, {}).setdefault(cell, []).append((x, y, (self.radius * w) ** 2))
        self._octaves.setdefault(key, set()).add(octave)
        self.visits += 1
        self.per_partition[partition] += 1
        return True

    def add_row(self, row: dict) -> bool:
        """Register one ledger row."""
        viewport = row.get("viewport") or {}
        family = row.get("family")
        if not isinstance(family, dict) or not viewport:
            self.unusable += 1
            return False
        return self.add(
            partition_of_row(row),
            identity_of(family),
            viewport.get("center_re"),
            viewport.get("center_im"),
            viewport.get("width"),
        )

    def density(self, partition: str, identity: tuple, center_re, center_im) -> int:
        """How many prior visits shadow this point in this partition and identity."""
        key = (partition, identity)
        cells = self._cells.get(key)
        if not cells:
            return 0
        x, y = float(center_re), float(center_im)
        found = 0
        for octave in self._octaves[key]:
            size = self._cell_size(octave)
            i0, j0 = math.floor(x / size), math.floor(y / size)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for vx, vy, r2 in cells.get((octave, i0 + di, j0 + dj), ()):
                        if (x - vx) ** 2 + (y - vy) ** 2 <= r2:
                            found += 1
        return found

    def density_scanned(self, partition: str, identity: tuple, center_re, center_im) -> int:
        """The definition, scanned linearly — the statement the index accelerates.

        Kept here rather than in the test so the calibration and the test share one
        referent, and so the index is pinned against a definition rather than
        against a second implementation.
        """
        cells = self._cells.get((partition, identity))
        if not cells:
            return 0
        x, y = float(center_re), float(center_im)
        return sum(
            1
            for bucket in cells.values()
            for (vx, vy, r2) in bucket
            if (x - vx) ** 2 + (y - vy) ** 2 <= r2
        )

    def summary(self) -> dict:
        """What went into the memory. A memory whose size nobody can read
        afterwards is a memory nobody can tell was empty."""
        return {
            "radius": self.radius,
            "visits": self.visits,
            "unusable_rows": self.unusable,
            "partitions": dict(sorted(self.per_partition.items())),
            "identity_buckets": len(self._cells),
            "ledgers": len(self.sources),
        }


def build(radius: float = RADIUS, root: Path | None = None, exclude: Path | None = None):
    """The cross-run memory, straight off the committed ledgers.

    Every recorded candidate is a visit — survivors and refusals alike — for the
    reason in the module docstring: a place that was checked was visited.
    """
    paths = ledgers.ledger_paths(root, exclude)
    index = VisitedIndex(radius)
    index.sources = [str(path) for path in paths]
    for path in paths:
        for row in ledgers.rows(path, kind="candidate"):
            index.add_row(row)
    return index


__all__ = [
    "RADIUS",
    "SATURATED_DENSITY",
    "STRENGTH",
    "VisitedIndex",
    "build",
    "discount",
    "identity_of",
]
