"""What `Palette.phase` actually moves, mode by mode, measured off the pixels.

A varied mining draw spends a third of its shots on `phase` — `depth.palette_drawn`
holds it at exactly 0 three times in ten and draws uniformly over the turn the rest
of the time — across every mode that is not a direct trap. On a mode where the shift
changes nothing those renders buy nothing, and until this module nothing in the tree
could say which modes those are. This renders the same recipe at several phases and
looks at the pixels.

**It is a measurement and not a study of adoption.** No head reads anything here, no
row reaches the candidate pool, and nothing about the draw moves: `depth.PALETTE_REPEATS`,
`depth.PALETTE_PHASE_HELD` and `depth.vary_palettes` are read and never touched. What
the leg produces is a table, and the decision about what mining draws is Matt's.

## `Palette.phase` is not `palettes.variants.phase`

Two things in this repository are called a phase and they are not the same operation.
[`palettes.variants.phase`] rolls a colormap's stops and writes a **new map**, which is
how a leg that wants a rotated gradient under its own recipe key gets one. This axis is
the engine's own recipe member — `engine/src/coloring.rs`'s `Palette::phase`, spent in
`Palette::place` as `frac(frac(gray · cycles) + phase)` — and it moves where the
traversal of an unchanged map starts. On a cyclic map at `cycles = 1` the two land on
near enough the same picture; on a folded one they do not, because the fold is applied
to the baked ramp and the traversal reads the folded result.

## The four direct traps are the harness control

`coloring::shade`'s `Coloring::Direct` arm hands `direct_trap::Painter::new` the shape,
the radius, the threshold, the opacity, the merge and the start colour, and **never the
`Palette`**. So there is no field for a traversal to start anywhere in and the axis is a
byte-for-byte no-op on those four modes by construction — the claim [`colorize.DIRECT_KIND`]
and `curation/LEGS.md`'s *`--vary-palette` — moving the palette block, and nothing else*
already carry off the eye sheet of 2026-09-10. A pass whose traps come back anything but
identical has a broken harness, and the rest of its table means nothing. [`control`] is
that reading, and `curate phase-response` **refuses on it** — the table is printed and the
command still fails, because a reader who sees only the table cannot tell that it is void.

## What a mode's flatness would be MADE of

`coloring.rs`'s `INTERIOR = [0.0, 0.0, 0.0]` is hard black and never goes through the
map. So on the exterior-only fields the share of frame a traversal can reach at all is
`1 − interior_fraction`, and a mode drawn at a place with a large interior is flat over
that share of the frame however far the phase moves. Three of the nineteen fill the
interior — `gaussian_int`, `trap_circle` and the composite over the second of them — and
the rest leave it black. Each row therefore carries [`black_share`] beside its distances,
because a mode that reads flat for that reason is flat *at that place* rather than flat.

⚠ **`flat` here is the axis and not [`curation.flatness`]**, which is dead space in a
picture — cells a plane fits with nothing left over — and is a fitted column of the rank
key. The two words are near neighbours and the quantities are unrelated: a picture can be
all structure and still not move when the phase does.

## Levelling is OFF, and that is what makes this a reading of the axis

The autolevel operator derives its curve from the picture's own histogram, so a phase
shift moves the histogram, which moves the curve, which moves the picture a second time.
Measured with the switch on, the column would be *phase plus re-levelling* and nothing
here could separate them — the same trap `palettes/README.md` records for the baked
lightness axis, where the operator acted on 100% of one dose's rows. Every render here
passes `level=False`. **The levelled arm is therefore unmeasured**, and production draws
levelled, so a mode this table calls live is live before the operator sees it.

## The unit of work, and why the sweep goes phase by phase

A phase is spent after the field is read, so on the seven `field` modes every phase of
one (location, mode) is a colormap lookup over one iteration pass — `colorize.render`
decides that on its own through [`colorize.shareable`], and the twelve modes with no
single scalar field behind them pay a full render each. That is a thirty-fold spread in
price across the roster, which is what makes the sweep's **order** a decision:

[`run`] renders the whole grid's **baselines** first, then one phase at a time over the
whole grid. A clock that binds therefore takes the outer phases from every mode equally,
where a mode-major sweep would have taken whole modes — and a table missing a mode cannot
answer the question that was asked. That is the rule this leg cuts by and the only one
it has: phases before places, and never a mode.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fractal_wallpapers.paths import under

#: The schema every row and record this module writes carries.
SCHEMA = 1

#: The subtree under `artifacts/curation/` a pass of this keeps its work in.
UNIT = "phase_response"

#: The phases a pass asks, in the order it asks them, as turns of the gradient.
#:
#: **Three, and the count is the point.** Whether an axis moves a mode at all is
#: visible at the first dose that is not the identity — a no-op is a no-op at every
#: phase, and a mode that moves is not going to hide it — so a spread wide enough to
#: read a *dose response* is a spread spent on a question nobody asked. Matt's
#: instruction of 2026-09-12, and it is the difference between seven minutes and
#: forty: the roster runs nineteen modes at a thirty-fold spread in price, so every
#: phase added is a whole grid.
#:
#: The three are not evenly spaced. `0.05` is there because
#: `curation/LEGS_decisions.md`'s *What the first pass found* measured the winning
#: rotation of a stored recipe as usually a **small** one, so a spread starting at a
#: quarter would miss the regime a mining draw most often lands a useful shot in.
#: `0.5` is there because a **folded** traversal is not symmetric in phase — the ramp
#: the engine reads is an out-and-back — so the antipode is where an asymmetry would
#: show. `0.25` is between them.
#:
#: Ordered small to large because [`run`] sweeps one phase at a time over the whole
#: grid and a clock that binds takes the tail.
PHASES: tuple[float, ...] = (0.05, 0.25, 0.5)

#: The baseline every phase in a cell is compared against. Zero, and named rather
#: than written as a literal at three sites, because it is also the phase every
#: recipe in the candidate pool was chosen at — `curation/LEGS.md`'s *`curate
#: rotate`* is the leg that exists because of it.
BASE_PHASE = 0.0

#: Oklab ΔE at or above which a pixel counts as **moved**, for [`compare`]'s
#: `moved` share. 0.02, which is the scale a just-noticeable difference is usually
#: quoted at in this space — Oklab's L runs 0 to 1, so this is two parts in a
#: hundred of the whole lightness range. It is a **reporting** threshold and
#: nothing here decides on it: the verdict is read off the distribution of means
#: and high percentiles, and this column only says how much of the frame carried
#: whatever change there was. A mode with a large mean and a small `moved` share
#: moved a little of the picture a long way; the reverse moved all of it slightly.
JND = 0.02

#: The high percentile every row reports beside its mean. Two of them, because the
#: pair separates the two shapes above without a reader having to ask for the
#: histogram: a phase shift that recolours the whole frame moves the mean and the
#: percentiles together, and one that only reaches a thin band of the field moves
#: the percentiles alone.
PERCENTILES: tuple[float, ...] = (95.0, 99.0)

#: Where the location panel is drawn from: the tracked release records of
#: `gallery3`, 150 seats over nine partitions. Tracked rather than the candidate
#: ledger on purpose — **nothing in this module holds the candidate pool**, so the
#: one-pool-holding-process rule does not bind on a pass of it, and the panel a
#: record names is one a clone can resolve without an artifacts tree.
PANEL_RUN = "gallery3"

#: The half of that population a place is drawn from, by iteration cap. **The
#: shallow half.** Depth is not what this measures — a phase is spent after the
#: field is read, so the cap buys the same picture more slowly — and it is very
#: nearly the whole price: `gallery3`'s caps run 4,923 to 49,351 with a median of
#: 16,584, so drawing over the whole population would spend a third of the clock
#: on the two deepest places and return the same answer. Stated here rather than
#: left in a docstring because it is a bias in the panel and a reader of the table
#: has to know it is there.
SHALLOW_SHARE = 0.5

#: One place per partition. A panel of four places at one partition would measure
#: one family's field four times, and what the spread within a mode has to be read
#: across is *places that are not alike*.
ONE_PER_PARTITION = True

#: The default panel: **two places and two maps**, which with [`PHASES`] is four
#: tiers over seventy-six cells and a few minutes of wall.
#:
#: Two maps rather than one because `mirror` is read off a map's own kind and the
#: two kinds are different objects to traverse, so one of each is the smallest panel
#: that can tell a mode's response from a kind's. Two places rather than one because
#: `coloring.rs`'s `INTERIOR` is hard black and outside the map, so how much of the
#: frame the axis can reach is a property of the *place*, and a single place could
#: not separate a flat mode from a flat location. Two of each is the floor under
#: both of those and not a sample of anything: a **spread** read across two is a
#: range and never a distribution, which is what `map_ratio` in [`summarise`] is for
#: and what the report has to say out loud. [`sized`] is what a pass with a clock
#: actually uses.
DEFAULT_PLACES = 2
DEFAULT_MAPS = 2

#: The seed for the place draw, the map draw and the pool collapse. One seed for
#: all three so a pass is named by a single integer, and recorded, because a panel
#: nobody can redraw is a table nobody can check.
DEFAULT_SEED = 0

#: The workers a pass drives the engine with. This machine's rule and not a knob —
#: more than three `fractal-engine` at once makes the desktop unusable — restated
#: off the module that owns it.
DEFAULT_WORKERS = 3


class PhaseResponseRefused(RuntimeError):
    """A panel this pass will not measure, or a pass that wrote nothing."""


# --------------------------------------------------------------------------- #
# Where it keeps things.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree every pass of this module keeps a directory under."""
    return under("curation", UNIT)


