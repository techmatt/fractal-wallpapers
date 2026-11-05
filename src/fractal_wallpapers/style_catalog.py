"""The custom-mode catalog: one row per style, and the page Matt marks them on.

`data/styles/catalog.json` (tracked) is the single record of where each style stands
as a custom mode for the explorer's dropdown:

    {"schema": 1,
     "modes": [{"style": "<style name>", "score": 1-5, "status": "publish|drop|discarded",
                "item": "<queue item>", "reference": "<the style file's reference image>",
                "variant": "<the published variant: the style file's default stack>",
                "show": [{"keep": "<keep id in <style>.keeps.json>", "caption": "..."}],
                "public": {"name": "<public name>", "palette": "<matched colormap>",
                           "knobs": ["<knob name in the style file's public block>", ...]},
                "what": "<one line>", "kept": "<what was kept, in words>",
                "note": "<the card's footnote>"}]}

`public` is a published mode's alone, and its knobs are named here and defined in the
style file (`data/styles/README.md`'s *Public knobs*), so `check` holds the two to
agreeing. Names are proposals Matt may rename: they are data, never code.

`style gallery` rebuilds `fractal-drive-sync/custom-modes/`: `index.html` and the
downscaled pictures in `img/` (each style's reference and the keeps the row shows,
read from `fractal-drive-sync/style-refs/` and `style-keeps/<style>/`), the Publish /
Maybe / Drop toggles starting from each row's status.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any

from fractal_wallpapers.paths import repo_root

#: The one schema the catalog carries today.
SCHEMA = 1

#: A row's status: shown with a toggle (`publish`, `drop`), or listed as discarded.
STATUSES = ("publish", "drop", "discarded")

#: The page's picture sizes: a keep and a reference, at most this wide.
KEEP_WIDTH = 960
REFERENCE_WIDTH = 1280
JPEG_QUALITY = 85


class CatalogError(ValueError):
    """A catalog that does not read, or disagrees with the styles it names."""


def catalog_path() -> Path:
    """The tracked catalog."""
    from fractal_wallpapers import styles

    return styles.styles_dir() / styles.CATALOG_FILE


def gallery_folder() -> Path:
    """Where the page goes: beside the reference pictures, never git."""
    return repo_root().parent / "fractal-drive-sync" / "custom-modes"


def load(path: Path | None = None) -> dict[str, Any]:
    """The catalog, checked; a `CatalogError` names every disagreement."""
    path = path or catalog_path()
    if not path.is_file():
        raise CatalogError(f"no catalog at {path}")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    problems = check(catalog)
    if problems:
        raise CatalogError("catalog out of step:\n  " + "\n  ".join(problems))
    return catalog


def keeps_of(style: str) -> dict[str, dict[str, Any]]:
    """A style's recorded keeps, by id; empty when it has none."""
    from fractal_wallpapers import style_keeps

    path = style_keeps.keeps_path(style)
    if not path.is_file():
        return {}
    return {entry["id"]: entry for entry in json.loads(path.read_text("utf-8"))["keeps"]}


def check(catalog: dict[str, Any]) -> list[str]:
    """Each way the catalog disagrees with itself or the styles; empty when it holds."""
    from fractal_wallpapers import styles
    from fractal_wallpapers.paths import colormap_dir

    if catalog.get("schema") != SCHEMA:
        return [f"schema {catalog.get('schema')}, expected {SCHEMA}"]
    problems = []
    seen = set()
    public_names = set()
    for row in catalog["modes"]:
        name = row.get("style", "?")
        if name in seen:
            problems.append(f"{name}: two rows")
        seen.add(name)
        try:
            document = styles.load(name)
        except styles.StyleError as refusal:
            problems.append(str(refusal))
            continue
        if row.get("reference") != document["reference"]["image"]:
            problems.append(f"{name}: reference {row.get('reference')} is not the style's")
        # No status is a mode Matt has not ruled on yet: its toggles start unmarked.
        if "status" in row and row["status"] not in STATUSES:
            problems.append(f"{name}: status {row.get('status')} is not one of {STATUSES}")
        if row.get("score") not in range(1, 6):
            problems.append(f"{name}: score {row.get('score')} is not 1 to 5")
        keeps = keeps_of(name)
        for shown in row.get("show", []):
            if shown["keep"] not in keeps:
                problems.append(f"{name}: shows '{shown['keep']}', not in its keeps")
        public = row.get("public")
        if row.get("status") != "publish":
            if public:
                problems.append(f"{name}: a {row.get('status')} mode has a public block")
            continue
        if not row.get("variant") or not public:
            problems.append(f"{name}: a published mode names its variant and public block")
            continue
        if public.get("name") in public_names:
            problems.append(f"{name}: public name {public.get('name')} is taken")
        public_names.add(public.get("name"))
        if not (colormap_dir() / f"{public.get('palette')}.json").is_file():
            problems.append(f"{name}: no colormap '{public.get('palette')}'")
        knobs = [knob["name"] for knob in (document.get("public") or {}).get("knobs") or []]
        if public.get("knobs") != knobs:
            problems.append(f"{name}: knobs {public.get('knobs')}, the style file's {knobs}")
        if not 3 <= len(knobs) <= 5:
            problems.append(f"{name}: {len(knobs)} public knobs, not 3 to 5")
        problems += [f"{name}: {problem}" for problem in styles.check_public(document)]
    return problems


