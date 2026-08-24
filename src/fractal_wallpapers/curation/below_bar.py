"""The glance sheet: every served wallpaper that today's acting bar would take back.

[`rejection.below_acting_bar`] is a rule read live against the live cut, so the
set it names moves whenever a head is re-shipped or a height is restated — and
what it hands back is keys and floats. A person cannot rule on keys and floats.
Whether a picture is a wallpaper is the one judgement this project never gives to
a head, so the rows have to be laid out **as pictures**, in score order, with the
number that condemns each one under it.

That is all this module is: one page, one row per condemned wallpaper, best score
first. It decides nothing, writes nothing into the record store, and re-renders
nothing — the picture on the page is the release PNG the row already serves.

## The page names exactly the rows the rejection pass would take

Not "rows near the bar", and not a re-derived comparison. The population comes
from [`rejection.below_acting_bar`] itself, so a page showing a row `curate
reject` would leave alone — or leaving one out — is a bug in one function rather
than a disagreement between two. The floor beside each score is that row's own
[`floors.release_bar`], read through the same call: floors are per KIND, and one
judge emitting both scales is exactly why the page prints the floor on every row
instead of once in the title.

## A ruled row is on the page, and it is not in the count

`data/curation/bar_exceptions.jsonl` holds rows a person ruled stay in service
below a bar, and [`rejection.below_acting_bar`] passes over them — correctly,
because the population here is *what a rejection pass would act on*. But a
reviewer reading twenty condemned rows would take the page for the whole
below-bar population, and it is not: others sit below the same bar and have
already been ruled on. So the rulings get their own section off the same store,
each carrying who ruled it and when.

## An exclusion is a person's instruction, and the page says so

A row can be dropped from the sheet by key — a row seated on a scale that has
since been retired is evidence about nothing current, and looking at it costs the
reviewer a judgement they do not have to make. That is a call rather than a rule,
so it arrives as keys and a reason and both are printed on the page. A sheet
silently holding twenty of twenty-one rows would be a sheet nobody could check
against the store. An exclusion naming a row that is not below the bar refuses,
for the same reason: it is a key that has moved, and the sheet would come out a
row short with no line saying so.
"""

from __future__ import annotations

import html
from pathlib import Path

from fractal_wallpapers.curation import records, rejection, sheet
from fractal_wallpapers.curation import run as run_module

#: The long edge of a thumbnail here. Wider than the release sheet's, because
#: that page is a contact grid of many small cards and this one is a single
#: column of rows somebody is deciding to keep or drop.
THUMBNAIL_WIDTH = 560

#: Where the sheet lands unless a caller says otherwise. `scratch/` because the
#: page carries its own pictures — a few hundred kilobytes of embedded JPEG the
#: tracked tree would refuse anyway — and because it is a review artifact rather
#: than a record.
DEFAULT_SHEET = Path("scratch") / "below_bar_glance.html"


def _cell(row: dict, floor: float, ruling: dict | None = None) -> dict:
    """One row of the page: the picture, the key, the kind, the score and the gap."""
    score = float(records.live_reading(row)["p_ge3"])
    picture = row.get("picture")
    return {
        "key": str(row.get("key")),
        "run": str(row.get("run")),
        "candidate": str(row.get("candidate")),
        "collection": row.get("collection"),
        "kind": records.kind_of(row),
        "score": score,
        "floor": float(floor),
        "below_by": float(floor) - score,
        "picture": (run_module.run_dir(str(row.get("run"))) / str(picture)) if picture else None,
        "ruling": ruling,
    }


def _by_score(cells: list[dict]) -> list[dict]:
    """Good to bad, ties broken by key so two draws of one population are one page."""
    return sorted(cells, key=lambda cell: (-cell["score"], cell["key"]))


def condemned(rows: list[dict], exclude=()) -> list[dict]:
    """Every served row an acting bar would take back today, best score first.

    The population is [`rejection.below_acting_bar`]'s and no other, minus the
    keys the reviewer excluded. Rows a ruling holds in service are not here —
    that function passes over them — and they come back from [`ruled`].
    """
    dropped = {str(key) for key in exclude}
    return _by_score(
        [
            _cell(row, bar.value)
            for row, bar in rejection.below_acting_bar(rows)
            if str(row.get("key")) not in dropped
        ]
    )


