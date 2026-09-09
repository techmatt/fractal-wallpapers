"""Two pictures of one colour-ceiling sweep. Matplotlib, scratch only, legibility only.

The durable product of [`curation.k_sweep`] is `readings.json` and the records
beside it; this module only draws what is already in that file. **A number this
draws that is not in the readings is a bug**: every bar here is a `cells.counts`
entry and the only arithmetic is a subtraction against the control rung.

## Why a picture at all, when the tables are already written

Because the question the sweep is run to answer is *does any colour collapse as
the ceiling stops binding*, and a collapse is a **shape** across 48 cells rather
than a number in a table. The ckpt-111 sweep found eight of nine short cells
ending shorter in absolute seats at a looser `K`; that is invisible in a column
of counts sorted by size and unmistakable as a bar below zero.

## The two figures answer the two halves

[`SPREAD`] is per-cell membership at every rung with the control **beside** each
arm, split into two panels of 24 so a bar is wide enough to read, each arm's
allowance drawn as a dashed line in its own colour so a pinned cell is visible
as one touching its line. [`DELTA`] is the same data as a difference against the
control, ordered by the widest arm's fall, which is the figure a floor would be
argued off.

Cells are ordered by the **control's** count at both, descending, so a cell sits
in the same place in both figures and the eye can carry between them.

`matplotlib` is not in the base install and is not in any of this project's
extras either. It is imported inside [`draw`] rather than at the top, for
[`curation.growth_plot`]'s reason: importing this module must cost a checkout
that has never installed it nothing at all.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.curation import k_sweep

#: The per-cell figure: every rung's membership, the control beside each arm.
SPREAD = "cells"

#: The difference figure: each arm's membership minus the control's.
DELTA = "cells_delta"

#: How many cells go in one panel of [`SPREAD`]. 48 in one row leaves a bar four
#: pixels wide at six rungs; two panels of this is the widest split that still
#: fits one screen.
PER_PANEL = 24


class PlotRefused(RuntimeError):
    """The sweep cannot be drawn."""


def read(stamp: str) -> dict:
    """One sweep's readings, by stamp. [`k_sweep.readings_named`] finds the file."""
    try:
        path = k_sweep.readings_named(str(stamp))
    except FileNotFoundError as missing:
        raise PlotRefused(str(missing)) from missing
    return json.loads(path.read_text(encoding="utf-8"))


def cells_of(held: dict) -> list:
    """Every cell any rung seated, ordered by the **control** rung, descending.

    Ordered on the control and not on the union's totals so that the two figures
    share an axis and a reader can carry a cell's position between them. A cell
    the control never seated sorts last, by name — it exists in the union because
    some looser rung found it, which is itself worth seeing.
    """
    control = held["rungs"][0]["cells"]["counts"]
    union: set = set()
    for rung in held["rungs"]:
        union |= set(rung["cells"]["counts"])
    return sorted(union, key=lambda cell: (-control.get(cell, 0), cell))


def series(held: dict, cells) -> list:
    """`[(label, allowance, [seats per cell])]`, one row per rung, in sweep order."""
    out = []
    for rung in held["rungs"]:
        counts = rung["cells"]["counts"]
        out.append(
            (
                f"K={float(rung['k']):g} (allowance {rung['allowance']})",
                int(rung["allowance"]),
                [counts.get(cell, 0) for cell in cells],
            )
        )
    return out


def _colours(count: int):
    """One colour per rung: the control grey, the arms up a sequential ramp.

    Grey for the control because it is the baseline and not a rung of the ramp —
    it appears beside every arm, and a reader has to be able to find it without
    counting bars.
    """
    from matplotlib import colormaps

    ramp = colormaps["viridis"]
    arms = max(1, count - 1)
    return ["#8a8a8a"] + [ramp(0.12 + 0.78 * at / max(1, arms - 1)) for at in range(arms)]


def _spread(held: dict, cells, rows, directory: Path, log) -> Path:
    """The control beside every arm, split into panels of [`PER_PANEL`] cells."""
    import matplotlib.pyplot as pyplot

    panels = [cells[at : at + PER_PANEL] for at in range(0, len(cells), PER_PANEL)]
    colours = _colours(len(rows))
    width = 1.0 / (len(rows) + 0.6)
    figure, axes = pyplot.subplots(len(panels), 1, figsize=(16.0, 4.6 * len(panels)))
    axes = [axes] if len(panels) == 1 else list(axes)
    for panel, plot in zip(panels, axes, strict=True):
        first = cells.index(panel[0])
        spots = range(len(panel))
        for at, (label, allowed, counts) in enumerate(rows):
            plot.bar(
                [spot + at * width for spot in spots],
                counts[first : first + len(panel)],
                width=width,
                color=colours[at],
                label=label if first == 0 else None,
            )
            plot.axhline(allowed, color=colours[at], linestyle="--", linewidth=0.8, alpha=0.55)
        plot.set_xticks([spot + width * (len(rows) - 1) / 2 for spot in spots])
        plot.set_xticklabels(panel, rotation=90, fontsize=7)
        plot.set_ylabel("seats dominant in the cell")
        plot.grid(True, axis="y", alpha=0.25)
        # A short last panel would otherwise stretch its bars across the full
        # width and read as a different scale from the panel above it.
        plot.set_xlim(-0.5, PER_PANEL - 0.5 + width * len(rows))
    axes[0].set_title(
        "colour-cell membership per rung, the control beside each arm "
        "(dashed: that rung's allowance)"
    )
    axes[0].legend(fontsize="small", ncol=3)
    figure.tight_layout()
    where = directory / f"{SPREAD}.png"
    figure.savefig(where, dpi=140)
    pyplot.close(figure)
    log(f"[k-sweep-plot] {where}")
    return where


