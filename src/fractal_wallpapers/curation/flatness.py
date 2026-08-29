"""How much of a finished picture is dead space, as a column beside the scores.

A density proxy, and the one the fitted rank key ([`curation.rank_key`]) carries.
Sweep the picture in cells, fit a plane to each cell, and count the cells with
nothing left over: `z = a*x + b*y + c` by least squares on the centred coordinate
grid, and a cell is **dead** when the residual RMS is under [`THRESHOLD`] on the
0-255 luminance scale.

The plane term is the whole of what separates this from a variance screen. A
smooth ramp across a cell is not detail, and a variance screen scores it as busy.

## It ranks backwards, which is the finding

Univariate AUC on the tier-4 boundary is **0.407 smooth / 0.480 strange** — more
dead space is a *worse* picture, which is the direction that makes it a density
signal rather than a second opinion about quality. On top of the render judge and
the location head it earns its place on both kinds, and it is the column the
nested selection chose in all five outer folds on smooth.

The JPEG byte count is the near neighbour and mostly carries the same fact —
Spearman -0.64 smooth / -0.58 strange — but head to head at n=342 the difference
does not resolve either way. This column is preferred on motivation and because
it earns on both kinds, not because it was proven better.

## One cell size and one threshold, and neither is chosen here

`flat16_1.0` — 16-pixel cells, a residual RMS of 1.0. It was selected over two
cell sizes and three thresholds by a nested selection that never saw the fold it
scored, unanimously across all five outer folds. The constants are pinned here so
that a reader can see them; **moving one is choosing a different column**, and
the fit that stands on it is fitted against this one.

## The sidecar, and why the column is not on the ledger row

Beside `scores.jsonl` and for [`candidate_ledger`]'s reason. A ledger row is the
recipe and the pixels, and neither moves; this is a reading of the picture taken
by a rule that could be re-chosen, so it lives keyed on the recipe key in a file
of its own and a row is never edited in place to carry it. It is also
regenerable: the pictures are on disk, and one command rebuilds the whole store.

The sweep costs about **7.5 ms a picture** single-threaded — a JPEG decode and
one pass of arithmetic over the luminance — so a pool of sixty thousand is a few
minutes over a small pool of workers, and the store is only ever swept for the
keys it does not already hold.

## A row with no picture has no flatness, and that is not a hole to fill

`curate retention` drops the picture of everything outside the top five per
(location, mode), so a quarter of the ledger names a JPEG that is not there.
Those rows have no reading and get no row here. They are also not in the pool:
[`solve.pool`] excludes an absent picture as `picture_absent`, so a seating that
ranks on a form carrying this column never has to impute one.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from fractal_wallpapers.curation import candidate_ledger, durability

#: The schema every sidecar row carries.
SCHEMA = 1

#: What the sidecar is called, beside `scores.jsonl` in the ledger's own subtree.
SIDECAR_NAME = "flatness.jsonl"

#: The cell the picture is tiled into, in pixels.
CELL = 16

#: Residual RMS in 0-255 luminance units, under which a cell holds no detail.
THRESHOLD = 1.0

#: The column's name, spelled the one way it is spelled everywhere: the cell size
#: and the threshold, because a flatness fraction read at other constants is a
#: different number and must not be able to wear this one.
COLUMN = f"flat{CELL}_{THRESHOLD}"

#: How many pictures one worker takes at a time. Large enough that the spawn cost
#: is amortized, small enough that the log moves.
CHUNK = 256

#: How many workers sweep by default. **Three**, the same number every leg that
#: drives the engine uses, for the same reason: this is a decode-bound sweep of
#: tens of thousands of JPEGs and it should not make the desktop unusable.
WORKERS = 3


class FlatnessError(RuntimeError):
    """The sidecar cannot be read, or the sweep cannot be run."""


# --------------------------------------------------------------------------- #
# The reading.
# --------------------------------------------------------------------------- #
def fraction(path, cell: int = CELL, threshold: float = THRESHOLD) -> float | None:
    """The share of `path`'s cells a plane fits with nothing left over.

    `None` when the picture cannot be opened or is smaller than one cell, which
    the caller counts. Never zero for either: no detail and no picture are
    different facts and a zero would put them under one number.
    """
    import numpy
    from PIL import Image

    where = Path(path)
    try:
        with Image.open(where) as image:
            grey = numpy.asarray(image.convert("L"), dtype=numpy.float32)
    except Exception:
        return None
    height = (grey.shape[0] // cell) * cell
    width = (grey.shape[1] // cell) * cell
    if height == 0 or width == 0:
        return None
    tiles = (
        grey[:height, :width]
        .reshape(height // cell, cell, width // cell, cell)
        .transpose(0, 2, 1, 3)
        .reshape(-1, cell, cell)
    )
    axis = numpy.arange(cell, dtype=numpy.float32) - (cell - 1) / 2.0
    x = numpy.broadcast_to(axis[None, :], (cell, cell))
    y = numpy.broadcast_to(axis[:, None], (cell, cell))
    # The design is orthogonal on a centred grid, so the least-squares plane is
    # three inner products and not a solve: `x` and `y` are uncorrelated with each
    # other and with the constant term over a full cell.
    norm = float((axis**2).sum() * cell)
    a = (tiles * x).sum(axis=(1, 2)) / norm
    b = (tiles * y).sum(axis=(1, 2)) / norm
    c = tiles.mean(axis=(1, 2))
    plane = a[:, None, None] * x + b[:, None, None] * y + c[:, None, None]
    rms = numpy.sqrt(((tiles - plane) ** 2).mean(axis=(1, 2)))
    return float((rms < threshold).mean())


def _chunk(payload: list) -> list:
    """One worker's share: `[(key, path)]` in, `[(key, reading)]` out."""
    return [(key, fraction(path)) for key, path in payload]


