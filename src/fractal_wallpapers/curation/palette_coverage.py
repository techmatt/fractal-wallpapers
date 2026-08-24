"""Coverage on pixels: how many maps can put a swatch on a real share of an image.

The colour census counts a swatch's share of a colormap's **ramp**. That is the
right question about a library and the wrong one about a picture, and the two
answers come apart badly. A map can carry a swatch across a quarter of its
gradient and put it on almost no pixels, because an escape-time field is not
uniform over `[0, 1]` — it piles up, sometimes very hard, at one end — and
production mirrors every non-cyclic map, which folds the far half of the ramp
back onto the near half. A swatch living at gradient position 0.8 of a mirrored
map is reachable only by field values near the middle of the frame's stretch, and
a frame with no middle never shows it.

So this module measures the same thing on pixels:

```text
a map COUNTS for swatch s at threshold t
    if at least one panel cell has >= t of its pixels assigned to s
```

Record-and-rank. Nothing here gates, filters or removes anything.

## Two reads, two estimands, never pooled

**Read A — capability.** Every baked map is put through a fixed probe panel under
production recipe settings, and the statistic is a *max over the panel*. It
answers "could this map ever show that colour", and it is bounded by the panel: a
wider panel can only raise a count.

**Read B — realized supply.** Over the renders the pool already holds, how many
distinct maps have *ever* produced an image carrying the swatch. No render is
made for it. It is conditioned on what the discovery walk found and what the
palette head picked, so it is a lower bound on capability and a different
quantity — the two tables are reported side by side and are never averaged.

## The panel is chosen for its field shapes, not for its pictures

A probe panel of pretty wallpapers overstates every count, because the fields that
make pretty wallpapers are the well-spread ones. The panel is therefore drawn from
existing pool rows and then *selected on the shape of its fields*: every dumpable
mode is represented, families are spread, and the two cells whose gradient
positions pile hardest at one end are taken by construction. Those are the cells
where a mirrored ramp strands its far half, and a panel without one is an
instrument that cannot see the failure it exists to find.

Only the seven `field` modes can be probed at all: a composite normalizes two
fields against the whole frame, a modulate looks up a different gradient place per
sample, and a direct trap is colour-valued before any gradient is spent. None has
one scalar field to dump, and the engine refuses rather than guessing.

## Production settings, and what a false capability is

The recipe is [`labeling.finished.recipe`] with every knob at the identity and
`mirror = colormap not in cyclic` — the rule [`models.palette_sets.recipe_for`]
owns. **Nothing samples the palette knobs**: gamma, cycles and phase are 1.0, 1.0
and 0.0 on every production colorize this repository makes, so there is no draw to
take a sample over and the max is over the panel alone.

A sequential map is also probed with the fold *off*, which production never does.
A swatch it reaches only that way is a **false capability** and is reported apart
from the main table rather than counted in it. The reverse case cannot arise: the
engine refuses to fold a cyclic map at all.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.palettes import codebook

#: The artifact's schema, carried from the first row.
SCHEMA = 1

#: The four thresholds this read is taken at, as a share of an image's pixels.
#: Finer and lower than [`codebook.SHARE_THRESHOLDS`] on purpose: the census's
#: 10%/25% pair asks *present* and *dominant* of a ramp, and the question here is
#: where the "sufficient" bar should be set at all, which needs the rungs below
#: the one that already exists.
THRESHOLDS: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20)

#: How many cells the probe panel holds. Inside the 12-20 the read is specified
#: over: wide enough that one unlucky field cannot decide a count, narrow enough
#: that every baked map through every cell is minutes rather than an evening.
PANEL_CELLS = 16

#: How many pool rows are dumped and measured before the panel is chosen from
#: them. The panel is a *selection* on field shape, so the pool it selects from
#: has to be several times its own size or the selection is a formality.
PANEL_DRAW = 56

#: The seed the candidate draw is taken under, so the panel is a function of the
#: pool and this file rather than of a shuffle.
PANEL_SEED = 20260823

#: How many deciles of gradient position a field's shape is described by. Ten is
#: what "piles up hard at one end" is legible in.
SHAPE_BINS = 10

#: What counts as one end of the gradient for the pile-up statistic: the bottom
#: decile of position, or the top one.
END_BINS = 1

#: The geometry a panel cell is probed at. The size every candidate render in this
#: project is made at, so a coverage share is comparable with a pool row's.
RESOLUTION = (640, 360)
SUPERSAMPLE = 2

#: The one mode the smooth judge owns; every other probeable mode is strange.
SMOOTH_MODE = "smooth"


class CoverageError(RuntimeError):
    """The coverage read cannot be taken over the stores as they are."""


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def coverage_dir() -> Path:
    """Where the coverage artifact lives. Ignored, and regenerable."""
    from fractal_wallpapers.paths import under

    return under("curation", "coverage")


def panel_path() -> Path:
    """The chosen panel: its cells, their field shapes, and what they were drawn from."""
    return coverage_dir() / "panel.json"


def fields_dir() -> Path:
    """The dumped fields. One iteration pass per cell, and every recolor reuses it."""
    return coverage_dir() / "fields"


def rows_path() -> Path:
    """One row per cell x map x fold: the share vector the recolor censused."""
    return coverage_dir() / "rows.jsonl"


def readout_path() -> Path:
    """The two tables, the false capabilities, and the population each was taken over."""
    return coverage_dir() / "coverage.json"


def _write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


# --------------------------------------------------------------------------- #
# The shape of one field, measured the way the engine spends it.
# --------------------------------------------------------------------------- #
def _percentile(ordered, p: float) -> float:
    """The engine's own percentile: nearest rank over the sorted valid samples.

    Restated from `coloring.rs` rather than approximated, because the whole
    descriptor is about where the mass lands and numpy's interpolating default
    would put the trim in a different place from the renderer's.
    """
    last = len(ordered) - 1
    index = min(int(round((p / 100.0) * last)), last)
    return float(ordered[index])


def _curve(position, transform: str):
    """The mode's own curve on a stretched position. `coloring.rs::Transform`."""
    import numpy

    if transform == "linear":
        return position
    if transform == "sqrt":
        return numpy.sqrt(position)
    if transform == "log":
        return numpy.log1p(position) / numpy.log(2.0)
    if transform == "scurve":
        return position * position * (3.0 - 2.0 * position)
    raise CoverageError(f"{transform} is not a curve the engine spends a field through")


