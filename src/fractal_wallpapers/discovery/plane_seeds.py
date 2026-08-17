"""The parameter planes' seed pool, and the procedure that derives it.

The four parameter-plane partitions — `mandelbrot` and `multibrot3/4/5` — have
no sampler on purpose: an unscreened draw over the higher degrees measured zero
good locations in a hundred and forty-four, so nothing here invents a root. What
they run on instead is *this* pool, and the first production run showed exactly
how load-bearing it is. Without a seed file `has_channel` is false for all four,
they can never be refilled, and half the registry is unservable the moment its
queues drain — which is the state that run stalled in.

So the pool is tracked data with a deriver beside it, on the same terms as every
other constant in this repository: **nothing reaches a shipped table except
through a regeneration.**

## Where a root comes from

One coarse grid per family over its home frame. Each grid point is handed to
[`nucleus.identify_nucleus`], which says which atom that point sits on; each
distinct atom becomes one root, framed at `FRAME_MULTIPLE × its own window
scale`. That is not a survey and is not meant to be — it is a source of *places
to start*, and the walk's own descent is what turns a place into a location.

Three filters, each of them a refusal rather than a preference:

* **a frame the walk can move inside.** Narrower than [`WIDTH_MIN`] and there is
  no `f64` headroom left to descend into; wider than [`WIDTH_MAX`] and the root
  is the home view with extra steps.
* **`f64` headroom**, at the same [`nucleus.MARGIN_MIN_DECADES`] the reframing
  operators use. One number, one meaning.
* **spread over periods before margin.** A pool that is five hundred copies of
  the same period is one place, not five hundred, so the keep is round-robin
  across periods and only ranks by margin *within* a period.

## The home views, and the six a person chose

Each family contributes its own home view, so a family whose every atom is
refused still has somewhere to stand. And the six hand-picked Mandelbrot frames
the early walks ran on are carried here rather than left in a scratch file:
they are the only roots in this repository that a person chose, they are known to
produce passing rows, and a pool that could not be rebuilt without a file nobody
tracks is not a tracked pool.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.discovery import nucleus
from fractal_wallpapers.paths import repo_root

#: The schema every pool row carries.
SCHEMA = 1

#: The four partitions this pool serves, with the degree each is solved at.
FAMILIES = (
    ("mandelbrot", {"kind": "mandelbrot"}, 2),
    ("multibrot3", {"kind": "multibrot", "degree": 3}, 3),
    ("multibrot4", {"kind": "multibrot", "degree": 4}, 4),
    ("multibrot5", {"kind": "multibrot", "degree": 5}, 5),
)

#: Columns of the grid laid over each family's home frame; rows follow from 16:9.
#: Coarse, because this is a source of roots and not a survey — and the shipped
#: pool's size is a straight consequence of it, so moving it is a regeneration.
COLUMNS = 340

#: Roots kept per partition. The four grids find between four hundred and eleven
#: hundred distinct atoms apiece, so this bites on three of the four and the
#: fourth ships everything it found.
PER_PARTITION = 500

#: The frame the **solver** may emit a root at. Narrower than [`WIDTH_MIN`] and
#: there is no `f64` headroom left to descend into; wider than [`WIDTH_MAX`] and
#: the root is the home view with extra steps.
#:
#: A bound on what the grid procedure produces, not a claim about every frame a
#: walk can use — the hand-picked roots are outside it in one case, because they
#: are somebody's judgement about where to look and this is a filter for a solver
#: that has none.
WIDTH_MIN = 1e-9
WIDTH_MAX = 0.5

#: Which channels the frame bound is an invariant of.
SOLVED = "nucleus_grid"

#: How far Newton looks for a period before giving up on a grid point, and how
#: many of the ranked candidate periods it tries.
MAX_PERIOD = 48
PERIODS_TRIED = 2

#: The six Mandelbrot frames a person chose, carried as data because they are not
#: derivable from anything: they are somebody's judgement about where to look.
HAND_PICKED = (
    ("m00", "-0.7453", "0.1127", "0.2"),
    ("m01", "0.2929", "0.0149", "0.1"),
    ("m02", "-0.1592", "1.0317", "0.08"),
    ("m03", "0.3245", "0.0489", "0.12"),
    ("m04", "-0.748", "0.263", "0.06"),
    ("m05", "0.4104135054546244", "0.20967482476903096", "0.5622541254857749"),
)


class PlaneSeedError(RuntimeError):
    """The pool cannot be derived, or does not hold what a pool has to hold."""


def pool_path() -> Path:
    """The tracked pool the parameter planes are seeded and refilled from."""
    return repo_root() / "data" / "discovery" / "plane_seed_pool.jsonl"


def rows_of(columns: int = COLUMNS) -> int:
    """Grid rows for `columns`, at the 16:9 the home frames are written in."""
    return max(1, round(columns * 9 / 16))


def grid(view: dict, columns: int):
    """Cell centres of a `columns × rows_of(columns)` grid over one home frame."""
    centre_re, centre_im = float(view["center_re"]), float(view["center_im"])
    width = float(view["width"])
    height = width * 9 / 16
    rows = rows_of(columns)
    for row in range(rows):
        for column in range(columns):
            yield complex(
                centre_re + width * ((column + 0.5) / columns - 0.5),
                centre_im + height * ((row + 0.5) / rows - 0.5),
            )


def _spread(found: list[dict], keep: int) -> list[dict]:
    """Round-robin over periods, best margin first inside each.

    Deliberately not "the `keep` best margins": those cluster on whichever period
    the grid resolved most cleanly, and a pool of one period is one place.
    """
    by_period: dict[int, list[dict]] = {}
    for record in found:
        by_period.setdefault(int(record["period"]), []).append(record)
    for rows in by_period.values():
        rows.sort(key=lambda record: -record["f64_margin_decades"])
    kept: list[dict] = []
    depth = 0
    while len(kept) < keep and any(len(rows) > depth for rows in by_period.values()):
        for period in sorted(by_period):
            if len(by_period[period]) > depth and len(kept) < keep:
                kept.append(by_period[period][depth])
        depth += 1
    return kept


def _width_of(record: dict) -> float:
    return nucleus.FRAME_MULTIPLE * record["window_scale"]


def derive(columns: int = COLUMNS, per_partition: int = PER_PARTITION, log=print) -> dict:
    """Walk every family's grid and build the pool. `(rows, per-partition record)`.

    Deterministic: no draw, no clock, and a stable sort — so a re-derivation on
    another machine is byte-identical and [`verify`] can be an equality rather
    than a tolerance.
    """
    import time

    import mpmath as mp

    from fractal_wallpapers import engine

    nucleus.set_precision()
    rows: list[dict] = []
    record: dict = {}
    for partition, family, degree in FAMILIES:
        view = engine.home_view(family)
        near = float(view["width"]) / columns
        found: dict[str, dict] = {}
        refused = {"no_period": 0, "no_nucleus": 0, "repeat": 0, "frame": 0, "margin": 0}
        started = time.monotonic()
        for point in grid(view, columns):
            periods = nucleus.period_candidates(
                point, degree, max_period=MAX_PERIOD, keep=PERIODS_TRIED
            )
            if not periods:
                refused["no_period"] += 1
                continue
            atom, _status = nucleus.identify_nucleus(
                point, degree=degree, near=near, periods=periods
            )
            if atom is None:
                refused["no_nucleus"] += 1
                continue
            if atom["key"] in found:
                refused["repeat"] += 1
                continue
            if not (WIDTH_MIN <= _width_of(atom) <= WIDTH_MAX):
                refused["frame"] += 1
                continue
            if atom["f64_margin_decades"] < nucleus.MARGIN_MIN_DECADES:
                refused["margin"] += 1
                continue
            found[atom["key"]] = atom

        kept = _spread(list(found.values()), per_partition)
        # The home view first, so a family whose every atom is refused still has
        # one place to stand.
        rows.append(
            {
                "schema": SCHEMA,
                "id": f"{partition}-home",
                "family": family,
                "provenance": {"channel": "home_view"},
            }
        )
        for index, atom in enumerate(kept):
            rows.append(
                {
                    "schema": SCHEMA,
                    "id": f"{partition}-p{atom['period']}-{index:03d}",
                    "family": family,
                    "viewport": {
                        "center_re": atom["center_re"],
                        "center_im": atom["center_im"],
                        "width": mp.nstr(mp.mpf(_width_of(atom)), 17, strip_zeros=False),
                    },
                    "provenance": {
                        "channel": "nucleus_grid",
                        "period": atom["period"],
                        "f64_margin_decades": atom["f64_margin_decades"],
                        "nucleus_key": atom["key"],
                    },
                }
            )
        periods = sorted({int(atom["period"]) for atom in kept})
        record[partition] = {
            "grid": [columns, rows_of(columns)],
            "atoms_found": len(found),
            "kept": len(kept),
            "periods": len(periods),
            "period_range": [periods[0], periods[-1]] if periods else [],
            "refused": refused,
            "seconds": round(time.monotonic() - started, 1),
        }
        log(
            f"{partition}: {len(found)} distinct atoms on a {columns}x{rows_of(columns)} grid, "
            f"{len(kept)} kept over {len(periods)} period(s), {record[partition]['seconds']}s"
        )

    for identifier, center_re, center_im, width in HAND_PICKED:
        rows.append(
            {
                "schema": SCHEMA,
                "id": identifier,
                "family": {"kind": "mandelbrot"},
                "viewport": {
                    "center_re": center_re,
                    "center_im": center_im,
                    "width": width,
                },
                "provenance": {"channel": "hand_picked"},
            }
        )
    record["hand_picked"] = len(HAND_PICKED)
    record["rows"] = len(rows)
    return {"rows": rows, "record": record}


def render(rows: list[dict]) -> str:
    """The pool as the tracked file's exact bytes."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write(rows: list[dict], path: Path | None = None) -> Path:
    path = pool_path() if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(rows), encoding="utf-8", newline="\n")
    return path


