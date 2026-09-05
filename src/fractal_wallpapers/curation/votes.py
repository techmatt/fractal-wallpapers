"""The voting kit: a recorded gallery as a folder somebody who is not here can rate.

Matt hands a thousand seats to friends. What travels is a zip -- two JPEGs per
seat, one HTML file and a paragraph of instructions -- and what comes back is one
small JSON file per person. Nothing in between needs a server, an account, or this
repository.

## The picture a friend sees is made here, never copied

A seat's stored candidate is 640x360, the size the judges read, and it is far too
small to vote on. So every seat in a kit is **rendered again** at [`FRAME`]
through [`curation.release`], exactly the way a shipped wallpaper is, and the
thumbnail is a downscale of *that*. Never of the candidate: the two are different
pictures, at different sizes, under different autolevel curves, and a grid of
candidate thumbnails over a fullscreen of fresh renders would be asking people to
vote on one picture while showing them another.

The release path measures its own curve at the frame it is rendering, so a seat
whose candidate curve was never recorded is not a special case here. Nothing in a
kit replays a curve, and `curation.depth.levelling_of` is a question about the
640x360 picture rather than about this one.

## The full is lossless first and JPEG second

`colorize.render` writes PNG and the kit ships JPEG, so encoding is a second step
over the render's own bytes rather than something the renderer is told. That is
what lets a pilot price the quality grid against a reference that is not itself a
JPEG, and it is why [`encode`] is the one encoder both sides call. The PNG is
deleted as soon as its two JPEGs exist: a thousand of them is ten gigabytes and
the whole point of a kit is that it fits in a message.

**`subsampling` is passed on every encode and never left to Pillow.** Pillow picks
4:2:0 below quality 95 and 4:4:4 at or above it, silently, so a grid that named
only the quality would be comparing two chroma decisions it never made.

## The page is opened by double-clicking, and that rules out almost everything

`file://` refuses `fetch` of a sibling file, so the seat list is embedded in the
page as JSON. No server, no build step, no CDN: the only external references are
relative paths to JPEGs in the folder beside it. This is
[`curation.tentative.page`]'s constraint, met the same way.

## A filename carries the seat's position and nothing else

No rank, no key, no mode. A friend who can read a rank off a filename has been
told the answer, and a friend who can read the mode is being invited to vote on
the mode. The **export** carries the recipe key, which is the ID that survives
every later merge ([`curation.tentative`]'s first property), so an ingest written
months from now joins on something that still names the same picture.

## The order is per-viewer and it is a permutation, not a shuffle of a window

Seeded from the viewer's own name, so reopening the folder resumes the same walk
rather than re-randomising what they have already seen. There is no sort, no
filter and no search: this is the one place in the project where a person is asked
what they like, and every affordance for finding a particular picture is an
affordance for voting on something other than the picture in front of them.

## What ingest will be handed, fixed here

`{viewer, record, name, order_seed, votes: {<recipe key>: 1 | 2}, pages_visited,
exported_at}` -- [`VIEWER`] names the shape. An export is the **complete** state
every time, so it is idempotent by name and the latest file per person wins. There
is no ingest in this module and there is not meant to be one yet: the schema is the
contract and the votes have to exist before anything reads them.
"""

from __future__ import annotations

import html
import json
import shutil
import time
import zipfile
from pathlib import Path

from fractal_wallpapers.curation import release, tentative

#: The shape of an exported label file. It travels on every export and an ingest
#: reads it before anything else, because the friends' copies of a kit outlive
#: this checkout's memory of what version wrote them.
VIEWER = "votes/v1"

#: What every seat is rendered at. The frame and not a [`release.Regime`]: the
#: supersample under it is the caller's, priced by `scratch/votes_pilot`, and the
#: frame is not -- a wallpaper is voted on at the size it will be used at.
FRAME = (2560, 1440)

#: The supersample a kit builds at unless told another. **4**, and it is the
#: expensive default in this file: **76.2 s a picture** on the locked three
#: workers, measured over the forty-seat kit, so a thousand seats is **21.2 h**
#: against something near 5.4 at ss2.
#:
#: It is the default anyway because the supersample is the **only** decision here
#: a person can see. ss2 against ss4 is a mean absolute difference of **6.28**
#: over the six pilot seats and **4.81** after fitting to 1080p, where the whole
#: quality axis from q95 to q80 moves the busiest crop by 3.71 to 6.09 — so
#: dropping to ss2 to save fifteen hours costs more picture than dropping five
#: quality steps does, and it costs it as aliasing rather than as softness.
SUPERSAMPLE = 4