def field_shape(record: Path) -> dict:
    """Where one dumped field's samples land on the gradient, as deciles.

    The engine's own path: trim to the 0.5th and 99.5th percentiles of the valid
    samples, stretch that span onto `[0, 1]`, then the mode's curve. Samples with
    no field value are the interior and take black rather than a gradient place,
    so they are counted apart — a frame that is half interior has half as many
    pixels available to carry any colour at all.
    """
    import numpy

    document = json.loads(Path(record).read_text(encoding="utf-8"))
    field = Path(record).parent / document["field_file"]
    values = numpy.fromfile(field, dtype="<f4").astype(numpy.float64)
    finite = numpy.isfinite(values)
    valid = values[finite]
    if valid.size == 0:
        raise CoverageError(f"{field} has no valid sample, so it has no gradient to spend")
    ordered = numpy.sort(valid)
    low = _percentile(ordered, 0.5)
    high = _percentile(ordered, 99.5)
    span = high - low if high > low else 1.0
    position = _curve(numpy.clip((valid - low) / span, 0.0, 1.0), document["transform"])
    counts, _ = numpy.histogram(position, bins=SHAPE_BINS, range=(0.0, 1.0))
    deciles = [round(float(count) / valid.size, 6) for count in counts]
    return {
        "interior_fraction": round(float(1.0 - finite.mean()), 6),
        "deciles": deciles,
        "low_end": round(sum(deciles[:END_BINS]), 6),
        "high_end": round(sum(deciles[-END_BINS:]), 6),
        "end_mass": round(max(sum(deciles[:END_BINS]), sum(deciles[-END_BINS:])), 6),
        "peak_decile": int(max(range(SHAPE_BINS), key=lambda index: deciles[index])),
        "peak_mass": round(max(deciles), 6),
        "spread_bits": round(codebook.entropy_bits(deciles), 4),
    }


