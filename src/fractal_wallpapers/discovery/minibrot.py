"""Is there a minibrot in this frame, and how big is it against the frame.

A *minibrot descent* is the move a person means when they say a zoom "went into a
minibrot and came out with a picture": the frame ends up holding a small copy of
the whole set, big enough to see and small enough not to be solid black. This
module makes that question a number, over frames this project already has, and it
answers it the way [`discovery.operators`] already answers it for a reframing —
[`discovery.nucleus`]' Newton and its atom instrument, no second nucleus finder.

## Two readings, and which one is kept

**(a) The frame holds an atom of comparable size.** Solve for the nucleus the
frame's centre sits on, measure the atom's linear scale `1/|A|`, and ask what the
frame's width is in atom sizes. This is a property of the *frame* and of nothing
else: two rows at one place answer identically, and a frame that arrived by
hand, by a reframing or by ten rungs of a walk all get the same reading.

**(b) The row descended far below its root.** Join the pool row back to the walk
ledger that found it, take the node's `depth` and the decades between its width
and its root's. This is a property of the *route*, and three things are wrong
with it as the census criterion: **25,172 of the pool's 55,884 locations join to
no walk row at all** ([`descent`] returns `None` for them, and a reframing's own
view is one of them by construction), the same frame reached twice reads twice,
and descending is what a walk does — at *depth ≥ 5 and two decades below the
root*, **8,935 of the 30,712** joinable locations clear it, which is a reading of
the search and not of the picture.

The census keeps **(a)**, and the named row of `minibrot_descent_census_ckpt140`
satisfies it: a **period-1026** nucleus 0.15 frame widths off centre, the frame
**11.8** atom sizes wide. It satisfies (b) as well — depth 6, 1.88 decades below
its root — which is why the tie had to be broken on what the reading is *of*
rather than on which one the row passes. [`descent`] is here, and reported
beside the census, precisely because it is cheap and it is the provenance half
of the story; it is not what decides a verdict.

## Why the period ceiling moves, and what makes that affordable

[`operators._solve_at_center`] sweeps to [`operators.MAX_PERIOD`] — 64 — which is
right for a walk deciding where to go next and **blind to every minibrot this
census is about**. The named row sits inside a period-27 satellite, so the atoms
in its frame have periods that are multiples of 27; the one that is there is
1026, sixteen times the ceiling. Raise the ceiling and the cost arrives with it:
Newton at period `p` walks a `p`-step orbit at 60 decimal digits, up to
[`nucleus.NEWTON_STEPS`] times.

So the ranked candidate periods are **screened before Newton, in `f64`, for
free**. `log|A| ≈ (d/(d−1)) · Σ log(d·|z_k|^(d−1))` over the critical orbit at the
frame's centre is one prefix sum over magnitudes the orbit scan already computed,
and a period whose atom cannot be anywhere near the frame's own scale never
reaches the solver. The approximation is loose — it read 8.37 against the true
9.96 at the named row's period 1026, because the frame's centre is not the
nucleus and `|z'_p|` is not `|Λ|` — so [`SCREEN_SLACK`] is three decades, twice
the worst error seen. Measured over 60 pool locations it cut the pass from
**158.2 s to 35.5 s** and changed **no** verdict: same 56 nuclei, same periods,
same ratios, and the worst single probe fell from 101.3 s to 13.3 s.

## What the census can and cannot be asked about

Only the parameter planes. A Julia or Phoenix view has no embedded copy of a
parameter-plane set to find and no nucleus to solve for, so [`PLANES`] is the
whole eligible population — 21,049 of the pool's 55,884 locations — and a caller
that hands in a dynamical partition gets `None` with the reason, never a zero.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers.discovery import nucleus as nuc
from fractal_wallpapers.supply import partitions as partitions_module

#: Iterations of the `f64` critical orbit the period ranking is read off.
#:
#: The scan stops at escape, which is what happens at almost every frame; this is
#: the ceiling for a centre that is *interior* — inside the set or inside one of
#: its atoms — where the orbit never escapes and the ranking has to be cut
#: somewhere. It bounds the period this instrument can name, and 40,000 is four
#: times past anything the pool holds: over 27,578 probes the deepest atom named
#: was **period 9,966**.
ORBIT_CAP = 40_000

#: Argmins of `|z_k|` kept from the scan, each contributing its divisors.
#:
#: [`nucleus.period_candidates`]' own `keep`, raised from its 4. The reason is
#: this census's population rather than a disagreement: a frame inside a
#: period-`q` satellite has its whole minimum structure on multiples of `q`, so
#: the useful argmins are further down the sorted list than they are for the
#: shallow views an operator fires at.
KEEP_ARGMINS = 6

#: How far off centre the nucleus may land, in frame widths.
#:
#: [`operators.SNAP_MAX_WIDTH_MULTIPLE`], and deliberately the same number: a
#: nucleus further from the centre than the frame is wide was not in the picture,
#: which is the same claim a snap makes when it refuses `nucleus_outside_frame`.
NEAR_MULTIPLE = 1.0

#: The frame's width in atom sizes, below which the frame is *inside* the atom.
#:
#: Framing into an atom is solid black — [`operators.FRAMINGS`] says so and has no
#: small framing for the same reason — so a reading under this is not a minibrot
#: in a frame, it is a minibrot the frame is in. Counted and reported apart.
FRAME_MIN = 1.0

#: The frame's width in atom sizes, above which the atom is a speck.
#:
#: The project's own framings bracket it: [`nucleus.FRAME_MULTIPLE`] is 4, the
#: "is this atom any good" frame, and 16 is [`operators.FRAMINGS`]' "worth
#: labeling" one. 32 is one doubling past the larger of those, which keeps a
#: frame that holds the atom plus a ring of its decorations and drops one where
#: the atom is a thousandth of the picture's area. **The census reports the whole
#: ratio distribution**, so this cut is a line to move and never a reading to
#: re-take: `minibrot_descent_census_ckpt140` read **10,603** locations in band at
#: 32 against **13,939** at 64, over 27,578 probed.
FRAME_MAX = 32.0

#: Decades of slack the `f64` screen allows around the band above.
#:
#: Twice the worst error the approximation was measured at. See the module
#: docstring: it is loose by construction and the slack is what keeps it a
#: screen rather than a second, worse criterion.
SCREEN_SLACK = 3.0

#: Newton solves one probe may spend, whatever the screen leaves.
#:
#: A backstop and not the working bound — the screen is what makes the pass
#: affordable, and over the census **374 probes of 27,578** reached it — 1.4%, on
#: 197,254 Newton solves in all, which is 7.2 a probe. It is
#: here because a pathological centre can rank dozens of large periods that all
#: survive a three-decade screen, and one of those cost 101 s before the screen
#: existed.
MAX_SOLVES = 24

#: The partitions this instrument can be asked about at all: the parameter
#: planes, where a small copy of the set is a thing that exists.
PLANES = partitions_module.PARAMETER_PLANES

#: What a probe over a dynamical partition is refused with.
NOT_A_PLANE = "not a parameter plane: a julia or phoenix view has no embedded copy"

#: What a probe whose orbit escapes at once is refused with.
ESCAPED = "orbit_escaped_immediately"

#: What a probe that solved nothing near its centre is refused with. Spelled the
#: way [`operators._solve_at_center`] spells it, because it is the same refusal.
OUTSIDE = "nucleus_outside_frame"


def degree_of(partition: str) -> int | None:
    """The degree a partition's frames iterate at, or `None` if it has no atoms."""
    if partition not in PLANES:
        return None
    return partitions_module.degree_of_plane(partition)