#: How wide a thumbnail is. 512 at 16:9 is 512x288 -- two of them across a phone,
#: five across the grid this page lays out, and small enough that a thousand of
#: them is a fraction of the fulls.
THUMB_WIDTH = 512

#: The JPEG quality a kit encodes at unless told another, and the chroma with it.
#: **85 at 4:2:0**, on the pilot's grid, and the reasoning is size rather than
#: fidelity: a thousand fulls at ss4 measures **1.13 GB** here against a projected
#: 1.31 at q90 and 1.82 at q95, and the busiest 1:1 crop at this cell is not
#: visibly apart from its own PNG. Chroma is the cheaper half of the same trade —
#: 4:2:0 is 24% smaller than 4:4:4 for 0.66 of mean absolute difference in the
#: busiest window, on pictures nobody will view at 1:1.
#:
#: **The zip is the constraint this record has not answered.** Every cell of the
#: grid puts a thousand seats between 0.88 and 2.88 GB, which is more than a
#: person sends a friend. Lowering the quality does not fix it; the frame or the
#: seat count would have to.
QUALITY = 85
CHROMA = "420"

#: What a chroma name means to Pillow. Two, because a wallpaper is either given
#: full colour resolution or the one every camera and every phone already uses,
#: and 4:2:2 is a third answer nobody asked for.
SUBSAMPLING = {"444": 0, "420": 2}

#: How many seats a page of the viewer holds. A thousand seats is ten pages, which
#: is a number a person can hold in their head while deciding whether to carry on.
PAGE = 100

#: The three names a kit's folder holds beside its two picture directories.
PAGE_NAME = "index.html"
READ_ME = "README.txt"
FULLS, THUMBS, STAGING = "full", "thumbs", "_png"


class VotesRefused(RuntimeError):
    """A voting kit cannot be built from what was named."""


# --------------------------------------------------------------------------- #
# Names and bytes.
# --------------------------------------------------------------------------- #
def seat_name(index: int) -> str:
    """A seat's filename stem: its **position** in the record, zero-padded.

    Four digits, which covers the thousand this exists for and the two thousand
    the next solve is reaching at. Nothing else is in the name on purpose -- see
    the module docstring.
    """
    return f"s{int(index):04d}"