# --------------------------------------------------------------------------- #
# The panel: drawn from the pool, chosen on shape.
# --------------------------------------------------------------------------- #
def probeable_modes() -> list[str]:
    """Every production mode with one scalar field behind it, in catalog order.

    Read out of the engine's catalog rather than listed here, so a mode cannot be
    probeable on one side of the boundary and not the other.
    """
    from fractal_wallpapers import engine

    production = set(engine.production_modes())
    return [
        entry["name"]
        for entry in engine.modes()
        if entry["name"] in production and entry["coloring"]["kind"] == "field"
    ]


def _pool_rows() -> list[dict]:
    """Every pool row, both stores — the same population the census reads."""
    from fractal_wallpapers.curation import gallery_store, records

    return [*records.read_decisions(records.RELEASE), *gallery_store.read()]


def candidates(log=print) -> list[dict]:
    """The pool rows a panel may be drawn from, one per location x mode, stratified.

    Seeded, and spread by construction rather than by luck: the draw walks each
    probeable mode in turn and prefers partitions it has not taken from yet, so a
    mode the pool happens to hold six hundred rows of does not arrive as six
    hundred rows of one family.
    """
    modes = set(probeable_modes())
    seen: set[tuple] = set()
    by_mode: dict[str, list[dict]] = {name: [] for name in modes}
    for row in _pool_rows():
        recipe = row.get("recipe") or {}
        location = row.get("location") or {}
        mode = recipe.get("mode")
        if mode not in modes or not location.get("key"):
            continue
        key = (location["key"], mode)
        if key in seen:
            continue
        seen.add(key)
        by_mode[mode].append(row)

    rng = random.Random(PANEL_SEED)
    for rows in by_mode.values():
        rng.shuffle(rows)
    per_mode = max(1, PANEL_DRAW // max(1, len(modes)))
    drawn: list[dict] = []
    for mode in sorted(by_mode):
        taken: list[dict] = []
        partitions: set[str] = set()
        for row in by_mode[mode]:
            partition = row["location"].get("partition")
            if partition in partitions and len(partitions) < per_mode:
                continue
            partitions.add(partition)
            taken.append(row)
            if len(taken) >= per_mode:
                break
        drawn.extend(taken)
    log(f"[panel] {len(drawn)} candidate cells drawn over {len(modes)} probeable modes")
    return drawn


def cell_id(row: dict) -> str:
    """A stable, filesystem-safe name for one location x mode cell."""
    import hashlib

    location = row["location"]
    digest = hashlib.sha256(location["key"].encode("utf-8")).hexdigest()[:10]
    return f"{row['recipe']['mode']}_{location['partition'].replace(':', '-')}_{digest}"


def dump(row: dict) -> Path:
    """This cell's field, dumped once. Every recolor of the cell reuses it."""
    from fractal_wallpapers import engine, paths

    location = row["location"]
    fields_dir().mkdir(parents=True, exist_ok=True)
    output = fields_dir() / f"{cell_id(row)}.f32"
    record = output.with_suffix(".json")
    if output.is_file() and record.is_file():
        return record
    engine.dump_field(
        {
            "schema": 1,
            "family": location["family"],
            "viewport": location["viewport"],
            "resolution": list(RESOLUTION),
            "supersample": SUPERSAMPLE,
            "maxiter": int(location["maxiter"]),
            "mode": row["recipe"]["mode"],
            "colormap": "twilight_shifted",
            "colormap_dir": str(paths.colormap_dir()),
            "output": str(output),
        }
    )
    return record


def choose(measured: list[dict], cells: int = PANEL_CELLS) -> list[dict]:
    """The panel: the two hardest pile-ups, every mode, then a spread over shapes.

    Three passes in a fixed order, each stated because each is a claim about what
    the panel can see:

    1. the two cells with the most mass in one end decile, because a mirrored ramp
       strands its far half exactly there and a panel without one of these reports
       a capability production does not have;
    2. one cell per probeable mode, so no field family is missing outright;
    3. the rest spread over the `end_mass` range at even quantiles, preferring a
       partition the panel does not hold yet.
    """
    ranked = sorted(measured, key=lambda cell: (-cell["shape"]["end_mass"], cell["cell"]))
    chosen: list[dict] = list(ranked[:2])
    taken = {cell["cell"] for cell in chosen}

    for mode in sorted({cell["mode"] for cell in measured}):
        if any(cell["mode"] == mode for cell in chosen):
            continue
        of_mode = [cell for cell in ranked if cell["mode"] == mode and cell["cell"] not in taken]
        if of_mode:
            pick = of_mode[len(of_mode) // 2]
            chosen.append(pick)
            taken.add(pick["cell"])

    remaining = [cell for cell in ranked if cell["cell"] not in taken]
    slots = max(0, cells - len(chosen))
    for step in range(slots):
        if not remaining:
            break
        target = (step + 0.5) / slots
        index = min(int(target * len(remaining)), len(remaining) - 1)
        held = {cell["partition"] for cell in chosen}
        fresh = [
            position for position, cell in enumerate(remaining) if cell["partition"] not in held
        ]
        if fresh:
            index = min(fresh, key=lambda position: abs(position - index))
        pick = remaining.pop(index)
        chosen.append(pick)
        taken.add(pick["cell"])
    return sorted(chosen, key=lambda cell: (cell["mode"], cell["cell"]))


def build_panel(log=print) -> dict:
    """Draw, dump, measure and choose. The panel is written and returned."""
    drawn = candidates(log=log)
    measured = []
    for row in drawn:
        record = dump(row)
        location = row["location"]
        measured.append(
            {
                "cell": cell_id(row),
                "mode": row["recipe"]["mode"],
                "kind": "smooth" if row["recipe"]["mode"] == SMOOTH_MODE else "strange",
                "partition": location["partition"],
                "family": location["family"],
                "viewport": location["viewport"],
                "maxiter": int(location["maxiter"]),
                "field": record.with_suffix(".f32").name,
                "shape": field_shape(record),
            }
        )
    log(f"[panel] {len(measured)} fields dumped and measured")
    chosen = choose(measured)
    document = {
        "schema": SCHEMA,
        "seed": PANEL_SEED,
        "drawn": len(measured),
        "cells": chosen,
        "modes": sorted({cell["mode"] for cell in chosen}),
        "partitions": sorted({cell["partition"] for cell in chosen}),
        "kinds": {
            "smooth": sum(1 for cell in chosen if cell["kind"] == "smooth"),
            "strange": sum(1 for cell in chosen if cell["kind"] == "strange"),
        },
        "rule": (
            "drawn from pool rows over the probeable (field-kind) modes, then chosen on "
            "field shape: the two hardest end-decile pile-ups, one cell per mode, then a "
            "spread over the end_mass range preferring unheld partitions"
        ),
        "resolution": list(RESOLUTION),
        "supersample": SUPERSAMPLE,
        "shape_bins": SHAPE_BINS,
    }
    _write_json(panel_path(), document)
    log(
        f"[panel] {len(chosen)} cells chosen: {document['kinds']['smooth']} smooth, "
        f"{document['kinds']['strange']} strange, {len(document['partitions'])} partitions"
    )
    return document


def panel() -> dict:
    """The panel as it was last built, refusing to invent one that is not there."""
    path = panel_path()
    if not path.is_file():
        raise CoverageError(f"{path} is missing — build the panel before probing it")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Read A — the recolor pass.
# --------------------------------------------------------------------------- #
def baked() -> list[str]:
    """Every baked map, in library order. What the panel is put through."""
    from fractal_wallpapers.paths import colormap_dir

    return sorted(path.stem for path in colormap_dir().glob("*.json"))


def of_drop() -> dict[str, str]:
    """`{map: drop}` for every map a tracked batch stamp ships.

    The separation between this batch and the library it landed in is the
    *absence* of the key on an older row, so a map is new exactly when
    provenance gives it a stamp. Nothing here re-derives that from a date.
    """
    from fractal_wallpapers.palettes import provenance

    return {name: row["drop"] for name, row in provenance.read().items() if row.get("drop")}


def _folds(colormap: str, cyclic: set[str]) -> list[tuple[str, bool]]:
    """The folds this map is probed under: production always, unfolded where it differs.

    A cyclic map has one fold and only one — the engine refuses to halve a cycle
    that closes — so the counterfactual exists for sequential maps alone.
    """
    if colormap in cyclic:
        return [("production", False)]
    return [("production", True), ("unfolded", False)]


def probe_cell(cell: dict, maps: list[str], workdir: Path) -> list[dict]:
    """One panel cell through every map under every fold it has. Rows, not files.

    The recolor is written, censused and overwritten: sixteen cells by nine
    hundred maps is a gigabyte of JPEG that answers one question each, and the
    answer is four hundred bytes. Keeping the field and throwing the picture away
    is the same trade the field dump itself is.
    """
    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.models import palette_sets

    cyclic = palette_sets.cyclic()
    workdir.mkdir(parents=True, exist_ok=True)
    picture = workdir / f"{cell['cell']}.jpg"
    field = fields_dir() / cell["field"]
    rows = []
    for colormap in maps:
        for fold, mirror in _folds(colormap, cyclic):
            engine.recolor(
                {
                    "schema": 1,
                    "field": str(field),
                    "colormap": colormap,
                    "colormap_dir": str(paths.colormap_dir()),
                    "palette": finished.recipe(mirror=mirror),
                    "output": str(picture),
                }
            )
            read = codebook.of_picture(picture)
            rows.append(
                {
                    "schema": SCHEMA,
                    "cell": cell["cell"],
                    "mode": cell["mode"],
                    "kind": cell["kind"],
                    "partition": cell["partition"],
                    "colormap": colormap,
                    "fold": fold,
                    "mirror": mirror,
                    **read,
                }
            )
    picture.unlink(missing_ok=True)
    return rows


def _probe_one(payload: tuple) -> list[dict]:
    """A worker's whole job: one cell, every map. Top level so it can be pickled."""
    cell, maps, workdir = payload
    return probe_cell(cell, maps, Path(workdir))


def probe(workers: int = 6, log=print) -> int:
    """Put the panel through every baked map, and write one row per recolor.

    Parallel over cells rather than over maps: a cell is a field the worker holds
    open for its whole run, and splitting a cell across workers would have each
    of them read the same three megabytes.
    """
    import time
    from concurrent.futures import ProcessPoolExecutor

    document = panel()
    maps = baked()
    cells = document["cells"]
    workdir = coverage_dir() / "work"
    started = time.time()
    log(f"[probe] {len(cells)} cells x {len(maps)} maps over {workers} workers")

    written: list[dict] = []
    payloads = [(cell, maps, str(workdir)) for cell in cells]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, rows in enumerate(pool.map(_probe_one, payloads), start=1):
            written.extend(rows)
            log(
                f"[probe] {done}/{len(cells)} cells, {len(written)} rows, "
                f"{time.time() - started:.0f}s"
            )
    count = _write_jsonl(rows_path(), written)
    log(f"[probe] {count} rows in {time.time() - started:.0f}s")
    return count


def read_rows() -> list[dict]:
    """The probe rows as they were last written."""
    path = rows_path()
    if not path.is_file():
        raise CoverageError(f"{path} is missing — probe the panel before reading it")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# --------------------------------------------------------------------------- #
# The tables.
# --------------------------------------------------------------------------- #
def reach(rows: list[dict], fold: str = "production") -> dict[str, dict[str, float]]:
    """`{map: {swatch: best share over the panel}}` under one fold.

    The max is the whole statistic: a map counts for a swatch if *some* cell
    showed it, so a cell where the field never reached that part of the ramp is
    silence rather than evidence against.
    """
    best: dict[str, dict[str, float]] = {}
    for row in rows:
        if row["fold"] != fold:
            continue
        cell = best.setdefault(row["colormap"], {})
        for swatch, share in row["shares"].items():
            if share > cell.get(swatch, 0.0):
                cell[swatch] = share
    return best


def counts(best: dict[str, dict[str, float]], maps=None) -> dict:
    """Per swatch, how many of these maps clear each threshold somewhere on the panel."""
    names = codebook.names()
    population = list(maps) if maps is not None else sorted(best)
    table = {}
    for name in names:
        cell = {}
        for threshold in THRESHOLDS:
            cell[f"at_{int(threshold * 100)}pct"] = sum(
                1 for colormap in population if best.get(colormap, {}).get(name, 0.0) >= threshold
            )
        table[name] = cell
    return {"maps": len(population), "swatches": table}


def carriers(best: dict[str, dict[str, float]], maps, swatch: str, threshold: float) -> list[tuple]:
    """Which of these maps reach a swatch, best first. The names behind a count."""
    found = [
        (colormap, round(best.get(colormap, {}).get(swatch, 0.0), 4))
        for colormap in maps
        if best.get(colormap, {}).get(swatch, 0.0) >= threshold
    ]
    return sorted(found, key=lambda entry: -entry[1])


def false_capabilities(rows: list[dict]) -> list[dict]:
    """Every (map, swatch) reached only with the fold off — never under production.

    Reported apart from the main table and counted in neither: production folds a
    sequential map, so a swatch that needs the fold off is a capability of a
    picture this pipeline does not make.
    """
    production = reach(rows, "production")
    unfolded = reach(rows, "unfolded")
    out = []
    for colormap in sorted(unfolded):
        for swatch in codebook.names():
            open_share = unfolded[colormap].get(swatch, 0.0)
            folded_share = production.get(colormap, {}).get(swatch, 0.0)
            reached = [t for t in THRESHOLDS if open_share >= t > folded_share]
            if reached:
                out.append(
                    {
                        "colormap": colormap,
                        "swatch": swatch,
                        "unfolded": round(open_share, 4),
                        "production": round(folded_share, 4),
                        "thresholds": [int(t * 100) for t in reached],
                    }
                )
    return out


# --------------------------------------------------------------------------- #
# Read B — realized supply, off the census the pool already has.
# --------------------------------------------------------------------------- #
def realized(log=print) -> dict:
    """Distinct maps that have ever produced a pool render carrying each swatch.

    Reuses the colour census's own per-picture share vectors — stage 3's survival
    rows — and re-renders nothing. A different estimand from the panel read: it
    is conditioned on which locations the walk found and which map the palette
    head picked for each, so a swatch can be thin here and abundant there, and
    that gap is the reading rather than a disagreement.
    """
    from fractal_wallpapers.curation import colors

    path = colors.rows_path()
    if not path.is_file():
        raise CoverageError(f"{path} is missing — take the colour census first")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and '"survival"' in line
    ]
    rows = [row for row in rows if row.get("stage") == "survival"]
    if not rows:
        raise CoverageError(f"{path} holds no survival row, so nothing has been realized")

    names = codebook.names()
    seen: dict[str, dict[str, float]] = {}
    for row in rows:
        colormap = row.get("colormap")
        if not colormap:
            continue
        cell = seen.setdefault(colormap, {})
        for swatch, share in row["shares"].items():
            if share > cell.get(swatch, 0.0):
                cell[swatch] = share
    table = {}
    for name in names:
        cell = {}
        for threshold in THRESHOLDS:
            cell[f"at_{int(threshold * 100)}pct"] = sum(
                1 for shares in seen.values() if shares.get(name, 0.0) >= threshold
            )
        table[name] = cell
    log(f"[realized] {len(rows)} pool renders over {len(seen)} distinct maps")
    return {
        "renders": len(rows),
        "maps": len(seen),
        "swatches": table,
        "estimand": (
            "distinct maps that have ever produced a pool render carrying the swatch. "
            "Conditioned on what the walk found and what the palette head picked, so it "
            "is a lower bound on capability and never pooled with the panel read"
        ),
        "source": str(path),
    }


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def take(log=print) -> dict:
    """Both reads, side by side, over the rows the probe wrote and the census holds."""
    from datetime import UTC, datetime

    document = panel()
    rows = read_rows()
    maps = baked()
    drops = of_drop()
    fresh = [name for name in maps if name in drops]
    prior = [name for name in maps if name not in drops]

    best = reach(rows, "production")
    capability = {
        "all": counts(best, maps),
        "prior": counts(best, prior),
        "drop": counts(best, fresh),
    }
    false = false_capabilities(rows)
    log(
        f"[capability] {len(maps)} maps ({len(prior)} pre-existing, {len(fresh)} in the drop); "
        f"{len(false)} false capabilities under the fold"
    )

    readout = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "thresholds": list(THRESHOLDS),
        "codebook": codebook.document(),
        "panel": document,
        "capability": capability,
        "false_capabilities": false,
        "realized": realized(log=log),
        "population": {
            "maps": len(maps),
            "prior_maps": len(prior),
            "drop_maps": len(fresh),
            "drops": sorted(set(drops.values())),
            "probe_rows": len(rows),
            "recipe": (
                "every palette knob at the identity (gamma 1.0, cycles 1.0, phase 0.0, "
                "reverse off) and mirror = colormap not in cyclic. Production samples "
                "none of these, so the panel is the only thing the max is taken over"
            ),
        },
        "estimands": (
            "capability is a max over a 16-cell probe panel and is bounded by it — a wider "
            "panel can only raise a count. realized is a count over renders that happened. "
            "They answer different questions and are never pooled or averaged"
        ),
    }
    _write_json(readout_path(), readout)
    return readout