@dataclass
class Scan:
    """One `f64` pass over the critical orbit at a frame's centre."""

    #: Candidate periods, ascending: the divisors of the kept argmins.
    periods: list[int]
    #: `log₁₀ Π_{j≤k} (d·|z_j|^(d−1))`, indexed by `k`. The screen's whole input.
    prefix: list[float]
    #: The iteration the orbit escaped at, or [`ORBIT_CAP`] if it never did.
    escaped_at: int

    def approx_log10_abs_a(self, period: int, degree: int) -> float | None:
        """`log₁₀|A|` at `period`, off the prefix sum. Loose by decades; see above."""
        if period - 1 >= len(self.prefix):
            return None
        return (degree / (degree - 1)) * self.prefix[period - 1]


def scan(center_re, center_im, degree: int, *, cap: int = ORBIT_CAP, keep: int = KEEP_ARGMINS):
    """Rank the periods worth solving at a centre, and keep the screen's input.

    [`nucleus.period_candidates`]' argument, at this census's ceiling and without
    its truncation: that function keeps the twelve *smallest* divisors, which is
    right for an operator whose answer is a shallow atom and wrong here, where the
    atom that is actually in the frame is the largest divisor of the deepest
    argmin. The divisors are returned whole and the screen does the cutting.
    """
    point = complex(float(center_re), float(center_im))
    escape = 2.0 ** (1.0 / max(degree - 1, 1)) * 2.0
    z = complex(0.0, 0.0)
    seen: list[tuple[float, int]] = []
    prefix = [0.0]
    step = 0
    for step in range(1, cap + 1):
        z = (z * z + point) if degree == 2 else (z**degree + point)
        magnitude = abs(z)
        if not math.isfinite(magnitude) or magnitude > escape:
            break
        seen.append((magnitude, step))
        prefix.append(
            prefix[-1] + math.log10(degree) + (degree - 1) * math.log10(magnitude)
            if magnitude > 0
            else prefix[-1]
        )
    if not seen:
        return Scan([], prefix, step)
    seen.sort()
    periods: set[int] = set()
    for _magnitude, multiple in seen[:keep]:
        periods.update(d for d in range(2, multiple + 1) if multiple % d == 0)
    return Scan(sorted(periods), prefix, step)