def pass_dir(name: str) -> Path:
    """The subtree one pass owns: its rows, its record, its baselines, its fields."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    return pass_dir(name) / "rows.jsonl"


def record_path(name: str) -> Path:
    return pass_dir(name) / "record.json"


# --------------------------------------------------------------------------- #
# The panel.
# --------------------------------------------------------------------------- #
def population() -> list[dict]:
    """Every seat of the tracked panel run, as places this module can render.

    One dict a seat carrying the engine's three — family, viewport, cap — plus the
    location key and partition a row is filed under, so a record names its panel in
    the same spelling every other record in this project names a place.
    """
    from fractal_wallpapers.paths import repo_root

    root = repo_root() / "data" / "curation" / "release" / PANEL_RUN
    if not root.is_dir():
        raise PhaseResponseRefused(f"{root} is not there, so there is no panel to draw from")
    out: list[dict] = []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            location = json.loads(line)["location"]
            out.append(
                {
                    "key": location["key"],
                    "partition": location["partition"],
                    "family": location["family"],
                    "viewport": location["viewport"],
                    "maxiter": int(location["maxiter"]),
                }
            )
    if not out:
        raise PhaseResponseRefused(f"{root} holds no rows")
    return out


def places(count: int = DEFAULT_PLACES, seed: int = DEFAULT_SEED) -> list[dict]:
    """`count` places, drawn seeded over the shallow half, at most one a partition.

    Sorted by location key before the draw and not left in file order: the draw has
    to be a function of the seed alone, and a record read back years later has to
    redraw the same panel from the same integer whether or not a file was rewritten
    in between.
    """
    import random

    everything = sorted(population(), key=lambda place: place["key"])
    ranked = sorted(everything, key=lambda place: place["maxiter"])
    shallow = ranked[: max(1, int(len(ranked) * SHALLOW_SHARE))]
    draw = random.Random(seed)
    order = list(shallow)
    draw.shuffle(order)
    out: list[dict] = []
    taken: set[str] = set()
    for place in order:
        if ONE_PER_PARTITION and place["partition"] in taken:
            continue
        taken.add(place["partition"])
        out.append(place)
        if len(out) >= int(count):
            break
    if len(out) < int(count):
        raise PhaseResponseRefused(
            f"the shallow half of {PANEL_RUN} offers {len(out)} places at one a partition and "
            f"{count} were asked for; lower the count or widen SHALLOW_SHARE"
        )
    return out


def maps(count: int = DEFAULT_MAPS, seed: int = DEFAULT_SEED, cyclic: set | None = None) -> list:
    """`count` maps off the drawable pool, half cyclic and half folded.

    **Both kinds, and in stated proportion.** `mirror` is read off the map's own
    `kind` everywhere in this project — a sequential map is folded to hide the seam
    its two ends would show and a cyclic one is not — so the ramp a traversal reads
    is a different object on the two kinds, and a panel of one kind could not tell
    a mode's response from a kind's. An odd `count` gives the extra to the cyclic
    side, which is the larger half of the library.

    Returned sorted, so the panel a record names does not depend on the order a
    shuffle happened to leave two independent draws in.
    """
    import random

    from fractal_wallpapers.curation import colorize

    known = colorize.cyclic() if cyclic is None else cyclic
    pool = colorize.pool(seed)
    loops = sorted(name for name in pool if name in known)
    folds = sorted(name for name in pool if name not in known)
    wanted = int(count)
    want_folds = wanted // 2
    want_loops = wanted - want_folds
    if len(loops) < want_loops or len(folds) < want_folds:
        raise PhaseResponseRefused(
            f"the drawable pool offers {len(loops)} cyclic and {len(folds)} folded maps, and "
            f"{want_loops} and {want_folds} were asked for"
        )
    draw = random.Random(seed)
    return sorted(draw.sample(loops, want_loops) + draw.sample(folds, want_folds))


# --------------------------------------------------------------------------- #
# The metric.
# --------------------------------------------------------------------------- #
def read_pixels(picture: Path):
    """One picture's pixels as sRGB8, at the size it was written.

    Not [`palettes.codebook.pixels`], which brings every picture to the census size
    so two of them are the same count. These two are the same render at the same
    geometry by construction, and the question is how far apart they are pixel for
    pixel, so a resample would be an averaging step between the measurement and
    the thing measured.
    """
    import numpy
    from PIL import Image

    path = Path(picture)
    if not path.is_file():
        raise PhaseResponseRefused(f"{path} is not there, so it cannot be read")
    with Image.open(path) as opened:
        return numpy.asarray(opened.convert("RGB"), dtype=numpy.uint8)


def black_share(pixels) -> float:
    """The share of the frame that is exactly black.

    The **ceiling on flatness a place imposes**, read off the picture rather than
    off a report, because it has to be available on both render paths and the
    recolour path fills no report at all. `coloring.rs`'s `INTERIOR` is exactly
    `[0, 0, 0]` and never goes through the map, so on an exterior-only field this
    is the interior, and no phase can reach it.

    It reads a little high on a map whose own dark end quantises to `(0, 0, 0)`,
    which is why the name is what is measured rather than what it stands for.
    """
    import numpy

    flat = numpy.asarray(pixels).reshape(-1, 3)
    return float(numpy.count_nonzero(~flat.any(axis=1)) / max(1, len(flat)))


def difference(base_pixels, other_pixels) -> dict:
    """How far two renders of one recipe are apart, per pixel, in Oklab.

    Euclidean ΔE over `(L, a, b)` through [`palettes.space.oklab`] — the
    repository's single copy of the arithmetic, so this reading and the autolevel
    band's and the palette metric's are in one unit. Reported as the mean, the
    [`PERCENTILES`] and the [`JND`] share, which between them say both how far the
    picture moved and how much of it did.
    """
    import numpy

    from fractal_wallpapers.palettes import space

    base = numpy.asarray(base_pixels)
    other = numpy.asarray(other_pixels)
    if base.shape != other.shape:
        raise PhaseResponseRefused(
            f"a phase variant came back {other.shape} against the baseline's {base.shape}"
        )
    delta = space.oklab(base.reshape(-1, 3)) - space.oklab(other.reshape(-1, 3))
    distance = numpy.sqrt(numpy.einsum("ij,ij->i", delta, delta))
    cuts = numpy.percentile(distance, list(PERCENTILES))
    out = {
        "mean": round(float(distance.mean()), 6),
        "moved": round(float(numpy.count_nonzero(distance >= JND) / max(1, distance.size)), 6),
    }
    for percentile, value in zip(PERCENTILES, cuts, strict=True):
        out[f"p{percentile:g}"] = round(float(value), 6)
    return out


def digest(picture: Path) -> str:
    """One picture's sha256. The identity half of the reading, and the control."""
    import hashlib

    return hashlib.sha256(Path(picture).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# One cell.
# --------------------------------------------------------------------------- #
def recipe_at(colormap: str, cyclic: set, phase: float) -> dict:
    """The plain candidate pass with `phase` moved and nothing else.

    Through [`labeling.finished.recipe`] rather than a dict spelled here, so the
    six knobs this does not move are the six a candidate leg would have drawn and a
    knob added to the recipe later cannot be silently left out of the baseline.
    """
    from fractal_wallpapers.labeling import finished

    return finished.recipe(mirror=colormap not in cyclic, phase=float(phase))


def baseline_name(mode: str, place: dict, colormap: str) -> str:
    """The file one cell's baseline is kept under, unique over the whole grid.

    The place is **digested and not spelled**: a location key is the JSON text of an
    array, so it carries quotes and brackets, and a Windows path holding one is a
    `WinError 123` rather than a bad name. The partition rides along in the clear
    because it is what a person looking in the directory wants to see, and its own
    colon is the other character that cannot be in a path here.

    A map name can carry a space and does — `Sorbet Vault` — and that is fine on both
    platforms. What it must not carry is a separator, and no map in the library does.
    """
    import hashlib

    partition = str(place["partition"]).replace(":", "-")
    where = hashlib.sha256(str(place["key"]).encode("utf-8")).hexdigest()[:12]
    return f"{mode}__{partition}__{where}__{colormap}"


def row_of(
    mode: str,
    place: dict,
    colormap: str,
    cyclic: set,
    phase: float,
    reading: dict,
    identical: bool,
    seconds: float,
) -> dict:
    """One phase of one cell, in this log's row shape and field order."""
    from fractal_wallpapers.curation import colorize

    row = {
        "schema": SCHEMA,
        "mode": mode,
        "mode_kind": colorize.kind_of(mode),
        "location": place["key"],
        "partition": place["partition"],
        "maxiter": int(place["maxiter"]),
        "colormap": colormap,
        "mirror": colormap not in cyclic,
        "phase": float(phase),
        "identical": bool(identical),
    }
    row.update(reading)
    row["seconds"] = round(float(seconds), 3)
    return row


def _render(
    place: dict,
    mode: str,
    colormap: str,
    cyclic: set,
    phase: float,
    output: Path,
    workdir: Path,
) -> tuple[Path, float]:
    """One picture of one cell at one phase, through the one place a picture is made.

    `level=False`, for the reason the module docstring gives; `fields` is the pass's
    own directory, so a `field` mode dumps once a (location, mode) and every phase
    and every map after it is a colormap lookup.
    """
    from fractal_wallpapers.curation import colorize

    output.unlink(missing_ok=True)
    started = time.perf_counter()
    colorize.render(
        {"family": place["family"], "viewport": place["viewport"], "maxiter": place["maxiter"]},
        mode,
        colormap,
        cyclic,
        output,
        level=False,
        fields=workdir / "fields",
        palette=recipe_at(colormap, cyclic, phase),
    )
    return output, time.perf_counter() - started


def baseline(place: dict, mode: str, colormap: str, cyclic: set, workdir: Path) -> dict:
    """The phase-0 picture of one cell, kept, plus what a comparison needs of it.

    Kept on disk rather than in memory: the whole grid's baselines are live at once
    while the phases sweep over it, and nineteen modes over a four-by-four panel is
    three hundred and four pictures — a hundred and fifty megabytes on disk against
    the two hundred megabytes of `uint8` that holding them would cost, in a process
    that is also holding a render pool.
    """
    picture = workdir / "baselines" / f"{baseline_name(mode, place, colormap)}.png"
    picture.parent.mkdir(parents=True, exist_ok=True)
    _made, spent = _render(place, mode, colormap, cyclic, BASE_PHASE, picture, workdir)
    pixels = read_pixels(picture)
    return {
        "picture": picture,
        "digest": digest(picture),
        "black_share": round(black_share(pixels), 6),
        "seconds": spent,
    }


def phase_row(
    place: dict,
    mode: str,
    colormap: str,
    cyclic: set,
    phase: float,
    base: dict,
    workdir: Path,
) -> dict:
    """One phase of one cell rendered, read against its baseline, and swept.

    The variant is unlinked as soon as it has been read. A full pass makes some
    thousands of these and none of them is wanted again — the row is the artifact —
    so keeping them would be a gigabyte of PNG for nothing.
    """
    variant = workdir / "variants" / f"{baseline_name(mode, place, colormap)}__{phase:g}.png"
    variant.parent.mkdir(parents=True, exist_ok=True)
    _made, spent = _render(place, mode, colormap, cyclic, phase, variant, workdir)
    identical = digest(variant) == base["digest"]
    reading = difference(read_pixels(base["picture"]), read_pixels(variant))
    reading["black_share"] = base["black_share"]
    variant.unlink(missing_ok=True)
    return row_of(mode, place, colormap, cyclic, phase, reading, identical, spent)


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
def cells(modes: list[str], panel: list[dict], library: list[str]) -> list[tuple]:
    """Every `(mode, place, colormap)` the grid holds, in the engine's mode order.

    Mode-major inside a phase tier so a `field` mode's dump is asked for once and
    then found, and place before map inside a mode for the same reason.
    """
    return [(mode, place, colormap) for mode in modes for place in panel for colormap in library]


def _warm_fields(modes: list[str], panel: list[dict], workdir: Path) -> None:
    """Dump each shareable mode's field at each place, serially, before a pool opens.

    Three threads asking for a field nobody has dumped yet is three iteration
    passes over one array and two of them are paid for nothing —
    `palettes.mass_sweep.run` learned this and the comment is its.
    """
    from fractal_wallpapers.curation import colorize

    for mode in modes:
        if not colorize.shareable(mode):
            continue
        for place in panel:
            colorize.field_of(
                {
                    "family": place["family"],
                    "viewport": place["viewport"],
                    "maxiter": place["maxiter"],
                },
                workdir / "fields",
                mode=mode,
                curve=colorize.CURVE,
            )


def run(
    modes: list[str],
    panel: list[dict],
    library: list[str],
    workdir: Path,
    phases: tuple[float, ...] = PHASES,
    workers: int = DEFAULT_WORKERS,
    budget: float | None = None,
    log=print,
) -> tuple[list[dict], dict]:
    """`(rows, report)` — the grid's baselines, then one phase at a time over it.

    **A phase is finished or not started, and a mode is never cut.** The clock, if
    it binds, takes the tail of [`phases`] from every mode at once, which is a
    stated absence a reader can price; a mode-major sweep would have taken whole
    rows out of the table and the question is a per-mode one.
    """
    from fractal_wallpapers.curation import colorize

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cyclic = colorize.cyclic()
    grid = cells(modes, panel, library)
    started = time.perf_counter()

    _warm_fields(modes, panel, workdir)
    log(f"[phase-response] fields warmed in {time.perf_counter() - started:.1f} s")

    at = time.perf_counter()
    bases: dict[tuple, dict] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        made = list(
            pool.map(
                lambda cell: (cell, baseline(cell[1], cell[0], cell[2], cyclic, workdir)),
                grid,
            )
        )
    for cell, base in made:
        bases[(cell[0], cell[1]["key"], cell[2])] = base
    spent = sum(base["seconds"] for _cell, base in made)
    log(
        f"[phase-response] {len(made):5} baseline(s)  {spent:8.1f} engine s  "
        f"{time.perf_counter() - at:8.1f} s wall"
    )

    rows: list[dict] = []
    done: list[float] = []
    for phase in phases:
        left = None if budget is None else budget - (time.perf_counter() - started)
        if left is not None and left <= 0:
            break
        at = time.perf_counter()
        with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
            made_rows = list(
                pool.map(
                    lambda cell, phase=phase: phase_row(
                        cell[1],
                        cell[0],
                        cell[2],
                        cyclic,
                        phase,
                        bases[(cell[0], cell[1]["key"], cell[2])],
                        workdir,
                    ),
                    grid,
                )
            )
        rows.extend(made_rows)
        done.append(phase)
        engine_seconds = sum(row["seconds"] for row in made_rows)
        log(
            f"[phase-response] phase {phase:<6g} {len(made_rows):5} render(s)  "
            f"{engine_seconds:8.1f} engine s  {time.perf_counter() - at:8.1f} s wall"
        )

    # Everything the pass made but the rows goes, and the rows ARE the artifact.
    # The baselines are the last pictures standing; the dumped fields are 3.5 MiB
    # each at candidate geometry and the whole grid's are tens of megabytes of
    # regenerable array — `curation/README.md`'s three-way rule calls anything
    # re-derivable from what is hot a delete, and a leg that left them would leave
    # that much again per pass under a name nothing reads.
    for base in bases.values():
        base["picture"].unlink(missing_ok=True)
    swept = colorize.sweep_fields(workdir / "fields", keep=0)
    report = {
        "modes": list(modes),
        "places": [place["key"] for place in panel],
        "partitions": sorted({place["partition"] for place in panel}),
        "maps": list(library),
        "phases_measured": done,
        "phases_left": [phase for phase in phases if phase not in done],
        "cells": len(grid),
        "rows": len(rows),
        "baseline_seconds": round(spent, 1),
        "engine_seconds": round(spent + sum(row["seconds"] for row in rows), 1),
        "wall_seconds": round(time.perf_counter() - started, 1),
        "fields_swept": swept,
        "leveled": False,
    }
    report["concurrency"] = round(report["engine_seconds"] / max(1e-9, report["wall_seconds"]), 3)
    return rows, report


# --------------------------------------------------------------------------- #
# The reading.
# --------------------------------------------------------------------------- #
def control(rows: list[dict]) -> dict:
    """The four direct traps' reading, which is the harness's own check.

    `{"cells": n, "identical": n, "passed": bool, "modes": {...}}`. A trap that
    comes back anything but byte-identical means the palette pass reached a picture
    it cannot reach, and then nothing else in the table is a reading of the axis.
    """
    from fractal_wallpapers.curation import colorize

    traps = [row for row in rows if row["mode_kind"] == colorize.DIRECT_KIND]
    by_mode: dict[str, dict] = {}
    for row in traps:
        seen = by_mode.setdefault(row["mode"], {"cells": 0, "identical": 0, "worst": 0.0})
        seen["cells"] += 1
        seen["identical"] += int(bool(row["identical"]))
        seen["worst"] = max(seen["worst"], float(row["mean"]))
    return {
        "cells": len(traps),
        "identical": sum(1 for row in traps if row["identical"]),
        "passed": bool(traps) and all(row["identical"] for row in traps),
        "modes": by_mode,
    }


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return float((ordered[middle - 1] + ordered[middle]) / 2.0)


def summarise(rows: list[dict]) -> list[dict]:
    """One entry a mode, ordered by how far the axis moves it.

    The per-mode figure is the **median over the cells** and not the mean: the
    grid is nineteen modes over a handful of places and maps, and one deep place
    with almost no interior would otherwise carry a mode's whole column.

    `map_low` and `map_high` are the smallest and largest per-**map** median inside
    the mode, which is the spread the question asks to be shown rather than
    averaged away: a mode whose response depends on the map it is drawn with has a
    wide pair here, and a mode that responds the same way to every map has a tight
    one.
    """
    modes: dict[str, list[dict]] = {}
    for row in rows:
        modes.setdefault(row["mode"], []).append(row)
    out: list[dict] = []
    for mode, held in modes.items():
        by_map: dict[str, list[float]] = {}
        for row in held:
            by_map.setdefault(row["colormap"], []).append(float(row["mean"]))
        per_map = sorted(_median(values) for values in by_map.values())
        out.append(
            {
                "mode": mode,
                "mode_kind": held[0]["mode_kind"],
                "cells": len(held),
                "identical": sum(1 for row in held if row["identical"]),
                "mean": round(_median([float(row["mean"]) for row in held]), 6),
                "p95": round(_median([float(row["p95"]) for row in held]), 6),
                "p99": round(_median([float(row["p99"]) for row in held]), 6),
                "moved": round(_median([float(row["moved"]) for row in held]), 6),
                "black_share": round(_median([float(row["black_share"]) for row in held]), 6),
                "map_low": round(per_map[0], 6),
                "map_high": round(per_map[-1], 6),
                "map_ratio": round(per_map[-1] / per_map[0], 3) if per_map[0] > 0 else None,
            }
        )
    return sorted(out, key=lambda entry: entry["mean"])


#: How much larger than the next largest step a gap has to be before [`split`] will
#: call the **ranking** separated. **1.5**, and it is a statement about the *shape*
#: of an ordering rather than a bar on the axis: a ranking whose two largest steps
#: are the same size has no gap anywhere in it, and saying so is the honest answer.
#:
#: This decides **nothing about a mode**. It answers the narrower question of whether
#: the live modes can be *ordered* into a near group and a far one, and where it
#: cannot they are one group with their own numbers beside them.
SEPARATION = 1.5

#: The share of the frame that has to have moved past [`JND`] before a mode is
#: called live, beside its median mean clearing the same JND. **Half**, which is a
#: plain reading of *phase clearly moves the picture* and not a tuned cut: a mode
#: that recolours most of the frame perceptibly is not a mode a draw is wasted on.
#:
#: **Neither floor is here to force a split.** They are the scale [`difference`]
#: already reports on, and a mode landing near either is exactly what the
#: `uncertain` group is for — the answer *this does not separate from a no-op* is a
#: result and the thing a made-up threshold would hide.
MOVED_FLOOR = 0.5


def split(summary: list[dict]) -> dict:
    """The three groups, and then separately whether the live ones can be ordered.

    * **`flat`** — every cell byte-identical. A **fact about the pictures** and not a
      threshold at all, which is why it is read first and read on its own: on this
      axis it is the four direct traps, and `coloring::shade` is why.
    * **`live`** — not flat, and the mode's median mean clears [`JND`] with at least
      [`MOVED_FLOOR`] of the frame past it. *Phase clearly moves the picture*, read
      on the scale the rows are already reported on.
    * **`uncertain`** — neither. A mode that moves something, but not enough of the
      frame or not far enough to call it apart from a no-op.

    **The ordering is a second question and is answered separately.** `ordered` says
    whether the live group's ranked means hold a gap that stands out — the widest
    multiplicative step between neighbours being at least [`SEPARATION`] times the
    next widest — and `gap`/`runner_up` carry both steps whichever way it went. Where
    the ranking does not separate, `near`/`far` are absent and the live modes are one
    group: an honest *the spread does not separate them* is worth more than a cut
    invented to produce two.
    """
    flat = [entry for entry in summary if entry["cells"] and entry["identical"] == entry["cells"]]
    rest = [entry for entry in summary if entry not in flat]
    live = [entry for entry in rest if entry["mean"] >= JND and entry["moved"] >= MOVED_FLOOR]
    out = {
        "flat": [entry["mode"] for entry in flat],
        "live": [entry["mode"] for entry in live],
        "uncertain": [entry["mode"] for entry in rest if entry not in live],
        "gap": None,
        "runner_up": None,
        "ordered": False,
    }
    if len(live) < 3:
        return out
    steps = [
        (live[index + 1]["mean"] / live[index]["mean"] if live[index]["mean"] > 0 else 0.0, index)
        for index in range(len(live) - 1)
    ]
    steps.sort(reverse=True)
    (widest, cut), (runner, _next) = steps[0], steps[1]
    out["gap"] = round(widest, 3)
    out["runner_up"] = round(runner, 3)
    if widest >= SEPARATION * max(1e-9, runner):
        out["ordered"] = True
        out["near"] = [entry["mode"] for entry in live[: cut + 1]]
        out["far"] = [entry["mode"] for entry in live[cut + 1 :]]
        out["at"] = live[cut + 1]["mode"]
    return out


# --------------------------------------------------------------------------- #
# Writing it down.
# --------------------------------------------------------------------------- #
def write(name: str, rows: list[dict], report: dict) -> dict:
    """The rows and the record of one pass. `newline="\\n"`, like everything here."""
    directory = pass_dir(name)
    directory.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    rows_path(name).write_text(body, encoding="utf-8", newline="\n")
    record = {"schema": SCHEMA, "name": str(name), **report}
    record_path(name).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return record


def read(name: str) -> tuple[list[dict], dict]:
    """One pass's rows and record back off disk."""
    path = rows_path(name)
    if not path.is_file():
        raise PhaseResponseRefused(f"{path} is not there; {name!r} has not run")
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    record = json.loads(record_path(name).read_text(encoding="utf-8"))
    return rows, record


__all__ = [
    "BASE_PHASE",
    "DEFAULT_MAPS",
    "DEFAULT_PLACES",
    "DEFAULT_SEED",
    "DEFAULT_WORKERS",
    "JND",
    "MOVED_FLOOR",
    "PANEL_RUN",
    "PERCENTILES",
    "PHASES",
    "SCHEMA",
    "SEPARATION",
    "SHALLOW_SHARE",
    "UNIT",
    "PhaseResponseRefused",
    "baseline",
    "baseline_name",
    "black_share",
    "cells",
    "control",
    "difference",
    "digest",
    "maps",
    "pass_dir",
    "phase_row",
    "places",
    "population",
    "read",
    "read_pixels",
    "recipe_at",
    "record_path",
    "row_of",
    "rows_path",
    "run",
    "split",
    "store_root",
    "summarise",
    "write",
]