#: Beside the page's pictures: which source and stamp each was shrunk from, so a rebuild
#: redraws a picture only when its row now shows another keep or the keep was redrawn.
SOURCES_FILE = "sources.json"


def shrink(source: Path, target: Path, width: int, drawn: dict[str, str]) -> bool:
    """A JPEG of `source` at most `width` wide; False when `drawn` says it is current."""
    from PIL import Image

    if not source.is_file():
        raise CatalogError(f"no picture at {source}")
    stamp = f"{source.as_posix()}@{source.stat().st_mtime_ns}"
    current = drawn.get(target.name) == stamp and target.is_file()
    drawn[target.name] = stamp
    if current:
        return False
    with Image.open(source) as image:
        image = image.convert("RGB")
        if image.width > width:
            image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
        image.save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return True


def stars(score: int) -> str:
    """A score as five stars."""
    return "★" * score + "☆" * (5 - score)


def link(target: Path, folder: Path) -> str:
    """`target` relative to the page, as a URL path."""
    return html.escape(Path(os.path.relpath(target, folder)).as_posix(), quote=True)


STYLE_SHEET = """\
:root{--bg:#111316;--panel:#1a1d22;--ink:#e8e6e1;--mute:#9aa0a8;--line:#2c3138;--acc:#d9b26a;\
--pub:#3f8f5a;--may:#b08a2e;--drop:#8f3f3f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);\
font:15px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1600px;margin:0 auto;padding:20px 16px 60px}h1{font-size:24px;margin:0 0 4px}\
.sub{color:var(--mute);margin:0 0 16px}
.bar{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;\
border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.bar button{background:var(--panel);color:var(--ink);border:1px solid var(--line);\
padding:6px 12px;border-radius:6px;cursor:pointer}
#tally{color:var(--mute)}.mode{background:var(--panel);border:1px solid var(--line);\
border-radius:10px;padding:14px;margin:16px 0}
.mode header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}h2{margin:0;\
font-size:19px;font-family:ui-monospace,Consolas,monospace}
.score{color:var(--acc);letter-spacing:2px}.meta{color:var(--mute);font-size:13px}\
.pub{margin-left:auto;display:flex;gap:6px}
.pub button{background:transparent;color:var(--mute);border:1px solid var(--line);\
padding:4px 10px;border-radius:6px;cursor:pointer}
.pub button.on[data-v=publish]{background:var(--pub);color:#fff;border-color:var(--pub)}\
.pub button.on[data-v=maybe]{background:var(--may);color:#fff;border-color:var(--may)}\
.pub button.on[data-v=drop]{background:var(--drop);color:#fff;border-color:var(--drop)}
.what{margin:6px 0 10px}.row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
figure{margin:0}figure img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:6px;\
display:block;background:#000}
figure.ref img{outline:2px solid var(--acc);outline-offset:-2px}figcaption{font-size:12px;\
color:var(--mute);margin-top:4px;overflow-wrap:anywhere}
.foot{font-size:12px;color:var(--mute);margin:10px 0 0}h3{margin:28px 0 8px}
.public{font-size:13px;margin:8px 0 0}.public b{color:var(--acc)}
.dis{display:flex;gap:12px;align-items:center;margin:8px 0;color:var(--mute)}\
.dis img{width:200px;aspect-ratio:16/10;object-fit:cover;border-radius:6px;opacity:.75}
ul{color:var(--mute)}textarea{width:100%;height:110px;background:var(--panel);color:var(--ink);\
border:1px solid var(--line);border-radius:6px;font:12px ui-monospace,monospace;display:none;\
margin-top:8px}
@media(max-width:900px){.row{grid-template-columns:repeat(2,minmax(0,1fr))}.pub{margin-left:0}}
#lb{position:fixed;inset:0;z-index:50;background:rgba(0,0,0,.88);display:none;\
align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:24px;\
cursor:zoom-out}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:88vh;object-fit:contain;\
border-radius:6px;cursor:default;box-shadow:0 8px 40px #000}
#lb .cap{color:#cfd3d8;font-size:13px;text-align:center;max-width:90vw}#lb .x{position:absolute;\
top:12px;right:18px;color:#cfd3d8;font-size:28px;background:none;border:0;cursor:pointer}
"""