def thinnest(readout: dict, count: int = 4, threshold: float = 0.10) -> list[str]:
    """The swatches fewest maps can reach on the panel, gamut-limited ones included.

    Ordered by the capability count at `threshold`, ties broken by the count at the
    lowest threshold, so a swatch nothing reaches at 10% but many touch at 5% sorts
    behind one that is thin all the way down.
    """
    key = f"at_{int(threshold * 100)}pct"
    lowest = f"at_{int(THRESHOLDS[0] * 100)}pct"
    table = readout["capability"]["all"]["swatches"]
    ordered = sorted(table.items(), key=lambda item: (item[1][key], item[1][lowest], item[0]))
    return [swatch for swatch, _ in ordered[:count]]


# --------------------------------------------------------------------------- #
# The contact sheet: what each threshold actually looks like.
# --------------------------------------------------------------------------- #
#: How wide a tile is drawn on the sheet. Small enough that a row of four fits a
#: screen, large enough that a 5% presence is visible as a colour rather than a
#: rumour.
TILE_WIDTH = 320


def _example_for(rows: list[dict], swatch: str, threshold: float, ceiling: float | None):
    """The probe row whose share of this swatch sits lowest inside the band.

    Lowest rather than best on purpose: the sheet exists so a bar can be set by
    eye, and the picture worth looking at is the *weakest* one a threshold still
    admits. A tile showing the best example of 5% would make 5% look sufficient
    when the row that decided the count looks like nothing.
    """
    inside = [
        row
        for row in rows
        if row["fold"] == "production"
        and row["shares"].get(swatch, 0.0) >= threshold
        and (ceiling is None or row["shares"].get(swatch, 0.0) < ceiling)
    ]
    if not inside:
        return None
    return min(inside, key=lambda row: row["shares"][swatch])