def _delta(held: dict, cells, rows, directory: Path, log) -> Path:
    """Each arm's membership minus the control's, ordered by the widest arm's fall."""
    import matplotlib.pyplot as pyplot

    base = rows[0][2]
    arms = rows[1:]
    if not arms:
        raise PlotRefused("a sweep of one rung has nothing to difference against")
    widest = arms[-1][2]
    order = sorted(range(len(cells)), key=lambda at: (widest[at] - base[at], cells[at]))
    colours = _colours(len(rows))[1:]
    width = 1.0 / (len(arms) + 0.6)
    figure, plot = pyplot.subplots(figsize=(16.0, 5.4))
    spots = range(len(order))
    for at, (label, _allowed, counts) in enumerate(arms):
        plot.bar(
            [spot + at * width for spot in spots],
            [counts[where] - base[where] for where in order],
            width=width,
            color=colours[at],
            label=label,
        )
    plot.axhline(0.0, color="black", linewidth=0.9)
    plot.set_xticks([spot + width * (len(arms) - 1) / 2 for spot in spots])
    plot.set_xticklabels([cells[where] for where in order], rotation=90, fontsize=7)
    plot.set_ylabel("seats gained or lost against K=2")
    plot.set_title("what each arm does to every colour cell, against the K=2 control")
    plot.grid(True, axis="y", alpha=0.25)
    plot.margins(y=0.12)
    plot.legend(fontsize="small", ncol=3, loc="upper left")
    figure.tight_layout()
    where = directory / f"{DELTA}.png"
    figure.savefig(where, dpi=140)
    pyplot.close(figure)
    log(f"[k-sweep-plot] {where}")
    return where


def draw(held: dict, directory: Path, log=print) -> list:
    """Draw both figures into `directory`. Returns what was written."""
    try:
        import matplotlib
    except ModuleNotFoundError as missing:
        raise PlotRefused(
            "matplotlib is not installed, and it is not in this project's dependency set "
            "either — the durable product of a K sweep is its readings.json and the "
            "records beside it, and this module only draws them. `uv pip install "
            "matplotlib` in the checkout's venv, then run this again"
        ) from missing

    matplotlib.use("Agg")
    if not held.get("rungs"):
        raise PlotRefused("the sweep holds no rungs")
    directory.mkdir(parents=True, exist_ok=True)
    cells = cells_of(held)
    rows = series(held, cells)
    return [
        _spread(held, cells, rows, directory, log),
        _delta(held, cells, rows, directory, log),
    ]


def table(held: dict) -> str:
    """The figures' own numbers as text, so a report never quotes a bar it read off.

    One row per cell in [`cells_of`] order, one column per rung, and the control's
    difference in the last column — which is the [`DELTA`] figure written out.
    """
    cells = cells_of(held)
    rows = series(held, cells)
    head = ["cell"] + [f"K={float(rung['k']):g}" for rung in held["rungs"]] + ["last-first"]
    lines = ["\t".join(head), "\t".join(["allowance"] + [str(row[1]) for row in rows] + [""])]
    for at, cell in enumerate(cells):
        counts = [row[2][at] for row in rows]
        moved = f"{counts[-1] - counts[0]:+d}"
        lines.append("\t".join([cell] + [str(one) for one in counts] + [moved]))
    return "\n".join(lines) + "\n"


def scratch_dir(stamp: str) -> Path:
    """Where one sweep's figures land. `scratch/`, which this project calls disposable."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "scratch" / f"k_sweep_{stamp}"


def plot(stamp: str, directory: Path | None = None, log=print) -> Path:
    """Read one stamped sweep and draw it. The whole entry point."""
    held = read(stamp)
    where = scratch_dir(stamp) if directory is None else Path(directory)
    draw(held, where, log=log)
    (where / "cells.tsv").write_text(table(held), encoding="utf-8", newline="\n")
    return where


__all__ = [
    "DELTA",
    "PER_PANEL",
    "SPREAD",
    "PlotRefused",
    "cells_of",
    "draw",
    "plot",
    "read",
    "scratch_dir",
    "series",
    "table",
]
