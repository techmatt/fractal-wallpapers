"""One self-contained HTML page: a grid of pictures with numbers beside them.

The reader doors — `judges score`, `judges check`, `harvest stats`, `curate
candidate-ledger browse` — each write plain files plus one of these, so a person
who has just run a step can open one file and see that the result is sane. The bar
is deliberately low: no server, no script, no framework, nothing fetched. A picture
is referred to by a path relative to the page, so the page works from the file
system and moves only with the pictures it points at.

A page is a title, a few lines of prose, optional tables, and sections of tiles.
A tile is a picture (or none) and a caption of `label: value` lines. A section can
also carry records: rows copied out of a file, shown whole with the field they were
joined on marked.

**Every table and every captioned tile section carries a legend**: one short line per
column, in words a reader who knows fractals and not this code would follow.
[`MEANING`] is the vocabulary the pages share, so one column reads the same on every
page, and [`legend`] refuses a label it has no line for.

**The page is drawn from `page.json`**, which is written first and holds exactly what
the page shows, so a reader parsing the step's state reads that file rather than
scraping HTML. Both name the command that wrote them at the top.
`write(..., bundle=DIR)` writes the same page a second time as a folder that can
leave the clone ([`fractal_wallpapers.bundle`]).
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path

from fractal_wallpapers import bundle as bundle_module


@dataclass
class Tile:
    """One picture and the numbers that go beside it."""

    picture: Path | None
    caption: list[tuple[str, object]] = field(default_factory=list)
    title: str = ""
    #: A short flag drawn over the caption — a miss on a check, a forced seat.
    mark: str = ""
    #: `best` or `worst`: consecutive tiles with one band are drawn on a faint
    #: green or red ground, labelled with the word.
    band: str = ""


@dataclass
class Section:
    """A heading, a line of prose, an optional table, and tiles."""

    heading: str
    note: str = ""
    tiles: list[Tile] = field(default_factory=list)
    table: list[list[object]] | None = None
    records: list[Record] = field(default_factory=list)
    #: `[(column, meaning)]`, drawn under the table and the tiles.
    legend: list[tuple[str, str]] = field(default_factory=list)


#: One line per column a page shows, shared so a column means one thing everywhere.
MEANING = {
    "family": "which fractal: the Mandelbrot set, a multibrot of degree 3 to 6, or a Julia "
    "or Phoenix set (julia:multibrot3 is the cubic Julia sets)",
    "found": "places the walk looked at",
    "places": "places it kept",
    "scored": "kept places the location judge has read so far",
    "P(>=3)": "the location judge's probability that a place is worth mining",
    "P(>=4)": "its probability that a place is among the best",
    "median P(>=3)": "the middle P(>=3) of the family's kept places",
    "P(>=3) > .5": "places the location judge thinks more likely than not worth mining",
    "P(>=4) > .5": "places it thinks more likely than not among the best",
    "width": "how wide the view is in the complex plane; smaller is deeper",
    "root channel": "where the walk's starting point for this place came from",
    "mode": "the coloring: how each point's escape is turned into a colour",
    "pictures": "candidate pictures in the pool",
    "judged": "pictures the wallpaper judge has read",
    "at the bar": "pictures whose wallpaper judge P(>=4) is at least 0.5, where a "
    "coloring's own bar starts",
    "median wallpaper judge P(>=4)": "the middle wallpaper judge P(>=4) of those pictures",
    "places drawn": "different places the pictures were drawn from",
    "wallpaper judge P(>=4)": "the wallpaper judge's probability that a picture is good",
    "wallpaper judge P(>=3)": "its probability that a picture is at least decent",
    "gallery judge": "the gallery judge's score; the gallery normally takes pictures above 0.03",
    "seat": "the seat's place in the gallery, in the order the solve filled them",
    "why": "why this one did not make the gallery",
    "file": "a file the chain runs through, in the order it is followed",
    "rows in the file": "how many rows the whole file holds",
    "rows shown": "how many of them are on this page, and in its files/ copy",
}


def legend(*labels: str, said: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """`[(label, meaning)]` for each label, from `said` first and then [`MEANING`].

    A label with no line anywhere raises `KeyError`: a column nobody explained is
    the thing the legend exists to stop.
    """
    words = {**MEANING, **(said or {})}
    return [(label, words[label]) for label in labels]


@dataclass
class Record:
    """One row out of one file, shown whole, with the field it was joined on."""

    file: str
    row: dict | None
    joined_on: str = ""
    key: object = None
    #: Why the chain stopped here, for a row that is missing or a reject.
    note: str = ""


def _cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return "—" if value is None else str(value)


def _plain(value: object):
    """A caption or table value as JSON can hold it."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


