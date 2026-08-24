"""The glance sheet: one batch's rows under two heads' orderings, side by side.

A non-inferiority band answers whether a retrain costs anything on the blind
sheets. It cannot answer the question a correction batch was actually bought to
answer, and on this project's rules it never will: the manufactured rows are
anchored, incumbent-screened and train-side forever, so every read of them is a
read of a population that was enriched twice to produce them. Quoting a number off
that would be quoting a ceiling as a rate.

So the read is a person's. This module lays the same rows out twice — once in the
order the incumbent puts them in, once in the candidate's — and prints the pair of
scores under each picture. What a reader is looking for is whether the pictures the
correction batch was cut for have moved up, and whether anything they would not
have promoted came up with them.

**It decides nothing and writes nothing into any record.** One HTML file into
`scratch/`, which is disposable, carrying its own pictures.

## Which picture, and why the crop rather than the sheet render

`artifacts/renders/<kind>/crops/<name>.jpg` — the picture both heads were trained
on and both read natively. The sheet render a person labelled is a different
geometry, and asking two heads to order rows at a geometry neither was read at
would add a difference that has nothing to do with either of them.
"""

from __future__ import annotations

import html
from pathlib import Path

from fractal_wallpapers.labeling import finished
from fractal_wallpapers.models import render_train, renders, ship, train

#: The long edge of a thumbnail here. Two columns of small cards, so narrower than
#: the single-column below-bar sheet.
THUMBNAIL_WIDTH = 320

#: How many rows each column holds unless a caller says otherwise.
ROWS = 12

#: Where the sheet lands unless a caller says otherwise.
DEFAULT_SHEET = Path("scratch") / "correction_batch_glance.html"

#: The column both orderings are read on. `P(>=3)` is the boundary a release floor
#: is a point on and the one the acting cut is taken at, so it is the ordering a
#: promotion would actually happen under.
COLUMN = "p_ge3"

#: `p_ge2` is column 0, so `P(>=3)` is column 1. Spelled out because the offset
#: between a cutpoint and its column reads right and is wrong by one.
COLUMN_INDEX = 1


class GlanceError(RuntimeError):
    """The sheet cannot be drawn, and drawing a partial one would mislead."""


def rows_of(batch: str) -> dict[str, list[dict]]:
    """`{kind: rows}` for every stored row whose batch starts with `batch`.

    A prefix rather than an exact name because a manufactured batch travels with
    its own contrast arm under a suffixed registration, and the two are one
    population to look at.
    """
    out: dict[str, list[dict]] = {}
    for kind in render_train.KINDS:
        mine = [row for row in finished.resolved(kind).scored() if row["batch"].startswith(batch)]
        if mine:
            out[kind] = mine
    if not out:
        raise GlanceError(f"no stored row of either kind is in a batch named {batch!r}")
    return out


def _pictures(kind: str, rows: list[dict]) -> list[Path]:
    crops = renders.crop_dir(kind)
    paths = [crops / f"{renders.job_name({**row, '_head': kind})}.jpg" for row in rows]
    absent = [path.name for path in paths if not path.is_file()]
    if absent:
        raise GlanceError(
            f"{len(absent)} picture(s) of the {kind} rows are not in the render cache "
            f"(e.g. {absent[:3]}). `renders build --head {kind}` first."
        )
    return paths


def _read(model, config, where, paths: list[Path]) -> list[float]:
    """`P(>=3)` for every picture, in the order given."""
    from fractal_wallpapers.models import scoring

    classes = int(config["classes"])
    probabilities = train.score(model, paths, scoring.transform_of(config), where, classes, config)
    return [float(row[COLUMN_INDEX]) for row in probabilities]


def scored(batch: str, run: str, which: str = "best", device: str = "auto") -> dict:
    """Every row of `batch`, with the incumbent's score and the candidate's."""
    incumbent = render_train.load_checkpoint(ship.shipped_path(render_train.HEAD), device)
    candidate = render_train.load(which, run, device)
    out = {}
    for kind, rows in rows_of(batch).items():
        paths = _pictures(kind, rows)
        theirs = _read(*incumbent, paths)
        ours = _read(*candidate, paths)
        cells = [
            {
                "kind": kind,
                "batch": row["batch"],
                "score": int(row["score"]),
                "mode": row["mode"],
                "colormap": row["colormap"],
                "picture": path,
                "incumbent": mine,
                "candidate": yours,
            }
            for row, path, mine, yours in zip(rows, paths, theirs, ours, strict=True)
        ]
        by_incumbent = sorted(cells, key=lambda cell: -cell["incumbent"])
        by_candidate = sorted(cells, key=lambda cell: -cell["candidate"])
        place_of = {id(cell): place for place, cell in enumerate(by_incumbent)}
        for place, cell in enumerate(by_candidate):
            cell["moved"] = place_of[id(cell)] - place
        out[kind] = {"cells": cells, "by_incumbent": by_incumbent, "by_candidate": by_candidate}
    return out


