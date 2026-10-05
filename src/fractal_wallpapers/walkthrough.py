"""Every inspection page of a run through the README's path, as one portable folder.

`fractal-wallpapers walkthrough --out DIR` is the last step of that path. It
writes each page's bundle ([`fractal_wallpapers.bundle`]) side by side, with the
small whole files a reader opens, and a top `index.html` linking them:

```text
DIR/index.html        links every page below, with the command that made it
DIR/walkthrough.json  the same listing, parseable
DIR/judges-check/     `judges check`
DIR/walk-stats/       `harvest stats`
DIR/candidates/       `curate candidate-ledger browse`
DIR/gallery/          a recorded gallery (`curate solve browse`)
DIR/trace/            that gallery traced back to the walk (`curate solve trace`)
DIR/summary.json      the harvest's own summary
DIR/stats.json        `harvest stats`' per-family numbers
DIR/keep.jsonl        the keep list
```

**Nothing is rendered or judged again.** A grid page's bundle is drawn from the
`page.json` its own command left beside it, so each still names the command that
produced it. A page that was never made is listed as missing with that command,
rather than made here, because making it is a step of the path with its own cost.
The gallery and its trace are derivations of the record, so they are written fresh.
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from fractal_wallpapers import bundle as bundle_module
from fractal_wallpapers.paths import tracked_name, under

#: The folder a reader opens by default.
UNIT = "walkthrough"


def out_dir() -> Path:
    """The walkthrough's directory. **The one accessor.**"""
    return under(UNIT)


def _source(href: str, directory: Path) -> Path:
    """A `page.json` picture back to the file it names."""
    if href.startswith("file:"):
        return Path(unquote(urlparse(href).path.lstrip("/")))
    return directory / href


def rebundle(page_dir: Path, into: Path) -> None:
    """A grid page's bundle, drawn from the `page.json` beside it.

    Raises `FileNotFoundError` for a page that has no twin, which is a page its
    command has not been run for (or was run before twins existed).
    """
    from fractal_wallpapers import grid_page

    twin = Path(page_dir) / bundle_module.PAGE_JSON
    doc = json.loads(twin.read_text(encoding="utf-8"))
    if into.is_dir():
        shutil.rmtree(into)
    pictures = bundle_module.Pictures(into)
    for section in doc["sections"]:
        for tile in section["tiles"]:
            if tile["picture"] is not None:
                tile["picture"] = pictures.href(_source(tile["picture"], Path(page_dir)))
    into.mkdir(parents=True, exist_ok=True)
    (into / bundle_module.PAGE_JSON).write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (into / "index.html").write_text(grid_page.render(doc), encoding="utf-8", newline="\n")


def build(out: Path, stamp: str, run_dir: Path, log=print) -> dict:
    """Write every bundle and the index into `out`. Returns the listing."""
    from fractal_wallpapers.curation import candidate_page, tentative, trace

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pages = []

    def grid(folder: str, title: str, page_dir: Path, command: str) -> None:
        try:
            rebundle(page_dir, out / folder)
            pages.append({"folder": folder, "title": title, "made_by": None})
        except FileNotFoundError:
            pages.append({"folder": folder, "title": title, "made_by": command, "missing": True})

    grid(
        "judges-check",
        "Judge check",
        under("judges", "check"),
        "fractal-wallpapers judges check",
    )
    grid(
        "walk-stats",
        "Harvest stats",
        Path(run_dir) / "stats",
        "fractal-wallpapers harvest stats",
    )
    grid(
        "candidates",
        "Candidate pool",
        candidate_page.out_dir(),
        "fractal-wallpapers curate candidate-ledger browse",
    )
    tentative.page(stamp, bundle=out / "gallery", log=lambda _line: None)
    pages.append({"folder": "gallery", "title": f"Gallery {stamp}", "made_by": None})
    trace.build(stamp, bundle=out / "trace", log=lambda _line: None)
    pages.append({"folder": "trace", "title": f"Trace of {stamp}", "made_by": None})

    whole = {
        "summary.json": Path(run_dir) / "summary.json",
        "stats.json": Path(run_dir) / "stats" / "stats.json",
        "keep.jsonl": tentative.keep_path(),
    }
    files = []
    for name, source in whole.items():
        if source.is_file():
            shutil.copyfile(source, out / name)
            files.append({"name": name, "source": tracked_name(source)})
        else:
            files.append({"name": name, "source": tracked_name(source), "missing": True})
    for page in pages:
        folder = out / page["folder"]
        if not page.get("missing"):
            twin = json.loads((folder / bundle_module.PAGE_JSON).read_text(encoding="utf-8"))
            page["command"] = twin["command"]
            page.update(bundle_module.measure(folder))
    listing = {
        "schema": 1,
        "command": bundle_module.invoked(),
        "stamp": stamp,
        "pages": pages,
        "files": files,
    }
    (out / "walkthrough.json").write_text(
        json.dumps(listing, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out / "index.html").write_text(_index(listing), encoding="utf-8", newline="\n")
    for page in pages:
        if page.get("missing"):
            log(f"  {page['folder']:<14} missing: run `{page['made_by']}` first")
        else:
            log(f"  {page['folder']:<14} {page['files']:>3} file(s) {page['bytes'] / 1e6:6.2f} MB")
    return listing


def _index(listing: dict) -> str:
    rows = []
    for page in listing["pages"]:
        if page.get("missing"):
            rows.append(
                f"<tr><td>{html.escape(page['title'])}</td><td>not made: run "
                f"<code>{html.escape(page['made_by'])}</code></td><td></td><td></td></tr>"
            )
            continue
        rows.append(
            f'<tr><td><a href="{page["folder"]}/index.html">{html.escape(page["title"])}</a>'
            f"</td><td><code>{html.escape(page['command'])}</code></td>"
            f"<td>{page['files']}</td><td>{page['bytes'] / 1e6:.2f} MB</td></tr>"
        )
    files = "".join(
        f'<li><a href="{html.escape(item["name"])}">{html.escape(item["name"])}</a> '
        f"<span>from {html.escape(str(item['source']))}</span></li>"
        if not item.get("missing")
        else f"<li>{html.escape(item['name'])}: not there yet</li>"
        for item in listing["files"]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Walkthrough</title><style>
:root {{ --bg: #fafafa; --fg: #1a1a1a; --muted: #666; --line: #ddd; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #161616; --fg: #eee; --muted: #999; --line: #333; }} }}
body {{ background: var(--bg); color: var(--fg); font: 14px/1.5 system-ui, sans-serif;
       margin: 0 auto; max-width: 1100px; padding: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid var(--line); padding: 4px 8px; text-align: left; }}
code {{ font-size: 12px; overflow-wrap: anywhere; }} span {{ color: var(--muted); }}
a {{ color: inherit; }}
</style></head><body>
<h1>Walkthrough</h1>
<p><code>{html.escape(listing["command"])}</code></p>
<p>Every page a reader opens on the way from a fresh clone to a gallery, each a folder of
its own with the JSON it is drawn from. Gallery {html.escape(listing["stamp"])}.</p>
<table><tr><th>page</th><th>made by</th><th>files</th><th>size</th></tr>
{"".join(rows)}
</table>
<h2>Whole files</h2><ul>{files}</ul>
</body></html>
"""