_STYLE = """
:root { --bg: #fafafa; --fg: #1a1a1a; --muted: #666; --card: #fff; --line: #ddd;
        --miss: #b3261e; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161616; --fg: #eee; --muted: #999; --card: #222; --line: #333;
          --miss: #ff8a80; } }
body { background: var(--bg); color: var(--fg); font: 14px/1.4 system-ui, sans-serif;
       margin: 0 auto; max-width: 1600px; padding: 16px; }
h1 { font-size: 20px; margin: 0 0 8px; } h2 { font-size: 16px; margin: 24px 0 6px; }
p { color: var(--muted); margin: 4px 0; max-width: 90ch; }
table { border-collapse: collapse; margin: 8px 0; font-variant-numeric: tabular-nums; }
td, th { border: 1px solid var(--line); padding: 3px 8px; text-align: right; }
th:first-child, td:first-child { text-align: left; }
.grid { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 4px;
        overflow: hidden; }
.tile img { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
.tile .none { aspect-ratio: 16 / 9; display: grid; place-items: center; color: var(--muted); }
.tile dl { display: grid; grid-template-columns: auto 1fr; gap: 0 8px; margin: 6px 8px 8px;
           font-variant-numeric: tabular-nums; }
.tile dt { color: var(--muted); } .tile dd { margin: 0; overflow-wrap: anywhere; }
.tile .title { font-weight: 600; margin: 6px 8px 0; overflow-wrap: anywhere; }
.tile .mark { color: var(--miss); font-weight: 700; margin: 6px 8px 0; }
.command { font: 12px/1.4 ui-monospace, Consolas, monospace; color: var(--muted);
           overflow-wrap: anywhere; margin: 0 0 10px; }
.record { margin: 6px 0; } .record summary { cursor: pointer; }
.record pre { background: var(--card); border: 1px solid var(--line); padding: 6px 8px;
              margin: 4px 0; overflow-x: auto; font-size: 12px; white-space: pre-wrap;
              overflow-wrap: anywhere; }
.record mark { background: #ffe08a; color: #1a1a1a; }
.record .note { color: var(--miss); }
.legend { color: var(--muted); font-size: 12px; margin: 6px 0 10px; padding: 0;
          list-style: none; max-width: 110ch; }
.legend b { color: var(--fg); font-weight: 600; }
.band { border-radius: 6px; padding: 6px 8px 8px; margin: 8px 0; }
.band.best { background: rgba(46, 160, 67, .10); }
.band.worst { background: rgba(207, 34, 46, .09); }
.band .label { font-weight: 700; font-size: 12px; text-transform: uppercase;
               letter-spacing: .06em; margin: 0 0 6px; }
.band.best .label { color: #2e8b47; } .band.worst .label { color: #c0392b; }
"""


def document(
    path: Path,
    title: str,
    intro: list[str],
    sections: list[Section],
    command: str,
    pictures: bundle_module.Pictures | None = None,
) -> dict:
    """What the page at `path` shows, as `page.json` holds it.

    A picture is the path the page will use: relative to `path`, or the bundled
    copy's when `pictures` is a bundle's.
    """
    directory = Path(path).parent

    def href(picture) -> str | None:
        if picture is None or not Path(picture).is_file():
            return None
        if pictures is not None:
            return pictures.href(picture)
        return bundle_module.relative_href(picture, directory)

    return {
        "schema": bundle_module.SCHEMA,
        "title": title,
        "command": command,
        "intro": list(intro),
        "sections": [
            {
                "heading": section.heading,
                "note": section.note,
                "table": (
                    [[_plain(cell) for cell in row] for row in section.table]
                    if section.table
                    else None
                ),
                "tiles": [
                    {
                        "picture": href(tile.picture),
                        "title": tile.title,
                        "mark": tile.mark,
                        "band": tile.band,
                        "caption": [[label, _plain(value)] for label, value in tile.caption],
                    }
                    for tile in section.tiles
                ],
                "legend": [[label, meaning] for label, meaning in section.legend],
                "records": [
                    {
                        "file": record.file,
                        "joined_on": record.joined_on,
                        "key": _plain(record.key),
                        "note": record.note,
                        "row": record.row,
                    }
                    for record in section.records
                ],
            }
            for section in sections
        ],
    }