def screened(held: Scan, width: float, degree: int, *, slack: float = SCREEN_SLACK) -> list[int]:
    """The candidate periods whose atom could be near the frame's own scale.

    `f64` and free: the band is [`FRAME_MIN`]–[`FRAME_MAX`] widened by `slack`
    decades either way, and the test is `log₁₀(width) + log₁₀|A|`, which is
    `log₁₀` of the frame's width in atom sizes.
    """
    low = math.log10(FRAME_MIN) - slack
    high = math.log10(FRAME_MAX) + slack
    if width <= 0:
        return []
    at = math.log10(width)
    kept = []
    for period in held.periods:
        approx = held.approx_log10_abs_a(period, degree)
        if approx is not None and low <= at + approx <= high:
            kept.append(period)
    return kept


def probe(
    center_re,
    center_im,
    width,
    degree: int,
    *,
    near_multiple: float = NEAR_MULTIPLE,
    max_solves: int = MAX_SOLVES,
    slack: float = SCREEN_SLACK,
) -> tuple[dict | None, dict]:
    """`(the atom this frame holds, what it cost)` — the census's one measurement.

    The atom record is [`nucleus.make_atom`]'s, with `seed_distance` beside it and
    two readings added: `frame_sizes`, the frame's width in atom sizes, and
    `in_frame`, whether that lands in the band. `None` with a reason where there
    is no atom to name.

    **Smallest period wins, among those the screen left** — [`nucleus`]' own rule,
    and it is the `near_multiple` bound that stops it handing back the parent: at
    the named row, period 27 and period 54 both converge to minimal nuclei and
    both are refused, at 582 and 193 frame widths off centre, before period 1026
    is reached at 0.15.
    """
    import mpmath as mp

    width = float(width)
    cost = {"solves": 0, "ranked": 0, "screened": 0, "escaped_at": 0}
    held = scan(center_re, center_im, degree)
    cost["ranked"] = len(held.periods)
    cost["escaped_at"] = held.escaped_at
    if not held.periods:
        return None, {**cost, "refused": ESCAPED}
    periods = screened(held, width, degree, slack=slack)[:max_solves]
    cost["screened"] = len(periods)
    if not periods:
        return None, {**cost, "refused": OUTSIDE}

    nuc.set_precision()
    center = mp.mpc(mp.mpf(str(center_re)), mp.mpf(str(center_im)))
    near = mp.mpf(str(near_multiple * width))
    refusal = OUTSIDE
    for period in periods:
        cost["solves"] += 1
        solve = nuc.newton_nucleus(center, period, degree=degree)
        if not solve.converged or abs(solve.c - center) > near:
            continue
        record = nuc.make_atom(solve.c, period, degree)
        if record is None:
            continue
        distance = float(abs(solve.c - center))
        sizes = width / record["window_scale"] if record["window_scale"] > 0 else float("inf")
        record["seed_distance"] = distance
        record["seed_distance_frames"] = distance / width if width else float("inf")
        record["frame_sizes"] = sizes
        record["in_frame"] = bool(FRAME_MIN <= sizes <= FRAME_MAX)
        return record, cost
    return None, {**cost, "refused": refusal}


# --------------------------------------------------------------------------- #
# The other reading: where the frame came from.
# --------------------------------------------------------------------------- #
@dataclass
class Descent:
    """What the walk ledgers say about how a frame was reached."""

    run: str
    depth: int | None
    fate: str | None
    branch: str | None
    root_width: float | None
    root_source: str | None
    root_provenance: dict = field(default_factory=dict)
    #: `log₁₀(root width / this width)`, or `None` with no root row.
    decades: float | None = None


