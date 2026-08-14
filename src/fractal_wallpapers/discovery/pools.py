"""The seed pools, and the one property they have to keep.

A walk needs somewhere to start, and where it starts is **data, not a sampler**.
Two pools are tracked in this repository, one per dynamical family, and a walk
over those families draws its roots from them. That is a decision with a
measurement behind it, and it cuts in two directions.

**For the dynamical families the pool is the good supply.** Julia sets worth
looking at cluster in a thin, targetable class of `c` — filament detail at
several scales together with composed interior lakes — which occupies a couple
of percent of the viable near-boundary parameters. The pool is what a
three-stage screen left after drawing that shell, screening for viability, and
ranking on boundary proximity with the interior-lake channel required to fire.

**For the parameter-plane families there is deliberately no draw at all.** An
unscreened shell draw over the higher multibrot degrees measured zero good
locations out of a hundred and forty-four — not a low rate, a zero — so this
module builds no raw-draw path for them. Those families run on explicit seeds
and on what the reframing operators find from what the walk already reached, and
a walk asked to source them from nothing says so instead of guessing.

## The `c`-spacing floor

Two Julia parameters closer than [`C_SPACING_FLOOR`] render as the same picture
often enough not to be worth carrying twice. The number is **a tolerance chosen
against pool cost, not a point where the looks stop being similar** — measured
at a fixed viewport across five decades of separation, the near-duplicate rate
falls smoothly and monotonically the whole way and there is no knee to read a
floor off. What the adopted floor buys is a stated rate: the closest pairs it
admits are near-duplicates about 7% of the time, against about 20% at a floor
three times finer, and the pool pays for it in size.

The floor is checked **at load**, over the shipped file, every time. It is the
one invariant of the pool that a later edit could silently break, and a pool
that has quietly saturated its own spacing is indistinguishable from a healthy
one until a run comes back with nothing new in it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from fractal_wallpapers.paths import repo_root

#: Minimum separation between two accepted Julia parameters.
C_SPACING_FLOOR = 3.2e-2


def pool_dir() -> Path:
    """Where the tracked seed pools live."""
    return repo_root() / "data" / "discovery"


@dataclass(frozen=True)
class JuliaSeed:
    """One Julia parameter, and where it came from."""

    id: str
    c: tuple[str, str]
    #: How this parameter was found. Provenance only; nothing selects on it.
    channel: str

    def family(self, degree: int = 2) -> dict:
        return {"kind": "julia", "degree": degree, "c": [self.c[0], self.c[1]]}


@dataclass(frozen=True)
class PhoenixSeed:
    """One point of Phoenix parameter space: `(c, p, z₋₁)` in full.

    All three are the seed, and this is not bookkeeping. `z₋₁` is load-bearing:
    the recurrence carries it forward, so any non-zero value moves pixels, and a
    non-real one gives the largest departure of all because it breaks the
    real-axis reflection that all-real parameters preserve. A pool that recorded
    only `c` would be a pool of different fractals under one name.
    """

    id: str
    c: tuple[str, str]
    p: tuple[str, str]
    z_prev: tuple[str, str]
    #: Which stability curve the parameter was drawn near.
    branch: str
    #: Phase along that curve, and the displacement off it.
    theta: str
    offset: str
    #: The sampler's real-`p` sub-mode.
    #:
    #: **Not** the classic pinned instance, which is a different thing entirely
    #: and is what this flag gets mistaken for. It records how the seed was
    #: *drawn*: `p` on the real axis in the classic regime, the displacement off
    #: the stability curve exactly zero, and `z₋₁` exactly zero. `c` still comes
    #: from the closed form at a complex phase, so it is not real and the seed is
    #: not a named location — it is an ordinary seed drawn a particular way.
    real_p_mode: bool

    def family(self) -> dict:
        return {
            "kind": "phoenix",
            "c": [self.c[0], self.c[1]],
            "p": [self.p[0], self.p[1]],
            "z_prev": [self.z_prev[0], self.z_prev[1]],
        }


def read_rows(path: Path) -> list[dict]:
    """Read a JSONL record file, checking the schema on every row."""
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("schema") != 1:
                raise ValueError(f"{path.name}:{number}: schema {row.get('schema')!r}, expected 1")
            rows.append(row)
    return rows


def closest_pair(points: list[tuple[float, float]]) -> float:
    """The smallest distance between any two of `points`, or infinity."""
    closest = math.inf
    for i, (ax, ay) in enumerate(points):
        for bx, by in points[i + 1 :]:
            closest = min(closest, math.hypot(ax - bx, ay - by))
    return closest


def julia_pool(path: Path | None = None, *, floor: float = C_SPACING_FLOOR) -> list[JuliaSeed]:
    """The tracked Julia `c`-pool, with its spacing verified.

    Verified rather than enforced: the pool is a shipped artifact and thinning
    it here would mean the file on disk and the pool in memory were different
    objects. If the floor is violated the file is wrong, and that is a failure
    to fix rather than to route around.
    """
    path = path or pool_dir() / "julia_c_pool.jsonl"
    seeds = [
        JuliaSeed(id=row["id"], c=(row["c"][0], row["c"][1]), channel=row["channel"])
        for row in read_rows(path)
    ]
    measured = closest_pair([(float(s.c[0]), float(s.c[1])) for s in seeds])
    if measured < floor:
        raise ValueError(
            f"{path.name}: closest pair is {measured:.4e}, under the {floor:.1e} "
            f"c-spacing floor — the pool has saturated its own spacing"
        )
    return seeds


def phoenix_pool(path: Path | None = None) -> list[PhoenixSeed]:
    """The tracked Phoenix seed pool.

    No spacing check: a Phoenix seed is a point of a six-dimensional parameter
    space, and a distance in it is not the quantity the Julia floor measures.
    Two seeds sharing a `c` and differing in `p` or `z₋₁` are different fractals.
    """
    path = path or pool_dir() / "phoenix_seed_pool.jsonl"
    return [
        PhoenixSeed(
            id=row["id"],
            c=(row["c"][0], row["c"][1]),
            p=(row["p"][0], row["p"][1]),
            z_prev=(row["z_prev"][0], row["z_prev"][1]),
            branch=row["branch"],
            theta=row["theta"],
            offset=row["offset"],
            real_p_mode=bool(row["real_p_mode"]),
        )
        for row in read_rows(path)
    ]


def read_seed_file(path: Path) -> list[dict]:
    """Read an explicit seed file: one `{family, viewport}` object per line.

    This is how the parameter-plane families are supplied, and the only way they
    are. A row is a whole location — the family with its constants, and the view
    to start from — because a c-plane root is a *place*, not a parameter, and
    splitting the two would leave rows that need a second file to mean anything.
    """
    rows = read_rows(path)
    for number, row in enumerate(rows, start=1):
        if "family" not in row:
            raise ValueError(f"{path.name}:{number}: a seed row needs a family")
    return rows