# --------------------------------------------------------------------------- #
# Where it lives.
# --------------------------------------------------------------------------- #
def sidecar_path() -> Path:
    """The sidecar: one row per recipe key, beside the scores sidecar."""
    return candidate_ledger.store_root() / SIDECAR_NAME


def durable() -> durability.Durable:
    """The sidecar as a [`durability.Durable`] — how it is saved and restored.

    Its own durable rather than a third file inside the ledger's `save`, because
    the ledger's save refuses when a file it names is not there, and a checkout
    that has never swept is the ordinary state rather than a loss.
    """
    return durability.Durable(
        name="the candidate ledger's flatness sidecar",
        live=sidecar_path(),
        copy=candidate_ledger.backup_path(SIDECAR_NAME),
        manifest=candidate_ledger.manifest_dir() / "flatness.manifest.json",
        why_not_tracked=(
            "one row per recipe with a picture on disk, which is tens of thousands of rows "
            "against a 1 MiB per-file history guard. Same guard, same answer as the rows and "
            "the scores."
        ),
        save_command="fractal-wallpapers curate flatness save",
        restore_command="fractal-wallpapers curate flatness restore",
        rebuild_command="fractal-wallpapers curate flatness sweep",
        facts=lambda path: {"column": COLUMN, "cell": CELL, "threshold": THRESHOLD},
    )


def row(key: str, reading: float) -> dict:
    """One sidecar row. The constants travel on it: a fraction read at another
    cell size is a different column and a reader must not have to guess."""
    return {
        "schema": SCHEMA,
        "recipe_key": str(key),
        "column": COLUMN,
        "cell": CELL,
        "threshold": THRESHOLD,
        COLUMN: round(float(reading), 6),
    }


def read(path: Path | None = None) -> list[dict]:
    """Every sidecar row. An absent sidecar reads empty rather than raising —
    nothing has swept yet is a state, not a failure."""
    where = sidecar_path() if path is None else Path(path)
    if not where.is_file():
        return []
    out = []
    with where.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                out.append(json.loads(line))
    return out


def by_recipe(rows=None, column: str = COLUMN) -> dict:
    """`{recipe key: reading}` for one column, refusing a mixed read.

    Named for [`candidate_ledger.scores_by_recipe`]'s reason: a store that came
    to hold two cell sizes would otherwise flatten last-row-wins into one
    ordering, with nothing anywhere saying which reading a seat was taken on.
    """
    read_rows = read() if rows is None else list(rows)
    return {
        str(entry["recipe_key"]): float(entry[column])
        for entry in read_rows
        if str(entry.get("column")) == str(column) and entry.get(column) is not None
    }


def write(rows) -> tuple[Path, int, int]:
    """Upsert `rows` into the sidecar by recipe key. `(path, total, new)`."""
    path = sidecar_path()
    held = {str(entry["recipe_key"]): entry for entry in read(path)}
    before = len(held)
    for entry in rows:
        held[str(entry["recipe_key"])] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in sorted(held):
            handle.write(json.dumps(held[key], ensure_ascii=False) + "\n")
    return path, len(held), len(held) - before


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
class PictureOf(NamedTuple):
    """The two fields [`missing`] reads, for a population that is not a pool.

    A [`solve.Candidate`] carries both and so does a raw ledger row, under other
    names and with a score this does not want. Two callers need the adapter now —
    `curate flatness --all` sweeping every row with a picture, and
    [`candidate_ledger.merge`] sweeping the rows one leg just wrote — so it lives
    here rather than in either of them.
    """

    key: str
    picture: str