OVERLAY = (
    '<div id="lb" role="dialog" aria-modal="true" aria-label="Expanded image">'
    '<button class="x" aria-label="Close">×</button><img alt=""><div class="cap"></div></div>'
)

OVERLAY_SCRIPT = """\
(()=>{const lb=document.getElementById('lb'),im=lb.querySelector('img'),\
cap=lb.querySelector('.cap');
function close(){lb.classList.remove('on');im.removeAttribute('src')}
document.addEventListener('click',e=>{const a=e.target.closest('a.zoom');if(!a)return;\
e.preventDefault();im.src=a.getAttribute('href');cap.textContent=a.dataset.cap||'';\
lb.classList.add('on')});
lb.addEventListener('click',e=>{if(e.target!==im)close()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&lb.classList.contains('on'))\
close()})})();
"""

SCRIPT = """\
const S=__STATUS__;const K='custom-modes-choices-__HASH__';let c={...S};
try{const s=JSON.parse(localStorage.getItem(K)||'null');if(s)c=s}catch(e){}
function save(){try{localStorage.setItem(K,JSON.stringify(c))}catch(e){}}
function paint(){let n={publish:0,maybe:0,drop:0},t=0;document.querySelectorAll('.mode')\
.forEach(s=>{t++;const v=c[s.dataset.id];if(v)n[v]++;s.querySelectorAll('.pub button')\
.forEach(b=>b.classList.toggle('on',b.dataset.v===v))});
document.getElementById('tally').textContent=`${t} modes · publish ${n.publish} · maybe \
${n.maybe} · drop ${n.drop} · unmarked ${t-n.publish-n.maybe-n.drop}`}
document.querySelectorAll('.pub button').forEach(b=>b.onclick=()=>{const id=b.closest('.mode')\
.dataset.id;c[id]=c[id]===b.dataset.v?undefined:b.dataset.v;if(!c[id])delete c[id];save();\
paint()});
document.getElementById('copy').onclick=async()=>{const txt='custom-modes choices: '+\
JSON.stringify(c);const o=document.getElementById('out');o.value=txt;o.style.display='block';\
o.select();try{await navigator.clipboard.writeText(txt)}catch(e){}};
paint();
"""

INTRO = (
    "Each render mode beside the reference that guided it, your score, and up to three of "
    "your keeps (click any image for full size; Esc closes it). Each toggle starts from the "
    "catalog's status (data/styles/catalog.json); mark each one to publish to Mandelnaut's "
    "custom-modes dropdown."
)


def zoom(full: str, small: str, caption: str) -> str:
    """A thumbnail that opens `full` in the page's overlay, captioned mode and picture.

    `full` is already a URL path (`link`); the href stays the full picture, so the page
    still works with scripts off.
    """
    return (
        f'<a class="zoom" href="{full}" data-cap="{html.escape(caption, quote=True)}">'
        f'<img loading="lazy" src="{small}" alt=""></a>'
    )


def card(row: dict[str, Any], document: dict[str, Any], images: dict[str, str]) -> str:
    """One mode's section: header and toggles, its line, the reference and keeps."""
    name = row["style"]
    esc = html.escape
    meta = f"item {row['item']} · kept: {row['kept']}" if row.get("kept") else f"item {row['item']}"
    reference = f"reference · {row['reference']}"
    figures = [
        f'<figure class="ref">{zoom(images["ref_link"], images["ref"], f"{name} · {reference}")}'
        f"<figcaption>{esc(reference)}</figcaption></figure>"
    ]
    for shown, (small, full) in zip(row.get("show", []), images["keeps"], strict=True):
        figures.append(
            f"<figure>{zoom(full, small, name + ' · ' + shown['caption'])}"
            f"<figcaption>{esc(shown['caption'])}</figcaption></figure>"
        )
    public = ""
    if row.get("public"):
        knobs = (document.get("public") or {}).get("knobs") or []
        dials = ", ".join(
            f"{esc(knob['label'])} ({knob['range'][0]:g}–{knob['range'][1]:g})" for knob in knobs
        )
        public = (
            f'\n <p class="public">Public: <b>{esc(row["public"]["name"])}</b> · palette '
            f"{esc(row['public']['palette'])} · variant {esc(row['variant'])} · knobs: {dials}</p>"
        )
    return (
        f'<section class="mode" data-id="{esc(name)}">\n'
        f' <header><h2>{esc(name)}</h2><span class="score" title="{row["score"]}/5">'
        f'{stars(row["score"])}</span><span class="meta">{esc(meta)}</span>\n'
        ' <div class="pub" role="group"><button data-v="publish">Publish</button>'
        '<button data-v="maybe">Maybe</button><button data-v="drop">Drop</button></div>'
        "</header>\n"
        f' <p class="what">{esc(row.get("what", document["description"]))}</p>\n'
        f' <div class="row">{"".join(figures)}</div>{public}\n'
        f' <p class="foot">{esc(row.get("note", ""))}</p>\n'
        "</section>"
    )


