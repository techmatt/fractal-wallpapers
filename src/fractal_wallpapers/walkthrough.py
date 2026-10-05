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
DIR/render/           the README's two render examples, each a modest JPEG, and
                      render.json: the command that made each and its seconds here
DIR/parameters.json   everything a reader can set on one render (`parameters.py`)
DIR/help/             the `--help` text of every command on the README's path
```

**Nothing on the path is rendered or judged again.** A grid page's bundle is drawn
from the `page.json` its own command left beside it, so each still names the command
that produced it. A page that was never made is listed as missing with that command,
rather than made here, because making it is a step of the path with its own cost.
The gallery and its trace are derivations of the record, so they are written fresh.
The two render examples are the one thing drawn here: they are seconds each, and
their point is the time they took on the reader's own machine.
"""

from __future__ import annotations

import contextlib
import html
import io
import json
import os
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from fractal_wallpapers import bundle as bundle_module
from fractal_wallpapers.paths import tracked_name, under

#: The folder a reader opens by default.
UNIT = "walkthrough"

#: The README's step-1 link: a quadratic Julia set in `tia`.
LINK = (
    "https://techmatt.github.io/fractals/explorer/?v=4&f=julia&cx=-1.2540170796954613"
    "&cy=-0.07161459637319667&m=tia&x=-0.336363658629224&y=-0.06271709146615745"
    "&w=0.5659066537374874&p=Oxblood%2C%20Cyan%2C%20Cream&phase=0.597858"
)

#: The README's two render examples, plain flags first, **as the README spells
#: them**; the suite holds the README's step 1 to these. `out` is the argument the
#: walkthrough points into its own folder instead.
RENDERS = [
    {
        "name": "render",
        "argv": [
            "fractal-wallpapers", "render", "--family", "julia", "--c", "-0.75", "0.11",
            "--center-re", "0", "--center-im", "0",
            "--width", "3", "--mode", "stripe", "--cycles", "2",
            "--out", "artifacts/first.png",
        ],
    },
    {
        "name": "render-link",
        "argv": [
            "engine/target/release/fractal-engine", "render-link", "--size", "2560x1440",
            "--out", "artifacts/seat.png", "--link", LINK,
        ],
    },
]  # fmt: skip

#: The width a render example is re-encoded at, and its JPEG quality: big enough to
#: judge the picture by, a few hundred kilobytes at most.
RENDER_WIDTH = 1280
RENDER_QUALITY = 82

#: Every `fractal-wallpapers` command on the README's path, in path order, whose
#: `--help` lands in `help/`. The suite holds every command the README's path runs
#: to this list.
HELP = [
    ("fetch-weights",),
    ("render",),
    ("modes",),
    ("palettes", "list"),
    ("judges", "check"),
    ("judges", "score"),
    ("harvest",),
    ("curate", "score"),
    ("harvest", "export"),
    ("harvest", "stats"),
    ("curate", "embed"),
    ("curate", "hunt", "run"),
    ("curate", "hunt", "merge"),
    ("curate", "candidate-ledger", "browse"),
    ("gallery-grade", "score-pool"),
    ("curate", "solve", "run"),
    ("curate", "solve", "record"),
    ("curate", "solve", "browse"),
    ("curate", "solve", "release"),
    ("curate", "mine", "run"),
    ("curate", "mine", "merge"),
    ("curate", "solve", "trace"),
    ("walkthrough",),
]

#: The engine's own subcommands on the path, beside the `fractal-wallpapers` ones.
ENGINE_HELP = ["render-link"]

#: The width help text is wrapped at, so a file reads the same from any terminal.
HELP_COLUMNS = 100


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


def subparser(path: tuple[str, ...]):
    """The parser of one `fractal-wallpapers` command, nested verbs and all."""
    import argparse

    from fractal_wallpapers import cli

    parser = cli.build_parser()
    for word in path:
        actions = [
            action
            for action in parser._actions  # noqa: SLF001
            if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
        ]
        parser = next(action.choices[word] for action in actions if word in action.choices)
    return parser


def write_help(directory: Path) -> list[str]:
    """Each command's `--help` as `<words>.txt`. Returns the file names."""
    directory = Path(directory)
    if directory.is_dir():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    from fractal_wallpapers import engine

    held = os.environ.get("COLUMNS")
    os.environ["COLUMNS"] = str(HELP_COLUMNS)
    names = []
    try:
        for path in HELP:
            name = "-".join(path) + ".txt"
            text = subparser(path).format_help()
            (directory / name).write_text(text, encoding="utf-8", newline="\n")
            names.append(name)
    finally:
        if held is None:
            os.environ.pop("COLUMNS", None)
        else:
            os.environ["COLUMNS"] = held
    for subcommand in ENGINE_HELP:
        name = f"fractal-engine-{subcommand}.txt"
        (directory / name).write_text(engine.usage(subcommand), encoding="utf-8", newline="\n")
        names.append(name)
    return names


def write_renders(directory: Path) -> list[dict]:
    """Draw the README's two render examples here, timed. Returns `render.json`'s rows.

    Each is drawn at the README's own size into a temporary full-size file, which
    is re-encoded at `RENDER_WIDTH` and deleted, so the folder stays small.
    """
    from PIL import Image

    from fractal_wallpapers import cli, engine

    directory = Path(directory)
    if directory.is_dir():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    rows = []
    for example in RENDERS:
        argv = example["argv"]
        full = directory / f"{example['name']}.full{Path(argv[argv.index('--out') + 1]).suffix}"
        started = time.perf_counter()
        if argv[1] == "render-link":
            size = argv[argv.index("--size") + 1].split("x")
            engine.render_link(argv[argv.index("--link") + 1], (int(size[0]), int(size[1])), full)
        else:
            ran = list(argv[1:])
            ran[ran.index("--out") + 1] = str(full)
            with contextlib.redirect_stdout(io.StringIO()):
                if cli.main(ran) != 0:
                    raise RuntimeError(f"`{' '.join(argv)}` failed")
        seconds = round(time.perf_counter() - started, 2)
        picture = directory / f"{example['name']}.jpg"
        with Image.open(full) as image:
            size = [image.width, image.height]
            image = image.convert("RGB")
            image = image.resize(
                (RENDER_WIDTH, round(image.height * RENDER_WIDTH / image.width)), Image.LANCZOS
            )
            image.save(picture, "JPEG", quality=RENDER_QUALITY, optimize=True, progressive=True)
        full.unlink()
        rows.append(
            {
                "name": example["name"],
                "command": argv,
                "rendered_at": size,
                "seconds": seconds,
                "picture": picture.name,
                "shown_at": RENDER_WIDTH,
            }
        )
    (directory / "render.json").write_text(
        json.dumps({"schema": 1, "renders": rows}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return rows


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
    from fractal_wallpapers import parameters

    (out / "parameters.json").write_text(
        json.dumps(parameters.describe(), indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    renders = write_renders(out / "render")
    helps = write_help(out / "help")
    listing = {
        "schema": 1,
        "command": bundle_module.invoked(),
        "stamp": stamp,
        "pages": pages,
        "files": files,
        "renders": [{key: row[key] for key in ("name", "picture", "seconds")} for row in renders],
        "help": helps,
    }
    (out / "walkthrough.json").write_text(
        json.dumps(listing, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out / "index.html").write_text(_index(listing), encoding="utf-8", newline="\n")
    for row in renders:
        log(f"  render/{row['picture']:<18} {row['seconds']:.2f} s")
    log(f"  help/          {len(helps)} file(s); parameters.json")
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
    renders = "".join(
        f'<figure><a href="render/{html.escape(row["picture"])}"><img '
        f'src="render/{html.escape(row["picture"])}" alt=""></a><figcaption>'
        f"<code>{html.escape(row['name'])}</code>, {row['seconds']:.2f} s on this run "
        f"(the command is in render/render.json)</figcaption></figure>"
        for row in listing["renders"]
    )
    helps = "".join(
        f'<li><a href="help/{html.escape(name)}">{html.escape(name)}</a></li>'
        for name in listing["help"]
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
figure {{ margin: 8px 0; }} figure img {{ width: 100%; max-width: 640px; display: block; }}
</style></head><body>
<h1>Walkthrough</h1>
<p><code>{html.escape(listing["command"])}</code></p>
<p>Every page a reader opens on the way from a fresh clone to a gallery, each a folder of
its own with the JSON it is drawn from. Gallery {html.escape(listing["stamp"])}.</p>
<table><tr><th>page</th><th>made by</th><th>files</th><th>size</th></tr>
{"".join(rows)}
</table>
<h2>Whole files</h2><ul>{files}</ul>
<h2>The README's two renders, drawn on this run</h2>{renders}
<h2>What a render can set</h2>
<p><a href="parameters.json">parameters.json</a>: every family, every coloring mode (and
which are production), the palette names, and each number's default and range, marked
settable by a flag of <code>fractal-wallpapers render</code> or only by a spec JSON.</p>
<h2>Every command's --help</h2><ul>{helps}</ul>
</body></html>
"""