def ruled(rows: list[dict]) -> list[dict]:
    """The served rows a tracked ruling holds in service below the same bar.

    Off the two stores that already answer it — [`records.served`] and
    [`rejection.exceptions`] — rather than recomputed, so a row on this section is
    a row the rejection pass is really excusing rather than one this page believes
    it ought to be.
    """
    from fractal_wallpapers.curation import floors

    excused = rejection.exceptions()
    out = []
    for row in records.served(rows):
        ruling = excused.get(str(row.get("key")))
        if ruling is None:
            continue
        bar = floors.release_bar(records.kind_of(row) or "")
        if bar is None:
            continue
        out.append(_cell(row, bar.value, ruling=ruling))
    return _by_score(out)


def _score_line(cell: dict) -> str:
    """The one number a reader is here for, and its distance from the one it fails."""
    return (
        f"P(>=3) {cell['score']:.4f} against {cell['floor']:g} — "
        f"{cell['below_by']:.4f} below the {cell['kind']} floor"
    )


def _meter(cell: dict) -> str:
    """The same gap as a length, so twenty of them rank at a glance."""
    filled = max(0.0, min(1.0, cell["score"])) * 100
    mark = max(0.0, min(1.0, cell["floor"])) * 100
    return (
        f'<div class="meter"><div class="fill" style="width:{filled:.1f}%"></div>'
        f'<div class="mark" style="left:{mark:.1f}%"></div></div>'
    )


def _row(cell: dict, index: int) -> str:
    source = sheet.thumbnail(cell["picture"], width=THUMBNAIL_WIDTH) if cell["picture"] else ""
    image = (
        f'<img src="{source}" alt="">'
        if source
        else '<div class="missing">no picture on disk</div>'
    )
    ruling = cell.get("ruling") or {}
    note = (
        '<p class="ruling">held in service by '
        f"{html.escape(str(ruling.get('ruled_by')))} on "
        f"{html.escape(str(ruling.get('date')))}: "
        f"{html.escape(str(ruling.get('reason')))}</p>"
        if ruling
        else ""
    )
    return (
        f'<tr><td class="n">{index}</td>'
        f'<td class="pic"><div class="frame">{image}</div></td>'
        f'<td class="facts"><b>{html.escape(cell["key"])}</b>'
        f'<p class="kind">{html.escape(cell["kind"])} · '
        f"{html.escape(str(cell['collection']))}</p>"
        f'<p class="score">{html.escape(_score_line(cell))}</p>'
        f"{_meter(cell)}{note}</td></tr>"
    )


def _table(cells: list[dict]) -> str:
    body = "".join(_row(cell, offset + 1) for offset, cell in enumerate(cells))
    return f'<table class="rows">{body}</table>'


STYLE = """
:root { color-scheme: light dark; }
body { font: 14px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 980px;
       padding: 0 1rem; }
h1 { font-size: 1.4rem; margin-bottom: .25rem; }
h2 { font-size: 1.1rem; margin-top: 2.5rem; border-top: 1px solid #8886; padding-top: 1rem; }
.lede { opacity: .8; margin-top: 0; }
.provenance { font-size: 12.5px; opacity: .85; padding-left: 1.1rem; }
.provenance li { margin: .25rem 0; overflow-wrap: anywhere; }
table.rows { border-collapse: collapse; width: 100%; }
table.rows td { border-top: 1px solid #8883; padding: 1rem .6rem; vertical-align: top; }
td.n { font: 12px ui-monospace, monospace; opacity: .5; width: 2rem; }
td.pic { width: 560px; }
.frame { background: #0003; border-radius: 4px; overflow: hidden; }
img { display: block; width: 100%; height: auto; }
.missing { padding: 4rem 1rem; text-align: center; opacity: .6; }
td.facts b { font-family: ui-monospace, monospace; font-size: 13px; overflow-wrap: anywhere; }
td.facts p { margin: .35rem 0 0; }
.kind { font-size: 12px; opacity: .7; }
.score { font-size: 13px; }
.ruling { font-size: 12px; opacity: .8; }
.meter { position: relative; height: 6px; margin: .6rem 0 0;
         border-radius: 3px; background: #8883; }
.meter .fill { position: absolute; inset: 0 auto 0 0; border-radius: 3px; background: #8889; }
.meter .mark { position: absolute; top: -4px; bottom: -4px; width: 2px; background: currentColor; }
"""