# --------------------------------------------------------------------------- #
# The page.
# --------------------------------------------------------------------------- #
def _card(cell: dict, place: int, show_move: bool = False) -> str:
    from fractal_wallpapers.curation import sheet

    source = sheet.thumbnail(cell["picture"], width=THUMBNAIL_WIDTH)
    image = f'<img src="{source}" alt="">' if source else '<div class="missing">no picture</div>'
    move = ""
    if show_move:
        way = "up" if cell["moved"] > 0 else ("down" if cell["moved"] < 0 else "level")
        move = f'<span class="moved {way}">{cell["moved"]:+d}</span>'
    arm = " - contrast arm" if cell["batch"].endswith("_contrast") else ""
    return (
        f'<figure><div class="n">{place}{move}</div>{image}'
        f"<figcaption><b>human {cell['score']}</b>{html.escape(arm)}<br>"
        f"{html.escape(cell['mode'])} - {html.escape(cell['colormap'])}<br>"
        f'<span class="s">candidate {cell["candidate"]:.4f} - '
        f"incumbent {cell['incumbent']:.4f}</span></figcaption></figure>"
    )


def _column(title: str, cells: list[dict], show_move: bool = False) -> str:
    body = "".join(_card(cell, place + 1, show_move) for place, cell in enumerate(cells))
    return f'<div class="col"><h3>{html.escape(title)}</h3>{body}</div>'


STYLE = """
:root { color-scheme: light dark; }
body { font: 14px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 1100px;
       padding: 0 1rem; }
h1 { font-size: 1.4rem; margin-bottom: .2rem; }
h2 { font-size: 1.05rem; margin-top: 2.4rem; border-top: 1px solid #8884; padding-top: 1rem; }
h3 { font-size: .95rem; font-weight: 600; margin: 0 0 .6rem; }
.lede, .provenance { opacity: .75; }
.provenance { padding-left: 1.1rem; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1.6rem; }
.col figure { margin: 0 0 1.1rem; }
.col img { width: 100%; border-radius: 3px; display: block; }
.missing { padding: 2rem; text-align: center; opacity: .5; border: 1px dashed #8886; }
.n { font-variant-numeric: tabular-nums; opacity: .6; font-size: .85rem; }
figcaption { font-size: .8rem; margin-top: .3rem; }
.s { font-variant-numeric: tabular-nums; opacity: .75; }
.moved { margin-left: .5rem; font-weight: 600; }
.moved.up { color: #2e9e4f; }
.moved.down { color: #c0392b; }
.moved.level { opacity: .5; }
"""


def page(read: dict, lines: list[str]) -> str:
    """The whole sheet, self-contained and carrying its own pictures."""
    facts = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
    blocks = []
    for kind in sorted(read):
        columns = read[kind]
        top = columns["rows"]
        blocks.append(
            f"<h2>{html.escape(kind)} - the top {top} either head would put first</h2>"
            f'<div class="pair">'
            f"{_column('under the CANDIDATE', columns['by_candidate'][:top], True)}"
            f"{_column('under the INCUMBENT', columns['by_incumbent'][:top])}"
            f"</div>"
            f"<h2>{html.escape(kind)} - the {top} rows that moved furthest</h2>"
            f'<div class="pair">'
            f"{_column('promoted by the candidate', columns['risers'], True)}"
            f"{_column('demoted by the candidate', columns['fallers'], True)}"
            f"</div>"
        )
    return (
        '<!doctype html><meta charset="utf-8">'
        f"<title>The correction batch under two heads</title><style>{STYLE}</style>"
        "<h1>The correction batch, ordered by the candidate and by the incumbent</h1>"
        '<p class="lede">A qualitative read and nothing else. These rows are anchored, '
        "incumbent-screened and train-side, so no rate quoted off them is a rate - the "
        "question is only whether the pictures look right in the order the candidate puts "
        "them in.</p>"
        f'<ul class="provenance">{facts}</ul>' + "".join(blocks)
    )


def write(
    batch: str,
    run: str,
    path: Path | None = None,
    rows: int = ROWS,
    which: str = "best",
    device: str = "auto",
) -> dict:
    """Draw the sheet and report what went on it. Writes one file and nothing else."""
    read = scored(batch, run, which, device)
    for columns in read.values():
        by_move = sorted(columns["by_candidate"], key=lambda cell: -cell["moved"])
        columns["rows"] = min(rows, len(columns["cells"]))
        columns["risers"] = by_move[: columns["rows"]]
        columns["fallers"] = list(reversed(by_move[-columns["rows"] :]))
    lines = [
        f"batch {batch}: {sum(len(c['cells']) for c in read.values())} stored rows across "
        f"{len(read)} kind(s)",
        f"ordered on {COLUMN} - the boundary a release floor is a point on",
        f"candidate {run} ({which}) against the shipped {render_train.HEAD} artifact",
        "pictures are the render cache's crops, the geometry both heads read natively",
    ]
    path = Path(path or DEFAULT_SHEET)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page(read, lines), encoding="utf-8", newline="\n")
    return {
        "path": str(path),
        "batch": batch,
        "run": run,
        "per_kind": {kind: len(columns["cells"]) for kind, columns in read.items()},
        "rows_per_column": {kind: columns["rows"] for kind, columns in read.items()},
    }


__all__ = [
    "COLUMN",
    "COLUMN_INDEX",
    "DEFAULT_SHEET",
    "ROWS",
    "STYLE",
    "GlanceError",
    "page",
    "rows_of",
    "scored",
    "write",
]