def contact_sheet(readout: dict, rows: list[dict], directory: Path, log=print) -> Path:
    """One tile per threshold for the thinnest swatches, so the bar is set by eye.

    Four rows of four pictures, each the weakest example its threshold admits,
    beside the codebook's own chip for the swatch. The tiles are re-made here
    rather than kept from the probe — a recolor is forty milliseconds and sixteen
    of them is cheaper than the gigabyte keeping them all would have cost.
    """
    import html

    from fractal_wallpapers import engine, paths
    from fractal_wallpapers.labeling import finished

    directory = Path(directory)
    tiles = directory / "tiles"
    tiles.mkdir(parents=True, exist_ok=True)
    chips = {entry["swatch"]: entry for entry in codebook.swatches()}
    wanted = thinnest(readout)
    by_cell = {cell["cell"]: cell for cell in readout["panel"]["cells"]}

    out = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>palette coverage: the thinnest swatches at each threshold</title>",
        "<style>body{background:#111;color:#ddd;font:14px/1.5 system-ui,sans-serif;"
        "margin:24px}h1{font-size:20px}h2{font-size:16px;margin:28px 0 8px}"
        f"td{{vertical-align:top;padding:0 12px 18px 0}}img{{width:{TILE_WIDTH}px;"
        "display:block;border-radius:3px}.chip{display:inline-block;width:14px;"
        "height:14px;border-radius:3px;vertical-align:-2px;margin-right:6px}"
        ".miss{opacity:.5;font-style:italic}</style>",
        "<h1>What a threshold looks like</h1>",
        "<p>The <b>weakest</b> panel picture each threshold still admits, for the four "
        "swatches fewest maps can reach. Production recipe, production fold. The bar is "
        "not set here &mdash; this is what setting it would be choosing between.</p>",
    ]
    made = 0
    for swatch in wanted:
        entry = chips[swatch]
        red, green, blue = entry["srgb"]
        limited = " &middot; gamut-limited" if entry["gamut_limited"] else ""
        out.append(
            f"<h2><span class='chip' style='background:rgb({red},{green},{blue})'></span>"
            f"{html.escape(swatch)}{limited}</h2><table><tr>"
        )
        for index, threshold in enumerate(THRESHOLDS):
            ceiling = THRESHOLDS[index + 1] if index + 1 < len(THRESHOLDS) else None
            row = _example_for(rows, swatch, threshold, ceiling)
            label = f"&ge;{int(threshold * 100)}%"
            if row is None:
                out.append(f"<td class='miss'>{label}<br>nothing on the panel</td>")
                continue
            cell = by_cell[row["cell"]]
            name = f"{swatch}_{int(threshold * 100)}_{row['cell']}_{row['colormap']}.jpg"
            name = "".join(char if char.isalnum() or char in "._-" else "-" for char in name)
            engine.recolor(
                {
                    "schema": 1,
                    "field": str(fields_dir() / cell["field"]),
                    "colormap": row["colormap"],
                    "colormap_dir": str(paths.colormap_dir()),
                    "palette": finished.recipe(mirror=row["mirror"]),
                    "output": str(tiles / name),
                }
            )
            made += 1
            share = row["shares"][swatch]
            out.append(
                f"<td><img src='tiles/{html.escape(name)}' alt=''>"
                f"<b>{label}</b> &mdash; measured {share:.3f}<br>"
                f"{html.escape(row['colormap'])}<br>"
                f"{html.escape(row['mode'])} &middot; {html.escape(row['partition'])}"
                f"{' &middot; folded' if row['mirror'] else ''}</td>"
            )
        out.append("</tr></table>")
    directory.mkdir(parents=True, exist_ok=True)
    page = directory / "coverage_tiles.html"
    page.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    log(f"[sheet] {made} tiles over {len(wanted)} swatches -> {page}")
    return page


__all__ = [
    "PANEL_CELLS",
    "PANEL_DRAW",
    "PANEL_SEED",
    "RESOLUTION",
    "SCHEMA",
    "SUPERSAMPLE",
    "THRESHOLDS",
    "CoverageError",
    "baked",
    "build_panel",
    "candidates",
    "carriers",
    "cell_id",
    "choose",
    "contact_sheet",
    "counts",
    "coverage_dir",
    "dump",
    "false_capabilities",
    "field_shape",
    "fields_dir",
    "of_drop",
    "panel",
    "panel_path",
    "probe",
    "probe_cell",
    "probeable_modes",
    "reach",
    "read_rows",
    "readout_path",
    "realized",
    "rows_path",
    "take",
    "thinnest",
]