def encode(image, path: Path, quality: int = QUALITY, chroma: str = CHROMA) -> int:
    """Write `image` as JPEG and return its byte count. **THE encoder.**

    The pilot's grid and the kit's own pictures come through here, so a cell Matt
    chose off a sheet is the cell a friend is looking at rather than something
    that resembles it.
    """
    if chroma not in SUBSAMPLING:
        raise VotesRefused(f"{chroma!r} is not a chroma; it is one of {sorted(SUBSAMPLING)}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    writing = Path(str(path) + ".writing")
    image.convert("RGB").save(
        writing,
        format="JPEG",
        quality=int(quality),
        subsampling=SUBSAMPLING[chroma],
        optimize=True,
    )
    writing.replace(path)
    return path.stat().st_size


# --------------------------------------------------------------------------- #
# The seats, and the pictures under them.
# --------------------------------------------------------------------------- #
def plan(stamp: str | None = None, limit: int | None = None) -> tuple[str, list[dict]]:
    """`(stamp, jobs)` -- the record's seats in seat order, cut to `limit`.

    A job carries the position, the key and the name, and it is what everything
    below joins on. The record's own row rides along under `row` for the manifest
    and for nothing the page ever sees.
    """
    stamp = tentative.latest() if stamp is None else str(stamp)
    rows = tentative.read_rows(stamp)
    if not rows:
        raise VotesRefused(f"{stamp} holds no seats to vote on.")
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    return stamp, [
        {"index": index, "key": str(row["key"]), "name": seat_name(index), "row": row}
        for index, row in enumerate(rows)
    ]


def recipes_for(jobs: list[dict]) -> dict:
    """`{key: recipe}` for the jobs that still need rendering.

    [`candidate_ledger.by_key`] and not a read: this wants a few hundred recipes
    out of a store of hundreds of thousands, and reading the whole ledger for them
    would hold every other row in memory for the length of a render leg.
    """
    from fractal_wallpapers.curation import candidate_ledger

    wanted = [job["key"] for job in jobs]
    rows = candidate_ledger.by_key(wanted)
    missing = set(wanted) - set(rows)
    if missing:
        raise VotesRefused(
            f"{len(missing)} seat(s) name a recipe the ledger does not hold -- "
            f"{sorted(missing)[:3]}. A seat cannot be rendered without its recipe."
        )
    return {key: row["recipe"] for key, row in rows.items()}


def render_fulls(jobs, staging: Path, regime, workers: int, arrived, log=print) -> dict:
    """Render each job's full-size PNG into `staging`, `arrived(job, png)` per row.

    **Module level and replaceable**, which is what lets the fast lane drive the
    whole of [`build`] -- the encode, the downscale, the page, the zip -- without
    an engine. Everything downstream of a picture is exercised either way, because
    `arrived` is called on this side of the seam rather than beyond it.

    `arrived` runs in the parent, once per job, in plan order: it is
    [`release.run_pass`]'s sink, and the reason a kit encodes and deletes as it
    goes instead of at the end is that a thousand of these PNGs is ten gigabytes.
    """
    staging.mkdir(parents=True, exist_ok=True)
    recipes = recipes_for(jobs)
    by_key = {job["key"]: job for job in jobs}
    tasks, standing = [], []
    for job in jobs:
        recipe = recipes[job["key"]]
        picture = staging / f"{job['key']}.png"
        if picture.is_file():
            standing.append(job)
            continue
        tasks.append(
            release.Task(
                id=job["key"],
                row={
                    "family": recipe["family"],
                    "viewport": recipe["viewport"],
                    "maxiter": recipe["maxiter"],
                },
                colormap=recipe["colormap"],
                mode=recipe["mode"],
                mode_params=dict(recipe.get("mode_params") or {}),
                output=str(picture),
                geometry={**regime.geometry(), "maxiter": int(recipe["maxiter"])},
            )
        )
    for job in standing:
        arrived(job, staging / f"{job['key']}.png")
    failed = []

    def sink(task, result):
        if result.ok:
            arrived(by_key[task.id], Path(result.info["picture"]))
        else:
            failed.append({"key": task.id, "error": result.error})
            log(f"[votes] {task.id} failed at {regime.spelled}: {result.error}")

    started = time.monotonic()
    record = release.run_pass(tasks, workers, sink, log)
    seconds = time.monotonic() - started
    made = len(tasks) - len(failed)
    return {
        "regime": regime.spelled,
        "workers": int(workers),
        "planned": len(tasks),
        "standing": len(standing),
        "made": made,
        "failed": failed,
        "leg_seconds": round(seconds, 1),
        "seconds_per_picture": round(seconds / max(1, made), 1),
        "pass_record": record,
    }


def cut(png: Path, job: dict, fulls: Path, thumbs: Path, quality: int, chroma: str) -> dict:
    """One render into the two JPEGs a kit ships, and the PNG gone after.

    The thumbnail is a `LANCZOS` reduction of the **full render** and there is no
    path here that reads the candidate: that is the claim the fast lane checks by
    building a kit whose candidates do not exist on disk at all.

    The `<stem>.leveled/` directory goes with the PNG. `colorize.render` writes one
    beside every acted render -- the operator's overriding colormap, ~76 KiB --
    and it is spelled here the way the writer spells it, because a staging tree
    that kept a thousand of those would be most of what a deleted PNG saved.
    """
    from PIL import Image

    with Image.open(png) as opened:
        opened.load()
        full_bytes = encode(opened, fulls / f"{job['name']}.jpg", quality, chroma)
        height = max(1, round(opened.height * THUMB_WIDTH / opened.width))
        small = opened.resize((THUMB_WIDTH, height), Image.LANCZOS)
    thumb_bytes = encode(small, thumbs / f"{job['name']}.jpg", quality, chroma)
    png.unlink(missing_ok=True)
    shutil.rmtree(png.parent / f"{png.stem}.leveled", ignore_errors=True)
    return {"full_bytes": full_bytes, "thumb_bytes": thumb_bytes}


# --------------------------------------------------------------------------- #
# The folder a friend opens.
# --------------------------------------------------------------------------- #
def page(directory: Path, stamp: str, jobs: list[dict]) -> Path:
    """Write `index.html`. Self-contained, and openable over `file://`."""
    keys = [job["key"] for job in jobs]
    path = directory / PAGE_NAME
    writing = Path(str(path) + ".writing")
    writing.write_text(
        _PAGE.replace("__RECORD__", html.escape(str(stamp)))
        .replace("__VIEWER__", html.escape(VIEWER))
        .replace("__PAGE__", str(int(PAGE)))
        .replace("__SEATS__", str(len(keys)))
        .replace("__KEYS__", json.dumps(keys, ensure_ascii=False)),
        encoding="utf-8",
        newline="\n",
    )
    writing.replace(path)
    return path


def read_me(directory: Path) -> Path:
    """The paragraph the friends read. One, and no jargon in it."""
    path = directory / READ_ME
    path.write_text(_READ_ME, encoding="utf-8", newline="\n")
    return path


def archive(directory: Path, log=print) -> Path:
    """Zip the kit beside itself, deflated, with nothing from the staging tree.

    Named off the folder rather than through `with_suffix`, which would eat
    everything after a dot in a folder somebody called `kit.v2`.

    **The JPEGs are stored and only the text is deflated.** Deflate on an already
    compressed picture is minutes of CPU for a fraction of a percent, and a kit is
    a gigabyte of pictures beside twenty kilobytes of page.
    """
    path = directory.parent / f"{directory.name}.zip"
    writing = Path(str(path) + ".writing")
    with zipfile.ZipFile(writing, "w") as bundle:
        for item in sorted(directory.rglob("*")):
            if item.is_dir() or STAGING in item.relative_to(directory).parts:
                continue
            bundle.write(
                item,
                Path(directory.name, item.relative_to(directory)).as_posix(),
                compress_type=(
                    zipfile.ZIP_STORED
                    if item.suffix.lower() in {".jpg", ".jpeg", ".png"}
                    else zipfile.ZIP_DEFLATED
                ),
            )
    writing.replace(path)
    log(f"[votes] {path} — {path.stat().st_size / 1e6:.1f} MB")
    return path


def build(
    stamp: str | None = None,
    out: Path | str | None = None,
    limit: int | None = None,
    quality: int = QUALITY,
    chroma: str = CHROMA,
    supersample: int = SUPERSAMPLE,
    workers: int | None = None,
    log=print,
) -> dict:
    """The whole kit: render, encode, thumbnail, page, paragraph, zip.

    Resumable at the seat: a seat whose two JPEGs are already there is not
    rendered again, so a killed leg picks up where it stopped and a kit rebuilt at
    another quality has to be built somewhere else -- which is the honest
    behaviour, because the quality is not in the filename either.
    """
    if out is None:
        raise VotesRefused("a kit is built into a directory; name one with --out.")
    if chroma not in SUBSAMPLING:
        raise VotesRefused(f"{chroma!r} is not a chroma; it is one of {sorted(SUBSAMPLING)}.")
    directory = Path(out)
    workers = release.DEFAULT_WORKERS if workers is None else int(workers)
    regime = release.Regime(FRAME, int(supersample))
    stamp, jobs = plan(stamp, limit)
    fulls, thumbs = directory / FULLS, directory / THUMBS
    for where in (fulls, thumbs, directory / STAGING):
        where.mkdir(parents=True, exist_ok=True)

    def done(job: dict) -> bool:
        return (fulls / f"{job['name']}.jpg").is_file() and (
            thumbs / f"{job['name']}.jpg"
        ).is_file()

    standing = [job for job in jobs if done(job)]
    wanted = [job for job in jobs if not done(job)]
    sizes: list[dict] = []

    def arrived(job, png):
        sizes.append({"name": job["name"], **cut(png, job, fulls, thumbs, quality, chroma)})

    log(
        f"[votes] {stamp}: {len(jobs)} seat(s), {len(standing)} already encoded, "
        f"{len(wanted)} to render at {regime.spelled} on {workers} worker(s)"
    )
    rendered = (
        render_fulls(wanted, directory / STAGING, regime, workers, arrived, log)
        if wanted
        else {"regime": regime.spelled, "planned": 0, "made": 0, "failed": []}
    )
    written = page(directory, stamp, jobs)
    read_me(directory)
    staging = directory / STAGING
    if staging.is_dir() and not any(staging.iterdir()):
        staging.rmdir()
    bundle = archive(directory, log)
    full_bytes = [row["full_bytes"] for row in sizes]
    manifest = {
        "schema": 1,
        "viewer": VIEWER,
        "record": stamp,
        "seats": len(jobs),
        "encoding": {"quality": int(quality), "chroma": chroma, "regime": regime.spelled},
        "where": str(directory),
        "page": str(written),
        "zip": str(bundle),
        "zip_bytes": bundle.stat().st_size,
        "render": rendered,
        "full_bytes": {
            "mean": round(sum(full_bytes) / len(full_bytes)) if full_bytes else None,
            "max": max(full_bytes) if full_bytes else None,
        },
    }
    log(
        f"[votes] {len(jobs)} seat(s) at q{quality} {chroma}, "
        f"{manifest['zip_bytes'] / 1e6:.1f} MB zipped"
    )
    return manifest


#: What the friends read before they open anything. One paragraph, and every
#: sentence in it is something they have to do -- there is no explanation of what
#: a fractal is, what a seat is, or what happens to the file afterwards, because
#: none of that changes what they should click.
_READ_ME = """Thanks for helping pick wallpapers.

Unzip this folder somewhere and open index.html — it opens in your browser and
needs nothing installed. Type your name when it asks. You'll see pages of
pictures. If you like one, click the thumbs-up under it; if you really like one,
click the star instead. Skip everything else — most of them should be skipped,
and there's no number you're trying to reach. Click a picture to see it large,
and press Escape to come back. Your choices are saved as you go, so you can close
the page and come back to it later.

When you're done, click Export at the top. Your browser will save a small file.
Send that file back and you're finished.
"""


#: The viewer, as one string with five substitutions: `__KEYS__`, `__RECORD__`,
#: `__VIEWER__`, `__PAGE__` and `__SEATS__`, all filled by [`page`]. Kept here
#: rather than in a tracked asset file for [`tentative`]'s reason -- a second file
#: is a second thing to find -- and it is the second and last page this project
#: writes for a person to drive.
_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pick the wallpapers you like</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #101216; color: #e8eaed;
         font: 14px/1.5 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
  header { position: sticky; top: 0; z-index: 3; background: #181b21;
           border-bottom: 1px solid #2a2f38; padding: 9px 14px;
           display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
  header .who { font-weight: 600; }
  header .grow { flex: 1; }
  .tally { font-variant-numeric: tabular-nums; color: #c6cbd3; }
  .pager { display: flex; gap: 5px; flex-wrap: wrap; }
  button { background: #262b34; color: #e8eaed; border: 1px solid #39404b;
           border-radius: 5px; padding: 5px 10px; font: inherit; cursor: pointer; }
  button:hover { background: #333a45; }
  button.on { background: #3d5cc4; border-color: #6f8ae8; }
  main { display: grid; gap: 12px; padding: 14px 14px 70px;
         grid-template-columns: repeat(5, minmax(0, 1fr)); }
  @media (max-width: 1100px) { main { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
  @media (max-width: 680px) { main { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .tile { border: 3px solid transparent; border-radius: 8px; overflow: hidden;
          background: #181b21; }
  .tile.up { border-color: #4ade80; }
  .tile.star { border-color: #fbbf24; }
  .tile img { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover;
              background: #0b0d10; cursor: zoom-in; }
  .bar { display: flex; gap: 6px; padding: 6px; }
  .bar button { flex: 1; padding: 4px 0; font-size: 15px; line-height: 1.2; }
  .bar button.on { background: #3d5cc4; border-color: #6f8ae8; }
  #big { position: fixed; inset: 0; z-index: 5; background: #06070a;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 10px; }
  #big img { max-width: 100vw; max-height: calc(100vh - 62px); object-fit: contain; }
  #big .bar { width: min(420px, 90vw); }
  #gate { position: fixed; inset: 0; z-index: 9; background: #101216;
          display: grid; place-items: center; padding: 20px; }
  #gate div { max-width: 460px; }
  #gate h1 { font-size: 19px; margin: 0 0 10px; }
  #gate p { color: #aeb5bf; }
  #gate input { background: #0b0d10; color: #e8eaed; border: 1px solid #39404b;
                border-radius: 5px; padding: 8px 10px; font: inherit; width: 220px; }
  [hidden] { display: none !important; }
</style>
<header hidden id="strip">
  <span class="who" id="who"></span>
  <span class="tally" id="tally"></span>
  <span class="grow"></span>
  <span class="pager" id="pager"></span>
  <button id="export">Export</button>
</header>
<main id="grid" hidden></main>
<div id="big" hidden>
  <img id="bigimg" alt="">
  <div class="bar">
    <button data-v="1">&#128077; like <small>(1)</small></button>
    <button data-v="2">&#9733; love <small>(2)</small></button>
  </div>
</div>
<div id="gate">
  <div>
    <h1>Pick the wallpapers you like</h1>
    <p>Type your name, then rate the ones you like with the thumbs-up, and the
       ones you really like with the star. Skip everything else.</p>
    <p><input id="name" placeholder="your name" autofocus>
       <button id="start">Start</button></p>
  </div>
</div>
<script>
const KEYS = __KEYS__;
const RECORD = "__RECORD__";
const VIEWER = "__VIEWER__";
const PER_PAGE = __PAGE__;
const PAGES = Math.max(1, Math.ceil(KEYS.length / PER_PAGE));
const NAME_KEY = "votes/" + RECORD + "/name";

let who = "";
let votes = {};
let visited = [];
let order = [];
let seed = 0;
let page = 0;
let hovered = null;
let open = null;
let scrolled = 0;

function pad(index) { return "s" + String(index).padStart(4, "0"); }

// FNV-1a over the name, so the same person gets the same walk every time they
// open the folder — a fresh shuffle on reopening would re-show what they had
// already decided about.
function seedOf(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function permutation(count, source) {
  const out = Array.from({length: count}, (_, i) => i);
  for (let i = count - 1; i > 0; i--) {
    const j = Math.floor(source() * (i + 1));
    const swap = out[i]; out[i] = out[j]; out[j] = swap;
  }
  return out;
}

function slot() { return "votes/" + RECORD + "/" + who; }

function save() {
  try {
    localStorage.setItem(slot(), JSON.stringify({votes: votes, pages: visited}));
  } catch (e) { /* a private window keeps nothing; the page still works */ }
}

function load() {
  try {
    const held = JSON.parse(localStorage.getItem(slot()) || "{}");
    votes = held.votes || {};
    visited = held.pages || [];
  } catch (e) { votes = {}; visited = []; }
}

function tally() {
  let up = 0, star = 0;
  for (const key in votes) { if (votes[key] === 2) star++; else if (votes[key] === 1) up++; }
  document.getElementById("tally").textContent =
    "\\u{1F44D} " + up + " \\u00B7 \\u2605 " + star;
}

function vote(index, kind) {
  const key = KEYS[index];
  if (votes[key] === kind) delete votes[key]; else votes[key] = kind;
  save();
  tally();
  paintTile(index);
}

function paintTile(index) {
  const tile = document.querySelector('[data-i="' + index + '"]');
  if (!tile) return;
  const kind = votes[KEYS[index]];
  tile.classList.toggle("up", kind === 1);
  tile.classList.toggle("star", kind === 2);
  for (const button of tile.querySelectorAll(".bar button")) {
    button.classList.toggle("on", Number(button.dataset.v) === kind);
  }
}

function drawPage(next) {
  page = Math.max(0, Math.min(PAGES - 1, next));
  if (!visited.includes(page)) { visited.push(page); save(); }
  const grid = document.getElementById("grid");
  grid.textContent = "";
  for (const index of order.slice(page * PER_PAGE, (page + 1) * PER_PAGE)) {
    const tile = document.createElement("figure");
    tile.className = "tile";
    tile.dataset.i = index;
    tile.style.margin = "0";
    const image = document.createElement("img");
    image.src = "thumbs/" + pad(index) + ".jpg";
    image.loading = "lazy";
    image.alt = "";
    image.addEventListener("click", () => enlarge(index));
    const bar = document.createElement("div");
    bar.className = "bar";
    for (const [kind, face] of [[1, "\\u{1F44D}"], [2, "\\u2605"]]) {
      const button = document.createElement("button");
      button.dataset.v = kind;
      button.textContent = face;
      button.addEventListener("click", () => vote(index, kind));
      bar.appendChild(button);
    }
    tile.appendChild(image);
    tile.appendChild(bar);
    tile.addEventListener("mouseenter", () => { hovered = index; });
    tile.addEventListener("mouseleave", () => { if (hovered === index) hovered = null; });
    grid.appendChild(tile);
    paintTile(index);
  }
  drawPager();
  window.scrollTo(0, 0);
}

function drawPager() {
  const pager = document.getElementById("pager");
  pager.textContent = "";
  for (let p = 0; p < PAGES; p++) {
    const button = document.createElement("button");
    button.textContent = String(p + 1);
    if (p === page) button.className = "on";
    button.addEventListener("click", () => drawPage(p));
    pager.appendChild(button);
  }
}

function enlarge(index) {
  if (open === null) scrolled = window.scrollY;
  open = index;
  document.getElementById("bigimg").src = "full/" + pad(index) + ".jpg";
  const big = document.getElementById("big");
  big.hidden = false;
  for (const button of big.querySelectorAll("button")) {
    button.classList.toggle("on", Number(button.dataset.v) === votes[KEYS[index]]);
  }
}

function shut() {
  open = null;
  document.getElementById("big").hidden = true;
  window.scrollTo(0, scrolled);
}

function step(by) {
  const at = order.indexOf(open);
  const next = at + by;
  if (at < 0 || next < 0 || next >= order.length) return;
  const wanted = Math.floor(next / PER_PAGE);
  // Stepping off the end of a page turns the page under the fullscreen. The
  // scroll position to come back to is that page's top, not the offset held
  // from the page they opened the picture on.
  if (wanted !== page) { drawPage(wanted); scrolled = 0; }
  enlarge(order[next]);
}

function rate(index, kind) {
  vote(index, kind);
  // A vote in fullscreen is a decision taken, so it closes: the next picture is
  // what somebody who has just decided wants to see.
  if (open === index) shut();
}

document.getElementById("start").addEventListener("click", begin);
document.getElementById("name").addEventListener("keydown", (event) => {
  if (event.key === "Enter") begin();
});

function begin() {
  const typed = document.getElementById("name").value.trim();
  if (!typed) return;
  who = typed;
  try { localStorage.setItem(NAME_KEY, who); } catch (e) { /* nothing kept */ }
  start();
}

function start() {
  seed = seedOf(who);
  order = permutation(KEYS.length, mulberry32(seed));
  load();
  document.getElementById("gate").hidden = true;
  document.getElementById("strip").hidden = false;
  document.getElementById("grid").hidden = false;
  document.getElementById("who").textContent = who;
  tally();
  // The furthest page they reached, not the first: reopening the folder is
  // carrying on, and starting them again at page one is asking them to scroll
  // past everything they have already decided about.
  drawPage(visited.length ? Math.max(...visited) : 0);
}

for (const button of document.querySelectorAll("#big .bar button")) {
  button.addEventListener("click", () => rate(open, Number(button.dataset.v)));
}

document.addEventListener("keydown", (event) => {
  if (document.getElementById("gate").hidden === false) return;
  if (event.key === "Escape" && open !== null) { shut(); return; }
  if (open !== null && event.key === "ArrowRight") { step(1); return; }
  if (open !== null && event.key === "ArrowLeft") { step(-1); return; }
  if (event.key !== "1" && event.key !== "2") return;
  const target = open !== null ? open : hovered;
  if (target !== null) rate(target, Number(event.key));
});

document.getElementById("export").addEventListener("click", () => {
  const payload = {
    viewer: VIEWER,
    record: RECORD,
    name: who,
    order_seed: seed,
    votes: votes,
    pages_visited: visited.slice().sort((a, b) => a - b),
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(payload, null, 1)], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = who.replace(/[^A-Za-z0-9_-]+/g, "_") + "_labels.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
});

const remembered = (function () {
  try { return localStorage.getItem(NAME_KEY); } catch (e) { return null; }
})();
if (remembered) { who = remembered; start(); }
</script>
"""

__all__ = [
    "CHROMA",
    "FRAME",
    "PAGE",
    "QUALITY",
    "SUPERSAMPLE",
    "THUMB_WIDTH",
    "VIEWER",
    "VotesRefused",
    "archive",
    "build",
    "cut",
    "encode",
    "page",
    "plan",
    "read_me",
    "recipes_for",
    "render_fulls",
    "seat_name",
]
