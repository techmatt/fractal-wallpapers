"""Six pictures of one growth sweep. Matplotlib, scratch only, legibility only.

The durable product of [`curation.growth`] is `growth.jsonl` and its schema — the
website's `pipeline-growth` figure bakes its own drawing from that file, and this
module is not in that path. What this is for is the reading: six plots a person
looks at once, to see where the fill breaks and whether more mining is still
buying anything.

So it lands in `scratch/` and nowhere else, it styles nothing beyond what makes a
line readable, and it is allowed to be thrown away. **A number this draws that is
not in the jsonl is a bug**: every series here is a column, and the only
arithmetic is the mean and the min/max band across the three seeds of a rung.

## One line per rung, labelled by effort

The legend is millions of **attempts**, not the fraction: a reader asking "what
does more mining buy" is asking about candidates rendered, and `1/16` means
nothing without the denominator. The fraction stays in the label beside it because
the attempt count is approximate ([`growth.visits`]) and the fraction is not.

`matplotlib` is not in the base install and is not in any of this project's
extras either. It is imported inside [`draw`] rather than at the top, so importing
this module — reading [`PANELS`], asking what a series means — costs a checkout
that has never installed it nothing at all.
"""

from __future__ import annotations

from pathlib import Path

from fractal_wallpapers.curation import growth

#: The six panels, each `(file stem, title, how to read one row)`. Adding a
#: seventh is a line here and a reader function, and nothing else.
PANELS = (
    ("fill", "seats filled vs n", "fill"),
    ("median", "seated median (fitted rank) vs n", "median"),
    ("p10", "seated 10th percentile (fitted rank) vs n", "p10"),
    ("lift", "selection lift: seated median - eligible median", "lift"),
    ("floors", "mode floors met vs n", "floors"),
    ("spread", "colour-cell spread (top cell / bottom cell) vs n", "spread"),
)


class PlotRefused(RuntimeError):
    """The run cannot be drawn."""


def _fill(row):
    return None if row["fill"] is None else 100.0 * row["fill"]


def _median(row):
    held = row["seated_rank"]
    return None if held is None else held["p50"]


def _p10(row):
    held = row["seated_rank"]
    return None if held is None else held["p10"]


def _lift(row):
    return row["selection_lift"]


def _floors(row):
    return row["floors_met"]


def _spread(row):
    return row["cell_spread"]["ratio"]


#: `{how to read one row: (the reader, what the y axis is)}`.
READERS = {
    "fill": (_fill, "seats filled (%)"),
    "median": (_median, "rank value"),
    "p10": (_p10, "rank value"),
    "lift": (_lift, "rank value"),
    "floors": (_floors, "floors met"),
    "spread": (_spread, "top cell / bottom cell"),
}


def series(rows, reading: str) -> dict:
    """`{rung: {n: (mean, low, high)}}` over the seeds of each rung.

    A cell whose value is `None` — a rung that seated nothing, so it has no
    median — is **dropped** rather than plotted at zero. A line that stops is the
    honest picture of a rung that ran out of pool.
    """
    read, _label = READERS[str(reading)]
    gathered: dict = {}
    for row in rows:
        value = read(row)
        if value is None:
            continue
        gathered.setdefault(str(row["rung"]), {}).setdefault(int(row["n"]), []).append(float(value))
    return {
        rung: {
            size: (sum(values) / len(values), min(values), max(values))
            for size, values in sorted(held.items())
        }
        for rung, held in gathered.items()
    }


def legend_of(rows) -> dict:
    """`{rung: its label}` — the fraction, and the attempts it stands for.

    Attempts are averaged over the rung's seeds and over its sizes, which are the
    same subsample repeated, so the average is exact and the spread across seeds
    is the only thing it hides.
    """
    per: dict = {}
    for row in rows:
        per.setdefault(str(row["rung"]), []).append(int(row["attempts"]))
    return {
        rung: f"{rung} ({sum(held) / len(held) / 1e6:.3f}M attempts)" for rung, held in per.items()
    }


def order_of(rows) -> list:
    """The rungs, smallest fraction first, so the legend reads bottom-up."""
    return [rung for _fraction, rung in sorted({(row["fraction"], row["rung"]) for row in rows})]


def draw(rows, directory: Path, log=print) -> list:
    """Draw all six panels into `directory`. Returns what was written."""
    try:
        import matplotlib
    except ModuleNotFoundError as missing:
        raise PlotRefused(
            "matplotlib is not installed, and it is not in this project's dependency set "
            "either — the durable product of a growth sweep is growth.jsonl, and this "
            "module only draws it. `uv pip install matplotlib` in the checkout's venv, "
            "then run this again"
        ) from missing

    matplotlib.use("Agg")
    import matplotlib.pyplot as pyplot

    directory.mkdir(parents=True, exist_ok=True)
    labels = legend_of(rows)
    rungs = order_of(rows)
    written = []
    for stem, title, reading in PANELS:
        _read, axis = READERS[reading]
        held = series(rows, reading)
        figure, plot = pyplot.subplots(figsize=(7.5, 4.8))
        for rung in rungs:
            points = held.get(rung)
            if not points:
                continue
            sizes = sorted(points)
            middle = [points[size][0] for size in sizes]
            low = [points[size][1] for size in sizes]
            high = [points[size][2] for size in sizes]
            (line,) = plot.plot(sizes, middle, marker="o", label=labels[rung])
            if any(a != b for a, b in zip(low, high, strict=True)):
                plot.fill_between(sizes, low, high, alpha=0.18, color=line.get_color())
        plot.set_title(title)
        plot.set_xlabel("gallery size n")
        plot.set_ylabel(axis)
        plot.grid(True, alpha=0.3)
        plot.legend(fontsize="small")
        figure.tight_layout()
        where = directory / f"{stem}.png"
        figure.savefig(where, dpi=140)
        pyplot.close(figure)
        written.append(where)
        log(f"[growth-plot] {where}")
    return written


def scratch_dir(stamp: str) -> Path:
    """Where one run's plots land. `scratch/`, which this project calls disposable."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "scratch" / f"growth_{stamp}"


def plot(stamp: str, directory: Path | None = None, log=print) -> Path:
    """Read one stamped run and draw it. The whole entry point."""
    rows, _manifest = growth.read_run(stamp)
    if not rows:
        raise PlotRefused(f"the run {stamp!r} holds no rows")
    where = scratch_dir(stamp) if directory is None else Path(directory)
    draw(rows, where, log=log)
    return where


__all__ = [
    "PANELS",
    "READERS",
    "PlotRefused",
    "draw",
    "legend_of",
    "order_of",
    "plot",
    "scratch_dir",
    "series",
]