def page(catalog: dict[str, Any], cards: list[str], discarded: list[str], rest: list[str]) -> str:
    """The whole page."""
    shown = [row for row in catalog["modes"] if row.get("status") != "discarded"]
    status = {row["style"]: row["status"] for row in shown if row.get("status")}
    digest = hashlib.sha256(json.dumps(status, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    script = SCRIPT.replace("__STATUS__", json.dumps(status)).replace("__HASH__", digest)
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1">',
        f"<title>Custom Modes</title><style>\n{STYLE_SHEET}</style></head><body><main>",
        f'<h1>Custom modes</h1><p class="sub">{html.escape(INTRO)}</p>',
        '<div class="bar"><span id="tally"></span><button id="copy">Copy choices</button>'
        '<span class="sub" style="margin:0">then paste them to Claude</span></div>',
        '<textarea id="out" readonly></textarea>',
        *cards,
        "<h3>Discarded</h3>" + "".join(discarded),
    ]
    if rest:
        items = "".join(f"<li>{html.escape(name)}</li>" for name in rest)
        parts.append(f"<h3>In the library, not yet catalogued</h3><ul>{items}</ul>")
    parts.append(
        f"</main><script>\n{script}</script>{OVERLAY}<script>\n{OVERLAY_SCRIPT}</script>"
        "</body></html>\n"
    )
    return "\n".join(parts)


def gallery(folder: Path, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rebuild the page in `folder` and its pictures in `folder/img/`.

    A picture is redrawn only when its source is newer; an `img/` file no row names is
    removed, since the folder is the page's own.
    """
    from fractal_wallpapers import style_keeps, styles

    catalog = catalog or load()
    img = folder / "img"
    img.mkdir(parents=True, exist_ok=True)
    ledger = img / SOURCES_FILE
    drawn = json.loads(ledger.read_text("utf-8")) if ledger.is_file() else {}
    wanted: set[str] = set()
    written = 0
    cards, discarded = [], []
    for row in catalog["modes"]:
        name = row["style"]
        document = styles.load(name)
        reference = styles.reference_path(document)
        ref_small = f"{name}__ref.jpg"
        written += shrink(reference, img / ref_small, REFERENCE_WIDTH, drawn)
        wanted.add(ref_small)
        if row.get("status") == "discarded":
            esc = html.escape
            full = link(reference, folder)
            caption = f"{name} · reference · {row['reference']}"
            discarded.append(
                f'<div class="dis">{zoom(full, f"img/{ref_small}", caption)}<div>'
                f"<b>{esc(name)}</b> (item {esc(row['item'])}) {stars(row['score'])}<br>"
                f"{esc(row.get('note', ''))}</div></div>"
            )
            continue
        keeps = keeps_of(name)
        pictures = []
        for index, shown in enumerate(row.get("show", [])):
            source = style_keeps.keeps_folder(name) / keeps[shown["keep"]]["image"]
            small = f"{name}__{index}.jpg"
            written += shrink(source, img / small, KEEP_WIDTH, drawn)
            wanted.add(small)
            pictures.append((f"img/{small}", link(source, folder)))
        images = {"ref": f"img/{ref_small}", "ref_link": link(reference, folder), "keeps": pictures}
        cards.append(card(row, document, images))
    for stale in img.glob("*.jpg"):
        if stale.name not in wanted:
            stale.unlink()
    with ledger.open("w", encoding="utf-8", newline="\n") as handle:
        kept = {name: drawn[name] for name in sorted(wanted)}
        handle.write(json.dumps(kept, indent=1, ensure_ascii=False) + "\n")
    catalogued = {row["style"] for row in catalog["modes"]}
    rest = [name for name in styles.names() if name not in catalogued]
    target = folder / "index.html"
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(page(catalog, cards, discarded, rest))
    return {
        "page": target,
        "modes": len(catalog["modes"]),
        "shown": len(cards),
        "discarded": len(discarded),
        "images": len(wanted),
        "written": written,
    }
