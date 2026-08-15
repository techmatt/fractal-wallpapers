"""Location groups: the unit a holdout is drawn on.

A train/evaluation split drawn over individual locations leaks. Two frames a
hair apart on the same plane are the same picture twice, and putting one on each
side of the boundary means the model is measured on something it was trained on.
So the split is drawn over **groups**, and a group is a connected component of
"these two would leak into each other".

Two locations are neighbours when all three of these hold:

* **They are the same plane, exactly.** Same partition, same degree, and every
  identifying constant *except* the seed `c` equal digit for digit.
* **Their seed `c` values are within [`C_TOLERANCE`]** of each other, for the
  families that have one.
* **Their frames overlap**: widths within a factor of [`NEIGHBOR_SCALE`], and
  centers within [`NEIGHBOR_SHIFT`] of the smaller width.

## Why the non-`c` axes are exact, and this is the whole rule

The source project grouped on the seed `c` alone. Phoenix has three parameter
pairs, and its five-hundred-row parameter sweep varied `p` and `z₋₁` at one fixed
viewport — so every row shared a `c` and a frame, and the grouping folded five
hundred *different fractals* into a single group. The holdout that came out of it
had five phoenix groups in it, and phoenix could not be calibrated at all.
Keying on the exact non-`c` axes gave a hundred and thirteen groups and made it
possible.

The failure is not phoenix's. **Any family swept at a fixed parameter point has
it available** — hold the frame still and vary a constant the grouping does not
read, and every row in the sweep collapses into one group. That is why the rule
is written as "every identifying constant except `c`, exactly" rather than as a
phoenix special case: a family registered tomorrow with a fourth constant is
grouped correctly without anyone remembering this.

The mirror failure is real too and is what the `c` tolerance is for. A ladder
that sweeps `c` at nearby frames produces neighbours that differ in the eighth
decimal place; grouping on an exact `c` would make each one its own group and put
near-identical pictures on opposite sides of the boundary. [`C_TOLERANCE`] is a
coarse constant rather than a measured distance, and it is deliberately generous:
over-grouping costs holdout granularity, under-grouping costs the instrument, and
only one of those is recoverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fractal_wallpapers.supply.location import IDENTIFYING_CONSTANTS, canonical
from fractal_wallpapers.supply.partitions import partition_of_family

#: The seed `c` distance below which two locations on one plane are treated as
#: the same picture. Absolute, in the parameter plane, which is three units
#: across at its home frame.
C_TOLERANCE = 1e-3

#: The widest ratio of frame widths that still counts as the same frame.
NEIGHBOR_SCALE = 1.5

#: How far two centers may sit apart, as a fraction of the smaller frame width.
NEIGHBOR_SHIFT = 0.5


def plane_of(family: dict) -> tuple:
    """THE exact-match half of the neighbour rule: what plane this is.

    Everything that decides which fractal is being drawn *except* the seed `c`,
    canonicalized so two spellings of one number are one plane.
    """
    kind = family.get("kind")
    constants = tuple(
        (name, None if family.get(name) is None else tuple(canonical(v) for v in family[name]))
        for name in IDENTIFYING_CONSTANTS.get(kind, ())
        if name != "c"
    )
    return (partition_of_family(family), int(family.get("degree", 2)), constants)


def _seed(family: dict) -> tuple[float, float] | None:
    """The seed `c` as floats, or `None` for a family that has no identifying one."""
    if "c" not in IDENTIFYING_CONSTANTS.get(family.get("kind"), ()):
        return None
    value = family.get("c")
    if value is None:
        return None
    return (float(value[0]), float(value[1]))


@dataclass
class _Place:
    plane: tuple
    seed: tuple | None
    center: tuple
    width: float


def _place(row: dict) -> _Place | None:
    family, viewport = row.get("family"), row.get("viewport")
    if not isinstance(family, dict) or not isinstance(viewport, dict):
        return None
    try:
        return _Place(
            plane=plane_of(family),
            seed=_seed(family),
            center=(float(viewport["center_re"]), float(viewport["center_im"])),
            width=float(viewport["width"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _neighbours(a: _Place, b: _Place) -> bool:
    """Whether these two places would leak into each other. The whole predicate."""
    if a.plane != b.plane:
        return False
    if a.seed is not None and b.seed is not None:
        dc_re, dc_im = a.seed[0] - b.seed[0], a.seed[1] - b.seed[1]
        if dc_re * dc_re + dc_im * dc_im > C_TOLERANCE * C_TOLERANCE:
            return False
    if not a.width or not b.width:
        return False
    ratio = a.width / b.width
    if ratio > NEIGHBOR_SCALE or ratio < 1.0 / NEIGHBOR_SCALE:
        return False
    tolerance = NEIGHBOR_SHIFT * min(a.width, b.width)
    dx, dy = a.center[0] - b.center[0], a.center[1] - b.center[1]
    return dx * dx + dy * dy <= tolerance * tolerance


class _Union:
    """Union-find, path-halving. Small enough to own rather than depend on."""

    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


@dataclass
class Grouping:
    """Dense group ids over a list of rows, and what could not be placed."""

    #: Group id per input row, `None` for a row with no location identity.
    of_row: list = field(default_factory=list)
    #: `{group id: [row index, ...]}`, in input order.
    members: dict = field(default_factory=dict)
    #: Rows that carry no location identity. Counted, never grouped.
    n_unplaced: int = 0

    def size(self) -> int:
        return len(self.members)

    def largest(self) -> int:
        return max((len(m) for m in self.members.values()), default=0)

    def summary(self) -> dict:
        sizes = sorted((len(m) for m in self.members.values()), reverse=True)
        return {
            "groups": len(sizes),
            "largest": sizes[0] if sizes else 0,
            "singletons": sum(1 for n in sizes if n == 1),
            "unplaced": self.n_unplaced,
        }


def assign(rows: list[dict]) -> Grouping:
    """Group `rows` into connected components under the neighbour rule.

    Comparison is confined to one plane at a time, and within a plane to pairs
    whose widths are already within [`NEIGHBOR_SCALE`] — which is what keeps a
    corpus of several thousand mandelbrot frames spanning a dozen decades of zoom
    from costing a full pairwise sweep.
    """
    places = [_place(row) for row in rows]
    grouping = Grouping(of_row=[None] * len(rows))
    grouping.n_unplaced = sum(1 for place in places if place is None)

    planes: dict = {}
    for index, place in enumerate(places):
        if place is not None:
            planes.setdefault(place.plane, []).append(index)

    next_id = 0
    for plane in sorted(planes, key=repr):
        indices = sorted(planes[plane], key=lambda i: places[i].width)
        union = _Union(len(indices))
        for i, index in enumerate(indices):
            here = places[index]
            for j in range(i + 1, len(indices)):
                there = places[indices[j]]
                if there.width > here.width * NEIGHBOR_SCALE:
                    break  # widths are sorted; nothing further can be a neighbour
                if _neighbours(here, there):
                    union.union(i, j)
        local: dict = {}
        for i, index in enumerate(indices):
            root = union.find(i)
            if root not in local:
                local[root] = next_id
                next_id += 1
            group = local[root]
            grouping.of_row[index] = group
            grouping.members.setdefault(group, []).append(index)
    for members in grouping.members.values():
        members.sort()
    return grouping


__all__ = [
    "C_TOLERANCE",
    "NEIGHBOR_SCALE",
    "NEIGHBOR_SHIFT",
    "Grouping",
    "assign",
    "plane_of",
]