def verify(rows: list[dict], path: Path | None = None) -> dict:
    """Compare a fresh derivation against the tracked pool, row by row.

    The default, because the expensive half of "is this file still what its
    procedure produces" is running the procedure, and having run it the
    comparison is free. A verify that passes is the pool's only real claim.
    """
    path = pool_path() if path is None else Path(path)
    if not path.is_file():
        return {"held": False, "reason": f"{path} does not exist", "derived": len(rows)}
    tracked = read(path)
    mismatched = [
        one.get("id") or two.get("id")
        for one, two in zip(rows, tracked, strict=False)
        if one != two
    ]
    return {
        "held": rows == tracked,
        "path": str(path),
        "derived": len(rows),
        "tracked": len(tracked),
        "mismatched": mismatched[:10],
        "mismatched_total": len(mismatched) + abs(len(rows) - len(tracked)),
    }


def read(path: Path | None = None) -> list[dict]:
    """The tracked pool, schema-checked, with the invariants a pool has to hold.

    Checked at load, every time, on the same principle as the Julia pool's
    spacing floor: the one property a later edit could silently break is the one
    nothing would notice until a run came back empty.
    """
    from fractal_wallpapers.discovery import pools

    path = pool_path() if path is None else Path(path)
    if not path.is_file():
        raise PlaneSeedError(
            f"{path} is missing, so the parameter planes have no roots and no refill channel. "
            f"Derive it with `fractal-wallpapers derive-plane-seeds --write`."
        )
    rows = pools.read_rows(path)
    seen: set[str] = set()
    for number, row in enumerate(rows, start=1):
        if "family" not in row or "id" not in row:
            raise PlaneSeedError(f"{path.name}:{number}: a pool row needs an id and a family")
        if row["id"] in seen:
            raise PlaneSeedError(f"{path.name}:{number}: duplicate id {row['id']!r}")
        seen.add(row["id"])
        view = row.get("viewport")
        if view is None:
            continue
        width = float(view["width"])
        if width <= 0:
            raise PlaneSeedError(f"{path.name}:{number}: {row['id']} has no frame to walk in")
        # The bound is the solver's, so it is checked on what the solver wrote. A
        # hand-picked frame is a person's judgement and the procedure has no
        # standing to refuse it.
        channel = (row.get("provenance") or {}).get("channel")
        if channel in (None, SOLVED) and not (WIDTH_MIN <= width <= WIDTH_MAX):
            raise PlaneSeedError(
                f"{path.name}:{number}: {row['id']} was solved for at width {width:g}, outside "
                f"[{WIDTH_MIN:g}, {WIDTH_MAX:g}] — a root the walk cannot move inside"
            )
    return rows


__all__ = [
    "COLUMNS",
    "FAMILIES",
    "HAND_PICKED",
    "MAX_PERIOD",
    "PERIODS_TRIED",
    "PER_PARTITION",
    "SCHEMA",
    "WIDTH_MAX",
    "WIDTH_MIN",
    "PlaneSeedError",
    "derive",
    "grid",
    "pool_path",
    "read",
    "render",
    "rows_of",
    "verify",
    "write",
]