def walk_index(paths=None) -> dict:
    """`{(center_re, center_im): [row, …]}` over every walk ledger on both tiers.

    Keyed on the coordinate **strings**, which is the identity a ledger writes and
    a pool row carries forward unaltered; the width is compared by the caller,
    relatively, because one place is reached at several widths. Over the 86
    ledgers this checkout can see it is 311,085 centres and 13 s.
    """
    from fractal_wallpapers.supply import ledgers

    index: dict[tuple[str, str], list[dict]] = {}
    for path in ledgers.ledger_paths() if paths is None else [Path(p) for p in paths]:
        run = Path(path).parent.name
        rows = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("kind") in ("candidate", "root"):
                rows.append(row)
        roots = {row.get("root_id"): row for row in rows if row.get("kind") == "root"}
        for row in rows:
            if row.get("kind") != "candidate":
                continue
            viewport = row.get("viewport") or {}
            root = roots.get(row.get("root_id")) or {}
            index.setdefault(
                (str(viewport.get("center_re")), str(viewport.get("center_im"))), []
            ).append(
                {
                    "run": run,
                    "width": viewport.get("width"),
                    "depth": row.get("depth"),
                    "fate": row.get("fate"),
                    "branch": row.get("branch"),
                    "root_width": (root.get("viewport") or {}).get("width"),
                    "root_source": root.get("source"),
                    "root_provenance": root.get("provenance") or {},
                }
            )
    return index


def descent(index: dict, center_re, center_im, width, *, tolerance: float = 1e-9) -> Descent | None:
    """The walk row a frame is, or `None` where no ledger holds it.

    `tolerance` is relative to the width, because the two strings being compared
    were written by different writers at different times and only ever mean the
    same `f64`.
    """
    rows = index.get((str(center_re), str(center_im)))
    if not rows:
        return None
    want = float(width)
    for row in rows:
        try:
            held = float(row["width"])
        except (TypeError, ValueError):
            continue
        if abs(held - want) > tolerance * abs(want):
            continue
        root = row.get("root_width")
        decades = None
        if root:
            try:
                decades = math.log10(float(root) / want)
            except (TypeError, ValueError, ZeroDivisionError):
                decades = None
        return Descent(
            run=row["run"],
            depth=row.get("depth"),
            fate=row.get("fate"),
            branch=row.get("branch"),
            root_width=float(root) if root else None,
            root_source=row.get("root_source"),
            root_provenance=row.get("root_provenance") or {},
            decades=decades,
        )
    return None


# --------------------------------------------------------------------------- #
# The census.
# --------------------------------------------------------------------------- #
#: The bin edges the ratio distribution is reported on, in atom sizes. Open at
#: both ends: the first bin is "the frame is inside the atom" and the last is
#: "the atom is a speck", and both are counts a reader of the band wants.
BANDS = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 256.0, 1024.0)


def band_of(sizes: float) -> str:
    """Which reporting bin a frame-in-atom-sizes reading falls in."""
    if sizes < BANDS[0]:
        return f"<{BANDS[0]:g}"
    for low, high in zip(BANDS, BANDS[1:], strict=False):
        if sizes < high:
            return f"{low:g}-{high:g}"
    return f">={BANDS[-1]:g}"


def _one(task: tuple) -> dict:
    """One census row, in a worker. Arguments are plain data so they pickle."""
    location, partition, center_re, center_im, width = task
    degree = degree_of(partition)
    if degree is None:
        return {"location": location, "refused": NOT_A_PLANE}
    record, cost = probe(center_re, center_im, width, degree)
    row = {"location": location, "partition": partition, "width": float(width), **cost}
    if record is None:
        return row
    return {
        **row,
        "period": record["period"],
        "window_scale": record["window_scale"],
        "frame_sizes": record["frame_sizes"],
        "seed_distance_frames": record["seed_distance_frames"],
        "in_frame": record["in_frame"],
        "band": band_of(record["frame_sizes"]),
        "nucleus": record["key"],
    }


def _initializer() -> None:
    from fractal_wallpapers import process_control

    process_control.set_background_priority()


def census(tasks, *, workers: int = 3, budget: float | None = None, log=print):
    """Probe a population of frames, yielding one row each, oldest task first.

    `tasks` is `(location key, partition, center_re, center_im, width)`. Three
    workers at below-normal priority, which is the render pool's shape and this
    box's rule — this leg drives no engine, but it saturates three cores for an
    hour and the desktop has to stay usable through it.

    `budget` is wall seconds; the pass stops handing out work when it is spent and
    the caller reports how far it got, which is what a capped scan owes its
    reader.
    """
    import time
    from concurrent.futures import ProcessPoolExecutor

    held = list(tasks)
    started = time.time()
    done = 0
    if workers <= 1:
        for task in held:
            if budget is not None and time.time() - started > budget:
                log(f"[census] budget spent after {done:,} of {len(held):,}")
                return
            yield _one(task)
            done += 1
        return
    with ProcessPoolExecutor(max_workers=workers, initializer=_initializer) as pool:
        for row in pool.map(_one, held, chunksize=8):
            yield row
            done += 1
            if budget is not None and time.time() - started > budget:
                log(f"[census] budget spent after {done:,} of {len(held):,}")
                return