def provenance(cells: list[dict], rulings: list[dict], excluded, reason: str) -> list[str]:
    """The lines that let a reader check this page against the store it came from."""
    from fractal_wallpapers.curation import floors

    lines = [
        "population: every row records.served still serves whose KIND has an ACTING release "
        "bar it does not clear — the same rule curate reject applies, read live",
        f"the bar: {floors.STRANGE_RELEASE_BAR}",
    ]
    for kind in sorted({cell["kind"] for cell in cells}):
        shown = [cell for cell in cells if cell["kind"] == kind]
        lines.append(
            f"{kind}: {len(shown)} row(s) against a floor of {shown[0]['floor']:g}, "
            f"{min(cell['score'] for cell in shown):.4f} to "
            f"{max(cell['score'] for cell in shown):.4f}"
        )
    if excluded:
        lines.append(
            f"{len(excluded)} row(s) excluded by the reviewer: "
            + ", ".join(sorted(excluded))
            + (f" — {reason}" if reason else "")
        )
    lines.append(
        f"{len(rulings)} row(s) below the same bar carry a ruling in "
        f"data/curation/{rejection.EXCEPTIONS_NAME} and are not counted above"
        if rulings
        else f"no row below the bar carries a ruling in data/curation/{rejection.EXCEPTIONS_NAME}"
    )
    lines.append("nothing is rejected, re-rendered or written to the record store by this page")
    return lines


def page(cells: list[dict], rulings: list[dict], lines: list[str]) -> str:
    """The whole sheet, as one self-contained document that carries its own pictures."""
    facts = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
    held = (
        f"<h2>{len(rulings)} more below the same bar, held in service by a ruling</h2>"
        f"{_table(rulings)}"
        if rulings
        else ""
    )
    return (
        '<!doctype html><meta charset="utf-8">'
        f"<title>Below the acting bar</title><style>{STYLE}</style>"
        f"<h1>{len(cells)} served wallpaper(s) below the acting bar</h1>"
        '<p class="lede">Best score first. Nothing here is rejected or changed by this page — '
        "it is the read to rule off.</p>"
        f'<ul class="provenance">{facts}</ul>'
        f"{_table(cells)}{held}"
    )


def write(path: Path | None = None, exclude=(), reason: str = "") -> dict:
    """Draw the sheet and report what went on it. Writes one file and nothing else."""
    rows = records.read_decisions(records.RELEASE)
    dropped = {str(key) for key in exclude}
    below = {str(row.get("key")) for row, _ in rejection.below_acting_bar(rows)}
    missing = sorted(dropped - below)
    if missing:
        raise ValueError(
            "asked to exclude " + ", ".join(missing) + " but no such row is below an acting "
            "bar today. An exclusion that names nothing is a key that has moved, and "
            "dropping it silently would leave the sheet a row short with no line saying so."
        )
    cells = condemned(rows, exclude=dropped)
    rulings = ruled(rows)
    out = Path(path) if path is not None else DEFAULT_SHEET
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page(cells, rulings, provenance(cells, rulings, dropped, reason)),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "sheet": str(out),
        "below_bar": len(below),
        "shown": len(cells),
        "excluded": sorted(dropped),
        "exclude_reason": reason,
        "held_by_ruling": [cell["key"] for cell in rulings],
        "no_picture_on_disk": [
            cell["key"] for cell in cells if not (cell["picture"] and cell["picture"].is_file())
        ],
        "rows": [
            {name: value for name, value in cell.items() if name not in ("picture", "ruling")}
            for cell in cells
        ],
    }


__all__ = ["DEFAULT_SHEET", "condemned", "page", "provenance", "ruled", "write"]
