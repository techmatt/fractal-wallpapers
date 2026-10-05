"""One self-contained HTML page: a grid of pictures with numbers beside them.

The reader doors — `judges score`, `judges check`, `harvest stats`, `curate
candidate-ledger browse` — each write plain files plus one of these, so a person
who has just run a step can open one file and see that the result is sane. The bar
is deliberately low: no server, no script, no framework, nothing fetched. A picture
is referred to by a path relative to the page, so the page works from the file
system and moves only with the pictures it points at.

A page is a title, a few lines of prose, optional tables, and sections of tiles.
A tile is a picture (or none) and a caption of `label: value` lines.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Tile:
    """One picture and the numbers that go beside it."""

    picture: Path | None
    caption: list[tuple[str, object]] = field(default_factory=list)
    title: str = ""
    #: A short flag drawn over the caption — a miss on a check, a forced seat.
    mark: str = ""


@dataclass
class Section:
    """A heading, a line of prose, an optional table, and tiles."""

    heading: str
    note: str = ""
    tiles: list[Tile] = field(default_factory=list)
    table: list[list[object]] | None = None


def _cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return "—" if value is None else str(value)


def _href(picture: Path, directory: Path) -> str:
    try:
        relative = os.path.relpath(Path(picture).resolve(), directory.resolve())
    except ValueError:
        relative = Path(picture).resolve().as_uri()
    return html.escape(str(relative).replace("\\", "/"), quote=True)


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
"""


def write(path: Path, title: str, intro: list[str], sections: list[Section]) -> Path:
    """Write the page to `path` and return it. Pictures are linked, never copied."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    directory = path.parent
    out = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
    ]
    out += [f"<p>{html.escape(line)}</p>" for line in intro]
    for section in sections:
        out.append(f"<h2>{html.escape(section.heading)}</h2>")
        if section.note:
            out.append(f"<p>{html.escape(section.note)}</p>")
        if section.table:
            head, *body = section.table
            out.append("<table><tr>" + "".join(f"<th>{html.escape(_cell(c))}</th>" for c in head))
            for row in body:
                out.append("<tr>" + "".join(f"<td>{html.escape(_cell(c))}</td>" for c in row))
            out.append("</table>")
        if section.tiles:
            out.append('<div class="grid">')
            for tile in section.tiles:
                out.append('<div class="tile">')
                if tile.picture is not None and Path(tile.picture).is_file():
                    out.append(
                        f'<a href="{_href(tile.picture, directory)}">'
                        f'<img loading="lazy" src="{_href(tile.picture, directory)}" alt=""></a>'
                    )
                else:
                    out.append('<div class="none">no picture</div>')
                if tile.mark:
                    out.append(f'<div class="mark">{html.escape(tile.mark)}</div>')
                if tile.title:
                    out.append(f'<div class="title">{html.escape(tile.title)}</div>')
                out.append("<dl>")
                for label, value in tile.caption:
                    out.append(f"<dt>{html.escape(label)}</dt><dd>{html.escape(_cell(value))}</dd>")
                out.append("</dl></div>")
            out.append("</div>")
    out.append("</body></html>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return path