def of_rows(rows) -> list:
    """[`PictureOf`] for every ledger row naming a picture. Order preserved.

    A row with no picture is left out rather than carried with a `None`: it has
    no reading to take and [`missing`] would drop it a step later anyway.
    """
    return [PictureOf(str(row["key"]), str(row["picture"])) for row in rows if row.get("picture")]


def missing(candidates, held=None) -> list:
    """`[(key, path)]` for the candidates the sidecar has no reading for.

    Anything with a `key` and a `picture` — a [`solve.Candidate`] or a raw ledger
    row's pair — because the pool is not the only population worth sweeping: the
    fit's own label rows include recipes a person **rejected**, which the pool
    excludes by rule and the key still has to be fitted on.
    """
    from fractal_wallpapers.paths import rehome

    known = by_recipe() if held is None else held
    out = []
    for candidate in candidates:
        key = str(candidate.key)
        if key in known:
            continue
        where = rehome(candidate.picture)
        if where is not None:
            out.append((key, Path(where)))
    return out


def sweep(candidates, workers: int = WORKERS, recompute: bool = False, log=print) -> dict:
    """Read every candidate the sidecar does not hold, and upsert what it finds.

    Incremental by construction: a store already swept costs one read of the
    sidecar and no decodes at all. `recompute` re-reads everything, which is what
    a moved constant would need — and a moved constant is a different [`COLUMN`],
    so it would land beside this one rather than over it.
    """
    import time
    from concurrent.futures import ProcessPoolExecutor

    started = time.time()
    held = {} if recompute else by_recipe()
    wanted = missing(candidates, held=held)
    already = sum(1 for candidate in candidates if str(candidate.key) in held)
    nameless = len(candidates) - already - len(wanted)
    log(
        f"[flatness] {len(candidates):,} candidates; {already:,} already read, "
        f"{len(wanted):,} to sweep at ~7.5 ms each over {workers} worker(s)"
        + (f", {nameless:,} name no picture this checkout can resolve" if nameless else "")
    )
    payloads = [wanted[at : at + CHUNK] for at in range(0, len(wanted), CHUNK)]
    made: list = []
    unreadable = 0

    def take(pairs) -> None:
        nonlocal unreadable
        for key, reading in pairs:
            if reading is None:
                unreadable += 1
            else:
                made.append(row(key, reading))

    if int(workers) <= 1 or not payloads:
        for done, payload in enumerate(payloads, start=1):
            take(_chunk(payload))
            if done % 20 == 0 or done == len(payloads):
                log(f"[flatness] {done}/{len(payloads)} chunk(s), {time.time() - started:.0f}s")
    else:
        with ProcessPoolExecutor(max_workers=int(workers)) as pool:
            for done, pairs in enumerate(pool.map(_chunk, payloads), start=1):
                take(pairs)
                if done % 20 == 0 or done == len(payloads):
                    log(f"[flatness] {done}/{len(payloads)} chunk(s), {time.time() - started:.0f}s")

    path, total, new = write(made) if made else (sidecar_path(), len(held), 0)
    seconds = time.time() - started
    record = {
        "column": COLUMN,
        "cell": CELL,
        "threshold": THRESHOLD,
        "candidates": len(candidates),
        "already_read": already,
        "no_resolvable_picture": nameless,
        "swept": len(wanted),
        "read": len(made),
        "unreadable": unreadable,
        "sidecar_rows": total,
        "new_rows": new,
        "seconds": round(seconds, 1),
        "seconds_per_picture": round(seconds / max(len(wanted), 1), 4),
        "workers": int(workers),
        "path": str(path),
    }
    log(
        f"[flatness] {len(made):,} read, {unreadable} unreadable, {total:,} rows in the "
        f"sidecar, {seconds:.0f}s"
    )
    return record


def coverage(candidates, rows=None) -> dict:
    """How much of a pool the sidecar can answer for, and what it cannot.

    The number the seating cares about: a candidate with no reading cannot be
    ranked by a form carrying this column, and a key that silently imputed one
    would be ranking a picture nobody has read.
    """
    known = by_recipe(rows)
    have = sum(1 for candidate in candidates if candidate.key in known)
    return {
        "column": COLUMN,
        "candidates": len(candidates),
        "with_a_reading": have,
        "without": len(candidates) - have,
        "share": round(have / max(len(candidates), 1), 6),
        "sidecar_rows": len(known),
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


__all__ = [
    "CELL",
    "CHUNK",
    "COLUMN",
    "SCHEMA",
    "SIDECAR_NAME",
    "THRESHOLD",
    "WORKERS",
    "FlatnessError",
    "by_recipe",
    "coverage",
    "durable",
    "fraction",
    "missing",
    "read",
    "row",
    "sidecar_path",
    "sweep",
    "write",
]