def _record_html(record: dict) -> str:
    joined = (
        f" — joined on <code>{html.escape(record['joined_on'])}</code> = "
        f"<code>{html.escape(_cell(record['key']))}</code>"
        if record["joined_on"]
        else ""
    )
    note = f' <span class="note">{html.escape(record["note"])}</span>' if record["note"] else ""
    if record["row"] is None:
        body = "<pre>(no row)</pre>"
    else:
        text = html.escape(json.dumps(record["row"], ensure_ascii=False))
        if record["joined_on"]:
            # The field the chain walked through, marked where it sits in the row.
            key = json.dumps(record["key"], ensure_ascii=False)
            needle = html.escape(f"{json.dumps(record['joined_on'])}: {key}")
            text = text.replace(needle, f"<mark>{needle}</mark>", 1)
        body = f"<pre>{text}</pre>"
    return (
        f'<details class="record" open><summary><b>{html.escape(record["file"])}</b>'
        f"{joined}{note}</summary>{body}</details>"
    )


def render(doc: dict) -> str:
    """The page, drawn from its `page.json` document and nothing else."""
    out = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(doc['title'])}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{html.escape(doc['title'])}</h1>",
        f'<p class="command">{html.escape(doc["command"])}</p>',
    ]
    out += [f"<p>{html.escape(line)}</p>" for line in doc["intro"]]
    for section in doc["sections"]:
        out.append(f"<h2>{html.escape(section['heading'])}</h2>")
        if section["note"]:
            out.append(f"<p>{html.escape(section['note'])}</p>")
        if section["table"]:
            head, *body = section["table"]
            out.append("<table><tr>" + "".join(f"<th>{html.escape(_cell(c))}</th>" for c in head))
            for row in body:
                out.append("<tr>" + "".join(f"<td>{html.escape(_cell(c))}</td>" for c in row))
            out.append("</table>")
        # Tiles in runs of one band each: a banded run is its own labelled ground.
        runs: list[tuple[str, list[dict]]] = []
        for tile in section["tiles"]:
            band = tile.get("band") or ""
            if runs and runs[-1][0] == band:
                runs[-1][1].append(tile)
            else:
                runs.append((band, [tile]))
        for band, tiles in runs:
            if band:
                out.append(
                    f'<div class="band {html.escape(band)}">'
                    f'<div class="label">{html.escape(band)}</div>'
                )
            out.append('<div class="grid">')
            for tile in tiles:
                out.append('<div class="tile">')
                if tile["picture"] is not None:
                    href = html.escape(tile["picture"], quote=True)
                    out.append(f'<a href="{href}"><img loading="lazy" src="{href}" alt=""></a>')
                else:
                    out.append('<div class="none">no picture</div>')
                if tile["mark"]:
                    out.append(f'<div class="mark">{html.escape(tile["mark"])}</div>')
                if tile["title"]:
                    out.append(f'<div class="title">{html.escape(tile["title"])}</div>')
                out.append("<dl>")
                for label, value in tile["caption"]:
                    out.append(f"<dt>{html.escape(label)}</dt><dd>{html.escape(_cell(value))}</dd>")
                out.append("</dl></div>")
            out.append("</div>")
            if band:
                out.append("</div>")
        if section.get("legend"):
            out.append('<ul class="legend">')
            out += [
                f"<li><b>{html.escape(label)}</b>: {html.escape(meaning)}</li>"
                for label, meaning in section["legend"]
            ]
            out.append("</ul>")
        out += [_record_html(record) for record in section["records"]]
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def _write_both(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / bundle_module.PAGE_JSON).write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    path.write_text(render(doc), encoding="utf-8", newline="\n")


def write(
    path: Path,
    title: str,
    intro: list[str],
    sections: list[Section],
    *,
    command: str | None = None,
    bundle: Path | None = None,
) -> Path:
    """Write `page.json` and the page drawn from it to `path`'s folder; return the page.

    Pictures are linked, never copied. `command` defaults to the running command
    line. `bundle` also writes the page into that folder with its pictures
    re-encoded beside it, and nothing outside it referred to.
    """
    path = Path(path)
    command = bundle_module.invoked() if command is None else command
    _write_both(path, document(path, title, intro, sections, command))
    if bundle is not None:
        bundle = Path(bundle)
        pictures = bundle_module.Pictures(bundle)
        _write_both(
            bundle / "index.html",
            document(bundle / "index.html", title, intro, sections, command, pictures),
        )
    return path
